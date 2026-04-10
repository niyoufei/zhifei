#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
REMOTE_HOST="${2:-${DOCGEN_ORIGIN_HOST:-}}"
REMOTE_BASE_DIR="${DOCGEN_REMOTE_BASE_DIR:-~/docgen-domain}"
SSH_OPTS="${DOCGEN_SSH_OPTS:-}"
SCP_BIN="${DOCGEN_SCP_BIN:-scp}"
SSH_BIN="${DOCGEN_SSH_BIN:-ssh}"
PROXY_STACK="${DOCGEN_PROXY_STACK:-nginx}"
REMOTE_INSTALL="${DOCGEN_REMOTE_INSTALL:-1}"
REMOTE_APPLY="${DOCGEN_REMOTE_APPLY:-0}"
PREVIEW="${DOCGEN_PREVIEW:-0}"
VERIFY_BASE_URL="${DOCGEN_VERIFY_BASE_URL:-}"
VERIFY_RESOLVE_IP="${DOCGEN_VERIFY_RESOLVE_IP:-}"
SSL_PROFILE="${DOCGEN_SSL_PROFILE:-letsencrypt}"
BUNDLE_NAME="${DOMAIN}.${PROXY_STACK}"

format_command() {
  python3 - "$@" <<'PY'
import shlex
import sys

print(" ".join(shlex.quote(arg) for arg in sys.argv[1:]))
PY
}

if [[ -z "$DOMAIN" || -z "$REMOTE_HOST" ]]; then
  echo "[ERROR] usage: $0 <full-domain> <user@host>" >&2
  echo "        example: $0 doc.niyoufei.com root@199.180.118.204" >&2
  exit 1
fi

bash "$ROOT/scripts/package_linux_domain_bundle.sh" "$DOMAIN"

ARCHIVE_BASENAME="${DOMAIN}.${PROXY_STACK}.tar.gz"
ARCHIVE_PATH="$ROOT/build/domain_bundle_release/${ARCHIVE_BASENAME}"
REMOTE_ARCHIVE="~/${ARCHIVE_BASENAME}"

remote_cmd=$(cat <<EOF
set -euo pipefail
mkdir -p ${REMOTE_BASE_DIR}
tar -xzf ${REMOTE_ARCHIVE} -C ${REMOTE_BASE_DIR}
cd ${REMOTE_BASE_DIR}/${BUNDLE_NAME}
bash ./detect_linux_proxy_stack.sh ${DOMAIN} || true
bash ./suggest_linux_origin_fix.sh ${DOMAIN} || true
export DOCGEN_PROXY_STACK=${PROXY_STACK}
EOF
)

if [[ "$REMOTE_INSTALL" = "1" ]]; then
  remote_cmd+=$'\n'"sudo -E ./install_bundle_on_origin.sh"
  remote_cmd+=$'\n'"DOCGEN_PROXY_STACK=${PROXY_STACK} bash ./verify_linux_domain_origin.sh ${DOMAIN}"
fi

if [[ -n "$VERIFY_RESOLVE_IP" ]]; then
  remote_cmd+=$'\n'"export DOCGEN_VERIFY_RESOLVE_IP=${VERIFY_RESOLVE_IP}"
fi

if [[ -n "$VERIFY_BASE_URL" ]]; then
  remote_cmd+=$'\n'"export DOCGEN_VERIFY_BASE_URL=${VERIFY_BASE_URL}"
fi

if [[ "$REMOTE_APPLY" = "1" ]]; then
  remote_cmd+=$'\n'"DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${SSL_PROFILE} bash ./execute_public_homepage_cutover.sh ${DOMAIN}"
else
  remote_cmd+=$'\n'"bash ./execute_public_homepage_cutover.sh ${DOMAIN}"
fi

scp_cmd=("$SCP_BIN")
ssh_cmd=("$SSH_BIN")
if [[ -n "$SSH_OPTS" ]]; then
  # shellcheck disable=SC2206
  ssh_opts_parts=($SSH_OPTS)
  scp_cmd+=("${ssh_opts_parts[@]}")
  ssh_cmd+=("${ssh_opts_parts[@]}")
fi
scp_cmd+=("$ARCHIVE_PATH" "${REMOTE_HOST}:${REMOTE_ARCHIVE}")
ssh_cmd+=("$REMOTE_HOST" "$remote_cmd")

if [[ "$PREVIEW" = "1" ]]; then
  printf 'archive_path=%s\n' "$ARCHIVE_PATH"
  printf 'remote_archive=%s\n' "$REMOTE_ARCHIVE"
  printf 'remote_install=%s\n' "$REMOTE_INSTALL"
  printf 'remote_apply=%s\n' "$REMOTE_APPLY"
  printf 'verify_base_url=%s\n' "$VERIFY_BASE_URL"
  printf 'verify_resolve_ip=%s\n' "$VERIFY_RESOLVE_IP"
  printf 'scp_bin=%s\n' "$SCP_BIN"
  printf 'ssh_bin=%s\n' "$SSH_BIN"
  printf 'scp_command=%s\n' "$(format_command "${scp_cmd[@]}")"
  printf 'ssh_command=%s\n' "$(format_command "${ssh_cmd[@]}")"
  exit 0
fi

"${scp_cmd[@]}"
"${ssh_cmd[@]}"

if [[ "$REMOTE_APPLY" = "1" ]]; then
  echo "[OK] uploaded and applied public homepage cutover: ${DOMAIN} -> ${REMOTE_HOST}"
else
  echo "[OK] uploaded and dry-ran public homepage cutover: ${DOMAIN} -> ${REMOTE_HOST}"
fi
