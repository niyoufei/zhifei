#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
OUT_DIR="${2:-$ROOT/build/domain_bundle_release}"
ORIGIN_HOST="${DOCGEN_ORIGIN_HOST:-}"
PROXY_STACK="${DOCGEN_PROXY_STACK:-nginx}"
VERIFY_RESOLVE_HINT="${DOCGEN_VERIFY_RESOLVE_IP:-<origin-ip>}"

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain> [output-dir]" >&2
  echo "        example: $0 doc.niyoufei.com" >&2
  exit 1
fi

bash "$ROOT/scripts/render_linux_domain_bundle.sh" "$DOMAIN"

BUNDLE_NAME="${DOMAIN}.${PROXY_STACK}"
BUNDLE_DIR="$ROOT/build/domain_bundle/${BUNDLE_NAME}"
RELEASE_DIR="${OUT_DIR%/}"
ARCHIVE_BASENAME="${DOMAIN}.${PROXY_STACK}.tar.gz"
ARCHIVE_PATH="${RELEASE_DIR}/${ARCHIVE_BASENAME}"
CHECKSUM_PATH="${ARCHIVE_PATH}.sha256"
UPLOAD_HINT_PATH="${RELEASE_DIR}/${DOMAIN}.${PROXY_STACK}.upload.txt"

mkdir -p "$RELEASE_DIR"
tar -C "$ROOT/build/domain_bundle" -czf "$ARCHIVE_PATH" "$BUNDLE_NAME"
shasum -a 256 "$ARCHIVE_PATH" > "$CHECKSUM_PATH"

cat > "$UPLOAD_HINT_PATH" <<EOF
Upload package:
  ${ARCHIVE_BASENAME}

Recommended steps on the origin host:
  mkdir -p ~/docgen-domain
  tar -xzf ${ARCHIVE_BASENAME} -C ~/docgen-domain
  cd ~/docgen-domain/${BUNDLE_NAME}
  bash ./detect_linux_proxy_stack.sh ${DOMAIN}
  bash ./suggest_linux_origin_fix.sh ${DOMAIN}
  export DOCGEN_PROXY_STACK=${PROXY_STACK}
  export DOCGEN_ENABLE_STREAMLIT_SERVICE=0
  sudo -E ./install_bundle_on_origin.sh
  DOCGEN_PROXY_STACK=${PROXY_STACK} bash ./verify_linux_domain_origin.sh ${DOMAIN}
  DOCGEN_PROXY_STACK=${PROXY_STACK} DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_linux_domain_origin.sh ${DOMAIN}
  DOCGEN_PROXY_STACK=${PROXY_STACK} DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 DOCGEN_SKIP_PROXY_HOST_CHECK=1 bash ./verify_linux_domain_origin.sh ${DOMAIN}
  DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_ocr_runtime.sh
  bash ./inspect_public_homepage_origin_conf.sh ${DOMAIN}
  bash ./inspect_public_homepage_live_topology.sh ${DOMAIN}
  bash ./execute_public_homepage_cutover.sh ${DOMAIN}
  DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_HINT} bash ./execute_public_homepage_cutover.sh ${DOMAIN}
  DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${DOCGEN_SSL_PROFILE:-letsencrypt} bash ./execute_public_homepage_cutover.sh ${DOMAIN}
  DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${DOCGEN_SSL_PROFILE:-letsencrypt} DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_HINT} bash ./execute_public_homepage_cutover.sh ${DOMAIN}
  bash ./verify_public_homepage_cutover.sh https://${DOMAIN}
  bash ./verify_public_homepage_cutover.sh https://${DOMAIN} ${VERIFY_RESOLVE_HINT}
  bash ./verify_public_edge_health.sh https://${DOMAIN}
  bash ./verify_public_edge_health_stable.sh https://${DOMAIN}
  ZF_EDGE_PROFILE=stable bash ./verify_public_edge_health.sh https://${DOMAIN}
  bash ./verify_origin_app_health.sh
  DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}
  bash ./report_docgen_runtime_health_stable.sh https://${DOMAIN}
  ZF_EDGE_PROFILE=stable DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}
EOF

if [[ -n "$ORIGIN_HOST" ]]; then
  cat >> "$UPLOAD_HINT_PATH" <<EOF

If SSH is available:
  scp "$ARCHIVE_PATH" ${ORIGIN_HOST}:~/
  ssh ${ORIGIN_HOST} 'mkdir -p ~/docgen-domain && tar -xzf ~/${ARCHIVE_BASENAME} -C ~/docgen-domain && cd ~/docgen-domain/${BUNDLE_NAME} && bash ./detect_linux_proxy_stack.sh ${DOMAIN} || true && bash ./suggest_linux_origin_fix.sh ${DOMAIN} || true && export DOCGEN_PROXY_STACK=${PROXY_STACK} && export DOCGEN_ENABLE_STREAMLIT_SERVICE=0 && sudo -E ./install_bundle_on_origin.sh && DOCGEN_PROXY_STACK=${PROXY_STACK} bash ./verify_linux_domain_origin.sh ${DOMAIN} && DOCGEN_PROXY_STACK=${PROXY_STACK} DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_linux_domain_origin.sh ${DOMAIN} && DOCGEN_PROXY_STACK=${PROXY_STACK} DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 DOCGEN_SKIP_PROXY_HOST_CHECK=1 bash ./verify_linux_domain_origin.sh ${DOMAIN} && bash ./inspect_public_homepage_origin_conf.sh ${DOMAIN} && bash ./inspect_public_homepage_live_topology.sh ${DOMAIN}'
  DOCGEN_PREVIEW=1 bash "$ROOT/scripts/push_public_homepage_cutover.sh" ${DOMAIN} ${ORIGIN_HOST}
  bash "$ROOT/scripts/push_public_homepage_cutover.sh" ${DOMAIN} ${ORIGIN_HOST}
  DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_HINT} bash "$ROOT/scripts/push_public_homepage_cutover.sh" ${DOMAIN} ${ORIGIN_HOST}
  DOCGEN_REMOTE_APPLY=1 DOCGEN_SSL_PROFILE=${DOCGEN_SSL_PROFILE:-letsencrypt} bash "$ROOT/scripts/push_public_homepage_cutover.sh" ${DOMAIN} ${ORIGIN_HOST}
  DOCGEN_REMOTE_APPLY=1 DOCGEN_SSL_PROFILE=${DOCGEN_SSL_PROFILE:-letsencrypt} DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_HINT} bash "$ROOT/scripts/push_public_homepage_cutover.sh" ${DOMAIN} ${ORIGIN_HOST}
EOF
fi

echo "[OK] archive created: ${ARCHIVE_PATH}"
echo "[OK] checksum created: ${CHECKSUM_PATH}"
echo "[OK] upload hint: ${UPLOAD_HINT_PATH}"
