"""
LLMClient 单元测试
覆盖 llm_client.py 的所有方法和 provider 初始化
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.zhifei_autoplan.utils.llm_client import LLMClient


# ==============================================================================
# __init__ tests
# ==============================================================================


class TestLLMClientInit:
    """测试 LLMClient 初始化"""

    def test_init_with_all_params(self):
        """所有参数初始化"""
        with patch.object(LLMClient, "_init_provider", return_value=MagicMock()):
            client = LLMClient(
                provider="openai",
                model="gpt-4",
                api_key="test-key",
                base_url="https://api.test.com",
                secret_key="secret",
                token_url="https://token.test.com",
            )
            assert client.provider == "openai"
            assert client.model == "gpt-4"
            assert client.api_key == "test-key"
            assert client.base_url == "https://api.test.com"
            assert client.secret_key == "secret"
            assert client.token_url == "https://token.test.com"

    def test_init_with_minimal_params(self):
        """最小参数初始化"""
        with patch.object(LLMClient, "_init_provider", return_value=MagicMock()):
            client = LLMClient(provider="openai", model="gpt-4")
            assert client.provider == "openai"
            assert client.model == "gpt-4"
            assert client.api_key is None
            assert client.base_url is None

    def test_init_calls_init_provider(self):
        """初始化时调用 _init_provider"""
        mock_provider = MagicMock()
        with patch.object(LLMClient, "_init_provider", return_value=mock_provider) as mock_init:
            client = LLMClient(provider="openai", model="gpt-4", api_key="test-key")
            mock_init.assert_called_once()
            assert client._impl == mock_provider


# ==============================================================================
# load_defaults tests
# ==============================================================================


class TestLoadDefaults:
    """测试 load_defaults 静态方法"""

    def test_load_defaults_file_exists(self, tmp_path, monkeypatch):
        """配置文件存在时加载"""
        config_data = {"provider": "openai", "model": "gpt-4"}
        config_dir = tmp_path / "backend" / "data" / "autoplan"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        
        monkeypatch.chdir(tmp_path)
        result = LLMClient.load_defaults()
        assert result == config_data

    def test_load_defaults_file_not_exists(self, tmp_path, monkeypatch):
        """配置文件不存在时返回空字典"""
        monkeypatch.chdir(tmp_path)
        result = LLMClient.load_defaults()
        assert result == {}

    def test_load_defaults_invalid_json(self, tmp_path, monkeypatch):
        """配置文件 JSON 无效时返回空字典"""
        config_dir = tmp_path / "backend" / "data" / "autoplan"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "config.json"
        config_file.write_text("invalid json {{{", encoding="utf-8")
        
        monkeypatch.chdir(tmp_path)
        result = LLMClient.load_defaults()
        assert result == {}


# ==============================================================================
# _init_provider tests
# ==============================================================================


class TestInitProvider:
    """测试 _init_provider 方法"""

    def test_init_openai_provider(self):
        """初始化 OpenAI provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.OpenAIProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="openai", model="gpt-4", api_key="test-key")
            mock.assert_called_once_with("test-key", "gpt-4")

    def test_init_anthropic_provider(self):
        """初始化 Anthropic provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.AnthropicProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="anthropic", model="claude-3", api_key="test-key")
            mock.assert_called_once_with("test-key", "claude-3")

    def test_init_grok_provider(self):
        """初始化 Grok provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.GrokProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="grok", model="grok-4-1-fast-reasoning", api_key="test-key")
            mock.assert_called_once_with("test-key", "grok-4-1-fast-reasoning", "https://api.x.ai/v1")

    def test_init_grok_provider_custom_url(self):
        """初始化 Grok provider（自定义 URL）"""
        with patch("backend.zhifei_autoplan.utils.llm_client.GrokProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(
                provider="grok",
                model="grok-4-1-fast-reasoning",
                api_key="test-key",
                base_url="https://custom.x.ai/v1",
            )
            mock.assert_called_once_with("test-key", "grok-4-1-fast-reasoning", "https://custom.x.ai/v1")

    def test_init_google_provider(self):
        """初始化 Google Gemini provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.GeminiProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="google", model="gemini-pro", api_key="test-key")
            mock.assert_called_once_with("test-key", "gemini-pro")

    def test_init_zhipu_provider(self):
        """初始化智谱 provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.ZhipuProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="zhipu", model="glm-4", api_key="test-key")
            mock.assert_called_once_with("test-key", "glm-4")

    def test_init_qwen_provider(self):
        """初始化通义千问 provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.QwenProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="qwen", model="qwen-plus", api_key="test-key")
            mock.assert_called_once_with("test-key", "qwen-plus")

    def test_init_deepseek_provider(self):
        """初始化 DeepSeek provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.DeepSeekProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(
                provider="deepseek",
                model="deepseek-chat",
                api_key="test-key",
                base_url="https://custom.api.com",
            )
            mock.assert_called_once_with("test-key", "deepseek-chat", "https://custom.api.com")

    def test_init_deepseek_provider_default_url(self):
        """初始化 DeepSeek provider（默认 URL）"""
        with patch("backend.zhifei_autoplan.utils.llm_client.DeepSeekProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="test-key")
            mock.assert_called_once_with("test-key", "deepseek-chat", "https://api.deepseek.com")

    def test_init_baidu_provider(self):
        """初始化百度文心 provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.BaiduProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(
                provider="baidu",
                model="ernie-bot",
                api_key="test-key",
                secret_key="test-secret",
                token_url="https://token.url",
            )
            mock.assert_called_once_with("test-key", "test-secret", "ernie-bot", "https://token.url")

    def test_init_baidu_provider_default_values(self):
        """百度 provider 缺少 secret_key 时短路。"""
        with patch("backend.zhifei_autoplan.utils.llm_client.BaiduProvider") as mock:
            client = LLMClient(provider="baidu", model="ernie-bot", api_key="test-key")
            mock.assert_not_called()
            assert client._impl is None
            assert client._init_error == "secret_key_missing"

    def test_init_iflytek_provider(self):
        """初始化讯飞星火 provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.IflytekProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(
                provider="iflytek",
                model="spark-v3",
                api_key="test-key",
                base_url="https://spark.api.com",
            )
            mock.assert_called_once_with("test-key", "spark-v3", "https://spark.api.com")

    def test_init_iflytek_provider_default_url(self):
        """初始化讯飞星火 provider（默认 URL）"""
        with patch("backend.zhifei_autoplan.utils.llm_client.IflytekProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="iflytek", model="spark-v3", api_key="test-key")
            mock.assert_called_once_with("test-key", "spark-v3", "")

    def test_init_tencent_provider(self):
        """初始化腾讯混元 provider"""
        with patch("backend.zhifei_autoplan.utils.llm_client.TencentProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(
                provider="tencent",
                model="hunyuan",
                api_key="test-key",
                base_url="https://hunyuan.api.com",
            )
            mock.assert_called_once_with("test-key", "hunyuan", "https://hunyuan.api.com")

    def test_init_tencent_provider_default_url(self):
        """初始化腾讯混元 provider（默认 URL）"""
        with patch("backend.zhifei_autoplan.utils.llm_client.TencentProvider") as mock:
            mock.return_value = MagicMock()
            client = LLMClient(provider="tencent", model="hunyuan", api_key="test-key")
            mock.assert_called_once_with("test-key", "hunyuan", "")

    def test_init_unknown_provider(self):
        """未知 provider 返回 None"""
        client = LLMClient(provider="unknown", model="test")
        assert client._impl is None

    def test_init_provider_with_none_api_key(self):
        """缺少必需密钥时应短路，不触发 provider 初始化。"""
        with patch("backend.zhifei_autoplan.utils.llm_client.OpenAIProvider") as mock:
            client = LLMClient(provider="openai", model="gpt-4", api_key=None)
            mock.assert_not_called()
            assert client._impl is None
            assert client._init_error == "api_key_missing"

    def test_init_provider_exception_does_not_raise(self):
        """Provider 初始化异常不应向上抛出，需由 client 返回 error。"""
        with patch("backend.zhifei_autoplan.utils.llm_client.GeminiProvider", side_effect=ValueError("missing api key")):
            client = LLMClient(provider="google", model="gemini-3-pro-preview", api_key="test-key")
            assert client._impl is None
            assert "missing api key" in str(client._init_error or "")


# ==============================================================================
# complete tests
# ==============================================================================


class TestComplete:
    """测试 complete 异步方法"""

    @pytest.mark.asyncio
    async def test_complete_no_impl(self):
        """无 provider 实现时返回错误"""
        client = LLMClient(provider="unknown", model="test")
        result = await client.complete("test prompt")
        assert result["error"] == "provider_not_configured"
        assert result["provider"] == "unknown"
        assert result["model"] == "test"
        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_complete_returns_init_error_when_provider_init_failed(self):
        """Provider 初始化失败时 complete 返回初始化错误信息。"""
        with patch("backend.zhifei_autoplan.utils.llm_client.GeminiProvider", side_effect=ValueError("missing api key")):
            client = LLMClient(provider="google", model="gemini-3-pro-preview", api_key="test-key")
            result = await client.complete("test prompt")
            assert "missing api key" in str(result.get("error") or "")
            assert result["provider"] == "google"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """成功调用 provider"""
        mock_impl = MagicMock()
        mock_impl.complete = AsyncMock(return_value={"text": "response", "provider": "test"})
        
        with patch.object(LLMClient, "_init_provider", return_value=mock_impl):
            client = LLMClient(provider="openai", model="gpt-4", api_key="test-key")
            result = await client.complete("test prompt", temperature=0.7)
            
            mock_impl.complete.assert_called_once_with("test prompt", temperature=0.7)
            assert result["text"] == "response"

    @pytest.mark.asyncio
    async def test_complete_timeout(self):
        """超时处理"""
        mock_impl = MagicMock()
        mock_impl.complete = AsyncMock(side_effect=TimeoutError())
        
        with patch.object(LLMClient, "_init_provider", return_value=mock_impl):
            client = LLMClient(provider="openai", model="gpt-4", api_key="test-key")
            result = await client.complete("test prompt")
            
            assert result["error"] == "timeout"
            assert result["provider"] == "openai"
            assert result["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_complete_exception(self):
        """异常处理"""
        mock_impl = MagicMock()
        mock_impl.complete = AsyncMock(side_effect=ValueError("test error"))
        
        with patch.object(LLMClient, "_init_provider", return_value=mock_impl):
            client = LLMClient(provider="openai", model="gpt-4", api_key="test-key")
            result = await client.complete("test prompt")
            
            assert "ValueError" in result["error"]
            assert "test error" in result["error"]
            assert result["provider"] == "openai"
            assert result["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_complete_with_kwargs(self):
        """带额外参数调用"""
        mock_impl = MagicMock()
        mock_impl.complete = AsyncMock(return_value={"text": "response"})
        
        with patch.object(LLMClient, "_init_provider", return_value=mock_impl):
            client = LLMClient(provider="openai", model="gpt-4", api_key="test-key")
            await client.complete("test", max_tokens=100, temperature=0.5, top_p=0.9)
            
            mock_impl.complete.assert_called_once_with(
                "test", max_tokens=100, temperature=0.5, top_p=0.9
            )
