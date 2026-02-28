from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _ratio(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return float(num) / float(den)


def _sentence_numeric_density(sections: List[Dict[str, Any]]) -> float:
    total = 0
    numeric = 0
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        text = str(sec.get("content") or "")
        lines = [x.strip() for x in re.split(r"[。；;!?！？]\s*", text) if x.strip()]
        for line in lines:
            total += 1
            if re.search(r"\d+(?:\.\d+)?", line):
                numeric += 1
    return round(_ratio(numeric, max(total, 1)), 6)


def _graph_binding_rate(sections: List[Dict[str, Any]]) -> float:
    total = 0
    hit = 0
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        total += 1
        graph_hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
        if str(graph_hit.get("node_id") or "").strip():
            hit += 1
    return round(_ratio(hit, max(total, 1)), 6)


def _evidence_strength_avg(sections: List[Dict[str, Any]]) -> float:
    grade_score = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.3}
    vals: List[float] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
        strength = hit.get("evidence_strength") if isinstance(hit.get("evidence_strength"), dict) else {}
        grade = str(strength.get("grade") or "").strip().upper()
        if grade in grade_score:
            vals.append(float(grade_score[grade]))
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 6)


def _gap_breakdown(gaps: List[Dict[str, Any]]) -> Dict[str, int]:
    counter: Dict[str, int] = {}
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        key = str(gap.get("type") or "unknown").strip() or "unknown"
        counter[key] = int(counter.get(key) or 0) + 1
    return dict(sorted(counter.items(), key=lambda x: (-x[1], x[0])))


