from __future__ import annotations

import json
import re
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


def _normalize_dimension(value: str) -> str:
    return str(value or "").strip()


SEVERITY_RANK = {"minor": 1, "major": 2, "blocker": 3}
BLOCKER_DIMENSIONS = {"扣分点", "安全"}


def _derive_point_severity(*, dimension: str, missing_keywords: List[str], match_mode: str, source: str) -> str:
    dim = str(dimension or "").strip()
    miss_count = len([x for x in (missing_keywords or []) if str(x).strip()])
    mode = str(match_mode or "").strip().lower()
    src = str(source or "").strip().lower()
    if dim in BLOCKER_DIMENSIONS and (mode == "all" or src == "score_points"):
        return "blocker"
    if miss_count >= 2 or mode == "all":
        return "major"
    return "minor"


def _max_severity(values: List[str]) -> str:
    if not values:
        return "minor"
    ranked = sorted(values, key=lambda x: int(SEVERITY_RANK.get(str(x), 0)), reverse=True)
    return str(ranked[0])


def _extract_score_points(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    points: List[Dict[str, Any]] = []
    raw_points = item.get("score_points")
    if not isinstance(raw_points, list):
        raw_points = item.get("response_points")
    if isinstance(raw_points, list):
        for idx, point in enumerate(raw_points, start=1):
            if isinstance(point, dict):
                req = point.get("required_keywords")
                if not isinstance(req, list):
                    req = point.get("keywords")
                req_keywords = [str(k).strip() for k in (req or []) if str(k).strip()]
                points.append(
                    {
                        "point_id": str(point.get("point_id") or f"P{idx}"),
                        "description": str(point.get("description") or point.get("name") or ""),
                        "required_keywords": req_keywords,
                        "match_mode": str(point.get("match_mode") or "any").lower(),
                        "source": "score_points",
                    }
                )
            elif point is not None:
                text = str(point).strip()
                if text:
                    points.append(
                        {
                            "point_id": f"P{idx}",
                            "description": text,
                            "required_keywords": [text],
                            "match_mode": "any",
                            "source": "score_points",
                        }
                    )

    if points:
        return points

    keywords = [str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()][:16]
    if keywords:
        points.append(
            {
                "point_id": "KW-ANY",
                "description": "keyword_fallback_any_hit",
                "required_keywords": keywords,
                "match_mode": "any",
                "source": "keywords",
            }
        )
    return points


def _match_keywords(text: str, required_keywords: List[str], match_mode: str) -> Tuple[bool, List[str], List[str]]:
    norm_text = _normalize_text(text)
    required = [str(k).strip() for k in (required_keywords or []) if str(k).strip()]
    if not required:
        return False, [], []
    hit = [kw for kw in required if _normalize_text(kw) in norm_text]
    if str(match_mode or "any").lower() == "all":
        ok = len(hit) == len(required)
    else:
        ok = len(hit) >= 1
    missing = [kw for kw in required if kw not in hit]
    return ok, hit, missing


def audit_against_index_matrix(index_matrix: Dict[str, Any], sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_text_raw = "\n".join(str(sec.get("content") or "") for sec in sections)
    all_text = _normalize_text(all_text_raw)
    by_dimension_text: Dict[str, str] = {}
    for sec in sections:
        title = _normalize_dimension(sec.get("title") or "")
        if not title:
            continue
        by_dimension_text[title] = str(sec.get("content") or "")

    checks: List[Dict[str, Any]] = []

    for item in index_matrix.get("index_matrix") or []:
        dimension = _normalize_dimension(item.get("dimension") or "")
        section_text = by_dimension_text.get(dimension) or all_text_raw
        points = _extract_score_points(item)
        point_checks: List[Dict[str, Any]] = []
        for point in points:
            ok, hit, missing = _match_keywords(
                section_text,
                point.get("required_keywords") or [],
                str(point.get("match_mode") or "any"),
            )
            severity = (
                "minor"
                if ok
                else _derive_point_severity(
                    dimension=dimension,
                    missing_keywords=missing,
                    match_mode=str(point.get("match_mode") or "any"),
                    source=str(point.get("source") or "keywords"),
                )
            )
            point_checks.append(
                {
                    "point_id": point.get("point_id"),
                    "description": point.get("description"),
                    "required_keywords": point.get("required_keywords") or [],
                    "match_mode": point.get("match_mode") or "any",
                    "source": point.get("source") or "keywords",
                    "hit_keywords": hit,
                    "missing_keywords": missing,
                    "severity": severity,
                    "ok": bool(ok),
                }
            )

        hit_keywords: List[str] = []
        missing_keywords: List[str] = []
        for p in point_checks:
            hit_keywords.extend([str(k) for k in (p.get("hit_keywords") or []) if str(k)])
            missing_keywords.extend([str(k) for k in (p.get("missing_keywords") or []) if str(k)])
        hit_keywords = list(dict.fromkeys(hit_keywords))
        missing_keywords = list(dict.fromkeys(missing_keywords))
        ok = all(bool(p.get("ok")) for p in point_checks) if point_checks else False
        coverage_ratio = round(
            (sum(1 for p in point_checks if p.get("ok")) / max(1, len(point_checks))),
            4,
        )
        severity = _max_severity([str(p.get("severity") or "minor") for p in point_checks if not bool(p.get("ok"))])
        checks.append(
            {
                "dimension": dimension,
                "keywords": [str(k).strip() for k in (item.get("keywords") or []) if str(k).strip()][:16],
                "hit_keywords": hit_keywords,
                "missing_keywords": missing_keywords,
                "score_points": point_checks,
                "score_point_total": len(point_checks),
                "score_point_hit": sum(1 for p in point_checks if p.get("ok")),
                "ok": ok,
                "coverage_ratio": coverage_ratio,
                "severity": severity if not ok else "minor",
            }
        )

    all_passed = all(check.get("ok") for check in checks) if checks else True
    severity_summary = {"blocker": 0, "major": 0, "minor": 0}
    for check in checks:
        if bool(check.get("ok")):
            continue
        sev = str(check.get("severity") or "minor").strip().lower()
        if sev not in severity_summary:
            sev = "minor"
        severity_summary[sev] += 1
    return {
        "ok": all_passed,
        "checks": checks,
        "failed_count": sum(1 for check in checks if not check.get("ok")),
        "severity_summary": severity_summary,
        "has_blocker": bool(severity_summary["blocker"] > 0),
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
        paragraph_cache.pop("__last_failed_dimensions__", None)
        paragraph_cache.pop("__last_failed_points__", None)
        return audit_result

    failures = [check for check in (audit_result.get("checks") or []) if not check.get("ok")]
    failed_dimensions = [str(check.get("dimension") or "").strip() for check in failures if str(check.get("dimension") or "").strip()]
    failed_points: List[Dict[str, Any]] = []
    for check in failures:
        dim = str(check.get("dimension") or "").strip()
        for point in check.get("score_points") or []:
            if not point.get("ok"):
                failed_points.append(
                    {
                        "dimension": dim,
                        "point_id": point.get("point_id"),
                        "description": point.get("description"),
                        "missing_keywords": point.get("missing_keywords") or [],
                    }
                )

    paragraph_cache.clear()

    audit_result["failed_dimensions"] = failed_dimensions
    audit_result["failed_points"] = failed_points
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "agent": agent_name,
        "attempt": int(attempt),
        "max_attempts": int(max_attempts),
        "failed_dimensions": failed_dimensions,
        "failed_points_count": len(failed_points),
        "failed_points": failures,
        "severity_summary": audit_result.get("severity_summary") or {},
        "has_blocker": bool(audit_result.get("has_blocker")),
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
            paragraph_cache["__last_failed_dimensions__"] = list(exc.audit_result.get("failed_dimensions") or [])
            paragraph_cache["__last_failed_points__"] = list(exc.audit_result.get("failed_points") or [])
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
            paragraph_cache["__last_failed_dimensions__"] = list(exc.audit_result.get("failed_dimensions") or [])
            paragraph_cache["__last_failed_points__"] = list(exc.audit_result.get("failed_points") or [])
            if attempt >= max_attempts:
                break
            continue

    if last_error is None:
        raise RuntimeError("async fail-fast retry pipeline exited unexpectedly")
    raise last_error
