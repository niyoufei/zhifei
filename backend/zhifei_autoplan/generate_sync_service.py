from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from backend.zhifei_autoplan import generate_sync_postprocess_service as postprocess_core


async def run_generate_sync(
    *,
    raw_payload: dict[str, Any],
    prepare_runtime_payload_fn: Callable[[dict[str, Any]], dict[str, Any]],
    build_variant_plan_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    normalize_logic_template_id_fn: Callable[[Any], str | None],
    run_autoplan_fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = prepare_runtime_payload_fn(raw_payload)
    variant_plan = build_variant_plan_fn(payload)
    payload["_variant_plan"] = variant_plan
    payload["_variant_ids"] = [int(v.get("variant_id") or 1) for v in variant_plan]
    results: list[dict[str, Any]] = []
    for item in variant_plan:
        local_payload = json.loads(json.dumps(payload))
        local_payload["variant_id"] = int(item.get("variant_id") or 1)
        tid = normalize_logic_template_id_fn(item.get("logic_template_id"))
        if tid:
            local_payload["logic_template_id"] = tid
        results.append(await run_autoplan_fn(local_payload))
    return payload, results


async def execute_generate_sync_request(
    *,
    raw_payload: dict[str, Any],
    prepare_runtime_payload_fn: Callable[[dict[str, Any]], dict[str, Any]],
    build_variant_plan_fn: Callable[[dict[str, Any]], list[dict[str, Any]]],
    normalize_logic_template_id_fn: Callable[[Any], str | None],
    run_autoplan_fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    load_params_fn: Callable[[], dict[str, Any]],
    rebuild_postprocessed_fn: Callable[..., None],
    workspace_dir_from_payload_fn: Callable[[dict[str, Any]], str | None],
    save_outputs_fn: Callable[..., dict[str, Any]],
    compute_variant_similarity_fn: Callable[..., dict[str, Any]],
    apply_diversity_autofix_fn: Callable[..., bool],
) -> dict[str, Any]:
    payload, results = await run_generate_sync(
        raw_payload=raw_payload,
        prepare_runtime_payload_fn=prepare_runtime_payload_fn,
        build_variant_plan_fn=build_variant_plan_fn,
        normalize_logic_template_id_fn=normalize_logic_template_id_fn,
        run_autoplan_fn=run_autoplan_fn,
    )
    postprocess_core.postprocess_generate_sync_results(
        payload=payload,
        results=results,
        load_params_fn=load_params_fn,
        rebuild_postprocessed_fn=rebuild_postprocessed_fn,
        workspace_dir_from_payload_fn=workspace_dir_from_payload_fn,
        compute_variant_similarity_fn=compute_variant_similarity_fn,
        apply_diversity_autofix_fn=apply_diversity_autofix_fn,
    )
    outputs = save_outputs_fn("actions_generated", results, workspace_dir=workspace_dir_from_payload_fn(payload))
    return build_generate_sync_response(results=results, outputs=outputs)


def build_generate_sync_response(
    *,
    results: list[dict[str, Any]],
    outputs: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": results,
        "quality": [v.get("quality_checks") for v in results],
        "files": outputs,
    }
