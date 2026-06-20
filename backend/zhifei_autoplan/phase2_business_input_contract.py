from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


PHASE_ID = "PHASE_2A_BUSINESS_INPUT_CONTRACT"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC"
NO_GO_STATUS = "NO-GO_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC"

DEFAULT_FIXTURE_PATH = Path("projects/_demo_phase2_business_input/project.json")

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

REQUIRED_PROJECT_FIELDS = (
    "project_id",
    "project_name",
    "project_type",
    "location",
    "sanitized_demo",
    "real_business_material",
)

REQUIRED_TENDER_FIELDS = (
    "tender_doc_ref",
    "tender_doc_version",
    "evaluation_method",
    "source_kind",
)

REQUIRED_SCORING_FIELDS = (
    "item_id",
    "item_name",
    "max_score",
    "requirement_summary",
    "evidence_needed",
    "related_engineering_object_ids",
)

REQUIRED_ENGINEERING_OBJECT_FIELDS = (
    "object_id",
    "object_type",
    "object_name",
    "synthetic_scope_summary",
)

REQUIRED_RISK_CLUE_FIELDS = (
    "risk_id",
    "risk_type",
    "risk_hint",
    "related_engineering_object_ids",
    "expected_response_mode",
)

REQUIRED_OUTPUT_INTENT_FIELDS = (
    "intended_outputs",
    "export_requested",
    "formal_writeback_requested",
)

REQUIRED_AUDIT_FIELDS = (
    "snapshot_id",
    "schema_version",
    "input_hash_mode",
    "requires_human_review",
)

REQUIRED_QINGTIAN_FIELDS = (
    "evaluation_friendly",
    "scoring_clause_refs_required",
    "evidence_anchor_required",
    "preview_advisory_not_evidence",
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


def build_phase2a_business_input_contract_snapshot(
    root: str | Path | None = None,
    *,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate the Phase 2A synthetic business input contract without runtime."""

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
        "contract_sections": _contract_sections(data),
        "forbidden_field_scan": _forbidden_field_scan(data),
        "scope": {
            "phase": "Phase 2A",
            "mode": "business_input_contract_static",
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
            "PHASE2B_SCORING_RESPONSE_MATRIX_PLAN_OR_WRITE_GATE"
            if status == PASS_STATUS
            else "repair Phase 2A static contract failures"
        ),
    }


def format_phase2a_business_input_contract_report(snapshot: dict[str, Any]) -> str:
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"fixture_path: {(snapshot.get('fixture') or {}).get('path')}",
        f"fixture_exists: {(snapshot.get('fixture') or {}).get('exists')}",
        f"contract_sections: {snapshot.get('contract_sections')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase2a_business_input_contract_json(snapshot: dict[str, Any]) -> str:
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
            "no_real_doc_body_like_fields": False,
            "no_secret_like_fields": False,
            "forbidden_action_flags_false": False,
            "qingtian_fields_present": False,
        }

    required_sections_present = all(section in data for section in REQUIRED_SECTIONS)
    required_section_types_valid = all(
        isinstance(data.get(section), expected_type)
        for section, expected_type in REQUIRED_SECTION_TYPES.items()
    )
    nested_fields_present = _required_nested_fields_present(data)
    project = data.get("project_metadata") if isinstance(data.get("project_metadata"), dict) else {}
    forbidden_scan = _forbidden_field_scan(data)
    safety = data.get("safety_boundary") if isinstance(data.get("safety_boundary"), dict) else {}
    qingtian = (
        data.get("qingtian_ai_review_metadata")
        if isinstance(data.get("qingtian_ai_review_metadata"), dict)
        else {}
    )

    return {
        "root_is_object": True,
        "required_sections_present": required_sections_present,
        "required_section_types_valid": required_section_types_valid,
        "required_nested_fields_present": nested_fields_present,
        "synthetic_fixture_declared": project.get("sanitized_demo") is True
        and project.get("real_business_material") is False,
        "no_real_doc_body_like_fields": not forbidden_scan["real_doc_body_like_paths"],
        "no_secret_like_fields": not forbidden_scan["secret_like_paths"],
        "forbidden_action_flags_false": all(safety.get(flag) is False for flag in REQUIRED_FALSE_FLAGS),
        "qingtian_fields_present": all(field in qingtian for field in REQUIRED_QINGTIAN_FIELDS),
    }


def _required_nested_fields_present(data: dict[str, Any]) -> bool:
    return (
        _has_fields(data.get("project_metadata"), REQUIRED_PROJECT_FIELDS)
        and _has_fields(data.get("tender_metadata"), REQUIRED_TENDER_FIELDS)
        and _list_items_have_fields(data.get("scoring_item_metadata"), REQUIRED_SCORING_FIELDS)
        and _list_items_have_fields(data.get("engineering_object_metadata"), REQUIRED_ENGINEERING_OBJECT_FIELDS)
        and _list_items_have_fields(data.get("risk_clue_metadata"), REQUIRED_RISK_CLUE_FIELDS)
        and _has_fields(data.get("output_intent_metadata"), REQUIRED_OUTPUT_INTENT_FIELDS)
        and _has_fields(data.get("audit_boundary_metadata"), REQUIRED_AUDIT_FIELDS)
    )


def _has_fields(value: Any, fields: Iterable[str]) -> bool:
    return isinstance(value, dict) and all(field in value for field in fields)


def _list_items_have_fields(value: Any, fields: Iterable[str]) -> bool:
    return isinstance(value, list) and bool(value) and all(_has_fields(item, fields) for item in value)


def _contract_sections(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return []
    return [section for section in REQUIRED_SECTIONS if section in data]


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
