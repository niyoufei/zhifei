#!/usr/bin/env bash
# Compatibility entrypoint: all runtime services now use one supervisor agent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/install_web_ui_launchd.sh" "$@"
