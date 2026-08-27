#!/usr/bin/env bash
# 启动 Web 控制台（后端 + Streamlit）
# 用法：
#   ./scripts/run_web_ui.sh           # 前台运行
#   ./scripts/run_web_ui.sh -b        # 后台运行，可关闭终端
#   ./scripts/run_web_ui.sh --background
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Production launches never execute the mutable workspace.  The only default
# route is the content-addressed release selected by the fixed current pointer.
# Developers may still run this legacy workspace path, but only by making that
# diagnostic intent explicit.
if [ "${ZF_DEV_WORKSPACE_MODE:-0}" != "1" ]; then
  BOOTSTRAP_PYTHON="/usr/bin/python3"
  OS_HOME="$("$BOOTSTRAP_PYTHON" -I -B -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
  case "$OS_HOME" in /*) ;; *) exit 2 ;; esac
  SEALED_BASE="${OS_HOME}/Library/Application Support/com.zhifei.construction-expert"
  TRUSTED_BOOTSTRAP="${SEALED_BASE}/bootstrap/launch_current.py"
  if [ ! -x "$BOOTSTRAP_PYTHON" ] || [ ! -f "$TRUSTED_BOOTSTRAP" ] || [ -L "$TRUSTED_BOOTSTRAP" ]; then
    printf '%s\n' \
      '{"ok":false,"error_code":"LAUNCH_BOOTSTRAP_MISSING","message":"固定外置可信启动入口不可用，请重新执行本地封存"}' \
      >&2
    exit 2
  fi
  SEALED_ARGS=()
  for arg in "$@"; do
    case "$arg" in
      -b|--background)
        # The immutable supervisor is always detached by its start command.
        ;;
      --no-open)
        SEALED_ARGS+=("$arg")
        ;;
      *)
        printf '%s\n' \
          '{"ok":false,"error_code":"LAUNCH_ARGUMENT_UNSUPPORTED","message":"不可变启动入口收到不受支持的参数"}' \
          >&2
        exit 2
        ;;
    esac
  done
  exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" "${SEALED_ARGS[@]}"
fi

# Optional local secrets file (single-user machine). Not committed to git.
KEYS_FILE="${ZF_KEYS_FILE:-$ROOT/.runtime/local_keys.env}"
if [ -f "$KEYS_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$KEYS_FILE"
  set +a
fi

pick_utf8_locale() {
  if [ -n "${ZF_LOCALE:-}" ]; then
    printf "%s" "$ZF_LOCALE"
    return 0
  fi
  if command -v locale >/dev/null 2>&1; then
    if locale -a 2>/dev/null | grep -Eiq '^zh_CN\.UTF-8$'; then
      printf "%s" "zh_CN.UTF-8"
      return 0
    fi
    if locale -a 2>/dev/null | grep -Eiq '^en_US\.UTF-8$'; then
      printf "%s" "en_US.UTF-8"
      return 0
    fi
  fi
  printf "%s" ""
}

LOCALE_VAL="$(pick_utf8_locale)"
if [ -n "$LOCALE_VAL" ]; then
  export LANG="$LOCALE_VAL"
  export LC_ALL="$LOCALE_VAL"
fi

# Mitigate macOS GUI-launch low fd soft-limit (e.g. 256) causing Errno 24.
ulimit -n "${ZF_MAX_OPEN_FILES:-8192}" >/dev/null 2>&1 || true

BACKGROUND=false
for arg in "$@"; do
  case "$arg" in
    -b|--background) BACKGROUND=true; break ;;
  esac
done

# Use one explicit value for the backend health contract and the watchdog
# launcher.  This makes Finder/app-bundle cold starts equivalent to the
# maintained background-start script.
export ZF_ENABLE_SELF_HEAL="${ZF_ENABLE_SELF_HEAL:-1}"

BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"
SYSTEM_ID="${ZF_SYSTEM_ID:-docgen-system}"
RUNTIME_DIR="${ZF_RUNTIME_DIR:-$ROOT/.runtime/docgen}"
PID_BACKEND="$RUNTIME_DIR/webui_backend.pid"
PID_STREAMLIT="$RUNTIME_DIR/streamlit.pid"
PID_WATCHDOG="$RUNTIME_DIR/webui_watchdog.pid"
PID_OLLAMA="$RUNTIME_DIR/ollama.pid"

mkdir -p logs "$RUNTIME_DIR"
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
export ZF_SYSTEM_ID="$SYSTEM_ID"
# No shared/default credential is permitted.  backend/app.py load the local
# 0600 env file themselves in development; sealed releases receive the same
# generated credential from the supervisor's 0600 env file.
if [ -n "${ZF_ACTIONS_KEY:-}" ]; then
  export ZF_ACTIONS_KEY
fi
export ZF_BACKEND_BASE_URL="${ZF_BACKEND_BASE_URL:-http://127.0.0.1:${BACKEND_PORT}}"
# Resolve the project compliance registry from the repository, regardless of
# whether the app is launched from Terminal, Finder, LaunchAgent, or an app
# bundle.  This prevents GUI launches from silently looking in a different cwd.
export ZF_COMPLIANCE_ROOT="${ZF_COMPLIANCE_ROOT:-$ROOT/知识图谱/compliance}"

# Local-model preview defaults for Apple Silicon machines.  This is an
# optional, read-only reviewer and never blocks the main generation service.
# Local preview is a strict loopback-only diagnostic.  Do not inherit a
# caller-controlled URL: prompts and chapter text must never leave this Mac
# through the Ollama compatibility path.
export OLLAMA_BASE_URL="http://127.0.0.1:11434"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3.5:4b}"
export ZDOC_OLLAMA_PREVIEW_ENABLED="${ZDOC_OLLAMA_PREVIEW_ENABLED:-1}"
export ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED="${ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED:-true}"
export ZDOC_OLLAMA_PREVIEW_BASE_URL="$OLLAMA_BASE_URL"
export ZDOC_OLLAMA_PREVIEW_MODEL="${ZDOC_OLLAMA_PREVIEW_MODEL:-$OLLAMA_MODEL}"

OLLAMA_BIN="${ZF_OLLAMA_BIN:-}"
if [ -z "$OLLAMA_BIN" ]; then
  if command -v ollama >/dev/null 2>&1; then
    OLLAMA_BIN="$(command -v ollama)"
  elif [ -x "/Applications/Ollama.app/Contents/Resources/ollama" ]; then
    OLLAMA_BIN="/Applications/Ollama.app/Contents/Resources/ollama"
  fi
fi

ensure_ollama_service() {
  local health_url="${OLLAMA_BASE_URL%/}/api/version"
  if curl -fsS --max-time 2 "$health_url" >/dev/null 2>&1; then
    return 0
  fi

  case "$OLLAMA_BASE_URL" in
    http://127.0.0.1:11434|http://localhost:11434)
      ;;
    *)
      echo "[WARN] 自定义 Ollama 地址当前不可用：$OLLAMA_BASE_URL；本地预览暂不可用。"
      return 0
      ;;
  esac

  if [ -z "$OLLAMA_BIN" ] || [ ! -x "$OLLAMA_BIN" ]; then
    echo "[WARN] 未发现 Ollama 可执行文件；本地模型预览暂不可用。"
    return 0
  fi

  nohup env \
    OLLAMA_HOST="127.0.0.1:11434" \
    OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-4096}" \
    OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}" \
    OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}" \
    OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:-3m}" \
    "$OLLAMA_BIN" serve \
    > logs/ollama.out.log 2> logs/ollama.err.log < /dev/null &
  echo $! > "$PID_OLLAMA"

  for _ in $(seq 1 20); do
    if curl -fsS --max-time 2 "$health_url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "[WARN] Ollama 未能启动；本地预览暂不可用，请检查 logs/ollama.err.log。"
  return 0
}

ensure_ollama_service

PYTHON="python3"
if [ -x "${ROOT}/venv/bin/python3" ]; then
  PYTHON="${ROOT}/venv/bin/python3"
elif [ -x "${ROOT}/.venv/bin/python3" ]; then
  PYTHON="${ROOT}/.venv/bin/python3"
fi

PYTHON_CMD=("$PYTHON")
HOST_SUPPORTS_ARM64="$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)"
if [ "$HOST_SUPPORTS_ARM64" = "1" ]; then
  # Some launchers run under Rosetta (x86_64), causing C-extension arch mismatch.
  if ! "$PYTHON" -c 'import pydantic_core' >/dev/null 2>&1; then
    if command -v arch >/dev/null 2>&1 && arch -arm64 "$PYTHON" -c 'import pydantic_core' >/dev/null 2>&1; then
      PYTHON_CMD=(arch -arm64 "$PYTHON")
    fi
  fi
fi

port_owner_pid() {
  lsof -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -n1
}

pid_cmdline() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

backend_identity_state() {
  local raw
  raw="$(curl -fsS --max-time 2 "http://127.0.0.1:${BACKEND_PORT}/health" 2>/dev/null || true)"
  [ -n "$raw" ] || return 1
  set +e
  ZF_HEALTH_RAW="$raw" "${PYTHON_CMD[@]}" - "$SYSTEM_ID" <<'PY'
import json
import os
import sys

expected = (sys.argv[1] or "").strip()
try:
    payload = json.loads(os.environ.get("ZF_HEALTH_RAW", ""))
except Exception:
    sys.exit(1)
sid = str(payload.get("system_id") or "").strip()
service = str(payload.get("service") or "").strip()
if sid:
    sys.exit(0 if sid == expected else 2)
if service and service != "文档生成系统":
    sys.exit(2)
sys.exit(0)
PY
  local code=$?
  set -e
  if [ "$code" -eq 0 ]; then
    return 0
  fi
  if [ "$code" -eq 2 ]; then
    return 2
  fi
  return 1
}

is_our_streamlit_cmd() {
  local cmd="$1"
  [[ "$cmd" == *"streamlit"* ]] || return 1
  [[ "$cmd" == *"$ROOT/app.py"* ]] || return 1
  [[ "$cmd" == *"--server.port ${WEB_PORT}"* ]] || return 1
  return 0
}

if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if ! backend_identity_state; then
    code=$?
    owner_pid="$(port_owner_pid "$BACKEND_PORT")"
    owner_cmd="$(pid_cmdline "${owner_pid:-}")"
    if [ "$code" -eq 2 ]; then
      echo "[ERROR] 端口 ${BACKEND_PORT} 已被其他系统占用（非文档生成系统），为防串线已停止启动。"
    else
      echo "[ERROR] 端口 ${BACKEND_PORT} 已被占用且健康检查不可识别，已停止启动。"
    fi
    echo "        占用进程: pid=${owner_pid:-unknown}"
    echo "        命令: ${owner_cmd:-unknown}"
    exit 1
  fi
  owner_pid="$(port_owner_pid "$BACKEND_PORT")"
  if [ -n "${owner_pid:-}" ]; then
    echo "$owner_pid" > "$PID_BACKEND"
  fi
else
  nohup "${PYTHON_CMD[@]}" -m uvicorn backend.app.main:app \
    --app-dir "$ROOT" \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    > logs/webui_backend.out.log 2> logs/webui_backend.err.log < /dev/null &
  echo $! > "$PID_BACKEND"

  ready=false
  for _ in $(seq 1 25); do
    if backend_identity_state; then
      ready=true
      break
    fi
    sleep 1
  done
  if [ "$ready" != true ]; then
    echo "[ERROR] 后端启动失败，请检查 logs/webui_backend.err.log"
    exit 1
  fi
fi

if [ "$BACKGROUND" = true ]; then
  if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    owner_pid="$(port_owner_pid "$WEB_PORT")"
    owner_cmd="$(pid_cmdline "${owner_pid:-}")"
    if ! is_our_streamlit_cmd "$owner_cmd"; then
      echo "[ERROR] 端口 ${WEB_PORT} 已被其他应用占用，为防止互相影响已停止启动。"
      echo "        占用进程: pid=${owner_pid:-unknown}"
      echo "        命令: ${owner_cmd:-unknown}"
      exit 1
    fi
    if [ -n "${owner_pid:-}" ]; then
      echo "$owner_pid" > "$PID_STREAMLIT"
    fi
  else
    nohup "${PYTHON_CMD[@]}" -m streamlit run "$ROOT/app.py" \
      --server.address 127.0.0.1 \
      --server.port "$WEB_PORT" \
      --server.headless true \
      --server.fileWatcherType none \
      --server.runOnSave false \
      >> logs/streamlit.out.log 2>> logs/streamlit.err.log < /dev/null &
    echo $! > "$PID_STREAMLIT"
  fi

  for _ in $(seq 1 30); do
    if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[ERROR] Web UI 启动失败，请检查 logs/streamlit.err.log"
    exit 1
  fi
  # Self-heal is enabled by default for local launches so every supported
  # desktop entry point gets the same crash-recovery behavior.  Set the flag
  # explicitly to 0 only for controlled diagnostics.
  if [ "${ZF_ENABLE_SELF_HEAL:-1}" = "1" ] && [ "${ZF_WATCHDOG_MODE:-0}" != "1" ]; then
    wd_need_start=true
    if [ -f "$PID_WATCHDOG" ]; then
      wd_pid="$(cat "$PID_WATCHDOG" 2>/dev/null || true)"
      if [ -n "${wd_pid:-}" ] && kill -0 "$wd_pid" >/dev/null 2>&1; then
        wd_need_start=false
      fi
    fi
    if [ "$wd_need_start" = true ]; then
      nohup env \
        BACKEND_PORT="$BACKEND_PORT" \
        WEB_PORT="$WEB_PORT" \
        ZF_WATCHDOG_MODE=1 \
        ZF_ENABLE_SELF_HEAL=1 \
        "$ROOT/scripts/web_ui_watchdog.sh" \
        >> logs/webui_watchdog.out.log 2>> logs/webui_watchdog.err.log < /dev/null &
      echo $! > "$PID_WATCHDOG"
    fi
  fi
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:${WEB_PORT}"
  fi
  echo "施组专家系统已进化完成，请访问 http://127.0.0.1:${WEB_PORT}"
  exit 0
fi

if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:${WEB_PORT}"
  fi
  echo "施组专家系统已进化完成，请访问 http://127.0.0.1:${WEB_PORT}"
  exit 0
fi

echo "施组专家系统已进化完成，请访问 http://127.0.0.1:${WEB_PORT}"
"${PYTHON_CMD[@]}" -m streamlit run "$ROOT/app.py" \
  --server.address 127.0.0.1 \
  --server.port "$WEB_PORT" \
  --server.headless true \
  --server.fileWatcherType none \
  --server.runOnSave false
