from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import FileResponse

from backend.zhifei_autoplan.exporter import export_autoplan_compare_docx, export_autoplan_docx, export_autoplan_focus_xlsx
from backend.zhifei_autoplan.job_store import create_job, get_job, update_job
from backend.zhifei_autoplan.orchestrator import run_autoplan
from backend.zhifei_autoplan.plan_store import load_plan, save_plan
from backend.zhifei_autoplan.parsers.tender_parser import TenderParser
from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.tender_store import save_tender_matrix
from backend.zhifei_autoplan.boq_store import save_boq_data
from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.quality_check import run_quality_checks, strip_nonconcrete_language
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.media import generate_boq_chart, generate_ingested_previews, generate_outline_mindmap
from backend.zhifei_autoplan.params_runtime import load_params, get_image_defaults, save_params
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids


router = APIRouter(prefix="/actions", tags=["Actions Bridge"])


def _auth_actions_key(x_actions_key: str | None):
    expected = os.environ.get("ZF_ACTIONS_KEY", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="actions key not configured")
    if (x_actions_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="invalid actions key")


class ActionsGenerateRequest(BaseModel):
    topic: str
    project_id: str | None = None
    project_type: str | None = None
    outline: List[str] = []
    requirements: List[str] = []
    global_instruction: str | None = None
    chapter_requirements: dict | None = None
    provider: str | None = None
    model: str | None = None
    providers: List[str] = []
    model_map: dict | None = None
    style: dict | None = None
    variants: int = 1
    chapter_pages: dict | None = None
    quality_strict: bool | None = True
    auto_remediate: bool = True
    remediate_mode: str = "template"
    compare_mode: str = "summary"
    compare_max_chars: int = 1200
    compare_titles: list[str] | None = None
    api_key: str | None = None
    api_keys: dict | None = None
    base_url: str | None = None
    secret_key: str | None = None
    token_url: str | None = None
    dry_run: bool = False
    generate_images: bool = True
    # Images / mindmap (prefer Gemini "banana" model)
    image_provider: str | None = None
    image_model: str | None = None
    image_aspect_ratio: str | None = None
    image_api_key: str | None = None
    bidder_company: str | None = None
    bidder_domain: str | None = None
    logo_url: str | None = None
    # Per-run editable parameter overrides (do not persist). Example:
    # {"qse_defaults": {"PM10阈值": "≤120ug/m3"}, "quant_defaults": {"频次": "3次/日"}}
    params_override: dict | None = None


class ActionsPlanRequest(BaseModel):
    outline: List[str]
    style: dict = {}
    project_type: str | None = None
    global_instruction: str | None = None
    variants: int = 1
    chapter_requirements: dict = {}
    chapter_pages: dict = {}
    quality_strict: bool = True
    auto_remediate: bool = True
    remediate_mode: str = "template"
    compare_mode: str = "summary"
    compare_max_chars: int = 1200
    compare_titles: list[str] | None = None


class ActionsSection(BaseModel):
    title: str
    content: str
    agent_role: str | None = None


class ActionsQualityCheckRequest(BaseModel):
    project_id: str | None = None
    outline: List[str] = []
    sections: List[ActionsSection]
    strict: bool = True


class ActionsExportRequest(BaseModel):
    topic: str
    project_id: str | None = None
    style: dict | None = None
    outline: List[str] = []
    sections: List[ActionsSection]
    quality_checks: dict | None = None
    generate_images: bool = True
    # Images / mindmap (prefer Gemini "banana" model)
    image_provider: str | None = None
    image_model: str | None = None
    image_aspect_ratio: str | None = None
    image_api_key: str | None = None
    bidder_company: str | None = None
    bidder_domain: str | None = None
    logo_url: str | None = None


class ActionsParamsSetRequest(BaseModel):
    update: dict
    merge: bool = True


class ActionsParamsDiffRequest(BaseModel):
    update: dict
    merge: bool = True


class ActionsJobCancelRequest(BaseModel):
    job_id: str


class ActionsReviewDecision(BaseModel):
    issue_id: str
    apply: bool = True
    replacement: str | None = None


class ActionsReviewApplyRequest(BaseModel):
    job_id: str
    variant: int = 1
    apply_all: bool = False
    decisions: List[ActionsReviewDecision] = []


