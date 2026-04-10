#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${1:-${DOCGEN_APP_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}}"
RELEASE_DIR="${DOCGEN_RELEASE_DIR:-${APP_ROOT%/}/releases}"
LATEST_RELEASE_PATH="${DOCGEN_LATEST_RELEASE_PATH:-${RELEASE_DIR%/}/latest-release.txt}"
INSPECTION_STATUS_PATH="${DOCGEN_READONLY_INSPECTION_STATUS_PATH:-${APP_ROOT%/}/logs/readonly_inspection/latest-status.txt}"
RETENTION_STATUS_PATH="${DOCGEN_READONLY_RETENTION_STATUS_PATH:-${APP_ROOT%/}/logs/readonly_retention/latest-status.txt}"
SERVICE_NAME="${DOCGEN_SERVICE_NAME:-docgen-autoplan.service}"
SYSTEMCTL_BIN="${DOCGEN_SYSTEMCTL_BIN:-systemctl}"
CURL_BIN="${DOCGEN_CURL_BIN:-curl}"
BACKEND_HEALTH_URL="${DOCGEN_BACKEND_HEALTH_URL:-http://127.0.0.1:8010/health}"
STREAMLIT_HEALTH_URL="${DOCGEN_STREAMLIT_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"

read_kv() {
  local key="$1"
  local file="$2"
  awk -F= -v wanted="$key" '$1 == wanted {print substr($0, index($0, "=") + 1); exit}' "$file"
}

