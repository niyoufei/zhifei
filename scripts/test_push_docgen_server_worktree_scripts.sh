#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUSH_SCRIPT="$ROOT/scripts/push_docgen_server_worktree_scripts.sh"
TMP_DIR="$(mktemp -d)"
PROJECT_ROOT="$TMP_DIR/project"
LOCAL_RELEASE_DIR="$TMP_DIR/release"
CALLS="$TMP_DIR/calls.log"

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

mkdir -p "$PROJECT_ROOT/scripts" "$LOCAL_RELEASE_DIR"
for script in \
  verify_origin_app_health.sh \
  verify_upload_parse_chain.sh \
  verify_docgen_server_release_dir.sh \
  verify_docgen_server_worktree_scripts.sh \
  show_docgen_server_status.sh \
  report_docgen_server_readonly_inspection.sh \
  report_docgen_server_readonly_retention.sh \
  prune_docgen_server_readonly_inspection_logs.sh
do
  cat > "$PROJECT_ROOT/scripts/$script" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
done

cat > "$LOCAL_RELEASE_DIR/docgen-server-app.manifest.json" <<'EOF'
{
  "runtime_probes": [
    "scripts/verify_origin_app_health.sh",
    "scripts/verify_upload_parse_chain.sh"
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

cat > "$TMP_DIR/mock-scp" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'scp %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-scp"

cat > "$TMP_DIR/mock-ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ssh %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-ssh"

OUTPUT="$TMP_DIR/output.log"
DOCGEN_PROJECT_ROOT="$PROJECT_ROOT" \
DOCGEN_LOCAL_RELEASE_DIR="$LOCAL_RELEASE_DIR" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_TEST_CALLS="$CALLS" \
DOCGEN_BACKUP_SUFFIX="bak.codex-test-server-worktree-sync" \
bash "$PUSH_SCRIPT" "root@example.com" >"$OUTPUT" 2>&1

assert_contains "[OK] server worktree scripts uploaded: root@example.com:/opt/docgen/scripts" "$OUTPUT"
assert_contains "[OK] server worktree scripts count: 8" "$OUTPUT"
assert_contains "ssh root@example.com set -euo pipefail" "$CALLS"
assert_contains "cp verify_origin_app_health.sh verify_origin_app_health.sh.\${backup_suffix}" "$CALLS"
assert_contains "scp $PROJECT_ROOT/scripts/verify_origin_app_health.sh $PROJECT_ROOT/scripts/verify_upload_parse_chain.sh $PROJECT_ROOT/scripts/verify_docgen_server_release_dir.sh $PROJECT_ROOT/scripts/verify_docgen_server_worktree_scripts.sh $PROJECT_ROOT/scripts/show_docgen_server_status.sh $PROJECT_ROOT/scripts/report_docgen_server_readonly_inspection.sh $PROJECT_ROOT/scripts/report_docgen_server_readonly_retention.sh $PROJECT_ROOT/scripts/prune_docgen_server_readonly_inspection_logs.sh root@example.com:/opt/docgen/scripts/" "$CALLS"
assert_contains "chown root:root verify_docgen_server_worktree_scripts.sh" "$CALLS"
assert_contains "bash /opt/docgen/scripts/verify_docgen_server_worktree_scripts.sh /opt/docgen /opt/docgen/releases" "$CALLS"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_PREVIEW=1 \
DOCGEN_PROJECT_ROOT="$PROJECT_ROOT" \
DOCGEN_LOCAL_RELEASE_DIR="$LOCAL_RELEASE_DIR" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_BACKUP_SUFFIX="bak.codex-test-server-worktree-sync" \
bash "$PUSH_SCRIPT" "root@example.com" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "remote_host=root@example.com" "$PREVIEW_OUTPUT"
assert_contains "remote_scripts_dir=/opt/docgen/scripts" "$PREVIEW_OUTPUT"
assert_contains "server_worktree_scripts_count=8" "$PREVIEW_OUTPUT"
assert_contains "server_worktree_scripts=scripts/verify_origin_app_health.sh,scripts/verify_upload_parse_chain.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$PREVIEW_OUTPUT"
assert_contains "ssh_prepare_command=" "$PREVIEW_OUTPUT"
assert_contains "scp_command=" "$PREVIEW_OUTPUT"
assert_contains "ssh_finalize_command=" "$PREVIEW_OUTPUT"

echo "[PASS] push_docgen_server_worktree_scripts regression checks passed"
