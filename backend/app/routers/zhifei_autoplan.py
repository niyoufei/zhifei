from __future__ import annotations

import asyncio
import tempfile
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel

from backend.zhifei_autoplan.parsers.tender_parser import TenderParser
from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.kg_store import save_kg_bytes, list_kg, set_active_kg, get_active_kg
from backend.zhifei_autoplan.kg_runtime import search_kg
from backend.zhifei_autoplan.tender_store import save_tender_matrix, load_tender_matrix
from backend.zhifei_autoplan.boq_store import save_boq_data
from backend.auth_store import get_user_by_id, update_balance, log_charge, count_user_actions_since
import jwt
import os
from backend.zhifei_autoplan.orchestrator import run_autoplan
from pathlib import Path
import json
from backend.zhifei_autoplan.exporter import export_autoplan_docx_from_file, export_autoplan_docx, export_autoplan_compare_docx
from fastapi.responses import FileResponse
from backend.zhifei_autoplan.job_store import create_job, update_job, get_job, list_jobs, cleanup_jobs
from backend.zhifei_autoplan.plan_store import save_plan, load_plan
from backend.zhifei_autoplan.optimizer import optimize_sections
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids

router = APIRouter(prefix="/autoplan", tags=["Zhifei AutoPlan"])
JWT_SECRET = os.environ.get("ZF_JWT_SECRET", "change-me")
JWT_ALG = "HS256"
COST_PER_JOB = int(os.environ.get("ZF_JOB_COST", "1"))


def _load_field_alias() -> dict:
    try:
        from pathlib import Path
        import json
        cfg_path = Path("backend/data/autoplan/config.json")
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            alias = cfg.get("job_list_field_alias")
            if isinstance(alias, dict):
                return {str(k): {str(s) for s in v} for k, v in alias.items() if isinstance(v, list)}
    except Exception:
        pass
    return {}


def _parse_fields(fields: list[str] | None) -> set[str]:
    if not fields:
        return set()
    parsed: set[str] = set()
    for f in fields:
        if not isinstance(f, str):
            continue
        for part in f.split(","):
            p = part.strip()
            if p:
                parsed.add(p)
    # alias expand (configurable)
    alias = _load_field_alias()
    if not alias:
        alias = {
            "time": {"created_at", "updated_at"},
            "meta": {"job_id", "status", "created_at", "updated_at"},
            "result_min": {"job_id", "status", "result"},
        }
    expanded: set[str] = set()
    for p in parsed:
        if p in alias:
            expanded.update(alias[p])
        else:
            expanded.add(p)
    return expanded


def _job_list_default_fields() -> set[str]:
    env_fields = os.environ.get("ZF_JOB_LIST_FIELDS")
    if env_fields:
        return {s.strip() for s in env_fields.split(",") if s.strip()}
    try:
        from pathlib import Path
        import json
        cfg_path = Path("backend/data/autoplan/config.json")
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            fields = cfg.get("job_list_default_fields")
            if isinstance(fields, list) and fields:
                return {str(s) for s in fields}
    except Exception:
        pass
    return {"job_id", "status", "created_at", "updated_at", "result", "error"}


def _job_list_field_alias() -> dict:
    alias = _load_field_alias()
    if alias:
        return alias
    return {
        "time": {"created_at", "updated_at"},
        "meta": {"job_id", "status", "created_at", "updated_at"},
        "result_min": {"job_id", "status", "result"},
    }


def _auth_user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(data.get("sub"))
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="invalid user")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")


def _is_admin(authorization: str | None) -> bool:
    admin_key = os.environ.get("ZF_ADMIN_KEY", "")
    return bool(admin_key and authorization == f"Bearer {admin_key}")


def _charge(user: dict, cost: int, action: str):
    if user.get("balance", 0) < cost:
        raise HTTPException(status_code=402, detail="insufficient balance")
    used = count_user_actions_since(user["id"], 24 * 3600)
    limit = int(user.get("daily_limit") or os.environ.get("ZF_DAILY_LIMIT", "50"))
    if used >= limit:
        raise HTTPException(status_code=429, detail="daily limit exceeded")
    update_balance(user["id"], -cost)
    log_charge(user["id"], action, cost)


def _audit(action: str, user_id: int | None = None, detail: dict | None = None):
    try:
        from datetime import datetime
        path = Path("backend/data/audit/autoplan.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "detail": detail or {},
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_audit(
    limit: int = 200,
    action: str | None = None,
    user_id: int | None = None,
    ts_after: str | None = None,
    ts_before: str | None = None,
):
    path = Path("backend/data/audit/autoplan.jsonl")
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    items = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if action and rec.get("action") != action:
            continue
        if user_id is not None and rec.get("user_id") != user_id:
            continue
        if ts_after and str(rec.get("ts") or "") < ts_after:
            continue
        if ts_before and str(rec.get("ts") or "") > ts_before:
            continue
        items.append(rec)
        if len(items) >= limit:
            break
    return items


def _audit_summary(limit: int = 10000, user_id: int | None = None, by_user: bool = False):
    path = Path("backend/data/audit/autoplan.jsonl")
    if not path.exists():
        return {"by_action": {}, "by_user": {}}
    lines = path.read_text(encoding="utf-8").splitlines()
    by_action = {}
    by_user_count = {}
    n = 0
    for line in reversed(lines):
        if n >= limit:
            break
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if user_id is not None and rec.get("user_id") != user_id:
            continue
        n += 1
        act = rec.get("action") or "unknown"
        by_action[act] = by_action.get(act, 0) + 1
        if by_user:
            uid = rec.get("user_id")
            by_user_count[uid] = by_user_count.get(uid, 0) + 1
    return {"by_action": by_action, "by_user": by_user_count, "total": n}


def _audit_stats_by_day(limit_days: int = 30, user_id: int | None = None):
    path = Path("backend/data/audit/autoplan.jsonl")
    if not path.exists():
        return {"by_day": {}, "total": 0}
    lines = path.read_text(encoding="utf-8").splitlines()
    by_day = {}
    total = 0
    try:
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=limit_days)).isoformat()[:10]
    except Exception:
        cutoff = ""
    for line in lines:
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if user_id is not None and rec.get("user_id") != user_id:
            continue
        ts = (rec.get("ts") or "")[:10]
        if cutoff and ts < cutoff:
            continue
        by_day[ts] = by_day.get(ts, 0) + 1
        total += 1
    return {"by_day": dict(sorted(by_day.items())), "total": total}


