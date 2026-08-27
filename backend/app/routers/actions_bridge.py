from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import FileResponse

from backend.zhifei_autoplan.job_store import (
    JobLeaseLostError,
    acquire_job_lease,
    create_job,
    get_job,
    heartbeat_job,
    job_lease_active,
    merge_job,
    run_with_job_lease,
    transition_job,
    update_job,
)
from backend.zhifei_autoplan.local_job_queue import submit_isolated_job
from backend.zhifei_autoplan.runtime_events import append_runtime_event, event_journal_path
from backend.zhifei_autoplan.generation_checkpoint import (
    mark_failed_checkpoint_namespace,
)
from backend.zhifei_autoplan import export_docx_service as export_docx_core
from backend.zhifei_autoplan.orchestrator import (
    _build_boq_focus,
    _normalize_provider_chain,
    _provider_chain_for_role,
    _resolve_provider_api_key,
    new_provider_admission_run_coordinator,
    probe_provider_candidate,
    run_autoplan,
)
from backend.zhifei_autoplan.provider_runtime import (
    ProviderSlot,
    ProviderRoutingConfigurationError,
    apply_server_provider_routing,
    build_server_provider_admission_candidates,
    server_provider_admission_required_roles,
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
from backend.zhifei_autoplan.model_reliability import classify_provider_error
from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.delivery_receipt import (
    build_delivery_receipt,
    canonical_delivery_receipt_digest,
)
from backend.zhifei_autoplan.requirement_evidence_matrix import (
    finalize_requirement_evidence_matrix,
    validate_chapter_requirement_evidence,
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
    commit_revision_promotion,
    create_revision_snapshot,
    issue_set_digest,
    list_revision_snapshots,
    load_revision_snapshot,
    prepare_revision_promotion,
    result_version,
    stable_issue_id,
    variant_version,
)
from backend.zhifei_autoplan.zbid_snapshot_mapper import map_zbid_snapshot_to_zdoc_draft_input
from backend.app.routers.ingest import (
    _handle_upload as _handle_ingest_upload,
    resolve_ingested_file_ids,
    resolve_ingested_tender_sources,
)
from backend.app.routers.ingest import _resolve_workspace_context as _resolve_ingest_workspace_context
from backend.app.routers.ingest import workspace_paths as ingest_workspace_paths


router = APIRouter(prefix="/actions", tags=["Actions Bridge"])


def _provider_admission_api_projection(value: Any) -> Dict[str, Any]:
    raw = value if isinstance(value, dict) else {}

    def _chain_entry(item: Any) -> Dict[str, Any]:
        row = item if isinstance(item, dict) else {}
        return {
            "slot": str(row.get("slot") or "")[:80],
            "role": str(row.get("role") or "")[:80],
            "provider": str(row.get("provider") or "")[:80],
            "model": str(row.get("model") or "")[:160],
        }

    slots: list[dict[str, Any]] = []
    for item in raw.get("slots") if isinstance(raw.get("slots"), list) else []:
        row = _chain_entry(item)
        source = item if isinstance(item, dict) else {}
        safe_layers: Dict[str, Any] = {}
        layers = source.get("layers") if isinstance(source.get("layers"), dict) else {}
        for name in ("configuration", "credentials", "model", "quota", "stream", "circuit"):
            layer = layers.get(name) if isinstance(layers.get(name), dict) else {}
            safe_layers[name] = {
                "status": str(layer.get("status") or "unknown")[:24],
                "code": str(layer.get("code") or "status_unknown")[:80],
            }
        row.update(
            {
                "admitted": bool(source.get("admitted")),
                "layers": safe_layers,
                "reason_codes": [
                    str(code)[:80]
                    for code in (source.get("reason_codes") or [])[:20]
                    if isinstance(code, str)
                ],
                "probe_duration_ms": max(
                    0, int(source.get("probe_duration_ms") or 0)
                ),
            }
        )
        slots.append(row)
    return {
        "schema_version": str(raw.get("schema_version") or "provider-admission-v1")[:80],
        "status": str(raw.get("status") or "missing")[:80],
        "configured_slots": max(0, int(raw.get("configured_slots") or 0)),
        "receipt_slots": max(0, int(raw.get("receipt_slots") or 0)),
        "required_roles": [
            str(role)[:80]
            for role in (raw.get("required_roles") or [])[:20]
            if isinstance(role, str)
        ],
        "slots": slots,
        "admitted_chain": [
            _chain_entry(item)
            for item in (raw.get("admitted_chain") or [])[:20]
            if isinstance(item, dict)
        ],
        "missing_roles": [
            str(role)[:80]
            for role in (raw.get("missing_roles") or [])[:20]
            if isinstance(role, str)
        ],
        "generation_allowed": bool(raw.get("generation_allowed")),
        "fallback_configured": bool(raw.get("fallback_configured")),
        "fallback_ready": bool(raw.get("fallback_ready")),
        "resilience_degraded": bool(raw.get("resilience_degraded")),
        "degraded": bool(raw.get("degraded")),
        "public_digest": str(raw.get("public_digest") or "")[:64],
    }


@router.get("/provider_admission")
def actions_provider_admission(
    x_actions_key: str | None = Header(default=None),
):
    """Return a credential-free, offline re-evaluation of the latest receipt."""

    _auth_actions_key(x_actions_key)
    from backend.zhifei_autoplan.provider_admission import evaluate_latest_snapshot
    from backend.zhifei_autoplan.provider_runtime import (
        build_server_provider_admission_candidates,
        server_provider_admission_required_roles,
    )

    candidates = build_server_provider_admission_candidates()
    required_roles = server_provider_admission_required_roles(candidates)
    admission = evaluate_latest_snapshot(
        candidates,
        required_roles,
        root=os.environ.get("ZF_PROVIDER_ADMISSION_STATE_DIR") or None,
    )
    return {"ok": True, "admission": _provider_admission_api_projection(admission)}


@router.get("/claude_usage_stats")
def actions_claude_usage_stats(
    project_id: str | None = Query(default=None, max_length=160),
    task_type: str | None = Query(default=None, max_length=120),
    x_actions_key: str | None = Header(default=None),
):
    """Return prompt-cache/token aggregates without prompts or credentials."""

    _auth_actions_key(x_actions_key)
    from backend.zhifei_autoplan.claude_usage import claude_usage_stats

    return {
        "ok": True,
        "stats": claude_usage_stats(project_id=project_id, task_type=task_type),
    }


def _public_provider_error(value: Any) -> Dict[str, Any]:
    """Reduce a provider diagnostic to stable, user-safe fields."""

    raw = dict(value) if isinstance(value, dict) else {"message": str(value or "provider_error")}
    classification_input: Any = raw
    if not str(raw.get("code") or "").strip():
        classification_input = str(raw.get("message") or "provider_error")
    info = classify_provider_error(
        classification_input,
        provider=str(raw.get("provider") or ""),
        model=str(raw.get("model") or ""),
    )
    return {
        "code": str(info.get("code") or "provider_error")[:80],
        "message": str(info.get("user_message") or "模型调用失败。")[:300],
        "action": str(info.get("action") or "请确认模型、网络和供应商状态后重试。")[:300],
        "retryable": bool(info.get("retryable")),
        "severity": str(info.get("severity") or "error")[:20],
    }


def _public_provider_state(value: Any) -> Dict[str, Any]:
    """Return provider runtime state without raw SDK/billing/network messages."""

    if not isinstance(value, dict):
        return {}

    def _scrub(node: Any, *, key: str = "") -> Any:
        if key in {"last_error", "error"} and node:
            return _public_provider_error(node)
        if isinstance(node, dict):
            result: Dict[str, Any] = {}
            for child_key, child_value in node.items():
                normalized = str(child_key).strip().lower().replace("-", "_")
                if (
                    normalized
                    in {
                        "api_key",
                        "api_keys",
                        "authorization",
                        "credential",
                        "credentials",
                        "headers",
                        "key_alias",
                        "prompt",
                        "raw",
                        "raw_error",
                        "raw_response",
                        "request_body",
                        "response_body",
                        "secret",
                        "secret_key",
                        "token",
                        "token_url",
                        "url",
                    }
                    or normalized.endswith("_api_key")
                    or normalized.endswith("_secret")
                    or normalized.endswith("_token")
                ):
                    continue
                if normalized == "message":
                    result[str(child_key)] = "模型供应商诊断已脱敏。"
                else:
                    result[str(child_key)] = _scrub(child_value, key=normalized)
            return result
        if isinstance(node, list):
            return [_scrub(item) for item in node]
        return node

    scrubbed = _scrub(value)
    return scrubbed if isinstance(scrubbed, dict) else {}


_DELIVERY_BLOCKER_GUIDANCE: Dict[str, tuple[str, str]] = {
    "DELIVERY_CONTENT_QUALITY_BLOCKED": (
        "独立内容质量审核未通过。",
        "请按内容审核阻断项修订章节后从检查点恢复。",
    ),
    "DELIVERY_PLAN_CONSISTENCY_BLOCKED": (
        "工期、资源峰值或关键线路的一致性校验未通过。",
        "请统一计划参数与关键线路口径后从检查点恢复。",
    ),
    "DELIVERY_STANDARD_EVIDENCE_BLOCKED": (
        "存在未核验、过期或冲突的规范引用。",
        "请修正规范引用与核验依据后从检查点恢复。",
    ),
    "DELIVERY_REQUIREMENT_EVIDENCE_BLOCKED": (
        "招标要求尚未全部形成可反查证据闭环。",
        "请补齐要求标记和来源定位后从检查点恢复。",
    ),
    "DELIVERY_CROSS_INDEX_BLOCKED": (
        "重点清单项未全部形成章节与依据闭环。",
        "请补齐重点清单项的章节、图纸或规范定位后从检查点恢复。",
    ),
    "DELIVERY_CROSS_INDEX_UNAVAILABLE": (
        "重点清单项交叉索引构建失败，系统已按失败关闭。",
        "请修复交叉索引构建错误后从检查点恢复。",
    ),
    "DELIVERY_MODEL_REVIEW_BLOCKED": (
        "关键章节精修或全文一致性终审未给出明确无冲突结论。",
        "请完成模型复核或修订冲突章节后从检查点恢复。",
    ),
}

_CHAPTER_VALIDATION_BLOCKER_GUIDANCE: Dict[str, tuple[str, str]] = {
    "CHAPTER_CHECK_STRUCTURE_BLOCKED": (
        "所选章节结构不完整。",
        "请补齐所选章节及其正文后从检查点恢复。",
    ),
    "CHAPTER_CHECK_OFFICIALESE_BLOCKED": (
        "所选章节存在空泛或公文化表达。",
        "请改为可执行动作、参数、频次和验收标准后从检查点恢复。",
    ),
    "CHAPTER_CHECK_RISK_TRIPLET_BLOCKED": (
        "所选章节的风险、控制和验证闭环未被完整识别。",
        "请补齐风险、控制、验证和记录后从检查点恢复。",
    ),
    "CHAPTER_CHECK_LOGIC_TEMPLATE_ADHERENCE_BLOCKED": (
        "所选章节未遵循选定的章节逻辑模板。",
        "请按模板锚点重组章节后从检查点恢复。",
    ),
    "CHAPTER_CHECK_QUANTITATIVE_BLOCKED": (
        "所选章节缺少必要的量化工程参数。",
        "请补齐数值、单位、频次或阈值后从检查点恢复。",
    ),
    "CHAPTER_CHECK_REQUIRED_TOPICS_DETAIL_BLOCKED": (
        "专项主题细则不完整。",
        "请在正式全文的责任章节补齐专项主题；单章验证不会据此阻断。",
    ),
    "CHAPTER_CHECK_EVIDENCE_TRACEABILITY_BLOCKED": (
        "所选章节的关键结论缺少可反查证据。",
        "请补齐来源定位后从检查点恢复。",
    ),
    "CHAPTER_CHECK_STANDARD_EVIDENCE_BLOCKED": (
        "所选章节的规范依据未通过核验。",
        "请修正规范名称、编号、版本或来源后从检查点恢复。",
    ),
    "CHAPTER_SECTION_QUALITY_BLOCKED": (
        "所选章节的独立内容评分低于章节阈值。",
        "请按独立内容审核意见修订后从检查点恢复。",
    ),
    "CHAPTER_AGENT_CONTRACT_BLOCKED": (
        "所选章节未满足责任 Agent 的输出合同。",
        "请补齐责任字段和验收闭环后从检查点恢复。",
    ),
    "CHAPTER_MODEL_REVIEW_BLOCKED": (
        "独立模型复核未给出通过结论。",
        "请完成模型复核或修订冲突内容后从检查点恢复。",
    ),
}


def _public_runtime_error(error: Any) -> Dict[str, Any]:
    """Return a stable, bounded error object without repr/prompt leakage."""

    raw = str(error or "").strip()
    candidates = [raw]
    if raw.startswith("RuntimeError(") and raw.endswith(")"):
        inner = raw[len("RuntimeError(") : -1].strip()
        if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in {"'", '"'}:
            try:
                import ast

                candidates.insert(0, str(ast.literal_eval(inner)))
            except Exception:
                pass
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except Exception:
            continue
        if isinstance(parsed, dict):
            code = str(parsed.get("code") or "RUNTIME_FAILED")[:80]
            failures = parsed.get("failures") if isinstance(parsed.get("failures"), list) else []
            safe_failures = []
            for item in failures[:20]:
                if not isinstance(item, dict):
                    continue
                raw_failure = str(
                    item.get("error") or item.get("message") or "provider_error"
                )
                structured_gate_failure = (
                    str(item.get("failure_kind") or "") == "quality_gate"
                    or str(item.get("code") or "")
                    == "requirement_evidence_failed"
                    or raw_failure.startswith(
                        "requirement_evidence_precheckpoint_blocked"
                    )
                )
                if (
                    code == "REQUIREMENT_EVIDENCE_CHAPTER_BLOCKED"
                    and structured_gate_failure
                ):
                    blocking_candidates = list(
                        item.get("blocking_requirement_ids") or []
                    )
                    if not blocking_candidates and ":" in raw_failure:
                        blocking_candidates = raw_failure.split(":", 1)[1].split(",")
                    blocking_ids = [
                        str(value).strip()[:160]
                        for value in blocking_candidates
                        if str(value).strip()
                        and re.fullmatch(
                            r"[A-Za-z0-9_.-]{1,160}", str(value).strip()
                        )
                    ][:20]
                    provider_error = {
                        "code": "requirement_evidence_failed",
                        "message": "章节正文未满足全部招标要求证据绑定。",
                        "action": "请按阻断要求补充同段要求与证据标记后，从已保存检查点显式恢复。",
                        "retryable": False,
                        "severity": "error",
                        **(
                            {"blocking_requirement_ids": blocking_ids}
                            if blocking_ids
                            else {}
                        ),
                    }
                else:
                    provider_error = _public_provider_error(
                        {
                            "message": raw_failure,
                            "provider": str(item.get("provider") or ""),
                            "model": str(item.get("model") or ""),
                            **({"code": str(item.get("code"))} if item.get("code") else {}),
                        }
                    )
                safe_failures.append(
                    {
                        "title": str(item.get("title") or "")[:200],
                        "provider": str(item.get("provider") or "")[:80],
                        "model": str(item.get("model") or "")[:120],
                        "error": provider_error["code"],
                        **provider_error,
                    }
                )
            return {
                "code": code,
                "message": str(parsed.get("message") or "任务执行失败。")[:500],
                "action": (
                    "请按阻断要求修订失败章节，并从已保存检查点显式恢复。"
                    if code == "REQUIREMENT_EVIDENCE_CHAPTER_BLOCKED"
                    else (
                        "请移除过小的手工预算，或按章节数量提高任务级模型调用预算后重新发起任务。"
                        if code == "EXECUTION_BUDGET_EXCEEDED"
                        else "请核对失败章节与模型健康状态后显式重试。"
                    )
                ),
                "failures": safe_failures,
            }
    validation_guidance = (
        (
            "CHAPTER_VALIDATION_QUALITY_BLOCKED",
            "CHAPTER_VALIDATION_QUALITY_BLOCKED",
            "章节真实模型验证质量门未通过。",
            "请按章节质量阻断项修订后，以相同交付范围从检查点恢复。",
        ),
        (
            "严格正式交付目录与招标目录不一致",
            "TENDER_OUTLINE_MISMATCH",
            "正式交付目录与招标目录不完全一致，系统未调用模型。",
            "请使用完整招标目录，或将小范围实跑明确设为 chapter_validation。",
        ),
        (
            "章节验证目录包含招标目录外章节",
            "CHAPTER_VALIDATION_OUTLINE_INVALID",
            "章节验证请求包含招标目录外章节，系统未调用模型。",
            "请仅选择招标目录中的章节进行验证。",
        ),
        (
            "招标文件/澄清答疑存在同优先级版式冲突",
            "TENDER_STYLE_CONFLICT",
            "招标版式要求存在同优先级冲突，系统未自行裁决。",
            "请确认冲突处理值后重新生成。",
        ),
        (
            "项目事实台账",
            "PROJECT_FACTS_INVALID",
            "项目事实台账未通过完整性或冲突校验。",
            "请确认项目事实或冲突处理值后重新生成。",
        ),
        (
            "项目适用规范生成前预检未通过",
            "COMPLIANCE_PREFLIGHT_BLOCKED",
            "项目适用规范生成前预检未通过。",
            "请补齐可核验的现行规范元数据后重新生成。",
        ),
        (
            "招标要求—证据计划完整性校验失败",
            "REQUIREMENT_EVIDENCE_PLAN_INVALID",
            "招标要求与证据计划未通过完整性校验。",
            "请补齐要求与章节证据绑定后重新生成。",
        ),
        (
            "招标要求—证据生成前准入失败",
            "REQUIREMENT_EVIDENCE_PREFLIGHT_BLOCKED",
            "招标要求的来源定位未通过生成前准入，系统尚未调用模型。",
            "请补齐阻断要求的可反查来源后重新生成。",
        ),
        (
            "项目适用规范核验未通过",
            "STANDARD_COMPLIANCE_BLOCKED",
            "章节初稿已保存，但项目适用规范核验未通过。",
            "请核对违规规范引用后从检查点恢复。",
        ),
        (
            "招标要求—证据矩阵完整性校验失败",
            "REQUIREMENT_EVIDENCE_INVALID",
            "章节初稿已保存，但招标要求与证据矩阵不完整。",
            "请补齐缺失证据绑定后从检查点恢复。",
        ),
        (
            "招标要求—证据交付硬门未通过",
            "REQUIREMENT_EVIDENCE_BLOCKED",
            "章节初稿已保存，但招标要求证据仍存在不可反查项。",
            "请修复阻断要求后从检查点恢复。",
        ),
        (
            "最终专业交付质量门未通过",
            "DELIVERY_QUALITY_BLOCKED",
            "章节初稿已保存，但最终专业交付质量门未通过。",
            "请根据质量门阻断项修订后从检查点恢复。",
        ),
    )
    for marker, code, message, action in validation_guidance:
        if marker in raw:
            result = {
                "code": code,
                "message": message,
                "action": action,
                "error_type": type(error).__name__ if isinstance(error, BaseException) else None,
            }
            if code == "DELIVERY_QUALITY_BLOCKED":
                blocker_codes = [
                    value
                    for value in re.findall(r"DELIVERY_[A-Z_]+", raw)
                    if value in _DELIVERY_BLOCKER_GUIDANCE
                ]
                if blocker_codes:
                    result["failures"] = [
                        {
                            "error": blocker_code,
                            "code": blocker_code,
                            "message": _DELIVERY_BLOCKER_GUIDANCE[blocker_code][0],
                            "action": _DELIVERY_BLOCKER_GUIDANCE[blocker_code][1],
                            "retryable": False,
                            "severity": "error",
                        }
                        for blocker_code in dict.fromkeys(blocker_codes)
                    ]
            elif code == "CHAPTER_VALIDATION_QUALITY_BLOCKED":
                blocker_codes = [
                    value
                    for value in re.findall(r"CHAPTER_[A-Z_]+_BLOCKED", raw)
                    if value in _CHAPTER_VALIDATION_BLOCKER_GUIDANCE
                ]
                if blocker_codes:
                    result["failures"] = [
                        {
                            "error": blocker_code,
                            "code": blocker_code,
                            "message": _CHAPTER_VALIDATION_BLOCKER_GUIDANCE[
                                blocker_code
                            ][0],
                            "action": _CHAPTER_VALIDATION_BLOCKER_GUIDANCE[
                                blocker_code
                            ][1],
                            "retryable": False,
                            "severity": "error",
                        }
                        for blocker_code in dict.fromkeys(blocker_codes)
                    ]
            return result
    if isinstance(error, ValueError):
        return {
            "code": "VALIDATION_FAILED",
            "message": "任务未通过输入或质量校验。",
            "action": "请核对运行阶段和已保存检查点后修正并重试。",
            "error_type": type(error).__name__,
        }
    error_info = classify_provider_error(raw, provider="", model="")
    return {
        "code": str(error_info.get("code") or "RUNTIME_FAILED"),
        "message": str(error_info.get("user_message") or "任务执行失败。")[:500],
        "action": str(error_info.get("action") or "请查看运行事件后重试。")[:500],
        "error_type": type(error).__name__ if isinstance(error, BaseException) else None,
    }


def _runtime_failure_transition(
    error: Any,
    prior_job: Dict[str, Any] | None,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any] | None]:
    """Build a truthful failure transition without discarding a complete draft."""

    prior = dict(prior_job or {})
    prior_progress = dict(prior.get("progress") or {})
    chapters = dict(prior_progress.get("chapters") or {})
    checkpoint = dict(prior_progress.get("checkpoint") or {})
    total = max(0, int(chapters.get("total") or 0))
    succeeded = max(0, int(chapters.get("succeeded") or 0))
    failed = max(0, int(chapters.get("failed") or 0))
    complete_draft = (
        isinstance(error, ValueError)
        and total > 0
        and succeeded == total
        and failed == 0
        and str(checkpoint.get("status") or "") in {"draft_complete", "complete"}
    )
    public_error = _public_runtime_error(error)
    phase = str(prior_progress.get("phase") or "generation")
    stage = "failed"
    recovery_result: Dict[str, Any] | None = None
    if complete_draft:
        phase = "quality_review"
        stage = "quality_review_failed"
        if public_error.get("code") == "VALIDATION_FAILED":
            public_error = {
                "code": "POST_GENERATION_QUALITY_BLOCKED",
                "message": "章节初稿已全部保存，但生成后质量校验未通过。",
                "action": "请保留检查点，核对规范、证据矩阵和交付质量门后显式恢复。",
                "error_type": "ValueError",
            }
        recovery_result = dict(prior.get("result") or {})
        recovery_result.update(
            {
                "section_count": succeeded,
                "checkpoint_status": str(checkpoint.get("status") or "draft_complete"),
                "recoverable": True,
                "delivery_ready": False,
            }
        )
    progress = {
        "percent": min(99, int(prior_progress.get("percent") or 0)),
        "stage": stage,
        "phase": phase,
        "work_state": "idle",
        "detail": str(public_error.get("message") or "任务执行失败。"),
    }
    return public_error, progress, recovery_result


