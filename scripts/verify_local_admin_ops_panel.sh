#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DOCGEN_PREVIEW="${DOCGEN_PREVIEW:-0}"
HOST="${DOCGEN_ADMIN_UI_SMOKE_HOST:-127.0.0.1}"
BACKEND_PORT="${DOCGEN_ADMIN_UI_SMOKE_BACKEND_PORT:-18012}"
WEB_PORT="${DOCGEN_ADMIN_UI_SMOKE_WEB_PORT:-18512}"
RUNTIME_DIR="${DOCGEN_ADMIN_UI_SMOKE_RUNTIME_DIR:-$ROOT/.runtime/docgen}"
BACKEND_LOG_FILE="${DOCGEN_ADMIN_UI_SMOKE_BACKEND_LOG_FILE:-$RUNTIME_DIR/local-admin-ui-backend.log}"
WEB_LOG_FILE="${DOCGEN_ADMIN_UI_SMOKE_WEB_LOG_FILE:-$RUNTIME_DIR/local-admin-ui-streamlit.log}"
WAIT_TIMEOUT_SEC="${DOCGEN_ADMIN_UI_SMOKE_WAIT_TIMEOUT_SEC:-120}"
RUNNER_IMPL="${DOCGEN_ADMIN_UI_SMOKE_BROWSER_IMPL:-python}"
NODE_BIN="${DOCGEN_ADMIN_UI_NODE_BIN:-node}"
PLAYWRIGHT_MODULE="${DOCGEN_ADMIN_UI_PLAYWRIGHT_MODULE:-playwright-core}"
PLAYWRIGHT_NODE_PATH="${DOCGEN_ADMIN_UI_PLAYWRIGHT_NODE_PATH:-}"
BROWSER_EXECUTABLE="${DOCGEN_ADMIN_UI_BROWSER_EXECUTABLE:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
BROWSER_WIDTH="${DOCGEN_ADMIN_UI_BROWSER_WIDTH:-1440}"
BROWSER_HEIGHT="${DOCGEN_ADMIN_UI_BROWSER_HEIGHT:-1200}"
KEEP_BROWSER="${DOCGEN_ADMIN_UI_KEEP_BROWSER:-0}"
PYTHON_BIN="${DOCGEN_ADMIN_UI_SMOKE_PYTHON:-}"

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
BACKEND_URL="http://${HOST}:${BACKEND_PORT}"
WEB_URL="http://${HOST}:${WEB_PORT}"
UI_URL="${WEB_URL}/?dev=1"

failures=0
tmp_dir=""
runner_js=""
runner_py=""
backend_pid=""
web_pid=""

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_number() {
  local value="$1"
  local label="$2"
  [[ "$value" =~ ^[0-9]+$ ]] || fail "$label must be a non-negative integer"
}

require_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "missing required command: $name"
  fi
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

detect_playwright_node_path() {
  if [[ -n "$PLAYWRIGHT_NODE_PATH" ]]; then
    printf '%s\n' "$PLAYWRIGHT_NODE_PATH"
    return 0
  fi
  local module_dir
  module_dir="$(find "$HOME/.npm/_npx" -maxdepth 3 -type d -name "$PLAYWRIGHT_MODULE" 2>/dev/null | head -n1)"
  if [[ -n "$module_dir" ]]; then
    dirname "$module_dir"
  fi
}

python_has_playwright() {
  "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
try:
    import playwright  # noqa: F401
    from playwright.sync_api import sync_playwright  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
}

extract_result() {
  local key="$1"
  local payload="$2"
  sed -n "s/^${key}=//p" <<<"$payload" | head -n 1
}

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
  if [[ -n "$web_pid" ]] && kill -0 "$web_pid" 2>/dev/null; then
    kill "$web_pid" >/dev/null 2>&1 || true
    wait "$web_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" >/dev/null 2>&1 || true
    wait "$backend_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

wait_for_url() {
  local url="$1"
  local label="$2"
  local timeout="$3"
  local started_at
  started_at="$(date +%s)"
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    if (( "$(date +%s)" - started_at >= timeout )); then
      fail "${label} did not become ready within ${timeout}s"
    fi
    sleep 0.5
  done
}

require_number "$BACKEND_PORT" "DOCGEN_ADMIN_UI_SMOKE_BACKEND_PORT"
require_number "$WEB_PORT" "DOCGEN_ADMIN_UI_SMOKE_WEB_PORT"
require_number "$WAIT_TIMEOUT_SEC" "DOCGEN_ADMIN_UI_SMOKE_WAIT_TIMEOUT_SEC"
require_number "$BROWSER_WIDTH" "DOCGEN_ADMIN_UI_BROWSER_WIDTH"
require_number "$BROWSER_HEIGHT" "DOCGEN_ADMIN_UI_BROWSER_HEIGHT"

