"""Validate the real CSRF function without opening the application database."""
import ast
import hmac
from pathlib import Path
import unittest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.datastructures import FormData

source = Path(__file__).resolve().parents[1] / 'app/security.py'
function = next(node for node in ast.parse(source.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == 'verify_csrf')
scope = dict(Request=Request, HTTPException=HTTPException, hmac=hmac)
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), scope)
verify_csrf = scope['verify_csrf']

class OfflineCsrfTests(unittest.TestCase):
    def request(self, token='valid', fields=1, entries=None):
        request = Request({'type': 'http', 'method': 'POST', 'path': '/inspection/climber_assist/save',
            'headers': [(b'x-sp-offline-sync', b'1'), (b'x-csrf-token', token.encode()),
                        (b'x-sp-offline-field-count', str(fields).encode())],
            'session': {'csrf_token': 'valid', 'user_id': 1}})
        request._form = FormData(entries if entries is not None else [('activity', 'Teste')])
        return request

    def test_header_recovers_missing_form_token(self):
        verify_csrf(self.request(), None)

    def test_wrong_header_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            verify_csrf(self.request(token='wrong'), None)
        self.assertEqual(error.exception.status_code, 403)

    def test_incomplete_document_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            verify_csrf(self.request(entries=[]), None)
        self.assertEqual(error.exception.status_code, 400)

    def test_duplicate_fields_are_counted(self):
        verify_csrf(self.request(fields=2, entries=[('worker', 'A'), ('worker', 'B')]), None)

    def bundle_part(self, request, entries):
        # Usa a classe real sem importar main e abrir o banco da aplicação.
        main = source.with_name('main.py')
        shim = next(node for node in ast.parse(main.read_text()).body
                    if isinstance(node, ast.ClassDef) and node.name == '_OfflineFormShim')
        scope = dict(Request=Request, Any=object, _SPFormData=FormData)
        exec(compile(ast.Module(body=[shim], type_ignores=[]), str(main), 'exec'), scope)
        return scope['_OfflineFormShim'](request, entries)

    def test_bundle_apr_part_uses_full_received_count(self):
        request = self.request(fields=3, entries=[('activity', 'APR'),
            ('pt0__activity', 'PT'), ('offline_bundle_id', 'bundle-123')])
        verify_csrf(self.bundle_part(request, [('activity', 'APR')]), None)

    def test_bundle_pt_part_uses_full_received_count(self):
        request = self.request(fields=3, entries=[('activity', 'APR'),
            ('pt0__activity', 'PT'), ('offline_bundle_id', 'bundle-123')])
        verify_csrf(self.bundle_part(request, [('activity', 'PT')]), None)

    def test_incomplete_bundle_is_still_rejected(self):
        request = self.request(fields=3, entries=[('activity', 'APR')])
        with self.assertRaises(HTTPException) as error:
            verify_csrf(self.bundle_part(request, [('activity', 'APR')]), None)
        self.assertEqual(error.exception.status_code, 400)

    def test_wrong_body_token_cannot_be_overridden_by_header(self):
        with self.assertRaises(HTTPException):
            verify_csrf(self.request(), 'wrong')

class OfflineTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_large_urlencoded_form_is_parsed_without_losing_fields(self):
        from urllib.parse import urlencode
        entries = [('csrf_token', 'valid'), ('worker', 'José'), ('worker', 'Ana'),
                   ('signature', 'data:image/png;base64,a+b/c=='), ('photo', '')]
        entries += [(f'check_{i}', 'Sim') for i in range(1500)]
        body = urlencode(entries).encode()
        messages = iter([{'type': 'http.request', 'body': body[:200], 'more_body': True},
                         {'type': 'http.request', 'body': body[200:], 'more_body': False}])

        async def receive():
            return next(messages)

        request = Request({'type': 'http', 'method': 'POST', 'path': '/inspection/general/save',
            'headers': [(b'content-type', b'application/x-www-form-urlencoded;charset=UTF-8'),
                        (b'x-sp-offline-sync', b'1'), (b'x-csrf-token', b'valid'),
                        (b'x-sp-offline-field-count', str(len(entries) - 1).encode())],
            'session': {'csrf_token': 'valid', 'user_id': 1}}, receive)
        form = await request.form()
        verify_csrf(request, form.get('csrf_token'))
        self.assertEqual(form.getlist('worker'), ['José', 'Ana'])
        self.assertEqual(form.get('signature'), 'data:image/png;base64,a+b/c==')
        self.assertEqual(form.get('photo'), '')
        self.assertEqual(len(list(form.multi_items())), len(entries))

if __name__ == '__main__':
    unittest.main()
