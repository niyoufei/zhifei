import sys
from pathlib import Path

from backend.zhifei_autoplan import zdoc_zbid_preview_outbound as outbound_module
from backend.zhifei_autoplan.zbid_preview_input_validator import validate_zbid_preview_input
from backend.zhifei_autoplan.zdoc_zbid_preview_outbound import (
    FORMAL_CHAIN_FALSE_FLAGS,
    NO_WRITE_FALSE_FLAGS,
    OUTBOUND_ENABLED_ENV,
    OUTBOUND_ENDPOINT_ENV,
    OUTBOUND_NETWORK_SEND_ENABLED_ENV,
    USER_VISIBLE_FALSE_FLAGS,
    ZBID_PREVIEW_ONLY_RECEIVER_PATH,
    build_zdoc_zbid_preview_only_outbound_config,
    build_zdoc_zbid_preview_only_outbound_payload,
    prepare_zdoc_zbid_preview_only_outbound,
)
from backend.zhifei_autoplan.zdoc_zbid_preview_packet import build_zdoc_zbid_preview_packet


FIXED_GENERATED_AT = "2026-01-01T00:00:00Z"
MAIN_CHAIN_OR_WRITEBACK_MODULES = {
    "backend.zhifei_autoplan.orchestrator",
    "backend.zhifei_autoplan.llm_client",
    "backend.zhifei_autoplan.provider",
    "backend.zhifei_autoplan.generation",
    "backend.zhifei_autoplan.export",
    "backend.zhifei_autoplan.review",
    "backend.app.routers.actions_bridge",
    "backend.app.routers.export",
    "backend.app.routers.review",
    "backend.zhifei_autoplan.zbid_snapshot_mapper",
    "docx",
}


def _file_count(path: str) -> int:
    root = Path(path)
    if not root.exists():
        return 0
    return sum(1 for item in root.rglob("*") if item.is_file())


def _write_surface_counts() -> dict[str, int]:
    return {
        "output": _file_count("output"),
        "job": _file_count("job"),
        "export": _file_count("export"),
    }


def _safe_preview_packet(**overrides):
    payload = {
        "source_system": "zdoc",
        "target_system": "zbid",
        "project_id": "project-preview-only",
        "document_id": "doc-preview-only",
        "section_id": "section-preview-only",
        "section_title": "Preview Only Section",
        "section_hash": "sha256:section-preview",
        "section_version": "v1",
        "tender_file_refs": ["tender:file:001"],
        "scoring_clause_refs": ["tender:scoring-clause:001"],
        "evidence_anchor_refs": ["tender:evidence-anchor:001"],
        "evidence_anchor_status": "source_verified",
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "preview_advisory_summary": "Fake preview-only advisory summary.",
        "generated_at": FIXED_GENERATED_AT,
        "model_provider": "fake",
        "model_name": "fake-model",
        "generated_advisory_used_as_evidence": False,
        "preview_advisory_used_as_evidence": False,
        "shadow_candidate_used_as_evidence": False,
        "patch_preview_used_as_evidence": False,
        "diff_preview_used_as_evidence": False,
        "rollback_plan_used_as_evidence": False,
        "dry_run_used_as_evidence": False,
        "scoring_clause_unverifiable": False,
        "high_risk_validation_ready": False,
        "zbid_writeback_requested": False,
        "docx_export_requested": False,
        "review_apply_requested": False,
        "formal_writeback_requested": False,
        "output_write_requested": False,
        "integration_request_id": "preview-only-outbound-001",
    }
    payload.update(overrides)
    return build_zdoc_zbid_preview_packet(**payload)


def _safe_outbound_inputs(**overrides):
    packet = _safe_preview_packet(**overrides)
    validator_result = validate_zbid_preview_input(packet)
    return packet, validator_result, packet["blocked_reasons"] + validator_result["blocked_reasons"]


def _assert_false_flags(container):
    for flag, expected in NO_WRITE_FALSE_FLAGS.items():
        assert container[flag] is expected


def _assert_user_visible_false_flags(container):
    for flag, expected in USER_VISIBLE_FALSE_FLAGS.items():
        assert container[flag] is expected


def _receiver_endpoint() -> str:
    return f"http://127.0.0.1:18080{ZBID_PREVIEW_ONLY_RECEIVER_PATH}"


def _receiver_success_response(payload: dict) -> dict:
    return {
        "status_code": 200,
        "body": {
            "status": "accepted_preview_only",
            "receiver_accepted": True,
            "preview_only": True,
            "no_write": True,
            "no_evidence": True,
            "preview_packet": payload["preview_packet"],
            "validator_result": payload["validator_result"],
            "blocked_reasons": payload["blocked_reasons"],
            "produces_evidence": False,
            "produces_writeback": False,
            "writes_storage": False,
            "writes_scoring_basis": False,
            **USER_VISIBLE_FALSE_FLAGS,
        },
    }


def _fail_sender(*args, **kwargs):
    raise AssertionError("real network sender must not be called")


