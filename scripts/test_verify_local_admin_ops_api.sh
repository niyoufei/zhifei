#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/verify_local_admin_ops_api.sh"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

pick_free_port() {
  python3 - <<'PY'
import socket

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
}

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
    echo "[FAIL] unexpected text present: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

API_PORT="$(pick_free_port)"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_PREVIEW=1 \
DOCGEN_ADMIN_SMOKE_PORT="$API_PORT" \
bash "$SCRIPT" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "host=127.0.0.1" "$PREVIEW_OUTPUT"
assert_contains "port=$API_PORT" "$PREVIEW_OUTPUT"
assert_contains "admin_key_source=temp_runtime_only" "$PREVIEW_OUTPUT"
assert_contains "tenant_usage_endpoint=http://127.0.0.1:${API_PORT}/auth/tenant_usage_reports" "$PREVIEW_OUTPUT"
assert_contains "exports_summary_endpoint=http://127.0.0.1:${API_PORT}/auth/tenant_usage_reports_exports_summary" "$PREVIEW_OUTPUT"
assert_contains "snapshot_export_summary_endpoint=http://127.0.0.1:${API_PORT}/auth/tenant_usage_reports_exports_summary_snapshot_exports_summary" "$PREVIEW_OUTPUT"
assert_not_contains "Bearer " "$PREVIEW_OUTPUT"

LIVE_OUTPUT="$TMP_DIR/live.log"
DOCGEN_ADMIN_SMOKE_PORT="$API_PORT" \
DOCGEN_ADMIN_SMOKE_LOG_FILE="$TMP_DIR/local-admin-ops-smoke.log" \
bash "$SCRIPT" >"$LIVE_OUTPUT" 2>&1

assert_contains "backend_url=http://127.0.0.1:${API_PORT}" "$LIVE_OUTPUT"
assert_contains "tenant_usage_status=200" "$LIVE_OUTPUT"
assert_contains "exports_summary_status=200" "$LIVE_OUTPUT"
assert_contains "snapshot_export_summary_status=200" "$LIVE_OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$LIVE_OUTPUT"
assert_not_contains "Bearer " "$LIVE_OUTPUT"

echo "[PASS] verify_local_admin_ops_api regression checks passed"
