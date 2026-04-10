#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

OBSERVE_SECONDS="${1:-${ZF_OBSERVE_SECONDS:-180}}"
OBSERVE_INTERVAL_SECONDS="${ZF_OBSERVE_INTERVAL_SECONDS:-1}"
BACKEND_URL="${ZF_OBSERVE_BACKEND_URL:-http://127.0.0.1:8010/health}"
WEB_HEALTH_URL="${ZF_OBSERVE_WEB_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
WEB_HOME_URL="${ZF_OBSERVE_WEB_HOME_URL:-http://127.0.0.1:8501/}"
CHIEF_LOG="${ZF_OBSERVE_CHIEF_LOG:-$ROOT/logs/chief_engineer_agent.log}"
PID_FILE="${ZF_OBSERVE_WEB_PID_FILE:-$ROOT/.runtime/docgen/streamlit.pid}"
BACKEND_FAIL_STREAK_THRESHOLD="${ZF_OBSERVE_BACKEND_FAIL_STREAK:-2}"
WEB_HEALTH_FAIL_STREAK_THRESHOLD="${ZF_OBSERVE_WEB_HEALTH_FAIL_STREAK:-2}"
HOME_FAIL_STREAK_THRESHOLD="${ZF_OBSERVE_HOME_FAIL_STREAK:-2}"

if ! [[ "$OBSERVE_SECONDS" =~ ^[0-9]+$ ]] || [ "$OBSERVE_SECONDS" -le 0 ]; then
  echo "[ERROR] observe seconds must be a positive integer" >&2
  exit 2
fi
if ! [[ "$OBSERVE_INTERVAL_SECONDS" =~ ^[0-9]+$ ]] || [ "$OBSERVE_INTERVAL_SECONDS" -le 0 ]; then
  echo "[ERROR] observe interval seconds must be a positive integer" >&2
  exit 2
fi
if ! [[ "$BACKEND_FAIL_STREAK_THRESHOLD" =~ ^[0-9]+$ ]] || [ "$BACKEND_FAIL_STREAK_THRESHOLD" -le 0 ]; then
  echo "[ERROR] backend fail streak threshold must be a positive integer" >&2
  exit 2
fi
if ! [[ "$WEB_HEALTH_FAIL_STREAK_THRESHOLD" =~ ^[0-9]+$ ]] || [ "$WEB_HEALTH_FAIL_STREAK_THRESHOLD" -le 0 ]; then
  echo "[ERROR] web health fail streak threshold must be a positive integer" >&2
  exit 2
fi
if ! [[ "$HOME_FAIL_STREAK_THRESHOLD" =~ ^[0-9]+$ ]] || [ "$HOME_FAIL_STREAK_THRESHOLD" -le 0 ]; then
  echo "[ERROR] home fail streak threshold must be a positive integer" >&2
  exit 2
fi

restart_count() {
  if [ ! -f "$CHIEF_LOG" ]; then
    echo "0"
    return 0
  fi
  grep -c 'web unhealthy -> restart' "$CHIEF_LOG" 2>/dev/null || echo "0"
}

listener_pid() {
  lsof -tiTCP:8501 -sTCP:LISTEN 2>/dev/null | head -n1 || true
}

head_ok() {
  curl -I -sS --max-time 2 "$WEB_HOME_URL" >/dev/null 2>&1
}

backend_ok() {
  curl -fsS --max-time 2 "$BACKEND_URL" >/dev/null 2>&1
}

web_health_ok() {
  [ "$(curl -fsS --max-time 2 "$WEB_HEALTH_URL" 2>/dev/null || true)" = "ok" ]
}

before_restart_count="$(restart_count)"
before_listener_pid="$(listener_pid)"
before_pid_file="$(cat "$PID_FILE" 2>/dev/null || true)"

backend_drop_at="none"
web_health_drop_at="none"
home_drop_at="none"
backend_fail_streak=0
web_health_fail_streak=0
home_fail_streak=0

loops=$(( OBSERVE_SECONDS / OBSERVE_INTERVAL_SECONDS ))
if [ $(( OBSERVE_SECONDS % OBSERVE_INTERVAL_SECONDS )) -ne 0 ]; then
  loops=$(( loops + 1 ))
fi

for ((i=0; i<loops; i++)); do
  if backend_ok; then
    backend_fail_streak=0
  else
    backend_fail_streak=$(( backend_fail_streak + 1 ))
    if [ "$backend_drop_at" = "none" ] && [ "$backend_fail_streak" -ge "$BACKEND_FAIL_STREAK_THRESHOLD" ]; then
      backend_drop_at="$(( (i - BACKEND_FAIL_STREAK_THRESHOLD + 1) * OBSERVE_INTERVAL_SECONDS ))"
    fi
  fi
  if web_health_ok; then
    web_health_fail_streak=0
  else
    web_health_fail_streak=$(( web_health_fail_streak + 1 ))
    if [ "$web_health_drop_at" = "none" ] && [ "$web_health_fail_streak" -ge "$WEB_HEALTH_FAIL_STREAK_THRESHOLD" ]; then
      web_health_drop_at="$(( (i - WEB_HEALTH_FAIL_STREAK_THRESHOLD + 1) * OBSERVE_INTERVAL_SECONDS ))"
    fi
  fi
  if head_ok; then
    home_fail_streak=0
  else
    home_fail_streak=$(( home_fail_streak + 1 ))
    if [ "$home_drop_at" = "none" ] && [ "$home_fail_streak" -ge "$HOME_FAIL_STREAK_THRESHOLD" ]; then
      home_drop_at="$(( (i - HOME_FAIL_STREAK_THRESHOLD + 1) * OBSERVE_INTERVAL_SECONDS ))"
    fi
  fi
  if [ "$i" -lt $(( loops - 1 )) ]; then
    sleep "$OBSERVE_INTERVAL_SECONDS"
  fi
done

after_restart_count="$(restart_count)"
after_listener_pid="$(listener_pid)"
after_pid_file="$(cat "$PID_FILE" 2>/dev/null || true)"

echo "observe_seconds=$OBSERVE_SECONDS"
echo "observe_interval_seconds=$OBSERVE_INTERVAL_SECONDS"
echo "backend_fail_streak_threshold=$BACKEND_FAIL_STREAK_THRESHOLD"
echo "web_health_fail_streak_threshold=$WEB_HEALTH_FAIL_STREAK_THRESHOLD"
echo "home_fail_streak_threshold=$HOME_FAIL_STREAK_THRESHOLD"
echo "before_restart_count=$before_restart_count"
echo "after_restart_count=$after_restart_count"
echo "before_listener_pid=${before_listener_pid:-none}"
echo "after_listener_pid=${after_listener_pid:-none}"
echo "before_pid_file=${before_pid_file:-none}"
echo "after_pid_file=${after_pid_file:-none}"
echo "backend_drop_at=$backend_drop_at"
echo "web_health_drop_at=$web_health_drop_at"
echo "home_drop_at=$home_drop_at"

if [ "$after_restart_count" -ne "$before_restart_count" ] || \
   [ "$backend_drop_at" != "none" ] || \
   [ "$web_health_drop_at" != "none" ] || \
   [ "$home_drop_at" != "none" ]; then
  exit 1
fi

exit 0
