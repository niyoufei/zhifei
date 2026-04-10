#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_remote_docgen_server_release_dir.sh"
TMP_DIR="$(mktemp -d)"
CALLS="$TMP_DIR/calls.log"
MOCK_VERIFY="$TMP_DIR/local-verify.sh"

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

cat > "$MOCK_VERIFY" <<'EOF'
#!/usr/bin/env bash
echo "LOCAL_VERIFY"
EOF
chmod +x "$MOCK_VERIFY"

cat > "$TMP_DIR/mock-ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
payload="$(cat)"
printf 'ssh %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
printf 'stdin %s\n' "$payload" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-ssh"

OUTPUT="$TMP_DIR/output.log"
DOCGEN_RELEASE_VERIFY_SCRIPT="$MOCK_VERIFY" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_TEST_CALLS="$CALLS" \
bash "$VERIFY_SCRIPT" "root@example.com" >"$OUTPUT" 2>&1

assert_contains "ssh root@example.com bash -s -- /opt/docgen/releases" "$CALLS"
assert_contains "stdin #!/usr/bin/env bash" "$CALLS"
assert_contains "LOCAL_VERIFY" "$CALLS"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_PREVIEW=1 \
DOCGEN_RELEASE_VERIFY_SCRIPT="$MOCK_VERIFY" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
bash "$VERIFY_SCRIPT" "root@example.com" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "remote_host=root@example.com" "$PREVIEW_OUTPUT"
assert_contains "remote_release_dir=/opt/docgen/releases" "$PREVIEW_OUTPUT"
assert_contains "verify_script=$MOCK_VERIFY" "$PREVIEW_OUTPUT"
assert_contains "ssh_command=" "$PREVIEW_OUTPUT"

echo "[PASS] verify_remote_docgen_server_release_dir regression checks passed"
