import sys
from pathlib import Path

from backend.zhifei_autoplan import zdoc_zbid_preview_outbound as outbound_module
from backend.zhifei_autoplan.zbid_preview_input_validator import validate_zbid_preview_input
from backend.zhifei_autoplan.zdoc_zbid_preview_outbound import (
    FORMAL_CHAIN_FALSE_FLAGS,
    NO_WRITE_FALSE_FLAGS,
    OUTBOUND_ENABLED_ENV,
    OUTBOUND_ENDPOINT_ENV,
    USER_VISIBLE_FALSE_FLAGS,
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


def test_configured_endpoint_remains_not_sent_by_design():
    config = build_zdoc_zbid_preview_only_outbound_config(
        env={
            OUTBOUND_ENABLED_ENV: "true",
            OUTBOUND_ENDPOINT_ENV: "https://zbid.example.invalid/preview-only",
        }
    )

    assert config["enabled"] is True
    assert config["default_off"] is False
    assert config["endpoint_configured"] is True
    assert config["status"] == "configured_not_sent"
    assert config["auto_send_allowed"] is False
    assert config["network_send_allowed"] is False
    assert config["network_send_attempted"] is False
    assert "zdoc_zbid_preview_only_outbound_not_sent_by_design" in config[
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
        "preview_only",
        "no_write",
        "metadata_only",
        *NO_WRITE_FALSE_FLAGS,
    }
    assert set(payload) == expected_keys
    assert payload["preview_packet"] == packet
    assert payload["validator_result"] == validator_result
    assert "preview_only_is_not_writeback_permission" in payload["blocked_reasons"]
    assert "preview_only_is_not_evidence" in payload["blocked_reasons"]
    assert payload["preview_only"] is True
    assert payload["no_write"] is True
    assert payload["metadata_only"] is True
    _assert_false_flags(payload)


def test_prepare_outbound_is_default_off_and_never_attempts_send():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(env={}),
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
    _assert_false_flags(result["payload"])


def test_prepare_outbound_blocks_missing_endpoint_without_formal_fallback():
    packet, validator_result, blocked_reasons = _safe_outbound_inputs()
    result = prepare_zdoc_zbid_preview_only_outbound(
        preview_packet=packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
        config=build_zdoc_zbid_preview_only_outbound_config(
            env={OUTBOUND_ENABLED_ENV: "1"}
        ),
    )

    assert result["outbound_status"] == "blocked_missing_endpoint"
    assert result["outbound_enabled"] is True
    assert result["endpoint_configured"] is False
    assert result["network_send_attempted"] is False
    assert "zdoc_zbid_preview_only_endpoint_missing" in result["blocked_reasons"]
    _assert_false_flags(result)


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
    assert payload["preview_only"] is True
    assert payload["no_write"] is True
    _assert_false_flags(payload)


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
        assert result["payload"][flag] is False
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


def test_outbound_adapter_imports_do_not_pull_main_chain_or_writeback_modules():
    loaded_modules = set(sys.modules)

    assert not (MAIN_CHAIN_OR_WRITEBACK_MODULES & loaded_modules)


def test_outbound_adapter_source_does_not_import_network_clients_or_formal_modules():
    source = Path(outbound_module.__file__).read_text(encoding="utf-8")

    forbidden_snippets = {
        "orchestrator",
        "llm_client",
        "actions_bridge",
        "zbid_snapshot_mapper",
        "requests",
        "httpx",
        "urllib",
        "socket",
        "subprocess",
        "open(",
        "Path(",
    }
    assert not {snippet for snippet in forbidden_snippets if snippet in source}
