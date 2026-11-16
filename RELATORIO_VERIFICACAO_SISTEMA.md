# Verificação do Safety Plus — 10/11/2026

## Visualização após finalizar documentos — 11/11/2026

Relato: tela inteiramente preta ao finalizar com Usuário/Administrador, em todos os tipos de documento, localmente e na VPS; Super Administrador/DEV funcionavam.

A finalização e as permissões foram exercitadas nos quatro perfis. Não foi reproduzida a tela preta integral descrita, nem encontrada uma regra de finalização que negasse acesso aos próprios documentos desses dois perfis. Foi comprovada uma inconsistência na abertura: sem `Accept: text/html` ou com `Accept: */*`, a rota retornava o PDF bruto ao plugin do navegador, em vez da tela interna. A mesma bateria de testes contra o pacote anterior apresentou 24 falhas por esse motivo.

Correções aplicadas:

- `/document/{id}/pdf` abre sempre o visualizador HTML; PDF bruto exige `raw=1`, já utilizado para compartilhar/abrir externamente. A entrega deixa de depender dos cabeçalhos de navegação do navegador/PWA.
- O carregamento aguarda a primeira página. Metadados e imagens têm limites de espera, mensagens de falha e ações de recuperação.
- Cada página que falhar apresenta uma mensagem e botão para tentar novamente. Sessão expirada, acesso recusado e resposta inesperada recebem mensagens próprias.
- Fallback de altura `100vh` para navegadores sem suporte a `100dvh`.

Validação: **40 testes locais aprovados**, incluindo 12 finalizações reais (três inspeções nos quatro perfis), PDF/metadados/PNG, 96 verificações negativas de acesso e oito cenários JavaScript. Chrome real confirmou renderização nos quatro perfis e recuperação visual em falha de PNG, PNG travado e metadados inválidos. Na imagem da VPS, 32 testes passaram e oito testes Node foram pulados por ausência de Node; esses oito passaram localmente.

Ajuste implantado na VPS com o serviço web saudável e 77 arquivos de código verificados pelo manifesto. Contagens de banco preservadas: 11 usuários, 1 documento, 9 participantes e 1 notificação. Backup: `/home/lucas.paiva/SafetyPlus/backups/deploy_20261111_113932_pdf`. Imagem anterior: `safety-plus-web:rollback-20261111-pdf.scpfya`.

A confirmação do desaparecimento da tela preta na conta/dispositivo relatados depende de repetir a operação nesse ambiente. No teste local, reiniciar o servidor carrega as mudanças; na VPS, atualizar a página carrega o novo visualizador.

## Implantação na VPS — 11/11/2026

Atualização concluída em `safetyplus-ub24`, instalação `/home/lucas.paiva/SafetyPlus`, projeto Compose `safetyplus`.

- Os 31 testes passaram localmente e na imagem preparada na VPS.
- Serviço web recriado e saudável; containers PostgreSQL e Caddy preservados.
- Confirmados 75 arquivos de código/templates/requisitos pelo manifesto e a rota de assinatura individual de novos integrantes ativa.
- Contagens anteriores e posteriores iguais: 11 usuários, 1 documento, 9 participantes, 1 notificação e nenhum chamado de suporte.
- Arquivos anteriores de storage preservados; os 67 arquivos da biblioteca de Momentos de Segurança foram comparados por SHA-256 e preservados.
- `.env`, arquivos Compose e Caddyfile permaneceram iguais aos anteriores à implantação.
- `/health` respondeu com `ok=true` e `/login` com HTTP 200 por HTTPS. A instalação utiliza `tls internal` do Caddy; a validação empregou a autoridade certificadora já existente na instalação, sem desativar a verificação TLS ou alterar certificados.

Site: `https://safetyplus.srna.co`.

Backup completo anterior à troca: `/home/lucas.paiva/SafetyPlus/backups/deploy_20261111_111335_integrantes` (dump PostgreSQL validado, storage, biblioteca, código e configurações). Imagem anterior preservada como `safety-plus-web:rollback-20261110-integrantes.o3nsio`.

O pacote havia sido enviado em 10/11; a ativação final não ocorreu naquele momento porque a revisão automática atingiu o limite de uso. A implantação efetiva e as verificações acima foram concluídas em 11/11.

## Inclusão de integrante com assinatura pela própria conta

