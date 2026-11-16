"""Supervisor externo do Safety Plus; apenas biblioteca padrão do Python."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request
from datetime import datetime, timezone


def run(root, args, **kwargs):
    return subprocess.run(['docker', 'compose', '--project-directory', str(root), *args],
                          check=True, timeout=kwargs.pop('timeout', 30), **kwargs)


def healthy(root, service):
    try:
        ids = run(root, ['ps', '-q', service], capture_output=True, text=True).stdout.split()
        if len(ids) != 1:
            return False
        result = subprocess.run(['docker', 'inspect', '--format',
                                 '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}', ids[0]],
                                capture_output=True, text=True, check=True, timeout=15)
        return result.stdout.strip() == 'running healthy'
    except (subprocess.SubprocessError, OSError):
        return False


def recovery(state, web_ok, db_ok, now, enabled):
    """Só reinicia web após 3 falhas, com banco saudável e intervalo de uma hora."""
    state['failures'] = 0 if web_ok else int(state.get('failures', 0)) + 1
    return (enabled and not web_ok and db_ok and state['failures'] >= 3
            and now - state.get('last_restart', 0) >= 3600)


def save_state(path, state):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state))
    tmp.replace(path)


def monitor(root, directory):
    path = directory / 'state.json'
    # Estado corrompido interrompe a execução; não libera reinícios adicionais.
    state = json.loads(path.read_text()) if path.exists() else {}
    db_ok, web_ok = healthy(root, 'db'), healthy(root, 'web')
    disk = shutil.disk_usage(root)
    report = {'event': 'monitor', 'db_ok': db_ok, 'web_ok': web_ok,
              'disk_used_percent': round(100 * disk.used / disk.total, 1)}
    url = os.getenv('MAINTENANCE_HEALTH_URL', '')
    if url:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                report['https_ok'] = json.loads(response.read(65536)).get('ok') is True
        except Exception:
            report['https_ok'] = False
    restart = recovery(state, web_ok, db_ok, time.time(),
                       os.getenv('MAINTENANCE_AUTO_RESTART', '0') == '1')
    if restart:
        # Persiste o limite ANTES da tentativa, inclusive quando docker falhar.
        state['last_restart'] = time.time()
    state['checks'] = dict(report)
    state['checked_at'] = time.time()
    save_state(path, state)
    if restart:
        run(root, ['restart', 'web'], timeout=90)
        report['web_restart_requested'] = True
    report['attention'] = (not web_ok or not db_ok or report.get('https_ok') is False
                           or report['disk_used_percent'] >= 85)
    print(json.dumps(report), flush=True)
    return 1 if report['attention'] else 0


def backup(root, directory):
    target = directory / 'backups'
    target.mkdir(mode=0o700, exist_ok=True)
    if shutil.disk_usage(target).free < 2 * 1024**3:
        raise RuntimeError('Menos de 2 GiB livres para iniciar backup')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    pending = target / (stamp + '.partial')
    pending.mkdir(mode=0o700)
    # Formato custom permite conferir o catálogo com pg_restore, sem restaurar produção.
    with (pending / 'database.dump').open('wb') as output:
        run(root, ['exec', '-T', 'db', 'sh', '-c',
                   'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB"'], stdout=output, timeout=1800)
    with (pending / 'database.dump').open('rb') as source:
        run(root, ['exec', '-T', 'db', 'sh', '-c',
                   'pg_restore --list -U "$POSTGRES_USER"'], stdin=source,
            stdout=subprocess.DEVNULL, timeout=300)
    with (pending / 'storage.tar.gz').open('wb') as output:
        run(root, ['exec', '-T', 'web', 'tar', '-C', '/app', '-czf', '-', 'storage'],
            stdout=output, timeout=1800)
    with tarfile.open(pending / 'storage.tar.gz', 'r:gz') as archive:
        count = 0
        for entry in archive:
            count += 1
            if entry.isfile():
                with archive.extractfile(entry) as source:
                    while source.read(1024**2):
                        pass
        if not count:
            raise RuntimeError('Arquivo de storage vazio')
    if not (pending / 'database.dump').stat().st_size:
        raise RuntimeError('Backup do banco vazio')
    (pending / 'manifest.json').write_text(json.dumps({
        'created_at_utc': stamp, 'validation': 'pg_restore --list + leitura integral do tar',
        'restore_tested': False, 'storage_entries': count}))
    pending.rename(target / stamp)
    print(json.dumps({'event': 'backup_verified', 'path': str(target / stamp),
                      'restore_tested': False}), flush=True)


def module_tests(root, directory):
    """Executa a suíte numa cópia descartável, sem rede ou volumes de produção."""
    import uuid
    image = run(root, ['images', '-q', 'web'], capture_output=True, text=True).stdout.split()
    if not image:
        raise RuntimeError('Imagem do serviço web não encontrada')
    reports = []
    started = time.time()
    log_path = directory / 'module-tests.log'
    with log_path.open('w') as log:
        for group in ('apr', 'pts', 'checklists', 'racs'):
            name = 'safetyplus-check-' + uuid.uuid4().hex[:12]
            command = ['docker', 'run', '--rm', '--name', name, '--network', 'none',
                       '--read-only', '--user', '65534:65534', '--cap-drop', 'ALL',
                       '--security-opt', 'no-new-privileges', '--pids-limit', '128',
                       '--memory', '768m', '--cpus', '1', '--tmpfs', '/tmp:rw,size=512m,mode=1777',
                       '-e', 'PYTHONDONTWRITEBYTECODE=1', '--workdir', '/checks']
            for folder in ('app', 'tests', 'tools'):
                command += ['--mount', f'type=bind,source={root.resolve()/folder},target=/checks/{folder},readonly']
            command += ['--entrypoint', 'python', image[0], '/checks/tools/module_checks.py', '--worker', group]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=600)
                log.write(f'\n=== {group} ===\n'+result.stderr+'\n'+result.stdout)
                report = json.loads(result.stdout.strip().splitlines()[-1])
                reports.append({'group': group, 'passed': result.returncode == 0 and report.get('passed') is True and int(report.get('tests', 0)) > int(report.get('skipped', 0)),
                                'tests': int(report.get('tests', 0)), 'failures': int(report.get('failures', 0)),
                                'errors': int(report.get('errors', 0)), 'skipped': int(report.get('skipped', 0))})
            except (subprocess.SubprocessError, OSError, ValueError, IndexError, TypeError) as error:
                log.write(f'{group}: {type(error).__name__}\n')
                reports.append({'group': group, 'passed': False, 'tests': 0, 'errors': 1})
            finally:
                subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=30)
    report = {'completed_at_utc': datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC'),
              'passed': all(r['passed'] for r in reports), 'groups': reports,
              'duration_seconds': round(time.time()-started, 1)}
    save_state(directory / 'module-tests.json', report)
    print(json.dumps({'event': 'module_tests', **report}), flush=True)
    return 0 if report['passed'] else 1


def publish_status(directory):
    """Publica somente metadados; o app não ganha acesso ao Docker ou aos backups."""
    state_path = directory / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    def active(unit):
        try:
            return subprocess.run(['systemctl', 'is-active', '--quiet', unit], timeout=5,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    backups = []
    for path in sorted((directory / 'backups').glob('*/manifest.json'), reverse=True):
        if path.parent.name.endswith('.partial'):
            continue
        try:
            manifest = json.loads(path.read_text())
            backups.append({'created_at_utc': manifest['created_at_utc'],
                            'restore_tested': manifest.get('restore_tested') is True})
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if len(backups) >= 20:
            break
    checked = state.get('checked_at')
    data = {'schema': 1, 'updated_at': checked or 0,
            'checked_at_label': datetime.fromtimestamp(checked, timezone.utc).strftime('%d/%m/%Y %H:%M UTC') if checked else '',
            'checks': {k: state.get('checks', {}).get(k) for k in ('web_ok', 'db_ok', 'https_ok')},
            'auto_restart': os.getenv('MAINTENANCE_AUTO_RESTART', '0') == '1',
            'monitor_timer_active': active('safetyplus-monitor.timer'),
            'backup_timer_active': active('safetyplus-backup.timer'), 'backups': backups}
    try:
        data['module_tests'] = json.loads((directory / 'module-tests.json').read_text())
    except (OSError, ValueError):
        data['module_tests'] = None
    public = directory / 'public'
    public.mkdir(mode=0o755, exist_ok=True)
    tmp = public / 'status.tmp'
    tmp.write_text(json.dumps(data))
    tmp.chmod(0o644)
    tmp.replace(public / 'status.json')


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['monitor', 'backup', 'test'])
    parser.add_argument('--root', type=Path, default=Path('/opt/safety-plus'))
    parser.add_argument('--state-dir', type=Path, default=Path('/var/lib/safetyplus-maintenance'))
    args = parser.parse_args()
    args.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Backup e recuperação nunca executam simultaneamente.
    with (args.state_dir / 'maintenance.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('{"event":"skipped_locked"}')
            return 0
        try:
            if args.action == 'monitor':
                return monitor(args.root, args.state_dir)
            if args.action == 'test':
                return module_tests(args.root, args.state_dir)
            backup(args.root, args.state_dir)
            return 0
        finally:
            publish_status(args.state_dir)


if __name__ == '__main__':
    raise SystemExit(main())
