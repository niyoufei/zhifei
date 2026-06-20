from backend.zhifei_autoplan.system_autonomy_state_machine import (
    StateAction,
    StateTransitionRequest,
    SystemAutonomyState,
    check_s6_action,
    check_state_transition,
)


def test_s5_to_s6_requires_evidence():
    result = check_state_transition(
        StateTransitionRequest(
            current_state=SystemAutonomyState.S5_CODE_CHANGE_PROPOSAL,
            target_state=SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME,
        )
    )

    assert result.allowed is False
    assert result.blocked_reasons == ("missing_transition_evidence_refs",)


def test_s6_must_not_skip_to_runtime_prefight():
    result = check_state_transition(
        StateTransitionRequest(
            current_state=SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME,
            target_state=SystemAutonomyState.S8_RUNTIME_PREFLIGHT_AUTHORIZATION_REQUIRED,
            evidence_refs=("diff",),
        )
    )

    assert result.allowed is False
    assert "target_state_not_next_authorized_state" in result.blocked_reasons
    assert "s6_may_only_stop_or_wait_for_static_validation_gate" in result.blocked_reasons


def test_s6_forbids_runtime_endpoint_ollama_model_prompt_and_real_data_actions():
    forbidden = (
        StateAction.START_SERVICE,
        StateAction.ACCESS_ENDPOINT,
        StateAction.RUN_OLLAMA,
        StateAction.RUN_MODEL_INFERENCE,
        StateAction.INPUT_PROMPT,
        StateAction.READ_REAL_KG,
        StateAction.READ_REAL_PROJECT_DATA,
        StateAction.GENERATE_EXPORT_WRITE_BACK,
    )

    for action in forbidden:
        result = check_s6_action(action)
        assert result.allowed is False
        assert result.blocked_reasons == ("action_forbidden_in_s6_no_runtime_state",)


def test_blocked_trigger_can_only_enter_sx():
    result = check_state_transition(
        StateTransitionRequest(
            current_state=SystemAutonomyState.S6_CODE_CHANGE_IMPLEMENTATION_NO_RUNTIME,
            target_state=SystemAutonomyState.S7_STATIC_VALIDATION_ONLY,
            blocked_triggered=True,
        )
    )

    assert result.allowed is False
    assert result.blocked_reasons == ("blocked_trigger_requires_sx",)
