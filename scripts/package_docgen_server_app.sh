#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-$ROOT/build/server_app_bundle}"
RELEASE_ID="${DOCGEN_RELEASE_ID:-$(date '+%Y%m%d-%H%M%S')}"
VERSIONED_BASENAME="docgen-server-app-${RELEASE_ID}.tgz"
VERSIONED_CHECKSUM_BASENAME="${VERSIONED_BASENAME}.sha256"
VERSIONED_MANIFEST_BASENAME="docgen-server-app-${RELEASE_ID}.manifest.json"
VERSIONED_SUMMARY_BASENAME="docgen-server-app-${RELEASE_ID}.summary.txt"
VERSIONED_NOTES_BASENAME="docgen-server-app-${RELEASE_ID}.notes.txt"
VERSIONED_OPS_BASENAME="docgen-server-app-${RELEASE_ID}.ops.txt"
VERSIONED_ARCHIVE_PATH="${OUT_DIR%/}/${VERSIONED_BASENAME}"
VERSIONED_CHECKSUM_PATH="${OUT_DIR%/}/${VERSIONED_CHECKSUM_BASENAME}"
VERSIONED_MANIFEST_PATH="${OUT_DIR%/}/${VERSIONED_MANIFEST_BASENAME}"
VERSIONED_SUMMARY_PATH="${OUT_DIR%/}/${VERSIONED_SUMMARY_BASENAME}"
VERSIONED_NOTES_PATH="${OUT_DIR%/}/${VERSIONED_NOTES_BASENAME}"
VERSIONED_OPS_PATH="${OUT_DIR%/}/${VERSIONED_OPS_BASENAME}"
LATEST_ARCHIVE_PATH="${OUT_DIR%/}/docgen-server-app.tgz"
LATEST_CHECKSUM_PATH="${LATEST_ARCHIVE_PATH}.sha256"
LATEST_MANIFEST_PATH="${OUT_DIR%/}/docgen-server-app.manifest.json"
LATEST_RELEASE_PATH="${OUT_DIR%/}/latest-release.txt"
RELEASES_INDEX_PATH="${OUT_DIR%/}/releases-index.txt"
LATEST_SUMMARY_PATH="${OUT_DIR%/}/latest-change-summary.txt"
LATEST_NOTES_PATH="${OUT_DIR%/}/latest-release-notes.txt"
LATEST_OPS_PATH="${OUT_DIR%/}/latest-release-ops.txt"
RELEASE_HOST_HINT="${DOCGEN_RELEASE_HOST_HINT:-root@199.180.118.204}"
REMOTE_APP_DIR_HINT="${DOCGEN_REMOTE_APP_DIR_HINT:-/opt/docgen}"
REMOTE_RELEASE_DIR_HINT="${DOCGEN_REMOTE_RELEASE_DIR_HINT:-/opt/docgen/releases}"
PUBLIC_BASE_URL_HINT="${DOCGEN_PUBLIC_BASE_URL_HINT:-https://doc.niyoufei.com}"

PACKAGE_ROOT_CANDIDATES=(
  "app.py"
  "devserver.py"
  "requirements.txt"
  "rules_sample.json"
  ".env.example"
  ".gitignore"
  ".streamlit"
  "backend"
  "modules"
  "scripts"
  "deploy"
  "knowledge_graph"
  "知识图谱"
  "03_系统核心规则与字典"
)

is_required_package_root() {
  case "$1" in
    "app.py"|"devserver.py"|"requirements.txt"|"rules_sample.json"|".env.example"|".gitignore"|"backend"|"modules"|"scripts"|"deploy")
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

PACKAGE_ROOTS=()
for package_root in "${PACKAGE_ROOT_CANDIDATES[@]}"; do
  if [[ -e "$ROOT/$package_root" ]]; then
    PACKAGE_ROOTS+=("$package_root")
    continue
  fi
  if is_required_package_root "$package_root"; then
    echo "[ERROR] missing required package root: $package_root" >&2
    exit 1
  fi
  echo "[WARN] skipping optional package root: $package_root" >&2
done

