#!/usr/bin/env bash
set -euo pipefail

OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
APP_DIR="${DOCGEN_APP_DIR:-/opt/docgen}"
API_BASE_URL="${DOCGEN_UPLOAD_PARSE_BASE_URL:-http://127.0.0.1:8010}"
INGEST_BASE_URL="${DOCGEN_UPLOAD_PARSE_INGEST_BASE_URL:-$API_BASE_URL}"
ACTIONS_BASE_URL="${DOCGEN_UPLOAD_PARSE_ACTIONS_BASE_URL:-$API_BASE_URL}"
VENV_PYTHON="${DOCGEN_VENV_PYTHON:-${APP_DIR%/}/.venv/bin/python}"
JSON_PYTHON="${DOCGEN_JSON_PYTHON:-python3}"
CURL_BIN="${DOCGEN_CURL_BIN:-curl}"
KEYS_FILE="${ZF_KEYS_FILE:-${APP_DIR%/}/.runtime/local_keys.env}"
ACTIONS_KEY="${ZF_ACTIONS_KEY:-}"
PROJECT_ID="${DOCGEN_UPLOAD_PARSE_PROJECT_ID:-codex_upload_parse_smoke_$(date '+%Y%m%d_%H%M%S')}"
FIXTURE_DIR="${DOCGEN_UPLOAD_PARSE_FIXTURE_DIR:-}"
KEEP_TMP="${DOCGEN_UPLOAD_PARSE_KEEP_TMP:-0}"
CONNECT_TIMEOUT="${DOCGEN_UPLOAD_PARSE_CONNECT_TIMEOUT_SECONDS:-5}"
MAX_TIME="${DOCGEN_UPLOAD_PARSE_MAX_TIME_SECONDS:-120}"
TMP_ROOT="${DOCGEN_UPLOAD_PARSE_TMP_ROOT:-${APP_DIR%/}/.codex_tmp}"

failures=0
tmp_dir=""
fixture_dir=""
cleanup_enabled=1
resolved_project_id=""

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站上传解析链自检。" >&2
  exit 1
fi

print_status() {
  local label="$1"
  local ok="$2"
  local detail="$3"
  if [[ "$ok" = "1" ]]; then
    echo "[OK] ${label}: ${detail}"
  else
    echo "[FAIL] ${label}: ${detail}"
    failures=$((failures + 1))
  fi
}

