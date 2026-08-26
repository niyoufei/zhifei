#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_ui_upload_outline_chain.sh"
TMP_DIR="$(mktemp -d)"
FIXTURE_DIR="$TMP_DIR/fixtures"
CALLS="$TMP_DIR/python.calls"
STATE_FILE="$TMP_DIR/state.txt"

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

mkdir -p "$FIXTURE_DIR"
printf 'docx' > "$FIXTURE_DIR/tender.docx"
printf 'xlsx' > "$FIXTURE_DIR/boq.xlsx"

cat > "$TMP_DIR/mock-python" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

CALLS_FILE="${DOCGEN_TEST_PYTHON_CALLS:?}"
STATE_FILE="${DOCGEN_TEST_PYTHON_STATE:?}"
if [[ "${1:-}" = "-" ]]; then
  cat >/dev/null
  printf 'probe\n' >>"$CALLS_FILE"
  exit 0
fi

SCRIPT_FILE="${1:?missing script file}"
printf '%s\n' "$SCRIPT_FILE" >>"$CALLS_FILE"

attempt=0
if [[ -f "$STATE_FILE" ]]; then
  attempt="$(cat "$STATE_FILE")"
fi
attempt=$((attempt + 1))
printf '%s' "$attempt" >"$STATE_FILE"

if [[ "$attempt" -eq 1 ]]; then
  cat <<'TEXT'
UI_PAGE_READY=1
UI_SELECTED_FILES=0
UI_OUTLINE_LOADED=0
UI_STREAMLIT_UPLOAD=0
UI_UPLOAD_204_MATCHES=0
UI_ERROR=Page.wait_for_function: Timeout 60000ms exceeded.
TEXT
  exit 0
fi

cat <<'TEXT'
UI_PAGE_READY=1
UI_SELECTED_FILES=1
UI_OUTLINE_LOADED=1
UI_STREAMLIT_UPLOAD=1
UI_UPLOAD_204_MATCHES=2
UI_ERROR=none
TEXT
EOF
chmod +x "$TMP_DIR/mock-python"

OUTPUT="$TMP_DIR/verify.out"

DOCGEN_UI_PYTHON="$TMP_DIR/mock-python" \
DOCGEN_TEST_PYTHON_CALLS="$CALLS" \
DOCGEN_TEST_PYTHON_STATE="$STATE_FILE" \
DOCGEN_UI_FIXTURE_DIR="$FIXTURE_DIR" \
DOCGEN_UI_BASE_URL="http://127.0.0.1:18501" \
DOCGEN_UI_BROWSER_IMPL="python" \
DOCGEN_UI_RUN_ATTEMPTS="2" \
DOCGEN_UI_RETRY_SLEEP_SECONDS="0" \
bash "$VERIFY_SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[WARN] browser smoke attempt 1 failed with transient browser shutdown, retrying after cleanup..." "$OUTPUT"
assert_contains "[INFO] browser_attempts=2/2" "$OUTPUT"
assert_contains "[OK] page ready: http://127.0.0.1:18501" "$OUTPUT"
assert_contains "[OK] selected files: 招标/答疑 1 · 清单 1" "$OUTPUT"
assert_contains "[OK] outline loaded: outline entries rendered" "$OUTPUT"
assert_contains "[OK] streamlit upload request: PUT /_stcore/upload_file => 204 x2" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
runner_calls="$(grep -c 'ui_upload_outline_smoke.py' "$CALLS" || true)"
if [[ "$runner_calls" != "2" ]]; then
  echo "[FAIL] expected 2 runner invocations, got $runner_calls" >&2
  cat "$CALLS" >&2
  exit 1
fi

echo "[PASS] verify_ui_upload_outline_chain timeout retry regression checks passed"
