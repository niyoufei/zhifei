#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
LOG="logs/webui_control.log"
echo "[$(date '+%F %T')] start requested" >> "$LOG"

# Delegate to the single startup entry to avoid drift and cross-system side effects.
export ZF_ENABLE_SELF_HEAL="${ZF_ENABLE_SELF_HEAL:-1}"
./scripts/run_web_ui.sh --background "$@"

echo "[$(date '+%F %T')] start finished" >> "$LOG"
