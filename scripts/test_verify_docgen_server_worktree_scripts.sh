#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERIFY_SCRIPT="$ROOT/scripts/verify_docgen_server_worktree_scripts.sh"
TMP_DIR="$(mktemp -d)"
APP_ROOT="$TMP_DIR/app"
RELEASE_DIR="$APP_ROOT/releases"
SCRIPTS_DIR="$APP_ROOT/scripts"
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

mkdir -p "$RELEASE_DIR" "$SCRIPTS_DIR"
cat > "$RELEASE_DIR/docgen-server-app.manifest.json" <<'EOF'
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
  cat > "$SCRIPTS_DIR/$script" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
  chmod 755 "$SCRIPTS_DIR/$script"
done

bash "$VERIFY_SCRIPT" "$APP_ROOT" "$RELEASE_DIR" >"$OUTPUT" 2>&1

assert_contains "[OK] app_root=$APP_ROOT" "$OUTPUT"
assert_contains "[OK] release_dir=$RELEASE_DIR" "$OUTPUT"
assert_contains "[OK] manifest_path=$RELEASE_DIR/docgen-server-app.manifest.json" "$OUTPUT"
assert_contains "[OK] server_worktree_scripts_count=8" "$OUTPUT"
assert_contains "scripts/verify_origin_app_health.sh,scripts/verify_upload_parse_chain.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

echo "[PASS] verify_docgen_server_worktree_scripts regression checks passed"
