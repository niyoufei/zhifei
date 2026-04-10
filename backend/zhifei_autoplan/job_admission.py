from __future__ import annotations

from typing import Any, Dict, List

from backend.zhifei_autoplan.job_store import list_jobs, reconcile_job_runtime
from backend.zhifei_autoplan.quota_policy import resolve_quota_policy
from backend.zhifei_autoplan.usage_profile import build_usage_warnings, summarize_usage_profile


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        return int(value)
    except Exception:
        return default


def resolve_admission_limits(
    scope: str,
    *,
    tenant_id: str | None = None,
    session_id: str | None = None,
    user_id: int | None = None,
) -> Dict[str, Any]:
    scope_name = "user" if str(scope or "").strip().lower() == "user" else "session"
    return resolve_quota_policy(
        scope=scope_name,
        tenant_id=tenant_id,
        session_id=session_id,
        user_id=user_id,
    )


def _clamp_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    parsed = _safe_int(value, default)
    if parsed is None:
        parsed = default
    return max(min_value, min(max_value, int(parsed)))


def inspect_job_pressure(
    *,
    scope: str,
    tenant_id: str | None = None,
    workspace_dir: str | None = None,
    user_id: int | None = None,
    scan_limit: int | None = None,
    lease_seconds: int | None = None,
) -> Dict[str, Any]:
    scope_name = "user" if str(scope or "").strip().lower() == "user" else "session"
    limits = resolve_admission_limits(
        scope_name,
        tenant_id=tenant_id,
        session_id=tenant_id if scope_name == "session" else None,
        user_id=user_id,
    )
    fetch_limit = max(20, int(scan_limit or limits["scan_limit"] or 500))
    lease = max(60, int(lease_seconds or limits["lease_seconds"] or 900))
    include_all = scope_name == "user"
    rows: List[Dict[str, Any]] = []
    queued_count = 0
    running_count = 0
    touched_workspaces: set[str] = set()
    for raw in list_jobs(
        limit=fetch_limit,
        user_id=user_id,
        workspace_dir=workspace_dir if scope_name == "session" else None,
        include_all_workspaces=include_all,
    ):
        rec = raw
        status = _clean_text(rec.get("status")).lower()
        rec_workspace_dir = _clean_text(rec.get("workspace_dir")) or workspace_dir
        job_id = _clean_text(rec.get("job_id"))
        if status == "running" and job_id:
            rec = reconcile_job_runtime(
                job_id,
                lease_seconds=lease,
                workspace_dir=rec_workspace_dir or None,
            ) or rec
            status = _clean_text(rec.get("status")).lower()
            rec_workspace_dir = _clean_text(rec.get("workspace_dir")) or rec_workspace_dir
        if status not in {"queued", "running"}:
            continue
        if status == "queued":
            queued_count += 1
        elif status == "running":
            running_count += 1
        if rec_workspace_dir:
            touched_workspaces.add(rec_workspace_dir)
        rows.append(
            {
                "job_id": job_id,
                "status": status,
                "workspace_dir": rec_workspace_dir or None,
                "updated_at": rec.get("updated_at"),
                "created_at": rec.get("created_at"),
                "user_id": rec.get("user_id"),
            }
        )
    return {
        "scope": scope_name,
        "workspace_dir": workspace_dir,
        "user_id": user_id,
        "scan_limit": fetch_limit,
        "lease_seconds": lease,
        "queued_count": queued_count,
        "running_count": running_count,
        "active_count": queued_count + running_count,
        "workspace_count": len(touched_workspaces),
        "jobs": rows[:20],
    }


