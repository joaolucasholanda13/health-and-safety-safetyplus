"""Configuração de módulos do Safety Plus.

Este arquivo não veio no pacote original enviado (só o backend Python
estava presente, sem `app/module_configs.py`, `app/static` e
`app/templates`). Foi reconstruído a partir de:

  1. Dados REAIS já documentados nos READMEs do próprio projeto:
     clusters, sites, os 7 tipos de PT e seus `kind` (README_V2_CLUSTER_
     SITE_VINCULADO_9_DOCUMENTOS.md, README_V2_CLIMBER_PARQUE_UNIDADE_
     CLUSTERS.md, README_V2_TALHA_CLUSTER_SITE_11_CLUSTERS.md e a lista
     `APR_CRITICAL_PERMIT_KIND` já existente em `main.py`).
  2. Leitura do código de `main.py` para inferir exatamente quais chaves
     cada `cfg` (item de `MODULES`/`INSPECTION_MODULES`) precisa ter e
     como cada uma é consumida (`get_document`, `parse_permit`,
     `parse_inspection`, `inspection_defaults`, etc.).
  3. Onde o conteúdo é de segurança do trabalho (itens de checklist,
     perigos, riscos, EPIs) e não havia fonte real disponível, usei
     conteúdo de referência baseado em normas regulamentadoras (NR-35
     trabalho em altura, NR-33 espaço confinado, NR-10 eletricidade,
     NR-12 içamento, NR-18/NR-11 veículos e talhas). Esses itens estão
     marcados como PLACEHOLDER abaixo e devem ser revisados e ajustados
     pelo time de SESMT da Serena antes de qualquer uso em campo real —
     são documentos de segurança do trabalho, não apenas texto de UI.
"""

# =====================================================================
# Clusters / sites (dado real — extraído dos READMEs do projeto)
# =====================================================================

# Lista "achatada" usada pela APR e pelos módulos de inspeção que ainda
# não migraram para cluster/site separados (climber, hoist, light_vehicle).
CLUSTERS = [
    'CHUI - CHUI',
    'CHUI - HERMENEGILDO',
    'CHUI - GERIBATU',
    'CHUI - SANTA VITORIA DO PALMAR',
    'CHUI - GARGAU',
    'CHUI - SERRA DAS AGULHAS',
    'CHUI - INDAIAS',
    'CHUI - GD SUDESTE',
    'CHUI - GD NORDESTE',
    'BAHIA - ASSURUÁ',
    'BAHIA - VENTOS DA BAHIA',
    'DELTAS - DELTA PIAUI',
    'DELTAS - DELTA MARANHÃO',
    'TEXAS - GOODNIGHT 1',
    'TEXAS - GOODNIGHT 2',
]

# Estrutura agrupada (cluster -> sites) usada pelas PTs e inspeções que
# têm os campos Cluster e Site separados (README_V2_CLUSTER_SITE_
# VINCULADO_9_DOCUMENTOS.md).
SEPARATE_CLUSTER_SITES = {
    'CHUI': [
        'CHUI', 'HERMENEGILDO', 'GERIBATU', 'SANTA VITORIA DO PALMAR',
        'GARGAU', 'SERRA DAS AGULHAS', 'INDAIAS', 'GD SUDESTE', 'GD NORDESTE',
    ],
    'BAHIA': ['ASSURUÁ', 'VENTOS DA BAHIA'],
    'DELTAS': ['DELTA PIAUI', 'DELTA MARANHÃO'],
    'TEXAS': ['GOODNIGHT 1', 'GOODNIGHT 2'],
}
SEPARATE_CLUSTERS = list(SEPARATE_CLUSTER_SITES.keys())


# =====================================================================
# Documentos: títulos e prefixos de código
# =====================================================================

DOCUMENT_TITLES = {
    'apr': 'Análise Preliminar de Risco',
    'vehicle': 'Inspeção de Veículo Pesado',
    'pt_height': 'PT — Trabalho em Altura',
    'confined': 'PT — Espaço Confinado',
    'electrical': 'PT — Intervenção Elétrica',
    'line_live': 'PT — Linha Viva',
    'vegetation': 'PT — Supressão de Vegetação',
    'lifting': 'PT — Içamento de Carga',
    'tme': 'PT — TME',
    'light_vehicle': 'Inspeção de Veículo Leve',
    'hoist': 'Inspeção de Talha Guincho',
    'height_kit': 'Inspeção diária antes da subida — Kit de Trabalho em Altura',
    'climber_assist': 'Inspeção Climber Assist',
    'safety_belt': 'Inspeção estrutural — Cinto de Segurança',
    'spiq': 'Equipamentos SPIQ',
    'loto': 'Formulário Padrão de LOTO',
    'grinder': 'Lista de Verificação — Esmerilhadeira',
    'drill': 'Lista de Verificação — Furadeira',
    'rotary_hammer': 'Lista de Verificação — Martelete',
    'circular_saw': 'Lista de Verificação — Serra Circular',
    'marble_saw': 'Lista de Verificação — Serra Mármore',
    'welding_machine': 'Lista de Verificação — Máquina de Solda',
    'lifting_accessories': 'Lista de Verificação — Acessórios de Içamento de Carga',
    'safety_moment': 'Momento de Segurança',
}

PREFIXES = {
    'apr': 'APR',
    'vehicle': 'VP',
    'pt_height': 'PTA',
    'confined': 'PTEC',
    'electrical': 'PTIE',
    'line_live': 'PTLV',
    'vegetation': 'PTSV',
    'lifting': 'PTIC',
    'tme': 'PTTME',
    'light_vehicle': 'VL',
    'hoist': 'TG',
    'height_kit': 'KTA',
    'climber_assist': 'CLA',
    'safety_belt': 'CCS',
    'spiq': 'LV11',
    'loto': 'LOTO',
    'grinder': 'LVES',
    'drill': 'LVFU',
    'rotary_hammer': 'LVMA',
    'circular_saw': 'LVSC',
    'marble_saw': 'LVSM',
    'welding_machine': 'LVMS',
    'lifting_accessories': 'LVAI',
    'safety_moment': 'MS',
}


# =====================================================================
# APR — checklist geral, perigos e riscos
# (PLACEHOLDER de conteúdo de segurança — validar com SESMT)
# =====================================================================

CHECKLIST = [
    'A equipe recebeu o Diálogo Diário de Segurança (DDS) antes do início da atividade?',
    'Todos os envolvidos possuem treinamento e ASO compatíveis com a atividade?',
    'Os EPIs necessários foram inspecionados e estão em condições de uso?',
    'A área de trabalho foi isolada e sinalizada adequadamente?',
    'As condições climáticas permitem a execução segura da atividade?',
    'Os equipamentos e ferramentas foram inspecionados antes do uso?',
    'Existe plano de resposta a emergência conhecido pela equipe?',
    'Os meios de comunicação (rádio/celular) estão testados e funcionando?',
    'A rota de acesso e fuga foi avaliada e está livre de obstáculos?',
    'Todos os riscos identificados possuem medida de controle definida?',
    'Existe procedimento operacional específico para a atividade e ele foi lido pela equipe?',
    'A equipe está ciente dos riscos e das medidas de controle desta APR?',
    'Foi verificada a necessidade de permissões de trabalho específicas (PT)?',
    'Ferramentas manuais e elétricas estão em bom estado de conservação?',
    'Há sinalização de área de risco visível para terceiros não envolvidos?',
    'Foi verificada a proximidade de redes elétricas, tubulações ou outras interferências?',
    'Extintor de incêndio ou outro recurso de combate a princípio de incêndio está disponível?',
    'Kit de primeiros socorros está disponível e acessível no local?',
    'A equipe sabe quem é o responsável/líder da atividade?',
    'Foi conferida a validade de treinamentos específicos (NR-35, NR-33, NR-10 etc.)?',
    'Veículos e equipamentos móveis envolvidos foram inspecionados?',
    'Existe iluminação adequada para a execução segura da atividade?',
    'A equipe foi orientada sobre uso correto dos EPIs específicos da atividade?',
    'Não há indícios de fadiga, uso de álcool/drogas ou condição inadequada da equipe?',
]

