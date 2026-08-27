from __future__ import annotations

import asyncio
import hashlib
import os
from typing import Optional, Dict, Any

from backend.zhifei_autoplan.model_reliability import (
    ModelReliabilityRuntime,
    bounded_retry_delay,
    classify_provider_error,
)
from backend.zhifei_autoplan.execution_control import (
    ExecutionBudgetExceededError,
    ExecutionCancelledError,
    ExecutionControlRuntime,
    model_request_input_chars,
    model_request_output_tokens,
)

from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider
from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider
from backend.zhifei_autoplan.providers.google_gemini_provider import GeminiProvider
from backend.zhifei_autoplan.providers.zhipu_provider import ZhipuProvider
from backend.zhifei_autoplan.providers.qwen_provider import QwenProvider
from backend.zhifei_autoplan.providers.deepseek_provider import DeepSeekProvider
from backend.zhifei_autoplan.providers.baidu_provider import BaiduProvider
from backend.zhifei_autoplan.providers.iflytek_provider import IflytekProvider
from backend.zhifei_autoplan.providers.tencent_provider import TencentProvider
from backend.zhifei_autoplan.providers.grok_provider import GrokProvider
from backend.zhifei_autoplan.providers.ollama_provider import OllamaProvider


def _env_bool(name: str, default: bool = False) -> bool:
    raw = str(os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "y"}