PACKAGE_ROOTS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:], ensure_ascii=False))' "${PACKAGE_ROOTS[@]}")"
PACKAGE_ROOTS_CSV="$(python3 -c 'import sys; print(",".join(sys.argv[1:]))' "${PACKAGE_ROOTS[@]}")"

mkdir -p "$OUT_DIR"

COPYFILE_DISABLE=1 tar -czf "$VERSIONED_ARCHIVE_PATH" -C "$ROOT" \
  --exclude='.DS_Store' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.cursor' \
  --exclude='.bin' \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='.runtime' \
  --exclude='.playwright-cli' \
  --exclude='build' \
  --exclude='logs' \
  --exclude='output' \
  --exclude='tmp' \
  --exclude='artifacts' \
  --exclude='deliveries' \
  --exclude='exports' \
  --exclude='04_实战演习输入' \
  --exclude='_autodoctor' \
  --exclude='_smartcheck' \
  --exclude='施组专家系统.app' \
  --exclude='backend/tests' \
  --exclude='backend/build' \
  --exclude='backend/data/uploads' \
  --exclude='backend/data/extracts' \
  --exclude='backend/data/audit' \
  --exclude='backend/data/auth' \
  --exclude='backend/data/previews' \
  --exclude='backend/data/autoplan/jobs' \
  --exclude='backend/data/autoplan/media' \
  --exclude='backend/data/autoplan/projects' \
  --exclude='backend/data/autoplan/archive' \
  --exclude='backend/data/autoplan/cache' \
  --exclude='01_真实项目测试' \
  --exclude='02_规范测试入库' \
  --exclude='*.bak' \
  --exclude='*.bak.*' \
  --exclude='*.wip' \
  --exclude='*.wip.*' \
  "${PACKAGE_ROOTS[@]}"

(
  cd "$OUT_DIR"
  shasum -a 256 "$VERSIONED_BASENAME" > "$VERSIONED_CHECKSUM_BASENAME"
)

CHECKSUM_VALUE="$(awk '{print $1}' "$VERSIONED_CHECKSUM_PATH")"
CREATED_AT_UTC="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

python3 - <<PY > "$VERSIONED_MANIFEST_PATH"
import json

payload = {
    "release_id": "${RELEASE_ID}",
    "created_at_utc": "${CREATED_AT_UTC}",
    "archive": "${VERSIONED_BASENAME}",
    "checksum_file": "${VERSIONED_CHECKSUM_BASENAME}",
    "checksum_sha256": "${CHECKSUM_VALUE}",
    "summary_file": "${VERSIONED_SUMMARY_BASENAME}",
    "notes_file": "${VERSIONED_NOTES_BASENAME}",
    "ops_file": "${VERSIONED_OPS_BASENAME}",
    "entrypoints": {
        "web": "app.py",
        "api": "backend/app/main.py",
        "launcher": "scripts/run_web_ui.sh",
    },
    "runtime_probes": [
        "scripts/verify_origin_app_health.sh",
        "scripts/verify_public_edge_health.sh",
        "scripts/verify_public_edge_health_stable.sh",
        "scripts/report_docgen_runtime_health.sh",
        "scripts/report_docgen_runtime_health_stable.sh",
        "scripts/verify_linux_domain_origin.sh",
        "scripts/verify_ocr_runtime.sh",
        "scripts/verify_upload_parse_chain.sh",
        "scripts/verify_generate_export_chain.sh",
    ],
    "operator_probes": [
        "scripts/verify_ui_upload_outline_chain.sh",
        "scripts/verify_remote_ui_upload_outline_chain.sh",
        "scripts/verify_remote_full_chain.sh",
    ],
    "operator_release_tools": [
        "scripts/package_docgen_server_app.sh",
        "scripts/push_docgen_server_release.sh",
        "scripts/push_docgen_server_worktree_scripts.sh",
        "scripts/verify_remote_docgen_server_release_dir.sh",
        "scripts/verify_remote_docgen_server_status.sh",
        "scripts/verify_remote_docgen_server_readonly_inspection.sh",
        "scripts/verify_remote_docgen_server_readonly_retention.sh",
    ],
    "server_release_tools": [
        "scripts/verify_docgen_server_release_dir.sh",
        "scripts/verify_docgen_server_worktree_scripts.sh",
        "scripts/show_docgen_server_status.sh",
        "scripts/report_docgen_server_readonly_inspection.sh",
        "scripts/report_docgen_server_readonly_retention.sh",
        "scripts/prune_docgen_server_readonly_inspection_logs.sh",
    ],
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
        "scripts/prune_docgen_server_readonly_inspection_logs.sh",
    ],
    "included_roots": ${PACKAGE_ROOTS_JSON},
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY

cat > "$VERSIONED_SUMMARY_PATH" <<EOF
release_id=${RELEASE_ID}
created_at_utc=${CREATED_AT_UTC}
archive=${VERSIONED_BASENAME}
checksum_file=${VERSIONED_CHECKSUM_BASENAME}
checksum_sha256=${CHECKSUM_VALUE}
entrypoints=app.py,backend/app/main.py,scripts/run_web_ui.sh
runtime_probes=scripts/verify_origin_app_health.sh,scripts/verify_public_edge_health.sh,scripts/verify_public_edge_health_stable.sh,scripts/report_docgen_runtime_health.sh,scripts/report_docgen_runtime_health_stable.sh,scripts/verify_linux_domain_origin.sh,scripts/verify_ocr_runtime.sh,scripts/verify_upload_parse_chain.sh,scripts/verify_generate_export_chain.sh
operator_probes=scripts/verify_ui_upload_outline_chain.sh,scripts/verify_remote_ui_upload_outline_chain.sh,scripts/verify_remote_full_chain.sh
operator_release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh
server_release_tools=scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/show_docgen_server_status.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh
release_tools=scripts/package_docgen_server_app.sh,scripts/push_docgen_server_release.sh,scripts/push_docgen_server_worktree_scripts.sh,scripts/verify_docgen_server_release_dir.sh,scripts/verify_docgen_server_worktree_scripts.sh,scripts/verify_remote_docgen_server_release_dir.sh,scripts/verify_remote_docgen_server_status.sh,scripts/show_docgen_server_status.sh,scripts/verify_remote_docgen_server_readonly_inspection.sh,scripts/verify_remote_docgen_server_readonly_retention.sh,scripts/report_docgen_server_readonly_inspection.sh,scripts/report_docgen_server_readonly_retention.sh,scripts/prune_docgen_server_readonly_inspection_logs.sh
included_roots=${PACKAGE_ROOTS_CSV}
EOF

cat > "$VERSIONED_OPS_PATH" <<EOF
release_id=${RELEASE_ID}
archive=${VERSIONED_BASENAME}
checksum_file=${VERSIONED_CHECKSUM_BASENAME}
manifest_file=${VERSIONED_MANIFEST_BASENAME}
summary_file=${VERSIONED_SUMMARY_BASENAME}
notes_file=${VERSIONED_NOTES_BASENAME}
release_host_hint=${RELEASE_HOST_HINT}
remote_release_dir_hint=${REMOTE_RELEASE_DIR_HINT}
public_base_url_hint=${PUBLIC_BASE_URL_HINT}

Recommended commands:
1. Preview sync command:
DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_release.sh ${RELEASE_HOST_HINT}

2. Execute sync:
bash ./scripts/push_docgen_server_release.sh ${RELEASE_HOST_HINT}

3. Preview server worktree script sync:
DOCGEN_PREVIEW=1 bash ./scripts/push_docgen_server_worktree_scripts.sh ${RELEASE_HOST_HINT}

4. Sync server worktree scripts:
bash ./scripts/push_docgen_server_worktree_scripts.sh ${RELEASE_HOST_HINT}

5. Remote checksum verify:
ssh ${RELEASE_HOST_HINT} 'cd ${REMOTE_RELEASE_DIR_HINT} && sha256sum -c docgen-server-app.tgz.sha256'