HAZARD_OPTIONS = [
    'Acessórios de içamento (Cabos, cintas) defeituosos',
    'Arcos elétricos em painéis/subestações',
    'Área com desnível',
    'Armazenamento de inflamáveis',
    'Atmosfera deficiente de Oxigênio (<19,5%)',
    'Atmosfera enriquecida com Oxigênio (>23%)',
    'Cabos elétricos expostos',
    'Capacitores e bancos de baterias',
    'Carga mal acondicionada',
    'Carga suspensa',
    'Chamas abertas',
    'Condições climáticas adversas',
    'Condições da via',
    'Condução de veículos em vias públicas',
    'Condução inadequada',
    'Condutores energizados (Alta/Baixa Tensão)',
    'Desnível de altura (Escadas, andaimes, torres)',
    'Diferença de potencial no solo',
    'Equipamento sem proteção',
    'Escalada em Torres Anemométricas',
    'Escavações, valas e taludes',
    'Estabilizadores inadequados',
    'Estrutura de andaime',
    'Estruturas de torres de transmissão',
    'Exposição a agentes biológicos',
    'Exposição a fatores ergonômicos inadequados',
    'Falha hidráulica',
    'Ferramentas inadequadas',
    'Ferramentas manuais',
    'Ferramentas manuais perfurocortantes',
    'Ferramentas rotativas',
    'Fluxo de água (Condutos e vertedouros)',
    'Fontes de ignição',
    'Gases e fumos',
    'Gases tóxicos acumulados (H2S, CO)',
    'Geometria interna estreita/confinada',
    'Iluminação inadequada',
    'Indução elétrica',
    'Indução eletromagnética (Linhas paralelas)',
    'Linha viva',
    'Local Desorganizado',
    'Local Energizado',
    'Manobra em área restrita',
    'Manuseio inadequado',
    'Máquinas e ferramentas rotativas',
    'Máquinas em operação',
    'Materiais empilhados',
    'Materiais suspensos',
    'Meio aquático',
    'Movimentação de carga',
    'Movimento de lança',
    'Movimento repetitivo',
    'Óleo isolante ou fluidos hidráulicos',
    'Partes energizadas expostas',
    'Partes móveis/rotativas sem proteção',
    'Poeira em suspensão',
    'Ponto cego',
    'Pontos de convergência (Prensas, cilindros)',
    'Presença de animais peçonhentos',
    'Pressão hidrostática',
    'Produtos inflamáveis / Gases',
    'Produtos químicos',
    'Pulverização manual',
    'Recipientes inadequado',
    'Ruído',
    'Solo inadequado',
    'Solo instável',
    'Subestação energizada',
    'Superfície instável',
    'Superfícies aquecidas',
    'Supressão Vegetal',
    'Terreno de patolagem instável',
    'Terreno irregular',
    'Trabalho com cordas',
    'Trabalho em Altura',
    'Trabalho em telhados ou superfícies frágeis',
    'Trabalhos sobrepostos',
    'Trânsito de veículos',
    'Uso de arma de fogo',
    'Vapor de solventes, tintas ou resinas',
    'Vibração de mãos, braços ou corpo inteiro',
]

RISK_OPTIONS = [
    'C',
    'B',
    'A',
]

# Catálogo de riscos (consequência/evento) — usado no dropdown "Risco" de
# cada etapa da APR. Diferente de RISK_OPTIONS acima, que é a escala de
# severidade (C/B/A — A é a mais alta).
RISK_CATALOG = [
    'Afogamento / submersão',
    'Amputação',
    'Aprisionamento / entalamento',
    'Arco elétrico / flash elétrico',
    'Asfixia / deficiência de oxigênio',
    'Atropelamento',
    'Choque elétrico / eletrocussão',
    'Colapso de andaime, estrutura ou ponto de ancoragem',
    'Colisão entre veículos, máquinas ou estruturas',
    'Contaminação do solo, água ou ar',
    'Contato / contaminação com produto químico',
    'Corte / laceração',
    'Danos a equipamentos / patrimônio',
    'Dermatite / irritação da pele',
    'Derrapagem / perda de controle do veículo',
    'Desmaio / mal súbito',
    'Distúrbio osteomuscular por movimento repetitivo',
    'Enroscamento / arraste por partes móveis',
    'Escorregamento de solo, talude ou material',
    'Esmagamento / prensamento',
    'Estresse térmico / insolação / desidratação',
    'Explosão',
    'Exposição a agente biológico / contaminação biológica',
    'Exposição a intempéries / descarga atmosférica',
    'Falha de comunicação / resposta inadequada à emergência',
    'Falha de sustentação / perda de estabilidade',
    'Ferimento por arma de fogo',
    'Impacto contra objeto ou estrutura',
    'Impacto por objeto em movimento',
    'Inalação de poeira, fumos, gases ou vapores',
    'Incêndio',
    'Intoxicação por gases ou produtos químicos',
    'Irritação ocular ou respiratória',
    'Lesão musculoesquelética / esforço excessivo',
    'Lesão por vibração',
    'Liberação inesperada de energia / pressão',
    'Movimento inesperado de máquina, equipamento ou carga',
    'Outro',
    'Perda auditiva / dano por ruído',
    'Perfuração / punctura',
    'Picada / mordida de animal peçonhento',
    'Projeção de partículas / fragmentos',
    'Queda de carga suspensa',
    'Queda de mesmo nível (tropeço, escorregão)',
    'Queda de nível diferente / queda de altura',
    'Queda de objetos, ferramentas ou materiais',
    'Queimadura elétrica',
    'Queimadura química',
    'Queimadura térmica',
    'Ruptura de cabo, cinta, corrente ou acessório de içamento',
    'Ruptura ou vazamento de sistema hidráulico',
    'Soterramento / desmoronamento',
    'Tombamento / capotamento de veículo ou equipamento',
    'Vazamento / derramamento de óleo, combustível ou produto químico',
]


# =====================================================================
# PTs (Permissões de Trabalho) — MODULES[kind]
# =====================================================================
# Cada módulo define:
#   checklist       -> perguntas de sim/não específicas da atividade
#   equipment_mode  -> None | 'multi' (checkbox) | 'text' (campo livre)
#   equipment_options -> lista de opções quando equipment_mode == 'multi'

