#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/verify_remote_docgen_server_status.sh"
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

OUTPUT="$TMP_DIR/output.log"
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_TEST_CALLS="$CALLS" \
bash "$SCRIPT" "root@example.com" >"$OUTPUT" 2>&1

assert_contains "ssh root@example.com bash '/opt/docgen/scripts/show_docgen_server_status.sh' '/opt/docgen'" "$CALLS"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_PREVIEW=1 \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
bash "$SCRIPT" "root@example.com" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "remote_host=root@example.com" "$PREVIEW_OUTPUT"
assert_contains "remote_app_dir=/opt/docgen" "$PREVIEW_OUTPUT"
assert_contains "remote_script=/opt/docgen/scripts/show_docgen_server_status.sh" "$PREVIEW_OUTPUT"
assert_contains "ssh_command=" "$PREVIEW_OUTPUT"

echo "[PASS] verify_remote_docgen_server_status regression checks passed"
