from __future__ import annotations

import copy
import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import local_llm_preview_safe


SAFE_PATH = "/local-llm/preview-safe"
REAL_ADAPTER_SOURCE = "zdoc_real_ollama_preview_adapter_fake_transport"
REAL_RUNTIME_ADAPTER_SOURCE = "zdoc_real_ollama_preview_adapter_real_transport"
REAL_ADAPTER_ENTRY_SOURCE = "zdoc_local_llm_preview_isolated_safe_endpoint_real_ollama_adapter"
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


def _assert_safe_endpoint_guard(
    result: dict,
    *,
    source: str = "zdoc_local_llm_preview_isolated_safe_endpoint_fake",
    entry_source: str = "zdoc_local_llm_preview_isolated_safe_endpoint_fake",
    fake_only: bool = True,
    calls_ollama: bool = False,
) -> None:
    assert result["preview_only"] is True
    assert result["no_write"] is True
    assert result["affects_generation"] is False
    assert result["affects_export"] is False
    assert result["affects_zbid_writeback"] is False
    assert result["source"] == source
    assert result["entry_type"] == "isolated_safe_endpoint"
    assert result["entry_source"] == entry_source
    assert result["endpoint_path"] == SAFE_PATH
    assert result["safe_endpoint_registered"] is True
    assert result["service_started"] is False
    assert result["fake_only"] is fake_only
    assert result["real_adapter_bridge"] is (not fake_only)
    assert result["calls_generate_route"] is False
    assert result["calls_export_docx_route"] is False
    assert result["calls_review_apply_route"] is False
    assert result["triggers_generation_chain"] is False
    assert result["triggers_export_chain"] is False
    assert result["writes_output"] is False
    assert result["writes_job"] is False
    assert result["writes_export"] is False
    assert result["calls_ollama"] is calls_ollama
    assert result["calls_external_model_api"] is False
    assert result["safety"]["isolated_safe_endpoint"] is True
    assert result["safety"]["safe_endpoint_registered"] is True
    assert result["safety"]["service_started"] is False
    assert result["safety"]["fake_only"] is fake_only
    assert result["safety"]["real_adapter_bridge"] is (not fake_only)
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
    assert result["safety"]["calls_ollama"] is calls_ollama
    assert result["safety"]["calls_external_model_api"] is False
    assert result["safety"]["downloads_models"] is False
    assert result["safety"]["pulls_models"] is False
    assert result["safety"]["listens_on_0_0_0_0"] is False
    _assert_no_formal_result_fields(result)


def _assert_safe_endpoint_prompt_metadata(result: dict, prompt_mode: str) -> None:
    assert result["prompt_mode"] == prompt_mode
    assert result["prompt_profile"] == "second_round_response_mode_tuning"
    assert result["prompt_version"] == "zdoc_response_mode_prompt_v2"
    assert result["prompt_tuning_applied"] is True
    assert isinstance(result["prompt_tuning_warnings"], list)
    assert result["json_mode_requested"] is (prompt_mode == "json_first")
    assert result["response_first_requested"] is (prompt_mode == "response_first")
    assert result["text_fallback_allowed"] is True
    assert result["evidence_aware_prompt_applied"] is True
    assert result["adapter_schema_mode"] == "compatible"


def test_safe_endpoint_exists() -> None:
    paths = {getattr(route, "path", "") for route in app.routes}
    assert SAFE_PATH in paths


def test_safe_endpoint_absent_flag_disabled_does_not_call_helper(monkeypatch) -> None:
    monkeypatch.delenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()

    def fail_helper(_payload):
        raise AssertionError("safe helper must not be called when endpoint is disabled")

    def fail_adapter(_payload):
        raise AssertionError("real adapter must not be called when endpoint is disabled")

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "_run_ollama_adapter_bridge", fail_adapter)

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

    def fail_adapter(_payload):
        raise AssertionError("real adapter must not be called when endpoint is disabled")

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "_run_ollama_adapter_bridge", fail_adapter)

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
    monkeypatch.delenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()
    helper_calls: list[dict] = []
    payload = _valid_endpoint_payload()
    original_payload = copy.deepcopy(payload)

    def fake_helper(helper_payload: dict) -> dict:
        helper_calls.append(copy.deepcopy(helper_payload))
        return _fake_safe_helper_response()

    def fail_adapter(_payload):
        raise AssertionError("real adapter must not be called when adapter flag is disabled")

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fake_helper)
    monkeypatch.setattr(local_llm_preview_safe, "_run_ollama_adapter_bridge", fail_adapter)

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


