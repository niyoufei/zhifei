#!/usr/bin/env bash
set -euo pipefail

LOG_ROOT="${1:-${DOCGEN_READONLY_INSPECTION_LOG_ROOT:-/opt/docgen/logs/readonly_inspection}}"
KEEP_RUNS="${DOCGEN_READONLY_INSPECTION_KEEP_RUNS:-10}"
EXECUTE="${DOCGEN_PRUNE_EXECUTE:-0}"
RETENTION_LOG_ROOT_DEFAULT="$(cd "$(dirname "${LOG_ROOT%/}")" && pwd)/readonly_retention"
RETENTION_LOG_ROOT="${DOCGEN_READONLY_RETENTION_LOG_ROOT:-${RETENTION_LOG_ROOT_DEFAULT}}"
LATEST_RETENTION_STATUS_PATH="${DOCGEN_READONLY_RETENTION_STATUS_PATH:-${RETENTION_LOG_ROOT%/}/latest-status.txt}"
LATEST_RETENTION_RUN_PATH="${DOCGEN_READONLY_RETENTION_RUN_PATH:-${RETENTION_LOG_ROOT%/}/latest-run.txt}"
LATEST_RETENTION_LINK_PATH="${DOCGEN_READONLY_RETENTION_LINK_PATH:-${RETENTION_LOG_ROOT%/}/latest}"
CONFIRM_RUN_ID="${DOCGEN_PRUNE_CONFIRM_RUN_ID:-}"
CONFIRM_CANDIDATES="${DOCGEN_PRUNE_CONFIRM_CANDIDATES:-}"

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

read_kv() {
  local key="$1"
  local file="$2"
  awk -F= -v wanted="$key" '$1 == wanted {print substr($0, index($0, "=") + 1); exit}' "$file"
}

[[ -d "$LOG_ROOT" ]] || fail "missing log root: $LOG_ROOT"
[[ "$KEEP_RUNS" =~ ^[0-9]+$ ]] || fail "KEEP_RUNS must be a non-negative integer: $KEEP_RUNS"

RUN_DIRS=()
while IFS= read -r line; do
  [[ -n "$line" ]] || continue
  RUN_DIRS+=("$line")
done < <(
  find "$LOG_ROOT" -mindepth 1 -maxdepth 1 -type d \
    | while IFS= read -r path; do basename "$path"; done \
    | LC_ALL=C sort
)

