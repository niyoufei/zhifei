#!/usr/bin/env bash
# 启动 Web 控制台（后端 + Streamlit）
# 用法：
#   ./scripts/run_web_ui.sh           # 前台运行
#   ./scripts/run_web_ui.sh -b        # 后台运行，可关闭终端
#   ./scripts/run_web_ui.sh --background
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

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

BACKEND_PORT="${BACKEND_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8501}"
BACKEND_HOST="${BACKEND_HOST:-${ZF_BACKEND_HOST:-${ZF_HOST:-127.0.0.1}}}"
WEB_HOST="${WEB_HOST:-${ZF_WEB_HOST:-${ZF_HOST:-127.0.0.1}}}"
BACKEND_CONNECT_HOST="${BACKEND_CONNECT_HOST:-${ZF_BACKEND_CONNECT_HOST:-127.0.0.1}}"
WEB_CONNECT_HOST="${WEB_CONNECT_HOST:-${ZF_WEB_CONNECT_HOST:-127.0.0.1}}"
WEB_READY_TIMEOUT_SEC="${ZF_WEB_READY_TIMEOUT_SECONDS:-120}"
WEB_POST_READY_STABLE_SEC="${ZF_WEB_POST_READY_STABLE_SECONDS:-15}"
PUBLIC_WEB_URL="${ZF_PUBLIC_WEB_URL:-}"
SYSTEM_ID="${ZF_SYSTEM_ID:-docgen-system}"
RUNTIME_DIR="${ZF_RUNTIME_DIR:-$ROOT/.runtime/docgen}"
PID_BACKEND="$RUNTIME_DIR/webui_backend.pid"
PID_STREAMLIT="$RUNTIME_DIR/streamlit.pid"
PID_WATCHDOG="$RUNTIME_DIR/webui_watchdog.pid"
CONTROL_LOG="logs/webui_control.log"

control_log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$1" >> "$CONTROL_LOG"
}

mkdir -p logs "$RUNTIME_DIR"
control_log "start requested background=$BACKGROUND backend_port=$BACKEND_PORT web_port=$WEB_PORT"
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
export ZF_SYSTEM_ID="$SYSTEM_ID"
export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
export ZF_BACKEND_BASE_URL="${ZF_BACKEND_BASE_URL:-http://${BACKEND_CONNECT_HOST}:${BACKEND_PORT}}"

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

spawn_detached() {
  local stdout_path="$1"
  local stderr_path="$2"
  shift 2
  ZF_SPAWN_STDOUT="$stdout_path" \
  ZF_SPAWN_STDERR="$stderr_path" \
  "${PYTHON_CMD[@]}" - "$@" <<'PY'
import os
import subprocess
import sys

cmd = sys.argv[1:]
with open(os.environ["ZF_SPAWN_STDOUT"], "ab", buffering=0) as out, \
     open(os.environ["ZF_SPAWN_STDERR"], "ab", buffering=0) as err:
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=out,
        stderr=err,
        start_new_session=True,
        close_fds=True,
    )
print(proc.pid)
PY
}

