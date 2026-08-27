from __future__ import annotations

import asyncio
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict


_SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{8,}\b", re.IGNORECASE),
    re.compile(r"\bAIza[A-Za-z0-9_-]{16,}\b"),
)


def sanitize_provider_message(value: Any, *, limit: int = 500) -> str:
    """Return a bounded provider message without credential-shaped strings."""

    text = str(value or "").replace("\x00", " ").strip()
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    text = " ".join(text.split())
    return text[:limit]


def _status_from_error(error: Any, message: str) -> int | None:
    for candidate in (
        getattr(error, "status_code", None),
        getattr(getattr(error, "response", None), "status_code", None),
    ):
        try:
            if candidate is not None:
                return int(candidate)
        except (TypeError, ValueError):
            pass
    # Do not treat arbitrary three-digit substrings as HTTP statuses.  Internal
    # requirement identifiers such as ``REQ-CR-E1AF505EF062`` are common in
    # quality-gate failures and previously turned into a fabricated HTTP 505.
    status_codes = r"400|401|403|404|408|409|422|429|5\d\d"
    contextual = re.search(
        rf"(?i)\b(?:http(?:\s+status)?|status(?:\s+code)?|error(?:\s+code)?|code)"
        rf"\s*[:=]?\s*({status_codes})(?![A-Za-z0-9])",
        message,
    )
    if contextual:
        return int(contextual.group(1))
    described = re.search(
        rf"(?i)(?<![A-Za-z0-9])({status_codes})(?![A-Za-z0-9])\s*(?:-|:)?\s*"
        r"(?:bad\s+request|invalid|unauthorized|forbidden|not\s+found|timed?\s*out|"
        r"timeout|conflict|unprocessable|rate\s+limit|too\s+many\s+requests|"
        r"internal\s+server\s+error|bad\s+gateway|service\s+unavailable|"
        r"gateway\s+timeout|provider\s+unavailable|unavailable)",
        message,
    )
    return int(described.group(1)) if described else None


def _retry_after(error: Any) -> float | None:
    headers = getattr(getattr(error, "response", None), "headers", None)
    if headers is None:
        headers = getattr(error, "headers", None)
    try:
        raw = headers.get("retry-after") if headers else None
        if raw is not None:
            return max(0.0, min(30.0, float(raw)))
    except (AttributeError, TypeError, ValueError):
        pass
    return None


_USER_GUIDANCE: Dict[str, tuple[str, str]] = {
    "authentication_failed": ("模型凭据无效或已失效。", "请重新配置对应供应商 API Key 后再试。"),
    "permission_denied": ("当前凭据没有调用该模型的权限。", "请在供应商控制台开通模型权限或改用已授权模型。"),
    "model_not_found": ("配置的模型不存在或当前账户不可见。", "请刷新模型名称并确认账户所在区域和项目。"),
    "quota_exhausted": ("模型账户额度、余额或配额已耗尽。", "请充值、提升配额或切换到可用备用模型。"),
    "rate_limited": ("模型服务触发临时限流。", "系统会按退避策略重试；持续限流时请降低并发或稍后重试。"),
    "timeout": ("模型请求超时。", "系统会重试瞬态超时；持续发生时请检查网络或降低章节并发。"),
    "provider_unavailable": ("模型供应商服务暂时不可用。", "系统会尝试备用模型；若全部不可用请稍后重试。"),
    "network_error": ("本机无法稳定连接模型供应商。", "请检查网络、代理和供应商服务状态。"),
    "content_filtered": ("模型供应商拒绝了本次内容。", "请检查输入资料和指令中的敏感或不合规内容。"),
    "invalid_request": ("发送给模型的参数或请求格式不受支持。", "请检查模型名称、上下文长度和高级参数。"),
    "no_visible_text": ("模型响应中没有可用正文。", "系统会重试；持续发生时请切换模型或关闭扩展思考。"),
    "output_truncated": ("模型正文达到输出上限且续写仍未完成。", "请缩小章节范围或提高有界续写预算后重试。"),
    "api_key_missing": ("未找到对应供应商 API Key。", "请在本机安全凭据中配置后再试。"),
    "secret_key_missing": ("未找到对应供应商 Secret Key。", "请在本机安全凭据中配置后再试。"),
    "provider_not_configured": ("模型供应商尚未完成配置。", "请配置供应商、模型名称和本机安全凭据。"),
    "ollama_provider_disabled": ("本地 Ollama 正文调用未启用。", "如确需本地正文调用，请先完成本地模型验收并启用开关。"),
    "circuit_open": ("该模型在本次任务中已被熔断。", "系统将跳过它并尝试健康的备用模型。"),
    "EXECUTION_BUDGET_EXCEEDED": (
        "本次任务的模型调用安全预算已用尽。",
        "请移除过小的手工预算，或按章节数量提高任务级模型调用预算后重新发起任务。",
    ),
    "provider_error": ("模型调用失败。", "请查看安全诊断码，并确认模型、网络和供应商状态。"),
}


