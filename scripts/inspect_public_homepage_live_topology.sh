#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
SEARCH_DIRS_RAW="${DOCGEN_NGINX_SEARCH_DIRS:-/etc/nginx/conf.d:/etc/nginx/sites-enabled:/etc/nginx/sites-available}"
XRAY_SEARCH_DIR="${DOCGEN_XRAY_SEARCH_DIR:-/etc/v2ray-agent/xray/conf}"
CURRENT_UPSTREAM="${DOCGEN_CURRENT_UPSTREAM:-http://127.0.0.1:3000}"
TARGET_UPSTREAM="${DOCGEN_TARGET_UPSTREAM:-http://127.0.0.1:8501}"
INCLUDE_INACTIVE_CONF="${DOCGEN_INCLUDE_INACTIVE_CONF:-0}"

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

extract_match_lines() {
  local pattern="$1"
  local file="$2"
  awk -v pat="$pattern" '
    BEGIN { IGNORECASE = 1 }
    $0 ~ pat {
      gsub(/^[[:space:]]+/, "", $0)
      print
    }
  ' "$file" 2>/dev/null || true
}

extract_ports_from_lines() {
  local text="$1"
  printf '%s\n' "$text" | \
    awk '
      {
        for (i = 1; i <= NF; i++) {
          if ($i ~ /^[0-9]+$/) {
            print $i
            break
          }
          if ($i ~ /:[0-9]+$/) {
            sub(/.*:/, "", $i)
            sub(/[^0-9].*$/, "", $i)
            if ($i ~ /^[0-9]+$/) {
              print $i
              break
            }
          }
        }
      }
    ' | sort -u
}

search_dirs=()
IFS=':' read -r -a raw_dirs <<< "$SEARCH_DIRS_RAW"
for dir in "${raw_dirs[@]}"; do
  dir="$(trim "$dir")"
  [[ -n "$dir" ]] || continue
  search_dirs+=("$dir")
done

nginx_matches=()
listen_ports=()
patch_targets=()
match_count=0

for dir in "${search_dirs[@]}"; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r -d '' file; do
    base_name="$(basename "$file")"
    if [[ "$INCLUDE_INACTIVE_CONF" != "1" ]]; then
      case "$base_name" in
        *.bak|*.bak.*|*.disabled|*.disabled-*|*.minbak-*|*.fixbak-*|*.old|*.orig|*.save)
          continue
          ;;
      esac
    fi
    if grep -Fqi "$DOMAIN" "$file"; then
      nginx_matches+=("$file")
    fi
  done < <(find "$dir" -maxdepth 1 -type f \( -name '*.conf' -o -name '*.vhost' -o -name '*.inc' -o -name '*' \) -print0 2>/dev/null)
done

if [[ "${#nginx_matches[@]}" -gt 0 ]]; then
  deduped_matches=()
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    deduped_matches+=("$line")
  done < <(printf '%s\n' "${nginx_matches[@]}" | awk '!seen[$0]++')
  nginx_matches=("${deduped_matches[@]}")
fi

echo "[INFO] domain=${DOMAIN}"
echo "[INFO] nginx_search_dirs=${SEARCH_DIRS_RAW}"
echo "[INFO] xray_search_dir=${XRAY_SEARCH_DIR}"
echo "[INFO] current_upstream=${CURRENT_UPSTREAM}"
echo "[INFO] target_upstream=${TARGET_UPSTREAM}"
echo "[INFO] nginx_match_count=${#nginx_matches[@]}"