MODULES = {
    'pt_height': {
        'checklist': [
            'A área de trabalho está sinalizada, isolada e bloqueada?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'A velocidade do vento está de acordo com a recomendação da RAC, ou dos preceitos da NR-35?',
            'A seleção, inspeção, forma de utilização e limitação de uso dos sistemas de proteção coletiva e individual estão atendendo às normas técnicas vigentes, às orientações do fabricante ou projetista e aos princípios da redução do impacto e dos fatores de queda?',
            'Foi avaliado se há trabalhos simultâneos que apresentem riscos específicos e se eles estão controlados?',
            'Os meios de comunicação para atividade estão definidos e disponíveis?',
            'Existe um planejamento para emergências no procedimento ou APR que inclua as emergências, o planejamento do resgate e primeiros socorros, de forma a reduzir o tempo da suspensão inerte do trabalhador, e todos os equipamentos necessários?',
            'Foi realizada a inspeção visual dos sistemas de proteção individual contra quedas?',
            'A inspeção formal dos sistemas de proteção coletiva contra quedas incluindo a PEMT foi executada?',
            'A certificação anual dos sistemas de proteção coletiva contra quedas (escada, linha de vida, ponto de ancoragem, elevador etc.) está vigente?',
            'Os trabalhadores realizaram inspeção rotineira nos seus EPIs e estão em boas condições?',
            'O dispositivo de retenção de queda para ferramentas está disponível?',
            'Foi realizada a aferição da pressão arterial de todos os executores do trabalho em altura?',
            'Todos os executores do trabalho em altura estão devidamente capacitados e habilitados conforme NR-35?',
            'A análise de riscos está detalhada o suficiente e adequada à realidade da atividade?',
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'Depois de toda avaliação, não foi identificada condição impeditiva para realizar o trabalho em altura?',
        ],
        'equipment_mode': None,
    },
    'confined': {
        'checklist': [
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'O procedimento de resgate é de conhecimento de todos os envolvidos?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'A velocidade do vento está de acordo com a recomendação da RAC, ou dos preceitos legais?',
            'A área de trabalho está sinalizada, isolada e bloqueada?',
            'Os meios de comunicação para atividade estão definidos e disponíveis?',
            'O vigia da atividade está na entrada do espaço confinado, em contato permanente com os autorizados?',
            'O teste inicial da atmosfera está registrado na PET?',
            'O nível de oxigênio está dentro da faixa aceitável da NR-33 (19,5% a 23,0%), com a causa de eventual redução/enriquecimento conhecida e controlada?',
            'Dispõe-se de equipamento de resgate/evacuação?',
            'Bloqueios, travamentos e etiquetagens estão dispostos?',
            'O equipamento de ventilação/exaustão está sendo utilizado?',
            'O monitor de gases está disponível no local de trabalho?',
            'Quando aplicável, o equipamento de proteção respiratória/autônomo ou sistema de ar mandado necessário está disponível, adequado e pronto para uso?',
            'O ambiente está isento de atmosfera Imediatamente Perigosa à Vida ou à Saúde?',
        ],
        'equipment_mode': None,
    },
    'electrical': {
        'checklist': [
            'A área de trabalho está sinalizada, delimitada e bloqueada para acesso de terceiros?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'A análise de riscos está detalhada o suficiente e adequada à realidade da atividade?',
            'A instalação possui sinalização de advertência de risco de choque elétrico?',
            'A instalação está fisicamente protegida para evitar o acesso de pessoas não autorizadas?',
            'É vedado o uso de adornos pessoais no trabalho com intervenção elétrica, ou em suas proximidades?',
            'Os EPIs estabelecidos na APR estão disponíveis?',
            'Os EPIs são adequados para a utilização pretendida? (vestimenta e calçado de segurança condutivo)',
            'Os EPIs e EPCs com materiais isolantes, destinados ao trabalho em alta tensão, foram submetidos a testes elétricos?',
            'Os trabalhadores realizaram inspeção visual/rotineira em seus EPIs, os quais estão em boas condições?',
            'O líder da atividade está presente no local de execução?',
            'As ferramentas foram inspecionadas e estão em ótimas condições de uso?',
            'A sequência para desenergizar a instalação elétrica foi executada corretamente? 1) Seccionamento 2) Impedimento de reenergização 3) Constatação da ausência de tensão 4) Instalação de aterramento temporário 5) Proteção dos elementos energizados na zona controlada 6) Instalação da sinalização de impedimento de reenergização.',
            'O kit de resgate (eletricidade) e o de primeiros socorros está disponível na frente de serviço?',
            'Os trabalhadores não envolvidos no processo de reenergização foram retirados da zona controlada?',
        ],
        'equipment_mode': None,
        # PDF-base ainda não está neste pacote — finalizar essa PT vai mostrar
        # "PDF não gerado" até o arquivo real ser adicionado em app/pdf_templates/.
        'template': 'PT Intervencao Eletrica - Modelo.pdf',
    },
    'line_live': {
        'checklist': [
            'A área de trabalho está sinalizada, isolada e bloqueada?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'A análise de riscos está detalhada o suficiente e adequada à realidade da atividade?',
            'A instalação possui sinalização de advertência de risco de choque elétrico?',
            'A instalação está fisicamente protegida para evitar o acesso de pessoas não autorizadas?',
            'É vedado o uso de adornos pessoais no trabalho com intervenção elétrica, ou em suas proximidades?',
            'Os EPIs estabelecidos na APR estão disponíveis?',
            'Os EPIs são adequados para a utilização pretendida? (vestimenta e calçado de segurança condutivo)',
            'Os trabalhadores realizaram inspeção visual/rotineira em seus EPIs, os quais estão em boas condições?',
            'O líder da atividade está presente no local de execução?',
            'Há ambulância disponível para a atividade?',
            'As ferramentas foram inspecionadas e estão em ótimas condições de uso?',
            'O kit de resgate (altura/eletricidade) e o de primeiros socorros está disponível na frente de serviço?',
            'O andaime e/ou escada utilizado é isolante e está em boas condições?',
            'Há comunicação estabelecida entre o líder da atividade e o responsável pela liberação de OS?',
            'Depois de toda avaliação, não foi identificada condição impeditiva para realização da atividade?',
        ],
        'equipment_mode': None,
        'template': 'PT Linha Viva - Modelo.pdf',
    },
    'vegetation': {
        'checklist': [
            'A Supressão está planejada, organizada e será executada por pessoas/equipes capacitadas e autorizadas?',
            'ASV: Existe autorização formal para a supressão de vegetação?',
            'Existe licença para porte e uso de motosserra?',
            'A supervisão para acompanhar a atividade está definida?',
            'Os meios de comunicação para a atividade estão definidos e disponíveis?',
            'A área de trabalho está sinalizada e isolada?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'Foi realizado o checklist de inspeção e registro dos equipamentos (motosserra, roçadeira, motopoda, similares etc.)? Estão em boas condições?',
            'As ferramentas de corte são guardadas e transportadas em bainhas? As lâminas dos equipamentos estão em boas condições?',
            'Os dispositivos de segurança dos equipamentos de poda estão em perfeito funcionamento e foram inspecionados?',
            'A equipe responsável pela atividade dispõe de EPIs adequados conforme recomendados na APR? (capacete com viseira, óculos, protetor auricular, vestimenta para motosserrista, perneira e luvas)',
            'O operador de motosserra utiliza vestimenta específica contra o risco de corte desse equipamento?',
            'Os trabalhadores realizaram inspeção visual/rotineira nos seus EPIs, estão em boas condições?',
            'Foi avaliado se há trabalhos simultâneos que apresentem riscos específicos. Os controles foram estabelecidos?',
            'Há banheiros disponíveis próximos da área de trabalho?',
            'Há um abrigo provisório capaz de proteger os trabalhadores em caso de atividade em lugares ermos?',
            'Existe um planejamento para emergências no procedimento ou APR que inclua as emergências e o planejamento do resgate e primeiros socorros?',
            'O kit de primeiros socorros está disponível próximo aos locais de trabalho?',
            'A água potável é fornecida em recipientes portáteis herméticos?',
            'O risco de contato com rede e/ou circuito elétrico foi avaliado na APR e está controlado?',
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'Depois de toda avaliação, não foi identificada condição impeditiva para realização da atividade?',
        ],
        'equipment_mode': None,
        'template': 'PT Supressao de Vegetacao - Modelo.pdf',
    },
    'lifting': {
        'checklist': [
            'Içamento planejado, organizado e executado por pessoas/equipes capacitadas e autorizadas?',
            'Foi avaliada a necessidade de Plano de Rigging na análise de risco ou procedimento da tarefa?',
            'Se aplicável, o Plano de Rigging está disponível na frente de serviço?',
            'A velocidade do vento está sendo monitorada de acordo com a recomendação do Plano de Rigging ou RAC?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'A área de trabalho está sinalizada, isolada e bloqueada?',
            'Capacidade de carga do equipamento, na condição proposta para a atividade, é suficiente para o içamento?',
            'Equipamento de guindar está com plano de manutenção ou certificação em dia?',
            'Foi realizado o checklist de inspeção e registro do equipamento de guindar e seus dispositivos? Estão em boas condições?',
            'Os acessórios de içamento foram inspecionados? Estão em boas condições?',
            'Os acessórios de içamento contêm etiqueta indelével? Estão em boas condições?',
            'Zona de perigo está definida na análise de riscos ou no procedimento operacional atendendo minimamente o distanciamento maior que a altura da carga ou maior que o comprimento da carga, devendo ser atendido aquele que for maior; no caso de não atendimento, medidas de controles complementares devem estar descritas? (Em caso de Plano de Rigging, o mesmo deve ser atendido.)',
            'Cordas e dispositivos guias estão definidos na APR e disponíveis para auxiliar o manuseio da carga suspensa?',
            'Está claro na APR a proibição de permanecer embaixo ou próximo da carga suspensa e a condição é satisfatória?',
            'O equipamento está posicionado em terreno nivelado e sobre pranchas/dormentes?',
            'Os trabalhadores realizaram inspeção visual/rotineira nos seus EPIs e os mesmos estão em boas condições?',
            'Os meios de comunicação para atividade estão definidos e disponíveis?',
            'O risco de contato com rede e/ou circuito elétrico foi avaliado na análise de riscos e está controlado?',
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'Depois de toda avaliação, não foi identificada condição impeditiva para realização da atividade?',
        ],
        'equipment_mode': 'multi',
        'equipment_options': [
            'Guindaste',
            'Munck',
            'Talha elétrica',
            'Talha manual (catraca)',
            'Guincho',
            'Ponte rolante',
        ],
        'template': 'PT Icamento de Carga - Modelo.pdf',
    },
    'tme': {
        'checklist': [
            'A área de trabalho está sinalizada, isolada e bloqueada?',
            'As condições meteorológicas permitem a realização da atividade com segurança; condições impeditivas foram descritas na APR e estão claras?',
            'A velocidade do vento está de acordo com a recomendação da RAC, ou dos preceitos da NR-35?',
            'A equipe responsável pela execução da atividade dispõe de EPIs adequados?',
            'Os trabalhadores realizaram inspeção visual/rotineira nos seus EPIs e estão em boas condições?',
            'É proibido trabalhar sobreposto?',
            'Os meios de comunicação para a atividade estão definidos e disponíveis?',
            'Existe um planejamento para emergências no procedimento ou APR que inclua as emergências, o planejamento do resgate e primeiros socorros, de forma a reduzir o tempo da suspensão inerte do trabalhador, e todos os equipamentos necessários?',
            'A análise de riscos e o procedimento para emergências foram discutidos e divulgados aos trabalhadores?',
            'A análise de riscos está detalhada o suficiente e adequada à realidade da atividade?',
            'Foi realizada a aferição da pressão arterial de todos os executores do trabalho em altura?',
            'O kit de resgate está na base da TME?',
            'O dispositivo de retenção de queda para ferramentas está disponível?',
            'As ferramentas são transportadas em bolsas adequadas?',
            'A área de trabalho dispõe de abrigo e banheiro químico?',
            'A corda guia está disponível para auxiliar o manuseio da carga suspensa? As fibras estão em boas condições?',
            'Bases, estais, âncoras, esticadores, anilhas, clipes e alças foram inspecionados?',
            'A estrutura da TME está em boas condições?',
            'Depois de toda avaliação, não foi identificada condição impeditiva para realização da atividade?',
        ],
        'equipment_mode': None,
        'template': 'PT TME - Modelo.pdf',
    },
}

