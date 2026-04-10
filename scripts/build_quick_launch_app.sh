#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="${1:-文档生成系统}"
OUT_DIR="${2:-$ROOT/build/quick_launch_apps}"
OUT_APP="${OUT_DIR}/${APP_NAME}.app"
CONTENTS_DIR="${OUT_APP}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"
EXECUTABLE_NAME="launcher"
APP_URL="${APP_URL:-${ZF_PUBLIC_WEB_URL:-http://127.0.0.1:8501}}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-http://127.0.0.1:8010/health}"
WAIT_SECONDS="${WAIT_SECONDS:-45}"
BUNDLE_ID="${BUNDLE_ID:-com.zhifei.docgen.quicklaunch}"
ICON_NAME="applet.icns"
ICON_ICNS_SOURCE="${ICON_ICNS_SOURCE:-}"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "[ERROR] osacompile not found (macOS required)" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
PATH_PREFIX="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT_ESCAPED="${ROOT//\\/\\\\}"
ROOT_ESCAPED="${ROOT_ESCAPED//\"/\\\"}"
TMP_DIR="$(mktemp -d -t docgen_quick_launch)"
TMP_STUB_SCRIPT="${TMP_DIR}/stub.applescript"
TMP_STUB_APP="${TMP_DIR}/stub.app"

rm -rf "$OUT_APP"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

if [[ -n "$ICON_ICNS_SOURCE" && -f "$ICON_ICNS_SOURCE" ]]; then
  cp "$ICON_ICNS_SOURCE" "${RESOURCES_DIR}/${ICON_NAME}"
else
  cat > "$TMP_STUB_SCRIPT" <<'EOF'
set x to 1
EOF
  osacompile -o "$TMP_STUB_APP" "$TMP_STUB_SCRIPT" >/dev/null
  if [[ -f "${TMP_STUB_APP}/Contents/Resources/${ICON_NAME}" ]]; then
    cp "${TMP_STUB_APP}/Contents/Resources/${ICON_NAME}" "${RESOURCES_DIR}/${ICON_NAME}"
  fi
fi

cat > "${MACOS_DIR}/${EXECUTABLE_NAME}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT_ESCAPED}"
APP_NAME="${APP_NAME}"
APP_URL="${APP_URL}"
HEALTH_URL="${HEALTH_URL}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL}"
WAIT_SECONDS="${WAIT_SECONDS}"
LOG_FILE="/tmp/docgen_quick_launch.log"
TERMINAL_WRAPPER_PREFIX="/tmp/docgen_quick_launch"
FAIL_DIALOG_TIMEOUT_SECONDS="\${DOCGEN_QUICK_LAUNCH_DIALOG_TIMEOUT_SECONDS:-120}"
export PATH="${PATH_PREFIX}"

cd "\$ROOT"

health_ok() {
  /usr/bin/curl -fsS --max-time 2 "\$BACKEND_HEALTH_URL" >/dev/null 2>&1 || return 1
  /usr/bin/curl -fsS --max-time 2 "\$HEALTH_URL" >/dev/null 2>&1 || return 1
}

wait_ready() {
  local limit="\$1"
  for ((i=1; i<=limit; i++)); do
    if health_ok; then
      return 0
    fi
    sleep 1
  done
  return 1
}

notify_user() {
  local message="\$1"
  local title="\${2:-\$APP_NAME}"
  local subtitle="\${3:-}"
  if [ -n "\$subtitle" ]; then
    /usr/bin/osascript - "\$message" "\$title" "\$subtitle" <<'OSA' >/dev/null 2>&1 || true
on run argv
  display notification (item 1 of argv) with title (item 2 of argv) subtitle (item 3 of argv)
end run
OSA
    return 0
  fi
  /usr/bin/osascript - "\$message" "\$title" <<'OSA' >/dev/null 2>&1 || true
on run argv
  display notification (item 1 of argv) with title (item 2 of argv)
end run
OSA
}

show_failure_dialog() {
  local message="\$1"
  local logs_dir="\$ROOT/logs"
  /usr/bin/osascript - "\$message" "\$APP_NAME" "\$logs_dir" "\$FAIL_DIALOG_TIMEOUT_SECONDS" <<'OSA' >/dev/null 2>&1 || true
on run argv
  set msgText to item 1 of argv
  set titleText to item 2 of argv
  set logsPath to item 3 of argv
  set timeoutSeconds to (item 4 of argv) as integer
  set dlgResult to display dialog msgText with title titleText buttons {"关闭", "打开日志"} default button "打开日志" giving up after timeoutSeconds
  if (gave up of dlgResult) is false and (button returned of dlgResult) is "打开日志" then
    do shell script "/usr/bin/open " & quoted form of logsPath
  end if
end run
OSA
}

write_terminal_wrapper() {
  local action="\$1"
  local wrapper="\${TERMINAL_WRAPPER_PREFIX}_\${action}.sh"
  cat > "\$wrapper" <<WRAP
#!/usr/bin/env bash
set -euo pipefail
trap 'rm -f "\$wrapper"' EXIT
cd "\$ROOT"
if [ "\$action" = "start" ]; then
  ZF_DISABLE_PREWARM="\${ZF_DISABLE_PREWARM:-1}" ZF_SKIP_OPEN=1 /bin/bash "\$ROOT/scripts/start_web_ui_background.sh" >> "\$LOG_FILE" 2>&1
else
  /bin/bash "\$ROOT/scripts/stop_web_ui_background.sh" >> "\$LOG_FILE" 2>&1
fi
WRAP
  chmod +x "\$wrapper"
  printf "%s" "\$wrapper"
}

run_via_osascript() {
  local action="\$1"
  local shell_cmd=""
  if [ "\$action" = "start" ]; then
    printf -v shell_cmd 'cd %q && ZF_DISABLE_PREWARM=%q ZF_SKIP_OPEN=1 /bin/bash %q >> %q 2>&1' \
      "\$ROOT" "\${ZF_DISABLE_PREWARM:-1}" "\$ROOT/scripts/start_web_ui_background.sh" "\$LOG_FILE"
  else
    printf -v shell_cmd 'cd %q && /bin/bash %q >> %q 2>&1' \
      "\$ROOT" "\$ROOT/scripts/stop_web_ui_background.sh" "\$LOG_FILE"
  fi
  /usr/bin/osascript - "\$shell_cmd" <<'OSA' >/dev/null 2>&1
on run argv
  do shell script (item 1 of argv)
end run
OSA
}

terminal_visible_state() {
  /usr/bin/osascript <<'OSA' 2>/dev/null || true
tell application "System Events"
  if exists process "Terminal" then
    if visible of process "Terminal" then
      return "true"
    else
      return "false"
    end if
  end if
end tell
return "NO_PROCESS"
OSA
}

rehide_terminal_if_needed() {
  local before="\${1:-NO_PROCESS}"
  if [ "\$before" = "true" ]; then
    return 0
  fi
  /usr/bin/osascript <<'OSA' >/dev/null 2>&1 &
repeat 20 times
  tell application "System Events"
    if exists process "Terminal" then
      try
        set visible of process "Terminal" to false
      end try
      exit repeat
    end if
  end tell
  delay 0.2
end repeat
OSA
}

run_in_terminal() {
  local action="\$1"
  local wrapper
  local terminal_before="NO_PROCESS"
  terminal_before="\$(terminal_visible_state)"
  wrapper="\$(write_terminal_wrapper "\$action")"
  /usr/bin/open -g -j -a Terminal "\$wrapper" >/dev/null 2>&1
  rehide_terminal_if_needed "\$terminal_before"
}

start_once() {
  if ! run_via_osascript start; then
    # Fallback for macOS GUI environments that still block direct repo-script execution.
    run_in_terminal start
  fi
}

stop_once() {
  if ! run_via_osascript stop; then
    run_in_terminal stop
  fi
}

{
  echo "[\$(date '+%F %T')] quick launch start"
} >> "\$LOG_FILE" 2>&1

ready=false
startup_attempted=false

if ! health_ok; then
  startup_attempted=true
  notify_user "正在启动，首次启动通常需要 20 到 40 秒。" "\$APP_NAME"
  start_once || true
  if wait_ready "\$WAIT_SECONDS"; then
    ready=true
  else
    {
      echo "[\$(date '+%F %T')] quick launch self-heal"
    } >> "\$LOG_FILE" 2>&1 || true
    notify_user "首次启动较慢，正在自动重试。" "\$APP_NAME"
    stop_once
    start_once || true
    if wait_ready "\$WAIT_SECONDS"; then
      ready=true
    fi
  fi
else
  ready=true
fi

if [ "\${DOCGEN_QUICK_LAUNCH_FORCE_FAIL:-0}" = "1" ]; then
  ready=false
fi

if [ "\$ready" = true ]; then
  {
    echo "[\$(date '+%F %T')] quick launch ready"
  } >> "\$LOG_FILE" 2>&1 || true
  if [ "\$startup_attempted" = true ]; then
    notify_user "系统已就绪，正在打开网页。" "\$APP_NAME"
  fi
  if [[ "\${DOCGEN_QUICK_LAUNCH_NO_OPEN:-0}" != "1" ]]; then
    /usr/bin/open "\$APP_URL"
  fi
else
  {
    echo "[\$(date '+%F %T')] quick launch failed_not_ready"
  } >> "\$LOG_FILE" 2>&1 || true
  notify_user "启动失败，请稍后重试；如仍失败，可手动运行启动脚本。" "\$APP_NAME"
  show_failure_dialog "施组专家系统未能完成启动。\n\n可稍后重试；如仍失败，请打开日志目录查看：\n\$ROOT/logs\n\n快速启动日志：\n\$LOG_FILE"
fi
EOF

cat > "${CONTENTS_DIR}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>zh_CN</string>
  <key>CFBundleDisplayName</key>
  <string>${APP_NAME}</string>
  <key>CFBundleExecutable</key>
  <string>${EXECUTABLE_NAME}</string>
  <key>CFBundleIconFile</key>
  <string>${ICON_NAME}</string>
  <key>CFBundleIdentifier</key>
  <string>${BUNDLE_ID}</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>${APP_NAME}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF

printf 'APPL????' > "${CONTENTS_DIR}/PkgInfo"
chmod +x "${MACOS_DIR}/${EXECUTABLE_NAME}"
rm -rf "$TMP_DIR"

echo "[OK] created: $OUT_APP"
