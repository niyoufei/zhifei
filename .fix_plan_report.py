from pathlib import Path
from datetime import datetime
import json

ROOT = Path.cwd()
OUT = ROOT / "_autodoctor"
OUT.mkdir(exist_ok=True)

report_json = OUT / "report.json"
data = {}
if report_json.exists():
    try:
        data = json.loads(report_json.read_text(encoding="utf-8"))
    except Exception:
        data = {}

main_chain = data.get("main_chain", {})
routes = data.get("routes", [])
kg = data.get("kg", {})
audit = data.get("audit", {})
side = data.get("side", {})

must_fix = []
should_fix = []
hold = []
archive = []

# 必须修
if not (ROOT / "AGENTS.md").exists():
    must_fix.append(["项目根规则缺失", "高", "根目录缺少 AGENTS.md", "已补齐后可关闭"])
if not (ROOT / "知识图谱/AGENTS.md").exists():
    must_fix.append(["知识图谱 规则缺失", "中", "中文子目录缺少 AGENTS.md", "已补齐后可关闭"])

# 建议修
if main_chain.get("devserver_target") == "backend.app.main:app":
    should_fix.append(["FastAPI 启动目标已统一", "低", "历史兼容壳 devserver 已指向 backend.app.main:app", "保持现状"])
else:
    should_fix.append(["FastAPI 启动目标待统一", "高", f"devserver 目标为 {main_chain.get('devserver_target')}", "统一到 backend.app.main:app"])

if kg.get("kg_index_exists") and kg.get("active_kg_exists"):
    should_fix.append(["KG 已初始化但仍需业务闭环验证", "中", "状态文件存在，但不代表已上传有效图谱", "后续走 /kg/upload 与 /kg/activate 验证"])
else:
    should_fix.append(["KG 可能尚未初始化", "中", "backend/data/kg 状态文件缺失或异常；按未上传/未激活优先判断", "如需启用在线 KG，走 /kg/upload 与 /kg/activate 验证"])

if audit.get("audit_dir_exists"):
    should_fix.append(["审计源已落盘", "低", "backend/data/audit 下已有 jsonl", "后续核对字段完整性"])
else:
    should_fix.append(["审计源待核查", "中", "未发现有效审计源", "补查 ingest/export 落盘逻辑"])

# 暂不动
hold.extend([
    ["v2 图谱处理链", "旁路/实验链，当前未接主入口", "backend/zhifei_autoplan/v2/"],
    ["graph_dispatcher", "旁路/实验链，当前未接主入口", "backend/zhifei_autoplan/graph_dispatcher.py"],
    ["assist_codex", "旁路能力，当前未接主入口", "routers/assist_codex.py"],
    ["clawdbot", "独立脚本链，当前未接 FastAPI 主链", "clawdbot/"],
])

# 可归档旁路目录
archive.extend([
    ["assist_codex", "如长期不用，可单独归档到 experiments/ 或 archive/"],
    ["clawdbot", "如仅做独立代理实验，可单独归档，不混入主服务判断"],
    ["v2", "如近期不启用，可做实验链标记与目录说明，不直接删除"],
])

md = []
md.append("# 项目结构与修正建议总表")
md.append("")
md.append(f"- 生成时间：{datetime.now().isoformat(timespec='seconds')}")
md.append(f"- 项目根目录：`{ROOT}`")
md.append("")
md.append("## 一、当前主链结论")
md.append(f"- V2 页面主链：`app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*`")
md.append(f"- 兼容 API 链：`backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*`")
md.append(f"- 历史兼容壳目标：`{main_chain.get('devserver_target')}`")
md.append("")
md.append("## 二、必须修")
if must_fix:
    for i, row in enumerate(must_fix, 1):
        md.append(f"{i}. **{row[0]}**")
        md.append(f"   - 优先级：{row[1]}")
        md.append(f"   - 现状：{row[2]}")
        md.append(f"   - 建议动作：{row[3]}")
else:
    md.append("1. 当前未发现新的必须修项。")
md.append("")
md.append("## 三、建议修")
for i, row in enumerate(should_fix, 1):
    md.append(f"{i}. **{row[0]}**")
    md.append(f"   - 优先级：{row[1]}")
    md.append(f"   - 现状：{row[2]}")
    md.append(f"   - 建议动作：{row[3]}")
md.append("")
md.append("## 四、暂不动")
for i, row in enumerate(hold, 1):
    md.append(f"{i}. **{row[0]}**")
    md.append(f"   - 原因：{row[1]}")
    md.append(f"   - 路径：`{row[2]}`")
md.append("")
md.append("## 五、可归档旁路目录")
for i, row in enumerate(archive, 1):
    md.append(f"{i}. **{row[0]}**")
    md.append(f"   - 建议：{row[1]}")
md.append("")
md.append("## 六、推荐修正顺序")
md.append("1. 保持 V2 页面主链稳定，不再回退到旧 `/autoplan` 主链口径")
md.append("2. 用真实业务文件走一次 `/actions` 主链 smoke 闭环")
md.append("3. 如需启用在线 KG，再走一次 `/kg/upload -> /kg/activate -> /kg/search` 闭环验证")
md.append("4. 核对审计 jsonl 字段结构与导出文件命名规则")
md.append("5. 为旁路目录追加说明文件，避免后续误判")
md.append("6. 如需要，再决定是否对 v2 / clawdbot / assist_codex 做归档")
md.append("")
md.append("## 七、当前建议")
md.append("- 当前不建议继续大范围改代码。")
md.append("- 当前最有价值的动作，是先做一次 **/actions 主链 smoke**；如需启用 KG，再补 **/kg/* 在线闭环验证**。")

out = OUT / "修正建议总表.md"
out.write_text("\n".join(md), encoding="utf-8")

print("[OK] 已生成：")
print(out)
print("")
print("[摘要]")
print("必须修：", len(must_fix))
print("建议修：", len(should_fix))
print("暂不动：", len(hold))
print("可归档：", len(archive))
