#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"
LOG="logs/webui_control.log"

mkdir -p logs
echo "[$(date '+%F %T')] stop requested" >> "$LOG"

# First, kill by process pattern (more robust in app-launch context).
pkill -f "streamlit run app.py --server.port ${WEB_PORT}" >/dev/null 2>&1 || true
pkill -f "uvicorn backend.app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}" >/dev/null 2>&1 || true

if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  lsof -tiTCP:"$WEB_PORT" -sTCP:LISTEN | xargs -I{} kill "{}" || true
fi

if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  lsof -tiTCP:"$BACKEND_PORT" -sTCP:LISTEN | xargs -I{} kill "{}" || true
fi

echo "[$(date '+%F %T')] stop finished" >> "$LOG"
