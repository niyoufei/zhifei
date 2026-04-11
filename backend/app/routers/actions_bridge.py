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
from backend.zhifei_autoplan.quality_check import run_quality_checks, strip_nonconcrete_language
from backend.zhifei_autoplan.orchestrator import _build_boq_focus
from backend.zhifei_autoplan.media import generate_boq_chart, generate_ingested_previews, generate_outline_mindmap
from backend.zhifei_autoplan.params_runtime import load_params, get_image_defaults, save_params
from backend.zhifei_autoplan.four_new_tech import recommend_four_new
from backend.zhifei_autoplan.resource_audit import append_resource_event
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.docx_formatter import build_bidding_format_config_from_style
from backend.zhifei_autoplan.provider_runtime import apply_server_provider_routing, iterate_image_failover_slots
from backend.zhifei_autoplan.self_evolution import build_chapter_effect_summary, summarize_runtime_budget_profile
from backend.zhifei_autoplan.chief_engineer_agent import load_chief_engineer_state
from backend.zhifei_autoplan.job_admission import admission_http_detail, apply_admission_degrade, evaluate_job_admission
from backend.zhifei_autoplan.workspace import maybe_cleanup_expired_workspaces, resolve_workspace_dir, workspace_paths


router = APIRouter(prefix="/actions", tags=["Actions Bridge"])
_HOUSEKEEP_LAST_TS = 0.0
_HOUSEKEEP_LAST_REPORT: Dict[str, Any] = {}
WORKER_LOG_DIR = Path("logs/job_workers")
WORKER_LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("zhifei.actions")


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
    detail: Dict[str, Any] = {
        "ok": False,
        "code": str(code or "").strip() or "actions_error",
        "message": str(message or "").strip() or "actions error",
        "stage": str(stage or "").strip() or "unknown",
        "log_anchor": str(log_anchor or "").strip(),
    }
    if job_id:
        detail["job_id"] = str(job_id)
    if request_id:
        detail["request_id"] = str(request_id)
    if trace_id:
        detail["trace_id"] = str(trace_id)
    if next_action:
        detail["next_action"] = str(next_action)
    if isinstance(extra, dict) and extra:
        detail["extra"] = extra
    return detail


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
    if not isinstance(result, dict):
        return {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        return {}
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    variants = data.get("variants") if isinstance(data, dict) else []
    if not isinstance(variants, list) or not variants:
        return {}
    first = variants[0] if isinstance(variants[0], dict) else {}
    if not isinstance(first, dict):
        return {}
    quality_gate = first.get("quality_gate") if isinstance(first.get("quality_gate"), dict) else {}
    terminology_audit = first.get("terminology_audit") if isinstance(first.get("terminology_audit"), dict) else {}
    return {
        "quality_gate_ok": bool(quality_gate.get("ok", False)),
        "quality_gate_failed_count": len(quality_gate.get("failed") or []) if isinstance(quality_gate.get("failed"), list) else 0,
        "quality_gate_retry_rounds": int(first.get("quality_gate_retry_rounds") or 0),
        "quality_score_final": (first.get("quality_checks") or {}).get("score") if isinstance(first.get("quality_checks"), dict) else None,
        "terminology_replacement_count": int(terminology_audit.get("replacement_count") or 0),
        "terminology_changed_sections": int(terminology_audit.get("changed_sections") or 0),
    }


def _recent_job_first_variant_summary(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    rows = [item for item in raw.values() if isinstance(item, dict)]
    if not rows:
        return {}
    rows.sort(
        key=lambda item: (
            int(item.get("variant_index") or 0),
            str(item.get("variant_id") or ""),
        )
    )
    return rows[0]


def _recent_job_generation_mode_summary(payload: dict | None, result: dict | None) -> dict[str, Any]:
    mode_policy = payload.get("_mode_policy") if isinstance(payload, dict) and isinstance(payload.get("_mode_policy"), dict) else {}
    result_summary = result.get("generation_mode_summary") if isinstance(result, dict) and isinstance(result.get("generation_mode_summary"), dict) else {}
    return {
        "profile": str(result_summary.get("profile") or mode_policy.get("profile") or (payload or {}).get("generation_mode") or "").strip() or None,
        "mode_effective": str(
            result_summary.get("mode_effective")
            or mode_policy.get("mode_effective")
            or (payload or {}).get("generation_mode")
            or ""
        ).strip()
        or None,
        "stable_output": bool(result_summary.get("stable_output", mode_policy.get("stable_output", False))),
        "deterministic_variant_forced": bool(
            result_summary.get("deterministic_variant_forced", mode_policy.get("deterministic_variant_forced", False))
        ),
        "deterministic_logic_template_id": str(
            result_summary.get("deterministic_logic_template_id")
            or mode_policy.get("deterministic_logic_template_id")
            or (payload or {}).get("logic_template_id")
            or ""
        ).strip()
        or None,
    }


def _recent_job_quality_overview(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    first = _recent_job_first_variant_summary(result.get("quality_by_variant"))
    if not first:
        return {}
    return {
        "logic_template_id": str(first.get("logic_template_id") or "").strip() or None,
        "logic_template_name": str(first.get("logic_template_name") or "").strip() or None,
        "quality_score": first.get("quality_score"),
        "quality_gate_ok": bool(first.get("quality_gate_ok", False)),
        "quality_gate_failed_count": int(first.get("quality_gate_failed_count") or 0),
    }


def _recent_job_agent_runtime_summary(agent_runtime: dict | None) -> dict[str, Any]:
    if not isinstance(agent_runtime, dict):
        return {}
    return {
        "requested_agent_parallelism": int(agent_runtime.get("requested_agent_parallelism") or 0),
        "agent_parallelism": int(agent_runtime.get("agent_parallelism") or 0),
        "variant_parallelism": int(agent_runtime.get("variant_parallelism") or 0),
        "planned_total_pages": int(agent_runtime.get("planned_total_pages") or 0),
        "outline_count": int(agent_runtime.get("outline_count") or 0),
        "runtime_agent_parallelism_reason": str(agent_runtime.get("runtime_agent_parallelism_reason") or "").strip(),
        "runtime_agent_parallelism_learning_applied": bool(agent_runtime.get("runtime_agent_parallelism_learning_applied", False)),
        "runtime_agent_parallelism_learning_reason": str(agent_runtime.get("runtime_agent_parallelism_learning_reason") or "").strip(),
        "runtime_agent_parallelism_learning_source_runs": int(agent_runtime.get("runtime_agent_parallelism_learning_source_runs") or 0),
    }


def _recent_job_sla_summary(sla: dict | None) -> dict[str, Any]:
    if not isinstance(sla, dict):
        return {}

    def _safe_non_negative_float(value: Any) -> float | None:
        try:
            out = float(value)
        except Exception:
            return None
        return out if out >= 0.0 else None

    total_seconds = _safe_non_negative_float(sla.get("total_seconds"))
    stages = sla.get("stages") if isinstance(sla.get("stages"), list) else []
    current_stage_name = ""
    current_stage_detail = ""
    current_stage_seconds = None
    current_stage_started_at = None
    dominant_stage_name = ""
    dominant_stage_seconds = None
    exporting_seconds = None
    variant_running_seconds = None
    for raw in reversed(stages):
        if not isinstance(raw, dict):
            continue
        current_stage_name = str(raw.get("name") or "").strip()
        current_stage_detail = str(raw.get("detail") or "").strip()
        current_stage_started_at = _safe_non_negative_float(raw.get("started_at"))
        current_stage_seconds = _safe_non_negative_float(raw.get("duration_sec"))
        ended_at = _safe_non_negative_float(raw.get("ended_at"))
        if current_stage_seconds is None and current_stage_started_at is not None and ended_at is None:
            current_stage_seconds = round(max(0.0, time.time() - current_stage_started_at), 3)
        if current_stage_name or current_stage_detail or current_stage_seconds is not None:
            break
    for raw in stages:
        if not isinstance(raw, dict):
            continue
        stage_name = str(raw.get("name") or "").strip()
        stage_seconds = _safe_non_negative_float(raw.get("duration_sec"))
        if stage_seconds is None:
            started_at = _safe_non_negative_float(raw.get("started_at"))
            ended_at = _safe_non_negative_float(raw.get("ended_at"))
            if started_at is not None and ended_at is None:
                stage_seconds = round(max(0.0, time.time() - started_at), 3)
        if stage_name == "exporting":
            exporting_seconds = stage_seconds
        if stage_name == "variant_running":
            variant_running_seconds = stage_seconds
        if stage_seconds is None:
            continue
        if dominant_stage_seconds is None or stage_seconds > dominant_stage_seconds:
            dominant_stage_name = stage_name
            dominant_stage_seconds = stage_seconds
    dominant_stage_share = None
    if total_seconds is not None and total_seconds > 0 and dominant_stage_seconds is not None:
        dominant_stage_share = round((dominant_stage_seconds / total_seconds) * 100.0, 1)
    exporting_share = None
    if total_seconds is not None and total_seconds > 0 and exporting_seconds is not None:
        exporting_share = round((exporting_seconds / total_seconds) * 100.0, 1)
    variant_running_share = None
    if total_seconds is not None and total_seconds > 0 and variant_running_seconds is not None:
        variant_running_share = round((variant_running_seconds / total_seconds) * 100.0, 1)
    return {
        "total_seconds": total_seconds,
        "current_stage": current_stage_name,
        "current_stage_detail": current_stage_detail,
        "current_stage_seconds": current_stage_seconds,
        "dominant_stage": dominant_stage_name,
        "dominant_stage_seconds": dominant_stage_seconds,
        "dominant_stage_share": dominant_stage_share,
        "exporting_seconds": exporting_seconds,
        "exporting_share": exporting_share,
        "variant_running_seconds": variant_running_seconds,
        "variant_running_share": variant_running_share,
    }


def _parse_recent_timestamp(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(time.mktime(time.strptime(text, "%Y-%m-%d %H:%M:%S")))
    except Exception:
        return 0.0


def _recent_signal_rank(kind: str, summary: str) -> int:
    skind = str(kind or "").strip().lower()
    stext = str(summary or "").strip().lower()
    if "error" in skind or "error" in stext or "failed" in stext:
        return 0
    if "restart" in skind or "restart" in stext or "throttled" in skind:
        return 1
    if skind in {"processing", "processed"}:
        return 2
    if "housekeep" in skind or "self_evolution" in skind:
        return 3
    if skind in {"exit_once", "missing_actions_key"}:
        return 4
    if skind in {"startup", "poll"}:
        return 5
    return 4


def _recent_summary_line(
    rows: list[dict[str, Any]],
    *,
    reference_timestamp: str = "",
    healthy: bool = False,
    recent_window_seconds: int = 1800,
    idle_fallback: str = "",
) -> str:
    if not rows:
        return ""
    ref_ts = _parse_recent_timestamp(reference_timestamp)
    filtered: list[dict[str, Any]] = []
    for item in rows:
        item_ts = _parse_recent_timestamp(item.get("timestamp") or "")
        if ref_ts > 0 and item_ts > 0:
            age_seconds = max(0.0, ref_ts - item_ts)
            if age_seconds > float(max(60, int(recent_window_seconds or 1800))):
                continue
        filtered.append(item)
    source = filtered
    if healthy:
        high_signal = [
            item
            for item in filtered
            if _recent_signal_rank(item.get("kind") or "", item.get("summary") or "") < 4
        ]
        if high_signal:
            source = high_signal
        elif idle_fallback:
            return idle_fallback
    elif not source:
        source = rows
    return "；".join(
        [
            str(item.get("summary") or "").strip()
            for item in source[:2]
            if str(item.get("summary") or "").strip()
        ]
    )


def _normalize_recent_rows(items: list[Any], *, limit: int = 6) -> list[dict[str, Any]]:
    rows = [
        {
            "timestamp": str(item.get("timestamp") or "").strip(),
            "kind": str(item.get("kind") or "").strip(),
            "summary": str(item.get("summary") or "").strip(),
        }
        for item in items[: max(1, int(limit or 6))]
        if isinstance(item, dict)
    ]
    rows.sort(
        key=lambda item: (
            _recent_signal_rank(item.get("kind") or "", item.get("summary") or ""),
            -_parse_recent_timestamp(item.get("timestamp") or ""),
        )
    )
    return rows


def _chief_agent_status_summary(state: dict | None, *, stale_seconds: int = 120) -> dict[str, Any]:
    if not isinstance(state, dict) or not state:
        return {}
    timestamp = str(state.get("timestamp") or "").strip()
    age_seconds = None
    try:
        if timestamp:
            age_seconds = max(0, int(time.time() - time.mktime(time.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))))
    except Exception:
        age_seconds = None
    backend_listener = int(state.get("backend_listener") or 0)
    web_listener = int(state.get("web_listener") or 0)
    backend_health = int(state.get("backend_health") or 0)
    web_health = int(state.get("web_health") or 0)
    maintenance = state.get("maintenance") if isinstance(state.get("maintenance"), dict) else {}
    job_housekeep = maintenance.get("job_housekeep") if isinstance(maintenance.get("job_housekeep"), dict) else {}
    self_evolution = maintenance.get("self_evolution") if isinstance(maintenance.get("self_evolution"), dict) else {}
    recent = state.get("recent") if isinstance(state.get("recent"), list) else []
    healthy = (
        backend_listener == 1
        and web_listener == 1
        and backend_health == 1
        and web_health == 1
        and (age_seconds is None or age_seconds <= max(30, int(stale_seconds or 120)))
    )
    job_changed = bool(job_housekeep.get("changed", False))
    runtime_changed = bool(((self_evolution.get("runtime_budget_profile") or {}).get("changed")))
    task_changed = bool(((self_evolution.get("task_parallelism_profile") or {}).get("changed")))
    recent_rows = _normalize_recent_rows(recent)
    recent_summary_line = _recent_summary_line(
        recent_rows,
        reference_timestamp=timestamp,
        healthy=bool(healthy),
        recent_window_seconds=max(600, int(stale_seconds or 120) * 6),
        idle_fallback="最近无异常动作",
    )
    return {
        "timestamp": timestamp,
        "age_seconds": age_seconds,
        "healthy": bool(healthy),
        "backend_listener": backend_listener,
        "web_listener": web_listener,
        "backend_health": backend_health,
        "web_health": web_health,
        "last_action": str(state.get("last_action") or "").strip(),
        "summary_line": (
            f"后端={'正常' if backend_listener == 1 and backend_health == 1 else '异常'}；"
            f"前端={'正常' if web_listener == 1 and web_health == 1 else '异常'}；"
            f"job housekeep={'有变更' if job_changed else '无变更'}；"
            f"self-evolution={'有变更' if (runtime_changed or task_changed) else '无变更'}"
        ),
        "recent_summary_line": recent_summary_line,
        "job_housekeep": {
            "changed": job_changed,
            "stale_fixed": int(job_housekeep.get("stale_fixed") or 0),
            "removed": int(job_housekeep.get("removed") or 0),
            "lease_seconds": int(job_housekeep.get("lease_seconds") or 0),
            "retention_seconds": int(job_housekeep.get("retention_seconds") or 0),
        },
        "self_evolution": {
            "enabled": bool(self_evolution.get("enabled", False)),
            "runtime_changed": runtime_changed,
            "runtime_entry_count": int(((self_evolution.get("runtime_budget_profile") or {}).get("entry_count")) or 0),
            "task_changed": task_changed,
            "task_entry_count": int(((self_evolution.get("task_parallelism_profile") or {}).get("entry_count")) or 0),
        },
        "recent": recent_rows,
    }


def _load_watcher_state() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[3] / ".runtime" / "docgen" / "watcher_state.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _watcher_status_summary(state: dict | None, *, stale_seconds: int = 180) -> dict[str, Any]:
    if not isinstance(state, dict) or not state:
        return {}
    timestamp = str(state.get("timestamp") or "").strip()
    age_seconds = None
    try:
        if timestamp:
            age_seconds = max(0, int(time.time() - time.mktime(time.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))))
    except Exception:
        age_seconds = None
    status = str(state.get("status") or "").strip() or "unknown"
    recent = state.get("recent") if isinstance(state.get("recent"), list) else []
    healthy = status != "error" and (age_seconds is None or age_seconds <= max(60, int(stale_seconds or 180)))
    recent_rows = _normalize_recent_rows(recent)
    recent_summary_line = _recent_summary_line(
        recent_rows,
        reference_timestamp=timestamp,
        healthy=bool(healthy),
        recent_window_seconds=max(900, int(stale_seconds or 180) * 6),
        idle_fallback="最近无项目动作" if status in {"idle", "unknown"} else "",
    )
    return {
        "timestamp": timestamp,
        "age_seconds": age_seconds,
        "healthy": bool(healthy),
        "status": status,
        "watch_root": str(state.get("watch_root") or "").strip(),
        "last_action": str(state.get("last_action") or "").strip(),
        "summary_line": (
            f"watcher={'正常' if healthy else '异常'}；"
            f"status={status}；"
            f"inbox={int(state.get('inbox_count') or 0)} / work={int(state.get('work_count') or 0)} / "
            f"done={int(state.get('done_count') or 0)} / failed={int(state.get('failed_count') or 0)}"
        ),
        "recent_summary_line": recent_summary_line,
        "last_project_id": str(state.get("last_project_id") or "").strip(),
        "last_project_name": str(state.get("last_project_name") or "").strip(),
        "last_error": str(state.get("last_error") or "").strip(),
        "inbox_count": int(state.get("inbox_count") or 0),
        "work_count": int(state.get("work_count") or 0),
        "done_count": int(state.get("done_count") or 0),
        "failed_count": int(state.get("failed_count") or 0),
        "recent": recent_rows,
    }


def _recent_job_runtime_budget_summary(result: dict | None) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        return []
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        return []
    variants = data.get("variants") if isinstance(data, dict) else []
    if not isinstance(variants, list) or not variants:
        return []
    first = variants[0] if isinstance(variants[0], dict) else {}
    if not isinstance(first, dict):
        return []
    rows: list[dict[str, Any]] = []
    for sec in (first.get("sections") or [])[:3]:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip()
        if not title:
            continue
        rows.append(
            {
                "title": title,
                "requested_timeout_sec": sec.get("requested_timeout_sec"),
                "requested_max_output_tokens": sec.get("requested_max_output_tokens"),
                "requested_section_retry_limit": sec.get("requested_section_retry_limit"),
                "runtime_budget_reason": str(sec.get("runtime_budget_reason") or "").strip(),
                "evolution_applied": bool(sec.get("evolution_applied", False)),
                "evolution_reason": str(sec.get("evolution_reason") or "").strip(),
                "evolution_source_runs": int(sec.get("evolution_source_runs") or 0),
                "used_key_alias": str(sec.get("used_key_alias") or "").strip(),
            }
        )
    return rows


def _recent_job_remediation_strategy_summary(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        return {}
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    variants = data.get("variants") if isinstance(data, dict) else []
    if not isinstance(variants, list) or not variants:
        return {}
    first = variants[0] if isinstance(variants[0], dict) else {}
    if not isinstance(first, dict):
        return {}
    quality_checks = first.get("quality_checks") if isinstance(first.get("quality_checks"), dict) else {}
    audit = quality_checks.get("remediation_strategy_audit") if isinstance(quality_checks.get("remediation_strategy_audit"), dict) else {}
    if not audit:
        return {}
    indicator_groups = audit.get("indicator_groups") if isinstance(audit.get("indicator_groups"), list) else []
    strategies = audit.get("strategies") if isinstance(audit.get("strategies"), list) else []
    by_title = audit.get("by_title") if isinstance(audit.get("by_title"), list) else []
    return {
        "issue_count": int(audit.get("issue_count") or 0),
        "remediation_count": int(audit.get("remediation_count") or 0),
        "indicator_groups": indicator_groups[:3],
        "strategies": strategies[:3],
        "by_title": by_title[:2],
    }


def _recent_job_remediation_execution_summary(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        return {}
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    variants = data.get("variants") if isinstance(data, dict) else []
    if not isinstance(variants, list) or not variants:
        return {}
    first = variants[0] if isinstance(variants[0], dict) else {}
    if not isinstance(first, dict):
        return {}
    quality_checks = first.get("quality_checks") if isinstance(first.get("quality_checks"), dict) else {}
    audit = quality_checks.get("remediation_execution_audit") if isinstance(quality_checks.get("remediation_execution_audit"), dict) else {}
    if not audit:
        return {}
    action_tags = audit.get("action_tags") if isinstance(audit.get("action_tags"), list) else []
    strategies = audit.get("strategies") if isinstance(audit.get("strategies"), list) else []
    status_counts = audit.get("status_counts") if isinstance(audit.get("status_counts"), list) else []
    by_title = audit.get("by_title") if isinstance(audit.get("by_title"), list) else []
    return {
        "trace_count": int(audit.get("trace_count") or 0),
        "action_tags": action_tags[:4],
        "strategies": strategies[:3],
        "status_counts": status_counts[:3],
        "by_title": by_title[:2],
    }


def _recent_job_remediation_learning_summary(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        return {}
    try:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    variants = data.get("variants") if isinstance(data, dict) else []
    if not isinstance(variants, list) or not variants:
        return {}
    first = variants[0] if isinstance(variants[0], dict) else {}
    if not isinstance(first, dict):
        return {}
    generation_trace = first.get("generation_trace") if isinstance(first.get("generation_trace"), dict) else {}
    self_evolution = generation_trace.get("self_evolution") if isinstance(generation_trace.get("self_evolution"), dict) else {}
    applied_count = int(self_evolution.get("remediation_combo_learning_applied_count") or 0)
    bundle_applied_count = int(self_evolution.get("remediation_combo_bundle_learning_applied_count") or 0)
    context_bundle_applied_count = int(self_evolution.get("remediation_context_bundle_learning_applied_count") or 0)
    metric_effect_applied_count = int(self_evolution.get("remediation_context_bundle_learning_metric_effect_applied_count") or 0)
    metric_action_effect_applied_count = int(self_evolution.get("remediation_context_bundle_learning_metric_action_effect_applied_count") or 0)
    if (
        applied_count <= 0
        and bundle_applied_count <= 0
        and context_bundle_applied_count <= 0
        and metric_effect_applied_count <= 0
        and metric_action_effect_applied_count <= 0
    ):
        return {}
    chapter_effect_summary = build_chapter_effect_summary(self_evolution, limit=3)
    if not chapter_effect_summary:
        fallback_titles = [
            str(x).strip()
            for x in (
                self_evolution.get("remediation_context_bundle_learning_metric_action_effect_titles")
                if isinstance(self_evolution.get("remediation_context_bundle_learning_metric_action_effect_titles"), list)
                else self_evolution.get("remediation_context_bundle_learning_metric_effect_titles")
            )
            or []
            if str(x).strip()
        ]
        fallback_metrics = [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_effect_metrics") or [])
            if str(x).strip()
        ]
        fallback_triplets = [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_action_effect_triplets") or [])
            if str(x).strip()
        ]
        fallback_bundles = [
            str(x).strip()
            for x in (
                self_evolution.get("remediation_context_bundle_learning_metric_action_effect_bundles")
                or self_evolution.get("remediation_context_bundle_learning_metric_effect_bundles")
                or []
            )
            if str(x).strip()
        ]
        fallback_reasons = [
            str(x).strip()
            for x in (
                self_evolution.get("remediation_context_bundle_learning_metric_action_effect_reasons")
                or self_evolution.get("remediation_context_bundle_learning_metric_effect_reasons")
                or []
            )
            if str(x).strip()
        ]
        for title in fallback_titles[:3]:
            chapter_effect_summary.append(
                {
                    "title": title,
                    "resolved_metric_count": len(fallback_metrics),
                    "resolved_metrics": fallback_metrics[:4],
                    "resolved_action_count": len(fallback_triplets),
                    "resolved_action_triplets": fallback_triplets[:6],
                    "bundles": fallback_bundles[:2],
                    "reasons": fallback_reasons[:3],
                    "source_runs": int(
                        self_evolution.get("remediation_context_bundle_learning_metric_action_effect_source_runs")
                        or self_evolution.get("remediation_context_bundle_learning_metric_effect_source_runs")
                        or 0
                    ),
                    "attribution_runs": int(
                        self_evolution.get("remediation_context_bundle_learning_metric_action_effect_source_runs")
                        or self_evolution.get("remediation_context_bundle_learning_metric_effect_source_runs")
                        or 0
                    ),
                }
            )
    return {
        "applied_count": applied_count,
        "source_runs": max(
            int(self_evolution.get("remediation_combo_learning_source_runs") or 0),
            int(self_evolution.get("remediation_combo_bundle_learning_source_runs") or 0),
            int(self_evolution.get("remediation_context_bundle_learning_source_runs") or 0),
            int(self_evolution.get("remediation_context_bundle_learning_metric_action_effect_source_runs") or 0),
        ),
        "titles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_combo_learning_titles") or [])
            if str(x).strip()
        ][:4],
        "reasons": [
            str(x).strip()
            for x in (self_evolution.get("remediation_combo_learning_reasons") or [])
            if str(x).strip()
        ][:4],
        "combos": [
            str(x).strip()
            for x in (self_evolution.get("remediation_combo_learning_combos") or [])
            if str(x).strip()
        ][:4],
        "bundle_applied_count": bundle_applied_count,
        "bundle_source_runs": int(self_evolution.get("remediation_combo_bundle_learning_source_runs") or 0),
        "bundle_titles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_combo_bundle_learning_titles") or [])
            if str(x).strip()
        ][:4],
        "bundle_reasons": [
            str(x).strip()
            for x in (self_evolution.get("remediation_combo_bundle_learning_reasons") or [])
            if str(x).strip()
        ][:4],
        "bundles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_combo_bundle_learning_bundles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_applied_count": context_bundle_applied_count,
        "context_bundle_source_runs": int(self_evolution.get("remediation_context_bundle_learning_source_runs") or 0),
        "context_bundle_titles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_titles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_contexts": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_contexts") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_reasons": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_reasons") or [])
            if str(x).strip()
        ][:4],
        "context_bundles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_bundles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_effect_applied_count": int(self_evolution.get("remediation_context_bundle_learning_effect_applied_count") or 0),
        "context_bundle_effect_source_runs": int(self_evolution.get("remediation_context_bundle_learning_effect_source_runs") or 0),
        "context_bundle_effect_titles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_effect_titles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_effect_reasons": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_effect_reasons") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_effect_bundles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_effect_bundles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_metric_effect_applied_count": metric_effect_applied_count,
        "context_bundle_metric_effect_source_runs": int(self_evolution.get("remediation_context_bundle_learning_metric_effect_source_runs") or 0),
        "context_bundle_metric_effect_titles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_effect_titles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_metric_effect_metrics": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_effect_metrics") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_metric_effect_reasons": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_effect_reasons") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_metric_effect_bundles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_effect_bundles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_metric_action_effect_applied_count": metric_action_effect_applied_count,
        "context_bundle_metric_action_effect_source_runs": int(self_evolution.get("remediation_context_bundle_learning_metric_action_effect_source_runs") or 0),
        "context_bundle_metric_action_effect_titles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_action_effect_titles") or [])
            if str(x).strip()
        ][:4],
        "context_bundle_metric_action_effect_triplets": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_action_effect_triplets") or [])
            if str(x).strip()
        ][:6],
        "context_bundle_metric_action_effect_reasons": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_action_effect_reasons") or [])
            if str(x).strip()
        ][:6],
        "context_bundle_metric_action_effect_bundles": [
            str(x).strip()
            for x in (self_evolution.get("remediation_context_bundle_learning_metric_action_effect_bundles") or [])
            if str(x).strip()
        ][:4],
        "chapter_effect_summary": chapter_effect_summary,
    }


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


