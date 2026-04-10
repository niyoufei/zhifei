#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_SCRIPT="$ROOT/scripts/report_docgen_runtime_health.sh"
TMP_DIR="$(mktemp -d)"

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
  local origin_rc="$2"
  local origin_log="$3"
  local edge_rc="$4"
  local edge_log="$5"
  local public_rc="$6"
  local public_log="$7"
  local expected_rc="$8"
  local summary_only="$9"
  shift 9
  local output_file="$TMP_DIR/${case_name}.out"

  local origin_stub="$TMP_DIR/${case_name}-origin.sh"
  local edge_stub="$TMP_DIR/${case_name}-edge.sh"
  local public_stub="$TMP_DIR/${case_name}-public.sh"

  cat > "$origin_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${origin_log}
LOG
exit ${origin_rc}
EOF

  cat > "$edge_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${edge_log}
LOG
exit ${edge_rc}
EOF

  cat > "$public_stub" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cat <<'LOG'
${public_log}
LOG
exit ${public_rc}
EOF

  chmod +x "$origin_stub" "$edge_stub" "$public_stub"

  set +e
  DOCGEN_RUNTIME_ORIGIN_SCRIPT="$origin_stub" \
  DOCGEN_RUNTIME_EDGE_SCRIPT="$edge_stub" \
  DOCGEN_RUNTIME_PUBLIC_VERIFY_SCRIPT="$public_stub" \
  DOCGEN_RUNTIME_SUMMARY_ONLY="$summary_only" \
  bash "$REPORT_SCRIPT" https://doc.niyoufei.com >"$output_file" 2>&1
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

echo "[STEP] fully healthy runtime"
run_case \
  healthy \
  0 "origin_app_state=healthy" \
  0 $'public_edge_state=healthy\nedge_profile=stable\nobserve_cycles=3\nedge_home_fail_streak_threshold=2\nedge_streamlit_fail_streak_threshold=2\nedge_home_drop_at=none\nedge_streamlit_drop_at=none' \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=Streamlit' \
  0 \
  0 \
  "origin_app_state=pass" \
  "public_edge_state=pass" \
  "public_homepage_state=docgen" \
  "public_edge_profile=stable" \
  "public_edge_observe_cycles=3" \
  "public_edge_home_fail_streak_threshold=2" \
  "public_edge_streamlit_fail_streak_threshold=2" \
  "public_edge_home_drop_at=none" \
  "public_edge_streamlit_drop_at=none" \
  "runtime_monitoring_state=pass" \
  "next_action=healthy"

echo "[STEP] origin degraded should block runtime pass"
run_case \
  origin_fail \
  1 "origin_app_state=degraded" \
  0 $'public_edge_state=healthy\nedge_profile=stable\nobserve_cycles=2\nedge_home_fail_streak_threshold=2\nedge_streamlit_fail_streak_threshold=2\nedge_home_drop_at=none\nedge_streamlit_drop_at=none' \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=Streamlit' \
  1 \
  0 \
  "origin_app_state=fail" \
  "public_edge_state=pass" \
  "public_homepage_state=docgen" \
  "runtime_monitoring_state=fail" \
  "next_action=fix_origin_runtime"

echo "[STEP] edge degraded should request edge inspection"
run_case \
  edge_fail \
  0 "origin_app_state=healthy" \
  1 $'public_edge_state=degraded\nedge_profile=stable\nobserve_cycles=3\nedge_home_fail_streak_threshold=2\nedge_streamlit_fail_streak_threshold=2\nedge_home_drop_at=2\nedge_streamlit_drop_at=2' \
  1 $'cutover_verified=no\nopen_webui_present=no\ntitle=' \
  1 \
  0 \
  "origin_app_state=pass" \
  "public_edge_state=fail" \
  "public_homepage_state=unknown" \
  "public_edge_home_drop_at=2" \
  "public_edge_streamlit_drop_at=2" \
  "runtime_monitoring_state=fail" \
  "next_action=inspect_public_edge"

echo "[STEP] summary-only should suppress logs"
run_case \
  summary_only \
  0 "origin_app_state=healthy" \
  0 $'public_edge_state=healthy\nedge_profile=stable\nobserve_cycles=3\nedge_home_fail_streak_threshold=2\nedge_streamlit_fail_streak_threshold=2\nedge_home_drop_at=none\nedge_streamlit_drop_at=none' \
  0 $'cutover_verified=yes\nopen_webui_present=no\ntitle=Streamlit' \
  0 \
  1 \
  "runtime_monitoring_state=pass" \
  "next_action=healthy"

assert_not_contains "-- origin app verify --" "$TMP_DIR/summary_only.out"
assert_not_contains "-- public edge verify --" "$TMP_DIR/summary_only.out"

echo "[PASS] report_docgen_runtime_health regression checks passed"
