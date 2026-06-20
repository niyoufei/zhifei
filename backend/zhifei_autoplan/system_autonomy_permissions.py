from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class PermissionDimension(str, Enum):
    DOCS_READ = "docs_read"
    DOCS_WRITE = "docs_write"
    CODE_READ = "code_read"
    CODE_MODIFY = "code_modify"
    SCRIPT_READ = "script_read"
    SCRIPT_EXECUTE = "script_execute"
    SERVICE_START = "service_start"
    WEB_UI_START = "web_ui_start"
    ENDPOINT_ACCESS = "endpoint_access"
    HTTP_REQUEST = "http_request"
    OLLAMA = "ollama"
    MODEL_COMMAND = "model_command"
    MODEL_INFERENCE = "model_inference"
    PROMPT_INPUT = "prompt_input"
    KG_READ = "kg_read"
    REAL_PROJECT_DATA_READ = "real_project_data_read"
    OUTPUT_JOB_EXPORT_LOG_READ = "output_job_export_log_read"
    SECRETS_READ = "secrets_read"
    GENERATION = "generation"
    EXPORT = "export"
    WRITE_BACK = "write_back"
    TRIAL = "trial"
    PRODUCTION_USE = "production_use"


class ApprovalLevel(str, Enum):
    A0_DOCS_READ = "A0"
    A1_DOCS_WRITE = "A1"
    A2_CODE_READ = "A2"
    A3_CODE_CHANGE = "A3"
    A4_RUNTIME_PREFLIGHT = "A4"
    A5_ENDPOINT_DRY_RUN_PROMPT = "A5"
    A6_REAL_DATA = "A6"
    A7_TRIAL = "A7"
    A8_PRODUCTION = "A8"


class GovernanceMode(str, Enum):
    DOCS_ONLY = "docs_only"
    CODE_READ_ONLY = "code_read_only"
    CODE_CHANGE_NO_RUNTIME = "code_change_no_runtime"
    STATIC_VALIDATION_ONLY = "static_validation_only"


DEFAULT_FORBIDDEN_DIMENSIONS = frozenset(
    {
        PermissionDimension.SERVICE_START,
        PermissionDimension.WEB_UI_START,
        PermissionDimension.ENDPOINT_ACCESS,
        PermissionDimension.HTTP_REQUEST,
        PermissionDimension.OLLAMA,
        PermissionDimension.MODEL_COMMAND,
        PermissionDimension.MODEL_INFERENCE,
        PermissionDimension.PROMPT_INPUT,
        PermissionDimension.KG_READ,
        PermissionDimension.REAL_PROJECT_DATA_READ,
        PermissionDimension.OUTPUT_JOB_EXPORT_LOG_READ,
        PermissionDimension.SECRETS_READ,
        PermissionDimension.GENERATION,
        PermissionDimension.EXPORT,
        PermissionDimension.WRITE_BACK,
        PermissionDimension.TRIAL,
        PermissionDimension.PRODUCTION_USE,
    }
)

MODE_ALLOWED_DIMENSIONS: Mapping[GovernanceMode, frozenset[PermissionDimension]] = {
    GovernanceMode.DOCS_ONLY: frozenset(
        {PermissionDimension.DOCS_READ, PermissionDimension.DOCS_WRITE}
    ),
    GovernanceMode.CODE_READ_ONLY: frozenset(
        {PermissionDimension.DOCS_READ, PermissionDimension.CODE_READ}
    ),
    GovernanceMode.CODE_CHANGE_NO_RUNTIME: frozenset(
        {
            PermissionDimension.DOCS_READ,
            PermissionDimension.DOCS_WRITE,
            PermissionDimension.CODE_READ,
            PermissionDimension.CODE_MODIFY,
        }
    ),
    GovernanceMode.STATIC_VALIDATION_ONLY: frozenset(
        {
            PermissionDimension.DOCS_READ,
            PermissionDimension.CODE_READ,
            PermissionDimension.SCRIPT_EXECUTE,
        }
    ),
}

MODE_REQUIRED_APPROVAL: Mapping[GovernanceMode, ApprovalLevel] = {
    GovernanceMode.DOCS_ONLY: ApprovalLevel.A1_DOCS_WRITE,
    GovernanceMode.CODE_READ_ONLY: ApprovalLevel.A2_CODE_READ,
    GovernanceMode.CODE_CHANGE_NO_RUNTIME: ApprovalLevel.A3_CODE_CHANGE,
    GovernanceMode.STATIC_VALIDATION_ONLY: ApprovalLevel.A3_CODE_CHANGE,
}


@dataclass(frozen=True)
class PermissionRequest:
    mode: GovernanceMode
    requested_dimensions: tuple[PermissionDimension, ...]
    approval_level: ApprovalLevel
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PermissionCheckResult:
    allowed: bool
    mode: GovernanceMode
    required_approval_level: ApprovalLevel
    blocked_dimensions: tuple[PermissionDimension, ...]
    missing_evidence: tuple[str, ...]
    blocked_reasons: tuple[str, ...]


def check_permission_request(request: PermissionRequest) -> PermissionCheckResult:
    allowed_dimensions = MODE_ALLOWED_DIMENSIONS[request.mode]
    blocked_dimensions = tuple(
        dimension
        for dimension in request.requested_dimensions
        if dimension not in allowed_dimensions or dimension in DEFAULT_FORBIDDEN_DIMENSIONS
    )
    required_approval = MODE_REQUIRED_APPROVAL[request.mode]
    missing_evidence = () if request.evidence_refs else ("evidence_refs",)
    blocked_reasons: list[str] = []
    if blocked_dimensions:
        blocked_reasons.append("requested_dimension_forbidden_in_current_mode")
    if _approval_rank(request.approval_level) < _approval_rank(required_approval):
        blocked_reasons.append("approval_level_below_required_gate")
    if missing_evidence:
        blocked_reasons.append("missing_permission_evidence_refs")
    return PermissionCheckResult(
        allowed=not blocked_dimensions
        and not missing_evidence
        and _approval_rank(request.approval_level) >= _approval_rank(required_approval),
        mode=request.mode,
        required_approval_level=required_approval,
        blocked_dimensions=blocked_dimensions,
        missing_evidence=missing_evidence,
        blocked_reasons=tuple(blocked_reasons),
    )


def _approval_rank(level: ApprovalLevel) -> int:
    return list(ApprovalLevel).index(level)
