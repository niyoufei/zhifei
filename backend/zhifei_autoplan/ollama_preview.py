from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Callable

from backend.zhifei_autoplan.preview_advisory_quality_gate import attach_preview_advisory_quality_gate


DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:0.6b"
DEFAULT_TIMEOUT_SECONDS = 60.0
LOCAL_LLM_PREVIEW_FLAG = "ZDOC_LOCAL_LLM_PREVIEW_ENABLED"
LOCAL_LLM_OLLAMA_PREVIEW_FLAG = "ZDOC_LOCAL_LLM_OLLAMA_PREVIEW_ENABLED"
LOCAL_LLM_OLLAMA_PREVIEW_MODEL_ENV = "ZDOC_OLLAMA_PREVIEW_MODEL"
LOCAL_LLM_OLLAMA_PREVIEW_TIMEOUT_ENV = "ZDOC_OLLAMA_PREVIEW_TIMEOUT"
LOCAL_LLM_OLLAMA_PREVIEW_NUM_PREDICT_ENV = "ZDOC_OLLAMA_PREVIEW_NUM_PREDICT"
LOCAL_LLM_PREVIEW_SOURCE = "zdoc_local_llm_preview_fake"
LOCAL_LLM_PREVIEW_MODEL = "fake-local-llm"
LOCAL_LLM_PREVIEW_ALLOWED_FIELDS = frozenset(
    {
        "section_text",
        "section_title",
        "review_focus",
        "preview_type",
        "source_context",
    }
)
LOCAL_LLM_PREVIEW_BRIDGE_ALLOWED_FIELDS = frozenset(
    {
        "section_text",
        "section_title",
        "review_focus",
        "preview_type",
        "source_context",
        "trigger",
        "caller",
    }
)
LOCAL_LLM_PREVIEW_BRIDGE_SOURCE = "zdoc_local_llm_preview_api_task_bridge_fake"
LOCAL_LLM_PREVIEW_BRIDGE_TYPE = "api_task_bridge"
LOCAL_LLM_PREVIEW_ENDPOINT_UI_SOURCE = "zdoc_local_llm_preview_endpoint_ui_entry_fake"
LOCAL_LLM_PREVIEW_ENDPOINT_UI_TYPE = "endpoint_ui_entry"
LOCAL_LLM_PREVIEW_ENDPOINT_UI_ALLOWED_FIELDS = LOCAL_LLM_PREVIEW_BRIDGE_ALLOWED_FIELDS | frozenset(
    {
        "entry_point",
        "ui_action",
    }
)
LOCAL_LLM_PREVIEW_SAFE_SERVICE_SOURCE = "zdoc_local_llm_preview_safe_service_entry_fake"
LOCAL_LLM_PREVIEW_SAFE_SERVICE_TYPE = "safe_service_entry"
LOCAL_LLM_PREVIEW_SAFE_SERVICE_ALLOWED_FIELDS = LOCAL_LLM_PREVIEW_BRIDGE_ALLOWED_FIELDS
LOCAL_LLM_PREVIEW_SAFE_SERVICE_PATH = "/diagnostics/local-llm-preview/safe"
LOCAL_LLM_OLLAMA_PREVIEW_SOURCE = "zdoc_real_ollama_preview_adapter_fake_transport"
LOCAL_LLM_OLLAMA_PREVIEW_REAL_TRANSPORT_SOURCE = "zdoc_real_ollama_preview_adapter_real_transport"
LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL = "http://127.0.0.1:11434"
LOCAL_LLM_OLLAMA_PREVIEW_TAGS_PATH = "/api/tags"
LOCAL_LLM_OLLAMA_PREVIEW_GENERATE_PATH = "/api/generate"
LOCAL_LLM_OLLAMA_PREVIEW_DEFAULT_TIMEOUT_SECONDS = 10.0
LOCAL_LLM_OLLAMA_PREVIEW_MAX_TIMEOUT_SECONDS = 30.0
LOCAL_LLM_OLLAMA_PREVIEW_DEFAULT_NUM_PREDICT = 256
LOCAL_LLM_OLLAMA_PREVIEW_MAX_NUM_PREDICT = 768
LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS = 1200
LOCAL_LLM_OLLAMA_PREVIEW_THINKING_CHARS = 360
LOCAL_LLM_OLLAMA_PREVIEW_MAX_LIST_ITEMS = 3
LOCAL_LLM_OLLAMA_PREVIEW_LIST_ITEM_CHARS = 220
LOCAL_LLM_PREVIEW_FORMAL_OUTPUT_FIELDS = frozenset(
    {
        "content",
        "docx",
        "docx_path",
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
)
LOCAL_LLM_PREVIEW_MANUAL_TRIGGERS = frozenset({"manual", "internal_diagnostic"})


Transport = Callable[[str, dict[str, Any], float], dict[str, Any]]
LocalLLMPreviewClient = Callable[[dict[str, Any]], dict[str, Any]]
LocalLLMPreviewHelper = Callable[[dict[str, Any]], dict[str, Any]]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y"}


def _clean_text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _clean_base_url(value: str | None) -> str:
    return str(value or DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL


def _clean_timeout(value: Any) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT_SECONDS
    return max(1.0, min(300.0, timeout))


def _fallback_response(
    *,
    enabled: bool,
    status: str,
    model: str,
    base_url: str,
    error: str | None = None,
    warning: str | None = None,
) -> dict[str, Any]:
    message = warning or error or "ollama_preview_unavailable"
    return {
        "ok": False,
        "enabled": bool(enabled),
        "status": status,
        "provider": "ollama",
        "model": model,
        "base_url": base_url,
        "content": "",
        "warning": message,
        "error": error,
        "fallback": {
            "available": True,
            "message": "Ollama preview is unavailable; main generation flow was not affected.",
        },
    }


def _preview_safety() -> dict[str, bool]:
    return {
        "default_off": True,
        "manual_trigger": True,
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "requires_human_review": True,
    }


def is_zdoc_ollama_preview_enabled() -> bool:
    return _env_bool(LOCAL_LLM_OLLAMA_PREVIEW_FLAG, default=False)


def _zdoc_ollama_preview_safety(*, real_transport_enabled: bool = False) -> dict[str, bool]:
    safety = _preview_safety()
    safety.update(
        {
            "fake_transport_only": not bool(real_transport_enabled),
            "real_ollama_runtime": bool(real_transport_enabled),
            "local_loopback_only": True,
            "downloads_models": False,
            "pulls_models": False,
            "writes_output": False,
            "writes_job": False,
            "writes_export": False,
        }
    )
    return safety


def _zdoc_ollama_base_url(value: Any = None) -> str:
    text = _clean_text(value, limit=120).rstrip("/")
    if not text:
        return LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL
    if text == LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL:
        return text
    return ""


def _zdoc_ollama_timeout(value: Any = None) -> float:
    raw = value if value is not None else os.environ.get(LOCAL_LLM_OLLAMA_PREVIEW_TIMEOUT_ENV)
    try:
        timeout = float(raw)
    except (TypeError, ValueError):
        timeout = LOCAL_LLM_OLLAMA_PREVIEW_DEFAULT_TIMEOUT_SECONDS
    return max(1.0, min(LOCAL_LLM_OLLAMA_PREVIEW_MAX_TIMEOUT_SECONDS, timeout))


def _zdoc_ollama_num_predict(value: Any = None) -> int:
    raw = value if value is not None else os.environ.get(LOCAL_LLM_OLLAMA_PREVIEW_NUM_PREDICT_ENV)
    try:
        num_predict = int(raw)
    except (TypeError, ValueError):
        num_predict = LOCAL_LLM_OLLAMA_PREVIEW_DEFAULT_NUM_PREDICT
    return max(1, min(LOCAL_LLM_OLLAMA_PREVIEW_MAX_NUM_PREDICT, num_predict))


def _zdoc_ollama_response(
    *,
    ok: bool,
    enabled: bool,
    adapter_enabled: bool,
    status: str,
    model: str = "",
    base_url: str = LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL,
    advisory: str = "",
    suggestions: list[str] | None = None,
    risk_notes: list[str] | None = None,
    warning: str | None = None,
    error_type: str | None = None,
    reason: str | None = None,
    preview_type: str = "section_review",
    preview_mode: str = "advisory",
    content_source: str = "",
    calls_ollama: bool = False,
    real_transport_enabled: bool = False,
) -> dict[str, Any]:
    source = LOCAL_LLM_OLLAMA_PREVIEW_REAL_TRANSPORT_SOURCE if real_transport_enabled else LOCAL_LLM_OLLAMA_PREVIEW_SOURCE
    entry = "real_ollama_preview_adapter_real_transport" if real_transport_enabled else "real_ollama_preview_adapter_fake_transport"
    return {
        "ok": bool(ok),
        "enabled": bool(enabled),
        "adapter_enabled": bool(adapter_enabled),
        "status": status,
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "source": source,
        "entry": entry,
        "provider": "ollama",
        "model": _clean_text(model, limit=120),
        "base_url": base_url,
        "transport_target": "127.0.0.1:11434",
        "tags_path": LOCAL_LLM_OLLAMA_PREVIEW_TAGS_PATH,
        "generate_path": LOCAL_LLM_OLLAMA_PREVIEW_GENERATE_PATH,
        "preview_type": preview_type,
        "fake_transport_only": not bool(real_transport_enabled),
        "real_transport_enabled": bool(real_transport_enabled),
        "calls_ollama": bool(calls_ollama),
        "calls_external_model_api": False,
        "downloads_models": False,
        "pulls_models": False,
        "writes_output": False,
        "writes_job": False,
        "writes_export": False,
        "triggers_generation_chain": False,
        "triggers_export_chain": False,
        "triggers_zbid_writeback": False,
        "advisory": _clean_text(advisory, limit=LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS),
        "suggestions": list(suggestions or []),
        "risk_notes": list(risk_notes or ([warning] if warning else [])),
        "warning": warning,
        "error_type": error_type,
        "reason": reason,
        "preview_mode": preview_mode,
        "content_source": content_source,
        "safety": _zdoc_ollama_preview_safety(real_transport_enabled=real_transport_enabled),
    }


def build_zdoc_ollama_disabled_response(
    *,
    enabled: bool,
    adapter_enabled: bool,
    reason: str,
    error_type: str = "ollama_preview_disabled",
) -> dict[str, Any]:
    return _zdoc_ollama_response(
        ok=False,
        enabled=enabled,
        adapter_enabled=adapter_enabled,
        status="disabled",
        warning=error_type,
        error_type=error_type,
        reason=reason,
    )


def build_zdoc_ollama_failure_response(
    *,
    error_type: str,
    reason: str,
    enabled: bool = True,
    adapter_enabled: bool = True,
    model: str = "",
    base_url: str = LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL,
    preview_type: str = "section_review",
    calls_ollama: bool = False,
    real_transport_enabled: bool = False,
) -> dict[str, Any]:
    return _zdoc_ollama_response(
        ok=False,
        enabled=enabled,
        adapter_enabled=adapter_enabled,
        status="failure",
        model=model,
        base_url=base_url,
        warning=error_type,
        error_type=error_type,
        reason=reason,
        preview_type=preview_type,
        calls_ollama=calls_ollama,
        real_transport_enabled=real_transport_enabled,
    )


def _zdoc_ollama_allowed_request_fields() -> frozenset[str]:
    return LOCAL_LLM_PREVIEW_ALLOWED_FIELDS | frozenset({"context_summary", "request_id"})


def _validate_zdoc_ollama_preview_request(request: dict[str, Any] | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(request, dict):
        return None, build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="request_must_be_object",
        )

    keys = set(request)
    forbidden = sorted((keys & LOCAL_LLM_PREVIEW_FORMAL_OUTPUT_FIELDS) | (keys - _zdoc_ollama_allowed_request_fields()))
    if forbidden:
        return None, build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason=f"illegal_field:{','.join(forbidden)}",
        )

    if "section_text" not in request:
        return None, build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="missing_section_text",
        )

    section_text = _clean_text(request.get("section_text"), limit=2000)
    if not section_text:
        return None, build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="empty_section_text",
        )

    normalized = {
        "section_text": section_text,
        "section_title": _clean_text(request.get("section_title"), limit=200) or "Untitled section",
        "review_focus": _clean_text(request.get("review_focus"), limit=300) or "preview advisory",
        "preview_type": _clean_text(request.get("preview_type"), limit=80) or "section_review",
        "source_context": _clean_text(request.get("source_context") or request.get("context_summary"), limit=1000),
        "request_id": _clean_text(request.get("request_id"), limit=120),
    }
    return normalized, None


