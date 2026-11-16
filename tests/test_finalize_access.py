"""Finalização e visualização por perfil, sempre com banco e arquivos temporários."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FinalizeAccessRegressionTests(unittest.TestCase):
    def test_finalize_access_routes(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), '--isolated'],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def _run_isolated_suite():
    import asyncio
    import base64
    import json
    import time

    sys.path.insert(0, str(ROOT))
    with tempfile.TemporaryDirectory(prefix='safety-finalize-access-') as folder:
        os.environ.update(
            DATABASE_URL=f'sqlite:///{folder}/tests.db', STORAGE_DIR=folder,
            APP_SECRET='isolated-finalize-access-secret', SECURE_COOKIES='false',
        )
        import fitz
        from starlette.requests import Request
        from app import main as m
        from app.database import SessionLocal, User, UserScope

        class Scenarios(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                cls.roles = ('Usuário', 'Administrador', 'Super Administrador', 'DEV')
                cls.cluster = next(iter(m.SEPARATE_CLUSTER_SITES))
                cls.site = m.SEPARATE_CLUSTER_SITES[cls.cluster][0]
                other_cluster = next(c for c in m.SEPARATE_CLUSTER_SITES if c != cls.cluster)
                other_site = m.SEPARATE_CLUSTER_SITES[other_cluster][0]
                with SessionLocal() as db:
                    cls.users = []
                    for index, role in enumerate(cls.roles):
                        user = User(username=f'finalize-{index}', full_name=f'Perfil {role}',
                                    role=role, password_hash='test', active=True)
                        db.add(user)
                        db.flush()
                        if role == 'Administrador':
                            db.add(UserScope(user_id=user.id, cluster=cls.cluster, site=cls.site))
                        cls.users.append(user)
                    cls.outsider = User(username='finalize-outsider', full_name='Outro usuário',
                                        role='Usuário', password_hash='test', active=True)
                    cls.outside_admin = User(username='finalize-outside-admin', full_name='Administrador externo',
                                             role='Administrador', password_hash='test', active=True)
                    db.add_all([cls.outsider, cls.outside_admin])
                    db.flush()
                    db.add(UserScope(user_id=cls.outside_admin.id, cluster=other_cluster, site=other_site))
                    db.commit()
                    for user in [*cls.users, cls.outsider, cls.outside_admin]:
                        db.expunge(user)
                pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 30), False)
                pixmap.clear_with(0)
                signature = m.save_signature(
                    'data:image/png;base64,' + base64.b64encode(pixmap.tobytes('png')).decode(),
                    prefix='finalize-test',
                )
                if not signature:
                    raise AssertionError('A assinatura real PNG não foi criada.')
                cls.documents = []
                for user in cls.users:
                    for kind in ('drill', 'height_kit', 'climber_assist'):
                        cfg = m.INSPECTION_MODULES[kind]
                        data = m.inspection_defaults(kind)
                        for key, _label in cfg.get('fields', []):
                            data[key] = 'Teste'
                        data.update(cluster=cls.cluster, site=cls.site)
                        if 'cluster_site' in data:
                            data['cluster_site'] = f'{cls.cluster} - {cls.site}'
                        active = 0
                        if cfg['mode'] in {'daily', 'weekly'}:
                            active = cfg['periods'].index(data.get('day_period', cfg['periods'][0]))
                            data['periods'][cfg['periods'][active]].update(
                                answers=['C'] * len(cfg['items']),
                                date=m.local_today().strftime('%d/%m/%Y'), signature_image=signature,
                            )
                            action = 'complete_period'
                        else:
                            data.update(
                                rows=[{'answer': 'ATENDE', 'action': '', 'evidence': '', 'photos': []}
                                      for _item in cfg['items']],
                                signature_image=signature, inspection_date=m.local_today().strftime('%d/%m/%Y'),
                            )
                            action = 'finalize'
                        response = m.process_inspection(cls.request(user), user, None, kind, data, action, active)
                        location = response.headers.get('location', '')
                        if response.status_code != 303 or not location.startswith('/document/'):
                            raise AssertionError(f'{user.role}/{kind}: finalização não abriu PDF: {location}')
                        doc = m.get_document(int(location.split('/')[2]))
                        if doc.status != 'Finalizada' or doc.created_by != user.id:
                            raise AssertionError(f'{user.role}/{kind}: finalização/autor incorretos')
                        cls.documents.append((user, kind, doc))

            @staticmethod
            def request(user=None, doc_id=1, *, query='', accept='text/html'):
                headers = [(b'host', b'testserver')]
                if accept is not None:
                    headers.append((b'accept', accept.encode()))
                session = {'csrf_token': 'test-csrf'}
                if user:
                    session.update(user_id=user.id, t=time.time())
                return Request({
                    'type': 'http', 'method': 'GET', 'path': f'/document/{doc_id}/pdf',
                    'scheme': 'http', 'root_path': '', 'query_string': query.encode(),
                    'headers': headers, 'session': session, 'app': m.app, 'router': m.app.router,
                    'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
                })

            @staticmethod
            def response_bytes(response):
                if hasattr(response, 'body'):
                    return response.body
                if hasattr(response, 'path'):
                    return Path(response.path).read_bytes()
                async def consume():
                    return b''.join([chunk async for chunk in response.body_iterator])
                return asyncio.run(consume())

            def test_finalized_inspection_viewer_and_previews_work_for_all_roles(self):
                for user, kind, doc in self.documents:
                    with self.subTest(role=user.role, kind=kind):
                        page = m.view_pdf(self.request(user, doc.id), doc.id)
                        self.assertEqual(page.status_code, 200)
                        self.assertIn('text/html', page.headers['content-type'])
                        self.assertIn(b'pdf-overlay', self.response_bytes(page))
                        metadata = m.view_pdf(self.request(user, doc.id, query='raw=1&preview_meta=1'), doc.id)
                        self.assertEqual(metadata.status_code, 200)
                        self.assertGreater(json.loads(metadata.body)['pages'], 0)
                        preview = m.view_pdf(self.request(user, doc.id, query='raw=1&preview_page=1'), doc.id)
                        self.assertEqual(preview.status_code, 200)
                        self.assertIn('image/png', preview.headers['content-type'])
                        # Uma segunda consulta também exercita o PNG servido do cache.
                        # Ela evita depender de threadpool de streaming no executor dos testes.
                        cached = m.view_pdf(self.request(user, doc.id, query='raw=1&preview_page=1'), doc.id)
                        self.assertTrue(cached.body.startswith(b'\x89PNG\r\n\x1a\n'))
                        raw = m.view_pdf(self.request(user, doc.id, query='raw=1', accept=None), doc.id)
                        self.assertEqual(raw.status_code, 200)
                        self.assertIn('application/pdf', raw.headers['content-type'])
                        self.assertTrue(self.response_bytes(raw).startswith(b'%PDF'))

            def test_viewer_is_html_even_without_explicit_browser_accept_header(self):
                for user, kind, doc in self.documents:
                    for accept in (None, '*/*'):
                        with self.subTest(role=user.role, kind=kind, accept=accept):
                            response = m.view_pdf(self.request(user, doc.id, accept=accept), doc.id)
                            self.assertEqual(response.status_code, 200)
                            self.assertIn('text/html', response.headers['content-type'])
                            self.assertIn(b'pdf-overlay', self.response_bytes(response))

            def test_other_users_and_admins_outside_scope_cannot_read_pdf_or_previews(self):
                for user, kind, doc in self.documents:
                    for actor in (self.outsider, self.outside_admin):
                        for query in ('', 'raw=1', 'raw=1&preview_meta=1', 'raw=1&preview_page=1'):
                            with self.subTest(owner=user.role, actor=actor.role, kind=kind, query=query):
                                response = m.view_pdf(self.request(actor, doc.id, query=query), doc.id)
                                self.assertEqual(response.status_code, 303)
                                self.assertEqual(response.headers['location'], '/')
                                self.assertNotIn('application/pdf', response.headers.get('content-type', ''))
                                self.assertNotIn('image/png', response.headers.get('content-type', ''))

            def test_anonymous_requests_redirect_to_login(self):
                _, _, doc = self.documents[0]
                for query in ('', 'raw=1', 'raw=1&preview_meta=1', 'raw=1&preview_page=1'):
                    with self.subTest(query=query):
                        response = m.view_pdf(self.request(None, doc.id, query=query), doc.id)
                        self.assertEqual(response.status_code, 303)
                        self.assertTrue(response.headers['location'].startswith('/login?next='))

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Scenarios))
        m.engine.dispose()
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if '--isolated' in sys.argv:
        raise SystemExit(_run_isolated_suite())
    unittest.main()
