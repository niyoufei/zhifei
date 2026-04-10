from pathlib import Path
import os, re, json, ast, hashlib
from datetime import datetime

ROOT = Path.cwd()
OUT = ROOT / "_autodoctor"
OUT.mkdir(exist_ok=True)

IGNORE = {
    ".git",".hg",".svn",".idea",".vscode",".pytest_cache",".mypy_cache",
    "__pycache__","node_modules","dist","build_tmp",".venv","venv",".cache",
    "_smartcheck","_autodoctor"
}
TEXT_EXTS = {".py",".md",".txt",".json",".yaml",".yml",".toml",".ini",".cfg",".conf",".sh",".env",".sql",".js",".ts",".html",".css",".xml"}

def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)

def safe_read(p: Path) -> str:
    try:
        if p.suffix.lower() not in TEXT_EXTS and p.stat().st_size > 2_000_000:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def walk(root: Path):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in IGNORE]
        for fn in fns:
            yield Path(dp) / fn

files = list(walk(ROOT))
py_files = [p for p in files if p.suffix.lower() == ".py"]

def grep_files(pattern, paths):
    rx = re.compile(pattern, re.I | re.M)
    rows = []
    for p in paths:
        txt = safe_read(p)
        for i, line in enumerate(txt.splitlines(), 1):
            if rx.search(line):
                rows.append((rel(p), i, line.strip()))
    return rows

# 1) 启动与主链
app_page = ROOT / "app.py"
devserver = ROOT / "devserver.py"
backend_main = ROOT / "backend/app/main.py"
actions_router = ROOT / "backend/app/routers/actions_bridge.py"
zhifei_router = ROOT / "backend/app/routers/zhifei_autoplan.py"

main_chain = {
    "app_page_exists": app_page.exists(),
    "devserver_exists": devserver.exists(),
    "backend_main_exists": backend_main.exists(),
    "actions_router_exists": actions_router.exists(),
    "zhifei_router_exists": zhifei_router.exists(),
    "devserver_target": None,
    "main_routers": [],
}

if devserver.exists():
    txt = safe_read(devserver)
    m = re.search(r'uvicorn\.run\(\s*[\'"]([^\'"]+)[\'"]', txt)
    if m:
        main_chain["devserver_target"] = m.group(1)

if backend_main.exists():
    txt = safe_read(backend_main)
    main_chain["main_routers"] = re.findall(r'include_router\(([^)]+)\)', txt)

# 2) 路由扫描
route_info = []
route_pat = re.compile(r'@router\.(get|post|put|delete|patch)\(\s*[rubfRUBF]*[\'"]([^\'"]+)')
prefix_pat = re.compile(r'APIRouter\s*\((?:(?!\)).)*?prefix\s*=\s*[\'"]([^\'"]+)[\'"]', re.S)
for p in sorted((ROOT / "backend/app/routers").glob("*.py")):
    txt = safe_read(p)
    eps = route_pat.findall(txt)
    prefix = ""
    mm = prefix_pat.search(txt)
    if mm:
        prefix = mm.group(1)
    route_info.append({
        "file": rel(p),
        "prefix": prefix,
        "endpoint_count": len(eps),
        "sample": [f"{m.upper()} {u}" for m, u in eps[:12]]
    })

# 3) 知识图谱链
kg_files = [
    ROOT / "backend/zhifei_autoplan/kg_store.py",
    ROOT / "backend/zhifei_autoplan/kg_runtime.py",
    ROOT / "backend/data/kg/kg_index.json",
    ROOT / "backend/data/kg/active_kg.json",
]
kg = {
    "online_routes": [],
    "kg_index_exists": kg_files[2].exists(),
    "active_kg_exists": kg_files[3].exists(),
    "kg_index_nonempty": False,
    "active_kg_nonempty": False,
}
if zhifei_router.exists():
    txt = safe_read(zhifei_router)
    for line in txt.splitlines():
        if "/kg/" in line or "save_kg_bytes" in line or "list_kg" in line or "set_active_kg" in line or "get_active_kg" in line or "search_kg" in line:
            kg["online_routes"].append(line.strip())

for kf, key in [(kg_files[2], "kg_index_nonempty"), (kg_files[3], "active_kg_nonempty")]:
    if kf.exists():
        s = safe_read(kf).strip()
        kg[key] = bool(s)