async def _save_upload(uf: UploadFile) -> str:
    # 临时落地到磁盘，供 pdfplumber/pandas 读取
    data = await uf.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"空文件：{uf.filename}")
    suffix = f"_{uf.filename}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(data)
        return f.name


@router.post("/tender/parse")
async def parse_tender(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    authorization: str | None = Header(default=None),
):
    """
    Module 1：招标文件指数级解析
    - MECE：输出 6 大维度指标，互不包含、完全穷举
    """
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "tender_parse")
    if not files:
        raise HTTPException(status_code=400, detail="未上传文件")
    paths = await asyncio.gather(*[_save_upload(f) for f in files])
    parser = TenderParser()
    matrix = await parser.parse(paths)
    saved_at = save_tender_matrix(matrix.model_dump(), project_id=project_id)
    return {"matrix": matrix.model_dump(), "saved_at": saved_at}


@router.post("/boq/parse")
async def parse_boq(
    file: UploadFile = File(...),
    project_id: str | None = None,
    authorization: str | None = Header(default=None),
):
    """
    Module 2：清单智能识别与统计
    - MECE：清单->工序->资源 三段映射
    """
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "boq_parse")
    if not file:
        raise HTTPException(status_code=400, detail="未上传文件")
    path = await _save_upload(file)
    parser = BoQParser()
    items, stats = await parser.parse(path)
    payload = {
        "items": [it.model_dump() for it in items],
        "stats": stats,
    }
    saved_at = save_boq_data(payload, project_id=project_id)
    return {**payload, "saved_at": saved_at}