def _pct(values: List[float], q: float) -> float | None:
    arr = [float(x) for x in values if float(x) >= 0.0]
    if not arr:
        return None
    arr.sort()
    if len(arr) == 1:
        return float(arr[0])
    pos = max(0.0, min(1.0, float(q))) * (len(arr) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(arr) - 1)
    if lo == hi:
        return float(arr[lo])
    w = pos - lo
    return float(arr[lo] * (1.0 - w) + arr[hi] * w)


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
    return [dict(item) for item in _GENERATION_MODE_CATALOG]


def _normalize_generation_mode_profile(raw: str | None) -> tuple[str, str | None]:
    mode = str(raw or "").strip()
    for item in _GENERATION_MODE_CATALOG:
        if mode != item["id"]:
            continue
        profile = str(item.get("profile") or "standard_auto").strip() or "standard_auto"
        if bool(item.get("legacy")):
            return profile, str(item["id"])
        return profile, None
    return "standard_auto", None


def _apply_generation_mode_policy(payload: dict) -> dict:
    mode_profile, legacy_mode = _normalize_generation_mode_profile(payload.get("generation_mode"))
    pages = _planned_total_pages(payload)
    existing_mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    auto_switched = False
    if legacy_mode == "hq_speed_500":
        mode_effective = "hq_speed_500"
    elif legacy_mode == "quality_200":
        mode_effective = "hq_speed_500" if pages > 200 else "quality_200"
        auto_switched = pages > 200
    elif mode_profile == "speed_fast":
        mode_effective = "speed_fast"
    elif mode_profile == "stable_delivery":
        mode_effective = "stable_delivery"
    elif mode_profile == "pro_polish":
        mode_effective = "pro_polish"
    else:
        mode_effective = "hq_speed_500" if pages > 200 else "quality_200"
        auto_switched = pages > 200

    explicit_template_id = _normalize_logic_template_id(payload.get("logic_template_id") or payload.get("logic_template"))
    explicit_selected_templates = _normalize_selected_templates(payload.get("selected_templates"))
    explicit_variant_id = _to_positive_int(payload.get("variant_id"))
    try:
        variants_requested = int(payload.get("variants") or 1)
    except Exception:
        variants_requested = 1
    variants_requested = max(1, min(5, variants_requested))
    stable_variant_forced = bool(existing_mode_policy.get("deterministic_variant_forced", False))
    deterministic_logic_template_id = str(
        existing_mode_policy.get("deterministic_logic_template_id")
        or payload.get("logic_template_id")
        or ""
    ).strip() or None
    if (
        mode_profile == "stable_delivery"
        and not explicit_template_id
        and not explicit_selected_templates
        and not explicit_variant_id
        and variants_requested == 1
    ):
        payload["variant_id"] = 1
        payload["logic_template_id"] = "A"
        stable_variant_forced = True

    if mode_effective == "quality_200":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 1
        if str(payload.get("remediate_mode") or "").strip() not in {"template", "llm"}:
            payload["remediate_mode"] = "template"
        ap = _to_positive_int(payload.get("agent_parallelism")) or 4
        payload["agent_parallelism"] = max(1, min(16, int(ap)))
    elif mode_effective == "hq_speed_500":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["remediate_mode"] = "template"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 1
        ap = _to_positive_int(payload.get("agent_parallelism")) or 6
        payload["agent_parallelism"] = max(6, min(16, int(ap)))
        vp = _to_positive_int(payload.get("variant_parallelism")) or 1
        payload["variant_parallelism"] = max(1, min(5, int(vp)))
        if payload.get("generate_images") is None:
            payload["generate_images"] = False
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 800
    elif mode_effective == "speed_fast":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["remediate_mode"] = "template"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 0
        ap = _to_positive_int(payload.get("agent_parallelism")) or 8
        payload["agent_parallelism"] = max(8, min(16, int(ap)))
        vp = _to_positive_int(payload.get("variant_parallelism")) or 1
        payload["variant_parallelism"] = max(1, min(5, int(vp)))
        if payload.get("generate_images") is None:
            payload["generate_images"] = False
        else:
            payload["generate_images"] = False
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 600
    elif mode_effective == "stable_delivery":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 1
        if str(payload.get("remediate_mode") or "").strip() not in {"template", "llm"}:
            payload["remediate_mode"] = "template"
        else:
            payload["remediate_mode"] = "template"
        ap = _to_positive_int(payload.get("agent_parallelism")) or 2
        payload["agent_parallelism"] = max(1, min(3, int(ap)))
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 1600
    else:
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        payload["remediate_mode"] = "llm"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 2
        ap = _to_positive_int(payload.get("agent_parallelism")) or 3
        payload["agent_parallelism"] = max(1, min(4, int(ap)))
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 1600

    # Image strategy tiers:
    # - quality_200/pro_polish: keep full auto density
    # - hq_speed_500/speed_fast: keep auto density but add a sensible default total-image budget for speed stability
    style = payload.get("style") if isinstance(payload.get("style"), dict) else {}
    chart_policy = style.get("chart_policy") if isinstance(style.get("chart_policy"), dict) else {}
    if mode_effective in {"quality_200", "pro_polish", "stable_delivery"}:
        chart_policy.setdefault("enabled", True)
        chart_policy.setdefault("mode", "page_density_auto")
        chart_policy.setdefault("position", "chapter")
    elif mode_effective in {"hq_speed_500", "speed_fast"}:
        chart_policy.setdefault("enabled", True)
        chart_policy.setdefault("mode", "page_density_auto")
        chart_policy.setdefault("position", "chapter")
        if "max_images_total" not in chart_policy:
            # Tuned for large-volume generation: keeps visual density while bounding export time.
            chart_policy["max_images_total"] = max(240, min(900, pages))
    if chart_policy:
        style["chart_policy"] = chart_policy
        payload["style"] = style

    degrade_plan = payload.get("_admission_degrade_plan") if isinstance(payload.get("_admission_degrade_plan"), dict) else {}
    if degrade_plan.get("applied"):
        degraded_ap = _to_positive_int(degrade_plan.get("agent_parallelism_after"))
        degraded_vp = _to_positive_int(degrade_plan.get("variant_parallelism_after"))
        if degraded_ap:
            payload["agent_parallelism"] = max(1, min(16, int(degraded_ap)))
        if degraded_vp:
            payload["variant_parallelism"] = max(1, min(5, int(degraded_vp)))

    payload["generation_mode"] = str(mode_effective if legacy_mode else mode_profile)
    payload["_mode_policy"] = {
        "profile": mode_profile,
        "mode_effective": mode_effective,
        "auto_switched": bool(auto_switched),
        "planned_total_pages": int(pages),
        "stable_output": mode_profile == "stable_delivery",
    }
    if stable_variant_forced:
        payload["_mode_policy"]["deterministic_variant_forced"] = True
        payload["_mode_policy"]["deterministic_logic_template_id"] = deterministic_logic_template_id or "A"
    if degrade_plan.get("applied"):
        payload["_mode_policy"]["admission_degrade_applied"] = True
        payload["_mode_policy"]["admission_degrade_reason"] = str(degrade_plan.get("reason") or "").strip()
        payload["_mode_policy"]["admission_degrade_warning_level"] = str(degrade_plan.get("warning_level") or "").strip()
    return payload


