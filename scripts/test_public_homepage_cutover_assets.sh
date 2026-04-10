#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-doc.niyoufei.com}"
ORIGIN_HOST="${2:-root@199.180.118.204}"
ORIGIN_IP="${3:-199.180.118.204}"

RENDER_SCRIPT="$ROOT/scripts/render_linux_domain_bundle.sh"
PACKAGE_SCRIPT="$ROOT/scripts/package_linux_domain_bundle.sh"
INSPECT_SCRIPT="$ROOT/scripts/inspect_public_homepage_origin_conf.sh"
TOPOLOGY_SCRIPT="$ROOT/scripts/inspect_public_homepage_live_topology.sh"
EXECUTE_SCRIPT="$ROOT/scripts/execute_public_homepage_cutover.sh"
CUTOVER_SCRIPT="$ROOT/scripts/cutover_public_homepage_origin.sh"
MULTI_CUTOVER_SCRIPT="$ROOT/scripts/cutover_public_homepage_upstream_targets.sh"
VERIFY_SCRIPT="$ROOT/scripts/verify_public_homepage_cutover.sh"

TMP_DIR="$(mktemp -d)"
RENDER_OUT="$TMP_DIR/render"
RELEASE_OUT="$TMP_DIR/release"
FAKE_NGINX_DIR="$TMP_DIR/nginx"
FAKE_CONF="$FAKE_NGINX_DIR/${DOMAIN}.conf"
INSPECT_LOG="$TMP_DIR/inspect.log"
EXECUTE_LOG="$TMP_DIR/execute.log"
CUTOVER_LOG="$TMP_DIR/cutover.log"
VERIFY_LOG="$TMP_DIR/verify.log"

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

assert_file_exists() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing file: $path"
}

mkdir -p "$FAKE_NGINX_DIR"
cat > "$FAKE_CONF" <<EOF
server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}
EOF

echo "[STEP] render bundle"
DOCGEN_PROXY_STACK=nginx DOCGEN_SSL_PROFILE=letsencrypt \
bash "$RENDER_SCRIPT" "$DOMAIN" "$RENDER_OUT" >/dev/null

BUNDLE_DIR="$RENDER_OUT/${DOMAIN}.nginx"
README_PATH="$BUNDLE_DIR/README.txt"
assert_file_exists "$README_PATH"
assert_file_exists "$BUNDLE_DIR/inspect_public_homepage_origin_conf.sh"
assert_file_exists "$BUNDLE_DIR/inspect_public_homepage_live_topology.sh"
assert_file_exists "$BUNDLE_DIR/cutover_public_homepage_upstream_targets.sh"
assert_file_exists "$BUNDLE_DIR/execute_public_homepage_cutover.sh"
assert_file_exists "$BUNDLE_DIR/verify_public_homepage_cutover.sh"
assert_file_exists "$BUNDLE_DIR/verify_public_edge_health.sh"
assert_file_exists "$BUNDLE_DIR/verify_public_edge_health_stable.sh"
assert_file_exists "$BUNDLE_DIR/verify_origin_app_health.sh"
assert_file_exists "$BUNDLE_DIR/report_docgen_runtime_health.sh"
assert_file_exists "$BUNDLE_DIR/report_docgen_runtime_health_stable.sh"
assert_file_exists "$BUNDLE_DIR/verify_ocr_runtime.sh"
assert_contains "export DOCGEN_ENABLE_STREAMLIT_SERVICE=0" "$README_PATH"
assert_contains "DOCGEN_ENABLE_STREAMLIT_SERVICE=1 sudo -E ./install_bundle_on_origin.sh" "$README_PATH"
assert_contains "bash ./inspect_public_homepage_live_topology.sh ${DOMAIN}" "$README_PATH"
assert_contains "DOCGEN_VERIFY_RESOLVE_IP=<origin-ip> bash ./execute_public_homepage_cutover.sh ${DOMAIN}" "$README_PATH"
assert_contains "bash ./verify_public_homepage_cutover.sh https://${DOMAIN} <origin-ip>" "$README_PATH"
assert_contains "DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}" "$README_PATH"
assert_contains "bash ./report_docgen_runtime_health_stable.sh https://${DOMAIN}" "$README_PATH"
assert_contains "ZF_EDGE_PROFILE=stable DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}" "$README_PATH"
assert_contains "bash ./verify_public_edge_health.sh https://${DOMAIN}" "$README_PATH"
assert_contains "bash ./verify_public_edge_health_stable.sh https://${DOMAIN}" "$README_PATH"
assert_contains "ZF_EDGE_PROFILE=stable bash ./verify_public_edge_health.sh https://${DOMAIN}" "$README_PATH"
assert_contains "bash ./verify_origin_app_health.sh" "$README_PATH"
assert_contains "DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_ocr_runtime.sh" "$README_PATH"

