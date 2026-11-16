"""Tipos de documento criados a partir de arquivo (área do DEV).

A planilha enviada vira um checklist no mesmo formato dos RACs: grupos com
itens. Depois de registrado, o tipo usa o formulário, a lista, o código
sequencial e o PDF dos RACs, sem nenhum código novo por documento.
"""
from __future__ import annotations
import io
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from .module_configs import RAC_MODULES, DOCUMENT_TITLES, PREFIXES

CUSTOM_KIND_PREFIX = 'custom_'

# Onde o novo documento aparece no sistema.
PLACEMENTS = {
    'rac': 'RAC (lista de RACs)',
    'permit': 'Permissões (emissão de PT)',
    'apr': 'APR (menu da APR)',
    'inspection': 'Inspeções Prévias (menu de Inspeções)',
    'policy': 'Política SST (página Política SST)',
    'tools': 'Ferramentas SST (página Ferramentas SST)',
}

# Tipos de resposta: (código, rótulo). Os códigos são os já tratados pelo
# sistema (ATENDE/NAO_ATENDE/NA e SIM/NAO); só o rótulo muda. O "negativo"
# exige plano de ação, como nos RACs.
GENERAL_PLACEMENTS = ('rac', 'permit', 'apr', 'inspection')
RESPONSE_PLACEMENTS = {
    # Política SST: ciência/cumprimento. Ferramentas SST: estado da ferramenta.
    'ciente': ('policy',), 'concordo': ('policy',), 'cumpre': ('policy',),
    'bom_ruim': ('tools',), 'apto': ('tools',), 'disponivel': ('tools',), 'funcionando': ('tools',),
}

def modes_for(placement: str) -> list[str]:
    """Chaves de RESPONSE_MODES permitidas para a posição escolhida."""
    return [k for k in RESPONSE_MODES if placement in RESPONSE_PLACEMENTS.get(k, GENERAL_PLACEMENTS)]


RESPONSE_MODES = {
    'atende': ('Atende / Não atende / N/A', [('ATENDE', 'Atende'), ('NAO_ATENDE', 'Não atende'), ('NA', 'N/A')]),
    'conforme': ('Conforme / Não conforme / N/A', [('ATENDE', 'Conforme'), ('NAO_ATENDE', 'Não conforme'), ('NA', 'N/A')]),
    'ok': ('OK / Não OK / N/A', [('ATENDE', 'OK'), ('NAO_ATENDE', 'Não OK'), ('NA', 'N/A')]),
    'sim_nao': ('Sim / Não / N/A', [('SIM', 'Sim'), ('NAO', 'Não'), ('NA', 'N/A')]),
    'sim_nao_sem_na': ('Sim / Não (sem N/A)', [('SIM', 'Sim'), ('NAO', 'Não')]),
    'ciente': ('Ciente / Não ciente / N/A', [('ATENDE', 'Ciente'), ('NAO_ATENDE', 'Não ciente'), ('NA', 'N/A')]),
    'concordo': ('Concordo / Não concordo / N/A', [('ATENDE', 'Concordo'), ('NAO_ATENDE', 'Não concordo'), ('NA', 'N/A')]),
    'cumpre': ('Cumpre / Não cumpre / N/A', [('ATENDE', 'Cumpre'), ('NAO_ATENDE', 'Não cumpre'), ('NA', 'N/A')]),
    'bom_ruim': ('Bom / Ruim / N/A', [('ATENDE', 'Bom'), ('NAO_ATENDE', 'Ruim'), ('NA', 'N/A')]),
    'apto': ('Apto / Inapto / N/A', [('ATENDE', 'Apto'), ('NAO_ATENDE', 'Inapto'), ('NA', 'N/A')]),
    'disponivel': ('Disponível / Indisponível / N/A', [('ATENDE', 'Disponível'), ('NAO_ATENDE', 'Indisponível'), ('NA', 'N/A')]),
    'funcionando': ('Funcionando / Com defeito / N/A', [('ATENDE', 'Funcionando'), ('NAO_ATENDE', 'Com defeito'), ('NA', 'N/A')]),
}
MAX_ITEMS = 400
_NUMBER_RE = re.compile(r'^\d+(?:\.\d+)*\.?$')


def _text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return re.sub(r'[ \t]+', ' ', str(value)).strip()


def slugify(value: str) -> str:
    raw = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '_', raw.lower()).strip('_')[:40]


def make_prefix(title: str, taken: set[str]) -> str:
    words = [w for w in re.split(r'[^A-Za-z0-9]+', unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().upper()) if w]
    base = ''.join(w[0] for w in words)[:4] or 'DOC'
    prefix = f'DOC-{base}'
    n = 2
    while prefix in taken:
        prefix = f'DOC-{base}{n}'; n += 1
    return prefix


