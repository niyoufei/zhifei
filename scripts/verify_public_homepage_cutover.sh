#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://doc.niyoufei.com}"
RESOLVE_IP="${2:-}"
USER_AGENT="${ZF_VERIFY_USER_AGENT:-Mozilla/5.0}"
CONNECT_TIMEOUT="${ZF_VERIFY_CONNECT_TIMEOUT_SECONDS:-5}"
MAX_TIME="${ZF_VERIFY_MAX_TIME_SECONDS:-15}"
ATTEMPTS="${ZF_VERIFY_ATTEMPTS:-3}"
RETRY_SLEEP_SECONDS="${ZF_VERIFY_RETRY_SLEEP_SECONDS:-1}"

if [[ "$BASE_URL" != http://* && "$BASE_URL" != https://* ]]; then
  echo "[ERROR] BASE_URL 必须包含协议，例如: https://doc.niyoufei.com" >&2
  exit 2
fi

host_from_url() {
  local url="$1"
  local host="${url#*://}"
  host="${host%%/*}"
  host="${host%%:*}"
  printf '%s' "$host"
}

HOST_NAME="$(host_from_url "$BASE_URL")"

curl_common=(
  --silent
  --show-error
  --location
  --user-agent "$USER_AGENT"
  --connect-timeout "$CONNECT_TIMEOUT"
  --max-time "$MAX_TIME"
)

if [ -n "$RESOLVE_IP" ] && [[ "$BASE_URL" == https://* ]]; then
  curl_common+=(--resolve "${HOST_NAME}:443:${RESOLVE_IP}")
fi

curl_http_code() {
  local code="000"
  local attempt
  for attempt in $(seq 1 "$ATTEMPTS"); do
    code="$(curl "${curl_common[@]}" -o /dev/null -w '%{http_code}' "$@" || true)"
    if [ -n "$code" ] && [ "$code" != "000" ]; then
      printf '%s' "$code"
      return 0
    fi
    if [ "$attempt" -lt "$ATTEMPTS" ]; then
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
    body="$(curl "${curl_common[@]}" "$@" 2>/dev/null || true)"
    if [ -n "$body" ]; then
      printf '%s' "$body"
      return 0
    fi
    if [ "$attempt" -lt "$ATTEMPTS" ]; then
      sleep "$RETRY_SLEEP_SECONDS"
    fi
  done
  printf '%s' "$body"
  return 1
}

home_status="$(curl_http_code -I "$BASE_URL" || true)"
if [ -z "$home_status" ] || [ "$home_status" = "000" ]; then
  home_status="$(curl_http_code "$BASE_URL" || true)"
fi

stcore_body="$(curl_body "${BASE_URL%/}/_stcore/health" || true)"

home_body="$(curl_body "$BASE_URL" || true)"

open_webui_present="no"
if printf '%s' "$home_body" | grep -q 'Open WebUI'; then
  open_webui_present="yes"
fi

title="$(
  printf '%s' "$home_body" | python3 -c 'import re, sys; html = sys.stdin.read(); m = re.search(r"<title>(.*?)</title>", html, re.I | re.S); print(m.group(1).strip() if m else "")'
)"

cutover_verified="no"
if [ "$home_status" = "200" ] && [ "$stcore_body" = "ok" ] && [ "$open_webui_present" = "no" ]; then
  cutover_verified="yes"
fi

echo "base_url=$BASE_URL"
echo "resolve_ip=$RESOLVE_IP"
echo "home_status=$home_status"
echo "stcore_body=$stcore_body"
echo "open_webui_present=$open_webui_present"
echo "title=$title"
echo "cutover_verified=$cutover_verified"

if [ "$cutover_verified" != "yes" ]; then
  exit 1
fi
