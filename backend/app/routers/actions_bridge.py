from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import FileResponse

from backend.zhifei_autoplan.job_store import create_job, get_job, heartbeat_job, update_job
from backend.zhifei_autoplan import export_docx_service as export_docx_core
from backend.zhifei_autoplan.orchestrator import (
    _build_boq_focus,
    _normalize_provider_chain,
    _provider_chain_for_role,
    _resolve_provider_api_key,
    run_autoplan,
)
from backend.zhifei_autoplan.multi_agent_runtime import AGENT_ROLE_DIRECTIVES
from backend.zhifei_autoplan.output_artifacts import save_outputs as save_output_artifacts
from backend.zhifei_autoplan.professional_document_renderer import (
    ProfessionalRenderError,
    render_professional_document,
)
from backend.zhifei_autoplan.plan_store import load_plan, save_plan
from backend.zhifei_autoplan.parsers.tender_parser import TenderParser
from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.tender_store import save_tender_matrix
from backend.zhifei_autoplan.boq_store import save_boq_data
from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.quality_check import apply_remediation, run_quality_checks, strip_nonconcrete_language
from backend.zhifei_autoplan.utils.llm_client import LLMClient
from backend.zhifei_autoplan.execution_control import ExecutionControlRuntime
from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.delivery_receipt import build_delivery_receipt
from backend.zhifei_autoplan.requirement_evidence_matrix import (
    finalize_requirement_evidence_matrix,
    validate_requirement_evidence_matrix,
)
from backend.zhifei_autoplan.compliance_policy import audit_standard_citations
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
from backend.zhifei_autoplan.review_revision import (
    artifact_manifest,
    canonical_digest,
    create_revision_snapshot,
    finalize_revision_snapshot,
    issue_set_digest,
    list_revision_snapshots,
    load_revision_snapshot,
    result_version,
    stable_issue_id,
    variant_version,
)
from backend.zhifei_autoplan.zbid_snapshot_mapper import map_zbid_snapshot_to_zdoc_draft_input
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
    max_model_parallelism: int | None = None
    max_model_attempts: int | None = None
    max_model_input_chars: int | None = None
    max_model_output_tokens: int | None = None
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
    # 实战生成默认先验证模型/凭据，并在整条文本模型链失效时停止，避免模板稿冒充成功结果。
    model_preflight: bool | None = True
    fail_on_model_exhaustion: bool | None = True
    # Resume integrity-bound completed chapters from a prior failed/cancelled
    # job. A changed project, outline, style, requirement plan or model route
    # produces a different binding and therefore cannot reuse old content.
    resume_from_job_id: str | None = None


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


class ActionsProfessionalRenderRequest(BaseModel):
    job_id: str
    variant: int = 1


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
    expected_result_version: str = ""
    expected_variant_version: str = ""
    expected_issue_digest: str = ""
    actor: str | None = None


class ActionsReviewRollbackRequest(BaseModel):
    job_id: str
    revision_id: str
    expected_result_version: str = ""
    actor: str | None = None


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


class ActionsZBidSnapshotDraftInputPreviewRequest(BaseModel):
    snapshot: dict


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
    payload.setdefault("model_preflight", True)
    payload.setdefault("fail_on_model_exhaustion", True)
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
    postprocess_blocked = [
        {
            "variant": index,
            "errors": row.get("postprocess_errors") or [],
        }
        for index, row in enumerate(results, start=1)
        if isinstance(row, dict) and bool(row.get("postprocess_errors"))
    ]
    if postprocess_blocked:
        raise RuntimeError(
            json.dumps(
                {
                    "code": "POSTPROCESS_REBUILD_FAILED",
                    "message": "最终内容复核后的派生报告重建失败，禁止沿用旧质量结论生成交付文件。",
                    "variants": postprocess_blocked,
                },
                ensure_ascii=False,
            )
        )
    blocked = [
        {
            "variant": index,
            "decision_digest": (row.get("delivery_quality_gate") or {}).get("decision_digest"),
            "blockers": (row.get("delivery_quality_gate") or {}).get("blockers") or [],
        }
        for index, row in enumerate(results, start=1)
        if isinstance(row, dict)
        and isinstance(row.get("delivery_quality_gate"), dict)
        and not bool((row.get("delivery_quality_gate") or {}).get("delivery_allowed"))
    ]
    if blocked:
        raise RuntimeError(
            json.dumps(
                {
                    "code": "DELIVERY_QUALITY_GATE_BLOCKED",
                    "message": "最终专业交付质量门未通过，禁止生成交付文件。",
                    "variants": blocked,
                },
                ensure_ascii=False,
            )
        )
    return save_output_artifacts(base_name, results)


def _clamp_execution_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = int(default)
    return max(int(minimum), min(int(maximum), parsed))


