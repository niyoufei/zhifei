#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP="${HOME}/Desktop"
START_NAME="${1:-智飞文档生成}"
STOP_NAME="${2:-停止智飞文档生成}"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "osacompile not found (macOS required)" >&2
  exit 1
fi

START_APP="${DESKTOP}/${START_NAME}.app"
STOP_APP="${DESKTOP}/${STOP_NAME}.app"

TMP_START="$(mktemp /tmp/zhifei_start_launcher.XXXXXX)"
TMP_STOP="$(mktemp /tmp/zhifei_stop_launcher.XXXXXX)"

cat > "$TMP_START" <<EOF
set rootPath to POSIX path of "${ROOT}/"
set cmd to "cd " & quoted form of rootPath & " && ./scripts/start_web_ui_background.sh"
do shell script "/bin/zsh -lc " & quoted form of cmd
EOF

cat > "$TMP_STOP" <<EOF
set rootPath to POSIX path of "${ROOT}/"
set cmd to "cd " & quoted form of rootPath & " && ./scripts/stop_web_ui_background.sh"
do shell script "/bin/zsh -lc " & quoted form of cmd
EOF

rm -rf "$START_APP" "$STOP_APP"
osacompile -o "$START_APP" "$TMP_START"
osacompile -o "$STOP_APP" "$TMP_STOP"

rm -f "$TMP_START" "$TMP_STOP"

echo "created: $START_APP"
echo "created: $STOP_APP"
