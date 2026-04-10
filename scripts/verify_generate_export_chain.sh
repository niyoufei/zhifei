#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
APP_DIR="${DOCGEN_APP_DIR:-/opt/docgen}"
API_BASE_URL="${DOCGEN_GENERATE_BASE_URL:-http://127.0.0.1:8010}"
VENV_PYTHON="${DOCGEN_VENV_PYTHON:-${APP_DIR%/}/.venv/bin/python}"
JSON_PYTHON="${DOCGEN_JSON_PYTHON:-python3}"
CURL_BIN="${DOCGEN_CURL_BIN:-curl}"
PIPELINE_PYTHON="${DOCGEN_GENERATE_PIPELINE_PYTHON:-$VENV_PYTHON}"
PIPELINE_SCRIPT="${DOCGEN_GENERATE_PIPELINE_SCRIPT:-$ROOT/scripts/run_actions_pipeline.py}"
KEYS_FILE="${ZF_KEYS_FILE:-${APP_DIR%/}/.runtime/local_keys.env}"
ACTIONS_KEY="${ZF_ACTIONS_KEY:-}"
PROJECT_ID="${DOCGEN_GENERATE_PROJECT_ID:-codex_generate_export_smoke_$(date '+%Y%m%d_%H%M%S')}"
TOPIC="${DOCGEN_GENERATE_TOPIC:-测试综合楼工程生成导出冒烟}"
FIXTURE_DIR="${DOCGEN_GENERATE_FIXTURE_DIR:-}"
KEEP_TMP="${DOCGEN_GENERATE_KEEP_TMP:-0}"
TIMEOUT_SECONDS="${DOCGEN_GENERATE_TIMEOUT_SECONDS:-180}"
POLL_SECONDS="${DOCGEN_GENERATE_POLL_SECONDS:-2}"
PROVIDER="${DOCGEN_GENERATE_DRY_RUN_PROVIDER:-google}"
MODEL="${DOCGEN_GENERATE_DRY_RUN_MODEL:-gemini-3-pro-preview}"
API_KEY="${DOCGEN_GENERATE_DRY_RUN_API_KEY:-dry-run-key}"
TMP_ROOT="${DOCGEN_GENERATE_TMP_ROOT:-${APP_DIR%/}/.codex_tmp}"
CONNECT_TIMEOUT="${DOCGEN_GENERATE_CONNECT_TIMEOUT_SECONDS:-5}"
MAX_TIME="${DOCGEN_GENERATE_MAX_TIME_SECONDS:-120}"

failures=0
tmp_dir=""
fixture_dir=""
cleanup_enabled=1

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站生成导出链自检。" >&2
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

check_nonempty_file() {
  local label="$1"
  local raw_path="$2"
  local abs_path=""
  if ! abs_path="$(resolve_app_path "$raw_path")"; then
    print_status "$label" "0" "empty path"
    return 0
  fi
  if [[ -s "$abs_path" ]]; then
    print_status "$label" "1" "$raw_path"
  elif [[ -e "$abs_path" ]]; then
    print_status "$label" "0" "$raw_path exists but empty"
  else
    print_status "$label" "0" "$raw_path missing ($abs_path)"
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
doc.save(root / "tender.docx")

wb = Workbook()
ws = wb.active
ws.title = "清单"
ws.append(["序号", "项目编码", "项目名称", "项目特征描述", "计量单位", "工程量"])
ws.append([1, "010101001001", "土方开挖", "机械开挖 基坑深度2m", "m3", 120.0])
ws.append([2, "010201001001", "混凝土垫层", "C15 商品混凝土", "m3", 32.5])
wb.save(root / "boq.xlsx")
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
if [[ ! -x "$PIPELINE_PYTHON" ]]; then
  echo "[ERROR] pipeline python 不可执行: $PIPELINE_PYTHON" >&2
  exit 1
fi
if [[ ! -f "$PIPELINE_SCRIPT" ]]; then
  echo "[ERROR] pipeline script 不存在: $PIPELINE_SCRIPT" >&2
  exit 1
fi

load_actions_key
if [[ -z "$ACTIONS_KEY" ]]; then
  echo "[ERROR] 缺少 ZF_ACTIONS_KEY，且未能从 $KEYS_FILE 读取。" >&2
  exit 1
fi

mkdir -p "$TMP_ROOT"
tmp_dir="$(mktemp -d "${TMP_ROOT%/}/generate-export-smoke.XXXXXX")"
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

echo "[INFO] app_dir=$APP_DIR"
echo "[INFO] api_base_url=$API_BASE_URL"
echo "[INFO] project_id=$PROJECT_ID"
echo "[INFO] topic=$TOPIC"
echo "[INFO] fixture_dir=$fixture_dir"
echo "[INFO] keep_tmp=$KEEP_TMP"
echo "[INFO] 注意：该脚本会写入少量 job/build/autoplan 冒烟记录。"

for fp in "$tender_file" "$boq_file"; do
  if [[ -f "$fp" ]]; then
    print_status "fixture $(basename "$fp")" "1" "$fp"
  else
    print_status "fixture $(basename "$fp")" "0" "$fp missing"
  fi
done

pipeline_log="$tmp_dir/pipeline.log"
set +e
(
  cd "$APP_DIR"
  "$PIPELINE_PYTHON" "$PIPELINE_SCRIPT" \
    --base-url "$API_BASE_URL" \
    --actions-key "$ACTIONS_KEY" \
    --topic "$TOPIC" \
    --project-id "$PROJECT_ID" \
    --tender "$tender_file" \
    --boq "$boq_file" \
    --outline "工程概况" \
    --outline "施工部署" \
    --outline "质量管理措施" \
    --variants 1 \
    --dry-run \
    --no-gate \
    --timeout-sec "$TIMEOUT_SECONDS" \
    --poll-sec "$POLL_SECONDS" \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    --api-key "$API_KEY" \
    >"$pipeline_log" 2>&1
)
pipeline_rc=$?
set -e
if [[ "$pipeline_rc" -eq 0 ]]; then
  print_status "run_actions_pipeline dry_run" "1" "rc=0"
else
  print_status "run_actions_pipeline dry_run" "0" "rc=${pipeline_rc}"
fi

job_id="$(awk -F= '/^job_id=/{print $2; exit}' "$pipeline_log" | tr -d '\r')"
saved_to="$(awk -F= '/^saved_to=/{print $2; exit}' "$pipeline_log" | tr -d '\r')"
if [[ -n "$job_id" ]]; then
  print_status "pipeline job_id" "1" "$job_id"
else
  print_status "pipeline job_id" "0" "missing"
fi
if [[ -n "$saved_to" ]]; then
  print_status "pipeline saved_to" "1" "$saved_to"
else
  print_status "pipeline saved_to" "0" "missing"
fi

check_nonempty_file "downloaded json" "${saved_to}/autoplan_${job_id}.json"
check_nonempty_file "downloaded docx" "${saved_to}/autoplan_${job_id}_v1.docx"
check_nonempty_file "downloaded compare docx" "${saved_to}/autoplan_${job_id}_compare_v1.docx"

job_status_json="$tmp_dir/job-status.json"
job_status_code="$(
  http_request "$job_status_json" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    "${API_BASE_URL%/}/actions/job_status?job_id=${job_id}"
)"
job_status="$(json_eval "$job_status_json" '(data.get("job") or {}).get("status") or ""')"
job_stage="$(json_eval "$job_status_json" '((data.get("job") or {}).get("progress") or {}).get("stage") or ""')"
if [[ "$job_status_code" = "200" && "$job_status" = "done" ]]; then
  print_status "actions job_status" "1" "status=${job_status}; stage=${job_stage}"
