#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
SEARCH_DIRS_RAW="${DOCGEN_NGINX_SEARCH_DIRS:-/etc/nginx/conf.d:/etc/nginx/sites-enabled:/etc/nginx/sites-available}"
SSL_PROFILE_HINT="${DOCGEN_SSL_PROFILE_HINT:-letsencrypt}"

if [[ -z "$DOMAIN" ]]; then
  echo "[ERROR] usage: $0 <full-domain>" >&2
  echo "        example: $0 doc.niyoufei.com" >&2
  exit 1
fi

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] 该脚本仅用于 Linux 源站只读检查。" >&2
  exit 1
fi

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

extract_match_line() {
  local pattern="$1"
  local file="$2"
  awk -v pat="$pattern" '
    BEGIN { IGNORECASE = 1 }
    $0 ~ pat { gsub(/^[[:space:]]+/, "", $0); print; exit }
  ' "$file" 2>/dev/null || true
}

classify_upstream() {
  local line="$1"
  if [[ "$line" == *"127.0.0.1:8501"* ]]; then
    printf '%s' "docgen-streamlit"
  elif [[ "$line" == *"127.0.0.1:3000"* ]]; then
    printf '%s' "open-webui"
  elif [[ -n "$line" ]]; then
    printf '%s' "custom"
  else
    printf '%s' "unknown"
  fi
}

search_dirs=()
IFS=':' read -r -a raw_dirs <<< "$SEARCH_DIRS_RAW"
for dir in "${raw_dirs[@]}"; do
  dir="$(trim "$dir")"
  [[ -n "$dir" ]] || continue
  search_dirs+=("$dir")
done

matches=()

for dir in "${search_dirs[@]}"; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r -d '' file; do
    if grep -Eiq "(^|[[:space:]])server_name([[:space:]]+[^;#]*)${DOMAIN}([[:space:];]|$)" "$file"; then
      matches+=("$file")
    fi
  done < <(find "$dir" -maxdepth 1 -type f \( -name '*.conf' -o -name '*.vhost' -o -name '*.inc' -o -name '*' \) -print0 2>/dev/null)
done

echo "[INFO] domain=${DOMAIN}"
echo "[INFO] search_dirs=${SEARCH_DIRS_RAW}"
echo "[INFO] match_count=${#matches[@]}"

if [[ "${#matches[@]}" -eq 0 ]]; then
  echo "[WARN] 未在默认 nginx 目录中找到 server_name 命中 ${DOMAIN} 的 conf。"
  echo "[WARN] 可改用 DOCGEN_NGINX_SEARCH_DIRS 扩大搜索范围。"
  exit 2
fi

for file in "${matches[@]}"; do
  server_line="$(extract_match_line "server_name[[:space:]].*${DOMAIN}" "$file")"
  listen_line="$(extract_match_line "listen[[:space:]]+" "$file")"
  proxy_line="$(extract_match_line "proxy_pass[[:space:]]+" "$file")"
  upstream_kind="$(classify_upstream "$proxy_line")"
  echo "[MATCH] path=${file}"
  echo "[MATCH] server_name=${server_line:-none}"
  echo "[MATCH] listen=${listen_line:-none}"
  echo "[MATCH] proxy_pass=${proxy_line:-none}"
  echo "[MATCH] upstream_kind=${upstream_kind}"
done

if [[ "${#matches[@]}" -eq 1 ]]; then
  target_path="${matches[0]}"
  proxy_line="$(extract_match_line "proxy_pass[[:space:]]+" "$target_path")"
  upstream_kind="$(classify_upstream "$proxy_line")"
  echo "[RECOMMEND] target_conf_path=${target_path}"
  echo "[RECOMMEND] current_upstream=${proxy_line:-unknown}"
  echo "[RECOMMEND] current_upstream_kind=${upstream_kind}"
  echo "[RECOMMEND] cutover_dry_run=bash ./cutover_public_homepage_origin.sh ${DOMAIN} ${target_path}"
  echo "[RECOMMEND] cutover_apply=DOCGEN_APPLY=1 DOCGEN_SSL_PROFILE=${SSL_PROFILE_HINT} bash ./cutover_public_homepage_origin.sh ${DOMAIN} ${target_path}"
  exit 0
fi

echo "[BLOCKED] 命中多个 conf，暂不自动给出单一 target_conf_path。"
echo "[BLOCKED] 请先人工确认哪个 conf 当前真正服务于 ${DOMAIN}。"
exit 3
