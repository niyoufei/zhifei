from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from backend.zhifei_autoplan import review_result_rebuild as review_rebuild_core
from backend.zhifei_autoplan.job_store import update_job
from backend.zhifei_autoplan.params_runtime import load_params
from backend.zhifei_autoplan.quality_check import apply_remediation, strip_nonconcrete_language
from backend.zhifei_autoplan.resource_audit import summarize_variants
from backend.zhifei_autoplan.run_contract import attach_contract_stamp

REVIEW_APPLY_HISTORY_LIMIT = 5


def _decision_field(item: Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _applied_item_summary_rows(selected: list[dict]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in selected or []:
        if not isinstance(item, dict):
            continue
        reference_case_id = str(item.get("reference_case_id") or "").strip() or None
        reference_context = item.get("reference_context") if isinstance(item.get("reference_context"), dict) else {}
        replacement = str(item.get("replacement") or "").strip()
        rows.append(
            {
                "issue_id": str(item.get("issue_id") or "").strip() or None,
                "source": str(item.get("source") or "").strip() or None,
                "title": str(item.get("title") or "").strip() or None,
                "type": str(item.get("type") or "").strip() or None,
                "apply_mode": "replacement" if replacement else "remediation",
                "reference_case_id": reference_case_id,
                "reference_context": reference_context,
            }
        )
    return rows


def _append_review_apply_audit_event(
    *,
    append_resource_event_fn: Callable[..., str] | None,
    workspace_dir: str,
    job_id: str,
    payload_obj: dict,
    variant_no: int,
    selected: list[dict],
    applied_reference_case_ids: list[str],
    template_applied_count: int,
    replacement_count: int,
) -> None:
    if not callable(append_resource_event_fn):
        return
    titles: list[str] = []
    seen_titles: set[str] = set()
    types: list[str] = []
    seen_types: set[str] = set()
    for item in selected:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            titles.append(title)
        issue_type = str(item.get("type") or "").strip()
        if issue_type and issue_type not in seen_types:
            seen_types.add(issue_type)
            types.append(issue_type)
    append_resource_event_fn(
        "review_apply",
        workspace_dir=workspace_dir,
        session_id=str(payload_obj.get("session_id") or "").strip() or None,
        user_id=payload_obj.get("user_id"),
        job_id=job_id,
        request_id=str(payload_obj.get("request_id") or "").strip() or None,
        trace_id=str(payload_obj.get("trace_id") or "").strip() or None,
        project_id=str(payload_obj.get("project_id") or "").strip() or None,
        topic=str(payload_obj.get("topic") or "").strip() or None,
        variant_id=variant_no,
        applied_count=len(selected),
        template_applied_count=template_applied_count,
        replacement_count=replacement_count,
        applied_reference_case_ids=applied_reference_case_ids,
        applied_titles=titles,
        applied_types=types,
    )


def _latest_review_apply_summary(
    *,
    variant_no: int,
    selected: list[dict],
    applied_reference_case_ids: list[str],
    template_applied_count: int,
    replacement_count: int,
) -> dict[str, Any]:
    titles: list[str] = []
    seen_titles: set[str] = set()
    issue_types: list[str] = []
    seen_types: set[str] = set()
    for item in selected:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if title and title not in seen_titles:
            seen_titles.add(title)
            titles.append(title)
        issue_type = str(item.get("type") or "").strip()
        if issue_type and issue_type not in seen_types:
            seen_types.add(issue_type)
            issue_types.append(issue_type)
    return {
        "variant": int(variant_no),
        "applied_count": len(selected),
        "template_applied_count": int(template_applied_count or 0),
        "replacement_count": int(replacement_count or 0),
        "titles": titles,
        "issue_types": issue_types,
        "reference_case_ids": list(applied_reference_case_ids or []),
        "has_reference_case": bool(applied_reference_case_ids),
    }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_review_apply_history(rows: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        titles = [str(item).strip() for item in (raw.get("titles") or []) if str(item).strip()]
        issue_types = [str(item).strip() for item in (raw.get("issue_types") or []) if str(item).strip()]
        reference_case_ids = [
            str(item).strip()
            for item in (raw.get("reference_case_ids") or [])
            if str(item).strip()
        ]
        try:
            variant = int(raw.get("variant") or 0)
        except Exception:
            variant = 0
        out.append(
            {
                "variant": variant or None,
                "applied_count": int(raw.get("applied_count") or 0),
                "template_applied_count": int(raw.get("template_applied_count") or 0),
                "replacement_count": int(raw.get("replacement_count") or 0),
                "titles": titles,
                "issue_types": issue_types,
                "reference_case_ids": reference_case_ids,
                "has_reference_case": bool(raw.get("has_reference_case", bool(reference_case_ids))),
                "applied_at": str(raw.get("applied_at") or "").strip() or None,
            }
        )
    return out


def _append_review_apply_history(
    existing_rows: Any,
    latest_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    history = _normalize_review_apply_history(existing_rows)
    entry = dict(latest_summary or {})
    entry["applied_at"] = _utc_now_iso()
    history.append(entry)
    return history[-REVIEW_APPLY_HISTORY_LIMIT:]


def select_review_variant(variants: list[dict], requested_variant: int | None = None, variant_index: int | None = None) -> tuple[int, dict]:
    if not variants:
        return 0, {}
    if requested_variant is not None:
        variant_no = max(1, int(requested_variant or 1))
        if variant_no <= len(variants):
            idx = variant_no - 1
        else:
            idx = 0
    else:
        idx = max(0, min(int(variant_index or 0), len(variants) - 1))
    target = variants[idx] if idx < len(variants) else variants[0]
    return idx, target


def apply_review_decisions(
    *,
    job_id: str,
    variant_index: int | None = None,
    requested_variant: int | None = None,
    workspace_dir: str,
    job: dict,
    data: dict,
    variants: list[dict],
    apply_all: bool,
    decisions: list[Any] | None,
    review_items: list[dict] | None = None,
    review_items_for_variant_fn: Callable[[dict], list[dict]] | None = None,
    save_outputs_fn: Callable[..., dict],
    rebuild_postprocessed_fn: Callable[..., None],
    review_result_metadata_fn: Callable[[list[dict], dict], dict],
    review_variant_result_summary_fn: Callable[[list[dict]], dict],
    write_review_result_bundle_fn: Callable[..., str],
    result_contract_view_fn: Callable[[str, dict, int], dict],
    append_resource_event_fn: Callable[..., str] | None = None,
) -> dict[str, Any]:
    idx, target = select_review_variant(variants, requested_variant=requested_variant, variant_index=variant_index)
    if not isinstance(target, dict):
        raise ValueError("invalid variant record")
    resolved_review_items = review_items
    if resolved_review_items is None and callable(review_items_for_variant_fn):
        resolved_review_items = review_items_for_variant_fn(target)
    if not isinstance(resolved_review_items, list):
        resolved_review_items = []

    item_map = {str(item.get("issue_id") or ""): item for item in resolved_review_items if isinstance(item, dict)}
    selected: list[dict] = []
    if bool(apply_all) and not decisions:
        selected = [item for item in resolved_review_items if isinstance(item, dict)]
    else:
        for decision in decisions or []:
            issue_id = str(_decision_field(decision, "issue_id") or "").strip()
            if not issue_id:
                continue
            base = item_map.get(issue_id)
            if not base or not bool(_decision_field(decision, "apply")):
                continue
            record = dict(base)
            replacement = str(_decision_field(decision, "replacement") or "").strip()
            if replacement:
                record["replacement"] = replacement
            selected.append(record)

    if not selected:
        return {
            "ok": True,
            "job_id": job_id,
            "variant": idx + 1,
            "applied_count": 0,
            "message": "no selected items",
        }

    sections = target.get("sections") if isinstance(target.get("sections"), list) else []
    if not isinstance(sections, list):
        raise ValueError("variant sections missing")

    remediation: list[dict[str, str]] = []
    replacement_count = 0
    for item in selected:
        title = str(item.get("title") or "").strip()
        issue_type = str(item.get("type") or "issue").strip()
        suggestion = str(item.get("suggestion") or item.get("problem") or "").strip()
        replacement = str(item.get("replacement") or "").strip()
        if replacement and title:
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                if str(sec.get("title") or "").strip() == title:
                    sec["original_content"] = sec.get("content") or ""
                    sec["content"] = replacement
                    sec["auto_remediated"] = "review_apply"
                    replacement_count += 1
                    break
            continue
        remediation.append({"title": title, "type": issue_type, "suggestion": suggestion})

    project_id = str(target.get("project_id") or (job.get("payload") or {}).get("project_id") or "").strip() or None
    boq_focus = target.get("boq_focus") if isinstance(target.get("boq_focus"), dict) else {}
    params = load_params()
    payload_obj = (job.get("payload") or {}) if isinstance(job.get("payload"), dict) else {}
    overrides = payload_obj.get("params_override")
    if isinstance(overrides, dict) and overrides:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(params.get(key), dict):
                merged = dict(params.get(key) or {})
                merged.update(value)
                params[key] = merged
            else:
                params[key] = value

    if remediation:
        apply_remediation(
            sections,
            remediation,
            project_id=project_id,
            boq_focus=boq_focus,
            params=params,
            workspace_dir=workspace_dir,
        )
    for sec in sections:
        if isinstance(sec, dict):
            sec["content"] = strip_nonconcrete_language(str(sec.get("content") or ""))

    payload_obj["workspace_dir"] = workspace_dir
    attach_contract_stamp(payload_obj)
    rebuild_postprocessed_fn(
        [target],
        payload=payload_obj,
        report=None,
        params=params,
        workspace_dir=workspace_dir,
    )
    applied_reference_case_ids: list[str] = []
    seen_case_ids: set[str] = set()
    for item in selected:
        if not isinstance(item, dict):
            continue
        case_id = str(item.get("reference_case_id") or "").strip()
        if not case_id or case_id in seen_case_ids:
            continue
        seen_case_ids.add(case_id)
        applied_reference_case_ids.append(case_id)
    latest_review_apply_summary = _latest_review_apply_summary(
        variant_no=idx + 1,
        selected=selected,
        applied_reference_case_ids=applied_reference_case_ids,
        template_applied_count=len(remediation),
        replacement_count=replacement_count,
    )
    existing_result = job.get("result") if isinstance(job.get("result"), dict) else {}
    review_apply_history = _append_review_apply_history(
        existing_result.get("review_apply_history"),
        latest_review_apply_summary,
    )

    outputs = save_outputs_fn(f"actions_{job_id}", variants, workspace_dir=workspace_dir)
    resource_usage_summary = summarize_variants(variants)
    result_metadata = review_result_metadata_fn(variants, payload_obj)
    if not isinstance(result_metadata, dict):
        result_metadata = {}
    result_metadata["latest_review_apply_summary"] = latest_review_apply_summary
    result_metadata["review_apply_history"] = review_apply_history
    quality_by_variant = result_metadata.get("quality_by_variant") if isinstance(result_metadata.get("quality_by_variant"), dict) else {}
    variant_key = str(target.get("variant_id") or "").strip() or str(idx + 1)
    quality_by_variant.setdefault(variant_key, {})
    if isinstance(quality_by_variant.get(variant_key), dict):
        quality_by_variant[variant_key]["latest_review_apply_summary"] = latest_review_apply_summary
        quality_by_variant[variant_key]["review_apply_history"] = [
            item
            for item in review_apply_history
            if not isinstance(item, dict) or not item.get("variant") or int(item.get("variant") or 0) == (idx + 1)
        ]
    result_metadata["quality_by_variant"] = quality_by_variant
    variant_summary = review_variant_result_summary_fn(variants)
    result_bundle_json = write_review_result_bundle_fn(
        job_id,
        payload=payload_obj,
        outputs=outputs,
        result_metadata=result_metadata,
        resource_usage_summary=resource_usage_summary,
        variant_summary=variant_summary,
    )
    job_result = review_rebuild_core.build_review_job_result(
        outputs=outputs,
        resource_usage_summary=resource_usage_summary,
        result_bundle_json=result_bundle_json,
        result_metadata=result_metadata,
    )
    update_job(job_id, workspace_dir=workspace_dir, status="done", result=job_result, error=None)
    data["variants"] = variants
    try:
        Path(outputs["json"]).write_text(json.dumps({"variants": variants}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    contract_view = result_contract_view_fn(job_id, job_result, idx + 1)
    response = {
        "ok": True,
        "job_id": job_id,
        "variant": idx + 1,
        "applied_count": len(selected),
        "template_applied_count": len(remediation),
        "replacement_count": replacement_count,
        "applied_items_summary": _applied_item_summary_rows(selected),
        "applied_reference_case_ids": list(applied_reference_case_ids),
        "files": job_result,
    }
    response["latest_review_apply_summary"] = latest_review_apply_summary
    response["review_apply_history"] = review_apply_history
    response["review_apply_history_count"] = len(review_apply_history)
    response["review_apply_last_applied_at"] = (
        str(review_apply_history[-1].get("applied_at") or "").strip() or None if review_apply_history else None
    )
    if isinstance(job_result, dict):
        job_result["latest_review_apply_summary"] = latest_review_apply_summary
        job_result["review_apply_history"] = review_apply_history
    _append_review_apply_audit_event(
        append_resource_event_fn=append_resource_event_fn,
        workspace_dir=workspace_dir,
        job_id=job_id,
        payload_obj=payload_obj,
        variant_no=idx + 1,
        selected=selected,
        applied_reference_case_ids=applied_reference_case_ids,
        template_applied_count=len(remediation),
        replacement_count=replacement_count,
    )
    response.update(contract_view)
    return response
