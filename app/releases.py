"""Versões do Safety Plus e novidades mostradas aos usuários.

Para publicar uma atualização: adicione um item NO TOPO de RELEASES (versão nova,
data e textos curtos). A versão do topo vira APP_VERSION automaticamente: ela
renova o cache do app, avisa os usuários ("Nova versão disponível") e abre a janela
"O que há de novo" uma vez por usuário.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

RELEASES: list[dict] = [
    {
        'version': '2026.11.16.5',
        'date': '16/11/2026',
        'title': 'APR offline com rubricas',
        'items': [
            'Com sinal fraco, ao avançar a APR sem internet o app abre o assistente de rubricas da equipe e do líder.',
            'Antes, a APR podia ser guardada só como rascunho, sem as rubricas.',
        ],
    },
    {
        'version': '2026.11.16.4',
        'date': '16/11/2026',
        'title': 'Auditoria mais detalhada',
        'items': [
            'O painel DEV passa a mostrar IP de origem, navegador e operação nos novos registros de auditoria.',
            'Alterações de documentos e cadastros DEV ficam mais claras, com valores anteriores e novos, busca ampliada e exportação CSV.',
            'Os registros anteriores são preservados; senhas e tokens não são incluídos nas diferenças dos documentos.',
        ],
    },
    {
        'version': '2026.11.16.3',
        'date': '16/11/2026',
        'title': 'Testes automáticos dos módulos',
        'items': [
            'O robô executa verificações isoladas de APRs, PTs, checklists e RACs, com resultados no painel DEV.',
            'Corrigida a geração do PDF do checklist de veículo leve para incluir os sete dias da semana.',
        ],
    },
    {
        'version': '2026.11.16.2',
        'date': '16/11/2026',
        'title': 'Robô de manutenção no painel DEV',
        'items': [
            'Monitoramento DEV passa a mostrar o estado do supervisor externo e os backups da VPS.',
            'Identificação de status desatualizado e consulta dos agendamentos, sem duplicar o backup interno.',
        ],
    },
    {
        'version': '2026.11.16.1',
        'date': '16/11/2026',
        'title': 'Correções nas rubricas e assinaturas',
        'items': [
            'Corrigida a captura da rubrica diária da APR ao abrir a área de assinatura.',
            'Imagens vazias não são aceitas como novas assinaturas; corrigidos o toque sem traço e a limpeza das rubricas.',
            'A rubrica da RAC é preservada ao redimensionar a tela.',
        ],
    },
    {
        'version': '2026.11.12.1',
        'date': '12/11/2026',
        'title': 'Arquivos dos Momentos de Segurança preservados',
        'items': [
            'Os PDFs da biblioteca de Momentos de Segurança passam a usar armazenamento persistente, preservando os uploads nas atualizações do servidor.',
            'Os arquivos ainda disponíveis na pasta antiga são migrados automaticamente e incluídos no backup completo.',
        ],
    },
    {
        'version': '2026.11.04',
        'date': '04/11/2026',
        'title': 'Checklist mais seguro, aprovação com justificativa e novos acessos',
        'items': [
            'APR: resposta NÃO no checklist agora não bloqueia — exige justificativa e o aprovador confirma a leitura.',
            'Assinatura com token (opcional), assinatura manual presencial e histórico de alterações dos documentos.',
            'Observações e novas etapas em APRs finalizadas, e Clonar APR com um toque.',
            'Colaboradores: escolha o perfil (Usuário, Administrador ou Super Administrador).',
            'Permissões de câmera, microfone e notificações pedidas no primeiro acesso.',
        ],
    },
]

BASE_VERSION: str = RELEASES[0]['version']
APP_VERSION: str = BASE_VERSION  # compatibilidade; o valor em uso vem de get_version()

_cache: dict = {'mtime': None, 'path': None, 'data': []}


def _file(storage_dir: Path) -> Path:
    return Path(storage_dir) / 'releases.json'


def _published(storage_dir: Path) -> list[dict]:
    """Atualizações publicadas pelo DEV (releases.json no STORAGE_DIR)."""
    path = _file(storage_dir)
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return []
    if _cache['path'] == str(path) and _cache['mtime'] == mtime:
        return _cache['data']
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        data = [r for r in data if isinstance(r, dict) and r.get('version')]
    except Exception:
        data = []
    _cache.update(path=str(path), mtime=mtime, data=data)
    return data


def _overrides_file(storage_dir: Path) -> Path:
    return Path(storage_dir) / 'releases_overrides.json'


def _overrides(storage_dir: Path) -> dict:
    """Edições e exclusões do histórico feitas pelo DEV (valem para qualquer versão)."""
    try:
        d = json.loads(_overrides_file(storage_dir).read_text(encoding='utf-8'))
        return {'edits': dict(d.get('edits') or {}), 'deleted': list(d.get('deleted') or [])}
    except Exception:
        return {'edits': {}, 'deleted': []}


def _save_overrides(storage_dir: Path, ov: dict) -> None:
    path = _overrides_file(storage_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(ov, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)


def _raw_releases(storage_dir: Path) -> list[dict]:
    return _published(storage_dir) + RELEASES


def get_releases(storage_dir: Path) -> list[dict]:
    """Mais recente primeiro (publicadas pelo DEV e depois as do código), já com as
    edições aplicadas e sem as versões excluídas. A versão atual nunca é excluída."""
    raw = _raw_releases(storage_dir)
    ov = _overrides(storage_dir)
    out = []
    for i, r in enumerate(raw):
        if i > 0 and r['version'] in ov['deleted']:
            continue
        e = ov['edits'].get(r['version'])
        out.append({**r, **{k: e[k] for k in ('title', 'items') if k in e}, 'edited': True} if e else dict(r))
    return out


def edit_release(storage_dir: Path, version: str, title: str, items: list[str]) -> bool:
    if not any(r['version'] == version for r in _raw_releases(storage_dir)):
        return False
    ov = _overrides(storage_dir)
    ov['edits'][version] = {'title': title.strip()[:160], 'items': [i.strip()[:300] for i in items if i.strip()][:12]}
    _save_overrides(storage_dir, ov)
    return True


def delete_release(storage_dir: Path, version: str) -> str:
    """Retorna '' se excluiu, ou o motivo de não ter excluído."""
    raw = _raw_releases(storage_dir)
    if not any(r['version'] == version for r in raw):
        return 'Versão não encontrada.'
    if raw[0]['version'] == version:
        return 'A versão atual não pode ser excluída. Edite o texto ou publique uma nova atualização antes.'
    ov = _overrides(storage_dir)
    if version not in ov['deleted']:
        ov['deleted'].append(version)
    _save_overrides(storage_dir, ov)
    return ''


def get_version(storage_dir: Path) -> str:
    return _raw_releases(storage_dir)[0]['version']


def publish_release(storage_dir: Path, title: str, items: list[str], author: str) -> dict:
    """Publica uma atualização: gera a versão nova (data + sequência) e grava no topo."""
    today = datetime.now()
    prefix = today.strftime('%Y.%m.%d')
    existing = [r['version'] for r in _raw_releases(storage_dir)]
    seq = 1
    while f'{prefix}.{seq}' in existing:
        seq += 1
    release = {
        'version': f'{prefix}.{seq}',
        'date': today.strftime('%d/%m/%Y'),
        'title': title.strip()[:160],
        'items': [i.strip()[:300] for i in items if i.strip()][:12],
        'published_by': author,
    }
    path = _file(storage_dir)
    data = list(_published(storage_dir))
    data.insert(0, release)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)
    return release
