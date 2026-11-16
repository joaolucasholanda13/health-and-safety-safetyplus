"""Login único (SSO) com Microsoft Entra ID via OpenID Connect.

Ativado por variáveis de ambiente (ver .env.example). O SSO só autentica:
o usuário precisa já existir e estar ativo, com o ``username`` igual ao e-mail
corporativo. Perfil e escopo continuam sendo definidos no cadastro do sistema.
"""
from __future__ import annotations

import os
from functools import lru_cache


def enabled() -> bool:
    return (os.getenv('SSO_ENABLED', '').strip().lower() in {'1', 'true', 'yes', 'sim'}
            and bool(tenant_id() and client_id() and client_secret()))


def tenant_id() -> str:
    return os.getenv('SSO_TENANT_ID', '').strip()


def client_id() -> str:
    return os.getenv('SSO_CLIENT_ID', '').strip()


def client_secret() -> str:
    return os.getenv('SSO_CLIENT_SECRET', '').strip()


def allowed_domains() -> set[str]:
    raw = os.getenv('SSO_ALLOWED_DOMAINS', '')
    return {d.strip().lower().lstrip('@') for d in raw.split(',') if d.strip()}


def redirect_uri() -> str:
    explicit = os.getenv('SSO_REDIRECT_URI', '').strip()
    if explicit:
        return explicit
    domain = os.getenv('DOMAIN', '').strip().rstrip('/')
    if not domain:
        return ''
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain
    return domain + '/sso/callback'


@lru_cache(maxsize=1)
def client():
    """Cliente OIDC (cria uma vez; metadados e chaves públicas são baixados sob demanda)."""
    from authlib.integrations.starlette_client import OAuth
    oauth = OAuth()
    oauth.register(
        name='entra',
        client_id=client_id(),
        client_secret=client_secret(),
        server_metadata_url=f'https://login.microsoftonline.com/{tenant_id()}/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile', 'code_challenge_method': 'S256'},
    )
    return oauth.entra


def email_from_claims(claims: dict) -> str:
    """E-mail do usuário no token; cai para o UPN quando 'email' não vem configurado."""
    for key in ('email', 'preferred_username', 'upn'):
        value = str(claims.get(key) or '').strip().lower()
        if '@' in value:
            return value
    return ''


def validate_claims(claims: dict) -> tuple[str, str]:
    """Devolve (email, erro). Erro vazio significa que as declarações são aceitáveis."""
    if tenant_id() and str(claims.get('tid') or '').lower() not in {'', tenant_id().lower()}:
        return '', 'Conta de outro diretório.'
    email = email_from_claims(claims)
    if not email:
        return '', 'O provedor não informou o e-mail.'
    domains = allowed_domains()
    if domains and email.rsplit('@', 1)[-1] not in domains:
        return email, 'Domínio de e-mail não permitido.'
    return email, ''
