#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_ui_upload_outline_chain.sh"
TMP_DIR="$(mktemp -d)"
FIXTURE_DIR="$TMP_DIR/fixtures"
CALLS="$TMP_DIR/python.calls"

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
if [[ "${1:-}" = "-" ]]; then
  cat >/dev/null
  printf 'probe\n' >>"$CALLS_FILE"
  exit 0
fi

SCRIPT_FILE="${1:?missing script file}"
printf '%s\n' "$SCRIPT_FILE" >>"$CALLS_FILE"

if ! grep -Fq -- "from playwright.sync_api import sync_playwright" "$SCRIPT_FILE"; then
  echo "[FAIL] missing python playwright import" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
fi
if ! grep -Fq -- "set_input_files" "$SCRIPT_FILE"; then
  echo "[FAIL] missing python upload step" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
fi
if ! grep -Fq -- "UI_STREAMLIT_UPLOAD" "$SCRIPT_FILE"; then
  echo "[FAIL] missing python streamlit upload emit" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
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
DOCGEN_UI_FIXTURE_DIR="$FIXTURE_DIR" \
DOCGEN_UI_BASE_URL="http://127.0.0.1:18501" \
DOCGEN_UI_BROWSER_IMPL="python" \
bash "$VERIFY_SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[INFO] browser_impl=python" "$OUTPUT"
assert_contains "[OK] page ready: http://127.0.0.1:18501" "$OUTPUT"
assert_contains "[OK] selected files: 招标/答疑 1 · 清单 1" "$OUTPUT"
assert_contains "[OK] outline loaded: outline entries rendered" "$OUTPUT"
assert_contains "[OK] streamlit upload request: PUT /_stcore/upload_file => 204 x2" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
assert_contains "probe" "$CALLS"
assert_contains "ui_upload_outline_smoke.py" "$CALLS"

echo "[PASS] verify_ui_upload_outline_chain python regression checks passed"
