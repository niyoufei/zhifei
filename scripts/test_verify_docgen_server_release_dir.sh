#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_docgen_server_release_dir.sh"
TMP_DIR="$(mktemp -d)"
RELEASE_DIR="$TMP_DIR/release"
OUTPUT="$TMP_DIR/output.log"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

assert_contains() {
  local needle="$1"
  local file="$2"
  if ! grep -Fq -- "$needle" "$file"; then
    echo "[FAIL] missing expected text: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

mkdir -p "$RELEASE_DIR"
ARCHIVE_BASENAME="docgen-server-app-20260401-142647.tgz"
CHECKSUM_BASENAME="${ARCHIVE_BASENAME}.sha256"
MANIFEST_BASENAME="docgen-server-app-20260401-142647.manifest.json"
SUMMARY_BASENAME="docgen-server-app-20260401-142647.summary.txt"
NOTES_BASENAME="docgen-server-app-20260401-142647.notes.txt"
OPS_BASENAME="docgen-server-app-20260401-142647.ops.txt"

printf 'payload\n' > "$RELEASE_DIR/$ARCHIVE_BASENAME"
CHECKSUM_VALUE="$(shasum -a 256 "$RELEASE_DIR/$ARCHIVE_BASENAME" | awk '{print $1}')"
printf '%s  %s\n' "$CHECKSUM_VALUE" "$ARCHIVE_BASENAME" > "$RELEASE_DIR/$CHECKSUM_BASENAME"
cat > "$RELEASE_DIR/$MANIFEST_BASENAME" <<EOF
{
  "release_id": "20260401-142647",
  "archive": "$ARCHIVE_BASENAME",
  "checksum_file": "$CHECKSUM_BASENAME",
  "summary_file": "$SUMMARY_BASENAME",
  "notes_file": "$NOTES_BASENAME",
  "ops_file": "$OPS_BASENAME",
  "release_tools": [
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
    "scripts/prune_docgen_server_readonly_inspection_logs.sh"
  ],
  "operator_release_tools": [
    "scripts/package_docgen_server_app.sh",
    "scripts/push_docgen_server_release.sh",
    "scripts/push_docgen_server_worktree_scripts.sh",
    "scripts/verify_remote_docgen_server_release_dir.sh",
    "scripts/verify_remote_docgen_server_status.sh",
    "scripts/verify_remote_docgen_server_readonly_inspection.sh",
    "scripts/verify_remote_docgen_server_readonly_retention.sh"
  ],
  "server_release_tools": [
    "scripts/verify_docgen_server_release_dir.sh",
    "scripts/verify_docgen_server_worktree_scripts.sh",
    "scripts/show_docgen_server_status.sh",
    "scripts/report_docgen_server_readonly_inspection.sh",
    "scripts/report_docgen_server_readonly_retention.sh",
    "scripts/prune_docgen_server_readonly_inspection_logs.sh"
  ]
}
EOF
cat > "$RELEASE_DIR/$SUMMARY_BASENAME" <<EOF
release_id=20260401-142647
archive=$ARCHIVE_BASENAME
operator_release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh
server_release_tools=scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh
release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/show_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh
EOF
cat > "$RELEASE_DIR/$NOTES_BASENAME" <<'EOF'
release_id=20260401-142647
impact_scope=tooling-only
operator_action=sync-scripts
EOF
cat > "$RELEASE_DIR/$OPS_BASENAME" <<'EOF'
release_id=20260401-142647
archive=docgen-server-app-20260401-142647.tgz
bash ./scripts/push_docgen_server_release.sh root@199.180.118.204
bash ./scripts/push_docgen_server_worktree_scripts.sh root@199.180.118.204
bash ./scripts/verify_docgen_server_release_dir.sh /opt/docgen/releases
ssh root@199.180.118.204 'bash /opt/docgen/scripts/verify_docgen_server_worktree_scripts.sh /opt/docgen /opt/docgen/releases'
bash ./scripts/verify_remote_docgen_server_release_dir.sh root@199.180.118.204
bash ./scripts/verify_remote_docgen_server_status.sh root@199.180.118.204
bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh root@199.180.118.204
bash ./scripts/verify_remote_docgen_server_readonly_retention.sh root@199.180.118.204
ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_inspection/latest-status.txt'
ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_retention/latest-status.txt'
ssh root@199.180.118.204 'DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 bash /opt/docgen/scripts/prune_docgen_server_readonly_inspection_logs.sh /opt/docgen/logs/readonly_inspection'
ssh root@199.180.118.204 'DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 DOCGEN_PRUNE_CONFIRM_RUN_ID=<retention_run_id> DOCGEN_PRUNE_CONFIRM_CANDIDATES=<candidate_csv> DOCGEN_PRUNE_EXECUTE=1 bash /opt/docgen/scripts/prune_docgen_server_readonly_inspection_logs.sh /opt/docgen/logs/readonly_inspection'
Execute is refused when prune_candidates=none.
EOF
printf '%s\n' "$ARCHIVE_BASENAME" > "$RELEASE_DIR/latest-release.txt"
cp "$RELEASE_DIR/$SUMMARY_BASENAME" "$RELEASE_DIR/latest-change-summary.txt"
cp "$RELEASE_DIR/$NOTES_BASENAME" "$RELEASE_DIR/latest-release-notes.txt"
cp "$RELEASE_DIR/$OPS_BASENAME" "$RELEASE_DIR/latest-release-ops.txt"
printf '%s\n' "$ARCHIVE_BASENAME" > "$RELEASE_DIR/releases-index.txt"
ln -s "$ARCHIVE_BASENAME" "$RELEASE_DIR/docgen-server-app.tgz"
ln -s "$CHECKSUM_BASENAME" "$RELEASE_DIR/docgen-server-app.tgz.sha256"
ln -s "$MANIFEST_BASENAME" "$RELEASE_DIR/docgen-server-app.manifest.json"

bash "$VERIFY_SCRIPT" "$RELEASE_DIR" >"$OUTPUT" 2>&1

assert_contains "[OK] release_dir=$RELEASE_DIR" "$OUTPUT"
assert_contains "[OK] latest release pointer: $ARCHIVE_BASENAME" "$OUTPUT"
assert_contains "[OK] latest symlinks: archive/checksum/manifest match versioned files" "$OUTPUT"
assert_contains "[OK] manifest fields: release_id/archive/checksum/summary/notes/ops match latest release" "$OUTPUT"
assert_contains "[OK] latest summary: release id, archive and release tools match" "$OUTPUT"
assert_contains "[OK] latest notes: release id and operator metadata present" "$OUTPUT"
assert_contains "[OK] latest ops: sync and release verify commands present" "$OUTPUT"
assert_contains "[OK] releases index: contains latest release" "$OUTPUT"
assert_contains "[OK] checksum: $CHECKSUM_VALUE" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

echo "[PASS] verify_docgen_server_release_dir regression checks passed"