def test_outbound_config_defaults_disabled_and_no_network_send():
    config = build_zdoc_zbid_preview_only_outbound_config(env={})

    assert config["enabled"] is False
    assert config["default_off"] is True
    assert config["endpoint_configured"] is False
    assert config["status"] == "disabled"
    assert config["auto_send_allowed"] is False
    assert config["network_send_allowed"] is False
    assert config["network_send_attempted"] is False
    assert config["zbid_writeback_attempted"] is False
    assert "zdoc_zbid_preview_only_outbound_disabled" in config["blocked_reasons"]
    _assert_false_flags(config)


def test_configured_endpoint_without_explicit_network_send_remains_not_sent():
    config = build_zdoc_zbid_preview_only_outbound_config(
        env={
            OUTBOUND_ENABLED_ENV: "true",
            OUTBOUND_ENDPOINT_ENV: _receiver_endpoint(),
        }
    )

    assert config["enabled"] is True
    assert config["default_off"] is True
    assert config["endpoint_configured"] is True
    assert config["receiver_endpoint_allowed"] is True
    assert config["network_send_explicitly_enabled"] is False
    assert config["status"] == "configured_not_sent"
    assert config["auto_send_allowed"] is False
    assert config["network_send_allowed"] is False
    assert config["network_send_attempted"] is False
    assert "zdoc_zbid_preview_only_network_send_not_enabled" in config[
        "blocked_reasons"
    ]
    _assert_false_flags(config)


def test_outbound_payload_contains_only_preview_data_and_false_flags():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    payload = build_zdoc_zbid_preview_only_outbound_payload(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
    )

    expected_keys = {
        "preview_packet",
        "validator_result",
        "blocked_reasons",
        *USER_VISIBLE_FALSE_FLAGS,
    }
    assert set(payload) == expected_keys
    assert payload["preview_packet"] == packet
    assert payload["validator_result"] == validator_result
    assert "preview_only_is_not_writeback_permission" in payload["blocked_reasons"]
    assert "preview_only_is_not_evidence" in payload["blocked_reasons"]
    _assert_user_visible_false_flags(payload)


def test_prepare_outbound_is_default_off_and_never_attempts_send():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(env={}),
        sender=_fail_sender,
    )

    assert result["ok"] is False
    assert result["outbound_status"] == "disabled"
    assert result["outbound_enabled"] is False
    assert result["default_off"] is True
    assert result["auto_send_allowed"] is False
    assert result["network_send_allowed"] is False
    assert result["network_send_attempted"] is False
    assert result["zbid_writeback_attempted"] is False
    assert result["payload"]["preview_packet"] == packet
    assert result["payload"]["validator_result"] == validator_result
    assert "zdoc_zbid_preview_only_outbound_disabled" in result["blocked_reasons"]
    _assert_false_flags(result)
    _assert_user_visible_false_flags(result["payload"])


def test_prepare_outbound_blocks_missing_endpoint_without_formal_fallback():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={OUTBOUND_ENABLED_ENV: "1"}
        ),
        sender=_fail_sender,
    )

    assert result["outbound_status"] == "blocked_missing_endpoint"
    assert result["outbound_enabled"] is True
    assert result["endpoint_configured"] is False
    assert result["network_send_attempted"] is False
    assert "zdoc_zbid_preview_only_endpoint_missing" in result["blocked_reasons"]
    _assert_false_flags(result)


def test_disallowed_endpoint_blocks_without_sender_call():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={
                OUTBOUND_ENABLED_ENV: "1",
                OUTBOUND_ENDPOINT_ENV: "http://127.0.0.1:18080/generate",
                OUTBOUND_NETWORK_SEND_ENABLED_ENV: "1",
            }
        ),
        sender=_fail_sender,
    )

    assert result["outbound_status"] == "blocked_disallowed_endpoint"
    assert result["receiver_endpoint_allowed"] is False
    assert result["network_send_allowed"] is False
    assert result["network_send_attempted"] is False
    assert "zdoc_zbid_preview_only_endpoint_not_receiver" in result["blocked_reasons"]
    _assert_false_flags(result)


def test_explicit_network_send_uses_fake_sender_for_receiver_endpoint_only():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    calls: list[tuple[str, dict]] = []

    def fake_sender(endpoint: str, payload: dict) -> dict:
        calls.append((endpoint, payload))
        return _receiver_success_response(payload)

    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={
                OUTBOUND_ENABLED_ENV: "1",
                OUTBOUND_ENDPOINT_ENV: _receiver_endpoint(),
                OUTBOUND_NETWORK_SEND_ENABLED_ENV: "1",
            }
        ),
        sender=fake_sender,
    )

    assert result["ok"] is True
    assert result["outbound_status"] == "sent_preview_only"
    assert result["network_send_allowed"] is True
    assert result["network_send_attempted"] is True
    assert result["network_send_succeeded"] is True
    assert result["http_status"] == 200
    assert calls == [(result["endpoint"], result["payload"])]
    assert result["endpoint"].endswith(ZBID_PREVIEW_ONLY_RECEIVER_PATH)
    assert set(result["payload"]) == {
        "preview_packet",
        "validator_result",
        "blocked_reasons",
        *USER_VISIBLE_FALSE_FLAGS,
    }
    assert result["receiver_response"]["preview_only"] is True
    assert result["receiver_response"]["no_write"] is True
    assert result["receiver_response"]["no_evidence"] is True
    _assert_false_flags(result)
    _assert_user_visible_false_flags(result["payload"])


