#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.."; pwd)"
cd "$ROOT"

echo "=== Traceable DocSys · 每日运行（增强版） ==="

# 1) 准备/激活虚拟环境
[ -d venv ] || { echo "[ENV] 创建虚拟环境 venv"; python3 -m venv venv; }
source venv/bin/activate
echo "[ENV] 已激活虚拟环境"

# 2) 依赖
[ -f requirements.txt ] && pip install -r requirements.txt >/dev/null || true
pip install -q openpyxl python-docx reportlab >/dev/null || true
echo "[PKG] 依赖就绪"

# 3) 生成/刷新文档（存在就跑）
if [ -f backend/audit/export_final_summary.py ]; then
  echo "[RUN] 生成 final_summary.xlsx"
  python3 backend/audit/export_final_summary.py || true
fi

# 4) 归档当日批次并校验
STAMP=$(date +"%Y%m%d_%H%M%S")
OUT="deliveries/${STAMP}"
mkdir -p "$OUT"

# 收拢成果（存在才复制）
ARTS=( \
  backend/audit/final_summary.xlsx \
  M32_Final_Archive_Report.docx \
  M32_manifest.json \
  M32_checksums.txt \
  M33_README.txt \
  README_FINGERPRINT.txt \
  M35_Project_Cover_README.pdf \
  M36_Final_Seal_Statement.pdf \
  Deliveries_Index.txt \
)
for f in "${ARTS[@]}"; do
  [ -f "$f" ] && cp -v "$f" "$OUT" || true
done

# 校验指纹（仅在目录非空时计算）
if [ "$(find "$OUT" -type f | wc -l | tr -d " ")" -gt 0 ]; then
  ( cd "$OUT" && shasum -a 256 * > FINAL_SHA256.txt )
else
  echo "NO_ARTIFACTS" > "$OUT/FINAL_SHA256.txt"
fi

# 5) 产出当日 ZIP 包
( cd deliveries && zip -r "TraceableDocSys_daily_${STAMP}.zip" "${STAMP}" >/dev/null )

echo "=== ✅ 每日运行完成 ==="
echo "批次目录：$OUT"
echo "当日ZIP ：deliveries/TraceableDocSys_daily_${STAMP}.zip"
echo "指纹清单：$OUT/FINAL_SHA256.txt"
echo "退出环境请输入：deactivate"
