from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Iterable, Mapping
from typing import Any

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
        status = str(raw.get("status") or "").strip().lower()
    else:
        value = raw
        unit = ""
        confidence = None
        evidence = None
        status = ""
    value = _normalize_scalar(value)
    if value is None or value == "" or value == [] or value == {}:
        return None
    record: dict[str, Any] = {"field": key, "value": value, "unit": unit}
    if status in FACT_STATUSES:
        record["status"] = status
    if confidence is not None:
        try:
            normalized_confidence = float(confidence)
        except (TypeError, ValueError):
            normalized_confidence = None
        if normalized_confidence is not None:
            record["confidence"] = max(0.0, min(1.0, normalized_confidence))
    if isinstance(evidence, Mapping):
        record["evidence"] = _sanitize_evidence(evidence)
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
            status = _fact_status(source_type, record.pop("status", None))
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
            source_type = (
                "clarification"
                if any(marker in file_name for marker in ("答疑", "澄清", "补疑"))
                else "tender"
            )
            locator = f"tender_matrix.items[{item_index}].source_spans[{span_index}]"
            evidence = {
                key: span.get(key)
                for key in ("file_name", "page", "start", "end", "snippet")
                if span.get(key) is not None
            }
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
) -> dict[str, Any]:
    payload_data = dict(payload or {})
    tender_data = dict(tender or {})
    cpm_data = dict(boq_wbs_cpm or {})
    sources: list[dict[str, Any]] = []

    approved = _facts_mapping(payload_data.get("approved_project_fact_resolutions"))
    if approved:
        sources.append(
            {
                "source_id": "approved-project-fact-resolutions",
                "source_type": "approved_resolution",
                "facts": approved,
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
        sources.append(
            {
                "source_id": "run-project-input",
                "source_type": "user_input",
                "facts": user_facts,
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
        sources.append(
            {
                "source_id": "boq-deterministic-schedule",
                "source_type": "boq",
                "facts": boq_facts,
                "evidence": {"locator": "boq_wbs_cpm.summary"},
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
    return build_project_fact_ledger(sources)


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
