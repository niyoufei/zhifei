#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OBSERVE_SCRIPT="$ROOT/scripts/observe_web_stability.sh"
TMP_DIR="$(mktemp -d)"

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

cat > "$TMP_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR="${TMP_OBSERVE_STATE_DIR:?}"
url=""
head_mode=0
for arg in "$@"; do
  if [[ "$arg" == "-I" ]]; then
    head_mode=1
  fi
  if [[ "$arg" != -* ]]; then
    url="$arg"
  fi
done

case "$url" in
  *backend*)
    key="backend"
    fail_calls="${MOCK_BACKEND_FAIL_CALLS:-}"
    ;;
  *web-health*)
    key="web_health"
    fail_calls="${MOCK_WEB_HEALTH_FAIL_CALLS:-}"
    ;;
  *web-home*)
    key="home"
    fail_calls="${MOCK_HOME_FAIL_CALLS:-}"
    ;;
  *)
    key="other"
    fail_calls=""
    ;;
esac

counter_file="$STATE_DIR/${key}.count"
count=0
if [[ -f "$counter_file" ]]; then
  count="$(cat "$counter_file")"
fi
count=$(( count + 1 ))
printf '%s' "$count" > "$counter_file"

if [[ -n "$fail_calls" ]]; then
  IFS=',' read -r -a items <<< "$fail_calls"
  for item in "${items[@]}"; do
    if [[ "$count" = "$item" ]]; then
      exit 1
    fi
  done
fi

if [[ "$key" = "web_health" ]]; then
  printf 'ok'
elif [[ "$head_mode" = "1" ]]; then
  printf 'HTTP/1.1 200 OK\r\n'
else
  printf 'ok'
fi
EOF

cat > "$TMP_DIR/lsof" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "${MOCK_LISTENER_PID:-38172}"
EOF

cat > "$TMP_DIR/sleep" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
:
EOF

chmod +x "$TMP_DIR/curl" "$TMP_DIR/lsof" "$TMP_DIR/sleep"

CHIEF_LOG="$TMP_DIR/chief.log"
PID_FILE="$TMP_DIR/streamlit.pid"
printf '38172' > "$PID_FILE"
: > "$CHIEF_LOG"

run_case() {
  local case_name="$1"
  local backend_fails="$2"
  local web_fails="$3"
  local home_fails="$4"
  local expected_rc="$5"
  shift 5
  local log="$TMP_DIR/${case_name}.log"
  local state_dir="$TMP_DIR/${case_name}-state"
  mkdir -p "$state_dir"

  set +e
  PATH="$TMP_DIR:$PATH" \
  TMP_OBSERVE_STATE_DIR="$state_dir" \
  MOCK_BACKEND_FAIL_CALLS="$backend_fails" \
  MOCK_WEB_HEALTH_FAIL_CALLS="$web_fails" \
  MOCK_HOME_FAIL_CALLS="$home_fails" \
  ZF_OBSERVE_BACKEND_URL="mock://backend" \
  ZF_OBSERVE_WEB_HEALTH_URL="mock://web-health" \
  ZF_OBSERVE_WEB_HOME_URL="mock://web-home" \
  ZF_OBSERVE_CHIEF_LOG="$CHIEF_LOG" \
  ZF_OBSERVE_WEB_PID_FILE="$PID_FILE" \
  bash "$OBSERVE_SCRIPT" 3 > "$log" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -ne "$expected_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expected_rc}, actual rc=${rc}" >&2
    cat "$log" >&2
    exit 1
  fi

  for needle in "$@"; do
    assert_contains "$needle" "$log"
  done
}

echo "[STEP] stable pass"
run_case stable "" "" "" 0 \
  "backend_fail_streak_threshold=2" \
  "web_health_fail_streak_threshold=2" \
  "home_fail_streak_threshold=2" \
  "backend_drop_at=none" \
  "web_health_drop_at=none" \
  "home_drop_at=none"

echo "[STEP] single backend miss should not fail"
run_case single_backend_miss "1" "" "" 0 \
  "backend_drop_at=none" \
  "web_health_drop_at=none" \
  "home_drop_at=none"

echo "[STEP] consecutive backend miss should fail"
run_case consecutive_backend_miss "1,2" "" "" 1 \
  "backend_drop_at=0"

echo "[STEP] consecutive home miss should fail"
run_case consecutive_home_miss "" "" "1,2" 1 \
  "home_drop_at=0"

echo "[PASS] observe_web_stability regression checks passed"
