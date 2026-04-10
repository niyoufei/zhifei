#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUSH_SCRIPT="$ROOT/scripts/push_linux_domain_bundle.sh"
DOMAIN="${1:-doc.niyoufei.com}"
REMOTE_HOST="${2:-root@199.180.118.204}"

TMP_DIR="$(mktemp -d)"
MOCK_LOG="$TMP_DIR/mock.log"
PREVIEW_LOG="$TMP_DIR/preview.log"
INSTALL_LOG="$TMP_DIR/install.log"
UPLOAD_ONLY_LOG="$TMP_DIR/upload-only.log"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

assert_contains() {
  local needle="$1"
  local file="$2"
  if ! grep -Fq "$needle" "$file"; then
    echo "[FAIL] missing expected text: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

assert_not_contains() {
  local needle="$1"
  local file="$2"
  if grep -Fq "$needle" "$file"; then
    echo "[FAIL] unexpected text present: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

cat > "$TMP_DIR/mock-scp.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'scp:%s\n' "$*" >> "$TMP_PUSH_LOG"
EOF

cat > "$TMP_DIR/mock-ssh.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ssh-host:%s\n' "$1" >> "$TMP_PUSH_LOG"
printf 'ssh-cmd:%s\n' "$2" >> "$TMP_PUSH_LOG"
EOF

chmod +x "$TMP_DIR/mock-scp.sh" "$TMP_DIR/mock-ssh.sh"

echo "[STEP] preview"
DOCGEN_PREVIEW=1 \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp.sh" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh.sh" \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$PREVIEW_LOG"

assert_contains "remote_install=1" "$PREVIEW_LOG"
assert_contains "scp_bin=$TMP_DIR/mock-scp.sh" "$PREVIEW_LOG"
assert_contains "ssh_bin=$TMP_DIR/mock-ssh.sh" "$PREVIEW_LOG"
assert_contains "scp_command=" "$PREVIEW_LOG"
assert_contains "ssh_command=" "$PREVIEW_LOG"
assert_contains "install_bundle_on_origin.sh" "$PREVIEW_LOG"
assert_contains "verify_linux_domain_origin.sh ${DOMAIN}" "$PREVIEW_LOG"

echo "[STEP] mock install"
: > "$MOCK_LOG"
TMP_PUSH_LOG="$MOCK_LOG" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp.sh" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh.sh" \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$INSTALL_LOG"

assert_contains "[OK] uploaded and installed: ${DOMAIN} -> ${REMOTE_HOST}" "$INSTALL_LOG"
assert_contains "scp:" "$MOCK_LOG"
assert_contains "ssh-host:${REMOTE_HOST}" "$MOCK_LOG"
assert_contains "mkdir -p ~/docgen-domain" "$MOCK_LOG"
assert_contains "tar -xzf ~/${DOMAIN}.nginx.tar.gz -C ~/docgen-domain" "$MOCK_LOG"
assert_contains "bash ./detect_linux_proxy_stack.sh ${DOMAIN}" "$MOCK_LOG"
assert_contains "bash ./suggest_linux_origin_fix.sh ${DOMAIN}" "$MOCK_LOG"
assert_contains "sudo -E ./install_bundle_on_origin.sh" "$MOCK_LOG"
assert_contains "DOCGEN_PROXY_STACK=nginx bash ./verify_linux_domain_origin.sh ${DOMAIN}" "$MOCK_LOG"

echo "[STEP] mock upload only"
: > "$MOCK_LOG"
TMP_PUSH_LOG="$MOCK_LOG" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp.sh" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh.sh" \
DOCGEN_REMOTE_INSTALL=0 \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$UPLOAD_ONLY_LOG"

assert_contains "[OK] uploaded only: $ROOT/build/domain_bundle_release/${DOMAIN}.nginx.tar.gz -> ${REMOTE_HOST}:~/${DOMAIN}.nginx.tar.gz" "$UPLOAD_ONLY_LOG"
assert_contains "scp:" "$MOCK_LOG"
assert_not_contains "ssh-host:${REMOTE_HOST}" "$MOCK_LOG"
assert_not_contains "install_bundle_on_origin.sh" "$MOCK_LOG"
assert_not_contains "verify_linux_domain_origin.sh ${DOMAIN}" "$MOCK_LOG"

echo "[PASS] push_linux_domain_bundle regression checks passed"
