#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${DOCGEN_UI_BASE_URL:-http://127.0.0.1:8501}"
FIXTURE_DIR="${DOCGEN_UI_FIXTURE_DIR:-$ROOT/output/playwright/ui-fixtures}"
PYTHON_BIN="${DOCGEN_UI_PYTHON:-python3}"
NODE_BIN="${DOCGEN_UI_NODE_BIN:-node}"
RUNNER_IMPL="${DOCGEN_UI_BROWSER_IMPL:-auto}"
PLAYWRIGHT_MODULE="${DOCGEN_UI_PLAYWRIGHT_MODULE:-playwright-core}"
PLAYWRIGHT_NODE_PATH="${DOCGEN_UI_PLAYWRIGHT_NODE_PATH:-}"
BROWSER_EXECUTABLE="${DOCGEN_UI_BROWSER_EXECUTABLE:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
WAIT_TIMEOUT_MS="${DOCGEN_UI_WAIT_TIMEOUT_MS:-60000}"
BROWSER_WIDTH="${DOCGEN_UI_BROWSER_WIDTH:-1440}"
BROWSER_HEIGHT="${DOCGEN_UI_BROWSER_HEIGHT:-1200}"
KEEP_BROWSER="${DOCGEN_UI_KEEP_BROWSER:-0}"
RUN_ATTEMPTS="${DOCGEN_UI_RUN_ATTEMPTS:-2}"
RETRY_SLEEP_SECONDS="${DOCGEN_UI_RETRY_SLEEP_SECONDS:-1}"

TENDER_FILE="$FIXTURE_DIR/tender.docx"
BOQ_FILE="$FIXTURE_DIR/boq.xlsx"

failures=0
tmp_dir=""

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
  if [[ -n "$tmp_dir" && -d "$tmp_dir" ]]; then
    rm -rf "$tmp_dir"
  fi
}
trap cleanup EXIT

require_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "[ERROR] missing required command: $name" >&2
    exit 1
  fi
}

normalize_positive_int() {
  local raw="$1"
  local fallback="$2"
  if [[ "$raw" =~ ^[0-9]+$ ]] && (( raw > 0 )); then
    printf '%s\n' "$raw"
  else
    printf '%s\n' "$fallback"
  fi
}

cleanup_playwright_runtime() {
  pkill -f 'playwright_chromiumdev_profile' >/dev/null 2>&1 || true
  pkill -f 'Google Chrome.app/Contents/MacOS/Google Chrome.*remote-debugging-pipe' >/dev/null 2>&1 || true
}

