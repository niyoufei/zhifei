#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
PROXY_STACK="${DOCGEN_PROXY_STACK:-nginx}"
BACKEND_SERVICE_NAME="${BACKEND_SERVICE_NAME:-docgen-autoplan.service}"
STREAMLIT_SERVICE_NAME="${STREAMLIT_SERVICE_NAME:-docgen-streamlit.service}"
EXPECT_STREAMLIT_SERVICE="${DOCGEN_EXPECT_STREAMLIT_SERVICE:-0}"
EXPECT_OCR="${DOCGEN_EXPECT_OCR:-0}"
EXPECT_OCR_CHINESE="${DOCGEN_EXPECT_OCR_CHINESE:-0}"
SKIP_PROXY_HOST_CHECK="${DOCGEN_SKIP_PROXY_HOST_CHECK:-0}"
NGINX_CONF_PATH="${NGINX_CONF_PATH:-/etc/nginx/conf.d/docgen-streamlit-origin.conf}"
CADDY_SERVICE_NAME="${CADDY_SERVICE_NAME:-caddy}"
CADDY_CONFIG_PATH="${CADDY_CONFIG_PATH:-/etc/caddy/Caddyfile}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8010/health}"
STREAMLIT_HEALTH_URL="${STREAMLIT_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
CHECK_TLS="${DOCGEN_EXPECT_TLS:-auto}"
APP_DIR="${DOCGEN_APP_DIR:-/opt/docgen}"
VENV_PYTHON="${DOCGEN_VENV_PYTHON:-${APP_DIR%/}/.venv/bin/python}"

failures=0

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站自检。" >&2
  exit 1
fi

if [[ -z "$DOMAIN" && "$PROXY_STACK" = "nginx" && -f "$NGINX_CONF_PATH" ]]; then
  DOMAIN="$(awk '/server_name/ {print $2}' "$NGINX_CONF_PATH" | tr -d ';' | head -n1)"
fi

if [[ -z "$DOMAIN" && "$PROXY_STACK" = "caddy" && -f "$CADDY_CONFIG_PATH" ]]; then
  DOMAIN="$(awk 'NF && $1 !~ /^[#{}]/ {print $1; exit}' "$CADDY_CONFIG_PATH")"
fi

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] 用法: $0 <完整域名>" >&2
  echo "        或提供 DOCGEN_DOMAIN，或保证 ${NGINX_CONF_PATH} 可读。" >&2
  exit 1
fi

if [[ "$CHECK_TLS" = "auto" ]]; then
  if [[ "$PROXY_STACK" = "nginx" ]]; then
    if [[ -f "$NGINX_CONF_PATH" ]] && grep -q 'listen 443 ssl' "$NGINX_CONF_PATH"; then
      CHECK_TLS="1"
    else
      CHECK_TLS="0"
    fi
  else
    CHECK_TLS="1"
  fi
fi

print_status() {
  local label="$1"
  local ok="$2"
  local detail="$3"
  if [[ "$ok" = "1" ]]; then
    echo "[OK] ${label}: ${detail}"
  else
    echo "[FAIL] ${label}: ${detail}"
    failures=$((failures + 1))
  fi
}

extract_nginx_ssl_cert_path() {
  if [[ -f "$NGINX_CONF_PATH" ]]; then
    awk '/ssl_certificate[[:space:]]+/ {print $2}' "$NGINX_CONF_PATH" | tr -d ';' | head -n1
  fi
}

http_code() {
  local url="$1"
  shift || true
  {
    curl -k -sS -o /dev/null -D - --max-time 10 "$@" "$url" 2>/dev/null || true
  } | awk 'index(toupper($1), "HTTP/") == 1 {code=$2} END{print code}'
}

service_state() {
  local service="$1"
  systemctl is-active "$service" 2>/dev/null || true
}

