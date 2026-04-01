#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_SCRIPT="${DOCGEN_LOCAL_ADMIN_API_SCRIPT:-$ROOT/scripts/verify_local_admin_ops_api.sh}"
PANEL_SCRIPT="${DOCGEN_LOCAL_ADMIN_PANEL_SCRIPT:-$ROOT/scripts/verify_local_admin_ops_panel.sh}"
RUN_API="${DOCGEN_LOCAL_ADMIN_RUN_API:-1}"
RUN_PANEL="${DOCGEN_LOCAL_ADMIN_RUN_PANEL:-1}"
LOG_ROOT="${DOCGEN_LOCAL_ADMIN_LOG_ROOT:-$ROOT/output/smoke_logs/local_admin_ops_chain}"
RUN_ID="${DOCGEN_LOCAL_ADMIN_RUN_ID:-$(date '+%Y%m%d_%H%M%S')}"

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
echo "[INFO] run_api=$RUN_API run_panel=$RUN_PANEL"
echo "[INFO] api_script=$API_SCRIPT"
echo "[INFO] panel_script=$PANEL_SCRIPT"
echo "[INFO] 注意：该脚本只跑本地 admin 只读 smoke，不改 8010/8501 常驻主链配置。"

if [[ "$RUN_API" = "1" ]]; then
  run_local_step "local admin api smoke" bash "$API_SCRIPT"
fi

if [[ "$RUN_PANEL" = "1" ]]; then
  run_local_step "local admin panel smoke" bash "$PANEL_SCRIPT"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