6. Remote latest pointers:
ssh ${RELEASE_HOST_HINT} 'cd ${REMOTE_RELEASE_DIR_HINT} && readlink docgen-server-app.tgz && readlink docgen-server-app.tgz.sha256 && readlink docgen-server-app.manifest.json'

7. Release directory self-check:
bash ./scripts/verify_docgen_server_release_dir.sh build/server_app_bundle

8. Remote release directory self-check:
bash ./scripts/verify_remote_docgen_server_release_dir.sh ${RELEASE_HOST_HINT}

9. Preview remote current server status:
DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_status.sh ${RELEASE_HOST_HINT}

10. Read current unified server status:
bash ./scripts/verify_remote_docgen_server_status.sh ${RELEASE_HOST_HINT}

11. Server worktree scripts self-check:
ssh ${RELEASE_HOST_HINT} 'bash ${REMOTE_APP_DIR_HINT:-/opt/docgen}/scripts/verify_docgen_server_worktree_scripts.sh ${REMOTE_APP_DIR_HINT:-/opt/docgen} ${REMOTE_RELEASE_DIR_HINT}'

12. Preview remote readonly inspection:
DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh ${RELEASE_HOST_HINT}

13. Execute remote readonly inspection:
bash ./scripts/verify_remote_docgen_server_readonly_inspection.sh ${RELEASE_HOST_HINT}

14. Preview remote readonly retention report:
DOCGEN_PREVIEW=1 bash ./scripts/verify_remote_docgen_server_readonly_retention.sh ${RELEASE_HOST_HINT}

15. Execute remote readonly retention report:
bash ./scripts/verify_remote_docgen_server_readonly_retention.sh ${RELEASE_HOST_HINT}

16. Read latest readonly inspection status:
ssh ${RELEASE_HOST_HINT} 'cat ${REMOTE_APP_DIR_HINT:-/opt/docgen}/logs/readonly_inspection/latest-status.txt'

17. Read latest readonly retention status:
ssh ${RELEASE_HOST_HINT} 'cat ${REMOTE_APP_DIR_HINT:-/opt/docgen}/logs/readonly_retention/latest-status.txt'

18. Preview readonly inspection log retention:
ssh ${RELEASE_HOST_HINT} 'DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 bash ${REMOTE_APP_DIR_HINT:-/opt/docgen}/scripts/prune_docgen_server_readonly_inspection_logs.sh ${REMOTE_APP_DIR_HINT:-/opt/docgen}/logs/readonly_inspection'

19. Execute readonly inspection log retention:
ssh ${RELEASE_HOST_HINT} 'DOCGEN_READONLY_INSPECTION_KEEP_RUNS=10 DOCGEN_PRUNE_CONFIRM_RUN_ID=<retention_run_id> DOCGEN_PRUNE_CONFIRM_CANDIDATES=<candidate_csv> DOCGEN_PRUNE_EXECUTE=1 bash ${REMOTE_APP_DIR_HINT:-/opt/docgen}/scripts/prune_docgen_server_readonly_inspection_logs.sh ${REMOTE_APP_DIR_HINT:-/opt/docgen}/logs/readonly_inspection'

Note:
- Preview command is the retention dry-run.
- Execute requires the latest readonly retention status to report the same run_id and candidate list.
- Execute is refused when prune_candidates=none.
EOF

PREVIOUS_MANIFEST_PATH="$(
  find "$OUT_DIR" -maxdepth 1 -type f -name 'docgen-server-app-*.manifest.json' ! -name "$VERSIONED_MANIFEST_BASENAME" -print \
    | sort \
    | tail -n1
)"

python3 - <<PY > "$VERSIONED_NOTES_PATH"
import json
from pathlib import Path

current = json.loads(Path("${VERSIONED_MANIFEST_PATH}").read_text(encoding="utf-8"))
previous_path = Path("${PREVIOUS_MANIFEST_PATH}") if "${PREVIOUS_MANIFEST_PATH}" else None
previous = None
if previous_path and previous_path.exists():
    previous = json.loads(previous_path.read_text(encoding="utf-8"))

def normalize(values):
    return list(values or [])

def format_list(values):
    return ",".join(values) if values else "none"

