from __future__ import annotations

import copy
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import local_llm_preview_safe


SAFE_PATH = "/local-llm/preview-safe"
FORMAL_RESULT_FIELDS = {
    "content",
    "docx",
    "docx_path",
    "download_url",
    "export_path",
    "generated_sections",
    "job",
    "job_id",
    "json",
    "json_path",
    "markdown",
    "markdown_path",
    "output",
    "output_path",
    "result_path",
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
        "autoplan_jobs": _file_count("backend/data/autoplan/jobs"),
        "build": _file_count("build"),
    }


def _client() -> TestClient:
    return TestClient(app)


def _valid_endpoint_payload() -> dict:
    return {
        "request_id": "safe-preview-1",
        "section_title": "质量保证措施",
        "section_text": "质量控制措施：责任到人，按节点验收。",
        "context_summary": "只做 local LLM preview diagnostics",
    }


def _fake_safe_helper_response() -> dict:
    return {
        "ok": True,
        "enabled": True,
        "status": "ok",
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "source": "fake_safe_helper",
        "entry_type": "safe_service_entry",
        "entry_source": "zdoc_local_llm_preview_safe_service_entry_fake",
        "advisory": "stable safe endpoint advisory",
        "suggestions": ["keep as preview", "do not write outputs"],
        "safety": {
            "preview_only": True,
            "no_write": True,
            "affects_generation": False,
            "affects_export": False,
            "affects_zbid_writeback": False,
        },
    }


def _assert_no_formal_result_fields(result: dict) -> None:
    for field in FORMAL_RESULT_FIELDS:
        assert field not in result


def _assert_safe_endpoint_guard(result: dict) -> None:
    assert result["preview_only"] is True
    assert result["no_write"] is True
    assert result["affects_generation"] is False
    assert result["affects_export"] is False
    assert result["affects_zbid_writeback"] is False
    assert result["source"] == "zdoc_local_llm_preview_isolated_safe_endpoint_fake"
    assert result["entry_type"] == "isolated_safe_endpoint"
    assert result["entry_source"] == "zdoc_local_llm_preview_isolated_safe_endpoint_fake"
    assert result["endpoint_path"] == SAFE_PATH
    assert result["safe_endpoint_registered"] is True
    assert result["service_started"] is False
    assert result["fake_only"] is True
    assert result["calls_generate_route"] is False
    assert result["calls_export_docx_route"] is False
    assert result["calls_review_apply_route"] is False
    assert result["triggers_generation_chain"] is False
    assert result["triggers_export_chain"] is False
    assert result["writes_output"] is False
    assert result["writes_job"] is False
    assert result["writes_export"] is False
    assert result["calls_ollama"] is False
    assert result["calls_external_model_api"] is False
    assert result["safety"]["isolated_safe_endpoint"] is True
    assert result["safety"]["safe_endpoint_registered"] is True
    assert result["safety"]["service_started"] is False
    assert result["safety"]["fake_only"] is True
    assert result["safety"]["preview_only"] is True
    assert result["safety"]["no_write"] is True
    assert result["safety"]["calls_generate_route"] is False
    assert result["safety"]["calls_export_docx_route"] is False
    assert result["safety"]["calls_review_apply_route"] is False
    assert result["safety"]["triggers_generation_chain"] is False
    assert result["safety"]["triggers_export_chain"] is False
    assert result["safety"]["writes_output"] is False
    assert result["safety"]["writes_job"] is False
    assert result["safety"]["writes_export"] is False
    assert result["safety"]["calls_ollama"] is False
    assert result["safety"]["calls_external_model_api"] is False
    assert result["safety"]["downloads_models"] is False
    assert result["safety"]["pulls_models"] is False
    assert result["safety"]["listens_on_0_0_0_0"] is False
    _assert_no_formal_result_fields(result)


def test_safe_endpoint_exists() -> None:
    paths = {getattr(route, "path", "") for route in app.routes}
    assert SAFE_PATH in paths


def test_safe_endpoint_absent_flag_disabled_does_not_call_helper(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()

    def fail_helper(_payload):
        raise AssertionError("safe helper must not be called when endpoint is disabled")

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)

    response = _client().post(SAFE_PATH, json=_valid_endpoint_payload())
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "local_llm_preview_safe_endpoint_disabled"
    assert result["reason"] == "feature_flag_disabled"
    assert result["request_id"] == "safe-preview-1"
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)


@pytest.mark.parametrize("flag_value", ["", "false", "0", "no", "off"])
def test_safe_endpoint_false_flags_disabled_without_helper(monkeypatch, flag_value: str) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", flag_value)
    before_counts = _write_surface_counts()

    def fail_helper(_payload):
        raise AssertionError("safe helper must not be called when endpoint is disabled")

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)

    response = _client().post(SAFE_PATH, json=_valid_endpoint_payload())
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)