def _extract_zdoc_ollama_model_names(tags_response: dict[str, Any]) -> list[str]:
    models = tags_response.get("models")
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for item in models:
        if isinstance(item, dict):
            name = _clean_text(item.get("name") or item.get("model"), limit=120)
        else:
            name = _clean_text(item, limit=120)
        if name:
            names.append(name)
    return names


def _read_zdoc_ollama_json_response(response: Any) -> dict[str, Any]:
    raw = response.read()
    if not raw:
        return {}
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("ollama_response_must_be_object")
    return parsed


def build_zdoc_ollama_default_transports(*, base_url: str | None = None) -> tuple[Transport, Transport]:
    resolved_base_url = _zdoc_ollama_base_url(base_url)
    if not resolved_base_url:
        raise ValueError("invalid_local_ollama_base_url")

    tags_url = f"{resolved_base_url}{LOCAL_LLM_OLLAMA_PREVIEW_TAGS_PATH}"
    generate_url = f"{resolved_base_url}{LOCAL_LLM_OLLAMA_PREVIEW_GENERATE_PATH}"

    def _assert_loopback_url(url: str, expected_url: str) -> None:
        if url != expected_url:
            raise ValueError("invalid_local_ollama_transport_url")

    def _tags_transport(url: str, _payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        _assert_loopback_url(url, tags_url)
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _read_zdoc_ollama_json_response(response)

    def _generate_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        _assert_loopback_url(url, generate_url)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return _read_zdoc_ollama_json_response(response)

    return _tags_transport, _generate_transport


def select_zdoc_local_ollama_model(
    *,
    tags_transport: Transport | None,
    requested_model: str | None = None,
    base_url: str | None = None,
    timeout: Any = None,
    real_transport_enabled: bool = False,
) -> dict[str, Any]:
    resolved_base_url = _zdoc_ollama_base_url(base_url)
    if not resolved_base_url:
        return build_zdoc_ollama_failure_response(
            error_type="transport_failure",
            reason="invalid_local_ollama_base_url",
            real_transport_enabled=real_transport_enabled,
        )

    if tags_transport is None:
        return build_zdoc_ollama_failure_response(
            error_type="transport_failure",
            reason="fake_tags_transport_required",
            base_url=resolved_base_url,
            real_transport_enabled=real_transport_enabled,
        )

    resolved_timeout = _zdoc_ollama_timeout(timeout)
    tags_url = f"{resolved_base_url}{LOCAL_LLM_OLLAMA_PREVIEW_TAGS_PATH}"
    try:
        tags_response = tags_transport(tags_url, {}, resolved_timeout)
    except (TimeoutError, socket.timeout):
        return build_zdoc_ollama_failure_response(
            error_type="timeout",
            reason="tags_timeout",
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )
    except (urllib.error.URLError, OSError):
        return build_zdoc_ollama_failure_response(
            error_type="ollama_unreachable",
            reason="tags_unreachable",
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )
    except ValueError:
        return build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="tags_invalid_response",
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )
    except Exception:
        return build_zdoc_ollama_failure_response(
            error_type="transport_failure",
            reason="tags_transport_failure",
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    if not isinstance(tags_response, dict):
        return build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="tags_response_must_be_object",
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    model_names = _extract_zdoc_ollama_model_names(tags_response)
    if not model_names:
        return build_zdoc_ollama_failure_response(
            error_type="model_unavailable",
            reason="no_local_ollama_models",
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    requested = _clean_text(requested_model or os.environ.get(LOCAL_LLM_OLLAMA_PREVIEW_MODEL_ENV), limit=120)
    if requested and requested not in model_names:
        return build_zdoc_ollama_failure_response(
            error_type="model_unavailable",
            reason="requested_model_unavailable",
            model=requested,
            base_url=resolved_base_url,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    selected = requested or model_names[0]
    result = _zdoc_ollama_response(
        ok=True,
        enabled=True,
        adapter_enabled=True,
        status="ok",
        model=selected,
        base_url=resolved_base_url,
        reason="model_selected",
        calls_ollama=True,
        real_transport_enabled=real_transport_enabled,
    )
    result["available_models_count"] = len(model_names)
    result["selection_only"] = True
    return result


def _zdoc_ollama_preview_prompt(request: dict[str, Any]) -> str:
    parts = [
        "Return preview-only advisory suggestions for the ZDoc section.",
        f"Section title: {request['section_title']}",
        f"Review focus: {request['review_focus']}",
    ]
    if request.get("source_context"):
        parts.append(f"Context summary: {request['source_context']}")
    parts.append(f"Section text: {request['section_text']}")
    parts.append("Do not write final document content. Do not create export artifacts.")
    return "\n".join(parts)


def _zdoc_ollama_suggestions(advisory: str) -> list[str]:
    lines = [_clean_text(line, limit=220) for line in advisory.splitlines()]
    suggestions = [line for line in lines if line][:3]
    return suggestions or ["Review the preview advisory manually before any future implementation step."]


def _zdoc_ollama_bounded_items(value: Any, *, fallback: list[str] | None = None) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = value.splitlines()
    else:
        raw_items = []
    items = [
        _clean_text(item, limit=LOCAL_LLM_OLLAMA_PREVIEW_LIST_ITEM_CHARS)
        for item in raw_items
    ]
    bounded = [item for item in items if item][:LOCAL_LLM_OLLAMA_PREVIEW_MAX_LIST_ITEMS]
    if bounded:
        return bounded
    return list(fallback or [])[:LOCAL_LLM_OLLAMA_PREVIEW_MAX_LIST_ITEMS]


def _zdoc_ollama_json_like(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _zdoc_ollama_thinking_fallback(thinking_text: str) -> dict[str, Any]:
    excerpt = _clean_text(thinking_text, limit=LOCAL_LLM_OLLAMA_PREVIEW_THINKING_CHARS)
    advisory = (
        "模型仅返回推理预览内容，以下为截断摘要，需人工复核："
        f"{excerpt}"
    )
    return {
        "advisory": _clean_text(advisory, limit=LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS),
        "suggestions": ["人工复核该 thinking-only preview 后再决定是否采纳。"],
        "risk_notes": ["thinking_only_fallback"],
        "preview_mode": "thinking_only_fallback",
        "content_source": "thinking",
    }


def _extract_zdoc_ollama_advisory_payload(raw_response: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    response_text = _clean_text(raw_response.get("response"), limit=LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS)
    content_source = "response" if response_text else ""
    message = raw_response.get("message")
    if not response_text and isinstance(message, dict):
        response_text = _clean_text(message.get("content"), limit=LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS)
        content_source = "message.content" if response_text else ""
    if not response_text:
        response_text = _clean_text(raw_response.get("advisory"), limit=LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS)
        content_source = "advisory" if response_text else ""

    thinking_text = _clean_text(raw_response.get("thinking"), limit=LOCAL_LLM_OLLAMA_PREVIEW_THINKING_CHARS)
    if response_text:
        if _zdoc_ollama_json_like(response_text):
            try:
                parsed = json.loads(response_text)
            except (TypeError, ValueError):
                return None, "malformed_json"
            if not isinstance(parsed, dict):
                return None, "malformed_response"
            advisory = _clean_text(parsed.get("advisory"), limit=LOCAL_LLM_OLLAMA_PREVIEW_ADVISORY_CHARS)
            if not advisory:
                return None, "missing_preview_advisory"
            suggestions = _zdoc_ollama_bounded_items(parsed.get("suggestions"), fallback=_zdoc_ollama_suggestions(advisory))
            risk_notes = _zdoc_ollama_bounded_items(parsed.get("risk_notes"))
            return {
                "advisory": advisory,
                "suggestions": suggestions,
                "risk_notes": risk_notes,
                "preview_mode": "structured_json",
                "content_source": content_source,
            }, None
        if response_text.startswith("<think"):
            return _zdoc_ollama_thinking_fallback(response_text), None
        return {
            "advisory": response_text,
            "suggestions": _zdoc_ollama_suggestions(response_text),
            "risk_notes": [],
            "preview_mode": "text_fallback",
            "content_source": content_source,
        }, None

    if thinking_text:
        return _zdoc_ollama_thinking_fallback(thinking_text), None

    if "response" in raw_response or "thinking" in raw_response:
        return None, "empty_response_and_thinking"
    return None, "missing_preview_advisory"


def normalize_zdoc_ollama_response(
    raw_response: Any,
    *,
    model: str,
    base_url: str = LOCAL_LLM_OLLAMA_PREVIEW_BASE_URL,
    preview_type: str = "section_review",
    real_transport_enabled: bool = False,
) -> dict[str, Any]:
    if not isinstance(raw_response, dict):
        return build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="malformed_response",
            model=model,
            base_url=base_url,
            preview_type=preview_type,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    error = _clean_text(raw_response.get("error"), limit=300)
    if error:
        return build_zdoc_ollama_failure_response(
            error_type="transport_failure",
            reason="ollama_error",
            model=model,
            base_url=base_url,
            preview_type=preview_type,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    try:
        normalized_payload, failure_reason = _extract_zdoc_ollama_advisory_payload(raw_response)
    except Exception:
        return build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason="normalization_failure",
            model=model,
            base_url=base_url,
            preview_type=preview_type,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )
    if not normalized_payload:
        return build_zdoc_ollama_failure_response(
            error_type="invalid_response",
            reason=failure_reason or "missing_preview_advisory",
            model=model,
            base_url=base_url,
            preview_type=preview_type,
            calls_ollama=True,
            real_transport_enabled=real_transport_enabled,
        )

    return _zdoc_ollama_response(
        ok=True,
        enabled=True,
        adapter_enabled=True,
        status="ok",
        model=model,
        base_url=base_url,
        advisory=normalized_payload["advisory"],
        suggestions=normalized_payload.get("suggestions") or _zdoc_ollama_suggestions(normalized_payload["advisory"]),
        risk_notes=normalized_payload.get("risk_notes") or [],
        preview_type=preview_type,
        preview_mode=normalized_payload.get("preview_mode") or "advisory",
        content_source=normalized_payload.get("content_source") or "",
        calls_ollama=True,
        real_transport_enabled=real_transport_enabled,
    )


def run_zdoc_ollama_preview(
    request: dict[str, Any] | None,
    *,
    tags_transport: Transport | None = None,
    generate_transport: Transport | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout: Any = None,
    num_predict: Any = None,
) -> dict[str, Any]:
    quality_context = dict(request) if isinstance(request, dict) else {}

    def _with_quality_gate(result: dict[str, Any]) -> dict[str, Any]:
        return attach_preview_advisory_quality_gate(result, context=quality_context)

    if not _env_bool(LOCAL_LLM_PREVIEW_FLAG, default=False):
        return _with_quality_gate(
            build_zdoc_ollama_disabled_response(
                enabled=False,
                adapter_enabled=False,
                reason="preview_feature_flag_disabled",
            )
        )

    if not is_zdoc_ollama_preview_enabled():
        return _with_quality_gate(
            build_zdoc_ollama_disabled_response(
                enabled=True,
                adapter_enabled=False,
                reason="adapter_feature_flag_disabled",
            )
        )

    normalized_request, failure = _validate_zdoc_ollama_preview_request(request)
    if failure:
        return _with_quality_gate(failure)
    quality_context = dict(normalized_request)

    resolved_base_url = _zdoc_ollama_base_url(base_url)
    if not resolved_base_url:
        return _with_quality_gate(
            build_zdoc_ollama_failure_response(
                error_type="transport_failure",
                reason="invalid_local_ollama_base_url",
            )
        )

    real_transport_enabled = False
    if tags_transport is None and generate_transport is None:
        try:
            tags_transport, generate_transport = build_zdoc_ollama_default_transports(base_url=resolved_base_url)
        except Exception:
            return _with_quality_gate(
                build_zdoc_ollama_failure_response(
                    error_type="transport_failure",
                    reason="default_transport_builder_failure",
                    base_url=resolved_base_url,
                    preview_type=normalized_request["preview_type"] if normalized_request else "section_review",
                    real_transport_enabled=True,
                )
            )
        real_transport_enabled = True
    elif tags_transport is None or generate_transport is None:
        return _with_quality_gate(
            build_zdoc_ollama_failure_response(
                error_type="transport_failure",
                reason="fake_transport_required",
                base_url=resolved_base_url,
                preview_type=normalized_request["preview_type"] if normalized_request else "section_review",
            )
        )

    selected = select_zdoc_local_ollama_model(
        tags_transport=tags_transport,
        requested_model=model,
        base_url=resolved_base_url,
        timeout=timeout,
        real_transport_enabled=real_transport_enabled,
    )
    if not selected.get("ok"):
        selected["preview_type"] = normalized_request["preview_type"] if normalized_request else "section_review"
        return _with_quality_gate(selected)

    selected_model = str(selected.get("model") or "")
    generate_url = f"{resolved_base_url}{LOCAL_LLM_OLLAMA_PREVIEW_GENERATE_PATH}"
    generate_payload = {
        "model": selected_model,
        "prompt": _zdoc_ollama_preview_prompt(normalized_request or {}),
        "stream": False,
        "options": {"num_predict": _zdoc_ollama_num_predict(num_predict)},
    }
    resolved_timeout = _zdoc_ollama_timeout(timeout)
    try:
        raw_response = generate_transport(generate_url, generate_payload, resolved_timeout)
    except (TimeoutError, socket.timeout):
        return _with_quality_gate(
            build_zdoc_ollama_failure_response(
                error_type="timeout",
                reason="generate_timeout",
                model=selected_model,
                base_url=resolved_base_url,
                preview_type=normalized_request["preview_type"] if normalized_request else "section_review",
                calls_ollama=True,
                real_transport_enabled=real_transport_enabled,
            )
        )
    except ValueError:
        return _with_quality_gate(
            build_zdoc_ollama_failure_response(
                error_type="invalid_response",
                reason="generate_invalid_response",
                model=selected_model,
                base_url=resolved_base_url,
                preview_type=normalized_request["preview_type"] if normalized_request else "section_review",
                calls_ollama=True,
                real_transport_enabled=real_transport_enabled,
            )
        )
    except Exception:
        return _with_quality_gate(
            build_zdoc_ollama_failure_response(
                error_type="transport_failure",
                reason="generate_transport_failure",
                model=selected_model,
                base_url=resolved_base_url,
                preview_type=normalized_request["preview_type"] if normalized_request else "section_review",
                calls_ollama=True,
                real_transport_enabled=real_transport_enabled,
            )
        )

    result = normalize_zdoc_ollama_response(
        raw_response,
        model=selected_model,
        base_url=resolved_base_url,
        preview_type=normalized_request["preview_type"] if normalized_request else "section_review",
        real_transport_enabled=real_transport_enabled,
    )
    result["request_id"] = normalized_request.get("request_id", "") if normalized_request else ""
    result["num_predict"] = _zdoc_ollama_num_predict(num_predict)
    return _with_quality_gate(result)


def build_zdoc_ollama_preview_client(
    *,
    tags_transport: Transport,
    generate_transport: Transport,
) -> LocalLLMPreviewClient:
    def _client(request: dict[str, Any]) -> dict[str, Any]:
        return run_zdoc_ollama_preview(
            request,
            tags_transport=tags_transport,
            generate_transport=generate_transport,
        )

    return _client


def _local_llm_preview_response(
    *,
    ok: bool,
    enabled: bool,
    status: str,
    advisory: str = "",
    suggestions: list[str] | None = None,
    preview_type: str = "section_review",
    warning: str | None = None,
    error_type: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "enabled": bool(enabled),
        "status": status,
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "source": LOCAL_LLM_PREVIEW_SOURCE,
        "model": LOCAL_LLM_PREVIEW_MODEL,
        "preview_type": preview_type,
        "advisory": advisory,
        "suggestions": list(suggestions or []),
        "warning": warning,
        "error_type": error_type,
        "reason": reason,
        "safety": _preview_safety(),
    }


def _with_local_llm_bridge_metadata(
    result: dict[str, Any],
    *,
    trigger: str = "manual",
    caller: str = "",
) -> dict[str, Any]:
    out = dict(result)
    out["bridge_type"] = LOCAL_LLM_PREVIEW_BRIDGE_TYPE
    out["bridge_source"] = LOCAL_LLM_PREVIEW_BRIDGE_SOURCE
    out["trigger"] = _clean_text(trigger, limit=80) or "manual"
    out["caller"] = _clean_text(caller, limit=120)
    out["preview_only"] = True
    out["no_write"] = True
    out["affects_generation"] = False
    out["affects_export"] = False
    out["affects_zbid_writeback"] = False
    safety = dict(out.get("safety") if isinstance(out.get("safety"), dict) else {})
    safety.update(_preview_safety())
    out["safety"] = safety
    return out


def _clean_local_llm_preview_entry_point(value: Any) -> str:
    raw = _clean_text(value, limit=40).lower()
    if raw in {"ui", "user_interface"}:
        return "ui"
    return "endpoint"


def _with_local_llm_endpoint_ui_metadata(
    result: dict[str, Any],
    *,
    entry_point: str = "endpoint",
    trigger: str = "manual",
    caller: str = "",
    ui_action: str = "manual_preview",
) -> dict[str, Any]:
    out = _with_local_llm_bridge_metadata(result, trigger=trigger, caller=caller)
    out["entry_type"] = LOCAL_LLM_PREVIEW_ENDPOINT_UI_TYPE
    out["entry_source"] = LOCAL_LLM_PREVIEW_ENDPOINT_UI_SOURCE
    out["entry_point"] = _clean_local_llm_preview_entry_point(entry_point)
    out["ui_action"] = _clean_text(ui_action, limit=80) or "manual_preview"
    out["endpoint_entry_ready"] = True
    out["ui_entry_ready"] = True
    out["endpoint_registered"] = False
    out["ui_registered"] = False
    out["service_started"] = False
    out["fake_only"] = True
    out["preview_only"] = True
    out["no_write"] = True
    out["affects_generation"] = False
    out["affects_export"] = False
    out["affects_zbid_writeback"] = False
    safety = dict(out.get("safety") if isinstance(out.get("safety"), dict) else {})
    safety.update(
        {
            "endpoint_ui_entry": True,
            "fake_only": True,
            "endpoint_registered": False,
            "ui_registered": False,
            "service_started": False,
            "manual_trigger": True,
            "preview_only": True,
            "no_write": True,
            "affects_generation": False,
            "affects_export": False,
            "affects_zbid_writeback": False,
        }
    )
    out["safety"] = safety
    return out


def _safe_service_safety() -> dict[str, bool]:
    return {
        "safe_service_entry": True,
        "safe_endpoint_isolated": True,
        "safe_endpoint_registered": False,
        "service_started": False,
        "fake_only": True,
        "calls_generate_route": False,
        "calls_export_docx_route": False,
        "calls_review_apply_route": False,
        "triggers_generation_chain": False,
        "triggers_export_chain": False,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "writes_output": False,
        "writes_job": False,
        "writes_export": False,
        "calls_ollama": False,
        "calls_external_model_api": False,
        "downloads_models": False,
        "pulls_models": False,
        "listens_on_0_0_0_0": False,
    }


def _with_local_llm_safe_service_metadata(
    result: dict[str, Any],
    *,
    trigger: str = "manual",
    caller: str = "",
) -> dict[str, Any]:
    out = _with_local_llm_bridge_metadata(result, trigger=trigger, caller=caller)
    out["entry_type"] = LOCAL_LLM_PREVIEW_SAFE_SERVICE_TYPE
    out["entry_source"] = LOCAL_LLM_PREVIEW_SAFE_SERVICE_SOURCE
    out["safe_service_entry_ready"] = True
    out["safe_endpoint_path"] = LOCAL_LLM_PREVIEW_SAFE_SERVICE_PATH
    out["safe_endpoint_registered"] = False
    out["service_started"] = False
    out["fake_only"] = True
    out["preview_only"] = True
    out["no_write"] = True
    out["affects_generation"] = False
    out["affects_export"] = False
    out["affects_zbid_writeback"] = False
    out["calls_generate_route"] = False
    out["calls_export_docx_route"] = False
    out["calls_review_apply_route"] = False
    out["triggers_generation_chain"] = False
    out["triggers_export_chain"] = False
    out["writes_output"] = False
    out["writes_job"] = False
    out["writes_export"] = False
    out["calls_ollama"] = False
    out["calls_external_model_api"] = False
    safety = dict(out.get("safety") if isinstance(out.get("safety"), dict) else {})
    safety.update(_safe_service_safety())
    out["safety"] = safety
    return out


def build_zdoc_local_llm_preview_api_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "section_text": _clean_text(request.get("section_text")),
        "section_title": _clean_text(request.get("section_title"), limit=200),
        "review_focus": _clean_text(request.get("review_focus"), limit=1000),
        "preview_type": _clean_text(request.get("preview_type"), limit=80) or "section_review",
        "source_context": request.get("source_context") if isinstance(request.get("source_context"), dict) else {},
    }


def run_zdoc_local_llm_preview_task(
    request: dict[str, Any] | None,
    *,
    preview_helper: LocalLLMPreviewHelper | None = None,
) -> dict[str, Any]:
    trigger = "manual"
    caller = ""
    if isinstance(request, dict):
        trigger = _clean_text(request.get("trigger"), limit=80) or trigger
        caller = _clean_text(request.get("caller"), limit=120)

    enabled = _env_bool(LOCAL_LLM_PREVIEW_FLAG, default=False)
    if not enabled:
        return _with_local_llm_bridge_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=False,
                status="disabled",
                warning="local_llm_preview_api_task_bridge_disabled",
                reason="feature_flag_disabled",
            ),
            trigger=trigger,
            caller=caller,
        )

    if not isinstance(request, dict):
        return _with_local_llm_bridge_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="missing_input",
                reason="payload_required",
            ),
            trigger=trigger,
            caller=caller,
        )

    extra_fields = sorted(set(request) - LOCAL_LLM_PREVIEW_BRIDGE_ALLOWED_FIELDS)
    if extra_fields:
        return _with_local_llm_bridge_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="illegal_field",
                reason=f"illegal_field:{extra_fields[0]}",
            ),
            trigger=trigger,
            caller=caller,
        )

    if "section_text" not in request:
        return _with_local_llm_bridge_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="missing_field",
                reason="missing_field:section_text",
            ),
            trigger=trigger,
            caller=caller,
        )

    payload = build_zdoc_local_llm_preview_api_payload(request)
    helper = preview_helper or run_zdoc_local_llm_preview
    try:
        result = helper(dict(payload))
    except (TimeoutError, socket.timeout):
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="bridge_helper_timeout",
            reason="bridge_helper_timeout",
        )
    except Exception as exc:
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type=f"bridge_helper_error:{type(exc).__name__}",
            reason="bridge_helper_error",
        )

    if not isinstance(result, dict):
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="invalid_bridge_response",
            reason="bridge_response_must_be_dict",
        )

    return _with_local_llm_bridge_metadata(result, trigger=trigger, caller=caller)


