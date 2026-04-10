#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_HOST="${1:-${DOCGEN_RELEASE_HOST:-}}"
REMOTE_RELEASE_DIR="${DOCGEN_REMOTE_RELEASE_DIR:-/opt/docgen/releases}"
SSH_OPTS="${DOCGEN_SSH_OPTS:-}"
SSH_BIN="${DOCGEN_SSH_BIN:-ssh}"
VERIFY_SCRIPT="${DOCGEN_RELEASE_VERIFY_SCRIPT:-$ROOT/scripts/verify_docgen_server_release_dir.sh}"
PREVIEW="${DOCGEN_PREVIEW:-0}"

format_command() {
  python3 - "$@" <<'PY'
import shlex
import sys

print(" ".join(shlex.quote(arg) for arg in sys.argv[1:]))
PY
}

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

[[ -n "$REMOTE_HOST" ]] || fail "usage: $0 <user@host>"
[[ -f "$VERIFY_SCRIPT" ]] || fail "missing verify script: $VERIFY_SCRIPT"

ssh_cmd=("$SSH_BIN")
if [[ -n "$SSH_OPTS" ]]; then
  # shellcheck disable=SC2206
  ssh_opts_parts=($SSH_OPTS)
  ssh_cmd+=("${ssh_opts_parts[@]}")
fi
ssh_cmd+=("$REMOTE_HOST" "bash -s -- ${REMOTE_RELEASE_DIR}")

if [[ "$PREVIEW" = "1" ]]; then
  printf 'remote_host=%s\n' "$REMOTE_HOST"
  printf 'remote_release_dir=%s\n' "$REMOTE_RELEASE_DIR"
  printf 'verify_script=%s\n' "$VERIFY_SCRIPT"
  printf 'ssh_bin=%s\n' "$SSH_BIN"
  printf 'ssh_command=%s < %s\n' "$(format_command "${ssh_cmd[@]}")" "$(printf '%q' "$VERIFY_SCRIPT")"
  exit 0
fi

"${ssh_cmd[@]}" < "$VERIFY_SCRIPT"
