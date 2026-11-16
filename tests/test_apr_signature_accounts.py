"""Autorização das assinaturas online sem acessar o banco de produção."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.datastructures import FormData
from starlette.responses import RedirectResponse

SOURCE = Path(__file__).resolve().parents[1] / 'app/main.py'
NAMES = {'apr_participant_signature_submit', 'apr_participant_signature_present_submit',
         'apr_manual_signature_lookup', 'apr_manual_signature_otp', 'apr_manual_signature_submit',
         'apr_public_signature_page', 'apr_public_signature_participant_lookup', 'apr_public_signature_submit'}

class SignatureAccountTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE.read_text())
        nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in NAMES]
        for node in nodes:
            node.decorator_list = []
        self.user = SimpleNamespace(id=100, role='Usuário')
        self.doc = SimpleNamespace(id=1, code='APR-TESTE', kind='apr', status='Pendente assinatura', created_by=99)
        self.data = {'workers': [{'participant_user_id': str(uid)} for uid in range(100, 105)]}
        def reached_signature(*args):
            raise RuntimeError('assinante autorizado')
        self.scope = dict(Request=Request, HTTPException=HTTPException, RedirectResponse=RedirectResponse,
            current_user=lambda r: self.user, get_document=lambda i: self.doc, doc_data=lambda d: self.data,
            clean=lambda v: str(v or '').strip(), verify_csrf=lambda *a: None,
            save_signature=reached_signature, _apr_public_signature_valid=lambda *a: True)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), self.scope)

    def request(self, index=0):
        request = Request({'type':'http', 'method':'POST', 'path':'/apr/1/assinar', 'headers':[], 'session':{}})
        request._form = FormData({'worker_index':str(index), 'sig_participant':'rubrica'})
        return request

    def call(self, name, index=0, **kwargs):
        result = self.scope[name](self.request(index), 1, **kwargs)
        return asyncio.run(result) if hasattr(result, '__await__') else result

    def test_five_members_can_each_sign_from_their_account(self):
        for index in range(5):
            self.user.id = 100 + index
            with self.assertRaisesRegex(RuntimeError, 'assinante autorizado'):
                self.call('apr_participant_signature_submit', index)

    def test_creator_admin_and_other_member_cannot_sign_for_someone_else(self):
        for uid, role in [(99,'Usuário'), (1,'Super Administrador'), (2,'Administrador'), (101,'Usuário')]:
            self.user.id, self.user.role = uid, role
            for route in ['apr_participant_signature_submit', 'apr_participant_signature_present_submit']:
                with self.assertRaises(HTTPException) as error:
                    self.call(route)
                self.assertEqual(error.exception.status_code, 403)

    def test_old_manual_and_public_endpoints_cannot_bypass_account(self):
        for route in ['apr_manual_signature_lookup', 'apr_manual_signature_otp', 'apr_manual_signature_submit',
                      'apr_public_signature_participant_lookup', 'apr_public_signature_submit']:
            with self.assertRaises(HTTPException) as error:
                self.call(route, **({'token':'old-valid-token'} if 'public' in route else {}))
            self.assertEqual(error.exception.status_code, 403)

    def test_old_qr_requires_login_and_goes_to_own_signature(self):
        self.user = None
        response = self.call('apr_public_signature_page', token='valid')
        self.assertEqual(response.headers['location'], '/login?next=/apr/1/assinar')
        self.user = SimpleNamespace(id=100)
        response = self.call('apr_public_signature_page', token='valid')
        self.assertEqual(response.headers['location'], '/apr/1/assinar')

    def test_offline_collection_remains_available(self):
        source = SOURCE.read_text()
        self.assertIn("@app.post('/apr/offline-bundle')", source)
        self.assertIn("form.get(f'offline_sig_{i}')", source)

if __name__ == '__main__':
    unittest.main()
