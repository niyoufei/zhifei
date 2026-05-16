from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.ollama_preview import (
    build_zdoc_local_llm_preview_ui_view,
    run_ollama_preview,
    run_ollama_section_review,
    run_zdoc_ollama_preview,
    run_zdoc_local_llm_preview,
    run_zdoc_local_llm_preview_endpoint_ui_entry,
    run_zdoc_local_llm_preview_safe_service_entry,
    run_zdoc_local_llm_preview_task,
    select_zdoc_local_ollama_model,
)


REAL_TRANSPORT_SOURCE = "zdoc_real_ollama_preview_adapter_real_transport"


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


def _valid_local_preview_payload() -> dict:
    return {
        "section_title": "质量保证措施",
        "section_text": "质量控制措施：责任到人，按节点验收。",
        "review_focus": "缺项、风险和证据支撑",
        "preview_type": "section_review",
    }


def _valid_local_preview_bridge_request() -> dict:
    return {
        **_valid_local_preview_payload(),
        "trigger": "manual",
        "caller": "unit_test",
    }


def _valid_local_preview_endpoint_ui_request() -> dict:
    return {
        **_valid_local_preview_bridge_request(),
        "entry_point": "ui",
        "ui_action": "manual_preview",
    }


def _valid_local_preview_safe_service_request() -> dict:
    return {
        **_valid_local_preview_payload(),
        "trigger": "manual",
        "caller": "safe_service_unit_test",
    }


def _assert_local_preview_guard(result: dict) -> None:
    assert result["preview_only"] is True
    assert result["no_write"] is True
    assert result["affects_generation"] is False
    assert result["affects_export"] is False
    assert result["affects_zbid_writeback"] is False
    assert result["source"] == "zdoc_local_llm_preview_fake"
    assert result["safety"]["preview_only"] is True
    assert result["safety"]["no_write"] is True
    assert result["safety"]["affects_generation"] is False
    assert result["safety"]["affects_export"] is False
    assert result["safety"]["affects_zbid_writeback"] is False


def _assert_local_preview_bridge_guard(result: dict) -> None:
    _assert_local_preview_guard(result)
    assert result["bridge_type"] == "api_task_bridge"
    assert result["bridge_source"] == "zdoc_local_llm_preview_api_task_bridge_fake"
    assert result["safety"]["manual_trigger"] is True
    assert result["safety"]["requires_human_review"] is True


def _assert_local_preview_endpoint_ui_guard(result: dict) -> None:
    _assert_local_preview_bridge_guard(result)
    assert result["entry_type"] == "endpoint_ui_entry"
    assert result["entry_source"] == "zdoc_local_llm_preview_endpoint_ui_entry_fake"
    assert result["endpoint_entry_ready"] is True
    assert result["ui_entry_ready"] is True
    assert result["endpoint_registered"] is False
    assert result["ui_registered"] is False
    assert result["service_started"] is False
    assert result["fake_only"] is True
    assert result["safety"]["endpoint_ui_entry"] is True
    assert result["safety"]["fake_only"] is True
    assert result["safety"]["endpoint_registered"] is False
    assert result["safety"]["ui_registered"] is False
    assert result["safety"]["service_started"] is False


def _assert_local_preview_safe_service_guard(result: dict) -> None:
    _assert_local_preview_bridge_guard(result)
    assert result["entry_type"] == "safe_service_entry"
    assert result["entry_source"] == "zdoc_local_llm_preview_safe_service_entry_fake"
    assert result["safe_service_entry_ready"] is True
    assert result["safe_endpoint_path"] == "/diagnostics/local-llm-preview/safe"
    assert result["safe_endpoint_registered"] is False
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
    assert result["safety"]["safe_service_entry"] is True
    assert result["safety"]["safe_endpoint_isolated"] is True
    assert result["safety"]["safe_endpoint_registered"] is False
    assert result["safety"]["service_started"] is False
    assert result["safety"]["fake_only"] is True
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


def _valid_zdoc_ollama_preview_request() -> dict:
    return {
        "section_title": "质量保证措施",
        "section_text": "质量控制措施：责任到人，按节点验收。",
        "review_focus": "缺项、风险和证据支撑",
        "preview_type": "section_review",
        "context_summary": "施工组织设计技术标章节预览。",
        "request_id": "fake-ollama-preview-1",
    }


def _assert_zdoc_ollama_guard(
    result: dict,
    *,
    calls_ollama: bool = False,
    source: str = "zdoc_real_ollama_preview_adapter_fake_transport",
    fake_transport_only: bool = True,
    real_transport_enabled: bool = False,
) -> None:
    assert result["preview_only"] is True
    assert result["no_write"] is True
    assert result["affects_generation"] is False
    assert result["affects_export"] is False
    assert result["affects_zbid_writeback"] is False
    assert result["source"] == source
    assert result["provider"] == "ollama"
    assert result["base_url"] == "http://127.0.0.1:11434"
    assert result["transport_target"] == "127.0.0.1:11434"
    assert result["fake_transport_only"] is fake_transport_only
    assert result["real_transport_enabled"] is real_transport_enabled
    assert result["calls_ollama"] is calls_ollama
    assert result["calls_external_model_api"] is False
    assert result["downloads_models"] is False
    assert result["pulls_models"] is False
    assert result["writes_output"] is False
    assert result["writes_job"] is False
    assert result["writes_export"] is False
    assert result["triggers_generation_chain"] is False
    assert result["triggers_export_chain"] is False
    assert result["triggers_zbid_writeback"] is False
    assert result["safety"]["preview_only"] is True
    assert result["safety"]["no_write"] is True
    assert result["safety"]["affects_generation"] is False
    assert result["safety"]["affects_export"] is False
    assert result["safety"]["affects_zbid_writeback"] is False
    assert result["safety"]["fake_transport_only"] is fake_transport_only
    assert result["safety"]["real_ollama_runtime"] is real_transport_enabled
    assert result["safety"]["downloads_models"] is False
    assert result["safety"]["pulls_models"] is False


