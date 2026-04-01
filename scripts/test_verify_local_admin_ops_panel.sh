#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/verify_local_admin_ops_panel.sh"
TMP_DIR="$(mktemp -d)"
FIXTURE_NODE_PATH="$TMP_DIR/node_modules"

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

mkdir -p "$FIXTURE_NODE_PATH/playwright-core"
BACKEND_PORT="$(pick_free_port)"
WEB_PORT="$(pick_free_port)"

cat > "$TMP_DIR/mock-node" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_FILE="${1:?missing script file}"

for needle in \
  "维护 / 诊断（开发）" \
  "运营管理台（只读）" \
  "getByLabel('Admin Key')" \
  "刷新管理台" \
  "导出资产" \
  "快照导出"
do
  if ! grep -Fq -- "$needle" "$SCRIPT_FILE"; then
    echo "[FAIL] missing expected browser step: $needle" >&2
    cat "$SCRIPT_FILE" >&2
    exit 1
  fi
done

cat <<'TEXT'
UI_PAGE_READY=1
UI_DEV_PANEL_VISIBLE=1
UI_ADMIN_PANEL_VISIBLE=1
UI_ADMIN_REFRESH_SUCCESS=1
UI_TENANT_TAB_READY=1
UI_EXPORTS_TAB_READY=1
UI_SNAPSHOT_EXPORT_TAB_READY=1
UI_ERROR=none
TEXT
EOF
chmod +x "$TMP_DIR/mock-node"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_PREVIEW=1 \
DOCGEN_ADMIN_UI_SMOKE_BROWSER_IMPL=node \
DOCGEN_ADMIN_UI_SMOKE_BACKEND_PORT="$BACKEND_PORT" \
DOCGEN_ADMIN_UI_SMOKE_WEB_PORT="$WEB_PORT" \
DOCGEN_ADMIN_UI_NODE_BIN="$TMP_DIR/mock-node" \
DOCGEN_ADMIN_UI_PLAYWRIGHT_NODE_PATH="$FIXTURE_NODE_PATH" \
bash "$SCRIPT" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "backend_port=$BACKEND_PORT" "$PREVIEW_OUTPUT"
assert_contains "web_port=$WEB_PORT" "$PREVIEW_OUTPUT"
assert_contains "ui_url=http://127.0.0.1:${WEB_PORT}/?dev=1" "$PREVIEW_OUTPUT"
assert_contains "admin_key_source=temp_runtime_only" "$PREVIEW_OUTPUT"
assert_contains "expected_assertions=dev_panel,admin_panel,tenant_tab,exports_tab,snapshot_export_tab" "$PREVIEW_OUTPUT"
assert_not_contains "Bearer " "$PREVIEW_OUTPUT"

LIVE_OUTPUT="$TMP_DIR/live.log"
DOCGEN_ADMIN_UI_SMOKE_BROWSER_IMPL=node \
DOCGEN_ADMIN_UI_SMOKE_BACKEND_PORT="$BACKEND_PORT" \
DOCGEN_ADMIN_UI_SMOKE_WEB_PORT="$WEB_PORT" \
DOCGEN_ADMIN_UI_SMOKE_BACKEND_LOG_FILE="$TMP_DIR/backend.log" \
DOCGEN_ADMIN_UI_SMOKE_WEB_LOG_FILE="$TMP_DIR/web.log" \
DOCGEN_ADMIN_UI_NODE_BIN="$TMP_DIR/mock-node" \
DOCGEN_ADMIN_UI_PLAYWRIGHT_NODE_PATH="$FIXTURE_NODE_PATH" \
DOCGEN_ADMIN_UI_BROWSER_EXECUTABLE="/bin/sh" \
bash "$SCRIPT" >"$LIVE_OUTPUT" 2>&1

assert_contains "[OK] page ready: http://127.0.0.1:${WEB_PORT}/?dev=1" "$LIVE_OUTPUT"
assert_contains "[OK] dev panel visible: 维护 / 诊断（开发）" "$LIVE_OUTPUT"
assert_contains "[OK] admin panel visible: 运营管理台（只读）" "$LIVE_OUTPUT"
assert_contains "[OK] admin refresh success: Admin Key accepted and dashboard loaded" "$LIVE_OUTPUT"
assert_contains "[OK] tenant tab ready: 当前页租户 / 计费事件 / 累计费用" "$LIVE_OUTPUT"
assert_contains "[OK] exports tab ready: 导出文件 / 已用确认票据 / 预览导出文件清理" "$LIVE_OUTPUT"
assert_contains "[OK] snapshot export tab ready: 快照导出数 / 预览快照导出清理" "$LIVE_OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$LIVE_OUTPUT"
assert_not_contains "Bearer " "$LIVE_OUTPUT"

echo "[PASS] verify_local_admin_ops_panel regression checks passed"