def _merge_plan_defaults(payload: dict) -> dict:
    pid = str(payload.get("project_id") or "").strip() or None
    workspace_dir = _workspace_dir_from_payload(payload)
    plan = load_plan(project_id=pid, workspace_dir=workspace_dir)
    if not isinstance(plan, dict):
        plan = {}
    tender = load_tender_matrix(project_id=pid, workspace_dir=workspace_dir) or {}
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
    if payload.get("front_matter_outline") is None:
        payload["front_matter_outline"] = plan.get("front_matter_outline") or {}
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
        plan_compare_max_chars = plan.get("compare_max_chars")
        if plan_compare_max_chars is not None:
            payload["compare_max_chars"] = plan_compare_max_chars
    if payload.get("compare_titles") is None:
        payload["compare_titles"] = plan.get("compare_titles")
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


def _prepare_runtime_payload(payload: dict) -> dict:
    workspace = _resolve_workspace_context(
        session_id=str(payload.get("session_id") or "").strip() or None,
        workspace_dir=str(payload.get("workspace_dir") or "").strip() or None,
    )
    payload["session_id"] = workspace["session_id"]
    payload["workspace_dir"] = workspace["workspace_dir"]
    prepared = apply_server_provider_routing(_merge_plan_defaults(payload))
    trace_id = str(prepared.get("trace_id") or prepared.get("request_id") or "").strip() or uuid.uuid4().hex
    prepared["request_id"] = trace_id
    prepared["trace_id"] = trace_id
    return prepared


