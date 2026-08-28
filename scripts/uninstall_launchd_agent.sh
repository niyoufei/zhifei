#!/usr/bin/env bash
# Compatibility entrypoint for the consolidated runtime supervisor uninstaller.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/uninstall_web_ui_launchd.sh" "$@"