GROUP_ORDER = ("scripts", "tests", "docs", "deploy", "backend", "root", "other")

def classify_path(path):
    if path.startswith("deploy/"):
        return "deploy"
    if path.startswith("backend/tests/") or path.startswith("scripts/test_"):
        return "tests"
    if path.startswith("scripts/"):
        return "scripts"
    if path.startswith("modules/"):
        return "backend"
    if path.startswith("backend/"):
        return "backend"
    if path.startswith("docs/"):
        return "docs"
    if "/" not in path:
        return "root"
    return "other"

def group_summary(values):
    counts = {key: 0 for key in GROUP_ORDER}
    for value in values:
        counts[classify_path(value)] += 1
    return "|".join(f"{key}:{counts[key]}" for key in GROUP_ORDER)

def nonzero_group_summary(values):
    counts = {key: 0 for key in GROUP_ORDER}
    for value in values:
        counts[classify_path(value)] += 1
    pairs = [f"{key}:{counts[key]}" for key in GROUP_ORDER if counts[key] > 0]
    return ",".join(pairs) if pairs else "none"

def group_highlights(values, limit=3):
    grouped = {key: [] for key in GROUP_ORDER}
    for value in values:
        key = classify_path(value)
        if len(grouped[key]) < limit:
            grouped[key].append(value)
    pairs = [f"{key}={','.join(grouped[key])}" for key in GROUP_ORDER if grouped[key]]
    return ";".join(pairs) if pairs else "none"

current_entrypoints = current.get("entrypoints", {})
current_runtime = normalize(current.get("runtime_probes"))
current_operator = normalize(current.get("operator_probes"))
current_operator_release_tools = normalize(current.get("operator_release_tools"))
current_server_release_tools = normalize(current.get("server_release_tools"))
current_release_tools = normalize(current.get("release_tools"))
current_roots = normalize(current.get("included_roots"))

notes = {
    "release_id": current["release_id"],
    "previous_release_id": "none",
    "comparison_mode": "initial_release",
    "impact_scope": "bootstrap",
    "operator_action": "initial-install",
    "service_restart_recommended": "no",
    "entrypoints_changed": "no",
    "runtime_probes_added": "none",
    "runtime_probes_removed": "none",
    "operator_probes_added": "none",
    "operator_probes_removed": "none",
    "operator_release_tools_added": "none",
    "operator_release_tools_removed": "none",
    "server_release_tools_added": "none",
    "server_release_tools_removed": "none",
    "release_tools_added": "none",
    "release_tools_removed": "none",
    "included_roots_added": "none",
    "included_roots_removed": "none",
    "archive_entries_added_count": "0",
    "archive_entries_removed_count": "0",
    "archive_entries_modified_count": "0",
    "archive_added_groups": group_summary([]),
    "archive_removed_groups": group_summary([]),
    "archive_modified_groups": group_summary([]),
    "archive_group_highlights_added": "none",
    "archive_group_highlights_removed": "none",
    "archive_group_highlights_modified": "none",
    "archive_highlights_added": "none",
    "archive_highlights_removed": "none",
    "archive_highlights_modified": "none",
}

summary_lines = []

if previous is None:
    notes["impact_scope"] = "bootstrap"
    notes["operator_action"] = "initial-install"
    notes["service_restart_recommended"] = "no"
    summary_lines.append("- initial release in this output directory")
    summary_lines.append("- impact scope: bootstrap")
    summary_lines.append("- operator action: initial-install")