Ao incluir outro integrante em uma APR finalizada, o sistema agora cria uma solicitação pendente para a conta ativa vinculada ao participante. A tela de inclusão não captura assinatura. A pessoa recebe a pendência no painel e nas notificações, consulta a APR e assina autenticada na própria conta; o solicitante, terceiros e administradores não podem assinar essa solicitação em seu lugar. O QR público também não substitui essa confirmação.

A APR atual permanece válida durante a espera. Somente após a assinatura é criada a nova versão, com a autoria da solicitação e da assinatura registradas no PDF. A versão anterior e seu PDF são preservados; PTs vinculadas e outras solicitações pendentes acompanham a versão vigente. Links anteriores continuam levando à solicitação correta e reenviar a assinatura não gera versões duplicadas.

Validação: 21 cenários isolados em `tests/test_apr_execution_member.py`, incluindo permissões, CSRF, conta inativa/vínculo alterado, notificações obrigatórias, dois pedidos sucessivos, falha de commit e geração real de assinatura PNG/PDF sem alterar o PDF anterior. Suíte geral atual: 31 testes, contando os testes que executam cenários adicionais em subprocessos.

## Correções aplicadas

Os oito itens abaixo foram tratados. O restante deste documento registra os achados da verificação inicial, antes das correções.

| Item | Correção |
| --- | --- |
| 1 — Backup completo | Inclui todas as tabelas existentes, inclusive chamados e imagens binárias, além de avatares, configurações, publicações e chave VAPID padrão de storage. Os ZIPs novos têm permissão restrita. |
| 2 — Restauração por usuário | Extrai somente anexos dos documentos efetivamente importados, em caminhos novos, remapeando as referências. Documentos ignorados e seus arquivos são preservados. |
| 3 — Assinaturas/evidências | Backup por usuário coleta referências aninhadas em `data_json`, incluindo assinaturas e evidências. A restauração avisa quando um backup antigo não contém anexos referenciados. |
| 4 — Inicialização Linux | Senha padrão passou para `admin123`; variáveis de ambiente informadas pelo operador são respeitadas. |
| 5 — Dependências Windows | Verifica todos os requisitos e versões declarados, sincroniza pacotes quando necessário e verifica imports, incluindo QR Code e Excel, além de `pip check`. |
| 6 — Sessões | Troca/redefinição de senha revoga sessões anteriores, incluindo importação Excel e CLI de DEV. A sessão atual é renovada quando pertence à conta alterada. |
| 7 — Atualização VPS | Consulta IDs dos containers, exige backups válidos antes de copiar código/reiniciar serviços, restringe permissões e retorna erro se o healthcheck falhar. |
| 8 — Integridade SQLite | Novas conexões aplicam chaves estrangeiras. As duas notificações órfãs foram removidas com backup consistente prévio; não restam violações de FK. |

Na restauração completa, os arquivos são preparados antes de alterar o banco. Falhas de instalação ou commit revertem os arquivos substituídos e a transação. A conta DEV responsável é preservada e a sessão recebe seu ID correto; as demais sessões anteriores à restauração são invalidadas. Backups antigos que omitam tabelas atualmente preenchidas são rejeitados para evitar perda ou atribuição incorreta de dados.

### Validação das correções

- `./.venv/bin/python -m unittest discover -s tests -v`: **30 testes aprovados**, incluindo um teste que executa dez cenários isolados de sessão.
- Testes de backup verificam imagens binárias, configurações, assinatura/evidência aninhada, colisões de caminho e ID, documentos ignorados, backups antigos e falhas simuladas de extração, instalação e commit.
- Testes dos scripts usam Docker simulado, sem deploy ou rede. Testes de reparo incluem WAL, idempotência e aborto se o backup falhar.
- Sintaxe dos scripts shell aprovada; análise AST dos 22 arquivos Python de aplicação/testes aprovada.
- Comparação do banco atual com o backup anterior ao reparo: somente `notifications` mudou, de 16 para 14 registros. As demais tabelas permaneceram iguais; `integrity_check=ok` e `foreign_key_check` vazio.

Backup anterior à limpeza: `storage/backups/antes_corrigir_notificacoes_20261110_164247_145374_e34e99bf.db`.

Para repetir a checagem de integridade sem modificar dados:

```sh
./.venv/bin/python -m app.repair_integrity --check
```

