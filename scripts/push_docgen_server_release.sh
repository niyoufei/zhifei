#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE_HOST="${1:-${DOCGEN_RELEASE_HOST:-}}"
LOCAL_RELEASE_DIR="${DOCGEN_LOCAL_RELEASE_DIR:-$ROOT/build/server_app_bundle}"
REMOTE_RELEASE_DIR="${DOCGEN_REMOTE_RELEASE_DIR:-/opt/docgen/releases}"
SSH_OPTS="${DOCGEN_SSH_OPTS:-}"
SCP_BIN="${DOCGEN_SCP_BIN:-scp}"
SSH_BIN="${DOCGEN_SSH_BIN:-ssh}"
PREVIEW="${DOCGEN_PREVIEW:-0}"
REPACKAGE="${DOCGEN_REPACKAGE:-0}"

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

require_file() {
  local path="$1"
  [[ -e "$path" ]] || fail "missing required file: $path"
}

if [[ -z "$REMOTE_HOST" ]]; then
  echo "[ERROR] usage: $0 <user@host>" >&2
  echo "        example: $0 root@199.180.118.204" >&2
  exit 1
fi

if [[ "$REPACKAGE" = "1" ]]; then
  bash "$ROOT/scripts/package_docgen_server_app.sh" "$LOCAL_RELEASE_DIR"
fi

LATEST_RELEASE_PATH="${LOCAL_RELEASE_DIR%/}/latest-release.txt"
LATEST_SUMMARY_PATH="${LOCAL_RELEASE_DIR%/}/latest-change-summary.txt"
LATEST_NOTES_PATH="${LOCAL_RELEASE_DIR%/}/latest-release-notes.txt"
LATEST_OPS_PATH="${LOCAL_RELEASE_DIR%/}/latest-release-ops.txt"
LATEST_ARCHIVE_PATH="${LOCAL_RELEASE_DIR%/}/docgen-server-app.tgz"
LATEST_CHECKSUM_PATH="${LATEST_ARCHIVE_PATH}.sha256"
LATEST_MANIFEST_PATH="${LOCAL_RELEASE_DIR%/}/docgen-server-app.manifest.json"
RELEASES_INDEX_PATH="${LOCAL_RELEASE_DIR%/}/releases-index.txt"

require_file "$LATEST_RELEASE_PATH"
require_file "$LATEST_SUMMARY_PATH"
require_file "$LATEST_NOTES_PATH"
require_file "$LATEST_OPS_PATH"
require_file "$LATEST_ARCHIVE_PATH"
require_file "$LATEST_CHECKSUM_PATH"
require_file "$LATEST_MANIFEST_PATH"
require_file "$RELEASES_INDEX_PATH"

VERSIONED_ARCHIVE_BASENAME="$(cat "$LATEST_RELEASE_PATH")"
[[ -n "$VERSIONED_ARCHIVE_BASENAME" ]] || fail "latest-release.txt is empty"

VERSIONED_ARCHIVE_PATH="${LOCAL_RELEASE_DIR%/}/${VERSIONED_ARCHIVE_BASENAME}"
VERSIONED_CHECKSUM_BASENAME="${VERSIONED_ARCHIVE_BASENAME}.sha256"
VERSIONED_CHECKSUM_PATH="${LOCAL_RELEASE_DIR%/}/${VERSIONED_CHECKSUM_BASENAME}"
VERSIONED_MANIFEST_BASENAME="${VERSIONED_ARCHIVE_BASENAME%.tgz}.manifest.json"
VERSIONED_MANIFEST_PATH="${LOCAL_RELEASE_DIR%/}/${VERSIONED_MANIFEST_BASENAME}"
VERSIONED_SUMMARY_BASENAME="${VERSIONED_ARCHIVE_BASENAME%.tgz}.summary.txt"
VERSIONED_SUMMARY_PATH="${LOCAL_RELEASE_DIR%/}/${VERSIONED_SUMMARY_BASENAME}"
VERSIONED_NOTES_BASENAME="${VERSIONED_ARCHIVE_BASENAME%.tgz}.notes.txt"
VERSIONED_NOTES_PATH="${LOCAL_RELEASE_DIR%/}/${VERSIONED_NOTES_BASENAME}"
VERSIONED_OPS_BASENAME="${VERSIONED_ARCHIVE_BASENAME%.tgz}.ops.txt"
VERSIONED_OPS_PATH="${LOCAL_RELEASE_DIR%/}/${VERSIONED_OPS_BASENAME}"

require_file "$VERSIONED_ARCHIVE_PATH"
require_file "$VERSIONED_CHECKSUM_PATH"
require_file "$VERSIONED_MANIFEST_PATH"
require_file "$VERSIONED_SUMMARY_PATH"
require_file "$VERSIONED_NOTES_PATH"
require_file "$VERSIONED_OPS_PATH"

files_to_upload=(
  "$VERSIONED_ARCHIVE_PATH"
  "$VERSIONED_CHECKSUM_PATH"
  "$VERSIONED_MANIFEST_PATH"
  "$VERSIONED_SUMMARY_PATH"
  "$VERSIONED_NOTES_PATH"
  "$VERSIONED_OPS_PATH"
  "$LATEST_RELEASE_PATH"
  "$LATEST_SUMMARY_PATH"
  "$LATEST_NOTES_PATH"
  "$LATEST_OPS_PATH"
  "$RELEASES_INDEX_PATH"
)

scp_cmd=("$SCP_BIN")
ssh_cmd=("$SSH_BIN")
if [[ -n "$SSH_OPTS" ]]; then
  # shellcheck disable=SC2206
  ssh_opts_parts=($SSH_OPTS)
  scp_cmd+=("${ssh_opts_parts[@]}")
  ssh_cmd+=("${ssh_opts_parts[@]}")
fi
scp_cmd+=("${files_to_upload[@]}" "${REMOTE_HOST}:${REMOTE_RELEASE_DIR}/")

remote_cmd=$(cat <<EOF
set -euo pipefail
mkdir -p ${REMOTE_RELEASE_DIR}
cd ${REMOTE_RELEASE_DIR}
ln -sfn ${VERSIONED_ARCHIVE_BASENAME} docgen-server-app.tgz
ln -sfn ${VERSIONED_CHECKSUM_BASENAME} docgen-server-app.tgz.sha256
ln -sfn ${VERSIONED_MANIFEST_BASENAME} docgen-server-app.manifest.json
sha256sum -c docgen-server-app.tgz.sha256
EOF
)
ssh_cmd+=("$REMOTE_HOST" "$remote_cmd")

if [[ "$PREVIEW" = "1" ]]; then
  printf 'remote_host=%s\n' "$REMOTE_HOST"
  printf 'local_release_dir=%s\n' "$LOCAL_RELEASE_DIR"
  printf 'remote_release_dir=%s\n' "$REMOTE_RELEASE_DIR"
  printf 'latest_release=%s\n' "$VERSIONED_ARCHIVE_BASENAME"
  printf 'scp_bin=%s\n' "$SCP_BIN"
  printf 'ssh_bin=%s\n' "$SSH_BIN"
  printf 'scp_command=%s\n' "$(format_command "${scp_cmd[@]}")"
  printf 'ssh_command=%s\n' "$(format_command "${ssh_cmd[@]}")"
  exit 0
fi

"${scp_cmd[@]}"
"${ssh_cmd[@]}"

echo "[OK] release uploaded: ${VERSIONED_ARCHIVE_BASENAME} -> ${REMOTE_HOST}:${REMOTE_RELEASE_DIR}"
