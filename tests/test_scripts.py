"""Verificações dos inicializadores e da atualização, sem Docker ou rede."""
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def executable(path, source):
    path.write_text(source, encoding='utf-8')
    path.chmod(0o755)


class UpdateScriptTests(unittest.TestCase):
    def run_update(self, scenario):
        fixture = tempfile.TemporaryDirectory(prefix='safety-script-')
        self.addCleanup(fixture.cleanup)
        root = Path(fixture.name)
        source, target, commands = [root / p for p in ('source', 'target', 'bin')]
        for p in (source, target, commands):
            p.mkdir()
        shutil.copy2(ROOT / 'ATUALIZAR_VPS.sh', source)
        (source / 'version.txt').write_text('new')
        (target / 'version.txt').write_text('old')
        (target / '.env').write_text('DOMAIN=localhost\n')
        (target / 'docker-compose.yml').write_text('services: {}\n')
        with tarfile.open(root / 'storage.tar.gz', 'w:gz') as archive:
            info = tarfile.TarInfo('storage/example.txt')
            info.size = 3
            archive.addfile(info, io.BytesIO(b'abc'))
        executable(commands / 'id', '#!/bin/sh\nprintf "0\\n"\n')
        executable(commands / 'sleep', '#!/bin/sh\nexit 0\n')
        executable(commands / 'docker', f'''#!{sys.executable}
import json, os, pathlib, sys
root = pathlib.Path(os.environ['MOCK_ROOT'])
scenario = os.environ['MOCK_SCENARIO']
args = sys.argv[1:]
with (root / 'calls.jsonl').open('a') as out:
    out.write(json.dumps(args)+'\\n')
if args[:2] == ['compose', 'ps']:
    if '--status' in args:
        if scenario == 'query_failure': sys.exit(1)
        if scenario != 'stopped': print('container-id')
    else: print('NAME IMAGE COMMAND SERVICE CREATED STATUS PORTS')
elif args[:5] == ['compose', 'exec', '-T', 'db', 'sh']:
    if scenario == 'sql_failure': sys.exit(1)
    if scenario != 'sql_empty': print('-- PostgreSQL dump')
elif args[:5] == ['compose', 'exec', '-T', 'web', 'sh']:
    if scenario == 'storage_failure': sys.exit(1)
    data = b'invalid archive' if scenario == 'storage_invalid' else (root / 'storage.tar.gz').read_bytes()
    sys.stdout.buffer.write(data)
elif args[:5] == ['compose', 'exec', '-T', 'web', 'python']:
    if scenario == 'health_failure' and '/health' in args[-1]: sys.exit(1)
    print('{{"ok":true}}')
''')
        result = subprocess.run(
            ['bash', str(source / 'ATUALIZAR_VPS.sh'), str(target)],
            env={**os.environ, 'PATH': str(commands) + os.pathsep + os.environ['PATH'],
                 'MOCK_ROOT': str(root), 'MOCK_SCENARIO': scenario},
            capture_output=True, text=True, timeout=15,
        )
        calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]
        return result, target, calls

    def test_success_validates_backups_before_up(self):
        result, target, calls = self.run_update('success')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((target / 'version.txt').read_text(), 'new')
        self.assertIn(['compose', 'ps', '--status', 'running', '-q', 'db'], calls)
        self.assertIn(['compose', 'ps', '--status', 'running', '-q', 'web'], calls)
        archives = list((target / 'backups').glob('storage_*.tar.gz'))
        self.assertEqual(len(archives), 1)
        with tarfile.open(archives[0]) as archive:
            self.assertIn('storage/example.txt', archive.getnames())
        self.assertEqual(archives[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(list((target / 'backups').glob('postgres_*.sql'))), 1)
        self.assertFalse(list((target / 'backups').glob('*.partial')))
        self.assertIn(['compose', 'up', '-d', '--build', '--remove-orphans'], calls)

    def test_backup_failures_stop_before_copy_and_restart(self):
        for scenario in ('stopped', 'query_failure', 'sql_failure', 'sql_empty',
                         'storage_failure', 'storage_invalid'):
            with self.subTest(scenario=scenario):
                result, target, calls = self.run_update(scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual((target / 'version.txt').read_text(), 'old')
                self.assertFalse(any(call[:2] == ['compose', 'up'] for call in calls))

    def test_health_failure_returns_failure(self):
        result, _, calls = self.run_update('health_failure')
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(call[:2] == ['compose', 'logs'] for call in calls))


class LocalLauncherTests(unittest.TestCase):
    def test_linux_defaults_and_environment_overrides(self):
        for overrides in ({}, {'ADMIN_PASSWORD': 'custom-password', 'ADMIN_USER': 'custom',
                               'APP_SECRET': 'custom-secret', 'SECURE_COOKIES': 'true'}):
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                shutil.copy2(ROOT / 'INICIAR_TESTE_LOCAL.sh', root)
                commands = root / '.venv' / 'bin'
                commands.mkdir(parents=True)
                (commands / 'activate').write_text(f'export PATH="{commands}:$PATH"\n')
                executable(commands / 'pip', '#!/bin/sh\nexit 0\n')
                executable(commands / 'python', f'''#!{sys.executable}
import json, os, pathlib
pathlib.Path('environment.json').write_text(json.dumps(dict(os.environ)))
raise SystemExit(0 if len(os.environ['ADMIN_PASSWORD']) >= 8 else 1)
''')
                executable(commands / 'uvicorn', '#!/bin/sh\nexit 0\n')
                environment = {k: v for k, v in os.environ.items()
                               if k not in ('ADMIN_PASSWORD', 'ADMIN_USER', 'APP_SECRET', 'SECURE_COOKIES')}
                result = subprocess.run(['sh', str(root / 'INICIAR_TESTE_LOCAL.sh')],
                                        env={**environment, **overrides}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = json.loads((root / 'environment.json').read_text())
                self.assertGreaterEqual(len(actual['ADMIN_PASSWORD']), 8)
                for key, value in overrides.items():
                    self.assertEqual(actual[key], value)

    def test_windows_requirement_check_detects_missing_and_wrong_versions(self):
        script = (ROOT / 'INICIAR_TESTE_LOCAL.bat').read_text(encoding='utf-8-sig')
        # Execute the actual Python check embedded in the BAT; cmd.exe is not available on Linux.
        code = re.search(r'"%PY_RUN%" -c "([^"\n]+)" "%CD%\\requirements.txt"', script).group(1)
        installed = importlib.metadata.version('qrcode')
        with tempfile.TemporaryDirectory() as directory:
            requirements = Path(directory) / 'requirements.txt'
            for contents, expected in ((f'qrcode=={installed}\n', 0), ('qrcode>=9999\n', 1),
                                       ('safety-nonexistent-audit-package==1\n', 1)):
                requirements.write_text(contents)
                result = subprocess.run([sys.executable, '-c', code, str(requirements)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
        self.assertIn('pywebpush,qrcode,openpyxl', script)


if __name__ == '__main__':
    unittest.main()
