#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DESKTOP="${HOME}/Desktop"
START_NAME="${1:-施组专家系统}"
START_APP="${DESKTOP}/${START_NAME}.app"
ICON_SOURCE="${ZF_LAUNCHER_ICON:-${ROOT}/assets/launcher/shi-zu-expert-app-icon.png}"

for command_name in iconutil sips codesign osacompile; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "缺少 macOS 系统工具：${command_name}" >&2
    exit 1
  fi
done

if [ ! -f "$ICON_SOURCE" ]; then
  echo "启动图标不存在：${ICON_SOURCE}" >&2
  exit 1
fi

mkdir -p "$DESKTOP"
TMP_DIR="$(mktemp -d /tmp/zhifei_desktop_launcher.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

BUNDLE="${TMP_DIR}/${START_NAME}.app"
APPLESCRIPT_SOURCE="${TMP_DIR}/launcher.applescript"
ICONSET="${TMP_DIR}/applet.iconset"
mkdir -p "$ICONSET"

# Escape the fixed repository location for an AppleScript string literal.
APPLE_ROOT="${ROOT//\\/\\\\}"
APPLE_ROOT="${APPLE_ROOT//\"/\\\"}"
cat > "$APPLESCRIPT_SOURCE" <<APPLESCRIPT
on run
  set appName to "施组专家系统"
  set rootPath to "${APPLE_ROOT}"
  set startScript to rootPath & "/scripts/run_web_ui.sh"
  set logDirectory to rootPath & "/logs"
  set logPath to logDirectory & "/desktop_launcher.log"
  set launchCommand to "/bin/mkdir -p " & quoted form of logDirectory & " && " & quoted form of startScript & " --background >> " & quoted form of logPath & " 2>&1"
  try
    do shell script launchCommand
  on error errorMessage number errorNumber
    display alert appName message "系统未能启动。请把日志 " & logPath & " 交给我检查。\n\n错误代码：" & errorNumber as critical buttons {"确定"} default button "确定"
  end try
end run
APPLESCRIPT

# Compile a real macOS applet so double-clicking never opens a Terminal window.
osacompile -o "$BUNDLE" "$APPLESCRIPT_SOURCE"
CONTENTS="${BUNDLE}/Contents"
RESOURCES_DIR="${CONTENTS}/Resources"
PLIST="${CONTENTS}/Info.plist"

# Build all standard macOS icon sizes from the single generated source image.
sips -z 16 16 "$ICON_SOURCE" --out "${ICONSET}/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_SOURCE" --out "${ICONSET}/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_SOURCE" --out "${ICONSET}/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_SOURCE" --out "${ICONSET}/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_SOURCE" --out "${ICONSET}/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_SOURCE" --out "${ICONSET}/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_SOURCE" --out "${ICONSET}/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_SOURCE" --out "${ICONSET}/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_SOURCE" --out "${ICONSET}/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$ICON_SOURCE" --out "${ICONSET}/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET" -o "${RESOURCES_DIR}/AppIcon.icns"

plist_set_string() {
  local key="$1"
  local value="$2"
  if /usr/libexec/PlistBuddy -c "Print :${key}" "$PLIST" >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c "Set :${key} ${value}" "$PLIST"
  else
    /usr/libexec/PlistBuddy -c "Add :${key} string ${value}" "$PLIST"
  fi
}

plist_set_string CFBundleDisplayName 施组专家系统
plist_set_string CFBundleName 施组专家系统
plist_set_string CFBundleIdentifier com.zhifei.construction-expert.launcher
plist_set_string CFBundleShortVersionString 1.1
plist_set_string CFBundleVersion 2
plist_set_string CFBundleIconFile AppIcon.icns
if /usr/libexec/PlistBuddy -c "Print :CFBundleIconName" "$PLIST" >/dev/null 2>&1; then
  /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$PLIST"
fi
if /usr/libexec/PlistBuddy -c "Print :LSUIElement" "$PLIST" >/dev/null 2>&1; then
  /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST"
else
  /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST"
fi

plutil -lint "$PLIST" >/dev/null
codesign --force --deep --sign - "$BUNDLE" >/dev/null

if [ -e "$START_APP" ]; then
  BACKUP_APP="${DESKTOP}/${START_NAME}.backup-$(date '+%Y%m%d-%H%M%S').app"
  mv "$START_APP" "$BACKUP_APP"
  echo "原启动应用已备份：${BACKUP_APP}"
fi

mv "$BUNDLE" "$START_APP"
xattr -dr com.apple.quarantine "$START_APP" >/dev/null 2>&1 || true
touch "$START_APP"

LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if [ -x "$LSREGISTER" ]; then
  "$LSREGISTER" -f "$START_APP" >/dev/null 2>&1 || true
fi

echo "桌面应用已创建：${START_APP}"
echo "双击应用即可启动施组专家系统。"