if [[ ! -x "$BROWSER_EXECUTABLE" ]]; then
  fail "browser executable not found: ${BROWSER_EXECUTABLE}"
fi

if [[ "$RUNNER_IMPL" = "node" ]]; then
  require_cmd "$NODE_BIN"
  PLAYWRIGHT_NODE_PATH="$(detect_playwright_node_path)"
  if [[ -z "$PLAYWRIGHT_NODE_PATH" || ! -d "$PLAYWRIGHT_NODE_PATH" ]]; then
    fail "playwright module path not found for ${PLAYWRIGHT_MODULE}"
  fi
elif [[ "$RUNNER_IMPL" = "python" ]]; then
  python_has_playwright || fail "python playwright is not available for ${PYTHON_BIN}"
else
  fail "DOCGEN_ADMIN_UI_SMOKE_BROWSER_IMPL must be 'python' or 'node'"
fi

BACKEND_START_CMD=(
  "$PYTHON_BIN" -m uvicorn backend.app.main:app
  --host "$HOST"
  --port "$BACKEND_PORT"
)
WEB_START_CMD=(
  "$PYTHON_BIN" -m streamlit run "$ROOT/app.py"
  --server.headless true
  --server.address "$HOST"
  --server.port "$WEB_PORT"
  --browser.gatherUsageStats false
)

if [[ "$DOCGEN_PREVIEW" = "1" ]]; then
  printf 'root=%s\n' "$ROOT"
  printf 'host=%s\n' "$HOST"
  printf 'backend_port=%s\n' "$BACKEND_PORT"
  printf 'web_port=%s\n' "$WEB_PORT"
  printf 'backend_url=%s\n' "$BACKEND_URL"
  printf 'web_url=%s\n' "$WEB_URL"
  printf 'ui_url=%s\n' "$UI_URL"
  printf 'python_bin=%s\n' "$PYTHON_BIN"
  printf 'runtime_dir=%s\n' "$RUNTIME_DIR"
  printf 'backend_log_file=%s\n' "$BACKEND_LOG_FILE"
  printf 'web_log_file=%s\n' "$WEB_LOG_FILE"
  printf 'wait_timeout_sec=%s\n' "$WAIT_TIMEOUT_SEC"
  printf 'browser_impl=%s\n' "$RUNNER_IMPL"
  printf 'admin_key_source=temp_runtime_only\n'
  if [[ "$RUNNER_IMPL" = "node" ]]; then
    printf 'playwright_module=%s\n' "$PLAYWRIGHT_MODULE"
    printf 'playwright_node_path=%s\n' "$PLAYWRIGHT_NODE_PATH"
  fi
  printf 'browser_executable=%s\n' "$BROWSER_EXECUTABLE"
  printf 'backend_start_command=%s\n' "$(format_command "${BACKEND_START_CMD[@]}")"
  printf 'web_start_command=%s\n' "$(format_command "${WEB_START_CMD[@]}")"
  printf 'expected_assertions=%s\n' 'dev_panel,admin_panel,tenant_tab,exports_tab,snapshot_export_tab'
  exit 0
fi

[[ -z "$(port_owner_pid "$BACKEND_PORT")" ]] || fail "backend port ${BACKEND_PORT} already in use"
[[ -z "$(port_owner_pid "$WEB_PORT")" ]] || fail "web port ${WEB_PORT} already in use"

mkdir -p "$RUNTIME_DIR"
tmp_dir="$(mktemp -d)"
runner_js="$tmp_dir/admin_ops_panel_smoke.cjs"
runner_py="$tmp_dir/admin_ops_panel_smoke.py"

ADMIN_KEY="$("$PYTHON_BIN" - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"

cat >"$runner_js" <<'EOF'
const { chromium } = require(process.env.DOCGEN_ADMIN_UI_PLAYWRIGHT_MODULE || 'playwright-core');

function emit(key, value) {
  const normalized = String(value).replace(/\r?\n/g, ' | ');
  console.log(`${key}=${normalized}`);
}

async function waitForBodyText(page, text, timeout) {
  await page.waitForFunction(
    expected => (document.body.innerText || '').includes(expected),
    text,
    { timeout }
  );
}