should_retry_browser_output() {
  local output="$1"
  grep -Eq 'BrowserType\.launch: Target page, context or browser has been closed|TargetClosedError|signal=SIGKILL|exception while trying to kill process: Error: kill EPERM' <<<"$output"
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

ensure_fixtures() {
  if [[ -f "$TENDER_FILE" && -f "$BOQ_FILE" ]]; then
    return 0
  fi

  mkdir -p "$FIXTURE_DIR"
  DOCGEN_UI_FIXTURE_DIR="$FIXTURE_DIR" "$PYTHON_BIN" - <<'PY'
from pathlib import Path
import os

from docx import Document
from openpyxl import Workbook

root = Path(os.environ["DOCGEN_UI_FIXTURE_DIR"])
root.mkdir(parents=True, exist_ok=True)

doc = Document()
doc.add_paragraph("UI smoke tender")
doc.add_paragraph("技术文件详细评审标准")
doc.add_paragraph("1）工程概况")
doc.add_paragraph("2）施工部署")
doc.save(root / "tender.docx")

wb = Workbook()
ws = wb.active
ws.title = "BOQ"
ws.append(["item", "qty"])
ws.append(["concrete", 1])
wb.save(root / "boq.xlsx")
PY
}

detect_playwright_node_path() {
  if [[ -n "$PLAYWRIGHT_NODE_PATH" ]]; then
    printf '%s\n' "$PLAYWRIGHT_NODE_PATH"
    return 0
  fi

  local module_dir
  module_dir="$(find "$HOME/.npm/_npx" -maxdepth 3 -type d -name "$PLAYWRIGHT_MODULE" 2>/dev/null | head -n 1)"
  if [[ -n "$module_dir" ]]; then
    dirname "$module_dir"
  fi
}

extract_result() {
  local key="$1"
  local payload="$2"
  sed -n "s/^${key}=//p" <<<"$payload" | head -n 1
}

require_cmd "$PYTHON_BIN"

RESOLVED_RUNNER_IMPL="$RUNNER_IMPL"
if [[ "$RESOLVED_RUNNER_IMPL" = "auto" ]]; then
  if python_has_playwright; then
    RESOLVED_RUNNER_IMPL="python"
  else
    RESOLVED_RUNNER_IMPL="node"
  fi
fi

if [[ "$RESOLVED_RUNNER_IMPL" = "node" ]]; then
  require_cmd "$NODE_BIN"
elif [[ "$RESOLVED_RUNNER_IMPL" != "python" ]]; then
  echo "[ERROR] DOCGEN_UI_BROWSER_IMPL must be auto, python, or node" >&2
  exit 1
fi

ensure_fixtures
tmp_dir="$(mktemp -d)"
runner_js="$tmp_dir/ui_upload_outline_smoke.cjs"
runner_py="$tmp_dir/ui_upload_outline_smoke.py"
RUN_ATTEMPTS="$(normalize_positive_int "$RUN_ATTEMPTS" 2)"

if [[ "$RESOLVED_RUNNER_IMPL" = "node" ]]; then
  PLAYWRIGHT_NODE_PATH="$(detect_playwright_node_path)"
  if [[ -z "$PLAYWRIGHT_NODE_PATH" || ! -d "$PLAYWRIGHT_NODE_PATH" ]]; then
    echo "[ERROR] playwright module path not found for $PLAYWRIGHT_MODULE" >&2
    exit 1
  fi
elif ! python_has_playwright; then
  echo "[ERROR] python playwright is not available for $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -x "$BROWSER_EXECUTABLE" ]]; then
  echo "[ERROR] browser executable not found: $BROWSER_EXECUTABLE" >&2
  exit 1
fi

cat >"$runner_js" <<'EOF'
const { chromium } = require(process.env.DOCGEN_UI_PLAYWRIGHT_MODULE || 'playwright-core');

function emit(key, value) {
  const normalized = String(value).replace(/\r?\n/g, ' | ');
  console.log(`${key}=${normalized}`);
}

async function findUploadInputs(page, wait) {
  const deadline = Date.now() + wait;
  while (Date.now() < deadline) {
    for (const frame of page.frames()) {
      const inputs = frame.locator('input[type="file"]');
      const count = await inputs.count().catch(() => 0);
      if (count >= 2) {
        return inputs;
      }
    }
    await page.waitForTimeout(500);
  }
  return null;
}

(async () => {
  const wait = Number(process.env.DOCGEN_UI_WAIT_TIMEOUT_MS || '60000');
  const width = Number(process.env.DOCGEN_UI_BROWSER_WIDTH || '1440');
  const height = Number(process.env.DOCGEN_UI_BROWSER_HEIGHT || '1200');
  const keepBrowser = process.env.DOCGEN_UI_KEEP_BROWSER === '1';
  const responses = [];
  const result = {
    pageReady: false,
    selectedFiles: false,
    outlineLoaded: false,
    streamlitUploadRequest: false,
    upload204Matches: 0,
    error: 'none',
  };

  let browser;
  try {
    browser = await chromium.launch({
      headless: !keepBrowser,
      executablePath: process.env.DOCGEN_UI_BROWSER_EXECUTABLE,
      args: [`--window-size=${width},${height}`],
    });
    const page = await browser.newPage({ viewport: { width, height } });
    page.on('response', response => {
      responses.push({
        url: response.url(),
        status: response.status(),
        method: response.request().method(),
      });
    });

    await page.goto(process.env.DOCGEN_UI_BASE_URL, {
      waitUntil: 'domcontentloaded',
      timeout: wait,
    });
    await page.waitForFunction(
      () => (document.body.innerText || '').includes('01 资料上传'),
      null,
      { timeout: wait }
    );
    result.pageReady = true;

    const inputs = await findUploadInputs(page, wait);
    if (!inputs) {
      throw new Error('expected at least 2 file inputs, got 0');
    }

    await inputs.nth(0).setInputFiles(process.env.DOCGEN_UI_TENDER_FILE);
    await inputs.nth(1).setInputFiles(process.env.DOCGEN_UI_BOQ_FILE);

    await page.waitForFunction(
      () => (document.body.innerText || '').includes('已选文件：招标/答疑 1 · 清单 1'),
      null,
      { timeout: wait }
    );
    result.selectedFiles = true;

    await page.getByRole('button', { name: '从评审标准载入目录' }).click();
    await page.waitForFunction(
      () => {
        const text = document.body.innerText || '';
        return text.includes('第1章') && !text.includes('目录为空。可先点击“从评审标准载入目录”，或手动新增章节。');
      },
      null,
      { timeout: wait }
    );
    result.outlineLoaded = true;

    const uploadMatches = responses.filter(entry =>
      entry.method === 'PUT' &&
      entry.status === 204 &&
      entry.url.includes('/_stcore/upload_file/')
    );
    result.upload204Matches = uploadMatches.length;
    result.streamlitUploadRequest = uploadMatches.length >= 2;

    if (keepBrowser) {
      await page.waitForTimeout(3600000);
    }
  } catch (error) {
    result.error = String(error && (error.stack || error.message) || error);
  } finally {
    emit('UI_PAGE_READY', result.pageReady ? 1 : 0);
    emit('UI_SELECTED_FILES', result.selectedFiles ? 1 : 0);
    emit('UI_OUTLINE_LOADED', result.outlineLoaded ? 1 : 0);
    emit('UI_STREAMLIT_UPLOAD', result.streamlitUploadRequest ? 1 : 0);
    emit('UI_UPLOAD_204_MATCHES', result.upload204Matches);
    emit('UI_ERROR', result.error);
    if (browser && !keepBrowser) {
      await browser.close().catch(() => {});
    }
  }
})();
EOF

cat >"$runner_py" <<'EOF'
#!/usr/bin/env python3
from __future__ import annotations

import os
from playwright.sync_api import sync_playwright


def emit(key: str, value: object) -> None:
    normalized = str(value).replace("\r\n", " | ").replace("\n", " | ")
    print(f"{key}={normalized}", flush=True)


def find_upload_inputs(page, timeout_ms: int):
    deadline = page.context.browser
    for _ in range(max(1, timeout_ms // 500)):
        for frame in page.frames:
            inputs = frame.locator('input[type="file"]')
            try:
                count = inputs.count()
            except Exception:  # noqa: BLE001
                count = 0
            if count >= 2:
                return inputs
        page.wait_for_timeout(500)
    return None


def main() -> None:
    wait_ms = int(os.environ.get("DOCGEN_UI_WAIT_TIMEOUT_MS", "60000"))
    width = int(os.environ.get("DOCGEN_UI_BROWSER_WIDTH", "1440"))
    height = int(os.environ.get("DOCGEN_UI_BROWSER_HEIGHT", "1200"))
    keep_browser = os.environ.get("DOCGEN_UI_KEEP_BROWSER", "0") == "1"
    browser_executable = os.environ["DOCGEN_UI_BROWSER_EXECUTABLE"]
    base_url = os.environ["DOCGEN_UI_BASE_URL"]
    tender_file = os.environ["DOCGEN_UI_TENDER_FILE"]
    boq_file = os.environ["DOCGEN_UI_BOQ_FILE"]

    page_ready = False
    selected_files = False
    outline_loaded = False
    streamlit_upload_request = False
    upload_204_matches = 0
    error = "none"
    browser = None
    responses = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=not keep_browser,
                executable_path=browser_executable,
                args=[f"--window-size={width},{height}"],
            )
            page = browser.new_page(viewport={"width": width, "height": height})

            page.on(
                "response",
                lambda response: responses.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "method": response.request.method,
                    }
                ),
            )

            page.goto(base_url, wait_until="domcontentloaded", timeout=wait_ms)
            page.wait_for_function(
                "() => (document.body.innerText || '').includes('01 资料上传')",
                timeout=wait_ms,
            )
            page_ready = True

            inputs = find_upload_inputs(page, wait_ms)
            if inputs is None:
                raise RuntimeError("expected at least 2 file inputs, got 0")

            inputs.nth(0).set_input_files(tender_file)
            inputs.nth(1).set_input_files(boq_file)
            page.wait_for_function(
                "() => (document.body.innerText || '').includes('已选文件：招标/答疑 1 · 清单 1')",
                timeout=wait_ms,
            )
            selected_files = True

            page.get_by_role("button", name="从评审标准载入目录").click(timeout=wait_ms)
            page.wait_for_function(
                "() => { const text = document.body.innerText || ''; return text.includes('第1章') && !text.includes('目录为空。可先点击“从评审标准载入目录”，或手动新增章节。'); }",
                timeout=wait_ms,
            )
            outline_loaded = True

            upload_matches = [
                entry
                for entry in responses
                if entry["method"] == "PUT"
                and entry["status"] == 204
                and "/_stcore/upload_file/" in entry["url"]
            ]
            upload_204_matches = len(upload_matches)
            streamlit_upload_request = upload_204_matches >= 2

            if keep_browser:
                page.wait_for_timeout(3600000)
            browser.close()
            browser = None
    except Exception as exc:  # noqa: BLE001
        error = str(exc)
    finally:
        emit("UI_PAGE_READY", 1 if page_ready else 0)
        emit("UI_SELECTED_FILES", 1 if selected_files else 0)
        emit("UI_OUTLINE_LOADED", 1 if outline_loaded else 0)
        emit("UI_STREAMLIT_UPLOAD", 1 if streamlit_upload_request else 0)
        emit("UI_UPLOAD_204_MATCHES", upload_204_matches)
        emit("UI_ERROR", error)
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass


