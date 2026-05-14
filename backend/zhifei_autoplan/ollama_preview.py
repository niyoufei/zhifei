from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Callable


DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3:0.6b"
DEFAULT_TIMEOUT_SECONDS = 60.0
LOCAL_LLM_PREVIEW_FLAG = "ZDOC_LOCAL_LLM_PREVIEW_ENABLED"
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
