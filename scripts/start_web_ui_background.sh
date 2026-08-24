#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
LOG="logs/webui_control.log"
echo "[$(date '+%F %T')] start requested" >> "$LOG"

# Delegate to the single startup entry to avoid drift and cross-system side effects.
# Keep the desktop launcher limited to starting the requested app. Continuous
# watchdog monitoring is opt-in so a manual launch does not silently recreate
# the automation the user disabled.
export ZF_ENABLE_SELF_HEAL="${ZF_ENABLE_SELF_HEAL:-0}"
./scripts/run_web_ui.sh --background "$@"

echo "[$(date '+%F %T')] start finished" >> "$LOG"
