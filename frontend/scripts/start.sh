#!/bin/sh
set -e

exec streamlit run app/main.py \
  --server.address "${FRONTEND_HOST:-0.0.0.0}" \
  --server.port "${FRONTEND_PORT:-8501}" \
  --browser.gatherUsageStats false