def _seal_failed_run_checkpoints(job_id: str) -> Dict[str, Any] | None:
    """Make persisted checkpoint scopes agree with a failed run terminal state."""

    try:
        scopes = mark_failed_checkpoint_namespace(job_id)
    except Exception:
        append_runtime_event(
            job_id,
            "checkpoint_terminal_update_failed",
            code="CHECKPOINT_TERMINAL_UPDATE_FAILED",
        )
        return None
    if not scopes:
        return None
    saved = sum(max(0, int(item.get("saved_chapter_count") or 0)) for item in scopes)
    status = "failed_partial" if saved else "failed_empty"
    projection = {
        "status": status,
        "saved_chapter_count": saved,
        "scopes": scopes,
    }
    append_runtime_event(
        job_id,
        "checkpoint_terminal_updated",
        checkpoint_status=status,
        saved_chapter_count=saved,
    )
    return projection


def _auth_actions_key(x_actions_key: str | None):
    expected = os.environ.get("ZF_ACTIONS_KEY", "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SYSTEM_ACTIONS_KEY_NOT_CONFIGURED",
                "message": "系统内部操作凭据尚未配置，已阻断请求。",
                "action": "请通过受监管运行环境生成本机凭据后重启服务。",
            },
        )
    if (x_actions_key or "").strip() != expected:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "SYSTEM_ACTIONS_KEY_INVALID",
                "message": "系统内部操作凭据不匹配，已阻断请求。",
                "action": "请从最新受监管版本重新打开页面。",
            },
        )


class ActionsGenerateRequest(BaseModel):
    topic: str
    project_id: str | None = None
    project_type: str | None = None
    generation_mode: str | None = None
    delivery_scope: Literal["document", "chapter_validation"] = "document"
    outline: List[str] = []
    requirements: List[str] = []
    global_instruction: str | None = None
    chapter_requirements: dict | None = None
    chapter_summaries: List[dict | str] = []
    project_stage_context: str | None = None
    common_construction_requirements: List[str] = []
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
    max_chapter_output_tokens: int | None = None
    model_request_timeout_seconds: int | None = None
    chapter_deadline_seconds: int | None = None
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
    except Exception:
        return {
            "ok": False,
            "error": {
                "code": "PARAM_RECEIPT_UNAVAILABLE",
                "message": "参数回执暂时无法读取。",
                "action": "请稍后重试；如持续失败，请检查受监管服务状态。",
            },
            "receipt": {},
        }


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


_VARIANT_PAIR_RE = re.compile(r"^v(\d+)_v(\d+)$")


