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

from backend.zhifei_autoplan.job_store import create_job, get_job, update_job
from backend.zhifei_autoplan import export_docx_service as export_docx_core
from backend.zhifei_autoplan.orchestrator import run_autoplan
from backend.zhifei_autoplan.output_artifacts import save_outputs as save_output_artifacts
from backend.zhifei_autoplan.plan_store import load_plan, save_plan
from backend.zhifei_autoplan.parsers.tender_parser import TenderParser
from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.tender_store import save_tender_matrix
from backend.zhifei_autoplan.boq_store import save_boq_data
from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.quality_check import run_quality_checks, strip_nonconcrete_language
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.params_runtime import load_params, save_params
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.case_library_service import (
    CASE_LIBRARY_SCOPE,
    case_library_record_id,
    list_case_library_items,
    normalize_case_library_options,
)
from backend.zhifei_autoplan.image_library import (
    IMAGE_LIBRARY_SCOPE,
    image_library_record_id,
    list_image_library_items,
    normalize_image_library_options,
    normalize_text_list,
)
from backend.zhifei_autoplan.ollama_preview import run_ollama_preview, run_ollama_section_review
from backend.zhifei_autoplan.section_drafts import (
    apply_section_draft,
    build_section_draft,
    compute_section_draft_diff,
    reject_section_draft,
    rollback_section_draft,
)
from backend.app.routers.ingest import _handle_upload as _handle_ingest_upload
from backend.app.routers.ingest import _resolve_workspace_context as _resolve_ingest_workspace_context
from backend.app.routers.ingest import workspace_paths as ingest_workspace_paths


router = APIRouter(prefix="/actions", tags=["Actions Bridge"])


def _auth_actions_key(x_actions_key: str | None):
    expected = os.environ.get("ZF_ACTIONS_KEY", "zf-webui-key").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="actions key not configured")
    if (x_actions_key or "").strip() != expected:
        raise HTTPException(status_code=401, detail="invalid actions key")


class ActionsGenerateRequest(BaseModel):
    topic: str
    project_id: str | None = None
    project_type: str | None = None
    generation_mode: str | None = None
    outline: List[str] = []
    requirements: List[str] = []
    global_instruction: str | None = None
    chapter_requirements: dict | None = None
    provider: str | None = None
    model: str | None = None
    provider_chain: List[dict] | None = None
    providers: List[str] = []
    model_map: dict | None = None
    style: dict | None = None
    variants: int = 1
    # 可选模板（A/B/C/D/E）；若提供则按所选模板逐份生成。
    selected_templates: List[str] | None = None
    # 并行控制：章节级 Agent 并行数（单份方案内），以及多份方案并行数（A/B/C/D/E 之间）。
    agent_parallelism: int | None = None
    variant_parallelism: int | None = None
    strict_tender_outline: bool | None = None
    total_pages_target: int | None = None
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
    case_library: dict | None = None
    image_library: dict | None = None


class ActionsPlanRequest(BaseModel):
    outline: List[str]
    style: dict = {}
    project_type: str | None = None
    generation_mode: str | None = None
    global_instruction: str | None = None
    variants: int = 1
    selected_templates: List[str] | None = None
    strict_tender_outline: bool | None = None
    total_pages_target: int | None = None
    chapter_requirements: dict = {}
    chapter_pages: dict = {}
    quality_strict: bool = True
    auto_remediate: bool = True
    remediate_mode: str = "template"
    compare_mode: str = "summary"
    compare_max_chars: int = 1200
    compare_titles: list[str] | None = None
    case_library: dict | None = None
    image_library: dict | None = None


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
    media: List[dict] | None = None
    image_selection_pack: dict | None = None
    case_reference_pack: dict | None = None


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


class ActionsOllamaPreviewRequest(BaseModel):
    content: str = ""
    section_title: str | None = None
    instruction: str | None = None
    model: str | None = None
    base_url: str | None = None
    timeout: float | None = None


class ActionsOllamaSectionReviewRequest(BaseModel):
    project_name: str | None = None
    section_title: str | None = None
    section_content: str = ""
    review_focus: str | None = None
    model: str | None = None
    base_url: str | None = None
    timeout: float | None = None