def _save_outputs(base_name: str, results: list[dict], *, workspace_dir: str | None = None) -> dict:
    build_dir = workspace_paths(workspace_dir)["build"] if workspace_dir else Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    out_json = build_dir / f"{base_name}.json"
    out_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    docx_files = []
    compare_files = []
    focus_xlsx_files = []
    score_overview_xlsx_files = []
    expert_review_docx_files = []
    for i, variant in enumerate(results):
        if isinstance(variant, dict) and workspace_dir and not str(variant.get("workspace_dir") or "").strip():
            variant["workspace_dir"] = workspace_dir
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
        out_overview = build_dir / f"{base_name}_评分点覆盖与证据引用总览_v{i + 1}.xlsx"
        try:
            from backend.zhifei_autoplan.exporter import export_scoring_evidence_overview_xlsx

            overview_path = export_scoring_evidence_overview_xlsx(variant, str(out_overview))
        except Exception:
            overview_path = ""
        score_overview_xlsx_files.append(str(overview_path) if overview_path else None)

        out_review = build_dir / f"{base_name}_专家复核提要版_v{i + 1}.docx"
        try:
            from backend.zhifei_autoplan.exporter import export_expert_review_brief_docx

            review_path = export_expert_review_brief_docx(variant, str(out_review))
        except Exception:
            review_path = ""
        expert_review_docx_files.append(str(review_path) if review_path else None)
    return {
        "json": str(out_json),
        "docx": docx_files,
        "compare_docx": compare_files,
        "focus_xlsx": focus_xlsx_files,
        "score_overview_xlsx": score_overview_xlsx_files,
        "expert_review_docx": expert_review_docx_files,
    }


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
    workspace_dir = _workspace_dir_from_payload(payload)

    # Load latest tender/boq for this project scope (best-effort).
    tender = load_tender_matrix(project_id=pid, workspace_dir=workspace_dir) or {}
    boq = load_boq_data(project_id=pid, workspace_dir=workspace_dir) or {}
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
            saved_at = save_latest_receipt(
                receipt,
                project_id=str(pid) if pid else None,
                workspace_dir=workspace_dir,
            )
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
            workspace_dir=workspace_dir,
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


