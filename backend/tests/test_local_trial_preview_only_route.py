from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.routers import local_trial_preview_only


ROUTE_PATH = "/local-trial/preview-only"
FORMAL_FLAGS = {
    "formal_writeback_allowed",
    "review_apply_allowed",
    "docx_export_allowed",
    "zbid_writeback_allowed",
    "output_write_allowed",
}
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


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(local_trial_preview_only.router)
    return TestClient(app)


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


def _safe_payload(**overrides) -> dict:
    payload = {
        "integration_request_id": "local-trial-preview-only-1",
        "source_system": "zdoc",
        "target_system": "zbid",
        "project_id": "project-local-trial",
        "document_id": "doc-local-trial",
        "section_id": "section-local-trial",
        "section_title": "Local Trial Preview Only Section",
        "section_hash": "sha256:local-trial-section",
        "section_version": "v1",
        "tender_file_refs": ["tender:file:001"],
        "scoring_clause_refs": ["tender:scoring-clause:001"],
        "evidence_anchor_refs": ["tender:evidence-anchor:001"],
        "evidence_anchor_status": "source_verified",
        "evidence_binding_status": "bound_to_source_verified_evidence",
        "response_mode": "preview_advisory",
        "input_risk_level": "low",
        "advisory_quality_gate_status": "preview_ok",
        "preview_advisory_summary": "Fake local trial preview-only advisory.",
        "generated_at": "2026-01-01T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _assert_no_write_route_flags(result: dict) -> None:
    assert result["preview_only"] is True
    assert result["no_write"] is True
    assert result["route_name"] == "local_trial_preview_only"
    assert result["endpoint_path"] == ROUTE_PATH
    assert result["calls_generate_route"] is False
    assert result["calls_export_docx_route"] is False
    assert result["calls_review_apply_route"] is False
    assert result["affects_zbid_writeback"] is False
    assert result["writes_output"] is False
    assert result["writes_job"] is False
    assert result["writes_export"] is False
    assert result["calls_ollama"] is False
    assert result["calls_external_model_api"] is False
    assert result["downloads_models"] is False
    assert result["pulls_models"] is False
    for flag in FORMAL_FLAGS:
        assert result[flag] is False


def _assert_formal_flags_false(container: dict) -> None:
    for flag in FORMAL_FLAGS:
        assert container[flag] is False


def test_local_trial_preview_only_route_returns_200_and_metadata_only_result():
    before_counts = _write_surface_counts()

    response = _client().post(ROUTE_PATH, json=_safe_payload())
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is True
    _assert_no_write_route_flags(result)
    assert isinstance(result["preview_packet"], dict)
    assert isinstance(result["validator_result"], dict)
    assert isinstance(result["blocked_reasons"], list)
    assert "preview_only_is_not_writeback_permission" in result["blocked_reasons"]
    assert "preview_only_is_not_evidence" in result["blocked_reasons"]
    assert result["preview_packet"]["zbid_input_status"] == "accepted_preview_only"
    assert result["validator_result"]["zbid_preview_validation_status"] == "accepted_preview_only"
    _assert_formal_flags_false(result["preview_packet"])
    _assert_formal_flags_false(result["validator_result"])
    assert _write_surface_counts() == before_counts


def test_local_trial_preview_only_route_returns_false_formal_flags_everywhere():
    result = _client().post(ROUTE_PATH, json=_safe_payload()).json()

    for container in (result, result["preview_packet"], result["validator_result"]):
        _assert_formal_flags_false(container)


def test_local_trial_preview_only_route_blocks_missing_scoring_refs_without_writes():
    before_counts = _write_surface_counts()

    response = _client().post(ROUTE_PATH, json=_safe_payload(scoring_clause_refs=[]))
    result = response.json()

    assert response.status_code == 200
    _assert_no_write_route_flags(result)
    assert "missing_scoring_clause_refs" in result["blocked_reasons"]
    assert result["preview_packet"]["zbid_input_status"] == "blocked"
    assert result["validator_result"]["zbid_preview_validation_status"] == "blocked"
    assert _write_surface_counts() == before_counts


def test_local_trial_preview_only_route_blocks_unsafe_evidence_without_writes():
    before_counts = _write_surface_counts()

    response = _client().post(
        ROUTE_PATH,
        json=_safe_payload(generated_advisory_used_as_evidence=True),
    )
    result = response.json()

    assert response.status_code == 200
    _assert_no_write_route_flags(result)
    assert "generated_advisory_cannot_be_evidence" in result["blocked_reasons"]
    assert result["preview_packet"]["zbid_input_status"] == "blocked"
    assert result["validator_result"]["zbid_preview_validation_status"] == "blocked"
    assert _write_surface_counts() == before_counts


def test_local_trial_preview_only_route_blocks_formal_requests_without_triggering_chains():
    result = _client().post(
        ROUTE_PATH,
        json=_safe_payload(
            zbid_writeback_requested=True,
            docx_export_requested=True,
            review_apply_requested=True,
            formal_writeback_requested=True,
            output_write_requested=True,
        ),
    ).json()

    _assert_no_write_route_flags(result)
    for reason in {
        "zbid_writeback_request_blocked",
        "docx_export_request_blocked",
        "review_apply_request_blocked",
        "formal_writeback_request_blocked",
        "output_write_request_blocked",
    }:
        assert reason in result["blocked_reasons"]


def test_local_trial_preview_only_route_module_does_not_import_main_chain_or_writeback_modules():
    loaded_modules = set(sys.modules)

    assert not (MAIN_CHAIN_OR_WRITEBACK_MODULES & loaded_modules)


def test_local_trial_preview_only_route_source_does_not_call_formal_routes_or_zbid_writeback():
    source = Path(local_trial_preview_only.__file__).read_text(encoding="utf-8")

    forbidden_snippets = {
        "orchestrator",
        "llm_client",
        "actions_bridge",
        "export_docx(",
        "review_apply(",
        "zbid_snapshot_mapper",
        "writeback(",
        "requests.",
        "httpx.",
    }
    assert not {snippet for snippet in forbidden_snippets if snippet in source}
