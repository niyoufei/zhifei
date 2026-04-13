from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

from backend.app.core import actions_result_view as result_view_core

from backend.zhifei_autoplan.self_evolution import build_chapter_effect_summary


def load_watcher_state(path: str | Path | None = None) -> dict[str, Any]:
    state_path = Path(path) if path is not None else Path(__file__).resolve().parents[3] / ".runtime" / "docgen" / "watcher_state.json"
    if not state_path.exists():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def recent_job_automation_summary(result: dict | None) -> dict[str, Any]:
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


def recent_job_first_variant_summary(raw: Any) -> dict[str, Any]:
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


def recent_job_generation_mode_summary(payload: dict | None, result: dict | None) -> dict[str, Any]:
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


def recent_job_quality_overview(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    first = recent_job_first_variant_summary(result.get("quality_by_variant"))
    blocking_issue_summary = (
        result.get("blocking_issue_summary")
        if isinstance(result.get("blocking_issue_summary"), dict)
        else (
            first.get("blocking_issue_summary")
            if isinstance(first, dict) and isinstance(first.get("blocking_issue_summary"), dict)
            else {}
        )
    )
    top_blocking_issues = (
        blocking_issue_summary.get("top_blocking_issues")
        if isinstance(blocking_issue_summary.get("top_blocking_issues"), list)
        else []
    )
    top_blocking_issue = top_blocking_issues[0] if top_blocking_issues and isinstance(top_blocking_issues[0], dict) else {}
    overview = {
        "logic_template_id": str(first.get("logic_template_id") or "").strip() or None if isinstance(first, dict) else None,
        "logic_template_name": str(first.get("logic_template_name") or "").strip() or None if isinstance(first, dict) else None,
        "quality_score": first.get("quality_score") if isinstance(first, dict) else None,
        "quality_gate_ok": bool(first.get("quality_gate_ok", False)) if isinstance(first, dict) else None,
        "quality_gate_failed_count": int(first.get("quality_gate_failed_count") or 0) if isinstance(first, dict) else 0,
        "blocking_issue_summary": blocking_issue_summary if isinstance(blocking_issue_summary, dict) else {},
        "has_blocking_issues": bool(blocking_issue_summary.get("has_blocking_issues", False))
        if isinstance(blocking_issue_summary, dict)
        else False,
        "blocking_issue_count": int(blocking_issue_summary.get("blocking_issue_count") or 0)
        if isinstance(blocking_issue_summary, dict)
        else 0,
        "failed_gate_metric_count": int(blocking_issue_summary.get("failed_gate_metric_count") or 0)
        if isinstance(blocking_issue_summary, dict)
        else 0,
        "top_blocking_issue_title": str(top_blocking_issue.get("title") or "").strip() or None,
        "top_blocking_issue_type": str(top_blocking_issue.get("type") or "").strip() or None,
    }
    if not isinstance(first, dict) and not isinstance(blocking_issue_summary, dict):
        return {}
    return overview


def recent_job_agent_runtime_summary(agent_runtime: dict | None) -> dict[str, Any]:
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


def recent_job_sla_summary(sla: dict | None, *, now_ts: float | None = None) -> dict[str, Any]:
    if not isinstance(sla, dict):
        return {}

    def _safe_non_negative_float(value: Any) -> float | None:
        try:
            out = float(value)
        except Exception:
            return None
        return out if out >= 0.0 else None

    clock = float(now_ts) if now_ts is not None else time.time()
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
            current_stage_seconds = round(max(0.0, clock - current_stage_started_at), 3)
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
                stage_seconds = round(max(0.0, clock - started_at), 3)
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


def parse_recent_timestamp(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(time.mktime(time.strptime(text, "%Y-%m-%d %H:%M:%S")))
    except Exception:
        return 0.0


def recent_signal_rank(kind: str, summary: str) -> int:
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


def recent_summary_line(
    rows: list[dict[str, Any]],
    *,
    reference_timestamp: str = "",
    healthy: bool = False,
    recent_window_seconds: int = 1800,
    idle_fallback: str = "",
) -> str:
    if not rows:
        return ""
    ref_ts = parse_recent_timestamp(reference_timestamp)
    filtered: list[dict[str, Any]] = []
    for item in rows:
        item_ts = parse_recent_timestamp(item.get("timestamp") or "")
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
            if recent_signal_rank(item.get("kind") or "", item.get("summary") or "") < 4
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


def normalize_recent_rows(items: list[Any], *, limit: int = 6) -> list[dict[str, Any]]:
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
            recent_signal_rank(item.get("kind") or "", item.get("summary") or ""),
            -parse_recent_timestamp(item.get("timestamp") or ""),
        )
    )
    return rows