def build_zdoc_local_llm_preview_endpoint_ui_payload(request: dict[str, Any]) -> dict[str, Any]:
    trigger = _clean_text(request.get("trigger"), limit=80) or "manual"
    return {
        "section_text": _clean_text(request.get("section_text")),
        "section_title": _clean_text(request.get("section_title"), limit=200),
        "review_focus": _clean_text(request.get("review_focus"), limit=1000),
        "preview_type": _clean_text(request.get("preview_type"), limit=80) or "section_review",
        "source_context": request.get("source_context") if isinstance(request.get("source_context"), dict) else {},
        "trigger": trigger,
        "caller": _clean_text(request.get("caller"), limit=120),
    }


def run_zdoc_local_llm_preview_endpoint_ui_entry(
    request: dict[str, Any] | None,
    *,
    preview_bridge: LocalLLMPreviewHelper | None = None,
) -> dict[str, Any]:
    entry_point = "endpoint"
    trigger = "manual"
    caller = ""
    ui_action = "manual_preview"
    if isinstance(request, dict):
        entry_point = _clean_local_llm_preview_entry_point(request.get("entry_point"))
        trigger = _clean_text(request.get("trigger"), limit=80) or trigger
        caller = _clean_text(request.get("caller"), limit=120)
        ui_action = _clean_text(request.get("ui_action"), limit=80) or ui_action

    enabled = _env_bool(LOCAL_LLM_PREVIEW_FLAG, default=False)
    if not enabled:
        return _with_local_llm_endpoint_ui_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=False,
                status="disabled",
                warning="local_llm_preview_endpoint_ui_entry_disabled",
                reason="feature_flag_disabled",
            ),
            entry_point=entry_point,
            trigger=trigger,
            caller=caller,
            ui_action=ui_action,
        )

    if trigger not in LOCAL_LLM_PREVIEW_MANUAL_TRIGGERS:
        return _with_local_llm_endpoint_ui_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="invalid_trigger",
                reason="manual_trigger_required",
            ),
            entry_point=entry_point,
            trigger=trigger,
            caller=caller,
            ui_action=ui_action,
        )

    if not isinstance(request, dict):
        return _with_local_llm_endpoint_ui_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="missing_input",
                reason="payload_required",
            ),
            entry_point=entry_point,
            trigger=trigger,
            caller=caller,
            ui_action=ui_action,
        )

    extra_fields = sorted(set(request) - LOCAL_LLM_PREVIEW_ENDPOINT_UI_ALLOWED_FIELDS)
    if extra_fields:
        return _with_local_llm_endpoint_ui_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="illegal_field",
                reason=f"illegal_field:{extra_fields[0]}",
            ),
            entry_point=entry_point,
            trigger=trigger,
            caller=caller,
            ui_action=ui_action,
        )

    if "section_text" not in request:
        return _with_local_llm_endpoint_ui_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="missing_field",
                reason="missing_field:section_text",
            ),
            entry_point=entry_point,
            trigger=trigger,
            caller=caller,
            ui_action=ui_action,
        )

    payload = build_zdoc_local_llm_preview_endpoint_ui_payload(request)
    if not payload["section_text"]:
        return _with_local_llm_endpoint_ui_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                preview_type=payload.get("preview_type") or "section_review",
                error_type="empty_text",
                reason="section_text_required",
            ),
            entry_point=entry_point,
            trigger=trigger,
            caller=caller,
            ui_action=ui_action,
        )

    bridge = preview_bridge or run_zdoc_local_llm_preview_task
    try:
        result = bridge(dict(payload))
    except (TimeoutError, socket.timeout):
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="endpoint_ui_bridge_timeout",
            reason="endpoint_ui_bridge_timeout",
        )
    except Exception as exc:
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type=f"endpoint_ui_bridge_error:{type(exc).__name__}",
            reason="endpoint_ui_bridge_error",
        )

    if not isinstance(result, dict):
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="invalid_endpoint_ui_bridge_response",
            reason="endpoint_ui_bridge_response_must_be_dict",
        )

    return _with_local_llm_endpoint_ui_metadata(
        result,
        entry_point=entry_point,
        trigger=payload.get("trigger") or trigger,
        caller=payload.get("caller") or caller,
        ui_action=ui_action,
    )


