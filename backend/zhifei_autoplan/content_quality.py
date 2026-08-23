from __future__ import annotations

from typing import Any, Dict, Iterable, List


QUALITY_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "tender_alignment": {
        "label": "招标与评分响应",
        "weight": 18,
        "agent": "招标评分响应Agent",
        "checks": ("score_coverage", "required_topics", "chapter_blueprint_adherence"),
        "issue_code": "TENDER_ALIGNMENT_GAP",
    },
    "evidence_traceability": {
        "label": "证据与可追溯性",
        "weight": 20,
        "agent": "证据溯源Agent",
        "checks": ("evidence_quality", "evidence_traceability", "core_conclusion_evidence"),
        "issue_code": "EVIDENCE_TRACEABILITY_GAP",
    },
    "quantitative_engineering": {
        "label": "量化与工程可执行性",
        "weight": 18,
        "agent": "技术深度Agent",
        "checks": ("engineering", "quantitative", "boq_focus_item_closure"),
        "issue_code": "QUANTITATIVE_ENGINEERING_GAP",
    },
    "risk_control_verification": {
        "label": "风险控制与验证闭环",
        "weight": 15,
        "agent": "风险闭环Agent",
        "checks": ("risk_triplet", "closed_loop", "qse_closed_loop"),
        "issue_code": "RISK_CONTROL_VERIFICATION_GAP",
    },
    "professional_specificity": {
        "label": "项目专属性与专业表达",
        "weight": 14,
        "agent": "技术深度Agent",
        "checks": ("content_specificity", "vague_terms", "officialese"),
        "issue_code": "PROFESSIONAL_SPECIFICITY_GAP",
    },
    "non_repetition": {
        "label": "去重复与信息增量",
        "weight": 8,
        "agent": "全篇一致性Agent",
        "checks": ("repetition_control",),
        "issue_code": "CONTENT_REPETITION_EXCESS",
    },
    "content_completeness": {
        "label": "结构与内容完整性",
        "weight": 7,
        "agent": "交付验收Agent",
        "checks": ("structure", "content_density", "logic_template_adherence"),
        "issue_code": "CONTENT_COMPLETENESS_GAP",
    },
}


PROFESSIONAL_DIMENSION_THRESHOLD = 65
PROFESSIONAL_SECTION_THRESHOLD = 60
PROFESSIONAL_OVERALL_THRESHOLD = 75


def _row_ratio(rows: Iterable[Any]) -> float | None:
    values = [bool(row.get("ok")) for row in rows if isinstance(row, dict) and "ok" in row]
    if not values:
        return None
    return sum(1 for value in values if value) / len(values)


def _check_ratio(value: Any) -> float | None:
    if not isinstance(value, dict):
        return None
    row_ratio = _row_ratio(value.get("by_section") or [])
    if row_ratio is not None:
        return row_ratio
    if "ok" in value:
        # A missing tender matrix is not a content failure; it simply means the
        # current project does not expose a machine-readable scoring matrix.
        if value.get("reason") == "tender_matrix_missing":
            return None
        return 1.0 if bool(value.get("ok")) else 0.0
    return None


def _dimension_score(checks: Dict[str, Any], names: Iterable[str]) -> int:
    ratios = [ratio for name in names if (ratio := _check_ratio(checks.get(name))) is not None]
    if not ratios:
        return 75
    return int(round(100 * sum(ratios) / len(ratios)))


def _section_ok(checks: Dict[str, Any], check_name: str, title: str) -> bool | None:
    value = checks.get(check_name)
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = value.get("by_section") or []
    else:
        return None
    for row in rows:
        if isinstance(row, dict) and str(row.get("title") or "").strip() == title:
            if "ok" in row:
                return bool(row.get("ok"))
    return None


def _section_score(checks: Dict[str, Any], section: Dict[str, Any]) -> int:
    title = str(section.get("title") or "").strip()
    names = (
        "score_coverage_by_section",
        "evidence_quality",
        "evidence_traceability",
        "engineering_by_section",
        "quantitative",
        "risk_triplet",
        "closed_loop_by_section",
        "content_specificity",
        "vague_terms",
        "officialese",
        "repetition_control",
        "content_density",
    )
    values = [value for name in names if (value := _section_ok(checks, name, title)) is not None]
    if not values:
        return 0 if not str(section.get("content") or "").strip() else 75
    return int(round(100 * sum(1 for value in values if value) / len(values)))