def _parse_variant_pair(raw: Any) -> tuple[int, int] | None:
    match = _VARIANT_PAIR_RE.fullmatch(str(raw or "").strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _delivery_progress_for_run(
    *,
    dry_run: bool,
    delivery_scope: str = "document",
) -> Dict[str, str]:
    if dry_run:
        return {
            "stage": "dry_run_done",
            "phase": "dry_run_done",
            "detail": "dry-run 预览已完成；未生成专业终稿或正式交付回执",
        }
    if str(delivery_scope or "document") == "chapter_validation":
        return {
            "stage": "chapter_validation_done",
            "phase": "chapter_validation_done",
            "detail": "章节真实模型验证已完成；未生成或冒充正式交付文件",
        }
    return {
        "stage": "done",
        "phase": "done",
        "detail": "专业 Word 已完成，可直接下载",
    }


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


def _build_resume_variant_plan(payload: dict, source_job: dict) -> List[Dict[str, Any]]:
    """Reuse the source job's immutable variant identities for checkpoint recovery."""

    source_payload = (
        source_job.get("payload") if isinstance(source_job.get("payload"), dict) else {}
    )
    requested_project_id = str(payload.get("project_id") or "").strip()
    source_project_id = str(source_payload.get("project_id") or "").strip()
    if (
        not requested_project_id
        or not source_project_id
        or requested_project_id != source_project_id
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESUME_PROJECT_SCOPE_MISMATCH",
                "message": "恢复请求与原任务的项目身份不一致，不能复用方案或检查点。",
            },
        )
    requested_scope = str(payload.get("delivery_scope") or "document").strip().lower()
    source_scope = str(source_payload.get("delivery_scope") or "document").strip().lower()
    if requested_scope != source_scope:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESUME_DELIVERY_SCOPE_MISMATCH",
                "message": "恢复请求不能跨正式交付与章节验证范围复用检查点。",
            },
        )
    source_plan = source_payload.get("_variant_plan")
    normalized: List[Dict[str, Any]] = []
    seen_variant_ids: set[int] = set()
    source_plan_invalid = not isinstance(source_plan, list) or not 1 <= len(source_plan) <= 5
    if isinstance(source_plan, list):
        for item in source_plan:
            if not isinstance(item, dict):
                source_plan_invalid = True
                continue
            try:
                variant_id = int(item.get("variant_id") or 0)
            except (TypeError, ValueError):
                variant_id = 0
            if variant_id <= 0:
                source_plan_invalid = True
                continue
            if variant_id in seen_variant_ids:
                source_plan_invalid = True
                continue
            seen_variant_ids.add(variant_id)
            row: Dict[str, Any] = {"variant_id": variant_id}
            template_id = _normalize_logic_template_id(item.get("logic_template_id"))
            if template_id:
                row["logic_template_id"] = template_id
            normalized.append(row)
    if source_plan_invalid or not normalized:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESUME_VARIANT_IDENTITY_INVALID",
                "message": "原任务的方案身份缺失、重复或超出安全范围，不能复用检查点。",
            },
        )

    requested_templates = _normalize_selected_templates(payload.get("selected_templates"))
    source_templates = [
        str(item.get("logic_template_id") or "") for item in normalized
    ]
    if requested_templates and requested_templates != source_templates:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESUME_VARIANT_TEMPLATE_MISMATCH",
                "message": "恢复请求的模板集合与原任务不一致。",
            },
        )
    try:
        requested_count = int(payload.get("variants") or 1)
    except (TypeError, ValueError):
        requested_count = 1
    if requested_templates:
        requested_count = len(requested_templates)
    if max(1, min(5, requested_count)) != len(normalized):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESUME_VARIANT_COUNT_MISMATCH",
                "message": "恢复请求的方案数量与原任务不一致。",
            },
        )
    if not requested_templates and all(source_templates):
        payload["selected_templates"] = source_templates
    payload["variants"] = len(normalized)
    return normalized


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
    explicit_validation_non_strict = (
        str(payload.get("delivery_scope") or "document").strip().lower()
        == "chapter_validation"
        and payload.get("quality_strict") is False
    )

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
    if explicit_validation_non_strict:
        # A bounded chapter validation produces JSON diagnostics only and can
        # honor an explicit non-strict request. Formal document modes remain
        # unconditionally strict.
        payload["quality_strict"] = False
    # A dry-run is a connectivity-free diagnostic preview, not a professional
    # delivery attempt.  Keep the real generation modes strict, but do not let
    # their defaults turn an offline preview into a failed delivery-quality
    # run or trigger remediation/model admission work.
    dry_run = bool(payload.get("dry_run"))
    if dry_run:
        payload["quality_strict"] = False
        payload["auto_remediate"] = False
        payload["model_preflight"] = False
        payload["fail_on_model_exhaustion"] = False
    payload["_mode_policy"] = {
        "mode_effective": mode,
        "auto_switched": bool(auto_switched),
        "planned_total_pages": int(pages),
        "dry_run": dry_run,
        "chapter_validation_non_strict": bool(
            explicit_validation_non_strict and not dry_run
        ),
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


def _assert_mandatory_generation_sources(payload: dict) -> None:
    if bool(payload.get("dry_run")):
        return
    project_scope = str(payload.get("project_id") or "").strip() or None
    if project_scope is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "PROJECT_SCOPE_REQUIRED",
                "message": "真实生成必须绑定明确项目，禁止使用全局资料池。",
            },
        )
    missing_sources: list[str] = []
    tender_source = load_tender_matrix(project_id=project_scope) or {}
    boq_source = load_boq_data(project_id=project_scope) or {}
    if not isinstance(tender_source.get("outline"), list) or not tender_source.get("outline"):
        missing_sources.append("tender")
    if not isinstance(boq_source.get("items"), list) or not boq_source.get("items"):
        missing_sources.append("boq")
    if missing_sources:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "MANDATORY_SOURCE_NOT_READY",
                "message": "招标/答疑与工程量清单必须全部解析成功后才能生成。",
                "missing": missing_sources,
            },
        )


def _apply_server_provider_routing_or_503(payload: dict) -> dict:
    try:
        return apply_server_provider_routing(payload)
    except ProviderRoutingConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_PROVIDER_CONFIGURATION_BLOCKED",
                "message": "服务端模型路由未配置完整或尚不支持准入，已阻止生成。",
                "action": "请检查本机主模型、备用模型和文档渲染模型配置。",
            },
        ) from exc


def _save_outputs(
    base_name: str,
    results: list[dict],
    *,
    preview_only: bool = False,
) -> dict:
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
    if blocked and not preview_only:
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
    if preview_only:
        return save_output_artifacts(base_name, results, preview_only=True)
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
    raw_max_model_parallelism = payload.get("max_model_parallelism")
    default_model_parallelism = min(agent_parallelism, 2)
    model_parallelism_source = "request"
    if raw_max_model_parallelism is None or raw_max_model_parallelism == "":
        raw_max_model_parallelism = default_model_parallelism
        model_parallelism_source = "safe_default"
    max_model_parallelism = _clamp_execution_int(
        raw_max_model_parallelism,
        default_model_parallelism,
        1,
        2,
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
        "model_parallelism_source": model_parallelism_source,
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


def _output_variant_value(result: dict[str, Any], key: str, variant: int) -> Any:
    value = result.get(key)
    if not isinstance(value, list):
        return value
    index = variant - 1
    return value[index] if 0 <= index < len(value) else None


def _professional_artifact_lists(
    result: dict[str, Any],
    *,
    variant_count: int,
) -> tuple[list[str], list[str], list[str]]:
    sources = result.get("source_docx")
    professional = result.get("professional_docx")
    receipts = result.get("professional_render_receipt")
    if not all(isinstance(value, list) for value in (sources, professional, receipts)):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DELIVERY_ARTIFACT_SET_INVALID",
                "message": "正式交付制品集合不完整，不能执行受控重渲染。",
            },
        )
    source_paths = [str(value or "") for value in sources]
    professional_paths = [str(value or "") for value in professional]
    receipt_paths = [str(value or "") for value in receipts]
    if (
        len(source_paths) != variant_count
        or len(professional_paths) != variant_count
        or len(receipt_paths) != variant_count
        or not all(source_paths + professional_paths + receipt_paths)
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DELIVERY_ARTIFACT_SET_INVALID",
                "message": "正式交付制品数量或路径不一致，不能执行受控重渲染。",
            },
        )
    return source_paths, professional_paths, receipt_paths


def _reseal_professional_variant(
    *,
    job_id: str,
    result: dict[str, Any],
    variant: int,
    variant_count: int,
    rendered: dict[str, Any],
) -> dict[str, Any]:
    source_paths, _, _ = _professional_artifact_lists(
        result,
        variant_count=variant_count,
    )
    candidate = copy.deepcopy(result)
    _set_output_variant_path(candidate, "professional_docx", variant, str(rendered["professional_docx"]))
    _set_output_variant_path(candidate, "professional_json", variant, str(rendered["professional_json"]))
    _set_output_variant_path(
        candidate,
        "professional_render_receipt",
        variant,
        str(rendered["professional_render_receipt"]),
    )
    professional_paths = [str(value) for value in candidate["professional_docx"]]
    receipt_paths = [str(value) for value in candidate["professional_render_receipt"]]
    receipt_path = (
        Path(str(rendered["professional_docx"])).parent
        / f"delivery_receipt_{job_id}_rerender_{uuid.uuid4().hex}.json"
    )
    sealed = build_delivery_receipt(
        job_id=job_id,
        source_docx=source_paths,
        professional_docx=professional_paths,
        professional_json=candidate.get("professional_json"),
        professional_receipts=receipt_paths,
        compare_docx=candidate.get("compare_docx"),
        focus_xlsx=candidate.get("focus_xlsx"),
        score_overview_xlsx=candidate.get("score_overview_xlsx"),
        expert_review_docx=candidate.get("expert_review_docx"),
        receipt_path=receipt_path,
    )
    candidate["docx"] = list(professional_paths)
    candidate["delivery_profile"] = "sonnet5_professional_word"
    candidate["delivery_receipt"] = str(sealed["receipt"])
    candidate["delivery_decision_digest"] = str(sealed["decision_digest"])
    return candidate


async def _render_professional_outputs_for_job(
    *,
    job_id: str,
    outputs: dict[str, Any],
    artifact_namespace: str | None = None,
    progress_callback: Any | None = None,
    execution_runtime: ExecutionControlRuntime | None = None,
    slot_override: ProviderSlot | None = None,
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
    if slot_override is None:
        slot_override = await _admit_current_server_route_for_existing_evidence(
            execution_runtime=execution_runtime
        )

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
        if artifact_namespace:
            render_kwargs["artifact_namespace"] = artifact_namespace
        if execution_runtime is not None:
            render_kwargs["execution_runtime"] = execution_runtime
        if slot_override is not None:
            render_kwargs["slot_override"] = slot_override
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
    delivery_receipt_kwargs: dict[str, Any] = {
        "job_id": job_id,
        "source_docx": source_docx,
        "professional_docx": professional_docx,
        "professional_json": professional_json,
        "professional_receipts": professional_receipts,
        "compare_docx": delivery.get("compare_docx"),
        "focus_xlsx": delivery.get("focus_xlsx"),
        "score_overview_xlsx": delivery.get("score_overview_xlsx"),
        "expert_review_docx": delivery.get("expert_review_docx"),
    }
    if artifact_namespace:
        safe_namespace = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "_",
            str(artifact_namespace),
        ).strip("._") or "candidate"
        delivery_receipt_kwargs["receipt_path"] = (
            Path(professional_docx[0]).parent
            / f"delivery_receipt_{safe_namespace}_{uuid.uuid4().hex}.json"
        )
    sealed_delivery = build_delivery_receipt(**delivery_receipt_kwargs)
    delivery["delivery_receipt"] = str(sealed_delivery["receipt"])
    delivery["delivery_decision_digest"] = str(sealed_delivery["decision_digest"])
    return delivery


def _admitted_document_render_slot(coordinator: Any) -> ProviderSlot:
    candidate = (
        coordinator.admitted_candidate("document_render")
        if coordinator is not None
        and callable(getattr(coordinator, "admitted_candidate", None))
        else None
    )
    if candidate is None:
        raise ProfessionalRenderError(
            "文档渲染模型未通过本次运行的供应商准入，已阻止专业终稿生成"
        )
    return ProviderSlot(
        slot=candidate.slot,
        role=candidate.role,
        provider=candidate.provider,
        model=candidate.model,
        api_key=candidate.credential,
        key_alias="",
    )


async def _admit_current_server_chain_for_existing_evidence(
    *,
    execution_runtime: ExecutionControlRuntime | None = None,
    require_document_render: bool = True,
) -> Any:
    """Freshly admit the full current route for an existing-evidence action."""

    candidates = build_server_provider_admission_candidates()
    required_roles = server_provider_admission_required_roles(
        candidates,
        require_document_render=require_document_render,
    )
    coordinator = new_provider_admission_run_coordinator({})
    snapshot = await coordinator.admit_chain_once(
        candidates=candidates,
        probe=lambda candidate: probe_provider_candidate(
            candidate,
            execution_runtime=execution_runtime,
        ),
        required_roles=required_roles,
    )
    if not bool(snapshot.get("generation_allowed")):
        from backend.zhifei_autoplan.provider_admission import public_snapshot

        admission = public_snapshot(snapshot)
        raise ProfessionalRenderError(
            "MODEL_PROVIDER_ADMISSION_BLOCKED: 模型供应商准入未通过；"
            + "、".join(admission.get("missing_roles") or ["unknown"])
        )
    return coordinator


async def _admit_current_server_route_for_existing_evidence(
    *,
    execution_runtime: ExecutionControlRuntime | None = None,
) -> ProviderSlot:
    """Freshly admit the full current route before a controlled re-render."""

    coordinator = await _admit_current_server_chain_for_existing_evidence(
        execution_runtime=execution_runtime
    )
    return _admitted_document_render_slot(coordinator)


async def _ensure_review_provider_admission(payload: dict[str, Any]) -> Any:
    """Bind review calls to one fresh, server-owned admission receipt."""

    existing = payload.get("_provider_admission_run_coordinator")
    if existing is not None:
        return existing
    try:
        routed = apply_server_provider_routing(payload)
        coordinator = await _admit_current_server_chain_for_existing_evidence(
            require_document_render=False,
        )
    except ProviderRoutingConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_PROVIDER_CONFIGURATION_BLOCKED",
                "message": "服务端模型路由未配置完整，已阻止复核调用。",
            },
        ) from exc
    except ProfessionalRenderError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_PROVIDER_ADMISSION_BLOCKED",
                "message": "模型供应商准入未通过，已在复核模型调用前停止。",
                "action": "请检查凭据、模型、配额和流式能力。",
            },
        ) from exc

    admitted_chain: list[dict[str, Any]] = []
    for candidate in coordinator.bound_candidates:
        if not str(candidate.role or "").startswith("text_"):
            continue
        admitted = coordinator.admitted_candidate(candidate.role)
        if admitted is None or admitted.identity_digest != candidate.identity_digest:
            continue
        admitted_chain.append(
            {
                "slot": candidate.slot,
                "role": candidate.role,
                "provider": candidate.provider,
                "model": candidate.model,
                # Ephemeral only: payload is a private per-request copy and is
                # never written back to the job record or response.
                "api_key": candidate.credential,
            }
        )
    if not admitted_chain:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODEL_PROVIDER_ADMISSION_EMPTY",
                "message": "没有可用的已准入复核模型，已停止调用。",
            },
        )
    routed["provider_chain"] = admitted_chain
    routed["provider"] = admitted_chain[0]["provider"]
    routed["model"] = admitted_chain[0]["model"]
    routed["_provider_admission_run_coordinator"] = coordinator
    payload.clear()
    payload.update(routed)
    return coordinator


