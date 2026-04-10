#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/install_linux_domain_origin.sh"
TMP_DIR="$(mktemp -d)"

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

assert_not_exists() {
  local path="$1"
  if [[ -e "$path" ]]; then
    echo "[FAIL] unexpected path exists: $path" >&2
    exit 1
  fi
}

BIN_DIR="$TMP_DIR/bin"
mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/uname" <<'EOF'
#!/usr/bin/env bash
printf 'Linux\n'
EOF

cat > "$BIN_DIR/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'systemctl %s\n' "$*" >> "$MOCK_INSTALL_LOG"
exit 0
EOF

cat > "$BIN_DIR/nginx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'nginx %s\n' "$*" >> "$MOCK_INSTALL_LOG"
exit 0
EOF

cat > "$BIN_DIR/caddy" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'caddy %s\n' "$*" >> "$MOCK_INSTALL_LOG"
exit 0
EOF

chmod +x "$BIN_DIR/uname" "$BIN_DIR/systemctl" "$BIN_DIR/nginx" "$BIN_DIR/caddy"

run_case_nginx() {
  local case_dir="$TMP_DIR/nginx-case"
  local log="$case_dir/calls.log"
  mkdir -p "$case_dir/systemd" "$case_dir/nginx"

  : > "$log"
  PATH="$BIN_DIR:$PATH" \
  MOCK_INSTALL_LOG="$log" \
  SYSTEMD_DIR="$case_dir/systemd" \
  NGINX_DIR="$case_dir/nginx" \
  bash "$SCRIPT" doc.niyoufei.com > "$case_dir/out"

  assert_contains "proxy stack: nginx" "$case_dir/out"
  assert_contains "streamlit service: disabled (backend-managed)" "$case_dir/out"
  assert_contains "public url: https://doc.niyoufei.com" "$case_dir/out"
  assert_contains "systemctl daemon-reload" "$log"
  assert_contains "systemctl enable --now docgen-autoplan.service" "$log"
  assert_contains "systemctl disable --now docgen-streamlit.service" "$log"
  assert_contains "systemctl reload nginx" "$log"
  assert_contains "nginx -t" "$log"
  assert_contains "server_name doc.niyoufei.com;" "$case_dir/nginx/docgen-streamlit-origin.conf"
  assert_contains "proxy_pass http://127.0.0.1:8501;" "$case_dir/nginx/docgen-streamlit-origin.conf"
  [[ -f "$case_dir/systemd/docgen-autoplan.service" ]] || {
    echo "[FAIL] missing backend service copy" >&2
    exit 1
  }
  assert_not_exists "$case_dir/systemd/docgen-streamlit.service"
}

run_case_caddy() {
  local case_dir="$TMP_DIR/caddy-case"
  local log="$case_dir/calls.log"
  mkdir -p "$case_dir/systemd" "$case_dir/caddy-snippets"
  cat > "$case_dir/Caddyfile" <<'EOF'
import conf.d/*
EOF

  : > "$log"
  PATH="$BIN_DIR:$PATH" \
  MOCK_INSTALL_LOG="$log" \
  DOCGEN_PROXY_STACK="caddy" \
  DOCGEN_ENABLE_STREAMLIT_SERVICE="1" \
  SYSTEMD_DIR="$case_dir/systemd" \
  CADDY_SNIPPET_DIR="$case_dir/caddy-snippets" \
  CADDY_MAIN_CONFIG_PATH="$case_dir/Caddyfile" \
  bash "$SCRIPT" doc.niyoufei.com > "$case_dir/out"

  assert_contains "proxy stack: caddy" "$case_dir/out"
  assert_contains "streamlit service: docgen-streamlit.service" "$case_dir/out"
  assert_contains "caddy validate --config $case_dir/Caddyfile" "$log"
  assert_contains "systemctl enable --now docgen-autoplan.service" "$log"
  assert_contains "systemctl enable --now docgen-streamlit.service" "$log"
  assert_contains "systemctl reload caddy" "$log"
  [[ -f "$case_dir/systemd/docgen-streamlit.service" ]] || {
    echo "[FAIL] missing streamlit service copy" >&2
    exit 1
  }
  assert_contains "ZF_PUBLIC_WEB_URL=https://doc.niyoufei.com" "$case_dir/systemd/docgen-streamlit.service"
  assert_contains "reverse_proxy 127.0.0.1:8501" "$case_dir/caddy-snippets/docgen-streamlit.Caddyfile"
}

echo "[STEP] nginx install path"
run_case_nginx

echo "[STEP] caddy install path"
run_case_caddy

echo "[PASS] install_linux_domain_origin regression checks passed"
