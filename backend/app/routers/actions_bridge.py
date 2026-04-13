from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import FileResponse

from backend.app.core import actions_download_response as download_response_core
from backend.app.core import actions_error_view as error_view_core
from backend.app.core import actions_generate_view as generate_view_core
from backend.app.core import actions_job_cancel_view as job_cancel_view_core
from backend.app.core import actions_job_status_response as job_status_response_core
from backend.app.core import actions_recent_view as recent_view_core
from backend.app.core import actions_review_view as review_view_core
from backend.app.core import actions_result_response as result_response_core
from backend.app.core import actions_result_view as result_view_core
from backend.app.core import actions_usage_view as usage_view_core
from backend.zhifei_autoplan import generate_request_service as generate_request_core
from backend.zhifei_autoplan import generate_sync_service as generate_sync_core
from backend.zhifei_autoplan import export_docx_service as export_docx_core
from backend.zhifei_autoplan import job_cancel_service as job_cancel_core
from backend.zhifei_autoplan import load_done_job_service as load_done_job_core
from backend.zhifei_autoplan import download_request_service as download_request_core
from backend.zhifei_autoplan import result_read_service as result_read_core
from backend.zhifei_autoplan import runtime_payload_service as runtime_payload_core
from backend.zhifei_autoplan.exporter import export_autoplan_compare_docx, export_autoplan_docx, export_autoplan_focus_xlsx
from backend.zhifei_autoplan.job_store import (
    compute_job_signature,
    create_job,
    discover_recent_jobs,
    find_reusable_job,
    get_job,
    has_result_artifacts,
    list_jobs,
    update_job,
    cleanup_jobs,
    mark_stale_running_jobs,
    reconcile_job_runtime,
)
from backend.zhifei_autoplan.orchestrator import run_autoplan
from backend.zhifei_autoplan.plan_store import load_plan, save_plan
from backend.zhifei_autoplan.parsers.tender_parser import TenderParser
from backend.zhifei_autoplan.parsers.boq_parser import BoQParser
from backend.zhifei_autoplan.tender_store import save_tender_matrix
from backend.zhifei_autoplan.tender_store import save_bidding_format_config
from backend.zhifei_autoplan.boq_store import save_boq_data
from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.quality_check import apply_remediation, run_quality_checks
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.params_runtime import load_params, save_params
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.resource_audit import append_resource_event, summarize_variants
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids
from backend.zhifei_autoplan.docx_formatter import build_bidding_format_config_from_style
from backend.zhifei_autoplan import generation_mode_policy as generation_mode_core
from backend.zhifei_autoplan import output_artifacts as output_artifacts_core
from backend.zhifei_autoplan import postprocessed_artifacts as postprocess_core
from backend.zhifei_autoplan.provider_runtime import apply_server_provider_routing
from backend.zhifei_autoplan import review_apply_service as review_apply_core
from backend.zhifei_autoplan import review_result_rebuild as review_rebuild_core
from backend.zhifei_autoplan.case_library_service import normalize_case_library_options
from backend.zhifei_autoplan.image_library import (
    image_library_record_id,
    list_image_library_items,
    normalize_image_library_options,
    normalize_text_list,
    summarize_image_library,
)
from backend.zhifei_autoplan.project_types import ordered_project_types
from backend.zhifei_autoplan.template_library import list_template_library_items, summarize_template_library, template_library_record_id
from backend.zhifei_autoplan.run_contract import (
    attach_contract_stamp,
)
from backend.zhifei_autoplan.self_evolution import summarize_runtime_budget_profile
from backend.zhifei_autoplan.chief_engineer_agent import load_chief_engineer_state
from backend.zhifei_autoplan.job_admission import admission_http_detail, apply_admission_degrade, evaluate_job_admission
from backend.zhifei_autoplan.workspace import maybe_cleanup_expired_workspaces, resolve_workspace_dir, workspace_paths


router = APIRouter(prefix="/actions", tags=["Actions Bridge"])
_HOUSEKEEP_LAST_TS = 0.0
_HOUSEKEEP_LAST_REPORT: Dict[str, Any] = {}
WORKER_LOG_DIR = Path("logs/job_workers")
WORKER_LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("zhifei.actions")

_DOWNLOAD_KIND_SPECS: Dict[str, Dict[str, str]] = {
    "docx": {
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename_pattern": "autoplan_{job_id}_v{variant}.docx",
    },
    "compare_docx": {
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename_pattern": "autoplan_{job_id}_compare_v{variant}.docx",
    },
    "json": {
        "media_type": "application/json",
        "filename_pattern": "autoplan_{job_id}.json",
    },
    "result_bundle_json": {
        "media_type": "application/json",
        "filename_pattern": "autoplan_{job_id}_result_bundle.json",
    },
    "focus_xlsx": {
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "filename_pattern": "autoplan_{job_id}_focus_v{variant}.xlsx",
    },
    "score_overview_xlsx": {
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "filename_pattern": "autoplan_{job_id}_评分点覆盖与证据引用总览_v{variant}.xlsx",
    },
    "expert_review_docx": {
        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "filename_pattern": "autoplan_{job_id}_专家复核提要版_v{variant}.docx",
    },
}


def _resolve_workspace_context(
    session_id: str | None = None,
    workspace_dir: str | None = None,
) -> Dict[str, str]:
    resolved = resolve_workspace_dir(session_id=session_id, workspace_dir=workspace_dir)
    maybe_cleanup_expired_workspaces(exclude_workspace=resolved)
    return {
        "session_id": str(session_id or resolved.name).strip() or resolved.name,
        "workspace_dir": str(resolved),
    }


def _workspace_dir_from_payload(payload: Dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    return str(payload.get("workspace_dir") or "").strip() or None


def _new_log_anchor(stage: str) -> str:
    safe_stage = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(stage or "").strip() or "unknown")
    return f"actions.{safe_stage}.{time.strftime('%Y%m%d%H%M%S')}.{uuid.uuid4().hex[:8]}"


def _job_trace_meta(job: Dict[str, Any] | None) -> Dict[str, str]:
    payload = job.get("payload") if isinstance(job, dict) and isinstance(job.get("payload"), dict) else {}
    return {
        "request_id": str(payload.get("request_id") or "").strip(),
        "trace_id": str(payload.get("trace_id") or "").strip(),
    }


