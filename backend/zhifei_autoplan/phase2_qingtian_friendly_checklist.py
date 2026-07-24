from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from backend.zhifei_autoplan.phase2_risk_object_binding import (
    PASS_STATUS as PHASE2C_PASS_STATUS,
    build_phase2c_risk_object_binding_snapshot,
)
from backend.zhifei_autoplan.phase2_scoring_response_matrix import (
    PASS_STATUS as PHASE2B_PASS_STATUS,
    build_phase2b_scoring_response_matrix_snapshot,
)


PHASE_ID = "PHASE_2D_QINGTIAN_FRIENDLY_CHECKLIST"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC"
NO_GO_STATUS = "NO-GO_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC"

DEFAULT_FIXTURE_PATH = Path("projects/_demo_phase2_qingtian_friendly_checklist/project.json")

REQUIRED_SECTIONS = (
    "project_metadata",
    "tender_metadata",
    "scoring_item_metadata",
    "engineering_object_metadata",
    "risk_clue_metadata",
    "qingtian_checklist_metadata",
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
    "qingtian_checklist_metadata": list,
    "output_intent_metadata": dict,
    "audit_boundary_metadata": dict,
    "qingtian_ai_review_metadata": dict,
    "safety_boundary": dict,
}

REQUIRED_CHECKLIST_FIELDS = (
    "checklist_id",
    "checklist_title",
    "checklist_category",
    "linked_scoring_item_ids",
    "linked_engineering_object_ids",
    "linked_risk_ids",
    "qingtian_keywords",
    "qingtian_parse_tags",
    "evidence_requirements",
    "traceability_requirements",
    "diagnosable_failure_reason",
    "severity",
    "affects_score",
    "official_score_claim",
)

