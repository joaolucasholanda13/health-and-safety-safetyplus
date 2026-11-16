"""Assinatura de integrante incluído após a conclusão, em banco temporário."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ExecutionMemberRegressionTests(unittest.TestCase):
    def test_execution_member_routes(self):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), '--isolated'],
            cwd=ROOT, text=True, capture_output=True, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def _run_isolated_suite():
    import asyncio
    import inspect
    import json
    import time
    from unittest.mock import patch

    sys.path.insert(0, str(ROOT))
    with tempfile.TemporaryDirectory(prefix='safety-execution-member-') as folder:
        os.environ.update(
            DATABASE_URL=f'sqlite:///{folder}/test.db', STORAGE_DIR=folder,
            APP_SECRET='isolated-execution-member-secret', SECURE_COOKIES='false',
        )
        from fastapi import HTTPException
        from starlette.datastructures import FormData
        from starlette.requests import Request
        from app import main as m
        from app.database import SessionLocal, User, Company, Participant, Document, Notification
        real_save_signature = m.save_signature
        real_finalize_pdf = m.finalize_pdf

        class Scenarios(unittest.TestCase):
            counter = 0

            def setUp(self):
                Scenarios.counter += 1
                serial = Scenarios.counter
                self.push = self.enterContext(patch.object(m, '_queue_push_notification_ids'))
                self.signature = self.enterContext(patch.object(m, 'save_signature', return_value='signatures/test-member.png'))
                self.pdf = self.enterContext(patch.object(m, 'finalize_pdf', side_effect=lambda doc, *a, **kw: doc))
                with SessionLocal() as db:
                    self.owner = User(username=f'owner-{serial}', full_name='Quem inclui', password_hash='test', role='Usuário', active=True)
                    self.member_user = User(username=f'member-{serial}', full_name='Quem assina', password_hash='test', role='Usuário', active=True)
                    self.third = User(username=f'third-{serial}', full_name='Terceiro', password_hash='test', role='Usuário', active=True)
                    self.admin = User(username=f'admin-{serial}', full_name='Administrador', password_hash='test', role='Super Administrador', active=True)
                    company = Company(name=f'Empresa-{serial}', active=True)
                    db.add_all([self.owner, self.member_user, self.third, self.admin, company])
                    db.flush()
                    self.participant = Participant(company_id=company.id, cpf=f'{serial:011d}', full_name='Integrante convidado', job_title='Técnico', user_id=self.member_user.id, active=True)
                    db.add(self.participant)
                    data = m.apr_defaults()
                    data.update(activity='Atividade aprovada', workers=[], execution_members=[], code=f'APR-2026-TEST-{serial}', status='Finalizada')
                    self.original = Document(code=data['code'], kind='apr', title='APR', status='Finalizada', created_by=self.owner.id, data_json=json.dumps(data), pdf_path=f'pdfs/original-{serial}.pdf', finalized_at=m.now())
                    db.add(self.original)
                    db.commit()
                    for row in [self.owner, self.member_user, self.third, self.admin, self.participant, self.original]:
                        db.expunge(row)

            def request(self, user=None, *, csrf=True, method='POST', **fields):
                session = {'csrf_token': 'test-csrf'}
                if user:
                    session.update(user_id=user.id, t=time.time())
                request = Request({'type': 'http', 'method': method, 'path': '/',
                                   'root_path': '', 'query_string': b'', 'scheme': 'http',
                                   'headers': [(b'host', b'testserver')], 'session': session,
                                   'server': ('testserver', 80), 'client': ('127.0.0.1', 1234),
                                   'app': m.app, 'router': m.app.router})
                request._form = FormData({**({'csrf_token': 'test-csrf'} if csrf else {}), **fields})
                return request

            def invoke(self, route, request, *args):
                result = route(request, *args)
                return asyncio.run(result) if inspect.isawaitable(result) else result

            def doc(self, doc_id=None):
                with SessionLocal() as db:
                    row = db.get(Document, doc_id or self.original.id)
                    db.expunge(row)
                    return row

            def payload(self, doc_id=None):
                return json.loads(self.doc(doc_id).data_json)

            def pending(self, **extra):
                response = self.invoke(m.apr_add_member_submit, self.request(self.owner, participant_id=str(self.participant.id), reason='Equipe adicional', **extra), self.original.id)
                self.assertEqual(response.status_code, 303)
                requests = self.payload().get('execution_member_requests') or []
                self.assertEqual(len(requests), 1)
                return requests[0]

            def assert_forbidden(self, function, request, *args, status=403):
                with self.assertRaises(HTTPException) as error:
                    self.invoke(function, request, *args)
                self.assertEqual(error.exception.status_code, status)

            def test_request_sends_notification_without_signature_or_new_version(self):
                member = self.pending(member_signature='data:image/png;base64,forged')
                self.assertEqual(member['participant_user_id'], str(self.member_user.id))
                self.assertEqual(member.get('signature_status'), 'Pendente')
                self.assertFalse(member.get('signature_image'))
                self.assertFalse(self.payload().get('execution_members'))
                self.assertEqual(self.doc().status, 'Finalizada')
                self.assertFalse(self.payload().get('replaced_by_apr_id'))
                self.signature.assert_not_called()
                self.pdf.assert_not_called()
                with SessionLocal() as db:
                    notes = db.query(Notification).filter(Notification.document_id == self.original.id, Notification.kind == 'apr_execution_member_signature').all()
                self.assertEqual(len(notes), 1)
                self.assertEqual(notes[0].recipient_user_id, self.member_user.id)
                self.assertIn(f'/apr/{self.original.id}/integrantes/{member["id"]}/assinar', m._notification_target(notes[0], self.doc(), self.member_user))
                self.push.assert_called()

            def test_requester_and_other_accounts_cannot_sign_recipient_request(self):
                member = self.pending()
                for actor in [self.owner, self.third, self.admin]:
                    with self.subTest(actor=actor.username):
                        self.assert_forbidden(m.apr_execution_member_signature_submit, self.request(actor, signature='data:image/png;base64,test'), self.original.id, member['id'])
                self.assertEqual(self.doc().status, 'Finalizada')
                self.assertFalse(self.payload().get('execution_members'))
                self.signature.assert_not_called()

            def test_signature_page_restricts_even_admin_to_the_recipient(self):
                member = self.pending()
                for actor in [self.owner, self.third, self.admin]:
                    with self.subTest(actor=actor.username):
                        self.assert_forbidden(m.apr_execution_member_signature_page, self.request(actor, method='GET'), self.original.id, member['id'])
                response = self.invoke(m.apr_execution_member_signature_page, self.request(self.member_user, method='GET'), self.original.id, member['id'])
                self.assertEqual(response.status_code, 200)

            def test_only_recipient_signature_creates_signed_version(self):
                member = self.pending()
                response = self.invoke(m.apr_execution_member_signature_submit, self.request(self.member_user, signature='data:image/png;base64,test'), self.original.id, member['id'])
                self.assertEqual(response.status_code, 303)
                old = self.doc()
                self.assertEqual(old.status, 'Substituída')
                old_data = json.loads(old.data_json)
                current_id = int(old_data['replaced_by_apr_id'])
                current = self.doc(current_id)
                data = json.loads(current.data_json)
                self.assertEqual(current.status, 'Finalizada')
                self.assertEqual(current.created_by, self.owner.id)
                self.assertEqual(data['activity'], 'Atividade aprovada')
                self.assertEqual(old.pdf_path, self.original.pdf_path)
                self.assertFalse(old_data.get('execution_members'))
                signed = data['execution_members'][0]
                self.assertEqual(signed['participant_id'], str(self.participant.id))
                self.assertEqual(signed['signed_by_user_id'], str(self.member_user.id))
                self.assertEqual(signed['signature_image'], 'signatures/test-member.png')
                self.assertEqual(signed['added_by_user_id'], str(self.owner.id))
                self.assertTrue(signed.get('signed_at'))
                self.signature.assert_called_once()
                self.pdf.assert_called()

            def test_duplicate_pending_request_is_not_added_twice(self):
                self.pending()
                response = self.invoke(m.apr_add_member_submit, self.request(self.owner, participant_id=str(self.participant.id)), self.original.id)
                self.assertEqual(response.status_code, 303)
                self.assertEqual(len(self.payload()['execution_member_requests']), 1)
                with SessionLocal() as db:
                    self.assertEqual(db.query(Notification).filter(Notification.document_id == self.original.id, Notification.kind == 'apr_execution_member_signature').count(), 1)

            def test_already_existing_worker_cannot_be_requested_again(self):
                with SessionLocal() as db:
                    row = db.get(Document, self.original.id)
                    data = json.loads(row.data_json)
                    data['workers'] = [{'participant_id': str(self.participant.id), 'participant_user_id': str(self.member_user.id), 'signature_image': 'signatures/already.png'}]
                    row.data_json = json.dumps(data)
                    db.commit()
                response = self.invoke(m.apr_add_member_submit, self.request(self.owner, participant_id=str(self.participant.id)), self.original.id)
                self.assertEqual(response.status_code, 303)
                self.assertFalse(self.payload().get('execution_member_requests'))

            def test_participant_without_active_account_cannot_receive_request(self):
                with SessionLocal() as db:
                    db.get(Participant, self.participant.id).user_id = None
                    db.commit()
                response = self.invoke(m.apr_add_member_submit, self.request(self.owner, participant_id=str(self.participant.id)), self.original.id)
                self.assertEqual(response.status_code, 303)
                self.assertFalse(self.payload().get('execution_member_requests'))
                with SessionLocal() as db:
                    self.assertEqual(db.query(Notification).filter(Notification.document_id == self.original.id).count(), 0)

            def test_inactive_account_cannot_receive_request(self):
                with SessionLocal() as db:
                    db.get(User, self.member_user.id).active = False
                    db.commit()
                response = self.invoke(m.apr_add_member_submit, self.request(self.owner, participant_id=str(self.participant.id)), self.original.id)
                self.assertEqual(response.status_code, 303)
                self.assertFalse(self.payload().get('execution_member_requests'))

            def test_request_and_signature_enforce_csrf(self):
                self.assert_forbidden(m.apr_add_member_submit, self.request(self.owner, csrf=False, participant_id=str(self.participant.id)), self.original.id)
                member = self.pending()
                self.assert_forbidden(m.apr_execution_member_signature_submit, self.request(self.member_user, csrf=False, signature='data:image/png;base64,test'), self.original.id, member['id'])
                self.assertFalse(self.payload().get('execution_members'))

            def test_pending_recipient_can_read_without_entering_owner_history(self):
                self.pending()
                self.assertTrue(m.user_can_access_document(self.member_user, self.doc()))
                self.assertFalse(m.user_can_list_document(self.member_user, self.doc()))
                self.assertFalse(m.user_can_access_document(self.third, self.doc()))

            def test_pending_recipient_cannot_use_read_access_to_invite_others(self):
                self.pending()
                self.assert_forbidden(m.apr_add_member_submit, self.request(self.member_user, participant_id=str(self.participant.id)), self.original.id)
                self.assertEqual(len(self.payload()['execution_member_requests']), 1)

            def test_pending_recipient_cannot_use_read_access_to_change_observations(self):
                self.pending()
                self.assert_forbidden(m.apr_add_execution_observation, self.request(self.member_user, observation='Tentativa de alterar a APR'), self.original.id)
                self.assertFalse(self.payload().get('execution_observations'))

            def test_pending_recipient_cannot_add_or_create_linked_permits(self):
                self.pending()
                permit_name = next(iter(m.APR_CRITICAL_PERMIT_KIND))
                kind = m.APR_CRITICAL_PERMIT_KIND[permit_name]
                with SessionLocal() as db:
                    count_before = db.query(Document).count()
                self.assert_forbidden(m.apr_add_permit_type, self.request(self.member_user, permit_name=permit_name), self.original.id)
                self.assert_forbidden(m.apr_open_linked_permit, self.request(self.member_user, method='GET'), self.original.id, kind)
                with SessionLocal() as db:
                    self.assertEqual(db.query(Document).count(), count_before)

            def test_required_request_arrives_even_with_notification_preferences_off(self):
                with patch.object(m, '_notification_enabled', return_value=False):
                    member = self.pending()
                self.push.assert_called_once_with([])
                with SessionLocal() as db:
                    note = db.query(Notification).filter(Notification.document_id == self.original.id, Notification.kind == 'apr_execution_member_signature').one()
                    self.assertFalse(note.read)
                response = m.dashboard(self.request(self.member_user, method='GET'))
                cards = response.context['pending_signatures']
                self.assertEqual(len(cards), 1)
                self.assertEqual(cards[0]['url'], f'/apr/{self.original.id}/integrantes/{member["id"]}/assinar')

            def test_admin_recipient_outside_scope_can_sign_only_own_request(self):
                member = self.pending()
                with SessionLocal() as db:
                    db.get(User, self.member_user.id).role = 'Administrador'
                    document = db.get(Document, self.original.id)
                    document.cluster = 'FORA-DO-ESCOPO'
                    document.site = 'Local'
                    db.commit()
                self.member_user.role = 'Administrador'
                self.assertFalse(m.admin_scope_allows_document(self.member_user, self.doc()))
                self.assertTrue(m.user_can_access_document(self.member_user, self.doc()))
                response = self.invoke(m.apr_execution_member_signature_submit, self.request(self.member_user, signature='data:image/png;base64,test'), self.original.id, member['id'])
                self.assertEqual(response.status_code, 303)
                self.assertEqual(self.doc().status, 'Substituída')

            def test_pending_request_cannot_be_signed_through_public_qr(self):
                self.pending()
                request = self.request(cpf=self.participant.cpf, accepted='1', sig_rubric='data:image/png;base64,test')
                with patch.object(m, '_apr_public_signature_valid', return_value=True), patch.object(
                    m, 'cpf_is_valid', return_value=True,
                ), patch.object(m, '_apr_day_context', return_value={'valid_today': True}):
                    self.assert_forbidden(m.apr_public_signature_submit, request, self.original.id, 'valid-token')
                self.signature.assert_not_called()
                self.assertFalse(self.payload().get('workers'))

            def test_signature_commit_failure_preserves_original_without_partial_version(self):
                from sqlalchemy import event
                member = self.pending()
                with SessionLocal() as db:
                    count_before = db.query(Document).count()
                def fail_commit(connection):
                    raise OSError('commit failed')
                event.listen(m.engine, 'commit', fail_commit)
                try:
                    with self.assertRaises(OSError):
                        self.invoke(m.apr_execution_member_signature_submit, self.request(self.member_user, signature='data:image/png;base64,test'), self.original.id, member['id'])
                finally:
                    event.remove(m.engine, 'commit', fail_commit)
                with SessionLocal() as db:
                    self.assertEqual(db.query(Document).count(), count_before)
                self.assertEqual(self.doc().status, 'Finalizada')
                self.assertFalse(self.payload().get('execution_members'))
                self.assertFalse(self.payload().get('replaced_by_apr_id'))

            def test_real_signature_and_pdf_include_signer_and_preserve_original_file(self):
                import base64
                import fitz
                original_file = Path(folder) / self.original.pdf_path
                with fitz.open() as original_pdf:
                    original_pdf.new_page().insert_text((50, 50), 'Original PDF preserved')
                    original_pdf.save(original_file)
                original_bytes = original_file.read_bytes()
                pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 30), False)
                pixmap.clear_with(255)
                pixmap.set_rect(fitz.IRect(5, 10, 65, 13), (0, 0, 0))
                signature = 'data:image/png;base64,' + base64.b64encode(pixmap.tobytes('png')).decode('ascii')
                member = self.pending()
                with patch.object(m, 'save_signature', side_effect=real_save_signature), patch.object(
                    m, 'finalize_pdf', side_effect=real_finalize_pdf,
                ):
                    response = self.invoke(m.apr_execution_member_signature_submit, self.request(self.member_user, signature=signature), self.original.id, member['id'])
                self.assertEqual(response.status_code, 303)
                current_id = int(self.payload()['replaced_by_apr_id'])
                current = self.doc(current_id)
                self.assertTrue(current.pdf_path)
                self.assertNotEqual(current.pdf_path, self.original.pdf_path)
                signature_file = Path(folder) / json.loads(current.data_json)['execution_members'][0]['signature_image']
                self.assertTrue(signature_file.is_file())
                with fitz.open(Path(folder) / current.pdf_path) as pdf:
                    text = '\n'.join(page.get_text() for page in pdf)
                self.assertIn('Assinado por:', text)
                self.assertIn(self.member_user.full_name, text)
                self.assertEqual(original_file.read_bytes(), original_bytes)

            def test_account_binding_change_prevents_former_account_from_signing(self):
                member = self.pending()
                with SessionLocal() as db:
                    db.get(Participant, self.participant.id).user_id = self.third.id
                    db.commit()
                self.assert_forbidden(m.apr_execution_member_signature_submit, self.request(self.member_user, signature='data:image/png;base64,test'), self.original.id, member['id'])
                self.signature.assert_not_called()
                self.assertEqual(self.doc().status, 'Finalizada')

            def test_replay_does_not_create_another_signed_version(self):
                member = self.pending()
                request = self.request(self.member_user, signature='data:image/png;base64,test')
                response = self.invoke(m.apr_execution_member_signature_submit, request, self.original.id, member['id'])
                self.assertEqual(response.status_code, 303)
                with SessionLocal() as db:
                    count_before = db.query(Document).count()
                try:
                    response = self.invoke(m.apr_execution_member_signature_submit, self.request(self.member_user, signature='data:image/png;base64,again'), self.original.id, member['id'])
                    self.assertIn(response.status_code, (200, 303, 409))
                except HTTPException as error:
                    self.assertEqual(error.status_code, 409)
                with SessionLocal() as db:
                    self.assertEqual(db.query(Document).count(), count_before)
                self.signature.assert_called_once()

            def test_remaining_request_and_old_link_follow_successive_versions(self):
                first = self.pending()
                with SessionLocal() as db:
                    user = User(username=f'second-member-{Scenarios.counter}', full_name='Segundo integrante', password_hash='test', role='Usuário', active=True)
                    db.add(user)
                    db.flush()
                    participant = Participant(company_id=self.participant.company_id, cpf=f'{Scenarios.counter + 1000:011d}', full_name='Segundo integrante', user_id=user.id, active=True)
                    db.add(participant)
                    db.commit()
                    db.expunge(user)
                    db.expunge(participant)
                response = self.invoke(m.apr_add_member_submit, self.request(self.owner, participant_id=str(participant.id)), self.original.id)
                self.assertEqual(response.status_code, 303)
                second = next(member for member in self.payload()['execution_member_requests'] if member['participant_id'] == str(participant.id))
                self.invoke(m.apr_execution_member_signature_submit, self.request(self.member_user, signature='data:image/png;base64,first'), self.original.id, first['id'])
                middle_id = int(self.payload()['replaced_by_apr_id'])
                with SessionLocal() as db:
                    note = db.query(Notification).filter(Notification.recipient_user_id == user.id, Notification.kind == 'apr_execution_member_signature').one()
                    self.assertEqual(note.document_id, middle_id)
                    self.assertFalse(note.read)
                    self.assertEqual(m._notification_target(note, self.doc(middle_id), user), f'/apr/{middle_id}/integrantes/{second["id"]}/assinar')
                response = self.invoke(m.apr_execution_member_signature_page, self.request(user, method='GET'), self.original.id, second['id'])
                self.assertEqual(response.status_code, 303)
                self.assertEqual(response.headers['location'], f'/apr/{middle_id}/integrantes/{second["id"]}/assinar')
                response = self.invoke(m.apr_execution_member_signature_submit, self.request(user, signature='data:image/png;base64,second'), self.original.id, second['id'])
                self.assertEqual(response.status_code, 303)
                current_id = int(self.payload(middle_id)['replaced_by_apr_id'])
                current = self.doc(current_id)
                data = json.loads(current.data_json)
                self.assertEqual(current.status, 'Finalizada')
                self.assertEqual(self.doc(middle_id).status, 'Substituída')
                self.assertFalse(data.get('execution_member_requests'))
                self.assertEqual({member['signed_by_user_id'] for member in data['execution_members']}, {str(self.member_user.id), str(user.id)})

        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Scenarios))
        return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    if '--isolated' in sys.argv:
        raise SystemExit(_run_isolated_suite())
    unittest.main()
