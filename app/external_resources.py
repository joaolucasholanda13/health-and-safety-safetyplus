"""Recursos externos de emergência por unidade (hospitais, bombeiros, órgãos públicos).

Cada recurso: (nome, contato, endereço). Contato/endereço podem ficar vazios.
Fonte: planilhas de recursos externos de cada unidade.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

_PUB = [
    ('Corpo de Bombeiros', '193', ''),
    ('SAMU', '192', ''),
    ('Polícia Militar', '190', ''),
    ('Polícia Rodoviária', '191', ''),
    ('Defesa Civil', '199', ''),
]

DEFAULT_UNITS = [
    {
        'key': 'assurua', 'name': 'Assuruá', 'cluster': 'BAHIA', 'clusters': ['BAHIA - ASSURUÁ'], 'state': 'BA',
        'resources': [
            ('COS – Centro de Operação Sistema Iqony', '(21) 96743-4576 / (21) 99971-6398', ''),
            ('Hospital Julieta Viana', '(74) 3661-1433', 'Rua Erotides Nogueira, nº 703, Centro, Xique Xique, BA'),
            ('Hospital Getúlio Reginaldo Cunha', '(74) 3637-2024', 'Rua Antônio Mariano Barreto, 64, Centro, Gentio do Ouro, BA'),
            ('Polícia Militar', '190', ''),
            ('Polícia Rodoviária', '191', ''),
            ('Defesa Civil', '199', ''),
            ('SEMA – Secretaria do Estado do Meio Ambiente e Recursos Naturais', '(71) 3115-3870', ''),
            ('Secretaria Municipal de Meio Ambiente e Recursos Hídricos', '(74) 3637-2127', ''),
            ('Companhia de Água e Esgoto da Bahia – EMBASA', '0800 0555 195', ''),
            ('Secretaria de Saúde de Gentio do Ouro', '(74) 3637-2087', ''),
            ('Prefeitura Municipal de Gentio do Ouro', '(74) 3637-2127', ''),
        ],
    },
    {
        'key': 'ventos-da-bahia', 'name': 'Ventos da Bahia', 'cluster': 'BAHIA', 'clusters': ['BAHIA - VENTOS DA BAHIA'], 'state': 'BA',
        'resources': [
            ('Maternidade Municipal Deputado José Carlos Araújo', '(75) 3343-2137', 'Pça. Sirlene Baraúna, Bonito/BA – CEP 46820-000 | Distância: VDB I 24 km · VDB II 31 km · VDB III 39 km'),
            ('Corpo de Bombeiros Morro do Chapéu', '(75) 3251-2462 / 193', 'Av. Joel Modesto, s/n – Morro do Chapéu/BA | Distância: VDB I 80 km · VDB II 87 km · VDB III 105 km'),
            ('Delegacia de Polícia Civil de Bonito', '(75) 3343-2164 / 197', 'Pça. Benedito Mina – Centro – Bonito/BA | Distância: VDB I 24 km · VDB II 31 km · VDB III 39 km'),
            ('SAMU', '192', 'Travessa ACM, s/n – Centro – Mulungu do Morro/BA | Distância: VDB I 27 km · VDB II 24 km · VDB III 28 km'),
            ('Hospital Municipal de Utinga – Tratamento para Animais Peçonhentos', '(75) 3337-1745', 'Rodovia BA Utinga-Wagner, 01 – Centro – Utinga/BA | Distância: VDB I 50 km · VDB II 57 km · VDB III 65 km'),
            ('Hospital Regional de Irecê', '(74) 3688-7700', 'Pça. Teodoro Sampaio – Irecê/BA – CEP 44900-000 | Distância: VDB I 112 km · VDB II 110 km · VDB III 112 km'),
            ('Hospital São Matheus', '(75) 3616-8858', 'Av. Getúlio Vargas, 1029 – Feira de Santana/BA – CEP 44020-260 | Distância: VDB I 336 km · VDB II 343 km · VDB III 374 km'),
            ('INEMA', '(71) 3118-4267', 'Av. Luís Viana Filho, 600 – CAB – Salvador/BA | Distância: VDB I 451 km · VDB II 458 km · VDB III 499 km'),
            ('Hospital Maternidade São Vicente de Paulo', '(74) 3653-2110', 'Rua Dois de Julho, 192 – Morro do Chapéu/BA – CEP 44850-000 | Distância: VDB I 80 km · VDB II 87 km · VDB III 105 km'),
            ('Hospital Municipal Jonival Lucas', '(75) 3339-2106', 'Pça. Luiz Eduardo Magalhães, s/n – Centro – Souto Soares/BA | Distância: VDB I 31 km · VDB II 29 km · VDB III 20 km'),
            ('Hospital Municipal do Povo', '(74) 3643-1002', 'Travessa ACM, s/n – Centro – Mulungu do Morro/BA | Distância: VDB I 27 km · VDB II 24 km · VDB III 28 km'),
            ('11º Batalhão de Bombeiros Militar', '(75) 3251-2070', 'Rua Otávio Mangabeira, s/n – Centro – Itaberaba/BA | Distância: VDB I 176 km · VDB II 183 km · VDB III 184 km'),
        ],
    },
    {
        'key': 'chui', 'name': 'Chuí', 'cluster': 'CHUI', 'clusters': ['CHUI - CHUI','CHUI - HERMENEGILDO','CHUI - GERIBATU','CHUI - SANTA VITORIA DO PALMAR','CHUI - GARGAU','CHUI - SERRA DAS AGULHAS','CHUI - INDAIAS','CHUI - GD SUDESTE','CHUI - GD NORDESTE'], 'state': 'RS',
        'resources': [
            ('Santa Casa de Misericórdia', '(53) 3263-1225 / (53) 98405-7405', 'Rua Dr. Alípio São Corrêa, 55 - Centro, Santa Vitória do Palmar-RS'),
            ('Associação de Caridade Santa Casa do Rio Grande', '(53) 3036-8800', 'Rua General Osório, 625 – Rio Grande-RS'),
            ('Santa Casa de Misericórdia de Pelotas', '(53) 3284-4700', 'Praça Piratinino de Almeida, 53 - Centro, Pelotas-RS'),
        ] + _PUB[:2] + [_PUB[2], _PUB[3], _PUB[4]],
    },
    {
        'key': 'delta-maranhao', 'name': 'Delta Maranhão', 'cluster': 'DELTAS', 'clusters': ['DELTAS - DELTA MARANHÃO'], 'state': 'MA',
        'resources': [
            ('Hospital Regional de Paulino Neves', '(98) 3487-1298 / 1067', 'MA-315, Paulino Neves - MA, 65585-000'),
            ('Hospital Regional de Barreirinhas', '(98) 99145-4537 / (98) 99249-7889', 'Av. Rodoviária, Barreirinhas - MA, 65590-000'),
            ('Hospital São Luiz', '(66) 99935-8719', 'Av. dos Sambaquis - Calhau, São Luís - MA, 65071-390'),
            ('Hospital da Ilha', '', "Av. São Luís Rei de França, 10913 - Olho D'água, São Luís - MA, 65066-620"),
            ('Corpo de Bombeiros', '193', ''),
            ('Polícia Militar', '190', ''),
            ('SAMU', '192', ''),
            ('Polícia Rodoviária', '191', ''),
            ('Defesa Civil', '199', ''),
            ('SEMA – Secretaria do Estado do Meio Ambiente e Recursos Naturais', '(98) 3194-8900', ''),
            ('Secretaria Municipal de Meio Ambiente', '', ''),
            ('Companhia de Água e Esgoto do Maranhão – CAEMA', '(98) 3219-5000', ''),
            ('Secretaria de Saúde de Paulino Neves', '(98) 98813-6369', ''),
            ('Prefeitura Municipal de Paulino Neves', '(98) 3487-1245', ''),
        ],
    },
    {
        'key': 'delta-piaui', 'name': 'Delta Piauí', 'cluster': 'DELTAS', 'clusters': ['DELTAS - DELTA PIAUI'], 'state': 'PI',
        'resources': [
            ('Hospital e Maternidade Marques Basto', '(86) 3315-7000 / (86) 3315-7001', 'R. Riachuelo, 932 - Centro, Parnaíba - PI, 64200-280'),
            ('Hospital Estadual Dirceu Arcoverde', '(86) 3323-7188', 'R. Rodrigues Coimbra, 1650 - Dirceu Arcoverde, Parnaíba - PI, 64210-230'),
            ('Dolce Vita – Hospital Nossa Senhora de Fátima', '(86) 3322-3796', 'R. Teresina, 796, Parnaíba - PI, 64218-680'),
            ('Hospital de Urgência de Teresina Prof. Zenon Rocha', '(86) 3218-5199', 'Rua Dr. Otto Tito, 1820, Redenção, Teresina-PI'),
            ('SAMU', '192', ''),
            ('Polícia Militar', '190', ''),
            ('Polícia Rodoviária', '191', ''),
            ('Defesa Civil', '199', ''),
            ('Corpo de Bombeiros', '193', ''),
        ],
    },
]




FILE_NAME = 'external_resources.json'


def _norm_unit(u: dict) -> dict:
    return {
        'key': str(u.get('key') or ''),
        'name': str(u.get('name') or '').strip(),
        'state': str(u.get('state') or '').strip().upper()[:2],
        'clusters': [str(c) for c in (u.get('clusters') or [])],
        'resources': [[str(r[0]).strip(), str(r[1] if len(r) > 1 else '').strip(), str(r[2] if len(r) > 2 else '').strip()]
                      for r in (u.get('resources') or []) if r and str(r[0]).strip()],
    }


def load_units(storage_dir) -> list[dict]:
    """Unidades editadas pelo DEV (arquivo no storage); se não houver, usa o padrão."""
    path = Path(storage_dir) / FILE_NAME
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return [_norm_unit(u) for u in data if u.get('key')]
    except Exception:
        pass
    return [_norm_unit(u) for u in DEFAULT_UNITS]


def save_units(storage_dir, units: list[dict]) -> None:
    path = Path(storage_dir) / FILE_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps([_norm_unit(u) for u in units], ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)


def slugify(text: str) -> str:
    t = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-') or 'unidade'


def unit_for_cluster(storage_dir, cluster: str):
    c = (cluster or '').strip().upper()
    if not c:
        return None
    for u in load_units(storage_dir):
        if any(c == x.strip().upper() for x in u['clusters']):
            return u
    return None


def resources_json_map(storage_dir, clusters) -> dict:
    """{cluster: {name,state,resources}} para o formulário da APR."""
    units = load_units(storage_dir)
    out = {}
    for c in clusters:
        cu = (c or '').strip().upper()
        for u in units:
            if any(cu == x.strip().upper() for x in u['clusters']):
                out[c] = {'name': u['name'], 'state': u['state'], 'resources': u['resources']}
                break
    return out