for file in "${nginx_matches[@]}"; do
  match_count=$((match_count + 1))
  server_lines="$(extract_match_lines "server_name[[:space:]].*${DOMAIN}" "$file")"
  listen_lines="$(extract_match_lines "listen[[:space:]]+" "$file")"
  proxy_lines="$(extract_match_lines "proxy_pass[[:space:]]+" "$file")"
  echo "[NGINX] path=${file}"
  echo "[NGINX] server_name=${server_lines//$'\n'/ | }"
  echo "[NGINX] listen=${listen_lines//$'\n'/ | }"
  echo "[NGINX] proxy_pass=${proxy_lines//$'\n'/ | }"

  while IFS= read -r port; do
    [[ -n "$port" ]] || continue
    listen_ports+=("$port")
  done < <(extract_ports_from_lines "$listen_lines")

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    if [[ "$line" == *"${CURRENT_UPSTREAM}"* ]]; then
      patch_targets+=("${file}|${CURRENT_UPSTREAM}|${TARGET_UPSTREAM}")
    fi
  done < <(printf '%s\n' "$proxy_lines")
done

if [[ "${#listen_ports[@]}" -gt 0 ]]; then
  deduped_ports=()
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    deduped_ports+=("$line")
  done < <(printf '%s\n' "${listen_ports[@]}" | awk '!seen[$0]++')
  listen_ports=("${deduped_ports[@]}")
fi

xray_hits=0
if [[ -d "$XRAY_SEARCH_DIR" ]]; then
  xray_pattern_parts=("$DOMAIN")
  for port in "${listen_ports[@]}"; do
    xray_pattern_parts+=("$port")
  done
  xray_pattern="$(printf '%s|' "${xray_pattern_parts[@]}")"
  xray_pattern="${xray_pattern%|}"

  while IFS= read -r file; do
    [[ -n "$file" ]] || continue
    hit_lines="$(rg -n "${xray_pattern}" "$file" 2>/dev/null || true)"
    [[ -n "$hit_lines" ]] || continue
    xray_hits=$((xray_hits + 1))
    echo "[XRAY] path=${file}"
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      echo "[XRAY] hit=${line}"
    done < <(printf '%s\n' "$hit_lines")
  done < <(find "$XRAY_SEARCH_DIR" -maxdepth 1 -type f -name '*.json' -print 2>/dev/null | sort)
fi

topology="unknown"
if [[ "$xray_hits" -gt 0 && "${#patch_targets[@]}" -gt 1 ]]; then
  topology="xray-nginx-multi-upstream"
elif [[ "$xray_hits" -gt 0 && "${#patch_targets[@]}" -eq 1 ]]; then
  topology="xray-nginx-single-upstream"
elif [[ "${#nginx_matches[@]}" -gt 1 ]]; then
  topology="nginx-multi-upstream"
elif [[ "${#nginx_matches[@]}" -eq 1 ]]; then
  topology="single-nginx-origin"
fi

echo "[RECOMMEND] topology=${topology}"
echo "[RECOMMEND] patch_count=${#patch_targets[@]}"

if [[ "$xray_hits" -gt 0 ]]; then
  echo "[RECOMMEND] keep_unchanged=xray,cloudflare,dns"
fi

if [[ "${#patch_targets[@]}" -eq 0 ]]; then
  echo "[BLOCKED] 未发现可直接从 ${CURRENT_UPSTREAM} 切到 ${TARGET_UPSTREAM} 的 proxy_pass。"
  exit 2
fi

for target in "${patch_targets[@]}"; do
  echo "[RECOMMEND] patch_target=${target}"
done

if [[ "${#patch_targets[@]}" -gt 1 ]]; then
  patch_paths=()
  for target in "${patch_targets[@]}"; do
    patch_paths+=("${target%%|*}")
  done
  deduped_paths=()
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    deduped_paths+=("$line")
  done < <(printf '%s\n' "${patch_paths[@]}" | awk '!seen[$0]++')
  echo "[RECOMMEND] multi_upstream_dry_run=bash ./cutover_public_homepage_upstream_targets.sh ${DOMAIN} ${deduped_paths[*]}"
  echo "[RECOMMEND] multi_upstream_apply=DOCGEN_APPLY=1 bash ./cutover_public_homepage_upstream_targets.sh ${DOMAIN} ${deduped_paths[*]}"
fi

exit 0
