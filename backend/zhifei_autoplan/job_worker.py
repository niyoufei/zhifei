from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.generation_mode_policy import (
    apply_generation_mode_policy,
    normalize_logic_template_id,
)
from backend.zhifei_autoplan.output_artifacts import save_outputs
from backend.zhifei_autoplan.postprocessed_artifacts import rebuild_postprocessed_artifacts
from backend.zhifei_autoplan import result_persistence
from backend.zhifei_autoplan import result_metadata_builder as metadata_core
from backend.zhifei_autoplan import result_variant_summary_builder as summary_core
from backend.zhifei_autoplan.job_store import get_job, update_job
from backend.zhifei_autoplan.orchestrator import run_autoplan
from backend.zhifei_autoplan.params_runtime import load_params
from backend.zhifei_autoplan.resource_audit import append_resource_event, summarize_variants
from backend.zhifei_autoplan.run_contract import (
    build_stage_artifact_envelope,
    contract_fingerprint,
    extract_outputs_from_result_bundle,
    load_result_bundle,
    resolve_contract_stamp,
    result_bundle_artifacts_complete,
)
from backend.zhifei_autoplan.self_evolution import (
    build_task_parallelism_hint,
    load_task_parallelism_profile,
    record_runtime_learning,
    record_task_parallelism_learning,
)
from backend.zhifei_autoplan.case_library_service import summarize_case_reference_pack
from backend.zhifei_autoplan.image_library import summarize_image_selection_pack
from backend.zhifei_autoplan.variant_cycle import reserve_variant_ids
from backend.zhifei_autoplan.workspace import resolve_workspace_dir, workspace_paths


WORKER_LOG_DIR = Path("logs/job_workers")
WORKER_LOG_DIR.mkdir(parents=True, exist_ok=True)
STAGE_RUN_DIR = Path("build/_stage_runs")
STAGE_RUN_DIR.mkdir(parents=True, exist_ok=True)

# Compatibility seam for existing tests and monkeypatch points.
_save_outputs = save_outputs
_rebuild_postprocessed_artifacts = rebuild_postprocessed_artifacts


def _worker_log(job_id: str, message: str, *, workspace_dir: str | None = None) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"[{stamp}][job:{str(job_id or '').strip() or 'unknown'}] {str(message or '').strip()}"
    if workspace_dir:
        try:
            worker_logs = workspace_paths(workspace_dir)["worker_logs"]
            worker_logs.mkdir(parents=True, exist_ok=True)
            with (worker_logs / f"{str(job_id or '').strip() or 'unknown'}.log").open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass
    print(line, flush=True)


def _get_job_record(job_id: str, *, workspace_dir: str | None = None):
    try:
        return get_job(job_id, workspace_dir=workspace_dir)
    except TypeError as exc:
        if "workspace_dir" not in str(exc):
            raise
        return get_job(job_id)


def _update_job_record(job_id: str, *, workspace_dir: str | None = None, **kwargs: Any):
    try:
        return update_job(job_id, workspace_dir=workspace_dir, **kwargs)
    except TypeError as exc:
        if "workspace_dir" not in str(exc):
            raise
        return update_job(job_id, **kwargs)


def _save_outputs_compat(prefix: str, results: List[Dict[str, Any]], *, workspace_dir: str | None = None):
    try:
        return _save_outputs(prefix, results, workspace_dir=workspace_dir)
    except TypeError as exc:
        if "workspace_dir" not in str(exc):
            raise
        return _save_outputs(prefix, results)


def _rebuild_postprocessed_artifacts_compat(
    results: List[Dict[str, Any]],
    *,
    payload: Dict[str, Any],
    report: Dict[str, Any],
    params: Dict[str, Any],
    workspace_dir: str | None = None,
) -> None:
    try:
        _rebuild_postprocessed_artifacts(
            results,
            payload=payload,
            report=report,
            params=params,
            workspace_dir=workspace_dir,
        )
    except TypeError as exc:
        if "workspace_dir" not in str(exc):
            raise
        _rebuild_postprocessed_artifacts(
            results,
            payload=payload,
            report=report,
            params=params,
        )


def _stage_run_dir(job_id: str, *, workspace_dir: str | None = None) -> Path:
    root = workspace_paths(workspace_dir)["stage_runs"] if workspace_dir else STAGE_RUN_DIR
    out = root / str(job_id or "").strip()
    out.mkdir(parents=True, exist_ok=True)
    return out


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _write_stage_artifact(job_id: str, filename: str, payload: Dict[str, Any], *, workspace_dir: str | None = None) -> str:
    out = _stage_run_dir(job_id, workspace_dir=workspace_dir) / str(filename or "artifact.json").strip()
    job_record = _get_job_record(job_id, workspace_dir=workspace_dir)
    job_payload = job_record.get("payload") if isinstance(job_record, dict) and isinstance(job_record.get("payload"), dict) else {}
    request_signature = str(job_record.get("request_signature") or "").strip() if isinstance(job_record, dict) else ""
    safe_payload = _json_safe(payload)
    envelope = build_stage_artifact_envelope(
        filename=filename,
        job_id=job_id,
        payload=safe_payload,
        request_signature=request_signature or None,
        contract_stamp=resolve_contract_stamp(job_payload),
    )
    out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


def _result_digest(result: Dict[str, Any] | None) -> str:
    raw = json.dumps(_json_safe(result if isinstance(result, dict) else {}), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _variant_result_artifact_name(variant_id: int) -> str:
    return f"03_variant_result_v{max(1, int(variant_id or 1))}.json"


def _write_variant_result_artifact(
    job_id: str,
    *,
    variant_id: int,
    logic_template_id: str | None,
    result: Dict[str, Any],
    workspace_dir: str | None = None,
) -> str:
    payload = {
        "job_id": job_id,
        "variant_id": int(variant_id or 1),
        "logic_template_id": str(logic_template_id or "").strip() or None,
        "result_sha1": _result_digest(result),
        "result": result,
    }
    return _write_stage_artifact(
        job_id,
        _variant_result_artifact_name(int(variant_id or 1)),
        payload,
        workspace_dir=workspace_dir,
    )


def _load_resumable_variant_results(
    job_id: str,
    *,
    payload: Dict[str, Any] | None,
    variant_plan: List[Dict[str, Any]],
    request_signature: str | None = None,
    workspace_dir: str | None = None,
) -> Dict[int, Dict[str, Any]]:
    resumed: Dict[int, Dict[str, Any]] = {}
    expected_contract_fp = contract_fingerprint(resolve_contract_stamp(payload if isinstance(payload, dict) else {}))
    expected_signature = str(request_signature or "").strip()
    for pos, item in enumerate(variant_plan or []):
        try:
            variant_id = int(item.get("variant_id") or 0)
        except Exception:
            variant_id = 0
        if variant_id <= 0:
            continue
        path = _stage_run_dir(job_id, workspace_dir=workspace_dir) / _variant_result_artifact_name(variant_id)
        if not path.exists():
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        artifact_meta = raw.get("_artifact") if isinstance(raw.get("_artifact"), dict) else {}
        artifact_contract = artifact_meta.get("contract") if isinstance(artifact_meta.get("contract"), dict) else {}
        artifact_signature = str(artifact_meta.get("request_signature") or "").strip()
        if expected_signature and artifact_signature and artifact_signature != expected_signature:
            continue
        if artifact_contract and contract_fingerprint(artifact_contract) != expected_contract_fp:
            continue
        result = raw.get("result") if isinstance(raw.get("result"), dict) else None
        if not isinstance(result, dict):
            continue
        stored_digest = str(raw.get("result_sha1") or "").strip()
        if stored_digest and stored_digest != _result_digest(result):
            continue
        sections = result.get("sections") if isinstance(result.get("sections"), list) else []
        if not sections:
            continue
        stored_variant_id = int(result.get("variant_id") or raw.get("variant_id") or variant_id)
        if stored_variant_id != variant_id:
            continue
        expected_template = normalize_logic_template_id(item.get("logic_template_id"))
        actual_template = normalize_logic_template_id(result.get("logic_template_id") or raw.get("logic_template_id"))
        if expected_template and actual_template and expected_template != actual_template:
            continue
        resumed[pos] = result
    return resumed


def _provider_chain_summary(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    chain = payload.get("provider_chain") if isinstance(payload.get("provider_chain"), list) else []
    for item in chain:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "slot": str(item.get("slot") or "").strip(),
                "provider": str(item.get("provider") or "").strip(),
                "model": str(item.get("model") or "").strip(),
                "key_alias": str(item.get("key_alias") or "").strip(),
            }
        )
    return rows