def _actions_error_detail(
    code: str,
    message: str,
    *,
    stage: str,
    log_anchor: str,
    job_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    next_action: str | None = None,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return error_view_core.build_actions_error_detail(
        code,
        message,
        stage=stage,
        log_anchor=log_anchor,
        job_id=job_id,
        request_id=request_id,
        trace_id=trace_id,
        next_action=next_action,
        extra=extra,
    )


def _raise_actions_http_error(
    status_code: int,
    code: str,
    message: str,
    *,
    stage: str,
    job_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    next_action: str | None = None,
    extra: Dict[str, Any] | None = None,
    exc: Exception | None = None,
) -> None:
    log_anchor = _new_log_anchor(stage)
    detail = _actions_error_detail(
        code,
        message,
        stage=stage,
        log_anchor=log_anchor,
        job_id=job_id,
        request_id=request_id,
        trace_id=trace_id,
        next_action=next_action,
        extra=extra,
    )
    if exc is None:
        logger.warning("%s code=%s status=%s detail=%s", log_anchor, code, status_code, detail)
    else:
        logger.exception("%s code=%s status=%s detail=%s", log_anchor, code, status_code, detail)
    raise HTTPException(status_code=status_code, detail=detail)


def _recent_job_automation_summary(result: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_automation_summary(result)


def _recent_job_first_variant_summary(raw: Any) -> dict[str, Any]:
    return recent_view_core.recent_job_first_variant_summary(raw)


def _recent_job_generation_mode_summary(payload: dict | None, result: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_generation_mode_summary(payload, result)


def _recent_job_quality_overview(result: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_quality_overview(result)


def _result_bundle_summary(result: dict | None) -> dict[str, Any]:
    return result_view_core.result_bundle_summary(result)


def _result_bundle_view(result: dict | None) -> dict[str, Any]:
    return result_view_core.result_bundle_view(result)


def _blocking_issue_summary_from_result(result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    return result_view_core.blocking_issue_summary_from_result(result, variant=variant)


def _blocking_issue_summary_fields(summary: dict | None) -> dict[str, Any]:
    return result_view_core.blocking_issue_summary_fields(summary)


def _download_artifact_path(result: dict | None, kind: str, *, variant: int = 1) -> str | None:
    return result_view_core.download_artifact_path(result, kind, variant=variant)


def _download_filename(job_id: str, kind: str, *, variant: int = 1) -> str:
    return result_view_core.download_filename(
        job_id,
        kind,
        download_kind_specs=_DOWNLOAD_KIND_SPECS,
        variant=variant,
    )


def _build_download_index(job_id: str, result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    return result_view_core.build_download_index(
        job_id,
        result,
        download_kind_specs=_DOWNLOAD_KIND_SPECS,
        variant=variant,
    )


def _download_ready_summary(download_index: dict | None) -> dict[str, Any]:
    return result_view_core.download_ready_summary(download_index)


def _result_contract_view(job_id: str, result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    return result_view_core.result_contract_view(
        job_id,
        result,
        download_kind_specs=_DOWNLOAD_KIND_SPECS,
        variant=variant,
    )


def _review_variant_result_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    return review_rebuild_core.build_review_variant_summary(results)


def _review_result_metadata(results: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
    return review_rebuild_core.build_review_result_metadata(results, payload)


def _write_review_result_bundle(
    job_id: str,
    *,
    payload: Dict[str, Any],
    outputs: Dict[str, Any],
    result_metadata: Dict[str, Any],
    resource_usage_summary: Dict[str, Any],
    variant_summary: Dict[str, Any],
) -> str:
    return review_rebuild_core.write_review_result_bundle(
        job_id,
        payload=payload,
        outputs=outputs,
        result_metadata=result_metadata,
        resource_usage_summary=resource_usage_summary,
        variant_summary=variant_summary,
    )


def _recent_job_agent_runtime_summary(agent_runtime: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_agent_runtime_summary(agent_runtime)


def _recent_job_sla_summary(sla: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_sla_summary(sla, now_ts=time.time())


def _parse_recent_timestamp(value: str) -> float:
    return recent_view_core.parse_recent_timestamp(value)


def _recent_signal_rank(kind: str, summary: str) -> int:
    return recent_view_core.recent_signal_rank(kind, summary)


def _recent_summary_line(
    rows: list[dict[str, Any]],
    *,
    reference_timestamp: str = "",
    healthy: bool = False,
    recent_window_seconds: int = 1800,
    idle_fallback: str = "",
) -> str:
    return recent_view_core.recent_summary_line(
        rows,
        reference_timestamp=reference_timestamp,
        healthy=healthy,
        recent_window_seconds=recent_window_seconds,
        idle_fallback=idle_fallback,
    )


def _normalize_recent_rows(items: list[Any], *, limit: int = 6) -> list[dict[str, Any]]:
    return recent_view_core.normalize_recent_rows(items, limit=limit)


def _chief_agent_status_summary(state: dict | None, *, stale_seconds: int = 120) -> dict[str, Any]:
    return recent_view_core.chief_agent_status_summary(state, stale_seconds=stale_seconds, now_ts=time.time())


def _load_watcher_state() -> dict[str, Any]:
    return recent_view_core.load_watcher_state()


def _watcher_status_summary(state: dict | None, *, stale_seconds: int = 180) -> dict[str, Any]:
    return recent_view_core.watcher_status_summary(state, stale_seconds=stale_seconds, now_ts=time.time())


def _recent_job_runtime_budget_summary(result: dict | None) -> list[dict[str, Any]]:
    return recent_view_core.recent_job_runtime_budget_summary(result)


def _recent_job_remediation_strategy_summary(result: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_remediation_strategy_summary(result)


def _recent_job_remediation_execution_summary(result: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_remediation_execution_summary(result)


def _recent_job_remediation_learning_summary(result: dict | None) -> dict[str, Any]:
    return recent_view_core.recent_job_remediation_learning_summary(result)


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
    logic_template_id: str | None = None
    logic_template: str | None = None
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
    front_matter_outline: dict | None = None
    quality_strict: bool | None = True
    auto_remediate: bool = True
    remediate_mode: str = "template"
    compare_mode: str = "summary"
    compare_max_chars: int | None = None
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
    case_library: dict | None = None
    image_library: dict | None = None
    # Per-run editable parameter overrides (do not persist). Example:
    # {"qse_defaults": {"PM10阈值": "≤120ug/m3"}, "quant_defaults": {"频次": "3次/日"}}
    params_override: dict | None = None


class ActionsPlanRequest(BaseModel):
    outline: List[str]
    style: dict = {}
    project_type: str | None = None
    generation_mode: str | None = None
    logic_template_id: str | None = None
    logic_template: str | None = None
    global_instruction: str | None = None
    variants: int = 1
    selected_templates: List[str] | None = None
    strict_tender_outline: bool | None = None
    total_pages_target: int | None = None
    chapter_requirements: dict = {}
    chapter_pages: dict = {}
    front_matter_outline: dict | None = None
    quality_strict: bool = True
    auto_remediate: bool = True
    remediate_mode: str = "template"
    compare_mode: str = "summary"
    compare_max_chars: int | None = None
    compare_titles: list[str] | None = None
    case_library: dict | None = None
    image_library: dict | None = None


class ActionsCaseLibraryOptions(BaseModel):
    enabled: bool = False
    selected_case_ids: List[str] | None = None
    top_k: int | None = None


class ActionsImageLibraryOptions(BaseModel):
    enabled: bool = False
    selected_image_ids: List[str] | None = None
    top_k: int | None = None


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
    media: List[dict] | None = None
    image_selection_pack: dict | None = None
    case_reference_pack: dict | None = None
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
async def actions_params_set(
    req: ActionsParamsSetRequest,
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    before = load_params()
    path = save_params(req.update, merge=bool(req.merge))
    after = load_params()
    diff = None
    try:
        from backend.zhifei_autoplan.param_trace import load_latest_receipt, diff_params_with_receipt

        diff = diff_params_with_receipt(
            before,
            after,
            load_latest_receipt(project_id=project_id, workspace_dir=workspace["workspace_dir"]),
        )
    except Exception:
        diff = None
    return {"ok": True, "saved_at": path, "params": after, "diff": diff}


@router.post("/params/diff")
async def actions_params_diff(
    req: ActionsParamsDiffRequest,
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
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

        diff = diff_params_with_receipt(
            before,
            after,
            load_latest_receipt(project_id=project_id, workspace_dir=workspace["workspace_dir"]),
        )
    except Exception:
        diff = None
    return {"ok": True, "before": before, "after": after, "diff": diff}


@router.get("/params/receipt/get")
async def actions_params_receipt_get(
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    try:
        from backend.zhifei_autoplan.param_trace import load_latest_receipt

        receipt = load_latest_receipt(project_id=project_id, workspace_dir=workspace["workspace_dir"]) or {}
        return {"ok": True, "receipt": receipt}
    except Exception as e:
        return {"ok": False, "error": repr(e), "receipt": {}}


async def _save_upload(uf: UploadFile, *, workspace_dir: str | None = None) -> str:
    data = await uf.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"empty file: {uf.filename}")
    workspace = _resolve_workspace_context(workspace_dir=workspace_dir)
    upload_dir = workspace_paths(workspace["workspace_dir"])["uploads"] / "_actions_tmp"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = re.sub(r"[^A-Za-z0-9_\-\.\u4e00-\u9fff]+", "_", str(uf.filename or "upload.bin")).strip("_") or "upload.bin"
    target = upload_dir / f"{uuid.uuid4().hex}_{filename}"
    target.write_bytes(data)
    return str(target)


def _safe_project_scope(raw: str | None) -> str | None:
    s = str(raw or "").strip()
    if not s:
        return None
    s = re.sub(r"[^A-Za-z0-9_\-\.\u4e00-\u9fff]+", "_", s).strip("_")
    return s[:96] or None


def _to_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v or "").strip().lower()
    if not s:
        return default
    return s in {"1", "true", "yes", "on", "y"}


def _case_library_item_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(item.get("record_id") or "").strip(),
        "title": str(item.get("title") or item.get("filename") or "").strip(),
        "name": str(item.get("title") or item.get("filename") or "").strip(),
        "project_type": item.get("project_type"),
        "tags": item.get("library_tags") if isinstance(item.get("library_tags"), list) else [],
        "chapter_scope": item.get("chapter_scope") if isinstance(item.get("chapter_scope"), list) else [],
        "source_file": item.get("source_file"),
        "storage_path": item.get("storage_path"),
        "enabled": bool(item.get("enabled", True)),
        "usable": bool(item.get("usable", True)),
        "created_at": item.get("ts"),
        "updated_at": item.get("ts"),
        "summary": item.get("library_summary") or item.get("library_note"),
        "style_profile": item.get("library_style_profile"),
        "preview_saved_as": item.get("preview_saved_as"),
        "template_page_bucket": item.get("template_page_bucket"),
        "template_scene_tags": item.get("template_scene_tags") if isinstance(item.get("template_scene_tags"), list) else [],
    }


def _case_library_saved_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": template_library_record_id(item),
        "title": str(item.get("library_title") or item.get("filename") or "").strip(),
        "name": str(item.get("library_title") or item.get("filename") or "").strip(),
        "project_type": item.get("project_type"),
        "tags": item.get("library_tags") if isinstance(item.get("library_tags"), list) else [],
        "chapter_scope": item.get("chapter_scope") if isinstance(item.get("chapter_scope"), list) else [],
        "source_file": item.get("saved_as"),
        "storage_path": item.get("saved_as"),
        "enabled": bool(item.get("enabled", True)),
        "usable": bool(item.get("usable", True)),
        "created_at": item.get("ts"),
        "updated_at": item.get("ts"),
        "summary": item.get("library_summary") or item.get("library_note"),
        "style_profile": item.get("library_style_profile"),
        "preview_saved_as": item.get("preview_saved_as"),
    }


def _image_library_item_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "image_id": str(item.get("image_id") or "").strip(),
        "title": str(item.get("title") or item.get("filename") or "").strip(),
        "name": str(item.get("title") or item.get("filename") or "").strip(),
        "project_type": item.get("project_type"),
        "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
        "chapter_scope": item.get("chapter_scope") if isinstance(item.get("chapter_scope"), list) else [],
        "process_scope": item.get("process_scope") if isinstance(item.get("process_scope"), list) else [],
        "caption": item.get("caption"),
        "description": item.get("description"),
        "source_path": item.get("source_path"),
        "storage_path": item.get("storage_path"),
        "enabled": bool(item.get("enabled", True)),
        "usable": bool(item.get("usable", True)),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "preview_saved_as": item.get("preview_saved_as"),
    }


def _image_library_saved_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "image_id": image_library_record_id(item),
        "title": str(item.get("library_title") or item.get("filename") or "").strip(),
        "name": str(item.get("library_title") or item.get("filename") or "").strip(),
        "project_type": item.get("project_type"),
        "tags": item.get("library_tags") if isinstance(item.get("library_tags"), list) else [],
        "chapter_scope": item.get("chapter_scope") if isinstance(item.get("chapter_scope"), list) else [],
        "process_scope": item.get("process_scope") if isinstance(item.get("process_scope"), list) else [],
        "caption": item.get("library_caption"),
        "description": item.get("library_description") or item.get("library_note"),
        "source_path": item.get("saved_as"),
        "storage_path": item.get("saved_as"),
        "enabled": bool(item.get("enabled", True)),
        "usable": bool(item.get("usable", True)),
        "created_at": item.get("ts"),
        "updated_at": item.get("ts"),
        "preview_saved_as": item.get("preview_saved_as"),
    }


def _run_background_housekeeping(force: bool = False, *, workspace_dir: str | None = None) -> Dict[str, Any]:
    global _HOUSEKEEP_LAST_TS, _HOUSEKEEP_LAST_REPORT
    now = time.time()
    interval = max(30, int(_to_positive_int(os.getenv("ZF_HOUSEKEEP_INTERVAL_SECONDS")) or 300))
    if (not force) and _HOUSEKEEP_LAST_TS > 0 and (now - _HOUSEKEEP_LAST_TS) < interval:
        return dict(_HOUSEKEEP_LAST_REPORT)
    lease_seconds = max(60, int(_to_positive_int(os.getenv("ZF_JOB_LEASE_SECONDS")) or 900))
    scan_limit = max(10, int(_to_positive_int(os.getenv("ZF_STALE_SCAN_LIMIT")) or 2000))
    retention = max(3600, int(_to_positive_int(os.getenv("ZF_JOB_RETENTION_SECONDS")) or (14 * 24 * 3600)))
    archive_enabled = _to_bool(os.getenv("ZF_JOB_ARCHIVE"), default=True)
    stale_fixed = 0
    removed = 0
    try:
        stale_fixed = int(
            mark_stale_running_jobs(
                lease_seconds=lease_seconds,
                limit=scan_limit,
                workspace_dir=workspace_dir,
            )
            or 0
        )
    except Exception:
        stale_fixed = 0
    try:
        removed = int(
            cleanup_jobs(
                older_than_seconds=retention,
                archive=archive_enabled,
                workspace_dir=workspace_dir,
            )
            or 0
        )
    except Exception:
        removed = 0
    report = {
        "ts": now,
        "interval_seconds": interval,
        "lease_seconds": lease_seconds,
        "retention_seconds": retention,
        "archive_enabled": archive_enabled,
        "stale_fixed": stale_fixed,
        "removed": removed,
    }
    _HOUSEKEEP_LAST_TS = now
    _HOUSEKEEP_LAST_REPORT = report
    return dict(report)


def _to_positive_int(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def _normalize_logic_template_id(raw: Any) -> str | None:
    return generation_mode_core.normalize_logic_template_id(raw)


def _normalize_selected_templates(raw: Any) -> List[str]:
    return generation_mode_core.normalize_selected_templates(raw)


def _worker_log_path(job_id: str, workspace_dir: str | None = None) -> Path:
    safe_job_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(job_id or "").strip()) or "unknown_job"
    if workspace_dir:
        return (workspace_paths(workspace_dir)["worker_logs"] / f"{safe_job_id}.log").resolve()
    return (WORKER_LOG_DIR / f"{safe_job_id}.log").resolve()


def _append_worker_log(job_id: str, message: str, *, workspace_dir: str | None = None) -> None:
    log_path = _worker_log_path(job_id, workspace_dir=workspace_dir)
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {str(message or '').strip()}\n"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def _spawn_generate_worker(job_id: str, *, workspace_dir: str | None = None) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "backend.zhifei_autoplan.job_worker", str(job_id)]
    if workspace_dir:
        cmd.append(str(workspace_dir))
    log_path = _worker_log_path(job_id, workspace_dir=workspace_dir)
    _append_worker_log(job_id, "worker_spawn_requested", workspace_dir=workspace_dir)
    with log_path.open("a", encoding="utf-8") as worker_log:
        proc = subprocess.Popen(  # noqa: S603,S607
            cmd,
            stdout=worker_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    _append_worker_log(job_id, f"worker_spawned pid={int(proc.pid)}", workspace_dir=workspace_dir)
    return int(proc.pid), str(log_path)


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
    return generation_mode_core.page_target_value(v)


def _planned_total_pages(payload: dict) -> int:
    return generation_mode_core.planned_total_pages(payload)


_GENERATION_MODE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "standard_auto",
        "profile": "standard_auto",
        "label": "Standard Auto",
        "legacy": False,
        "stable_output": False,
        "description": "Default mode that uses quality_200 or hq_speed_500 based on planned total pages.",
    },
    {
        "id": "quality_200",
        "profile": "standard_auto",
        "label": "Quality 200",
        "legacy": True,
        "stable_output": False,
        "description": "Legacy alias that prefers high quality under 200 planned pages and auto-switches above that.",
    },
    {
        "id": "hq_speed_500",
        "profile": "standard_auto",
        "label": "HQ Speed 500",
        "legacy": True,
        "stable_output": False,
        "description": "Legacy alias for the large-document speed profile with stricter template remediation defaults.",
    },
    {
        "id": "speed_fast",
        "profile": "speed_fast",
        "label": "Speed Fast",
        "legacy": False,
        "stable_output": False,
        "description": "Fastest deterministic template-first mode with lower compare budget and no image generation.",
    },
    {
        "id": "pro_polish",
        "profile": "pro_polish",
        "label": "Pro Polish",
        "legacy": False,
        "stable_output": False,
        "description": "Higher-polish mode with stricter review retries and LLM remediation enabled.",
    },
    {
        "id": "stable_delivery",
        "profile": "stable_delivery",
        "label": "Stable Delivery",
        "legacy": False,
        "stable_output": True,
        "description": "Deterministic delivery mode that fixes variant/template selection when the request leaves them unspecified.",
    },
)


def generation_mode_catalog() -> List[Dict[str, Any]]:
    return generation_mode_core.generation_mode_catalog()


def _normalize_generation_mode_profile(raw: str | None) -> tuple[str, str | None]:
    return generation_mode_core.normalize_generation_mode_profile(raw)


def _apply_generation_mode_policy(payload: dict) -> dict:
    return generation_mode_core.apply_generation_mode_policy(payload)


def _merge_plan_defaults(payload: dict) -> dict:
    return runtime_payload_core.merge_plan_defaults(
        payload,
        workspace_dir_from_payload_fn=_workspace_dir_from_payload,
        load_plan_fn=load_plan,
        load_tender_matrix_fn=load_tender_matrix,
        normalize_selected_templates_fn=_normalize_selected_templates,
        apply_generation_mode_policy_fn=_apply_generation_mode_policy,
    )


def _prepare_runtime_payload(payload: dict) -> dict:
    if payload.get("case_library") is not None:
        payload["case_library"] = normalize_case_library_options(payload.get("case_library"))
    if payload.get("image_library") is not None:
        payload["image_library"] = normalize_image_library_options(payload.get("image_library"))
    return runtime_payload_core.prepare_runtime_payload(
        payload,
        resolve_workspace_context_fn=_resolve_workspace_context,
        merge_plan_defaults_fn=_merge_plan_defaults,
        apply_server_provider_routing_fn=apply_server_provider_routing,
        uuid_hex_fn=lambda: uuid.uuid4().hex,
    )


def _save_outputs(base_name: str, results: list[dict], *, workspace_dir: str | None = None) -> dict:
    return output_artifacts_core.save_outputs(base_name, results, workspace_dir=workspace_dir)


def _rebuild_postprocessed_artifacts(
    results: list[dict],
    *,
    payload: dict,
    report: dict | None,
    params: dict | None,
) -> None:
    return postprocess_core.rebuild_postprocessed_artifacts(
        results,
        payload=payload,
        report=report,
        params=params,
    )


def _load_done_job_variants(job_id: str, *, workspace_dir: str | None = None) -> tuple[dict, dict, dict, list]:
    try:
        loaded = load_done_job_core.load_done_job_variants(
            job_id=job_id,
            workspace_dir=workspace_dir,
            get_job_fn=get_job,
            result_loader_fn=lambda result: result_read_core.load_result_bundle_with_contract(
                result,
                empty_code="empty_result_variants",
                empty_message="empty result variants",
                read_text_errors="ignore",
            ),
        )
    except load_done_job_core.LoadDoneJobFailure as exc:
        job = get_job(job_id, workspace_dir=workspace_dir)
        trace_meta = _job_trace_meta(job)
        status_code = 404 if exc.code == "job_not_found" else 409
        _raise_actions_http_error(
            status_code,
            exc.code,
            exc.message,
            stage="load_done_job",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action=exc.next_action,
            extra=exc.extra,
        )
    except result_read_core.ResultReadFailure as exc:
        trace_meta = _job_trace_meta(loaded.job if "loaded" in locals() else get_job(job_id, workspace_dir=workspace_dir))
        _raise_actions_http_error(
            404,
            exc.code,
            exc.message,
            stage="load_done_job",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action=exc.next_action,
            extra=exc.extra,
        )
    return loaded.job, loaded.result, loaded.data, loaded.variants


def _review_items_for_variant(variant_rec: dict, *, max_excerpt: int = 320) -> list[dict]:
    return review_view_core.review_items_for_variant(variant_rec, max_excerpt=max_excerpt)


@router.post("/plan/save")
async def actions_plan_save(
    req: ActionsPlanRequest,
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    path = save_plan(req.model_dump(), project_id=project_id, workspace_dir=workspace["workspace_dir"])
    return {"ok": True, "saved_at": path}


@router.get("/plan/get")
async def actions_plan_get(
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    return {"ok": True, "plan": load_plan(project_id=project_id, workspace_dir=workspace["workspace_dir"]) or {}}


@router.post("/tender/parse")
async def actions_tender_parse(
    files: List[UploadFile] = File(...),
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    if not files:
        raise HTTPException(status_code=400, detail="no files")
    paths = await asyncio.gather(*[_save_upload(f, workspace_dir=workspace["workspace_dir"]) for f in files])
    parser = TenderParser()
    matrix = await parser.parse(paths)
    matrix_dict = matrix.model_dump()
    bidding_format_config = build_bidding_format_config_from_style(matrix_dict.get("style"))
    matrix_dict["bidding_format_config"] = bidding_format_config
    extraction_meta = matrix_dict.get("extraction_meta") if isinstance(matrix_dict.get("extraction_meta"), dict) else {}
    extraction_meta["format_extraction_rule"] = "优先提取招标排版要求；未提及字段在 bidding_format_config.json 显式置 null。"
    matrix_dict["extraction_meta"] = extraction_meta
    parsed_code = _safe_project_scope(matrix_dict.get("project_code"))
    parsed_name = str(matrix_dict.get("project_name") or "").strip() or None
    requested_pid = _safe_project_scope(project_id)
    resolved_project_id = requested_pid or parsed_code
    if not resolved_project_id and parsed_name:
        resolved_project_id = _safe_project_scope(parsed_name)
    saved_at = save_tender_matrix(
        matrix_dict,
        project_id=resolved_project_id,
        workspace_dir=workspace["workspace_dir"],
    )
    format_saved_at = save_bidding_format_config(
        bidding_format_config,
        project_id=resolved_project_id,
        workspace_dir=workspace["workspace_dir"],
    )
    return {
        "ok": True,
        "matrix": matrix_dict,
        "project_id": resolved_project_id,
        "project_name": parsed_name,
        "project_code": parsed_code,
        "saved_at": saved_at,
        "bidding_format_config_saved_at": format_saved_at,
    }


@router.post("/boq/parse")
async def actions_boq_parse(
    file: List[UploadFile] = File(...),
    project_id: str | None = None,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    if not file:
        raise HTTPException(status_code=400, detail="no file")
    paths = await asyncio.gather(*[_save_upload(f, workspace_dir=workspace["workspace_dir"]) for f in file])
    parser = BoQParser()
    merged_items = []
    for p in paths:
        items, _ = await parser.parse(p)
        merged_items.extend(items)
    stats = parser._calc_stats(merged_items)
    payload = {"items": [it.model_dump() for it in merged_items], "stats": stats, "source_file_count": len(paths)}
    saved_at = save_boq_data(payload, project_id=project_id, workspace_dir=workspace["workspace_dir"])
    return {**payload, "ok": True, "saved_at": saved_at}


@router.post("/quality_check")
async def actions_quality_check(
    req: ActionsQualityCheckRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    pid = str(req.project_id or "").strip() or None
    tender = load_tender_matrix(project_id=pid, workspace_dir=workspace["workspace_dir"]) or {}
    boq = load_boq_data(project_id=pid, workspace_dir=workspace["workspace_dir"]) or {}
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
        workspace_dir=workspace["workspace_dir"],
    )
    return {"ok": True, "boq_focus": boq_focus, "quality_checks": qc}


@router.post("/export_docx")
async def actions_export_docx(
    req: ActionsExportRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    return export_docx_core.execute_export_docx_request(
        raw_request=req.model_dump(),
        workspace_dir=workspace["workspace_dir"],
        save_outputs_fn=_save_outputs,
    )


@router.post("/generate")
async def actions_generate(
    req: ActionsGenerateRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    from backend.zhifei_autoplan.diversity_autofix import apply_diversity_autofix
    from backend.zhifei_autoplan.variant_similarity import compute_variant_similarity

    return await generate_sync_core.execute_generate_sync_request(
        raw_payload={**req.model_dump(), "session_id": session_id, "workspace_dir": workspace_dir},
        prepare_runtime_payload_fn=_prepare_runtime_payload,
        build_variant_plan_fn=_build_variant_plan,
        normalize_logic_template_id_fn=_normalize_logic_template_id,
        run_autoplan_fn=run_autoplan,
        load_params_fn=load_params,
        rebuild_postprocessed_fn=_rebuild_postprocessed_artifacts,
        workspace_dir_from_payload_fn=_workspace_dir_from_payload,
        save_outputs_fn=_save_outputs,
        compute_variant_similarity_fn=compute_variant_similarity,
        apply_diversity_autofix_fn=apply_diversity_autofix,
    )


@router.post("/generate_async")
async def actions_generate_async(
    req: ActionsGenerateRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    _run_background_housekeeping(force=False, workspace_dir=workspace["workspace_dir"])
    try:
        return generate_request_core.execute_generate_request_from_runtime(
            raw_payload={**req.model_dump(), "session_id": workspace["session_id"], "workspace_dir": workspace["workspace_dir"]},
            session_id=workspace["session_id"],
            workspace_dir=workspace["workspace_dir"],
            prepare_runtime_payload_fn=_prepare_runtime_payload,
            attach_contract_stamp_fn=attach_contract_stamp,
            compute_job_signature_fn=compute_job_signature,
            find_reusable_job_fn=find_reusable_job,
            evaluate_job_admission_fn=evaluate_job_admission,
            admission_http_detail_fn=admission_http_detail,
            append_resource_event_fn=append_resource_event,
            build_reused_response_fn=generate_view_core.build_generate_async_reused_response,
            build_rejection_event_fn=generate_view_core.build_generate_async_rejection_event,
            build_rejected_detail_fn=generate_view_core.build_generate_async_rejected_detail,
            apply_admission_degrade_fn=apply_admission_degrade,
            new_log_anchor_fn=_new_log_anchor,
            create_job_fn=create_job,
            spawn_generate_worker_fn=_spawn_generate_worker,
            update_job_fn=update_job,
            append_worker_log_fn=_append_worker_log,
            build_variant_plan_fn=_build_variant_plan,
            build_queued_response_fn=generate_view_core.build_generate_async_queued_response,
            build_payload_prepare_error_fn=generate_view_core.build_generate_payload_prepare_error,
            build_worker_spawn_error_fn=generate_view_core.build_generate_worker_spawn_error,
        )
    except Exception as exc:
        failure = generate_request_core.translate_generate_request_failure(exc)
        if failure is None:
            raise
        if failure.detail is not None:
            warning = failure.warning_log or {}
            logger.warning(
                "%s code=%s status=%s detail=%s",
                warning.get("log_anchor"),
                warning.get("code"),
                failure.status_code,
                warning.get("detail"),
            )
            raise HTTPException(status_code=failure.status_code, detail=failure.detail)
        error_spec = failure.error_spec or {}
        _raise_actions_http_error(
            int(failure.status_code),
            str(error_spec["code"]),
            str(error_spec["message"]),
            stage=str(error_spec["stage"]),
            job_id=error_spec.get("job_id"),
            request_id=error_spec.get("request_id"),
            trace_id=error_spec.get("trace_id"),
            next_action=error_spec.get("next_action"),
            extra=error_spec.get("extra"),
            exc=failure.cause,
        )


@router.get("/usage_status")
async def actions_usage_status(
    requested_jobs: int = 1,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    decision = evaluate_job_admission(
        scope="session",
        tenant_id=workspace["session_id"],
        workspace_dir=workspace["workspace_dir"],
        requested_jobs=max(0, int(requested_jobs or 0)),
    )
    return usage_view_core.build_actions_usage_status_response(admission_http_detail(decision))


@router.get("/usage_report")
async def actions_usage_report(
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    decision = evaluate_job_admission(
        scope="session",
        tenant_id=workspace["session_id"],
        workspace_dir=workspace["workspace_dir"],
        requested_jobs=0,
    )
    return usage_view_core.build_actions_usage_report_response(
        session_id=workspace["session_id"],
        workspace_dir=workspace["workspace_dir"],
        decision=decision,
    )


@router.get("/case_library/project_types")
async def actions_case_library_project_types(
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    return {"ok": True, "project_types": ordered_project_types()}


@router.get("/case_library/summary")
async def actions_case_library_summary(
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    summary = summarize_template_library(
        project_types=ordered_project_types(),
        audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
    )
    return {"ok": True, "summary": summary}


@router.get("/case_library/items")
async def actions_case_library_items(
    project_type: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    sort_by: str | None = None,
    limit: int = 20,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    items = list_template_library_items(
        project_type=project_type,
        template_page_bucket=template_page_bucket,
        scene_tags=normalize_text_list(template_scene_tags),
        sort_by=sort_by,
        limit=max(1, min(int(limit or 20), 60)),
        audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
    )
    return {"ok": True, "items": [_case_library_item_view(item) for item in items]}


@router.post("/case_library/upload")
async def actions_case_library_upload(
    files: List[UploadFile] = File(...),
    project_type: str | None = None,
    title: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    summary: str | None = None,
    style_profile: str | None = None,
    library_note: str | None = None,
    template_page_bucket: str | None = None,
    template_scene_tags: str | None = None,
    enabled: bool = True,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    from backend.app.routers.ingest import _handle_upload, TEMPLATE_LIBRARY_SCOPE

    saved = await _handle_upload(
        files,
        session_id=workspace["session_id"],
        workspace_dir=workspace["workspace_dir"],
        project_type=project_type,
        library_scope=TEMPLATE_LIBRARY_SCOPE,
        library_note=library_note,
        template_page_bucket=template_page_bucket,
        template_scene_tags=template_scene_tags,
        library_tags=tags,
        chapter_scope=chapter_scope,
        library_title=title,
        library_summary=summary,
        library_style_profile=style_profile,
        library_enabled=enabled,
    )
    rows = saved.get("saved") if isinstance(saved.get("saved"), list) else []
    return {"ok": True, "items": [_case_library_saved_view(item) for item in rows]}


@router.get("/image_library/summary")
async def actions_image_library_summary(
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    summary = summarize_image_library(
        project_types=ordered_project_types(),
        audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
    )
    return {"ok": True, "summary": summary}


@router.get("/image_library/items")
async def actions_image_library_items(
    project_type: str | None = None,
    tags: str | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    limit: int = 20,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    items = list_image_library_items(
        project_type=project_type,
        tags=normalize_text_list(tags),
        chapter_scope=chapter_scope,
        process_scope=process_scope,
        limit=max(1, min(int(limit or 20), 60)),
        audit_path=workspace_paths(workspace["workspace_dir"])["ingest_audit"],
    )
    return {"ok": True, "items": [_image_library_item_view(item) for item in items]}


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
    library_note: str | None = None,
    enabled: bool = True,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    from backend.app.routers.ingest import _handle_upload

    saved = await _handle_upload(
        files,
        session_id=workspace["session_id"],
        workspace_dir=workspace["workspace_dir"],
        project_type=project_type,
        library_scope="image_library",
        library_note=library_note,
        library_tags=tags,
        chapter_scope=chapter_scope,
        process_scope=process_scope,
        library_title=title,
        library_caption=caption,
        library_description=description,
        library_enabled=enabled,
    )
    rows = saved.get("saved") if isinstance(saved.get("saved"), list) else []
    return {"ok": True, "items": [_image_library_saved_view(item) for item in rows]}


@router.post("/job_cancel")
async def actions_job_cancel(
    req: ActionsJobCancelRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    job_id = str(req.job_id or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    job = get_job(job_id, workspace_dir=workspace["workspace_dir"])
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job_cancel_core.cancel_job(
        job_id=job_id,
        workspace_dir=workspace["workspace_dir"],
        job=job,
        kill_fn=os.kill,
        update_job_fn=update_job,
        build_response_fn=job_cancel_view_core.build_actions_job_cancel_response,
    )


@router.get("/job_status")
async def actions_job_status(
    job_id: str,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    _run_background_housekeeping(force=False, workspace_dir=workspace["workspace_dir"])
    lease_seconds = max(60, int(_to_positive_int(os.getenv("ZF_JOB_LEASE_SECONDS")) or 900))
    job = reconcile_job_runtime(job_id, lease_seconds=lease_seconds, workspace_dir=workspace["workspace_dir"]) or get_job(job_id, workspace_dir=workspace["workspace_dir"])
    if not job:
        _raise_actions_http_error(
            404,
            "job_not_found",
            "job not found",
            stage="job_status",
            job_id=job_id,
            next_action="check job_id or workspace scope",
        )
    trace_meta = _job_trace_meta(job)
    response = job_status_response_core.build_actions_job_status_response(
        job_id=job_id,
        job=job,
        trace_meta=trace_meta,
        result_contract_view_fn=lambda x_job_id, x_result, x_variant: _result_contract_view(x_job_id, x_result, variant=x_variant),
    )
    response["housekeep"] = dict(_HOUSEKEEP_LAST_REPORT)
    return response


@router.get("/self_evolution/status")
async def actions_self_evolution_status(
    limit: int = 6,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    params = load_params()
    return {
        "ok": True,
        "self_evolution": summarize_runtime_budget_profile(params=params, limit=limit),
    }


@router.get("/chief_agent/status")
async def actions_chief_agent_status(
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    state = load_chief_engineer_state()
    return {
        "ok": True,
        "chief_agent": _chief_agent_status_summary(state),
    }


@router.get("/watcher/status")
async def actions_watcher_status(
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    state = _load_watcher_state()
    return {
        "ok": True,
        "watcher": _watcher_status_summary(state),
    }


@router.get("/jobs/recent")
async def actions_jobs_recent(
    limit: int = 8,
    statuses: str = "queued,running,done",
    max_age_hours: int = 24,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    _run_background_housekeeping(force=False, workspace_dir=workspace["workspace_dir"])
    wanted_statuses = tuple(
        str(x or "").strip().lower()
        for x in str(statuses or "").split(",")
        if str(x or "").strip()
    ) or ("queued", "running", "done")
    lease_seconds = max(60, int(_to_positive_int(os.getenv("ZF_JOB_LEASE_SECONDS")) or 900))
    rows = discover_recent_jobs(
        limit=max(1, min(20, int(limit or 8))),
        statuses=wanted_statuses,
        max_age_seconds=max(1, int(max_age_hours or 24)) * 3600,
        lease_seconds=lease_seconds,
        workspace_dir=workspace["workspace_dir"],
    )
    items: List[Dict[str, Any]] = []
    for rec in rows:
        result = rec.get("result") if isinstance(rec.get("result"), dict) else {}
        result_available = has_result_artifacts(result)
        items.append(
            recent_view_core.build_recent_job_item(
                rec,
                result_available=result_available,
                download_kind_specs=_DOWNLOAD_KIND_SPECS,
            )
        )
    return {"ok": True, "items": items, "housekeep": dict(_HOUSEKEEP_LAST_REPORT)}


@router.get("/jobs/sla_summary")
async def actions_jobs_sla_summary(
    limit: int = 200,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    _run_background_housekeeping(force=False, workspace_dir=workspace["workspace_dir"])
    n = max(10, min(1000, int(limit or 200)))
    rows = list_jobs(limit=n, workspace_dir=workspace["workspace_dir"])
    summary = recent_view_core.jobs_sla_summary(rows, limit=n)
    return {
        "ok": True,
        "window": summary["window"],
        "total_latency": summary["total_latency"],
        "stage_latency": summary["stage_latency"],
        "housekeep": dict(_HOUSEKEEP_LAST_REPORT),
    }


@router.get("/review/issues")
async def actions_review_issues(
    job_id: str,
    variant: int = 1,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    _, _, _, variants = _load_done_job_variants(job_id, workspace_dir=workspace["workspace_dir"])
    return review_view_core.build_review_issues_response(
        job_id=job_id,
        requested_variant=variant,
        variants=variants,
        review_items_fn=_review_items_for_variant,
    )


@router.post("/review/apply")
async def actions_review_apply(
    req: ActionsReviewApplyRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    job_id = str(req.job_id or "").strip()
    if not job_id:
        raise HTTPException(status_code=400, detail="job_id required")
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    job, _, data, variants = _load_done_job_variants(job_id, workspace_dir=workspace["workspace_dir"])
    try:
        return review_apply_core.apply_review_decisions(
            job_id=job_id,
            requested_variant=int(req.variant or 1),
            workspace_dir=workspace["workspace_dir"],
            job=job,
            data=data,
            variants=variants,
            apply_all=bool(req.apply_all),
            decisions=list(req.decisions or []),
            review_items_for_variant_fn=_review_items_for_variant,
            save_outputs_fn=_save_outputs,
            rebuild_postprocessed_fn=_rebuild_postprocessed_artifacts,
            review_result_metadata_fn=_review_result_metadata,
            review_variant_result_summary_fn=_review_variant_result_summary,
            write_review_result_bundle_fn=_write_review_result_bundle,
            result_contract_view_fn=lambda x_job_id, x_result, x_variant: _result_contract_view(x_job_id, x_result, variant=x_variant),
            append_resource_event_fn=append_resource_event,
        )
    except ValueError as exc:
        message = str(exc or "").strip()
        if message in {"invalid variant record", "variant sections missing"}:
            raise HTTPException(status_code=400, detail=message)
        raise


@router.get("/result")
async def actions_result(
    job_id: str,
    variant: int = 1,
    include_sections: bool = False,
    max_chars: int = 4000,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    job = get_job(job_id, workspace_dir=workspace["workspace_dir"])
    if not job:
        _raise_actions_http_error(
            404,
            "job_not_found",
            "job not found",
            stage="result",
            job_id=job_id,
            next_action="check job_id or workspace scope",
        )
    trace_meta = _job_trace_meta(job)
    if job.get("status") != "done":
        return result_response_core.build_actions_result_not_done_response(
            job_id=job_id,
            status=job.get("status"),
            error=job.get("error"),
            trace_meta=trace_meta,
        )
    result = job.get("result") or {}
    try:
        result_bundle = result_read_core.load_result_bundle(result)
    except result_read_core.ResultReadFailure as exc:
        _raise_actions_http_error(
            404,
            exc.code,
            exc.message,
            stage="result",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action=exc.next_action,
            extra=exc.extra,
        )
    return result_response_core.build_actions_result_response(
        job_id=job_id,
        trace_meta=trace_meta,
        result=result,
        variants=result_bundle.variants,
        variant=variant,
        include_sections=include_sections,
        max_chars=max_chars,
        result_contract_view_fn=lambda x_job_id, x_result, x_variant: _result_contract_view(x_job_id, x_result, variant=x_variant),
        download_artifact_path_fn=lambda x_result, kind, x_variant: _download_artifact_path(x_result, kind, variant=x_variant),
    )


@router.get("/download")
async def actions_download(
    job_id: str,
    kind: str = "docx",  # docx|compare_docx|json|focus_xlsx|score_overview_xlsx|expert_review_docx|result_bundle_json
    variant: int = 1,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    workspace = _resolve_workspace_context(session_id=session_id, workspace_dir=workspace_dir)
    job = get_job(job_id, workspace_dir=workspace["workspace_dir"])
    if not job:
        _raise_actions_http_error(
            404,
            "job_not_found",
            "job not found",
            stage="download",
            job_id=job_id,
            next_action="check job_id or workspace scope",
            extra={"kind": kind, "variant": max(1, int(variant or 1))},
        )
    trace_meta = _job_trace_meta(job)
    result = job.get("result") or {}
    try:
        download_resolution = download_request_core.resolve_download_request(
            job_id=job_id,
            job=job,
            result=result,
            kind=kind,
            variant=variant,
            build_download_resolution_fn=lambda job_id, result, kind, variant: download_response_core.build_actions_download_resolution(
                job_id=job_id,
                result=result,
                kind=kind,
                variant=variant,
                download_kind_specs=_DOWNLOAD_KIND_SPECS,
                download_artifact_path_fn=lambda xx_result, xx_kind, xx_variant: _download_artifact_path(xx_result, xx_kind, variant=xx_variant),
                download_filename_fn=lambda xx_job_id, xx_kind, xx_variant: _download_filename(xx_job_id, xx_kind, variant=xx_variant),
                build_download_index_fn=lambda xx_job_id, xx_result, xx_variant: _build_download_index(xx_job_id, xx_result, variant=xx_variant),
            ),
        )
    except download_request_core.DownloadRequestFailure as exc:
        status_code = 409 if exc.code == "job_not_done" else 400 if exc.code == "invalid_artifact_kind" else 404
        _raise_actions_http_error(
            status_code,
            exc.code,
            exc.message,
            stage="download",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action=exc.next_action,
            extra=exc.extra,
        )
    requested_variant = download_resolution["requested_variant"]
    path = download_resolution["path"]
    media_type = download_resolution["media_type"]
    filename = download_resolution["filename"]
    file_size_bytes = Path(path).stat().st_size
    append_resource_event(
        "artifact_download",
        workspace_dir=workspace["workspace_dir"],
        session_id=workspace["session_id"],
        user_id=None,
        **download_response_core.build_actions_download_event_fields(
            job=job,
            job_id=job_id,
            kind=kind,
            variant=requested_variant,
            file_path=str(path),
            file_size_bytes=file_size_bytes,
        ),
    )
    return FileResponse(str(path), media_type=media_type, filename=filename)
