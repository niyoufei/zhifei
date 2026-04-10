#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${1:-${DOCGEN_RELEASE_HOST:-}}"
REMOTE_APP_DIR="${DOCGEN_REMOTE_APP_DIR:-/opt/docgen}"
REMOTE_SCRIPT="${DOCGEN_REMOTE_READONLY_RETENTION_SCRIPT:-${REMOTE_APP_DIR%/}/scripts/report_docgen_server_readonly_retention.sh}"
REMOTE_INSPECTION_LOG_ROOT="${DOCGEN_READONLY_INSPECTION_LOG_ROOT:-${REMOTE_APP_DIR%/}/logs/readonly_inspection}"
REMOTE_RETENTION_LOG_ROOT="${DOCGEN_READONLY_RETENTION_LOG_ROOT:-${REMOTE_APP_DIR%/}/logs/readonly_retention}"
REMOTE_KEEP_RUNS="${DOCGEN_READONLY_INSPECTION_KEEP_RUNS:-10}"
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
ssh_cmd+=(
  "$REMOTE_HOST"
  "DOCGEN_READONLY_INSPECTION_LOG_ROOT='${REMOTE_INSPECTION_LOG_ROOT}' DOCGEN_READONLY_RETENTION_LOG_ROOT='${REMOTE_RETENTION_LOG_ROOT}' DOCGEN_READONLY_INSPECTION_KEEP_RUNS='${REMOTE_KEEP_RUNS}' bash '${REMOTE_SCRIPT}' '${REMOTE_APP_DIR}'"
)

if [[ "$PREVIEW" = "1" ]]; then
  printf 'remote_host=%s\n' "$REMOTE_HOST"
  printf 'remote_app_dir=%s\n' "$REMOTE_APP_DIR"
  printf 'remote_script=%s\n' "$REMOTE_SCRIPT"
  printf 'remote_inspection_log_root=%s\n' "$REMOTE_INSPECTION_LOG_ROOT"
  printf 'remote_retention_log_root=%s\n' "$REMOTE_RETENTION_LOG_ROOT"
  printf 'remote_keep_runs=%s\n' "$REMOTE_KEEP_RUNS"
  printf 'ssh_bin=%s\n' "$SSH_BIN"
  printf 'ssh_command=%s\n' "$(format_command "${ssh_cmd[@]}")"
  exit 0
fi

"${ssh_cmd[@]}"
