#!/usr/bin/env bash
# Uninstall the macOS launchd LaunchAgent for this project.
set -euo pipefail

PLIST_ID="com.youfeini.docgen.autoplan"
PLIST_ID_WATCH="com.youfeini.docgen.autoplan.watcher"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_ID}.plist"
PLIST_PATH_WATCH="$HOME/Library/LaunchAgents/${PLIST_ID_WATCH}.plist"

if [ -f "$PLIST_PATH" ]; then
  set +e
  launchctl bootout "gui/$UID" "$PLIST_PATH" >/dev/null 2>&1
  set -e
  rm -f "$PLIST_PATH"
  echo "[OK] removed: $PLIST_PATH"
else
  echo "[OK] not installed: $PLIST_PATH"
fi

if [ -f "$PLIST_PATH_WATCH" ]; then
  set +e
  launchctl bootout "gui/$UID" "$PLIST_PATH_WATCH" >/dev/null 2>&1
  set -e
  rm -f "$PLIST_PATH_WATCH"
  echo "[OK] removed: $PLIST_PATH_WATCH"
else
  echo "[OK] not installed: $PLIST_PATH_WATCH"
fi
