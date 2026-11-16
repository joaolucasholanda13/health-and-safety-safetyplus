"""Auditoria com dados sintéticos, sem importar o banco real no processo pai."""
import asyncio
from pathlib import Path
import subprocess
import sys
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.audit_context import AuditContextMiddleware, metadata, csv_cell, detail_view

ROOT=Path(__file__).resolve().parents[1]

class AuditMetadataTests(unittest.TestCase):
    def test_concurrent_requests_do_not_mix_ips_and_forwarded_header_is_not_trusted(self):
        async def exercise():
            results={}
            async def app(scope,receive,send):
                scope['route']=SimpleNamespace(path='/document/{token}')
                await asyncio.sleep(.001)
                results[scope['client'][0]]=await asyncio.to_thread(metadata)
            middleware=AuditContextMiddleware(app)
            async def request(ip):
                scope=dict(type='http',method='POST',path='/document/secret-token',headers=[(b'user-agent',b'Test browser'),(b'x-forwarded-for',b'1.2.3.4')],client=(ip,123),server=('localhost',80),scheme='http',query_string=b'')
                await middleware(scope,None,None)
            await asyncio.gather(request('192.0.2.1'),request('2001:db8::1'))
            self.assertEqual(results['192.0.2.1']['ip_address'],'192.0.2.1')
            self.assertEqual(results['2001:db8::1']['ip_address'],'2001:db8::1')
            self.assertNotEqual(results['192.0.2.1']['request_id'],results['2001:db8::1']['request_id'])
            self.assertEqual(results['192.0.2.1']['request_path'],'/document/{token}')
            self.assertEqual(metadata()['ip_address'],'')
        asyncio.run(exercise())

    def test_csv_and_detail_rendering(self):
        self.assertEqual(csv_cell('=SUM(1,2)'),"'=SUM(1,2)")
        self.assertEqual(csv_cell('normal'),'normal')
        self.assertEqual(detail_view('legacy details')['text'],'legacy details')

    def test_database_migration_and_document_audit_in_isolation(self):
        result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--isolated'],cwd=ROOT,capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)


def isolated():
    import os,json,tempfile
    sys.path.insert(0,str(ROOT))
    with tempfile.TemporaryDirectory() as tmp:
        os.environ.update(STORAGE_DIR=tmp,DATABASE_URL='sqlite:///'+tmp+'/main.db',APP_SECRET='audit-test-secret',SECURE_COOKIES='false')
        from sqlalchemy import create_engine,text
        from app.database import ensure_audit_columns,SessionLocal,User,AuditLog
        legacy=create_engine('sqlite:///'+tmp+'/legacy.db')
        with legacy.begin() as conn:
            conn.execute(text('CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, detail TEXT)'))
            conn.execute(text("INSERT INTO audit_logs VALUES (1,'registro preservado')"))
        ensure_audit_columns(legacy);ensure_audit_columns(legacy)
        with legacy.connect() as conn:
            row=conn.execute(text('SELECT detail,ip_address FROM audit_logs')).one()
            assert row==('registro preservado',''),row
        from app import main as m
        with SessionLocal() as db:
            user=User(username='audit-test',password_hash='not-a-real-password',role='DEV',full_name='Auditor teste',active=True)
            db.add(user);db.commit();db.refresh(user);db.expunge(user)
        async def app(scope,receive,send):
            scope['route']=SimpleNamespace(path='/apr/{doc_id}/salvar')
            first=m.save_doc(None,'apr',dict(activity='ANTES',password='segredo-antigo',token='token-antigo'),user)
            m.save_doc(first,'apr',dict(activity='DEPOIS',password='segredo-novo',token='token-novo'),user)
            m.audit(user.id,'trocar_senha','Senha alterada')
            with SessionLocal() as db:
                direct=AuditLog(user_id=user.id,action='direto',detail='registro na transação')
                db.add(direct);db.commit()
        scope=dict(type='http',method='POST',path='/apr/1/salvar',headers=[(b'user-agent',b'Firefox test')],client=('192.0.2.25',123),server=('localhost',80),scheme='http',query_string=b'')
        asyncio.run(AuditContextMiddleware(app)(scope,None,None))
        with SessionLocal() as db:
            rows=db.query(AuditLog).order_by(AuditLog.id).all()
            assert len(rows)==4,len(rows)
            assert all(r.ip_address=='192.0.2.25' for r in rows)
            assert all(r.user_agent=='Firefox test' for r in rows)
            assert all(r.request_path=='/apr/{doc_id}/salvar' for r in rows)
            assert len({r.request_id for r in rows})==1
            changes=json.loads(rows[1].detail)['changes']
            assert any(c['before']=='ANTES' and c['after']=='DEPOIS' for c in changes),changes
            assert 'segredo' not in rows[1].detail and 'token-novo' not in rows[1].detail
            for row in rows: db.expunge(row)
        from jinja2 import Environment
        source=(ROOT/'app/templates/ti_tools.html').read_text()
        fragment=source.split("{% elif section=='audit' %}",1)[1].split("{% elif section=='integrity' %}",1)[0]
        html=Environment(autoescape=True).from_string(fragment).render(logs=rows,names={user.id:'Auditor teste'},
            audit_label=m.audit_label,detail_view=m.detail_view,total=4,page=1,pages=1,actions=[],
            f=dict(q='',action='',user_id='',start='',end=''),qs='')
        assert '192.0.2.25' in html and 'ANTES' in html and 'DEPOIS' in html
        assert 'Firefox test' in html and 'Criou um documento' in html
        from starlette.requests import Request
        from unittest.mock import patch
        with patch.object(m,'require_dev',return_value=user):
            response=m.ti_audit_csv(Request(scope))
        csv=response.body.decode('utf-8-sig')
        assert 'ip_origem' in csv and '192.0.2.25' in csv and 'Firefox test' in csv

if __name__=='__main__':
    if '--isolated' in sys.argv:isolated()
    else:unittest.main()