def _prepare_execution_control(
    payload: dict[str, Any],
    *,
    cancel_callback: Any | None = None,
) -> tuple[ExecutionControlRuntime, dict[str, Any]]:
    """Apply one execution policy to every generation entry point.

    The returned runtime is intentionally attached only after JSON cloning so
    secrets, callbacks and synchronization primitives never enter persisted
    request payloads.  All chapter, variant and professional-render model calls
    then share the same concurrency semaphore and cumulative budgets.
    """

    variants_total = _clamp_execution_int(payload.get("variants") or 1, 1, 1, 5)
    agent_parallelism = _clamp_execution_int(
        payload.get("agent_parallelism") or 4,
        4,
        1,
        16,
    )
    variant_parallelism = _clamp_execution_int(
        payload.get("variant_parallelism") or 1,
        1,
        1,
        5,
    )
    max_model_parallelism = _clamp_execution_int(
        payload.get("max_model_parallelism") or 8,
        8,
        1,
        16,
    )
    variant_parallelism = min(variant_parallelism, variants_total, max_model_parallelism)
    agent_parallelism = min(
        agent_parallelism,
        max(1, max_model_parallelism // max(1, variant_parallelism)),
    )

    chapter_count = max(
        1,
        len(payload.get("outline")) if isinstance(payload.get("outline"), list) else 1,
    )
    default_attempts = min(
        1_200,
        max(96, variants_total * (chapter_count * 10 + 24)),
    )
    max_model_attempts = _clamp_execution_int(
        payload.get("max_model_attempts") or default_attempts,
        default_attempts,
        1,
        10_000,
    )
    default_input_chars = max(12_000_000, max_model_attempts * 120_000)
    default_output_tokens = max(1_500_000, max_model_attempts * 16_000)
    runtime = ExecutionControlRuntime(
        max_concurrency=max_model_parallelism,
        max_model_attempts=max_model_attempts,
        max_input_chars=_clamp_execution_int(
            payload.get("max_model_input_chars") or default_input_chars,
            default_input_chars,
            1,
            2_000_000_000,
        ),
        max_requested_output_tokens=_clamp_execution_int(
            payload.get("max_model_output_tokens") or default_output_tokens,
            default_output_tokens,
            1,
            200_000_000,
        ),
        cancel_callback=cancel_callback,
    )
    policy = {
        "schema_version": "execution-policy-v1",
        "max_model_parallelism": max_model_parallelism,
        "chapter_task_parallelism": agent_parallelism,
        "variant_parallelism": variant_parallelism,
        **runtime.snapshot()["limits"],
    }
    payload["variants"] = variants_total
    payload["agent_parallelism"] = agent_parallelism
    payload["variant_parallelism"] = variant_parallelism
    payload["max_model_parallelism"] = max_model_parallelism
    payload["_execution_policy"] = policy
    return runtime, policy


def _set_output_variant_path(result: dict[str, Any], key: str, variant: int, value: str) -> None:
    values = list(result.get(key)) if isinstance(result.get(key), list) else []
    while len(values) < variant:
        values.append(None)
    values[variant - 1] = value
    result[key] = values


async def _render_professional_outputs_for_job(
    *,
    job_id: str,
    outputs: dict[str, Any],
    progress_callback: Any | None = None,
    execution_runtime: ExecutionControlRuntime | None = None,
) -> dict[str, Any]:
    """Promote Sonnet-refined DOCX files to the only user-facing Word outputs.

    The deterministic source export remains available under ``source_docx`` for
    audit and controlled re-rendering.  The public ``docx`` slot is replaced
    only after every requested variant passes the professional-render gates.
    """

    delivery = dict(outputs or {})
    raw_sources = delivery.get("source_docx")
    if not isinstance(raw_sources, list) or not raw_sources:
        raw_sources = delivery.get("docx")
    source_docx = [str(path) for path in raw_sources] if isinstance(raw_sources, list) else []
    if not source_docx:
        raise ProfessionalRenderError("中间 Word 不存在，无法自动生成专业交付版")
    if not delivery.get("json"):
        raise ProfessionalRenderError("生成结果 JSON 不存在，无法自动生成专业交付版")

    render_source = dict(delivery)
    render_source["docx"] = list(source_docx)
    professional_docx: list[str] = []
    professional_json: list[str] = []
    professional_receipts: list[str] = []
    total = len(source_docx)
    for variant in range(1, total + 1):
        if callable(progress_callback):
            progress_callback(variant, total)
        render_kwargs: dict[str, Any] = {
            "job_id": job_id,
            "variant": variant,
            "result": render_source,
        }
        if execution_runtime is not None:
            render_kwargs["execution_runtime"] = execution_runtime
        rendered = await render_professional_document(**render_kwargs)
        professional_docx.append(str(rendered["professional_docx"]))
        professional_json.append(str(rendered["professional_json"]))
        professional_receipts.append(str(rendered["professional_render_receipt"]))

    # Do not expose the deterministic intermediate as the main Word download.
    # This promotion occurs atomically after all variants pass rendering.
    delivery["source_docx"] = source_docx
    delivery["professional_docx"] = professional_docx
    delivery["professional_json"] = professional_json
    delivery["professional_render_receipt"] = professional_receipts
    delivery["docx"] = list(professional_docx)
    delivery["delivery_profile"] = "sonnet5_professional_word"
    sealed_delivery = build_delivery_receipt(
        job_id=job_id,
        source_docx=source_docx,
        professional_docx=professional_docx,
        professional_receipts=professional_receipts,
    )
    delivery["delivery_receipt"] = str(sealed_delivery["receipt"])
    delivery["delivery_decision_digest"] = str(sealed_delivery["decision_digest"])
    return delivery


def _rebuild_postprocessed_artifacts(
    results: list[dict],
    *,
    payload: dict,
    report: dict | None,
    params: dict | None,
    fail_closed: bool = False,
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

    postprocess_errors: list[dict[str, str]] = []

    # Normalize per-variant derived artifacts.
    for v in results:
        if not isinstance(v, dict):
            continue
        variant_error_start = len(postprocess_errors)
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
        except Exception as exc:
            postprocess_errors.append(
                {"stage": "plan_consistency", "error_type": type(exc).__name__, "message": str(exc)}
            )

        # Param trace receipt (in-place placeholder substitution).
        try:
            from backend.zhifei_autoplan.param_trace import build_param_receipt, save_latest_receipt

            receipt = build_param_receipt(sections, params)
            saved_at = save_latest_receipt(receipt, project_id=str(pid) if pid else None)
            v["param_trace"] = {"ok": True, "saved_at": saved_at, "receipt": receipt}
        except Exception as exc:
            postprocess_errors.append(
                {"stage": "param_trace", "error_type": type(exc).__name__, "message": str(exc)}
            )

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
        except Exception as exc:
            postprocess_errors.append(
                {"stage": "cross_index", "error_type": type(exc).__name__, "message": str(exc)}
            )
        try:
            v["evidence_tracking"] = build_evidence_tracking(
                sections=sections,
                tender=tender,
                chapter_pages=v.get("chapter_pages") if isinstance(v.get("chapter_pages"), dict) else {},
            )
        except Exception as exc:
            v["evidence_tracking"] = {"rows": [], "summary": {}}
            postprocess_errors.append(
                {"stage": "evidence_tracking", "error_type": type(exc).__name__, "message": str(exc)}
            )

        try:
            requirement_plan = (
                v.get("requirement_evidence_plan")
                if isinstance(v.get("requirement_evidence_plan"), dict)
                else {}
            )
            requirement_matrix = finalize_requirement_evidence_matrix(
                plan=requirement_plan,
                sections=sections,
                evidence_tracking=(
                    v.get("evidence_tracking")
                    if isinstance(v.get("evidence_tracking"), dict)
                    else {}
                ),
            )
            v["requirement_evidence_matrix"] = requirement_matrix
            v["requirement_evidence_validation"] = validate_requirement_evidence_matrix(
                requirement_matrix
            )
        except Exception as exc:
            postprocess_errors.append(
                {
                    "stage": "requirement_evidence_matrix",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

        try:
            standards_manifest = (
                v.get("project_applicable_standards")
                if isinstance(v.get("project_applicable_standards"), dict)
                else {}
            )
            v["standard_citation_audit"] = audit_standard_citations(
                sections,
                standards_manifest,
            )
        except Exception as exc:
            postprocess_errors.append(
                {
                    "stage": "standard_citation_audit",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

        try:
            routing = v.get("model_routing") if isinstance(v.get("model_routing"), dict) else {}
            delivery_gate = build_delivery_quality_gate(
                strict=strict,
                content_review=(
                    qc.get("independent_content_review")
                    if isinstance(qc.get("independent_content_review"), dict)
                    else {}
                ),
                plan_consistency=(
                    v.get("plan_consistency")
                    if isinstance(v.get("plan_consistency"), dict)
                    else {}
                ),
                model_review_audit=(
                    routing.get("review_audit")
                    if isinstance(routing.get("review_audit"), dict)
                    else {}
                ),
                requirement_matrix=(
                    v.get("requirement_evidence_matrix")
                    if isinstance(v.get("requirement_evidence_matrix"), dict)
                    else {}
                ),
                standard_audit=(
                    v.get("standard_citation_audit")
                    if isinstance(v.get("standard_citation_audit"), dict)
                    else {}
                ),
                cross_index=(
                    v.get("cross_index") if isinstance(v.get("cross_index"), dict) else {}
                ),
                model_review_required=(
                    str(routing.get("mode") or "") == "anthropic_tiered"
                    and not bool(payload.get("dry_run"))
                ),
            )
            v["delivery_quality_gate"] = delivery_gate
            qc["delivery_quality_gate"] = delivery_gate
            if not bool(delivery_gate.get("delivery_allowed")):
                postprocess_errors.append(
                    {
                        "stage": "delivery_quality_gate",
                        "error_type": "DeliveryQualityGateBlocked",
                        "message": json.dumps(
                            delivery_gate.get("blockers") or [],
                            ensure_ascii=False,
                        ),
                    }
                )
        except Exception as exc:
            postprocess_errors.append(
                {
                    "stage": "delivery_quality_gate",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

        variant_errors = postprocess_errors[variant_error_start:]
        if variant_errors:
            v["postprocess_errors"] = list(variant_errors)
        else:
            v.pop("postprocess_errors", None)

    if fail_closed and postprocess_errors:
        raise RuntimeError(
            json.dumps(
                {
                    "code": "POSTPROCESS_REBUILD_FAILED",
                    "message": "复核后的派生报告重建失败，候选版本未晋升。",
                    "errors": postprocess_errors,
                },
                ensure_ascii=False,
            )
        )


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
    title_to_digest: Dict[str, str] = {}
    for s in sections:
        if not isinstance(s, dict):
            continue
        t = str(s.get("title") or "").strip()
        if not t or t in title_to_excerpt:
            continue
        c = str(s.get("content") or "").strip()
        title_to_excerpt[t] = c[:max_excerpt] + ("..." if len(c) > max_excerpt else "")
        title_to_digest[t] = canonical_digest({"title": t, "content": c})

    out: list[dict] = []
    severity_rank = {"high": 3, "medium": 2, "low": 1}
    for it in issues:
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or "").strip() or "章节"
        source = "issue_list"
        row = {
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
        row["issue_id"] = stable_issue_id(row, section_digest=title_to_digest.get(title, ""))
        out.append(row)

    # Add recs not already covered by issue_list.
    seen = {(str(x.get("title")), str(x.get("type")), str(x.get("suggestion"))) for x in out}
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
        row = {
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
        row["issue_id"] = stable_issue_id(row, section_digest=title_to_digest.get(title, ""))
        out.append(row)
    out.sort(key=lambda x: (-int(x.get("severity_rank") or 0), str(x.get("title") or ""), str(x.get("type") or "")))
    return out


def _review_versions(variants: list[dict], idx: int) -> dict[str, str]:
    target = variants[idx]
    items = _review_items_for_variant(target)
    return {
        "result_version": result_version(variants),
        "variant_version": variant_version(target),
        "issue_digest": issue_set_digest(items),
    }


def _require_review_preconditions(
    *,
    variants: list[dict],
    idx: int,
    expected_result_version: str,
    expected_variant_version: str | None = None,
    expected_issue_digest: str | None = None,
) -> dict[str, str]:
    expected_result = str(expected_result_version or "").strip()
    expected_variant = str(expected_variant_version or "").strip()
    expected_issues = str(expected_issue_digest or "").strip()
    required = {"expected_result_version": expected_result}
    if expected_variant_version is not None:
        required["expected_variant_version"] = expected_variant
    if expected_issue_digest is not None:
        required["expected_issue_digest"] = expected_issues
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise HTTPException(
            status_code=428,
            detail={"code": "REVIEW_PRECONDITION_REQUIRED", "missing": missing},
        )

    live = _review_versions(variants, idx)
    mismatches = {}
    if expected_result != live["result_version"]:
        mismatches["result_version"] = live["result_version"]
    if expected_variant_version is not None and expected_variant != live["variant_version"]:
        mismatches["variant_version"] = live["variant_version"]
    if expected_issue_digest is not None and expected_issues != live["issue_digest"]:
        mismatches["issue_digest"] = live["issue_digest"]
    if mismatches:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "STALE_REVIEW_STATE",
                "message": "问题清单或文档已更新，请重新载入后再应用。",
                "live": mismatches,
            },
        )
    return live


def _review_quality_counts(items: list[dict]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0, "total": len(items)}
    for item in items:
        severity = str(item.get("severity") or "medium").lower()
        counts[severity if severity in counts else "medium"] += 1
    return counts


def _review_section_manifest(variant: dict) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    sections = variant.get("sections") if isinstance(variant.get("sections"), list) else []
    for section in sections:
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        content = str(section.get("content") or "")
        if title:
            rows[title] = {"sha256": canonical_digest(content), "characters": len(content)}
    return rows


def _review_section_changes(before: dict, after: dict) -> list[dict[str, Any]]:
    before_rows = _review_section_manifest(before)
    after_rows = _review_section_manifest(after)
    changes: list[dict[str, Any]] = []
    for title in sorted(set(before_rows) | set(after_rows)):
        old = before_rows.get(title, {"sha256": "", "characters": 0})
        new = after_rows.get(title, {"sha256": "", "characters": 0})
        if old["sha256"] == new["sha256"]:
            continue
        changes.append(
            {
                "title": title,
                "before_sha256": old["sha256"],
                "after_sha256": new["sha256"],
                "before_characters": old["characters"],
                "after_characters": new["characters"],
            }
        )
    return changes


def _find_review_target_section(sections: list[dict], item: dict) -> dict | None:
    """Resolve a QC item to one existing chapter without inventing a new chapter."""
    title = str(item.get("title") or "").strip()
    for section in sections:
        if isinstance(section, dict) and str(section.get("title") or "").strip() == title:
            return section

    issue_type = str(item.get("type") or "").strip().lower()
    candidates: tuple[str, ...]
    if issue_type == "consistency" or title == "全局一致性":
        candidates = ("进度", "工期", "关键线路", "资源", "施工部署")
    elif issue_type in {"boq_focus", "qse_closed_loop"} or title == "清单重点项":
        candidates = ("施工方案", "工程重点", "质量", "安全", "文明", "环保")
    else:
        candidates = (title,) if title else ()

    for keyword in candidates:
        for section in sections:
            section_title = str(section.get("title") or "").strip() if isinstance(section, dict) else ""
            if keyword and keyword in section_title:
                return section
    return None


def _clean_review_rewrite(text: str, *, title: str) -> str:
    value = str(text or "").strip()
    if value.startswith("```") and value.endswith("```"):
        value = re.sub(r"^```(?:markdown|md|text)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value).strip()
    lines = value.splitlines()
    if lines:
        first = re.sub(r"^\s*#{1,6}\s*", "", lines[0]).strip()
        if first in {title, f"第{title}"}:
            value = "\n".join(lines[1:]).strip()
    return value


def _safe_review_error(value: object) -> str:
    text = str(value or "provider_error")[:500]
    text = re.sub(r"(?:sk|sk-ant|AIza)[A-Za-z0-9_\-]{12,}", "[redacted]", text)
    return text


async def _rewrite_review_section(
    *,
    section: dict,
    issues: list[dict],
    payload: dict,
    round_number: int,
) -> tuple[str, dict]:
    """Use the configured review chain to revise one complete chapter."""
    title = str(section.get("title") or "章节").strip() or "章节"
    original = str(section.get("content") or "").strip()
    audit: dict[str, Any] = {
        "round": int(round_number),
        "title": title,
        "issue_ids": [str(item.get("issue_id") or "") for item in issues],
        "status": "failed",
        "attempts": [],
    }
    if not original:
        audit["error"] = "empty_section_content"
        return "", audit

    issue_lines = []
    for index, item in enumerate(issues, start=1):
        issue_lines.append(
            f"{index}. 类型：{str(item.get('type') or 'issue')}；"
            f"级别：{str(item.get('severity') or 'medium')}；"
            f"问题：{str(item.get('problem') or '').strip()}；"
            f"修订要求：{str(item.get('suggestion') or '').strip()}"
        )
    prompt = f"""你是施工组织设计技术标的资深复核工程师。请对下面的完整章节执行第{round_number}轮闭环精修。

硬约束：
1. 只修订现有章节《{title}》，不得新增、删除或重命名章节。
2. 必须逐项解决所列问题，同时保留原文中已有的项目事实、工程量、参数、证据标记和可执行措施。
3. 不得编造项目事实、工程量、工期、规范名称、规范编号、人员资质、设备型号或验收结论；没有依据的内容使用“以经审查文件/现场确认结果为准”的受控表达。
4. 统一前后矛盾的工期、资源峰值、关键线路间隔等口径；补充内容必须形成“指标/措施—风险—控制—验证—证据”的闭环。
5. 删除空话、套话、与本项目无关的内容，语言应专业、具体、可复核。
6. 仅输出修订后的完整章节正文，不要输出标题、解释、前言、总结说明、Markdown代码围栏或JSON。

待解决问题：
{chr(10).join(issue_lines)}

原章节正文：
{original}
"""

    chain = _provider_chain_for_role(
        _normalize_provider_chain(payload),
        "review",
        allow_fable_escalation=bool(payload.get("allow_fable_escalation", False)),
    )
    for entry in chain:
        provider = str(entry.get("provider") or "").strip().lower()
        model = str(entry.get("model") or "").strip()
        slot = str(entry.get("slot") or "").strip()
        if not provider or not model:
            continue
        api_key = _resolve_provider_api_key(
            payload,
            provider,
            slot_id=slot,
            explicit_key=str(entry.get("api_key") or ""),
        )
        attempt: dict[str, Any] = {"slot": slot, "provider": provider, "model": model}
        client = LLMClient(
            provider,
            model,
            api_key=api_key,
            base_url=payload.get("base_url"),
            secret_key=payload.get("secret_key"),
            token_url=payload.get("token_url"),
        )
        response = await client.complete(prompt, timeout=240, max_tokens=12000)
        rewritten = _clean_review_rewrite(str(response.get("text") or ""), title=title)
        if rewritten:
            attempt["status"] = "success"
            audit["attempts"].append(attempt)
            audit.update({"status": "success", "provider": provider, "model": model, "slot": slot})
            return rewritten, audit
        attempt.update({"status": "failed", "error": _safe_review_error(response.get("error"))})
        audit["attempts"].append(attempt)

    audit["error"] = "review_chain_exhausted"
    return "", audit


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


def _zbid_mock_api_enabled() -> bool:
    return os.environ.get("ZDOC_ZBID_MOCK_API_ENABLED", "").strip() == "1"


def _zbid_mock_api_base_response(*, ok: bool, status: str, data: dict | None, error: str | None = None) -> dict:
    return {
        "ok": ok,
        "status": status,
        "mode": "mock_only",
        "draft_only": True,
        "no_write": True,
        "source_system": "zbid",
        "data": data,
        "error": error,
    }


@router.post("/zbid/snapshot_draft_input/preview")
async def actions_zbid_snapshot_draft_input_preview(
    req: ActionsZBidSnapshotDraftInputPreviewRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    if not _zbid_mock_api_enabled():
        return _zbid_mock_api_base_response(
            ok=False,
            status="disabled",
            data=None,
            error="zbid_mock_api_disabled",
        )

    try:
        data = map_zbid_snapshot_to_zdoc_draft_input(req.snapshot)
    except ValueError as exc:
        detail = _zbid_mock_api_base_response(
            ok=False,
            status="validation_error",
            data=None,
            error="validation_error",
        )
        detail["message"] = str(exc)
        raise HTTPException(status_code=400, detail=detail) from None

    return _zbid_mock_api_base_response(
        ok=True,
        status="mapped",
        data=data,
    )


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
    return (req_model or os.environ.get("OLLAMA_MODEL") or "qwen3.5:4b").strip() or "qwen3.5:4b"


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


@router.post("/professional_render")
async def actions_professional_render(
    req: ActionsProfessionalRenderRequest,
    x_actions_key: str | None = Header(default=None),
):
    """Controlled re-render endpoint; normal generation already renders automatically."""

    _auth_actions_key(x_actions_key)
    job_id = str(req.job_id or "").strip()
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.get("status") != "done":
        raise HTTPException(status_code=409, detail=f"job not done: {job.get('status')}")
    result = dict(job.get("result") or {})
    variant = max(1, int(req.variant or 1))
    render_source = dict(result)
    source_docx = result.get("source_docx")
    if isinstance(source_docx, list) and source_docx:
        render_source["docx"] = list(source_docx)
    try:
        rendered = await render_professional_document(
            job_id=job_id,
            variant=variant,
            result=render_source,
        )
    except ProfessionalRenderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"专业精修与渲染失败: {exc}") from exc

    if not isinstance(result.get("source_docx"), list):
        existing_docx = result.get("docx")
        result["source_docx"] = list(existing_docx) if isinstance(existing_docx, list) else []
    _set_output_variant_path(result, "professional_docx", variant, rendered["professional_docx"])
    _set_output_variant_path(result, "professional_json", variant, rendered["professional_json"])
    _set_output_variant_path(
        result,
        "professional_render_receipt",
        variant,
        rendered["professional_render_receipt"],
    )
    _set_output_variant_path(result, "docx", variant, rendered["professional_docx"])
    result["delivery_profile"] = "sonnet5_professional_word"
    update_job(job_id, status="done", result=result, error=None)
    return {
        "ok": True,
        "job_id": job_id,
        "variant": variant,
        "display_model": rendered["receipt"].get("display_model"),
        "model_id": rendered["receipt"].get("model_id"),
        "quality_gate": rendered["receipt"].get("quality_gate"),
        "files": {
            "professional_docx": rendered["professional_docx"],
            "professional_json": rendered["professional_json"],
            "professional_render_receipt": rendered["professional_render_receipt"],
        },
    }


@router.post("/generate")
async def actions_generate(req: ActionsGenerateRequest, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    payload = _merge_plan_defaults(req.model_dump())
    resume_from_job_id = str(payload.get("resume_from_job_id") or "").strip()
    if resume_from_job_id:
        if not re.fullmatch(r"[a-f0-9]{32}", resume_from_job_id):
            raise HTTPException(status_code=400, detail="invalid resume_from_job_id")
        source_job = get_job(resume_from_job_id)
        if not source_job:
            raise HTTPException(status_code=404, detail="resume source job not found")
        if str(source_job.get("status") or "").strip().lower() not in {"failed", "cancelled"}:
            raise HTTPException(
                status_code=409,
                detail="only failed or cancelled jobs can be resumed",
            )
    variant_plan = _build_variant_plan(payload)
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(v.get("variant_id") or 1) for v in variant_plan]
    payload["variants"] = len(variant_plan) if variant_plan else int(payload.get("variants") or 1)
    execution_runtime, execution_policy = _prepare_execution_control(payload)

    ordered_results: list[dict[str, Any] | None] = [None] * len(variant_plan)
    direct_sem = asyncio.Semaphore(int(execution_policy["variant_parallelism"]))

    async def _run_direct_variant(position: int, item: dict[str, Any]) -> None:
        local_payload = json.loads(json.dumps(payload))
        local_payload["variant_id"] = int(item.get("variant_id") or 1)
        tid = _normalize_logic_template_id(item.get("logic_template_id"))
        if tid:
            local_payload["logic_template_id"] = tid
        # Runtime/callback objects are deliberately attached only after cloning.
        local_payload["_execution_runtime"] = execution_runtime
        async with direct_sem:
            ordered_results[position] = await run_autoplan(local_payload)

    await asyncio.gather(
        *[_run_direct_variant(i, item) for i, item in enumerate(variant_plan)]
    )
    results = [item for item in ordered_results if isinstance(item, dict)]
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
    outputs = await _render_professional_outputs_for_job(
        job_id=f"direct-{uuid.uuid4().hex}",
        outputs=outputs,
        execution_runtime=execution_runtime,
    )
    quality = [v.get("quality_checks") for v in results]
    return {
        "ok": True,
        "result": results,
        "quality": quality,
        "files": outputs,
        "execution_control": execution_runtime.snapshot(),
    }


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
        heartbeat_stop = threading.Event()
        heartbeat_thread: threading.Thread | None = None
        try:
            local_payload = _apply_generation_mode_policy(json.loads(json.dumps(_payload)))
            local_payload["_job_id"] = _job_id

            def _is_cancelled() -> bool:
                j = get_job(_job_id) or {}
                return str(j.get("status") or "").strip().lower() == "cancelled"

            execution_runtime, execution_policy = _prepare_execution_control(
                local_payload,
                cancel_callback=_is_cancelled,
            )
            variants_total = int(local_payload["variants"])
            agent_parallelism = int(execution_policy["chapter_task_parallelism"])
            variant_parallelism = int(execution_policy["variant_parallelism"])
            max_model_parallelism = int(execution_policy["max_model_parallelism"])

            agent_runtime = {
                "mode": "parallel",
                "master_agent": "主控Agent",
                "compliance_agent": "合规Agent",
                "specialist_role_count": len(AGENT_ROLE_DIRECTIVES),
                "parallelism_semantics": "bounded_chapter_tasks_not_agent_count",
                "agent_parallelism": agent_parallelism,
                "variant_parallelism": variant_parallelism,
                "max_model_parallelism": max_model_parallelism,
                "variants_total": variants_total,
                "variants_done": 0,
                "chapters_total": 0,
                "chapters_started": 0,
                "chapters_done": 0,
                "active_agents": 0,
                "current_chapters": [],
            }
            activity_lock = threading.RLock()
            activity_state: Dict[str, Any] = {
                "activity": "主控Agent正在准备章节任务",
                "chapter_totals": {},
                "started": set(),
                "completed": set(),
                "active": {},
            }

            def _activity_snapshot() -> tuple[str, Dict[str, Any]]:
                with activity_lock:
                    runtime = dict(agent_runtime)
                    current = [str(x) for x in activity_state.get("active", {}).values() if str(x).strip()]
                    runtime.update(
                        {
                            "chapters_total": int(sum(activity_state.get("chapter_totals", {}).values())),
                            "chapters_started": len(activity_state.get("started", set())),
                            "chapters_done": len(activity_state.get("completed", set())),
                            "active_agents": len(current),
                            "current_chapters": current[:6],
                        }
                    )
                    agent_runtime.update(runtime)
                    return str(activity_state.get("activity") or "Agent正在工作"), runtime

            def _heartbeat_loop() -> None:
                while not heartbeat_stop.is_set():
                    activity, runtime = _activity_snapshot()
                    heartbeat_job(
                        _job_id,
                        activity=activity,
                        agent_runtime_updates=runtime,
                    )
                    heartbeat_stop.wait(5.0)

            def _variant_progress_callback(variant_id: int):
                def _callback(event: Dict[str, Any]) -> None:
                    event_name = str(event.get("event") or "").strip()
                    chapter_idx = int(event.get("chapter_index") or 0)
                    chapter_title = str(event.get("chapter_title") or "").strip()
                    total = max(0, int(event.get("chapters_total") or 0))
                    variant_key = str(int(variant_id))
                    chapter_key = f"{variant_key}:{chapter_idx}"
                    with activity_lock:
                        if total:
                            activity_state["chapter_totals"][variant_key] = total
                        if event_name == "compliance_preflight":
                            verified_count = max(
                                0,
                                int(event.get("verified_standard_count") or 0),
                            )
                            if bool(event.get("ready")) and verified_count > 0:
                                activity_state["activity"] = (
                                    f"合规Agent已完成生成前预检：{verified_count}项项目适用规范通过核验"
                                )
                            else:
                                activity_state["activity"] = (
                                    "合规Agent正在核验项目适用规范，尚未进入内容生成"
                                )
                        elif event_name == "chapter_started":
                            activity_state["started"].add(chapter_key)
                            activity_state["active"][chapter_key] = chapter_title
                        elif event_name == "chapter_resumed":
                            activity_state["started"].add(chapter_key)
                            activity_state["completed"].add(chapter_key)
                            activity_state["active"].pop(chapter_key, None)
                            activity_state["activity"] = f"已从可信断点恢复章节：{chapter_title}"
                        elif event_name == "chapter_checkpoint_saved":
                            activity_state["activity"] = f"章节已安全保存，可断点续编：{chapter_title}"
                        elif event_name == "chapter_completed":
                            activity_state["started"].add(chapter_key)
                            activity_state["completed"].add(chapter_key)
                            activity_state["active"].pop(chapter_key, None)
                        elif event_name == "draft_complete":
                            activity_state["activity"] = "章节初稿完成，合规Agent正在复核与校验"

                        current = [
                            str(x)
                            for x in activity_state.get("active", {}).values()
                            if str(x).strip()
                        ]
                        if current:
                            preview = "、".join(current[:3])
                            suffix = "…" if len(current) > 3 else ""
                            activity_state["activity"] = (
                                f"{len(current)}个章节任务正在编辑：{preview}{suffix}"
                            )
                        done = len(activity_state.get("completed", set()))
                        all_total = int(sum(activity_state.get("chapter_totals", {}).values()))

                    progress_updates: Dict[str, Any] = {
                        "chapters_total": all_total,
                        "chapters_done": done,
                    }
                    if all_total > 0:
                        progress_updates["percent"] = min(75, 15 + int((done / all_total) * 60))
                    activity, runtime = _activity_snapshot()
                    heartbeat_job(
                        _job_id,
                        activity=activity,
                        progress_updates=progress_updates,
                        agent_runtime_updates=runtime,
                    )

                return _callback

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

            agent_runtime["execution_control"] = execution_runtime.snapshot()

            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user")
                return
            update_job(_job_id, status="running", agent_runtime=agent_runtime)
            heartbeat_thread = threading.Thread(
                target=_heartbeat_loop,
                name=f"autoplan-heartbeat-{_job_id[:8]}",
                daemon=True,
            )
            heartbeat_thread.start()
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
                (
                    f"{len(AGENT_ROLE_DIRECTIVES)}个专业角色已进入任务编排："
                    f"同时编写章节={agent_parallelism}，方案并行={variant_parallelism}"
                ),
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
                    lp["_progress_callback"] = _variant_progress_callback(vid)
                    lp["_job_id"] = _job_id
                    lp["_checkpoint_namespace"] = str(
                        local_payload.get("resume_from_job_id") or _job_id
                    )
                    lp["_cancel_callback"] = _is_cancelled
                    lp["_execution_runtime"] = execution_runtime
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
            agent_runtime["execution_control"] = execution_runtime.snapshot()
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
            _update_progress(91, "exporting_source", "正在生成可追溯中间稿与质控附件")
            outputs = _save_outputs(f"actions_{_job_id}", results)
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user", result=outputs)
                return

            def _professional_progress(variant: int, total: int) -> None:
                percent = 93 + int(((variant - 1) / max(1, total)) * 6)
                detail = f"Sonnet 5 正在精修并专业落版：方案 {variant}/{total}"
                with activity_lock:
                    activity_state["activity"] = detail
                _update_progress(percent, "professional_rendering", detail)

            _update_progress(
                93,
                "professional_rendering",
                "Sonnet 5 正在逐章精修、统一视觉规范并执行 Word 质量闸门",
            )
            outputs = asyncio.run(
                _render_professional_outputs_for_job(
                    job_id=_job_id,
                    outputs=outputs,
                    progress_callback=_professional_progress,
                    execution_runtime=execution_runtime,
                )
            )
            agent_runtime["execution_control"] = execution_runtime.snapshot()
            if _is_cancelled():
                update_job(_job_id, status="cancelled", error="cancelled_by_user", result=outputs)
                return
            _update_progress(100, "done", "专业 Word 已完成，可直接下载")
            update_job(_job_id, status="done", result=outputs, agent_runtime=agent_runtime)
        except Exception as e:
            error_text = repr(e)
            cancel_probe = locals().get("_is_cancelled")
            was_cancelled = bool(cancel_probe()) if callable(cancel_probe) else False
            if was_cancelled or "cancelled_by_user" in error_text:
                prior_progress = ((get_job(_job_id) or {}).get("progress") or {})
                update_job(
                    _job_id,
                    status="cancelled",
                    error="cancelled_by_user",
                    progress={
                        "percent": int(prior_progress.get("percent") or 0),
                        "stage": "cancelled",
                        "detail": "用户已取消；未完成章节已停止，已完成章节保留为可信断点。",
                    },
                )
            else:
                update_job(
                    _job_id,
                    status="failed",
                    error=error_text,
                    progress={"percent": 100, "stage": "failed", "detail": error_text},
                )
        finally:
            heartbeat_stop.set()
            if heartbeat_thread is not None and heartbeat_thread.is_alive():
                heartbeat_thread.join(timeout=0.25)

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
    idx = (v - 1) if v <= len(variants) else 0
    items = _review_items_for_variant(rec)
    versions = _review_versions(variants, idx)
    return {
        "ok": True,
        "job_id": job_id,
        "variant": int(v if v <= len(variants) else 1),
        "count": len(items),
        "items": items,
        **versions,
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
    job, current_result, _, variants = _load_done_job_variants(job_id)

    v = max(1, int(req.variant or 1))
    idx = (v - 1) if v <= len(variants) else 0
    if not isinstance(variants[idx], dict):
        raise HTTPException(status_code=400, detail="invalid variant record")

    live_versions = _require_review_preconditions(
        variants=variants,
        idx=idx,
        expected_result_version=req.expected_result_version,
        expected_variant_version=req.expected_variant_version,
        expected_issue_digest=req.expected_issue_digest,
    )
    original_target = variants[idx]
    original_items = _review_items_for_variant(original_target)
    original_quality = _review_quality_counts(original_items)
    candidate_variants = copy.deepcopy(variants)
    target = candidate_variants[idx]

    items = _review_items_for_variant(original_target)
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
            **live_versions,
        }

    revision = create_revision_snapshot(
        job_id=job_id,
        variants=copy.deepcopy(variants),
        result=current_result,
        reason="pre_review_apply",
        metadata={
            "actor": str(req.actor or "webui").strip() or "webui",
            "variant": idx + 1,
            "selected_issue_ids": [str(item.get("issue_id") or "") for item in selected],
            "expected_issue_digest": req.expected_issue_digest,
        },
    )

    sections = target.get("sections") if isinstance(target.get("sections"), list) else []
    if not isinstance(sections, list):
        raise HTTPException(status_code=400, detail="variant sections missing")

    remediation = []
    replacement_count = 0
    ai_rewritten_count = 0
    fallback_count = 0
    review_audit: list[dict] = []
    grouped: dict[str, dict[str, Any]] = {}
    for item in selected:
        section = _find_review_target_section(sections, item)
        replacement = str(item.get("replacement") or "").strip()
        if replacement and section is not None:
            section.setdefault("pre_review_apply_content", section.get("content") or "")
            section["content"] = replacement
            section["auto_remediated"] = "review_apply_manual_replacement"
            replacement_count += 1
            review_audit.append(
                {
                    "round": 1,
                    "title": str(section.get("title") or ""),
                    "issue_ids": [str(item.get("issue_id") or "")],
                    "status": "manual_replacement",
                }
            )
            continue
        if section is None:
            remediation.append(
                {
                    "title": str(item.get("title") or "").strip(),
                    "type": str(item.get("type") or "issue").strip(),
                    "suggestion": str(item.get("suggestion") or item.get("problem") or "").strip(),
                }
            )
            fallback_count += 1
            continue
        section_title = str(section.get("title") or "").strip()
        grouped.setdefault(section_title, {"section": section, "items": []})["items"].append(item)

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

    modified_titles: set[str] = set()
    for section in sections:
        if isinstance(section, dict) and section.get("auto_remediated") == "review_apply_manual_replacement":
            modified_titles.add(str(section.get("title") or "").strip())
    for group in grouped.values():
        section = group["section"]
        group_items = group["items"]
        rewritten, audit = await _rewrite_review_section(
            section=section,
            issues=group_items,
            payload=payload_obj,
            round_number=1,
        )
        review_audit.append(audit)
        if rewritten:
            section.setdefault("pre_review_apply_content", section.get("content") or "")
            section["content"] = rewritten
            section["auto_remediated"] = "review_apply_ai_round_1"
            section["review_apply_model"] = {
                "provider": audit.get("provider"),
                "model": audit.get("model"),
                "slot": audit.get("slot"),
            }
            section["review_apply_issue_ids"] = list(audit.get("issue_ids") or [])
            modified_titles.add(str(section.get("title") or "").strip())
            ai_rewritten_count += 1
            continue
        for item in group_items:
            remediation.append(
                {
                    "title": str(item.get("title") or "").strip(),
                    "type": str(item.get("type") or "issue").strip(),
                    "suggestion": str(item.get("suggestion") or item.get("problem") or "").strip(),
                }
            )
            fallback_count += 1

    if remediation:
        apply_remediation(
            sections,
            remediation,
            project_id=pid,
            boq_focus=boq_focus,
            params=params,
        )
        for item in selected:
            section = _find_review_target_section(sections, item)
            if isinstance(section, dict):
                modified_titles.add(str(section.get("title") or "").strip())
    for sec in sections:
        if isinstance(sec, dict):
            sec["content"] = strip_nonconcrete_language(str(sec.get("content") or ""))

    # Rebuild receipts/QC/cross-index after round 1. This is the first full-document recheck.
    _rebuild_postprocessed_artifacts(
        [target], payload=payload_obj, report=None, params=params, fail_closed=True
    )

    round_2_recheck_count = 0
    round_2_rewritten_count = 0
    if modified_titles:
        remaining_items = _review_items_for_variant(target)
        round_2_groups: dict[str, dict[str, Any]] = {}
        for item in remaining_items:
            if int(item.get("severity_rank") or 0) < 2:
                continue
            section = _find_review_target_section(sections, item)
            section_title = str(section.get("title") or "").strip() if isinstance(section, dict) else ""
            if not section_title or section_title not in modified_titles:
                continue
            round_2_groups.setdefault(section_title, {"section": section, "items": []})["items"].append(item)
        round_2_recheck_count = sum(len(group["items"]) for group in round_2_groups.values())
        for group in round_2_groups.values():
            section = group["section"]
            rewritten, audit = await _rewrite_review_section(
                section=section,
                issues=group["items"],
                payload=payload_obj,
                round_number=2,
            )
            review_audit.append(audit)
            if not rewritten:
                continue
            section["content"] = rewritten
            section["auto_remediated"] = "review_apply_ai_round_2"
            section["review_apply_model"] = {
                "provider": audit.get("provider"),
                "model": audit.get("model"),
                "slot": audit.get("slot"),
            }
            section["review_apply_issue_ids"] = list(audit.get("issue_ids") or [])
            round_2_rewritten_count += 1
        if round_2_rewritten_count:
            for sec in sections:
                if isinstance(sec, dict):
                    sec["content"] = strip_nonconcrete_language(str(sec.get("content") or ""))
            # A second rebuild is mandatory after AI round 2 so all derivative
            # reports, evidence tables and exported files describe final text.
            _rebuild_postprocessed_artifacts(
                [target], payload=payload_obj, report=None, params=params, fail_closed=True
            )

    final_review_items = _review_items_for_variant(target)
    final_quality = _review_quality_counts(final_review_items)
    remaining_high = [item for item in final_review_items if str(item.get("severity") or "").lower() == "high"]
    target["review_apply_audit"] = {
        "revision_id": revision["revision_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "actor": str(req.actor or "webui").strip() or "webui",
        "before_result_version": live_versions["result_version"],
        "before_variant_version": live_versions["variant_version"],
        "before_issue_digest": live_versions["issue_digest"],
        "selected_count": len(selected),
        "ai_rewritten_chapter_count": ai_rewritten_count,
        "manual_replacement_count": replacement_count,
        "template_fallback_item_count": fallback_count,
        "round_2_recheck_item_count": round_2_recheck_count,
        "round_2_rewritten_chapter_count": round_2_rewritten_count,
        "remaining_issue_count": len(final_review_items),
        "before_quality_counts": original_quality,
        "after_quality_counts": final_quality,
        "section_changes": _review_section_changes(original_target, target),
        "candidate_section_digest": canonical_digest(_review_section_manifest(target)),
        "promotion": "validated_for_commit",
        "rounds": review_audit,
    }

    if remaining_high:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "REVIEW_HIGH_RISK_REMAINS",
                "message": "复核后仍存在高风险问题，候选版本未晋升，当前 Word 保持不变。",
                "revision_id": revision["revision_id"],
                "remaining_high_count": len(remaining_high),
                "remaining_issue_count": len(final_review_items),
            },
        )

    # Candidate outputs use unique paths.  The live job is promoted only after
    # persistence, professional rendering and every gate above has succeeded.
    candidate_version = result_version(candidate_variants)
    candidate_suffix = revision["revision_id"].lower()
    out = _save_outputs(f"actions_{job_id}_{candidate_suffix}", candidate_variants)
    out = await _render_professional_outputs_for_job(
        job_id=f"{job_id}-{candidate_suffix}",
        outputs=out,
    )
    candidate_artifacts = artifact_manifest(out)
    finalize_revision_snapshot(
        job_id=job_id,
        revision_id=revision["revision_id"],
        promotion={
            "actor": str(req.actor or "webui").strip() or "webui",
            "candidate_result_version": candidate_version,
            "candidate_variant_version": variant_version(target),
            "candidate_issue_digest": issue_set_digest(final_review_items),
            "candidate_artifact_digest": canonical_digest(candidate_artifacts),
            "artifacts": candidate_artifacts,
        },
    )
    update_job(job_id, status="done", result=out, error=None)

    return {
        "ok": True,
        "job_id": job_id,
        "variant": idx + 1,
        "applied_count": len(selected),
        "template_applied_count": len(remediation),
        "replacement_count": replacement_count,
        "ai_rewritten_chapter_count": ai_rewritten_count,
        "template_fallback_item_count": fallback_count,
        "round_2_recheck_item_count": round_2_recheck_count,
        "round_2_rewritten_chapter_count": round_2_rewritten_count,
        "remaining_issue_count": len(final_review_items),
        "revision_id": revision["revision_id"],
        "result_version": candidate_version,
        "variant_version": variant_version(target),
        "issue_digest": issue_set_digest(final_review_items),
        "candidate_artifact_digest": canonical_digest(candidate_artifacts),
        "files": out,
    }


@router.get("/review/revisions")
async def actions_review_revisions(
    job_id: str,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    _load_done_job_variants(job_id)
    return {"ok": True, "job_id": job_id, "revisions": list_revision_snapshots(job_id=job_id)}


@router.post("/review/rollback")
async def actions_review_rollback(
    req: ActionsReviewRollbackRequest,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    job_id = str(req.job_id or "").strip()
    revision_id = str(req.revision_id or "").strip()
    if not job_id or not revision_id:
        raise HTTPException(status_code=400, detail="job_id and revision_id required")
    _, current_result, _, current_variants = _load_done_job_variants(job_id)
    _require_review_preconditions(
        variants=current_variants,
        idx=0,
        expected_result_version=req.expected_result_version,
    )
    try:
        revision = load_revision_snapshot(job_id=job_id, revision_id=revision_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="revision not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=f"invalid revision: {exc}")

    safety = create_revision_snapshot(
        job_id=job_id,
        variants=copy.deepcopy(current_variants),
        result=current_result,
        reason="pre_review_rollback",
        metadata={
            "actor": str(req.actor or "webui").strip() or "webui",
            "restore_revision_id": revision_id,
        },
    )
    restored_variants = copy.deepcopy(revision["variants"])
    restored_version = result_version(restored_variants)
    candidate_suffix = f"rollback-{revision_id.lower()}-{safety['revision_id'].lower()}"
    out = _save_outputs(f"actions_{job_id}_{candidate_suffix}", restored_variants)
    out = await _render_professional_outputs_for_job(
        job_id=f"{job_id}-{candidate_suffix}",
        outputs=out,
    )
    rollback_artifacts = artifact_manifest(out)
    finalize_revision_snapshot(
        job_id=job_id,
        revision_id=safety["revision_id"],
        promotion={
            "actor": str(req.actor or "webui").strip() or "webui",
            "operation": "rollback",
            "restored_revision_id": revision_id,
            "candidate_result_version": restored_version,
            "candidate_artifact_digest": canonical_digest(rollback_artifacts),
            "artifacts": rollback_artifacts,
        },
    )
    update_job(job_id, status="done", result=out, error=None)
    return {
        "ok": True,
        "job_id": job_id,
        "restored_revision_id": revision_id,
        "safety_revision_id": safety["revision_id"],
        "result_version": restored_version,
        "candidate_artifact_digest": canonical_digest(rollback_artifacts),
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
            "professional_docx": (result.get("professional_docx") or [None])[v - 1]
            if isinstance(result.get("professional_docx"), list)
            else result.get("professional_docx"),
            "professional_render_receipt": (result.get("professional_render_receipt") or [None])[v - 1]
            if isinstance(result.get("professional_render_receipt"), list)
            else result.get("professional_render_receipt"),
            "delivery_receipt": result.get("delivery_receipt"),
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
    kind: str = "docx",  # docx|professional_docx|compare_docx|json|delivery_receipt|focus_xlsx|score_overview_xlsx|expert_review_docx
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
    if kind in (
        "docx",
        "professional_docx",
        "professional_json",
        "professional_render_receipt",
        "compare_docx",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    ) and isinstance(path, list):
        v = max(1, int(variant or 1))
        path = path[v - 1] if v <= len(path) else None
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="file not found")
    if kind in {"json", "professional_json", "professional_render_receipt", "delivery_receipt"}:
        media_type = "application/json"
        if kind == "json":
            filename = f"autoplan_{job_id}.json"
        elif kind == "delivery_receipt":
            filename = f"autoplan_{job_id}_delivery_receipt.json"
        else:
            suffix = "_professional" if kind == "professional_json" else "_professional_receipt"
            filename = f"autoplan_{job_id}{suffix}_v{max(1, int(variant or 1))}.json"
    elif kind == "focus_xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"autoplan_{job_id}_focus_v{max(1, int(variant or 1))}.xlsx"
    elif kind == "score_overview_xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{max(1, int(variant or 1))}.xlsx"
    elif kind == "expert_review_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_专家复核提要版_v{max(1, int(variant or 1))}.docx"
    elif kind == "professional_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_Sonnet5专业精修版_v{max(1, int(variant or 1))}.docx"
    elif kind == "compare_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_compare_v{max(1, int(variant or 1))}.docx"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_v{max(1, int(variant or 1))}.docx"
    return FileResponse(str(path), media_type=media_type, filename=filename)