CHECKLIST_FIELDS = (
    "checklist_id",
    "checklist_title",
    "checklist_category",
    "linked_scoring_item_ids",
    "linked_engineering_object_ids",
    "linked_risk_ids",
    "qingtian_keywords",
    "qingtian_parse_tags",
    "evidence_requirements",
    "traceability_requirements",
    "diagnosable_failure_reason",
    "severity",
    "affects_score",
    "official_score_claim",
    "checklist_status",
    "audit_traceability_id",
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

OFFICIAL_SCORE_MARKERS = (
    "official_evaluation_score",
    "official_score",
    "real_qingtian_score",
    "qingtian_score",
    "official_scoring_result",
    "formal_evaluation_score",
)

OFFICIAL_SCORE_ALLOWED_KEYS = {"official_score_claim"}


def build_phase2d_qingtian_friendly_checklist_snapshot(
    root: str | Path | None = None,
    *,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and validate the Phase 2D Qingtian-friendly checklist without runtime."""

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
    phase2c_snapshot = build_phase2c_risk_object_binding_snapshot(
        repo_root,
        fixture_path=rel_fixture,
    )
    checks = _checks(data, phase2b_snapshot, phase2c_snapshot)
    failures.extend(name for name, passed in checks.items() if not passed)
    failures = _dedupe(failures)
    status = PASS_STATUS if not failures else NO_GO_STATUS
    checklist_rows = _checklist_rows(data, phase2b_snapshot, phase2c_snapshot)

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
        "phase2c_binding": {
            "status": phase2c_snapshot.get("status"),
            "failures": phase2c_snapshot.get("failures", []),
            "risk_ids": (phase2c_snapshot.get("binding_summary") or {}).get("risk_ids", []),
        },
        "checklist_fields": list(CHECKLIST_FIELDS),
        "checklist_rows": checklist_rows,
        "checklist_summary": _checklist_summary(checklist_rows),
        "forbidden_field_scan": _forbidden_field_scan(data),
        "official_score_blocking": _official_score_scan(data),
        "scope": {
            "phase": "Phase 2D",
            "mode": "qingtian_friendly_checklist_static_preview_only",
            "preview_only": True,
            "connects_real_qingtian_system": False,
            "generates_official_score": False,
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
            "PHASE2E_FINAL_REVIEW_ISSUE_LIST_PLAN_OR_WRITE_GATE"
            if status == PASS_STATUS
            else "repair Phase 2D static Qingtian-friendly checklist failures"
        ),
    }


def format_phase2d_qingtian_friendly_checklist_report(snapshot: dict[str, Any]) -> str:
    summary = snapshot.get("checklist_summary") or {}
    phase2b = snapshot.get("phase2b_matrix") or {}
    phase2c = snapshot.get("phase2c_binding") or {}
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"fixture_path: {(snapshot.get('fixture') or {}).get('path')}",
        f"fixture_exists: {(snapshot.get('fixture') or {}).get('exists')}",
        f"phase2b_matrix_status: {phase2b.get('status')}",
        f"phase2c_binding_status: {phase2c.get('status')}",
        f"checklist_row_count: {summary.get('row_count')}",
        f"checklist_ids: {summary.get('checklist_ids')}",
        f"covered_scoring_item_ids: {summary.get('covered_scoring_item_ids')}",
        f"score_generation_performed: {(snapshot.get('scope') or {}).get('generates_official_score')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase2d_qingtian_friendly_checklist_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "data": None}
    try:
        return {"exists": True, "data": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"exists": True, "data": None, "error": str(exc)}


def _checks(
    data: Any,
    phase2b_snapshot: dict[str, Any],
    phase2c_snapshot: dict[str, Any],
) -> dict[str, bool]:
    if not isinstance(data, dict):
        return {
            "root_is_object": False,
            "required_sections_present": False,
            "required_section_types_valid": False,
            "required_nested_fields_present": False,
            "synthetic_fixture_declared": False,
            "phase2b_matrix_pass": False,
            "phase2c_binding_pass": False,
            "checklist_items_present": False,
            "checklist_ids_unique": False,
            "checklist_covers_scoring_items": False,
            "qingtian_keywords_present": False,
            "qingtian_parse_tags_present": False,
            "linked_scoring_items_known": False,
            "linked_engineering_objects_known": False,
            "linked_risks_known": False,
            "evidence_requirements_present": False,
            "traceability_requirements_present": False,
            "affects_score_false": False,
            "official_score_claim_false": False,
            "no_official_score_like_fields": False,
            "checklist_rows_cover_items": False,
            "checklist_rows_have_required_fields": False,
            "no_real_doc_body_like_fields": False,
            "no_secret_like_fields": False,
            "forbidden_action_flags_false": False,
        }

    checklist_items = data.get("qingtian_checklist_metadata")
    project = data.get("project_metadata") if isinstance(data.get("project_metadata"), dict) else {}
    safety = data.get("safety_boundary") if isinstance(data.get("safety_boundary"), dict) else {}
    forbidden_scan = _forbidden_field_scan(data)
    official_scan = _official_score_scan(data)
    checklist_rows = _checklist_rows(data, phase2b_snapshot, phase2c_snapshot)

    return {
        "root_is_object": True,
        "required_sections_present": all(section in data for section in REQUIRED_SECTIONS),
        "required_section_types_valid": all(
            isinstance(data.get(section), expected_type)
            for section, expected_type in REQUIRED_SECTION_TYPES.items()
        ),
        "required_nested_fields_present": _list_items_have_fields(checklist_items, REQUIRED_CHECKLIST_FIELDS),
        "synthetic_fixture_declared": project.get("sanitized_demo") is True
        and project.get("real_business_material") is False,
        "phase2b_matrix_pass": phase2b_snapshot.get("status") == PHASE2B_PASS_STATUS,
        "phase2c_binding_pass": phase2c_snapshot.get("status") == PHASE2C_PASS_STATUS,
        "checklist_items_present": isinstance(checklist_items, list) and bool(checklist_items),
        "checklist_ids_unique": _checklist_ids_unique(checklist_items),
        "checklist_covers_scoring_items": _checklist_covers_scoring_items(checklist_items, phase2b_snapshot),
        "qingtian_keywords_present": _checklist_list_field_present(checklist_items, "qingtian_keywords"),
        "qingtian_parse_tags_present": _checklist_list_field_present(checklist_items, "qingtian_parse_tags"),
        "linked_scoring_items_known": _linked_scoring_items_known(checklist_items, phase2b_snapshot),
        "linked_engineering_objects_known": _linked_engineering_objects_known(data),
        "linked_risks_known": _linked_risks_known(checklist_items, phase2c_snapshot),
        "evidence_requirements_present": _checklist_list_field_present(checklist_items, "evidence_requirements"),
        "traceability_requirements_present": _checklist_list_field_present(
            checklist_items, "traceability_requirements"
        ),
        "affects_score_false": _boolean_field_false(checklist_items, "affects_score"),
        "official_score_claim_false": _boolean_field_false(checklist_items, "official_score_claim"),
        "no_official_score_like_fields": not official_scan["official_score_like_paths"],
        "checklist_rows_cover_items": _checklist_rows_cover_items(checklist_items, checklist_rows),
        "checklist_rows_have_required_fields": _checklist_rows_have_required_fields(checklist_rows),
        "no_real_doc_body_like_fields": not forbidden_scan["real_doc_body_like_paths"],
        "no_secret_like_fields": not forbidden_scan["secret_like_paths"],
        "forbidden_action_flags_false": all(safety.get(flag) is False for flag in REQUIRED_FALSE_FLAGS),
    }


def _list_items_have_fields(value: Any, fields: Iterable[str]) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict) and all(field in item for field in fields)
        for item in value
    )


def _checklist_ids_unique(checklist_items: Any) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    ids = [
        item.get("checklist_id")
        for item in checklist_items
        if isinstance(item, dict)
        and isinstance(item.get("checklist_id"), str)
        and item.get("checklist_id")
    ]
    return len(ids) == len(checklist_items) and len(ids) == len(set(ids))


def _checklist_covers_scoring_items(checklist_items: Any, phase2b_snapshot: dict[str, Any]) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    expected_ids = set((phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []))
    if not expected_ids:
        return False
    covered_ids = {
        scoring_id
        for item in checklist_items
        if isinstance(item, dict) and isinstance(item.get("linked_scoring_item_ids"), list)
        for scoring_id in item["linked_scoring_item_ids"]
        if isinstance(scoring_id, str)
    }
    return expected_ids.issubset(covered_ids)


def _checklist_list_field_present(checklist_items: Any, field: str) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    return all(isinstance(item, dict) and _non_empty_string_list(item.get(field)) for item in checklist_items)


def _linked_scoring_items_known(checklist_items: Any, phase2b_snapshot: dict[str, Any]) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    known_ids = set((phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []))
    if not known_ids:
        return False
    for item in checklist_items:
        if not isinstance(item, dict):
            return False
        refs = item.get("linked_scoring_item_ids")
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _linked_engineering_objects_known(data: dict[str, Any]) -> bool:
    checklist_items = data.get("qingtian_checklist_metadata")
    engineering_objects = data.get("engineering_object_metadata")
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    if not isinstance(engineering_objects, list) or not engineering_objects:
        return False
    known_ids = {
        item.get("object_id")
        for item in engineering_objects
        if isinstance(item, dict) and isinstance(item.get("object_id"), str)
    }
    for item in checklist_items:
        if not isinstance(item, dict):
            return False
        refs = item.get("linked_engineering_object_ids")
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _linked_risks_known(checklist_items: Any, phase2c_snapshot: dict[str, Any]) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    known_ids = set((phase2c_snapshot.get("binding_summary") or {}).get("risk_ids", []))
    for item in checklist_items:
        if not isinstance(item, dict):
            return False
        refs = item.get("linked_risk_ids")
        if refs in (None, []):
            continue
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _boolean_field_false(checklist_items: Any, field: str) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    return all(isinstance(item, dict) and item.get(field) is False for item in checklist_items)


def _checklist_rows_cover_items(checklist_items: Any, checklist_rows: list[dict[str, Any]]) -> bool:
    if not isinstance(checklist_items, list) or not checklist_items:
        return False
    expected_ids = sorted(
        item.get("checklist_id")
        for item in checklist_items
        if isinstance(item, dict) and isinstance(item.get("checklist_id"), str) and item.get("checklist_id")
    )
    row_ids = sorted(row.get("checklist_id") for row in checklist_rows)
    return len(expected_ids) == len(checklist_items) and row_ids == expected_ids


def _checklist_rows_have_required_fields(checklist_rows: list[dict[str, Any]]) -> bool:
    return bool(checklist_rows) and all(all(field in row for field in CHECKLIST_FIELDS) for row in checklist_rows)


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _checklist_rows(
    data: Any,
    phase2b_snapshot: dict[str, Any],
    phase2c_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get("qingtian_checklist_metadata"), list):
        return []
    known_object_ids = _known_engineering_object_ids(data)
    known_scoring_item_ids = set((phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []))
    known_risk_ids = set((phase2c_snapshot.get("binding_summary") or {}).get("risk_ids", []))

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(data["qingtian_checklist_metadata"]):
        if not isinstance(item, dict):
            continue
        checklist_id = (
            item.get("checklist_id") if isinstance(item.get("checklist_id"), str) else f"checklist-{index:03d}"
        )
        diagnostics = _diagnostics_for_checklist(item, known_object_ids, known_scoring_item_ids, known_risk_ids)
        rows.append(
            {
                "checklist_id": checklist_id,
                "checklist_title": (
                    item.get("checklist_title") if isinstance(item.get("checklist_title"), str) else ""
                ),
                "checklist_category": (
                    item.get("checklist_category") if isinstance(item.get("checklist_category"), str) else ""
                ),
                "linked_scoring_item_ids": _sorted_string_list(item.get("linked_scoring_item_ids")),
                "linked_engineering_object_ids": _sorted_string_list(item.get("linked_engineering_object_ids")),
                "linked_risk_ids": _sorted_string_list(item.get("linked_risk_ids")),
                "qingtian_keywords": _sorted_string_list(item.get("qingtian_keywords")),
                "qingtian_parse_tags": _sorted_string_list(item.get("qingtian_parse_tags")),
                "evidence_requirements": _sorted_string_list(item.get("evidence_requirements")),
                "traceability_requirements": _sorted_string_list(item.get("traceability_requirements")),
                "diagnosable_failure_reason": (
                    item.get("diagnosable_failure_reason")
                    if isinstance(item.get("diagnosable_failure_reason"), str)
                    else ""
                ),
                "severity": item.get("severity") if isinstance(item.get("severity"), str) else "",
                "affects_score": item.get("affects_score"),
                "official_score_claim": item.get("official_score_claim"),
                "checklist_status": "ready_static" if not diagnostics else "no_go_static",
                "audit_traceability_id": f"phase2d:{checklist_id}",
            }
        )
    return sorted(rows, key=lambda row: row["checklist_id"])


def _diagnostics_for_checklist(
    item: dict[str, Any],
    known_object_ids: set[str],
    known_scoring_item_ids: set[str],
    known_risk_ids: set[str],
) -> list[str]:
    diagnostics: list[str] = []
    if not isinstance(item.get("checklist_id"), str) or not item.get("checklist_id").strip():
        diagnostics.append("checklist_id")
    if not isinstance(item.get("checklist_title"), str) or not item.get("checklist_title").strip():
        diagnostics.append("checklist_title")
    if not isinstance(item.get("checklist_category"), str) or not item.get("checklist_category").strip():
        diagnostics.append("checklist_category")
    if not _non_empty_string_list(item.get("linked_scoring_item_ids")):
        diagnostics.append("linked_scoring_item_ids")
    else:
        diagnostics.extend(
            f"unknown_scoring_item_id:{ref}"
            for ref in sorted(set(item["linked_scoring_item_ids"]) - known_scoring_item_ids)
        )
    if not _non_empty_string_list(item.get("linked_engineering_object_ids")):
        diagnostics.append("linked_engineering_object_ids")
    else:
        diagnostics.extend(
            f"unknown_engineering_object_id:{ref}"
            for ref in sorted(set(item["linked_engineering_object_ids"]) - known_object_ids)
        )
    linked_risk_ids = item.get("linked_risk_ids")
    if linked_risk_ids not in (None, []):
        if not _non_empty_string_list(linked_risk_ids):
            diagnostics.append("linked_risk_ids")
        else:
            diagnostics.extend(
                f"unknown_risk_id:{ref}" for ref in sorted(set(linked_risk_ids) - known_risk_ids)
            )
    if not _non_empty_string_list(item.get("qingtian_keywords")):
        diagnostics.append("qingtian_keywords")
    if not _non_empty_string_list(item.get("qingtian_parse_tags")):
        diagnostics.append("qingtian_parse_tags")
    if not _non_empty_string_list(item.get("evidence_requirements")):
        diagnostics.append("evidence_requirements")
    if not _non_empty_string_list(item.get("traceability_requirements")):
        diagnostics.append("traceability_requirements")
    if not isinstance(item.get("diagnosable_failure_reason"), str) or not item.get(
        "diagnosable_failure_reason"
    ).strip():
        diagnostics.append("diagnosable_failure_reason")
    if not isinstance(item.get("severity"), str) or not item.get("severity").strip():
        diagnostics.append("severity")
    if item.get("affects_score") is not False:
        diagnostics.append("affects_score")
    if item.get("official_score_claim") is not False:
        diagnostics.append("official_score_claim")
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


def _checklist_summary(checklist_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "row_count": len(checklist_rows),
        "checklist_ids": [row["checklist_id"] for row in checklist_rows],
        "covered_scoring_item_ids": sorted(
            {
                scoring_id
                for row in checklist_rows
                for scoring_id in row.get("linked_scoring_item_ids", [])
            }
        ),
        "linked_risk_ids": sorted(
            {
                risk_id
                for row in checklist_rows
                for risk_id in row.get("linked_risk_ids", [])
            }
        ),
        "checklist_statuses": sorted({row["checklist_status"] for row in checklist_rows}),
        "affects_score_values": sorted({row["affects_score"] for row in checklist_rows}),
        "official_score_claim_values": sorted({row["official_score_claim"] for row in checklist_rows}),
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


def _official_score_scan(data: Any) -> dict[str, list[str]]:
    official_score_like_paths: list[str] = []
    for path, value in _walk(data):
        lowered = path.lower()
        key = path.rsplit(".", 1)[-1].lower()
        if key in OFFICIAL_SCORE_ALLOWED_KEYS:
            continue
        if key in OFFICIAL_SCORE_MARKERS or any(marker in lowered for marker in OFFICIAL_SCORE_MARKERS):
            official_score_like_paths.append(path)
        if isinstance(value, str):
            lowered_value = value.lower()
            if any(marker.replace("_", " ") in lowered_value for marker in OFFICIAL_SCORE_MARKERS):
                official_score_like_paths.append(path)
    return {"official_score_like_paths": _dedupe(official_score_like_paths)}


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
