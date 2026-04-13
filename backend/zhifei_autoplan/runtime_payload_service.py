from __future__ import annotations

from typing import Any, Callable


def merge_plan_defaults(
    payload: dict[str, Any],
    *,
    workspace_dir_from_payload_fn: Callable[[dict[str, Any] | None], str | None],
    load_plan_fn: Callable[..., Any],
    load_tender_matrix_fn: Callable[..., Any],
    normalize_selected_templates_fn: Callable[[Any], list[str]],
    apply_generation_mode_policy_fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    pid = str(payload.get("project_id") or "").strip() or None
    workspace_dir = workspace_dir_from_payload_fn(payload)
    plan = load_plan_fn(project_id=pid, workspace_dir=workspace_dir)
    if not isinstance(plan, dict):
        plan = {}
    tender = load_tender_matrix_fn(project_id=pid, workspace_dir=workspace_dir) or {}
    if not payload.get("outline"):
        payload["outline"] = plan.get("outline") or []
    if not payload.get("outline"):
        payload["outline"] = tender.get("outline") or []
    if payload.get("chapter_requirements") is None:
        payload["chapter_requirements"] = plan.get("chapter_requirements") or {}
    if not payload.get("chapter_requirements"):
        payload["chapter_requirements"] = tender.get("chapter_requirements") or {}
    if payload.get("style") is None:
        payload["style"] = plan.get("style") or {}
    if not payload.get("style"):
        payload["style"] = tender.get("style") or {}
    if payload.get("chapter_pages") is None:
        payload["chapter_pages"] = plan.get("chapter_pages") or {}
    if not payload.get("chapter_pages"):
        payload["chapter_pages"] = tender.get("chapter_pages") or {}
    if payload.get("front_matter_outline") is None:
        payload["front_matter_outline"] = plan.get("front_matter_outline") or {}
    if payload.get("total_pages_target") is None:
        payload["total_pages_target"] = plan.get("total_pages_target")
    if payload.get("quality_strict") is None:
        payload["quality_strict"] = plan.get("quality_strict", True)
    if payload.get("auto_remediate") is None:
        payload["auto_remediate"] = plan.get("auto_remediate", True)
    if payload.get("remediate_mode") is None:
        payload["remediate_mode"] = plan.get("remediate_mode", "template")
    if payload.get("compare_mode") is None:
        payload["compare_mode"] = plan.get("compare_mode", "summary")
    if payload.get("compare_max_chars") is None:
        plan_compare_max_chars = plan.get("compare_max_chars")
        if plan_compare_max_chars is not None:
            payload["compare_max_chars"] = plan_compare_max_chars
    if payload.get("compare_titles") is None:
        payload["compare_titles"] = plan.get("compare_titles")
    if payload.get("case_library") is None:
        payload["case_library"] = plan.get("case_library")
    if payload.get("image_library") is None:
        payload["image_library"] = plan.get("image_library")
    if payload.get("selected_templates") is None:
        payload["selected_templates"] = plan.get("selected_templates")
    payload["selected_templates"] = normalize_selected_templates_fn(payload.get("selected_templates"))
    if payload.get("selected_templates"):
        payload["variants"] = len(payload["selected_templates"])
    if not payload.get("variants"):
        payload["variants"] = plan.get("variants") or 1
    if payload.get("strict_tender_outline") is None:
        payload["strict_tender_outline"] = plan.get("strict_tender_outline", False)
    if not payload.get("project_type"):
        payload["project_type"] = plan.get("project_type")
    if payload.get("generation_mode") is None:
        payload["generation_mode"] = plan.get("generation_mode")
    if payload.get("global_instruction") is None:
        payload["global_instruction"] = plan.get("global_instruction")
    return apply_generation_mode_policy_fn(payload)


def prepare_runtime_payload(
    payload: dict[str, Any],
    *,
    resolve_workspace_context_fn: Callable[..., dict[str, str]],
    merge_plan_defaults_fn: Callable[[dict[str, Any]], dict[str, Any]],
    apply_server_provider_routing_fn: Callable[[dict[str, Any]], dict[str, Any]],
    uuid_hex_fn: Callable[[], str],
) -> dict[str, Any]:
    workspace = resolve_workspace_context_fn(
        session_id=str(payload.get("session_id") or "").strip() or None,
        workspace_dir=str(payload.get("workspace_dir") or "").strip() or None,
    )
    payload["session_id"] = workspace["session_id"]
    payload["workspace_dir"] = workspace["workspace_dir"]
    prepared = apply_server_provider_routing_fn(merge_plan_defaults_fn(payload))
    trace_id = str(prepared.get("trace_id") or prepared.get("request_id") or "").strip() or uuid_hex_fn()
    prepared["request_id"] = trace_id
    prepared["trace_id"] = trace_id
    return prepared