echo "[STEP] package bundle"
DOCGEN_ORIGIN_HOST="$ORIGIN_HOST" DOCGEN_VERIFY_RESOLVE_IP="$ORIGIN_IP" DOCGEN_PROXY_STACK=nginx DOCGEN_SSL_PROFILE=letsencrypt \
bash "$PACKAGE_SCRIPT" "$DOMAIN" "$RELEASE_OUT" >/dev/null

ARCHIVE_PATH="$RELEASE_OUT/${DOMAIN}.nginx.tar.gz"
UPLOAD_HINT="$RELEASE_OUT/${DOMAIN}.nginx.upload.txt"
assert_file_exists "$ARCHIVE_PATH"
assert_file_exists "$UPLOAD_HINT"
assert_contains "DOCGEN_PREVIEW=1 bash \"$ROOT/scripts/push_public_homepage_cutover.sh\" ${DOMAIN} ${ORIGIN_HOST}" "$UPLOAD_HINT"
assert_contains "DOCGEN_VERIFY_RESOLVE_IP=${ORIGIN_IP} bash \"$ROOT/scripts/push_public_homepage_cutover.sh\" ${DOMAIN} ${ORIGIN_HOST}" "$UPLOAD_HINT"
assert_contains "bash ./verify_public_homepage_cutover.sh https://${DOMAIN} ${ORIGIN_IP}" "$UPLOAD_HINT"
assert_contains "bash ./inspect_public_homepage_live_topology.sh ${DOMAIN}" "$UPLOAD_HINT"
assert_contains "DOCGEN_PROXY_STACK=nginx DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_linux_domain_origin.sh ${DOMAIN}" "$UPLOAD_HINT"
assert_contains "DOCGEN_PROXY_STACK=nginx DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 DOCGEN_SKIP_PROXY_HOST_CHECK=1 bash ./verify_linux_domain_origin.sh ${DOMAIN}" "$UPLOAD_HINT"
assert_contains "bash ./verify_public_edge_health.sh https://${DOMAIN}" "$UPLOAD_HINT"
assert_contains "bash ./verify_public_edge_health_stable.sh https://${DOMAIN}" "$UPLOAD_HINT"
assert_contains "ZF_EDGE_PROFILE=stable bash ./verify_public_edge_health.sh https://${DOMAIN}" "$UPLOAD_HINT"
assert_contains "bash ./verify_origin_app_health.sh" "$UPLOAD_HINT"
assert_contains "DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}" "$UPLOAD_HINT"
assert_contains "bash ./report_docgen_runtime_health_stable.sh https://${DOMAIN}" "$UPLOAD_HINT"
assert_contains "ZF_EDGE_PROFILE=stable DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}" "$UPLOAD_HINT"
assert_contains "DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_ocr_runtime.sh" "$UPLOAD_HINT"

TAR_LIST="$TMP_DIR/tar.list"
tar -tzf "$ARCHIVE_PATH" > "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/inspect_public_homepage_origin_conf.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/inspect_public_homepage_live_topology.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/cutover_public_homepage_upstream_targets.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/execute_public_homepage_cutover.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/verify_public_homepage_cutover.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/verify_public_edge_health.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/verify_public_edge_health_stable.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/verify_origin_app_health.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/report_docgen_runtime_health.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/report_docgen_runtime_health_stable.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/verify_ocr_runtime.sh" "$TAR_LIST"
assert_contains "${DOMAIN}.nginx/public_homepage_cutover.md" "$TAR_LIST"

