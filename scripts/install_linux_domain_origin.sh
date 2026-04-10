#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
PROXY_STACK="${DOCGEN_PROXY_STACK:-nginx}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-docgen-autoplan.service}"
STREAMLIT_SERVICE_NAME="${STREAMLIT_SERVICE_NAME:-docgen-streamlit.service}"
ENABLE_STREAMLIT_SERVICE="${DOCGEN_ENABLE_STREAMLIT_SERVICE:-0}"
NGINX_CONF_NAME="${NGINX_CONF_NAME:-docgen-streamlit-origin.conf}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
NGINX_DIR="${NGINX_DIR:-/etc/nginx/conf.d}"
CADDY_SERVICE_NAME="${CADDY_SERVICE_NAME:-caddy}"
CADDY_SNIPPET_DIR="${CADDY_SNIPPET_DIR:-/etc/caddy/conf.d}"
CADDY_SNIPPET_NAME="${CADDY_SNIPPET_NAME:-docgen-streamlit.Caddyfile}"
CADDY_MAIN_CONFIG_PATH="${CADDY_MAIN_CONFIG_PATH:-/etc/caddy/Caddyfile}"
SSL_CERT_PATH="${DOCGEN_SSL_CERT:-}"
SSL_KEY_PATH="${DOCGEN_SSL_KEY:-}"
SSL_PROFILE="${DOCGEN_SSL_PROFILE:-}"

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] 用法: $0 <完整域名>" >&2
  echo "        例如: $0 doc.niyoufei.com" >&2
  exit 1
fi

if [[ "$SSL_PROFILE" = "letsencrypt" && -z "$SSL_CERT_PATH" && -z "$SSL_KEY_PATH" ]]; then
  SSL_CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  SSL_KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站安装。" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[ERROR] systemctl not found" >&2
  exit 1
fi

mkdir -p "$SYSTEMD_DIR"

cp "$ROOT/deploy/systemd/docgen-autoplan.service" "${SYSTEMD_DIR}/${BACKEND_SERVICE_NAME}"
if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
  sed "s|https://__DOCGEN_DOMAIN__|https://${DOMAIN}|g" \
    "$ROOT/deploy/systemd/docgen-streamlit.service" \
    > "${SYSTEMD_DIR}/${STREAMLIT_SERVICE_NAME}"
fi

if [[ "$PROXY_STACK" = "nginx" ]]; then
  if ! command -v nginx >/dev/null 2>&1; then
    echo "[ERROR] nginx not found" >&2
    exit 1
  fi
  mkdir -p "$NGINX_DIR"
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
      > "${NGINX_DIR}/${NGINX_CONF_NAME}"
  else
    sed "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
      "$ROOT/deploy/nginx/docgen-streamlit-origin.conf.template" \
      > "${NGINX_DIR}/${NGINX_CONF_NAME}"
  fi
  nginx -t
  systemctl daemon-reload
  systemctl enable --now "${BACKEND_SERVICE_NAME}"
  if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
    systemctl enable --now "${STREAMLIT_SERVICE_NAME}"
  else
    systemctl disable --now "${STREAMLIT_SERVICE_NAME}" >/dev/null 2>&1 || true
  fi
  systemctl reload nginx
else
  if ! command -v caddy >/dev/null 2>&1; then
    echo "[ERROR] caddy not found" >&2
    exit 1
  fi
  mkdir -p "$CADDY_SNIPPET_DIR"
  sed "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
    "$ROOT/deploy/caddy/Caddyfile.docgen-streamlit.template" \
    > "${CADDY_SNIPPET_DIR}/${CADDY_SNIPPET_NAME}"
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
fi

echo "[OK] 域名源站配置已安装"
echo "     DOMAIN=${DOMAIN}"
echo "     proxy stack: ${PROXY_STACK}"
echo "     backend service: ${BACKEND_SERVICE_NAME}"
if [[ "$ENABLE_STREAMLIT_SERVICE" = "1" ]]; then
  echo "     streamlit service: ${STREAMLIT_SERVICE_NAME}"
else
  echo "     streamlit service: disabled (backend-managed)"
fi
if [[ "$PROXY_STACK" = "nginx" ]]; then
  echo "     nginx conf: ${NGINX_DIR}/${NGINX_CONF_NAME}"
else
  echo "     caddy snippet: ${CADDY_SNIPPET_DIR}/${CADDY_SNIPPET_NAME}"
  echo "     caddy main config: ${CADDY_MAIN_CONFIG_PATH}"
fi
echo "     public url: https://${DOMAIN}"
if [[ -n "$SSL_CERT_PATH" ]]; then
  echo "     origin tls cert: ${SSL_CERT_PATH}"
  echo "     origin tls key: ${SSL_KEY_PATH}"
  if [[ -n "$SSL_PROFILE" ]]; then
    echo "     origin tls profile: ${SSL_PROFILE}"
  fi
fi