def _load_done_job_variants(job_id: str, *, workspace_dir: str | None = None) -> tuple[dict, dict, dict, list]:
    job = get_job(job_id, workspace_dir=workspace_dir)
    if not job:
        _raise_actions_http_error(
            404,
            "job_not_found",
            "job not found",
            stage="load_done_job",
            job_id=job_id,
            next_action="check job_id or workspace scope",
        )
    trace_meta = _job_trace_meta(job)
    if str(job.get("status") or "").strip() != "done":
        _raise_actions_http_error(
            409,
            "job_not_done",
            f"job not done: {job.get('status')}",
            stage="load_done_job",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="poll /actions/job_status until status=done",
            extra={"status": str(job.get("status") or "")},
        )
    result = job.get("result") or {}
    json_path = str(result.get("json") or "").strip()
    if not json_path or not Path(json_path).exists():
        _raise_actions_http_error(
            404,
            "result_json_not_found",
            "result json not found",
            stage="load_done_job",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="check worker log and result artifact output",
            extra={"json_path": json_path},
        )
    data = json.loads(Path(json_path).read_text(encoding="utf-8", errors="ignore"))
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []
    if not variants:
        _raise_actions_http_error(
            404,
            "empty_result_variants",
            "empty result variants",
            stage="load_done_job",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="check result json content",
            extra={"json_path": json_path},
        )
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
    pid = str(req.project_id or "").strip() or None
    tender = load_tender_matrix(project_id=pid, workspace_dir=workspace["workspace_dir"]) or {}
    boq = load_boq_data(project_id=pid, workspace_dir=workspace["workspace_dir"]) or {}
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
        workspace_dir=workspace["workspace_dir"],
    )
    # Drawing/standard index + cross-index for reviewer XLSX (best-effort).
    drawing_index = None
    standard_index = None
    cross_index = None
    try:
        from backend.zhifei_autoplan.drawing_index import build_drawing_index
        from backend.zhifei_autoplan.standard_index import build_standard_index
        from backend.zhifei_autoplan.cross_index import build_cross_index

        drawing_index = build_drawing_index(
            req.topic,
            outline,
            project_id=pid,
            workspace_dir=workspace["workspace_dir"],
        )
        standard_index = build_standard_index(
            req.topic,
            outline,
            project_id=pid,
            workspace_dir=workspace["workspace_dir"],
        )
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
        "project_id": pid,
        "project_name": str(tender.get("project_name") or "").strip() if isinstance(tender, dict) else "",
        "project_code": str(tender.get("project_code") or "").strip() if isinstance(tender, dict) else "",
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
    if pid or req.bidder_company or req.logo_url or req.bidder_domain:
        payload["branding"] = {
            "project_id": pid,
            "bidder_company": req.bidder_company,
            "bidder_domain": req.bidder_domain,
            "logo_url": req.logo_url,
        }
    try:
        payload["evidence_tracking"] = build_evidence_tracking(
            sections=sections,
            tender=tender,
            chapter_pages={},
        )
    except Exception:
        payload["evidence_tracking"] = {"rows": [], "summary": {}}
    if bool(req.generate_images):
        stats = boq.get("stats") if isinstance(boq, dict) else None
        media = []
        if stats:
            media.extend(generate_boq_chart(stats))
        media.extend(generate_ingested_previews(limit=6, project_id=pid, workspace_dir=workspace["workspace_dir"]))
        # Mindmap (prefer Gemini "banana" image model when key is configured)
        try:
            img_defaults = get_image_defaults(params)
            aspect_ratio = (req.image_aspect_ratio or img_defaults.get("aspect_ratio") or "16:9").strip()
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
                        workspace_dir=workspace["workspace_dir"],
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
                            workspace_dir=workspace["workspace_dir"],
                        )
                except Exception:
                    pass
            mm = None
            for image_slot in iterate_image_failover_slots():
                if image_slot.provider != "google":
                    continue
                mm = generate_outline_mindmap(
                    req.topic,
                    outline,
                    api_key=image_slot.api_key,
                    model=image_slot.model,
                    aspect_ratio=aspect_ratio,
                    logo_path=logo_embed,
                    bidder_company=req.bidder_company,
                    logo_url=req.logo_url,
                    bidder_domain=req.bidder_domain,
                    workspace_dir=workspace["workspace_dir"],
                )
                if mm:
                    media.append(mm)
                    break
        except Exception:
            pass
        if media:
            payload["media"] = media
    job_id = create_job({"action": "export_docx", "workspace_dir": workspace["workspace_dir"]}, user_id=None, workspace_dir=workspace["workspace_dir"])
    outputs = _save_outputs(f"actions_export_{job_id}", [payload], workspace_dir=workspace["workspace_dir"])
    update_job(job_id, status="done", result=outputs, workspace_dir=workspace["workspace_dir"])
    return {"ok": True, "job_id": job_id, "files": outputs}


