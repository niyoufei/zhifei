#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${1:-${DOCGEN_APP_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}}"
TARGET_URL="${2:-${DOCGEN_PUBLIC_BASE_URL:-https://doc.niyoufei.com}}"
RELEASE_DIR="${DOCGEN_RELEASE_DIR:-${APP_ROOT%/}/releases}"
LOG_ROOT="${DOCGEN_READONLY_INSPECTION_LOG_ROOT:-${APP_ROOT%/}/logs/readonly_inspection}"
RETENTION_LOG_ROOT="${DOCGEN_READONLY_RETENTION_LOG_ROOT:-${APP_ROOT%/}/logs/readonly_retention}"
RUN_ID="${DOCGEN_READONLY_INSPECTION_RUN_ID:-$(date -u '+%Y%m%d-%H%M%S')}"
LOG_DIR="${LOG_ROOT%/}/${RUN_ID}"
LATEST_LINK_PATH="${LOG_ROOT%/}/latest"
LATEST_RUN_PATH="${LOG_ROOT%/}/latest-run.txt"
LATEST_STATUS_PATH="${LOG_ROOT%/}/latest-status.txt"
RETENTION_STATUS_PATH="${RETENTION_LOG_ROOT%/}/latest-status.txt"

RELEASE_VERIFY_SCRIPT="${DOCGEN_RELEASE_VERIFY_SCRIPT:-${APP_ROOT%/}/scripts/verify_docgen_server_release_dir.sh}"
WORKTREE_VERIFY_SCRIPT="${DOCGEN_WORKTREE_VERIFY_SCRIPT:-${APP_ROOT%/}/scripts/verify_docgen_server_worktree_scripts.sh}"
RUNTIME_REPORT_SCRIPT="${DOCGEN_RUNTIME_REPORT_SCRIPT:-${APP_ROOT%/}/scripts/report_docgen_runtime_health_stable.sh}"
RETENTION_REPORT_SCRIPT="${DOCGEN_RETENTION_REPORT_SCRIPT:-${APP_ROOT%/}/scripts/report_docgen_server_readonly_retention.sh}"

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing required file: $path"
}

require_file "$RELEASE_VERIFY_SCRIPT"
require_file "$WORKTREE_VERIFY_SCRIPT"
require_file "$RUNTIME_REPORT_SCRIPT"
require_file "$RETENTION_REPORT_SCRIPT"

mkdir -p "$LOG_DIR"

FAILURES=()
FAILURE_COUNT=0

run_step() {
  local label="$1"
  local logfile="$2"
  shift 2

  {
    printf '[RUN] %s\n' "$label"
    printf '[CMD]'
    printf ' %q' "$@"
    printf '\n'
    "$@"
  } >"$logfile" 2>&1 || {
    local rc=$?
    FAILURES+=("${label}:${rc}")
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
    echo "[ERROR] ${label} failed (rc=${rc}): ${logfile}" >&2
    return 0
  }

  echo "[OK] ${label}: ${logfile}"
}

read_kv() {
  local key="$1"
  local file="$2"
  awk -F= -v wanted="$key" '$1 == wanted {print substr($0, index($0, "=") + 1); exit}' "$file"
}

RELEASE_LOG="${LOG_DIR%/}/release-dir.log"
WORKTREE_LOG="${LOG_DIR%/}/server-worktree.log"
RUNTIME_LOG="${LOG_DIR%/}/runtime-health.log"
RETENTION_LOG="${LOG_DIR%/}/readonly-retention.log"
SUMMARY_PATH="${LOG_DIR%/}/summary.txt"

echo "[OK] app_root=${APP_ROOT}"
echo "[OK] release_dir=${RELEASE_DIR}"
echo "[OK] target_url=${TARGET_URL}"
echo "[OK] log_dir=${LOG_DIR}"

run_step "release-dir" "$RELEASE_LOG" bash "$RELEASE_VERIFY_SCRIPT" "$RELEASE_DIR"
run_step "server-worktree" "$WORKTREE_LOG" bash "$WORKTREE_VERIFY_SCRIPT" "$APP_ROOT" "$RELEASE_DIR"
run_step "runtime-health" "$RUNTIME_LOG" bash "$RUNTIME_REPORT_SCRIPT" "$TARGET_URL"
run_step "readonly-retention" "$RETENTION_LOG" bash "$RETENTION_REPORT_SCRIPT" "$APP_ROOT"

