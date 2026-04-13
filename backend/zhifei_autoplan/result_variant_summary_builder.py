from __future__ import annotations

from typing import Any, Dict


def build_variant_summary_row(
    *,
    item: Dict[str, Any],
    variant_index: int,
    logic_template_id: str | None,
    logic_template_name: str | None,
    section_count: int,
    section_runtime_budget_preview: list[dict[str, Any]],
    remediation_strategy_audit: dict[str, Any],
    remediation_execution_audit: dict[str, Any],
    extra_fields: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    generation_trace = item.get("generation_trace") if isinstance(item.get("generation_trace"), dict) else {}
    return {
        "variant_index": variant_index,
        "variant_id": item.get("variant_id"),
        "topic": str(item.get("topic") or "").strip(),
        "generation_mode": str(generation_trace.get("generation_mode") or item.get("generation_mode") or "").strip() or None,
        "mode_effective": str(
            generation_trace.get("mode_effective")
            or generation_trace.get("generation_mode")
            or item.get("generation_mode")
            or ""
        ).strip()
        or None,
        "stable_output": bool(generation_trace.get("stable_output", False)),
        "deterministic_variant_forced": bool(generation_trace.get("deterministic_variant_forced", False)),
        "deterministic_logic_template_id": str(
            generation_trace.get("deterministic_logic_template_id") or logic_template_id or ""
        ).strip()
        or None,
        "logic_template_id": logic_template_id,
        "logic_template_name": logic_template_name,
        "section_count": int(section_count or 0),
        "quality_score": (
            item.get("quality_checks", {}).get("score")
            if isinstance(item.get("quality_checks"), dict)
            else None
        ),
        "quality_gate_ok": bool(
            (item.get("quality_gate") or {}).get("ok", False)
            if isinstance(item.get("quality_gate"), dict)
            else False
        ),
        "quality_gate_failed_count": len((item.get("quality_gate") or {}).get("failed") or [])
        if isinstance(item.get("quality_gate"), dict) and isinstance((item.get("quality_gate") or {}).get("failed"), list)
        else 0,
        "pipeline_stages": generation_trace.get("pipeline_stages") if isinstance(generation_trace.get("pipeline_stages"), list) else item.get("pipeline_stages"),
        "retrieval_cache": generation_trace.get("retrieval_cache") if isinstance(generation_trace.get("retrieval_cache"), dict) else item.get("retrieval_cache"),
        "self_evolution": generation_trace.get("self_evolution") if isinstance(generation_trace.get("self_evolution"), dict) else {},
        "remediation_strategy_audit": remediation_strategy_audit,
        "remediation_execution_audit": remediation_execution_audit,
        "section_runtime_budget_preview": section_runtime_budget_preview,
        "resource_usage_summary": item.get("resource_usage_summary") if isinstance(item.get("resource_usage_summary"), dict) else {},
        **(extra_fields if isinstance(extra_fields, dict) else {}),
    }