INSTALL_SCRIPT="$BUNDLE_DIR/install_bundle_on_origin.sh"
assert_file_exists "$INSTALL_SCRIPT"
assert_contains 'ENABLE_STREAMLIT_SERVICE="${DOCGEN_ENABLE_STREAMLIT_SERVICE:-0}"' "$INSTALL_SCRIPT"
assert_contains 'streamlit service: disabled (backend-managed)' "$INSTALL_SCRIPT"
assert_contains 'systemctl disable --now "${STREAMLIT_SERVICE_NAME}" >/dev/null 2>&1 || true' "$INSTALL_SCRIPT"

echo "[STEP] inspect fake nginx conf"
DOCGEN_OS_NAME=Linux DOCGEN_NGINX_SEARCH_DIRS="$FAKE_NGINX_DIR" \
bash "$INSPECT_SCRIPT" "$DOMAIN" > "$INSPECT_LOG"
assert_contains "[INFO] match_count=1" "$INSPECT_LOG"
assert_contains "[RECOMMEND] target_conf_path=${FAKE_CONF}" "$INSPECT_LOG"
assert_contains "[RECOMMEND] current_upstream_kind=open-webui" "$INSPECT_LOG"

echo "[STEP] inspect fake live topology"
FAKE_XRAY_DIR="$TMP_DIR/xray"
mkdir -p "$FAKE_XRAY_DIR"
cat > "$FAKE_XRAY_DIR/02_VLESS_TCP_inbounds.json" <<EOF
{
  "fallbacks": [
    {"dest": 443}
  ]
}
EOF
DOCGEN_OS_NAME=Linux DOCGEN_NGINX_SEARCH_DIRS="$FAKE_NGINX_DIR" DOCGEN_XRAY_SEARCH_DIR="$FAKE_XRAY_DIR" \
bash "$TOPOLOGY_SCRIPT" "$DOMAIN" > "$TMP_DIR/topology.log"
assert_contains "[RECOMMEND] topology=xray-nginx-single-upstream" "$TMP_DIR/topology.log"
assert_contains "[RECOMMEND] patch_count=1" "$TMP_DIR/topology.log"

echo "[STEP] multi-upstream dry-run rewrite helper"
bash "$MULTI_CUTOVER_SCRIPT" "$DOMAIN" "$FAKE_CONF" > "$TMP_DIR/multi-cutover.log"
assert_contains "[INFO] dry-run only; no files written." "$TMP_DIR/multi-cutover.log"
assert_contains "proxy_pass http://127.0.0.1:3000;" "$TMP_DIR/multi-cutover.log"

echo "[STEP] execute dry-run orchestration"
DOCGEN_OS_NAME=Linux DOCGEN_NGINX_SEARCH_DIRS="$FAKE_NGINX_DIR" DOCGEN_VERIFY_BASE_URL="http://127.0.0.1:8501" \
bash "$EXECUTE_SCRIPT" "$DOMAIN" > "$EXECUTE_LOG"
assert_contains "[STEP] dry-run cutover config" "$EXECUTE_LOG"
assert_contains "target_conf_path=${FAKE_CONF}" "$EXECUTE_LOG"
assert_contains "[INFO] 当前为 dry-run 模式，未写入源站配置。" "$EXECUTE_LOG"

echo "[STEP] cutover dry-run render"
bash "$CUTOVER_SCRIPT" "$DOMAIN" "$FAKE_CONF" > "$CUTOVER_LOG"
assert_contains "[INFO] dry-run rendered config" "$CUTOVER_LOG"
assert_contains "target_conf_path=${FAKE_CONF}" "$CUTOVER_LOG"
assert_contains "proxy_pass http://127.0.0.1:8501;" "$CUTOVER_LOG"

echo "[STEP] verify local docgen homepage"
bash "$VERIFY_SCRIPT" "http://127.0.0.1:8501" > "$VERIFY_LOG"
assert_contains "home_status=200" "$VERIFY_LOG"
assert_contains "stcore_body=ok" "$VERIFY_LOG"
assert_contains "cutover_verified=yes" "$VERIFY_LOG"

echo "[PASS] public homepage cutover assets regression checks passed"
