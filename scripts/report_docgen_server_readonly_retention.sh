#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${1:-${DOCGEN_APP_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}}"
INSPECTION_LOG_ROOT="${DOCGEN_READONLY_INSPECTION_LOG_ROOT:-${APP_ROOT%/}/logs/readonly_inspection}"
RETENTION_LOG_ROOT="${DOCGEN_READONLY_RETENTION_LOG_ROOT:-${APP_ROOT%/}/logs/readonly_retention}"
RUN_ID="${DOCGEN_READONLY_RETENTION_RUN_ID:-$(date -u '+%Y%m%d-%H%M%S')}"
KEEP_RUNS="${DOCGEN_READONLY_INSPECTION_KEEP_RUNS:-10}"
PRUNE_SCRIPT="${DOCGEN_READONLY_RETENTION_PRUNE_SCRIPT:-${APP_ROOT%/}/scripts/prune_docgen_server_readonly_inspection_logs.sh}"

LOG_DIR="${RETENTION_LOG_ROOT%/}/${RUN_ID}"
LATEST_LINK_PATH="${RETENTION_LOG_ROOT%/}/latest"
LATEST_RUN_PATH="${RETENTION_LOG_ROOT%/}/latest-run.txt"
LATEST_STATUS_PATH="${RETENTION_LOG_ROOT%/}/latest-status.txt"
PREVIEW_LOG="${LOG_DIR%/}/prune-preview.log"
SUMMARY_PATH="${LOG_DIR%/}/summary.txt"

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing required file: $path"
}

read_kv() {
  local key="$1"
  local file="$2"
  awk -F= -v wanted="$key" '$1 == wanted {print substr($0, index($0, "=") + 1); exit}' "$file"
}

require_file "$PRUNE_SCRIPT"
[[ -d "$INSPECTION_LOG_ROOT" ]] || fail "missing inspection log root: $INSPECTION_LOG_ROOT"
[[ "$KEEP_RUNS" =~ ^[0-9]+$ ]] || fail "KEEP_RUNS must be a non-negative integer: $KEEP_RUNS"

mkdir -p "$LOG_DIR"

{
  printf '[RUN] prune-preview\n'
  printf '[CMD] DOCGEN_READONLY_INSPECTION_KEEP_RUNS=%q bash %q %q\n' "$KEEP_RUNS" "$PRUNE_SCRIPT" "$INSPECTION_LOG_ROOT"
  DOCGEN_READONLY_INSPECTION_KEEP_RUNS="$KEEP_RUNS" \
    bash "$PRUNE_SCRIPT" "$INSPECTION_LOG_ROOT"
} >"$PREVIEW_LOG" 2>&1 || fail "prune-preview failed: $PREVIEW_LOG"

mode="$(read_kv "mode" "$PREVIEW_LOG" || true)"
existing_runs_count="$(read_kv "existing_runs_count" "$PREVIEW_LOG" || true)"
latest_run="$(read_kv "latest_run" "$PREVIEW_LOG" || true)"
prune_candidates_count="$(read_kv "prune_candidates_count" "$PREVIEW_LOG" || true)"
prune_candidates="$(read_kv "prune_candidates" "$PREVIEW_LOG" || true)"

[[ -n "$mode" ]] || mode="unknown"
[[ -n "$existing_runs_count" ]] || existing_runs_count="unknown"
[[ -n "$latest_run" ]] || latest_run="none"
[[ -n "$prune_candidates_count" ]] || prune_candidates_count="unknown"
[[ -n "$prune_candidates" ]] || prune_candidates="none"

[[ "$mode" = "preview" ]] || fail "unexpected retention mode: ${mode}"

next_action="healthy"
overall_state="pass"
execute_allowed="no"
if [[ "$prune_candidates_count" =~ ^[0-9]+$ ]] && [[ "$prune_candidates_count" -gt 0 ]]; then
  next_action="review-prune-candidates"
  execute_allowed="yes"
fi

cat >"$SUMMARY_PATH" <<EOF
run_id=${RUN_ID}
app_root=${APP_ROOT}
inspection_log_root=${INSPECTION_LOG_ROOT}
retention_log_root=${RETENTION_LOG_ROOT}
log_dir=${LOG_DIR}
keep_runs=${KEEP_RUNS}
existing_runs_count=${existing_runs_count}
latest_run=${latest_run}
prune_candidates_count=${prune_candidates_count}
prune_candidates=${prune_candidates}
mode=${mode}
execute_allowed=${execute_allowed}
next_action=${next_action}
overall_state=${overall_state}
EOF

ln -sfn "$RUN_ID" "$LATEST_LINK_PATH"
printf '%s\n' "$RUN_ID" >"$LATEST_RUN_PATH"
cp "$SUMMARY_PATH" "$LATEST_STATUS_PATH"

echo "[OK] app_root=${APP_ROOT}"
echo "[OK] inspection_log_root=${INSPECTION_LOG_ROOT}"
echo "[OK] retention_log_root=${RETENTION_LOG_ROOT}"
echo "[OK] keep_runs=${KEEP_RUNS}"
echo "[OK] log_dir=${LOG_DIR}"
echo "[OK] prune-preview: ${PREVIEW_LOG}"
echo "[OK] summary: ${SUMMARY_PATH}"
echo "[OK] latest link: ${LATEST_LINK_PATH} -> ${RUN_ID}"
echo "[OK] latest status: ${LATEST_STATUS_PATH}"
echo "[SUMMARY] all checks passed."