async function clickVisible(page, label, timeout) {
  const candidates = [
    page.locator('summary').filter({ hasText: label }),
    page.locator('button').filter({ hasText: label }),
    page.getByRole('button', { name: label, exact: true }),
    page.getByRole('tab', { name: label, exact: true }),
    page.getByText(label, { exact: true }),
  ];
  for (const locator of candidates) {
    const count = await locator.count().catch(() => 0);
    if (count > 0) {
      await locator.first().click({ timeout });
      return;
    }
  }
  throw new Error(`click target not found: ${label}`);
}

(async () => {
  const waitMs = Number(process.env.DOCGEN_ADMIN_UI_WAIT_TIMEOUT_MS || '120000');
  const width = Number(process.env.DOCGEN_ADMIN_UI_BROWSER_WIDTH || '1440');
  const height = Number(process.env.DOCGEN_ADMIN_UI_BROWSER_HEIGHT || '1200');
  const keepBrowser = process.env.DOCGEN_ADMIN_UI_KEEP_BROWSER === '1';
  const result = {
    pageReady: false,
    devPanelVisible: false,
    adminPanelVisible: false,
    adminRefreshSuccess: false,
    tenantTabReady: false,
    exportsTabReady: false,
    snapshotExportTabReady: false,
    error: 'none',
  };

  let browser;
  try {
    browser = await chromium.launch({
      headless: !keepBrowser,
      executablePath: process.env.DOCGEN_ADMIN_UI_BROWSER_EXECUTABLE,
      args: [`--window-size=${width},${height}`],
    });
    const page = await browser.newPage({ viewport: { width, height } });

    await page.goto(process.env.DOCGEN_ADMIN_UI_URL, {
      waitUntil: 'domcontentloaded',
      timeout: waitMs,
    });
    await waitForBodyText(page, '维护 / 诊断（开发）', waitMs);
    result.pageReady = true;

    await clickVisible(page, '维护 / 诊断（开发）', waitMs);
    await waitForBodyText(page, '运营管理台（只读）', waitMs);
    result.devPanelVisible = true;

    await clickVisible(page, '运营管理台（只读）', waitMs);
    await waitForBodyText(page, 'Admin Key', waitMs);
    result.adminPanelVisible = true;

    await page.getByLabel('Admin Key').fill(process.env.DOCGEN_ADMIN_UI_KEY);
    await page.getByRole('button', { name: '刷新管理台', exact: true }).click({ timeout: waitMs });

    await waitForBodyText(page, '当前页租户', waitMs);
    await waitForBodyText(page, '计费事件', waitMs);
    await waitForBodyText(page, '累计费用', waitMs);
    result.adminRefreshSuccess = true;
    result.tenantTabReady = true;

    await clickVisible(page, '导出资产', waitMs);
    await waitForBodyText(page, '导出文件', waitMs);
    await waitForBodyText(page, '已用确认票据', waitMs);
    await waitForBodyText(page, '预览导出文件清理', waitMs);
    result.exportsTabReady = true;

    await clickVisible(page, '快照导出', waitMs);
    await waitForBodyText(page, '快照导出数', waitMs);
    await waitForBodyText(page, '预览快照导出清理', waitMs);
    result.snapshotExportTabReady = true;

    if (keepBrowser) {
      await page.waitForTimeout(3600000);
    }
  } catch (error) {
    result.error = String(error && (error.stack || error.message) || error);
  } finally {
    emit('UI_PAGE_READY', result.pageReady ? 1 : 0);
    emit('UI_DEV_PANEL_VISIBLE', result.devPanelVisible ? 1 : 0);
    emit('UI_ADMIN_PANEL_VISIBLE', result.adminPanelVisible ? 1 : 0);
    emit('UI_ADMIN_REFRESH_SUCCESS', result.adminRefreshSuccess ? 1 : 0);
    emit('UI_TENANT_TAB_READY', result.tenantTabReady ? 1 : 0);
    emit('UI_EXPORTS_TAB_READY', result.exportsTabReady ? 1 : 0);
    emit('UI_SNAPSHOT_EXPORT_TAB_READY', result.snapshotExportTabReady ? 1 : 0);
    emit('UI_ERROR', result.error);
    if (browser && !keepBrowser) {
      await browser.close().catch(() => {});
    }
    process.exit(0);
  }
})();
EOF

cat >"$runner_py" <<'EOF'
#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from playwright.sync_api import sync_playwright


def emit(key: str, value: object) -> None:
    normalized = str(value).replace("\r\n", " | ").replace("\n", " | ")
    print(f"{key}={normalized}", flush=True)


