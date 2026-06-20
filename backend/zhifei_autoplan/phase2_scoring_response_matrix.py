from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


PHASE_ID = "PHASE_2B_SCORING_RESPONSE_MATRIX"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC"
NO_GO_STATUS = "NO-GO_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC"

DEFAULT_FIXTURE_PATH = Path("projects/_demo_phase2_scoring_response_matrix/project.json")

REQUIRED_SECTIONS = (
    "project_metadata",
    "tender_metadata",
    "scoring_item_metadata",
    "engineering_object_metadata",
    "risk_clue_metadata",
    "output_intent_metadata",
    "audit_boundary_metadata",
    "qingtian_ai_review_metadata",
    "safety_boundary",
)

REQUIRED_SECTION_TYPES = {
    "project_metadata": dict,
    "tender_metadata": dict,
    "scoring_item_metadata": list,
    "engineering_object_metadata": list,
    "risk_clue_metadata": list,
    "output_intent_metadata": dict,
    "audit_boundary_metadata": dict,
    "qingtian_ai_review_metadata": dict,
    "safety_boundary": dict,
}

REQUIRED_SCORING_FIELDS = (
    "item_id",
    "item_name",
    "scoring_category",
    "max_score",
    "requirement_summary",
    "response_strategy",
    "evidence_needed",
    "related_engineering_object_ids",
    "qingtian_keywords",
    "qingtian_parse_tags",
)

REQUIRED_ENGINEERING_OBJECT_FIELDS = (
    "object_id",
    "object_type",
    "object_name",
    "synthetic_scope_summary",
)

REQUIRED_FALSE_FLAGS = (
    "runtime_allowed",
    "endpoint_access_allowed",
    "launcher_allowed",
    "held_config_body_read_allowed",
    "real_business_doc_body_allowed",
    "secret_body_allowed",
    "fetch_pull_merge_push_allowed",
    "export_allowed",
    "formal_writeback_allowed",
)

MATRIX_FIELDS = (
    "scoring_item_id",
    "scoring_title",
    "scoring_category",
    "max_score",
    "response_strategy",
    "linked_engineering_objects",
    "required_evidence",
    "qingtian_keywords",
    "qingtian_parse_tags",
    "missing_items",
    "audit_status",
    "traceability_id",
)

REAL_DOC_BODY_MARKERS = (
    "real_doc_body",
    "document_body",
    "tender_body",
    "drawing_body",
    "boq_body",
    "customer_material_body",
    "original_text",
    "full_text",
    "raw_text",
    "verbatim_text",
    "source_body",
)

SECRET_MARKERS = (
    "api_key",
    "token",
    "secret",
    "password",
    "private_key",
    "credential",
)


