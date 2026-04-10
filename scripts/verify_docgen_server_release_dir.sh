#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE_DIR="${1:-${DOCGEN_RELEASE_DIR:-$ROOT/build/server_app_bundle}}"

fail() {
  echo "[ERROR] $*" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing file: $path"
}

require_link() {
  local path="$1"
  [[ -L "$path" ]] || fail "missing symlink: $path"
}

assert_contains() {
  local needle="$1"
  local file="$2"
  if ! grep -Fq -- "$needle" "$file"; then
    fail "missing expected text '$needle' in $file"
  fi
}

sha256_value() {
  local path="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
    return
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
    return
  fi
  fail "missing checksum tool: sha256sum or shasum"
}

LATEST_RELEASE_PATH="${RELEASE_DIR%/}/latest-release.txt"
LATEST_SUMMARY_PATH="${RELEASE_DIR%/}/latest-change-summary.txt"
LATEST_NOTES_PATH="${RELEASE_DIR%/}/latest-release-notes.txt"
LATEST_OPS_PATH="${RELEASE_DIR%/}/latest-release-ops.txt"
LATEST_ARCHIVE_PATH="${RELEASE_DIR%/}/docgen-server-app.tgz"
LATEST_CHECKSUM_PATH="${LATEST_ARCHIVE_PATH}.sha256"
LATEST_MANIFEST_PATH="${RELEASE_DIR%/}/docgen-server-app.manifest.json"
RELEASES_INDEX_PATH="${RELEASE_DIR%/}/releases-index.txt"

require_file "$LATEST_RELEASE_PATH"
require_file "$LATEST_SUMMARY_PATH"
require_file "$LATEST_NOTES_PATH"
require_file "$LATEST_OPS_PATH"
require_file "$RELEASES_INDEX_PATH"
require_link "$LATEST_ARCHIVE_PATH"
require_link "$LATEST_CHECKSUM_PATH"
require_link "$LATEST_MANIFEST_PATH"

VERSIONED_ARCHIVE_BASENAME="$(cat "$LATEST_RELEASE_PATH")"
[[ -n "$VERSIONED_ARCHIVE_BASENAME" ]] || fail "latest-release.txt is empty"

case "$VERSIONED_ARCHIVE_BASENAME" in
  docgen-server-app-*.tgz) ;;
  *) fail "unexpected latest release basename: $VERSIONED_ARCHIVE_BASENAME" ;;
esac

RELEASE_ID="${VERSIONED_ARCHIVE_BASENAME#docgen-server-app-}"
RELEASE_ID="${RELEASE_ID%.tgz}"
VERSIONED_CHECKSUM_BASENAME="${VERSIONED_ARCHIVE_BASENAME}.sha256"
VERSIONED_MANIFEST_BASENAME="docgen-server-app-${RELEASE_ID}.manifest.json"
VERSIONED_SUMMARY_BASENAME="docgen-server-app-${RELEASE_ID}.summary.txt"
VERSIONED_NOTES_BASENAME="docgen-server-app-${RELEASE_ID}.notes.txt"
VERSIONED_OPS_BASENAME="docgen-server-app-${RELEASE_ID}.ops.txt"

VERSIONED_ARCHIVE_PATH="${RELEASE_DIR%/}/${VERSIONED_ARCHIVE_BASENAME}"
VERSIONED_CHECKSUM_PATH="${RELEASE_DIR%/}/${VERSIONED_CHECKSUM_BASENAME}"
VERSIONED_MANIFEST_PATH="${RELEASE_DIR%/}/${VERSIONED_MANIFEST_BASENAME}"
VERSIONED_SUMMARY_PATH="${RELEASE_DIR%/}/${VERSIONED_SUMMARY_BASENAME}"
VERSIONED_NOTES_PATH="${RELEASE_DIR%/}/${VERSIONED_NOTES_BASENAME}"
VERSIONED_OPS_PATH="${RELEASE_DIR%/}/${VERSIONED_OPS_BASENAME}"

