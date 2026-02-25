#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Mitigate fd-limit issues when launched from GUI contexts.
ulimit -n "${ZF_MAX_OPEN_FILES:-8192}" >/dev/null 2>&1 || true

mkdir -p logs
LOG="logs/webui_control.log"

echo "[$(date '+%F %T')] start requested" >> "$LOG"

export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
export ZF_BACKEND_BASE_URL="${ZF_BACKEND_BASE_URL:-http://127.0.0.1:8010}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"

if ! lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[$(date '+%F %T')] starting backend on :$BACKEND_PORT" >> "$LOG"
  nohup python3 -m uvicorn backend.app.main:app \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    > logs/webui_backend.out.log 2> logs/webui_backend.err.log < /dev/null &
  echo $! > logs/webui_backend.pid
fi

if ! lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[$(date '+%F %T')] starting streamlit on :$WEB_PORT" >> "$LOG"
  nohup python3 -m streamlit run app.py \
    --server.port "$WEB_PORT" \
    --server.headless true \
    --server.fileWatcherType none \
    --server.runOnSave false \
    > logs/webui_streamlit.out.log 2> logs/webui_streamlit.err.log < /dev/null &
  echo $! > logs/streamlit.pid
fi

# Wait briefly for streamlit to come up
for _ in $(seq 1 15); do
  if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

open "http://127.0.0.1:${WEB_PORT}"
echo "[$(date '+%F %T')] open browser http://127.0.0.1:${WEB_PORT}" >> "$LOG"
