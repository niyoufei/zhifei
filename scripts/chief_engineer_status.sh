#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_FILE="${ZF_WATCHDOG_STATE:-$ROOT/.runtime/docgen/chief_engineer_state.json}"
WEB_PID_FILE="${ZF_WEB_PID_FILE:-$ROOT/.runtime/docgen/streamlit.pid}"
BACKEND_URL="${ZF_STATUS_BACKEND_URL:-http://127.0.0.1:8010/health}"
WEB_HEALTH_URL="${ZF_STATUS_WEB_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
WEB_HOME_URL="${ZF_STATUS_WEB_HOME_URL:-http://127.0.0.1:8501/}"
RUN_WEB_UI_SCRIPT="${ZF_STATUS_RUN_WEB_UI_SCRIPT:-$ROOT/scripts/run_web_ui.sh}"
CHIEF_AGENT_FILE="${ZF_STATUS_CHIEF_AGENT_FILE:-$ROOT/backend/zhifei_autoplan/chief_engineer_agent.py}"

backend_ok() {
  curl -fsS --max-time 2 "$BACKEND_URL" >/dev/null 2>&1
}

web_health_ok() {
  [ "$(curl -fsS --max-time 2 "$WEB_HEALTH_URL" 2>/dev/null || true)" = "ok" ]
}

web_home_ok() {
  curl -I -sS --max-time 2 "$WEB_HOME_URL" >/dev/null 2>&1
}

listener_pid() {
  lsof -tiTCP:8501 -sTCP:LISTEN 2>/dev/null | head -n1 || true
}

read_pid_file() {
  cat "$WEB_PID_FILE" 2>/dev/null || true
}

read_default_web_timeout() {
  grep 'WEB_READY_TIMEOUT_SEC=' "$RUN_WEB_UI_SCRIPT" 2>/dev/null | head -n1 | sed -E 's/.*:-([0-9]+).*/\1/' || true
}

read_default_web_grace() {
  grep 'ZF_WEB_START_GRACE_SECONDS' "$CHIEF_AGENT_FILE" 2>/dev/null | head -n1 | sed -E 's/.*ZF_WEB_START_GRACE_SECONDS"), ([0-9]+)\)\).*/\1/' || true
}

restart_count() {
  grep -c 'web unhealthy -> restart' "$ROOT/logs/chief_engineer_agent.log" 2>/dev/null || echo "0"
}

last_restart_line() {
  grep 'web unhealthy -> restart' "$ROOT/logs/chief_engineer_agent.log" 2>/dev/null | tail -n1 || true
}

state_last_action() {
  python3 - "$STATE_FILE" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
if not path.exists():
    print("not_started")
    raise SystemExit(0)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("unreadable")
    raise SystemExit(0)
print(str(data.get("last_action") or "unknown"))
PY
}

echo "=== 即时摘要 ==="
echo "backend_health=$(backend_ok && echo ok || echo bad)"
echo "web_health=$(web_health_ok && echo ok || echo bad)"
echo "web_home=$(web_home_ok && echo ok || echo bad)"
echo "web_listener_pid=$(listener_pid || true)"
echo "web_pid_file=$(read_pid_file || true)"
echo "web_pid_aligned=$([ -n \"$(listener_pid || true)\" ] && [ \"$(listener_pid || true)\" = \"$(read_pid_file || true)\" ] && echo yes || echo no)"
echo "chief_last_action=$(state_last_action)"
echo "chief_restart_count=$(restart_count)"
echo "chief_last_restart=$(last_restart_line)"
echo "default_web_ready_timeout_sec=$(read_default_web_timeout)"
echo "default_web_start_grace_sec=$(read_default_web_grace)"
echo "observe_hint=bash \"$ROOT/scripts/observe_web_stability.sh\" 180"
echo

echo "=== 技术总工 Agent 状态 ==="
if [ -f "$STATE_FILE" ]; then
  cat "$STATE_FILE"
else
  echo "{\"status\":\"not_started\"}"
fi
echo

echo "=== 端口监听 ==="
lsof -nP -iTCP:8010 -sTCP:LISTEN || true
lsof -nP -iTCP:8501 -sTCP:LISTEN || true
echo

echo "=== 最近日志 (watchdog) ==="
echo "-- chief_engineer_agent.log --"
tail -n 40 "$ROOT/logs/chief_engineer_agent.log" 2>/dev/null || true
echo
echo "-- legacy webui_watchdog.log --"
tail -n 20 "$ROOT/logs/webui_watchdog.log" 2>/dev/null || true