else
  print_status "actions job_status" "0" "HTTP ${job_status_code}; status=${job_status:-none}; stage=${job_stage:-none}"
fi

result_json="$tmp_dir/result.json"
result_code="$(
  http_request "$result_json" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    "${API_BASE_URL%/}/actions/result?job_id=${job_id}&variant=1&include_sections=false"
)"
result_ok="$(json_eval "$result_json" 'bool(data.get("ok"))')"
result_outline_count="$(json_eval "$result_json" 'len(data.get("outline") or [])')"
result_json_path="$(json_eval "$result_json" '((data.get("files") or {}).get("json")) or ""')"
result_docx_path="$(json_eval "$result_json" '((data.get("files") or {}).get("docx")) or ""')"
result_compare_path="$(json_eval "$result_json" '((data.get("files") or {}).get("compare_docx")) or ""')"
if [[ "$result_code" = "200" && "$result_ok" = "true" && "$result_outline_count" -ge 1 ]]; then
  print_status "actions result" "1" "outline=${result_outline_count}"
else
  print_status "actions result" "0" "HTTP ${result_code}; ok=${result_ok}; outline=${result_outline_count:-0}"
fi
check_nonempty_file "result json artifact" "$result_json_path"
check_nonempty_file "result docx artifact" "$result_docx_path"
check_nonempty_file "result compare docx artifact" "$result_compare_path"

download_json_out="$tmp_dir/download-result.json"
download_json_code="$(
  http_request "$download_json_out" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    "${API_BASE_URL%/}/actions/download?job_id=${job_id}&kind=json&variant=1"
)"
if [[ "$download_json_code" = "200" && -s "$download_json_out" ]]; then
  print_status "actions download json" "1" "bytes=$(wc -c < "$download_json_out" | tr -d ' ')"
else
  print_status "actions download json" "0" "HTTP ${download_json_code}; bytes=$(wc -c < "$download_json_out" 2>/dev/null | tr -d ' ' || printf '0')"
fi

download_docx_out="$tmp_dir/download-result.docx"
download_docx_code="$(
  http_request "$download_docx_out" \
    -H "x-actions-key: ${ACTIONS_KEY}" \
    "${API_BASE_URL%/}/actions/download?job_id=${job_id}&kind=docx&variant=1"
)"
if [[ "$download_docx_code" = "200" && -s "$download_docx_out" ]]; then
  print_status "actions download docx" "1" "bytes=$(wc -c < "$download_docx_out" | tr -d ' ')"
else
  print_status "actions download docx" "0" "HTTP ${download_docx_code}; bytes=$(wc -c < "$download_docx_out" 2>/dev/null | tr -d ' ' || printf '0')"
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
