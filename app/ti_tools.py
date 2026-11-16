"""Ferramentas do DEV: backup/restauração e configurações globais.

O backup é lógico (tabelas em JSON + arquivos), então funciona igual em SQLite
e PostgreSQL. A restauração sempre grava antes um backup de segurança.
"""
from __future__ import annotations
import json
import base64
import os
import secrets
import tempfile
import shutil
import time
import zipfile
from datetime import datetime, date
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, LargeBinary, MetaData, text, insert, delete, select
from .database import Document, User

FILE_DIRS = ('pdfs', 'signatures', 'evidence', 'custom_docs', 'avatars', 'safety_moments')
FILE_NAMES = ('system_settings.json', 'notification_preferences.json', 'releases.json',
              'releases_overrides.json', 'external_resources.json', 'push_vapid_private.pem')
DOCUMENT_FILE_DIRS = ('pdfs', 'signatures', 'evidence')
SETTINGS_FILE = 'system_settings.json'
BACKUP_DIR = 'backups'


# ---------------------------------------------------------------- configurações
def load_settings(storage: Path) -> dict:
    try:
        data = json.loads((storage / SETTINGS_FILE).read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_settings(storage: Path, data: dict) -> None:
    path = storage / SETTINGS_FILE
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)


# ---------------------------------------------------------------- serialização
def _enc(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {'__safetyplus_bytes__': base64.b64encode(bytes(value)).decode('ascii')}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _dec(column, value: Any) -> Any:
    if isinstance(column.type, LargeBinary) and isinstance(value, dict) and '__safetyplus_bytes__' in value:
        return base64.b64decode(value['__safetyplus_bytes__'], validate=True)
    if value is not None and isinstance(column.type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value)
    return value


def _rows(conn, table, where=None) -> list[dict]:
    q = select(table)
    if where is not None:
        q = q.where(where)
    return [{k: _enc(v) for k, v in dict(r._mapping).items()} for r in conn.execute(q)]


def _add_dir(zf: zipfile.ZipFile, storage: Path, name: str) -> None:
    base = storage / name
    if not base.is_dir():
        return
    for p in base.rglob('*'):
        if p.is_file() and storage.resolve() in p.resolve().parents:
            zf.write(p, f'files/{name}/{p.relative_to(base).as_posix()}')


def _backup_tables(conn):
    """Inclui também tabelas criadas por SQL direto, como o suporte."""
    metadata = MetaData()
    metadata.reflect(bind=conn)
    return list(metadata.sorted_tables)


def _file_relative(value: Any, *, document: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    rel = value.replace('\\', '/')
    parts = rel.split('/')
    if not rel or any(p in {'', '.', '..'} for p in parts):
        return None
    directories = DOCUMENT_FILE_DIRS if document else FILE_DIRS
    if len(parts) > 1 and parts[0] in directories:
        return rel
    if not document and rel in FILE_NAMES:
        return rel
    return None


def _document_files(doc: dict) -> set[str]:
    paths: set[str] = set()
    def visit(value):
        if isinstance(value, dict):
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
        else:
            rel = _file_relative(value, document=True)
            if rel: paths.add(rel)
    visit(doc.get('pdf_path'))
    try: visit(json.loads(doc.get('data_json') or '{}'))
    except (ValueError, TypeError): pass
    return paths


def _remap_document_files(doc: dict, mapping: dict[str, str]) -> dict:
    def visit(value):
        if isinstance(value, dict): return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list): return [visit(v) for v in value]
        rel = _file_relative(value, document=True)
        return mapping.get(rel, value) if rel else value
    result = dict(doc)
    result['pdf_path'] = visit(doc.get('pdf_path'))
    try:
        result['data_json'] = json.dumps(visit(json.loads(doc.get('data_json') or '{}')), ensure_ascii=False)
    except (ValueError, TypeError): pass
    return result


def _new_backup_path(storage: Path, label: str) -> Path:
    folder = storage / BACKUP_DIR
    folder.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f'backup_{label}_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}_', suffix='.zip', dir=folder)
    os.close(fd)
    return Path(name)


