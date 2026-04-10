#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_upload_parse_chain.sh"
TMP_DIR="$(mktemp -d)"
APP_DIR="$TMP_DIR/app"
FIXTURE_DIR="$TMP_DIR/fixtures"

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

mkdir -p \
  "$APP_DIR/.runtime" \
  "$APP_DIR/backend/data/uploads" \
  "$APP_DIR/backend/data/extracts" \
  "$APP_DIR/backend/data/previews" \
  "$APP_DIR/backend/data/autoplan/projects/ZX_2026_001"

cat > "$APP_DIR/.runtime/local_keys.env" <<'EOF'
ZF_ACTIONS_KEY=test-actions-key
EOF

mkdir -p "$FIXTURE_DIR"
printf 'docx' > "$FIXTURE_DIR/tender.docx"
printf 'xlsx' > "$FIXTURE_DIR/boq.xlsx"
printf 'png' > "$FIXTURE_DIR/drawing.png"

printf 'saved' > "$APP_DIR/backend/data/uploads/tender.docx"
printf 'saved' > "$APP_DIR/backend/data/uploads/boq.xlsx"
printf 'saved' > "$APP_DIR/backend/data/uploads/drawing.png"
printf 'extract' > "$APP_DIR/backend/data/extracts/tender.txt"
printf 'extract' > "$APP_DIR/backend/data/extracts/boq.txt"
printf 'extract' > "$APP_DIR/backend/data/extracts/drawing.txt"
printf 'preview' > "$APP_DIR/backend/data/previews/drawing_preview.png"
printf '{}' > "$APP_DIR/backend/data/autoplan/projects/ZX_2026_001/tender_matrix.json"
printf '{}' > "$APP_DIR/backend/data/autoplan/projects/ZX_2026_001/bidding_format_config.json"
printf '{}' > "$APP_DIR/backend/data/autoplan/projects/ZX_2026_001/boq_data.json"
printf '{}' > "$APP_DIR/backend/data/autoplan/projects/ZX_2026_001/plan.json"

cat > "$TMP_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

body_file=""
url=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o)
      body_file="$2"
      shift 2
      ;;
    -w)
      shift 2
      ;;
    -H|--header|-F|--form|--data-binary|--data|--request|--connect-timeout|--max-time)
      shift 2
      ;;
    --silent|--show-error|--location)
      shift
      ;;
    *)
      url="$1"
      shift
      ;;
  esac
done

case "$url" in
  *"/ingest/upload?project_id="*"&source_hint=tender_qa")
    cat > "$body_file" <<'JSON'
{"saved":[{"parsed_type":"word","extract_saved_as":"backend/data/extracts/tender.txt"}]}
JSON
    ;;
  *"/ingest/upload?project_id="*"&source_hint=boq")
    cat > "$body_file" <<'JSON'
{"saved":[{"parsed_type":"excel","extract_saved_as":"backend/data/extracts/boq.txt","parsed_meta":{"sheets":1}}]}
JSON
    ;;
  *"/ingest/upload?project_id="*"&source_hint=drawing_standard")
    cat > "$body_file" <<'JSON'
{"saved":[{"parsed_type":"image","extract_saved_as":"backend/data/extracts/drawing.txt","preview_saved_as":"backend/data/previews/drawing_preview.png"}]}
JSON
    ;;
  *"/actions/tender/parse?project_id="*)
    cat > "$body_file" <<'JSON'
{"ok":true,"project_id":"ZX_2026_001","project_name":"测试综合楼工程","project_code":"ZX-2026-001","saved_at":"backend/data/autoplan/projects/ZX_2026_001/tender_matrix.json","bidding_format_config_saved_at":"backend/data/autoplan/projects/ZX_2026_001/bidding_format_config.json","matrix":{"outline":["工程概况","施工部署"],"style":{"font_family":"宋体"},"chapter_requirements":{"工程概况":["说明项目位置"]},"chapter_pages":{"工程概况":3}}}
JSON
    ;;
  *"/actions/boq/parse?project_id=ZX_2026_001")
    cat > "$body_file" <<'JSON'
{"ok":true,"items":[{"name":"土方开挖"}],"source_file_count":1,"saved_at":"backend/data/autoplan/projects/ZX_2026_001/boq_data.json"}
JSON
    ;;
  *"/actions/plan/save?project_id=ZX_2026_001")
    cat > "$body_file" <<'JSON'
{"ok":true,"saved_at":"backend/data/autoplan/projects/ZX_2026_001/plan.json"}
JSON
    ;;
  *"/actions/plan/get?project_id=ZX_2026_001")
    cat > "$body_file" <<'JSON'
{"ok":true,"plan":{"outline":["工程概况","施工部署"],"global_instruction":"upload-parse-smoke"}}
JSON
    ;;
  *)
    echo "[FAIL] unexpected url: $url" >&2
    exit 1
    ;;
esac

printf '200'
EOF
chmod +x "$TMP_DIR/curl"

OUTPUT="$TMP_DIR/verify.out"

PATH="$TMP_DIR:$PATH" \
DOCGEN_OS_NAME="Linux" \
DOCGEN_APP_DIR="$APP_DIR" \
DOCGEN_VENV_PYTHON="$(command -v python3)" \
DOCGEN_JSON_PYTHON="$(command -v python3)" \
DOCGEN_UPLOAD_PARSE_BASE_URL="http://127.0.0.1:8010" \
DOCGEN_UPLOAD_PARSE_FIXTURE_DIR="$FIXTURE_DIR" \
DOCGEN_UPLOAD_PARSE_PROJECT_ID="codex_smoke_upload_chain_test" \
ZF_KEYS_FILE="$APP_DIR/.runtime/local_keys.env" \
bash "$VERIFY_SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[OK] ingest tender: parsed_type=word" "$OUTPUT"
assert_contains "[OK] ingest boq: parsed_type=excel; sheets=1" "$OUTPUT"
assert_contains "[OK] ingest drawing: parsed_type=image" "$OUTPUT"
assert_contains "[OK] actions tender/parse: project_id=ZX_2026_001; outline=2" "$OUTPUT"
assert_contains "[OK] actions boq/parse: items=1; files=1" "$OUTPUT"
assert_contains "[OK] actions plan/save: project_id=ZX_2026_001" "$OUTPUT"
assert_contains "[OK] actions plan/get: outline=2; instruction=upload-parse-smoke" "$OUTPUT"
assert_contains "[OK] plan file: backend/data/autoplan/projects/ZX_2026_001/plan.json" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

echo "[PASS] verify_upload_parse_chain regression checks passed"
