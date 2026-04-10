#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
FIX_DIR="$TMP_DIR/fix"
BIN_DIR="$TMP_DIR/bin"

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

mkdir -p "$FIX_DIR" "$BIN_DIR" "$TMP_DIR/nginx" "$TMP_DIR/caddy"
cp "$ROOT/scripts/suggest_linux_origin_fix.sh" "$FIX_DIR/suggest_linux_origin_fix.sh"
cp "$ROOT/scripts/detect_linux_proxy_stack.sh" "$FIX_DIR/detect_linux_proxy_stack.sh"
cp "$ROOT/scripts/generate_origin_tls_csr.sh" "$FIX_DIR/generate_origin_tls_csr.sh"
chmod 0644 \
  "$FIX_DIR/suggest_linux_origin_fix.sh" \
  "$FIX_DIR/detect_linux_proxy_stack.sh" \
  "$FIX_DIR/generate_origin_tls_csr.sh"

cat > "$BIN_DIR/uname" <<'EOF'
#!/usr/bin/env bash
printf 'Linux\n'
EOF

cat > "$BIN_DIR/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "is-active" && "${2:-}" == "nginx" ]]; then
  printf 'active\n'
elif [[ "$1" == "is-active" && "${2:-}" == "caddy" ]]; then
  printf 'inactive\n'
else
  printf 'inactive\n'
fi
EOF

cat > "$BIN_DIR/nginx" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "$BIN_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
url="${!#}"
case "$url" in
  http://127.0.0.1)
    printf 'HTTP/1.1 200 OK\r\nServer: nginx\r\n'
    ;;
  https://127.0.0.1)
    printf 'HTTP/1.1 200 OK\r\nServer: nginx\r\n'
    ;;
  *)
    printf 'HTTP/1.1 000 FAIL\r\n'
    ;;
esac
EOF

cat > "$BIN_DIR/openssl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exit 1
EOF

chmod +x "$BIN_DIR/uname" "$BIN_DIR/systemctl" "$BIN_DIR/nginx" "$BIN_DIR/curl" "$BIN_DIR/openssl"

cat > "$TMP_DIR/nginx/docgen-streamlit-origin.conf" <<'EOF'
server {
  listen 443 ssl;
  server_name doc.niyoufei.com;
}
EOF

cat > "$TMP_DIR/caddy/Caddyfile" <<'EOF'
import conf.d/*
EOF

echo "[STEP] helper files without exec bit should still be discovered"
PATH="$BIN_DIR:$PATH" \
NGINX_CONF_PATH="$TMP_DIR/nginx/docgen-streamlit-origin.conf" \
CADDY_CONFIG_PATH="$TMP_DIR/caddy/Caddyfile" \
bash "$FIX_DIR/suggest_linux_origin_fix.sh" doc.niyoufei.com > "$TMP_DIR/out"

assert_contains "[INFO] proxy_stack=nginx" "$TMP_DIR/out"
assert_contains "[RECOMMEND] 使用 nginx 发布链。" "$TMP_DIR/out"
assert_contains "bash ./generate_origin_tls_csr.sh doc.niyoufei.com" "$TMP_DIR/out"

echo "[PASS] suggest_linux_origin_fix regression checks passed"