def _professional_render_failure_result(
    outputs: dict[str, Any], error: Exception
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Preserve source artifacts without presenting them as final delivery."""

    delivery = copy.deepcopy(outputs or {})
    raw_sources = delivery.get("source_docx") or delivery.get("docx") or []
    if isinstance(raw_sources, (str, Path)):
        raw_sources = [raw_sources]
    if not isinstance(raw_sources, list):
        raw_sources = []
    source_docx = [str(path) for path in raw_sources if str(path)]
    delivery["source_docx"] = source_docx

    for key in (
        "docx",
        "professional_docx",
        "professional_json",
        "professional_render_receipt",
        "delivery_receipt",
        "delivery_decision_digest",
    ):
        delivery.pop(key, None)

    if isinstance(error, ProfessionalRenderError):
        error_info: dict[str, Any] = {
            "code": "professional_quality_gate_failed",
            "message": "professional render quality gate failed",
            "retryable": False,
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "user_message": "专业终稿未通过质量门槛。",
            "action": "请检查专业渲染报告后修正，禁止交付中间稿。",
            "severity": "error",
        }
    else:
        error_info = classify_provider_error(
            error,
            provider="anthropic",
            model="claude-sonnet-5",
        )

    delivery["delivery_profile"] = "professional_render_incomplete"
    delivery["delivery_ready"] = False
    delivery["professional_render_status"] = {
        "status": "failed",
        "retryable": bool(error_info.get("retryable")),
        "code": str(error_info.get("code") or "provider_error"),
        "message": str(error_info.get("user_message") or "专业终稿渲染未完成。"),
        "action": str(error_info.get("action") or ""),
        "source_preserved": bool(source_docx),
    }
    return delivery, error_info


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
            from backend.zhifei_autoplan.cross_index import (
                build_cross_index,
                validate_cross_index_contract,
            )

            drawing_index = v.get("drawing_index") if isinstance(v.get("drawing_index"), dict) else None
            standard_index = v.get("standard_index") if isinstance(v.get("standard_index"), dict) else None
            v["cross_index"] = validate_cross_index_contract(
                build_cross_index(
                    boq=boq,
                    sections=sections,
                    boq_focus=boq_focus,
                    drawing_index=drawing_index,
                    standard_index=standard_index,
                    quality_checks=qc,
                    project_id=pid,
                ),
                expected_names=(boq_focus or {}).get("must_cover_keywords") or [],
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
            chapter_gates: list[dict[str, Any]] = []
            for section in sections:
                if not isinstance(section, dict):
                    continue
                chapter_gates.append(
                    validate_chapter_requirement_evidence(
                        plan=requirement_plan,
                        title=str(section.get("title") or ""),
                        section=section,
                    )
                )
            v["requirement_evidence_chapter_gates"] = chapter_gates
            blocking_requirement_ids = sorted(
                {
                    str(requirement_id)
                    for gate in chapter_gates
                    for requirement_id in (gate.get("blocking_requirement_ids") or [])
                    if str(requirement_id).strip()
                }
            )
            requirement_hard_gate = bool(
                payload.get("requirement_evidence_hard_gate", bool(tender))
            )
            if strict and requirement_hard_gate and blocking_requirement_ids:
                postprocess_errors.append(
                    {
                        "stage": "requirement_evidence_chapter_gate",
                        "error_type": "RequirementEvidencePostprocessBlocked",
                        "message": json.dumps(
                            {
                                "code": "REQUIREMENT_EVIDENCE_POSTPROCESS_BLOCKED",
                                "blocking_requirement_ids": blocking_requirement_ids,
                            },
                            ensure_ascii=False,
                        ),
                    }
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
            # A quality decision is not a rebuild failure.  Keep it on the
            # dedicated delivery gate so formal exports fail with the precise
            # DELIVERY_QUALITY_GATE_BLOCKED code while an explicit dry-run
            # preview may still persist non-deliverable diagnostic artifacts.
            # Genuine derivation failures above remain fail-closed through
            # ``postprocess_errors``.
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


def _strict_formal_generation(payload: dict[str, Any]) -> bool:
    return (
        str(payload.get("delivery_scope") or "document").strip().lower()
        == "document"
        and not bool(payload.get("dry_run"))
        and bool(payload.get("quality_strict", True))
    )


def _finalize_variant_derivatives(
    results: list[dict[str, Any]],
    *,
    payload: dict[str, Any],
    allow_diversity_autofix: bool = True,
    force_rebuild: bool = False,
    fail_closed: bool | None = None,
    progress_callback: Any | None = None,
) -> dict[str, Any] | None:
    """Recompute cross-variant diversity and every derivative before export.

    Formal strict generation must never continue to persistence when diversity
    calculation, deterministic remediation, or derivative rebuilding fails.
    Validation and dry-run scopes keep this diagnostic best-effort behavior but
    remain non-deliverable.
    """

    if not results or (len(results) < 2 and not force_rebuild):
        return None
    enforce = _strict_formal_generation(payload) if fail_closed is None else bool(fail_closed)
    try:
        params = load_params()
        overrides = payload.get("params_override")
        if isinstance(overrides, dict) and overrides:
            for key, value in overrides.items():
                if isinstance(value, dict) and isinstance(params.get(key), dict):
                    merged = dict(params.get(key) or {})
                    merged.update(value)
                    params[key] = merged
                else:
                    params[key] = value

        report: dict[str, Any] | None = None
        if len(results) >= 2:
            from backend.zhifei_autoplan.diversity_autofix import (
                apply_diversity_autofix,
            )
            from backend.zhifei_autoplan.variant_similarity import (
                compute_variant_similarity,
            )

            div_cfg = (
                params.get("variant_diversity")
                if isinstance(params.get("variant_diversity"), dict)
                else {}
            )

            def _run_report() -> dict[str, Any]:
                return compute_variant_similarity(
                    results,
                    chapter_threshold=float(div_cfg.get("chapter_threshold") or 0.90),
                    overall_threshold=float(div_cfg.get("overall_threshold") or 0.85),
                    min_chars=int(div_cfg.get("min_chars") or 800),
                    ignore_title_keywords=(
                        div_cfg.get("ignore_title_keywords")
                        if isinstance(div_cfg.get("ignore_title_keywords"), list)
                        else None
                    ),
                    relaxed_title_keywords=(
                        div_cfg.get("relaxed_title_keywords")
                        if isinstance(div_cfg.get("relaxed_title_keywords"), list)
                        else None
                    ),
                    relaxed_chapter_threshold=(
                        float(div_cfg.get("relaxed_chapter_threshold"))
                        if div_cfg.get("relaxed_chapter_threshold") is not None
                        else None
                    ),
                )

            report = _run_report()
            max_rounds = int(div_cfg.get("auto_fix_rounds") or 1)
            max_rounds = max(0, max_rounds) if allow_diversity_autofix else 0
            rounds = 0
            while (
                rounds < max_rounds
                and report.get("ok") is False
                and report.get("flagged")
            ):
                changed_any = False
                for finding in (report.get("flagged") or [])[:24]:
                    title = str(finding.get("title") or "").strip()
                    pair = str(finding.get("pair") or "").strip()
                    pair_indexes = _parse_variant_pair(pair)
                    if not pair_indexes or not title:
                        continue
                    target_index = max(pair_indexes)
                    if target_index <= 1 or target_index > len(results):
                        continue
                    sections = results[target_index - 1].get("sections")
                    if not isinstance(sections, list):
                        continue
                    for section in sections:
                        if not isinstance(section, dict):
                            continue
                        if str(section.get("title") or "").strip() != title:
                            continue
                        if apply_diversity_autofix(
                            section,
                            params=params,
                            evidence_hint=pair,
                        ):
                            changed_any = True
                        break
                if not changed_any:
                    break
                report = _run_report()
                rounds += 1

        if callable(progress_callback):
            progress_callback()
        _rebuild_postprocessed_artifacts(
            results,
            payload=payload,
            report=report,
            params=params,
            fail_closed=enforce,
        )
        if enforce and isinstance(report, dict) and report.get("ok") is False:
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "VARIANT_DIVERSITY_BLOCKED",
                        "message": "多方案差异性校验仍未通过，已在正式文件生成前停止。",
                        "flagged_count": int(report.get("flagged_count") or 0),
                    },
                    ensure_ascii=False,
                )
            )
        return report
    except Exception as exc:
        if not enforce:
            return None
        try:
            parsed = json.loads(str(exc))
        except Exception:
            parsed = None
        if isinstance(parsed, dict) and parsed.get("code"):
            raise
        raise RuntimeError(
            json.dumps(
                {
                    "code": "POSTPROCESS_REBUILD_FAILED",
                    "message": "正式交付派生报告重建失败，已在文件生成前停止。",
                    "error_type": type(exc).__name__,
                },
                ensure_ascii=False,
            )
        ) from exc


def _load_done_job_variants(job_id: str) -> tuple[dict, dict, dict, list]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "JOB_NOT_FOUND", "message": "未找到指定任务。"},
        )
    if str(job.get("status") or "").strip() not in {"done", "succeeded"}:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "JOB_NOT_READY_FOR_RENDER",
                "message": "任务尚未完成，不能执行专业渲染。",
            },
        )
    result = job.get("result") or {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        raise HTTPException(status_code=404, detail="result json not found")
    data = json.loads(Path(json_path).read_text(encoding="utf-8", errors="ignore"))
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []
    if not variants:
        raise HTTPException(status_code=404, detail="empty result variants")
    return job, result, data, variants


def _require_variant_number(value: Any, variant_count: int) -> int:
    try:
        variant = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "VARIANT_OUT_OF_RANGE", "message": "方案序号无效。"},
        ) from exc
    if variant < 1 or variant > int(variant_count):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "VARIANT_OUT_OF_RANGE",
                "message": f"方案序号必须位于 1..{int(variant_count)}。",
            },
        )
    return variant


def _artifact_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _same_artifact_path(left: Any, right: Any) -> bool:
    try:
        return Path(str(left)).resolve() == Path(str(right)).resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def _promotion_audit_state(job: dict, result: dict) -> tuple[bool, str]:
    """Fail closed while a CAS-winning review promotion is not audit-committed."""

    raw_path = result.get("promotion_audit_receipt")
    if raw_path is None or not str(raw_path).strip():
        return True, "promotion_audit_not_applicable"
    audit_path = Path(str(raw_path))
    if not audit_path.is_file():
        return False, "promotion_audit_missing"
    try:
        raw_audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "promotion_audit_invalid"
    if not isinstance(raw_audit, dict):
        return False, "promotion_audit_invalid"
    expected_job_id = str(job.get("job_id") or "").strip()
    revision_id = str(raw_audit.get("revision_id") or "").strip()
    if (
        raw_audit.get("schema_version") != "review-revision-v1"
        or not str(raw_audit.get("snapshot_digest") or "").strip()
        or not expected_job_id
        or str(raw_audit.get("job_id") or "").strip() != expected_job_id
        or not revision_id
    ):
        return False, "promotion_audit_invalid"
    try:
        sealed_audit = load_revision_snapshot(
            job_id=expected_job_id,
            revision_id=revision_id,
        )
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        return False, "promotion_audit_invalid"
    if not _same_artifact_path(sealed_audit.get("path"), audit_path):
        return False, "promotion_audit_path_mismatch"
    promotion = sealed_audit.get("promotion")
    if not isinstance(promotion, dict):
        return False, "promotion_audit_invalid"
    state = str(promotion.get("state") or "").strip().lower()
    if state == "candidate_prepared":
        return False, "promotion_audit_pending"
    if state != "committed":
        return False, "promotion_audit_invalid"
    try:
        promoted_revision = int(promotion.get("promoted_job_revision") or 0)
        current_revision = int(job.get("revision") or 0)
    except (TypeError, ValueError):
        return False, "promotion_audit_invalid"
    if (
        promoted_revision <= 0
        or current_revision < promoted_revision
        or str(promotion.get("promoted_job_status") or "").strip().lower()
        not in {"done", "succeeded"}
        or not str(promotion.get("candidate_artifact_digest") or "").strip()
    ):
        return False, "promotion_audit_invalid"
    return True, "promotion_audit_committed"


def _formal_delivery_state(
    job: dict,
    result: dict,
    variants: list,
) -> tuple[bool, str]:
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    if bool(payload.get("dry_run")):
        return False, "dry_run"
    if (
        "delivery_scope" not in payload
        or not str(payload.get("delivery_scope") or "").strip()
    ):
        return False, "delivery_scope_missing"
    payload_scope = str(payload.get("delivery_scope") or "").strip().lower()
    if payload_scope != "document":
        return False, payload_scope or "unknown_scope"
    status = str(job.get("status") or "").strip().lower()
    if status not in {"done", "succeeded"}:
        return False, "job_not_succeeded"
    if not variants or any(not isinstance(row, dict) for row in variants):
        return False, "variant_record_invalid"
    if any(
        "delivery_scope" not in row
        or not str(row.get("delivery_scope") or "").strip()
        for row in variants
    ):
        return False, "variant_scope_missing"
    record_scopes = {
        str(row.get("delivery_scope") or "").strip().lower()
        for row in variants
        if isinstance(row, dict)
    }
    if record_scopes != {"document"}:
        return False, "variant_scope_mismatch"
    if any(row.get("delivery_ready") is not True for row in variants):
        return False, "delivery_not_ready"
    if not isinstance(result, dict):
        return False, "delivery_result_invalid"
    if str(result.get("delivery_profile") or "").strip() != "sonnet5_professional_word":
        return False, "delivery_profile_mismatch"
    if result.get("delivery_ready") is False:
        return False, "outer_delivery_not_ready"
    audit_ready, audit_reason = _promotion_audit_state(job, result)
    if not audit_ready:
        return False, audit_reason

    variant_count = len(variants)
    required_list_keys = (
        "source_docx",
        "docx",
        "professional_docx",
        "professional_json",
        "professional_render_receipt",
        "compare_docx",
    )
    optional_list_keys = (
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    )
    artifact_lists: dict[str, list[str | None]] = {}
    for key in required_list_keys + optional_list_keys:
        values = result.get(key)
        if not isinstance(values, list) or len(values) != variant_count:
            return False, "delivery_artifact_set_incomplete"
        normalized = [str(value or "").strip() or None for value in values]
        if key in required_list_keys and not all(normalized):
            return False, "delivery_artifact_set_incomplete"
        identities: set[Path] = set()
        for value in normalized:
            if value is None:
                continue
            try:
                identity = Path(value).resolve()
            except (OSError, RuntimeError, ValueError):
                return False, "delivery_artifact_path_invalid"
            if identity in identities:
                return False, "delivery_artifact_variant_reuse"
            identities.add(identity)
        artifact_lists[key] = normalized

    for docx, professional in zip(
        artifact_lists["docx"], artifact_lists["professional_docx"]
    ):
        if not _same_artifact_path(docx, professional):
            return False, "public_professional_path_mismatch"
        docx_path = Path(docx)
        professional_path = Path(professional)
        if not docx_path.is_file() or not professional_path.is_file():
            return False, "delivery_artifact_missing"
        try:
            if _artifact_sha256(docx_path) != _artifact_sha256(professional_path):
                return False, "public_professional_hash_mismatch"
        except OSError:
            return False, "delivery_artifact_unreadable"

    for key in (
        "source_docx",
        "professional_json",
        "professional_render_receipt",
        "compare_docx",
    ):
        if any(path is None or not Path(path).is_file() for path in artifact_lists[key]):
            return False, "delivery_artifact_missing"
    for key in optional_list_keys:
        if any(
            path is not None and not Path(path).is_file()
            for path in artifact_lists[key]
        ):
            return False, "delivery_artifact_missing"

    receipt_path = Path(str(result.get("delivery_receipt") or ""))
    decision_digest = str(result.get("delivery_decision_digest") or "").strip()
    if not decision_digest or not receipt_path.is_file():
        return False, "delivery_receipt_missing"
    try:
        task_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "delivery_receipt_invalid"
    if not isinstance(task_receipt, dict):
        return False, "delivery_receipt_invalid"
    try:
        receipt_variant_count = int(task_receipt.get("variant_count") or 0)
    except (TypeError, ValueError):
        return False, "delivery_receipt_invalid"
    recorded_digest = str(task_receipt.get("decision_digest") or "").strip()
    computed_digest = canonical_delivery_receipt_digest(task_receipt)
    if not recorded_digest or recorded_digest != computed_digest or decision_digest != computed_digest:
        return False, "delivery_receipt_digest_mismatch"
    if (
        task_receipt.get("schema") != "zhifei.delivery_receipt.v2"
        or task_receipt.get("status") != "pass"
        or task_receipt.get("delivery_profile") != "sonnet5_professional_word"
        or receipt_variant_count != variant_count
    ):
        return False, "delivery_receipt_invalid"
    expected_job_id = str(job.get("job_id") or "").strip()
    if expected_job_id and str(task_receipt.get("job_id") or "") != expected_job_id:
        return False, "delivery_receipt_job_mismatch"
    receipt_variants = task_receipt.get("variants")
    if not isinstance(receipt_variants, list) or len(receipt_variants) != variant_count:
        return False, "delivery_receipt_variant_mismatch"

    receipt_bindings = (
        ("source_docx", "source_docx", False),
        ("professional_docx", "professional_docx", False),
        ("professional_json", "professional_json", False),
        ("professional_render_receipt", "professional_render_receipt", False),
        ("compare_docx", "compare_docx", False),
        ("focus_xlsx", "focus_xlsx", True),
        ("score_overview_xlsx", "score_overview_xlsx", True),
        ("expert_review_docx", "expert_review_docx", True),
    )
    for index, row in enumerate(receipt_variants, start=1):
        if not isinstance(row, dict):
            return False, "delivery_receipt_variant_mismatch"
        try:
            receipt_variant = int(row.get("variant") or 0)
        except (TypeError, ValueError):
            return False, "delivery_receipt_variant_mismatch"
        if receipt_variant != index:
            return False, "delivery_receipt_variant_mismatch"
        for result_key, receipt_key, optional in receipt_bindings:
            if receipt_key not in row:
                return False, "delivery_receipt_artifact_invalid"
            artifact = row.get(receipt_key)
            expected_path = artifact_lists[result_key][index - 1]
            if optional and expected_path is None:
                if artifact is not None:
                    return False, "delivery_receipt_artifact_mismatch"
                continue
            if not isinstance(artifact, dict):
                return False, "delivery_receipt_artifact_invalid"
            if expected_path is None:
                return False, "delivery_receipt_artifact_invalid"
            if not _same_artifact_path(artifact.get("path"), expected_path):
                return False, "delivery_receipt_artifact_mismatch"
            path = Path(expected_path)
            try:
                actual_sha256 = _artifact_sha256(path)
            except OSError:
                return False, "delivery_artifact_unreadable"
            if str(artifact.get("sha256") or "") != actual_sha256:
                return False, "delivery_receipt_hash_mismatch"
    return True, "formal_document_ready"


def _public_job_files(job: dict, result: dict, variants: list) -> dict[str, Any]:
    formal_ready, reason = _formal_delivery_state(job, result, variants)
    public = {
        "json": result.get("json"),
        "delivery_profile": result.get("delivery_profile"),
        "delivery_ready": formal_ready,
    }
    formal_keys = (
        "docx",
        "professional_docx",
        "professional_json",
        "professional_render_receipt",
        "compare_docx",
        "delivery_receipt",
        "delivery_decision_digest",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    )
    if formal_ready:
        public.update({key: result.get(key) for key in formal_keys if result.get(key)})
    elif any(result.get(key) for key in formal_keys):
        public["artifact_leak_blocked"] = True
        public["non_delivery_reason"] = reason
    return public


def _require_formal_document_mutation(
    job: dict,
    result: dict,
    variants: list,
) -> None:
    formal_ready, reason = _formal_delivery_state(job, result, variants)
    if not formal_ready:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NON_DELIVERABLE_MUTATION_FORBIDDEN",
                "message": "非正式交付任务仅允许只读复核，不能晋升、回滚或渲染正式交付文件。",
                "reason": reason,
            },
        )


def _capture_promotion_revision(job: dict) -> tuple[str, int]:
    status = str(job.get("status") or "").strip().lower()
    try:
        revision = int(job.get("revision") or 0)
    except (TypeError, ValueError):
        revision = 0
    if status not in {"done", "succeeded"} or revision <= 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "STALE_PROMOTION",
                "message": "任务版本状态无效，候选结果未晋升。",
            },
        )
    return status, revision


def _promote_job_result_cas(
    *,
    job_id: str,
    initial_status: str,
    initial_revision: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    transitioned = transition_job(
        job_id,
        allowed_from={initial_status},
        status=initial_status,
        expected_revision=initial_revision,
        result=result,
        error=None,
    )
    if transitioned is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "STALE_PROMOTION",
                "message": "任务在候选文件生成期间已被其他操作更新；候选结果未晋升。",
            },
        )
    return transitioned


def _promote_review_candidate_two_phase(
    *,
    job_id: str,
    revision_id: str,
    initial_status: str,
    initial_revision: int,
    result: dict[str, Any],
    promotion: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prepare audit evidence, CAS the job, then commit the audit receipt.

    A prepare failure cannot mutate the live job.  A stale CAS leaves the
    snapshot explicitly in ``candidate_prepared`` state.  If the final audit
    commit fails after a successful CAS, the promoted job points back to the
    still-sealed prepared receipt so recovery can commit it idempotently.
    """

    candidate_digest = str(promotion.get("candidate_artifact_digest") or "").strip()
    if not candidate_digest:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PROMOTION_AUDIT_PREPARE_FAILED",
                "message": "候选制品摘要缺失，旧任务结果保持不变。",
            },
        )
    prepared_payload = dict(promotion)
    prepared_payload.update(
        {
            "expected_job_revision": int(initial_revision),
            "expected_job_status": str(initial_status),
            "expected_promoted_job_revision": int(initial_revision) + 1,
            "recovery": {
                "operation": "commit_prepared_promotion_after_job_cas_verification",
                "candidate_artifact_digest": candidate_digest,
                "expected_promoted_job_revision": int(initial_revision) + 1,
            },
        }
    )
    try:
        prepared = prepare_revision_promotion(
            job_id=job_id,
            revision_id=revision_id,
            promotion=prepared_payload,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PROMOTION_AUDIT_PREPARE_FAILED",
                "message": "候选晋升凭证封印失败，旧任务结果保持不变。",
                "revision_id": revision_id,
            },
        ) from exc

    result["promotion_audit_receipt"] = str(prepared["path"])
    transitioned = _promote_job_result_cas(
        job_id=job_id,
        initial_status=initial_status,
        initial_revision=initial_revision,
        result=result,
    )
    try:
        committed = commit_revision_promotion(
            job_id=job_id,
            revision_id=revision_id,
            candidate_artifact_digest=candidate_digest,
            promoted_job_revision=int(transitioned.get("revision") or 0),
            promoted_job_status=str(transitioned.get("status") or ""),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "PROMOTION_AUDIT_COMMIT_PENDING",
                "message": "任务已完成原子晋升，但审计凭证仍处于 candidate_prepared；可按凭证摘要安全续提 committed。",
                "revision_id": revision_id,
                "promotion_state": "candidate_prepared",
                "job_promotion_committed": True,
                "promoted_job_revision": int(transitioned.get("revision") or 0),
                "candidate_artifact_digest": candidate_digest,
                "promotion_audit_receipt": str(prepared["path"]),
            },
        ) from exc
    return transitioned, committed


