"""Login SSO (Microsoft Entra ID): casamento por e-mail, sem criar contas."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SsoTests(unittest.TestCase):
    def test_sso_flow(self):
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--isolated'],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


def _run():
    sys.path.insert(0, str(ROOT))
    with tempfile.TemporaryDirectory(prefix='safety-sso-') as folder:
        os.environ.update(DATABASE_URL=f'sqlite:///{folder}/t.db', STORAGE_DIR=folder,
                          APP_SECRET='isolated-sso-secret', SECURE_COOKIES='false',
                          SSO_ENABLED='true', SSO_TENANT_ID='tenant-1', SSO_CLIENT_ID='cid',
                          SSO_CLIENT_SECRET='sec', SSO_ALLOWED_DOMAINS='empresa.com',
                          DOMAIN='safetyplus.tech')
        import asyncio
        from starlette.requests import Request
        from app import main as m, sso
        from app.database import SessionLocal, User, AuditLog

        with SessionLocal() as db:
            db.add_all([User(username='ana@empresa.com', full_name='Ana', role='Usuário', password_hash='x', active=True),
                        User(username='off@empresa.com', full_name='Off', role='Usuário', password_hash='x', active=False)])
            db.commit()

        class Fake:
            claims = {}
            raises = False
            async def authorize_access_token(self, request):
                if self.raises: raise ValueError('state')
                return {'userinfo': self.claims}
        fake = Fake(); sso.client = lambda: fake

        def call(claims=None, raises=False, query=b''):
            fake.claims = claims or {}; fake.raises = raises
            req = Request({'type': 'http', 'method': 'GET', 'path': '/sso/callback', 'headers': [],
                           'query_string': query, 'session': {'sso_next': '/apr/new'}, 'app': m.app,
                           'client': ('1.2.3.4', 1)})
            resp = asyncio.run(m.sso_callback(req))
            return resp, req.session

        assert sso.redirect_uri() == 'https://safetyplus.tech/sso/callback'
        ok, sess = call({'tid': 'tenant-1', 'preferred_username': 'Ana@Empresa.com'})
        assert ok.headers['location'] == '/apr/new' and sess.get('user_id'), (ok.headers, sess)
        for claims, why in [({'tid': 'tenant-1', 'email': 'ghost@empresa.com'}, 'inexistente'),
                            ({'tid': 'tenant-1', 'email': 'off@empresa.com'}, 'inativo'),
                            ({'tid': 'tenant-1', 'email': 'ana@outro.com'}, 'domínio'),
                            ({'tid': 'outro', 'email': 'ana@empresa.com'}, 'tenant'),
                            ({'tid': 'tenant-1'}, 'sem e-mail')]:
            resp, sess = call(claims)
            assert resp.headers['location'] == '/login' and not sess.get('user_id'), why
        resp, sess = call(raises=True)
        assert resp.headers['location'] == '/login' and not sess.get('user_id')
        resp, sess = call(query=b'error=access_denied')
        assert resp.headers['location'] == '/login'
        with SessionLocal() as db:
            actions = [a.action for a in db.query(AuditLog).all()]
        assert actions.count('login_sso') == 1 and actions.count('login_sso_falha') == 7, actions
        os.environ['SSO_ENABLED'] = 'false'
        assert not sso.enabled()
        print('ok')


if __name__ == '__main__':
    if '--isolated' in sys.argv: _run()
    else: unittest.main()
