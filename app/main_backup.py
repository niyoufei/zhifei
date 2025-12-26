# -*- coding: utf-8 -*-
from fastapi import FastAPI
from backend.app.routers.score_router import router as score_router
from backend.routes_report import router as report_router

app = FastAPI()
app.include_router(score_router)
app.include_router(report_router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)

# === [M9+] Export Layout Optimization Hook ===
from fastapi import BackgroundTasks
import subprocess, os

@app.post("/export")
async def export_document(background_tasks: BackgroundTasks):
    """
    Export endpoint with layout optimization and audit trace.
    """
    # 1️⃣ 假设已有生成逻辑，这里引用你的最终 docx 输出路径：
    generated_docx = "build/_demo.docx"

    # 2️⃣ 启动后处理（异步执行，避免阻塞）
    hook_path = "backend/hooks/export_postprocess.py"
    if os.path.exists(hook_path):
        background_tasks.add_task(
            subprocess.run, ["python3", hook_path, generated_docx]
        )
        return {"status": "exported", "path": generated_docx, "postprocess": "scheduled"}
    else:
        return {"status": "exported", "path": generated_docx, "postprocess": "missing_hook"}

# === [M10] Unified full export with layout optimization + audit trace ===
@app.post("/export/full")
async def export_full(background_tasks: BackgroundTasks):
    """
    One-click export: generate docx, optimize layout, update audit chain, build trace map.
    """
    generated_docx = "build/_demo.docx"
    hooks = [
        "backend/hooks/export_postprocess.py",
        "backend/hooks/export_finalize.py",
    ]
    for hook in hooks:
        if os.path.exists(hook):
            background_tasks.add_task(subprocess.run, ["python3", hook, generated_docx])
    return {"status": "exported", "path": generated_docx, "pipeline": "layout+audit+trace_map"}

# === [M11] Full export with parameterized layout ===
from pydantic import BaseModel

class ExportLayoutConfig(BaseModel):
    paper: str = "A4"                     # "A4" | "Letter"
    orientation: str = "auto"             # "auto" | "portrait" | "landscape"
    margins: str = "20,20,20,25"          # "top,right,bottom,left" in mm
    auto_pagebreak: bool = True           # H1 是否自动分页

@app.post("/export/full/config")
async def export_full_config(cfg: ExportLayoutConfig, background_tasks: BackgroundTasks):
    """
    One-click export with user-specified layout params:
    - paper/orientation/margins/auto_pagebreak are written into audit trace
    - still generates audit_trace_map.xlsx/pdf
    """
    generated_docx = "build/_demo.docx"
    # 触发带参数的后处理
    hook_post = "backend/hooks/export_postprocess.py"
    if os.path.exists(hook_post):
        args = ["python3", hook_post, generated_docx,
                "--paper", cfg.paper,
                "--orientation", cfg.orientation,
                "--margins", cfg.margins]
        if not cfg.auto_pagebreak:
            args.append("--no-pagebreak")
        background_tasks.add_task(subprocess.run, args)
    # 生成追溯图表
    hook_final = "backend/hooks/export_finalize.py"
    if os.path.exists(hook_final):
        background_tasks.add_task(subprocess.run, ["python3", hook_final])
    return {"status": "exported",
            "path": generated_docx,
            "pipeline": "layout+audit+trace_map",
            "params": cfg.model_dump()}

# === [M14] Audit Dashboard & Data ===
from fastapi.responses import FileResponse, JSONResponse

@app.get("/audit/chain")
def get_audit_chain():
    import json, os
    path = "build/export_audit_chain.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try: data = json.load(f) or {"chain":[]}
            except Exception: data = {"chain":[]}
    else:
        data = {"chain":[]}
    return JSONResponse(data)

@app.get("/audit/dashboard")
def audit_dashboard():
    import os
    html = "frontend/audit_dashboard.html"
    return FileResponse(html) if os.path.exists(html) else JSONResponse({"error":"dashboard not found"}, status_code=404)

from fastapi.responses import FileResponse, JSONResponse

@app.get("/audit/chain")
def get_audit_chain():
    import json, os
    path = "build/export_audit_chain.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f) or {"chain": []}
            except Exception:
                data = {"chain": []}
    else:
        data = {"chain": []}
    return JSONResponse(data)

@app.get("/audit/dashboard")
def audit_dashboard():
    import os
    html = "frontend/audit_dashboard.html"
    return FileResponse(html) if os.path.exists(html) else JSONResponse({"error": "dashboard not found"}, status_code=404)

from pydantic import BaseModel
from fastapi.responses import JSONResponse
import subprocess, os, json

class ReplayReq(BaseModel):
    index: int = -1

@app.post("/export/replay")
def export_replay(req: ReplayReq):
    script = "tools/replay_export.py"
    if not os.path.exists(script):
        return JSONResponse({"error": "replay script missing"}, status_code=500)
    r = subprocess.run(
        ["python3", script, "--index", str(req.index)],
        capture_output=True, text=True
    )
    ok = (r.returncode == 0)
    return {
        "status": "ok" if ok else "error",
        "returncode": r.returncode,
        "stdout": r.stdout[-2000:],
        "stderr": r.stderr[-2000:]
    }

class DiffReq(BaseModel):
    a: int = -1
    b: int = -2

