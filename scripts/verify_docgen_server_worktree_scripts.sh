#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${1:-${DOCGEN_APP_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}}"
RELEASE_DIR="${2:-${DOCGEN_RELEASE_DIR:-${APP_ROOT%/}/releases}}"
MANIFEST_PATH="${DOCGEN_MANIFEST_PATH:-${RELEASE_DIR%/}/docgen-server-app.manifest.json}"

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing file: $path"
}

require_file "$MANIFEST_PATH"

REQUIRED_SCRIPTS=()
while IFS= read -r line; do
  [[ -n "$line" ]] || continue
  REQUIRED_SCRIPTS+=("$line")
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

[[ ${#REQUIRED_SCRIPTS[@]} -gt 0 ]] || fail "manifest does not define any server worktree scripts"

missing=()
nonexec=()
for rel in "${REQUIRED_SCRIPTS[@]}"; do
  abs="${APP_ROOT%/}/${rel}"
  if [[ ! -f "$abs" ]]; then
    missing+=("$rel")
    continue
  fi
  if [[ ! -x "$abs" ]]; then
    nonexec+=("$rel")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  fail "missing server worktree scripts: $(IFS=,; echo "${missing[*]}")"
fi

if [[ ${#nonexec[@]} -gt 0 ]]; then
  fail "non-executable server worktree scripts: $(IFS=,; echo "${nonexec[*]}")"
fi

echo "[OK] app_root=${APP_ROOT}"
echo "[OK] release_dir=${RELEASE_DIR}"
echo "[OK] manifest_path=${MANIFEST_PATH}"
echo "[OK] server_worktree_scripts_count=${#REQUIRED_SCRIPTS[@]}"
echo "[OK] server_worktree_scripts=$(IFS=,; echo "${REQUIRED_SCRIPTS[*]}")"
echo "[SUMMARY] all checks passed."
