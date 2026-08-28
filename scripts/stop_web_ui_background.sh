#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Production stop is identity-bound to the selected immutable supervisor.  It
# never scans workspace pid files or ports.  The legacy process cleanup below
# is retained solely for an explicitly requested mutable-workspace diagnostic.
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
  exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" --stop
fi

BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"
RUNTIME_DIR="${ZF_RUNTIME_DIR:-$ROOT/.runtime/docgen}"
PID_BACKEND="$RUNTIME_DIR/webui_backend.pid"
PID_STREAMLIT="$RUNTIME_DIR/streamlit.pid"
PID_WATCHDOG="$RUNTIME_DIR/webui_watchdog.pid"
OLD_PID_BACKEND="logs/webui_backend.pid"
OLD_PID_STREAMLIT="logs/streamlit.pid"
LOG="logs/webui_control.log"

mkdir -p logs
echo "[$(date '+%F %T')] stop requested" >> "$LOG"

pid_cmdline() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

pid_cwd() {
  local pid="$1"
  lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n1
}

is_our_backend_pid() {
  local pid="$1"
  local cmd cwd
  cmd="$(pid_cmdline "$pid")"
  cwd="$(pid_cwd "$pid")"
  [[ "$cmd" == *"uvicorn"* ]] || return 1
  [[ "$cmd" == *"backend.app.main:app"* ]] || return 1
  [[ "$cmd" == *"--port ${BACKEND_PORT}"* ]] || return 1
  [[ "$cmd" == *"--app-dir ${ROOT}"* || "$cwd" == "$ROOT" ]] || return 1
  return 0
}

is_our_streamlit_pid() {
  local pid="$1"
  local cmd cwd
  cmd="$(pid_cmdline "$pid")"
  cwd="$(pid_cwd "$pid")"
  [[ "$cmd" == *"streamlit"* ]] || return 1
  [[ "$cmd" == *"--server.port ${WEB_PORT}"* ]] || return 1
  [[ "$cmd" == *"$ROOT/app.py"* || "$cwd" == "$ROOT" ]] || return 1
  return 0
}

kill_if_ours() {
  local pid="$1"
  local kind="$2"
  if [ -z "$pid" ]; then
    return 0
  fi
  if [ "$kind" = "backend" ]; then
    is_our_backend_pid "$pid" || return 0
  else
    is_our_streamlit_pid "$pid" || return 0
  fi
  kill "$pid" >/dev/null 2>&1 || true
}

# Prefer pid files written by run_web_ui.sh.
for pf in "$PID_STREAMLIT" "$OLD_PID_STREAMLIT"; do
  if [ -f "$pf" ]; then
    kill_if_ours "$(cat "$pf")" "streamlit"
    rm -f "$pf"
  fi
done
for pf in "$PID_BACKEND" "$OLD_PID_BACKEND"; do
  if [ -f "$pf" ]; then
    kill_if_ours "$(cat "$pf")" "backend"
    rm -f "$pf"
  fi
done

# Stop self-heal watchdog if running.
if [ -f "$PID_WATCHDOG" ]; then
  wd_pid="$(cat "$PID_WATCHDOG" 2>/dev/null || true)"
  if [ -n "${wd_pid:-}" ]; then
    kill "$wd_pid" >/dev/null 2>&1 || true
  fi
  rm -f "$PID_WATCHDOG"
fi

# Fallback: only stop listeners that can be verified as this project.
if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  while read -r pid; do
    [ -n "$pid" ] || continue
    kill_if_ours "$pid" "streamlit"
  done < <(lsof -tiTCP:"$WEB_PORT" -sTCP:LISTEN 2>/dev/null || true)
fi

if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  while read -r pid; do
    [ -n "$pid" ] || continue
    kill_if_ours "$pid" "backend"
  done < <(lsof -tiTCP:"$BACKEND_PORT" -sTCP:LISTEN 2>/dev/null || true)
fi

echo "[$(date '+%F %T')] stop finished" >> "$LOG"
