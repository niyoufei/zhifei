#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# The immutable runtime supervisor owns crash detection and bounded restarts.
# A legacy watchdog invocation therefore becomes a one-shot health-gated launch
# and exits.  The old polling loop remains available only for explicit mutable
# workspace diagnostics.
if [ "${ZF_DEV_WORKSPACE_MODE:-0}" != "1" ]; then
  BOOTSTRAP_PYTHON="/usr/bin/python3"
  OS_HOME="$("$BOOTSTRAP_PYTHON" -I -B -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
  case "$OS_HOME" in /*) ;; *) exit 2 ;; esac
  TRUSTED_BOOTSTRAP="${OS_HOME}/Library/Application Support/com.zhifei.construction-expert/bootstrap/launch_current.py"
  if [ ! -x "$BOOTSTRAP_PYTHON" ] || [ ! -f "$TRUSTED_BOOTSTRAP" ] || [ -L "$TRUSTED_BOOTSTRAP" ]; then
    printf '%s\n' \
      '{"ok":false,"error_code":"LAUNCH_BOOTSTRAP_MISSING","message":"固定外置可信启动入口不可用，请重新执行本地封存"}' \
      >&2
    exit 2
  fi
  exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" --no-open
fi

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
    env ZF_WATCHDOG_MODE=1 ZF_ENABLE_SELF_HEAL=1 \
      BACKEND_PORT="$BACKEND_PORT" WEB_PORT="$WEB_PORT" \
      ./scripts/run_web_ui.sh --background >> "$LOG_FILE" 2>&1 || true
  fi
  sleep "$WATCH_INTERVAL"
done
