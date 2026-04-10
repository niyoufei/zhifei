from __future__ import annotations

import os
import hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr

from backend.auth_store import create_user, verify_user, get_user_by_id, update_balance, get_user_by_email, list_charges, list_charges_by_user, update_daily_limit, list_users, list_users_page
from backend.zhifei_autoplan.quota_policy import append_quota_policy_audit
from backend.zhifei_autoplan.job_admission import admission_http_detail, evaluate_job_admission
from backend.zhifei_autoplan.usage_profile import summarize_usage_profile
from backend.zhifei_autoplan.workspace import resolve_workspace_dir

router = APIRouter(prefix="/auth", tags=["Auth"])

JWT_SECRET = os.environ.get("ZF_JWT_SECRET", "change-me")
JWT_ALG = "HS256"
ADMIN_KEY = os.environ.get("ZF_ADMIN_KEY", "")
AUTH_OPS_EXPORT_DIR = Path("backend/data/auth/ops_exports")
AUTH_OPS_SUMMARY_SNAPSHOT_DIR = AUTH_OPS_EXPORT_DIR / "summary_snapshots"
DEFAULT_AUTH_OPS_SUMMARY_SNAPSHOT_DIR = Path("backend/data/auth/ops_exports/summary_snapshots")
AUTH_OPS_SUMMARY_SNAPSHOT_EXPORT_DIR = AUTH_OPS_EXPORT_DIR / "summary_snapshot_exports"
DEFAULT_AUTH_OPS_SUMMARY_SNAPSHOT_EXPORT_DIR = Path("backend/data/auth/ops_exports/summary_snapshot_exports")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TopupRequest(BaseModel):
    email: EmailStr
    amount: int


class DailyLimitRequest(BaseModel):
    email: EmailStr
    limit: int


class ExportRetentionRequest(BaseModel):
    keep_latest: int = 20
    older_than_hours: int = 168
    export_format: str = ""
    execute: bool = False
    confirm_token: str = ""
    confirm_generated_at: str = ""
    confirm_prune_candidates_count: int = 0


class ConfirmTokenRetentionRequest(BaseModel):
    keep_latest: int = 200
    older_than_hours: int = 168
    execute: bool = False


class SummarySnapshotRetentionRequest(BaseModel):
    keep_latest: int = 50
    older_than_hours: int = 168
    execute: bool = False


class SummarySnapshotExportRetentionRequest(BaseModel):
    keep_latest: int = 50
    older_than_hours: int = 168
    execute: bool = False


def _issue_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(days=7),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _get_user_from_token(auth_header: Optional[str]):
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth_header.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(data.get("sub"))
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="invalid user")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="invalid token")


def _require_admin(authorization: Optional[str]) -> None:
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")


def _billing_summary(user_id: int) -> dict:
    items = list_charges_by_user(user_id, limit=5000)
    by_action = {}
    total_cost = 0
    for item in items:
        action = str(item.get("action") or "unknown").strip() or "unknown"
        cost = int(item.get("cost") or 0)
        total_cost += cost
        bucket = by_action.get(action)
        if bucket is None:
            bucket = {"count": 0, "cost_total": 0}
            by_action[action] = bucket
        bucket["count"] += 1
        bucket["cost_total"] += cost
    return {
        "charge_event_count": len(items),
        "charge_cost_total": total_cost,
        "by_action": by_action,
    }


def _usage_ops_summary(usage_profile: dict | None) -> dict:
    profile = usage_profile if isinstance(usage_profile, dict) else {}
    windows = profile.get("windows") if isinstance(profile.get("windows"), dict) else {}
    last_hour = windows.get("last_hour") if isinstance(windows.get("last_hour"), dict) else {}
    last_day = windows.get("last_day") if isinstance(windows.get("last_day"), dict) else {}
    return {
        "last_hour": {
            "queued_jobs": int(last_hour.get("queued_jobs") or 0),
            "rejected_jobs": int(last_hour.get("rejected_jobs") or 0),
            "degraded_jobs": int(last_hour.get("degraded_jobs") or 0),
            "completed_jobs": int(last_hour.get("completed_jobs") or 0),
            "failed_jobs": int(last_hour.get("failed_jobs") or 0),
            "download_count": int(last_hour.get("download_count") or 0),
            "rejection_codes": dict(last_hour.get("rejection_codes") or {}),
            "text_chain_profiles": dict(last_hour.get("text_chain_profiles") or {}),
        },
        "last_day": {
            "queued_jobs": int(last_day.get("queued_jobs") or 0),
            "rejected_jobs": int(last_day.get("rejected_jobs") or 0),
            "degraded_jobs": int(last_day.get("degraded_jobs") or 0),
            "completed_jobs": int(last_day.get("completed_jobs") or 0),
            "failed_jobs": int(last_day.get("failed_jobs") or 0),
            "download_count": int(last_day.get("download_count") or 0),
            "rejection_codes": dict(last_day.get("rejection_codes") or {}),
            "text_chain_profiles": dict(last_day.get("text_chain_profiles") or {}),
        },
    }


def _normalize_page_limit(limit: int, *, default: int = 20, max_limit: int = 50) -> int:
    try:
        value = int(limit)
    except Exception:
        value = int(default)
    return max(1, min(value, max_limit))


def _normalize_offset(offset: int) -> int:
    try:
        value = int(offset)
    except Exception:
        value = 0
    return max(0, value)


def _normalize_metric_threshold(value: int) -> int:
    try:
        number = int(value)
    except Exception:
        number = 0
    return max(0, number)


def _normalize_sort_by(sort_by: str) -> str:
    value = str(sort_by or "").strip().lower()
    if value in {
        "user_id",
        "charge_cost_total",
        "rejected_jobs",
        "degraded_jobs",
        "queued_jobs",
        "completed_jobs",
        "failed_jobs",
        "download_count",
    }:
        return value
    return "user_id"


def _normalize_sort_order(sort_order: str) -> str:
    return "asc" if str(sort_order or "").strip().lower() == "asc" else "desc"


def _normalize_warning_level(warning_level: str) -> str:
    value = str(warning_level or "").strip().lower()
    if value in {"none", "notice", "warning"}:
        return value
    return ""


def _normalize_text_chain_profile(profile: str) -> str:
    return str(profile or "").strip().lower()


def _user_public_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(user["id"]),
        "email": str(user.get("email") or ""),
        "balance": int(user.get("balance") or 0),
        "daily_limit": int(user.get("daily_limit") or 0),
    }


def _usage_profile_from_decision(
    decision: dict[str, Any],
    *,
    scope: str,
    user_id: int | None = None,
    workspace_dir: str | None = None,
) -> dict[str, Any]:
    usage = decision.get("usage") if isinstance(decision.get("usage"), dict) else {}
    usage_profile = usage.get("usage_profile") if isinstance(usage.get("usage_profile"), dict) else None
    if isinstance(usage_profile, dict):
        return usage_profile
    return summarize_usage_profile(scope=scope, user_id=user_id, workspace_dir=workspace_dir)


def _build_user_usage_report(user: dict[str, Any], *, workspace_dir: str | None = None) -> dict[str, Any]:
    user_decision = evaluate_job_admission(
        scope="user",
        tenant_id=f"user-{user['id']}",
        user_id=int(user["id"]),
        workspace_dir=str(workspace_dir or "").strip() or None,
        requested_jobs=0,
    )
    user_profile = _usage_profile_from_decision(
        user_decision,
        scope="user",
        user_id=int(user["id"]),
    )
    return {
        "admission": admission_http_detail(user_decision),
        "usage_profile": user_profile,
        "ops_summary": _usage_ops_summary(user_profile),
        "billing_summary": _billing_summary(int(user["id"])),
    }


def _build_session_usage_report(*, session_id: str, workspace_dir: str) -> dict[str, Any]:
    session_decision = evaluate_job_admission(
        scope="session",
        tenant_id=session_id,
        workspace_dir=workspace_dir,
        requested_jobs=0,
    )
    session_profile = _usage_profile_from_decision(
        session_decision,
        scope="session",
        workspace_dir=workspace_dir,
    )
    return {
        "session_id": session_id,
        "workspace_dir": workspace_dir,
        "admission": admission_http_detail(session_decision),
        "usage_profile": session_profile,
        "ops_summary": _usage_ops_summary(session_profile),
    }


