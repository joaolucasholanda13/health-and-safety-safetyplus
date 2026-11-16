from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

try:
    from pywebpush import webpush, WebPushException
except Exception:  # pacote opcional durante atualização/testes locais antigos
    webpush = None
    WebPushException = Exception


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=') .decode('ascii')


def _private_key_path(storage_dir: Path) -> Path:
    custom = (os.getenv('VAPID_PRIVATE_KEY_FILE') or '').strip()
    return Path(custom).expanduser().resolve() if custom else (storage_dir / 'push_vapid_private.pem')


def ensure_vapid_private_key(storage_dir: Path) -> Path:
    """Cria uma chave VAPID P-256 persistente na primeira execução.

    A chave precisa permanecer estável; trocar a chave invalida as inscrições push
    já salvas nos celulares/navegadores.
    """
    path = _private_key_path(storage_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return path
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass
    return path


def vapid_public_key(storage_dir: Path) -> str:
    path = ensure_vapid_private_key(storage_dir)
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return _b64url(public)


def push_backend_available() -> bool:
    return webpush is not None


def vapid_subject() -> str:
    configured = (os.getenv('VAPID_SUBJECT') or '').strip()
    if configured:
        return configured
    domain = (os.getenv('DOMAIN') or '').strip().strip('/')
    if domain and domain not in {'localhost', '127.0.0.1'}:
        if domain.startswith('https://') or domain.startswith('http://'):
            return domain
        return 'https://' + domain
    return 'mailto:safetyplus@localhost'


def send_web_push(subscription: Any, payload: dict[str, Any], storage_dir: Path) -> tuple[bool, bool, str]:
    """Envia Web Push.

    Retorna (enviado, inscricao_expirada, detalhe). Inscrições 404/410 devem ser
    desativadas para não tentar novamente a cada evento.
    """
    if webpush is None:
        return False, False, 'pywebpush não instalado'
    endpoint = (getattr(subscription, 'endpoint', '') or '').strip()
    p256dh = (getattr(subscription, 'p256dh', '') or '').strip()
    auth = (getattr(subscription, 'auth', '') or '').strip()
    if not endpoint or not p256dh or not auth:
        return False, True, 'inscrição incompleta'
    try:
        webpush(
            subscription_info={
                'endpoint': endpoint,
                'keys': {'p256dh': p256dh, 'auth': auth},
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=str(ensure_vapid_private_key(storage_dir)),
            vapid_claims={'sub': vapid_subject()},
            timeout=8,
        )
        return True, False, ''
    except WebPushException as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        gone = status in {404, 410}
        return False, gone, f'HTTP {status or "?"}: {exc}'[:500]
    except Exception as exc:
        return False, False, str(exc)[:500]
