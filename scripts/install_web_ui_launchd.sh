#!/usr/bin/env bash
# 安装 macOS launchd 服务，使 Web 控制台（后端 + Streamlit）在后台常驻运行，无需依赖终端。
# 用法：
#   ZF_ACTIONS_KEY=... ZF_GOOGLE_API_KEY=... ./scripts/install_web_ui_launchd.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# macOS TCC: LaunchAgent background processes may be blocked from Desktop/Documents paths.
# If the project is in protected folders, prefer direct startup script instead of launchd.
if [[ "$ROOT_DIR" == "$HOME/Desktop/"* || "$ROOT_DIR" == "$HOME/Documents/"* ]]; then
  echo "[WARN] 当前项目位于受保护目录：$ROOT_DIR"
  echo "[WARN] 为避免 launchd 无权限导致“页面打不开”，本次不安装 launchd。"
  echo "[OK] 请使用：./scripts/run_web_ui.sh --background"
  exit 0
fi

PLIST_ID_BACKEND="com.youfeini.docgen.webui.backend"
PLIST_ID_STREAMLIT="com.youfeini.docgen.webui.streamlit"
PLIST_ID_WATCHDOG="com.youfeini.docgen.webui.watchdog"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH_BACKEND="$PLIST_DIR/${PLIST_ID_BACKEND}.plist"
PLIST_PATH_STREAMLIT="$PLIST_DIR/${PLIST_ID_STREAMLIT}.plist"
PLIST_PATH_WATCHDOG="$PLIST_DIR/${PLIST_ID_WATCHDOG}.plist"

HOST="${ZF_HOST:-127.0.0.1}"
BACKEND_PORT="${ZF_BACKEND_PORT:-8010}"
WEB_PORT="${ZF_WEB_PORT:-8501}"
SYSTEM_ID="${ZF_SYSTEM_ID:-docgen-system}"

PYTHON=""
if [ -x "$ROOT_DIR/venv/bin/python3" ]; then
  PYTHON="$ROOT_DIR/venv/bin/python3"
elif [ -x "$ROOT_DIR/.venv/bin/python3" ]; then
  PYTHON="$ROOT_DIR/.venv/bin/python3"
else
  PYTHON="$(python3 -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
  if [ -z "${PYTHON:-}" ] || [ ! -x "${PYTHON:-}" ]; then
    PYTHON="$(command -v python3 || true)"
  fi
fi
if [ -z "${PYTHON:-}" ] || [ ! -x "${PYTHON:-}" ]; then
  echo "[FAIL] python3 not found"
  exit 1
fi

PY_LAUNCH_XML="      <string>${PYTHON}</string>"
HOST_SUPPORTS_ARM64="$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)"
if [ "$HOST_SUPPORTS_ARM64" = "1" ]; then
  # Force arm64 slice under launchd to avoid x86_64/Rosetta mismatches.
  if command -v arch >/dev/null 2>&1 && arch -arm64 "$PYTHON" -c 'import pydantic_core' >/dev/null 2>&1; then
    PY_LAUNCH_XML="      <string>/usr/bin/arch</string>
      <string>-arm64</string>
      <string>${PYTHON}</string>"
  fi
fi

mkdir -p "$PLIST_DIR"
mkdir -p "$ROOT_DIR/logs"

ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"
ZF_GOOGLE_API_KEY="${ZF_GOOGLE_API_KEY:-${GEMINI_API_KEY:-${GOOGLE_API_KEY:-}}}"
UTF8_LOCALE="${ZF_LOCALE:-}"
if [ -z "$UTF8_LOCALE" ] && command -v locale >/dev/null 2>&1; then
  if locale -a 2>/dev/null | grep -Eiq '^zh_CN\.UTF-8$'; then
    UTF8_LOCALE="zh_CN.UTF-8"
  elif locale -a 2>/dev/null | grep -Eiq '^en_US\.UTF-8$'; then
    UTF8_LOCALE="en_US.UTF-8"
  fi
fi
[ -n "$UTF8_LOCALE" ] || UTF8_LOCALE="en_US.UTF-8"

# 清理旧的双进程 LaunchAgent，避免与 watchdog 互相抢占。
for old_id in "$PLIST_ID_BACKEND" "$PLIST_ID_STREAMLIT"; do
  set +e
  launchctl bootout "gui/$UID/${old_id}" >/dev/null 2>&1
  launchctl bootout "gui/$UID" "$PLIST_DIR/${old_id}.plist" >/dev/null 2>&1
  set -e
  rm -f "$PLIST_DIR/${old_id}.plist"
done

# 单一 watchdog 服务：统一守护后端+Streamlit，掉线自动拉起。
cat >"$PLIST_PATH_WATCHDOG" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${PLIST_ID_WATCHDOG}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>${ROOT_DIR}</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PYTHONPATH</key>
      <string>${ROOT_DIR}</string>
      <key>LANG</key>
      <string>${UTF8_LOCALE}</string>
      <key>LC_ALL</key>
      <string>${UTF8_LOCALE}</string>
      <key>PYTHONUTF8</key>
      <string>1</string>
      <key>ZF_SYSTEM_ID</key>
      <string>${SYSTEM_ID}</string>
      <key>ZF_ACTIONS_KEY</key>
      <string>${ZF_ACTIONS_KEY}</string>
      <key>ZF_GOOGLE_API_KEY</key>
      <string>${ZF_GOOGLE_API_KEY}</string>
      <key>BACKEND_PORT</key>
      <string>${BACKEND_PORT}</string>
      <key>WEB_PORT</key>
      <string>${WEB_PORT}</string>
      <key>ZF_WATCHDOG_INTERVAL</key>
      <string>6</string>
    </dict>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>${ROOT_DIR}/scripts/web_ui_watchdog.sh</string>
    </array>
    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/logs/webui_watchdog.out.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/logs/webui_watchdog.err.log</string>
    <key>SoftResourceLimits</key>
    <dict>
      <key>NumberOfFiles</key>
      <integer>8192</integer>
    </dict>
    <key>HardResourceLimits</key>
    <dict>
      <key>NumberOfFiles</key>
      <integer>65536</integer>
    </dict>
  </dict>
</plist>
EOF

echo "[OK] wrote: $PLIST_PATH_WATCHDOG"

# (Re)load
set +e
launchctl bootout "gui/$UID" "$PLIST_PATH_WATCHDOG" >/dev/null 2>&1
set -e

launchctl bootstrap "gui/$UID" "$PLIST_PATH_WATCHDOG"
launchctl kickstart -k "gui/$UID/${PLIST_ID_WATCHDOG}" >/dev/null 2>&1 || true

echo "[OK] Web UI launchd 已安装并启动"
echo "     后端: http://${HOST}:${BACKEND_PORT}/health"
echo "     Web 控制台: http://${HOST}:${WEB_PORT}"
echo "     日志: logs/webui_watchdog.*.log, logs/webui_backend.*.log, logs/streamlit.*.log"
echo ""
echo "     卸载: ./scripts/uninstall_web_ui_launchd.sh"
