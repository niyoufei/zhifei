from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from backend.zhifei_autoplan.phase2_business_input_contract import (
    PASS_STATUS as PHASE2A_PASS_STATUS,
    build_phase2a_business_input_contract_snapshot,
)
from backend.zhifei_autoplan.phase2_qingtian_friendly_checklist import (
    PASS_STATUS as PHASE2D_PASS_STATUS,
    build_phase2d_qingtian_friendly_checklist_snapshot,
)
from backend.zhifei_autoplan.phase2_risk_object_binding import (
    PASS_STATUS as PHASE2C_PASS_STATUS,
    build_phase2c_risk_object_binding_snapshot,
)
from backend.zhifei_autoplan.phase2_scoring_response_matrix import (
    PASS_STATUS as PHASE2B_PASS_STATUS,
    build_phase2b_scoring_response_matrix_snapshot,
)


PHASE_ID = "PHASE_2E_FINAL_REVIEW_ISSUE_LIST"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC"
NO_GO_STATUS = "NO-GO_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC"

DEFAULT_FIXTURE_PATH = Path("projects/_demo_phase2_final_review_issue_list/project.json")

REQUIRED_SECTIONS = (
    "project_metadata",
    "tender_metadata",
    "scoring_item_metadata",
    "engineering_object_metadata",
    "risk_clue_metadata",
    "qingtian_checklist_metadata",
    "final_review_issue_metadata",
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
    "final_review_issue_metadata": list,
    "output_intent_metadata": dict,
    "audit_boundary_metadata": dict,
    "qingtian_ai_review_metadata": dict,
    "safety_boundary": dict,
}

REQUIRED_ISSUE_FIELDS = (
    "issue_id",
    "issue_title",
    "issue_category",
    "severity",
    "source_phase",
    "linked_scoring_item_ids",
    "linked_engineering_object_ids",
    "linked_risk_ids",
    "linked_checklist_ids",
    "issue_reason",
    "diagnostic_evidence",
    "recommended_action",
    "responsible_review_role",
    "review_status",
    "blocking_level",
    "formal_writeback_allowed",
    "export_allowed",
    "official_score_claim",
)