def test_safe_endpoint_enabled_calls_fake_only_safe_helper_without_writes(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()
    helper_calls: list[dict] = []
    payload = _valid_endpoint_payload()
    original_payload = copy.deepcopy(payload)

    def fake_helper(helper_payload: dict) -> dict:
        helper_calls.append(copy.deepcopy(helper_payload))
        return _fake_safe_helper_response()

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fake_helper)

    response = _client().post(SAFE_PATH, json=payload)
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["advisory"] == "stable safe endpoint advisory"
    assert result["suggestions"] == ["keep as preview", "do not write outputs"]
    assert result["request_id"] == "safe-preview-1"
    assert helper_calls == [
        {
            "section_title": "质量保证措施",
            "section_text": "质量控制措施：责任到人，按节点验收。",
            "review_focus": "只做 local LLM preview diagnostics",
            "preview_type": "safe_endpoint_preview",
            "source_context": {
                "context_summary": "只做 local LLM preview diagnostics",
                "request_id": "safe-preview-1",
            },
            "trigger": "manual",
            "caller": "isolated_safe_endpoint",
        }
    ]
    assert payload == original_payload
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)


def test_safe_endpoint_enabled_actual_helper_is_fake_only_and_deterministic(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "yes")
    before_counts = _write_surface_counts()
    payload = _valid_endpoint_payload()

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("external model/API transport must not be called")

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)

    first = _client().post(SAFE_PATH, json=payload).json()
    second = _client().post(SAFE_PATH, json=payload).json()

    assert first == second
    assert first["ok"] is True
    assert first["enabled"] is True
    assert first["status"] == "ok"
    assert first["preview_type"] == "safe_endpoint_preview"
    assert first["advisory"].startswith("Fake local LLM preview for 质量保证措施")
    assert len(first["suggestions"]) == 3
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(first)


def test_safe_endpoint_enabled_does_not_call_forbidden_routes_or_chains(monkeypatch) -> None:
    from backend.app.routers import actions_bridge, zhifei_autoplan

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "on")
    before_counts = _write_surface_counts()

    def fake_helper(_helper_payload: dict) -> dict:
        return _fake_safe_helper_response()

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fake_helper)

    forbidden_patches = [
        patch.object(actions_bridge, "actions_generate", side_effect=AssertionError("/actions/generate must not be called")),
        patch.object(actions_bridge, "actions_export_docx", side_effect=AssertionError("/actions/export_docx must not be called")),
        patch.object(actions_bridge, "actions_review_apply", side_effect=AssertionError("/actions/review/apply must not be called")),
        patch.object(zhifei_autoplan, "generate_plan", side_effect=AssertionError("/autoplan/generate must not be called")),
        patch.object(zhifei_autoplan, "export_docx", side_effect=AssertionError("/autoplan/export_docx must not be called")),
    ]

    with ExitStack() as stack:
        for item in forbidden_patches:
            stack.enter_context(item)
        result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is True
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)


@pytest.mark.parametrize(
    ("payload", "error_type", "reason"),
    [
        ({}, "missing_field", "missing_field:section_text"),
        ({**_valid_endpoint_payload(), "section_text": "   "}, "empty_text", "section_text_required"),
        ({**_valid_endpoint_payload(), "generate": True}, "illegal_field", "illegal_field:generate"),
        ({**_valid_endpoint_payload(), "export_docx": True}, "illegal_field", "illegal_field:export_docx"),
        ({**_valid_endpoint_payload(), "review_apply": True}, "illegal_field", "illegal_field:review_apply"),
        ({**_valid_endpoint_payload(), "job_id": "job-1"}, "illegal_field", "illegal_field:job_id"),
        ({**_valid_endpoint_payload(), "output_path": "output/x.json"}, "illegal_field", "illegal_field:output_path"),
    ],
)
def test_safe_endpoint_invalid_inputs_return_stable_failure(monkeypatch, payload: dict, error_type: str, reason: str) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()
    original_payload = copy.deepcopy(payload)

    response = _client().post(SAFE_PATH, json=payload)
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == error_type
    assert result["reason"] == reason
    assert payload == original_payload
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)


def test_safe_endpoint_rejects_formal_helper_fields(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()

    def formal_field_helper(_helper_payload: dict) -> dict:
        result = _fake_safe_helper_response()
        result["docx_path"] = "export/formal.docx"
        return result

    monkeypatch.setattr(
        local_llm_preview_safe,
        "run_zdoc_local_llm_preview_safe_service_entry",
        formal_field_helper,
    )

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == "forbidden_safe_helper_field"
    assert result["reason"] == "forbidden_field:docx_path"
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)
