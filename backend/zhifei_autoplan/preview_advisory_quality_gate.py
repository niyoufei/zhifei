from __future__ import annotations

import re
from typing import Any

from backend.zhifei_autoplan.evidence_anchor import evaluate_evidence_anchor


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
_INPUT_CONTEXT_FIELDS = (
    "section_text",
    "section_title",
    "review_focus",
    "source_context",
    "context_summary",
    "content",
    "title",
    "section",
    "input_context",
    "original_payload",
)
_INPUT_EVIDENCE_MARKERS = (
    "需资料核验",
    "需资料复核",
    "未查明",
    "待招标文件确认",
    "待确认",
    "待资料确认",
    "以招标文件为准",
    "待图纸",
    "待清单",
    "待踏勘记录",
    "不得作为正式响应依据",
)
_INPUT_CLAUSE_PATTERNS = (
    re.compile(r"(?:招标文件|招标|评分(?:办法|项|标准)|补疑|澄清)\s*第\s*[\d.一二三四五六七八九十]+\s*[条款]?", re.I),
)
_INPUT_STANDARD_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])(?:GB|JGJ|CJJ|DBJ)[\s/-]?\d{3,6}(?:-\d{2,4})?(?![A-Za-z0-9])", re.I),
)
_INPUT_QUANTITY_PATTERNS = (
    re.compile(r"(?:工程量|面积|数量|材料数量)[^，。；;,.]{0,12}\d+(?:\.\d+)?\s*(?:平方米|m2|㎡|立方米|m3|m³|米|吨|台|套)", re.I),
)
_INPUT_DURATION_PATTERNS = (
    re.compile(r"(?:工期|总工期|计划工期)[^，。；;,.]{0,12}\d+(?:\.\d+)?\s*(?:日历天|天|个月|月)", re.I),
    re.compile(r"\d+(?:\.\d+)?\s*日历天", re.I),
)
_INPUT_COST_PATTERNS = (
    re.compile(r"(?:金额|造价|费用|投资|合同价|报价)[^，。；;,.]{0,12}\d+(?:\.\d+)?\s*(?:万元|亿元|元)", re.I),
    re.compile(r"\d+(?:\.\d+)?\s*(?:万元|亿元)", re.I),
)
_INPUT_UNSUPPORTED_FACT_PATTERNS = (
    re.compile(r"本项目[^。；;]{0,60}(?:必须|要求|采用|位于|包含|设置|配置)", re.I),
)
_INPUT_EVIDENCE_MISSING_PATTERNS = (
    re.compile(
        r"(?:no|without)\s+(?:drawings?|site\s+records?|site\s+survey|boq|tender\s+documents?|evidence)",
        re.I,
    ),
    re.compile(r"(?:未提供|无|缺少|没有)[^。；;]{0,20}(?:图纸|清单|踏勘记录|现场记录|招标文件|资料|依据|证据)", re.I),
)
_INPUT_PROJECT_FACT_PATTERNS = (
    re.compile(
        r"(?:本项目|现场|施工现场|项目现场)[^。；;]{0,100}"
        r"(?:已有|已设置|已确认|已具备|全部无误|达到满分|确定|包含|设置|配置|采用|必须达到)"
        r"[^。；;]{0,100}"
        r"(?:塔吊|拌合站|材料堆场|道路|管线|临建|作业面|加工棚|设备|机械|清单|工程量|设计参数|评分项)",
        re.I,
    ),
    re.compile(
        r"(?:本项目|现场|施工现场|项目现场)[^。；;]{0,100}"
        r"(?:塔吊|拌合站|材料堆场|道路|管线|临建|作业面|加工棚|设备|机械|清单|工程量|设计参数|评分项)"
        r"[^。；;]{0,100}"
        r"(?:已有|已设置|已确认|已具备|全部无误|达到满分|确定|包含|设置|配置|采用|必须达到)",
        re.I,
    ),
)
_INPUT_PROJECT_FACT_QUANTITY_PATTERNS = (
    re.compile(
        r"\d+(?:\.\d+)?\s*(?:台|座|个|处|套|条|平方米|m2|㎡|米|吨)"
        r"\s*(?:塔吊|拌合站|材料堆场|道路|管线|临建|作业面|加工棚|设备|机械|清单|工程量)?",
        re.I,
    ),
)
_INPUT_TENDER_EVIDENCE_PATTERNS = (
    re.compile(r"(?:招标文件|评分项|评分标准|补疑|澄清|质量目标|工期)", re.I),
)
_INPUT_DRAWING_BOQ_PATTERNS = (
    re.compile(r"(?:图纸|清单|工程量|材料数量|系统参数|设备参数)", re.I),
)
_INPUT_DIRECT_WRITE_PATTERNS = (
    re.compile(r"(?:请|直接|立即)?(?:写入|写回|替换)(?:正式)?(?:章节|正文|方案|ZBid)", re.I),
    re.compile(r"(?:导出|生成)(?:\s*DOCX|正式文档|正式正文)", re.I),
    re.compile(r"写回\s*ZBid", re.I),
)
_INPUT_FORMAL_CONTENT_PATTERNS = (
    re.compile(r"(?:请|直接|立即)?生成(?:正式)?(?:正文|章节正文|方案内容)", re.I),
)
_INPUT_NEGATION_MARKERS = ("不得", "不要", "禁止", "不应", "不可", "do not")


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