else:
    previous_entrypoints = previous.get("entrypoints", {})
    previous_runtime = normalize(previous.get("runtime_probes"))
    previous_operator = normalize(previous.get("operator_probes"))
    previous_operator_release_tools = normalize(previous.get("operator_release_tools"))
    previous_server_release_tools = normalize(previous.get("server_release_tools"))
    previous_release_tools = normalize(previous.get("release_tools"))
    previous_roots = normalize(previous.get("included_roots"))
    previous_archive_path = previous_path.with_name(previous.get("archive", "")) if previous.get("archive") else None

    archive_added = []
    archive_removed = []
    if previous_archive_path and previous_archive_path.exists():
        import hashlib
        import tarfile

        def tar_names(path):
            with tarfile.open(path, "r:gz") as tf:
                return sorted(member.name for member in tf.getmembers())

        def tar_fingerprints(path):
            fingerprints = {}
            with tarfile.open(path, "r:gz") as tf:
                for member in tf.getmembers():
                    if member.isdir():
                        fingerprints[member.name] = "dir"
                        continue
                    if member.isfile():
                        extracted = tf.extractfile(member)
                        data = extracted.read() if extracted is not None else b""
                        fingerprints[member.name] = "file:" + hashlib.sha256(data).hexdigest()
                        continue
                    fingerprints[member.name] = (
                        f"type:{member.type}|size:{member.size}|mode:{member.mode}|link:{member.linkname}"
                    )
            return fingerprints

        current_archive_path = Path("${VERSIONED_ARCHIVE_PATH}")
        current_names = tar_names(current_archive_path)
        previous_names = tar_names(previous_archive_path)
        archive_added = [item for item in current_names if item not in previous_names]
        archive_removed = [item for item in previous_names if item not in current_names]
        current_fingerprints = tar_fingerprints(current_archive_path)
        previous_fingerprints = tar_fingerprints(previous_archive_path)
        shared_names = [item for item in current_names if item in previous_fingerprints]
        archive_modified = [
            item for item in shared_names
            if current_fingerprints.get(item) != previous_fingerprints.get(item)
        ]

    runtime_added = [item for item in current_runtime if item not in previous_runtime]
    runtime_removed = [item for item in previous_runtime if item not in current_runtime]
    operator_added = [item for item in current_operator if item not in previous_operator]
    operator_removed = [item for item in previous_operator if item not in current_operator]
    operator_release_tools_added = [
        item for item in current_operator_release_tools if item not in previous_operator_release_tools
    ]
    operator_release_tools_removed = [
        item for item in previous_operator_release_tools if item not in current_operator_release_tools
    ]
    server_release_tools_added = [
        item for item in current_server_release_tools if item not in previous_server_release_tools
    ]
    server_release_tools_removed = [
        item for item in previous_server_release_tools if item not in current_server_release_tools
    ]
    release_tools_added = [item for item in current_release_tools if item not in previous_release_tools]
    release_tools_removed = [item for item in previous_release_tools if item not in current_release_tools]
    roots_added = [item for item in current_roots if item not in previous_roots]
    roots_removed = [item for item in previous_roots if item not in current_roots]

    notes["previous_release_id"] = previous.get("release_id", "unknown")
    notes["comparison_mode"] = "against_previous_release"
    notes["entrypoints_changed"] = "yes" if current_entrypoints != previous_entrypoints else "no"
    notes["runtime_probes_added"] = format_list(runtime_added)
    notes["runtime_probes_removed"] = format_list(runtime_removed)
    notes["operator_probes_added"] = format_list(operator_added)
    notes["operator_probes_removed"] = format_list(operator_removed)
    notes["operator_release_tools_added"] = format_list(operator_release_tools_added)
    notes["operator_release_tools_removed"] = format_list(operator_release_tools_removed)
    notes["server_release_tools_added"] = format_list(server_release_tools_added)
    notes["server_release_tools_removed"] = format_list(server_release_tools_removed)
    notes["release_tools_added"] = format_list(release_tools_added)
    notes["release_tools_removed"] = format_list(release_tools_removed)
    notes["included_roots_added"] = format_list(roots_added)
    notes["included_roots_removed"] = format_list(roots_removed)
    notes["archive_entries_added_count"] = str(len(archive_added))
    notes["archive_entries_removed_count"] = str(len(archive_removed))
    notes["archive_entries_modified_count"] = str(len(archive_modified))
    notes["archive_added_groups"] = group_summary(archive_added)
    notes["archive_removed_groups"] = group_summary(archive_removed)
    notes["archive_modified_groups"] = group_summary(archive_modified)
    notes["archive_group_highlights_added"] = group_highlights(archive_added)
    notes["archive_group_highlights_removed"] = group_highlights(archive_removed)
    notes["archive_group_highlights_modified"] = group_highlights(archive_modified)
    notes["archive_highlights_added"] = format_list(archive_added[:10])
    notes["archive_highlights_removed"] = format_list(archive_removed[:10])
    notes["archive_highlights_modified"] = format_list(archive_modified[:10])

    changed_groups = {
        classify_path(item) for item in archive_added + archive_removed + archive_modified
    }
    if notes["entrypoints_changed"] == "yes" or roots_added or roots_removed or {"backend", "root"} & changed_groups:
        notes["impact_scope"] = "app-runtime"
    elif "deploy" in changed_groups:
        notes["impact_scope"] = "deploy-assets"
    elif (
        runtime_added or runtime_removed or operator_added or operator_removed
        or operator_release_tools_added or operator_release_tools_removed
        or server_release_tools_added or server_release_tools_removed
        or release_tools_added or release_tools_removed
        or {"scripts", "tests"} & changed_groups
    ):
        notes["impact_scope"] = "tooling-only"
    elif {"docs", "other"} & changed_groups:
        notes["impact_scope"] = "metadata-only"
    else:
        notes["impact_scope"] = "no-asset-diff"

    if notes["impact_scope"] == "app-runtime":
        notes["operator_action"] = "rollout-runtime"
        notes["service_restart_recommended"] = "yes"
    elif notes["impact_scope"] == "deploy-assets":
        notes["operator_action"] = "inspect-deploy-assets"
        notes["service_restart_recommended"] = "no"
    elif notes["impact_scope"] == "tooling-only":
        notes["operator_action"] = "sync-scripts"
        notes["service_restart_recommended"] = "no"
    elif notes["impact_scope"] == "metadata-only":
        notes["operator_action"] = "refresh-release-metadata"
        notes["service_restart_recommended"] = "no"
    else:
        notes["operator_action"] = "no-op"
        notes["service_restart_recommended"] = "no"

    summary_lines.append(f"- impact scope: {notes['impact_scope']}")
    summary_lines.append(
        f"- operator action: {notes['operator_action']} (restart={notes['service_restart_recommended']})"
    )
    if notes["entrypoints_changed"] == "yes":
      summary_lines.append("- entrypoints changed")
    else:
      summary_lines.append("- entrypoints unchanged")
    if runtime_added or runtime_removed:
      summary_lines.append(f"- runtime probes changed: added={format_list(runtime_added)} removed={format_list(runtime_removed)}")
    else:
      summary_lines.append("- runtime probes unchanged")
    if operator_added or operator_removed:
      summary_lines.append(f"- operator probes changed: added={format_list(operator_added)} removed={format_list(operator_removed)}")
    else:
      summary_lines.append("- operator probes unchanged")
    if operator_release_tools_added or operator_release_tools_removed:
      summary_lines.append(f"- operator release tools changed: added={format_list(operator_release_tools_added)} removed={format_list(operator_release_tools_removed)}")
    else:
      summary_lines.append("- operator release tools unchanged")
    if server_release_tools_added or server_release_tools_removed:
      summary_lines.append(f"- server release tools changed: added={format_list(server_release_tools_added)} removed={format_list(server_release_tools_removed)}")
    else:
      summary_lines.append("- server release tools unchanged")
    if release_tools_added or release_tools_removed:
      summary_lines.append(f"- release tools changed: added={format_list(release_tools_added)} removed={format_list(release_tools_removed)}")
    else:
      summary_lines.append("- release tools unchanged")
    if roots_added or roots_removed:
      summary_lines.append(f"- included roots changed: added={format_list(roots_added)} removed={format_list(roots_removed)}")
    else:
      summary_lines.append("- included roots unchanged")
    if archive_added or archive_removed or archive_modified:
      summary_lines.append(
          f"- archive entries changed: added={len(archive_added)} removed={len(archive_removed)} modified={len(archive_modified)}"
      )
      summary_lines.append(
          f"- archive groups: added={nonzero_group_summary(archive_added)} removed={nonzero_group_summary(archive_removed)} modified={nonzero_group_summary(archive_modified)}"
      )
      for label, values in (
          ("added", archive_added),
          ("removed", archive_removed),
          ("modified", archive_modified),
      ):
          grouped_summary = group_highlights(values)
          if grouped_summary != "none":
              for group_item in grouped_summary.split(";"):
                  group, paths = group_item.split("=", 1)
                  summary_lines.append(f"- archive {label} {group}: {paths}")
    else:
      summary_lines.append("- archive entries unchanged")

