#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_ui_upload_outline_chain.sh"
TMP_DIR="$(mktemp -d)"
FIXTURE_DIR="$TMP_DIR/fixtures"
CALLS="$TMP_DIR/node.calls"

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
mkdir -p "$TMP_DIR/node_modules/playwright-core"
printf 'docx' > "$FIXTURE_DIR/tender.docx"
printf 'xlsx' > "$FIXTURE_DIR/boq.xlsx"

cat > "$TMP_DIR/mock-node" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

CALLS_FILE="${DOCGEN_TEST_NODE_CALLS:?}"
SCRIPT_FILE="${1:?missing script file}"
printf '%s\n' "$SCRIPT_FILE" >>"$CALLS_FILE"

if ! grep -Fq -- "require(process.env.DOCGEN_UI_PLAYWRIGHT_MODULE || 'playwright-core')" "$SCRIPT_FILE"; then
  echo "[FAIL] missing playwright-core require" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
fi
if ! grep -Fq -- "setInputFiles(process.env.DOCGEN_UI_TENDER_FILE)" "$SCRIPT_FILE"; then
  echo "[FAIL] missing tender upload step" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
fi
if ! grep -Fq -- "setInputFiles(process.env.DOCGEN_UI_BOQ_FILE)" "$SCRIPT_FILE"; then
  echo "[FAIL] missing boq upload step" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
fi
if ! grep -Fq -- "UI_STREAMLIT_UPLOAD" "$SCRIPT_FILE"; then
  echo "[FAIL] missing streamlit upload result emit" >&2
  cat "$SCRIPT_FILE" >&2
  exit 1
fi
if ! grep -Fq -- "null," "$SCRIPT_FILE"; then
  echo "[FAIL] missing explicit waitForFunction arg placeholder" >&2
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
chmod +x "$TMP_DIR/mock-node"

OUTPUT="$TMP_DIR/verify.out"

DOCGEN_UI_NODE_BIN="$TMP_DIR/mock-node" \
DOCGEN_TEST_NODE_CALLS="$CALLS" \
DOCGEN_UI_PLAYWRIGHT_NODE_PATH="$TMP_DIR/node_modules" \
DOCGEN_UI_FIXTURE_DIR="$FIXTURE_DIR" \
DOCGEN_UI_BASE_URL="http://127.0.0.1:18501" \
DOCGEN_UI_BROWSER_IMPL="node" \
bash "$VERIFY_SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[OK] page ready: http://127.0.0.1:18501" "$OUTPUT"
assert_contains "[OK] selected files: 招标/答疑 1 · 清单 1" "$OUTPUT"
assert_contains "[OK] outline loaded: outline entries rendered" "$OUTPUT"
assert_contains "[OK] streamlit upload request: PUT /_stcore/upload_file => 204 x2" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"
assert_contains "ui_upload_outline_smoke.cjs" "$CALLS"

echo "[PASS] verify_ui_upload_outline_chain regression checks passed"