if __name__ == "__main__":
    main()
EOF

echo "[INFO] ui_base_url=$BASE_URL"
echo "[INFO] fixture_dir=$FIXTURE_DIR"
echo "[INFO] browser_impl=$RESOLVED_RUNNER_IMPL"
if [[ "$RESOLVED_RUNNER_IMPL" = "node" ]]; then
  echo "[INFO] playwright_module=$PLAYWRIGHT_MODULE"
  echo "[INFO] playwright_node_path=$PLAYWRIGHT_NODE_PATH"
fi
echo "[INFO] browser_executable=$BROWSER_EXECUTABLE"
echo "[INFO] keep_browser=$KEEP_BROWSER"
echo "[INFO] 注意：该脚本只验证浏览器端“文件选择 -> 目录载入”前半链路，不触发真实生成。"

if [[ -f "$TENDER_FILE" ]]; then
  print_status "fixture tender.docx" "1" "$TENDER_FILE"
else
  print_status "fixture tender.docx" "0" "$TENDER_FILE missing"
fi
if [[ -f "$BOQ_FILE" ]]; then
  print_status "fixture boq.xlsx" "1" "$BOQ_FILE"
else
  print_status "fixture boq.xlsx" "0" "$BOQ_FILE missing"
fi

node_output=""
page_ready=""
selected_files=""
outline_loaded=""
streamlit_upload=""
upload_matches=""
ui_error=""
attempt=1