def _payload_stage_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    front_matter = payload.get("front_matter_outline") if isinstance(payload.get("front_matter_outline"), dict) else {}
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    deterministic_logic_template_id = str(mode_policy.get("deterministic_logic_template_id") or "").strip() or None
    return {
        "project_id": str(payload.get("project_id") or "").strip(),
        "topic": str(payload.get("topic") or "").strip(),
        "generation_mode": str(mode_policy.get("profile") or payload.get("generation_mode") or "").strip(),
        "mode_effective": str(mode_policy.get("mode_effective") or payload.get("generation_mode") or "").strip(),
        "stable_output": bool(mode_policy.get("stable_output", False)),
        "deterministic_variant_forced": bool(mode_policy.get("deterministic_variant_forced", False)),
        "deterministic_logic_template_id": deterministic_logic_template_id,
        "strict_tender_outline": bool(payload.get("strict_tender_outline", False)),
        "version_modes": [str(x).strip() for x in (payload.get("version_modes") or []) if str(x).strip()],
        "variant_parallelism": payload.get("variant_parallelism"),
        "agent_parallelism": payload.get("agent_parallelism"),
        "requested_agent_parallelism": payload.get("_requested_agent_parallelism"),
        "runtime_agent_parallelism": payload.get("_runtime_agent_parallelism"),
        "runtime_agent_parallelism_reason": str(payload.get("_runtime_agent_parallelism_reason") or "").strip(),
        "runtime_agent_parallelism_learning_applied": bool(payload.get("_runtime_agent_parallelism_learning_applied", False)),
        "runtime_agent_parallelism_learning_reason": str(payload.get("_runtime_agent_parallelism_learning_reason") or "").strip(),
        "runtime_agent_parallelism_learning_source_runs": int(payload.get("_runtime_agent_parallelism_learning_source_runs") or 0),
        "provider_chain": _provider_chain_summary(payload if isinstance(payload, dict) else {}),
        "front_matter_sequence": [str(x).strip() for x in (front_matter.get("sequence") or []) if str(x).strip()],
        "front_matter_pages": {
            "cover_pages": int(front_matter.get("cover_pages") or 0),
            "full_index_pages": int(front_matter.get("full_index_pages") or 0),
            "toc_pages": int(front_matter.get("toc_pages") or 0),
        },
        "request_id": str(payload.get("request_id") or "").strip(),
        "trace_id": str(payload.get("trace_id") or "").strip(),
    }


def _variant_result_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for idx, item in enumerate(results or [], start=1):
        if not isinstance(item, dict):
            continue
        sections = item.get("sections") if isinstance(item.get("sections"), list) else []
        quality = item.get("quality_checks") if isinstance(item.get("quality_checks"), dict) else {}
        quality_gate = item.get("quality_gate") if isinstance(item.get("quality_gate"), dict) else {}
        generation_trace = item.get("generation_trace") if isinstance(item.get("generation_trace"), dict) else {}
        logic_template = item.get("logic_template") if isinstance(item.get("logic_template"), dict) else {}
        logic_template_id = normalize_logic_template_id(item.get("logic_template_id") or logic_template.get("id"))
        logic_template_name = str(item.get("logic_template_name") or logic_template.get("name") or "").strip() or None
        remediation_strategy_audit = quality.get("remediation_strategy_audit") if isinstance(quality.get("remediation_strategy_audit"), dict) else {}
        remediation_execution_audit = quality.get("remediation_execution_audit") if isinstance(quality.get("remediation_execution_audit"), dict) else {}
        section_runtime_budget_preview = []
        for sec in sections[:8]:
            if not isinstance(sec, dict):
                continue
            section_runtime_budget_preview.append(
                {
                    "title": str(sec.get("title") or "").strip(),
                    "requested_timeout_sec": sec.get("requested_timeout_sec"),
                    "requested_max_output_tokens": sec.get("requested_max_output_tokens"),
                    "requested_section_retry_limit": sec.get("requested_section_retry_limit"),
                    "runtime_budget_reason": str(sec.get("runtime_budget_reason") or "").strip(),
                    "evolution_applied": bool(sec.get("evolution_applied", False)),
                    "evolution_reason": str(sec.get("evolution_reason") or "").strip(),
                    "evolution_source_runs": int(sec.get("evolution_source_runs") or 0),
                    "used_key_alias": str(sec.get("used_key_alias") or "").strip(),
                }
            )
        rows.append(
            summary_core.build_variant_summary_row(
                item=item,
                variant_index=idx,
                logic_template_id=logic_template_id,
                logic_template_name=logic_template_name,
                section_count=len(sections),
                section_runtime_budget_preview=section_runtime_budget_preview,
                remediation_strategy_audit=remediation_strategy_audit,
                remediation_execution_audit=remediation_execution_audit,
                extra_fields={
                    "section_titles": [str(sec.get("title") or "").strip() for sec in sections if isinstance(sec, dict)],
                    "case_library_summary": summarize_case_reference_pack(item.get("case_reference_pack")),
                    "image_library_summary": summarize_image_selection_pack(item.get("image_selection_pack")),
                },
            )
        )
    return {"variant_count": len(rows), "variants": rows}


def _variant_result_key(row: Dict[str, Any]) -> str:
    return metadata_core.variant_result_key(row)


