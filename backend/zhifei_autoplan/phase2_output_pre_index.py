from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Iterable

from backend.zhifei_autoplan.phase2_business_input_contract import (
    PASS_STATUS as PHASE2A_PASS_STATUS,
    build_phase2a_business_input_contract_snapshot,
)
from backend.zhifei_autoplan.phase2_final_review_issue_list import (
    PASS_STATUS as PHASE2E_PASS_STATUS,
    build_phase2e_final_review_issue_list_snapshot,
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


PHASE_ID = "PHASE_2F_OUTPUT_PRE_INDEX"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE2F_OUTPUT_PRE_INDEX_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE2F_OUTPUT_PRE_INDEX_STATIC"
NO_GO_STATUS = "NO-GO_PHASE2F_OUTPUT_PRE_INDEX_STATIC"

DEFAULT_FIXTURE_PATH = Path("projects/_demo_phase2_output_pre_index/project.json")

OUTPUT_PRE_INDEX_SECTION = "output_pre_index_metadata"
OUTPUT_ENTRY_FIELDS = (
    "output_id",
    "output_type",
    "title",
    "source_phase",
    "source_inputs",
    "intended_consumer",
    "allowed_format_descriptor",
    "export_status",
    "writeback_status",
    "official_score_status",
    "artifact_generation_status",
    "data_boundary",
    "trace_links",
    "blocker_reason",
)

OUTPUT_TYPES = (
    "final_review_report",
    "scoring_matrix",
    "issue_list",
    "audit_index",
    "delivery_package_index",
    "handoff_summary",
    "evidence_trace_index",
)

VALID_SOURCE_PHASES = ("P2A", "P2B", "P2C", "P2D", "P2E", "cross_phase")
VALID_EXPORT_STATUSES = ("blocked", "preview_only")
BLOCKED_OR_PREVIEW_STATUSES = ("blocked", "preview_only")
FORBIDDEN_GENERATED_STATUSES = ("generated", "performed", "materialized", "exported", "written")

REQUIRED_FALSE_BOUNDARY_FLAGS = (
    "held_config_body_read",
    "real_business_doc_body_read",
    "secret_read",
    "runtime_started",
    "endpoint_accessed",
)

REQUIRED_FALSE_SAFETY_FLAGS = (
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

BLOCKING_RULES = (
    "export_blocked",
    "file_artifact_generation_blocked",
    "formal_writeback_blocked",
    "official_score_blocked",
    "real_business_document_body_blocked",
    "held_config_body_blocked",
    "runtime_endpoint_blocked",
    "secret_blocked",
)


def build_phase2f_output_pre_index_snapshot(
    root: str | Path | None = None,
    *,
    fixture_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build and validate the Phase 2F output pre-index without runtime or artifacts."""

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

    with _upstream_fixture_view(data, rel_fixture) as upstream_fixture:
        phase2a_snapshot = build_phase2a_business_input_contract_snapshot(
            repo_root,
            fixture_path=upstream_fixture,
        )
        phase2b_snapshot = build_phase2b_scoring_response_matrix_snapshot(
            repo_root,
            fixture_path=upstream_fixture,
        )
        phase2c_snapshot = build_phase2c_risk_object_binding_snapshot(
            repo_root,
            fixture_path=upstream_fixture,
        )
        phase2d_snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(
            repo_root,
            fixture_path=upstream_fixture,
        )
        phase2e_snapshot = build_phase2e_final_review_issue_list_snapshot(
            repo_root,
            fixture_path=upstream_fixture,
        )

        trace_catalog = _trace_catalog(data, phase2b_snapshot, phase2c_snapshot, phase2d_snapshot, phase2e_snapshot)
        validation_errors = _validation_errors(data, trace_catalog)
        checks = _checks(
            data,
            phase2a_snapshot,
            phase2b_snapshot,
            phase2c_snapshot,
            phase2d_snapshot,
            phase2e_snapshot,
            trace_catalog,
            validation_errors,
        )
    failures.extend(name for name, passed in checks.items() if not passed)
    failures = _dedupe(failures)
    status = PASS_STATUS if not failures else NO_GO_STATUS
    output_entries = _output_entries(data)

    return {
        "status": status,
        "phase_id": PHASE_ID,
        "failures": failures,
        "validation_errors": validation_errors,
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
        "phase2e_issue_list": {
            "status": phase2e_snapshot.get("status"),
            "failures": phase2e_snapshot.get("failures", []),
            "issue_ids": (phase2e_snapshot.get("issue_summary") or {}).get("issue_ids", []),
        },
        "output_entry_fields": list(OUTPUT_ENTRY_FIELDS),
        "output_type_enum": list(OUTPUT_TYPES),
        "blocking_rules": list(BLOCKING_RULES),
        "trace_catalog": sorted(trace_catalog),
        "output_entries": output_entries,
        "output_summary": _output_summary(output_entries),
        "forbidden_field_scan": _forbidden_field_scan(data),
        "scope": {
            "phase": "Phase 2F",
            "mode": "output_pre_index_static_preview_only",
            "preview_only": True,
            "connects_real_qingtian_system": False,
            "export_performed": False,
            "artifact_generation_performed": False,
            "formal_writeback_performed": False,
            "official_score_generated": False,
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
            "PHASE2_CLOSEOUT_READONLY_PLAN_OR_GATE"
            if status == PASS_STATUS
            else "repair Phase 2F static output pre-index failures"
        ),
    }


def format_phase2f_output_pre_index_report(snapshot: dict[str, Any]) -> str:
    summary = snapshot.get("output_summary") or {}
    phase2a = snapshot.get("phase2a_contract") or {}
    phase2b = snapshot.get("phase2b_matrix") or {}
    phase2c = snapshot.get("phase2c_binding") or {}
    phase2d = snapshot.get("phase2d_checklist") or {}
    phase2e = snapshot.get("phase2e_issue_list") or {}
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
        f"phase2e_issue_list_status: {phase2e.get('status')}",
        f"output_entry_count: {summary.get('row_count')}",
        f"output_ids: {summary.get('output_ids')}",
        f"output_type_counts: {summary.get('output_type_counts')}",
        f"export_status_counts: {summary.get('export_status_counts')}",
        f"artifact_generation_performed: {scope.get('artifact_generation_performed')}",
        f"formal_writeback_performed: {scope.get('formal_writeback_performed')}",
        f"export_performed: {scope.get('export_performed')}",
        f"official_score_generated: {scope.get('official_score_generated')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"blocking_rules: {snapshot.get('blocking_rules')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    validation_errors = snapshot.get("validation_errors") or []
    if validation_errors:
        lines.append("validation_errors:")
        lines.extend(f"- {item}" for item in validation_errors)
    return "\n".join(lines)


def dump_phase2f_output_pre_index_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "data": None}
    try:
        return {"exists": True, "data": json.loads(path.read_text(encoding="utf-8"))}
    except Exception as exc:
        return {"exists": True, "data": None, "error": str(exc)}


class _upstream_fixture_view:
    def __init__(self, data: Any, fallback_fixture: Path) -> None:
        self._data = data
        self._fallback_fixture = fallback_fixture
        self._tmpdir: tempfile.TemporaryDirectory[str] | None = None
        self._path: Path | None = None

    def __enter__(self) -> Path:
        if not isinstance(self._data, dict):
            return self._fallback_fixture
        upstream_data = dict(self._data)
        upstream_data.pop(OUTPUT_PRE_INDEX_SECTION, None)
        self._tmpdir = tempfile.TemporaryDirectory()
        self._path = Path(self._tmpdir.name) / "phase2f_upstream_fixture.json"
        self._path.write_text(json.dumps(upstream_data, ensure_ascii=False), encoding="utf-8")
        return self._path

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()


def _checks(
    data: Any,
    phase2a_snapshot: dict[str, Any],
    phase2b_snapshot: dict[str, Any],
    phase2c_snapshot: dict[str, Any],
    phase2d_snapshot: dict[str, Any],
    phase2e_snapshot: dict[str, Any],
    trace_catalog: set[str],
    validation_errors: list[str],
) -> dict[str, bool]:
    if not isinstance(data, dict):
        return {
            "root_is_object": False,
            "output_pre_index_section_present": False,
            "output_entries_present": False,
            "required_output_entry_fields_present": False,
            "output_ids_unique": False,
            "output_types_valid": False,
            "output_type_coverage_present": False,
            "source_phases_valid": False,
            "export_status_allowed": False,
            "writeback_not_performed": False,
            "official_score_not_generated": False,
            "artifact_generation_not_generated": False,
            "data_boundary_blocks_forbidden_reads": False,
            "trace_links_present": False,
            "trace_links_known": False,
            "blocker_reasons_present": False,
            "phase2a_contract_pass": False,
            "phase2b_matrix_pass": False,
            "phase2c_binding_pass": False,
            "phase2d_checklist_pass": False,
            "phase2e_issue_list_pass": False,
            "safety_boundary_false": False,
            "no_real_doc_body_like_fields": False,
            "no_secret_like_fields": False,
            "readable_validation_errors": bool(validation_errors),
        }

    entries = _output_entries(data)
    output_section = data.get(OUTPUT_PRE_INDEX_SECTION)
    safety = data.get("safety_boundary") if isinstance(data.get("safety_boundary"), dict) else {}
    forbidden_scan = _forbidden_field_scan(data)

    return {
        "root_is_object": True,
        "output_pre_index_section_present": isinstance(output_section, list),
        "output_entries_present": isinstance(entries, list) and bool(entries),
        "required_output_entry_fields_present": _entries_have_required_fields(entries),
        "output_ids_unique": _output_ids_unique(entries),
        "output_types_valid": _entry_enum_values_valid(entries, "output_type", OUTPUT_TYPES),
        "output_type_coverage_present": _output_type_coverage_present(entries),
        "source_phases_valid": _entry_enum_values_valid(entries, "source_phase", VALID_SOURCE_PHASES),
        "export_status_allowed": _entry_enum_values_valid(entries, "export_status", VALID_EXPORT_STATUSES),
        "writeback_not_performed": _entry_status_not_forbidden(entries, "writeback_status", ("performed",)),
        "official_score_not_generated": _entry_status_not_forbidden(entries, "official_score_status", ("generated",)),
        "artifact_generation_not_generated": _entry_status_not_forbidden(
            entries,
            "artifact_generation_status",
            ("generated",),
        ),
        "data_boundary_blocks_forbidden_reads": _data_boundary_blocks_forbidden_reads(entries),
        "trace_links_present": _trace_links_present(entries),
        "trace_links_known": _trace_links_known(entries, trace_catalog),
        "blocker_reasons_present": _entry_string_field_present(entries, "blocker_reason"),
        "phase2a_contract_pass": phase2a_snapshot.get("status") == PHASE2A_PASS_STATUS,
        "phase2b_matrix_pass": phase2b_snapshot.get("status") == PHASE2B_PASS_STATUS,
        "phase2c_binding_pass": phase2c_snapshot.get("status") == PHASE2C_PASS_STATUS,
        "phase2d_checklist_pass": phase2d_snapshot.get("status") == PHASE2D_PASS_STATUS,
        "phase2e_issue_list_pass": phase2e_snapshot.get("status") == PHASE2E_PASS_STATUS,
        "safety_boundary_false": all(safety.get(flag) is False for flag in REQUIRED_FALSE_SAFETY_FLAGS),
        "no_real_doc_body_like_fields": not forbidden_scan["real_doc_body_like_paths"],
        "no_secret_like_fields": not forbidden_scan["secret_like_paths"],
        "readable_validation_errors": bool(validation_errors) == any(
            not passed
            for name, passed in {
                "required_output_entry_fields_present": _entries_have_required_fields(entries),
                "output_types_valid": _entry_enum_values_valid(entries, "output_type", OUTPUT_TYPES),
                "export_status_allowed": _entry_enum_values_valid(entries, "export_status", VALID_EXPORT_STATUSES),
                "writeback_not_performed": _entry_status_not_forbidden(entries, "writeback_status", ("performed",)),
                "official_score_not_generated": _entry_status_not_forbidden(entries, "official_score_status", ("generated",)),
                "artifact_generation_not_generated": _entry_status_not_forbidden(entries, "artifact_generation_status", ("generated",)),
                "data_boundary_blocks_forbidden_reads": _data_boundary_blocks_forbidden_reads(entries),
                "trace_links_present": _trace_links_present(entries),
                "trace_links_known": _trace_links_known(entries, trace_catalog),
            }.items()
            if name
        ),
    }


def _output_entries(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    value = data.get(OUTPUT_PRE_INDEX_SECTION)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _entries_have_required_fields(entries: Any) -> bool:
    return isinstance(entries, list) and bool(entries) and all(
        isinstance(item, dict) and all(field in item for field in OUTPUT_ENTRY_FIELDS)
        for item in entries
    )


def _output_ids_unique(entries: Any) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    ids = [
        item.get("output_id")
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("output_id"), str) and item.get("output_id")
    ]
    return len(ids) == len(entries) and len(ids) == len(set(ids))


def _output_type_coverage_present(entries: Any) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    types = {
        item.get("output_type")
        for item in entries
        if isinstance(item, dict) and isinstance(item.get("output_type"), str)
    }
    return set(OUTPUT_TYPES).issubset(types)


def _entry_enum_values_valid(entries: Any, field: str, valid_values: Iterable[str]) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    allowed = set(valid_values)
    return all(
        isinstance(item, dict)
        and isinstance(item.get(field), str)
        and item.get(field) in allowed
        for item in entries
    )


def _entry_status_not_forbidden(entries: Any, field: str, forbidden_values: Iterable[str]) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    forbidden = set(forbidden_values) | set(FORBIDDEN_GENERATED_STATUSES)
    return all(
        isinstance(item, dict)
        and isinstance(item.get(field), str)
        and item.get(field) not in forbidden
        for item in entries
    )


def _entry_string_field_present(entries: Any, field: str) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    return all(
        isinstance(item, dict)
        and isinstance(item.get(field), str)
        and bool(item[field].strip())
        for item in entries
    )


def _data_boundary_blocks_forbidden_reads(entries: Any) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    for item in entries:
        if not isinstance(item, dict):
            return False
        boundary = item.get("data_boundary")
        if not isinstance(boundary, dict):
            return False
        for flag in REQUIRED_FALSE_BOUNDARY_FLAGS:
            if boundary.get(flag) is not False:
                return False
        if boundary.get("content_source") != "synthetic_fixture_only":
            return False
    return True


def _trace_links_present(entries: Any) -> bool:
    if not isinstance(entries, list) or not entries:
        return False
    return all(
        isinstance(item, dict)
        and _non_empty_string_list(item.get("trace_links"))
        for item in entries
    )


def _trace_links_known(entries: Any, trace_catalog: set[str]) -> bool:
    if not isinstance(entries, list) or not entries or not trace_catalog:
        return False
    for item in entries:
        if not isinstance(item, dict):
            return False
        refs = item.get("trace_links")
        if not _non_empty_string_list(refs):
            return False
        if any(ref not in trace_catalog for ref in refs):
            return False
    return True


def _trace_catalog(
    data: Any,
    phase2b_snapshot: dict[str, Any],
    phase2c_snapshot: dict[str, Any],
    phase2d_snapshot: dict[str, Any],
    phase2e_snapshot: dict[str, Any],
) -> set[str]:
    catalog = {
        "phase2a:business_input_contract",
        "phase2a:project_metadata",
        "phase2a:tender_metadata",
        "phase2b:scoring_response_matrix",
        "phase2c:risk_object_binding",
        "phase2d:qingtian_friendly_checklist",
        "phase2e:final_review_issue_list",
        "synthetic_fixture:project.json",
    }
    if isinstance(data, dict):
        audit_boundary = data.get("audit_boundary_metadata")
        if isinstance(audit_boundary, dict) and isinstance(audit_boundary.get("snapshot_id"), str):
            catalog.add(f"synthetic_fixture:{audit_boundary['snapshot_id']}")
    for item_id in (phase2b_snapshot.get("matrix_summary") or {}).get("scoring_item_ids", []):
        catalog.add(f"phase2b:{item_id}")
    for risk_id in (phase2c_snapshot.get("binding_summary") or {}).get("risk_ids", []):
        catalog.add(f"phase2c:{risk_id}")
    for checklist_id in (phase2d_snapshot.get("checklist_summary") or {}).get("checklist_ids", []):
        catalog.add(f"phase2d:{checklist_id}")
    for issue_id in (phase2e_snapshot.get("issue_summary") or {}).get("issue_ids", []):
        catalog.add(f"phase2e:{issue_id}")
    return catalog


def _validation_errors(data: Any, trace_catalog: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["fixture root must be a JSON object"]
    entries = data.get(OUTPUT_PRE_INDEX_SECTION)
    if not isinstance(entries, list):
        return [f"{OUTPUT_PRE_INDEX_SECTION} must be a list of output entry objects"]
    for idx, item in enumerate(entries):
        path = f"{OUTPUT_PRE_INDEX_SECTION}[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in OUTPUT_ENTRY_FIELDS:
            if field not in item:
                errors.append(f"{path} missing required field: {field}")
        output_type = item.get("output_type")
        if "output_type" in item and output_type not in OUTPUT_TYPES:
            errors.append(f"{path}.output_type must be one of {list(OUTPUT_TYPES)}")
        export_status = item.get("export_status")
        if "export_status" in item and export_status not in VALID_EXPORT_STATUSES:
            errors.append(f"{path}.export_status must be blocked or preview_only")
        for field, generated_value in (
            ("artifact_generation_status", "generated"),
            ("official_score_status", "generated"),
            ("writeback_status", "performed"),
        ):
            if item.get(field) == generated_value:
                errors.append(f"{path}.{field} must not be {generated_value}")
        boundary = item.get("data_boundary")
        if "data_boundary" in item:
            if not isinstance(boundary, dict):
                errors.append(f"{path}.data_boundary must be an object")
            else:
                for flag in REQUIRED_FALSE_BOUNDARY_FLAGS:
                    if boundary.get(flag) is not False:
                        errors.append(f"{path}.data_boundary.{flag} must be false")
                if boundary.get("content_source") != "synthetic_fixture_only":
                    errors.append(f"{path}.data_boundary.content_source must be synthetic_fixture_only")
        trace_links = item.get("trace_links")
        if "trace_links" in item:
            if not _non_empty_string_list(trace_links):
                errors.append(f"{path}.trace_links must be a non-empty list of strings")
            else:
                missing = [ref for ref in trace_links if ref not in trace_catalog]
                if missing:
                    errors.append(f"{path}.trace_links contains unknown refs: {missing}")
    return errors


def _output_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    output_type_counts: dict[str, int] = {}
    export_status_counts: dict[str, int] = {}
    for item in entries:
        output_type = item.get("output_type")
        if isinstance(output_type, str):
            output_type_counts[output_type] = output_type_counts.get(output_type, 0) + 1
        export_status = item.get("export_status")
        if isinstance(export_status, str):
            export_status_counts[export_status] = export_status_counts.get(export_status, 0) + 1
    return {
        "row_count": len(entries),
        "output_ids": [
            item.get("output_id")
            for item in entries
            if isinstance(item.get("output_id"), str)
        ],
        "output_type_counts": output_type_counts,
        "export_status_counts": export_status_counts,
    }


def _forbidden_field_scan(data: Any) -> dict[str, list[str]]:
    real_doc_paths: list[str] = []
    secret_paths: list[str] = []
    real_doc_boundary_keys = {"real_business_doc_body_allowed", "real_business_doc_body_read"}
    secret_boundary_keys = {"secret_body_allowed", "secret_read"}

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key).lower()
                child_path = f"{path}.{key}" if path else str(key)
                if key_text not in real_doc_boundary_keys and any(
                    marker in key_text for marker in REAL_DOC_BODY_MARKERS
                ):
                    real_doc_paths.append(child_path)
                if key_text not in secret_boundary_keys and any(marker in key_text for marker in SECRET_MARKERS):
                    secret_paths.append(child_path)
                visit(child, child_path)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                visit(child, f"{path}[{idx}]")
        elif isinstance(value, str):
            text = value.lower()
            if any(marker in text for marker in SECRET_MARKERS):
                secret_paths.append(path)

    visit(data, "")
    return {
        "real_doc_body_like_paths": sorted(set(real_doc_paths)),
        "secret_like_paths": sorted(set(secret_paths)),
    }


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and bool(item.strip())
        for item in value
    )


def _dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))
