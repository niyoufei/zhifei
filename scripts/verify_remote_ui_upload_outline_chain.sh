#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="${DOCGEN_UI_VERIFY_SCRIPT:-$ROOT/scripts/verify_ui_upload_outline_chain.sh}"
TARGET="${1:-${DOCGEN_UI_REMOTE_TARGET:-}}"
LOCAL_PORT="${DOCGEN_UI_LOCAL_TUNNEL_PORT:-18501}"
REMOTE_HOST="${DOCGEN_UI_REMOTE_HOST:-127.0.0.1}"
REMOTE_PORT="${DOCGEN_UI_REMOTE_PORT:-8501}"
TUNNEL_TIMEOUT_SECONDS="${DOCGEN_UI_TUNNEL_TIMEOUT_SECONDS:-20}"
SSH_BIN="${DOCGEN_UI_SSH_BIN:-ssh}"
CURL_BIN="${DOCGEN_UI_CURL_BIN:-curl}"

tunnel_pid=""

cleanup() {
  if [[ -n "$tunnel_pid" ]]; then
    kill "$tunnel_pid" >/dev/null 2>&1 || true
    wait "$tunnel_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

require_cmd() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "[ERROR] missing required command: $name" >&2
    exit 1
  fi
}

if [[ -z "$TARGET" ]]; then
  echo "[ERROR] missing ssh target. usage: bash ./scripts/verify_remote_ui_upload_outline_chain.sh user@host" >&2
  exit 1
fi

if [[ ! -x "$VERIFY_SCRIPT" ]]; then
  echo "[ERROR] ui verify script not executable: $VERIFY_SCRIPT" >&2
  exit 1
fi

require_cmd "$SSH_BIN"
require_cmd "$CURL_BIN"

echo "[INFO] ssh_target=$TARGET"
echo "[INFO] tunnel=127.0.0.1:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT}"
echo "[INFO] verify_script=$VERIFY_SCRIPT"

"$SSH_BIN" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -L "${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}" \
  "$TARGET" \
  -N &
tunnel_pid="$!"

for _ in $(seq 1 "$TUNNEL_TIMEOUT_SECONDS"); do
  if "$CURL_BIN" -fsS "http://127.0.0.1:${LOCAL_PORT}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! "$CURL_BIN" -fsS "http://127.0.0.1:${LOCAL_PORT}" >/dev/null 2>&1; then
  echo "[ERROR] ssh tunnel did not become ready within ${TUNNEL_TIMEOUT_SECONDS}s" >&2
  exit 1
fi

echo "[OK] tunnel ready: http://127.0.0.1:${LOCAL_PORT}"

DOCGEN_UI_BASE_URL="http://127.0.0.1:${LOCAL_PORT}" \
  bash "$VERIFY_SCRIPT"