def wait_for_body_text(page, text: str, timeout_ms: int) -> None:
    page.wait_for_function(
        "(expected) => (document.body.innerText || '').includes(expected)",
        arg=text,
        timeout=timeout_ms,
    )


def click_summary(page, label: str, timeout_ms: int) -> None:
    page.locator("summary").filter(has_text=label).first.click(timeout=timeout_ms)


def click_button(page, label: str, timeout_ms: int) -> None:
    page.locator("button").filter(has_text=label).first.click(timeout=timeout_ms)


def main() -> None:
    wait_ms = int(os.environ.get("DOCGEN_ADMIN_UI_WAIT_TIMEOUT_MS", "120000"))
    width = int(os.environ.get("DOCGEN_ADMIN_UI_BROWSER_WIDTH", "1440"))
    height = int(os.environ.get("DOCGEN_ADMIN_UI_BROWSER_HEIGHT", "1200"))
    keep_browser = os.environ.get("DOCGEN_ADMIN_UI_KEEP_BROWSER", "0") == "1"
    browser_executable = os.environ["DOCGEN_ADMIN_UI_BROWSER_EXECUTABLE"]
    ui_url = os.environ["DOCGEN_ADMIN_UI_URL"]
    admin_key = os.environ["DOCGEN_ADMIN_UI_KEY"]

    page_ready = False
    dev_panel_visible = False
    admin_panel_visible = False
    admin_refresh_success = False
    tenant_tab_ready = False
    exports_tab_ready = False
    snapshot_export_tab_ready = False
    error = "none"
    browser = None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=not keep_browser,
                executable_path=browser_executable,
                args=[f"--window-size={width},{height}"],
            )
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(ui_url, wait_until="domcontentloaded", timeout=wait_ms)
            wait_for_body_text(page, "维护 / 诊断（开发）", wait_ms)
            page_ready = True

            click_summary(page, "维护 / 诊断（开发）", wait_ms)
            wait_for_body_text(page, "运营管理台（只读）", wait_ms)
            dev_panel_visible = True

            click_summary(page, "运营管理台（只读）", wait_ms)
            wait_for_body_text(page, "Admin Key", wait_ms)
            admin_panel_visible = True

            page.get_by_label("Admin Key").fill(admin_key, timeout=wait_ms)
            click_button(page, "刷新管理台", wait_ms)
            wait_for_body_text(page, "当前页租户", wait_ms)
            wait_for_body_text(page, "计费事件", wait_ms)
            wait_for_body_text(page, "累计费用", wait_ms)
            admin_refresh_success = True
            tenant_tab_ready = True

            click_button(page, "导出资产", wait_ms)
            wait_for_body_text(page, "导出文件", wait_ms)
            wait_for_body_text(page, "已用确认票据", wait_ms)
            wait_for_body_text(page, "预览导出文件清理", wait_ms)
            exports_tab_ready = True

            click_button(page, "快照导出", wait_ms)
            wait_for_body_text(page, "快照导出数", wait_ms)
            wait_for_body_text(page, "预览快照导出清理", wait_ms)
            snapshot_export_tab_ready = True

            if keep_browser:
                page.wait_for_timeout(3600000)
            browser.close()
            browser = None
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    finally:
        emit("UI_PAGE_READY", 1 if page_ready else 0)
        emit("UI_DEV_PANEL_VISIBLE", 1 if dev_panel_visible else 0)
        emit("UI_ADMIN_PANEL_VISIBLE", 1 if admin_panel_visible else 0)
        emit("UI_ADMIN_REFRESH_SUCCESS", 1 if admin_refresh_success else 0)
        emit("UI_TENANT_TAB_READY", 1 if tenant_tab_ready else 0)
        emit("UI_EXPORTS_TAB_READY", 1 if exports_tab_ready else 0)
        emit("UI_SNAPSHOT_EXPORT_TAB_READY", 1 if snapshot_export_tab_ready else 0)
        emit("UI_ERROR", error)
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    main()
EOF

(
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
  export ZF_ADMIN_KEY="$ADMIN_KEY"
  export ZF_DISABLE_PREWARM=1
  "${BACKEND_START_CMD[@]}" >"$BACKEND_LOG_FILE" 2>&1
) &
backend_pid=$!

wait_for_url "${BACKEND_URL}/health" "temporary backend" "$WAIT_TIMEOUT_SEC"

(
  export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
  export ZF_BACKEND_BASE_URL="$BACKEND_URL"
  export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
  export ZF_SHOW_DEV_PANELS=1
  export ZF_DISABLE_PREWARM=1
  "${WEB_START_CMD[@]}" >"$WEB_LOG_FILE" 2>&1
) &
web_pid=$!