PRUNE_CANDIDATES=()
if [[ ${#RUN_DIRS[@]} -gt "$KEEP_RUNS" ]]; then
  PRUNE_COUNT=$((${#RUN_DIRS[@]} - KEEP_RUNS))
  for ((i = 0; i < PRUNE_COUNT; i++)); do
    PRUNE_CANDIDATES+=("${RUN_DIRS[$i]}")
  done
fi

LATEST_RUN="none"
if [[ -f "${LOG_ROOT%/}/latest-run.txt" ]]; then
  LATEST_RUN="$(tr -d '\n' < "${LOG_ROOT%/}/latest-run.txt")"
elif [[ -L "${LOG_ROOT%/}/latest" ]]; then
  LATEST_RUN="$(readlink "${LOG_ROOT%/}/latest")"
fi

PRUNE_CANDIDATES_VALUE="none"
if [[ ${#PRUNE_CANDIDATES[@]} -gt 0 ]]; then
  PRUNE_CANDIDATES_VALUE="$(IFS=,; echo "${PRUNE_CANDIDATES[*]}")"
fi

MODE="preview"
if [[ "$EXECUTE" = "1" ]]; then
  [[ -f "$LATEST_RETENTION_STATUS_PATH" ]] || fail "missing latest retention status: $LATEST_RETENTION_STATUS_PATH"
  [[ -n "$CONFIRM_RUN_ID" ]] || fail "missing DOCGEN_PRUNE_CONFIRM_RUN_ID for execute mode"
  [[ -n "$CONFIRM_CANDIDATES" ]] || fail "missing DOCGEN_PRUNE_CONFIRM_CANDIDATES for execute mode"
  RETENTION_RUN_ID="$(read_kv "run_id" "$LATEST_RETENTION_STATUS_PATH" || true)"
  RETENTION_KEEP_RUNS="$(read_kv "keep_runs" "$LATEST_RETENTION_STATUS_PATH" || true)"
  RETENTION_MODE="$(read_kv "mode" "$LATEST_RETENTION_STATUS_PATH" || true)"
  RETENTION_PRUNE_CANDIDATES="$(read_kv "prune_candidates" "$LATEST_RETENTION_STATUS_PATH" || true)"
  RETENTION_PRUNE_CANDIDATES_COUNT="$(read_kv "prune_candidates_count" "$LATEST_RETENTION_STATUS_PATH" || true)"
  RETENTION_INSPECTION_LOG_ROOT="$(read_kv "inspection_log_root" "$LATEST_RETENTION_STATUS_PATH" || true)"
  LATEST_RETENTION_RUN_VALUE=""
  LATEST_RETENTION_LINK_VALUE=""
  if [[ -f "$LATEST_RETENTION_RUN_PATH" ]]; then
    LATEST_RETENTION_RUN_VALUE="$(tr -d '\n' < "$LATEST_RETENTION_RUN_PATH")"
  fi
  if [[ -L "$LATEST_RETENTION_LINK_PATH" ]]; then
    LATEST_RETENTION_LINK_VALUE="$(readlink "$LATEST_RETENTION_LINK_PATH")"
  fi

  [[ -n "$RETENTION_RUN_ID" ]] || fail "invalid retention status, missing run_id: $LATEST_RETENTION_STATUS_PATH"
  [[ "$RETENTION_MODE" = "preview" ]] || fail "retention status is not preview: $LATEST_RETENTION_STATUS_PATH"
  [[ "$RETENTION_KEEP_RUNS" = "$KEEP_RUNS" ]] || fail "retention keep_runs mismatch: expected=$KEEP_RUNS actual=${RETENTION_KEEP_RUNS:-missing}"
  [[ "$RETENTION_INSPECTION_LOG_ROOT" = "$LOG_ROOT" ]] || fail "retention inspection_log_root mismatch: expected=$LOG_ROOT actual=${RETENTION_INSPECTION_LOG_ROOT:-missing}"
  [[ -n "$LATEST_RETENTION_RUN_VALUE" ]] || fail "missing latest retention run pointer: $LATEST_RETENTION_RUN_PATH"
  [[ "$LATEST_RETENTION_RUN_VALUE" = "$RETENTION_RUN_ID" ]] || fail "latest retention run pointer drifted: expected=$RETENTION_RUN_ID actual=$LATEST_RETENTION_RUN_VALUE"
  if [[ -n "$LATEST_RETENTION_LINK_VALUE" ]]; then
    [[ "$LATEST_RETENTION_LINK_VALUE" = "$RETENTION_RUN_ID" ]] || fail "latest retention symlink drifted: expected=$RETENTION_RUN_ID actual=$LATEST_RETENTION_LINK_VALUE"
  fi
  [[ "${RETENTION_PRUNE_CANDIDATES:-none}" != "none" ]] || fail "retention preview has no prune candidates; execute refused"
  [[ "${RETENTION_PRUNE_CANDIDATES_COUNT:-0}" =~ ^[0-9]+$ ]] || fail "invalid prune_candidates_count in retention status: ${RETENTION_PRUNE_CANDIDATES_COUNT:-missing}"
  [[ "${RETENTION_PRUNE_CANDIDATES_COUNT:-0}" -gt 0 ]] || fail "retention preview candidate count is zero; execute refused"
  [[ "$CONFIRM_CANDIDATES" != "none" ]] || fail "confirm candidates cannot be none in execute mode"
  [[ "$CONFIRM_RUN_ID" = "$RETENTION_RUN_ID" ]] || fail "confirm run_id mismatch: expected=$RETENTION_RUN_ID actual=$CONFIRM_RUN_ID"
  [[ "$CONFIRM_CANDIDATES" = "$RETENTION_PRUNE_CANDIDATES" ]] || fail "confirm candidates mismatch: expected=${RETENTION_PRUNE_CANDIDATES:-none} actual=$CONFIRM_CANDIDATES"
  [[ "$PRUNE_CANDIDATES_VALUE" != "none" ]] || fail "current prune candidates are none; execute refused"
  [[ "$PRUNE_CANDIDATES_VALUE" = "${RETENTION_PRUNE_CANDIDATES:-none}" ]] || fail "current prune candidates drifted since preview: current=$PRUNE_CANDIDATES_VALUE preview=${RETENTION_PRUNE_CANDIDATES:-none}"
  MODE="execute"
  for run_id in "${PRUNE_CANDIDATES[@]}"; do
    rm -rf "${LOG_ROOT%/}/${run_id}"
  done
fi

echo "log_root=${LOG_ROOT}"
echo "keep_runs=${KEEP_RUNS}"
echo "existing_runs_count=${#RUN_DIRS[@]}"
echo "latest_run=${LATEST_RUN:-none}"
echo "prune_candidates_count=${#PRUNE_CANDIDATES[@]}"
echo "retention_log_root=${RETENTION_LOG_ROOT}"
echo "latest_retention_status=${LATEST_RETENTION_STATUS_PATH}"
echo "prune_candidates=${PRUNE_CANDIDATES_VALUE}"
echo "mode=${MODE}"
if [[ "$MODE" = "execute" ]]; then
  echo "confirm_run_id=${CONFIRM_RUN_ID}"
  echo "confirm_candidates=${CONFIRM_CANDIDATES}"
  echo "[OK] pruned_runs=${PRUNE_CANDIDATES_VALUE}"
else
  echo "[OK] preview_only=1"
fi
echo "[SUMMARY] all checks passed."
