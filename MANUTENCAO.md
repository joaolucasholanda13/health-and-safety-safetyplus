# Manutenção do Safety Plus

Preparado para a instalação existente em `/opt/safety-plus`, fora dos containers.
Não usa IA, não altera código nem publica versões. Não envia mensagens externas.

## Instalar na VPS

Depois de enviar `tools/maintenance.py` e `ops/maintenance/` para a instalação:

```bash
cd /opt/safety-plus
sudo bash ops/maintenance/install.sh
sudo systemctl start safetyplus-monitor.service
sudo systemctl start safetyplus-backup.service
sudo journalctl -u safetyplus-monitor.service -u safetyplus-backup.service -n 50
```

O monitor roda a cada minuto e o backup diariamente às 03h de São Paulo.
Por padrão, o monitor somente registra problemas no journal. Para habilitar
recuperação, configure `MAINTENANCE_AUTO_RESTART=1` em
`/etc/safetyplus-maintenance.conf`. A configuração é relida a cada execução.
Após três falhas consecutivas e somente com o banco saudável, pode tentar
reiniciar o web no máximo uma vez por hora. Não reinicia banco ou proxy;
falha exclusiva no HTTPS não provoca reinício. A próxima execução confere o resultado.
Uma trava evita que recuperação e backup ocorram simultaneamente.

## Backups e limites

Backups ficam em `/var/lib/safetyplus-maintenance/backups`, com acesso restrito,
fora do container. Incluem PostgreSQL e todo o storage (inclusive chaves,
assinaturas e PDFs); não incluem `.env`. O deploy existente mantém seu próprio
backup de configuração. Não são enviados para outro servidor.

O robô valida o catálogo PostgreSQL e lê integralmente o arquivo de storage.
Isso não equivale a testar uma restauração. Banco e anexos são copiados em
sequência com o sistema online; não constituem um snapshot transacional conjunto.
Uma restauração real deve ser ensaiada em ambiente isolado, nunca em produção.

Backups completos recebem manifesto; tentativas incompletas ficam com sufixo
`.partial`. Não há exclusão automática nem retenção configurada: acompanhe o disco
e defina armazenamento externo e retenção antes de uso prolongado. O monitor
registra atenção a partir de 85% de uso, e backups não começam com menos de 2 GiB livres.
Alertas por mensagem e revisão de erros por IA ainda não estão implementados.
O acesso ao Docker exige privilégios equivalentes aos de administrador da VPS.

## Desativar

```bash
sudo systemctl disable --now safetyplus-monitor.timer safetyplus-backup.timer
```

Isso impede novas execuções agendadas; serviços já em andamento terminam normalmente.
Nenhum backup é apagado.

## Teste manual na VPS em 16/11/2026

Executado no host `srv2137804`, sem instalar os timers e com
`MAINTENANCE_AUTO_RESTART=0`. Monitor antes e depois do backup confirmou web,
PostgreSQL e HTTPS saudáveis. Backup real de aproximadamente 394 MiB gerado em
`/var/lib/safetyplus-maintenance-test/backups/20261116T153410323674Z`, com catálogo
PostgreSQL e leitura integral do tar validados. Restauração não executada.
Os timers de monitoramento e backup permaneceram inativos. O código do teste
foi extraído em diretório temporário; a instalação permanente continua pendente.

## Integração com o painel DEV

Em **DEV → Monitoramento → Robô de manutenção** é possível consultar o estado
externo e os últimos 20 backups concluídos. A aba Backup contém um link para esse
acompanhamento, sem duplicar as funções de backup interno.

O supervisor publica somente metadados em
`/var/lib/safetyplus-maintenance/public/status.json`. O Compose monta apenas
essa pasta, em modo de leitura, em `/app/maintenance-status`. Nunca monte a pasta
inteira de backups nem o socket do Docker no serviço web. Após atualizar uma
instalação existente, execute novamente o instalador do supervisor e recrie o
serviço web para aplicar a montagem. Isso é uma etapa de publicação separada.

No teste local sem supervisor, o painel mostra **Não conectado**. Para consultar
um resumo local já existente, defina `MAINTENANCE_STATUS_FILE` com seu caminho
antes de iniciar `INICIAR_TESTE_LOCAL.sh`. Nenhuma conexão automática à VPS é feita.
Registros com mais de três minutos são identificados como desatualizados.
Esta integração é de consulta: não ativa timers, não reinicia serviços nem
permite executar comandos pelo painel.

## Ativação em produção em 16/11/2026

Supervisor instalado permanentemente em `/opt/safety-plus/tools/maintenance.py`.
Timers de monitoramento e backup habilitados. Recuperação automática desabilitada.
Primeiro backup concluído: `20261116T154307896346Z`. Integração do painel
confirmada com resumo real, arquivo público somente leitura e versão
`2026.11.16.2`. Teste local continua independente da VPS.

## Testes automáticos de APRs, PTs, checklists e RACs

O comando local `.venv/bin/python tools/module_checks.py` executa os quatro grupos
com SQLite, anexos e credenciais sintéticos em diretórios temporários. Confere
PDFs de APR, sete PTs e checklists configurados, regras de assinatura e finalização
já cobertas pela suíte. RACs incluem modelos oficiais e cálculos de aderência.
Não testa todos os cliques do navegador nem substitui a conferência visual.

Na VPS, `systemctl start safetyplus-tests.service` executa a rotina externa.
O timer agenda diariamente às **02h de São Paulo**. Cada grupo usa um container
novo com a imagem web, sem rede, sem privilégios adicionais, filesystem somente
leitura, usuário sem privilégios e limites de CPU/memória. Só são montadas as
pastas de código `app`, `tests` e `tools`, em modo leitura: nenhum volume de banco,
anexos, `.env` ou socket Docker é entregue ao container. Resultados detalhados
ficam em `/var/lib/safetyplus-maintenance/module-tests.log` e o resumo no painel
DEV. Falhas e timeout são registrados como falha, não corrigem nem publicam código.
As execuções compartilham a trava da manutenção para evitar concorrência com backup.
Durante os testes, o monitor pode pular um ciclo; o painel exibe a idade do registro.
O arquivo de log é substituído a cada rodada, não cresce sem limite.
Para desativar somente os testes: `systemctl disable --now safetyplus-tests.timer`.

Ativação dos testes em 16/11/2026: primeira execução na VPS concluída em
25,8 segundos, com 35 testes aprovados (APR 7, PT 7, checklists 16, RAC 5).
Timer de testes habilitado para 02h de São Paulo. Logs completos ficam
restritos na VPS; o painel recebe apenas contagens e resultados.
