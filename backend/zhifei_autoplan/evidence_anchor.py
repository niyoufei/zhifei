from __future__ import annotations

import re
from typing import Any


EVIDENCE_STATUS_ANCHORED = "anchored"
EVIDENCE_STATUS_PARTIALLY_ANCHORED = "partially_anchored"
EVIDENCE_STATUS_MISSING = "missing"
EVIDENCE_STATUS_CONFLICTING = "conflicting"
EVIDENCE_STATUS_UNVERIFIED = "unverified"
EVIDENCE_STATUS_NOT_REQUIRED = "not_required"
EVIDENCE_STATUS_INVALID_ANCHOR = "invalid_anchor"
EVIDENCE_STATUS_SYSTEM_ERROR = "system_error"

FORMAL_GENERATION_ALLOWED = False
SHADOW_CANDIDATE_ALLOWED = False
WRITEBACK_ALLOWED = False
EXPORT_ALLOWED = False
ZBID_WRITEBACK_ALLOWED = False

VALID_EVIDENCE_SOURCE_TYPES = frozenset(
    {
        "tender_document",
        "tender_addendum",
        "scoring_criteria",
        "drawing",
        "boq",
        "site_survey",
        "photos",
        "contract_or_owner_requirement",
        "standard_or_code",
        "user_provided_context",
        "system_generated_preview",
        "unknown_or_unverified",
    }
)
STRONG_SOURCE_TYPES = frozenset(
    {
        "tender_document",
        "tender_addendum",
        "scoring_criteria",
        "drawing",
        "boq",
        "site_survey",
        "photos",
        "contract_or_owner_requirement",
        "standard_or_code",
    }
)
MODEL_GENERATED_SOURCE_TYPES = frozenset({"system_generated_preview"})
UNVERIFIED_SOURCE_TYPES = frozenset({"unknown_or_unverified"})

FACTUAL_PATTERNS = (
    re.compile(r"(?:招标文件|评分(?:办法|项|标准)|补疑|澄清)\s*第\s*[\d.一二三四五六七八九十]+\s*[条款]?", re.I),
    re.compile(r"(?<![A-Za-z0-9])(?:GB|JGJ|CJJ|DBJ)[\s/-]?\d{3,6}(?:-\d{2,4})?(?![A-Za-z0-9])", re.I),
    re.compile(r"(?:工程量|面积|数量|材料数量)[^，。；;,.]{0,16}\d+(?:\.\d+)?\s*(?:平方米|m2|㎡|立方米|m3|m³|米|吨|台|套)", re.I),
    re.compile(r"(?:工期|总工期|计划工期)[^，。；;,.]{0,16}\d+(?:\.\d+)?\s*(?:日历天|天|个月|月)", re.I),
    re.compile(r"(?:金额|造价|费用|投资|合同价|报价)[^，。；;,.]{0,16}\d+(?:\.\d+)?\s*(?:万元|亿元|元)", re.I),
    re.compile(r"(?:现场|施工现场|项目现场|本项目)[^。；;]{0,80}(?:塔吊|拌合站|材料堆场|道路|管线|作业面|设备|机械|清单|图纸|评分项)", re.I),
    re.compile(r"(?:质量目标|安全文明目标|验收标准|检查频次|建设单位|工期节点|专业系统|施工参数)", re.I),
)


def _text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _append_unique(items: list[str], item: str) -> None:
    if item and item not in items:
        items.append(item)


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        parts = [_flatten_text(item) for item in value.values()]
        return "\n".join(part for part in parts if part)
    if isinstance(value, (list, tuple, set)):
        parts = [_flatten_text(item) for item in value]
        return "\n".join(part for part in parts if part)
    return _text(value)


def _normalize_sources(value: Any) -> list[dict[str, Any]]:
    raw_sources = _list_value(value)
    if isinstance(value, dict):
        raw_sources = [value]
    sources: list[dict[str, Any]] = []
    for raw in raw_sources:
        if not isinstance(raw, dict):
            sources.append(
                {
                    "evidence_source_type": "",
                    "evidence_source_id": "",
                    "evidence_source_title": _text(raw, limit=200),
                    "evidence_location": "",
                    "evidence_page": "",
                    "evidence_clause": "",
                    "evidence_quote_excerpt": "",
                    "evidence_confidence": 0,
                    "generated_from_model": False,
                }
            )
            continue
        source_type = _text(raw.get("evidence_source_type") or raw.get("source_type") or raw.get("type"), limit=80)
        source_id = _text(raw.get("evidence_source_id") or raw.get("source_id") or raw.get("id"), limit=200)
        source_title = _text(
            raw.get("evidence_source_title") or raw.get("source_title") or raw.get("title"),
            limit=300,
        )
        sources.append(
            {
                "evidence_source_type": source_type,
                "evidence_source_id": source_id,
                "evidence_source_title": source_title,
                "evidence_location": _text(raw.get("evidence_location") or raw.get("location"), limit=300),
                "evidence_page": _text(raw.get("evidence_page") or raw.get("page"), limit=80),
                "evidence_clause": _text(raw.get("evidence_clause") or raw.get("clause"), limit=160),
                "evidence_quote_excerpt": _text(
                    raw.get("evidence_quote_excerpt") or raw.get("quote_excerpt") or raw.get("quote"),
                    limit=300,
                ),
                "evidence_confidence": _bounded_int(raw.get("evidence_confidence") or raw.get("confidence"), default=0),
                "generated_from_model": bool(raw.get("generated_from_model", False)),
            }
        )
    return sources


