from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def build_actions_job_status_response(
    *,
    job_id: str,
    job: dict[str, Any],
    trace_meta: dict[str, str],
    result_contract_view_fn: Callable[[str, dict, int], dict[str, Any]],
) -> dict[str, Any]:
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    out = {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "error": job.get("error"),
        "request_id": trace_meta.get("request_id") or None,
        "trace_id": trace_meta.get("trace_id") or None,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "heartbeat_at": job.get("heartbeat_at"),
        "stage_artifacts_dir": job.get("stage_artifacts_dir"),
        "progress": job.get("progress") if isinstance(job.get("progress"), dict) else {},
        "agent_runtime": job.get("agent_runtime") if isinstance(job.get("agent_runtime"), dict) else {},
        "worker": job.get("worker") if isinstance(job.get("worker"), dict) else {},
        "sla": job.get("sla") if isinstance(job.get("sla"), dict) else {},
        "generation_mode_summary": {
            "profile": str(mode_policy.get("profile") or payload.get("generation_mode") or "").strip() or None,
            "mode_effective": str(mode_policy.get("mode_effective") or payload.get("generation_mode") or "").strip() or None,
            "stable_output": bool(mode_policy.get("stable_output", False)),
            "deterministic_variant_forced": bool(mode_policy.get("deterministic_variant_forced", False)),
            "deterministic_logic_template_id": str(mode_policy.get("deterministic_logic_template_id") or payload.get("logic_template_id") or "").strip() or None,
        },
    }
    result = job.get("result") or {}
    if isinstance(result, dict):
        contract_view = result_contract_view_fn(job_id, result, 1)
        result_generation_mode_summary = result.get("generation_mode_summary") if isinstance(result.get("generation_mode_summary"), dict) else {}
        if result_generation_mode_summary:
            out["generation_mode_summary"] = {
                "profile": str(result_generation_mode_summary.get("profile") or out["generation_mode_summary"].get("profile") or "").strip() or None,
                "mode_effective": str(result_generation_mode_summary.get("mode_effective") or out["generation_mode_summary"].get("mode_effective") or "").strip() or None,
                "stable_output": bool(result_generation_mode_summary.get("stable_output", out["generation_mode_summary"].get("stable_output", False))),
                "deterministic_variant_forced": bool(
                    result_generation_mode_summary.get(
                        "deterministic_variant_forced",
                        out["generation_mode_summary"].get("deterministic_variant_forced", False),
                    )
                ),
                "deterministic_logic_template_id": str(
                    result_generation_mode_summary.get("deterministic_logic_template_id")
                    or out["generation_mode_summary"].get("deterministic_logic_template_id")
                    or ""
                ).strip()
                or None,
            }
        out["files"] = result
        out["resource_usage_summary"] = result.get("resource_usage_summary") if isinstance(result.get("resource_usage_summary"), dict) else {}
        out.update(contract_view)
        if isinstance(result.get("runtime_by_variant"), dict):
            out["runtime_by_variant"] = result.get("runtime_by_variant")
        if isinstance(result.get("quality_by_variant"), dict):
            out["quality_by_variant"] = result.get("quality_by_variant")
            quality_rows = sorted(
                [item for item in result["quality_by_variant"].values() if isinstance(item, dict)],
                key=lambda item: (int(item.get("variant_index") or 0), str(item.get("variant_id") or "")),
            )
            if quality_rows:
                out["quality_ok"] = [bool(item.get("quality_gate_ok", False)) for item in quality_rows]
        if isinstance(result.get("blocking_issue_summary_by_variant"), dict):
            out["blocking_issue_summary_by_variant"] = result.get("blocking_issue_summary_by_variant")
        if isinstance(result.get("reference_quality_summary_by_variant"), dict):
            out["reference_quality_summary_by_variant"] = result.get("reference_quality_summary_by_variant")
        if isinstance(result.get("reference_quality_summary"), dict):
            out["reference_quality_summary"] = result.get("reference_quality_summary")
        runtime_rows = out.get("runtime_by_variant") if isinstance(out.get("runtime_by_variant"), dict) else {}
        quality_rows_map = out.get("quality_by_variant") if isinstance(out.get("quality_by_variant"), dict) else {}
        variant_count = max(len(runtime_rows), len(quality_rows_map))
        if variant_count > 0:
            out["variants"] = variant_count
        if str(result.get("logic_template_id") or "").strip():
            out["logic_template_id"] = str(result.get("logic_template_id") or "").strip() or None
        if str(result.get("logic_template_name") or "").strip():
            out["logic_template_name"] = str(result.get("logic_template_name") or "").strip() or None
        json_path = result.get("json")
        if json_path and Path(json_path).exists():
            try:
                data = json.loads(Path(json_path).read_text(encoding="utf-8"))
                variants = data.get("variants") or []
                out["variants"] = len(variants)
                out["quality_ok"] = [bool((variant.get("quality_checks") or {}).get("structure", {}).get("ok")) for variant in variants]
                if variants and isinstance(variants[0], dict):
                    first = variants[0]
                    logic_template = first.get("logic_template") if isinstance(first.get("logic_template"), dict) else {}
                    out["logic_template_id"] = str(first.get("logic_template_id") or logic_template.get("id") or "").strip() or None
                    out["logic_template_name"] = str(first.get("logic_template_name") or logic_template.get("name") or "").strip() or None
                    multi_agent = first.get("multi_agent")
                    if isinstance(multi_agent, dict):
                        out["multi_agent"] = multi_agent
            except Exception:
                pass
    return {"ok": True, "job": out}
