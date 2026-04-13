from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from backend.zhifei_autoplan.run_contract import (
    load_result_bundle,
    result_bundle_artifacts_complete,
)


def result_bundle_summary(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    path = str(result.get("result_bundle_json") or "").strip()
    if not path:
        return {}
    bundle = load_result_bundle(path)
    return {
        "path": path,
        "available": bool(Path(path).exists()),
        "loaded": isinstance(bundle, dict),
        "complete": result_bundle_artifacts_complete(bundle) if isinstance(bundle, dict) else False,
        "schema_version": str(((bundle or {}).get("_bundle") or {}).get("schema_version") or "").strip() or None,
    }


def result_bundle_view(result: dict | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    path = str(result.get("result_bundle_json") or "").strip()
    if not path:
        return {}
    bundle = load_result_bundle(path)
    if not isinstance(bundle, dict):
        return {}
    request = bundle.get("request") if isinstance(bundle.get("request"), dict) else {}
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), list) else []
    artifact_rows: List[Dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        artifact_rows.append(
            {
                "kind": str(item.get("kind") or "").strip() or None,
                "path": str(item.get("path") or "").strip() or None,
                "exists": bool(item.get("exists", False)),
                "size_bytes": item.get("size_bytes"),
                "sha256": str(item.get("sha256") or "").strip() or None,
            }
        )
    return {
        "request": {
            "project_id": str(request.get("project_id") or "").strip() or None,
            "topic": str(request.get("topic") or "").strip() or None,
            "session_id": str(request.get("session_id") or "").strip() or None,
            "trace_id": str(request.get("trace_id") or "").strip() or None,
            "request_id": str(request.get("request_id") or "").strip() or None,
        },
        "artifacts": artifact_rows,
        "artifact_count": len(artifact_rows),
    }


def blocking_issue_summary_from_result(result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    by_variant = result.get("blocking_issue_summary_by_variant")
    if isinstance(by_variant, dict):
        key_candidates = [str(max(1, int(variant or 1))), str(variant or "")]
        for key in key_candidates:
            item = by_variant.get(key)
            if isinstance(item, dict):
                return item
    summary = result.get("blocking_issue_summary")
    return summary if isinstance(summary, dict) else {}


def reference_quality_summary_from_result(result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    by_variant = result.get("reference_quality_summary_by_variant")
    if isinstance(by_variant, dict):
        key_candidates = [str(max(1, int(variant or 1))), str(variant or "")]
        for key in key_candidates:
            item = by_variant.get(key)
            if isinstance(item, dict):
                return item
    summary = result.get("reference_quality_summary")
    return summary if isinstance(summary, dict) else {}


def blocking_issue_summary_fields(summary: dict | None) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    top_rows = summary.get("top_blocking_issues") if isinstance(summary.get("top_blocking_issues"), list) else []
    top = top_rows[0] if top_rows and isinstance(top_rows[0], dict) else {}
    return {
        "blocking_issue_summary": summary,
        "has_blocking_issues": bool(summary.get("has_blocking_issues", False)),
        "blocking_issue_count": int(summary.get("blocking_issue_count") or 0),
        "failed_gate_metric_count": int(summary.get("failed_gate_metric_count") or 0),
        "top_blocking_issue_title": str(top.get("title") or "").strip() or None,
        "top_blocking_issue_type": str(top.get("type") or "").strip() or None,
    }


def reference_quality_summary_fields(summary: dict | None) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    top_rows = summary.get("top_reference_risks") if isinstance(summary.get("top_reference_risks"), list) else []
    top = top_rows[0] if top_rows and isinstance(top_rows[0], dict) else {}
    affected_case_ids = [
        str(item).strip()
        for item in (summary.get("affected_case_ids") or [])
        if str(item).strip()
    ]
    return {
        "reference_quality_summary": summary,
        "has_reference_risks": bool(summary.get("has_reference_risks", False)),
        "reference_risk_count": int(summary.get("reference_risk_count") or 0),
        "case_copy_risk_count": int(summary.get("case_copy_risk_count") or 0),
        "affected_case_ids": affected_case_ids,
        "top_reference_risk_title": str(top.get("title") or "").strip() or None,
        "top_reference_risk_type": str(top.get("type") or "").strip() or None,
    }


def latest_review_apply_summary_fields(summary: dict | None) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    reference_case_ids = [
        str(item).strip()
        for item in (summary.get("reference_case_ids") or [])
        if str(item).strip()
    ]
    issue_types = [
        str(item).strip()
        for item in (summary.get("issue_types") or [])
        if str(item).strip()
    ]
    return {
        "latest_review_apply_summary": summary,
        "review_apply_variant": int(summary.get("variant") or 0) or None,
        "review_apply_applied_count": int(summary.get("applied_count") or 0),
        "review_apply_template_applied_count": int(summary.get("template_applied_count") or 0),
        "review_apply_replacement_count": int(summary.get("replacement_count") or 0),
        "review_apply_reference_case_ids": reference_case_ids,
        "review_apply_has_reference_case": bool(summary.get("has_reference_case", False)),
        "review_apply_issue_types": issue_types,
    }


def latest_review_apply_summary_from_result(result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    quality_by_variant = result.get("quality_by_variant")
    if isinstance(quality_by_variant, dict):
        key_candidates = [str(max(1, int(variant or 1))), str(variant or "")]
        for key in key_candidates:
            item = quality_by_variant.get(key)
            if isinstance(item, dict) and isinstance(item.get("latest_review_apply_summary"), dict):
                return item.get("latest_review_apply_summary") or {}
    summary = result.get("latest_review_apply_summary")
    return summary if isinstance(summary, dict) else {}


def review_apply_history_from_result(result: dict | None, *, variant: int = 1) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    raw = result.get("review_apply_history")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    target_variant = max(1, int(variant or 1))
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            item_variant = int(item.get("variant") or 0)
        except Exception:
            item_variant = 0
        if item_variant and item_variant != target_variant:
            continue
        out.append(item)
    return out


def review_apply_history_fields(history: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = [item for item in (history or []) if isinstance(item, dict)]
    latest = rows[-1] if rows else {}
    return {
        "review_apply_history": rows,
        "review_apply_history_count": len(rows),
        "review_apply_last_applied_at": str(latest.get("applied_at") or "").strip() or None,
    }


def reference_enhancements_from_result(result: dict | None, *, variant: int = 1) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    by_variant = result.get("reference_enhancements_by_variant")
    if isinstance(by_variant, dict):
        key_candidates = [str(max(1, int(variant or 1))), str(variant or "")]
        for key in key_candidates:
            item = by_variant.get(key)
            if isinstance(item, dict):
                return item
    aggregate = result.get("reference_enhancements")
    return aggregate if isinstance(aggregate, dict) else {}


def _library_enhancement_fields(summary: dict | None, *, id_key: str, prefix: str) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    selected_ids = [
        str(item).strip()
        for item in (summary.get(id_key) or [])
        if str(item).strip()
    ]
    warnings = [
        str(item).strip()
        for item in (summary.get("warning_list") or [])
        if str(item).strip()
    ]
    matched_chapters = [
        str(item).strip()
        for item in (summary.get("matched_chapters") or [])
        if str(item).strip()
    ]
    if not matched_chapters:
        chapter = str(summary.get("matched_chapter") or "").strip()
        if chapter:
            matched_chapters = [chapter]
    match_reasons = [
        str(item).strip()
        for item in (summary.get("match_reasons") or [])
        if str(item).strip()
    ]
    if not match_reasons:
        reason = str(summary.get("match_reason") or "").strip()
        if reason:
            match_reasons = [reason]
    return {
        f"{prefix}_enabled": bool(summary.get("enabled", False)),
        f"{prefix}_selected_ids": selected_ids,
        f"{prefix}_matched_project_type": str(summary.get("matched_project_type") or "").strip() or None,
        f"{prefix}_matched_chapters": matched_chapters,
        f"{prefix}_match_reasons": match_reasons,
        f"{prefix}_hit_count": int(summary.get("hit_count") or 0),
        f"{prefix}_warning_list": warnings,
        f"{prefix}_warning_count": len(warnings),
    }


def reference_enhancement_fields(enhancements: dict | None) -> dict[str, Any]:
    if not isinstance(enhancements, dict):
        return {}
    case_library = enhancements.get("case_library") if isinstance(enhancements.get("case_library"), dict) else {}
    image_library = enhancements.get("image_library") if isinstance(enhancements.get("image_library"), dict) else {}
    return {
        "reference_enhancements": enhancements,
        "case_library_summary": case_library,
        "image_library_summary": image_library,
        **_library_enhancement_fields(case_library, id_key="selected_case_ids", prefix="case_library"),
        **_library_enhancement_fields(image_library, id_key="selected_image_ids", prefix="image_library"),
    }


def download_artifact_path(result: dict | None, kind: str, *, variant: int = 1) -> str | None:
    if not isinstance(result, dict):
        return None
    raw = result.get(kind)
    if kind in {"docx", "compare_docx", "focus_xlsx", "score_overview_xlsx", "expert_review_docx"} and isinstance(raw, list):
        idx = max(1, int(variant or 1)) - 1
        item = raw[idx] if idx < len(raw) else None
        path = str(item or "").strip()
        return path or None
    path = str(raw or "").strip()
    return path or None


def download_filename(
    job_id: str,
    kind: str,
    *,
    download_kind_specs: Dict[str, Dict[str, str]],
    variant: int = 1,
) -> str:
    spec = download_kind_specs.get(kind) or download_kind_specs["docx"]
    return spec["filename_pattern"].format(job_id=str(job_id or "").strip(), variant=max(1, int(variant or 1)))


def build_download_index(
    job_id: str,
    result: dict | None,
    *,
    download_kind_specs: Dict[str, Dict[str, str]],
    variant: int = 1,
) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    out: Dict[str, Any] = {}
    current_variant = max(1, int(variant or 1))
    for kind, spec in download_kind_specs.items():
        path = download_artifact_path(result, kind, variant=current_variant)
        exists = bool(path and Path(path).exists())
        out[kind] = {
            "kind": kind,
            "path": path,
            "exists": exists,
            "downloadable": exists,
            "variant": current_variant if kind in {"docx", "compare_docx", "focus_xlsx", "score_overview_xlsx", "expert_review_docx"} else None,
            "media_type": spec["media_type"],
            "filename": download_filename(
                job_id,
                kind,
                download_kind_specs=download_kind_specs,
                variant=current_variant,
            ),
        }
    return out


def download_ready_summary(download_index: dict | None) -> dict[str, Any]:
    if not isinstance(download_index, dict):
        return {
            "download_ready_count": 0,
            "download_ready_kinds": [],
            "primary_download_kind": None,
        }
    ready_kinds: List[str] = []
    for kind, item in download_index.items():
        if not isinstance(item, dict):
            continue
        if bool(item.get("downloadable", False)):
            ready_kinds.append(str(kind))
    primary_download_kind = None
    for candidate in ("docx", "compare_docx", "json", "result_bundle_json", "focus_xlsx", "score_overview_xlsx", "expert_review_docx"):
        if candidate in ready_kinds:
            primary_download_kind = candidate
            break
    return {
        "download_ready_count": len(ready_kinds),
        "download_ready_kinds": ready_kinds,
        "primary_download_kind": primary_download_kind,
    }


def result_contract_view(
    job_id: str,
    result: dict | None,
    *,
    download_kind_specs: Dict[str, Dict[str, str]],
    variant: int = 1,
) -> dict[str, Any]:
    bundle_summary = result_bundle_summary(result)
    bundle_view = result_bundle_view(result)
    download_index = build_download_index(
        job_id,
        result,
        download_kind_specs=download_kind_specs,
        variant=variant,
    )
    download_ready = download_ready_summary(download_index)
    blocking_summary = blocking_issue_summary_from_result(result, variant=variant)
    reference_quality_summary = reference_quality_summary_from_result(result, variant=variant)
    reference_enhancements = reference_enhancements_from_result(result, variant=variant)
    latest_review_apply_summary = latest_review_apply_summary_from_result(result, variant=variant)
    review_apply_history = review_apply_history_from_result(result, variant=variant)
    out: Dict[str, Any] = {
        "download_index": download_index,
        **download_ready,
        **blocking_issue_summary_fields(blocking_summary),
        **reference_quality_summary_fields(reference_quality_summary),
        **reference_enhancement_fields(reference_enhancements),
        **latest_review_apply_summary_fields(latest_review_apply_summary),
        **review_apply_history_fields(review_apply_history),
    }
    if bundle_summary:
        out["result_bundle_summary"] = bundle_summary
        out["result_bundle_json"] = bundle_summary.get("path")
        out["result_bundle_available"] = bool(bundle_summary.get("available", False))
        out["result_bundle_loaded"] = bool(bundle_summary.get("loaded", False))
        out["result_bundle_complete"] = bool(bundle_summary.get("complete", False))
        out["result_bundle_schema_version"] = bundle_summary.get("schema_version")
    if bundle_view:
        out["result_bundle_request"] = bundle_view.get("request")
        out["result_bundle_artifacts"] = bundle_view.get("artifacts")
        out["result_bundle_artifact_count"] = bundle_view.get("artifact_count")
    return out
