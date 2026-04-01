#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOCGEN_PREVIEW="${DOCGEN_PREVIEW:-0}"
HOST="${DOCGEN_ADMIN_SMOKE_HOST:-127.0.0.1}"
PORT="${DOCGEN_ADMIN_SMOKE_PORT:-18010}"
RUNTIME_DIR="${DOCGEN_ADMIN_SMOKE_RUNTIME_DIR:-$ROOT/.runtime/docgen}"
LOG_FILE="${DOCGEN_ADMIN_SMOKE_LOG_FILE:-$RUNTIME_DIR/local-admin-ops-smoke.log}"
KEEP_LATEST="${DOCGEN_ADMIN_SMOKE_KEEP_LATEST:-20}"
OLDER_THAN_HOURS="${DOCGEN_ADMIN_SMOKE_OLDER_THAN_HOURS:-168}"
SNAPSHOT_EXPORT_LIMIT="${DOCGEN_ADMIN_SMOKE_SNAPSHOT_EXPORT_LIMIT:-20}"
TENANT_LIMIT="${DOCGEN_ADMIN_SMOKE_TENANT_LIMIT:-5}"
WINDOW_LIMIT="${DOCGEN_ADMIN_SMOKE_WINDOW_LIMIT:-25}"
PYTHON_BIN="${DOCGEN_ADMIN_SMOKE_PYTHON:-}"

pick_python() {
  if [[ -n "$PYTHON_BIN" && -x "$PYTHON_BIN" ]]; then
    printf '%s\n' "$PYTHON_BIN"
    return 0
  fi
  if [[ -x "$ROOT/venv/bin/python3" ]]; then
    printf '%s\n' "$ROOT/venv/bin/python3"
    return 0
  fi
  if [[ -x "$ROOT/.venv/bin/python3" ]]; then
    printf '%s\n' "$ROOT/.venv/bin/python3"
    return 0
  fi
  command -v python3
}

PYTHON_BIN="$(pick_python)"

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_number() {
  local value="$1"
  local label="$2"
  [[ "$value" =~ ^[0-9]+$ ]] || fail "$label must be a non-negative integer"
}

port_owner_pid() {
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -n1 || true
}

format_command() {
  "$PYTHON_BIN" - "$@" <<'PY'
import shlex
import sys

print(" ".join(shlex.quote(arg) for arg in sys.argv[1:]))
PY
}

json_field() {
  local file="$1"
  local expr="$2"
  "$PYTHON_BIN" - "$file" "$expr" <<'PY'
import json
import sys

path = sys.argv[1]
expr = sys.argv[2]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)
value = data
for part in expr.split("."):
    if not isinstance(value, dict):
        raise SystemExit(1)
    value = value.get(part)
if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print("")
else:
    print(value)
PY
}

require_number "$PORT" "DOCGEN_ADMIN_SMOKE_PORT"
require_number "$KEEP_LATEST" "DOCGEN_ADMIN_SMOKE_KEEP_LATEST"
require_number "$OLDER_THAN_HOURS" "DOCGEN_ADMIN_SMOKE_OLDER_THAN_HOURS"
require_number "$SNAPSHOT_EXPORT_LIMIT" "DOCGEN_ADMIN_SMOKE_SNAPSHOT_EXPORT_LIMIT"
require_number "$TENANT_LIMIT" "DOCGEN_ADMIN_SMOKE_TENANT_LIMIT"
require_number "$WINDOW_LIMIT" "DOCGEN_ADMIN_SMOKE_WINDOW_LIMIT"

BACKEND_URL="http://${HOST}:${PORT}"
OWNER_PID="$(port_owner_pid "$PORT")"
[[ -z "$OWNER_PID" ]] || fail "port ${PORT} already in use by pid=${OWNER_PID}"

START_CMD=(
  "$PYTHON_BIN" -m uvicorn backend.app.main:app
  --host "$HOST"
  --port "$PORT"
)

if [[ "$DOCGEN_PREVIEW" = "1" ]]; then
  printf 'root=%s\n' "$ROOT"
  printf 'host=%s\n' "$HOST"
  printf 'port=%s\n' "$PORT"
  printf 'backend_url=%s\n' "$BACKEND_URL"
  printf 'python_bin=%s\n' "$PYTHON_BIN"
  printf 'runtime_dir=%s\n' "$RUNTIME_DIR"
  printf 'log_file=%s\n' "$LOG_FILE"
  printf 'tenant_limit=%s\n' "$TENANT_LIMIT"
  printf 'window_limit=%s\n' "$WINDOW_LIMIT"
  printf 'keep_latest=%s\n' "$KEEP_LATEST"
  printf 'older_than_hours=%s\n' "$OLDER_THAN_HOURS"
  printf 'snapshot_export_limit=%s\n' "$SNAPSHOT_EXPORT_LIMIT"
  printf 'admin_key_source=temp_runtime_only\n'
  printf 'start_command=%s\n' "$(format_command "${START_CMD[@]}")"
  printf 'tenant_usage_endpoint=%s\n' "${BACKEND_URL}/auth/tenant_usage_reports"
  printf 'exports_summary_endpoint=%s\n' "${BACKEND_URL}/auth/tenant_usage_reports_exports_summary"
  printf 'snapshot_export_summary_endpoint=%s\n' "${BACKEND_URL}/auth/tenant_usage_reports_exports_summary_snapshot_exports_summary"
  exit 0
