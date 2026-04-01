#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
CALLS="$TMP_DIR/calls.log"
PYTHON_BIN="$TMP_DIR/mock-python"
SMOKE_SCRIPT="$TMP_DIR/mock_smoke.py"
ADMIN_SCRIPT="$TMP_DIR/mock_admin.sh"

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
    echo "[FAIL] unexpected text: $needle" >&2
    echo "--- $file ---" >&2
    cat "$file" >&2
    exit 1
  fi
}

cat > "$PYTHON_BIN" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

CALLS_FILE="${DOCGEN_TEST_CALLS:?}"
if [[ "${1:-}" = "-" ]]; then
  body="$(cat)"
  printf 'stdin\n' >>"$CALLS_FILE"
  if grep -Fq -- "consistency(mode=" <<<"$body"; then
    echo "[WARN] consistency(mode=warn): topic=NA domain_key=NA region_key=NA"
  else
    echo "[OK] consistency_gate: OK (mode=warn)"
  fi
  exit 0
fi

printf 'py %s\n' "$*" >>"$CALLS_FILE"
echo "[SUCCESS] mock smoke"
EOF

cat > "$SMOKE_SCRIPT" <<'EOF'
print("mock smoke body")
EOF

cat > "$ADMIN_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'admin\n' >>"${DOCGEN_TEST_CALLS:?}"
echo "[SUMMARY] local ui/admin smoke ok"
EOF

chmod +x "$PYTHON_BIN" "$ADMIN_SCRIPT"

run_case() {
  local target_script="$1"
  local output_file="$2"
  shift 2
  DOCGEN_TEST_CALLS="$CALLS" \
  DOCGEN_SMOKE_PYTHON="$PYTHON_BIN" \
  DOCGEN_SMOKE_E2E_SCRIPT="$SMOKE_SCRIPT" \
  DOCGEN_LOCAL_UI_ADMIN_SCRIPT="$ADMIN_SCRIPT" \
  "$@" \
  bash "$target_script" >"$output_file" 2>&1
}

ROOT_OUTPUT="$TMP_DIR/root.out"
run_case "$ROOT/scripts/run_smoke.sh" "$ROOT_OUTPUT" env DOCGEN_RUN_LOCAL_UI_ADMIN_SMOKE=1
assert_contains "[SUCCESS] mock smoke" "$ROOT_OUTPUT"
assert_contains "[WARN] consistency(mode=warn): topic=NA domain_key=NA region_key=NA" "$ROOT_OUTPUT"
assert_contains "[OK] consistency_gate: OK (mode=warn)" "$ROOT_OUTPUT"
assert_contains "[INFO] local_ui_admin_smoke: enabled ($ADMIN_SCRIPT)" "$ROOT_OUTPUT"
assert_contains "[SUMMARY] local ui/admin smoke ok" "$ROOT_OUTPUT"

BACKEND_OUTPUT="$TMP_DIR/backend.out"
run_case "$ROOT/backend/scripts/run_smoke.sh" "$BACKEND_OUTPUT" env DOCGEN_RUN_LOCAL_UI_ADMIN_SMOKE=1
assert_contains "[SUCCESS] mock smoke" "$BACKEND_OUTPUT"
assert_contains "[INFO] local_ui_admin_smoke: enabled ($ADMIN_SCRIPT)" "$BACKEND_OUTPUT"
assert_contains "[SUMMARY] local ui/admin smoke ok" "$BACKEND_OUTPUT"

SKIP_OUTPUT="$TMP_DIR/skip.out"
run_case "$ROOT/scripts/run_smoke.sh" "$SKIP_OUTPUT" env DOCGEN_RUN_LOCAL_UI_ADMIN_SMOKE=0
assert_not_contains "local_ui_admin_smoke: enabled" "$SKIP_OUTPUT"

assert_contains "py $SMOKE_SCRIPT" "$CALLS"
assert_contains "admin" "$CALLS"

echo "[PASS] run_smoke opt-in local ops regression checks passed"
