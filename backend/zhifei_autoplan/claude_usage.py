from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


SCHEMA_VERSION = "claude-cache-usage-v1"
DEFAULT_USAGE_PATH = Path("backend/data/autoplan/claude_usage/events.jsonl")
_WRITE_LOCK = threading.RLock()
_SAFE_TASK_RE = re.compile(r"[^a-z0-9_.:-]+")


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            payload = dump()
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
    return {
        key: getattr(value, key, None)
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
    }


def normalize_claude_usage(value: Any) -> Dict[str, Any]:
    """Normalize Anthropic usage, including responses from older SDKs.

    Anthropic's ``input_tokens`` excludes tokens read from or written to the
    prompt cache.  ``total_input_tokens`` is therefore the sum of all three
    input categories.
    """

    usage = _mapping(value)
    uncached = _non_negative_int(usage.get("input_tokens"))
    cache_write = _non_negative_int(usage.get("cache_creation_input_tokens"))
    cache_read = _non_negative_int(usage.get("cache_read_input_tokens"))
    output = _non_negative_int(usage.get("output_tokens"))
    total = uncached + cache_write + cache_read
    return {
        "input_tokens": uncached,
        "output_tokens": output,
        "cache_creation_input_tokens": cache_write,
        "cache_read_input_tokens": cache_read,
        "total_input_tokens": total,
        "cache_hit_ratio": round(cache_read / total, 6) if total else 0.0,
    }


def _model_prices(model: str) -> tuple[float, float, str]:
    """Return input/output USD per million tokens for current model families."""

    name = str(model or "").strip().lower().replace("_", "-")
    if "fable" in name or "mythos" in name:
        return 10.0, 50.0, "anthropic-2026-08"
    if "sonnet-5" in name:
        return 2.0, 10.0, "anthropic-2026-08"
    if (
        "claude-3-opus" in name
        or "opus-4-0" in name
        or "opus-4-1" in name
        or re.search(r"opus-4-20\d{6}", name)
    ):
        return 15.0, 75.0, "anthropic-2026-08"
    if "opus" in name:
        return 5.0, 25.0, "anthropic-2026-08"
    if "sonnet" in name:
        return 3.0, 15.0, "anthropic-2026-08"
    if "haiku-4-5" in name:
        return 1.0, 5.0, "anthropic-2026-08"
    if "haiku-3-5" in name:
        return 0.8, 4.0, "anthropic-2026-08"
    if "haiku-3" in name:
        return 0.25, 1.25, "anthropic-2026-08"
    # Unknown aliases remain observable.  Use a clearly-labelled conservative
    # estimate rather than silently reporting zero cost.
    return 3.0, 15.0, "conservative-fallback"


def estimate_claude_cost(model: str, usage: Any) -> Dict[str, Any]:
    normalized = normalize_claude_usage(usage)
    input_rate, output_rate, source = _model_prices(model)
    uncached = normalized["input_tokens"]
    cache_write = normalized["cache_creation_input_tokens"]
    cache_read = normalized["cache_read_input_tokens"]
    output = normalized["output_tokens"]
    input_cost = (
        uncached * input_rate
        + cache_write * input_rate * 1.25
        + cache_read * input_rate * 0.10
    ) / 1_000_000
    output_cost = output * output_rate / 1_000_000
    no_cache_cost = (
        normalized["total_input_tokens"] * input_rate + output * output_rate
    ) / 1_000_000
    actual = input_cost + output_cost
    savings = no_cache_cost - actual
    return {
        "estimated_cost_usd": round(actual, 8),
        "estimated_input_cost_usd": round(input_cost, 8),
        "estimated_output_cost_usd": round(output_cost, 8),
        "estimated_no_cache_cost_usd": round(no_cache_cost, 8),
        "estimated_savings_usd": round(savings, 8),
        "estimated_savings_ratio": round(savings / no_cache_cost, 6)
        if no_cache_cost
        else 0.0,
        "pricing_source": source,
        "input_usd_per_mtok": input_rate,
        "output_usd_per_mtok": output_rate,
    }


