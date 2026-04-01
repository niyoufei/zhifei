#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/verify_local_admin_ops_chain.sh"
TMP_DIR="$(mktemp -d)"
CALLS="$TMP_DIR/calls.log"
API_SCRIPT="$TMP_DIR/mock_api.sh"
PANEL_SCRIPT="$TMP_DIR/mock_panel.sh"
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

cat > "$API_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'api\n' >>"${DOCGEN_TEST_CALLS:?}"
echo "api smoke ok"
EOF

cat > "$PANEL_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'panel\n' >>"${DOCGEN_TEST_CALLS:?}"
echo "panel smoke ok"
EOF

chmod +x "$API_SCRIPT" "$PANEL_SCRIPT"

DOCGEN_TEST_CALLS="$CALLS" \
DOCGEN_LOCAL_ADMIN_API_SCRIPT="$API_SCRIPT" \
DOCGEN_LOCAL_ADMIN_PANEL_SCRIPT="$PANEL_SCRIPT" \
DOCGEN_LOCAL_ADMIN_LOG_ROOT="$TMP_DIR/logs" \
DOCGEN_LOCAL_ADMIN_RUN_ID="smoke-run" \
bash "$SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[INFO] run_api=1 run_panel=1" "$OUTPUT"
assert_contains "[OK] local admin api smoke: passed (log=local-admin-api-smoke.log)" "$OUTPUT"
assert_contains "[OK] local admin panel smoke: passed (log=local-admin-panel-smoke.log)" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
assert_contains "api" "$CALLS"
assert_contains "panel" "$CALLS"
assert_contains "api smoke ok" "$TMP_DIR/logs/smoke-run/local-admin-api-smoke.log"
assert_contains "panel smoke ok" "$TMP_DIR/logs/smoke-run/local-admin-panel-smoke.log"

echo "[PASS] verify_local_admin_ops_chain regression checks passed"
