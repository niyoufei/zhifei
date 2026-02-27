#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"
WATCH_INTERVAL="${ZF_WATCHDOG_INTERVAL:-8}"
LOG_FILE="${ZF_WATCHDOG_LOG:-$ROOT/logs/webui_watchdog.log}"

mkdir -p "$ROOT/logs"

is_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

echo "[$(date '+%F %T')] watchdog started (backend=${BACKEND_PORT}, web=${WEB_PORT}, interval=${WATCH_INTERVAL}s)" >> "$LOG_FILE"
trap 'echo "[$(date "+%F %T")] watchdog stopped" >> "$LOG_FILE"; exit 0' INT TERM

while true; do
  if ! is_listening "$BACKEND_PORT" || ! is_listening "$WEB_PORT"; then
    echo "[$(date '+%F %T')] watchdog detected missing listener, restarting web ui" >> "$LOG_FILE"
    env ZF_WATCHDOG_MODE=1 ZF_ENABLE_SELF_HEAL=0 \
      BACKEND_PORT="$BACKEND_PORT" WEB_PORT="$WEB_PORT" \
      ./scripts/run_web_ui.sh --background >> "$LOG_FILE" 2>&1 || true
  fi
  sleep "$WATCH_INTERVAL"
done
