#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

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
  exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP"
fi

mkdir -p logs
LOG="logs/webui_control.log"
echo "[$(date '+%F %T')] start requested" >> "$LOG"

# Delegate to the single startup entry to avoid drift and cross-system side effects.
# The backend performs native document parsing, so keep the lightweight local
# watchdog enabled unless an operator explicitly opts out for diagnostics.
export ZF_ENABLE_SELF_HEAL="${ZF_ENABLE_SELF_HEAL:-1}"
./scripts/run_web_ui.sh --background "$@"

echo "[$(date '+%F %T')] start finished" >> "$LOG"
