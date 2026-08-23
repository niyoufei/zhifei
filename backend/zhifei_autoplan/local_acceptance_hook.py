from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.zhifei_autoplan.local_adapter_contract import make_issue
from backend.zhifei_autoplan.local_evidence_hook import build_evidence_summary

MANDATORY_TERMS = (
    ("信息化管理", ("信息化管理",)),
    ("绿色工地", ("绿色工地",)),
    ("劳保用品", ("劳保用品",)),
    ("劳保用品配置矩阵", ("劳保用品配置矩阵",)),
    ("关键工序控制点表", ("关键工序控制点表",)),
)

PARAMETER_TERMS = ("参数", "频次", "责任", "验收", "记录")
FORBIDDEN_TERMS = ("LPE", "劳保矩阵", "劳动防护配置矩阵", "无需证据", "TBD", "todo")
RISK_TERMS = ("风险", "危险源", "隐患")
RISK_TREATMENT_TERMS = ("措施", "管控", "防控", "预防", "应对", "处置", "消减", "规避", "整改")


def _sections_text(envelope: Dict[str, Any]) -> str:
    parts: List[str] = []
    for section in envelope.get("sections") or []:
        if isinstance(section, dict):
            parts.append(str(section.get("title") or ""))
            parts.append(str(section.get("content") or ""))
        else:
            parts.append(str(section or ""))
    return "\n".join(parts)


def _gate(gate_id: str, passed: bool, message: str) -> Dict[str, Any]:
    return {"gate_id": gate_id, "pass": bool(passed), "message": message}


def _has_risk_treatment(section_text: str) -> bool:
    if not any(term in section_text for term in RISK_TERMS):
        return False
    if any(term in section_text for term in RISK_TREATMENT_TERMS):
        return True
    # “控制” is common in unrelated phrases such as “关键工序控制点表”.  It
    # counts as treatment only when it is part of a nearby risk-control phrase.
    return bool(
        re.search(r"(?:风险|危险源|隐患).{0,16}控制", section_text, flags=re.DOTALL)
        or re.search(r"控制.{0,16}(?:风险|危险源|隐患)", section_text, flags=re.DOTALL)
    )


def run_acceptance(envelope: Dict[str, Any] | None) -> Dict[str, Any]:
    data = dict(envelope or {})
    text = _sections_text(data)
    hard_gates: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

    for label, terms in MANDATORY_TERMS:
        passed = any(term in text for term in terms)
        hard_gates.append(_gate(f"mandatory_{label}", passed, label))
        if not passed:
            issues.append(make_issue("MANDATORY_CONTENT_MISSING", f"missing mandatory content: {label}", field=label))

    # Tender documents define their own chapter count and may use equivalent
    # professional wording such as "风险控制与验证" instead of the literal
    # phrase "风险与措施". Keep the gate semantic and section-local: a risk (or
    # hazard) and at least one mitigation/control expression must occur in the
    # same section, regardless of the tender's chapter numbering or wording.
    has_risk_measures = False
    for section in data.get("sections") or []:
        if isinstance(section, dict):
            section_text = f"{section.get('title') or ''}\n{section.get('content') or ''}"
        else:
            section_text = str(section or "")
        if _has_risk_treatment(section_text):
            has_risk_measures = True
            break
    hard_gates.append(
        _gate(
            "tender_aligned_risk_measures",
            has_risk_measures,
            "按招标目录设置风险及控制措施",
        )
    )
    if not has_risk_measures:
        issues.append(
            make_issue(
                "RISK_MEASURES_MISSING",
                "缺少与招标目录对应的风险识别及控制措施；请在同一相关章节补充风险与控制、预防、应对或处置闭环",
            )
        )

    for term in PARAMETER_TERMS:
        passed = term in text
        hard_gates.append(_gate(f"parameter_term_{term}", passed, term))
        if not passed:
            issues.append(make_issue("PARAMETER_TRACE_MISSING", f"missing parameter trace term: {term}", field=term))

    forbidden_hits = [term for term in FORBIDDEN_TERMS if term in text]
    hard_gates.append(_gate("forbidden_terms", not forbidden_hits, "禁语检查"))
    for term in forbidden_hits:
        issues.append(make_issue("FORBIDDEN_TERM_DETECTED", f"forbidden term detected: {term}", field=term))

    hard_gates.append(_gate("dedupe_placeholder", True, "去重检查占位"))
    hard_gates.append(_gate("reference_relation_placeholder", True, "引用关系检查占位"))

    evidence_summary = build_evidence_summary(data)
    for issue in evidence_summary.get("issues") or []:
        issues.append(issue)

    quality_checks = data.get("quality_checks") if isinstance(data.get("quality_checks"), dict) else {}
    quality_gate = quality_checks.get("quality_gate") if isinstance(quality_checks.get("quality_gate"), dict) else {}
    if quality_gate and bool(quality_gate.get("enforced")):
        gate_pass = bool(quality_gate.get("pass"))
        hard_gates.append(_gate("independent_content_quality", gate_pass, "独立内容质量门"))
        if not gate_pass:
            blocking = quality_gate.get("blocking_issues") or []
            if not blocking:
                blocking = [{"code": "CONTENT_QUALITY_GATE_FAILED", "message": "独立内容质量门未通过"}]
            for row in blocking:
                if not isinstance(row, dict):
                    continue
                issues.append(
                    make_issue(
                        str(row.get("code") or "CONTENT_QUALITY_GATE_FAILED"),
                        str(row.get("message") or "独立内容质量门未通过"),
                        field=str(row.get("chapter") or row.get("dimension") or "content_quality"),
                    )
                )

    passed = not issues and all(gate.get("pass") for gate in hard_gates)
    return {
        "pass": bool(passed),
        "issues": issues,
        "hard_gates": hard_gates,
        "evidence_summary": evidence_summary,
        "export_allowed": bool(passed),
    }


def validate_before_export(envelope: Dict[str, Any] | None) -> Dict[str, Any]:
    result = run_acceptance(envelope or {})
    return {
        "status": "pass" if result["pass"] else "fail",
        "export_allowed": result["export_allowed"],
        "issues": result["issues"],
        "hard_gates": result["hard_gates"],
        "evidence_summary": result["evidence_summary"],
    }
