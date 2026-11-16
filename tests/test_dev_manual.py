"""Manual de uso da área DEV: só o perfil DEV recebe os artigos."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DevManualTests(unittest.TestCase):
    def test_dev_articles_only_for_dev(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--isolated'],
                                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def _run():
    sys.path.insert(0, str(ROOT))
    with tempfile.TemporaryDirectory(prefix='safety-dev-manual-') as folder:
        os.environ.update(DATABASE_URL=f'sqlite:///{folder}/t.db', STORAGE_DIR=folder,
                          APP_SECRET='isolated-dev-manual-secret', SECURE_COOKIES='false')
        from starlette.requests import Request
        from app import main as m
        from app.database import SessionLocal, User
        req = Request({'type': 'http', 'method': 'GET', 'path': '/central-ajuda', 'headers': [],
                       'query_string': b'', 'session': {}, 'app': m.app})
        seen = {}
        with SessionLocal() as db:
            for i, role in enumerate(('Usuário', 'Administrador', 'Super Administrador', 'DEV')):
                u = User(username=f'man-{i}', full_name=role, role=role, password_hash='x', active=True)
                db.add(u); db.commit(); db.refresh(u)
                ctx = m._support_center_context(req, u, 'como-usar', '')
                seen[role] = ([a['id'] for a in ctx['help_articles'] if a['cat'] == 'dev'],
                              [c[0] for c in ctx['help_cats']])
        assert seen['DEV'][0] and 'dev' in seen['DEV'][1], seen['DEV']
        for role in ('Usuário', 'Administrador', 'Super Administrador'):
            assert not seen[role][0] and 'dev' not in seen[role][1], (role, seen[role])
        print('ok')


if __name__ == '__main__':
    if '--isolated' in sys.argv:
        _run()
    else:
        unittest.main()
