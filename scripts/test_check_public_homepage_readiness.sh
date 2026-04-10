#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
READINESS_SCRIPT="$ROOT/scripts/check_public_homepage_readiness.sh"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

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

cat > "$TMP_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

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
    mode="${MOCK_BACKEND_MODE:-ok}"
    ;;
  *web-health*)
    mode="${MOCK_WEB_HEALTH_MODE:-ok}"
    ;;
  *web-home*)
    mode="${MOCK_HOME_MODE:-ok}"
    ;;
  *)
    mode="ok"
    ;;
esac

if [[ "$mode" != "ok" ]]; then
  exit 1
fi

if [[ "$url" == *web-health* ]]; then
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

chmod +x "$TMP_DIR/curl" "$TMP_DIR/lsof"

run_case() {
  local case_name="$1"
  local observe_rc="$2"
  local observe_log="$3"
  local smoke_rc="$4"
  local smoke_log="$5"
  local include_smoke="$6"
  local expect_rc="$7"
  shift 7

  local observe_stub="$TMP_DIR/${case_name}-observe.sh"
  local smoke_stub="$TMP_DIR/${case_name}-smoke.py"
  local keys_file="$TMP_DIR/${case_name}.env"
  local pid_file="$TMP_DIR/${case_name}.pid"
  local output="$TMP_DIR/${case_name}.out"

  printf '38172' > "$pid_file"
  printf 'DUMMY=1\n' > "$keys_file"

  cat > "$observe_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${observe_log}
LOG
exit ${observe_rc}
EOF

  cat > "$smoke_stub" <<EOF
#!/usr/bin/env python3
import sys
sys.stdout.write("""${smoke_log}""")
sys.exit(${smoke_rc})
EOF

  chmod +x "$observe_stub" "$smoke_stub"

  set +e
  PATH="$TMP_DIR:$PATH" \
  ZF_STATUS_BACKEND_HEALTH_URL="mock://backend" \
  ZF_STATUS_WEB_HEALTH_URL="mock://web-health" \
  ZF_STATUS_WEB_HOME_URL="mock://web-home" \
  ZF_WEB_PID_FILE="$pid_file" \
  ZF_STATUS_OBSERVE_SCRIPT="$observe_stub" \
  ZF_STATUS_SMOKE_SCRIPT="$smoke_stub" \
  ZF_INCLUDE_SMOKE="$include_smoke" \
  ZF_KEYS_FILE="$keys_file" \
  MOCK_BACKEND_MODE="ok" \
  MOCK_WEB_HEALTH_MODE="ok" \
  MOCK_HOME_MODE="ok" \
  bash "$READINESS_SCRIPT" 3 > "$output" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -ne "$expect_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expect_rc}, actual rc=${rc}" >&2
    cat "$output" >&2
    exit 1
  fi

  for needle in "$@"; do
    assert_contains "$needle" "$output"
  done
}

echo "[STEP] green path without smoke"
run_case ready_no_smoke 0 $'backend_drop_at=none\nweb_health_drop_at=none\nhome_drop_at=none' 0 "" 0 0 \
  "backend_health=ok" \
  "web_health=ok" \
  "web_home=ok" \
  "web_pid_aligned=yes" \
  "observe_result=pass" \
  "smoke_result=skipped" \
  "public_cutover_ready=yes"

echo "[STEP] observe fail should block"
run_case observe_fail 1 $'backend_drop_at=10\nweb_health_drop_at=none\nhome_drop_at=none' 0 "" 0 1 \
  "observe_result=fail" \
  "public_cutover_ready=no"

echo "[STEP] smoke fail should block"
run_case smoke_fail 0 $'backend_drop_at=none\nweb_health_drop_at=none\nhome_drop_at=none' 1 "[FAIL] smoke" 1 1 \
  "observe_result=pass" \
  "smoke_result=fail" \
  "public_cutover_ready=no"

echo "[PASS] check_public_homepage_readiness regression checks passed"
