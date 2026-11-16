# Manual de Uso — Safety Plus

Versão do sistema documentada: **V36.22.5** (app 2026.11.16.5).
Este manual também está disponível dentro do sistema, em **Central de Ajuda → Como usar**.

---

## Sumário

1. [O que é o Safety Plus](#1-o-que-é-o-safety-plus)
2. [Perfis de acesso](#2-perfis-de-acesso)
3. [Primeiros passos](#3-primeiros-passos)
4. [O Painel](#4-o-painel)
5. [APR — Análise Preliminar de Risco](#5-apr--análise-preliminar-de-risco)
6. [PT — Permissões de Trabalho](#6-pt--permissões-de-trabalho)
7. [RAC — Requisitos de Atividades Críticas](#7-rac--requisitos-de-atividades-críticas)
8. [Inspeções Prévias e LOTO](#8-inspeções-prévias-e-loto)
9. [Momento de Segurança e Integração](#9-momento-de-segurança-e-integração)
10. [Modo Offline](#10-modo-offline)
11. [Ferramentas SST, Recursos Externos e Sobre](#11-ferramentas-sst-recursos-externos-e-sobre)
12. [Central de Ajuda e Suporte](#12-central-de-ajuda-e-suporte)
13. [Administração (Administrador e Super Administrador)](#13-administração)
14. [Operação e manutenção do servidor](#14-operação-e-manutenção-do-servidor)
15. [Regras de ouro e problemas comuns](#15-regras-de-ouro-e-problemas-comuns)

---

## 1. O que é o Safety Plus

Aplicativo web (instalável como PWA) para gestão de Saúde e Segurança do Trabalho em campo. Substitui formulários em papel por documentos digitais com assinatura na tela, geração de PDF no modelo oficial e rastreabilidade completa.

| Módulo | Para que serve |
|---|---|
| **APR** | Analisar etapas, perigos, riscos e controles da atividade; coletar assinatura da equipe e aprovação do líder. Vigência de 7 dias. |
| **PT** | Permissão de Trabalho para atividades críticas (7 tipos). Vale só no dia em que é iniciada. |
| **RAC** | Checklists de Requisitos de Atividades Críticas (8 tipos) com plano de ação. |
| **Inspeções** | Checklists de equipamentos e veículos, e formulário de LOTO. |
| **Momento de Segurança** | Registro do DSS com lista de presença e biblioteca de materiais. |
| **Dashboard** | Indicadores de risco por módulo, site e período. |
| **Modo Offline** | Trabalho sem internet com envio automático depois. |
| **Central de Ajuda** | Manual, chamados de erro/melhoria. |

---

## 2. Perfis de acesso

| Perfil | O que vê e faz |
|---|---|
| **Usuário** | Cria e assina documentos; vê apenas os que criou ou em que participa. |
| **Administrador** | Tudo do Usuário + aprova APRs, atende solicitações, vê documentos dos **sites do seu escopo**. |
| **Super Administrador** | Todos os sites. Cadastra colaboradores, acessos, empresas, configura notificações; pode filtrar a visão por cluster. |

> Cada pessoa usa **o próprio login**. As assinaturas ficam registradas no nome de quem está logado.

---

## 3. Primeiros passos

### 3.1 Entrar
1. Abra o endereço do Safety Plus no navegador ou no app instalado.
2. Informe usuário e senha → **Entrar**.
3. Esqueceu a senha? Peça ao Super Administrador (Administração → Colaboradores → Acessos ao sistema).

### 3.2 Instalar como aplicativo
- **Android/computador (Chrome):** Minha Conta → **Instalar Safety Plus**.
- **iPhone (Safari):** Compartilhar → **Adicionar à Tela de Início**.

O app instalado é o mesmo sistema, sem barra de endereço, e é onde o modo offline funciona melhor.

### 3.3 Notificações
Minha Conta → Notificações → **Ativar neste aparelho** → permitir no navegador → escolher tipos → **Salvar preferências** → **Enviar teste**.
O sino no topo mostra avisos dentro do sistema; o ponto vermelho indica não lidos. Tipos marcados “Desativado pela Administração” foram desligados para todos.

### 3.4 Trocar senha
Minha Conta → senha atual + nova (mínimo 8 caracteres) → Salvar. Ao trocar a senha, as sessões antigas são encerradas.

### 3.5 Ler QR Code
O ícone de QR no topo abre a câmera e leva direto à tela correspondente (ex.: assinatura de APR). Se não abrir, libere a permissão de câmera no navegador.

---

## 4. O Painel

Tela inicial (`/`). Mostra:

- **Assinaturas pendentes para você** e **Aguardando sua aprovação** (no topo).
- Resumo semanal de documentos.
- **Lista de documentos** com busca por código, atividade, site ou empresa e filtros por tipo, situação, período, criador, cluster e site.

**Botão de ação por situação:**

| Situação | Ação |
|---|---|
| Rascunho | Continuar |
| Coletando assinaturas | Assinaturas |
| Aguardando aprovação | Aprovar (líder) |
| PT iniciada | Encerrar PT |
| PT pendente de encerramento | Encerrar PT (com observação) |
| Finalizada | PDF, Compartilhar, Mais ações |

### PDF
Documento finalizado → ícone de PDF para visualizar; **Abrir externamente** para baixar; **Compartilhar** para enviar (WhatsApp, e-mail). Para APR com PTs, use **PTs / Dossiê → Gerar dossiê completo** (APR + PTs em um arquivo).

---

## 5. APR — Análise Preliminar de Risco

### 5.1 Criar
Menu **APR → Nova APR**.

1. **Dados gerais:** Cluster/Site, atividade, hora, telefones, canal de rádio.
2. **Etapas** (até 20): para cada uma, perigos, riscos, **severidade (A alta, B média, C baixa — obrigatória)** e medidas de controle. Em perigo/risco use *Selecionar*, *Digitar* ou *Voz*.
3. **Checklist** de 24 itens: Sim / Não / N/A.
4. **Atividade crítica:** marque Sim para vincular PTs.
5. **Equipe** (até 24): busque por CPF ou nome, ou leia o QR do integrante.
6. **Aprovador:** escolha o líder responsável.
7. **Próxima etapa:** “Preencher PTs” (atividade crítica) ou “Coletar assinaturas”.

*Salvar rascunho* funciona a qualquer momento (também guarda no aparelho). Validade: **7 dias corridos**.

> ⚠ **Regra do NÃO:** resposta **Não** no checklist bloqueia a APR (sem PTs, assinaturas, aprovação ou PDF). Corrija a condição em campo e troque para Sim. Não use N/A para contornar condição insegura.

### 5.2 Assinaturas da equipe
Uma coleta única vale para a APR e todas as PTs vinculadas.

- **Por QR Code:** responsável mostra o QR geral; cada integrante lê, confere a APR completa, seleciona o nome, digita o CPF, marca “Li a APR e estou de acordo”, rubrica e confirma.
- **Presencial:** a pessoa assina na tela do aparelho do responsável.
- Acompanhe a lista; com todos assinados → **Enviar para aprovação**.
- Para corrigir algo: **Cancelar coleta** (descarta as assinaturas).

### 5.3 Aprovação (líder)
Painel → *Aguardando sua aprovação* → confere APR e PTs (somente leitura) → rubrica → **Aprovar**. APR finalizada gera o dossiê PDF.
**Reprovar:** informe o motivo; o criador é avisado e pode corrigir e reenviar. Também é possível **trocar o aprovador**.

### 5.4 Depois de aprovada
| Ação | Onde | Observação |
|---|---|---|
| **Assinatura diária** | PTs / Dossiê → Assinar APR de hoje | Presença da equipe a cada dia; não permite dias futuros/passados. |
| **Vigência (7 dias)** | PTs / Dossiê | Linha do tempo com dias restantes; fora da vigência, criar nova APR. |
| **+ Integrante** | Painel → APR finalizada | Cria pendência para a conta vinculada ao integrante, que assina autenticado; gera nova versão preservando a anterior. |
| **+ Observação** | Painel → APR finalizada | Registra mudança de cenário/novo risco em folha própria no PDF. |
| **Anexar outro tipo de PT** | PTs / Dossiê → “Adicionar outro tipo” | Só em APR vigente e aprovada. |
| **Duplicar** | Mais ações → Duplicar como nova APR | Opção de copiar a equipe. |
| **Salvar como modelo** | Mais ações → Salvar como modelo | Modelos em **APR → Modelos de APR** (compartilhados com a equipe). |

---

## 6. PT — Permissões de Trabalho

### 6.1 Regras gerais
- Sete tipos: **Altura, Espaço Confinado, Intervenção Elétrica, Linha Viva, Supressão de Vegetação, Içamento de Carga, TME**.
- Checklist: **Sim** = atendido, **Não** = impeditivo, **N/A** = não se aplica. Só inicia com tudo em Sim/N/A.
- A PT **vale apenas no dia em que foi iniciada, até 23:59**. À meia-noite, PT aberta vira **Pendente de encerramento** e você é avisado.
- PT encerrada nunca é reaproveitada: emita uma nova no dia seguinte.

### 6.2 Fluxos
- **Junto com a APR** (atividade crítica): a APR abre uma PT após a outra; preencha e use “Concluir PT e ir para a próxima etapa”. Depois, coleta única de assinaturas.
- **PT do dia:** Painel → APR finalizada → **PTs / Dossiê** → *Emitir PT de hoje* → **+ Nova PT para hoje**.

### 6.3 Iniciar e encerrar
- **Iniciar:** dados gerais, descrição, trabalhadores, checklist completo, responsável de abertura + rubrica → **Iniciar PT** (horário do servidor; dados de execução ficam bloqueados).
- **Encerrar:** Painel → **Encerrar PT** → responsável + rubrica (se pendente, escreva a observação) → gera o PDF.
- **Excluir:** só rascunho sem assinatura, pelo criador ou administrador (lixeira em PTs / Dossiê).

### 6.4 Particularidades por tipo
| Tipo | Itens | Destaques |
|---|---|---|
| Altura | 17 | Tipos de trabalho (escada, andaime, cinto, linha de vida, PTA, corda, telhado); pressão arterial; NR-35; até 5 trabalhadores. |
| Espaço Confinado | 15 | Tipo de entrada; medições O₂ (19,5–23,0%), %LII, CO, H₂S; supervisor e vigia. |
| Elétrica | 16 | Abertura/encerramento com rubrica. |
| Linha Viva | 17 | Trabalho em linha energizada. |
| Vegetação | 22 | Até 5 trabalhadores. |
| Içamento | 20 | Seleção de equipamentos (guindaste, munck, talhas). |
| TME | 19 | — |

---

## 7. RAC — Requisitos de Atividades Críticas

Menu **RAC**. Oito tipos: Altura, Espaço Confinado, Eletricidade, Linha Viva, Supressão de Vegetação, Içamento de Carga, TME e Movimentação/Operação de Equipamentos e Veículos Pesados.

1. Escolha o tipo e preencha os dados gerais.
2. Responda cada item: **Atende / Não atende / N/A** (Linha Viva usa Sim/Não/N/A).
3. Cada **Não atende** exige plano de ação: ação, responsável e prazo.
4. Anexe **várias fotos** e **áudio/voz** como evidência por item.
5. Rubrica do responsável → **Finalizar RAC e gerar PDF**.

O histórico de RACs fica na própria tela, com filtros. Há também **modelo** em branco para cada tipo.

---

## 8. Inspeções Prévias e LOTO

Menu **Inspeções**. Cada período concluído fica bloqueado e o mesmo PDF é atualizado. Só se preenche o dia atual.

| Inspeção | Periodicidade | Itens |
|---|---|---|
| Veículo Pesado | Diária (dias da semana), foto opcional nos itens C/NC | — |
| Veículo Leve | Semanal (1ª a 5ª) | 24 |
| Talha Guincho | Diária | 16 |
| Kit de Trabalho em Altura | Diária, antes da subida | 10 |
| Climber Assist | Única | 15 |
| Cinto de segurança (estrutural) | Única | 16 |
| **LOTO** | Única | 17 + Parte 2 |

**LOTO:** dados gerais, dispositivos e fabricante; 17 itens (“Não atende” exige ação corretiva); Parte 2 com cada trabalhador afetado (busca, horário e assinatura) → Finalizar.

Há ainda o **PDF consolidado do dia** (`/inspecoes/dia-pdf`).

---

## 9. Momento de Segurança e Integração

Acessíveis em **Ferramentas SST**.

- **Momento de Segurança:** registre tema, pontos abordados, lista de presença com rubricas e rubrica do responsável; gera PDF com código próprio. Há lista de presença em PNG para uso em campo.
- **Biblioteca de Momentos:** materiais prontos (PDF) para conduzir o DSS; é possível abrir, ver miniaturas e (com permissão) adicionar/excluir materiais.
- **Integração de Segurança:** registra a integração de colaboradores, coleta assinaturas digitais e gera a ata em PDF.

---

## 10. Modo Offline

Menu **Modo Offline**.

**Preparar (com internet):** *Preparar este aparelho* e aguardar a barra completar. Ficam guardados os formulários, arquivos do app e a lista de colaboradores. Atualiza sozinho a cada 12 h com sinal. Use o app instalado, sem aba anônima.

**Trabalhar sem sinal:** os formulários abrem normalmente. Ao salvar aparece “Sem internet: guardado no aparelho”. Ao voltar o sinal a fila é enviada sozinha (ou toque **Enviar agora**). APR e PT soltas chegam como rascunho; RAC e inspeções seguem com a ação escolhida.

**APR concluída offline (“Concluir offline”):**
1. Preencha a APR e busque integrantes pelo nome; preencha PTs se crítica.
2. Cada integrante assina na tela e digita o próprio **CPF**.
3. O líder assina, digita a **senha** do Safety Plus e confirma a declaração.
4. **Guardar no aparelho.** Com internet o servidor confere e gera o PDF.

Se a senha do líder não conferir → vai para aprovação online. Se um CPF não conferir → fica em rascunho e aparece em **Para revisar**.

**Fila de envio / Para revisar:** leia a mensagem → **Abrir e corrigir** → **Já revisei**. *Descartar* apaga do aparelho sem enviar.

---

## 11. Ferramentas SST, Recursos Externos e Sobre

- **Ferramentas SST:** atalhos para plataformas externas (ERP Distrinox, Siclope, O.A.C), Integração de Segurança, Momento de Segurança.
- **Recursos externos:** contatos de emergência por unidade (hospitais, bombeiros 193, SAMU 192, polícia 190/191, Defesa Civil 199, órgãos ambientais). A lista usada depende do cluster/site da APR.
- **Sobre a Serena:** apresentação institucional, **Política de SST** e **Regras pela Vida** (PDFs).
- **Novidades:** histórico de versões e melhorias (`/novidades`).

---

## 12. Central de Ajuda e Suporte

Menu **Central de Ajuda**.

- **Como usar:** este manual, com busca e passo a passo ilustrado.
- **Nova solicitação:** *Reportar erro* ou *Sugerir melhoria* → módulo, tela, assunto, descrição, print (clique, arraste ou Ctrl+V) → **Enviar solicitação**.
- **Minhas solicitações:** acompanhe *Recebida → Em verificação → Concluída* e a resposta da equipe.
- **Recebidas** (administradores): filtre, mude a situação, encaminhe, escreva a resposta → **Salvar resposta e situação**. O contador no menu mostra o que está com você.

---

## 13. Administração

### 13.1 Colaboradores (Super Administrador) — `Administração → Colaboradores`
- **Novo colaborador:** nome, CPF (validado; avisa duplicidade), função, empresa e acesso (sem login / vincular conta existente / criar login com senha inicial). O CPF não pode ser alterado depois.
- **Editar / inativar / remover:** lápis na lista; desmarque *Colaborador ativo* para inativar. Remover apaga o cadastro, mas preserva documentos antigos.
- **Empresas → Excel:** baixe o modelo (Nome, CPF, Função, Login, Senha, Ativo, Perfil), preencha e importe. CPF existente é atualizado; senha em branco mantém a atual. *Baixar lista atual* exporta.
- **Acessos ao sistema:** novo acesso ou editar conta; perfil Usuário / Administrador (marque os **sites do escopo**) / Super Administrador; senha e situação.
- **Exclusão em massa:** selecione contas (ou “todas as comuns”), digite **EXCLUIR**. Documentos e PDFs são preservados; com assinatura pendente nada é apagado.

### 13.2 Consulta de colaborador
`Administração → Consulta de colaborador`: busque por nome ou CPF e veja documentos emitidos e participações, tipos mais gerados, severidade A/B/C, respostas NÃO, perigos, riscos, locais e últimos 12 meses.
**Mesmo nome, seleções diferentes:** aponta APRs da mesma atividade preenchidas de forma divergente, campo a campo. Administradores veem só o próprio escopo; cada consulta é registrada.

### 13.3 Dashboard operacional
Menu **Dashboard** (`/indicadores/riscos`): documentos por módulo, situação e site; ranking de perigos e riscos; filtros por cluster/site e período.

### 13.4 Documentos
- **Cancelar** documento aguardando aprovação (informe o motivo; permanece no histórico).
- **Excluir** rascunhos.
- **Histórico/versões** de cada documento.

### 13.5 Configurações de notificações
`Administração → Configurações de Notificações`: marque/desmarque os tipos de aviso disponíveis; tipos desativados ficam indisponíveis para todos.

### 13.6 Documentos automáticos
`/admin/documentos-automaticos`: tela de configuração de documentos gerados automaticamente.

---

## 14. Operação e manutenção do servidor

Resumo para a equipe técnica. Detalhes em [DEPLOY_VPS.md](DEPLOY_VPS.md) e [MANUTENCAO.md](MANUTENCAO.md).

**Arquitetura:** Docker Compose com **web (FastAPI)**, **PostgreSQL** e **Caddy** (HTTPS). Dados em `STORAGE_DIR` (assinaturas, PDFs, evidências, biblioteca, chave VAPID).

**Configuração (`.env`, base em `.env.example`):** `DOMAIN`, `APP_TIMEZONE`, `SECURE_COOKIES`, `APP_SECRET`, `ADMIN_USER/PASSWORD/NAME`, `POSTGRES_*`, `DATABASE_URL`, `STORAGE_DIR`, `VAPID_SUBJECT`. Gere valores fortes em produção; nunca versione o `.env`.

**Testes locais:** `INICIAR_TESTE_LOCAL.sh` (Linux/WSL) ou `.bat` / `.ps1` (Windows). Diagnóstico: `DIAGNOSTICO.bat`; correção de ambiente: `CORRIGIR_AMBIENTE.bat`.

**Publicar atualização:**
1. Montar pacote sem `.env`, credenciais, `.git`, `.venv`, dados de `storage` e backups.
2. Enviar à VPS e extrair em diretório temporário.
3. `bash ./ATUALIZAR_VPS.sh /opt/safety-plus` (gera backups de configuração, PostgreSQL e storage antes de recriar o container).
4. Validar containers e `/health`; conferir a versão efetiva (`storage/releases.json` tem prioridade sobre `app/releases.py`).

**Robô de manutenção (systemd):** monitor a cada minuto; backup diário às 03h (São Paulo); recuperação automática opcional (`MAINTENANCE_AUTO_RESTART=1`, máx. 1 reinício/hora, só com banco saudável). Backups ficam fora do container; **não há retenção automática nem cópia externa** — acompanhe o disco e restaure apenas em ambiente isolado.

**Testes automatizados:** pasta `tests/` (`pytest`), cobrindo APR, PTs, RACs, backups, senhas/sessões, assinaturas, offline, auditoria e scripts.

---

## 15. Regras de ouro e problemas comuns

**Regras de ouro**
1. Use sempre o seu login; nunca assine por outra pessoa.
2. Resposta **NÃO** = condição impeditiva. Corrija antes de avançar.
3. APR vale **7 dias**; PT vale **só no dia**, até 23:59.
4. Encerre a PT no mesmo dia para gerar o PDF.
5. Antes de ir a campo sem sinal, **prepare o aparelho** no Modo Offline.

**Problemas comuns**

| Sintoma | O que fazer |
|---|---|
| Botão de avançar bloqueado na APR/PT | Há resposta **Não** ou item obrigatório vazio; revise o checklist. |
| Não encontro a pessoa na equipe | Peça ao Super Administrador para cadastrá-la em Colaboradores. |
| Integrante não consegue assinar pelo celular | Precisa de login vinculado ao cadastro. |
| Câmera do QR não abre | Libere a permissão de câmera; use Chrome/Edge atualizados. |
| PDF não carrega | Use *Tentar novamente* na página com falha ou *Abrir externamente*; se persistir, abra uma solicitação. |
| PT aparece “Pendente de encerramento” | Abra *Encerrar PT* e escreva a observação de encerramento. |
| Item “Para revisar” no offline | Modo Offline → Fila de envio → *Abrir e corrigir*. |
| Não recebo avisos | Minha Conta → ativar notificações neste aparelho e conferir as preferências. |

**Suporte:** Central de Ajuda → Nova solicitação.