def test_safe_endpoint_adapter_off_illegal_content_field_is_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.delenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", raising=False)
    before_counts = _write_surface_counts()
    payload = {**_valid_endpoint_payload(), "content": "literal formal content must be rejected"}
    original_payload = copy.deepcopy(payload)

    def fail_helper(_payload):
        raise AssertionError("safe helper must not be called for illegal adapter-off payload")

    def fail_adapter(_payload):
        raise AssertionError("real adapter must not be called when adapter flag is disabled")

    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "_run_ollama_adapter_bridge", fail_adapter)

    response = _client().post(SAFE_PATH, json=payload)
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is False
    assert result["enabled"] is True
    assert result["status"] == "failure"
    assert result["error_type"] == "illegal_field"
    assert result["reason"] == "illegal_field:content"
    assert payload == original_payload
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(result)


def test_safe_endpoint_double_flags_calls_fake_ollama_adapter_generate_without_writes(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "qwen3:0.6b")
    before_counts = _write_surface_counts()
    seen = {}

    def fail_helper(_payload):
        raise AssertionError("safe fake helper must not be called when adapter flag is enabled")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("real 127.0.0.1:11434 access must not happen in deterministic tests")

    def fake_tags(url, payload, timeout):
        seen["tags_url"] = url
        seen["tags_payload"] = copy.deepcopy(payload)
        seen["tags_timeout"] = timeout
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(url, payload, timeout):
        seen["generate_url"] = url
        seen["generate_payload"] = copy.deepcopy(payload)
        seen["generate_timeout"] = timeout
        return {"response": "建议补充质量验收记录。\n建议明确责任闭环。"}

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)
    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    response = _client().post(SAFE_PATH, json=_valid_endpoint_payload())
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["model"] == "qwen3:0.6b"
    assert result["advisory"] == "建议补充质量验收记录。\n建议明确责任闭环。"
    assert result["suggestions"] == ["建议补充质量验收记录。", "建议明确责任闭环。"]
    assert result["fake_transport_only"] is True
    assert result["real_adapter_bridge"] is True
    assert seen["tags_url"] == "http://127.0.0.1:11434/api/tags"
    assert seen["tags_payload"] == {}
    assert seen["generate_url"] == "http://127.0.0.1:11434/api/generate"
    assert seen["generate_payload"]["model"] == "qwen3:0.6b"
    assert seen["generate_payload"]["stream"] is False
    assert seen["generate_url"] != "http://127.0.0.1:11434/generate"
    assert seen["generate_url"] != "http://127.0.0.1:11434/export_docx"
    assert seen["generate_url"] != "http://127.0.0.1:11434/review/apply"
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_no_injected_transport_uses_default_builder_fake_substitute(
    monkeypatch,
) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "qwen3:0.6b")
    before_counts = _write_surface_counts()
    seen = {}

    def fail_helper(_payload):
        raise AssertionError("safe fake helper must not be called when adapter flag is enabled")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("real 127.0.0.1:11434 access must not happen in deterministic tests")

    def fake_tags(url, payload, timeout):
        seen["tags_url"] = url
        seen["tags_payload"] = copy.deepcopy(payload)
        seen["tags_timeout"] = timeout
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(url, payload, timeout):
        seen["generate_url"] = url
        seen["generate_payload"] = copy.deepcopy(payload)
        seen["generate_timeout"] = timeout
        return {"response": "default builder fake transport advisory"}

    def fake_builder(*, base_url=None):
        seen["builder_base_url"] = base_url
        return fake_tags, fake_generate

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)
    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fake_builder)
    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", None)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", None)

    response = _client().post(SAFE_PATH, json=_valid_endpoint_payload())
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is True
    assert result["enabled"] is True
    assert result["status"] == "ok"
    assert result["model"] == "qwen3:0.6b"
    assert result["advisory"] == "default builder fake transport advisory"
    assert result["real_transport_enabled"] is True
    assert result["fake_transport_only"] is False
    assert seen["builder_base_url"] == "http://127.0.0.1:11434"
    assert seen["tags_url"] == "http://127.0.0.1:11434/api/tags"
    assert seen["tags_payload"] == {}
    assert seen["generate_url"] == "http://127.0.0.1:11434/api/generate"
    assert seen["generate_payload"]["model"] == "qwen3:0.6b"
    assert seen["generate_payload"]["stream"] is False
    assert "content" not in result
    assert "docx" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_RUNTIME_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_preserves_input_risk_quality_gate_metadata(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "qwen3:0.6b")
    before_counts = _write_surface_counts()

    def fail_helper(_payload):
        raise AssertionError("safe fake helper must not be called when adapter flag is enabled")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("real 127.0.0.1:11434 access must not happen in deterministic tests")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "建议先核验证据来源，并补充责任岗位、检查频次、整改闭环和资料归档要求。"}

    def fake_builder(*, base_url=None):
        assert base_url == "http://127.0.0.1:11434"
        return fake_tags, fake_generate

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)
    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fake_builder)
    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", None)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", None)

    payload = {
        **_valid_endpoint_payload(),
        "section_text": "招标文件第99.99条要求采用GB99999-2099，工期999天，工程量为123456平方米。",
    }
    response = _client().post(SAFE_PATH, json=payload)
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["quality_status"] == "blocked"
    assert result["input_risk_status"] == "blocked"
    assert "suspicious_clause_reference" in result["input_risk_flags"]
    assert "suspicious_standard_reference" in result["input_risk_flags"]
    assert (
        "suspicious_duration_claim" in result["input_risk_flags"]
        or "suspicious_quantity_claim" in result["input_risk_flags"]
    )
    assert result["evidence_anchor_required"] is True
    assert result["evidence_anchor_status"] == "invalid_anchor"
    assert result["evidence_blocked"] is True
    assert result["formal_generation_allowed"] is False
    assert result["shadow_candidate_allowed"] is False
    assert result["writeback_allowed"] is False
    assert result["export_allowed"] is False
    assert result["zbid_writeback_allowed"] is False
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_RUNTIME_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_preserves_unsupported_project_fact_metadata(monkeypatch) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "qwen3:0.6b")
    before_counts = _write_surface_counts()

    def fail_helper(_payload):
        raise AssertionError("safe fake helper must not be called when adapter flag is enabled")

    def fail_urlopen(*_args, **_kwargs):
        raise AssertionError("real 127.0.0.1:11434 access must not happen in deterministic tests")

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "建议补充责任岗位、检查频次、整改闭环和资料归档要求。"}

    def fake_builder(*, base_url=None):
        assert base_url == "http://127.0.0.1:11434"
        return fake_tags, fake_generate

    monkeypatch.setattr(preview_module.urllib.request, "urlopen", fail_urlopen)
    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", fake_builder)
    monkeypatch.setattr(local_llm_preview_safe, "run_zdoc_local_llm_preview_safe_service_entry", fail_helper)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", None)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", None)

    payload = {
        **_valid_endpoint_payload(),
        "section_text": (
            "本项目现场已有3台塔吊、2座拌合站和5个固定材料堆场。"
            "No drawings or site records are provided."
        ),
    }
    response = _client().post(SAFE_PATH, json=payload)
    result = response.json()

    assert response.status_code == 200
    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["quality_status"] == "review_required"
    assert result["quality_status"] != "preview_ok"
    assert result["input_risk_status"] != "clear"
    assert "unsupported_project_fact" in result["input_risk_flags"]
    assert result["unsupported_project_fact_detected"] is True
    assert result["project_fact_without_evidence"] is True
    assert result["evidence_source_missing"] is True
    assert result["evidence_anchor_required"] is True
    assert result["evidence_anchor_status"] == "missing"
    assert result["evidence_review_required"] is True
    _assert_safe_endpoint_prompt_metadata(result, "response_first")
    assert result["formal_generation_allowed"] is False
    assert result["shadow_candidate_allowed"] is False
    assert result["writeback_allowed"] is False
    assert result["export_allowed"] is False
    assert result["zbid_writeback_allowed"] is False
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_RUNTIME_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_default_builder_init_exception_returns_controlled_failure(
    monkeypatch,
) -> None:
    import backend.zhifei_autoplan.ollama_preview as preview_module

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    def failing_builder(*, base_url=None):
        assert base_url == "http://127.0.0.1:11434"
        raise RuntimeError("builder unavailable")

    monkeypatch.setattr(preview_module, "build_zdoc_ollama_default_transports", failing_builder)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", None)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", None)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "transport_failure"
    assert result["reason"] == "default_transport_builder_failure"
    assert result["calls_ollama"] is False
    assert result["real_transport_enabled"] is True
    assert result["fake_transport_only"] is False
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_RUNTIME_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=False,
    )


