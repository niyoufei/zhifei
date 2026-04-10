#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_remote_full_chain.sh"
TMP_DIR="$(mktemp -d)"
CALLS="$TMP_DIR/calls.log"

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

cat > "$TMP_DIR/mock-ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ssh %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-ssh"

cat > "$TMP_DIR/mock-ui" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ui %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-ui"

OUTPUT="$TMP_DIR/output.log"
LOG_ROOT="$TMP_DIR/logs"

DOCGEN_REMOTE_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_REMOTE_UI_SCRIPT="$TMP_DIR/mock-ui" \
DOCGEN_REMOTE_LOG_ROOT="$LOG_ROOT" \
DOCGEN_REMOTE_RUN_ID="case01" \
DOCGEN_TEST_CALLS="$CALLS" \
bash "$VERIFY_SCRIPT" "root@example.com" >"$OUTPUT" 2>&1

assert_contains "[INFO] log_dir=$LOG_ROOT/case01" "$OUTPUT"
assert_contains "[OK] ui upload outline chain: passed" "$OUTPUT"
assert_contains "[OK] runtime health: passed" "$OUTPUT"
assert_contains "[OK] upload parse chain: passed" "$OUTPUT"
assert_contains "[OK] generate export chain: passed" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
assert_contains "ui root@example.com" "$CALLS"
assert_contains "ssh root@example.com cd /opt/docgen && bash ./scripts/report_docgen_runtime_health_stable.sh https://doc.niyoufei.com" "$CALLS"
assert_contains "ssh root@example.com cd /opt/docgen && bash ./scripts/verify_upload_parse_chain.sh" "$CALLS"
assert_contains "ssh root@example.com cd /opt/docgen && bash ./scripts/verify_generate_export_chain.sh" "$CALLS"
[[ -f "$LOG_ROOT/case01/ui-upload-outline-chain.log" ]] || exit 1
[[ -f "$LOG_ROOT/case01/runtime-health.log" ]] || exit 1
[[ -f "$LOG_ROOT/case01/upload-parse-chain.log" ]] || exit 1
[[ -f "$LOG_ROOT/case01/generate-export-chain.log" ]] || exit 1

echo "[PASS] verify_remote_full_chain regression checks passed"