def _build_blocking_issue_summary(
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


def _build_variant_resume_index(
    variant_plan: List[Dict[str, Any]],
    *,
    resumed_positions: set[int] | None = None,
    generated_positions: set[int] | None = None,
) -> Dict[str, Any]:
    resumed_pos = resumed_positions if isinstance(resumed_positions, set) else set()
    generated_pos = generated_positions if isinstance(generated_positions, set) else set()
    resumed_variant_ids: List[int] = []
    generated_variant_ids: List[int] = []
    for pos, item in enumerate(variant_plan or []):
        try:
            variant_id = int(item.get("variant_id") or 0)
        except Exception:
            variant_id = 0
        if variant_id <= 0:
            continue
        if pos in resumed_pos:
            resumed_variant_ids.append(variant_id)
        elif pos in generated_pos:
            generated_variant_ids.append(variant_id)
    return {
        "resume_applied": bool(resumed_variant_ids),
        "variants_total": len([it for it in (variant_plan or []) if isinstance(it, dict)]),
        "resumed_count": len(resumed_variant_ids),
        "generated_count": len(generated_variant_ids),
        "resumed_variant_ids": resumed_variant_ids,
        "generated_variant_ids": generated_variant_ids,
    }


def _persisted_job_result_metadata(results: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = _variant_result_summary(results)
    rows = summary.get("variants") if isinstance(summary.get("variants"), list) else []
    return metadata_core.build_result_metadata_from_rows(
        results=results,
        payload=payload,
        rows=rows,
        blocking_summary_builder=_build_blocking_issue_summary,
    )


def _write_result_bundle(
    job_id: str,
    *,
    payload: Dict[str, Any],
    outputs: Dict[str, Any],
    result_metadata: Dict[str, Any],
    resource_usage_summary: Dict[str, Any],
    variant_summary: Dict[str, Any],
    workspace_dir: str | None = None,
) -> str:
    build_dir = workspace_paths(workspace_dir)["build"] if workspace_dir else Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    return result_persistence.write_result_bundle_file(
        job_id=job_id,
        payload=payload,
        outputs=outputs,
        result_metadata=result_metadata,
        resource_usage_summary=resource_usage_summary,
        variant_summary=variant_summary,
        fallback_build_dir=build_dir,
        normalizer=_json_safe,
    )


def _default_result_bundle_path(job_id: str, *, workspace_dir: str | None = None) -> Path:
    build_dir = workspace_paths(workspace_dir)["build"] if workspace_dir else Path("build")
    build_dir.mkdir(parents=True, exist_ok=True)
    return build_dir / f"actions_{str(job_id or '').strip() or 'unknown'}_result_bundle.json"


def _load_reusable_result_bundle(
    job_id: str,
    *,
    job_result: Dict[str, Any] | None,
    workspace_dir: str | None = None,
) -> Dict[str, Any] | None:
    result = job_result if isinstance(job_result, dict) else {}
    candidates: List[Path] = []
    explicit = str(result.get("result_bundle_json") or "").strip()
    if explicit:
        candidates.append(Path(explicit))
    legacy_json = str(result.get("json") or "").strip()
    if legacy_json:
        candidates.append(Path(legacy_json).with_name(f"{Path(legacy_json).stem}_result_bundle.json"))
    candidates.append(_default_result_bundle_path(job_id, workspace_dir=workspace_dir))
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        bundle = load_result_bundle(path)
        if not bundle or not result_bundle_artifacts_complete(bundle):
            continue
        outputs = extract_outputs_from_result_bundle(bundle)
        if not outputs:
            continue
        return {
            "bundle_path": str(path),
            "outputs": outputs,
            "result_metadata": bundle.get("result_metadata") if isinstance(bundle.get("result_metadata"), dict) else {},
            "resource_usage_summary": bundle.get("resource_usage_summary") if isinstance(bundle.get("resource_usage_summary"), dict) else {},
            "variant_summary": bundle.get("variant_summary") if isinstance(bundle.get("variant_summary"), dict) else {},
        }
    return None


def _clamp_int(v: Any, default: int, lo: int, hi: int) -> int:
    try:
        n = int(v)
    except Exception:
        n = int(default)
    return max(lo, min(hi, n))


def _outline_count(payload: Dict[str, Any]) -> int:
    outline = payload.get("outline")
    if isinstance(outline, list) and outline:
        count = 0
        for item in outline:
            if isinstance(item, str) and item.strip():
                count += 1
            elif isinstance(item, dict):
                title = str(item.get("title") or item.get("name") or "").strip()
                if title:
                    count += 1
        if count > 0:
            return count
    chapter_pages = payload.get("chapter_pages")
    if isinstance(chapter_pages, dict) and chapter_pages:
        return sum(1 for k in chapter_pages.keys() if str(k).strip())
    return 0


def _derive_runtime_agent_parallelism(
    payload: Dict[str, Any],
    requested: int,
    variants_total: int,
    *,
    params: Dict[str, Any] | None = None,
    task_profile: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    effective = max(1, int(requested or 1))
    reasons: List[str] = []
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    planned_pages = _clamp_int(
        mode_policy.get("planned_total_pages") or payload.get("total_pages_target") or 0,
        0,
        0,
        100000,
    )
    outline_count = _outline_count(payload)

    if variants_total >= 2 and effective > 4:
        effective = min(effective, 4)
        reasons.append("variants>=2_cap=4")

    if planned_pages > 0 and planned_pages <= 12:
        cap = 2 if outline_count <= 4 else 3
        if effective > cap:
            effective = cap
            reasons.append(f"small_job_cap={cap}")
    elif planned_pages > 0 and planned_pages <= 24:
        if effective > 3:
            effective = 3
            reasons.append("mid_small_cap=3")
    elif planned_pages > 0 and planned_pages <= 40:
        if effective > 4:
            effective = 4
            reasons.append("mid_job_cap=4")
    elif outline_count > 0 and outline_count <= 4 and effective > 2:
        effective = 2
        reasons.append("compact_outline_cap=2")
    elif outline_count > 0 and outline_count <= 8 and effective > 3:
        effective = 3
        reasons.append("outline_cap=3")

    learning_applied = False
    learning_reason = ""
    learning_source_runs = 0
    hints = build_task_parallelism_hint(
        params=params,
        payload=payload,
        requested=requested,
        effective=effective,
        variants_total=variants_total,
        profile=task_profile,
    )
    if isinstance(hints, dict):
        try:
            hinted_effective = max(1, int(hints.get("effective") or effective))
        except Exception:
            hinted_effective = effective
        learning_applied = bool(hints.get("applied", False)) and hinted_effective < effective
        learning_reason = str(hints.get("reason") or "").strip()
        try:
            learning_source_runs = int(hints.get("source_runs") or 0)
        except Exception:
            learning_source_runs = 0
        if learning_applied:
            effective = hinted_effective
            if learning_reason:
                reasons.append(learning_reason)

    return {
        "requested": int(requested or 1),
        "effective": max(1, int(effective)),
        "planned_pages": int(planned_pages),
        "outline_count": int(outline_count),
        "reason": ", ".join(reasons),
        "learning_applied": learning_applied,
        "learning_reason": learning_reason,
        "learning_source_runs": learning_source_runs,
    }


def _is_cancelled(job_id: str, *, workspace_dir: str | None = None) -> bool:
    j = _get_job_record(job_id, workspace_dir=workspace_dir) or {}
    return str(j.get("status") or "").strip().lower() == "cancelled"


def _collect_hard_variant_failures(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []
    for idx, result in enumerate(results, start=1):
        sections = result.get("sections") if isinstance(result, dict) else None
        if not isinstance(sections, list) or not sections:
            failures.append(
                {
                    "variant_index": idx,
                    "variant_id": result.get("variant_id") if isinstance(result, dict) else None,
                    "reason": "sections_missing",
                    "section_total": 0,
                    "error_count": 0,
                    "sample_errors": [],
                }
            )
            continue
        error_sections = []
        sample_errors: List[str] = []
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            content = str(sec.get("content") or "").strip()
            error_text = str(sec.get("error") or "").strip()
            failed = bool(error_text) or not content or content == "章节生成失败"
            if failed:
                error_sections.append(sec)
                if error_text and len(sample_errors) < 3:
                    sample_errors.append(error_text)
        if error_sections and len(error_sections) >= len(sections):
            failures.append(
                {
                    "variant_index": idx,
                    "variant_id": result.get("variant_id") if isinstance(result, dict) else None,
                    "reason": "all_sections_failed",
                    "section_total": len(sections),
                    "error_count": len(error_sections),
                    "sample_errors": sample_errors,
                }
            )
    return failures


def _build_sla_public(sla_state: Dict[str, Any], status: str = "running") -> Dict[str, Any]:
    out = {
        "status": status,
        "started_at": float(sla_state.get("started_at") or time.time()),
        "updated_at": float(sla_state.get("updated_at") or time.time()),
        "total_seconds": float(sla_state.get("elapsed_sec") or 0.0),
        "stages": [],
    }
    stages = sla_state.get("stages") if isinstance(sla_state.get("stages"), list) else []
    for st in stages:
        if not isinstance(st, dict):
            continue
        out["stages"].append(
            {
                "name": str(st.get("name") or ""),
                "started_at": st.get("started_at"),
                "ended_at": st.get("ended_at"),
                "duration_sec": st.get("duration_sec"),
                "percent": st.get("percent"),
                "detail": st.get("detail"),
            }
        )
    return out


def _record_sla_stage(sla_state: Dict[str, Any], stage: str, percent: int, detail: str) -> None:
    now = time.time()
    stages = sla_state.setdefault("stages", [])
    if stages and str(stages[-1].get("name") or "") == str(stage or ""):
        stages[-1]["percent"] = int(percent)
        stages[-1]["detail"] = str(detail or "")
    else:
        if stages and stages[-1].get("ended_at") is None:
            st = stages[-1]
            st["ended_at"] = now
            st["duration_sec"] = round(max(0.0, now - float(st.get("started_at") or now)), 3)
        stages.append(
            {
                "name": str(stage or ""),
                "started_at": now,
                "ended_at": None,
                "duration_sec": None,
                "percent": int(percent),
                "detail": str(detail or ""),
            }
        )
    sla_state["updated_at"] = now
    sla_state["elapsed_sec"] = round(max(0.0, now - float(sla_state.get("started_at") or now)), 3)


def _finalize_sla(sla_state: Dict[str, Any], status: str) -> Dict[str, Any]:
    now = time.time()
    stages = sla_state.get("stages") if isinstance(sla_state.get("stages"), list) else []
    if stages and stages[-1].get("ended_at") is None:
        stages[-1]["ended_at"] = now
        stages[-1]["duration_sec"] = round(max(0.0, now - float(stages[-1].get("started_at") or now)), 3)
    sla_state["updated_at"] = now
    sla_state["elapsed_sec"] = round(max(0.0, now - float(sla_state.get("started_at") or now)), 3)
    return _build_sla_public(sla_state, status=status)


def _update_progress(
    job_id: str,
    agent_runtime: Dict[str, Any],
    variants_total: int,
    percent: int,
    stage: str,
    detail: str = "",
    *,
    progress_state: Dict[str, Any] | None = None,
    sla_state: Dict[str, Any] | None = None,
    workspace_dir: str | None = None,
) -> None:
    p = max(0, min(100, int(percent)))
    ps = progress_state if isinstance(progress_state, dict) else {}
    ps["percent"] = p
    ps["stage"] = str(stage or "")
    ps["detail"] = str(detail or "")
    if isinstance(sla_state, dict):
        _record_sla_stage(sla_state, stage=str(stage or ""), percent=p, detail=str(detail or ""))
    now = time.time()
    kwargs: Dict[str, Any] = {
        "progress": {
            "percent": p,
            "stage": str(stage or ""),
            "detail": str(detail or ""),
            "variants_total": variants_total,
            "variants_done": int(agent_runtime.get("variants_done") or 0),
        },
        "agent_runtime": agent_runtime,
        "heartbeat_at": now,
    }
    if isinstance(sla_state, dict):
        kwargs["sla"] = _build_sla_public(sla_state, status="running")
    _update_job_record(
        job_id,
        workspace_dir=workspace_dir,
        **kwargs,
    )
    _worker_log(job_id, f"progress stage={str(stage or '').strip()} percent={p} detail={str(detail or '').strip()}", workspace_dir=workspace_dir)


def execute_job(job_id: str, workspace_dir: str | None = None) -> None:
    job = _get_job_record(job_id, workspace_dir=workspace_dir)
    if not job:
        return
    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    payload_session_id = str(payload.get("session_id") or "").strip() or None
    payload_workspace = workspace_dir or str(job.get("workspace_dir") or payload.get("workspace_dir") or "").strip() or None
    resolved_workspace = (
        str(
            resolve_workspace_dir(
                session_id=payload_session_id,
                workspace_dir=payload_workspace,
            )
        )
        if payload_workspace or payload_session_id
        else None
    )
    if resolved_workspace:
        payload["workspace_dir"] = resolved_workspace
    else:
        payload.pop("workspace_dir", None)
    stage_dir = _stage_run_dir(job_id, workspace_dir=resolved_workspace)
    try:
        _worker_log(job_id, "job_execute_started", workspace_dir=resolved_workspace)
        append_resource_event(
            "job_started",
            workspace_dir=resolved_workspace,
            session_id=payload_session_id,
            user_id=job.get("user_id"),
            job_id=job_id,
            request_signature=job.get("request_signature"),
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
            project_id=payload.get("project_id"),
            topic=payload.get("topic"),
        )
        local_payload = apply_generation_mode_policy(json.loads(json.dumps(payload)))
        local_payload["_job_id"] = job_id
        if resolved_workspace:
            local_payload["workspace_dir"] = resolved_workspace
        else:
            local_payload.pop("workspace_dir", None)
        params = load_params()
        task_parallelism_profile = load_task_parallelism_profile()

        variants_total = _clamp_int(local_payload.get("variants") or 1, 1, 1, 5)
        requested_agent_parallelism = _clamp_int(local_payload.get("agent_parallelism") or 4, 4, 1, 16)
        variant_parallelism = _clamp_int(local_payload.get("variant_parallelism") or 1, 1, 1, 5)
        runtime_parallelism = _derive_runtime_agent_parallelism(
            local_payload,
            requested_agent_parallelism,
            variants_total,
            params=params,
            task_profile=task_parallelism_profile,
        )
        agent_parallelism = int(runtime_parallelism.get("effective") or requested_agent_parallelism)
        local_payload["agent_parallelism"] = agent_parallelism
        local_payload["variant_parallelism"] = variant_parallelism
        local_payload["_requested_agent_parallelism"] = requested_agent_parallelism
        local_payload["_runtime_agent_parallelism"] = agent_parallelism
        local_payload["_runtime_agent_parallelism_reason"] = str(runtime_parallelism.get("reason") or "").strip()
        local_payload["_runtime_agent_parallelism_learning_applied"] = bool(runtime_parallelism.get("learning_applied", False))
        local_payload["_runtime_agent_parallelism_learning_reason"] = str(runtime_parallelism.get("learning_reason") or "").strip()
        local_payload["_runtime_agent_parallelism_learning_source_runs"] = int(runtime_parallelism.get("learning_source_runs") or 0)

        agent_runtime = {
            "mode": "parallel",
            "master_agent": "主控Agent",
            "compliance_agent": "合规Agent",
            "requested_agent_parallelism": requested_agent_parallelism,
            "agent_parallelism": agent_parallelism,
            "variant_parallelism": variant_parallelism,
            "variants_total": variants_total,
            "variants_done": 0,
            "worker_mode": "subprocess",
            "worker_pid": str(os.getpid()),
            "planned_total_pages": int(runtime_parallelism.get("planned_pages") or 0),
            "outline_count": int(runtime_parallelism.get("outline_count") or 0),
            "runtime_agent_parallelism_reason": str(runtime_parallelism.get("reason") or "").strip(),
            "runtime_agent_parallelism_learning_applied": bool(runtime_parallelism.get("learning_applied", False)),
            "runtime_agent_parallelism_learning_reason": str(runtime_parallelism.get("learning_reason") or "").strip(),
            "runtime_agent_parallelism_learning_source_runs": int(runtime_parallelism.get("learning_source_runs") or 0),
        }
        if agent_parallelism != requested_agent_parallelism:
            _worker_log(
                job_id,
                "runtime_agent_parallelism_adjusted "
                f"requested={requested_agent_parallelism} effective={agent_parallelism} "
                f"planned_pages={int(runtime_parallelism.get('planned_pages') or 0)} "
                f"outline_count={int(runtime_parallelism.get('outline_count') or 0)} "
                f"reason={str(runtime_parallelism.get('reason') or '').strip() or 'n/a'}",
                workspace_dir=resolved_workspace,
            )
        if bool(runtime_parallelism.get("learning_applied", False)):
            _worker_log(
                job_id,
                "runtime_agent_parallelism_learning_applied "
                f"requested={requested_agent_parallelism} "
                f"effective={agent_parallelism} source_runs={int(runtime_parallelism.get('learning_source_runs') or 0)} "
                f"reason={str(runtime_parallelism.get('learning_reason') or '').strip() or 'n/a'}",
                workspace_dir=resolved_workspace,
            )
        progress_state: Dict[str, Any] = {"percent": 0, "stage": "queued", "detail": "任务排队中"}
        sla_state: Dict[str, Any] = {
            "started_at": time.time(),
            "updated_at": time.time(),
            "elapsed_sec": 0.0,
            "stages": [],
        }
        shared_retrieval_cache: Dict[str, Any] = {
            "items": {},
            "stats": {"hits": 0, "misses": 0, "stores": 0},
        }

        if _is_cancelled(job_id, workspace_dir=resolved_workspace):
            append_resource_event(
                "job_cancelled",
                workspace_dir=resolved_workspace,
                session_id=payload_session_id,
                user_id=job.get("user_id"),
                job_id=job_id,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
                project_id=payload.get("project_id"),
                topic=payload.get("topic"),
                reason="cancelled_by_user",
            )
            _update_job_record(
                job_id,
                workspace_dir=resolved_workspace,
                status="cancelled",
                error="cancelled_by_user",
                heartbeat_at=time.time(),
                sla=_finalize_sla(sla_state, status="cancelled"),
            )
            return
        _update_job_record(
            job_id,
            workspace_dir=resolved_workspace,
            status="running",
            agent_runtime=agent_runtime,
            stage_artifacts_dir=str(stage_dir),
            heartbeat_at=time.time(),
            sla=_build_sla_public(sla_state, status="running"),
        )
        _write_stage_artifact(
            job_id,
            "01_job_started.json",
            {
                "job_id": job_id,
                "status": "running",
                "payload_summary": _payload_stage_summary(local_payload),
                "agent_runtime": agent_runtime,
            },
            workspace_dir=resolved_workspace,
        )
        _update_progress(
            job_id,
            agent_runtime,
            variants_total,
            5,
            "job_started",
            "任务已启动，正在分配多Agent",
            progress_state=progress_state,
            sla_state=sla_state,
            workspace_dir=resolved_workspace,
        )
        mode_policy = local_payload.get("_mode_policy") if isinstance(local_payload.get("_mode_policy"), dict) else {}
        mode_name = str(mode_policy.get("mode_effective") or local_payload.get("generation_mode") or "quality_200")
        pages_planned = int(mode_policy.get("planned_total_pages") or 0)
        if bool(mode_policy.get("auto_switched")):
            _update_progress(
                job_id,
                agent_runtime,
                variants_total,
                8,
                "mode_switch",
                f"页数规划={pages_planned}，已自动切换到高质量加速模式（{mode_name})",
                progress_state=progress_state,
                sla_state=sla_state,
                workspace_dir=resolved_workspace,
            )
        else:
            _update_progress(
                job_id,
                agent_runtime,
                variants_total,
                8,
                "mode_ready",
                f"生成模式={mode_name}，页数规划={pages_planned}",
                progress_state=progress_state,
                sla_state=sla_state,
                workspace_dir=resolved_workspace,
            )
        variant_plan = local_payload.get("_variant_plan")
        normalized_plan: List[Dict[str, Any]] = []
        if isinstance(variant_plan, list) and variant_plan:
            for it in variant_plan:
                if not isinstance(it, dict):
                    continue
                try:
                    vid = int(it.get("variant_id") or 0)
                except Exception:
                    vid = 0
                if vid <= 0:
                    continue
                rec: Dict[str, Any] = {"variant_id": vid}
                tid = normalize_logic_template_id(it.get("logic_template_id"))
                if tid:
                    rec["logic_template_id"] = tid
                normalized_plan.append(rec)
        if not normalized_plan:
            variants = variants_total
            variant_ids = local_payload.get("_variant_ids")
            if not isinstance(variant_ids, list) or not variant_ids:
                variant_ids = reserve_variant_ids(
                    project_id=str(local_payload.get("project_id") or "").strip() or None,
                    count=max(1, variants),
                    explicit_variant_id=local_payload.get("variant_id"),
                    explicit_template_id=local_payload.get("logic_template_id") or local_payload.get("logic_template"),
                )
            for vid in variant_ids:
                try:
                    normalized_plan.append({"variant_id": int(vid)})
                except Exception:
                    continue
        if not normalized_plan:
            normalized_plan = [{"variant_id": 1}]
        variant_plan = normalized_plan
        variants_total = max(1, len(variant_plan))
        agent_runtime["variants_total"] = variants_total
        if variant_parallelism > variants_total:
            variant_parallelism = variants_total
            local_payload["variant_parallelism"] = variant_parallelism
            agent_runtime["variant_parallelism"] = variant_parallelism
        _write_stage_artifact(
            job_id,
            "02_variant_plan.json",
            {
                "job_id": job_id,
                "variants_total": variants_total,
                "variant_parallelism": variant_parallelism,
                "agent_parallelism": agent_parallelism,
                "variant_plan": variant_plan,
                "mode_policy": local_payload.get("_mode_policy") if isinstance(local_payload.get("_mode_policy"), dict) else {},
            },
            workspace_dir=resolved_workspace,
        )
        _update_progress(
            job_id,
            agent_runtime,
            variants_total,
            10,
            "agent_ready",
            (
                f"多Agent协作已启用：章节并行={agent_parallelism}"
                + (f"（请求={requested_agent_parallelism}，已按任务规模收敛）" if agent_parallelism != requested_agent_parallelism else "")
                + f"，方案并行={variant_parallelism}"
            ),
            progress_state=progress_state,
            sla_state=sla_state,
            workspace_dir=resolved_workspace,
        )

        async def _run_variants_parallel() -> list[dict]:
            sem = asyncio.Semaphore(max(1, int(variant_parallelism)))
            lock = asyncio.Lock()
            ordered: list[dict | None] = [None for _ in range(len(variant_plan))]
            resumed = _load_resumable_variant_results(
                job_id,
                payload=local_payload,
                variant_plan=variant_plan,
                request_signature=str(job.get("request_signature") or "").strip() or None,
                workspace_dir=resolved_workspace,
            )
            resumed_positions = set(resumed.keys())
            generated_positions: set[int] = set()
            for pos, result in resumed.items():
                ordered[pos] = result
            done_count = len(resumed)
            if done_count > 0:
                agent_runtime["variants_done"] = int(done_count)
                agent_runtime["resumed_variant_count"] = int(done_count)
                _update_progress(
                    job_id,
                    agent_runtime,
                    variants_total,
                    15 + int((done_count / max(1, variants_total)) * 65),
                    "variant_resume",
                    f"已恢复方案进度：{done_count}/{variants_total}",
                    progress_state=progress_state,
                    sla_state=sla_state,
                    workspace_dir=resolved_workspace,
                )
            heartbeat_interval = max(10, int(local_payload.get("heartbeat_interval") or os.getenv("ZF_JOB_HEARTBEAT_SECONDS") or 20))
            stop_hb = asyncio.Event()

            async def _heartbeat_loop() -> None:
                while not stop_hb.is_set():
                    try:
                        await asyncio.wait_for(stop_hb.wait(), timeout=float(heartbeat_interval))
                        break
                    except asyncio.TimeoutError:
                        pass
                    if _is_cancelled(job_id, workspace_dir=resolved_workspace):
                        break
                    _update_job_record(
                        job_id,
                        workspace_dir=resolved_workspace,
                        heartbeat_at=time.time(),
                        progress={
                            "percent": int(progress_state.get("percent") or 0),
                            "stage": str(progress_state.get("stage") or "running"),
                            "detail": str(progress_state.get("detail") or ""),
                            "variants_total": variants_total,
                            "variants_done": int(agent_runtime.get("variants_done") or 0),
                        },
                        agent_runtime=agent_runtime,
                        sla=_build_sla_public(sla_state, status="running"),
                    )

            async def _run_one(pos: int, item: Dict[str, Any]):
                nonlocal done_count
                if _is_cancelled(job_id, workspace_dir=resolved_workspace):
                    return
                vid = int(item.get("variant_id") or 1)
                tid = normalize_logic_template_id(item.get("logic_template_id"))
                lp = json.loads(json.dumps(local_payload))
                lp["variant_id"] = int(vid)
                if tid:
                    lp["logic_template_id"] = tid
                lp["agent_parallelism"] = agent_parallelism
                lp["workspace_dir"] = resolved_workspace
                lp["_shared_retrieval_cache_obj"] = shared_retrieval_cache
                async with sem:
                    if _is_cancelled(job_id, workspace_dir=resolved_workspace):
                        return
                    detail = f"正在并行编制方案 v{int(vid)}"
                    if tid:
                        detail += f"（模板{tid}）"
                    _worker_log(job_id, f"variant_started variant=v{int(vid)} template={tid or 'default'}", workspace_dir=resolved_workspace)
                    _update_progress(
                        job_id,
                        agent_runtime,
                        variants_total,
                        15 + int((done_count / max(1, variants_total)) * 65),
                        "variant_running",
                        detail,
                        progress_state=progress_state,
                        sla_state=sla_state,
                        workspace_dir=resolved_workspace,
                    )
                    res = await run_autoplan(lp)
                    ordered[pos] = res
                    generated_positions.add(pos)
                    _write_variant_result_artifact(
                        job_id,
                        variant_id=vid,
                        logic_template_id=tid,
                        result=res,
                        workspace_dir=resolved_workspace,
                    )
                    case_reference_pack = res.get("case_reference_pack") if isinstance(res.get("case_reference_pack"), dict) else {}
                    if case_reference_pack:
                        _write_stage_artifact(
                            job_id,
                            f"03_case_reference_pack_v{int(vid)}.json",
                            {
                                "job_id": job_id,
                                "variant_id": int(vid),
                                "logic_template_id": tid,
                                "case_reference_pack": case_reference_pack,
                            },
                            workspace_dir=resolved_workspace,
                        )
                    image_selection_pack = res.get("image_selection_pack") if isinstance(res.get("image_selection_pack"), dict) else {}
                    if image_selection_pack:
                        _write_stage_artifact(
                            job_id,
                            f"03_image_selection_pack_v{int(vid)}.json",
                            {
                                "job_id": job_id,
                                "variant_id": int(vid),
                                "logic_template_id": tid,
                                "image_selection_pack": image_selection_pack,
                            },
                            workspace_dir=resolved_workspace,
                        )
                    _worker_log(job_id, f"variant_finished variant=v{int(vid)} template={tid or 'default'}", workspace_dir=resolved_workspace)
                async with lock:
                    done_count += 1
                    agent_runtime["variants_done"] = int(done_count)
                    _update_progress(
                        job_id,
                        agent_runtime,
                        variants_total,
                        15 + int((done_count / max(1, variants_total)) * 65),
                        "variant_running",
                        f"方案完成进度：{done_count}/{variants_total}",
                        progress_state=progress_state,
                        sla_state=sla_state,
                        workspace_dir=resolved_workspace,
                    )

            hb_task = asyncio.create_task(_heartbeat_loop())
            try:
                pending_tasks = [_run_one(i, item) for i, item in enumerate(variant_plan) if not isinstance(ordered[i], dict)]
                if pending_tasks:
                    await asyncio.gather(*pending_tasks)
            finally:
                stop_hb.set()
                try:
                    await hb_task
                except Exception:
                    pass
            agent_runtime["generated_variant_count"] = int(len(generated_positions))
            agent_runtime["resumed_variant_count"] = int(len(resumed_positions))
            agent_runtime["variant_resume_index"] = _build_variant_resume_index(
                variant_plan,
                resumed_positions=resumed_positions,
                generated_positions=generated_positions,
            )
            return [x for x in ordered if isinstance(x, dict)]

        results = asyncio.run(_run_variants_parallel())
        _write_stage_artifact(
            job_id,
            "03_variant_results_summary.json",
            {
                "job_id": job_id,
                "result_summary": _variant_result_summary(results),
                "resume_index": dict(agent_runtime.get("variant_resume_index") or {}),
            },
            workspace_dir=resolved_workspace,
        )
        learning_summary: Dict[str, Any] = {}
        try:
            learning_summary = record_runtime_learning(local_payload, results, params=params)
        except Exception as exc:
            learning_summary = {
                "enabled": True,
                "error": str(exc),
                "updated_entries": 0,
            }
        task_parallelism_learning_summary: Dict[str, Any] = {}
        hard_failures = _collect_hard_variant_failures(results)
        try:
            task_parallelism_learning_summary = record_task_parallelism_learning(
                local_payload,
                agent_runtime=agent_runtime,
                results=results,
                hard_failures=hard_failures,
                params=params,
            )
        except Exception as exc:
            task_parallelism_learning_summary = {
                "enabled": True,
                "error": str(exc),
                "updated_entries": 0,
            }
        _write_stage_artifact(
            job_id,
            "03_self_evolution_learning.json",
            {
                "job_id": job_id,
                "runtime_budget_learning_summary": learning_summary,
                "task_parallelism_learning_summary": task_parallelism_learning_summary,
            },
            workspace_dir=resolved_workspace,
        )
        if _is_cancelled(job_id, workspace_dir=resolved_workspace):
            _update_job_record(
                job_id,
                workspace_dir=resolved_workspace,
                status="cancelled",
                error="cancelled_by_user",
                stage_artifacts_dir=str(stage_dir),
                heartbeat_at=time.time(),
                sla=_finalize_sla(sla_state, status="cancelled"),
            )
            return
        if results and hard_failures and len(hard_failures) >= len(results):
            resource_usage_summary = summarize_variants(results)
            summary = []
            for item in hard_failures:
                label = f"v{int(item.get('variant_id') or item.get('variant_index') or 0)}"
                summary.append(
                    f"{label}:{item.get('reason')}({int(item.get('error_count') or 0)}/{int(item.get('section_total') or 0)})"
                )
            error_text = "all_variants_failed_hard_gate: " + "; ".join(summary)
            _worker_log(job_id, error_text, workspace_dir=resolved_workspace)
            _write_stage_artifact(
                job_id,
                "04_hard_failures.json",
                {
                    "job_id": job_id,
                    "error": error_text,
                    "hard_failures": hard_failures,
                    "result_summary": _variant_result_summary(results),
                },
                workspace_dir=resolved_workspace,
            )
            _update_job_record(
                job_id,
                workspace_dir=resolved_workspace,
                status="failed",
                error=error_text,
                progress={"percent": 100, "stage": "failed", "detail": "所有章节生成失败，已终止导出"},
                result={
                    "hard_failures": hard_failures,
                    "resource_usage_summary": resource_usage_summary,
                },
                agent_runtime=agent_runtime,
                stage_artifacts_dir=str(stage_dir),
                heartbeat_at=time.time(),
                sla=_finalize_sla(sla_state, status="failed"),
            )
            append_resource_event(
                "job_failed",
                workspace_dir=resolved_workspace,
                session_id=payload_session_id,
                user_id=job.get("user_id"),
                job_id=job_id,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
                project_id=payload.get("project_id"),
                topic=payload.get("topic"),
                error=error_text,
                resource_usage_summary=resource_usage_summary,
            )
            return
        agent_runtime["retrieval_cache"] = dict((shared_retrieval_cache.get("stats") or {}))
        if len(results) >= 2:
            try:
                from backend.zhifei_autoplan.variant_similarity import compute_variant_similarity
                from backend.zhifei_autoplan.diversity_autofix import apply_diversity_autofix

                params = load_params()
                overrides = local_payload.get("params_override")
                if isinstance(overrides, dict) and overrides:
                    for k, v in overrides.items():
                        if isinstance(v, dict) and isinstance(params.get(k), dict):
                            merged = dict(params.get(k) or {})
                            merged.update(v)
                            params[k] = merged
                        else:
                            params[k] = v
                div_cfg = params.get("variant_diversity") if isinstance(params.get("variant_diversity"), dict) else {}

                def _run_report():
                    return compute_variant_similarity(
                        results,
                        chapter_threshold=float(div_cfg.get("chapter_threshold") or 0.90),
                        overall_threshold=float(div_cfg.get("overall_threshold") or 0.85),
                        min_chars=int(div_cfg.get("min_chars") or 800),
                        ignore_title_keywords=(div_cfg.get("ignore_title_keywords") if isinstance(div_cfg.get("ignore_title_keywords"), list) else None),
                        relaxed_title_keywords=(div_cfg.get("relaxed_title_keywords") if isinstance(div_cfg.get("relaxed_title_keywords"), list) else None),
                        relaxed_chapter_threshold=(float(div_cfg.get("relaxed_chapter_threshold")) if div_cfg.get("relaxed_chapter_threshold") is not None else None),
                    )

                report = _run_report()
                max_rounds = int(div_cfg.get("auto_fix_rounds") or 1)
                if max_rounds < 0:
                    max_rounds = 0
                rounds = 0
                while rounds < max_rounds and report.get("ok") is False and report.get("flagged"):
                    changed_any = False
                    for f in (report.get("flagged") or [])[:24]:
                        title = str(f.get("title") or "").strip()
                        pair = str(f.get("pair") or "").strip()
                        m = re.match(r"^v(\\d+)_v(\\d+)$", pair)
                        if not m or not title:
                            continue
                        a = int(m.group(1))
                        b = int(m.group(2))
                        target_idx = max(a, b)
                        if target_idx <= 1 or target_idx > len(results):
                            continue
                        target = results[target_idx - 1]
                        secs = target.get("sections") if isinstance(target, dict) else None
                        if not isinstance(secs, list):
                            continue
                        for sec in secs:
                            if not isinstance(sec, dict):
                                continue
                            if str(sec.get("title") or "").strip() != title:
                                continue
                            if apply_diversity_autofix(sec, params=params, evidence_hint=str(pair)):
                                changed_any = True
                            break
                    if not changed_any:
                        break
                    report = _run_report()
                    rounds += 1
                _update_progress(
                    job_id,
                    agent_runtime,
                    variants_total,
                    86,
                    "cross_variant_check",
                    "正在执行跨方案一致性与差异性审计",
                    progress_state=progress_state,
                    sla_state=sla_state,
                    workspace_dir=resolved_workspace,
                )
                _rebuild_postprocessed_artifacts_compat(
                    results,
                    payload=local_payload,
                    report=report,
                    params=params,
                    workspace_dir=resolved_workspace,
                )
            except Exception:
                pass
        if _is_cancelled(job_id, workspace_dir=resolved_workspace):
            _update_job_record(
                job_id,
                workspace_dir=resolved_workspace,
                status="cancelled",
                error="cancelled_by_user",
                heartbeat_at=time.time(),
                sla=_finalize_sla(sla_state, status="cancelled"),
            )
            return
        _update_progress(
            job_id,
            agent_runtime,
            variants_total,
            92,
            "exporting",
            "正在导出 DOCX / 对照稿 / 问题清单",
            progress_state=progress_state,
            sla_state=sla_state,
            workspace_dir=resolved_workspace,
        )
        reusable_bundle = _load_reusable_result_bundle(
            job_id,
            job_result=job.get("result") if isinstance(job.get("result"), dict) else {},
            workspace_dir=resolved_workspace,
        )
        if reusable_bundle:
            outputs = reusable_bundle.get("outputs") if isinstance(reusable_bundle.get("outputs"), dict) else {}
            resource_usage_summary = reusable_bundle.get("resource_usage_summary") if isinstance(reusable_bundle.get("resource_usage_summary"), dict) else {}
            result_metadata = reusable_bundle.get("result_metadata") if isinstance(reusable_bundle.get("result_metadata"), dict) else {}
            variant_summary = reusable_bundle.get("variant_summary") if isinstance(reusable_bundle.get("variant_summary"), dict) else {}
            result_bundle_json = str(reusable_bundle.get("bundle_path") or "").strip()
            if not resource_usage_summary:
                resource_usage_summary = summarize_variants(results)
            if not result_metadata:
                result_metadata = _persisted_job_result_metadata(results, local_payload)
            if not variant_summary:
                variant_summary = _variant_result_summary(results)
            _update_progress(
                job_id,
                agent_runtime,
                variants_total,
                96,
                "export_reused",
                "检测到已完成导出结果，复用现有产物",
                progress_state=progress_state,
                sla_state=sla_state,
                workspace_dir=resolved_workspace,
            )
        else:
            outputs = _save_outputs_compat(f"actions_{job_id}", results, workspace_dir=resolved_workspace)
            resource_usage_summary = summarize_variants(results)
            result_metadata = _persisted_job_result_metadata(results, local_payload)
            variant_summary = _variant_result_summary(results)
            result_bundle_json = _write_result_bundle(
                job_id,
                payload=local_payload,
                outputs=outputs,
                result_metadata=result_metadata,
                resource_usage_summary=resource_usage_summary,
                variant_summary=variant_summary,
                workspace_dir=resolved_workspace,
            )
        job_result = result_persistence.build_job_result_payload(
            outputs=outputs,
            resource_usage_summary=resource_usage_summary,
            result_bundle_json=result_bundle_json,
            result_metadata=result_metadata,
        )
        _write_stage_artifact(
            job_id,
            "04_outputs.json",
            {
                "job_id": job_id,
                "outputs": job_result,
                "result_summary": variant_summary,
            },
            workspace_dir=resolved_workspace,
        )
        if _is_cancelled(job_id, workspace_dir=resolved_workspace):
            append_resource_event(
                "job_cancelled",
                workspace_dir=resolved_workspace,
                session_id=payload_session_id,
                user_id=job.get("user_id"),
                job_id=job_id,
                request_id=payload.get("request_id"),
                trace_id=payload.get("trace_id"),
                project_id=payload.get("project_id"),
                topic=payload.get("topic"),
                reason="cancelled_by_user",
                resource_usage_summary=resource_usage_summary,
            )
            _update_job_record(
                job_id,
                workspace_dir=resolved_workspace,
                status="cancelled",
                error="cancelled_by_user",
                result=job_result,
                stage_artifacts_dir=str(stage_dir),
                heartbeat_at=time.time(),
                sla=_finalize_sla(sla_state, status="cancelled"),
            )
            return
        _update_progress(
            job_id,
            agent_runtime,
            variants_total,
            100,
            "done",
            "任务完成",
            progress_state=progress_state,
            sla_state=sla_state,
            workspace_dir=resolved_workspace,
        )
        done_sla = _finalize_sla(sla_state, status="done")
        _update_job_record(
            job_id,
            workspace_dir=resolved_workspace,
            status="done",
            result=job_result,
            agent_runtime=agent_runtime,
            stage_artifacts_dir=str(stage_dir),
            heartbeat_at=time.time(),
            sla=done_sla,
        )
        append_resource_event(
            "job_completed",
            workspace_dir=resolved_workspace,
            session_id=payload_session_id,
            user_id=job.get("user_id"),
            job_id=job_id,
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
            project_id=payload.get("project_id"),
            topic=payload.get("topic"),
            file_count=sum(
                len(value) if isinstance(value, list) else int(bool(value))
                for value in outputs.values()
            ),
            duration_ms=int(float(done_sla.get("total_seconds") or 0.0) * 1000),
            resource_usage_summary=resource_usage_summary,
        )
        _worker_log(job_id, f"job_execute_done outputs={json.dumps(outputs, ensure_ascii=False)}", workspace_dir=resolved_workspace)
    except Exception as e:
        _worker_log(job_id, f"job_execute_failed error={repr(e)}", workspace_dir=resolved_workspace if 'resolved_workspace' in locals() else workspace_dir)
        try:
            _write_stage_artifact(
                job_id,
                "99_failure.json",
                {
                    "job_id": job_id,
                    "error": repr(e),
                    "payload_summary": _payload_stage_summary(payload if isinstance(payload, dict) else {}),
                },
                workspace_dir=resolved_workspace if 'resolved_workspace' in locals() else workspace_dir,
            )
        except Exception:
            pass
        _update_job_record(
            job_id,
            workspace_dir=resolved_workspace if 'resolved_workspace' in locals() else workspace_dir,
            status="failed",
            error=repr(e),
            progress={"percent": 100, "stage": "failed", "detail": repr(e)},
            stage_artifacts_dir=str(stage_dir),
            heartbeat_at=time.time(),
            sla=_finalize_sla(sla_state if "sla_state" in locals() else {"started_at": time.time(), "stages": []}, status="failed"),
        )
        append_resource_event(
            "job_failed",
            workspace_dir=resolved_workspace if 'resolved_workspace' in locals() else workspace_dir,
            session_id=payload_session_id if 'payload_session_id' in locals() else None,
            user_id=(job or {}).get("user_id") if isinstance(job, dict) else None,
            job_id=job_id,
            request_id=(payload or {}).get("request_id") if isinstance(payload, dict) else None,
            trace_id=(payload or {}).get("trace_id") if isinstance(payload, dict) else None,
            project_id=(payload or {}).get("project_id") if isinstance(payload, dict) else None,
            topic=(payload or {}).get("topic") if isinstance(payload, dict) else None,
            error=repr(e),
        )


def main() -> int:
    job_id = str(sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not job_id:
        return 2
    workspace_dir = str(sys.argv[2] if len(sys.argv) > 2 else "").strip() or None
    execute_job(job_id, workspace_dir=workspace_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