cleanup() {
  if [[ "$cleanup_enabled" = "1" && -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

resolve_app_path() {
  local raw="$1"
  if [[ -z "$raw" || "$raw" = "None" || "$raw" = "null" ]]; then
    return 1
  fi
  if [[ "$raw" = /* ]]; then
    printf '%s\n' "$raw"
  else
    printf '%s\n' "${APP_DIR%/}/$raw"
  fi
}

check_reported_path() {
  local label="$1"
  local raw_path="$2"
  local abs_path=""
  if ! abs_path="$(resolve_app_path "$raw_path")"; then
    print_status "$label" "0" "empty path"
    return 0
  fi
  if [[ -e "$abs_path" ]]; then
    print_status "$label" "1" "$raw_path"
  else
    print_status "$label" "0" "$raw_path (missing: $abs_path)"
  fi
}

http_request() {
  local body_file="$1"
  shift
  "$CURL_BIN" \
    --silent \
    --show-error \
    --location \
    --connect-timeout "$CONNECT_TIMEOUT" \
    --max-time "$MAX_TIME" \
    -o "$body_file" \
    -w '%{http_code}' \
    "$@" || true
}

json_eval() {
  local json_file="$1"
  local expression="$2"
  "$JSON_PYTHON" - "$json_file" "$expression" <<'PY'
import json
import sys

path, expression = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
value = eval(expression, {"__builtins__": {}}, {"data": data, "len": len, "bool": bool})
if value is None:
    print("")
elif isinstance(value, bool):
    print("true" if value else "false")
elif isinstance(value, (dict, list)):
    print(json.dumps(value, ensure_ascii=False))
else:
    print(value)
PY
}

load_actions_key() {
  if [[ -n "$ACTIONS_KEY" ]]; then
    return 0
  fi
  if [[ -f "$KEYS_FILE" ]]; then
    ACTIONS_KEY="$(
      KEYS_FILE="$KEYS_FILE" bash -lc '
        set -a
        . "$KEYS_FILE"
        set +a
        printf %s "${ZF_ACTIONS_KEY:-}"
      ' 2>/dev/null || true
    )"
  fi
}

create_smoke_fixtures() {
  mkdir -p "$fixture_dir"
  DOCGEN_SMOKE_FIXTURE_DIR="$fixture_dir" "$VENV_PYTHON" - <<'PY'
from pathlib import Path
import os

from docx import Document
from openpyxl import Workbook
from PIL import Image, ImageDraw

root = Path(os.environ["DOCGEN_SMOKE_FIXTURE_DIR"])
root.mkdir(parents=True, exist_ok=True)

doc = Document()
doc.add_paragraph("项目名称：测试综合楼工程")
doc.add_paragraph("项目编号：ZX-2026-001")
doc.add_paragraph("技术文件详细评审标准")
for line in (
    "1）工程概况",
    "2）施工部署",
    "3）主要施工方法",
    "4）确保工程质量的技术组织措施",
):
    doc.add_paragraph(line)
doc.add_paragraph("施工组织设计排版要求：纸张 A4，正文宋体小四，1.5 倍行距。")
doc.save(root / "tender.docx")

wb = Workbook()
ws = wb.active
ws.title = "清单"
ws.append(["序号", "项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"])
ws.append([1, "010101001001", "土方开挖", "机械开挖 基坑深度2m", "m3", 120.0])
ws.append([2, "010201001001", "混凝土垫层", "C15 商品混凝土", "m3", 32.5])
wb.save(root / "boq.xlsx")

im = Image.new("RGB", (960, 640), color="white")
draw = ImageDraw.Draw(im)
draw.rectangle((80, 80, 880, 560), outline="black", width=4)
draw.text((120, 140), "SMOKE DRAWING 01", fill="black")
draw.text((120, 210), "GRID A-1", fill="black")
im.save(root / "drawing.png")
PY
}

if [[ ! -d "$APP_DIR" ]]; then
  echo "[ERROR] app_dir 不存在: $APP_DIR" >&2
  exit 1
fi
if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "[ERROR] venv python 不可执行: $VENV_PYTHON" >&2
  exit 1
fi

load_actions_key
if [[ -z "$ACTIONS_KEY" ]]; then
  echo "[ERROR] 缺少 ZF_ACTIONS_KEY，且未能从 $KEYS_FILE 读取。" >&2
  exit 1
fi

mkdir -p "$TMP_ROOT"
tmp_dir="$(mktemp -d "${TMP_ROOT%/}/upload-parse-smoke.XXXXXX")"
if [[ "$KEEP_TMP" = "1" ]]; then
  cleanup_enabled=0
fi

if [[ -n "$FIXTURE_DIR" ]]; then
  fixture_dir="$FIXTURE_DIR"
else
  fixture_dir="$tmp_dir/fixtures"
  create_smoke_fixtures
fi

tender_file="$fixture_dir/tender.docx"
boq_file="$fixture_dir/boq.xlsx"
drawing_file="$fixture_dir/drawing.png"

echo "[INFO] app_dir=$APP_DIR"
echo "[INFO] api_base_url=$API_BASE_URL"
echo "[INFO] project_id=$PROJECT_ID"
echo "[INFO] fixture_dir=$fixture_dir"
echo "[INFO] keep_tmp=$KEEP_TMP"
echo "[INFO] 注意：该脚本会写入少量 ingest/audit/autoplan 冒烟记录。"

for fp in "$tender_file" "$boq_file" "$drawing_file"; do
  if [[ -f "$fp" ]]; then
    print_status "fixture $(basename "$fp")" "1" "$fp"
  else
    print_status "fixture $(basename "$fp")" "0" "$fp missing"
  fi
done

tender_ingest_json="$tmp_dir/ingest-tender.json"
tender_ingest_code="$(
  http_request "$tender_ingest_json" \
    -F "files=@${tender_file}" \
    "${INGEST_BASE_URL%/}/ingest/upload?project_id=${PROJECT_ID}&source_hint=tender_qa"
)"
tender_ingest_type="$(json_eval "$tender_ingest_json" '(data.get("saved") or [{}])[0].get("parsed_type") or ""')"
tender_ingest_extract="$(json_eval "$tender_ingest_json" '(data.get("saved") or [{}])[0].get("extract_saved_as") or ""')"
if [[ "$tender_ingest_code" = "200" && "$tender_ingest_type" = "word" ]]; then
  print_status "ingest tender" "1" "parsed_type=${tender_ingest_type}"
else
  print_status "ingest tender" "0" "HTTP ${tender_ingest_code}; parsed_type=${tender_ingest_type:-none}"
fi
check_reported_path "ingest tender extract" "$tender_ingest_extract"

boq_ingest_json="$tmp_dir/ingest-boq.json"
boq_ingest_code="$(
  http_request "$boq_ingest_json" \
    -F "files=@${boq_file}" \
    "${INGEST_BASE_URL%/}/ingest/upload?project_id=${PROJECT_ID}&source_hint=boq"
)"
boq_ingest_type="$(json_eval "$boq_ingest_json" '(data.get("saved") or [{}])[0].get("parsed_type") or ""')"
boq_ingest_sheets="$(json_eval "$boq_ingest_json" '((data.get("saved") or [{}])[0].get("parsed_meta") or {}).get("sheets") or 0')"
if [[ "$boq_ingest_code" = "200" && "$boq_ingest_type" = "excel" && "$boq_ingest_sheets" -ge 1 ]]; then
  print_status "ingest boq" "1" "parsed_type=${boq_ingest_type}; sheets=${boq_ingest_sheets}"
else
  print_status "ingest boq" "0" "HTTP ${boq_ingest_code}; parsed_type=${boq_ingest_type:-none}; sheets=${boq_ingest_sheets:-0}"
fi
check_reported_path "ingest boq extract" "$(json_eval "$boq_ingest_json" '(data.get("saved") or [{}])[0].get("extract_saved_as") or ""')"

drawing_ingest_json="$tmp_dir/ingest-drawing.json"
drawing_ingest_code="$(
  http_request "$drawing_ingest_json" \
    -F "files=@${drawing_file}" \
    "${INGEST_BASE_URL%/}/ingest/upload?project_id=${PROJECT_ID}&source_hint=drawing_standard"
)"
drawing_ingest_type="$(json_eval "$drawing_ingest_json" '(data.get("saved") or [{}])[0].get("parsed_type") or ""')"
drawing_preview="$(json_eval "$drawing_ingest_json" '(data.get("saved") or [{}])[0].get("preview_saved_as") or ""')"
if [[ "$drawing_ingest_code" = "200" && "$drawing_ingest_type" = "image" ]]; then
  print_status "ingest drawing" "1" "parsed_type=${drawing_ingest_type}"
else
  print_status "ingest drawing" "0" "HTTP ${drawing_ingest_code}; parsed_type=${drawing_ingest_type:-none}"
fi
check_reported_path "ingest drawing preview" "$drawing_preview"
check_reported_path "ingest drawing extract" "$(json_eval "$drawing_ingest_json" '(data.get("saved") or [{}])[0].get("extract_saved_as") or ""')"

tender_parse_json="$tmp_dir/actions-tender-parse.json"
tender_parse_code="$(
  http_request "$tender_parse_json" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    -F "files=@${tender_file}" \
    "${ACTIONS_BASE_URL%/}/actions/tender/parse?project_id=${PROJECT_ID}"
)"
tender_parse_ok="$(json_eval "$tender_parse_json" 'bool(data.get("ok"))')"
resolved_project_id="$(json_eval "$tender_parse_json" 'data.get("project_id") or ""')"
tender_project_name="$(json_eval "$tender_parse_json" 'data.get("project_name") or ""')"
tender_project_code="$(json_eval "$tender_parse_json" 'data.get("project_code") or ""')"
tender_outline_count="$(json_eval "$tender_parse_json" 'len((data.get("matrix") or {}).get("outline") or [])')"
if [[ "$tender_parse_code" = "200" && "$tender_parse_ok" = "true" && -n "$resolved_project_id" && -n "$tender_project_name" && -n "$tender_project_code" && "$tender_outline_count" -ge 1 ]]; then
  print_status "actions tender/parse" "1" "project_id=${resolved_project_id}; outline=${tender_outline_count}"
else
  print_status "actions tender/parse" "0" "HTTP ${tender_parse_code}; ok=${tender_parse_ok}; project_id=${resolved_project_id:-none}; outline=${tender_outline_count:-0}"
fi
check_reported_path "tender matrix file" "$(json_eval "$tender_parse_json" 'data.get("saved_at") or ""')"
check_reported_path "bidding format config" "$(json_eval "$tender_parse_json" 'data.get("bidding_format_config_saved_at") or ""')"

if [[ -z "$resolved_project_id" ]]; then
  resolved_project_id="$PROJECT_ID"
fi
echo "[INFO] resolved_project_id=$resolved_project_id"

boq_parse_json="$tmp_dir/actions-boq-parse.json"
boq_parse_code="$(
  http_request "$boq_parse_json" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    -F "file=@${boq_file}" \
    "${ACTIONS_BASE_URL%/}/actions/boq/parse?project_id=${resolved_project_id}"
)"
boq_parse_ok="$(json_eval "$boq_parse_json" 'bool(data.get("ok"))')"
boq_item_count="$(json_eval "$boq_parse_json" 'len(data.get("items") or [])')"
boq_source_file_count="$(json_eval "$boq_parse_json" 'data.get("source_file_count") or 0')"
if [[ "$boq_parse_code" = "200" && "$boq_parse_ok" = "true" && "$boq_item_count" -ge 1 && "$boq_source_file_count" -ge 1 ]]; then
  print_status "actions boq/parse" "1" "items=${boq_item_count}; files=${boq_source_file_count}"
else
  print_status "actions boq/parse" "0" "HTTP ${boq_parse_code}; ok=${boq_parse_ok}; items=${boq_item_count:-0}; files=${boq_source_file_count:-0}"
fi
check_reported_path "boq data file" "$(json_eval "$boq_parse_json" 'data.get("saved_at") or ""')"

plan_payload_json="$tmp_dir/plan-payload.json"
TENDER_PARSE_JSON="$tender_parse_json" PLAN_PAYLOAD_JSON="$plan_payload_json" "$JSON_PYTHON" - <<'PY'
import json
import os
from pathlib import Path

data = json.loads(Path(os.environ["TENDER_PARSE_JSON"]).read_text(encoding="utf-8"))
matrix = data.get("matrix") or {}
outline = list(matrix.get("outline") or [])
if not outline:
    outline = ["工程概况", "施工部署", "质量管理措施"]
payload = {
    "outline": outline[:3],
    "style": matrix.get("style") or {},
    "chapter_requirements": matrix.get("chapter_requirements") or {},
    "chapter_pages": matrix.get("chapter_pages") or {},
    "global_instruction": "upload-parse-smoke",
    "compare_mode": "summary",
}
Path(os.environ["PLAN_PAYLOAD_JSON"]).write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
PY

plan_save_json="$tmp_dir/actions-plan-save.json"
plan_save_code="$(
  http_request "$plan_save_json" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    -H "content-type: application/json" \
    --data-binary "@${plan_payload_json}" \
    "${ACTIONS_BASE_URL%/}/actions/plan/save?project_id=${resolved_project_id}"
)"
plan_save_ok="$(json_eval "$plan_save_json" 'bool(data.get("ok"))')"
if [[ "$plan_save_code" = "200" && "$plan_save_ok" = "true" ]]; then
  print_status "actions plan/save" "1" "project_id=${resolved_project_id}"
else
  print_status "actions plan/save" "0" "HTTP ${plan_save_code}; ok=${plan_save_ok}"
fi
check_reported_path "plan file" "$(json_eval "$plan_save_json" 'data.get("saved_at") or ""')"

plan_get_json="$tmp_dir/actions-plan-get.json"
plan_get_code="$(
  http_request "$plan_get_json" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    "${ACTIONS_BASE_URL%/}/actions/plan/get?project_id=${resolved_project_id}"
)"
plan_get_ok="$(json_eval "$plan_get_json" 'bool(data.get("ok"))')"
plan_outline_count="$(json_eval "$plan_get_json" 'len((data.get("plan") or {}).get("outline") or [])')"
plan_instruction="$(json_eval "$plan_get_json" '(data.get("plan") or {}).get("global_instruction") or ""')"
if [[ "$plan_get_code" = "200" && "$plan_get_ok" = "true" && "$plan_outline_count" -ge 1 && "$plan_instruction" = "upload-parse-smoke" ]]; then
  print_status "actions plan/get" "1" "outline=${plan_outline_count}; instruction=${plan_instruction}"
else
  print_status "actions plan/get" "0" "HTTP ${plan_get_code}; ok=${plan_get_ok}; outline=${plan_outline_count:-0}; instruction=${plan_instruction:-none}"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  if [[ "$cleanup_enabled" = "0" && -n "$tmp_dir" ]]; then
    echo "[INFO] smoke_tmp_dir=${tmp_dir}"
  fi
  exit 1
fi

echo "[SUMMARY] all checks passed."
if [[ "$cleanup_enabled" = "0" && -n "$tmp_dir" ]]; then
  echo "[INFO] smoke_tmp_dir=${tmp_dir}"
fi
