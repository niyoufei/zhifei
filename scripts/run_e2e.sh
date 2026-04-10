#!/usr/bin/env bash
# 一键端到端验证脚本 - 无人工交互
# DoD: 无交互即可跑通一次端到端流程，产出 build/ 下结构化中间产物（JSON）+ DOCX
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

LOG_FILE="build/clawdbot/audit.log"
mkdir -p build/clawdbot

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

cleanup() {
    log "Cleaning up..."
    if [ "${SERVER_STARTED:-false}" = "true" ] && [ -n "${SERVER_PID:-}" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

log "=== E2E Test Start ==="
log "Working directory: $ROOT_DIR"

# 1) Check Python
if ! command -v python3 &>/dev/null; then
    log "[FAIL] python3 not found"
    exit 1
fi
log "[OK] Python: $(python3 --version)"

# 2) Check dependencies (quick import test)
log "Checking key dependencies..."
python3 -c "import fastapi, uvicorn, docx; print('Dependencies OK')" 2>&1 | tee -a "$LOG_FILE"
if [ "${PIPESTATUS[0]}" -ne 0 ]; then
    log "[WARN] Missing dependencies, attempting install..."
    pip3 install -r requirements.txt --quiet
fi

# 3) Start server in background (or reuse existing healthy server)
SERVER_STARTED=false
export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"
if curl -s http://127.0.0.1:8010/health >/dev/null 2>&1; then
    log "[OK] Existing FastAPI server detected on 8010, reuse."
else
    log "Starting FastAPI server..."
    python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 &
    SERVER_PID=$!
    SERVER_STARTED=true
    log "Server PID: $SERVER_PID"
fi

# 4) Wait for server ready (max 30s)
log "Waiting for server to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8010/health >/dev/null 2>&1; then
        log "[OK] Server ready after ${i}s"
        python3 scripts/smoke_api.py http://127.0.0.1:8010 2>&1 | tee -a "$LOG_FILE" || true
        break
    fi
    if [ "$i" -eq 30 ]; then
        log "[FAIL] Server did not start within 30s"
        exit 1
    fi
    sleep 1
done

# 5) Run smoke E2E test
log "Running smoke E2E test..."
cd "$ROOT_DIR"
python3 backend/scripts/smoke_e2e.py 2>&1 | tee -a "$LOG_FILE"
E2E_STATUS=${PIPESTATUS[0]}

# 6) Verify artifacts
log "Verifying artifacts..."
LATEST_JSON="$(ls -1t build/actions_*.json 2>/dev/null | head -n1 || true)"
LATEST_DOCX="$(ls -1t build/actions_*_v1.docx 2>/dev/null | head -n1 || true)"
LATEST_COMPARE="$(ls -1t build/actions_*_compare_v1.docx 2>/dev/null | head -n1 || true)"
ALL_OK=true
if [ -n "$LATEST_JSON" ] && [ -f "$LATEST_JSON" ]; then
    log "[OK] JSON output: $LATEST_JSON"
else
    log "[FAIL] Missing actions json output"
    ALL_OK=false
fi
if [ -n "$LATEST_DOCX" ] && [ -f "$LATEST_DOCX" ]; then
    log "[OK] DOCX output: $LATEST_DOCX"
else
    log "[FAIL] Missing actions DOCX output"
    ALL_OK=false
fi
if [ -n "$LATEST_COMPARE" ] && [ -f "$LATEST_COMPARE" ]; then
    log "[OK] Compare DOCX output: $LATEST_COMPARE"
else
    log "[FAIL] Missing actions compare DOCX output"
    ALL_OK=false
fi

# 7) Summary
log "=== E2E Test Complete ==="
if [ "$E2E_STATUS" -eq 0 ] && [ "$ALL_OK" = true ]; then
    log "[PASS] All checks passed"
    echo "PASS" > build/clawdbot/e2e_result.txt
    exit 0
else
    log "[FAIL] Some checks failed"
    echo "FAIL" > build/clawdbot/e2e_result.txt
    exit 1
fi