require_file "$VERSIONED_ARCHIVE_PATH"
require_file "$VERSIONED_CHECKSUM_PATH"
require_file "$VERSIONED_MANIFEST_PATH"
require_file "$VERSIONED_SUMMARY_PATH"
require_file "$VERSIONED_NOTES_PATH"
require_file "$VERSIONED_OPS_PATH"

ARCHIVE_LINK_TARGET="$(readlink "$LATEST_ARCHIVE_PATH")"
CHECKSUM_LINK_TARGET="$(readlink "$LATEST_CHECKSUM_PATH")"
MANIFEST_LINK_TARGET="$(readlink "$LATEST_MANIFEST_PATH")"

[[ "$ARCHIVE_LINK_TARGET" = "$VERSIONED_ARCHIVE_BASENAME" ]] || fail "latest archive link mismatch: $ARCHIVE_LINK_TARGET"
[[ "$CHECKSUM_LINK_TARGET" = "$VERSIONED_CHECKSUM_BASENAME" ]] || fail "latest checksum link mismatch: $CHECKSUM_LINK_TARGET"
[[ "$MANIFEST_LINK_TARGET" = "$VERSIONED_MANIFEST_BASENAME" ]] || fail "latest manifest link mismatch: $MANIFEST_LINK_TARGET"

echo "[OK] release_dir=$RELEASE_DIR"
echo "[OK] latest release pointer: $VERSIONED_ARCHIVE_BASENAME"
echo "[OK] latest symlinks: archive/checksum/manifest match versioned files"

python3 - "$VERSIONED_MANIFEST_PATH" "$RELEASE_ID" "$VERSIONED_ARCHIVE_BASENAME" "$VERSIONED_CHECKSUM_BASENAME" "$VERSIONED_SUMMARY_BASENAME" "$VERSIONED_NOTES_BASENAME" "$VERSIONED_OPS_BASENAME" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
release_id, archive, checksum_file, summary_file, notes_file, ops_file = sys.argv[2:]
payload = json.loads(manifest_path.read_text(encoding="utf-8"))

expected = {
    "release_id": release_id,
    "archive": archive,
    "checksum_file": checksum_file,
    "summary_file": summary_file,
    "notes_file": notes_file,
    "ops_file": ops_file,
}
for key, value in expected.items():
    actual = payload.get(key)
    if actual != value:
        raise SystemExit(f"[ERROR] manifest mismatch for {key}: expected={value} actual={actual}")

release_tools = payload.get("release_tools") or []
operator_release_tools = payload.get("operator_release_tools") or []
server_release_tools = payload.get("server_release_tools") or []
required_tools = {
    "scripts/package_docgen_server_app.sh",
    "scripts/push_docgen_server_release.sh",
    "scripts/push_docgen_server_worktree_scripts.sh",
    "scripts/verify_docgen_server_release_dir.sh",
    "scripts/verify_docgen_server_worktree_scripts.sh",
    "scripts/verify_remote_docgen_server_release_dir.sh",
    "scripts/verify_remote_docgen_server_status.sh",
    "scripts/show_docgen_server_status.sh",
    "scripts/verify_remote_docgen_server_readonly_inspection.sh",
    "scripts/verify_remote_docgen_server_readonly_retention.sh",
    "scripts/report_docgen_server_readonly_inspection.sh",
    "scripts/report_docgen_server_readonly_retention.sh",
    "scripts/prune_docgen_server_readonly_inspection_logs.sh",
}
required_operator_tools = {
    "scripts/package_docgen_server_app.sh",
    "scripts/push_docgen_server_release.sh",
    "scripts/push_docgen_server_worktree_scripts.sh",
    "scripts/verify_remote_docgen_server_release_dir.sh",
    "scripts/verify_remote_docgen_server_status.sh",
    "scripts/verify_remote_docgen_server_readonly_inspection.sh",
    "scripts/verify_remote_docgen_server_readonly_retention.sh",
}
required_server_tools = {
    "scripts/verify_docgen_server_release_dir.sh",
    "scripts/verify_docgen_server_worktree_scripts.sh",
    "scripts/show_docgen_server_status.sh",
    "scripts/report_docgen_server_readonly_inspection.sh",
    "scripts/report_docgen_server_readonly_retention.sh",
    "scripts/prune_docgen_server_readonly_inspection_logs.sh",
}
missing = sorted(required_tools.difference(release_tools))
if missing:
    raise SystemExit(f"[ERROR] manifest missing release_tools: {','.join(missing)}")
