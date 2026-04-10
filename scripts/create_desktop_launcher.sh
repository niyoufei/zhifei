#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP="${HOME}/Desktop"
APP_NAME="${1:-施组专家系统}"
BUILD_SCRIPT="${ROOT}/scripts/build_quick_launch_app.sh"
RENDER_SCRIPT="${ROOT}/scripts/render_desktop_launcher_icon.py"
PREVIEW_DIR="${ROOT}/build/desktop_launcher"
TMP_DIR="$(mktemp -d /tmp/docgen_desktop_launcher.XXXXXX)"
ICONSET_DIR="${TMP_DIR}/AppIcon.iconset"
ICON_ICNS="${TMP_DIR}/AppIcon.icns"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found" >&2
  exit 1
fi

if ! command -v iconutil >/dev/null 2>&1; then
  echo "[ERROR] iconutil not found (macOS required)" >&2
  exit 1
fi

if [[ ! -x "$BUILD_SCRIPT" ]]; then
  echo "[ERROR] build script not executable: $BUILD_SCRIPT" >&2
  exit 1
fi

mkdir -p "$PREVIEW_DIR"

python3 "$RENDER_SCRIPT" \
  --iconset-dir "$ICONSET_DIR" \
  --preview-png "$PREVIEW_DIR/${APP_NAME}.png"

iconutil -c icns "$ICONSET_DIR" -o "$ICON_ICNS"

ICON_ICNS_SOURCE="$ICON_ICNS" "$BUILD_SCRIPT" "$APP_NAME" "$DESKTOP"

echo "[OK] 已在桌面生成启动入口: ${DESKTOP}/${APP_NAME}.app"
echo "[OK] 图标预览已输出: ${PREVIEW_DIR}/${APP_NAME}.png"