def build_zdoc_local_llm_preview_safe_service_payload(request: dict[str, Any]) -> dict[str, Any]:
    trigger = _clean_text(request.get("trigger"), limit=80) or "manual"
    return {
        "section_text": _clean_text(request.get("section_text")),
        "section_title": _clean_text(request.get("section_title"), limit=200),
        "review_focus": _clean_text(request.get("review_focus"), limit=1000),
        "preview_type": _clean_text(request.get("preview_type"), limit=80) or "section_review",
        "source_context": request.get("source_context") if isinstance(request.get("source_context"), dict) else {},
        "trigger": trigger,
        "caller": _clean_text(request.get("caller"), limit=120),
    }


def run_zdoc_local_llm_preview_safe_service_entry(
    request: dict[str, Any] | None,
    *,
    preview_bridge: LocalLLMPreviewHelper | None = None,
) -> dict[str, Any]:
    trigger = "manual"
    caller = ""
    if isinstance(request, dict):
        trigger = _clean_text(request.get("trigger"), limit=80) or trigger
        caller = _clean_text(request.get("caller"), limit=120)

    enabled = _env_bool(LOCAL_LLM_PREVIEW_FLAG, default=False)
    if not enabled:
        return _with_local_llm_safe_service_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=False,
                status="disabled",
                warning="local_llm_preview_safe_service_entry_disabled",
                reason="feature_flag_disabled",
            ),
            trigger=trigger,
            caller=caller,
        )

    if trigger not in LOCAL_LLM_PREVIEW_MANUAL_TRIGGERS:
        return _with_local_llm_safe_service_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="invalid_trigger",
                reason="manual_trigger_required",
            ),
            trigger=trigger,
            caller=caller,
        )

    if not isinstance(request, dict):
        return _with_local_llm_safe_service_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="missing_input",
                reason="payload_required",
            ),
            trigger=trigger,
            caller=caller,
        )

    extra_fields = sorted(set(request) - LOCAL_LLM_PREVIEW_SAFE_SERVICE_ALLOWED_FIELDS)
    if extra_fields:
        return _with_local_llm_safe_service_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="illegal_field",
                reason=f"illegal_field:{extra_fields[0]}",
            ),
            trigger=trigger,
            caller=caller,
        )

    if "section_text" not in request:
        return _with_local_llm_safe_service_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                error_type="missing_field",
                reason="missing_field:section_text",
            ),
            trigger=trigger,
            caller=caller,
        )

    payload = build_zdoc_local_llm_preview_safe_service_payload(request)
    if not payload["section_text"]:
        return _with_local_llm_safe_service_metadata(
            _local_llm_preview_response(
                ok=False,
                enabled=True,
                status="failure",
                preview_type=payload.get("preview_type") or "section_review",
                error_type="empty_text",
                reason="section_text_required",
            ),
            trigger=trigger,
            caller=caller,
        )

    bridge = preview_bridge or run_zdoc_local_llm_preview_task
    try:
        result = bridge(dict(payload))
    except (TimeoutError, socket.timeout):
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="safe_service_bridge_timeout",
            reason="safe_service_bridge_timeout",
        )
    except Exception as exc:
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type=f"safe_service_bridge_error:{type(exc).__name__}",
            reason="safe_service_bridge_error",
        )

    if not isinstance(result, dict):
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="invalid_safe_service_bridge_response",
            reason="safe_service_bridge_response_must_be_dict",
        )

    forbidden_result_fields = sorted(set(result) & LOCAL_LLM_PREVIEW_FORMAL_OUTPUT_FIELDS)
    if forbidden_result_fields:
        result = _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=payload.get("preview_type") or "section_review",
            error_type="forbidden_safe_service_bridge_field",
            reason=f"forbidden_field:{forbidden_result_fields[0]}",
        )

    return _with_local_llm_safe_service_metadata(
        result,
        trigger=payload.get("trigger") or trigger,
        caller=payload.get("caller") or caller,
    )


