#!/usr/bin/env bash
set -euo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
APPLY="${DOCGEN_APPLY:-0}"
OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
VERIFY_BASE_URL="${DOCGEN_VERIFY_BASE_URL:-}"
VERIFY_RESOLVE_IP="${DOCGEN_VERIFY_RESOLVE_IP:-}"
SSL_PROFILE="${DOCGEN_SSL_PROFILE:-letsencrypt}"
INSPECT_SCRIPT="${SELF_DIR}/inspect_public_homepage_origin_conf.sh"
TOPOLOGY_SCRIPT="${SELF_DIR}/inspect_public_homepage_live_topology.sh"
CUTOVER_SCRIPT="${SELF_DIR}/cutover_public_homepage_origin.sh"
MULTI_CUTOVER_SCRIPT="${SELF_DIR}/cutover_public_homepage_upstream_targets.sh"
VERIFY_SCRIPT="${SELF_DIR}/verify_public_homepage_cutover.sh"

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站执行。" >&2
  exit 1
fi

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain>" >&2
  echo "        example: $0 doc.niyoufei.com" >&2
  exit 1
fi

if [[ -z "$VERIFY_BASE_URL" ]]; then
  VERIFY_BASE_URL="https://${DOMAIN}"
fi

inspect_output="$(bash "$INSPECT_SCRIPT" "$DOMAIN" 2>&1 || true)"
topology_output="$(bash "$TOPOLOGY_SCRIPT" "$DOMAIN" 2>&1 || true)"

target_conf_path="$(printf '%s\n' "$inspect_output" | awk -F= '/^\[RECOMMEND\] target_conf_path=/{print $2; exit}')"
current_upstream_kind="$(printf '%s\n' "$inspect_output" | awk -F= '/^\[RECOMMEND\] current_upstream_kind=/{print $2; exit}')"
topology_kind="$(printf '%s\n' "$topology_output" | awk -F= '/^\[RECOMMEND\] topology=/{print $2; exit}')"
topology_patch_count="$(printf '%s\n' "$topology_output" | awk -F= '/^\[RECOMMEND\] patch_count=/{print $2; exit}')"

if [[ -n "$topology_patch_count" && "$topology_patch_count" -gt 1 ]]; then
  printf '%s\n' "$topology_output"

  multi_paths=()
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    path="${line%%|*}"
    multi_paths+=("$path")
  done < <(printf '%s\n' "$topology_output" | awk -F= '/^\[RECOMMEND\] patch_target=/{print $2}')

  if [[ "${#multi_paths[@]}" -eq 0 ]]; then
    echo "[BLOCKED] 已识别为多 upstream 拓扑，但未能解析 patch targets。" >&2
    exit 2
  fi

  deduped_paths=()
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    deduped_paths+=("$line")
  done < <(printf '%s\n' "${multi_paths[@]}" | awk '!seen[$0]++')

  echo "[INFO] execute topology=${topology_kind:-unknown}"
  echo "[INFO] execute patch_count=${topology_patch_count}"
  echo "[STEP] dry-run multi-upstream cutover"
  bash "$MULTI_CUTOVER_SCRIPT" "$DOMAIN" "${deduped_paths[@]}"

  if [[ "$APPLY" != "1" ]]; then
    echo "[INFO] 当前为 dry-run 模式，未写入源站配置。"
    echo "[INFO] 如需真正切换，请重新执行："
    echo "       DOCGEN_APPLY=1 bash ./execute_public_homepage_cutover.sh ${DOMAIN}"
    exit 0
  fi

  echo "[STEP] apply multi-upstream cutover"
  DOCGEN_APPLY=1 bash "$MULTI_CUTOVER_SCRIPT" "$DOMAIN" "${deduped_paths[@]}"

  echo "[STEP] verify public homepage cutover"
  bash "$VERIFY_SCRIPT" "$VERIFY_BASE_URL" "$VERIFY_RESOLVE_IP"

  echo "[OK] public homepage cutover completed"
  echo "     domain=${DOMAIN}"
  echo "     topology=${topology_kind:-unknown}"
  echo "     verify_base_url=${VERIFY_BASE_URL}"
  if [[ -n "$VERIFY_RESOLVE_IP" ]]; then
    echo "     verify_resolve_ip=${VERIFY_RESOLVE_IP}"
  fi
  exit 0
fi

printf '%s\n' "$inspect_output"
printf '%s\n' "$topology_output"

if [[ -z "$target_conf_path" ]]; then
  echo "[BLOCKED] 未能从 inspect 输出中解析到唯一 target_conf_path。" >&2
  exit 2
fi

echo "[INFO] execute target_conf_path=${target_conf_path}"
echo "[INFO] current_upstream_kind=${current_upstream_kind:-unknown}"

echo "[STEP] dry-run cutover config"
bash "$CUTOVER_SCRIPT" "$DOMAIN" "$target_conf_path"

if [[ "$APPLY" != "1" ]]; then
  echo "[INFO] 当前为 dry-run 模式，未写入源站配置。"
  echo "[INFO] 如需真正切换，请重新执行："
  echo "       DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${SSL_PROFILE} bash ./execute_public_homepage_cutover.sh ${DOMAIN}"
  exit 0
fi

echo "[STEP] apply cutover config"
DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE="$SSL_PROFILE" bash "$CUTOVER_SCRIPT" "$DOMAIN" "$target_conf_path"

echo "[STEP] verify public homepage cutover"
bash "$VERIFY_SCRIPT" "$VERIFY_BASE_URL" "$VERIFY_RESOLVE_IP"

echo "[OK] public homepage cutover completed"
echo "     domain=${DOMAIN}"
echo "     target_conf_path=${target_conf_path}"
echo "     verify_base_url=${VERIFY_BASE_URL}"
if [[ -n "$VERIFY_RESOLVE_IP" ]]; then
  echo "     verify_resolve_ip=${VERIFY_RESOLVE_IP}"
fi
