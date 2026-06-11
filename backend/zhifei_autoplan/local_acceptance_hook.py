from __future__ import annotations

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

    has_chapter_16 = ("第十六章" in text or "16章" in text or "第16章" in text) and ("风险" in text and "措施" in text)
    hard_gates.append(_gate("chapter_16_risk_measures", has_chapter_16, "16章风险与措施"))
    if not has_chapter_16:
        issues.append(make_issue("CHAPTER_16_RISK_MEASURES_MISSING", "missing 16章风险与措施"))

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