def test_zdoc_local_llm_preview_absent_flag_disabled_does_not_call_fake_client(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)

    def fail_client(_payload):
        raise AssertionError("fake/model client must not be called when disabled")

    result = run_zdoc_local_llm_preview(_valid_local_preview_payload(), fake_client=fail_client)

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "local_llm_preview_disabled"
    assert result["reason"] == "feature_flag_disabled"
    _assert_local_preview_guard(result)


@pytest.mark.parametrize("flag_value", ["", "false", "0", "no", "off"])
def test_zdoc_local_llm_preview_false_flags_disabled(monkeypatch, flag_value: str) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", flag_value)

    def fail_client(_payload):
        raise AssertionError("fake/model client must not be called when disabled")

    result = run_zdoc_local_llm_preview(_valid_local_preview_payload(), fake_client=fail_client)

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    _assert_local_preview_guard(result)


def test_zdoc_local_llm_preview_enabled_returns_fake_preview_without_writes(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()
    payload = _valid_local_preview_payload()

    result = run_zdoc_local_llm_preview(payload)

    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["model"] == "fake-local-llm"
    assert result["preview_type"] == "section_review"
    assert result["advisory"].startswith("Fake local LLM preview for 质量保证措施")
    assert len(result["suggestions"]) == 3
    assert "content" not in result
    assert "docx" not in result
    assert "markdown" not in result
    assert "json" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_local_preview_guard(result)


def test_zdoc_local_llm_preview_enabled_does_not_call_ollama_or_external_api(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "on")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("external model/API transport must not be called")

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)

    result = run_zdoc_local_llm_preview(_valid_local_preview_payload())

    assert result["ok"] is True
    assert result["source"] == "zdoc_local_llm_preview_fake"
    _assert_local_preview_guard(result)


def test_zdoc_local_llm_preview_deterministic_and_does_not_modify_section(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "yes")
    payload = _valid_local_preview_payload()
    original_payload = copy.deepcopy(payload)

    first = run_zdoc_local_llm_preview(payload)
    second = run_zdoc_local_llm_preview(payload)

    assert first == second
    assert payload == original_payload
    assert payload["section_text"] == "质量控制措施：责任到人，按节点验收。"
    assert first["advisory"] != payload["section_text"]
    _assert_local_preview_guard(first)


