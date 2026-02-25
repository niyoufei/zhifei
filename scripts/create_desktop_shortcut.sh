#!/usr/bin/env bash
# 在桌面创建启动快捷方式（与系统文件分离）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP="${HOME}/Desktop"
SHORTCUT="$DESKTOP/启动文档生成系统.command"

cat > "$SHORTCUT" << LAUNCHER
#!/usr/bin/env bash
# 文档生成系统 - 桌面快捷方式
cd "$ROOT"
echo "正在启动文档生成系统..."
chmod +x scripts/run_web_ui.sh 2>/dev/null || true
./scripts/run_web_ui.sh --background
echo ""
echo "按回车键关闭此窗口（服务已在后台运行）"
read -r
LAUNCHER
chmod +x "$SHORTCUT"

echo "[OK] 已在桌面创建快捷方式: $SHORTCUT"
echo "     可将项目内的 启动文档生成系统.command 删除"
