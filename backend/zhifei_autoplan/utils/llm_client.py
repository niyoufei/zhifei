from __future__ import annotations

from typing import Optional, Dict, Any

from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider
from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider
from backend.zhifei_autoplan.providers.google_gemini_provider import GeminiProvider
from backend.zhifei_autoplan.providers.zhipu_provider import ZhipuProvider
from backend.zhifei_autoplan.providers.qwen_provider import QwenProvider
from backend.zhifei_autoplan.providers.deepseek_provider import DeepSeekProvider
from backend.zhifei_autoplan.providers.baidu_provider import BaiduProvider
from backend.zhifei_autoplan.providers.iflytek_provider import IflytekProvider
from backend.zhifei_autoplan.providers.tencent_provider import TencentProvider


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
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.secret_key = secret_key
        self.token_url = token_url

        self._impl = None
        self._init_error: Exception | None = None
        try:
            self._impl = self._init_provider()
        except Exception as exc:
            self._init_error = exc
            self._impl = None

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
        return None

    async def complete(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        if self._impl is None:
            error = "provider_not_configured"
            if self._init_error is not None:
                error = f"provider_init_failed:{type(self._init_error).__name__}:{self._init_error}"
            return {"provider": self.provider, "model": self.model, "text": "", "error": error}
        try:
            return await self._impl.complete(prompt, **kwargs)
        except TimeoutError:
            return {"provider": self.provider, "model": self.model, "text": "", "error": "timeout"}
        except Exception as e:
            return {"provider": self.provider, "model": self.model, "text": "", "error": repr(e)}
