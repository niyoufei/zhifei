#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WRAPPER_SCRIPT="$ROOT/scripts/verify_public_edge_health_stable.sh"
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

STUB_SCRIPT="$TMP_DIR/stub-verify.sh"
cat > "$STUB_SCRIPT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "zf_edge_profile=${ZF_EDGE_PROFILE:-}"
echo "zf_edge_observe_cycles=${ZF_EDGE_OBSERVE_CYCLES:-}"
echo "args=$*"
EOF
chmod +x "$STUB_SCRIPT"

echo "[STEP] wrapper should force stable profile"
DOCGEN_EDGE_VERIFY_SCRIPT="$STUB_SCRIPT" ZF_EDGE_PROFILE=default \
  bash "$WRAPPER_SCRIPT" https://doc.niyoufei.com > "$TMP_DIR/default.out"
assert_contains "zf_edge_profile=stable" "$TMP_DIR/default.out"
assert_contains "args=https://doc.niyoufei.com" "$TMP_DIR/default.out"

echo "[STEP] explicit threshold overrides should still pass through"
DOCGEN_EDGE_VERIFY_SCRIPT="$STUB_SCRIPT" ZF_EDGE_OBSERVE_CYCLES=5 \
  bash "$WRAPPER_SCRIPT" https://doc.niyoufei.com > "$TMP_DIR/override.out"
assert_contains "zf_edge_profile=stable" "$TMP_DIR/override.out"
assert_contains "zf_edge_observe_cycles=5" "$TMP_DIR/override.out"

echo "[PASS] verify_public_edge_health_stable regression checks passed"
