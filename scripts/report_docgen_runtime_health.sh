#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_BASE_URL="${1:-${DOCGEN_RUNTIME_PUBLIC_BASE_URL:-https://doc.niyoufei.com}}"
PUBLIC_RESOLVE_IP="${DOCGEN_RUNTIME_PUBLIC_RESOLVE_IP:-}"
SUMMARY_ONLY="${DOCGEN_RUNTIME_SUMMARY_ONLY:-0}"

ORIGIN_SCRIPT="${DOCGEN_RUNTIME_ORIGIN_SCRIPT:-$ROOT/scripts/verify_origin_app_health.sh}"
EDGE_SCRIPT="${DOCGEN_RUNTIME_EDGE_SCRIPT:-$ROOT/scripts/verify_public_edge_health.sh}"
PUBLIC_VERIFY_SCRIPT="${DOCGEN_RUNTIME_PUBLIC_VERIFY_SCRIPT:-$ROOT/scripts/verify_public_homepage_cutover.sh}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

run_capture() {
  local name="$1"
  shift
  local log="$TMP_DIR/${name}.log"
  set +e
  "$@" >"$log" 2>&1
  local rc=$?
  set -e
  printf '%s\n' "$rc" > "$TMP_DIR/${name}.rc"
}

rc_of() {
  cat "$TMP_DIR/$1.rc"
}

log_of() {
  cat "$TMP_DIR/$1.log"
}

value_from_log() {
  local key="$1"
  local log="$2"
  awk -F= -v k="$key" '$1 == k { print substr($0, index($0, "=") + 1); exit }' "$log"
}

run_capture origin bash "$ORIGIN_SCRIPT"
run_capture edge bash "$EDGE_SCRIPT" "$PUBLIC_BASE_URL"
if [[ -n "$PUBLIC_RESOLVE_IP" ]]; then
  run_capture public_verify bash "$PUBLIC_VERIFY_SCRIPT" "$PUBLIC_BASE_URL" "$PUBLIC_RESOLVE_IP"
else
  run_capture public_verify bash "$PUBLIC_VERIFY_SCRIPT" "$PUBLIC_BASE_URL"
fi

origin_state="fail"
public_edge_state="fail"
public_homepage_state="unknown"

if [[ "$(rc_of origin)" = "0" ]]; then
  origin_state="pass"
fi
if [[ "$(rc_of edge)" = "0" ]]; then
  public_edge_state="pass"
fi

public_cutover_verified="$(value_from_log cutover_verified "$TMP_DIR/public_verify.log")"
public_open_webui_present="$(value_from_log open_webui_present "$TMP_DIR/public_verify.log")"
public_edge_profile="$(value_from_log edge_profile "$TMP_DIR/edge.log")"
public_edge_observe_cycles="$(value_from_log observe_cycles "$TMP_DIR/edge.log")"
public_edge_home_fail_streak_threshold="$(value_from_log edge_home_fail_streak_threshold "$TMP_DIR/edge.log")"
public_edge_streamlit_fail_streak_threshold="$(value_from_log edge_streamlit_fail_streak_threshold "$TMP_DIR/edge.log")"
public_edge_home_drop_at="$(value_from_log edge_home_drop_at "$TMP_DIR/edge.log")"
public_edge_streamlit_drop_at="$(value_from_log edge_streamlit_drop_at "$TMP_DIR/edge.log")"
if [[ "$public_cutover_verified" = "yes" ]]; then
  public_homepage_state="docgen"
elif [[ "$public_open_webui_present" = "yes" ]]; then
  public_homepage_state="open-webui"
fi

runtime_monitoring_state="fail"
next_action="inspect_public_identity"
if [[ "$origin_state" != "pass" ]]; then
  next_action="fix_origin_runtime"
elif [[ "$public_edge_state" != "pass" ]]; then
  next_action="inspect_public_edge"
elif [[ "$public_homepage_state" = "open-webui" ]]; then
  next_action="inspect_public_identity"
elif [[ "$public_homepage_state" = "docgen" ]]; then
  runtime_monitoring_state="pass"
  next_action="healthy"
fi

echo "public_base_url=$PUBLIC_BASE_URL"
echo "public_resolve_ip=$PUBLIC_RESOLVE_IP"
echo "origin_app_state=$origin_state"
echo "public_edge_state=$public_edge_state"
echo "public_homepage_state=$public_homepage_state"
if [[ -n "$public_edge_profile" ]]; then
  echo "public_edge_profile=$public_edge_profile"
fi
if [[ -n "$public_edge_observe_cycles" ]]; then
  echo "public_edge_observe_cycles=$public_edge_observe_cycles"
fi
if [[ -n "$public_edge_home_fail_streak_threshold" ]]; then
  echo "public_edge_home_fail_streak_threshold=$public_edge_home_fail_streak_threshold"
fi
if [[ -n "$public_edge_streamlit_fail_streak_threshold" ]]; then
  echo "public_edge_streamlit_fail_streak_threshold=$public_edge_streamlit_fail_streak_threshold"
fi
if [[ -n "$public_edge_home_drop_at" ]]; then
  echo "public_edge_home_drop_at=$public_edge_home_drop_at"
fi
if [[ -n "$public_edge_streamlit_drop_at" ]]; then
  echo "public_edge_streamlit_drop_at=$public_edge_streamlit_drop_at"
fi
echo "runtime_monitoring_state=$runtime_monitoring_state"
echo "next_action=$next_action"

if [[ "$SUMMARY_ONLY" = "1" ]]; then
  if [[ "$runtime_monitoring_state" != "pass" ]]; then
    exit 1
  fi
  exit 0
fi

echo
echo "-- origin app verify --"
log_of origin

echo
echo "-- public edge verify --"
log_of edge

echo
echo "-- public identity verify --"
log_of public_verify

if [[ "$runtime_monitoring_state" != "pass" ]]; then
  exit 1
fi
