#!/bin/sh
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export ADMIN_USER="${ADMIN_USER:-admin}" ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}" ADMIN_NAME="${ADMIN_NAME:-Administrador}" APP_SECRET="${APP_SECRET:-teste-local-troque-em-producao}" SECURE_COOKIES="${SECURE_COOKIES:-false}"
python -m app.init_db
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
