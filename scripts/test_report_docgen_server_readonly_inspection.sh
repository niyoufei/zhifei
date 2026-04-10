#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/report_docgen_server_readonly_inspection.sh"
TMP_DIR="$(mktemp -d)"
APP_ROOT="$TMP_DIR/app"
SCRIPTS_DIR="$APP_ROOT/scripts"
LOG_ROOT="$TMP_DIR/logs"
OUTPUT="$TMP_DIR/output.log"
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

mkdir -p "$SCRIPTS_DIR" "$APP_ROOT/releases"

cat > "$SCRIPTS_DIR/mock-release-verify.sh" <<'EOF'
#!/usr/bin/env bash
echo "RELEASE_VERIFY_OK $1"
EOF

cat > "$SCRIPTS_DIR/mock-worktree-verify.sh" <<'EOF'
#!/usr/bin/env bash
echo "WORKTREE_VERIFY_OK $1 $2"
EOF

cat > "$SCRIPTS_DIR/mock-runtime-report.sh" <<'EOF'
#!/usr/bin/env bash
echo "runtime_monitoring_state=pass"
echo "next_action=healthy"
echo "RUNTIME_REPORT_OK $1"
EOF

cat > "$SCRIPTS_DIR/mock-retention-report.sh" <<'EOF'
#!/usr/bin/env bash
mkdir -p "${DOCGEN_READONLY_RETENTION_LOG_ROOT:?}/20260401-retention-test"
cat > "${DOCGEN_READONLY_RETENTION_LOG_ROOT:?}/latest-status.txt" <<STATUS
run_id=20260401-retention-test
inspection_log_root=${DOCGEN_READONLY_INSPECTION_LOG_ROOT:?}
retention_log_root=${DOCGEN_READONLY_RETENTION_LOG_ROOT:?}
log_dir=${DOCGEN_READONLY_RETENTION_LOG_ROOT:?}/20260401-retention-test
keep_runs=10
existing_runs_count=2
latest_run=20260401-readonly-test
prune_candidates_count=0
prune_candidates=none
mode=preview
execute_allowed=no
next_action=healthy
overall_state=pass
STATUS
printf '%s\n' "20260401-retention-test" > "${DOCGEN_READONLY_RETENTION_LOG_ROOT:?}/latest-run.txt"
ln -sfn "20260401-retention-test" "${DOCGEN_READONLY_RETENTION_LOG_ROOT:?}/latest"
echo "RETENTION_REPORT_OK $1"
EOF

chmod 755 \
  "$SCRIPTS_DIR/mock-release-verify.sh" \
  "$SCRIPTS_DIR/mock-worktree-verify.sh" \
  "$SCRIPTS_DIR/mock-runtime-report.sh" \
  "$SCRIPTS_DIR/mock-retention-report.sh"

DOCGEN_RELEASE_VERIFY_SCRIPT="$SCRIPTS_DIR/mock-release-verify.sh" \
DOCGEN_WORKTREE_VERIFY_SCRIPT="$SCRIPTS_DIR/mock-worktree-verify.sh" \
DOCGEN_RUNTIME_REPORT_SCRIPT="$SCRIPTS_DIR/mock-runtime-report.sh" \
DOCGEN_RETENTION_REPORT_SCRIPT="$SCRIPTS_DIR/mock-retention-report.sh" \
DOCGEN_READONLY_INSPECTION_LOG_ROOT="$LOG_ROOT" \
DOCGEN_READONLY_RETENTION_LOG_ROOT="$RETENTION_LOG_ROOT" \
DOCGEN_READONLY_INSPECTION_RUN_ID="20260401-readonly-test" \
bash "$SCRIPT" "$APP_ROOT" "https://example.test" >"$OUTPUT" 2>&1

assert_contains "[OK] app_root=$APP_ROOT" "$OUTPUT"
assert_contains "[OK] release_dir=$APP_ROOT/releases" "$OUTPUT"
assert_contains "[OK] target_url=https://example.test" "$OUTPUT"
assert_contains "[OK] log_dir=$LOG_ROOT/20260401-readonly-test" "$OUTPUT"
assert_contains "[OK] release-dir: $LOG_ROOT/20260401-readonly-test/release-dir.log" "$OUTPUT"
assert_contains "[OK] server-worktree: $LOG_ROOT/20260401-readonly-test/server-worktree.log" "$OUTPUT"
assert_contains "[OK] runtime-health: $LOG_ROOT/20260401-readonly-test/runtime-health.log" "$OUTPUT"
assert_contains "[OK] readonly-retention: $LOG_ROOT/20260401-readonly-test/readonly-retention.log" "$OUTPUT"
assert_contains "[OK] summary: $LOG_ROOT/20260401-readonly-test/summary.txt" "$OUTPUT"
assert_contains "[OK] latest link: $LOG_ROOT/latest -> 20260401-readonly-test" "$OUTPUT"
assert_contains "[OK] latest status: $LOG_ROOT/latest-status.txt" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

assert_contains "RELEASE_VERIFY_OK $APP_ROOT/releases" "$LOG_ROOT/20260401-readonly-test/release-dir.log"
assert_contains "WORKTREE_VERIFY_OK $APP_ROOT $APP_ROOT/releases" "$LOG_ROOT/20260401-readonly-test/server-worktree.log"
assert_contains "RUNTIME_REPORT_OK https://example.test" "$LOG_ROOT/20260401-readonly-test/runtime-health.log"
assert_contains "RETENTION_REPORT_OK $APP_ROOT" "$LOG_ROOT/20260401-readonly-test/readonly-retention.log"
assert_contains "run_id=20260401-readonly-test" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "release_dir_state=pass" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "server_worktree_state=pass" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "runtime_monitoring_state=pass" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "readonly_retention_state=pass" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "readonly_retention_run_id=20260401-retention-test" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "readonly_retention_prune_candidates_count=0" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "readonly_retention_execute_allowed=no" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "next_action=healthy" "$LOG_ROOT/20260401-readonly-test/summary.txt"
assert_contains "overall_state=pass" "$LOG_ROOT/20260401-readonly-test/summary.txt"
[[ -L "$LOG_ROOT/latest" ]] || {
  echo "[FAIL] missing latest symlink" >&2
  exit 1
}
assert_contains "20260401-readonly-test" <(readlink "$LOG_ROOT/latest")
assert_contains "run_id=20260401-readonly-test" "$LOG_ROOT/latest-status.txt"

echo "[PASS] report_docgen_server_readonly_inspection regression checks passed"
