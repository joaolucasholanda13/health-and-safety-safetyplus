import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.database import configure_sqlite_foreign_keys
from app.repair_integrity import main, repair_orphan_notifications


class SQLiteIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='safety-integrity-test-')
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / 'test.db'

    def seed_legacy_database(self, *, wal=False):
        with contextlib.closing(sqlite3.connect(self.database)) as connection:
            if wal:
                connection.execute('PRAGMA journal_mode=WAL')
            connection.executescript('''
                CREATE TABLE users(id INTEGER PRIMARY KEY);
                CREATE TABLE documents(id INTEGER PRIMARY KEY, created_by INTEGER REFERENCES users(id));
                CREATE TABLE notifications(id INTEGER PRIMARY KEY,
                    recipient_user_id INTEGER REFERENCES users(id),
                    document_id INTEGER REFERENCES documents(id));
                INSERT INTO users VALUES(1);
                INSERT INTO documents VALUES(1,1),(2,999);
                INSERT INTO notifications VALUES(1,1,1),(2,999,1),(3,1,999);
            ''')

    def rows(self, table, database=None):
        with contextlib.closing(sqlite3.connect(database or self.database)) as connection:
            return connection.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()

    def test_every_new_connection_enforces_foreign_keys(self):
        engine = create_engine(f'sqlite:///{self.database}')
        self.addCleanup(engine.dispose)
        configure_sqlite_foreign_keys(engine)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE parent(id INTEGER PRIMARY KEY)'))
            connection.execute(text('CREATE TABLE child(id INTEGER REFERENCES parent(id))'))
        # Duas conexões físicas simultâneas, seguidas de outra após dispose.
        with engine.connect() as first, engine.connect() as second:
            for connection in (first, second):
                self.assertEqual(connection.execute(text('PRAGMA foreign_keys')).scalar(), 1)
                with self.assertRaises(IntegrityError):
                    connection.execute(text('INSERT INTO child VALUES(42)'))
                connection.rollback()
        engine.dispose()
        with engine.connect() as connection:
            self.assertEqual(connection.execute(text('PRAGMA foreign_keys')).scalar(), 1)

    def test_non_sqlite_dialect_is_untouched(self):
        class OtherEngine:
            class dialect:
                name = 'postgresql'
        with patch('app.database.event.listen') as listen:
            configure_sqlite_foreign_keys(OtherEngine())
            listen.assert_not_called()

    def test_repair_preserves_valid_rows_and_backs_up_all_original_rows(self):
        self.seed_legacy_database()
        result = repair_orphan_notifications(self.database)
        self.assertEqual(result['removed_notifications'], 2)
        self.assertEqual(result['orphan_notification_ids'], [2, 3])
        self.assertEqual(self.rows('notifications'), [(1, 1, 1)])
        self.assertEqual(self.rows('documents'), [(1, 1), (2, 999)])
        self.assertEqual(self.rows('notifications', result['backup']),
                         [(1, 1, 1), (2, 999, 1), (3, 1, 999)])
        self.assertEqual(result['remaining_foreign_key_violations'], [
            {'table': 'documents', 'rowid': 2, 'parent': 'users', 'foreign_key': 0}])
        self.assertEqual(Path(result['backup']).stat().st_mode & 0o777, 0o600)
        repeated = repair_orphan_notifications(self.database)
        self.assertEqual(repeated['removed_notifications'], 0)
        self.assertIsNone(repeated['backup'])

    def test_wal_database_uses_consistent_sqlite_backup(self):
        self.seed_legacy_database(wal=True)
        result = repair_orphan_notifications(self.database)
        self.assertEqual(self.rows('notifications', result['backup']),
                         [(1, 1, 1), (2, 999, 1), (3, 1, 999)])
        with contextlib.closing(sqlite3.connect(result['backup'])) as backup:
            self.assertEqual(backup.execute('PRAGMA integrity_check').fetchall(), [('ok',)])

    def test_check_does_not_change_data_or_create_backup(self):
        self.seed_legacy_database()
        result = repair_orphan_notifications(self.database, dry_run=True)
        self.assertEqual(result['orphan_notification_ids'], [2, 3])
        self.assertEqual(result['removed_notifications'], 0)
        self.assertEqual(len(self.rows('notifications')), 3)
        self.assertFalse((self.database.parent / 'backups').exists())

    def test_failed_backup_prevents_deletion(self):
        self.seed_legacy_database()
        with patch('app.repair_integrity._backup_locked_database', side_effect=OSError('backup indisponível')):
            with self.assertRaisesRegex(OSError, 'backup indisponível'):
                repair_orphan_notifications(self.database)
        self.assertEqual(len(self.rows('notifications')), 3)

    def test_missing_database_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            repair_orphan_notifications(self.database)
        self.assertFalse(self.database.exists())

    def test_cli_uses_configured_sqlite_database_and_reports_violations(self):
        self.seed_legacy_database()
        output = io.StringIO()
        with patch.dict(os.environ, {'DATABASE_URL': f'sqlite:///{self.database}'}):
            with contextlib.redirect_stdout(output):
                status = main(['--check'])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())['orphan_notification_ids'], [2, 3])

    def test_cli_rejects_postgresql_without_connecting(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://invalid/test'}):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main([])
        self.assertEqual(error.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
