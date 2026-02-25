#!/usr/bin/env bash
# 启动 Web 控制台（后端 + Streamlit）
# 用法：
#   ./scripts/run_web_ui.sh           # 前台运行
#   ./scripts/run_web_ui.sh -b        # 后台运行，可关闭终端
#   ./scripts/run_web_ui.sh --background
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Keep UTF-8 output stable for Chinese paths/content.
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
# Mitigate macOS GUI-launch low fd soft-limit (e.g. 256) causing Errno 24.
ulimit -n "${ZF_MAX_OPEN_FILES:-8192}" >/dev/null 2>&1 || true

BACKGROUND=false
for arg in "$@"; do
  case "$arg" in
    -b|--background) BACKGROUND=true; break ;;
  esac
done

mkdir -p logs
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
export ZF_BACKEND_BASE_URL="${ZF_BACKEND_BASE_URL:-http://127.0.0.1:8010}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"

PYTHON="python3"
if [ -x "${ROOT}/venv/bin/python3" ]; then
  PYTHON="${ROOT}/venv/bin/python3"
elif [ -x "${ROOT}/.venv/bin/python3" ]; then
  PYTHON="${ROOT}/.venv/bin/python3"
fi

if ! lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  nohup "$PYTHON" -m uvicorn backend.app.main:app \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    > logs/webui_backend.out.log 2> logs/webui_backend.err.log < /dev/null &
  echo $! > logs/webui_backend.pid
  for _ in $(seq 1 20); do
    if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[ERROR] 后端启动失败，请检查 logs/webui_backend.err.log"
  exit 1
fi

if [ "$BACKGROUND" = true ]; then
  if ! lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    nohup "$PYTHON" -m streamlit run app.py \
      --server.port "$WEB_PORT" \
      --server.headless true \
      --server.fileWatcherType none \
      --server.runOnSave false \
      >> logs/streamlit.out.log 2>> logs/streamlit.err.log < /dev/null &
    echo $! > logs/streamlit.pid
  fi
  for i in $(seq 1 30); do
    if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[ERROR] Web UI 启动失败，请检查 logs/streamlit.err.log"
    exit 1
  fi
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:${WEB_PORT}"
  fi
  echo "施组专家系统已进化完成，请访问 http://127.0.0.1:8501"
  exit 0
fi

if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:${WEB_PORT}"
  fi
  echo "施组专家系统已进化完成，请访问 http://127.0.0.1:8501"
  exit 0
fi

echo "施组专家系统已进化完成，请访问 http://127.0.0.1:8501"
"$PYTHON" -m streamlit run app.py \
  --server.port "$WEB_PORT" \
  --server.headless true \
  --server.fileWatcherType none \
  --server.runOnSave false
