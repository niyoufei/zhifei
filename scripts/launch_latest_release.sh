#!/bin/bash
# Fixed production entrypoint: the Python launcher performs all current.json,
# current symlink, release-manifest, runtime and live identity checks.
set -euo pipefail

BOOTSTRAP_PYTHON="/usr/bin/python3"
OS_HOME="$("$BOOTSTRAP_PYTHON" -I -B -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
case "$OS_HOME" in /*) ;; *) exit 2 ;; esac
TRUSTED_BOOTSTRAP="${OS_HOME}/Library/Application Support/com.zhifei.construction-expert/bootstrap/launch_current.py"

if [ ! -x "$BOOTSTRAP_PYTHON" ]; then
  printf '%s\n' \
    '{"ok":false,"error_code":"LAUNCH_BOOTSTRAP_PYTHON_MISSING","message":"系统缺少可信的本地启动解释器"}' \
    >&2
  exit 2
fi
if [ ! -f "$TRUSTED_BOOTSTRAP" ] || [ -L "$TRUSTED_BOOTSTRAP" ]; then
  printf '%s\n' \
    '{"ok":false,"error_code":"LAUNCH_BOOTSTRAP_MISSING","message":"固定外置可信启动入口不可用"}' \
    >&2
  exit 2
fi

exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP" "$@"