def build_zdoc_local_llm_preview_ui_view(result: dict[str, Any]) -> dict[str, Any]:
    normalized = result if isinstance(result, dict) else _local_llm_preview_response(
        ok=False,
        enabled=False,
        status="failure",
        error_type="invalid_ui_view_input",
        reason="result_must_be_dict",
    )
    out = _with_local_llm_endpoint_ui_metadata(
        normalized,
        entry_point=str(normalized.get("entry_point") or "ui"),
        trigger=str(normalized.get("trigger") or "manual"),
        caller=str(normalized.get("caller") or ""),
        ui_action=str(normalized.get("ui_action") or "manual_preview"),
    )
    suggestions = out.get("suggestions") if isinstance(out.get("suggestions"), list) else []
    return {
        "ok": bool(out.get("ok")),
        "enabled": bool(out.get("enabled")),
        "status": str(out.get("status") or ""),
        "entry_type": LOCAL_LLM_PREVIEW_ENDPOINT_UI_TYPE,
        "entry_source": LOCAL_LLM_PREVIEW_ENDPOINT_UI_SOURCE,
        "entry_point": out.get("entry_point"),
        "preview_only": True,
        "no_write": True,
        "affects_generation": False,
        "affects_export": False,
        "affects_zbid_writeback": False,
        "display": {
            "kind": "local_llm_preview_diagnostics",
            "label": "Local LLM preview diagnostics",
            "advisory": _clean_text(out.get("advisory"), limit=4000),
            "suggestions": [_clean_text(item, limit=500) for item in suggestions if _clean_text(item, limit=500)],
            "disabled": not bool(out.get("enabled")),
            "actions": {
                "can_write_back": False,
                "can_generate": False,
                "can_export": False,
                "can_zbid_writeback": False,
            },
        },
        "safety": dict(out.get("safety") if isinstance(out.get("safety"), dict) else {}),
    }