def _recommended_actions_from_gaps(gaps: List[Dict[str, Any]], *, limit: int = 8) -> List[str]:
    actions: List[str] = []
    seen = set()
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        for item in gap.get("suggested_parameters") or []:
            text = str(item or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            actions.append(text)
            if len(actions) >= limit:
                return actions
    return actions


def build_hit_rate_dashboard(
    *,
    index_matrix: Dict[str, Any],
    audit_result: Dict[str, Any],
    graph_audit: Dict[str, Any],
    compliance_audit: Dict[str, Any],
    sentence_evidence_stats: Dict[str, Any],
    sections: List[Dict[str, Any]],
    gaps: List[Dict[str, Any]],
    pre_healing_gap_count: int,
    self_healing: Dict[str, Any],
    boq_governance: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    matrix_rows = index_matrix.get("index_matrix") if isinstance(index_matrix.get("index_matrix"), list) else []
    dimension_total = int(len(matrix_rows))
    score_checks = audit_result.get("checks") if isinstance(audit_result.get("checks"), list) else []
    score_point_total = sum(_safe_int(x.get("score_point_total"), 0) for x in score_checks if isinstance(x, dict))
    score_point_hit = sum(_safe_int(x.get("score_point_hit"), 0) for x in score_checks if isinstance(x, dict))
    score_hit_rate = round(_ratio(score_point_hit, max(score_point_total, 1)), 6)

    graph_checks = graph_audit.get("checks") if isinstance(graph_audit.get("checks"), list) else []
    graph_ok_count = sum(1 for x in graph_checks if isinstance(x, dict) and bool(x.get("ok")))
    graph_hit_rate = round(_ratio(graph_ok_count, max(len(graph_checks), 1)), 6)

    fail_fast_trigger_rate = round(_ratio(len(gaps), max(dimension_total, 1)), 6)
    post_gap_count = int(len(gaps))
    self_heal_release_rate = 0.0
    if bool((self_healing or {}).get("triggered")) and pre_healing_gap_count > 0:
        self_heal_release_rate = round(max(0.0, 1.0 - _ratio(post_gap_count, pre_healing_gap_count)), 6)

    trace_ratio = round(_safe_float((sentence_evidence_stats or {}).get("trace_coverage_ratio"), 0.0), 6)
    numeric_density = _sentence_numeric_density(sections)
    graph_binding_rate = _graph_binding_rate(sections)
    evidence_strength_avg = _evidence_strength_avg(sections)

    consistency_total = _safe_int((compliance_audit or {}).get("inconsistency_count"), 0)
    severity_map = (compliance_audit or {}).get("inconsistency_severity") if isinstance(
        (compliance_audit or {}).get("inconsistency_severity"), dict
    ) else {}
    blocker_count = _safe_int(severity_map.get("blocker"), 0)
    major_count = _safe_int(severity_map.get("major"), 0)
    minor_count = _safe_int(severity_map.get("minor"), 0)

    boq = boq_governance if isinstance(boq_governance, dict) else {}
    boq_enabled = bool(boq.get("enabled"))
    boq_trusted = bool(boq.get("trusted")) if boq_enabled else True
    boq_score = round(_safe_float(boq.get("overall_trust_score"), 0.0), 6) if boq_enabled else 0.0
    boq_threshold = round(_safe_float(boq.get("trust_threshold"), 0.0), 6) if boq_enabled else 0.0
    boq_parse_error_rate = round(_safe_float(boq.get("parse_error_rate"), 0.0), 6) if boq_enabled else 0.0

    gap_breakdown = _gap_breakdown(gaps)
    recommended_actions = _recommended_actions_from_gaps(gaps)
    if boq_enabled and not boq_trusted:
        recommended_actions.insert(0, "修复BOQ低置信度与异常条目，完成人工复核队列闭环")
    recommended_actions = recommended_actions[:8]

    thresholds = {
        "score_hit_rate_min": 0.92,
        "graph_hit_rate_min": 0.92,
        "fail_fast_trigger_rate_max": 0.08,
        "sentence_trace_ratio_min": 0.90,
        "graph_binding_rate_min": 0.90,
        "numeric_density_min": 0.95,
        "boq_trust_score_min": boq_threshold if boq_enabled else 0.0,
    }
    checks = {
        "score_hit_rate_ok": score_hit_rate >= float(thresholds["score_hit_rate_min"]),
        "graph_hit_rate_ok": graph_hit_rate >= float(thresholds["graph_hit_rate_min"]),
        "fail_fast_trigger_rate_ok": fail_fast_trigger_rate <= float(thresholds["fail_fast_trigger_rate_max"]),
        "sentence_trace_ratio_ok": trace_ratio >= float(thresholds["sentence_trace_ratio_min"]),
        "graph_binding_rate_ok": graph_binding_rate >= float(thresholds["graph_binding_rate_min"]),
        "numeric_density_ok": numeric_density >= float(thresholds["numeric_density_min"]),
        "consistency_blocker_ok": blocker_count == 0,
        "boq_trust_ok": bool(boq_trusted),
    }
    overall_ok = all(bool(v) for v in checks.values())

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "overall_ok": overall_ok,
        "metrics": {
            "dimension_total": dimension_total,
            "score_point_total": int(score_point_total),
            "score_point_hit": int(score_point_hit),
            "score_hit_rate": score_hit_rate,
            "graph_hit_rate": graph_hit_rate,
            "fail_fast_trigger_rate": fail_fast_trigger_rate,
            "pre_healing_gap_count": int(pre_healing_gap_count),
            "post_healing_gap_count": int(post_gap_count),
            "self_healing_release_rate": self_heal_release_rate,
            "sentence_trace_ratio": trace_ratio,
            "graph_binding_rate": graph_binding_rate,
            "numeric_sentence_density": numeric_density,
            "evidence_strength_avg": evidence_strength_avg,
            "consistency_total": int(consistency_total),
            "consistency_blocker_count": blocker_count,
            "consistency_major_count": major_count,
            "consistency_minor_count": minor_count,
            "boq_trust_enabled": boq_enabled,
            "boq_trust_score": boq_score,
            "boq_trust_threshold": boq_threshold,
            "boq_parse_error_rate": boq_parse_error_rate,
        },
        "thresholds": thresholds,
        "checks": checks,
        "gate_breakdown": gap_breakdown,
        "recommended_actions": recommended_actions,
    }


def build_tactical_effects(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    logs: List[Dict[str, Any]] = []
    shield_triggered = 0
    booster_triggered = 0
    estimated_score_gain = 0.0
    trap_logic_total = 0
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip()
        hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
        shield = hit.get("competitor_shield") if isinstance(hit.get("competitor_shield"), dict) else {}
        booster = hit.get("qt_score_booster") if isinstance(hit.get("qt_score_booster"), dict) else {}
        trap_logic = str(shield.get("trap_logic") or shield.get("trap") or "").strip()
        if trap_logic:
            shield_triggered += 1
            trap_logic_total += 1

        score_weight = _safe_float(booster.get("score_weight"), _safe_float(booster.get("weight"), 0.0))
        if score_weight <= 0 and isinstance(booster.get("expected_score_gain"), (int, float)):
            score_weight = _safe_float(booster.get("expected_score_gain"), 0.0)
        if score_weight > 0:
            booster_triggered += 1
            estimated_score_gain += score_weight

        if trap_logic or score_weight > 0:
            logs.append(
                {
                    "section": title,
                    "node_id": hit.get("node_id"),
                    "shield_triggered": bool(trap_logic),
                    "booster_triggered": score_weight > 0,
                    "trap_logic": trap_logic[:120],
                    "estimated_gain": round(max(0.0, score_weight), 4),
                }
            )

    return {
        "enabled": True,
        "shield_triggered_count": shield_triggered,
        "booster_triggered_count": booster_triggered,
        "trap_logic_count": trap_logic_total,
        "estimated_score_gain": round(estimated_score_gain, 4),
        "logs": logs[:120],
    }


def build_missing_enrichment_draft(
    *,
    gaps: List[Dict[str, Any]],
    output_path: Path | str,
) -> Dict[str, Any]:
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        dim = str(gap.get("dimension") or "未知维度").strip()
        grouped.setdefault(dim, []).append(gap)

    draft_nodes: List[Dict[str, Any]] = []
    for dim, rows in grouped.items():
        all_keywords: List[str] = []
        all_params: List[str] = []
        for row in rows:
            for kw in row.get("required_keywords") or []:
                text = str(kw).strip()
                if text and text not in all_keywords:
                    all_keywords.append(text)
            for p in row.get("suggested_parameters") or []:
                text = str(p).strip()
                if text and text not in all_params:
                    all_params.append(text)
        node_type = "FormulaNode" if any(str(r.get("type") or "") == "formula_missing" for r in rows) else "EngineeringNode"
        draft_nodes.append(
            {
                "node_id": f"DRAFT-{dim}-AUTO",
                "node_type": node_type,
                "dimension": dim,
                "keywords": all_keywords[:20],
                "required_params": all_params[:20],
                "source_hierarchy": "国标",
                "reference_standard": ["GB 50300-2013"],
                "is_auto_generated": True,
                "from_gap_types": sorted({str(x.get("type") or "") for x in rows if isinstance(x, dict)}),
            }
        )

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "gap_count": len(gaps),
        "dimension_count": len(grouped),
        "draft_nodes": draft_nodes,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "saved_at": str(out), "draft_node_count": len(draft_nodes)}


def score_variant_bundle(
    *,
    name: str,
    sections: List[Dict[str, Any]],
    graph_audit: Dict[str, Any],
    compliance_audit: Dict[str, Any],
    sentence_evidence_stats: Dict[str, Any],
) -> Dict[str, Any]:
    graph_ok_rate = round(
        _ratio(
            sum(1 for x in (graph_audit.get("checks") or []) if isinstance(x, dict) and bool(x.get("ok"))),
            max(len(graph_audit.get("checks") or []), 1),
        ),
        6,
    )
    trace_ratio = round(_safe_float(sentence_evidence_stats.get("trace_coverage_ratio"), 0.0), 6)
    numeric_density = _sentence_numeric_density(sections)
    binding_rate = _graph_binding_rate(sections)
    evidence_avg = _evidence_strength_avg(sections)
    inconsistency = _safe_int(compliance_audit.get("inconsistency_count"), 0)
    blocker = _safe_int((compliance_audit.get("inconsistency_severity") or {}).get("blocker"), 0)

    # Composite score for A/B winner selection.
    composite = (
        graph_ok_rate * 0.25
        + trace_ratio * 0.20
        + numeric_density * 0.20
        + binding_rate * 0.20
        + evidence_avg * 0.15
        - min(0.30, inconsistency * 0.02)
        - min(0.40, blocker * 0.08)
    )
    composite = round(max(0.0, min(1.0, composite)), 6)
    return {
        "name": name,
        "graph_ok_rate": graph_ok_rate,
        "trace_ratio": trace_ratio,
        "numeric_density": numeric_density,
        "binding_rate": binding_rate,
        "evidence_strength_avg": evidence_avg,
        "inconsistency_count": inconsistency,
        "blocker_count": blocker,
        "composite_score": composite,
    }


def compare_ab_variants(variant_a: Dict[str, Any], variant_b: Dict[str, Any]) -> Dict[str, Any]:
    a = score_variant_bundle(
        name="A",
        sections=variant_a.get("sections") or [],
        graph_audit=variant_a.get("graph_audit") or {},
        compliance_audit=variant_a.get("compliance_audit") or {},
        sentence_evidence_stats=variant_a.get("sentence_evidence_stats") or {},
    )
    b = score_variant_bundle(
        name="B",
        sections=variant_b.get("sections") or [],
        graph_audit=variant_b.get("graph_audit") or {},
        compliance_audit=variant_b.get("compliance_audit") or {},
        sentence_evidence_stats=variant_b.get("sentence_evidence_stats") or {},
    )
    winner = "A" if float(a.get("composite_score") or 0.0) >= float(b.get("composite_score") or 0.0) else "B"
    return {
        "enabled": True,
        "winner": winner,
        "variant_a": a,
        "variant_b": b,
        "delta": round(float(a.get("composite_score") or 0.0) - float(b.get("composite_score") or 0.0), 6),
    }


def write_hit_rate_dashboard(
    *,
    dashboard: Dict[str, Any],
    out_json: Path | str,
    out_md: Path | str,
) -> Dict[str, Any]:
    j = Path(out_json).expanduser().resolve()
    m = Path(out_md).expanduser().resolve()
    j.parent.mkdir(parents=True, exist_ok=True)
    m.parent.mkdir(parents=True, exist_ok=True)
    j.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics = dashboard.get("metrics") if isinstance(dashboard.get("metrics"), dict) else {}
    checks = dashboard.get("checks") if isinstance(dashboard.get("checks"), dict) else {}
    lines = [
        "# Hit-Rate Dashboard",
        "",
        f"- Generated At: {dashboard.get('generated_at')}",
        f"- Overall OK: {bool(dashboard.get('overall_ok'))}",
        "",
        "## Metrics",
        "",
        f"- Score Hit Rate: {float(metrics.get('score_hit_rate') or 0.0):.4f}",
        f"- Graph Hit Rate: {float(metrics.get('graph_hit_rate') or 0.0):.4f}",
        f"- Fail-Fast Trigger Rate: {float(metrics.get('fail_fast_trigger_rate') or 0.0):.4f}",
        f"- Self-Healing Release Rate: {float(metrics.get('self_healing_release_rate') or 0.0):.4f}",
        f"- Sentence Trace Ratio: {float(metrics.get('sentence_trace_ratio') or 0.0):.4f}",
        f"- Graph Binding Rate: {float(metrics.get('graph_binding_rate') or 0.0):.4f}",
        f"- Numeric Sentence Density: {float(metrics.get('numeric_sentence_density') or 0.0):.4f}",
        f"- Evidence Strength Avg: {float(metrics.get('evidence_strength_avg') or 0.0):.4f}",
        f"- Consistency Blockers: {int(metrics.get('consistency_blocker_count') or 0)}",
        f"- BOQ Trust Enabled: {bool(metrics.get('boq_trust_enabled'))}",
        f"- BOQ Trust Score: {float(metrics.get('boq_trust_score') or 0.0):.4f}",
        f"- BOQ Parse Error Rate: {float(metrics.get('boq_parse_error_rate') or 0.0):.4f}",
        "",
        "## Checks",
        "",
    ]
    for k in sorted(checks.keys()):
        lines.append(f"- {k}: {bool(checks.get(k))}")
    gate_breakdown = dashboard.get("gate_breakdown") if isinstance(dashboard.get("gate_breakdown"), dict) else {}
    lines.extend(["", "## Gate Breakdown", ""])
    if gate_breakdown:
        for k, v in gate_breakdown.items():
            lines.append(f"- {k}: {int(v)}")
    else:
        lines.append("- none")
    actions = dashboard.get("recommended_actions") if isinstance(dashboard.get("recommended_actions"), list) else []
    lines.extend(["", "## Recommended Actions", ""])
    if actions:
        for item in actions:
            lines.append(f"- {str(item)}")
    else:
        lines.append("- none")
    m.write_text("\n".join(lines), encoding="utf-8")
    return {"ok": True, "json_path": str(j), "md_path": str(m)}
