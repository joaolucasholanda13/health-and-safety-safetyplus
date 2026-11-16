from __future__ import annotations
import base64, hashlib, hmac, os, secrets
from pathlib import Path
from starlette.requests import Request
from fastapi import HTTPException
from .database import SessionLocal, User

ITERATIONS = 390_000

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(dk).decode()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters, salt_b64, hash_b64 = stored.split('$', 3)
        if scheme != 'pbkdf2_sha256': return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(hash_b64.encode())
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(iters))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def revoke_password_sessions(storage: Path, user_id: int, request: Request | None = None) -> None:
    """Encerra as sessões anteriores à troca de senha e renova a sessão atual."""
    from . import ti_tools
    cutoff = ti_tools.force_logout(storage, user_id)
    if request is not None and request.session.get('user_id') == user_id:
        request.session['t'] = cutoff

from contextvars import ContextVar
VIEW_CLUSTER: ContextVar[str] = ContextVar('view_cluster', default='')

def current_user(request: Request) -> User | None:
    uid = request.session.get('user_id')
    if not uid: return None
    with SessionLocal() as db:
        u = db.get(User, int(uid))
        if not u or not u.active: return None
        from . import ti_tools
        if ti_tools.session_revoked(u.id, float(request.session.get('t') or 0)):
            request.session.clear()
            return None
        db.expunge(u)
        VIEW_CLUSTER.set(str(request.session.get('view_cluster') or '') if u.role in ('Super Administrador','DEV') else '')
        return u

def require_user(request: Request) -> User:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Não autenticado')
    return user

def require_admin(request: Request) -> User:
    user = require_user(request)
    if user.role not in {'Administrador','Super Administrador','DEV'}:
        raise HTTPException(status_code=403, detail='Acesso restrito ao administrador')
    return user

def require_super_admin(request: Request) -> User:
    user = require_user(request)
    if user.role not in {'Super Administrador','DEV'}:
        raise HTTPException(status_code=403, detail='Acesso restrito ao Super Administrador')
    return user

def require_dev(request: Request) -> User:
    user = require_user(request)
    if user.role != 'DEV':
        raise HTTPException(status_code=403, detail='Acesso restrito ao DEV')
    return user

def csrf_token(request: Request) -> str:
    token = request.session.get('csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        request.session['csrf_token'] = token
    return token

def verify_csrf(request: Request, submitted: str | None):
    # O cabeçalho usa o mesmo token da sessão, inclusive em envios multipart.
    # Nunca aceita um formulário incompleto quando o cliente informa a contagem.
    if request.headers.get('x-sp-offline-sync') == '1':
        count = request.headers.get('x-sp-offline-field-count')
        if count is not None:
            form = getattr(request, '_offline_original_form', None)
            if form is None:
                form = getattr(request, '_form', None)
            received = sum(1 for key, _ in form.multi_items() if key != 'csrf_token') if form is not None else 0
            if not count.isdigit() or received != int(count):
                raise HTTPException(400, f'O formulário chegou incompleto ao servidor (esperados: {count}; recebidos: {received}). Os dados continuam no aparelho; tente enviar novamente.')
    submitted = submitted or request.headers.get('x-csrf-token')
    expected = request.session.get('csrf_token')
    if not expected or not submitted or not hmac.compare_digest(expected, submitted):
        if not expected: why = 'o servidor não recebeu a sua sessão'
        elif not submitted: why = 'o envio chegou sem o token'
        else: why = 'o token enviado é diferente do da sessão'
        import logging
        logging.getLogger(__name__).warning(
            'CSRF recusado: path=%s reason=%s authenticated=%s submitted_present=%s offline_sync=%s',
            request.url.path, why, bool(request.session.get('user_id')), bool(submitted),
            request.headers.get('x-sp-offline-sync') == '1',
        )
        raise HTTPException(status_code=403, detail=f'Sessão expirada ou token inválido ({why}). Atualize a página.')