def test_safe_endpoint_double_flags_requested_model_missing_returns_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_OLLAMA_PREVIEW_MODEL", "missing-model:latest")
    before_counts = _write_surface_counts()
    generate_calls = []

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        generate_calls.append(True)
        raise AssertionError("generate must not be called for a missing model")

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "model_unavailable"
    assert result["reason"] == "requested_model_unavailable"
    assert result["model"] == "missing-model:latest"
    assert generate_calls == []
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_empty_generate_response_returns_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "   "}

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "invalid_response"
    assert result["reason"] == "empty_response_and_thinking"
    assert result["advisory"] == ""
    assert result["suggestions"] == []
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_thinking_only_response_is_bounded_preview(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()
    thinking_only = "<think>" + ("仅作预览推理。" * 300)

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": thinking_only}

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "thinking_only_fallback"
    assert result["response_mode"] == "thinking_only_fallback"
    assert result["thinking_fallback_detected"] is True
    assert result["response_mode_review_required"] is True
    assert result["content_source"] == "thinking"
    assert result["advisory"].startswith("模型仅返回推理预览内容")
    assert len(result["advisory"]) <= 1200
    assert result["advisory"] != thinking_only
    assert result["risk_notes"] == ["thinking_only_fallback"]
    assert "content" not in result
    assert "docx" not in result
    assert "job_id" not in result
    assert "export_path" not in result
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_json_response_keeps_bounded_lists(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {
            "response": json.dumps(
                {
                    "advisory": "建议补充样板验收资料。",
                    "suggestions": ["建议一", "建议二", "建议三", "建议四"],
                    "risk_notes": ["风险一", "风险二", "风险三", "风险四"],
                },
                ensure_ascii=False,
            )
        }

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "structured_json"
    assert result["response_mode"] == "json_advisory"
    assert result["response_source"] == "response"
    _assert_safe_endpoint_prompt_metadata(result, "response_first")
    assert result["advisory"] == "建议补充样板验收资料。"
    assert result["suggestions"] == ["建议一", "建议二", "建议三"]
    assert result["risk_notes"] == ["风险一", "风险二", "风险三"]
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_empty_response_with_thinking_is_bounded_fallback(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()
    thinking = "分析：" + ("仅作预览推理。" * 240)

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "", "thinking": thinking}

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["preview_mode"] == "thinking_only_fallback"
    assert result["response_mode"] == "thinking_only_fallback"
    assert result["thinking_fallback_detected"] is True
    assert result["content_source"] == "thinking"
    assert result["advisory"].startswith("模型仅返回推理预览内容")
    assert result["advisory"] != thinking
    assert result["risk_notes"] == ["thinking_only_fallback"]
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_transport_exception_returns_controlled_failure(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(*_args, **_kwargs):
        raise RuntimeError("fake transport failed")

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json=_valid_endpoint_payload()).json()

    assert result["ok"] is False
    assert result["status"] == "failure"
    assert result["error_type"] == "transport_failure"
    assert result["reason"] == "generate_transport_failure"
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


def test_safe_endpoint_double_flags_missing_optional_fields_uses_defaults(monkeypatch) -> None:
    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()
    seen = {}

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, payload, _timeout):
        seen["prompt"] = payload["prompt"]
        return {"response": "默认字段预览建议。"}

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

    result = _client().post(SAFE_PATH, json={"section_text": "只有正文。"}).json()

    assert result["ok"] is True
    assert result["status"] == "ok"
    assert result["request_id"] == ""
    assert "Untitled section" in seen["prompt"]
    assert result["response_mode"] == "response_advisory"
    _assert_safe_endpoint_prompt_metadata(result, "response_first")
    assert _write_surface_counts() == before_counts
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


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


def test_safe_endpoint_double_flags_does_not_call_forbidden_routes_or_chains(monkeypatch) -> None:
    from backend.app.routers import actions_bridge, zhifei_autoplan

    monkeypatch.setenv("ZDOC_LOCAL_LLM_PREVIEW_ENABLED", "true")
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()

    def fake_tags(_url, _payload, _timeout):
        return {"models": [{"name": "qwen3:0.6b"}]}

    def fake_generate(_url, _payload, _timeout):
        return {"response": "只返回 preview advisory。"}

    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_TAGS_TRANSPORT", fake_tags)
    monkeypatch.setattr(local_llm_preview_safe, "SAFE_ENDPOINT_OLLAMA_GENERATE_TRANSPORT", fake_generate)

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
    _assert_safe_endpoint_guard(
        result,
        source=REAL_ADAPTER_SOURCE,
        entry_source=REAL_ADAPTER_ENTRY_SOURCE,
        fake_only=False,
        calls_ollama=True,
    )


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
    monkeypatch.setenv("ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED", "true")
    before_counts = _write_surface_counts()
    original_payload = copy.deepcopy(payload)

    def fail_adapter(_payload):
        raise AssertionError("adapter must not be called for invalid endpoint payload")

    monkeypatch.setattr(local_llm_preview_safe, "_run_ollama_adapter_bridge", fail_adapter)

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
