from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


GATE_REPORT_REQUIRED_FIELDS = (
    "node_name",
    "completed",
    "new_codex_thread",
    "goal_mode_used",
    "start_branch",
    "start_head",
    "start_tag",
    "end_head",
    "git_status_short_clean",
    "added_files",
    "modified_files",
    "changed_files_authorized_only",
    "actual_read_files",
    "runtime_script_body_read",
    "service_started_stopped_restarted",
    "web_ui_start_script_executed",
    "html_opened_previewed_or_run",
    "endpoint_or_http_or_localhost_accessed",
    "runtime_pid_file_read_cleaned_deleted",
    "ollama_or_model_command_run",
    "model_inference_performed",
    "prompt_input_performed",
    "real_kg_or_project_data_read",
    "secrets_tokens_credentials_read",
    "output_job_export_log_body_read",
    "generation_export_writeback_executed",
    "local_launcher_static_modified",
    "runtime_script_modified",
    "web_ui_endpoint_api_model_kg_modified",
    "runtime_endpoint_api_model_kg_code_created",
    "test_suite_run",
    "py_compile_evidence",
    "git_diff_check_evidence",
    "git_diff_cached_name_status_evidence",
    "commit",
    "tag",
    "node_conclusion",
    "stopped_without_next_node",
)

FORBIDDEN_CONFIRMATION_FIELDS = frozenset(
    {
        "runtime_script_body_read",
        "service_started_stopped_restarted",
        "web_ui_start_script_executed",
        "html_opened_previewed_or_run",
        "endpoint_or_http_or_localhost_accessed",
        "runtime_pid_file_read_cleaned_deleted",
        "ollama_or_model_command_run",
        "model_inference_performed",
        "prompt_input_performed",
        "real_kg_or_project_data_read",
        "secrets_tokens_credentials_read",
        "output_job_export_log_body_read",
        "generation_export_writeback_executed",
        "local_launcher_static_modified",
        "runtime_script_modified",
        "web_ui_endpoint_api_model_kg_modified",
        "runtime_endpoint_api_model_kg_code_created",
        "test_suite_run",
    }
)


@dataclass(frozen=True)
class EvidenceCheckResult:
    complete: bool
    missing_fields: tuple[str, ...]
    forbidden_confirmations_triggered: tuple[str, ...]
    blocked_reasons: tuple[str, ...]


def build_gate_report_template() -> dict[str, Any]:
    return {field: None for field in GATE_REPORT_REQUIRED_FIELDS}


def validate_gate_report(report: Mapping[str, Any]) -> EvidenceCheckResult:
    missing_fields = tuple(
        field
        for field in GATE_REPORT_REQUIRED_FIELDS
        if field not in report or _is_empty(report[field])
    )
    forbidden_hits = tuple(
        field for field in FORBIDDEN_CONFIRMATION_FIELDS if report.get(field) is True
    )
    blocked_reasons: list[str] = []
    if missing_fields:
        blocked_reasons.append("gate_report_required_fields_missing")
    if forbidden_hits:
        blocked_reasons.append("forbidden_confirmation_field_triggered")
    if report.get("changed_files_authorized_only") is not True:
        blocked_reasons.append("changed_files_not_confirmed_authorized_only")
    if report.get("git_status_short_clean") is not True:
        blocked_reasons.append("git_status_not_confirmed_clean")
    if report.get("stopped_without_next_node") is not True:
        blocked_reasons.append("stop_point_not_confirmed")
    return EvidenceCheckResult(
        complete=not missing_fields and not forbidden_hits and not blocked_reasons,
        missing_fields=missing_fields,
        forbidden_confirmations_triggered=forbidden_hits,
        blocked_reasons=tuple(blocked_reasons),
    )


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
