#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${ZF_EDGE_BASE_URL:-https://doc.niyoufei.com}}"
USER_AGENT="${ZF_EDGE_USER_AGENT:-Mozilla/5.0}"
CONNECT_TIMEOUT="${ZF_EDGE_CONNECT_TIMEOUT_SECONDS:-5}"
MAX_TIME="${ZF_EDGE_MAX_TIME_SECONDS:-15}"
ATTEMPTS="${ZF_EDGE_ATTEMPTS:-3}"
RETRY_SLEEP_SECONDS="${ZF_EDGE_RETRY_SLEEP_SECONDS:-1}"
EDGE_PROFILE="${ZF_EDGE_PROFILE:-default}"

case "$EDGE_PROFILE" in
  default)
    OBSERVE_CYCLES="${ZF_EDGE_OBSERVE_CYCLES:-1}"
    OBSERVE_INTERVAL_SECONDS="${ZF_EDGE_OBSERVE_INTERVAL_SECONDS:-2}"
    HOME_FAIL_STREAK_THRESHOLD="${ZF_EDGE_HOME_FAIL_STREAK_THRESHOLD:-1}"
    STREAMLIT_FAIL_STREAK_THRESHOLD="${ZF_EDGE_STREAMLIT_FAIL_STREAK_THRESHOLD:-1}"
    ;;
  stable)
    OBSERVE_CYCLES="${ZF_EDGE_OBSERVE_CYCLES:-3}"
    OBSERVE_INTERVAL_SECONDS="${ZF_EDGE_OBSERVE_INTERVAL_SECONDS:-2}"
    HOME_FAIL_STREAK_THRESHOLD="${ZF_EDGE_HOME_FAIL_STREAK_THRESHOLD:-2}"
    STREAMLIT_FAIL_STREAK_THRESHOLD="${ZF_EDGE_STREAMLIT_FAIL_STREAK_THRESHOLD:-2}"
    ;;
  *)
    echo "[ERROR] ZF_EDGE_PROFILE 仅支持 default 或 stable，实际为: ${EDGE_PROFILE}" >&2
    exit 2
    ;;
esac

if [[ "$BASE_URL" != http://* && "$BASE_URL" != https://* ]]; then
  echo "[ERROR] BASE_URL 必须包含协议，例如: https://doc.niyoufei.com" >&2
  exit 2
fi

curl_common=(
  --silent
  --show-error
  --location
  --user-agent "$USER_AGENT"
  --connect-timeout "$CONNECT_TIMEOUT"
  --max-time "$MAX_TIME"
)

require_positive_int() {
  local name="$1"
  local value="$2"
  if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "[ERROR] ${name} 必须是正整数，实际为: ${value}" >&2
    exit 2
  fi
}

require_non_negative_int() {
  local name="$1"
  local value="$2"
  if ! [[ "$value" =~ ^[0-9]+$ ]]; then
    echo "[ERROR] ${name} 必须是非负整数，实际为: ${value}" >&2
    exit 2
  fi
}

require_positive_int "ZF_EDGE_ATTEMPTS" "$ATTEMPTS"
require_positive_int "ZF_EDGE_OBSERVE_CYCLES" "$OBSERVE_CYCLES"
require_non_negative_int "ZF_EDGE_OBSERVE_INTERVAL_SECONDS" "$OBSERVE_INTERVAL_SECONDS"
require_positive_int "ZF_EDGE_HOME_FAIL_STREAK_THRESHOLD" "$HOME_FAIL_STREAK_THRESHOLD"
require_positive_int "ZF_EDGE_STREAMLIT_FAIL_STREAK_THRESHOLD" "$STREAMLIT_FAIL_STREAK_THRESHOLD"

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

stcore_url="${BASE_URL%/}/_stcore/health"
home_status="000"
stcore_http_status="000"
stcore_body=""
home_body=""
title=""
home_fail_streak=0
streamlit_fail_streak=0
home_fail_streak_max=0
streamlit_fail_streak_max=0
edge_home_drop_at="none"
edge_streamlit_drop_at="none"

for cycle in $(seq 1 "$OBSERVE_CYCLES"); do
  home_status="$(curl_http_code "$BASE_URL" || true)"
  stcore_http_status="$(curl_http_code "$stcore_url" || true)"
  stcore_body="$(curl_body "$stcore_url" || true)"
  home_body="$(curl_body "$BASE_URL" || true)"
  title="$(
    printf '%s' "$home_body" | python3 -c 'import re, sys; html = sys.stdin.read(); m = re.search(r"<title>(.*?)</title>", html, re.I | re.S); print(m.group(1).strip() if m else "")'
  )"

  if [[ "$home_status" = "200" ]]; then
    home_fail_streak=0
  else
    home_fail_streak=$((home_fail_streak + 1))
    if [[ "$home_fail_streak" -gt "$home_fail_streak_max" ]]; then
      home_fail_streak_max="$home_fail_streak"
    fi
    if [[ "$edge_home_drop_at" = "none" && "$home_fail_streak" -ge "$HOME_FAIL_STREAK_THRESHOLD" ]]; then
      edge_home_drop_at="$cycle"
    fi
  fi

  if [[ "$stcore_http_status" = "200" && "$stcore_body" = "ok" ]]; then
    streamlit_fail_streak=0
  else
    streamlit_fail_streak=$((streamlit_fail_streak + 1))
    if [[ "$streamlit_fail_streak" -gt "$streamlit_fail_streak_max" ]]; then
      streamlit_fail_streak_max="$streamlit_fail_streak"
    fi
    if [[ "$edge_streamlit_drop_at" = "none" && "$streamlit_fail_streak" -ge "$STREAMLIT_FAIL_STREAK_THRESHOLD" ]]; then
      edge_streamlit_drop_at="$cycle"
    fi
  fi

  if [[ "$cycle" -lt "$OBSERVE_CYCLES" && "$OBSERVE_INTERVAL_SECONDS" -gt 0 ]]; then
    sleep "$OBSERVE_INTERVAL_SECONDS"
  fi
done

edge_home_ok="yes"
edge_streamlit_ok="yes"
public_edge_state="healthy"

if [[ "$edge_home_drop_at" != "none" ]]; then
  edge_home_ok="no"
  public_edge_state="degraded"
fi
if [[ "$edge_streamlit_drop_at" != "none" ]]; then
  edge_streamlit_ok="no"
  public_edge_state="degraded"
fi

echo "base_url=$BASE_URL"
echo "edge_profile=$EDGE_PROFILE"
echo "observe_cycles=$OBSERVE_CYCLES"
echo "observe_interval_seconds=$OBSERVE_INTERVAL_SECONDS"
echo "edge_home_fail_streak_threshold=$HOME_FAIL_STREAK_THRESHOLD"
echo "edge_streamlit_fail_streak_threshold=$STREAMLIT_FAIL_STREAK_THRESHOLD"
echo "home_status=$home_status"
echo "title=$title"
echo "stcore_url=$stcore_url"
echo "stcore_http_status=$stcore_http_status"
echo "stcore_body=$stcore_body"
echo "edge_home_fail_streak_max=$home_fail_streak_max"
echo "edge_streamlit_fail_streak_max=$streamlit_fail_streak_max"
echo "edge_home_drop_at=$edge_home_drop_at"
echo "edge_streamlit_drop_at=$edge_streamlit_drop_at"
echo "edge_home_ok=$edge_home_ok"
echo "edge_streamlit_ok=$edge_streamlit_ok"
echo "public_edge_state=$public_edge_state"

if [[ "$public_edge_state" != "healthy" ]]; then
  exit 1
fi