def _stable_local_llm_fake_preview(request: dict[str, Any]) -> dict[str, Any]:
    title = " ".join(_clean_text(request.get("section_title"), limit=120).split()) or "untitled section"
    focus = " ".join(_clean_text(request.get("review_focus"), limit=160).split())
    focus_text = focus or "missing items, risks, and manual review suggestions"
    return {
        "advisory": (
            f"Fake local LLM preview for {title}: advisory-only review for {focus_text}. "
            "The original section was not modified."
        ),
        "suggestions": [
            "Check whether required evidence is present before manual adoption.",
            "Review risk and compliance wording without changing the source text.",
            "Keep this preview out of generation, export, job, output, and ZBid write-back paths.",
        ],
    }


def run_zdoc_local_llm_preview(
    payload: dict[str, Any] | None,
    *,
    fake_client: LocalLLMPreviewClient | None = None,
) -> dict[str, Any]:
    enabled = _env_bool(LOCAL_LLM_PREVIEW_FLAG, default=False)
    if not enabled:
        return _local_llm_preview_response(
            ok=False,
            enabled=False,
            status="disabled",
            warning="local_llm_preview_disabled",
            reason="feature_flag_disabled",
        )

    if not isinstance(payload, dict):
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            error_type="missing_input",
            reason="payload_required",
        )

    extra_fields = sorted(set(payload) - LOCAL_LLM_PREVIEW_ALLOWED_FIELDS)
    if extra_fields:
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            error_type="illegal_field",
            reason=f"illegal_field:{extra_fields[0]}",
        )

    if "section_text" not in payload:
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            error_type="missing_field",
            reason="missing_field:section_text",
        )

    section_text = _clean_text(payload.get("section_text"))
    preview_type = _clean_text(payload.get("preview_type"), limit=80) or "section_review"
    if not section_text:
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=preview_type,
            error_type="empty_text",
            reason="section_text_required",
        )

    request = {
        "section_text": section_text,
        "section_title": _clean_text(payload.get("section_title"), limit=200),
        "review_focus": _clean_text(payload.get("review_focus"), limit=1000),
        "preview_type": preview_type,
        "source_context": payload.get("source_context") if isinstance(payload.get("source_context"), dict) else {},
    }

    client = fake_client or _stable_local_llm_fake_preview
    try:
        data = client(dict(request))
    except (TimeoutError, socket.timeout):
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=preview_type,
            error_type="fake_client_timeout",
            reason="fake_client_timeout",
        )
    except Exception as exc:
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=preview_type,
            error_type=f"fake_client_error:{type(exc).__name__}",
            reason="fake_client_error",
        )

    if not isinstance(data, dict):
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=preview_type,
            error_type="invalid_fake_response",
            reason="fake_response_must_be_dict",
        )

    advisory = _clean_text(data.get("advisory"), limit=4000)
    raw_suggestions = data.get("suggestions")
    if not advisory or not isinstance(raw_suggestions, list):
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=preview_type,
            error_type="invalid_fake_response",
            reason="advisory_and_suggestions_required",
        )

    suggestions = [_clean_text(item, limit=500) for item in raw_suggestions if _clean_text(item, limit=500)]
    if not suggestions:
        return _local_llm_preview_response(
            ok=False,
            enabled=True,
            status="failure",
            preview_type=preview_type,
            error_type="invalid_fake_response",
            reason="suggestions_required",
        )

    return _local_llm_preview_response(
        ok=True,
        enabled=True,
        status="ok",
        preview_type=preview_type,
        advisory=advisory,
        suggestions=suggestions,
    )