def parse_checklist_xlsx(content: bytes) -> list[dict]:
    """Lê a primeira planilha e devolve grupos [{'name','items':[...]}].

    Regras: linha com uma única célula preenchida e sem numeração é título de
    grupo; as demais linhas com texto são itens (numeração opcional na primeira
    coluna). Linhas vazias são ignoradas.
    """
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    groups: list[dict] = []
    current = None
    total = 0
    for row in ws.iter_rows(values_only=True):
        cells = [_text(c) for c in row]
        filled = [c for c in cells if c]
        if not filled:
            continue
        if len(filled) == 1 and not _NUMBER_RE.match(filled[0]):
            only = filled[0]
            # Linha isolada curta ou em maiúsculas é título; frase longa é item.
            if (len(only) <= 90 and not only.endswith(('?', '.', ':'))) or only.isupper():
                current = {'name': only, 'items': []}
                groups.append(current)
                continue
        number = ''
        if cells and _NUMBER_RE.match(cells[0]) and len(filled) > 1:
            number = cells[0].rstrip('.')
            filled = [c for c in cells[1:] if c]
        text = max(filled, key=len)
        if len(text) < 3:
            continue
        if current is None:
            current = {'name': 'Itens', 'items': []}
            groups.append(current)
        idx = len(current['items']) + 1
        current['items'].append({'section': current['name'], 'number': number or str(idx), 'text': text, 'requirement': '', 'recommendation': ''})
        total += 1
        if total >= MAX_ITEMS:
            break
    return [g for g in groups if g['items']]


def _registry_path(storage: Path) -> Path:
    return storage / 'custom_docs' / 'registry.json'


def load_registry(storage: Path) -> dict[str, dict]:
    path = _registry_path(storage)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_registry(storage: Path, data: dict) -> None:
    path = _registry_path(storage)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)


def register(kind: str, cfg: dict) -> None:
    RAC_MODULES[kind] = cfg
    DOCUMENT_TITLES[kind] = cfg['title']
    PREFIXES[kind] = cfg['prefix']


def unregister(kind: str) -> None:
    RAC_MODULES.pop(kind, None)
    DOCUMENT_TITLES.pop(kind, None)
    PREFIXES.pop(kind, None)


def load_all(storage: Path) -> None:
    """Registra no startup os tipos já criados."""
    for kind, cfg in load_registry(storage).items():
        if kind.startswith(CUSTOM_KIND_PREFIX) and kind not in RAC_MODULES:
            register(kind, cfg)


def create_type(storage: Path, title: str, response_mode: str, placement: str, filename: str, content: bytes) -> tuple[str, dict]:
    placement = placement if placement in PLACEMENTS else 'rac'
    if response_mode not in modes_for(placement):
        raise ValueError('Esse tipo de resposta não está disponível para a posição escolhida.')
    groups = parse_checklist_xlsx(content)
    if not groups:
        raise ValueError('Não encontrei itens na planilha. Coloque um item por linha, com títulos de grupo em linhas próprias.')
    registry = load_registry(storage)
    base = slugify(title)
    if not base:
        raise ValueError('Informe um nome para o documento.')
    kind = f'{CUSTOM_KIND_PREFIX}{base}'
    if kind in RAC_MODULES or kind in registry:
        raise ValueError('Já existe um tipo de documento com esse nome.')
    taken = set(PREFIXES.values())
    source = f'{kind}.xlsx'
    folder = storage / 'custom_docs'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / source).write_bytes(content)
    cfg = {
        'title': title, 'short': title, 'icon': 'mi-clipboard', 'prefix': make_prefix(title, taken),
        'revision': 'Rev. 00', 'source_file': source, 'source_format': 'xlsx', 'custom': True,
        'response_mode': 'sim_nao' if response_mode.startswith('sim_nao') else 'atende',
        'response_options': [list(x) for x in RESPONSE_MODES.get(response_mode, RESPONSE_MODES['atende'])[1]],
        'placement': placement,
        'groups': groups, 'item_count': sum(len(g['items']) for g in groups),
    }
    registry[kind] = cfg
    _save_registry(storage, registry)
    register(kind, cfg)
    return kind, cfg


def delete_type(storage: Path, kind: str) -> None:
    registry = load_registry(storage)
    cfg = registry.pop(kind, None)
    _save_registry(storage, registry)
    unregister(kind)
    if cfg:
        try: (storage / 'custom_docs' / cfg.get('source_file', '')).unlink()
        except OSError: pass


def update_type(storage: Path, kind: str, title: str, placement: str, response_mode: str, used: int) -> dict:
    registry = load_registry(storage)
    cfg = registry.get(kind)
    if not cfg:
        raise ValueError('Tipo de documento não encontrado.')
    title = title.strip()
    if not title:
        raise ValueError('Informe um nome para o documento.')
    if placement not in PLACEMENTS:
        raise ValueError('Posição inválida.')
    if response_mode not in modes_for(placement):
        raise ValueError('Esse tipo de resposta não está disponível para a posição escolhida.')
    family = 'sim_nao' if response_mode.startswith('sim_nao') else 'atende'
    if used and family != cfg.get('response_mode'):
        raise ValueError('Já existem documentos emitidos: só dá para trocar entre tipos de resposta da mesma família (Atende/… ou Sim/Não).')
    cfg.update(title=title, short=title, placement=placement, response_mode=family,
               response_options=[list(x) for x in RESPONSE_MODES[response_mode][1]])
    registry[kind] = cfg
    _save_registry(storage, registry)
    register(kind, cfg)
    return cfg