class ActionsOllamaSectionDraftBuildRequest(BaseModel):
    project_name: str | None = None
    section_title: str | None = None
    original_content: str = ""
    draft_content: str = ""
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    prompt: str | None = None
    confirmed_by: str | None = None


class ActionsOllamaSectionDraftDecisionRequest(BaseModel):
    draft: dict
    confirmed_by: str | None = None
    confirmed_at: str | None = None


class ActionsOllamaMainChainSmokeRequest(BaseModel):
    topic: str | None = None
    outline: List[str] = []
    requirements: List[str] = []
    global_instruction: str | None = None
    section_title: str | None = None
    section_content: str | None = None
    chapter_requirements: dict | None = None
    model: str | None = None
    base_url: str | None = None


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


def _to_positive_int(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def _normalize_logic_template_id(raw: Any) -> str | None:
    s = str(raw or "").strip().upper()
    if not s:
        return None
    if s in {"A", "B", "C", "D", "E"}:
        return s
    alias = {
        "TEMPLATE_A": "A",
        "TEMPLATE_B": "B",
        "TEMPLATE_C": "C",
        "TEMPLATE_D": "D",
        "TEMPLATE_E": "E",
        "方案A": "A",
        "方案B": "B",
        "方案C": "C",
        "方案D": "D",
        "方案E": "E",
        # Compatibility: users may input S as C.
        "S": "C",
        "方案S": "C",
        "TEMPLATE_S": "C",
    }
    return alias.get(s)


def _normalize_selected_templates(raw: Any) -> List[str]:
    arr = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
    out: List[str] = []
    seen = set()
    for x in arr:
        tid = _normalize_logic_template_id(x)
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append(tid)
        if len(out) >= 5:
            break
    return out


def _build_variant_plan(payload: dict) -> List[Dict[str, Any]]:
    pid = str(payload.get("project_id") or "").strip() or None
    selected = _normalize_selected_templates(payload.get("selected_templates"))
    explicit_variant_id = payload.get("variant_id")
    explicit_template_id = _normalize_logic_template_id(payload.get("logic_template_id") or payload.get("logic_template"))

    if selected:
        variant_ids = reserve_variant_ids(
            project_id=pid,
            count=max(1, len(selected)),
            explicit_variant_id=explicit_variant_id,
            explicit_template_id=None,
        )
        payload["selected_templates"] = selected
        payload["variants"] = len(selected)
        return [
            {"variant_id": int(variant_ids[i]), "logic_template_id": selected[i]}
            for i in range(min(len(variant_ids), len(selected)))
        ]

    try:
        variants = int(payload.get("variants") or 1)
    except Exception:
        variants = 1
    variants = max(1, min(5, variants))
    variant_ids = reserve_variant_ids(
        project_id=pid,
        count=variants,
        explicit_variant_id=explicit_variant_id,
        explicit_template_id=explicit_template_id,
    )
    if explicit_template_id:
        return [{"variant_id": int(vid), "logic_template_id": explicit_template_id} for vid in variant_ids]
    return [{"variant_id": int(vid)} for vid in variant_ids]


def _page_target_value(v: Any) -> int | None:
    if isinstance(v, dict):
        v = v.get("target") or v.get("pages") or v.get("page_target") or v.get("count")
    return _to_positive_int(v)


def _planned_total_pages(payload: dict) -> int:
    hard = _to_positive_int(payload.get("total_pages_target"))
    if hard:
        return int(hard)
    chapter_pages = payload.get("chapter_pages") if isinstance(payload.get("chapter_pages"), dict) else {}
    if not chapter_pages:
        return 0
    s = 0
    for _, raw in chapter_pages.items():
        n = _page_target_value(raw)
        if n:
            s += int(n)
    return int(s)


def _apply_generation_mode_policy(payload: dict) -> dict:
    mode = str(payload.get("generation_mode") or "quality_200").strip()
    if not mode:
        mode = "quality_200"
    pages = _planned_total_pages(payload)
    auto_switched = False

    if mode == "quality_200" and pages > 500:
        mode = "hq_speed_500"
        auto_switched = True

    if mode == "quality_200":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        if str(payload.get("remediate_mode") or "").strip() not in {"template", "llm"}:
            payload["remediate_mode"] = "template"
        ap = _to_positive_int(payload.get("agent_parallelism")) or 4
        payload["agent_parallelism"] = max(1, min(16, int(ap)))
    elif mode == "hq_speed_500":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["remediate_mode"] = "template"
        ap = _to_positive_int(payload.get("agent_parallelism")) or 6
        payload["agent_parallelism"] = max(6, min(16, int(ap)))
        vp = _to_positive_int(payload.get("variant_parallelism")) or 1
        payload["variant_parallelism"] = max(1, min(5, int(vp)))
        if payload.get("generate_images") is None:
            payload["generate_images"] = False
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 800
    else:
        mode = "quality_200"
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        ap = _to_positive_int(payload.get("agent_parallelism")) or 4
        payload["agent_parallelism"] = max(1, min(16, int(ap)))

    payload["generation_mode"] = mode
    payload["_mode_policy"] = {
        "mode_effective": mode,
        "auto_switched": bool(auto_switched),
        "planned_total_pages": int(pages),
    }
    return payload


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
    if payload.get("total_pages_target") is None:
        payload["total_pages_target"] = plan.get("total_pages_target")
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
    if payload.get("case_library") is None:
        payload["case_library"] = plan.get("case_library")
    if payload.get("image_library") is None:
        payload["image_library"] = plan.get("image_library")
    if payload.get("case_library") is not None:
        payload["case_library"] = normalize_case_library_options(payload.get("case_library"))
    if payload.get("image_library") is not None:
        payload["image_library"] = normalize_image_library_options(payload.get("image_library"))
    if payload.get("selected_templates") is None:
        payload["selected_templates"] = plan.get("selected_templates")
    payload["selected_templates"] = _normalize_selected_templates(payload.get("selected_templates"))
    if payload.get("selected_templates"):
        payload["variants"] = len(payload["selected_templates"])
    if not payload.get("variants"):
        payload["variants"] = plan.get("variants") or 1
    if payload.get("strict_tender_outline") is None:
        payload["strict_tender_outline"] = plan.get("strict_tender_outline", False)
    if not payload.get("project_type"):
        payload["project_type"] = plan.get("project_type")
    if payload.get("generation_mode") is None:
        payload["generation_mode"] = plan.get("generation_mode")
    if payload.get("global_instruction") is None:
        payload["global_instruction"] = plan.get("global_instruction")
    return _apply_generation_mode_policy(payload)


def _save_outputs(base_name: str, results: list[dict]) -> dict:
    return save_output_artifacts(base_name, results)


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
        try:
            v["evidence_tracking"] = build_evidence_tracking(
                sections=sections,
                tender=tender,
                chapter_pages=v.get("chapter_pages") if isinstance(v.get("chapter_pages"), dict) else {},
            )
        except Exception:
            v["evidence_tracking"] = {"rows": [], "summary": {}}


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


def _reference_audit_path(session_id: str | None = None, workspace_dir: str | None = None) -> Path:
    workspace = _resolve_ingest_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    return ingest_workspace_paths(workspace["workspace_dir"])["ingest_audit"]


def _case_library_saved_view(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_library_record_id(rec),
        "title": str(rec.get("library_title") or rec.get("filename") or "").strip(),
        "filename": rec.get("filename"),
        "project_type": rec.get("project_type"),
        "tags": normalize_text_list(rec.get("library_tags")),
        "chapter_scope": normalize_text_list(rec.get("chapter_scope")),
        "summary": str(rec.get("library_summary") or "").strip(),
        "style_profile": str(rec.get("library_style_profile") or "").strip(),
        "source_file": rec.get("saved_as"),
        "storage_path": rec.get("saved_as"),
        "extract_saved_as": rec.get("extract_saved_as"),
        "enabled": bool(rec.get("enabled", True)),
        "usable": bool(rec.get("usable", True)),
        "created_at": rec.get("ts"),
        "updated_at": rec.get("ts"),
    }


def _image_library_saved_view(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "image_id": image_library_record_id(rec),
        "title": str(rec.get("library_title") or rec.get("filename") or "").strip(),
        "filename": rec.get("filename"),
        "project_type": rec.get("project_type"),
        "tags": normalize_text_list(rec.get("library_tags")),
        "chapter_scope": normalize_text_list(rec.get("chapter_scope")),
        "process_scope": normalize_text_list(rec.get("process_scope")),
        "caption": str(rec.get("library_caption") or "").strip(),
        "description": str(rec.get("library_description") or "").strip(),
        "source_path": rec.get("saved_as"),
        "storage_path": rec.get("saved_as"),
        "preview_saved_as": rec.get("preview_saved_as"),
        "enabled": bool(rec.get("enabled", True)),
        "usable": bool(rec.get("usable", True)),
        "created_at": rec.get("ts"),
        "updated_at": rec.get("ts"),
    }


@router.get("/case_library/items")
async def actions_case_library_items(
    project_type: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    limit: int = 50,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    items = list_case_library_items(
        project_type=project_type,
        tags=normalize_text_list(tags),
        chapter_scope=chapter_scope,
        limit=max(1, min(int(limit or 50), 100)),
        audit_path=_reference_audit_path(session_id=session_id, workspace_dir=workspace_dir),
    )
    return {"ok": True, "items": items}


@router.post("/case_library/upload")
async def actions_case_library_upload(
    files: List[UploadFile] = File(...),
    project_type: str | None = None,
    title: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    summary: str | None = None,
    style_profile: str | None = None,
    usable: bool | str | None = True,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    res = await _handle_ingest_upload(
        files,
        source_hint=CASE_LIBRARY_SCOPE,
        session_id=session_id,
        workspace_dir=workspace_dir,
        library_scope=CASE_LIBRARY_SCOPE,
        project_type=project_type,
        title=title,
        tags=tags,
        chapter_scope=chapter_scope,
        summary=summary,
        style_profile=style_profile,
        usable=usable,
    )
    rows = res.get("saved") if isinstance(res, dict) else []
    return {"ok": True, "items": [_case_library_saved_view(row) for row in rows if isinstance(row, dict)]}


@router.get("/image_library/items")
async def actions_image_library_items(
    project_type: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    limit: int = 50,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    items = list_image_library_items(
        project_type=project_type,
        tags=normalize_text_list(tags),
        chapter_scope=chapter_scope,
        process_scope=process_scope,
        limit=max(1, min(int(limit or 50), 100)),
        audit_path=_reference_audit_path(session_id=session_id, workspace_dir=workspace_dir),
    )
    return {"ok": True, "items": items}


@router.post("/image_library/upload")
async def actions_image_library_upload(
    files: List[UploadFile] = File(...),
    project_type: str | None = None,
    title: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    caption: str | None = None,
    description: str | None = None,
    usable: bool | str | None = True,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    res = await _handle_ingest_upload(
        files,
        source_hint=IMAGE_LIBRARY_SCOPE,
        session_id=session_id,
        workspace_dir=workspace_dir,
        library_scope=IMAGE_LIBRARY_SCOPE,
        project_type=project_type,
        title=title,
        tags=tags,
        chapter_scope=chapter_scope,
        process_scope=process_scope,
        caption=caption,
        description=description,
        usable=usable,
    )
    rows = res.get("saved") if isinstance(res, dict) else []
    return {"ok": True, "items": [_image_library_saved_view(row) for row in rows if isinstance(row, dict)]}


@router.post("/ollama/preview")
async def actions_ollama_preview(
    req: ActionsOllamaPreviewRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    return run_ollama_preview(
        content=req.content,
        section_title=req.section_title,
        instruction=req.instruction,
        model=req.model,
        base_url=req.base_url,
        timeout=req.timeout,
    )


@router.post("/ollama/review_section")
async def actions_ollama_review_section(
    req: ActionsOllamaSectionReviewRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    return run_ollama_section_review(
        project_name=req.project_name,
        section_title=req.section_title,
        section_content=req.section_content,
        review_focus=req.review_focus,
        model=req.model,
        base_url=req.base_url,
        timeout=req.timeout,
    )


def _ollama_write_back_enabled() -> bool:
    return os.environ.get("ZDOC_OLLAMA_WRITE_BACK_ENABLED", "").strip() == "1"


def _ollama_section_draft_disabled_response(action_type: str) -> dict:
    return {
        "ok": False,
        "status": "disabled",
        "draft_type": "section_draft",
        "action_type": action_type,
        "draft": None,
        "audit": [],
        "error": None,
        "warning": "ollama_write_back_disabled",
    }


def _ollama_section_draft_decision_response(action_type: str, draft: dict) -> dict:
    return {
        "ok": True,
        "status": draft.get("status", "ok"),
        "draft_type": "section_draft",
        "action_type": action_type,
        "draft": draft,
        "audit": draft.get("audit", []),
        "error": None,
    }


@router.post("/ollama/section_draft/build")
async def actions_ollama_section_draft_build(
    req: ActionsOllamaSectionDraftBuildRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    section_title = (req.section_title or "").strip()
    if not _ollama_write_back_enabled():
        return {
            "ok": False,
            "status": "disabled",
            "draft_type": "section_draft",
            "section_title": section_title,
            "draft": None,
            "diff_preview": "",
            "audit": [],
            "error": None,
            "warning": "ollama_write_back_disabled",
        }

    draft = build_section_draft(
        section_title=section_title,
        original_content=req.original_content,
        draft_content=req.draft_content,
        provider=req.provider,
        model=req.model,
        base_url=req.base_url,
        prompt=req.prompt,
    )
    diff_preview = compute_section_draft_diff(req.original_content, req.draft_content)
    return {
        "ok": True,
        "status": "ok",
        "draft_type": "section_draft",
        "section_title": draft.get("section_title", section_title),
        "draft": draft,
        "diff_preview": diff_preview,
        "audit": draft.get("audit", []),
        "error": None,
    }


@router.post("/ollama/section_draft/apply_preview")
async def actions_ollama_section_draft_apply_preview(
    req: ActionsOllamaSectionDraftDecisionRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    action_type = "apply_preview"
    if not _ollama_write_back_enabled():
        return _ollama_section_draft_disabled_response(action_type)

    draft = apply_section_draft(
        req.draft,
        confirmed_by=req.confirmed_by,
        confirmed_at=req.confirmed_at,
    )
    return _ollama_section_draft_decision_response(action_type, draft)


@router.post("/ollama/section_draft/reject")
async def actions_ollama_section_draft_reject(
    req: ActionsOllamaSectionDraftDecisionRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    action_type = "reject"
    if not _ollama_write_back_enabled():
        return _ollama_section_draft_disabled_response(action_type)

    draft = reject_section_draft(
        req.draft,
        confirmed_by=req.confirmed_by,
        confirmed_at=req.confirmed_at,
    )
    return _ollama_section_draft_decision_response(action_type, draft)


@router.post("/ollama/section_draft/rollback")
async def actions_ollama_section_draft_rollback(
    req: ActionsOllamaSectionDraftDecisionRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    action_type = "rollback"
    if not _ollama_write_back_enabled():
        return _ollama_section_draft_disabled_response(action_type)

    draft = rollback_section_draft(
        req.draft,
        confirmed_by=req.confirmed_by,
        confirmed_at=req.confirmed_at,
    )
    return _ollama_section_draft_decision_response(action_type, draft)


def _ollama_smoke_enabled() -> bool:
    return os.environ.get("ZDOC_OLLAMA_MAIN_CHAIN_SMOKE_ENABLED", "").strip() == "1"


def _ollama_smoke_model(req_model: str | None) -> str:
    return (req_model or os.environ.get("OLLAMA_MODEL") or "qwen3:0.6b").strip() or "qwen3:0.6b"


def _ollama_smoke_base_url(req_base_url: str | None) -> str:
    return (req_base_url or os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").strip() or "http://127.0.0.1:11434"


def _ollama_smoke_title(req: ActionsOllamaMainChainSmokeRequest) -> str:
    candidates = [req.section_title, *(req.outline or [])]
    for value in candidates:
        text = str(value or "").strip()
        if text:
            return text
    return "Ollama主链烟测"


def _ollama_smoke_requirements(req: ActionsOllamaMainChainSmokeRequest) -> list[str]:
    requirements = [str(item).strip() for item in (req.requirements or []) if str(item or "").strip()]
    if requirements:
        return requirements[:1]
    section_content = str(req.section_content or "").strip()
    if section_content:
        return [section_content]
    return ["仅用于 no-write 主链烟测，输出一段简短章节内容。"]


def _ollama_smoke_payload(req: ActionsOllamaMainChainSmokeRequest) -> dict:
    title = _ollama_smoke_title(req)
    chapter_requirements: dict[str, Any] = {}
    if isinstance(req.chapter_requirements, dict):
        raw = req.chapter_requirements.get(title)
        if raw is not None:
            chapter_requirements[title] = raw
    if title not in chapter_requirements:
        chapter_requirements[title] = _ollama_smoke_requirements(req)

    return {
        "topic": str(req.topic or "ZDoc Ollama no-write main-chain smoke").strip(),
        "outline": [title],
        "requirements": _ollama_smoke_requirements(req),
        "global_instruction": req.global_instruction,
        "chapter_requirements": chapter_requirements,
        "chapter_pages": {title: 1},
        "total_pages_target": 1,
        "strict_tender_outline": True,
        "provider": "ollama",
        "model": _ollama_smoke_model(req.model),
        "base_url": _ollama_smoke_base_url(req.base_url),
        "no_write": True,
        "preview_only": True,
        "generate_images": False,
        "auto_remediate": False,
        "quality_strict": False,
        "agent_parallelism": 1,
        "variant_parallelism": 1,
    }


def _section_text_preview(section: dict) -> str:
    for key in ("content", "body", "markdown", "text"):
        value = section.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]
    return ""


def _ollama_smoke_sections_preview(result: dict) -> list[dict]:
    sections = result.get("sections") if isinstance(result, dict) else []
    if not isinstance(sections, list):
        return []
    preview: list[dict] = []
    for section in sections[:1]:
        if not isinstance(section, dict):
            continue
        preview.append(
            {
                "title": section.get("title"),
                "provider": section.get("provider"),
                "model": section.get("model"),
                "error": section.get("error"),
                "content_preview": _section_text_preview(section),
            }
        )
    return preview


@router.post("/ollama/main_chain_smoke")
async def actions_ollama_main_chain_smoke(
    req: ActionsOllamaMainChainSmokeRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    model = _ollama_smoke_model(req.model)
    base_url = _ollama_smoke_base_url(req.base_url)
    smoke_type = "ollama_main_chain_no_write"
    if not _ollama_smoke_enabled():
        return {
            "ok": False,
            "enabled": False,
            "status": "disabled",
            "provider": "ollama",
            "model": model,
            "base_url": base_url,
            "section_count": 0,
            "sections_preview": [],
            "error": None,
            "warning": "ollama_main_chain_smoke_disabled",
            "smoke_type": smoke_type,
        }

    payload = _ollama_smoke_payload(req)
    try:
        result = await run_autoplan(payload)
    except Exception as exc:
        return {
            "ok": False,
            "enabled": True,
            "status": "fallback",
            "provider": "ollama",
            "model": model,
            "base_url": base_url,
            "section_count": 0,
            "sections_preview": [],
            "error": f"ollama_main_chain_smoke_error:{type(exc).__name__}",
            "warning": None,
            "smoke_type": smoke_type,
        }

    sections = result.get("sections") if isinstance(result, dict) else []
    section_count = len(sections) if isinstance(sections, list) else 0
    return {
        "ok": True,
        "enabled": True,
        "status": "ok",
        "provider": "ollama",
        "model": model,
        "base_url": base_url,
        "section_count": section_count,
        "sections_preview": _ollama_smoke_sections_preview(result if isinstance(result, dict) else {}),
        "error": None,
        "warning": None,
        "smoke_type": smoke_type,
    }


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
async def actions_export_docx(
    req: ActionsExportRequest,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    return export_docx_core.execute_export_docx_request(
        raw_request=req.model_dump(),
        workspace_dir=str(workspace_dir or "."),
        save_outputs_fn=_save_outputs,
    )


@router.post("/generate")
async def actions_generate(req: ActionsGenerateRequest, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    payload = _merge_plan_defaults(req.model_dump())
    variant_plan = _build_variant_plan(payload)
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(v.get("variant_id") or 1) for v in variant_plan]
    results = []
    for item in variant_plan:
        local_payload = json.loads(json.dumps(payload))
        local_payload["variant_id"] = int(item.get("variant_id") or 1)
        tid = _normalize_logic_template_id(item.get("logic_template_id"))
        if tid:
            local_payload["logic_template_id"] = tid
        results.append(await run_autoplan(local_payload))
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
            # This is deterministic and avoids "换词" by switching to A/B/C/D/E structural blocks.
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
    variant_plan = _build_variant_plan(payload)
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(v.get("variant_id") or 1) for v in variant_plan]
    payload["variants"] = len(variant_plan) if variant_plan else int(payload.get("variants") or 1)
    job_id = create_job(payload, user_id=None)

    def _run_job(_job_id: str, _payload: dict):
        try:
            local_payload = _apply_generation_mode_policy(json.loads(json.dumps(_payload)))

            def _clamp_int(v: Any, default: int, lo: int, hi: int) -> int:
                try:
                    n = int(v)
                except Exception:
                    n = int(default)
                return max(lo, min(hi, n))

            variants_total = _clamp_int(local_payload.get("variants") or 1, 1, 1, 5)
            agent_parallelism = _clamp_int(local_payload.get("agent_parallelism") or 4, 4, 1, 16)
            variant_parallelism = _clamp_int(local_payload.get("variant_parallelism") or 1, 1, 1, 5)
            local_payload["agent_parallelism"] = agent_parallelism
            local_payload["variant_parallelism"] = variant_parallelism

            agent_runtime = {
                "mode": "parallel",
                "master_agent": "主控Agent",
                "compliance_agent": "合规Agent",
                "agent_parallelism": agent_parallelism,
                "variant_parallelism": variant_parallelism,
                "variants_total": variants_total,
                "variants_done": 0,
            }

            def _update_progress(percent: int, stage: str, detail: str = "") -> None:
                p = max(0, min(100, int(percent)))
                update_job(
                    _job_id,
                    progress={
                        "percent": p,
                        "stage": str(stage or ""),
                        "detail": str(detail or ""),
                        "variants_total": variants_total,
                        "variants_done": int(agent_runtime.get("variants_done") or 0),
                    },
                    agent_runtime=agent_runtime,
                )

            def _is_cancelled() -> bool:
                j = get_job(_job_id) or {}
                return str(j.get("status") or "").strip().lower() == "cancelled"

            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user")
                return
            update_job(_job_id, status="running", agent_runtime=agent_runtime)
            _update_progress(5, "job_started", "任务已启动，正在分配多Agent")
            mode_policy = local_payload.get("_mode_policy") if isinstance(local_payload.get("_mode_policy"), dict) else {}
            mode_name = str(mode_policy.get("mode_effective") or local_payload.get("generation_mode") or "quality_200")
            pages_planned = int(mode_policy.get("planned_total_pages") or 0)
            if bool(mode_policy.get("auto_switched")):
                _update_progress(
                    8,
                    "mode_switch",
                    f"页数规划={pages_planned}，已自动切换到高质量加速模式（{mode_name}）",
                )
            else:
                _update_progress(
                    8,
                    "mode_ready",
                    f"生成模式={mode_name}，页数规划={pages_planned}",
                )
            variant_plan = local_payload.get("_variant_plan")
            normalized_plan: List[Dict[str, Any]] = []
            if isinstance(variant_plan, list) and variant_plan:
                for it in variant_plan:
                    if not isinstance(it, dict):
                        continue
                    try:
                        vid = int(it.get("variant_id") or 0)
                    except Exception:
                        vid = 0
                    if vid <= 0:
                        continue
                    rec: Dict[str, Any] = {"variant_id": vid}
                    tid = _normalize_logic_template_id(it.get("logic_template_id"))
                    if tid:
                        rec["logic_template_id"] = tid
                    normalized_plan.append(rec)
            if not normalized_plan:
                variants = variants_total
                variant_ids = local_payload.get("_variant_ids")
                if not isinstance(variant_ids, list) or not variant_ids:
                    variant_ids = reserve_variant_ids(
                        project_id=str(local_payload.get("project_id") or "").strip() or None,
                        count=max(1, variants),
                        explicit_variant_id=local_payload.get("variant_id"),
                        explicit_template_id=local_payload.get("logic_template_id") or local_payload.get("logic_template"),
                    )
                for vid in variant_ids:
                    try:
                        normalized_plan.append({"variant_id": int(vid)})
                    except Exception:
                        continue
            if not normalized_plan:
                normalized_plan = [{"variant_id": 1}]
            variant_plan = normalized_plan
            variants_total = max(1, len(variant_plan))
            agent_runtime["variants_total"] = variants_total
            if variant_parallelism > variants_total:
                variant_parallelism = variants_total
                local_payload["variant_parallelism"] = variant_parallelism
                agent_runtime["variant_parallelism"] = variant_parallelism
            _update_progress(
                10,
                "agent_ready",
                f"多Agent协作已启用：章节并行={agent_parallelism}，方案并行={variant_parallelism}",
            )

            async def _run_variants_parallel() -> list[dict]:
                sem = asyncio.Semaphore(max(1, int(variant_parallelism)))
                lock = asyncio.Lock()
                done_count = 0
                ordered: list[dict | None] = [None for _ in range(len(variant_plan))]

                async def _run_one(pos: int, item: Dict[str, Any]):
                    nonlocal done_count
                    if _is_cancelled():
                        return
                    vid = int(item.get("variant_id") or 1)
                    tid = _normalize_logic_template_id(item.get("logic_template_id"))
                    lp = json.loads(json.dumps(local_payload))
                    lp["variant_id"] = int(vid)
                    if tid:
                        lp["logic_template_id"] = tid
                    lp["agent_parallelism"] = agent_parallelism
                    async with sem:
                        if _is_cancelled():
                            return
                        detail = f"正在并行编制方案 v{int(vid)}"
                        if tid:
                            detail += f"（模板{tid}）"
                        _update_progress(
                            15 + int((done_count / max(1, variants_total)) * 65),
                            "variant_running",
                            detail,
                        )
                        res = await run_autoplan(lp)
                        ordered[pos] = res
                    async with lock:
                        done_count += 1
                        agent_runtime["variants_done"] = int(done_count)
                        _update_progress(
                            15 + int((done_count / max(1, variants_total)) * 65),
                            "variant_running",
                            f"方案完成进度：{done_count}/{variants_total}",
                        )

                await asyncio.gather(*[_run_one(i, item) for i, item in enumerate(variant_plan)])
                return [x for x in ordered if isinstance(x, dict)]

            results = asyncio.run(_run_variants_parallel())
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
                    _update_progress(86, "cross_variant_check", "正在执行跨方案一致性与差异性审计")
                    _rebuild_postprocessed_artifacts(results, payload=local_payload, report=report, params=params)
                except Exception:
                    pass
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user")
                return
            _update_progress(92, "exporting", "正在导出 DOCX / 对照稿 / 问题清单")
            outputs = _save_outputs(f"actions_{_job_id}", results)
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user", result=outputs)
                return
            _update_progress(100, "done", "任务完成")
            update_job(_job_id, status="done", result=outputs, agent_runtime=agent_runtime)
        except Exception as e:
            update_job(
                _job_id,
                status="failed",
                error=repr(e),
                progress={"percent": 100, "stage": "failed", "detail": repr(e)},
            )

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
        "progress": job.get("progress") if isinstance(job.get("progress"), dict) else {},
        "agent_runtime": job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {},
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
                if variants and isinstance(variants[0], dict):
                    ma = variants[0].get("multi_agent")
                    if isinstance(ma, dict):
                        out["multi_agent"] = ma
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
            "score_overview_xlsx": (result.get("score_overview_xlsx") or [None])[v - 1]
            if isinstance(result.get("score_overview_xlsx"), list)
            else result.get("score_overview_xlsx"),
            "expert_review_docx": (result.get("expert_review_docx") or [None])[v - 1]
            if isinstance(result.get("expert_review_docx"), list)
            else result.get("expert_review_docx"),
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
    kind: str = "docx",  # docx|compare_docx|json|focus_xlsx|score_overview_xlsx|expert_review_docx
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
    if kind in ("docx", "compare_docx", "focus_xlsx", "score_overview_xlsx", "expert_review_docx") and isinstance(path, list):
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
    elif kind == "score_overview_xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{max(1, int(variant or 1))}.xlsx"
    elif kind == "expert_review_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_专家复核提要版_v{max(1, int(variant or 1))}.docx"
    elif kind == "compare_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_compare_v{max(1, int(variant or 1))}.docx"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_v{max(1, int(variant or 1))}.docx"
    return FileResponse(str(path), media_type=media_type, filename=filename)