# Quantidade de linhas de trabalhador exibidas por tipo de PT (usada em
# `permit_worker_count` no main.py: 5 para estes quatro, 6 para as demais).
# Mantido aqui só como referência — o valor em si já está hardcoded no
# main.py e não precisa ser importado deste arquivo.
# {'pt_height','vegetation','lifting','tme'} -> 5 trabalhadores
# demais ('confined','electrical','line_live') -> 6 trabalhadores

PT_WORK_TYPES = [
    'Uso de escada',
    'Uso de andaime',
    'Cinto de segurança tipo paraquedista',
    'Linha de vida horizontal/vertical',
    'Plataforma elevatória (PTA)',
    'Acesso por corda (técnica de acesso)',
    'Trabalho em telhado/cobertura',
]

CONFINED_ENTRY_TYPES = [
    'Fundação - Turbina Eólica',
    'HUB - Turbina Eólica',
    'Pá - Turbina Eólica',
    'Caixa Separadora de Óleo',
    'Unidade Geradora - UG',
]

# Linhas da tabela de monitoramento atmosférico do espaço confinado
# (NR-33): (rótulo, faixa de referência, chave usada em air_readings).
# `main.py` lê 4 valores por linha (uma leitura a cada reentrada/intervalo).
CONFINED_AIR_ROWS = [
    ('Oxigênio (O2)', '19,5% a 23,0%', 'o2'),
    ('Gases inflamáveis (%LII)', 'abaixo de 10% do LII', 'lii'),
    ('Monóxido de carbono (CO)', 'limite definido no PGR/procedimento', 'co'),
    ('Gás sulfídrico (H2S)', 'limite definido no PGR/procedimento', 'h2s'),
]


# =====================================================================
# Inspeção de Veículo Pesado (kind='vehicle', módulo dedicado)
# =====================================================================

VEHICLE_CHECK_ITEMS = [
    'CRLV disponível e vigente.',
    'Habilitação compatível com a categoria e vigente.',
    'Existência e condições de uso da chave de roda, macaco e triângulo.',
    'Estado de conservação dos pneus e rodas, incluindo estepe.',
    'Buzina / Faróis / Faroletes / Lanternas / Retrovisores.',
    'Luzes de emergência (pisca alerta).',
    'Luz e alarme de ré operacionais.',
    'Para-brisa dianteiro e traseiro sem avarias.',
    'Limpador de para-brisa.',
    'Cinto de segurança para todos os passageiros.',
    'Existência de vazamentos (água e óleo).',
    'Freio pedal e de estacionamento em boas condições/eficientes.',
    'Placas de identificação dianteira e traseira.',
    'Tanque de combustível vedado e sem vazamentos.',
    'Acesso à carroceria adequado e em boas condições de uso.',
    'Calços de estacionamento disponíveis.',
]

# O modelo oficial Serena possui uma lacuna de numeração: após o item 9,
# o próximo item impresso é o 11. Mantemos essa numeração visual no sistema.
VEHICLE_ITEM_NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17]

VEHICLE_DAYS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']


