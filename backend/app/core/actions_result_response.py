from __future__ import annotations

from typing import Any, Callable


def build_actions_result_not_done_response(
    *,
    job_id: str,
    status: Any,
    error: Any,
    trace_meta: dict[str, str],
) -> dict[str, Any]:
    return {
        "ok": False,
        "code": "job_not_done",
        "message": "job not done",
        "job_id": job_id,
        "status": status,
        "error": error,
        "request_id": trace_meta.get("request_id") or None,
        "trace_id": trace_meta.get("trace_id") or None,
        "next_action": "poll /actions/job_status until status=done",
    }


def build_actions_result_response(
    *,
    job_id: str,
    trace_meta: dict[str, str],
    result: dict[str, Any],
    variants: list[Any],
    variant: int,
    include_sections: bool,
    max_chars: int,
    result_contract_view_fn: Callable[[str, dict, int], dict[str, Any]],
    download_artifact_path_fn: Callable[[dict, str, int], str | None],
) -> dict[str, Any]:
    current_variant = max(1, int(variant or 1))
    rec = variants[current_variant - 1] if current_variant <= len(variants) else variants[0]
    mode_policy = rec.get("mode_policy") if isinstance(rec.get("mode_policy"), dict) else {}
    generation_trace = rec.get("generation_trace") if isinstance(rec.get("generation_trace"), dict) else {}
    logic_template = rec.get("logic_template") if isinstance(rec.get("logic_template"), dict) else {}
    logic_template_id = str(rec.get("logic_template_id") or logic_template.get("id") or "").strip() or None
    logic_template_name = str(rec.get("logic_template_name") or logic_template.get("name") or "").strip() or None
    contract_view = result_contract_view_fn(job_id, result, current_variant)
    response = {
        "ok": True,
        "variant_id": rec.get("variant_id") or current_variant,
        "logic_template_id": logic_template_id,
        "logic_template_name": logic_template_name,
        "topic": rec.get("topic"),
        "outline": rec.get("outline"),
        "boq_focus": rec.get("boq_focus"),
        "quality_checks": rec.get("quality_checks"),
        "request_id": trace_meta.get("request_id") or None,
        "trace_id": trace_meta.get("trace_id") or None,
        "generation_mode_summary": {
            "profile": str(mode_policy.get("profile") or generation_trace.get("generation_mode") or rec.get("generation_mode") or "").strip() or None,
            "mode_effective": str(
                mode_policy.get("mode_effective")
                or generation_trace.get("mode_effective")
                or generation_trace.get("generation_mode")
                or rec.get("generation_mode")
                or ""
            ).strip()
            or None,
            "stable_output": bool(mode_policy.get("stable_output", generation_trace.get("stable_output", False))),
            "deterministic_variant_forced": bool(
                mode_policy.get("deterministic_variant_forced", generation_trace.get("deterministic_variant_forced", False))
            ),
            "deterministic_logic_template_id": str(
                mode_policy.get("deterministic_logic_template_id")
                or generation_trace.get("deterministic_logic_template_id")
                or logic_template_id
                or ""
            ).strip()
            or None,
        },
        "resource_usage_summary": rec.get("resource_usage_summary") if isinstance(rec.get("resource_usage_summary"), dict) else {},
        "job_resource_usage_summary": result.get("resource_usage_summary") if isinstance(result.get("resource_usage_summary"), dict) else {},
        "files": {
            "json": result.get("json"),
            "result_bundle_json": download_artifact_path_fn(result, "result_bundle_json", current_variant),
            "docx": download_artifact_path_fn(result, "docx", current_variant),
            "compare_docx": download_artifact_path_fn(result, "compare_docx", current_variant),
            "focus_xlsx": download_artifact_path_fn(result, "focus_xlsx", current_variant),
            "score_overview_xlsx": download_artifact_path_fn(result, "score_overview_xlsx", current_variant),
            "expert_review_docx": download_artifact_path_fn(result, "expert_review_docx", current_variant),
        },
    }
    response.update(contract_view)
    if include_sections:
        trimmed = []
        section_max_chars = max(200, min(20000, int(max_chars or 4000)))
        for sec in rec.get("sections") or []:
            text = sec.get("content") or ""
            if len(text) > section_max_chars:
                text = text[:section_max_chars] + "..."
            trimmed.append({"title": sec.get("title"), "content": text, "agent_role": sec.get("agent_role")})
        response["sections"] = trimmed
    return response
