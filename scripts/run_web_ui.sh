#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs

export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
export ZF_BACKEND_BASE_URL="${ZF_BACKEND_BASE_URL:-http://127.0.0.1:8010}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"

if ! lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  nohup python3 -m uvicorn backend.app.main:app \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    > logs/webui_backend.out.log 2> logs/webui_backend.err.log &
  sleep 1
fi

python3 -m streamlit run app.py \
  --server.port "$WEB_PORT" \
  --server.headless true