# =====================================================================
# Inspeções adicionais — INSPECTION_MODULES[kind]
# =====================================================================
# Três dos quatro módulos abaixo (hoist, light_vehicle, height_kit) usam
# mode='daily': múltiplos "períodos" nomeados (como a inspeção de Veículo
# Pesado), cada um com sua data, respostas e rubrica — foi assim que o
# gerador de PDF (app/pdfgen.py, já existente no projeto) foi construído
# para eles, com uma grade de colunas por período. Só o Climber Assist usa
# mode='single' (uma inspeção, uma rubrica), porque seu gerador de PDF
# usa esse formato. A quantidade de itens abaixo bate exatamente com o
# número de linhas que o pdfgen.py espera para cada um — se mudar a
# quantidade aqui, o desenho no PDF sai desalinhado assim que o
# arquivo-modelo oficial for adicionado.

# =====================================================================
# MODELO PADRÃO DE CHECKLIST (Serena)
# =====================================================================
# Todo checklist novo deve usar estas funções: cabeçalho, dias da semana,
# C/NC/NA, rubrica e PDF no layout padrão vêm prontos. Para criar um novo,
# basta informar o título e a lista de itens (use '*' no fim = impeditivo).
# Itens comuns reaproveitáveis: STD_EPI e STD_APR.

STD_EPI = "EPI's para operação (Capacete, óculos, luvas, protetor auricular, botina de segurança).*"
STD_APR = 'A APR está disponível? Todos estão cientes?*'
STD_WEEK = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']


def standard_daily_checklist(short: str, model_label: str, items: list, *, fields=None) -> dict:
    """Checklist diário (segunda a domingo) no modelo padrão Serena."""
    return {
        'short': short,
        'mode': 'daily',
        'layout': 'standard',
        'month_year': True,
        'periods': list(STD_WEEK),
        'fields': fields or [
            ('cluster', 'Cluster'),
            ('local', 'Local'),
            ('model', model_label),
            ('leader', 'Líder'),
        ],
        'items': [(t,) for t in items],
    }


def standard_single_checklist(short: str, items: list, *, fields, note: str = '') -> dict:
    """Checklist de inspeção única (uma data, uma rubrica) no modelo padrão.
    `items` = lista de (texto, 'seção.número')."""
    return {
        'short': short,
        'mode': 'single',
        'grouped': True, 'layout': 'standard',
        'month_year': False,
        'fields': list(fields),
        'items': [tuple(i) for i in items],
        'note': note,
    }



SPIQ_NOTE = ('Notas: 1) Se a inspeção identificar uma condição defeituosa, retire o equipamento de operação imediatamente e acondicione numa área isolada; 2) Este documento deve ser arquivado pelo responsável da inspeção; 3) Realize a inspeção de acordo com as recomendações do manual do fabricante; 4) Item 35.6.6.1 Inspeção Inicial: realizada entre o recebimento e a primeira utilização do componente do SPIQ, com o objetivo de assegurar que este seja apropriado para a aplicação pretendida, que funciona corretamente, que atende aos requisitos normativos e que esteja em boas condições. Item 35.6.6.3 Inspeção Periódica: realizada periodicamente e caracterizada por um controle do equipamento, componente ou sistema a fim de detectar seus defeitos, danos ou desgastes, respeitando as instruções do projetista ou fabricante, com periodicidade não superior a 12 meses; 5) Legenda: A - aprovado; AR - aprovado com restrição; R - reprovado.')
_ETIQ = ('ETIQUETA', ['Certifique-se de que todas as etiquetas estejam presentes e indeléveis.'])
SPIQ_SECTIONS = [('CINTURÃO DE SEGURANÇA — TECIDO (costuras e fitas)', ['O material não deve apresentar fibras puídas, cortadas ou rompidas.', 'Verifique se há rasgos, abrasões, bolor, queimaduras ou descoloração.', 'Inspecione a costura, verifique se há pontos partidos ou soltos.', 'Analise se o indicador de impacto costurado foi ativado.', 'Fita para trauma de suspensão deve estar em boas condições.']),
    ('CINTURÃO DE SEGURANÇA — FERRAGENS (fivelas, argolas em D, almofadas, prendedores de laço, ajustes do torso verticais)', ['Esses itens não podem estar danificados, quebrados, distorcidos.', 'Devem estar isentos de bordas afiadas, rebarbas, rachaduras, partes gastas ou corrosão.', 'Para garantir a não-condutividade, as ferragens revestidas com PVC não podem ter cortes, rasgos, rachaduras, orifícios.', 'Certifique-se de que as abas de liberação das fivelas funcionam livremente.', 'Os botões de catraca devem virar facilmente no sentido horário, e não devem girar no sentido anti-horário quando o botão é puxado para fora.']),
    ('CINTURÃO DE SEGURANÇA — ETIQUETA', ['Certifique-se de que todas as etiquetas estejam presentes e indeléveis.']),
    ('TALABARTE DE POSICIONAMENTO — CORDA', ['A corda não deve apresentar cortes, fios rompidos, abrasões, bolor, queimaduras e descoloramento.', 'Verifique se há a costura está isenta de sujidades excessivas, manchas de ferrugem e tinta.', 'A proteção da corda deve estar íntegra de danos.']),
    ('TALABARTE DE POSICIONAMENTO — FERRAGEM (mosquetão automático, regulador de corda)', ['Esses itens não podem estar danificados, quebrados, distorcidos.', 'Devem estar isentos de bordas afiadas, rebarbas, rachaduras, partes gastas ou corrosão.', 'Teste o funcionamento do mosquetão automático e do regulador de corda.']),
    ('TALABARTE DE POSICIONAMENTO — ETIQUETA', ['Certifique-se de que todas as etiquetas estejam presentes e indeléveis.']),
    ('TALABARTE Y — TECIDO', ['O material não deve apresentar fibras puídas, cortadas ou rompidas.', 'Verifique se há rasgos, abrasões, bolor, queimaduras ou descoloração.', 'Inspecione a costura, verifique se há pontos partidos ou soltos.', 'O absorvedor de energia deve estar íntegro.', 'O indicador de impacto deve estar isento de fios descosturados.']),
    ('TALABARTE Y — FERRAGEM (ganchos automáticos, ganchos de conexão e argola D)', ['Esses itens não podem estar danificados, quebrados, distorcidos.', 'Devem estar isentos de bordas afiadas, rebarbas, rachaduras, partes gastas ou corrosão.', 'Teste o funcionamento das molas dos ganchos.']),
    ('TALABARTE Y — ETIQUETA', ['Certifique-se de que todas as etiquetas estejam presentes e indeléveis.']),
    ('TRAVA-QUEDAS DESLIZANTE — FERRAGEM', ['Verifique se as partes metálicas não apresentam deformações, fissuras ou traços de corrosão.', 'Observe se apresenta batidas, rachaduras ou torção.', 'O mosquetão deve estar em bom estado de conservação.', 'Analise o funcionamento do sistema de travamento e da mola de retorno.', 'O equipamento não pode apresentar sujidades.', 'O indicador de queda deve estar íntegro.']),
    ('TRAVA-QUEDAS DESLIZANTE — ETIQUETA', ['Certifique-se de que todas as etiquetas estejam presentes e indeléveis.'])]