Os testes não executaram Windows, PostgreSQL real, deploy nem notificações push externas. Backups antigos não passam a conter arquivos que nunca foram exportados. O backup cobre a chave VAPID padrão em storage; uma chave configurada fora de storage por `VAPID_PRIVATE_KEY_FILE` exige preservação separada.

## Registro da verificação inicial

## Resultado

A aplicação iniciou e os testes de consulta e geração de PDFs passaram. Foram encontrados problemas de backup/restauração, inicialização local e revogação de sessões. Esta verificação não certifica todos os fluxos de negócio ou a instalação em produção.

Na verificação inicial, nenhum código da aplicação ou dado existente foi alterado. Os testes com escrita usaram bancos e pastas temporários em `/tmp`. As mudanças posteriores estão descritas na seção de correções acima.

## Problemas encontrados

### 1. Alta — “Backup completo” não inclui todos os dados persistentes

Local: `app/ti_tools.py:19`, `app/ti_tools.py:76`; tabelas adicionais em `app/main.py:8670` e `app/main.py:8753`.

O backup exporta somente `Base.metadata.sorted_tables`. As tabelas `support_tickets` e `support_images` são criadas por SQL direto e ficam fora desse metadata. Também são copiados apenas os diretórios `pdfs`, `signatures`, `evidence` e `custom_docs`: avatares, configurações JSON e a chave VAPID persistida na raiz de storage não entram no arquivo.

Reprodução: criado um chamado em banco temporário, gerado o ZIP e inspecionado `db.json`; `support_tickets` não estava presente. Em uma recuperação para outra instalação, chamados/imagens e configurações não são recuperados; perder a chave VAPID pode exigir nova inscrição dos dispositivos em push. Na restauração sobre instalação existente, as tabelas de suporte antigas também não são substituídas.

Correção sugerida: definir explicitamente todos os dados que compõem o backup completo, incluindo tabelas criadas fora do ORM e arquivos persistentes, com teste de ida e volta para uma instalação vazia.

### 2. Alta — Restaurar backup de usuário sobrescreve PDF de documento ignorado

Local: `app/ti_tools.py:191` (`restore_user`).

O importador ignora documentos cujo código já existe, mas depois extrai todos os arquivos do ZIP, sobrescrevendo os PDFs existentes desses mesmos documentos. Assim, os dados atuais ficam no banco enquanto o PDF pode voltar para uma versão antiga.

Reprodução em pasta temporária: backup com PDF antigo; atualização do arquivo atual; restauração do backup para o mesmo usuário. Resultado: `skipped=1`, mas o PDF atual foi substituído pelo antigo.

Correção sugerida: extrair somente arquivos dos documentos efetivamente importados e evitar colisão de caminhos.

### 3. Média — Backup por usuário omite assinaturas e evidências

Local: `app/ti_tools.py:87`.

O ZIP inclui os dados JSON dos documentos e os arquivos referenciados por `pdf_path`, mas não os arquivos de assinaturas ou evidências referenciados dentro de `data_json`. Restaurar em uma instalação vazia recupera referências para arquivos que não existem, comprometendo edição e regeneração fiel de PDFs.

Reprodução: documento temporário com `signature_image` apontando para arquivo existente; o ZIP gerado não continha a assinatura.

Correção sugerida: coletar as dependências de arquivo dos documentos, incluindo campos aninhados, e validar sua restauração.

### 4. Média — Inicialização local Linux falha em instalação limpa

Local: `INICIAR_TESTE_LOCAL.sh:7`; validação em `app/init_db.py:27`.

O script configura `ADMIN_PASSWORD=admin`, mas o inicializador exige pelo menos oito caracteres quando não há usuários. Com `set -e`, o script para antes de iniciar o servidor.

Reprodução: banco temporário vazio e senha `admin` produziram o RuntimeError previsto pela validação. O `.bat` usa `admin123`, que atende ao comprimento mínimo; este problema específico não se aplica a ele.

Correção sugerida: alinhar a configuração inicial à validação e permitir informar credenciais locais.

### 5. Média — Verificação de dependências do Windows pode aceitar ambiente incompleto

Local: `INICIAR_TESTE_LOCAL.bat:84` e `INICIAR_TESTE_LOCAL.bat:93`.

