from __future__ import annotations
import asyncio, base64, hashlib, hmac, io, json, os, re, secrets, threading, unicodedata, time
from collections import Counter
from contextlib import nullcontext
import fitz
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Any
from urllib.parse import urlencode
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, HTMLResponse, RedirectResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import or_, desc, text, delete, func
from sqlalchemy.exc import SQLAlchemyError
import qrcode
import qrcode.image.svg

from .audit_context import AuditContextMiddleware, audit_label, detail_view, csv_cell
from . import monitor
from .database import DocumentVersion, Base, engine, SessionLocal, User, UserScope, Company, Participant, Document, Notification, PushSubscription, AuditLog
from .security import VIEW_CLUSTER, hash_password, verify_password, current_user, csrf_token, verify_csrf, require_admin, require_super_admin, require_dev, revoke_password_sessions
from . import custom_docs, ti_tools
from .module_configs import (
    MODULES, DOCUMENT_TITLES, PREFIXES, CLUSTERS, CHECKLIST, HAZARD_OPTIONS, RISK_OPTIONS, RISK_CATALOG,
    PT_WORK_TYPES, CONFINED_ENTRY_TYPES, CONFINED_AIR_ROWS, VEHICLE_CHECK_ITEMS, VEHICLE_ITEM_NUMBERS, VEHICLE_DAYS, INSPECTION_MODULES, RAC_MODULES,
    SEPARATE_CLUSTERS, SEPARATE_CLUSTER_SITES,
)
from .pdfgen import generate_document, generate_day_checklist, safe_filename
from . import sso
from .help_articles import ARTICLES as HELP_ARTICLES, CATEGORIES as HELP_CATEGORIES, SYNONYMS as HELP_SYNONYMS
from .releases import RELEASES, get_releases, get_version, publish_release, edit_release, delete_release
from .push import vapid_public_key, push_backend_available, send_web_push
from .safety_library import prepare_library

APP_NAME='Safety Plus'
APR_MAX_STEPS=20
REVALIDATION_WINDOW_DAYS=7
BASE_DIR=Path(__file__).resolve().parent
STORAGE_DIR=Path(os.getenv('STORAGE_DIR',str(BASE_DIR.parent/'storage'))).resolve()
PDF_DIR=STORAGE_DIR/'pdfs'; SIG_DIR=STORAGE_DIR/'signatures'; EVIDENCE_DIR=STORAGE_DIR/'evidence'
INFO_DOCS_DIR=BASE_DIR/'info_docs'
PDF_DIR.mkdir(parents=True,exist_ok=True); SIG_DIR.mkdir(parents=True,exist_ok=True); EVIDENCE_DIR.mkdir(parents=True,exist_ok=True)

ABOUT_SERENA_DOCS={
    'politica-sst': {
        'title':'Política de Saúde e Segurança do Trabalho',
        'filename':'Politica_de_SST_PT.pdf',
        'download_name':'Politica_de_SST_Serena.pdf',
    },
    'regras-pela-vida': {
        'title':'Regras pela Vida',
        'filename':'Regras_pela_Vida.pdf',
        'download_name':'Regras_pela_Vida_Serena.pdf',
    },
}

SECURE_COOKIES=os.getenv('SECURE_COOKIES','false').lower()=='true'
APP_SECRET_VALUE=(os.getenv('APP_SECRET') or '').strip()
_INSECURE_APP_SECRETS={'troque-a-chave-do-checklist-serena-v1','troque-a-chave-do-checklist-serena-v2','ALTERE_PARA_UMA_CHAVE_FORTE'}
if not APP_SECRET_VALUE:
    if SECURE_COOKIES:
        raise RuntimeError('APP_SECRET é obrigatório na VPS/produção. Execute o instalador ou configure uma chave forte no .env.')
    APP_SECRET_VALUE=secrets.token_urlsafe(48)
    os.environ['APP_SECRET']=APP_SECRET_VALUE
elif SECURE_COOKIES and APP_SECRET_VALUE in _INSECURE_APP_SECRETS:
    raise RuntimeError('APP_SECRET inseguro/placeholder detectado. Gere uma chave forte antes de iniciar em produção.')

app=FastAPI(title=APP_NAME)
@app.middleware('http')
async def maintenance_mode(request: Request, call_next):
    """Com o modo manutenção ligado, só o DEV usa o sistema."""
    state=ti_tools.maintenance_state(STORAGE_DIR)
    path=request.url.path
    if not state['on'] or path.startswith(('/login','/logout','/sso','/static','/api/session/status','/api/app-version')) or path in {'/sw.js','/manifest.webmanifest','/favicon.ico','/health'}:
        return await call_next(request)
    uid=request.session.get('user_id')
    if uid:
        with SessionLocal() as db:
            u=db.get(User,int(uid)); role=u.role if u else ''
        if role==ROLE_DEV: return await call_next(request)
    msg=state['message'] or 'O sistema está em manutenção. Tente novamente em instantes.'
    if path.startswith('/api') or 'application/json' in (request.headers.get('accept') or ''):
        return JSONResponse({'detail':msg,'maintenance':True},status_code=503,headers={'Retry-After':'300'})
    from html import escape
    body=f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Em manutenção</title></head><body style='font-family:system-ui;background:#f7f4f0;display:grid;place-items:center;min-height:100vh;margin:0'><div style='background:#fff;border:1px solid #ece8e3;border-radius:16px;padding:28px;max-width:440px;text-align:center'><h2 style='margin:0 0 10px'>Sistema em manutenção</h2><p>{escape(msg)}</p><p style='font-size:.85rem;color:#6b6661'>Safety Plus</p><a href='/logout-page' style='display:none'></a></div></body></html>"
    return HTMLResponse(body,status_code=503,headers={'Retry-After':'300','Cache-Control':'no-store'})


from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_VALUE, https_only=SECURE_COOKIES, same_site='lax', max_age=60*60*12)
@app.middleware('http')
async def monitor_requests(request: Request, call_next):
    """Registra tempo/status de cada requisição para a aba Monitoramento do DEV (somente em memória)."""
    path=request.url.path
    if path.startswith('/static'):
        return await call_next(request)
    t0=time.perf_counter()
    try:
        response=await call_next(request)
    except Exception as exc:
        monitor.record(request.method,path,500,(time.perf_counter()-t0)*1000,(request.scope.get('session') or {}).get('user_id'),f'{type(exc).__name__}: {exc}')
        raise
    monitor.record(request.method,path,response.status_code,(time.perf_counter()-t0)*1000,(request.scope.get('session') or {}).get('user_id'))
    return response

app.add_middleware(AuditContextMiddleware)

app.mount('/static',StaticFiles(directory=BASE_DIR/'static'),name='static')
templates=Jinja2Templates(directory=BASE_DIR/'templates')
Base.metadata.create_all(engine)
from .database import ensure_audit_columns
ensure_audit_columns(engine)

# Sessões temporárias para captura de integrante por QR na própria APR.
# O token não contém CPF/dados pessoais e expira automaticamente.
APR_TEAM_QR_SESSIONS: dict[str, dict[str, Any]] = {}
APR_TEAM_QR_TTL_SECONDS = 10 * 60

def _apr_team_qr_cleanup() -> None:
    now=datetime.now(timezone.utc)
    expired=[k for k,v in APR_TEAM_QR_SESSIONS.items() if (now-v.get('created_at',now)).total_seconds()>APR_TEAM_QR_TTL_SECONDS]
    for k in expired: APR_TEAM_QR_SESSIONS.pop(k,None)


ROLE_SUPER_ADMIN='Super Administrador'
ROLE_ADMIN='Administrador'
ROLE_USER='Usuário'
ROLE_DEV='DEV'  # perfil técnico externo: acesso total, oculto das listagens e fora dos fluxos de aprovação
ADMIN_ROLES={ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_DEV}


def _upgrade_legacy_admin_roles():
    # Preserva o acesso global dos administradores já existentes.
    # A versão anterior só possuía o papel Administrador, que enxergava tudo.
    with SessionLocal() as db:
        has_super=db.query(User).filter(User.role==ROLE_SUPER_ADMIN).first()
        if has_super:
            return
        legacy=db.query(User).filter(User.role==ROLE_ADMIN).all()
        if legacy:
            for u in legacy:
                u.role=ROLE_SUPER_ADMIN
            db.commit()

_upgrade_legacy_admin_roles()
custom_docs.load_all(STORAGE_DIR); ti_tools.configure(STORAGE_DIR)

def _repair_admins_without_scope():
    """Corrige perfis Administrador antigos que ficaram sem escopo após a migração.

    A interface atual não permite salvar um Administrador sem Cluster/Site.
    Se um registro legado estiver nessa condição, ele ficaria sem acesso a
    documentos. Para preservar o comportamento anterior, recebe todos os
    escopos disponíveis.
    """
    with SessionLocal() as db:
        admins=db.query(User).filter(User.role==ROLE_ADMIN,User.active==True).all()
        changed=0
        for user in admins:
            has_scope=db.query(UserScope).filter(UserScope.user_id==user.id).first()
            if has_scope:
                continue
            for cluster,sites in SEPARATE_CLUSTER_SITES.items():
                for site in sites:
                    db.add(UserScope(user_id=user.id,cluster=cluster,site=site,created_at=datetime.utcnow()))
            changed+=1
        if changed:
            db.commit()

_repair_admins_without_scope()

def _normalize_inspection_titles():
    """Mantém Kit de Altura e Cinto claramente separados também nos registros antigos."""
    desired={
        'height_kit':DOCUMENT_TITLES.get('height_kit','Inspeção diária antes da subida — Kit de Trabalho em Altura'),
        'safety_belt':DOCUMENT_TITLES.get('safety_belt','Inspeção estrutural — Cinto de Segurança'),
    }
    with SessionLocal() as db:
        changed=False
        for kind,title in desired.items():
            rows=db.query(Document).filter(Document.kind==kind).all()
            for doc in rows:
                if doc.title!=title:
                    doc.title=title; changed=True
        if changed:
            db.commit()

_normalize_inspection_titles()

@app.middleware('http')
async def no_store_private_pages(request: Request, call_next):
    """Evita que o navegador reutilize telas autenticadas depois do logout.

    O Safety Plus opera online; páginas autenticadas não devem permanecer em cache após logout.
    """
    response=await call_next(request)
    content_type=(response.headers.get('content-type') or '').lower()
    if 'text/html' in content_type or request.url.path in {'/login','/logout'}:
        response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']='no-cache'
        response.headers['Expires']='0'
    # Proteções de navegador sem alterar o fluxo dos documentos ou o PWA.
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='SAMEORIGIN'
    response.headers['Permissions-Policy']='camera=(self), microphone=(self), geolocation=()'
    if SECURE_COOKIES:
        response.headers['Strict-Transport-Security']='max-age=31536000'
    return response

@app.get('/sw.js', include_in_schema=False)
def service_worker():
    # A versão vai dentro do arquivo: cada release gera um service worker novo e renova o cache.
    text=(BASE_DIR/'static'/'sw.js').read_text(encoding='utf-8').replace('__APP_VERSION__',get_version(STORAGE_DIR))
    return Response(
        text,
        media_type='application/javascript',
        headers={'Cache-Control':'no-cache, no-store, must-revalidate','Service-Worker-Allowed':'/'},
    )


def _maintenance_notice() -> dict|None:
    """Aviso de parada programada para o banner dos usuários (None se não houver)."""
    sch=ti_tools.maintenance_state(STORAGE_DIR).get('schedule')
    if not sch: return None
    return {'message':sch.get('message',''),'start_ts':sch.get('start_ts'),'end_ts':sch.get('end_ts'),
            'start_label':sch.get('start_label',''),'end_label':sch.get('end_label',''),'popup':sch.get('popup',True)}


@app.get('/api/app-version', include_in_schema=False)
def app_version_api():
    return JSONResponse({'version':get_version(STORAGE_DIR),'maintenance':_maintenance_notice()},headers={'Cache-Control':'no-store'})


@app.get('/novidades')
def release_notes_page(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    return templates.TemplateResponse(request,'release_notes.html',context(request,releases=get_releases(STORAGE_DIR)))

APP_TIMEZONE=os.getenv('APP_TIMEZONE','America/Sao_Paulo').strip() or 'America/Sao_Paulo'
try:
    LOCAL_TZ=ZoneInfo(APP_TIMEZONE)
except ZoneInfoNotFoundError:
    # Fallback seguro para o horário de Brasília caso o banco de fusos não esteja disponível.
    LOCAL_TZ=timezone(timedelta(hours=-3))

def local_now() -> datetime:
    # Mantém timestamps sem tzinfo no banco atual, mas sempre calculados no fuso configurado.
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)

def local_today() -> date:
    return datetime.now(LOCAL_TZ).date()

def now(): return local_now()


NOTIFICATION_TYPES = {
    'signatures': {'label':'Assinaturas', 'kinds':['apr_participant_signature','apr_execution_member_signature','apr_creator_signature','apr_creator_signatures_complete','apr_creator_daily_signature']},
    'pt_pending': {'label':'PTs pendentes', 'prefixes':['pt_pending'], 'kinds':['pt_closure_pending']},
    'approvals': {'label':'Aprovações pendentes', 'kinds':['apr_approval']},
    'approved': {'label':'Documentos aprovados', 'kinds':['apr_creator_approved']},
    'rejected': {'label':'Documentos reprovados', 'kinds':['apr_creator_rejected']},
}
NOTIFICATION_PREFS_FILE=STORAGE_DIR/'notification_preferences.json'

def _notification_category(kind: str) -> str:
    k=clean(kind).lower()
    for key,cfg in NOTIFICATION_TYPES.items():
        if k in [str(x).lower() for x in cfg.get('kinds',[])]: return key
        if any(k.startswith(str(x).lower()) for x in cfg.get('prefixes',[])): return key
    return 'other'

def _load_notification_preferences() -> dict:
    default={'global':{k:True for k in NOTIFICATION_TYPES},'users':{}}
    try:
        if NOTIFICATION_PREFS_FILE.exists():
            raw=json.loads(NOTIFICATION_PREFS_FILE.read_text(encoding='utf-8'))
            if isinstance(raw,dict):
                default['global'].update(raw.get('global') or {})
                default['users']=raw.get('users') or {}
    except Exception: pass
    return default

def _save_notification_preferences(data: dict) -> None:
    NOTIFICATION_PREFS_FILE.parent.mkdir(parents=True,exist_ok=True)
    tmp=NOTIFICATION_PREFS_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(NOTIFICATION_PREFS_FILE)

def _notification_enabled(user_id: int, kind: str) -> bool:
    cat=_notification_category(kind)
    if cat=='other': return True
    prefs=_load_notification_preferences()
    if not bool(prefs.get('global',{}).get(cat,True)): return False
    up=(prefs.get('users',{}).get(str(user_id)) or {})
    return bool(up.get(cat,True))

def _notification_title(kind: str) -> str:
    k=clean(kind).lower()
    if k in {'apr_participant_signature','apr_execution_member_signature'}: return 'Assinatura necessária'
    if k=='apr_approval': return 'Aprovação pendente'
    if k.startswith('pt_pending') or k=='pt_closure_pending': return 'PT pendente'
    if k=='apr_creator_approved': return 'APR aprovada'
    if k=='apr_creator_rejected': return 'APR reprovada'
    if k=='apr_creator_signature': return 'Nova rubrica na APR'
    if k=='apr_creator_signatures_complete': return 'Assinaturas concluídas'
    if k=='apr_creator_daily_signature': return 'Assinatura diária registrada'
    return 'Safety Plus'


def _push_notification_ids_sync(notification_ids: list[int]) -> None:
    """Entrega no celular/navegador as notificações persistidas no banco.

    Web Push é complementar ao sino interno. Qualquer falha de push fica registrada
    na inscrição e nunca desfaz a ação que originou a notificação.
    """
    ids=[]
    for raw in notification_ids or []:
        try: nid=int(raw)
        except Exception: continue
        if nid and nid not in ids: ids.append(nid)
    if not ids or not push_backend_available():
        return
    try:
        with SessionLocal() as db:
            notes=db.query(Notification).filter(Notification.id.in_(ids)).all()
            for note in notes:
                user=db.get(User,note.recipient_user_id)
                if not user or not user.active: continue
                doc=db.get(Document,note.document_id)
                if doc and not user_can_access_document(user,doc):
                    continue
                try:
                    target=_notification_target(note,doc,user)
                except Exception:
                    target='/notifications'
                payload={
                    'title':_notification_title(note.kind),
                    'body':note.message,
                    'url':f'/notifications/{note.id}/open',
                    'notification_id':note.id,
                    'tag':f'safety-plus-{note.kind}-{note.document_id}',
                    'icon':'/static/icons/safety-plus-icon-192-v361831.png',
                    'badge':'/static/icons/safety-plus-favicon-64-v361831.png',
                }
                subscriptions=(db.query(PushSubscription)
                    .filter(PushSubscription.user_id==user.id,PushSubscription.active==True)
                    .all())
                for sub in subscriptions:
                    ok,gone,detail=send_web_push(sub,payload,STORAGE_DIR)
                    if ok:
                        sub.last_success_at=now(); sub.last_error=''; sub.updated_at=now()
                    else:
                        sub.last_error=detail; sub.updated_at=now()
                        if gone: sub.active=False
            db.commit()
    except Exception:
        # O fluxo operacional nunca pode falhar porque um serviço de push está fora.
        pass


def _queue_push_notification_ids(notification_ids: list[int]) -> None:
    ids=[int(x) for x in (notification_ids or []) if str(x or '').isdigit()]
    if not ids: return
    try:
        threading.Thread(target=_push_notification_ids_sync,args=(ids,),daemon=True,name='safety-plus-push').start()
    except Exception:
        pass


def _add_notification(db, *, recipient_user_id: int, document_id: int, kind: str, message: str) -> Notification|None:
    if not _notification_enabled(recipient_user_id,kind):
        return None
    note=Notification(
        recipient_user_id=recipient_user_id,document_id=document_id,kind=kind,
        message=message,read=False,created_at=now(),
    )
    db.add(note); db.flush()
    return note

def flash(request: Request, message: str, level: str='info'):
    request.session.setdefault('_flashes',[]).append({'message':message,'level':level})

def pop_flashes(request: Request):
    return request.session.pop('_flashes',[])

def context(request: Request, **kwargs):
    user=current_user(request)
    notification_count=0
    if user:
        with SessionLocal() as db:
            unread=db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.read==False).all()
            for note in unread:
                doc=db.get(Document,note.document_id)
                if not doc or user_can_access_document(user,doc):
                    notification_count+=1
    access_scope_labels=[]
    system_notice=ti_tools.load_settings(STORAGE_DIR).get('notice','')
    custom_apr_links=[(c.get('title',''),f'/rac/{k}/new') for k,c in RAC_MODULES.items() if c.get('custom') and c.get('placement')=='apr']
    if user:
        if is_super_admin(user):
            access_scope_labels=['Todos os Clusters/Sites']
        elif user.role==ROLE_ADMIN:
            access_scope_labels=[f'{c} - {st}' for c,st in scopes_for_user(user)]
    today=local_today()
    max_7_days=today+timedelta(days=REVALIDATION_WINDOW_DAYS-1)
    return {'request':request,'user':user,'app_name':APP_NAME,'app_version':get_version(STORAGE_DIR),'maint_notice':_maintenance_notice(),'app_release':get_releases(STORAGE_DIR)[0],'csrf_token':csrf_token(request),'flashes':pop_flashes(request),'view_cluster':(clean(request.session.get('view_cluster')) if user and user.role in (ROLE_SUPER_ADMIN,ROLE_DEV) else ''),'view_cluster_options':(list(SEPARATE_CLUSTERS) if user and user.role in (ROLE_SUPER_ADMIN,ROLE_DEV) else []),'notification_count':notification_count,'access_scope_labels':access_scope_labels,'custom_apr_links':custom_apr_links,'system_notice':system_notice,'apr_hazard_options':HAZARD_OPTIONS,'apr_risk_catalog':RISK_CATALOG,'today_input':today.strftime('%Y-%m-%d'),'apr_max_date_input':max_7_days.strftime('%Y-%m-%d'),**kwargs}

def pdf_preview_response(request: Request, path: Path):
    """Renderiza paginas do PDF como PNG para o visualizador interno.

    Navegadores moveis nem sempre exibem application/pdf dentro de iframe.
    A pre-visualizacao por imagem usa o PyMuPDF que ja faz parte do Safety Plus,
    preserva as mesmas regras de permissao da rota original e nao depende de
    plugins/CDNs externos.
    """
    wants_meta=request.query_params.get('preview_meta')=='1'
    page_raw=clean(request.query_params.get('preview_page'))
    if not wants_meta and not page_raw:
        return None
    path=Path(path)
    if not path.exists() or not path.is_file() or path.suffix.lower()!='.pdf':
        raise HTTPException(404,'PDF não encontrado para visualização.')
    # Cache em disco: renderizar PNG a 2,5x é caro; com muita gente abrindo o mesmo PDF, só renderiza 1 vez.
    try:
        st=path.stat(); ckey=hashlib.sha1(f'{path.resolve()}|{st.st_mtime_ns}|{st.st_size}'.encode()).hexdigest()
    except Exception: ckey=''
    cache_dir=STORAGE_DIR/'cache'/'preview'
    if ckey and page_raw and page_raw.isdigit():
        cf=cache_dir/f'{ckey}_{int(page_raw)}.png'
        if cf.exists():
            return Response(cf.read_bytes(),media_type='image/png',headers={'Cache-Control':'private, max-age=300','X-Content-Type-Options':'nosniff'})
    try:
        pdf=fitz.open(path)
    except Exception as exc:
        raise HTTPException(500,f'Não foi possível abrir o PDF para visualização: {exc}')
    try:
        total=pdf.page_count
        if wants_meta:
            return JSONResponse({'ok':True,'pages':total},headers={'Cache-Control':'private, no-store'})
        try:
            page_number=int(page_raw)
        except (TypeError,ValueError):
            raise HTTPException(400,'Página inválida.')
        if page_number<1 or page_number>total:
            raise HTTPException(404,'Página do PDF não encontrada.')
        page=pdf.load_page(page_number-1)
        # 2.5x: texto nítido em celulares de alta densidade (zoom incluso).
        pix=page.get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False)
        payload=pix.tobytes('png')
        if ckey:
            try:
                cache_dir.mkdir(parents=True,exist_ok=True); (cache_dir/f'{ckey}_{page_number}.png').write_bytes(payload)
                if secrets.randbelow(50)==0:
                    cutoff=time.time()-86400
                    for old in cache_dir.glob('*.png'):
                        if old.stat().st_mtime<cutoff: old.unlink(missing_ok=True)
            except Exception: pass
    finally:
        pdf.close()
    return StreamingResponse(
        io.BytesIO(payload),media_type='image/png',
        headers={'Cache-Control':'private, max-age=300','X-Content-Type-Options':'nosniff'},
    )

def active_admins(cluster: str='', site: str=''):
    with SessionLocal() as db:
        rows=(db.query(User).filter(User.role==ROLE_SUPER_ADMIN,User.active==True)
              .order_by(User.full_name,User.username).all())
        result=[]
        for u in rows:
            allowed=bool(u.role==ROLE_SUPER_ADMIN or not cluster or admin_scope_allows_location(u,cluster,site))
            if not allowed:
                continue
            if u.role==ROLE_SUPER_ADMIN:
                u.scope_keys=['*']
            else:
                u.scope_keys=[f'{c} - {st}' for c,st in user_scope_pairs(u.id) if st]
            db.expunge(u); result.append(u)
        return result

def available_approvers_for_creator(user: User) -> list[User]:
    rows=active_admins()
    if user.role!=ROLE_ADMIN:
        return rows
    mine=set(scopes_for_user(user))
    out=[]
    for admin in rows:
        if is_super_admin(admin):
            out.append(admin); continue
        theirs=set(user_scope_pairs(admin.id))
        if mine.intersection(theirs):
            out.append(admin)
    return out

def notify_apr_approval(doc: Document, approvers: list[User], requester: User):
    requester_name=requester.full_name or requester.username
    unique=[]
    seen=set()
    for approver in approvers:
        if approver.id in seen: continue
        seen.add(approver.id)
        unique.append(approver)
    push_ids=[]
    with SessionLocal() as db:
        db.query(Notification).filter(Notification.document_id==doc.id,Notification.kind=='apr_approval').delete(synchronize_session=False)
        for approver in unique:
            note=_add_notification(db,recipient_user_id=approver.id,document_id=doc.id,kind='apr_approval',message=f'{doc_reference_code(doc)} enviada por {requester_name} para sua aprovação.')
            
            if note: push_ids.append(note.id)
        db.commit()
    _queue_push_notification_ids(push_ids)

def mark_approval_notification_read(user_id: int, doc_id: int):
    with SessionLocal() as db:
        rows=db.query(Notification).filter(Notification.recipient_user_id==user_id,Notification.document_id==doc_id,Notification.kind=='apr_approval',Notification.read==False).all()
        for n in rows:
            n.read=True; n.read_at=now()
        if rows: db.commit()


def notify_document_creator(doc: Document, kind: str, message: str, *, replace: bool=False):
    """Envia ao criador do documento uma atualização do fluxo e dispara Web Push."""
    try:
        push_ids=[]
        with SessionLocal() as db:
            creator=db.get(User,doc.created_by)
            if not creator or not creator.active:
                return
            if replace:
                db.query(Notification).filter(
                    Notification.recipient_user_id==creator.id,
                    Notification.document_id==doc.id,
                    Notification.kind==kind,
                ).delete(synchronize_session=False)
            note=_add_notification(db,recipient_user_id=creator.id,document_id=doc.id,kind=kind,message=message)
            
            if note: push_ids.append(note.id)
            db.commit()
        _queue_push_notification_ids(push_ids)
    except Exception:
        # A notificação é complementar e não pode desfazer uma assinatura/aprovação.
        pass


def notify_user(user_id: int, doc: Document, kind: str, message: str, *, replace: bool=False):
    """Envia uma notificação direta a um usuário específico e dispara Web Push."""
    try:
        push_ids=[]
        with SessionLocal() as db:
            target=db.get(User,user_id)
            if not target or not target.active:
                return
            if replace:
                db.query(Notification).filter(
                    Notification.recipient_user_id==target.id,
                    Notification.document_id==doc.id,
                    Notification.kind==kind,
                ).delete(synchronize_session=False)
            note=_add_notification(db,recipient_user_id=target.id,document_id=doc.id,kind=kind,message=message)
            
            if note: push_ids.append(note.id)
            db.commit()
        _queue_push_notification_ids(push_ids)
    except Exception:
        pass


def audit(user_id: int|None, action: str, detail: str=''):
    with SessionLocal() as db:
        db.add(AuditLog(user_id=user_id,action=action,detail=detail[:50000],created_at=now())); db.commit()

# Campos técnicos que não ajudam na leitura do histórico administrativo.
_AUDIT_TECHNICAL_KEYS={
    '_show_completion_issues','participant_id','participant_user_id','signed_by_user_id',
    'participant_signatures_requested_by_id','submitted_by_id','approved_by_id',
    'approver_user_id','approver_extra_user_ids','linked_permit_ids'
}

def _audit_flatten(value: Any, prefix: str='') -> dict[str,Any]:
    out={}
    if isinstance(value,dict):
        for k,v in value.items():
            if k in _AUDIT_TECHNICAL_KEYS or any(term in str(k).lower() for term in ('password','passwd','secret','token','csrf')): continue
            p=f'{prefix}.{k}' if prefix else str(k)
            out.update(_audit_flatten(v,p))
    elif isinstance(value,list):
        for i,v in enumerate(value):
            p=f'{prefix}.{i}' if prefix else str(i)
            out.update(_audit_flatten(v,p))
    else:
        out[prefix]=value
    return out

def _audit_field_label(path: str) -> str:
    direct={
        'full_name':'Nome completo','role':'Perfil','active':'Acesso ativo',
        'cluster':'Cluster / Site','site':'Site','activity':'Atividade','objective':'Objetivo','severity':'Severidade geral',
        'apr_date':'Data da APR','apr_time':'Hora da APR','leader_phone':'Telefone líder','sst_phone':'Telefone SST',
        'radio_channel':'Canal de rádio','critical_activity':'Atividade crítica','observations':'Observações',
        'comments':'Comentários','open_date':'Data de abertura','open_time':'Hora de abertura','close_date':'Data de fechamento',
        'close_time':'Hora de fechamento','model':'Modelo','operator':'Motorista / Operador','month':'Mês','year':'Ano',
        'inspection_date':'Data da inspeção','contractor':'Contratada','base':'Base','status':'Status'
    }
    if path in direct: return direct[path]
    m=re.fullmatch(r'steps\.(\d+)\.(stage|hazard|risk|severity|control)',path)
    if m:
        labels={'stage':'Etapa','hazard':'Perigo','risk':'Risco','severity':'Severidade','control':'Medida de controle'}
        return f'Etapa {int(m.group(1))+1} — {labels[m.group(2)]}'
    m=re.fullmatch(r'checklist\.(\d+)',path)
    if m: return f'Checklist {int(m.group(1))+1:02d}'
    m=re.fullmatch(r'workers\.(\d+)\.(cpf|company|worker|role|date|signature|signature_image|signature_status|signed_at|signed_by_name)',path)
    if m:
        labels={'cpf':'CPF','company':'Empresa','worker':'Trabalhador','role':'Função / cargo','date':'Data da assinatura','signature':'Rubrica','signature_image':'Assinatura / rubrica','signature_status':'Status da assinatura','signed_at':'Assinado em','signed_by_name':'Assinado por'}
        return f'Integrante {int(m.group(1))+1} — {labels[m.group(2)]}'
    m=re.fullmatch(r'approvals\.(\d+)\.(name|role|start|end|signature|signature_image)',path)
    if m:
        labels={'name':'Nome','role':'Função','start':'Início','end':'Fim','signature':'Rubrica','signature_image':'Assinatura / rubrica'}
        return f'Aprovação {int(m.group(1))+1} — {labels[m.group(2)]}'
    m=re.fullmatch(r'days\.([^.]+)\.answers\.(\d+)',path)
    if m: return f'{m.group(1)} — Item {int(m.group(2))+1:02d}'
    m=re.fullmatch(r'days\.([^.]+)\.(signature_image|visto)',path)
    if m: return f'{m.group(1)} — Assinatura / rubrica'
    m=re.fullmatch(r'periods\.([^.]+)\.answers\.(\d+)',path)
    if m: return f'{m.group(1)} — Item {int(m.group(2))+1:02d}'
    m=re.fullmatch(r'periods\.([^.]+)\.(date|signature_image|visto)',path)
    if m: return f'{m.group(1)} — '+('Data' if m.group(2)=='date' else 'Assinatura / rubrica')
    m=re.fullmatch(r'rows\.(\d+)\.(answer|evidence|action)',path)
    if m:
        labels={'answer':'Resposta','evidence':'Evidência','action':'Ação corretiva'}
        return f'Item {int(m.group(1))+1:02d} — {labels[m.group(2)]}'
    m=re.fullmatch(r'nonconformities\.(\d+)\.(item|action|responsible|date)',path)
    if m:
        labels={'item':'Item','action':'Ação','responsible':'Responsável','date':'Data'}
        return f'Não conformidade {int(m.group(1))+1} — {labels[m.group(2)]}'
    # Rótulo genérico legível para os demais campos.
    return path.replace('_',' ').replace('.',' › ').strip().title()

def _audit_display_value(path: str, value: Any) -> str:
    if str(value or '').startswith('data:'):
        return 'Arquivo registrado'
    if path.endswith('signature_image'):
        return 'Registrada' if clean(value) else 'Não registrada'
    if path.endswith('.cpf') or path=='cpf':
        return cpf_format(value) if clean(value) else ''
    if isinstance(value,bool): return 'Sim' if value else 'Não'
    text=clean(value)
    if len(text)>700: text=text[:697]+'...'
    return text

def document_change_rows(before: dict, after: dict) -> list[dict]:
    a=_audit_flatten(before or {}); b=_audit_flatten(after or {})
    rows=[]
    for path in sorted(set(a)|set(b)):
        old=a.get(path,''); new=b.get(path,'')
        if old==new: continue
        old_text=_audit_display_value(path,old); new_text=_audit_display_value(path,new)
        if old_text==new_text: continue
        rows.append({'field':_audit_field_label(path),'before':old_text or '—','after':new_text or '—'})
    return rows

def audit_admin_document_change(admin: User, doc: Document, before: dict, after: dict, changes: list[dict]):
    payload={
        'document_id':doc.id,'code':doc_reference_code(doc),'kind':doc.kind,'title':doc.title,
        'administrator':admin.full_name or admin.username,'username':admin.username,
        'changes':changes,
    }
    audit(admin.id,'alterar_documento_admin',json.dumps(payload,ensure_ascii=False))

def clean(s: Any) -> str: return str(s or '').strip()

def is_super_admin(user: User|None) -> bool:
    return bool(user and user.role in {ROLE_SUPER_ADMIN, ROLE_DEV})

def is_admin_user(user: User|None) -> bool:
    return bool(user and user.role in ADMIN_ROLES)

def can_approve_any(user: User|None) -> bool:
    """Administrador e Super Administrador podem aprovar/reprovar qualquer APR, mesmo direcionada a outro responsável."""
    return bool(user and user.role in {ROLE_SUPER_ADMIN,ROLE_ADMIN})

def normalize_location_pair(cluster: Any, site: Any='') -> tuple[str,str]:
    cluster=clean(cluster); site=clean(site)
    if cluster in SEPARATE_CLUSTER_SITES:
        return cluster,site
    for group,sites in SEPARATE_CLUSTER_SITES.items():
        prefix=group+' - '
        if cluster.startswith(prefix):
            inferred=cluster[len(prefix):].strip()
            if not site and inferred in sites:
                site=inferred
            return group,site
    return cluster,site

def user_scope_pairs(user_id: int) -> list[tuple[str,str]]:
    with SessionLocal() as db:
        rows=(db.query(UserScope).filter(UserScope.user_id==user_id)
              .order_by(UserScope.cluster,UserScope.site).all())
        pairs=[(clean(r.cluster),clean(r.site)) for r in rows if clean(r.cluster)]
        if pairs: return pairs
        # Sem escopo próprio: vale o cluster/site do cadastro de colaborador vinculado à conta.
        part=db.query(Participant).filter(Participant.user_id==user_id,Participant.active==True).first()
        if part and clean(part.cluster) in SEPARATE_CLUSTER_SITES:
            site=clean(part.site)
            return [(clean(part.cluster),site if site in SEPARATE_CLUSTER_SITES[clean(part.cluster)] else '')]
        return []

def scopes_for_user(user: User) -> list[tuple[str,str]]:
    cached=getattr(user,'_scope_pairs_cache',None)
    if cached is None:
        cached=user_scope_pairs(user.id)
        try: user._scope_pairs_cache=cached
        except Exception: pass
    return cached

def admin_scope_allows_location(user: User, cluster: Any, site: Any='') -> bool:
    if is_super_admin(user):
        return True
    if user.role!=ROLE_ADMIN:
        return False
    target_cluster,target_site=normalize_location_pair(cluster,site)
    if not target_cluster:
        return False
    for scope_cluster,scope_site in scopes_for_user(user):
        if scope_cluster!=target_cluster:
            continue
        if not target_site or not scope_site or scope_site==target_site:
            return True
    return False

def admin_scope_allows_document(user: User, doc: Document) -> bool:
    if is_super_admin(user):
        return True
    if user.role!=ROLE_ADMIN:
        return False
    cluster,site=normalize_location_pair(doc.cluster,doc.site)
    if not cluster:
        # Um rascunho criado pelo próprio administrador ainda sem local definido
        # precisa continuar acessível para que ele consiga concluí-lo.
        return doc.created_by==user.id
    return admin_scope_allows_location(user,cluster,site)

def allowed_locations_for_admin(user: User) -> dict[str,list[str]]:
    if is_super_admin(user) or user.role!=ROLE_ADMIN:
        return {k:list(v) for k,v in SEPARATE_CLUSTER_SITES.items()}
    scopes=scopes_for_user(user)
    result: dict[str,list[str]]={}
    for cluster,site in scopes:
        if cluster not in SEPARATE_CLUSTER_SITES:
            continue
        if not site:
            result[cluster]=list(SEPARATE_CLUSTER_SITES[cluster])
        elif site in SEPARATE_CLUSTER_SITES[cluster]:
            result.setdefault(cluster,[])
            if site not in result[cluster]:
                result[cluster].append(site)
    return result

def default_location_for(user: User) -> tuple[str,str]:
    """Cluster/site que entram automaticamente em documentos novos.

    Super Administrador e DEV: cluster escolhido no seletor do topo.
    Demais perfis: cluster do cadastro de colaborador (participante) e, se não
    houver, o escopo atribuído, desde que seja um só.
    """
    if user.role in (ROLE_SUPER_ADMIN,ROLE_DEV):
        vc=clean(VIEW_CLUSTER.get())
        return (vc,'') if vc in SEPARATE_CLUSTER_SITES else ('','')
    cluster=site=''
    try:
        with SessionLocal() as db:
            part=db.query(Participant).filter(Participant.user_id==user.id,Participant.active==True).first()
            if part and part.cluster in SEPARATE_CLUSTER_SITES:
                cluster=part.cluster; site=part.site if part.site in SEPARATE_CLUSTER_SITES[cluster] else ''
    except Exception:
        cluster=site=''
    if cluster and (user.role!=ROLE_ADMIN or admin_scope_allows_location(user,cluster,site)):
        return cluster,site
    allowed=allowed_locations_for_admin(user) if user.role==ROLE_ADMIN else {}
    if not allowed:
        pairs=[(c,st) for c,st in scopes_for_user(user) if c in SEPARATE_CLUSTER_SITES]
        for c,st in pairs: allowed.setdefault(c,[]); allowed[c]=allowed[c]+([st] if st else list(SEPARATE_CLUSTER_SITES[c]))
    if len(allowed)==1:
        c=next(iter(allowed)); sites=list(dict.fromkeys(allowed[c]))
        return c,(sites[0] if len(sites)==1 else '')
    return '',''

def prefill_location(user: User, data: dict, *, combined_key: str='', cluster_key: str='cluster', site_key: str='site', options: list[str]|None=None) -> dict:
    """Preenche cluster (e site) num documento novo. Não sobrescreve o que já veio preenchido."""
    cluster,site=default_location_for(user)
    if not cluster: return data
    if combined_key:
        if clean(data.get(combined_key)): return data
        value=f'{cluster} - {site}' if site else ''
        if value and (options is None or value in options): data[combined_key]=value
        return data
    if not clean(data.get(cluster_key)):
        data[cluster_key]=cluster
        if site_key and not clean(data.get(site_key)) and site: data[site_key]=site
    return data

def combined_clusters_for_user(user: User) -> list[str]:
    if user.role!=ROLE_ADMIN:
        return list(CLUSTERS)
    allowed=allowed_locations_for_admin(user)
    return [f'{cluster} - {site}' for cluster,sites in allowed.items() for site in sites]

def separate_clusters_for_user(user: User) -> tuple[list[str],dict[str,list[str]]]:
    if user.role!=ROLE_ADMIN:
        return list(SEPARATE_CLUSTERS),{k:list(v) for k,v in SEPARATE_CLUSTER_SITES.items()}
    allowed=allowed_locations_for_admin(user)
    return list(allowed.keys()),allowed

def normalize_apr_severity(value: Any) -> str:
    """Normaliza severidade da APR para A/B/C, mantendo compatibilidade com dados antigos."""
    raw=clean(value).upper()
    return {'ALTO':'A','MÉDIO':'B','MEDIO':'B','BAIXO':'C','A':'A','B':'B','C':'C'}.get(raw,'')

def _normalize_multi_step_values(raw_values: Any, legacy_value: Any='') -> list[str]:
    """Normaliza seleção múltipla de perigo/risco preservando APRs antigas."""
    values=[]
    if isinstance(raw_values,(list,tuple,set)):
        candidates=list(raw_values)
    elif clean(raw_values):
        candidates=[raw_values]
    elif clean(legacy_value):
        candidates=[legacy_value]
    else:
        candidates=[]
    for raw in candidates:
        value=clean(raw)
        if value and value not in values:
            values.append(value)
    return values

def clean_single_line(s: Any) -> str:
    """Normaliza texto de cadastro sem remover acentos ou caracteres usuais."""
    return re.sub(r'\s+', ' ', clean(s))

def cpf_digits(value: Any) -> str:
    return re.sub(r'\D','',clean(value))[:11]

def cpf_is_valid(value: Any) -> bool:
    """Validação operacional do cadastro.

    O Safety Plus usa o CPF principalmente como identificador do participante.
    Para evitar bloqueios por pontuação, colagem ou divergência de dígito
    verificador no cadastro legado, exigimos somente os 11 algarismos.
    A máscara visual continua sendo aplicada automaticamente.
    """
    return len(cpf_digits(value))==11

def cpf_format(value: Any) -> str:
    cpf=cpf_digits(value)
    if len(cpf)!=11: return cpf
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'

def cpf_mask(value: Any) -> str:
    cpf=cpf_digits(value)
    if len(cpf)!=11: return '***.***.***-**'
    return f'***.***.***-{cpf[-2:]}'

def cpf_hash(value: Any) -> str:
    """Hash interno do CPF com o segredo do servidor."""
    digits=cpf_digits(value)
    if len(digits)!=11: return ''
    salt=APP_SECRET_VALUE
    return hashlib.sha256(f'{salt}:{digits}'.encode('utf-8')).hexdigest()

def parse_date_br(value: str) -> date|None:
    value=clean(value)
    if not value: return None
    for fmt in ('%Y-%m-%d','%d/%m/%Y'):
        try: return datetime.strptime(value,fmt).date()
        except ValueError: pass
    raise ValueError('Data inválida')

def br_date(value: str) -> str:
    d=parse_date_br(value)
    return d.strftime('%d/%m/%Y') if d else ''

def date_input(value: str) -> str:
    try:
        d=parse_date_br(value); return d.strftime('%Y-%m-%d') if d else ''
    except Exception: return ''

def validate_dates(data: dict, pairs=(('open_date','abertura'),('close_date','fechamento')), old: dict|None=None):
    today=local_today(); parsed={}; old=old or {}
    for key,label in pairs:
        raw=clean(data.get(key))
        if not raw: continue
        d=parse_date_br(raw); parsed[key]=d
        previous=clean(old.get(key))
        unchanged=False
        if previous:
            try: unchanged=parse_date_br(previous)==d
            except Exception: unchanged=False
        if d<today and not unchanged:
            raise ValueError(f'A data de {label} ({d.strftime("%d/%m/%Y")}) não pode ser retroativa.')
    if 'open_date' in parsed and 'close_date' in parsed:
        ot=clean(data.get('open_time')) or '00:00'; ct=clean(data.get('close_time')) or '00:00'
        od=datetime.combine(parsed['open_date'],datetime.strptime(ot,'%H:%M').time()); cd=datetime.combine(parsed['close_date'],datetime.strptime(ct,'%H:%M').time())
        if cd<od: raise ValueError('A data/hora de fechamento não pode ser anterior à abertura.')

_CODE_LOCK=threading.Lock()

def _next_code_in_db(db, kind: str) -> str:
    prefix=PREFIXES[kind]; year=now().year; pattern=f'{prefix}-{year}-%'
    rows=db.query(Document.code).filter(Document.code.like(pattern)).all()
    maxn=0
    for (code,) in rows:
        try: maxn=max(maxn,int(code.rsplit('-',1)[-1]))
        except Exception: pass
    return f'{prefix}-{year}-{maxn+1:04d}'

def next_code(kind: str) -> str:
    # Prévia para exibição no formulário. Na criação efetiva, save_doc reserva
    # novamente o código dentro da transação para evitar colisão multiusuário.
    with SessionLocal() as db:
        return _next_code_in_db(db,kind)

def _migrate_loto_removed_items(data: dict) -> dict:
    """V36.18.35: itens 8 a 21 do LOTO foram removidos. Registros antigos (31 linhas)
    perdem as linhas 8 a 21 para que as respostas e fotos continuem alinhadas aos itens atuais."""
    rows=data.get('rows')
    if isinstance(rows,list) and len(rows)>17 and not data.get('loto_items_v2'):
        data['rows']=rows[:7]+rows[21:]
        data['loto_items_v2']='1'
    return data

def doc_data(doc: Document|None) -> dict:
    if not doc: return {}
    try: data=json.loads(doc.data_json or '{}')
    except Exception: return {}
    if getattr(doc,'kind','')=='loto' and isinstance(data,dict):
        data=_migrate_loto_removed_items(data)
    return data

def _usina_slug(value: Any) -> str:
    """Transforma o nome da usina/site em uma referência curta para o código."""
    text=clean(value)
    if not text: return ''
    text=unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode('ascii')
    text=re.sub(r'[^A-Za-z0-9]+','-',text).strip('-').upper()
    return text[:42]

def _site_from_combined(value: Any) -> str:
    text=clean(value)
    if ' - ' in text:
        return text.split(' - ',1)[1].strip()
    return text

def document_usina_reference(kind: str, data: dict|None=None, cluster: str='', site: str='') -> str:
    """Obtém a referência de usina/parque/site sem alterar o identificador interno."""
    data=dict(data or {})
    kind=clean(kind)
    if kind=='apr':
        raw=_site_from_combined(data.get('cluster') or cluster)
    elif kind=='hoist':
        raw=_site_from_combined(data.get('cluster_site') or cluster)
    elif kind=='light_vehicle':
        raw=_site_from_combined(data.get('cluster') or cluster)
    elif kind=='climber_assist':
        raw=clean(data.get('park')) or _site_from_combined(data.get('cluster') or cluster)
    else:
        raw=clean(data.get('site')) or clean(site) or _site_from_combined(data.get('cluster') or cluster)
    return _usina_slug(raw)

def data_reference_code(kind: str, data: dict|None=None, cluster: str='', site: str='') -> str:
    """Exibe TIPO-USINA-ANO-NÚMERO mantendo ano/número originais."""
    data=dict(data or {})
    raw=clean(data.get('code'))
    if not raw: return raw
    prefix=PREFIXES.get(kind,'')
    if not prefix: return raw
    m=re.fullmatch(rf'{re.escape(prefix)}(?:-[A-Z0-9-]+)?-(\d{{4}})-(\d+)',raw.upper())
    if not m: return raw
    ref=document_usina_reference(kind,data,cluster,site)
    if not ref: return raw
    return f'{prefix}-{ref}-{m.group(1)}-{m.group(2)}'

def doc_reference_code(doc: Document|None) -> str:
    if not doc: return ''
    data=doc_data(doc)
    if not data.get('code'): data['code']=doc.code
    return data_reference_code(doc.kind,data,doc.cluster,doc.site) or doc.code

def document_company_search_text(doc: Document|None) -> str:
    if not doc: return ''
    try: data=doc_data(doc)
    except Exception: data={}
    values=[]
    for key in ('contractor','company','company_name','empresa','contratada'):
        value=clean(data.get(key))
        if value: values.append(value)
    for worker in (data.get('workers') or data.get('participants') or []):
        if isinstance(worker,dict):
            value=clean(worker.get('company') or worker.get('empresa'))
            if value: values.append(value)
    return ' '.join(dict.fromkeys(values))

# Disponível em todos os templates para mostrar o código com a referência da usina.
templates.env.globals['doc_reference_code']=doc_reference_code
def _ext_res_json():
    from .external_resources import resources_json_map
    return json.dumps(resources_json_map(STORAGE_DIR,CLUSTERS),ensure_ascii=False)
templates.env.globals['ext_res_json']=_ext_res_json
templates.env.globals['data_reference_code']=data_reference_code


def document_open_url(doc: Document|None, user: User|None=None) -> str:
    # Rota direta do documento, sem depender do redirecionamento /document/{id}.
    if not doc:
        return '/'
    if doc.status=='Finalizada':
        return f'/document/{doc.id}/pdf'
    if doc.kind=='apr':
        if doc.status=='Aguardando aprovação' and user and is_admin_user(user):
            data=doc_data(doc)
            allowed=_approver_ids_for_data(data)
            if not allowed or user.id in allowed or can_approve_any(user):
                return f'/apr/{doc.id}/aprovar'
        return f'/apr/{doc.id}/edit'
    if doc.kind=='vehicle':
        return f'/vehicle/{doc.id}/edit'
    if doc.kind=='safety_moment':
        return f'/momento-seguranca/{doc.id}/edit'
    if doc.kind in INSPECTION_MODULES:
        return f'/inspection/{doc.kind}/{doc.id}/edit'
    if doc.kind in MODULES:
        return f'/permit/{doc.kind}/{doc.id}/edit'
    if doc.kind in RAC_MODULES:
        return f'/rac/{doc.kind}/{doc.id}/edit'
    return f'/document/{doc.id}'

templates.env.globals['document_open_url']=document_open_url

def inspection_result(doc: Document) -> str:
    """APTO / INAPTO / '' para o histórico (somente inspeções; ''=não se aplica ou sem respostas)."""
    try:
        data=doc_data(doc)
        if doc.kind=='vehicle':
            ans=[a for info in (data.get('days') or {}).values() for a in (info.get('answers') or [])]
            bad={'NC'}
        elif doc.kind in INSPECTION_MODULES:
            cfg=INSPECTION_MODULES[doc.kind]
            if cfg['mode'] in {'daily','weekly'}:
                periods=data.get('periods') or {}
                if data.get('day_mode') and data.get('day_period') in periods: periods={data['day_period']:periods[data['day_period']]}
                ans=[a for info in periods.values() for a in (info.get('answers') or [])]
                bad={'NC'}
            else:
                ans=[(r or {}).get('answer') for r in (data.get('rows') or [])]
                bad={'NAO_ATENDE'}
        else:
            return ''
        ans=[a for a in ans if a]
        if not ans: return ''
        return 'INAPTO' if any(a in bad for a in ans) else 'APTO'
    except Exception:
        return ''
templates.env.globals['inspection_result']=inspection_result

def save_signature(data_url: str|None, existing: str='', prefix='sig') -> str:
    value=clean(data_url)
    if not value: return existing or ''
    if not value.startswith('data:image/'): return existing or ''
    try:
        header,b64=value.split(',',1); raw=base64.b64decode(b64)
        if len(raw)>2_500_000: raise ValueError('Assinatura muito grande')
        # Um canvas oculto pode produzir PNG 1x1 ou inteiramente transparente.
        pix=fitz.Pixmap(raw)
        if pix.width<2 or pix.height<2 or pix.width*pix.height>16_000_000:
            raise ValueError('Assinatura inválida')
        samples=pix.samples
        channels=pix.n
        if not any((not pix.alpha or samples[i+channels-1]>28) and min(samples[i:i+channels-int(pix.alpha)])<225 for i in range(0,len(samples),channels)):
            raise ValueError('Faça sua rubrica antes de confirmar')
        name=f'{safe_filename(prefix)}_{now().strftime("%Y%m%d_%H%M%S_%f")}_{secrets.token_hex(3)}.png'
        path=SIG_DIR/name; path.write_bytes(raw)
        return str(Path('signatures')/name)
    except Exception:
        return existing or ''

async def save_rac_evidence_photo(upload, existing: str='', prefix: str='rac_evidencia') -> str:
    """Valida e salva uma foto de evidência da RAC em storage/evidence.

    O arquivo é normalizado para PNG para manter compatibilidade entre navegador,
    VPS e gerador de PDF. Se nenhum arquivo novo for enviado, preserva o existente.
    """
    if upload is None or not hasattr(upload,'read') or not getattr(upload,'filename',''):
        return existing or ''
    content_type=(getattr(upload,'content_type','') or '').lower()
    if content_type and not content_type.startswith('image/'):
        raise ValueError('A evidência deve ser uma imagem.')
    raw=await upload.read()
    if not raw:
        return existing or ''
    if len(raw)>10_000_000:
        raise ValueError('A foto de evidência deve ter no máximo 10 MB.')
    suffix=Path(str(getattr(upload,'filename','') or '')).suffix.lower()
    filetype={'jpg':'jpeg','jpeg':'jpeg','png':'png','webp':'webp'}.get(suffix.lstrip('.'))
    if not filetype:
        filetype={'image/jpeg':'jpeg','image/jpg':'jpeg','image/png':'png','image/webp':'webp'}.get(content_type)
    if not filetype:
        raise ValueError('Formato de imagem não suportado. Use JPG, PNG ou WEBP.')
    try:
        image_doc=fitz.open(stream=raw,filetype=filetype)
        pix=image_doc[0].get_pixmap(alpha=False)
        normalized=pix.tobytes('png')
        image_doc.close()
    except Exception as exc:
        raise ValueError('Não foi possível ler a foto selecionada.') from exc
    name=f'{safe_filename(prefix)}_{now().strftime("%Y%m%d_%H%M%S_%f")}_{secrets.token_hex(3)}.png'
    path=EVIDENCE_DIR/name
    path.write_bytes(normalized)
    if existing:
        try:
            old=(STORAGE_DIR/Path(existing)).resolve()
            if EVIDENCE_DIR in old.parents and old.is_file(): old.unlink()
        except Exception:
            pass
    return str(Path('evidence')/name)

async def save_photo_or_flash(request: Request, upload, prefix: str) -> str:
    """Salva a foto de evidência; se for inválida, avisa o usuário e segue sem derrubar o formulário."""
    try:
        return await save_rac_evidence_photo(upload,'',prefix)
    except ValueError as exc:
        flash(request,f'Foto não anexada ({getattr(upload,"filename","") or "arquivo"}): {exc}','error')
        return ''

def remove_rac_evidence_photo(value: str|None):
    if not value: return
    try:
        target=(STORAGE_DIR/Path(value)).resolve()
        if EVIDENCE_DIR in target.parents and target.is_file(): target.unlink()
    except Exception:
        pass

def get_document(doc_id: int) -> Document:
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404,'Documento não encontrado')
        db.expunge(doc); return doc

def user_can_access_document(user: User, doc: Document, _depth: int=0) -> bool:
    """Regra central de visibilidade e acesso direto aos documentos.

    - Super Administrador: acesso total.
    - Administrador: acesso apenas aos documentos do Cluster/Site sob sua
      responsabilidade.
    - Usuário: somente documentos que ele próprio criou.
    - Exceção operacional: numa APR em Pendente assinatura, o integrante
      vinculado ao usuário pode abrir a APR enquanto sua própria assinatura
      estiver pendente. Isso mantém a área de pendências funcional sem expor
      o histórico dos documentos criados por outras pessoas.
    - Modelos de APR permanecem compartilhados com a equipe.
    - Integrante adicional pode ler a APR finalizada para assinar sua inclusão;
      esse acesso não concede permissão para alterar a APR ou suas PTs.
    """
    if is_super_admin(user):
        return True
    if doc.kind=='apr_template':
        return True
    if doc.kind=='apr' and doc.status=='Finalizada':
        data=doc_data(doc)
        if any(str(m.get('participant_user_id') or '')==str(user.id)
               for m in (data.get('execution_member_requests') or [])+(data.get('execution_members') or [])):
            return True
    if user.role==ROLE_ADMIN:
        return admin_scope_allows_document(user,doc)
    if doc.created_by==user.id:
        return True
    if doc.kind=='apr' and doc.status=='Pendente assinatura':
        try:
            data=doc_data(doc)
        except Exception:
            data={}
        for worker in (data.get('workers') or []):
            try:
                same_user=int(worker.get('participant_user_id') or 0)==user.id
            except Exception:
                same_user=False
            if same_user:
                return True
    return False

def user_can_list_document(user: User, doc: Document) -> bool:
    """Visibilidade nos painéis/históricos.

    Usuário comum vê somente documentos criados por ele. Pendências de
    assinatura de terceiros são mostradas em cards próprios e não entram no
    histórico principal. Administradores locais veem todo o escopo atribuído.
    """
    if user.role in (ROLE_SUPER_ADMIN,ROLE_DEV):
        vc=VIEW_CLUSTER.get()
        return (not vc) or normalize_location_pair(doc.cluster,doc.site)[0]==vc
    if is_super_admin(user):
        return True
    if user.role==ROLE_ADMIN:
        return admin_scope_allows_document(user,doc)
    return doc.created_by==user.id

def require_document_access(request: Request, doc: Document) -> User:
    """Garante login + permissão sobre o documento específico.

    Uso: `user=require_document_access(request, doc)` logo após buscar
    o documento com `get_document(doc_id)`.
    """
    user=current_user(request)
    if not user:
        raise HTTPException(401,'Não autenticado')
    if not user_can_access_document(user, doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para acessar este documento.')
    return user

def save_doc(doc: Document|None, kind: str, data: dict, user: User, status='Rascunho') -> Document:
    # Lock local + advisory lock PostgreSQL: dois usuários criando o mesmo tipo
    # no mesmo instante não recebem o mesmo código sequencial.
    guard=_CODE_LOCK if doc is None else nullcontext()
    with guard:
        with SessionLocal() as db:
            payload=dict(data)
            if doc:
                target=db.get(Document,doc.id)
                previous=doc_data(target)
                previous['status']=target.status
                if target.status in {'Finalizada','Cancelado'}: raise HTTPException(409,'Documento finalizado ou cancelado não pode ser editado.')
            else:
                if db.bind and db.bind.dialect.name=='postgresql':
                    db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:lock_key))'),{'lock_key':f'safetyplus-code-{kind}-{now().year}'})
                previous={}
                reserved=_next_code_in_db(db,kind)
                payload['code']=reserved
                target=Document(code=reserved,kind=kind,title=DOCUMENT_TITLES[kind],status='Rascunho',created_by=user.id,created_at=now(),updated_at=now())
                db.add(target)
            payload['status']=status
            new_cluster=clean(payload.get('cluster')); new_site=clean(payload.get('site'))
            if user.role==ROLE_ADMIN and new_cluster and not admin_scope_allows_location(user,new_cluster,new_site):
                raise HTTPException(403,'Este Cluster/Site não faz parte do seu escopo de administração.')
            payload['status']=status
            target.status=status; target.cluster=new_cluster; target.site=new_site; target.activity=clean(payload.get('activity') or payload.get('objective'))
            target.data_json=json.dumps(payload,ensure_ascii=False); target.updated_at=now()
            if status=='Finalizada': target.finalized_at=now()
            db.flush()
            changes=document_change_rows(previous,payload)
            if changes or doc is None:
                details={'document_id':target.id,'code':target.code,'kind':kind,'title':target.title,
                         'changes':[{k:str(v)[:240] for k,v in row.items()} for row in changes[:60]],
                         'omitted_changes':max(0,len(changes)-60)}
                db.add(AuditLog(user_id=user.id,action='editar_documento' if doc else 'criar_documento',
                                detail=json.dumps(details,ensure_ascii=False),created_at=now()))
            db.commit(); db.refresh(target); db.expunge(target)
        return target

def save_validation_state(doc: Document|None, kind: str, data: dict, user: User, fields: list[str]|tuple[str,...], status: str='Rascunho') -> Document:
    """Salva o que já foi preenchido antes de devolver um erro de validação."""
    payload=dict(data)
    unique=[]
    for field in fields or []:
        name=clean(field)
        if name and name not in unique:
            unique.append(name)
    payload['_validation_fields']=unique
    return save_doc(doc,kind,payload,user,status)

def clear_validation_state(data: dict) -> dict:
    data.pop('_validation_fields',None)
    return data


def _append_apr_external_resources(pdf_path: Path, data: dict) -> None:
    """Anexa a página de recursos externos de emergência da unidade (cluster) da APR."""
    from .external_resources import unit_for_cluster
    unit=unit_for_cluster(STORAGE_DIR,clean(data.get('cluster')))
    if not unit:
        return
    doc=fitz.open(pdf_path)
    try:
        width,height=595.0,842.0
        page=doc.new_page(width=width,height=height)
        page.draw_rect(fitz.Rect(42,36,553,58),color=None,fill=(0.29,0.29,0.29))
        page.insert_text((60,52),f"RECURSOS EXTERNOS DE EMERGÊNCIA - {unit['name'].upper()} ({unit['state']})",fontsize=9,fontname='hebo',color=(1,1,1))
        y=80.0
        def wrap(txt,size,font,maxw):
            out=[];cur=''
            for w in txt.split():
                t=(cur+' '+w).strip()
                if fitz.get_text_length(t,fontname=font,fontsize=size)>maxw and cur:
                    out.append(cur);cur=w
                else: cur=t
            if cur: out.append(cur)
            return out
        for idx,(name,phone,addr) in enumerate(unit['resources'],1):
            nl=wrap(name,9,'hebo',250); al=wrap(addr,8,'helv',250) if addr else []
            ph=[x for x in (phone or '').split(' / ') if x]
            rows=max(len(nl)*12+len(al)*11,len(ph)*12,14)
            if y+rows>800:
                page=doc.new_page(width=width,height=height); y=48
            if idx%2: page.draw_rect(fitz.Rect(42,y-9,553,y+rows-3),color=None,fill=(0.96,0.95,0.93))
            page.insert_text((48,y),f'RECURSO {idx:02d}',fontsize=8,fontname='helv')
            yy=y
            for l in nl: page.insert_text((130,yy),l,fontsize=9,fontname='hebo'); yy+=12
            for l in al: page.insert_text((130,yy),l,fontsize=8,fontname='helv'); yy+=11
            for i,t in enumerate(ph): page.insert_text((400,y+i*12),t,fontsize=9,fontname='hebo')
            y+=rows+6
        tmp=pdf_path.with_name(pdf_path.stem+'_ext_tmp.pdf')
        if tmp.exists(): tmp.unlink()
        doc.save(tmp,garbage=4,deflate=True)
    finally:
        doc.close()
    tmp.replace(pdf_path)


def _append_apr_execution_members(pdf_path: Path, data: dict) -> None:
    """Anexa folha auditável com integrantes incluídos após a conclusão da APR."""
    members=[dict(x or {}) for x in (data.get('execution_members') or []) if clean((x or {}).get('worker'))]
    if not members:
        return
    doc=fitz.open(pdf_path)
    try:
        width,height=595.0,842.0
        page=doc.new_page(width=width,height=height)
        page.insert_text((42,48),'APR — INTEGRANTES INCLUÍDOS DURANTE A EXECUÇÃO',fontsize=13,fontname='hebo')
        page.draw_line((42,58),(553,58),color=(0.95,0.33,0.29),width=1.6)
        y=82.0
        for idx,item in enumerate(members,1):
            if y>740:
                page=doc.new_page(width=width,height=height); y=48
            page.insert_text((42,y),f"{idx:02d}. {clean(item.get('worker'))}",fontsize=10,fontname='hebo'); y+=15
            linhas=[
                f"Empresa: {clean(item.get('company')) or '-'}   |   Função: {clean(item.get('role')) or '-'}",
                f"CPF: {clean(item.get('cpf_masked')) or '-'}",
                f"Incluído por: {clean(item.get('added_by')) or '-'} em {clean(item.get('created_at')) or '-'}",
            ]
            if clean(item.get('signed_by_name')):
                linhas.append(f"Assinado por: {clean(item.get('signed_by_name'))} em {clean(item.get('signed_at')) or '-'}")
            if clean(item.get('reason')):
                linhas.append(f"Motivo: {clean(item.get('reason'))}")
            for linha in linhas:
                texto=linha
                while texto:
                    corte=len(texto)
                    while corte>1 and fitz.get_text_length(texto[:corte],fontname='helv',fontsize=9)>495:
                        corte-=1
                    page.insert_text((50,y),texto[:corte],fontsize=9,fontname='helv'); y+=13
                    texto=texto[corte:]
            sig_rel=clean(item.get('signature_image'))
            if sig_rel:
                sig_path=(STORAGE_DIR/Path(sig_rel)).resolve()
                if sig_path.exists():
                    page.insert_text((50,y),'Assinatura do integrante:',fontsize=8,fontname='hebo'); y+=5
                    try:
                        rect=fitz.Rect(50,y,190,y+42)
                        page.insert_image(rect,filename=str(sig_path),keep_proportion=True,overlay=True)
                        y+=48
                    except Exception:
                        page.insert_text((50,y),'Assinatura registrada.',fontsize=8,fontname='helv'); y+=14
            y+=12
        tmp=pdf_path.with_name(pdf_path.stem+'_mem_tmp.pdf')
        if tmp.exists(): tmp.unlink()
        doc.save(tmp,garbage=4,deflate=True)
    finally:
        doc.close()
    tmp.replace(pdf_path)


def _append_apr_execution_observations(pdf_path: Path, data: dict) -> None:
    """Anexa uma folha auditável com observações registradas após a conclusão da APR."""
    notes=[dict(x or {}) for x in (data.get('execution_observations') or []) if clean((x or {}).get('text'))]
    if not notes:
        return
    doc=fitz.open(pdf_path)
    try:
        width,height=595.0,842.0
        page=doc.new_page(width=width,height=height)
        page.insert_text((42,48),'APR — OBSERVAÇÕES DURANTE A EXECUÇÃO',fontsize=13,fontname='hebo')
        page.draw_line((42,58),(553,58),color=(0.95,0.33,0.29),width=1.6)
        y=82.0
        for idx,note in enumerate(notes,1):
            author=clean(note.get('author')) or 'Usuário'
            at=clean(note.get('created_at')) or ''
            header=f'{idx:02d}. [{clean(note.get("type")) or "Observação"}] {author}'
            if at:
                header+=f' — {at}'
            if y>760:
                page=doc.new_page(width=width,height=height); y=48
                page.insert_text((42,y),'APR — OBSERVAÇÕES DURANTE A EXECUÇÃO (continuação)',fontsize=12,fontname='hebo'); y+=28
            page.insert_text((42,y),header,fontsize=9.5,fontname='hebo'); y+=15
            text_value=clean(note.get('text'))
            words=text_value.split()
            lines=[]; current=''
            for word in words:
                trial=(current+' '+word).strip()
                if fitz.get_text_length(trial,fontname='helv',fontsize=9)<=495:
                    current=trial
                else:
                    if current: lines.append(current)
                    current=word
            if current: lines.append(current)
            for line in lines:
                if y>790:
                    page=doc.new_page(width=width,height=height); y=48
                page.insert_text((50,y),line,fontsize=9,fontname='helv'); y+=13
            y+=12
        tmp=pdf_path.with_name(pdf_path.stem+'_obs_tmp.pdf')
        if tmp.exists(): tmp.unlink()
        doc.save(tmp,garbage=4,deflate=True)
    finally:
        doc.close()
    tmp.replace(pdf_path)


def _rollback_document_after_pdf_failure(doc_id: int, status: str='Rascunho') -> None:
    """Evita documento preso como Finalizado quando a geração do PDF falha."""
    with SessionLocal() as db:
        target=db.get(Document,doc_id)
        if not target:
            return
        target.status=status
        target.finalized_at=None if status!='Finalizada' else target.finalized_at
        target.updated_at=now()
        try:
            payload=json.loads(target.data_json or '{}')
        except Exception:
            payload={}
        payload['status']=status
        target.data_json=json.dumps(payload,ensure_ascii=False)
        db.commit()


def finalize_pdf(doc: Document, data: dict, extra_pdf_paths: list[Path]|None=None) -> Document:
    if doc.kind in RAC_MODULES:
        data = dict(data)
        data['score'] = calculate_rac_score(doc.kind, data.get('answers') or [])
        data['_rac_report_version'] = '2026-11-12.1'
    # O banco mantém o código-base estável. O PDF recebe o código visual com a usina.
    pdf_data=dict(data)
    pdf_data['_document_id']=str(doc.id)
    pdf_data['code']=data_reference_code(doc.kind,pdf_data,doc.cluster,doc.site) or doc.code
    # Justificativas de respostas negativas entram no PDF junto das observações.
    try:
        if doc.kind in MODULES and clean(pdf_data.get('checklist_no_justification')):
            pdf_data['comments']=(clean(pdf_data.get('comments'))+'\nJustificativa do NÃO no checklist: '+clean(pdf_data['checklist_no_justification'])).strip()
        elif doc.kind in RAC_MODULES and any(clean(x) for x in (pdf_data.get('no_justifications') or [])):
            obs=list(pdf_data.get('observations') or [])
            for i,j in enumerate(pdf_data.get('no_justifications') or []):
                if clean(j):
                    obs=obs+['']*(i+1-len(obs)); obs[i]=(clean(obs[i])+' | Justificativa: '+clean(j)).strip(' |')
            pdf_data['observations']=obs
        elif doc.kind=='vehicle' and pdf_data.get('day_mode'):
            nj=clean(((pdf_data.get('days') or {}).get(pdf_data.get('day_period')) or {}).get('no_justification'))
            if nj: pdf_data['observations']=(clean(pdf_data.get('observations'))+'\nJustificativa do item Não conforme: '+nj).strip()
    except Exception:
        pass
    rel=Path('pdfs')/f'{safe_filename(pdf_data["code"])}.pdf'; out=STORAGE_DIR/rel
    generate_document(doc.kind,pdf_data,out)
    # Quando a APR possui PTs vinculadas, o PDF final vira um único dossiê:
    # APR primeiro e, em seguida, cada PT finalizada na ordem selecionada.
    # Se o chamador não informar caminhos explicitamente, a APR busca
    # automaticamente todas as PTs vinculadas já finalizadas. Isso também
    # vale para reconstrução do PDF, evitando uma APR sem as PTs.
    if doc.kind=='apr' and extra_pdf_paths is None:
        try:
            extra_pdf_paths=linked_permit_pdf_paths(data)
        except Exception:
            extra_pdf_paths=[]
    extra_pdf_paths=[Path(x) for x in (extra_pdf_paths or [])]
    if doc.kind=='apr':
        # Marca PDFs novos para que uma instalação atualizada consiga distinguir
        # dossiês completos de PDFs antigos gerados sem as PTs anexadas.
        data['pdf_includes_linked_permits']='1' if extra_pdf_paths else clean(data.get('pdf_includes_linked_permits'))
    if extra_pdf_paths:
        merged=fitz.open(out)
        try:
            for extra in extra_pdf_paths:
                if not extra.exists():
                    raise FileNotFoundError(f'PDF vinculado não encontrado: {extra.name}')
                src=fitz.open(extra)
                try: merged.insert_pdf(src)
                finally: src.close()
            tmp=out.with_name(out.stem+'_completo_tmp.pdf')
            if tmp.exists(): tmp.unlink()
            merged.save(tmp,garbage=4,deflate=True)
        finally:
            merged.close()
        tmp.replace(out)
    if doc.kind=='apr':
        _append_apr_execution_observations(out,data)
        _append_apr_execution_members(out,data)
        _append_apr_external_resources(out,data)
    with SessionLocal() as db:
        target=db.get(Document,doc.id); target.pdf_path=str(rel); target.data_json=json.dumps(data,ensure_ascii=False); target.updated_at=now(); db.commit(); db.refresh(target); db.expunge(target)
    return target

def ensure_document_pdf(doc: Document, _seen: set[int]|None=None) -> Path|None:
    """Garante que um documento finalizado tenha um PDF físico disponível.

    Algumas versões antigas mantinham o caminho no banco mesmo quando o arquivo
    não existia mais no volume. Em vez de responder 404, o Safety Plus recompõe
    o PDF a partir dos dados salvos. Para APRs, recompõe primeiro as PTs ligadas
    e remonta o dossiê completo.
    """
    if not doc or doc.status not in ('Finalizada','Substituída'):
        return None
    data=doc_data(doc)
    if doc.pdf_path:
        current=STORAGE_DIR/doc.pdf_path
        if current.exists() and current.is_file():
            # PDFs antigos da APR podiam existir sem as PTs no arquivo principal.
            # Se há PT finalizada e o marcador de dossiê ainda não existe,
            # recompõe uma vez e passa a gravar o marcador na própria APR.
            needs_dossier_rebuild=bool(doc.kind in RAC_MODULES and data.get('_rac_report_version') != '2026-11-12.1')
            if doc.kind=='apr' and clean(data.get('pdf_includes_linked_permits'))!='1':
                try: needs_dossier_rebuild=bool(linked_permit_pdf_paths(data))
                except Exception: needs_dossier_rebuild=False
            if not needs_dossier_rebuild:
                # Não devolve arquivo truncado/corrompido ao navegador. Alguns
                # celulares exibem apenas uma tela branca/ícone de PDF quando o
                # arquivo físico existe, mas ficou incompleto após uma interrupção.
                try:
                    probe=fitz.open(current)
                    try:
                        if probe.page_count > 0:
                            return current
                    finally:
                        probe.close()
                except Exception as exc:
                    audit(None,'pdf_corrompido_reconstruir',f'{doc.code}: {exc}')
                    try: current.unlink()
                    except Exception: pass
    seen=set(_seen or set())
    if doc.id in seen:
        return None
    seen.add(doc.id)
    rebuilt=finalize_pdf(doc,data)
    if rebuilt.pdf_path:
        path=STORAGE_DIR/rebuilt.pdf_path
        if path.exists():
            return path
    return None

@app.get('/health')
def health(): return {'ok':True,'version':get_version(STORAGE_DIR)}


def _safe_next_path(value: str|None, fallback: str='/') -> str:
    """Aceita somente caminhos internos para retorno após login."""
    value=clean(value)
    if not value or not value.startswith('/') or value.startswith('//'):
        return fallback
    return value


def _public_base_url(request: Request) -> str:
    """URL pública usada no QR Code. Em produção prefere DOMAIN; local usa a própria requisição."""
    domain=(os.getenv('DOMAIN','') or '').strip().strip('/')
    if domain and domain not in {'localhost','127.0.0.1'}:
        if domain.startswith('http://') or domain.startswith('https://'):
            return domain.rstrip('/')
        return 'https://'+domain
    return str(request.base_url).rstrip('/')


def _apr_signature_periods(data: dict) -> list[dict]:
    """Períodos aprovados, incluindo o original; sem inventar datas ou apagar histórico."""
    periods=[]
    original=parse_date_br(data.get('apr_date'))
    if original:
        periods.append({'title':'Período original','days':[original+timedelta(days=i) for i in range(REVALIDATION_WINDOW_DAYS)]})
    for i, row in enumerate(data.get('approvals') or []):
        if not isinstance(row,dict) or clean(row.get('type')).lower()!='revalidação':
            continue
        start=parse_date_br(row.get('start'))
        end=parse_date_br(row.get('end'))
        if start and end and start<=end:
            days=[start+timedelta(days=i) for i in range(min((end-start).days+1,REVALIDATION_WINDOW_DAYS))]
            periods.append({'title':f'Revalidação {len(periods)}','days':days})
    return periods


def _apr_valid_days(data: dict) -> list[date]:
    periods=_apr_signature_periods(data)
    return periods[-1]['days'] if periods else []


def _worker_daily_signatures(worker: dict) -> dict:
    raw=(worker or {}).get('daily_signatures') or {}
    if not isinstance(raw,dict):
        return {}
    out={}
    for key,val in raw.items():
        if isinstance(val,dict): out[str(key)]=dict(val)
    return out


def _record_worker_daily_signature(worker: dict, signed_day: date, *, signature_image: str, signer: User, signed_at: datetime|None=None, mode: str='Online') -> dict:
    """Registra a rubrica diária sem substituir a assinatura inicial da APR."""
    signed_at=signed_at or now()
    daily=_worker_daily_signatures(worker)
    key=signed_day.isoformat()
    daily[key]={
        'date':signed_day.strftime('%d/%m/%Y'),
        'signature_image':clean(signature_image),
        'signed_at':signed_at.strftime('%d/%m/%Y %H:%M'),
        'signed_by_user_id':str(signer.id),
        'signed_by_name':signer.full_name or signer.username,
        'capture_mode':mode,
    }
    worker['daily_signatures']=daily
    return worker


def _maybe_record_initial_signature_as_daily(worker: dict, data: dict, *, signature_image: str, signer: User, signed_at: datetime|None=None, mode: str='Assinatura inicial') -> dict:
    signed_at=signed_at or now()
    signed_day=signed_at.date()
    if signed_day in _apr_valid_days(data):
        daily=_worker_daily_signatures(worker)
        if signed_day.isoformat() not in daily:
            _record_worker_daily_signature(worker,signed_day,signature_image=signature_image,signer=signer,signed_at=signed_at,mode=mode)
    return worker


def _apr_participant_worker_index(data: dict, user_id: int) -> int|None:
    for i,w in enumerate(data.get('workers') or []):
        try: uid=int((w or {}).get('participant_user_id') or 0)
        except Exception: uid=0
        if uid==user_id: return i
    return None

@app.get('/login',response_class=HTMLResponse)
def login_page(request: Request):
    next_path=_safe_next_path(request.query_params.get('next'))
    if current_user(request): return RedirectResponse(next_path,303)
    return templates.TemplateResponse(request,'login.html',context(request,next_path=next_path,sso_enabled=sso.enabled()))

# Limite por origem e login; expiração automática e memória limitada.
# Para múltiplas réplicas, usar Redis compartilhado em uma versão futura.
_LOGIN_FAILURES: dict[tuple[str,str],list[float]]={}
_LOGIN_LOCK=threading.Lock()
_LOGIN_WINDOW=600
_LOGIN_LIMIT=8

def _login_attempt_allowed(ip: str, username: str) -> bool:
    now=time.monotonic()
    with _LOGIN_LOCK:
        if len(_LOGIN_FAILURES)>10000:
            for key in list(_LOGIN_FAILURES):
                recent=[t for t in _LOGIN_FAILURES[key] if now-t<_LOGIN_WINDOW]
                if recent: _LOGIN_FAILURES[key]=recent
                else: _LOGIN_FAILURES.pop(key,None)
        key=(ip,username.casefold())
        recent=[t for t in _LOGIN_FAILURES.get(key,[]) if now-t<_LOGIN_WINDOW]
        if recent: _LOGIN_FAILURES[key]=recent
        else: _LOGIN_FAILURES.pop(key,None)
        return len(recent)<_LOGIN_LIMIT

def _login_record_failure(ip: str, username: str) -> None:
    now=time.monotonic()
    with _LOGIN_LOCK:
        key=(ip,username.casefold())
        _LOGIN_FAILURES[key]=[t for t in _LOGIN_FAILURES.get(key,[]) if now-t<_LOGIN_WINDOW]+[now]

def _login_reset_failures(ip: str, username: str) -> None:
    with _LOGIN_LOCK:
        _LOGIN_FAILURES.pop((ip,username.casefold()),None)

@app.post('/login')
async def login(request: Request):
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    username=clean(form.get('username')); password=str(form.get('password') or '')
    next_path=_safe_next_path(form.get('next'))
    ip=request.client.host if request.client else 'unknown'
    if not _login_attempt_allowed(ip,username):
        flash(request,'Muitas tentativas. Aguarde 10 minutos antes de tentar novamente.','error')
        return RedirectResponse('/login',303,headers={'Retry-After':'600'})
    with SessionLocal() as db:
        user=db.query(User).filter(User.username==username,User.active==True).first()
        if not user or not verify_password(password,user.password_hash):
            _login_record_failure(ip,username)
            audit(None,'login_falha',f'{username} | ip={ip}')
            flash(request,'Usuário ou senha inválidos.','error'); return RedirectResponse('/login?next='+next_path,303)
        uid=user.id
    _login_reset_failures(ip,username)
    # Descarta dados da sessão anterior ao autenticar (mitigação de fixation).
    request.session.clear()
    request.session['user_id']=uid
    request.session['t']=time.time()
    audit(uid,'login',f'{username} | ip={ip}'); return RedirectResponse(next_path,303)

@app.get('/sso/login')
async def sso_login(request: Request):
    if not sso.enabled(): raise HTTPException(404)
    if current_user(request): return RedirectResponse(_safe_next_path(request.query_params.get('next')),303)
    next_path=_safe_next_path(request.query_params.get('next'))
    uri=sso.redirect_uri()
    if not uri:
        flash(request,'SSO sem endereço de retorno configurado.','error'); return RedirectResponse('/login',303)
    request.session['sso_next']=next_path
    try:
        return await sso.client().authorize_redirect(request,uri)
    except Exception as exc:
        audit(None,'login_sso_falha',f'provedor indisponível ou mal configurado: {type(exc).__name__}')
        flash(request,'SSO indisponível no momento. Use usuário e senha.','error'); return RedirectResponse('/login',303)

@app.get('/sso/callback')
async def sso_callback(request: Request):
    if not sso.enabled(): raise HTTPException(404)
    ip=request.client.host if request.client else 'unknown'
    next_path=_safe_next_path(request.session.get('sso_next'))
    def fail(msg: str, detail: str, uid=None):
        audit(uid,'login_sso_falha',f'{detail} | ip={ip}')
        flash(request,msg,'error'); return RedirectResponse('/login',303)
    if request.query_params.get('error'):
        return fail('Entrada pelo SSO não concluída.',f"provedor: {clean(request.query_params.get('error'))[:80]}")
    try:
        token=await sso.client().authorize_access_token(request)
    except Exception as exc:
        return fail('Não foi possível validar o login pelo SSO. Tente novamente.',f'token inválido: {type(exc).__name__}')
    claims=dict(token.get('userinfo') or {})
    email,err=sso.validate_claims(claims)
    if err: return fail('Esta conta não pode entrar pelo SSO.',f'{err} | {email or "sem email"}')
    with SessionLocal() as db:
        user=db.query(User).filter(func.lower(User.username)==email,User.active==True).first()
        uid=user.id if user else None
    if not uid:
        return fail('Seu e-mail não tem acesso cadastrado no Safety Plus. Fale com o administrador.',f'usuário não encontrado ou inativo | {email}')
    request.session.clear()
    request.session['user_id']=uid
    request.session['t']=time.time()
    audit(uid,'login_sso',f'{email} | ip={ip}')
    return RedirectResponse(next_path,303)

@app.get('/api/session/status')
def session_status(request: Request):
    user=current_user(request)
    return JSONResponse(
        {'authenticated':bool(user),'user_id':user.id if user else None},
        status_code=200 if user else 401,
        headers={'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache'},
    )

@app.post('/logout')
async def logout(request: Request):
    # Logout idempotente: uma página antiga no histórico não deve gerar erro de
    # CSRF depois que a sessão já foi encerrada.
    uid=request.session.get('user_id')
    if uid:
        form=await request.form()
        verify_csrf(request,form.get('csrf_token'))
    request.session.clear()
    if uid:
        audit(uid,'logout','')
    response=RedirectResponse('/login?logged_out=1',303)
    response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma']='no-cache'
    response.headers['Clear-Site-Data']='"cache"'
    return response

EMISSION_PERMITS=[
    ('Trabalho em Altura','pt_height','mi-hardhat'),
    ('Espaço Confinado','confined','mi-confined'),
    ('Intervenção Elétrica','electrical','mi-zap'),
    ('Linha Viva','line_live','mi-live'),
    ('Supressão de Vegetação','vegetation','mi-leaf'),
    ('Içamento de Carga','lifting','mi-hook'),
    ('PT — TME','tme','mi-tower'),
]
RAC_TEMPLATES_DIR=BASE_DIR/'rac_templates'
RAC_TEMPLATES_DIR.mkdir(parents=True,exist_ok=True)

@app.get('/emissao-documentos',response_class=HTMLResponse)
def emission_documents(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    return RedirectResponse('/apr/new',303)

INSPECTION_MENU=[
    ('Veículo Pesado','/vehicle/new','mi-truck'),
    ('Veículo Leve','/inspection/light_vehicle/new','mi-car'),
    ('Talha Guincho','/inspection/hoist/new','mi-hoist'),
    ('Inspeção diária — Kit de Altura','/inspection/height_kit/new','mi-kit'),
    ('Climber Assist','/inspection/climber_assist/new','mi-climb'),
    ('Inspeção estrutural — Cinto','/inspection/safety_belt/new','mi-belt'),
    ('SPIQ — Cinturão, Talabarte e Trava-quedas','/inspection/spiq/new','mi-belt'),
    ('LOTO','/inspection/loto/new','mi-zap'),
    ('Esmerilhadeira','/inspection/grinder/new','mi-tools'),
    ('Furadeira','/inspection/drill/new','mi-tools'),
    ('Martelete','/inspection/rotary_hammer/new','mi-tools'),
    ('Serra Circular','/inspection/circular_saw/new','mi-tools'),
    ('Serra Mármore','/inspection/marble_saw/new','mi-tools'),
    ('Máquina de Solda','/inspection/welding_machine/new','mi-zap'),
    ('Acessórios de Içamento de Carga','/inspection/lifting_accessories/new','mi-hook'),
]

@app.get('/inspecoes',response_class=HTMLResponse)
def inspections_menu(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    return templates.TemplateResponse(request,'emission_permits.html',context(request,permit_options=INSPECTION_MENU+[(c.get('title',''),f'/rac/{k}/new',c.get('icon','mi-clipboard')) for k,c in RAC_MODULES.items() if c.get('custom') and c.get('placement')=='inspection'],page_title='Inspeções Prévias',page_sub='Selecione o checklist que deseja preencher.',option_note='Abrir novo checklist',history=build_doc_history(request,user,['vehicle']+list(INSPECTION_MODULES.keys()),{**{k:t for t,u,_ in INSPECTION_MENU for k in [u.split('/')[2] if u.startswith('/inspection/') else 'vehicle']}}),history_title='Histórico de Inspeções',history_empty='Nenhuma inspeção registrada ainda.',history_col='Checklist'))


def build_doc_history(request,user,kinds,kind_labels):
    """Histórico filtrável (mesmo padrão da RAC) para Permissões e Inspeções."""
    qp=request.query_params
    q=clean(qp.get('q')); kind=clean(qp.get('kind')); status=clean(qp.get('status')); period=clean(qp.get('period')).lower()
    date_from=clean(qp.get('date_from')); date_to=clean(qp.get('date_to')); creator=clean(qp.get('creator')); cluster=clean(qp.get('cluster'))
    sort=clean(qp.get('sort')).lower() or 'recent'
    if kind not in kinds: kind=''
    if sort not in {'recent','oldest'}: sort='recent'
    if period not in {'today','7days','month','custom'}: period=''
    today=local_today()
    if period=='today': date_from=date_to=today.strftime('%Y-%m-%d')
    elif period=='7days': date_from=(today-timedelta(days=6)).strftime('%Y-%m-%d'); date_to=today.strftime('%Y-%m-%d')
    elif period=='month': date_from=today.replace(day=1).strftime('%Y-%m-%d'); date_to=today.strftime('%Y-%m-%d')
    def _d(v):
        try: return datetime.strptime(v,'%Y-%m-%d').date()
        except ValueError: return None
    with SessionLocal() as db:
        base=db.query(Document).filter(Document.kind.in_(list(kinds)))
        query=base
        if kind: query=query.filter(Document.kind==kind)
        if status: query=query.filter(Document.status==status)
        if cluster: query=query.filter(Document.cluster==cluster)
        if q:
            like=f'%{q}%'
            query=query.filter(or_(Document.code.ilike(like),Document.title.ilike(like),Document.activity.ilike(like),Document.cluster.ilike(like),Document.site.ilike(like)))
        df=_d(date_from) if date_from else None; dt=_d(date_to) if date_to else None
        if date_from and not df: date_from=''
        if date_to and not dt: date_to=''
        if df: query=query.filter(Document.updated_at>=datetime.combine(df,datetime.min.time()))
        if dt: query=query.filter(Document.updated_at<datetime.combine(dt+timedelta(days=1),datetime.min.time()))
        if creator.isdigit(): query=query.filter(Document.created_by==int(creator))
        else: creator=''
        ordering=Document.updated_at.asc() if sort=='oldest' else desc(Document.updated_at)
        cand=query.order_by(ordering).limit(1200).all()
        rows=[d for d in cand if user_can_list_document(user,d)]
        allv=base.order_by(desc(Document.updated_at)).limit(2000).all()
        allv=[d for d in allv if user_can_list_document(user,d)]
        statuses=sorted({clean(d.status) for d in allv if clean(d.status)},key=lambda x:x.casefold())
        clusters=sorted({clean(d.cluster) for d in allv if clean(d.cluster)},key=lambda x:x.casefold())
        if is_admin_user(user):
            creators=[{'id':u.id,'name':u.full_name or u.username} for u in db.query(User).filter(User.role!=ROLE_DEV).order_by(User.full_name,User.username).all()]
        else:
            creators=[{'id':user.id,'name':user.full_name or user.username}]
        for d in rows: db.expunge(d)
    return {'docs':rows,'q':q,'kind':kind,'status':status,'period':period,'date_from':date_from,'date_to':date_to,
            'creator':creator,'cluster':cluster,'sort':sort,'statuses':statuses,'clusters':clusters,'creators':creators,
            'kinds':[(k,kind_labels.get(k,k)) for k in kinds],'labels':kind_labels,'action':request.url.path}

@app.get('/emissao-documentos/permissoes',response_class=HTMLResponse)
def emission_permits(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    extra=[(c.get('title',''),f'/rac/{k}/new',c.get('icon','mi-clipboard')) for k,c in RAC_MODULES.items() if c.get('custom') and c.get('placement')=='permit']
    hist=build_doc_history(request,user,list(MODULES.keys()),{k:t for t,k,_ in EMISSION_PERMITS})
    return templates.TemplateResponse(request,'emission_permits.html',context(request,permit_options=list(EMISSION_PERMITS)+extra,history=hist,history_title='Histórico de Permissões',history_empty='Nenhuma permissão emitida ainda.',history_col='Permissão'))

def rac_response_options(kind: str) -> list[tuple[str,str]]:
    cfg=RAC_MODULES[kind]
    if cfg.get('response_options'):
        return [(str(v),str(l)) for v,l in cfg['response_options']]
    if cfg.get('response_mode')=='sim_nao':
        # RACs com Sim/Não também possuem requisitos condicionais.
        # N/A evita registrar falsa não conformidade quando o requisito
        # realmente não se aplica ao método/equipamento da atividade.
        return [('SIM','Sim'),('NAO','Não'),('NA','N/A')]
    return [('ATENDE','Atende'),('NAO_ATENDE','Não atende'),('NA','N/A')]

def rac_items(kind: str) -> list[dict]:
    items=[]
    for group in RAC_MODULES[kind].get('groups',[]):
        for item in group.get('items',[]):
            items.append(item)
    return items

def rac_groups_for_view(kind: str) -> list[dict]:
    groups=[]; idx=0
    for group in RAC_MODULES[kind].get('groups',[]):
        out=[]
        for item in group.get('items',[]):
            row=dict(item); row['index']=idx; out.append(row); idx+=1
        groups.append({'name':group.get('name',''),'items':out})
    return groups

def rac_defaults(kind: str) -> dict:
    count=len(rac_items(kind))
    return {
        'code':next_code(kind),'status':'Rascunho','cluster':'','site':'','contractor':'','activity':'',
        'inspection_date':local_today().strftime('%d/%m/%Y'),'responsible_name':'','signature_image':'',
        'answers':['']*count,'observations':['']*count,'evidence_photos':[[] for _ in range(count)],
        'action_plans':[{'action':'','responsible':'','due_date':'','status':'Pendente'} for _ in range(count)],
        'general_observations':'','score':None,
    }

def normalize_rac_data(kind: str, data: dict) -> dict:
    d=dict(data or {})
    count=len(rac_items(kind))
    d['cluster'],d['site']=split_separate_cluster_site(d.get('cluster',''),d.get('site',''))
    d.setdefault('answers',[]); d['answers']=(list(d['answers'])+['']*count)[:count]
    d.setdefault('observations',[]); d['observations']=(list(d['observations'])+['']*count)[:count]
    d.setdefault('evidence_photos',[])
    raw_photos=(list(d['evidence_photos'])+[[] for _ in range(count)])[:count]
    d['evidence_photos']=[([clean(x) for x in row if clean(x)] if isinstance(row,list) else ([clean(row)] if clean(row) else [])) for row in raw_photos]
    raw_plans=d.get('action_plans') if isinstance(d.get('action_plans'),list) else []
    plans=[]
    for i in range(count):
        raw=raw_plans[i] if i < len(raw_plans) and isinstance(raw_plans[i],dict) else {}
        due=clean(raw.get('due_date'))
        plans.append({
            'action':clean(raw.get('action')),
            'responsible':clean(raw.get('responsible')),
            'due_date':due,
            'due_date_input':date_input(due),
            'status':clean(raw.get('status')) or 'Pendente',
        })
    d['action_plans']=plans
    d.setdefault('general_observations','')
    d['inspection_date_input']=date_input(d.get('inspection_date',''))
    return d

def calculate_rac_score(kind: str, answers: list[str]) -> float|None:
    from .rac_reports import adherence
    count = sum(len(group.get('items', [])) for group in RAC_MODULES[kind].get('groups', []))
    score = adherence(answers, count)['score']
    return round(score, 1) if score is not None else None

@app.get('/rac',response_class=HTMLResponse)
def rac_page(request: Request, q: str='', rac_kind: str='', status: str='', period: str='', date_from: str='', date_to: str='', creator: str='', company: str='', cluster: str='', site: str='', sort: str='recent'):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)

    q=clean(q); rac_kind=clean(rac_kind); status=clean(status); period=clean(period).lower()
    date_from=clean(date_from); date_to=clean(date_to); creator=clean(creator); company=clean(company)
    cluster=clean(cluster); site=clean(site); sort=clean(sort).lower() or 'recent'
    if rac_kind not in RAC_MODULES: rac_kind=''
    if sort not in {'recent','oldest'}: sort='recent'
    if period not in {'today','7days','month','custom'}: period=''

    today=local_today()
    if period=='today':
        date_from=date_to=today.strftime('%Y-%m-%d')
    elif period=='7days':
        date_from=(today-timedelta(days=6)).strftime('%Y-%m-%d')
        date_to=today.strftime('%Y-%m-%d')
    elif period=='month':
        date_from=today.replace(day=1).strftime('%Y-%m-%d')
        date_to=today.strftime('%Y-%m-%d')

    with SessionLocal() as db:
        query=db.query(Document).filter(Document.kind.in_(list(RAC_MODULES.keys())))
        if rac_kind: query=query.filter(Document.kind==rac_kind)
        if status: query=query.filter(Document.status==status)
        if cluster: query=query.filter(Document.cluster==cluster)
        if site: query=query.filter(Document.site==site)
        if q:
            s=f'%{q}%'
            query=query.filter(or_(Document.code.ilike(s),Document.title.ilike(s),Document.activity.ilike(s),Document.cluster.ilike(s),Document.site.ilike(s)))
        if date_from:
            try: query=query.filter(Document.updated_at>=datetime.combine(datetime.strptime(date_from,'%Y-%m-%d').date(),datetime.min.time()))
            except ValueError: date_from=''
        if date_to:
            try: query=query.filter(Document.updated_at<datetime.combine(datetime.strptime(date_to,'%Y-%m-%d').date()+timedelta(days=1),datetime.min.time()))
            except ValueError: date_to=''
        if creator.isdigit(): query=query.filter(Document.created_by==int(creator))
        else: creator=''

        ordering=Document.updated_at.asc() if sort=='oldest' else desc(Document.updated_at)
        candidates=query.order_by(ordering).limit(1200).all()
        rows=[d for d in candidates if user_can_list_document(user,d)]

        if company:
            needle_company=company.casefold()
            rows=[d for d in rows if needle_company in document_company_search_text(d).casefold()]

        # O código visual da RAC é calculado e pode não existir em Document.code.
        if q and not rows:
            fallback=db.query(Document).filter(Document.kind.in_(list(RAC_MODULES.keys())))
            if rac_kind: fallback=fallback.filter(Document.kind==rac_kind)
            if status: fallback=fallback.filter(Document.status==status)
            if cluster: fallback=fallback.filter(Document.cluster==cluster)
            if site: fallback=fallback.filter(Document.site==site)
            if date_from:
                fallback=fallback.filter(Document.updated_at>=datetime.combine(datetime.strptime(date_from,'%Y-%m-%d').date(),datetime.min.time()))
            if date_to:
                fallback=fallback.filter(Document.updated_at<datetime.combine(datetime.strptime(date_to,'%Y-%m-%d').date()+timedelta(days=1),datetime.min.time()))
            if creator: fallback=fallback.filter(Document.created_by==int(creator))
            raw=fallback.order_by(ordering).limit(1500).all()
            raw=[d for d in raw if user_can_list_document(user,d)]
            if company:
                needle_company=company.casefold()
                raw=[d for d in raw if needle_company in document_company_search_text(d).casefold()]
            q_norm=q.upper()
            rows=[d for d in raw if q_norm in doc_reference_code(d).upper()]

        visible_all=db.query(Document).filter(Document.kind.in_(list(RAC_MODULES.keys()))).order_by(desc(Document.updated_at)).limit(2000).all()
        visible_all=[d for d in visible_all if user_can_list_document(user,d)]
        rac_statuses=sorted({clean(d.status) for d in visible_all if clean(d.status)}, key=lambda x:x.casefold())
        master_clusters,master_cluster_sites=separate_clusters_for_user(user)
        cluster_values={clean(c) for c in master_clusters if clean(c)}
        cluster_values.update({clean(d.cluster) for d in visible_all if clean(d.cluster)})
        rac_clusters=sorted(cluster_values,key=lambda x:x.casefold())
        site_sets={c:set(master_cluster_sites.get(c,[])) for c in rac_clusters}
        for d in visible_all:
            c=clean(d.cluster); st=clean(d.site)
            if c and st: site_sets.setdefault(c,set()).add(st)
        rac_cluster_sites={c:sorted(v,key=lambda x:x.casefold()) for c,v in site_sets.items()}
        if is_admin_user(user):
            creator_options=[{'id':u.id,'name':u.full_name or u.username} for u in db.query(User).filter(User.role!=ROLE_DEV).order_by(User.full_name,User.username).all()]
        else:
            creator_options=[{'id':user.id,'name':user.full_name or user.username}]
        for d in rows: db.expunge(d)

    cards=[{'kind':kind,**cfg} for kind,cfg in RAC_MODULES.items() if cfg.get('placement','rac')=='rac']
    return templates.TemplateResponse(request,'rac.html',context(
        request,rac_cards=cards,rac_documents=rows,
        q=q,rac_kind_filter=rac_kind,status_filter=status,period_filter=period,
        date_from_filter=date_from,date_to_filter=date_to,creator_filter=creator,
        company_filter=company,cluster_filter=cluster,site_filter=site,sort_filter=sort,
        rac_statuses=rac_statuses,rac_clusters=rac_clusters,rac_cluster_sites=rac_cluster_sites,
        creator_options=creator_options
    ))

@app.get('/rac/{kind}/new',response_class=HTMLResponse)
def rac_new(request: Request, kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in RAC_MODULES: raise HTTPException(404)
    d=rac_defaults(kind)
    d['responsible_name']=user.full_name or user.username
    prefill_location(user,d)
    d=normalize_rac_data(kind,d)
    return templates.TemplateResponse(
        request,'rac_form.html',
        context(request,cfg=RAC_MODULES[kind],kind=kind,data=d,doc=None,
                groups=rac_groups_for_view(kind),response_options=rac_response_options(kind),
                clusters=list(SEPARATE_CLUSTERS),cluster_sites={k:list(v) for k,v in SEPARATE_CLUSTER_SITES.items()})
    )

@app.get('/rac/{kind}/{doc_id}/edit',response_class=HTMLResponse)
def rac_edit(request: Request, kind: str, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in RAC_MODULES: raise HTTPException(404)
    doc=get_document(doc_id)
    if doc.kind!=kind: raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar este documento.')
    if doc.status=='Finalizada':
        return RedirectResponse(f'/document/{doc.id}/pdf',303)
    d=normalize_rac_data(kind,doc_data(doc))
    return templates.TemplateResponse(
        request,'rac_form.html',
        context(request,cfg=RAC_MODULES[kind],kind=kind,data=d,doc=doc,
                groups=rac_groups_for_view(kind),response_options=rac_response_options(kind),
                clusters=list(SEPARATE_CLUSTERS),cluster_sites={k:list(v) for k,v in SEPARATE_CLUSTER_SITES.items()})
    )

async def parse_rac(request: Request, kind: str, old: dict) -> tuple[dict,str]:
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    count=len(rac_items(kind))
    d={
        'code':old.get('code') or next_code(kind),
        'status':old.get('status','Rascunho'),
        'cluster':clean(form.get('cluster')),
        'site':clean(form.get('site')),
        'contractor':clean(form.get('contractor')),
        'activity':clean(form.get('activity')),
        'inspection_date':br_date(form.get('inspection_date')) if form.get('inspection_date') else clean(old.get('inspection_date')),
        'responsible_name':clean(form.get('responsible_name')),
        'general_observations':clean(form.get('general_observations')),
    }
    d['cluster'],d['site']=sanitize_separate_cluster_site(d['cluster'],d['site'])
    d['answers']=[clean(form.get(f'answer_{i}')) for i in range(count)]
    d['observations']=[clean(form.get(f'observation_{i}')) for i in range(count)]
    raw_old=(list(old.get('evidence_photos') or [])+[[] for _ in range(count)])[:count]
    old_photos=[(list(row) if isinstance(row,list) else ([row] if row else [])) for row in raw_old]
    d['evidence_photos']=[]
    for i in range(count):
        existing=[clean(x) for x in old_photos[i] if clean(x)]
        remove_indexes=set()
        for value in form.getlist(f'remove_evidence_{i}'):
            try: remove_indexes.add(int(value))
            except Exception: pass
        kept=[]
        for pos,rel in enumerate(existing):
            if pos in remove_indexes: remove_rac_evidence_photo(rel)
            else: kept.append(rel)
        for upload in form.getlist(f'evidence_photo_{i}'):
            if len(kept) >= 3: break
            if upload is not None and getattr(upload,'filename',''):
                saved=await save_photo_or_flash(request,upload,f"{d['code']}_item_{i+1}")
                if saved: kept.append(saved)
        d['evidence_photos'].append(kept)
    d['no_justifications']=[clean(form.get(f'no_justification_{i}'))[:1500] if clean(form.get(f'answer_{i}')) in {'NAO_ATENDE','NAO'} else '' for i in range(count)]
    d['action_plans']=[]
    for i in range(count):
        due_raw=clean(form.get(f'action_due_date_{i}'))
        d['action_plans'].append({
            'action':clean(form.get(f'action_plan_{i}')),
            'responsible':clean(form.get(f'action_responsible_{i}')),
            'due_date':br_date(due_raw) if due_raw else '',
            'status':clean(form.get(f'action_status_{i}')) or 'Pendente',
        })
    d['signature_image']=save_signature(form.get('sig_responsible'),clean(old.get('signature_image')),f"{d['code']}_rac")
    d['score']=calculate_rac_score(kind,d['answers'])
    action=clean(form.get('action')) or 'draft'
    return d,action

def process_rac_save(request: Request,user: User,kind: str,doc: Document|None,d: dict,action: str):
    old_data=doc_data(doc) if doc else {}
    if action!='finalize':
        clear_validation_state(d)
        saved=save_doc(doc,kind,d,user,'Rascunho')
        audit(user.id,'salvar_rascunho_rac',f'{saved.code} {kind}')
        flash(request,'Rascunho da RAC salvo com sucesso.','success')
        return RedirectResponse(f'/rac/{kind}/{saved.id}/edit',303)

    missing_fields=[]
    if not d.get('cluster'): missing_fields.append('cluster')
    if not d.get('site'): missing_fields.append('site')
    if not d.get('activity'): missing_fields.append('activity')
    if not d.get('inspection_date'): missing_fields.append('inspection_date')
    if not d.get('responsible_name'): missing_fields.append('responsible_name')
    allowed={value for value,_ in rac_response_options(kind)}
    missing_answers=[i for i,a in enumerate(d.get('answers') or []) if a not in allowed]
    if missing_answers:
        missing_fields.extend(f'answer_{i}' for i in missing_answers)
    nonconforming=[i for i,a in enumerate(d.get('answers') or []) if a in {'NAO_ATENDE','NAO'}]
    # Resposta negativa não bloqueia: exige apenas a justificativa do item (plano de ação é opcional).
    action_plan_missing=[]
    just=d.get('no_justifications') or []
    for i in nonconforming:
        if not (i < len(just) and clean(just[i])):
            missing_fields.append(f'no_justification_{i}'); action_plan_missing.append(i)
    if not clean(d.get('signature_image')):
        missing_fields.append('sig_responsible')
    if missing_fields:
        saved=save_validation_state(doc,kind,d,user,missing_fields,'Rascunho')
        parts=[]
        if any(x in missing_fields for x in ('cluster','site','activity','inspection_date','responsible_name')):
            parts.append('preencha os dados gerais obrigatórios')
        if missing_answers:
            parts.append(f'responda todos os itens ({len(missing_answers)} pendente(s))')
        if action_plan_missing:
            parts.append(f'justifique os itens com resposta negativa ({len(action_plan_missing)} pendente(s))')
        if 'sig_responsible' in missing_fields:
            parts.append('registre a rubrica do responsável')
        flash(request,'Não foi possível finalizar a RAC: '+', '.join(parts)+'. O que já foi preenchido foi mantido.','error')
        return RedirectResponse(f'/rac/{kind}/{saved.id}/edit',303)

    try:
        d['score']=calculate_rac_score(kind,d['answers'])
        clear_validation_state(d)
        saved=save_doc(doc,kind,d,user,'Finalizada')
        saved=finalize_pdf(saved,d)
    except Exception as e:
        if 'saved' in locals():
            with SessionLocal() as db:
                target=db.get(Document,saved.id)
                if target:
                    rollback=doc_data(target); rollback['status']='Rascunho'
                    target.status='Rascunho'; target.finalized_at=None; target.data_json=json.dumps(rollback,ensure_ascii=False); target.updated_at=now(); db.commit()
            flash(request,f'O PDF não foi gerado. A RAC permaneceu como rascunho: {e}','error')
            return RedirectResponse(f'/rac/{kind}/{saved.id}/edit',303)
        raise
    audit(user.id,'finalizar_rac',f'{saved.code} {kind}')
    flash(request,f'{doc_reference_code(saved)} finalizada com sucesso.','success')
    return RedirectResponse(f'/document/{saved.id}/pdf',303)

@app.post('/rac/{kind}/save')
async def rac_create_save(request: Request, kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in RAC_MODULES: raise HTTPException(404)
    old=rac_defaults(kind); d,action=await parse_rac(request,kind,old)
    return process_rac_save(request,user,kind,None,d,action)

@app.post('/rac/{kind}/{doc_id}/save')
async def rac_update_save(request: Request, kind: str, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in RAC_MODULES: raise HTTPException(404)
    doc=get_document(doc_id)
    if doc.kind!=kind: raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar este documento.')
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    d,action=await parse_rac(request,kind,doc_data(doc))
    return process_rac_save(request,user,kind,doc,d,action)

@app.get('/rac/{kind}/{doc_id}/evidence/{idx}')
@app.get('/rac/{kind}/{doc_id}/evidence/{idx}/{photo_idx}')
def rac_evidence_photo(request: Request, kind: str, doc_id: int, idx: int, photo_idx: int=0):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in RAC_MODULES: raise HTTPException(404)
    doc=get_document(doc_id)
    if doc.kind!=kind or not user_can_access_document(user,doc): raise HTTPException(403)
    data=normalize_rac_data(kind,doc_data(doc))
    photos=data.get('evidence_photos') or []
    if idx<0 or idx>=len(photos): raise HTTPException(404)
    item_photos=photos[idx] if isinstance(photos[idx],list) else ([photos[idx]] if photos[idx] else [])
    if photo_idx<0 or photo_idx>=len(item_photos) or not item_photos[photo_idx]: raise HTTPException(404)
    path=(STORAGE_DIR/Path(item_photos[photo_idx])).resolve()
    if EVIDENCE_DIR not in path.parents or not path.exists() or not path.is_file(): raise HTTPException(404)
    return FileResponse(path,media_type='image/png',headers={'Cache-Control':'private, no-store'})

@app.get('/rac/{kind}/modelo')
def rac_source_template(request: Request, kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in RAC_MODULES: raise HTTPException(404)
    safe=Path(RAC_MODULES[kind]['source_file']).name
    base_dir=(STORAGE_DIR/'custom_docs') if RAC_MODULES[kind].get('custom') else RAC_TEMPLATES_DIR
    path=(base_dir/safe).resolve()
    if path.parent!=base_dir.resolve() or not path.exists() or not path.is_file():
        raise HTTPException(404,'Modelo original não encontrado.')
    media='application/pdf' if path.suffix.lower()=='.pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    if media=='application/pdf':
        preview=pdf_preview_response(request,path)
        if preview is not None: return preview
    if media=='application/pdf' and request.query_params.get('raw')!='1':
        return templates.TemplateResponse(request,'pdf_viewer.html',context(
            request,doc=None,pdf_title=f'Modelo {RAC_MODULES[kind].get("title") or kind}',pdf_error='',
            raw_pdf_url=f'/rac/{kind}/modelo?raw=1',daily_signature_url='',
        ))
    return FileResponse(path,filename=safe,media_type=media,
                        headers={'Cache-Control':'private, no-store, max-age=0'})

@app.get('/admin/documentos-automaticos',response_class=HTMLResponse)
def custom_docs_page(request: Request):
    admin=require_dev(request)
    with SessionLocal() as db:
        rows=[]
        for kind,cfg in custom_docs.load_registry(STORAGE_DIR).items():
            used=db.query(Document).filter(Document.kind==kind).count()
            rows.append({'kind':kind,'cfg':cfg,'used':used})
    return templates.TemplateResponse(request,'custom_docs.html',context(request,rows=rows,response_modes=custom_docs.RESPONSE_MODES,placements=custom_docs.PLACEMENTS,modes_by_placement={p:custom_docs.modes_for(p) for p in custom_docs.PLACEMENTS}))

@app.post('/admin/documentos-automaticos/criar')
async def custom_docs_create(request: Request):
    admin=require_dev(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    title=clean_single_line(form.get('title'))[:100]
    mode=clean(form.get('response_mode'))
    placement=clean(form.get('placement'))
    upload=form.get('file')
    if not title:
        flash(request,'Informe o nome do documento.','error'); return RedirectResponse('/admin/documentos-automaticos',303)
    if not upload or not str(getattr(upload,'filename','') or '').lower().endswith('.xlsx'):
        flash(request,'Envie a planilha no formato .xlsx.','error'); return RedirectResponse('/admin/documentos-automaticos',303)
    content=await upload.read()
    if not content or len(content)>8*1024*1024:
        flash(request,'A planilha está vazia ou excede 8 MB.','error'); return RedirectResponse('/admin/documentos-automaticos',303)
    try:
        kind,cfg=custom_docs.create_type(STORAGE_DIR,title,mode,placement,upload.filename,content)
    except ValueError as exc:
        flash(request,str(exc),'error'); return RedirectResponse('/admin/documentos-automaticos',303)
    except Exception:
        flash(request,'Não foi possível ler a planilha. Confira se o arquivo é um .xlsx válido.','error'); return RedirectResponse('/admin/documentos-automaticos',303)
    audit(admin.id,'criar_tipo_documento',f'{kind} | itens={cfg["item_count"]}')
    flash(request,f'Documento “{title}” criado com {cfg["item_count"]} item(ns). Ele aparece em: {custom_docs.PLACEMENTS.get(cfg["placement"],"RAC")}.','success')
    return RedirectResponse('/admin/documentos-automaticos',303)

@app.post('/admin/documentos-automaticos/{kind}/excluir')
async def custom_docs_delete(request: Request, kind: str):
    admin=require_dev(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    if kind not in custom_docs.load_registry(STORAGE_DIR): raise HTTPException(404)
    with SessionLocal() as db:
        if db.query(Document).filter(Document.kind==kind).count():
            flash(request,'Este tipo já tem documentos emitidos e não pode ser removido.','error'); return RedirectResponse('/admin/documentos-automaticos',303)
    custom_docs.delete_type(STORAGE_DIR,kind)
    audit(admin.id,'excluir_tipo_documento',kind)
    flash(request,'Tipo de documento removido.','success')
    return RedirectResponse('/admin/documentos-automaticos',303)


# -------------------- Ferramentas do DEV ("modo deus") --------------------
TI_DOC_STATUSES=['Rascunho','Aguardando aprovação','Pendente assinatura','Em andamento','Finalizada','Substituída']

def _dev_ctx(request: Request, section: str, **kw):
    return context(request,section=section,**kw)

def _dev_redirect(path: str, request: Request, message: str, level: str='success'):
    flash(request,message,level); return RedirectResponse(path,303)

@app.get('/dev/sso',response_class=HTMLResponse)
def dev_sso(request: Request):
    require_dev(request)
    info={'enabled':sso.enabled(),'flag':os.getenv('SSO_ENABLED','').strip().lower() in {'1','true','yes','sim'},
          'tenant':sso.tenant_id(),'client':sso.client_id(),'secret':bool(sso.client_secret()),
          'redirect':sso.redirect_uri(),'domains':', '.join(sorted(sso.allowed_domains()))}
    with SessionLocal() as db:
        logs=db.query(AuditLog).filter(AuditLog.action.in_(('login_sso','login_sso_falha'))).order_by(desc(AuditLog.id)).limit(50).all()
        no_email=[u.username for u in db.query(User).filter(User.active==True,User.role!=ROLE_DEV).all() if '@' not in (u.username or '')]
        for l in logs: db.expunge(l)
    return templates.TemplateResponse(request,'dev_sso.html',_dev_ctx(request,'sso',sso=info,logs=logs,no_email=sorted(no_email)))

@app.get('/dev/recursos-emergencia',response_class=HTMLResponse)
def ti_emergency_page(request: Request, unidade: str=''):
    require_dev(request)
    from .external_resources import load_units
    units=load_units(STORAGE_DIR)
    cur=next((u for u in units if u['key']==unidade),units[0] if units else None)
    return templates.TemplateResponse(request,'ti_recursos_emergencia.html',context(request,units=units,cur=cur,all_clusters=list(CLUSTERS)))

@app.post('/dev/recursos-emergencia/salvar')
async def ti_emergency_save(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    from .external_resources import load_units,save_units
    units=load_units(STORAGE_DIR); key=clean(form.get('unit_key'))
    u=next((x for x in units if x['key']==key),None)
    if not u: return _dev_redirect('/dev/recursos-emergencia',request,'Unidade não encontrada.','error')
    name=clean(form.get('name'))
    if not name: return _dev_redirect(f'/dev/recursos-emergencia?unidade={key}',request,'Informe o nome da unidade.','error')
    names=form.getlist('res_name'); phones=form.getlist('res_phone'); addrs=form.getlist('res_addr')
    res=[[clean(n),clean(phones[i]) if i<len(phones) else '',clean(addrs[i]) if i<len(addrs) else ''] for i,n in enumerate(names) if clean(n)]
    u['name']=name; u['state']=clean(form.get('state')).upper()[:2]
    u['clusters']=[c for c in form.getlist('clusters') if c in CLUSTERS]
    before=len(u['resources']); u['resources']=res
    save_units(STORAGE_DIR,units)
    audit(admin.id,'ti_editar_recursos_emergencia',f"{u['name']} | recursos {before} -> {len(res)} | clusters={len(u['clusters'])}")
    return _dev_redirect(f'/dev/recursos-emergencia?unidade={key}',request,f"Recursos de emergência de {u['name']} salvos ({len(res)} recursos).")

@app.post('/dev/recursos-emergencia/nova')
async def ti_emergency_new(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    from .external_resources import load_units,save_units,slugify
    units=load_units(STORAGE_DIR); name=clean(form.get('name'))
    if not name: return _dev_redirect('/dev/recursos-emergencia',request,'Informe o nome da nova unidade.','error')
    base=slugify(name); key=base; n=2
    while any(x['key']==key for x in units): key=f'{base}-{n}'; n+=1
    units.append({'key':key,'name':name,'state':clean(form.get('state')).upper()[:2],'clusters':[],'resources':[]})
    save_units(STORAGE_DIR,units); audit(admin.id,'ti_criar_unidade_emergencia',name)
    return _dev_redirect(f'/dev/recursos-emergencia?unidade={key}',request,f'Unidade {name} criada. Adicione os recursos e vincule os clusters.')

@app.post('/dev/recursos-emergencia/excluir')
async def ti_emergency_delete(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    from .external_resources import load_units,save_units
    units=load_units(STORAGE_DIR); key=clean(form.get('unit_key'))
    u=next((x for x in units if x['key']==key),None)
    if not u: return _dev_redirect('/dev/recursos-emergencia',request,'Unidade não encontrada.','error')
    save_units(STORAGE_DIR,[x for x in units if x['key']!=key]); audit(admin.id,'ti_excluir_unidade_emergencia',u['name'])
    return _dev_redirect('/dev/recursos-emergencia',request,f"Unidade {u['name']} excluída.")

@app.post('/dev/recursos-emergencia/restaurar')
async def ti_emergency_restore(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    f=STORAGE_DIR/'external_resources.json'
    if f.exists(): f.unlink()
    audit(admin.id,'ti_restaurar_recursos_emergencia','padrão')
    return _dev_redirect('/dev/recursos-emergencia',request,'Lista restaurada para o padrão original.')

@app.get('/dev/atualizacoes',response_class=HTMLResponse)
def ti_updates_page(request: Request):
    require_dev(request)
    return templates.TemplateResponse(request,'ti_atualizacoes.html',context(request,releases=get_releases(STORAGE_DIR),maint=ti_tools.maintenance_state(STORAGE_DIR)))

@app.post('/dev/atualizacoes/editar')
async def ti_updates_edit(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    version=clean(form.get('version')); title=clean(form.get('title'))
    items=[clean(x) for x in (form.get('items') or '').splitlines()]
    if not title or not any(items):
        return _dev_redirect('/dev/atualizacoes',request,'Informe o título e pelo menos um tópico.','error')
    if not edit_release(STORAGE_DIR,version,title,items):
        return _dev_redirect('/dev/atualizacoes',request,'Versão não encontrada.','error')
    audit(admin.id,'ti_editar_atualizacao',f'versao={version} | {title}')
    return _dev_redirect('/dev/atualizacoes',request,f'Versão {version} atualizada no histórico.')

@app.post('/dev/atualizacoes/excluir')
async def ti_updates_delete(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    version=clean(form.get('version')); err=delete_release(STORAGE_DIR,version)
    if err: return _dev_redirect('/dev/atualizacoes',request,err,'error')
    audit(admin.id,'ti_excluir_atualizacao',f'versao={version}')
    return _dev_redirect('/dev/atualizacoes',request,f'Versão {version} removida do histórico.')

@app.post('/dev/atualizacoes/publicar')
async def ti_updates_publish(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    title=clean(form.get('title'))
    items=[clean(x) for x in (form.get('items') or '').splitlines()]
    if not title or not any(items):
        return _dev_redirect('/dev/atualizacoes',request,'Informe o título e pelo menos um tópico do que mudou.','error')
    rel=publish_release(STORAGE_DIR,title,items,admin.full_name or admin.username)
    audit(admin.id,'ti_publicar_atualizacao',f"versao={rel['version']} | {rel['title']}")
    return _dev_redirect('/dev/atualizacoes',request,f"Atualização {rel['version']} publicada. Os usuários verão o aviso de nova versão e as novidades.")

def _broadcast_push(title: str, body: str, url: str='/') -> None:
    """Envia um push a todos os aparelhos cadastrados (em segundo plano)."""
    def run():
        try:
            with SessionLocal() as db:
                subs=db.query(PushSubscription).filter(PushSubscription.active==True).all()
                for sub in subs:
                    ok,gone,detail=send_web_push(sub,{'title':title,'body':body,'url':url,'tag':'safety-plus-manutencao',
                        'icon':'/static/icons/safety-plus-icon-192-v361831.png','badge':'/static/icons/safety-plus-favicon-64-v361831.png'},STORAGE_DIR)
                    if gone: sub.active=False
                db.commit()
        except Exception:
            pass
    threading.Thread(target=run,daemon=True,name='safety-plus-broadcast').start()


@app.post('/dev/manutencao/agendar')
async def ti_maintenance_schedule(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    msg=clean(form.get('message'))[:300]
    try:
        start=datetime.strptime(clean(form.get('start')),'%Y-%m-%dT%H:%M').replace(tzinfo=LOCAL_TZ)
        end=datetime.strptime(clean(form.get('end')),'%Y-%m-%dT%H:%M').replace(tzinfo=LOCAL_TZ)
    except ValueError:
        return _dev_redirect('/dev/atualizacoes',request,'Informe a data e hora de início e de retorno previsto.','error')
    if end<=start or end.timestamp()<=time.time():
        return _dev_redirect('/dev/atualizacoes',request,'O retorno previsto precisa ser depois do início e no futuro.','error')
    if not msg: msg='O sistema ficará indisponível para manutenção programada.'
    sched={'start_ts':start.timestamp(),'end_ts':end.timestamp(),'start_label':start.strftime('%d/%m/%Y %H:%M'),
           'end_label':end.strftime('%d/%m/%Y %H:%M'),'message':msg,'popup':clean(form.get('popup'))=='1','created_by':admin.full_name or admin.username}
    ti_tools.set_maintenance_schedule(STORAGE_DIR,sched)
    audit(admin.id,'ti_agendar_parada',f"{sched['start_label']} ate {sched['end_label']} | {msg}")
    if clean(form.get('notify'))=='1':
        _broadcast_push('Parada programada do sistema',f"{sched['start_label']} até {sched['end_label']}. {msg}")
    return _dev_redirect('/dev/atualizacoes',request,'Parada programada. Todos os usuários verão o aviso no sistema; no horário o acesso é bloqueado, exceto para o DEV')

@app.post('/dev/manutencao/cancelar-agenda')
async def ti_maintenance_cancel(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    ti_tools.set_maintenance_schedule(STORAGE_DIR,None)
    audit(admin.id,'ti_cancelar_parada','agenda removida')
    return _dev_redirect('/dev/atualizacoes',request,'Parada programada cancelada e aviso removido.')

@app.get('/dev',response_class=HTMLResponse)
def ti_home(request: Request):
    require_dev(request)
    with SessionLocal() as db:
        counts={'Usuários':db.query(User).count(),'Documentos':db.query(Document).count(),'Finalizados':db.query(Document).filter(Document.status=='Finalizada').count(),
                'Colaboradores':db.query(Participant).count(),'Empresas':db.query(Company).count(),'Notificações':db.query(Notification).count(),
                'Notificações lidas':db.query(Notification).filter(Notification.read==True).count()}
        logs=db.query(AuditLog).order_by(desc(AuditLog.id)).limit(60).all()
        names={u.id:(u.full_name or u.username) for u in db.query(User).all()}
        for l in logs: db.expunge(l)
    sizes={n:ti_tools.dir_size(STORAGE_DIR/n) for n in ti_tools.FILE_DIRS+(ti_tools.BACKUP_DIR,)}
    stats=ti_tools.system_stats(STORAGE_DIR)
    info={'Banco':engine.dialect.name,'Pasta de dados':str(STORAGE_DIR),'Documentos customizados':len(custom_docs.load_registry(STORAGE_DIR))}
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'home',counts=counts,logs=logs,names=names,sizes=sizes,info=info,stats=stats,maint=ti_tools.maintenance_state(STORAGE_DIR),settings=ti_tools.load_settings(STORAGE_DIR)))


_CL_CACHE={'t':0,'v':None}
def cluster_storage(force=False):
    """GB de documentos (PDFs, assinaturas, evidências) por cluster. Cache de 60 s."""
    if not force and _CL_CACHE['v'] is not None and time.time()-_CL_CACHE['t']<60: return _CL_CACHE['v']
    with SessionLocal() as db:
        rows=db.query(Document.code,Document.cluster,Document.pdf_path).all()
    by_code={c:(cl or '(sem cluster)') for c,cl,_ in rows}
    out={}; seen=set()
    def add(cl,sz,files=1):
        o=out.setdefault(cl,{'bytes':0,'files':0,'docs':0}); o['bytes']+=sz; o['files']+=files
    for c,cl,pp in rows:
        out.setdefault(cl or '(sem cluster)',{'bytes':0,'files':0,'docs':0})['docs']+=1
        if pp:
            f=STORAGE_DIR/pp
            if f.is_file() and f not in seen: seen.add(f); add(cl or '(sem cluster)',f.stat().st_size)
    for d in ('pdfs','signatures','evidence'):
        base=STORAGE_DIR/d
        if not base.is_dir(): continue
        for f in base.rglob('*'):
            if not f.is_file() or f in seen: continue
            code=f.name.split('_')[0]
            add(by_code.get(code,'(sem vínculo)'),f.stat().st_size)
    res=sorted(({'cluster':k,**v} for k,v in out.items()),key=lambda x:-x['bytes'])
    _CL_CACHE.update(t=time.time(),v=res); return res

@app.get('/dev/monitoramento',response_class=HTMLResponse)
def ti_monitor(request: Request, aba: str='servidor', janela: int=15):
    require_dev(request)
    aba=aba if aba in ('servidor','usuarios','requisicoes','erros','banco','robo') else 'servidor'
    janela=janela if janela in (5,15,30,60) else 15
    ctx={'aba':aba,'janela':janela}
    if aba=='robo':
        ctx['robot']=ti_tools.robot_status()
    elif aba=='servidor':
        ctx['stats']=ti_tools.system_stats(STORAGE_DIR); ctx['mon']=monitor.summary(janela)
        ctx['clusters']=cluster_storage()
    elif aba=='usuarios':
        rows=monitor.online_users(5)
        with SessionLocal() as db:
            names={u.id:(u.full_name or u.username,u.role) for u in db.query(User).filter(User.id.in_([r[0] for r in rows] or [0])).all()}
            ctx['total_users']=db.query(User).filter(User.role!=ROLE_DEV).count()
        ctx['online']=[{'name':names.get(u,('(removido)',''))[0],'role':names.get(u,('',''))[1],'last':datetime.fromtimestamp(ts,LOCAL_TZ).strftime('%H:%M:%S'),'n':n} for u,ts,n in rows]
    elif aba=='requisicoes':
        ctx['mon']=monitor.summary(janela)
    elif aba=='erros':
        ctx['errs']=[{'ts':datetime.fromtimestamp(e[0],LOCAL_TZ).strftime('%d/%m %H:%M:%S'),'method':e[1],'path':e[2],'status':e[3],'msg':e[4],'uid':e[5]} for e in monitor.errors(100)]
    else:
        from sqlalchemy import text as _sqt
        tables=[]
        with engine.connect() as c:
            for tb in Base.metadata.sorted_tables:
                try: tables.append((tb.name,c.execute(_sqt(f'SELECT COUNT(*) FROM "{tb.name}"')).scalar()))
                except Exception: tables.append((tb.name,None))
        try: pool=engine.pool.status()
        except Exception: pool='indisponível'
        ctx['tables']=sorted(tables,key=lambda x:-(x[1] or 0)); ctx['pool']=pool
        ctx['sizes']={n:ti_tools.dir_size(STORAGE_DIR/n) for n in ti_tools.FILE_DIRS+(ti_tools.BACKUP_DIR,)}
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'monitor',**ctx))

@app.get('/dev/sistema.json')
async def ti_system_json(request: Request):
    require_dev(request)
    return JSONResponse(await asyncio.to_thread(ti_tools.system_stats,STORAGE_DIR))

@app.post('/dev/aviso')
async def ti_notice(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    st=ti_tools.load_settings(STORAGE_DIR); old=st.get('notice','')
    st['notice']=clean(form.get('notice'))[:500]; ti_tools.save_settings(STORAGE_DIR,st)
    audit(admin.id,'ti_aviso_global',f'antes={old!r} | depois={st["notice"]!r}')
    return _dev_redirect('/dev',request,'Aviso global atualizado.' if st['notice'] else 'Aviso global removido.')

@app.post('/dev/manutencao/limpar-notificacoes')
async def ti_clear_notifications(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        n=db.query(Notification).filter(Notification.read==True).delete(synchronize_session=False); db.commit()
    audit(admin.id,'ti_limpar_notificacoes',f'removidas={n}')
    return _dev_redirect('/dev',request,f'{n} notificação(ões) lida(s) removida(s).')

# ---- documentos
@app.get('/dev/documentos',response_class=HTMLResponse)
def ti_documents(request: Request, q: str='', kind: str='', status: str=''):
    require_dev(request); q=clean(q)
    with SessionLocal() as db:
        query=db.query(Document)
        if q:
            s=f'%{q}%'; query=query.filter(or_(Document.code.ilike(s),Document.activity.ilike(s),Document.cluster.ilike(s),Document.site.ilike(s),Document.title.ilike(s)))
        if kind: query=query.filter(Document.kind==kind)
        if status: query=query.filter(Document.status==status)
        total=query.count()
        docs=query.order_by(desc(Document.updated_at)).limit(100).all()
        kinds=[k for (k,) in db.query(Document.kind).distinct().order_by(Document.kind).all()]
        names={u.id:(u.full_name or u.username) for u in db.query(User).all()}
        for d in docs: db.expunge(d)
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'docs',docs=docs,total=total,q=q,kind_filter=kind,status_filter=status,kinds=kinds,statuses=TI_DOC_STATUSES,names=names,titles=DOCUMENT_TITLES))

@app.get('/dev/documentos/{doc_id}',response_class=HTMLResponse)
def ti_document(request: Request, doc_id: int):
    require_dev(request)
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404)
        creator=db.get(User,doc.created_by); db.expunge(doc)
    raw=json.dumps(doc_data(doc),ensure_ascii=False,indent=2)
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'doc',doc=doc,creator=creator,raw=raw,statuses=TI_DOC_STATUSES,titles=DOCUMENT_TITLES,pdf_exists=bool(doc.pdf_path and (STORAGE_DIR/doc.pdf_path).is_file())))

@app.post('/dev/documentos/{doc_id}/salvar')
async def ti_document_save(request: Request, doc_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    back=f'/dev/documentos/{doc_id}'
    try:
        data=json.loads(form.get('data_json') or '{}')
        if not isinstance(data,dict): raise ValueError
    except ValueError:
        return _dev_redirect(back,request,'O JSON dos dados é inválido. Nada foi salvo.','error')
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404)
        before={'status':doc.status,'cluster':doc.cluster,'site':doc.site,'activity':doc.activity,'title':doc.title,'data_json':doc.data_json}
        doc.status=clean(form.get('status')) or doc.status
        doc.cluster=clean(form.get('cluster')); doc.site=clean(form.get('site')); doc.activity=clean(form.get('activity'))
        doc.title=clean(form.get('title')) or doc.title
        doc.data_json=json.dumps(data,ensure_ascii=False)
        if doc.status!='Finalizada': doc.finalized_at=None
        elif not doc.finalized_at: doc.finalized_at=now()
        doc.updated_at=now(); db.commit()
    audit(admin.id,'ti_editar_documento',f'doc={doc_id} | antes={json.dumps(before,ensure_ascii=False)}')
    return _dev_redirect(back,request,'Documento salvo. O valor anterior ficou na auditoria.')

@app.post('/dev/documentos/{doc_id}/reabrir')
async def ti_document_reopen(request: Request, doc_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404)
        old=doc.status; data=doc_data(doc); data['status']='Rascunho'
        doc.status='Rascunho'; doc.finalized_at=None; doc.data_json=json.dumps(data,ensure_ascii=False); doc.updated_at=now(); db.commit()
    audit(admin.id,'ti_reabrir_documento',f'doc={doc_id} | status_anterior={old}')
    return _dev_redirect(f'/dev/documentos/{doc_id}',request,'Documento reaberto como Rascunho.')

@app.post('/dev/documentos/{doc_id}/pdf')
async def ti_document_pdf(request: Request, doc_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404)
        db.expunge(doc)
    try:
        finalize_pdf(doc,doc_data(doc))
    except Exception as exc:
        return _dev_redirect(f'/dev/documentos/{doc_id}',request,f'Não foi possível gerar o PDF: {exc}','error')
    audit(admin.id,'ti_regenerar_pdf',f'doc={doc_id}')
    return _dev_redirect(f'/dev/documentos/{doc_id}',request,'PDF regenerado.')

@app.post('/dev/documentos/{doc_id}/excluir')
async def ti_document_delete(request: Request, doc_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404)
        snapshot={'code':doc.code,'kind':doc.kind,'status':doc.status,'created_by':doc.created_by,'data_json':doc.data_json,'pdf_path':doc.pdf_path}
        db.query(Notification).filter(Notification.document_id==doc_id).delete(synchronize_session=False)
        try:
            from .database import SnowflakeSyncState
            db.query(SnowflakeSyncState).filter(SnowflakeSyncState.document_id==doc_id).delete(synchronize_session=False)
        except Exception: pass
        db.delete(doc); db.commit()
    if snapshot['pdf_path']:
        try: (STORAGE_DIR/snapshot['pdf_path']).unlink()
        except OSError: pass
    audit(admin.id,'ti_excluir_documento',f'doc={doc_id} | {json.dumps(snapshot,ensure_ascii=False)}')
    return _dev_redirect('/dev/documentos',request,f'Documento {snapshot["code"]} excluído. Uma cópia dos dados ficou na auditoria.')

# ---- usuários e acessos (inclui contas ocultas)
@app.get('/dev/usuarios',response_class=HTMLResponse)
def ti_users(request: Request):
    require_dev(request)
    with SessionLocal() as db:
        users=db.query(User).order_by(User.role,User.username).all()
        scope_count={}
        for s in db.query(UserScope).all(): scope_count[s.user_id]=scope_count.get(s.user_id,0)+1
        for u in users: db.expunge(u)
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'users',users=users,scope_count=scope_count,roles=[ROLE_USER,ROLE_ADMIN,ROLE_SUPER_ADMIN,ROLE_DEV]))

@app.post('/dev/usuarios/criar')
async def ti_user_create(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    username=clean(form.get('username')); password=str(form.get('password') or ''); role=clean(form.get('role'))
    if role not in {ROLE_USER,ROLE_ADMIN,ROLE_SUPER_ADMIN,ROLE_DEV}: role=ROLE_USER
    if not username or len(password)<8:
        return _dev_redirect('/dev/usuarios',request,'Informe o login e uma senha com pelo menos 8 caracteres.','error')
    with SessionLocal() as db:
        if db.query(User).filter(User.username==username).first():
            return _dev_redirect('/dev/usuarios',request,'Já existe um usuário com esse login.','error')
        db.add(User(username=username,full_name=clean(form.get('full_name')),password_hash=hash_password(password),role=role,active=True)); db.commit()
    audit(admin.id,'ti_criar_usuario',f'{username} | {role}')
    return _dev_redirect('/dev/usuarios',request,f'Usuário {username} criado.')

@app.post('/dev/usuarios/{user_id}/atualizar')
async def ti_user_update(request: Request, user_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    role=clean(form.get('role')); password=str(form.get('password') or '')
    with SessionLocal() as db:
        u=db.get(User,user_id)
        if not u: raise HTTPException(404)
        before={'full_name':u.full_name,'role':u.role,'active':u.active}
        if clean(form.get('full_name')): u.full_name=clean(form.get('full_name'))
        if role in {ROLE_USER,ROLE_ADMIN,ROLE_SUPER_ADMIN,ROLE_DEV} and user_id!=admin.id: u.role=role
        if user_id!=admin.id: u.active=form.get('active')=='1'
        reset=False
        if password:
            if len(password)<8: return _dev_redirect('/dev/usuarios',request,'A nova senha deve ter pelo menos 8 caracteres.','error')
            u.password_hash=hash_password(password); reset=True
        after={'full_name':u.full_name,'role':u.role,'active':u.active}
        db.commit(); uname=u.username
    if reset:
        revoke_password_sessions(STORAGE_DIR,user_id,request)
    changes=document_change_rows(before,after)
    if reset: changes.append({'field':'Senha','before':'Não exibida','after':'Redefinida pelo administrador'})
    audit(admin.id,'ti_atualizar_usuario',json.dumps({'code':f'Usuário {uname} (ID {user_id})','changes':changes},ensure_ascii=False))
    return _dev_redirect('/dev/usuarios',request,f'Usuário {uname} atualizado.')


# ---- auditoria completa
def _ti_audit_query(db, q: str, action: str, user_id: str, start: str, end: str):
    query=db.query(AuditLog)
    if q: query=query.filter(or_(AuditLog.detail.ilike(f'%{q}%'),AuditLog.ip_address.ilike(f'%{q}%'),AuditLog.user_agent.ilike(f'%{q}%'),AuditLog.request_path.ilike(f'%{q}%')))
    if action: query=query.filter(AuditLog.action==action)
    if user_id.isdigit(): query=query.filter(AuditLog.user_id==int(user_id))
    try:
        if start: query=query.filter(AuditLog.created_at>=datetime.strptime(start,'%Y-%m-%d'))
        if end: query=query.filter(AuditLog.created_at<datetime.strptime(end,'%Y-%m-%d')+timedelta(days=1))
    except ValueError: pass
    return query

@app.get('/dev/auditoria',response_class=HTMLResponse)
def ti_audit(request: Request, q: str='', action: str='', user_id: str='', start: str='', end: str='', page: int=1):
    require_dev(request); q=clean(q); page=max(page,1); size=50
    with SessionLocal() as db:
        query=_ti_audit_query(db,q,action,user_id,start,end)
        total=query.count()
        logs=query.order_by(desc(AuditLog.id)).offset((page-1)*size).limit(size).all()
        actions=[a for (a,) in db.query(AuditLog.action).distinct().order_by(AuditLog.action).all()]
        names={u.id:(u.full_name or u.username) for u in db.query(User).all()}
        for l in logs: db.expunge(l)
    qs={'q':q,'action':action,'user_id':user_id,'start':start,'end':end}
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'audit',logs=logs,total=total,page=page,pages=max((total+size-1)//size,1),actions=actions,names=names,audit_label=audit_label,detail_view=detail_view,f=qs,qs=urlencode({k:v for k,v in qs.items() if v})))

@app.get('/dev/auditoria.csv')
def ti_audit_csv(request: Request, q: str='', action: str='', user_id: str='', start: str='', end: str=''):
    admin=require_dev(request)
    import csv
    buf=io.StringIO(); w=csv.writer(buf,delimiter=';'); w.writerow(['id','data','id_usuario','usuario','acao','descricao','ip_origem','navegador','metodo','rota','id_requisicao','detalhe'])
    with SessionLocal() as db:
        names={u.id:(u.full_name or u.username) for u in db.query(User).all()}
        for l in _ti_audit_query(db,clean(q),action,user_id,start,end).order_by(desc(AuditLog.id)).limit(50000):
            w.writerow([csv_cell(v) for v in [l.id,l.created_at.strftime('%Y-%m-%d %H:%M:%S'),l.user_id or '',names.get(l.user_id,''),l.action,audit_label(l.action),l.ip_address,l.user_agent,l.http_method,l.request_path,l.request_id,l.detail or '']])
    audit(admin.id,'ti_exportar_auditoria',f'q={q} action={action} user={user_id}')
    return Response('﻿'+buf.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="auditoria.csv"'})

# ---- versões do documento
@app.get('/dev/documentos/{doc_id}/versoes',response_class=HTMLResponse)
def ti_document_versions(request: Request, doc_id: int):
    require_dev(request)
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404)
        versions=db.query(DocumentVersion).filter(DocumentVersion.document_id==doc_id).order_by(desc(DocumentVersion.id)).all()
        db.expunge(doc)
        for v in versions: db.expunge(v)
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'versions',doc=doc,versions=versions))

@app.post('/dev/documentos/{doc_id}/versoes/{version_id}/restaurar')
async def ti_document_version_restore(request: Request, doc_id: int, version_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        doc=db.get(Document,doc_id); v=db.get(DocumentVersion,version_id)
        if not doc or not v or v.document_id!=doc_id: raise HTTPException(404)
        doc.status=v.status or doc.status; doc.title=v.title or doc.title; doc.cluster=v.cluster; doc.site=v.site
        doc.activity=v.activity; doc.data_json=v.data_json; doc.updated_at=now()
        doc.finalized_at=doc.finalized_at if doc.status=='Finalizada' else None
        db.commit()
    audit(admin.id,'ti_restaurar_versao',f'doc={doc_id} | versao={version_id}')
    return _dev_redirect(f'/dev/documentos/{doc_id}/versoes',request,'Versão restaurada. O estado anterior também foi guardado no histórico.')

# ---- backup: automático e exclusão
@app.post('/dev/backup/automatico')
async def ti_backup_auto(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    def num(key,default,lo,hi):
        try: return min(max(int(form.get(key)),lo),hi)
        except (TypeError,ValueError): return default
    st=ti_tools.load_settings(STORAGE_DIR); old=ti_tools.auto_backup_config(STORAGE_DIR)
    st['auto_backup']={'enabled':form.get('enabled')=='1','interval_hours':num('interval_hours',24,1,720),'keep':num('keep',7,1,60),'last_run':old.get('last_run','')}
    ti_tools.save_settings(STORAGE_DIR,st)
    audit(admin.id,'ti_backup_automatico',json.dumps(st['auto_backup']))
    return _dev_redirect('/dev/backup',request,'Backup automático configurado. A primeira execução acontece em até 15 minutos.')

@app.post('/dev/backup/excluir/{name}')
async def ti_backup_delete(request: Request, name: str):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    folder=(STORAGE_DIR/ti_tools.BACKUP_DIR).resolve(); path=(folder/Path(name).name).resolve()
    if path.parent!=folder or not path.is_file(): raise HTTPException(404)
    path.unlink(); audit(admin.id,'ti_excluir_backup',path.name)
    return _dev_redirect('/dev/backup',request,f'{path.name} excluído.')



# ---- forçar logout, mover documentos, edição em massa, editar tipos
@app.post('/dev/usuarios/{user_id}/deslogar')
async def ti_user_logout(request: Request, user_id: int):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    ts=ti_tools.force_logout(STORAGE_DIR,user_id)
    if user_id==admin.id: request.session['t']=ts+1
    audit(admin.id,'ti_forcar_logout',f'user={user_id}')
    return _dev_redirect('/dev/usuarios',request,'Sessões do usuário encerradas.')

@app.post('/dev/usuarios/deslogar-todos')
async def ti_logout_all(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    ts=ti_tools.force_logout(STORAGE_DIR,None)
    request.session['t']=ts+1
    audit(admin.id,'ti_forcar_logout_todos','')
    return _dev_redirect('/dev/usuarios',request,'Todos os usuários foram deslogados (exceto você).')

@app.post('/dev/usuarios/mover-documentos')
async def ti_move_documents(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: src=int(form.get('from_user')); dst=int(form.get('to_user'))
    except (TypeError,ValueError): return _dev_redirect('/dev/usuarios',request,'Escolha o usuário de origem e o de destino.','error')
    if src==dst: return _dev_redirect('/dev/usuarios',request,'Origem e destino são o mesmo usuário.','error')
    with SessionLocal() as db:
        if not db.get(User,src) or not db.get(User,dst): raise HTTPException(404)
        rows=db.query(Document).filter(Document.created_by==src).all()
        ids=[d.id for d in rows]
        for d in rows: d.created_by=dst
        db.commit()
    audit(admin.id,'ti_mover_documentos',f'de={src} para={dst} | qtd={len(ids)} | ids={ids[:500]}')
    return _dev_redirect('/dev/usuarios',request,f'{len(ids)} documento(s) movido(s).')

@app.post('/dev/documentos/massa')
async def ti_bulk_edit(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    ids=[int(x) for x in form.getlist('ids') if str(x).isdigit()]
    status=clean(form.get('status')); cluster=clean(form.get('cluster')); site=clean(form.get('site'))
    if not ids or not (status or cluster or site):
        return _dev_redirect('/dev/documentos',request,'Marque documentos e informe ao menos um campo a alterar.','error')
    if status and status not in TI_DOC_STATUSES:
        return _dev_redirect('/dev/documentos',request,'Status inválido.','error')
    with SessionLocal() as db:
        rows=db.query(Document).filter(Document.id.in_(ids)).all()
        for d in rows:
            data=doc_data(d)
            if status:
                d.status=status; data['status']=status
                if status=='Finalizada' and not d.finalized_at: d.finalized_at=now()
                elif status!='Finalizada': d.finalized_at=None
            if cluster: d.cluster=cluster; data['cluster']=cluster
            if site: d.site=site; data['site']=site
            d.data_json=json.dumps(data,ensure_ascii=False); d.updated_at=now()
        db.commit(); n=len(rows)
    audit(admin.id,'ti_edicao_em_massa',f'qtd={n} status={status} cluster={cluster} site={site} ids={ids[:500]}')
    return _dev_redirect('/dev/documentos',request,f'{n} documento(s) atualizado(s). O estado anterior de cada um ficou no histórico de versões.')

@app.post('/admin/documentos-automaticos/{kind}/editar')
async def custom_docs_edit(request: Request, kind: str):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        used=db.query(Document).filter(Document.kind==kind).count()
    try:
        cfg=custom_docs.update_type(STORAGE_DIR,kind,clean_single_line(form.get('title'))[:100],clean(form.get('placement')),clean(form.get('response_mode')),used)
    except ValueError as exc:
        return _dev_redirect('/admin/documentos-automaticos',request,str(exc),'error')
    with SessionLocal() as db:
        for d in db.query(Document).filter(Document.kind==kind).all(): d.title=cfg['title'][:120]
        db.commit()
    audit(admin.id,'ti_editar_tipo_documento',f'{kind} | {cfg["title"]} | {cfg["placement"]} | {cfg["response_options"]}')
    return _dev_redirect('/admin/documentos-automaticos',request,'Tipo de documento atualizado.')

# ---- modo manutenção e integridade
@app.post('/dev/manutencao/modo')
async def ti_maintenance(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    on=form.get('on')=='1'; msg=clean(form.get('message'))[:300]
    ti_tools.set_maintenance(STORAGE_DIR,on,msg)
    audit(admin.id,'ti_modo_manutencao',f'on={on} | {msg}')
    return _dev_redirect('/dev',request,'Modo manutenção LIGADO: só o DEV consegue usar o sistema.' if on else 'Modo manutenção desligado.')

@app.get('/dev/integridade',response_class=HTMLResponse)
def ti_integrity(request: Request):
    require_dev(request)
    rep=ti_tools.integrity_report(engine,STORAGE_DIR)
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'integrity',rep=rep,total=sum(len(v) for v in rep.values())))

@app.post('/dev/integridade/corrigir')
async def ti_integrity_fix(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    done=await asyncio.to_thread(ti_tools.fix_orphans,engine,STORAGE_DIR,admin.id)
    audit(admin.id,'ti_corrigir_integridade',json.dumps(done))
    return _dev_redirect('/dev/integridade',request,'Correção feita: '+', '.join(f'{k}={v}' for k,v in done.items())+'. PDFs órfãos foram para a pasta quarentena, não apagados.')

@app.post('/dev/integridade/regenerar-pdfs')
async def ti_integrity_pdfs(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    rep=ti_tools.integrity_report(engine,STORAGE_DIR); ok=fail=0
    for item in rep['docs_sem_pdf']:
        with SessionLocal() as db:
            doc=db.get(Document,item['id'])
            if doc: db.expunge(doc)
        try: finalize_pdf(doc,doc_data(doc)); ok+=1
        except Exception: fail+=1
    audit(admin.id,'ti_regenerar_pdfs_ausentes',f'ok={ok} falhas={fail}')
    return _dev_redirect('/dev/integridade',request,f'PDFs regenerados: {ok}. Falhas: {fail}.','success' if not fail else 'error')

# ---- backup e restauração
@app.get('/dev/backup',response_class=HTMLResponse)
def ti_backup_page(request: Request):
    require_dev(request)
    with SessionLocal() as db:
        users=db.query(User).filter(User.role!=ROLE_DEV).order_by(User.full_name,User.username).all()
        for u in users: db.expunge(u)
    return templates.TemplateResponse(request,'ti_tools.html',_dev_ctx(request,'backup',users=users,backups=ti_tools.list_backups(STORAGE_DIR),auto=ti_tools.auto_backup_config(STORAGE_DIR),robot=ti_tools.robot_status()))

@app.post('/dev/backup/completo')
async def ti_backup_full(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    path=await asyncio.to_thread(ti_tools.backup_full,engine,STORAGE_DIR)
    audit(admin.id,'ti_backup_completo',path.name)
    return FileResponse(path,filename=path.name,media_type='application/zip')

@app.post('/dev/backup/usuario')
async def ti_backup_user(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: uid=int(form.get('user_id'))
    except (TypeError,ValueError): return _dev_redirect('/dev/backup',request,'Escolha um usuário.','error')
    path=await asyncio.to_thread(ti_tools.backup_user,engine,STORAGE_DIR,uid)
    audit(admin.id,'ti_backup_usuario',f'user={uid} | {path.name}')
    return FileResponse(path,filename=path.name,media_type='application/zip')

@app.post('/dev/backup/apagar-tudo')
async def ti_wipe_all(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    if clean(form.get('confirm'))!='APAGAR TUDO':
        return _dev_redirect('/dev/backup',request,'Confirmação incorreta. Digite exatamente APAGAR TUDO.','error')
    res=await asyncio.to_thread(ti_tools.wipe_all,engine,STORAGE_DIR,admin.id)
    audit(admin.id,'dev_apagar_tudo',json.dumps(res,ensure_ascii=False))
    return _dev_redirect('/dev/backup',request,f'Todos os dados foram apagados ({sum(v for v in res["tables"].values() if v and v>0)} registros, {res["files"]} arquivos). Backup de segurança: {res["safety"]}. Reinicie o servidor.')

@app.get('/dev/backup/baixar/{name}')
def ti_backup_download(request: Request, name: str):
    require_dev(request)
    path=(STORAGE_DIR/ti_tools.BACKUP_DIR/Path(name).name).resolve()
    if path.parent!=(STORAGE_DIR/ti_tools.BACKUP_DIR).resolve() or not path.is_file(): raise HTTPException(404)
    return FileResponse(path,filename=path.name,media_type='application/zip')

@app.post('/dev/backup/restaurar')
async def ti_backup_restore(request: Request):
    admin=require_dev(request); form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    upload=form.get('file')
    if not upload or not str(getattr(upload,'filename','') or '').lower().endswith('.zip'):
        return _dev_redirect('/dev/backup',request,'Envie o arquivo .zip do backup.','error')
    import tempfile, shutil
    tmp_fd,tmp_name=tempfile.mkstemp(suffix='.zip',dir=str(STORAGE_DIR))
    os.close(tmp_fd)
    tmp=Path(tmp_name)
    try:
        with open(tmp,'wb') as out: shutil.copyfileobj(upload.file,out)
        manifest=ti_tools.read_manifest(tmp)
        if manifest.get('kind')=='full':
            with SessionLocal() as db:
                row=db.get(User,admin.id)
                keep={c.name:(getattr(row,c.name).isoformat() if isinstance(getattr(row,c.name),datetime) else getattr(row,c.name)) for c in User.__table__.columns}
            res=await asyncio.to_thread(ti_tools.restore_full,engine,STORAGE_DIR,tmp,keep)
            request.session.clear()
            request.session['user_id']=res['keep_user_id']
            request.session['t']=res['session_cutoff']
            csrf_token(request)
            msg=f'Backup completo restaurado ({sum(res["tables"].values())} registros, {res["files"]} arquivos). Backup de segurança: {res["safety"]}. Reinicie o servidor para recarregar tudo.'
            audit(res['keep_user_id'],'ti_restaurar_completo',json.dumps(res,ensure_ascii=False))
        elif manifest.get('kind')=='user':
            target=None
            try: target=int(form.get('target_user_id'))
            except (TypeError,ValueError): pass
            with SessionLocal() as db:
                u=db.get(User,target) if target else db.query(User).filter(User.username==manifest.get('username')).first()
                if not u: return _dev_redirect('/dev/backup',request,'Escolha o usuário que receberá os documentos.','error')
                target=u.id
            res=await asyncio.to_thread(ti_tools.restore_user,engine,STORAGE_DIR,tmp,target)
            msg=f'Backup de usuário restaurado: {res["added"]} documento(s) novo(s), {res["skipped"]} já existiam. Backup de segurança: {res["safety"]}.'
            if res.get('missing_files'):
                msg+=f' O backup não contém {res["missing_files"]} anexo(s) referenciado(s); confira os documentos importados.'
            audit(admin.id,'ti_restaurar_usuario',json.dumps({**res,'target':target},ensure_ascii=False))
        else:
            return _dev_redirect('/dev/backup',request,'Arquivo de backup não reconhecido.','error')
    except Exception as exc:
        return _dev_redirect('/dev/backup',request,f'Não foi possível restaurar: {exc}','error')
    finally:
        try: tmp.unlink()
        except OSError: pass
    return _dev_redirect('/dev/backup',request,msg)

@app.get('/',response_class=HTMLResponse)
def dashboard(request: Request, q: str='', kind: str='', status: str='', today: str='', period: str='', date_from: str='', date_to: str='', creator: str='', company: str='', cluster: str='', site: str='', sort: str='recent'):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    refresh_pending_permit_closures()
    with SessionLocal() as db:
        query=db.query(Document).filter(Document.kind!='apr_template',Document.status!='Substituída')
        if q:
            s=f'%{q}%'; query=query.filter(or_(Document.code.ilike(s),Document.activity.ilike(s),Document.cluster.ilike(s),Document.site.ilike(s),Document.title.ilike(s)))
        if kind: query=query.filter(Document.kind==kind)
        if status: query=query.filter(Document.status==status)
        today_filter = str(today or '').strip().lower() in {'1','true','sim','yes'}
        period=clean(period).lower(); sort=clean(sort).lower() or 'recent'
        if period not in {'today','7days','month','custom'}: period=''
        if sort not in {'recent','oldest'}: sort='recent'
        today_date=local_today()
        if period=='today':
            date_from=date_to=today_date.strftime('%Y-%m-%d')
        elif period=='7days':
            date_from=(today_date-timedelta(days=6)).strftime('%Y-%m-%d'); date_to=today_date.strftime('%Y-%m-%d')
        elif period=='month':
            date_from=today_date.replace(day=1).strftime('%Y-%m-%d'); date_to=today_date.strftime('%Y-%m-%d')
        if today_filter:
            query=query.filter(Document.updated_at>=datetime.combine(local_today(),datetime.min.time()))
        date_from=clean(date_from); date_to=clean(date_to); creator=clean(creator); company=clean(company); cluster=clean(cluster); site=clean(site)
        if date_from:
            try: query=query.filter(Document.updated_at>=datetime.combine(datetime.strptime(date_from,'%Y-%m-%d').date(),datetime.min.time()))
            except ValueError: date_from=''
        if date_to:
            try: query=query.filter(Document.updated_at<datetime.combine(datetime.strptime(date_to,'%Y-%m-%d').date()+timedelta(days=1),datetime.min.time()))
            except ValueError: date_to=''
        if creator.isdigit(): query=query.filter(Document.created_by==int(creator))
        else: creator=''
        if cluster: query=query.filter(Document.cluster==cluster)
        if site: query=query.filter(Document.site==site)
        ordering=Document.updated_at.asc() if sort=='oldest' else desc(Document.updated_at)
        candidates=query.order_by(ordering).limit(1000).all()
        docs=[d for d in candidates if user_can_list_document(user,d)]
        if company:
            needle_company=company.casefold()
            docs=[d for d in docs if needle_company in document_company_search_text(d).casefold()]

        # Permite buscar também pelo código visual TIPO-USINA-ANO-NÚMERO.
        if q and not docs:
            fallback=db.query(Document).filter(Document.kind!='apr_template',Document.status!='Substituída')
            if kind: fallback=fallback.filter(Document.kind==kind)
            if status: fallback=fallback.filter(Document.status==status)
            if today_filter: fallback=fallback.filter(Document.updated_at>=datetime.combine(local_today(),datetime.min.time()))
            if date_from:
                fallback=fallback.filter(Document.updated_at>=datetime.combine(datetime.strptime(date_from,'%Y-%m-%d').date(),datetime.min.time()))
            if date_to:
                fallback=fallback.filter(Document.updated_at<datetime.combine(datetime.strptime(date_to,'%Y-%m-%d').date()+timedelta(days=1),datetime.min.time()))
            if creator: fallback=fallback.filter(Document.created_by==int(creator))
            if cluster: fallback=fallback.filter(Document.cluster==cluster)
            if site: fallback=fallback.filter(Document.site==site)
            q_norm=clean(q).upper()
            raw=fallback.order_by(ordering).limit(1500).all()
            raw=[d for d in raw if user_can_list_document(user,d)]
            if company:
                needle_company=company.casefold()
                raw=[d for d in raw if needle_company in document_company_search_text(d).casefold()]
            docs=[d for d in raw if q_norm in doc_reference_code(d).upper()]

        # Com um cluster escolhido no seletor, os totais passam pelo mesmo filtro das listas.
        super_all=is_super_admin(user) and not clean(VIEW_CLUSTER.get())
        if super_all:
            counts={
                'total':db.query(Document).filter(Document.kind!='apr_template').count(),
                'drafts':db.query(Document).filter(Document.kind!='apr_template',Document.status=='Rascunho').count(),
                'pending':db.query(Document).filter(Document.kind!='apr_template',Document.status.in_(['Aguardando aprovação','Pendente assinatura','Pendente de encerramento'])).count(),
                'final':db.query(Document).filter(Document.kind!='apr_template',Document.status=='Finalizada').count(),
                'today':db.query(Document).filter(Document.kind!='apr_template',Document.updated_at>=datetime.combine(local_today(),datetime.min.time())).count(),
            }
        else:
            _q_all=db.query(Document).filter(Document.kind!='apr_template').order_by(desc(Document.updated_at))
            all_candidates=_q_all.all() if is_super_admin(user) else _q_all.limit(2000).all()
            visible=[d for d in all_candidates if user_can_list_document(user,d)]
            today_start=datetime.combine(local_today(),datetime.min.time())
            counts={
                'total':len(visible),
                'drafts':sum(1 for d in visible if d.status=='Rascunho'),
                'pending':sum(1 for d in visible if d.status in {'Aguardando aprovação','Pendente assinatura','Pendente de encerramento'}),
                'final':sum(1 for d in visible if d.status=='Finalizada'),
                'today':sum(1 for d in visible if d.updated_at and d.updated_at>=today_start),
            }

        week_start=local_today()-timedelta(days=6)
        if super_all:
            stamps=[r[0] for r in db.query(Document.updated_at).filter(Document.kind!='apr_template',Document.updated_at>=datetime.combine(week_start,datetime.min.time())).all()]
        else:
            stamps=[d.updated_at for d in visible if d.updated_at]
        week_counts=Counter(s.date() for s in stamps if s and s.date()>=week_start)
        week_labels=['seg','ter','qua','qui','sex','sáb','dom']
        week_activity=[{'label':week_labels[(week_start+timedelta(days=i)).weekday()],'day':(week_start+timedelta(days=i)).strftime('%d/%m'),'count':week_counts.get(week_start+timedelta(days=i),0)} for i in range(7)]

        approval_assignments={}
        for d in docs:
            if d.kind=='apr':
                try: approval_assignments[d.id]=_approver_ids_for_data(json.loads(d.data_json or '{}'))
                except Exception: approval_assignments[d.id]=[]
        pending_approvals=[]
        pending_signatures=[]
        sig_notes=db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.kind.in_(['apr_participant_signature','apr_execution_member_signature'])).order_by(desc(Notification.created_at)).all()
        seen_sig=set()
        for n in sig_notes:
            if n.document_id in seen_sig: continue
            doc=db.get(Document,n.document_id)
            if not doc or doc.kind!='apr': continue
            data=doc_data(doc)
            if n.kind=='apr_execution_member_signature':
                member=_execution_member_for_notification(data,n,user.id)
                if doc.status=='Finalizada' and member and not clean(member.get('signature_image')):
                    pending_signatures.append({'doc':doc,'message':n.message,'unread':not n.read,'url':_execution_member_signature_url(doc.id,member['id'])})
                    seen_sig.add(n.document_id)
                continue
            if doc.status!='Pendente assinatura': continue
            my_pending=False
            for w in data.get('workers') or []:
                try: uid=int(w.get('participant_user_id') or 0)
                except Exception: uid=0
                if uid==user.id and not clean(w.get('signature_image')):
                    my_pending=True; break
            if not my_pending: continue
            pending_signatures.append({'doc':doc,'message':n.message,'unread':not n.read})
            seen_sig.add(n.document_id)

        if is_admin_user(user):
            notes=db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.kind=='apr_approval').order_by(desc(Notification.created_at)).all()
            seen=set()
            for n in notes:
                if n.document_id in seen: continue
                doc=db.get(Document,n.document_id)
                if not doc or doc.status!='Aguardando aprovação': continue
                if not user_can_access_document(user,doc): continue
                creator=db.get(User,doc.created_by)
                pending_approvals.append({'doc':doc,'message':n.message,'unread':not n.read,'creator':(creator.full_name or creator.username) if creator else ''})
                seen.add(n.document_id)
        if is_admin_user(user):
            creator_options=[{'id':u.id,'name':u.full_name or u.username} for u in db.query(User).filter(User.role!=ROLE_DEV).order_by(User.full_name,User.username).all()]
        else:
            creator_options=[{'id':user.id,'name':user.full_name or user.username}]
    history_clusters,history_cluster_sites=separate_clusters_for_user(user)
    return templates.TemplateResponse(request,'dashboard.html',context(request,documents=docs,counts=counts,week_activity=week_activity,kinds=DOCUMENT_TITLES,q=q,kind_filter=kind,status_filter=status,today_filter=today_filter,period_filter=period,sort_filter=sort,approval_assignments=approval_assignments,pending_approvals=pending_approvals,pending_signatures=pending_signatures,date_from_filter=date_from,date_to_filter=date_to,creator_filter=creator,company_filter=company,cluster_filter=cluster,site_filter=site,creator_options=creator_options,history_clusters=history_clusters,history_cluster_sites=history_cluster_sites))


@app.get('/indicadores/riscos',response_class=HTMLResponse)
def risk_indicators(request: Request, status: str='', cluster: str='', severity: str=''):
    """Dashboard dedicado à análise dos perigos e riscos selecionados nas APRs.

    O painel considera somente itens efetivamente selecionados nas etapas das APRs
    acessíveis ao usuário. O catálogo completo nunca entra nas contagens.
    """
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)

    # Operational overview uses the same visibility rules as the main panel.
    with SessionLocal() as overview_db:
        overview_candidates=overview_db.query(Document).filter(Document.kind!='apr_template').order_by(desc(Document.updated_at)).all()
        overview_docs=[d for d in overview_candidates if user_can_list_document(user,d)]
        overview_today=datetime.combine(local_today(),datetime.min.time())
        overview={
            'total':len(overview_docs),
            'drafts':sum(d.status=='Rascunho' for d in overview_docs),
            'pending':sum(d.status in {'Aguardando aprovação','Pendente assinatura','Pendente de encerramento'} for d in overview_docs),
            'final':sum(d.status=='Finalizada' for d in overview_docs),
            'today':sum(bool(d.updated_at and d.updated_at>=overview_today) for d in overview_docs),
        }

    from collections import Counter
    overview['by_kind']=sorted(Counter(DOCUMENT_TITLES.get(d.kind,d.kind) for d in overview_docs).items(),key=lambda x:-x[1])[:12]
    overview['by_cluster']=sorted(Counter((d.cluster or 'Não informado') for d in overview_docs).items(),key=lambda x:-x[1])[:12]
    overview['by_status']=sorted(Counter(d.status or 'Sem status' for d in overview_docs).items(),key=lambda x:-x[1])
    overview['max_kind']=max([v for _,v in overview['by_kind']] or [1])
    overview['max_cluster']=max([v for _,v in overview['by_cluster']] or [1])
    overview['max_status']=max([v for _,v in overview['by_status']] or [1])
    overview['final_pct']=round(100*overview['final']/overview['total']) if overview['total'] else 0

    status=clean(status)
    cluster=clean(cluster)
    severity=clean(severity).upper()
    if severity not in {'A','B','C'}:
        severity=''

    with SessionLocal() as db:
        query=db.query(Document).filter(Document.kind=='apr')
        if status:
            query=query.filter(Document.status==status)
        if cluster:
            query=query.filter(Document.cluster==cluster)
        candidates=query.order_by(desc(Document.updated_at)).all()
        docs=[d for d in candidates if user_can_list_document(user,d)]

        # Opções do filtro respeitam as permissões do usuário, mas não o filtro
        # atual, para permitir mudar de Cluster/Site diretamente no Dashboard.
        cluster_candidates=db.query(Document).filter(Document.kind=='apr').order_by(Document.cluster).all()
        if not is_super_admin(user):
            cluster_candidates=[d for d in cluster_candidates if user_can_list_document(user,d)]
        cluster_options=sorted({clean(d.cluster) for d in cluster_candidates if clean(d.cluster)}, key=lambda x: x.casefold())

        hazards=Counter()
        risks=Counter()
        severities=Counter()
        locations=Counter()
        pairs=Counter()
        rows=[]
        aprs_with_selection=0
        total_selections=0

        for d in docs:
            data=doc_data(d)
            seen=set()
            doc_has_selection=False
            for idx,step in enumerate(data.get('steps') or []):
                stage=clean(step.get('stage')) or f'Etapa {idx+1}'
                hazard_values=_normalize_multi_step_values(step.get('hazards'),step.get('hazard'))
                risk_values=_normalize_multi_step_values(step.get('risks'),step.get('risk'))
                hazard='; '.join(hazard_values)
                risk='; '.join(risk_values)
                step_severity=normalize_apr_severity(step.get('severity'))
                if severity and step_severity != severity:
                    continue
                if not hazard_values and not risk_values:
                    continue

                # Evita duplicação acidental da mesma seleção dentro da mesma APR.
                dedup_key=(stage,tuple(hazard_values),tuple(risk_values),step_severity)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                doc_has_selection=True
                total_selections += max(1,len(hazard_values),len(risk_values))

                for item in hazard_values: hazards[item] += 1
                for item in risk_values: risks[item] += 1
                for h in hazard_values:
                    for r in risk_values:
                        pairs[(h,r)] += 1
                if step_severity:
                    severities[step_severity] += 1

                location=clean(d.cluster)
                if clean(d.site):
                    location=f'{location} · {clean(d.site)}' if location else clean(d.site)
                if location:
                    locations[location] += 1

                rows.append({
                    'doc':d,
                    'code':doc_reference_code(d),
                    'stage':stage,
                    'hazard':hazard,
                    'risk':risk,
                    'severity':step_severity,
                })

            if doc_has_selection:
                aprs_with_selection += 1

        def chart(counter: Counter, total=None):
            maximum=max(counter.values(), default=0)
            total_value=total if total is not None else sum(counter.values())
            return [
                {
                    'label':label,
                    'count':count,
                    'pct':round((count/maximum)*100,2) if maximum else 0,
                    'share':round((count/total_value)*100,1) if total_value else 0,
                }
                for label,count in sorted(counter.items(), key=lambda item:(-item[1], str(item[0]).casefold()))
            ]

        hazard_chart=chart(hazards)
        risk_chart=chart(risks)
        location_chart=chart(locations)
        pair_chart=[]
        pair_max=max(pairs.values(), default=0)
        for (hazard,risk),count in sorted(pairs.items(), key=lambda item:(-item[1], item[0][0].casefold(), item[0][1].casefold())):
            pair_chart.append({
                'hazard':hazard,
                'risk':risk,
                'count':count,
                'pct':round((count/pair_max)*100,2) if pair_max else 0,
            })

        severity_order=['A','B','C']
        severity_max=max([severities.get(k,0) for k in severity_order] or [0])
        severity_total=sum(severities.values())
        severity_chart=[{
            'label':key,
            'count':severities.get(key,0),
            'pct':round((severities.get(key,0)/severity_max)*100,2) if severity_max else 0,
            'share':round((severities.get(key,0)/severity_total)*100,1) if severity_total else 0,
        } for key in severity_order]
        for key,count in sorted(severities.items()):
            if key not in severity_order:
                severity_chart.append({
                    'label':key,
                    'count':count,
                    'pct':round((count/severity_max)*100,2) if severity_max else 0,
                    'share':round((count/severity_total)*100,1) if severity_total else 0,
                })

        top_risk=risk_chart[0] if risk_chart else None
        top_hazard=hazard_chart[0] if hazard_chart else None
        top_pair=pair_chart[0] if pair_chart else None

    return templates.TemplateResponse(
        request,
        'risk_indicators.html',
        context(
            request,
            overview=overview,
            status_filter=status,
            cluster_filter=cluster,
            severity_filter=severity,
            cluster_options=cluster_options,
            apr_count=len(docs),
            aprs_with_selection=aprs_with_selection,
            total_selections=total_selections,
            unique_hazards=len(hazards),
            unique_risks=len(risks),
            hazard_chart=hazard_chart,
            risk_chart=risk_chart,
            location_chart=location_chart,
            pair_chart=pair_chart,
            severity_chart=severity_chart,
            top_risk=top_risk,
            top_hazard=top_hazard,
            top_pair=top_pair,
            selection_rows=rows,
        ),
    )


def _notification_target(notification: Notification, doc: Document|None, user: User) -> str:
    if not doc: return '/'
    if notification.kind=='apr_execution_member_signature' and doc.kind=='apr':
        member=_execution_member_for_notification(doc_data(doc),notification,user.id)
        if member: return _execution_member_signature_url(doc.id,member['id'])
        return '/notifications'
    if notification.kind=='apr_participant_signature' and doc.kind=='apr': return f'/apr/{doc.id}/assinar'
    if notification.kind=='apr_approval' and doc.kind=='apr': return f'/apr/{doc.id}/aprovar'
    if notification.kind=='apr_creator_signatures_complete' and doc.kind=='apr': return f'/apr/{doc.id}/edit'
    return document_open_url(doc,user)

@app.get('/api/notifications/unread')
def notifications_unread_api(request: Request, limit: int=10):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    limit=max(1,min(int(limit or 10),50))
    items=[]; count=0
    with SessionLocal() as db:
        notes=(db.query(Notification)
            .filter(Notification.recipient_user_id==user.id,Notification.read==False)
            .order_by(desc(Notification.created_at)).limit(200).all())
        for n in notes:
            doc=db.get(Document,n.document_id)
            if doc and not user_can_access_document(user,doc):
                continue
            count+=1
            if len(items)<limit:
                items.append({
                    'id':n.id,'title':_notification_title(n.kind),'message':n.message,
                    'created_at':n.created_at.isoformat() if n.created_at else '',
                    'url':f'/notifications/{n.id}/open','kind':n.kind,
                    'tag':f'safety-plus-{n.kind}-{n.document_id}',
                })
    return JSONResponse({'count':count,'items':items},headers={'Cache-Control':'no-store'})


@app.get('/api/notifications/push/public-key')
def notifications_push_public_key(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    try:
        public_key=vapid_public_key(STORAGE_DIR)
    except Exception as exc:
        raise HTTPException(503,f'Não foi possível preparar as notificações push: {exc}')
    return JSONResponse({'public_key':public_key,'backend_available':push_backend_available()},headers={'Cache-Control':'no-store'})


@app.get('/api/notifications/push/status')
def notifications_push_status(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    with SessionLocal() as db:
        count=db.query(PushSubscription).filter(PushSubscription.user_id==user.id,PushSubscription.active==True).count()
    return JSONResponse({'ok':True,'backend_available':push_backend_available(),'devices':count},headers={'Cache-Control':'no-store'})


@app.post('/api/notifications/push/subscribe')
async def notifications_push_subscribe(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    try: body=await request.json()
    except Exception: raise HTTPException(400,'Dados de inscrição inválidos.')
    verify_csrf(request,body.get('csrf_token'))
    raw=body.get('subscription') or {}
    endpoint=clean(raw.get('endpoint'))
    keys=raw.get('keys') or {}
    p256dh=clean(keys.get('p256dh')); auth=clean(keys.get('auth'))
    if not endpoint or not endpoint.startswith('https://') or not p256dh or not auth:
        raise HTTPException(422,'Inscrição push incompleta.')
    with SessionLocal() as db:
        sub=db.query(PushSubscription).filter(PushSubscription.endpoint==endpoint).first()
        if not sub:
            sub=PushSubscription(user_id=user.id,endpoint=endpoint,p256dh=p256dh,auth=auth,user_agent=clean(request.headers.get('user-agent')),active=True,created_at=now(),updated_at=now())
            db.add(sub)
        else:
            sub.user_id=user.id; sub.p256dh=p256dh; sub.auth=auth
            sub.user_agent=clean(request.headers.get('user-agent')); sub.active=True
            sub.updated_at=now(); sub.last_error=''
        db.commit()
    audit(user.id,'ativar_notificacao_push','Dispositivo registrado para notificações do Safety Plus.')
    return {'ok':True,'backend_available':push_backend_available()}


@app.post('/api/notifications/push/test')
async def notifications_push_test(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    try: body=await request.json()
    except Exception: body={}
    verify_csrf(request,body.get('csrf_token'))
    if not push_backend_available():
        raise HTTPException(503,'O módulo de envio push não está disponível no servidor.')
    sent=0; failed=0
    with SessionLocal() as db:
        subscriptions=db.query(PushSubscription).filter(PushSubscription.user_id==user.id,PushSubscription.active==True).all()
        for sub in subscriptions:
            ok,gone,detail=send_web_push(sub,{
                'title':'Safety Plus',
                'body':'Notificações no celular ativadas com sucesso.',
                'url':'/notifications',
                'tag':f'safety-plus-test-{user.id}',
                'icon':'/static/icons/safety-plus-icon-192-v361831.png',
                'badge':'/static/icons/safety-plus-favicon-64-v361831.png',
            },STORAGE_DIR)
            if ok:
                sent+=1; sub.last_success_at=now(); sub.last_error=''; sub.updated_at=now()
            else:
                failed+=1; sub.last_error=detail; sub.updated_at=now()
                if gone: sub.active=False
        db.commit()
    if not sent:
        raise HTTPException(503,'Nenhum aparelho recebeu o teste. Confirme a permissão de notificações e tente ativar novamente.')
    return {'ok':True,'sent':sent,'failed':failed}


@app.post('/api/notifications/push/unsubscribe')
async def notifications_push_unsubscribe(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    try: body=await request.json()
    except Exception: raise HTTPException(400,'Dados inválidos.')
    verify_csrf(request,body.get('csrf_token'))
    endpoint=clean(body.get('endpoint'))
    with SessionLocal() as db:
        q=db.query(PushSubscription).filter(PushSubscription.user_id==user.id)
        if endpoint: q=q.filter(PushSubscription.endpoint==endpoint)
        rows=q.all()
        for sub in rows:
            sub.active=False; sub.updated_at=now()
        if rows: db.commit()
    audit(user.id,'desativar_notificacao_push',f'dispositivos={len(rows)}')
    return {'ok':True}



_notification_housekeeping_task=None


async def _notification_housekeeping_loop():
    # Pequeno atraso evita disputar a inicialização do banco/servidor.
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.to_thread(refresh_pending_permit_closures)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(60*60)


async def _auto_backup_loop():
    while True:
        try:
            await asyncio.to_thread(ti_tools.run_auto_backup_if_due,engine,STORAGE_DIR)
        except asyncio.CancelledError: raise
        except Exception as exc:
            print('[backup automático] falhou:',exc)
        await asyncio.sleep(15*60)

_auto_backup_task=None

@app.on_event('startup')
async def _migrate_role_ti_to_dev():
    """Renomeia o perfil legado 'T.I.' para 'DEV' (idempotente)."""
    try:
        with SessionLocal() as db:
            n=db.query(User).filter(User.role=='T.I.').update({User.role:ROLE_DEV},synchronize_session=False)
            db.commit()
            if n: print(f'[migração] {n} usuário(s) T.I. -> DEV')
    except Exception as exc:
        print('[migração] perfil T.I. -> DEV falhou:',exc)

@app.on_event('startup')
async def _start_auto_backup():
    global _auto_backup_task
    if _auto_backup_task is None or _auto_backup_task.done():
        _auto_backup_task=asyncio.create_task(_auto_backup_loop())

@app.on_event('startup')
async def _start_notification_housekeeping():
    global _notification_housekeeping_task
    if _notification_housekeeping_task is None or _notification_housekeeping_task.done():
        _notification_housekeeping_task=asyncio.create_task(_notification_housekeeping_loop())


@app.on_event('shutdown')
async def _stop_notification_housekeeping():
    global _notification_housekeeping_task
    if _notification_housekeeping_task and not _notification_housekeeping_task.done():
        _notification_housekeeping_task.cancel()
        try: await _notification_housekeeping_task
        except (asyncio.CancelledError,Exception): pass
    _notification_housekeeping_task=None


@app.get('/notifications',response_class=HTMLResponse)
def notifications_page(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    items=[]
    with SessionLocal() as db:
        notes=db.query(Notification).filter(Notification.recipient_user_id==user.id).order_by(desc(Notification.created_at)).limit(300).all()
        for n in notes:
            doc=db.get(Document,n.document_id)
            if doc and not user_can_access_document(user,doc):
                continue
            items.append({
                'id':n.id,'message':n.message,'read':bool(n.read),'created_at':n.created_at,
                'doc_code':doc_reference_code(doc) if doc else 'Documento removido',
                'doc_title':doc.title if doc else '',
                'url':_notification_target(n,doc,user),
                'kind':n.kind,
            })
    return templates.TemplateResponse(request,'notifications.html',context(request,items=items))

@app.get('/notifications/{notification_id}/open')
def notification_open(request: Request,notification_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    with SessionLocal() as db:
        n=db.get(Notification,notification_id)
        if not n or n.recipient_user_id!=user.id: raise HTTPException(404,'Notificação não encontrada.')
        doc=db.get(Document,n.document_id)
        if doc and not user_can_access_document(user,doc):
            raise HTTPException(403,'Esta notificação não pertence mais ao seu escopo de acesso.')
        target=_notification_target(n,doc,user)
        if not n.read:
            n.read=True; n.read_at=now(); db.commit()
    return RedirectResponse(target,303)

@app.post('/notifications/{notification_id}/read')
async def notification_read(request: Request,notification_id:int):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        n=db.get(Notification,notification_id)
        if not n or n.recipient_user_id!=user.id: raise HTTPException(404,'Notificação não encontrada.')
        if not n.read:
            n.read=True; n.read_at=now(); db.commit()
    return {'ok':True}

@app.post('/notifications/read-all')
async def notifications_read_all(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        notes=db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.read==False).all()
        for n in notes:
            n.read=True; n.read_at=now()
        db.commit()
    flash(request,'Notificações marcadas como lidas.','success')
    return RedirectResponse('/notifications',303)

def _custom_cards(placement: str) -> list[dict]:
    return [{'title':c.get('title',''),'url':f'/rac/{k}/new','items':c.get('item_count',0)} for k,c in RAC_MODULES.items() if c.get('custom') and c.get('placement')==placement]

@app.get('/ferramentas-sst',response_class=HTMLResponse)
def ferramentas_sst(request: Request):
    if not current_user(request): return RedirectResponse('/login',303)
    return templates.TemplateResponse(request,'ferramentas_sst.html',context(request,custom_cards=_custom_cards('tools')))


# ---------------- Momento de Segurança (Ferramentas SST) ----------------
def _sm_clean_sig(value, existing=''):
    value=clean(value)
    if value.startswith('data:image/'): return save_signature(value,existing,'momento')
    if value.startswith('signatures/') and '..' not in value: return value
    return existing or ''

def _sm_parse(form, old: dict) -> dict:
    d={'code':old.get('code') or next_code('safety_moment'),'status':old.get('status','Rascunho')}
    rawdate=clean(form.get('moment_date'))
    d['moment_date']=br_date(rawdate) if rawdate else ''
    d['moment_time']=clean(form.get('moment_time'))
    d['cluster']=clean_single_line(form.get('cluster')); d['site']=clean_single_line(form.get('site'))
    d['theme']=clean_single_line(form.get('theme')); d['conductor']=clean_single_line(form.get('conductor'))
    d['key_points']=clean(form.get('key_points'))[:4000]
    d['activity']=d['theme']
    d['conductor_signature']=_sm_clean_sig(form.get('conductor_signature'),old.get('conductor_signature',''))
    names=form.getlist('p_name'); comps=form.getlist('p_company'); roles=form.getlist('p_role'); sigs=form.getlist('p_sig')
    people=[]
    for i,name in enumerate(names):
        name=clean_single_line(name)
        if not name: continue
        people.append({'name':name,'company':clean_single_line(comps[i] if i<len(comps) else ''),'role':clean_single_line(roles[i] if i<len(roles) else ''),
                       'signature_image':_sm_clean_sig(sigs[i] if i<len(sigs) else '')})
        if len(people)>=60: break
    d['participants']=people
    return d

def _sm_form_page(request,user,doc=None):
    data=doc_data(doc) if doc else {}
    if not doc:
        data={'code':next_code('safety_moment'),'moment_date':local_today().strftime('%d/%m/%Y'),'moment_time':now().strftime('%H:%M'),'conductor':user.full_name or user.username,'participants':[]}
    if not doc: prefill_location(user,data)
    clusters,sites=separate_clusters_for_user(user)
    raw_date=''
    try: raw_date=datetime.strptime(data.get('moment_date',''),'%d/%m/%Y').strftime('%Y-%m-%d')
    except Exception: raw_date=local_today().strftime('%Y-%m-%d')
    return templates.TemplateResponse(request,'safety_moment_form.html',context(request,doc=doc,d=data,raw_date=raw_date,sm_clusters=clusters,sm_sites=sites,sm_code=data_reference_code('safety_moment',data,data.get('cluster',''),data.get('site','')) or data.get('code','')))


# ---- Biblioteca de Momentos de Segurança (PDFs oficiais) ----
SM_LIBRARY_DIR=prepare_library(STORAGE_DIR,BASE_DIR/'info_docs'/'momentos')

def _sm_library() -> list[dict]:
    try: return json.loads((SM_LIBRARY_DIR/'manifest.json').read_text(encoding='utf-8'))
    except Exception: return []

@app.get('/momento-seguranca/biblioteca',response_class=HTMLResponse)
def safety_moment_library(request: Request):
    if not current_user(request): return RedirectResponse('/login',303)
    return templates.TemplateResponse(request,'safety_moment_library.html',context(request,sm_items=_sm_library(),sm_can_manage=is_admin_user(current_user(request)),sm_open=request.query_params.get('novo')=='1',sm_msg=request.query_params.get('msg',''),sm_err=request.query_params.get('err','')))

def _sm_write_manifest(items: list[dict]) -> None:
    items.sort(key=lambda i:(-int(i.get('num') or 0),str(i.get('lang'))))
    tmp=SM_LIBRARY_DIR/'manifest.json.tmp'
    tmp.write_text(json.dumps(items,ensure_ascii=False,indent=1),encoding='utf-8')
    tmp.replace(SM_LIBRARY_DIR/'manifest.json')

@app.post('/momento-seguranca/biblioteca/upload')
async def safety_moment_library_upload(request: Request):
    user=require_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    def back(k,m): return RedirectResponse('/momento-seguranca/biblioteca?'+urlencode({k:m}),303)
    upload=form.get('file')
    if not upload or not hasattr(upload,'read'): return back('err','Selecione um arquivo PDF.')
    raw=await upload.read()
    if len(raw)>25*1024*1024: return back('err','O PDF deve ter no máximo 25 MB.')
    if not raw.startswith(b'%PDF'): return back('err','O arquivo enviado não é um PDF válido.')
    try:
        with fitz.open(stream=raw,filetype='pdf') as d: pages=d.page_count
        if pages<1: raise ValueError
    except Exception: return back('err','Não foi possível ler o PDF enviado.')
    title=clean(form.get('title'))[:140]
    if not title: return back('err','Informe o tema do Momento de Segurança.')
    lang='EN' if clean(form.get('lang')).upper()=='EN' else 'PT'
    period=clean(form.get('period'))[:30]
    items=_sm_library()
    try: num=int(clean(form.get('num')))
    except ValueError: num=max([int(i.get('num') or 0) for i in items] or [0])+1
    slug=re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode().lower()).strip('-')[:60] or 'momento'
    mid=f'{num:03d}-{lang.lower()}-{slug}'
    if any(i.get('id')==mid for i in items): return back('err','Já existe um Momento com esse número, idioma e tema.')
    fname=mid+'.pdf'
    SM_LIBRARY_DIR.mkdir(parents=True,exist_ok=True)
    (SM_LIBRARY_DIR/fname).write_bytes(raw)
    items.append({'num':num,'title':title,'lang':lang,'period':period,'file':fname,'pages':pages,'id':mid})
    _sm_write_manifest(items)
    audit(user.id,'momento_biblioteca_adicionar',mid)
    return back('msg',f'Momento #{num} adicionado à biblioteca.')

@app.post('/momento-seguranca/biblioteca/{mid}/delete')
async def safety_moment_library_delete(request: Request, mid: str):
    user=require_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    items=_sm_library()
    item=next((i for i in items if i.get('id')==mid),None)
    if not item: raise HTTPException(404,'Momento de Segurança não encontrado.')
    items=[i for i in items if i.get('id')!=mid]
    _sm_write_manifest(items)
    try: (SM_LIBRARY_DIR/item['file']).unlink()
    except OSError: pass
    audit(user.id,'momento_biblioteca_remover',mid)
    return RedirectResponse('/momento-seguranca/biblioteca?'+urlencode({'msg':'Momento removido da biblioteca.'}),303)

@app.get('/momento-seguranca/lista-presenca.png')
def safety_moment_attendance_qr(request: Request):
    if not current_user(request): return RedirectResponse('/login',303)
    path=SM_LIBRARY_DIR/'lista-presenca-qr.png'
    if not path.exists(): raise HTTPException(404,'QR Code não encontrado.')
    return FileResponse(path,media_type='image/png',headers={'Cache-Control':'private, max-age=86400'})

@app.get('/momento-seguranca/biblioteca/{mid}/thumb')
def safety_moment_library_thumb(request: Request, mid: str):
    if not current_user(request): return RedirectResponse('/login',303)
    item=next((i for i in _sm_library() if i.get('id')==mid),None)
    if not item: raise HTTPException(404,'Momento de Segurança não encontrado.')
    path=SM_LIBRARY_DIR/item['file']
    if not path.exists(): raise HTTPException(404,'Arquivo não encontrado.')
    cache_dir=STORAGE_DIR/'sm_thumbs'; cache_dir.mkdir(parents=True,exist_ok=True)
    thumb=cache_dir/f'{mid}-v6-{int(path.stat().st_mtime)}.jpg'
    if not thumb.exists():
        try:
            with fitz.open(path) as d:
                cands={}
                for pn in range(min(10,d.page_count)):
                    for x in d.load_page(pn).get_images(full=True):
                        if x[2]>=250 and x[3]>=150 and 0.9<=x[2]/x[3]<=2.4 and x[0] not in cands: cands[x[0]]=(pn,x[2]*x[3])
                pix=None
                # prioriza imagens das primeiras páginas (tema do DSS); dentro da página, a maior
                for xref in sorted(cands,key=lambda k:(cands[k][0]>=4,-cands[k][1]))[:10]:
                    try:
                        q=fitz.Pixmap(d,xref)
                        if q.colorspace is None or q.colorspace.n!=3: q=fitz.Pixmap(fitz.csRGB,q)
                        if q.alpha: q=fitz.Pixmap(q,0)
                        if q.width>1000: q.shrink(max(1,q.width//800))
                        sm=bytes(q.samples); npx=len(sm)//3; step=max(1,npx//3000)
                        px=[(sm[i*3],sm[i*3+1],sm[i*3+2]) for i in range(0,npx,step)]
                        ref=px[0]
                        flat=sum(1 for c in px if max(abs(c[0]-ref[0]),abs(c[1]-ref[1]),abs(c[2]-ref[2]))<14)/len(px)
                        bw=sum(1 for c in px if max(c)<70 or min(c)>190)/len(px)
                        # descarta QR Code (preto e branco), fundo liso/degradê e imagens dominadas por uma cor
                        rng=max(max(c[k] for c in px)-min(c[k] for c in px) for k in range(3))
                        if bw>0.8 or flat>0.55 or rng<120: continue
                        edge=sum(abs(a_-b_) for c1,c2 in zip(px,px[1:]) for a_,b_ in zip(c1,c2))/(3*max(len(px)-1,1))
                        if edge<2.0: continue
                        pix=q; break
                    except Exception: continue
                if pix is None:
                    pix=d.load_page(0).get_pixmap(matrix=fitz.Matrix(0.6,0.6),alpha=False)
                thumb.write_bytes(pix.tobytes('jpg',jpg_quality=82))
        except Exception: raise HTTPException(500,'Não foi possível gerar a miniatura.')
    return FileResponse(thumb,media_type='image/jpeg',headers={'Cache-Control':'private, max-age=86400'})

@app.get('/momento-seguranca/biblioteca/{mid}')
def safety_moment_library_open(request: Request, mid: str):
    if not current_user(request): return RedirectResponse('/login',303)
    item=next((i for i in _sm_library() if i.get('id')==mid),None)
    if not item: raise HTTPException(404,'Momento de Segurança não encontrado.')
    path=SM_LIBRARY_DIR/item['file']
    if not path.exists(): raise HTTPException(404,'Arquivo não encontrado.')
    preview=pdf_preview_response(request,path)
    if preview is not None: return preview
    if request.query_params.get('raw')=='1':
        return FileResponse(path,media_type='application/pdf',filename=item['file'],content_disposition_type='inline',headers={'Cache-Control':'private, max-age=3600'})
    title=f"DSS #{item['num']} — {item['title']}"
    return templates.TemplateResponse(request,'pdf_viewer.html',context(request,doc=None,pdf_title=title,pdf_error='',raw_pdf_url=f'/momento-seguranca/biblioteca/{mid}?raw=1',daily_signature_url='',close_url='/momento-seguranca/biblioteca'))

@app.get('/momento-seguranca')
def safety_moment_home(request: Request):
    if not current_user(request): return RedirectResponse('/login',303)
    return RedirectResponse('/momento-seguranca/biblioteca',303)

@app.get('/momento-seguranca/new',response_class=HTMLResponse)
def safety_moment_new(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    return RedirectResponse('/momento-seguranca/biblioteca?novo=1',303)

@app.get('/momento-seguranca/{doc_id}/edit',response_class=HTMLResponse)
def safety_moment_edit(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if not doc or doc.kind!='safety_moment': raise HTTPException(404)
    if not user_can_access_document(user,doc): raise HTTPException(403,'Você não tem permissão para acessar este registro.')
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    return _sm_form_page(request,user,doc)

async def _sm_save(request: Request, doc_id: int|None):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    doc=None; old={}
    if doc_id:
        doc=get_document(doc_id)
        if not doc or doc.kind!='safety_moment': raise HTTPException(404)
        if not user_can_access_document(user,doc): raise HTTPException(403,'Você não tem permissão para acessar este registro.')
        if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
        old=doc_data(doc)
    d=_sm_parse(form,old)
    if d['cluster'] and d['cluster'] not in separate_clusters_for_user(user)[0]:
        d['cluster']=''; d['site']=''
    action=clean(form.get('action')) or 'draft'
    if action=='finalize':
        miss=[]
        if not d['moment_date']: miss.append('data')
        if not d['cluster']: miss.append('cluster')
        if not d['theme']: miss.append('tema')
        if not d['conductor']: miss.append('responsável')
        if not d['participants']: miss.append('pelo menos um participante')
        elif any(not p['signature_image'] for p in d['participants']): miss.append('rubrica de todos os participantes')
        if not d['conductor_signature']: miss.append('rubrica do responsável')
        if miss:
            saved=save_doc(doc,'safety_moment',d,user,'Rascunho')
            flash(request,'Para finalizar, informe: '+', '.join(miss)+'. O que já foi preenchido foi mantido.','error')
            return RedirectResponse(f'/momento-seguranca/{saved.id}/edit',303)
        saved=save_doc(doc,'safety_moment',d,user,'Finalizada')
        try: saved=finalize_pdf(saved,d)
        except Exception as e:
            _rollback_document_after_pdf_failure(saved.id,'Rascunho')
            flash(request,f'Dados salvos, mas o PDF não foi gerado: {e}. O registro permaneceu em Rascunho.','error')
            return RedirectResponse(f'/momento-seguranca/{saved.id}/edit',303)
        audit(user.id,'finalizar_momento_seguranca',saved.code)
        return RedirectResponse(f'/document/{saved.id}/pdf',303)
    saved=save_doc(doc,'safety_moment',d,user,'Rascunho')
    flash(request,'Rascunho salvo.','success')
    return RedirectResponse(f'/momento-seguranca/{saved.id}/edit',303)

@app.post('/momento-seguranca/save')
async def safety_moment_create_save(request: Request): return await _sm_save(request,None)

@app.post('/momento-seguranca/{doc_id}/save')
async def safety_moment_update_save(request: Request, doc_id: int): return await _sm_save(request,doc_id)

@app.get('/recursos-externos',response_class=HTMLResponse)
def recursos_externos(request: Request, unidade: str=''):
    if not current_user(request): return RedirectResponse('/login',303)
    from .external_resources import load_units
    units=load_units(STORAGE_DIR)
    if not units: return templates.TemplateResponse(request,'recursos_externos.html',context(request,units=[],cur=None))
    cur=next((u for u in units if u['key']==unidade),units[0])
    return templates.TemplateResponse(request,'recursos_externos.html',context(request,units=units,cur=cur))

@app.get('/sobre-serena',response_class=HTMLResponse)
def sobre_serena(request: Request):
    if not current_user(request): return RedirectResponse('/login',303)
    return templates.TemplateResponse(request,'sobre_serena.html',context(request,custom_cards=_custom_cards('policy')))

@app.get('/sobre-serena/documentos/{slug}')
def sobre_serena_documento(request: Request, slug: str):
    if not current_user(request): return RedirectResponse('/login',303)
    item=ABOUT_SERENA_DOCS.get(slug)
    if not item: raise HTTPException(404,'Documento institucional não encontrado.')
    path=INFO_DOCS_DIR/item['filename']
    if not path.exists(): raise HTTPException(404,'Arquivo institucional não encontrado.')
    preview=pdf_preview_response(request,path)
    if preview is not None: return preview
    if request.query_params.get('raw')=='1':
        return FileResponse(path,media_type='application/pdf',filename=item['download_name'],content_disposition_type='inline',headers={'Cache-Control':'private, max-age=3600'})
    return templates.TemplateResponse(request,'pdf_viewer.html',context(
        request,doc=None,pdf_title=item['title'],pdf_error='',raw_pdf_url=f'/sobre-serena/documentos/{slug}?raw=1',daily_signature_url='',
    ))

@app.get('/sobre-serena/politica-sst')
def sobre_serena_politica_alias(request: Request):
    return sobre_serena_documento(request,'politica-sst')

@app.get('/sobre-serena/regras-pela-vida')
def sobre_serena_regras_alias(request: Request):
    return sobre_serena_documento(request,'regras-pela-vida')

@app.get('/new/{kind}')
def new_document(request: Request, kind: str):
    if not current_user(request): return RedirectResponse('/login',303)
    if kind not in DOCUMENT_TITLES: raise HTTPException(404)
    if kind=='apr': return RedirectResponse('/apr/new',303)
    if kind=='vehicle': return RedirectResponse('/vehicle/new',303)
    if kind in INSPECTION_MODULES: return RedirectResponse(f'/inspection/{kind}/new',303)
    if kind not in MODULES: raise HTTPException(404)
    return RedirectResponse(f'/permit/{kind}/new',303)

@app.get('/document/{doc_id}')
def open_document(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    refresh_pending_permit_closures(doc_id)
    try:
        doc=get_document(doc_id)
    except HTTPException:
        flash(request,'Este documento não está mais disponível neste endereço. Atualize o painel para carregar a versão atual.','error')
        return RedirectResponse('/',303)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        flash(request,'Você não tem permissão para abrir este documento.','error')
        return RedirectResponse('/',303)
    return RedirectResponse(document_open_url(doc,user),303)

@app.get('/document/{doc_id}/pdf')
def view_pdf(request: Request, doc_id: int):
    user=current_user(request)
    if not user:
        return RedirectResponse('/login?next='+_safe_next_path(str(request.url.path)),303)
    try:
        doc=get_document(doc_id)
    except HTTPException:
        flash(request,'Este documento não está mais disponível neste endereço. Atualize o painel para carregar a versão atual.','error')
        return RedirectResponse('/',303)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        flash(request,'Você não tem permissão para abrir este documento.','error')
        return RedirectResponse('/',303)
    if doc.status not in ('Finalizada','Substituída'):
        return RedirectResponse(f'/document/{doc.id}',303)
    raw=request.query_params.get('raw')=='1'
    is_preview=request.query_params.get('preview_meta')=='1' or bool(request.query_params.get('preview_page'))
    try:
        p=ensure_document_pdf(doc)
    except Exception as e:
        # Navegação comum recebe uma tela amigável com Voltar. Fetch/API continua
        # recebendo erro real para não mascarar falhas de compartilhamento/sincronização.
        if not raw and not is_preview:
            return templates.TemplateResponse(request,'pdf_viewer.html',context(
                request,doc=doc,pdf_error=f'Não foi possível reconstruir o PDF deste documento: {e}',raw_pdf_url='',
                daily_signature_url=(f'/apr/{doc.id}/assinatura-diaria' if doc.kind=='apr' else ''),
            ),status_code=500)
        raise HTTPException(500,f'Não foi possível reconstruir o PDF deste documento: {e}')
    if not p or not p.exists():
        raise HTTPException(404,'O documento existe, mas o PDF não pôde ser localizado nem reconstruído.')

    preview=pdf_preview_response(request,p)
    if preview is not None: return preview

    # O PDF bruto é explícito. Cabeçalhos de PWA/fetch variam entre navegadores;
    # eles não devem trocar o visualizador pelo plugin PDF nativo após finalizar.
    if raw:
        return FileResponse(p,media_type='application/pdf',filename=f'{doc_reference_code(doc)}.pdf',content_disposition_type='inline',headers={'Cache-Control':'private, max-age=0, must-revalidate'})

    return templates.TemplateResponse(request,'pdf_viewer.html',context(
        request,doc=doc,pdf_error='',raw_pdf_url=f'/document/{doc.id}/pdf?raw=1',
        daily_signature_url=(f'/apr/{doc.id}/assinatura-diaria' if doc.kind=='apr' else ''),
    ))

# Compatibilidade com links de versões antigas/caches anteriores.
@app.get('/documents/{doc_id}')
def open_document_legacy_plural(request: Request, doc_id: int):
    return open_document(request,doc_id)

@app.get('/documents/{doc_id}/pdf')
def view_pdf_legacy_plural(request: Request, doc_id: int):
    return view_pdf(request,doc_id)

@app.get('/arquivo/{doc_id}')
def open_document_legacy_arquivo(request: Request, doc_id: int):
    return open_document(request,doc_id)

@app.get('/arquivo/{doc_id}/pdf')
def view_pdf_legacy_arquivo(request: Request, doc_id: int):
    return view_pdf(request,doc_id)

# -------------------- PTs --------------------
def split_separate_cluster_site(cluster: str, site: str='') -> tuple[str,str]:
    """Converte o formato antigo 'CLUSTER - SITE' para os campos separados."""
    cluster=clean(cluster); site=clean(site)
    if cluster in SEPARATE_CLUSTER_SITES:
        return cluster,site
    for group,sites in SEPARATE_CLUSTER_SITES.items():
        prefix=group+' - '
        if cluster.startswith(prefix):
            inferred=cluster[len(prefix):].strip()
            if not site and inferred in sites:
                site=inferred
            return group,site
    return cluster,site


def sanitize_separate_cluster_site(cluster: str, site: str) -> tuple[str,str]:
    """Mantém somente combinações válidas sem quebrar registros históricos."""
    cluster,site=split_separate_cluster_site(cluster,site)
    if cluster in SEPARATE_CLUSTER_SITES:
        if site not in SEPARATE_CLUSTER_SITES[cluster]:
            site=''
    elif not cluster:
        site=''
    return cluster,site


PERMIT_ACTIVE_STATUSES={'Em andamento','Pendente de encerramento'}


def permit_defaults(kind: str) -> dict:
    return {
        'code':next_code(kind),'status':'Rascunho','cluster':'','site':'','base':'','contractor':'','activity':'',
        'checklist':['']*len(MODULES[kind]['checklist']),'workers':[],'comments':'','closing_note':'',
        'open_date':'','open_time':'','close_date':'','close_time':'',
    }


def permit_worker_count(kind: str) -> int:
    return 5 if kind in {'pt_height','vegetation','lifting','tme'} else 6


def _permit_opening_date(data: dict) -> date|None:
    try:
        return parse_date_br(clean(data.get('open_date')))
    except Exception:
        return None


def refresh_pending_permit_closures(doc_id: int|None=None) -> int:
    """Vira PT aberta de dia anterior para 'Pendente de encerramento'.

    Não encerra a PT automaticamente: apenas encerra sua validade operacional.
    O responsável ainda precisa abrir o documento e confirmar o fechamento.
    """
    today=local_today(); changed=0; push_ids=[]
    with SessionLocal() as db:
        query=db.query(Document).filter(Document.kind.in_(list(MODULES.keys())),Document.status=='Em andamento')
        if doc_id is not None:
            query=query.filter(Document.id==doc_id)
        for target in query.all():
            data=doc_data(target)
            opened=_permit_opening_date(data)
            if not opened or opened>=today:
                continue
            target.status='Pendente de encerramento'
            data['status']='Pendente de encerramento'
            data['closure_pending_since']=today.strftime('%d/%m/%Y')
            target.data_json=json.dumps(data,ensure_ascii=False)
            target.updated_at=now()
            exists=(db.query(Notification.id)
                    .filter(Notification.document_id==target.id,
                            Notification.recipient_user_id==target.created_by,
                            Notification.kind=='pt_closure_pending')
                    .first())
            if not exists:
                note=_add_notification(
                    db,recipient_user_id=target.created_by,document_id=target.id,kind='pt_closure_pending',
                    message=f'{doc_reference_code(target)} venceu às 23:59 e está pendente de encerramento. A PT não é válida para continuar o trabalho no novo dia.',
                )
                
            if note: push_ids.append(note.id)
            changed+=1
        if changed:
            db.commit()
    _queue_push_notification_ids(push_ids)
    return changed


def _permit_checklist_issues(data: dict) -> tuple[list[int],list[int]]:
    checklist=list(data.get('checklist') or [])
    # NÃO não bloqueia mais: basta registrar a justificativa na caixa do checklist.
    bad=[] if clean(data.get('checklist_no_justification')) else [i+1 for i,a in enumerate(checklist) if a=='NÃO']
    blank=[i+1 for i,a in enumerate(checklist) if not a]
    return bad,blank


def _permit_opening_signature_error(kind: str, data: dict) -> str:
    if kind=='confined':
        if not clean(data.get('open_supervisor_name')) or not clean(data.get('open_vigia_name')):
            return 'Informe o supervisor e o vigia da abertura.'
        if not clean(data.get('open_supervisor_signature_image')) or not clean(data.get('open_vigia_signature_image')):
            return 'Registre as rubricas do supervisor e do vigia antes de iniciar a PT.'
    elif kind=='pt_height':
        if not clean(data.get('open_name')): return 'Informe o responsável pela abertura.'
        if not clean(data.get('open_signature_image')): return 'Registre a rubrica de abertura antes de iniciar a PT.'
    else:
        if not clean(data.get('open_responsible_name')): return 'Informe o responsável pela abertura.'
        if not clean(data.get('open_responsible_signature_image')): return 'Registre a rubrica de abertura antes de iniciar a PT.'
    return ''


def _permit_closing_signature_error(kind: str, data: dict) -> str:
    if kind=='confined':
        if not clean(data.get('close_supervisor_name')) or not clean(data.get('close_vigia_name')):
            return 'Informe o supervisor e o vigia do encerramento.'
        if not clean(data.get('close_supervisor_signature_image')) or not clean(data.get('close_vigia_signature_image')):
            return 'Registre as rubricas do supervisor e do vigia para encerrar a PT.'
    elif kind=='pt_height':
        if not clean(data.get('close_name')): return 'Informe o responsável pelo encerramento.'
        if not clean(data.get('close_signature_image')): return 'Registre a rubrica de encerramento.'
    else:
        if not clean(data.get('close_responsible_name')): return 'Informe o responsável pelo encerramento.'
        if not clean(data.get('close_responsible_signature_image')): return 'Registre a rubrica de encerramento.'
    return ''


def _clear_permit_closing_fields(kind: str, data: dict) -> None:
    data['close_date']=''; data['close_time']=''; data['closing_note']=''
    if kind=='confined':
        for key in ('close_supervisor_name','close_supervisor_signature_image','close_vigia_name','close_vigia_signature_image'):
            data[key]=''
    elif kind=='pt_height':
        data['close_name']=''; data['close_signature_image']=''
    else:
        data['close_responsible_name']=''; data['close_responsible_signature_image']=''


def _apply_default_permit_person(kind: str, data: dict, user: User, phase: str) -> None:
    person=user.full_name or user.username
    if phase=='open':
        if kind=='confined': data['open_supervisor_name']=clean(data.get('open_supervisor_name')) or person
        elif kind=='pt_height': data['open_name']=clean(data.get('open_name')) or person
        else: data['open_responsible_name']=clean(data.get('open_responsible_name')) or person
    else:
        if kind=='confined': data['close_supervisor_name']=clean(data.get('close_supervisor_name')) or person
        elif kind=='pt_height': data['close_name']=clean(data.get('close_name')) or person
        else: data['close_responsible_name']=clean(data.get('close_responsible_name')) or person


def _permit_action_time(data: dict) -> datetime:
    return now()


def normalize_permit_data_for_view(kind: str, data: dict) -> dict:
    d=dict(data)
    d['cluster'],d['site']=split_separate_cluster_site(d.get('cluster',''),d.get('site',''))
    d.setdefault('checklist',['']*len(MODULES[kind]['checklist'])); d['checklist']=(d['checklist']+['']*len(MODULES[kind]['checklist']))[:len(MODULES[kind]['checklist'])]
    d.setdefault('closing_note','')
    max_workers=permit_worker_count(kind)
    workers=list(d.get('workers',[]) or [])[:max_workers]
    while len(workers)>1 and not any(clean(workers[-1].get(k)) for k in ('name','company','signature','signature_image')):
        workers.pop()
    if not workers:
        workers=[{}]
    d['workers']=workers
    d['worker_count']=len(workers)
    d['worker_max']=max_workers
    for k in ['open_date','close_date']: d[k+'_input']=date_input(d.get(k,''))
    d['execution_locked']=d.get('status') in PERMIT_ACTIVE_STATUSES
    d['pending_closure']=d.get('status')=='Pendente de encerramento'
    return d

@app.get('/permit/{kind}/new',response_class=HTMLResponse)
def permit_new(request: Request, kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in MODULES: raise HTTPException(404)
    d=normalize_permit_data_for_view(kind,prefill_location(user,permit_defaults(kind)))
    return templates.TemplateResponse(request,'permit_form.html',context(request,cfg=MODULES[kind],kind=kind,data=d,doc=None,clusters=separate_clusters_for_user(user)[0],cluster_sites=separate_clusters_for_user(user)[1],work_types=PT_WORK_TYPES,entry_types=CONFINED_ENTRY_TYPES,air_rows=CONFINED_AIR_ROWS,readonly=False,now_date=local_today().strftime('%Y-%m-%d')))

@app.get('/permit/{kind}/{doc_id}/edit',response_class=HTMLResponse)
def permit_edit(request: Request, kind: str, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    refresh_pending_permit_closures(doc_id)
    doc=get_document(doc_id)
    if doc.kind!=kind: raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar este documento.')
    admin_mode=False
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    d=normalize_permit_data_for_view(kind,doc_data(doc))
    return templates.TemplateResponse(request,'permit_form.html',context(request,cfg=MODULES[kind],kind=kind,data=d,doc=doc,clusters=separate_clusters_for_user(user)[0],cluster_sites=separate_clusters_for_user(user)[1],work_types=PT_WORK_TYPES,entry_types=CONFINED_ENTRY_TYPES,air_rows=CONFINED_AIR_ROWS,readonly=False,now_date=local_today().strftime('%Y-%m-%d'),admin_edit=admin_mode))

def existing_sig(old: dict, key: str) -> str: return clean(old.get(key,''))

async def parse_permit(request: Request, kind: str, old: dict) -> tuple[dict,str]:
    form=await request.form(); verify_csrf(request,form.get('csrf_token')); cfg=MODULES[kind]
    d={'code':old.get('code') or next_code(kind),'status':old.get('status','Rascunho'),'cluster':clean(form.get('cluster')),'site':clean(form.get('site')),'base':clean(form.get('base')),'contractor':clean(form.get('contractor')),'activity':clean(form.get('activity')),'comments':clean(form.get('comments')),'closing_note':clean(form.get('closing_note')),'open_date':br_date(form.get('open_date')) if form.get('open_date') else clean(old.get('open_date')),'open_time':clean(form.get('open_time')) or clean(old.get('open_time')),'close_date':br_date(form.get('close_date')) if form.get('close_date') else clean(old.get('close_date')),'close_time':clean(form.get('close_time')) or clean(old.get('close_time'))}
    d['cluster'],d['site']=sanitize_separate_cluster_site(d['cluster'],d['site'])
    for key in ('linked_apr_id','linked_apr_code','linked_permit_name','pre_signature_flow','pre_signature_completed'):
        d[key]=clean(old.get(key))
    d['checklist']=[clean(form.get(f'check_{i}')) for i in range(len(cfg['checklist']))]
    d['checklist_no_justification']=clean(form.get('checklist_no_justification'))[:1500] if 'NÃO' in d['checklist'] else ''
    if kind=='pt_height':
        d['work_types']=[clean(x) for x in form.getlist('work_types')]
        d['open_name']=clean(form.get('open_name')); d['close_name']=clean(form.get('close_name'))
        d['open_signature_image']=save_signature(form.get('sig_open'),existing_sig(old,'open_signature_image'),f"{d['code']}_open")
        d['close_signature_image']=save_signature(form.get('sig_close'),existing_sig(old,'close_signature_image'),f"{d['code']}_close")
    elif kind=='confined':
        d['entry_types']=[clean(x) for x in form.getlist('entry_types')]
        d['air_readings']={key:[clean(form.get(f'air_{key}_{j}')) for j in range(4)] for _,_,key in CONFINED_AIR_ROWS}
        for pref in ('open','close'):
            for role in ('supervisor','vigia'):
                nk=f'{pref}_{role}_name'; sk=f'{pref}_{role}_signature_image'; d[nk]=clean(form.get(nk)); d[sk]=save_signature(form.get(f'sig_{pref}_{role}'),existing_sig(old,sk),f"{d['code']}_{pref}_{role}")
    else:
        d['open_responsible_name']=clean(form.get('open_responsible_name')); d['close_responsible_name']=clean(form.get('close_responsible_name'))
        for pref in ('open','close'):
            sk=f'{pref}_responsible_signature_image'; d[sk]=save_signature(form.get(f'sig_{pref}'),existing_sig(old,sk),f"{d['code']}_{pref}")
        if cfg.get('equipment_mode')=='multi': d['equipment_types']=[clean(x) for x in form.getlist('equipment_types')]
        elif cfg.get('equipment_mode')=='text': d['equipment_type']=clean(form.get('equipment_type'))
    oldworkers=old.get('workers',[]) or []; workers=[]
    try:
        worker_count=int(clean(form.get('worker_count')) or str(len(oldworkers) or 1))
    except ValueError:
        worker_count=len(oldworkers) or 1
    worker_count=max(1,min(worker_count,permit_worker_count(kind)))
    for i in range(worker_count):
        participant_id=clean(form.get(f'worker_participant_id_{i}')); participant_user_id=clean(form.get(f'worker_user_id_{i}')); cpf=clean(form.get(f'worker_cpf_{i}'))
        n=clean(form.get(f'worker_name_{i}')); c=clean(form.get(f'worker_company_{i}')); role=clean(form.get(f'worker_role_{i}')); prev=oldworkers[i].get('signature_image','') if i<len(oldworkers) else ''
        if participant_id.isdigit():
            with SessionLocal() as lookup_db:
                participant=lookup_db.get(Participant,int(participant_id)); company=lookup_db.get(Company,participant.company_id) if participant else None
                if participant and participant.active and company and company.active:
                    n=participant.full_name; c=company.name; role=participant.job_title or ''; cpf=participant.cpf; participant_user_id=str(participant.user_id or '')
                else:
                    participant_id=''; participant_user_id=''; cpf=''
        sig=save_signature(form.get(f'sig_worker_{i}'),prev,f"{d['code']}_worker_{i+1}")
        if n or c or sig:
            workers.append({'participant_id':participant_id,'participant_user_id':participant_user_id,'cpf':cpf,'name':n,'company':c,'role':role,'signature_image':sig,'signature':'RUBRICA' if sig else ''})
    d['workers']=workers
    action=clean(form.get('action')) or 'draft'
    return d,action

@app.post('/permit/{kind}/save')
async def permit_create_save(request: Request, kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in MODULES: raise HTTPException(404)
    old=permit_defaults(kind); d,action=await parse_permit(request,kind,old)
    return process_permit_save(request,user,kind,None,d,action)

@app.post('/permit/{kind}/{doc_id}/save')
async def permit_update_save(request: Request, kind: str, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar este documento.')
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    d,action=await parse_permit(request,kind,doc_data(doc))
    return process_permit_save(request,user,kind,doc,d,action)

def _permit_signature_field_names(kind: str, phase: str) -> list[str]:
    if kind=='confined':
        return [f'{phase}_supervisor_name',f'sig_{phase}_supervisor',f'{phase}_vigia_name',f'sig_{phase}_vigia']
    if kind=='pt_height':
        return [f'{phase}_name',f'sig_{phase}']
    return [f'{phase}_responsible_name',f'sig_{phase}']


def process_permit_save(request: Request,user: User,kind: str,doc: Document|None,d: dict,action: str):
    old_data=doc_data(doc) if doc else {}
    current_status=doc.status if doc else 'Rascunho'
    if action=='finalize':
        action='start' if current_status=='Rascunho' else 'close'

    if current_status in PERMIT_ACTIVE_STATUSES and action not in {'close'}:
        flash(request,'A PT já foi iniciada. Os dados de execução estão bloqueados; use “Encerrar PT” para concluir o documento.','error')
        return RedirectResponse(f'/permit/{kind}/{doc.id}/edit',303)

    if action=='start':
        if current_status!='Rascunho':
            flash(request,'Esta PT já foi iniciada.','error')
            return RedirectResponse(f'/permit/{kind}/{doc.id}/edit' if doc else f'/permit/{kind}/new',303)
        bad,blank=_permit_checklist_issues(d)
        validation_fields=[f'check_{i-1}' for i in [*bad,*blank]]
        if bad or blank:
            parts=[]
            if bad: parts.append('NÃO sem justificativa nos itens: '+', '.join(map(str,bad)))
            if blank: parts.append('Sem seleção: '+', '.join(map(str,blank)))
            if bad: validation_fields.append('checklist_no_justification')
            saved=save_validation_state(doc,kind,d,user,validation_fields,'Rascunho')
            flash(request,'Não é possível iniciar a PT. '+ ' | '.join(parts)+'. Descreva na caixa de justificativa o motivo do NÃO e as medidas adotadas. O que já foi preenchido foi mantido.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        if not d.get('activity'):
            saved=save_validation_state(doc,kind,d,user,['activity'],'Rascunho')
            flash(request,'Preencha a descrição/objetivo da atividade. O restante foi mantido.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        if clean(d.get('pre_signature_flow'))=='1':
            started=_permit_action_time(d)
            clear_validation_state(d)
            d['open_date']=started.strftime('%d/%m/%Y'); d['open_time']=started.strftime('%H:%M')
            d['pre_signature_completed']='1'
            saved=save_doc(doc,kind,d,user,'Rascunho')
            with SessionLocal() as db:
                rows=db.query(Notification).filter(Notification.document_id==saved.id,Notification.kind=='pt_pending',Notification.read==False).all()
                for n in rows:
                    n.read=True; n.read_at=now()
                if rows: db.commit()
            linked_apr_id=clean(d.get('linked_apr_id'))
            if linked_apr_id.isdigit():
                apr_doc=get_document(int(linked_apr_id)); apr_data=doc_data(apr_doc)
                next_url=_next_linked_permit_url(apr_doc,apr_data)
                if next_url:
                    flash(request,f'{d.get("linked_permit_name") or "Permissão"} concluída. Abrindo a próxima permissão selecionada.','success')
                    return RedirectResponse(next_url,303)
                # Última PT concluída: não volta para uma etapa de assinatura na APR.
                # O sistema abre diretamente a coleta única; cada rubrica será replicada para APR + PTs.
                return _begin_apr_signature_collection(request,user,apr_doc,apr_data,redirect_to_signatures=True)
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        _apply_default_permit_person(kind,d,user,'open')
        sig_error=_permit_opening_signature_error(kind,d)
        if sig_error:
            saved=save_validation_state(doc,kind,d,user,_permit_signature_field_names(kind,'open'),'Rascunho')
            flash(request,sig_error+' O restante foi mantido.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        started=_permit_action_time(d)
        clear_validation_state(d)
        d['open_date']=started.strftime('%d/%m/%Y'); d['open_time']=started.strftime('%H:%M')
        d['opened_by_user_id']=str(user.id); d['opened_by_name']=user.full_name or user.username
        d['valid_until']=started.strftime('%d/%m/%Y')+' 23:59'
        _clear_permit_closing_fields(kind,d)
        saved=save_doc(doc,kind,d,user,'Em andamento')
        audit(user.id,'iniciar_pt',f'{saved.code} {kind} em {d["open_date"]} {d["open_time"]}')
        if started.date() < local_today():
            refresh_pending_permit_closures(saved.id)
            saved=get_document(saved.id)
            flash(request,f'{doc_reference_code(saved)} sincronizada. A validade do dia {d["open_date"]} já terminou e a PT está pendente de encerramento.','success')
        else:
            flash(request,f'{doc_reference_code(saved)} iniciada. A PT é válida somente hoje, até 23:59. Ao concluir o trabalho, use “Encerrar PT”.','success')
        return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)

    if action=='close':
        if not doc or current_status not in PERMIT_ACTIVE_STATUSES:
            flash(request,'Somente uma PT em andamento ou pendente de encerramento pode ser encerrada.','error')
            return RedirectResponse(f'/permit/{kind}/{doc.id}/edit' if doc else f'/permit/{kind}/new',303)
        merged=dict(old_data)
        merged['code']=old_data.get('code') or d.get('code') or doc.code
        merged['closing_note']=clean(d.get('closing_note'))
        if kind=='confined':
            for key in ('close_supervisor_name','close_supervisor_signature_image','close_vigia_name','close_vigia_signature_image'):
                merged[key]=d.get(key) or old_data.get(key,'')
        elif kind=='pt_height':
            merged['close_name']=d.get('close_name') or old_data.get('close_name','')
            merged['close_signature_image']=d.get('close_signature_image') or old_data.get('close_signature_image','')
        else:
            merged['close_responsible_name']=d.get('close_responsible_name') or old_data.get('close_responsible_name','')
            merged['close_responsible_signature_image']=d.get('close_responsible_signature_image') or old_data.get('close_responsible_signature_image','')
        _apply_default_permit_person(kind,merged,user,'close')
        sig_error=_permit_closing_signature_error(kind,merged)
        if sig_error:
            saved=save_validation_state(doc,kind,merged,user,_permit_signature_field_names(kind,'close'),current_status)
            flash(request,sig_error+' Os dados de encerramento já informados foram mantidos.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        opened=_permit_opening_date(merged)
        if not opened:
            saved=save_validation_state(doc,kind,merged,user,['closing_note'],current_status)
            flash(request,'A PT não possui uma data de abertura válida. Os dados informados foram mantidos.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        closed=_permit_action_time(d)
        try:
            open_clock=datetime.strptime(clean(merged.get('open_time')) or '00:00','%H:%M').time()
            opened_at=datetime.combine(opened,open_clock)
        except Exception:
            opened_at=datetime.combine(opened,datetime.min.time())
        if closed < opened_at:
            saved=save_validation_state(doc,kind,merged,user,['closing_note'],current_status)
            flash(request,'A data/hora de encerramento não pode ser anterior à abertura da PT. Os dados informados foram mantidos.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        if opened < closed.date() and not merged['closing_note']:
            saved=save_validation_state(doc,kind,merged,user,['closing_note'],current_status)
            flash(request,'Como a PT venceu no dia anterior, informe uma observação de encerramento antes de concluir. Os demais dados foram mantidos.','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        clear_validation_state(merged)
        merged['close_date']=closed.strftime('%d/%m/%Y'); merged['close_time']=closed.strftime('%H:%M')
        merged['closed_by_user_id']=str(user.id); merged['closed_by_name']=user.full_name or user.username
        if merged['closing_note']:
            base_comments=clean(old_data.get('comments'))
            merged['comments']=(base_comments+'\n' if base_comments else '')+'Encerramento: '+merged['closing_note']
        previous_status=current_status
        saved=save_doc(doc,kind,merged,user,'Finalizada')
        try:
            saved=finalize_pdf(saved,merged)
        except Exception as e:
            with SessionLocal() as db:
                t=db.get(Document,saved.id)
                rollback=doc_data(t); rollback['status']=previous_status
                t.status=previous_status; t.finalized_at=None; t.data_json=json.dumps(rollback,ensure_ascii=False); t.updated_at=now(); db.commit()
            flash(request,f'O PDF não foi gerado. A PT continua como {previous_status}: {e}','error')
            return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
        with SessionLocal() as db:
            db.query(Notification).filter(Notification.document_id==saved.id,Notification.kind=='pt_closure_pending').update({'read':True,'read_at':now()},synchronize_session=False)
            db.commit()
        audit(user.id,'encerrar_pt',f'{saved.code} {kind} em {merged["close_date"]} {merged["close_time"]}')
        linked_apr_id=clean(merged.get('linked_apr_id'))
        if linked_apr_id.isdigit():
            flash(request,f'{doc_reference_code(saved)} encerrada e anexada à APR {merged.get("linked_apr_code") or linked_apr_id}.','success')
            return RedirectResponse(f'/apr/{linked_apr_id}/pts',303)
        return RedirectResponse(f'/document/{saved.id}/pdf',303)

    try:
        validate_dates(d,old=old_data)
    except Exception as e:
        saved=save_validation_state(doc,kind,d,user,['open_date','close_date'],'Rascunho')
        flash(request,str(e)+' O que já foi preenchido foi mantido.','error')
        return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)
    clear_validation_state(d)
    saved=save_doc(doc,kind,d,user,'Rascunho')
    audit(user.id,'salvar_rascunho',f'{saved.code} {kind}')
    flash(request,'Rascunho salvo com sucesso.','success')
    return RedirectResponse(f'/permit/{kind}/{saved.id}/edit',303)


APR_CRITICAL_PERMITS = [
    'Trabalho em Altura',
    'Espaço Confinado',
    'Intervenção Elétrica',
    'Linha Viva',
    'Supressão de Vegetação',
    'Içamento de Carga',
    'PT — TME',
]
APR_CRITICAL_PERMIT_KIND = {
    'Trabalho em Altura':'pt_height',
    'Espaço Confinado':'confined',
    'Intervenção Elétrica':'electrical',
    'Linha Viva':'line_live',
    'Supressão de Vegetação':'vegetation',
    'Içamento de Carga':'lifting',
    'PT — TME':'tme',
}
APR_CRITICAL_KIND_PERMIT = {v:k for k,v in APR_CRITICAL_PERMIT_KIND.items()}


def _apr_validity_bounds(apr_data: dict) -> tuple[date|None,date|None]:
    """Período operacional vigente da APR.

    Usa a última aprovação preenchida quando existir. Antes da
    aprovação, mantém a regra histórica da data da APR + 6 dias.
    """
    periods=[]
    for row in apr_data.get('approvals',[]) or []:
        st=parse_date_br(row.get('start'))
        en=parse_date_br(row.get('end'))
        if st:
            en=en or (st+timedelta(days=6))
            if en < st: en=st
            if en > st+timedelta(days=6): en=st+timedelta(days=6)
            periods.append((st,en))
    if periods:
        periods.sort(key=lambda x:x[0])
        return periods[-1]
    base=parse_date_br(apr_data.get('apr_date'))
    if not base: return None,None
    return base,base+timedelta(days=6)


def _apr_day_context(apr_data: dict, reference: date|None=None) -> dict:
    reference=reference or local_today()
    start,end=_apr_validity_bounds(apr_data)
    valid=bool(start and end and start<=reference<=end)
    day=(reference-start).days+1 if start and valid else None
    return {
        'start':start,'end':end,'valid_today':valid,'day_number':day,
        'start_label':start.strftime('%d/%m/%Y') if start else '',
        'end_label':end.strftime('%d/%m/%Y') if end else '',
    }


def _linked_permit_prefill(apr_doc: Document, apr_data: dict, permit_name: str) -> dict:
    kind=APR_CRITICAL_PERMIT_KIND[permit_name]
    d=permit_defaults(kind)
    d['cluster'],d['site']=split_separate_cluster_site(apr_data.get('cluster',''),apr_data.get('site',''))
    d['activity']=clean(apr_data.get('activity'))
    # A PT é diária. A data/hora pertencem ao dia em que esta nova PT foi criada,
    # nunca à data original da APR-mãe.
    d['open_date']=local_today().strftime('%d/%m/%Y')
    d['open_time']=now().strftime('%H:%M')
    d['linked_apr_id']=str(apr_doc.id)
    d['linked_apr_code']=data_reference_code('apr',apr_data,apr_doc.cluster,apr_doc.site) or apr_doc.code
    d['linked_permit_name']=permit_name
    d['pre_signature_flow']='1'
    d['pre_signature_completed']=''
    # Reaproveita a equipe da APR. As rubricas serão coletadas uma única vez na APR
    # e replicadas automaticamente para esta PT depois que todas as permissões forem preenchidas.
    workers=[]
    for item in apr_data.get('workers',[]) or []:
        name=clean(item.get('worker')); company=clean(item.get('company'))
        if name or company: workers.append({'name':name,'company':company,'signature_image':'','signature':''})
    d['workers']=workers[:permit_worker_count(kind)]
    return d


def _persist_document_data(doc_id: int, data: dict):
    with SessionLocal() as db:
        target=db.get(Document,doc_id)
        if not target: return
        target.data_json=json.dumps(data,ensure_ascii=False); target.updated_at=now(); db.commit()


def _linked_history_ids(apr_data: dict) -> list[int]:
    ids=[]
    for row in apr_data.get('linked_permit_history',[]) or []:
        try: rid=int((row or {}).get('id') or 0)
        except Exception: rid=0
        if rid and rid not in ids: ids.append(rid)
    # Migração silenciosa das versões antigas, que guardavam apenas a última PT
    # de cada tipo em linked_permit_ids.
    for raw in (apr_data.get('linked_permit_ids') or {}).values():
        try: rid=int(raw or 0)
        except Exception: rid=0
        if rid and rid not in ids: ids.append(rid)
    return ids


def linked_permit_records(apr_data: dict) -> list[dict]:
    rows=[]
    ids=_linked_history_ids(apr_data)
    if not ids: return rows
    with SessionLocal() as db:
        docs=db.query(Document).filter(Document.id.in_(ids)).all()
        by_id={d.id:d for d in docs}
        for rid in ids:
            doc=by_id.get(rid)
            if not doc or doc.kind not in APR_CRITICAL_KIND_PERMIT: continue
            pd=doc_data(doc)
            name=clean(pd.get('linked_permit_name')) or APR_CRITICAL_KIND_PERMIT.get(doc.kind,'')
            opened=parse_date_br(pd.get('open_date'))
            rows.append({
                'id':doc.id,'name':name,'kind':doc.kind,'code':doc_reference_code(doc),
                'status':doc.status,'date':clean(pd.get('open_date')),'open_time':clean(pd.get('open_time')),
                'close_date':clean(pd.get('close_date')),'close_time':clean(pd.get('close_time')),
                'pdf_path':doc.pdf_path,'ready':bool(doc.status=='Finalizada' and doc.pdf_path),
                '_sort_date':opened or date.min,'_sort_time':clean(pd.get('open_time')),
            })
    rows.sort(key=lambda r:(r['_sort_date'],r['_sort_time'],r['id']))
    for row in rows:
        row.pop('_sort_date',None); row.pop('_sort_time',None)
    return rows


def _append_linked_history(apr_data: dict, permit_doc: Document, permit_name: str) -> None:
    history=[dict(x or {}) for x in (apr_data.get('linked_permit_history') or [])]
    ids={str(x.get('id')) for x in history}
    if str(permit_doc.id) not in ids:
        pd=doc_data(permit_doc)
        history.append({
            'id':permit_doc.id,'name':permit_name,'kind':permit_doc.kind,
            'date':clean(pd.get('open_date')) or local_today().strftime('%d/%m/%Y'),
            'created_at':now().strftime('%d/%m/%Y %H:%M'),
        })
    apr_data['linked_permit_history']=history


def ensure_linked_permit(apr_doc: Document, apr_data: dict, permit_name: str, user: User) -> Document:
    """Retorna a PT aberta de hoje ou cria uma nova PT diária.

    PTs encerradas nunca são reutilizadas. Assim a mesma APR pode acumular
    diversas PTs ao longo de seus sete dias, inclusive mais de uma PT do mesmo
    tipo no mesmo dia quando a anterior já tiver sido encerrada.
    """
    kind=APR_CRITICAL_PERMIT_KIND[permit_name]
    ctx=_apr_day_context(apr_data)
    if not ctx['valid_today']:
        raise ValueError(f'A APR não está vigente hoje. Período atual: {ctx["start_label"] or "-"} a {ctx["end_label"] or "-"}.')
    today_label=local_today().strftime('%d/%m/%Y')

    # Primeiro procura uma PT ainda não finalizada deste mesmo tipo e deste dia.
    for row in reversed(linked_permit_records(apr_data)):
        if row['kind']!=kind or row['date']!=today_label: continue
        if row['status']!='Finalizada':
            return get_document(row['id'])

    # Compatibilidade com uma PT antiga em rascunho que estava apenas no mapping.
    mapping=dict(apr_data.get('linked_permit_ids') or {})
    raw=mapping.get(permit_name)
    if str(raw or '').isdigit():
        try:
            legacy=get_document(int(raw))
            if legacy.kind==kind and legacy.status=='Rascunho':
                pd=doc_data(legacy)
                old_date=parse_date_br(pd.get('open_date'))
                if not old_date or old_date==local_today():
                    pd.update(_linked_permit_prefill(apr_doc,apr_data,permit_name) | {k:v for k,v in pd.items() if clean(v)})
                    pd['linked_apr_id']=str(apr_doc.id); pd['linked_apr_code']=doc_reference_code(apr_doc); pd['linked_permit_name']=permit_name
                    legacy=save_doc(legacy,kind,pd,user,'Rascunho')
                    _append_linked_history(apr_data,legacy,permit_name)
                    mapping[permit_name]=legacy.id; apr_data['linked_permit_ids']=mapping
                    _persist_document_data(apr_doc.id,apr_data)
                    return legacy
        except Exception:
            pass

    created=save_doc(None,kind,_linked_permit_prefill(apr_doc,apr_data,permit_name),user,'Rascunho')
    mapping[permit_name]=created.id
    apr_data['linked_permit_ids']=mapping
    _append_linked_history(apr_data,created,permit_name)
    _persist_document_data(apr_doc.id,apr_data)
    audit(user.id,'criar_pt_diaria_vinculada',f'{apr_doc.code} -> {created.code} ({permit_name}) | {today_label}')
    notify_user(
        apr_doc.created_by,created,'pt_pending',
        f'{permit_name} está pendente. Preencha esta PT para continuar o fluxo da {doc_reference_code(apr_doc)}.',
        replace=True,
    )
    return created


def sync_apr_linked_permits(apr_doc: Document, apr_data: dict, user: User) -> dict:
    # Desde V36.17.14 a APR é aprovada primeiro. As PTs são criadas diariamente
    # depois da aprovação, portanto o envio da APR não cria PTs antecipadamente.
    apr_data['linked_permit_ids']=dict(apr_data.get('linked_permit_ids') or {})
    apr_data['linked_permit_history']=list(apr_data.get('linked_permit_history') or [])
    _persist_document_data(apr_doc.id,apr_data)
    return apr_data


def linked_permit_states(apr_data: dict) -> dict:
    # Mantém a leitura simples e estável usada pela tela da APR.
    # O histórico completo das PTs diárias fica em /apr/{id}/pts.
    mapping=apr_data.get('linked_permit_ids') or {}
    result={}
    with SessionLocal() as db:
        for name in APR_CRITICAL_PERMITS:
            kind=APR_CRITICAL_PERMIT_KIND[name]; doc=None
            raw_id=mapping.get(name)
            if str(raw_id or '').isdigit():
                candidate=db.get(Document,int(raw_id))
                if candidate and candidate.kind==kind: doc=candidate
            result[name]={
                'name':name,'kind':kind,'id':doc.id if doc else None,
                'code':doc_reference_code(doc) if doc else '',
                'status':doc.status if doc else 'Pendente',
                'pdf_path':doc.pdf_path if doc else None,
                'ready':bool(doc and doc.status=='Finalizada' and doc.pdf_path),
                'open_url':(f'/document/{doc.id}/pdf' if doc.status=='Finalizada' and doc.pdf_path else f'/permit/{kind}/{doc.id}/edit') if doc else '',
            }
    return result


def linked_permits_incomplete(apr_data: dict) -> list[str]:
    """Permissões críticas que ainda não foram preenchidas antes das assinaturas."""
    if clean(apr_data.get('critical_activity')).upper()!='SIM':
        return []
    selected=[p for p in (apr_data.get('critical_permits') or []) if p in APR_CRITICAL_PERMITS]
    mapping=apr_data.get('linked_permit_ids') or {}
    pending=[]
    with SessionLocal() as db:
        for name in selected:
            raw=mapping.get(name)
            doc=db.get(Document,int(raw)) if str(raw or '').isdigit() else None
            if not doc or doc.kind!=APR_CRITICAL_PERMIT_KIND[name]:
                pending.append(name); continue
            pd=doc_data(doc)
            if clean(pd.get('pre_signature_completed'))!='1': pending.append(name)
    return pending


def _next_linked_permit_url(apr_doc: Document, apr_data: dict) -> str|None:
    pending=linked_permits_incomplete(apr_data)
    if not pending: return None
    name=pending[0]
    return f'/apr/{apr_doc.id}/permit/{APR_CRITICAL_PERMIT_KIND[name]}/open'


def _sync_apr_signatures_to_linked_permits(apr_data: dict) -> None:
    """Copia nome/empresa/rubricas da equipe da APR para todas as PTs vinculadas."""
    workers=list(apr_data.get('workers') or [])
    ids=_linked_history_ids(apr_data)
    if not ids: return
    with SessionLocal() as db:
        for rid in ids:
            target=db.get(Document,rid)
            if not target or target.kind not in APR_CRITICAL_KIND_PERMIT: continue
            pd=doc_data(target)
            if clean(apr_data.get('_document_id')) and clean(pd.get('linked_apr_id'))!=clean(apr_data.get('_document_id')):
                continue
            existing=list(pd.get('workers') or [])
            synced=[]
            # O PDF da PT possui limite próprio de linhas. Recria a equipe a
            # partir da APR para não perder rubricas caso a PT tenha sido salva
            # sem todas as linhas durante o preenchimento.
            for i,aw in enumerate(workers[:permit_worker_count(target.kind)]):
                pw=dict(existing[i]) if i<len(existing) else {}
                pw['name']=clean(pw.get('name')) or clean(aw.get('worker')) or clean(aw.get('name'))
                pw['company']=clean(pw.get('company')) or clean(aw.get('company'))
                pw['role']=clean(pw.get('role')) or clean(aw.get('role'))
                pw['signature_image']=clean(aw.get('signature_image'))
                pw['signature']='RUBRICA' if pw['signature_image'] else ''
                pw['signed_at']=clean(aw.get('signed_at'))
                pw['signed_by_name']=clean(aw.get('signed_by_name'))
                synced.append(pw)
            pd['workers']=synced
            pd['participant_signature_status']=clean(apr_data.get('participant_signature_status'))
            target.data_json=json.dumps(pd,ensure_ascii=False); target.updated_at=now()
        db.commit()


def _apr_leader_approval_signature(apr_data: dict) -> tuple[str,str]:
    """Retorna nome e rubrica do líder/responsável que aprovou a APR."""
    for row in apr_data.get('approvals') or []:
        sig=clean((row or {}).get('signature_image'))
        if sig:
            name=clean((row or {}).get('name')) or clean(apr_data.get('approved_by_name')) or clean(apr_data.get('approver_name'))
            return name,sig
    return clean(apr_data.get('approved_by_name')) or clean(apr_data.get('approver_name')),''


def _apply_apr_leader_to_linked_permit(kind: str, permit_data: dict, apr_data: dict) -> None:
    """Preenche automaticamente o responsável da PT com a aprovação da APR.

    Isso é aplicado somente nas PTs do fluxo APR -> PTs -> assinaturas -> aprovação.
    A rubrica do líder não substitui as rubricas da equipe; ela ocupa os campos
    de responsável/supervisor existentes no modelo oficial da própria PT.
    """
    if clean(permit_data.get('pre_signature_flow'))!='1':
        return
    name,sig=_apr_leader_approval_signature(apr_data)
    if not name and not sig:
        return
    if kind=='pt_height':
        if name:
            permit_data['open_name']=clean(permit_data.get('open_name')) or name
            permit_data['close_name']=clean(permit_data.get('close_name')) or name
        if sig:
            permit_data['open_signature_image']=clean(permit_data.get('open_signature_image')) or sig
            permit_data['close_signature_image']=clean(permit_data.get('close_signature_image')) or sig
    elif kind=='confined':
        # Na PET há papéis distintos de Supervisor e Vigia. A aprovação da APR
        # preenche automaticamente apenas o Supervisor; o Vigia não é inferido.
        if name:
            permit_data['open_supervisor_name']=clean(permit_data.get('open_supervisor_name')) or name
            permit_data['close_supervisor_name']=clean(permit_data.get('close_supervisor_name')) or name
        if sig:
            permit_data['open_supervisor_signature_image']=clean(permit_data.get('open_supervisor_signature_image')) or sig
            permit_data['close_supervisor_signature_image']=clean(permit_data.get('close_supervisor_signature_image')) or sig
    else:
        if name:
            permit_data['open_responsible_name']=clean(permit_data.get('open_responsible_name')) or name
            permit_data['close_responsible_name']=clean(permit_data.get('close_responsible_name')) or name
        if sig:
            permit_data['open_responsible_signature_image']=clean(permit_data.get('open_responsible_signature_image')) or sig
            permit_data['close_responsible_signature_image']=clean(permit_data.get('close_responsible_signature_image')) or sig
    permit_data['responsible_from_apr_approval']='1'


def _finalize_prepared_linked_permits(apr_doc: Document, apr_data: dict, user: User) -> None:
    """Finaliza as PTs preenchidas no fluxo da APR e gera seus PDFs após a aprovação."""
    _sync_apr_signatures_to_linked_permits({**apr_data,'_document_id':str(apr_doc.id)})
    ids=_linked_history_ids(apr_data)
    for rid in ids:
        try:
            target=get_document(rid)
        except Exception:
            continue
        if target.kind not in APR_CRITICAL_KIND_PERMIT or target.status=='Finalizada': continue
        pd=doc_data(target)
        if clean(pd.get('pre_signature_completed'))!='1': continue
        # A aprovação da APR é a assinatura do Líder ou responsável pela atividade.
        # Nas PTs preparadas antes das assinaturas, ela preenche automaticamente
        # os campos de responsável do modelo antes da geração do PDF.
        _apply_apr_leader_to_linked_permit(target.kind,pd,apr_data)
        stamp=now()
        pd['open_date']=clean(pd.get('open_date')) or stamp.strftime('%d/%m/%Y')
        pd['open_time']=clean(pd.get('open_time')) or stamp.strftime('%H:%M')
        pd['close_date']=clean(pd.get('close_date')) or stamp.strftime('%d/%m/%Y')
        pd['close_time']=clean(pd.get('close_time')) or stamp.strftime('%H:%M')
        pd['status']='Finalizada'
        pd['finalized_with_apr']='1'
        saved=save_doc(target,target.kind,pd,user,'Finalizada')
        finalize_pdf(saved,pd)


def linked_permit_pdf_paths(apr_data: dict) -> list[Path]:
    paths=[]
    for row in linked_permit_records(apr_data):
        if row.get('ready') and row.get('pdf_path'):
            p=STORAGE_DIR/row['pdf_path']
            if p.exists(): paths.append(p)
    return paths

# -------------------- APR --------------------
def apr_defaults():
    return {
        'code':next_code('apr'),'status':'Rascunho','cluster':'','severity':'','activity':'',
        'apr_date':local_today().strftime('%d/%m/%Y'),'apr_time':now().strftime('%H:%M'),
        'leader_phone':'','sst_phone':'','radio_channel':'','critical_activity':'SIM','critical_permits':[],'linked_permit_ids':{},'linked_permit_history':[],
        'steps':[{'stage':'','hazard':'','risk':'','severity':'','control':''}],
        'checklist':['']*24,'approvals':[{} for _ in range(5)],'workers':[{}],
        'participant_signature_status':'Não solicitada','participant_signatures_requested_at':'','participant_signatures_requested_by_id':'','participant_signatures_requested_by_name':'',
        'approver_user_id':'','approver_name':'','approver_extra_user_ids':[],'approver_extra_names':[],'approval_requested_at':'','submitted_by_id':'','submitted_by_name':'',
        'approved_by_id':'','approved_by_name':'','approved_at':''
    }

def apr_view(d):
    x=dict(d); x['apr_date_input']=date_input(x.get('apr_date',''))
    x['severity']=normalize_apr_severity(x.get('severity'))
    # Tela da APR usa a regra estável: data da APR + 6 dias.
    # O módulo diário de PTs calcula separadamente a aprovação vigente.
    try:
        _apr_base=parse_date_br(x.get('apr_date'))
        x['apr_valid_from']=_apr_base.strftime('%d/%m/%Y')
        x['apr_valid_until']=(_apr_base+timedelta(days=6)).strftime('%d/%m/%Y')
    except Exception:
        x['apr_valid_from']=''
        x['apr_valid_until']=''
    x['critical_activity']='SIM' if clean(x.get('critical_activity')).upper()=='SIM' else 'NÃO'
    x['critical_permits']=[p for p in (x.get('critical_permits') or []) if p in APR_CRITICAL_PERMITS]
    x['linked_permit_ids']=dict(x.get('linked_permit_ids') or {})
    x['linked_permit_history']=list(x.get('linked_permit_history') or [])
    extras=x.get('approver_extra_user_ids') or []
    if isinstance(extras,str): extras=[extras]
    x['approver_extra_user_ids']=[clean(v) for v in extras if clean(v)]
    extra_names=x.get('approver_extra_names') or []
    if isinstance(extra_names,str): extra_names=[extra_names]
    x['approver_extra_names']=[clean(v) for v in extra_names if clean(v)]
    steps=[dict(s or {}) for s in (x.get('steps',[]) or [])[:APR_MAX_STEPS]]
    for _step in steps:
        _step['severity']=normalize_apr_severity(_step.get('severity'))
        _hazards=_normalize_multi_step_values(_step.get('hazards'),_step.get('hazard'))
        _risks=_normalize_multi_step_values(_step.get('risks'),_step.get('risk'))
        _step['hazards']=_hazards
        _step['risks']=_risks
        _step['hazard']='\n'.join(_hazards)
        _step['risk']='\n'.join(_risks)
        _step['hazard_custom']='\n'.join(v for v in _hazards if v not in HAZARD_OPTIONS)
        _step['risk_custom']='\n'.join(v for v in _risks if v not in RISK_CATALOG)
    # Remove somente etapas vazias no final. Assim, APRs antigas que tinham 5 linhas
    # vazias por padrão passam a abrir com 1 etapa, sem perder nenhuma etapa preenchida.
    while len(steps)>1 and not any(clean(steps[-1].get(k)) for k in ('stage','hazard','risk','severity','control')):
        steps.pop()
    if len(steps)<1: steps = [{}]
    x['steps']=steps; x['step_count']=len(steps); x['checklist']=(x.get('checklist',[])+['']*24)[:24]
    # Na tela administrativa, começa mostrando somente a Aprovação 1.
    # Aprovações já preenchidas continuam visíveis, sem perder o histórico.
    approvals=list(x.get('approvals',[]) or [])[:5]
    while len(approvals)>1 and not any(clean(approvals[-1].get(k)) for k in ('name','role','start','end','signature','signature_image')):
        approvals.pop()
    if len(approvals)<1: approvals=[{}]
    x['approvals']=approvals
    workers=list(x.get('workers',[]) or [])[:24]
    # Remove somente integrantes vazios no final. Registros preenchidos permanecem intactos.
    worker_keys=('participant_id','participant_user_id','cpf','company','worker','role','date','signature','signature_image')
    while len(workers)>1 and not any(clean(workers[-1].get(k)) for k in worker_keys):
        workers.pop()
    visible_workers=max(1,len(workers))
    x['workers']=(workers+[{} for _ in range(visible_workers-len(workers))])[:24]; x['worker_count']=len(x['workers'])
    requested=bool(clean(x.get('participant_signatures_requested_at')) or clean(x.get('participant_signature_status')) in {'Pendente','Concluída'})
    signed_count=0
    participant_count=0
    for a in x['approvals']:
        a['start_input']=date_input(a.get('start','')); a['end_input']=date_input(a.get('end',''))
    for w in x['workers']:
        # Antes da assinatura, exibe sempre a data atual no campo somente leitura.
        # Quando o integrante assina, a data real da assinatura fica gravada e prevalece.
        w['date_input']=date_input(w.get('date','')) or local_today().strftime('%Y-%m-%d')
        w['cpf_input']=cpf_format(w.get('cpf')) if clean(w.get('cpf')) else ''
        w['cpf_masked']=cpf_mask(w.get('cpf')) if clean(w.get('cpf')) else ''
        if clean(w.get('participant_id')):
            participant_count+=1
        if clean(w.get('signature_image')):
            signed_count+=1
            w['signature_status']='Assinado'
        elif requested and clean(w.get('participant_id')):
            w['signature_status']='Pendente assinatura'
        else:
            w['signature_status']='Não solicitada'
    x['participant_signed_count']=signed_count
    x['participant_count']=participant_count
    x['participant_signature_status']='Concluída' if requested and participant_count and signed_count==participant_count else ('Pendente' if requested else 'Não solicitada')
    return x

def _approver_ids_for_data(data: dict) -> list[int]:
    ids=[]
    raw=[data.get('approver_user_id')]
    extras=data.get('approver_extra_user_ids') or []
    if isinstance(extras,str): extras=[extras]
    raw += list(extras)
    for value in raw:
        try: aid=int(value or 0)
        except Exception: aid=0
        if aid and aid not in ids: ids.append(aid)
    return ids


def _approvers_for_data(data: dict) -> list[User]:
    ids=_approver_ids_for_data(data)
    if not ids: return []
    with SessionLocal() as db:
        rows=db.query(User).filter(User.id.in_(ids),User.role==ROLE_SUPER_ADMIN,User.active==True).all()
        rows_map={u.id:u for u in rows}
        ordered=[]
        for aid in ids:
            u=rows_map.get(aid)
            if u:
                db.expunge(u)
                ordered.append(u)
        return ordered


def _approver_for_data(data: dict) -> User|None:
    rows=_approvers_for_data(data)
    return rows[0] if rows else None

def _participant_signature_required(data: dict) -> bool:
    return bool(clean(data.get('participant_signatures_requested_at')) or clean(data.get('participant_signature_status')) in {'Pendente','Concluída'})

def _participant_signature_counts(data: dict) -> tuple[int,int]:
    workers=list(data.get('workers',[]) or [])
    required=[w for w in workers if clean(w.get('participant_id'))]
    signed=[w for w in required if clean(w.get('signature_image'))]
    return len(signed),len(required)

def _participant_signatures_complete(data: dict) -> bool:
    signed,total=_participant_signature_counts(data)
    return bool(_participant_signature_required(data) and total>0 and signed==total)

def _validate_apr_workers_for_signature(data: dict) -> list[dict]:
    workers=[dict(w) for w in (data.get('workers') or []) if any(clean(w.get(k)) for k in ('participant_id','participant_user_id','cpf','company','worker','role'))]
    if not workers:
        raise ValueError('Adicione pelo menos um integrante usando CPF ou nome antes de solicitar as assinaturas.')
    participant_ids=[]
    with SessionLocal() as db:
        for idx,w in enumerate(workers,1):
            try: participant_id=int(w.get('participant_id') or 0)
            except Exception: participant_id=0
            try: participant_user_id=int(w.get('participant_user_id') or 0)
            except Exception: participant_user_id=0
            if not participant_id or not clean(w.get('cpf')) or not clean(w.get('worker')) or not clean(w.get('company')):
                raise ValueError(f'Integrante {idx}: use a busca por CPF ou nome para vincular um participante cadastrado.')
            if participant_id in participant_ids:
                raise ValueError(f'Integrante {idx}: o mesmo participante não pode ser adicionado duas vezes na APR.')
            participant_ids.append(participant_id)
            participant=db.get(Participant,participant_id)
            if not participant or not participant.active or participant.cpf!=cpf_digits(w.get('cpf')):
                raise ValueError(f'Integrante {idx}: cadastro do participante não está disponível. Faça uma nova busca por CPF ou nome.')
            company=db.get(Company,participant.company_id)
            if not company or not company.active:
                raise ValueError(f'Integrante {idx}: a empresa do participante está inativa.')
            if not participant_user_id or participant.user_id!=participant_user_id:
                raise ValueError(f'Integrante {idx}: o participante precisa estar vinculado a um usuário do Safety Plus para receber a solicitação de assinatura.')
            linked_user=db.get(User,participant_user_id)
            if not linked_user or not linked_user.active:
                raise ValueError(f'Integrante {idx}: o usuário vinculado ao participante está inativo.')
            w['participant_id']=str(participant.id)
            w['participant_user_id']=str(linked_user.id)
            w['cpf']=participant.cpf
            w['company']=company.name
            w['worker']=participant.full_name
            w['role']=participant.job_title or ''
    return workers

def _notify_apr_participant_signatures(doc: Document, data: dict, requester: User):
    requester_name=requester.full_name or requester.username
    recipients=[]
    seen=set()
    for w in data.get('workers') or []:
        try: uid=int(w.get('participant_user_id') or 0)
        except Exception: uid=0
        if uid and uid not in seen:
            seen.add(uid); recipients.append(uid)
    push_ids=[]
    with SessionLocal() as db:
        db.query(Notification).filter(Notification.document_id==doc.id,Notification.kind=='apr_participant_signature').delete(synchronize_session=False)
        for uid in recipients:
            note=_add_notification(db,recipient_user_id=uid,document_id=doc.id,kind='apr_participant_signature',message=f'{doc_reference_code(doc)}: {requester_name} solicitou sua assinatura para a APR e as PTs vinculadas.')
            
            if note: push_ids.append(note.id)
        db.commit()
    _queue_push_notification_ids(push_ids)

def _clear_apr_signature_notifications(doc_id: int):
    with SessionLocal() as db:
        db.query(Notification).filter(Notification.document_id==doc_id,Notification.kind=='apr_participant_signature').delete(synchronize_session=False)
        db.commit()



def _apr_template_code() -> str:
    """Código interno único para modelos de APR (não aparece como APR operacional)."""
    return f'APRMOD-{now().strftime("%Y%m%d%H%M%S")}-{secrets.token_hex(3).upper()}'


def _apr_copy_workers(source: dict, copy_team: bool=False) -> list[dict]:
    if not copy_team:
        return [{}]
    copied=[]
    for raw in (source.get('workers') or []):
        w=dict(raw or {})
        if not any(clean(w.get(k)) for k in ('participant_id','cpf','company','worker','role')):
            continue
        copied.append({
            'participant_id':clean(w.get('participant_id')),
            'participant_user_id':clean(w.get('participant_user_id')),
            'cpf':cpf_digits(w.get('cpf')),
            'company':clean(w.get('company')),
            'worker':clean(w.get('worker')),
            'role':clean(w.get('role')),
            'date':'','signature':'','signature_image':'','signature_status':'',
            'signed_at':'','signed_by_user_id':'','signed_by_name':'',
        })
    return copied or [{}]


def _apr_clone_data(source: dict, *, source_doc: Document|None=None, copy_team: bool=False, template_doc: Document|None=None) -> dict:
    """Cria uma NOVA APR a partir de outra APR/modelo sem reutilizar aprovações ou confirmações."""
    base=apr_defaults()
    for key in ('cluster','activity','leader_phone','sst_phone','radio_channel','critical_activity'):
        base[key]=source.get(key,base.get(key,''))
    base['critical_permits']=[p for p in (source.get('critical_permits') or []) if p in APR_CRITICAL_PERMITS]
    base['steps']=[]
    for x in (source.get('steps') or [])[:APR_MAX_STEPS]:
        hazards=_normalize_multi_step_values(x.get('hazards'),x.get('hazard'))
        risks=_normalize_multi_step_values(x.get('risks'),x.get('risk'))
        base['steps'].append({
            'stage':clean(x.get('stage')),
            'hazards':hazards,'hazard':'\n'.join(hazards),
            'risks':risks,'risk':'\n'.join(risks),
            'severity':normalize_apr_severity(x.get('severity')),
            'control':clean(x.get('control')),
        })
    if not base['steps']: base['steps']=[{}]
    # Cada nova APR precisa confirmar novamente os 24 itens de verificação.
    base['checklist']=['']*24
    base['workers']=_apr_copy_workers(source,copy_team=copy_team)
    base['code']=next_code('apr')
    base['status']='Rascunho'
    base['apr_date']=local_today().strftime('%d/%m/%Y')
    base['apr_time']=now().strftime('%H:%M')
    base['severity']=''
    base['approvals']=[{} for _ in range(5)]
    base['linked_permit_ids']={}
    base['linked_permit_history']=[]
    base['model_review_required']='SIM'
    if template_doc:
        tdata=doc_data(template_doc)
        base['created_from_template_id']=str(template_doc.id)
        base['created_from_template_name']=clean(tdata.get('template_name')) or template_doc.activity or 'Modelo de APR'
        base['model_source_label']=f'Modelo: {base["created_from_template_name"]}'
    elif source_doc:
        base['created_from_apr_id']=str(source_doc.id)
        base['created_from_apr_code']=doc_reference_code(source_doc)
        base['model_source_label']=f'APR anterior: {doc_reference_code(source_doc)}'
    return base


def _save_apr_template_record(source_doc: Document, source: dict, user: User, name: str) -> Document:
    payload=_apr_clone_data(source,source_doc=source_doc,copy_team=False)
    payload['template_name']=clean(name) or clean(source.get('activity')) or doc_reference_code(source_doc)
    payload['template_source_apr_id']=str(source_doc.id)
    payload['template_source_apr_code']=doc_reference_code(source_doc)
    payload['template_created_by_name']=user.full_name or user.username
    # Modelo não é uma APR operacional: código/data/fluxo serão recriados quando usado.
    payload['code']=_apr_template_code()
    payload['status']='Modelo'
    payload['model_review_required']=''
    with SessionLocal() as db:
        target=Document(
            code=payload['code'],kind='apr_template',title='Modelo de APR',status='Modelo',
            cluster=clean(source.get('cluster')),site='',activity=payload['template_name'],
            data_json=json.dumps(payload,ensure_ascii=False),created_by=user.id,created_at=now(),updated_at=now(),
        )
        db.add(target); db.commit(); db.refresh(target); db.expunge(target)
        return target



@app.get('/document/{doc_id}/historico',response_class=HTMLResponse)
def document_history(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if not user_can_access_document(user,doc):
        raise HTTPException(403,'Você não tem permissão para acessar este documento.')
    code=doc_reference_code(doc)
    needles=[n for n in {doc.code,code} if n]
    with SessionLocal() as db:
        conds=[AuditLog.detail.like(f'%{n}%') for n in needles]+[AuditLog.detail.like(f'doc_id={doc.id}%'),AuditLog.detail.like(f'doc={doc.id} %')]
        rows=db.query(AuditLog).filter(or_(*conds)).order_by(desc(AuditLog.id)).limit(200).all()
        names={u.id:(u.full_name or u.username) for u in db.query(User).filter(User.id.in_([r.user_id for r in rows if r.user_id])).all()} if rows else {}
        versions=db.query(DocumentVersion).filter(DocumentVersion.document_id==doc.id).order_by(desc(DocumentVersion.id)).limit(30).all()
    events=[]
    for r in rows:
        d=(r.detail or '').strip()
        if d.startswith('{') or d.startswith('['): d='Alteração administrativa registrada'
        events.append({'at':r.created_at,'who':names.get(r.user_id,'Sistema' if not r.user_id else f'Usuário {r.user_id}'),'action':r.action.replace('_',' ').capitalize(),'detail':d[:220]})
    snaps=[{'at':v.created_at,'status':v.status,'activity':v.activity} for v in versions]
    return templates.TemplateResponse(request,'document_history.html',context(request,doc=doc,code=code,events=events,snaps=snaps))

@app.post('/apr/{doc_id}/observations')
async def apr_add_execution_observation(request: Request, doc_id: int):
    user=current_user(request)
    if not user:
        return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    text_value=clean(form.get('observation'))
    note_type=clean(form.get('note_type'))
    if note_type not in {'Observação','Etapa adicional'}: note_type='Observação'
    step_extra=None
    if note_type=='Etapa adicional':
        stage=clean(form.get('step_stage')); hazard=clean(form.get('step_hazard')); risk=clean(form.get('step_risk'))
        sev=normalize_apr_severity(form.get('step_severity')); control=clean(form.get('step_control'))
        if not (stage and hazard and risk and sev and control):
            flash(request,'Etapa completa: preencha etapa, perigo, risco, severidade e medida de controle.','error')
            return RedirectResponse('/',303)
        step_extra={'stage':stage,'hazard':hazard,'risk':risk,'severity':sev,'control':control}
        text_value=' | '.join([f'Etapa: {stage}',f'Perigo: {hazard}',f'Risco: {risk}',f'Severidade: {sev}',f'Controle: {control}'])
    if not text_value:
        flash(request,'Digite a observação antes de salvar.','error')
        return RedirectResponse('/',303)
    if len(text_value)>2000:
        flash(request,'A observação deve ter no máximo 2000 caracteres.','error')
        return RedirectResponse('/',303)
    with SessionLocal() as db:
        target=db.get(Document,doc_id)
        if not target or target.kind!='apr':
            raise HTTPException(404,'APR não encontrada.')
        if target.status!='Finalizada':
            raise HTTPException(409,'A observação pós-conclusão só pode ser registrada em APR finalizada.')
        db.expunge(target)
    if not _can_manage_finalized_apr(user,target):
        raise HTTPException(403,'Você não tem permissão para registrar observação nesta APR.')
    data=doc_data(target)
    notes=list(data.get('execution_observations') or [])
    notes.append({
        'text':text_value,
        'type':note_type,
        **({'step':step_extra} if step_extra else {}),
        'author_user_id':str(user.id),
        'author':user.full_name or user.username,
        'created_at':now().strftime('%d/%m/%Y %H:%M'),
    })
    data['execution_observations']=notes[-50:]
    with SessionLocal() as db:
        db_target=db.get(Document,target.id)
        db_target.data_json=json.dumps(data,ensure_ascii=False)
        db_target.updated_at=now()
        db.commit(); db.refresh(db_target); db.expunge(db_target)
    try:
        rebuilt=finalize_pdf(db_target,data)
    except Exception as exc:
        audit(user.id,'erro_observacao_apr_pdf',f'{target.code}: {exc}')
        flash(request,'Observação registrada, mas houve falha ao atualizar o PDF. O sistema tentará reconstruí-lo ao abrir.','error')
        return RedirectResponse('/',303)
    audit(user.id,'adicionar_observacao_apr',f'{doc_reference_code(rebuilt)} | {text_value[:160]}')
    flash(request,'Observação adicionada à APR concluída e PDF atualizado.','success')
    return RedirectResponse(f'/document/{rebuilt.id}/pdf',303)


def _can_manage_finalized_apr(user: User, doc: Document) -> bool:
    if is_super_admin(user): return True
    if user.role==ROLE_ADMIN: return admin_scope_allows_document(user,doc)
    return doc.created_by==user.id


def _execution_member_signature_url(doc_id: int, member_id: str) -> str:
    return f'/apr/{doc_id}/integrantes/{member_id}/assinar'


def _execution_member_for_notification(data: dict, note: Notification, user_id: int) -> dict|None:
    entries=(data.get('execution_member_requests') or [])+(data.get('execution_members') or [])
    mine=[m for m in entries if str(m.get('participant_user_id') or '')==str(user_id)]
    exact=next((m for m in mine if str(m.get('notification_id') or '')==str(note.id)),None)
    return exact or next((m for m in mine if not clean(m.get('signature_image'))),None)


def _execution_member_document(db, doc_id: int, member_id: str, *, lock: bool=False):
    """Links antigos acompanham a APR vigente, mantendo o identificador do pedido."""
    seen=set()
    while doc_id not in seen and len(seen)<100:
        seen.add(doc_id)
        query=db.query(Document).filter(Document.id==doc_id)
        doc=query.with_for_update().first() if lock else query.first()
        if not doc or doc.kind!='apr': raise HTTPException(404,'APR não encontrada.')
        data=doc_data(doc)
        if doc.status=='Substituída' and str(data.get('replaced_by_apr_id') or '').isdigit():
            doc_id=int(data['replaced_by_apr_id']); continue
        for entry in (data.get('execution_member_requests') or [])+(data.get('execution_members') or []):
            if clean(entry.get('id'))==member_id:
                return doc,data,dict(entry)
        raise HTTPException(404,'Solicitação de assinatura não encontrada.')
    raise HTTPException(409,'Não foi possível localizar a versão atual desta APR.')


def _require_execution_member_signer(db, member: dict, user: User) -> None:
    if str(member.get('participant_user_id') or '')!=str(user.id):
        raise HTTPException(403,'Somente o próprio integrante pode assinar esta solicitação pela sua conta.')
    participant=db.get(Participant,int(member['participant_id']))
    company=db.get(Company,participant.company_id) if participant else None
    signer=db.get(User,user.id)
    if (not participant or not participant.active or participant.user_id!=user.id
            or not company or not company.active or not signer or not signer.active):
        raise HTTPException(403,'O integrante precisa manter um cadastro e uma conta ativa vinculada para assinar.')


@app.get('/apr/{doc_id}/membro',response_class=HTMLResponse)
def apr_add_member_page(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404,'APR não encontrada.')
    if doc.status!='Finalizada':
        flash(request,'Só é possível incluir integrante em APR finalizada.','error')
        return RedirectResponse('/',303)
    if not _can_manage_finalized_apr(user,doc):
        raise HTTPException(403,'Você não tem permissão para alterar esta APR.')
    data=doc_data(doc)
    return templates.TemplateResponse(request,'apr_add_member.html',context(
        request,doc=doc,data=data,members=list(data.get('execution_members') or []),
        pending_members=list(data.get('execution_member_requests') or [])))


@app.post('/apr/{doc_id}/membro')
async def apr_add_member_submit(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: participant_id=int(clean(form.get('participant_id')))
    except Exception: participant_id=0
    reason=clean(form.get('reason'))[:500]
    if not participant_id:
        flash(request,'Pesquise e selecione o integrante antes de incluir.','error')
        return RedirectResponse(f'/apr/{doc_id}/membro',303)
    push_ids=[]
    with _CODE_LOCK, SessionLocal.begin() as db:
        target=db.query(Document).filter(Document.id==doc_id).with_for_update().first()
        if not target or target.kind!='apr':
            raise HTTPException(404,'APR não encontrada.')
        if target.status!='Finalizada':
            raise HTTPException(409,'Só é possível incluir integrante em APR finalizada.')
        if not _can_manage_finalized_apr(user,target):
            raise HTTPException(403,'Você não tem permissão para alterar esta APR.')
        participant=db.get(Participant,participant_id)
        company=db.get(Company,participant.company_id) if participant else None
        if not participant or not participant.active or not company or not company.active:
            flash(request,'Participante não encontrado ou inativo.','error')
            return RedirectResponse(f'/apr/{doc_id}/membro',303)
        linked=db.get(User,participant.user_id) if participant.user_id else None
        if not linked or not linked.active:
            flash(request,'Vincule este integrante a um usuário ativo para que ele receba e assine a solicitação pela própria conta.','error')
            return RedirectResponse(f'/apr/{doc_id}/membro',303)
        data=doc_data(target)
        entries=(data.get('workers') or [])+(data.get('execution_members') or [])+(data.get('execution_member_requests') or [])
        if any(str(w.get('participant_id') or '')==str(participant.id) for w in entries):
            flash(request,'Este integrante já faz parte da equipe ou possui uma solicitação de assinatura pendente.','error')
            return RedirectResponse(f'/apr/{doc_id}/membro',303)
        if len(data.get('execution_members') or [])+len(data.get('execution_member_requests') or [])>=50:
            raise HTTPException(409,'Esta APR já atingiu o limite de integrantes adicionais.')
        member={
            'id':secrets.token_urlsafe(18),'participant_id':str(participant.id),'participant_user_id':str(linked.id),
            'worker':participant.full_name,'role':participant.job_title or '','company':company.name,
            'cpf_masked':cpf_mask(participant.cpf),'reason':reason,'signature_status':'Pendente','signature_image':'',
            'added_by_user_id':str(user.id),'added_by':user.full_name or user.username,
            'created_at':now().strftime('%d/%m/%Y %H:%M'),
        }
        # Uma solicitação obrigatória permanece disponível no sino e nas pendências.
        note=Notification(recipient_user_id=linked.id,document_id=target.id,kind='apr_execution_member_signature',
            message=f'{doc_reference_code(target)}: {member["added_by"]} solicitou sua assinatura para incluir você na equipe da APR.',read=False,created_at=now())
        db.add(note); db.flush()
        member['notification_id']=str(note.id)
        data['execution_member_requests']=list(data.get('execution_member_requests') or [])+[member]
        target.data_json=json.dumps(data,ensure_ascii=False); target.updated_at=now()
        if _notification_enabled(linked.id,note.kind): push_ids.append(note.id)
    _queue_push_notification_ids(push_ids)
    audit(user.id,'solicitar_inclusao_membro_apr',f'{target.code} | integrante={member["worker"]} | destinatario={member["participant_user_id"]}')
    flash(request,f'Solicitação enviada para {member["worker"]}. O integrante deve entrar na própria conta para assinar.','success')
    return RedirectResponse(f'/apr/{doc_id}/membro',303)


@app.get('/apr/{doc_id}/integrantes/{member_id}/assinar',response_class=HTMLResponse)
def apr_execution_member_signature_page(request: Request, doc_id: int, member_id: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login?'+urlencode({'next':_execution_member_signature_url(doc_id,member_id)}),303)
    with SessionLocal() as db:
        doc,data,member=_execution_member_document(db,doc_id,member_id)
        _require_execution_member_signer(db,member,user)
        if doc.status!='Finalizada': raise HTTPException(409,'Esta APR não está disponível para inclusão de integrantes.')
        if doc.id!=doc_id: return RedirectResponse(_execution_member_signature_url(doc.id,member_id),303)
        db.expunge(doc)
    return templates.TemplateResponse(request,'apr_execution_member_signature.html',context(
        request,doc=doc,data=data,member=member,already_signed=bool(clean(member.get('signature_image')))))


@app.post('/apr/{doc_id}/integrantes/{member_id}/assinar')
async def apr_execution_member_signature_submit(request: Request, doc_id: int, member_id: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login?'+urlencode({'next':_execution_member_signature_url(doc_id,member_id)}),303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    sig=''
    committed=False
    push_ids=[]
    try:
        with _CODE_LOCK, SessionLocal.begin() as db:
            if engine.dialect.name=='postgresql':
                db.execute(text('SELECT pg_advisory_xact_lock(hashtext(:lock_key))'),{'lock_key':f'safetyplus-code-apr-{now().year}'})
            target,data,member=_execution_member_document(db,doc_id,member_id,lock=True)
            _require_execution_member_signer(db,member,user)
            if target.status!='Finalizada': raise HTTPException(409,'Esta APR não está disponível para inclusão de integrantes.')
            if clean(member.get('signature_image')):
                flash(request,'Sua assinatura já foi registrada.','info')
                return RedirectResponse(_execution_member_signature_url(target.id,member_id),303)
            sig=save_signature(form.get('signature'),'',f'{target.code}_execution_member_{member_id}')
            if not sig:
                flash(request,'Faça sua assinatura antes de confirmar.','error')
                return RedirectResponse(_execution_member_signature_url(target.id,member_id),303)
            signed_at=now()
            member.update({'signature_image':sig,'signature_status':'Assinado',
                'signed_at':signed_at.strftime('%d/%m/%Y %H:%M'),'signed_by_user_id':str(user.id),
                'signed_by_name':user.full_name or user.username,'signature_capture_mode':'Conta do próprio integrante'})
            old_code=doc_reference_code(target)
            new_data=json.loads(json.dumps(data,ensure_ascii=False))
            for key in ('code','_document_id','replaced_by_apr_id','replaced_by_apr_code','replaced_at'):
                new_data.pop(key,None)
            new_data['execution_member_requests']=[m for m in (data.get('execution_member_requests') or []) if clean(m.get('id'))!=member_id]
            new_data['execution_members']=list(data.get('execution_members') or [])+[member]
            new_data['previous_versions']=list(data.get('previous_versions') or [])+[{
                'id':str(target.id),'code':old_code,'replaced_at':member['signed_at'],'added_member':member['worker']}]
            new_data['replaces_apr_id']=str(target.id); new_data['replaces_apr_code']=old_code
            new_data['code']=_next_code_in_db(db,'apr'); new_data['status']='Finalizada'
            new_doc=Document(code=new_data['code'],kind='apr',title=target.title,status='Finalizada',cluster=target.cluster,
                site=target.site,activity=target.activity,data_json=json.dumps(new_data,ensure_ascii=False),
                created_by=target.created_by,created_at=signed_at,updated_at=signed_at,finalized_at=signed_at)
            db.add(new_doc); db.flush()
            new_code=doc_reference_code(new_doc)
            old_data=dict(data)
            old_data.update({'replaced_by_apr_id':str(new_doc.id),'replaced_by_apr_code':new_code,'replaced_at':member['signed_at']})
            target.data_json=json.dumps(old_data,ensure_ascii=False); target.status='Substituída'; target.updated_at=signed_at
            linked_ids=set(_linked_history_ids(data))
            linked_ids.update(int(raw) for raw in (data.get('linked_permit_ids') or {}).values() if str(raw or '').isdigit())
            for pid in linked_ids:
                pt=db.get(Document,pid)
                if not pt or pt.kind not in APR_CRITICAL_KIND_PERMIT: continue
                pd=doc_data(pt)
                if clean(pd.get('linked_apr_id'))!=str(target.id): continue
                pd['linked_apr_id']=str(new_doc.id); pd['linked_apr_code']=new_code
                pt.data_json=json.dumps(pd,ensure_ascii=False); pt.updated_at=signed_at
            notes=db.query(Notification).filter(Notification.document_id==target.id,Notification.kind=='apr_execution_member_signature').all()
            for note in notes:
                note.document_id=new_doc.id
                if str(note.id)==str(member.get('notification_id')):
                    note.read=True; note.read_at=signed_at
            for recipient in {target.created_by,int(member['added_by_user_id'])}:
                account=db.get(User,recipient)
                if account and account.active:
                    notice=_add_notification(db,recipient_user_id=recipient,document_id=new_doc.id,kind='apr_creator_signature',
                        message=f'{member["worker"]} assinou a inclusão. Nova APR {new_code} criada; a versão anterior foi preservada.')
                    if notice: push_ids.append(notice.id)
            db.flush(); db.expunge(new_doc)
        committed=True
    except Exception:
        if sig and not committed: _remove_storage_file(sig)
        raise
    _queue_push_notification_ids(push_ids)
    try:
        finalize_pdf(new_doc,doc_data(new_doc))
    except Exception as exc:
        audit(user.id,'erro_incluir_membro_apr_pdf',f'{new_doc.code}: {exc}')
        flash(request,'Assinatura registrada e integrante incluído. O PDF será reconstruído ao abrir o documento.','info')
    else:
        flash(request,'Sua assinatura foi registrada e você foi incluído na nova versão da APR.','success')
    audit(user.id,'incluir_membro_apr',f'{old_code} -> {new_code} | {member["worker"]} | assinado_por={user.id}')
    return RedirectResponse(_execution_member_signature_url(new_doc.id,member_id),303)


@app.get('/apr/modelos',response_class=HTMLResponse)
def apr_models(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    with SessionLocal() as db:
        rows=db.query(Document).filter(Document.kind=='apr_template',Document.status=='Modelo').order_by(desc(Document.updated_at)).all()
        creators={}
        for row in rows:
            creator=db.get(User,row.created_by)
            creators[row.id]=(creator.full_name or creator.username) if creator else ''
            db.expunge(row)
    models=[]
    for row in rows:
        models.append({'doc':row,'data':doc_data(row),'creator':creators.get(row.id,'')})
    return templates.TemplateResponse(request,'apr_models.html',context(request,models=models))


@app.get('/apr/{doc_id}/duplicar',response_class=HTMLResponse)
def apr_duplicate_confirm(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr' or not user_can_access_document(user,doc): raise HTTPException(403)
    return templates.TemplateResponse(request,'apr_duplicate_confirm.html',context(request,doc=doc,data=apr_view(doc_data(doc))))


@app.post('/apr/{doc_id}/duplicar')
async def apr_duplicate_submit(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr' or not user_can_access_document(user,doc): raise HTTPException(403)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    copy_team=clean(form.get('copy_team')).lower() in {'1','true','sim','yes','on'}
    data=_apr_clone_data(doc_data(doc),source_doc=doc,copy_team=copy_team)
    saved=save_doc(None,'apr',data,user,'Rascunho')
    audit(user.id,'duplicar_apr_como_nova',f'{doc_reference_code(doc)} -> {saved.code} | copiar_equipe={copy_team}')
    flash(request,f'Nova APR criada a partir de {doc_reference_code(doc)}. Preencha o checklist de 24 itens e revise os campos antes de solicitar assinaturas.','success')
    return RedirectResponse(f'/apr/{saved.id}/edit',303)


@app.get('/apr/{doc_id}/salvar-modelo',response_class=HTMLResponse)
def apr_save_template_form(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr' or not user_can_access_document(user,doc): raise HTTPException(403)
    data=doc_data(doc)
    default_name=clean(data.get('activity')) or f'Modelo {doc_reference_code(doc)}'
    return templates.TemplateResponse(request,'apr_save_template.html',context(request,doc=doc,data=apr_view(data),default_name=default_name))


@app.post('/apr/{doc_id}/salvar-modelo')
async def apr_save_template_submit(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr' or not user_can_access_document(user,doc): raise HTTPException(403)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    name=clean(form.get('template_name'))
    if not name:
        flash(request,'Informe um nome para o modelo.','error')
        return RedirectResponse(f'/apr/{doc.id}/salvar-modelo',303)
    model=_save_apr_template_record(doc,doc_data(doc),user,name)
    audit(user.id,'salvar_modelo_apr',f'{doc_reference_code(doc)} -> modelo_id={model.id} nome={name}')
    flash(request,f'Modelo “{name}” salvo e disponibilizado para a equipe.','success')
    return RedirectResponse('/apr/modelos',303)


@app.post('/apr/modelos/{template_id}/usar')
async def apr_use_template(request: Request, template_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    model=get_document(template_id)
    if model.kind!='apr_template' or model.status!='Modelo': raise HTTPException(404)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    source=doc_data(model)
    data=_apr_clone_data(source,template_doc=model,copy_team=False)
    if user.role==ROLE_ADMIN and clean(data.get('cluster')) and not admin_scope_allows_location(user,data.get('cluster'),data.get('site','')):
        data['cluster']=''; data['site']=''
        flash(request,'O modelo foi carregado, mas o local foi limpo porque não pertence ao seu escopo. Selecione um Cluster/Site permitido.','info')
    try:
        saved=save_doc(None,'apr',data,user,'Rascunho')
    except Exception as exc:
        audit(user.id,'erro_usar_modelo_apr',f'modelo_id={model.id}: {exc}')
        flash(request,f'Não foi possível usar o modelo: {exc}','error')
        return RedirectResponse('/apr/modelos',303)
    audit(user.id,'usar_modelo_apr',f'modelo_id={model.id} -> {saved.code}')
    flash(request,'APR criada a partir do modelo. Revise a análise e responda novamente o checklist antes de solicitar assinaturas.','success')
    return RedirectResponse(f'/apr/{saved.id}/edit',303)


@app.post('/apr/modelos/{template_id}/excluir')
async def apr_delete_template(request: Request, template_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        model=db.get(Document,template_id)
        if not model or model.kind!='apr_template': raise HTTPException(404)
        if not is_super_admin(user) and model.created_by!=user.id:
            raise HTTPException(403,'Somente quem criou o modelo ou um administrador pode excluí-lo.')
        name=clean(doc_data(model).get('template_name')) or model.activity or 'Modelo'
        db.delete(model); db.commit()
    audit(user.id,'excluir_modelo_apr',f'modelo_id={template_id} nome={name}')
    flash(request,f'Modelo “{name}” excluído.','success')
    return RedirectResponse('/apr/modelos',303)


@app.get('/apr/new',response_class=HTMLResponse)
def apr_new(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    # Rota crítica: não permite que navegador/proxy reutilize uma tela vazia antiga.
    data=apr_view(prefill_location(user,apr_defaults(),combined_key='cluster',options=combined_clusters_for_user(user)))
    response=templates.TemplateResponse(
        request,'apr_form.html',
        context(request,data=data,doc=None,clusters=combined_clusters_for_user(user),checklist_items=CHECKLIST,
                hazard_options=HAZARD_OPTIONS,risk_options=RISK_OPTIONS,risk_catalog=RISK_CATALOG,
                critical_permits=APR_CRITICAL_PERMITS,linked_permit_states=linked_permit_states(data),
                linked_permits_pending=[],admins=available_approvers_for_creator(user),apr_readonly=False,approval_editable=False,
                assigned_admin=None,approval_mode=False,signature_phase=False,signature_complete=False,
                signature_pending_count=0,completion_issues=[]),
    )
    response.headers['Cache-Control']='no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma']='no-cache'
    return response

@app.get('/apr/{doc_id}/aprovar',response_class=HTMLResponse)
def apr_approval_readonly_page(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if doc.status!='Aguardando aprovação':
        if doc.status=='Finalizada' and doc.pdf_path:
            return RedirectResponse(f'/document/{doc.id}/pdf',303)
        return RedirectResponse(f'/apr/{doc.id}/edit',303)
    if not is_admin_user(user):
        raise HTTPException(403,'Somente o líder ou responsável selecionado pode aprovar esta APR.')
    if not user_can_access_document(user,doc):
        raise HTTPException(403,'Esta APR não pertence ao seu Cluster/Site de responsabilidade.')
    raw=doc_data(doc)
    allowed=_approver_ids_for_data(raw)
    if allowed and user.id not in allowed and not can_approve_any(user):
        raise HTTPException(403,'Esta APR foi direcionada a outro líder ou responsável pela atividade.')
    mark_approval_notification_read(user.id,doc.id)
    data=apr_view(raw)
    linked_states=linked_permit_states(data)
    linked_pending=linked_permits_incomplete(data)
    approval_start=local_today()
    approval_end=approval_start+timedelta(days=6)
    signed,total=_participant_signature_counts(data)
    return templates.TemplateResponse(
        request,'apr_approval_readonly.html',
        context(
            request,doc=doc,data=data,checklist_items=CHECKLIST,
            critical_permits=APR_CRITICAL_PERMITS,linked_permit_states=linked_states,
            linked_permits_pending=linked_pending,participant_signed_count=signed,participant_total=total,
            approval_start=approval_start.strftime('%d/%m/%Y'),
            approval_end=approval_end.strftime('%d/%m/%Y'),
            admins=active_admins(data.get('cluster'),data.get('site')),
        )
    )


@app.post('/apr/{doc_id}/alterar-aprovador')
async def apr_change_approver(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if doc.status!='Aguardando aprovação':
        flash(request,'A alteração do responsável só está disponível enquanto a APR aguarda aprovação.','error')
        return RedirectResponse(f'/apr/{doc.id}/edit',303)
    if not is_admin_user(user):
        raise HTTPException(403,'Somente um líder ou administrador responsável por esta aprovação pode transferi-la.')
    data=doc_data(doc)
    assigned_ids=_approver_ids_for_data(data)
    if assigned_ids and user.id not in assigned_ids and not can_approve_any(user):
        raise HTTPException(403,'Esta APR está direcionada a outro líder ou responsável.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: new_id=int(clean(form.get('approver_user_id')) or 0)
    except Exception: new_id=0
    if not new_id:
        flash(request,'Selecione o novo líder ou responsável.','error')
        return RedirectResponse(f'/apr/{doc.id}/aprovar',303)
    with SessionLocal() as db:
        new_admin=db.get(User,new_id)
        if not new_admin or not new_admin.active or not is_admin_user(new_admin):
            flash(request,'O administrador selecionado não está disponível.','error')
            return RedirectResponse(f'/apr/{doc.id}/aprovar',303)
        if not is_super_admin(new_admin) and not admin_scope_allows_location(new_admin,data.get('cluster'),data.get('site')):
            flash(request,'O administrador selecionado não é responsável pelo Cluster/Site desta APR.','error')
            return RedirectResponse(f'/apr/{doc.id}/aprovar',303)
        db.expunge(new_admin)

    primary=clean(data.get('approver_user_id'))
    extras=[clean(v) for v in (data.get('approver_extra_user_ids') or []) if clean(v)]
    uid=str(user.id); nid=str(new_id)
    if primary==uid or not primary:
        data['approver_user_id']=nid
        data['approver_name']=new_admin.full_name or new_admin.username
    elif uid in extras:
        extras=[nid if x==uid else x for x in extras]
    else:
        # Compatibilidade com APR antiga sem lista consistente: transfere o responsável principal.
        data['approver_user_id']=nid
        data['approver_name']=new_admin.full_name or new_admin.username
    # Remove duplicidade do novo responsável nas aprovações adicionais.
    extras=[x for i,x in enumerate(extras) if x and x!=clean(data.get('approver_user_id')) and x not in extras[:i]]
    data['approver_extra_user_ids']=extras
    extra_names=[]
    if extras:
        with SessionLocal() as db:
            for raw in extras:
                try: aid=int(raw)
                except Exception: continue
                a=db.get(User,aid)
                if a: extra_names.append(a.full_name or a.username)
    data['approver_extra_names']=extra_names
    saved=save_doc(doc,'apr',data,user,'Aguardando aprovação')
    approvers=_approvers_for_data(data)
    notify_apr_approval(saved,approvers,user)
    audit(user.id,'alterar_aprovador_apr',f'{saved.code} -> {new_admin.full_name or new_admin.username}')
    flash(request,f'Responsável pela aprovação alterado para {new_admin.full_name or new_admin.username}. O novo responsável foi notificado.','success')
    if new_id==user.id:
        return RedirectResponse(f'/apr/{saved.id}/aprovar',303)
    return RedirectResponse('/dashboard',303)

@app.get('/apr/{doc_id}/edit',response_class=HTMLResponse)
def apr_edit(request: Request,doc_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para acessar esta APR.')
    admin_mode=False
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    data=doc_data(doc); data['status']=doc.status
    assigned_admin=_approver_for_data(data)
    waiting=bool(doc.status=='Aguardando aprovação')
    signature_phase=bool(doc.status=='Pendente assinatura')
    allowed_approver_ids=_approver_ids_for_data(data)
    # Compatibilidade com APRs antigas: se não houver responsável gravado,
    # qualquer Administrador pode revisar/aprovar/reprovar. Nas APRs novas,
    # continua restrito ao líder/responsável selecionado.
    approval_editable=bool(waiting and is_admin_user(user) and (not allowed_approver_ids or user.id in allowed_approver_ids or can_approve_any(user)))
    apr_readonly=bool(waiting or signature_phase)
    if waiting and approval_editable: mark_approval_notification_read(user.id,doc.id)
    view_data=apr_view(data)
    signed,total=_participant_signature_counts(view_data)
    signature_complete=_participant_signatures_complete(view_data)
    pending_linked=linked_permits_incomplete(view_data)
    completion_issues=apr_completion_issues(view_data) if view_data.get('_show_completion_issues') and not (waiting or signature_phase) else []
    return templates.TemplateResponse(request,'apr_form.html',context(request,data=view_data,doc=doc,clusters=combined_clusters_for_user(user),checklist_items=CHECKLIST,hazard_options=HAZARD_OPTIONS,risk_options=RISK_OPTIONS,risk_catalog=RISK_CATALOG,critical_permits=APR_CRITICAL_PERMITS,linked_permit_states=linked_permit_states(view_data),linked_permits_pending=pending_linked,admins=active_admins(view_data.get('cluster'),view_data.get('site')),apr_readonly=apr_readonly,approval_editable=approval_editable,assigned_admin=assigned_admin,approval_mode=waiting,signature_phase=signature_phase,signature_complete=signature_complete,signature_pending_count=max(0,total-signed),completion_issues=completion_issues,admin_edit=admin_mode))

async def parse_apr(request: Request,old:dict):
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    # A data da APR não é aceita do navegador: fica travada no servidor.
    # Em APR nova usa a data local do dia; nas existentes preserva a data original.
    fixed_apr_date=clean(old.get('apr_date')) or local_today().strftime('%d/%m/%Y')
    d={'code':old.get('code') or next_code('apr'),'cluster':clean(form.get('cluster')),'severity':clean(form.get('severity')),'activity':clean(form.get('activity')),'apr_date':fixed_apr_date,'apr_time':clean(form.get('apr_time')),'leader_phone':clean(form.get('leader_phone')),'sst_phone':clean(form.get('sst_phone')),'radio_channel':clean(form.get('radio_channel'))}
    d['critical_activity']='SIM' if clean(form.get('critical_activity')).upper()=='SIM' else 'NÃO'
    selected_permits=[clean(v) for v in form.getlist('critical_permits')]
    d['critical_permits']=[p for p in APR_CRITICAL_PERMITS if p in selected_permits] if d['critical_activity']=='SIM' else []
    d['linked_permit_ids']=dict(old.get('linked_permit_ids') or {})
    d['linked_permit_history']=list(old.get('linked_permit_history') or [])
    try: step_count=int(clean(form.get('step_count')) or '1')
    except ValueError: step_count=1
    step_count=max(1,min(step_count,APR_MAX_STEPS))
    d['steps']=[]
    for i in range(step_count):
        hazards=[]
        for raw in form.getlist(f'step_{i}_hazards'):
            value=clean(raw)
            if value and value in HAZARD_OPTIONS and value not in hazards:
                hazards.append(value)
        hazard_custom=clean(form.get(f'step_{i}_hazard_custom'))
        if hazard_custom and hazard_custom not in hazards:
            hazards.append(hazard_custom)
        risks=[]
        for raw in form.getlist(f'step_{i}_risks'):
            value=clean(raw)
            if value and value in RISK_CATALOG and value not in risks:
                risks.append(value)
        risk_custom=clean(form.get(f'step_{i}_risk_custom'))
        if risk_custom and risk_custom not in risks:
            risks.append(risk_custom)
        d['steps'].append({
            'stage':clean(form.get(f'step_{i}_stage')),
            'hazards':hazards,
            'hazard':'\n'.join(hazards),
            'risks':risks,
            'risk':'\n'.join(risks),
            'severity':clean(form.get(f'step_{i}_severity')),
            'control':clean(form.get(f'step_{i}_control')),
        })
    # Severidade por etapa: C (verde), B (amarelo), A (vermelho).
    # O valor geral é sempre derivado das etapas para não depender do navegador.
    for _step in d['steps']:
        _step['severity']=normalize_apr_severity(_step.get('severity'))
    _sev_rank={'C':1,'B':2,'A':3}
    d['severity']=max((s.get('severity','') for s in d['steps']), key=lambda v:_sev_rank.get(v,0), default='')
    d['checklist']=[clean(form.get(f'check_{i}')) for i in range(24)]
    # NÃO no checklist não bloqueia: exige aviso de segurança + justificativa do motivo.
    _just=clean(form.get('checklist_no_justification'))[:1500]
    if 'NÃO' in d['checklist'] and _just:
        d['checklist_no_justification']=_just
        if clean(old.get('checklist_no_justification'))==_just and old.get('checklist_no_by'):
            d['checklist_no_by']=old['checklist_no_by']; d['checklist_no_at']=old.get('checklist_no_at','')
        else:
            _u=current_user(request)
            d['checklist_no_by']=(_u.full_name or _u.username) if _u else ''; d['checklist_no_at']=now().strftime('%d/%m/%Y %H:%M')
    else:
        d['checklist_no_justification']=''; d['checklist_no_by']=''; d['checklist_no_at']=''
    # Aprovação é protegida: no rascunho o usuário não pode preencher ou rubricar essa área.
    d['approvals']=old.get('approvals',[]) or [{} for _ in range(5)]
    oldw=old.get('workers',[]) or []; d['workers']=[]
    try: worker_count=int(clean(form.get('worker_count')) or '1')
    except ValueError: worker_count=1
    worker_count=max(1,min(worker_count,24))
    for i in range(worker_count):
        prev=oldw[i] if i<len(oldw) else {}
        participant_id=clean(form.get(f'worker_{i}_participant_id'))
        participant_user_id=clean(form.get(f'worker_{i}_user_id'))
        worker={
            'participant_id':participant_id,
            'participant_user_id':participant_user_id,
            'cpf':cpf_digits(form.get(f'worker_{i}_cpf')),
            'company':clean(form.get(f'worker_{i}_company')),
            'worker':clean(form.get(f'worker_{i}_worker')),
            'role':clean(form.get(f'worker_{i}_role')),
            'date':clean(prev.get('date')),
            'signature':clean(prev.get('signature')),
            'signature_image':clean(prev.get('signature_image')),
            'signature_status':clean(prev.get('signature_status')),
            'signed_at':clean(prev.get('signed_at')),
            'signed_by_user_id':clean(prev.get('signed_by_user_id')),
            'signed_by_name':clean(prev.get('signed_by_name')),
        }
        d['workers'].append(worker)
    # Mantém metadados do fluxo e permite escolher o administrador enquanto ainda é rascunho.
    for key in ('participant_signature_status','participant_signatures_requested_at','participant_signatures_requested_by_id','participant_signatures_requested_by_name','approval_requested_at','submitted_by_id','submitted_by_name','approved_by_id','approved_by_name','approved_at','rejection_status','last_rejected_at','last_rejected_by_id','last_rejected_by_name','last_rejection_reason','created_from_apr_id','created_from_apr_code','created_from_template_id','created_from_template_name','model_review_required','model_source_label'):
        d[key]=old.get(key,'')
    # O seletor oculto é a fonte oficial. Digitar um nome sem escolhê-lo na lista
    # não mantém silenciosamente o aprovador anterior; remover aprovadores adicionais
    # também passa a ser respeitado no salvamento.
    d['approver_user_id']=clean(form.get('approver_user_id'))
    extra_ids=[]
    for raw in form.getlist('approver_extra_user_ids'):
        value=clean(raw)
        if value and value!=d['approver_user_id'] and value not in extra_ids:
            extra_ids.append(value)
    d['approver_extra_user_ids']=extra_ids
    d['approver_name']=clean(old.get('approver_name'))
    prev_names=old.get('approver_extra_names') or []
    if isinstance(prev_names,str): prev_names=[prev_names]
    d['approver_extra_names']=[clean(v) for v in prev_names if clean(v)]
    return d,clean(form.get('action')) or 'draft'

def validate_apr_dates(d: dict, old: dict|None=None):
    today=local_today(); old=old or {}
    fields=[('Data da APR',d.get('apr_date'),old.get('apr_date'))]
    old_approvals=old.get('approvals',[]) or []
    for i,a in enumerate(d.get('approvals',[]),1):
        prev=old_approvals[i-1] if i-1<len(old_approvals) else {}
        fields += [(f'Aprovação {i} - Início',a.get('start'),prev.get('start')),(f'Aprovação {i} - Fim',a.get('end'),prev.get('end'))]
    old_workers=old.get('workers',[]) or []
    for i,w in enumerate(d.get('workers',[]),1):
        prev=old_workers[i-1] if i-1<len(old_workers) else {}
        fields.append((f'Equipe {i} - Data',w.get('date'),prev.get('date')))
    for label,raw,previous in fields:
        if not clean(raw): continue
        parsed=parse_date_br(raw)
        unchanged=False
        if clean(previous):
            try: unchanged=parse_date_br(previous)==parsed
            except Exception: unchanged=False
        if parsed<today and not unchanged:
            raise ValueError(f'{label}: data retroativa não permitida ({parsed.strftime("%d/%m/%Y")}).')
    if clean(d.get('apr_date')):
        apr_date=parse_date_br(d.get('apr_date'))
        old_apr=clean(old.get('apr_date'))
        unchanged_apr=False
        if old_apr:
            try: unchanged_apr=parse_date_br(old_apr)==apr_date
            except Exception: unchanged_apr=False
        max_date=today+timedelta(days=6)
        if apr_date>max_date and not unchanged_apr:
            raise ValueError(f'Data da APR: selecione no máximo até {max_date.strftime("%d/%m/%Y")} (7 dias corridos contando hoje).')

def apr_no_unacknowledged(d: dict) -> list[int]:
    """Itens NÃO do checklist da APR sem justificativa registrada."""
    if clean(d.get('checklist_no_justification')): return []
    return [i+1 for i,a in enumerate(d.get('checklist') or []) if clean(a).upper()=='NÃO']


def validate_apr_ready_for_approval(d: dict):
    if not d.get('activity') or not d.get('cluster'):
        raise ValueError('Informe Cluster/Site e Atividade.')
    if d.get('critical_activity')=='SIM' and not d.get('critical_permits'):
        raise ValueError('A atividade foi marcada como crítica. Selecione pelo menos uma Permissão de Trabalho aplicável.')
    invalid=[i+1 for i,a in enumerate(d.get('checklist',[])) if not a]
    if invalid:
        raise ValueError('Não é possível enviar para aprovação. Itens do checklist sem seleção: '+', '.join(map(str,invalid)))
    no_items=apr_no_unacknowledged(d)
    if no_items:
        raise ValueError('Há resposta NÃO no checklist (itens '+', '.join(map(str,no_items))+'). Leia o aviso de segurança e justifique o motivo do NÃO na caixa de justificativa para prosseguir.')


def apr_completion_issues(d: dict) -> list[dict]:
    """Retorna uma lista amigável do que ainda falta para solicitar assinaturas."""
    issues=[]
    if not clean(d.get('cluster')):
        issues.append({'section':'Dados gerais','message':'Selecione o Cluster / Site.'})
    if not clean(d.get('activity')):
        issues.append({'section':'Dados gerais','message':'Informe a atividade da APR.'})
    if clean(d.get('critical_activity')).upper()=='SIM' and not (d.get('critical_permits') or []):
        issues.append({'section':'Atividade crítica','message':'Selecione pelo menos uma Permissão de Trabalho aplicável.'})

    for i,step in enumerate(d.get('steps') or [],1):
        filled=bool(clean(step.get('stage')) or clean(step.get('hazard')) or clean(step.get('risk')) or clean(step.get('control')))
        if filled and not normalize_apr_severity(step.get('severity')):
            issues.append({'section':'Etapas · Perigos · Riscos','message':f'Etapa {i:02d}: selecione obrigatoriamente a severidade A, B ou C.'})

    checklist=list(d.get('checklist') or [])
    checklist=(checklist+['']*len(CHECKLIST))[:len(CHECKLIST)]
    for i,(answer,question) in enumerate(zip(checklist,CHECKLIST),1):
        answer=clean(answer)
        if not answer:
            issues.append({'section':'Checklist','check_index':i-1,'message':f'Checklist {i:02d}: falta selecionar uma resposta — {question}'})
        elif answer=='NÃO' and not clean(d.get('checklist_no_justification')):
            issues.append({'section':'Checklist','check_index':i-1,'message':f'Checklist {i:02d}: está marcado como NÃO — justifique o NÃO na caixa de justificativa — {question}'})

    try:
        _selected_approvers_for_submission(d)
    except Exception as e:
        issues.append({'section':'Aprovação','message':str(e)})
    return issues

def _selected_approvers_for_submission(d: dict) -> list[User]:
    try: approver_id=int(d.get('approver_user_id') or 0)
    except Exception: approver_id=0
    if not approver_id:
        raise ValueError('Selecione o líder ou responsável pela atividade para aprovação.')
    raw_ids=[approver_id]
    for raw in d.get('approver_extra_user_ids') or []:
        try: extra_id=int(raw or 0)
        except Exception: extra_id=0
        if extra_id and extra_id not in raw_ids: raw_ids.append(extra_id)
    approvers=[]
    with SessionLocal() as db:
        for aid in raw_ids:
            approver=db.get(User,aid)
            if not approver or not approver.active or not is_admin_user(approver):
                raise ValueError('Um dos líderes ou responsáveis selecionados não está disponível para aprovação.')
            if not is_super_admin(approver) and not admin_scope_allows_location(approver,d.get('cluster'),d.get('site')):
                raise ValueError('O administrador selecionado não é responsável pelo Cluster/Site desta APR.')
            db.expunge(approver); approvers.append(approver)
    return approvers


def _submit_apr_for_approval(request: Request, user: User, doc: Document, d: dict):
    target=f'/apr/{doc.id}/edit'
    if user.id!=doc.created_by and not is_admin_user(user):
        raise HTTPException(403,'Somente o responsável pela APR ou um administrador pode enviá-la para aprovação.')
    try:
        validate_apr_ready_for_approval(d)
        if _participant_signature_required(d) and not _participant_signatures_complete(d):
            signed,total=_participant_signature_counts(d)
            raise ValueError(f'Não é possível enviar para aprovação. Assinaturas dos integrantes: {signed}/{total} concluídas.')
        if not _participant_signature_required(d):
            raise ValueError('Primeiro solicite e conclua as assinaturas de todos os integrantes.')
        approvers=_selected_approvers_for_submission(d)
        d['linked_permit_history']=list(d.get('linked_permit_history') or [])
        primary_approver=approvers[0]; extra_approvers=approvers[1:]
        d['approver_user_id']=str(primary_approver.id)
        d['approver_name']=primary_approver.full_name or primary_approver.username
        d['approver_extra_user_ids']=[str(a.id) for a in extra_approvers]
        d['approver_extra_names']=[a.full_name or a.username for a in extra_approvers]
        d['approval_requested_at']=now().strftime('%d/%m/%Y %H:%M')
        d['submitted_by_id']=str(user.id); d['submitted_by_name']=user.full_name or user.username
        d['rejection_status']=''
        d['status']='Aguardando aprovação'
        saved=save_doc(doc,'apr',d,user,'Aguardando aprovação')
        _clear_apr_signature_notifications(saved.id)
        notify_apr_approval(saved,approvers,user)
        approver_label=', '.join([d['approver_name'], *d.get('approver_extra_names',[])]) if d.get('approver_extra_names') else d['approver_name']
        audit(user.id,'enviar_apr_aprovacao',f'{saved.code} -> {approver_label}')
        if d.get('critical_activity')=='SIM' and d.get('critical_permits'):
            flash(request,f'{doc_reference_code(saved)} enviada para aprovação com as PTs selecionadas e as assinaturas da equipe concluídas. Após a aprovação, o PDF final será gerado como dossiê APR + PTs.','success')
        else:
            flash(request,f'{doc_reference_code(saved)} enviada para aprovação de {approver_label}. Todas as assinaturas dos integrantes estão concluídas.','success')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)
    except Exception as e:
        flash(request,str(e),'error'); return RedirectResponse(target,303)


def _cancel_apr_signature_collection(request: Request, user: User, doc: Document, d: dict):
    if user.id!=doc.created_by and not is_admin_user(user):
        raise HTTPException(403,'Somente o responsável pela APR ou um administrador pode cancelar a coleta de assinaturas.')
    workers=[]
    for w in d.get('workers') or []:
        item=dict(w)
        for key in ('date','signature','signature_image','signature_status','signed_at','signed_by_user_id','signed_by_name'):
            item[key]=''
        workers.append(item)
    d['workers']=workers
    d['participant_signature_status']='Não solicitada'
    d['participant_signatures_requested_at']=''
    d['participant_signatures_requested_by_id']=''
    d['participant_signatures_requested_by_name']=''
    saved=save_doc(doc,'apr',d,user,'Rascunho')
    _clear_apr_signature_notifications(saved.id)
    audit(user.id,'cancelar_assinaturas_apr',saved.code)
    flash(request,'Coleta de assinaturas cancelada. A APR voltou para edição e deverá ser assinada novamente após as alterações.','success')
    return RedirectResponse(f'/apr/{saved.id}/edit',303)

@app.post('/apr/save')
async def apr_create_save(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    d,action=await parse_apr(request,apr_defaults()); return process_apr(request,user,None,d,action)

@app.post('/apr/{doc_id}/save')
async def apr_update_save(request: Request,doc_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar esta APR.')
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    if doc.status=='Aguardando aprovação':
        raise HTTPException(409,'APR enviada para aprovação não pode mais ser alterada pelo formulário normal.')
    if doc.status=='Pendente assinatura':
        form=await request.form(); verify_csrf(request,form.get('csrf_token'))
        action=clean(form.get('action'))
        data=doc_data(doc)
        if action=='submit_approval': return _submit_apr_for_approval(request,user,doc,data)
        if action=='cancel_signatures': return _cancel_apr_signature_collection(request,user,doc,data)
        raise HTTPException(409,'APR está bloqueada enquanto aguarda as assinaturas dos integrantes.')
    d,action=await parse_apr(request,doc_data(doc)); return process_apr(request,user,doc,d,action)

def apr_validation_fields(d: dict) -> list[str]:
    fields=[]
    if not clean(d.get('cluster')): fields.append('cluster')
    if not clean(d.get('activity')): fields.append('activity')
    if clean(d.get('critical_activity')).upper()=='SIM' and not (d.get('critical_permits') or []): fields.append('critical_permits')
    for i,step in enumerate(d.get('steps') or []):
        filled=bool(clean(step.get('stage')) or clean(step.get('hazard')) or clean(step.get('risk')) or clean(step.get('control')))
        if filled and not normalize_apr_severity(step.get('severity')):
            fields.append(f'step_{i}_severity')
    checklist=list(d.get('checklist') or [])
    for i,answer in enumerate(checklist):
        if clean(answer)=='' or (clean(answer)=='NÃO' and not clean(d.get('checklist_no_justification'))): fields.append(f'check_{i}')
    if not clean(d.get('approver_user_id')): fields.append('approver_user_id')
    return fields

def _begin_apr_signature_collection(request: Request, user: User, doc: Document, d: dict, *, redirect_to_signatures: bool=False):
    """Inicia a coleta única depois que APR e PTs vinculadas estiverem prontas."""
    if doc.status=='Pendente assinatura':
        destination=f'/apr/{doc.id}/assinar' if redirect_to_signatures else f'/apr/{doc.id}/edit'
        return RedirectResponse(destination,303)
    if doc.status!='Rascunho':
        flash(request,'A APR não está disponível para iniciar a coleta de assinaturas.','error')
        return RedirectResponse(f'/apr/{doc.id}/edit',303)
    try:
        issues=apr_completion_issues(d)
        if issues:
            raise ValueError(f'Falta finalizar {len(issues)} item(ns) da APR antes da coleta de assinaturas.')
        pending_permits=linked_permits_incomplete(d)
        if pending_permits:
            raise ValueError('Conclua primeiro as permissões selecionadas: '+', '.join(pending_permits)+'.')
        validate_apr_ready_for_approval(d)
        _selected_approvers_for_submission(d)
        d['workers']=_validate_apr_workers_for_signature(d) if any(any(clean(w.get(k)) for k in ('participant_id','cpf','worker','company')) for w in (d.get('workers') or [])) else []
        d.pop('_show_completion_issues',None)
        clear_validation_state(d)
        for w in d['workers']:
            for key in ('date','signature','signature_image','signature_status','signed_at','signed_by_user_id','signed_by_name'):
                w[key]=''
        d['participant_signature_status']='Pendente'
        d['participant_signatures_requested_at']=now().strftime('%d/%m/%Y %H:%M')
        d['participant_signatures_requested_by_id']=str(user.id)
        d['participant_signatures_requested_by_name']=user.full_name or user.username
        saved=save_doc(doc,'apr',d,user,'Pendente assinatura')
        _notify_apr_participant_signatures(saved,d,user)
        audit(user.id,'solicitar_assinaturas_apr',f'{saved.code} | integrantes={len(d["workers"])}')
        flash(request,f'{doc_reference_code(saved)}: PTs concluídas. Agora faça a coleta única das assinaturas; elas valerão para a APR e para todas as PTs vinculadas.','success')
        destination=f'/apr/{saved.id}/assinar' if redirect_to_signatures else f'/apr/{saved.id}/edit'
        return RedirectResponse(destination,303)
    except Exception as e:
        d['_show_completion_issues']=True
        saved=save_validation_state(doc,'apr',d,user,apr_validation_fields(d),'Rascunho')
        flash(request,f'{e} O que já foi preenchido foi mantido.','error')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)


def process_apr(request,user,doc,d,action):
    target=f'/apr/{doc.id}/edit' if doc else '/apr/new'
    old_data=doc_data(doc) if doc else {}
    try:
        validate_apr_dates(d,old_data)
    except Exception as e:
        saved=save_validation_state(doc,'apr',d,user,['apr_date'],'Rascunho')
        flash(request,str(e)+' O que já foi preenchido foi mantido.','error')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)

    # Proteção para navegador/cache antigo: se o formulário ainda enviar
    # request_signatures logo após selecionar PTs pendentes, tratamos a ação
    # como a próxima etapa das permissões em vez de mostrar um erro antes.
    if (action=='request_signatures' and clean(d.get('critical_activity')).upper()=='SIM'
            and (d.get('critical_permits') or []) and linked_permits_incomplete(d)):
        action='continue_permits'

    if action=='continue_permits':
        issues=apr_completion_issues(d)
        if issues:
            d['_show_completion_issues']=True
            saved=save_validation_state(doc,'apr',d,user,apr_validation_fields(d),'Rascunho')
            flash(request,f'Falta finalizar {len(issues)} item(ns) da APR antes de abrir as permissões. O preenchimento foi mantido.','error')
            return RedirectResponse(f'/apr/{saved.id}/edit',303)
        saved=save_doc(doc,'apr',d,user,'Rascunho')
        for permit_name in d.get('critical_permits') or []:
            ensure_linked_permit(saved,d,permit_name,user)
        saved=get_document(saved.id); d=doc_data(saved)
        next_url=_next_linked_permit_url(saved,d)
        if next_url:
            flash(request,'APR salva. Preencha agora as permissões selecionadas. A coleta de assinaturas aparecerá somente depois da última PT.','success')
            return RedirectResponse(next_url,303)
        return RedirectResponse(f'/apr/{saved.id}/edit',303)

    if action=='request_signatures':
        # Sem PT crítica, ou como recuperação após PTs já concluídas, inicia a mesma coleta única.
        saved=save_doc(doc,'apr',d,user,'Rascunho')
        return _begin_apr_signature_collection(request,user,saved,doc_data(saved),redirect_to_signatures=True)

    if action in {'draft',''}:
        d.pop('_show_completion_issues',None)
        clear_validation_state(d)
        saved=save_doc(doc,'apr',d,user,'Rascunho')
        audit(user.id,'salvar_rascunho',saved.code)
        flash(request,'APR salva como rascunho. Se houver atividade crítica, conclua primeiro as permissões selecionadas; depois colete as assinaturas.','success')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)

    if not d.get('activity') or not d.get('cluster'):
        fields=[]
        if not d.get('cluster'): fields.append('cluster')
        if not d.get('activity'): fields.append('activity')
        saved=save_validation_state(doc,'apr',d,user,fields,'Rascunho')
        flash(request,'Informe Cluster/Site e Atividade. O restante foi mantido.','error')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)
    if action.startswith('open_permit:'):
        saved=save_validation_state(doc,'apr',d,user,apr_validation_fields(d),'Rascunho')
        flash(request,'Conclua a APR e preencha primeiro as permissões selecionadas. A coleta única de assinaturas será liberada depois da última PT.','info')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)
    if action=='submit_approval':
        saved=save_validation_state(doc,'apr',d,user,apr_validation_fields(d),'Rascunho')
        flash(request,'Antes de enviar para aprovação, solicite e conclua as assinaturas de todos os integrantes. O preenchimento atual foi mantido.','error')
        return RedirectResponse(f'/apr/{saved.id}/edit',303)
    clear_validation_state(d)
    saved=save_doc(doc,'apr',d,user,'Rascunho')
    audit(user.id,'salvar_rascunho',saved.code)
    flash(request,'APR salva como rascunho. Se houver atividade crítica, conclua primeiro as permissões selecionadas; depois colete as assinaturas.','success')
    return RedirectResponse(f'/apr/{saved.id}/edit',303)

def _participant_lookup_payload(participant: Participant, company: Company, linked_user: User|None) -> dict:
    can_sign=bool(linked_user and linked_user.active)
    return {
        'found':True,
        'participant_id':participant.id,
        'user_id':participant.user_id or '',
        'cpf':cpf_format(participant.cpf),
        'full_name':participant.full_name,
        'job_title':participant.job_title or '',
        'company':company.name,
        'can_sign':can_sign,
        'message':'Participante localizado.' if can_sign else 'Participante localizado, mas ainda não possui usuário ativo vinculado para assinar.'
    }


def _apr_public_signature_token(doc_id: int) -> str:
    secret=APP_SECRET_VALUE.encode('utf-8')
    return hmac.new(secret,f'apr-public-signature:{int(doc_id)}'.encode('utf-8'),hashlib.sha256).hexdigest()[:40]

def _apr_public_signature_valid(doc_id: int, token: str) -> bool:
    return hmac.compare_digest(_apr_public_signature_token(doc_id),clean(token))

def _normalize_person_name(value: Any) -> str:
    text=clean_single_line(value).casefold()
    text=unicodedata.normalize('NFKD',text)
    return ' '.join(''.join(ch for ch in text if not unicodedata.combining(ch)).split())


@app.post('/api/apr/team-qr/start')
async def apr_team_qr_start(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    _apr_team_qr_cleanup()
    token=secrets.token_urlsafe(24)
    APR_TEAM_QR_SESSIONS[token]={'created_at':datetime.now(timezone.utc),'owner_user_id':user.id,'status':'waiting','participant':None}
    return {'ok':True,'token':token,'qr_url':f'/apr/equipe/qr/{token}.svg','mobile_url':f'/apr/equipe/qr/{token}'}

@app.get('/api/apr/team-qr/{token}/status')
def apr_team_qr_status(token: str, request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    _apr_team_qr_cleanup(); sess=APR_TEAM_QR_SESSIONS.get(token)
    if not sess or sess.get('owner_user_id')!=user.id: return {'ok':False,'status':'expired'}
    return {'ok':True,'status':sess.get('status','waiting'),'participant':sess.get('participant')}

@app.get('/apr/equipe/qr/{token}.svg')
def apr_team_qr_svg(token: str, request: Request):
    _apr_team_qr_cleanup(); sess=APR_TEAM_QR_SESSIONS.get(token)
    if not sess: raise HTTPException(404,'QR expirado.')
    target=str(request.base_url).rstrip('/')+f'/apr/equipe/qr/{token}'
    img=qrcode.make(target,image_factory=qrcode.image.svg.SvgPathImage)
    buf=io.BytesIO(); img.save(buf)
    return StreamingResponse(io.BytesIO(buf.getvalue()),media_type='image/svg+xml',headers={'Cache-Control':'no-store'})

@app.get('/apr/equipe/qr/{token}',response_class=HTMLResponse)
def apr_team_qr_mobile(token: str, request: Request):
    _apr_team_qr_cleanup(); sess=APR_TEAM_QR_SESSIONS.get(token)
    if not sess: return HTMLResponse('<h2>QR Code expirado.</h2><p>Solicite um novo QR na APR.</p>',410)
    return templates.TemplateResponse('apr_team_qr_mobile.html',{'request':request,'token':token,'done':sess.get('status')=='done','error':''})

@app.post('/apr/equipe/qr/{token}',response_class=HTMLResponse)
async def apr_team_qr_mobile_submit(token: str, request: Request):
    _apr_team_qr_cleanup(); sess=APR_TEAM_QR_SESSIONS.get(token)
    if not sess: return HTMLResponse('<h2>QR Code expirado.</h2><p>Solicite um novo QR na APR.</p>',410)
    form=await request.form(); raw_cpf=clean(form.get('cpf')); error=''
    cpf=cpf_digits(raw_cpf)
    if not cpf_is_valid(cpf): error='CPF inválido. Confira os 11 dígitos.'
    else:
        with SessionLocal() as db:
            row=(db.query(Participant,Company,User).join(Company,Participant.company_id==Company.id).outerjoin(User,Participant.user_id==User.id).filter(Participant.cpf==cpf,Participant.active==True,Company.active==True).first())
            if not row: error='CPF não encontrado no cadastro de participantes.'
            else:
                participant,company,linked_user=row
                sess['participant']=_participant_lookup_payload(participant,company,linked_user); sess['status']='done'
    return templates.TemplateResponse('apr_team_qr_mobile.html',{'request':request,'token':token,'done':sess.get('status')=='done','error':error})

@app.post('/api/participants/lookup')
async def participant_lookup(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Sessão expirada.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    raw_cpf=clean(form.get('cpf'))
    raw_name=clean_single_line(form.get('name'))

    with SessionLocal() as db:
        if raw_cpf:
            cpf=cpf_digits(raw_cpf)
            if not cpf_is_valid(cpf):
                return {'found':False,'message':'CPF inválido. Confira os 11 dígitos.'}
            row=(db.query(Participant,Company,User)
                 .join(Company,Participant.company_id==Company.id)
                 .outerjoin(User,Participant.user_id==User.id)
                 .filter(Participant.cpf==cpf,Participant.active==True)
                 .first())
            if not row:
                return {'found':False,'message':'CPF não encontrado no cadastro de participantes.'}
            participant,company,linked_user=row
            if not company.active:
                return {'found':False,'message':'A empresa deste participante está inativa.'}
            return _participant_lookup_payload(participant,company,linked_user)

        name_key=_normalize_person_name(raw_name)
        if len(name_key)<2:
            return {'found':False,'message':'Digite pelo menos 2 letras do nome para pesquisar.'}

        rows=(db.query(Participant,Company,User)
              .join(Company,Participant.company_id==Company.id)
              .outerjoin(User,Participant.user_id==User.id)
              .filter(Participant.active==True,Company.active==True)
              .order_by(Participant.full_name)
              .all())
        matches=[]
        for participant,company,linked_user in rows:
            full_key=_normalize_person_name(participant.full_name)
            if name_key in full_key:
                matches.append(_participant_lookup_payload(participant,company,linked_user))
            if len(matches)>=12:
                break
        if not matches:
            return {'found':False,'message':'Nome não encontrado no cadastro de participantes.'}
        exact=[m for m in matches if _normalize_person_name(m.get('full_name'))==name_key]
        if len(exact)==1:
            return exact[0]
        if len(matches)==1:
            return matches[0]
        return {
            'found':False,
            'multiple':True,
            'matches':matches,
            'message':f'{len(matches)} participantes encontrados. Selecione o nome correto.'
        }


@app.get('/apr/{doc_id}/assinar',response_class=HTMLResponse)
def apr_participant_signature_page(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind=apr assinatura')
        raise HTTPException(403,'Você não tem permissão para acessar esta APR.')
    data=doc_data(doc)
    collector_mode=bool(is_admin_user(user) or doc.created_by==user.id)
    entries=[]
    for i,w in enumerate(data.get('workers') or []):
        try: uid=int(w.get('participant_user_id') or 0)
        except Exception: uid=0
        if not collector_mode and uid!=user.id:
            continue
        item=dict(w)
        item['index']=i
        item['cpf_masked']=cpf_mask(w.get('cpf'))
        item['date_input']=date_input(w.get('date',''))
        item['participant_user_id']=uid or ''
        item['is_own']=bool(uid==user.id)
        item['can_capture_present']=False
        entries.append(item)
    if not entries and not collector_mode and doc.status=='Pendente assinatura':
        with SessionLocal() as db:
            participant=db.query(Participant).filter(Participant.user_id==user.id,Participant.active==True).first()
            company=db.get(Company,participant.company_id) if participant else None
        if participant and company and company.active:
            entries.append({
                'index':-1,'participant_id':str(participant.id),'participant_user_id':user.id,
                'cpf':participant.cpf,'cpf_masked':cpf_mask(participant.cpf),'company':company.name,
                'worker':participant.full_name,'role':participant.job_title or '', 'date':'','date_input':'',
                'signature_image':'','is_own':True,'can_capture_present':False,'self_enroll':True
            })
        else:
            flash(request,'Seu usuário precisa estar vinculado a um participante ativo para assinar esta APR.','error')
            return RedirectResponse('/',303)
    with SessionLocal() as db:
        notes=db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.document_id==doc.id,Notification.kind=='apr_participant_signature',Notification.read==False).all()
        for n in notes: n.read=True; n.read_at=now()
        if notes: db.commit()
    view=apr_view(data)
    signed,total=_participant_signature_counts(view)
    all_signed=bool(total and signed==total)
    can_sign=bool(doc.status=='Pendente assinatura' and not all_signed)

    # Resumo do QR geral: usa a assinatura diária do dia atual quando existir.
    # Durante a coleta inicial, a primeira assinatura já é registrada também como
    # assinatura diária, então o contador funciona nos dois momentos do fluxo.
    today_key=local_today().isoformat()
    signed_today=0
    eligible_today=0
    for w in (view.get('workers') or []):
        try:
            uid=int((w or {}).get('participant_user_id') or 0)
        except Exception:
            uid=0
        if not uid:
            continue
        eligible_today += 1
        daily=_worker_daily_signatures(w or {})
        if clean((daily.get(today_key) or {}).get('signature_image')):
            signed_today += 1
    pending_today=max(0,eligible_today-signed_today)
    qr_token=_apr_public_signature_token(doc.id)
    qr_target_url=f'{_public_base_url(request)}/apr/{doc.id}/assinatura-diaria'

    return templates.TemplateResponse(request,'apr_signature.html',context(
        request,doc=doc,data=view,entries=entries,can_sign=can_sign,all_signed=all_signed,
        collector_mode=collector_mode,checklist_items=CHECKLIST,critical_permits=APR_CRITICAL_PERMITS,
        linked_permit_states=linked_permit_states(view),
        participant_signed_count=signed,participant_total=total,
        qr_target_url=qr_target_url,signed_today=signed_today,pending_today=pending_today,
        eligible_today=eligible_today,today_label=local_today().strftime('%d/%m/%Y'),
    ))


OTP_TTL_SECONDS=300
OTP_MAX_TRIES=5
OTP_RESEND_SECONDS=30

def _otp_hash(user_id: int, doc_id: int, code: str) -> str:
    return hmac.new(APP_SECRET_VALUE.encode(),f'sign-otp:{user_id}:{doc_id}:{code}'.encode(),hashlib.sha256).hexdigest()

def _otp_issue(request: Request, user: User, doc: Document) -> tuple[bool,str]:
    """Gera um código de 6 dígitos, guarda só o HMAC na sessão e entrega por notificação interna."""
    cur=request.session.get('otp_sign') or {}
    t=time.time()
    if cur.get('doc')==doc.id and t-float(cur.get('sent',0))<OTP_RESEND_SECONDS:
        return False,f'Aguarde {int(OTP_RESEND_SECONDS-(t-float(cur.get("sent",0))))+1}s para pedir um novo código.'
    code=f'{secrets.randbelow(1000000):06d}'
    request.session['otp_sign']={'doc':doc.id,'h':_otp_hash(user.id,doc.id,code),'exp':t+OTP_TTL_SECONDS,'sent':t,'tries':0}
    with SessionLocal() as db:
        db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.document_id==doc.id,Notification.kind=='apr_signature_otp').delete(synchronize_session=False)
        note=Notification(recipient_user_id=user.id,document_id=doc.id,kind='apr_signature_otp',message=f'Código de assinatura: {code} (válido por {OTP_TTL_SECONDS//60} min). Não compartilhe.',read=False,created_at=now())
        db.add(note); db.commit()
    audit(user.id,'otp_assinatura_emitido',f'{doc.code}')
    return True,'Código enviado para suas notificações.'

def _otp_check(request: Request, user: User, doc: Document, code: str) -> str:
    """Retorna '' se válido; senão a mensagem de erro. O código é de uso único."""
    cur=request.session.get('otp_sign') or {}
    if cur.get('doc')!=doc.id or not cur.get('h'): return 'Solicite o código de assinatura antes de confirmar.'
    if time.time()>float(cur.get('exp',0)):
        request.session.pop('otp_sign',None); return 'O código expirou. Solicite um novo.'
    if int(cur.get('tries',0))>=OTP_MAX_TRIES:
        request.session.pop('otp_sign',None); return 'Tentativas excedidas. Solicite um novo código.'
    code=''.join(ch for ch in str(code or '') if ch.isdigit())
    if not hmac.compare_digest(_otp_hash(user.id,doc.id,code),cur['h']):
        cur['tries']=int(cur.get('tries',0))+1; request.session['otp_sign']=cur
        audit(user.id,'otp_assinatura_falha',f'{doc.code}')
        return 'Código incorreto.'
    request.session.pop('otp_sign',None)
    with SessionLocal() as db:
        db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.document_id==doc.id,Notification.kind=='apr_signature_otp').delete(synchronize_session=False); db.commit()
    return ''

@app.post('/apr/{doc_id}/assinar/codigo')
async def apr_signature_otp_request(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return JSONResponse({'ok':False,'message':'Sessão expirada.'},status_code=401)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    doc=get_document(doc_id)
    if doc.kind!='apr' or doc.status!='Pendente assinatura': return JSONResponse({'ok':False,'message':'APR não está aguardando assinatura.'},status_code=409)
    if not user_can_access_document(user,doc): return JSONResponse({'ok':False,'message':'Sem permissão.'},status_code=403)
    ok,msg=_otp_issue(request,user,doc)
    return JSONResponse({'ok':ok,'message':msg})

@app.post('/apr/{doc_id}/assinar')
async def apr_participant_signature_submit(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if doc.status!='Pendente assinatura':
        flash(request,'Esta APR não está aguardando assinatura de integrantes.','error')
        return RedirectResponse('/',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: worker_index=int(clean(form.get('worker_index')))
    except Exception: worker_index=-1
    data=doc_data(doc); workers=list(data.get('workers') or [])
    self_enroll = worker_index == -1
    if self_enroll:
        with SessionLocal() as db:
            participant=db.query(Participant).filter(Participant.user_id==user.id,Participant.active==True).first()
            company=db.get(Company,participant.company_id) if participant else None
        if not participant or not company or not company.active:
            raise HTTPException(403,'Seu usuário precisa estar vinculado a um participante ativo para assinar esta APR.')
        if any(str(w.get('participant_id') or '')==str(participant.id) for w in workers):
            raise HTTPException(409,'Este participante já faz parte da equipe desta APR.')
        worker={'participant_id':str(participant.id),'participant_user_id':str(user.id),'cpf':participant.cpf,'company':company.name,'worker':participant.full_name,'role':participant.job_title or ''}
        worker_index=len(workers)
        workers.append(worker)
    elif worker_index<0 or worker_index>=len(workers):
        raise HTTPException(400,'Integrante inválido.')
    else:
        worker=dict(workers[worker_index])
    try: linked_user_id=int(worker.get('participant_user_id') or 0)
    except Exception: linked_user_id=0
    if linked_user_id!=user.id:
        raise HTTPException(403,'Você só pode assinar sua própria participação na APR.')
    if clean(worker.get('signature_image')):
        flash(request,'Sua assinatura neste conjunto APR/PTs já foi registrada.','info')
        return RedirectResponse(f'/apr/{doc.id}/assinar',303)
    # O código é opcional: assinatura manual segue liberada; se informado, precisa ser válido.
    otp_error=_otp_check(request,user,doc,form.get('otp')) if clean(form.get('otp')) else ''
    if otp_error:
        flash(request,otp_error,'error')
        return RedirectResponse(f'/apr/{doc.id}/assinar',303)
    sig=save_signature(form.get('sig_participant'),' ',f'{data.get("code") or doc.code}_participant_{worker_index+1}').strip()
    if not sig:
        flash(request,'Faça sua rubrica para assinar a APR e as PTs vinculadas.','error')
        return RedirectResponse(f'/apr/{doc.id}/assinar',303)
    worker['signature']='RUBRICA'; worker['signature_image']=sig
    worker['date']=local_today().strftime('%d/%m/%Y')
    worker['signature_status']='Assinado'
    worker['signed_at']=now().strftime('%d/%m/%Y %H:%M')
    worker['signed_by_user_id']=str(user.id)
    worker['signed_by_name']=user.full_name or user.username
    _maybe_record_initial_signature_as_daily(worker,data,signature_image=sig,signer=user,signed_at=now(),mode='Assinatura inicial online')
    workers[worker_index]=worker; data['workers']=workers
    signed,total=_participant_signature_counts(data)
    data['participant_signature_status']='Concluída' if total and signed==total else 'Pendente'
    with SessionLocal() as db:
        target=db.get(Document,doc.id)
        if not target or target.status!='Pendente assinatura': raise HTTPException(409,'A APR mudou de status.')
        target.data_json=json.dumps({**data,'status':'Pendente assinatura'},ensure_ascii=False)
        target.updated_at=now()
        notes=db.query(Notification).filter(Notification.recipient_user_id==user.id,Notification.document_id==doc.id,Notification.kind=='apr_participant_signature').all()
        for n in notes: n.read=True; n.read_at=now()
        db.commit()
    _sync_apr_signatures_to_linked_permits({**data,'_document_id':str(doc.id)})
    audit(user.id,'assinar_apr_integrante',f'{doc.code} | integrante={worker_index+1}')
    signer_name=user.full_name or user.username
    notify_document_creator(
        doc,
        'apr_creator_signature',
        f'{doc_reference_code(doc)}: {signer_name} assinou como integrante. Assinaturas concluídas: {signed}/{total}.',
    )
    if total and signed==total:
        notify_document_creator(
            doc,
            'apr_creator_signatures_complete',
            f'{doc_reference_code(doc)}: todas as assinaturas dos integrantes foram concluídas. A APR já pode ser enviada para aprovação.',
            replace=True,
        )
        flash(request,'Assinatura registrada. Todas as assinaturas dos integrantes foram concluídas; a APR já pode ser enviada para aprovação.','success')
    else:
        flash(request,'Sua assinatura foi registrada com sucesso.','success')
    return RedirectResponse(f'/apr/{doc.id}/assinar',303)


@app.post('/api/apr/{doc_id}/participant-signature-present')
async def apr_participant_signature_present_submit(request: Request, doc_id: int):
    # Compatibilidade com telas antigas: aplica a mesma autorização da conta própria.
    return await apr_participant_signature_submit(request, doc_id)



def _manual_collector_check(user: User, doc: Document):
    if doc.kind!='apr': raise HTTPException(404,'APR não encontrada.')
    if doc.status!='Pendente assinatura': raise HTTPException(409,'Esta APR não está aguardando assinatura de integrantes.')
    if not (is_admin_user(user) or doc.created_by==user.id): raise HTTPException(403,'Somente o criador da APR ou um administrador pode coletar assinatura manual.')
    if not user_can_access_document(user,doc): raise HTTPException(403,'Esta APR não pertence ao seu escopo.')

def _manual_participant(cpf: str):
    cpf_clean=cpf_digits(cpf)
    if not cpf_is_valid(cpf_clean): raise HTTPException(422,'CPF inválido. Confira os 11 dígitos.')
    with SessionLocal() as db:
        row=(db.query(Participant,Company).join(Company,Participant.company_id==Company.id).filter(Participant.cpf==cpf_clean,Participant.active==True,Company.active==True).first())
        if not row: raise HTTPException(404,'CPF não encontrado no cadastro de participantes ativos.')
        participant,company=row
        linked=db.get(User,participant.user_id) if participant.user_id else None
        if linked and not linked.active: linked=None
        if linked: db.expunge(linked)
        db.expunge(participant); db.expunge(company)
    return participant,company,linked

@app.get('/apr/{doc_id}/assinar-manual/buscar')
def apr_manual_signature_lookup(request: Request, doc_id: int, cpf: str=''):
    raise HTTPException(403, 'Com internet, cada integrante deve entrar na própria conta para assinar a APR. A coleta no mesmo aparelho está disponível no fluxo offline.')


@app.post('/apr/{doc_id}/assinar-manual/codigo')
async def apr_manual_signature_otp(request: Request, doc_id: int):
    raise HTTPException(403, 'Cada integrante deve solicitar o código pela própria conta, na sua tela de assinatura.')


@app.post('/apr/{doc_id}/assinar-manual')
async def apr_manual_signature_submit(request: Request, doc_id: int):
    raise HTTPException(403, 'Com internet, cada integrante deve assinar pela própria conta. Use o fluxo offline para coletar assinaturas no mesmo aparelho.')


@app.get('/apr/{doc_id}/assinaturas-qr.svg')
def apr_signature_qr(request: Request, doc_id: int):
    user=current_user(request)
    if not user:
        raise HTTPException(401,'Entre no Safety Plus para visualizar este QR Code.')
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404,'APR não encontrada.')
    data=doc_data(doc)
    participant_idx=_apr_participant_worker_index(data,user.id)
    if not user_can_access_document(user,doc) and participant_idx is None:
        raise HTTPException(403,'Você não tem acesso a esta APR.')
    token=_apr_public_signature_token(doc.id)
    target=f'{_public_base_url(request)}/apr/{doc.id}/assinatura-diaria'
    qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=8,border=3)
    qr.add_data(target); qr.make(fit=True)
    img=qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    buf=io.BytesIO(); img.save(buf); buf.seek(0)
    return StreamingResponse(buf,media_type='image/svg+xml',headers={'Cache-Control':'private, no-store'})


@app.get('/apr/{doc_id}/assinar-publico/{token}',response_class=HTMLResponse)
def apr_public_signature_page(request: Request, doc_id: int, token: str):
    if not _apr_public_signature_valid(doc_id, token):
        raise HTTPException(403, 'Link de assinatura inválido.')
    doc = get_document(doc_id)
    if doc.kind != 'apr': raise HTTPException(404, 'APR não encontrada.')
    target = f'/apr/{doc_id}/assinar' if doc.status == 'Pendente assinatura' else f'/apr/{doc_id}/assinatura-diaria'
    if not current_user(request):
        return RedirectResponse(f'/login?next={target}', 303)
    return RedirectResponse(target, 303)


@app.get('/apr/{doc_id}/assinar-publico/{token}/participante')
def apr_public_signature_participant_lookup(request: Request, doc_id: int, token: str, cpf: str=''):
    # Links antigos não permitem consultar terceiros nem assinar por CPF.
    raise HTTPException(403, 'Entre na própria conta e abra sua assinatura da APR.')



@app.post('/apr/{doc_id}/assinar-publico/{token}',response_class=HTMLResponse)
async def apr_public_signature_submit(request: Request, doc_id: int, token: str):
    # Não aproveita rubricas de formulários públicos antigos, mesmo com token válido.
    raise HTTPException(403, 'A assinatura online exige a conta do próprio integrante. Entre na sua conta e assine novamente.')


@app.get('/apr/{doc_id}/assinatura-diaria',response_class=HTMLResponse)
def apr_daily_signature_page(request: Request, doc_id: int):
    user=current_user(request)
    if not user:
        return RedirectResponse(f'/login?next=/apr/{doc_id}/assinatura-diaria',303)
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404,'APR não encontrada.')
    data=doc_data(doc)
    participant_idx=_apr_participant_worker_index(data,user.id)
    collector_mode=bool(is_admin_user(user) or doc.created_by==user.id)
    if participant_idx is None and not collector_mode:
        raise HTTPException(403,'Seu usuário não está vinculado como integrante desta APR.')

    # Durante a coleta inicial, o mesmo QR leva o participante diretamente para a rubrica inicial.
    if doc.status=='Pendente assinatura' and participant_idx is not None:
        worker=(data.get('workers') or [])[participant_idx]
        if not clean((worker or {}).get('signature_image')):
            return RedirectResponse(f'/apr/{doc.id}/assinar',303)

    periods=_apr_signature_periods(data)
    valid_days=_apr_valid_days(data)
    today=local_today()
    period_tables=[]
    workers=list(data.get('workers') or [])
    for period in periods:
        rows=[]
        for i,w0 in enumerate(workers):
            w=dict(w0 or {})
            try: uid=int(w.get('participant_user_id') or 0)
            except Exception: uid=0
            if not collector_mode and uid!=user.id: continue
            daily=_worker_daily_signatures(w)
            day_cells=[]
            for d in period['days']:
                item=dict(daily.get(d.isoformat()) or {})
                day_cells.append({
                    'iso':d.isoformat(),'label':d.strftime('%d/%m'),'weekday':('Seg','Ter','Qua','Qui','Sex','Sáb','Dom')[d.weekday()],
                    'signed':bool(clean(item.get('signature_image'))),'signed_at':clean(item.get('signed_at')),
                    'signed_by_name':clean(item.get('signed_by_name')),
                    'is_today':d==today,'is_future':d>today,'is_past':d<today,
                })
            rows.append({'index':i,'worker':w.get('worker') or '', 'company':w.get('company') or '', 'role':w.get('role') or '', 'user_id':uid or '', 'days':day_cells})
        period_tables.append({'title':period['title'],'rows':rows})
    own_worker=(workers[participant_idx] if participant_idx is not None and participant_idx<len(workers) else {})
    own_daily=_worker_daily_signatures(own_worker or {})
    today_key=today.isoformat()
    today_in_range=today in valid_days
    already_today=bool(clean((own_daily.get(today_key) or {}).get('signature_image')))
    can_sign_today=bool(participant_idx is not None and doc.status in {'Aguardando aprovação','Finalizada'} and today_in_range and not already_today)
    return templates.TemplateResponse(request,'apr_daily_signature.html',context(
        request,doc=doc,data=apr_view(data),period_tables=period_tables,collector_mode=collector_mode,
        participant_idx=participant_idx,can_sign_today=can_sign_today,already_today=already_today,
        today_label=today.strftime('%d/%m/%Y'),today_in_range=today_in_range,
        qr_url=f'/apr/{doc.id}/assinaturas-qr.svg',
        public_signature_url=f'/apr/{doc.id}/assinatura-diaria',
    ))


@app.post('/apr/{doc_id}/assinatura-diaria')
async def apr_daily_signature_submit(request: Request, doc_id: int):
    user=current_user(request)
    if not user:
        return RedirectResponse(f'/login?next=/apr/{doc_id}/assinatura-diaria',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        target=db.get(Document,doc_id)
        if not target or target.kind!='apr': raise HTTPException(404,'APR não encontrada.')
        if target.status not in {'Aguardando aprovação','Finalizada'}:
            flash(request,'A assinatura diária fica disponível após a coleta inicial dos integrantes.','error')
            return RedirectResponse(f'/apr/{doc_id}/assinatura-diaria',303)
        data=doc_data(target); workers=list(data.get('workers') or [])
        idx=_apr_participant_worker_index(data,user.id)
        if idx is None:
            raise HTTPException(403,'Seu usuário não está vinculado como integrante desta APR.')
        valid_days=_apr_valid_days(data); today=local_today()
        if today not in valid_days:
            flash(request,'Hoje está fora do período de validade desta APR.','error')
            return RedirectResponse(f'/apr/{doc_id}/assinatura-diaria',303)
        worker=dict(workers[idx] or {}); daily=_worker_daily_signatures(worker)
        if clean((daily.get(today.isoformat()) or {}).get('signature_image')):
            flash(request,'Sua assinatura de hoje já foi registrada.','info')
            return RedirectResponse(f'/apr/{doc_id}/assinatura-diaria',303)
        sig=save_signature(form.get('sig_daily'),' ',f'{data.get("code") or target.code}_daily_{idx+1}_{today.isoformat()}').strip()
        if not sig:
            flash(request,'Faça sua rubrica antes de confirmar a assinatura diária.','error')
            return RedirectResponse(f'/apr/{doc_id}/assinatura-diaria',303)
        _record_worker_daily_signature(worker,today,signature_image=sig,signer=user,mode='Assinatura diária')
        workers[idx]=worker; data['workers']=workers
        target.data_json=json.dumps(data,ensure_ascii=False); target.updated_at=now()
        finalizada=target.status=='Finalizada'
        db.commit(); db.refresh(target); db.expunge(target)
    # Confirma a persistência antes de exibir sucesso ao usuário.
    saved_data=doc_data(get_document(doc_id))
    saved_workers=list(saved_data.get('workers') or [])
    confirmed=(idx<len(saved_workers) and bool(clean((_worker_daily_signatures(saved_workers[idx]).get(today.isoformat()) or {}).get('signature_image'))))
    if not confirmed:
        audit(user.id,'apr_assinatura_diaria_nao_confirmada',f'{target.code} | data={today.isoformat()}')
        flash(request,'A rubrica não foi confirmada no banco. Tente novamente.','error')
        return RedirectResponse(f'/apr/{doc_id}/assinatura-diaria',303)
    if finalizada:
        # Atualiza automaticamente o PDF/dossiê final com a folha de assinaturas diárias.
        try:
            target=finalize_pdf(target,saved_data)
        except Exception as exc:
            audit(user.id,'apr_pdf_diario_falha',f'{target.code}: {exc}')
            flash(request,'Assinatura salva no banco, mas o PDF não foi atualizado.','warning')
    audit(user.id,'assinar_apr_diaria',f'{target.code} | data={today.isoformat()} | integrante={idx+1}')
    notify_document_creator(target,'apr_creator_daily_signature',f'{doc_reference_code(target)}: {user.full_name or user.username} registrou a assinatura diária de {today.strftime("%d/%m/%Y")}.' )
    flash(request,'Assinatura diária registrada com sucesso.','success')
    return RedirectResponse(f'/apr/{doc_id}/assinatura-diaria',303)


@app.post('/apr/{apr_id}/pts/adicionar')
async def apr_add_permit_type(request: Request, apr_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    apr=get_document(apr_id)
    if apr.kind!='apr': raise HTTPException(404,'APR não encontrada.')
    if not _can_manage_finalized_apr(user,apr): raise HTTPException(403,'Acesso negado.')
    form=await request.form()
    verify_csrf(request,form.get('csrf_token'))
    name=clean(form.get('permit_name'))
    data=doc_data(apr)
    if name not in APR_CRITICAL_PERMIT_KIND:
        flash(request,'Selecione uma permissão válida.','error')
        return RedirectResponse(f'/apr/{apr.id}/pts',303)
    if apr.status!='Finalizada':
        flash(request,'A APR precisa estar aprovada e finalizada.','error')
        return RedirectResponse(f'/apr/{apr.id}/pts',303)
    if not _apr_day_context(data)['valid_today']:
        flash(request,'APR fora da vigência. Crie uma nova APR para continuar a atividade.','error')
        return RedirectResponse(f'/apr/{apr.id}/pts',303)
    selected=list(data.get('critical_permits') or [])
    if name not in selected:
        selected.append(name)
        data['critical_permits']=[p for p in APR_CRITICAL_PERMITS if p in selected]
        data['critical_activity']='SIM'
        _persist_document_data(apr.id,data)
        audit(user.id,'adicionar_tipo_pt_apr',f'{doc_reference_code(apr)}: {name}')
    return RedirectResponse(f'/apr/{apr.id}/permit/{APR_CRITICAL_PERMIT_KIND[name]}/open',303)


@app.get('/apr/{apr_id}/permit/{kind}/open')
def apr_open_linked_permit(request: Request, apr_id: int, kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    permit_name=APR_CRITICAL_KIND_PERMIT.get(kind)
    if not permit_name: raise HTTPException(404,'Permissão não reconhecida.')
    apr=get_document(apr_id)
    if apr.kind!='apr': raise HTTPException(404)
    if not user_can_access_document(user,apr):
        audit(user.id,'acesso_negado_documento',f'doc_id={apr.id} kind=apr')
        raise HTTPException(403,'Você não tem permissão para acessar esta APR.')
    if apr.status=='Finalizada' and not _can_manage_finalized_apr(user,apr):
        raise HTTPException(403,'Você não tem permissão para emitir permissões nesta APR.')
    data=doc_data(apr)
    if data.get('critical_activity')!='SIM' or permit_name not in (data.get('critical_permits') or []):
        flash(request,'Essa permissão não está selecionada nesta APR.','error')
        return RedirectResponse(f'/apr/{apr.id}/pts',303)
    if apr.status in {'Pendente assinatura','Aguardando aprovação'}:
        flash(request,'As permissões não podem mais ser alteradas depois que a coleta de assinaturas foi iniciada.','error')
        return RedirectResponse(f'/apr/{apr.id}/edit',303)
    ctx=_apr_day_context(data)
    if not ctx['valid_today']:
        flash(request,f'A APR não está vigente hoje. Período atual: {ctx["start_label"] or "-"} a {ctx["end_label"] or "-"}. Crie uma nova APR antes de emitir uma nova PT.','error')
        return RedirectResponse(f'/apr/{apr.id}/pts',303)
    try:
        linked=ensure_linked_permit(apr,data,permit_name,user)
    except Exception as e:
        flash(request,str(e),'error')
        return RedirectResponse(f'/apr/{apr.id}/pts',303)
    return RedirectResponse(f'/permit/{kind}/{linked.id}/edit',303)


def _pt_has_registered_signature(value: Any) -> bool:
    """Impede excluir rascunhos com qualquer rubrica registrada."""
    if isinstance(value, dict):
        for key, item in value.items():
            k=str(key).lower()
            if ('signature' in k or 'rubric' in k or 'rubrica' in k or k in ('visto','signed_at')) and k not in ('signature_status','signature_mode','signature_pending','signature_required'):
                if isinstance(item, str) and item.strip() and item.strip().lower() not in ('não','nao','pendente','false','0','sem assinatura'):
                    return True
            if isinstance(item,(dict,list)) and _pt_has_registered_signature(item): return True
    elif isinstance(value,list):
        return any(_pt_has_registered_signature(item) for item in value)
    return False


@app.post('/apr/{apr_id}/pts/{pt_id}/excluir')
async def apr_delete_linked_pt_draft(request: Request, apr_id: int, pt_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        apr=db.get(Document,apr_id)
        pt=db.get(Document,pt_id)
        if not apr or apr.kind!='apr' or not pt: raise HTTPException(404,'APR ou PT não encontrada.')
        if not user_can_access_document(user,apr) or not user_can_access_document(user,pt): raise HTTPException(403,'Sem acesso.')
        if apr.status=='Finalizada' and not _can_manage_finalized_apr(user,apr): raise HTTPException(403,'Sem permissão para alterar esta APR.')
        if user.id!=pt.created_by and not is_admin_user(user): raise HTTPException(403,'Somente o criador ou administrador pode excluir.')
        apr_data=doc_data(apr); pt_data=doc_data(pt)
        if pt_id not in _linked_history_ids(apr_data) or str(pt_data.get('linked_apr_id'))!=str(apr_id):
            raise HTTPException(409,'Esta PT não está vinculada à APR informada.')
        if pt.status!='Rascunho' or _pt_has_registered_signature(pt_data):
            raise HTTPException(409,'Somente PT em rascunho e sem assinatura pode ser excluída.')
        code=doc_reference_code(pt); internal_code=pt.code; pdf_path=pt.pdf_path
        # Retira as referências antes da exclusão, sem alterar a APR nem outras PTs.
        apr_data['linked_permit_history']=[x for x in (apr_data.get('linked_permit_history') or []) if str((x or {}).get('id'))!=str(pt_id)]
        mapping=dict(apr_data.get('linked_permit_ids') or {})
        apr_data['linked_permit_ids']={k:v for k,v in mapping.items() if str(v)!=str(pt_id)}
        apr.data_json=json.dumps(apr_data,ensure_ascii=False); apr.updated_at=now()
        db.query(Notification).filter(Notification.document_id==pt_id).delete(synchronize_session=False)
        db.delete(pt); db.commit()
    _remove_storage_file(pdf_path)
    audit(user.id,'excluir_pt_rascunho_vinculada',f'{code} | APR {apr_id}')
    flash(request,f'{code} excluída com sucesso.','success')
    return RedirectResponse(f'/apr/{apr_id}/pts',303)


@app.get('/apr/{doc_id}/pts',response_class=HTMLResponse)
def apr_daily_permits_page(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    apr=get_document(doc_id)
    if apr.kind!='apr': raise HTTPException(404)
    if not user_can_access_document(user,apr):
        raise HTTPException(403,'Você não tem permissão para acessar esta APR.')
    refresh_pending_permit_closures()
    data=apr_view(doc_data(apr))
    ctx=_apr_day_context(data)
    records=linked_permit_records(data)
    start=ctx['start']; today=local_today()
    for row in records:
        d=parse_date_br(row.get('date'))
        row['day_number']=(d-start).days+1 if d and start and start<=d<=(ctx['end'] or d) else None
        row['is_today']=bool(d==today)
        linked_doc=get_document(row['id'])
        row['can_delete']=bool(row['status']=='Rascunho' and not _pt_has_registered_signature(doc_data(linked_doc)) and (user.id==linked_doc.created_by or is_admin_user(user)))
        if row['status']=='Finalizada': row['open_url']=f'/document/{row["id"]}/pdf'
        else: row['open_url']=f'/permit/{row["kind"]}/{row["id"]}/edit'
    today_records=[r for r in records if r.get('is_today')]
    history=list(reversed(records))
    selected=[p for p in (data.get('critical_permits') or []) if p in APR_CRITICAL_PERMITS]
    # V36.18.97 — linha do tempo da vigência e resumo por tipo de PT.
    end=ctx['end']; timeline_days=[]
    if start and end:
        span=(end-start).days+1
        for i in range(max(1,min(span,31))):
            d=start+timedelta(days=i)
            timeline_days.append({'n':i+1,'label':d.strftime('%d/%m'),'state':'today' if d==today else ('past' if d<today else 'future'),
                                  'count':sum(1 for r in records if parse_date_br(r.get('date'))==d)})
    days_left=(end-today).days if end and ctx['valid_today'] else None
    expired_days=(today-end).days if end and today>end else None
    not_started=bool(start and today<start)
    by_name={}
    for r in today_records: by_name.setdefault(r['name'],[]).append(r)
    total_by_name={}
    for r in records: total_by_name[r['name']]=total_by_name.get(r['name'],0)+1
    return templates.TemplateResponse(
        request,'apr_permits.html',context(
            request,doc=apr,data=data,validity=ctx,records=history,today_records=today_records,
            selected_permits=selected,available_permits=[p for p in APR_CRITICAL_PERMITS if p not in selected],permit_kind=APR_CRITICAL_PERMIT_KIND,
            timeline_days=timeline_days,days_left=days_left,expired_days=expired_days,not_started=not_started,
            today_by_name=by_name,total_by_name=total_by_name,open_today=sum(1 for r in today_records if r['status']!='Finalizada'),
        )
    )


@app.get('/apr/{doc_id}/dossie')
def apr_dossier(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    apr=get_document(doc_id)
    if apr.kind!='apr': raise HTTPException(404)
    if not user_can_access_document(user,apr):
        raise HTTPException(403,'Você não tem permissão para acessar esta APR.')
    if apr.status!='Finalizada':
        flash(request,'O dossiê fica disponível depois que a APR é aprovada.','error')
        return RedirectResponse(f'/apr/{apr.id}/edit',303)
    data=doc_data(apr)
    # Sempre recria a primeira parte diretamente dos dados da APR para garantir
    # que o dossiê não duplique PTs que versões antigas possam ter mesclado no PDF.
    dossier_dir=PDF_DIR/'dossies'; dossier_dir.mkdir(parents=True,exist_ok=True)
    code=data_reference_code('apr',data,apr.cluster,apr.site) or apr.code
    base_path=dossier_dir/f'{safe_filename(code)}_APR_BASE_TMP.pdf'
    out=dossier_dir/f'{safe_filename(code)}_DOSSIE.pdf'
    is_preview=(request.query_params.get('preview_meta')=='1' or bool(clean(request.query_params.get('preview_page'))))
    # A abertura normal recria o dossie para garantir conteudo atual. As requisicoes
    # das imagens de cada pagina reutilizam o arquivo acabado de gerar.
    if not is_preview or not out.exists():
        pdf_data=dict(data); pdf_data['code']=code
        generate_document('apr',pdf_data,base_path)
        merged=fitz.open(base_path)
        try:
            for row in linked_permit_records(data):
                if row.get('status')!='Finalizada': continue
                linked=get_document(row['id'])
                p=ensure_document_pdf(linked)
                if not p or not p.exists(): continue
                src=fitz.open(p)
                try: merged.insert_pdf(src)
                finally: src.close()
            tmp=out.with_name(out.stem+'_tmp.pdf')
            if tmp.exists(): tmp.unlink()
            merged.save(tmp,garbage=4,deflate=True)
        finally:
            merged.close()
            try: base_path.unlink()
            except Exception: pass
        tmp.replace(out)
        audit(user.id,'gerar_dossie_apr_pts',f'{apr.code} | pts={len(linked_permit_records(data))}')
    preview=pdf_preview_response(request,out)
    if preview is not None: return preview
    if request.query_params.get('raw')=='1':
        return FileResponse(out,media_type='application/pdf',filename=f'{safe_filename(code)}_DOSSIE.pdf',content_disposition_type='inline',headers={'Cache-Control':'no-store'})
    return templates.TemplateResponse(request,'pdf_viewer.html',context(
        request,doc=apr,pdf_title=f'Dossiê {code}',pdf_error='',raw_pdf_url=f'/apr/{apr.id}/dossie?raw=1',
        daily_signature_url=f'/apr/{apr.id}/assinatura-diaria',
    ))


async def parse_apr_approval(request: Request, old: dict, user: User) -> dict:
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    d=dict(old); olda=old.get('approvals',[]) or []
    signature_only=clean(form.get('approval_signature_only'))=='1'
    if signature_only:
        approvals=[dict(a) for a in olda[:5]]
        while len(approvals)<5: approvals.append({})
        prev=approvals[0] if approvals else {}
        sig=save_signature(form.get('sig_approval_0'),prev.get('signature_image',''),f"{d['code']}_approval_1")
        start=local_today(); end=start+timedelta(days=6)
        approvals[0]={
            'name':user.full_name or user.username,
            'role':'Líder ou responsável pela atividade',
            'start':start.strftime('%d/%m/%Y'),
            'end':end.strftime('%d/%m/%Y'),
            'signature':'RUBRICA' if sig else '',
            'signature_image':sig,
        }
        d['approvals']=approvals
        d['_approval_signature_only']=True
        return d
    approvals=[]
    for i in range(5):
        prev=olda[i] if i<len(olda) else {}
        field_names=(f'approval_{i}_name',f'approval_{i}_role',f'approval_{i}_start',f'approval_{i}_end',f'sig_approval_{i}')
        # Linhas que não estão sendo exibidas na tela não podem apagar
        # aprovações antigas já salvas.
        if i>0 and not any(key in form for key in field_names):
            approvals.append(dict(prev)); continue
        sig=save_signature(form.get(f'sig_approval_{i}'),prev.get('signature_image',''),f"{d['code']}_approval_{i+1}")
        name=clean(form.get(f'approval_{i}_name'))
        role=clean(form.get(f'approval_{i}_role'))
        # Na primeira aprovação, facilita o trabalho do administrador selecionado.
        if i==0 and not name: name=user.full_name or user.username
        if i==0 and not role: role='Líder ou responsável pela atividade'
        approvals.append({'name':name,'role':role,'start':br_date(form.get(f'approval_{i}_start')),'end':br_date(form.get(f'approval_{i}_end')),'signature':'RUBRICA' if sig else '','signature_image':sig})
    d['approvals']=approvals
    return d


@app.post('/apr/{doc_id}/approve')
async def apr_approve(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if not is_admin_user(user): raise HTTPException(403,'Somente administrador pode aprovar APR.')
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if doc.status!='Aguardando aprovação': raise HTTPException(409,'Esta APR não está aguardando aprovação.')
    if not user_can_access_document(user,doc):
        raise HTTPException(403,'Esta APR não pertence ao seu Cluster/Site de responsabilidade.')
    old=doc_data(doc)
    allowed_approver_ids=_approver_ids_for_data(old)
    if allowed_approver_ids and user.id not in allowed_approver_ids and not can_approve_any(user):
        raise HTTPException(403,'Esta APR foi direcionada a outro líder ou responsável pela atividade.')
    d=await parse_apr_approval(request,old,user)
    signature_only=bool(d.pop('_approval_signature_only',False))
    approval_return=f'/apr/{doc.id}/aprovar' if signature_only else f'/apr/{doc.id}/edit'
    try: validate_apr_dates(d,old)
    except Exception as e:
        flash(request,str(e),'error'); return RedirectResponse(approval_return,303)
    if not any(clean(a.get('signature_image')) for a in d.get('approvals',[])):
        flash(request,'Faça sua rubrica antes de aprovar a APR.','error'); return RedirectResponse(approval_return,303)
    if _participant_signature_required(d) and not _participant_signatures_complete(d):
        signed,total=_participant_signature_counts(d)
        flash(request,f'Não é possível aprovar. Assinaturas dos integrantes: {signed}/{total} concluídas.','error'); return RedirectResponse(approval_return,303)
    apr_no=apr_no_unacknowledged(d)
    if apr_no:
        flash(request,'Não é possível aprovar: o checklist da APR tem resposta NÃO (itens '+', '.join(map(str,apr_no))+') sem justificativa registrada.','error')
        return RedirectResponse(approval_return,303)
    if any(clean(x).upper()=='NÃO' for x in (d.get('checklist') or [])):
        _form=await request.form()
        if clean(_form.get('no_ack_approver'))!='1':
            flash(request,'Esta APR tem resposta NÃO no checklist. Leia a justificativa e marque a ciência do aprovador para aprovar.','error')
            return RedirectResponse(approval_return,303)
        d['checklist_no_approver_ack_by']=user.full_name or user.username
        d['checklist_no_approver_ack_at']=now().strftime('%d/%m/%Y %H:%M')
        audit(user.id,'apr_aprovada_com_nao',f'{doc.code} | justificativa de {clean(d.get("checklist_no_by"))}')
    d['approved_by_id']=str(user.id); d['approved_by_name']=user.full_name or user.username; d['approved_at']=now().strftime('%d/%m/%Y %H:%M'); d['status']='Finalizada'
    saved=save_doc(doc,'apr',d,user,'Finalizada')
    try:
        _finalize_prepared_linked_permits(saved,d,user)
        saved=finalize_pdf(saved,d)
    except Exception as e:
        with SessionLocal() as db:
            t=db.get(Document,saved.id); t.status='Aguardando aprovação'; t.finalized_at=None; t.data_json=json.dumps({**d,'status':'Aguardando aprovação'},ensure_ascii=False); db.commit()
        flash(request,f'Falha ao gerar o PDF; a APR continua aguardando aprovação: {e}','error'); return RedirectResponse(f'/apr/{saved.id}/aprovar' if signature_only else f'/apr/{saved.id}/edit',303)
    with SessionLocal() as db:
        notes=db.query(Notification).filter(Notification.document_id==saved.id,Notification.kind=='apr_approval').all()
        for n in notes: n.read=True; n.read_at=now()
        db.commit()
    audit(user.id,'aprovar_apr',f'{saved.code} | aprovador={d["approved_by_name"]}')
    notify_document_creator(
        saved,
        'apr_creator_approved',
        f'{doc_reference_code(saved)}: aprovada por {d["approved_by_name"]}. O documento foi finalizado e o PDF está disponível.',
        replace=True,
    )
    flash(request,f'{doc_reference_code(saved)} aprovada e PDF gerado com sucesso.','success')
    return RedirectResponse(f'/document/{saved.id}/pdf',303)

@app.post('/apr/{doc_id}/reject')
async def apr_reject(request: Request, doc_id: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if not is_admin_user(user): raise HTTPException(403,'Somente administrador pode reprovar APR.')
    doc=get_document(doc_id)
    if doc.kind!='apr': raise HTTPException(404)
    if doc.status!='Aguardando aprovação': raise HTTPException(409,'Esta APR não está aguardando aprovação.')
    if not user_can_access_document(user,doc):
        raise HTTPException(403,'Esta APR não pertence ao seu Cluster/Site de responsabilidade.')
    data=doc_data(doc)
    allowed_approver_ids=_approver_ids_for_data(data)
    if allowed_approver_ids and user.id not in allowed_approver_ids and not can_approve_any(user):
        raise HTTPException(403,'Esta APR foi direcionada a outro líder ou responsável pela atividade.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    reason=clean(form.get('reason'))
    if not reason:
        flash(request,'Informe o motivo da reprovação da APR.','error')
        return RedirectResponse(f'/apr/{doc.id}/edit',303)

    # A APR volta para correção. Como o conteúdo poderá ser alterado,
    # as assinaturas dos integrantes são zeradas e deverão ser coletadas novamente.
    workers=[]
    for w in data.get('workers') or []:
        item=dict(w)
        for key in ('date','signature','signature_image','signature_status','signed_at','signed_by_user_id','signed_by_name'):
            item[key]=''
        workers.append(item)
    data['workers']=workers
    data['approvals']=[{} for _ in range(5)]
    data['participant_signature_status']='Não solicitada'
    data['participant_signatures_requested_at']=''
    data['participant_signatures_requested_by_id']=''
    data['participant_signatures_requested_by_name']=''
    data['approval_requested_at']=''
    data['submitted_by_id']=''
    data['submitted_by_name']=''
    data['approved_by_id']=''
    data['approved_by_name']=''
    data['approved_at']=''
    data['rejection_status']='Reprovada'
    data['last_rejected_at']=now().strftime('%d/%m/%Y %H:%M')
    data['last_rejected_by_id']=str(user.id)
    data['last_rejected_by_name']=user.full_name or user.username
    data['last_rejection_reason']=reason
    data['status']='Rascunho'
    saved=save_doc(doc,'apr',data,user,'Rascunho')
    _clear_apr_signature_notifications(saved.id)
    with SessionLocal() as db:
        notes=db.query(Notification).filter(Notification.document_id==saved.id,Notification.kind=='apr_approval').all()
        for n in notes:
            n.read=True; n.read_at=now()
        db.commit()
    notify_user(
        saved.created_by,saved,'apr_creator_rejected',
        f'{doc_reference_code(saved)}: reprovada por {data["last_rejected_by_name"]}. Motivo: {reason}',
        replace=True,
    )
    audit(user.id,'reprovar_apr',f'{saved.code} | motivo={reason}')
    flash(request,f'{doc_reference_code(saved)} reprovada e devolvida para correção.','success')
    return RedirectResponse(f'/apr/{saved.id}/edit',303)


# -------------------- Veículo pesado --------------------
def vehicle_defaults():
    return {'code':next_code('vehicle'),'status':'Rascunho','cluster':'','site':'','model':'','operator':'','month':f'{local_today().month:02d}','year':str(local_today().year),'observations':'','day_mode':True,'day_period':VEHICLE_DAYS[local_today().weekday()],'days':{day:{'answers':['']*len(VEHICLE_CHECK_ITEMS),'photos':[[] for _ in VEHICLE_CHECK_ITEMS],'signature_image':'','locked':False,'completed_at':''} for day in VEHICLE_DAYS}}

def _vehicle_day_locked(info: dict) -> bool:
    if bool(info.get('locked')):
        return True
    answers=list(info.get('answers',[]) or [])
    return bool(info.get('signature_image')) and len(answers)==len(VEHICLE_CHECK_ITEMS) and all(a in {'C','NA'} for a in answers)

def vehicle_view(d):
    x=dict(d)
    x['cluster'],x['site']=split_separate_cluster_site(x.get('cluster',''),x.get('site',''))
    x.setdefault('days',{})
    for day in VEHICLE_DAYS:
        info=x['days'].setdefault(day,{})
        info['answers']=(list(info.get('answers',[]))+['']*len(VEHICLE_CHECK_ITEMS))[:len(VEHICLE_CHECK_ITEMS)]
        raw_photos=list(info.get('photos') or [])
        info['photos']=[([clean(x) for x in (raw_photos[i] if i<len(raw_photos) and isinstance(raw_photos[i],list) else []) if clean(x)][:3]) for i in range(len(VEHICLE_CHECK_ITEMS))]
        info.setdefault('signature_image','')
        info['locked']=_vehicle_day_locked(info)
        info.setdefault('completed_at','')
    return x

@app.get('/vehicle/new',response_class=HTMLResponse)
def vehicle_new(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    return templates.TemplateResponse(request,'vehicle_form.html',context(request,data=vehicle_view(prefill_location(user,vehicle_defaults())),doc=None,clusters=separate_clusters_for_user(user)[0],cluster_sites=separate_clusters_for_user(user)[1],items=VEHICLE_CHECK_ITEMS,item_numbers=VEHICLE_ITEM_NUMBERS,days=VEHICLE_DAYS))

@app.get('/vehicle/{doc_id}/edit',response_class=HTMLResponse)
def vehicle_edit(request: Request,doc_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if doc.kind!='vehicle': raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para acessar este documento.')
    admin_mode=False
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    return templates.TemplateResponse(request,'vehicle_form.html',context(request,data=vehicle_view(doc_data(doc)),doc=doc,clusters=separate_clusters_for_user(user)[0],cluster_sites=separate_clusters_for_user(user)[1],items=VEHICLE_CHECK_ITEMS,item_numbers=VEHICLE_ITEM_NUMBERS,days=VEHICLE_DAYS,admin_edit=admin_mode))

async def parse_vehicle(request: Request,old:dict):
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    d={'code':old.get('code') or next_code('vehicle'),'status':old.get('status','Rascunho'),'cluster':clean(form.get('cluster')),'site':clean(form.get('site')),'model':clean(form.get('model')),'operator':clean(form.get('operator')),'month':clean(form.get('month')),'year':clean(form.get('year')),'observations':clean(form.get('observations')),'days':{}}
    if old.get('day_mode'): d['day_mode']=True; d['day_period']=old.get('day_period') or VEHICLE_DAYS[local_today().weekday()]
    d['cluster'],d['site']=sanitize_separate_cluster_site(d['cluster'],d['site'])
    olddays=old.get('days',{}) or {}
    if any(_vehicle_day_locked(olddays.get(day,{}) or {}) for day in VEHICLE_DAYS):
        # Depois do primeiro dia concluído, os dados gerais do mesmo código também ficam imutáveis.
        for key in ('cluster','site','model','operator','month','year','observations'):
            d[key]=old.get(key,d.get(key,''))
    for di,day in enumerate(VEHICLE_DAYS):
        prev=olddays.get(day,{}) or {}
        if d.get('day_mode') and day!=d['day_period']:
            d['days'][day]={'answers':['']*len(VEHICLE_CHECK_ITEMS),'photos':[[] for _ in VEHICLE_CHECK_ITEMS],'signature_image':'','locked':False,'completed_at':''}
            continue
        if _vehicle_day_locked(prev):
            # Dia concluído é imutável, inclusive para administrador ou POST manipulado.
            d['days'][day]={
                'answers':(list(prev.get('answers',[]))+['']*len(VEHICLE_CHECK_ITEMS))[:len(VEHICLE_CHECK_ITEMS)],
                'photos':list(prev.get('photos') or [[] for _ in VEHICLE_CHECK_ITEMS]),
                'signature_image':prev.get('signature_image',''),
                'visto':prev.get('visto') or ('RUBRICA' if prev.get('signature_image') else ''),
                'no_justification':prev.get('no_justification',''),
                'locked':True,
                'completed_at':prev.get('completed_at',''),
            }
            continue
        answers=[clean(form.get(f'day_{di}_item_{i}')) for i in range(len(VEHICLE_CHECK_ITEMS))]
        if clean(form.get('fill_na'))=='1' and clean(form.get('action'))=='complete_day' and di==int(clean(form.get('active_day')) or '-1'):
            answers=[x if x in {'C','NC','NA'} else 'NA' for x in answers]  # confirmado pelo usuário no navegador
        sig=save_signature(form.get(f'sig_day_{di}'),prev.get('signature_image',''),f"{d['code']}_{di}")
        requested_lock=clean(form.get(f'day_{di}_locked'))=='1'
        prev_photos=list(prev.get('photos') or [])
        photos=[]
        for i in range(len(VEHICLE_CHECK_ITEMS)):
            kept=[clean(x) for x in (prev_photos[i] if i<len(prev_photos) and isinstance(prev_photos[i],list) else []) if clean(x)][:3]
            for upload in form.getlist(f'day_{di}_photo_{i}'):
                if len(kept)>=3: break
                if getattr(upload,'filename',''):
                    _saved=await save_photo_or_flash(request,upload,f"{d['code']}_vehicle_{di}_{i+1}")
                    if _saved: kept.append(_saved)
            photos.append(kept[:3])
        no_just=clean(form.get(f'day_{di}_no_justification'))[:1500] if 'NC' in answers else ''
        info={'answers':answers,'photos':photos,'signature_image':sig,'visto':'RUBRICA' if sig else '','no_justification':no_just,'locked':False,'completed_at':''}
        if requested_lock and bool(sig) and len(answers)==len(VEHICLE_CHECK_ITEMS) and all(a in {'C','NC','NA'} for a in answers) and ('NC' not in answers or no_just):
            info['locked']=True
            info['completed_at']=now().isoformat()
        d['days'][day]=info
    return d,clean(form.get('action')) or 'draft',int(clean(form.get('active_day')) or '0')

def day_complete(info): return bool(info.get('signature_image')) and all(a in {'C','NC','NA'} for a in info.get('answers',[])) and ('NC' not in info.get('answers',[]) or bool(clean(info.get('no_justification')))) and len(info.get('answers',[]))==len(VEHICLE_CHECK_ITEMS)

@app.post('/vehicle/save')
async def vehicle_create_save(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    d,action,active=await parse_vehicle(request,vehicle_defaults()); return process_vehicle(request,user,None,d,action,active)

@app.post('/vehicle/{doc_id}/save')
async def vehicle_update_save(request: Request,doc_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    doc=get_document(doc_id)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar este documento.')
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    d,action,active=await parse_vehicle(request,doc_data(doc)); return process_vehicle(request,user,doc,d,action,active)

def process_vehicle(request,user,doc,d,action,active):
    if action=='complete_day':
        general=[]
        if not d.get('model'): general.append('model')
        if not d.get('operator'): general.append('operator')
        if d.get('day_mode') and d.get('day_period') in VEHICLE_DAYS: active=VEHICLE_DAYS.index(d['day_period'])
        active=max(0,min(active,len(VEHICLE_DAYS)-1)); day=VEHICLE_DAYS[active]; info=d['days'][day]
        nc=[i+1 for i,a in enumerate(info['answers']) if a=='NC' and not clean(info.get('no_justification'))]; blank=[i+1 for i,a in enumerate(info['answers']) if not a]
        fields=general+[f'day_{active}_item_{i-1}' for i in [*nc,*blank]]
        if nc: fields.append(f'day_{active}_no_justification')
        if not info.get('signature_image'): fields.append(f'sig_day_{active}')
        missing_photo=[]  # foto de evidência é opcional em todas as inspeções
        if general or nc or blank or not info.get('signature_image') or missing_photo:
            msg=f'Não é possível concluir {day}. '
            if general: msg+='Preencha Modelo e Motorista/Operador. '
            if nc: msg+='Item(ns) Não conforme sem justificativa: '+', '.join(map(str,nc))+'. Descreva a justificativa na caixa do dia. '
            if blank: msg+='Sem seleção: '+', '.join(map(str,blank))+'. '
            if not info.get('signature_image'): msg+='Faça a rubrica do responsável do dia. '
            if missing_photo: msg+='Anexe foto nos itens aplicáveis: '+', '.join(map(str,missing_photo))+'. '
            saved=save_validation_state(doc,'vehicle',d,user,fields,'Rascunho')
            flash(request,msg+'O que já foi preenchido foi mantido.','error')
            return RedirectResponse(f'/vehicle/{saved.id}/edit',303)
        info['locked']=True
        info['completed_at']=info.get('completed_at') or now().isoformat()
        clear_validation_state(d)
        final=all(_vehicle_day_locked(d['days'][x]) for x in ([d['day_period']] if d.get('day_mode') else VEHICLE_DAYS)); status='Finalizada' if final else 'Rascunho'; saved=save_doc(doc,'vehicle',d,user,status)
        try: saved=finalize_pdf(saved,d)
        except Exception as e:
            flash(request,f'Dados salvos, mas o PDF não foi atualizado: {e}','error'); return RedirectResponse(f'/vehicle/{saved.id}/edit',303)
        audit(user.id,'concluir_dia',f'{saved.code} {day}')
        return RedirectResponse(f'/document/{saved.id}/pdf',303)
    clear_validation_state(d)
    saved=save_doc(doc,'vehicle',d,user,'Rascunho'); flash(request,'Rascunho da inspeção salvo.','success'); return RedirectResponse(f'/vehicle/{saved.id}/edit',303)


# -------------------- Inspeções adicionais --------------------
def inspection_defaults(kind: str) -> dict:
    cfg=INSPECTION_MODULES[kind]
    d={'code':next_code(kind),'status':'Rascunho','cluster':'','site':'','activity':cfg['short']}
    for key,_label in cfg.get('fields',[]): d[key]=''
    if cfg.get('month_year'):
        d['month']=f'{local_today().month:02d}'; d['year']=str(local_today().year)
    if cfg['mode'] in {'daily','weekly'}:
        d['periods']={name:{'answers':['']*len(cfg['items']),'photos':[[] for _ in cfg['items']],'date':'','signature_image':'','locked':False,'completed_at':''} for name in cfg['periods']}
        d['observations']=''
        if list(cfg['periods'])==['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']:
            # 1 documento por dia: cada inspeção diária nasce já presa ao dia de hoje.
            wd=cfg['periods'][local_today().weekday()]
            d['day_mode']=True; d['day_period']=wd
            d['periods'][wd]['date']=local_today().strftime('%d/%m/%Y')
        if cfg.get('nonconformities'):
            d['nonconformities']=[{'item':'','action':'','responsible':'','date':''} for _ in range(int(cfg['nonconformities']))]
    else:
        d['inspection_date']=local_today().strftime('%d/%m/%Y')
        d['rows']=[{'answer':'','evidence':'','action':'','photos':[]} for _ in cfg['items']]
        d['signature_image']=''
        if kind=='loto':
            d['workers']=[{
                'participant_id':'','participant_user_id':'','cpf':'','company':'','worker':'','role':'','time':'','signature_image':''
            }]
            d['improvements_answer']=''
            d['improvements_description']=''
    return d


def inspection_view(kind: str, data: dict) -> dict:
    cfg=INSPECTION_MODULES[kind]; d=dict(data)
    if kind=='height_kit':
        d['cluster'],d['site']=split_separate_cluster_site(d.get('cluster',''),d.get('site',''))
    for key,_label in cfg.get('fields',[]): d.setdefault(key,'')
    if cfg.get('month_year'):
        d.setdefault('month',f'{local_today().month:02d}'); d.setdefault('year',str(local_today().year))
    if cfg['mode'] in {'daily','weekly'}:
        d.setdefault('periods',{})
        for name in cfg['periods']:
            info=d['periods'].setdefault(name,{})
            info['answers']=(list(info.get('answers',[]))+['']*len(cfg['items']))[:len(cfg['items'])]
            info.setdefault('date',''); info['date_input']=date_input(info.get('date',''))
            info.setdefault('signature_image','')
            raw_photos=(list(info.get('photos') or [])+[[] for _ in cfg['items']])[:len(cfg['items'])]
            info['photos']=[([clean(x) for x in row if clean(x)][:3] if isinstance(row,list) else ([clean(row)] if clean(row) else [])) for row in raw_photos]
            # V36.17.51: preenchimento completo deixa o período pronto, mas só o botão Finalizar bloqueia.
            info['locked']=bool(info.get('locked'))
            info.setdefault('completed_at','')
        # V36.17.52: nos checklists por dia, somente o dia real de hoje fica liberado.
        week_days = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
        if d.get('day_mode') and d.get('day_period') in cfg['periods']:
            active_period_index = list(cfg['periods']).index(d['day_period'])
            if bool((d['periods'].get(d['day_period']) or {}).get('locked')):
                active_period_index = -1
        elif list(cfg['periods']) == week_days:
            active_period_index = local_today().weekday()
            if bool((d['periods'].get(cfg['periods'][active_period_index]) or {}).get('locked')):
                active_period_index = -1
        else:
            active_period_index = next((i for i, name in enumerate(cfg['periods']) if not bool((d['periods'].get(name) or {}).get('locked'))), -1)
        for i, name in enumerate(cfg['periods']):
            d['periods'][name]['editable'] = (i == active_period_index)
        d['active_period_index'] = active_period_index
        d.setdefault('observations','')
        d['header_locked']=any(bool((d['periods'].get(name) or {}).get('locked')) for name in cfg['periods'])
        if cfg.get('nonconformities'):
            n=int(cfg['nonconformities']); d.setdefault('nonconformities',[])
            d['nonconformities']=(list(d['nonconformities'])+[{} for _ in range(n)])[:n]
            for row in d['nonconformities']:
                for k in ('item','action','responsible','date'): row.setdefault(k,'')
                row['date_input']=date_input(row.get('date',''))
    else:
        d.setdefault('inspection_date',local_today().strftime('%d/%m/%Y')); d['inspection_date_input']=date_input(d.get('inspection_date',''))
        d.setdefault('rows',[]); d['rows']=(list(d['rows'])+[{} for _ in cfg['items']])[:len(cfg['items'])]
        for row in d['rows']:
            row.setdefault('answer',''); row.setdefault('evidence',''); row.setdefault('action',''); row['photos']=[clean(x) for x in (row.get('photos') or []) if clean(x)][:3]
        d.setdefault('signature_image','')
        if kind=='loto':
            # V36.18.32 — Parte 2 da planilha oficial: trabalhadores afetados + melhorias.
            legacy_workers=clean(d.get('affected_workers'))
            workers=list(d.get('workers') or [])
            if not workers and legacy_workers:
                workers=[{'participant_id':'','participant_user_id':'','cpf':'','company':'','worker':legacy_workers,'role':'','time':'','signature_image':''}]
            if not workers:
                workers=[{'participant_id':'','participant_user_id':'','cpf':'','company':'','worker':'','role':'','time':'','signature_image':''}]
            normalized=[]
            for worker in workers[:30]:
                w=dict(worker or {})
                for key in ('participant_id','participant_user_id','cpf','company','worker','role','time','signature_image'):
                    w.setdefault(key,'')
                normalized.append(w)
            d['workers']=normalized
            d.setdefault('improvements_answer','')
            d.setdefault('improvements_description',clean(d.get('improvements')))
    return d


@app.get('/inspection/{kind}/new',response_class=HTMLResponse)
def inspection_new(request: Request,kind: str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in INSPECTION_MODULES: raise HTTPException(404)
    if kind=='height_kit':
        inspection_clusters,inspection_cluster_sites=separate_clusters_for_user(user)
    else:
        inspection_clusters,inspection_cluster_sites=combined_clusters_for_user(user),{}
    _idata=inspection_defaults(kind)
    _fkeys={k for k,_l in INSPECTION_MODULES[kind].get('fields',[])}
    if kind=='height_kit': prefill_location(user,_idata)
    elif 'cluster_site' in _fkeys: prefill_location(user,_idata,combined_key='cluster_site',options=inspection_clusters)
    elif 'cluster' in _fkeys: prefill_location(user,_idata,combined_key='cluster',options=inspection_clusters)
    return templates.TemplateResponse(request,'inspection_form.html',context(request,cfg=INSPECTION_MODULES[kind],kind=kind,data=inspection_view(kind,_idata),doc=None,now_date=local_today().strftime('%Y-%m-%d'),clusters=inspection_clusters,cluster_sites=inspection_cluster_sites))


@app.get('/inspection/{kind}/{doc_id}/edit',response_class=HTMLResponse)
def inspection_edit(request: Request,kind: str,doc_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in INSPECTION_MODULES: raise HTTPException(404)
    doc=get_document(doc_id)
    if doc.kind!=kind: raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para acessar este documento.')
    admin_mode=False
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    if kind=='height_kit':
        inspection_clusters,inspection_cluster_sites=separate_clusters_for_user(user)
    else:
        inspection_clusters,inspection_cluster_sites=combined_clusters_for_user(user),{}
    return templates.TemplateResponse(request,'inspection_form.html',context(request,cfg=INSPECTION_MODULES[kind],kind=kind,data=inspection_view(kind,doc_data(doc)),doc=doc,now_date=local_today().strftime('%Y-%m-%d'),clusters=inspection_clusters,cluster_sites=inspection_cluster_sites,admin_edit=admin_mode))


async def parse_inspection(request: Request,kind: str,old:dict):
    cfg=INSPECTION_MODULES[kind]; form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    d={'code':old.get('code') or next_code(kind),'status':old.get('status','Rascunho'),'activity':cfg['short']}
    for key,_label in cfg.get('fields',[]): d[key]=clean(form.get(key))
    oldperiods=old.get('periods',{}) or {}
    if old.get('day_mode') or (not old and list(cfg.get('periods') or [])==['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']):
        d['day_mode']=True
        d['day_period']=old.get('day_period') or (cfg['periods'][local_today().weekday()] if cfg.get('periods') else '')
    has_locked_period=False
    if cfg['mode'] in {'daily','weekly'}:
        for period_name in cfg['periods']:
            prev=oldperiods.get(period_name,{}) or {}
            prev_answers=(list(prev.get('answers',[]))+['']*len(cfg['items']))[:len(cfg['items'])]
            if bool(prev.get('locked')):
                has_locked_period=True
                break
        if has_locked_period:
            for key,_label in cfg.get('fields',[]): d[key]=old.get(key,d.get(key,''))
    if kind=='height_kit':
        d['cluster'],d['site']=sanitize_separate_cluster_site(d.get('cluster',''),d.get('site',''))
    # Mapeia campos principais para as colunas de busca do painel.
    if kind=='hoist':
        d['cluster']=d.get('cluster_site',''); d['site']=d.get('turbine','')
    elif kind=='light_vehicle':
        d['cluster']=d.get('cluster',''); d['site']=d.get('local',''); d['activity']=f"Veículo leve {d.get('vehicle','')} {d.get('plate','')}".strip()
    elif kind=='height_kit':
        d['cluster']=d.get('cluster',''); d['site']=d.get('site',''); d['activity']=f"Kit trabalho em altura {d.get('model','')}".strip()
    elif kind=='safety_belt':
        d['cluster']=d.get('unit',''); d['site']=''; d['activity']=f"Checklist de Cinto de Segurança {d.get('model','')}".strip()
    elif kind in {'grinder','drill','rotary_hammer','circular_saw','marble_saw','welding_machine'}:
        d['cluster']=d.get('cluster',''); d['site']=d.get('local',''); d['activity']='Equipamentos SPIQ '+' / '.join(x for x in (d.get('model_belt'),d.get('model_pos'),d.get('model_y'),d.get('model_arr')) if x)
    elif kind=='spiq':
        d['cluster']=d.get('cluster',''); d['site']=d.get('local',''); d['activity']='Equipamentos SPIQ '+' / '.join(x for x in (d.get('model_belt'),d.get('model_pos'),d.get('model_y'),d.get('model_arr')) if x)
    elif kind=='lifting_accessories':
        d['cluster']=d.get('unit',''); d['site']=''; d['activity']=f"{cfg['short']} {d.get('company','')}".strip()
    elif kind=='loto':
        d['cluster']=d.get('park',''); d['site']=d.get('aeg_number',''); d['activity']=f"LOTO {d.get('aeg_number','')} {d.get('work_description','')}".strip()
    else:
        d['cluster']=d.get('cluster',''); d['site']=d.get('park',''); d['activity']=f"Climber Assist {d.get('turbine','')}".strip()
    if cfg.get('month_year'):
        if has_locked_period:
            d['month']=old.get('month',''); d['year']=old.get('year','')
        else:
            d['month']=clean(form.get('month')); d['year']=clean(form.get('year'))
    action=clean(form.get('action')) or 'draft'
    active=int(clean(form.get('active_period')) or '0')
    if cfg['mode'] in {'daily','weekly'}:
        d['observations']=clean(form.get('observations')); d['periods']={}
        for pi,name in enumerate(cfg['periods']):
            prev=oldperiods.get(name,{}) or {}
            prev_answers=(list(prev.get('answers',[]))+['']*len(cfg['items']))[:len(cfg['items'])]
            prev_locked=bool(prev.get('locked'))
            week_days = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
            if d.get('day_mode') and d.get('day_period') in cfg['periods']:
                allowed_period = list(cfg['periods']).index(d['day_period'])
            elif list(cfg['periods']) == week_days:
                allowed_period = local_today().weekday()
            else:
                allowed_period = next((i for i, pname in enumerate(cfg['periods']) if not bool((oldperiods.get(pname,{}) or {}).get('locked'))), -1)
            if prev_locked or pi != allowed_period:
                # V36.17.52: concluídos e dias fora do dia atual são imutáveis no servidor.
                d['periods'][name]={
                    'answers':prev_answers,
                    'date':prev.get('date',''),
                    'signature_image':prev.get('signature_image',''),
                    'photos':(list(prev.get('photos') or [])+[[] for _ in cfg['items']])[:len(cfg['items'])],
                    'visto':prev.get('visto') or ('RUBRICA' if prev.get('signature_image') else ''),
                    'locked':prev_locked,
                    'completed_at':prev.get('completed_at',''),
                }
                continue
            answers=[clean(form.get(f'period_{pi}_item_{i}')) for i in range(len(cfg['items']))]
            if clean(form.get('fill_na'))=='1' and clean(form.get('action'))=='complete_period' and pi==active:
                answers=[x if x in {'C','NC','NA'} else 'NA' for x in answers]  # confirmado pelo usuário no navegador
            rawdate=clean(form.get(f'period_{pi}_date')); datebr=br_date(rawdate) if rawdate else clean(prev.get('date'))
            if d.get('day_mode'): datebr=clean(prev.get('date')) or local_today().strftime('%d/%m/%Y')
            sig=save_signature(form.get(f'sig_period_{pi}'),prev.get('signature_image',''),f"{d['code']}_{kind}_{pi}")
            requested_lock=clean(form.get(f'period_{pi}_locked'))=='1'
            prev_photos=(list(prev.get('photos') or [])+[[] for _ in cfg['items']])[:len(cfg['items'])]
            photos=[]
            for ii in range(len(cfg['items'])):
                kept=[clean(x) for x in (prev_photos[ii] if isinstance(prev_photos[ii],list) else []) if clean(x)][:3]
                for upload in form.getlist(f'period_{pi}_photo_{ii}'):
                    if len(kept)>=3: break
                    if getattr(upload,'filename',''):
                        _saved=await save_photo_or_flash(request,upload,f"{d['code']}_{kind}_{pi}_{ii+1}")
                        if _saved: kept.append(_saved)
                photos.append(kept[:3])
            info={'answers':answers,'date':datebr,'signature_image':sig,'photos':photos,'visto':'RUBRICA' if sig else '','locked':False,'completed_at':''}
            if requested_lock and bool(sig) and bool(datebr) and len(answers)==len(cfg['items']) and all(a in {'C','NC','NA'} for a in answers):
                info['locked']=True
                info['completed_at']=now().isoformat()
            d['periods'][name]=info
        # V36.17.53: somente o dia real atual pode ser finalizado nos checklists Segunda-Domingo.
        if action=='complete_period' and cfg['periods']:
            active=max(0,min(active,len(cfg['periods'])-1))
            week_days = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
            if d.get('day_mode'):
                allowed_period = list(cfg['periods']).index(d['day_period'])
                if active != allowed_period:
                    raise HTTPException(400, f'Este documento é do dia {d["day_period"]}.')
            elif list(cfg['periods']) == week_days:
                allowed_period = local_today().weekday()
                if active != allowed_period:
                    raise HTTPException(400, f'Somente {cfg["periods"][allowed_period]} está liberada para preenchimento hoje.')
            active_name=cfg['periods'][active]
            # A data do dia em execução é sempre a data real atual; não aceita repetição/manual.
            if d.get('day_mode'):
                d['periods'][active_name]['date']=clean(d['periods'][active_name].get('date')) or local_today().strftime('%d/%m/%Y')
            elif list(cfg['periods']) == week_days:
                d['periods'][active_name]['date']=local_today().strftime('%d/%m/%Y')
            elif not clean(d['periods'][active_name].get('date')):
                d['periods'][active_name]['date']=local_today().strftime('%d/%m/%Y')
        if cfg.get('nonconformities'):
            rows=[]
            for i in range(int(cfg['nonconformities'])):
                raw=clean(form.get(f'nc_date_{i}'))
                rows.append({'item':clean(form.get(f'nc_item_{i}')),'action':clean(form.get(f'nc_action_{i}')),'responsible':clean(form.get(f'nc_responsible_{i}')),'date':br_date(raw) if raw else ''})
            d['nonconformities']=rows
    else:
        rawdate=clean(form.get('inspection_date')); d['inspection_date']=br_date(rawdate) if rawdate else ''
        d['rows']=[]
        for i,_item in enumerate(cfg['items']):
            prevrow=((old.get('rows') or [])+[{} for _ in cfg['items']])[i] or {}
            photos=[clean(x) for x in (prevrow.get('photos') or []) if clean(x)][:3]
            for upload in form.getlist(f'row_photo_{i}'):
                if len(photos)>=3: break
                if getattr(upload,'filename',''):
                    _saved=await save_photo_or_flash(request,upload,f"{d['code']}_{kind}_{i+1}")
                    if _saved: photos.append(_saved)
            d['rows'].append({'answer':clean(form.get(f'row_answer_{i}')),'evidence':clean(form.get(f'row_evidence_{i}')),'action':clean(form.get(f'row_action_{i}')),'photos':photos[:3]})
        d['signature_image']=save_signature(form.get('sig_responsible'),old.get('signature_image',''),f"{d['code']}_{kind}_responsible")
        if kind=='loto':
            raw_indices=clean(form.get('loto_worker_indices'))
            indices=[]
            for token in raw_indices.split(','):
                token=token.strip()
                if token.isdigit():
                    idx=int(token)
                    if idx not in indices and len(indices)<30: indices.append(idx)
            if not indices:
                try:
                    count=max(1,min(30,int(clean(form.get('loto_worker_count')) or '1')))
                except Exception:
                    count=1
                indices=list(range(count))

            old_workers=list(old.get('workers') or [])
            old_by_participant={clean(w.get('participant_id')):w for w in old_workers if clean((w or {}).get('participant_id'))}
            old_by_cpf={cpf_digits(w.get('cpf')):w for w in old_workers if cpf_digits((w or {}).get('cpf'))}
            workers=[]; seen=set()
            with SessionLocal() as db:
                for idx in indices:
                    participant_id=clean(form.get(f'loto_worker_{idx}_participant_id'))
                    participant_user_id=clean(form.get(f'loto_worker_{idx}_user_id'))
                    cpf=clean(form.get(f'loto_worker_{idx}_cpf'))
                    company=clean(form.get(f'loto_worker_{idx}_company'))
                    worker_name=clean(form.get(f'loto_worker_{idx}_worker'))
                    role=clean(form.get(f'loto_worker_{idx}_role'))
                    work_time=clean(form.get(f'loto_worker_{idx}_time'))
                    prev=old_by_participant.get(participant_id) or old_by_cpf.get(cpf_digits(cpf)) or {}
                    signature=save_signature(form.get(f'sig_loto_worker_{idx}'),prev.get('signature_image',''),f"{d['code']}_loto_worker_{idx+1}")
                    if not any((participant_id,cpf,company,worker_name,role,work_time,signature)):
                        continue
                    # Quando o participante veio do cadastro, o servidor substitui os dados recebidos
                    # pelos dados oficiais para evitar alteração manual do nome/empresa/função no POST.
                    valid_participant=False
                    if participant_id.isdigit():
                        participant=db.get(Participant,int(participant_id))
                        if participant and participant.active:
                            participant_company=db.get(Company,participant.company_id)
                            if participant_company and participant_company.active:
                                valid_participant=True
                                participant_user_id=str(participant.user_id or '')
                                cpf=cpf_format(participant.cpf)
                                company=participant_company.name
                                worker_name=participant.full_name
                                role=participant.job_title or ''
                    if not valid_participant:
                        participant_id=''
                        participant_user_id=''
                    key=participant_id or cpf_digits(cpf) or _normalize_person_name(worker_name)
                    if key and key in seen:
                        continue
                    if key: seen.add(key)
                    workers.append({
                        'participant_id':participant_id,'participant_user_id':participant_user_id,'cpf':cpf,
                        'company':company,'worker':worker_name,'role':role,'time':work_time,'signature_image':signature,
                    })
            d['workers']=workers
            d['improvements_answer']=clean(form.get('improvements_answer')).upper()
            if d['improvements_answer']=='NAO': d['improvements_answer']='NÃO'
            d['improvements_description']=clean(form.get('improvements_description'))
            # Preserva os campos legados apenas para documentos antigos ainda em rascunho.
            d['affected_workers']=clean(old.get('affected_workers'))
            d['improvements']=clean(old.get('improvements'))
    return d,action,active


def validate_inspection_dates(kind: str, d: dict, old: dict|None=None):
    cfg=INSPECTION_MODULES[kind]
    today=local_today(); old=old or {}
    fields=[]
    if cfg['mode'] in {'daily','weekly'}:
        old_periods=old.get('periods',{}) or {}
        for name,info in (d.get('periods') or {}).items():
            fields.append((f'{name} - data da inspeção',info.get('date'),(old_periods.get(name) or {}).get('date')))
        old_nc=old.get('nonconformities',[]) or []
        for i,row in enumerate(d.get('nonconformities') or [],1):
            prev=old_nc[i-1] if i-1<len(old_nc) else {}
            fields.append((f'Não conformidade {i} - data',row.get('date'),prev.get('date')))
    else:
        fields.append(('Data da inspeção',d.get('inspection_date'),old.get('inspection_date')))
    for label,raw,previous in fields:
        if not clean(raw): continue
        parsed=parse_date_br(raw)
        unchanged=False
        if clean(previous):
            try: unchanged=parse_date_br(previous)==parsed
            except Exception: unchanged=False
        if parsed<today and not unchanged:
            raise ValueError(f'{label}: data retroativa não permitida ({parsed.strftime("%d/%m/%Y")}).')


def inspection_period_complete(info: dict, item_count: int) -> bool:
    answers=list(info.get('answers',[]))
    return bool(info.get('signature_image')) and bool(info.get('date')) and len(answers)==item_count and all(a in {'C','NC','NA'} for a in answers)


@app.get('/inspection/{kind}/{doc_id}/photo/{period_idx}/{item_idx}/{photo_idx}')
def inspection_photo(request: Request, kind: str, doc_id: int, period_idx: int, item_idx: int, photo_idx: int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in INSPECTION_MODULES: raise HTTPException(404)
    doc=get_document(doc_id)
    if doc.kind!=kind or not user_can_access_document(user,doc): raise HTTPException(403)
    data=inspection_view(kind,doc_data(doc)); cfg=INSPECTION_MODULES[kind]
    if cfg['mode'] in {'daily','weekly'}:
        if period_idx<0 or period_idx>=len(cfg['periods']): raise HTTPException(404)
        photos=((data['periods'][cfg['periods'][period_idx]].get('photos') or [])+[[] for _ in cfg['items']])
        row=photos[item_idx] if 0<=item_idx<len(cfg['items']) else []
    else:
        if item_idx<0 or item_idx>=len(data.get('rows') or []): raise HTTPException(404)
        row=(data['rows'][item_idx].get('photos') or [])
    if photo_idx<0 or photo_idx>=len(row): raise HTTPException(404)
    path=(STORAGE_DIR/Path(row[photo_idx])).resolve()
    if EVIDENCE_DIR not in path.parents or not path.exists(): raise HTTPException(404)
    return FileResponse(path,media_type='image/png',headers={'Cache-Control':'private, no-store'})


def _matching_daily_inspection_draft(user: User, kind: str, data: dict) -> Document|None:
    """Evita rascunhos duplicados por duplo envio nos dois checklists de altura."""
    # Permitido criar várias inspeções do mesmo tipo/equipamento no mesmo dia.
    # O duplo envio já é evitado no navegador (submit-feedback.js).
    return None
    if kind not in {'height_kit','safety_belt'}:
        return None
    if kind=='height_kit':
        keys=('cluster','site','brand','model','company','month','year')
    else:
        keys=('unit','manufacturer','model','responsible')
    fingerprint=tuple(clean(data.get(k)).casefold() for k in keys)
    if not any(fingerprint):
        return None
    day_start=now().replace(hour=0,minute=0,second=0,microsecond=0)
    with SessionLocal() as db:
        rows=(db.query(Document)
              .filter(Document.kind==kind,Document.created_by==user.id,Document.status=='Rascunho',Document.created_at>=day_start)
              .order_by(desc(Document.updated_at)).limit(20).all())
        for row in rows:
            rdata=doc_data(row)
            other=tuple(clean(rdata.get(k)).casefold() for k in keys)
            if other==fingerprint:
                db.expunge(row); return row
    return None

def _wrap_text_pdf(text: str, width: float, fontsize: float=9.0, fontname: str='helv') -> list[str]:
    lines=[]; current=''
    for word in clean(text).split():
        trial=(current+' '+word).strip()
        if fitz.get_text_length(trial,fontname=fontname,fontsize=fontsize)<=width:
            current=trial
        else:
            if current: lines.append(current)
            current=word
    if current: lines.append(current)
    return lines


def build_inspection_day_pdf(user: User, day_br: str) -> bytes|None:
    """PDF único com todos os checklists periódicos do dia selecionado (itens, respostas, assinatura e fotos)."""
    from .pdfgen import _sig_abs
    kinds=[k for k,c in INSPECTION_MODULES.items() if c.get('mode') in {'daily','weekly'}]
    entries=[]
    with SessionLocal() as db:
        rows=db.query(Document).filter(Document.kind.in_(kinds)).order_by(Document.updated_at.desc()).limit(3000).all()
        for row in rows: db.expunge(row)
    for doc in rows:
        if not user_can_access_document(user,doc): continue
        cfg=INSPECTION_MODULES[doc.kind]
        data=inspection_view(doc.kind,doc_data(doc))
        for name in cfg['periods']:
            info=(data.get('periods') or {}).get(name) or {}
            if clean(info.get('date'))!=day_br: continue
            # Só entra na folha do dia o checklist realmente concluído (todas as opções + rubrica).
            if not inspection_period_complete(info,len(cfg['items'])): continue
            entries.append((doc,cfg,data,name,info))
    if not entries: return None
    pdf=fitz.open(); W,H=595.0,842.0; M=42.0
    def new_page(title):
        pg=pdf.new_page(width=W,height=H)
        pg.insert_text((M,40),title,fontsize=12,fontname='hebo')
        pg.draw_line((M,48),(W-M,48),color=(0.95,0.33,0.29),width=1.4)
        return pg,64.0
    label={'C':'Conforme','NC':'NÃO CONFORME','NA':'N/A'}
    for doc,cfg,data,name,info in entries:
        # Folha padrão (mesmo layout do PDF individual do dia); o layout simples abaixo é só contingência.
        try:
            if name not in VEHICLE_DAYS: raise ValueError('período não diário')
            d2=dict(data); d2['day_mode']=True; d2['day_period']=name; d2['periods']={name:info}; d2.setdefault('code',doc_reference_code(doc))
            tmp_one=STORAGE_DIR/'tmp'/f'_dia_{doc.id}_{abs(hash(name))}.pdf'; tmp_one.parent.mkdir(parents=True,exist_ok=True)
            generate_day_checklist(doc.kind,d2,tmp_one)
            one=fitz.open(str(tmp_one)); pdf.insert_pdf(one); one.close(); tmp_one.unlink(missing_ok=True)
            continue
        except Exception:
            pass
        titulo=f"{DOCUMENT_TITLES.get(doc.kind,cfg.get('short',doc.kind))} — {day_br}"
        pg,y=new_page(titulo[:80])
        meta=[f"Documento: {doc_reference_code(doc)}   |   Dia: {name}   |   Data: {day_br}"]
        ident=' | '.join(f"{lab}: {clean(data.get(key))}" for key,lab in cfg.get('fields',[]) if clean(data.get(key)))
        if ident: meta.append(ident)
        for line in meta:
            for sub in _wrap_text_pdf(line,W-2*M,9):
                pg.insert_text((M,y),sub,fontsize=9,fontname='helv'); y+=12
        y+=8
        for idx,item in enumerate(cfg['items']):
            texto=f"{idx+1:02d}. {item[0]}"
            lines=_wrap_text_pdf(texto,W-2*M-95,8.5)
            photos=[p for p in ((info.get('photos') or [])+[[] for _ in cfg['items']])[idx] if clean(p)][:3]
            need=max(len(lines)*11,12)+(62 if photos else 0)+6
            if y+need>H-50:
                pg,y=new_page(titulo[:60]+' (continuação)')
            ans=clean((info.get('answers') or [''])[idx] if idx<len(info.get('answers') or []) else '')
            y0=y
            for ln in lines:
                pg.insert_text((M,y+8),ln,fontsize=8.5,fontname='helv'); y+=11
            pg.insert_text((W-M-85,y0+8),label.get(ans,'—'),fontsize=8.5,fontname='hebo',color=((0.75,0.1,0.1) if ans=='NC' else (0,0,0)))
            if photos:
                x=M+8
                for ph in photos:
                    try:
                        pth=(STORAGE_DIR/Path(ph)).resolve()
                        if EVIDENCE_DIR in pth.parents and pth.exists():
                            pg.insert_image(fitz.Rect(x,y+2,x+56,y+58),filename=str(pth),keep_proportion=True)
                            x+=62
                    except Exception: pass
                y+=62
            y+=6
        if y+70>H-50: pg,y=new_page(titulo[:60]+' (continuação)')
        pg.insert_text((M,y+10),'Assinatura / rubrica:',fontsize=9,fontname='hebo')
        sig=_sig_abs(info.get('signature_image'))
        if sig:
            try: pg.insert_image(fitz.Rect(M+110,y-6,M+260,y+36),filename=str(sig),keep_proportion=True)
            except Exception: pass
        if clean(info.get('completed_at')):
            pg.insert_text((M+280,y+10),f"Concluído em: {clean(info.get('completed_at'))}",fontsize=9,fontname='helv')
        if clean(data.get('observations')):
            y+=48
            pg.insert_text((M,y),'Observações:',fontsize=9,fontname='hebo'); y+=13
            for ln in _wrap_text_pdf(data.get('observations'),W-2*M,9)[:12]:
                if y>H-40: break
                pg.insert_text((M,y),ln,fontsize=9,fontname='helv'); y+=12
    out=pdf.tobytes(garbage=3,deflate=True); pdf.close()
    return out


@app.get('/inspecoes/dia-pdf')
def inspections_day_pdf(request: Request, date: str=''):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    raw=clean(date)
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):
            day_br=datetime.strptime(raw,'%Y-%m-%d').strftime('%d/%m/%Y')
        else:
            day_br=datetime.strptime(raw,'%d/%m/%Y').strftime('%d/%m/%Y')
    except Exception:
        flash(request,'Data inválida para gerar o PDF do dia.','error')
        return RedirectResponse('/',303)
    try:
        content=build_inspection_day_pdf(user,day_br)
    except Exception as exc:
        audit(user.id,'erro_pdf_checklists_dia',f'{day_br}: {exc}')
        flash(request,'Não foi possível gerar o PDF dos checklists do dia.','error')
        return RedirectResponse('/',303)
    if not content:
        flash(request,f'Nenhum checklist preenchido em {day_br}.','info')
        return RedirectResponse('/',303)
    fname=f"Checklists_{day_br.replace('/','-')}.pdf"
    is_navigation=((request.headers.get('sec-fetch-dest') or '').lower()=='document' or 'text/html' in (request.headers.get('accept') or '').lower())
    wants_preview=bool(request.query_params.get('preview_meta') or request.query_params.get('preview_page'))
    if not wants_preview and (request.query_params.get('raw')=='1' or not is_navigation):
        audit(user.id,'pdf_checklists_dia',day_br)
        return Response(content,media_type='application/pdf',headers={'Content-Disposition':f'inline; filename="{fname}"','Cache-Control':'private, no-store'})
    # Visualizador interno (mesmo da APR): fundo claro e botão X para fechar.
    tmp_dir=STORAGE_DIR/'tmp'; tmp_dir.mkdir(parents=True,exist_ok=True)
    tmp_pdf=tmp_dir/f"dia_{user.id}_{day_br.replace('/','-')}.pdf"
    tmp_pdf.write_bytes(content)
    preview=pdf_preview_response(request,tmp_pdf)
    if preview is not None: return preview
    audit(user.id,'pdf_checklists_dia',day_br)
    return templates.TemplateResponse(request,'pdf_viewer.html',context(
        request,doc=None,pdf_title=f'Checklists do dia {day_br}',pdf_error='',
        raw_pdf_url=f"/inspecoes/dia-pdf?date={raw}&raw=1",daily_signature_url='',
    ))


@app.post('/inspection/{kind}/save')
async def inspection_create_save(request: Request,kind:str):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in INSPECTION_MODULES: raise HTTPException(404)
    d,action,active=await parse_inspection(request,kind,inspection_defaults(kind))
    existing=_matching_daily_inspection_draft(user,kind,d)
    if existing:
        flash(request,'Já existe um rascunho deste mesmo checklist criado hoje. O registro existente foi aberto para evitar duplicidade.','info')
        return RedirectResponse(f'/inspection/{kind}/{existing.id}/edit',303)
    return process_inspection(request,user,None,kind,d,action,active)


@app.post('/inspection/{kind}/{doc_id}/save')
async def inspection_update_save(request: Request,kind:str,doc_id:int):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if kind not in INSPECTION_MODULES: raise HTTPException(404)
    doc=get_document(doc_id)
    if doc.kind!=kind: raise HTTPException(404)
    if not user_can_access_document(user,doc):
        audit(user.id,'acesso_negado_documento',f'doc_id={doc.id} kind={doc.kind}')
        raise HTTPException(403,'Você não tem permissão para editar este documento.')
    if doc.status=='Finalizada': return RedirectResponse(f'/document/{doc.id}/pdf',303)
    d,action,active=await parse_inspection(request,kind,doc_data(doc))
    return process_inspection(request,user,doc,kind,d,action,active)


def process_inspection(request,user,doc,kind,d,action,active):
    cfg=INSPECTION_MODULES[kind]
    old_data=doc_data(doc) if doc else {}
    required=[key for key,_ in cfg.get('fields',[]) if key not in {'leader'}]
    missing_keys=[key for key,_label in cfg.get('fields',[]) if key in required and not clean(d.get(key))]
    missing_labels=[label for key,label in cfg.get('fields',[]) if key in missing_keys]

    try:
        # Registro feito sem internet e enviado depois: a data é a do preenchimento, não a do envio.
        if not request.headers.get('X-SP-Offline-Sync'):
            validate_inspection_dates(kind,d,old_data)
    except Exception as e:
        if cfg['mode'] in {'daily','weekly'}:
            date_fields=[f'period_{i}_date' for i,_ in enumerate(cfg['periods'])]
        else:
            date_fields=['inspection_date']
        saved=save_validation_state(doc,kind,d,user,date_fields,'Rascunho')
        flash(request,str(e)+' O que já foi preenchido foi mantido.','error')
        return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)

    if cfg['mode'] in {'daily','weekly'}:
        if action=='complete_period':
            active=max(0,min(active,len(cfg['periods'])-1)); name=cfg['periods'][active]; info=d['periods'][name]
            blanks=[i+1 for i,a in enumerate(info.get('answers',[])) if a not in {'C','NC','NA'}]
            fields=list(missing_keys)+[f'period_{active}_item_{i-1}' for i in blanks]
            if not info.get('date'): fields.append(f'period_{active}_date')
            if not info.get('signature_image'): fields.append(f'sig_period_{active}')
            missing_photo_idx=[]  # foto de evidência é opcional em todas as inspeções
            if missing_keys or blanks or not info.get('date') or not info.get('signature_image') or missing_photo_idx:
                msg=f'Não é possível concluir {name}. '
                if missing_labels: msg+='Preencha: '+', '.join(missing_labels)+'. '
                if blanks: msg+='Sem seleção: '+', '.join(map(str,blanks))+'. '
                if not info.get('date'): msg+='Informe a data da inspeção. '
                if not info.get('signature_image'): msg+='Faça a rubrica do responsável. '
                if missing_photo_idx: msg+='Anexe foto nos itens aplicáveis: '+', '.join(str(i+1) for i in missing_photo_idx)+'. '
                saved=save_validation_state(doc,kind,d,user,fields,'Rascunho')
                flash(request,msg+'O que já foi preenchido foi mantido.','error')
                return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)
            info['locked']=True
            info['completed_at']=info.get('completed_at') or now().isoformat()
            clear_validation_state(d)
            _fin_periods=[d['day_period']] if d.get('day_mode') else list(cfg['periods'])
            final=all(bool(d['periods'][p].get('locked')) and inspection_period_complete(d['periods'][p],len(cfg['items'])) for p in _fin_periods)
            status='Finalizada' if final else 'Rascunho'; saved=save_doc(doc,kind,d,user,status)
            try: saved=finalize_pdf(saved,d)
            except Exception as e:
                if status=='Finalizada':
                    _rollback_document_after_pdf_failure(saved.id,'Rascunho')
                flash(request,f'Dados salvos, mas o PDF não foi atualizado: {e}. O documento permaneceu em Rascunho para permitir a correção.','error')
                return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)
            audit(user.id,'concluir_inspecao_periodo',f'{saved.code} {name}')
            return RedirectResponse(f'/document/{saved.id}/pdf',303)
        clear_validation_state(d)
        saved=save_doc(doc,kind,d,user,'Rascunho'); flash(request,'Rascunho da inspeção salvo.','success'); return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)

    if action=='finalize':
        fields=list(missing_keys)
        if not d.get('inspection_date'): fields.append('inspection_date')
        loto_issues=[]
        if kind=='loto':
            workers=[w for w in (d.get('workers') or []) if any(clean(w.get(k)) for k in ('participant_id','cpf','company','worker','role','time','signature_image'))]
            if not workers:
                loto_issues.append('Adicione pelo menos um Trabalhador LOTO Afetado.')
                fields.append('loto_workers')
            for wi,w in enumerate(workers,1):
                if not clean(w.get('participant_id')):
                    loto_issues.append(f'Integrante {wi}: selecione um participante cadastrado por CPF ou nome.')
                    fields.append('loto_workers')
                if not clean(w.get('worker')): loto_issues.append(f'Integrante {wi}: nome não informado.')
                if not clean(w.get('role')): loto_issues.append(f'Integrante {wi}: função não informada.')
                if not clean(w.get('time')): loto_issues.append(f'Integrante {wi}: informe o horário.')
                if not clean(w.get('signature_image')): loto_issues.append(f'Integrante {wi}: faça a assinatura/rubrica.')
        blanks=[cfg['items'][i][0] for i,row in enumerate(d['rows']) if row.get('answer') not in {'ATENDE','NAO_ATENDE','NA'}]
        blank_idx=[i for i,row in enumerate(d['rows']) if row.get('answer') not in {'ATENDE','NAO_ATENDE','NA'}]
        corrective=[cfg['items'][i][0] for i,row in enumerate(d['rows']) if row.get('answer')=='NAO_ATENDE' and not clean(row.get('action'))]
        corrective_idx=[i for i,row in enumerate(d['rows']) if row.get('answer')=='NAO_ATENDE' and not clean(row.get('action'))]
        fields += [f'row_answer_{i}' for i in blank_idx] + [f'row_action_{i}' for i in corrective_idx]
        if not d.get('signature_image'): fields.append('sig_responsible')
        missing_photo_idx=[]  # foto de evidência é opcional em todas as inspeções
        if missing_keys or not d.get('inspection_date') or blanks or corrective or not d.get('signature_image') or loto_issues or missing_photo_idx:
            msg='Não é possível finalizar. '
            if missing_labels: msg+='Preencha: '+', '.join(missing_labels)+'. '
            if not d.get('inspection_date'): msg+='Informe a data da inspeção. '
            if blanks: msg+='Itens sem resposta: '+', '.join(blanks)+'. '
            if corrective: msg+='Informe ação corretiva para: '+', '.join(corrective)+'. '
            if not d.get('signature_image'): msg+='Faça a assinatura/rubrica do responsável. '
            if missing_photo_idx: msg+='Anexe foto nos itens aplicáveis: '+', '.join(str(i+1) for i in missing_photo_idx)+'. '
            if loto_issues: msg+=' '.join(loto_issues)+' '
            saved=save_validation_state(doc,kind,d,user,fields,'Rascunho')
            flash(request,msg+'O que já foi preenchido foi mantido.','error')
            return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)
        clear_validation_state(d)
        saved=save_doc(doc,kind,d,user,'Finalizada')
        try: saved=finalize_pdf(saved,d)
        except Exception as e:
            _rollback_document_after_pdf_failure(saved.id,'Rascunho')
            flash(request,f'O PDF não foi gerado: {e}. O documento voltou para Rascunho para você corrigir e tentar novamente.','error')
            return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)
        audit(user.id,'finalizar_inspecao',saved.code); return RedirectResponse(f'/document/{saved.id}/pdf',303)
    clear_validation_state(d)
    saved=save_doc(doc,kind,d,user,'Rascunho'); flash(request,'Rascunho da inspeção salvo.','success'); return RedirectResponse(f'/inspection/{kind}/{saved.id}/edit',303)


# -------------------- Exclusão administrativa de documentos --------------------
def _signature_paths(value: Any):
    """Localiza rubricas armazenadas dentro do JSON do documento."""
    if isinstance(value, dict):
        for v in value.values():
            yield from _signature_paths(v)
    elif isinstance(value, list):
        for v in value:
            yield from _signature_paths(v)
    elif isinstance(value, str):
        normalized=value.replace('\\','/')
        if normalized.startswith(('signatures/','evidence/')):
            yield normalized


def _remove_storage_file(relative_path: str|None):
    if not relative_path:
        return
    try:
        rel=Path(relative_path)
        candidate=(STORAGE_DIR/rel).resolve()
        # Nunca permite que uma exclusão saia da pasta de armazenamento do sistema.
        if STORAGE_DIR == candidate or STORAGE_DIR in candidate.parents:
            if candidate.is_file(): candidate.unlink()
    except Exception:
        pass


@app.post('/admin/documents/{doc_id}/delete')
async def admin_delete_document(request: Request, doc_id: int):
    admin=current_user(request)
    if not admin: return RedirectResponse('/login',303)
    if not is_admin_user(admin): raise HTTPException(status_code=403,detail='Acesso restrito ao administrador')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404,'Documento não encontrado')
        if not user_can_access_document(admin,doc):
            raise HTTPException(403,'Este documento não pertence ao seu Cluster/Site de responsabilidade.')
        if doc.status!='Rascunho':
            raise HTTPException(409,'Somente documentos em Rascunho podem ser excluídos. Para documentos já submetidos, utilize Cancelar documento.')
        code,title,status=doc_reference_code(doc),doc.title,doc.status
        data=doc_data(doc)
        pdf_path=doc.pdf_path
        signature_paths=list(dict.fromkeys(_signature_paths(data)))
        internal_code=doc.code
        db.query(Notification).filter(Notification.document_id==doc_id).delete(synchronize_session=False)
        db.delete(doc); db.commit()
    _remove_storage_file(pdf_path)
    for sig_path in signature_paths:
        _remove_storage_file(sig_path)
    audit(admin.id,'excluir_documento',f'{code} | {title} | {status}')
    flash(request,f'{code} excluído com sucesso.','success')
    return RedirectResponse('/',303)


@app.post('/admin/documents/{doc_id}/cancel')
async def admin_cancel_document(request: Request, doc_id: int):
    admin=current_user(request)
    if not admin: return RedirectResponse('/login',303)
    if not is_admin_user(admin): raise HTTPException(status_code=403,detail='Acesso restrito ao ADM/Super')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    reason=clean(form.get('reason'))
    if not reason:
        flash(request,'Informe o motivo do cancelamento.','error')
        return RedirectResponse('/',303)
    with SessionLocal() as db:
        doc=db.get(Document,doc_id)
        if not doc: raise HTTPException(404,'Documento não encontrado')
        if not user_can_access_document(admin,doc):
            raise HTTPException(403,'Este documento não pertence ao seu Cluster/Site de responsabilidade.')
        if doc.status!='Aguardando aprovação':
            raise HTTPException(409,'Somente documentos já submetidos e aguardando aprovação podem ser cancelados.')
        data=doc_data(doc)
        admin_name=admin.full_name or admin.username
        data['status']='Cancelado'
        data['cancelled_by_user_id']=admin.id
        data['cancelled_by_name']=admin_name
        data['cancelled_at']=now().isoformat(timespec='seconds')
        data['cancellation_reason']=reason
        doc.status='Cancelado'
        doc.data_json=json.dumps(data,ensure_ascii=False)
        doc.updated_at=now()
        db.query(Notification).filter(Notification.document_id==doc.id,Notification.kind=='apr_approval').delete(synchronize_session=False)
        db.commit(); db.refresh(doc); db.expunge(doc)
    notify_document_creator(doc,'document_cancelled',f'{doc_reference_code(doc)} foi cancelado por {admin_name}. Motivo: {reason}',replace=True)
    audit(admin.id,'cancelar_documento',f'{doc_reference_code(doc)} | motivo={reason}')
    flash(request,f'{doc_reference_code(doc)} cancelado. O registro foi preservado no histórico.','success')
    return RedirectResponse('/',303)

# -------------------- Administração --------------------
@app.get('/admin/people',response_class=HTMLResponse)
def people_admin_page(request: Request, company: str=''):
    """V36.18.94 — Gestão de colaboradores reconstruída.

    Diretório único e paginado de colaboradores (participantes) com filtros,
    edição em gaveta lateral, empresas e contas de acesso em abas.
    """
    admin=current_user(request)
    if not admin: return RedirectResponse('/login',303)
    if not is_super_admin(admin): raise HTTPException(403,'Somente o Super Administrador pode acessar esta área.')
    with SessionLocal() as db:
        companies=db.query(Company).order_by(Company.name).all()
        participants=db.query(Participant).order_by(Participant.full_name).all()
        users=db.query(User).filter(User.role!=ROLE_DEV).order_by(User.full_name,User.username).all()
        user_by_id={u.id:u for u in users}
        company_by_id={c.id:c for c in companies}
        counts={}; active_counts={}
        for participant in participants:
            counts[participant.company_id]=counts.get(participant.company_id,0)+1
            if participant.active:
                active_counts[participant.company_id]=active_counts.get(participant.company_id,0)+1
        company_rows=[{'company':c,'participant_count':counts.get(c.id,0),
                       'active_participant_count':active_counts.get(c.id,0)} for c in companies]
        linked_user_ids={p.user_id for p in participants if p.user_id}
        people=[]
        for p in participants:
            comp=company_by_id.get(p.company_id); lu=user_by_id.get(p.user_id) if p.user_id else None
            people.append({
                'id':p.id,'name':p.full_name,'cpf':cpf_format(p.cpf),'cpf_digits':p.cpf,'job':p.job_title or '',
                'cluster':p.cluster or '','site':p.site or '','company_id':p.company_id,'company':comp.name if comp else '—','company_active':bool(comp and comp.active),
                'active':bool(p.active),'user_id':p.user_id or '','username':lu.username if lu else '',
                'user_role':lu.role if lu else '','user_active':bool(lu and lu.active),
                'created':p.created_at.strftime('%d/%m/%Y') if p.created_at else '',
            })
        stats={'companies':len(companies),'active_companies':sum(1 for c in companies if c.active),
               'participants':len(participants),'active_participants':sum(1 for p in participants if p.active),
               'with_login':sum(1 for p in participants if p.user_id),
               'users':len(users),'admins':sum(1 for u in users if u.role in ADMIN_ROLES)}
        bulk_users=[u for u in users if u.role==ROLE_USER and u.id!=admin.id]
        scopes=db.query(UserScope).order_by(UserScope.cluster,UserScope.site).all()
        scope_map={}
        for item in scopes:
            scope_map.setdefault(item.user_id,[]).append((item.cluster,item.site))
        participant_by_user={p.user_id:p for p in participants if p.user_id}
        user_rows=[{'user':u,'participant':participant_by_user.get(u.id),
                    'company':(company_by_id.get(participant_by_user[u.id].company_id).name if u.id in participant_by_user and company_by_id.get(participant_by_user[u.id].company_id) else '')}
                   for u in users]
        free_users=[u for u in users if u.active and u.id not in linked_user_ids]
        active_users=[u for u in users if u.active]
    try: selected_company=int(company or 0)
    except ValueError: selected_company=0
    return templates.TemplateResponse(request,'people_admin.html',context(
        request,company_rows=company_rows,stats=stats,users=users,user_rows=user_rows,bulk_users=bulk_users,
        total=len(bulk_users),scope_map=scope_map,cluster_sites=SEPARATE_CLUSTER_SITES,
        people=people,free_users=free_users,active_users=active_users,selected_company=selected_company,
        role_super=ROLE_SUPER_ADMIN,role_admin=ROLE_ADMIN,role_user=ROLE_USER,
    ))

@app.get('/admin/participants',response_class=HTMLResponse)
def participants_page(request: Request):
    if not current_user(request): return RedirectResponse('/login',303)
    return RedirectResponse('/admin/people#colaboradores',303)


@app.get('/admin/companies/{company_id}/participants',response_class=HTMLResponse)
def company_participants_page(request: Request, company_id: int):
    if not current_user(request): return RedirectResponse('/login',303)
    return RedirectResponse(f'/admin/people?company={company_id}#colaboradores',303)


def cpf_check_digits_ok(value: Any) -> bool:
    """Valida os dígitos verificadores do CPF (usado no cadastro manual)."""
    cpf=cpf_digits(value)
    if len(cpf)!=11 or cpf==cpf[0]*11: return False
    for n in (9,10):
        total=sum(int(cpf[i])*((n+1)-i) for i in range(n))
        digit=(total*10)%11
        if digit==10: digit=0
        if digit!=int(cpf[n]): return False
    return True


# -------------------- Importação/exportação de participantes em Excel --------------------
def _xlsx_cell_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return clean_single_line(value)


def _xlsx_cpf(value: Any) -> str:
    raw=_xlsx_cell_text(value)
    digits=re.sub(r'\D','',raw)
    # Quando o Excel converte CPF numérico que começa com zero, o zero inicial é perdido.
    if digits and len(digits)<11 and raw.replace('.0','').isdigit():
        digits=digits.zfill(11)
    return digits[:11]


def _xlsx_bool(value: Any, default: bool=True) -> bool:
    raw=_xlsx_cell_text(value).casefold()
    if raw in {'não','nao','n','0','false','inativo','inativa'}:
        return False
    if raw in {'sim','s','1','true','ativo','ativa'}:
        return True
    return default


def _participant_excel_workbook(company: Company, rows: list[dict[str,Any]]|None=None, *, template_only: bool=False):
    """Monta o arquivo XLSX usado para baixar modelo/lista atual.

    A senha nunca é exportada. A coluna Senha fica em branco e serve somente
    para criação de um novo login ou redefinição intencional durante o upload.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.worksheet.datavalidation import DataValidation
    except Exception as exc:
        raise HTTPException(500,'Recurso Excel indisponível. Instale as dependências desta versão.') from exc

    wb=Workbook(); ws=wb.active; ws.title='Participantes'
    headers=['Nome completo','CPF','Função','Login','Senha','Ativo','Perfil']
    ws.append(headers)
    for cell in ws[1]:
        cell.font=Font(bold=True,color='FFFFFF')
        cell.fill=PatternFill('solid',fgColor='FF554D')
        cell.alignment=Alignment(horizontal='center',vertical='center')
    ws.freeze_panes='A2'
    widths={'A':34,'B':18,'C':28,'D':25,'E':20,'F':12,'G':22}
    for col,width in widths.items(): ws.column_dimensions[col].width=width
    ws.column_dimensions['B'].number_format='@'

    if template_only:
        ws.append(['Exemplo da Silva','01234567890','Técnico','exemplo.silva','Senha@123','Sim','Usuário'])
        ws.append(['','','','','','',''])
    else:
        for row in rows or []:
            ws.append([
                row.get('full_name',''),
                row.get('cpf',''),
                row.get('job_title',''),
                row.get('username',''),
                '',
                'Sim' if row.get('active',True) else 'Não',
                row.get('role', ROLE_USER),
            ])

    # Mantém CPF como texto para preservar zeros à esquerda.
    for c in ws['B'][1:]: c.number_format='@'
    dv=DataValidation(type='list', formula1='"Sim,Não"', allow_blank=True)
    ws.add_data_validation(dv); dv.add('F2:F5000')
    dv_role=DataValidation(type='list', formula1='"Usuário,Administrador,Super Administrador"', allow_blank=True)
    ws.add_data_validation(dv_role); dv_role.add('G2:G5000')

    notes=wb.create_sheet('Instruções')
    notes['A1']=f'Importação de participantes — {company.name}'
    notes['A1'].font=Font(bold=True,size=14,color='FF554D')
    instructions=[
        'Preencha uma linha por participante.',
        'Nome completo e CPF (11 dígitos) são obrigatórios.',
        'Login é opcional. Se informado e ainda não existir, o Safety Plus cria um usuário comum automaticamente.',
        'Para NOVO login, a Senha deve ter pelo menos 8 caracteres.',
        'Para login já existente, deixe Senha vazia para manter a senha atual. Se preencher, a senha será redefinida.',
        'A senha é usada apenas durante a importação e fica armazenada no banco somente como hash criptográfico.',
        'Ativo aceita Sim/Não. Se ficar vazio, será considerado Sim.',
        'Perfil aceita Usuário, Administrador ou Super Administrador. Se ficar vazio, será considerado Usuário. Por segurança, Administrador importado deve ter seus Clusters/Sites definidos depois em Usuários e acessos.',
        'Não altere os nomes das colunas da primeira linha.',
    ]
    for i,text in enumerate(instructions,3): notes.cell(i,1,text)
    notes.column_dimensions['A'].width=105
    for row in notes.iter_rows(min_row=1,max_row=notes.max_row):
        for cell in row: cell.alignment=Alignment(wrap_text=True,vertical='top')
    return wb


@app.get('/admin/companies/{company_id}/participants/template.xlsx')
def participant_excel_template(request: Request, company_id: int):
    require_super_admin(request)
    with SessionLocal() as db:
        company=db.get(Company,company_id)
        if not company: raise HTTPException(404,'Empresa não encontrada.')
        db.expunge(company)
    wb=_participant_excel_workbook(company,template_only=True)
    buf=io.BytesIO(); wb.save(buf); buf.seek(0)
    filename=safe_filename(f'Modelo_Participantes_{company.name}.xlsx')
    return StreamingResponse(buf,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f'attachment; filename="{filename}"'})


@app.get('/admin/companies/{company_id}/participants/export.xlsx')
def participant_excel_export(request: Request, company_id: int):
    require_super_admin(request)
    with SessionLocal() as db:
        company=db.get(Company,company_id)
        if not company: raise HTTPException(404,'Empresa não encontrada.')
        participants=db.query(Participant).filter(Participant.company_id==company_id).order_by(Participant.full_name).all()
        rows=[]
        for p in participants:
            u=db.get(User,p.user_id) if p.user_id else None
            rows.append({'full_name':p.full_name,'cpf':cpf_format(p.cpf),'job_title':p.job_title or '', 'username':u.username if u else '', 'active':p.active, 'role':u.role if u else ROLE_USER})
        db.expunge(company)
    wb=_participant_excel_workbook(company,rows=rows)
    buf=io.BytesIO(); wb.save(buf); buf.seek(0)
    filename=safe_filename(f'Participantes_{company.name}.xlsx')
    return StreamingResponse(buf,media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',headers={'Content-Disposition':f'attachment; filename="{filename}"'})


@app.post('/admin/companies/{company_id}/participants/import')
async def participant_excel_import(request: Request, company_id: int):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    upload=form.get('participants_file')
    if not upload or not getattr(upload,'filename',''):
        flash(request,'Selecione um arquivo Excel (.xlsx).','error'); return _participants_admin_redirect(company_id)
    filename=str(getattr(upload,'filename','') or '')
    if not filename.lower().endswith('.xlsx'):
        flash(request,'Envie a lista no formato .xlsx.','error'); return _participants_admin_redirect(company_id)
    content=await upload.read()
    if not content:
        flash(request,'O arquivo enviado está vazio.','error'); return _participants_admin_redirect(company_id)
    if len(content)>8*1024*1024:
        flash(request,'A planilha excede o limite de 8 MB.','error'); return _participants_admin_redirect(company_id)
    try:
        from openpyxl import load_workbook
        wb=load_workbook(io.BytesIO(content),read_only=True,data_only=True)
        ws=wb['Participantes'] if 'Participantes' in wb.sheetnames else wb[wb.sheetnames[0]]
    except Exception:
        flash(request,'Não foi possível ler a planilha. Use o botão “Baixar modelo Excel” e tente novamente.','error'); return _participants_admin_redirect(company_id)

    raw_headers=[_xlsx_cell_text(c.value).casefold() for c in next(ws.iter_rows(min_row=1,max_row=1))]
    aliases={
        'nome completo':'name','nome':'name','participante':'name',
        'cpf':'cpf','função':'job','funcao':'job','cargo':'job',
        'login':'login','usuário':'login','usuario':'login','e-mail/login':'login','email/login':'login',
        'senha':'password','password':'password','ativo':'active','ativa':'active',
        'perfil':'role','acesso':'role','tipo de usuário':'role','tipo de usuario':'role',
    }
    colmap={aliases[h]:idx for idx,h in enumerate(raw_headers) if h in aliases}
    if 'name' not in colmap or 'cpf' not in colmap:
        flash(request,'A planilha precisa ter pelo menos as colunas “Nome completo” e “CPF”.','error'); return _participants_admin_redirect(company_id)

    created=updated=users_created=users_password_reset=0
    errors=[]; processed=0
    with SessionLocal() as db:
        company=db.get(Company,company_id)
        if not company or not company.active:
            flash(request,'A empresa precisa estar ativa para importar participantes.','error'); return _participants_admin_redirect(company_id)
        for excel_row,row in enumerate(ws.iter_rows(min_row=2,values_only=True),start=2):
            if processed>=5000:
                errors.append('Limite de 5.000 linhas atingido; as demais não foram processadas.')
                break
            if not any(v not in (None,'') for v in row):
                continue
            processed+=1
            def val(key):
                idx=colmap.get(key)
                return row[idx] if idx is not None and idx<len(row) else ''
            name=_xlsx_cell_text(val('name')); cpf=_xlsx_cpf(val('cpf')); job=_xlsx_cell_text(val('job'))
            login=_xlsx_cell_text(val('login')); password=str(val('password') or '').strip(); active=_xlsx_bool(val('active'),True)
            imported_role=_normalize_user_role(_xlsx_cell_text(val('role')) or ROLE_USER)
            if not name:
                errors.append(f'Linha {excel_row}: nome completo ausente.'); continue
            if not cpf_is_valid(cpf):
                errors.append(f'Linha {excel_row}: CPF deve ter 11 dígitos.'); continue
            try:
                reset_user_id=None
                participant=db.query(Participant).filter(Participant.cpf==cpf).first()
                if participant and participant.company_id!=company_id:
                    errors.append(f'Linha {excel_row}: CPF {cpf_mask(cpf)} já pertence a outra empresa.'); continue

                linked_user=None
                if login:
                    linked_user=db.query(User).filter(User.username==login).first()
                    if linked_user:
                        other=db.query(Participant).filter(Participant.user_id==linked_user.id).first()
                        if other and (not participant or other.id!=participant.id):
                            errors.append(f'Linha {excel_row}: login “{login}” já está vinculado a outro participante.'); continue
                        if password:
                            if len(password)<8:
                                errors.append(f'Linha {excel_row}: senha de “{login}” deve ter pelo menos 8 caracteres.'); continue
                            linked_user.password_hash=hash_password(password); users_password_reset+=1
                            reset_user_id=linked_user.id
                        linked_user.full_name=name
                        # Perfil pode ser informado na planilha. Super Administrador existente nunca é rebaixado por importação.
                        if linked_user.role!=ROLE_SUPER_ADMIN:
                            linked_user.role=imported_role
                            linked_user.active=active
                    else:
                        if len(password)<8:
                            errors.append(f'Linha {excel_row}: novo login “{login}” exige senha com pelo menos 8 caracteres.'); continue
                        linked_user=User(username=login,full_name=name,password_hash=hash_password(password),role=imported_role,active=active)
                        db.add(linked_user); db.flush(); users_created+=1

                if participant:
                    participant.full_name=name; participant.job_title=job; participant.active=active; participant.updated_at=now()
                    if linked_user: participant.user_id=linked_user.id
                    updated+=1
                else:
                    participant=Participant(company_id=company_id,cpf=cpf,full_name=name,job_title=job,user_id=(linked_user.id if linked_user else None),active=active,created_at=now(),updated_at=now())
                    db.add(participant); created+=1
                db.commit()
                if reset_user_id is not None:
                    revoke_password_sessions(STORAGE_DIR,reset_user_id,request)
            except Exception as exc:
                db.rollback()
                errors.append(f'Linha {excel_row}: não foi possível importar este registro.')

    audit(admin.id,'importar_participantes_excel',f'empresa={company_id} | linhas={processed} | novos={created} | atualizados={updated} | usuarios_novos={users_created} | erros={len(errors)}')
    summary=f'Importação concluída: {created} participante(s) novo(s), {updated} atualizado(s), {users_created} usuário(s) criado(s)'
    if users_password_reset: summary+=f', {users_password_reset} senha(s) redefinida(s)'
    summary+='.'
    if errors:
        summary+=f' {len(errors)} linha(s) com problema. ' + ' '.join(errors[:8])
        if len(errors)>8: summary+=f' (+{len(errors)-8} erro(s) não exibidos)'
        flash(request,summary,'error')
    else:
        flash(request,summary,'success')
    return _participants_admin_redirect(company_id)


def _participants_admin_redirect(company_id: int|None=None):
    if company_id:
        return RedirectResponse(f'/admin/people?company={company_id}#colaboradores',303)
    return RedirectResponse('/admin/people#colaboradores',303)


@app.post('/admin/companies/create')
async def company_create(request: Request):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    name=clean_single_line(form.get('name'))
    if not name:
        flash(request,'Informe o nome da empresa.','error'); return RedirectResponse('/admin/people#empresas',303)
    with SessionLocal() as db:
        if db.query(Company).filter(Company.name.ilike(name)).first():
            flash(request,'Essa empresa já está cadastrada.','error'); return RedirectResponse('/admin/people#empresas',303)
        db.add(Company(name=name,active=True,created_at=now(),updated_at=now())); db.commit()
    audit(admin.id,'criar_empresa',name); flash(request,'Empresa cadastrada.','success')
    return RedirectResponse('/admin/people#empresas',303)


@app.post('/admin/companies/{company_id}/update')
async def company_update(request: Request, company_id: int):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    name=clean_single_line(form.get('name')); active=clean(form.get('active'))=='1'
    if not name:
        flash(request,'Informe o nome da empresa.','error'); return _participants_admin_redirect(company_id)
    with SessionLocal() as db:
        company=db.get(Company,company_id)
        if not company: raise HTTPException(404,'Empresa não encontrada.')
        duplicate=db.query(Company).filter(Company.id!=company_id,Company.name.ilike(name)).first()
        if duplicate:
            flash(request,'Já existe outra empresa com esse nome.','error'); return _participants_admin_redirect(company_id)
        company.name=name; company.active=active; company.updated_at=now(); db.commit()
    audit(admin.id,'alterar_empresa',f'{company_id} | {name}'); flash(request,'Empresa atualizada.','success')
    return _participants_admin_redirect(company_id)


@app.post('/admin/companies/{company_id}/delete')
async def company_delete(request: Request, company_id: int):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    # Exclui exclusivamente o cadastro da empresa e os participantes associados.
    # Usuários de login, documentos, PDFs e históricos não são apagados.
    try:
        with SessionLocal.begin() as db:
            # Bloqueia a empresa durante a remoção para evitar novos participantes
            # simultâneos (PostgreSQL). Em SQLite o bloqueio é gerenciado pelo banco.
            query=db.query(Company).filter(Company.id==company_id)
            if db.bind.dialect.name == 'postgresql':
                query=query.with_for_update()
            company=query.first()
            if not company:
                flash(request,'Empresa não encontrada ou já removida.','error')
                return RedirectResponse('/admin/people#empresas',303)
            name=company.name
            participant_count=db.query(Participant).filter(Participant.company_id==company_id).count()
            db.execute(delete(Participant).where(Participant.company_id==company_id))
            db.delete(company)
            db.flush()
            db.add(AuditLog(user_id=admin.id,action='excluir_empresa',
                            detail=f'{company_id} | {name} | participantes={participant_count}',
                            created_at=now()))
        msg=f'Empresa “{name}” removida do cadastro.'
        if participant_count:
            msg+=f' {participant_count} participante(s) também removido(s). Documentos antigos preservados.'
        flash(request,msg,'success')
    except SQLAlchemyError:
        # Rollback automático da transação. Nunca expor dados internos do banco.
        import logging
        logging.getLogger(__name__).exception('Falha ao remover empresa id=%s',company_id)
        flash(request,'Não foi possível remover a empresa. Nenhum cadastro foi excluído. Consulte os logs do servidor.','error')
    return RedirectResponse('/admin/people#empresas',303)


ASSIGNABLE_ROLES={ROLE_USER,ROLE_ADMIN,ROLE_SUPER_ADMIN}

def _form_role(form) -> str:
    """Perfil escolhido em Colaboradores. DEV nunca é atribuído por aqui."""
    value=clean(form.get('role'))
    return value if value in ASSIGNABLE_ROLES else ''

@app.post('/admin/participants/create')
async def participant_create(request: Request):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: company_id=int(clean(form.get('company_id')) or 0)
    except Exception: company_id=0
    full_name=clean_single_line(form.get('full_name')); cpf=cpf_digits(form.get('cpf')); job_title=clean_single_line(form.get('job_title'))
    try: user_id=int(clean(form.get('user_id')) or 0)
    except Exception: user_id=0
    if not company_id:
        flash(request,'Selecione a empresa do participante.','error'); return RedirectResponse('/admin/participants',303)
    if not full_name:
        flash(request,'Informe o nome completo do participante.','error'); return _participants_admin_redirect(company_id)
    if not cpf_is_valid(cpf):
        flash(request,'Informe os 11 números do CPF. Pontos e hífen são opcionais e serão formatados automaticamente.','error'); return _participants_admin_redirect(company_id)
    if not cpf_check_digits_ok(cpf):
        flash(request,'CPF inválido: os dígitos verificadores não conferem. Confira o número digitado.','error'); return _participants_admin_redirect(company_id)
    create_login=clean(form.get('create_login'))=='1'
    new_username=clean_single_line(form.get('new_username')); new_password=str(form.get('new_password') or '').strip()
    with SessionLocal() as db:
        company=db.get(Company,company_id)
        if not company or not company.active:
            flash(request,'A empresa precisa estar ativa para cadastrar participantes.','error'); return _participants_admin_redirect(company_id)
        existing=db.query(Participant).filter(Participant.cpf==cpf).first()
        if existing:
            other_company=db.get(Company,existing.company_id)
            flash(request,f'Esse CPF já está cadastrado para {existing.full_name} ({other_company.name if other_company else "outra empresa"}).','error'); return _participants_admin_redirect(company_id)
        if create_login and not user_id:
            if not new_username or len(new_password)<8:
                flash(request,'Para criar o acesso, informe o login e uma senha com pelo menos 8 caracteres.','error'); return _participants_admin_redirect(company_id)
            if db.query(User).filter(User.username==new_username).first():
                flash(request,f'O login “{new_username}” já existe. Escolha outro ou vincule o usuário existente.','error'); return _participants_admin_redirect(company_id)
            new_user=User(username=new_username,full_name=full_name,password_hash=hash_password(new_password),role=_form_role(form) or ROLE_USER,active=True)
            db.add(new_user); db.flush(); user_id=new_user.id
            db.add(AuditLog(user_id=admin.id,action='criar_usuario_colaborador',detail=f'{new_username} | {full_name}',created_at=now()))
        if user_id:
            linked=db.get(User,user_id)
            if not linked or not linked.active:
                flash(request,'Selecione um usuário ativo do Safety Plus.','error'); return _participants_admin_redirect(company_id)
            other=db.query(Participant).filter(Participant.user_id==user_id).first()
            if other:
                flash(request,'Esse usuário do Safety Plus já está vinculado a outro participante.','error'); return _participants_admin_redirect(company_id)
            new_role=_form_role(form)
            if new_role and linked.role!=ROLE_DEV and linked.id!=admin.id and linked.role!=new_role:
                db.add(AuditLog(user_id=admin.id,action='alterar_perfil_colaborador',detail=f'{linked.username}: {linked.role} -> {new_role}',created_at=now())); linked.role=new_role
        _pc,_ps=_form_cluster_site(form)
        db.add(Participant(company_id=company_id,cpf=cpf,full_name=full_name,job_title=job_title,cluster=_pc,site=_ps,user_id=user_id or None,active=True,created_at=now(),updated_at=now())); db.commit()
    audit(admin.id,'criar_participante',f'{full_name} | CPF final {cpf[-2:]}'); flash(request,'Participante cadastrado.','success')
    return _participants_admin_redirect(company_id)


def _form_cluster_site(form) -> tuple[str,str]:
    c=clean_single_line(form.get('cluster')); st=clean_single_line(form.get('site'))
    if c not in SEPARATE_CLUSTER_SITES: return '',''
    if st not in SEPARATE_CLUSTER_SITES.get(c,[]): st=''
    return c,st

@app.post('/admin/participants/{participant_id}/update')
async def participant_update(request: Request, participant_id: int):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    try: company_id=int(clean(form.get('company_id')) or 0)
    except Exception: company_id=0
    full_name=clean_single_line(form.get('full_name')); job_title=clean_single_line(form.get('job_title')); active=clean(form.get('active'))=='1'
    try: user_id=int(clean(form.get('user_id')) or 0)
    except Exception: user_id=0
    with SessionLocal() as db:
        participant=db.get(Participant,participant_id)
        if not participant: raise HTTPException(404,'Participante não encontrado.')
        redirect_company_id=company_id or participant.company_id
        company=db.get(Company,redirect_company_id)
        if not company:
            flash(request,'Empresa inválida.','error'); return RedirectResponse('/admin/participants',303)
        if not full_name:
            flash(request,'Informe o nome do participante.','error'); return _participants_admin_redirect(redirect_company_id)
        if user_id:
            linked=db.get(User,user_id)
            if not linked or not linked.active:
                flash(request,'Selecione um usuário ativo do Safety Plus.','error'); return _participants_admin_redirect(redirect_company_id)
            other=db.query(Participant).filter(Participant.user_id==user_id,Participant.id!=participant_id).first()
            if other:
                flash(request,'Esse usuário do Safety Plus já está vinculado a outro participante.','error'); return _participants_admin_redirect(redirect_company_id)
        new_role=_form_role(form)
        if user_id and new_role:
            target_user=db.get(User,user_id)
            if target_user and target_user.role!=ROLE_DEV and target_user.id!=admin.id and target_user.role!=new_role:
                db.add(AuditLog(user_id=admin.id,action='alterar_perfil_colaborador',detail=f'{target_user.username}: {target_user.role} -> {new_role}',created_at=now())); target_user.role=new_role
        participant.company_id=redirect_company_id; participant.full_name=full_name; participant.job_title=job_title
        participant.cluster,participant.site=_form_cluster_site(form)
        participant.user_id=user_id or None; participant.active=active; participant.updated_at=now(); db.commit()
    audit(admin.id,'alterar_participante',str(participant_id)); flash(request,'Participante atualizado.','success')
    return _participants_admin_redirect(redirect_company_id)


@app.post('/admin/participants/{participant_id}/delete')
async def participant_delete(request: Request, participant_id: int):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    with SessionLocal() as db:
        participant=db.get(Participant,participant_id)
        if not participant: raise HTTPException(404,'Participante não encontrado.')
        company_id=participant.company_id
        name=participant.full_name; db.delete(participant); db.commit()
    audit(admin.id,'excluir_participante',f'{participant_id} | {name}'); flash(request,'Participante excluído do cadastro. APRs antigas permanecem preservadas.','success')
    return _participants_admin_redirect(company_id)

@app.post('/cluster/select')
async def cluster_select(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if user.role not in (ROLE_SUPER_ADMIN,ROLE_DEV): raise HTTPException(403,'Somente o Super Administrador ou o DEV pode escolher o cluster.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    value=clean(form.get('cluster'))
    if value and value not in SEPARATE_CLUSTERS: raise HTTPException(400,'Cluster inválido.')
    request.session['view_cluster']=value
    audit(user.id,'selecionar_cluster',value or 'todos')
    return RedirectResponse(_safe_next_path(form.get('next'),'/'),303)

AVATAR_DIR=STORAGE_DIR/'avatars'

@app.post('/account/photo')
async def account_photo(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    if clean(form.get('remove'))=='1':
        _set_user_photo(user.id,'')
        flash(request,'Foto de perfil removida.','success'); return RedirectResponse('/account',303)
    upload=form.get('photo')
    raw=await upload.read() if upload is not None and getattr(upload,'filename','') else b''
    if not raw: flash(request,'Selecione uma imagem.','error'); return RedirectResponse('/account',303)
    if len(raw)>12*1024*1024: flash(request,'Imagem muito grande (máx. 12 MB).','error'); return RedirectResponse('/account',303)
    try:
        from PIL import Image, ImageOps
        im=Image.open(io.BytesIO(raw)); im=ImageOps.exif_transpose(im)
        if im.mode in ('RGBA','LA','P'):
            im=im.convert('RGBA'); bg=Image.new('RGB',im.size,(255,255,255)); bg.paste(im,mask=im.split()[-1]); im=bg
        else: im=im.convert('RGB')
        im=ImageOps.fit(im,(320,320),method=Image.LANCZOS,centering=(0.5,0.4))
        AVATAR_DIR.mkdir(parents=True,exist_ok=True)
        rel=f'avatars/{user.id}.jpg'; im.save(STORAGE_DIR/rel,'JPEG',quality=88,optimize=True)
    except Exception:
        flash(request,'Não foi possível ler essa imagem. Use JPG ou PNG.','error'); return RedirectResponse('/account',303)
    _set_user_photo(user.id,rel); audit(user.id,'alterar_foto_perfil',str(user.id))
    flash(request,'Foto de perfil atualizada.','success'); return RedirectResponse('/account',303)

def _set_user_photo(user_id:int,rel:str):
    with SessionLocal() as db:
        u=db.get(User,user_id)
        if u:
            if not rel and clean(u.photo_path):
                try: (STORAGE_DIR/u.photo_path).unlink(missing_ok=True)
                except Exception: pass
            u.photo_path=rel; db.commit()

@app.get('/avatar/{user_id}')
def avatar(request: Request,user_id:int):
    if not current_user(request): raise HTTPException(401)
    with SessionLocal() as db:
        u=db.get(User,user_id); rel=clean(u.photo_path) if u else ''
    p=(STORAGE_DIR/rel).resolve() if rel else None
    if not p or AVATAR_DIR.resolve() not in p.parents or not p.exists(): raise HTTPException(404)
    return FileResponse(p,media_type='image/jpeg',headers={'Cache-Control':'private, max-age=0, must-revalidate'})

@app.get('/admin/users',response_class=HTMLResponse)
def users_page(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if not is_super_admin(user): raise HTTPException(403,'Somente o Super Administrador pode gerenciar usuários e acessos.')
    with SessionLocal() as db:
        users=db.query(User).filter(User.role!=ROLE_DEV).order_by(User.username).all()
        scopes=db.query(UserScope).order_by(UserScope.cluster,UserScope.site).all()
        scope_map={}
        for row in scopes:
            scope_map.setdefault(row.user_id,[]).append((row.cluster,row.site))
        vc=VIEW_CLUSTER.get()
        if vc:  # Super Admin escolheu um cluster: mostra só administradores/usuários dele
            users=[u for u in users if u.id==user.id or any(normalize_location_pair(c,s)[0]==vc for c,s in scope_map.get(u.id,[]))]
    return templates.TemplateResponse(request,'users.html',context(
        request,users=users,scope_map=scope_map,cluster_sites=SEPARATE_CLUSTER_SITES,
        role_super=ROLE_SUPER_ADMIN,role_admin=ROLE_ADMIN,role_user=ROLE_USER,
    ))

def _scope_pairs_from_form(form) -> list[tuple[str,str]]:
    pairs=[]
    for raw in form.getlist('scope_location'):
        value=clean(raw)
        if '|||' not in value:
            continue
        cluster,site=value.split('|||',1)
        cluster,site=clean(cluster),clean(site)
        if cluster in SEPARATE_CLUSTER_SITES and site in SEPARATE_CLUSTER_SITES[cluster]:
            pair=(cluster,site)
            if pair not in pairs:
                pairs.append(pair)
    return pairs

def _normalize_user_role(value: str) -> str:
    value=clean(value)
    return value if value in {ROLE_SUPER_ADMIN,ROLE_ADMIN,ROLE_USER} else ROLE_USER

@app.post('/admin/users/create')
async def user_create(request: Request):
    admin=current_user(request)
    if not admin: return RedirectResponse('/login',303)
    if not is_super_admin(admin): raise HTTPException(403,'Somente o Super Administrador pode criar usuários.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    username=clean(form.get('username')); full=clean(form.get('full_name')); password=str(form.get('password') or '')
    role=_normalize_user_role(form.get('role'))
    scopes=_scope_pairs_from_form(form)
    if not username or len(password)<8:
        flash(request,'Informe usuário e senha com pelo menos 8 caracteres.','error'); return RedirectResponse('/admin/people#usuarios',303)
    if role==ROLE_ADMIN and not scopes:
        flash(request,'Selecione pelo menos um Cluster/Site para o Administrador.','error'); return RedirectResponse('/admin/people#usuarios',303)
    with SessionLocal() as db:
        if db.query(User).filter(User.username==username).first():
            flash(request,'Esse usuário já existe.','error'); return RedirectResponse('/admin/people#usuarios',303)
        u=User(username=username,full_name=full,password_hash=hash_password(password),role=role,active=True)
        db.add(u); db.flush()
        if role==ROLE_ADMIN:
            for cluster,site in scopes:
                db.add(UserScope(user_id=u.id,cluster=cluster,site=site,created_at=now()))
        db.commit()
        new_id=u.id
    audit(admin.id,'criar_usuario',f'{username} | perfil={role} | escopos={len(scopes)}')
    flash(request,'Usuário criado.','success'); return RedirectResponse('/admin/people#usuarios',303)

def _reassign_pending_admin_work(db, target_user_id: int, replacement: User) -> tuple[list[int],int]:
    """Transfere aprovações pendentes antes de remover o acesso do aprovador."""
    push_ids=[]; approval_count=0
    replacement_id=str(replacement.id); replacement_name=replacement.full_name or replacement.username
    docs=db.query(Document).filter(Document.kind=='apr').all()
    for doc in docs:
        try: data=json.loads(doc.data_json or '{}')
        except Exception: data={}
        changed=False
        if doc.status=='Aguardando aprovação':
            primary=clean(data.get('approver_user_id'))
            extras=data.get('approver_extra_user_ids') or []
            if isinstance(extras,str): extras=[extras]
            extras=[clean(v) for v in extras if clean(v)]
            touched=(primary==str(target_user_id) or str(target_user_id) in extras)
            if touched:
                if primary==str(target_user_id):
                    primary=replacement_id
                extras=[replacement_id if x==str(target_user_id) else x for x in extras]
                dedup=[]
                for aid in extras:
                    if aid and aid!=primary and aid not in dedup: dedup.append(aid)
                data['approver_user_id']=primary
                primary_user=db.get(User,int(primary)) if primary.isdigit() else None
                data['approver_name']=(primary_user.full_name or primary_user.username) if primary_user else replacement_name
                data['approver_extra_user_ids']=dedup
                names=[]
                for aid in dedup:
                    a=db.get(User,int(aid)) if aid.isdigit() else None
                    if a: names.append(a.full_name or a.username)
                data['approver_extra_names']=names
                db.query(Notification).filter(Notification.document_id==doc.id,Notification.kind=='apr_approval').delete(synchronize_session=False)
                notify_ids=[]
                if primary.isdigit(): notify_ids.append(int(primary))
                notify_ids.extend(int(x) for x in dedup if x.isdigit() and int(x) not in notify_ids)
                for aid in notify_ids:
                    note=_add_notification(db,recipient_user_id=aid,document_id=doc.id,kind='apr_approval',message=f'{doc_reference_code(doc)} permanece pendente de aprovação. A responsabilidade foi atualizada pelo administrador.')
                    if note: push_ids.append(note.id)
                approval_count+=1; changed=True
        if changed:
            doc.data_json=json.dumps(data,ensure_ascii=False); doc.updated_at=now()
    return push_ids,approval_count

@app.post('/admin/users/{user_id}/update')
async def user_update(request: Request,user_id:int):
    admin=current_user(request)
    if not admin: return RedirectResponse('/login',303)
    if not is_super_admin(admin): raise HTTPException(403,'Somente o Super Administrador pode alterar usuários.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    requested_role=_normalize_user_role(form.get('role')); scopes=_scope_pairs_from_form(form)
    if requested_role==ROLE_ADMIN and not scopes:
        flash(request,'Selecione pelo menos um Cluster/Site para o Administrador.','error'); return RedirectResponse('/admin/people#usuarios',303)
    push_ids=[]; reassigned_approvals=0
    with SessionLocal() as db:
        u=db.get(User,user_id)
        if not u: raise HTTPException(404)
        old_can_approve=bool(u.active and u.role in ADMIN_ROLES)
        if user_id==admin.id and requested_role!=ROLE_SUPER_ADMIN:
            flash(request,'Você não pode remover seu próprio perfil de Super Administrador.','error'); return RedirectResponse('/admin/people#usuarios',303)
        new_active=True if user_id==admin.id else clean(form.get('active'))=='1'
        if u.role==ROLE_SUPER_ADMIN and (requested_role!=ROLE_SUPER_ADMIN or not new_active):
            super_count=db.query(User).filter(User.role==ROLE_SUPER_ADMIN,User.active==True).count()
            if super_count<=1:
                flash(request,'O sistema precisa manter pelo menos um Super Administrador ativo.','error'); return RedirectResponse('/admin/people#usuarios',303)
        new_can_approve=bool(new_active and requested_role in ADMIN_ROLES)
        if old_can_approve and not new_can_approve:
            replacement=db.get(User,admin.id)
            ids,a_count=_reassign_pending_admin_work(db,user_id,replacement)
            push_ids.extend(ids); reassigned_approvals+=a_count
        u.full_name=clean(form.get('full_name')); u.role=requested_role; u.active=new_active
        pwd=str(form.get('new_password') or '')
        if pwd:
            if len(pwd)<8:
                flash(request,'A nova senha deve ter pelo menos 8 caracteres.','error'); return RedirectResponse('/admin/people#usuarios',303)
            u.password_hash=hash_password(pwd)
        db.query(UserScope).filter(UserScope.user_id==user_id).delete(synchronize_session=False)
        if requested_role==ROLE_ADMIN:
            for cluster,site in scopes: db.add(UserScope(user_id=user_id,cluster=cluster,site=site,created_at=now()))
        db.commit()
    if pwd:
        revoke_password_sessions(STORAGE_DIR,user_id,request)
    _queue_push_notification_ids(push_ids)
    audit(admin.id,'alterar_usuario',f'{user_id} | perfil={requested_role} | escopos={len(scopes)} | aprovacoes_repassadas={reassigned_approvals}')
    msg='Usuário atualizado.'
    if reassigned_approvals:
        msg+=f' Pendências transferidas: {reassigned_approvals} aprovação(ões).'
    flash(request,msg,'success'); return RedirectResponse('/admin/people#usuarios',303)

@app.get('/admin/users/bulk',response_class=HTMLResponse)
def users_bulk_page(request: Request):
    admin=require_super_admin(request)
    with SessionLocal() as db:
        candidates=db.query(User).filter(User.role==ROLE_USER,User.id!=admin.id).order_by(User.username).all()
    return templates.TemplateResponse(request,'users_bulk.html',context(
        request,users=candidates,total=len(candidates),
    ))


@app.post('/admin/users/bulk/delete')
async def users_bulk_delete(request: Request):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    if clean(form.get('confirmation'))!='EXCLUIR':
        flash(request,'Digite EXCLUIR para confirmar a exclusão em massa.','error')
        return RedirectResponse('/admin/people#exclusao-massa',303)
    select_all=clean(form.get('selection'))=='all'
    selected=set()
    if not select_all:
        for raw in form.getlist('user_ids'):
            value=clean(raw)
            if value.isdecimal(): selected.add(int(value))
        if not selected:
            flash(request,'Selecione pelo menos um usuário.','error')
            return RedirectResponse('/admin/people#exclusao-massa',303)
    push_ids=[]; removed=0; reassigned=0
    try:
        with SessionLocal.begin() as db:
            replacement=db.get(User,admin.id)
            if not replacement or replacement.role!=ROLE_SUPER_ADMIN:
                raise ValueError('O Super Administrador precisa permanecer ativo.')
            query=db.query(User).filter(User.role==ROLE_USER,User.id!=admin.id)
            if not select_all: query=query.filter(User.id.in_(selected))
            targets=query.order_by(User.id).all()
            ids={u.id for u in targets}
            if not select_all and ids!=selected:
                raise ValueError('A seleção contém contas inexistentes ou administrativas. Atualize a página.')
            # Não deixar documentos aguardando assinatura sem responsável.
            pending_docs=db.query(Document).filter(Document.kind=='apr',Document.status=='Pendente assinatura').all()
            for doc in pending_docs:
                data=doc_data(doc)
                for worker in data.get('workers') or []:
                    value=str(worker.get('participant_user_id') or '')
                    if value.isdecimal() and int(value) in ids and not clean(worker.get('signature_image')):
                        raise ValueError(f'Exclusão bloqueada: há assinatura pendente na {doc_reference_code(doc)}. Resolva a pendência primeiro.')
            for target in targets:
                db.query(Document).filter(Document.created_by==target.id).update({Document.created_by:admin.id},synchronize_session=False)
                notices,approved=_reassign_pending_admin_work(db,target.id,replacement)
                push_ids.extend(notices); reassigned+=approved
                db.query(Notification).filter(Notification.recipient_user_id==target.id).delete(synchronize_session=False)
                db.query(PushSubscription).filter(PushSubscription.user_id==target.id).delete(synchronize_session=False)
                db.query(Participant).filter(Participant.user_id==target.id).update({Participant.user_id:None},synchronize_session=False)
                db.query(UserScope).filter(UserScope.user_id==target.id).delete(synchronize_session=False)
                db.delete(target)
                removed+=1
            db.add(AuditLog(user_id=admin.id,action='excluir_usuarios_em_massa',
                            detail=f'total={removed} | transferidas_aprovacoes={reassigned}',created_at=now()))
            db.flush()
    except ValueError as exc:
        flash(request,str(exc),'error')
        return RedirectResponse('/admin/people#exclusao-massa',303)
    except SQLAlchemyError:
        import logging
        logging.getLogger(__name__).exception('Falha ao excluir usuários em massa')
        flash(request,'Erro no banco de dados. Exclusão cancelada e alterações revertidas.','error')
        return RedirectResponse('/admin/people#exclusao-massa',303)
    _queue_push_notification_ids(push_ids)
    flash(request,f'{removed} conta(s) de usuário removida(s). Documentos e histórico preservados; cadastros de participantes mantidos sem vínculo de login.','success')
    return RedirectResponse('/admin/people#exclusao-massa',303)


@app.post('/admin/users/{user_id}/delete')
async def user_delete(request: Request,user_id:int):
    admin=require_super_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    if user_id==admin.id:
        flash(request,'Você não pode excluir a própria conta de administrador.','error')
        return RedirectResponse('/admin/people#usuarios',303)
    push_ids=[]
    with SessionLocal() as db:
        target=db.get(User,user_id)
        if not target:
            raise HTTPException(404,'Usuário não encontrado')
        target_name=target.full_name or target.username
        pending_signature_docs=db.query(Document).filter(Document.kind=='apr',Document.status=='Pendente assinatura').all()
        for pending_doc in pending_signature_docs:
            pdata=doc_data(pending_doc)
            for worker in pdata.get('workers') or []:
                if str(worker.get('participant_user_id') or '')==str(user_id) and not clean(worker.get('signature_image')):
                    flash(request,f'Não é possível excluir {target_name}: existe assinatura pendente na {doc_reference_code(pending_doc)}. Cancele a coleta de assinaturas ou vincule o participante a outro usuário primeiro.','error')
                    return RedirectResponse('/admin/people#usuarios',303)
        # Preserva o histórico documental: documentos criados pelo usuário passam para
        # o administrador que está executando a exclusão.
        db.query(Document).filter(Document.created_by==user_id).update({Document.created_by:admin.id},synchronize_session=False)
        replacement=db.get(User,admin.id)
        transfer_ids,reassigned=_reassign_pending_admin_work(db,user_id,replacement)
        push_ids.extend(transfer_ids)
        db.query(Notification).filter(Notification.recipient_user_id==user_id).delete(synchronize_session=False)
        db.query(PushSubscription).filter(PushSubscription.user_id==user_id).delete(synchronize_session=False)
        db.query(Participant).filter(Participant.user_id==user_id).update({Participant.user_id:None},synchronize_session=False)
        db.query(UserScope).filter(UserScope.user_id==user_id).delete(synchronize_session=False)
        db.delete(target)
        db.commit()
    _queue_push_notification_ids(push_ids)
    audit(admin.id,'excluir_usuario',f'{user_id} | {target_name} | aprs_repassadas={reassigned}')
    msg=f'Usuário {target_name} excluído. Os documentos foram preservados.'
    if reassigned: msg+=f' Pendências transferidas: {reassigned} aprovação(ões).'
    flash(request,msg,'success')
    return RedirectResponse('/admin/people#usuarios',303)

@app.get('/account',response_class=HTMLResponse)
def account(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    prefs=_load_notification_preferences(); global_prefs=prefs.get('global',{})
    user_prefs=prefs.get('users',{}).get(str(user.id),{})
    effective={k:(bool(global_prefs.get(k,True)) and bool(user_prefs.get(k,True))) for k in NOTIFICATION_TYPES}
    return templates.TemplateResponse(request,'account.html',context(request,notification_types=NOTIFICATION_TYPES,global_notification_prefs=global_prefs,user_notification_prefs=user_prefs,effective_notification_prefs=effective))

@app.post('/account/notifications')
async def account_notifications(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if user.role != ROLE_USER: raise HTTPException(403,'As preferências pessoais de notificações são exclusivas do usuário padrão.')
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    prefs=_load_notification_preferences(); selected=set(form.getlist('notification_types'))
    prefs.setdefault('users',{})[str(user.id)]={k:(k in selected) for k in NOTIFICATION_TYPES}
    _save_notification_preferences(prefs)
    audit(user.id,'configurar_notificacoes','Tipos pessoais de notificação atualizados.')
    flash(request,'Preferências de notificações salvas.','success')
    return RedirectResponse('/account#notificacoes',303)

@app.get('/admin/notifications',response_class=HTMLResponse)
def admin_notifications(request: Request):
    admin=require_admin(request)
    prefs=_load_notification_preferences()
    return templates.TemplateResponse(request,'admin_notifications.html',context(request,notification_types=NOTIFICATION_TYPES,global_notification_prefs=prefs.get('global',{})))

@app.post('/admin/notifications')
async def admin_notifications_save(request: Request):
    admin=require_admin(request)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    selected=set(form.getlist('notification_types')); prefs=_load_notification_preferences()
    prefs['global']={k:(k in selected) for k in NOTIFICATION_TYPES}; _save_notification_preferences(prefs)
    audit(admin.id,'configurar_notificacoes_globais','Tipos globais de notificação atualizados.')
    flash(request,'Configurações gerais de notificações salvas.','success')
    return RedirectResponse('/admin/notifications',303)

@app.post('/account/password')
async def account_password(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token')); current=str(form.get('current_password') or ''); new=str(form.get('new_password') or '')
    if len(new)<8: flash(request,'A nova senha deve ter pelo menos 8 caracteres.','error'); return RedirectResponse('/account',303)
    with SessionLocal() as db:
        u=db.get(User,user.id)
        if not verify_password(current,u.password_hash): flash(request,'Senha atual incorreta.','error'); return RedirectResponse('/account',303)
        u.password_hash=hash_password(new); db.commit()
    revoke_password_sessions(STORAGE_DIR,user.id,request)
    audit(user.id,'trocar_senha',''); flash(request,'Senha alterada com sucesso.','success'); return RedirectResponse('/account',303)

# Central de Ajuda: tickets persistidos no banco principal.
from sqlalchemy import text as _support_sql

def _support_init():
    with engine.begin() as conn:
        conn.execute(_support_sql(f"""CREATE TABLE IF NOT EXISTS support_tickets (
            id {"INTEGER PRIMARY KEY" if engine.dialect.name == "sqlite" else "INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY"}, user_id INTEGER NOT NULL, category VARCHAR(32) NOT NULL,
            subject VARCHAR(160) NOT NULL, description TEXT NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'Em análise', response TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"""))
_support_init()

# Encaminhamento de solicitações: migração aditiva, sem alterar registros existentes.
with engine.begin() as _routing_conn:
    _routing_cols = {r[1] for r in _routing_conn.execute(_support_sql('PRAGMA table_info(support_tickets)')).all()} if engine.dialect.name == 'sqlite' else {r[0] for r in _routing_conn.execute(_support_sql("SELECT column_name FROM information_schema.columns WHERE table_name='support_tickets'")).all()}
    if 'assigned_to' not in _routing_cols:
        _routing_conn.execute(_support_sql('ALTER TABLE support_tickets ADD COLUMN assigned_to INTEGER'))

# Colaboradores: vínculo opcional com Cluster/Site (migração aditiva, não altera registros existentes).
with engine.begin() as _pc_conn:
    _pc_cols = {r[1] for r in _pc_conn.execute(_support_sql('PRAGMA table_info(participants)')).all()} if engine.dialect.name == 'sqlite' else {r[0] for r in _pc_conn.execute(_support_sql("SELECT column_name FROM information_schema.columns WHERE table_name='participants'")).all()}
    if 'cluster' not in _pc_cols:
        _pc_conn.execute(_support_sql("ALTER TABLE participants ADD COLUMN cluster VARCHAR(120) NOT NULL DEFAULT ''"))
    if 'site' not in _pc_cols:
        _pc_conn.execute(_support_sql("ALTER TABLE participants ADD COLUMN site VARCHAR(160) NOT NULL DEFAULT ''"))

@app.get('/api/support/recipients')
def support_recipients(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401)
    with SessionLocal() as db:
        people=db.query(User).filter(User.active==True, User.role==ROLE_SUPER_ADMIN).order_by(User.role.desc(),User.full_name).all()
        return JSONResponse({'recipients':[{'id':u.id,'name':u.full_name or u.username,'role':u.role} for u in people]})

@app.post('/api/support/tickets')
async def support_create(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,'Faça login para solicitar suporte.')
    form=await request.form()
    verify_csrf(request,form.get('csrf_token'))
    category=str(form.get('category','')).strip()
    subject=str(form.get('subject','')).strip()[:160]
    module=str(form.get('module','')).strip()[:80]
    location=str(form.get('location','')).strip()[:160]
    description=str(form.get('description','')).strip()[:4000]
    if category not in ('Erro no sistema','Solicitar melhoria') or not subject or not description or not module:
        raise HTTPException(400,'Preencha os campos obrigatórios.')
    recipient_raw=str(form.get('assigned_to','')).strip()
    try: recipient_id=int(recipient_raw)
    except (ValueError,TypeError): raise HTTPException(400,'Selecione quem receberá a solicitação.')
    with SessionLocal() as db:
        recipient=db.query(User).filter(User.id==recipient_id,User.active==True,User.role==ROLE_SUPER_ADMIN).first()
        if not recipient: raise HTTPException(400,'Responsável inválido ou inativo.')
    description=f'Módulo: {module}\nTela/Local: {location or "—"}\n\n{description}'
    upload=form.get('image')
    image_data=None
    image_type=None
    if upload is not None and getattr(upload,'filename',None):
        image_data=await upload.read(5*1024*1024+1)
        if len(image_data)>5*1024*1024:
            raise HTTPException(400,'Imagem muito grande. Limite de 5 MB.')
        if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            image_type='image/png'
        elif image_data.startswith(b'\xff\xd8\xff'):
            image_type='image/jpeg'
        elif image_data.startswith(b'RIFF') and image_data[8:12]==b'WEBP':
            image_type='image/webp'
        else:
            raise HTTPException(400,'Envie uma imagem PNG, JPG ou WebP válida.')
    with engine.begin() as conn:
        result=conn.execute(_support_sql("INSERT INTO support_tickets (user_id,category,subject,description,assigned_to) VALUES (:u,:c,:s,:d,:a) RETURNING id"),
                     {'u':user.id,'c':category,'s':subject,'d':description,'a':recipient_id})
        ticket_id=result.scalar_one()
        if image_data:
            conn.execute(_support_sql('INSERT INTO support_images (ticket_id,media_type,image_data) VALUES (:id,:m,:d)'),
                         {'id':ticket_id,'m':image_type,'d':image_data})
    audit(user.id,'solicitacao_suporte_criada',f'#{ticket_id} encaminhada para usuario {recipient_id}')
    return JSONResponse({'ok':True,'id':int(ticket_id),'message':'Solicitação encaminhada ao responsável. Acompanhe em Minhas solicitações.'})


# Imagens de solicitações ficam no banco, com acesso restrito ao autor e à administração.
image_sql_type = 'BLOB' if engine.dialect.name == 'sqlite' else 'BYTEA'
with engine.begin() as _support_conn:
    _support_conn.execute(_support_sql(f"""CREATE TABLE IF NOT EXISTS support_images (
        ticket_id INTEGER PRIMARY KEY, media_type VARCHAR(32) NOT NULL, image_data {image_sql_type} NOT NULL)"""))

@app.get('/api/support/tickets/{ticket_id}/image')
async def support_image(request:Request,ticket_id:int):
    user=current_user(request)
    if not user: raise HTTPException(401)
    with engine.connect() as conn:
        row=conn.execute(_support_sql("""SELECT t.user_id,i.media_type,i.image_data
            FROM support_tickets t JOIN support_images i ON i.ticket_id=t.id
            WHERE t.id=:id"""),{'id':ticket_id}).mappings().first()
    if not row: raise HTTPException(404)
    if row['user_id']!=user.id and user.role not in ADMIN_ROLES: raise HTTPException(403)
    return Response(content=bytes(row['image_data']),media_type=row['media_type'],headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@app.get('/api/support/tickets')
async def support_list(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401)
    with engine.connect() as conn:
        rows=conn.execute(_support_sql("""SELECT t.id,t.category,t.subject,t.description,t.status,t.response,t.created_at, u.full_name AS assigned_name, u.username AS assigned_username,
             EXISTS(SELECT 1 FROM support_images si WHERE si.ticket_id=t.id) AS has_image
             FROM support_tickets t LEFT JOIN users u ON u.id=t.assigned_to WHERE t.user_id=:uid ORDER BY t.id DESC LIMIT 40"""),{'uid':user.id}).mappings().all()
    return JSONResponse({'tickets':[dict(r,created_at=str(r['created_at']),has_image=bool(r['has_image'])) for r in rows]})

@app.get('/api/support/pending-alerts')
def support_pending_alerts(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401)
    if user.role not in ADMIN_ROLES: raise HTTPException(403)
    with engine.connect() as conn:
        rows=conn.execute(_support_sql("""SELECT id,subject,created_at FROM support_tickets
            WHERE assigned_to=:uid AND status != 'Atualização concluída'
            ORDER BY id DESC LIMIT 20"""),{'uid':user.id}).mappings().all()
    return JSONResponse({'count':len(rows),'tickets':[{'id':int(r['id']),'subject':str(r['subject']),'created_at':str(r['created_at'])} for r in rows]},headers={'Cache-Control':'no-store'})

SUPPORT_STATUSES=('Em análise','Sendo verificado','Em andamento','Atualização concluída')


def _support_split_description(raw: str) -> tuple[str,str,str]:
    """Separa Módulo e Tela/Local gravados no início da descrição."""
    module=location=''; body=[]; header=True
    for line in str(raw or '').splitlines():
        if header and line.startswith('Módulo:'):
            module=line.split(':',1)[1].strip(); continue
        if header and line.startswith('Tela/Local:'):
            location=line.split(':',1)[1].strip(); continue
        if header and not line.strip() and (module or location):
            header=False; continue
        header=False; body.append(line)
    return module,location,'\n'.join(body).strip()


def _support_fmt_dt(value: Any) -> str:
    raw=str(value or '')[:16]
    try:
        dt=datetime.fromisoformat(raw)
        return dt.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return raw


def _support_ticket_view(r, user) -> dict:
    status=str(r['status'] or 'Em análise')
    if status=='Aberta': status='Em análise'
    if status=='Resolvida': status='Atualização concluída'
    module,location,body=_support_split_description(r['description'])
    return {
        'id':int(r['id']),'subject':str(r['subject'] or ''),'category':str(r['category'] or ''),
        'module':module,'location':location,'body':body,'status':status,
        'status_key':'done' if status=='Atualização concluída' else 'progress' if status in ('Sendo verificado','Em andamento') else 'new',
        'step':3 if status=='Atualização concluída' else 2 if status in ('Sendo verificado','Em andamento') else 1,
        'response':str(r['response'] or ''),'created_at':_support_fmt_dt(r['created_at']),'updated_at':_support_fmt_dt(r.get('updated_at')),
        'requester':str(r.get('full_name') or r.get('username') or f"Usuário {r['user_id']}"),
        'assigned_to':r['assigned_to'],'assigned_name':str(r.get('assigned_name') or r.get('assigned_username') or ''),
        'has_image':bool(r['has_image']),
        'mine':r['assigned_to']==user.id,
        'can_edit':is_super_admin(user) or r['assigned_to']==user.id,
    }


def _support_center_context(request: Request, user: User, tab: str='', kind: str='') -> dict:
    is_admin=user.role in ADMIN_ROLES
    with engine.connect() as conn:
        mine_rows=conn.execute(_support_sql("""SELECT t.*,a.full_name AS assigned_name,a.username AS assigned_username,
            EXISTS(SELECT 1 FROM support_images si WHERE si.ticket_id=t.id) AS has_image
            FROM support_tickets t LEFT JOIN users a ON a.id=t.assigned_to WHERE t.user_id=:uid ORDER BY t.id DESC LIMIT 60"""),{'uid':user.id}).mappings().all()
        recv_rows=conn.execute(_support_sql("""SELECT t.*,u.full_name,u.username,a.full_name AS assigned_name,a.username AS assigned_username,
            EXISTS(SELECT 1 FROM support_images si WHERE si.ticket_id=t.id) AS has_image
            FROM support_tickets t LEFT JOIN users u ON u.id=t.user_id LEFT JOIN users a ON a.id=t.assigned_to
            ORDER BY t.id DESC LIMIT 300""")).mappings().all() if is_admin else []
    with SessionLocal() as db:
        routing_users=db.query(User).filter(User.active==True,User.role==ROLE_SUPER_ADMIN).order_by(User.full_name).all()
        routing_options=[{'id':u.id,'name':u.full_name or u.username,'role':u.role} for u in routing_users]
    mine=[_support_ticket_view(r,user) for r in mine_rows]
    received=[_support_ticket_view(r,user) for r in recv_rows]
    counts={k:sum(1 for t in received if t['status']==k) for k in SUPPORT_STATUSES}
    stats={
        'total':len(received),'open':sum(1 for t in received if t['status_key']!='done'),
        'new':counts['Em análise'],'progress':counts['Sendo verificado']+counts['Em andamento'],'done':counts['Atualização concluída'],
        'mine':sum(1 for t in received if t['mine'] and t['status_key']!='done'),
        'errors':sum(1 for t in received if t['category']=='Erro no sistema' and t['status_key']!='done'),
    }
    my_stats={'total':len(mine),'open':sum(1 for t in mine if t['status_key']!='done'),
              'answered':sum(1 for t in mine if t['response']),'done':sum(1 for t in mine if t['status_key']=='done')}
    tabs=['como-usar','nova','minhas']+(['recebidas'] if is_admin else [])
    if tab not in tabs: tab='como-usar'
    is_dev_user=(user.role==ROLE_DEV)
    help_articles=[a for a in HELP_ARTICLES if (is_admin or not a.get('admin')) and (is_dev_user or not a.get('dev'))]
    help_cats=[(c,label,sum(1 for a in help_articles if a['cat']==c)) for c,label in HELP_CATEGORIES]
    help_cats=[c for c in help_cats if c[2]]
    return context(request,support_tab=tab,support_kind=('melhoria' if kind=='melhoria' else 'erro'),
                   mine=mine,my_stats=my_stats,tickets=received,stats=stats,statuses=SUPPORT_STATUSES,
                   routing_options=routing_options,modules=sorted({t['module'] for t in received if t['module']}),
                   is_super=is_super_admin(user),is_support_admin=is_admin,
                   help_articles=help_articles,help_cats=help_cats,help_synonyms=HELP_SYNONYMS)


@app.get('/admin/support')
async def support_admin(request: Request, ticket: str=''):
    """Painel antigo: agora é a aba “Recebidas” da Central de Ajuda."""
    if not current_user(request): return RedirectResponse('/login',303)
    return RedirectResponse('/central-ajuda?aba=recebidas'+(f'&ticket={int(ticket)}' if str(ticket).isdigit() else ''),303)

@app.post('/admin/support/{ticket_id}')
async def support_admin_update(request: Request,ticket_id:int):
    user=current_user(request)
    if not user: raise HTTPException(401)
    if user.role not in ADMIN_ROLES: raise HTTPException(403)
    form=await request.form()
    verify_csrf(request,form.get('csrf_token'))
    status=str(form.get('status',''))
    if status not in ('Em análise','Sendo verificado','Em andamento','Atualização concluída'): raise HTTPException(400)
    with engine.begin() as conn:
        existing=conn.execute(_support_sql('SELECT assigned_to FROM support_tickets WHERE id=:id'),{'id':ticket_id}).mappings().first()
        if not existing: raise HTTPException(404)
        assigned_to=existing['assigned_to']
        if is_super_admin(user) and form.get('assigned_to'):
            try: candidate=int(form.get('assigned_to'))
            except (TypeError,ValueError): raise HTTPException(400,'Responsável inválido.')
            with SessionLocal() as db:
                valid=db.query(User).filter(User.id==candidate,User.active==True,User.role==ROLE_SUPER_ADMIN).first()
                if not valid: raise HTTPException(400,'Responsável inválido.')
            assigned_to=candidate
        elif not is_super_admin(user) and assigned_to!=user.id:
            raise HTTPException(403,'Apenas o responsável designado ou o superadministrador pode responder.')
        conn.execute(_support_sql('UPDATE support_tickets SET status=:s,response=:r,assigned_to=:a,updated_at=CURRENT_TIMESTAMP WHERE id=:id'),
                     {'s':status,'r':str(form.get('response',''))[:4000],'a':assigned_to,'id':ticket_id})
    audit(user.id,'solicitacao_suporte_atualizada',f'#{ticket_id} | status={status}')
    flash(request,f'Solicitação #{ticket_id} atualizada.','success')
    return RedirectResponse(f'/central-ajuda?aba=recebidas&ticket={ticket_id}',303)


@app.get('/central-ajuda/{section}', response_class=HTMLResponse)
async def support_section_page(request: Request, section: str):
    if not current_user(request): return RedirectResponse('/login', status_code=303)
    target={'reportar-erro':'?aba=nova&tipo=erro','solicitar-melhoria':'?aba=nova&tipo=melhoria','minhas-solicitacoes':'?aba=minhas','recebidas':'?aba=recebidas','como-usar':'?aba=como-usar','manual':'?aba=como-usar'}.get(section)
    if not target: raise HTTPException(404)
    return RedirectResponse('/central-ajuda'+target,303)

@app.get('/central-ajuda', response_class=HTMLResponse)
async def support_center_page(request: Request, aba: str='', tipo: str=''):
    user=current_user(request)
    if not user:
        return RedirectResponse('/login', status_code=303)
    return templates.TemplateResponse(request, 'support_center.html', _support_center_context(request,user,aba,tipo))


@app.get('/api/offline/form-manifest')
def offline_form_manifest(request: Request):
    if not current_user(request):
        raise HTTPException(401, 'Autenticação necessária')
    items=[{'path':'/apr/new','group':'apr','title':'Nova APR'}]
    items+=[{'path':f'/permit/{kind}/new','group':'permit','title':DOCUMENT_TITLES.get(kind,kind).replace('PT — ','')} for kind in MODULES]
    items+=[{'path':f'/rac/{kind}/new','group':'rac','title':RAC_MODULES[kind].get('title',kind).replace('RAC — ','')} for kind in RAC_MODULES]
    items+=[{'path':'/vehicle/new','group':'inspection','title':'Veículo Pesado'}]
    friendly={'hoist':'Talha Guincho','light_vehicle':'Veículo Leve','height_kit':'Kit de Trabalho em Altura (diária)','climber_assist':'Climber Assist','safety_belt':'Cinto de Segurança (estrutural)','spiq':'Equipamentos SPIQ','loto':'LOTO','grinder':'Esmerilhadeira','drill':'Furadeira','rotary_hammer':'Martelete','circular_saw':'Serra Circular','marble_saw':'Serra Mármore','welding_machine':'Máquina de Solda','lifting_accessories':'Acessórios de Içamento de Carga'}
    items+=[{'path':f'/inspection/{kind}/new','group':'inspection','title':friendly.get(kind) or DOCUMENT_TITLES.get(kind,kind)} for kind in INSPECTION_MODULES]
    return JSONResponse({'paths':[i['path'] for i in items],'items':items,'count':len(items)},headers={'Cache-Control':'no-store'})


@app.get('/api/offline/sync-token')
def offline_sync_token(request: Request):
    """Token atual da sessão para reenviar formulários guardados offline.

    O formulário preparado guarda o token CSRF do momento da preparação; depois
    de um novo login ele deixa de valer. A fila do aparelho busca aqui o token
    vigente e confere se o usuário logado é o mesmo que gerou o registro.
    """
    user=current_user(request)
    if not user:
        return JSONResponse({'authenticated':False},status_code=401,headers={'Cache-Control':'no-store'})
    return JSONResponse({'authenticated':True,'user_id':user.id,'csrf_token':csrf_token(request)},headers={'Cache-Control':'no-store, private'})


@app.get('/offline', response_class=HTMLResponse)
def offline_center_standalone(request: Request):
    """Central Offline pública (sem dados do usuário): guardada pelo Service Worker
    e exibida quando não há internet. Os dados vêm do próprio aparelho."""
    return templates.TemplateResponse(request,'offline_standalone.html',{'request':request},headers={'Cache-Control':'no-cache'})

@app.get('/admin/offline', response_class=HTMLResponse)
def admin_offline_page(request: Request):
    if not current_user(request): return RedirectResponse('/login', status_code=303)
    return templates.TemplateResponse(request, 'admin_offline.html', context(request))


# -------------------- V36.18.94 — Consulta inteligente de colaborador --------------------
# Painel analítico por colaborador (participante): documentos emitidos e com
# participação, tipos mais gerados, severidades, perigos/riscos, respostas
# NÃO e documentos com o mesmo nome mas seleções diferentes.
import difflib as _difflib

_NEGATIVE_ANSWERS={'NÃO','NAO','NC','NÃO ATENDE','NAO ATENDE','NÃO CONFORME'}
_MONTHS_PT=['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']


def _norm_text(value: Any) -> str:
    raw=unicodedata.normalize('NFKD',clean(value)).encode('ascii','ignore').decode('ascii').lower()
    raw=re.sub(r'[^a-z0-9]+',' ',raw)
    return re.sub(r'\s+',' ',raw).strip()


def _kind_label(kind: str) -> str:
    title=DOCUMENT_TITLES.get(kind,kind)
    return title.replace('PT — ','PT · ')


def _doc_mentions(value: Any, name_norm: str, cpf: str, depth: int=0) -> bool:
    if depth>5: return False
    if isinstance(value,str):
        if cpf and cpf_digits(value)==cpf and len(re.sub(r'\D','',value))==11: return True
        return bool(name_norm) and _norm_text(value)==name_norm
    if isinstance(value,dict):
        return any(_doc_mentions(v,name_norm,cpf,depth+1) for k,v in value.items() if not str(k).endswith('signature_image'))
    if isinstance(value,(list,tuple)):
        return any(_doc_mentions(v,name_norm,cpf,depth+1) for v in value)
    return False


def _worker_matches(worker: dict, participant: Participant, name_norm: str) -> bool:
    if not isinstance(worker,dict): return False
    if clean(worker.get('participant_id'))==str(participant.id): return True
    if participant.cpf and cpf_digits(worker.get('cpf'))==participant.cpf: return True
    wname=_norm_text(worker.get('worker') or worker.get('name') or worker.get('nome'))
    return bool(name_norm) and wname==name_norm


def _negative_answers(data: dict) -> int:
    total=0
    def walk(v, inside=False, depth=0):
        nonlocal total
        if depth>4: return
        if isinstance(v,str):
            if inside and v.strip().upper() in _NEGATIVE_ANSWERS: total+=1
        elif isinstance(v,dict):
            for k,x in v.items():
                key=str(k).lower()
                walk(x, inside or any(t in key for t in ('check','answer','resposta','item')), depth+1)
        elif isinstance(v,(list,tuple)):
            for x in v: walk(x,inside,depth+1)
    walk({k:v for k,v in data.items() if k not in ('critical_activity','improvements_answer')})
    return total


def _doc_selections(kind: str, data: dict) -> dict[str,str]:
    """Seleções comparáveis de um documento (usadas na detecção de divergências)."""
    sel={}
    if kind=='apr':
        sev=normalize_apr_severity(data.get('severity'))
        if sev: sel['Severidade geral']=sev
        steps=[s for s in (data.get('steps') or []) if isinstance(s,dict)]
        step_sev=[normalize_apr_severity(s.get('severity')) for s in steps if normalize_apr_severity(s.get('severity'))]
        if step_sev: sel['Severidade das etapas']=' / '.join(step_sev)
        hazards=sorted({h for s in steps for h in _normalize_multi_step_values(s.get('hazards'),s.get('hazard'))})
        risks=sorted({r for s in steps for r in _normalize_multi_step_values(s.get('risks'),s.get('risk'))})
        if hazards: sel['Perigos selecionados']='; '.join(hazards)
        if risks: sel['Riscos selecionados']='; '.join(risks)
        sel['Atividade crítica']='SIM' if clean(data.get('critical_activity')).upper()=='SIM' else 'NÃO'
        pts=[p for p in (data.get('critical_permits') or []) if p]
        if pts: sel['PTs selecionadas']=', '.join(sorted(pts))
        questions=CHECKLIST
    else:
        questions=(MODULES.get(kind) or {}).get('checklist') or []
        for key,label in (('work_types','Tipos de trabalho'),('entry_types','Tipos de entrada'),('equipment_types','Equipamentos')):
            vals=[clean(v) for v in (data.get(key) or []) if clean(v)]
            if vals: sel[label]=', '.join(sorted(vals))
        if clean(data.get('equipment_type')): sel['Equipamento']=clean(data.get('equipment_type'))
    checklist=data.get('checklist') if isinstance(data.get('checklist'),list) else []
    for i,ans in enumerate(checklist):
        if isinstance(ans,str) and clean(ans):
            q=questions[i] if i<len(questions) else ''
            label=f'Checklist {i+1:02d}'+(f' — {q[:90]}{"…" if len(q)>90 else ""}' if q else '')
            sel[label]=clean(ans).upper()
    return sel


def _doc_display_name(doc: Document, data: dict) -> str:
    return clean(data.get('activity')) or clean(doc.activity) or ''


def collaborator_insights(viewer: User, participant_id: int) -> dict:
    with SessionLocal() as db:
        participant=db.get(Participant,participant_id)
        if not participant: raise HTTPException(404,'Colaborador não encontrado.')
        company=db.get(Company,participant.company_id)
        linked_user=db.get(User,participant.user_id) if participant.user_id else None
        name_norm=_norm_text(participant.full_name)
        conds=[]
        if participant.user_id: conds.append(Document.created_by==participant.user_id)
        if participant.cpf: conds.append(Document.data_json.like(f'%{participant.cpf}%'))
        if participant.full_name: conds.append(Document.data_json.ilike(f'%{participant.full_name}%'))
        docs=db.query(Document).filter(Document.kind!='apr_template',or_(*conds)).order_by(Document.created_at.desc()).limit(3000).all() if conds else []
        creators={u.id:(u.full_name or u.username) for u in db.query(User).all()}
        for d in docs: db.expunge(d)
        db.expunge(participant)

    rows=[]
    for doc in docs:
        if not user_can_list_document(viewer,doc): continue
        try: data=doc_data(doc)
        except Exception: data={}
        emitted=bool(participant.user_id and doc.created_by==participant.user_id)
        member=any(_worker_matches(w,participant,name_norm) for w in (data.get('workers') or data.get('participants') or []) if isinstance(w,dict))
        cited=False if (emitted or member) else _doc_mentions(data,name_norm,participant.cpf)
        if not (emitted or member or cited): continue
        rows.append({'doc':doc,'data':data,'emitted':emitted,'member':member,'cited':cited})

    by_kind=Counter(); by_kind_emitted=Counter(); by_status=Counter(); by_site=Counter()
    sev_overall=Counter(); sev_steps=Counter(); hazards=Counter(); risks=Counter()
    negatives=0; docs_with_negative=0; recent=[]
    today=local_today()
    months=[]
    y,m=today.year,today.month
    for _ in range(12):
        months.append((y,m)); m-=1
        if m==0: m=12; y-=1
    months.reverse()
    timeline={k:{'emitted':0,'member':0} for k in months}
    for r in rows:
        doc,data=r['doc'],r['data']
        by_kind[doc.kind]+=1
        if r['emitted']: by_kind_emitted[doc.kind]+=1
        by_status[doc.status]+=1
        place=' · '.join(x for x in (clean(doc.cluster),clean(doc.site)) if x)
        if place: by_site[place]+=1
        if doc.kind=='apr':
            sev=normalize_apr_severity(data.get('severity'))
            if sev: sev_overall[sev]+=1
            for st in data.get('steps') or []:
                if not isinstance(st,dict): continue
                s=normalize_apr_severity(st.get('severity'))
                if s: sev_steps[s]+=1
                for h in _normalize_multi_step_values(st.get('hazards'),st.get('hazard')): hazards[h]+=1
                for rk in _normalize_multi_step_values(st.get('risks'),st.get('risk')): risks[rk]+=1
        neg=_negative_answers(data)
        negatives+=neg
        if neg: docs_with_negative+=1
        created=doc.created_at
        if created:
            key=(created.year,created.month)
            if key in timeline: timeline[key]['emitted' if r['emitted'] else 'member']+=1
    for r in rows[:25]:
        doc,data=r['doc'],r['data']
        recent.append({
            'id':doc.id,'code':doc_reference_code(doc),'kind':doc.kind,'kind_label':_kind_label(doc.kind),
            'activity':_doc_display_name(doc,data)[:140],'status':doc.status,
            'date':doc.created_at.strftime('%d/%m/%Y') if doc.created_at else '',
            'site':' · '.join(x for x in (clean(doc.cluster),clean(doc.site)) if x),
            'role':'Emitente' if r['emitted'] else ('Integrante' if r['member'] else 'Citado'),
            'severity':normalize_apr_severity(data.get('severity')) if doc.kind=='apr' else '',
            'negatives':_negative_answers(data),
            'creator':creators.get(doc.created_by,''),
        })

    # Mesmo nome (atividade) + mesmo tipo, com seleções diferentes.
    groups=[]
    for r in rows:
        doc,data=r['doc'],r['data']
        name=_doc_display_name(doc,data); key=_norm_text(name)
        if len(key)<4: continue
        target=None
        for g in groups:
            if g['kind']==doc.kind and (g['key']==key or _difflib.SequenceMatcher(None,g['key'],key).ratio()>=0.9):
                target=g; break
        if not target:
            target={'kind':doc.kind,'key':key,'name':name,'items':[]}; groups.append(target)
        target['items'].append(r)
    divergences=[]
    for g in groups:
        if len(g['items'])<2: continue
        sels=[(r,_doc_selections(r['doc'].kind,r['data'])) for r in g['items']]
        fields=[]
        def _field_rank(name: str):
            order=('Severidade geral','Severidade das etapas','Atividade crítica','PTs selecionadas','Perigos selecionados','Riscos selecionados')
            return (order.index(name) if name in order else len(order), name)
        for f in sorted({k for _,s in sels for k in s},key=_field_rank):
            values={}
            for r,s in sels:
                if f in s: values.setdefault(s[f],[]).append(doc_reference_code(r['doc']))
            if len(values)>1:
                fields.append({'field':f,'values':[{'value':v,'docs':d} for v,d in sorted(values.items(),key=lambda x:-len(x[1]))]})
        if fields:
            critical=any(f['field'].startswith(('Severidade','Atividade crítica','PTs')) or any(v['value'] in _NEGATIVE_ANSWERS for v in f['values']) for f in fields)
            divergences.append({
                'name':g['name'],'kind':g['kind'],'kind_label':_kind_label(g['kind']),
                'documents':[{'id':r['doc'].id,'code':doc_reference_code(r['doc']),'date':r['doc'].created_at.strftime('%d/%m/%Y') if r['doc'].created_at else '','status':r['doc'].status,'role':'Emitente' if r['emitted'] else ('Integrante' if r['member'] else 'Citado')} for r in g['items']],
                'fields':fields,'field_count':len(fields),'critical':critical,
            })
    divergences.sort(key=lambda d:(not d['critical'],-d['field_count']))

    emitted_total=sum(1 for r in rows if r['emitted'])
    member_total=sum(1 for r in rows if r['member'])
    apr_total=by_kind.get('apr',0)
    pt_total=sum(v for k,v in by_kind.items() if k in MODULES)
    return {
        'participant':{
            'id':participant.id,'name':participant.full_name,'cpf':cpf_mask(participant.cpf),
            'job':participant.job_title or '','company':company.name if company else '—','active':bool(participant.active),
            'username':linked_user.username if linked_user else '','role':linked_user.role if linked_user else '',
            'since':participant.created_at.strftime('%d/%m/%Y') if participant.created_at else '',
            'initials':''.join(p[0] for p in participant.full_name.split()[:2]).upper(),
        },
        'totals':{'documents':len(rows),'emitted':emitted_total,'member':member_total,'cited':sum(1 for r in rows if r['cited']),
                  'apr':apr_total,'pt':pt_total,'negatives':negatives,'docs_with_negative':docs_with_negative,
                  'divergences':len(divergences),
                  'severity_a':sev_overall.get('A',0)},
        'by_kind':[{'kind':k,'label':_kind_label(k),'count':v,'emitted':by_kind_emitted.get(k,0)} for k,v in by_kind.most_common()],
        'by_status':[{'status':k,'count':v} for k,v in by_status.most_common()],
        'by_site':[{'site':k,'count':v} for k,v in by_site.most_common(6)],
        'severity_overall':{k:sev_overall.get(k,0) for k in 'ABC'},
        'severity_steps':{k:sev_steps.get(k,0) for k in 'ABC'},
        'top_hazards':[{'label':k,'count':v} for k,v in hazards.most_common(6)],
        'top_risks':[{'label':k,'count':v} for k,v in risks.most_common(6)],
        'timeline':[{'label':f'{_MONTHS_PT[m-1]}/{str(y)[2:]}','emitted':timeline[(y,m)]['emitted'],'member':timeline[(y,m)]['member']} for y,m in months],
        'recent':recent,
        'divergences':divergences[:30],
    }


@app.get('/colaboradores/consulta',response_class=HTMLResponse)
def collaborator_lookup_page(request: Request, id: str=''):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    if not is_admin_user(user): raise HTTPException(403,'Somente administradores podem consultar colaboradores.')
    preselected=int(id) if str(id).isdigit() else 0
    return templates.TemplateResponse(request,'collaborator_lookup.html',context(request,preselected=preselected))


@app.get('/api/colaboradores/busca')
def collaborator_search(request: Request, q: str=''):
    user=current_user(request)
    if not user: raise HTTPException(401)
    if not is_admin_user(user): raise HTTPException(403)
    term=clean_single_line(q)
    digits=re.sub(r'\D','',term)
    if len(term)<2: return JSONResponse({'results':[]})
    with SessionLocal() as db:
        query=db.query(Participant)
        if digits and len(digits)>=3 and len(digits)==len(re.sub(r'[\s.\-]','',term)):
            query=query.filter(Participant.cpf.like(f'{digits}%'))
        else:
            parts=[p for p in term.split(' ') if p]
            for p in parts[:4]:
                query=query.filter(Participant.full_name.ilike(f'%{p}%'))
        found=query.order_by(Participant.active.desc(),Participant.full_name).limit(15).all()
        companies={c.id:c.name for c in db.query(Company).all()}
        results=[{'id':p.id,'name':p.full_name,'company':companies.get(p.company_id,''),'job':p.job_title or '',
                  'cpf':cpf_mask(p.cpf),'active':bool(p.active)} for p in found]
    return JSONResponse({'results':results},headers={'Cache-Control':'no-store'})


@app.get('/api/colaboradores/{participant_id}/painel')
def collaborator_dashboard_api(request: Request, participant_id: int):
    user=current_user(request)
    if not user: raise HTTPException(401)
    if not is_admin_user(user): raise HTTPException(403)
    data=collaborator_insights(user,participant_id)
    audit(user.id,'consulta_colaborador',f'participante={participant_id} | documentos={data["totals"]["documents"]}')
    return JSONResponse(data,headers={'Cache-Control':'no-store'})


# -------------------- V36.18.98 — APR offline com assinatura manual e aprovação manual --------------------
# Sem internet, o técnico preenche a APR e as PTs, cada integrante assina na tela
# do mesmo aparelho (rubrica + CPF) e o líder aprova com rubrica + senha. Tudo
# fica na fila do aparelho e chega aqui em um único pacote quando a conexão volta.
# O servidor confere CPF de cada integrante e a senha do líder; se a senha não
# conferir, a APR segue para a aprovação online normal.
from starlette.datastructures import FormData as _SPFormData


class _OfflineFormShim:
    """Permite reaproveitar parse_apr/parse_permit com uma parte do formulário."""
    def __init__(self, request: Request, items: list[tuple[str,Any]]):
        self._request=request; self._form=_SPFormData(items)
        # A integridade pertence ao pacote recebido, não a esta parte da APR/PT.
        self._offline_original_form=request._form
        self.session=request.session; self.client=request.client; self.headers=request.headers
    async def form(self): return self._form


def _offline_capture_moment(raw: str) -> datetime:
    try:
        moment=datetime.fromisoformat(clean(raw).replace('Z','+00:00'))
        if moment.tzinfo: moment=moment.astimezone(LOCAL_TZ).replace(tzinfo=None)
    except Exception:
        raise ValueError('Horário de registro offline inválido.')
    current=now()
    if moment>current+timedelta(minutes=15):
        raise ValueError('O horário do aparelho está adiantado em relação ao servidor. Ajuste a data/hora do celular e envie novamente.')
    if moment<current-timedelta(days=6):
        raise ValueError('Este registro offline tem mais de 6 dias e ficou fora da vigência possível da APR. Refaça a APR com internet.')
    return moment


def _offline_pts_blocking(apr_data: dict) -> list[str]:
    out=[]
    with SessionLocal() as db:
        for rid in _linked_history_ids(apr_data):
            t=db.get(Document,rid)
            if not t or t.kind not in APR_CRITICAL_KIND_PERMIT or t.status in ('Finalizada','Cancelado'): continue
            bad,_=_permit_checklist_issues(doc_data(t))
            if bad: out.append(APR_CRITICAL_KIND_PERMIT[t.kind])
    return out


def _find_offline_bundle_apr(key: str) -> Document|None:
    if not re.fullmatch(r'[A-Za-z0-9%/_.:\-]{6,200}',key or ''): return None
    with SessionLocal() as db:
        for cand in db.query(Document).filter(Document.kind=='apr',Document.data_json.like(f'%{key}%')).order_by(Document.id.desc()).limit(5).all():
            if clean(doc_data(cand).get('offline_bundle_id'))==key:
                db.expunge(cand); return cand
    return None


@app.post('/apr/offline-bundle')
async def apr_offline_bundle(request: Request):
    user=current_user(request)
    if not user: return RedirectResponse('/login',303)
    form=await request.form(); verify_csrf(request,form.get('csrf_token'))
    key=clean(form.get('offline_bundle_id'))
    existing=_find_offline_bundle_apr(key) if key else None
    if existing and existing.status=='Finalizada':
        flash(request,f'{doc_reference_code(existing)} já havia sido sincronizada e aprovada.','success')
        return RedirectResponse(f'/document/{existing.id}/pdf',303)
    if existing and existing.status=='Aguardando aprovação':
        flash(request,f'{doc_reference_code(existing)} já foi recebida e está aguardando aprovação online.','error')
        return RedirectResponse(f'/apr/{existing.id}/edit',303)
    try:
        return await _apr_offline_bundle_apply(request,user,form,existing)
    except HTTPException:
        raise
    except Exception as exc:
        import logging; logging.getLogger(__name__).exception('Falha no pacote offline da APR')
        target=_find_offline_bundle_apr(key) if key else None
        flash(request,f'O pacote offline chegou, mas não pôde ser concluído ({exc}). Abra a APR e finalize com internet.','error')
        return RedirectResponse(f'/apr/{target.id}/edit' if target else '/apr/new',303)


async def _apr_offline_bundle_apply(request: Request, user: User, form, existing: Document|None):
    items=list(form.multi_items())
    apr_items=[(k,v) for k,v in items if not re.match(r'^pt\d+__',k) and not k.startswith('offline_')]
    pt_groups={}
    for k,v in items:
        m=re.match(r'^pt(\d+)__(.+)$',k)
        if m: pt_groups.setdefault(int(m.group(1)),[]).append((m.group(2),v))
    target_url='/apr/new'
    try:
        moment=_offline_capture_moment(form.get('offline_captured_at'))
    except ValueError as e:
        flash(request,str(e),'error'); return RedirectResponse(target_url,303)

    # 1) APR: novo documento ou rascunho já existente aberto no aparelho.
    doc=existing
    raw_doc=clean(form.get('offline_apr_doc_id'))
    if existing and existing.status=='Pendente assinatura':
        # Reenvio após falha na etapa de aprovação: retoma do ponto em que parou.
        return await _apr_offline_bundle_approve(request,user,form,existing,doc_data(existing),_offline_capture_moment(form.get('offline_captured_at')))
    if not doc and raw_doc.isdigit():
        doc=get_document(int(raw_doc))
        if doc.kind!='apr' or not user_can_access_document(user,doc): raise HTTPException(403)
        if doc.status!='Rascunho':
            flash(request,f'{doc_reference_code(doc)} já não está em rascunho no servidor (situação: {doc.status}). O pacote offline não foi aplicado.','error')
            return RedirectResponse(f'/apr/{doc.id}/edit',303)
    old=doc_data(doc) if doc else apr_defaults()
    d,_=await parse_apr(_OfflineFormShim(request,apr_items),old)
    d['apr_date']=moment.strftime('%d/%m/%Y'); d['apr_time']=clean(d.get('apr_time')) or moment.strftime('%H:%M')
    d['offline_bundle']='1'; d['offline_captured_at']=moment.strftime('%d/%m/%Y %H:%M'); d['offline_bundle_id']=clean(form.get('offline_bundle_id'))
    d['offline_registered_by_id']=str(user.id); d['offline_registered_by_name']=user.full_name or user.username
    saved=save_doc(doc,'apr',d,user,'Rascunho'); target_url=f'/apr/{saved.id}/edit'
    issues=apr_completion_issues(d)
    if issues:
        d['_show_completion_issues']=True
        save_validation_state(saved,'apr',d,user,apr_validation_fields(d),'Rascunho')
        flash(request,f'APR salva como rascunho, mas faltam {len(issues)} item(ns): '+'; '.join(i['message'] for i in issues[:4])+'. Assinaturas e aprovação offline não foram aplicadas.','error')
        return RedirectResponse(target_url,303)

    # 2) PTs preenchidas offline (atividade crítica).
    names_needed=[p for p in (d.get('critical_permits') or []) if p in APR_CRITICAL_PERMITS] if d.get('critical_activity')=='SIM' else []
    filled={}
    for idx,group in sorted(pt_groups.items()):
        name=clean(dict(group).get('permit_name'))
        if name in names_needed: filled[name]=group
    missing=[n for n in names_needed if n not in filled]
    if missing:
        flash(request,'APR salva como rascunho. Faltou preencher offline: '+', '.join(missing)+'. Conclua as PTs com internet.','error')
        return RedirectResponse(target_url,303)
    apr_data=doc_data(saved)
    for name in names_needed:
        try:
            pt_doc=ensure_linked_permit(saved,apr_data,name,user)
        except ValueError as e:
            flash(request,f'APR salva como rascunho. {e}','error'); return RedirectResponse(target_url,303)
        apr_data=doc_data(get_document(saved.id))
        kind=APR_CRITICAL_PERMIT_KIND[name]
        group=[(k,v) for k,v in filled[name] if k not in ('permit_name','csrf_token','action')]+[('csrf_token',form.get('csrf_token'))]
        pd,_=await parse_permit(_OfflineFormShim(request,group),kind,doc_data(pt_doc))
        bad,blank=_permit_checklist_issues(pd)
        if bad or blank or not clean(pd.get('activity')):
            save_doc(pt_doc,kind,pd,user,'Rascunho')
            problem=('NÃO nos itens '+', '.join(map(str,bad)) if bad else ('sem resposta nos itens '+', '.join(map(str,blank)) if blank else 'sem descrição da atividade'))
            flash(request,f'{name}: {problem}. A APR ficou em rascunho; corrija a PT com internet.','error')
            return RedirectResponse(target_url,303)
        pd['open_date']=moment.strftime('%d/%m/%Y'); pd['open_time']=moment.strftime('%H:%M')
        pd['pre_signature_completed']='1'; pd['offline_bundle']='1'; pd['offline_captured_at']=moment.strftime('%d/%m/%Y %H:%M')
        save_doc(pt_doc,kind,pd,user,'Rascunho')
    saved=get_document(saved.id); d=doc_data(saved)

    # 3) Assinatura manual de cada integrante (rubrica + CPF conferido aqui).
    workers=[dict(w) for w in (d.get('workers') or []) if clean(w.get('participant_id'))]
    if not workers:
        flash(request,'APR salva como rascunho: inclua pelo menos um integrante cadastrado.','error'); return RedirectResponse(target_url,303)
    errors=[]
    with SessionLocal() as db:
        for i,w in enumerate(d.get('workers') or []):
            if not clean(w.get('participant_id')): continue
            participant=db.get(Participant,int(w['participant_id'])) if str(w['participant_id']).isdigit() else None
            company=db.get(Company,participant.company_id) if participant else None
            if not participant or not participant.active or not company or not company.active:
                errors.append(f'Integrante {i+1}: cadastro indisponível.'); continue
            typed=cpf_digits(form.get(f'offline_cpf_{i}'))
            if typed!=participant.cpf:
                errors.append(f'{participant.full_name}: CPF digitado não confere com o cadastro.'); continue
            sig=save_signature(form.get(f'offline_sig_{i}'),'',f'{d.get("code") or saved.code}_offline_participant_{i+1}')
            if not sig:
                errors.append(f'{participant.full_name}: rubrica não registrada.'); continue
            signer=db.get(User,participant.user_id) if participant.user_id else None
            w.update({'participant_id':str(participant.id),'participant_user_id':str(participant.user_id or ''),'cpf':participant.cpf,'company':company.name,
                      'worker':participant.full_name,'role':participant.job_title or '','signature':'RUBRICA','signature_image':sig,
                      'date':moment.strftime('%d/%m/%Y'),'signature_status':'Assinado','signed_at':moment.strftime('%d/%m/%Y %H:%M'),
                      'signed_by_user_id':str(participant.user_id or ''),'signed_by_name':participant.full_name,
                      'signature_capture_mode':'Offline presencial (rubrica + CPF)','signature_collected_by_user_id':str(user.id),
                      'signature_collected_by_name':user.full_name or user.username})
            if signer:
                db.expunge(signer)
                _maybe_record_initial_signature_as_daily(w,d,signature_image=sig,signer=signer,signed_at=moment,mode='Assinatura inicial offline presencial')
            d['workers'][i]=w
    if errors:
        save_doc(saved,'apr',d,user,'Rascunho')
        flash(request,'APR e PTs salvas como rascunho, mas as assinaturas não foram aceitas: '+' '.join(errors[:6])+' Colete as assinaturas com internet.','error')
        return RedirectResponse(target_url,303)
    d['participant_signature_status']='Concluída'
    d['participant_signatures_requested_at']=moment.strftime('%d/%m/%Y %H:%M')
    d['participant_signatures_requested_by_id']=str(user.id); d['participant_signatures_requested_by_name']=user.full_name or user.username
    saved=save_doc(saved,'apr',d,user,'Pendente assinatura')
    _sync_apr_signatures_to_linked_permits({**d,'_document_id':str(saved.id)})
    audit(user.id,'apr_offline_assinaturas',f'{saved.code} | integrantes={len(workers)} | registrado={d["offline_captured_at"]}')

    return await _apr_offline_bundle_approve(request,user,form,saved,d,moment)


async def _apr_offline_bundle_approve(request: Request, user: User, form, saved: Document, d: dict, moment: datetime):
    target_url=f'/apr/{saved.id}/edit'
    # 4) Aprovação manual do líder (rubrica + senha conferida aqui).
    try:
        approvers=_selected_approvers_for_submission(d)
    except Exception as e:
        flash(request,f'Assinaturas registradas, mas {e}','error'); return RedirectResponse(target_url,303)
    leader=approvers[0]
    password=str(form.get('offline_leader_password') or '')
    leader_sig_raw=form.get('offline_leader_sig')
    ip=request.client.host if request.client else 'unknown'
    password_ok=False
    if password and _login_attempt_allowed(ip,leader.username):
        with SessionLocal() as db:
            fresh=db.get(User,leader.id)
            password_ok=bool(fresh and fresh.active and verify_password(password,fresh.password_hash))
        if not password_ok: _login_record_failure(ip,leader.username)
    allowed_leader=any(a.id==leader.id for a in active_admins(d.get('cluster',''),d.get('site','')))
    if not (password_ok and allowed_leader and clean(leader_sig_raw)):
        # Fallback seguro: segue para a aprovação online do líder.
        resp=_submit_apr_for_approval(request,user,saved,d)
        reason='a senha do líder não conferiu' if not password_ok else ('o líder não tem acesso a este site' if not allowed_leader else 'faltou a rubrica do líder')
        flash(request,f'Assinaturas da equipe registradas, mas {reason}. A APR foi enviada para aprovação online de {leader.full_name or leader.username}.','error')
        audit(user.id,'apr_offline_aprovacao_recusada',f'{saved.code} | lider={leader.username} | motivo={reason}')
        return resp
    blocking=apr_no_unacknowledged(d)
    if blocking or _offline_pts_blocking(d):
        flash(request,'Aprovação offline recusada: há resposta NÃO sem justificativa na APR ou em PT vinculada.','error')
        return _submit_apr_for_approval(request,user,saved,d)
    sig=save_signature(leader_sig_raw,'',f'{d.get("code") or saved.code}_offline_approval_1')
    start=moment.date(); end=start+timedelta(days=6)
    approvals=[dict(a) for a in (d.get('approvals') or [])[:5]]
    while len(approvals)<5: approvals.append({})
    approvals[0]={'name':leader.full_name or leader.username,'role':'Líder ou responsável pela atividade','start':start.strftime('%d/%m/%Y'),
                  'end':end.strftime('%d/%m/%Y'),'signature':'RUBRICA','signature_image':sig,'mode':'Aprovação manual offline (rubrica + senha)'}
    d['approvals']=approvals
    d['approver_name']=leader.full_name or leader.username
    d['approved_by_id']=str(leader.id); d['approved_by_name']=leader.full_name or leader.username
    d['approved_at']=moment.strftime('%d/%m/%Y %H:%M'); d['offline_manual_approval']='1'
    d['approval_requested_at']=moment.strftime('%d/%m/%Y %H:%M'); d['submitted_by_id']=str(user.id); d['submitted_by_name']=user.full_name or user.username
    d['status']='Finalizada'
    saved=save_doc(saved,'apr',d,user,'Finalizada')
    try:
        _finalize_prepared_linked_permits(saved,d,leader)
        saved=finalize_pdf(saved,d)
    except Exception as e:
        with SessionLocal() as db:
            t=db.get(Document,saved.id); t.status='Aguardando aprovação'; t.finalized_at=None
            t.data_json=json.dumps({**d,'status':'Aguardando aprovação'},ensure_ascii=False); db.commit()
        notify_apr_approval(get_document(saved.id),approvers,user)
        flash(request,f'Assinaturas e aprovação recebidas, mas o PDF não foi gerado ({e}). A APR ficou aguardando aprovação online.','error')
        return RedirectResponse(target_url,303)
    audit(leader.id,'aprovar_apr_offline_manual',f'{saved.code} | registrado_por={user.username} | em={d["approved_at"]}')
    notify_document_creator(saved,'apr_creator_approved',f'{doc_reference_code(saved)}: aprovada manualmente (offline) por {d["approved_by_name"]}. O PDF está disponível.',replace=True)
    flash(request,f'{doc_reference_code(saved)} sincronizada: assinaturas da equipe e aprovação manual do líder registradas. PDF gerado.','success')
    return RedirectResponse(f'/document/{saved.id}/pdf',303)


@app.get('/api/offline/participants')
def offline_participants_directory(request: Request):
    """Lista de colaboradores para busca por nome sem internet (sem CPF no aparelho)."""
    user=current_user(request)
    if not user: raise HTTPException(401)
    with SessionLocal() as db:
        rows=(db.query(Participant,Company).join(Company,Participant.company_id==Company.id)
              .filter(Participant.active==True,Company.active==True).order_by(Participant.full_name).all())
        out=[{'participant_id':p.id,'full_name':p.full_name,'company':c.name,'job_title':p.job_title or '','user_id':p.user_id or '','can_sign':bool(p.user_id)} for p,c in rows]
    return JSONResponse({'people':out,'count':len(out)},headers={'Cache-Control':'no-store, private'})
