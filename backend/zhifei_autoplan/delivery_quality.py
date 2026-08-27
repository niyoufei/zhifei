from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from backend.zhifei_autoplan.project_fact_ledger import (
    FORMAL_REQUIRED_FIELDS,
    validate_project_fact_ledger,
)

_SAFE_CONSISTENCY_RE = re.compile(
    r"(DECISION\s*:\s*PASS|未发现(?:实质性|明显|前后)?冲突|"
    r"无(?:实质性|明显)?冲突|no\s+(?:material\s+)?conflict)",
    re.IGNORECASE,
)
_CONFLICT_RE = re.compile(
    r"(DECISION\s*:\s*BLOCK|存在(?:实质性|明显|前后)?冲突|"
    r"发现(?:实质性|明显|前后)?冲突|不一致|相互矛盾|"
    r"conflict(?:s|ing)?\s+(?:found|detected)|inconsisten)",
    re.IGNORECASE,
)
_MACHINE_DECISION_RE = re.compile(
    r"^\s*DECISION\s*:\s*(PASS|BLOCK)\b",
    re.IGNORECASE,
)
_FORMAL_PARAMETER_STATUSES = frozenset({"verified", "derived", "approved"})
_FORMAL_PARAMETER_LABELS = {
    "planned_duration_days": ("总工期", "计划工期", "合同工期", "工期要求"),
    "resource_peak": ("资源峰值", "高峰投入", "人数峰值"),
    "critical_interval_days": ("关键线路间隔", "关键线路步距", "关键间隔"),
    "risk_inspection_frequency": ("风险检查频次", "检查频次", "巡检频次", "抽检频次"),
    "quality_threshold": ("质量阈值", "允许偏差", "验收阈值"),
    "deviation_action_deadline": ("偏差处置时限", "整改时限", "处置时限"),
}
_STALE_DEFAULT_PATTERNS = {
    "planned_duration_days": (r"(?<!\d)120\s*(?:日历)?天(?!\d)",),
    "resource_peak": (r"(?<!\d)80\s*人(?![\d当量])",),
    "critical_interval_days": (r"(?<!\d)3\s*天(?!\d)",),
    "risk_inspection_frequency": (r"(?<!\d)2\s*次\s*/\s*日(?!\d)",),
    "quality_threshold": (r"(?:偏差\s*)?(?:≤|<=)\s*5\s*mm(?!\w)",),
    "deviation_action_deadline": (
        r"(?:偏差处置时限\s*)?(?:≤|<=)?\s*4\s*h(?!\w)",
        r"(?:偏差处置时限\s*)?(?:≤|<=)?\s*4\s*小时(?!\w)",
    ),
}
_STALE_DEFAULT_TOKENS = {
    "planned_duration_days": {"120天", "120日历天"},
    "resource_peak": {"80人"},
    "critical_interval_days": {"3天"},
    "risk_inspection_frequency": {"2次/日"},
    "quality_threshold": {"≤5mm", "<=5mm", "偏差≤5mm", "偏差<=5mm"},
    "deviation_action_deadline": {"4h", "≤4h", "<=4h", "4小时", "≤4小时", "<=4小时"},
}
_GENERIC_REGISTRY_DEFAULT_PATTERNS = {
    "crew_size": r"(?<!\d)8\s*人\s*/\s*班(?!\d)",
    "excavator_allocation": r"(?<!\d)20\s*t\s*挖机\s*[（(]?\s*1\s*台\s*[）)]?",
    "work_segment_duration": r"(?<!\d)4\s*h\s*/\s*作业段(?!\w)",
}
_FULL_PARAMETER_LOCATOR_RE = re.compile(
    r"^(?P<file>[^#\r\n]+\.(?:pdf|docx?|xlsx?|xls|csv|ods|txt|dwg))"
    r"#p(?P<page>[1-9]\d*)_(?P<sha256>[0-9a-fA-F]{64})@(?P<offset>\d+)$",
    re.IGNORECASE,
)
_FILE_PARAMETER_LOCATOR_RE = re.compile(
    r"^[^#\r\n]+\.(?:pdf|docx?|xlsx?|xls|csv|ods|txt|dwg)(?:#|::).+",
    re.IGNORECASE,
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_APPROVED_AT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_APPROVAL_RECEIPT_FIELDS = (
    "receipt_id",
    "status",
    "project_id",
    "field",
    "value_digest",
    "summary",
    "approved_by",
    "approved_at",
)
_DERIVATION_CHECKS = frozenset(
    {
        "productivity_units_verified",
        "resource_allocations_verified",
        "dependencies_verified",
    }
)


def _canonical_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _issue(code: str, message: str, *, source: str, details: Any = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "code": code,
        "severity": "error",
        "source": source,
        "message": message,
    }
    if details not in (None, "", [], {}):
        row["details"] = details
    return row


def _fact_locator(fact: dict[str, Any]) -> str:
    evidence = fact.get("evidence") if isinstance(fact.get("evidence"), dict) else {}
    return str(evidence.get("locator") or evidence.get("file_name") or "").strip()


def _same_value(left: Any, right: Any) -> bool:
    return _canonical_digest({"value": left}) == _canonical_digest({"value": right})


def _evidence_digest_valid(evidence: dict[str, Any]) -> bool:
    claimed = str(evidence.get("evidence_digest") or "").strip().lower()
    payload = {key: value for key, value in evidence.items() if key != "evidence_digest"}
    return bool(_SHA256_RE.fullmatch(claimed) and claimed == _canonical_digest(payload))


def _file_evidence_errors(
    evidence: dict[str, Any], *, require_text_anchor: bool
) -> list[str]:
    errors: list[str] = []
    locator = str(evidence.get("locator") or "").strip()
    document_sha256 = str(
        evidence.get("document_sha256") or evidence.get("source_sha256") or ""
    ).strip().lower()
    file_name = str(evidence.get("file_name") or "").strip()
    locator_file = locator.split("#", 1)[0].split("::", 1)[0]
    if _FILE_PARAMETER_LOCATOR_RE.fullmatch(locator) is None:
        errors.append("file_locator_invalid")
    if _SHA256_RE.fullmatch(document_sha256) is None:
        errors.append("document_sha256_invalid")
    if file_name and locator_file != file_name:
        errors.append("file_name_locator_mismatch")
    if not _evidence_digest_valid(evidence):
        errors.append("evidence_digest_invalid")
    if require_text_anchor:
        page_text_sha256 = str(evidence.get("page_text_sha256") or "").strip()
        try:
            page = int(evidence.get("page"))
        except (TypeError, ValueError):
            page = 0
        has_global_range = False
        try:
            start = int(evidence.get("start"))
            end = int(evidence.get("end"))
            has_global_range = start >= 0 and end > start
        except (TypeError, ValueError):
            pass
        try:
            offset = int(evidence.get("offset"))
            has_offset = offset >= 0
        except (TypeError, ValueError):
            has_offset = False
        if page < 1:
            errors.append("page_invalid")
        if _SHA256_RE.fullmatch(page_text_sha256) is None:
            errors.append("page_text_sha256_invalid")
        if not has_global_range and not has_offset:
            errors.append("text_offset_invalid")
    return errors


def _approval_receipt_errors(
    field: str,
    fact: dict[str, Any],
    *,
    expected_project_id: str,
) -> list[str]:
    receipt = (
        fact.get("approval_receipt")
        if isinstance(fact.get("approval_receipt"), dict)
        else {}
    )
    errors: list[str] = []
    if any(not str(receipt.get(key) or "").strip() for key in _APPROVAL_RECEIPT_FIELDS):
        errors.append("approval_receipt_incomplete")
        return errors
    if str(receipt.get("status") or "").strip().lower() != "approved":
        errors.append("approval_receipt_not_approved")
    if str(receipt.get("field") or "").strip() != field:
        errors.append("approval_receipt_field_mismatch")
    if (
        not expected_project_id
        or str(receipt.get("project_id") or "").strip() != expected_project_id
    ):
        errors.append("approval_receipt_project_mismatch")
    expected_value_digest = _canonical_digest(
        {
            "field": field,
            "value": fact.get("value"),
            "unit": str(fact.get("unit") or "").strip(),
        }
    )
    claimed_value_digest = str(receipt.get("value_digest") or "").strip().lower()
    if claimed_value_digest != expected_value_digest:
        errors.append("approval_receipt_value_mismatch")
    if _APPROVED_AT_RE.fullmatch(str(receipt.get("approved_at") or "").strip()) is None:
        errors.append("approval_receipt_time_invalid")
    receipt_payload = {
        key: receipt.get(key) for key in _APPROVAL_RECEIPT_FIELDS
    }
    claimed_receipt_digest = str(receipt.get("receipt_digest") or "").strip().lower()
    if (
        _SHA256_RE.fullmatch(claimed_receipt_digest) is None
        or claimed_receipt_digest != _canonical_digest(receipt_payload)
    ):
        errors.append("approval_receipt_digest_invalid")
    return errors


def _derivation_receipt_errors(
    fact: dict[str, Any], *, expected_project_id: str
) -> list[str]:
    evidence = fact.get("evidence") if isinstance(fact.get("evidence"), dict) else {}
    receipt = (
        evidence.get("derivation_receipt")
        if isinstance(evidence.get("derivation_receipt"), dict)
        else {}
    )
    errors: list[str] = []
    checks = receipt.get("checks") if isinstance(receipt.get("checks"), dict) else {}
    if receipt.get("ready") is not True or receipt.get("schedule_fact_eligible") is not True:
        errors.append("derivation_receipt_not_ready")
    if str(receipt.get("status") or "").strip().lower() not in {"verified", "approved"}:
        errors.append("derivation_receipt_status_invalid")
    if (
        not expected_project_id
        or str(receipt.get("project_id") or "").strip() != expected_project_id
    ):
        errors.append("derivation_receipt_project_mismatch")
    locator = str(receipt.get("locator") or "").strip()
    if not locator or locator.startswith(("payload.", "project_fact_sources.")):
        errors.append("derivation_receipt_locator_invalid")
    if set(checks) != _DERIVATION_CHECKS or not all(
        checks.get(name) is True for name in _DERIVATION_CHECKS
    ):
        errors.append("derivation_receipt_checks_invalid")
    if receipt.get("schedule_fact_reasons") not in ([], ()):
        errors.append("derivation_receipt_reasons_present")
    payload = {key: value for key, value in receipt.items() if key != "receipt_digest"}
    claimed = str(receipt.get("receipt_digest") or "").strip().lower()
    if _SHA256_RE.fullmatch(claimed) is None or claimed != _canonical_digest(payload):
        errors.append("derivation_receipt_digest_invalid")
    if not _evidence_digest_valid(evidence):
        errors.append("evidence_digest_invalid")
    return errors


def _formal_fact_source_errors(
    field: str,
    fact: dict[str, Any],
    *,
    expected_project_id: str,
) -> list[str]:
    status = str(fact.get("status") or "").strip().lower()
    source_type = str(fact.get("source_type") or "").strip().lower()
    evidence = fact.get("evidence") if isinstance(fact.get("evidence"), dict) else {}
    errors: list[str] = []
    if field == "quality_threshold":
        if source_type == "reviewed_design":
            expected = _canonical_digest(fact.get("value"))
            claimed = str(evidence.get("source_sha256") or "").strip().lower()
            if status != "verified":
                errors.append("source_status_mismatch")
            if claimed != expected:
                errors.append("quality_bundle_digest_mismatch")
            if not _evidence_digest_valid(evidence):
                errors.append("evidence_digest_invalid")
            return errors
        if source_type in {"approved_resolution", "user_input"}:
            if status != "approved":
                errors.append("source_status_mismatch")
            errors.extend(_file_evidence_errors(evidence, require_text_anchor=False))
            errors.extend(
                _approval_receipt_errors(
                    field,
                    fact,
                    expected_project_id=expected_project_id,
                )
            )
            return errors
        errors.append("formal_source_invalid")
        return errors
    if source_type in {"tender", "clarification", "reviewed_design"}:
        if status != "verified":
            errors.append("source_status_mismatch")
        errors.extend(_file_evidence_errors(evidence, require_text_anchor=True))
    elif source_type == "boq":
        if status != "derived" or fact.get("source_id") != "boq-deterministic-schedule":
            errors.append("source_status_mismatch")
        errors.extend(
            _derivation_receipt_errors(
                fact,
                expected_project_id=expected_project_id,
            )
        )
    elif source_type in {"approved_resolution", "user_input"}:
        if status != "approved":
            errors.append("source_status_mismatch")
        errors.extend(_file_evidence_errors(evidence, require_text_anchor=False))
        errors.extend(
            _approval_receipt_errors(
                field,
                fact,
                expected_project_id=expected_project_id,
            )
        )
    else:
        errors.append("formal_source_invalid")
    return list(dict.fromkeys(errors))


def _normalized_text(value: Any) -> str:
    return (
        re.sub(r"\s+", "", str(value or ""))
        .replace("＜", "<")
        .replace("＞", ">")
        .replace("（", "(")
        .replace("）", ")")
    )


def _fact_value_tokens(field: str, fact: dict[str, Any]) -> list[str]:
    value = fact.get("value")
    if field == "quality_threshold" and isinstance(value, dict):
        # Process-bound thresholds are validated item-by-item below.  Treating
        # the bundle's JSON encoding as a body token would allow a serialized
        # dictionary to satisfy the formal gate without any usable statement.
        return []
    if isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        rendered = str(value if value is not None else "")
    unit = str(fact.get("unit") or "").strip()
    base = rendered if unit and rendered.endswith(unit) else f"{rendered}{unit}"
    tokens = [_normalized_text(base)]
    if field == "planned_duration_days" and unit in {"天", "日"}:
        tokens.append(_normalized_text(f"{rendered}日历天"))
    return [token for token in dict.fromkeys(tokens) if token]


def _process_quality_bundle_check(fact: dict[str, Any]) -> dict[str, Any]:
    value = fact.get("value")
    errors: list[dict[str, str]] = []
    items_out: list[dict[str, str]] = []
    if not isinstance(value, dict) or value.get("mode") != "process_bound":
        return {
            "ok": False,
            "errors": [{"item_id": "quality_threshold", "reason": "process_bound_bundle_required"}],
            "items": [],
        }
    raw_items = value.get("items") if isinstance(value.get("items"), list) else []
    if not raw_items:
        return {
            "ok": False,
            "errors": [{"item_id": "quality_threshold", "reason": "bundle_items_missing"}],
            "items": [],
        }
    seen: set[str] = set()
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            errors.append({"item_id": f"item-{index + 1}", "reason": "item_invalid"})
            continue
        item_id = str(raw.get("id") or "").strip()
        process = str(raw.get("process") or "").strip()
        metric = str(raw.get("metric") or "").strip()
        operator = str(raw.get("operator") or "").strip()
        item_value = raw.get("value")
        unit = str(raw.get("unit") or "").strip()
        status = str(raw.get("status") or "").strip().lower()
        source = str(raw.get("source") or "").strip()
        evidence = raw.get("evidence") if isinstance(raw.get("evidence"), dict) else {}
        locator = str(raw.get("locator") or evidence.get("locator") or "").strip()
        locator_match = _FULL_PARAMETER_LOCATOR_RE.fullmatch(locator)
        document_sha256 = str(
            raw.get("document_sha256") or evidence.get("document_sha256") or ""
        ).strip().lower()
        extract_text_sha256 = str(
            raw.get("extract_text_sha256")
            or evidence.get("extract_text_sha256")
            or ""
        ).strip().lower()
        page_text_sha256 = str(
            raw.get("page_text_sha256") or evidence.get("page_text_sha256") or ""
        ).strip().lower()
        match_text_sha256 = str(
            raw.get("match_text_sha256") or evidence.get("match_text_sha256") or ""
        ).strip().lower()
        reasons: list[str] = []
        if not item_id:
            reasons.append("id_missing")
        elif item_id in seen:
            reasons.append("id_duplicate")
        else:
            seen.add(item_id)
        if not process:
            reasons.append("process_missing")
        if not metric:
            reasons.append("metric_missing")
        if operator not in {"=", ">=", "≥", "<=", "≤", ">", "<"}:
            reasons.append("operator_invalid")
        if item_value in (None, "", [], {}):
            reasons.append("value_missing")
        if status not in _FORMAL_PARAMETER_STATUSES:
            reasons.append("status_invalid")
        if not source:
            reasons.append("source_missing")
        if locator_match is None:
            reasons.append("locator_invalid")
        if _SHA256_RE.fullmatch(document_sha256) is None:
            reasons.append("document_sha256_invalid")
        if _SHA256_RE.fullmatch(extract_text_sha256) is None:
            reasons.append("extract_text_sha256_invalid")
        if _SHA256_RE.fullmatch(page_text_sha256) is None:
            reasons.append("page_text_sha256_invalid")
        if _SHA256_RE.fullmatch(match_text_sha256) is None:
            reasons.append("match_text_sha256_invalid")
        try:
            page = int(raw.get("page", evidence.get("page")))
            offset = int(raw.get("offset", evidence.get("offset")))
            end = int(raw.get("end", evidence.get("end")))
            page_start_offset = int(
                raw.get("page_start_offset", evidence.get("page_start_offset"))
            )
            page_end_offset = int(
                raw.get("page_end_offset", evidence.get("page_end_offset"))
            )
            page_match_start = int(
                raw.get("page_match_start", evidence.get("page_match_start"))
            )
            page_match_end = int(
                raw.get("page_match_end", evidence.get("page_match_end"))
            )
        except (TypeError, ValueError):
            reasons.append("reversible_offsets_invalid")
        else:
            if (
                locator_match is None
                or page != int(locator_match.group("page"))
                or offset != int(locator_match.group("offset"))
                or document_sha256 != locator_match.group("sha256").lower()
            ):
                reasons.append("locator_evidence_mismatch")
            if (
                end <= offset
                or page_start_offset < 0
                or page_end_offset <= page_start_offset
                or not page_start_offset <= offset < end <= page_end_offset
                or page_match_start != offset - page_start_offset
                or page_match_end != end - page_start_offset
                or page_match_end <= page_match_start
            ):
                reasons.append("reversible_offsets_invalid")
        if reasons:
            errors.extend(
                {"item_id": item_id or f"item-{index + 1}", "reason": reason}
                for reason in reasons
            )
            continue
        rendered_value = f"{operator}{item_value}{unit}"
        items_out.append(
            {
                "id": item_id,
                "process": process,
                "metric": metric,
                "value_token": _normalized_text(rendered_value),
                "locator": _normalized_text(locator),
            }
        )
    return {"ok": not errors and len(items_out) == len(raw_items), "errors": errors, "items": items_out}


def _process_quality_body_check(
    fact: dict[str, Any],
    normalized_body: str,
) -> dict[str, Any]:
    bundle = _process_quality_bundle_check(fact)
    missing: list[str] = []
    unlocated: list[str] = []
    for item in bundle["items"]:
        process = _normalized_text(item["process"])
        metric = _normalized_text(item["metric"])
        value_token = str(item["value_token"])
        locator = str(item["locator"])
        bound = False
        statement_seen = False
        start = 0
        while process and (position := normalized_body.find(process, start)) >= 0:
            vicinity = normalized_body[
                max(0, position - 120) : position + len(process) + 720
            ]
            if metric in vicinity and value_token in vicinity:
                statement_seen = True
                if f"证据:{locator}" in vicinity:
                    bound = True
                    break
            start = position + len(process)
        if not bound:
            missing.append(item["id"])
            if statement_seen:
                unlocated.append(item["id"])
    return {
        "ok": bool(bundle["ok"] and not missing and not unlocated),
        "bundle_errors": list(bundle["errors"]),
        "missing_items": missing,
        "unlocated_items": unlocated,
    }


def _formal_parameter_body_check(
    sections: list[dict[str, Any]] | None,
    project_fact_ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    """Bind every formal parameter statement to its ledger value and locator."""

    rows = [row for row in (sections or []) if isinstance(row, dict)]
    body = "\n".join(
        f"{row.get('title') or ''!s}\n{row.get('content') or ''!s}" for row in rows
    )
    normalized_body = _normalized_text(body)
    ledger = dict(project_fact_ledger or {})
    facts = ledger.get("facts") if isinstance(ledger.get("facts"), dict) else {}
    missing_bindings: list[str] = []
    conflicting_defaults: list[dict[str, str]] = []
    unlocated_statements: list[str] = []
    unverified_registry_defaults: list[dict[str, str]] = []
    process_quality_check: dict[str, Any] = {
        "ok": False,
        "bundle_errors": [],
        "missing_items": [],
        "unlocated_items": [],
    }

    accepted_fact_bindings: list[tuple[str, str]] = []
    for fact in facts.values():
        if not isinstance(fact, dict):
            continue
        if str(fact.get("status") or "").strip().lower() not in _FORMAL_PARAMETER_STATUSES:
            continue
        locator = _normalized_text(_fact_locator(fact))
        if not locator:
            continue
        for token in _fact_value_tokens(str(fact.get("field") or ""), fact):
            accepted_fact_bindings.append((token, locator))

    for field in FORMAL_REQUIRED_FIELDS:
        fact = facts.get(field) if isinstance(facts.get(field), dict) else {}
        locator = _normalized_text(_fact_locator(fact))
        labels = tuple(_normalized_text(value) for value in _FORMAL_PARAMETER_LABELS[field])
        tokens = _fact_value_tokens(field, fact)
        bound = False
        statement_seen = False
        if field == "quality_threshold" and isinstance(fact.get("value"), dict):
            process_quality_check = _process_quality_body_check(
                fact, normalized_body
            )
            bound = bool(process_quality_check.get("ok"))
            statement_seen = bool(
                process_quality_check.get("missing_items")
                or process_quality_check.get("unlocated_items")
            )
        else:
            for token in tokens:
                start = 0
                while token and (position := normalized_body.find(token, start)) >= 0:
                    before = normalized_body[max(0, position - 140) : position]
                    vicinity = normalized_body[
                        max(0, position - 180) : position + len(token) + 360
                    ]
                    labelled = any(label in before[-120:] or label in vicinity[:180] for label in labels)
                    if labelled:
                        statement_seen = True
                        if locator and f"证据:{locator}" in vicinity:
                            bound = True
                    start = position + len(token)
        if not bound:
            missing_bindings.append(field)
            if statement_seen:
                unlocated_statements.append(field)

        expected_is_default = bool(set(tokens) & _STALE_DEFAULT_TOKENS[field])
        for pattern in _STALE_DEFAULT_PATTERNS[field]:
            for match in re.finditer(pattern, body, flags=re.IGNORECASE):
                default_token = _normalized_text(match.group(0))
                context = _normalized_text(
                    body[max(0, match.start() - 140) : match.end() + 140]
                )
                has_parameter_context = any(
                    label in context for label in labels
                ) or any(marker in context for marker in ("旧口径", "默认值", "项目参数"))
                if not has_parameter_context:
                    continue
                if not expected_is_default:
                    conflicting_defaults.append(
                        {"field": field, "default": default_token, "reason": "ledger_value_conflict"}
                    )
                    break
                vicinity = _normalized_text(
                    body[max(0, match.start() - 180) : match.end() + 360]
                )
                if not locator or f"证据:{locator}" not in vicinity:
                    unlocated_statements.append(field)
            else:
                continue
            break

    for name, pattern in _GENERIC_REGISTRY_DEFAULT_PATTERNS.items():
        for match in re.finditer(pattern, body, flags=re.IGNORECASE):
            matched_token = _normalized_text(match.group(0))
            vicinity = _normalized_text(
                body[max(0, match.start() - 220) : match.end() + 360]
            )
            approved_fact_bound = any(
                token == matched_token
                and f"证据:{locator}" in vicinity
                for token, locator in accepted_fact_bindings
            )
            # An unrelated drawing/BoQ locator nearby cannot promote a
            # registry default into a project fact.  The exact value must be
            # present in the accepted ledger and bound to that fact's locator.
            if not approved_fact_bound:
                unverified_registry_defaults.append(
                    {"name": name, "value": _normalized_text(match.group(0))}
                )

    available = bool(rows and normalized_body)
    return {
        "pass": bool(
            available
            and not missing_bindings
            and not conflicting_defaults
            and not unlocated_statements
            and not unverified_registry_defaults
        ),
        "available": available,
        "required_fields": list(FORMAL_REQUIRED_FIELDS),
        "missing_bindings": sorted(set(missing_bindings)),
        "unlocated_statements": sorted(set(unlocated_statements)),
        "conflicting_defaults": conflicting_defaults,
        "unverified_registry_defaults": unverified_registry_defaults,
        "process_quality_bundle": process_quality_check,
    }


def _formal_project_parameter_check(
    parameter_report: dict[str, Any] | None,
    project_fact_ledger: dict[str, Any] | None,
) -> dict[str, Any]:
    """Revalidate the bound receipt instead of trusting caller summary booleans."""

    report = dict(parameter_report or {})
    ledger = dict(project_fact_ledger or {})
    ledger_validation = validate_project_fact_ledger(ledger)
    readiness = (
        ledger.get("formal_parameter_readiness")
        if isinstance(ledger.get("formal_parameter_readiness"), dict)
        else {}
    )
    facts = ledger.get("facts") if isinstance(ledger.get("facts"), dict) else {}
    ledger_project_id = str(ledger.get("project_id") or "").strip()
    required_fields = [
        str(value).strip()
        for value in (readiness.get("required_fields") or [])
        if str(value).strip()
    ]
    ready_fields = {
        str(value).strip()
        for value in (readiness.get("ready_fields") or [])
        if str(value).strip()
    }
    resolved = [dict(row) for row in (report.get("resolved") or []) if isinstance(row, dict)]
    resolved_fields = [
        str(row.get("field") or "").strip()
        for row in resolved
        if str(row.get("field") or "").strip()
    ]
    resolved_by_field = {
        str(row.get("field") or "").strip(): row
        for row in resolved
        if str(row.get("field") or "").strip()
    }

    unresolved_fields: list[str] = []
    invalid_statuses: list[dict[str, str]] = []
    receipt_mismatches: list[dict[str, str]] = []
    source_evidence_errors: list[dict[str, Any]] = []
    quality_fact = (
        facts.get("quality_threshold")
        if isinstance(facts.get("quality_threshold"), dict)
        else {}
    )
    structured_quality_validation = _process_quality_bundle_check(quality_fact)
    for field in required_fields:
        fact = facts.get(field) if isinstance(facts.get(field), dict) else {}
        receipt = resolved_by_field.get(field, {})
        status = str(fact.get("status") or "missing").strip().lower()
        value = fact.get("value")
        locator = _fact_locator(fact)
        if status not in _FORMAL_PARAMETER_STATUSES:
            invalid_statuses.append({"field": field, "status": status or "missing"})
        source_errors = _formal_fact_source_errors(
            field,
            fact,
            expected_project_id=ledger_project_id,
        )
        if source_errors:
            source_evidence_errors.append(
                {"field": field, "reasons": source_errors}
            )
        if field not in ready_fields or value in (None, "", [], {}):
            unresolved_fields.append(field)
        if not receipt:
            receipt_mismatches.append({"field": field, "reason": "receipt_missing"})
            continue
        mismatch_reasons: list[str] = []
        if not _same_value(receipt.get("value"), value):
            mismatch_reasons.append("value")
        if str(receipt.get("unit") or "").strip() != str(fact.get("unit") or "").strip():
            mismatch_reasons.append("unit")
        if str(receipt.get("status") or "").strip().lower() != status:
            mismatch_reasons.append("status")
        if not locator or str(receipt.get("locator") or "").strip() != locator:
            mismatch_reasons.append("locator")
        if str(receipt.get("source") or "").strip() != str(fact.get("source_type") or "").strip():
            mismatch_reasons.append("source")
        if mismatch_reasons:
            receipt_mismatches.append(
                {"field": field, "reason": ",".join(mismatch_reasons)}
            )

    report_missing = [
        str(row.get("field") or row.get("key") or "parameter").strip()
        for row in (report.get("missing") or [])
        if isinstance(row, dict)
    ]
    report_provisional = [
        str(row.get("field") or row.get("key") or "parameter").strip()
        for row in (report.get("provisional") or [])
        if isinstance(row, dict)
    ]
    ledger_unresolved = [
        str(value).strip()
        for value in (ledger.get("unresolved_fields") or [])
        if str(value).strip()
    ]
    required_contract_ok = (
        len(required_fields) == len(FORMAL_REQUIRED_FIELDS)
        and set(required_fields) == set(FORMAL_REQUIRED_FIELDS)
    )
    ready_contract_ok = set(required_fields) == ready_fields
    resolved_contract_ok = (
        len(resolved_fields) == len(FORMAL_REQUIRED_FIELDS)
        and len(resolved_fields) == len(set(resolved_fields))
        and set(resolved_fields) == set(FORMAL_REQUIRED_FIELDS)
    )
    digest_bound = bool(
        ledger.get("ledger_digest")
        and str(report.get("project_fact_ledger_digest") or "").strip()
        == str(ledger.get("ledger_digest") or "").strip()
    )
    receipt_available = bool(
        report.get("schema_version") == "missing-parameter-probe-v2"
        and ledger.get("schema_version") == "project-fact-ledger-v1"
        and ledger.get("ledger_digest")
        and required_contract_ok
        and resolved_contract_ok
    )
    ok = bool(
        receipt_available
        and ledger_validation.get("ok") is True
        and bool(ledger_project_id)
        and digest_bound
        and report.get("formal_ready") is True
        and report.get("ok") is True
        and readiness.get("ready") is True
        and ledger.get("status") == "PASS_PROJECT_FACTS_RESOLVED"
        and ready_contract_ok
        and not report_missing
        and not report_provisional
        and not (report.get("blocked_fields") or [])
        and not (report.get("auto_fill") or {})
        and {
            str(value).strip().lower()
            for value in (report.get("accepted_statuses") or [])
            if str(value).strip()
        }
        == _FORMAL_PARAMETER_STATUSES
        and not ledger_unresolved
        and not (readiness.get("missing_fields") or [])
        and not (readiness.get("provisional_fields") or [])
        and not unresolved_fields
        and not invalid_statuses
        and not source_evidence_errors
        and not receipt_mismatches
        and structured_quality_validation.get("ok") is True
    )
    return {
        "pass": ok,
        "available": receipt_available,
        "ledger_validation_ok": ledger_validation.get("ok") is True,
        "project_identity_bound": bool(ledger_project_id),
        "project_id": ledger_project_id or None,
        "ledger_validation_errors": list(ledger_validation.get("errors") or []),
        "receipt_digest_bound": digest_bound,
        "required_contract_ok": required_contract_ok,
        "ready_contract_ok": ready_contract_ok,
        "resolved_contract_ok": resolved_contract_ok,
        "accepted_statuses": sorted(_FORMAL_PARAMETER_STATUSES),
        "required_fields": required_fields,
        "ready_fields": sorted(ready_fields),
        "report_missing_fields": report_missing,
        "report_provisional_fields": report_provisional,
        "ledger_unresolved_fields": ledger_unresolved,
        "unresolved_fields": sorted(set(unresolved_fields)),
        "invalid_statuses": invalid_statuses,
        "source_evidence_errors": source_evidence_errors,
        "receipt_mismatches": receipt_mismatches,
        "structured_quality_validation": structured_quality_validation,
        "report_formal_ready": report.get("formal_ready") is True,
        "ledger_formal_ready": readiness.get("ready") is True,
    }


def build_delivery_quality_gate(
    *,
    strict: bool,
    content_review: dict[str, Any] | None,
    plan_consistency: dict[str, Any] | None,
    model_review_audit: dict[str, Any] | None,
    requirement_matrix: dict[str, Any] | None,
    standard_audit: dict[str, Any] | None,
    cross_index: dict[str, Any] | None,
    model_review_required: bool,
    formal_delivery_required: bool = False,
    project_parameters: dict[str, Any] | None = None,
    project_fact_ledger: dict[str, Any] | None = None,
    sections: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Combine independent specialist results into one fail-closed delivery decision."""

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    content = dict(content_review or {})
    content_gate = content.get("quality_gate") if isinstance(content.get("quality_gate"), dict) else {}
    content_ok = bool(content_gate.get("pass"))
    checks.append({"name": "independent_content_quality", "pass": content_ok})
    if not content_ok:
        blockers.append(
            _issue(
                "DELIVERY_CONTENT_QUALITY_BLOCKED",
                "独立内容质量审核未通过。",
                source="independent_content_review",
                details=content_gate.get("blocking_issues") or content.get("issues") or [],
            )
        )

    plan = dict(plan_consistency or {})
    plan_ok = bool(plan) and bool(plan.get("ok", False))
    checks.append({"name": "plan_consistency", "pass": plan_ok})
    if not plan_ok:
        blockers.append(
            _issue(
                "DELIVERY_PLAN_CONSISTENCY_BLOCKED",
                "工期、资源峰值或关键线路的一致性校验未通过。",
                source="plan_consistency",
                details=plan,
            )
        )

    standards = dict(standard_audit or {})
    standards_ok = bool(standards.get("ok", False))
    checks.append({"name": "verified_standards", "pass": standards_ok})
    if not standards_ok:
        blockers.append(
            _issue(
                "DELIVERY_STANDARD_EVIDENCE_BLOCKED",
                "存在未核验、过期或冲突的规范引用。",
                source="standard_citation_audit",
                details=(standards.get("violations") or [])[:20],
            )
        )

    req = dict(requirement_matrix or {})
    req_summary = req.get("summary") if isinstance(req.get("summary"), dict) else {}
    req_present = bool(req)
    req_ok = (not req_present) or bool(req_summary.get("strict_delivery_allowed", False))
    checks.append({"name": "requirement_evidence_matrix", "pass": req_ok})
    if not req_ok:
        blockers.append(
            _issue(
                "DELIVERY_REQUIREMENT_EVIDENCE_BLOCKED",
                "招标要求尚未全部形成可反查证据闭环。",
                source="requirement_evidence_matrix",
                details=req_summary.get("blocking_requirement_ids") or [],
            )
        )

    cross = dict(cross_index or {})
    cross_contract_fields = {
        "ok",
        "focus_count",
        "mentioned_count",
        "closed_ok_count",
        "missing_drawing_locator_count",
        "missing_standard_locator_count",
        "focus_items",
    }
    focus_count = int(cross.get("focus_count") or 0)
    mentioned_count = int(cross.get("mentioned_count") or 0)
    closed_count = int(cross.get("closed_ok_count") or 0)
    missing_drawing = int(cross.get("missing_drawing_locator_count") or 0)
    missing_standard = int(cross.get("missing_standard_locator_count") or 0)
    focus_rows = cross.get("focus_items")
    cross_available = (
        bool(cross)
        and not bool(cross.get("build_failed"))
        and cross_contract_fields.issubset(cross)
        and isinstance(focus_rows, list)
        and len(focus_rows) == focus_count
        and (focus_count == 0 or cross.get("ok") is True)
        and 0 <= closed_count <= mentioned_count <= focus_count
        and 0 <= missing_drawing <= mentioned_count
        and 0 <= missing_standard <= mentioned_count
    )
    cross_ok = cross_available and (focus_count == 0 or (
        mentioned_count >= focus_count
        and closed_count >= focus_count
        and missing_drawing == 0
        and missing_standard == 0
    ))
    checks.append(
        {
            "name": "boq_cross_index_closure",
            "pass": cross_ok,
            "available": cross_available,
            "focus_count": focus_count,
            "mentioned_count": mentioned_count,
            "closed_ok_count": closed_count,
            "missing_drawing_locator_count": missing_drawing,
            "missing_standard_locator_count": missing_standard,
        }
    )
    if not cross_ok:
        blocker_code = (
            "DELIVERY_CROSS_INDEX_UNAVAILABLE"
            if not cross_available
            else "DELIVERY_CROSS_INDEX_BLOCKED"
        )
        blocker_message = (
            "重点清单项交叉索引构建失败，严格交付已按失败关闭。"
            if not cross_available
            else "重点清单项未全部绑定章节、图纸/规范定位并形成量化闭环。"
        )
        blockers.append(
            _issue(
                blocker_code,
                blocker_message,
                source="cross_index",
                details=checks[-1],
            )
        )

    parameter_check = {
        "pass": True,
        "required": bool(formal_delivery_required),
        "accepted_statuses": sorted(_FORMAL_PARAMETER_STATUSES),
    }
    if formal_delivery_required:
        parameter_check = {
            **_formal_project_parameter_check(project_parameters, project_fact_ledger),
            "required": True,
        }
    checks.append({"name": "formal_project_parameters", **parameter_check})
    if not parameter_check.get("pass"):
        blockers.append(
            _issue(
                "DELIVERY_PROJECT_PARAMETERS_UNRESOLVED",
                "正式文档仍有缺失、临时默认或未经核验的项目参数。",
                source="project_parameter_readiness",
                details=parameter_check,
            )
        )

    body_parameter_check = {
        "pass": True,
        "required": bool(formal_delivery_required),
    }
    if formal_delivery_required:
        body_parameter_check = {
            **_formal_parameter_body_check(sections, project_fact_ledger),
            "required": True,
        }
    checks.append({"name": "formal_parameter_body_binding", **body_parameter_check})
    if not body_parameter_check.get("pass"):
        blockers.append(
            _issue(
                "DELIVERY_PROJECT_PARAMETER_BODY_CONFLICT",
                "正文中的正式参数未与项目事实台账值及证据定位一致绑定。",
                source="formal_parameter_body_binding",
                details=body_parameter_check,
            )
        )

    model_audit = dict(model_review_audit or {})
    consistency = (
        model_audit.get("consistency_review")
        if isinstance(model_audit.get("consistency_review"), dict)
        else {}
    )
    failed_chapters = [row for row in (model_audit.get("failed_chapters") or []) if isinstance(row, dict)]
    summary = str(consistency.get("summary") or "").strip()
    machine_decision = _MACHINE_DECISION_RE.match(summary)
    if machine_decision:
        consistency_safe = machine_decision.group(1).upper() == "PASS"
    else:
        consistency_safe = bool(_SAFE_CONSISTENCY_RE.search(summary)) and not bool(
            _CONFLICT_RE.search(_SAFE_CONSISTENCY_RE.sub("", summary))
        )
    model_ok = True
    if model_review_required:
        model_ok = bool(consistency.get("ok")) and consistency_safe and not failed_chapters
    checks.append(
        {
            "name": "independent_model_review",
            "pass": model_ok,
            "required": bool(model_review_required),
            "failed_chapter_count": len(failed_chapters),
            "explicit_no_conflict": consistency_safe,
            "machine_decision": (
                machine_decision.group(1).upper() if machine_decision else None
            ),
        }
    )
    if not model_ok:
        blockers.append(
            _issue(
                "DELIVERY_MODEL_REVIEW_BLOCKED",
                "关键章节精修或全文一致性终审未给出明确无冲突结论。",
                source="model_review_audit",
                details={
                    "failed_chapters": failed_chapters,
                    "consistency_ok": bool(consistency.get("ok")),
                    "summary": summary[:1200],
                },
            )
        )
    elif not model_review_required:
        warnings.append(
            {
                "code": "DELIVERY_MODEL_REVIEW_NOT_REQUIRED",
                "severity": "info",
                "source": "model_review_audit",
                "message": "当前执行模式未要求外部模型终审；其余确定性质量门仍已执行。",
            }
        )

    decision = {
        "schema_version": "delivery-quality-gate-v1",
        "strict": bool(strict),
        "delivery_allowed": not blockers,
        "checks": checks,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "blockers": blockers,
        "warnings": warnings,
    }
    decision["decision_digest"] = _canonical_digest(decision)
    return decision