python_ocr_probe() {
  if [[ ! -x "$VENV_PYTHON" || ! -d "$APP_DIR" ]]; then
    return 0
  fi
  (
    cd "$APP_DIR"
    "$VENV_PYTHON" - <<'PY'
from backend.zhifei_autoplan.ocr_runtime import guess_ocr_lang, is_tesseract_available

print("available=" + str(is_tesseract_available()))
print("lang=" + guess_ocr_lang(prefer_chinese=True))
PY
  ) 2>/dev/null || true
}

echo "[INFO] domain=${DOMAIN}"
echo "[INFO] proxy_stack=${PROXY_STACK}"
echo "[INFO] backend_health=${BACKEND_HEALTH_URL}"
echo "[INFO] streamlit_health=${STREAMLIT_HEALTH_URL}"
echo "[INFO] expect_streamlit_service=${EXPECT_STREAMLIT_SERVICE}"
echo "[INFO] expect_ocr=${EXPECT_OCR}"
echo "[INFO] expect_ocr_chinese=${EXPECT_OCR_CHINESE}"
echo "[INFO] skip_proxy_host_check=${SKIP_PROXY_HOST_CHECK}"
echo "[INFO] app_dir=${APP_DIR}"
if [[ "$PROXY_STACK" = "nginx" ]]; then
  echo "[INFO] nginx_conf=${NGINX_CONF_PATH}"
else
  echo "[INFO] caddy_conf=${CADDY_CONFIG_PATH}"
fi
echo "[INFO] expect_tls=${CHECK_TLS}"

backend_state="$(service_state "$BACKEND_SERVICE_NAME")"
streamlit_state="$(service_state "$STREAMLIT_SERVICE_NAME")"

print_status "$BACKEND_SERVICE_NAME" "$([[ "$backend_state" = "active" ]] && echo 1 || echo 0)" "${backend_state:-unknown}"
if [[ "$EXPECT_STREAMLIT_SERVICE" = "1" ]]; then
  print_status "$STREAMLIT_SERVICE_NAME" "$([[ "$streamlit_state" = "active" ]] && echo 1 || echo 0)" "${streamlit_state:-unknown}"
else
  if [[ "$streamlit_state" = "active" ]]; then
    print_status "${STREAMLIT_SERVICE_NAME} (optional)" "1" "${streamlit_state}"
  else
    echo "[INFO] ${STREAMLIT_SERVICE_NAME}: optional (${streamlit_state:-unknown})"
  fi
fi

if [[ "$PROXY_STACK" = "nginx" ]]; then
  if nginx -t >/tmp/docgen_nginx_verify.out 2>/tmp/docgen_nginx_verify.err; then
    print_status "nginx -t" "1" "config ok"
  else
    detail="$(tail -n 5 /tmp/docgen_nginx_verify.err 2>/dev/null || true)"
    print_status "nginx -t" "0" "${detail:-config invalid}"
  fi
else
  caddy_state="$(service_state "$CADDY_SERVICE_NAME")"
  print_status "$CADDY_SERVICE_NAME" "$([[ "$caddy_state" = "active" ]] && echo 1 || echo 0)" "${caddy_state:-unknown}"
  if caddy validate --config "$CADDY_CONFIG_PATH" >/tmp/docgen_caddy_verify.out 2>/tmp/docgen_caddy_verify.err; then
    print_status "caddy validate" "1" "config ok"
  else
    detail="$(tail -n 5 /tmp/docgen_caddy_verify.err 2>/dev/null || true)"
    print_status "caddy validate" "0" "${detail:-config invalid}"
  fi
fi

if [[ "$PROXY_STACK" = "nginx" && "$CHECK_TLS" = "1" ]]; then
  cert_path="$(extract_nginx_ssl_cert_path)"
  if [[ -n "${cert_path:-}" && -f "$cert_path" ]]; then
    print_status "tls cert file" "1" "$cert_path"
    if openssl x509 -in "$cert_path" -noout -checkhost "$DOMAIN" >/dev/null 2>&1; then
      print_status "tls cert coverage" "1" "${DOMAIN}"
    else
      print_status "tls cert coverage" "0" "${DOMAIN} not covered by ${cert_path}"
    fi
  else
    print_status "tls cert file" "0" "${cert_path:-not configured}"
  fi
