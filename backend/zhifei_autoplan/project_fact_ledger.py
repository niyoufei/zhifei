from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from typing import Any

from backend.zhifei_autoplan.project_parameter_evidence import (
    validate_project_parameter_evidence,
)

SCHEMA_VERSION = "project-fact-ledger-v1"

FACT_STATUSES = ("verified", "derived", "approved", "provisional", "missing")
FORMAL_ACCEPTED_STATUSES = frozenset({"verified", "derived", "approved"})
FORMAL_REQUIRED_FIELDS = (
    "planned_duration_days",
    "resource_peak",
    "critical_interval_days",
    "risk_inspection_frequency",
    "quality_threshold",
    "deviation_action_deadline",
)

SOURCE_DEFAULT_STATUSES: dict[str, str] = {
    "approved_resolution": "approved",
    "clarification": "verified",
    "tender": "verified",
    "user_input": "approved",
    "reviewed_design": "verified",
    "boq": "derived",
    "verified_knowledge_graph": "verified",
    "case_library": "provisional",
    "system_default": "provisional",
}

# Higher values are more authoritative.  A later source may only replace an
# earlier fact by using an explicitly higher class; insertion order never wins.
SOURCE_PRIORITIES: dict[str, int] = {
    "approved_resolution": 600,
    "clarification": 500,
    "tender": 400,
    "user_input": 350,
    "reviewed_design": 300,
    "boq": 200,
    "verified_knowledge_graph": 100,
    "case_library": 50,
    "system_default": 0,
}

SOURCE_LABELS: dict[str, str] = {
    "approved_resolution": "经批准的冲突处理",
    "clarification": "澄清答疑",
    "tender": "招标文件",
    "user_input": "本次项目输入",
    "reviewed_design": "审查合格设计文件",
    "boq": "工程量清单/确定性计算",
    "verified_knowledge_graph": "已核验知识图谱",
    "case_library": "案例库参考",
    "system_default": "系统默认",
}

FACT_LABELS: dict[str, str] = {
    "project_name": "项目名称",
    "project_code": "项目编号",
    "planned_duration_days": "总工期",
    "resource_peak": "资源峰值",
    "critical_interval_days": "关键线路间隔",
    "critical_path_names": "关键线路工序",
    "risk_inspection_frequency": "风险检查频次",
    "quality_threshold": "质量阈值",
    "deviation_action_deadline": "偏差处置时限",
}

