#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WRAPPER_SCRIPT="$ROOT/scripts/report_docgen_runtime_health_stable.sh"
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

STUB_SCRIPT="$TMP_DIR/stub-report.sh"
cat > "$STUB_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "zf_edge_profile=${ZF_EDGE_PROFILE:-}"
echo "docgen_runtime_summary_only=${DOCGEN_RUNTIME_SUMMARY_ONLY:-}"
echo "args=$*"
EOF
chmod +x "$STUB_SCRIPT"

echo "[STEP] wrapper should default to stable summary mode"
DOCGEN_RUNTIME_REPORT_SCRIPT="$STUB_SCRIPT" DOCGEN_RUNTIME_SUMMARY_ONLY= \
  bash "$WRAPPER_SCRIPT" https://doc.niyoufei.com > "$TMP_DIR/default.out"
assert_contains "zf_edge_profile=stable" "$TMP_DIR/default.out"
assert_contains "docgen_runtime_summary_only=1" "$TMP_DIR/default.out"
assert_contains "args=https://doc.niyoufei.com" "$TMP_DIR/default.out"

echo "[STEP] explicit summary override should pass through"
DOCGEN_RUNTIME_REPORT_SCRIPT="$STUB_SCRIPT" DOCGEN_RUNTIME_SUMMARY_ONLY=0 \
  bash "$WRAPPER_SCRIPT" https://doc.niyoufei.com > "$TMP_DIR/override.out"
assert_contains "zf_edge_profile=stable" "$TMP_DIR/override.out"
assert_contains "docgen_runtime_summary_only=0" "$TMP_DIR/override.out"

echo "[PASS] report_docgen_runtime_health_stable regression checks passed"
