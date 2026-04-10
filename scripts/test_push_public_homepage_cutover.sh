#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUSH_SCRIPT="$ROOT/scripts/push_public_homepage_cutover.sh"
DOMAIN="${1:-doc.niyoufei.com}"
REMOTE_HOST="${2:-root@199.180.118.204}"
VERIFY_BASE_URL="${DOCGEN_TEST_VERIFY_BASE_URL:-https://${DOMAIN}}"
VERIFY_RESOLVE_IP="${DOCGEN_TEST_VERIFY_RESOLVE_IP:-199.180.118.204}"
SSL_PROFILE="${DOCGEN_TEST_SSL_PROFILE:-letsencrypt}"

TMP_DIR="$(mktemp -d)"
MOCK_LOG="$TMP_DIR/mock.log"
PREVIEW_LOG="$TMP_DIR/preview.log"
DRY_RUN_LOG="$TMP_DIR/dry-run.log"
APPLY_LOG="$TMP_DIR/apply.log"
NO_INSTALL_LOG="$TMP_DIR/no-install.log"

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
DOCGEN_VERIFY_BASE_URL="$VERIFY_BASE_URL" \
DOCGEN_VERIFY_RESOLVE_IP="$VERIFY_RESOLVE_IP" \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$PREVIEW_LOG"

assert_contains "remote_apply=0" "$PREVIEW_LOG"
assert_contains "verify_base_url=${VERIFY_BASE_URL}" "$PREVIEW_LOG"
assert_contains "verify_resolve_ip=${VERIFY_RESOLVE_IP}" "$PREVIEW_LOG"
assert_contains "scp_command=" "$PREVIEW_LOG"
assert_contains "ssh_command=" "$PREVIEW_LOG"

echo "[STEP] mock dry-run"
: > "$MOCK_LOG"
TMP_PUSH_LOG="$MOCK_LOG" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp.sh" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh.sh" \
DOCGEN_VERIFY_BASE_URL="$VERIFY_BASE_URL" \
DOCGEN_VERIFY_RESOLVE_IP="$VERIFY_RESOLVE_IP" \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$DRY_RUN_LOG"

assert_contains "[OK] uploaded and dry-ran public homepage cutover" "$DRY_RUN_LOG"
assert_contains "scp:" "$MOCK_LOG"
assert_contains "ssh-host:${REMOTE_HOST}" "$MOCK_LOG"
assert_contains "export DOCGEN_VERIFY_BASE_URL=${VERIFY_BASE_URL}" "$MOCK_LOG"
assert_contains "export DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_IP}" "$MOCK_LOG"
assert_contains "bash ./execute_public_homepage_cutover.sh ${DOMAIN}" "$MOCK_LOG"
assert_not_contains "DOCGEN_APPLY=1" "$MOCK_LOG"

echo "[STEP] mock apply"
: > "$MOCK_LOG"
TMP_PUSH_LOG="$MOCK_LOG" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp.sh" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh.sh" \
DOCGEN_REMOTE_APPLY=1 \
DOCGEN_SSL_PROFILE="$SSL_PROFILE" \
DOCGEN_VERIFY_BASE_URL="$VERIFY_BASE_URL" \
DOCGEN_VERIFY_RESOLVE_IP="$VERIFY_RESOLVE_IP" \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$APPLY_LOG"

assert_contains "[OK] uploaded and applied public homepage cutover" "$APPLY_LOG"
assert_contains "DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${SSL_PROFILE} bash ./execute_public_homepage_cutover.sh ${DOMAIN}" "$MOCK_LOG"
assert_contains "export DOCGEN_VERIFY_BASE_URL=${VERIFY_BASE_URL}" "$MOCK_LOG"
assert_contains "export DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_IP}" "$MOCK_LOG"

echo "[STEP] mock no-install"
: > "$MOCK_LOG"
TMP_PUSH_LOG="$MOCK_LOG" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp.sh" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh.sh" \
DOCGEN_REMOTE_INSTALL=0 \
DOCGEN_VERIFY_BASE_URL="$VERIFY_BASE_URL" \
DOCGEN_VERIFY_RESOLVE_IP="$VERIFY_RESOLVE_IP" \
bash "$PUSH_SCRIPT" "$DOMAIN" "$REMOTE_HOST" >"$NO_INSTALL_LOG"

assert_contains "[OK] uploaded and dry-ran public homepage cutover" "$NO_INSTALL_LOG"
assert_contains "bash ./execute_public_homepage_cutover.sh ${DOMAIN}" "$MOCK_LOG"
assert_not_contains "install_bundle_on_origin.sh" "$MOCK_LOG"
assert_not_contains "verify_linux_domain_origin.sh" "$MOCK_LOG"

echo "[PASS] push_public_homepage_cutover regression checks passed"