def _tenant_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "admission": dict(report.get("admission") or {}),
        "ops_summary": dict(report.get("ops_summary") or {}),
        "billing_summary": dict(report.get("billing_summary") or {}),
    }


def _tenant_last_hour_metrics(summary: dict[str, Any]) -> dict[str, int]:
    ops = summary.get("ops_summary") if isinstance(summary.get("ops_summary"), dict) else {}
    last_hour = ops.get("last_hour") if isinstance(ops.get("last_hour"), dict) else {}
    return {
        "queued_jobs": int(last_hour.get("queued_jobs") or 0),
        "rejected_jobs": int(last_hour.get("rejected_jobs") or 0),
        "degraded_jobs": int(last_hour.get("degraded_jobs") or 0),
        "completed_jobs": int(last_hour.get("completed_jobs") or 0),
        "failed_jobs": int(last_hour.get("failed_jobs") or 0),
        "download_count": int(last_hour.get("download_count") or 0),
    }


def _tenant_last_hour_text_chain_profiles(summary: dict[str, Any]) -> dict[str, int]:
    ops = summary.get("ops_summary") if isinstance(summary.get("ops_summary"), dict) else {}
    last_hour = ops.get("last_hour") if isinstance(ops.get("last_hour"), dict) else {}
    profiles = last_hour.get("text_chain_profiles") if isinstance(last_hour.get("text_chain_profiles"), dict) else {}
    return {
        str(key).strip().lower(): int(value or 0)
        for key, value in profiles.items()
        if str(key).strip()
    }