for key in (
    "release_id",
    "previous_release_id",
    "comparison_mode",
    "impact_scope",
    "operator_action",
    "service_restart_recommended",
    "entrypoints_changed",
    "runtime_probes_added",
    "runtime_probes_removed",
    "operator_probes_added",
    "operator_probes_removed",
    "operator_release_tools_added",
    "operator_release_tools_removed",
    "server_release_tools_added",
    "server_release_tools_removed",
    "release_tools_added",
    "release_tools_removed",
    "included_roots_added",
    "included_roots_removed",
    "archive_entries_added_count",
    "archive_entries_removed_count",
    "archive_entries_modified_count",
    "archive_added_groups",
    "archive_removed_groups",
    "archive_modified_groups",
    "archive_group_highlights_added",
    "archive_group_highlights_removed",
    "archive_group_highlights_modified",
    "archive_highlights_added",
    "archive_highlights_removed",
    "archive_highlights_modified",
):
    print(f"{key}={notes[key]}")
print()
print("Human summary:")
for line in summary_lines:
    print(line)
PY

printf '%s\n' "$VERSIONED_BASENAME" > "$LATEST_RELEASE_PATH"
cp "$VERSIONED_SUMMARY_PATH" "$LATEST_SUMMARY_PATH"
cp "$VERSIONED_NOTES_PATH" "$LATEST_NOTES_PATH"
cp "$VERSIONED_OPS_PATH" "$LATEST_OPS_PATH"
find "$OUT_DIR" -maxdepth 1 -type f -name 'docgen-server-app-*.tgz' -print \
  | sed 's#.*/##' \
  | sort > "$RELEASES_INDEX_PATH"

