from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SystemAutonomyState(str, Enum):
    S0_DOCS_ONLY_PLANNING = "S0_DOCS_ONLY_PLANNING"
    S1_DOCS_GOVERNANCE_LOCKED = "S1_DOCS_GOVERNANCE_LOCKED"
    S2_TASK_DECOMPOSITION_LOCKED = "S2_TASK_DECOMPOSITION_LOCKED"
    S3_PERMISSION_MATRIX_LOCKED = "S3_PERMISSION_MATRIX_LOCKED"
    S4_CODE_READ_ONLY_INVENTORY = "S4_CODE_READ_ONLY_INVENTORY"
    S5_CODE_CHANGE_PROPOSAL = "S5_CODE_CHANGE_PROPOSAL"
    S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME = "S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME"
    S7_STATIC_VALIDATION_ONLY = "S7_STATIC_VALIDATION_ONLY"
    S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED = "S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED"
    S9_RUNTIME_PREFLIGHT_NO_ENDPOINT = "S9_RUNTIME_PREFLIGHT_NO_ENDPOINT"
    S10_MOCK_OR_DRY_RUN_AUTHORIZATION_REQUIRED = "S10_MOCK_OR_DRY_RUN_AUTHORIZATION_REQUIRED"
    S11_CONTROLLED_DRY_RUN_NO_REAL_DATA = "S11_CONTROLLED_DRY_RUN_NO_REAL_DATA"
    S12_SINGLE_USER_TRIAL_AUTHORIZATION_REQUIRED = "S12_SINGLE_USER_TRIAL_AUTHORIZATION_REQUIRED"
    S13_LIMITED_PILOT_AUTHORIZATION_REQUIRED = "S13_LIMITED_PILOT_AUTHORIZATION_REQUIRED"
    S14_PRODUCTION_FREEZE_REVIEW = "S14_PRODUCTION_FREEZE_REVIEW"
    S15_PRODUCTION_USE_AUTHORIZATION_REQUIRED = "S15_PRODUCTION_USE_AUTHORIZATION_REQUIRED"
    SX_BLOCKED_OR_ROLLBACK = "SX_BLOCKED_OR_ROLLBACK"


class StateAction(str, Enum):
    READ_AUTHORIZED_DOCS = "read_authorized_docs"
    READ_AUTHORIZED_CODE = "read_authorized_code"
    MODIFY_AUTHORIZED_CODE = "modify_authorized_code"
    WRITE_AUTHORIZED_TEST_SOURCE = "write_authorized_test_source"
    WRITE_AUTHORIZED_DOC_RECORD = "write_authorized_doc_record"
    PY_COMPILE_AUTHORIZED_FILES = "py_compile_authorized_files"
    DIFF_CHECK_AUTHORIZED_FILES = "diff_check_authorized_files"
    START_SERVICE = "start_service"
    ACCESS_ENDPOINT = "access_endpoint"
    RUN_OLLAMA = "run_ollama"
    RUN_MODEL_INFERENCE = "run_model_inference"
    INPUT_PROMPT = "input_prompt"
    READ_REAL_KG = "read_real_kg"
    READ_REAL_PROJECT_DATA = "read_real_project_data"
    GENERATE_EXPORT_WRITE_BACK = "generate_export_write_back"


S6_ALLOWED_ACTIONS = frozenset(
    {
        StateAction.READ_AUTHORIZED_DOCS,
        StateAction.READ_AUTHORIZED_CODE,
        StateAction.MODIFY_AUTHORIZED_CODE,
        StateAction.WRITE_AUTHORIZED_TEST_SOURCE,
        StateAction.WRITE_AUTHORIZED_DOC_RECORD,
        StateAction.PY_COMPILE_AUTHORIZED_FILES,
        StateAction.DIFF_CHECK_AUTHORIZED_FILES,
    }
)