def build_preview_prompt(*, content: str, section_title: str = "", instruction: str = "") -> str:
    title = _clean_text(section_title, limit=200) or "未命名章节"
    body = _clean_text(content)
    user_instruction = _clean_text(instruction, limit=1000)
    instruction_block = user_instruction or "请对该章节做只读预览增强，指出缺项、风险和可改进表达，不要重写原文。"
    return (
        "你是施工组织设计文档的人工预览助手。"
        "本次只允许输出审阅建议，不允许改写正文，不允许生成新事实。\n"
        "输出要求：\n"
        "1. 用简体中文。\n"
        "2. 只列缺项、风险提示和可人工采纳的优化建议。\n"
        "3. 不要替用户自动改正文。\n"
        "4. 若信息不足，明确写“信息不足”，不要臆造。\n\n"
        f"章节标题：{title}\n"
        f"人工指令：{instruction_block}\n\n"
        f"待预览内容：\n{body}\n"
    )


def build_section_review_prompt(
    *,
    project_name: str | None = None,
    section_title: str | None = None,
    section_content: str,
    review_focus: str | None = None,
) -> str:
    project = _clean_text(project_name, limit=200) or "未命名项目"
    title = _clean_text(section_title, limit=200) or "未命名章节"
    body = _clean_text(section_content)
    focus = _clean_text(review_focus, limit=1000) or "章节完整性、缺项、风险点、可执行字段、证据支撑和表达清晰度"
    return (
        "你是施工组织设计文档的人工章节复核助手。"
        "本次只允许输出复核建议，不允许改写正文，不允许生成新事实，不允许替用户自动采纳。\n"
        "输出要求：\n"
        "1. 用简体中文。\n"
        "2. 按“缺项”“风险点”“优化建议”三类输出。\n"
        "3. 只基于给定章节文本判断，信息不足时明确写“信息不足”。\n"
        "4. 不要输出完整改写稿，不要改变原章节。\n\n"
        f"项目名称：{project}\n"
        f"章节标题：{title}\n"
        f"复核重点：{focus}\n\n"
        f"已生成章节正文：\n{body}\n"
    )


