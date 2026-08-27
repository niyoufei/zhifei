#!/usr/bin/env bash
# 在桌面创建启动快捷方式（与系统文件分离）
set -euo pipefail

BOOTSTRAP_PYTHON="/usr/bin/python3"
OS_HOME="$("$BOOTSTRAP_PYTHON" -I -B -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
case "$OS_HOME" in /*) ;; *) exit 2 ;; esac
DESKTOP="${OS_HOME}/Desktop"
SHORTCUT="$DESKTOP/启动文档生成系统.command"

cat > "$SHORTCUT" <<'LAUNCHER'
#!/usr/bin/env bash
# 文档生成系统 - 桌面快捷方式
set -euo pipefail
echo "正在启动文档生成系统..."
BOOTSTRAP_PYTHON="/usr/bin/python3"
OS_HOME="$("$BOOTSTRAP_PYTHON" -I -B -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')"
case "$OS_HOME" in /*) ;; *) exit 2 ;; esac
TRUSTED_BOOTSTRAP="${OS_HOME}/Library/Application Support/com.zhifei.construction-expert/bootstrap/launch_current.py"
if [ ! -x "$BOOTSTRAP_PYTHON" ] || [ ! -f "$TRUSTED_BOOTSTRAP" ] || [ -L "$TRUSTED_BOOTSTRAP" ]; then
  echo "尚未构建可启动的最新不可变本地发布。" >&2
  exit 2
fi
exec "$BOOTSTRAP_PYTHON" -I -B "$TRUSTED_BOOTSTRAP"
LAUNCHER
chmod +x "$SHORTCUT"

echo "[OK] 已在桌面创建快捷方式: $SHORTCUT"
echo "     可将项目内的 启动文档生成系统.command 删除"