def evaluate_job_admission(
    *,
    scope: str,
    tenant_id: str,
    workspace_dir: str | None = None,
    user_id: int | None = None,
    requested_jobs: int = 1,
) -> Dict[str, Any]:
    scope_name = "user" if str(scope or "").strip().lower() == "user" else "session"
    requested = max(0, int(requested_jobs or 0))
    limits = resolve_admission_limits(
        scope_name,
        tenant_id=tenant_id,
        session_id=tenant_id if scope_name == "session" else None,
        user_id=user_id,
    )
    usage = inspect_job_pressure(
        scope=scope_name,
        tenant_id=tenant_id,
        workspace_dir=workspace_dir,
        user_id=user_id,
        scan_limit=limits["scan_limit"],
        lease_seconds=limits["lease_seconds"],
    )
    usage_profile = summarize_usage_profile(
        scope=scope_name,
        workspace_dir=workspace_dir,
        user_id=user_id,
    )
    usage["usage_profile"] = usage_profile

    code = ""
    message = ""
    next_action = "accept"
    running_limit = limits.get("running_limit")
    queued_limit = limits.get("queued_limit")
    active_limit = limits.get("active_limit")

    if running_limit is not None and int(usage["running_count"]) >= int(running_limit):
        code = f"{scope_name}_running_capacity_exceeded"
        message = "当前租户并发生成任务已达上限，请等待正在运行的任务完成后再试。"
        next_action = "wait_for_running_jobs"
    elif queued_limit is not None and int(usage["queued_count"]) + requested > int(queued_limit):
        code = f"{scope_name}_queue_capacity_exceeded"
        message = "当前租户排队任务过多，请稍后再试。"
        next_action = "wait_for_queued_jobs"
    elif active_limit is not None and int(usage["active_count"]) + requested > int(active_limit):
        code = f"{scope_name}_active_capacity_exceeded"
        message = "当前租户活跃任务总数已达上限，请等待现有任务完成后再试。"
        next_action = "wait_for_active_jobs"

    allowed = not code
    warnings = build_usage_warnings(
        usage=usage,
        limits=limits,
        requested_jobs=requested,
        scope=scope_name,
        policy=limits,
    )
    return {
        "allowed": allowed,
        "scope": scope_name,
        "tenant_id": _clean_text(tenant_id) or scope_name,
        "workspace_dir": workspace_dir,
        "user_id": user_id,
        "requested_jobs": requested,
        "limits": limits,
        "usage": usage,
        "code": code or "accepted",
        "message": message or "accepted",
        "retryable": not allowed,
        "next_action": next_action,
        "warning_level": warnings.get("warning_level"),
        "warnings": warnings.get("warnings") or [],
        "warning_ratio": warnings.get("warning_ratio"),
    }