@router.post("/plan/save")
async def save_plan_api(req: PlanRequest, project_id: str | None = None, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    path = save_plan(req.model_dump(), project_id=project_id)
    _audit("plan_save", user_id=user["id"], detail={"path": path, "project_id": project_id})
    return {"ok": True, "saved_at": path}


@router.get("/plan/get")
async def get_plan_api(project_id: str | None = None, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _audit("plan_get", user_id=user["id"], detail={"project_id": project_id})
    return {"ok": True, "plan": load_plan(project_id=project_id) or {}}


class ActivateKGRequest(BaseModel):
    kg_id: str


class GenerateRequest(BaseModel):
    project_id: str | None = None
    topic: str
    outline: List[str] = []
    requirements: List[str] = []
    chapter_requirements: dict | None = None
    provider: str | None = None
    model: str | None = None
    provider_chain: List[dict] | None = None
    providers: List[str] = []
    model_map: dict | None = None
    style: dict | None = None
    variants: int = 1
    chapter_pages: dict | None = None
    quality_strict: bool | None = None
    auto_remediate: bool = True
    remediate_mode: str = "template"  # template | llm
    compare_mode: str = "full"  # full | summary
    compare_max_chars: int = 800
    compare_titles: list[str] | None = None
    api_key: str | None = None
    base_url: str | None = None
    secret_key: str | None = None
    token_url: str | None = None
    dry_run: bool = False
    generate_images: bool = True


class PlanRequest(BaseModel):
    outline: List[str]
    style: dict = {}
    variants: int = 1
    chapter_requirements: dict = {}
    chapter_pages: dict = {}
    quality_strict: bool = True
    auto_remediate: bool = True
    remediate_mode: str = "template"
    compare_mode: str = "full"
    compare_max_chars: int = 800
    compare_titles: list[str] | None = None


class OptimizeRequest(BaseModel):
    titles: List[str]
    instruction: str = "请在保持证据引用的前提下优化本章表达。"
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    secret_key: str | None = None
    token_url: str | None = None


class JobListFilterRequest(BaseModel):
    job_ids: list[str] | None = None
    limit: int = 200
    status: str | None = None
    has_compare: bool | None = None
    updated_after: float | None = None
    updated_before: float | None = None
    recent_hours: int | None = None
    created_after: float | None = None
    created_before: float | None = None
    recent_days: int | None = None
    completed_after: float | None = None
    completed_before: float | None = None
    completed_recent_hours: int | None = None
    fields: list[str] | None = None
    full: bool = False


class AuditQueryRequest(BaseModel):
    limit: int = 200
    action: str | None = None
    user_id: int | None = None
    ts_after: str | None = None
    ts_before: str | None = None


class AuditExportRequest(BaseModel):
    fmt: str = "json"  # json|csv|xlsx
    limit: int = 1000
    action: str | None = None
    user_id: int | None = None
    ts_after: str | None = None
    ts_before: str | None = None
    filename: str | None = None


class AuditExportListRequest(BaseModel):
    user_id: int | None = None
    limit: int = 100


class AuditExportCleanupRequest(BaseModel):
    user_id: int | None = None
    older_than_days: int | None = None
    keep_latest_n: int | None = None


@router.post("/kg/upload")
async def upload_kg(file: UploadFile = File(...)):
    """
    上传你已有的知识图谱（JSON），系统只做存档与追溯，不重新构建。
    """
    if not file:
        raise HTTPException(status_code=400, detail="未上传文件")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    try:
        # 仅做 JSON 结构校验，避免错误文件
        import json as _json
        _json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        raise HTTPException(status_code=400, detail="仅支持 JSON 知识图谱文件")
    meta = save_kg_bytes(data, file.filename)
    return {"ok": True, "kg": meta}


@router.get("/kg/list")
async def list_kg_files():
    return {"ok": True, "items": list_kg()}


@router.get("/kg/active")
async def get_active_kg_file():
    return {"ok": True, "active": get_active_kg()}


@router.post("/kg/activate")
async def activate_kg(req: ActivateKGRequest):
    try:
        rec = set_active_kg(req.kg_id)
        return {"ok": True, "active": rec}
    except ValueError:
        raise HTTPException(status_code=404, detail="kg_id not found")


@router.get("/kg/search")
async def search_kg_api(q: str, top_k: int = 6):
    return search_kg(q, top_k=top_k)


@router.post("/generate")
async def generate_plan(req: GenerateRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_generate")
    payload = req.model_dump()
    pid = str(payload.get("project_id") or "").strip() or None
    plan = load_plan(project_id=pid) or {}
    tender = load_tender_matrix(project_id=pid) or {}
    if not payload.get("outline"):
        payload["outline"] = plan.get("outline") or []
    if not payload.get("outline"):
        payload["outline"] = tender.get("outline") or []
    if payload.get("chapter_requirements") is None:
        payload["chapter_requirements"] = plan.get("chapter_requirements") or {}
    if not payload.get("chapter_requirements"):
        payload["chapter_requirements"] = tender.get("chapter_requirements") or {}
    if payload.get("style") is None:
        payload["style"] = plan.get("style") or {}
    if not payload.get("style"):
        payload["style"] = tender.get("style") or {}
    if payload.get("chapter_pages") is None:
        payload["chapter_pages"] = plan.get("chapter_pages") or {}
    if not payload.get("chapter_pages"):
        payload["chapter_pages"] = tender.get("chapter_pages") or {}
    if payload.get("quality_strict") is None:
        payload["quality_strict"] = plan.get("quality_strict", True)
    if payload.get("auto_remediate") is None:
        payload["auto_remediate"] = plan.get("auto_remediate", True)
    if payload.get("remediate_mode") is None:
        payload["remediate_mode"] = plan.get("remediate_mode", "template")
    if payload.get("compare_mode") is None:
        payload["compare_mode"] = plan.get("compare_mode", "full")
    if payload.get("compare_max_chars") is None:
        payload["compare_max_chars"] = plan.get("compare_max_chars", 800)
    if payload.get("compare_titles") is None:
        payload["compare_titles"] = plan.get("compare_titles")
    if not payload.get("variants"):
        payload["variants"] = plan.get("variants") or 1

    variants = int(payload.get("variants") or 1)
    variant_ids = reserve_variant_ids(
        project_id=pid,
        count=max(1, variants),
        explicit_variant_id=payload.get("variant_id"),
        explicit_template_id=payload.get("logic_template_id") or payload.get("logic_template"),
    )
    results = []
    for vid in variant_ids:
        payload["variant_id"] = int(vid)
        results.append(await run_autoplan(payload))
    out_path = Path("build") / "autoplan_generated.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    # 自动导出 DOCX（每个版本一个文件）
    docx_files = []
    for i, variant in enumerate(results):
        out_docx = Path("build") / f"autoplan_generated_v{i + 1}.docx"
        export_autoplan_docx(variant, str(out_docx))
        docx_files.append(str(out_docx))
    _audit("generate", user_id=user["id"], detail={"variants": len(results), "docx": docx_files, "project_id": pid})
    return {"ok": True, "saved_at": str(out_path), "docx": docx_files, "result": results}


@router.post("/generate_async")
async def generate_plan_async(req: GenerateRequest, background_tasks: BackgroundTasks, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_generate_async")
    payload = req.model_dump()
    pid = str(payload.get("project_id") or "").strip() or None
    plan = load_plan(project_id=pid) or {}
    tender = load_tender_matrix(project_id=pid) or {}
    if not payload.get("outline"):
        payload["outline"] = plan.get("outline") or []
    if not payload.get("outline"):
        payload["outline"] = tender.get("outline") or []
    if payload.get("chapter_requirements") is None:
        payload["chapter_requirements"] = plan.get("chapter_requirements") or {}
    if not payload.get("chapter_requirements"):
        payload["chapter_requirements"] = tender.get("chapter_requirements") or {}
    if payload.get("style") is None:
        payload["style"] = plan.get("style") or {}
    if not payload.get("style"):
        payload["style"] = tender.get("style") or {}
    if payload.get("chapter_pages") is None:
        payload["chapter_pages"] = plan.get("chapter_pages") or {}
    if not payload.get("chapter_pages"):
        payload["chapter_pages"] = tender.get("chapter_pages") or {}
    if payload.get("quality_strict") is None:
        payload["quality_strict"] = plan.get("quality_strict", True)
    if payload.get("auto_remediate") is None:
        payload["auto_remediate"] = plan.get("auto_remediate", True)
    if payload.get("remediate_mode") is None:
        payload["remediate_mode"] = plan.get("remediate_mode", "template")
    if payload.get("compare_mode") is None:
        payload["compare_mode"] = plan.get("compare_mode", "full")
    if payload.get("compare_max_chars") is None:
        payload["compare_max_chars"] = plan.get("compare_max_chars", 800)
    if payload.get("compare_titles") is None:
        payload["compare_titles"] = plan.get("compare_titles")
    if not payload.get("variants"):
        payload["variants"] = plan.get("variants") or 1
    variants = int(payload.get("variants") or 1)
    payload["_variant_ids"] = reserve_variant_ids(
        project_id=pid,
        count=max(1, variants),
        explicit_variant_id=payload.get("variant_id"),
        explicit_template_id=payload.get("logic_template_id") or payload.get("logic_template"),
    )
    job_id = create_job(payload, user_id=user["id"])
    _audit("generate_async", user_id=user["id"], detail={"job_id": job_id, "project_id": pid})

    def _run_job():
        try:
            update_job(job_id, status="running")
            variants = int(payload.get("variants") or 1)
            variant_ids = payload.get("_variant_ids")
            if not isinstance(variant_ids, list) or not variant_ids:
                variant_ids = reserve_variant_ids(
                    project_id=pid,
                    count=max(1, variants),
                    explicit_variant_id=payload.get("variant_id"),
                    explicit_template_id=payload.get("logic_template_id") or payload.get("logic_template"),
                )
            results = []
            for vid in variant_ids:
                payload["variant_id"] = int(vid)
                results.append(asyncio.run(run_autoplan(payload)))
            out_json = Path("build") / f"autoplan_{job_id}.json"
            out_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
            docx_files = []
            compare_files = []
            for i, variant in enumerate(results):
                out_docx = Path("build") / f"autoplan_{job_id}_v{i + 1}.docx"
                export_autoplan_docx(variant, str(out_docx))
                docx_files.append(str(out_docx))
                out_compare = Path("build") / f"autoplan_{job_id}_compare_v{i + 1}.docx"
                export_autoplan_compare_docx(variant, str(out_compare))
                compare_files.append(str(out_compare))
            update_job(
                job_id,
                status="done",
                result={"json": str(out_json), "docx": docx_files, "compare_docx": compare_files},
            )
        except Exception as e:
            update_job(job_id, status="failed", error=repr(e))

    background_tasks.add_task(_run_job)
    return {"ok": True, "job_id": job_id}


@router.post("/generate_async_batch")
async def generate_async_batch(requests: list[GenerateRequest], background_tasks: BackgroundTasks, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    jobs = []
    for req in requests[:10]:
        _charge(user, COST_PER_JOB, "autoplan_generate_async_batch")
        payload = req.model_dump()
        pid = str(payload.get("project_id") or "").strip() or None
        plan = load_plan(project_id=pid) or {}
        tender = load_tender_matrix(project_id=pid) or {}
        if not payload.get("outline"):
            payload["outline"] = plan.get("outline") or []
        if not payload.get("outline"):
            payload["outline"] = tender.get("outline") or []
        if payload.get("chapter_requirements") is None:
            payload["chapter_requirements"] = plan.get("chapter_requirements") or {}
        if not payload.get("chapter_requirements"):
            payload["chapter_requirements"] = tender.get("chapter_requirements") or {}
        if payload.get("style") is None:
            payload["style"] = plan.get("style") or {}
        if not payload.get("style"):
            payload["style"] = tender.get("style") or {}
        if payload.get("chapter_pages") is None:
            payload["chapter_pages"] = plan.get("chapter_pages") or {}
        if not payload.get("chapter_pages"):
            payload["chapter_pages"] = tender.get("chapter_pages") or {}
        if payload.get("quality_strict") is None:
            payload["quality_strict"] = plan.get("quality_strict", True)
        if payload.get("auto_remediate") is None:
            payload["auto_remediate"] = plan.get("auto_remediate", True)
        if payload.get("remediate_mode") is None:
            payload["remediate_mode"] = plan.get("remediate_mode", "template")
        if payload.get("compare_mode") is None:
            payload["compare_mode"] = plan.get("compare_mode", "full")
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = plan.get("compare_max_chars", 800)
        if payload.get("compare_titles") is None:
            payload["compare_titles"] = plan.get("compare_titles")
        if not payload.get("variants"):
            payload["variants"] = plan.get("variants") or 1
        variants = int(payload.get("variants") or 1)
        payload["_variant_ids"] = reserve_variant_ids(
            project_id=pid,
            count=max(1, variants),
            explicit_variant_id=payload.get("variant_id"),
            explicit_template_id=payload.get("logic_template_id") or payload.get("logic_template"),
        )
        job_id = create_job(payload, user_id=user["id"])

        def _run_job(_job_id: str, _payload: dict):
            try:
                local_payload = json.loads(json.dumps(_payload))
                update_job(_job_id, status="running")
                variants = int(local_payload.get("variants") or 1)
                variant_ids = local_payload.get("_variant_ids")
                if not isinstance(variant_ids, list) or not variant_ids:
                    variant_ids = reserve_variant_ids(
                        project_id=str(local_payload.get("project_id") or "").strip() or None,
                        count=max(1, variants),
                        explicit_variant_id=local_payload.get("variant_id"),
                        explicit_template_id=local_payload.get("logic_template_id") or local_payload.get("logic_template"),
                    )
                results = []
                for vid in variant_ids:
                    local_payload["variant_id"] = int(vid)
                    results.append(asyncio.run(run_autoplan(local_payload)))
                out_json = Path("build") / f"autoplan_{_job_id}.json"
                out_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
                docx_files = []
                compare_files = []
                for i, variant in enumerate(results):
                    out_docx = Path("build") / f"autoplan_{_job_id}_v{i + 1}.docx"
                    export_autoplan_docx(variant, str(out_docx))
                    docx_files.append(str(out_docx))
                    out_compare = Path("build") / f"autoplan_{_job_id}_compare_v{i + 1}.docx"
                    export_autoplan_compare_docx(variant, str(out_compare))
                    compare_files.append(str(out_compare))
                update_job(
                    _job_id,
                    status="done",
                    result={"json": str(out_json), "docx": docx_files, "compare_docx": compare_files},
                )
            except Exception as e:
                update_job(_job_id, status="failed", error=repr(e))

        background_tasks.add_task(_run_job, job_id, payload)
        jobs.append(job_id)
    return {"ok": True, "job_ids": jobs}


@router.post("/optimize")
async def optimize_content(req: OptimizeRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_optimize")
    json_path = Path("build") / "autoplan_generated.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="autoplan_generated.json not found")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    result = await optimize_sections(data, req.model_dump())
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    docx_files = []
    if isinstance(result, dict) and isinstance(result.get("variants"), list) and result["variants"]:
        for i, variant in enumerate(result["variants"]):
            out_docx = Path("build") / f"autoplan_generated_v{i + 1}.docx"
            export_autoplan_docx(variant, str(out_docx))
            docx_files.append(str(out_docx))
    else:
        out_docx = Path("build") / "autoplan_generated_v1.docx"
        export_autoplan_docx_from_file(str(json_path), str(out_docx))
        docx_files.append(str(out_docx))
    _audit("optimize", user_id=user["id"], detail={"docx": docx_files})
    return {"ok": True, "docx": docx_files}


@router.get("/job_status")
async def job_status(job_id: str, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("user_id") not in (None, user["id"]):
        raise HTTPException(status_code=403, detail="forbidden")
    return {"ok": True, "job": job}


@router.get("/job_download")
async def job_download(job_id: str, kind: str = "docx", v: int = 1, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("user_id") not in (None, user["id"]):
        raise HTTPException(status_code=403, detail="forbidden")
    result = job.get("result") or {}
    path = result.get(kind)
    if kind in ("docx", "compare_docx") and isinstance(path, list):
        v = max(1, int(v or 1))
        path = path[v - 1] if v <= len(path) else None
    if not path:
        raise HTTPException(status_code=404, detail="file not ready")
    _audit("job_download", user_id=user["id"], detail={"job_id": job_id, "kind": kind, "v": v, "path": path})
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if kind in ("docx", "compare_docx")
        else "application/json",
        filename=f"autoplan_{job_id}_v{v}.docx"
        if kind in ("docx", "compare_docx")
        else f"autoplan_{job_id}.{kind}",
    )


@router.get("/job_docx_versions")
async def job_docx_versions(job_id: str, kind: str = "docx", authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("user_id") not in (None, user["id"]):
        raise HTTPException(status_code=403, detail="forbidden")
    result = job.get("result") or {}
    docx = result.get(kind)
    if isinstance(docx, list):
        versions = list(range(1, len(docx) + 1))
        files = [Path(p).name for p in docx]
    elif isinstance(docx, str):
        versions = [1]
        files = [Path(docx).name]
    else:
        versions = []
        files = []
    return {"ok": True, "versions": versions, "files": files}


@router.get("/job_list")
async def job_list(
    limit: int = 50,
    status: str | None = None,
    has_compare: bool | None = None,
    updated_after: float | None = None,
    updated_before: float | None = None,
    recent_hours: int | None = None,
    created_after: float | None = None,
    created_before: float | None = None,
    recent_days: int | None = None,
    completed_after: float | None = None,
    completed_before: float | None = None,
    completed_recent_hours: int | None = None,
    full: bool = False,
    fields: list[str] | None = None,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    items = list_jobs(limit=limit, user_id=user["id"])
    if status:
        items = [it for it in items if it.get("status") == status]
    if has_compare is not None:
        if has_compare:
            items = [it for it in items if it.get("result", {}).get("compare_docx")]
        else:
            items = [it for it in items if not it.get("result", {}).get("compare_docx")]
    if updated_after is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) >= float(updated_after)]
    if updated_before is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) <= float(updated_before)]
    if recent_hours is not None:
        import time
        threshold = time.time() - int(recent_hours) * 3600
        items = [it for it in items if float(it.get("updated_at") or 0) >= threshold]
    if created_after is not None:
        items = [it for it in items if float(it.get("created_at") or 0) >= float(created_after)]
    if created_before is not None:
        items = [it for it in items if float(it.get("created_at") or 0) <= float(created_before)]
    if recent_days is not None:
        import time
        threshold = time.time() - int(recent_days) * 86400
        items = [it for it in items if float(it.get("created_at") or 0) >= threshold]
    # completed_* 基于 updated_at（约定 status=done 时 updated_at 为完成时间）
    if completed_after is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) >= float(completed_after)]
    if completed_before is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) <= float(completed_before)]
    if completed_recent_hours is not None:
        import time
        threshold = time.time() - int(completed_recent_hours) * 3600
        items = [it for it in items if float(it.get("updated_at") or 0) >= threshold]
    if not full:
        _fields = _parse_fields(fields) or set(_job_list_default_fields())
        items = [{k: v for k, v in it.items() if k in _fields} for it in items]
    _audit("job_list", user_id=user["id"], detail={"count": len(items)})
    return {"ok": True, "items": items}


@router.post("/job_status_batch")
async def job_status_batch(job_ids: list[str], authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    items = []
    for jid in job_ids[:50]:
        job = get_job(jid)
        if not job:
            continue
        if job.get("user_id") not in (None, user["id"]):
            continue
        items.append(job)
    return {"ok": True, "items": items}


@router.post("/job_list_filtered")
async def job_list_filtered(req: JobListFilterRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    items = list_jobs(limit=req.limit, user_id=user["id"])
    if req.job_ids:
        ids = set(req.job_ids)
        items = [it for it in items if it.get("job_id") in ids]
    if req.status:
        items = [it for it in items if it.get("status") == req.status]
    if req.has_compare is not None:
        if req.has_compare:
            items = [it for it in items if it.get("result", {}).get("compare_docx")]
        else:
            items = [it for it in items if not it.get("result", {}).get("compare_docx")]
    if req.updated_after is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) >= float(req.updated_after)]
    if req.updated_before is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) <= float(req.updated_before)]
    if req.recent_hours is not None:
        import time
        threshold = time.time() - int(req.recent_hours) * 3600
        items = [it for it in items if float(it.get("updated_at") or 0) >= threshold]
    if req.created_after is not None:
        items = [it for it in items if float(it.get("created_at") or 0) >= float(req.created_after)]
    if req.created_before is not None:
        items = [it for it in items if float(it.get("created_at") or 0) <= float(req.created_before)]
    if req.recent_days is not None:
        import time
        threshold = time.time() - int(req.recent_days) * 86400
        items = [it for it in items if float(it.get("created_at") or 0) >= threshold]
    if req.completed_after is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) >= float(req.completed_after)]
    if req.completed_before is not None:
        items = [it for it in items if float(it.get("updated_at") or 0) <= float(req.completed_before)]
    if req.completed_recent_hours is not None:
        import time
        threshold = time.time() - int(req.completed_recent_hours) * 3600
        items = [it for it in items if float(it.get("updated_at") or 0) >= threshold]
    if not req.full:
        fields = _parse_fields(req.fields) or set(_job_list_default_fields())
        trimmed = []
        for it in items:
            trimmed.append({k: v for k, v in it.items() if k in fields})
        items = trimmed
    _audit("job_list_filtered", user_id=user["id"], detail={"count": len(items)})
    return {"ok": True, "items": items}