wait_for_url "${WEB_URL}/_stcore/health" "temporary streamlit" "$WAIT_TIMEOUT_SEC"

echo "[INFO] backend_url=$BACKEND_URL"
echo "[INFO] web_url=$WEB_URL"
echo "[INFO] ui_url=$UI_URL"
echo "[INFO] backend_log_file=$BACKEND_LOG_FILE"
echo "[INFO] web_log_file=$WEB_LOG_FILE"
echo "[INFO] 注意：该脚本只验证开发态只读管理台的浏览器成功路径，不触发任何 execute/delete。"

if [[ "$RUNNER_IMPL" = "node" ]]; then
  RUN_OUTPUT="$(
    DOCGEN_ADMIN_UI_PLAYWRIGHT_MODULE="$PLAYWRIGHT_MODULE" \
    NODE_PATH="$PLAYWRIGHT_NODE_PATH" \
    DOCGEN_ADMIN_UI_BROWSER_EXECUTABLE="$BROWSER_EXECUTABLE" \
    DOCGEN_ADMIN_UI_BROWSER_WIDTH="$BROWSER_WIDTH" \
    DOCGEN_ADMIN_UI_BROWSER_HEIGHT="$BROWSER_HEIGHT" \
    DOCGEN_ADMIN_UI_WAIT_TIMEOUT_MS="$((WAIT_TIMEOUT_SEC * 1000))" \
    DOCGEN_ADMIN_UI_KEEP_BROWSER="$KEEP_BROWSER" \
    DOCGEN_ADMIN_UI_URL="$UI_URL" \
    DOCGEN_ADMIN_UI_KEY="$ADMIN_KEY" \
    "$NODE_BIN" "$runner_js"
  )"
else
  RUN_OUTPUT="$(
    DOCGEN_ADMIN_UI_BROWSER_EXECUTABLE="$BROWSER_EXECUTABLE" \
    DOCGEN_ADMIN_UI_BROWSER_WIDTH="$BROWSER_WIDTH" \
    DOCGEN_ADMIN_UI_BROWSER_HEIGHT="$BROWSER_HEIGHT" \
    DOCGEN_ADMIN_UI_WAIT_TIMEOUT_MS="$((WAIT_TIMEOUT_SEC * 1000))" \
    DOCGEN_ADMIN_UI_KEEP_BROWSER="$KEEP_BROWSER" \
    DOCGEN_ADMIN_UI_URL="$UI_URL" \
    DOCGEN_ADMIN_UI_KEY="$ADMIN_KEY" \
    "$PYTHON_BIN" "$runner_py"
  )"
fi

page_ready="$(extract_result "UI_PAGE_READY" "$RUN_OUTPUT")"
dev_panel_visible="$(extract_result "UI_DEV_PANEL_VISIBLE" "$RUN_OUTPUT")"
admin_panel_visible="$(extract_result "UI_ADMIN_PANEL_VISIBLE" "$RUN_OUTPUT")"
admin_refresh_success="$(extract_result "UI_ADMIN_REFRESH_SUCCESS" "$RUN_OUTPUT")"
tenant_tab_ready="$(extract_result "UI_TENANT_TAB_READY" "$RUN_OUTPUT")"
exports_tab_ready="$(extract_result "UI_EXPORTS_TAB_READY" "$RUN_OUTPUT")"
snapshot_export_tab_ready="$(extract_result "UI_SNAPSHOT_EXPORT_TAB_READY" "$RUN_OUTPUT")"
ui_error="$(extract_result "UI_ERROR" "$RUN_OUTPUT")"

print_status "page ready" "$page_ready" "$UI_URL"
print_status "dev panel visible" "$dev_panel_visible" "维护 / 诊断（开发）"
print_status "admin panel visible" "$admin_panel_visible" "运营管理台（只读）"
print_status "admin refresh success" "$admin_refresh_success" "Admin Key accepted and dashboard loaded"
print_status "tenant tab ready" "$tenant_tab_ready" "当前页租户 / 计费事件 / 累计费用"
print_status "exports tab ready" "$exports_tab_ready" "导出文件 / 已用确认票据 / 预览导出文件清理"
print_status "snapshot export tab ready" "$snapshot_export_tab_ready" "快照导出数 / 预览快照导出清理"

if [[ "${ui_error:-none}" != "none" ]]; then
  print_status "playwright error" "0" "$ui_error"
fi

if (( failures > 0 )); then
  echo "[SUMMARY] ${failures} check(s) failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