# ---------------------------------------------------------------- backup
def backup_full(engine, storage: Path, label: str = 'completo') -> Path:
    out = _new_backup_path(storage, label)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf, engine.connect() as conn:
        # Uma única fotografia lógica das tabelas durante a exportação.
        if engine.dialect.name == 'postgresql':
            conn = conn.execution_options(isolation_level='REPEATABLE READ')
        elif engine.dialect.name == 'sqlite':
            conn.exec_driver_sql('BEGIN')
        tables = {t.name: _rows(conn, t) for t in _backup_tables(conn)}
        zf.writestr('manifest.json', json.dumps({'kind': 'full', 'format_version': 2, 'created_at': datetime.now().isoformat(), 'tables': {k: len(v) for k, v in tables.items()}}, ensure_ascii=False))
        zf.writestr('db.json', json.dumps(tables, ensure_ascii=False))
        for name in FILE_DIRS:
            _add_dir(zf, storage, name)
        for name in FILE_NAMES:
            path = storage / name
            if path.is_file() and storage.resolve() in path.resolve().parents:
                zf.write(path, f'files/{name}')
    return out


def backup_user(engine, storage: Path, user_id: int) -> Path:
    out = _new_backup_path(storage, f'usuario{user_id}')
    docs_t = Document.__table__
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf, engine.connect() as conn:
        user = conn.execute(select(User.__table__.c.username, User.__table__.c.full_name).where(User.__table__.c.id == user_id)).first()
        docs = _rows(conn, docs_t, docs_t.c.created_by == user_id)
        zf.writestr('manifest.json', json.dumps({'kind': 'user', 'format_version': 2, 'created_at': datetime.now().isoformat(), 'username': user[0] if user else '', 'documents': len(docs)}, ensure_ascii=False))
        zf.writestr('documents.json', json.dumps(docs, ensure_ascii=False))
        for rel in sorted(set().union(*(_document_files(d) for d in docs))):
            p = (storage / rel).resolve()
            if p.is_file() and storage.resolve() in p.parents:
                zf.write(p, f'files/{rel}')
    return out


