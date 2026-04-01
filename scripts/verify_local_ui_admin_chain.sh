#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UI_SCRIPT="${DOCGEN_LOCAL_UI_SCRIPT:-$ROOT/scripts/verify_ui_upload_outline_chain.sh}"
ADMIN_SCRIPT="${DOCGEN_LOCAL_ADMIN_CHAIN_SCRIPT:-$ROOT/scripts/verify_local_admin_ops_chain.sh}"
RUN_UI="${DOCGEN_LOCAL_RUN_UI:-1}"
RUN_ADMIN="${DOCGEN_LOCAL_RUN_ADMIN:-1}"
LOG_ROOT="${DOCGEN_LOCAL_UI_ADMIN_LOG_ROOT:-$ROOT/output/smoke_logs/local_ui_admin_chain}"
RUN_ID="${DOCGEN_LOCAL_UI_ADMIN_RUN_ID:-$(date '+%Y%m%d_%H%M%S')}"
ADMIN_API_PORT="${DOCGEN_LOCAL_UI_ADMIN_API_PORT:-18110}"
ADMIN_PANEL_BACKEND_PORT="${DOCGEN_LOCAL_UI_ADMIN_PANEL_BACKEND_PORT:-18112}"
ADMIN_PANEL_WEB_PORT="${DOCGEN_LOCAL_UI_ADMIN_PANEL_WEB_PORT:-18612}"

failures=0
log_dir=""

print_status() {
  local label="$1"
  local ok="$2"
  local detail="$3"
  if [[ "$ok" = "1" ]]; then
    echo "[OK] ${label}: ${detail}"
  else
    echo "[FAIL] ${label}: ${detail}"
    failures=$((failures + 1))
  fi
}

require_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "[ERROR] missing required command: $name" >&2
    exit 1
  fi
}

step_log_path() {
  local label="$1"
  local slug
  slug="$(printf '%s' "$label" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
  slug="${slug#-}"
  slug="${slug%-}"
  printf '%s/%s.log\n' "$log_dir" "$slug"
}

run_local_step() {
  local label="$1"
  shift
  local output=""
  local log_file=""
  log_file="$(step_log_path "$label")"
  if output="$("$@" 2>&1)"; then
    printf '%s\n' "$output" >"$log_file"
    print_status "$label" "1" "passed (log=$(basename "$log_file"))"
  else
    printf '%s\n' "$output" >"$log_file"
    print_status "$label" "0" "$(printf '%s' "$output" | tail -n 4 | tr '\n' ' ' | sed 's/  */ /g') [log=$(basename "$log_file")]"
  fi
}

require_cmd bash
mkdir -p "$LOG_ROOT"
log_dir="${LOG_ROOT%/}/$RUN_ID"
mkdir -p "$log_dir"

echo "[INFO] log_dir=$log_dir"
echo "[INFO] run_ui=$RUN_UI run_admin=$RUN_ADMIN"
echo "[INFO] ui_script=$UI_SCRIPT"
echo "[INFO] admin_script=$ADMIN_SCRIPT"
echo "[INFO] admin_api_port=$ADMIN_API_PORT admin_panel_backend_port=$ADMIN_PANEL_BACKEND_PORT admin_panel_web_port=$ADMIN_PANEL_WEB_PORT"
echo "[INFO] 注意：该脚本只跑本地浏览器运维 smoke，不改 8010/8501 常驻主链配置，也不触发 execute/delete。"

if [[ "$RUN_UI" = "1" ]]; then
  run_local_step "local ui upload outline chain" env DOCGEN_UI_BROWSER_IMPL="${DOCGEN_LOCAL_UI_BROWSER_IMPL:-python}" bash "$UI_SCRIPT"
fi

if [[ "$RUN_ADMIN" = "1" ]]; then
  run_local_step \
    "local admin ops chain" \
    env \
    DOCGEN_ADMIN_SMOKE_PORT="$ADMIN_API_PORT" \
    DOCGEN_ADMIN_UI_SMOKE_BACKEND_PORT="$ADMIN_PANEL_BACKEND_PORT" \
    DOCGEN_ADMIN_UI_SMOKE_WEB_PORT="$ADMIN_PANEL_WEB_PORT" \
    bash "$ADMIN_SCRIPT"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
