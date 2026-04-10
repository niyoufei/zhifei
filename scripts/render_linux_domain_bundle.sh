#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
OUT_DIR="${2:-$ROOT/build/domain_bundle}"
PROXY_STACK="${DOCGEN_PROXY_STACK:-nginx}"
ENABLE_STREAMLIT_SERVICE="${DOCGEN_ENABLE_STREAMLIT_SERVICE:-0}"
SSL_CERT_PATH="${DOCGEN_SSL_CERT:-}"
SSL_KEY_PATH="${DOCGEN_SSL_KEY:-}"
SSL_PROFILE="${DOCGEN_SSL_PROFILE:-}"

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain> [output-dir]" >&2
  echo "        example: $0 doc.niyoufei.com" >&2
  exit 1
fi

if [[ "$SSL_PROFILE" = "letsencrypt" && -z "$SSL_CERT_PATH" && -z "$SSL_KEY_PATH" ]]; then
  SSL_CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  SSL_KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
fi

BUNDLE_NAME="${DOMAIN}.${PROXY_STACK}"
BUNDLE_DIR="${OUT_DIR%/}/${BUNDLE_NAME}"
mkdir -p "$BUNDLE_DIR"

cp "$ROOT/deploy/systemd/docgen-autoplan.service" \
  "$BUNDLE_DIR/docgen-autoplan.service"

sed "s|https://__DOCGEN_DOMAIN__|https://${DOMAIN}|g" \
  "$ROOT/deploy/systemd/docgen-streamlit.service" \
  > "$BUNDLE_DIR/docgen-streamlit.service"

sed "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
  "$ROOT/deploy/caddy/Caddyfile.docgen-streamlit.template" \
  > "$BUNDLE_DIR/Caddyfile.docgen-streamlit"

if [[ -n "$SSL_CERT_PATH" || -n "$SSL_KEY_PATH" ]]; then
  if [[ -z "$SSL_CERT_PATH" || -z "$SSL_KEY_PATH" ]]; then
    echo "[ERROR] DOCGEN_SSL_CERT 与 DOCGEN_SSL_KEY 必须同时提供。" >&2
    exit 1
  fi
  sed \
    -e "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
    -e "s|__DOCGEN_SSL_CERT__|${SSL_CERT_PATH}|g" \
    -e "s|__DOCGEN_SSL_KEY__|${SSL_KEY_PATH}|g" \
    "$ROOT/deploy/nginx/docgen-streamlit-origin-ssl.conf.template" \
    > "$BUNDLE_DIR/docgen-streamlit-origin.conf"
else
  sed "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
    "$ROOT/deploy/nginx/docgen-streamlit-origin.conf.template" \
    > "$BUNDLE_DIR/docgen-streamlit-origin.conf"
fi

cat > "$BUNDLE_DIR/README.txt" <<EOF
DocGen Linux domain bundle
==========================

Domain: ${DOMAIN}
Proxy stack: ${PROXY_STACK}

Files:
- docgen-autoplan.service
- docgen-streamlit.service (optional)
- docgen-streamlit-origin.conf
- Caddyfile.docgen-streamlit
- cutover_public_homepage_origin.sh
- cutover_public_homepage_upstream_targets.sh
- inspect_public_homepage_origin_conf.sh
- inspect_public_homepage_live_topology.sh
- execute_public_homepage_cutover.sh
- verify_public_homepage_cutover.sh
- verify_public_edge_health.sh
- verify_public_edge_health_stable.sh
- verify_origin_app_health.sh
- report_docgen_runtime_health.sh
- report_docgen_runtime_health_stable.sh
- public_homepage_cutover.md
- install_bundle_on_origin.sh
- detect_linux_proxy_stack.sh
- suggest_linux_origin_fix.sh
- generate_origin_tls_csr.sh
- verify_linux_domain_origin.sh
- verify_ocr_runtime.sh

Apply on the Linux origin host:

1. Detect proxy stack if uncertain:
   bash ./detect_linux_proxy_stack.sh ${DOMAIN}

2. Print recommended next step:
   bash ./suggest_linux_origin_fix.sh ${DOMAIN}

3. Select proxy stack:
   export DOCGEN_PROXY_STACK=${PROXY_STACK}

4. Default to single-service install:
   export DOCGEN_ENABLE_STREAMLIT_SERVICE=${ENABLE_STREAMLIT_SERVICE}

