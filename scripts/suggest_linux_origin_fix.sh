#!/usr/bin/env bash
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
PROXY_STACK="${DOCGEN_PROXY_STACK:-}"
NGINX_CONF_PATH="${NGINX_CONF_PATH:-/etc/nginx/conf.d/docgen-streamlit-origin.conf}"
CADDY_CONFIG_PATH="${CADDY_CONFIG_PATH:-/etc/caddy/Caddyfile}"
LE_CERT="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
LE_KEY="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
DETECT_SCRIPT="${SELF_DIR}/detect_linux_proxy_stack.sh"
CSR_SCRIPT="${SELF_DIR}/generate_origin_tls_csr.sh"
CERTBOT_PATH="$(command -v certbot || true)"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站建议输出。" >&2
  exit 1
fi

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain>" >&2
  echo "        example: $0 doc.niyoufei.com" >&2
  exit 1
fi

detect_output=""
if [[ -f "$DETECT_SCRIPT" ]]; then
  detect_output="$(bash "$DETECT_SCRIPT" "$DOMAIN" 2>&1 || true)"
  if [[ -z "$PROXY_STACK" ]]; then
    PROXY_STACK="$(printf '%s\n' "$detect_output" | awk -F= '/^\[RECOMMEND\] proxy_stack=/{print $2; exit}')"
  fi
fi

le_cert_exists=0
le_cert_covers=0
if [[ -f "$LE_CERT" ]]; then
  le_cert_exists=1
  if openssl x509 -in "$LE_CERT" -noout -checkhost "$DOMAIN" >/dev/null 2>&1; then
    le_cert_covers=1
  fi
fi

caddy_import_conf_d=0
if [[ -f "$CADDY_CONFIG_PATH" ]] && grep -Eq '^[[:space:]]*import[[:space:]].*conf\.d' "$CADDY_CONFIG_PATH"; then
  caddy_import_conf_d=1
fi

echo "[INFO] domain=${DOMAIN}"
if [[ -n "$PROXY_STACK" ]]; then
  echo "[INFO] proxy_stack=${PROXY_STACK}"
else
  echo "[WARN] proxy_stack=undetermined"
fi
echo "[INFO] letsencrypt cert exists=${le_cert_exists}"
echo "[INFO] letsencrypt cert covers domain=${le_cert_covers}"
echo "[INFO] certbot=${CERTBOT_PATH:-missing}"
echo "[INFO] nginx conf path=${NGINX_CONF_PATH}"
echo "[INFO] caddy conf path=${CADDY_CONFIG_PATH}"
echo "[INFO] caddy import conf.d=${caddy_import_conf_d}"

if [[ -z "$PROXY_STACK" ]]; then
  echo "[RECOMMEND] 先根据当前在线入口手工确认反代栈，再安装 bundle。"
  echo "[RECOMMEND] 可优先检查 /etc/nginx、/etc/caddy/Caddyfile 以及 systemctl status nginx caddy。"
  exit 0
fi

case "$PROXY_STACK" in
  nginx)
    echo "[RECOMMEND] 使用 nginx 发布链。"
    if [[ "$le_cert_exists" = "1" && "$le_cert_covers" = "1" ]]; then
      echo "1. export DOCGEN_PROXY_STACK=nginx"
      echo "2. export DOCGEN_SSL_PROFILE=letsencrypt"
      echo "3. sudo -E ./install_bundle_on_origin.sh"
      echo "4. DOCGEN_PROXY_STACK=nginx bash ./verify_linux_domain_origin.sh ${DOMAIN}"
    else
      echo "[BLOCKED] 当前未发现覆盖 ${DOMAIN} 的 Let's Encrypt 证书。"
      if [[ -n "$CERTBOT_PATH" ]]; then
        echo "1. sudo certbot certonly --nginx -d ${DOMAIN}"
        echo "2. export DOCGEN_PROXY_STACK=nginx"
        echo "3. export DOCGEN_SSL_PROFILE=letsencrypt"
        echo "4. sudo -E ./install_bundle_on_origin.sh"
        echo "5. DOCGEN_PROXY_STACK=nginx bash ./verify_linux_domain_origin.sh ${DOMAIN}"
      elif [[ -f "$CSR_SCRIPT" ]]; then
        echo "1. bash ./generate_origin_tls_csr.sh ${DOMAIN}"
        echo "2. 用生成的 CSR 向 Let's Encrypt / Cloudflare Origin CA / 现有 CA 申请证书"
        echo "3. 设置 DOCGEN_SSL_CERT 与 DOCGEN_SSL_KEY，或签发到 /etc/letsencrypt/live/${DOMAIN}/"
        echo "4. export DOCGEN_PROXY_STACK=nginx"
        echo "5. sudo -E ./install_bundle_on_origin.sh"
        echo "6. DOCGEN_PROXY_STACK=nginx bash ./verify_linux_domain_origin.sh ${DOMAIN}"
      else
        echo "1. 先为 ${DOMAIN} 申请覆盖该子域名的证书"
        echo "2. export DOCGEN_PROXY_STACK=nginx"
        echo "3. 然后再执行 nginx 发布链"
      fi
    fi
    ;;
  caddy)
    echo "[RECOMMEND] 使用 caddy 发布链。"
    if [[ "$caddy_import_conf_d" != "1" ]]; then
      echo "[BLOCKED] 当前 /etc/caddy/Caddyfile 未见 conf.d 导入，bundle 片段不会自动生效。"
      echo "1. 先在 /etc/caddy/Caddyfile 中添加 conf.d 导入"
      echo "2. 重新运行本脚本确认"
      echo "3. 再执行 caddy 发布链"
    else
      echo "1. export DOCGEN_PROXY_STACK=caddy"
      echo "2. sudo -E ./install_bundle_on_origin.sh"
      echo "3. DOCGEN_PROXY_STACK=caddy bash ./verify_linux_domain_origin.sh ${DOMAIN}"
      echo "4. 若 caddy 未自动拿到 ${DOMAIN} 的证书，再回退到 CSR/证书申请流程"
    fi
    ;;
  *)
    echo "[WARN] 未识别的 proxy stack: ${PROXY_STACK}"
    ;;
esac
