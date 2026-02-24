from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Tuple

AUDIT_LOG_PATH = Path("backend/data/autoplan/v2/failfast_audit.jsonl")


class FailFastAuditError(Exception):
    def __init__(self, message: str, *, audit_result: Dict[str, Any]):
        super().__init__(message)
        self.audit_result = audit_result


def _normalize_text(text: str) -> str:
    return "".join(str(text or "").split())


def audit_against_index_matrix(index_matrix: Dict[str, Any], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_text = _normalize_text("\n".join(str(sec.get("content") or "") for sec in sections))
    checks: List[Dict[str, Any]] = []

    for item in index_matrix.get("index_matrix") or []:
        dimension = str(item.get("dimension") or "")
        keywords = [str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()][:16]
        hit_keywords = [kw for kw in keywords if _normalize_text(kw) in all_text]
        missing_keywords = [kw for kw in keywords if kw not in hit_keywords]

        # Boolean audit point per score item.
        ok = bool(hit_keywords)
        checks.append(
            {
                "dimension": dimension,
                "keywords": keywords,
                "hit_keywords": hit_keywords,
                "missing_keywords": missing_keywords,
                "ok": ok,
                "coverage_ratio": round(len(hit_keywords) / max(1, len(keywords)), 4),
            }
        )

    all_passed = all(check.get("ok") for check in checks) if checks else True
    return {
        "ok": all_passed,
        "checks": checks,
        "failed_count": sum(1 for check in checks if not check.get("ok")),
    }


def _append_audit_log(record: Dict[str, Any], *, log_path: Path = AUDIT_LOG_PATH) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def enforce_fail_fast(
    *,
    index_matrix: Dict[str, Any],
    sections: List[Dict[str, Any]],
    paragraph_cache: Dict[str, Any],
    agent_name: str,
    attempt: int,
    max_attempts: int,
    log_path: Path = AUDIT_LOG_PATH,
) -> Dict[str, Any]:
    audit_result = audit_against_index_matrix(index_matrix, sections)
    if audit_result.get("ok"):
        return audit_result

    paragraph_cache.clear()
    failures = [check for check in (audit_result.get("checks") or []) if not check.get("ok")]
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "agent": agent_name,
        "attempt": int(attempt),
        "max_attempts": int(max_attempts),
        "failed_points": failures,
        "event": "fail_fast_retry",
    }
    _append_audit_log(record, log_path=log_path)

    raise FailFastAuditError(
        f"agent={agent_name} failed audit checks: {len(failures)} points missing",
        audit_result=audit_result,
    )


def run_with_fail_fast_retry(
    *,
    generator: Callable[[int, Dict[str, Any]], List[Dict[str, Any]]],
    index_matrix: Dict[str, Any],
    paragraph_cache: Dict[str, Any],
    agent_name: str,
    max_attempts: int = 3,
    log_path: Path = AUDIT_LOG_PATH,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    last_error: FailFastAuditError | None = None

    for attempt in range(1, max(1, int(max_attempts)) + 1):
        sections = generator(attempt, paragraph_cache)
        try:
            audit_result = enforce_fail_fast(
                index_matrix=index_matrix,
                sections=sections,
                paragraph_cache=paragraph_cache,
                agent_name=agent_name,
                attempt=attempt,
                max_attempts=max_attempts,
                log_path=log_path,
            )
            return sections, audit_result
        except FailFastAuditError as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            continue

    if last_error is None:
        raise RuntimeError("fail-fast retry pipeline exited unexpectedly")
    raise last_error


async def run_with_fail_fast_retry_async(
    *,
    generator: Callable[[int, Dict[str, Any]], Awaitable[List[Dict[str, Any]]]],
    index_matrix: Dict[str, Any],
    paragraph_cache: Dict[str, Any],
    agent_name: str,
    max_attempts: int = 3,
    log_path: Path = AUDIT_LOG_PATH,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    last_error: FailFastAuditError | None = None

    for attempt in range(1, max(1, int(max_attempts)) + 1):
        sections = await generator(attempt, paragraph_cache)
        try:
            audit_result = enforce_fail_fast(
                index_matrix=index_matrix,
                sections=sections,
                paragraph_cache=paragraph_cache,
                agent_name=agent_name,
                attempt=attempt,
                max_attempts=max_attempts,
                log_path=log_path,
            )
            return sections, audit_result
        except FailFastAuditError as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            continue

    if last_error is None:
        raise RuntimeError("async fail-fast retry pipeline exited unexpectedly")
    raise last_error