5. Install:
   sudo -E ./install_bundle_on_origin.sh

6. Verify:
   DOCGEN_PROXY_STACK=${PROXY_STACK} bash ./verify_linux_domain_origin.sh ${DOMAIN}

   Optional OCR verify for scanned-PDF/image ingest hosts:
   DOCGEN_PROXY_STACK=${PROXY_STACK} DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_linux_domain_origin.sh ${DOMAIN}

   Optional OCR verify for xray/nginx fallback hosts without local :80/:443 listeners:
   DOCGEN_PROXY_STACK=${PROXY_STACK} DOCGEN_EXPECT_OCR=1 DOCGEN_EXPECT_OCR_CHINESE=1 DOCGEN_SKIP_PROXY_HOST_CHECK=1 bash ./verify_linux_domain_origin.sh ${DOMAIN}

   Optional dedicated OCR smoke:
   DOCGEN_EXPECT_OCR_CHINESE=1 bash ./verify_ocr_runtime.sh

7. Optional standalone Streamlit systemd unit:
   DOCGEN_ENABLE_STREAMLIT_SERVICE=1 sudo -E ./install_bundle_on_origin.sh

8. Locate the live nginx conf for ${DOMAIN}:
   bash ./inspect_public_homepage_origin_conf.sh ${DOMAIN}

9. Optional topology inspect for xray/nginx fallback hosts:
   bash ./inspect_public_homepage_live_topology.sh ${DOMAIN}

10. Optional one-command dry-run:
   bash ./execute_public_homepage_cutover.sh ${DOMAIN}

11. Optional source-IP verify dry-run:
   DOCGEN_VERIFY_RESOLVE_IP=<origin-ip> bash ./execute_public_homepage_cutover.sh ${DOMAIN}

12. Optional one-command apply:
   DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${SSL_PROFILE:-letsencrypt} bash ./execute_public_homepage_cutover.sh ${DOMAIN}

13. Optional source-IP verify apply:
   DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${SSL_PROFILE:-letsencrypt} DOCGEN_VERIFY_RESOLVE_IP=<origin-ip> bash ./execute_public_homepage_cutover.sh ${DOMAIN}

14. Verify the public homepage cutover:
   bash ./verify_public_homepage_cutover.sh https://${DOMAIN}

15. Optional direct-origin verify:
   bash ./verify_public_homepage_cutover.sh https://${DOMAIN} <origin-ip>

16. Optional runtime health summary on the origin host:
   DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}

   Recommended stable summary wrapper:
   bash ./report_docgen_runtime_health_stable.sh https://${DOMAIN}

   Advanced stable summary with explicit overrides:
   ZF_EDGE_PROFILE=stable DOCGEN_RUNTIME_SUMMARY_ONLY=1 bash ./report_docgen_runtime_health.sh https://${DOMAIN}

17. Optional edge-only verify:
   bash ./verify_public_edge_health.sh https://${DOMAIN}

   Recommended stable edge wrapper:
   bash ./verify_public_edge_health_stable.sh https://${DOMAIN}

   Advanced stable edge verify with explicit overrides:
   ZF_EDGE_PROFILE=stable bash ./verify_public_edge_health.sh https://${DOMAIN}

18. Optional origin-app-only verify:
   bash ./verify_origin_app_health.sh

19. Public URL:
   https://${DOMAIN}
EOF

if [[ -n "$SSL_CERT_PATH" ]]; then
  cat >> "$BUNDLE_DIR/README.txt" <<EOF

7. Origin TLS:
   cert: ${SSL_CERT_PATH}
   key: ${SSL_KEY_PATH}
EOF
  if [[ -n "$SSL_PROFILE" ]]; then
    cat >> "$BUNDLE_DIR/README.txt" <<EOF
   profile: ${SSL_PROFILE}
EOF
  fi
fi

