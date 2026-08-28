#!/usr/bin/env bash
# Stop and remove the single runtime supervisor plus obsolete local agents.
set -euo pipefail

PLIST_DIR="$HOME/Library/LaunchAgents"
SUPERVISOR_ID="com.youfeini.docgen.runtime-supervisor"
KNOWN_IDS=(
  "$SUPERVISOR_ID"
  "com.youfeini.docgen.webui.backend"
  "com.youfeini.docgen.webui.streamlit"
  "com.youfeini.docgen.webui.watchdog"
  "com.youfeini.docgen.autoplan"
  "com.youfeini.docgen.autoplan.watcher"
)

for label in "${KNOWN_IDS[@]}"; do
  path="$PLIST_DIR/${label}.plist"
  launchctl bootout "gui/$UID/${label}" >/dev/null 2>&1 || true
  launchctl bootout "gui/$UID" "$path" >/dev/null 2>&1 || true
  if [ -f "$path" ]; then
    rm -f "$path"
    echo "[OK] removed: $path"
  fi
done

echo "[OK] runtime supervisor is stopped and uninstalled"