missing_operator = sorted(required_operator_tools.difference(operator_release_tools))
if missing_operator:
    raise SystemExit(f"[ERROR] manifest missing operator_release_tools: {','.join(missing_operator)}")
missing_server = sorted(required_server_tools.difference(server_release_tools))
if missing_server:
    raise SystemExit(f"[ERROR] manifest missing server_release_tools: {','.join(missing_server)}")
PY

echo "[OK] manifest fields: release_id/archive/checksum/summary/notes/ops match latest release"

assert_contains "release_id=${RELEASE_ID}" "$LATEST_SUMMARY_PATH"
assert_contains "archive=${VERSIONED_ARCHIVE_BASENAME}" "$LATEST_SUMMARY_PATH"
assert_contains "operator_release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh" "$LATEST_SUMMARY_PATH"
assert_contains "server_release_tools=scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$LATEST_SUMMARY_PATH"
assert_contains "release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/show_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$LATEST_SUMMARY_PATH"
echo "[OK] latest summary: release id, archive and release tools match"

assert_contains "release_id=${RELEASE_ID}" "$LATEST_NOTES_PATH"
assert_contains "impact_scope=" "$LATEST_NOTES_PATH"
assert_contains "operator_action=" "$LATEST_NOTES_PATH"
echo "[OK] latest notes: release id and operator metadata present"

assert_contains "release_id=${RELEASE_ID}" "$LATEST_OPS_PATH"
assert_contains "archive=${VERSIONED_ARCHIVE_BASENAME}" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/push_docgen_server_release.sh" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/push_docgen_server_worktree_scripts.sh" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_docgen_server_release_dir.sh" "$LATEST_OPS_PATH"
assert_contains "verify_docgen_server_worktree_scripts.sh /opt/docgen /opt/docgen/releases" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_release_dir.sh" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_status.sh" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_readonly_retention.sh" "$LATEST_OPS_PATH"
assert_contains "logs/readonly_inspection/latest-status.txt" "$LATEST_OPS_PATH"
assert_contains "logs/readonly_retention/latest-status.txt" "$LATEST_OPS_PATH"
assert_contains "prune_docgen_server_readonly_inspection_logs.sh" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PRUNE_CONFIRM_RUN_ID=<retention_run_id>" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PRUNE_CONFIRM_CANDIDATES=<candidate_csv>" "$LATEST_OPS_PATH"
assert_contains "Execute is refused when prune_candidates=none." "$LATEST_OPS_PATH"
echo "[OK] latest ops: sync and release verify commands present"

assert_contains "$VERSIONED_ARCHIVE_BASENAME" "$RELEASES_INDEX_PATH"
echo "[OK] releases index: contains latest release"

EXPECTED_CHECKSUM="$(awk '{print $1}' "$VERSIONED_CHECKSUM_PATH")"
ACTUAL_CHECKSUM="$(sha256_value "$VERSIONED_ARCHIVE_PATH")"
[[ "$EXPECTED_CHECKSUM" = "$ACTUAL_CHECKSUM" ]] || fail "checksum mismatch: expected=$EXPECTED_CHECKSUM actual=$ACTUAL_CHECKSUM"
echo "[OK] checksum: $ACTUAL_CHECKSUM"

echo "[SUMMARY] all checks passed."
