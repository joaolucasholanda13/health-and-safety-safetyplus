#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERRO: execute como root: sudo ./ATUALIZAR_VPS.sh"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: Docker não está instalado nesta VPS."
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERRO: Docker Compose (docker compose) não está disponível."
  exit 1
fi

# Pode informar manualmente o diretório atual como primeiro argumento.
TARGET_DIR="${1:-}"
if [ -z "$TARGET_DIR" ]; then
  for candidate in \
    /opt/checklist-serena/Checklist_Serena_Web_V1_CORRIGIDA_2 \
    /opt/checklist-serena/Checklist_Serena_Web_V2 \
    /opt/safety-plus/current \
    /opt/safety-plus
  do
    if [ -f "$candidate/docker-compose.yml" ] && [ -f "$candidate/.env" ]; then
      TARGET_DIR="$candidate"
      break
    fi
  done
fi

if [ -z "$TARGET_DIR" ]; then
  echo "ERRO: não encontrei uma instalação existente do Safety Plus."
  echo "Para uma VPS nova, use: ./INSTALAR_VPS.sh"
  echo "Ou informe a pasta atual: ./ATUALIZAR_VPS.sh /caminho/da/instalacao"
  exit 1
fi

if [ ! -f "$TARGET_DIR/.env" ]; then
  echo "ERRO: arquivo .env não encontrado em $TARGET_DIR"
  exit 1
fi
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

BACKUP_DIR="${TARGET_DIR%/}/backups"
mkdir -p "$BACKUP_DIR"

echo "Safety Plus V36.22.1 - atualização VPS"
echo "Origem : $SOURCE_DIR"
echo "Destino: $TARGET_DIR"
echo

cd "$TARGET_DIR"

echo "[1/7] Salvando configuração..."
cp -a .env "$BACKUP_DIR/env_${STAMP}.backup"
chmod 600 "$BACKUP_DIR/env_${STAMP}.backup"

DB_IDS="$(docker compose ps --status running -q db)"
WEB_IDS="$(docker compose ps --status running -q web)"
if [ -z "$DB_IDS" ] || [ -z "$WEB_IDS" ]; then
  echo "ERRO: db e web precisam estar em execução para gerar os backups antes da atualização."
  echo "Inicie os serviços da instalação atual e execute a atualização novamente."
  exit 1
fi

echo "[2/7] Criando backup do PostgreSQL..."
SQL_BACKUP="$BACKUP_DIR/postgres_${STAMP}.sql"
if ! docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "${SQL_BACKUP}.partial"; then
  echo "ERRO: falha no backup do PostgreSQL. A atualização foi cancelada."
  exit 1
fi
if [ ! -s "${SQL_BACKUP}.partial" ]; then
  echo "ERRO: backup do PostgreSQL vazio. A atualização foi cancelada."
  exit 1
fi
mv "${SQL_BACKUP}.partial" "$SQL_BACKUP"

echo "[3/7] Criando backup dos PDFs/anexos/chave de push..."
# Preserve uploads in the old container before rebuilding it. This runs before
# the storage backup so the migrated library is also protected by that backup.
docker compose exec -T web python -c '
import os, shutil
from pathlib import Path
source = Path("/app/app/info_docs/momentos")
target = Path(os.getenv("STORAGE_DIR", "/app/storage")) / "safety_moments"
if not (target / "manifest.json").exists() and (source / "manifest.json").exists():
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file() and path.name != "manifest.json" and not (target / path.name).exists():
            shutil.copy2(path, target / path.name)
    shutil.copy2(source / "manifest.json", target / "manifest.json")
'
STORAGE_BACKUP="$BACKUP_DIR/storage_${STAMP}.tar.gz"
if ! docker compose exec -T web sh -c 'tar -C /app -czf - storage' > "${STORAGE_BACKUP}.partial"; then
  echo "ERRO: falha no backup do storage. A atualização foi cancelada."
  exit 1
fi
if ! tar -tzf "${STORAGE_BACKUP}.partial" >/dev/null; then
  echo "ERRO: backup do storage inválido. A atualização foi cancelada."
  exit 1
fi
mv "${STORAGE_BACKUP}.partial" "$STORAGE_BACKUP"

echo "[4/7] Atualizando o código sem sobrescrever .env nem dados..."
tar \
  --exclude='./.env' \
  --exclude='./storage' \
  --exclude='./backups' \
  -C "$SOURCE_DIR" -cf - . | tar -C "$TARGET_DIR" -xf -

chmod +x "$TARGET_DIR/entrypoint.sh" "$TARGET_DIR/ATUALIZAR_VPS.sh" "$TARGET_DIR/INSTALAR_VPS.sh" 2>/dev/null || true

cd "$TARGET_DIR"
echo "[5/7] Validando Docker Compose..."
docker compose config -q

echo "[6/7] Reconstruindo os containers..."
docker compose up -d --build --remove-orphans

echo "[7/7] Aguardando o sistema responder..."
HEALTH_FILE="$(mktemp "${TMPDIR:-/tmp}/safety_plus_health.XXXXXX")"
trap 'rm -f -- "$HEALTH_FILE"' EXIT
OK=0
for i in $(seq 1 24); do
  if docker compose exec -T web python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).read().decode())" >"$HEALTH_FILE" 2>/dev/null; then
    OK=1
    break
  fi
  sleep 5
done

echo
if [ "$OK" -eq 1 ]; then
  echo "ATUALIZAÇÃO CONCLUÍDA."
  cat "$HEALTH_FILE"
else
  echo "AVISO: os containers subiram, mas o health check não respondeu a tempo."
  echo "Últimos logs do web:"
  docker compose logs --tail=120 web || true
  docker compose ps || true
  exit 1
fi

echo
echo "Status:"
docker compose ps

echo
DOMAIN_VALUE="$(grep -E '^DOMAIN=' .env | tail -1 | cut -d= -f2- || true)"
if [ -n "$DOMAIN_VALUE" ]; then
  case "$DOMAIN_VALUE" in
    http://*|https://*) echo "Acesse: $DOMAIN_VALUE" ;;
    *) echo "Acesse: https://$DOMAIN_VALUE" ;;
  esac
fi

echo "Backups: $BACKUP_DIR"
