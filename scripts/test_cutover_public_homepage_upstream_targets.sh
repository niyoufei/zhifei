#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/cutover_public_homepage_upstream_targets.sh"
DOMAIN="${1:-doc.niyoufei.com}"
TMP_DIR="$(mktemp -d)"
CONF_DIR="$TMP_DIR/nginx"
BIN_DIR="$TMP_DIR/bin"
LOG_FILE="$TMP_DIR/mock.log"
DOC_CONF="$CONF_DIR/doc.conf"
ALONE_CONF="$CONF_DIR/alone.conf"

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

write_confs() {
  mkdir -p "$CONF_DIR"
  cat > "$DOC_CONF" <<EOF
server {
    listen 23890 ssl;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
EOF

  cat > "$ALONE_CONF" <<EOF
server {
    listen 31302;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
server {
    listen 31300;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
EOF
}

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/nginx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'nginx %s\n' "$*" >> "$MOCK_LOG_FILE"
if [[ "${DOCGEN_FAIL_NGINX_T:-0}" = "1" && "${1:-}" = "-t" ]]; then
  exit 1
fi
exit 0
EOF

cat > "$BIN_DIR/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'systemctl %s\n' "$*" >> "$MOCK_LOG_FILE"
exit 0
EOF

chmod +x "$BIN_DIR/nginx" "$BIN_DIR/systemctl"

echo "[STEP] dry-run"
write_confs
MOCK_LOG_FILE="$LOG_FILE" PATH="$BIN_DIR:$PATH" bash "$SCRIPT" "$DOMAIN" "$DOC_CONF" "$ALONE_CONF" > "$TMP_DIR/dry-run.log"
assert_contains "[INFO] dry-run only; no files written." "$TMP_DIR/dry-run.log"
assert_contains "proxy_pass http://127.0.0.1:3000;" "$TMP_DIR/dry-run.log"

echo "[STEP] apply success"
write_confs
: > "$LOG_FILE"
DOCGEN_APPLY=1 DOCGEN_OS_NAME=Linux MOCK_LOG_FILE="$LOG_FILE" PATH="$BIN_DIR:$PATH" bash "$SCRIPT" "$DOMAIN" "$DOC_CONF" "$ALONE_CONF" > "$TMP_DIR/apply.log"
assert_contains "[OK] upstream targets updated" "$TMP_DIR/apply.log"
assert_contains "proxy_pass http://127.0.0.1:8501;" "$DOC_CONF"
assert_contains "proxy_pass http://127.0.0.1:8501;" "$ALONE_CONF"
assert_contains "systemctl reload nginx" "$LOG_FILE"

echo "[STEP] apply rollback on nginx -t failure"
write_confs
: > "$LOG_FILE"
if DOCGEN_APPLY=1 DOCGEN_OS_NAME=Linux DOCGEN_FAIL_NGINX_T=1 MOCK_LOG_FILE="$LOG_FILE" PATH="$BIN_DIR:$PATH" bash "$SCRIPT" "$DOMAIN" "$DOC_CONF" "$ALONE_CONF" > "$TMP_DIR/fail.log" 2>&1; then
  fail "expected failure when nginx -t fails"
fi
assert_contains "[ERROR] nginx -t failed after upstream rewrite." "$TMP_DIR/fail.log"
assert_contains "proxy_pass http://127.0.0.1:3000;" "$DOC_CONF"
assert_contains "proxy_pass http://127.0.0.1:3000;" "$ALONE_CONF"

echo "[PASS] cutover_public_homepage_upstream_targets regression checks passed"
