#!/bin/sh
set -eu

mkdir -p "${STORAGE_DIR:-/app/storage}"
python -m app.init_db

exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips='*'