def _default_transport(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8", errors="replace"))


def run_ollama_preview(
    *,
    content: str,
    section_title: str | None = None,
    instruction: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | int | str | None = None,
    enabled: bool | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    resolved_enabled = _env_bool("ZDOC_OLLAMA_PREVIEW_ENABLED", default=False) if enabled is None else bool(enabled)
    resolved_model = str(model or os.environ.get("ZDOC_OLLAMA_PREVIEW_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    resolved_base_url = _clean_base_url(base_url or os.environ.get("ZDOC_OLLAMA_PREVIEW_BASE_URL"))
    resolved_timeout = _clean_timeout(timeout or os.environ.get("ZDOC_OLLAMA_PREVIEW_TIMEOUT"))

    if not resolved_enabled:
        return _fallback_response(
            enabled=False,
            status="disabled",
            model=resolved_model,
            base_url=resolved_base_url,
            warning="ollama_preview_disabled",
        )

    text = _clean_text(content)
    if not text:
        return _fallback_response(
            enabled=True,
            status="empty_content",
            model=resolved_model,
            base_url=resolved_base_url,
            warning="content_required",
        )

    prompt = build_preview_prompt(
        content=text,
        section_title=str(section_title or ""),
        instruction=str(instruction or ""),
    )
    payload = {
        "model": resolved_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
    }
    url = f"{resolved_base_url}/api/chat"
    sender = transport or _default_transport
    try:
        data = sender(url, payload, resolved_timeout)
    except (TimeoutError, socket.timeout):
        return _fallback_response(
            enabled=True,
            status="fallback",
            model=resolved_model,
            base_url=resolved_base_url,
            error="ollama_preview_timeout",
        )
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        return _fallback_response(
            enabled=True,
            status="fallback",
            model=resolved_model,
            base_url=resolved_base_url,
            error=f"ollama_preview_error:{type(exc).__name__}",
        )
    except Exception as exc:
        return _fallback_response(
            enabled=True,
            status="fallback",
            model=resolved_model,
            base_url=resolved_base_url,
            error=f"ollama_preview_error:{type(exc).__name__}",
        )

    message = data.get("message") if isinstance(data, dict) else {}
    content_text = ""
    if isinstance(message, dict):
        content_text = str(message.get("content") or "").strip()
    if not content_text and isinstance(data, dict):
        content_text = str(data.get("response") or data.get("content") or "").strip()
    if not content_text:
        return _fallback_response(
            enabled=True,
            status="fallback",
            model=resolved_model,
            base_url=resolved_base_url,
            error="ollama_preview_empty_response",
        )
    return {
        "ok": True,
        "enabled": True,
        "status": "ok",
        "provider": "ollama",
        "model": str(data.get("model") or resolved_model) if isinstance(data, dict) else resolved_model,
        "base_url": resolved_base_url,
        "content": content_text,
        "warning": None,
        "error": None,
        "fallback": None,
        "metadata": {
            "endpoint": "/api/chat",
            "stream": False,
            "think": False,
        },
    }


def _as_section_review_result(result: dict[str, Any]) -> dict[str, Any]:
    out = dict(result)
    out["review_type"] = "section_review"
    out["fallback_reason"] = None if out.get("ok") else str(
        out.get("error") or out.get("warning") or out.get("status") or ""
    )
    return out


def run_ollama_section_review(
    *,
    project_name: str | None = None,
    section_title: str | None = None,
    section_content: str,
    review_focus: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | int | str | None = None,
    enabled: bool | None = None,
    transport: Transport | None = None,
) -> dict[str, Any]:
    if not _clean_text(section_content):
        result = run_ollama_preview(
            content="",
            section_title=section_title,
            instruction="只做人工章节复核，返回缺项、风险点和可人工采纳的优化建议；不要改写正文。",
            model=model,
            base_url=base_url,
            timeout=timeout,
            enabled=enabled,
            transport=transport,
        )
        return _as_section_review_result(result)

    prompt = build_section_review_prompt(
        project_name=project_name,
        section_title=section_title,
        section_content=section_content,
        review_focus=review_focus,
    )
    result = run_ollama_preview(
        content=prompt,
        section_title=section_title,
        instruction="只做人工章节复核，返回缺项、风险点和可人工采纳的优化建议；不要改写正文。",
        model=model,
        base_url=base_url,
        timeout=timeout,
        enabled=enabled,
        transport=transport,
    )
    return _as_section_review_result(result)