def _safe_project_id(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "unscoped"
    key = str(
        os.environ.get("ZF_PROJECT_ID_HASH_KEY")
        or os.environ.get("ZF_JWT_SECRET")
        or "zhifei-local-usage-v1"
    ).encode("utf-8", errors="ignore")
    digest = hmac.new(
        key,
        raw.encode("utf-8", errors="ignore"),
        hashlib.sha256,
    ).hexdigest()[:20]
    return f"project-{digest}"


def _safe_task_type(value: Any) -> str:
    raw = str(value or "generic_completion").strip().lower()
    cleaned = _SAFE_TASK_RE.sub("_", raw).strip("_.:-")[:80]
    return cleaned or "generic_completion"


def _usage_path(path: str | Path | None = None) -> Path:
    configured = str(os.environ.get("ZHIFEI_CLAUDE_USAGE_LOG") or "").strip()
    return Path(path) if path is not None else Path(configured) if configured else DEFAULT_USAGE_PATH


def record_claude_usage(
    *,
    model: str,
    usage: Any,
    duration_ms: int,
    project_id: Any = None,
    task_type: Any = None,
    status: str = "success",
    error_type: str | None = None,
    streamed: bool = False,
    cache_strategy: str = "disabled",
    path: str | Path | None = None,
) -> Dict[str, Any]:
    """Append one privacy-safe Claude usage event.

    No prompt, message, API key, response body, user content, or source-document
    text is accepted by this API, so those values cannot accidentally reach the
    observability log.
    """

    normalized = normalize_claude_usage(usage)
    cost = estimate_claude_cost(model, normalized)
    event: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "provider": "anthropic",
        "model": str(model or "unknown")[:160],
        "project_id": _safe_project_id(project_id),
        "task_type": _safe_task_type(task_type),
        "status": "success" if str(status).lower() == "success" else "error",
        "error_type": str(error_type or "")[:120] or None,
        "request_duration_ms": _non_negative_int(duration_ms),
        "streamed": bool(streamed),
        "cache_strategy": str(cache_strategy or "disabled")[:80],
        **normalized,
        **cost,
    }
    destination = _usage_path(path)
    try:
        line = (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        with _WRITE_LOCK:
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                destination.parent.chmod(0o700)
            except OSError:
                pass
            fd = os.open(destination, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                os.write(fd, line)
            finally:
                os.close(fd)
            try:
                destination.chmod(0o600)
            except OSError:
                pass
    except Exception:
        # Observability must never turn a successful model response into a
        # failed generation.  The normalized event remains available to caller.
        event["log_persisted"] = False
    else:
        event["log_persisted"] = True
    return event


def _iter_events(path: Path, *, limit: int) -> Iterable[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    rows: deque[Dict[str, Any]] = deque(maxlen=max(1, min(200_000, int(limit or 50_000))))
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if isinstance(item, dict) and item.get("schema_version") == SCHEMA_VERSION:
                    rows.append(item)
    except OSError:
        return []
    return list(rows)


def _empty_totals() -> Dict[str, Any]:
    return {
        "calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "input_tokens": 0,
        "total_input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_hit_ratio": 0.0,
        "request_duration_ms": 0,
        "estimated_cost_usd": 0.0,
        "estimated_no_cache_cost_usd": 0.0,
        "estimated_savings_usd": 0.0,
        "estimated_savings_ratio": 0.0,
    }


def _add_event(total: Dict[str, Any], event: Dict[str, Any]) -> None:
    total["calls"] += 1
    if event.get("status") == "success":
        total["successful_calls"] += 1
    else:
        total["failed_calls"] += 1
    for key in (
        "input_tokens",
        "total_input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "request_duration_ms",
    ):
        total[key] += _non_negative_int(event.get(key))
    for key in (
        "estimated_cost_usd",
        "estimated_no_cache_cost_usd",
        "estimated_savings_usd",
    ):
        try:
            total[key] += float(event.get(key) or 0.0)
        except (TypeError, ValueError):
            pass


def _finish_totals(total: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(total)
    total_input = _non_negative_int(out.get("total_input_tokens"))
    cache_read = _non_negative_int(out.get("cache_read_input_tokens"))
    no_cache = float(out.get("estimated_no_cache_cost_usd") or 0.0)
    savings = float(out.get("estimated_savings_usd") or 0.0)
    out["cache_hit_ratio"] = round(cache_read / total_input, 6) if total_input else 0.0
    out["estimated_cost_usd"] = round(float(out["estimated_cost_usd"]), 8)
    out["estimated_no_cache_cost_usd"] = round(no_cache, 8)
    out["estimated_savings_usd"] = round(savings, 8)
    out["estimated_savings_ratio"] = round(savings / no_cache, 6) if no_cache else 0.0
    return out


def claude_usage_stats(
    *,
    project_id: Any = None,
    task_type: Any = None,
    path: str | Path | None = None,
    limit: int = 50_000,
) -> Dict[str, Any]:
    project_filter = _safe_project_id(project_id) if str(project_id or "").strip() else None
    task_filter = _safe_task_type(task_type) if str(task_type or "").strip() else None
    rows = [
        row
        for row in _iter_events(_usage_path(path), limit=limit)
        if (project_filter is None or row.get("project_id") == project_filter)
        and (task_filter is None or row.get("task_type") == task_filter)
    ]
    totals = _empty_totals()
    groups: Dict[str, Dict[str, Dict[str, Any]]] = {
        "model": {},
        "project": {},
        "task": {},
    }
    for row in rows:
        _add_event(totals, row)
        for group, key in (
            ("model", str(row.get("model") or "unknown")),
            ("project", str(row.get("project_id") or "unscoped")),
            ("task", str(row.get("task_type") or "generic_completion")),
        ):
            bucket = groups[group].setdefault(key, _empty_totals())
            _add_event(bucket, row)

    def _group_rows(group: str, label: str) -> list[Dict[str, Any]]:
        return sorted(
            [{label: key, **_finish_totals(value)} for key, value in groups[group].items()],
            key=lambda item: (-int(item.get("total_input_tokens") or 0), str(item.get(label) or "")),
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "filters": {"project_id": project_filter, "task_type": task_filter},
        "totals": _finish_totals(totals),
        "by_model": _group_rows("model", "model"),
        "by_project": _group_rows("project", "project_id"),
        "by_task": _group_rows("task", "task_type"),
        "recent": [
            {
                key: row.get(key)
                for key in (
                    "recorded_at",
                    "model",
                    "project_id",
                    "task_type",
                    "status",
                    "total_input_tokens",
                    "output_tokens",
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                    "cache_hit_ratio",
                    "request_duration_ms",
                    "estimated_cost_usd",
                )
            }
            for row in rows[-50:]
        ],
    }