def build_independent_content_review(
    checks: Dict[str, Any] | None,
    *,
    sections: List[Dict[str, Any]] | None,
    strict: bool,
) -> Dict[str, Any]:
    """Build a stable, independently auditable content-quality decision.

    The existing detailed checks remain the source of facts.  This layer turns
    them into weighted dimensions, stable issue codes and a single delivery
    decision so that a long list of booleans cannot silently pass the pipeline.
    """

    base = dict(checks or {})
    rows = [dict(row) for row in (sections or []) if isinstance(row, dict)]
    dimensions: Dict[str, Dict[str, Any]] = {}
    weighted = 0
    total_weight = 0
    issues: List[Dict[str, Any]] = []

    for key, policy in QUALITY_DIMENSIONS.items():
        score = _dimension_score(base, policy["checks"])
        weight = int(policy["weight"])
        weighted += score * weight
        total_weight += weight
        dimensions[key] = {
            "label": policy["label"],
            "score": score,
            "weight": weight,
            "responsible_agent": policy["agent"],
            "pass": score >= PROFESSIONAL_DIMENSION_THRESHOLD,
        }
        if score < PROFESSIONAL_DIMENSION_THRESHOLD:
            issues.append(
                {
                    "code": policy["issue_code"],
                    "severity": "error" if strict else "warning",
                    "dimension": key,
                    "responsible_agent": policy["agent"],
                    "message": (
                        f"{policy['label']}得分{score}，低于专业交付线"
                        f"{PROFESSIONAL_DIMENSION_THRESHOLD}。"
                    ),
                }
            )

    overall_score = int(round(weighted / max(1, total_weight)))
    per_section: List[Dict[str, Any]] = []
    blocking_issues: List[Dict[str, Any]] = []
    if not rows:
        blocking_issues.append(
            {
                "code": "CONTENT_SECTIONS_MISSING",
                "severity": "error",
                "responsible_agent": "主控Agent",
                "message": "没有可交付章节。",
            }
        )

    for section in rows:
        title = str(section.get("title") or "未命名章节").strip() or "未命名章节"
        text = str(section.get("content") or "").strip()
        score = _section_score(base, section)
        state = "pass"
        if len(text) < 40:
            state = "blocked"
            blocking_issues.append(
                {
                    "code": "CHAPTER_CONTENT_EMPTY_OR_TRIVIAL",
                    "severity": "error",
                    "chapter": title,
                    "responsible_agent": "技术深度Agent",
                    "message": f"章节“{title}”有效正文不足40字。",
                }
            )
        elif score < PROFESSIONAL_SECTION_THRESHOLD:
            state = "blocked" if strict else "needs_revision"
            if strict:
                blocking_issues.append(
                    {
                        "code": "CHAPTER_QUALITY_BELOW_THRESHOLD",
                        "severity": "error",
                        "chapter": title,
                        "responsible_agent": "技术深度Agent",
                        "message": (
                            f"章节“{title}”独立质量得分{score}，低于专业交付线"
                            f"{PROFESSIONAL_SECTION_THRESHOLD}。"
                        ),
                    }
                )
        per_section.append(
            {
                "title": title,
                "score": score,
                "character_count": len(text),
                "status": state,
            }
        )

    if strict and overall_score < PROFESSIONAL_OVERALL_THRESHOLD:
        blocking_issues.append(
            {
                "code": "QUALITY_SCORE_BELOW_THRESHOLD",
                "severity": "error",
                "responsible_agent": "交付验收Agent",
                "message": (
                    f"独立内容质量总分{overall_score}，低于专业交付线"
                    f"{PROFESSIONAL_OVERALL_THRESHOLD}。"
                ),
            }
        )

    if strict:
        for issue in issues:
            if str(issue.get("severity") or "") == "error":
                blocking_issues.append(dict(issue))

    # Stable de-duplication keeps UI, evidence and revision APIs deterministic.
    dedup: Dict[tuple, Dict[str, Any]] = {}
    for issue in [*blocking_issues, *issues]:
        key = (issue.get("code"), issue.get("chapter"), issue.get("dimension"))
        dedup[key] = issue
    all_issues = list(dedup.values())
    blocking_codes = {
        (issue.get("code"), issue.get("chapter"), issue.get("dimension"))
        for issue in blocking_issues
    }
    blocking_issues = [
        issue
        for issue in all_issues
        if (issue.get("code"), issue.get("chapter"), issue.get("dimension")) in blocking_codes
    ]
    gate_pass = not blocking_issues

    return {
        "version": "content-quality-v2",
        "score": overall_score,
        "threshold": PROFESSIONAL_OVERALL_THRESHOLD,
        "section_threshold": PROFESSIONAL_SECTION_THRESHOLD,
        "dimension_threshold": PROFESSIONAL_DIMENSION_THRESHOLD,
        "strict": bool(strict),
        "dimensions": dimensions,
        "by_section": per_section,
        "issues": all_issues,
        "quality_gate": {
            "pass": gate_pass,
            "enforced": bool(strict),
            "blocking_issue_count": len(blocking_issues),
            "blocking_issues": blocking_issues,
        },
    }