rm -f "$LATEST_ARCHIVE_PATH" "$LATEST_CHECKSUM_PATH" "$LATEST_MANIFEST_PATH"
ln -s "$VERSIONED_BASENAME" "$LATEST_ARCHIVE_PATH"
ln -s "$VERSIONED_CHECKSUM_BASENAME" "$LATEST_CHECKSUM_PATH"
ln -s "$VERSIONED_MANIFEST_BASENAME" "$LATEST_MANIFEST_PATH"

echo "[OK] versioned archive created: ${VERSIONED_ARCHIVE_PATH}"
echo "[OK] versioned checksum created: ${VERSIONED_CHECKSUM_PATH}"
echo "[OK] versioned manifest created: ${VERSIONED_MANIFEST_PATH}"
echo "[OK] versioned summary created: ${VERSIONED_SUMMARY_PATH}"
echo "[OK] versioned notes created: ${VERSIONED_NOTES_PATH}"
echo "[OK] versioned ops created: ${VERSIONED_OPS_PATH}"
echo "[OK] latest archive symlink updated: ${LATEST_ARCHIVE_PATH} -> ${VERSIONED_BASENAME}"
echo "[OK] latest checksum symlink updated: ${LATEST_CHECKSUM_PATH} -> ${VERSIONED_CHECKSUM_BASENAME}"
echo "[OK] latest manifest symlink updated: ${LATEST_MANIFEST_PATH} -> ${VERSIONED_MANIFEST_BASENAME}"
echo "[OK] latest release pointer updated: ${LATEST_RELEASE_PATH}"
echo "[OK] latest summary updated: ${LATEST_SUMMARY_PATH}"
echo "[OK] latest notes updated: ${LATEST_NOTES_PATH}"
echo "[OK] latest ops updated: ${LATEST_OPS_PATH}"
echo "[OK] releases index updated: ${RELEASES_INDEX_PATH}"