@router.post("/job_download_batch")
async def job_download_batch(job_ids: list[str], authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    from pathlib import Path
    import zipfile
    zip_path = Path("build") / "autoplan_batch.zip"
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass
    with zipfile.ZipFile(zip_path, "w") as z:
        for jid in job_ids[:20]:
            job = get_job(jid)
            if not job:
                continue
            if job.get("user_id") not in (None, user["id"]):
                continue
            result = job.get("result") or {}
            for k in ("docx", "json", "compare_docx"):
                p = result.get(k)
                if isinstance(p, list):
                    for pi in p:
                        if pi and Path(pi).exists():
                            z.write(pi, arcname=Path(pi).name)
                elif p and Path(p).exists():
                    z.write(p, arcname=Path(p).name)
    return {"ok": True, "zip": str(zip_path)}


@router.post("/job_download_compare_batch")
async def job_download_compare_batch(job_ids: list[str], authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    from pathlib import Path
    import zipfile
    zip_path = Path("build") / "autoplan_compare_batch.zip"
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass
    with zipfile.ZipFile(zip_path, "w") as z:
        for jid in job_ids[:20]:
            job = get_job(jid)
            if not job:
                continue
            if job.get("user_id") not in (None, user["id"]):
                continue
            result = job.get("result") or {}
            p = result.get("compare_docx")
            if isinstance(p, list):
                for pi in p:
                    if pi and Path(pi).exists():
                        z.write(pi, arcname=Path(pi).name)
            elif p and Path(p).exists():
                z.write(p, arcname=Path(p).name)
    return {"ok": True, "zip": str(zip_path)}


@router.get("/job_download_compare_batch_file")
async def job_download_compare_batch_file(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    from pathlib import Path
    zip_path = Path("build") / "autoplan_compare_batch.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="zip not found")
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="autoplan_compare_batch.zip",
    )


@router.get("/job_download_batch_file")
async def job_download_batch_file(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    from pathlib import Path
    zip_path = Path("build") / "autoplan_batch.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="zip not found")
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="autoplan_batch.zip",
    )


@router.post("/job_cleanup")
async def job_cleanup(older_than_days: int = 7, authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    removed = cleanup_jobs(older_than_seconds=older_than_days * 24 * 3600)
    return {"ok": True, "removed": removed}


@router.post("/export_docx")
async def export_docx(authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_export_docx")
    json_path = Path("build") / "autoplan_generated.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="autoplan_generated.json not found")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    docx_files = []
    if isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
        for i, variant in enumerate(data["variants"]):
            out_docx = Path("build") / f"autoplan_generated_v{i + 1}.docx"
            export_autoplan_docx(variant, str(out_docx))
            docx_files.append(str(out_docx))
    else:
        out_docx = Path("build") / "autoplan_generated_v1.docx"
        export_autoplan_docx_from_file(str(json_path), str(out_docx))
        docx_files.append(str(out_docx))
    _audit("export_docx", user_id=user["id"], detail={"docx": docx_files})
    return {"ok": True, "docx": docx_files}


@router.post("/export_compare_docx")
async def export_compare_docx(v: int = 1, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_export_compare_docx")
    json_path = Path("build") / "autoplan_generated.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="autoplan_generated.json not found")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
        v = max(1, int(v or 1))
        data = data["variants"][v - 1] if v <= len(data["variants"]) else data["variants"][0]
    out_docx = Path("build") / f"autoplan_compare_v{v}.docx"
    export_autoplan_compare_docx(data, str(out_docx))
    _audit("export_compare_docx", user_id=user["id"], detail={"v": v, "docx": str(out_docx)})
    return {"ok": True, "docx": str(out_docx)}


@router.post("/export_compare_docx_all")
async def export_compare_docx_all(authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_export_compare_docx_all")
    json_path = Path("build") / "autoplan_generated.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="autoplan_generated.json not found")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
        docx_files = []
        for i, variant in enumerate(data["variants"]):
            out_docx = Path("build") / f"autoplan_compare_v{i + 1}.docx"
            export_autoplan_compare_docx(variant, str(out_docx))
            docx_files.append(str(out_docx))
        _audit("export_compare_docx_all", user_id=user["id"], detail={"docx": docx_files})
        return {"ok": True, "docx": docx_files}
    out_docx = Path("build") / "autoplan_compare_v1.docx"
    export_autoplan_compare_docx(data, str(out_docx))
    _audit("export_compare_docx_all", user_id=user["id"], detail={"docx": [str(out_docx)]})
    return {"ok": True, "docx": [str(out_docx)]}


@router.get("/download_docx")
async def download_docx(v: int = 1, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_download_docx")
    v = max(1, int(v or 1))
    out_docx = Path("build") / f"autoplan_generated_v{v}.docx"
    if not out_docx.exists():
        raise HTTPException(status_code=404, detail="docx not found")
    _audit("download_docx", user_id=user["id"], detail={"v": v, "path": str(out_docx)})
    return FileResponse(
        str(out_docx),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"autoplan_generated_v{v}.docx",
    )


@router.get("/download_compare_docx")
async def download_compare_docx(v: int = 1, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_download_compare_docx")
    v = max(1, int(v or 1))
    out_docx = Path("build") / f"autoplan_compare_v{v}.docx"
    if not out_docx.exists():
        raise HTTPException(status_code=404, detail="docx not found")
    _audit("download_compare_docx", user_id=user["id"], detail={"v": v, "path": str(out_docx)})
    return FileResponse(
        str(out_docx),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"autoplan_compare_v{v}.docx",
    )


@router.get("/download_compare_docx_all")
async def download_compare_docx_all(authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_download_compare_docx_all")
    from zipfile import ZipFile
    build_dir = Path("build")
    files = sorted(build_dir.glob("autoplan_compare_v*.docx"))
    if not files:
        raise HTTPException(status_code=404, detail="docx not found")
    zip_path = build_dir / "autoplan_compare_all.zip"
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass
    with ZipFile(str(zip_path), "w") as z:
        for p in files:
            z.write(p, arcname=p.name)
    _audit("download_compare_docx_all", user_id=user["id"], detail={"zip": str(zip_path)})
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="autoplan_compare_all.zip",
    )


@router.get("/compare_docx_versions")
async def compare_docx_versions(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    from pathlib import Path
    files = sorted(Path("build").glob("autoplan_compare_v*.docx"))
    versions = []
    for p in files:
        name = p.stem  # autoplan_compare_vX
        if "_v" in name:
            v = name.split("_v")[-1]
            if v.isdigit():
                versions.append(int(v))
    versions = sorted(set(versions))
    return {
        "ok": True,
        "versions": versions,
        "files": [f"autoplan_compare_v{v}.docx" for v in versions],
    }


@router.get("/job_list_fields")
async def job_list_fields(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    return {
        "ok": True,
        "default_fields": sorted(_job_list_default_fields()),
        "field_alias": {k: sorted(list(v)) for k, v in _job_list_field_alias().items()},
    }


@router.get("/audit")
async def audit_log(
    limit: int = 200,
    action: str | None = None,
    user_id: int | None = None,
    ts_after: str | None = None,
    ts_before: str | None = None,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = user_id
    if user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    items = _read_audit(limit=limit, action=action, user_id=uid, ts_after=ts_after, ts_before=ts_before)
    return {"ok": True, "items": items}


@router.get("/audit/summary")
async def audit_summary(
    limit: int = 10000,
    by_user: bool = False,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = None if _is_admin(authorization) else user["id"]
    summary = _audit_summary(limit=limit, user_id=uid, by_user=by_user and _is_admin(authorization))
    return {"ok": True, "summary": summary}


@router.get("/audit/stats")
async def audit_stats(
    days: int = 30,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = None if _is_admin(authorization) else user["id"]
    stats = _audit_stats_by_day(limit_days=days, user_id=uid)
    return {"ok": True, "stats": stats}


@router.post("/audit/query")
async def audit_query(req: AuditQueryRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    uid = req.user_id
    if req.user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    items = _read_audit(
        limit=req.limit,
        action=req.action,
        user_id=uid,
        ts_after=req.ts_after,
        ts_before=req.ts_before,
    )
    return {"ok": True, "items": items}


@router.get("/audit/export")
async def audit_export(
    fmt: str = "json",
    limit: int = 1000,
    action: str | None = None,
    user_id: int | None = None,
    ts_after: str | None = None,
    ts_before: str | None = None,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = user_id
    if user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    items = _read_audit(limit=limit, action=action, user_id=uid, ts_after=ts_after, ts_before=ts_before)
    fmt = (fmt or "json").lower()
    if fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="format must be json|csv")
    if fmt == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"ok": True, "items": items})
    # csv
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ts", "action", "user_id", "detail"])
    for it in items:
        writer.writerow([it.get("ts"), it.get("action"), it.get("user_id"), json.dumps(it.get("detail"), ensure_ascii=False)])
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_export.csv"},
    )


@router.get("/audit/export_xlsx")
async def audit_export_xlsx(
    limit: int = 1000,
    action: str | None = None,
    user_id: int | None = None,
    ts_after: str | None = None,
    ts_before: str | None = None,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = user_id
    if user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    items = _read_audit(limit=limit, action=action, user_id=uid, ts_after=ts_after, ts_before=ts_before)
    import io
    output = io.BytesIO()
    try:
        from openpyxl import Workbook
    except Exception:
        raise HTTPException(status_code=500, detail="openpyxl not installed")

    wb = Workbook()
    ws = wb.active
    ws.title = "audit"
    headers = ["ts", "action", "user_id", "detail"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for r, it in enumerate(items, start=2):
        ws.cell(row=r, column=1, value=it.get("ts"))
        ws.cell(row=r, column=2, value=it.get("action"))
        ws.cell(row=r, column=3, value=it.get("user_id"))
        ws.cell(row=r, column=4, value=json.dumps(it.get("detail"), ensure_ascii=False))
    wb.save(output)
    output.seek(0)
    from fastapi.responses import Response
    return Response(
        content=output.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=audit_export.xlsx"},
    )


@router.get("/audit/export_file_download")
async def audit_export_file_download(
    filename: str = "audit_export",
    user_id: int | None = None,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = user_id
    if user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    base_dir = Path("build") / "audit_exports" / str(uid or user["id"])
    json_path = base_dir / f"{filename}.json"
    csv_path = base_dir / f"{filename}.csv"
    xlsx_path = base_dir / f"{filename}.xlsx"
    if json_path.exists():
        return FileResponse(str(json_path), media_type="application/json", filename=f"{filename}.json")
    if csv_path.exists():
        return FileResponse(str(csv_path), media_type="text/csv", filename=f"{filename}.csv")
    if xlsx_path.exists():
        return FileResponse(
            str(xlsx_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{filename}.xlsx",
        )
    raise HTTPException(status_code=404, detail="export file not found")


@router.get("/audit/export_file_list")
async def audit_export_file_list(
    user_id: int | None = None,
    limit: int = 100,
    authorization: str | None = Header(default=None),
):
    user = _auth_user(authorization)
    uid = user_id
    if user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    base_dir = Path("build") / "audit_exports" / str(uid or user["id"])
    if not base_dir.exists():
        return {"ok": True, "files": []}
    files = sorted(base_dir.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for p in files[:limit]:
        items.append(
            {
                "name": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
        )
    return {"ok": True, "files": items}


@router.post("/audit/export_file_list")
async def audit_export_file_list_post(req: AuditExportListRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    uid = req.user_id
    if req.user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    base_dir = Path("build") / "audit_exports" / str(uid or user["id"])
    if not base_dir.exists():
        return {"ok": True, "files": []}
    files = sorted(base_dir.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    items = []
    for p in files[: req.limit]:
        items.append(
            {
                "name": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
        )
    return {"ok": True, "files": items}


@router.post("/audit/export_file_cleanup")
async def audit_export_file_cleanup(req: AuditExportCleanupRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    uid = req.user_id
    if req.user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    if req.older_than_days is None and req.keep_latest_n is None:
        raise HTTPException(status_code=400, detail="set older_than_days or keep_latest_n")
    import time
    base_dir = Path("build") / "audit_exports" / str(uid or user["id"])
    if not base_dir.exists():
        return {"ok": True, "removed": 0}
    files = sorted(base_dir.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    removed = 0
    now = time.time()
    if req.older_than_days is not None:
        threshold = now - req.older_than_days * 86400
        for p in files:
            if p.stat().st_mtime < threshold:
                try:
                    p.unlink()
                    removed += 1
                except Exception:
                    pass
    if req.keep_latest_n is not None and req.keep_latest_n >= 0:
        for p in files[req.keep_latest_n:]:
            try:
                if p.exists():
                    p.unlink()
                    removed += 1
            except Exception:
                pass
    return {"ok": True, "removed": removed}


@router.post("/audit/export_file")
async def audit_export_file(req: AuditExportRequest, authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    uid = req.user_id
    if req.user_id is not None and not _is_admin(authorization):
        raise HTTPException(status_code=403, detail="forbidden")
    if uid is None and not _is_admin(authorization):
        uid = user["id"]
    items = _read_audit(
        limit=req.limit,
        action=req.action,
        user_id=uid,
        ts_after=req.ts_after,
        ts_before=req.ts_before,
    )
    fmt = (req.fmt or "json").lower()
    if fmt not in ("json", "csv", "xlsx"):
        raise HTTPException(status_code=400, detail="format must be json|csv|xlsx")
    build_dir = Path("build") / "audit_exports" / str(uid or user["id"])
    build_dir.mkdir(parents=True, exist_ok=True)
    base_name = req.filename or "audit_export"
    if fmt == "json":
        out_path = build_dir / f"{base_name}.json"
        out_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "file": str(out_path)}
    if fmt == "csv":
        import csv
        out_path = build_dir / f"{base_name}.csv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ts", "action", "user_id", "detail"])
            for it in items:
                writer.writerow([it.get("ts"), it.get("action"), it.get("user_id"), json.dumps(it.get("detail"), ensure_ascii=False)])
        return {"ok": True, "file": str(out_path)}
    # xlsx
    out_path = build_dir / f"{base_name}.xlsx"
    try:
        from openpyxl import Workbook
    except Exception:
        raise HTTPException(status_code=500, detail="openpyxl not installed")
    wb = Workbook()
    ws = wb.active
    ws.title = "audit"
    headers = ["ts", "action", "user_id", "detail"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=1, column=c, value=h)
    for r, it in enumerate(items, start=2):
        ws.cell(row=r, column=1, value=it.get("ts"))
        ws.cell(row=r, column=2, value=it.get("action"))
        ws.cell(row=r, column=3, value=it.get("user_id"))
        ws.cell(row=r, column=4, value=json.dumps(it.get("detail"), ensure_ascii=False))
    wb.save(str(out_path))
    return {"ok": True, "file": str(out_path)}


@router.get("/download_docx_all")
async def download_docx_all(authorization: str | None = Header(default=None)):
    user = _auth_user(authorization)
    _charge(user, COST_PER_JOB, "autoplan_download_docx_all")
    from zipfile import ZipFile
    build_dir = Path("build")
    files = sorted(build_dir.glob("autoplan_generated_v*.docx"))
    if not files:
        raise HTTPException(status_code=404, detail="docx not found")
    zip_path = build_dir / "autoplan_generated_all.zip"
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass
    with ZipFile(str(zip_path), "w") as z:
        for p in files:
            z.write(p, arcname=p.name)
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename="autoplan_generated_all.zip",
    )


@router.get("/docx_versions")
async def docx_versions(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    from pathlib import Path
    files = sorted(Path("build").glob("autoplan_generated_v*.docx"))
    versions = []
    for p in files:
        name = p.stem  # autoplan_generated_vX
        if "_v" in name:
            v = name.split("_v")[-1]
            if v.isdigit():
                versions.append(int(v))
    versions = sorted(set(versions))
    return {
        "ok": True,
        "versions": versions,
        "files": [f"autoplan_generated_v{v}.docx" for v in versions],
    }


@router.get("/generate_status")
async def generate_status(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    json_path = Path("build") / "autoplan_generated.json"
    v1_path = Path("build") / "autoplan_generated_v1.docx"
    any_docx = sorted(Path("build").glob("autoplan_generated_v*.docx"))
    status = {
        "json_exists": json_path.exists(),
        "docx_exists": bool(any_docx),
        "json_mtime": json_path.stat().st_mtime if json_path.exists() else None,
        "docx_mtime": v1_path.stat().st_mtime if v1_path.exists() else (any_docx[0].stat().st_mtime if any_docx else None),
        "docx_versions": [p.name for p in any_docx],
    }
    return {"ok": True, "status": status}


@router.get("/check")
async def check_generated(authorization: str | None = Header(default=None)):
    _ = _auth_user(authorization)
    json_path = Path("build") / "autoplan_generated.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="autoplan_generated.json not found")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
        return {"ok": True, "quality": [v.get("quality_checks") for v in data["variants"]]}
    return {"ok": True, "quality": data.get("quality_checks")}