def _validate_rollback_snapshot(
    *,
    revision: dict[str, Any],
    current_job: dict[str, Any],
    current_result: dict[str, Any],
    current_variants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    def _invalid(reason: str) -> HTTPException:
        return HTTPException(
            status_code=409,
            detail={
                "code": "ROLLBACK_SNAPSHOT_INVALID",
                "message": "回滚快照未通过身份与正式交付校验，未创建安全快照或候选文件。",
                "reason": reason,
            },
        )

    if revision.get("schema_version") != "review-revision-v1":
        raise _invalid("schema_mismatch")
    if not str(revision.get("snapshot_digest") or "").strip():
        raise _invalid("snapshot_seal_missing")
    restored = revision.get("variants")
    if not isinstance(restored, list) or any(not isinstance(row, dict) for row in restored):
        raise _invalid("variant_record_invalid")
    try:
        revision_variant_count = int(revision.get("variant_count") or 0)
    except (TypeError, ValueError):
        raise _invalid("variant_count_mismatch")
    if revision_variant_count != len(restored) or len(restored) != len(current_variants):
        raise _invalid("variant_count_mismatch")

    current_ids = [str(row.get("variant_id") or "").strip() for row in current_variants]
    restored_ids = [str(row.get("variant_id") or "").strip() for row in restored]
    if (
        not all(current_ids)
        or not all(restored_ids)
        or len(set(current_ids)) != len(current_ids)
        or restored_ids != current_ids
    ):
        raise _invalid("variant_identity_mismatch")

    formal_ready, reason = _formal_delivery_state(
        current_job,
        current_result,
        restored,
    )
    if not formal_ready:
        raise _invalid(f"restored_{reason}")
    return copy.deepcopy(restored)


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
    if payload.get("_provider_admission_run_coordinator") is None:
        audit["error"] = "provider_admission_required"
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
        client = LLMClient(provider, model, api_key=api_key, retry_attempts=1)
        try:
            response = await client.complete(
                prompt,
                timeout=240,
                max_tokens=12000,
                stream=True,
            )
        except Exception as exc:
            info = classify_provider_error(exc, provider=provider, model=model)
            attempt.update(
                {
                    "status": "failed",
                    "error": str(info.get("code") or "provider_error")[:80],
                }
            )
            audit["attempts"].append(attempt)
            continue
        finally:
            client.close()
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
    requested = str(
        req_base_url or os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434"
    ).strip().rstrip("/")
    if requested in {"http://127.0.0.1:11434", "http://localhost:11434"}:
        return "http://127.0.0.1:11434"
    return ""


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
    if not base_url:
        return {
            "ok": False,
            "enabled": bool(_ollama_smoke_enabled()),
            "status": "blocked",
            "provider": "ollama",
            "model": model,
            "base_url": "http://127.0.0.1:11434",
            "section_count": 0,
            "sections_preview": [],
            "error": {
                "code": "LOCAL_OLLAMA_LOOPBACK_REQUIRED",
                "message": "仅允许本机 Ollama 127.0.0.1:11434，已阻止其他地址。",
            },
            "warning": None,
            "smoke_type": smoke_type,
        }
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
    files: List[UploadFile] | None = File(default=None),
    file_id: List[str] | None = Query(default=None),
    project_id: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    if not files and not file_id:
        raise HTTPException(status_code=400, detail="no files")
    paths = await asyncio.gather(*[_save_upload(f) for f in (files or [])])
    cached_texts: Dict[str, str] = {}
    resolved_sources = await asyncio.to_thread(
        resolve_ingested_tender_sources, file_id
    )
    for source in resolved_sources:
        source_path = str(source["path"])
        paths.append(source_path)
        cached_text = source.get("cached_text")
        if isinstance(cached_text, str):
            cached_texts[source_path] = cached_text
    parser = TenderParser()
    matrix = await parser.parse(paths, cached_texts=cached_texts)
    matrix_dict = matrix.model_dump()
    parsed_code = _safe_project_scope(matrix_dict.get("project_code"))
    parsed_name = str(matrix_dict.get("project_name") or "").strip() or None
    requested_pid = _safe_project_scope(project_id)
    resolved_project_id = parsed_code or requested_pid
    if not resolved_project_id and parsed_name:
        resolved_project_id = _safe_project_scope(parsed_name)
    if not resolved_project_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_SCOPE_REQUIRED", "message": "无法确定招标资料所属项目。"},
        )
    if not isinstance(matrix_dict.get("outline"), list) or not matrix_dict.get("outline"):
        raise HTTPException(
            status_code=422,
            detail={"code": "TENDER_PARSE_NOT_READY", "message": "未解析出有效招标目录，资料未标记为可生成。"},
        )
    matrix_dict["parse_status"] = "ready"
    matrix_dict["project_id"] = resolved_project_id
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
    file: List[UploadFile] | None = File(default=None),
    file_id: List[str] | None = Query(default=None),
    project_id: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    if not file and not file_id:
        raise HTTPException(status_code=400, detail="no file")
    paths = await asyncio.gather(*[_save_upload(f) for f in (file or [])])
    paths.extend(await asyncio.to_thread(resolve_ingested_file_ids, file_id))
    parser = BoQParser()
    merged_items = []
    for p in paths:
        items, _ = await parser.parse(p)
        merged_items.extend(items)
    stats = parser._calc_stats(merged_items)
    project_scope = _safe_project_scope(project_id)
    if not project_scope:
        raise HTTPException(
            status_code=422,
            detail={"code": "PROJECT_SCOPE_REQUIRED", "message": "工程量清单必须绑定明确项目。"},
        )
    if not merged_items:
        raise HTTPException(
            status_code=422,
            detail={"code": "BOQ_PARSE_NOT_READY", "message": "未解析出有效工程量清单条目，资料未标记为可生成。"},
        )
    payload = {
        "items": [it.model_dump() for it in merged_items],
        "stats": stats,
        "source_file_count": len(paths),
        "parse_status": "ready",
        "project_id": project_scope,
    }
    saved_at = save_boq_data(payload, project_id=project_scope)
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
    job, stored_result, _, variants = _load_done_job_variants(job_id)
    _require_formal_document_mutation(job, stored_result, variants)
    initial_status, initial_revision = _capture_promotion_revision(job)
    result = dict(stored_result)
    variant = _require_variant_number(req.variant, len(variants))
    _professional_artifact_lists(result, variant_count=len(variants))
    render_source = dict(result)
    source_docx = result.get("source_docx")
    if isinstance(source_docx, list) and source_docx:
        render_source["docx"] = list(source_docx)
    candidate_namespace = (
        f"{job_id}-rerender-v{variant}-{uuid.uuid4().hex}"
    )
    try:
        admitted_slot = await _admit_current_server_route_for_existing_evidence()
        rendered = await render_professional_document(
            job_id=job_id,
            variant=variant,
            result=render_source,
            artifact_namespace=candidate_namespace,
            slot_override=admitted_slot,
        )
    except ProfessionalRenderError as exc:
        public_error = _public_runtime_error(exc)
        status_code = (
            503
            if str(public_error.get("code") or "").startswith("MODEL_PROVIDER_")
            else 422
        )
        raise HTTPException(status_code=status_code, detail=public_error) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=_public_runtime_error(exc),
        ) from exc

    try:
        candidate_result = _reseal_professional_variant(
            job_id=job_id,
            result=result,
            variant=variant,
            variant_count=len(variants),
            rendered=rendered,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "DELIVERY_RECEIPT_RESEAL_FAILED",
                "message": "专业 Word 已生成，但任务级交付封印重建失败，旧交付结果保持不变。",
            },
        ) from exc
    _promote_job_result_cas(
        job_id=job_id,
        initial_status=initial_status,
        initial_revision=initial_revision,
        result=candidate_result,
    )
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
    _assert_mandatory_generation_sources(payload)
    resume_from_job_id = str(payload.get("resume_from_job_id") or "").strip()
    if resume_from_job_id:
        if not re.fullmatch(r"[a-f0-9]{32}", resume_from_job_id):
            raise HTTPException(status_code=400, detail="invalid resume_from_job_id")
        source_job = get_job(resume_from_job_id)
        if not source_job:
            raise HTTPException(status_code=404, detail="resume source job not found")
        if str(source_job.get("status") or "").strip().lower() not in {
            "failed",
            "cancelled",
            "interrupted_recoverable",
        }:
            raise HTTPException(
                status_code=409,
                detail="only failed, cancelled or interrupted jobs can be resumed",
            )
        raise HTTPException(
            status_code=409,
            detail={
                "code": "RESUME_REQUIRES_ASYNC_JOB",
                "message": "检查点恢复仅支持异步任务入口，请使用 generate_async。",
            },
        )
    payload = _apply_server_provider_routing_or_503(payload)
    provider_admission_run = (
        new_provider_admission_run_coordinator(payload)
        if bool(payload.get("_provider_admission_required"))
        else None
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
        if provider_admission_run is not None:
            local_payload["_provider_admission_run_coordinator"] = provider_admission_run
        async with direct_sem:
            ordered_results[position] = await run_autoplan(local_payload)

    await asyncio.gather(
        *[_run_direct_variant(i, item) for i, item in enumerate(variant_plan)]
    )
    results = [item for item in ordered_results if isinstance(item, dict)]
    _finalize_variant_derivatives(results, payload=payload)
    is_dry_run = bool(payload.get("dry_run"))
    is_chapter_validation = (
        str(payload.get("delivery_scope") or "document") == "chapter_validation"
    )
    outputs = _save_outputs(
        "actions_generated",
        results,
        preview_only=is_dry_run or is_chapter_validation,
    )
    if is_dry_run:
        outputs["delivery_profile"] = "dry_run_preview_no_provider_calls"
        outputs["delivery_ready"] = False
    elif is_chapter_validation:
        outputs["delivery_profile"] = "chapter_validation_real_model_no_delivery"
        outputs["delivery_ready"] = False
        outputs["validation_scope"] = "chapter_validation"
    else:
        outputs = await _render_professional_outputs_for_job(
            job_id=f"direct-{uuid.uuid4().hex}",
            outputs=outputs,
            execution_runtime=execution_runtime,
            slot_override=_admitted_document_render_slot(provider_admission_run),
        )
    quality = [v.get("quality_checks") for v in results]
    return {
        "ok": True,
        "result": results,
        "quality": quality,
        "files": outputs,
        "execution_control": execution_runtime.snapshot(),
    }


def run_actions_generation_job(_job_id: str, _payload: dict):
    heartbeat_stop = threading.Event()
    heartbeat_thread: threading.Thread | None = None
    try:
        lease_record = acquire_job_lease(_job_id)
        if lease_record is None:
            return
        lease_attempt_id = str(lease_record.get("attempt_id") or "")
        lease_owner_instance_id = str(lease_record.get("owner_instance_id") or "")
        if not lease_attempt_id or not lease_owner_instance_id:
            raise RuntimeError("job_lease_acquisition_invalid")

        def _lease_active() -> bool:
            return job_lease_active(
                _job_id,
                attempt_id=lease_attempt_id,
                owner_instance_id=lease_owner_instance_id,
            )

        def _is_cancelled() -> bool:
            j = get_job(_job_id) or {}
            status = str(j.get("status") or "").strip().lower()
            if status in {
                "cancel_requested",
                "cancelled",
            }:
                return True
            return not _lease_active()

        def _lease_side_effect(callback: Any, *args: Any, **kwargs: Any) -> Any:
            return run_with_job_lease(
                _job_id,
                attempt_id=lease_attempt_id,
                owner_instance_id=lease_owner_instance_id,
                callback=callback,
                callback_args=tuple(args),
                callback_kwargs=dict(kwargs),
            )

        def _append_active_event(event: str, **fields: Any) -> bool:
            try:
                _lease_side_effect(
                    append_runtime_event,
                    _job_id,
                    event,
                    **fields,
                )
                return True
            except JobLeaseLostError:
                return False

        def _mark_cancelled(result: Dict[str, Any] | None = None) -> None:
            if not _lease_active():
                return
            prior_progress = ((get_job(_job_id) or {}).get("progress") or {})
            checkpoint_projection: Dict[str, Any]
            seal_failed = False
            try:
                from backend.zhifei_autoplan.generation_checkpoint import (
                    mark_checkpoint_namespace_interrupted,
                )

                checkpoints = _lease_side_effect(
                    mark_checkpoint_namespace_interrupted,
                    _job_id,
                )
                saved_chapter_count = sum(
                    int(item.get("saved_chapter_count") or 0)
                    for item in checkpoints
                    if isinstance(item, dict)
                )
                chapters_total = sum(
                    int(item.get("chapters_total") or 0)
                    for item in checkpoints
                    if isinstance(item, dict)
                )
                checkpoint_projection = {
                    "status": (
                        "interrupted_recoverable"
                        if checkpoints
                        else "interrupted_empty"
                    ),
                    "saved_chapter_count": saved_chapter_count,
                    "scopes": checkpoints,
                }
            except JobLeaseLostError:
                return
            except Exception as seal_error:
                seal_failed = True
                saved_chapter_count = 0
                chapters_total = int(prior_progress.get("chapters_total") or 0)
                checkpoint_projection = {
                    "status": "interruption_seal_failed",
                    "saved_chapter_count": 0,
                    "error_code": "CHECKPOINT_INTERRUPTION_SEAL_FAILED",
                    "error_type": type(seal_error).__name__,
                }

            prior_chapters = (
                prior_progress.get("chapters")
                if isinstance(prior_progress.get("chapters"), dict)
                else {}
            )
            chapters_total = max(
                chapters_total,
                int(prior_chapters.get("total") or 0),
            )
            chapters_started = max(
                saved_chapter_count,
                int(prior_chapters.get("started") or 0),
            )
            values: Dict[str, Any] = {
                "error": {
                    "code": (
                        "JOB_CANCELLED_CHECKPOINT_SEAL_FAILED"
                        if seal_failed
                        else "JOB_CANCELLED"
                    ),
                    "message": (
                        "用户已取消任务，但检查点封存失败；该故障已显式记录。"
                        if seal_failed
                        else "用户已取消任务。"
                    ),
                    "action": (
                        "先检查检查点存储与权限，再决定是否从先前可信断点恢复。"
                        if seal_failed
                        else "可从已保存的可信检查点显式恢复。"
                    ),
                },
                "progress": {
                    "percent": int(prior_progress.get("percent") or 0),
                    "stage": "cancelled",
                    "phase": str(prior_progress.get("phase") or "generation"),
                    "work_state": "idle",
                    "detail": "用户已取消；未完成章节已停止，已完成章节保留为可信断点。",
                    "chapters_total": chapters_total,
                    "chapters_done": saved_chapter_count,
                    "chapters_succeeded": saved_chapter_count,
                    "chapters_failed": int(prior_chapters.get("failed") or 0),
                    "chapters": {
                        "started": chapters_started,
                        "succeeded": saved_chapter_count,
                        "failed": int(prior_chapters.get("failed") or 0),
                        "total": chapters_total,
                    },
                    "checkpoint": checkpoint_projection,
                },
            }
            if isinstance(result, dict):
                values["result"] = result
            transitioned = transition_job(
                _job_id,
                allowed_from={"running", "cancel_requested"},
                status="cancelled",
                expected_attempt_id=lease_attempt_id,
                expected_owner_instance_id=lease_owner_instance_id,
                revoke_lease=True,
                **values,
            )
            if transitioned is None:
                return
            append_runtime_event(_job_id, "job_cancelled")

        local_payload = _apply_generation_mode_policy(json.loads(json.dumps(_payload)))
        local_payload["_job_id"] = _job_id
        provider_admission_run = (
            new_provider_admission_run_coordinator(local_payload)
            if bool(local_payload.get("_provider_admission_required"))
            else None
        )

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
            "work_state": "idle",
            "chapter_totals": {},
            "started": set(),
            "succeeded": set(),
            "failed": set(),
            "active": {},
            "provider": {},
        }

        def _activity_snapshot() -> tuple[str, Dict[str, Any]]:
            with activity_lock:
                runtime = dict(agent_runtime)
                current = [str(x) for x in activity_state.get("active", {}).values() if str(x).strip()]
                runtime.update(
                    {
                        "chapters_total": int(sum(activity_state.get("chapter_totals", {}).values())),
                        "chapters_started": len(activity_state.get("started", set())),
                        "chapters_succeeded": len(activity_state.get("succeeded", set())),
                        "chapters_failed": len(activity_state.get("failed", set())),
                        "chapters_done": len(activity_state.get("succeeded", set())),
                        "active_agents": len(current),
                        "current_chapters": current[:6],
                        "provider": dict(activity_state.get("provider") or {}),
                        "execution_control": execution_runtime.snapshot(),
                    }
                )
                agent_runtime.update(runtime)
                return str(activity_state.get("activity") or "Agent正在工作"), runtime

        def _heartbeat_loop() -> None:
            while not heartbeat_stop.is_set():
                if not _lease_active():
                    heartbeat_stop.set()
                    return
                activity, runtime = _activity_snapshot()
                heartbeat_job(
                    _job_id,
                    activity=activity,
                    progress_updates={
                        "phase": "generation",
                        "work_state": str(activity_state.get("work_state") or "idle"),
                        "chapters": {
                            "started": int(runtime.get("chapters_started") or 0),
                            "succeeded": int(runtime.get("chapters_succeeded") or 0),
                            "failed": int(runtime.get("chapters_failed") or 0),
                            "total": int(runtime.get("chapters_total") or 0),
                        },
                    },
                    agent_runtime_updates=runtime,
                    expected_attempt_id=lease_attempt_id,
                    expected_owner_instance_id=lease_owner_instance_id,
                )
                heartbeat_stop.wait(5.0)

        def _variant_progress_callback(variant_id: int):
            def _callback(event: Dict[str, Any]) -> None:
                if not _lease_active():
                    return
                event_name = str(event.get("event") or "").strip()
                chapter_idx = int(event.get("chapter_index") or 0)
                chapter_title = str(event.get("chapter_title") or "").strip()
                total = max(0, int(event.get("chapters_total") or 0))
                variant_key = str(int(variant_id))
                chapter_key = f"{variant_key}:{chapter_idx}"
                with activity_lock:
                    if total:
                        activity_state["chapter_totals"][variant_key] = total
                    if event_name == "preflight_started":
                        activity_state["work_state"] = "processing_preflight"
                        activity_state["activity"] = "正在校验项目事实、清单与生成约束"
                    elif event_name == "boq_schedule_started":
                        activity_state["work_state"] = "processing_preflight"
                        activity_state["activity"] = "正在校验工程量清单并构建有界进度网络"
                    elif event_name == "boq_schedule_completed":
                        activity_state["work_state"] = "processing_preflight"
                        warnings = int(event.get("warning_count") or 0)
                        activity_state["activity"] = (
                            "清单进度网络已完成，异常数量已隔离"
                            if warnings
                            else "清单进度网络已完成"
                        )
                    elif event_name == "compliance_preflight":
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
                    elif event_name == "provider_admission_started":
                        activity_state["work_state"] = "waiting_provider"
                        activity_state["provider"] = {
                            "admission_status": "checking",
                            "required_roles": list(event.get("required_roles") or []),
                            "candidate_count": int(event.get("candidate_count") or 0),
                        }
                        activity_state["activity"] = "正在执行模型供应商生成前准入检查"
                    elif event_name == "provider_admission_completed":
                        activity_state["work_state"] = "processing_chapter"
                        activity_state["provider"] = {
                            "admission_status": str(event.get("status") or "unknown"),
                            "generation_allowed": bool(event.get("generation_allowed")),
                            "degraded": bool(event.get("degraded")),
                            "admitted_chain": list(event.get("admitted_chain") or []),
                            "missing_roles": list(event.get("missing_roles") or []),
                            "public_digest": str(event.get("public_digest") or ""),
                        }
                        activity_state["activity"] = (
                            "模型供应商已降级准入，准备生成"
                            if bool(event.get("degraded"))
                            else "模型供应商准入通过，准备生成"
                        )
                    elif event_name == "provider_admission_failed":
                        activity_state["work_state"] = "idle"
                        activity_state["provider"] = {
                            "admission_status": "failed",
                            "code": str(event.get("code") or "MODEL_PROVIDER_ADMISSION_UNAVAILABLE"),
                        }
                        activity_state["activity"] = "模型供应商准入失败，任务已安全停止"
                    elif event_name == "chapter_started":
                        activity_state["started"].add(chapter_key)
                        activity_state["active"][chapter_key] = chapter_title
                        activity_state["work_state"] = "processing_chapter"
                    elif event_name == "chapter_resumed":
                        activity_state["started"].add(chapter_key)
                        activity_state["succeeded"].add(chapter_key)
                        activity_state["failed"].discard(chapter_key)
                        activity_state["active"].pop(chapter_key, None)
                        activity_state["activity"] = f"已从可信断点恢复章节：{chapter_title}"
                    elif event_name == "chapter_checkpoint_saved":
                        activity_state["work_state"] = "checkpointing"
                        activity_state["activity"] = f"章节已安全保存，可断点续编：{chapter_title}"
                    elif event_name == "chapter_completed":
                        activity_state["started"].add(chapter_key)
                        if bool(event.get("ok")):
                            activity_state["succeeded"].add(chapter_key)
                            activity_state["failed"].discard(chapter_key)
                        else:
                            activity_state["failed"].add(chapter_key)
                            activity_state["succeeded"].discard(chapter_key)
                        activity_state["active"].pop(chapter_key, None)
                    elif event_name == "provider_attempt_started":
                        activity_state["work_state"] = "waiting_provider"
                        activity_state["provider"] = {
                            "slot": str(event.get("slot") or ""),
                            "name": str(event.get("provider") or ""),
                            "model": str(event.get("model") or ""),
                            "request_started_at": time.time(),
                            "deadline_at": time.time() + int(event.get("request_timeout_seconds") or 240),
                        }
                        activity_state["activity"] = (
                            f"正在等待模型响应：{event.get('provider')}/{event.get('model')} · {chapter_title}"
                        )
                    elif event_name == "provider_attempt_finished":
                        provider_state = dict(activity_state.get("provider") or {})
                        provider_state["last_ok"] = bool(event.get("ok"))
                        provider_state["finished_at"] = time.time()
                        provider_state["circuits"] = (
                            dict(event.get("circuits"))
                            if isinstance(event.get("circuits"), dict)
                            else provider_state.get("circuits") or {}
                        )
                        activity_state["provider"] = provider_state
                        activity_state["work_state"] = "processing_chapter"
                    elif event_name == "draft_complete":
                        activity_state["work_state"] = "checkpointing"
                        activity_state["activity"] = "章节初稿完成，合规Agent正在复核与校验"
                    elif event_name == "draft_failed":
                        activity_state["work_state"] = "idle"
                        activity_state["activity"] = "章节生成存在失败，正在封存检查点与故障证据"

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
                    succeeded = len(activity_state.get("succeeded", set()))
                    failed = len(activity_state.get("failed", set()))
                    all_total = int(sum(activity_state.get("chapter_totals", {}).values()))

                progress_updates: Dict[str, Any] = {
                    "chapters_total": all_total,
                    "chapters_done": succeeded,
                    "chapters_succeeded": succeeded,
                    "chapters_failed": failed,
                    "chapters": {
                        "started": len(activity_state.get("started", set())),
                        "succeeded": succeeded,
                        "failed": failed,
                        "total": all_total,
                    },
                    "phase": "generation",
                    "work_state": str(activity_state.get("work_state") or "idle"),
                    "provider": dict(activity_state.get("provider") or {}),
                }
                if event.get("checkpoint_status") or event.get("saved_chapter_count") is not None:
                    progress_updates["checkpoint"] = {
                        "status": str(event.get("checkpoint_status") or "partial"),
                        "saved_chapter_count": int(event.get("saved_chapter_count") or 0),
                    }
                if all_total > 0:
                    progress_updates["percent"] = min(75, 15 + int((succeeded / all_total) * 60))
                activity, runtime = _activity_snapshot()
                _append_active_event(
                    event_name or "generation_progress",
                    variant_id=variant_id,
                    chapter_index=chapter_idx,
                    chapter_title=chapter_title,
                    ok=event.get("ok"),
                    provider=event.get("provider"),
                    model=event.get("model"),
                    slot=event.get("slot"),
                    blocking_requirement_ids=[
                        str(value)[:160]
                        for value in (event.get("blocking_requirement_ids") or [])[:20]
                        if str(value).strip()
                    ],
                    warning_requirement_ids=[
                        str(value)[:160]
                        for value in (event.get("warning_requirement_ids") or [])[:20]
                        if str(value).strip()
                    ],
                    chapters=progress_updates.get("chapters"),
                )
                heartbeat_job(
                    _job_id,
                    activity=activity,
                    progress_updates=progress_updates,
                    agent_runtime_updates=runtime,
                    expected_attempt_id=lease_attempt_id,
                    expected_owner_instance_id=lease_owner_instance_id,
                )

            return _callback

        def _update_progress(percent: int, stage: str, detail: str = "") -> None:
            p = max(0, min(100, int(percent)))
            updated = merge_job(
                _job_id,
                expected_attempt_id=lease_attempt_id,
                expected_owner_instance_id=lease_owner_instance_id,
                progress={
                    "percent": p,
                    "stage": str(stage or ""),
                    "phase": str(stage or ""),
                    "work_state": "idle" if p >= 100 else "processing",
                    "detail": str(detail or ""),
                    "variants_total": variants_total,
                    "variants_done": int(agent_runtime.get("variants_done") or 0),
                },
                agent_runtime=agent_runtime,
            )
            if updated is None:
                raise JobLeaseLostError("job_lease_lost")

        agent_runtime["execution_control"] = execution_runtime.snapshot()

        if _is_cancelled():
            _mark_cancelled()
            return
        started = merge_job(
            _job_id,
            expected_attempt_id=lease_attempt_id,
            expected_owner_instance_id=lease_owner_instance_id,
            agent_runtime=agent_runtime,
        )
        if started is None:
            return
        _append_active_event("job_started", execution_policy=execution_policy)
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
                # Recovery reads the immutable source namespace but always
                # writes a complete new checkpoint lineage under this job.
                lp["_checkpoint_namespace"] = _job_id
                lp["_resume_checkpoint_namespace"] = str(
                    local_payload.get("resume_from_job_id") or ""
                ).strip()
                lp["_cancel_callback"] = _is_cancelled
                lp["_checkpoint_write_guard"] = _lease_side_effect
                lp["_execution_runtime"] = execution_runtime
                if provider_admission_run is not None:
                    lp["_provider_admission_run_coordinator"] = provider_admission_run
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
            _mark_cancelled()
            return
        _finalize_variant_derivatives(
            results,
            payload=local_payload,
            progress_callback=lambda: _update_progress(
                86,
                "cross_variant_check",
                "正在执行跨方案一致性与差异性审计",
            ),
        )
        if _is_cancelled():
            _mark_cancelled()
            return
        _update_progress(91, "exporting_source", "正在生成可追溯中间稿与质控附件")
        is_dry_run = bool(local_payload.get("dry_run"))
        delivery_scope = str(local_payload.get("delivery_scope") or "document")
        is_chapter_validation = delivery_scope == "chapter_validation"
        outputs = _save_outputs(
            f"actions_{_job_id}",
            results,
            preview_only=is_dry_run or is_chapter_validation,
        )
        if _is_cancelled():
            _mark_cancelled(outputs)
            return

        def _professional_progress(variant: int, total: int) -> None:
            percent = 93 + int(((variant - 1) / max(1, total)) * 6)
            detail = f"Sonnet 5 正在精修并专业落版：方案 {variant}/{total}"
            with activity_lock:
                activity_state["activity"] = detail
            _update_progress(percent, "professional_rendering", detail)

        if is_dry_run:
            _update_progress(
                93,
                "dry_run_finalizing",
                "正在封装 dry-run 预览；不会生成专业终稿或正式交付回执",
            )
        elif is_chapter_validation:
            _update_progress(
                93,
                "chapter_validation_finalizing",
                "正在封装章节真实模型验证结果；不会生成正式交付文件",
            )
        else:
            _update_progress(
                93,
                "professional_rendering",
                "Sonnet 5 正在逐章精修、统一视觉规范并执行 Word 质量闸门",
            )
        try:
            if is_dry_run:
                outputs["delivery_profile"] = "dry_run_preview_no_provider_calls"
                outputs["delivery_ready"] = False
            elif is_chapter_validation:
                outputs["delivery_profile"] = "chapter_validation_real_model_no_delivery"
                outputs["delivery_ready"] = False
                outputs["validation_scope"] = "chapter_validation"
            else:
                outputs = asyncio.run(
                    _render_professional_outputs_for_job(
                        job_id=_job_id,
                        outputs=outputs,
                        progress_callback=_professional_progress,
                        execution_runtime=execution_runtime,
                        slot_override=_admitted_document_render_slot(
                            provider_admission_run
                        ),
                    )
                )
        except Exception as render_error:
            if _is_cancelled():
                _mark_cancelled()
                return
            agent_runtime["execution_control"] = execution_runtime.snapshot()
            recovery, error_info = _professional_render_failure_result(
                outputs,
                render_error,
            )
            failed_checkpoint = _lease_side_effect(
                _seal_failed_run_checkpoints,
                _job_id,
            )
            if failed_checkpoint is not None:
                saved_chapter_count = int(
                    failed_checkpoint.get("saved_chapter_count") or 0
                )
                recovery.update(
                    {
                        "section_count": saved_chapter_count,
                        "checkpoint_status": str(
                            failed_checkpoint.get("status") or "failed_partial"
                        ),
                        "recoverable": bool(saved_chapter_count),
                        "delivery_ready": False,
                    }
                )
            detail = (
                "专业终稿渲染未完成："
                f"{error_info.get('user_message') or '外部模型连接失败。'} "
                "已保全中间稿与质控附件；未将中间稿冒充专业终稿。"
            )
            failed_transition = transition_job(
                _job_id,
                allowed_from={"running"},
                status="failed",
                expected_attempt_id=lease_attempt_id,
                expected_owner_instance_id=lease_owner_instance_id,
                revoke_lease=True,
                error={
                    "code": str(error_info.get("code") or "PROFESSIONAL_RENDER_FAILED"),
                    "message": detail,
                    "action": str(error_info.get("action") or "检查模型连接后显式重试专业渲染。"),
                },
                result=recovery,
                agent_runtime=agent_runtime,
                progress={
                    "percent": min(99, int(((get_job(_job_id) or {}).get("progress") or {}).get("percent") or 0)),
                    "stage": "professional_render_failed",
                    "phase": "professional_rendering",
                    "work_state": "idle",
                    "detail": detail,
                    **(
                        {"checkpoint": failed_checkpoint}
                        if failed_checkpoint is not None
                        else {}
                    ),
                },
            )
            if failed_transition is not None:
                append_runtime_event(
                    _job_id,
                    "job_failed",
                    code=str(error_info.get("code") or "PROFESSIONAL_RENDER_FAILED"),
                    phase="professional_rendering",
                )
            return
        agent_runtime["execution_control"] = execution_runtime.snapshot()
        if _is_cancelled():
            _mark_cancelled(outputs)
            return
        completion = _delivery_progress_for_run(
            dry_run=is_dry_run,
            delivery_scope=delivery_scope,
        )
        _update_progress(100, completion["stage"], completion["detail"])
        succeeded_transition = transition_job(
            _job_id,
            allowed_from={"running"},
            status="succeeded",
            expected_attempt_id=lease_attempt_id,
            expected_owner_instance_id=lease_owner_instance_id,
            revoke_lease=True,
            result=outputs,
            agent_runtime=agent_runtime,
            progress={
                "stage": completion["stage"],
                "phase": completion["phase"],
                "work_state": "idle",
                "percent": 100,
                "detail": completion["detail"],
            },
        )
        if succeeded_transition is not None:
            append_runtime_event(
                _job_id,
                "job_succeeded",
                phase=completion["phase"],
                dry_run=is_dry_run,
                delivery_scope=delivery_scope,
            )
    except Exception as e:
        error_text = str(e)
        cancel_probe = locals().get("_is_cancelled")
        was_cancelled = bool(cancel_probe()) if callable(cancel_probe) else False
        if was_cancelled or "cancelled_by_user" in error_text:
            cancel_handler = locals().get("_mark_cancelled")
            if callable(cancel_handler):
                cancel_handler()
        else:
            prior_job = get_job(_job_id) or {}
            public_error, failure_progress, recovery_result = _runtime_failure_transition(
                e,
                prior_job,
            )
            failed_checkpoint = None
            lease_side_effect = locals().get("_lease_side_effect")
            if callable(lease_side_effect):
                try:
                    failed_checkpoint = lease_side_effect(
                        _seal_failed_run_checkpoints,
                        _job_id,
                    )
                except JobLeaseLostError:
                    failed_checkpoint = None
            if failed_checkpoint is not None:
                failure_progress["checkpoint"] = failed_checkpoint
                saved_chapter_count = int(
                    failed_checkpoint.get("saved_chapter_count") or 0
                )
                if recovery_result is None and saved_chapter_count:
                    recovery_result = dict(prior_job.get("result") or {})
                if recovery_result is not None:
                    recovery_result.update(
                        {
                            "section_count": saved_chapter_count,
                            "checkpoint_status": str(
                                failed_checkpoint.get("status") or "failed_partial"
                            ),
                            "recoverable": bool(saved_chapter_count),
                            "delivery_ready": False,
                        }
                    )
            failure_fields: Dict[str, Any] = {
                "error": public_error,
                "progress": failure_progress,
            }
            if recovery_result is not None:
                failure_fields["result"] = recovery_result
            active_attempt_id = str(locals().get("lease_attempt_id") or "")
            active_owner_id = str(locals().get("lease_owner_instance_id") or "")
            failed_transition = None
            if active_attempt_id and active_owner_id:
                failed_transition = transition_job(
                    _job_id,
                    allowed_from={"running"},
                    status="failed",
                    expected_attempt_id=active_attempt_id,
                    expected_owner_instance_id=active_owner_id,
                    revoke_lease=True,
                    **failure_fields,
                )
            if failed_transition is not None:
                append_runtime_event(
                    _job_id,
                    "job_failed",
                    code=public_error.get("code"),
                    phase=str(failure_progress.get("phase") or "generation"),
                    failures=public_error.get("failures"),
                )
    finally:
        heartbeat_stop.set()
        if heartbeat_thread is not None and heartbeat_thread.is_alive():
            heartbeat_thread.join(timeout=0.25)