backend_identity_state() {
  local raw
  raw="$(curl -fsS --max-time 2 "http://${BACKEND_CONNECT_HOST}:${BACKEND_PORT}/health" 2>/dev/null || true)"
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

streamlit_health_ok() {
  local raw
  raw="$(curl -fsS --max-time 2 "http://${WEB_CONNECT_HOST}:${WEB_PORT}/_stcore/health" 2>/dev/null || true)"
  [ -n "$raw" ]
}

backend_provider_alignment() {
  local raw
  raw="$(curl -fsS --max-time 2 "http://${BACKEND_CONNECT_HOST}:${BACKEND_PORT}/capabilities" 2>/dev/null || true)"
  [ -n "$raw" ] || return 1
  set +e
  ZF_CAPS_RAW="$raw" \
  EXPECT_TEXT_MAIN="$([ -n "${OPENAI_API_KEY_TEXT_MAIN:-${OPENAI_API_KEY:-}}" ] && echo 1 || echo 0)" \
  EXPECT_TEXT_BACKUP="$([ -n "${OPENAI_API_KEY_TEXT_BACKUP:-${ZF_LLM_FALLBACK1_API_KEY:-}}" ] && echo 1 || echo 0)" \
  EXPECT_AUTOMATION="$([ -n "${OPENAI_API_KEY_AUTOMATION:-}" ] && echo 1 || echo 0)" \
  EXPECT_GEMINI_A="$([ -n "${GEMINI_API_KEY_A:-${ZF_GOOGLE_API_KEY:-${GOOGLE_API_KEY:-${GEMINI_API_KEY:-}}}}" ] && echo 1 || echo 0)" \
  EXPECT_GEMINI_B="$([ -n "${GEMINI_API_KEY_B:-}" ] && echo 1 || echo 0)" \
  "${PYTHON_CMD[@]}" - <<'PY'
import json
import os
import sys

def _expect(name: str) -> bool:
    return os.environ.get(name, "0").strip() == "1"

try:
    payload = json.loads(os.environ.get("ZF_CAPS_RAW", ""))
except Exception:
    sys.exit(1)
ps = payload.get("provider_status") if isinstance(payload, dict) else None
if not isinstance(ps, dict):
    sys.exit(1)

checks = [
    ("EXPECT_TEXT_MAIN", "text_main"),
    ("EXPECT_TEXT_BACKUP", "text_backup"),
    ("EXPECT_AUTOMATION", "automation"),
    ("EXPECT_GEMINI_A", "gemini_a"),
    ("EXPECT_GEMINI_B", "gemini_b"),
]
for env_name, field in checks:
    if not _expect(env_name):
        continue
    item = ps.get(field)
    if not isinstance(item, dict) or not bool(item.get("configured")):
        sys.exit(2)
sys.exit(0)
PY
  local code=$?
  set -e
  return "$code"
}

expect_local_provider_bootstrap() {
  [ -n "${OPENAI_API_KEY_TEXT_MAIN:-${OPENAI_API_KEY:-}}" ] && return 0
  [ -n "${OPENAI_API_KEY_TEXT_BACKUP:-${ZF_LLM_FALLBACK1_API_KEY:-}}" ] && return 0
  [ -n "${OPENAI_API_KEY_AUTOMATION:-}" ] && return 0
  [ -n "${GEMINI_API_KEY_A:-${ZF_GOOGLE_API_KEY:-${GOOGLE_API_KEY:-${GEMINI_API_KEY:-}}}}" ] && return 0
  [ -n "${GEMINI_API_KEY_B:-}" ] && return 0
  return 1
}

is_our_streamlit_cmd() {
  local cmd="$1"
  [[ "$cmd" == *"streamlit"* ]] || return 1
  [[ "$cmd" == *"$ROOT/app.py"* ]] || return 1
  [[ "$cmd" == *"--server.port ${WEB_PORT}"* ]] || return 1
  return 0
}

open_browser_if_allowed() {
  local open_url=""
  if [ "${ZF_SKIP_OPEN:-0}" = "1" ]; then
    return 0
  fi
  open_url="${PUBLIC_WEB_URL:-http://${WEB_CONNECT_HOST}:${WEB_PORT}}"
  if command -v open >/dev/null 2>&1; then
    # Browser auto-open is a best-effort convenience and must not flip the whole
    # launcher into a failed state once backend/web listeners are already up.
    open "$open_url" >/dev/null 2>&1 || true
  fi
  return 0
}

if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  set +e
  backend_identity_state
  code=$?
  set -e
  if [ "$code" -ne 0 ]; then
    owner_pid="$(port_owner_pid "$BACKEND_PORT")"
    owner_cmd="$(pid_cmdline "${owner_pid:-}")"
    if [ "$code" -eq 2 ]; then
      echo "[ERROR] 端口 ${BACKEND_PORT} 已被其他系统占用（非文档生成系统），为防串线已停止启动。"
    else
      echo "[ERROR] 端口 ${BACKEND_PORT} 已被占用且健康检查不可识别，已停止启动。"
    fi
    echo "        占用进程: pid=${owner_pid:-unknown}"
    echo "        命令: ${owner_cmd:-unknown}"
    control_log "start failed backend_port_conflict code=$code owner_pid=${owner_pid:-unknown}"
    exit 1
  fi
  owner_pid="$(port_owner_pid "$BACKEND_PORT")"
  if backend_provider_alignment; then
    if [ -n "${owner_pid:-}" ]; then
      echo "$owner_pid" > "$PID_BACKEND"
    fi
    control_log "backend ready pid=${owner_pid:-unknown} reused=true"
  else
    code=$?
    if expect_local_provider_bootstrap && { [ "$code" -eq 2 ] || [ "$code" -eq 1 ]; }; then
      echo "[WARN] 已发现旧 backend 进程，但 provider 未就绪；正在切换到读取本地 key 文件的新实例。"
      control_log "backend provider_mismatch code=$code owner_pid=${owner_pid:-unknown}; restarting"
      if [ -n "${owner_pid:-}" ]; then
        kill "$owner_pid" >/dev/null 2>&1 || true
      fi
      for _ in $(seq 1 10); do
        if ! lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
          break
        fi
        sleep 1
      done
      if lsof -nP -iTCP:"$BACKEND_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "[ERROR] 无法释放旧 backend 端口 ${BACKEND_PORT}，请检查占用进程。"
        control_log "start failed backend_port_release_timeout port=$BACKEND_PORT owner_pid=${owner_pid:-unknown}"
        exit 1
      fi
      spawn_detached "logs/webui_backend.out.log" "logs/webui_backend.err.log" \
        "${PYTHON_CMD[@]}" -m uvicorn backend.app.main:app \
        --app-dir "$ROOT" \
        --host "$BACKEND_HOST" \
        --port "$BACKEND_PORT" \
        > "$PID_BACKEND"

      ready=false
      for _ in $(seq 1 25); do
        if backend_identity_state && backend_provider_alignment; then
          ready=true
          break
        fi
        sleep 1
      done
      if [ "$ready" != true ]; then
        echo "[ERROR] 后端重启后 provider 仍未就绪，请检查 logs/webui_backend.err.log 和本地 key 文件。"
        control_log "start failed backend_provider_unready_after_restart"
        exit 1
      fi
      control_log "backend ready pid=$(cat "$PID_BACKEND" 2>/dev/null || echo unknown) reused=false restarted_for_provider=true"
    elif [ -n "${owner_pid:-}" ]; then
      echo "$owner_pid" > "$PID_BACKEND"
      control_log "backend ready pid=${owner_pid:-unknown} reused=true provider_check_skipped code=$code"
    fi
  fi
else
  spawn_detached "logs/webui_backend.out.log" "logs/webui_backend.err.log" \
    "${PYTHON_CMD[@]}" -m uvicorn backend.app.main:app \
    --app-dir "$ROOT" \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    > "$PID_BACKEND"

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
    control_log "start failed backend_boot_timeout"
    exit 1
  fi
  control_log "backend ready pid=$(cat "$PID_BACKEND" 2>/dev/null || echo unknown) reused=false"
fi

if [ "$BACKGROUND" = true ]; then
  web_reused=false
  if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    owner_pid="$(port_owner_pid "$WEB_PORT")"
    owner_cmd="$(pid_cmdline "${owner_pid:-}")"
    if ! is_our_streamlit_cmd "$owner_cmd"; then
      echo "[ERROR] 端口 ${WEB_PORT} 已被其他应用占用，为防止互相影响已停止启动。"
      echo "        占用进程: pid=${owner_pid:-unknown}"
      echo "        命令: ${owner_cmd:-unknown}"
      control_log "start failed web_port_conflict owner_pid=${owner_pid:-unknown}"
      exit 1
    fi
    if [ -n "${owner_pid:-}" ]; then
      echo "$owner_pid" > "$PID_STREAMLIT"
    fi
    web_reused=true
  else
    spawn_detached "logs/streamlit.out.log" "logs/streamlit.err.log" \
      "${PYTHON_CMD[@]}" -m streamlit run "$ROOT/app.py" \
      --server.address "$WEB_HOST" \
      --server.port "$WEB_PORT" \
      --server.headless true \
      --server.fileWatcherType none \
      --server.runOnSave false \
      > "$PID_STREAMLIT"
  fi

  web_ready=false
  for _ in $(seq 1 "$WEB_READY_TIMEOUT_SEC"); do
    if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1 && streamlit_health_ok; then
      web_ready=true
      break
    fi
    sleep 1
  done
  if [ "$web_ready" != true ]; then
    echo "[ERROR] Web UI 启动失败，请检查 logs/streamlit.err.log"
    control_log "start failed web_boot_timeout timeout_sec=$WEB_READY_TIMEOUT_SEC"
    exit 1
  fi
  if [ "$WEB_POST_READY_STABLE_SEC" -gt 0 ]; then
    stable_left="$WEB_POST_READY_STABLE_SEC"
    while [ "$stable_left" -gt 0 ]; do
      if ! lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1 || ! streamlit_health_ok; then
        echo "[ERROR] Web UI 启动后未能稳定就绪，请检查 logs/streamlit.err.log"
        control_log "start failed web_post_ready_unstable stable_sec=$WEB_POST_READY_STABLE_SEC"
        exit 1
      fi
      stable_left=$((stable_left - 1))
      if [ "$stable_left" -gt 0 ]; then
        sleep 1
      fi
    done
  fi
  owner_pid="$(port_owner_pid "$WEB_PORT")"
  if [ -n "${owner_pid:-}" ]; then
    echo "$owner_pid" > "$PID_STREAMLIT"
  fi
  if [ -f "$PID_STREAMLIT" ]; then
    control_log "web ready pid=$(cat "$PID_STREAMLIT" 2>/dev/null || echo unknown) reused=$web_reused stable_sec=$WEB_POST_READY_STABLE_SEC"
  fi
  # Optional self-heal watchdog (legacy mode; keep disabled by default, chief agent now runs in backend).
  # Disabled when already running inside watchdog context to avoid recursion.
  if [ "${ZF_ENABLE_SELF_HEAL:-0}" = "1" ] && [ "${ZF_WATCHDOG_MODE:-0}" != "1" ]; then
    wd_need_start=true
    if [ -f "$PID_WATCHDOG" ]; then
      wd_pid="$(cat "$PID_WATCHDOG" 2>/dev/null || true)"
      if [ -n "${wd_pid:-}" ] && kill -0 "$wd_pid" >/dev/null 2>&1; then
        wd_need_start=false
      fi
    fi
    if [ "$wd_need_start" = true ]; then
      nohup env \
        BACKEND_HOST="$BACKEND_CONNECT_HOST" \
        BACKEND_PORT="$BACKEND_PORT" \
        WEB_HOST="$WEB_CONNECT_HOST" \
        WEB_PORT="$WEB_PORT" \
        ZF_WATCHDOG_MODE=1 \
        ZF_ENABLE_SELF_HEAL=0 \
        "$ROOT/scripts/web_ui_watchdog.sh" \
        >> logs/webui_watchdog.out.log 2>> logs/webui_watchdog.err.log < /dev/null &
      echo $! > "$PID_WATCHDOG"
      control_log "watchdog ready pid=$(cat "$PID_WATCHDOG" 2>/dev/null || echo unknown)"
    fi
  fi
  open_browser_if_allowed
  control_log "start finished backend_pid=$(cat "$PID_BACKEND" 2>/dev/null || echo unknown) web_pid=$(cat "$PID_STREAMLIT" 2>/dev/null || echo unknown)"
  echo "文档生成系统已就绪，请访问 ${PUBLIC_WEB_URL:-http://${WEB_CONNECT_HOST}:${WEB_PORT}}"
  exit 0
fi

if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  owner_pid="$(port_owner_pid "$WEB_PORT")"
  control_log "start finished backend_pid=$(cat "$PID_BACKEND" 2>/dev/null || echo unknown) web_pid=${owner_pid:-unknown} foreground_reused_web=true"
  open_browser_if_allowed
  echo "文档生成系统已就绪，请访问 ${PUBLIC_WEB_URL:-http://${WEB_CONNECT_HOST}:${WEB_PORT}}"
  exit 0
fi

echo "文档生成系统已就绪，请访问 ${PUBLIC_WEB_URL:-http://${WEB_CONNECT_HOST}:${WEB_PORT}}"
control_log "start finished backend_pid=$(cat "$PID_BACKEND" 2>/dev/null || echo unknown) web_pid=foreground foreground_reused_web=false"
"${PYTHON_CMD[@]}" -m streamlit run "$ROOT/app.py" \
  --server.address "$WEB_HOST" \
  --server.port "$WEB_PORT" \
  --server.headless true \
  --server.fileWatcherType none \
  --server.runOnSave false