@router.get("/params/get")
async def actions_params_get(x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    return {"ok": True, "params": load_params()}


@router.post("/params/set")
async def actions_params_set(req: ActionsParamsSetRequest, project_id: str | None = None, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    before = load_params()
    path = save_params(req.update, merge=bool(req.merge))
    after = load_params()
    diff = None
    try:
        from backend.zhifei_autoplan.param_trace import load_latest_receipt, diff_params_with_receipt

        diff = diff_params_with_receipt(before, after, load_latest_receipt(project_id=project_id))
    except Exception:
        diff = None
    return {"ok": True, "saved_at": path, "params": after, "diff": diff}


@router.post("/params/diff")
async def actions_params_diff(req: ActionsParamsDiffRequest, project_id: str | None = None, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    before = load_params()
    update = req.update if isinstance(req.update, dict) else {}
    merge = bool(req.merge)
    # Preview merge without persisting.
    if merge:
        after = dict(before)
        for k, v in update.items():
            if isinstance(v, dict) and isinstance(after.get(k), dict):
                merged = dict(after.get(k) or {})
                merged.update(v)
                after[k] = merged
            else:
                after[k] = v
    else:
        after = update
    diff = None
    try:
        from backend.zhifei_autoplan.param_trace import load_latest_receipt, diff_params_with_receipt

        diff = diff_params_with_receipt(before, after, load_latest_receipt(project_id=project_id))
    except Exception:
        diff = None
    return {"ok": True, "before": before, "after": after, "diff": diff}


@router.get("/params/receipt/get")
async def actions_params_receipt_get(project_id: str | None = None, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    try:
        from backend.zhifei_autoplan.param_trace import load_latest_receipt

        receipt = load_latest_receipt(project_id=project_id) or {}
        return {"ok": True, "receipt": receipt}
    except Exception as e:
        return {"ok": False, "error": repr(e), "receipt": {}}


async def _save_upload(uf: UploadFile) -> str:
    data = await uf.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"empty file: {uf.filename}")
    suffix = f"_{uf.filename}" if uf.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(data)
        return f.name


def _safe_project_scope(raw: str | None) -> str | None:
    s = str(raw or "").strip()
    if not s:
        return None
    s = re.sub(r"[^A-Za-z0-9_\-\.\u4e00-\u9fff]+", "_", s).strip("_")
    return s[:96] or None


def _merge_plan_defaults(payload: dict) -> dict:
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
        payload["compare_mode"] = plan.get("compare_mode", "summary")
    if payload.get("compare_max_chars") is None:
        payload["compare_max_chars"] = plan.get("compare_max_chars", 1200)
    if payload.get("compare_titles") is None:
        payload["compare_titles"] = plan.get("compare_titles")
    if not payload.get("variants"):
        payload["variants"] = plan.get("variants") or 1
    if not payload.get("project_type"):
        payload["project_type"] = plan.get("project_type")
    if payload.get("global_instruction") is None:
        payload["global_instruction"] = plan.get("global_instruction")
    return payload


def _save_outputs(base_name: str, results: list[dict]) -> dict:
    build_dir = Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    out_json = build_dir / f"{base_name}.json"
    out_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    docx_files = []
    compare_files = []
    focus_xlsx_files = []
    for i, variant in enumerate(results):
        out_docx = build_dir / f"{base_name}_v{i + 1}.docx"
        export_autoplan_docx(variant, str(out_docx))
        docx_files.append(str(out_docx))
        out_compare = build_dir / f"{base_name}_compare_v{i + 1}.docx"
        export_autoplan_compare_docx(variant, str(out_compare))
        compare_files.append(str(out_compare))
        out_focus = build_dir / f"{base_name}_focus_v{i + 1}.xlsx"
        try:
            focus_path = export_autoplan_focus_xlsx(variant, str(out_focus))
        except Exception:
            focus_path = ""
        focus_xlsx_files.append(str(focus_path) if focus_path else None)
    return {"json": str(out_json), "docx": docx_files, "compare_docx": compare_files, "focus_xlsx": focus_xlsx_files}


def _rebuild_postprocessed_artifacts(
    results: list[dict],
    *,
    payload: dict,
    report: dict | None,
    params: dict | None,
) -> None:
    """
    When we modify section text after `run_autoplan` (e.g., diversity autofix),
    we must rebuild derived artifacts so exports/quality gates reflect the final content:
    - plan consistency receipt (工期/资源峰值/关键线路间隔)
    - editable param receipt (param_trace)
    - quality checks (including chapter blueprints gate)
    - cross_index (BoQ focus closure table)
    """
    pid = str(payload.get("project_id") or "").strip() or None
    strict = bool(payload.get("quality_strict", True))

    # Load latest tender/boq for this project scope (best-effort).
    tender = load_tender_matrix(project_id=pid) or {}
    boq = load_boq_data(project_id=pid) or {}
    base_focus = _build_boq_focus(boq)

    # Params are used for param_trace placeholder substitution.
    if not isinstance(params, dict):
        params = load_params()
        overrides = payload.get("params_override")
        if isinstance(overrides, dict) and overrides:
            for k, v in overrides.items():
                if isinstance(v, dict) and isinstance(params.get(k), dict):
                    merged = dict(params.get(k) or {})
                    merged.update(v)
                    params[k] = merged
                else:
                    params[k] = v

    # Keep four-new recommendations available for downstream remediation/export (best-effort).
    try:
        outline_base = payload.get("outline") if isinstance(payload.get("outline"), list) else []
        recs = recommend_four_new(boq, outline=outline_base, limit=6, topic=str(payload.get("topic") or ""))
        if isinstance(recs, list) and recs:
            base_focus["four_new_recommendations"] = recs
    except Exception:
        pass

    # Normalize per-variant derived artifacts.
    for v in results:
        if not isinstance(v, dict):
            continue
        sections = v.get("sections") if isinstance(v.get("sections"), list) else []
        outline = v.get("outline") if isinstance(v.get("outline"), list) and v.get("outline") else []
        if not outline:
            outline = [str(s.get("title") or "").strip() for s in sections if isinstance(s, dict) and str(s.get("title") or "").strip()]

        boq_focus = v.get("boq_focus") if isinstance(v.get("boq_focus"), dict) else base_focus
        if isinstance(boq_focus, dict) and isinstance(base_focus.get("four_new_recommendations"), list):
            if not isinstance(boq_focus.get("four_new_recommendations"), list):
                merged = dict(boq_focus)
                merged["four_new_recommendations"] = base_focus.get("four_new_recommendations") or []
                boq_focus = merged
                v["boq_focus"] = merged

        # Plan consistency normalization (in-place section edits).
        try:
            from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections

            v["plan_consistency"] = normalize_metrics_in_sections(sections)
        except Exception:
            pass

        # Param trace receipt (in-place placeholder substitution).
        try:
            from backend.zhifei_autoplan.param_trace import build_param_receipt, save_latest_receipt

            receipt = build_param_receipt(sections, params)
            saved_at = save_latest_receipt(receipt, project_id=str(pid) if pid else None)
            v["param_trace"] = {"ok": True, "saved_at": saved_at, "receipt": receipt}
        except Exception:
            pass

        # Recompute quality checks for final content (deterministic; no LLM calls).
        qc = run_quality_checks(
            tender,
            outline,
            sections,
            boq=boq,
            boq_focus=boq_focus,
            project_id=pid,
            strict=strict,
        )

        # Variant diversity report is computed cross-variant; re-attach it after QC rebuild.
        if isinstance(report, dict) and int(report.get("variant_count") or 0) >= 2:
            v["variant_similarity"] = report
            qc["variant_diversity"] = {
                "ok": bool(report.get("ok")),
                "avg_max_similarity": report.get("avg_max_similarity"),
                "avg_max_similarity_all": report.get("avg_max_similarity_all"),
                "flagged_count": report.get("flagged_count"),
                "relaxed_flagged_count": report.get("relaxed_flagged_count"),
                "chapter_threshold": report.get("chapter_threshold"),
                "relaxed_chapter_threshold": report.get("relaxed_chapter_threshold"),
                "overall_threshold": report.get("overall_threshold"),
                "flagged": report.get("flagged") or [],
                "relaxed_flagged": report.get("relaxed_flagged") or [],
            }
            if report.get("ok") is False:
                issue_list = qc.setdefault("issue_list", [])
                auto_recs = qc.setdefault("auto_revision_suggestions", [])
                for f in (report.get("flagged") or [])[:10]:
                    title = str(f.get("title") or "").strip() or "章节"
                    pair = str(f.get("pair") or "").strip() or "pair"
                    sim = f.get("similarity")
                    s_sim = str(sim) if sim is not None else ""
                    msg = (
                        f"多方案相似度过高：{pair}={s_sim}。要求：不改招标目录，仅重写本章章内逻辑；"
                        "强制使用模版锚点标题（A=交付物/约束/步骤/闭环，B=工序流程/控制点表/资源节拍，C=指标矩阵/人机料法环/闭环分组），"
                        "并把同类条目改为“清单项控制卡/闭环卡片/指标矩阵”短句结构，避免段落复述。"
                    )
                    issue_list.append(
                        {
                            "severity": "high",
                            "title": title,
                            "type": "variant_diversity_gap",
                            "problem": msg,
                            "suggestion": msg,
                        }
                    )
                    auto_recs.append({"title": title, "type": "variant_diversity_gap", "suggestion": msg})

        v["quality_checks"] = qc

        # Cross-index rebuild (depends on latest qc + final section text).
        try:
            from backend.zhifei_autoplan.cross_index import build_cross_index

            drawing_index = v.get("drawing_index") if isinstance(v.get("drawing_index"), dict) else None
            standard_index = v.get("standard_index") if isinstance(v.get("standard_index"), dict) else None
            v["cross_index"] = build_cross_index(
                boq=boq,
                sections=sections,
                boq_focus=boq_focus,
                drawing_index=drawing_index,
                standard_index=standard_index,
                quality_checks=qc,
                project_id=pid,
            )
        except Exception:
            pass


def _load_done_job_variants(job_id: str) -> tuple[dict, dict, dict, list]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if str(job.get("status") or "").strip() != "done":
        raise HTTPException(status_code=409, detail=f"job not done: {job.get('status')}")
    result = job.get("result") or {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        raise HTTPException(status_code=404, detail="result json not found")
    data = json.loads(Path(json_path).read_text(encoding="utf-8", errors="ignore"))
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []
    if not variants:
        raise HTTPException(status_code=404, detail="empty result variants")
    return job, result, data, variants


def _review_items_for_variant(variant_rec: dict, *, max_excerpt: int = 320) -> list[dict]:
    qc = variant_rec.get("quality_checks") if isinstance(variant_rec.get("quality_checks"), dict) else {}
    issues = qc.get("issue_list") if isinstance(qc.get("issue_list"), list) else []
    recs = qc.get("auto_revision_suggestions") if isinstance(qc.get("auto_revision_suggestions"), list) else []
    sections = variant_rec.get("sections") if isinstance(variant_rec.get("sections"), list) else []

    title_to_excerpt: Dict[str, str] = {}
    for s in sections:
        if not isinstance(s, dict):
            continue
        t = str(s.get("title") or "").strip()
        if not t or t in title_to_excerpt:
            continue
        c = str(s.get("content") or "").strip()
        title_to_excerpt[t] = c[:max_excerpt] + ("..." if len(c) > max_excerpt else "")

    out: list[dict] = []
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    for i, it in enumerate(issues, start=1):
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip() or "章节"
        source = "issue_list"
        issue_id = f"I{i:04d}"
        out.append(
            {
                "issue_id": issue_id,
                "source": source,
                "title": title,
                "type": str(it.get("type") or "issue"),
                "severity": str(it.get("severity") or "medium"),
                "severity_rank": severity_rank.get(str(it.get("severity") or "").lower(), 2),
                "problem": str(it.get("problem") or ""),
                "suggestion": str(it.get("suggestion") or ""),
                "section_excerpt": title_to_excerpt.get(title, ""),
                "apply": True,
                "replacement": "",
            }
        )

    # Add recs not already covered by issue_list.
    seen = {(str(x.get("title")), str(x.get("type")), str(x.get("suggestion"))) for x in out}
    rid = 0
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        title = str(rec.get("title") or "").strip() or "章节"
        rtype = str(rec.get("type") or "issue")
        sugg = str(rec.get("suggestion") or "")
        key = (title, rtype, sugg)
        if key in seen:
            continue
        seen.add(key)
        rid += 1
        out.append(
            {
                "issue_id": f"R{rid:04d}",
                "source": "auto_revision_suggestions",
                "title": title,
                "type": rtype,
                "severity": "medium",
                "severity_rank": 2,
                "problem": "",
                "suggestion": sugg,
                "section_excerpt": title_to_excerpt.get(title, ""),
                "apply": True,
                "replacement": "",
            }
        )
    out.sort(key=lambda x: (-int(x.get("severity_rank") or 0), str(x.get("title") or ""), str(x.get("type") or "")))
    return out


@router.post("/plan/save")
async def actions_plan_save(req: ActionsPlanRequest, project_id: str | None = None, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    path = save_plan(req.model_dump(), project_id=project_id)
    return {"ok": True, "saved_at": path}


@router.get("/plan/get")
async def actions_plan_get(project_id: str | None = None, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    return {"ok": True, "plan": load_plan(project_id=project_id) or {}}


@router.post("/tender/parse")
async def actions_tender_parse(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    if not files:
        raise HTTPException(status_code=400, detail="no files")
    paths = await asyncio.gather(*[_save_upload(f) for f in files])
    parser = TenderParser()
    matrix = await parser.parse(paths)
    matrix_dict = matrix.model_dump()
    parsed_code = _safe_project_scope(matrix_dict.get("project_code"))
    parsed_name = str(matrix_dict.get("project_name") or "").strip() or None
    requested_pid = _safe_project_scope(project_id)
    resolved_project_id = parsed_code or requested_pid
    if not resolved_project_id and parsed_name:
        resolved_project_id = _safe_project_scope(parsed_name)
    saved_at = save_tender_matrix(matrix_dict, project_id=resolved_project_id)
    return {
        "ok": True,
        "matrix": matrix_dict,
        "project_id": resolved_project_id,
        "project_name": parsed_name,
        "project_code": parsed_code,
        "saved_at": saved_at,
    }


@router.post("/boq/parse")
async def actions_boq_parse(
    file: List[UploadFile] = File(...),
    project_id: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    if not file:
        raise HTTPException(status_code=400, detail="no file")
    paths = await asyncio.gather(*[_save_upload(f) for f in file])
    parser = BoQParser()
    merged_items = []
    for p in paths:
        items, _ = await parser.parse(p)
        merged_items.extend(items)
    stats = parser._calc_stats(merged_items)
    payload = {"items": [it.model_dump() for it in merged_items], "stats": stats, "source_file_count": len(paths)}
    saved_at = save_boq_data(payload, project_id=project_id)
    return {**payload, "ok": True, "saved_at": saved_at}


@router.post("/quality_check")
async def actions_quality_check(req: ActionsQualityCheckRequest, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    pid = str(req.project_id or "").strip() or None
    tender = load_tender_matrix(project_id=pid) or {}
    boq = load_boq_data(project_id=pid) or {}
    boq_focus = _build_boq_focus(boq)
    # Four-new recommendations for better "四新技术" realism and review.
    try:
        outline = req.outline or [s.title for s in req.sections]
        recs = recommend_four_new(boq, outline=outline, limit=6)
        if isinstance(recs, list) and recs:
            boq_focus["four_new_recommendations"] = recs
    except Exception:
        pass
    sections = [s.model_dump() for s in req.sections]
    qc = run_quality_checks(
        tender,
        req.outline or [s.get("title") for s in sections],
        sections,
        boq=boq,
        boq_focus=boq_focus,
        project_id=pid,
        strict=bool(req.strict),
    )
    return {"ok": True, "boq_focus": boq_focus, "quality_checks": qc}


@router.post("/export_docx")
async def actions_export_docx(req: ActionsExportRequest, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    pid = str(req.project_id or "").strip() or None
    tender = load_tender_matrix(project_id=pid) or {}
    boq = load_boq_data(project_id=pid) or {}
    boq_focus = _build_boq_focus(boq)
    params = load_params()
    sections = [s.model_dump() for s in req.sections]
    for s in sections:
        s["content"] = strip_nonconcrete_language(s.get("content") or "")
    plan_receipt = None
    try:
        from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections

        plan_receipt = normalize_metrics_in_sections(sections)
    except Exception:
        plan_receipt = None
    outline = req.outline or [s.get("title") for s in sections]
    # Four-new recommendations for realism (used by focus_xlsx + downstream remediation).
    try:
        recs = recommend_four_new(boq, outline=outline, limit=6, topic=str(req.topic))
        if isinstance(recs, list) and recs:
            boq_focus["four_new_recommendations"] = recs
    except Exception:
        pass
    qc = run_quality_checks(
        tender,
        outline,
        sections,
        boq=boq,
        boq_focus=boq_focus,
        project_id=pid,
        strict=True,
    )
    # Drawing/standard index + cross-index for reviewer XLSX (best-effort).
    drawing_index = None
    standard_index = None
    cross_index = None
    try:
        from backend.zhifei_autoplan.drawing_index import build_drawing_index
        from backend.zhifei_autoplan.standard_index import build_standard_index
        from backend.zhifei_autoplan.cross_index import build_cross_index

        drawing_index = build_drawing_index(req.topic, outline, project_id=pid)
        standard_index = build_standard_index(req.topic, outline, project_id=pid)
        cross_index = build_cross_index(
            boq=boq,
            sections=sections,
            boq_focus=boq_focus,
            drawing_index=drawing_index,
            standard_index=standard_index,
            quality_checks=qc,
            project_id=pid,
        )
    except Exception:
        drawing_index = None
        standard_index = None
        cross_index = None
    payload = {
        "topic": req.topic,
        "style": req.style or {},
        "outline": outline,
        "sections": sections,
        "quality_checks": qc,
        "boq_focus": boq_focus,
        "drawing_index": drawing_index,
        "standard_index": standard_index,
        "cross_index": cross_index,
        "plan_consistency": plan_receipt,
    }
    if bool(req.generate_images):
        stats = boq.get("stats") if isinstance(boq, dict) else None
        media = []
        if stats:
            media.extend(generate_boq_chart(stats))
        media.extend(generate_ingested_previews(limit=6, project_id=pid))
        # Mindmap (prefer Gemini "banana" image model when key is configured)
        try:
            img_defaults = get_image_defaults(params)
            image_provider = (req.image_provider or img_defaults.get("provider") or "").strip()
            image_model = (req.image_model or img_defaults.get("model") or "").strip()
            aspect_ratio = (req.image_aspect_ratio or img_defaults.get("aspect_ratio") or "16:9").strip()
            image_api_key = req.image_api_key or os.environ.get("ZF_GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            # Resolve bidder logo once; embed it into DOCX and pass into mindmap generation if possible.
            logo_embed = None
            logo_raw_path = None
            try:
                from backend.zhifei_autoplan.logo_runtime import resolve_logo, prepare_logo_for_embedding

                # Resolve when bidder info is provided OR project_id is set (so we can scope to this project).
                if req.bidder_company or req.logo_url or req.bidder_domain or pid:
                    logo_raw = resolve_logo(
                        bidder_company=req.bidder_company,
                        logo_url=req.logo_url,
                        bidder_domain=req.bidder_domain,
                        project_id=pid,
                    )
                    if logo_raw:
                        logo_raw_path = str(logo_raw)
                        logo_embed = prepare_logo_for_embedding(logo_raw) or None
            except Exception:
                logo_embed = None
            if logo_embed:
                media.append({"path": logo_embed, "caption": "投标单位LOGO"})
                # Lock branding to this project to avoid mis-grabs across reruns.
                try:
                    if pid:
                        from backend.zhifei_autoplan.branding_store import update_branding

                        update_branding(
                            str(pid),
                            {
                                "bidder_company": req.bidder_company,
                                "bidder_domain": req.bidder_domain,
                                "logo_url": req.logo_url,
                                "logo_raw_path": logo_raw_path,
                                "logo_embed_path": str(logo_embed),
                                "logo_path": str(logo_embed),
                            },
                            merge=True,
                        )
                except Exception:
                    pass
            mm = None
            if image_provider == "google":
                mm = generate_outline_mindmap(
                    req.topic,
                    outline,
                    api_key=image_api_key,
                    model=image_model,
                    aspect_ratio=aspect_ratio,
                    logo_path=logo_embed,
                    bidder_company=req.bidder_company,
                    logo_url=req.logo_url,
                    bidder_domain=req.bidder_domain,
                )
            if mm:
                media.append(mm)
        except Exception:
            pass
        if media:
            payload["media"] = media
    job_id = create_job({"action": "export_docx"}, user_id=None)
    outputs = _save_outputs(f"actions_export_{job_id}", [payload])
    update_job(job_id, status="done", result=outputs)
    return {"ok": True, "job_id": job_id, "files": outputs}


@router.post("/generate")
async def actions_generate(req: ActionsGenerateRequest, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    payload = _merge_plan_defaults(req.model_dump())
    variants = int(payload.get("variants") or 1)
    variant_ids = reserve_variant_ids(
        project_id=str(payload.get("project_id") or "").strip() or None,
        count=max(1, variants),
        explicit_variant_id=payload.get("variant_id"),
        explicit_template_id=payload.get("logic_template_id") or payload.get("logic_template"),
    )
    results = []
    for vid in variant_ids:
        payload["variant_id"] = int(vid)
        results.append(await run_autoplan(payload))
    # Cross-variant similarity (anti-paraphrase diversity gate). Best-effort; does not change outline.
    if len(results) >= 2:
        try:
            from backend.zhifei_autoplan.variant_similarity import compute_variant_similarity
            from backend.zhifei_autoplan.diversity_autofix import apply_diversity_autofix

            params = load_params()
            overrides = payload.get("params_override")
            if isinstance(overrides, dict) and overrides:
                for k, v in overrides.items():
                    if isinstance(v, dict) and isinstance(params.get(k), dict):
                        merged = dict(params.get(k) or {})
                        merged.update(v)
                        params[k] = merged
                    else:
                        params[k] = v
            div_cfg = params.get("variant_diversity") if isinstance(params.get("variant_diversity"), dict) else {}
            def _run_report():
                return compute_variant_similarity(
                    results,
                    chapter_threshold=float(div_cfg.get("chapter_threshold") or 0.90),
                    overall_threshold=float(div_cfg.get("overall_threshold") or 0.85),
                    min_chars=int(div_cfg.get("min_chars") or 800),
                    ignore_title_keywords=(div_cfg.get("ignore_title_keywords") if isinstance(div_cfg.get("ignore_title_keywords"), list) else None),
                    relaxed_title_keywords=(div_cfg.get("relaxed_title_keywords") if isinstance(div_cfg.get("relaxed_title_keywords"), list) else None),
                    relaxed_chapter_threshold=(float(div_cfg.get("relaxed_chapter_threshold")) if div_cfg.get("relaxed_chapter_threshold") is not None else None),
                )

            report = _run_report()

            # Auto-fix: reshape only flagged chapters (do not change tender outline).
            # This is deterministic and avoids "换词" by switching to A/B/C structural blocks.
            max_rounds = int(div_cfg.get("auto_fix_rounds") or 1)
            if max_rounds < 0:
                max_rounds = 0
            rounds = 0
            while rounds < max_rounds and report.get("ok") is False and report.get("flagged"):
                changed_any = False
                for f in (report.get("flagged") or [])[:24]:
                    title = str(f.get("title") or "").strip()
                    pair = str(f.get("pair") or "").strip()
                    m = re.match(r"^v(\\d+)_v(\\d+)$", pair)
                    if not m or not title:
                        continue
                    a = int(m.group(1))
                    b = int(m.group(2))
                    # Rewrite the later variant in the max-sim pair.
                    target_idx = max(a, b)
                    if target_idx <= 1 or target_idx > len(results):
                        continue
                    target = results[target_idx - 1]
                    secs = target.get("sections") if isinstance(target, dict) else None
                    if not isinstance(secs, list):
                        continue
                    for sec in secs:
                        if not isinstance(sec, dict):
                            continue
                        if str(sec.get("title") or "").strip() != title:
                            continue
                        if apply_diversity_autofix(sec, params=params, evidence_hint=str(pair)):
                            changed_any = True
                        break
                if not changed_any:
                    break
                # Recompute report after patching
                report = _run_report()
                rounds += 1

            _rebuild_postprocessed_artifacts(results, payload=payload, report=report, params=params)
        except Exception:
            pass
    outputs = _save_outputs("actions_generated", results)
    quality = [v.get("quality_checks") for v in results]
    return {"ok": True, "result": results, "quality": quality, "files": outputs}


@router.post("/generate_async")
async def actions_generate_async(
    req: ActionsGenerateRequest,
    background_tasks: BackgroundTasks,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    payload = _merge_plan_defaults(req.model_dump())
    variants = int(payload.get("variants") or 1)
    payload["_variant_ids"] = reserve_variant_ids(
        project_id=str(payload.get("project_id") or "").strip() or None,
        count=max(1, variants),
        explicit_variant_id=payload.get("variant_id"),
        explicit_template_id=payload.get("logic_template_id") or payload.get("logic_template"),
    )
    job_id = create_job(payload, user_id=None)

    def _run_job(_job_id: str, _payload: dict):
        try:
            local_payload = json.loads(json.dumps(_payload))
            def _is_cancelled() -> bool:
                j = get_job(_job_id) or {}
                return str(j.get("status") or "").strip().lower() == "cancelled"

            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user")
                return
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
                if _is_cancelled():
                    update_job(_job_id, status="cancelled", error="cancelled_by_user")
                    return
                local_payload["variant_id"] = int(vid)
                results.append(asyncio.run(run_autoplan(local_payload)))
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user")
                return
            # Cross-variant similarity (anti-paraphrase diversity gate). Best-effort.
            if len(results) >= 2:
                try:
                    from backend.zhifei_autoplan.variant_similarity import compute_variant_similarity
                    from backend.zhifei_autoplan.diversity_autofix import apply_diversity_autofix

                    params = load_params()
                    overrides = local_payload.get("params_override")
                    if isinstance(overrides, dict) and overrides:
                        for k, v in overrides.items():
                            if isinstance(v, dict) and isinstance(params.get(k), dict):
                                merged = dict(params.get(k) or {})
                                merged.update(v)
                                params[k] = merged
                            else:
                                params[k] = v
                    div_cfg = params.get("variant_diversity") if isinstance(params.get("variant_diversity"), dict) else {}
                    def _run_report():
                        return compute_variant_similarity(
                            results,
                            chapter_threshold=float(div_cfg.get("chapter_threshold") or 0.90),
                            overall_threshold=float(div_cfg.get("overall_threshold") or 0.85),
                            min_chars=int(div_cfg.get("min_chars") or 800),
                            ignore_title_keywords=(div_cfg.get("ignore_title_keywords") if isinstance(div_cfg.get("ignore_title_keywords"), list) else None),
                            relaxed_title_keywords=(div_cfg.get("relaxed_title_keywords") if isinstance(div_cfg.get("relaxed_title_keywords"), list) else None),
                            relaxed_chapter_threshold=(float(div_cfg.get("relaxed_chapter_threshold")) if div_cfg.get("relaxed_chapter_threshold") is not None else None),
                        )

                    report = _run_report()

                    # Auto-fix: deterministic reshape for flagged chapters (do not change tender outline).
                    max_rounds = int(div_cfg.get("auto_fix_rounds") or 1)
                    if max_rounds < 0:
                        max_rounds = 0
                    rounds = 0
                    while rounds < max_rounds and report.get("ok") is False and report.get("flagged"):
                        changed_any = False
                        for f in (report.get("flagged") or [])[:24]:
                            title = str(f.get("title") or "").strip()
                            pair = str(f.get("pair") or "").strip()
                            m = re.match(r"^v(\\d+)_v(\\d+)$", pair)
                            if not m or not title:
                                continue
                            a = int(m.group(1))
                            b = int(m.group(2))
                            target_idx = max(a, b)
                            if target_idx <= 1 or target_idx > len(results):
                                continue
                            target = results[target_idx - 1]
                            secs = target.get("sections") if isinstance(target, dict) else None
                            if not isinstance(secs, list):
                                continue
                            for sec in secs:
                                if not isinstance(sec, dict):
                                    continue
                                if str(sec.get("title") or "").strip() != title:
                                    continue
                                if apply_diversity_autofix(sec, params=params, evidence_hint=str(pair)):
                                    changed_any = True
                                break
                        if not changed_any:
                            break
                        report = _run_report()
                        rounds += 1
                    _rebuild_postprocessed_artifacts(results, payload=local_payload, report=report, params=params)
                except Exception:
                    pass
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user")
                return
            outputs = _save_outputs(f"actions_{_job_id}", results)
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user", result=outputs)
                return
            update_job(_job_id, status="done", result=outputs)
        except Exception as e:
            update_job(_job_id, status="failed", error=repr(e))

    background_tasks.add_task(_run_job, job_id, payload)
    return {"ok": True, "job_id": job_id, "status": "queued"}


@router.post("/job_cancel")
async def actions_job_cancel(req: ActionsJobCancelRequest, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    job_id = str(req.job_id or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    status = str(job.get("status") or "").strip().lower()
    if status in {"done", "failed", "cancelled"}:
        return {"ok": True, "job_id": job_id, "status": status}
    update_job(job_id, status="cancelled", error="cancelled_by_user")
    return {"ok": True, "job_id": job_id, "status": "cancelled"}


@router.get("/job_status")
async def actions_job_status(job_id: str, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    out = {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }
    result = job.get("result") or {}
    if isinstance(result, dict):
        out["files"] = result
        json_path = result.get("json")
        if json_path and Path(json_path).exists():
            try:
                data = json.loads(Path(json_path).read_text(encoding="utf-8"))
                variants = data.get("variants") or []
                out["variants"] = len(variants)
                out["quality_ok"] = [
                    bool((v.get("quality_checks") or {}).get("structure", {}).get("ok"))
                    for v in variants
                ]
            except Exception:
                pass
    return {"ok": True, "job": out}


@router.get("/review/issues")
async def actions_review_issues(
    job_id: str,
    variant: int = 1,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    _, _, _, variants = _load_done_job_variants(job_id)
    v = max(1, int(variant or 1))
    rec = variants[v - 1] if v <= len(variants) else variants[0]
    items = _review_items_for_variant(rec)
    return {
        "ok": True,
        "job_id": job_id,
        "variant": int(v if v <= len(variants) else 1),
        "count": len(items),
        "items": items,
    }


@router.post("/review/apply")
async def actions_review_apply(
    req: ActionsReviewApplyRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    job_id = str(req.job_id or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")
    job, _, data, variants = _load_done_job_variants(job_id)

    v = max(1, int(req.variant or 1))
    idx = (v - 1) if v <= len(variants) else 0
    target = variants[idx]
    if not isinstance(target, dict):
        raise HTTPException(status_code=400, detail="invalid variant record")

    items = _review_items_for_variant(target)
    item_map = {str(it.get("issue_id") or ""): it for it in items}

    selected: list[dict] = []
    if bool(req.apply_all) and not req.decisions:
        selected = [it for it in items]
    else:
        for d in req.decisions or []:
            iid = str(d.issue_id or "").strip()
            if not iid:
                continue
            base = item_map.get(iid)
            if not base or not bool(d.apply):
                continue
            rec = dict(base)
            rep = str(d.replacement or "").strip()
            if rep:
                rec["replacement"] = rep
            selected.append(rec)

    if not selected:
        return {
            "ok": True,
            "job_id": job_id,
            "variant": idx + 1,
            "applied_count": 0,
            "message": "no selected items",
        }

    sections = target.get("sections") if isinstance(target.get("sections"), list) else []
    if not isinstance(sections, list):
        raise HTTPException(status_code=400, detail="variant sections missing")

    remediation = []
    replacement_count = 0
    for it in selected:
        title = str(it.get("title") or "").strip()
        rtype = str(it.get("type") or "issue").strip()
        suggestion = str(it.get("suggestion") or it.get("problem") or "").strip()
        replacement = str(it.get("replacement") or "").strip()
        if replacement and title:
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                if str(sec.get("title") or "").strip() == title:
                    sec["original_content"] = sec.get("content") or ""
                    sec["content"] = replacement
                    sec["auto_remediated"] = "review_apply"
                    replacement_count += 1
                    break
            continue
        remediation.append({"title": title, "type": rtype, "suggestion": suggestion})

    pid = str(target.get("project_id") or (job.get("payload") or {}).get("project_id") or "").strip() or None
    boq_focus = target.get("boq_focus") if isinstance(target.get("boq_focus"), dict) else {}
    params = load_params()
    payload_obj = (job.get("payload") or {}) if isinstance(job.get("payload"), dict) else {}
    overrides = payload_obj.get("params_override")
    if isinstance(overrides, dict) and overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(params.get(k), dict):
                merged = dict(params.get(k) or {})
                merged.update(v)
                params[k] = merged
            else:
                params[k] = v

    if remediation:
        apply_remediation(
            sections,
            remediation,
            project_id=pid,
            boq_focus=boq_focus,
            params=params,
        )
    for sec in sections:
        if isinstance(sec, dict):
            sec["content"] = strip_nonconcrete_language(str(sec.get("content") or ""))

    # Rebuild receipts/QC/cross-index for this variant after manual confirmation.
    _rebuild_postprocessed_artifacts([target], payload=payload_obj, report=None, params=params)

    # Persist all variants back to output files and refresh job result paths.
    out = _save_outputs(f"actions_{job_id}", variants)
    update_job(job_id, status="done", result=out, error=None)
    data["variants"] = variants
    try:
        Path(out["json"]).write_text(json.dumps({"variants": variants}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {
        "ok": True,
        "job_id": job_id,
        "variant": idx + 1,
        "applied_count": len(selected),
        "template_applied_count": len(remediation),
        "replacement_count": replacement_count,
        "files": out,
    }


@router.get("/result")
async def actions_result(
    job_id: str,
    variant: int = 1,
    include_sections: bool = False,
    max_chars: int = 4000,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        return {"ok": False, "status": job.get("status"), "error": job.get("error")}
    result = job.get("result") or {}
    json_path = result.get("json")
    if not json_path or not Path(json_path).exists():
        raise HTTPException(status_code=404, detail="result json not found")
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    variants = data.get("variants") or []
    if not variants:
        raise HTTPException(status_code=404, detail="empty result")
    v = max(1, int(variant or 1))
    rec = variants[v - 1] if v <= len(variants) else variants[0]
    response = {
        "ok": True,
        "variant_id": rec.get("variant_id") or v,
        "topic": rec.get("topic"),
        "outline": rec.get("outline"),
        "boq_focus": rec.get("boq_focus"),
        "quality_checks": rec.get("quality_checks"),
        "files": {
            "json": json_path,
            "docx": (result.get("docx") or [None])[v - 1] if isinstance(result.get("docx"), list) else result.get("docx"),
            "compare_docx": (result.get("compare_docx") or [None])[v - 1]
            if isinstance(result.get("compare_docx"), list)
            else result.get("compare_docx"),
            "focus_xlsx": (result.get("focus_xlsx") or [None])[v - 1]
            if isinstance(result.get("focus_xlsx"), list)
            else result.get("focus_xlsx"),
        },
    }
    if include_sections:
        trimmed = []
        max_chars = max(200, min(20000, int(max_chars or 4000)))
        for s in rec.get("sections") or []:
            txt = s.get("content") or ""
            if len(txt) > max_chars:
                txt = txt[:max_chars] + "..."
            trimmed.append({"title": s.get("title"), "content": txt, "agent_role": s.get("agent_role")})
        response["sections"] = trimmed
    return response


@router.get("/download")
async def actions_download(
    job_id: str,
    kind: str = "docx",  # docx|compare_docx|json|focus_xlsx
    variant: int = 1,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"job not done: {job.get('status')}")
    result = job.get("result") or {}
    path = result.get(kind)
    if kind in ("docx", "compare_docx", "focus_xlsx") and isinstance(path, list):
        v = max(1, int(variant or 1))
        path = path[v - 1] if v <= len(path) else None
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="file not found")
    if kind == "json":
        media_type = "application/json"
        filename = f"autoplan_{job_id}.json"
    elif kind == "focus_xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"autoplan_{job_id}_focus_v{max(1, int(variant or 1))}.xlsx"
    elif kind == "compare_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_compare_v{max(1, int(variant or 1))}.docx"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_v{max(1, int(variant or 1))}.docx"
    return FileResponse(str(path), media_type=media_type, filename=filename)
