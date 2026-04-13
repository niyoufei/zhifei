from __future__ import annotations

from typing import Any, Callable, Dict, List


def variant_result_key(row: Dict[str, Any]) -> str:
    variant_id = str(row.get("variant_id") or "").strip()
    if variant_id:
        return variant_id
    return f"v{max(1, int(row.get('variant_index') or 1))}"


def build_blocking_issue_summary(
    *,
    quality_checks: Dict[str, Any] | None,
    quality_gate: Dict[str, Any] | None,
    limit: int = 8,
) -> Dict[str, Any]:
    qc = quality_checks if isinstance(quality_checks, dict) else {}
    gate = quality_gate if isinstance(quality_gate, dict) else {}
    issues = qc.get("issue_list") if isinstance(qc.get("issue_list"), list) else []
    gate_failed = gate.get("failed") if isinstance(gate.get("failed"), list) else []
    blocking_types = {
        "evidence_gap",
        "evidence_traceability_gap",
        "core_conclusion_evidence_gap",
        "risk_triplet_gap",
        "engineering_gap",
        "quantitative_gap",
        "score_point_missing",
        "special_topic_missing",
        "required_topic_detail_gap",
        "qse_closed_loop_gap",
        "chapter_blueprint_gap",
        "boq_focus_missing",
        "boq_focus_item_closure_gap",
        "boq_focus_item_typed_evidence_gap",
        "drawing_evidence_gap",
        "drawing_anchor_gap",
        "standard_evidence_gap",
        "consistency_conflict",
        "outline_missing",
    }
    non_blocking_high_severity_types = {
        "case_reference_copy_risk",
    }
    blocking_severity = {"high", "critical", "blocker"}
    rows: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue_type = str(item.get("type") or "").strip()
        severity = str(item.get("severity") or "").strip().lower()
        if issue_type in non_blocking_high_severity_types:
            continue
        if issue_type not in blocking_types and severity not in blocking_severity:
            continue
        title = str(item.get("title") or "").strip() or "章节"
        key = (title, issue_type, str(item.get("problem") or "").strip())
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "title": title,
                "type": issue_type or "blocking_issue",
                "severity": severity or "high",
                "problem": str(item.get("problem") or "").strip(),
                "suggestion": str(item.get("suggestion") or "").strip(),
            }
        )
    failed_metrics: List[str] = []
    for item in gate_failed:
        if not isinstance(item, dict):
            continue
        metric = str(item.get("metric") or "").strip()
        if metric:
            failed_metrics.append(metric)
    return {
        "has_blocking_issues": bool(rows) or bool(failed_metrics),
        "blocking_issue_count": len(rows),
        "failed_gate_metric_count": len(failed_metrics),
        "failed_gate_metrics": failed_metrics[: max(1, int(limit or 8))],
        "top_blocking_issues": rows[: max(1, int(limit or 8))],
    }


def build_reference_quality_summary(
    *,
    quality_checks: Dict[str, Any] | None,
    limit: int = 8,
) -> Dict[str, Any]:
    qc = quality_checks if isinstance(quality_checks, dict) else {}
    issues = qc.get("issue_list") if isinstance(qc.get("issue_list"), list) else []
    reference_types = {"case_reference_copy_risk"}
    rows: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    affected_case_ids: List[str] = []
    seen_case_ids: set[str] = set()
    case_copy_risk_count = 0
    for item in issues:
        if not isinstance(item, dict):
            continue
        issue_type = str(item.get("type") or "").strip()
        if issue_type not in reference_types:
            continue
        title = str(item.get("title") or "").strip() or "章节"
        problem = str(item.get("problem") or "").strip()
        severity = str(item.get("severity") or "").strip().lower() or "high"
        reference_case_id = str(item.get("reference_case_id") or "").strip()
        key = (title, issue_type, problem, reference_case_id)
        if key in seen:
            continue
        seen.add(key)
        case_copy_risk_count += 1
        row = {
            "title": title,
            "type": issue_type,
            "severity": severity,
            "problem": problem,
            "suggestion": str(item.get("suggestion") or "").strip(),
        }
        if reference_case_id:
            row["reference_case_id"] = reference_case_id
            if reference_case_id not in seen_case_ids:
                seen_case_ids.add(reference_case_id)
                affected_case_ids.append(reference_case_id)
        rows.append(row)
    return {
        "has_reference_risks": bool(rows),
        "reference_risk_count": len(rows),
        "case_copy_risk_count": case_copy_risk_count,
        "affected_case_ids": affected_case_ids,
        "top_reference_risks": rows[: max(1, int(limit or 8))],
    }