def _build_tenant_report_item(user: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    return {
        "user": _user_public_payload(user),
        "report_summary": _tenant_report_summary(report),
    }


def _accumulate_page_summary(page_summary: dict[str, Any], item: dict[str, Any]) -> None:
    page_summary["tenant_count"] += 1
    summary = item.get("report_summary") if isinstance(item.get("report_summary"), dict) else {}
    billing = summary.get("billing_summary") if isinstance(summary.get("billing_summary"), dict) else {}
    page_summary["charge_event_count"] += int(billing.get("charge_event_count") or 0)
    page_summary["charge_cost_total"] += int(billing.get("charge_cost_total") or 0)
    for field, value in _tenant_last_hour_metrics(summary).items():
        page_summary["last_hour"][field] += int(value or 0)


def _new_page_summary() -> dict[str, Any]:
    return {
        "tenant_count": 0,
        "charge_event_count": 0,
        "charge_cost_total": 0,
        "last_hour": {
            "queued_jobs": 0,
            "rejected_jobs": 0,
            "degraded_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "download_count": 0,
        },
    }


def _tenant_report_matches_filters(
    item: dict[str, Any],
    *,
    email_query: str,
    warning_level: str,
    min_charge_cost_total: int,
    min_rejected_jobs: int,
    text_chain_profile: str,
) -> bool:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    summary = item.get("report_summary") if isinstance(item.get("report_summary"), dict) else {}
    admission = summary.get("admission") if isinstance(summary.get("admission"), dict) else {}
    billing = summary.get("billing_summary") if isinstance(summary.get("billing_summary"), dict) else {}
    if email_query:
        email_value = str(user.get("email") or "").lower()
        if email_query not in email_value:
            return False
    if warning_level:
        if str(admission.get("warning_level") or "").strip().lower() != warning_level:
            return False
    if int(billing.get("charge_cost_total") or 0) < min_charge_cost_total:
        return False
    metrics = _tenant_last_hour_metrics(summary)
    if int(metrics.get("rejected_jobs") or 0) < min_rejected_jobs:
        return False
    if text_chain_profile:
        profiles = _tenant_last_hour_text_chain_profiles(summary)
        if int(profiles.get(text_chain_profile) or 0) <= 0:
            return False
    return True


def _tenant_report_sort_value(item: dict[str, Any], sort_by: str) -> Any:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    summary = item.get("report_summary") if isinstance(item.get("report_summary"), dict) else {}
    billing = summary.get("billing_summary") if isinstance(summary.get("billing_summary"), dict) else {}
    metrics = _tenant_last_hour_metrics(summary)
    mapping = {
        "user_id": int(user.get("id") or 0),
        "charge_cost_total": int(billing.get("charge_cost_total") or 0),
        "rejected_jobs": int(metrics.get("rejected_jobs") or 0),
        "degraded_jobs": int(metrics.get("degraded_jobs") or 0),
        "queued_jobs": int(metrics.get("queued_jobs") or 0),
        "completed_jobs": int(metrics.get("completed_jobs") or 0),
        "failed_jobs": int(metrics.get("failed_jobs") or 0),
        "download_count": int(metrics.get("download_count") or 0),
    }
    return mapping.get(sort_by, int(user.get("id") or 0))


def _tenant_rejection_codes(summary: dict[str, Any]) -> dict[str, int]:
    ops = summary.get("ops_summary") if isinstance(summary.get("ops_summary"), dict) else {}
    last_hour = ops.get("last_hour") if isinstance(ops.get("last_hour"), dict) else {}
    codes = last_hour.get("rejection_codes") if isinstance(last_hour.get("rejection_codes"), dict) else {}
    return {
        str(key).strip(): int(value or 0)
        for key, value in codes.items()
        if str(key).strip()
    }


def _tenant_usage_reports_payload(
    *,
    limit: int,
    before_user_id: int,
    offset: int,
    window_limit: int,
    email_query: str,
    warning_level: str,
    min_charge_cost_total: int,
    min_rejected_jobs: int,
    text_chain_profile: str,
    sort_by: str,
    sort_order: str,
) -> dict[str, Any]:
    normalized_limit = _normalize_page_limit(limit)
    normalized_offset = _normalize_offset(offset)
    normalized_window_limit = _normalize_page_limit(window_limit, default=100, max_limit=200)
    normalized_email_query = str(email_query or "").strip().lower()
    normalized_warning_level = _normalize_warning_level(warning_level)
    normalized_min_charge_cost_total = _normalize_metric_threshold(min_charge_cost_total)
    normalized_min_rejected_jobs = _normalize_metric_threshold(min_rejected_jobs)
    normalized_text_chain_profile = _normalize_text_chain_profile(text_chain_profile)
    normalized_sort_by = _normalize_sort_by(sort_by)
    normalized_sort_order = _normalize_sort_order(sort_order)
    use_window_query = bool(
        normalized_offset
        or normalized_email_query
        or normalized_warning_level
        or normalized_min_charge_cost_total
        or normalized_min_rejected_jobs
        or normalized_text_chain_profile
        or normalized_sort_by != "user_id"
        or normalized_sort_order != "desc"
        or normalized_window_limit != 100
    )
    if use_window_query:
        source_users = list_users(limit=normalized_window_limit)
        filtered_items = []
        for user in source_users:
            item = _build_tenant_report_item(user, _build_user_usage_report(user))
            if _tenant_report_matches_filters(
                item,
                email_query=normalized_email_query,
                warning_level=normalized_warning_level,
                min_charge_cost_total=normalized_min_charge_cost_total,
                min_rejected_jobs=normalized_min_rejected_jobs,
                text_chain_profile=normalized_text_chain_profile,
            ):
                filtered_items.append(item)
        filtered_items.sort(
            key=lambda item: (
                _tenant_report_sort_value(item, normalized_sort_by),
                int((item.get("user") or {}).get("id") or 0),
            ),
            reverse=(normalized_sort_order == "desc"),
        )
        items = filtered_items[normalized_offset : normalized_offset + normalized_limit]
        page_summary = _new_page_summary()
        for item in items:
            _accumulate_page_summary(page_summary, item)
        total_matched = len(filtered_items)
        return {
            "ok": True,
            "items": items,
            "page": {
                "mode": "window_query",
                "limit": normalized_limit,
                "offset": normalized_offset,
                "window_limit": normalized_window_limit,
                "has_more": normalized_offset + len(items) < total_matched,
                "next_offset": normalized_offset + len(items) if normalized_offset + len(items) < total_matched else None,
                "total_matched": total_matched,
                "scanned_users": len(source_users),
            },
            "filters": {
                "email_query": normalized_email_query,
                "warning_level": normalized_warning_level,
                "min_charge_cost_total": normalized_min_charge_cost_total,
                "min_rejected_jobs": normalized_min_rejected_jobs,
                "text_chain_profile": normalized_text_chain_profile,
            },
            "sort": {
                "sort_by": normalized_sort_by,
                "sort_order": normalized_sort_order,
                "sort_scope": "window_query",
            },
            "summary": page_summary,
        }

    page = list_users_page(
        limit=normalized_limit,
        before_id=int(before_user_id) if int(before_user_id or 0) > 0 else None,
    )
    items = []
    page_summary = _new_page_summary()
    for user in page.get("items") or []:
        item = _build_tenant_report_item(user, _build_user_usage_report(user))
        _accumulate_page_summary(page_summary, item)
        items.append(item)
    return {
        "ok": True,
        "items": items,
        "page": {
            "mode": "cursor",
            "limit": int(page.get("limit") or normalized_limit),
            "before_user_id": int(before_user_id or 0),
            "has_more": bool(page.get("has_more")),
            "next_before_user_id": page.get("next_before_user_id"),
        },
        "filters": {
            "email_query": "",
            "warning_level": "",
            "min_charge_cost_total": 0,
            "min_rejected_jobs": 0,
            "text_chain_profile": "",
        },
        "sort": {
            "sort_by": "user_id",
            "sort_order": "desc",
            "sort_scope": "cursor_page",
        },
        "summary": page_summary,
    }


def _tenant_usage_export_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload.get("items") or []:
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        summary = item.get("report_summary") if isinstance(item.get("report_summary"), dict) else {}
        admission = summary.get("admission") if isinstance(summary.get("admission"), dict) else {}
        billing = summary.get("billing_summary") if isinstance(summary.get("billing_summary"), dict) else {}
        metrics = _tenant_last_hour_metrics(summary)
        text_chain_profiles = _tenant_last_hour_text_chain_profiles(summary)
        rejection_codes = _tenant_rejection_codes(summary)
        rows.append(
            {
                "user_id": int(user.get("id") or 0),
                "email": str(user.get("email") or ""),
                "balance": int(user.get("balance") or 0),
                "daily_limit": int(user.get("daily_limit") or 0),
                "admission_allowed": bool(admission.get("allowed")),
                "warning_level": str(admission.get("warning_level") or ""),
                "next_action": str(admission.get("next_action") or ""),
                "charge_event_count": int(billing.get("charge_event_count") or 0),
                "charge_cost_total": int(billing.get("charge_cost_total") or 0),
                "queued_jobs_last_hour": int(metrics.get("queued_jobs") or 0),
                "rejected_jobs_last_hour": int(metrics.get("rejected_jobs") or 0),
                "degraded_jobs_last_hour": int(metrics.get("degraded_jobs") or 0),
                "completed_jobs_last_hour": int(metrics.get("completed_jobs") or 0),
                "failed_jobs_last_hour": int(metrics.get("failed_jobs") or 0),
                "download_count_last_hour": int(metrics.get("download_count") or 0),
                "text_chain_profiles_json": __import__("json").dumps(text_chain_profiles, ensure_ascii=False, sort_keys=True),
                "rejection_codes_json": __import__("json").dumps(rejection_codes, ensure_ascii=False, sort_keys=True),
            }
        )
    return rows


def _audit_ops_export(action: str, *, detail: dict[str, Any] | None = None) -> str:
    normalized_action = str(action or "").strip() or "ops_export_unknown"
    payload = dict(detail or {})
    payload.setdefault("component", "auth.ops_exports")
    return append_quota_policy_audit(
        action=normalized_action,
        detail=payload,
    )


def _normalize_export_format(value: str) -> str:
    fmt = str(value or "").strip().lower()
    if fmt in {"", "csv", "json"}:
        return fmt
    raise HTTPException(status_code=400, detail="export_format must be csv, json, or empty")


def _normalize_keep_latest(value: int) -> int:
    try:
        keep = int(value)
    except Exception:
        keep = 20
    return max(0, min(keep, 500))


def _normalize_older_than_hours(value: int) -> int:
    try:
        hours = int(value)
    except Exception:
        hours = 168
    return max(0, min(hours, 24 * 365))


def _ops_export_retention_confirm_ttl_seconds() -> int:
    raw = os.environ.get("ZF_AUTH_OPS_EXPORT_RETENTION_CONFIRM_TTL_SECONDS", "900")
    try:
        ttl = int(raw)
    except Exception:
        ttl = 900
    return max(60, min(ttl, 24 * 3600))


def _parse_utc_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _parse_confirm_generated_at(value: str) -> datetime | None:
    return _parse_utc_datetime(value)


def _ops_export_file_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    ts = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    suffix = path.suffix.lstrip(".").lower()
    mode = "unknown"
    parts = path.stem.split("-")
    if len(parts) >= 4 and parts[0] == "tenant_usage_reports":
        mode = parts[1]
    return {
        "path": str(path),
        "filename": path.name,
        "format": suffix,
        "mode": mode,
        "size_bytes": int(stat.st_size),
        "mtime_ts": float(stat.st_mtime),
        "mtime_iso": ts.isoformat(),
    }


def _list_ops_export_files(*, export_format: str = "", limit: int = 100) -> list[dict[str, Any]]:
    normalized_format = _normalize_export_format(export_format)
    AUTH_OPS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for path in AUTH_OPS_EXPORT_DIR.glob("tenant_usage_reports-*.*"):
        if not path.is_file():
            continue
        record = _ops_export_file_record(path)
        if normalized_format and record["format"] != normalized_format:
            continue
        records.append(record)
    records.sort(key=lambda item: (-float(item["mtime_ts"]), item["filename"]))
    return records[: _normalize_page_limit(limit, default=100, max_limit=500)]


def _ops_export_retention_plan(
    *,
    keep_latest: int,
    older_than_hours: int,
    export_format: str = "",
) -> dict[str, Any]:
    normalized_keep = _normalize_keep_latest(keep_latest)
    normalized_hours = _normalize_older_than_hours(older_than_hours)
    records = _list_ops_export_files(export_format=export_format, limit=500)
    cutoff_ts = None
    if normalized_hours > 0:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - (normalized_hours * 3600)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, record in enumerate(records):
        stale_by_count = idx >= normalized_keep if normalized_keep > 0 else True
        stale_by_age = cutoff_ts is not None and float(record["mtime_ts"]) <= cutoff_ts
        if not stale_by_count and not stale_by_age:
            continue
        key = str(record["path"])
        if key in seen:
            continue
        seen.add(key)
        candidates.append(record)
    return {
        "keep_latest": normalized_keep,
        "older_than_hours": normalized_hours,
        "export_format": _normalize_export_format(export_format),
        "total_exports": len(records),
        "prune_candidates": candidates,
    }


def _ops_export_retention_confirm_token(plan: dict[str, Any], *, confirm_generated_at: str) -> str:
    export_format = str(plan.get("export_format") or "")
    keep_latest = int(plan.get("keep_latest") or 0)
    older_than_hours = int(plan.get("older_than_hours") or 0)
    candidates = plan.get("prune_candidates") or []
    paths = sorted(str(item.get("path") or "") for item in candidates if str(item.get("path") or "").strip())
    payload = {
        "export_format": export_format,
        "keep_latest": keep_latest,
        "older_than_hours": older_than_hours,
        "confirm_generated_at": str(confirm_generated_at or ""),
        "candidate_count": len(paths),
        "paths": paths,
    }
    return hashlib.sha256(
        __import__("json").dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _ops_export_retention_used_tokens_file() -> Path:
    AUTH_OPS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return AUTH_OPS_EXPORT_DIR / ".retention_used_tokens.jsonl"


def _ops_export_retention_token_used(token: str) -> bool:
    target = str(token or "").strip()
    if not target:
        return False
    state_file = _ops_export_retention_used_tokens_file()
    if not state_file.exists():
        return False
    json_mod = __import__("json")
    for raw_line in state_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json_mod.loads(line)
        except Exception:
            continue
        if str(payload.get("confirm_token") or "").strip() == target:
            return True
    return False


def _record_ops_export_retention_token_use(
    *,
    confirm_token: str,
    confirm_generated_at: str,
    confirm_valid_until: str,
    export_format: str,
    keep_latest: int,
    older_than_hours: int,
    prune_candidates_count: int,
) -> str:
    state_file = _ops_export_retention_used_tokens_file()
    payload = {
        "confirm_token": str(confirm_token or "").strip(),
        "confirm_generated_at": str(confirm_generated_at or "").strip(),
        "confirm_valid_until": str(confirm_valid_until or "").strip(),
        "used_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "export_format": str(export_format or "").strip(),
        "keep_latest": int(keep_latest),
        "older_than_hours": int(older_than_hours),
        "prune_candidates_count": int(prune_candidates_count),
    }
    with state_file.open("a", encoding="utf-8") as fh:
        fh.write(__import__("json").dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return str(state_file)


def _read_ops_export_retention_token_records() -> list[dict[str, Any]]:
    state_file = _ops_export_retention_used_tokens_file()
    if not state_file.exists():
        return []
    records: list[dict[str, Any]] = []
    json_mod = __import__("json")
    now_ts = datetime.now(timezone.utc).timestamp()
    for raw_line in state_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json_mod.loads(line)
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        used_at_dt = _parse_utc_datetime(payload.get("used_at") or payload.get("confirm_generated_at") or "")
        confirm_valid_until_dt = _parse_utc_datetime(payload.get("confirm_valid_until") or "")
        record = dict(payload)
        record["_payload"] = dict(payload)
        record["_used_at_ts"] = used_at_dt.timestamp() if used_at_dt else 0.0
        record["_confirm_valid_until_ts"] = (
            confirm_valid_until_dt.timestamp() if confirm_valid_until_dt else None
        )
        record["used_at"] = used_at_dt.isoformat() if used_at_dt else ""
        record["confirm_valid_until"] = (
            confirm_valid_until_dt.isoformat() if confirm_valid_until_dt else str(payload.get("confirm_valid_until") or "")
        )
        record["is_expired"] = (
            confirm_valid_until_dt is not None and now_ts > confirm_valid_until_dt.timestamp()
        )
        records.append(record)
    records.sort(key=lambda item: (-float(item.get("_used_at_ts") or 0.0), str(item.get("confirm_token") or "")))
    return records


def _public_ops_export_retention_token_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "confirm_token": str(record.get("confirm_token") or ""),
        "confirm_generated_at": str(record.get("confirm_generated_at") or ""),
        "confirm_valid_until": str(record.get("confirm_valid_until") or ""),
        "used_at": str(record.get("used_at") or ""),
        "export_format": str(record.get("export_format") or ""),
        "keep_latest": int(record.get("keep_latest") or 0),
        "older_than_hours": int(record.get("older_than_hours") or 0),
        "prune_candidates_count": int(record.get("prune_candidates_count") or 0),
        "is_expired": bool(record.get("is_expired")),
    }


def _ops_export_confirm_token_retention_plan(
    *,
    keep_latest: int,
    older_than_hours: int,
) -> dict[str, Any]:
    normalized_keep = _normalize_keep_latest(keep_latest)
    normalized_hours = _normalize_older_than_hours(older_than_hours)
    state_file = _ops_export_retention_used_tokens_file()
    records = _read_ops_export_retention_token_records()
    cutoff_ts = None
    if normalized_hours > 0:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - (normalized_hours * 3600)
    prune_candidates: list[dict[str, Any]] = []
    retained_records: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        used_at_ts = float(record.get("_used_at_ts") or 0.0)
        stale_by_count = idx >= normalized_keep if normalized_keep > 0 else True
        stale_by_age = cutoff_ts is not None and used_at_ts > 0 and used_at_ts <= cutoff_ts
        if stale_by_count or stale_by_age:
            prune_candidates.append(_public_ops_export_retention_token_record(record))
            continue
        retained_records.append(record)
    return {
        "path": str(state_file),
        "exists": state_file.exists(),
        "keep_latest": normalized_keep,
        "older_than_hours": normalized_hours,
        "total_records": len(records),
        "prune_candidates": prune_candidates,
        "retained_records": retained_records,
    }


def _ops_export_summary(
    *,
    export_format: str = "",
    keep_latest: int = 20,
    older_than_hours: int = 168,
) -> dict[str, Any]:
    normalized_format = _normalize_export_format(export_format)
    records = _list_ops_export_files(export_format=normalized_format, limit=500)
    by_format: dict[str, int] = {}
    by_mode: dict[str, int] = {}
    total_size_bytes = 0
    oldest_record = None
    newest_record = None
    for record in records:
        fmt = str(record.get("format") or "unknown")
        mode = str(record.get("mode") or "unknown")
        by_format[fmt] = int(by_format.get(fmt) or 0) + 1
        by_mode[mode] = int(by_mode.get(mode) or 0) + 1
        total_size_bytes += int(record.get("size_bytes") or 0)
        if oldest_record is None or float(record.get("mtime_ts") or 0) < float(oldest_record.get("mtime_ts") or 0):
            oldest_record = record
        if newest_record is None or float(record.get("mtime_ts") or 0) > float(newest_record.get("mtime_ts") or 0):
            newest_record = record
    retention = _ops_export_retention_plan(
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
        export_format=normalized_format,
    )
    prune_candidates = retention.get("prune_candidates") or []
    prune_total_bytes = sum(int(item.get("size_bytes") or 0) for item in prune_candidates)
    now_ts = datetime.now(timezone.utc).timestamp()
    oldest_age_hours = None
    if isinstance(oldest_record, dict):
        oldest_age_hours = round(max(0.0, now_ts - float(oldest_record.get("mtime_ts") or 0.0)) / 3600.0, 3)
    newest_age_hours = None
    if isinstance(newest_record, dict):
        newest_age_hours = round(max(0.0, now_ts - float(newest_record.get("mtime_ts") or 0.0)) / 3600.0, 3)
    confirm_token_plan = _ops_export_confirm_token_retention_plan(
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    confirm_token_records = _read_ops_export_retention_token_records()
    confirm_token_state_file = _ops_export_retention_used_tokens_file()
    confirm_token_total_bytes = confirm_token_state_file.stat().st_size if confirm_token_state_file.exists() else 0
    oldest_used_record = confirm_token_records[-1] if confirm_token_records else None
    newest_used_record = confirm_token_records[0] if confirm_token_records else None
    expired_record_count = sum(1 for item in confirm_token_records if bool(item.get("is_expired")))
    summary_snapshot_records = _list_ops_export_summary_snapshots(limit=500)
    summary_snapshot_plan = _ops_export_summary_snapshot_retention_plan(
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    summary_snapshot_total_bytes = sum(int(item.get("size_bytes") or 0) for item in summary_snapshot_records)
    oldest_snapshot_record = summary_snapshot_records[-1] if summary_snapshot_records else None
    newest_snapshot_record = summary_snapshot_records[0] if summary_snapshot_records else None
    summary_snapshot_export_state = _ops_export_summary_snapshot_export_summary(
        limit=500,
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    return {
        "export_format": normalized_format,
        "total_exports": len(records),
        "total_size_bytes": total_size_bytes,
        "by_format": by_format,
        "by_mode": by_mode,
        "oldest_export": oldest_record,
        "newest_export": newest_record,
        "oldest_export_age_hours": oldest_age_hours,
        "newest_export_age_hours": newest_age_hours,
        "retention_preview": {
            "keep_latest": retention["keep_latest"],
            "older_than_hours": retention["older_than_hours"],
            "prune_candidates_count": len(prune_candidates),
            "prune_candidates_total_size_bytes": prune_total_bytes,
            "prune_candidates_preview": prune_candidates[:10],
        },
        "confirm_token_state": {
            "path": str(confirm_token_state_file),
            "exists": confirm_token_state_file.exists(),
            "record_count": len(confirm_token_records),
            "size_bytes": confirm_token_total_bytes,
            "expired_record_count": expired_record_count,
            "newest_used_at": str((newest_used_record or {}).get("used_at") or ""),
            "oldest_used_at": str((oldest_used_record or {}).get("used_at") or ""),
            "retention_preview": {
                "keep_latest": confirm_token_plan["keep_latest"],
                "older_than_hours": confirm_token_plan["older_than_hours"],
                "prune_candidates_count": len(confirm_token_plan["prune_candidates"]),
                "prune_candidates_preview": confirm_token_plan["prune_candidates"][:10],
            },
        },
        "summary_snapshot_state": {
            "path": str(_ops_export_summary_snapshot_dir()),
            "count": len(summary_snapshot_records),
            "size_bytes": summary_snapshot_total_bytes,
            "newest_snapshot": newest_snapshot_record,
            "oldest_snapshot": oldest_snapshot_record,
            "retention_preview": {
                "keep_latest": summary_snapshot_plan["keep_latest"],
                "older_than_hours": summary_snapshot_plan["older_than_hours"],
                "prune_candidates_count": len(summary_snapshot_plan["prune_candidates"]),
                "prune_candidates_preview": summary_snapshot_plan["prune_candidates"][:10],
            },
        },
        "summary_snapshot_export_state": {
            **summary_snapshot_export_state,
        },
    }


def _ops_export_summary_snapshot_path() -> Path:
    snapshot_dir = _ops_export_summary_snapshot_dir()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return snapshot_dir / f"ops_exports_summary-{ts}.json"


def _ops_export_summary_snapshot_dir() -> Path:
    configured = Path(AUTH_OPS_SUMMARY_SNAPSHOT_DIR)
    if configured == DEFAULT_AUTH_OPS_SUMMARY_SNAPSHOT_DIR:
        return Path(AUTH_OPS_EXPORT_DIR) / "summary_snapshots"
    return configured


def _ops_export_summary_snapshot_export_dir() -> Path:
    configured = Path(AUTH_OPS_SUMMARY_SNAPSHOT_EXPORT_DIR)
    if configured == DEFAULT_AUTH_OPS_SUMMARY_SNAPSHOT_EXPORT_DIR:
        return Path(AUTH_OPS_EXPORT_DIR) / "summary_snapshot_exports"
    return configured


def _ops_summary_snapshot_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    ts = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    return {
        "path": str(path),
        "filename": path.name,
        "size_bytes": int(stat.st_size),
        "mtime_ts": float(stat.st_mtime),
        "mtime_iso": ts.isoformat(),
    }


def _list_ops_export_summary_snapshots(*, limit: int = 100) -> list[dict[str, Any]]:
    snapshot_dir = _ops_export_summary_snapshot_dir()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in snapshot_dir.glob("ops_exports_summary-*.json"):
        if not path.is_file():
            continue
        records.append(_ops_summary_snapshot_record(path))
    records.sort(key=lambda item: (-float(item["mtime_ts"]), item["filename"]))
    return records[: _normalize_page_limit(limit, default=100, max_limit=500)]


def _ops_export_summary_snapshot_retention_plan(
    *,
    keep_latest: int,
    older_than_hours: int,
) -> dict[str, Any]:
    normalized_keep = _normalize_keep_latest(keep_latest)
    normalized_hours = _normalize_older_than_hours(older_than_hours)
    records = _list_ops_export_summary_snapshots(limit=500)
    cutoff_ts = None
    if normalized_hours > 0:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - (normalized_hours * 3600)
    prune_candidates: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        stale_by_count = idx >= normalized_keep if normalized_keep > 0 else True
        stale_by_age = cutoff_ts is not None and float(record["mtime_ts"]) <= cutoff_ts
        if stale_by_count or stale_by_age:
            prune_candidates.append(record)
    return {
        "path": str(_ops_export_summary_snapshot_dir()),
        "keep_latest": normalized_keep,
        "older_than_hours": normalized_hours,
        "total_snapshots": len(records),
        "prune_candidates": prune_candidates,
    }


def _ops_export_summary_snapshot_inventory(*, limit: int = 100) -> dict[str, Any]:
    items = _list_ops_export_summary_snapshots(limit=limit)
    total_size_bytes = sum(int(item.get("size_bytes") or 0) for item in items)
    return {
        "path": str(_ops_export_summary_snapshot_dir()),
        "count": len(items),
        "total_size_bytes": total_size_bytes,
        "items": items,
    }


def _ops_summary_snapshot_export_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    ts = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    return {
        "path": str(path),
        "filename": path.name,
        "format": path.suffix.lstrip(".").lower(),
        "size_bytes": int(stat.st_size),
        "mtime_ts": float(stat.st_mtime),
        "mtime_iso": ts.isoformat(),
    }


def _list_ops_export_summary_snapshot_exports(*, limit: int = 100) -> list[dict[str, Any]]:
    export_dir = _ops_export_summary_snapshot_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for path in export_dir.glob("summary_snapshot_inventory-*.*"):
        if not path.is_file():
            continue
        records.append(_ops_summary_snapshot_export_record(path))
    records.sort(key=lambda item: (-float(item["mtime_ts"]), item["filename"]))
    return records[: _normalize_page_limit(limit, default=100, max_limit=500)]


def _ops_export_summary_snapshot_export_inventory(*, limit: int = 100) -> dict[str, Any]:
    items = _list_ops_export_summary_snapshot_exports(limit=limit)
    total_size_bytes = sum(int(item.get("size_bytes") or 0) for item in items)
    by_format: dict[str, int] = {}
    for item in items:
        fmt = str(item.get("format") or "unknown")
        by_format[fmt] = int(by_format.get(fmt) or 0) + 1
    return {
        "path": str(_ops_export_summary_snapshot_export_dir()),
        "count": len(items),
        "total_size_bytes": total_size_bytes,
        "by_format": by_format,
        "items": items,
    }


def _ops_export_summary_snapshot_export_summary(
    *,
    limit: int = 100,
    keep_latest: int,
    older_than_hours: int,
) -> dict[str, Any]:
    inventory = _ops_export_summary_snapshot_export_inventory(limit=limit)
    items = list(inventory.get("items") or [])
    retention = _ops_export_summary_snapshot_export_retention_plan(
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    newest_record = items[0] if items else None
    oldest_record = items[-1] if items else None
    return {
        "path": str(_ops_export_summary_snapshot_export_dir()),
        "count": int(inventory.get("count") or 0),
        "size_bytes": int(inventory.get("total_size_bytes") or 0),
        "by_format": dict(inventory.get("by_format") or {}),
        "newest_export": newest_record,
        "oldest_export": oldest_record,
        "retention_preview": {
            "keep_latest": retention["keep_latest"],
            "older_than_hours": retention["older_than_hours"],
            "prune_candidates_count": len(retention["prune_candidates"]),
            "prune_candidates_preview": retention["prune_candidates"][:10],
        },
    }


def _ops_export_summary_snapshot_export_retention_plan(
    *,
    keep_latest: int,
    older_than_hours: int,
) -> dict[str, Any]:
    normalized_keep = _normalize_keep_latest(keep_latest)
    normalized_hours = _normalize_older_than_hours(older_than_hours)
    records = _list_ops_export_summary_snapshot_exports(limit=500)
    cutoff_ts = None
    if normalized_hours > 0:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - (normalized_hours * 3600)
    prune_candidates: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        stale_by_count = idx >= normalized_keep if normalized_keep > 0 else True
        stale_by_age = cutoff_ts is not None and float(record["mtime_ts"]) <= cutoff_ts
        if stale_by_count or stale_by_age:
            prune_candidates.append(record)
    return {
        "path": str(_ops_export_summary_snapshot_export_dir()),
        "keep_latest": normalized_keep,
        "older_than_hours": normalized_hours,
        "total_exports": len(records),
        "prune_candidates": prune_candidates,
    }


@router.post("/register")
def register(req: RegisterRequest):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="email already exists")
    user = create_user(req.email, req.password)
    token = _issue_token(user["id"])
    return {"ok": True, "user": {"id": user["id"], "email": user["email"], "balance": user["balance"]}, "token": token}


@router.post("/login")
def login(req: LoginRequest):
    user = verify_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = _issue_token(user["id"])
    return {"ok": True, "user": {"id": user["id"], "email": user["email"], "balance": user["balance"]}, "token": token}


@router.get("/me")
def me(authorization: Optional[str] = Header(default=None)):
    user = _get_user_from_token(authorization)
    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "balance": user["balance"],
            "daily_limit": user.get("daily_limit"),
        },
    }


@router.post("/topup")
def topup(req: TopupRequest, authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    balance = update_balance(user["id"], req.amount)
    return {"ok": True, "email": req.email, "balance": balance}


@router.post("/set_daily_limit")
def set_daily_limit(req: DailyLimitRequest, authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    limit = update_daily_limit(user["id"], req.limit)
    return {"ok": True, "email": req.email, "daily_limit": limit}


@router.get("/charges")
def charges(authorization: Optional[str] = Header(default=None), limit: int = 100):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    return {"ok": True, "items": list_charges(limit=limit)}


@router.get("/my_charges")
def my_charges(authorization: Optional[str] = Header(default=None), limit: int = 100):
    user = _get_user_from_token(authorization)
    return {"ok": True, "items": list_charges_by_user(user["id"], limit=limit)}


@router.get("/charge_summary")
def charge_summary(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    items = list_charges(limit=10000)
    total = sum(int(i.get("cost") or 0) for i in items)
    by_action = {}
    for it in items:
        act = it.get("action") or "unknown"
        by_action[act] = by_action.get(act, 0) + int(it.get("cost") or 0)
    return {"ok": True, "total": total, "by_action": by_action}


@router.get("/usage_summary")
def usage_summary(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    items = list_charges(limit=20000)
    by_user = {}
    by_action = {}
    for it in items:
        uid = it.get("user_id")
        act = it.get("action") or "unknown"
        by_user[uid] = by_user.get(uid, 0) + 1
        by_action[act] = by_action.get(act, 0) + 1
    return {"ok": True, "by_user": by_user, "by_action": by_action, "total_events": len(items)}


@router.get("/active_summary")
def active_summary(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    items = list_charges(limit=20000)
    now = datetime.utcnow().timestamp()
    day7 = now - 7 * 24 * 3600
    day30 = now - 30 * 24 * 3600
    u7 = set()
    u30 = set()
    for it in items:
        ts = it.get("ts")
        try:
            # ts is sqlite datetime string
            from datetime import datetime as _dt
            t = _dt.fromisoformat(ts).timestamp()
        except Exception:
            t = None
        if t is None:
            continue
        if t >= day7:
            u7.add(it.get("user_id"))
        if t >= day30:
            u30.add(it.get("user_id"))
    return {"ok": True, "active_7d": len(u7), "active_30d": len(u30)}


@router.get("/users")
def users(authorization: Optional[str] = Header(default=None), limit: int = 100):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    return {"ok": True, "items": list_users(limit=limit)}


@router.get("/export_csv")
def export_csv(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    users_data = list_users(limit=10000)
    charges = list_charges(limit=20000)
    from pathlib import Path
    import csv
    out_dir = Path("backend/data/auth")
    out_dir.mkdir(parents=True, exist_ok=True)
    users_csv = out_dir / "users_export.csv"
    charges_csv = out_dir / "charges_export.csv"

    with users_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "email", "balance", "daily_limit"])
        w.writeheader()
        for u in users_data:
            w.writerow(u)

    with charges_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "user_id", "action", "cost", "ts"])
        w.writeheader()
        for c in charges:
            w.writerow(c)

    return {"ok": True, "users_csv": str(users_csv), "charges_csv": str(charges_csv)}


@router.get("/tenant_usage_report")
def tenant_usage_report(
    user_id: int,
    session_id: str = "",
    workspace_dir: str = "",
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    user = get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    user_report = _build_user_usage_report(user, workspace_dir=str(workspace_dir or "").strip() or None)

    session_block = None
    sid = str(session_id or "").strip()
    wdir = str(workspace_dir or "").strip()
    if sid or wdir:
        resolved_workspace = str(resolve_workspace_dir(session_id=sid or None, workspace_dir=wdir or None, create=False))
        effective_session_id = sid or resolved_workspace.rsplit("/", 1)[-1]
        session_block = _build_session_usage_report(
            session_id=effective_session_id,
            workspace_dir=resolved_workspace,
        )

    return {
        "ok": True,
        "user": _user_public_payload(user),
        "user_report": user_report,
        "session_report": session_block,
    }


@router.get("/tenant_usage_reports")
def tenant_usage_reports(
    limit: int = 20,
    before_user_id: int = 0,
    offset: int = 0,
    window_limit: int = 100,
    email_query: str = "",
    warning_level: str = "",
    min_charge_cost_total: int = 0,
    min_rejected_jobs: int = 0,
    text_chain_profile: str = "",
    sort_by: str = "user_id",
    sort_order: str = "desc",
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    return _tenant_usage_reports_payload(
        limit=limit,
        before_user_id=before_user_id,
        offset=offset,
        window_limit=window_limit,
        email_query=email_query,
        warning_level=warning_level,
        min_charge_cost_total=min_charge_cost_total,
        min_rejected_jobs=min_rejected_jobs,
        text_chain_profile=text_chain_profile,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/tenant_usage_reports_export")
def tenant_usage_reports_export(
    export_format: str = "csv",
    limit: int = 20,
    before_user_id: int = 0,
    offset: int = 0,
    window_limit: int = 100,
    email_query: str = "",
    warning_level: str = "",
    min_charge_cost_total: int = 0,
    min_rejected_jobs: int = 0,
    text_chain_profile: str = "",
    sort_by: str = "user_id",
    sort_order: str = "desc",
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    normalized_format = str(export_format or "").strip().lower() or "csv"
    if normalized_format not in {"csv", "json"}:
        raise HTTPException(status_code=400, detail="export_format must be csv or json")
    payload = _tenant_usage_reports_payload(
        limit=limit,
        before_user_id=before_user_id,
        offset=offset,
        window_limit=window_limit,
        email_query=email_query,
        warning_level=warning_level,
        min_charge_cost_total=min_charge_cost_total,
        min_rejected_jobs=min_rejected_jobs,
        text_chain_profile=text_chain_profile,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    AUTH_OPS_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    mode = str((payload.get("page") or {}).get("mode") or "unknown")
    export_path = AUTH_OPS_EXPORT_DIR / f"tenant_usage_reports-{mode}-{ts}.{normalized_format}"
    if normalized_format == "json":
        export_path.write_text(
            __import__("json").dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        import csv

        rows = _tenant_usage_export_rows(payload)
        fieldnames = [
            "user_id",
            "email",
            "balance",
            "daily_limit",
            "admission_allowed",
            "warning_level",
            "next_action",
            "charge_event_count",
            "charge_cost_total",
            "queued_jobs_last_hour",
            "rejected_jobs_last_hour",
            "degraded_jobs_last_hour",
            "completed_jobs_last_hour",
            "failed_jobs_last_hour",
            "download_count_last_hour",
            "text_chain_profiles_json",
            "rejection_codes_json",
        ]
        with export_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    audit_path = _audit_ops_export(
        "ops_export_create",
        detail={
            "export_format": normalized_format,
            "export_path": str(export_path),
            "item_count": len(payload.get("items") or []),
            "page_mode": str((payload.get("page") or {}).get("mode") or ""),
            "filters": payload.get("filters") or {},
            "sort": payload.get("sort") or {},
        },
    )
    return {
        "ok": True,
        "export_format": normalized_format,
        "export_path": str(export_path),
        "item_count": len(payload.get("items") or []),
        "page": payload.get("page"),
        "filters": payload.get("filters"),
        "sort": payload.get("sort"),
        "summary": payload.get("summary"),
        "audit_path": audit_path,
    }


@router.get("/tenant_usage_reports_exports")
def tenant_usage_reports_exports(
    limit: int = 100,
    export_format: str = "",
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    records = _list_ops_export_files(
        export_format=export_format,
        limit=limit,
    )
    return {
        "ok": True,
        "items": records,
        "count": len(records),
        "export_format": _normalize_export_format(export_format),
    }


@router.get("/tenant_usage_reports_exports_summary")
def tenant_usage_reports_exports_summary(
    export_format: str = "",
    keep_latest: int = 20,
    older_than_hours: int = 168,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    summary = _ops_export_summary(
        export_format=export_format,
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    return {
        "ok": True,
        "summary": summary,
    }


@router.get("/tenant_usage_reports_exports_summary_snapshots")
def tenant_usage_reports_exports_summary_snapshots(
    limit: int = 100,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    inventory = _ops_export_summary_snapshot_inventory(limit=limit)
    return {"ok": True, **inventory}


@router.get("/tenant_usage_reports_exports_summary_snapshots_export")
def tenant_usage_reports_exports_summary_snapshots_export(
    export_format: str = "json",
    limit: int = 100,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    normalized_format = str(export_format or "").strip().lower() or "json"
    if normalized_format not in {"csv", "json"}:
        raise HTTPException(status_code=400, detail="export_format must be csv or json")
    inventory = _ops_export_summary_snapshot_inventory(limit=limit)
    export_dir = _ops_export_summary_snapshot_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    export_path = export_dir / f"summary_snapshot_inventory-{ts}.{normalized_format}"
    if normalized_format == "json":
        export_path.write_text(
            __import__("json").dumps({"ok": True, **inventory}, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    else:
        import csv

        fieldnames = ["filename", "path", "size_bytes", "mtime_iso"]
        with export_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for item in inventory["items"]:
                writer.writerow(
                    {
                        "filename": str(item.get("filename") or ""),
                        "path": str(item.get("path") or ""),
                        "size_bytes": int(item.get("size_bytes") or 0),
                        "mtime_iso": str(item.get("mtime_iso") or ""),
                    }
                )
    audit_path = _audit_ops_export(
        "ops_export_summary_snapshot_inventory_export",
        detail={
            "export_format": normalized_format,
            "export_path": str(export_path),
            "snapshot_count": int(inventory.get("count") or 0),
            "total_size_bytes": int(inventory.get("total_size_bytes") or 0),
        },
    )
    return {
        "ok": True,
        "export_format": normalized_format,
        "export_path": str(export_path),
        "snapshot_count": int(inventory.get("count") or 0),
        "total_size_bytes": int(inventory.get("total_size_bytes") or 0),
        "audit_path": audit_path,
    }


@router.get("/tenant_usage_reports_exports_summary_snapshot_exports")
def tenant_usage_reports_exports_summary_snapshot_exports(
    limit: int = 100,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    inventory = _ops_export_summary_snapshot_export_inventory(limit=limit)
    return {"ok": True, **inventory}


@router.get("/tenant_usage_reports_exports_summary_snapshot_exports_summary")
def tenant_usage_reports_exports_summary_snapshot_exports_summary(
    limit: int = 100,
    keep_latest: int = 20,
    older_than_hours: int = 168,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    summary = _ops_export_summary_snapshot_export_summary(
        limit=limit,
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    return {"ok": True, **summary}


@router.get("/tenant_usage_reports_exports_summary_export")
def tenant_usage_reports_exports_summary_export(
    export_format: str = "",
    keep_latest: int = 20,
    older_than_hours: int = 168,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    summary = _ops_export_summary(
        export_format=export_format,
        keep_latest=keep_latest,
        older_than_hours=older_than_hours,
    )
    snapshot_path = _ops_export_summary_snapshot_path()
    payload = {
        "ok": True,
        "snapshot_created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": summary,
    }
    snapshot_path.write_text(
        __import__("json").dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    audit_path = _audit_ops_export(
        "ops_export_summary_snapshot_create",
        detail={
            "snapshot_path": str(snapshot_path),
            "export_format": _normalize_export_format(export_format),
            "keep_latest": int(keep_latest),
            "older_than_hours": int(older_than_hours),
            "total_exports": int(summary.get("total_exports") or 0),
            "confirm_token_record_count": int(
                ((summary.get("confirm_token_state") or {}).get("record_count") or 0)
            ),
        },
    )
    return {
        "ok": True,
        "snapshot_path": str(snapshot_path),
        "summary": summary,
        "audit_path": audit_path,
    }


@router.post("/tenant_usage_reports_exports_summary_snapshots_retention")
def tenant_usage_reports_exports_summary_snapshots_retention(
    req: SummarySnapshotRetentionRequest,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    plan = _ops_export_summary_snapshot_retention_plan(
        keep_latest=req.keep_latest,
        older_than_hours=req.older_than_hours,
    )
    deleted_paths: list[str] = []
    if bool(req.execute):
        for record in plan["prune_candidates"]:
            path = Path(str(record["path"]))
            if not path.exists() or not path.is_file():
                continue
            path.unlink()
            deleted_paths.append(str(path))
    audit_action = (
        "ops_export_summary_snapshots_retention_execute"
        if bool(req.execute)
        else "ops_export_summary_snapshots_retention_preview"
    )
    audit_path = _audit_ops_export(
        audit_action,
        detail={
            "path": plan["path"],
            "keep_latest": plan["keep_latest"],
            "older_than_hours": plan["older_than_hours"],
            "total_snapshots": plan["total_snapshots"],
            "prune_candidates_count": len(plan["prune_candidates"]),
            "deleted_count": len(deleted_paths),
            "deleted_paths": deleted_paths,
        },
    )
    return {
        "ok": True,
        "mode": "execute" if bool(req.execute) else "preview",
        "path": plan["path"],
        "keep_latest": plan["keep_latest"],
        "older_than_hours": plan["older_than_hours"],
        "total_snapshots": plan["total_snapshots"],
        "prune_candidates_count": len(plan["prune_candidates"]),
        "prune_candidates": plan["prune_candidates"][:50],
        "deleted_count": len(deleted_paths),
        "deleted_paths": deleted_paths,
        "audit_path": audit_path,
    }


@router.post("/tenant_usage_reports_exports_summary_snapshot_exports_retention")
def tenant_usage_reports_exports_summary_snapshot_exports_retention(
    req: SummarySnapshotExportRetentionRequest,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    plan = _ops_export_summary_snapshot_export_retention_plan(
        keep_latest=req.keep_latest,
        older_than_hours=req.older_than_hours,
    )
    deleted_paths: list[str] = []
    if bool(req.execute):
        for record in plan["prune_candidates"]:
            path = Path(str(record["path"]))
            if not path.exists() or not path.is_file():
                continue
            path.unlink()
            deleted_paths.append(str(path))
    audit_action = (
        "ops_export_summary_snapshot_exports_retention_execute"
        if bool(req.execute)
        else "ops_export_summary_snapshot_exports_retention_preview"
    )
    audit_path = _audit_ops_export(
        audit_action,
        detail={
            "path": plan["path"],
            "keep_latest": plan["keep_latest"],
            "older_than_hours": plan["older_than_hours"],
            "total_exports": plan["total_exports"],
            "prune_candidates_count": len(plan["prune_candidates"]),
            "deleted_count": len(deleted_paths),
            "deleted_paths": deleted_paths,
        },
    )
    return {
        "ok": True,
        "mode": "execute" if bool(req.execute) else "preview",
        "path": plan["path"],
        "keep_latest": plan["keep_latest"],
        "older_than_hours": plan["older_than_hours"],
        "total_exports": plan["total_exports"],
        "prune_candidates_count": len(plan["prune_candidates"]),
        "prune_candidates": plan["prune_candidates"][:50],
        "deleted_count": len(deleted_paths),
        "deleted_paths": deleted_paths,
        "audit_path": audit_path,
    }


@router.post("/tenant_usage_reports_exports_retention")
def tenant_usage_reports_exports_retention(
    req: ExportRetentionRequest,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    plan = _ops_export_retention_plan(
        keep_latest=req.keep_latest,
        older_than_hours=req.older_than_hours,
        export_format=req.export_format,
    )
    ttl_seconds = _ops_export_retention_confirm_ttl_seconds()
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)
    confirm_generated_at_dt = now_utc
    if bool(req.execute):
        if not str(req.confirm_generated_at or "").strip():
            raise HTTPException(status_code=400, detail="confirm_generated_at required for execute")
        parsed_confirm_generated_at = _parse_confirm_generated_at(req.confirm_generated_at)
        if parsed_confirm_generated_at is None:
            raise HTTPException(status_code=400, detail="confirm_generated_at invalid")
        confirm_generated_at_dt = parsed_confirm_generated_at
    confirm_generated_at = confirm_generated_at_dt.isoformat()
    confirm_valid_until_dt = confirm_generated_at_dt + timedelta(seconds=ttl_seconds)
    confirm_valid_until = confirm_valid_until_dt.isoformat()
    confirm_token = _ops_export_retention_confirm_token(
        plan,
        confirm_generated_at=confirm_generated_at,
    )
    confirm_count = int(req.confirm_prune_candidates_count or 0)
    prune_candidates = plan["prune_candidates"]
    deleted_paths: list[str] = []
    confirm_state_path = str(_ops_export_retention_used_tokens_file())
    if bool(req.execute):
        if not prune_candidates:
            raise HTTPException(status_code=400, detail="no prune candidates available for execute")
        if now_utc > confirm_valid_until_dt:
            raise HTTPException(status_code=400, detail="confirm_token expired")
        if not str(req.confirm_token or "").strip():
            raise HTTPException(status_code=400, detail="confirm_token required for execute")
        if confirm_count != len(prune_candidates):
            raise HTTPException(status_code=400, detail="confirm_prune_candidates_count mismatch")
        if str(req.confirm_token).strip() != confirm_token:
            raise HTTPException(status_code=400, detail="confirm_token mismatch")
        if _ops_export_retention_token_used(confirm_token):
            raise HTTPException(status_code=400, detail="confirm_token already used")
        confirm_state_path = _record_ops_export_retention_token_use(
            confirm_token=confirm_token,
            confirm_generated_at=confirm_generated_at,
            confirm_valid_until=confirm_valid_until,
            export_format=plan["export_format"],
            keep_latest=plan["keep_latest"],
            older_than_hours=plan["older_than_hours"],
            prune_candidates_count=len(prune_candidates),
        )
        for record in prune_candidates:
            path = Path(str(record["path"]))
            if not path.exists() or not path.is_file():
                continue
            path.unlink()
            deleted_paths.append(str(path))
    audit_action = "ops_export_retention_execute" if bool(req.execute) else "ops_export_retention_preview"
    audit_path = _audit_ops_export(
        audit_action,
        detail={
            "keep_latest": plan["keep_latest"],
            "older_than_hours": plan["older_than_hours"],
            "export_format": plan["export_format"],
            "confirm_generated_at": confirm_generated_at,
            "confirm_valid_until": confirm_valid_until,
            "confirm_ttl_seconds": ttl_seconds,
            "confirm_state_path": confirm_state_path,
            "total_exports": plan["total_exports"],
            "prune_candidates_count": len(plan["prune_candidates"]),
            "deleted_count": len(deleted_paths),
            "deleted_paths": deleted_paths,
        },
    )
    return {
        "ok": True,
        "mode": "execute" if bool(req.execute) else "preview",
        "keep_latest": plan["keep_latest"],
        "older_than_hours": plan["older_than_hours"],
        "export_format": plan["export_format"],
        "total_exports": plan["total_exports"],
        "prune_candidates_count": len(prune_candidates),
        "prune_candidates": prune_candidates,
        "confirm_token": confirm_token,
        "confirm_generated_at": confirm_generated_at,
        "confirm_valid_until": confirm_valid_until,
        "confirm_ttl_seconds": ttl_seconds,
        "confirm_state_path": confirm_state_path,
        "confirm_prune_candidates_count": len(prune_candidates),
        "deleted_count": len(deleted_paths),
        "deleted_paths": deleted_paths,
        "audit_path": audit_path,
    }


@router.post("/tenant_usage_reports_exports_confirm_tokens_retention")
def tenant_usage_reports_exports_confirm_tokens_retention(
    req: ConfirmTokenRetentionRequest,
    authorization: Optional[str] = Header(default=None),
):
    _require_admin(authorization)
    plan = _ops_export_confirm_token_retention_plan(
        keep_latest=req.keep_latest,
        older_than_hours=req.older_than_hours,
    )
    deleted_count = 0
    state_file = _ops_export_retention_used_tokens_file()
    if bool(req.execute):
        retained_records = plan["retained_records"]
        if retained_records:
            with state_file.open("w", encoding="utf-8") as fh:
                for record in retained_records:
                    fh.write(
                        __import__("json").dumps(record["_payload"], ensure_ascii=False, sort_keys=True) + "\n"
                    )
        elif state_file.exists():
            state_file.unlink()
        deleted_count = len(plan["prune_candidates"])
    audit_action = (
        "ops_export_confirm_tokens_retention_execute"
        if bool(req.execute)
        else "ops_export_confirm_tokens_retention_preview"
    )
    audit_path = _audit_ops_export(
        audit_action,
        detail={
            "path": plan["path"],
            "keep_latest": plan["keep_latest"],
            "older_than_hours": plan["older_than_hours"],
            "total_records": plan["total_records"],
            "prune_candidates_count": len(plan["prune_candidates"]),
            "deleted_count": deleted_count,
        },
    )
    return {
        "ok": True,
        "mode": "execute" if bool(req.execute) else "preview",
        "path": plan["path"],
        "exists": Path(plan["path"]).exists(),
        "keep_latest": plan["keep_latest"],
        "older_than_hours": plan["older_than_hours"],
        "total_records": plan["total_records"],
        "prune_candidates_count": len(plan["prune_candidates"]),
        "prune_candidates": plan["prune_candidates"][:50],
        "deleted_count": deleted_count,
        "audit_path": audit_path,
    }


@router.post("/set_default_model")
def set_default_model(authorization: Optional[str] = Header(default=None), provider: str = "", model: str = ""):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    if not provider or not model:
        raise HTTPException(status_code=400, detail="provider and model required")
    # 写入到本地配置文件（避免直接改系统环境变量）
    from pathlib import Path
    import json
    cfg_path = Path("backend/data/autoplan/config.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cfg["default_provider"] = provider
    cfg["default_model"] = model
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "default_provider": provider, "default_model": model, "config_path": str(cfg_path)}


@router.post("/set_agent_roles")
def set_agent_roles(authorization: Optional[str] = Header(default=None), payload: dict = None):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    if not payload:
        raise HTTPException(status_code=400, detail="payload required")
    # 配置校验：必须包含 default + rules(list)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")
    if "default" not in payload or "rules" not in payload:
        raise HTTPException(status_code=400, detail="payload must include default and rules")
    if not isinstance(payload.get("rules"), list):
        raise HTTPException(status_code=400, detail="rules must be list")
    for r in payload.get("rules", []):
        if not isinstance(r, dict):
            raise HTTPException(status_code=400, detail="each rule must be object")
        if "match" not in r or "role" not in r:
            raise HTTPException(status_code=400, detail="each rule must include match and role")
        if not isinstance(r.get("match"), list) or not all(isinstance(x, str) for x in r.get("match")):
            raise HTTPException(status_code=400, detail="match must be list of strings")
        if not isinstance(r.get("role"), str) or not r.get("role"):
            raise HTTPException(status_code=400, detail="role must be non-empty string")
    from pathlib import Path
    import json
    cfg_path = Path("backend/data/autoplan/agent_roles.json")
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "config_path": str(cfg_path)}


@router.get("/get_agent_roles")
def get_agent_roles(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    from pathlib import Path
    import json
    cfg_path = Path("backend/data/autoplan/agent_roles.json")
    if not cfg_path.exists():
        return {"ok": True, "config": None}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        cfg = None
    return {"ok": True, "config": cfg}


@router.get("/quota_policy")
def get_quota_policy(authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    from backend.zhifei_autoplan.quota_policy import load_quota_policy

    policy = load_quota_policy()
    return {"ok": True, "policy": policy}


@router.post("/quota_policy")
def set_quota_policy(payload: dict | None = None, authorization: Optional[str] = Header(default=None)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=403, detail="admin key not configured")
    if not authorization or authorization != f"Bearer {ADMIN_KEY}":
        raise HTTPException(status_code=403, detail="admin key invalid")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be object")
    from backend.zhifei_autoplan.quota_policy import save_quota_policy

    try:
        saved = save_quota_policy(payload, actor="admin")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "policy": saved}
