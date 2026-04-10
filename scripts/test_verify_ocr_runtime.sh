#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_ocr_runtime.sh"
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
payload="$(cat)"
if grep -q 'guess_ocr_lang' <<<"$payload"; then
  cat <<'OUT'
available=True
lang=chi_sim+eng
OUT
else
  cat <<'OUT'
error=None
pages=1
text=HELLO 123
OUT
fi
EOF

chmod +x "$TMP_DIR/tesseract" "$TMP_DIR/app/.venv/bin/python"

echo "[STEP] smoke should pass"
PATH="$TMP_DIR:$PATH" \
DOCGEN_OS_NAME="Linux" \
DOCGEN_APP_DIR="$TMP_DIR/app" \
DOCGEN_VENV_PYTHON="$TMP_DIR/app/.venv/bin/python" \
DOCGEN_EXPECT_OCR_CHINESE="1" \
bash "$VERIFY_SCRIPT" >"$TMP_DIR/out" 2>&1

assert_contains "[OK] venv python:" "$TMP_DIR/out"
assert_contains "[OK] ocr binary:" "$TMP_DIR/out"
assert_contains "[OK] ocr runtime: available=True lang=chi_sim+eng" "$TMP_DIR/out"
assert_contains "[OK] ocr smoke: pages=1 text=HELLO 123" "$TMP_DIR/out"
assert_contains "[SUMMARY] all checks passed." "$TMP_DIR/out"

echo "[PASS] verify_ocr_runtime regression checks passed"
