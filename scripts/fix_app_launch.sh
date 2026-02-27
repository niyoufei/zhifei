#!/usr/bin/env bash
# 修复 .app 无法启动（解除 macOS 隔离、确保可执行权限）
# 用法：./scripts/fix_app_launch.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP="$ROOT/文档生成系统.app"

if [ ! -d "$APP" ]; then
  echo "[FAIL] 未找到 文档生成系统.app"
  exit 1
fi

# 移除隔离属性（解决「已损坏」或禁止符号）
xattr -cr "$APP" 2>/dev/null || true

# 确保可执行
chmod +x "$APP/Contents/MacOS/launch" 2>/dev/null || true

echo "[OK] 已修复，请再次双击 文档生成系统.app 启动"
echo ""
echo "若仍无法打开："
echo "  1. 右键 文档生成系统.app → 打开（首次需手动允许）"
echo "  2. 确保 .app 在项目文件夹内，不要单独拖到桌面"
echo ""
echo "若浏览器显示「连接被拒绝」："
echo "  请先在终端运行: cd 项目目录 && ./scripts/run_web_ui.sh"
echo "  检查 Python 环境是否正常（如架构兼容问题）"
