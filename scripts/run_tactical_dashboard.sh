#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p logs
PORT="${TACTICAL_WEB_PORT:-8512}"

python3 -m streamlit run tactical_dashboard.py \
  --server.port "$PORT" \
  --server.headless true