@router.post("/generate_async")
async def actions_generate_async(
    req: ActionsGenerateRequest,
    background_tasks: BackgroundTasks,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    payload = _merge_plan_defaults(req.model_dump())
    _assert_mandatory_generation_sources(payload)
    resume_source_job: Dict[str, Any] | None = None
    resume_from_job_id = str(payload.get("resume_from_job_id") or "").strip()
    if resume_from_job_id:
        if not re.fullmatch(r"[a-f0-9]{32}", resume_from_job_id):
            raise HTTPException(status_code=400, detail="invalid resume_from_job_id")
        source_job = get_job(resume_from_job_id)
        if not source_job:
            raise HTTPException(status_code=404, detail="resume source job not found")
        if str(source_job.get("status") or "").strip().lower() not in {
            "failed",
            "cancelled",
            "interrupted_recoverable",
        }:
            raise HTTPException(
                status_code=409,
                detail="only failed, cancelled or interrupted jobs can be resumed",
            )
        resume_source_job = source_job
    payload = _apply_server_provider_routing_or_503(payload)
    variant_plan = (
        _build_resume_variant_plan(payload, resume_source_job)
        if resume_source_job is not None
        else _build_variant_plan(payload)
    )
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(v.get("variant_id") or 1) for v in variant_plan]
    payload["variants"] = len(variant_plan) if variant_plan else int(payload.get("variants") or 1)
    job_id = create_job(payload, user_id=None)

    queue_depth = submit_isolated_job(job_id, run_actions_generation_job, job_id, payload)
    return {"ok": True, "job_id": job_id, "run_id": job_id, "status": "queued", "queue_depth": queue_depth}


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
    if status in {"done", "succeeded", "failed", "cancelled", "interrupted_recoverable"}:
        return {"ok": True, "job_id": job_id, "status": status}
    transitioned = transition_job(
        job_id,
        allowed_from={"queued", "running"},
        status="cancel_requested",
        error={
            "code": "JOB_CANCEL_REQUESTED",
            "message": "已收到取消请求，正在停止活动工作并封存检查点。",
            "action": "请等待任务确认取消；已完成章节不会被删除。",
        },
        progress={"work_state": "cancelling", "stage": "cancel_requested"},
    )
    if transitioned is None:
        latest = get_job(job_id) or {}
        return {"ok": True, "job_id": job_id, "status": latest.get("status")}
    append_runtime_event(job_id, "cancel_requested")
    return {"ok": True, "job_id": job_id, "status": "cancel_requested"}


