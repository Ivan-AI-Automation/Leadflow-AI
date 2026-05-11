#!/bin/sh
set -e

mkdir -p "${UPLOAD_DIR:-/app/uploads}" "${EXPORT_DIR:-/app/exports}"

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi

exec uvicorn app.main:app \
  --host "${BACKEND_HOST:-0.0.0.0}" \
  --port "${BACKEND_PORT:-8000}"