@router.post("/generate")
async def actions_generate(
    req: ActionsGenerateRequest,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    x_actions_key: str | None = Header(default=None),
):
    _auth_actions_key(x_actions_key)
    payload = _prepare_runtime_payload({**req.model_dump(), "session_id": session_id, "workspace_dir": workspace_dir})
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

            _rebuild_postprocessed_artifacts(
                results,
                payload=payload,
                report=report,
                params=params,
                workspace_dir=_workspace_dir_from_payload(payload),
            )
        except Exception:
            pass
    outputs = _save_outputs("actions_generated", results, workspace_dir=_workspace_dir_from_payload(payload))
    quality = [v.get("quality_checks") for v in results]
    return {"ok": True, "result": results, "quality": quality, "files": outputs}


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
        payload = _prepare_runtime_payload(
            {**req.model_dump(), "session_id": workspace["session_id"], "workspace_dir": workspace["workspace_dir"]}
        )
    except RuntimeError as e:
        raw = str(e or "").strip()
        if raw.startswith("text_provider_not_configured"):
            _raise_actions_http_error(
                503,
                "provider_not_configured",
                "text provider not configured",
                stage="payload_prepare",
                next_action="configure text provider env keys or use dry_run=true",
                extra={"reason": raw},
            )
        _raise_actions_http_error(
            500,
            "payload_prepare_failed",
            "failed to prepare runtime payload",
            stage="payload_prepare",
            next_action="check server logs for payload preparation failure",
            extra={"reason": raw},
            exc=e,
        )
    except Exception as e:
        _raise_actions_http_error(
            500,
            "payload_prepare_failed",
            "failed to prepare runtime payload",
            stage="payload_prepare",
            next_action="check server logs for payload preparation failure",
            exc=e,
        )
    request_signature = compute_job_signature(payload)
    reusable = find_reusable_job(
        request_signature,
        max_age_seconds=12 * 3600,
        workspace_dir=workspace["workspace_dir"],
    )
    if reusable:
        reusable_admission = evaluate_job_admission(
            scope="session",
            tenant_id=workspace["session_id"],
            workspace_dir=workspace["workspace_dir"],
            requested_jobs=0,
        )
        return {
            "ok": True,
            "job_id": reusable.get("job_id"),
            "status": reusable.get("status"),
            "reused": True,
            "reuse_reason": "same_payload",
            "admission": admission_http_detail(reusable_admission),
            "request_id": (reusable.get("payload") or {}).get("request_id") if isinstance(reusable.get("payload"), dict) else None,
            "trace_id": (reusable.get("payload") or {}).get("trace_id") if isinstance(reusable.get("payload"), dict) else None,
        }
    admission = evaluate_job_admission(
        scope="session",
        tenant_id=workspace["session_id"],
        workspace_dir=workspace["workspace_dir"],
        requested_jobs=1,
    )
    if not admission.get("allowed", False):
        append_resource_event(
            "job_rejected",
            workspace_dir=workspace["workspace_dir"],
            session_id=workspace["session_id"],
            user_id=None,
            request_signature=request_signature,
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
            project_id=payload.get("project_id"),
            topic=payload.get("topic"),
            variants=int(payload.get("variants") or 1),
            rejection_code=admission.get("code"),
            rejection_scope=admission.get("scope"),
            next_action=admission.get("next_action"),
            usage=admission.get("usage"),
            limits=admission.get("limits"),
        )
        rejected = dict(admission_http_detail(admission))
        rejected["ok"] = False
        rejected["message"] = "job admission rejected"
        rejected["stage"] = "admission"
        rejected["log_anchor"] = _new_log_anchor("admission")
        rejected["request_id"] = payload.get("request_id")
        rejected["trace_id"] = payload.get("trace_id")
        logger.warning("%s code=%s status=%s detail=%s", rejected["log_anchor"], rejected.get("code"), 429, rejected)
        raise HTTPException(status_code=429, detail=rejected)
    degrade_plan = apply_admission_degrade(payload, admission)
    if degrade_plan:
        admission["degrade_plan"] = degrade_plan
    variant_plan = _build_variant_plan(payload)
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(v.get("variant_id") or 1) for v in variant_plan]
    payload["variants"] = len(variant_plan) if variant_plan else int(payload.get("variants") or 1)
    job_id = create_job(
        payload,
        user_id=None,
        request_signature=request_signature,
        workspace_dir=workspace["workspace_dir"],
    )
    append_resource_event(
        "job_queued",
        workspace_dir=workspace["workspace_dir"],
        session_id=workspace["session_id"],
        user_id=None,
        job_id=job_id,
        request_signature=request_signature,
        request_id=payload.get("request_id"),
        trace_id=payload.get("trace_id"),
        project_id=payload.get("project_id"),
        topic=payload.get("topic"),
        variants=int(payload.get("variants") or 1),
        warning_level=admission.get("warning_level"),
        warning_codes=[item.get("code") for item in admission.get("warnings") or [] if isinstance(item, dict) and item.get("code")],
        degrade_plan=degrade_plan or None,
    )
    try:
        worker_pid, worker_log_path = _spawn_generate_worker(job_id, workspace_dir=workspace["workspace_dir"])
        update_job(
            job_id,
            workspace_dir=workspace["workspace_dir"],
            worker={
                "mode": "subprocess",
                "pid": int(worker_pid),
                "log_path": str(worker_log_path),
                "alive": True,
            },
            progress={"percent": 0, "stage": "queued", "detail": "任务已入队，等待Worker执行"},
        )
    except Exception as e:
        try:
            _append_worker_log(job_id, f"worker_spawn_failed error={e!r}", workspace_dir=workspace["workspace_dir"])
        except Exception:
            pass
        update_job(
            job_id,
            workspace_dir=workspace["workspace_dir"],
            status="failed",
            error=f"worker_spawn_failed: {e!r}",
            progress={"percent": 100, "stage": "failed", "detail": f"worker_spawn_failed: {e!r}"},
        )
        _raise_actions_http_error(
            500,
            "worker_spawn_failed",
            "worker spawn failed",
            stage="worker_spawn",
            job_id=job_id,
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
            next_action="check worker log and subprocess spawn permissions",
            extra={"worker_log_path": str(worker_log_path) if 'worker_log_path' in locals() else ""},
            exc=e,
        )
    return {
        "ok": True,
        "job_id": job_id,
        "status": "queued",
        "workspace_dir": workspace["workspace_dir"],
        "session_id": workspace["session_id"],
        "admission": admission_http_detail(admission),
        "request_id": payload.get("request_id"),
        "trace_id": payload.get("trace_id"),
    }


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
    return {"ok": True, "admission": admission_http_detail(decision)}


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
    usage = decision.get("usage") if isinstance(decision.get("usage"), dict) else {}
    return {
        "ok": True,
        "scope": "session",
        "session_id": workspace["session_id"],
        "workspace_dir": workspace["workspace_dir"],
        "usage_profile": usage.get("usage_profile") if isinstance(usage.get("usage_profile"), dict) else {},
        "limits": dict(decision.get("limits") or {}),
        "warning_level": str(decision.get("warning_level") or "none"),
        "warnings": list(decision.get("warnings") or []),
    }


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
    status = str(job.get("status") or "").strip().lower()
    if status in {"done", "failed", "cancelled"}:
        return {"ok": True, "job_id": job_id, "status": status}
    worker = job.get("worker") if isinstance(job.get("worker"), dict) else {}
    pid = worker.get("pid")
    try:
        if pid:
            os.kill(int(pid), 15)
    except Exception:
        pass
    update_job(job_id, workspace_dir=workspace["workspace_dir"], status="cancelled", error="cancelled_by_user")
    return {"ok": True, "job_id": job_id, "status": "cancelled"}


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
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    out = {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "error": job.get("error"),
        "request_id": trace_meta.get("request_id") or None,
        "trace_id": trace_meta.get("trace_id") or None,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "heartbeat_at": job.get("heartbeat_at"),
        "stage_artifacts_dir": job.get("stage_artifacts_dir"),
        "progress": job.get("progress") if isinstance(job.get("progress"), dict) else {},
        "agent_runtime": job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {},
        "worker": job.get("worker") if isinstance(job.get("worker"), dict) else {},
        "sla": job.get("sla") if isinstance(job.get("sla"), dict) else {},
        "generation_mode_summary": {
            "profile": str(mode_policy.get("profile") or payload.get("generation_mode") or "").strip() or None,
            "mode_effective": str(mode_policy.get("mode_effective") or payload.get("generation_mode") or "").strip() or None,
            "stable_output": bool(mode_policy.get("stable_output", False)),
            "deterministic_variant_forced": bool(mode_policy.get("deterministic_variant_forced", False)),
            "deterministic_logic_template_id": str(mode_policy.get("deterministic_logic_template_id") or payload.get("logic_template_id") or "").strip() or None,
        },
    }
    result = job.get("result") or {}
    if isinstance(result, dict):
        result_generation_mode_summary = result.get("generation_mode_summary") if isinstance(result.get("generation_mode_summary"), dict) else {}
        if result_generation_mode_summary:
            out["generation_mode_summary"] = {
                "profile": str(
                    result_generation_mode_summary.get("profile")
                    or out["generation_mode_summary"].get("profile")
                    or ""
                ).strip()
                or None,
                "mode_effective": str(
                    result_generation_mode_summary.get("mode_effective")
                    or out["generation_mode_summary"].get("mode_effective")
                    or ""
                ).strip()
                or None,
                "stable_output": bool(
                    result_generation_mode_summary.get("stable_output", out["generation_mode_summary"].get("stable_output", False))
                ),
                "deterministic_variant_forced": bool(
                    result_generation_mode_summary.get(
                        "deterministic_variant_forced",
                        out["generation_mode_summary"].get("deterministic_variant_forced", False),
                    )
                ),
                "deterministic_logic_template_id": str(
                    result_generation_mode_summary.get("deterministic_logic_template_id")
                    or out["generation_mode_summary"].get("deterministic_logic_template_id")
                    or ""
                ).strip()
                or None,
            }
        out["files"] = result
        out["resource_usage_summary"] = result.get("resource_usage_summary") if isinstance(result.get("resource_usage_summary"), dict) else {}
        if isinstance(result.get("runtime_by_variant"), dict):
            out["runtime_by_variant"] = result.get("runtime_by_variant")
        if isinstance(result.get("quality_by_variant"), dict):
            out["quality_by_variant"] = result.get("quality_by_variant")
            quality_rows = sorted(
                [item for item in result["quality_by_variant"].values() if isinstance(item, dict)],
                key=lambda item: (int(item.get("variant_index") or 0), str(item.get("variant_id") or "")),
            )
            if quality_rows:
                out["quality_ok"] = [bool(item.get("quality_gate_ok", False)) for item in quality_rows]
        runtime_rows = out.get("runtime_by_variant") if isinstance(out.get("runtime_by_variant"), dict) else {}
        quality_rows_map = out.get("quality_by_variant") if isinstance(out.get("quality_by_variant"), dict) else {}
        variant_count = max(len(runtime_rows), len(quality_rows_map))
        if variant_count > 0:
            out["variants"] = variant_count
        if str(result.get("logic_template_id") or "").strip():
            out["logic_template_id"] = str(result.get("logic_template_id") or "").strip() or None
        if str(result.get("logic_template_name") or "").strip():
            out["logic_template_name"] = str(result.get("logic_template_name") or "").strip() or None
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
                    out["logic_template_id"] = str(
                        variants[0].get("logic_template_id") or ((variants[0].get("logic_template") or {}) if isinstance(variants[0].get("logic_template"), dict) else {}).get("id") or ""
                    ).strip() or None
                    out["logic_template_name"] = str(
                        variants[0].get("logic_template_name") or ((variants[0].get("logic_template") or {}) if isinstance(variants[0].get("logic_template"), dict) else {}).get("name") or ""
                    ).strip() or None
                    ma = variants[0].get("multi_agent")
                    if isinstance(ma, dict):
                        out["multi_agent"] = ma
            except Exception:
                pass
    return {"ok": True, "job": out, "housekeep": dict(_HOUSEKEEP_LAST_REPORT)}


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
        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
        progress = rec.get("progress") if isinstance(rec.get("progress"), dict) else {}
        result = rec.get("result") if isinstance(rec.get("result"), dict) else {}
        sla = rec.get("sla") if isinstance(rec.get("sla"), dict) else {}
        agent_runtime = rec.get("agent_runtime") if isinstance(rec.get("agent_runtime"), dict) else {}
        mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
        generation_mode_summary = _recent_job_generation_mode_summary(payload, result)
        quality_overview = _recent_job_quality_overview(result)
        automation_summary = _recent_job_automation_summary(result) if has_result_artifacts(result) else {}
        runtime_budget_summary = _recent_job_runtime_budget_summary(result) if has_result_artifacts(result) else []
        remediation_strategy_summary = _recent_job_remediation_strategy_summary(result) if has_result_artifacts(result) else {}
        remediation_execution_summary = _recent_job_remediation_execution_summary(result) if has_result_artifacts(result) else {}
        remediation_learning_summary = _recent_job_remediation_learning_summary(result) if has_result_artifacts(result) else {}
        items.append(
            {
                "job_id": rec.get("job_id"),
                "status": rec.get("status"),
                "error": rec.get("error"),
                "created_at": rec.get("created_at"),
                "updated_at": rec.get("updated_at"),
                "heartbeat_at": rec.get("heartbeat_at"),
                "topic": payload.get("topic"),
                "project_id": payload.get("project_id"),
                "project_type": payload.get("project_type"),
                "variants": payload.get("variants"),
                "generation_mode": generation_mode_summary.get("profile") or mode_policy.get("profile") or payload.get("generation_mode"),
                "mode_effective": generation_mode_summary.get("mode_effective") or mode_policy.get("mode_effective"),
                "generation_mode_summary": generation_mode_summary,
                "planned_total_pages": mode_policy.get("planned_total_pages") or payload.get("total_pages_target"),
                "logic_template_id": quality_overview.get("logic_template_id"),
                "logic_template_name": quality_overview.get("logic_template_name"),
                "quality_score": quality_overview.get("quality_score"),
                "quality_gate_ok": quality_overview.get("quality_gate_ok"),
                "quality_gate_failed_count": quality_overview.get("quality_gate_failed_count"),
                "progress_stage": progress.get("stage"),
                "progress_percent": progress.get("percent"),
                "sla_summary": _recent_job_sla_summary(sla),
                "stage_artifacts_dir": rec.get("stage_artifacts_dir"),
                "result_available": has_result_artifacts(result),
                "auto_remediate": bool(payload.get("auto_remediate", True)),
                "quality_gate_retry_rounds_planned": int(payload.get("quality_gate_retry_rounds") or 0),
                "agent_runtime": _recent_job_agent_runtime_summary(agent_runtime),
                "automation_summary": automation_summary,
                "runtime_budget_summary": runtime_budget_summary,
                "remediation_strategy_summary": remediation_strategy_summary,
                "remediation_execution_summary": remediation_execution_summary,
                "remediation_learning_summary": remediation_learning_summary,
            }
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
    terminal = [r for r in rows if str(r.get("status") or "").strip().lower() in {"done", "failed", "cancelled"}]
    totals: List[float] = []
    by_stage: Dict[str, List[float]] = {}
    for rec in terminal:
        sla = rec.get("sla") if isinstance(rec.get("sla"), dict) else {}
        t = sla.get("total_seconds")
        try:
            if t is not None and float(t) >= 0.0:
                totals.append(float(t))
        except Exception:
            pass
        stages = sla.get("stages") if isinstance(sla.get("stages"), list) else []
        for st in stages:
            if not isinstance(st, dict):
                continue
            name = str(st.get("name") or "").strip()
            if not name:
                continue
            try:
                dur = float(st.get("duration_sec"))
            except Exception:
                continue
            if dur < 0:
                continue
            by_stage.setdefault(name, []).append(dur)

    stage_stats: Dict[str, Any] = {}
    for k, vals in by_stage.items():
        stage_stats[k] = {
            "count": len(vals),
            "p50_sec": _pct(vals, 0.50),
            "p95_sec": _pct(vals, 0.95),
            "avg_sec": (sum(vals) / len(vals)) if vals else None,
        }
    return {
        "ok": True,
        "window": {"limit": n, "terminal_jobs": len(terminal)},
        "total_latency": {
            "count": len(totals),
            "p50_sec": _pct(totals, 0.50),
            "p95_sec": _pct(totals, 0.95),
            "avg_sec": (sum(totals) / len(totals)) if totals else None,
        },
        "stage_latency": stage_stats,
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
            workspace_dir=workspace["workspace_dir"],
        )
    for sec in sections:
        if isinstance(sec, dict):
            sec["content"] = strip_nonconcrete_language(str(sec.get("content") or ""))

    # Rebuild receipts/QC/cross-index for this variant after manual confirmation.
    payload_obj["workspace_dir"] = workspace["workspace_dir"]
    _rebuild_postprocessed_artifacts(
        [target],
        payload=payload_obj,
        report=None,
        params=params,
        workspace_dir=workspace["workspace_dir"],
    )

    # Persist all variants back to output files and refresh job result paths.
    out = _save_outputs(f"actions_{job_id}", variants, workspace_dir=workspace["workspace_dir"])
    update_job(job_id, workspace_dir=workspace["workspace_dir"], status="done", result=out, error=None)
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
        return {
            "ok": False,
            "code": "job_not_done",
            "message": "job not done",
            "job_id": job_id,
            "status": job.get("status"),
            "error": job.get("error"),
            "request_id": trace_meta.get("request_id") or None,
            "trace_id": trace_meta.get("trace_id") or None,
            "next_action": "poll /actions/job_status until status=done",
        }
    result = job.get("result") or {}
    json_path = result.get("json")
    if not json_path or not Path(json_path).exists():
        _raise_actions_http_error(
            404,
            "result_json_not_found",
            "result json not found",
            stage="result",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="check worker log and result artifact output",
            extra={"json_path": str(json_path or "")},
        )
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    variants = data.get("variants") or []
    if not variants:
        _raise_actions_http_error(
            404,
            "empty_result",
            "empty result",
            stage="result",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="check result json content",
            extra={"json_path": str(json_path or "")},
        )
    v = max(1, int(variant or 1))
    rec = variants[v - 1] if v <= len(variants) else variants[0]
    mode_policy = rec.get("mode_policy") if isinstance(rec.get("mode_policy"), dict) else {}
    generation_trace = rec.get("generation_trace") if isinstance(rec.get("generation_trace"), dict) else {}
    logic_template = rec.get("logic_template") if isinstance(rec.get("logic_template"), dict) else {}
    logic_template_id = str(rec.get("logic_template_id") or logic_template.get("id") or "").strip() or None
    logic_template_name = str(rec.get("logic_template_name") or logic_template.get("name") or "").strip() or None
    response = {
        "ok": True,
        "variant_id": rec.get("variant_id") or v,
        "logic_template_id": logic_template_id,
        "logic_template_name": logic_template_name,
        "topic": rec.get("topic"),
        "outline": rec.get("outline"),
        "boq_focus": rec.get("boq_focus"),
        "quality_checks": rec.get("quality_checks"),
        "request_id": trace_meta.get("request_id") or None,
        "trace_id": trace_meta.get("trace_id") or None,
        "generation_mode_summary": {
            "profile": str(mode_policy.get("profile") or generation_trace.get("generation_mode") or rec.get("generation_mode") or "").strip() or None,
            "mode_effective": str(mode_policy.get("mode_effective") or generation_trace.get("mode_effective") or generation_trace.get("generation_mode") or rec.get("generation_mode") or "").strip() or None,
            "stable_output": bool(mode_policy.get("stable_output", generation_trace.get("stable_output", False))),
            "deterministic_variant_forced": bool(
                mode_policy.get("deterministic_variant_forced", generation_trace.get("deterministic_variant_forced", False))
            ),
            "deterministic_logic_template_id": str(
                mode_policy.get("deterministic_logic_template_id")
                or generation_trace.get("deterministic_logic_template_id")
                or logic_template_id
                or ""
            ).strip()
            or None,
        },
        "resource_usage_summary": rec.get("resource_usage_summary") if isinstance(rec.get("resource_usage_summary"), dict) else {},
        "job_resource_usage_summary": result.get("resource_usage_summary") if isinstance(result.get("resource_usage_summary"), dict) else {},
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
    if job.get("status") != "done":
        _raise_actions_http_error(
            409,
            "job_not_done",
            f"job not done: {job.get('status')}",
            stage="download",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="poll /actions/job_status until status=done",
            extra={"status": str(job.get("status") or ""), "kind": kind, "variant": max(1, int(variant or 1))},
        )
    result = job.get("result") or {}
    path = result.get(kind)
    if kind in ("docx", "compare_docx", "focus_xlsx", "score_overview_xlsx", "expert_review_docx") and isinstance(path, list):
        v = max(1, int(variant or 1))
        path = path[v - 1] if v <= len(path) else None
    if not path or not Path(path).exists():
        _raise_actions_http_error(
            404,
            "artifact_not_found",
            "file not found",
            stage="download",
            job_id=job_id,
            request_id=trace_meta.get("request_id") or None,
            trace_id=trace_meta.get("trace_id") or None,
            next_action="check result artifacts or rerun generation",
            extra={"kind": kind, "variant": max(1, int(variant or 1)), "path": str(path or "")},
        )
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
    append_resource_event(
        "artifact_download",
        workspace_dir=workspace["workspace_dir"],
        session_id=workspace["session_id"],
        user_id=None,
        job_id=job_id,
        kind=kind,
        variant=max(1, int(variant or 1)),
        file_path=str(path),
        file_size_bytes=Path(path).stat().st_size,
        project_id=(job.get("payload") or {}).get("project_id") if isinstance(job.get("payload"), dict) else None,
        topic=(job.get("payload") or {}).get("topic") if isinstance(job.get("payload"), dict) else None,
        request_id=((job.get("payload") or {}).get("request_id") if isinstance(job.get("payload"), dict) else None),
        trace_id=((job.get("payload") or {}).get("trace_id") if isinstance(job.get("payload"), dict) else None),
    )
    return FileResponse(str(path), media_type=media_type, filename=filename)
