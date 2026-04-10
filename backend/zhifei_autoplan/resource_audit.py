from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.zhifei_autoplan.workspace import workspace_paths


RESOURCE_AUDIT_FILE = Path("backend/data/audit/resource_usage.jsonl")
RESOURCE_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)


def _audit_file(workspace_dir: str | None = None) -> Path:
    if workspace_dir:
        return workspace_paths(workspace_dir)["resource_usage_audit"]
    RESOURCE_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    return RESOURCE_AUDIT_FILE


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any) -> int | None:
    try:
        out = int(value)
    except Exception:
        return None
    return out if out >= 0 else None


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_token_usage(raw: Any) -> Dict[str, int] | None:
    if not isinstance(raw, dict):
        return None
    input_tokens = _safe_int(raw.get("input_tokens"))
    output_tokens = _safe_int(raw.get("output_tokens"))
    total_tokens = _safe_int(raw.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    out: Dict[str, int] = {}
    if input_tokens is not None:
        out["input_tokens"] = input_tokens
    if output_tokens is not None:
        out["output_tokens"] = output_tokens
    if total_tokens is not None:
        out["total_tokens"] = total_tokens
    return out or None


def normalize_attempt(raw: Any, *, section_title: str | None = None) -> Dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    token_usage = normalize_token_usage(raw.get("token_usage"))
    provider = _clean_text(raw.get("provider"))
    model = _clean_text(raw.get("model"))
    latency_ms = _safe_int(raw.get("latency_ms"))
    cached_tokens = _safe_int(raw.get("cached_tokens")) or 0
    attempt = {
        "attempt": max(1, _safe_int(raw.get("attempt")) or 1),
        "section_title": _clean_text(section_title or raw.get("section_title")),
        "provider": provider,
        "model": model,
        "request_id": _clean_text(raw.get("request_id")),
        "client_request_id": _clean_text(raw.get("client_request_id")),
        "used_key_alias": _clean_text(raw.get("used_key_alias")),
        "service_tier": _clean_text(raw.get("service_tier")),
        "latency_ms": latency_ms,
        "token_usage": token_usage,
        "cache_key": _clean_text(raw.get("cache_key")),
        "cache_hit": bool(raw.get("cache_hit", False)),
        "cached_tokens": cached_tokens,
        "error": _clean_text(raw.get("error")),
    }
    return attempt


def section_usage_attempts(section: Any) -> List[Dict[str, Any]]:
    if not isinstance(section, dict):
        return []
    title = _clean_text(section.get("title"))
    attempts = section.get("resource_usage_attempts")
    rows: List[Dict[str, Any]] = []
    if isinstance(attempts, list):
        for item in attempts:
            normalized = normalize_attempt(item, section_title=title)
            if normalized:
                rows.append(normalized)
    if rows:
        return rows
    normalized = normalize_attempt(section, section_title=title)
    if normalized and (
        normalized.get("provider")
        or normalized.get("model")
        or normalized.get("latency_ms") is not None
        or normalized.get("token_usage")
        or normalized.get("error")
    ):
        normalized["attempt"] = max(1, int(normalized.get("attempt") or 1))
        return [normalized]
    return []


def _provider_bucket_key(attempt: Dict[str, Any]) -> tuple[str, str]:
    return (
        str(attempt.get("provider") or "").strip(),
        str(attempt.get("model") or "").strip(),
    )


def summarize_attempts(attempts: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [item for item in attempts if isinstance(item, dict)]
    by_provider: Dict[tuple[str, str], Dict[str, Any]] = {}
    section_titles: set[str] = set()
    call_count = 0
    error_count = 0
    latency_ms_total = 0
    latency_tracked_calls = 0
    token_usage_tracked_calls = 0
    input_tokens_total = 0
    output_tokens_total = 0
    total_tokens_total = 0
    cache_hit_calls = 0
    cached_tokens_total = 0

    for item in rows:
        call_count += 1
        title = _clean_text(item.get("section_title"))
        if title:
            section_titles.add(title)
        provider_key = _provider_bucket_key(item)
        bucket = by_provider.setdefault(
            provider_key,
            {
                "provider": provider_key[0] or None,
                "model": provider_key[1] or None,
                "call_count": 0,
                "error_count": 0,
                "latency_ms_total": 0,
                "latency_tracked_calls": 0,
                "token_usage_tracked_calls": 0,
                "input_tokens_total": 0,
                "output_tokens_total": 0,
                "total_tokens_total": 0,
                "cache_hit_calls": 0,
                "cached_tokens_total": 0,
            },
        )
        bucket["call_count"] += 1

        if _clean_text(item.get("error")):
            error_count += 1
            bucket["error_count"] += 1

        latency_ms = _safe_int(item.get("latency_ms"))
        if latency_ms is not None:
            latency_ms_total += latency_ms
            latency_tracked_calls += 1
            bucket["latency_ms_total"] += latency_ms
            bucket["latency_tracked_calls"] += 1

        token_usage = normalize_token_usage(item.get("token_usage"))
        if token_usage:
            token_usage_tracked_calls += 1
            bucket["token_usage_tracked_calls"] += 1
            input_tokens = int(token_usage.get("input_tokens") or 0)
            output_tokens = int(token_usage.get("output_tokens") or 0)
            total_tokens = int(token_usage.get("total_tokens") or (input_tokens + output_tokens))
            input_tokens_total += input_tokens
            output_tokens_total += output_tokens
            total_tokens_total += total_tokens
            bucket["input_tokens_total"] += input_tokens
            bucket["output_tokens_total"] += output_tokens
            bucket["total_tokens_total"] += total_tokens

        if bool(item.get("cache_hit", False)):
            cache_hit_calls += 1
            bucket["cache_hit_calls"] += 1
        cached_tokens = _safe_int(item.get("cached_tokens")) or 0
        cached_tokens_total += cached_tokens
        bucket["cached_tokens_total"] += cached_tokens

    provider_rows = sorted(
        by_provider.values(),
        key=lambda item: (
            str(item.get("provider") or ""),
            str(item.get("model") or ""),
        ),
    )

    summary = {
        "call_count": call_count,
        "section_count": len(section_titles),
        "error_count": error_count,
        "latency_ms_total": latency_ms_total,
        "latency_tracked_calls": latency_tracked_calls,
        "token_usage_tracked_calls": token_usage_tracked_calls,
        "input_tokens_total": input_tokens_total,
        "output_tokens_total": output_tokens_total,
        "total_tokens_total": total_tokens_total,
        "cache_hit_calls": cache_hit_calls,
        "cached_tokens_total": cached_tokens_total,
        "providers": provider_rows,
    }
    if latency_tracked_calls > 0:
        summary["latency_ms_avg"] = round(latency_ms_total / latency_tracked_calls, 2)
    return summary


def summarize_sections(sections: Iterable[Any]) -> Dict[str, Any]:
    attempts: List[Dict[str, Any]] = []
    section_count = 0
    for section in sections:
        if isinstance(section, dict):
            section_count += 1
        attempts.extend(section_usage_attempts(section))
    summary = summarize_attempts(attempts)
    summary["section_count_declared"] = section_count
    return summary


def summarize_variants(variants: Iterable[Any]) -> Dict[str, Any]:
    variant_rows: List[Dict[str, Any]] = []
    all_attempts: List[Dict[str, Any]] = []
    variant_count = 0
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        variant_count += 1
        sections = variant.get("sections") if isinstance(variant.get("sections"), list) else []
        variant_attempts: List[Dict[str, Any]] = []
        for section in sections:
            variant_attempts.extend(section_usage_attempts(section))
        summary = summarize_attempts(variant_attempts)
        summary["variant_id"] = variant.get("variant_id")
        summary["topic"] = _clean_text(variant.get("topic"))
        summary["section_count_declared"] = len(sections)
        variant_rows.append(summary)
        all_attempts.extend(variant_attempts)
    overall = summarize_attempts(all_attempts)
    overall["variant_count"] = variant_count
    overall["variants"] = variant_rows
    return overall


def build_llm_usage_events(
    sections: Iterable[Any],
    *,
    session_id: str | None = None,
    workspace_dir: str | None = None,
    user_id: int | None = None,
    job_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    project_id: str | None = None,
    topic: str | None = None,
    variant_id: Any = None,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for section in sections:
        for attempt in section_usage_attempts(section):
            event = {
                "event": "llm_section_generation",
                "session_id": _clean_text(session_id),
                "workspace_dir": _clean_text(workspace_dir),
                "user_id": user_id,
                "job_id": _clean_text(job_id),
                "request_id": _clean_text(request_id),
                "trace_id": _clean_text(trace_id),
                "project_id": _clean_text(project_id),
                "topic": _clean_text(topic),
                "variant_id": variant_id,
                "section_title": _clean_text(attempt.get("section_title")),
                "attempt": int(attempt.get("attempt") or 1),
                "provider": _clean_text(attempt.get("provider")),
                "model": _clean_text(attempt.get("model")),
                "provider_request_id": _clean_text(attempt.get("request_id")),
                "client_request_id": _clean_text(attempt.get("client_request_id")),
                "used_key_alias": _clean_text(attempt.get("used_key_alias")),
                "service_tier": _clean_text(attempt.get("service_tier")),
                "latency_ms": _safe_int(attempt.get("latency_ms")),
                "token_usage": normalize_token_usage(attempt.get("token_usage")),
                "cache_hit": bool(attempt.get("cache_hit", False)),
                "cached_tokens": _safe_int(attempt.get("cached_tokens")) or 0,
                "cache_key": _clean_text(attempt.get("cache_key")),
                "error": _clean_text(attempt.get("error")),
            }
            events.append(event)
    return events


def append_resource_event(event: str, *, workspace_dir: str | None = None, **fields: Any) -> str:
    path = _audit_file(workspace_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    token_usage = normalize_token_usage(fields.get("token_usage"))
    rec: Dict[str, Any] = {
        "ts": _utc_iso(),
        "event": str(event or "").strip() or "unknown",
    }
    for key, value in fields.items():
        if key == "token_usage":
            continue
        rec[key] = value
    if token_usage:
        rec["token_usage"] = token_usage
        rec["input_tokens"] = token_usage.get("input_tokens", 0)
        rec["output_tokens"] = token_usage.get("output_tokens", 0)
        rec["total_tokens"] = token_usage.get("total_tokens", 0)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return str(path)


def append_resource_events(events: Iterable[Dict[str, Any]], *, workspace_dir: str | None = None) -> str | None:
    path: str | None = None
    for event in events:
        if not isinstance(event, dict):
            continue
        payload = dict(event)
        event_name = str(payload.pop("event", "")).strip() or "unknown"
        payload_workspace_dir = _clean_text(payload.pop("workspace_dir", None))
        path = append_resource_event(
            event_name,
            workspace_dir=workspace_dir or payload_workspace_dir,
            **payload,
        )
    return path
