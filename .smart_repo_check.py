from pathlib import Path
import os, re, json, ast
from datetime import datetime

ROOT = Path.cwd()
OUT = ROOT / "_smartcheck"
OUT.mkdir(exist_ok=True)

IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".pytest_cache", ".mypy_cache",
    "__pycache__", "node_modules", "dist", "build", "target", ".venv", "venv",
    ".next", ".turbo", ".cache", "_smartcheck"
}
TEXT_EXTS = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".conf", ".env", ".sh", ".sql", ".js", ".ts", ".html", ".css", ".xml"
}
MAX_BYTES = 1500000
NOISE_PATH_PARTS = {
    "_autodoctor",
    "_smartcheck",
    "_untracked_backup_20260102_170109",
    "build_tmp",
    "exports",
    "output",
    "04_实战演习输入",
}
ENTRY_SUFFIXES = {".py", ".sh"}
ENTRY_PATH_BOOSTS = {
    "app.py": ("V2页面入口", 6),
    "backend/app/main.py": ("FastAPI主入口", 6),
    "devserver.py": ("历史兼容启动壳", 4),
}
PRIMARY_ENTRY_ORDER = {
    "app.py": 0,
    "backend/app/main.py": 1,
    "devserver.py": 2,
}
NOISE_FILE_TOKENS = (
    ".bak",
    ".orig",
    ".rej",
    "_backup",
    "backup_",
    "_legacy",
    "legacy_",
    "_patch",
    "patch_",
    "_clean",
    "clean_",
)

def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)

def is_noise_path(p: Path) -> bool:
    rp = rel(p).replace("\\", "/")
    rp_lower = rp.lower()
    parts = {part.lower() for part in p.parts}
    if parts & {item.lower() for item in NOISE_PATH_PARTS}:
        return True
    if p.name.startswith(".") and p.suffix.lower() == ".py":
        return True
    if any(token in rp_lower for token in NOISE_FILE_TOKENS):
        return True
    return False

def is_test_like_path(p: Path) -> bool:
    rp = rel(p).replace("\\", "/").lower()
    if p.name.lower().startswith("test_"):
        return True
    return "/tests/" in f"/{rp}/"

def walk_files(root: Path):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in IGNORE_DIRS and not d.startswith(".git")]
        for fn in fns:
            p = Path(dp) / fn
            if is_noise_path(p):
                continue
            yield p

def safe_read(p: Path) -> str:
    try:
        if p.suffix.lower() not in TEXT_EXTS and p.stat().st_size > MAX_BYTES:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

files = list(walk_files(ROOT))
dirs = set()
for p in files:
    parent = p.parent
    while str(parent) != str(ROOT.parent) and str(parent).startswith(str(ROOT)):
        dirs.add(parent)
        if parent == ROOT:
            break
        parent = parent.parent

py_files = [p for p in files if p.suffix.lower() == ".py"]
json_files = [p for p in files if p.suffix.lower() == ".json"]
sh_files = [p for p in files if p.suffix.lower() == ".sh"]

stack = []
fastapi_hits = []
flask_hits = []
for p in py_files:
    txt = safe_read(p)
    if "FastAPI(" in txt or "APIRouter(" in txt or "fastapi" in txt:
        fastapi_hits.append(rel(p))
    if "Flask(" in txt or "flask" in txt:
        flask_hits.append(rel(p))

if py_files:
    stack.append(f"Python({len(py_files)})")
if fastapi_hits:
    stack.append(f"FastAPI({len(fastapi_hits)})")
if flask_hits:
    stack.append(f"Flask({len(flask_hits)})")
if sh_files:
    stack.append(f"Shell({len(sh_files)})")
if json_files:
    stack.append(f"JSON知识资产({len(json_files)})")

for marker in ["requirements.txt", "pyproject.toml", "Pipfile", "package.json", "docker-compose.yml", "Dockerfile"]:
    if (ROOT / marker).exists():
        stack.append(marker)