@app.post("/export/diff")
def export_diff(req: DiffReq):
    script = "tools/diff_audit.py"
    if not os.path.exists(script):
        return JSONResponse({"error": "diff script missing"}, status_code=500)
    r = subprocess.run(
        ["python3", script, "--a", str(req.a), "--b", str(req.b)],
        capture_output=True, text=True
    )
    ok = (r.returncode == 0)
    txt = "build/diff_audit_report.txt"
    jsn = "build/diff_audit_report.json"
    payload = {
        "passed": None, "txt": txt, "json": jsn,
        "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]
    }
    try:
        with open(jsn, "r", encoding="utf-8") as f:
            result = json.load(f)
            payload.update(result)
    except Exception:
        pass
    payload["status"] = "ok" if ok else "error"
    return payload

# === [M14+ 审计日志整合] ===
from audit_log import log_audit

@app.post("/export/audit_log")
def export_audit_log(req: DiffReq):
    """对导出操作进行日志审计"""
    try:
        result = {
            "action": "export_diff",
            "input": {"a": req.a, "b": req.b},
            "output": "diff_audit_report.json",
        }
        entry = log_audit("export_diff", result["input"], result["output"], "v1.0-M14+")
        return {"status": "ok", "audit_entry": entry}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# === [M15 自动审计：真实导出路径挂接] ===
from audit_log import log_audit

@app.post("/export/diff_audited")
def export_diff_audited(req: DiffReq):
    """
    与 /export/diff 等价，但在成功生成后自动写入审计日志。
    """
    import os, subprocess, json
    script = "tools/diff_audit.py"
    if not os.path.exists(script):
        return JSONResponse({"error": "diff script missing"}, status_code=500)

    # 复用原导出流程
    r = subprocess.run(
        ["python3", script, "--a", str(req.a), "--b", str(req.b)],
        capture_output=True, text=True
    )
    ok = (r.returncode == 0)
    txt = "build/diff_audit_report.txt"
    jsn = "build/diff_audit_report.json"
    payload = {
        "passed": ok,
        "note": "audited export",
        "stdout": r.stdout[-2000:],
        "stderr": r.stderr[-2000:]
    }
    try:
        with open(jsn, "r", encoding="utf-8") as f:
            result = json.load(f)
            payload.update(result)
    except Exception:
        pass

    # 自动审计：记录输入/输出/模型版本
    try:
        input_data = {"a": req.a, "b": req.b}
        output_data = {"report_json": jsn, "report_txt": txt, "ok": ok}
        entry = log_audit("export_diff", input_data, output_data, "v1.0-M15")
        payload["audit_entry"] = entry
    except Exception as e:
        payload["audit_error"] = str(e)

    payload["status"] = "ok" if ok else "error"
    return payload

# === [M15 仪表板数据接口] ===
@app.get("/audit/data")
def audit_data(limit: int = 100):
    """
    返回最近 limit 条审计日志（从 audit_trail.jsonl 读取）。
    """
    import json, os
    path = "audit_trail.jsonl"
    if not os.path.exists(path):
        return {"items": [], "total": 0}
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                continue
    items = items[-limit:]  # 只保留最近 limit 条
    return {"items": items, "total": len(items)}

# ---------------------------
# M16-5 接口注册模板 (一致性修复)
# ---------------------------
from fastapi import Body
from pydantic import BaseModel

class IngestRequest(BaseModel):
    file_path: str
    parse_mode: str = "auto"

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5

class ComposeRequest(BaseModel):
    topic: str
    outline: list[str]

class ExportRequest(BaseModel):
    doc_id: str
    format: str = "docx"

@app.post("/ingest")
def ingest(req: IngestRequest):
    return {"status": "ok", "received": req.dict()}

@app.post("/retrieve")
def retrieve(req: RetrieveRequest):
    return {"status": "ok", "query": req.query, "results": []}

from compose_engine import Composer

composer = Composer()

@app.post("/compose")
def compose(req: ComposeRequest):
    result = composer.compose(
        topic=req.topic,
        outline=req.outline,
        max_pages=50
    )
    return {
        "status": "ok",
        "topic": req.topic,
        "outline": req.outline,
        "sections": result["sections"]
    }


from utils_write_docx import write_compose_to_docx
import json
import os

@app.post("/export")
def export(req: ExportRequest):
    # 1. compose 的结果存储在 build/compose.json（你系统生成的 compose 输出）
    compose_json_path = "build/compose.json"
    if not os.path.exists(compose_json_path):
        return {"status": "error", "message": "compose result not found"}

    # 2. 读取 compose 生成的 sections
    with open(compose_json_path, "r", encoding="utf-8") as f:
        compose_data = json.load(f)

    sections = compose_data.get("sections", [])

    # 3. 调用你的 Word 写入函数
    output_path = f"build/{req.doc_id}.docx"
    write_compose_to_docx(sections, output_path=output_path)

    return {
        "status": "exported",
        "path": output_path
    }


# ---------------------------
# M18-2 集成规则引擎（compose 前评分）
# ---------------------------
from pathlib import Path
from rules.rule_engine import load_rules_from_yaml, RuleEngine

RULE_PATH = Path.home() / "traceable-docsys" / "rules" / "configs" / "example.yaml"
rules = load_rules_from_yaml(str(RULE_PATH))
engine = RuleEngine(rules)

@app.post("/compose")
def compose(req: ComposeRequest):
    # 1. 执行规则判定
    evaluation = engine.evaluate(req.dict())

    # 2. 生成表述逻辑（仅在规则全部通过时执行）
    passed = all(d["passed"] for d in evaluation["details"])
    if not passed:
        return {
            "status": "blocked",
            "reason": "规则未全部通过，阻止生成",
            "evaluation": evaluation
        }

    # 3. 若通过则继续生成
    composed = {
        "topic": req.topic,
        "outline": req.outline,
        "generated_text": f"基于规则校验结果，总分 {evaluation['total_score']}，开始生成文稿。"
    }
    return {"status": "ok", "evaluation": evaluation, "composed": composed}
