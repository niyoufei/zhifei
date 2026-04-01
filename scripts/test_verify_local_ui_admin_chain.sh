#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/verify_local_ui_admin_chain.sh"
TMP_DIR="$(mktemp -d)"
CALLS="$TMP_DIR/calls.log"
UI_SCRIPT="$TMP_DIR/mock_ui.sh"
ADMIN_SCRIPT="$TMP_DIR/mock_admin.sh"
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

cat > "$UI_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ui\n' >>"${DOCGEN_TEST_CALLS:?}"
echo "ui smoke ok"
EOF

cat > "$ADMIN_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'admin\n' >>"${DOCGEN_TEST_CALLS:?}"
echo "api_port=${DOCGEN_ADMIN_SMOKE_PORT:-}"
echo "backend_port=${DOCGEN_ADMIN_UI_SMOKE_BACKEND_PORT:-}"
echo "web_port=${DOCGEN_ADMIN_UI_SMOKE_WEB_PORT:-}"
echo "admin smoke ok"
EOF

chmod +x "$UI_SCRIPT" "$ADMIN_SCRIPT"

DOCGEN_TEST_CALLS="$CALLS" \
DOCGEN_LOCAL_UI_SCRIPT="$UI_SCRIPT" \
DOCGEN_LOCAL_ADMIN_CHAIN_SCRIPT="$ADMIN_SCRIPT" \
DOCGEN_LOCAL_UI_ADMIN_LOG_ROOT="$TMP_DIR/logs" \
DOCGEN_LOCAL_UI_ADMIN_RUN_ID="browser-run" \
bash "$SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[INFO] run_ui=1 run_admin=1" "$OUTPUT"
assert_contains "[INFO] admin_api_port=18110 admin_panel_backend_port=18112 admin_panel_web_port=18612" "$OUTPUT"
assert_contains "[OK] local ui upload outline chain: passed (log=local-ui-upload-outline-chain.log)" "$OUTPUT"
assert_contains "[OK] local admin ops chain: passed (log=local-admin-ops-chain.log)" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
assert_contains "ui" "$CALLS"
assert_contains "admin" "$CALLS"
assert_contains "ui smoke ok" "$TMP_DIR/logs/browser-run/local-ui-upload-outline-chain.log"
assert_contains "api_port=18110" "$TMP_DIR/logs/browser-run/local-admin-ops-chain.log"
assert_contains "backend_port=18112" "$TMP_DIR/logs/browser-run/local-admin-ops-chain.log"
assert_contains "web_port=18612" "$TMP_DIR/logs/browser-run/local-admin-ops-chain.log"
assert_contains "admin smoke ok" "$TMP_DIR/logs/browser-run/local-admin-ops-chain.log"

echo "[PASS] verify_local_ui_admin_chain regression checks passed"
