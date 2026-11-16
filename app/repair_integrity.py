"""Repara notificações órfãs em SQLite, preservando um backup consistente.

Uso: python -m app.repair_integrity [--database caminho.db] [--check]
Sem --database, utiliza DATABASE_URL (ou o banco SQLite local padrão).
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid


_ORPHAN_PREDICATE = """NOT EXISTS (
    SELECT 1 FROM users WHERE users.id = notifications.recipient_user_id
) OR NOT EXISTS (
    SELECT 1 FROM documents WHERE documents.id = notifications.document_id
)"""


def _foreign_key_violations(connection: sqlite3.Connection) -> list[dict]:
    return [dict(zip(('table', 'rowid', 'parent', 'foreign_key'), row))
            for row in connection.execute('PRAGMA foreign_key_check')]


def _backup_locked_database(database: Path, folder: Path) -> Path:
    """O chamador mantém BEGIN IMMEDIATE para impedir escritas durante a cópia."""
    folder.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix='.integrity_', suffix='.tmp', dir=folder)
    os.close(fd)
    temporary = Path(temporary_name)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    destination = folder / f'antes_corrigir_notificacoes_{stamp}_{uuid.uuid4().hex[:8]}.db'
    try:
        # Uma segunda conexão lê o estado anterior à exclusão. Fazer backup na
        # própria conexão com transação de escrita aberta bloquearia a operação.
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(temporary)) as snapshot:
                source.backup(snapshot)
                if snapshot.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise RuntimeError('O backup não passou na verificação de integridade.')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def repair_orphan_notifications(database: Path, backup_dir: Path | None = None,
                                *, dry_run: bool = False) -> dict:
    """Remove apenas notificações sem usuário/documento, numa única transação.

    Nenhuma outra violação é corrigida automaticamente; todas são devolvidas no
    resultado. Se não há notificações órfãs, não cria backup nem modifica dados.
    """
    database = Path(database).expanduser().resolve(strict=True)
    if not database.is_file():
        raise ValueError('Informe um arquivo SQLite existente.')
    with closing(sqlite3.connect(database.as_uri() + '?mode=rw', uri=True,
                                timeout=30, isolation_level=None)) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('BEGIN' if dry_run else 'BEGIN IMMEDIATE')
        try:
            if connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('O banco não passou na verificação de integridade; nenhuma alteração foi feita.')
            ids = [row[0] for row in connection.execute(
                f'SELECT id FROM notifications WHERE {_ORPHAN_PREDICATE} ORDER BY id')]
            backup = None
            removed = 0
            if ids and not dry_run:
                folder = Path(backup_dir).expanduser().resolve() if backup_dir else database.parent / 'backups'
                backup = _backup_locked_database(database, folder)
                removed = connection.execute(f'DELETE FROM notifications WHERE {_ORPHAN_PREDICATE}').rowcount
            violations = _foreign_key_violations(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return {
        'database': str(database),
        'orphan_notification_ids': ids,
        'removed_notifications': removed,
        'backup': str(backup) if backup else None,
        'remaining_foreign_key_violations': violations,
        'dry_run': dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, help='Caminho do arquivo SQLite existente.')
    parser.add_argument('--backup-dir', type=Path, help='Diretório para o backup anterior à correção.')
    parser.add_argument('--check', action='store_true', help='Somente verificar, sem alterar dados nem criar backup.')
    args = parser.parse_args(argv)
    try:
        database = args.database
        if database is None:
            from sqlalchemy.engine import make_url
            url = make_url(os.getenv('DATABASE_URL', 'sqlite:///./storage/checklist_serena.db'))
            if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
                raise ValueError('Este comando requer um arquivo SQLite. Use --database para informar o caminho.')
            database = Path(url.database)
        result = repair_orphan_notifications(database, args.backup_dir, dry_run=args.check)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        parser.exit(1, f'Erro: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['remaining_foreign_key_violations'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
