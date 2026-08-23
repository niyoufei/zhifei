"""Deterministic, advisory-only review insights for one generated bid variant.

The builder summarizes data that already exists in the generation bundle.  It
does not call a model, invent an official evaluation score, or change any
document.  The output is intended for an internal quality-control dashboard.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


QUALITY_DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("structure", "目录结构"),
    ("officialese", "表达精炼"),
    ("risk_triplet", "风险-控制-验证"),
    ("qse_closed_loop", "质量安全环保闭环"),
    ("logic_template_adherence", "逻辑模板"),
    ("chapter_blueprint_adherence", "章节蓝图"),
    ("quantitative", "量化指标"),
    ("required_topics_detail", "重点内容"),
    ("evidence_traceability", "证据可追溯"),
    ("drawing_evidence", "图纸依据"),
    ("standard_evidence", "规范依据"),
    ("boq_focus_item_typed_evidence", "清单重点项"),
    ("consistency", "全文一致性"),
    ("variant_diversity", "方案差异度"),
)

_HIGH_SEVERITIES = frozenset({"critical", "high", "严重", "高", "阻断"})
_MEDIUM_SEVERITIES = frozenset({"medium", "moderate", "中", "一般"})
_LOW_SEVERITIES = frozenset({"low", "minor", "低", "提示"})


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _clamp_ratio(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    return round(max(0.0, min(1.0, number)), 4)


def _bool_signal(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict) and isinstance(value.get("ok"), bool):
        return bool(value["ok"])
    return None


def _severity_bucket(value: Any) -> str:
    severity = str(value or "").strip().lower()
    if severity in _HIGH_SEVERITIES:
        return "high"
    if severity in _MEDIUM_SEVERITIES:
        return "medium"
    if severity in _LOW_SEVERITIES:
        return "low"
    return "unknown"


def _weighted_score(signals: list[tuple[float | None, float]]) -> float | None:
    available = [(value, weight) for value, weight in signals if value is not None]
    weight_sum = sum(weight for _, weight in available)
    if not available or weight_sum <= 0:
        return None
    score = sum(float(value) * weight for value, weight in available) / weight_sum
    return round(max(0.0, min(1.0, score)) * 100.0, 1)


def _quality_level(score: float | None) -> str:
    if score is None:
        return "数据不足"
    if score >= 90:
        return "优秀"
    if score >= 80:
        return "良好"
    if score >= 60:
        return "待改进"
    return "风险较高"


def build_review_insight(variant: dict[str, Any] | None) -> dict[str, Any]:
    """Build one deterministic internal-review dashboard payload."""

    data = _mapping(variant)
    quality = _mapping(data.get("quality_checks"))
    score_mapping = _mapping(data.get("score_mapping"))
    score_summary = _mapping(score_mapping.get("summary"))
    evidence_summary = _mapping(_mapping(data.get("evidence_tracking")).get("summary"))
    contract = _mapping(data.get("agent_contract_checks"))
    pipeline = _rows(data.get("pipeline_stages"))

    dimensions: list[dict[str, Any]] = []
    for key, label in QUALITY_DIMENSIONS:
        passed = _bool_signal(quality.get(key))
        if passed is None:
            continue
        dimensions.append(
            {
                "key": key,
                "dimension": label,
                "passed": passed,
                "status": "通过" if passed else "待整改",
            }
        )
    dimension_pass_ratio = (
        round(sum(1 for row in dimensions if row["passed"]) / len(dimensions), 4)
        if dimensions
        else None
    )

    issues = _rows(quality.get("issue_list"))
    severity_counts = Counter(_severity_bucket(row.get("severity")) for row in issues)
    high_issue_count = int(severity_counts.get("high", 0))

    item_cards = _rows(score_mapping.get("item_cards"))
    score_coverage_ratio = _clamp_ratio(score_summary.get("estimated_ratio"))
    if score_coverage_ratio is None and item_cards:
        card_ratios = [ratio for row in item_cards if (ratio := _clamp_ratio(row.get("coverage_ratio"))) is not None]
        if card_ratios:
            score_coverage_ratio = round(sum(card_ratios) / len(card_ratios), 4)

    high_risk_items = _rows(score_mapping.get("high_risk_items"))
    if not high_risk_items:
        high_risk_items = [
            row
            for row in item_cards
            if (_number(row.get("deduction_risk")) or 0.0) >= 0.45
        ]
    reported_high_risk = _number(score_summary.get("high_risk_item_count"))
    high_risk_count = int(reported_high_risk) if reported_high_risk is not None else len(high_risk_items)

    paragraph_count = int(_number(evidence_summary.get("paragraph_count")) or 0)
    traceable_rows = int(_number(evidence_summary.get("traceable_locator_rows")) or 0)
    evidence_traceability_ratio = (
        round(min(1.0, traceable_rows / paragraph_count), 4) if paragraph_count > 0 else None
    )
    traceability_sections = _rows(_mapping(quality.get("evidence_traceability")).get("by_section"))
    traceability_section_signals = [
        bool(row.get("ok"))
        for row in traceability_sections
        if isinstance(row.get("ok"), bool)
    ]
    traceability_section_passed = sum(1 for passed in traceability_section_signals if passed)
    evidence_traceability_section_ratio = (
        round(traceability_section_passed / len(traceability_section_signals), 4)
        if traceability_section_signals
        else None
    )

    pipeline_signals = [bool(row.get("ok")) for row in pipeline if isinstance(row.get("ok"), bool)]
    pipeline_pass_ratio = (
        round(sum(1 for passed in pipeline_signals if passed) / len(pipeline_signals), 4)
        if pipeline_signals
        else None
    )
    contract_ok = bool(contract.get("ok")) if isinstance(contract.get("ok"), bool) else None

    quality_score_raw = _number(quality.get("score"))
    quality_score = round(max(0.0, min(100.0, quality_score_raw)), 1) if quality_score_raw is not None else None
    if quality_score is None and dimension_pass_ratio is not None:
        quality_score = round(dimension_pass_ratio * 100.0, 1)

    composite_score = _weighted_score(
        [
            (quality_score / 100.0 if quality_score is not None else None, 0.40),
            (score_coverage_ratio, 0.25),
            (evidence_traceability_ratio, 0.20),
            (pipeline_pass_ratio, 0.15),
        ]
    )

    has_assessment_data = bool(
        dimensions
        or item_cards
        or issues
        or pipeline_signals
        or quality_score_raw is not None
        or paragraph_count > 0
    )
    blocking = bool(
        contract_ok is False
        or high_issue_count >= 3
        or high_risk_count >= 3
        or (quality_score is not None and quality_score < 60)
    )
    caution = bool(
        high_issue_count > 0
        or high_risk_count > 0
        or issues
        or (quality_score is not None and quality_score < 80)
        or (dimension_pass_ratio is not None and dimension_pass_ratio < 0.80)
        or (score_coverage_ratio is not None and score_coverage_ratio < 0.75)
        or (evidence_traceability_ratio is not None and evidence_traceability_ratio < 0.65)
        or (pipeline_pass_ratio is not None and pipeline_pass_ratio < 1.0)
    )
    if not has_assessment_data:
        readiness = "insufficient_data"
        readiness_label = "数据不足，待人工复核"
    elif blocking:
        readiness = "not_ready"
        readiness_label = "暂不建议提交"
    elif caution:
        readiness = "remediate_then_review"
        readiness_label = "整改后复核"
    else:
        readiness = "human_final_review"
        readiness_label = "建议进入人工终审"

    actions: list[str] = []
    if contract_ok is False:
        actions.append("先修复 Agent 合同校验失败项，再进行质量终审。")
    if high_risk_count:
        actions.append(f"优先处理 {high_risk_count} 个高风险评分项，补齐关键词、章节响应和可定位证据。")
    if high_issue_count:
        actions.append(f"关闭 {high_issue_count} 个高等级问题，并由人工复核修订内容。")
    if score_coverage_ratio is not None and score_coverage_ratio < 0.75:
        actions.append("评分点覆盖不足：按招标评审标准逐项补齐响应，避免只优化通用文本。")
    if evidence_traceability_ratio is not None and evidence_traceability_ratio < 0.65:
        actions.append("证据追溯不足：补充图纸、规范、清单或原文页码定位，不得编造来源。")
    failed_dimensions = [row["dimension"] for row in dimensions if not row["passed"]]
    if failed_dimensions:
        actions.append(f"整改未通过维度：{'、'.join(failed_dimensions[:6])}。")
    if not actions and has_assessment_data:
        actions.append("维持当前版本，进入人工终审并核对招标原文、评分办法与最终导出件。")
    if not has_assessment_data:
        actions.append("先完成招标文件解析和至少一版施组生成，再形成内部质量判断。")

    top_risks: list[dict[str, Any]] = []
    for row in sorted(
        high_risk_items,
        key=lambda item: float(_number(item.get("deduction_risk")) or 0.0),
        reverse=True,
    )[:8]:
        top_risks.append(
            {
                "评分项": str(row.get("dimension") or row.get("item_id") or "评分项"),
                "覆盖率": _clamp_ratio(row.get("coverage_ratio")),
                "扣分风险": _clamp_ratio(row.get("deduction_risk")),
                "缺失关键词": "、".join(str(x) for x in (row.get("missing_keywords") or [])[:8]),
            }
        )

    return {
        "schema_version": "zhifei.review-insight.v1",
        "advisory_only": True,
        "official_score_claim": False,
        "readiness": readiness,
        "readiness_label": readiness_label,
        "quality_level": _quality_level(composite_score),
        "composite_score": composite_score,
        "metrics": {
            "internal_quality_score": quality_score,
            "dimension_pass_ratio": dimension_pass_ratio,
            "score_coverage_ratio": score_coverage_ratio,
            "evidence_traceability_ratio": evidence_traceability_ratio,
            "evidence_traceability_section_ratio": evidence_traceability_section_ratio,
            "evidence_paragraph_count": paragraph_count,
            "evidence_traceable_paragraph_count": traceable_rows,
            "evidence_section_count": len(traceability_section_signals),
            "evidence_traceable_section_count": traceability_section_passed,
            "pipeline_pass_ratio": pipeline_pass_ratio,
            "issue_count": len(issues),
            "high_issue_count": high_issue_count,
            "high_risk_score_item_count": high_risk_count,
            "score_item_count": int(_number(score_summary.get("item_count")) or len(item_cards)),
            "agent_contract_ok": contract_ok,
        },
        "severity_counts": {
            "high": high_issue_count,
            "medium": int(severity_counts.get("medium", 0)),
            "low": int(severity_counts.get("low", 0)),
            "unknown": int(severity_counts.get("unknown", 0)),
        },
        "dimensions": dimensions,
        "top_risks": top_risks,
        "priority_actions": actions[:6],
        "disclaimer": "仅供投标文件内部质量控制，不是招标人或评标委员会的官方评分、结论或中标承诺。",
    }


__all__ = ["QUALITY_DIMENSIONS", "build_review_insight"]
