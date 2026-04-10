#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/inspect_public_homepage_live_topology.sh"
DOMAIN="${1:-doc.niyoufei.com}"
TMP_DIR="$(mktemp -d)"
NGINX_DIR="$TMP_DIR/nginx"
XRAY_DIR="$TMP_DIR/xray"
OUT_MULTI="$TMP_DIR/multi.log"
OUT_SINGLE="$TMP_DIR/single.log"

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
    {"dest": 31302},
    {"dest": 31296}
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

echo "[STEP] inspect xray+nginx multi-upstream topology"
DOCGEN_OS_NAME=Linux DOCGEN_NGINX_SEARCH_DIRS="$NGINX_DIR" DOCGEN_XRAY_SEARCH_DIR="$XRAY_DIR" \
  bash "$SCRIPT" "$DOMAIN" > "$OUT_MULTI"
assert_contains "[RECOMMEND] topology=xray-nginx-multi-upstream" "$OUT_MULTI"
assert_contains "[RECOMMEND] patch_count=3" "$OUT_MULTI"
assert_contains "[RECOMMEND] keep_unchanged=xray,cloudflare,dns" "$OUT_MULTI"
assert_contains "[RECOMMEND] patch_target=$NGINX_DIR/doc.conf|http://127.0.0.1:3000|http://127.0.0.1:8501" "$OUT_MULTI"
assert_contains "[RECOMMEND] patch_target=$NGINX_DIR/alone.conf|http://127.0.0.1:3000|http://127.0.0.1:8501" "$OUT_MULTI"
assert_contains "[RECOMMEND] multi_upstream_dry_run=bash ./cutover_public_homepage_upstream_targets.sh ${DOMAIN} $NGINX_DIR/alone.conf $NGINX_DIR/doc.conf" "$OUT_MULTI"
assert_contains "[XRAY] path=$XRAY_DIR/07_VLESS_vision_reality_inbounds.json" "$OUT_MULTI"

rm -rf "$NGINX_DIR" "$XRAY_DIR"
mkdir -p "$NGINX_DIR" "$XRAY_DIR"

cat > "$NGINX_DIR/doc.conf" <<EOF
server {
    listen 443 ssl;
    server_name ${DOMAIN};
    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
EOF

echo "[STEP] inspect single nginx origin topology"
DOCGEN_OS_NAME=Linux DOCGEN_NGINX_SEARCH_DIRS="$NGINX_DIR" DOCGEN_XRAY_SEARCH_DIR="$XRAY_DIR" \
  bash "$SCRIPT" "$DOMAIN" > "$OUT_SINGLE"
assert_contains "[RECOMMEND] topology=single-nginx-origin" "$OUT_SINGLE"
assert_contains "[RECOMMEND] patch_count=1" "$OUT_SINGLE"

echo "[PASS] inspect_public_homepage_live_topology regression checks passed"