_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
_TENDER_DURATION_RE = re.compile(
    r"(?:计划工期|总工期|合同工期|工期要求)[^\d]{0,16}"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:日历天|天|日)",
    re.IGNORECASE,
)
_TRACEABLE_APPROVAL_FIELDS = frozenset(FORMAL_REQUIRED_FIELDS)
_FILE_LOCATOR_RE = re.compile(
    r"\.(?:pdf|docx?|xlsx?|xls|csv|ods|txt|dwg)(?:#|::).+",
    re.IGNORECASE,
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
_QUALITY_LOCATOR_RE = re.compile(
    r"^(?P<file>[^#\r\n]+\.(?:pdf|docx?|xlsx?|xls|csv|ods|txt|dwg))"
    r"#p(?P<page>[1-9]\d*)_(?P<sha256>[0-9a-fA-F]{64})@(?P<offset>\d+)$",
    re.IGNORECASE,
)
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
_QUALITY_EVIDENCE_FIELDS = (
    "document_sha256",
    "extract_text_sha256",
    "page",
    "page_text_sha256",
    "offset",
    "start",
    "end",
    "page_start",
    "page_end",
    "page_start_offset",
    "page_end_offset",
    "page_match_start",
    "page_match_end",
    "match_text_sha256",
)
_QUALITY_OPERATOR_ALIASES = {
    ">=": "≥",
    "=>": "≥",
    "≥": "≥",
    "<=": "≤",
    "=<": "≤",
    "≤": "≤",
    ">": ">",
    "<": "<",
    "=": "=",
    "==": "=",
}
_GENERIC_PROCESS_SCOPES = frozenset(
    {"全局", "通用", "所有工序", "全部工序", "本项目", "工程整体", "按工序"}
)


def _json_default(value: Any) -> str:
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return int(value) if value.is_integer() else round(value, 6)
    if isinstance(value, str):
        text = " ".join(value.split()).strip()
        return text
    if isinstance(value, (list, tuple)):
        return [_normalize_scalar(item) for item in value]
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_scalar(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return str(value)


def _normalize_unit(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _is_generic_locator(value: Any) -> bool:
    locator = str(value or "").strip()
    return not locator or locator == "metadata" or locator.startswith(
        ("payload.", "project_fact_sources.")
    )


def _fact_value_digest(field: str, value: Any, unit: Any = "") -> str:
    normalized_value: Any
    if field == "quality_threshold":
        quality = _normalize_quality_threshold(value)
        normalized_value = quality[0] if quality is not None else _normalize_scalar(value)
    else:
        normalized_value = _normalize_scalar(value)
    return _sha256(
        {
            "field": str(field or "").strip(),
            "value": normalized_value,
            "unit": _normalize_unit(unit),
        }
    )


def _raw_fact_parts(raw: Any) -> tuple[Any, str, Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(raw, Mapping) or "value" not in raw:
        return raw, "", {}, {}
    evidence = raw.get("evidence") if isinstance(raw.get("evidence"), Mapping) else {}
    receipt = raw.get("approval_receipt")
    if not isinstance(receipt, Mapping):
        receipt = raw.get("confirmation_receipt")
    return (
        raw.get("value"),
        _normalize_unit(raw.get("unit")),
        evidence,
        receipt if isinstance(receipt, Mapping) else {},
    )


def _traceable_file_evidence(raw: Any) -> tuple[dict[str, Any], bool]:
    _, _, evidence, _ = _raw_fact_parts(raw)
    locator = str(evidence.get("locator") or "").strip()
    file_name = str(evidence.get("file_name") or "").strip()
    document_sha256 = str(
        evidence.get("document_sha256") or evidence.get("source_sha256") or ""
    ).strip().lower()
    locator_file = locator.split("#", 1)[0].split("::", 1)[0]
    valid = bool(
        not _is_generic_locator(locator)
        and _FILE_LOCATOR_RE.search(locator) is not None
        and _SHA256_RE.fullmatch(document_sha256) is not None
        and (not file_name or locator_file == file_name)
    )
    return _sanitize_evidence(evidence), valid


def _normalize_approval_receipt(
    *,
    field: str,
    raw: Any,
    expected_project_id: str,
) -> tuple[dict[str, Any], bool]:
    value, unit, _, receipt = _raw_fact_parts(raw)
    normalized = {
        key: _normalize_unit(receipt.get(key)) for key in _APPROVAL_RECEIPT_FIELDS
    }
    expected_value_digest = _fact_value_digest(field, value, unit)
    receipt_project_id = normalized["project_id"]
    valid = bool(
        all(normalized.values())
        and bool(expected_project_id)
        and normalized["status"].lower() == "approved"
        and normalized["field"] == field
        and _SHA256_RE.fullmatch(normalized["value_digest"]) is not None
        and normalized["value_digest"].lower() == expected_value_digest
        and _APPROVED_AT_RE.fullmatch(normalized["approved_at"]) is not None
        and receipt_project_id == expected_project_id
    )
    normalized["status"] = normalized["status"].lower()
    normalized["value_digest"] = normalized["value_digest"].lower()
    normalized["receipt_digest"] = _sha256(normalized)
    return normalized, valid


def _normalize_formal_approval(
    *,
    field: str,
    raw: Any,
    expected_project_id: str,
) -> dict[str, Any]:
    if isinstance(raw, Mapping) and "value" in raw:
        normalized = copy.deepcopy(dict(raw))
    else:
        normalized = {"value": copy.deepcopy(raw)}
    receipt, receipt_ok = _normalize_approval_receipt(
        field=field,
        raw=normalized,
        expected_project_id=expected_project_id,
    )
    _, evidence_ok = _traceable_file_evidence(normalized)
    normalized["approval_receipt"] = receipt
    normalized.pop("confirmation_receipt", None)
    normalized["status"] = "approved" if receipt_ok and evidence_ok else "provisional"
    return normalized


def _quality_item_evidence(raw_item: Mapping[str, Any]) -> dict[str, Any]:
    nested = raw_item.get("evidence")
    nested_evidence = nested if isinstance(nested, Mapping) else {}
    evidence: dict[str, Any] = {}
    for key in _QUALITY_EVIDENCE_FIELDS:
        raw_value = raw_item.get(key)
        if raw_value is None:
            raw_value = nested_evidence.get(key)
        if raw_value is not None and str(raw_value).strip() != "":
            evidence[key] = _normalize_scalar(raw_value)
    return evidence


def _quality_item_evidence_ready(
    *, locator: str, evidence: Mapping[str, Any]
) -> bool:
    match = _QUALITY_LOCATOR_RE.fullmatch(locator)
    if match is None:
        return False
    document_sha256 = str(evidence.get("document_sha256") or "").strip().lower()
    page_text_sha256 = str(evidence.get("page_text_sha256") or "").strip().lower()
    extract_text_sha256 = str(
        evidence.get("extract_text_sha256") or ""
    ).strip().lower()
    match_text_sha256 = str(evidence.get("match_text_sha256") or "").strip().lower()
    try:
        page = int(evidence.get("page"))
        offset = int(evidence.get("offset"))
    except (TypeError, ValueError):
        return False
    if (
        _SHA256_RE.fullmatch(document_sha256) is None
        or _SHA256_RE.fullmatch(extract_text_sha256) is None
        or _SHA256_RE.fullmatch(page_text_sha256) is None
        or _SHA256_RE.fullmatch(match_text_sha256) is None
        or page != int(match.group("page"))
        or offset != int(match.group("offset"))
        or document_sha256 != match.group("sha256").lower()
    ):
        return False
    for start_key, end_key in (("page_start", "page_end"),):
        if start_key not in evidence and end_key not in evidence:
            continue
        try:
            start = int(evidence.get(start_key))
            end = int(evidence.get(end_key))
        except (TypeError, ValueError):
            return False
        if start < 0 or end <= start:
            return False
    try:
        end = int(evidence.get("end"))
        page_start_offset = int(evidence.get("page_start_offset"))
        page_end_offset = int(evidence.get("page_end_offset"))
        page_match_start = int(evidence.get("page_match_start"))
        page_match_end = int(evidence.get("page_match_end"))
    except (TypeError, ValueError):
        return False
    if (
        end <= offset
        or page_start_offset < 0
        or page_end_offset <= page_start_offset
        or not page_start_offset <= offset < end <= page_end_offset
        or page_match_start != offset - page_start_offset
        or page_match_end != end - page_start_offset
        or page_match_end <= page_match_start
    ):
        return False
    if "start" in evidence:
        try:
            if int(evidence.get("start")) != offset:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _validated_parameter_evidence_quality(
    report: Mapping[str, Any],
    *,
    expected_project_id: str,
    audit_lines: tuple[str, ...] | None = None,
) -> Mapping[str, Any] | None:
    validation = validate_project_parameter_evidence(
        report,
        audit_lines=audit_lines,
    )
    if validation.get("ok") is not True:
        return None
    quality = report.get("quality_threshold")
    if not isinstance(quality, Mapping):
        return None
    report_project_id = str(report.get("project_id") or "").strip()
    if not expected_project_id or report_project_id != expected_project_id:
        return None
    value = quality.get("value")
    if not isinstance(value, Mapping):
        return None
    items = value.get("items") if isinstance(value.get("items"), list) else []
    try:
        matched_item_count = int(report.get("matched_item_count"))
    except (TypeError, ValueError):
        return None
    if (
        str(quality.get("status") or "").strip().lower() != "derived"
        or matched_item_count != len(items)
        or not items
    ):
        return None
    return quality


def _normalize_quality_threshold(value: Any) -> tuple[dict[str, Any], bool] | None:
    """Normalize a per-process threshold bundle without creating a global rule."""
    if not isinstance(value, Mapping):
        return None
    if str(value.get("mode") or "").strip().lower() != "process_bound":
        return None
    raw_items = value.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return None

    normalized_items: list[dict[str, Any]] = []
    seen_scopes: set[tuple[str, str]] = set()
    all_items_ready = True
    for raw_item in raw_items:
        if not isinstance(raw_item, Mapping):
            return None
        process = _normalize_unit(raw_item.get("process"))
        metric = _normalize_unit(raw_item.get("metric"))
        operator = _QUALITY_OPERATOR_ALIASES.get(
            str(raw_item.get("operator") or "").strip()
        )
        threshold_value = _normalize_scalar(raw_item.get("value"))
        if (
            not process
            or process in _GENERIC_PROCESS_SCOPES
            or not metric
            or operator is None
            or isinstance(threshold_value, (bool, list, Mapping))
            or threshold_value in (None, "")
        ):
            return None
        scope = (process, metric)
        if scope in seen_scopes:
            return None
        seen_scopes.add(scope)

        status = str(raw_item.get("status") or "missing").strip().lower()
        if status not in FACT_STATUSES:
            status = "missing"
        source = _normalize_unit(
            raw_item.get("source") or raw_item.get("source_type")
        )
        evidence = raw_item.get("evidence")
        locator = _normalize_unit(
            raw_item.get("locator")
            or (evidence.get("locator") if isinstance(evidence, Mapping) else "")
        )
        item_evidence = _quality_item_evidence(raw_item)
        item_ready = (
            status in FORMAL_ACCEPTED_STATUSES
            and bool(source)
            and _quality_item_evidence_ready(
                locator=locator,
                evidence=item_evidence,
            )
        )
        all_items_ready = all_items_ready and item_ready
        core = {
            "process": process,
            "metric": metric,
            "operator": operator,
            "value": threshold_value,
            "unit": _normalize_unit(raw_item.get("unit")),
            "status": status,
            "source": source,
            "locator": locator,
            **item_evidence,
        }
        item_id = _normalize_unit(raw_item.get("id") or raw_item.get("item_id"))
        core["id"] = item_id or _sha256(core)[:16]
        normalized_items.append(core)

    normalized_items.sort(
        key=lambda item: (
            str(item["id"]),
            str(item["process"]),
            str(item["metric"]),
        )
    )
    return {"mode": "process_bound", "items": normalized_items}, all_items_ready


def _sanitize_evidence(value: Any, *, default_locator: str = "") -> dict[str, Any]:
    evidence = value if isinstance(value, Mapping) else {}
    allowed = (
        "file_name",
        "page",
        "locator",
        "source_sha256",
        "document_sha256",
        "start",
        "end",
        "page_text_sha256",
        "page_start",
        "page_end",
        "offset",
        "match_text_sha256",
        "derivation_receipt",
        "evidence_set_receipt",
        "evidence_set_receipt_digest",
    )
    result: dict[str, Any] = {}
    for key in allowed:
        item = evidence.get(key)
        if item is None or str(item).strip() == "":
            continue
        result[key] = _normalize_scalar(item)
    snippet = evidence.get("snippet")
    if snippet is not None and str(snippet):
        result["snippet_sha256"] = hashlib.sha256(str(snippet).encode("utf-8")).hexdigest()
    if default_locator and not result.get("locator"):
        result["locator"] = default_locator
    result["evidence_digest"] = _sha256(result)
    return result


def _normalize_fact_record(field: str, raw: Any) -> dict[str, Any] | None:
    key = str(field or "").strip()
    if not _FIELD_RE.fullmatch(key):
        return None
    if isinstance(raw, Mapping) and "value" in raw:
        value = raw.get("value")
        unit = _normalize_unit(raw.get("unit"))
        confidence = raw.get("confidence")
        evidence = raw.get("evidence")
        approval_receipt = raw.get("approval_receipt")
        if not isinstance(approval_receipt, Mapping):
            approval_receipt = raw.get("confirmation_receipt")
        status = str(raw.get("status") or "").strip().lower()
    else:
        value = raw
        unit = ""
        confidence = None
        evidence = None
        approval_receipt = None
        status = ""
    forced_status = ""
    if key == "quality_threshold":
        normalized_quality = _normalize_quality_threshold(value)
        if normalized_quality is None:
            return None
        value, quality_ready = normalized_quality
        if not quality_ready:
            forced_status = "provisional"
    else:
        value = _normalize_scalar(value)
    if value is None or value == "" or value == [] or value == {}:
        return None
    record: dict[str, Any] = {"field": key, "value": value, "unit": unit}
    if status in FACT_STATUSES:
        record["status"] = status
    if forced_status:
        record["forced_status"] = forced_status
    if confidence is not None:
        try:
            normalized_confidence = float(confidence)
        except (TypeError, ValueError):
            normalized_confidence = None
        if normalized_confidence is not None:
            record["confidence"] = max(0.0, min(1.0, normalized_confidence))
    if isinstance(evidence, Mapping):
        record["evidence"] = _sanitize_evidence(evidence)
    if isinstance(approval_receipt, Mapping):
        record["approval_receipt"] = _normalize_scalar(approval_receipt)
    return record


def _fact_status(source_type: str, explicit_status: Any = None) -> str:
    default = SOURCE_DEFAULT_STATUSES.get(source_type, "provisional")
    requested = str(explicit_status or "").strip().lower()
    if requested not in FACT_STATUSES:
        return default
    # Low-trust sources can never self-promote into a formal fact merely by
    # carrying a caller-supplied status string.
    if source_type in {"system_default", "case_library"}:
        return "provisional"
    if source_type == "approved_resolution":
        if requested in {"provisional", "missing"}:
            return "provisional"
        return "approved"
    if source_type in {"clarification", "tender", "reviewed_design"}:
        return "verified"
    if source_type == "boq":
        return "derived"
    return requested


def _iter_source_facts(source: Mapping[str, Any]) -> Iterable[dict[str, Any]]:
    raw_facts = source.get("facts")
    if isinstance(raw_facts, Mapping):
        for field, raw in raw_facts.items():
            record = _normalize_fact_record(str(field), raw)
            if record:
                yield record
    elif isinstance(raw_facts, list):
        for item in raw_facts:
            if not isinstance(item, Mapping):
                continue
            field = str(item.get("field") or "").strip()
            record = _normalize_fact_record(field, item)
            if record:
                yield record


def build_project_fact_ledger(sources: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Resolve project facts without mutating inputs and bind the result to a digest."""
    candidates: dict[str, list[dict[str, Any]]] = {}
    source_receipts: list[dict[str, Any]] = []

    for index, source in enumerate(copy.deepcopy(list(sources or []))):
        if not isinstance(source, Mapping):
            continue
        source_type = str(source.get("source_type") or "system_default").strip()
        if source_type not in SOURCE_PRIORITIES:
            source_type = "system_default"
        source_id = str(source.get("source_id") or f"source-{index + 1}").strip()
        priority = SOURCE_PRIORITIES[source_type]
        source_evidence = _sanitize_evidence(
            source.get("evidence"),
            default_locator=f"project_fact_sources.{source_id}",
        )
        fact_count = 0
        for record in _iter_source_facts(source):
            fact_count += 1
            evidence = record.pop("evidence", None) or source_evidence
            forced_status = str(record.pop("forced_status", "")).strip()
            explicit_status = record.pop("status", None)
            status = forced_status or _fact_status(source_type, explicit_status)
            candidate = {
                **record,
                "status": status,
                "source_id": source_id,
                "source_type": source_type,
                "source_label": SOURCE_LABELS[source_type],
                "priority": priority,
                "evidence": evidence,
            }
            candidates.setdefault(record["field"], []).append(candidate)
        source_receipts.append(
            {
                "source_id": source_id,
                "source_type": source_type,
                "source_label": SOURCE_LABELS[source_type],
                "priority": priority,
                "fact_count": fact_count,
                "evidence_digest": source_evidence["evidence_digest"],
            }
        )

    selected: dict[str, dict[str, Any]] = {}
    conflicts: list[dict[str, Any]] = []
    overridden: list[dict[str, Any]] = []
    for field in sorted(candidates):
        rows = sorted(
            candidates[field],
            key=lambda row: (-int(row["priority"]), str(row["source_id"]), _canonical_json(row["value"])),
        )
        top_priority = int(rows[0]["priority"])
        top_rows = [row for row in rows if int(row["priority"]) == top_priority]
        value_groups: dict[str, list[dict[str, Any]]] = {}
        for row in top_rows:
            identity = _canonical_json({"value": row["value"], "unit": row.get("unit") or ""})
            value_groups.setdefault(identity, []).append(row)
        if len(value_groups) > 1:
            conflicts.append(
                {
                    "field": field,
                    "label": FACT_LABELS.get(field, field),
                    "priority": top_priority,
                    "candidates": [
                        {
                            "value": row["value"],
                            "unit": row.get("unit") or "",
                            "source_id": row["source_id"],
                            "source_type": row["source_type"],
                            "evidence": row["evidence"],
                        }
                        for row in top_rows
                    ],
                }
            )
            continue

        chosen = copy.deepcopy(top_rows[0])
        chosen["corroborating_sources"] = [row["source_id"] for row in top_rows]
        selected[field] = chosen
        chosen_identity = _canonical_json({"value": chosen["value"], "unit": chosen.get("unit") or ""})
        for row in rows[len(top_rows) :]:
            row_identity = _canonical_json({"value": row["value"], "unit": row.get("unit") or ""})
            if row_identity != chosen_identity:
                overridden.append(
                    {
                        "field": field,
                        "selected_source_id": chosen["source_id"],
                        "overridden_source_id": row["source_id"],
                        "overridden_value": row["value"],
                        "overridden_unit": row.get("unit") or "",
                        "reason": "lower_source_priority",
                    }
                )

    ledger: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "policy": {
            "source_priorities": dict(SOURCE_PRIORITIES),
            "same_priority_conflict": "HOLD",
            "lower_priority_conflict": "record_and_override",
            "formal_accepted_statuses": sorted(FORMAL_ACCEPTED_STATUSES),
        },
        "status": "HOLD_PROJECT_FACT_CONFLICT" if conflicts else "PASS_PROJECT_FACTS_RESOLVED",
        "unresolved_fields": [row["field"] for row in conflicts],
        "facts": selected,
        "conflicts": conflicts,
        "overridden_candidates": overridden,
        "sources": sorted(source_receipts, key=lambda row: (-int(row["priority"]), str(row["source_id"]))),
    }
    ready_fields: list[str] = []
    missing_fields: list[str] = []
    provisional_fields: list[str] = []
    for field in FORMAL_REQUIRED_FIELDS:
        fact = selected.get(field)
        if not isinstance(fact, Mapping):
            missing_fields.append(field)
        elif str(fact.get("status") or "missing") in FORMAL_ACCEPTED_STATUSES:
            ready_fields.append(field)
        else:
            provisional_fields.append(field)
    ledger["formal_parameter_readiness"] = {
        "ready": not conflicts and not missing_fields and not provisional_fields,
        "required_fields": list(FORMAL_REQUIRED_FIELDS),
        "ready_fields": ready_fields,
        "missing_fields": missing_fields,
        "provisional_fields": provisional_fields,
        "accepted_statuses": sorted(FORMAL_ACCEPTED_STATUSES),
    }
    ledger["ledger_digest"] = _sha256(ledger)
    return ledger


def validate_project_fact_ledger(ledger: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(ledger or {}))
    claimed = str(payload.pop("ledger_digest", "")).strip()
    computed = _sha256(payload)
    unresolved = [str(x) for x in (payload.get("unresolved_fields") or []) if str(x)]
    errors: list[str] = []
    if not claimed:
        errors.append("ledger_digest_missing")
    elif claimed != computed:
        errors.append("ledger_digest_mismatch")
    if unresolved:
        errors.append("project_fact_conflict")
    return {
        "ok": not errors,
        "errors": errors,
        "claimed_digest": claimed,
        "computed_digest": computed,
        "unresolved_fields": unresolved,
    }


def _facts_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _tender_duration_sources(tender: Mapping[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    items = tender.get("items") if isinstance(tender.get("items"), list) else []
    for item_index, item in enumerate(items):
        if not isinstance(item, Mapping):
            continue
        spans = item.get("source_spans") if isinstance(item.get("source_spans"), list) else []
        for span_index, span in enumerate(spans):
            if not isinstance(span, Mapping):
                continue
            snippet = str(span.get("snippet") or "")
            match = _TENDER_DURATION_RE.search(snippet)
            if not match:
                continue
            raw_value = float(match.group("value"))
            value: int | float = int(raw_value) if raw_value.is_integer() else raw_value
            file_name = str(span.get("file_name") or "")
            display_file_name = file_name.replace("\\", "/").rsplit("/", 1)[-1]
            source_type = (
                "clarification"
                if any(marker in file_name for marker in ("答疑", "澄清", "补疑"))
                else "tender"
            )
            document_sha256 = str(
                span.get("document_sha256") or span.get("source_sha256") or ""
            ).strip().lower()
            page_text_sha256 = str(span.get("page_text_sha256") or "").strip().lower()
            try:
                page = int(span.get("page"))
                start = int(span.get("start"))
                end = int(span.get("end"))
            except (TypeError, ValueError):
                page, start, end = 0, -1, -1
            if (
                display_file_name
                and _SHA256_RE.fullmatch(document_sha256)
                and _SHA256_RE.fullmatch(page_text_sha256)
                and page >= 1
                and start >= 0
                and end > start
            ):
                locator = (
                    f"{display_file_name}#p{page}_{document_sha256}@{start}"
                )
            else:
                locator = (
                    f"tender_matrix.items[{item_index}]"
                    f".source_spans[{span_index}]"
                )
            evidence = {
                key: span.get(key)
                for key in (
                    "file_name",
                    "page",
                    "start",
                    "end",
                    "snippet",
                    "document_sha256",
                    "source_sha256",
                    "page_text_sha256",
                    "page_start",
                    "page_end",
                )
                if span.get(key) is not None
            }
            if display_file_name:
                evidence["file_name"] = display_file_name
            if start >= 0:
                evidence["offset"] = start
            evidence["locator"] = locator
            sources.append(
                {
                    "source_id": f"tender-duration-{item_index + 1}-{span_index + 1}",
                    "source_type": source_type,
                    "facts": {
                        "planned_duration_days": {
                            "value": value,
                            "unit": "天",
                            "status": "verified",
                            "confidence": 1.0,
                        }
                    },
                    "evidence": evidence,
                }
            )
    return sources


def build_project_fact_ledger_from_inputs(
    *,
    payload: Mapping[str, Any] | None,
    tender: Mapping[str, Any] | None,
    boq_wbs_cpm: Mapping[str, Any] | None,
    project_parameter_evidence: Mapping[str, Any] | None = None,
    trusted_ingest_audit_lines: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    payload_data = dict(payload or {})
    tender_data = dict(tender or {})
    cpm_data = dict(boq_wbs_cpm or {})
    sources: list[dict[str, Any]] = []
    project_id = str(payload_data.get("project_id") or "").strip()

    parameter_evidence_data = dict(project_parameter_evidence or {})
    quality_threshold = _validated_parameter_evidence_quality(
        parameter_evidence_data,
        expected_project_id=project_id,
        audit_lines=trusted_ingest_audit_lines,
    )
    if isinstance(quality_threshold, Mapping):
        sources.append(
            {
                "source_id": "project-parameter-evidence",
                "source_type": "reviewed_design",
                "facts": {"quality_threshold": dict(quality_threshold)},
                "evidence": {
                    "locator": "project_parameter_evidence.quality_threshold"
                },
            }
        )

    approved = _facts_mapping(payload_data.get("approved_project_fact_resolutions"))
    if approved:
        normalized_approved: dict[str, Any] = {}
        for field, raw in approved.items():
            if field not in _TRACEABLE_APPROVAL_FIELDS:
                normalized_approved[field] = raw
                continue
            normalized_approved[field] = _normalize_formal_approval(
                field=field,
                raw=raw,
                expected_project_id=project_id,
            )
        sources.append(
            {
                "source_id": "approved-project-fact-resolutions",
                "source_type": "approved_resolution",
                "facts": normalized_approved,
                "evidence": {"locator": "payload.approved_project_fact_resolutions"},
            }
        )

    clarification_facts = _facts_mapping(tender_data.get("clarification_facts"))
    extraction_meta = tender_data.get("extraction_meta") if isinstance(tender_data.get("extraction_meta"), Mapping) else {}
    if not clarification_facts:
        clarification_facts = _facts_mapping(extraction_meta.get("clarification_facts"))
    if clarification_facts:
        sources.append(
            {
                "source_id": "tender-clarifications",
                "source_type": "clarification",
                "facts": clarification_facts,
                "evidence": {"locator": "tender.clarification_facts"},
            }
        )

    tender_header_facts: dict[str, Any] = {}
    if str(tender_data.get("project_name") or "").strip():
        tender_header_facts["project_name"] = tender_data["project_name"]
    if str(tender_data.get("project_code") or "").strip():
        tender_header_facts["project_code"] = tender_data["project_code"]
    if tender_header_facts:
        sources.append(
            {
                "source_id": "tender-project-header",
                "source_type": "tender",
                "facts": tender_header_facts,
                "evidence": {"locator": "tender_matrix"},
            }
        )
    # Preserve independent tender extraction outputs as independent candidates.
    # A dict merge here would silently let the last parser win and conceal a
    # same-authority contradiction that strict generation must hold on.
    tender_explicit_facts = _facts_mapping(tender_data.get("project_facts"))
    if tender_explicit_facts:
        sources.append(
            {
                "source_id": "tender-explicit-project-facts",
                "source_type": "tender",
                "facts": tender_explicit_facts,
                "evidence": {"locator": "tender_matrix.project_facts"},
            }
        )
    tender_extracted_facts = _facts_mapping(extraction_meta.get("project_facts"))
    if tender_extracted_facts:
        sources.append(
            {
                "source_id": "tender-extracted-project-facts",
                "source_type": "tender",
                "facts": tender_extracted_facts,
                "evidence": {"locator": "tender_matrix.extraction_meta.project_facts"},
            }
        )

    # Older tender matrices did not project schedule facts into
    # extraction_meta.project_facts, but they did preserve exact source spans.
    # Deterministically recover a tender-authoritative duration from those
    # spans, retaining the locator and hashed snippet in the ledger.
    sources.extend(_tender_duration_sources(tender_data))

    user_facts = _facts_mapping(payload_data.get("project_facts"))
    topic = str(payload_data.get("topic") or "").strip()
    project_code = str(payload_data.get("project_code") or "").strip()
    if topic and topic != "未命名项目":
        user_facts.setdefault("project_name", topic)
    if project_code:
        user_facts.setdefault("project_code", project_code)
    if user_facts:
        normalized_user_facts: dict[str, Any] = {}
        for field, raw in user_facts.items():
            if field not in _TRACEABLE_APPROVAL_FIELDS:
                normalized_user_facts[field] = raw
                continue
            normalized_user_facts[field] = _normalize_formal_approval(
                field=field,
                raw=raw,
                expected_project_id=project_id,
            )
        sources.append(
            {
                "source_id": "run-project-input",
                "source_type": "user_input",
                "facts": normalized_user_facts,
                "evidence": {"locator": "payload.project_facts"},
            }
        )

    summary = cpm_data.get("summary") if isinstance(cpm_data.get("summary"), Mapping) else {}
    boq_facts: dict[str, Any] = {}
    schedule_fact_eligible = bool(summary.get("schedule_fact_eligible", False))
    if schedule_fact_eligible and summary.get("estimated_duration_days"):
        boq_facts["planned_duration_days"] = {
            "value": summary["estimated_duration_days"],
            "unit": "天",
        }
    if schedule_fact_eligible and summary.get("resource_peak"):
        boq_facts["resource_peak"] = {"value": summary["resource_peak"], "unit": "人当量"}
    if schedule_fact_eligible and summary.get("critical_interval_days"):
        boq_facts["critical_interval_days"] = {
            "value": summary["critical_interval_days"],
            "unit": "天",
        }
    critical_path = [
        str(x).strip()
        for x in (summary.get("critical_path_names") or [])
        if schedule_fact_eligible and str(x).strip()
    ]
    if critical_path:
        boq_facts["critical_path_names"] = critical_path
    if boq_facts:
        schedule_input_readiness = (
            summary.get("schedule_input_readiness")
            if isinstance(summary.get("schedule_input_readiness"), Mapping)
            else {}
        )
        derivation_receipt_core = {
            "project_id": project_id,
            "status": str(schedule_input_readiness.get("status") or "").strip().lower(),
            "locator": str(schedule_input_readiness.get("locator") or "").strip(),
            "ready": schedule_input_readiness.get("ready") is True,
            "checks": _normalize_scalar(schedule_input_readiness.get("checks") or {}),
            "schedule_fact_eligible": schedule_fact_eligible,
            "schedule_fact_reasons": _normalize_scalar(
                summary.get("schedule_fact_reasons") or []
            ),
        }
        derivation_receipt = {
            **derivation_receipt_core,
            "receipt_digest": _sha256(derivation_receipt_core),
        }
        sources.append(
            {
                "source_id": "boq-deterministic-schedule",
                "source_type": "boq",
                "facts": boq_facts,
                "evidence": {
                    "locator": "boq_wbs_cpm.summary",
                    "derivation_receipt": derivation_receipt,
                },
            }
        )

    defaults = _facts_mapping(payload_data.get("system_default_project_facts"))
    if defaults:
        sources.append(
            {
                "source_id": "system-project-fact-defaults",
                "source_type": "system_default",
                "facts": defaults,
                "evidence": {"locator": "payload.system_default_project_facts"},
            }
        )
    ledger = build_project_fact_ledger(sources)
    ledger.pop("ledger_digest", None)
    ledger["project_id"] = project_id or None
    ledger["ledger_digest"] = _sha256(ledger)
    return ledger


def project_fact_prompt_requirements(ledger: Mapping[str, Any]) -> list[str]:
    digest = str(ledger.get("ledger_digest") or "").strip()
    lines = [
        f"【不可变项目事实台账】digest={digest}。所有Agent必须使用下列统一口径，不得另行推测、改写或制造冲突。"
    ]
    facts = ledger.get("facts") if isinstance(ledger.get("facts"), Mapping) else {}
    for field in sorted(facts):
        row = facts[field]
        if not isinstance(row, Mapping):
            continue
        status = str(row.get("status") or "missing")
        if status not in FORMAL_ACCEPTED_STATUSES:
            continue
        value = row.get("value")
        if (
            field == "quality_threshold"
            and isinstance(value, Mapping)
            and value.get("mode") == "process_bound"
        ):
            items = value.get("items") if isinstance(value.get("items"), list) else []
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                lines.append(
                    "工序质量阈值："
                    f"工序={item.get('process')}；指标={item.get('metric')}；"
                    f"判定={item.get('operator')}{item.get('value')}"
                    f"{item.get('unit') or ''}"
                    f"【状态:{item.get('status')};来源:{item.get('source')};"
                    f"证据:{item.get('locator')}】"
                )
            continue
        if isinstance(value, list):
            rendered = "→".join(str(x) for x in value)
        elif isinstance(value, Mapping):
            rendered = _canonical_json(value)
        else:
            rendered = str(value)
        unit = str(row.get("unit") or "")
        source_label = str(row.get("source_label") or row.get("source_type") or "")
        evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
        locator = str(evidence.get("locator") or evidence.get("file_name") or "metadata")
        lines.append(
            f"项目事实：{FACT_LABELS.get(field, field)}={rendered}{unit}"
            f"【状态:{status};来源:{source_label};证据:{locator}】"
        )
    return lines
