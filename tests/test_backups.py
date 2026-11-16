import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, event, insert, select, text

from app.database import Base, Document, User
from app import ti_tools


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.storage = self.root / 'storage'
        self.storage.mkdir()
        self.engine = self.new_engine('source')
        with self.engine.begin() as c:
            c.execute(insert(User), [{'id': 1, 'username': 'audit', 'password_hash': 'test', 'role': 'DEV'}])

    def new_engine(self, name):
        engine = create_engine(f'sqlite:///{self.root / name}.db')
        self.addCleanup(engine.dispose)
        @event.listens_for(engine, 'connect')
        def enforce_fk(conn, _):
            conn.execute('PRAGMA foreign_keys=ON')
        Base.metadata.create_all(engine)
        with engine.begin() as c:
            c.execute(text('CREATE TABLE support_tickets (id INTEGER PRIMARY KEY, user_id INTEGER, subject TEXT, created_at TIMESTAMP)'))
            c.execute(text('CREATE TABLE support_images (ticket_id INTEGER PRIMARY KEY, media_type VARCHAR(32), image_data BLOB NOT NULL)'))
        return engine

    def file(self, rel, content=b'audit'):
        path = self.storage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def doc(self, code='APR-2026-0001', pdf='pdfs/a.pdf', data=None):
        with self.engine.begin() as c:
            c.execute(insert(Document), [{'code': code, 'kind': 'apr', 'title': 'Audit', 'created_by': 1, 'pdf_path': pdf, 'data_json': json.dumps(data or {})}])

    def rows(self, engine, table):
        with engine.connect() as c:
            return [dict(r) for r in c.execute(select(table)).mappings()]

    def test_full_roundtrip_includes_support_binary_and_persistent_files(self):
        payload = b'\x89PNG\x00\xff\x80image'
        self.doc()
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO support_tickets VALUES(8,1,'audit','2026-11-10 10:30:00')"))
            c.execute(text('INSERT INTO support_images VALUES(8, :type, :image)'), {'type': 'image/png', 'image': payload})
        for rel in ['pdfs/a.pdf', 'signatures/a.png', 'evidence/a.png', 'avatars/1.jpg', 'custom_docs/registry.json', 'safety_moments/manifest.json', 'safety_moments/upload.pdf', *ti_tools.FILE_NAMES]:
            self.file(rel, b'{"audit_setting": true}' if rel == ti_tools.SETTINGS_FILE else rel.encode())
        archive = ti_tools.backup_full(self.engine, self.storage)
        target = self.new_engine('target')
        target_storage = self.root / 'restored'
        target_storage.mkdir()
        with target.begin() as c:
            c.execute(text("INSERT INTO support_tickets VALUES(99,99,'outdated',NULL)"))
            c.execute(text("INSERT INTO support_images VALUES(99,'old',X'00')"))
        result = ti_tools.restore_full(target, target_storage, archive, None)
        self.assertEqual(result['tables']['support_images'], 1)
        with target.connect() as c:
            self.assertEqual(c.execute(text('SELECT image_data FROM support_images')).scalar_one(), payload)
            self.assertEqual(c.execute(text('SELECT id FROM support_tickets')).scalar_one(), 8)
        self.assertEqual(self.rows(self.engine, Document), self.rows(target, Document))
        for rel in ['pdfs/a.pdf', 'signatures/a.png', 'evidence/a.png', 'avatars/1.jpg', 'custom_docs/registry.json', 'safety_moments/manifest.json', 'safety_moments/upload.pdf', *ti_tools.FILE_NAMES]:
            if rel == ti_tools.SETTINGS_FILE:
                settings = json.loads((target_storage / rel).read_text())
                self.assertTrue(settings['audit_setting'])
                self.assertEqual(settings['force_logout']['all'], result['session_cutoff'])
            else:
                self.assertEqual((target_storage / rel).read_bytes(), rel.encode())
        self.assertEqual((target_storage / 'push_vapid_private.pem').stat().st_mode & 0o777, 0o600)

    def test_user_backup_includes_nested_signatures_and_evidence_only(self):
        self.doc(data={'workers': [{'signature_image': 'signatures/a.png', 'daily': ['signatures\\daily.png']}], 'photos': ['evidence/a.jpg'], 'bad': '../outside'})
        for rel in ['pdfs/a.pdf', 'signatures/a.png', 'signatures/daily.png', 'evidence/a.jpg', 'avatars/1.jpg', 'system_settings.json']:
            self.file(rel)
        archive = ti_tools.backup_user(self.engine, self.storage, 1)
        with zipfile.ZipFile(archive) as z:
            files = {n for n in z.namelist() if n.startswith('files/')}
        self.assertEqual(files, {'files/pdfs/a.pdf', 'files/signatures/a.png', 'files/signatures/daily.png', 'files/evidence/a.jpg'})

    def test_skipped_documents_do_not_extract_any_files(self):
        self.doc(data={'signature_image': 'signatures/a.png'})
        self.file('pdfs/a.pdf', b'old')
        self.file('signatures/a.png', b'old-signature')
        archive = ti_tools.backup_user(self.engine, self.storage, 1)
        self.file('pdfs/a.pdf', b'current')
        self.file('signatures/a.png', b'current-signature')
        result = ti_tools.restore_user(self.engine, self.storage, archive, 1)
        self.assertEqual((result['added'], result['skipped'], result['files']), (0, 1, 0))
        self.assertEqual((self.storage / 'pdfs/a.pdf').read_bytes(), b'current')
        self.assertEqual((self.storage / 'signatures/a.png').read_bytes(), b'current-signature')

    def test_import_remaps_collisions_and_nested_file_references(self):
        self.doc(data={'workers': [{'signature_image': 'signatures/a.png'}], 'photos': ['evidence/a.jpg']})
        for rel in ['pdfs/a.pdf', 'signatures/a.png', 'evidence/a.jpg']:
            self.file(rel, b'backup')
        archive = ti_tools.backup_user(self.engine, self.storage, 1)
        with self.engine.begin() as c:
            c.execute(Document.__table__.delete())
        for rel in ['pdfs/a.pdf', 'signatures/a.png', 'evidence/a.jpg']:
            self.file(rel, b'current')
        # Arquivo alheio e traversal não devem ser extraídos pelo importador.
        with zipfile.ZipFile(archive, 'a') as z:
            z.writestr('files/avatars/1.jpg', b'unrelated')
            z.writestr('files/../outside.txt', b'invalid')
        result = ti_tools.restore_user(self.engine, self.storage, archive, 1)
        self.assertEqual((result['added'], result['files']), (1, 3))
        doc = self.rows(self.engine, Document)[0]
        data = json.loads(doc['data_json'])
        for rel in [doc['pdf_path'], data['workers'][0]['signature_image'], data['photos'][0]]:
            self.assertIn('restaurado_', rel)
            self.assertEqual((self.storage / rel).read_bytes(), b'backup')
        for rel in ['pdfs/a.pdf', 'signatures/a.png', 'evidence/a.jpg']:
            self.assertEqual((self.storage / rel).read_bytes(), b'current')
        self.assertFalse((self.storage / 'avatars/1.jpg').exists())
        self.assertFalse((self.root / 'outside.txt').exists())

    def test_user_insert_failure_rolls_back_files_and_documents(self):
        self.doc()
        self.file('pdfs/a.pdf')
        archive = ti_tools.backup_user(self.engine, self.storage, 1)
        with self.engine.begin() as c:
            c.execute(Document.__table__.delete())
        with zipfile.ZipFile(archive) as z:
            manifest = z.read('manifest.json')
            docs = json.loads(z.read('documents.json'))
        docs[0]['kind'] = None
        broken = self.root / 'broken.zip'
        with zipfile.ZipFile(broken, 'w') as z:
            z.writestr('manifest.json', manifest)
            z.writestr('documents.json', json.dumps(docs))
            z.writestr('files/pdfs/a.pdf', b'test')
        with self.assertRaises(Exception):
            ti_tools.restore_user(self.engine, self.storage, broken, 1)
        self.assertEqual(self.rows(self.engine, Document), [])
        self.assertEqual(list((self.storage / 'pdfs').glob('restaurado_*')), [])

    def test_full_restore_preserves_dev_on_id_collision(self):
        archive = ti_tools.backup_full(self.engine, self.storage)
        ti_tools.restore_full(self.engine, self.storage, archive, {'id': 1, 'username': 'other-dev', 'password_hash': 'other', 'role': 'DEV'})
        users = self.rows(self.engine, User)
        self.assertEqual({r['username'] for r in users}, {'audit', 'other-dev'})
        self.assertEqual(len({r['id'] for r in users}), 2)

    def test_full_restore_preserves_current_dev_credentials_and_revokes_sessions(self):
        self.file(ti_tools.SETTINGS_FILE, b'{"force_logout":{"all":0}}')
        archive = ti_tools.backup_full(self.engine, self.storage)
        result = ti_tools.restore_full(self.engine, self.storage, archive, {'id': 1, 'username': 'audit', 'password_hash': 'current-password', 'role': 'DEV', 'active': True})
        self.assertEqual(self.rows(self.engine, User)[0]['password_hash'], 'current-password')
        self.assertEqual(result['keep_user_id'], 1)
        cutoff = json.loads((self.storage / ti_tools.SETTINGS_FILE).read_text())['force_logout']['all']
        self.assertEqual(cutoff, result['session_cutoff'])
        self.assertGreater(cutoff, 0)

    def legacy_backup(self):
        archive = ti_tools.backup_full(self.engine, self.storage)
        with zipfile.ZipFile(archive) as z:
            data = json.loads(z.read('db.json'))
        data.pop('support_tickets')
        data.pop('support_images')
        legacy = self.root / 'legacy.zip'
        with zipfile.ZipFile(legacy, 'w') as z:
            z.writestr('manifest.json', json.dumps({'kind': 'full'}))
            z.writestr('db.json', json.dumps(data))
        return legacy

    def test_legacy_full_backup_restores_into_empty_support_tables(self):
        ti_tools.restore_full(self.engine, self.storage, self.legacy_backup(), None)
        self.assertEqual(len(self.rows(self.engine, User)), 1)

    def test_legacy_full_backup_refuses_to_reassign_existing_support(self):
        legacy = self.legacy_backup()
        with self.engine.begin() as c:
            c.execute(text("INSERT INTO support_tickets VALUES(9,1,'preserve',NULL)"))
            c.execute(text("UPDATE users SET username='current-account' WHERE id=1"))
        with self.assertRaisesRegex(ValueError, 'backup antigo'):
            ti_tools.restore_full(self.engine, self.storage, legacy, None)
        with self.engine.connect() as c:
            self.assertEqual(c.execute(text('SELECT subject FROM support_tickets')).scalar_one(), 'preserve')
            self.assertEqual(c.execute(text('SELECT username FROM users WHERE id=1')).scalar_one(), 'current-account')

    def test_full_extraction_failure_does_not_change_database(self):
        archive = ti_tools.backup_full(self.engine, self.storage)
        with self.engine.begin() as c:
            c.execute(text("UPDATE users SET username='current' WHERE id=1"))
        with patch.object(ti_tools, '_safe_extract_files', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                ti_tools.restore_full(self.engine, self.storage, archive, None)
        self.assertEqual(self.rows(self.engine, User)[0]['username'], 'current')

    def test_full_install_failure_rolls_back_files_and_database(self):
        self.file('pdfs/a.pdf', b'backup')
        self.file('signatures/a.png', b'backup')
        archive = ti_tools.backup_full(self.engine, self.storage)
        self.file('pdfs/a.pdf', b'current')
        self.file('signatures/a.png', b'current')
        with self.engine.begin() as c:
            c.execute(text("UPDATE users SET username='current' WHERE id=1"))
        real_replace = os.replace
        def fail_second_file(src, dst):
            if Path(src).name == 'a.png' and '/new/' in str(src):
                raise OSError('disk full')
            return real_replace(src, dst)
        with patch.object(ti_tools.os, 'replace', side_effect=fail_second_file):
            with self.assertRaises(OSError):
                ti_tools.restore_full(self.engine, self.storage, archive, None)
        self.assertEqual(self.rows(self.engine, User)[0]['username'], 'current')
        self.assertEqual((self.storage / 'pdfs/a.pdf').read_bytes(), b'current')
        self.assertEqual((self.storage / 'signatures/a.png').read_bytes(), b'current')

    def test_full_restore_does_not_replace_existing_directory_with_file(self):
        self.file('pdfs/a.pdf', b'backup')
        archive = ti_tools.backup_full(self.engine, self.storage)
        (self.storage / 'pdfs/a.pdf').unlink()
        self.file('pdfs/a.pdf/keep.txt', b'preserve')
        with self.assertRaises(ValueError):
            ti_tools.restore_full(self.engine, self.storage, archive, None)
        self.assertEqual((self.storage / 'pdfs/a.pdf/keep.txt').read_bytes(), b'preserve')

    def test_full_commit_failure_rolls_back_files_and_database(self):
        self.file('pdfs/a.pdf', b'backup')
        archive = ti_tools.backup_full(self.engine, self.storage)
        self.file('pdfs/a.pdf', b'current')
        def fail_commit(conn):
            raise OSError('commit failed')
        event.listen(self.engine, 'commit', fail_commit)
        try:
            with self.assertRaises(OSError):
                ti_tools.restore_full(self.engine, self.storage, archive, None)
        finally:
            event.remove(self.engine, 'commit', fail_commit)
        self.assertEqual((self.storage / 'pdfs/a.pdf').read_bytes(), b'current')

    def test_user_commit_failure_removes_restored_files(self):
        self.doc()
        self.file('pdfs/a.pdf')
        archive = ti_tools.backup_user(self.engine, self.storage, 1)
        with self.engine.begin() as c:
            c.execute(Document.__table__.delete())
        def fail_commit(conn):
            raise OSError('commit failed')
        event.listen(self.engine, 'commit', fail_commit)
        try:
            with self.assertRaises(OSError):
                ti_tools.restore_user(self.engine, self.storage, archive, 1)
        finally:
            event.remove(self.engine, 'commit', fail_commit)
        self.assertEqual(list((self.storage / 'pdfs').glob('restaurado_*')), [])

    def test_backup_does_not_follow_symlinks_outside_storage(self):
        outside = self.root / 'private.txt'
        outside.write_bytes(b'private')
        (self.storage / 'signatures').mkdir()
        (self.storage / 'signatures/leak.png').symlink_to(outside)
        archive = ti_tools.backup_full(self.engine, self.storage)
        with zipfile.ZipFile(archive) as z:
            self.assertNotIn('files/signatures/leak.png', z.namelist())


if __name__ == '__main__':
    unittest.main()