cat > "$BUNDLE_DIR/install_bundle_on_origin.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
PROXY_STACK="${DOCGEN_PROXY_STACK:-nginx}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
NGINX_DIR="${NGINX_DIR:-/etc/nginx/conf.d}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-docgen-autoplan.service}"
STREAMLIT_SERVICE_NAME="${STREAMLIT_SERVICE_NAME:-docgen-streamlit.service}"
NGINX_CONF_NAME="${NGINX_CONF_NAME:-docgen-streamlit-origin.conf}"
CADDY_SERVICE_NAME="${CADDY_SERVICE_NAME:-caddy}"
CADDY_SNIPPET_DIR="${CADDY_SNIPPET_DIR:-/etc/caddy/conf.d}"
CADDY_SNIPPET_NAME="${CADDY_SNIPPET_NAME:-docgen-streamlit.Caddyfile}"
CADDY_MAIN_CONFIG_PATH="${CADDY_MAIN_CONFIG_PATH:-/etc/caddy/Caddyfile}"
ENABLE_STREAMLIT_SERVICE="${DOCGEN_ENABLE_STREAMLIT_SERVICE:-0}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站安装。" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[ERROR] systemctl not found" >&2
  exit 1
fi

mkdir -p "$SYSTEMD_DIR"
cp "$SELF_DIR/docgen-autoplan.service" "${SYSTEMD_DIR}/${BACKEND_SERVICE_NAME}"
if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
  cp "$SELF_DIR/docgen-streamlit.service" "${SYSTEMD_DIR}/${STREAMLIT_SERVICE_NAME}"
fi

if [[ "$PROXY_STACK" = "nginx" ]]; then
  if ! command -v nginx >/dev/null 2>&1; then
    echo "[ERROR] nginx not found" >&2
    exit 1
  fi
  mkdir -p "$SYSTEMD_DIR" "$NGINX_DIR"
  cp "$SELF_DIR/docgen-streamlit-origin.conf" "${NGINX_DIR}/${NGINX_CONF_NAME}"
  nginx -t
  systemctl daemon-reload
  systemctl enable --now "${BACKEND_SERVICE_NAME}"
  if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
    systemctl enable --now "${STREAMLIT_SERVICE_NAME}"
  else
    systemctl disable --now "${STREAMLIT_SERVICE_NAME}" >/dev/null 2>&1 || true
  fi
  systemctl reload nginx
  echo "[OK] bundle installed from ${SELF_DIR}"
  echo "     proxy stack: nginx"
  echo "     backend service: ${BACKEND_SERVICE_NAME}"
  if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
    echo "     streamlit service: ${STREAMLIT_SERVICE_NAME}"
  else
    echo "     streamlit service: disabled (backend-managed)"
  fi
  echo "     nginx conf: ${NGINX_DIR}/${NGINX_CONF_NAME}"
else
  if ! command -v caddy >/dev/null 2>&1; then
    echo "[ERROR] caddy not found" >&2
    exit 1
  fi
  mkdir -p "$SYSTEMD_DIR" "$CADDY_SNIPPET_DIR"
  cp "$SELF_DIR/Caddyfile.docgen-streamlit" "${CADDY_SNIPPET_DIR}/${CADDY_SNIPPET_NAME}"
  if [[ ! -f "$CADDY_MAIN_CONFIG_PATH" ]]; then
    echo "[ERROR] caddy main config not found: ${CADDY_MAIN_CONFIG_PATH}" >&2
    exit 1
  fi
  if ! grep -Eq "^[[:space:]]*import[[:space:]].*(conf\\.d|${CADDY_SNIPPET_NAME})" "$CADDY_MAIN_CONFIG_PATH"; then
    echo "[ERROR] ${CADDY_MAIN_CONFIG_PATH} 未发现对 conf.d 或 ${CADDY_SNIPPET_NAME} 的 import，当前不会自动生效。" >&2
    exit 1
  fi
  caddy validate --config "$CADDY_MAIN_CONFIG_PATH"
  systemctl daemon-reload
  systemctl enable --now "${BACKEND_SERVICE_NAME}"
  if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
    systemctl enable --now "${STREAMLIT_SERVICE_NAME}"
  else
    systemctl disable --now "${STREAMLIT_SERVICE_NAME}" >/dev/null 2>&1 || true
  fi
  systemctl reload "${CADDY_SERVICE_NAME}"
  echo "[OK] bundle installed from ${SELF_DIR}"
  echo "     proxy stack: caddy"
  echo "     backend service: ${BACKEND_SERVICE_NAME}"
  if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
    echo "     streamlit service: ${STREAMLIT_SERVICE_NAME}"
  else
    echo "     streamlit service: disabled (backend-managed)"
  fi
  echo "     caddy snippet: ${CADDY_SNIPPET_DIR}/${CADDY_SNIPPET_NAME}"
  echo "     caddy main config: ${CADDY_MAIN_CONFIG_PATH}"