@pytest.mark.parametrize(
    ("payload", "error_type", "reason"),
    [
        (None, "missing_input", "payload_required"),
        ({"section_title": "质量保证措施"}, "missing_field", "missing_field:section_text"),
        ({**_valid_local_preview_payload(), "section_text": "   "}, "empty_text", "section_text_required"),
        ({**_valid_local_preview_payload(), "export": True}, "illegal_field", "illegal_field:export"),
        ({**_valid_local_preview_payload(), "job": "job-1"}, "illegal_field", "illegal_field:job"),
    ],
)
def test_zdoc_local_llm_preview_invalid_inputs_return_stable_failure(
    monkeypatch,
    payload,
    error_type: str,
    reason: str,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")

    result = run_zdoc_local_llm_preview(payload)

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == error_type
    assert result["reason"] == reason
    assert result["advisory"] == ""
    assert result["suggestions"] == []
    _assert_local_preview_guard(result)


def test_zdoc_local_llm_preview_fake_client_timeout_returns_stable_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")

    def timeout_client(_payload):
        raise TimeoutError("timeout")

    result = run_zdoc_local_llm_preview(_valid_local_preview_payload(), fake_client=timeout_client)

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "fake_client_timeout"
    assert result["reason"] == "fake_client_timeout"
    _assert_local_preview_guard(result)


@pytest.mark.parametrize(
    "fake_response",
    [
        None,
        {},
        {"advisory": "建议", "suggestions": "not-a-list"},
        {"advisory": "", "suggestions": ["建议"]},
        {"advisory": "建议", "suggestions": []},
    ],
)
def test_zdoc_local_llm_preview_invalid_fake_response_returns_stable_failure(
    monkeypatch,
    fake_response,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")

    def fake_client(_payload):
        return fake_response

    result = run_zdoc_local_llm_preview(_valid_local_preview_payload(), fake_client=fake_client)

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_fake_response"
    _assert_local_preview_guard(result)


def test_zdoc_local_llm_preview_task_default_disabled_does_not_call_helper_or_write(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()

    def fail_helper(_payload):
        raise AssertionError("preview helper must not be called when bridge is disabled")

    result = run_zdoc_local_llm_preview_task(_valid_local_preview_bridge_request(), preview_helper=fail_helper)

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "local_llm_preview_api_task_bridge_disabled"
    assert result["reason"] == "feature_flag_disabled"
    assert result["trigger"] == "manual"
    assert result["caller"] == "unit_test"
    assert _write_surface_counts() == before_counts
    _assert_local_preview_bridge_guard(result)


@pytest.mark.parametrize("flag_value", ["", "false", "0", "no", "off"])
def test_zdoc_local_llm_preview_task_false_flags_disabled_without_helper(monkeypatch, flag_value: str) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", flag_value)

    def fail_helper(_payload):
        raise AssertionError("preview helper must not be called when bridge is disabled")

    result = run_zdoc_local_llm_preview_task(_valid_local_preview_bridge_request(), preview_helper=fail_helper)

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    _assert_local_preview_bridge_guard(result)


def test_zdoc_local_llm_preview_task_enabled_calls_fake_helper_without_writes(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()
    request = _valid_local_preview_bridge_request()
    original_request = copy.deepcopy(request)
    helper_calls = []

    def counting_helper(payload):
        helper_calls.append(copy.deepcopy(payload))
        return run_zdoc_local_llm_preview(payload)

    result = run_zdoc_local_llm_preview_task(request, preview_helper=counting_helper)

    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["model"] == "fake-local-llm"
    assert result["preview_type"] == "section_review"
    assert result["trigger"] == "manual"
    assert result["caller"] == "unit_test"
    assert len(result["suggestions"]) == 3
    assert helper_calls == [_valid_local_preview_payload() | {"source_context": {}}]
    assert request == original_request
    assert "content" not in result
    assert "docx" not in result
    assert "markdown" not in result
    assert "json" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_local_preview_bridge_guard(result)


def test_zdoc_local_llm_preview_task_enabled_does_not_call_ollama_or_external_api(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "on")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("external model/API transport must not be called")

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)

    result = run_zdoc_local_llm_preview_task(_valid_local_preview_bridge_request())

    assert result["ok"] is True
    assert result["source"] == "zdoc_local_llm_preview_fake"
    _assert_local_preview_bridge_guard(result)


def test_zdoc_local_llm_preview_task_deterministic_and_does_not_modify_section(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "yes")
    request = _valid_local_preview_bridge_request()
    original_request = copy.deepcopy(request)

    first = run_zdoc_local_llm_preview_task(request)
    second = run_zdoc_local_llm_preview_task(request)

    assert first == second
    assert request == original_request
    assert request["section_text"] == "质量控制措施：责任到人，按节点验收。"
    assert first["advisory"] != request["section_text"]
    _assert_local_preview_bridge_guard(first)


@pytest.mark.parametrize(
    ("bridge_request", "error_type", "reason"),
    [
        (None, "missing_input", "payload_required"),
        ({"section_title": "质量保证措施", "trigger": "manual"}, "missing_field", "missing_field:section_text"),
        ({**_valid_local_preview_bridge_request(), "section_text": "   "}, "empty_text", "section_text_required"),
        ({**_valid_local_preview_bridge_request(), "export": True}, "illegal_field", "illegal_field:export"),
        ({**_valid_local_preview_bridge_request(), "job": "job-1"}, "illegal_field", "illegal_field:job"),
    ],
)
def test_zdoc_local_llm_preview_task_invalid_inputs_return_stable_failure(
    monkeypatch,
    bridge_request,
    error_type: str,
    reason: str,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    result = run_zdoc_local_llm_preview_task(bridge_request)

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == error_type
    assert result["reason"] == reason
    assert result["advisory"] == ""
    assert result["suggestions"] == []
    assert _write_surface_counts() == before_counts
    _assert_local_preview_bridge_guard(result)


def test_zdoc_local_llm_preview_endpoint_ui_absent_flag_disabled_without_bridge(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()

    def fail_bridge(_payload):
        raise AssertionError("endpoint/UI bridge must not be called when disabled")

    result = run_zdoc_local_llm_preview_endpoint_ui_entry(
        _valid_local_preview_endpoint_ui_request(),
        preview_bridge=fail_bridge,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "local_llm_preview_endpoint_ui_entry_disabled"
    assert result["reason"] == "feature_flag_disabled"
    assert result["entry_point"] == "ui"
    assert result["ui_action"] == "manual_preview"
    assert _write_surface_counts() == before_counts
    _assert_local_preview_endpoint_ui_guard(result)


@pytest.mark.parametrize("flag_value", ["", "false", "0", "no", "off"])
def test_zdoc_local_llm_preview_endpoint_ui_false_flags_disabled_without_bridge(
    monkeypatch,
    flag_value: str,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", flag_value)

    def fail_bridge(_payload):
        raise AssertionError("endpoint/UI bridge must not be called when disabled")

    result = run_zdoc_local_llm_preview_endpoint_ui_entry(
        _valid_local_preview_endpoint_ui_request(),
        preview_bridge=fail_bridge,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    _assert_local_preview_endpoint_ui_guard(result)


def test_zdoc_local_llm_preview_endpoint_ui_enabled_calls_fake_bridge_without_writes(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()
    request = _valid_local_preview_endpoint_ui_request()
    original_request = copy.deepcopy(request)
    bridge_calls = []

    def counting_bridge(payload):
        bridge_calls.append(copy.deepcopy(payload))
        return run_zdoc_local_llm_preview_task(payload)

    result = run_zdoc_local_llm_preview_endpoint_ui_entry(request, preview_bridge=counting_bridge)

    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["entry_point"] == "ui"
    assert result["ui_action"] == "manual_preview"
    assert result["advisory"].startswith("Fake local LLM preview for 质量保证措施")
    assert len(result["suggestions"]) == 3
    assert bridge_calls == [_valid_local_preview_bridge_request() | {"source_context": {}}]
    assert request == original_request
    assert "content" not in result
    assert "docx" not in result
    assert "markdown" not in result
    assert "json" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_local_preview_endpoint_ui_guard(result)


def test_zdoc_local_llm_preview_endpoint_ui_enabled_does_not_call_ollama_or_external_api(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "on")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("external model/API transport must not be called")

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)

    result = run_zdoc_local_llm_preview_endpoint_ui_entry(_valid_local_preview_endpoint_ui_request())

    assert result["ok"] is True
    assert result["entry_source"] == "zdoc_local_llm_preview_endpoint_ui_entry_fake"
    _assert_local_preview_endpoint_ui_guard(result)


def test_zdoc_local_llm_preview_endpoint_ui_deterministic_and_does_not_modify_section(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "yes")
    request = _valid_local_preview_endpoint_ui_request()
    original_request = copy.deepcopy(request)

    first = run_zdoc_local_llm_preview_endpoint_ui_entry(request)
    second = run_zdoc_local_llm_preview_endpoint_ui_entry(request)

    assert first == second
    assert request == original_request
    assert request["section_text"] == "质量控制措施：责任到人，按节点验收。"
    assert first["advisory"] != request["section_text"]
    _assert_local_preview_endpoint_ui_guard(first)


@pytest.mark.parametrize(
    ("entry_request", "error_type", "reason"),
    [
        (None, "missing_input", "payload_required"),
        ({"section_title": "质量保证措施", "trigger": "manual"}, "missing_field", "missing_field:section_text"),
        ({**_valid_local_preview_endpoint_ui_request(), "section_text": "   "}, "empty_text", "section_text_required"),
        ({**_valid_local_preview_endpoint_ui_request(), "export": True}, "illegal_field", "illegal_field:export"),
        ({**_valid_local_preview_endpoint_ui_request(), "job": "job-1"}, "illegal_field", "illegal_field:job"),
        ({**_valid_local_preview_endpoint_ui_request(), "trigger": "automatic"}, "invalid_trigger", "manual_trigger_required"),
    ],
)
def test_zdoc_local_llm_preview_endpoint_ui_invalid_inputs_return_stable_failure(
    monkeypatch,
    entry_request,
    error_type: str,
    reason: str,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    result = run_zdoc_local_llm_preview_endpoint_ui_entry(entry_request)

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == error_type
    assert result["reason"] == reason
    assert result["advisory"] == ""
    assert result["suggestions"] == []
    assert _write_surface_counts() == before_counts
    _assert_local_preview_endpoint_ui_guard(result)


def test_zdoc_local_llm_preview_ui_view_is_preview_only_and_no_action(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    result = run_zdoc_local_llm_preview_endpoint_ui_entry(_valid_local_preview_endpoint_ui_request())

    view = build_zdoc_local_llm_preview_ui_view(result)

    assert view["ok"] is True
    assert view["enabled"] is True
    assert view["entry_type"] == "endpoint_ui_entry"
    assert view["entry_source"] == "zdoc_local_llm_preview_endpoint_ui_entry_fake"
    assert view["preview_only"] is True
    assert view["no_write"] is True
    assert view["affects_generation"] is False
    assert view["affects_export"] is False
    assert view["affects_zbid_writeback"] is False
    assert view["display"]["kind"] == "local_llm_preview_diagnostics"
    assert view["display"]["advisory"].startswith("Fake local LLM preview for 质量保证措施")
    assert len(view["display"]["suggestions"]) == 3
    assert view["display"]["actions"] == {
        "can_write_back": False,
        "can_generate": False,
        "can_export": False,
        "can_zbid_writeback": False,
    }


def test_zdoc_local_llm_preview_safe_service_entry_default_disabled_without_bridge(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()

    def fail_bridge(_payload):
        raise AssertionError("safe service bridge must not be called when disabled")

    result = run_zdoc_local_llm_preview_safe_service_entry(
        _valid_local_preview_safe_service_request(),
        preview_bridge=fail_bridge,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "local_llm_preview_safe_service_entry_disabled"
    assert result["reason"] == "feature_flag_disabled"
    assert result["trigger"] == "manual"
    assert result["caller"] == "safe_service_unit_test"
    assert _write_surface_counts() == before_counts
    _assert_local_preview_safe_service_guard(result)


@pytest.mark.parametrize("flag_value", ["", "false", "0", "no", "off"])
def test_zdoc_local_llm_preview_safe_service_entry_false_flags_disabled_without_bridge(
    monkeypatch,
    flag_value: str,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", flag_value)

    def fail_bridge(_payload):
        raise AssertionError("safe service bridge must not be called when disabled")

    result = run_zdoc_local_llm_preview_safe_service_entry(
        _valid_local_preview_safe_service_request(),
        preview_bridge=fail_bridge,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    _assert_local_preview_safe_service_guard(result)


def test_zdoc_local_llm_preview_safe_service_entry_enabled_calls_fake_bridge_without_writes(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()
    request = _valid_local_preview_safe_service_request()
    original_request = copy.deepcopy(request)
    bridge_calls = []

    def counting_bridge(payload):
        bridge_calls.append(copy.deepcopy(payload))
        return run_zdoc_local_llm_preview_task(payload)

    result = run_zdoc_local_llm_preview_safe_service_entry(request, preview_bridge=counting_bridge)

    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["entry_type"] == "safe_service_entry"
    assert result["advisory"].startswith("Fake local LLM preview for 质量保证措施")
    assert len(result["suggestions"]) == 3
    assert bridge_calls == [_valid_local_preview_safe_service_request() | {"source_context": {}}]
    assert request == original_request
    assert "content" not in result
    assert "docx" not in result
    assert "markdown" not in result
    assert "json" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_local_preview_safe_service_guard(result)


def test_zdoc_local_llm_preview_safe_service_entry_enabled_does_not_call_ollama_or_external_api(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "on")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("external model/API transport must not be called")

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)

    result = run_zdoc_local_llm_preview_safe_service_entry(_valid_local_preview_safe_service_request())

    assert result["ok"] is True
    assert result["entry_source"] == "zdoc_local_llm_preview_safe_service_entry_fake"
    _assert_local_preview_safe_service_guard(result)


def test_zdoc_local_llm_preview_safe_service_entry_deterministic_and_does_not_modify_section(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "yes")
    request = _valid_local_preview_safe_service_request()
    original_request = copy.deepcopy(request)

    first = run_zdoc_local_llm_preview_safe_service_entry(request)
    second = run_zdoc_local_llm_preview_safe_service_entry(request)

    assert first == second
    assert request == original_request
    assert request["section_text"] == "质量控制措施：责任到人，按节点验收。"
    assert first["advisory"] != request["section_text"]
    _assert_local_preview_safe_service_guard(first)


@pytest.mark.parametrize(
    ("entry_request", "error_type", "reason"),
    [
        (None, "missing_input", "payload_required"),
        ({"section_title": "质量保证措施", "trigger": "manual"}, "missing_field", "missing_field:section_text"),
        ({**_valid_local_preview_safe_service_request(), "section_text": "   "}, "empty_text", "section_text_required"),
        ({**_valid_local_preview_safe_service_request(), "generate": True}, "illegal_field", "illegal_field:generate"),
        ({**_valid_local_preview_safe_service_request(), "export_docx": True}, "illegal_field", "illegal_field:export_docx"),
        ({**_valid_local_preview_safe_service_request(), "review_apply": True}, "illegal_field", "illegal_field:review_apply"),
        ({**_valid_local_preview_safe_service_request(), "output": "path"}, "illegal_field", "illegal_field:output"),
        ({**_valid_local_preview_safe_service_request(), "job": "job-1"}, "illegal_field", "illegal_field:job"),
        ({**_valid_local_preview_safe_service_request(), "export": True}, "illegal_field", "illegal_field:export"),
        ({**_valid_local_preview_safe_service_request(), "trigger": "automatic"}, "invalid_trigger", "manual_trigger_required"),
    ],
)
def test_zdoc_local_llm_preview_safe_service_entry_invalid_inputs_return_stable_failure(
    monkeypatch,
    entry_request,
    error_type: str,
    reason: str,
) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    result = run_zdoc_local_llm_preview_safe_service_entry(entry_request)

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == error_type
    assert result["reason"] == reason
    assert result["advisory"] == ""
    assert result["suggestions"] == []
    assert _write_surface_counts() == before_counts
    _assert_local_preview_safe_service_guard(result)


def test_zdoc_local_llm_preview_safe_service_entry_rejects_formal_bridge_fields(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "1")
    before_counts = _write_surface_counts()

    def invalid_bridge(payload):
        result = run_zdoc_local_llm_preview_task(payload)
        result["job_id"] = "formal-job-1"
        result["export_path"] = "export/formal.docx"
        return result

    result = run_zdoc_local_llm_preview_safe_service_entry(
        _valid_local_preview_safe_service_request(),
        preview_bridge=invalid_bridge,
    )

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == "forbidden_safe_service_bridge_field"
    assert result["reason"] == "forbidden_field:export_path"
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_local_preview_safe_service_guard(result)


def test_zdoc_ollama_preview_total_flag_absent_disabled_without_transport(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    def fail_builder(*_args, **_kwargs):
        raise AssertionError("default transport builder must not be called when total flag is disabled")

    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fail_builder)

    result = run_zdoc_ollama_preview(_valid_zdoc_ollama_preview_request())

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["adapter_enabled"] is False
    assert result["status"] == "disabled"
    assert result["error_type"] == "ollama_preview_disabled"
    assert result["reason"] == "preview_feature_flag_disabled"
    assert _write_surface_counts() == before_counts
    _assert_zdoc_ollama_guard(result)


@pytest.mark.parametrize("flag_value", ["false", "0", "no", "off"])
def test_zdoc_ollama_preview_total_false_flags_disabled_without_transport(monkeypatch, flag_value: str) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", flag_value)
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fail_transport(*_args, **_kwargs):
        raise AssertionError("adapter transport must not be called when total flag is disabled")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fail_transport,
        generate_transport=fail_transport,
    )

    assert result["ok"] is False
    assert result["status"] == "disabled"
    assert result["enabled"] is False
    assert result["adapter_enabled"] is False
    _assert_zdoc_ollama_guard(result)


def test_zdoc_ollama_preview_adapter_flag_absent_disabled_without_transport(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.delenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", raising=False)

    def fail_builder(*_args, **_kwargs):
        raise AssertionError("default transport builder must not be called when adapter flag is disabled")

    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fail_builder)

    result = run_zdoc_ollama_preview(_valid_zdoc_ollama_preview_request())

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["adapter_enabled"] is False
    assert result["status"] == "disabled"
    assert result["error_type"] == "ollama_preview_disabled"
    assert result["reason"] == "adapter_feature_flag_disabled"
    _assert_zdoc_ollama_guard(result)


def test_zdoc_ollama_preview_requested_model_missing_does_not_generate_or_pull(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "missing-model:latest")
    generate_calls = []

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        generate_calls.append(True)
        raise AssertionError("generate must not be called when requested model is unavailable")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "model_unavailable"
    assert result["reason"] == "requested_model_unavailable"
    assert result["model"] == "missing-model:latest"
    assert generate_calls == []
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


@pytest.mark.parametrize("flag_value", ["false", "0", "no", "off"])
def test_zdoc_ollama_preview_adapter_false_flags_disabled_without_transport(monkeypatch, flag_value: str) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", flag_value)

    def fail_transport(*_args, **_kwargs):
        raise AssertionError("adapter transport must not be called when adapter flag is disabled")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fail_transport,
        generate_transport=fail_transport,
    )

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["adapter_enabled"] is False
    assert result["status"] == "disabled"
    _assert_zdoc_ollama_guard(result)


def test_zdoc_ollama_preview_selects_model_from_fake_tags(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_OLLAMA_PREVIEW_MODEL", raising=False)
    seen = {}

    def fake_tags(url, payload, timeout):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"models": [{"name": "qwen3:0.6b"}, {"name": "llama3.2:latest"}]}

    result = select_zdoc_local_ollama_model(tags_transport=fake_tags, timeout=2)

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["model"] == "qwen3:0.6b"
    assert result["selection_only"] is True
    assert seen == {"url": "http://127.0.0.1:11434/api/tags", "payload": {}, "timeout": 2.0}
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_tags_empty_returns_model_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    generate_calls = []

    def fake_tags(_url, _payload, _timeout):
        return {"models": []}

    def fake_generate(*_args, **_kwargs):
        generate_calls.append(True)
        raise AssertionError("generate must not be called when no model is available")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "model_unavailable"
    assert result["reason"] == "no_local_ollama_models"
    assert generate_calls == []
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_tags_unreachable_returns_stable_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(*_args, **_kwargs):
        raise OSError("fake client unavailable")

    def fake_generate(*_args, **_kwargs):
        raise AssertionError("generate must not be called when tags are unavailable")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "ollama_unreachable"
    assert result["reason"] == "tags_unreachable"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_success_is_preview_only(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()
    request = _valid_zdoc_ollama_preview_request()
    original_request = copy.deepcopy(request)
    seen = {}

    def fake_tags(url, payload, timeout):
        seen["tags_url"] = url
        seen["tags_payload"] = payload
        seen["tags_timeout"] = timeout
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(url, payload, timeout):
        seen["generate_url"] = url
        seen["generate_payload"] = copy.deepcopy(payload)
        seen["generate_timeout"] = timeout
        return {"response": "建议补充质量验收记录。\n建议明确责任闭环。"}

    first = run_zdoc_ollama_preview(
        request,
        tags_transport=fake_tags,
        generate_transport=fake_generate,
        timeout=3,
        num_predict=128,
    )
    second = run_zdoc_ollama_preview(
        request,
        tags_transport=fake_tags,
        generate_transport=fake_generate,
        timeout=3,
        num_predict=128,
    )

    assert first == second
    assert first["ok"] is True
    assert first["status"] == "ok"
    assert first["enabled"] is True
    assert first["adapter_enabled"] is True
    assert first["model"] == "qwen3:0.6b"
    assert first["advisory"] == "建议补充质量验收记录。\n建议明确责任闭环。"
    assert first["suggestions"] == ["建议补充质量验收记录。", "建议明确责任闭环。"]
    assert first["quality_status"] == "preview_ok"
    assert first["quality_gate"]["quality_status"] == "preview_ok"
    assert first["formal_generation_allowed"] is False
    assert first["shadow_candidate_allowed"] is False
    assert first["writeback_allowed"] is False
    assert first["export_allowed"] is False
    assert first["zbid_writeback_allowed"] is False
    assert "content" not in first
    assert "docx" not in first
    assert "markdown" not in first
    assert "json" not in first
    assert "job_id" not in first
    assert "export_path" not in first
    assert seen["tags_url"] == "http://127.0.0.1:11434/api/tags"
    assert seen["generate_url"] == "http://127.0.0.1:11434/api/generate"
    assert seen["generate_payload"]["model"] == "qwen3:0.6b"
    assert seen["generate_payload"]["stream"] is False
    assert seen["generate_payload"]["options"]["num_predict"] == 128
    assert seen["generate_url"] != "http://127.0.0.1:11434/generate"
    assert seen["generate_url"] != "http://127.0.0.1:11434/export_docx"
    assert seen["generate_url"] != "http://127.0.0.1:11434/review/apply"
    assert request == original_request
    assert _write_surface_counts() == before_counts
    _assert_zdoc_ollama_guard(first, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_timeout_returns_stable_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        raise TimeoutError("fake timeout")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "timeout"
    assert result["reason"] == "generate_timeout"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_empty_response_returns_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "   "}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_response"
    assert result["reason"] == "empty_response_and_thinking"
    assert result["advisory"] == ""
    assert result["suggestions"] == []
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_thinking_only_is_bounded_preview(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    thinking_only = "<think>" + ("只做推理预览。" * 300)

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": thinking_only}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "thinking_only_fallback"
    assert result["content_source"] == "thinking"
    assert result["advisory"].startswith("模型仅返回推理预览内容")
    assert len(result["advisory"]) <= 1200
    assert result["advisory"] != thinking_only
    assert result["risk_notes"] == ["thinking_only_fallback"]
    assert result["quality_status"] == "review_required"
    assert result["shadow_candidate_allowed"] is False
    assert "thinking_only_fallback_review_required" in result["review_reasons"]
    assert "content" not in result
    assert "docx" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_json_text_extracts_bounded_advisory(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {
            "response": json.dumps(
                {
                    "advisory": "建议补充材料验收记录。",
                    "suggestions": ["建议一", "建议二", "建议三", "建议四"],
                    "risk_notes": ["风险一", "风险二", "风险三", "风险四"],
                },
                ensure_ascii=False,
            )
        }

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "structured_json"
    assert result["content_source"] == "response"
    assert result["advisory"] == "建议补充材料验收记录。"
    assert result["suggestions"] == ["建议一", "建议二", "建议三"]
    assert result["risk_notes"] == ["风险一", "风险二", "风险三"]
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_non_json_text_is_advisory(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "技术建议：补充隐蔽验收记录，并明确整改闭环。"}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "text_fallback"
    assert result["content_source"] == "response"
    assert result["advisory"] == "技术建议：补充隐蔽验收记录，并明确整改闭环。"
    assert result["suggestions"] == ["技术建议：补充隐蔽验收记录，并明确整改闭环。"]
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_empty_response_with_thinking_uses_bounded_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    thinking = "分析：" + ("只做预览推理，不写正式正文。" * 120)

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "", "thinking": thinking}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "thinking_only_fallback"
    assert result["content_source"] == "thinking"
    assert result["advisory"].startswith("模型仅返回推理预览内容")
    assert len(result["advisory"]) <= 1200
    assert result["advisory"] != thinking
    assert result["risk_notes"] == ["thinking_only_fallback"]
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_message_content_is_advisory(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"message": {"content": "需补充检验批验收频次。"}}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["content_source"] == "message.content"
    assert result["advisory"] == "需补充检验批验收频次。"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_long_text_is_bounded(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    long_text = "建议补充质量记录。" * 200

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": long_text}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert len(result["advisory"]) <= 1200
    assert result["advisory"] != long_text
    assert len(result["suggestions"]) <= 3
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_missing_json_advisory_is_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": json.dumps({"suggestions": ["建议一"]}, ensure_ascii=False)}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_response"
    assert result["reason"] == "missing_preview_advisory"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_malformed_json_is_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "{\"advisory\": "}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_response"
    assert result["reason"] == "malformed_json"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_normalization_exception_is_controlled_failure(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "建议补充质量记录。"}

    def fail_extract(_raw_response):
        raise RuntimeError("normalizer exploded")

    monkeypatch.setattr(preview_module, "_extract_zdoc_ollama_advisory_payload", fail_extract)

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_response"
    assert result["reason"] == "normalization_failure"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_invalid_json_returns_stable_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        raise ValueError("invalid json")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_response"
    assert result["reason"] == "generate_invalid_response"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_generate_error_field_returns_stable_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"error": "model not found"}

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "transport_failure"
    assert result["reason"] == "ollama_error"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_fake_transport_failure_returns_stable_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        raise RuntimeError("fake transport failed")

    result = run_zdoc_ollama_preview(
        _valid_zdoc_ollama_preview_request(),
        tags_transport=fake_tags,
        generate_transport=fake_generate,
    )

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "transport_failure"
    assert result["reason"] == "generate_transport_failure"
    _assert_zdoc_ollama_guard(result, calls_ollama=True)


def test_zdoc_ollama_preview_no_injected_transport_uses_default_builder_fake_success(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "qwen3:0.6b")
    seen = {}

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("real 127.0.0.1:11434 access must not happen in deterministic tests")

    def fake_tags(url, payload, timeout):
        seen["tags_url"] = url
        seen["tags_payload"] = payload
        seen["tags_timeout"] = timeout
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(url, payload, timeout):
        seen["generate_url"] = url
        seen["generate_payload"] = copy.deepcopy(payload)
        seen["generate_timeout"] = timeout
        return {"response": "默认 real transport builder fake 替身建议。"}

    def fake_builder(*, base_url=None):
        seen["builder_base_url"] = base_url
        return fake_tags, fake_generate

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)
    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fake_builder)

    result = run_zdoc_ollama_preview(_valid_zdoc_ollama_preview_request())

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["model"] == "qwen3:0.6b"
    assert result["advisory"] == "默认 real transport builder fake 替身建议。"
    assert seen["builder_base_url"] == "http://127.0.0.1:11434"
    assert seen["tags_url"] == "http://127.0.0.1:11434/api/tags"
    assert seen["tags_payload"] == {}
    assert seen["generate_url"] == "http://127.0.0.1:11434/api/generate"
    assert seen["generate_payload"]["model"] == "qwen3:0.6b"
    assert result["reason"] is None
    _assert_zdoc_ollama_guard(
        result,
        calls_ollama=True,
        source=REAL_TRANSPORT_SOURCE,
        fake_transport_only=False,
        real_transport_enabled=True,
    )


def test_zdoc_ollama_preview_default_builder_tags_missing_model_controlled_failure(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "missing-model:latest")
    generate_calls = []

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        generate_calls.append(True)
        raise AssertionError("generate must not be called for a missing model")

    def fake_builder(*, base_url=None):
        assert base_url == "http://127.0.0.1:11434"
        return fake_tags, fake_generate

    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fake_builder)

    result = run_zdoc_ollama_preview(_valid_zdoc_ollama_preview_request())

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "model_unavailable"
    assert result["reason"] == "requested_model_unavailable"
    assert result["model"] == "missing-model:latest"
    assert generate_calls == []
    _assert_zdoc_ollama_guard(
        result,
        calls_ollama=True,
        source=REAL_TRANSPORT_SOURCE,
        fake_transport_only=False,
        real_transport_enabled=True,
    )


def test_zdoc_ollama_preview_default_builder_init_exception_controlled_failure(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def failing_builder(*, base_url=None):
        assert base_url == "http://127.0.0.1:11434"
        raise RuntimeError("builder unavailable")

    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", failing_builder)

    result = run_zdoc_ollama_preview(_valid_zdoc_ollama_preview_request())

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "transport_failure"
    assert result["reason"] == "default_transport_builder_failure"
    _assert_zdoc_ollama_guard(
        result,
        source=REAL_TRANSPORT_SOURCE,
        fake_transport_only=False,
        real_transport_enabled=True,
    )


def test_zdoc_ollama_preview_default_builder_generate_exception_controlled_failure(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        raise RuntimeError("fake builder generate failure")

    def fake_builder(*, base_url=None):
        assert base_url == "http://127.0.0.1:11434"
        return fake_tags, fake_generate

    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fake_builder)

    result = run_zdoc_ollama_preview(_valid_zdoc_ollama_preview_request())

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "transport_failure"
    assert result["reason"] == "generate_transport_failure"
    _assert_zdoc_ollama_guard(
        result,
        calls_ollama=True,
        source=REAL_TRANSPORT_SOURCE,
        fake_transport_only=False,
        real_transport_enabled=True,
    )


def test_ollama_preview_disabled_does_not_call_network(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_OLLAMA_PREVIEW_ENABLED", raising=False)

    def fail_transport(*_args, **_kwargs):
        raise AssertionError("network should not be called when preview is disabled")

    result = run_ollama_preview(
        content="施工部署章节内容",
        transport=fail_transport,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "ollama_preview_disabled"


def test_ollama_preview_enabled_success_uses_api_chat(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")
    seen: dict = {}

    def fake_transport(url, payload, timeout):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"model": "qwen3:0.6b", "message": {"content": "缺项：需补充验收频次。"}}

    result = run_ollama_preview(
        content="质量控制措施：责任到人。",
        section_title="质量保证措施",
        instruction="只做缺项检查",
        transport=fake_transport,
    )

    assert result["ok"] is True
    assert result["content"] == "缺项：需补充验收频次。"
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["think"] is False
    assert seen["payload"]["messages"][0]["role"] == "user"
    assert seen["timeout"] == 60.0


def test_ollama_preview_enabled_timeout_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")

    def timeout_transport(*_args, **_kwargs):
        raise TimeoutError("timeout")

    result = run_ollama_preview(
        content="安全文明施工章节",
        timeout=2,
        transport=timeout_transport,
    )

    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "fallback"
    assert result["error"] == "ollama_preview_timeout"
    assert result["fallback"]["available"] is True


def test_ollama_preview_enabled_exception_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")

    def error_transport(*_args, **_kwargs):
        raise RuntimeError("model not found")

    result = run_ollama_preview(
        content="进度计划章节",
        transport=error_transport,
    )

    assert result["ok"] is False
    assert result["status"] == "fallback"
    assert result["error"] == "ollama_preview_error:RuntimeError"


def test_ollama_section_review_disabled_does_not_call_network(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_OLLAMA_PREVIEW_ENABLED", raising=False)

    def fail_transport(*_args, **_kwargs):
        raise AssertionError("network should not be called when section review is disabled")

    result = run_ollama_section_review(
        project_name="厂房项目",
        section_title="质量保证措施",
        section_content="质量控制措施：责任到人。",
        transport=fail_transport,
    )

    assert result["ok"] is False
    assert result["enabled"] is False
    assert result["status"] == "disabled"
    assert result["warning"] == "ollama_preview_disabled"
    assert result["review_type"] == "section_review"
    assert result["fallback_reason"] == "ollama_preview_disabled"


def test_ollama_section_review_enabled_success_returns_review_type(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")
    seen: dict = {}

    def fake_transport(url, payload, timeout):
        seen["url"] = url
        seen["payload"] = payload
        seen["timeout"] = timeout
        return {"model": "qwen3:0.6b", "message": {"content": "缺项：需补充验收记录。"}}

    result = run_ollama_section_review(
        project_name="厂房项目",
        section_title="质量保证措施",
        section_content="质量控制措施：责任到人。",
        review_focus="验收记录和责任闭环",
        transport=fake_transport,
    )

    prompt = seen["payload"]["messages"][0]["content"]
    assert result["ok"] is True
    assert result["review_type"] == "section_review"
    assert result["fallback_reason"] is None
    assert result["content"] == "缺项：需补充验收记录。"
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert "人工章节复核助手" in prompt
    assert "厂房项目" in prompt
    assert "质量保证措施" in prompt
    assert "验收记录和责任闭环" in prompt


def test_ollama_section_review_enabled_exception_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")

    def error_transport(*_args, **_kwargs):
        raise RuntimeError("model not found")

    result = run_ollama_section_review(
        project_name="厂房项目",
        section_title="进度计划",
        section_content="进度计划章节。",
        transport=error_transport,
    )

    assert result["ok"] is False
    assert result["status"] == "fallback"
    assert result["review_type"] == "section_review"
    assert result["fallback_reason"] == "ollama_preview_error:RuntimeError"


def test_ollama_section_review_enabled_empty_content_returns_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_ENABLED", "1")

    def fail_transport(*_args, **_kwargs):
        raise AssertionError("network should not be called for empty section content")

    result = run_ollama_section_review(
        project_name="厂房项目",
        section_title="进度计划",
        section_content="",
        transport=fail_transport,
    )

    assert result["ok"] is False
    assert result["status"] == "empty_content"
    assert result["review_type"] == "section_review"
    assert result["fallback_reason"] == "content_required"
