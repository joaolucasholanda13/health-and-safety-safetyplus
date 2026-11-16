# Publicação do Safety Plus

Dados confirmados em 12/11/2026:

- VPS de produção: `2.25.207.2` (hostname `srv2137804`).
- Usuário SSH: `root`.
- Chave local: `~/.ssh/id_ed25519_vps` (não copiar nem incluir em pacotes).
- Instalação: `/opt/safety-plus`.
- Site: https://safetyplus.tech.
- O alias SSH local `safetyplus-vps` aponta para `10.233.7.59`; esse endereço não respondeu nesta sessão. Usar o IP confirmado acima.

## Atualização

1. Preparar pacote do código, excluindo `.env`, credenciais, `.aws`, `.git`, `.agents`, `.codex`, `.venv`, dados de `storage`, backups e anexos locais.
2. Enviar o pacote para `/tmp` da VPS e extrair em um diretório temporário exclusivo.
3. Executar `bash ./ATUALIZAR_VPS.sh /opt/safety-plus` a partir do diretório extraído. O script preserva a biblioteca antiga antes de recriar o container e gera backups de configuração, PostgreSQL e armazenamento em `/opt/safety-plus/backups`.
4. Validar os containers e `https://safetyplus.tech/health`, além da biblioteca persistente em `STORAGE_DIR/safety_moments`.
5. Conferir a versão efetiva: `storage/releases.json` tem prioridade sobre `app/releases.py`. Ao publicar a nova versão, preservar o histórico existente.

Última publicação confirmada: **V36.22.4**, versão do aplicativo **2026.11.16.3**, em 16/11/2026. Testes isolados de APRs, PTs, checklists e RACs no supervisor: 35 testes passaram na VPS, agendados às 02h de São Paulo. Backup às 03h, monitoramento a cada minuto, recuperação automática desabilitada. Corrigido o PDF de veículo leve para sete dias, preservando identificação e não conformidades.

Cada envio requer uma solicitação do usuário; este registro não autoriza futuras publicações automaticamente.
