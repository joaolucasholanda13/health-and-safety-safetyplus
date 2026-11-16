"""Metadados de auditoria por requisição, isolados inclusive entre threads."""
from contextvars import ContextVar
import ipaddress
import re
import secrets

_request = ContextVar('audit_request', default=None)
_request_id = ContextVar('audit_request_id', default='')


def metadata():
    request = _request.get()
    if request is None:
        return dict(ip_address='', user_agent='', http_method='', request_path='', request_id='')
    try:
        ip = str(ipaddress.ip_address(request.client.host)) if request.client else ''
    except ValueError:
        ip = ''
    # Usa a rota parametrizada, não a URL que pode conter tokens/CPFs.
    route = request.scope.get('route')
    path = getattr(route, 'path', '')
    ua = re.sub(r'[\x00-\x1f\x7f]', '', request.headers.get('user-agent', ''))[:400]
    return dict(ip_address=ip, user_agent=ua, http_method=request.method[:10],
                request_path=path[:250], request_id=_request_id.get())


class AuditContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        from starlette.requests import Request
        token = _request.set(Request(scope))
        id_token = _request_id.set(secrets.token_hex(12))
        try:
            await self.app(scope, receive, send)
        finally:
            _request.reset(token)
            _request_id.reset(id_token)


def audit_label(action):
    labels = {
        'login': 'Entrou no sistema', 'login_falha': 'Tentativa de login recusada',
        'logout': 'Saiu do sistema', 'criar_documento': 'Criou um documento',
        'editar_documento': 'Alterou um documento', 'assinar_apr_diaria': 'Registrou rubrica diária da APR',
        'assinar_apr': 'Assinou a APR', 'aprovar_apr': 'Aprovou a APR',
        'reprovar_apr': 'Reprovou a APR', 'iniciar_pt': 'Abriu a PT',
        'finalizar_pt': 'Encerrou a PT', 'finalizar_rac': 'Finalizou a RAC',
        'salvar_rascunho_rac': 'Salvou rascunho da RAC',
        'concluir_dia': 'Concluiu o checklist do dia',
        'concluir_inspecao_periodo': 'Concluiu período da inspeção',
        'finalizar_inspecao': 'Finalizou a inspeção',
        'trocar_senha': 'Alterou a própria senha',
        'alterar_documento_admin': 'Editou documento como administrador',
        'ti_atualizar_usuario': 'Atualizou cadastro ou acesso de usuário',
        'acesso_negado_documento': 'Tentou acessar documento sem permissão',
    }
    return labels.get(action, action.replace('_', ' ').capitalize())


def detail_view(value):
    """Apresenta detalhes estruturados sem cortar silenciosamente o histórico."""
    import json
    try:
        parsed = json.loads(value or '')
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get('changes'), list):
        return {'text': '', 'document': parsed.get('code', ''),
                'title': parsed.get('title', ''), 'changes': parsed['changes'],
                'omitted': parsed.get('omitted_changes', 0)}
    return {'text': value or '', 'changes': [], 'document': '', 'title': '', 'omitted': 0}


def csv_cell(value):
    # Não permita que detalhes/navegadores sejam interpretados como fórmula no Excel.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + value
    return value
