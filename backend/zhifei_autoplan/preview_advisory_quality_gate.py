from __future__ import annotations

import re
from typing import Any


QUALITY_STATUS_BLOCKED = "blocked"
QUALITY_STATUS_REVIEW_REQUIRED = "review_required"
QUALITY_STATUS_PREVIEW_OK = "preview_ok"
QUALITY_STATUS_SYSTEM_ERROR = "system_error"

MAX_ADVISORY_CHARS = 1200
MAX_SUGGESTIONS = 3
MAX_RISK_NOTES = 3

FORMAL_GENERATION_ALLOWED = False
SHADOW_CANDIDATE_ALLOWED = False
WRITEBACK_ALLOWED = False
EXPORT_ALLOWED = False
ZBID_WRITEBACK_ALLOWED = False

_FORMAL_RESULT_FIELDS = frozenset(
    {
        "content",
        "docx",
        "docx_path",
        "download_url",
        "export_path",
        "generated_sections",
        "job",
        "job_id",
        "json",
        "json_path",
        "markdown",
        "markdown_path",
        "output",
        "output_path",
        "result_path",
    }
)
_REQUIRED_SAFETY_FLAGS = {
    "preview_only": True,
    "no_write": True,
    "affects_generation": False,
    "affects_export": False,
    "affects_zbid_writeback": False,
}
_FORBIDDEN_TRUE_FLAGS = frozenset(
    {
        "calls_generate_route",
        "calls_export_docx_route",
        "calls_review_apply_route",
        "triggers_generation_chain",
        "triggers_export_chain",
        "triggers_zbid_writeback",
        "writes_output",
        "writes_job",
        "writes_export",
        "writes_formal_section",
        "calls_zbid_writeback",
    }
)
_GENERIC_PHRASES = (
    "加强管理",
    "严格控制",
    "确保质量",
    "落实责任",
    "高度重视",
    "完善制度",
    "加强协调",
)
_CONCRETE_MARKERS = (
    "验收",
    "检查",
    "记录",
    "频次",
    "责任岗位",
    "闭环",
    "工序",
    "节点",
    "资源",
    "风险",
    "措施",
    "控制点",
    "复核",
    "资料",
    "样板",
    "旁站",
    "检验批",
    "整改",
    "验证",
)
_CONSTRUCTION_MARKERS = _CONCRETE_MARKERS + (
    "质量",
    "安全",
    "进度",
    "环保",
    "施工",
    "组织",
    "技术",
)
_MISLEADING_WRITEBACK_PHRASES = (
    "已写入",
    "已生成正式文档",
    "已导出docx",
    "已导出 DOCX",
    "已写回zbid",
    "已写回 ZBid",
)
_FORMAL_REPLACEMENT_MARKERS = (
    "正式正文",
    "替换为",
    "本章节内容如下",
    "以下为正式",
)
_HALLUCINATION_PATTERNS = (
    re.compile(r"招标文件第\s*[\d.一二三四五六七八九十]+\s*[条款]", re.I),
    re.compile(r"评分(?:办法|项|标准).*第\s*[\d.一二三四五六七八九十]+", re.I),
    re.compile(r"\b(?:GB|JGJ|CJJ|DBJ)[\s/-]?\d{3,6}(?:-\d{2,4})?\b", re.I),
    re.compile(r"\d+(?:\.\d+)?\s*(?:万元|亿元|日历天|平方米|m2|㎡)", re.I),
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


def _has_forbidden_route_trace(value: Any) -> bool:
    if isinstance(value, str):
        return value in {"/generate", "/export_docx", "/review/apply"}
    if isinstance(value, (list, tuple, set)):
        return any(_has_forbidden_route_trace(item) for item in value)
    if isinstance(value, dict):
        return any(_has_forbidden_route_trace(item) for item in value.values())
    return False


def _looks_generic(advisory: str) -> bool:
    phrase_count = sum(1 for phrase in _GENERIC_PHRASES if phrase in advisory)
    concrete_count = sum(1 for marker in _CONCRETE_MARKERS if marker in advisory)
    compact = re.sub(r"\s+", "", advisory)
    if phrase_count >= 2 and concrete_count < 2:
        return True
    if phrase_count >= 1 and concrete_count == 0 and len(compact) <= 80:
        return True
    return False


def _looks_unrelated(advisory: str, context: dict[str, Any]) -> bool:
    section_title = _text(context.get("section_title"), limit=200)
    if not section_title:
        return False
    title_chars = {char for char in section_title if "\u4e00" <= char <= "\u9fff"}
    overlap = sum(1 for char in title_chars if char in advisory)
    marker_hits = sum(1 for marker in _CONSTRUCTION_MARKERS if marker in advisory)
    return overlap == 0 and marker_hits == 0


def _has_hallucination_risk(advisory: str) -> bool:
    lowered = advisory.lower()
    if any(phrase.lower() in lowered for phrase in _MISLEADING_WRITEBACK_PHRASES):
        return True
    return any(pattern.search(advisory) for pattern in _HALLUCINATION_PATTERNS)


def _has_formal_replacement_risk(advisory: str) -> bool:
    lowered = advisory.lower()
    if any(marker in advisory for marker in _FORMAL_REPLACEMENT_MARKERS):
        return True
    return "docx" in lowered or "markdown文件" in advisory or "json文件" in advisory


def _score_dimensions(
    *,
    advisory: str,
    context: dict[str, Any],
    preview_mode: str,
    safety_blockers: list[str],
    blockers: list[str],
    review_reasons: list[str],
    warnings: list[str],
) -> dict[str, int]:
    relevance = 80
    if _looks_unrelated(advisory, context):
        relevance = 20
    elif context.get("section_title") and any(char in advisory for char in _text(context.get("section_title"))):
        relevance = 90

    specificity = 75
    if _looks_generic(advisory):
        specificity = 35
    elif any(marker in advisory for marker in _CONCRETE_MARKERS):
        specificity = 85

    engineering = 65 + min(20, sum(1 for marker in _CONSTRUCTION_MARKERS if marker in advisory) * 4)
    quantification = 70 if re.search(r"\d|每|频次|节点|责任岗位|检查", advisory) else 45
    risk_closure = 80 if all(marker in advisory for marker in ("风险", "措施")) or "闭环" in advisory else 50
    evidence_safety = 30 if _has_hallucination_risk(advisory) else 85
    format_score = 90 if advisory and len(advisory) <= MAX_ADVISORY_CHARS else 45
    write_safety = 0 if safety_blockers else 100
    fallback_penalty = 35 if preview_mode == "thinking_only_fallback" else 0

    base = int(
        (
            relevance
            + specificity
            + engineering
            + quantification
            + risk_closure
            + evidence_safety
            + format_score
            + write_safety
        )
        / 8
    )
    score = base - fallback_penalty - len(blockers) * 25 - len(review_reasons) * 10 - len(warnings) * 3
    return {
        "relevance_score": max(0, min(100, relevance)),
        "specificity_score": max(0, min(100, specificity)),
        "engineering_score": max(0, min(100, engineering)),
        "quantification_score": max(0, min(100, quantification)),
        "risk_closure_score": max(0, min(100, risk_closure)),
        "evidence_safety_score": max(0, min(100, evidence_safety)),
        "format_score": max(0, min(100, format_score)),
        "write_safety_score": max(0, min(100, write_safety)),
        "fallback_penalty": fallback_penalty,
        "overall_quality_status": max(0, min(100, score)),
    }


def _base_gate(
    *,
    quality_status: str,
    gate_level: str,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    review_reasons: list[str] | None = None,
    passed_checks: list[str] | None = None,
    failed_checks: list[str] | None = None,
    preview_mode: str = "",
    response_source: str = "",
    model: str = "",
    calls_ollama: bool = False,
    advisory_length: int = 0,
    suggestions_count: int = 0,
    risk_notes_count: int = 0,
    quality_score: int = 0,
    score_dimensions: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "quality_status": quality_status,
        "quality_score": max(0, min(100, int(quality_score))),
        "score_dimensions": dict(score_dimensions or {}),
        "gate_level": gate_level,
        "blockers": list(blockers or []),
        "warnings": list(warnings or []),
        "review_reasons": list(review_reasons or []),
        "passed_checks": list(passed_checks or []),
        "failed_checks": list(failed_checks or []),
        "preview_mode": preview_mode,
        "response_source": response_source,
        "content_source": response_source,
        "model": model,
        "calls_ollama": bool(calls_ollama),
        "advisory_length": int(advisory_length),
        "suggestions_count": min(int(suggestions_count), MAX_SUGGESTIONS),
        "risk_notes_count": min(int(risk_notes_count), MAX_RISK_NOTES),
        "formal_ineligible": True,
        "formal_generation_allowed": FORMAL_GENERATION_ALLOWED,
        "shadow_candidate_allowed": SHADOW_CANDIDATE_ALLOWED,
        "writeback_allowed": WRITEBACK_ALLOWED,
        "export_allowed": EXPORT_ALLOWED,
        "zbid_writeback_allowed": ZBID_WRITEBACK_ALLOWED,
    }


def _evaluate_preview_advisory_quality_gate(
    preview_response: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(context or {})
    blockers: list[str] = []
    warnings: list[str] = []
    review_reasons: list[str] = []
    passed_checks: list[str] = []
    failed_checks: list[str] = []

    for field, expected in _REQUIRED_SAFETY_FLAGS.items():
        if preview_response.get(field) is expected:
            _append_unique(passed_checks, f"{field}_guard")
        else:
            _append_unique(blockers, f"{field}_unsafe")
            _append_unique(failed_checks, f"{field}_guard")

    formal_fields = sorted(set(preview_response) & _FORMAL_RESULT_FIELDS)
    if formal_fields:
        _append_unique(blockers, f"formal_result_field:{formal_fields[0]}")
        _append_unique(failed_checks, "formal_result_field_guard")

    for field in sorted(_FORBIDDEN_TRUE_FLAGS):
        if preview_response.get(field) is True:
            _append_unique(blockers, f"forbidden_trace:{field}")
            _append_unique(failed_checks, f"{field}_guard")

    if _has_forbidden_route_trace(preview_response.get("called_routes")) or _has_forbidden_route_trace(
        preview_response.get("route_triggers")
    ):
        _append_unique(blockers, "forbidden_route_trace")
        _append_unique(failed_checks, "forbidden_route_trace_guard")

    advisory = _text(preview_response.get("advisory"), limit=MAX_ADVISORY_CHARS + 1000)
    advisory_length = len(advisory)
    suggestions = _list_value(preview_response.get("suggestions"))
    risk_notes = _list_value(preview_response.get("risk_notes") or preview_response.get("warnings"))
    preview_mode = _text(preview_response.get("preview_mode"), limit=80)
    response_source = _text(
        preview_response.get("response_source") or preview_response.get("content_source"),
        limit=120,
    )
    model = _text(preview_response.get("model"), limit=120)
    calls_ollama_present = "calls_ollama" in preview_response

    if advisory:
        _append_unique(passed_checks, "advisory_present")
    else:
        _append_unique(blockers, "empty_advisory")
        _append_unique(failed_checks, "advisory_present")

    if advisory_length > MAX_ADVISORY_CHARS:
        _append_unique(warnings, "advisory_over_limit")
        _append_unique(review_reasons, "advisory_length_review_required")
        _append_unique(failed_checks, "advisory_length_limit")
    elif advisory:
        _append_unique(passed_checks, "advisory_length_limit")

    if len(suggestions) > MAX_SUGGESTIONS:
        _append_unique(warnings, "suggestions_truncated")
        _append_unique(failed_checks, "suggestions_count_limit")
    else:
        _append_unique(passed_checks, "suggestions_count_limit")

    if len(risk_notes) > MAX_RISK_NOTES:
        _append_unique(warnings, "risk_notes_truncated")
        _append_unique(failed_checks, "risk_notes_count_limit")
    else:
        _append_unique(passed_checks, "risk_notes_count_limit")

    for field, value in {
        "source": preview_response.get("source"),
        "model": model,
        "preview_mode": preview_mode,
        "response_source": response_source,
    }.items():
        if _text(value, limit=120):
            _append_unique(passed_checks, f"{field}_trace")
        else:
            _append_unique(review_reasons, f"missing_{field}")
            _append_unique(failed_checks, f"{field}_trace")
    if calls_ollama_present:
        _append_unique(passed_checks, "calls_ollama_trace")
    else:
        _append_unique(review_reasons, "missing_calls_ollama")
        _append_unique(failed_checks, "calls_ollama_trace")

    if preview_mode == "thinking_only_fallback":
        _append_unique(review_reasons, "thinking_only_fallback_review_required")
        _append_unique(warnings, "thinking_only_fallback")
        _append_unique(failed_checks, "thinking_only_fallback_not_shadow_candidate")
    elif preview_mode:
        _append_unique(passed_checks, "preview_mode_not_thinking_only_fallback")

    if advisory and _looks_generic(advisory):
        _append_unique(review_reasons, "vague_advisory")
        _append_unique(failed_checks, "specificity_guard")
    elif advisory:
        _append_unique(passed_checks, "specificity_guard")

    if advisory and _looks_unrelated(advisory, context):
        _append_unique(review_reasons, "advisory_may_be_unrelated")
        _append_unique(failed_checks, "relevance_guard")
    elif advisory:
        _append_unique(passed_checks, "relevance_guard")

    if advisory and _has_hallucination_risk(advisory):
        _append_unique(blockers, "hallucination_risk")
        _append_unique(failed_checks, "evidence_safety_guard")
    elif advisory:
        _append_unique(passed_checks, "evidence_safety_guard")

    if advisory and _has_formal_replacement_risk(advisory):
        _append_unique(blockers, "formal_replacement_risk")
        _append_unique(failed_checks, "formal_replacement_guard")
    elif advisory:
        _append_unique(passed_checks, "formal_replacement_guard")

    if advisory and any(marker in advisory for marker in _CONCRETE_MARKERS):
        _append_unique(passed_checks, "construction_specificity_guard")
    elif advisory:
        _append_unique(review_reasons, "construction_specificity_review_required")
        _append_unique(failed_checks, "construction_specificity_guard")

    score_dimensions = _score_dimensions(
        advisory=advisory,
        context=context,
        preview_mode=preview_mode,
        safety_blockers=[item for item in blockers if item.endswith("_unsafe")],
        blockers=blockers,
        review_reasons=review_reasons,
        warnings=warnings,
    )
    score = score_dimensions["overall_quality_status"]

    if blockers:
        status = QUALITY_STATUS_BLOCKED
        gate_level = "P0" if any(item.endswith("_unsafe") or item.startswith("forbidden") for item in blockers) else "P3"
    elif review_reasons:
        status = QUALITY_STATUS_REVIEW_REQUIRED
        if any("thinking_only" in item for item in review_reasons):
            gate_level = "P2"
        elif any("missing_" in item or "length" in item for item in review_reasons):
            gate_level = "P1"
        else:
            gate_level = "P3"
    else:
        status = QUALITY_STATUS_PREVIEW_OK
        gate_level = "P4"

    return _base_gate(
        quality_status=status,
        quality_score=score,
        score_dimensions=score_dimensions,
        gate_level=gate_level,
        blockers=blockers,
        warnings=warnings,
        review_reasons=review_reasons,
        passed_checks=passed_checks,
        failed_checks=failed_checks,
        preview_mode=preview_mode,
        response_source=response_source,
        model=model,
        calls_ollama=bool(preview_response.get("calls_ollama")),
        advisory_length=advisory_length,
        suggestions_count=len(suggestions),
        risk_notes_count=len(risk_notes),
    )


def evaluate_preview_advisory_quality_gate(
    preview_response: Any,
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(preview_response, dict):
            return _base_gate(
                quality_status=QUALITY_STATUS_SYSTEM_ERROR,
                gate_level="system_error",
                blockers=["quality_gate_input_must_be_object"],
                failed_checks=["quality_gate_input"],
            )
        return _evaluate_preview_advisory_quality_gate(preview_response, context=context)
    except Exception:
        return _base_gate(
            quality_status=QUALITY_STATUS_SYSTEM_ERROR,
            gate_level="system_error",
            blockers=["quality_gate_exception"],
            failed_checks=["quality_gate_exception"],
        )


_QUALITY_GATE_PUBLIC_FIELDS = (
    "quality_status",
    "quality_score",
    "gate_level",
    "blockers",
    "warnings",
    "review_reasons",
    "passed_checks",
    "failed_checks",
    "preview_mode",
    "response_source",
    "model",
    "calls_ollama",
    "advisory_length",
    "suggestions_count",
    "risk_notes_count",
    "formal_ineligible",
    "formal_generation_allowed",
    "shadow_candidate_allowed",
    "writeback_allowed",
    "export_allowed",
    "zbid_writeback_allowed",
)


def attach_preview_advisory_quality_gate(
    preview_response: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = dict(preview_response)
    gate = evaluate_preview_advisory_quality_gate(out, context=context)
    out["quality_gate"] = gate
    for field in _QUALITY_GATE_PUBLIC_FIELDS:
        out[field] = gate[field]
    return out
