#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="${DOCGEN_PROJECT_ROOT:-$ROOT}"
REMOTE_HOST="${1:-${DOCGEN_RELEASE_HOST:-}}"
LOCAL_RELEASE_DIR="${DOCGEN_LOCAL_RELEASE_DIR:-$PROJECT_ROOT/build/server_app_bundle}"
REMOTE_APP_DIR="${DOCGEN_REMOTE_APP_DIR:-/opt/docgen}"
REMOTE_SCRIPTS_DIR="${DOCGEN_REMOTE_SCRIPTS_DIR:-${REMOTE_APP_DIR%/}/scripts}"
REMOTE_RELEASE_DIR="${DOCGEN_REMOTE_RELEASE_DIR:-${REMOTE_APP_DIR%/}/releases}"
SSH_OPTS="${DOCGEN_SSH_OPTS:-}"
SCP_BIN="${DOCGEN_SCP_BIN:-scp}"
SSH_BIN="${DOCGEN_SSH_BIN:-ssh}"
PREVIEW="${DOCGEN_PREVIEW:-0}"
BACKUP_SUFFIX="${DOCGEN_BACKUP_SUFFIX:-bak.codex-$(date -u +%Y%m%d-%H%M%S)-server-worktree-sync}"
MANIFEST_PATH="${DOCGEN_MANIFEST_PATH:-${LOCAL_RELEASE_DIR%/}/docgen-server-app.manifest.json}"

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
  [[ -f "$path" ]] || fail "missing required file: $path"
}

if [[ -z "$REMOTE_HOST" ]]; then
  echo "[ERROR] usage: $0 <user@host>" >&2
  echo "        example: $0 root@199.180.118.204" >&2
  exit 1
fi

require_file "$MANIFEST_PATH"

WORKTREE_REL_PATHS=()
while IFS= read -r line; do
  [[ -n "$line" ]] || continue
  WORKTREE_REL_PATHS+=("$line")
done < <(python3 - "$MANIFEST_PATH" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
ordered = []
seen = set()
for group in ("runtime_probes", "server_release_tools"):
    for item in payload.get(group, []) or []:
        if not isinstance(item, str) or not item.startswith("scripts/"):
            raise SystemExit(f"[ERROR] invalid server worktree script entry in {group}: {item!r}")
        if item not in seen:
            seen.add(item)
            ordered.append(item)
for item in ordered:
    print(item)
PY
)

[[ ${#WORKTREE_REL_PATHS[@]} -gt 0 ]] || fail "manifest does not define any server worktree scripts"

local_files=()
remote_basenames=()
for rel in "${WORKTREE_REL_PATHS[@]}"; do
  local_path="${PROJECT_ROOT%/}/${rel}"
  require_file "$local_path"
  local_files+=("$local_path")
  remote_basenames+=("${rel##*/}")
done

scp_cmd=("$SCP_BIN")
ssh_prepare_cmd=("$SSH_BIN")
ssh_finalize_cmd=("$SSH_BIN")
if [[ -n "$SSH_OPTS" ]]; then
  # shellcheck disable=SC2206
  ssh_opts_parts=($SSH_OPTS)
  scp_cmd+=("${ssh_opts_parts[@]}")
  ssh_prepare_cmd+=("${ssh_opts_parts[@]}")
  ssh_finalize_cmd+=("${ssh_opts_parts[@]}")
fi

scp_cmd+=("${local_files[@]}" "${REMOTE_HOST}:${REMOTE_SCRIPTS_DIR}/")

prepare_remote_cmd=$(
  {
    printf 'set -euo pipefail\n'
    printf 'mkdir -p %s\n' "$REMOTE_SCRIPTS_DIR"
    printf 'cd %s\n' "$REMOTE_SCRIPTS_DIR"
    printf 'backup_suffix=%q\n' "$BACKUP_SUFFIX"
    for base in "${remote_basenames[@]}"; do
      printf 'if [ -e %q ]; then cp %q %q.${backup_suffix}; fi\n' "$base" "$base" "$base"
    done
  }
)
ssh_prepare_cmd+=("$REMOTE_HOST" "$prepare_remote_cmd")

finalize_remote_cmd=$(
  {
    printf 'set -euo pipefail\n'
    printf 'cd %s\n' "$REMOTE_SCRIPTS_DIR"
    for base in "${remote_basenames[@]}"; do
      printf 'chown root:root %q\n' "$base"
      printf 'chmod 755 %q\n' "$base"
    done
    printf 'bash %q %q %q\n' "${REMOTE_SCRIPTS_DIR%/}/verify_docgen_server_worktree_scripts.sh" "$REMOTE_APP_DIR" "$REMOTE_RELEASE_DIR"
  }
)
ssh_finalize_cmd+=("$REMOTE_HOST" "$finalize_remote_cmd")

if [[ "$PREVIEW" = "1" ]]; then
  printf 'remote_host=%s\n' "$REMOTE_HOST"
  printf 'project_root=%s\n' "$PROJECT_ROOT"
  printf 'local_release_dir=%s\n' "$LOCAL_RELEASE_DIR"
  printf 'remote_app_dir=%s\n' "$REMOTE_APP_DIR"
  printf 'remote_scripts_dir=%s\n' "$REMOTE_SCRIPTS_DIR"
  printf 'remote_release_dir=%s\n' "$REMOTE_RELEASE_DIR"
  printf 'manifest_path=%s\n' "$MANIFEST_PATH"
  printf 'backup_suffix=%s\n' "$BACKUP_SUFFIX"
  printf 'server_worktree_scripts_count=%s\n' "${#WORKTREE_REL_PATHS[@]}"
  printf 'server_worktree_scripts=%s\n' "$(IFS=,; echo "${WORKTREE_REL_PATHS[*]}")"
  printf 'ssh_prepare_command=%s\n' "$(format_command "${ssh_prepare_cmd[@]}")"
  printf 'scp_command=%s\n' "$(format_command "${scp_cmd[@]}")"
  printf 'ssh_finalize_command=%s\n' "$(format_command "${ssh_finalize_cmd[@]}")"
  exit 0
fi

"${ssh_prepare_cmd[@]}"
"${scp_cmd[@]}"
"${ssh_finalize_cmd[@]}"

echo "[OK] server worktree scripts uploaded: ${REMOTE_HOST}:${REMOTE_SCRIPTS_DIR}"
echo "[OK] server worktree scripts count: ${#WORKTREE_REL_PATHS[@]}"
