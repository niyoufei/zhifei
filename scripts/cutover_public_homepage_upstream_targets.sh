#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-${DOCGEN_DOMAIN:-}}"
shift || true
TARGET_CONFS=("$@")
APPLY="${DOCGEN_APPLY:-0}"
OS_NAME="${DOCGEN_OS_NAME:-$(uname -s)}"
CURRENT_UPSTREAM="${DOCGEN_CURRENT_UPSTREAM:-http://127.0.0.1:3000}"
TARGET_UPSTREAM="${DOCGEN_TARGET_UPSTREAM:-http://127.0.0.1:8501}"
BACKUP_DIR="${DOCGEN_CUTOVER_BACKUP_DIR:-}"

if [[ -z "$DOMAIN" || "${#TARGET_CONFS[@]}" -eq 0 ]]; then
  echo "[ERROR] usage: $0 <full-domain> <nginx-conf-path> [more-conf-paths...]" >&2
  echo "        example: $0 doc.niyoufei.com /etc/nginx/conf.d/doc.conf /etc/nginx/conf.d/alone.conf" >&2
  exit 1
fi

matches=0
files_with_matches=0

for file in "${TARGET_CONFS[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[ERROR] target conf not found: ${file}" >&2
    exit 1
  fi
done

echo "[INFO] domain=${DOMAIN}"
echo "[INFO] current_upstream=${CURRENT_UPSTREAM}"
echo "[INFO] target_upstream=${TARGET_UPSTREAM}"
echo "[INFO] target_conf_count=${#TARGET_CONFS[@]}"

for file in "${TARGET_CONFS[@]}"; do
  match_lines="$(grep -Fn "proxy_pass ${CURRENT_UPSTREAM};" "$file" || true)"
  match_count=0
  if [[ -n "$match_lines" ]]; then
    match_count="$(printf '%s\n' "$match_lines" | wc -l | tr -d '[:space:]')"
  fi
  echo "[TARGET] path=${file}"
  echo "[TARGET] match_count=${match_count}"
  if [[ -n "$match_lines" ]]; then
    files_with_matches=$((files_with_matches + 1))
    matches=$((matches + match_count))
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      echo "[TARGET] match=${line}"
    done < <(printf '%s\n' "$match_lines")
  fi
done

if [[ "$matches" -eq 0 ]]; then
  echo "[BLOCKED] 未在目标 conf 中找到 ${CURRENT_UPSTREAM} 的 proxy_pass。" >&2
  exit 2
fi

if [[ "$APPLY" != "1" ]]; then
  echo "[INFO] dry-run only; no files written."
  echo "[INFO] apply command:"
  echo "       DOCGEN_APPLY=1 DOCGEN_CURRENT_UPSTREAM=${CURRENT_UPSTREAM} DOCGEN_TARGET_UPSTREAM=${TARGET_UPSTREAM} bash ./cutover_public_homepage_upstream_targets.sh ${DOMAIN} ${TARGET_CONFS[*]}"
  exit 0
fi

if [[ "$OS_NAME" != "Linux" ]]; then
  echo "[ERROR] DOCGEN_APPLY=1 仅允许在 Linux 源站执行。" >&2
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "[ERROR] nginx not found" >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[ERROR] systemctl not found" >&2
  exit 1
fi

timestamp="$(date '+%Y%m%d-%H%M%S')"
backup_paths=()

for file in "${TARGET_CONFS[@]}"; do
  file_dir="$(dirname "$file")"
  if [[ -z "$BACKUP_DIR" ]]; then
    backup_base="${file_dir}/.docgen-cutover-backups"
  else
    backup_base="$BACKUP_DIR"
  fi
  mkdir -p "$backup_base"
  backup_path="${backup_base}/$(basename "$file").${timestamp}.bak"
  cp "$file" "$backup_path"
  backup_paths+=("$file|$backup_path")
  CURRENT_UPSTREAM="$CURRENT_UPSTREAM" TARGET_UPSTREAM="$TARGET_UPSTREAM" \
    perl -0pi -e 'BEGIN { $from = $ENV{CURRENT_UPSTREAM}; $to = $ENV{TARGET_UPSTREAM}; } s/\Q$from\E/$to/g' "$file"
done

if ! nginx -t; then
  echo "[ERROR] nginx -t failed after upstream rewrite." >&2
  for item in "${backup_paths[@]}"; do
    file="${item%%|*}"
    backup="${item#*|}"
    cp "$backup" "$file"
  done
  exit 1
fi

systemctl reload nginx

echo "[OK] upstream targets updated"
echo "domain=${DOMAIN}"
echo "files_with_matches=${files_with_matches}"
echo "match_count=${matches}"
for item in "${backup_paths[@]}"; do
  file="${item%%|*}"
  backup="${item#*|}"
  echo "backup_path=${backup}"
  echo "updated_path=${file}"
done