def spiq_checklist(short: str, sections: list) -> dict:
    """LV11 — Inspeção SPIQ (A / AR / R). Todos os equipamentos SPIQ usam o mesmo modelo."""
    items = []
    for si, (sec, texts) in enumerate(sections, 1):
        for ti, txt in enumerate(texts, 1):
            items.append((f'{sec}: {txt}', f'{si}.{ti}'))
    cfg = standard_single_checklist(
        short, items,
        fields=[('cluster', 'Cluster'), ('local', 'Site'), ('model_belt', 'Cinturão — Modelo/N° Série'), ('model_pos', 'Talabarte de Posicionamento — Modelo/N° Série'), ('model_y', 'Talabarte Y — Modelo/N° Série'), ('model_arr', 'Trava-quedas — Modelo/N° Série'), ('company', 'Empresa'),
                ('inspection_type', 'Tipo de Inspeção (Inicial / Periódica)'), ('inspector', 'Nome do Inspetor'),
                ('acquisition_date', 'Data de Aquisição'), ('first_use_date', 'Data de Primeiro Uso')],
        note=SPIQ_NOTE)
    # Escala A / AR / R (valores internos mantidos: ATENDE / NA / NAO_ATENDE)
    cfg['scale'] = [('ATENDE', 'A', 'Aprovado', 'v-sim'), ('NA', 'AR', 'Aprovado com restrição', 'v-na'), ('NAO_ATENDE', 'R', 'Reprovado', 'v-nao')]
    cfg['ref'] = 'Ref.: RAC - Trabalho em<br/>Altura'
    return cfg


