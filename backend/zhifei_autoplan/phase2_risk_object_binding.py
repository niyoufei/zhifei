from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from backend.zhifei_autoplan.phase2_scoring_response_matrix import (
    PASS_STATUS as PHASE2B_PASS_STATUS,
    build_phase2b_scoring_response_matrix_snapshot,
)


PHASE_ID = "PHASE_2C_RISK_OBJECT_BINDING"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE2C_RISK_OBJECT_BINDING_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC"
NO_GO_STATUS = "NO-GO_PHASE2C_RISK_OBJECT_BINDING_STATIC"

DEFAULT_FIXTURE_PATH = Path("projects/_demo_phase2_risk_object_binding/project.json")

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

REQUIRED_RISK_FIELDS = (
    "risk_id",
    "risk_title",
    "risk_category",
    "risk_level",
    "risk_clue_id",
    "linked_engineering_object_ids",
    "linked_scoring_item_ids",
    "response_control_points",
    "required_evidence",
    "qingtian_tags",
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

BINDING_FIELDS = (
    "risk_id",
    "risk_title",
    "risk_category",
    "risk_level",
    "risk_clue_id",
    "linked_engineering_object_ids",
    "linked_scoring_item_ids",
    "response_control_points",
    "required_evidence",
    "qingtian_tags",
    "audit_traceability_id",
    "binding_status",
    "diagnostics",
)

VALID_RISK_LEVELS = ("low", "medium", "high", "critical")

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


def build_phase2c_risk_object_binding_snapshot(
    root: str | Path | None = None,
    *,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and validate the Phase 2C risk-object binding without runtime."""

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

    phase2b_snapshot = build_phase2b_scoring_response_matrix_snapshot(
        repo_root,
        fixture_path=rel_fixture,
    )
    checks = _checks(data, phase2b_snapshot)
    failures.extend(name for name, passed in checks.items() if not passed)
    failures = _dedupe(failures)
    status = PASS_STATUS if not failures else NO_GO_STATUS
    binding_rows = _binding_rows(data, phase2b_snapshot)

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
        "phase2b_matrix": {
            "status": phase2b_snapshot.get("status"),
            "failures": phase2b_snapshot.get("failures", []),
            "scoring_item_ids": (phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []),
        },
        "binding_fields": list(BINDING_FIELDS),
        "binding_rows": binding_rows,
        "binding_summary": _binding_summary(binding_rows),
        "forbidden_field_scan": _forbidden_field_scan(data),
        "scope": {
            "phase": "Phase 2C",
            "mode": "risk_object_binding_static",
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
            "PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_PLAN_OR_WRITE_GATE"
            if status == PASS_STATUS
            else "repair Phase 2C static risk-object binding failures"
        ),
    }


def format_phase2c_risk_object_binding_report(snapshot: dict[str, Any]) -> str:
    summary = snapshot.get("binding_summary") or {}
    phase2b = snapshot.get("phase2b_matrix") or {}
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"fixture_path: {(snapshot.get('fixture') or {}).get('path')}",
        f"fixture_exists: {(snapshot.get('fixture') or {}).get('exists')}",
        f"phase2b_matrix_status: {phase2b.get('status')}",
        f"binding_row_count: {summary.get('row_count')}",
        f"binding_risk_ids: {summary.get('risk_ids')}",
        f"binding_risk_levels: {summary.get('risk_levels')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase2c_risk_object_binding_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "data": None}
    try:
        return {"exists": True, "data": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"exists": True, "data": None, "error": str(exc)}


def _checks(data: Any, phase2b_snapshot: dict[str, Any]) -> dict[str, bool]:
    if not isinstance(data, dict):
        return {
            "root_is_object": False,
            "required_sections_present": False,
            "required_section_types_valid": False,
            "required_nested_fields_present": False,
            "synthetic_fixture_declared": False,
            "phase2b_matrix_pass": False,
            "risk_clues_present": False,
            "risk_ids_unique": False,
            "risk_levels_valid": False,
            "linked_engineering_objects_known": False,
            "linked_scoring_items_known": False,
            "response_control_points_present": False,
            "required_evidence_present": False,
            "qingtian_tags_present": False,
            "binding_rows_cover_risk_clues": False,
            "binding_rows_have_required_fields": False,
            "no_real_doc_body_like_fields": False,
            "no_secret_like_fields": False,
            "forbidden_action_flags_false": False,
        }

    risk_clues = data.get("risk_clue_metadata")
    project = data.get("project_metadata") if isinstance(data.get("project_metadata"), dict) else {}
    safety = data.get("safety_boundary") if isinstance(data.get("safety_boundary"), dict) else {}
    forbidden_scan = _forbidden_field_scan(data)
    binding_rows = _binding_rows(data, phase2b_snapshot)

    return {
        "root_is_object": True,
        "required_sections_present": all(section in data for section in REQUIRED_SECTIONS),
        "required_section_types_valid": all(
            isinstance(data.get(section), expected_type)
            for section, expected_type in REQUIRED_SECTION_TYPES.items()
        ),
        "required_nested_fields_present": _list_items_have_fields(risk_clues, REQUIRED_RISK_FIELDS),
        "synthetic_fixture_declared": project.get("sanitized_demo") is True
        and project.get("real_business_material") is False,
        "phase2b_matrix_pass": phase2b_snapshot.get("status") == PHASE2B_PASS_STATUS,
        "risk_clues_present": isinstance(risk_clues, list) and bool(risk_clues),
        "risk_ids_unique": _risk_ids_unique(risk_clues),
        "risk_levels_valid": _risk_levels_valid(risk_clues),
        "linked_engineering_objects_known": _linked_engineering_objects_known(data),
        "linked_scoring_items_known": _linked_scoring_items_known(data, phase2b_snapshot),
        "response_control_points_present": _risk_list_field_present(risk_clues, "response_control_points"),
        "required_evidence_present": _risk_list_field_present(risk_clues, "required_evidence"),
        "qingtian_tags_present": _risk_list_field_present(risk_clues, "qingtian_tags"),
        "binding_rows_cover_risk_clues": _binding_rows_cover_risk_clues(risk_clues, binding_rows),
        "binding_rows_have_required_fields": _binding_rows_have_required_fields(binding_rows),
        "no_real_doc_body_like_fields": not forbidden_scan["real_doc_body_like_paths"],
        "no_secret_like_fields": not forbidden_scan["secret_like_paths"],
        "forbidden_action_flags_false": all(safety.get(flag) is False for flag in REQUIRED_FALSE_FLAGS),
    }


def _list_items_have_fields(value: Any, fields: Iterable[str]) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict) and all(field in item for field in fields)
        for item in value
    )


def _risk_ids_unique(risk_clues: Any) -> bool:
    if not isinstance(risk_clues, list) or not risk_clues:
        return False
    ids = [
        item.get("risk_id")
        for item in risk_clues
        if isinstance(item, dict) and isinstance(item.get("risk_id"), str) and item.get("risk_id")
    ]
    return len(ids) == len(risk_clues) and len(ids) == len(set(ids))


def _risk_levels_valid(risk_clues: Any) -> bool:
    if not isinstance(risk_clues, list) or not risk_clues:
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get("risk_level"), str)
        and item["risk_level"] in VALID_RISK_LEVELS
        for item in risk_clues
    )


def _linked_engineering_objects_known(data: dict[str, Any]) -> bool:
    risk_clues = data.get("risk_clue_metadata")
    engineering_objects = data.get("engineering_object_metadata")
    if not isinstance(risk_clues, list) or not risk_clues:
        return False
    if not isinstance(engineering_objects, list) or not engineering_objects:
        return False
    known_ids = {
        item.get("object_id")
        for item in engineering_objects
        if isinstance(item, dict) and isinstance(item.get("object_id"), str)
    }
    for item in risk_clues:
        if not isinstance(item, dict):
            return False
        refs = item.get("linked_engineering_object_ids")
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _linked_scoring_items_known(data: dict[str, Any], phase2b_snapshot: dict[str, Any]) -> bool:
    risk_clues = data.get("risk_clue_metadata")
    if not isinstance(risk_clues, list) or not risk_clues:
        return False
    known_ids = set((phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []))
    if not known_ids:
        return False
    for item in risk_clues:
        if not isinstance(item, dict):
            return False
        refs = item.get("linked_scoring_item_ids")
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _risk_list_field_present(risk_clues: Any, field: str) -> bool:
    if not isinstance(risk_clues, list) or not risk_clues:
        return False
    return all(isinstance(item, dict) and _non_empty_string_list(item.get(field)) for item in risk_clues)


def _binding_rows_cover_risk_clues(risk_clues: Any, binding_rows: list[dict[str, Any]]) -> bool:
    if not isinstance(risk_clues, list) or not risk_clues:
        return False
    expected_ids = sorted(
        item.get("risk_id")
        for item in risk_clues
        if isinstance(item, dict) and isinstance(item.get("risk_id"), str) and item.get("risk_id")
    )
    row_ids = sorted(row.get("risk_id") for row in binding_rows)
    return len(expected_ids) == len(risk_clues) and row_ids == expected_ids


def _binding_rows_have_required_fields(binding_rows: list[dict[str, Any]]) -> bool:
    return bool(binding_rows) and all(all(field in row for field in BINDING_FIELDS) for row in binding_rows)


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _binding_rows(data: Any, phase2b_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get("risk_clue_metadata"), list):
        return []

    known_object_ids = _known_engineering_object_ids(data)
    known_scoring_item_ids = set((phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []))
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(data["risk_clue_metadata"]):
        if not isinstance(item, dict):
            continue
        risk_id = item.get("risk_id") if isinstance(item.get("risk_id"), str) else f"risk-{index:03d}"
        diagnostics = _diagnostics_for_risk(item, known_object_ids, known_scoring_item_ids)
        rows.append(
            {
                "risk_id": risk_id,
                "risk_title": item.get("risk_title") if isinstance(item.get("risk_title"), str) else "",
                "risk_category": item.get("risk_category") if isinstance(item.get("risk_category"), str) else "",
                "risk_level": item.get("risk_level") if isinstance(item.get("risk_level"), str) else "",
                "risk_clue_id": item.get("risk_clue_id") if isinstance(item.get("risk_clue_id"), str) else "",
                "linked_engineering_object_ids": _sorted_string_list(item.get("linked_engineering_object_ids")),
                "linked_scoring_item_ids": _sorted_string_list(item.get("linked_scoring_item_ids")),
                "response_control_points": _sorted_string_list(item.get("response_control_points")),
                "required_evidence": _sorted_string_list(item.get("required_evidence")),
                "qingtian_tags": _sorted_string_list(item.get("qingtian_tags")),
                "audit_traceability_id": f"phase2c:{risk_id}",
                "binding_status": "ready_static" if not diagnostics else "no_go_static",
                "diagnostics": diagnostics,
            }
        )
    return sorted(rows, key=lambda row: row["risk_id"])


def _diagnostics_for_risk(
    item: dict[str, Any],
    known_object_ids: set[str],
    known_scoring_item_ids: set[str],
) -> list[str]:
    diagnostics: list[str] = []
    if not isinstance(item.get("risk_id"), str) or not item.get("risk_id").strip():
        diagnostics.append("risk_id")
    if not isinstance(item.get("risk_title"), str) or not item.get("risk_title").strip():
        diagnostics.append("risk_title")
    if not isinstance(item.get("risk_category"), str) or not item.get("risk_category").strip():
        diagnostics.append("risk_category")
    if not isinstance(item.get("risk_level"), str) or item.get("risk_level") not in VALID_RISK_LEVELS:
        diagnostics.append("risk_level")
    if not isinstance(item.get("risk_clue_id"), str) or not item.get("risk_clue_id").strip():
        diagnostics.append("risk_clue_id")
    if not _non_empty_string_list(item.get("linked_engineering_object_ids")):
        diagnostics.append("linked_engineering_object_ids")
    else:
        diagnostics.extend(
            f"unknown_engineering_object_id:{ref}"
            for ref in sorted(set(item["linked_engineering_object_ids"]) - known_object_ids)
        )
    if not _non_empty_string_list(item.get("linked_scoring_item_ids")):
        diagnostics.append("linked_scoring_item_ids")
    else:
        diagnostics.extend(
            f"unknown_scoring_item_id:{ref}"
            for ref in sorted(set(item["linked_scoring_item_ids"]) - known_scoring_item_ids)
        )
    if not _non_empty_string_list(item.get("response_control_points")):
        diagnostics.append("response_control_points")
    if not _non_empty_string_list(item.get("required_evidence")):
        diagnostics.append("required_evidence")
    if not _non_empty_string_list(item.get("qingtian_tags")):
        diagnostics.append("qingtian_tags")
    return diagnostics


def _known_engineering_object_ids(data: dict[str, Any]) -> set[str]:
    engineering_objects = data.get("engineering_object_metadata")
    if not isinstance(engineering_objects, list):
        return set()
    return {
        item.get("object_id")
        for item in engineering_objects
        if isinstance(item, dict) and isinstance(item.get("object_id"), str)
    }


def _sorted_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(item for item in value if isinstance(item, str))


def _binding_summary(binding_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "row_count": len(binding_rows),
        "risk_ids": [row["risk_id"] for row in binding_rows],
        "risk_levels": sorted({row["risk_level"] for row in binding_rows if row.get("risk_level")}),
        "linked_scoring_item_ids": sorted(
            {
                scoring_id
                for row in binding_rows
                for scoring_id in row.get("linked_scoring_item_ids", [])
            }
        ),
        "binding_statuses": sorted({row["binding_status"] for row in binding_rows}),
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