def recommend_admission_degrade(
    *,
    decision: Dict[str, Any],
    payload: Dict[str, Any] | None,
) -> Dict[str, Any]:
    if not isinstance(decision, dict) or not bool(decision.get("allowed", False)):
        return {}
    if not isinstance(payload, dict):
        return {}
    warning_level = _clean_text(decision.get("warning_level")) or "none"
    if warning_level not in {"notice", "warning"}:
        return {}
    scope_name = _clean_text(decision.get("scope")) or "session"
    warnings = decision.get("warnings") if isinstance(decision.get("warnings"), list) else []
    warning_codes = {
        _clean_text(item.get("code"))
        for item in warnings
        if isinstance(item, dict) and _clean_text(item.get("code"))
    }
    if not warning_codes:
        return {}

    capacity_codes = {
        f"{scope_name}_running_capacity_near_limit",
        f"{scope_name}_queue_capacity_near_limit",
        f"{scope_name}_active_capacity_near_limit",
    }
    token_code = f"{scope_name}_tokens_last_hour_near_limit"
    current_ap = _clamp_int(payload.get("agent_parallelism"), 4, 1, 16)
    current_vp = _clamp_int(payload.get("variant_parallelism"), 1, 1, 5)
    current_generate_images = bool(payload.get("generate_images", True))
    current_compare_max_chars = _clamp_int(payload.get("compare_max_chars"), 1200, 200, 5000)
    limits = decision.get("limits") if isinstance(decision.get("limits"), dict) else {}
    current_text_chain_profile = _clean_text(payload.get("text_chain_profile")) or _clean_text(limits.get("text_chain_profile")) or "default"
    target_text_chain_profile = current_text_chain_profile
    degrade_text_chain_profile = _clean_text(limits.get("degrade_text_chain_profile")) or current_text_chain_profile
    target_ap = current_ap
    target_vp = current_vp
    target_generate_images = current_generate_images
    target_compare_max_chars = current_compare_max_chars
    triggers: List[str] = []

    if warning_codes & capacity_codes:
        triggers.append("capacity")
        target_vp = min(target_vp, 1)
        if degrade_text_chain_profile:
            target_text_chain_profile = degrade_text_chain_profile
        if warning_level == "warning":
            target_ap = min(target_ap, max(1, current_ap // 2))
        else:
            target_ap = min(target_ap, max(1, current_ap - 1))
    if token_code in warning_codes:
        triggers.append("tokens")
        if degrade_text_chain_profile:
            target_text_chain_profile = degrade_text_chain_profile
        target_ap = min(target_ap, max(1, current_ap - 1))
        target_generate_images = False
        target_compare_max_chars = min(target_compare_max_chars, 600)
    if warning_level == "warning" and warning_codes & capacity_codes:
        target_generate_images = False
        target_compare_max_chars = min(target_compare_max_chars, 800)

    if (
        target_ap >= current_ap
        and target_vp >= current_vp
        and target_generate_images == current_generate_images
        and target_compare_max_chars >= current_compare_max_chars
        and target_text_chain_profile == current_text_chain_profile
    ):
        return {}

    message = "当前租户负载已接近阈值，系统已自动切换为保守并发配置以降低排队放大风险。"
    if triggers == ["tokens"]:
        message = "当前租户最近一小时 Token 消耗偏高，系统已自动下调并发并收缩附加开销以控制成本波动。"
    elif warning_level == "warning" and warning_codes & capacity_codes:
        message = "当前租户负载偏高，系统已自动下调并发并关闭高开销附加步骤，以避免任务堆积放大。"

    return {
        "applied": True,
        "warning_level": warning_level,
        "reason": "soft_capacity_guard",
        "message": message,
        "trigger_codes": sorted(warning_codes),
        "trigger_types": triggers,
        "agent_parallelism_before": current_ap,
        "agent_parallelism_after": target_ap,
        "variant_parallelism_before": current_vp,
        "variant_parallelism_after": target_vp,
        "generate_images_before": current_generate_images,
        "generate_images_after": target_generate_images,
        "compare_max_chars_before": current_compare_max_chars,
        "compare_max_chars_after": target_compare_max_chars,
        "text_chain_profile_before": current_text_chain_profile,
        "text_chain_profile_after": target_text_chain_profile,
    }


def apply_admission_degrade(
    payload: Dict[str, Any] | None,
    decision: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    plan = recommend_admission_degrade(decision=decision, payload=payload)
    if not plan.get("applied", False):
        return {}
    payload["agent_parallelism"] = int(plan["agent_parallelism_after"])
    payload["variant_parallelism"] = int(plan["variant_parallelism_after"])
    payload["generate_images"] = bool(plan["generate_images_after"])
    payload["compare_max_chars"] = int(plan["compare_max_chars_after"])
    payload["text_chain_profile"] = _clean_text(plan.get("text_chain_profile_after")) or _clean_text(payload.get("text_chain_profile")) or "default"
    payload["_admission_degrade_plan"] = dict(plan)
    return dict(plan)


def admission_http_detail(decision: Dict[str, Any]) -> Dict[str, Any]:
    detail = {
        "code": _clean_text(decision.get("code")) or "accepted",
        "message": _clean_text(decision.get("message")) or "accepted",
        "scope": _clean_text(decision.get("scope")) or "session",
        "tenant_id": _clean_text(decision.get("tenant_id")) or "tenant",
        "requested_jobs": max(0, int(decision.get("requested_jobs") or 0)),
        "usage": dict(decision.get("usage") or {}),
        "limits": dict(decision.get("limits") or {}),
        "next_action": _clean_text(decision.get("next_action")) or "accept",
        "retryable": bool(decision.get("retryable", False)),
        "warning_level": _clean_text(decision.get("warning_level")) or "none",
        "warnings": list(decision.get("warnings") or []),
    }
    degrade_plan = decision.get("degrade_plan")
    if isinstance(degrade_plan, dict) and degrade_plan:
        detail["degrade_plan"] = dict(degrade_plan)
    return detail
