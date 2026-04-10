#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${1:-${DOCGEN_RELEASE_HOST:-}}"
REMOTE_APP_DIR="${DOCGEN_REMOTE_APP_DIR:-/opt/docgen}"
REMOTE_SCRIPT="${DOCGEN_REMOTE_SERVER_STATUS_SCRIPT:-${REMOTE_APP_DIR%/}/scripts/show_docgen_server_status.sh}"
SSH_OPTS="${DOCGEN_SSH_OPTS:-}"
SSH_BIN="${DOCGEN_SSH_BIN:-ssh}"
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

ssh_cmd=("$SSH_BIN")
if [[ -n "$SSH_OPTS" ]]; then
  # shellcheck disable=SC2206
  ssh_opts_parts=($SSH_OPTS)
  ssh_cmd+=("${ssh_opts_parts[@]}")
fi
ssh_cmd+=("$REMOTE_HOST" "bash '${REMOTE_SCRIPT}' '${REMOTE_APP_DIR}'")

if [[ "$PREVIEW" = "1" ]]; then
  printf 'remote_host=%s\n' "$REMOTE_HOST"
  printf 'remote_app_dir=%s\n' "$REMOTE_APP_DIR"
  printf 'remote_script=%s\n' "$REMOTE_SCRIPT"
  printf 'ssh_bin=%s\n' "$SSH_BIN"
  printf 'ssh_command=%s\n' "$(format_command "${ssh_cmd[@]}")"
  exit 0
fi

"${ssh_cmd[@]}"