fi

mkdir -p "$RUNTIME_DIR"
TMP_DIR="$(mktemp -d)"
TENANT_JSON="$TMP_DIR/tenant_usage.json"
EXPORTS_JSON="$TMP_DIR/exports_summary.json"
SNAPSHOT_EXPORT_JSON="$TMP_DIR/snapshot_export_summary.json"
TEMP_BACKEND_PID=""

cleanup() {
  if [[ -n "$TEMP_BACKEND_PID" ]] && kill -0 "$TEMP_BACKEND_PID" 2>/dev/null; then
    kill "$TEMP_BACKEND_PID" >/dev/null 2>&1 || true
    wait "$TEMP_BACKEND_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ADMIN_KEY="$("$PYTHON_BIN" - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"

(
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
  export ZF_ADMIN_KEY="$ADMIN_KEY"
  export ZF_DISABLE_PREWARM=1
  "${START_CMD[@]}" >"$LOG_FILE" 2>&1
) &
TEMP_BACKEND_PID=$!

for _ in $(seq 1 60); do
  if curl -fsS "${BACKEND_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

curl -fsS "${BACKEND_URL}/health" >/dev/null 2>&1 || fail "temporary backend did not become healthy"

tenant_status="$(
  curl -sS -o "$TENANT_JSON" -w '%{http_code}' \
    -H "Authorization: Bearer ${ADMIN_KEY}" \
    "${BACKEND_URL}/auth/tenant_usage_reports?limit=${TENANT_LIMIT}&window_limit=${WINDOW_LIMIT}&sort_by=charge_cost_total&sort_order=desc"
)"
[[ "$tenant_status" = "200" ]] || fail "tenant_usage_reports status=${tenant_status}"

exports_status="$(
  curl -sS -o "$EXPORTS_JSON" -w '%{http_code}' \
    -H "Authorization: Bearer ${ADMIN_KEY}" \
    "${BACKEND_URL}/auth/tenant_usage_reports_exports_summary?keep_latest=${KEEP_LATEST}&older_than_hours=${OLDER_THAN_HOURS}"
)"
[[ "$exports_status" = "200" ]] || fail "tenant_usage_reports_exports_summary status=${exports_status}"

snapshot_export_status="$(
  curl -sS -o "$SNAPSHOT_EXPORT_JSON" -w '%{http_code}' \
    -H "Authorization: Bearer ${ADMIN_KEY}" \
    "${BACKEND_URL}/auth/tenant_usage_reports_exports_summary_snapshot_exports_summary?limit=${SNAPSHOT_EXPORT_LIMIT}&keep_latest=${KEEP_LATEST}&older_than_hours=${OLDER_THAN_HOURS}"
)"
[[ "$snapshot_export_status" = "200" ]] || fail "tenant_usage_reports_exports_summary_snapshot_exports_summary status=${snapshot_export_status}"

[[ "$(json_field "$TENANT_JSON" "ok")" = "true" ]] || fail "tenant_usage_reports ok=false"
[[ "$(json_field "$EXPORTS_JSON" "ok")" = "true" ]] || fail "exports_summary ok=false"
[[ "$(json_field "$SNAPSHOT_EXPORT_JSON" "ok")" = "true" ]] || fail "snapshot_export_summary ok=false"

printf 'backend_url=%s\n' "$BACKEND_URL"
printf 'temp_backend_pid=%s\n' "$TEMP_BACKEND_PID"
printf 'log_file=%s\n' "$LOG_FILE"
printf 'tenant_usage_status=%s\n' "$tenant_status"
printf 'tenant_usage_page_mode=%s\n' "$(json_field "$TENANT_JSON" "page.mode")"
printf 'tenant_usage_tenant_count=%s\n' "$(json_field "$TENANT_JSON" "summary.tenant_count")"
printf 'exports_summary_status=%s\n' "$exports_status"
printf 'exports_total=%s\n' "$(json_field "$EXPORTS_JSON" "summary.total_exports")"
printf 'exports_confirm_token_records=%s\n' "$(json_field "$EXPORTS_JSON" "summary.confirm_token_state.record_count")"
printf 'snapshot_export_summary_status=%s\n' "$snapshot_export_status"
printf 'snapshot_export_count=%s\n' "$(json_field "$SNAPSHOT_EXPORT_JSON" "count")"
echo "[SUMMARY] all checks passed."
