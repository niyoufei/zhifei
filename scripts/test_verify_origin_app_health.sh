#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_origin_app_health.sh"
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

write_code=""
url=""
for ((i=1; i<=$#; i++)); do
  arg="${!i}"
  if [[ "$arg" == "-w" ]]; then
    next=$(( i + 1 ))
    write_code="${!next}"
  elif [[ "$arg" != -* ]]; then
    url="$arg"
  fi
done

http_code="200"
body=""
case "$url" in
  http://127.0.0.1:8010/health)
    body='{"ok":true}'
    ;;
  http://127.0.0.1:8501/_stcore/health)
    body='ok'
    ;;
  http://127.0.0.1:8501/bad/_stcore/health)
    body='down'
    http_code='503'
    ;;
esac

if [[ -n "$write_code" ]]; then
  printf '%s' "$http_code"
  exit 0
fi

printf '%s' "$body"
EOF

cat > "$TMP_DIR/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" = "is-active" ]]; then
  printf '%s\n' "${MOCK_SYSTEMCTL_STATE:-active}"
  exit 0
fi
exit 1
EOF

chmod +x "$TMP_DIR/curl" "$TMP_DIR/systemctl"

run_case() {
  local case_name="$1"
  local expected_rc="$2"
  shift 2
  local output="$TMP_DIR/${case_name}.out"
  : > "$MOCK_LOG"
  set +e
  PATH="$TMP_DIR:$PATH" MOCK_CURL_LOG="$MOCK_LOG" "$@" >"$output" 2>&1
  local rc=$?
  set -e
  if [[ "$rc" -ne "$expected_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expected_rc}, actual rc=${rc}" >&2
    cat "$output" >&2
    exit 1
  fi
  LAST_OUTPUT_FILE="$output"
}

echo "[STEP] healthy origin runtime"
run_case healthy 0 bash "$VERIFY_SCRIPT"
assert_contains "backend_service_state=active" "$LAST_OUTPUT_FILE"
assert_contains "origin_backend_ok=yes" "$LAST_OUTPUT_FILE"
assert_contains "origin_streamlit_ok=yes" "$LAST_OUTPUT_FILE"
assert_contains "origin_app_state=healthy" "$LAST_OUTPUT_FILE"

echo "[STEP] degraded streamlit runtime"
run_case degraded 1 env DOCGEN_ORIGIN_STREAMLIT_HEALTH_URL="http://127.0.0.1:8501/bad/_stcore/health" bash "$VERIFY_SCRIPT"
assert_contains "streamlit_http_status=503" "$LAST_OUTPUT_FILE"
assert_contains "origin_streamlit_ok=no" "$LAST_OUTPUT_FILE"
assert_contains "origin_app_state=degraded" "$LAST_OUTPUT_FILE"

echo "[PASS] verify_origin_app_health regression checks passed"