fi

backend_code="$(http_code "$BACKEND_HEALTH_URL")"
if [[ "$backend_code" = "200" ]]; then
  print_status "backend health" "1" "HTTP 200"
else
  print_status "backend health" "0" "HTTP ${backend_code:-none}"
fi

streamlit_code="$(http_code "$STREAMLIT_HEALTH_URL")"
if [[ "$streamlit_code" = "200" ]]; then
  print_status "streamlit health" "1" "HTTP 200"
else
  print_status "streamlit health" "0" "HTTP ${streamlit_code:-none}"
fi

tesseract_path="$(command -v tesseract || true)"
ocr_probe="$(python_ocr_probe)"
ocr_available="$(printf '%s\n' "$ocr_probe" | awk -F= '/^available=/{print $2}' | tail -n1)"
ocr_lang="$(printf '%s\n' "$ocr_probe" | awk -F= '/^lang=/{print $2}' | tail -n1)"
ocr_langs="$(tesseract --list-langs 2>/dev/null || true)"

if [[ "$EXPECT_OCR" = "1" ]]; then
  if [[ -n "$tesseract_path" ]]; then
    print_status "ocr binary" "1" "$tesseract_path"
  else
    print_status "ocr binary" "0" "tesseract not found"
  fi

  if [[ "$ocr_available" = "True" ]]; then
    print_status "ocr runtime" "1" "available=True lang=${ocr_lang:-unknown}"
  else
    print_status "ocr runtime" "0" "${ocr_probe:-python probe unavailable}"
  fi

  if [[ "$EXPECT_OCR_CHINESE" = "1" ]]; then
    if grep -Eq '(^|[[:space:]])chi_(sim|tra)($|[[:space:]])' <<<"$ocr_langs"; then
      print_status "ocr chinese langpack" "1" "$(tr '\n' ' ' <<<"$ocr_langs" | sed 's/[[:space:]]\+/ /g')"
    else
      print_status "ocr chinese langpack" "0" "$(tr '\n' ' ' <<<"$ocr_langs" | sed 's/[[:space:]]\+/ /g')"
    fi
  fi
else
  if [[ -n "$tesseract_path" ]]; then
    echo "[INFO] ocr binary: optional (${tesseract_path})"
  else
    echo "[INFO] ocr binary: optional (not installed)"
  fi
  if [[ -n "$ocr_probe" ]]; then
    echo "[INFO] ocr runtime: optional (${ocr_probe//$'\n'/; })"
  fi
fi

if [[ "$SKIP_PROXY_HOST_CHECK" = "1" ]]; then
  echo "[INFO] proxy host header checks: skipped"
else
  origin_http_code="$(http_code "http://${DOMAIN}" --resolve "${DOMAIN}:80:127.0.0.1")"
  case "$origin_http_code" in
    200|301|302|307|308)
      print_status "proxy host header :80" "1" "HTTP ${origin_http_code}"
      ;;
    *)
      print_status "proxy host header :80" "0" "HTTP ${origin_http_code:-none}"
      ;;
  esac

  if [[ "$CHECK_TLS" = "1" ]]; then
    origin_https_code="$(http_code "https://${DOMAIN}" --resolve "${DOMAIN}:443:127.0.0.1")"
    case "$origin_https_code" in
      200|301|302|307|308)
        print_status "proxy host header :443" "1" "HTTP ${origin_https_code}"
        ;;
      *)
        print_status "proxy host header :443" "0" "HTTP ${origin_https_code:-none}"
        ;;
    esac
  else
    echo "[INFO] proxy host header :443: skipped (TLS not expected)"
  fi
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[SUMMARY] ${failures} checks failed."
  exit 1
fi

echo "[SUMMARY] all checks passed."