entry_candidates = []
for p in files:
    if p.suffix.lower() not in ENTRY_SUFFIXES:
        continue
    if is_test_like_path(p):
        continue
    txt = safe_read(p)
    score = 0
    reasons = []
    boost = ENTRY_PATH_BOOSTS.get(rel(p).replace("\\", "/"))
    if boost:
        score += boost[1]
        reasons.append(boost[0])
    if p.name in {"main.py", "app.py", "server.py", "devserver.py", "run.py"}:
        score += 2
        reasons.append("入口型文件名")
    if p.name == "run.sh":
        score += 3
        reasons.append("run.sh")
    if "FastAPI(" in txt:
        score += 5
        reasons.append("FastAPI实例")
    if "APIRouter(" in txt:
        score += 1
        reasons.append("路由定义")
    if "include_router(" in txt:
        score += 2
        reasons.append("路由挂载")
    if "uvicorn.run(" in txt or "gunicorn" in txt or "uvicorn " in txt:
        score += 4
        reasons.append("服务启动")
    if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', txt):
        score += 3
        reasons.append("__main__")
    if score > 0:
        normalized_rel = rel(p).replace("\\", "/")
        entry_candidates.append({
            "file": rel(p),
            "score": score,
            "reason": "、".join(dict.fromkeys(reasons)),
            "_primary_rank": PRIMARY_ENTRY_ORDER.get(normalized_rel, 9),
        })
entry_candidates = sorted(entry_candidates, key=lambda x: (x.get("_primary_rank", 9), -x["score"], x["file"]))[:15]
for row in entry_candidates:
    row.pop("_primary_rank", None)

route_rows = []
route_pat = re.compile(r'@(?:router|app)\.(get|post|put|delete|patch|options|head|websocket)\(\s*[rubfRUBF]*[\'"]([^\'"]+)')
prefix_pat = re.compile(r'APIRouter\s*\((?:(?!\)).)*?prefix\s*=\s*[\'"]([^\'"]+)[\'"]', re.S)
include_pat = re.compile(r'include_router\(\s*([A-Za-z_][A-Za-z0-9_]*)')

for p in py_files:
    txt = safe_read(p)
    endpoints = route_pat.findall(txt)
    if endpoints or "APIRouter(" in txt or "include_router(" in txt or "/routers/" in rel(p).replace("\\", "/"):
        prefix_m = prefix_pat.search(txt)
        prefix = prefix_m.group(1) if prefix_m else ""
        includes = include_pat.findall(txt)
        route_rows.append({
            "file": rel(p),
            "prefix": prefix,
            "endpoint_count": len(endpoints),
            "sample_endpoints": [f"{m.upper()} {u}" for m, u in endpoints[:5]],
            "include_router": includes[:8],
        })
route_rows = sorted(route_rows, key=lambda x: (-x["endpoint_count"], x["file"]))[:30]

rule_files = []
for p in files:
    rp = rel(p).lower()
    if p.name == "AGENTS.md" or "prompt" in rp or "supervisor_prompt" in rp:
        rule_files.append(rel(p))
rule_files = sorted(rule_files)

def themed_candidates(keys, limit=20):
    rows = []
    for p in files:
        txt = safe_read(p)
        rp = rel(p).lower()
        score = 0
        reasons = []
        for k in keys:
            kl = k.lower()
            if kl in rp:
                score += 3
                reasons.append(f"path:{k}")
            if txt and kl in txt.lower():
                score += 1
                reasons.append(k)
        if score > 0:
            rows.append({
                "file": rel(p),
                "score": score,
                "reason": "、".join(dict.fromkeys(reasons))
            })
    rows.sort(key=lambda x: (-x["score"], x["file"]))
    return rows[:limit]

audit_rows = themed_candidates(["audit", "审计", "score", "评分", "replay"])
export_rows = themed_candidates(["export", "导出", "docx", "pdf", "artifact"])
kg_rows = themed_candidates(["knowledge_graph", "知识图谱", "project_profile", "graph", ".json"])

temp_rows = []
for p in files:
    name = p.name.lower()
    if any(x in name for x in ["tmp", "temp", "demo", "example", "sample", "test", "pdfdemo"]):
        temp_rows.append(rel(p))
temp_rows = sorted(dict.fromkeys(temp_rows))[:30]

def import_glimpse(p: Path):
    txt = safe_read(p)
    if not txt.strip():
        return []
    try:
        tree = ast.parse(txt)
    except Exception:
        return []
    mods = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            if base.strip("."):
                mods.append(base)
            for n in node.names[:8]:
                mods.append(f"{base}:{n.name}")
    keys = []
    for m in mods:
        if any(k in m for k in ["routers", "knowledge_graph", "project_profile", "audit", "export", "app", "tools", "clawdbot"]):
            keys.append(m)
    return keys[:12]

