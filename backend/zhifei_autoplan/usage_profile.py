from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.zhifei_autoplan.resource_audit import RESOURCE_AUDIT_FILE
from backend.zhifei_autoplan.workspace import workspace_paths, workspace_root


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _event_ts(value: Any) -> float | None:
    text = _clean_text(value)
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return __import__("datetime").datetime.fromisoformat(text).timestamp()
    except Exception:
        return None


def _iter_audit_files(*, scope: str, workspace_dir: str | None = None) -> List[Path]:
    scope_name = "user" if _clean_text(scope).lower() == "user" else "session"
    if scope_name == "session" and workspace_dir:
        return [workspace_paths(workspace_dir)["resource_usage_audit"]]
    files: List[Path] = []
    if scope_name == "user":
        try:
            for child in workspace_root().iterdir():
                if not child.is_dir():
                    continue
                files.append(child / "audit" / "resource_usage.jsonl")
        except Exception:
            pass
    else:
        files.append(RESOURCE_AUDIT_FILE)
    unique: List[Path] = []
    seen: set[str] = set()
    for path in files:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _iter_records(
    *,
    scope: str,
    workspace_dir: str | None = None,
    user_id: int | None = None,
    now_ts: float | None = None,
    max_age_seconds: int | None = None,
) -> Iterable[Dict[str, Any]]:
    now = float(now_ts or time.time())
    max_age = max_age_seconds if max_age_seconds and max_age_seconds > 0 else None
    for path in _iter_audit_files(scope=scope, workspace_dir=workspace_dir):
        if not path.exists():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict):
                continue
            if scope == "session":
                if workspace_dir and _clean_text(rec.get("workspace_dir")) not in {"", _clean_text(workspace_dir)}:
                    continue
            elif user_id is not None and rec.get("user_id") != user_id:
                continue
            ts = _event_ts(rec.get("ts"))
            if max_age is not None and ts is not None and max(0.0, now - ts) > max_age:
                continue
            yield rec


def _init_bucket(window_seconds: int, *, now_ts: float) -> Dict[str, Any]:
    return {
        "window_seconds": int(window_seconds),
        "window_hours": round(window_seconds / 3600.0, 2),
        "as_of_ts": float(now_ts),
        "event_count": 0,
        "llm_call_count": 0,
        "queued_jobs": 0,
        "rejected_jobs": 0,
        "completed_jobs": 0,
        "failed_jobs": 0,
        "download_count": 0,
        "degraded_jobs": 0,
        "input_tokens_total": 0,
        "output_tokens_total": 0,
        "total_tokens_total": 0,
        "latency_ms_total": 0,
        "latency_tracked_calls": 0,
        "cache_hit_calls": 0,
        "cached_tokens_total": 0,
        "providers": {},
        "rejection_codes": {},
        "text_chain_profiles": {},
    }


def _provider_bucket(bucket: Dict[str, Any], provider: str, model: str) -> Dict[str, Any]:
    key = f"{provider}::{model}"
    providers = bucket["providers"]
    row = providers.get(key)
    if row is None:
        row = {
            "provider": provider or None,
            "model": model or None,
            "call_count": 0,
            "total_tokens_total": 0,
            "latency_ms_total": 0,
        }
        providers[key] = row
    return row


def _apply_record(bucket: Dict[str, Any], rec: Dict[str, Any]) -> None:
    bucket["event_count"] += 1
    event = _clean_text(rec.get("event"))
    if event == "llm_section_generation":
        bucket["llm_call_count"] += 1
        input_tokens = _safe_int(rec.get("input_tokens"))
        output_tokens = _safe_int(rec.get("output_tokens"))
        total_tokens = _safe_int(rec.get("total_tokens"), input_tokens + output_tokens)
        latency_ms = _safe_int(rec.get("latency_ms"))
        cached_tokens = _safe_int(rec.get("cached_tokens"))
        bucket["input_tokens_total"] += input_tokens
        bucket["output_tokens_total"] += output_tokens
        bucket["total_tokens_total"] += total_tokens
        bucket["cached_tokens_total"] += cached_tokens
        if rec.get("cache_hit"):
            bucket["cache_hit_calls"] += 1
        if latency_ms > 0:
            bucket["latency_ms_total"] += latency_ms
            bucket["latency_tracked_calls"] += 1
        row = _provider_bucket(bucket, _clean_text(rec.get("provider")), _clean_text(rec.get("model")))
        row["call_count"] += 1
        row["total_tokens_total"] += total_tokens
        row["latency_ms_total"] += latency_ms
    elif event == "job_queued":
        bucket["queued_jobs"] += 1
        degrade_plan = rec.get("degrade_plan") if isinstance(rec.get("degrade_plan"), dict) else {}
        if bool(degrade_plan.get("applied")):
            bucket["degraded_jobs"] += 1
            profile_key = _clean_text(degrade_plan.get("text_chain_profile_after")) or _clean_text(rec.get("text_chain_profile")) or "degraded"
        else:
            profile_key = _clean_text(rec.get("text_chain_profile")) or _clean_text(degrade_plan.get("text_chain_profile_after")) or "default"
        profiles = bucket["text_chain_profiles"]
        profiles[profile_key] = _safe_int(profiles.get(profile_key)) + 1
    elif event == "job_rejected":
        bucket["rejected_jobs"] += 1
        code = _clean_text(rec.get("rejection_code")) or "unknown"
        rejection_codes = bucket["rejection_codes"]
        rejection_codes[code] = _safe_int(rejection_codes.get(code)) + 1
    elif event == "job_completed":
        bucket["completed_jobs"] += 1
    elif event == "job_failed":
        bucket["failed_jobs"] += 1
    elif event == "artifact_download":
        bucket["download_count"] += 1


