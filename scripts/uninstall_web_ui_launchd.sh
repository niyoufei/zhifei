#!/usr/bin/env bash
# 卸载 Web 控制台 launchd 服务
set -euo pipefail

PLIST_ID_BACKEND="com.youfeini.docgen.webui.backend"
PLIST_ID_STREAMLIT="com.youfeini.docgen.webui.streamlit"
PLIST_PATH_BACKEND="$HOME/Library/LaunchAgents/${PLIST_ID_BACKEND}.plist"
PLIST_PATH_STREAMLIT="$HOME/Library/LaunchAgents/${PLIST_ID_STREAMLIT}.plist"

for path in "$PLIST_PATH_BACKEND" "$PLIST_PATH_STREAMLIT"; do
  if [ -f "$path" ]; then
    set +e
    launchctl bootout "gui/$UID" "$path" >/dev/null 2>&1
    set -e
    rm -f "$path"
    echo "[OK] removed: $path"
  else
    echo "[OK] not installed: $path"
  fi
done
