#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_SCRIPT="$ROOT/scripts/report_public_homepage_cutover_status.sh"
TMP_DIR="$(mktemp -d)"

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
  if ! grep -Fq "$needle" "$file"; then
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
    echo "[FAIL] unexpected text present: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

run_case() {
  local case_name="$1"
  local readiness_rc="$2"
  local readiness_log="$3"
  local local_verify_rc="$4"
  local local_verify_log="$5"
  local public_verify_rc="$6"
  local public_verify_log="$7"
  local push_rc="$8"
  local push_log="$9"
  local asset_rc="${10}"
  local asset_log="${11}"
  local expected_rc="${12}"
  local summary_only="${13}"
  shift 13
  local output_file="$TMP_DIR/${case_name}.out"

  local readiness_stub="$TMP_DIR/${case_name}-readiness.sh"
  local verify_stub="$TMP_DIR/${case_name}-verify.sh"
  local push_stub="$TMP_DIR/${case_name}-push.sh"
  local asset_stub="$TMP_DIR/${case_name}-asset.sh"

  cat > "$readiness_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${readiness_log}
LOG
exit ${readiness_rc}
EOF

  cat > "$verify_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [[ "\$1" == http://127.0.0.1:8501* ]]; then
  cat <<'LOG'
${local_verify_log}
LOG
  exit ${local_verify_rc}
fi
cat <<'LOG'
${public_verify_log}
LOG
exit ${public_verify_rc}
EOF

  cat > "$push_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${push_log}
LOG
exit ${push_rc}
EOF

  cat > "$asset_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${asset_log}
LOG
exit ${asset_rc}
EOF

  chmod +x "$readiness_stub" "$verify_stub" "$push_stub" "$asset_stub"

  set +e
  ZF_STATUS_READINESS_SCRIPT="$readiness_stub" \
  ZF_STATUS_VERIFY_SCRIPT="$verify_stub" \
  ZF_STATUS_PUSH_TEST_SCRIPT="$push_stub" \
  ZF_STATUS_ASSET_TEST_SCRIPT="$asset_stub" \
  ZF_STATUS_SUMMARY_ONLY="$summary_only" \
  bash "$REPORT_SCRIPT" 60 >"$output_file" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -ne "$expected_rc" ]]; then
    echo "[FAIL] case ${case_name}: expected rc=${expected_rc}, actual rc=${rc}" >&2
    cat "$output_file" >&2
    exit 1
  fi

  for needle in "$@"; do
    assert_contains "$needle" "$output_file"
  done
}

echo "[STEP] ready but public still open-webui"
run_case \
  ready_open_webui \
  0 "public_cutover_ready=yes" \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=文档生成系统' \
  1 $'cutover_verified=no\nopen_webui_present=yes\ntitle=Open WebUI' \
  0 "[PASS] push_public_homepage_cutover regression checks passed" \
  0 "[PASS] public homepage cutover assets regression checks passed" \
  0 \
  0 \
  "readiness_state=pass" \
  "local_homepage_state=docgen" \
  "push_test_state=pass" \
  "asset_test_state=pass" \
  "public_homepage_state=open-webui" \
  "public_cutover_needed=yes" \
  "ready_to_apply=yes" \
  "next_action=apply_public_cutover"

echo "[STEP] ready and public already docgen"
run_case \
  ready_docgen \
  0 "public_cutover_ready=yes" \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=文档生成系统' \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=文档生成系统' \
  0 "[PASS] push_public_homepage_cutover regression checks passed" \
  0 "[PASS] public homepage cutover assets regression checks passed" \
  0 \
  0 \
  "public_homepage_state=docgen" \
  "public_cutover_needed=no" \
  "ready_to_apply=yes" \
  "next_action=none_already_cutover"

echo "[STEP] readiness fail should block apply"
run_case \
  readiness_fail \
  1 "public_cutover_ready=no" \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=文档生成系统' \
  1 $'cutover_verified=no\nopen_webui_present=yes\ntitle=Open WebUI' \
  0 "[PASS] push_public_homepage_cutover regression checks passed" \
  0 "[PASS] public homepage cutover assets regression checks passed" \
  1 \
  0 \
  "readiness_state=fail" \
  "public_homepage_state=open-webui" \
  "public_cutover_needed=yes" \
  "ready_to_apply=no" \
  "next_action=fix_local_readiness"

echo "[STEP] summary-only should suppress detailed logs"
run_case \
  summary_only \
  0 "public_cutover_ready=yes" \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=文档生成系统' \
  1 $'cutover_verified=no\nopen_webui_present=yes\ntitle=Open WebUI' \
  0 "[PASS] push_public_homepage_cutover regression checks passed" \
  0 "[PASS] public homepage cutover assets regression checks passed" \
  0 \
  1 \
  "public_homepage_state=open-webui" \
  "public_cutover_needed=yes" \
  "ready_to_apply=yes" \
  "next_action=apply_public_cutover"

assert_not_contains "-- readiness output --" "$TMP_DIR/summary_only.out"
assert_not_contains "-- public homepage verify --" "$TMP_DIR/summary_only.out"

echo "[PASS] report_public_homepage_cutover_status regression checks passed"
