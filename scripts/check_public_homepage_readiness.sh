#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OBSERVE_SECONDS="${1:-180}"
BACKEND_HEALTH_URL="${ZF_STATUS_BACKEND_HEALTH_URL:-http://127.0.0.1:8010/health}"
WEB_HEALTH_URL="${ZF_STATUS_WEB_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
WEB_HOME_URL="${ZF_STATUS_WEB_HOME_URL:-http://127.0.0.1:8501/}"
PID_FILE="${ZF_WEB_PID_FILE:-$ROOT/.runtime/docgen/streamlit.pid}"
OBSERVE_SCRIPT="${ZF_STATUS_OBSERVE_SCRIPT:-$ROOT/scripts/observe_web_stability.sh}"
SMOKE_SCRIPT="${ZF_STATUS_SMOKE_SCRIPT:-$ROOT/backend/scripts/smoke_e2e.py}"
INCLUDE_SMOKE="${ZF_INCLUDE_SMOKE:-0}"
KEYS_FILE="${ZF_KEYS_FILE:-$ROOT/.runtime/local_keys.env}"

backend_ok() {
  curl -fsS --max-time 3 "$BACKEND_HEALTH_URL" >/dev/null 2>&1
}

web_ok() {
  curl -fsS --max-time 3 "$WEB_HEALTH_URL" >/dev/null 2>&1
}

home_ok() {
  curl -fsSI --max-time 5 "$WEB_HOME_URL" >/dev/null 2>&1
}

listener_pid() {
  lsof -tiTCP:8501 -sTCP:LISTEN 2>/dev/null | head -n1 || true
}

pid_file_value() {
  cat "$PID_FILE" 2>/dev/null || true
}

backend_health="$(backend_ok && echo ok || echo bad)"
web_health="$(web_ok && echo ok || echo bad)"
web_home="$(home_ok && echo ok || echo bad)"
listener="$(listener_pid)"
pid_file_pid="$(pid_file_value)"
pid_aligned="no"
if [ -n "${listener:-}" ] && [ -n "${pid_file_pid:-}" ] && [ "$listener" = "$pid_file_pid" ]; then
  pid_aligned="yes"
fi

observe_result="pass"
set +e
observe_output="$(bash "$OBSERVE_SCRIPT" "$OBSERVE_SECONDS" 2>&1)"
observe_rc=$?
set -e
if [ "$observe_rc" -ne 0 ]; then
  observe_result="fail"
fi

smoke_result="skipped"
if [ "$INCLUDE_SMOKE" = "1" ]; then
  if [ ! -f "$KEYS_FILE" ]; then
    smoke_result="missing_keys"
  else
    set +e
    smoke_output="$(\
      cd "$ROOT" && \
      set -a && \
      . "$KEYS_FILE" >/dev/null 2>&1 && \
      set +a && \
      python3 -u "$SMOKE_SCRIPT" 2>&1\
    )"
    smoke_rc=$?
    set -e
    if [ "$smoke_rc" -eq 0 ]; then
      smoke_result="pass"
    else
      smoke_result="fail"
    fi
  fi
fi

public_cutover_ready="no"
if [ "$backend_health" = "ok" ] && \
   [ "$web_health" = "ok" ] && \
   [ "$web_home" = "ok" ] && \
   [ "$pid_aligned" = "yes" ] && \
   [ "$observe_result" = "pass" ] && \
   { [ "$smoke_result" = "skipped" ] || [ "$smoke_result" = "pass" ]; }; then
  public_cutover_ready="yes"
fi

echo "backend_health=$backend_health"
echo "web_health=$web_health"
echo "web_home=$web_home"
echo "web_listener_pid=${listener:-}"
echo "web_pid_file=${pid_file_pid:-}"
echo "web_pid_aligned=$pid_aligned"
echo "observe_seconds=$OBSERVE_SECONDS"
echo "observe_result=$observe_result"
echo "smoke_result=$smoke_result"
echo "public_cutover_ready=$public_cutover_ready"
echo
echo "-- observe output --"
printf '%s\n' "$observe_output"

if [ "$INCLUDE_SMOKE" = "1" ]; then
  echo
  echo "-- smoke output --"
  printf '%s\n' "${smoke_output:-}"
fi

if [ "$public_cutover_ready" != "yes" ]; then
  exit 1
fi
