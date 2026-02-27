#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP="${HOME}/Desktop"
START_NAME="${1:-智飞文档生成}"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "osacompile not found (macOS required)" >&2
  exit 1
fi

START_APP="${DESKTOP}/${START_NAME}.app"
TMP_START="$(mktemp /tmp/zhifei_start_launcher.XXXXXX)"

cat > "$TMP_START" <<EOF
set rootPath to POSIX path of "${ROOT}/"
set cmd to "cd " & quoted form of rootPath & " && ./scripts/run_web_ui.sh"
tell application "Terminal"
  activate
  do script "/bin/bash -lc " & quoted form of cmd
end tell
EOF

rm -rf "$START_APP"
osacompile -o "$START_APP" "$TMP_START"

rm -f "$TMP_START"

echo "created: $START_APP"