def _with_user_guidance(info: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(info)
    code = str(result.get("code") or "provider_error")
    user_message, action = _USER_GUIDANCE.get(code, _USER_GUIDANCE["provider_error"])
    result.setdefault("user_message", user_message)
    result.setdefault("action", action)
    result.setdefault("severity", "warning" if bool(result.get("retryable")) else "error")
    return result


def classify_provider_error(
    error: Any,
    *,
    provider: str,
    model: str,
) -> Dict[str, Any]:
    """Normalize SDK/provider failures into a stable, non-secret record."""

    is_connection_error = isinstance(error, ConnectionError)

    if isinstance(error, dict) and error.get("code"):
        info = dict(error)
        info.setdefault("provider", provider)
        info.setdefault("model", model)
        info["message"] = sanitize_provider_message(info.get("message") or info.get("code"))
        info.setdefault("retryable", False)
        return _with_user_guidance(info)

    if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
        message = "provider request timed out"
        status = 408
    else:
        message = sanitize_provider_message(error)
        status = _status_from_error(error, message)
    lower = message.lower()

    quota_markers = (
        "insufficient_quota",
        "quota exceeded",
        "quota_exceeded",
        "credit balance",
        "billing hard limit",
        "billing limit",
        "out of credits",
        "no credits remaining",
        "add credits",
        "余额不足",
        "额度不足",
        "配额已用尽",
    )

    if status == 401 or any(x in lower for x in ("invalid api key", "authentication", "unauthorized")):
        code, retryable = "authentication_failed", False
    elif status == 403 or any(x in lower for x in ("permission denied", "forbidden")):
        code, retryable = "permission_denied", False
    elif status == 404 or any(x in lower for x in ("model_not_found", "model not found", "does not exist")):
        code, retryable = "model_not_found", False
    elif any(x in lower for x in quota_markers):
        # Several providers encode exhausted credit/quota as HTTP 429.  Retrying
        # such a response only wastes time and can duplicate billable work.
        code, retryable = "quota_exhausted", False
    elif status == 429 or any(x in lower for x in ("rate limit", "rate_limit", "too many requests")):
        code, retryable = "rate_limited", True
    elif status in {408} or any(x in lower for x in ("timed out", "timeout")):
        code, retryable = "timeout", True
    elif status is not None and status >= 500:
        code, retryable = "provider_unavailable", True
    elif is_connection_error or any(
        x in lower
        for x in (
            "connection",
            "network",
            "temporarily unavailable",
            "service unavailable",
        )
    ):
        code, retryable = "network_error", True
    elif any(
        x in lower
        for x in (
            "content filter",
            "content_filter",
            "content policy",
            "safety filter",
            "safety policy",
            "blocked by safety",
            "safety blocked",
            "moderation_blocked",
        )
    ):
        code, retryable = "content_filtered", False
    elif any(x in lower for x in ("invalid request", "bad request", "unprocessable")) or status in {400, 409, 422}:
        code, retryable = "invalid_request", False
    elif lower in {"no_visible_text", "empty_response"}:
        code, retryable = "no_visible_text", True
    elif lower in {"output_truncated", "max_output_tokens"}:
        code, retryable = "output_truncated", False
    elif lower in {"api_key_missing", "secret_key_missing"}:
        code, retryable = lower, False
    elif lower in {"provider_not_configured", "ollama_provider_disabled"}:
        code, retryable = lower, False
    else:
        code, retryable = "provider_error", False

    return _with_user_guidance({
        "code": code,
        "message": message or code,
        "status": status,
        "retryable": retryable,
        "retry_after": _retry_after(error),
        "provider": str(provider or ""),
        "model": str(model or ""),
        "exception_type": type(error).__name__ if isinstance(error, BaseException) else None,
    })


@dataclass
class ModelReliabilityRuntime:
    """Job-local circuit breaker and provider-health ledger."""

    failure_threshold: int = 2
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @staticmethod
    def key(provider: str, model: str, identity: str | None = None) -> str:
        base = f"{str(provider or '').strip().lower()}::{str(model or '').strip()}"
        normalized_identity = str(identity or "").strip().lower()
        return f"{base}::{normalized_identity}" if normalized_identity else base

    def is_open(self, provider: str, model: str, identity: str | None = None) -> bool:
        exact = self.key(provider, model, identity)
        if identity:
            return bool(self.states.get(exact, {}).get("open")) or bool(
                self.states.get(self.key(provider, model), {}).get("open")
            )
        # Compatibility/read-side aggregate for callers that do not know the
        # credential identity. Runtime model calls always provide one when a
        # credential exists, so one exhausted key cannot quarantine another.
        prefix = self.key(provider, model) + "::"
        return bool(self.states.get(exact, {}).get("open")) or any(
            bool(value.get("open"))
            for key, value in self.states.items()
            if key.startswith(prefix)
        )

    def record_success(self, provider: str, model: str, identity: str | None = None) -> None:
        state = self.states.setdefault(self.key(provider, model, identity), {})
        state.update(
            {
                "open": False,
                "opened_reason": None,
                "consecutive_failures": 0,
                "last_error": None,
                "last_success_at": time.time(),
            }
        )
        state["successes"] = int(state.get("successes") or 0) + 1

    def record_failure(
        self,
        provider: str,
        model: str,
        error_info: Dict[str, Any],
        identity: str | None = None,
    ) -> None:
        state = self.states.setdefault(self.key(provider, model, identity), {})
        count = int(state.get("consecutive_failures") or 0) + 1
        # A single attributable failure is evidence for provider rotation, not
        # enough evidence to quarantine the provider for the whole run.  This
        # keeps the circuit contract literal: two consecutive logical failures
        # open the default breaker, while a successful call resets the streak.
        should_open = bool(count >= max(1, int(self.failure_threshold)))
        state.update(
            {
                "consecutive_failures": count,
                "last_error": dict(error_info),
                "last_failure_at": time.time(),
                "failures": int(state.get("failures") or 0) + 1,
                "open": should_open,
                "opened_reason": str(error_info.get("code") or "provider_error") if should_open else None,
            }
        )

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        return {key: dict(value) for key, value in sorted(self.states.items())}


async def bounded_retry_delay(
    attempt: int,
    *,
    retry_after: float | None = None,
    base_delay: float = 0.25,
    jitter_ratio: float = 0.15,
    random_fn: Callable[[], float] = random.random,
    sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
) -> None:
    delay = retry_after if retry_after is not None else base_delay * (2 ** max(0, attempt - 1))
    bounded = max(0.0, min(8.0, float(delay)))
    ratio = max(0.0, min(0.5, float(jitter_ratio or 0.0)))
    if bounded and ratio:
        # Symmetric jitter prevents chapter workers from retrying in lockstep.
        bounded *= 1.0 + ((float(random_fn()) * 2.0) - 1.0) * ratio
    await sleep(max(0.0, min(8.0, bounded)))
