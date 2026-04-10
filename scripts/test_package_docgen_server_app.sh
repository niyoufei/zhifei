#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PACKAGE_SCRIPT="$ROOT/scripts/package_docgen_server_app.sh"
TMP_DIR="$(mktemp -d)"
OUT_DIR="$TMP_DIR/out"
ARCHIVE_PATH="$OUT_DIR/docgen-server-app.tgz"
CHECKSUM_PATH="${ARCHIVE_PATH}.sha256"
MANIFEST_PATH="$OUT_DIR/docgen-server-app.manifest.json"
LATEST_RELEASE_PATH="$OUT_DIR/latest-release.txt"
RELEASES_INDEX_PATH="$OUT_DIR/releases-index.txt"
LATEST_SUMMARY_PATH="$OUT_DIR/latest-change-summary.txt"
LATEST_NOTES_PATH="$OUT_DIR/latest-release-notes.txt"
LATEST_OPS_PATH="$OUT_DIR/latest-release-ops.txt"
TAR_LIST="$TMP_DIR/tar.list"
EXPECTED_ROOTS_FILE="$TMP_DIR/expected_roots.txt"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

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

assert_not_contains() {
  local needle="$1"
  local file="$2"
  if grep -Fq -- "$needle" "$file"; then
    echo "[FAIL] unexpected text: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

compute_expected_roots() {
  local base_dir="$1"
  python3 - "$base_dir" <<'PY'
from pathlib import Path
import sys

base = Path(sys.argv[1])
candidates = [
    "app.py",
    "devserver.py",
    "requirements.txt",
    "rules_sample.json",
    ".env.example",
    ".gitignore",
    ".streamlit",
    "backend",
    "modules",
    "scripts",
    "deploy",
    "knowledge_graph",
    "知识图谱",
    "03_系统核心规则与字典",
]
roots = [item for item in candidates if (base / item).exists()]
print(",".join(roots))
PY
}

echo "[STEP] package server app bundle"
bash "$PACKAGE_SCRIPT" "$OUT_DIR" >/dev/null
compute_expected_roots "$ROOT" > "$EXPECTED_ROOTS_FILE"
EXPECTED_ROOTS_CSV="$(cat "$EXPECTED_ROOTS_FILE")"

[[ -f "$ARCHIVE_PATH" ]] || fail "missing archive: $ARCHIVE_PATH"
[[ -f "$CHECKSUM_PATH" ]] || fail "missing checksum: $CHECKSUM_PATH"
[[ -f "$MANIFEST_PATH" ]] || fail "missing manifest: $MANIFEST_PATH"
[[ -f "$LATEST_RELEASE_PATH" ]] || fail "missing latest release pointer: $LATEST_RELEASE_PATH"
[[ -f "$RELEASES_INDEX_PATH" ]] || fail "missing releases index: $RELEASES_INDEX_PATH"
[[ -f "$LATEST_SUMMARY_PATH" ]] || fail "missing latest summary: $LATEST_SUMMARY_PATH"
[[ -f "$LATEST_NOTES_PATH" ]] || fail "missing latest notes: $LATEST_NOTES_PATH"
[[ -f "$LATEST_OPS_PATH" ]] || fail "missing latest ops: $LATEST_OPS_PATH"
[[ -L "$ARCHIVE_PATH" ]] || fail "latest archive is not a symlink"
[[ -L "$CHECKSUM_PATH" ]] || fail "latest checksum is not a symlink"
[[ -L "$MANIFEST_PATH" ]] || fail "latest manifest is not a symlink"

VERSIONED_ARCHIVE_BASENAME="$(readlink "$ARCHIVE_PATH")"
VERSIONED_CHECKSUM_BASENAME="$(readlink "$CHECKSUM_PATH")"
VERSIONED_MANIFEST_BASENAME="$(readlink "$MANIFEST_PATH")"
VERSIONED_ARCHIVE_PATH="$OUT_DIR/$VERSIONED_ARCHIVE_BASENAME"
VERSIONED_CHECKSUM_PATH="$OUT_DIR/$VERSIONED_CHECKSUM_BASENAME"
VERSIONED_MANIFEST_PATH="$OUT_DIR/$VERSIONED_MANIFEST_BASENAME"

[[ -f "$VERSIONED_ARCHIVE_PATH" ]] || fail "missing versioned archive: $VERSIONED_ARCHIVE_PATH"
[[ -f "$VERSIONED_CHECKSUM_PATH" ]] || fail "missing versioned checksum: $VERSIONED_CHECKSUM_PATH"
[[ -f "$VERSIONED_MANIFEST_PATH" ]] || fail "missing versioned manifest: $VERSIONED_MANIFEST_PATH"
assert_contains "docgen-server-app-" <(printf '%s\n' "$VERSIONED_ARCHIVE_BASENAME")
assert_contains "$VERSIONED_ARCHIVE_BASENAME" "$VERSIONED_CHECKSUM_PATH"
assert_not_contains "$OUT_DIR" "$VERSIONED_CHECKSUM_PATH"
assert_contains "\"release_id\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"archive\": \"$VERSIONED_ARCHIVE_BASENAME\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"checksum_file\": \"$VERSIONED_CHECKSUM_BASENAME\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"summary_file\": \"docgen-server-app-" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"notes_file\": \"docgen-server-app-" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"ops_file\": \"docgen-server-app-" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"entrypoints\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"web\": \"app.py\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"api\": \"backend/app/main.py\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"runtime_probes\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_origin_app_health.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_public_edge_health.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_public_edge_health_stable.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/report_docgen_runtime_health.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/report_docgen_runtime_health_stable.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"operator_probes\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_ui_upload_outline_chain.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_ui_upload_outline_chain.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_full_chain.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"operator_release_tools\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/package_docgen_server_app.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/push_docgen_server_release.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/push_docgen_server_worktree_scripts.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_release_dir.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_status.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_readonly_inspection.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_readonly_retention.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"server_release_tools\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_docgen_server_release_dir.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_docgen_server_worktree_scripts.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/show_docgen_server_status.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/report_docgen_server_readonly_inspection.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/report_docgen_server_readonly_retention.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/prune_docgen_server_readonly_inspection_logs.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"release_tools\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/package_docgen_server_app.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/push_docgen_server_release.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/push_docgen_server_worktree_scripts.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_docgen_server_release_dir.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_docgen_server_worktree_scripts.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_release_dir.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_status.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/show_docgen_server_status.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_readonly_inspection.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_remote_docgen_server_readonly_retention.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/report_docgen_server_readonly_inspection.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/report_docgen_server_readonly_retention.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/prune_docgen_server_readonly_inspection_logs.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"included_roots\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_upload_parse_chain.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"scripts/verify_generate_export_chain.sh\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"rules_sample.json\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"modules\"" "$VERSIONED_MANIFEST_PATH"
assert_contains "\"included_roots\": [" "$VERSIONED_MANIFEST_PATH"
assert_contains "$VERSIONED_ARCHIVE_BASENAME" "$LATEST_RELEASE_PATH"
assert_contains "$VERSIONED_ARCHIVE_BASENAME" "$RELEASES_INDEX_PATH"
assert_contains "release_id=" "$LATEST_SUMMARY_PATH"
assert_contains "archive=$VERSIONED_ARCHIVE_BASENAME" "$LATEST_SUMMARY_PATH"
assert_contains "entrypoints=app.py,backend/app/main.py,scripts/run_web_ui.sh" "$LATEST_SUMMARY_PATH"
assert_contains "runtime_probes=scripts/verify_origin_app_health.sh,scripts/verify_public_edge_health.sh,scripts/verify_public_edge_health_stable.sh,scripts/report_docgen_runtime_health.sh,scripts/report_docgen_runtime_health_stable.sh,scripts/verify_linux_domain_origin.sh,scripts/verify_ocr_runtime.sh,scripts/verify_upload_parse_chain.sh,scripts/verify_generate_export_chain.sh" "$LATEST_SUMMARY_PATH"
assert_contains "operator_probes=scripts/verify_ui_upload_outline_chain.sh,scripts/verify_remote_ui_upload_outline_chain.sh,scripts/verify_remote_full_chain.sh" "$LATEST_SUMMARY_PATH"
assert_contains "operator_release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh" "$LATEST_SUMMARY_PATH"
assert_contains "server_release_tools=scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$LATEST_SUMMARY_PATH"
assert_contains "release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/show_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$LATEST_SUMMARY_PATH"
assert_contains "included_roots=$EXPECTED_ROOTS_CSV" "$LATEST_SUMMARY_PATH"
assert_contains "release_id=" "$LATEST_OPS_PATH"
assert_contains "archive=$VERSIONED_ARCHIVE_BASENAME" "$LATEST_OPS_PATH"
assert_contains "release_host_hint=root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "remote_release_dir_hint=/opt/docgen/releases" "$LATEST_OPS_PATH"
assert_contains "public_base_url_hint=https://doc.niyoufei.com" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_release.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/push_docgen_server_release.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_worktree_scripts.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/push_docgen_server_worktree_scripts.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "sha256sum -c docgen-server-app.tgz.sha256" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_docgen_server_release_dir.sh build/server_app_bundle" "$LATEST_OPS_PATH"
assert_contains "ssh root@199.180.118.204 'bash /opt/docgen/scripts/verify_docgen_server_worktree_scripts.sh /opt/docgen /opt/docgen/releases'" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_release_dir.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_status.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_status.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_retention.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "bash ./scripts/verify_remote_docgen_server_readonly_retention.sh root@199.180.118.204" "$LATEST_OPS_PATH"
assert_contains "ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_inspection/latest-status.txt'" "$LATEST_OPS_PATH"
assert_contains "ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_retention/latest-status.txt'" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 bash /opt/docgen/scripts/prune_docgen_server_readonly_inspection_logs.sh /opt/docgen/logs/readonly_inspection" "$LATEST_OPS_PATH"
assert_contains "DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 DOCGEN_PRUNE_CONFIRM_RUN_ID=<retention_run_id> DOCGEN_PRUNE_CONFIRM_CANDIDATES=<candidate_csv> DOCGEN_PRUNE_EXECUTE=1 bash /opt/docgen/scripts/prune_docgen_server_readonly_inspection_logs.sh /opt/docgen/logs/readonly_inspection" "$LATEST_OPS_PATH"
assert_contains "Execute is refused when prune_candidates=none." "$LATEST_OPS_PATH"
assert_contains "release_id=" "$LATEST_NOTES_PATH"
assert_contains "comparison_mode=initial_release" "$LATEST_NOTES_PATH"
assert_contains "impact_scope=bootstrap" "$LATEST_NOTES_PATH"
assert_contains "operator_action=initial-install" "$LATEST_NOTES_PATH"
assert_contains "service_restart_recommended=no" "$LATEST_NOTES_PATH"
assert_contains "runtime_probes_added=none" "$LATEST_NOTES_PATH"
assert_contains "runtime_probes_removed=none" "$LATEST_NOTES_PATH"
assert_contains "operator_probes_added=none" "$LATEST_NOTES_PATH"
assert_contains "operator_probes_removed=none" "$LATEST_NOTES_PATH"
assert_contains "operator_release_tools_added=none" "$LATEST_NOTES_PATH"
assert_contains "operator_release_tools_removed=none" "$LATEST_NOTES_PATH"
assert_contains "server_release_tools_added=none" "$LATEST_NOTES_PATH"
assert_contains "server_release_tools_removed=none" "$LATEST_NOTES_PATH"
assert_contains "release_tools_added=none" "$LATEST_NOTES_PATH"
assert_contains "release_tools_removed=none" "$LATEST_NOTES_PATH"
assert_contains "included_roots_added=none" "$LATEST_NOTES_PATH"
assert_contains "included_roots_removed=none" "$LATEST_NOTES_PATH"
assert_contains "archive_entries_added_count=0" "$LATEST_NOTES_PATH"
assert_contains "archive_entries_removed_count=0" "$LATEST_NOTES_PATH"
assert_contains "archive_entries_modified_count=0" "$LATEST_NOTES_PATH"
assert_contains "archive_added_groups=scripts:0|tests:0|docs:0|deploy:0|backend:0|root:0|other:0" "$LATEST_NOTES_PATH"
assert_contains "archive_removed_groups=scripts:0|tests:0|docs:0|deploy:0|backend:0|root:0|other:0" "$LATEST_NOTES_PATH"
assert_contains "archive_modified_groups=scripts:0|tests:0|docs:0|deploy:0|backend:0|root:0|other:0" "$LATEST_NOTES_PATH"
assert_contains "archive_group_highlights_added=none" "$LATEST_NOTES_PATH"
assert_contains "archive_group_highlights_removed=none" "$LATEST_NOTES_PATH"
assert_contains "archive_group_highlights_modified=none" "$LATEST_NOTES_PATH"
assert_contains "Human summary:" "$LATEST_NOTES_PATH"
assert_contains "- impact scope: bootstrap" "$LATEST_NOTES_PATH"
assert_contains "- operator action: initial-install" "$LATEST_NOTES_PATH"

tar -tzf "$ARCHIVE_PATH" > "$TAR_LIST"
assert_contains "rules_sample.json" "$TAR_LIST"
assert_contains "deploy/nginx/docgen-streamlit-origin.conf.template" "$TAR_LIST"
assert_contains "deploy/systemd/docgen-autoplan.service" "$TAR_LIST"
assert_contains "03_系统核心规则与字典/" "$TAR_LIST"
assert_contains "知识图谱/" "$TAR_LIST"
assert_contains "modules/parser/parser_unify.py" "$TAR_LIST"
assert_contains "scripts/verify_public_edge_health_stable.sh" "$TAR_LIST"
assert_contains "scripts/report_docgen_runtime_health_stable.sh" "$TAR_LIST"
assert_contains "scripts/verify_upload_parse_chain.sh" "$TAR_LIST"
assert_contains "scripts/verify_generate_export_chain.sh" "$TAR_LIST"
assert_contains "scripts/verify_ui_upload_outline_chain.sh" "$TAR_LIST"
assert_contains "scripts/verify_remote_ui_upload_outline_chain.sh" "$TAR_LIST"
assert_contains "scripts/verify_remote_full_chain.sh" "$TAR_LIST"
assert_contains "scripts/push_docgen_server_release.sh" "$TAR_LIST"
assert_contains "scripts/push_docgen_server_worktree_scripts.sh" "$TAR_LIST"
assert_contains "scripts/verify_docgen_server_release_dir.sh" "$TAR_LIST"
assert_contains "scripts/verify_docgen_server_worktree_scripts.sh" "$TAR_LIST"
assert_contains "scripts/verify_remote_docgen_server_release_dir.sh" "$TAR_LIST"
assert_contains "scripts/verify_remote_docgen_server_status.sh" "$TAR_LIST"
assert_contains "scripts/show_docgen_server_status.sh" "$TAR_LIST"
assert_contains "scripts/verify_remote_docgen_server_readonly_inspection.sh" "$TAR_LIST"
assert_contains "scripts/verify_remote_docgen_server_readonly_retention.sh" "$TAR_LIST"
assert_contains "scripts/report_docgen_server_readonly_inspection.sh" "$TAR_LIST"
assert_contains "scripts/report_docgen_server_readonly_retention.sh" "$TAR_LIST"
assert_contains "scripts/prune_docgen_server_readonly_inspection_logs.sh" "$TAR_LIST"
assert_not_contains "backend/tests/" "$TAR_LIST"
assert_not_contains "backend/data/uploads/" "$TAR_LIST"
assert_not_contains "build/" "$TAR_LIST"

python3 - "$VERSIONED_MANIFEST_PATH" "$EXPECTED_ROOTS_CSV" <<'PY'
import json
import sys

manifest_path, expected_csv = sys.argv[1], sys.argv[2]
expected = expected_csv.split(",") if expected_csv else []
with open(manifest_path, "r", encoding="utf-8") as fh:
    manifest = json.load(fh)
actual = manifest.get("included_roots")
if actual != expected:
    raise SystemExit(
        f"[FAIL] included_roots mismatch: expected={expected!r} actual={actual!r}"
    )
PY

echo "[STEP] package from minimal tree without optional roots"
FIXTURE_ROOT="$TMP_DIR/fixture-root"
FIXTURE_OUT="$TMP_DIR/fixture-out"
FIXTURE_ERR="$TMP_DIR/fixture.err"
mkdir -p "$FIXTURE_ROOT/scripts" "$FIXTURE_ROOT/backend/app" "$FIXTURE_ROOT/modules/parser" "$FIXTURE_ROOT/deploy/systemd"
touch "$FIXTURE_ROOT/app.py"
touch "$FIXTURE_ROOT/devserver.py"
touch "$FIXTURE_ROOT/requirements.txt"
touch "$FIXTURE_ROOT/rules_sample.json"
touch "$FIXTURE_ROOT/.env.example"
touch "$FIXTURE_ROOT/.gitignore"
touch "$FIXTURE_ROOT/backend/app/main.py"
touch "$FIXTURE_ROOT/modules/parser/parser_unify.py"
touch "$FIXTURE_ROOT/deploy/systemd/docgen-autoplan.service"
cp "$PACKAGE_SCRIPT" "$FIXTURE_ROOT/scripts/package_docgen_server_app.sh"

bash "$FIXTURE_ROOT/scripts/package_docgen_server_app.sh" "$FIXTURE_OUT" >/dev/null 2>"$FIXTURE_ERR"
assert_contains "[WARN] skipping optional package root: .streamlit" "$FIXTURE_ERR"
assert_contains "[WARN] skipping optional package root: knowledge_graph" "$FIXTURE_ERR"
assert_contains "[WARN] skipping optional package root: 知识图谱" "$FIXTURE_ERR"
assert_contains "[WARN] skipping optional package root: 03_系统核心规则与字典" "$FIXTURE_ERR"
assert_contains "included_roots=app.py,devserver.py,requirements.txt,rules_sample.json,.env.example,.gitignore,backend,modules,scripts,deploy" "$FIXTURE_OUT/latest-change-summary.txt"

echo "[STEP] package against seeded previous release"
PREV_RELEASE_ID="19990101-000000"
PREV_ARCHIVE_BASENAME="docgen-server-app-${PREV_RELEASE_ID}.tgz"
PREV_CHECKSUM_BASENAME="${PREV_ARCHIVE_BASENAME}.sha256"
PREV_MANIFEST_BASENAME="docgen-server-app-${PREV_RELEASE_ID}.manifest.json"
PREV_SUMMARY_BASENAME="docgen-server-app-${PREV_RELEASE_ID}.summary.txt"
PREV_NOTES_BASENAME="docgen-server-app-${PREV_RELEASE_ID}.notes.txt"
PREV_SEED_DIR="$TMP_DIR/seed"
mkdir -p "$PREV_SEED_DIR"
printf 'legacy app content\n' > "$PREV_SEED_DIR/app.py"
tar -czf "$OUT_DIR/$PREV_ARCHIVE_BASENAME" -C "$PREV_SEED_DIR" app.py
(
  cd "$OUT_DIR"
  shasum -a 256 "$PREV_ARCHIVE_BASENAME" > "$PREV_CHECKSUM_BASENAME"
)
cat > "$OUT_DIR/$PREV_MANIFEST_BASENAME" <<EOF
{
  "release_id": "$PREV_RELEASE_ID",
  "archive": "$PREV_ARCHIVE_BASENAME",
  "checksum_file": "$PREV_CHECKSUM_BASENAME",
  "summary_file": "$PREV_SUMMARY_BASENAME",
  "notes_file": "$PREV_NOTES_BASENAME",
  "entrypoints": {
    "web": "app.py",
    "api": "backend/app/main.py",
    "launcher": "scripts/run_web_ui.sh"
  },
  "runtime_probes": [
    "scripts/verify_origin_app_health.sh"
  ],
  "included_roots": [
    "app.py"
  ]
}
EOF
printf 'seed summary\n' > "$OUT_DIR/$PREV_SUMMARY_BASENAME"
printf 'seed notes\n' > "$OUT_DIR/$PREV_NOTES_BASENAME"

SECOND_OUT_DIR="$TMP_DIR/out-second"
mkdir -p "$SECOND_OUT_DIR"
cp "$OUT_DIR/$PREV_ARCHIVE_BASENAME" "$SECOND_OUT_DIR/$PREV_ARCHIVE_BASENAME"
cp "$OUT_DIR/$PREV_CHECKSUM_BASENAME" "$SECOND_OUT_DIR/$PREV_CHECKSUM_BASENAME"
cp "$OUT_DIR/$PREV_MANIFEST_BASENAME" "$SECOND_OUT_DIR/$PREV_MANIFEST_BASENAME"
cp "$OUT_DIR/$PREV_SUMMARY_BASENAME" "$SECOND_OUT_DIR/$PREV_SUMMARY_BASENAME"
cp "$OUT_DIR/$PREV_NOTES_BASENAME" "$SECOND_OUT_DIR/$PREV_NOTES_BASENAME"
bash "$PACKAGE_SCRIPT" "$SECOND_OUT_DIR" >/dev/null
SECOND_LATEST_NOTES="$SECOND_OUT_DIR/latest-release-notes.txt"
SECOND_LATEST_OPS="$SECOND_OUT_DIR/latest-release-ops.txt"
assert_contains "comparison_mode=against_previous_release" "$SECOND_LATEST_NOTES"
assert_contains "previous_release_id=19990101-000000" "$SECOND_LATEST_NOTES"
assert_contains "impact_scope=app-runtime" "$SECOND_LATEST_NOTES"
assert_contains "operator_action=rollout-runtime" "$SECOND_LATEST_NOTES"
assert_contains "service_restart_recommended=yes" "$SECOND_LATEST_NOTES"
assert_contains "operator_release_tools_added=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh" "$SECOND_LATEST_NOTES"
assert_contains "operator_release_tools_removed=none" "$SECOND_LATEST_NOTES"
assert_contains "server_release_tools_added=scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$SECOND_LATEST_NOTES"
assert_contains "server_release_tools_removed=none" "$SECOND_LATEST_NOTES"
assert_contains "release_tools_added=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/show_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh" "$SECOND_LATEST_NOTES"
assert_contains "release_tools_removed=none" "$SECOND_LATEST_NOTES"
assert_contains "archive_entries_modified_count=1" "$SECOND_LATEST_NOTES"
assert_contains "archive_modified_groups=scripts:0|tests:0|docs:0|deploy:0|backend:0|root:1|other:0" "$SECOND_LATEST_NOTES"
assert_contains "archive_group_highlights_modified=root=app.py" "$SECOND_LATEST_NOTES"
assert_contains "archive_highlights_modified=app.py" "$SECOND_LATEST_NOTES"
assert_contains "- archive groups:" "$SECOND_LATEST_NOTES"
assert_contains "- impact scope: app-runtime" "$SECOND_LATEST_NOTES"
assert_contains "- operator action: rollout-runtime (restart=yes)" "$SECOND_LATEST_NOTES"
assert_contains "- operator release tools changed: added=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh removed=none" "$SECOND_LATEST_NOTES"
assert_contains "- server release tools changed: added=scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh removed=none" "$SECOND_LATEST_NOTES"
assert_contains "- release tools changed: added=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/show_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh removed=none" "$SECOND_LATEST_NOTES"
assert_contains "modified=root:1" "$SECOND_LATEST_NOTES"
assert_contains "- archive modified root: app.py" "$SECOND_LATEST_NOTES"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_release.sh root@199.180.118.204" "$SECOND_LATEST_OPS"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_worktree_scripts.sh root@199.180.118.204" "$SECOND_LATEST_OPS"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_status.sh root@199.180.118.204" "$SECOND_LATEST_OPS"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh root@199.180.118.204" "$SECOND_LATEST_OPS"
assert_contains "DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_retention.sh root@199.180.118.204" "$SECOND_LATEST_OPS"
assert_contains "ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_inspection/latest-status.txt'" "$SECOND_LATEST_OPS"
assert_contains "ssh root@199.180.118.204 'cat /opt/docgen/logs/readonly_retention/latest-status.txt'" "$SECOND_LATEST_OPS"
assert_contains "DOCGEN_PRUNE_CONFIRM_RUN_ID=<retention_run_id>" "$SECOND_LATEST_OPS"
assert_contains "DOCGEN_PRUNE_CONFIRM_CANDIDATES=<candidate_csv>" "$SECOND_LATEST_OPS"
assert_contains "Execute is refused when prune_candidates=none." "$SECOND_LATEST_OPS"

echo "[PASS] package_docgen_server_app regression checks passed"