class LLMClient:
    """
    统一 LLM 调用入口（OpenAI / Claude / LangChain）。
    - 这里做最小接口，后续可用 LangChain 的 ChatOpenAI/ChatAnthropic 替换。
    """

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        secret_key: Optional[str] = None,
        token_url: Optional[str] = None,
        reliability_runtime: ModelReliabilityRuntime | None = None,
        retry_attempts: int = 1,
        retry_base_delay: float = 0.25,
        execution_runtime: ExecutionControlRuntime | None = None,
        reliability_identity: str | None = None,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.secret_key = secret_key
        self.token_url = token_url
        self.reliability_runtime = reliability_runtime
        self.retry_attempts = max(1, min(5, int(retry_attempts or 1)))
        self.retry_base_delay = max(0.0, min(8.0, float(retry_base_delay or 0.0)))
        self.execution_runtime = execution_runtime
        normalized_identity = str(reliability_identity or "").strip().lower()
        if not normalized_identity and str(api_key or "").strip():
            normalized_identity = hashlib.sha256(
                b"model-reliability-v1\x00" + str(api_key).strip().encode("utf-8")
            ).hexdigest()
        self.reliability_identity = normalized_identity or None

        self._impl = None
        self._init_error = None
        cred_err = self._check_required_credentials()
        if cred_err:
            self._impl = None
            self._init_error = cred_err
            return
        try:
            self._impl = self._init_provider()
        except Exception as e:
            # Never crash caller on provider init error.
            # This allows orchestrator to rotate to next provider.
            self._impl = None
            self._init_error = repr(e)

    def _check_required_credentials(self) -> str | None:
        p = str(self.provider or "").strip().lower()
        api = str(self.api_key or "").strip()
        sec = str(self.secret_key or "").strip()
        # Most providers require API key; short-circuit to avoid slow remote failures.
        key_required = {"openai", "grok", "anthropic", "google", "zhipu", "qwen", "deepseek", "iflytek", "tencent"}
        if p in key_required and not api:
            return "api_key_missing"
        if p == "baidu":
            if not api:
                return "api_key_missing"
            if not sec:
                return "secret_key_missing"
        return None

    @staticmethod
    def load_defaults() -> dict:
        from pathlib import Path
        import json
        cfg_path = Path("backend/data/autoplan/config.json")
        if not cfg_path.exists():
            return {}
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _init_provider(self):
        if self.provider == "openai":
            return OpenAIProvider(self.api_key or "", self.model)
        if self.provider == "grok":
            return GrokProvider(self.api_key or "", self.model, self.base_url or "https://api.x.ai/v1")
        if self.provider == "anthropic":
            return AnthropicProvider(self.api_key or "", self.model)
        if self.provider == "google":
            return GeminiProvider(self.api_key or "", self.model)
        if self.provider == "zhipu":
            return ZhipuProvider(self.api_key or "", self.model)
        if self.provider == "qwen":
            return QwenProvider(self.api_key or "", self.model)
        if self.provider == "deepseek":
            return DeepSeekProvider(self.api_key or "", self.model, self.base_url or "https://api.deepseek.com")
        if self.provider == "baidu":
            return BaiduProvider(self.api_key or "", self.secret_key or "", self.model, self.token_url or "")
        if self.provider == "iflytek":
            return IflytekProvider(self.api_key or "", self.model, self.base_url or "")
        if self.provider == "tencent":
            return TencentProvider(self.api_key or "", self.model, self.base_url or "")
        if self.provider == "ollama":
            if not _env_bool("ZDOC_OLLAMA_PROVIDER_ENABLED", default=False):
                self._init_error = "ollama_provider_disabled"
                return None
            return OllamaProvider(model=self.model, base_url=self.base_url)
        return None

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        if self._impl is None:
            legacy_error = self._init_error or "provider_not_configured"
            return {
                "provider": self.provider,
                "model": self.model,
                "text": "",
                "error": legacy_error,
                "error_info": classify_provider_error(
                    legacy_error,
                    provider=self.provider,
                    model=self.model,
                ),
                "attempts": 0,
            }

        runtime = self.reliability_runtime
        if runtime is not None and runtime.is_open(
            self.provider,
            self.model,
            self.reliability_identity,
        ):
            error_info = classify_provider_error(
                "circuit_open",
                provider=self.provider,
                model=self.model,
            )
            error_info.update(
                {
                    "code": "circuit_open",
                    "retryable": False,
                    "user_message": "该模型在本次任务中已被熔断。",
                    "action": "系统将跳过它并尝试健康的备用模型。",
                    "severity": "error",
                }
            )
            return {
                "provider": self.provider,
                "model": self.model,
                "text": "",
                "error": "circuit_open",
                "error_info": error_info,
                "attempts": 0,
            }

        attempts = max(1, min(5, int(kwargs.pop("retry_attempts", self.retry_attempts) or 1)))
        if str(self.provider or "").strip().lower() in {"openai", "anthropic", "google"}:
            kwargs.setdefault("timeout", 240.0)
            kwargs.setdefault("stream", True)
        last_error: Any = "provider_error"
        last_info: Dict[str, Any] | None = None
        for attempt in range(1, attempts + 1):
            try:
                if self.execution_runtime is None:
                    result = await self._impl.complete(prompt, **kwargs)
                else:
                    async with self.execution_runtime.model_attempt(
                        provider=self.provider,
                        model=self.model,
                        prompt_chars=model_request_input_chars(prompt, kwargs),
                        requested_output_tokens=model_request_output_tokens(
                            self.provider,
                            kwargs,
                        ),
                    ):
                        result = await self._impl.complete(prompt, **kwargs)
                        if isinstance(result, dict):
                            self.execution_runtime.record_result(result)
                if not isinstance(result, dict):
                    result = {"text": str(result or "")}
                text = str(result.get("text") or "").strip()
                raw_error = result.get("error")
                if text and not raw_error:
                    if runtime is not None:
                        runtime.record_success(
                            self.provider,
                            self.model,
                            self.reliability_identity,
                        )
                    result.setdefault("provider", self.provider)
                    result.setdefault("model", self.model)
                    result["attempts"] = attempt
                    return result
                last_error = raw_error or "no_visible_text"
                last_info = classify_provider_error(
                    result.get("error_info") or last_error,
                    provider=self.provider,
                    model=self.model,
                )
            except (ExecutionCancelledError, ExecutionBudgetExceededError):
                raise
            except (asyncio.TimeoutError, TimeoutError) as exc:
                last_error = "timeout"
                last_info = classify_provider_error(exc, provider=self.provider, model=self.model)
            except Exception as exc:
                last_error = repr(exc)
                last_info = classify_provider_error(exc, provider=self.provider, model=self.model)

            retry_code = str((last_info or {}).get("code") or "")
            # A timed-out generation may still be completing remotely.  Never
            # duplicate it against the same provider.  Only explicit rate
            # limiting and provider-side 5xx outages receive one bounded retry.
            retry_allowed = retry_code in {"rate_limited", "provider_unavailable"}
            if not retry_allowed or attempt >= min(2, attempts):
                break
            await bounded_retry_delay(
                attempt,
                retry_after=last_info.get("retry_after"),
                base_delay=self.retry_base_delay,
            )

        final_info = last_info or classify_provider_error(
            last_error,
            provider=self.provider,
            model=self.model,
        )
        if runtime is not None:
            # Internal retries belong to one logical provider request. Counting
            # every attempt as a separate failure opens the shared circuit from
            # a single transient outage and starves parallel chapter agents.
            runtime.record_failure(
                self.provider,
                self.model,
                final_info,
                self.reliability_identity,
            )
        return {
            "provider": self.provider,
            "model": self.model,
            "text": "",
            "error": last_error,
            "error_info": final_info,
            "attempts": attempt,
        }

    def close(self) -> None:
        impl = self._impl
        client = getattr(impl, "client", None)
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass

    async def preflight(self, *, timeout: float = 30.0) -> Dict[str, Any]:
        """Validate credentials/model availability with a minimal visible-text call."""

        result = await self.complete(
            "Reply with exactly OK.",
            timeout=max(5.0, min(60.0, float(timeout or 30.0))),
            # OpenAI Responses currently enforces a minimum of 16 output
            # tokens.  Keep the cross-provider probe at that common floor so a
            # healthy backup route is not rejected by its own preflight.
            max_tokens=16,
            retry_attempts=min(2, self.retry_attempts),
            task_type="provider_preflight",
            project_id="system",
        )
        text = str(result.get("text") or "").strip() if isinstance(result, dict) else ""
        return {
            "ok": bool(text) and not bool(result.get("error")),
            "provider": self.provider,
            "model": self.model,
            "streamed": bool(result.get("streamed")),
            "attempts": int(result.get("attempts") or 0),
            "error": result.get("error"),
            "error_info": result.get("error_info"),
        }
