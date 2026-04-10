#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/execute_public_homepage_cutover.sh"
DOMAIN="${1:-doc.niyoufei.com}"
TMP_DIR="$(mktemp -d)"
NGINX_DIR="$TMP_DIR/nginx"
XRAY_DIR="$TMP_DIR/xray"
OUT_LOG="$TMP_DIR/out.log"

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
  if grep -Fq -- "$needle" "$file"; then
    echo "[FAIL] unexpected text present: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

mkdir -p "$NGINX_DIR" "$XRAY_DIR"

cat > "$NGINX_DIR/doc.conf" <<EOF
server {
    listen 23890 ssl;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
EOF

cat > "$NGINX_DIR/alone.conf" <<EOF
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

cat > "$XRAY_DIR/02_VLESS_TCP_inbounds.json" <<EOF
{
  "fallbacks": [
    {"dest": 31302}
  ]
}
EOF

cat > "$XRAY_DIR/04_trojan_TCP_inbounds.json" <<EOF
{
  "fallbacks": [
    {"dest": 31300}
  ]
}
EOF

cat > "$XRAY_DIR/07_VLESS_vision_reality_inbounds.json" <<EOF
{
  "target": "${DOMAIN}:23890"
}
EOF

echo "[STEP] execute dry-run on multi-upstream topology"
DOCGEN_OS_NAME=Linux DOCGEN_NGINX_SEARCH_DIRS="$NGINX_DIR" DOCGEN_XRAY_SEARCH_DIR="$XRAY_DIR" DOCGEN_VERIFY_BASE_URL="http://127.0.0.1:8501" \
  bash "$SCRIPT" "$DOMAIN" > "$OUT_LOG"
assert_contains "[RECOMMEND] topology=xray-nginx-multi-upstream" "$OUT_LOG"
assert_contains "[STEP] dry-run multi-upstream cutover" "$OUT_LOG"
assert_contains "[INFO] dry-run only; no files written." "$OUT_LOG"
assert_contains "cutover_public_homepage_upstream_targets.sh ${DOMAIN} $NGINX_DIR/alone.conf $NGINX_DIR/doc.conf" "$OUT_LOG"
assert_not_contains "[BLOCKED] 命中多个 conf" "$OUT_LOG"

echo "[PASS] execute_public_homepage_cutover multi-upstream regression checks passed"
