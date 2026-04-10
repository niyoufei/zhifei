#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-${DOCGEN_REMOTE_TARGET:-}}"
SSH_BIN="${DOCGEN_REMOTE_SSH_BIN:-ssh}"
APP_DIR="${DOCGEN_REMOTE_APP_DIR:-/opt/docgen}"
PUBLIC_URL="${DOCGEN_REMOTE_PUBLIC_URL:-https://doc.niyoufei.com}"
UI_SCRIPT="${DOCGEN_REMOTE_UI_SCRIPT:-$ROOT/scripts/verify_remote_ui_upload_outline_chain.sh}"
RUNTIME_SCRIPT="${DOCGEN_REMOTE_RUNTIME_SCRIPT:-./scripts/report_docgen_runtime_health_stable.sh}"
UPLOAD_SCRIPT="${DOCGEN_REMOTE_UPLOAD_SCRIPT:-./scripts/verify_upload_parse_chain.sh}"
GENERATE_SCRIPT="${DOCGEN_REMOTE_GENERATE_SCRIPT:-./scripts/verify_generate_export_chain.sh}"
RUN_UI="${DOCGEN_REMOTE_RUN_UI:-1}"
RUN_RUNTIME="${DOCGEN_REMOTE_RUN_RUNTIME:-1}"
RUN_UPLOAD="${DOCGEN_REMOTE_RUN_UPLOAD:-1}"
RUN_GENERATE="${DOCGEN_REMOTE_RUN_GENERATE:-1}"
LOG_ROOT="${DOCGEN_REMOTE_LOG_ROOT:-$ROOT/output/smoke_logs/remote_full_chain}"
RUN_ID="${DOCGEN_REMOTE_RUN_ID:-$(date '+%Y%m%d_%H%M%S')}"

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
    print_status "$label" "0" "$(printf '%s' "$output" | tail -n 3 | tr '\n' ' ' | sed 's/  */ /g') [log=$(basename "$log_file")]"
  fi
}

run_remote_step() {
  local label="$1"
  local remote_cmd="$2"
  local output=""
  local log_file=""
  log_file="$(step_log_path "$label")"
  if output="$("$SSH_BIN" "$TARGET" "$remote_cmd" 2>&1)"; then
    printf '%s\n' "$output" >"$log_file"
    print_status "$label" "1" "passed (log=$(basename "$log_file"))"
  else
    printf '%s\n' "$output" >"$log_file"
    print_status "$label" "0" "$(printf '%s' "$output" | tail -n 3 | tr '\n' ' ' | sed 's/  */ /g') [log=$(basename "$log_file")]"
  fi
}

if [[ -z "$TARGET" ]]; then
  echo "[ERROR] missing ssh target. usage: bash ./scripts/verify_remote_full_chain.sh user@host" >&2
  exit 1
fi

require_cmd "$SSH_BIN"
mkdir -p "$LOG_ROOT"
log_dir="${LOG_ROOT%/}/$RUN_ID"
mkdir -p "$log_dir"

echo "[INFO] ssh_target=$TARGET"
echo "[INFO] app_dir=$APP_DIR"
echo "[INFO] public_url=$PUBLIC_URL"
echo "[INFO] run_ui=$RUN_UI run_runtime=$RUN_RUNTIME run_upload=$RUN_UPLOAD run_generate=$RUN_GENERATE"
echo "[INFO] log_dir=$log_dir"
echo "[INFO] 注意：upload/generate 两步会在远端写入少量 smoke 记录，仅应在允许的运维窗口执行。"

if [[ "$RUN_UI" = "1" ]]; then
  run_local_step "ui upload outline chain" bash "$UI_SCRIPT" "$TARGET"
fi

if [[ "$RUN_RUNTIME" = "1" ]]; then
  printf -v remote_cmd 'cd %q && bash %q %q' "$APP_DIR" "$RUNTIME_SCRIPT" "$PUBLIC_URL"
  run_remote_step "runtime health" "$remote_cmd"
fi

if [[ "$RUN_UPLOAD" = "1" ]]; then
  printf -v remote_cmd 'cd %q && bash %q' "$APP_DIR" "$UPLOAD_SCRIPT"
  run_remote_step "upload parse chain" "$remote_cmd"
fi

if [[ "$RUN_GENERATE" = "1" ]]; then
  printf -v remote_cmd 'cd %q && bash %q' "$APP_DIR" "$GENERATE_SCRIPT"
  run_remote_step "generate export chain" "$remote_cmd"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
