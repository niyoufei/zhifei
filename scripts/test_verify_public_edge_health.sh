#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_public_edge_health.sh"
TMP_DIR="$(mktemp -d)"
MOCK_LOG="$TMP_DIR/curl.log"
MOCK_STATE_DIR="$TMP_DIR/state"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$MOCK_STATE_DIR"

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
state_key="$(printf '%s' "$url" | tr '/:?' '___')"
state_file="$MOCK_STATE_DIR/$state_key.count"
count=0
if [[ -f "$state_file" ]]; then
  count="$(cat "$state_file")"
fi
count=$((count + 1))
printf '%s' "$count" > "$state_file"

case "$url" in
  https://doc.niyoufei.com)
    body='<html><head><title>文档生成系统</title></head><body>DocGen</body></html>'
    ;;
  https://doc.niyoufei.com/_stcore/health)
    body='ok'
    ;;
  https://doc.niyoufei.com/flaky)
    if [[ "$count" -eq 1 ]]; then
      body='<html><head><title>Bad Gateway</title></head><body>edge error</body></html>'
      http_code='502'
    else
      body='<html><head><title>文档生成系统</title></head><body>DocGen</body></html>'
    fi
    ;;
  https://doc.niyoufei.com/flaky/_stcore/health)
    if [[ "$count" -eq 1 ]]; then
      body='timeout'
      http_code='504'
    else
      body='ok'
    fi
    ;;
  https://doc.niyoufei.com/bad)
    body='<html><head><title>Bad Gateway</title></head><body>error</body></html>'
    http_code='502'
    ;;
  https://doc.niyoufei.com/bad/_stcore/health)
    body='timeout'
    http_code='504'
    ;;
esac

if [[ -n "$write_code" ]]; then
  printf '%s' "$http_code"
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
  local args=()
  local env_args=()
  local arg
  for arg in "$@"; do
    if [[ "$arg" == *=* ]]; then
      env_args+=("$arg")
    else
      args+=("$arg")
    fi
  done
  : > "$MOCK_LOG"
  rm -f "$MOCK_STATE_DIR"/*.count 2>/dev/null || true
  set +e
  if [[ "${#env_args[@]}" -gt 0 ]]; then
    PATH="$TMP_DIR:$PATH" MOCK_CURL_LOG="$MOCK_LOG" MOCK_STATE_DIR="$MOCK_STATE_DIR" \
      env "${env_args[@]}" bash "$VERIFY_SCRIPT" "${args[@]}" >"$output" 2>&1
  else
    PATH="$TMP_DIR:$PATH" MOCK_CURL_LOG="$MOCK_LOG" MOCK_STATE_DIR="$MOCK_STATE_DIR" \
      bash "$VERIFY_SCRIPT" "${args[@]}" >"$output" 2>&1
  fi
  local rc=$?
  set -e
  if [[ "$rc" -ne "$expected_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expected_rc}, actual rc=${rc}" >&2
    cat "$output" >&2
    exit 1
  fi
  LAST_OUTPUT_FILE="$output"
}

echo "[STEP] healthy public edge"
run_case healthy 0 "https://doc.niyoufei.com"
assert_contains "home_status=200" "$LAST_OUTPUT_FILE"
assert_contains "title=文档生成系统" "$LAST_OUTPUT_FILE"
assert_contains "edge_profile=default" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_ok=yes" "$LAST_OUTPUT_FILE"
assert_contains "public_edge_state=healthy" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_drop_at=none" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_drop_at=none" "$LAST_OUTPUT_FILE"

echo "[STEP] stable profile should use 3/2 defaults"
run_case stable_profile 0 "https://doc.niyoufei.com/flaky" \
  ZF_EDGE_PROFILE=stable \
  ZF_EDGE_OBSERVE_INTERVAL_SECONDS=0
assert_contains "edge_profile=stable" "$LAST_OUTPUT_FILE"
assert_contains "observe_cycles=3" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_fail_streak_threshold=2" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_fail_streak_threshold=2" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_fail_streak_max=1" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_fail_streak_max=1" "$LAST_OUTPUT_FILE"
assert_contains "public_edge_state=healthy" "$LAST_OUTPUT_FILE"

echo "[STEP] transient edge failure should pass with streak threshold"
run_case transient_threshold 0 "https://doc.niyoufei.com/flaky" \
  ZF_EDGE_OBSERVE_CYCLES=2 \
  ZF_EDGE_OBSERVE_INTERVAL_SECONDS=0 \
  ZF_EDGE_HOME_FAIL_STREAK_THRESHOLD=2 \
  ZF_EDGE_STREAMLIT_FAIL_STREAK_THRESHOLD=2
assert_contains "observe_cycles=2" "$LAST_OUTPUT_FILE"
assert_contains "observe_interval_seconds=0" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_fail_streak_threshold=2" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_fail_streak_threshold=2" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_fail_streak_max=1" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_fail_streak_max=1" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_drop_at=none" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_drop_at=none" "$LAST_OUTPUT_FILE"
assert_contains "public_edge_state=healthy" "$LAST_OUTPUT_FILE"

echo "[STEP] explicit override should beat stable profile"
run_case stable_override 1 "https://doc.niyoufei.com/flaky" \
  ZF_EDGE_PROFILE=stable \
  ZF_EDGE_OBSERVE_INTERVAL_SECONDS=0 \
  ZF_EDGE_HOME_FAIL_STREAK_THRESHOLD=1 \
  ZF_EDGE_STREAMLIT_FAIL_STREAK_THRESHOLD=1
assert_contains "edge_profile=stable" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_fail_streak_threshold=1" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_fail_streak_threshold=1" "$LAST_OUTPUT_FILE"
assert_contains "edge_home_drop_at=1" "$LAST_OUTPUT_FILE"
assert_contains "edge_streamlit_drop_at=1" "$LAST_OUTPUT_FILE"
assert_contains "public_edge_state=degraded" "$LAST_OUTPUT_FILE"

echo "[STEP] degraded public edge"
run_case degraded 1 "https://doc.niyoufei.com/bad"
assert_contains "home_status=502" "$LAST_OUTPUT_FILE"
assert_contains "stcore_http_status=504" "$LAST_OUTPUT_FILE"
assert_contains "public_edge_state=degraded" "$LAST_OUTPUT_FILE"

echo "[PASS] verify_public_edge_health regression checks passed"