while true; do
  runner_output_file="$tmp_dir/browser-runner-output.txt"
  runner_status=0
  if [[ "$RESOLVED_RUNNER_IMPL" = "node" ]]; then
    set +e
    NODE_PATH="$PLAYWRIGHT_NODE_PATH" \
    DOCGEN_UI_PLAYWRIGHT_MODULE="$PLAYWRIGHT_MODULE" \
    DOCGEN_UI_BROWSER_EXECUTABLE="$BROWSER_EXECUTABLE" \
    DOCGEN_UI_BASE_URL="$BASE_URL" \
    DOCGEN_UI_WAIT_TIMEOUT_MS="$WAIT_TIMEOUT_MS" \
    DOCGEN_UI_BROWSER_WIDTH="$BROWSER_WIDTH" \
    DOCGEN_UI_BROWSER_HEIGHT="$BROWSER_HEIGHT" \
    DOCGEN_UI_KEEP_BROWSER="$KEEP_BROWSER" \
    DOCGEN_UI_TENDER_FILE="$TENDER_FILE" \
    DOCGEN_UI_BOQ_FILE="$BOQ_FILE" \
    "$NODE_BIN" "$runner_js" >"$runner_output_file" 2>&1
    runner_status=$?
    set -e
  else
    set +e
    DOCGEN_UI_BROWSER_EXECUTABLE="$BROWSER_EXECUTABLE" \
    DOCGEN_UI_BASE_URL="$BASE_URL" \
    DOCGEN_UI_WAIT_TIMEOUT_MS="$WAIT_TIMEOUT_MS" \
    DOCGEN_UI_BROWSER_WIDTH="$BROWSER_WIDTH" \
    DOCGEN_UI_BROWSER_HEIGHT="$BROWSER_HEIGHT" \
    DOCGEN_UI_KEEP_BROWSER="$KEEP_BROWSER" \
    DOCGEN_UI_TENDER_FILE="$TENDER_FILE" \
    DOCGEN_UI_BOQ_FILE="$BOQ_FILE" \
    "$PYTHON_BIN" "$runner_py" >"$runner_output_file" 2>&1
    runner_status=$?
    set -e
  fi

  node_output="$(cat "$runner_output_file")"
  page_ready="$(extract_result "UI_PAGE_READY" "$node_output")"
  selected_files="$(extract_result "UI_SELECTED_FILES" "$node_output")"
  outline_loaded="$(extract_result "UI_OUTLINE_LOADED" "$node_output")"
  streamlit_upload="$(extract_result "UI_STREAMLIT_UPLOAD" "$node_output")"
  upload_matches="$(extract_result "UI_UPLOAD_204_MATCHES" "$node_output")"
  ui_error="$(extract_result "UI_ERROR" "$node_output")"

  if [[ "${page_ready:-0}" = "1" && "${selected_files:-0}" = "1" && "${outline_loaded:-0}" = "1" && "${streamlit_upload:-0}" = "1" ]]; then
    break
  fi

  if (( attempt >= RUN_ATTEMPTS )) || ! should_retry_browser_output "${ui_error:-$node_output}"; then
    break
  fi

  echo "[WARN] browser smoke attempt ${attempt} failed with transient browser shutdown, retrying after cleanup..."
  cleanup_playwright_runtime
  sleep "$RETRY_SLEEP_SECONDS"
  attempt=$((attempt + 1))
done

echo "[INFO] browser_attempts=$attempt/$RUN_ATTEMPTS"

if [[ "${page_ready:-0}" = "1" ]]; then
  print_status "page ready" "1" "$BASE_URL"
else
  print_status "page ready" "0" "${ui_error:-page did not finish loading}"
fi

if [[ "${selected_files:-0}" = "1" ]]; then
  print_status "selected files" "1" "招标/答疑 1 · 清单 1"
else
  print_status "selected files" "0" "${ui_error:-summary missing in page text}"
fi

if [[ "${outline_loaded:-0}" = "1" ]]; then
  print_status "outline loaded" "1" "outline entries rendered"
else
  print_status "outline loaded" "0" "${ui_error:-outline still empty}"
fi

if [[ "${streamlit_upload:-0}" = "1" ]]; then
  print_status "streamlit upload request" "1" "PUT /_stcore/upload_file => 204 x${upload_matches:-0}"
else
  print_status "streamlit upload request" "0" "${ui_error:-missing upload_file 204 in network log}"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