ISSUE_FIELDS = (
    "issue_id",
    "issue_title",
    "issue_category",
    "severity",
    "source_phase",
    "linked_scoring_item_ids",
    "linked_engineering_object_ids",
    "linked_risk_ids",
    "linked_checklist_ids",
    "issue_reason",
    "diagnostic_evidence",
    "recommended_action",
    "responsible_review_role",
    "review_status",
    "blocking_level",
    "audit_traceability_id",
    "formal_writeback_allowed",
    "export_allowed",
    "official_score_claim",
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

VALID_SEVERITIES = ("info", "low", "medium", "high", "blocking")
VALID_SOURCE_PHASES = ("P2A", "P2B", "P2C", "P2D", "cross_phase")
VALID_BLOCKING_LEVELS = ("pass", "warning", "blocking")
VALID_REVIEW_STATUSES = ("pass_static", "warning_static", "blocking_static")

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


def build_phase2e_final_review_issue_list_snapshot(
    root: str | Path | None = None,
    *,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and validate the Phase 2E final review issue list without runtime."""

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

    phase2a_snapshot = build_phase2a_business_input_contract_snapshot(
        repo_root,
        fixture_path=rel_fixture,
    )
    phase2b_snapshot = build_phase2b_scoring_response_matrix_snapshot(
        repo_root,
        fixture_path=rel_fixture,
    )
    phase2c_snapshot = build_phase2c_risk_object_binding_snapshot(
        repo_root,
        fixture_path=rel_fixture,
    )
    phase2d_snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(
        repo_root,
        fixture_path=rel_fixture,
    )
    checks = _checks(data, phase2a_snapshot, phase2b_snapshot, phase2c_snapshot, phase2d_snapshot)
    failures.extend(name for name, passed in checks.items() if not passed)
    failures = _dedupe(failures)
    status = PASS_STATUS if not failures else NO_GO_STATUS
    issue_rows = _issue_rows(data)

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
        "phase2a_contract": {
            "status": phase2a_snapshot.get("status"),
            "failures": phase2a_snapshot.get("failures", []),
        },
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
        "phase2d_checklist": {
            "status": phase2d_snapshot.get("status"),
            "failures": phase2d_snapshot.get("failures", []),
            "checklist_ids": (phase2d_snapshot.get("checklist_summary") or {}).get("checklist_ids", []),
        },
        "issue_fields": list(ISSUE_FIELDS),
        "issue_rows": issue_rows,
        "issue_summary": _issue_summary(issue_rows),
        "forbidden_field_scan": _forbidden_field_scan(data),
        "official_score_blocking": _official_score_scan(data),
        "scope": {
            "phase": "Phase 2E",
            "mode": "final_review_issue_list_static_preview_only",
            "preview_only": True,
            "connects_real_qingtian_system": False,
            "generates_official_score": False,
            "formal_writeback_performed": False,
            "export_performed": False,
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
            "PHASE2F_OUTPUT_PRE_INDEX_PLAN_OR_WRITE_GATE"
            if status == PASS_STATUS
            else "repair Phase 2E static final review issue list failures"
        ),
    }


def format_phase2e_final_review_issue_list_report(snapshot: dict[str, Any]) -> str:
    summary = snapshot.get("issue_summary") or {}
    phase2a = snapshot.get("phase2a_contract") or {}
    phase2b = snapshot.get("phase2b_matrix") or {}
    phase2c = snapshot.get("phase2c_binding") or {}
    phase2d = snapshot.get("phase2d_checklist") or {}
    scope = snapshot.get("scope") or {}
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"fixture_path: {(snapshot.get('fixture') or {}).get('path')}",
        f"fixture_exists: {(snapshot.get('fixture') or {}).get('exists')}",
        f"phase2a_contract_status: {phase2a.get('status')}",
        f"phase2b_matrix_status: {phase2b.get('status')}",
        f"phase2c_binding_status: {phase2c.get('status')}",
        f"phase2d_checklist_status: {phase2d.get('status')}",
        f"issue_row_count: {summary.get('row_count')}",
        f"issue_ids: {summary.get('issue_ids')}",
        f"blocking_level_counts: {summary.get('blocking_level_counts')}",
        f"source_phases: {summary.get('source_phases')}",
        f"formal_writeback_performed: {scope.get('formal_writeback_performed')}",
        f"export_performed: {scope.get('export_performed')}",
        f"official_score_generated: {scope.get('generates_official_score')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase2e_final_review_issue_list_json(snapshot: dict[str, Any]) -> str:
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
    phase2a_snapshot: dict[str, Any],
    phase2b_snapshot: dict[str, Any],
    phase2c_snapshot: dict[str, Any],
    phase2d_snapshot: dict[str, Any],
) -> dict[str, bool]:
    if not isinstance(data, dict):
        return {
            "root_is_object": False,
            "required_sections_present": False,
            "required_section_types_valid": False,
            "required_nested_fields_present": False,
            "synthetic_fixture_declared": False,
            "phase2a_contract_pass": False,
            "phase2b_matrix_pass": False,
            "phase2c_binding_pass": False,
            "phase2d_checklist_pass": False,
            "issue_items_present": False,
            "issue_ids_unique": False,
            "issue_levels_cover_pass_warning_blocking": False,
            "severity_values_valid": False,
            "source_phases_valid": False,
            "linked_scoring_items_known": False,
            "linked_engineering_objects_known": False,
            "linked_risks_known": False,
            "linked_checklists_known": False,
            "issue_reason_present": False,
            "diagnostic_evidence_present": False,
            "recommended_action_present": False,
            "review_statuses_valid": False,
            "blocking_levels_valid": False,
            "formal_writeback_allowed_false": False,
            "export_allowed_false": False,
            "official_score_claim_false": False,
            "issue_rows_cover_items": False,
            "issue_rows_have_required_fields": False,
            "no_official_score_like_fields": False,
            "no_real_doc_body_like_fields": False,
            "no_secret_like_fields": False,
            "forbidden_action_flags_false": False,
        }

    issue_items = data.get("final_review_issue_metadata")
    project = data.get("project_metadata") if isinstance(data.get("project_metadata"), dict) else {}
    safety = data.get("safety_boundary") if isinstance(data.get("safety_boundary"), dict) else {}
    forbidden_scan = _forbidden_field_scan(data)
    official_scan = _official_score_scan(data)
    issue_rows = _issue_rows(data)

    return {
        "root_is_object": True,
        "required_sections_present": all(section in data for section in REQUIRED_SECTIONS),
        "required_section_types_valid": all(
            isinstance(data.get(section), expected_type)
            for section, expected_type in REQUIRED_SECTION_TYPES.items()
        ),
        "required_nested_fields_present": _list_items_have_fields(issue_items, REQUIRED_ISSUE_FIELDS),
        "synthetic_fixture_declared": project.get("sanitized_demo") is True
        and project.get("real_business_material") is False,
        "phase2a_contract_pass": phase2a_snapshot.get("status") == PHASE2A_PASS_STATUS,
        "phase2b_matrix_pass": phase2b_snapshot.get("status") == PHASE2B_PASS_STATUS,
        "phase2c_binding_pass": phase2c_snapshot.get("status") == PHASE2C_PASS_STATUS,
        "phase2d_checklist_pass": phase2d_snapshot.get("status") == PHASE2D_PASS_STATUS,
        "issue_items_present": isinstance(issue_items, list) and bool(issue_items),
        "issue_ids_unique": _issue_ids_unique(issue_items),
        "issue_levels_cover_pass_warning_blocking": _issue_levels_cover_pass_warning_blocking(issue_items),
        "severity_values_valid": _issue_enum_values_valid(issue_items, "severity", VALID_SEVERITIES),
        "source_phases_valid": _issue_enum_values_valid(issue_items, "source_phase", VALID_SOURCE_PHASES),
        "linked_scoring_items_known": _linked_scoring_items_known(issue_items, phase2b_snapshot),
        "linked_engineering_objects_known": _linked_engineering_objects_known(data),
        "linked_risks_known": _linked_risks_known(issue_items, phase2c_snapshot),
        "linked_checklists_known": _linked_checklists_known(issue_items, phase2d_snapshot),
        "issue_reason_present": _issue_string_field_present(issue_items, "issue_reason"),
        "diagnostic_evidence_present": _issue_list_field_present(issue_items, "diagnostic_evidence"),
        "recommended_action_present": _issue_string_field_present(issue_items, "recommended_action"),
        "review_statuses_valid": _issue_enum_values_valid(issue_items, "review_status", VALID_REVIEW_STATUSES),
        "blocking_levels_valid": _issue_enum_values_valid(issue_items, "blocking_level", VALID_BLOCKING_LEVELS),
        "formal_writeback_allowed_false": _boolean_field_false(issue_items, "formal_writeback_allowed"),
        "export_allowed_false": _boolean_field_false(issue_items, "export_allowed"),
        "official_score_claim_false": _boolean_field_false(issue_items, "official_score_claim"),
        "issue_rows_cover_items": _issue_rows_cover_items(issue_items, issue_rows),
        "issue_rows_have_required_fields": _issue_rows_have_required_fields(issue_rows),
        "no_official_score_like_fields": not official_scan["official_score_like_paths"],
        "no_real_doc_body_like_fields": not forbidden_scan["real_doc_body_like_paths"],
        "no_secret_like_fields": not forbidden_scan["secret_like_paths"],
        "forbidden_action_flags_false": all(safety.get(flag) is False for flag in REQUIRED_FALSE_FLAGS),
    }


def _list_items_have_fields(value: Any, fields: Iterable[str]) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, dict) and all(field in item for field in fields)
        for item in value
    )


def _issue_ids_unique(issue_items: Any) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    ids = [
        item.get("issue_id")
        for item in issue_items
        if isinstance(item, dict) and isinstance(item.get("issue_id"), str) and item.get("issue_id")
    ]
    return len(ids) == len(issue_items) and len(ids) == len(set(ids))


def _issue_levels_cover_pass_warning_blocking(issue_items: Any) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    levels = {
        item.get("blocking_level")
        for item in issue_items
        if isinstance(item, dict) and isinstance(item.get("blocking_level"), str)
    }
    return set(VALID_BLOCKING_LEVELS).issubset(levels)


def _issue_enum_values_valid(issue_items: Any, field: str, valid_values: Iterable[str]) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    allowed = set(valid_values)
    return all(
        isinstance(item, dict)
        and isinstance(item.get(field), str)
        and item.get(field) in allowed
        for item in issue_items
    )


def _linked_scoring_items_known(issue_items: Any, phase2b_snapshot: dict[str, Any]) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    known_ids = set((phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []))
    if not known_ids:
        return False
    return _linked_ids_known(issue_items, "linked_scoring_item_ids", known_ids)


def _linked_engineering_objects_known(data: dict[str, Any]) -> bool:
    issue_items = data.get("final_review_issue_metadata")
    engineering_objects = data.get("engineering_object_metadata")
    if not isinstance(issue_items, list) or not issue_items:
        return False
    if not isinstance(engineering_objects, list) or not engineering_objects:
        return False
    known_ids = {
        item.get("object_id")
        for item in engineering_objects
        if isinstance(item, dict) and isinstance(item.get("object_id"), str)
    }
    return _linked_ids_known(issue_items, "linked_engineering_object_ids", known_ids)


def _linked_risks_known(issue_items: Any, phase2c_snapshot: dict[str, Any]) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    known_ids = set((phase2c_snapshot.get("binding_summary") or {}).get("risk_ids", []))
    return _linked_ids_known(issue_items, "linked_risk_ids", known_ids)


def _linked_checklists_known(issue_items: Any, phase2d_snapshot: dict[str, Any]) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    known_ids = set((phase2d_snapshot.get("checklist_summary") or {}).get("checklist_ids", []))
    return _linked_ids_known(issue_items, "linked_checklist_ids", known_ids)


def _linked_ids_known(issue_items: Any, field: str, known_ids: set[str]) -> bool:
    for item in issue_items:
        if not isinstance(item, dict):
            return False
        refs = item.get(field)
        if not isinstance(refs, list):
            return False
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            return False
        if any(ref not in known_ids for ref in refs):
            return False
    return True


def _issue_string_field_present(issue_items: Any, field: str) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get(field), str)
        and bool(item[field].strip())
        for item in issue_items
    )


def _issue_list_field_present(issue_items: Any, field: str) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    return all(isinstance(item, dict) and _non_empty_string_list(item.get(field)) for item in issue_items)


def _boolean_field_false(issue_items: Any, field: str) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    return all(isinstance(item, dict) and item.get(field) is False for item in issue_items)


def _issue_rows_cover_items(issue_items: Any, issue_rows: list[dict[str, Any]]) -> bool:
    if not isinstance(issue_items, list) or not issue_items:
        return False
    expected_ids = sorted(
        item.get("issue_id")
        for item in issue_items
        if isinstance(item, dict) and isinstance(item.get("issue_id"), str) and item.get("issue_id")
    )
    row_ids = sorted(row.get("issue_id") for row in issue_rows)
    return len(expected_ids) == len(issue_items) and row_ids == expected_ids


def _issue_rows_have_required_fields(issue_rows: list[dict[str, Any]]) -> bool:
    return bool(issue_rows) and all(all(field in row for field in ISSUE_FIELDS) for row in issue_rows)


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip()) for item in value
    )


def _issue_rows(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict) or not isinstance(data.get("final_review_issue_metadata"), list):
        return []
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(data["final_review_issue_metadata"]):
        if not isinstance(item, dict):
            continue
        issue_id = item.get("issue_id") if isinstance(item.get("issue_id"), str) else f"issue-{index:03d}"
        rows.append(
            {
                "issue_id": issue_id,
                "issue_title": item.get("issue_title") if isinstance(item.get("issue_title"), str) else "",
                "issue_category": (
                    item.get("issue_category") if isinstance(item.get("issue_category"), str) else ""
                ),
                "severity": item.get("severity") if isinstance(item.get("severity"), str) else "",
                "source_phase": item.get("source_phase") if isinstance(item.get("source_phase"), str) else "",
                "linked_scoring_item_ids": _sorted_string_list(item.get("linked_scoring_item_ids")),
                "linked_engineering_object_ids": _sorted_string_list(item.get("linked_engineering_object_ids")),
                "linked_risk_ids": _sorted_string_list(item.get("linked_risk_ids")),
                "linked_checklist_ids": _sorted_string_list(item.get("linked_checklist_ids")),
                "issue_reason": item.get("issue_reason") if isinstance(item.get("issue_reason"), str) else "",
                "diagnostic_evidence": _sorted_string_list(item.get("diagnostic_evidence")),
                "recommended_action": (
                    item.get("recommended_action") if isinstance(item.get("recommended_action"), str) else ""
                ),
                "responsible_review_role": (
                    item.get("responsible_review_role")
                    if isinstance(item.get("responsible_review_role"), str)
                    else ""
                ),
                "review_status": (
                    item.get("review_status") if isinstance(item.get("review_status"), str) else ""
                ),
                "blocking_level": (
                    item.get("blocking_level") if isinstance(item.get("blocking_level"), str) else ""
                ),
                "audit_traceability_id": f"phase2e:{issue_id}",
                "formal_writeback_allowed": item.get("formal_writeback_allowed"),
                "export_allowed": item.get("export_allowed"),
                "official_score_claim": item.get("official_score_claim"),
            }
        )
    return sorted(rows, key=lambda row: row["issue_id"])


def _sorted_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(item for item in value if isinstance(item, str))


def _issue_summary(issue_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "row_count": len(issue_rows),
        "issue_ids": [row["issue_id"] for row in issue_rows],
        "source_phases": sorted({row["source_phase"] for row in issue_rows if row.get("source_phase")}),
        "severity_counts": _counts(issue_rows, "severity", VALID_SEVERITIES),
        "blocking_level_counts": _counts(issue_rows, "blocking_level", VALID_BLOCKING_LEVELS),
        "review_status_counts": _counts(issue_rows, "review_status", VALID_REVIEW_STATUSES),
        "linked_scoring_item_ids": sorted(
            {
                scoring_id
                for row in issue_rows
                for scoring_id in row.get("linked_scoring_item_ids", [])
            }
        ),
        "linked_engineering_object_ids": sorted(
            {
                object_id
                for row in issue_rows
                for object_id in row.get("linked_engineering_object_ids", [])
            }
        ),
        "linked_risk_ids": sorted(
            {
                risk_id
                for row in issue_rows
                for risk_id in row.get("linked_risk_ids", [])
            }
        ),
        "linked_checklist_ids": sorted(
            {
                checklist_id
                for row in issue_rows
                for checklist_id in row.get("linked_checklist_ids", [])
            }
        ),
        "formal_writeback_allowed_values": _sorted_unique_values(
            row.get("formal_writeback_allowed") for row in issue_rows
        ),
        "export_allowed_values": _sorted_unique_values(row.get("export_allowed") for row in issue_rows),
        "official_score_claim_values": _sorted_unique_values(
            row.get("official_score_claim") for row in issue_rows
        ),
    }


def _counts(rows: list[dict[str, Any]], field: str, ordered_values: Iterable[str]) -> dict[str, int]:
    return {
        value: sum(1 for row in rows if row.get(field) == value)
        for value in ordered_values
        if any(row.get(field) == value for row in rows)
    }


def _sorted_unique_values(values: Iterable[Any]) -> list[Any]:
    return sorted({value for value in values}, key=lambda item: str(item))


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