def _normalize_reference_library_summary(summary: Dict[str, Any] | None, *, id_key: str) -> Dict[str, Any]:
    data = summary if isinstance(summary, dict) else {}
    selected_ids = [
        str(item).strip()
        for item in (data.get(id_key) or [])
        if str(item).strip()
    ]
    warning_list = [
        str(item).strip()
        for item in (data.get("warning_list") or [])
        if str(item).strip()
    ]
    matched_project_type = str(data.get("matched_project_type") or "").strip() or None
    matched_chapter = str(data.get("matched_chapter") or "").strip() or None
    match_reason = str(data.get("match_reason") or "").strip() or None
    return {
        "enabled": bool(data.get("enabled", False)),
        id_key: selected_ids,
        "matched_project_type": matched_project_type,
        "matched_chapter": matched_chapter,
        "match_reason": match_reason,
        "hit_count": int(data.get("hit_count") or 0),
        "warning_list": warning_list,
    }


def _aggregate_reference_library_summaries(
    by_variant: Dict[str, Any] | None,
    *,
    id_key: str,
) -> Dict[str, Any]:
    rows = by_variant if isinstance(by_variant, dict) else {}
    enabled = False
    selected_ids: List[str] = []
    seen_ids: set[str] = set()
    matched_project_types: List[str] = []
    seen_project_types: set[str] = set()
    matched_chapters: List[str] = []
    seen_chapters: set[str] = set()
    match_reasons: List[str] = []
    seen_reasons: set[str] = set()
    warning_list: List[str] = []
    seen_warnings: set[str] = set()
    variant_ids: List[str] = []
    hit_count = 0
    for variant_id, raw in rows.items():
        item = _normalize_reference_library_summary(raw, id_key=id_key)
        if item["enabled"] or item["hit_count"] or item["warning_list"]:
            variant_ids.append(str(variant_id))
        enabled = enabled or bool(item["enabled"])
        hit_count += int(item["hit_count"] or 0)
        for value in item[id_key]:
            if value not in seen_ids:
                seen_ids.add(value)
                selected_ids.append(value)
        project_type = str(item.get("matched_project_type") or "").strip()
        if project_type and project_type not in seen_project_types:
            seen_project_types.add(project_type)
            matched_project_types.append(project_type)
        chapter = str(item.get("matched_chapter") or "").strip()
        if chapter and chapter not in seen_chapters:
            seen_chapters.add(chapter)
            matched_chapters.append(chapter)
        reason = str(item.get("match_reason") or "").strip()
        if reason and reason not in seen_reasons:
            seen_reasons.add(reason)
            match_reasons.append(reason)
        for warning in item["warning_list"]:
            if warning not in seen_warnings:
                seen_warnings.add(warning)
                warning_list.append(warning)
    return {
        "enabled": enabled,
        id_key: selected_ids,
        "matched_project_type": matched_project_types[0] if len(matched_project_types) == 1 else None,
        "matched_chapters": matched_chapters,
        "match_reasons": match_reasons,
        "hit_count": hit_count,
        "warning_list": warning_list,
        "variant_ids": variant_ids,
    }


