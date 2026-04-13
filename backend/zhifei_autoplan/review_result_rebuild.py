from __future__ import annotations

from typing import Any, Dict, List

from backend.zhifei_autoplan import result_persistence
from backend.zhifei_autoplan import result_metadata_builder as metadata_core
from backend.zhifei_autoplan import result_variant_summary_builder as summary_core


def build_blocking_issue_summary(
    *,
    quality_checks: Dict[str, Any] | None,
    quality_gate: Dict[str, Any] | None,
    limit: int = 8,
) -> Dict[str, Any]:
    return metadata_core.build_blocking_issue_summary(
        quality_checks=quality_checks,
        quality_gate=quality_gate,
        limit=limit,
    )


def build_review_variant_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for idx, item in enumerate(results or [], start=1):
        if not isinstance(item, dict):
            continue
        sections = item.get("sections") if isinstance(item.get("sections"), list) else []
        generation_trace = item.get("generation_trace") if isinstance(item.get("generation_trace"), dict) else {}
        logic_template = item.get("logic_template") if isinstance(item.get("logic_template"), dict) else {}
        logic_template_id = str(item.get("logic_template_id") or logic_template.get("id") or "").strip() or None
        logic_template_name = str(item.get("logic_template_name") or logic_template.get("name") or "").strip() or None
        quality = item.get("quality_checks") if isinstance(item.get("quality_checks"), dict) else {}
        quality_gate = item.get("quality_gate") if isinstance(item.get("quality_gate"), dict) else {}
        remediation_strategy_audit = (
            item.get("remediation_strategy_audit") if isinstance(item.get("remediation_strategy_audit"), dict) else {}
        )
        remediation_execution_audit = (
            item.get("remediation_execution_audit") if isinstance(item.get("remediation_execution_audit"), dict) else {}
        )
        section_runtime_budget_preview = item.get("section_runtime_budget_preview")
        if not isinstance(section_runtime_budget_preview, list):
            section_runtime_budget_preview = []
        rows.append(
            summary_core.build_variant_summary_row(
                item=item,
                variant_index=idx,
                logic_template_id=logic_template_id,
                logic_template_name=logic_template_name,
                section_count=len([sec for sec in sections if isinstance(sec, dict)]),
                section_runtime_budget_preview=section_runtime_budget_preview,
                remediation_strategy_audit=remediation_strategy_audit,
                remediation_execution_audit=remediation_execution_audit,
            )
        )
    return {"variant_count": len(rows), "variants": rows}


def build_review_result_metadata(results: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = build_review_variant_summary(results)
    rows = summary.get("variants") if isinstance(summary.get("variants"), list) else []
    return metadata_core.build_result_metadata_from_rows(
        results=results,
        payload=payload,
        rows=rows,
        blocking_summary_builder=build_blocking_issue_summary,
    )


def write_review_result_bundle(
    job_id: str,
    *,
    payload: Dict[str, Any],
    outputs: Dict[str, Any],
    result_metadata: Dict[str, Any],
    resource_usage_summary: Dict[str, Any],
    variant_summary: Dict[str, Any],
    workspace_dir: str | None = None,
) -> str:
    del workspace_dir
    return result_persistence.write_result_bundle_file(
        job_id=job_id,
        payload=payload,
        outputs=outputs,
        result_metadata=result_metadata,
        resource_usage_summary=resource_usage_summary,
        variant_summary=variant_summary,
    )


def build_review_job_result(
    *,
    outputs: Dict[str, Any],
    resource_usage_summary: Dict[str, Any],
    result_bundle_json: str,
    result_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    return result_persistence.build_job_result_payload(
        outputs=outputs,
        resource_usage_summary=resource_usage_summary,
        result_bundle_json=result_bundle_json,
        result_metadata=result_metadata,
    )
