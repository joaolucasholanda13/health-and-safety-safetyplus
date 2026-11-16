"""Regression tests for password changes, isolated from the real database."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PasswordSessionRegressionTest(unittest.TestCase):
    def test_password_session_routes(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), '--isolated'],
            cwd=ROOT, text=True, capture_output=True, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def _run_isolated_suite():
    import asyncio
    import time
    from unittest.mock import patch

    sys.path.insert(0, str(ROOT))
    with tempfile.TemporaryDirectory(prefix='safety-password-tests-') as folder:
        os.environ.update(
            DATABASE_URL=f'sqlite:///{folder}/tests.db', STORAGE_DIR=folder,
            APP_SECRET='isolated-password-test-secret', SECURE_COOKIES='false',
        )
        from starlette.datastructures import FormData, UploadFile
        from starlette.requests import Request
        from app import main as m, ti_tools
        from app.database import SessionLocal, User, Company
        from app.security import current_user, hash_password, verify_password

        class Scenarios(unittest.TestCase):
            def setUp(self):
                self.storage = Path(tempfile.mkdtemp(dir=folder))
                m.STORAGE_DIR = self.storage
                ti_tools.configure(self.storage)
                # configure() does not invalidate the cache used by other storage roots.
                ti_tools._LOGOUT_CACHE.update(t=0.0, v={})
                with SessionLocal() as db:
                    users = [
                        User(username=f'{self.id()}-{role}', full_name=role,
                             password_hash=hash_password('old-password-123'), role=role, active=True)
                        for role in ('Super Administrador', 'DEV', 'Usuário')
                    ]
                    db.add_all(users)
                    db.commit()
                    self.users = {u.role: u for u in users}

            def request(self, user=None, **fields):
                session = {'csrf_token': 'test-csrf'}
                if user:
                    session.update(user_id=user.id, t=time.time() - 60)
                request = Request({'type': 'http', 'method': 'POST', 'path': '/',
                                   'headers': [], 'session': session})
                request._form = FormData({'csrf_token': 'test-csrf', **fields})
                return request

            def call(self, route, request, *args):
                response = asyncio.run(route(request, *args))
                self.assertEqual(response.status_code, 303)
                return response

            def check_password(self, user, password='new-password-123'):
                with SessionLocal() as db:
                    self.assertTrue(verify_password(password, db.get(User, user.id).password_hash))

            def assert_revoked(self, request):
                self.assertIsNone(current_user(request))
                self.assertNotIn('user_id', request.session)

            def assert_login_with_new_password(self, user):
                request = self.request(username=user.username, password='new-password-123')
                self.call(m.login, request)
                self.assertEqual(request.session.get('user_id'), user.id)
                self.assertIsNotNone(current_user(request))

            def test_own_password_change_preserves_current_session(self):
                user = self.users['Usuário']
                other_session = self.request(user)
                request = self.request(user, current_password='old-password-123', new_password='new-password-123')
                self.call(m.account_password, request)
                self.check_password(user)
                self.assert_revoked(other_session)
                self.assertIsNotNone(current_user(request))
                cutoff = ti_tools.load_settings(self.storage)['force_logout']['users'][str(user.id)]
                self.assertEqual(request.session['t'], cutoff)
                self.assertLessEqual(request.session['t'], time.time())
                self.assert_login_with_new_password(user)

            def test_incorrect_current_password_keeps_sessions_and_password(self):
                user = self.users['Usuário']
                other_session = self.request(user)
                request = self.request(user, current_password='incorrect', new_password='new-password-123')
                self.call(m.account_password, request)
                self.check_password(user, 'old-password-123')
                self.assertIsNotNone(current_user(other_session))

            def test_admin_reset_revokes_target_but_keeps_actor(self):
                user, actor = self.users['Usuário'], self.users['Super Administrador']
                old_session = self.request(user)
                request = self.request(actor, role='Usuário', active='1', new_password='new-password-123')
                self.call(m.user_update, request, user.id)
                self.check_password(user)
                self.assert_revoked(old_session)
                self.assertIsNotNone(current_user(request))
                self.assert_login_with_new_password(user)

            def test_admin_self_reset_preserves_current_session(self):
                actor = self.users['Super Administrador']
                old_session = self.request(actor)
                request = self.request(actor, role=actor.role, active='1', new_password='new-password-123')
                self.call(m.user_update, request, actor.id)
                self.assert_revoked(old_session)
                self.assertIsNotNone(current_user(request))
                self.check_password(actor)

            def test_dev_reset_revokes_target_but_keeps_actor(self):
                user, actor = self.users['Usuário'], self.users['DEV']
                old_session = self.request(user)
                request = self.request(actor, role='Usuário', active='1', password='new-password-123')
                self.call(m.ti_user_update, request, user.id)
                self.assert_revoked(old_session)
                self.assertIsNotNone(current_user(request))
                self.check_password(user)
                self.assert_login_with_new_password(user)

            def test_dev_self_reset_preserves_current_session(self):
                actor = self.users['DEV']
                old_session = self.request(actor)
                request = self.request(actor, password='new-password-123')
                self.call(m.ti_user_update, request, actor.id)
                self.assert_revoked(old_session)
                self.assertIsNotNone(current_user(request))
                self.check_password(actor)

            def test_profile_update_without_password_keeps_target_session(self):
                user = self.users['Usuário']
                old_session = self.request(user)
                request = self.request(self.users['Super Administrador'], role='Usuário', active='1')
                self.call(m.user_update, request, user.id)
                self.assertIsNotNone(current_user(old_session))

            def test_excel_password_reset_revokes_target_session(self):
                from openpyxl import Workbook
                user = self.users['Usuário']
                with SessionLocal() as db:
                    company = Company(name=self.id(), active=True)
                    db.add(company)
                    db.commit()
                    company_id = company.id
                wb = Workbook()
                wb.active.append(['Nome completo', 'CPF', 'Login', 'Senha'])
                wb.active.append(['Participante teste', '52998224725', user.username, 'new-password-123'])
                content = tempfile.SpooledTemporaryFile(max_size=1024 * 1024)
                self.addCleanup(content.close)
                wb.save(content)
                content.seek(0)
                old_session = self.request(user)
                request = self.request(self.users['Super Administrador'], participants_file=UploadFile(content, filename='tests.xlsx'))
                self.call(m.participant_excel_import, request, company_id)
                self.check_password(user)
                self.assert_revoked(old_session)

            def test_cli_reset_revokes_existing_dev_session(self):
                from app.create_ti_user import main as create_dev
                user = self.users['DEV']
                old_session = self.request(user)
                with patch.object(sys, 'argv', ['create_ti_user', user.username]), patch.dict(
                    os.environ, STORAGE_DIR=str(self.storage), TI_PASSWORD='new-password-123',
                ):
                    create_dev()
                self.check_password(user)
                self.assert_revoked(old_session)

            def test_full_restore_renews_session_with_remapped_dev_id(self):
                actor = self.users['DEV']
                content = tempfile.SpooledTemporaryFile(max_size=1024)
                self.addCleanup(content.close)
                content.write(b'archive contents supplied by mock')
                content.seek(0)
                request = self.request(actor, file=UploadFile(content, filename='backup.zip'))
                request.session.update(view_cluster='old-cluster', stale='old-session-data')
                restored_id = actor.id + 10000
                result = {'tables': {'users': 1}, 'files': 1, 'safety': 'safety.zip',
                          'keep_user_id': restored_id, 'session_cutoff': time.time()}

                async def run_inline(function, *args, **kwargs):
                    return function(*args, **kwargs)

                with patch.object(ti_tools, 'read_manifest', return_value={'kind': 'full'}), patch.object(
                    ti_tools, 'restore_full', return_value=result,
                ) as restore, patch.object(m.asyncio, 'to_thread', side_effect=run_inline), patch.object(m, 'audit') as audit:
                    self.call(m.ti_backup_restore, request)
                restore.assert_called_once()
                self.assertEqual(request.session['user_id'], restored_id)
                self.assertEqual(request.session['t'], result['session_cutoff'])
                self.assertNotEqual(request.session['csrf_token'], 'test-csrf')
                self.assertNotIn('view_cluster', request.session)
                self.assertNotIn('stale', request.session)
                self.assertEqual(audit.call_args.args[:2], (restored_id, 'ti_restaurar_completo'))

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Scenarios))
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if '--isolated' in sys.argv:
        raise SystemExit(_run_isolated_suite())
    unittest.main()
