#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/prune_docgen_server_readonly_inspection_logs.sh"
TMP_DIR="$(mktemp -d)"
LOG_ROOT="$TMP_DIR/readonly_inspection"
RETENTION_LOG_ROOT="$TMP_DIR/readonly_retention"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

assert_contains() {
  local needle="$1"
  local file="$2"
  if ! grep -Fq -- "$needle" "$file"; then
    echo "[FAIL] missing expected text: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

mkdir -p \
  "$LOG_ROOT/20260401-120000" \
  "$LOG_ROOT/20260401-121000" \
  "$LOG_ROOT/20260401-122000"
mkdir -p "$RETENTION_LOG_ROOT"
printf '%s\n' "20260401-122000" > "$LOG_ROOT/latest-run.txt"
ln -sfn "20260401-122000" "$LOG_ROOT/latest"
printf 'summary\n' > "$LOG_ROOT/latest-status.txt"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_READONLY_INSPECTION_KEEP_RUNS=2 \
bash "$SCRIPT" "$LOG_ROOT" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "log_root=$LOG_ROOT" "$PREVIEW_OUTPUT"
assert_contains "keep_runs=2" "$PREVIEW_OUTPUT"
assert_contains "existing_runs_count=3" "$PREVIEW_OUTPUT"
assert_contains "latest_run=20260401-122000" "$PREVIEW_OUTPUT"
assert_contains "prune_candidates_count=1" "$PREVIEW_OUTPUT"
assert_contains "retention_log_root=$RETENTION_LOG_ROOT" "$PREVIEW_OUTPUT"
assert_contains "latest_retention_status=$RETENTION_LOG_ROOT/latest-status.txt" "$PREVIEW_OUTPUT"
assert_contains "prune_candidates=20260401-120000" "$PREVIEW_OUTPUT"
assert_contains "mode=preview" "$PREVIEW_OUTPUT"
assert_contains "[OK] preview_only=1" "$PREVIEW_OUTPUT"
[[ -d "$LOG_ROOT/20260401-120000" ]] || {
  echo "[FAIL] preview deleted oldest run" >&2
  exit 1
}

cat > "$RETENTION_LOG_ROOT/latest-status.txt" <<'EOF'
run_id=20260401-retention-preview
inspection_log_root=__LOG_ROOT__
retention_log_root=__RETENTION_ROOT__
keep_runs=2
existing_runs_count=3
latest_run=20260401-122000
prune_candidates_count=1
prune_candidates=20260401-120000
mode=preview
next_action=review-prune-candidates
overall_state=pass
EOF
perl -0pi -e "s#__LOG_ROOT__#$LOG_ROOT#g; s#__RETENTION_ROOT__#$RETENTION_LOG_ROOT#g" "$RETENTION_LOG_ROOT/latest-status.txt"
printf '%s\n' "20260401-retention-preview" > "$RETENTION_LOG_ROOT/latest-run.txt"
ln -sfn "20260401-retention-preview" "$RETENTION_LOG_ROOT/latest"

MISSING_CONFIRM_OUTPUT="$TMP_DIR/missing-confirm.log"
set +e
DOCGEN_READONLY_INSPECTION_KEEP_RUNS=2 \
DOCGEN_READONLY_RETENTION_LOG_ROOT="$RETENTION_LOG_ROOT" \
DOCGEN_PRUNE_EXECUTE=1 \
bash "$SCRIPT" "$LOG_ROOT" >"$MISSING_CONFIRM_OUTPUT" 2>&1
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "execute without confirmation unexpectedly succeeded"
assert_contains "missing DOCGEN_PRUNE_CONFIRM_RUN_ID" "$MISSING_CONFIRM_OUTPUT"
[[ -d "$LOG_ROOT/20260401-120000" ]] || fail "missing confirm path deleted oldest run"

NONE_CONFIRM_OUTPUT="$TMP_DIR/none-confirm.log"
set +e
DOCGEN_READONLY_INSPECTION_KEEP_RUNS=2 \
DOCGEN_READONLY_RETENTION_LOG_ROOT="$RETENTION_LOG_ROOT" \
DOCGEN_PRUNE_EXECUTE=1 \
DOCGEN_PRUNE_CONFIRM_RUN_ID=20260401-retention-preview \
DOCGEN_PRUNE_CONFIRM_CANDIDATES=none \
bash "$SCRIPT" "$LOG_ROOT" >"$NONE_CONFIRM_OUTPUT" 2>&1
rc=$?
set -e
[[ "$rc" -ne 0 ]] || fail "execute with none candidates unexpectedly succeeded"
assert_contains "confirm candidates cannot be none" "$NONE_CONFIRM_OUTPUT"
[[ -d "$LOG_ROOT/20260401-120000" ]] || fail "none confirm path deleted oldest run"

EXEC_OUTPUT="$TMP_DIR/execute.log"
DOCGEN_READONLY_INSPECTION_KEEP_RUNS=2 \
DOCGEN_READONLY_RETENTION_LOG_ROOT="$RETENTION_LOG_ROOT" \
DOCGEN_PRUNE_EXECUTE=1 \
DOCGEN_PRUNE_CONFIRM_RUN_ID=20260401-retention-preview \
DOCGEN_PRUNE_CONFIRM_CANDIDATES=20260401-120000 \
bash "$SCRIPT" "$LOG_ROOT" >"$EXEC_OUTPUT" 2>&1

assert_contains "latest_retention_status=$RETENTION_LOG_ROOT/latest-status.txt" "$EXEC_OUTPUT"
assert_contains "mode=execute" "$EXEC_OUTPUT"
assert_contains "confirm_run_id=20260401-retention-preview" "$EXEC_OUTPUT"
assert_contains "confirm_candidates=20260401-120000" "$EXEC_OUTPUT"
assert_contains "[OK] pruned_runs=20260401-120000" "$EXEC_OUTPUT"
[[ ! -d "$LOG_ROOT/20260401-120000" ]] || {
  echo "[FAIL] execute did not prune oldest run" >&2
  exit 1
}
[[ -d "$LOG_ROOT/20260401-121000" ]] || {
  echo "[FAIL] execute pruned retained run 20260401-121000" >&2
  exit 1
}
[[ -d "$LOG_ROOT/20260401-122000" ]] || {
  echo "[FAIL] execute pruned retained run 20260401-122000" >&2
  exit 1
}
assert_contains "20260401-122000" <(readlink "$LOG_ROOT/latest")
assert_contains "20260401-122000" "$LOG_ROOT/latest-run.txt"
assert_contains "summary" "$LOG_ROOT/latest-status.txt"

echo "[PASS] prune_docgen_server_readonly_inspection_logs regression checks passed"
