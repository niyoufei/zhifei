#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-}"
if [[ -z "${TAG}" ]]; then
  TAG="$(git tag --list "v0.4-quality-gate-mode.*" --sort=version:refname | tail -1 || true)"
fi

if [[ -z "${TAG}" ]]; then
  echo "[FAIL] push_safe: no tag provided and no v0.4-quality-gate-mode.* tags found."
  exit 2
fi

echo "== push_safe: target = main + ${TAG} =="

dns_ok=0
tcp_ok=0

echo
echo "== MECE A) DNS check (github.com) =="
if dig +time=2 +tries=1 github.com A +short >/dev/null 2>&1; then
  dig +time=2 +tries=1 github.com A +short | head -n 2 || true
  dns_ok=1
else
  echo "[FAIL] DNS cannot resolve github.com via system resolver."
  dns_ok=0
fi

echo
echo "== MECE B) TCP/443 check (github.com) =="
if curl -I https://github.com --max-time 6 >/dev/null 2>&1; then
  echo "[OK] TCP/443 reachable"
  tcp_ok=1
else
  echo "[FAIL] TCP/443 not reachable (direct)"
  tcp_ok=0
fi

echo
echo "== MECE C) System proxy detection (scutil --proxy) =="
PXY="$(scutil --proxy || true)"
getv(){ echo "$PXY" | awk -v k="$1" -F" : " '$1==k{gsub(/^[ \t]+|[ \t]+$/,"",$2); print $2}' | tail -1; }

SOCKS_EN="$(getv SOCKSEnable || true)"
SOCKS_H="$(getv SOCKSProxy || true)"
SOCKS_P="$(getv SOCKSPort || true)"
HTTPS_EN="$(getv HTTPSEnable || true)"
HTTPS_H="$(getv HTTPSProxy || true)"
HTTPS_P="$(getv HTTPSPort || true)"
HTTP_EN="$(getv HTTPEnable || true)"
HTTP_H="$(getv HTTPProxy || true)"
HTTP_P="$(getv HTTPPort || true)"

echo "SOCKS: enable=${SOCKS_EN:-0} ${SOCKS_H:-} ${SOCKS_P:-}"
echo "HTTPS: enable=${HTTPS_EN:-0} ${HTTPS_H:-} ${HTTPS_P:-}"
echo "HTTP : enable=${HTTP_EN:-0} ${HTTP_H:-} ${HTTP_P:-}"

PROXY_URL=""
if [[ "${SOCKS_EN:-0}" == "1" && -n "${SOCKS_H:-}" && -n "${SOCKS_P:-}" ]]; then
  PROXY_URL="socks5h://${SOCKS_H}:${SOCKS_P}"
elif [[ "${HTTPS_EN:-0}" == "1" && -n "${HTTPS_H:-}" && -n "${HTTPS_P:-}" ]]; then
  PROXY_URL="http://${HTTPS_H}:${HTTPS_P}"
elif [[ "${HTTP_EN:-0}" == "1" && -n "${HTTP_H:-}" && -n "${HTTP_P:-}" ]]; then
  PROXY_URL="http://${HTTP_H}:${HTTP_P}"
fi

push_direct() {
  git -c http.version=HTTP/1.1 push origin main
  git -c http.version=HTTP/1.1 push origin "${TAG}"
}

push_via_proxy() {
  local px="$1"
  HTTPS_PROXY="$px" HTTP_PROXY="$px" ALL_PROXY="$px" \
    git -c http.version=HTTP/1.1 push origin main
  HTTPS_PROXY="$px" HTTP_PROXY="$px" ALL_PROXY="$px" \
    git -c http.version=HTTP/1.1 push origin "${TAG}"
}

echo
echo "== Action) push attempt =="
if [[ "${tcp_ok}" == "1" ]]; then
  echo "[INFO] using direct push (TCP/443 OK)"
  push_direct
else
  if [[ -n "${PROXY_URL}" ]]; then
    echo "[INFO] using system proxy: ${PROXY_URL}"
    HTTPS_PROXY="$PROXY_URL" HTTP_PROXY="$PROXY_URL" ALL_PROXY="$PROXY_URL" \
      curl -I https://github.com --max-time 8 >/dev/null && echo "[OK] github.com:443 via proxy" || echo "[WARN] github.com:443 via proxy test failed (still trying git push)"
    push_via_proxy "${PROXY_URL}"
  else
    echo "[FAIL] No direct TCP/443 and no system proxy enabled."
    echo "MECE next steps:"
    echo "1) Switch network (hotspot) and retry, OR"
    echo "2) Enable System Proxy/TUN in your proxy client so scutil --proxy shows enable=1."
    exit 2
  fi
fi

echo
echo "== Verify) remote tag exists =="
git ls-remote --tags origin "${TAG}"
git status -sb
echo "[OK] push_safe done"