def build_phase2b_scoring_response_matrix_snapshot(
    root: str | Path | None = None,
    *,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and validate the Phase 2B scoring response matrix without runtime."""

    repo_root = Path(root or ".").resolve()
    rel_fixture = Path(fixture_path or DEFAULT_FIXTURE_PATH)
    fixture_file = rel_fixture if rel_fixture.is_absolute() else repo_root / rel_fixture
    fixture = _load_fixture(fixture_file)

    failures: list[str] = []
    if not fixture["exists"]:
        failures.append("synthetic_fixture_missing")
        data: Any = None
    elif fixture["data"] is None:
        failures.append("synthetic_fixture_invalid_json")
        data = None
    else:
        data = fixture["data"]

    checks = _checks(data)
    failures.extend(name for name, passed in checks.items() if not passed)
    failures = _dedupe(failures)
    status = PASS_STATUS if not failures else NO_GO_STATUS
    matrix_rows = _matrix_rows(data)

    return {
        "status": status,
        "phase_id": PHASE_ID,
        "failures": failures,
        "workspace_root": str(repo_root),
        "fixture": {
            "path": str(rel_fixture),
            "exists": fixture["exists"],
            "json_loaded": fixture["data"] is not None,
            "content_source": "synthetic_fixture_only",
            "real_business_doc_body_read": False,
        },
        "checks": checks,
        "matrix_fields": list(MATRIX_FIELDS),
        "matrix_rows": matrix_rows,
        "matrix_summary": _matrix_summary(matrix_rows),
        "forbidden_field_scan": _forbidden_field_scan(data),
        "scope": {
            "phase": "Phase 2B",
            "mode": "scoring_response_matrix_static",
            "starts_runtime": False,
            "visits_endpoint": False,
            "runs_launcher": False,
            "reads_held_config_content": False,
            "reads_real_business_content": False,
            "reads_secrets": False,
            "fetch_pull_merge_push": False,
            "materializes_business_outputs": False,
        },
        "forbidden_actions_performed": [],
        "next_gate": (
            "PHASE2C_RISK_OBJECT_BINDING_PLAN_OR_WRITE_GATE"
            if status == PASS_STATUS
            else "repair Phase 2B static scoring response matrix failures"
        ),
    }


def format_phase2b_scoring_response_matrix_report(snapshot: dict[str, Any]) -> str:
    summary = snapshot.get("matrix_summary") or {}
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"fixture_path: {(snapshot.get('fixture') or {}).get('path')}",
        f"fixture_exists: {(snapshot.get('fixture') or {}).get('exists')}",
        f"matrix_row_count: {summary.get('row_count')}",
        f"matrix_scoring_item_ids: {summary.get('scoring_item_ids')}",
        f"matrix_total_max_score: {summary.get('total_max_score')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase2b_scoring_response_matrix_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "data": None}
    try:
        return {"exists": True, "data": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"exists": True, "data": None, "error": str(exc)}


def _checks(data: Any) -> dict[str, bool]:
    if not isinstance(data, dict):
        return {
            "root_is_object": False,
            "required_sections_present": False,
            "required_section_types_valid": False,
            "required_nested_fields_present": False,
            "synthetic_fixture_declared": False,
            "scoring_items_present": False,
            "scoring_item_ids_unique": False,
            "max_scores_valid": False,
            "response_strategies_present": False,
            "required_evidence_present": False,
            "linked_engineering_objects_known": False,
            "qingtian_matrix_fields_present": False,
            "matrix_rows_cover_scoring_items": False,
            "matrix_rows_have_required_fields": False,
            "no_real_doc_body_like_fields": False,
            "no_secret_like_fields": False,
            "forbidden_action_flags_false": False,
        }

    scoring_items = data.get("scoring_item_metadata")
    project = data.get("project_metadata") if isinstance(data.get("project_metadata"), dict) else {}
    safety = data.get("safety_boundary") if isinstance(data.get("safety_boundary"), dict) else {}
    forbidden_scan = _forbidden_field_scan(data)
    matrix_rows = _matrix_rows(data)

    return {
        "root_is_object": True,
        "required_sections_present": all(section in data for section in REQUIRED_SECTIONS),
        "required_section_types_valid": all(
            isinstance(data.get(section), expected_type)
            for section, expected_type in REQUIRED_SECTION_TYPES.items()
        ),
        "required_nested_fields_present": _required_nested_fields_present(data),
        "synthetic_fixture_declared": project.get("sanitized_demo") is True
        and project.get("real_business_material") is False,
        "scoring_items_present": isinstance(scoring_items, list) and bool(scoring_items),
        "scoring_item_ids_unique": _scoring_item_ids_unique(scoring_items),
        "max_scores_valid": _max_scores_valid(scoring_items),
        "response_strategies_present": _response_strategies_present(scoring_items),
        "required_evidence_present": _required_evidence_present(scoring_items),
        "linked_engineering_objects_known": _linked_engineering_objects_known(data),
        "qingtian_matrix_fields_present": _qingtian_matrix_fields_present(scoring_items),
        "matrix_rows_cover_scoring_items": _matrix_rows_cover_scoring_items(scoring_items, matrix_rows),
        "matrix_rows_have_required_fields": _matrix_rows_have_required_fields(matrix_rows),
        "no_real_doc_body_like_fields": not forbidden_scan["real_doc_body_like_paths"],
        "no_secret_like_fields": not forbidden_scan["secret_like_paths"],
        "forbidden_action_flags_false": all(safety.get(flag) is False for flag in REQUIRED_FALSE_FLAGS),
    }


def _required_nested_fields_present(data: dict[str, Any]) -> bool:
    return (
        _list_items_have_fields(data.get("scoring_item_metadata"), REQUIRED_SCORING_FIELDS)
        and _list_items_have_fields(data.get("engineering_object_metadata"), REQUIRED_ENGINEERING_OBJECT_FIELDS)
    )


def _list_items_have_fields(value: Any, fields: Iterable[str]) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict) and all(field in item for field in fields)
        for item in value
    )


def _scoring_item_ids_unique(scoring_items: Any) -> bool:
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    ids = [
        item.get("item_id")
        for item in scoring_items
        if isinstance(item, dict) and isinstance(item.get("item_id"), str) and item.get("item_id")
    ]
    return len(ids) == len(scoring_items) and len(ids) == len(set(ids))


def _max_scores_valid(scoring_items: Any) -> bool:
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get("max_score"), (int, float))
        and not isinstance(item.get("max_score"), bool)
        and item["max_score"] > 0
        for item in scoring_items
    )


def _response_strategies_present(scoring_items: Any) -> bool:
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get("response_strategy"), str)
        and bool(item["response_strategy"].strip())
        for item in scoring_items
    )


def _required_evidence_present(scoring_items: Any) -> bool:
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    return all(_non_empty_string_list(item.get("evidence_needed")) for item in scoring_items if isinstance(item, dict))


def _linked_engineering_objects_known(data: dict[str, Any]) -> bool:
    scoring_items = data.get("scoring_item_metadata")
    engineering_objects = data.get("engineering_object_metadata")
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    if not isinstance(engineering_objects, list) or not engineering_objects:
        return False
    known_ids = {
        item.get("object_id")
        for item in engineering_objects
        if isinstance(item, dict) and isinstance(item.get("object_id"), str)
    }
    for item in scoring_items:
        if not isinstance(item, dict):
            return False
        refs = item.get("related_engineering_object_ids")
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _qingtian_matrix_fields_present(scoring_items: Any) -> bool:
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get("scoring_category"), str)
        and bool(item["scoring_category"].strip())
        and _non_empty_string_list(item.get("qingtian_keywords"))
        and _non_empty_string_list(item.get("qingtian_parse_tags"))
        for item in scoring_items
    )


def _matrix_rows_cover_scoring_items(scoring_items: Any, matrix_rows: list[dict[str, Any]]) -> bool:
    if not isinstance(scoring_items, list) or not scoring_items:
        return False
    expected_ids = sorted(
        item.get("item_id")
        for item in scoring_items
        if isinstance(item, dict) and isinstance(item.get("item_id"), str) and item.get("item_id")
    )
    row_ids = sorted(row.get("scoring_item_id") for row in matrix_rows)
    return len(expected_ids) == len(scoring_items) and row_ids == expected_ids


def _matrix_rows_have_required_fields(matrix_rows: list[dict[str, Any]]) -> bool:
    return bool(matrix_rows) and all(all(field in row for field in MATRIX_FIELDS) for row in matrix_rows)


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _matrix_rows(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get("scoring_item_metadata"), list):
        return []
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(data["scoring_item_metadata"]):
        if not isinstance(item, dict):
            continue
        scoring_item_id = item.get("item_id") if isinstance(item.get("item_id"), str) else f"row-{index:03d}"
        missing_items = _missing_items_for_scoring_item(item)
        rows.append(
            {
                "scoring_item_id": scoring_item_id,
                "scoring_title": item.get("item_name") if isinstance(item.get("item_name"), str) else "",
                "scoring_category": (
                    item.get("scoring_category") if isinstance(item.get("scoring_category"), str) else ""
                ),
                "max_score": item.get("max_score"),
                "response_strategy": (
                    item.get("response_strategy") if isinstance(item.get("response_strategy"), str) else ""
                ),
                "linked_engineering_objects": _sorted_string_list(item.get("related_engineering_object_ids")),
                "required_evidence": _sorted_string_list(item.get("evidence_needed")),
                "qingtian_keywords": _sorted_string_list(item.get("qingtian_keywords")),
                "qingtian_parse_tags": _sorted_string_list(item.get("qingtian_parse_tags")),
                "missing_items": missing_items,
                "audit_status": "ready_static" if not missing_items else "no_go_static",
                "traceability_id": f"phase2b:{scoring_item_id}",
            }
        )
    return sorted(rows, key=lambda row: row["scoring_item_id"])


def _missing_items_for_scoring_item(item: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not isinstance(item.get("item_id"), str) or not item.get("item_id"):
        missing.append("scoring_item_id")
    if not isinstance(item.get("item_name"), str) or not item.get("item_name").strip():
        missing.append("scoring_title")
    if not isinstance(item.get("scoring_category"), str) or not item.get("scoring_category").strip():
        missing.append("scoring_category")
    if (
        not isinstance(item.get("max_score"), (int, float))
        or isinstance(item.get("max_score"), bool)
        or item.get("max_score") <= 0
    ):
        missing.append("max_score")
    if not isinstance(item.get("response_strategy"), str) or not item.get("response_strategy").strip():
        missing.append("response_strategy")
    if not _non_empty_string_list(item.get("related_engineering_object_ids")):
        missing.append("linked_engineering_objects")
    if not _non_empty_string_list(item.get("evidence_needed")):
        missing.append("required_evidence")
    if not _non_empty_string_list(item.get("qingtian_keywords")):
        missing.append("qingtian_keywords")
    if not _non_empty_string_list(item.get("qingtian_parse_tags")):
        missing.append("qingtian_parse_tags")
    return missing


def _sorted_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(item for item in value if isinstance(item, str))


def _matrix_summary(matrix_rows: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_scores = [
        row["max_score"]
        for row in matrix_rows
        if isinstance(row.get("max_score"), (int, float)) and not isinstance(row.get("max_score"), bool)
    ]
    return {
        "row_count": len(matrix_rows),
        "scoring_item_ids": [row["scoring_item_id"] for row in matrix_rows],
        "total_max_score": sum(numeric_scores),
        "audit_statuses": sorted({row["audit_status"] for row in matrix_rows}),
    }


def _forbidden_field_scan(data: Any) -> dict[str, list[str]]:
    real_doc_body_like_paths: list[str] = []
    secret_like_paths: list[str] = []
    for path, value in _walk(data):
        lowered = path.lower()
        key = path.rsplit(".", 1)[-1].lower()
        if key in REQUIRED_FALSE_FLAGS:
            continue
        if any(marker in key or marker in lowered for marker in REAL_DOC_BODY_MARKERS):
            real_doc_body_like_paths.append(path)
        if any(marker in key or marker in lowered for marker in SECRET_MARKERS):
            secret_like_paths.append(path)
        if isinstance(value, str) and any(marker in value.lower() for marker in SECRET_MARKERS):
            secret_like_paths.append(path)
    return {
        "real_doc_body_like_paths": _dedupe(real_doc_body_like_paths),
        "secret_like_paths": _dedupe(secret_like_paths),
    }


def _walk(value: Any, prefix: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}"
            yield child, item
            yield from _walk(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{prefix}[{index}]"
            yield child, item
            yield from _walk(item, child)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