focus_files = []
seen = set()
for group in [entry_candidates[:5], audit_rows[:5], export_rows[:5], kg_rows[:5]]:
    for row in group:
        if row["file"] not in seen:
            seen.add(row["file"])
            focus_files.append(row["file"])

import_views = []
for f in focus_files[:20]:
    import_views.append({
        "file": f,
        "imports": import_glimpse(ROOT / f)
    })

top_dirs = sorted({rel(d) for d in dirs if len(d.relative_to(ROOT).parts) <= 2})

report = {
    "root": str(ROOT),
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "counts": {
        "files": len(files),
        "dirs": len(dirs),
        "py": len(py_files),
        "json": len(json_files),
        "sh": len(sh_files)
    },
    "stack": stack,
    "entry_candidates": entry_candidates,
    "routes": route_rows,
    "rule_files": rule_files,
    "audit_chain_candidates": audit_rows,
    "export_chain_candidates": export_rows,
    "knowledge_graph_candidates": kg_rows,
    "temp_demo_files": temp_rows,
    "focus_imports": import_views,
    "top_dirs": top_dirs,
}

(OUT / "repo_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

lines = []
lines.append("# 文档生成系统 原地体检报告")
lines.append("")
lines.append(f"- 根目录：`{ROOT}`")
lines.append(f"- 生成时间：{report['generated_at']}")
lines.append(f"- 文件/目录：{len(files)} / {len(dirs)}")
lines.append(f"- Python/JSON/Shell：{len(py_files)} / {len(json_files)} / {len(sh_files)}")
lines.append("")
lines.append("## 1. 技术栈判断")
for s in stack:
    lines.append(f"- {s}")
lines.append("")
lines.append("## 2. 入口候选")
for r in entry_candidates:
    lines.append(f"- `{r['file']}` | 分值 {r['score']} | {r['reason']}")
lines.append("")
lines.append("## 3. 路由结构")
for r in route_rows:
    lines.append(f"- `{r['file']}` | prefix=`{r['prefix']}` | endpoint={r['endpoint_count']} | include_router={', '.join(r['include_router']) if r['include_router'] else '-'}")
    for ep in r["sample_endpoints"]:
        lines.append(f"  - {ep}")
lines.append("")
lines.append("## 4. 规则/提示词文件")
for f in rule_files:
    lines.append(f"- `{f}`")
lines.append("")
lines.append("## 5. 审计链路候选")
for r in audit_rows:
    lines.append(f"- `{r['file']}` | 分值 {r['score']} | {r['reason']}")
lines.append("")
lines.append("## 6. 导出链路候选")
for r in export_rows:
    lines.append(f"- `{r['file']}` | 分值 {r['score']} | {r['reason']}")
lines.append("")
lines.append("## 7. 知识图谱链路候选")
for r in kg_rows:
    lines.append(f"- `{r['file']}` | 分值 {r['score']} | {r['reason']}")
lines.append("")
lines.append("## 8. 重点文件导入线索")
for r in import_views:
    lines.append(f"- `{r['file']}`")
    if r["imports"]:
        for m in r["imports"]:
            lines.append(f"  - {m}")
    else:
        lines.append("  - 无明显本地导入线索")
lines.append("")
lines.append("## 9. 临时/样例/演示文件")
for f in temp_rows:
    lines.append(f"- `{f}`")
lines.append("")
lines.append("## 10. 二层目录快照")
for d in top_dirs:
    lines.append(f"- `{d}`")
lines.append("")

(OUT / "repo_report.md").write_text("\n".join(lines), encoding="utf-8")

print("[OK] 已生成：")
print(f"  {OUT / 'repo_report.md'}")
print(f"  {OUT / 'repo_report.json'}")
print("")
print("[技术栈]", " | ".join(stack) if stack else "未识别")
print("")
print("[入口候选 TOP5]")
for r in entry_candidates[:5]:
    print(f"- {r['file']} | {r['score']} | {r['reason']}")
print("")
print("[审计/导出/知识图谱 各TOP3]")
for title, rows in [("审计", audit_rows), ("导出", export_rows), ("知识图谱", kg_rows)]:
    print(f"{title}:")
    for r in rows[:3]:
        print(f"  - {r['file']} | {r['score']} | {r['reason']}")