release_state="pass"
server_worktree_state="pass"
runtime_monitoring_state="$(read_kv "runtime_monitoring_state" "$RUNTIME_LOG" || true)"
next_action="$(read_kv "next_action" "$RUNTIME_LOG" || true)"
readonly_retention_state="pass"
readonly_retention_run_id="none"
readonly_retention_prune_candidates_count="unknown"
readonly_retention_execute_allowed="unknown"
readonly_retention_next_action="inspect-retention-log"
[[ -n "$runtime_monitoring_state" ]] || runtime_monitoring_state="fail"
[[ -n "$next_action" ]] || next_action="inspect-runtime-log"

if ! printf '%s\n' "${FAILURES[@]}" | grep -Fq "readonly-retention:"; then
  [[ -f "$RETENTION_STATUS_PATH" ]] || {
    FAILURES+=("readonly-retention:status")
    FAILURE_COUNT=$((FAILURE_COUNT + 1))
  }
  if [[ -f "$RETENTION_STATUS_PATH" ]]; then
    readonly_retention_run_id="$(read_kv "run_id" "$RETENTION_STATUS_PATH" || true)"
    readonly_retention_prune_candidates_count="$(read_kv "prune_candidates_count" "$RETENTION_STATUS_PATH" || true)"
    readonly_retention_execute_allowed="$(read_kv "execute_allowed" "$RETENTION_STATUS_PATH" || true)"
    readonly_retention_next_action="$(read_kv "next_action" "$RETENTION_STATUS_PATH" || true)"
    [[ -n "$readonly_retention_run_id" ]] || readonly_retention_run_id="none"
    [[ -n "$readonly_retention_prune_candidates_count" ]] || readonly_retention_prune_candidates_count="unknown"
    [[ -n "$readonly_retention_execute_allowed" ]] || readonly_retention_execute_allowed="unknown"
    [[ -n "$readonly_retention_next_action" ]] || readonly_retention_next_action="inspect-retention-log"
  fi
fi

if [[ $FAILURE_COUNT -gt 0 ]]; then
  for item in "${FAILURES[@]}"; do
    case "$item" in
      release-dir:*) release_state="fail" ;;
      server-worktree:*) server_worktree_state="fail" ;;
      runtime-health:*)
        runtime_monitoring_state="fail"
        next_action="inspect-runtime-log"
        ;;
      readonly-retention:*)
        readonly_retention_state="fail"
        next_action="inspect-retention-log"
        ;;
    esac
  done
fi

if [[ $FAILURE_COUNT -eq 0 ]]; then
  if [[ "$runtime_monitoring_state" != "pass" ]]; then
    next_action="${next_action:-inspect-runtime-log}"
  elif [[ "$readonly_retention_execute_allowed" = "yes" ]]; then
    next_action="${readonly_retention_next_action:-review-prune-candidates}"
  else
    next_action="healthy"
  fi
fi

overall_state="pass"
if [[ $FAILURE_COUNT -gt 0 ]]; then
  overall_state="fail"
fi

cat >"$SUMMARY_PATH" <<EOF
run_id=${RUN_ID}
app_root=${APP_ROOT}
release_dir=${RELEASE_DIR}
target_url=${TARGET_URL}
log_dir=${LOG_DIR}
release_dir_state=${release_state}
server_worktree_state=${server_worktree_state}
runtime_monitoring_state=${runtime_monitoring_state}
readonly_retention_state=${readonly_retention_state}
readonly_retention_run_id=${readonly_retention_run_id}
readonly_retention_prune_candidates_count=${readonly_retention_prune_candidates_count}
readonly_retention_execute_allowed=${readonly_retention_execute_allowed}
next_action=${next_action}
overall_state=${overall_state}
EOF

ln -sfn "$RUN_ID" "$LATEST_LINK_PATH"
printf '%s\n' "$RUN_ID" >"$LATEST_RUN_PATH"
cp "$SUMMARY_PATH" "$LATEST_STATUS_PATH"

echo "[OK] summary: ${SUMMARY_PATH}"
echo "[OK] latest link: ${LATEST_LINK_PATH} -> ${RUN_ID}"
echo "[OK] latest status: ${LATEST_STATUS_PATH}"

if [[ $FAILURE_COUNT -gt 0 ]]; then
  fail "readonly inspection failed: $(IFS=,; echo "${FAILURES[*]}")"
fi

echo "[SUMMARY] all checks passed."