def _bounded_int(value: Any, *, default: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def _source_identity(source: dict[str, Any]) -> bool:
    return bool(source.get("evidence_source_id") or source.get("evidence_source_title"))


def _source_locator(source: dict[str, Any]) -> bool:
    return bool(source.get("evidence_location") or source.get("evidence_page") or source.get("evidence_clause"))


def _standard_has_reference(source: dict[str, Any]) -> bool:
    combined = " ".join(
        _text(source.get(key), limit=300)
        for key in ("evidence_source_id", "evidence_source_title", "evidence_location", "evidence_clause")
    )
    return bool(re.search(r"(?:GB|JGJ|CJJ|DBJ)[\s/-]?\d{3,6}(?:-\d{2,4})?", combined, re.I))


def _has_factual_content(value: Any) -> bool:
    text = _flatten_text(value)
    return any(pattern.search(text) for pattern in FACTUAL_PATTERNS)


def _first_source_value(sources: list[dict[str, Any]], key: str) -> Any:
    for source in sources:
        if source.get(key):
            return source[key]
    return ""


def _formal_chain_flags() -> dict[str, bool]:
    return {
        "formal_generation_allowed": FORMAL_GENERATION_ALLOWED,
        "shadow_candidate_allowed": SHADOW_CANDIDATE_ALLOWED,
        "writeback_allowed": WRITEBACK_ALLOWED,
        "export_allowed": EXPORT_ALLOWED,
        "zbid_writeback_allowed": ZBID_WRITEBACK_ALLOWED,
    }


def _base_result(
    *,
    required: bool,
    status: str,
    sources: list[dict[str, Any]] | None = None,
    missing_reasons: list[str] | None = None,
    unsupported_claims: list[str] | None = None,
    unsupported_project_facts: list[str] | None = None,
    unverified_parameters: list[str] | None = None,
    trace_id: str = "",
    source_snapshot_id: str = "",
    generated_from_model: bool = False,
    generated_content_must_not_be_evidence: bool = False,
    confidence: int | None = None,
) -> dict[str, Any]:
    source_list = list(sources or [])
    blocked = status in {
        EVIDENCE_STATUS_CONFLICTING,
        EVIDENCE_STATUS_INVALID_ANCHOR,
        EVIDENCE_STATUS_SYSTEM_ERROR,
    }
    review_required = status in {
        EVIDENCE_STATUS_PARTIALLY_ANCHORED,
        EVIDENCE_STATUS_MISSING,
        EVIDENCE_STATUS_UNVERIFIED,
    }
    if confidence is None:
        confidence_by_status = {
            EVIDENCE_STATUS_ANCHORED: 100,
            EVIDENCE_STATUS_PARTIALLY_ANCHORED: 60,
            EVIDENCE_STATUS_MISSING: 20,
            EVIDENCE_STATUS_CONFLICTING: 0,
            EVIDENCE_STATUS_UNVERIFIED: 30,
            EVIDENCE_STATUS_NOT_REQUIRED: 90,
            EVIDENCE_STATUS_INVALID_ANCHOR: 0,
            EVIDENCE_STATUS_SYSTEM_ERROR: 0,
        }
        confidence = confidence_by_status.get(status, 0)
    level = {
        EVIDENCE_STATUS_ANCHORED: "P4",
        EVIDENCE_STATUS_NOT_REQUIRED: "P4",
        EVIDENCE_STATUS_PARTIALLY_ANCHORED: "P2",
        EVIDENCE_STATUS_MISSING: "P3",
        EVIDENCE_STATUS_UNVERIFIED: "P2",
        EVIDENCE_STATUS_CONFLICTING: "P0",
        EVIDENCE_STATUS_INVALID_ANCHOR: "P0",
        EVIDENCE_STATUS_SYSTEM_ERROR: "system_error",
    }.get(status, "P3")
    return {
        "evidence_anchor_required": bool(required),
        "evidence_anchor_status": status,
        "evidence_anchor_level": level,
        "evidence_sources": source_list,
        "evidence_source_type": _first_source_value(source_list, "evidence_source_type"),
        "evidence_source_id": _first_source_value(source_list, "evidence_source_id"),
        "evidence_source_title": _first_source_value(source_list, "evidence_source_title"),
        "evidence_location": _first_source_value(source_list, "evidence_location"),
        "evidence_page": _first_source_value(source_list, "evidence_page"),
        "evidence_clause": _first_source_value(source_list, "evidence_clause"),
        "evidence_quote_excerpt": _first_source_value(source_list, "evidence_quote_excerpt"),
        "evidence_confidence": _bounded_int(confidence, default=0),
        "evidence_missing_reasons": list(missing_reasons or []),
        "unsupported_claims": list(unsupported_claims or []),
        "unsupported_project_facts": list(unsupported_project_facts or []),
        "unverified_parameters": list(unverified_parameters or []),
        "evidence_review_required": bool(review_required),
        "evidence_blocked": bool(blocked),
        "trace_id": trace_id,
        "source_snapshot_id": source_snapshot_id,
        "generated_from_model": bool(generated_from_model),
        "generated_content_must_not_be_evidence": bool(generated_content_must_not_be_evidence),
        **_formal_chain_flags(),
    }


def evaluate_evidence_anchor(anchor_input: Any, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        if not isinstance(anchor_input, dict):
            return _base_result(
                required=True,
                status=EVIDENCE_STATUS_SYSTEM_ERROR,
                missing_reasons=["evidence_anchor_input_must_be_object"],
            )
        payload = dict(anchor_input)
        context = dict(context or {})
        sources = _normalize_sources(payload.get("evidence_sources") or payload.get("evidence_source"))
        unsupported_claims = [
            _text(item, limit=160)
            for item in _list_value(payload.get("unsupported_claims"))
            if _text(item, limit=160)
        ]
        unsupported_project_facts = [
            _text(item, limit=160)
            for item in _list_value(payload.get("unsupported_project_facts"))
            if _text(item, limit=160)
        ]
        unverified_parameters = [
            _text(item, limit=160)
            for item in _list_value(payload.get("unverified_parameters"))
            if _text(item, limit=160)
        ]
        input_risk = payload.get("input_risk")
        if isinstance(input_risk, dict):
            for item in _list_value(input_risk.get("input_risk_blockers")):
                _append_unique(unsupported_claims, f"input_risk:{_text(item, limit=120)}")
            if input_risk.get("unsupported_claims_detected") and not input_risk.get("input_risk_blocked"):
                _append_unique(unverified_parameters, "input_risk:unsupported_claims_detected")
            if input_risk.get("unsupported_project_fact_detected"):
                _append_unique(unsupported_project_facts, "input_risk:unsupported_project_fact")
            if input_risk.get("evidence_source_missing"):
                _append_unique(unverified_parameters, "input_risk:evidence_source_missing")
            if input_risk.get("project_fact_without_evidence"):
                _append_unique(unsupported_project_facts, "input_risk:project_fact_without_evidence")

        trace_id = _text(payload.get("trace_id") or context.get("request_id"), limit=120)
        source_snapshot_id = _text(payload.get("source_snapshot_id") or context.get("source_snapshot_id"), limit=120)
        generated_from_model = bool(payload.get("generated_from_model", False))
        preview_mode = _text(payload.get("preview_mode"), limit=80)
        factual_content = _has_factual_content(
            {
                "claim_text": payload.get("claim_text"),
                "advisory": payload.get("advisory"),
                "context": context,
            }
        )
        future_formal_attempt = any(
            bool(payload.get(field))
            for field in (
                "zbid_writeback_attempted",
                "zbid_writeback_requested",
                "docx_export_attempted",
                "docx_export_requested",
                "candidate_patch_attempted",
                "candidate_patch_requested",
                "formal_generation_requested",
                "writeback_requested",
            )
        )
        required = bool(
            payload.get("evidence_anchor_required")
            or unsupported_claims
            or unsupported_project_facts
            or unverified_parameters
            or factual_content
            or future_formal_attempt
        )
        if preview_mode == "thinking_only_fallback" and factual_content:
            required = True
            _append_unique(unverified_parameters, "thinking_fallback_factual_claim")

        missing_reasons: list[str] = []
        invalid_reasons: list[str] = []
        partial_reasons: list[str] = []
        unverified_reasons: list[str] = []
        anchored_sources = 0
        partial_sources = 0
        source_types = [str(source.get("evidence_source_type") or "") for source in sources]

        if bool(payload.get("evidence_conflicting") or payload.get("conflicting_evidence")):
            return _base_result(
                required=True,
                status=EVIDENCE_STATUS_CONFLICTING,
                sources=sources,
                missing_reasons=["conflicting_evidence"],
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=generated_from_model,
            )

        for source in sources:
            source_type = str(source.get("evidence_source_type") or "")
            if source_type not in VALID_EVIDENCE_SOURCE_TYPES:
                _append_unique(invalid_reasons, "invalid_evidence_source_type")
                continue
            if source_type in MODEL_GENERATED_SOURCE_TYPES or source.get("generated_from_model"):
                _append_unique(invalid_reasons, "model_generated_preview_as_evidence")
                continue
            if source_type in UNVERIFIED_SOURCE_TYPES:
                _append_unique(unverified_reasons, "unknown_or_unverified_source")
                continue
            if source_type == "user_provided_context":
                if _source_identity(source):
                    partial_sources += 1
                    _append_unique(partial_reasons, "user_context_requires_verification")
                else:
                    _append_unique(unverified_reasons, "user_context_missing_source")
                continue
            if source_type == "standard_or_code" and not _standard_has_reference(source):
                partial_sources += 1
                _append_unique(partial_reasons, "standard_or_code_missing_version_or_source")
                continue
            if source_type in STRONG_SOURCE_TYPES:
                if not _source_identity(source):
                    _append_unique(missing_reasons, "evidence_source_identity_missing")
                    continue
                if not _source_locator(source):
                    partial_sources += 1
                    _append_unique(partial_reasons, "evidence_source_location_missing")
                    continue
                anchored_sources += 1

        if invalid_reasons:
            return _base_result(
                required=required or bool(sources),
                status=EVIDENCE_STATUS_INVALID_ANCHOR,
                sources=sources,
                missing_reasons=invalid_reasons,
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=True,
            )

        if future_formal_attempt and not anchored_sources:
            return _base_result(
                required=True,
                status=EVIDENCE_STATUS_INVALID_ANCHOR,
                sources=sources,
                missing_reasons=["formal_chain_attempt_without_evidence"],
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=generated_from_model,
            )

        if unverified_reasons:
            return _base_result(
                required=True,
                status=EVIDENCE_STATUS_UNVERIFIED,
                sources=sources,
                missing_reasons=unverified_reasons,
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=generated_from_model,
            )

        if required and not sources:
            _append_unique(missing_reasons, "evidence_source_missing")
            status = EVIDENCE_STATUS_MISSING
            if unsupported_claims or bool(isinstance(input_risk, dict) and input_risk.get("input_risk_blocked")):
                status = EVIDENCE_STATUS_INVALID_ANCHOR
            return _base_result(
                required=True,
                status=status,
                sources=sources,
                missing_reasons=missing_reasons,
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=generated_from_model,
            )

        if required and anchored_sources and not (partial_sources or partial_reasons or missing_reasons):
            confidence = min(100, max(80, max([source.get("evidence_confidence", 0) for source in sources] or [0])))
            return _base_result(
                required=True,
                status=EVIDENCE_STATUS_ANCHORED,
                sources=sources,
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=generated_from_model,
                confidence=confidence,
            )

        if required and (partial_sources or partial_reasons or missing_reasons):
            reasons = missing_reasons + partial_reasons
            if not reasons:
                reasons = ["evidence_partial_anchor_requires_review"]
            return _base_result(
                required=True,
                status=EVIDENCE_STATUS_PARTIALLY_ANCHORED,
                sources=sources,
                missing_reasons=reasons,
                unsupported_claims=unsupported_claims,
                unsupported_project_facts=unsupported_project_facts,
                unverified_parameters=unverified_parameters,
                trace_id=trace_id,
                source_snapshot_id=source_snapshot_id,
                generated_from_model=generated_from_model,
                generated_content_must_not_be_evidence=generated_from_model,
            )

        if source_types and not required:
            if partial_sources or partial_reasons:
                return _base_result(
                    required=False,
                    status=EVIDENCE_STATUS_PARTIALLY_ANCHORED,
                    sources=sources,
                    missing_reasons=partial_reasons,
                    trace_id=trace_id,
                    source_snapshot_id=source_snapshot_id,
                    generated_from_model=generated_from_model,
                    generated_content_must_not_be_evidence=generated_from_model,
                )
            if anchored_sources:
                return _base_result(
                    required=False,
                    status=EVIDENCE_STATUS_ANCHORED,
                    sources=sources,
                    trace_id=trace_id,
                    source_snapshot_id=source_snapshot_id,
                    generated_from_model=generated_from_model,
                    generated_content_must_not_be_evidence=generated_from_model,
                )

        return _base_result(
            required=False,
            status=EVIDENCE_STATUS_NOT_REQUIRED,
            sources=sources,
            trace_id=trace_id,
            source_snapshot_id=source_snapshot_id,
            generated_from_model=generated_from_model,
            generated_content_must_not_be_evidence=generated_from_model,
        )
    except Exception:
        return _base_result(
            required=True,
            status=EVIDENCE_STATUS_SYSTEM_ERROR,
            missing_reasons=["evidence_anchor_exception"],
        )
