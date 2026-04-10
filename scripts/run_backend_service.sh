#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

KEYS_FILE="${ZF_KEYS_FILE:-$ROOT/.runtime/local_keys.env}"
if [ -f "$KEYS_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$KEYS_FILE"
  set +a
fi

export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"
export ZF_ACTIONS_KEY="${ZF_ACTIONS_KEY:-zf-webui-key}"

HOST="${ZF_HOST:-127.0.0.1}"
PORT="${ZF_PORT:-8010}"

PYTHON="$ROOT/venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$ROOT/.venv/bin/python3"
fi
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || true)"
fi
if [ -z "${PYTHON:-}" ] || [ ! -x "$PYTHON" ]; then
  echo "[FAIL] python3 not found" >&2
  exit 1
fi

exec "$PYTHON" -m uvicorn backend.app.main:app --host "$HOST" --port "$PORT"