def chief_agent_status_summary(
    state: dict | None,
    *,
    stale_seconds: int = 120,
    now_ts: float | None = None,
) -> dict[str, Any]:
    if not isinstance(state, dict) or not state:
        return {}
    clock = float(now_ts) if now_ts is not None else time.time()
    timestamp = str(state.get("timestamp") or "").strip()
    age_seconds = None
    try:
        if timestamp:
            age_seconds = max(0, int(clock - time.mktime(time.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))))
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
    recent_rows = normalize_recent_rows(recent)
    recent_summary = recent_summary_line(
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
        "recent_summary_line": recent_summary,
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


def watcher_status_summary(
    state: dict | None,
    *,
    stale_seconds: int = 180,
    now_ts: float | None = None,
) -> dict[str, Any]:
    if not isinstance(state, dict) or not state:
        return {}
    clock = float(now_ts) if now_ts is not None else time.time()
    timestamp = str(state.get("timestamp") or "").strip()
    age_seconds = None
    try:
        if timestamp:
            age_seconds = max(0, int(clock - time.mktime(time.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))))
    except Exception:
        age_seconds = None
    status = str(state.get("status") or "").strip() or "unknown"
    recent = state.get("recent") if isinstance(state.get("recent"), list) else []
    healthy = status != "error" and (age_seconds is None or age_seconds <= max(60, int(stale_seconds or 180)))
    recent_rows = normalize_recent_rows(recent)
    recent_summary = recent_summary_line(
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
        "recent_summary_line": recent_summary,
        "last_project_id": str(state.get("last_project_id") or "").strip(),
        "last_project_name": str(state.get("last_project_name") or "").strip(),
        "last_error": str(state.get("last_error") or "").strip(),
        "inbox_count": int(state.get("inbox_count") or 0),
        "work_count": int(state.get("work_count") or 0),
        "done_count": int(state.get("done_count") or 0),
        "failed_count": int(state.get("failed_count") or 0),
        "recent": recent_rows,
    }


def recent_job_runtime_budget_summary(result: dict | None) -> list[dict[str, Any]]:
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


def recent_job_remediation_strategy_summary(result: dict | None) -> dict[str, Any]:
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


def recent_job_remediation_execution_summary(result: dict | None) -> dict[str, Any]:
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


def recent_job_remediation_learning_summary(result: dict | None) -> dict[str, Any]:
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


