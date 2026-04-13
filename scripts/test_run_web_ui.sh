#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/run_web_ui.sh"
TMP_DIR="$(mktemp -d)"
MOCK_DIR="$TMP_DIR/mock"
CONTROL_LOG="$TMP_DIR/webui_control.log"
OUTPUT_OK="$TMP_DIR/ok.log"
OUTPUT_UNHEALTHY="$TMP_DIR/unhealthy.log"
OUTPUT_FOREIGN="$TMP_DIR/foreign.log"

mkdir -p "$MOCK_DIR"

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

assert_not_contains() {
  local needle="$1"
  local file="$2"
  if grep -Fq -- "$needle" "$file"; then
    echo "[FAIL] unexpected text: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

cat > "$MOCK_DIR/lsof" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
args="$*"
pid=""
if [[ "$args" == *"8010"* ]]; then
  pid="${MOCK_BACKEND_PID:-41010}"
elif [[ "$args" == *"8501"* ]]; then
  pid="${MOCK_WEB_PID:-41050}"
else
  exit 1
fi
printf '%s\n' "$pid"
EOF

cat > "$MOCK_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
url="${*: -1}"
case "$url" in
  http://127.0.0.1:8010/health)
    printf '%s' '{"ok":true,"system_id":"docgen-system","service":"文档生成系统"}'
    ;;
  http://127.0.0.1:8010/capabilities)
    printf '%s' '{"provider_status":{"text_main":{"configured":true},"text_backup":{"configured":true},"automation":{"configured":true},"gemini_a":{"configured":true},"gemini_b":{"configured":true}}}'
    ;;
  http://127.0.0.1:8501/_stcore/health)
    if [[ "${MOCK_STREAMLIT_HEALTH:-1}" = "1" ]]; then
      printf 'ok'
    else
      exit 1
    fi
    ;;
  *)
    exit 1
    ;;
esac
EOF

cat > "$MOCK_DIR/ps" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
pid=""
prev=""
for arg in "$@"; do
  if [[ "$prev" = "-p" ]]; then
    pid="$arg"
    break
  fi
  prev="$arg"
done
if [[ "$pid" = "${MOCK_WEB_PID:-41050}" ]]; then
  printf '%s\n' "${MOCK_WEB_CMD:-python -m streamlit run ${DOCGEN_TEST_ROOT:?}/app.py --server.port 8501}"
  exit 0
fi
if [[ "$pid" = "${MOCK_BACKEND_PID:-41010}" ]]; then
  printf '%s\n' "python -m uvicorn backend.app.main:app --port 8010"
  exit 0
fi
exit 1
EOF

cat > "$MOCK_DIR/sleep" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
:
EOF

chmod +x "$MOCK_DIR/lsof" "$MOCK_DIR/curl" "$MOCK_DIR/ps" "$MOCK_DIR/sleep"

run_case() {
  local output_file="$1"
  shift
  PATH="$MOCK_DIR:$PATH" \
  DOCGEN_TEST_ROOT="$ROOT" \
  ZF_SKIP_OPEN=1 \
  ZF_ENABLE_SELF_HEAL=0 \
  ZF_WEB_UI_CONTROL_LOG="$CONTROL_LOG" \
  ZF_RUNTIME_DIR="$TMP_DIR/runtime" \
  "$@" \
  bash "$SCRIPT" >"$output_file" 2>&1
}

run_case "$OUTPUT_OK" env MOCK_STREAMLIT_HEALTH=1
assert_contains "文档生成系统已就绪，请访问 http://127.0.0.1:8501" "$OUTPUT_OK"
assert_contains "foreground_reused_web=true" "$CONTROL_LOG"

set +e
run_case "$OUTPUT_UNHEALTHY" env MOCK_STREAMLIT_HEALTH=0
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo "[FAIL] expected unhealthy reused listener case to fail" >&2
  cat "$OUTPUT_UNHEALTHY" >&2
  exit 1
fi
assert_contains "健康检查失败" "$OUTPUT_UNHEALTHY"
assert_not_contains "文档生成系统已就绪" "$OUTPUT_UNHEALTHY"
assert_contains "start failed web_reused_listener_unhealthy" "$CONTROL_LOG"

set +e
run_case "$OUTPUT_FOREIGN" env MOCK_STREAMLIT_HEALTH=1 MOCK_WEB_CMD="python -m http.server 8501"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  echo "[FAIL] expected foreign listener case to fail" >&2
  cat "$OUTPUT_FOREIGN" >&2
  exit 1
fi
assert_contains "已被其他应用占用" "$OUTPUT_FOREIGN"
assert_not_contains "文档生成系统已就绪" "$OUTPUT_FOREIGN"
assert_contains "start failed web_port_conflict" "$CONTROL_LOG"

echo "[PASS] run_web_ui foreground reuse checks passed"