fi

echo "     verify: DOCGEN_PROXY_STACK=${PROXY_STACK} bash ${SELF_DIR}/verify_linux_domain_origin.sh"
EOF

chmod +x "$BUNDLE_DIR/install_bundle_on_origin.sh"
cp "$ROOT/scripts/detect_linux_proxy_stack.sh" \
  "$BUNDLE_DIR/detect_linux_proxy_stack.sh"
chmod +x "$BUNDLE_DIR/detect_linux_proxy_stack.sh"
cp "$ROOT/scripts/suggest_linux_origin_fix.sh" \
  "$BUNDLE_DIR/suggest_linux_origin_fix.sh"
chmod +x "$BUNDLE_DIR/suggest_linux_origin_fix.sh"
cp "$ROOT/scripts/generate_origin_tls_csr.sh" \
  "$BUNDLE_DIR/generate_origin_tls_csr.sh"
chmod +x "$BUNDLE_DIR/generate_origin_tls_csr.sh"
cp "$ROOT/scripts/cutover_public_homepage_origin.sh" \
  "$BUNDLE_DIR/cutover_public_homepage_origin.sh"
chmod +x "$BUNDLE_DIR/cutover_public_homepage_origin.sh"
cp "$ROOT/scripts/cutover_public_homepage_upstream_targets.sh" \
  "$BUNDLE_DIR/cutover_public_homepage_upstream_targets.sh"
chmod +x "$BUNDLE_DIR/cutover_public_homepage_upstream_targets.sh"
cp "$ROOT/scripts/inspect_public_homepage_origin_conf.sh" \
  "$BUNDLE_DIR/inspect_public_homepage_origin_conf.sh"
chmod +x "$BUNDLE_DIR/inspect_public_homepage_origin_conf.sh"
cp "$ROOT/scripts/inspect_public_homepage_live_topology.sh" \
  "$BUNDLE_DIR/inspect_public_homepage_live_topology.sh"
chmod +x "$BUNDLE_DIR/inspect_public_homepage_live_topology.sh"
cp "$ROOT/scripts/execute_public_homepage_cutover.sh" \
  "$BUNDLE_DIR/execute_public_homepage_cutover.sh"
chmod +x "$BUNDLE_DIR/execute_public_homepage_cutover.sh"
cp "$ROOT/scripts/verify_public_homepage_cutover.sh" \
  "$BUNDLE_DIR/verify_public_homepage_cutover.sh"
chmod +x "$BUNDLE_DIR/verify_public_homepage_cutover.sh"
cp "$ROOT/scripts/verify_public_edge_health.sh" \
  "$BUNDLE_DIR/verify_public_edge_health.sh"
chmod +x "$BUNDLE_DIR/verify_public_edge_health.sh"
cp "$ROOT/scripts/verify_public_edge_health_stable.sh" \
  "$BUNDLE_DIR/verify_public_edge_health_stable.sh"
chmod +x "$BUNDLE_DIR/verify_public_edge_health_stable.sh"
cp "$ROOT/scripts/verify_origin_app_health.sh" \
  "$BUNDLE_DIR/verify_origin_app_health.sh"
chmod +x "$BUNDLE_DIR/verify_origin_app_health.sh"
cp "$ROOT/scripts/report_docgen_runtime_health.sh" \
  "$BUNDLE_DIR/report_docgen_runtime_health.sh"
chmod +x "$BUNDLE_DIR/report_docgen_runtime_health.sh"
cp "$ROOT/scripts/report_docgen_runtime_health_stable.sh" \
  "$BUNDLE_DIR/report_docgen_runtime_health_stable.sh"
chmod +x "$BUNDLE_DIR/report_docgen_runtime_health_stable.sh"
cp "$ROOT/scripts/verify_linux_domain_origin.sh" \
  "$BUNDLE_DIR/verify_linux_domain_origin.sh"
chmod +x "$BUNDLE_DIR/verify_linux_domain_origin.sh"
cp "$ROOT/scripts/verify_ocr_runtime.sh" \
  "$BUNDLE_DIR/verify_ocr_runtime.sh"
chmod +x "$BUNDLE_DIR/verify_ocr_runtime.sh"
cp "$ROOT/docs/public_homepage_cutover.md" \
  "$BUNDLE_DIR/public_homepage_cutover.md"

echo "[OK] bundle created: ${BUNDLE_DIR}"
