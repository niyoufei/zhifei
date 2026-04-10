#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/show_docgen_server_status.sh"
TMP_DIR="$(mktemp -d)"
APP_ROOT="$TMP_DIR/app"
RELEASE_DIR="$APP_ROOT/releases"
INSPECTION_DIR="$APP_ROOT/logs/readonly_inspection"
RETENTION_DIR="$APP_ROOT/logs/readonly_retention"
MOCK_DIR="$TMP_DIR/mock"
OUTPUT="$TMP_DIR/output.log"
FAIL_OUTPUT="$TMP_DIR/fail-output.log"

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

mkdir -p "$RELEASE_DIR" "$INSPECTION_DIR" "$RETENTION_DIR" "$MOCK_DIR"
printf '%s\n' "docgen-server-app-20260401-222243.tgz" > "$RELEASE_DIR/latest-release.txt"

cat > "$INSPECTION_DIR/latest-status.txt" <<'EOF'
run_id=20260401-142415
release_dir_state=pass
server_worktree_state=pass
runtime_monitoring_state=pass
readonly_retention_state=pass
readonly_retention_run_id=20260401-142421
readonly_retention_prune_candidates_count=0
readonly_retention_execute_allowed=no
next_action=healthy
overall_state=pass
EOF

cat > "$RETENTION_DIR/latest-status.txt" <<'EOF'
run_id=20260401-142421
prune_candidates_count=0
execute_allowed=no
next_action=healthy
overall_state=pass
EOF

cat > "$MOCK_DIR/systemctl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" = "is-active" && "${2:-}" = "docgen-autoplan.service" ]]; then
  printf 'active\n'
  exit 0
fi
exit 1
EOF

cat > "$MOCK_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
url="${*: -1}"
case "$url" in
  http://127.0.0.1:8010/health)
    printf '%s' '{"ok":true,"service":"docgen"}'
    ;;
  http://127.0.0.1:8501/_stcore/health)
    printf 'ok'
    ;;
  *)
    exit 1
    ;;
esac
EOF

chmod 755 "$MOCK_DIR/systemctl" "$MOCK_DIR/curl"

DOCGEN_SYSTEMCTL_BIN="$MOCK_DIR/systemctl" \
DOCGEN_CURL_BIN="$MOCK_DIR/curl" \
bash "$SCRIPT" "$APP_ROOT" >"$OUTPUT" 2>&1

assert_contains "latest_release=docgen-server-app-20260401-222243.tgz" "$OUTPUT"
assert_contains "release_pointer_state=pass" "$OUTPUT"
assert_contains "inspection_status_state=pass" "$OUTPUT"
assert_contains "inspection_run_id=20260401-142415" "$OUTPUT"
assert_contains "readonly_retention_run_id=20260401-142421" "$OUTPUT"
assert_contains "retention_status_sync_state=pass" "$OUTPUT"
assert_contains "service_unit_state=active" "$OUTPUT"
assert_contains "backend_health_state=pass" "$OUTPUT"
assert_contains "streamlit_health_state=pass" "$OUTPUT"
assert_contains "next_action=healthy" "$OUTPUT"
assert_contains "overall_state=pass" "$OUTPUT"
assert_contains "[SUMMARY] all checks passed." "$OUTPUT"

cat > "$RETENTION_DIR/latest-status.txt" <<'EOF'
run_id=20260401-999999
prune_candidates_count=0
execute_allowed=no
next_action=healthy
overall_state=pass
EOF

if DOCGEN_SYSTEMCTL_BIN="$MOCK_DIR/systemctl" \
  DOCGEN_CURL_BIN="$MOCK_DIR/curl" \
  bash "$SCRIPT" "$APP_ROOT" >"$FAIL_OUTPUT" 2>&1; then
  echo "[FAIL] expected mismatch run to fail" >&2
  cat "$FAIL_OUTPUT" >&2
  exit 1
fi

assert_contains "retention_status_sync_state=fail" "$FAIL_OUTPUT"
assert_contains "next_action=run-readonly-inspection" "$FAIL_OUTPUT"
assert_contains "overall_state=fail" "$FAIL_OUTPUT"

echo "[PASS] show_docgen_server_status regression checks passed"
