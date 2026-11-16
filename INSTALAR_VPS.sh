#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${TARGET_DIR:-/opt/safety-plus}"
DOMAIN_VALUE="${1:-safetyplus.tech}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERRO: execute como root: sudo ./INSTALAR_VPS.sh [dominio]"
  exit 1
fi
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "ERRO: instale Docker + Docker Compose antes de continuar."
  exit 1
fi
if [ -e "$TARGET_DIR/.env" ]; then
  echo "ERRO: já existe uma instalação em $TARGET_DIR. Use ATUALIZAR_VPS.sh."
  exit 1
fi

mkdir -p "$TARGET_DIR"
tar --exclude='./.env' --exclude='./storage' -C "$SOURCE_DIR" -cf - . | tar -C "$TARGET_DIR" -xf -

rand_hex() { python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
}
rand_pass() { python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
}

APP_SECRET_VALUE="$(rand_hex)"
DB_PASSWORD_VALUE="$(rand_pass)"
ADMIN_PASSWORD_VALUE="$(rand_pass)"

cat > "$TARGET_DIR/.env" <<ENVEOF
DOMAIN=$DOMAIN_VALUE
APP_TIMEZONE=America/Sao_Paulo
SECURE_COOKIES=true
APP_SECRET=$APP_SECRET_VALUE
ADMIN_USER=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD_VALUE
ADMIN_NAME=Super Administrador
POSTGRES_DB=safetyplus
POSTGRES_USER=safetyplus
POSTGRES_PASSWORD=$DB_PASSWORD_VALUE
DATABASE_URL=postgresql+psycopg://safetyplus:$DB_PASSWORD_VALUE@db:5432/safetyplus
STORAGE_DIR=/app/storage
VAPID_SUBJECT=https://$DOMAIN_VALUE
ENVEOF
chmod 600 "$TARGET_DIR/.env"
chmod +x "$TARGET_DIR/entrypoint.sh" "$TARGET_DIR/ATUALIZAR_VPS.sh" "$TARGET_DIR/INSTALAR_VPS.sh"

cd "$TARGET_DIR"
docker compose config -q
docker compose up -d --build

echo
echo "Instalação iniciada. Aguarde o HTTPS do Caddy ficar disponível."
echo "URL: https://$DOMAIN_VALUE"
echo "Usuário inicial: admin"
echo "Senha inicial: $ADMIN_PASSWORD_VALUE"
echo "IMPORTANTE: guarde a senha acima e troque-a no primeiro acesso."
echo
echo "Status:"
docker compose ps
