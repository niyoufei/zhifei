#!/usr/bin/env bash
# Install a macOS launchd LaunchAgent to keep the FastAPI backend running.
# Usage:
#   ZF_ACTIONS_KEY=... ZF_GOOGLE_API_KEY=... ./scripts/install_launchd_agent.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PLIST_ID="com.youfeini.docgen.autoplan"
PLIST_ID_WATCH="com.youfeini.docgen.autoplan.watcher"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/${PLIST_ID}.plist"
PLIST_PATH_WATCH="$PLIST_DIR/${PLIST_ID_WATCH}.plist"

HOST="${ZF_HOST:-127.0.0.1}"
PORT="${ZF_PORT:-8010}"
WATCH_ROOT="${ZF_WATCH_ROOT:-${ROOT_DIR}/projects}"
WATCH_POLL_SEC="${ZF_WATCH_POLL_SEC:-3}"
WATCH_STABLE_SEC="${ZF_WATCH_STABLE_SEC:-15}"

PYTHON="$ROOT_DIR/venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || true)"
fi
if [ -z "${PYTHON:-}" ]; then
  echo "[FAIL] python3 not found"
  exit 1
fi

mkdir -p "$PLIST_DIR"
mkdir -p "$ROOT_DIR/logs"

# Optional env vars
ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-}"
ZF_GOOGLE_API_KEY="${ZF_GOOGLE_API_KEY:-${GEMINI_API_KEY:-${GOOGLE_API_KEY:-}}}"

cat >"$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${PLIST_ID}</string>

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
      <string>${PORT}</string>
    </array>

    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/logs/uvicorn.out.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/logs/uvicorn.err.log</string>
  </dict>
</plist>
EOF

echo "[OK] wrote: $PLIST_PATH"

cat >"$PLIST_PATH_WATCH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${PLIST_ID_WATCH}</string>

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
      <key>ZF_HOST</key>
      <string>${HOST}</string>
      <key>ZF_PORT</key>
      <string>${PORT}</string>
      <key>ZF_WATCH_ROOT</key>
      <string>${WATCH_ROOT}</string>
      <key>ZF_WATCH_POLL_SEC</key>
      <string>${WATCH_POLL_SEC}</string>
      <key>ZF_WATCH_STABLE_SEC</key>
      <string>${WATCH_STABLE_SEC}</string>
    </dict>

    <key>ProgramArguments</key>
    <array>
      <string>${PYTHON}</string>
      <string>${ROOT_DIR}/scripts/watch_projects_autoplan.py</string>
    </array>

    <key>StandardOutPath</key>
    <string>${ROOT_DIR}/logs/watcher.out.log</string>
    <key>StandardErrorPath</key>
    <string>${ROOT_DIR}/logs/watcher.err.log</string>
  </dict>
</plist>
EOF

echo "[OK] wrote: $PLIST_PATH_WATCH"

# (Re)load the agent
set +e
launchctl bootout "gui/$UID" "$PLIST_PATH" >/dev/null 2>&1
launchctl bootout "gui/$UID" "$PLIST_PATH_WATCH" >/dev/null 2>&1
set -e

launchctl bootstrap "gui/$UID" "$PLIST_PATH"
launchctl bootstrap "gui/$UID" "$PLIST_PATH_WATCH"
launchctl enable "gui/$UID/${PLIST_ID}" >/dev/null 2>&1 || true
launchctl enable "gui/$UID/${PLIST_ID_WATCH}" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID/${PLIST_ID}" >/dev/null 2>&1 || true
launchctl kickstart -k "gui/$UID/${PLIST_ID_WATCH}" >/dev/null 2>&1 || true

echo "[OK] launchd agent installed and started: $PLIST_ID"
echo "[OK] launchd agent installed and started: $PLIST_ID_WATCH"
echo "     Health: curl -s http://${HOST}:${PORT}/health"
echo "     Watch:  ${WATCH_ROOT}/inbox (auto move -> work/done/failed)"