# 4) 审计与导出
audit_dir = ROOT / "backend/data/audit"
build_dir = ROOT / "build"
audit = {
    "audit_dir_exists": audit_dir.exists(),
    "audit_files": [rel(p) for p in sorted(audit_dir.glob("*"))] if audit_dir.exists() else [],
    "build_exists": build_dir.exists(),
    "build_docx": [rel(p) for p in sorted(build_dir.glob("*.docx"))[:20]] if build_dir.exists() else [],
    "build_json": [rel(p) for p in sorted(build_dir.glob("*.json"))[:20]] if build_dir.exists() else [],
    "audit_export_dirs": [rel(p) for p in sorted(build_dir.glob("_audit_exports/*"))[:20]] if build_dir.exists() else [],
}

# 5) 旁路链
assist = ROOT / "routers/assist_codex.py"
claw = ROOT / "clawdbot/run.sh"
refs_side = grep_files(r'assist_codex|clawdbot|supervisor_prompt|prompt_path', py_files + [p for p in files if p.suffix.lower()==".sh"])
side = {
    "assist_codex_exists": assist.exists(),
    "clawdbot_run_exists": claw.exists(),
    "refs": refs_side[:50],
}

# 6) 配置
cfg_files = []
for pat in ["requirements.txt","pyproject.toml",".env",".env.local","backend/data/autoplan/config.json","kg_config.json"]:
    p = ROOT / pat
    if p.exists():
        cfg_files.append(rel(p))

autoplan_cfg = {}
cfgp = ROOT / "backend/data/autoplan/config.json"
if cfgp.exists():
    try:
        autoplan_cfg = json.loads(safe_read(cfgp) or "{}")
    except Exception:
        autoplan_cfg = {"_parse_error": True}

# 7) 静态问题识别
issues = []

if main_chain["devserver_target"] != "backend.app.main:app":
    issues.append({"level":"high","title":"启动目标异常","detail":f"devserver.py 当前目标为 {main_chain['devserver_target']}"})
else:
    issues.append({"level":"info","title":"FastAPI 启动目标已锁定","detail":"devserver.py 作为历史兼容壳，当前仍指向 backend.app.main:app"})

if "actions_bridge_router" not in main_chain["main_routers"]:
    issues.append({"level":"high","title":"V2 页面主路由未确认挂载","detail":"backend/app/main.py 未识别到 actions_bridge_router include_router"})
else:
    issues.append({"level":"info","title":"V2 页面主路由已挂载","detail":"backend/app/main.py 已识别 actions_bridge_router"})

if "zhifei_autoplan_router" not in main_chain["main_routers"]:
    issues.append({"level":"medium","title":"兼容 API 路由未确认挂载","detail":"backend/app/main.py 未识别到 zhifei_autoplan_router include_router"})
else:
    issues.append({"level":"info","title":"兼容 API 路由已挂载","detail":"backend/app/main.py 已识别 zhifei_autoplan_router"})

if not kg["kg_index_exists"] and not kg["active_kg_exists"]:
    issues.append({"level":"medium","title":"在线知识图谱当前未初始化","detail":"backend/data/kg 下未见 kg_index.json 与 active_kg.json；更像未上传/未激活，而非代码缺链"})
elif kg["kg_index_exists"] and not kg["kg_index_nonempty"]:
    issues.append({"level":"medium","title":"kg_index.json 为空","detail":"存在文件但无内容，需判断是初始化态还是异常"})
elif kg["active_kg_exists"] and not kg["active_kg_nonempty"]:
    issues.append({"level":"medium","title":"active_kg.json 为空","detail":"存在文件但无内容，检索可能返回 no_active_kg"})

if audit["audit_dir_exists"] and audit["audit_files"]:
    issues.append({"level":"info","title":"审计源存在","detail":"backend/data/audit 下已有 ingest/export jsonl"})
else:
    issues.append({"level":"high","title":"审计源缺失","detail":"backend/data/audit 未发现有效审计文件"})

if side["assist_codex_exists"]:
    refs = [r for r in side["refs"] if "assist_codex" in r[0] or "assist_codex" in r[2]]
    if not refs:
        issues.append({"level":"low","title":"assist_codex 旁路未接主链","detail":"文件存在，但当前未发现主入口引用"})
if side["clawdbot_run_exists"]:
    refs = [r for r in side["refs"] if "clawdbot" in r[0] or "clawdbot" in r[2]]
    if len(refs) <= 1:
        issues.append({"level":"low","title":"clawdbot 为独立旁路脚本","detail":"当前未见接入 FastAPI 主链"})

