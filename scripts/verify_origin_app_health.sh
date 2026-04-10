#!/usr/bin/env bash
set -euo pipefail

BACKEND_SERVICE_NAME="${DOCGEN_ORIGIN_BACKEND_SERVICE_NAME:-docgen-autoplan.service}"
BACKEND_HEALTH_URL="${1:-${DOCGEN_ORIGIN_BACKEND_HEALTH_URL:-http://127.0.0.1:8010/health}}"
STREAMLIT_HEALTH_URL="${2:-${DOCGEN_ORIGIN_STREAMLIT_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}}"
CONNECT_TIMEOUT="${DOCGEN_ORIGIN_CONNECT_TIMEOUT_SECONDS:-5}"
MAX_TIME="${DOCGEN_ORIGIN_MAX_TIME_SECONDS:-15}"
ATTEMPTS="${DOCGEN_ORIGIN_VERIFY_ATTEMPTS:-3}"
RETRY_SLEEP_SECONDS="${DOCGEN_ORIGIN_RETRY_SLEEP_SECONDS:-1}"

curl_common=(
  --silent
  --show-error
  --location
  --connect-timeout "$CONNECT_TIMEOUT"
  --max-time "$MAX_TIME"
)

curl_http_code() {
  local code="000"
  local attempt
  for attempt in $(seq 1 "$ATTEMPTS"); do
    code="$(curl "${curl_common[@]}" -o /dev/null -w '%{http_code}' "$1" || true)"
    if [[ -n "$code" && "$code" != "000" ]]; then
      printf '%s' "$code"
      return 0
    fi
    if [[ "$attempt" -lt "$ATTEMPTS" ]]; then
      sleep "$RETRY_SLEEP_SECONDS"
    fi
  done
  printf '%s' "${code:-000}"
  return 1
}

curl_body() {
  local body=""
  local attempt
  for attempt in $(seq 1 "$ATTEMPTS"); do
    body="$(curl "${curl_common[@]}" "$1" 2>/dev/null || true)"
    if [[ -n "$body" ]]; then
      printf '%s' "$body"
      return 0
    fi
    if [[ "$attempt" -lt "$ATTEMPTS" ]]; then
      sleep "$RETRY_SLEEP_SECONDS"
    fi
  done
  printf '%s' "$body"
  return 1
}

service_state() {
  if ! command -v systemctl >/dev/null 2>&1; then
    printf 'unknown'
    return 0
  fi
  systemctl is-active "$BACKEND_SERVICE_NAME" 2>/dev/null || true
}

backend_service_state="$(service_state)"
backend_http_status="$(curl_http_code "$BACKEND_HEALTH_URL" || true)"
streamlit_http_status="$(curl_http_code "$STREAMLIT_HEALTH_URL" || true)"
streamlit_body="$(curl_body "$STREAMLIT_HEALTH_URL" || true)"

origin_backend_ok="no"
origin_streamlit_ok="no"
origin_app_state="degraded"

if [[ "$backend_http_status" = "200" ]]; then
  origin_backend_ok="yes"
fi
if [[ "$streamlit_http_status" = "200" && "$streamlit_body" = "ok" ]]; then
  origin_streamlit_ok="yes"
fi
if [[ "$origin_backend_ok" = "yes" && "$origin_streamlit_ok" = "yes" ]]; then
  origin_app_state="healthy"
fi

echo "backend_service_name=$BACKEND_SERVICE_NAME"
echo "backend_service_state=$backend_service_state"
echo "backend_health_url=$BACKEND_HEALTH_URL"
echo "backend_http_status=$backend_http_status"
echo "streamlit_health_url=$STREAMLIT_HEALTH_URL"
echo "streamlit_http_status=$streamlit_http_status"
echo "streamlit_body=$streamlit_body"
echo "origin_backend_ok=$origin_backend_ok"
echo "origin_streamlit_ok=$origin_streamlit_ok"
echo "origin_app_state=$origin_app_state"

if [[ "$origin_app_state" != "healthy" ]]; then
  exit 1
fi
