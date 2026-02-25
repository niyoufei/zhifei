#!/usr/bin/env bash
# 安装 macOS launchd 服务，使 Web 控制台（后端 + Streamlit）在后台常驻运行，无需依赖终端。
# 用法：
#   ZF_ACTIONS_KEY=... ZF_GOOGLE_API_KEY=... ./scripts/install_web_ui_launchd.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST_ID_BACKEND="com.youfeini.docgen.webui.backend"
PLIST_ID_STREAMLIT="com.youfeini.docgen.webui.streamlit"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH_BACKEND="$PLIST_DIR/${PLIST_ID_BACKEND}.plist"
PLIST_PATH_STREAMLIT="$PLIST_DIR/${PLIST_ID_STREAMLIT}.plist"

HOST="${ZF_HOST:-127.0.0.1}"
BACKEND_PORT="${ZF_BACKEND_PORT:-8010}"
WEB_PORT="${ZF_WEB_PORT:-8501}"

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

mkdir -p "$PLIST_DIR"
mkdir -p "$ROOT_DIR/logs"

ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-}"
ZF_GOOGLE_API_KEY="${ZF_GOOGLE_API_KEY:-${GEMINI_API_KEY:-${GOOGLE_API_KEY:-}}}"

# 后端服务 (8010)
cat >"$PLIST_PATH_BACKEND" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${PLIST_ID_BACKEND}</string>
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
      <key>ZF_ACTIONS_KEY</key>
      <string>${ZF_ACTIONS_KEY}</string>
      <key>ZF_GOOGLE_API_KEY</key>
      <string>${ZF_GOOGLE_API_KEY}</string>
    </dict>
    <key>ProgramArguments</key>
    <array>
      <string>${PYTHON}</string>
      <string>-m</string>
      <string>uvicorn</string>
      <string>backend.app.main:app</string>
      <string>--host</string>
      <string>${HOST}</string>
      <string>--port</string>
      <string>${BACKEND_PORT}</string>
    </array>
    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/logs/webui_backend.out.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/logs/webui_backend.err.log</string>
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

echo "[OK] wrote: $PLIST_PATH_BACKEND"

# Streamlit Web UI (8501)
cat >"$PLIST_PATH_STREAMLIT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${PLIST_ID_STREAMLIT}</string>
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
      <key>ZF_BACKEND_BASE_URL</key>
      <string>http://${HOST}:${BACKEND_PORT}</string>
      <key>ZF_ACTIONS_KEY</key>
      <string>${ZF_ACTIONS_KEY}</string>
    </dict>
    <key>ProgramArguments</key>
    <array>
      <string>${PYTHON}</string>
      <string>-m</string>
      <string>streamlit</string>
      <string>run</string>
      <string>app.py</string>
      <string>--server.port</string>
      <string>${WEB_PORT}</string>
      <string>--server.headless</string>
      <string>true</string>
      <string>--server.fileWatcherType</string>
      <string>none</string>
      <string>--server.runOnSave</string>
      <string>false</string>
    </array>
    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/logs/streamlit.out.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/logs/streamlit.err.log</string>
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

echo "[OK] wrote: $PLIST_PATH_STREAMLIT"

# (Re)load
set +e
launchctl bootout "gui/$UID" "$PLIST_PATH_BACKEND" >/dev/null 2>&1
launchctl bootout "gui/$UID" "$PLIST_PATH_STREAMLIT" >/dev/null 2>&1
set -e

launchctl bootstrap "gui/$UID" "$PLIST_PATH_BACKEND"
launchctl bootstrap "gui/$UID" "$PLIST_PATH_STREAMLIT"
launchctl kickstart -k "gui/$UID/${PLIST_ID_BACKEND}" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID/${PLIST_ID_STREAMLIT}" >/dev/null 2>&1 || true

echo "[OK] Web UI launchd 已安装并启动"
echo "     后端: http://${HOST}:${BACKEND_PORT}/health"
echo "     Web 控制台: http://${HOST}:${WEB_PORT}"
echo "     日志: logs/webui_backend.*.log, logs/streamlit.*.log"
echo ""
echo "     卸载: ./scripts/uninstall_web_ui_launchd.sh"