# 8) 自动结论
conclusions = [
    "V2 页面主链：app.py -> backend/app/main.py -> backend/app/routers/actions_bridge.py -> backend/zhifei_autoplan/*",
    "兼容 API 链：backend/app/main.py -> backend/app/routers/zhifei_autoplan.py -> backend/zhifei_autoplan/*",
    "devserver.py 为历史兼容启动壳，不再视为当前页面主入口",
    "导出主落盘：build/",
    "审计源：backend/data/audit/*.jsonl",
    "知识图谱在线链：/kg/upload /kg/list /kg/active /kg/activate /kg/search -> backend/data/kg",
    "v2 / graph_dispatcher / 外部“知识图谱”目录目前未见挂入主入口在线链",
    "routers/assist_codex.py、clawdbot/run.sh 当前更像旁路能力"
]

# 9) 输出
report = {
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "root": str(ROOT),
    "main_chain": main_chain,
    "routes": route_info,
    "kg": kg,
    "audit": audit,
    "side": side,
    "config_files": cfg_files,
    "autoplan_config": autoplan_cfg,
    "issues": issues,
    "conclusions": conclusions,
}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

md = []
md.append("# 文档生成系统 自动体检总报告")
md.append("")
md.append(f"- 时间：{report['generated_at']}")
md.append(f"- 根目录：`{ROOT}`")
md.append("")
md.append("## 一、主链判定")
md.append(f"- app.py 存在：{main_chain['app_page_exists']}")
md.append(f"- devserver.py 存在：{main_chain['devserver_exists']}")
md.append(f"- backend/app/main.py 存在：{main_chain['backend_main_exists']}")
md.append(f"- actions_bridge 主路由存在：{main_chain['actions_router_exists']}")
md.append(f"- zhiFei 主路由存在：{main_chain['zhifei_router_exists']}")
md.append(f"- devserver 历史壳启动目标：`{main_chain['devserver_target']}`")
md.append(f"- main.py 挂载路由：`{', '.join(main_chain['main_routers'])}`")
md.append("")
md.append("## 二、核心路由")
for r in route_info:
    md.append(f"- `{r['file']}` | prefix=`{r['prefix']}` | endpoint={r['endpoint_count']}")
md.append("")
md.append("## 三、知识图谱")
md.append(f"- 在线接口链已存在：{bool(kg['online_routes'])}")
md.append(f"- kg_index.json 存在：{kg['kg_index_exists']} / 非空：{kg['kg_index_nonempty']}")
md.append(f"- active_kg.json 存在：{kg['active_kg_exists']} / 非空：{kg['active_kg_nonempty']}")
md.append("")
md.append("## 四、审计与导出")
md.append(f"- 审计目录存在：{audit['audit_dir_exists']}")
md.append(f"- 审计文件：{', '.join(audit['audit_files']) if audit['audit_files'] else '无'}")
md.append(f"- build 目录存在：{audit['build_exists']}")
md.append(f"- build 下 docx：{', '.join(audit['build_docx']) if audit['build_docx'] else '无'}")
md.append("")
md.append("## 五、旁路链")
md.append(f"- assist_codex.py 存在：{side['assist_codex_exists']}")
md.append(f"- clawdbot/run.sh 存在：{side['clawdbot_run_exists']}")
md.append("")
md.append("## 六、配置")
for f in cfg_files:
    md.append(f"- `{f}`")
md.append("")
md.append("## 七、自动识别问题")
for it in issues:
    md.append(f"- [{it['level']}] {it['title']}：{it['detail']}")
md.append("")
md.append("## 八、结论")
for c in conclusions:
    md.append(f"- {c}")
md.append("")
md.append("## 九、下一步建议")
md.append("- 先核对 V2 页面主链：app.py -> /actions/* -> backend/zhifei_autoplan/*")
md.append("- 再核对兼容 API / KG / 审计链：/autoplan/* 与 backend/data/kg/、backend/data/audit/")
md.append("- 如需补规则，优先补主链相关子目录 AGENTS.md，再补旁路目录边界说明")
(OUT / "summary.md").write_text("\n".join(md), encoding="utf-8")

print("[OK] 已生成：")
print(OUT / "summary.md")
print(OUT / "report.json")
print("")
print("[主链]")
print("app.py -> backend.app.main:app -> /actions/*")
print("devserver.py (legacy shell) ->", main_chain["devserver_target"])
print("main routers:", ", ".join(main_chain["main_routers"]))
print("")
print("[关键判断]")
for c in conclusions:
    print("-", c)
print("")
print("[问题]")
for it in issues:
    print(f"- [{it['level']}] {it['title']}：{it['detail']}")
