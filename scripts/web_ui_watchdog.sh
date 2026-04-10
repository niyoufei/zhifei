#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-8501}"
WATCH_INTERVAL="${ZF_WATCHDOG_INTERVAL:-8}"
LOG_FILE="${ZF_WATCHDOG_LOG:-$ROOT/logs/webui_watchdog.log}"
STATE_FILE="${ZF_WATCHDOG_STATE:-$ROOT/.runtime/docgen/chief_engineer_state.json}"
MAX_RESTARTS_PER_HOUR="${ZF_MAX_RESTARTS_PER_HOUR:-10}"

mkdir -p "$ROOT/logs" "$(dirname "$STATE_FILE")"

now() {
  date '+%F %T'
}

is_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

http_ok() {
  local url="$1"
  curl -fsS --max-time 3 "$url" >/dev/null 2>&1
}

append_restart_ts() {
  local ts
  ts="$(date +%s)"
  local hist_file="$ROOT/.runtime/docgen/.watchdog_restart_ts"
  touch "$hist_file"
  echo "$ts" >> "$hist_file"
  tail -n 200 "$hist_file" > "${hist_file}.tmp" && mv "${hist_file}.tmp" "$hist_file"
}

restart_count_last_hour() {
  local hist_file="$ROOT/.runtime/docgen/.watchdog_restart_ts"
  [ -f "$hist_file" ] || { echo 0; return 0; }
  local cutoff
  cutoff="$(( $(date +%s) - 3600 ))"
  awk -v c="$cutoff" '($1+0)>=c{n++} END{print n+0}' "$hist_file" 2>/dev/null || echo 0
}

write_state() {
  local backend_listener="$1"
  local web_listener="$2"
  local backend_health="$3"
  local web_health="$4"
  local action="$5"
  local ts
  ts="$(date '+%F %T')"
  cat > "$STATE_FILE" <<EOF
{"timestamp":"$ts","backend_listener":$backend_listener,"web_listener":$web_listener,"backend_health":$backend_health,"web_health":$web_health,"last_action":"$action"}
EOF
}

echo "[$(now)] chief-engineer watchdog started (backend=${BACKEND_HOST}:${BACKEND_PORT}, web=${WEB_HOST}:${WEB_PORT}, interval=${WATCH_INTERVAL}s)" >> "$LOG_FILE"
trap 'echo "[$(now)] chief-engineer watchdog stopped" >> "$LOG_FILE"; exit 0' INT TERM

while true; do
  backend_listener=1
  web_listener=1
  backend_health=1
  web_health=1
  action="noop"

  if ! is_listening "$BACKEND_PORT"; then
    backend_listener=0
  fi
  if ! is_listening "$WEB_PORT"; then
    web_listener=0
  fi
  if ! http_ok "http://${BACKEND_HOST}:${BACKEND_PORT}/health"; then
    backend_health=0
  fi
  if ! http_ok "http://${WEB_HOST}:${WEB_PORT}/"; then
    web_health=0
  fi

  if [ "$backend_listener" -eq 0 ] || [ "$web_listener" -eq 0 ] || [ "$backend_health" -eq 0 ] || [ "$web_health" -eq 0 ]; then
    restarts="$(restart_count_last_hour)"
    if [ "$restarts" -ge "$MAX_RESTARTS_PER_HOUR" ]; then
      action="throttled"
      echo "[$(now)] watchdog throttle hit (${restarts}/${MAX_RESTARTS_PER_HOUR} per hour), skip restart" >> "$LOG_FILE"
    else
      action="restart_web_ui"
      echo "[$(now)] watchdog unhealthy -> restart (backend_listener=${backend_listener}, web_listener=${web_listener}, backend_health=${backend_health}, web_health=${web_health})" >> "$LOG_FILE"
      env ZF_WATCHDOG_MODE=1 ZF_ENABLE_SELF_HEAL=0 \
        BACKEND_PORT="$BACKEND_PORT" WEB_PORT="$WEB_PORT" \
        ./scripts/run_web_ui.sh --background >> "$LOG_FILE" 2>&1 || true
      append_restart_ts
    fi
  fi

  write_state "$backend_listener" "$web_listener" "$backend_health" "$web_health" "$action"
  sleep "$WATCH_INTERVAL"
done
