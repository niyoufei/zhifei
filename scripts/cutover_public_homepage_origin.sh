#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
TARGET_CONF_PATH="${2:-${DOCGEN_TARGET_CONF_PATH:-}}"
APPLY="${DOCGEN_APPLY:-0}"
SSL_CERT_PATH="${DOCGEN_SSL_CERT:-}"
SSL_KEY_PATH="${DOCGEN_SSL_KEY:-}"
SSL_PROFILE="${DOCGEN_SSL_PROFILE:-}"
BACKUP_DIR="${DOCGEN_CUTOVER_BACKUP_DIR:-}"

if [[ -z "$DOMAIN" || -z "$TARGET_CONF_PATH" ]]; then
  echo "[ERROR] usage: $0 <full-domain> <target-nginx-conf-path>" >&2
  echo "        example: $0 doc.niyoufei.com /etc/nginx/conf.d/doc.niyoufei.com.conf" >&2
  exit 1
fi

if [[ "$SSL_PROFILE" = "letsencrypt" && -z "$SSL_CERT_PATH" && -z "$SSL_KEY_PATH" ]]; then
  SSL_CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  SSL_KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
fi

if [[ -n "$SSL_CERT_PATH" || -n "$SSL_KEY_PATH" ]]; then
  if [[ -z "$SSL_CERT_PATH" || -z "$SSL_KEY_PATH" ]]; then
    echo "[ERROR] DOCGEN_SSL_CERT 与 DOCGEN_SSL_KEY 必须同时提供。" >&2
    exit 1
  fi
  TEMPLATE_PATH="$ROOT/deploy/nginx/docgen-streamlit-origin-ssl.conf.template"
else
  TEMPLATE_PATH="$ROOT/deploy/nginx/docgen-streamlit-origin.conf.template"
fi

TMP_RENDER="$(mktemp "${TMPDIR:-/tmp}/docgen-cutover.XXXXXX.conf")"
cleanup() {
  rm -f "$TMP_RENDER"
}
trap cleanup EXIT

if [[ "$TEMPLATE_PATH" = *"-ssl.conf.template" ]]; then
  sed \
    -e "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
    -e "s|__DOCGEN_SSL_CERT__|${SSL_CERT_PATH}|g" \
    -e "s|__DOCGEN_SSL_KEY__|${SSL_KEY_PATH}|g" \
    "$TEMPLATE_PATH" \
    > "$TMP_RENDER"
else
  sed "s|__DOCGEN_DOMAIN__|${DOMAIN}|g" \
    "$TEMPLATE_PATH" \
    > "$TMP_RENDER"
fi

if [[ "$APPLY" != "1" ]]; then
  echo "[INFO] dry-run rendered config"
  echo "domain=${DOMAIN}"
  echo "target_conf_path=${TARGET_CONF_PATH}"
  echo "template_path=${TEMPLATE_PATH}"
  if [[ -n "$SSL_CERT_PATH" ]]; then
    echo "ssl_cert_path=${SSL_CERT_PATH}"
    echo "ssl_key_path=${SSL_KEY_PATH}"
  fi
  echo "--- rendered config begin ---"
  cat "$TMP_RENDER"
  echo "--- rendered config end ---"
  exit 0
fi

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERROR] DOCGEN_APPLY=1 仅允许在 Linux 源站执行。" >&2
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "[ERROR] nginx not found" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[ERROR] systemctl not found" >&2
  exit 1
fi

TARGET_DIR="$(dirname "$TARGET_CONF_PATH")"
mkdir -p "$TARGET_DIR"

if [[ -z "$BACKUP_DIR" ]]; then
  BACKUP_DIR="${TARGET_DIR}/.docgen-cutover-backups"
fi
mkdir -p "$BACKUP_DIR"

timestamp="$(date '+%Y%m%d-%H%M%S')"
backup_path=""
if [[ -f "$TARGET_CONF_PATH" ]]; then
  backup_path="${BACKUP_DIR}/$(basename "$TARGET_CONF_PATH").${timestamp}.bak"
  cp "$TARGET_CONF_PATH" "$backup_path"
fi

cp "$TMP_RENDER" "$TARGET_CONF_PATH"

if ! nginx -t; then
  echo "[ERROR] nginx -t failed after writing ${TARGET_CONF_PATH}" >&2
  if [[ -n "$backup_path" && -f "$backup_path" ]]; then
    cp "$backup_path" "$TARGET_CONF_PATH"
  else
    rm -f "$TARGET_CONF_PATH"
  fi
  exit 1
fi

systemctl reload nginx

echo "[OK] public homepage cutover config applied"
echo "domain=${DOMAIN}"
echo "target_conf_path=${TARGET_CONF_PATH}"
echo "proxy_pass=http://127.0.0.1:8501"
if [[ -n "$backup_path" ]]; then
  echo "backup_path=${backup_path}"
else
  echo "backup_path="
fi
