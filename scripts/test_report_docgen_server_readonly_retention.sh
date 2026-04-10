#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/report_docgen_server_readonly_retention.sh"
TMP_DIR="$(mktemp -d)"
APP_ROOT="$TMP_DIR/app"
SCRIPTS_DIR="$APP_ROOT/scripts"
INSPECTION_LOG_ROOT="$TMP_DIR/readonly_inspection"
RETENTION_LOG_ROOT="$TMP_DIR/readonly_retention"
OUTPUT="$TMP_DIR/output.log"

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

mkdir -p "$SCRIPTS_DIR" "$INSPECTION_LOG_ROOT/20260401-120000" "$INSPECTION_LOG_ROOT/20260401-121000"
printf '%s\n' "20260401-121000" > "$INSPECTION_LOG_ROOT/latest-run.txt"
ln -sfn "20260401-121000" "$INSPECTION_LOG_ROOT/latest"

cat > "$SCRIPTS_DIR/mock-prune.sh" <<'EOF'
#!/usr/bin/env bash
echo "log_root=$1"
echo "keep_runs=${DOCGEN_READONLY_INSPECTION_KEEP_RUNS:-missing}"
echo "existing_runs_count=2"
echo "latest_run=20260401-121000"
echo "prune_candidates_count=0"
echo "prune_candidates=none"
echo "mode=preview"
echo "[OK] preview_only=1"
echo "[SUMMARY] all checks passed."
EOF
chmod 755 "$SCRIPTS_DIR/mock-prune.sh"

DOCGEN_READONLY_RETENTION_PRUNE_SCRIPT="$SCRIPTS_DIR/mock-prune.sh" \
DOCGEN_READONLY_INSPECTION_LOG_ROOT="$INSPECTION_LOG_ROOT" \
DOCGEN_READONLY_RETENTION_LOG_ROOT="$RETENTION_LOG_ROOT" \
DOCGEN_READONLY_RETENTION_RUN_ID="20260401-retention-test" \
DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 \
bash "$SCRIPT" "$APP_ROOT" >"$OUTPUT" 2>&1

assert_contains "[OK] app_root=$APP_ROOT" "$OUTPUT"
assert_contains "[OK] inspection_log_root=$INSPECTION_LOG_ROOT" "$OUTPUT"
assert_contains "[OK] retention_log_root=$RETENTION_LOG_ROOT" "$OUTPUT"
assert_contains "[OK] keep_runs=10" "$OUTPUT"
assert_contains "[OK] log_dir=$RETENTION_LOG_ROOT/20260401-retention-test" "$OUTPUT"
assert_contains "[OK] prune-preview: $RETENTION_LOG_ROOT/20260401-retention-test/prune-preview.log" "$OUTPUT"
assert_contains "[OK] summary: $RETENTION_LOG_ROOT/20260401-retention-test/summary.txt" "$OUTPUT"
assert_contains "[OK] latest link: $RETENTION_LOG_ROOT/latest -> 20260401-retention-test" "$OUTPUT"
assert_contains "[OK] latest status: $RETENTION_LOG_ROOT/latest-status.txt" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

assert_contains "keep_runs=10" "$RETENTION_LOG_ROOT/20260401-retention-test/prune-preview.log"
assert_contains "prune_candidates_count=0" "$RETENTION_LOG_ROOT/20260401-retention-test/summary.txt"
assert_contains "execute_allowed=no" "$RETENTION_LOG_ROOT/20260401-retention-test/summary.txt"
assert_contains "next_action=healthy" "$RETENTION_LOG_ROOT/20260401-retention-test/summary.txt"
assert_contains "overall_state=pass" "$RETENTION_LOG_ROOT/20260401-retention-test/summary.txt"
[[ -L "$RETENTION_LOG_ROOT/latest" ]] || {
  echo "[FAIL] missing latest symlink" >&2
  exit 1
}
assert_contains "20260401-retention-test" <(readlink "$RETENTION_LOG_ROOT/latest")
assert_contains "run_id=20260401-retention-test" "$RETENTION_LOG_ROOT/latest-status.txt"

echo "[PASS] report_docgen_server_readonly_retention regression checks passed"