def summarize_usage_profile(
    *,
    scope: str,
    workspace_dir: str | None = None,
    user_id: int | None = None,
    now_ts: float | None = None,
) -> Dict[str, Any]:
    scope_name = "user" if _clean_text(scope).lower() == "user" else "session"
    now = float(now_ts or time.time())
    windows = {
        "last_hour": _init_bucket(3600, now_ts=now),
        "last_day": _init_bucket(24 * 3600, now_ts=now),
    }
    max_age = max(item["window_seconds"] for item in windows.values())

    for rec in _iter_records(
        scope=scope_name,
        workspace_dir=workspace_dir,
        user_id=user_id,
        now_ts=now,
        max_age_seconds=max_age,
    ):
        ts = _event_ts(rec.get("ts"))
        age = max(0.0, now - ts) if ts is not None else None
        for bucket in windows.values():
            if age is not None and age > float(bucket["window_seconds"]):
                continue
            _apply_record(bucket, rec)

    for bucket in windows.values():
        providers = sorted(
            bucket["providers"].values(),
            key=lambda item: (
                -_safe_int(item.get("call_count")),
                _clean_text(item.get("provider")),
                _clean_text(item.get("model")),
            ),
        )
        bucket["providers"] = providers[:8]
        bucket["rejection_codes"] = dict(
            sorted(
                (bucket.get("rejection_codes") or {}).items(),
                key=lambda item: (-_safe_int(item[1]), _clean_text(item[0])),
            )[:8]
        )
        bucket["text_chain_profiles"] = dict(
            sorted(
                (bucket.get("text_chain_profiles") or {}).items(),
                key=lambda item: (-_safe_int(item[1]), _clean_text(item[0])),
            )[:8]
        )
        if bucket["latency_tracked_calls"] > 0:
            bucket["latency_ms_avg"] = round(
                float(bucket["latency_ms_total"]) / float(bucket["latency_tracked_calls"]),
                2,
            )

    return {
        "scope": scope_name,
        "workspace_dir": workspace_dir,
        "user_id": user_id,
        "windows": windows,
    }


def build_usage_warnings(
    *,
    usage: Dict[str, Any],
    limits: Dict[str, Any],
    requested_jobs: int,
    scope: str,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    scope_name = "user" if _clean_text(scope).lower() == "user" else "session"
    try:
        warning_ratio = max(0.5, min(0.99, float((policy or {}).get("warning_ratio") or 0.8)))
    except Exception:
        warning_ratio = 0.8

    warnings: List[Dict[str, Any]] = []
    for field, limit_key, code, message in (
        ("running_count", "running_limit", "running_capacity_near_limit", "当前并发任务数已接近上限。"),
        ("queued_count", "queued_limit", "queue_capacity_near_limit", "当前排队任务数已接近上限。"),
        ("active_count", "active_limit", "active_capacity_near_limit", "当前活跃任务总数已接近上限。"),
    ):
        limit_value = limits.get(limit_key)
        if limit_value is None:
            continue
        current = _safe_int(usage.get(field))
        projected = current + (requested_jobs if field != "running_count" else 0)
        threshold = max(1.0, float(limit_value) * warning_ratio)
        if projected >= threshold:
            warnings.append(
                {
                    "code": f"{scope_name}_{code}",
                    "message": message,
                    "current": current,
                    "projected": projected,
                    "limit": int(limit_value),
                    "ratio": round(projected / float(limit_value), 3) if float(limit_value) > 0 else None,
                }
            )

    usage_windows = usage.get("usage_profile", {}).get("windows") if isinstance(usage.get("usage_profile"), dict) else {}
    token_limit = _safe_int((policy or {}).get("tokens_last_hour_warning"), 0)
    if token_limit > 0 and isinstance(usage_windows, dict):
        last_hour = usage_windows.get("last_hour") if isinstance(usage_windows.get("last_hour"), dict) else {}
        tokens = _safe_int(last_hour.get("total_tokens_total"))
        if tokens >= max(1.0, token_limit * warning_ratio):
            warnings.append(
                {
                    "code": f"{scope_name}_tokens_last_hour_near_limit",
                    "message": "最近一小时 Token 消耗已接近预警阈值。",
                    "current": tokens,
                    "limit": token_limit,
                    "ratio": round(tokens / float(token_limit), 3) if token_limit > 0 else None,
                }
            )

    warning_level = "none"
    if warnings:
        max_ratio = max(float(item.get("ratio") or 0.0) for item in warnings)
        warning_level = "warning" if max_ratio >= 0.95 else "notice"

    return {
        "warning_ratio": warning_ratio,
        "warning_level": warning_level,
        "warnings": warnings,
    }
