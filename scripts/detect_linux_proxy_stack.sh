#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
NGINX_SERVICE_NAME="${NGINX_SERVICE_NAME:-nginx}"
CADDY_SERVICE_NAME="${CADDY_SERVICE_NAME:-caddy}"
NGINX_CONF_PATH="${NGINX_CONF_PATH:-/etc/nginx/conf.d/docgen-streamlit-origin.conf}"
CADDY_CONFIG_PATH="${CADDY_CONFIG_PATH:-/etc/caddy/Caddyfile}"
CADDY_SNIPPET_DIR="${CADDY_SNIPPET_DIR:-/etc/caddy/conf.d}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站探测。" >&2
  exit 1
fi

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

service_state() {
  systemctl is-active "$1" 2>/dev/null || true
}

http_code() {
  local url="$1"
  {
    curl -k -sS -o /dev/null -D - --max-time 5 "$url" 2>/dev/null || true
  } | awk 'index(toupper($1), "HTTP/") == 1 {code=$2} END{print code}'
}

server_header() {
  local url="$1"
  curl -k -sS -I --max-time 5 "$url" 2>/dev/null \
    | awk 'tolower($1)=="server:" {print $2; exit}' \
    | tr -d '\r'
}

recommend=""
reason=""

nginx_cmd=0
caddy_cmd=0
nginx_state="$(service_state "$NGINX_SERVICE_NAME")"
caddy_state="$(service_state "$CADDY_SERVICE_NAME")"

have_cmd nginx && nginx_cmd=1
have_cmd caddy && caddy_cmd=1

loopback_http_code="$(http_code "http://127.0.0.1")"
loopback_https_code="$(http_code "https://127.0.0.1")"
loopback_http_server="$(server_header "http://127.0.0.1")"
loopback_https_server="$(server_header "https://127.0.0.1")"

caddy_import_conf_d=0
if [[ -f "$CADDY_CONFIG_PATH" ]] && grep -Eq '^[[:space:]]*import[[:space:]].*conf\.d' "$CADDY_CONFIG_PATH"; then
  caddy_import_conf_d=1
fi

if [[ "$nginx_state" = "active" && "$caddy_state" != "active" ]]; then
  recommend="nginx"
  reason="nginx service active while caddy is not active"
elif [[ "$caddy_state" = "active" && "$nginx_state" != "active" ]]; then
  recommend="caddy"
  reason="caddy service active while nginx is not active"
elif [[ -n "$loopback_http_server" && "$loopback_http_server" == nginx* ]]; then
  recommend="nginx"
  reason="loopback :80 server header reports nginx"
elif [[ -n "$loopback_https_server" && "$loopback_https_server" == nginx* ]]; then
  recommend="nginx"
  reason="loopback :443 server header reports nginx"
elif [[ "$caddy_import_conf_d" = "1" && "$caddy_cmd" = "1" ]]; then
  recommend="caddy"
  reason="caddy main config imports conf.d and caddy command exists"
elif [[ -f "$NGINX_CONF_PATH" && "$nginx_cmd" = "1" ]]; then
  recommend="nginx"
  reason="nginx config path exists and nginx command is available"
fi

echo "[INFO] domain=${DOMAIN:-[not-provided]}"
echo "[INFO] nginx command=$nginx_cmd"
echo "[INFO] nginx service=${nginx_state:-unknown}"
echo "[INFO] nginx conf=${NGINX_CONF_PATH} $( [[ -f "$NGINX_CONF_PATH" ]] && echo present || echo missing )"
echo "[INFO] caddy command=$caddy_cmd"
echo "[INFO] caddy service=${caddy_state:-unknown}"
echo "[INFO] caddy conf=${CADDY_CONFIG_PATH} $( [[ -f "$CADDY_CONFIG_PATH" ]] && echo present || echo missing )"
echo "[INFO] caddy import conf.d=${caddy_import_conf_d}"
echo "[INFO] loopback :80 code=${loopback_http_code:-none} server=${loopback_http_server:-none}"
echo "[INFO] loopback :443 code=${loopback_https_code:-none} server=${loopback_https_server:-none}"

if [[ -n "$DOMAIN" ]]; then
  le_cert="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
  if [[ -f "$le_cert" ]]; then
    if openssl x509 -in "$le_cert" -noout -checkhost "$DOMAIN" >/dev/null 2>&1; then
      echo "[INFO] letsencrypt cert=${le_cert} covered=1"
    else
      echo "[INFO] letsencrypt cert=${le_cert} covered=0"
    fi
  else
    echo "[INFO] letsencrypt cert=${le_cert} missing"
  fi
fi

if [[ -n "$recommend" ]]; then
  echo "[RECOMMEND] proxy_stack=${recommend}"
  echo "[RECOMMEND] reason=${reason}"
  exit 0
fi

echo "[WARN] proxy_stack=undetermined"
echo "[WARN] reason=当前证据不足，建议手工检查 /etc/nginx 与 /etc/caddy 的真实在线入口。"
exit 2