INSPECTION_MODULES = {
    'hoist': {
        'short': 'Inspeção de Talha Guincho',
        'mode': 'daily',
        'month_year': True,
        'periods': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'],
        'fields': [
            ('cluster_site', 'Cluster / Site'),
            ('local', 'Local'),
            ('turbine', 'Dados da turbina'),
            ('leader', 'Líder'),
        ],
        'items': [
            ('Corrente está livre de corrosão e bem lubrificada?',),
            ('A corrente está passando livremente pela talha, não apresentando ruídos e/ou vibrações anormais?',),
            ('Gancho está com movimento giratório livre, evitando torção da corrente?',),
            ('A trava do gancho está em perfeitas condições, livre de avarias, desgastes e deformações?',),
            ('Mola do Gancho - Inspecionar a elasticidade da mola, se a mesma está danificada, se está acionando o fim de curso da talha ao ser recolhida.',),
            ('O controle está bem fixado e o cabeamento está livre de fissuras? (Se equipado)',),
            ('Os botões de controle e emergência (se equipado) estão todos funcionando corretamente?',),
            ('Durante o funcionamento da talha não é observado nenhum som, movimento ou vibração que sejam incomuns.',),
            ('Guia da corrente está bem fixado e posicionado para o correto armazenamento da corrente no container? (Se equipado)',),
            ('Os sensores de fim de curso estão funcionando corretamente. *** Realize o teste da talha sem carga?',),
            ('Os freios estão funcionando corretamente. *** Execute o teste do freio durante a primeira subida de carga.',),
            ('A talha está bem fixa em seu suporte e os parafusos estão torqueados e com a marcação alinhada?',),
            ('Viga está livre de trincas, oxidação e possui todas as travas operativas? (Se equipado)',),
            ('Inspecionar o conjunto de fixação do balde e garantir que não existam movimentações/soltura do conjunto, gaps entre a alça e a base de fixação ou quaisquer',),
            ('Recolher a corrente após o uso.',),
            ('Fechar a escotilha do Yaw Deck após o recolhimento da corrente da talha.',),
        ],
        'template': 'Checklist Talha Guincho - Modelo.pdf',
    },
    'light_vehicle': {
        'short': 'Inspeção de Veículo Leve',
        'mode': 'daily',
        'month_year': False,
        'periods': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'],
        'fields': [
            ('cluster', 'Cluster'),
            ('local', 'Local'),
            ('vehicle', 'Veículo'),
            ('plate', 'Placa'),
            ('company', 'Empresa'),
        ],
        'items': [
            ('Freios',),
            ('Freio de estacionamento',),
            ('Motor de partida',),
            ('Limpador de para-brisa',),
            ('Lavador de para-brisa',),
            ('Buzina',),
            ('Faróis*',),
            ('Lanternas dianteiras (seta)*',),
            ('Lanternas traseiras (seta)*',),
            ('Luz de freio*',),
            ('Luz de ré',),
            ('Triângulo de advertência*',),
            ('Espelhos retrovisores*',),
            ('Indicadores de painel',),
            ('Pneus*',),
            ('Pneu estepe*',),
            ('Vidros',),
            ('Portas',),
            ('Cinto de segurança*',),
            ('Macaco',),
            ('Chave de roda',),
            ('Nível de óleo',),
            ('Nível fluido de freio',),
            ('Nível de água',),
        ],
        'nonconformities': 5,
        'template': 'Checklist Veiculo Leve - Modelo.pdf',
    },
    'height_kit': {
        'short': 'Inspeção diária antes da subida — Kit de Trabalho em Altura',
        'mode': 'daily',
        'month_year': True,
        'periods': ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo'],
        'fields': [
            ('cluster', 'Cluster'),
            ('site', 'Site'),
            ('brand', 'Marca'),
            ('model', 'Modelo'),
            ('company', 'Empresa'),
        ],
        'items': [
            ('O cinto encontra-se isento de sujidade acima do normal de óleo e graxa? (Que comprometa o material.)',),
            ("O Kit está completo, composto por: Cinturão, trava-quedas, talabarte de posicionamento, talabarte ''Y''?",),
            ('O tecido das fitas está sem desgastes ou danos (fiapos, repuxos, cortes)?*',),
            ('Os conectores estão em boa condição, e sem amassos ou deformações?',),
            ('Os dispositivos de trava do mosquetão estão funcionando corretamente?',),
            ('As fivelas do cinturão não possuem sinais de corrosão a ponto de comprometer o uso?',),
            ('As etiquetas de identificação do cinturão estão visíveis? Há identificação do C.A.?',),
            ('O absorvedor de energia está em bom estado de conservação? (Sem rompimento de costura.)*',),
            ('Realizado o Check-Cruzado por algum membro da equipe?',),
            ('Análise Preliminar de Risco foi discutida e, todos compreenderam? Está assinada?*',),
        ],
        'template': 'Checklist Kit Trabalho em Altura - Modelo.pdf',
    },
    'climber_assist': {
        'short': 'Inspeção Climber Assist',
        'mode': 'single',
        'month_year': False,
        'fields': [
            ('cluster', 'Cluster'),
            ('park', 'Parque / Unidade'),
            ('turbine', 'Turbina / Torre'),
            ('responsible', 'Responsável (Nome)'),
            ('model', 'Modelo do Climb Assist'),
        ],
        'items': [
            ('Cable Grip / Garra de Cabo: sem trincas, deformações ou dentes gastos; trava/aciona livremente; etiqueta legível.', '1.1'),
            ('Cabo de tração / lanyard do assistente: sem cortes, desfiamento, queimaduras, nós ou sinais de corrosão.', '1.2'),
            ('Unidade Motora (Motor Control Unit): carcaça íntegra, cabo de energia sem rachaduras, botão de emergência destravado.', '1.3'),
            ('Sistema trava-quedas de escada: cursor desliza livremente e trava sob tração; cabo/trilho sem folgas.', '1.4'),
            ('Arnês de segurança: costuras, fivelas e argolas (D-rings) íntegras; etiqueta de inspeção válida.', '1.5'),
            ('Conectores (mosquetões/ganchos): autotravantes, sem deformação; fecho trava corretamente.', '1.6'),
            ('Verificar o comando de subida e de descida do Climb Assist e confirmar se o equipamento opera conforme o comando acionado.', '2.1'),
            ('Localizar a região soldada da correia. Com um polegar em cada lado da solda, forçar a correia com a borda voltada para fora da curva; repetir na outra extremidade. Qualquer rachadura: contatar o fabricante.', '3.1'),
            ('Verificar, na área da solda, sinais de costura partida ou material do núcleo exposto. Havendo rachadura, contatar o fabricante.', '3.2'),
            ('Inspecionar visualmente a espessura da solda: o diâmetro no interior não deve ser maior que o diâmetro nominal da correia fora da região soldada, sem sobressaltos.', '3.3'),
            ('Registrar evidência fotográfica da solda após a inspeção.', '3.4'),
            ('Verificar se a etiqueta na parte traseira do controlador está presente e legível, e se a mola da garra está no lugar, forçando o fechamento.', '4.1'),
            ('Testar os botões do controlador: pressionar STOP e UP quatro vezes; pressionar STOP e DOWN quatro vezes.', '4.2'),
            ('Verificar se o mosquetão e o cinto de conexão estão em perfeito estado e travam corretamente; cinto livre de rasgos, com etiqueta de segurança.', '4.3'),
            ('Verificar as três conexões mecânicas entre a garra de corda e o cinto: (1) garra ao conector, (2) conector, (3) conector ao controle.', '4.4'),
        ],
        'template': 'Checklist Pre Uso Climber Assist.pdf',
    },
    'safety_belt': {
        'short': 'Inspeção estrutural — Cinto de Segurança',
        'mode': 'single',
        'month_year': False,
        'fields': [
            ('unit', 'Unidade'),
            ('manufacturer', 'Fabricante'),
            ('model', 'Modelo'),
            ('responsible', 'Responsável'),
        ],
        'items': [
            ('A sujeira presente no cinto é um impeditivo para o uso?', '1'),
            ('O cinto encontra-se completo? (não existe ausência de partes, componentes)', '2'),
            ('O cinto está em perfeito estado de conservação sem partes deformadas, partidas, fendidas ou frouxas?', '3'),
            ('As argolas estão em boas condições e sem trincas?', '4'),
            ('O talabarte do cinto encontra-se em perfeito estado de conservação, sem cortes, fios rompidos, ilhós oxidado, ressecado ou corroído por produtos químicos?', '5'),
            ('O mosquetão está travando corretamente?', '6'),
            ('O cadarço encontra-se em boas condições de uso, sem desgaste ou ressecamento?', '7'),
            ('Os ilhoses e fivelas do cinto de segurança apresentam-se sem sinais de ferrugem?', '8'),
            ('A trava do gancho encontra-se em perfeito estado? (duplo travamento, molas oxidadas, trava quebrada, parte metálica oxidada)', '9'),
            ('Trava-quedas possui dupla trava de segurança?', '10'),
            ('O número do CA está identificado com gravação visível?', '11'),
            ('A data de fabricação, o lote do cinturão e os talabartes estão identificados de forma visível?', '12'),
            ('O absorvedor de energia está em perfeito estado? (sem rompimento da costura)', '13'),
            ('A montagem do cinto está correta?', '14'),
            ('O cinto está com dois talabartes?', '15'),
            ('Possui ponto de ancoragem nos ombros para resgate em espaço confinado?', '17'),
        ],
        'template': 'Checklist Cinto de Seguranca - Modelo.pdf',
    },

    'loto': {
        'short': 'Formulário Padrão de LOTO',
        'mode': 'single',
        'month_year': False,
        'fields': [
            ('company', 'Nome da empresa'),
            ('responsible', 'Responsável / Autorizado pela aplicação do LOTO'),
            ('role', 'Função'),
            ('park', 'Local da atividade (Parque Eólico)'),
            ('aeg_number', 'Nº AEG'),
            ('manufacturer_model', 'Fabricante / Modelo do AEG'),
            ('loto_start_time', 'Horário: início do LOTO'),
            ('loto_end_time', 'Horário: conclusão do LOTO'),
            ('work_description', 'Descrição do trabalho'),
            ('loto_devices', 'Dispositivos de LOTO utilizados'),
        ],
        'items': [
            ('Preparar para desligar o AEG de forma LOCAL AEG seguindo os passos corretamente.', '1'),
            ('DESLIGUE O AEROGERADOR LOCAL: acione IDLE/DESLIGAR; gire a chave para manutenção; aplique o LOTO no Q1 do AEG para impedir comandos remotos.', '2'),
            ('Garanta que a velocidade de vento esteja dentro dos limites corretos conforme orientado pelo cliente/contratante.', '3'),
            ('Posicione o ROTOR e utilize o freio hidráulico para parar o rotor na posição de 3 ou 9h.', '4'),
            ('Aplique a Trava do Rotor e verifique se está bem engatada.', '5'),
            ('Aplique o dispositivo de LOTO na Trava do Rotor.', '6'),
            ('Verifique visualmente se o dispositivo de bloqueio do Rotor de Alta Velocidade está totalmente engatado.', '7'),
            ('O escopo de trabalho exige que o Yaw esteja desabilitado?', '8'),
            ('Desative o YAW de forma Downtower.', '9'),
            ('Antes de tocar em qualquer peça exposta, verifique sempre a energia zero C40 diretamente no componente.', '10'),
            ('Notifique todos os Funcionários Afetados que o sistema será destravado.', '11'),
            ('Assegure-se de que a área de trabalho esteja limpa e segura para desbloquear o ROTOR.', '12'),
            ('Certifique-se de que todas as ferramentas do Hub foram removidas e a área de trabalho está desobstruída.', '13'),
            ('Remova todos os dispositivos de LOTO aplicados no bloqueio do rotor e destrave o bloqueio do rotor.', '14'),
            ('Verifique se o ambiente está seguro e livre de riscos adicionais.', '15'),
            ('O YAW será ativado para automático Downtower.', '16'),
            ('Após todas as etapas coloque o Aerogerador em Operação e informe ao contratante/cliente.', '17'),
        ],
    },
    'grinder': standard_daily_checklist(
        'Lista de Verificação — Esmerilhadeira',
        'Modelo da esmerilhadeira',
        [
            'O disco está em boas condições?*',
            'O disco é apropriado para atividade que será realizada?*',
            'Botão seletor liga/desliga está em boa condição?',
            'A carcaça está em boas condições?',
            'Flange de apoio em boas condições?',
            'Capa de proteção em boas condições, devidamente instalada?*',
            'Empunhadeira em boas condições, devidamente instalada?',
            'Bloqueio do eixo em funcionamento?',
            'Os cabos de alimentação estão em boas condições?*',
            "EPI's para operação (Capacete, óculos, luvas, protetor auricular, botina de segurança).*",
            'A APR está disponível? Todos estão cientes?*',
        ],
    ),
    'drill': standard_daily_checklist(
        'Lista de Verificação — Furadeira',
        'Modelo da furadeira',
        [
            'Os cabos de alimentação estão em boas condições?',
            'Carcaça da furadeira está em boas condições?',
            'Mandril e chave do mandril em boas condições?',
            'Gatilho de acionamento em boas condições?*',
            'Chave seletora de impacto.',
            'Punho de segurança.',
            'Botão seletor liga/desliga.*',
            "EPI's para operação (Capacete, óculos, luvas, protetor auricular, botina de segurança).*",
            'A APR está disponível? Todos estão cientes?*',
        ],
    ),
    'rotary_hammer': standard_daily_checklist(
        'Lista de Verificação — Martelete',
        'Modelo do martelete',
        [
            'Os cabos de alimentação estão em boas condições? Os mesmos não devem estar enrolados.',
            'Carcaça do martelete está em boas condições?',
            'A ponteira trava corretamente no equipamento?*',
            'Ponteira em boas condições?*',
            'Chave seletora de impacto.*',
            'Punho auxiliar.',
            'Botão seletor liga/desliga.*',
            "EPI's para operação (Capacete, óculos, luvas, protetor auricular, botina de segurança).*",
            'A APR está disponível? Todos estão cientes?*',
        ],
    ),
    'circular_saw': standard_daily_checklist(
        'Lista de Verificação — Serra Circular',
        'Modelo da serra',
        [
            'O disco da serra está em boas condições?*',
            'Existe coifa protetora?*',
            'Existe cutelo divisor?',
            'Mesa estável e em boas condições?*',
            'Chave seletora de impacto.',
            'As guias empurradoras estão disponíveis?*',
            'Botão seletor liga/desliga está protegido?*',
            'A iluminação é adequada e suficiente?*',
            'Existe botão de parada de emergência?*',
            "EPI's para operação (Capacete, óculos, luvas, protetor auricular, botina de segurança).*",
            'A APR está disponível? Todos estão cientes?*',
        ],
    ),
    'marble_saw': standard_daily_checklist(
        'Lista de Verificação — Serra Mármore',
        'Modelo da serra',
        [
            'O disco da serra está em boas condições?*',
            'A capa protetora da serra está em boas condições?',
            'A placa base está em boas condições?',
            'Botão seletor liga/desliga está em boa condição?',
            'Flange externa em boas condições?',
            "EPI's para operação (Capacete, óculos, luvas, protetor auricular, botina de segurança).*",
            'A APR está disponível? Todos estão cientes?*',
            'Bancada para operação disponível?*',
        ],
    ),
    'welding_machine': standard_daily_checklist(
        'Lista de Verificação — Máquina de Solda',
        'Modelo da máquina',
        [
            'A carcaça está em boas condições?',
            'Os cabos de alimentação estão em boas condições? (A tomada deve ser compatível com o plugue.)',
            'Chave seletora liga/desliga em boas condições?',
            'Máquina encontra-se aterrada?*',
            'A peça a ser soldada está aterrada?',
            'A peça a ser soldada encontra-se isenta de sujidade: óleo, graxa?',
            'Capa de proteção do eletrodo está íntegra?*',
            'Alavanca de regulagem da amperagem encontra-se em bom estado?',
            'Local da atividade encontra-se bem ventilado?',
            'Existe extintor de incêndio adequado para a atividade?*',
            'É necessário a instalação de biombos?',
            'Área isolada e delimitada?',
            'O reboque da máquina está em bom estado?',
            "EPI's para operação (Capacete, respirador, proteção facial, óculos, luvas, protetor auricular, botina de segurança, luvas e avental).*",
            'A APR está disponível? Todos estão cientes?*',
        ],
    ),
    'spiq': spiq_checklist('Equipamentos SPIQ', SPIQ_SECTIONS),
    'lifting_accessories': standard_single_checklist(
        'Lista de Verificação — Acessórios de Içamento de Carga',
        [
            ('Ganchos: Gancho em perfeitas condições para utilização.', '1.1'),
            ('Ganchos: Danos mecânicos.', '1.2'),
            ('Ganchos: Identificação de carga máxima.*', '1.3'),
            ('Ganchos: Identificação única legível (TAG).', '1.4'),
            ('Correntes: Correntes identificadas (TAG e capacidade de carga).*', '2.1'),
            ('Correntes: Ausência de deformação por dobra ou torção.*', '2.2'),
            ('Correntes: Ausência de elos danificados por amassamento.', '2.3'),
            ('Correntes: Ausência de elos danificados por entalhamento.', '2.4'),
            ('Correntes: Ausência de elos danificados com fissuras.', '2.5'),
            ('Correntes: Ausência de elos dobrados.', '2.6'),
            ('Correntes: Identificação de carga máxima.*', '2.7'),
            ('Correntes: Identificação única legível (TAG).', '2.8'),
            ('Cabo de aço: Cabo de aço em perfeitas condições para utilização.*', '3.1'),
            ('Cabo de aço: Arames externos das pernas visíveis.', '3.2'),
            ('Cabo de aço: Corrosões acentuadas.', '3.3'),
            ('Cabo de aço: Arames rompidos junto aos terminais.', '3.4'),
            ('Cabo de aço: Terminais mal instalados.', '3.5'),
            ('Cabo de aço: Terminais desgastados.', '3.6'),
            ('Cabo de aço: Terminais tortos.', '3.7'),
            ('Cabo de aço: Terminais trincados.', '3.8'),
            ('Cabo de aço: Presilhas desgastadas.', '3.9'),
            ('Cabo de aço: Apresenta cinco arames rompidos distribuídos aleatoriamente em um passo.', '3.10'),
            ('Cabo de aço: Apresenta três arames rompidos em uma única perna dentro de um passo do cabo.', '3.11'),
            ('Cabo de aço: Apresenta arame externo rompido.', '3.12'),
            ('Cabo de aço: Apresenta alma rompida.', '3.13'),
            ('Cabo de aço: Sinais de torção.', '3.14'),
            ('Cabo de aço: Nós.', '3.15'),
            ('Cabo de aço: Sinais de dobra.', '3.16'),
            ('Cabo de aço: Formação de gaiola de passarinho.', '3.17'),
            ('Cabo de aço: Alma de aço apresenta sinais de rompimento.', '3.18'),
            ('Cabo de aço: Identificação de carga máxima.', '3.19'),
            ('Cabo de aço: Identificação única legível (TAG).', '3.20'),
            ('Cintas: Há cortes transversais na cinta?', '4.1'),
            ('Cintas: Há cortes longitudinais na cinta?', '4.2'),
            ('Cintas: Há rupturas de costura no olhal?', '4.3'),
            ('Cintas: Ruptura de costura ao longo da cinta?', '4.4'),
            ('Cintas: Há danos devido a abrasão nas cintas?', '4.5'),
            ('Cintas: Etiqueta da cinta em condição legível?', '4.6'),
            ('Cintas: Identificação de carga máxima (vertical).', '4.7'),
            ('Cintas: Identificação única legível (TAG).', '4.8'),
            ('Manilha / Olhal / Anel / Grampo: Sinais de corrosão.', '5.1'),
            ('Manilha / Olhal / Anel / Grampo: Presença de trincas.*', '5.2'),
            ('Manilha / Olhal / Anel / Grampo: Danos à rosca (manilha e grampos).', '5.3'),
            ('Manilha / Olhal / Anel / Grampo: Identificação de carga máxima.', '5.4'),
            ('Manilha / Olhal / Anel / Grampo: Identificação única legível (TAG).', '5.5'),
        ],
        fields=[('unit', 'Site'), ('company', 'Empresa'), ('responsible', 'Responsável pela inspeção')],
        note='Caso algum item esteja não conforme, o equipamento está inapto para o trabalho. O operador deverá informar o líder operacional para providenciar a correção. Itens marcados com * são impeditivos.',
    ),
}


# =====================================================================
# RACs — Requisitos para Atividades Críticas
# Conteúdo extraído das planilhas oficiais fornecidas em 22/09/2026.
# =====================================================================
from .rac_configs import RAC_MODULES

for _rac_kind, _rac_cfg in RAC_MODULES.items():
    DOCUMENT_TITLES[_rac_kind] = _rac_cfg['title']
    PREFIXES[_rac_kind] = _rac_cfg['prefix']

