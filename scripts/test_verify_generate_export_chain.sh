#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_generate_export_chain.sh"
TMP_DIR="$(mktemp -d)"
APP_DIR="$TMP_DIR/app"
FIXTURE_DIR="$TMP_DIR/fixtures"
OUT_DIR="$APP_DIR/build/actions_runs/test-job-001"

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
  "$OUT_DIR" \
  "$APP_DIR/build" \
  "$FIXTURE_DIR"

cat > "$APP_DIR/.runtime/local_keys.env" <<'EOF'
ZF_ACTIONS_KEY=test-actions-key
EOF

printf 'docx' > "$FIXTURE_DIR/tender.docx"
printf 'xlsx' > "$FIXTURE_DIR/boq.xlsx"
printf '{"ok":true}' > "$OUT_DIR/autoplan_test-job-001.json"
printf 'docx-binary' > "$OUT_DIR/autoplan_test-job-001_v1.docx"
printf 'compare-binary' > "$OUT_DIR/autoplan_test-job-001_compare_v1.docx"
printf '{"variants":[{}]}' > "$APP_DIR/build/actions_test-job-001.json"
printf 'server-docx' > "$APP_DIR/build/actions_test-job-001_v1.docx"
printf 'server-compare' > "$APP_DIR/build/actions_test-job-001_compare_v1.docx"

cat > "$TMP_DIR/pipeline.py" <<'EOF'
#!/usr/bin/env python3
from pathlib import Path
import os
import sys

app_dir = Path(os.environ["DOCGEN_TEST_APP_DIR"])
out_dir = app_dir / "build" / "actions_runs" / "test-job-001"
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "autoplan_test-job-001.json").write_text('{"ok": true}', encoding="utf-8")
(out_dir / "autoplan_test-job-001_v1.docx").write_bytes(b"docx-binary")
(out_dir / "autoplan_test-job-001_compare_v1.docx").write_bytes(b"compare-binary")
print("job_id=test-job-001")
print("saved_to=build/actions_runs/test-job-001")
sys.exit(0)
EOF
chmod +x "$TMP_DIR/pipeline.py"

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
    -H|--header|--connect-timeout|--max-time)
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
  *"/actions/job_status?job_id=test-job-001")
    cat > "$body_file" <<'JSON'
{"ok":true,"job":{"status":"done","progress":{"stage":"done"},"files":{"json":"build/actions_test-job-001.json","docx":["build/actions_test-job-001_v1.docx"],"compare_docx":["build/actions_test-job-001_compare_v1.docx"]}}}
JSON
    ;;
  *"/actions/result?job_id=test-job-001"*)
    cat > "$body_file" <<'JSON'
{"ok":true,"outline":["工程概况","施工部署"],"files":{"json":"build/actions_test-job-001.json","docx":"build/actions_test-job-001_v1.docx","compare_docx":"build/actions_test-job-001_compare_v1.docx"}}
JSON
    ;;
  *"/actions/download?job_id=test-job-001&kind=json"*)
    printf '{"ok":true}' > "$body_file"
    ;;
  *"/actions/download?job_id=test-job-001&kind=docx"*)
    printf 'docx-binary' > "$body_file"
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
DOCGEN_GENERATE_PIPELINE_PYTHON="$(command -v python3)" \
DOCGEN_GENERATE_PIPELINE_SCRIPT="$TMP_DIR/pipeline.py" \
DOCGEN_GENERATE_BASE_URL="http://127.0.0.1:8010" \
DOCGEN_GENERATE_FIXTURE_DIR="$FIXTURE_DIR" \
DOCGEN_GENERATE_PROJECT_ID="codex_generate_export_smoke_test" \
DOCGEN_TEST_APP_DIR="$APP_DIR" \
ZF_KEYS_FILE="$APP_DIR/.runtime/local_keys.env" \
bash "$VERIFY_SCRIPT" >"$OUTPUT" 2>&1

assert_contains "[OK] run_actions_pipeline dry_run: rc=0" "$OUTPUT"
assert_contains "[OK] pipeline job_id: test-job-001" "$OUTPUT"
assert_contains "[OK] pipeline saved_to: build/actions_runs/test-job-001" "$OUTPUT"
assert_contains "[OK] downloaded json: build/actions_runs/test-job-001/autoplan_test-job-001.json" "$OUTPUT"
assert_contains "[OK] downloaded docx: build/actions_runs/test-job-001/autoplan_test-job-001_v1.docx" "$OUTPUT"
assert_contains "[OK] downloaded compare docx: build/actions_runs/test-job-001/autoplan_test-job-001_compare_v1.docx" "$OUTPUT"
assert_contains "[OK] actions job_status: status=done; stage=done" "$OUTPUT"
assert_contains "[OK] actions result: outline=2" "$OUTPUT"
assert_contains "[OK] result json artifact: build/actions_test-job-001.json" "$OUTPUT"
assert_contains "[OK] actions download json:" "$OUTPUT"
assert_contains "[OK] actions download docx:" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

echo "[PASS] verify_generate_export_chain regression checks passed"
