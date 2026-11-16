"""Configurações das RACs integradas ao Safety Plus.

Gerado a partir das planilhas oficiais fornecidas pelo usuário em 22/09/2026.
As perguntas são mantidas no sistema para permitir rascunho, finalização, histórico e PDF próprios.
Os textos dos requisitos são mantidos integralmente, sem abreviação.
"""

RAC_MODULES = {'rac_height': {'title': 'RAC — Trabalho em Altura',
                'short': 'Trabalho em Altura',
                'icon': 'mi-hardhat',
                'prefix': 'RAC-ALT',
                'revision': 'Rev. 1\nMaio/2023',
                'source_file': 'Trabalho em altura.xlsx',
                'response_mode': 'atende',
                'groups': [{'name': 'PESSOAS',
                            'items': [{'section': '1. SAÚDE',
                                       'number': '1.1',
                                       'text': 'Os exames ocupacionais vigentes para comprovar a aptidão para realizar '
                                               'trabalho em altura e o Atestado de Saúde Ocupacional (ASO) estão '
                                               'válidos e aprovados, a aptidão está\n'
                                               'esta mencionada por escrito na ASO?',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. SAÚDE',
                                       'number': '1.2',
                                       'text': 'Os ASOs para trabalhos em altura inclui, em adição ao exame clínico '
                                               'básico, os seguintes exames complementares: acuidade visual, '
                                               'audiometria ocupacional, eletroencefalograma, eletrocardiograma, '
                                               'glicemia em jejum, hemograma completo?',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. SAÚDE',
                                       'number': '1.3',
                                       'text': 'Os exames ocupacionais e a sistemática de avaliação fazem parte do PGR '
                                               '(Plano de Gerenciamento de Riscos) e PCMSO (Plano de Controle Médio de '
                                               'Saúde Ocupacional), conforme NR-1 e NR-7?',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. SAÚDE',
                                       'number': '1.4',
                                       'text': 'A avaliação dos exames ocupacionais, a definição da a aptidão para '
                                               'realizar atividades que envolvam trabalho em altura e a emissão do '
                                               'Atestado de Saúde Ocupacional (ASO) são realizadas por médico do '
                                               'trabalho habilitado?',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CAPACITAÇÃO',
                                       'number': '2.1',
                                       'text': 'Todo coempreendedor ou terceiro que realiza trabalhos em altura e/ ou '
                                               'montagem de andaime recebeu autorização formal de sua organização e  '
                                               'treinamento para trabalho em altura e reciclagem bienal, conforme '
                                               'NR-35 item 35.4 e subitens?',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CAPACITAÇÃO',
                                       'number': '2.2',
                                       'text': 'Os executores das atividades que envolvam trabalho em altura, com '
                                               'acesso por cordas, em adição aos treinamentos definidos na NR-35, '
                                               'devem:\n'
                                               '- Ser qualificados como Profissionais de Acesso por Cordas Nível 1, 2 '
                                               'ou 3\n'
                                               '(N1, N2 ou N3) conforme especificado na NBR 15475:2015 - Acesso por '
                                               'corda / Qualificação e certificação de pessoas;\n'
                                               '- A atividade deve ser supervisionada no local e o supervisor deve '
                                               'possuir qualificação N3.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CAPACITAÇÃO',
                                       'number': '2.3',
                                       'text': 'Nas atividades que envolvem a utilização de plataforma elevatória '
                                               'móvel de trabalho (PEMT), em adição aos treinamentos definidos na '
                                               'NR-35, devem realizar e serem aprovados em treinamento teórico e '
                                               'prático com carga horária mínima de 4 horas com reciclagem bianual '
                                               '(NR-18) e conteúdo definido pelo fabricante e/ou empresa usuária da '
                                               'PEMT',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CAPACITAÇÃO',
                                       'number': '2.4',
                                       'text': '35.4.1.3.1 A organização deve estabelecer sistema de identificação que '
                                               'permita a qualquer tempo conhecer a abrangência da autorização de cada '
                                               'trabalhador.',
                                       'requirement': '',
                                       'recommendation': ''}]},
                           {'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                            'items': [{'section': '1. EPI',
                                       'number': '1.1',
                                       'text': 'Os EPIs para proteção contra queda em trabalhos em altura devem ser:\n'
                                               '- Certificados, ou seja, com CA e atendendo às normas aplicáveis;\n'
                                               '- Adequados para a utilização pretendida;\n'
                                               '- Utilizados considerando os limites de uso;\n'
                                               '- Ajustados ao peso e à altura do trabalhador.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. EPI',
                                       'number': '1.2',
                                       'text': 'As cordas de fibra, fitas e fios de costura devem:\n'
                                               'a) ser fabricados de fibras sintéticas virgens mono ou multifilamento '
                                               '(polipropileno não é aceitável);\n'
                                               'b) a resistência à ruptura das fibras sintéticas deve ser, no mínimo, '
                                               'de 0,6 N/tex;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. EPI',
                                       'number': '1.3',
                                       'text': '- Os cabos metálicos devem ser de aço e as sapatilhas embutidas nos '
                                               'terminais e ser de um material metálico dúctil. Os cabos metálicos não '
                                               'fabricados de aço inoxidável devem ser galvanizados de acordo com a '
                                               'ABNT NBR ISO 2408;\n'
                                               '- As correntes devem cumprir, como mínimo, os requisitos referentes às '
                                               'correntes de 6 mm, estabelecidos na EN 818-2. Os elos finais, com '
                                               'forma oval ou similar, assim como todos os elos de conexão, devem ser '
                                               'compatíveis com a corrente em todos os aspectos;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. EPI',
                                       'number': '1.4',
                                       'text': 'Os conectores devem estar e conformidade com a ABNT NBR 15837 que é '
                                               'evidenciada pelas as seguintes marcações / indicações em português e '
                                               'legíveis:\n'
                                               'a) código e/ou modelo do conector;\n'
                                               'b) data e/ou lote de fabricação;\n'
                                               'c) menção à NBR 15837 e classe do conector;\n'
                                               'd) resistência estática mínima do eixo maior ou a resistência '
                                               'informada pelo fabricante (quando maior) gravada no corpo do conecto, '
                                               'em kN, e corresponder à posição fechada e travada;\n'
                                               'e) marca do fabricante ou responsável pela comercialização;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CINTO DE SEGURANÇA TIPO PARAQUEDISTA',
                                       'number': '2.1',
                                       'text': 'Deve atender aos seguintes requisitos: \n'
                                               '- As fitas e os fios de costura devem ser fabricados a partir de '
                                               'fibras sintéticas virgens mono ou multifilamento (polipropileno não é '
                                               'aceitável), os fios devem ter cores contrastantes ao material básico '
                                               'para facilitar a inspeção visual;\n'
                                               '- A resistência à ruptura das fibras sintéticas deve ser, no mínimo, '
                                               'de 0,6 N/tex; \n'
                                               '- Ser constituído de fitas desde a região da pélvis até os ombros, '
                                               'ajustável ao usuário, sendo a largura mínima das fitas primárias (que '
                                               'exerce funções de sustentação) 40 mm e das secundárias (que não '
                                               'exercem funções de sustentação) 20 mm;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CINTO DE SEGURANÇA TIPO PARAQUEDISTA',
                                       'number': '2.2',
                                       'text': 'Deve atender aos seguintes requisitos: \n'
                                               '- Os elementos de engate para proteção contra queda podem estar '
                                               'situados de forma que, durante a utilização do equipamento, se '
                                               'encontrem acima do centro de gravidade do corpo, no peito e/ou nas '
                                               'costas do usuário;\n'
                                               '- Os conectores devem cumprir os requisitos da ABNT NBR 15837 e os '
                                               'acessórios metálicos devem estar em conformidade com os requisitos de '
                                               'proteção contra a corrosão especificados na ABNT NBR 8094;\n'
                                               '- Ser aprovado nos ensaios de resistência estática, resistência '
                                               'dinâmica e resistência à corrosão por exposição à névoa salina, '
                                               'conforme NBR 15836;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. CINTO DE SEGURANÇA TIPO PARAQUEDISTA',
                                       'number': '2.3',
                                       'text': 'Deve conter as seguintes marcações / indicações em português e '
                                               'legíveis:\n'
                                               'a) pictograma que indique que os usuários devem ler as informações / '
                                               'manual fornecidos pelo fabricante;\n'
                                               'b) pictograma com a letra "A" maiúscula em cada elemento de engate '
                                               'para proteção contra queda;\n'
                                               'c) pictograma com uma marcação “A/N”, maiúscula, quando existirem n '
                                               'elementos de engate simultâneos;\n'
                                               'd) indicação de atendimento à NBR 15836;\n'
                                               'e) código e tamanho;\n'
                                               'f) data de fabricação e lote;\n'
                                               'g) logotipo e/ou nome do fabricante nacional ou importado.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '3. TALABARTES',
                                       'number': '3.1',
                                       'text': 'Deve atender aos seguintes requisitos:\n'
                                               '- O comprimento de um talabarte simples, duplo ou regulável com seus '
                                               'terminais, não pode exceder 2,00 m em sua totalidade, medido a partir '
                                               'dos pontos de contato dos terminais;\n'
                                               '- Os talabartes que tiverem mais de 0,90 m e forem utilizados em um '
                                               'sistema antiqueda, devem possuir absorvedor de energia em conformidade '
                                               'com a ABNT NBR 14629, neste caso o comprimento do talabarte deve ser '
                                               'determinado com o absorvedor de energia intacto;\n'
                                               '- Os talabartes com fitas elásticas devem ser esticados para a '
                                               'obtenção do seu comprimento;\n'
                                               '- Os extremos da seção regulável do talabarte devem estar dotados de '
                                               'um batente final;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '3. TALABARTES',
                                       'number': '3.2',
                                       'text': 'Deve ser aprovado nos ensaios de resistência estática, resistência '
                                               'dinâmica e  resistência à corrosão por exposição à névoa salina, '
                                               'conforme NBR 15834; \n'
                                               '- Deve conter as seguintes marcações / indicações em português e '
                                               'legíveis:\n'
                                               'a) nome do fabricante, fornecedor ou marca comercial;\n'
                                               'b) lote de fabricação ou número de série e data de fabricação;\n'
                                               'c) modelo e tipo;\n'
                                               'd) pictograma que indique que os usuários devem ler as informações /  '
                                               'manual fornecidos pelo fabricante; \n'
                                               'e) menção à NBR 15834;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '3. TALABARTES',
                                       'number': '3.3',
                                       'text': 'Nos talabartes com absorvedor de energia, deve ser informada a zona '
                                               'livre de queda. É recomendado o uso de um pictograma que informe a '
                                               'distância da zona livre de queda, que compreende o ponto de ancoragem '
                                               'e o solo ou ponto mais provável de impacto.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.1',
                                       'text': 'Trava-quedas Ancoragem em linha flexível:\n'
                                               '- A linha de ancoragem flexível deve ser fixada em um ponto de '
                                               'ancoragem superior e deve possuir um batente superior, ou ser capaz de '
                                               'ajustar-se a um batente superior, para evitar que o trava-queda '
                                               'deslizante se separe, de modo involuntário, da linha de ancoragem;\n'
                                               '- Caso o trava-queda possua uma trava manual (mecanismo que bloqueia o '
                                               'trava-queda deslizante na linha de ancoragem), o extremo inferior da '
                                               'linha de ancoragem flexível deve ter uma terminação, por exemplo, um '
                                               'terminal inferior fixo ou um lastro;\n'
                                               '- Uma linha de ancoragem flexível feita de cabo metálico deve ser '
                                               'dotada, em todos os casos, de um terminal inferior ou um lastro.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.2',
                                       'text': 'Trava-quedas Ancoragem em linha rígida:\n'
                                               '- Deve ser constituída por um trilho ou cabo metálico, o cabo metálico '
                                               'deve possuir um diâmetro de 8 mm ou uma dimensão que proporcione '
                                               'segurança equivalente;\n'
                                               '-Para limitar movimentos laterais deve ser fixada na estrutura a '
                                               'intervalos estabelecidos; se for formada por cabo metálico, este deve '
                                               'estar firmemente fixado e tensionado sobre uma estrutura;\n'
                                               '- A linha de ancoragem deve ser projetada de tal forma que o '
                                               'trava-queda se movimente nas direções especificadas e que seja '
                                               'impedida a separação voluntária do trava-queda da linha de ancoragem;\n'
                                               '- Todos os pontos de engate e desengate da linha de ancoragem devem '
                                               'estar equipados com um batente final para evitar que o trava-queda se '
                                               'separe involuntariamente da linha de ancoragem.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.3',
                                       'text': 'Trava-queda:\n'
                                               '- Deve estar equipado com um conector ou com um extensor mais um '
                                               'conector, com um comprimento máximo de 1m, incluindo, se for o caso, '
                                               'absorvedor de energia e conectores. Se possuir somente conector, este '
                                               'pode estar unido de modo permanente ou ser separável. O comprimento do '
                                               'extensor deve ser especificado pelo fabricante e estar indicado nas '
                                               'instruções de uso. \n'
                                               '- O mecanismo para a sua abertura deve ser projetado de forma  que só '
                                               'pode ser aberto ou fechado, mediante duas ações manuais consecutivas e '
                                               'voluntárias;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.4',
                                       'text': 'O absorvedor de energia, integrado ou não com o extensor, deve estar '
                                               'conformidade com a ABNT NBR 14629; e a força de impacto transmitida ao '
                                               'trabalhador seja de no máximo 6kN quando de uma eventual queda '
                                               'indicador de fim de vida útil;\n'
                                               'A conformidade a ABNT NBR 14629 é evidenciada pelas seguintes '
                                               'marcações / indicações em português e legíveis:\n'
                                               'a) nome fabricante, fornecedor ou marca comercial; \n'
                                               'b) lote de fabricação ou número de série e data de fabricação;\n'
                                               'c) modelo e tipo;\n'
                                               'd) pictograma que indique que os usuários devem ler as informações / '
                                               'manual fornecidos pelo fabricante;\n'
                                               'e) menção da NBR 14629;\n'
                                               'f) informação de que o comprimento máximo do absorvedor de energia '
                                               '(sem extensão), com o talabarte e conectores, não pode exceder 2,0 m;\n'
                                               'g) comprimento do absorvedor, após distensão total máxima, para '
                                               'absorvedores de energia vendidos como componentes, para possibilitar o '
                                               'cálculo da zona livre de queda, quando este for montado a um sistema '
                                               'de retenção de queda;\n'
                                               'h) nos absorvedores de energia incorporados a talabartes de segurança, '
                                               'a informação sobre a zona livre de queda. Deve conter um pictograma '
                                               'que informe a distância da zona livre de queda, que compreende o ponto '
                                               'de ancoragem e o solo ou ponto mais provável de impacto.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.5',
                                       'text': 'Ser aprovado nos ensaios de travamento, resistência estática, '
                                               'resistência estática, comportamento dinâmico e resistência à corrosão '
                                               'por exposição à névoa salina, conforme NBR 14626 (ancorado em linha '
                                               'flexível) ou NBR 14627 (ancorado em linha rígida);',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.6',
                                       'text': 'Deve conter as seguintes marcações / indicações em português e '
                                               'legíveis:\n'
                                               'a)\tpictograma que indique que os usuários devem ler as informações / '
                                               'manual fornecidos pelo fabricante;\n'
                                               'b)\tindicação da posição correta de uso.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.7',
                                       'text': 'Para ancoragem em linha flexível:\n'
                                               'c) indicação informando ao usuário que deve ser utilizada somente a '
                                               'linha de ancoragem flexível especificada pelo fabricante;\n'
                                               'd) identificação do modelo e de que é um trava-queda deslizante para '
                                               'linha flexível;\n'
                                               'e) menção à NBR 14626.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                       'number': '4.8',
                                       'text': 'Para ancoragem em linha rígida:\n'
                                               'c)  caso possa ser removido da linha de ancoragem rígida, deve existir '
                                               'informação sobre sua utilização em linhas rígidas apropriadas, gravada '
                                               'no trava-queda ou em uma zona adjacente à linha;\n'
                                               'd)  identificação do modelo e de que é um trava-queda deslizante para '
                                               'linha rígida;\n'
                                               'e)  menção à NBR 14627.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '5. SISTEMAS DE ANCORAGEM',
                                       'number': '5.1',
                                       'text': 'A ancoragem estrutural e seus elementos de fixação devem:\n'
                                               '-Ser projetados e construídos sob responsabilidade de profissional '
                                               'legalmente habilitado;\n'
                                               '-Atender às normas técnicas nacionais ou, na sua inexistência, às '
                                               'normas internacionais aplicáveis;\n'
                                               '- Os pontos da ancoragem devem possuir marcação realizada pelo '
                                               'fabricante ou responsável contendo, no mínimo:\n'
                                               'a) identificação do fabricante;\n'
                                               'b) número de série ou outro meio de rastreabilidade\n'
                                               'c) número máximo de trabalhadores conectados simultaneamente ou força '
                                               'máxima aplicável.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '5. SISTEMAS DE ANCORAGEM',
                                       'number': '5.2',
                                       'text': 'Dispositivo de ancoragem deve ser:\n'
                                               '- Certificado;\n'
                                               '- Fabricado em conformidade com as normas técnicas nacionais vigentes '
                                               'sob responsabilidade do profissional legalmente habilitado;\n'
                                               '- Projetado por profissional legalmente habilitado, tendo como '
                                               'referência as normas técnicas nacionais vigentes, como parte '
                                               'integrante de um sistema completo de proteção individual contra '
                                               'quedas.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '5. SISTEMAS DE ANCORAGEM',
                                       'number': '5.3',
                                       'text': 'Os sistemas de ancoragem devem ser:\n'
                                               '- Instalados por trabalhadores capacitados;\n'
                                               '- Submetidos à inspeção inicial e periódica;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '5. SISTEMAS DE ANCORAGEM',
                                       'number': '5.4',
                                       'text': 'Inspeção em sistemas de ancoragem:\n'
                                               ' - A inspeção inicial deve ser realizada após a instalação, alteração '
                                               'ou mudança de local;\n'
                                               '- inspeção periódica deve ser efetuada de acordo com o procedimento '
                                               'operacional, considerando o projeto, respeitando as instruções do '
                                               'fabricante e as normas regulamentadoras e técnicas aplicáveis, com '
                                               'periodicidade não superior a 12 meses.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '5. SISTEMAS DE ANCORAGEM',
                                       'number': '5.5',
                                       'text': 'Sistema de ancoragem temporário deve:\n'
                                               '- Atender os requisitos de compatibilidade a cada local de instalação '
                                               'conforme procedimento operacional;\n'
                                               '- Ter os pontos de fixação definidos sob responsabilidade de '
                                               'profissional legalmente habilitado.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '5. SISTEMAS DE ANCORAGEM',
                                       'number': '5.6',
                                       'text': 'Um sistema de ancoragem deve possuir projeto e a instalação deve estar '
                                               'sob responsabilidade de profissional legalmente habilitado.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.1',
                                       'text': 'Os cálculos para dimensionamento dos andaimes, sua estrutura de '
                                               'fixação e sustentação devem ser realizado por profissionais legalmente '
                                               'habilitados, com ART, de acordo com a NBR-9464 e NR-18 item 18.12 e '
                                               'fabricados por empresas regularmente inscritas no respectivo conselho '
                                               'de classe;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.2',
                                       'text': 'A montagem do andaime deve ser acompanhada por profissional legalmente '
                                               'habilitado e deve ser sinalizado que está bloqueado para o uso até sua '
                                               'liberação;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.3',
                                       'text': 'Os andaimes devem possuir registro formal para liberação: cartão de '
                                               'liberação informado o equipamento ou estrutura a que o andaime está '
                                               'acessando, os serviços autorizados a serem realizados, data da '
                                               'liberação e assinado por profissional legalmente habilitado;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.4',
                                       'text': 'Os andaimes, quando não estaiados ou não fixados à estrutura, não '
                                               'podem exceder, em altura, 4 (quatro) vezes a menor dimensão da base de '
                                               'apoio;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.5',
                                       'text': 'Estrutura do andaime deve:\n'
                                               '- Ser tubular, não de encaixe, em aço galvanizado, com braçadeiras '
                                               'fixas e giratórias, base fixa e ajustável possuir montantes e painéis '
                                               'fixados com travamento contra o desencaixe acidental;\n'
                                               '- Possuir possuir sistema de proteção contra quedas em todo o '
                                               'perímetro com exceção do lado da face de trabalho; podendo ser rígida '
                                               'ou composta por guarda-corpo e rodapé (NR-18, requisitos 18.9.4.1/2);\n'
                                               '- A superfície de trabalho com ter forração completa, antiderrapante, '
                                               'nivelada e possuir travamento que não permita seu deslocamento ou '
                                               'desencaixe;\n'
                                               '- Ser apoiado em sapatas sobre base rígida e nivelada, com ajustes que '
                                               'permitam o nivelamento, ou seja, não utilizar rodízios;\n'
                                               '- Ser fixado, quando necessário, à estrutura da construção ou '
                                               'edificação, por meio de amarração, de modo a resistir aos esforços a '
                                               'que estará sujeito;\n'
                                               '- Possuir placa de identificação fixada em local de fácil visualização '
                                               'e conter a identificação do fabricante e a capacidade de carga em peso '
                                               'e número de ocupantes.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.6',
                                       'text': 'O acesso ao andaime, cujo piso de trabalho esteja situado a mais de '
                                               '1,0 m de altura deve ser feito por meio de escadas, por uma das '
                                               'seguintes alternativas:\n'
                                               '- Escada de mão, incorporada ou acoplada aos painéis, com largura '
                                               'mínima de 0,40 m e distância uniforme entre os degraus compreendida '
                                               'entre 0,25 e 0,30 m;\n'
                                               '- Escada para uso coletivo, incorporada interna ou externamente ao '
                                               'andaime, com largura mínima de 0,60 m, corrimão e degraus '
                                               'antiderrapantes;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '6. ANDAIMES (Considerados apenas andaimes simplesmente apoiados)',
                                       'number': '6.7',
                                       'text': 'O ponto de instalação de qualquer aparelho de içar materiais no '
                                               'andaime deve ser escolhido de modo a não comprometer a sua '
                                               'estabilidade e a segurança do trabalhador.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.1',
                                       'text': 'Dispositivos de segurança que garantam seu perfeito nivelamento no '
                                               'ponto de trabalho;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.2',
                                       'text': 'Alça de apoio interno;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.3',
                                       'text': 'Sistema de proteção contra quedas;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.4',
                                       'text': 'Botão de parada de emergência;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.5',
                                       'text': 'Dispositivo de emergência que possibilite baixar o trabalhador e a '
                                               'plataforma até o solo em caso de pane elétrica, hidráulica ou '
                                               'mecânica;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.6',
                                       'text': 'Sistema sonoro automático de sinalização acionado durante a subida e a '
                                               'descida;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.7',
                                       'text': 'Proteção contra choque elétrico;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.8',
                                       'text': 'Horímetro.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '7. PLATAFORMA ELEVATÓRIA MÓVEL DE TRABALHO – PEMT',
                                       'number': '7.9',
                                       'text': 'Devem ser utilizados sistema de proteção individual contra quedas '
                                               'conectado nos pontos de ancoragem definidos pelo fabricante.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '8. ACESSO POR CORDAS',
                                       'number': '8.1',
                                       'text': 'As cordas utilizadas devem atender aos requisitos das normas técnicas '
                                               'nacionais.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '8. ACESSO POR CORDAS',
                                       'number': '8.2',
                                       'text': 'Os equipamentos auxiliares utilizados devem ser certificados de acordo '
                                               'com normas técnicas nacionais ou, na ausência dessas, de acordo com '
                                               'normas técnicas internacionais.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '8. ACESSO POR CORDAS',
                                       'number': '8.3',
                                       'text': 'Na inexistência de normas técnicas internacionais, a certificação por '
                                               'normas estrangeiras pode ser aceita desde que atendidos aos requisitos '
                                               'previstos na norma europeia (EN).',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '8. ACESSO POR CORDAS',
                                       'number': '8.4',
                                       'text': 'Durante a execução da atividade o trabalhador deve estar conectado a '
                                               'pelo menos duas cordas em pontos de ancoragem independentes.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '8. ACESSO POR CORDAS',
                                       'number': '8.5',
                                       'text': 'A execução da atividade com o trabalhador conectado a apenas uma corda '
                                               'pode ser permitida se atendidos cumulativamente aos seguintes '
                                               'requisitos:\n'
                                               '-\tFor evidenciado na análise de risco que o uso de uma segunda corda '
                                               'gera um risco superior;\n'
                                               '-\tSejam implementadas medidas suplementares, previstas na análise de '
                                               'risco, que garantam um desempenho de segurança no mínimo equivalente '
                                               'ao uso de duas cordas.',
                                       'requirement': '',
                                       'recommendation': ''}]},
                           {'name': 'PLANEJAMENTO EXECUÇÃO',
                            'items': [{'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.1',
                                       'text': 'Todo trabalho em altura deve ser supervisionado.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.2',
                                       'text': 'Precedido de uma Análise Preliminar de Risco (APR), que deve '
                                               'considerar, conforme item da NR35 35.5.5.1:\n'
                                               'a) O local em que os serviços serão executados e seu entorno; \n'
                                               'b) O isolamento e a sinalização no entorno da área de trabalho; '
                                               'Definição dos pontos de ancoragem;\n'
                                               'c) O estabelecimento dos sistemas e pontos de ancoragem;\n'
                                               'd) as condições meteorológicas adversas; Isolamento e sinalização;\n'
                                               'e) a seleção, inspeção, forma de utilização e limitação de uso dos '
                                               'sistemas de proteção coletiva e individual, atendendo às normas '
                                               'técnicas vigentes, às orientações do fabricante ou projetista e aos '
                                               'princípios da redução do impacto e dos fatores de queda; \n'
                                               'f) os trabalhos simultâneos que apresentem riscos específicos;\n'
                                               'g) Planejamento para situações de emergência;\n'
                                               'h) o atendimento aos requisitos de segurança e saúde contidos nas '
                                               'demais normas regulamentadoras;\n'
                                               'i) os riscos adicionais;\n'
                                               'j) as condições impeditivas;\n'
                                               'k) as situações de emergência e o planejamento do resgate e primeiros '
                                               'socorros, de forma a reduzir o tempo da suspensão inerte do '
                                               'trabalhador;\n'
                                               'l) a necessidade de sistema de comunicação; e\n'
                                               'm) a forma da supervisão.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.3',
                                       'text': 'As medidas de controle das atividade de trabalho em altura não '
                                               'rotineiras devem ser evidenciadas na Análise Preliminar de Risco e na '
                                               'Permissão de Trabalho;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.4',
                                       'text': 'Precedido de uma inspeção de pré-uso (checklist) de todos os EPIs, '
                                               'ferramentas e equipamentos, inclusive PEMTs que serão utilizados. No '
                                               'checklist de inspeção devem ser indicadas as condições impeditivas '
                                               'para a sua utilização, os itens não conformes devem ser imediatamente '
                                               'substituídos.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.5',
                                       'text': 'Nas atividades rotineiras de trabalho em altura que possuam '
                                               'procedimento operacional, a análise de risco pode estar inserida '
                                               'neste, no entanto, qualquer alteração em relação às condições e '
                                               'cenários considerados no procedimento, este fica invalidado e deve ser '
                                               'realizada nova análise de risco e emissão de Permissão de Trabalho',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.6',
                                       'text': 'O procedimento operacional das atividades rotineiras de trabalho em '
                                               'altura devem conter, no mínimo, conforme item 35.5.6.1:\n'
                                               'a) o detalhamento da tarefa;\n'
                                               'b) as medidas de prevenção características à rotina; \n'
                                               'c) as condições impeditivas; \n'
                                               'd) Medidas de controle dos riscos características à rotina;\n'
                                               'e) os sistemas de proteção coletiva e individual necessários e;\n'
                                               'f) competências e responsabilidades.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.7',
                                       'text': 'As atividades não rotineiras de trabalhos em altura ou rotineiras que '
                                               'não possuam procedimento operacional devem: ser previamente '
                                               'autorizadas por uma Permissão de Trabalho, aprovada pelo responsável, '
                                               'disponibilizada no local de execução da atividade e, ao final, '
                                               'encerrada e arquivada de forma a permitir sua rastreabilidade;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '1. DOCUMENTAÇÃO',
                                       'number': '1.8',
                                       'text': 'Todos os executores da atividade devem participar na elaboração da '
                                               'Análise Preliminar de Risco e da Permissão de Trabalho, que deve  ser '
                                               'realizada no local de execução da atividade;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. PRÉ-OPERAÇÃO',
                                       'number': '2.1',
                                       'text': 'Precedido por verificação se isolamento e sinalização estão '
                                               'implantados conforme definido na Análise de Riscos e/ou Permissão de '
                                               'Trabalho ou no procedimento operacional;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. PRÉ-OPERAÇÃO',
                                       'number': '2.2',
                                       'text': 'Precedido da medição / verificação da pressão arterial de todos os '
                                               'executores do trabalho em altura',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. PRÉ-OPERAÇÃO',
                                       'number': '2.3',
                                       'text': 'A Permissão de Trabalho deve conter:\n'
                                               'a)\tRequisitos mínimos a serem atendidos para a execução dos '
                                               'trabalhos;\n'
                                               'b)\tDisposições e medidas estabelecidas na Análise Preliminar de '
                                               'Risco;\n'
                                               'c)\tRelação de todos os envolvidos e suas autorizações.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '2. PRÉ-OPERAÇÃO',
                                       'number': '2.4',
                                       'text': 'A Permissão de Trabalho deve ter validade limitada à duração da '
                                               'atividade, restrita ao turno de trabalho, podendo ser revalidada pelo '
                                               'responsável pela aprovação nas situações em que não ocorram mudanças '
                                               'nas condições estabelecidas ou na equipe de execução.',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '3. MANUTENÇÃO',
                                       'number': '3.1',
                                       'text': 'Para PEMTs, em adição: confirmação formal do cumprimento do plano de '
                                               'manutenção preventiva, realizado por profissional legalmente '
                                               'habilitado ou profissional qualificado, conforme disposto no item '
                                               '12.11 da NR-12;',
                                       'requirement': '',
                                       'recommendation': ''},
                                      {'section': '3. MANUTENÇÃO',
                                       'number': '3.2',
                                       'text': 'Não se deve permitir alterações ou modificações que alterem as '
                                               'condições originais dos equipamentos/estruturas, exceto mediante '
                                               'informação técnica do fabricante ou de um profissional habilitado, com '
                                               'as devidas justificativas e controles de alteração.',
                                       'requirement': '',
                                       'recommendation': ''}]}],
                'item_count': 67},
 'rac_confined': {'title': 'RAC — Espaço Confinado',
                  'short': 'Espaço Confinado',
                  'icon': 'mi-confined',
                  'prefix': 'RAC-EC',
                  'revision': 'Rev. 1\nMaio/2023',
                  'source_file': 'Espaço confinado.xlsx',
                  'response_mode': 'atende',
                  'groups': [{'name': 'PESSOAS',
                              'items': [{'section': '1. SAÚDE',
                                         'number': '1.1',
                                         'text': 'Os exames ocupacionais vigentes para comprovar a aptidão para '
                                                 'realizar trabalhos em espaços confinados o Atestado de Saúde '
                                                 'Ocupacional (ASO) estão válidos e aprovados, a aptidão está\n'
                                                 'esta mencionada por escrito na ASO?',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. SAÚDE',
                                         'number': '1.2',
                                         'text': 'Os ASOs para trabalhos em espaços confinados inclui, em adição ao '
                                                 'exame clínico básico, os seguintes exames complementares: acuidade '
                                                 'visual, audiometria ocupacional, eletroencefalograma, '
                                                 'eletrocardiograma, glicemia em jejum, hemograma completo, '
                                                 'espirometria e avaliação psicológica?',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. SAÚDE',
                                         'number': '1.3',
                                         'text': 'Os exames ocupacionais e a sistemática de avaliação fazem parte do '
                                                 'PGR (Plano de Gerenciamento de Riscos) e PCMSO (Plano de Controle '
                                                 'Médio de Saúde Ocupacional), conforme NR-1 e NR-7?',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. SAÚDE',
                                         'number': '1.4',
                                         'text': 'A avaliação dos exames ocupacionais, a definição da a aptidão para '
                                                 'realizar atividades que envolvam trabalho em espaço confinado e a '
                                                 'emissão do Atestado de Saúde Ocupacional (ASO) são realizadas por '
                                                 'médico do trabalho habilitado?',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. CAPACITAÇÃO',
                                         'number': '2.1',
                                         'text': 'Os trabalhadores envolvidos nas atividades em espaço confinado: '
                                                 'supervisores de entrada, vigias e executores, e a equipe de '
                                                 'emergência e resgate devem realizar e serem aprovados nas '
                                                 'capacitações inicial, periódica e eventual, com conteúdo, carga '
                                                 'horária e periodicidade definidos no Anexo III da NR-33.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. CAPACITAÇÃO',
                                         'number': '2.2',
                                         'text': 'A capacitação deve considerar o tipo de espaço confinado e as '
                                                 'atividades desenvolvidas, devendo estas informações e a anuência do '
                                                 'responsável técnico previsto no item 33.3.2 desta NR constarem no '
                                                 'certificado do trabalhador, além do disposto na NR-01.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. CAPACITAÇÃO',
                                         'number': '2.3',
                                         'text': 'Os treinamentos devem ser avaliados de modo a aferir os '
                                                 'conhecimentos adquiridos pelos trabalhadores.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. CAPACITAÇÃO',
                                         'number': '2.4',
                                         'text': 'Os instrutores devem possuir comprovada proficiência no conteúdo que '
                                                 'irão ministrar.',
                                         'requirement': '',
                                         'recommendation': ''}]},
                             {'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                              'items': [{'section': '1. INSTALAÇÕES',
                                         'number': '1.1',
                                         'text': 'Deve ser mantida sinalização permanente em todos os espaços '
                                                 'confinados, junto à entrada, conforme modelo constante do Anexo I da '
                                                 'NR33',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. INSTALAÇÕES',
                                         'number': '1.2',
                                         'text': 'Caso a sinalização permanente não se torne visível após a abertura '
                                                 'do espaço confinado, deve ser providenciada sinalização '
                                                 'complementar, conforme modelo do Anexo I da NR-33.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. INSTALAÇÕES',
                                         'number': '1.3',
                                         'text': 'Em locais com exposição a agentes agressivos ou circulação de '
                                                 'pessoas, veículos ou equipamentos, a sinalização permanente deve ser '
                                                 'indelével, de forma a garantir que não seja danificada ou retirada.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. INSTALAÇÕES',
                                         'number': '1.4',
                                         'text': 'A organização que possuir espaço confinado deve elaborar e manter o '
                                                 'cadastro do espaço confinado, contemplando:\n'
                                                 'a) identificação do espaço confinado, podendo para esse fim, ser '
                                                 'utilizado código ou número\n'
                                                 'de rastreio;\n'
                                                 'b) volume do espaço confinado;\n'
                                                 'c) número de aberturas de entrada e "bocas de visita", e suas '
                                                 'dimensões;\n'
                                                 'd) formas de acesso, suas dimensões e geometria;\n'
                                                 'e) condição do espaço confinado (ativo ou inativo);\n'
                                                 'f) croqui do espaço confinado (com previsão de bloqueios e '
                                                 'raquetes); e\n'
                                                 'g) utilização e/ou produto armazenado e indicação dos possíveis '
                                                 'perigos existentes antes da\n'
                                                 'liberação de entrada.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. EQUIPAMENTOS DE ACESSOS E TRABALHOS',
                                         'number': '2.1',
                                         'text': 'Em áreas classificadas, os equipamentos elétricos e eletrônicos '
                                                 'devem estar certificados ou possuir documento contemplado no âmbito '
                                                 'do Sistema Nacional de Metrologia, Normalização e Qualidade '
                                                 'Industrial - Sinmetro.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. EQUIPAMENTOS DE ACESSOS E TRABALHOS',
                                         'number': '2.2',
                                         'text': 'Os equipamentos utilizados para avaliações atmosféricas devem:\n'
                                                 'a) atender o disposto nas normas técnicas nacionais ou, na sua '
                                                 'ausência, normas técnicas \n'
                                                 'internacionais aplicáveis;\n'
                                                 'b) efetuar leitura instantânea;\n'
                                                 'c) ser intrinsecamente seguro,\n'
                                                 'd) ser protegido contra interferências eletromagnéticas de '
                                                 'radiofrequência, devendo suportar \n'
                                                 'campo de 10 V/m (dez Volts por metro);\n'
                                                 'e) possuir alarme sonoro, visual e vibratório, acionados '
                                                 'simultaneamente;\n'
                                                 'f) possuir grau de proteção contra o ingresso de poeira e água '
                                                 'adequado; e\n'
                                                 'g) possuir manual em português.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. EQUIPAMENTOS DE ACESSOS E TRABALHOS',
                                         'number': '2.3',
                                         'text': 'O auto-zero ou ajuste de ar limpo e o teste de resposta do '
                                                 'equipamento de avaliação, quando utilizados, devem ser realizados '
                                                 'diariamente antes do início das avaliações.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. EQUIPAMENTOS DE ACESSOS E TRABALHOS',
                                         'number': '2.4',
                                         'text': 'Durante a realização da atividade em espaço confinado, devem ser '
                                                 'atendidos os seguintes requisitos:\n'
                                                 'a) o sistema de ventilação deve ser selecionado e dimensionado de '
                                                 'acordo com as características dos espaços confinados, observando as '
                                                 'recomendações previstas em normas técnicas nacionais ou, de forma '
                                                 'complementar, as normas internacionais aplicáveis, a fim de garantir '
                                                 'a renovação do ar;',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. EQUIPAMENTOS DE ACESSOS E TRABALHOS',
                                         'number': '2.5',
                                         'text': 'Durante a realização da atividade em espaço confinado, devem ser '
                                                 'atendidos os seguintes requisitos:\n'
                                                 'e b) as condições térmicas devem observar o disposto no Anexo III da '
                                                 'NR-09.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': "3. EPI's",
                                         'number': '3.1',
                                         'text': 'Os EPIs para proteção contra queda em trabalhos em espaços '
                                                 'confinados, devem ser:\n'
                                                 '- Certificados, ou seja, com CA e atendendo às normas aplicáveis;\n'
                                                 '- Adequados para a utilização pretendida;\n'
                                                 '- Utilizados considerando os limites de uso;\n'
                                                 '- Ajustados ao peso e à altura do trabalhador.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': "3. EPI's",
                                         'number': '3.2',
                                         'text': 'Os sistemas de ancoragem devem ser:\n'
                                                 '- Instalados por trabalhadores capacitados;\n'
                                                 '- Submetidos à inspeção inicial e periódica;',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': "3. EPI's",
                                         'number': '3.3',
                                         'text': 'Sistema de ancoragem temporário deve:\n'
                                                 '- Atender os requisitos de compatibilidade a cada local de '
                                                 'instalação conforme procedimento operacional;\n'
                                                 '- Ter os pontos de fixação definidos sob responsabilidade de '
                                                 'profissional legalmente habilitado.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': "3. EPI's",
                                         'number': '3.4',
                                         'text': "Para trabalhos em espaços confinados ''úmidos'', adicionalmente aso "
                                                 "EPI's básicos e para trabalho em altura, deve-se disponibilizar bota "
                                                 'impermeável e/ou vestimenta impermeável.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': "3. EPI's",
                                         'number': '3.5',
                                         'text': 'Uma inspeção de pré-uso (checklist) de todos os EPIs, ferramentas e '
                                                 'equipamentos. No checklist de inspeção devem ser indicadas as '
                                                 'condições impeditivas para a sua utilização, os itens não conformes '
                                                 'devem ser imediatamente substituídos.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.1',
                                         'text': 'Tripé para resgate onde aplicável',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.2',
                                         'text': 'Talabarte retrátil, onde aplicável, de acordo com o espaço '
                                                 'confinado, procedimento e análise de risco.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.3',
                                         'text': 'Instalação de pontos de ancoragens temporários, de acordo com a '
                                                 'especificidade do espaço confinado',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.4',
                                         'text': 'Lanternas de capacete intrinsecamente seguras',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.5',
                                         'text': '1 par de sistema de cilindro autônomo',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.6',
                                         'text': 'Guincho de resgate',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.7',
                                         'text': 'Trapézio de resgate vertical',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.8',
                                         'text': 'Linha de vida back up com trava quedas tipo corda e mosquestão',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.9',
                                         'text': 'Cintas de amarração e ancoragem com quebra quinas',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '4. EQUIPAMENTOS PARA RESGATE',
                                         'number': '4.10',
                                         'text': 'Maca envelope',
                                         'requirement': '',
                                         'recommendation': ''}]},
                             {'name': 'PLANEJAMENTO EXECUÇÃO',
                              'items': [{'section': '1. DOCUMENTAÇÃO',
                                         'number': '1.1',
                                         'text': 'A organização que possui espaços confinados deve manter no '
                                                 'estabelecimento: a) cadastro dos espaços confinados; b) PETs '
                                                 'emitidas; e c) inventário de riscos do trabalho em espaço confinado '
                                                 'realizado pela contratada, quando aplicável.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. DOCUMENTAÇÃO',
                                         'number': '1.2',
                                         'text': 'A organização que realiza trabalho em espaços confinados deve manter '
                                                 'os seguintes documentos: a) modelo de PET; b) procedimentos de '
                                                 'segurança; e c) plano de resgate.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. DOCUMENTAÇÃO',
                                         'number': '1.3',
                                         'text': 'O plano de resgate deve ser elaborado pela organização que realiza '
                                                 'trabalho em espaço confinado e deve estar articulado com o plano de '
                                                 'atendimento de emergência da organização que possui espaço '
                                                 'confinado.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. DOCUMENTAÇÃO',
                                         'number': '1.4',
                                         'text': 'O plano de resgate deve conter: a) identificação dos perigos '
                                                 'associados à operação de resgate; b) designação da equipe de '
                                                 'emergência e salvamento, interna ou externa, dimensionada conforme a '
                                                 'geometria, acessos e riscos das atividades e operação de resgate; c) '
                                                 'tempo de resposta para atendimento à emergência; d) seleção das '
                                                 'técnicas apropriadas, equipamentos pessoais e/ou coletivos '
                                                 'específicos e sistema de resgate disponíveis, de forma a reduzir o '
                                                 'tempo de suspensão inerte do trabalhador e sua exposição aos perigos '
                                                 'existentes; e e) previsão da realização de simulados dos cenários '
                                                 'identificados.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. DOCUMENTAÇÃO',
                                         'number': '1.5',
                                         'text': 'O modelo de PET a ser adotado pela organização deve ser adaptado de '
                                                 'modo a contemplar as peculiaridades dos espaços confinados da '
                                                 'organização tendo como referência o Anexo II desta NR.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '1. DOCUMENTAÇÃO',
                                         'number': '1.6',
                                         'text': 'A organização deve possuir uma análise de perigos e riscos '
                                                 'específicas para espaço confinado, contemplando:\n'
                                                 'a) os perigos existentes nas adjacências do espaço confinado que '
                                                 'possam interferir nas\n'
                                                 'condições de segurança do trabalho em espaço confinado; \n'
                                                 'b) a possibilidade de formação de atmosferas perigosas;\n'
                                                 'c) a necessidade de controle de energias perigosas nos espaços '
                                                 'confinados; e\n'
                                                 'd) as demais medidas de prevenção descritas nesta NR.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. COMPETÊNCIAS',
                                         'number': '2.1',
                                         'text': 'Compete ao responsável técnico: a) identificar e elaborar o cadastro '
                                                 'de espaços confinados; b) adaptar o modelo da Permissão de Entrada e '
                                                 'Trabalho - PET de modo a contemplar as peculiaridades dos espaços '
                                                 'confinados da organização; c) elaborar os procedimentos de segurança '
                                                 'relacionados ao espaço confinado; d) indicar os equipamentos para '
                                                 'trabalho em espaços confinados; e) elaborar o plano de resgate; e f) '
                                                 'coordenar a capacitação inicial e periódica dos supervisores de '
                                                 'entrada, vigias, trabalhadores autorizados e da equipe de emergência '
                                                 'e salvamento.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. COMPETÊNCIAS',
                                         'number': '2.2',
                                         'text': 'Compete ao supervisor de entrada: a) emitir a PET antes do início '
                                                 'das atividades; b) executar os testes e conferir os equipamentos, '
                                                 'antes da utilização; c) implementar os procedimentos contidos na '
                                                 'PET; d) assegurar que os serviços de emergência e salvamento estejam '
                                                 'disponíveis e que os meios para os acionar estejam operantes; e) '
                                                 'cancelar os procedimentos de entrada e trabalho, quando necessário; '
                                                 'f) encerrar a PET após o término dos serviços; g) desempenhar a '
                                                 'função de vigia, quando previsto na PET; e h) assegurar que o vigia '
                                                 'esteja operante durante a realização dos trabalhos em espaço '
                                                 'confinado.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. COMPETÊNCIAS',
                                         'number': '2.3',
                                         'text': 'Compete ao vigia: a) permitir somente a entrada de trabalhadores '
                                                 'autorizados em espaços confinados relacionados na PET;\n'
                                                 'b) manter continuamente o controle do número de trabalhadores '
                                                 'autorizados a entrar no\n'
                                                 'espaço confinado e assegurar que todos saiam ao término da '
                                                 'atividade;\n'
                                                 'c) permanecer fora do espaço confinado, junto à entrada, em contato '
                                                 'ou comunicação\n'
                                                 'permanente com os trabalhadores autorizados;\n'
                                                 'd) acionar a equipe de emergência e salvamento, interna ou externa, '
                                                 'quando necessário;\n'
                                                 'e) operar os movimentadores de pessoas;\n'
                                                 'f) ordenar o abandono do espaço confinado sempre que reconhecer '
                                                 'algum sinal de alarme,\n'
                                                 'perigo, sintoma, queixa, condição proibida, acidente, situação não '
                                                 'prevista ou quando não\n'
                                                 'puder desempenhar efetivamente suas tarefas, nem ser substituído por '
                                                 'outro vigia;\n'
                                                 'g) não realizar outras tarefas durante as operações em espaços '
                                                 'confinados; e\n'
                                                 'h) comunicar ao supervisor de entrada qualquer evento não previsto '
                                                 'ou estranho à operação\n'
                                                 'de vigilância, inclusive quando da ordenação do abandono.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. COMPETÊNCIAS',
                                         'number': '2.4',
                                         'text': 'O vigia pode acompanhar as atividades de mais de um espaço '
                                                 'confinado, quando atendidos os seguintes requisitos: a) permanecer '
                                                 'junto à entrada dos espaços confinados ou nas suas proximidades, '
                                                 'podendo ser assistido por sistema de vigilância e comunicação '
                                                 'eletrônicas; b) que todos os espaços confinados estejam no seu campo '
                                                 'visual, sem o uso de equipamentos eletrônicos; c) que o número de '
                                                 'espaços confinados não prejudique suas funções de vigia; d) que a '
                                                 'mesma atividade seja executada em todos os espaços confinados sob '
                                                 'sua responsabilidade; e) seja limitada a permanência de 2 (dois) '
                                                 'trabalhadores no interior de cada espaço confinado; e f) seja '
                                                 'possível a visualização dos trabalhadores através do acesso do '
                                                 'espaço confinado.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. COMPETÊNCIAS',
                                         'number': '2.5',
                                         'text': 'Compete aos trabalhadores autorizados: a) cumprir as orientações '
                                                 'recebidas nos treinamentos e os procedimentos de trabalho previstos '
                                                 'na PET; b) utilizar adequadamente os meios e equipamentos fornecidos '
                                                 'pela organização; e c) comunicar ao vigia ou supervisor de entrada '
                                                 'as situações de risco para segurança e saúde dos trabalhadores e '
                                                 'terceiros, que sejam do seu conhecimento.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '2. COMPETÊNCIAS',
                                         'number': '2.6',
                                         'text': 'Compete à equipe de emergência e salvamento: a) assegurar que as '
                                                 'medidas de salvamento e primeiros socorros estejam operantes e '
                                                 'executálas em caso de emergência; e b) participar do exercício de '
                                                 'simulado anual de salvamento que contemple os possíveis cenários de '
                                                 'acidentes em espaços confinados, conforme previsto no plano de '
                                                 'resgate.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '3. EXECUÇÃO',
                                         'number': '3.1',
                                         'text': 'Antes de adentrar no espaço confinado deve-se realizar as '
                                                 'verificações de medição da atmosfera e monitoramento durante as '
                                                 'atividades',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '3. EXECUÇÃO',
                                         'number': '3.2',
                                         'text': 'Definição dos sistema de comunição de acordo com a PET',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '3. EXECUÇÃO',
                                         'number': '3.3',
                                         'text': 'Verificação e aplicação de bloqueio e etiquetagem',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '3. EXECUÇÃO',
                                         'number': '3.4',
                                         'text': 'Para atividades em condutos realizar inspeção prévia para '
                                                 'verificação sujidade que interfira na execução dos trabalhos. Caso '
                                                 'haja sujidade suficiente, deve-se realizar limpeza.',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '3. EXECUÇÃO',
                                         'number': '3.5',
                                         'text': 'É mantida periodicamente a comunicação com o vigia do espaço '
                                                 'confinado e executores',
                                         'requirement': '',
                                         'recommendation': ''},
                                        {'section': '3. EXECUÇÃO',
                                         'number': '3.6',
                                         'text': 'Sistema de iluminação para trabalho extra baixa tensão - 24Vcc',
                                         'requirement': '',
                                         'recommendation': ''}]}],
                  'item_count': 50},
 'rac_electrical': {'title': 'RAC — Trabalho com Eletricidade',
                    'short': 'Trabalho com Eletricidade',
                    'icon': 'mi-zap',
                    'prefix': 'RAC-EL',
                    'revision': 'Rev. 1\nMai/2023',
                    'source_file': 'Trabalho com eletricidade.xlsx',
                    'response_mode': 'atende',
                    'groups': [{'name': 'PESSOAS',
                                'items': [{'section': '1. SAÚDE',
                                           'number': '1.1',
                                           'text': 'Os exames ocupacionais vigentes para comprovar a aptidão para '
                                                   'realizar trabalho estas atividades e o Atestado de Saúde '
                                                   'Ocupacional (ASO) válidos',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. SAÚDE',
                                           'number': '1.2',
                                           'text': 'A ASO para trabalhos com eletricidade, em adição ao exame clínico '
                                                   'básico, deve incluir os seguintes exames complementares: acuidade '
                                                   'visual, eletroencefalograma, eletrocardiograma, glicemia em jejum; '
                                                   'hemograma\n'
                                                   'completo e espirometria.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. SAÚDE',
                                           'number': '1.3',
                                           'text': 'Os exames ocupacionais e a sistemática de avaliação devem ser '
                                                   'partes integrantes do PGR (Plano de Gerenciamento de Riscos), e '
                                                   'PCMSO (Plano de\n'
                                                   'Controle Médio de Saúde Ocupacional, conforme NR-1 e NR-7, da '
                                                   'Omega Energia, empresas contratadas e subcontratadas.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. SAÚDE',
                                           'number': '1.4',
                                           'text': 'A avaliação dos exames ocupacionais, a definição da aptidão para '
                                                   'realizar atividades em instalações elétricas e a emissão do '
                                                   'Atestado de Saúde Ocupacional (ASO) devem ser realizadas por '
                                                   'médico do trabalho habilitado.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.1',
                                           'text': 'Os executores das atividades em instalações elétricas devem ser '
                                                   'capacitados e aprovados nos seguintes treinamentos com carga '
                                                   'individual de 40 horas, com reciclagem a cada 2 anos, e conteúdo '
                                                   'programático definido no Anexo III, da NR-10, a saber:\n'
                                                   '- Básico: Segurança em instalações e serviços com eletricidade;\n'
                                                   '- Complementar: Segurança no sistema elétrico de potência (SEP) e '
                                                   'suas proximidades.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.2',
                                           'text': 'Para os executores de atividades em instalações energizadas é '
                                                   'obrigatório, que em adição aos treinamentos básico e complementar, '
                                                   'sejam capacitados em treinamentos específicos para trabalho em '
                                                   'linhas vivas AT, ministrados por\n'
                                                   'empresas capacitadas e que atendam aos requisitos da SEPRT '
                                                   '(Secretaria Especial de Previdência e Trabalho).               '
                                                   'Obs.: A capacitação é válida apenas para a empresa que o capacitou '
                                                   'e nas condições estabelecidas pelo profissional habilitado e '
                                                   'autorizado responsável pela capacitação.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.3',
                                           'text': 'Os executores das atividades em instalações elétricas devem '
                                                   'possuir anuência formal da empresa.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.4',
                                           'text': 'As atividades em instalações elétricas podem envolver trabalho em '
                                                   'altura, içamento de cargas e/ou espaço confiando, logo os '
                                                   'executores devem, em adição, serem capcitados e habilitados para '
                                                   'estas atividades.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.5',
                                           'text': 'As empresas contratadas e subcontratadas que executam trabalhos '
                                                   'com eletricidade devem designar um responsável técnico devidamente '
                                                   'qualificado e habilitado',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.6',
                                           'text': 'Os executores serão considerados habilitados e liberados para as '
                                                   'atividades apenas se todas as capacitações e habilitações exigidas '
                                                   'estiverem válidas, inseridas no SGF e aprovadas.',
                                           'requirement': '',
                                           'recommendation': ''}]},
                               {'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                                'items': [{'section': '1. INSTALAÇÕES',
                                           'number': '1.1',
                                           'text': 'As instalações elétricas devem possuir sinalização de advertência '
                                                   'e protegidas fisicamente para evitar o acesso de pessoas não '
                                                   'autorizadas.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. INSTALAÇÕES',
                                           'number': '1.2',
                                           'text': 'As instalações devem ser mantidas em condições seguras de '
                                                   'funcionamento e seus sistemas de\n'
                                                   'proteção devem ser inspecionados e controlados periodicamente, de\n'
                                                   'acordo com as regulamentações existentes e especificações do '
                                                   'projeto;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. INSTALAÇÕES',
                                           'number': '1.3',
                                           'text': 'As instalações devem possuir dispositivos de desligamento de '
                                                   'circuitos e impedimento de reenergização;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. INSTALAÇÕES',
                                           'number': '1.4',
                                           'text': 'As instalações devem estar protegidas contra cargas transitórias;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. INSTALAÇÕES',
                                           'number': '1.5',
                                           'text': 'As instalações devem estar aterradas e/ou apresentar condições de '
                                                   'adoção de aterramento temporário',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. INSTALAÇÕES',
                                           'number': '1.6',
                                           'text': 'Os equipamentos, dispositivos e ferramentas que possuam isolamento '
                                                   'elétrico devem estar adequados às tensões envolvidas, e serem '
                                                   'inspecionados e testados de acordo com as regulamentações '
                                                   'existentes ou recomendações\n'
                                                   'dos fabricantes.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. INSTALAÇÕES',
                                           'number': '1.7',
                                           'text': 'Os equipamentos, ferramentas e dispositivos isolantes ou equipados '
                                                   'com materiais isolantes, destinados ao trabalho em alta tensão, '
                                                   'devem ser submetidos a testes elétricos ou ensaios de laboratório '
                                                   'periódicos, obedecendo-se as especificações do fabricante, os '
                                                   'procedimentos da empresa e na ausência desses, no mínimo, '
                                                   'anualmente.           Sendo, dentre outros, tapetes e estrados '
                                                   'isolantes, vara de manobra, vara telescópica, loadbuster, bastão '
                                                   'de salvamento, ferramentas, manta isolante.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. EPIs / EPCs',
                                           'number': '2.1',
                                           'text': 'Os EPIs e EPCs para execução de trabalhos em instalações elétricas '
                                                   'devem ser certificados, ou seja, com CA e atendendo às normas '
                                                   'aplicáveis;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. EPIs / EPCs',
                                           'number': '2.2',
                                           'text': 'Os EPIs e EPCs devem estar adequados para a utilização '
                                                   'pretendida:\n'
                                                   '- nível de tensão;\n'
                                                   '- nível / classe de isolamento requerida;\n'
                                                   '- instalação não energizada;\n'
                                                   '- instalação energizada (método ao contado/isolado ou ao '
                                                   'potencial).',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. EPIs / EPCs',
                                           'number': '2.3',
                                           'text': 'As vestimentas de trabalho devem ser adequadas às atividades, '
                                                   'devendo contemplar a condutibilidade, inflamabilidade e '
                                                   'influências eletromagnéticas.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. EPIs / EPCs',
                                           'number': '2.4',
                                           'text': 'As vestimentas para trabalho em linha viva método ao potencial '
                                                   'devem atender aos requisitos da NBR 16135.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. EPIs / EPCs',
                                           'number': '2.5',
                                           'text': 'Os EPIs e EPCs com materiais isolantes, destinados ao trabalho em '
                                                   'alta tensão, devem ser submetidos a testes elétricos ou ensaios de '
                                                   'laboratório periódicos, obedecendo-se as especificações do '
                                                   'fabricante, os procedimentos da empresa e na ausência desses, no '
                                                   'mínimo, anualmente.\n'
                                                   'Na análise de risco prévia, dependendo das condições observadas '
                                                   'dos EPIs ou EPCs (condições físicas, laudos últimos testes '
                                                   'elétricos), pode ser definido pela realização de novos testes '
                                                   'elétricos ou substituição por novos.\n'
                                                   'Sendo, dentre outros, luva isolante de borracha, banqueta isolada, '
                                                   'manga isolante de borracha, manta isolante, bota isolante.',
                                           'requirement': '',
                                           'recommendation': ''}]},
                               {'name': 'PLANEJAMENTO EXECUÇÃO',
                                'items': [{'section': '1. REQUISITOS GERAIS',
                                           'number': '1.1',
                                           'text': 'Todo trabalho em instalações elétricas deve ser planejado, '
                                                   'organizado e executado por pessoas / equipes capacitadas e '
                                                   'autorizadas – vide item 3.1;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. REQUISITOS GERAIS',
                                           'number': '1.2',
                                           'text': 'Precedido de uma Análise de Risco, que deve '
                                                   'considerar:               a) Riscos inerentes à atividade '
                                                   '(depedendo poderá envolver trabalho em altura, içamento de cargas '
                                                   'e/ou espaço confiando);\n'
                                                   'b) A localização e as interfências no entorno, inclusive outros '
                                                   'serviços que estiverem sendo executados;\n'
                                                   'c) As manobras de isolação e normalização envolvidas;\n'
                                                   'd) Instalação desenergizada: formas de bloqueio / isolação '
                                                   'elétrica\n'
                                                   'Instalação energizadas: método empregaddo e controles adicionais;\n'
                                                   'e) Isolamento físico e sinalização da área;\n'
                                                   'f) Sistema de comunicação necessários;\n'
                                                   'g) EPIs aplicáveis;\n'
                                                   'h) Condições impeditivas, inclusive condições meteorológicas '
                                                   'adversas;\n'
                                                   'i) A forma da supervisão;\n'
                                                   'j) Planejamento situações de emergência.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. REQUISITOS GERAIS',
                                           'number': '1.3',
                                           'text': 'Ser autorizado por uma Permissão de Trabalho, aprovada pelo '
                                                   'responsável, disponibilizada no local de execução da atividade e, '
                                                   'ao final, encerrada e arquivada de forma a permitir sua '
                                                   'rastreabilidade;\n'
                                                   'Obs.: Todos os executores dos trabalhos nas instalações elétricas '
                                                   'devem participar na elaboração da Análise de Risco e da Permissão '
                                                   'de Trabalho, que deve ser realizada no local de execução da '
                                                   'atividade;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. REQUISITOS GERAIS',
                                           'number': '1.4',
                                           'text': 'Precedido por verificação se isolamento físico e a sinalização da '
                                                   'área estão implantados conforme definido na Análise de Riscos e/ou '
                                                   'na Permissão de Trabalho;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.1',
                                           'text': 'Realizar a isolação e normalização do sistema / equipamento '
                                                   'conforme definido no procedimento formal de sequência de manobras.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.2',
                                           'text': 'Realizar o bloqueio de energia conforme definido em procedimento '
                                                   'formal, sempre que possível utilizar sistema com cadeado e '
                                                   'etiqueta de boqueio.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.3',
                                           'text': 'Caso as manobras envolvidas não possuam procedimento formal de '
                                                   'sequência de manobras, este deve ser desenvolvido pela empresa '
                                                   'responsável pela operação e manutenção, coordenada por '
                                                   'profissional legalmente habilitado e autorizado, e submetida à '
                                                   'aprovação da operação e manutenção da Omega Energia.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.4',
                                           'text': 'O procedimento de sequencia de manobras deve ser específico por '
                                                   'manobra (isolação e normalização) e sistema / equipamento e '
                                                   'conter, no mínimo:                                      a) '
                                                   'Requisitos de segurança: análise de risco, EPIs, isolamento;\n'
                                                   'b) Equipamentos e documentos necessários à execução da atividade;\n'
                                                   'c) Detalhamento (passo a passo) do sequenciamento das manobras;\n'
                                                   'd) Responsabilidades.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.5',
                                           'text': 'São consideradas desenergizadas e, portanto, liberadas para '
                                                   'trabalhos, as instalações elétricas em que tenham sido os '
                                                   'realizados os seguintes procedimentos e respeitando a sequência:\n'
                                                   'a) Isolação (seccionamento);\n'
                                                   'b) Impedimento de reenergização;\n'
                                                   'c) Constatação da ausência de tensão;\n'
                                                   'd) Instalação de aterramento temporário com equipotencialização '
                                                   'dos condutores dos circuitos;\n'
                                                   'e) Proteção dos elementos energizados existentes na zona '
                                                   'controlada (entorno de parte condutora energizada, não segregada, '
                                                   'acessível, de dimensões estabelecidas de acordo com o nível de '
                                                   'tensão, cuja aproximação só é permitida a profissionais '
                                                   'autorizados), se aplicável;\n'
                                                   'f) Instalação da sinalização de impedimento de reenergização',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.6',
                                           'text': 'O estado de instalação desenergizada deve ser mantido até a '
                                                   'autorização para reenergização, devendo ser reenergizada '
                                                   'respeitando a sequência de procedimentos abaixo:\n'
                                                   'a) Retirada das ferramentas, utensílios e equipamentos;\n'
                                                   'b) Retirada da zona controlada de todos os trabalhadores não '
                                                   'envolvidos no processo de reenergização;\n'
                                                   'c) Remoção do aterramento temporário, da equipotencialização e das '
                                                   'proteções adicionais;\n'
                                                   'd) Remoção da sinalização de impedimento de reenergização;\n'
                                                   'e) Destravamento, se houver, e religação dos dispositivos de '
                                                   'seccionamento.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS '
                                                      'DESENERGIZADAS',
                                           'number': '2.7',
                                           'text': 'Nos serviços em instalações elétricas desligadas, mas com\n'
                                                   'possibilidade de energização, por qualquer meio ou razão, devem '
                                                   'atender aos requisitos estabelecidos para instalações elétricas '
                                                   'energizadas.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS ENERGIZADAS',
                                           'number': '3.1',
                                           'text': 'Quando não for possível a desenergizar a instalação elétrica, '
                                                   'podem ser adotadas proteções coletivas, como: isolação das partes '
                                                   'vivas, obstáculos, barreiras e sinalização.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS ENERGIZADAS',
                                           'number': '3.2',
                                           'text': 'Os trabalhos em instalações elétricas em que seja necessário '
                                                   'acessar / ingressar na zona controlada ou risco devem ser '
                                                   'realizados mediante procedimentos específicos e respeitando as '
                                                   'distâncias previstas no Anexo II da NR-10, que apresenta as '
                                                   'distâncias radiais das zonas de risco, controlada e livre em '
                                                   'função da faixa de tensão nominal da\n'
                                                   'instalação elétrica, sendo que:\n'
                                                   'a) Zona controlada - acesso permitido apenas a profissionais '
                                                   'autorizados;\n'
                                                   'b) Zona de risco - acesso permitido apenas a profissionais '
                                                   'autorizados e com a adoção de técnicas e instrumentos apropriados '
                                                   'de trabalho.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS ENERGIZADAS',
                                           'number': '3.3',
                                           'text': 'Os serviços executados em instalações elétricas energizadas em AT '
                                                   'e no Sistema Elétrico de Potência - SEP, não podem ser realizados '
                                                   'individualmente.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS ENERGIZADAS',
                                           'number': '3.4',
                                           'text': 'Os serviços em instalações elétricas energizadas em AT somente '
                                                   'podem ser realizados quando houver procedimentos específicos, '
                                                   'detalhados e assinados por profissional autorizado.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. REQUISITOS ADICIONAIS PARA INSTALAÇÕES ELÉTRICAS ENERGIZADAS',
                                           'number': '3.5',
                                           'text': 'Os executores das atividades em instalações elétricas energizadas '
                                                   'em AT e no SEP devem dispor de equipamento que permita a '
                                                   'comunicação permanente com os demais membros da equipe ou com o '
                                                   'centro de operação durante a realização do serviço.',
                                           'requirement': '',
                                           'recommendation': ''}]}],
                    'item_count': 38},
 'rac_line_live': {'title': 'RAC — Linha Viva',
                   'short': 'Linha Viva',
                   'icon': 'mi-live',
                   'prefix': 'RAC-LV',
                   'revision': 'Rev. 00',
                   'source_file': 'CheckList_Obrigações_Linha_Viva.xlsx',
                   'response_mode': 'sim_nao',
                   'groups': [{'name': 'CHECKLIST DE OBRIGAÇÕES',
                               'items': [{'section': 'Obrigações das contratadas',
                                          'number': '1',
                                          'text': 'Obrigatoriedade de técnico de segurança',
                                          'requirement': 'NR 4',
                                          'recommendation': ''},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '2',
                                          'text': 'Apresentação de veiculos para inspeção',
                                          'requirement': 'Detran',
                                          'recommendation': 'Se houver veículo, apresentar o check list em '
                                                            'conformidade'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '3',
                                          'text': 'Apresentação de equipamentos para inspeção',
                                          'requirement': 'NR 12',
                                          'recommendation': 'Realizar o check list diário das ferramentas e '
                                                            'equipamentos'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '4',
                                          'text': 'Apresentação de ferramentas elétricas/isolantes para inspeção',
                                          'requirement': 'NR 12',
                                          'recommendation': 'Realizar o check list diário das ferramentas e '
                                                            'equipamentos'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '5',
                                          'text': 'Uso obrigatório de vestimenta condutiva',
                                          'requirement': 'NR 6',
                                          'recommendation': 'Ver RAC Trabalho Linha Viva, item 3.2 Capacitação'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '6',
                                          'text': 'Treinamento e exames de aptidão para a NR 10*',
                                          'requirement': 'NR 10',
                                          'recommendation': 'Ver RAC Trabalho Linha Viva, item 3.1.3 Capacitação'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '7',
                                          'text': 'Treinamento e exames de aptidão para a NR 35*',
                                          'requirement': 'NR 35',
                                          'recommendation': 'Se houver atividade acima de 02 metros, deverá apresentar '
                                                            'o certificado e aptidão médica no ASO. Além de preencher '
                                                            'a PTE.'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '8',
                                          'text': 'Treinamento e exames de aptidão para a condução de equipamentos '
                                                  'móveis*',
                                          'requirement': 'NR 12',
                                          'recommendation': 'Enviar a CNH do condutor de veículo, se houver.'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '9',
                                          'text': 'Risco de ataques de animais peçonhentos',
                                          'requirement': 'NR 6',
                                          'recommendation': 'Se exercer atividade em área de risco é obrigatório uso '
                                                            'da perneira.'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '10',
                                          'text': 'PPRA - Programa de Prevenção de Riscos Ambientais*',
                                          'requirement': 'NR 9',
                                          'recommendation': 'Apresentar no SGF'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '11',
                                          'text': 'PCMSO - Programa de Controle de Saúde Médico Ocupacional*',
                                          'requirement': 'NR 7',
                                          'recommendation': 'Apresentar no SGF'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '12',
                                          'text': 'ASO - Atestado de saúde ocupacional*',
                                          'requirement': 'NR 7',
                                          'recommendation': 'Apresentar no SGF'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '13',
                                          'text': 'Ficha de EPI - Equipamento de proteção individual*',
                                          'requirement': 'NR 6',
                                          'recommendation': 'Apresentar no SGF'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '14',
                                          'text': 'Treinamento de integração*',
                                          'requirement': 'Manual Gestão',
                                          'recommendation': 'Agendar com antecedencia com o setor de SSO'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '15',
                                          'text': 'Diálogo de Saúde e Segurança*',
                                          'requirement': 'Manual Gestão',
                                          'recommendation': 'Realizar o DDS com a equipe, evidenciando em impresso '
                                                            'próprio'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '16',
                                          'text': 'Ordem de Serviço dos empregados*',
                                          'requirement': 'NR-01',
                                          'recommendation': 'Apresentar no SGF'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '17',
                                          'text': 'Plano de atendimento a emergência, informando hospitais e contatos*',
                                          'requirement': 'SGF',
                                          'recommendation': 'Validação no SGF e pelo time de SST da Serena Energia'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '18',
                                          'text': 'Seguro de vida e de acidentes pessoais*',
                                          'requirement': 'SGF',
                                          'recommendation': 'Se houver'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '19',
                                          'text': 'Análise de Risco da Atividade',
                                          'requirement': 'RAC LV',
                                          'recommendation': '1 - Realizar a Análise de Risco da atividade com '
                                                            'antecedencia e aprová-la na operação\n'
                                                            '2 - Repassar com fornecedor RAC - Trabalho Linha Viva, '
                                                            'item 6. Instruções gerais para realização da atividade'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '20',
                                          'text': 'Ambulância',
                                          'requirement': 'RAC LV',
                                          'recommendation': 'Informar ambulância no PAE e Procedimento operacional. '
                                                            'Estar com a mesma disponível na frente de serviço'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '21',
                                          'text': 'Integração de SST Serena Energia',
                                          'requirement': 'RAC LV',
                                          'recommendation': 'Realizar integração de SST com o time da Serena Energia, '
                                                            'antes do início das atividades,'},
                                         {'section': 'Obrigações das contratadas',
                                          'number': '22',
                                          'text': 'Procedimento operacional para execução',
                                          'requirement': 'RAC LV',
                                          'recommendation': 'Apresentação ao time de SST, Engenharia da Manutenção e '
                                                            'Time local.'}]}],
                   'item_count': 22},
 'rac_vegetation': {'title': 'RAC — Supressão de Vegetação',
                    'short': 'Supressão de Vegetação',
                    'icon': 'mi-leaf',
                    'prefix': 'RAC-SV',
                    'revision': 'Rev. 1\nMai/2023',
                    'source_file': 'Supressão de vegetação.xlsx',
                    'response_mode': 'atende',
                    'groups': [{'name': 'PESSOAS',
                                'items': [{'section': '1. SAÚDE',
                                           'number': '1.1',
                                           'text': 'Os exames ocupacionais vigentes para comprovar a aptidão para '
                                                   'realizar trabalhos em espaços confinados o Atestado de Saúde '
                                                   'Ocupacional (ASO) estão válidos e aprovados, a aptidão está esta '
                                                   'mencionada por escrito na ASO?',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. SAÚDE',
                                           'number': '1.2',
                                           'text': 'A ASO para supressão vegetal manual, em adição ao exame clínico '
                                                   'básico, deve incluir: eletroencefalograma, eletrocardiograma, '
                                                   'glicemia em jejum; hemograma completo e espirometria; para '
                                                   'supressão com motosserra incluir audiometria ocupacional.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. SAÚDE',
                                           'number': '1.3',
                                           'text': 'Os exames ocupacionais e a sistemática de avaliação devem ser '
                                                   'partes integrantes do PGR (Plano de Gerenciamento de Riscos) / '
                                                   'PGRTR (Plano de Gerenciamento de Riscos no Trabalho Rural), e '
                                                   'PCMSO (Plano de Controle Médio de Saúde Ocupacional/ conforme '
                                                   'NR-1/NR-31 e NR-7, da Omega Energia, empresas contratadas e '
                                                   'subcontratadas.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. SAÚDE',
                                           'number': '1.4',
                                           'text': 'A avaliação dos exames ocupacionais, a definição da a aptidão para '
                                                   'realizar atividades que envolvam trabalho em espaço confinado e a '
                                                   'emissão do Atestado de Saúde Ocupacional (ASO) são realizadas por '
                                                   'médico do trabalho habilitado?',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.1',
                                           'text': 'Os executores das atividades de supressão de vegetação que '
                                                   'envolvam a utilização de motosserras e similares, como roçadeiras, '
                                                   'devem realizar capacitação para utilização segura da máquina, com '
                                                   'carga horária mínima de 8 horas, com reciclagem anual, e conforme '
                                                   'conteúdo programático relativo à utilização constante no manual de '
                                                   'instruções disponibilizado pelo fabricante ou importador, que deve '
                                                   'conter informações:\n'
                                                   '\n'
                                                   'Riscos à segurança e a saúde durante o seu manuseio, incluíndo os '
                                                   'associados com animais peçonhentos;\n'
                                                   'nstruções de segurança no trabalho com o equipamento, de acordo '
                                                   'com as Recomendações Práticas da Organização Internacional do '
                                                   'Trabalho -OIT;-Especificações de ruído e vibração;-Advertências '
                                                   'sobre o uso inadequado.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.2',
                                           'text': 'Os executores das atividades de supressão de vegetação que '
                                                   'envolvam movimentação de equipamentos (tratores de esteira e '
                                                   'retroescavadeiras) e veículos pesados (caminhões) devem ser '
                                                   'possuir e comprovar habilitação específica –CNH –na categoria '
                                                   'requerida pelo Código Nacional de Trânsito para o tipo de '
                                                   'equipamento / veículo (Lei Nº. 12.452, 21/07/2011, Art. 143 a '
                                                   '145).',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.3',
                                           'text': 'Os executores que movimentam e/ou operam equipamentos e veículos '
                                                   'pesados devem realizar capacitação teórica e prática, com conteúdo '
                                                   'programático e reciclagem periódica conforme definido no Anexo II, '
                                                   'da NR-12 –vide RAC Movimentação e Operação de Veículos Pesados.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. CAPACITAÇÃO',
                                           'number': '2.4',
                                           'text': 'Os executores das atividades que envolvam supressão de vegetação '
                                                   'serão considerados habilitados e liberados para as atividades '
                                                   'apenas se todas as capacitações e habilitações exigidas estiverem '
                                                   'válidas, inseridas no SGF e aprovadas.',
                                           'requirement': '',
                                           'recommendation': ''}]},
                               {'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                                'items': [{'section': '1. EPI',
                                           'number': '1.1',
                                           'text': 'Supressão com motosserra, roçadeiras e similares-Capacete '
                                                   'proteção;\n'
                                                   '-Viseira ou óculos de proteção;\n'
                                                   '-Protetor auditivo;-Luvas de proteção;\n'
                                                   '-Calçado de segurança com biqueira;\n'
                                                   '-Perneira de couro / vaqueta;\n'
                                                   '-Vestimenta de corpo inteiro com camisa manga cumprida;\n'
                                                   'Específico para motosserra vestimenta para operador de motosserra.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. FERRAMENTAS MANUAIS',
                                           'number': '2.1',
                                           'text': 'Não é permitido o uso de ferramentas adaptadas ou com reparos '
                                                   'provisórios, devendo ser substituídas assim que constatada o '
                                                   'defeito / falha.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. FERRAMENTAS MANUAIS',
                                           'number': '2.2',
                                           'text': 'As ferramentas manuais devem ser seguras e eficientes, devendo ser '
                                                   'utilizadas exclusivamente para os fins a que se destinam, serem '
                                                   'mantidas em condições adequadas de uso e devendo ter seu uso '
                                                   'previamente aprovado pela Omega.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. FERRAMENTAS MANUAIS',
                                           'number': '2.3',
                                           'text': 'As ferramentas de corte devem ser guardadas e transportadas em '
                                                   'bainha.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. FERRAMENTAS MANUAIS',
                                           'number': '2.4',
                                           'text': 'Os cabos das ferramentas devem permitir boa aderência em situação '
                                                   'de manuseio, possuir formato que favoreça a empunhadura da mão do '
                                                   'trabalhador e ser fixado de forma a não se soltar acidentalmente '
                                                   'da lâmina.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. MOTOSSERRAS E ROÇADEIRAS',
                                           'number': '3.1',
                                           'text': 'Devem possuir os seguintes dispositivos de segurança:-Freio manual '
                                                   'ou automático de corrente;-Pino pega-corrente;-Protetor da mão '
                                                   'direita;-Protetor da mão esquerda;-Trava de segurança do '
                                                   'acelerador.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. MOTOSSERRAS E ROÇADEIRAS',
                                           'number': '3.2',
                                           'text': 'Devem conter sinalização de advertência indelével e resistente, em '
                                                   'local de fácil leitura e visualização do usuário, com a seguinte '
                                                   'informação: o uso inadequado pode provocar acidentes graves e '
                                                   'danos à saúde.',
                                           'requirement': '',
                                           'recommendation': ''}]},
                               {'name': 'PLANEJAMENTO EXECUÇÃO',
                                'items': [{'section': '1. DOCUMENTAÇÃO',
                                           'number': '1.1',
                                           'text': 'Todas atividades de supressão de vegetação deve ter supervisão.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. DOCUMENTAÇÃO',
                                           'number': '1.2',
                                           'text': 'Toda supressão vegetal deve possuir uma Autorização de Supressão '
                                                   'Vegetal ASV) emitida pela Diretoria de Licenciamento Ambiental '
                                                   'Federal (DILIC) do IBAMA.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. DOCUMENTAÇÃO',
                                           'number': '1.3',
                                           'text': 'Toda supressão vegetal deve possuir licença para porte e uso de '
                                                   'motosserra (LPU) emitida pelo IBAMA.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '1. DOCUMENTAÇÃO',
                                           'number': '1.4',
                                           'text': 'Toda supressão vegetal deve possuir uma APR (Análise de risco).',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. PRÉ-OPERAÇÃO',
                                           'number': '2.1',
                                           'text': 'Toda supressão de vegetação, seja em ativos existentes, em '
                                                   'expansões, em implantação ou em desenvolvimento, deve ser:\n'
                                                   'Planejada, organizada e executada por pessoas / equipes '
                                                   'capacitadas e autorizadas – vide item 3.1;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. PRÉ-OPERAÇÃO',
                                           'number': '2.2',
                                           'text': 'Os operadores das equipamentos autopropelidos e veículos pesados '
                                                   'devem portar comprovante de sua capacitação durante a operação '
                                                   'destes equipamentos;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. PRÉ-OPERAÇÃO',
                                           'number': '2.3',
                                           'text': 'Precedida de uma Análise de Risco (APR), específica para a '
                                                   'atividade, considerando os seguintes :\n'
                                                   'a) riscos inerentes à atividade, inclusive trabalho a céu aberto e '
                                                   'presença de animais peçonhentos;\n'
                                                   'b) riscos envolvendo afugentamento da fauna;\n'
                                                   'c) a localização e as interfências no entorno;\n'
                                                   'd) EPIs necessários;\n'
                                                   'e) utilização ferramentas manuais, motoserras e similares;\n'
                                                   'f) supervisão / coordenação da equipe de trabalho;\n'
                                                   'g) interação entre equipes de trabalho manual e os equipamentos e '
                                                   'veículos pesados na frente de trabalho;\n'
                                                   'h) sinalizadores, quando da utilização de equipamentos e/ou '
                                                   'veículos pesados;\n'
                                                   'i) sistemas de comunicação necessários;\n'
                                                   'j) condições impeditivas, inclusive meteorológicas;\n'
                                                   'k) planejamento para situações de emergência.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. PRÉ-OPERAÇÃO',
                                           'number': '2.4',
                                           'text': 'Na supressão de vegetação em locais ermos, ou seja, com pouco ou '
                                                   'nenhum suporte, principalmente para atendimento médico e acessos, '
                                                   'na análise de risco, deve ser definido previamente:\n'
                                                   '- Serviços de atendimento médico mais próximos;\n'
                                                   '- Locais que podem ser utilizados como apoio próximos, por '
                                                   'exemplo: \n'
                                                   'povoados, fazendas, clareiras, pastos;\n'
                                                   '- Plano de atendimento para primeiros socorros;\n'
                                                   '- A equipe deverá contar com membro(s) treinado(s) em primeiros '
                                                   'socorros;\n'
                                                   '- Caixa de primeiros socorros com medicamentos e equipamentos;\n'
                                                   '- Plano de resgate e meio de remoção, considerando:\n'
                                                   'a) os riscos do local e atividade, inclusive animais peçonhentos;\n'
                                                   'b) o tempo de resgate que não comprometa a recuperação do \n'
                                                   'acidentado.',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '2. PRÉ-OPERAÇÃO',
                                           'number': '2.5',
                                           'text': 'Precedida por inspeção de pré-uso (checklist) de todas as '
                                                   'ferramentas manuais, motosserras e similares, equipamentos e '
                                                   'veículos pesados que serão utilizados. O checklist de inspeção '
                                                   'deve ser indicadas as condições impeditivas para \n'
                                                   'a sua utilização, todos os equipamentos e veículos pesados não \n'
                                                   'conformes devem ser imediatamente substituídos;',
                                           'requirement': '',
                                           'recommendation': ''},
                                          {'section': '3. MANUTENÇÃO',
                                           'number': '3.1',
                                           'text': 'As motosseras e similares devem possui plano de manutenção '
                                                   'preventiva baseado nas recomedações dos seus fabricantes.',
                                           'requirement': '',
                                           'recommendation': ''}]}],
                    'item_count': 25},
 'rac_lifting': {'title': 'RAC — Içamento de Carga',
                 'short': 'Içamento de Carga',
                 'icon': 'mi-hook',
                 'prefix': 'RAC-IC',
                 'revision': 'Rev. 1\nMaio/2023',
                 'source_file': 'Içamento de Carga .xlsx',
                 'response_mode': 'atende',
                 'groups': [{'name': 'PLANEJAMENTO EXECUÇÃO',
                             'items': [{'section': '1. PLANEJAMENTO',
                                        'number': '1.1',
                                        'text': 'Todo içamento é planejado, organizado e executado por pessoas / '
                                                'equipes capacitadas e autorizadas?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.2',
                                        'text': 'Deve haver um Plano de Movimentação de Carga / Rigging para as '
                                                'condições abaixo:\n'
                                                'a)  Içamento de carga superior a 10 t;\n'
                                                'b) Operação em que carga exceda 75% da capacidade do equipamento;\n'
                                                'c) Içamento simultâneo utilizando dois ou mais equipamentos;\n'
                                                'd) Operação com translação do guindaste, utilizando o arraste para \n'
                                                'mudar a carga de localização;\n'
                                                'e) Operação próxima a redes elétricas de baixa, média ou alta '
                                                'tensão;\n'
                                                'f) Içamento de carga de geometria complexa e/ou em locais com \n'
                                                'restrição de espaço/interferências para a operação;\n'
                                                'g) Içamentos realizados por gruas, incluindo implantação e '
                                                'manutenção \n'
                                                'de aerogeradores, com exceção dos realizados pelos guinchos \n'
                                                'auxiliares, caso não se enquadrem nas condições b) c) ou f);\n'
                                                'As gruas devem em adição abranger o requerido no item 18.10.1.17.1;\n'
                                                'h) Operação de guindaste embarcado.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.3',
                                        'text': 'É emitido o termo de entrega técnica e liberação para uso após '
                                                'conclusão da montagem inicial de Gruas?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.4',
                                        'text': 'O trabalho de içamento é precedido de uma análise de risco?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.5',
                                        'text': 'É emitida uma Permissão de Trabalho para trabalhos de içamento não '
                                                'rotineiros?\n'
                                                'Todos os executores participam da elaboração da Análise de Risco e da '
                                                'Permissão de Trabalho?\n'
                                                'A elaboração desses documentos é realizada no local de execução da '
                                                'atividade?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.6',
                                        'text': 'É realizada inspeção de pré-uso (check-llist) nos equipamentos de '
                                                'guindar, cintas e dispositivos auxiliares de içamento que serão '
                                                'utilizados?\n'
                                                'Nos check-lists estão indicadas as condições impeditivas de '
                                                'utilização?\n'
                                                'Todos os equipamentos e dispositivos auxiliares não conformes são '
                                                'imediatamente substituídos?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.7',
                                        'text': 'Zona de perigo está implantada conforme definido na Análise de Riscos '
                                                'e/ou Permissão de Trabalho ou no procedimento operacional atendendo '
                                                'minimamente o distanciamento maior que a altura da carga ou maior que '
                                                'o comprimento da carga, devendo ser atendido aquele que for maior '
                                                '(distância de segurança mínimo). Em caso de plano de Rigging o mesmo '
                                                'deve ser atendido.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. PLANEJAMENTO',
                                        'number': '1.8',
                                        'text': 'Os planos de manutenção preventiva dos equipamentos são checados '
                                                'previamente ao início da atividade?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.1',
                                        'text': 'Documentos que devem estar disponibilizados no local da atividade de '
                                                'içamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.2',
                                        'text': 'Plano de Movimentação de Cargas / Rigging individual;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.3',
                                        'text': 'Registro de todas as ações de manutenção preventivas e corretivas e '
                                                'de inspeção do equipamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.4',
                                        'text': 'Comprovantes de capacitação e autorização do operador do \n'
                                                'equipamento de guindar em operação no local',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.5',
                                        'text': 'Comprovantes de capacitação do sinaleiro/amarrador de cargas e do '
                                                'trabalhador designado para inspecionar plataformas em balanço para '
                                                'recebimento de cargas',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.6',
                                        'text': 'Projeto de fixação na edificação ou em estrutura independente',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.7',
                                        'text': 'Projeto para a passarela de acesso à torre da grua',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.8',
                                        'text': 'Checklists dos equipamentos, cintas e dispositivos auxiliares de '
                                                'içamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.9',
                                        'text': 'Instruções de segurança emitidas, específicas à operacionalização do '
                                                'equipamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.10',
                                        'text': 'Circulação e permanência de pessoas sob as cargas suspensas e na zona '
                                                'de perigo são expressamente proibidas?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.11',
                                        'text': 'Movimentações de cargas com peso desconhecido são proibidas?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.12',
                                        'text': 'Movimentações de arraste ou içamentos inclinados são proibidos?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.13',
                                        'text': 'Içamento de carga que não esteja totalmente desprendida da sua '
                                                'superfície de apoio e livre de qualquer interferência que ofereça '
                                                'resistência ao movimento pretendido são proibidos?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.14',
                                        'text': 'Movimentação / alinhamento das cargas içadas com os braços / mãos são '
                                                'proibidos?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.15',
                                        'text': 'É vedada a utilização de cordas de fibras naturais ou sintéticas como '
                                                'elementos de içamento de cargas, salvo cabos de fibra sintética '
                                                'previstos nas normas técnicas nacionais vigentes?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.16',
                                        'text': 'É vedado o transporte de pessoas, salvo nas condições em operação de '
                                                'resgate e salvamento?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.17',
                                        'text': 'É proibido o trabalho em condições climáticas adversas ou qualquer '
                                                'outra condição meteorológica que possa afetar a segurança dos '
                                                'trabalhadores?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.18',
                                        'text': 'Os seguintes requisitos estabelecidos na NR-18 são seguidos?\n'
                                                '(1) o trabalho sob condições de ventos com velocidade acima de 42 '
                                                'km/h deve ser precedido de análise de risco específica e autorizado '
                                                'mediante permissão de trabalho;\n'
                                                '(2) sob nenhuma condição é permitida a operação com gruas quando da '
                                                'ocorrência de ventos com velocidade superior a 72 km/h;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. EXECUÇÃO',
                                        'number': '2.19',
                                        'text': 'A ponta da lança e o cabo de aço de levantamento da carga devem estar '
                                                'afastados da rede elétrica conforme orientação da concessionária '
                                                'local e distar, no mínimo, 3,0 m de qualquer obstáculo, sendo que, '
                                                'para distanciamentos inferiores a operacionalização da grua, deve ser '
                                                'realizada análise de risco elaborada por profissional legalmente '
                                                'habilitado.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. MANUTENÇÃO',
                                        'number': '3.1',
                                        'text': 'Todos os equipamentos de guindar, sob responsabilidade da Omega '
                                                'Energia ou empresas contratadas ou subcontratadas, devem possuir um '
                                                'plano individual manutenção preventivas baseado nas requisitos '
                                                'técnicos e prazos intervalos definidos pelos seus fabricantes e nas '
                                                'condições e caracteríticas de uso.\n'
                                                'Estes planos de manutenção devem ser inseridos no SGF e aprovados',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. MANUTENÇÃO',
                                        'number': '3.2',
                                        'text': 'As manutenções preventivas devem ser realizados por empresas '
                                                'especializadas e apresentarem laudos técnicos que indiquem todos os '
                                                'serviços realizados, peças / itens substituídos, recomendações para '
                                                'as preventivas posteriores e aprovação para utilização.Rev. 0 13\n'
                                                '▪ Os planos de manutençao preventivas e seus registros devem estar '
                                                'disponibilizados no canteiro de obras conforme requerido no item '
                                                '18.10.1.23 da NR-18.\n'
                                                '▪ Os registros das manutenções corretivas realizadas realizadas nos '
                                                'últimos doze meses devem estar disponibilizados para consulta / '
                                                'análise da Omega Energia.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. MANUTENÇÃO',
                                        'number': '3.3',
                                        'text': 'As cintas de içamento devem possuir um plano de inspeções períodicas '
                                                'para verificar danos, defeitos e outras não conformidades, que possam '
                                                'comprometer a segurança das atividades de içamento.\n'
                                                'A periodicidade deve ser determinada por um responsável qualificado.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. MANUTENÇÃO',
                                        'number': '3.4',
                                        'text': 'As manutenções preventivas e inspeções dos equipamentos de guindar, '
                                                'cintas e dispositivos auxiliares de içamento devem ser realizadas por '
                                                'profissional legalmente habilitado (ART)',
                                        'requirement': '',
                                        'recommendation': ''}]},
                            {'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                             'items': [{'section': '1. GRUA',
                                        'number': '1.1',
                                        'text': 'Indicação de fácil visualização da carga máxima admissível',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.2',
                                        'text': 'Limitador de carga máxima',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.3',
                                        'text': 'Estruturas aterradas e equipotencializadas / proteção contra descarga '
                                                'atmosférica;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.4',
                                        'text': 'Limitador de altura que permita a frenagem do moitão na elevação de '
                                                'cargas',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.5',
                                        'text': 'Dispositivo de monitoramento na descida, se definido na análise de '
                                                'risco;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.6',
                                        'text': 'Alarme sonoro com acionamento automático quando o limitador de carga '
                                                'ou de momento estiver atuando;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.7',
                                        'text': 'Alarme sonoro para ser acionado pelo operador em situações de risco '
                                                'e/ou alerta',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.8',
                                        'text': 'Trava de segurança no gancho do moitão',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.9',
                                        'text': 'Dispositivo instalado nas polias que impeça o escape acidental dos '
                                                'cabos de aço',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.10',
                                        'text': 'Limitadores de curso para movimento de translação quando instalado '
                                                'sobre trilhos',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.11',
                                        'text': 'Limitador de fim de curso para o carro da lança nas duas '
                                                'extremidades; sistema automático de controle de carga admissível ou '
                                                'placas indicativas de carga admissível ao longo da lança, conforme '
                                                'especificado pelo fabricante ou locador',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.12',
                                        'text': 'Luz de obstáculo no ponto mais alto da grua, caso exceda 45 m deve '
                                                'ser instalada sinalização para aviões: balizador de aeródromo '
                                                '(airfield  lighting).',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.13',
                                        'text': 'SPIQ (sistema de proteção individual contra quedas) para acesso '
                                                'horizontal e vertical onde houver risco de queda;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.14',
                                        'text': 'Limitador/contador de giro, mesmo quando a grua dispuser de coletor '
                                                'elétrico',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.15',
                                        'text': 'Sistema de proteção contra quedas na transposição entre a escada de '
                                                'acesso e o posto de trabalho do operador e na contra lança, conforme '
                                                'a NR-12',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.16',
                                        'text': 'Escadas fixas conforme disposto no item 18.8 da NR-18;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.17',
                                        'text': 'Limitadores de movimento para lanças retráteis ou basculantes',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.18',
                                        'text': 'Dispositivo automático de medição de vento interligado com o '
                                                'computador de bordo interligado com dispositivo de segurança '
                                                'bloqueando a operação, caso o vento ultrapasse os limites definidos '
                                                'para o tipo de içamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.19',
                                        'text': '(1) o trabalho sob condições de ventos com velocidade acima de 42 '
                                                'km/h deve ser precedido de análise de risco específica e autorizado '
                                                'mediante permissão de trabalho; (2) sob nenhuma condição é permitida '
                                                'a operação com gruas quando da ocorrência de ventos com velocidade \n'
                                                'superior a 72 km/h;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. GRUA',
                                        'number': '1.20',
                                        'text': 'Dispositivo de parada de emergência',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.1',
                                        'text': 'Acesso seguro e, quando necessário em movimentação vertical para '
                                                'acessar a cabine, tornar obrigatório o uso do SPIQ (sistema de '
                                                'proteção individual contra quedas);',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.2',
                                        'text': 'Ter acoplada à parte giratória do equipamento, exceto para gruas de '
                                                'pequeno porte e automontante;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.3',
                                        'text': 'Interior climatizado;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.4',
                                        'text': 'Assento ergonômico;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.5',
                                        'text': 'Proteção contra raios solares e intempéries',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.6',
                                        'text': 'Tabela de cargas máximas em todas as condições de uso, escrita em '
                                                'língua portuguesa, no seu interior de fácil visualização pelo '
                                                'operador e para consulta para terceiros;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.7',
                                        'text': 'Extintor de incêndio adequado ao risco;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.8',
                                        'text': 'Limitador de momento máximo, impedindo a continuidade do movimento e '
                                                'só permitindo a sua reversão;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.9',
                                        'text': 'Anemômetro que indique no interior da cabine do equipamento a '
                                                'velocidade do vento;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.10',
                                        'text': 'Indicadores de níveis longitudinal e transversal, exceto para as '
                                                'gruas que não são montadas sobre base móvel;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. GRUAS (cabine de comando)',
                                        'number': '2.11',
                                        'text': 'Dispositivo de parada de emergência.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.1',
                                        'text': 'Indicação de fácil visualização da carga máxima admissível',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.2',
                                        'text': 'Limitador de carga máxima',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.3',
                                        'text': 'Ponto para aterramento (guindaste / veículo base);',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.4',
                                        'text': 'Limitador de altura que permita a frenagem do moitão na elevação de '
                                                'cargas;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.5',
                                        'text': 'Dispositivo de monitoramento na descida, se definido na análise de '
                                                'risco;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.6',
                                        'text': 'Monitoramento de pressão das patolas com alarme sonoro',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.7',
                                        'text': 'Alarme sonoro com acionamento automático quando o limitador de carga '
                                                'ou de momento estiver atuando;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.8',
                                        'text': 'Alarme sonoro para ser acionado pelo operador em situações de risco '
                                                'e/ou alerta;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.9',
                                        'text': 'Trava de segurança no gancho do moitão',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.10',
                                        'text': 'Dispositivo instalado nas polias que impeça o escape acidental dos '
                                                'cabos de aço',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.11',
                                        'text': 'Limitadores de curso para movimento de translação quando instalado '
                                                'sobre trilhos',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.12',
                                        'text': 'Dispositivo de parada de emergência',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '3. GUINDASTES',
                                        'number': '3.13',
                                        'text': 'Em lanças treliçadas que excedam 45 m de altura deve ser instalada, '
                                                'no ponto mais alto, sinalização para aviões: balizador de aeródromo '
                                                '(airfield lighting).',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.1',
                                        'text': 'Acesso seguro e, quando necessário em movimentação vertical para '
                                                'acessar a cabine, tornar obrigatório o uso do SPIQ (sistema de '
                                                'proteção individual contra quedas);',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.2',
                                        'text': 'Ter acoplada à parte giratória do equipamento, exceto para gruas de '
                                                'pequeno porte e automontante;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.3',
                                        'text': 'Interior climatizado;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.4',
                                        'text': 'Assento ergonômico;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.5',
                                        'text': 'Proteção contra raios solares e intempéries',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.6',
                                        'text': 'Tabela de cargas máximas em todas as condições de uso, escrita em '
                                                'língua portuguesa, no seu interior de fácil visualização pelo '
                                                'operador e para consulta para terceiros;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.7',
                                        'text': 'Extintor de incêndio adequado ao risco;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.8',
                                        'text': 'Limitador de momento máximo, impedindo a continuidade do movimento e '
                                                'só permitindo a sua reversão;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.9',
                                        'text': 'Anemômetro que indique no interior da cabine do equipamento a '
                                                'velocidade do vento;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '4. GUINDASTES (cabine de comando)',
                                        'number': '4.10',
                                        'text': 'Dispositivo de parada de emergência.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '5. GUINDASTES VEICULARES ARTICULADOS (Munck)',
                                        'number': '5.1',
                                        'text': 'Indicação de fácil visualização da carga máxima admissível da lança '
                                                'do braço articulado;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '5. GUINDASTES VEICULARES ARTICULADOS (Munck)',
                                        'number': '5.2',
                                        'text': 'Possuir tabela de cargas máximas em todas as condições de uso, '
                                                'escrita em língua portuguesa, de fácil visualização pelo operador e '
                                                'de consulta por terceiros;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '5. GUINDASTES VEICULARES ARTICULADOS (Munck)',
                                        'number': '5.3',
                                        'text': 'Sistema de comando da lança por controle remoto',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '5. GUINDASTES VEICULARES ARTICULADOS (Munck)',
                                        'number': '5.4',
                                        'text': 'Ponto de aterramento guindaste / veículo base',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '5. GUINDASTES VEICULARES ARTICULADOS (Munck)',
                                        'number': '5.5',
                                        'text': 'Veículo / caminhão base com espelhos retrovisores externos, faróis, '
                                                'luz de marcha à ré, alarme sonoro de marcha a ré, freio de '
                                                'estacionamento, buzina, extintores de incêndio adequado ao risco e '
                                                'cinto de segurança de três pontos para todos os ocupantes',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.1',
                                        'text': 'Indicação de fácil visualização da carga máxima admissível',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.2',
                                        'text': 'Possuir instalações elétricas conforme requerido pela NR-12, item '
                                                '12.3',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.3',
                                        'text': 'Aterramento / equipotencialização',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.4',
                                        'text': 'Alerta sonoro e/ou visual de movimentação',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.5',
                                        'text': 'spositivos de partida, acionamento e parada conforme requerido pela '
                                                'NR-12, item 12.4;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.6',
                                        'text': 'Dispositivo de parada de emergência conforme requerido pela NR-12, '
                                                'item 12.6, subitens 12.6.1 a 12.6.5.1;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.7',
                                        'text': 'Sistema de freio eletromecânico, eletromagnético ou eletro-hidráulico '
                                                'do sistema de movimentação do gancho;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.8',
                                        'text': 'Chaves limite de cabo frouxo, fim-de-curso para todos movimentos, '
                                                'limite de velocidade de redução dos movimentos de translação e '
                                                'sobre_x0002_velocidade;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.9',
                                        'text': 'Partes rotativas e móveis com proteções físicas',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.10',
                                        'text': 'Sistema de movimento de elevação provido de dispositivo de frenagem '
                                                'de segurança, no caso de interrupção no fornecimento de energia '
                                                'elétrica;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.11',
                                        'text': 'Dispositivo para travar as rodas nos trilhos para impedir '
                                                'descarrilamento;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.12',
                                        'text': 'Sinalização padronizada do sentido de atuação dos controles de '
                                                'acionamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.13',
                                        'text': 'Acessos seguros à ponte, aos carros e à cabine do operador. No caso '
                                                'de acessos à ponte no mesmo nível do caminho de rolamento da ponte, '
                                                'devem ser previstos portões que permaneçam normalmente fechados',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '6. PONTES ROLANTES',
                                        'number': '6.14',
                                        'text': 'Cabine de operação que atenda aos requisitos ergonômicos e possua '
                                                'dispositivos de segurança contra acionamento acidental.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.1',
                                        'text': 'Indicação de fácil visualização da carga máxima admissível',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.2',
                                        'text': 'Dispositivos de partida, acionamento e parada conforme requerido pela '
                                                'NR-12, item 12.6, subitens 12.6.1 a 12.6.5.1',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.3',
                                        'text': 'Ponto para aterramento / equipotencialização;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.4',
                                        'text': 'Dispositivo de parada de emergência',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.5',
                                        'text': 'Dispositivo de travamento físico para prevenir a queda livre da carga',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.6',
                                        'text': 'Chaves limites fim de curso para todos os movimentos;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.7',
                                        'text': 'Partes rotativas e móveis com proteções físicas',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.8',
                                        'text': 'Sistema de movimento de elevação provido de dispositivo de frenagem '
                                                'de segurança no caso de interrupção no fornecimento de energia '
                                                'elétrica',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.9',
                                        'text': 'Ganchos providos de trava de segurança',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.10',
                                        'text': 'Chave de bloqueio removível para os controles remotos;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.11',
                                        'text': 'Sinalização padronizada do sentido de atuação dos controles de '
                                                'acionamento;',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '7. TALHAS ELÉTRICAS',
                                        'number': '7.12',
                                        'text': 'Sinalização indicativa do movimento de translação nos controles de '
                                                'acionamento e na estrutura.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '8. CINTAS DE IÇAMENTO',
                                        'number': '8.1',
                                        'text': 's cintas de içamento planas, tubulares ou as de ultra-alta '
                                                'tenacidade \n'
                                                'devem ser manufaturadas e atendendo aos requisitos da NBR-15637, \n'
                                                'Partes 1, 2 e 3 respectivamente',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '8. CINTAS DE IÇAMENTO',
                                        'number': '8.2',
                                        'text': 'As cintas devem ser manufaturadas formadas por multifilamentos de '
                                                'fios \n'
                                                'sintéticos de alta tenacidade, garantido pelo fabricante como sendo \n'
                                                'estáveis à luz e a temperatura, com tenacidade igual ou superior a '
                                                '60 \n'
                                                'cN/tex, em poliamida (PA), poliéster (PES) ou polipropileno (PP)',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '8. CINTAS DE IÇAMENTO',
                                        'number': '8.3',
                                        'text': 'As cintas devem ser marcadas com etiquetas legíveis e duráveis '
                                                'fixadas diretamente na própria cinta e devem conter, no mínimo, as '
                                                'seguintes informações:\n'
                                                '- Carga máxima de trabalho (CMT) em elevação vertical, cesto e '
                                                'forca;\n'
                                                '- Composição da cinta;\n'
                                                '- Comprimento nominal;\n'
                                                'Rev. 0 9\n'
                                                '- Nome do fabricante, símbolo, marca registrada ou outra '
                                                'identificação \n'
                                                'sem ambiguidade;\n'
                                                '- Código de fabricação, costurado internamente;\n'
                                                '- Referência a atendimento da NBR-15637.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '8. CINTAS DE IÇAMENTO',
                                        'number': '8.4',
                                        'text': 'Cintas sem identificação nunca devem ser utilizadas devido ao alto '
                                                'risco potencial envolvido nas atividades de içamento',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '9. DISPOSITIVO AUXILIARES DE IÇAMENTO',
                                        'number': '9.1',
                                        'text': 'Os dispositivos auxiliares de içamento: conectores, elos, ganchos, '
                                                'correntes/lingas, manilhas, olhais, patolas, pega-chapas, '
                                                'pega-tambor, e pega-tubos devem possuir: \n'
                                                '- Identificação da norma construtiva de referência;\n'
                                                '- Identificação de carga máxima admissível para trabalho; \n'
                                                '- Identificação do fabricante e número de série, que permita sua '
                                                'rastreabilidade;\n'
                                                '- Certificado ou dispor de projeto elaborado por profissional '
                                                'legalmente habilitado, contendo a especificação e descrição das '
                                                'características mecânicas e elétricas, quando aplicáveis.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '10. CONDIÇÕES ESPECÍFICAS',
                                        'number': '10.1',
                                        'text': 'Equipamento de guindar sobre base móvel:\n'
                                                'sua estabilidade deve ser garantida, assim como a da superfície que '
                                                'será utilizada, atendendo às recomendações do fabricante ou do '
                                                'profissional legalmente habilitado.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '10. CONDIÇÕES ESPECÍFICAS',
                                        'number': '10.2',
                                        'text': 'Operação simultânea de equipamentos de guindar com risco de '
                                                'interferência entre seus movimentos:\n'
                                                'deve haver sistema automatizado anticolisão instalado nos '
                                                'equipamentos ou sinaleiro capacitado e autorizado para coordenar os '
                                                'movimentos desses equipamentos.',
                                        'requirement': '',
                                        'recommendation': ''}]},
                            {'name': 'PESSOAS',
                             'items': [{'section': '1. SAÚDE',
                                        'number': '1.1',
                                        'text': 'São checados se os exames ocupacionais vigentes para comprovar a '
                                                'aptidão para realizar atividades que envolvam Içamento de Carga e o '
                                                'Atestado de Saúde Ocupacional (ASO) estão válidos e aprovados, e a '
                                                'aptidão está\n'
                                                'esta mencionada por escrito na ASO?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. SAÚDE',
                                        'number': '1.2',
                                        'text': 'Os ASOs para trabalhos em altura incluem, em adição ao exame clínico '
                                                'básico, os seguintes exames complementares: acuidade visual, '
                                                'eletroencefalograma, eletrocardiograma, glicemia em jejum, hemograma '
                                                'completo e espirometria?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. SAÚDE',
                                        'number': '1.3',
                                        'text': 'Os exames ocupacionais e a sistemática de avaliação fazem parte do '
                                                'PGR (Plano de Gerenciamento de Riscos) e PCMSO (Plano de Controle '
                                                'Médio de Saúde Ocupacional), conforme NR-1 e NR-7?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '1. SAÚDE',
                                        'number': '1.4',
                                        'text': 'A avaliação dos exames ocupacionais, a definição da a aptidão para '
                                                'realizar atividades que envolvam içamento de carga e a emissão do '
                                                'Atestado de Saúde Ocupacional (ASO) são realizadas por médico do '
                                                'trabalho habilitado?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.1',
                                        'text': 'Todo executor das atividades que envolvam Içamento de Carga possui '
                                                'capacitação teórica e prática conforme definido no anexo I da NR-18?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.2',
                                        'text': 'Os operadores de máquinas automores e autopropoelidas são capacitados '
                                                'no conteúdo definido no ítem 1.1 do anexo II da NR12?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.3',
                                        'text': '35.4.1.3.1 A organização deve estabelecer sistema de identificação '
                                                'que permita a qualquer tempo conhecer a abrangência da autorização de '
                                                'cada trabalhador.',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.4',
                                        'text': 'Existe evidencia (cracha de treinamento, adesivo em capacete, etc) de '
                                                'fácil consulta em campo para os profissionais envolvidos com operação '
                                                'de içamento de carga e tipo de equipamento permitido para operar?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.5',
                                        'text': 'Os sinaleiros/amarrador possuem evidencia de treinamento de facil '
                                                'consulta em campo?',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.6',
                                        'text': 'O Supervisor de rigger tem evidencia de capacitação para projetar, '
                                                'auditar e ajustar planos de rigger de facil consulta e aprovados no '
                                                'S.G.F. (Sistema de Gestão de Fornecedores).',
                                        'requirement': '',
                                        'recommendation': ''},
                                       {'section': '2. CAPACITAÇÃO',
                                        'number': '2.7',
                                        'text': 'Os executantes das atividades que envolvam içamento de carga têm '
                                                'evidencia de capacitação para projetar, auditar e ajustar planos de '
                                                'rigger de facil consulta e aprovados no S.G.F. (Sistema de Gestão de '
                                                'Fornecedores).',
                                        'requirement': '',
                                        'recommendation': ''}]}],
                 'item_count': 134},
 'rac_tme': {'title': 'RAC — TME',
             'short': 'TME',
             'icon': 'mi-tower',
             'prefix': 'RAC-TME',
             'revision': 'Rev. 03',
             'source_file': 'RAC - TME_rev.03.xlsx',
             'response_mode': 'atende',
             'groups': [{'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                         'items': [{'section': '1. EPI',
                                    'number': '1.1',
                                    'text': 'Os EPIs para proteção contra queda em trabalhos em altura devem ser:\n'
                                            '- Certificados, ou seja, com CA e atendendo às normas aplicáveis;\n'
                                            '- Adequados para a utilização pretendida;\n'
                                            '- Utilizados considerando os limites de uso;\n'
                                            '- Ajustados ao peso e à altura do trabalhador.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. EPI',
                                    'number': '1.2',
                                    'text': 'Os conectores devem estar e conformidade com a ABNT NBR 15837 que é '
                                            'evidenciada pelas as seguintes marcações / indicações em português e '
                                            'legíveis:\n'
                                            'a) código e/ou modelo do conector;\n'
                                            'b) data e/ou lote de fabricação;\n'
                                            'c) menção à NBR 15837 e classe do conector;\n'
                                            'd) resistência estática mínima do eixo maior ou a resistência informada '
                                            'pelo fabricante (quando maior) gravada no corpo do conecto, em kN, e '
                                            'corresponder à posição fechada e travada;\n'
                                            'e) marca do fabricante ou responsável pela comercialização;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. CINTO DE SEGURANÇA TIPO PARAQUEDISTA',
                                    'number': '2.1',
                                    'text': 'Deve atender aos seguintes requisitos: \n'
                                            '- As fitas e os fios de costura devem ser fabricados a partir de fibras '
                                            'sintéticas virgens mono ou multifilamento (polipropileno não é '
                                            'aceitável), os fios devem ter cores contrastantes ao material básico para '
                                            'facilitar a inspeção visual;\n'
                                            '- A resistência à ruptura das fibras sintéticas deve ser, no mínimo, de '
                                            '0,6 N/tex; \n'
                                            '- Ser constituído de fitas desde a região da pélvis até os ombros, '
                                            'ajustável ao usuário, sendo a largura mínima das fitas primárias (que '
                                            'exerce funções de sustentação) 40 mm e das secundárias (que não exercem '
                                            'funções de sustentação) 20 mm;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. CINTO DE SEGURANÇA TIPO PARAQUEDISTA',
                                    'number': '2.2',
                                    'text': 'Deve atender aos seguintes requisitos: \n'
                                            '- Os elementos de engate para proteção contra queda podem estar situados '
                                            'de forma que, durante a utilização do equipamento, se encontrem acima do '
                                            'centro de gravidade do corpo, no peito e/ou nas costas do usuário;\n'
                                            '- Os conectores devem cumprir os requisitos da ABNT NBR 15837 e os '
                                            'acessórios metálicos devem estar em conformidade com os requisitos de '
                                            'proteção contra a corrosão especificados na ABNT NBR 8094;\n'
                                            '- Ser aprovado nos ensaios de resistência estática, resistência dinâmica '
                                            'e resistência à corrosão por exposição à névoa salina, conforme NBR '
                                            '15836;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. CINTO DE SEGURANÇA TIPO PARAQUEDISTA',
                                    'number': '2.3',
                                    'text': 'Deve conter as seguintes marcações / indicações em português e legíveis:\n'
                                            'a) pictograma que indique que os usuários devem ler as informações / '
                                            'manual fornecidos pelo fabricante;\n'
                                            'b) pictograma com a letra "A" maiúscula em cada elemento de engate para '
                                            'proteção contra queda;\n'
                                            'c) pictograma com uma marcação “A/N”, maiúscula, quando existirem n '
                                            'elementos de engate simultâneos;\n'
                                            'd) indicação de atendimento à NBR 15836;\n'
                                            'e) código e tamanho;\n'
                                            'f) data de fabricação e lote;\n'
                                            'g) logotipo e/ou nome do fabricante nacional ou importado.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. TALABARTES',
                                    'number': '3.1',
                                    'text': 'Deve atender aos seguintes requisitos:\n'
                                            '- O comprimento de um talabarte simples, duplo ou regulável com seus '
                                            'terminais, não pode exceder 2,00 m em sua totalidade, medido a partir dos '
                                            'pontos de contato dos terminais;\n'
                                            '- Os talabartes que tiverem mais de 0,90 m e forem utilizados em um '
                                            'sistema antiqueda, devem possuir absorvedor de energia em conformidade '
                                            'com a ABNT NBR 14629, neste caso o comprimento do talabarte deve ser '
                                            'determinado com o absorvedor de energia intacto;\n'
                                            '- Os talabartes com fitas elásticas devem ser esticados para a obtenção '
                                            'do seu comprimento;\n'
                                            '- Os extremos da seção regulável do talabarte devem estar dotados de um '
                                            'batente final;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. TALABARTES',
                                    'number': '3.2',
                                    'text': 'Deve ser aprovado nos ensaios de resistência estática, resistência '
                                            'dinâmica e  resistência à corrosão por exposição à névoa salina, conforme '
                                            'NBR 15834; \n'
                                            '- Deve conter as seguintes marcações / indicações em português e '
                                            'legíveis:\n'
                                            'a) nome do fabricante, fornecedor ou marca comercial;\n'
                                            'b) lote de fabricação ou número de série e data de fabricação;\n'
                                            'c) modelo e tipo;\n'
                                            'd) pictograma que indique que os usuários devem ler as informações /  '
                                            'manual fornecidos pelo fabricante; \n'
                                            'e) menção à NBR 15834;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. TALABARTES',
                                    'number': '3.3',
                                    'text': 'Nos talabartes com absorvedor de energia, deve ser informada a zona livre '
                                            'de queda. É recomendado o uso de um pictograma que informe a distância da '
                                            'zona livre de queda, que compreende o ponto de ancoragem e o solo ou '
                                            'ponto mais provável de impacto.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.1',
                                    'text': 'Trava-quedas Ancoragem em linha flexível:\n'
                                            '- A linha de ancoragem flexível deve ser fixada em um ponto de ancoragem '
                                            'superior e deve possuir um batente superior, ou ser capaz de ajustar-se a '
                                            'um batente superior, para evitar que o trava-queda deslizante se separe, '
                                            'de modo involuntário, da linha de ancoragem;\n'
                                            '- Caso o trava-queda possua uma trava manual (mecanismo que bloqueia o '
                                            'trava-queda deslizante na linha de ancoragem), o extremo inferior da '
                                            'linha de ancoragem flexível deve ter uma terminação, por exemplo, um '
                                            'terminal inferior fixo ou um lastro;\n'
                                            '- Uma linha de ancoragem flexível feita de cabo metálico deve ser dotada, '
                                            'em todos os casos, de um terminal inferior ou um lastro.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.2',
                                    'text': 'Trava-quedas Ancoragem em linha rígida:\n'
                                            '- Deve ser constituída por um trilho ou cabo metálico, o cabo metálico '
                                            'deve possuir um diâmetro de 8 mm ou uma dimensão que proporcione '
                                            'segurança equivalente;\n'
                                            '-Para limitar movimentos laterais deve ser fixada na estrutura a '
                                            'intervalos estabelecidos; se for formada por cabo metálico, este deve '
                                            'estar firmemente fixado e tensionado sobre uma estrutura;\n'
                                            '- A linha de ancoragem deve ser projetada de tal forma que o trava-queda '
                                            'se movimente nas direções especificadas e que seja impedida a separação '
                                            'voluntária do trava-queda da linha de ancoragem;\n'
                                            '- Todos os pontos de engate e desengate da linha de ancoragem devem estar '
                                            'equipados com um batente final para evitar que o trava-queda se separe '
                                            'involuntariamente da linha de ancoragem.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.3',
                                    'text': 'Trava-queda:\n'
                                            '- Deve estar equipado com um conector ou com um extensor mais um '
                                            'conector, com um comprimento máximo de 1m, incluindo, se for o caso, '
                                            'absorvedor de energia e conectores. Se possuir somente conector, este '
                                            'pode estar unido de modo permanente ou ser separável. O comprimento do '
                                            'extensor deve ser especificado pelo fabricante e estar indicado nas '
                                            'instruções de uso. \n'
                                            '- O mecanismo para a sua abertura deve ser projetado de forma  que só '
                                            'pode ser aberto ou fechado, mediante duas ações manuais consecutivas e '
                                            'voluntárias;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.4',
                                    'text': 'O absorvedor de energia, integrado ou não com o extensor, deve estar '
                                            'conformidade com a ABNT NBR 14629; e a força de impacto transmitida ao '
                                            'trabalhador seja de no máximo 6kN quando de uma eventual queda indicador '
                                            'de fim de vida útil;\n'
                                            'A conformidade a ABNT NBR 14629 é evidenciada pelas seguintes marcações / '
                                            'indicações em português e legíveis:\n'
                                            'a) nome fabricante, fornecedor ou marca comercial; \n'
                                            'b) lote de fabricação ou número de série e data de fabricação;\n'
                                            'c) modelo e tipo;\n'
                                            'd) pictograma que indique que os usuários devem ler as informações / '
                                            'manual fornecidos pelo fabricante;\n'
                                            'e) menção da NBR 14629;\n'
                                            'f) informação de que o comprimento máximo do absorvedor de energia (sem '
                                            'extensão), com o talabarte e conectores, não pode exceder 2,0 m;\n'
                                            'g) comprimento do absorvedor, após distensão total máxima, para '
                                            'absorvedores de energia vendidos como componentes, para possibilitar o '
                                            'cálculo da zona livre de queda, quando este for montado a um sistema de '
                                            'retenção de queda;\n'
                                            'h) nos absorvedores de energia incorporados a talabartes de segurança, a '
                                            'informação sobre a zona livre de queda. Deve conter um pictograma que '
                                            'informe a distância da zona livre de queda, que compreende o ponto de '
                                            'ancoragem e o solo ou ponto mais provável de impacto.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.5',
                                    'text': 'Ser aprovado nos ensaios de travamento, resistência estática, resistência '
                                            'estática, comportamento dinâmico e resistência à corrosão por exposição à '
                                            'névoa salina, conforme NBR 14626 (ancorado em linha flexível) ou NBR '
                                            '14627 (ancorado em linha rígida);',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.6',
                                    'text': 'Deve conter as seguintes marcações / indicações em português e legíveis:\n'
                                            'a)\tpictograma que indique que os usuários devem ler as informações / '
                                            'manual fornecidos pelo fabricante;\n'
                                            'b)\tindicação da posição correta de uso.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.7',
                                    'text': 'Para ancoragem em linha flexível:\n'
                                            'c) indicação informando ao usuário que deve ser utilizada somente a linha '
                                            'de ancoragem flexível especificada pelo fabricante;\n'
                                            'd) identificação do modelo e de que é um trava-queda deslizante para '
                                            'linha flexível;\n'
                                            'e) menção à NBR 14626.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '4. TRAVA-QUEDAS DESLISANTES E SISTEMAS DE ANCORAGEM ASSOCIADOS',
                                    'number': '4.8',
                                    'text': 'Para ancoragem em linha rígida:\n'
                                            'c)  caso possa ser removido da linha de ancoragem rígida, deve existir '
                                            'informação sobre sua utilização em linhas rígidas apropriadas, gravada no '
                                            'trava-queda ou em uma zona adjacente à linha;\n'
                                            'd)  identificação do modelo e de que é um trava-queda deslizante para '
                                            'linha rígida;\n'
                                            'e)  menção à NBR 14627.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '5. SISTEMAS DE ANCORAGEM',
                                    'number': '5.1',
                                    'text': 'A ancoragem estrutural e seus elementos de fixação devem:\n'
                                            '• Ser projetados e construídos sob responsabilidade de profissional '
                                            'legalmente habilitado;\n'
                                            '• Atender às normas técnicas nacionais ou, na sua inexistência, às normas '
                                            'internacionais aplicáveis;\n'
                                            '• Os pontos da ancoragem devem possuir marcação realizada pelo fabricante '
                                            'ou responsável contendo, no mínimo:\n'
                                            'a) Identificação do fabricante;\n'
                                            'b) Número de série ou outro meio de rastreabilidade\n'
                                            'c) Número máximo de trabalhadores conectados simultaneamente ou força '
                                            'máxima aplicável.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '5. SISTEMAS DE ANCORAGEM',
                                    'number': '5.2',
                                    'text': 'Dispositivo de ancoragem deve ser:\n'
                                            '• Certificado;\n'
                                            '• Fabricado em conformidade com as normas técnicas nacionais vigentes sob '
                                            'responsabilidade do profissional legalmente habilitado;\n'
                                            '• Projetado por profissional legalmente habilitado, tendo como referência '
                                            'as normas técnicas nacionais vigentes, como parte integrante de um '
                                            'sistema completo de proteção individual contra quedas.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '5. SISTEMAS DE ANCORAGEM',
                                    'number': '5.3',
                                    'text': 'Os sistemas de ancoragem devem ser:\n'
                                            '• Instalados por trabalhadores capacitados;\n'
                                            '• Submetidos à inspeção inicial e periódica.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '5. SISTEMAS DE ANCORAGEM',
                                    'number': '5.4',
                                    'text': 'Inspeção em sistemas de ancoragem:\n'
                                            '• A inspeção inicial deve ser realizada após a instalação, alteração ou '
                                            'mudança de local;\n'
                                            '• inspeção periódica deve ser efetuada de acordo com o procedimento '
                                            'operacional, considerando o projeto, respeitando as instruções do '
                                            'fabricante e as normas regulamentadoras e técnicas aplicáveis, com '
                                            'periodicidade não superior a 12 meses.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '5. SISTEMAS DE ANCORAGEM',
                                    'number': '5.5',
                                    'text': 'Sistema de ancoragem temporário deve:\n'
                                            '• Atender os requisitos de compatibilidade a cada local de instalação '
                                            'conforme procedimento operacional;\n'
                                            '• Ter os pontos de fixação definidos sob responsabilidade de profissional '
                                            'legalmente habilitado.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '5. SISTEMAS DE ANCORAGEM',
                                    'number': '5.6',
                                    'text': 'Um sistema de ancoragem deve possuir projeto e a instalação deve estar '
                                            'sob responsabilidade de profissional legalmente habilitado.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '6. ARMAZENAMENTO',
                                    'number': '6.1',
                                    'text': 'Existe local adequado para guarda e armazenamento dos Equipamentos de '
                                            'proteção para trabalho em altura? (Bolsas, compartimentos, etc).',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '7. EQUIPAMENTO',
                                    'number': '7.1',
                                    'text': 'A TME encontra-se certificada e com toda documentação arquivada?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '7. EQUIPAMENTO',
                                    'number': '7.2',
                                    'text': 'A certificação possui ART com responsável técnico?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '7. EQUIPAMENTO',
                                    'number': '7.3',
                                    'text': 'Os equipamentos de precisão para certificação da TME estão com calibração '
                                            'validas? (Ex.: tensiomentro, torquimetro, inclinômetro, multimetro, '
                                            'esclerômetro...)',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '8. TORRE / FUNDAÇÕES / ESTAIS',
                                    'number': '8.1',
                                    'text': 'Foi realizada inspeção visual e fotográfica completa da torre, fundações, '
                                            'cordoalhas e estais antes da escalada, registrando anomalias no relatório '
                                            'técnico?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '8. TORRE / FUNDAÇÕES / ESTAIS',
                                    'number': '8.2',
                                    'text': 'Os estais apresentam tensão dentro da faixa de 150 a 400 kgf, medida com '
                                            'tensiômetro calibrado e registrada em planilha/laudo?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '8. TORRE / FUNDAÇÕES / ESTAIS',
                                    'number': '8.3',
                                    'text': 'Há registro da avaliação de corrosão, deformações e torções da estrutura, '
                                            'utilizando a classificação de oxidação (Grau A, B, C e D) e indicando '
                                            'condições impeditivas para graus C e D?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '8. TORRE / FUNDAÇÕES / ESTAIS',
                                    'number': '8.4',
                                    'text': 'As fundações em concreto foram avaliadas por esclerometria quando '
                                            'aplicável, com índice médio ≥ 23 ou encaminhamento à engenharia quando '
                                            'abaixo desse limite?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '9. SISTEMA DE PROTEÇÃO CONTRA DESCARGAS ATMOSFÉRICAS (SPDA)',
                                    'number': '9.1',
                                    'text': 'O SPDA foi inspecionado (captor, cabos de descida, conexões, caixas de '
                                            'inspeção e aterramento), com registro fotográfico e medição de '
                                            'resistência elétrica quando previsto?',
                                    'requirement': '',
                                    'recommendation': ''}]},
                        {'name': 'PLANEJAMENTO EXECUÇÃO',
                         'items': [{'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.1',
                                    'text': 'Todos os trabalhos em altura devem ser supervisionados, com '
                                            'acompanhamento de um trabalhador no nível do solo.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.2',
                                    'text': 'Nas atividades de manutenção onde são necessários dois executores '
                                            'simultâneos na torre, por exemplo, posicionamento dos sensores (1 '
                                            'executor no topo e outro no datalogger), há uma terceira pessoa em nível '
                                            'de solo? Os mesmos não se encontram sobrepostos.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.3',
                                    'text': 'A equipe está dimensionada corretamente para a atividade, onde o '
                                            'encarregado/responsável está dedicado na supervisão?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.4',
                                    'text': 'Precedido de uma Análise Preliminar de Risco (APR), que deve considerar, '
                                            'conforme item da NR35 35.5.5.1:\n'
                                            'a) O local em que os serviços serão executados e seu entorno; \n'
                                            'b) O isolamento e a sinalização no entorno da área de trabalho; Definição '
                                            'dos pontos de ancoragem;\n'
                                            'c) O estabelecimento dos sistemas e pontos de ancoragem;\n'
                                            'd) as condições meteorológicas adversas; Isolamento e sinalização;\n'
                                            'e) a seleção, inspeção, forma de utilização e limitação de uso dos '
                                            'sistemas de proteção coletiva e individual, atendendo às normas técnicas '
                                            'vigentes, às orientações do fabricante ou projetista e aos princípios da '
                                            'redução do impacto e dos fatores de queda; \n'
                                            'f) os trabalhos simultâneos que apresentem riscos específicos;\n'
                                            'g) Planejamento para situações de emergência;\n'
                                            'h) o atendimento aos requisitos de segurança e saúde contidos nas demais '
                                            'normas regulamentadoras;\n'
                                            'i) os riscos adicionais;\n'
                                            'j) as condições impeditivas;\n'
                                            'k) as situações de emergência e o planejamento do resgate e primeiros '
                                            'socorros, de forma a reduzir o tempo da suspensão inerte do trabalhador;\n'
                                            'l) a necessidade de sistema de comunicação; e\n'
                                            'm) a forma da supervisão.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.5',
                                    'text': 'Precedido de uma inspeção de pré-uso (checklist) de todos os EPIs, '
                                            'ferramentas e equipamentos, que serão utilizados. No checklist de '
                                            'inspeção devem ser indicadas as condições impeditivas para a sua '
                                            'utilização, os itens não conformes devem ser imediatamente substituídos.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.6',
                                    'text': 'Nas atividades rotineiras de trabalho em altura que possuam procedimento '
                                            'operacional, a análise de risco pode estar inserida neste, no entanto, '
                                            'qualquer alteração em relação às condições e cenários considerados no '
                                            'procedimento, este fica invalidado e deve ser realizada nova análise de '
                                            'risco e emissão de Permissão de Trabalho',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.7',
                                    'text': 'O procedimento operacional das atividades rotineiras de trabalho em '
                                            'altura devem conter, no mínimo, conforme item 35.5.6.1:\n'
                                            'a) o detalhamento da tarefa;\n'
                                            'b) as medidas de prevenção características à rotina; \n'
                                            'c) as condições impeditivas; \n'
                                            'd) Medidas de controle dos riscos características à rotina;\n'
                                            'e) os sistemas de proteção coletiva e individual necessários e;\n'
                                            'f) competências e responsabilidades.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.8',
                                    'text': 'As atividades não rotineiras de trabalhos em altura ou rotineiras que não '
                                            'possuam procedimento operacional devem: ser previamente autorizadas por '
                                            'uma Permissão de Trabalho, aprovada pelo responsável, disponibilizada no '
                                            'local de execução da atividade e, ao final, encerrada e arquivada de '
                                            'forma a permitir sua rastreabilidade;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.9',
                                    'text': 'Todos os executores da atividade devem participar na elaboração da '
                                            'Análise Preliminar de Risco e da Permissão de Trabalho, que deve  ser '
                                            'realizada no local de execução da atividade;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.10',
                                    'text': 'Os relatórios técnicos de manutenção preventiva da TME incluem, como '
                                            'anexos mínimos, registros fotográficos, medições de tensão dos estais, '
                                            'esclerometria, torque e resistência de aterramento?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '1. DOCUMENTAÇÃO',
                                    'number': '1.11',
                                    'text': 'Os certificados de calibração dos instrumentos de medição utilizados na '
                                            'atividade estão válidos e arquivados junto à documentação da torre?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.1',
                                    'text': 'Precedido por verificação se isolamento e sinalização estão implantados '
                                            'conforme definido na Análise de Riscos e/ou Permissão de Trabalho ou no '
                                            'procedimento operacional;',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.2',
                                    'text': 'Precedido da medição / verificação da pressão arterial de todos os '
                                            'executores do trabalho em altura.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.3',
                                    'text': 'A Permissão de Trabalho deve conter:\n'
                                            'a)\tRequisitos mínimos a serem atendidos para a execução dos trabalhos;\n'
                                            'b)\tDisposições e medidas estabelecidas na Análise Preliminar de Risco;\n'
                                            'c)\tRelação de todos os envolvidos e suas autorizações.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.4',
                                    'text': 'A Permissão de Trabalho deve ter validade limitada à duração da '
                                            'atividade, restrita ao turno de trabalho, podendo ser revalidada pelo '
                                            'responsável pela aprovação nas situações em que não ocorram mudanças nas '
                                            'condições estabelecidas ou na equipe de execução.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.5',
                                    'text': 'Antes da escalada é verificada a ausência de descargas atmosféricas na '
                                            'região, garantindo intervalo mínimo de 30 minutos desde o último raio e '
                                            'raio de 48 km sem novas ocorrências?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.6',
                                    'text': 'A superfície da torre, degraus e pontos de apoio não apresentam umidade '
                                            'excessiva ou condição escorregadia; em caso positivo a atividade é '
                                            'suspensa?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '2. PRÉ-OPERAÇÃO',
                                    'number': '2.7',
                                    'text': 'Para torres com alimentação 220 V em sua estrutura, foi realizado o '
                                            'bloqueio LOTO, instalada a identificação de bloqueio por todos os '
                                            'envolvidos e confirmada a ausência de tensão com instrumento calibrado?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. INSPEÇÃO E MANUTENÇÃO',
                                    'number': '3.1',
                                    'text': 'Durante a execução da montagem/desmontagem da torre, o guincho utilizado '
                                            'para elevação dos módulos está posicionado após o primeiro bloco de '
                                            'ancoragem, a uma distância mínima entre 20 e 30 metros?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. INSPEÇÃO E MANUTENÇÃO',
                                    'number': '3.2',
                                    'text': 'Caso o item 3.1 sejá aplicável foi realizada a RAC de Içamento?',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. INSPEÇÃO E MANUTENÇÃO',
                                    'number': '3.3',
                                    'text': 'Durante a realização de atividades em altura na TME, a velocidade do '
                                            'vento deve ser monitorada com anemômetro portátil, caso ultrapasse 40 '
                                            'km/h a atividade deve ser interrompida,de acordo com NR-35.',
                                    'requirement': '',
                                    'recommendation': ''},
                                   {'section': '3. INSPEÇÃO E MANUTENÇÃO',
                                    'number': '3.4',
                                    'text': 'O trabalhador quando realiza escalada em estrutura TME está devidamente  '
                                            "ancorado com o talabarte ''Y'' cada um em uma treliça? Mantendo sempre os "
                                            'três pontos de fixação e fator de queda "0"?',
                                    'requirement': '',
                                    'recommendation': ''}]}],
             'item_count': 53},
 'rac_heavy_vehicle': {'title': 'RAC — Movimentação e Operação de Equipamentos e Veículos Pesados',
                       'short': 'Movimentação e Operação de Equipamentos e Veículos Pesados',
                       'icon': 'mi-truck',
                       'prefix': 'RAC-VP',
                       'revision': 'Rev. 1\nMaio/2023',
                       'source_file': 'Movimentação e Operação de Equipamentos e Veículos Pesados.xlsx',
                       'response_mode': 'atende',
                       'groups': [{'name': 'PESSOAS',
                                   'items': [{'section': '1. SAÚDE',
                                              'number': '1.1',
                                              'text': 'Os exames ocupacionais vigentes para comprovar a aptidão para '
                                                      'realizar atividades de movimentação e operação de equipamentos '
                                                      'e veículos pesados e o Atestado de Saúde Ocupacional (ASO) '
                                                      'estão válidos e aprovados no SGF (Sistema de Gestão de '
                                                      'Fornecedores)?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. SAÚDE',
                                              'number': '1.2',
                                              'text': 'Os ASOs para movimentação e operação de equipamentos e veículos '
                                                      'pesados  inclui, em adição ao exame clínico básico, e os '
                                                      'seguintes exames complementares: acuidade visual, '
                                                      'eletroencefalograma, eletrocardiograma, glicemia em jejum, '
                                                      'hemograma completo e espirometria?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. SAÚDE',
                                              'number': '1.3',
                                              'text': 'Os exames ocupacionais e a sistemática de avaliação fazem parte '
                                                      'do PGR (Plano de Gerenciamento de Riscos) e PCMSO (Plano de '
                                                      'Controle Médio de Saúde Ocupacional), conforme NR-1 e NR-7?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. SAÚDE',
                                              'number': '1.4',
                                              'text': 'A avaliação dos exames ocupacionais, a definição da aptidão '
                                                      'para realizar atividades que envolvam movimentação e operação '
                                                      'de equipamentos e veículos pesados e a emissão do Atestado de '
                                                      'Saúde Ocupacional (ASO) são realizadas por médico do trabalho '
                                                      'habilitado?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. CAPACITAÇÃO',
                                              'number': '2.1',
                                              'text': 'Todo coempreendedor ou terceiro que movimentam equipamentos e '
                                                      'veículos pesados devem comprovar habilitação específica na '
                                                      'categoria requerida pelo Código Nacional de Trânsito para o '
                                                      'tipo de equipamento / veículo conforme Lei Nº 12.452, '
                                                      '21/07/2011. Art. 143 a 145?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. CAPACITAÇÃO',
                                              'number': '2.2',
                                              'text': 'Os executores que movimentam e/ou operam equipamentos e '
                                                      'veículos pesados devem realizar e serem aprovados em '
                                                      'treinamento teórico e pratico conforme anexo II, da NR-12, com '
                                                      'conteúdo geral e específico, a '
                                                      'saber:                                                            '
                                                      'a) descrição e identificação dos riscos associados com cada '
                                                      'máquina e as\n'
                                                      'proteções específicas;\n'
                                                      'b) funcionamento das proteções;\n'
                                                      'c) circunstâncias em que uma proteção pode ser removida;\n'
                                                      'd) ações caso uma proteção foi danificada ou se perdeu sua '
                                                      'função;\n'
                                                      'e) os princípios de segurança na utilização da máquina;\n'
                                                      'f) segurança para riscos mecânicos, elétricos e outros '
                                                      'relevantes;\n'
                                                      'g) método de trabalho seguro;\n'
                                                      'h) permissão de trabalho;\n'
                                                      'i) sistema de bloqueio de funcionamento da máquina.\n'
                                                      '- Em adição para Equipamentos Motrizes ou Autopropelidos:\n'
                                                      'a) noções sobre legislação de trânsito e de legislação de '
                                                      'segurança e\n'
                                                      'saúde no trabalho;\n'
                                                      'b) noções sobre acidentes e doenças decorrentes da exposição '
                                                      'aos riscos\n'
                                                      'existentes na máquina, equipamentos e implementos;\n'
                                                      'c) medidas de controle dos riscos: Equipamentos de Proteção '
                                                      'Coletiva -\n'
                                                      'EPCs e Equipamentos de Proteção Individual - EPIs;\n'
                                                      'd) inspeção, regulagem e manutenção com segurança;\n'
                                                      'e) procedimentos em situação de emergência;\n'
                                                      'f) noções sobre prestação de primeiros socorros.\n'
                                                      'A etapa prática deve ser supervisionada e documentada?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. CAPACITAÇÃO',
                                              'number': '2.3',
                                              'text': 'Os executores que movimentam e/ou operam equipamentos e '
                                                      'veículos pesados serão considerados capacitados e habilitados '
                                                      'se todas as capacitações estiverem válidas e aprovadas no SGF?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. CAPACITAÇÃO',
                                              'number': '2.4',
                                              'text': '12.16.10. A organização deve estabelecer cartão de '
                                                      'identificação com nome, função e fotografia dando abrangência '
                                                      'da autorização de cada trabalhador?',
                                              'requirement': '',
                                              'recommendation': ''}]},
                                  {'name': 'INSTALAÇÕES E EQUIPAMENTOS',
                                   'items': [{'section': '1. EPI',
                                              'number': '1.1',
                                              'text': 'Os EPIs para proteção para movimentação e operação de '
                                                      'equipamentos e veículos pesados devem ser:\n'
                                                      '- Certificados, ou seja, com CA e atendendo às normas '
                                                      'aplicáveis;\n'
                                                      '- Adequados para a utilização pretendida;\n'
                                                      '- Utilizados considerando os limites de uso;\n'
                                                      '- Ajustados ao peso e à altura do trabalhador.',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. EPI',
                                              'number': '1.2',
                                              'text': 'Operação interna:\n'
                                                      'a) Óculos de '
                                                      'segurança;                                                                                  '
                                                      'b) Protetor '
                                                      'auricular;                                                                              '
                                                      'c) Calçado de segurança com '
                                                      'biqueira;                                                    d) '
                                                      'Cinto de segurança;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. EPI',
                                              'number': '1.3',
                                              'text': 'Operação externa:\n'
                                                      'a) Óculos de '
                                                      'segurança;                                                                                  '
                                                      'b) Protetor '
                                                      'auricular;                                                                           '
                                                      'c) Colete refletivo ou tira refletiva para '
                                                      'sinalização;                                                                                        '
                                                      'd) Chapéu ou boné tipo árabe ou legionário contra o '
                                                      'sol;                   e) Luva de '
                                                      'proteção;                                                                                  '
                                                      'f) Calçado de segurança com '
                                                      'biqueira;                                                    g) '
                                                      'Capacete de proteção com '
                                                      'jugular;                                         h) Perneira de '
                                                      'couro / '
                                                      'vaqueta;                                                               '
                                                      'i) Vestimenta de corpo inteiro com camisa manga comprida;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. EPC',
                                              'number': '2.1',
                                              'text': 'Os EPCs para proteção coletiva durante a movimentação e '
                                                      'operação de equipamentos e veículos pesados devem ser:\n'
                                                      '- Atender às normas aplicáveis;\n'
                                                      '- Adequados para a utilização pretendida;\n'
                                                      '- Utilizados considerando os limites de uso;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. EPC',
                                              'number': '2.2',
                                              'text': 'Operação interna:\n'
                                                      'a) Extintor de incêndio '
                                                      'ABC;                                                  \n'
                                                      'b) Sinal sonoro audível de ré;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. EPC',
                                              'number': '2.3',
                                              'text': 'Operação externa:\n'
                                                      'a) Proteção de partes '
                                                      'móveis;                                                               '
                                                      'b) Extintor de incêndio '
                                                      'ABC;                                                 \n'
                                                      'c) Sinal sonoro audível de '
                                                      'ré;                                                                      '
                                                      'd) Luzes auxiliares para atividades '
                                                      'noturna;                                      e) Cones e '
                                                      'correntes de sinalização e isolamento de área;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.1',
                                              'text': 'a) Ter certificação da cabine de operador contra capotamento e '
                                                      'contra queda de materiais?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.2',
                                              'text': 'b) Equipamentos com tara igual ou superior a 4.500 kg devem '
                                                      'possuir cabine climatizada e proteção contra incidência de '
                                                      'raios solares e intempéries?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.3',
                                              'text': 'c) Partes móveis e transmissões de força e os componentes '
                                                      'móveis a elas interligados, acessíveis ou expostos, desde que '
                                                      'ofereçam risco, devem possuir proteções físicas fixas, ou '
                                                      'móveis que impeçam o acesso por todos os lados, conforme '
                                                      'especificado na NR-12, itens 12.5.9, 12.5.9.1 e 12.5.9.2;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.4',
                                              'text': 'd) Mangueiras, tubulações e demais componentes pressurizados '
                                                      'devem ser localizados ou protegidos de tal forma que uma '
                                                      'situação de ruptura destes componentes e vazamentos de fluidos '
                                                      'não possa atingir pessoas;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.5',
                                              'text': 'e) Sinalização de segurança que indique claramente os riscos e '
                                                      'a parte da máquina associada, conforme especificado na NR-12, '
                                                      'item 12.12;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.6',
                                              'text': 'f) Pontos de articulação com potencial para esmagamento devem '
                                                      'possuir sinalização clara e visível dos perigos associados a '
                                                      'lesões e indicação do(s) ponto(s) de bloqueio;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.7',
                                              'text': 'g) Possuir retrovisores externos, alarme sonoro audível (acima '
                                                      'do ruído de fundo) acoplado ao sistema de câmbio quando operada '
                                                      'em marcha a ré, faróis, luz de ré e buzina audível;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.8',
                                              'text': 'h) Luzes auxiliares para atividade noturna;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.9',
                                              'text': 'i) Cinto de segurança para todos os ocupantes, se for o caso;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.10',
                                              'text': 'j) Extintor de incêndio ABC;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '3. EQUIPAMENTOS',
                                              'number': '3.11',
                                              'text': 'k) Placa de identificação conforme NR-12, item 12.12.7.',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.1',
                                              'text': 'a) Pontos de articulação com potencial para esmagamento devem '
                                                      'possuir sinalização clara e visível dos perigos associados a '
                                                      'lesões e indicação do(s) ponto(s) de bloqueio;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.2',
                                              'text': 'b) Possuir retrovisores externos, alarme sonoro audível (acima '
                                                      'do ruído de fundo) acoplado ao sistema de câmbio quando operada '
                                                      'em marcha a ré, luz de ré e buzina audível;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.3',
                                              'text': 'c) Caminhões basculantes devem possuir: \n'
                                                      '- Indicação posicionamento da báscula elevada / alto visual e '
                                                      'sonoro no painel – no caso de acionamento interno da báscula;\n'
                                                      '- limitador de velocidade e/ou bloqueio de deslocamento com a '
                                                      'báscula elevada;\n'
                                                      '- inclinômetro;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.4',
                                              'text': 'd) Caminhões-tanque que transportam combustíveis devem possuir '
                                                      'cabo com conector para interligação com a rede de aterramento '
                                                      'do tanque,dispositivo ou instalação para onde o combustível '
                                                      'será descarregado;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.5',
                                              'text': 'e) Luzes auxiliares para atividade noturna;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.6',
                                              'text': 'f) Extintor de incêndio ABC;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '4. VEÍCULOS PESADOS \n'
                                                         '(Os veículos pesados, em adição aos requisitos básicos e '
                                                         'obrigatórios exigidos pelo CONTRAN)',
                                              'number': '4.7',
                                              'text': 'g) Identificação capacidade de carga.',
                                              'requirement': '',
                                              'recommendation': ''}]},
                                  {'name': 'PLANEJAMENTO EXECUÇÃO',
                                   'items': [{'section': '1. DOCUMENTAÇÃO',
                                              'number': '1.1',
                                              'text': 'Toda movimentação interna e operação de equipamentos e veículos '
                                                      'pesados devem '
                                                      'ser:                                                                   '
                                                      'a) Planejada, organizada e executada por pessoas e equipes '
                                                      'capacitadas e autorizadas com identificação de fácil acesso '
                                                      'podendo ser crachá emitido pela empresa?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. DOCUMENTAÇÃO',
                                              'number': '1.2',
                                              'text': 'Precedida de uma Análise Preliminar de Risco (APR), específica '
                                                      'para atividades que deve considerar os seguintes '
                                                      'iténs:                                                                                                             '
                                                      'a) riscos inerentes à '
                                                      'atividade;                                                            '
                                                      'b) movimentação dos equipamentos até a frente de trabalho /\n'
                                                      'manutenção;                                                                                            '
                                                      'c) movimentação dos veículos pesados até a frente de trabalho '
                                                      '/\n'
                                                      'manutenção;                                                                                                  '
                                                      'd) movimentação e organização do trafego dos veículos pesados '
                                                      'na frente de trabalho / '
                                                      'manutenção;                                                          '
                                                      'e) interação entre os equipamentos e veículos pesados na frente '
                                                      'de trabalho / '
                                                      'manutenção;                                                                          '
                                                      'f) operação indivudual dos '
                                                      'equipamentos;                                                g) '
                                                      'a forma da '
                                                      'supervisão;                                                                              '
                                                      'h) '
                                                      'sinalizadores;                                                                                          '
                                                      'i) sistemas de comunicação '
                                                      'necessários;                                                      '
                                                      'j) isolamento e sinalização até e na frente de trabalho / '
                                                      'manutenção;                                                                                                  '
                                                      'k) condições impeditivas, inclusive '
                                                      'meteorológicas;                             l) planejamento '
                                                      'para situações de emergência.',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. DOCUMENTAÇÃO',
                                              'number': '1.3',
                                              'text': 'Precedida de uma inspeção de pré-uso (checklist), de todos os '
                                                      'equipamentos e veículos pesados que serão utilizados. De todos '
                                                      'os EPIs/EPCs e ferramentas, inclusive PEMTs que serão '
                                                      'utilizados. No checklist de inspeção devem ser indicadas as '
                                                      'condições impeditivas para a sua utilização, os itens não '
                                                      'conformes devem ser imediatamente substituídos',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. DOCUMENTAÇÃO',
                                              'number': '1.4',
                                              'text': 'Precedida de plano de manutenção, formal do cumprimento da '
                                                      'preventiva dos equipamentos e veículos pesaos, realizado por '
                                                      'profissional legalmente habilitato ou qualificado, conforme '
                                                      'disposto no item 12.11 da NR-12',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '1. DOCUMENTAÇÃO',
                                              'number': '1.5',
                                              'text': 'Plano de movimentação Deverá ser enviado previamente o plano de '
                                                      'movimentação, considerando a carga, níveis máximos de vento '
                                                      'durante movimentação, etapas de movimentação e todo '
                                                      'detalhamento necessário, incluindo emissão de ART',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. MANUTENÇÃO',
                                              'number': '2.1',
                                              'text': 'Todos os equipamentos e veículos pesados, devem possuir um '
                                                      'plano individual de manutenção preventiva baseado nos '
                                                      'requisitos técnicos, prazos e intervalos definidos pelos seus '
                                                      'fabricantes e nas condições e caracteríticas de uso e devem '
                                                      'estar aprovados e inseridos no SGF?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. MANUTENÇÃO',
                                              'number': '2.2',
                                              'text': 'A manutenção preventiva deve ser realiada por empresa '
                                                      'especializada e apresentar laudo técnico que indiquem todos os '
                                                      'servições realizados, peças / itens subistituídos, '
                                                      'recomendações para as preventivas posteriores e aprovação para '
                                                      'utilização?',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. MANUTENÇÃO',
                                              'number': '2.3',
                                              'text': 'Os planos de manutençao preventivas e seus registros devem '
                                                      'estar disponiveis para consulta (no SGF) conforme requerido na '
                                                      'NR-12, item 12.11.2.1;',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. MANUTENÇÃO',
                                              'number': '2.4',
                                              'text': 'Os equipamentos e veículos pesados que não estiverem com os '
                                                      'seus plano de manutenção preventiva realizados conforme '
                                                      'estabelecidos não serão atuorizados a operar.',
                                              'requirement': '',
                                              'recommendation': ''},
                                             {'section': '2. MANUTENÇÃO',
                                              'number': '2.5',
                                              'text': 'A existencia dos planos de manutenção preventiva realizados '
                                                      'conforme estabelecidos não elimina a necessidade de realizar as '
                                                      'inspeções de preuso (cheklists).',
                                              'requirement': '',
                                              'recommendation': ''}]}],
                       'item_count': 42}}


# V36.17.22 - official PDF RAC overrides
try:
    from .rac_pdf_sources import RAC_PDF_OVERRIDES
except ImportError:  # execução direta para diagnóstico
    from rac_pdf_sources import RAC_PDF_OVERRIDES

for _kind, _override in RAC_PDF_OVERRIDES.items():
    if _kind in RAC_MODULES:
        RAC_MODULES[_kind].update(_override)

RAC_KINDS = tuple(RAC_MODULES.keys())