# ---------------------------------------------------------------- restauração
def _safe_extract_files(zf: zipfile.ZipFile, storage: Path, mapping: dict[str, str] | None = None) -> int:
    count = 0
    root = storage.resolve()
    for info in zf.infolist():
        name = info.filename
        if info.is_dir() or not name.startswith('files/'):
            continue
        rel = _file_relative(name[len('files/'):])
        if rel is None or (mapping is not None and rel not in mapping):
            continue
        target = _file_relative(mapping[rel]) if mapping is not None else rel
        if target is None:
            continue
        dest = (storage / target).resolve()
        if root not in dest.parents:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(dest, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        if dest.name == 'push_vapid_private.pem':
            os.chmod(dest, 0o600)
        count += 1
    return count


def read_manifest(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read('manifest.json'))


def _install_restored_files(staged: Path, storage: Path, previous: Path, installed: list) -> None:
    for source in staged.rglob('*'):
        if not source.is_file():
            continue
        rel = source.relative_to(staged)
        dest = storage / rel
        if (storage.resolve() not in dest.resolve().parents or dest.is_symlink()
                or (dest.exists() and not dest.is_file())):
            raise ValueError('Destino de arquivo inválido na restauração.')
        dest.parent.mkdir(parents=True, exist_ok=True)
        old = previous / rel if dest.exists() else None
        if old is not None:
            old.parent.mkdir(parents=True, exist_ok=True)
            os.replace(dest, old)
        installed.append((dest, old))
        os.replace(source, dest)


def _undo_restored_files(installed: list) -> None:
    for dest, old in reversed(installed):
        dest.unlink(missing_ok=True)
        if old is not None:
            os.replace(old, dest)


def restore_full(engine, storage: Path, zip_path: Path, keep_user: dict | None) -> dict:
    """Substitui todo o banco e os arquivos pelo conteúdo do backup.

    `keep_user` é a conta DEV que está executando a restauração; ela é
    recriada se o backup não a contiver, para ninguém ficar sem acesso.
    """
    safety = backup_full(engine, storage, 'antes_restaurar')
    keep_user_id = None
    installed = []
    with zipfile.ZipFile(zip_path) as zf, tempfile.TemporaryDirectory(prefix='.restore_', dir=storage) as temporary:
        manifest = json.loads(zf.read('manifest.json'))
        if manifest.get('kind') != 'full':
            raise ValueError('Este arquivo não é um backup completo.')
        data = json.loads(zf.read('db.json'))
        if not isinstance(data, dict):
            raise ValueError('Conteúdo do banco inválido no backup.')
        if zf.testzip() is not None:
            raise ValueError('O backup contém um arquivo corrompido.')
        staged = Path(temporary) / 'new'
        staged.mkdir()
        files = _safe_extract_files(zf, staged)
        session_cutoff = time.time()
        settings = load_settings(staged) if (staged / SETTINGS_FILE).exists() else load_settings(storage)
        settings['force_logout'] = {'all': session_cutoff, 'users': {}}
        save_settings(staged, settings)
        try:
            with engine.begin() as conn:
                tables = _backup_tables(conn)
                unknown = set(data) - {t.name for t in tables}
                if unknown:
                    raise ValueError('Atualize/inicie a aplicação antes de restaurar estas tabelas: ' + ', '.join(sorted(unknown)))
                # Não associa chamados atuais a usuários antigos com o mesmo ID.
                for table in tables:
                    if table.name not in data and conn.execute(select(table).limit(1)).first() is not None:
                        raise ValueError(f'O backup antigo não inclui a tabela {table.name}, que contém dados atuais. A restauração foi cancelada para preservá-los.')
                tables = [t for t in tables if t.name in data]
                decoded = {}
                for t in tables:
                    cols = {c.name: c for c in t.columns}
                    decoded[t.name] = [{k: _dec(cols[k], v) for k, v in r.items() if k in cols} for r in (data[t.name] or [])]
                for t in reversed(tables):
                    conn.execute(delete(t))
                for t in tables:
                    rows = decoded[t.name]
                    if rows:
                        conn.execute(insert(t), rows)
                ut = User.__table__
                if keep_user:
                    keep_user_id = conn.execute(select(ut.c.id).where(ut.c.username == keep_user['username'])).scalar()
                    if keep_user_id is None:
                        row = dict(keep_user)
                        if conn.execute(select(ut.c.id).where(ut.c.id == row['id'])).first():
                            row['id'] = max(conn.execute(select(ut.c.id)).scalars(), default=0) + 1
                        result = conn.execute(insert(ut), [{k: _dec(ut.c[k], v) for k, v in row.items() if k in ut.c}])
                        keep_user_id = result.inserted_primary_key[0]
                    else:
                        # Mantém as credenciais/perfil da conta que recupera o sistema.
                        values = {k: _dec(ut.c[k], v) for k, v in keep_user.items() if k in ut.c and k != 'id'}
                        conn.execute(ut.update().where(ut.c.id == keep_user_id).values(**values))
                if engine.dialect.name == 'postgresql':
                    for t in tables:
                        if 'id' in t.c:
                            quoted = conn.dialect.identifier_preparer.quote(t.name)
                            sequence = conn.execute(text('SELECT pg_get_serial_sequence(:table_name, :column_name)'), {'table_name': quoted, 'column_name': 'id'}).scalar()
                            if sequence:
                                maximum = conn.execute(select(t.c.id).order_by(t.c.id.desc()).limit(1)).scalar()
                                conn.execute(text('SELECT setval(CAST(:sequence AS regclass), :value, :called)'), {'sequence': sequence, 'value': maximum or 1, 'called': maximum is not None})
                _install_restored_files(staged, storage, Path(temporary) / 'previous', installed)
        except Exception:
            _undo_restored_files(installed)
            raise
    _LOGOUT_CACHE['t'] = 0.0
    _MAINT_CACHE['t'] = 0.0
    return {'tables': {k: len(v) for k, v in data.items()}, 'files': files, 'safety': safety.name,
            'keep_user_id': keep_user_id, 'session_cutoff': session_cutoff}


def wipe_all(engine, storage: Path, keep_user_id: int) -> dict:
    """Apaga TODOS os dados (registros e arquivos), mantendo só a conta DEV
    que executa a ação. Gera um backup completo antes (em backups/)."""
    safety = backup_full(engine, storage, 'antes_apagar_tudo')
    ut = User.__table__
    removed = {}
    with engine.begin() as conn:
        for t in reversed(_backup_tables(conn)):
            if t.name == ut.name:
                res = conn.execute(delete(t).where(ut.c.id != keep_user_id))
            else:
                res = conn.execute(delete(t))
            removed[t.name] = res.rowcount
    files = 0
    for name in FILE_DIRS:
        base = storage / name
        if base.is_dir():
            for p in base.rglob('*'):
                if p.is_file():
                    try:
                        p.unlink(); files += 1
                    except OSError:
                        pass
    return {'tables': removed, 'files': files, 'safety': safety.name}


@contextmanager
def _user_restore_transaction(engine, restored_files):
    try:
        with engine.begin() as conn:
            yield conn
    except Exception:
        # Inclui falhas de COMMIT, além das falhas durante inserção/extração.
        for path in restored_files:
            path.unlink(missing_ok=True)
        raise


def restore_user(engine, storage: Path, zip_path: Path, target_user_id: int) -> dict:
    """Importa os documentos de um backup por usuário que ainda não existem (por código)."""
    safety = backup_full(engine, storage, 'antes_restaurar')
    docs_t = Document.__table__
    with zipfile.ZipFile(zip_path) as zf:
        manifest = json.loads(zf.read('manifest.json'))
        if manifest.get('kind') != 'user':
            raise ValueError('Este arquivo não é um backup de usuário.')
        docs = json.loads(zf.read('documents.json'))
        if not isinstance(docs, list):
            raise ValueError('Lista de documentos inválida no backup.')
        if zf.testzip() is not None:
            raise ValueError('O backup contém um arquivo corrompido.')
        added = skipped = 0
        mapping: dict[str, str] = {}
        pending = []
        available = {i.filename[len('files/'):] for i in zf.infolist() if i.filename.startswith('files/') and not i.is_dir()}
        missing = set()
        restored_files = []
        with _user_restore_transaction(engine, restored_files) as conn:
            if not conn.execute(select(User.id).where(User.id == target_user_id)).first():
                raise ValueError('Usuário de destino não encontrado.')
            existing = {r[0] for r in conn.execute(select(docs_t.c.code))}
            for d in docs:
                if d.get('code') in existing:
                    skipped += 1
                    continue
                existing.add(d.get('code'))
                pending.append(d)
            needed = set().union(*(_document_files(d) for d in pending))
            for rel in sorted(needed):
                if rel not in available:
                    missing.add(rel)
                    continue
                # Sempre reserva caminho novo: nunca altera anexos de outro documento.
                original = Path(rel)
                target = original.with_name(f'restaurado_{secrets.token_hex(12)}{original.suffix}').as_posix()
                dest = (storage / target).resolve()
                if storage.resolve() not in dest.parents:
                    raise ValueError('Destino de arquivo inválido no backup.')
                if dest.exists():
                    raise ValueError('Colisão no destino de restauração. Tente novamente.')
                mapping[rel] = target
            try:
                # Extrai antes de inserir: falhas de arquivo não deixam documentos importados.
                restored_files.extend(storage / target for target in mapping.values())
                files = _safe_extract_files(zf, storage, mapping)
                for d in pending:
                    d = _remap_document_files(d, mapping)
                    row = {k: _dec(docs_t.c[k], v) for k, v in d.items() if k in docs_t.c and k != 'id'}
                    row['created_by'] = target_user_id
                    conn.execute(insert(docs_t), [row])
                    added += 1
            except Exception:
                for path in restored_files:
                    path.unlink(missing_ok=True)
                raise
    return {'added': added, 'skipped': skipped, 'files': files, 'missing_files': len(missing), 'safety': safety.name}


def list_backups(storage: Path) -> list[dict]:
    folder = storage / BACKUP_DIR
    if not folder.is_dir():
        return []
    rows = [{'name': p.name, 'size': p.stat().st_size, 'mtime': datetime.fromtimestamp(p.stat().st_mtime)} for p in folder.glob('backup_*.zip')]
    return sorted(rows, key=lambda r: r['mtime'], reverse=True)[:30]


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.is_dir() else 0


# ---------------------------------------------------------------- saúde do sistema
def _cpu_times() -> tuple[int, int]:
    with open('/proc/stat') as fh:
        parts = [int(x) for x in fh.readline().split()[1:]]
    return sum(parts), parts[3] + (parts[4] if len(parts) > 4 else 0)


def _meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    with open('/proc/meminfo') as fh:
        for line in fh:
            k, _, v = line.partition(':')
            out[k] = int(v.split()[0]) * 1024
    return out


def system_stats(storage: Path) -> dict:
    """Disco, memória e processador do servidor (Linux, sem dependências extras)."""
    stats: dict[str, Any] = {'cpu_count': os.cpu_count() or 1}
    du = shutil.disk_usage(storage)
    stats['disk'] = {'total': du.total, 'used': du.used, 'free': du.free, 'percent': round(du.used / du.total * 100, 1) if du.total else 0}
    try:
        t1, i1 = _cpu_times()
        time.sleep(0.25)
        t2, i2 = _cpu_times()
        stats['cpu_percent'] = round((1 - (i2 - i1) / (t2 - t1)) * 100, 1) if t2 > t1 else 0.0
    except OSError:
        stats['cpu_percent'] = None
    try:
        stats['load'] = [round(x, 2) for x in os.getloadavg()]
    except OSError:
        stats['load'] = None
    try:
        m = _meminfo()
        total, avail = m['MemTotal'], m.get('MemAvailable', m.get('MemFree', 0))
        stats['memory'] = {'total': total, 'used': total - avail, 'free': avail, 'percent': round((total - avail) / total * 100, 1)}
        stats['swap'] = {'total': m.get('SwapTotal', 0), 'used': m.get('SwapTotal', 0) - m.get('SwapFree', 0)}
    except (OSError, KeyError):
        stats['memory'] = None
        stats['swap'] = None
    try:
        with open('/proc/self/status') as fh:
            rss = next((int(l.split()[1]) * 1024 for l in fh if l.startswith('VmRSS:')), 0)
        stats['process_rss'] = rss
    except OSError:
        stats['process_rss'] = None
    try:
        with open('/proc/uptime') as fh:
            stats['uptime'] = int(float(fh.read().split()[0]))
    except OSError:
        stats['uptime'] = None
    return stats


# ---------------------------------------------------------------- backup agendado
AUTO_DEFAULTS = {'enabled': False, 'interval_hours': 24, 'keep': 7, 'last_run': ''}


def auto_backup_config(storage: Path) -> dict:
    cfg = dict(AUTO_DEFAULTS)
    cfg.update(load_settings(storage).get('auto_backup') or {})
    return cfg


def prune_backups(storage: Path, prefix: str, keep: int) -> int:
    folder = storage / BACKUP_DIR
    files = sorted(folder.glob(f'{prefix}*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    for p in files[max(keep, 1):]:
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def run_auto_backup_if_due(engine, storage: Path) -> Path | None:
    cfg = auto_backup_config(storage)
    if not cfg['enabled']:
        return None
    try:
        last = datetime.fromisoformat(cfg['last_run']) if cfg['last_run'] else None
    except ValueError:
        last = None
    if last and (datetime.now() - last).total_seconds() < max(int(cfg['interval_hours']), 1) * 3600:
        return None
    path = backup_full(engine, storage, 'auto')
    st = load_settings(storage)
    st['auto_backup'] = {**cfg, 'last_run': datetime.now().isoformat()}
    save_settings(storage, st)
    prune_backups(storage, 'backup_auto_', int(cfg['keep']))
    return path


# ---------------------------------------------------------------- modo manutenção
_MAINT_CACHE: dict[str, Any] = {'t': 0.0, 'v': {'on': False, 'message': ''}}


def maintenance_state(storage: Path) -> dict:
    """Estado da manutenção: modo manual ligado OU janela agendada em andamento."""
    if time.time() - _MAINT_CACHE['t'] > 3:
        cfg = load_settings(storage)
        m = cfg.get('maintenance') or {}
        sch = cfg.get('maintenance_schedule') or None
        now = time.time()
        if sch and float(sch.get('end_ts') or 0) <= now:
            sch = None
        active = bool(sch and float(sch.get('start_ts') or 0) <= now)
        message = str(m.get('message') or '')
        if not m.get('on') and active:
            message = str(sch.get('message') or '')
            if sch.get('end_label'):
                message = (message + ' ' if message else '') + 'Previsão de retorno: ' + str(sch['end_label']) + '.'
        _MAINT_CACHE.update(t=time.time(), v={'on': bool(m.get('on')) or active, 'message': message,
                                              'schedule': sch, 'scheduled_active': active})
    return _MAINT_CACHE['v']


def set_maintenance(storage: Path, on: bool, message: str) -> None:
    st = load_settings(storage)
    st['maintenance'] = {'on': on, 'message': message}
    save_settings(storage, st)
    _MAINT_CACHE['t'] = 0.0


def set_maintenance_schedule(storage: Path, schedule: dict | None) -> None:
    st = load_settings(storage)
    if schedule:
        st['maintenance_schedule'] = schedule
    else:
        st.pop('maintenance_schedule', None)
    save_settings(storage, st)
    _MAINT_CACHE['t'] = 0.0


# ---------------------------------------------------------------- integridade
def integrity_report(engine, storage: Path) -> dict:
    """Procura inconsistências. Retorna listas de problemas por categoria."""
    from .database import Notification, UserScope, Participant, Company
    d, u = Document.__table__, User.__table__
    n, sc, pa, co = Notification.__table__, UserScope.__table__, Participant.__table__, Company.__table__
    rep: dict[str, list] = {}
    with engine.connect() as c:
        user_ids = {r[0] for r in c.execute(select(u.c.id))}
        doc_ids = set()
        no_pdf, bad_json, no_creator, referenced = [], [], [], set()
        for r in c.execute(select(d.c.id, d.c.code, d.c.status, d.c.pdf_path, d.c.created_by, d.c.data_json)):
            doc_ids.add(r.id)
            rel = (r.pdf_path or '').replace('\\', '/').lstrip('/')
            if rel:
                referenced.add(rel)
            if r.status == 'Finalizada' and not (rel and (storage / rel).is_file()):
                no_pdf.append({'id': r.id, 'code': r.code})
            try:
                if not isinstance(json.loads(r.data_json or '{}'), dict):
                    raise ValueError
            except ValueError:
                bad_json.append({'id': r.id, 'code': r.code})
            if r.created_by not in user_ids:
                no_creator.append({'id': r.id, 'code': r.code})
        rep['docs_sem_pdf'] = no_pdf
        rep['docs_json_invalido'] = bad_json
        rep['docs_sem_criador'] = no_creator
        rep['notificacoes_orfas'] = [{'id': r.id} for r in c.execute(select(n.c.id, n.c.document_id, n.c.recipient_user_id)) if r.document_id not in doc_ids or r.recipient_user_id not in user_ids]
        rep['escopos_orfaos'] = [{'id': r.id} for r in c.execute(select(sc.c.id, sc.c.user_id)) if r.user_id not in user_ids]
        company_ids = {r[0] for r in c.execute(select(co.c.id))}
        rep['colaboradores_sem_empresa'] = [{'id': r.id, 'name': r.full_name} for r in c.execute(select(pa.c.id, pa.c.company_id, pa.c.full_name)) if r.company_id not in company_ids]
    orphans = []
    pdfs = storage / 'pdfs'
    if pdfs.is_dir():
        for p in pdfs.rglob('*'):
            rel = p.relative_to(storage).as_posix()
            if p.is_file() and rel not in referenced:
                orphans.append({'path': rel, 'size': p.stat().st_size})
    rep['pdfs_orfaos'] = orphans
    return rep


def fix_orphans(engine, storage: Path, new_owner_id: int) -> dict:
    """Corrige o que é seguro: apaga notificações/escopos órfãos, move PDFs órfãos
    para storage/quarentena e reatribui documentos sem criador."""
    from .database import Notification, UserScope
    rep = integrity_report(engine, storage)
    n, sc, d = Notification.__table__, UserScope.__table__, Document.__table__
    done = {'notificacoes': 0, 'escopos': 0, 'docs_reatribuidos': 0, 'pdfs_quarentena': 0}
    with engine.begin() as c:
        for r in rep['notificacoes_orfas']:
            c.execute(delete(n).where(n.c.id == r['id']))
            done['notificacoes'] += 1
        for r in rep['escopos_orfaos']:
            c.execute(delete(sc).where(sc.c.id == r['id']))
            done['escopos'] += 1
        for r in rep['docs_sem_criador']:
            c.execute(d.update().where(d.c.id == r['id']).values(created_by=new_owner_id))
            done['docs_reatribuidos'] += 1
    quarantine = storage / 'quarentena'
    for r in rep['pdfs_orfaos']:
        dest = quarantine / r['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(storage / r['path']), str(dest))
        done['pdfs_quarentena'] += 1
    return done


# ---------------------------------------------------------------- forçar logout
STORAGE: Path | None = None
_LOGOUT_CACHE: dict[str, Any] = {'t': 0.0, 'v': {}}


def configure(storage: Path) -> None:
    global STORAGE
    STORAGE = storage


def _logout_cutoffs() -> dict:
    if STORAGE is None:
        return {}
    if time.time() - _LOGOUT_CACHE['t'] > 2:
        _LOGOUT_CACHE.update(t=time.time(), v=load_settings(STORAGE).get('force_logout') or {})
    return _LOGOUT_CACHE['v']


def session_revoked(user_id: int, session_time: float) -> bool:
    """True se a sessão (criada em session_time) foi invalidada pelo DEV"""
    c = _logout_cutoffs()
    cutoff = max(float(c.get('all') or 0), float((c.get('users') or {}).get(str(user_id)) or 0))
    return session_time < cutoff


def force_logout(storage: Path, user_id: int | None) -> float:
    """Invalida as sessões de um usuário (ou de todos, se user_id for None)."""
    st = load_settings(storage)
    fl = st.setdefault('force_logout', {})
    now_ts = time.time()
    if user_id is None:
        fl['all'] = now_ts
    else:
        fl.setdefault('users', {})[str(user_id)] = now_ts
    save_settings(storage, st)
    _LOGOUT_CACHE['t'] = 0.0
    return now_ts


def robot_status() -> dict:
    """Lê somente o resumo público do supervisor, nunca arquivos de backup."""
    path = Path(os.getenv('MAINTENANCE_STATUS_FILE', '/app/maintenance-status/status.json'))
    result = {'available': False, 'fresh': False, 'data': {}, 'label': 'Não conectado'}
    try:
        if path.stat().st_size > 128_000:
            return result
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or data.get('schema') != 1:
            return result
        age = time.time() - float(data['updated_at'])
        result.update(available=True, fresh=0 <= age <= 180, data=data)
        result['label'] = ('Ativo' if data.get('monitor_timer_active') and result['fresh']
                           else 'Sem atualização recente' if not result['fresh']
                           else 'Agendamento desativado')
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return result