have_cmd() {
  local candidate="$1"
  if [[ "$candidate" == */* ]]; then
    [[ -x "$candidate" ]]
    return
  fi
  command -v "$candidate" >/dev/null 2>&1
}

latest_release="none"
release_pointer_state="fail"
if [[ -f "$LATEST_RELEASE_PATH" ]]; then
  latest_release="$(tr -d '\n' < "$LATEST_RELEASE_PATH")"
  [[ -n "$latest_release" ]] || latest_release="none"
  if [[ "$latest_release" != "none" ]]; then
    release_pointer_state="pass"
  fi
fi

inspection_status_state="fail"
inspection_run_id="none"
release_dir_state="unknown"
server_worktree_state="unknown"
runtime_monitoring_state="unknown"
readonly_retention_state="unknown"
readonly_retention_run_id="none"
readonly_retention_prune_candidates_count="unknown"
readonly_retention_execute_allowed="unknown"
inspection_next_action="run-readonly-inspection"
inspection_overall_state="fail"
if [[ -f "$INSPECTION_STATUS_PATH" ]]; then
  inspection_status_state="pass"
  inspection_run_id="$(read_kv "run_id" "$INSPECTION_STATUS_PATH" || true)"
  release_dir_state="$(read_kv "release_dir_state" "$INSPECTION_STATUS_PATH" || true)"
  server_worktree_state="$(read_kv "server_worktree_state" "$INSPECTION_STATUS_PATH" || true)"
  runtime_monitoring_state="$(read_kv "runtime_monitoring_state" "$INSPECTION_STATUS_PATH" || true)"
  readonly_retention_state="$(read_kv "readonly_retention_state" "$INSPECTION_STATUS_PATH" || true)"
  readonly_retention_run_id="$(read_kv "readonly_retention_run_id" "$INSPECTION_STATUS_PATH" || true)"
  readonly_retention_prune_candidates_count="$(read_kv "readonly_retention_prune_candidates_count" "$INSPECTION_STATUS_PATH" || true)"
  readonly_retention_execute_allowed="$(read_kv "readonly_retention_execute_allowed" "$INSPECTION_STATUS_PATH" || true)"
  inspection_next_action="$(read_kv "next_action" "$INSPECTION_STATUS_PATH" || true)"
  inspection_overall_state="$(read_kv "overall_state" "$INSPECTION_STATUS_PATH" || true)"
  [[ -n "$inspection_run_id" ]] || inspection_run_id="none"
  [[ -n "$release_dir_state" ]] || release_dir_state="unknown"
  [[ -n "$server_worktree_state" ]] || server_worktree_state="unknown"
  [[ -n "$runtime_monitoring_state" ]] || runtime_monitoring_state="unknown"
  [[ -n "$readonly_retention_state" ]] || readonly_retention_state="unknown"
  [[ -n "$readonly_retention_run_id" ]] || readonly_retention_run_id="none"
  [[ -n "$readonly_retention_prune_candidates_count" ]] || readonly_retention_prune_candidates_count="unknown"
  [[ -n "$readonly_retention_execute_allowed" ]] || readonly_retention_execute_allowed="unknown"
  [[ -n "$inspection_next_action" ]] || inspection_next_action="run-readonly-inspection"
  [[ -n "$inspection_overall_state" ]] || inspection_overall_state="fail"
fi

retention_status_state="fail"
retention_run_id_current="none"
retention_prune_candidates_count_current="unknown"
retention_execute_allowed_current="unknown"
retention_next_action_current="unknown"
retention_overall_state_current="fail"
if [[ -f "$RETENTION_STATUS_PATH" ]]; then
  retention_status_state="pass"
  retention_run_id_current="$(read_kv "run_id" "$RETENTION_STATUS_PATH" || true)"
  retention_prune_candidates_count_current="$(read_kv "prune_candidates_count" "$RETENTION_STATUS_PATH" || true)"
  retention_execute_allowed_current="$(read_kv "execute_allowed" "$RETENTION_STATUS_PATH" || true)"
  retention_next_action_current="$(read_kv "next_action" "$RETENTION_STATUS_PATH" || true)"
  retention_overall_state_current="$(read_kv "overall_state" "$RETENTION_STATUS_PATH" || true)"
  [[ -n "$retention_run_id_current" ]] || retention_run_id_current="none"
  [[ -n "$retention_prune_candidates_count_current" ]] || retention_prune_candidates_count_current="unknown"
  [[ -n "$retention_execute_allowed_current" ]] || retention_execute_allowed_current="unknown"
  [[ -n "$retention_next_action_current" ]] || retention_next_action_current="unknown"
  [[ -n "$retention_overall_state_current" ]] || retention_overall_state_current="fail"
fi

retention_status_sync_state="fail"
if [[ "$inspection_status_state" = "pass" && "$retention_status_state" = "pass" ]]; then
  if [[ "$readonly_retention_run_id" = "$retention_run_id_current" ]] \
    && [[ "$readonly_retention_prune_candidates_count" = "$retention_prune_candidates_count_current" ]] \
    && [[ "$readonly_retention_execute_allowed" = "$retention_execute_allowed_current" ]]; then
    retention_status_sync_state="pass"
  fi
fi

service_unit_state="unknown"
if have_cmd "$SYSTEMCTL_BIN"; then
  service_unit_state="$("$SYSTEMCTL_BIN" is-active "$SERVICE_NAME" 2>/dev/null || true)"
  [[ -n "$service_unit_state" ]] || service_unit_state="unknown"
fi

backend_health_state="fail"
backend_health_body="unavailable"
if have_cmd "$CURL_BIN"; then
  if backend_health_body="$("$CURL_BIN" -fsS "$BACKEND_HEALTH_URL" 2>/dev/null)" \
    && printf '%s' "$backend_health_body" | grep -Fq '"ok":true'; then
    backend_health_state="pass"
  fi
fi

streamlit_health_state="fail"
streamlit_health_body="unavailable"
if have_cmd "$CURL_BIN"; then
  if streamlit_health_body="$("$CURL_BIN" -fsS "$STREAMLIT_HEALTH_URL" 2>/dev/null)" \
    && [[ "$streamlit_health_body" = "ok" ]]; then
    streamlit_health_state="pass"
  fi
fi

overall_state="pass"
next_action="${inspection_next_action:-healthy}"
[[ -n "$next_action" ]] || next_action="healthy"

if [[ "$release_pointer_state" != "pass" ]]; then
  overall_state="fail"
  next_action="inspect-release-dir"
fi

if [[ "$inspection_status_state" != "pass" || "$inspection_overall_state" != "pass" ]]; then
  overall_state="fail"
  next_action="run-readonly-inspection"
fi

if [[ "$retention_status_sync_state" != "pass" ]]; then
  overall_state="fail"
  next_action="run-readonly-inspection"
fi

if [[ "$service_unit_state" != "active" || "$backend_health_state" != "pass" || "$streamlit_health_state" != "pass" ]]; then
  overall_state="fail"
  next_action="inspect-runtime-health"
fi

echo "app_root=${APP_ROOT}"
echo "release_dir=${RELEASE_DIR}"
echo "latest_release=${latest_release}"
echo "release_pointer_state=${release_pointer_state}"
echo "inspection_status_path=${INSPECTION_STATUS_PATH}"
echo "inspection_status_state=${inspection_status_state}"
echo "inspection_run_id=${inspection_run_id}"
echo "release_dir_state=${release_dir_state}"
echo "server_worktree_state=${server_worktree_state}"
echo "runtime_monitoring_state=${runtime_monitoring_state}"
echo "readonly_retention_state=${readonly_retention_state}"
echo "readonly_retention_run_id=${readonly_retention_run_id}"
echo "readonly_retention_prune_candidates_count=${readonly_retention_prune_candidates_count}"
echo "readonly_retention_execute_allowed=${readonly_retention_execute_allowed}"
echo "inspection_next_action=${inspection_next_action}"
echo "inspection_overall_state=${inspection_overall_state}"
echo "retention_status_path=${RETENTION_STATUS_PATH}"
echo "retention_status_state=${retention_status_state}"
echo "retention_run_id_current=${retention_run_id_current}"
echo "retention_prune_candidates_count_current=${retention_prune_candidates_count_current}"
echo "retention_execute_allowed_current=${retention_execute_allowed_current}"
echo "retention_next_action_current=${retention_next_action_current}"
echo "retention_overall_state_current=${retention_overall_state_current}"
echo "retention_status_sync_state=${retention_status_sync_state}"
echo "service_name=${SERVICE_NAME}"
echo "service_unit_state=${service_unit_state}"
echo "backend_health_url=${BACKEND_HEALTH_URL}"
echo "backend_health_state=${backend_health_state}"
echo "streamlit_health_url=${STREAMLIT_HEALTH_URL}"
echo "streamlit_health_state=${streamlit_health_state}"
echo "next_action=${next_action}"
echo "overall_state=${overall_state}"

if [[ "$overall_state" != "pass" ]]; then
  exit 1
fi

echo "[SUMMARY] all checks passed."
