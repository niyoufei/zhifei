#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_remote_ui_upload_outline_chain.sh"
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
sleep 60
EOF
chmod +x "$TMP_DIR/mock-ssh"

cat > "$TMP_DIR/mock-curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'curl %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
exit 0
EOF
chmod +x "$TMP_DIR/mock-curl"

cat > "$TMP_DIR/mock-verify" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'verify %s\n' "${DOCGEN_UI_BASE_URL:-missing}" >>"${DOCGEN_TEST_CALLS:?}"
echo "[SUMMARY] all checks passed."
EOF
chmod +x "$TMP_DIR/mock-verify"

OUTPUT="$TMP_DIR/output.log"

DOCGEN_UI_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_UI_CURL_BIN="$TMP_DIR/mock-curl" \
DOCGEN_UI_VERIFY_SCRIPT="$TMP_DIR/mock-verify" \
DOCGEN_TEST_CALLS="$CALLS" \
bash "$VERIFY_SCRIPT" "root@example.com" >"$OUTPUT" 2>&1

assert_contains "[INFO] ssh_target=root@example.com" "$OUTPUT"
assert_contains "[OK] tunnel ready: http://127.0.0.1:18501" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
assert_contains "ssh -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -L 18501:127.0.0.1:8501 root@example.com -N" "$CALLS"
assert_contains "curl -fsS http://127.0.0.1:18501" "$CALLS"
assert_contains "verify http://127.0.0.1:18501" "$CALLS"

echo "[PASS] verify_remote_ui_upload_outline_chain regression checks passed"