def build_result_metadata_from_rows(
    *,
    results: List[Dict[str, Any]],
    payload: Dict[str, Any],
    rows: List[Dict[str, Any]],
    blocking_summary_builder: Callable[..., Dict[str, Any]],
) -> Dict[str, Any]:
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    first = rows[0] if rows else {}
    metadata: Dict[str, Any] = {
        "generation_mode_summary": {
            "profile": str(mode_policy.get("profile") or first.get("generation_mode") or payload.get("generation_mode") or "").strip() or None,
            "mode_effective": str(
                mode_policy.get("mode_effective")
                or first.get("mode_effective")
                or first.get("generation_mode")
                or payload.get("generation_mode")
                or ""
            ).strip()
            or None,
            "stable_output": bool(mode_policy.get("stable_output", first.get("stable_output", False))),
            "deterministic_variant_forced": bool(
                mode_policy.get("deterministic_variant_forced", first.get("deterministic_variant_forced", False))
            ),
            "deterministic_logic_template_id": str(
                mode_policy.get("deterministic_logic_template_id")
                or first.get("deterministic_logic_template_id")
                or first.get("logic_template_id")
                or payload.get("logic_template_id")
                or ""
            ).strip()
            or None,
        },
        "runtime_by_variant": {},
        "quality_by_variant": {},
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = variant_result_key(row)
        metadata["runtime_by_variant"][key] = {
            "variant_index": row.get("variant_index"),
            "variant_id": row.get("variant_id"),
            "generation_mode": row.get("generation_mode"),
            "mode_effective": row.get("mode_effective"),
            "section_count": row.get("section_count"),
            "pipeline_stages": row.get("pipeline_stages"),
            "retrieval_cache": row.get("retrieval_cache"),
            "self_evolution": row.get("self_evolution"),
            "section_runtime_budget_preview": row.get("section_runtime_budget_preview"),
            "resource_usage_summary": row.get("resource_usage_summary"),
            "case_library_summary": row.get("case_library_summary") if isinstance(row.get("case_library_summary"), dict) else {},
            "image_library_summary": row.get("image_library_summary") if isinstance(row.get("image_library_summary"), dict) else {},
        }
        metadata["quality_by_variant"][key] = {
            "variant_index": row.get("variant_index"),
            "variant_id": row.get("variant_id"),
            "logic_template_id": row.get("logic_template_id"),
            "logic_template_name": row.get("logic_template_name"),
            "quality_score": row.get("quality_score"),
            "quality_gate_ok": row.get("quality_gate_ok"),
            "quality_gate_failed_count": row.get("quality_gate_failed_count"),
            "remediation_strategy_audit": row.get("remediation_strategy_audit"),
            "remediation_execution_audit": row.get("remediation_execution_audit"),
        }
    blocking_by_variant: Dict[str, Any] = {}
    for idx, item in enumerate(results or [], start=1):
        if not isinstance(item, dict):
            continue
        key = str(item.get("variant_id") or "").strip() or str(idx)
        summary = blocking_summary_builder(
            quality_checks=item.get("quality_checks") if isinstance(item.get("quality_checks"), dict) else {},
            quality_gate=item.get("quality_gate") if isinstance(item.get("quality_gate"), dict) else {},
        )
        metadata["quality_by_variant"].setdefault(key, {})
        metadata["quality_by_variant"][key]["blocking_issue_summary"] = summary
        blocking_by_variant[key] = summary
    metadata["blocking_issue_summary_by_variant"] = blocking_by_variant
    reference_quality_by_variant: Dict[str, Any] = {}
    for idx, item in enumerate(results or [], start=1):
        if not isinstance(item, dict):
            continue
        key = str(item.get("variant_id") or "").strip() or str(idx)
        summary = build_reference_quality_summary(
            quality_checks=item.get("quality_checks") if isinstance(item.get("quality_checks"), dict) else {},
        )
        metadata["quality_by_variant"].setdefault(key, {})
        metadata["quality_by_variant"][key]["reference_quality_summary"] = summary
        reference_quality_by_variant[key] = summary
    metadata["reference_quality_summary_by_variant"] = reference_quality_by_variant
    top_variant_key = None
    top_variant_count = -1
    for key, summary in blocking_by_variant.items():
        if not isinstance(summary, dict):
            continue
        score = int(summary.get("blocking_issue_count") or 0) + int(summary.get("failed_gate_metric_count") or 0)
        if score > top_variant_count:
            top_variant_count = score
            top_variant_key = key
    metadata["blocking_issue_summary"] = (
        dict(blocking_by_variant.get(top_variant_key) or {})
        if top_variant_key and isinstance(blocking_by_variant.get(top_variant_key), dict)
        else {
            "has_blocking_issues": False,
            "blocking_issue_count": 0,
            "failed_gate_metric_count": 0,
            "failed_gate_metrics": [],
            "top_blocking_issues": [],
        }
    )
    aggregate_rows: List[Dict[str, Any]] = []
    aggregate_case_ids: List[str] = []
    seen_aggregate_case_ids: set[str] = set()
    total_case_copy_risk_count = 0
    for key, summary in reference_quality_by_variant.items():
        if not isinstance(summary, dict):
            continue
        total_case_copy_risk_count += int(summary.get("case_copy_risk_count") or 0)
        for case_id in summary.get("affected_case_ids") or []:
            text = str(case_id or "").strip()
            if text and text not in seen_aggregate_case_ids:
                seen_aggregate_case_ids.add(text)
                aggregate_case_ids.append(text)
        for row in summary.get("top_reference_risks") or []:
            if isinstance(row, dict):
                rec = dict(row)
                rec.setdefault("variant_id", key)
                aggregate_rows.append(rec)
    metadata["reference_quality_summary"] = {
        "has_reference_risks": any(
            bool(summary.get("has_reference_risks"))
            for summary in reference_quality_by_variant.values()
            if isinstance(summary, dict)
        ),
        "reference_risk_count": sum(
            int(summary.get("reference_risk_count") or 0)
            for summary in reference_quality_by_variant.values()
            if isinstance(summary, dict)
        ),
        "case_copy_risk_count": total_case_copy_risk_count,
        "affected_case_ids": aggregate_case_ids,
        "top_reference_risks": aggregate_rows[:8],
    }
    if len(rows) == 1 and isinstance(first, dict):
        logic_template_id = str(first.get("logic_template_id") or "").strip() or None
        logic_template_name = str(first.get("logic_template_name") or "").strip() or None
        if logic_template_id:
            metadata["logic_template_id"] = logic_template_id
        if logic_template_name:
            metadata["logic_template_name"] = logic_template_name
    metadata["reference_enhancements_by_variant"] = {
        key: {
            "case_library": _normalize_reference_library_summary(
                runtime.get("case_library_summary") if isinstance(runtime, dict) else {},
                id_key="selected_case_ids",
            ),
            "image_library": _normalize_reference_library_summary(
                runtime.get("image_library_summary") if isinstance(runtime, dict) else {},
                id_key="selected_image_ids",
            ),
        }
        for key, runtime in metadata["runtime_by_variant"].items()
        if isinstance(runtime, dict)
    }
    enhancements_by_variant = metadata["reference_enhancements_by_variant"]
    metadata["reference_enhancements"] = {
        "case_library": _aggregate_reference_library_summaries(
            {
                key: value.get("case_library")
                for key, value in enhancements_by_variant.items()
                if isinstance(value, dict)
            },
            id_key="selected_case_ids",
        ),
        "image_library": _aggregate_reference_library_summaries(
            {
                key: value.get("image_library")
                for key, value in enhancements_by_variant.items()
                if isinstance(value, dict)
            },
            id_key="selected_image_ids",
        ),
    }
    return metadata