def _flatten_input_text(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in _INPUT_CONTEXT_FIELDS:
            if key in value:
                parts.append(_flatten_input_text(value.get(key)))
        return "\n".join(part for part in parts if part)
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_flatten_input_text(item) for item in value)
    return _text(value)


def _context_input_text(context: dict[str, Any]) -> str:
    parts = []
    for key in _INPUT_CONTEXT_FIELDS:
        if key in context:
            parts.append(_flatten_input_text(context.get(key)))
    return "\n".join(part for part in parts if part)


def _has_input_evidence_marker(text: str) -> bool:
    return any(marker in text for marker in _INPUT_EVIDENCE_MARKERS)


def _has_negated_input_match(text: str, match: re.Match[str]) -> bool:
    start = max(0, match.start() - 12)
    prefix = text[start : match.start()].lower()
    return any(marker in prefix for marker in _INPUT_NEGATION_MARKERS)


def _has_unsafe_input_request(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    for pattern in patterns:
        for match in pattern.finditer(text):
            if not _has_negated_input_match(text, match):
                return True
    return False


def _match_any_input_risk(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _input_risk_gate(context: dict[str, Any]) -> dict[str, Any]:
    text = _context_input_text(context)
    flags: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    evidence_reasons: list[str] = []
    suspicious_references: list[str] = []
    evidence_marker = _has_input_evidence_marker(text)
    evidence_source_missing = False
    project_fact_without_evidence = False
    unsupported_project_fact_detected = False

    def mark(flag: str, *, block: bool = True, reference: bool = False) -> None:
        _append_unique(flags, flag)
        if reference:
            _append_unique(suspicious_references, flag)
        if evidence_marker and block:
            _append_unique(warnings, flag)
            _append_unique(evidence_reasons, "evidence_required_marker")
        elif block:
            _append_unique(blockers, flag)
        else:
            _append_unique(warnings, flag)

    if text:
        evidence_source_missing = _match_any_input_risk(text, _INPUT_EVIDENCE_MISSING_PATTERNS)
        project_fact_detected = _match_any_input_risk(text, _INPUT_PROJECT_FACT_PATTERNS)
        project_fact_quantity_detected = _match_any_input_risk(text, _INPUT_PROJECT_FACT_QUANTITY_PATTERNS)
        project_fact_without_evidence = evidence_source_missing and (
            project_fact_detected or project_fact_quantity_detected
        )
        if _match_any_input_risk(text, _INPUT_CLAUSE_PATTERNS):
            mark("suspicious_clause_reference", reference=True)
            if not evidence_marker:
                _append_unique(warnings, "tender_evidence_missing")
        if _match_any_input_risk(text, _INPUT_STANDARD_PATTERNS):
            mark("suspicious_standard_reference", reference=True)
        if _match_any_input_risk(text, _INPUT_QUANTITY_PATTERNS):
            mark("suspicious_quantity_claim")
            if not evidence_marker:
                _append_unique(warnings, "drawing_or_boq_evidence_missing")
        if _match_any_input_risk(text, _INPUT_DURATION_PATTERNS):
            mark("suspicious_duration_claim")
            if not evidence_marker:
                _append_unique(warnings, "tender_evidence_missing")
        if _match_any_input_risk(text, _INPUT_COST_PATTERNS):
            mark("suspicious_cost_claim")
        unsupported_project_fact_detected = (
            _match_any_input_risk(text, _INPUT_UNSUPPORTED_FACT_PATTERNS)
            or project_fact_without_evidence
        )
        if unsupported_project_fact_detected:
            mark("unsupported_project_fact", block=False)
        if evidence_source_missing:
            _append_unique(flags, "evidence_source_missing")
            _append_unique(warnings, "evidence_source_missing")
            _append_unique(evidence_reasons, "evidence_source_missing")
        if project_fact_without_evidence:
            _append_unique(flags, "project_fact_without_evidence")
            _append_unique(warnings, "project_fact_without_evidence")
            _append_unique(evidence_reasons, "project_fact_without_evidence")
        if _match_any_input_risk(text, _INPUT_TENDER_EVIDENCE_PATTERNS) and not evidence_marker:
            _append_unique(warnings, "tender_evidence_missing")
        if _match_any_input_risk(text, _INPUT_DRAWING_BOQ_PATTERNS) and not evidence_marker:
            _append_unique(warnings, "drawing_or_boq_evidence_missing")
        if evidence_marker:
            _append_unique(flags, "evidence_required_marker")
            _append_unique(warnings, "evidence_required_marker")
            _append_unique(evidence_reasons, "evidence_required_marker")
        if _has_unsafe_input_request(text, _INPUT_FORMAL_CONTENT_PATTERNS):
            _append_unique(flags, "formal_content_request_without_evidence")
            _append_unique(blockers, "formal_content_request_without_evidence")
        if _has_unsafe_input_request(text, _INPUT_DIRECT_WRITE_PATTERNS):
            _append_unique(flags, "direct_write_request_detected")
            _append_unique(blockers, "direct_write_request_detected")

    blocked = bool(blockers)
    review_required = bool(warnings or evidence_reasons) and not blocked
    status = "blocked" if blocked else "review_required" if review_required else "clear"
    score = 0 if blocked else 45 if review_required else 100
    return {
        "input_risk_status": status,
        "input_risk_score": score,
        "input_risk_flags": flags,
        "input_risk_blockers": blockers,
        "input_risk_warnings": warnings,
        "input_evidence_required": bool(evidence_reasons or warnings or blockers),
        "unsupported_claims_detected": bool(
            set(flags)
            & {
                "suspicious_clause_reference",
                "suspicious_standard_reference",
                "suspicious_quantity_claim",
                "suspicious_duration_claim",
                "suspicious_cost_claim",
                "unsupported_project_fact",
                "project_fact_without_evidence",
            }
        ),
        "suspicious_references": suspicious_references,
        "evidence_required_reasons": evidence_reasons,
        "input_risk_review_required": review_required,
        "input_risk_blocked": blocked,
        "evidence_anchor_required": bool(flags and status != "clear"),
        "unsupported_project_fact_detected": bool(unsupported_project_fact_detected),
        "evidence_source_missing": bool(evidence_source_missing),
        "project_fact_without_evidence": bool(project_fact_without_evidence),
    }


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


def _response_mode_metadata(preview_response: dict[str, Any], *, preview_mode: str, response_source: str) -> dict[str, Any]:
    response_mode = _text(preview_response.get("response_mode"), limit=80)
    if not response_mode:
        if preview_mode == "structured_json":
            response_mode = "json_advisory"
        elif preview_mode == "thinking_only_fallback":
            response_mode = "thinking_only_fallback"
        elif preview_mode == "text_fallback":
            response_mode = "text_fallback"
        else:
            response_mode = "response_advisory"
    fallback_reason = _text(preview_response.get("fallback_reason"), limit=180)
    warnings = [
        _text(item, limit=120)
        for item in _list_value(preview_response.get("response_mode_warnings"))
        if _text(item, limit=120)
    ]
    if response_mode in {
        "thinking_only_fallback",
        "empty_response",
        "malformed_response",
        "normalization_failure",
        "system_error",
    }:
        _append_unique(warnings, response_mode)
    if fallback_reason:
        _append_unique(warnings, fallback_reason)
    try:
        confidence = int(preview_response.get("response_mode_confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    if confidence <= 0:
        confidence = {
            "response_advisory": 90,
            "json_advisory": 95,
            "text_fallback": 65,
            "thinking_only_fallback": 30,
        }.get(response_mode, 0)
    review_required = bool(preview_response.get("response_mode_review_required")) or response_mode in {
        "thinking_only_fallback",
        "empty_response",
        "malformed_response",
        "normalization_failure",
        "system_error",
    }
    return {
        "response_mode": response_mode,
        "response_source": _text(preview_response.get("response_source") or response_source, limit=120),
        "fallback_reason": fallback_reason,
        "response_mode_confidence": max(0, min(100, confidence)),
        "response_mode_warnings": warnings,
        "response_mode_review_required": review_required,
        "thinking_fallback_detected": bool(preview_response.get("thinking_fallback_detected"))
        or response_mode == "thinking_only_fallback",
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
    response_mode: str = "",
    fallback_reason: str = "",
    response_mode_confidence: int = 0,
    response_mode_warnings: list[str] | None = None,
    response_mode_review_required: bool = False,
    thinking_fallback_detected: bool = False,
    model: str = "",
    calls_ollama: bool = False,
    advisory_length: int = 0,
    suggestions_count: int = 0,
    risk_notes_count: int = 0,
    quality_score: int = 0,
    score_dimensions: dict[str, int] | None = None,
    input_risk: dict[str, Any] | None = None,
    evidence_anchor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_risk_data = dict(input_risk or {})
    evidence_data = dict(evidence_anchor or {})
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
        "response_mode": response_mode,
        "response_source": response_source,
        "content_source": response_source,
        "fallback_reason": fallback_reason,
        "response_mode_confidence": max(0, min(100, int(response_mode_confidence))),
        "response_mode_warnings": list(response_mode_warnings or []),
        "response_mode_review_required": bool(response_mode_review_required),
        "thinking_fallback_detected": bool(thinking_fallback_detected),
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
        "input_risk_status": input_risk_data.get("input_risk_status", "clear"),
        "input_risk_score": int(input_risk_data.get("input_risk_score", 100)),
        "input_risk_flags": list(input_risk_data.get("input_risk_flags") or []),
        "input_risk_blockers": list(input_risk_data.get("input_risk_blockers") or []),
        "input_risk_warnings": list(input_risk_data.get("input_risk_warnings") or []),
        "input_evidence_required": bool(input_risk_data.get("input_evidence_required", False)),
        "unsupported_claims_detected": bool(input_risk_data.get("unsupported_claims_detected", False)),
        "suspicious_references": list(input_risk_data.get("suspicious_references") or []),
        "evidence_required_reasons": list(input_risk_data.get("evidence_required_reasons") or []),
        "input_risk_review_required": bool(input_risk_data.get("input_risk_review_required", False)),
        "input_risk_blocked": bool(input_risk_data.get("input_risk_blocked", False)),
        "evidence_anchor_required": bool(
            evidence_data.get(
                "evidence_anchor_required",
                input_risk_data.get("evidence_anchor_required", False),
            )
        ),
        "evidence_anchor_status": str(evidence_data.get("evidence_anchor_status", "not_required")),
        "evidence_anchor_level": str(evidence_data.get("evidence_anchor_level", "P4")),
        "evidence_sources": list(evidence_data.get("evidence_sources") or []),
        "evidence_source_type": str(evidence_data.get("evidence_source_type") or ""),
        "evidence_source_id": str(evidence_data.get("evidence_source_id") or ""),
        "evidence_source_title": str(evidence_data.get("evidence_source_title") or ""),
        "evidence_location": str(evidence_data.get("evidence_location") or ""),
        "evidence_page": str(evidence_data.get("evidence_page") or ""),
        "evidence_clause": str(evidence_data.get("evidence_clause") or ""),
        "evidence_quote_excerpt": str(evidence_data.get("evidence_quote_excerpt") or ""),
        "evidence_confidence": int(evidence_data.get("evidence_confidence", 0)),
        "evidence_missing_reasons": list(evidence_data.get("evidence_missing_reasons") or []),
        "unsupported_claims": list(evidence_data.get("unsupported_claims") or []),
        "unsupported_project_facts": list(evidence_data.get("unsupported_project_facts") or []),
        "unverified_parameters": list(evidence_data.get("unverified_parameters") or []),
        "evidence_review_required": bool(evidence_data.get("evidence_review_required", False)),
        "evidence_blocked": bool(evidence_data.get("evidence_blocked", False)),
        "trace_id": str(evidence_data.get("trace_id") or ""),
        "source_snapshot_id": str(evidence_data.get("source_snapshot_id") or ""),
        "generated_from_model": bool(evidence_data.get("generated_from_model", False)),
        "generated_content_must_not_be_evidence": bool(
            evidence_data.get("generated_content_must_not_be_evidence", False)
        ),
        "generated_preview_as_evidence_detected": bool(
            evidence_data.get("generated_preview_as_evidence_detected", False)
        ),
        "generated_content_evidence_blocked": bool(
            evidence_data.get("generated_content_evidence_blocked", False)
        ),
        "invalid_anchor_reason": str(evidence_data.get("invalid_anchor_reason") or ""),
        "unsupported_project_fact_detected": bool(
            input_risk_data.get("unsupported_project_fact_detected", False)
        ),
        "evidence_source_missing": bool(input_risk_data.get("evidence_source_missing", False)),
        "project_fact_without_evidence": bool(input_risk_data.get("project_fact_without_evidence", False)),
    }


def _evaluate_preview_advisory_quality_gate(
    preview_response: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(context or {})
    input_risk = _input_risk_gate(context)
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
    response_mode_data = _response_mode_metadata(
        preview_response,
        preview_mode=preview_mode,
        response_source=response_source,
    )
    response_mode = response_mode_data["response_mode"]
    response_source = response_mode_data["response_source"]
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
        "response_mode": response_mode,
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

    if response_mode_data["response_mode_review_required"]:
        for item in response_mode_data["response_mode_warnings"]:
            _append_unique(warnings, f"response_mode:{item}")
        _append_unique(review_reasons, f"response_mode:{response_mode}")
        _append_unique(failed_checks, f"response_mode:{response_mode}")
    else:
        _append_unique(passed_checks, f"response_mode:{response_mode}")

    if preview_mode == "thinking_only_fallback" or response_mode_data["thinking_fallback_detected"]:
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

    evidence_anchor = evaluate_evidence_anchor(
        {
            "advisory": advisory,
            "preview_mode": preview_mode,
            "response_mode": response_mode,
            "response_source": response_source,
            "evidence_anchor_required": bool(input_risk.get("evidence_anchor_required", False))
            or bool(preview_response.get("evidence_anchor_required", False)),
            "evidence_sources": preview_response.get("evidence_sources"),
            "generated_preview_as_evidence_detected": bool(
                preview_response.get("generated_preview_as_evidence_detected", False)
            ),
            "unsupported_claims": list(input_risk.get("input_risk_blockers") or []),
            "unsupported_project_facts": [
                item
                for item in input_risk.get("input_risk_flags", [])
                if item in {"unsupported_project_fact", "project_fact_without_evidence"}
            ],
            "unverified_parameters": list(input_risk.get("evidence_required_reasons") or []),
            "input_risk": input_risk,
            "trace_id": preview_response.get("request_id") or context.get("request_id"),
            "source_snapshot_id": preview_response.get("source_snapshot_id")
            or context.get("source_snapshot_id"),
            "generated_from_model": bool(preview_response.get("calls_ollama"))
            or response_source in {"thinking", "response", "message.content", "advisory"},
            "zbid_writeback_attempted": preview_response.get("calls_zbid_writeback")
            or preview_response.get("zbid_writeback_requested")
            or preview_response.get("zbid_writeback_allowed"),
            "docx_export_attempted": preview_response.get("calls_export_docx_route")
            or preview_response.get("docx_export_requested")
            or preview_response.get("export_allowed"),
            "candidate_patch_attempted": preview_response.get("candidate_patch_requested")
            or preview_response.get("shadow_candidate_allowed"),
        },
        context=context,
    )
    if evidence_anchor.get("evidence_blocked"):
        _append_unique(blockers, f"evidence_anchor:{evidence_anchor.get('evidence_anchor_status')}")
        _append_unique(failed_checks, f"evidence_anchor:{evidence_anchor.get('evidence_anchor_status')}")
    elif evidence_anchor.get("evidence_review_required"):
        _append_unique(warnings, f"evidence_anchor:{evidence_anchor.get('evidence_anchor_status')}")
        _append_unique(review_reasons, f"evidence_anchor:{evidence_anchor.get('evidence_anchor_status')}")
        _append_unique(failed_checks, f"evidence_anchor:{evidence_anchor.get('evidence_anchor_status')}")
    else:
        _append_unique(passed_checks, f"evidence_anchor:{evidence_anchor.get('evidence_anchor_status')}")
    if evidence_anchor.get("generated_preview_as_evidence_detected"):
        _append_unique(warnings, "generated_preview_as_evidence_detected")
        if evidence_anchor.get("evidence_blocked"):
            _append_unique(blockers, "generated_preview_as_evidence")
            _append_unique(failed_checks, "generated_preview_as_evidence_guard")
        else:
            _append_unique(review_reasons, "generated_preview_as_evidence_review_required")
            _append_unique(failed_checks, "generated_preview_as_evidence_guard")

    for item in input_risk["input_risk_blockers"]:
        _append_unique(blockers, f"input_risk:{item}")
        _append_unique(failed_checks, f"input_risk:{item}")
    for item in input_risk["input_risk_warnings"]:
        _append_unique(warnings, f"input_risk:{item}")
        _append_unique(review_reasons, f"input_risk:{item}")
        _append_unique(failed_checks, f"input_risk:{item}")
    if input_risk["input_risk_status"] == "clear":
        _append_unique(passed_checks, "input_risk_guard")

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
        gate_level = (
            "P0"
            if any(
                item.endswith("_unsafe")
                or item.startswith("forbidden")
                or "direct_write_request_detected" in item
                or "formal_content_request_without_evidence" in item
                for item in blockers
            )
            else "P3"
        )
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
        response_mode=response_mode,
        fallback_reason=response_mode_data["fallback_reason"],
        response_mode_confidence=response_mode_data["response_mode_confidence"],
        response_mode_warnings=response_mode_data["response_mode_warnings"],
        response_mode_review_required=response_mode_data["response_mode_review_required"],
        thinking_fallback_detected=response_mode_data["thinking_fallback_detected"],
        model=model,
        calls_ollama=bool(preview_response.get("calls_ollama")),
        advisory_length=advisory_length,
        suggestions_count=len(suggestions),
        risk_notes_count=len(risk_notes),
        input_risk=input_risk,
        evidence_anchor=evidence_anchor,
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
    "response_mode",
    "response_source",
    "fallback_reason",
    "response_mode_confidence",
    "response_mode_warnings",
    "response_mode_review_required",
    "thinking_fallback_detected",
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
    "input_risk_status",
    "input_risk_score",
    "input_risk_flags",
    "input_risk_blockers",
    "input_risk_warnings",
    "input_evidence_required",
    "unsupported_claims_detected",
    "suspicious_references",
    "evidence_required_reasons",
    "input_risk_review_required",
    "input_risk_blocked",
    "evidence_anchor_required",
    "evidence_anchor_status",
    "evidence_anchor_level",
    "evidence_sources",
    "evidence_source_type",
    "evidence_source_id",
    "evidence_source_title",
    "evidence_location",
    "evidence_page",
    "evidence_clause",
    "evidence_quote_excerpt",
    "evidence_confidence",
    "evidence_missing_reasons",
    "unsupported_claims",
    "unsupported_project_facts",
    "unverified_parameters",
    "evidence_review_required",
    "evidence_blocked",
    "trace_id",
    "source_snapshot_id",
    "generated_from_model",
    "generated_content_must_not_be_evidence",
    "generated_preview_as_evidence_detected",
    "generated_content_evidence_blocked",
    "invalid_anchor_reason",
    "unsupported_project_fact_detected",
    "evidence_source_missing",
    "project_fact_without_evidence",
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
