#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUSH_SCRIPT="$ROOT/scripts/push_docgen_server_release.sh"
TMP_DIR="$(mktemp -d)"
LOCAL_RELEASE_DIR="$TMP_DIR/release"
CALLS="$TMP_DIR/calls.log"

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

mkdir -p "$LOCAL_RELEASE_DIR"
printf 'payload\n' > "$LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.tgz"
printf 'abcd1234  docgen-server-app-20260401-140244.tgz\n' > "$LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.tgz.sha256"
printf '{"release_id":"20260401-140244"}\n' > "$LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.manifest.json"
printf 'summary\n' > "$LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.summary.txt"
printf 'notes\n' > "$LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.notes.txt"
printf 'ops\n' > "$LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.ops.txt"
printf 'docgen-server-app-20260401-140244.tgz\n' > "$LOCAL_RELEASE_DIR/latest-release.txt"
printf 'latest summary\n' > "$LOCAL_RELEASE_DIR/latest-change-summary.txt"
printf 'latest notes\n' > "$LOCAL_RELEASE_DIR/latest-release-notes.txt"
printf 'latest ops\n' > "$LOCAL_RELEASE_DIR/latest-release-ops.txt"
printf 'docgen-server-app-20260401-140244.tgz\n' > "$LOCAL_RELEASE_DIR/releases-index.txt"
ln -s "docgen-server-app-20260401-140244.tgz" "$LOCAL_RELEASE_DIR/docgen-server-app.tgz"
ln -s "docgen-server-app-20260401-140244.tgz.sha256" "$LOCAL_RELEASE_DIR/docgen-server-app.tgz.sha256"
ln -s "docgen-server-app-20260401-140244.manifest.json" "$LOCAL_RELEASE_DIR/docgen-server-app.manifest.json"

cat > "$TMP_DIR/mock-scp" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'scp %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-scp"

cat > "$TMP_DIR/mock-ssh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'ssh %s\n' "$*" >>"${DOCGEN_TEST_CALLS:?}"
EOF
chmod +x "$TMP_DIR/mock-ssh"

OUTPUT="$TMP_DIR/output.log"
DOCGEN_LOCAL_RELEASE_DIR="$LOCAL_RELEASE_DIR" \
DOCGEN_REMOTE_RELEASE_DIR="/opt/docgen/releases" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
DOCGEN_TEST_CALLS="$CALLS" \
bash "$PUSH_SCRIPT" "root@example.com" >"$OUTPUT" 2>&1

assert_contains "[OK] release uploaded: docgen-server-app-20260401-140244.tgz -> root@example.com:/opt/docgen/releases" "$OUTPUT"
assert_contains "scp $LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.tgz $LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.tgz.sha256 $LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.manifest.json $LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.summary.txt $LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.notes.txt $LOCAL_RELEASE_DIR/docgen-server-app-20260401-140244.ops.txt $LOCAL_RELEASE_DIR/latest-release.txt $LOCAL_RELEASE_DIR/latest-change-summary.txt $LOCAL_RELEASE_DIR/latest-release-notes.txt $LOCAL_RELEASE_DIR/latest-release-ops.txt $LOCAL_RELEASE_DIR/releases-index.txt root@example.com:/opt/docgen/releases/" "$CALLS"
assert_contains "ssh root@example.com set -euo pipefail" "$CALLS"
assert_contains "ln -sfn docgen-server-app-20260401-140244.tgz docgen-server-app.tgz" "$CALLS"
assert_contains "ln -sfn docgen-server-app-20260401-140244.tgz.sha256 docgen-server-app.tgz.sha256" "$CALLS"
assert_contains "ln -sfn docgen-server-app-20260401-140244.manifest.json docgen-server-app.manifest.json" "$CALLS"
assert_contains "sha256sum -c docgen-server-app.tgz.sha256" "$CALLS"

PREVIEW_OUTPUT="$TMP_DIR/preview.log"
DOCGEN_PREVIEW=1 \
DOCGEN_LOCAL_RELEASE_DIR="$LOCAL_RELEASE_DIR" \
DOCGEN_REMOTE_RELEASE_DIR="/opt/docgen/releases" \
DOCGEN_SCP_BIN="$TMP_DIR/mock-scp" \
DOCGEN_SSH_BIN="$TMP_DIR/mock-ssh" \
bash "$PUSH_SCRIPT" "root@example.com" >"$PREVIEW_OUTPUT" 2>&1

assert_contains "remote_host=root@example.com" "$PREVIEW_OUTPUT"
assert_contains "latest_release=docgen-server-app-20260401-140244.tgz" "$PREVIEW_OUTPUT"
assert_contains "scp_command=" "$PREVIEW_OUTPUT"
assert_contains "ssh_command=" "$PREVIEW_OUTPUT"

echo "[PASS] push_docgen_server_release regression checks passed"