@router.get("/job_status")
async def actions_job_status(job_id: str, x_actions_key: str | None = Header(default=None)):
    _auth_actions_key(x_actions_key)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    runtime = job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {}
    public_provider = _public_provider_state(progress.get("provider") or runtime.get("provider") or {})
    public_progress = dict(progress)
    if isinstance(public_progress.get("provider"), dict):
        public_progress["provider"] = _public_provider_state(public_progress["provider"])
    public_runtime = dict(runtime)
    if isinstance(public_runtime.get("provider"), dict):
        public_runtime["provider"] = _public_provider_state(public_runtime["provider"])
    chapters = progress.get("chapters") if isinstance(progress.get("chapters"), dict) else {
        "started": int(progress.get("chapters_started") or runtime.get("chapters_started") or 0),
        "succeeded": int(progress.get("chapters_succeeded") or runtime.get("chapters_succeeded") or progress.get("chapters_done") or 0),
        "failed": int(progress.get("chapters_failed") or runtime.get("chapters_failed") or 0),
        "total": int(progress.get("chapters_total") or runtime.get("chapters_total") or 0),
    }
    out = {
        "job_id": job.get("job_id"),
        "run_id": job.get("job_id"),
        "status": job.get("status"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "heartbeat_at": progress.get("heartbeat_at"),
        "phase": progress.get("phase") or progress.get("stage"),
        "work_state": progress.get("work_state") or "idle",
        "chapters": chapters,
        "provider": public_provider,
        "checkpoint": progress.get("checkpoint") or {},
        "warnings": progress.get("warnings") if isinstance(progress.get("warnings"), list) else [],
        "progress": public_progress,
        "agent_runtime": public_runtime,
        "event_journal": str(event_journal_path(job_id) or "") or None,
    }
    result = job.get("result") or {}
    if isinstance(result, dict):
        json_path = result.get("json")
        variants = []
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
                variants = []
        out["files"] = _public_job_files(job, result, variants)
    return {"ok": True, "job": out}


@router.post("/runs")
async def actions_create_run(
    req: ActionsGenerateRequest,
    background_tasks: BackgroundTasks,
    x_actions_key: str | None = Header(default=None),
):
    """Unified run-creation alias; legacy generate_async remains supported."""

    return await actions_generate_async(req, background_tasks, x_actions_key)


@router.get("/runs/{run_id}")
async def actions_get_run(
    run_id: str,
    x_actions_key: str | None = Header(default=None),
):
    return await actions_job_status(run_id, x_actions_key)


@router.post("/runs/{run_id}/cancel")
async def actions_cancel_run(
    run_id: str,
    x_actions_key: str | None = Header(default=None),
):
    return await actions_job_cancel(ActionsJobCancelRequest(job_id=run_id), x_actions_key)


@router.get("/review/issues")
async def actions_review_issues(
    job_id: str,
    variant: int = 1,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    _, _, _, variants = _load_done_job_variants(job_id)
    v = _require_variant_number(variant, len(variants))
    rec = variants[v - 1]
    idx = v - 1
    items = _review_items_for_variant(rec)
    versions = _review_versions(variants, idx)
    return {
        "ok": True,
        "job_id": job_id,
        "variant": v,
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
    _require_formal_document_mutation(job, current_result, variants)
    initial_status, initial_revision = _capture_promotion_revision(job)

    v = _require_variant_number(req.variant, len(variants))
    idx = v - 1
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
    payload_obj = (
        copy.deepcopy(job.get("payload") or {})
        if isinstance(job.get("payload"), dict)
        else {}
    )
    overrides = payload_obj.get("params_override")
    if isinstance(overrides, dict) and overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(params.get(k), dict):
                merged = dict(params.get(k) or {})
                merged.update(v)
                params[k] = merged
            else:
                params[k] = v

    # Manual replacements need no text model.  As soon as an AI rewrite is
    # required, run one fresh full-chain admission and reuse it for both review
    # rounds and the final professional renderer.
    review_admission = None
    if grouped:
        review_admission = await _ensure_review_provider_admission(payload_obj)

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

    # Rebuild the complete candidate set after round 1.  Cross-variant
    # diversity is a document-level invariant; a one-variant rebuild could
    # otherwise promote a reviewed chapter that duplicates another方案.
    _finalize_variant_derivatives(
        candidate_variants,
        payload=payload_obj,
        allow_diversity_autofix=False,
        force_rebuild=True,
        fail_closed=True,
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
            # A second full-set rebuild is mandatory after AI round 2 so every
            # derivative and the diversity gate describe the final candidate.
            _finalize_variant_derivatives(
                candidate_variants,
                payload=payload_obj,
                allow_diversity_autofix=False,
                force_rebuild=True,
                fail_closed=True,
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
    render_kwargs: dict[str, Any] = {
        "job_id": job_id,
        "artifact_namespace": f"{job_id}-{candidate_suffix}",
        "outputs": out,
    }
    if review_admission is not None:
        render_kwargs["slot_override"] = _admitted_document_render_slot(
            review_admission
        )
    out = await _render_professional_outputs_for_job(**render_kwargs)
    candidate_artifacts = artifact_manifest(out)
    candidate_artifact_digest = canonical_digest(candidate_artifacts)
    _promote_review_candidate_two_phase(
        job_id=job_id,
        revision_id=revision["revision_id"],
        initial_status=initial_status,
        initial_revision=initial_revision,
        result=out,
        promotion={
            "actor": str(req.actor or "webui").strip() or "webui",
            "candidate_result_version": candidate_version,
            "candidate_variant_version": variant_version(target),
            "candidate_issue_digest": issue_set_digest(final_review_items),
            "candidate_artifact_digest": candidate_artifact_digest,
            "artifacts": candidate_artifacts,
        },
    )

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
        "candidate_artifact_digest": candidate_artifact_digest,
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
    current_job, current_result, _, current_variants = _load_done_job_variants(job_id)
    _require_formal_document_mutation(
        current_job,
        current_result,
        current_variants,
    )
    initial_status, initial_revision = _capture_promotion_revision(current_job)
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

    restored_variants = _validate_rollback_snapshot(
        revision=revision,
        current_job=current_job,
        current_result=current_result,
        current_variants=current_variants,
    )
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
    restored_version = result_version(restored_variants)
    candidate_suffix = f"rollback-{revision_id.lower()}-{safety['revision_id'].lower()}"
    out = _save_outputs(f"actions_{job_id}_{candidate_suffix}", restored_variants)
    out = await _render_professional_outputs_for_job(
        job_id=job_id,
        artifact_namespace=f"{job_id}-{candidate_suffix}",
        outputs=out,
    )
    rollback_artifacts = artifact_manifest(out)
    rollback_artifact_digest = canonical_digest(rollback_artifacts)
    _promote_review_candidate_two_phase(
        job_id=job_id,
        revision_id=safety["revision_id"],
        initial_status=initial_status,
        initial_revision=initial_revision,
        result=out,
        promotion={
            "actor": str(req.actor or "webui").strip() or "webui",
            "operation": "rollback",
            "restored_revision_id": revision_id,
            "candidate_result_version": restored_version,
            "candidate_artifact_digest": rollback_artifact_digest,
            "artifacts": rollback_artifacts,
        },
    )
    return {
        "ok": True,
        "job_id": job_id,
        "restored_revision_id": revision_id,
        "safety_revision_id": safety["revision_id"],
        "result_version": restored_version,
        "candidate_artifact_digest": rollback_artifact_digest,
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
    if str(job.get("status") or "").strip() not in {"done", "succeeded"}:
        return {"ok": False, "status": job.get("status"), "error": job.get("error")}
    result = job.get("result") or {}
    json_path = result.get("json")
    if not json_path or not Path(json_path).exists():
        raise HTTPException(status_code=404, detail="result json not found")
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    variants = data.get("variants") or []
    if not variants:
        raise HTTPException(status_code=404, detail="empty result")
    v = _require_variant_number(variant, len(variants))
    rec = variants[v - 1]
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    if (
        "delivery_scope" not in payload
        or not str(payload.get("delivery_scope") or "").strip()
        or "delivery_scope" not in rec
        or not str(rec.get("delivery_scope") or "").strip()
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DELIVERY_SCOPE_RESULT_MISSING",
                "message": "任务请求或结果记录缺少显式交付范围，系统已失败关闭。",
            },
        )
    payload_scope = str(payload.get("delivery_scope") or "").strip().lower()
    record_scope = str(rec.get("delivery_scope") or "").strip().lower()
    if payload_scope != record_scope:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "DELIVERY_SCOPE_RESULT_MISMATCH",
                "message": "任务请求与结果记录的交付范围不一致。",
            },
        )
    formal_ready, non_delivery_reason = _formal_delivery_state(job, result, variants)
    formal_artifact_keys = (
        "docx",
        "compare_docx",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
        "professional_docx",
        "professional_render_receipt",
        "delivery_receipt",
    )
    if not formal_ready and any(result.get(key) for key in formal_artifact_keys):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NON_DELIVERABLE_ARTIFACT_LEAK_BLOCKED",
                "message": "非正式交付结果包含正式文件引用，系统已阻断暴露。",
                "reason": non_delivery_reason,
            },
        )
    files = {"json": json_path}
    if formal_ready:
        files.update(
            {
                "docx": _output_variant_value(result, "docx", v),
                "compare_docx": _output_variant_value(result, "compare_docx", v),
                "focus_xlsx": _output_variant_value(result, "focus_xlsx", v),
                "score_overview_xlsx": _output_variant_value(result, "score_overview_xlsx", v),
                "expert_review_docx": _output_variant_value(result, "expert_review_docx", v),
                "professional_docx": _output_variant_value(result, "professional_docx", v),
                "professional_render_receipt": _output_variant_value(
                    result,
                    "professional_render_receipt",
                    v,
                ),
                "delivery_receipt": result.get("delivery_receipt"),
            }
        )
    response = {
        "ok": True,
        "variant_id": rec.get("variant_id") or v,
        "topic": rec.get("topic"),
        "outline": rec.get("outline"),
        "delivery_scope": record_scope,
        "delivery_ready": formal_ready,
        "boq_focus": rec.get("boq_focus"),
        "quality_checks": rec.get("quality_checks"),
        "files": files,
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
    allowed_kinds = {
        "json",
        "docx",
        "professional_docx",
        "professional_json",
        "professional_render_receipt",
        "compare_docx",
        "delivery_receipt",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    }
    if kind not in allowed_kinds:
        raise HTTPException(
            status_code=422,
            detail={"code": "DOWNLOAD_KIND_INVALID", "message": "下载类型不在允许清单中。"},
        )
    job, result, _, variants = _load_done_job_variants(job_id)
    v = _require_variant_number(variant, len(variants))
    if kind != "json":
        _require_formal_document_mutation(job, result, variants)
    path = (
        _output_variant_value(result, kind, v)
        if kind in {
            "docx",
            "professional_docx",
            "professional_json",
            "professional_render_receipt",
            "compare_docx",
            "focus_xlsx",
            "score_overview_xlsx",
            "expert_review_docx",
        }
        else result.get(kind)
    )
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
            filename = f"autoplan_{job_id}{suffix}_v{v}.json"
    elif kind == "focus_xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"autoplan_{job_id}_focus_v{v}.xlsx"
    elif kind == "score_overview_xlsx":
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"autoplan_{job_id}_评分点覆盖与证据引用总览_v{v}.xlsx"
    elif kind == "expert_review_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_专家复核提要版_v{v}.docx"
    elif kind == "professional_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_Sonnet5专业精修版_v{v}.docx"
    elif kind == "compare_docx":
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_compare_v{v}.docx"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"autoplan_{job_id}_v{v}.docx"
    return FileResponse(str(path), media_type=media_type, filename=filename)
