#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_linux_domain_origin.sh"
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

cat > "$TMP_DIR/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${2:-}" == "docgen-autoplan.service" ]]; then
  printf '%s\n' "${MOCK_BACKEND_STATE:-active}"
elif [[ "${2:-}" == "docgen-streamlit.service" ]]; then
  printf '%s\n' "${MOCK_STREAMLIT_STATE:-inactive}"
else
  printf 'active\n'
fi
EOF

cat > "$TMP_DIR/nginx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "-t" ]]; then
  exit 0
fi
exit 0
EOF

cat > "$TMP_DIR/openssl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exit 0
EOF

cat > "$TMP_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

dump_headers=0
url=""
for ((i=1; i<=$#; i++)); do
  arg="${!i}"
  if [[ "$arg" == "-D" ]]; then
    dump_headers=1
  elif [[ "$arg" != -* ]]; then
    url="$arg"
  fi
done

if [[ "${MOCK_CURL_MODE:-ok}" == "host_fail" && "$url" == http://doc.niyoufei.com* ]]; then
  exit 1
fi

if [[ "$dump_headers" = "1" ]]; then
  printf 'HTTP/1.1 200 OK\r\n'
else
  printf 'ok'
fi
EOF

cat > "$TMP_DIR/tesseract" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--list-langs" ]]; then
  cat <<'LANGS'
List of available languages in "/usr/share/tesseract-ocr/5/tessdata/" (3):
chi_sim
eng
osd
LANGS
  exit 0
fi
exit 0
EOF

mkdir -p "$TMP_DIR/app/.venv/bin"
cat > "$TMP_DIR/app/.venv/bin/python" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cat <<'PYOUT'
available=True
lang=chi_sim+eng
PYOUT
EOF

chmod +x \
  "$TMP_DIR/systemctl" \
  "$TMP_DIR/nginx" \
  "$TMP_DIR/openssl" \
  "$TMP_DIR/curl" \
  "$TMP_DIR/tesseract" \
  "$TMP_DIR/app/.venv/bin/python"

CERT_PATH="$TMP_DIR/server.crt"
printf 'dummy' > "$CERT_PATH"

NGINX_CONF="$TMP_DIR/docgen.conf"
cat > "$NGINX_CONF" <<EOF
server {
  listen 443 ssl;
  server_name doc.niyoufei.com;
  ssl_certificate $CERT_PATH;
}
EOF

run_case() {
  local case_name="$1"
  local expect_rc="$2"
  shift 2
  local output="$TMP_DIR/${case_name}.out"

  set +e
  PATH="$TMP_DIR:$PATH" \
  DOCGEN_OS_NAME="Linux" \
  DOCGEN_PROXY_STACK="nginx" \
  NGINX_CONF_PATH="$NGINX_CONF" \
  DOCGEN_APP_DIR="$TMP_DIR/app" \
  DOCGEN_VENV_PYTHON="$TMP_DIR/app/.venv/bin/python" \
  MOCK_BACKEND_STATE="active" \
  MOCK_STREAMLIT_STATE="inactive" \
  bash "$VERIFY_SCRIPT" doc.niyoufei.com >"$output" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -ne "$expect_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expect_rc}, actual rc=${rc}" >&2
    cat "$output" >&2
    exit 1
  fi

  LAST_OUTPUT_FILE="$output"
}

echo "[STEP] optional ocr should not block"
run_case optional_ocr 0
assert_contains "[SUMMARY] all checks passed." "$LAST_OUTPUT_FILE"
assert_contains "[INFO] ocr binary: optional (" "$LAST_OUTPUT_FILE"

echo "[STEP] enforced ocr should pass with chinese langpack"
set +e
PATH="$TMP_DIR:$PATH" \
DOCGEN_OS_NAME="Linux" \
DOCGEN_PROXY_STACK="nginx" \
NGINX_CONF_PATH="$NGINX_CONF" \
DOCGEN_APP_DIR="$TMP_DIR/app" \
DOCGEN_VENV_PYTHON="$TMP_DIR/app/.venv/bin/python" \
DOCGEN_EXPECT_OCR="1" \
DOCGEN_EXPECT_OCR_CHINESE="1" \
MOCK_BACKEND_STATE="active" \
MOCK_STREAMLIT_STATE="inactive" \
bash "$VERIFY_SCRIPT" doc.niyoufei.com >"$TMP_DIR/enforced.out" 2>&1
rc=$?
set -e

if [[ "$rc" -ne 0 ]]; then
  echo "[FAIL] enforced ocr case failed" >&2
  cat "$TMP_DIR/enforced.out" >&2
  exit 1
fi

assert_contains "[OK] ocr binary:" "$TMP_DIR/enforced.out"
assert_contains "[OK] ocr runtime: available=True lang=chi_sim+eng" "$TMP_DIR/enforced.out"
assert_contains "[OK] ocr chinese langpack:" "$TMP_DIR/enforced.out"
assert_contains "[SUMMARY] all checks passed." "$TMP_DIR/enforced.out"

echo "[STEP] skip proxy host checks should tolerate no local 80/443 listener"
set +e
PATH="$TMP_DIR:$PATH" \
DOCGEN_OS_NAME="Linux" \
DOCGEN_PROXY_STACK="nginx" \
NGINX_CONF_PATH="$NGINX_CONF" \
DOCGEN_APP_DIR="$TMP_DIR/app" \
DOCGEN_VENV_PYTHON="$TMP_DIR/app/.venv/bin/python" \
DOCGEN_EXPECT_OCR="1" \
DOCGEN_SKIP_PROXY_HOST_CHECK="1" \
MOCK_BACKEND_STATE="active" \
MOCK_STREAMLIT_STATE="inactive" \
MOCK_CURL_MODE="host_fail" \
bash "$VERIFY_SCRIPT" doc.niyoufei.com >"$TMP_DIR/skip-proxy.out" 2>&1
rc=$?
set -e

if [[ "$rc" -ne 0 ]]; then
  echo "[FAIL] skip proxy host case failed" >&2
  cat "$TMP_DIR/skip-proxy.out" >&2
  exit 1
fi

assert_contains "[INFO] proxy host header checks: skipped" "$TMP_DIR/skip-proxy.out"
assert_contains "[OK] ocr runtime: available=True lang=chi_sim+eng" "$TMP_DIR/skip-proxy.out"
assert_contains "[SUMMARY] all checks passed." "$TMP_DIR/skip-proxy.out"

echo "[PASS] verify_linux_domain_origin regression checks passed"
