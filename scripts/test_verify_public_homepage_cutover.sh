#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_public_homepage_cutover.sh"
TMP_DIR="$(mktemp -d)"
MOCK_LOG="$TMP_DIR/curl.log"

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

cat > "$TMP_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >> "$MOCK_CURL_LOG"

head_mode=0
write_code=""
url=""
for ((i=1; i<=$#; i++)); do
  arg="${!i}"
  if [[ "$arg" == "-I" ]]; then
    head_mode=1
  elif [[ "$arg" == "-w" ]]; then
    next=$(( i + 1 ))
    write_code="${!next}"
  elif [[ "$arg" != -* ]]; then
    url="$arg"
  fi
done

http_code="200"
body=""
if [[ "$url" == "https://doc.niyoufei.com/head-fallback" && "$head_mode" = "1" ]]; then
  exit 28
fi
case "$url" in
  http://127.0.0.1:8501/_stcore/health)
    body="ok"
    ;;
  http://127.0.0.1:8501)
    body='<html><head><title>文档生成系统</title></head><body>DocGen</body></html>'
    ;;
  https://doc.niyoufei.com/_stcore/health)
    body='<!doctype html><title>Open WebUI</title>'
    ;;
  https://doc.niyoufei.com)
    body='<html><head><title>Open WebUI</title></head><body>Open WebUI</body></html>'
    ;;
  https://doc.niyoufei.com/switch)
    body='<html><head><title>文档生成系统</title></head><body>DocGen</body></html>'
    ;;
  https://doc.niyoufei.com/switch/_stcore/health)
    body='ok'
    ;;
  https://doc.niyoufei.com/head-fallback)
    body='<html><head><title>文档生成系统</title></head><body>DocGen</body></html>'
    ;;
  https://doc.niyoufei.com/head-fallback/_stcore/health)
    body='ok'
    ;;
  *)
    body=""
    ;;
esac

if [[ -n "$write_code" ]]; then
  printf '%s' "$http_code"
  exit 0
fi

if [[ "$head_mode" = "1" ]]; then
  printf 'HTTP/1.1 %s OK\r\n' "$http_code"
  exit 0
fi

printf '%s' "$body"
EOF

chmod +x "$TMP_DIR/curl"

run_case() {
  local case_name="$1"
  local expected_rc="$2"
  shift 2
  local output="$TMP_DIR/${case_name}.out"
  : > "$MOCK_LOG"
  set +e
  PATH="$TMP_DIR:$PATH" MOCK_CURL_LOG="$MOCK_LOG" bash "$VERIFY_SCRIPT" "$@" >"$output" 2>&1
  local rc=$?
  set -e
  if [[ "$rc" -ne "$expected_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expected_rc}, actual rc=${rc}" >&2
    cat "$output" >&2
    exit 1
  fi
  LAST_OUTPUT_FILE="$output"
}

echo "[STEP] local docgen verify"
run_case local_docgen 0 "http://127.0.0.1:8501"
assert_contains "home_status=200" "$LAST_OUTPUT_FILE"
assert_contains "stcore_body=ok" "$LAST_OUTPUT_FILE"
assert_contains "open_webui_present=no" "$LAST_OUTPUT_FILE"
assert_contains "title=文档生成系统" "$LAST_OUTPUT_FILE"
assert_contains "cutover_verified=yes" "$LAST_OUTPUT_FILE"

echo "[STEP] public open-webui verify"
run_case public_open_webui 1 "https://doc.niyoufei.com"
assert_contains "open_webui_present=yes" "$LAST_OUTPUT_FILE"
assert_contains "title=Open WebUI" "$LAST_OUTPUT_FILE"
assert_contains "cutover_verified=no" "$LAST_OUTPUT_FILE"

echo "[STEP] https resolve verify"
run_case https_resolve 0 "https://doc.niyoufei.com/switch" "199.180.118.204"
assert_contains "resolve_ip=199.180.118.204" "$LAST_OUTPUT_FILE"
assert_contains "title=文档生成系统" "$LAST_OUTPUT_FILE"
assert_contains "cutover_verified=yes" "$LAST_OUTPUT_FILE"
assert_contains "--resolve doc.niyoufei.com:443:199.180.118.204" "$MOCK_LOG"

echo "[STEP] head fallback verify"
run_case head_fallback 0 "https://doc.niyoufei.com/head-fallback"
assert_contains "home_status=200" "$LAST_OUTPUT_FILE"
assert_contains "title=文档生成系统" "$LAST_OUTPUT_FILE"
assert_contains "cutover_verified=yes" "$LAST_OUTPUT_FILE"

echo "[PASS] verify_public_homepage_cutover regression checks passed"
