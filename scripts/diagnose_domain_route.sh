#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-}"
ORIGIN_IP="${2:-}"

unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY all_proxy ALL_PROXY

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain> [origin-ip]" >&2
  echo "        example: $0 doc.niyoufei.com 199.180.118.204" >&2
  exit 1
fi

is_fake_ip() {
  local ip="$1"
  [[ "$ip" =~ ^198\.18\. ]] || [[ "$ip" =~ ^198\.19\. ]]
}

curl_status() {
  local url="$1"
  shift || true
  {
    curl -k -sS -o /dev/null -D - --max-time 10 "$@" "$url" 2>/dev/null || true
  } \
    | awk 'index(toupper($1), "HTTP/") == 1 {code=$2} END{print code}'
}

curl_head() {
  local url="$1"
  shift || true
  curl -k -sS -I --max-time 10 "$@" "$url" || true
}

print_assessment() {
  local label="$1"
  local code="$2"
  case "$code" in
    200|301|302|307|308)
      echo "[OK] ${label}: HTTP ${code}"
      ;;
    521)
      echo "[WARN] ${label}: HTTP 521，Cloudflare 无法连到源站。"
      ;;
    525)
      echo "[WARN] ${label}: HTTP 525，Cloudflare 到源站的 TLS 握手失败。"
      ;;
    "")
      echo "[WARN] ${label}: 未拿到 HTTP 状态，可能是空响应、握手失败或超时。"
      ;;
    *)
      echo "[WARN] ${label}: HTTP ${code}"
      ;;
  esac
}

echo "[INFO] domain=${DOMAIN}"
if command -v dig >/dev/null 2>&1; then
  DNS_LINES="$(dig +short "$DOMAIN" | tr -d '\r' || true)"
  echo "[INFO] dns:"
  if [[ -n "$DNS_LINES" ]]; then
    printf '%s\n' "$DNS_LINES" | sed 's/^/  - /'
    while IFS= read -r line; do
      if is_fake_ip "$line"; then
        echo "[WARN] dns: ${line} 落在 198.18.0.0/15，疑似本机代理 fake-IP，不能当作真实公网解析结果。"
      fi
    done <<< "$DNS_LINES"
  else
    echo "  - [EMPTY]"
  fi
fi

echo
echo "[EDGE] http://${DOMAIN}"
EDGE_HTTP_CODE="$(curl_status "http://${DOMAIN}")"
print_assessment "edge-http" "$EDGE_HTTP_CODE"
curl_head "http://${DOMAIN}"

echo
echo "[EDGE] https://${DOMAIN}"
EDGE_HTTPS_CODE="$(curl_status "https://${DOMAIN}")"
print_assessment "edge-https" "$EDGE_HTTPS_CODE"
curl_head "https://${DOMAIN}"

if [[ -n "$ORIGIN_IP" ]]; then
  echo
  echo "[ORIGIN] http://${DOMAIN} via ${ORIGIN_IP}:80"
  ORIGIN_HTTP_CODE="$(curl_status "http://${DOMAIN}" --resolve "${DOMAIN}:80:${ORIGIN_IP}")"
  print_assessment "origin-http" "$ORIGIN_HTTP_CODE"
  curl_head "http://${DOMAIN}" --resolve "${DOMAIN}:80:${ORIGIN_IP}"

  echo
  echo "[ORIGIN] https://${DOMAIN} via ${ORIGIN_IP}:443"
  ORIGIN_HTTPS_CODE="$(curl_status "https://${DOMAIN}" --resolve "${DOMAIN}:443:${ORIGIN_IP}")"
  print_assessment "origin-https" "$ORIGIN_HTTPS_CODE"
  curl_head "https://${DOMAIN}" --resolve "${DOMAIN}:443:${ORIGIN_IP}"
fi