S6_FORBIDDEN_ACTIONS = frozenset(
    {
        StateAction.START_SERVICE,
        StateAction.ACCESS_ENDPOINT,
        StateAction.RUN_OLLAMA,
        StateAction.RUN_MODEL_INFERENCE,
        StateAction.INPUT_PROMPT,
        StateAction.READ_REAL_KG,
        StateAction.READ_REAL_PROJECT_DATA,
        StateAction.GENERATE_EXPORT_WRITE_BACK,
    }
)

ALLOWED_TRANSITIONS = {
    SystemAutonomyState.S0_DOCS_ONLY_PLANNING: frozenset(
        {SystemAutonomyState.S1_DOCS_GOVERNANCE_LOCKED}
    ),
    SystemAutonomyState.S1_DOCS_GOVERNANCE_LOCKED: frozenset(
        {SystemAutonomyState.S2_TASK_DECOMPOSITION_LOCKED}
    ),
    SystemAutonomyState.S2_TASK_DECOMPOSITION_LOCKED: frozenset(
        {SystemAutonomyState.S3_PERMISSION_MATRIX_LOCKED}
    ),
    SystemAutonomyState.S3_PERMISSION_MATRIX_LOCKED: frozenset(
        {SystemAutonomyState.S4_CODE_READ_ONLY_INVENTORY}
    ),
    SystemAutonomyState.S4_CODE_READ_ONLY_INVENTORY: frozenset(
        {SystemAutonomyState.S5_CODE_CHANGE_PROPOSAL}
    ),
    SystemAutonomyState.S5_CODE_CHANGE_PROPOSAL: frozenset(
        {SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME}
    ),
    SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME: frozenset(
        {SystemAutonomyState.S7_STATIC_VALIDATION_ONLY}
    ),
    SystemAutonomyState.S7_STATIC_VALIDATION_ONLY: frozenset(
        {SystemAutonomyState.S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED}
    ),
}


@dataclass(frozen=True)
class StateTransitionRequest:
    current_state: SystemAutonomyState
    target_state: SystemAutonomyState
    evidence_refs: tuple[str, ...] = ()
    blocked_triggered: bool = False


@dataclass(frozen=True)
class StateTransitionCheckResult:
    allowed: bool
    current_state: SystemAutonomyState
    target_state: SystemAutonomyState
    blocked_reasons: tuple[str, ...]


def check_state_transition(request: StateTransitionRequest) -> StateTransitionCheckResult:
    if request.blocked_triggered:
        return StateTransitionCheckResult(
            allowed=request.target_state is SystemAutonomyState.SX_BLOCKED_OR_ROLLBACK,
            current_state=request.current_state,
            target_state=request.target_state,
            blocked_reasons=()
            if request.target_state is SystemAutonomyState.SX_BLOCKED_OR_ROLLBACK
            else ("blocked_trigger_requires_sx",),
        )
    allowed_targets = ALLOWED_TRANSITIONS.get(request.current_state, frozenset())
    blocked_reasons: list[str] = []
    if request.target_state not in allowed_targets:
        blocked_reasons.append("target_state_not_next_authorized_state")
    if not request.evidence_refs:
        blocked_reasons.append("missing_transition_evidence_refs")
    if (
        request.current_state is SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME
        and request.target_state is not SystemAutonomyState.S7_STATIC_VALIDATION_ONLY
    ):
        blocked_reasons.append("s6_may_only_stop_or_wait_for_static_validation_gate")
    return StateTransitionCheckResult(
        allowed=not blocked_reasons,
        current_state=request.current_state,
        target_state=request.target_state,
        blocked_reasons=tuple(blocked_reasons),
    )


def check_s6_action(action: StateAction) -> StateTransitionCheckResult:
    blocked_reasons = ()
    if action in S6_FORBIDDEN_ACTIONS or action not in S6_ALLOWED_ACTIONS:
        blocked_reasons = ("action_forbidden_in_s6_no_runtime_state",)
    return StateTransitionCheckResult(
        allowed=not blocked_reasons,
        current_state=SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME,
        target_state=SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME,
        blocked_reasons=blocked_reasons,
    )