def build_recent_job_item(
    rec: dict[str, Any],
    *,
    result_available: bool,
    download_kind_specs: Dict[str, Dict[str, str]],
) -> dict[str, Any]:
    payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
    progress = rec.get("progress") if isinstance(rec.get("progress"), dict) else {}
    result = rec.get("result") if isinstance(rec.get("result"), dict) else {}
    sla = rec.get("sla") if isinstance(rec.get("sla"), dict) else {}
    agent_runtime = rec.get("agent_runtime") if isinstance(rec.get("agent_runtime"), dict) else {}
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    generation_mode = recent_job_generation_mode_summary(payload, result)
    quality_overview = recent_job_quality_overview(result)
    contract_view = result_view_core.result_contract_view(
        str(rec.get("job_id") or ""),
        result,
        download_kind_specs=download_kind_specs,
        variant=1,
    )
    automation_summary = recent_job_automation_summary(result) if result_available else {}
    runtime_budget_summary = recent_job_runtime_budget_summary(result) if result_available else []
    remediation_strategy_summary = recent_job_remediation_strategy_summary(result) if result_available else {}
    remediation_execution_summary = recent_job_remediation_execution_summary(result) if result_available else {}
    remediation_learning_summary = recent_job_remediation_learning_summary(result) if result_available else {}
    return {
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
        "generation_mode": generation_mode.get("profile") or mode_policy.get("profile") or payload.get("generation_mode"),
        "mode_effective": generation_mode.get("mode_effective") or mode_policy.get("mode_effective"),
        "generation_mode_summary": generation_mode,
        "planned_total_pages": mode_policy.get("planned_total_pages") or payload.get("total_pages_target"),
        "logic_template_id": quality_overview.get("logic_template_id"),
        "logic_template_name": quality_overview.get("logic_template_name"),
        "quality_score": quality_overview.get("quality_score"),
        "quality_gate_ok": quality_overview.get("quality_gate_ok"),
        "quality_gate_failed_count": quality_overview.get("quality_gate_failed_count"),
        "blocking_issue_summary": quality_overview.get("blocking_issue_summary"),
        "has_blocking_issues": quality_overview.get("has_blocking_issues"),
        "blocking_issue_count": quality_overview.get("blocking_issue_count"),
        "failed_gate_metric_count": quality_overview.get("failed_gate_metric_count"),
        "top_blocking_issue_title": quality_overview.get("top_blocking_issue_title"),
        "top_blocking_issue_type": quality_overview.get("top_blocking_issue_type"),
        "progress_stage": progress.get("stage"),
        "progress_percent": progress.get("percent"),
        "sla_summary": recent_job_sla_summary(sla),
        "stage_artifacts_dir": rec.get("stage_artifacts_dir"),
        "result_available": result_available,
        "result_bundle_json": contract_view.get("result_bundle_json"),
        "result_bundle_available": contract_view.get("result_bundle_available"),
        "result_bundle_loaded": contract_view.get("result_bundle_loaded"),
        "result_bundle_complete": contract_view.get("result_bundle_complete"),
        "result_bundle_schema_version": contract_view.get("result_bundle_schema_version"),
        "download_ready_count": contract_view.get("download_ready_count"),
        "download_ready_kinds": contract_view.get("download_ready_kinds"),
        "primary_download_kind": contract_view.get("primary_download_kind"),
        "reference_quality_summary": contract_view.get("reference_quality_summary"),
        "has_reference_risks": contract_view.get("has_reference_risks"),
        "reference_risk_count": contract_view.get("reference_risk_count"),
        "case_copy_risk_count": contract_view.get("case_copy_risk_count"),
        "affected_case_ids": contract_view.get("affected_case_ids"),
        "top_reference_risk_title": contract_view.get("top_reference_risk_title"),
        "top_reference_risk_type": contract_view.get("top_reference_risk_type"),
        "reference_enhancements": contract_view.get("reference_enhancements"),
        "case_library_summary": contract_view.get("case_library_summary"),
        "image_library_summary": contract_view.get("image_library_summary"),
        "case_library_enabled": contract_view.get("case_library_enabled"),
        "case_library_selected_ids": contract_view.get("case_library_selected_ids"),
        "case_library_matched_project_type": contract_view.get("case_library_matched_project_type"),
        "case_library_matched_chapters": contract_view.get("case_library_matched_chapters"),
        "case_library_match_reasons": contract_view.get("case_library_match_reasons"),
        "case_library_hit_count": contract_view.get("case_library_hit_count"),
        "case_library_warning_list": contract_view.get("case_library_warning_list"),
        "case_library_warning_count": contract_view.get("case_library_warning_count"),
        "image_library_enabled": contract_view.get("image_library_enabled"),
        "image_library_selected_ids": contract_view.get("image_library_selected_ids"),
        "image_library_matched_project_type": contract_view.get("image_library_matched_project_type"),
        "image_library_matched_chapters": contract_view.get("image_library_matched_chapters"),
        "image_library_match_reasons": contract_view.get("image_library_match_reasons"),
        "image_library_hit_count": contract_view.get("image_library_hit_count"),
        "image_library_warning_list": contract_view.get("image_library_warning_list"),
        "image_library_warning_count": contract_view.get("image_library_warning_count"),
        "latest_review_apply_summary": contract_view.get("latest_review_apply_summary"),
        "review_apply_variant": contract_view.get("review_apply_variant"),
        "review_apply_applied_count": contract_view.get("review_apply_applied_count"),
        "review_apply_template_applied_count": contract_view.get("review_apply_template_applied_count"),
        "review_apply_replacement_count": contract_view.get("review_apply_replacement_count"),
        "review_apply_reference_case_ids": contract_view.get("review_apply_reference_case_ids"),
        "review_apply_has_reference_case": contract_view.get("review_apply_has_reference_case"),
        "review_apply_issue_types": contract_view.get("review_apply_issue_types"),
        "review_apply_history_count": contract_view.get("review_apply_history_count"),
        "review_apply_last_applied_at": contract_view.get("review_apply_last_applied_at"),
        "auto_remediate": bool(payload.get("auto_remediate", True)),
        "quality_gate_retry_rounds_planned": int(payload.get("quality_gate_retry_rounds") or 0),
        "agent_runtime": recent_job_agent_runtime_summary(agent_runtime),
        "automation_summary": automation_summary,
        "runtime_budget_summary": runtime_budget_summary,
        "remediation_strategy_summary": remediation_strategy_summary,
        "remediation_execution_summary": remediation_execution_summary,
        "remediation_learning_summary": remediation_learning_summary,
    }


def percentile(values: list[float], q: float) -> float | None:
    vals = sorted(float(v) for v in values if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return round(vals[0], 3)
    q = max(0.0, min(1.0, float(q)))
    pos = (len(vals) - 1) * q
    lo = int(pos)
    hi = min(len(vals) - 1, lo + 1)
    frac = pos - lo
    return round(vals[lo] * (1 - frac) + vals[hi] * frac, 3)


def jobs_sla_summary(rows: list[dict[str, Any]], *, limit: int) -> dict[str, Any]:
    terminal = [r for r in rows if str(r.get("status") or "").strip().lower() in {"done", "failed", "cancelled"}]
    totals: list[float] = []
    by_stage: dict[str, list[float]] = {}
    for rec in terminal:
        sla = rec.get("sla") if isinstance(rec.get("sla"), dict) else {}
        total = sla.get("total_seconds")
        try:
            if total is not None and float(total) >= 0.0:
                totals.append(float(total))
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

    stage_stats: dict[str, Any] = {}
    for name, vals in by_stage.items():
        stage_stats[name] = {
            "count": len(vals),
            "p50_sec": percentile(vals, 0.50),
            "p95_sec": percentile(vals, 0.95),
            "avg_sec": (sum(vals) / len(vals)) if vals else None,
        }
    return {
        "window": {"limit": int(limit), "terminal_jobs": len(terminal)},
        "total_latency": {
            "count": len(totals),
            "p50_sec": percentile(totals, 0.50),
            "p95_sec": percentile(totals, 0.95),
            "avg_sec": (sum(totals) / len(totals)) if totals else None,
        },
        "stage_latency": stage_stats,
    }