As verificações de importação não incluem `qrcode` e `openpyxl`, embora ambos estejam em `requirements.txt`. Em ambiente antigo com os outros pacotes presentes, o script ignora a instalação. Como `app/main.py` importa `qrcode` no início, a aplicação pode nem iniciar; a importação/exportação Excel também pode falhar sem `openpyxl`. A verificação tampouco detecta versões antigas de pacotes já instalados.

Constatação por leitura do código; o script Windows não foi executado neste ambiente Linux.

Correção sugerida: sincronizar as dependências ao mudar o requirements, em vez de considerar apenas a existência de alguns imports.

### 6. Média — Troca/redefinição de senha preserva sessões anteriores

Local: `app/main.py:8658`, `app/main.py:8466`, `app/main.py:2562`; verificação de sessão em `app/security.py:31`.

Esses fluxos atualizam o hash da senha, mas não acionam o mecanismo existente de revogação de sessões. Uma sessão já autenticada continua utilizável após a troca, inclusive quando a redefinição serve para recuperar uma conta comprometida.

Reprodução em banco temporário: após mudar o hash da senha, uma sessão com timestamp anterior ainda foi aceita por `current_user`.

Correção sugerida: invalidar sessões anteriores após troca/redefinição de senha, preservando ou renovando a sessão atual conforme o fluxo.

### 7. Média — Atualização da VPS continua após falha do backup de arquivos

Local: `ATUALIZAR_VPS.sh:71`.

O comando que salva storage termina com `|| true`. Se o tar falhar, a atualização prossegue mesmo com um arquivo de backup ausente ou incompleto. Além disso, a detecção de containers usa a saída tabular de `docker compose ps` com `grep -q .`; o cabeçalho pode ser interpretado como container em execução.

Constatação por leitura; Docker não está disponível neste ambiente.

Correção sugerida: interromper em falha de backup, validar o arquivo e consultar IDs de containers em execução com saída apropriada para scripts.

### 8. Baixa — Duas notificações com referências inválidas no banco atual

Local: `storage/checklist_serena.db`, tabela `notifications`; configuração do banco em `app/database.py:12`.

A leitura com SQLite em modo somente leitura identificou duas notificações órfãs e duas violações em `PRAGMA foreign_key_check`. Não foram encontrados documentos sem criador, JSON inválido ou documento finalizado sem PDF.

O engine SQLite não configura `PRAGMA foreign_keys=ON` para novas conexões. Isso permite persistir referências inválidas; os dados existentes devem ser saneados antes de habilitar a fiscalização e validar os fluxos de exclusão.

Correção sugerida: tratar as notificações órfãs pelo mecanismo de integridade existente e revisar a aplicação de integridade referencial no SQLite. Nenhuma correção de dados foi executada nesta revisão.

## Verificações concluídas

- Sintaxe dos 17 arquivos Python: aprovada por análise AST.
- Compilação dos 75 templates Jinja: aprovada.
- `pip check` no ambiente virtual existente: nenhuma dependência incompatível reportada.
- Sintaxe dos scripts shell de inicialização, instalação e atualização: aprovada.
- Servidor HTTP local com banco temporário: 295 consultas, abrangendo 59 rotas sem parâmetros de caminho, em cinco contextos (anônimo, Usuário, Administrador, Super Administrador e DEV). Nenhuma resposta 500; respostas 200/303/401/403 compatíveis com as verificações de acesso observadas.
- Login sem CSRF: rejeitado com HTTP 403. A varredura por perfis usou sessões de teste assinadas com uma chave exclusiva do ambiente temporário; isso não substitui um teste completo do login no navegador.
- Geração e abertura de PDFs dos 31 tipos testados, usando dados padrão: aprovadas. Não houve inspeção visual de cada página nem validação de todos os campos preenchidos.
- SQLite atual, aberto somente para leitura: `integrity_check=ok`; 46 documentos, nenhum JSON de documento inválido e nenhum documento finalizado sem arquivo PDF.
- Reprodução isolada das omissões de backup, sobrescrita de PDF na restauração e persistência de sessão após mudança de senha.

## Limites

Não foram executados deploy, Docker, PostgreSQL real, scripts Windows, navegação visual, notificações push externas ou testes completos de assinatura/aprovação/offline em dispositivos. Não foi encontrada suíte de testes automatizados no projeto. A pasta fornecida não é um repositório Git, portanto não foi possível comparar alterações com um histórico versionado.

Prioridade de correção: backup completo e restauração por usuário; em seguida, inicialização, dependências e revogação de sessões.