def test_true_formal_chain_flag_blocks_before_network_send():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    packet["generate_called"] = True

    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={
                OUTBOUND_ENABLED_ENV: "1",
                OUTBOUND_ENDPOINT_ENV: _receiver_endpoint(),
                OUTBOUND_NETWORK_SEND_ENABLED_ENV: "1",
            }
        ),
        sender=_fail_sender,
    )

    assert result["ok"] is False
    assert result["network_send_allowed"] is True
    assert result["network_send_attempted"] is False
    assert "formal_chain_flag_must_be_false:generate_called" in result[
        "blocked_reasons"
    ]
    _assert_false_flags(result)


def test_fake_sender_failure_returns_preview_only_no_write_error_without_fallback():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()

    def failing_sender(endpoint: str, payload: dict) -> dict:
        raise RuntimeError("receiver unavailable")

    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={
                OUTBOUND_ENABLED_ENV: "1",
                OUTBOUND_ENDPOINT_ENV: _receiver_endpoint(),
                OUTBOUND_NETWORK_SEND_ENABLED_ENV: "1",
            }
        ),
        sender=failing_sender,
    )

    assert result["ok"] is False
    assert result["outbound_status"] == "send_failed"
    assert result["network_send_attempted"] is True
    assert result["network_send_succeeded"] is False
    assert result["preview_only"] is True
    assert result["no_write"] is True
    assert "zdoc_zbid_preview_only_send_failed" in result["blocked_reasons"]
    assert result["calls_generate_route_runtime"] is False
    assert result["calls_export_docx_route_runtime"] is False
    assert result["calls_review_apply_route_runtime"] is False
    assert result["zbid_writeback_attempted"] is False


def test_receiver_rejection_remains_preview_only_no_write_without_fallback():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()

    def rejecting_sender(endpoint: str, payload: dict) -> dict:
        body = _receiver_success_response(payload)["body"]
        body["status"] = "blocked_preview_only"
        body["receiver_accepted"] = False
        return {"status_code": 200, "body": body}

    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={
                OUTBOUND_ENABLED_ENV: "1",
                OUTBOUND_ENDPOINT_ENV: _receiver_endpoint(),
                OUTBOUND_NETWORK_SEND_ENABLED_ENV: "1",
            }
        ),
        sender=rejecting_sender,
    )

    assert result["ok"] is False
    assert result["outbound_status"] == "receiver_rejected_or_invalid"
    assert result["network_send_attempted"] is True
    assert result["network_send_succeeded"] is False
    assert "zbid_preview_only_receiver_blocked_payload" in result["blocked_reasons"]
    assert "zbid_preview_only_receiver_not_accepted" in result["blocked_reasons"]
    assert result["produces_evidence"] is False
    assert result["produces_writeback"] is False
    assert result["writes_output_job_export"] is False


def test_invalid_payload_inputs_return_preview_only_no_write_errors():
    payload = build_zdoc_zbid_preview_only_outbound_payload(
        preview_packet=None,
        validator_result=None,
        blocked_reasons=None,
    )

    assert payload["preview_packet"] == {}
    assert payload["validator_result"] == {}
    assert "invalid_preview_packet_for_outbound" in payload["blocked_reasons"]
    assert "invalid_validator_result_for_outbound" in payload["blocked_reasons"]
    _assert_user_visible_false_flags(payload)


def test_outbound_adapter_preserves_formal_and_user_visible_false_flags():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(env={}),
    )

    for flag in FORMAL_CHAIN_FALSE_FLAGS:
        assert result[flag] is False
    for flag in USER_VISIBLE_FALSE_FLAGS:
        assert result[flag] is False
        assert result["payload"][flag] is False


def test_outbound_adapter_does_not_write_output_job_export():
    before_counts = _write_surface_counts()
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()

    prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(env={}),
    )

    assert _write_surface_counts() == before_counts


def test_outbound_adapter_imports_do_not_pull_main_chain_or_writeback_modules(
    assert_clean_import,
):
    assert_clean_import(
        "backend.zhifei_autoplan.zdoc_zbid_preview_outbound",
        MAIN_CHAIN_OR_WRITEBACK_MODULES,
    )


def test_outbound_adapter_source_does_not_import_network_clients_or_formal_modules():
    source = Path(outbound_module.__file__).read_text(encoding="utf-8")

    forbidden_snippets = {
        "orchestrator",
        "llm_client",
        "actions_bridge",
        "zbid_snapshot_mapper",
        "requests",
        "httpx",
        "socket",
        "subprocess",
        "Path(",
    }
    assert not {snippet for snippet in forbidden_snippets if snippet in source}
