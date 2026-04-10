#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OBSERVE_SECONDS="${1:-${ZF_STATUS_OBSERVE_SECONDS:-60}}"
LOCAL_BASE_URL="${ZF_STATUS_LOCAL_BASE_URL:-http://127.0.0.1:8501}"
PUBLIC_BASE_URL="${ZF_STATUS_PUBLIC_BASE_URL:-https://doc.niyoufei.com}"
PUBLIC_RESOLVE_IP="${ZF_STATUS_PUBLIC_RESOLVE_IP:-}"
INCLUDE_PUSH_TEST="${ZF_STATUS_INCLUDE_PUSH_TEST:-1}"
INCLUDE_ASSET_TEST="${ZF_STATUS_INCLUDE_ASSET_TEST:-1}"
SUMMARY_ONLY="${ZF_STATUS_SUMMARY_ONLY:-0}"

READINESS_SCRIPT="${ZF_STATUS_READINESS_SCRIPT:-$ROOT/scripts/check_public_homepage_readiness.sh}"
VERIFY_SCRIPT="${ZF_STATUS_VERIFY_SCRIPT:-$ROOT/scripts/verify_public_homepage_cutover.sh}"
PUSH_TEST_SCRIPT="${ZF_STATUS_PUSH_TEST_SCRIPT:-$ROOT/scripts/test_push_public_homepage_cutover.sh}"
ASSET_TEST_SCRIPT="${ZF_STATUS_ASSET_TEST_SCRIPT:-$ROOT/scripts/test_public_homepage_cutover_assets.sh}"

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

run_capture readiness bash "$READINESS_SCRIPT" "$OBSERVE_SECONDS"
run_capture local_verify bash "$VERIFY_SCRIPT" "$LOCAL_BASE_URL"

if [[ -n "$PUBLIC_RESOLVE_IP" ]]; then
  run_capture public_verify bash "$VERIFY_SCRIPT" "$PUBLIC_BASE_URL" "$PUBLIC_RESOLVE_IP"
else
  run_capture public_verify bash "$VERIFY_SCRIPT" "$PUBLIC_BASE_URL"
fi

if [[ "$INCLUDE_PUSH_TEST" = "1" ]]; then
  run_capture push_test bash "$PUSH_TEST_SCRIPT"
fi

if [[ "$INCLUDE_ASSET_TEST" = "1" ]]; then
  run_capture asset_test bash "$ASSET_TEST_SCRIPT"
fi

readiness_rc="$(rc_of readiness)"
local_verify_rc="$(rc_of local_verify)"
public_verify_rc="$(rc_of public_verify)"

push_test_rc="skipped"
asset_test_rc="skipped"
if [[ "$INCLUDE_PUSH_TEST" = "1" ]]; then
  push_test_rc="$(rc_of push_test)"
fi
if [[ "$INCLUDE_ASSET_TEST" = "1" ]]; then
  asset_test_rc="$(rc_of asset_test)"
fi

readiness_state="fail"
local_homepage_state="fail"
push_test_state="skipped"
asset_test_state="skipped"
public_homepage_state="unknown"

if [[ "$readiness_rc" = "0" ]]; then
  readiness_state="pass"
fi
if [[ "$local_verify_rc" = "0" ]]; then
  local_homepage_state="docgen"
fi
if [[ "$push_test_rc" = "0" ]]; then
  push_test_state="pass"
elif [[ "$push_test_rc" != "skipped" ]]; then
  push_test_state="fail"
fi
if [[ "$asset_test_rc" = "0" ]]; then
  asset_test_state="pass"
elif [[ "$asset_test_rc" != "skipped" ]]; then
  asset_test_state="fail"
fi

public_cutover_verified="$(value_from_log cutover_verified "$TMP_DIR/public_verify.log")"
public_open_webui_present="$(value_from_log open_webui_present "$TMP_DIR/public_verify.log")"
if [[ "$public_cutover_verified" = "yes" ]]; then
  public_homepage_state="docgen"
elif [[ "$public_open_webui_present" = "yes" ]]; then
  public_homepage_state="open-webui"
fi

ready_to_apply="no"
if [[ "$readiness_state" = "pass" ]] && \
   [[ "$local_homepage_state" = "docgen" ]] && \
   { [[ "$push_test_state" = "pass" ]] || [[ "$push_test_state" = "skipped" ]]; } && \
   { [[ "$asset_test_state" = "pass" ]] || [[ "$asset_test_state" = "skipped" ]]; }; then
  ready_to_apply="yes"
fi

public_cutover_needed="unknown"
case "$public_homepage_state" in
  docgen)
    public_cutover_needed="no"
    ;;
  open-webui)
    public_cutover_needed="yes"
    ;;
esac

next_action="inspect_public_homepage"
if [[ "$readiness_state" != "pass" ]]; then
  next_action="fix_local_readiness"
elif [[ "$local_homepage_state" != "docgen" ]]; then
  next_action="fix_local_homepage"
elif [[ "$push_test_state" = "fail" ]] || [[ "$asset_test_state" = "fail" ]]; then
  next_action="fix_cutover_tooling"
elif [[ "$public_homepage_state" = "open-webui" ]]; then
  next_action="apply_public_cutover"
elif [[ "$public_homepage_state" = "docgen" ]]; then
  next_action="none_already_cutover"
fi

echo "observe_seconds=${OBSERVE_SECONDS}"
echo "local_base_url=${LOCAL_BASE_URL}"
echo "public_base_url=${PUBLIC_BASE_URL}"
echo "public_resolve_ip=${PUBLIC_RESOLVE_IP}"
echo "readiness_state=${readiness_state}"
echo "local_homepage_state=${local_homepage_state}"
echo "push_test_state=${push_test_state}"
echo "asset_test_state=${asset_test_state}"
echo "public_homepage_state=${public_homepage_state}"
echo "public_cutover_needed=${public_cutover_needed}"
echo "ready_to_apply=${ready_to_apply}"
echo "next_action=${next_action}"

if [[ "$SUMMARY_ONLY" = "1" ]]; then
  if [[ "$ready_to_apply" != "yes" ]]; then
    exit 1
  fi
  exit 0
fi

echo
echo "-- readiness output --"
log_of readiness

echo
echo "-- local homepage verify --"
log_of local_verify

echo
echo "-- public homepage verify --"
log_of public_verify

if [[ "$INCLUDE_PUSH_TEST" = "1" ]]; then
  echo
  echo "-- push regression --"
  log_of push_test
fi

if [[ "$INCLUDE_ASSET_TEST" = "1" ]]; then
  echo
  echo "-- asset regression --"
  log_of asset_test
fi

if [[ "$ready_to_apply" != "yes" ]]; then
  exit 1
fi
