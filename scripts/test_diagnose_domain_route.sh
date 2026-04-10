#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$ROOT/scripts/diagnose_domain_route.sh"
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

cat > "$TMP_DIR/dig" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "${MOCK_DIG_OUTPUT:-}"
EOF

cat > "$TMP_DIR/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

head_mode=0
resolve_mode=0
url=""
for ((i=1; i<=$#; i++)); do
  arg="${!i}"
  if [[ "$arg" == "-I" ]]; then
    head_mode=1
  elif [[ "$arg" == "--resolve" ]]; then
    resolve_mode=1
  elif [[ "$arg" != -* ]]; then
    url="$arg"
  fi
done

status="000"
case "$url" in
  http://doc.niyoufei.com)
    if [[ "$resolve_mode" = "1" ]]; then
      status="200"
    else
      status="521"
    fi
    ;;
  https://doc.niyoufei.com)
    if [[ "$resolve_mode" = "1" ]]; then
      status="302"
    else
      status="525"
    fi
    ;;
esac

printf 'HTTP/1.1 %s MOCK\r\n' "$status"
if [[ "$head_mode" = "0" ]]; then
  printf 'Server: mock\r\n'
fi
EOF

chmod +x "$TMP_DIR/dig" "$TMP_DIR/curl"

run_case() {
  local case_name="$1"
  shift
  local out="$TMP_DIR/${case_name}.out"
  PATH="$TMP_DIR:$PATH" "$@" > "$out"
  LAST_OUTPUT_FILE="$out"
}

echo "[STEP] edge failure with fake-ip dns and origin override"
run_case with_origin env MOCK_DIG_OUTPUT=$'198.18.0.1\n104.21.1.2' bash "$SCRIPT" doc.niyoufei.com 199.180.118.204
assert_contains "[WARN] dns: 198.18.0.1 落在 198.18.0.0/15" "$LAST_OUTPUT_FILE"
assert_contains "[WARN] edge-http: HTTP 521" "$LAST_OUTPUT_FILE"
assert_contains "[WARN] edge-https: HTTP 525" "$LAST_OUTPUT_FILE"
assert_contains "[OK] origin-http: HTTP 200" "$LAST_OUTPUT_FILE"
assert_contains "[OK] origin-https: HTTP 302" "$LAST_OUTPUT_FILE"

echo "[STEP] without origin ip should skip origin checks"
run_case no_origin env MOCK_DIG_OUTPUT=$'104.21.1.2' bash "$SCRIPT" doc.niyoufei.com
assert_contains "[EDGE] http://doc.niyoufei.com" "$LAST_OUTPUT_FILE"
assert_contains "[EDGE] https://doc.niyoufei.com" "$LAST_OUTPUT_FILE"
assert_not_contains "[ORIGIN]" "$LAST_OUTPUT_FILE"

echo "[PASS] diagnose_domain_route regression checks passed"
