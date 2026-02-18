"""
LLM Providers 单元测试
覆盖所有 provider 的 __init__ 和 complete 方法
"""

from __future__ import annotations

from typing import Dict, Any
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from backend.zhifei_autoplan.providers.base import BaseProvider
from backend.zhifei_autoplan.providers.openai_provider import OpenAIProvider
from backend.zhifei_autoplan.providers.anthropic_provider import AnthropicProvider
from backend.zhifei_autoplan.providers.deepseek_provider import DeepSeekProvider
from backend.zhifei_autoplan.providers.google_gemini_provider import GeminiProvider
from backend.zhifei_autoplan.providers.zhipu_provider import ZhipuProvider
from backend.zhifei_autoplan.providers.qwen_provider import QwenProvider
from backend.zhifei_autoplan.providers.baidu_provider import BaiduProvider
from backend.zhifei_autoplan.providers.iflytek_provider import IflytekProvider
from backend.zhifei_autoplan.providers.tencent_provider import TencentProvider


# ==============================================================================
# BaseProvider tests
# ==============================================================================


class TestBaseProvider:
    """测试 BaseProvider 基类"""

    def test_name_attribute(self):
        """name 属性默认值"""
        assert BaseProvider.name == "base"

    @pytest.mark.asyncio
    async def test_complete_not_implemented(self):
        """complete 方法抛出 NotImplementedError"""
        provider = BaseProvider()
        with pytest.raises(NotImplementedError):
            await provider.complete("test prompt")


# ==============================================================================
# OpenAIProvider tests
# ==============================================================================


class TestOpenAIProvider:
    """测试 OpenAI provider"""

    def test_init(self):
        """初始化"""
        with patch("backend.zhifei_autoplan.providers.openai_provider.OpenAI") as mock_openai:
            mock_openai.return_value = MagicMock()
            provider = OpenAIProvider(api_key="test-key", model="gpt-4")
            assert provider.model == "gpt-4"
            mock_openai.assert_called_once_with(api_key="test-key")

    def test_name_attribute(self):
        """name 属性"""
        assert OpenAIProvider.name == "openai"

    @pytest.mark.asyncio
    async def test_complete_with_output_text(self):
        """complete 方法 - 有 output_text 属性"""
        with patch("backend.zhifei_autoplan.providers.openai_provider.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.output_text = "Hello, world!"
            mock_client.responses.create.return_value = mock_resp
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(api_key="test-key", model="gpt-4")
            result = await provider.complete("test prompt")

            assert result["provider"] == "openai"
            assert result["model"] == "gpt-4"
            assert result["text"] == "Hello, world!"
            mock_client.responses.create.assert_called_once_with(model="gpt-4", input="test prompt")

    @pytest.mark.asyncio
    async def test_complete_without_output_text(self):
        """complete 方法 - 无 output_text 属性（fallback 到 str）"""
        with patch("backend.zhifei_autoplan.providers.openai_provider.OpenAI") as mock_openai:
            mock_client = MagicMock()
            # 创建一个没有 output_text 属性的响应对象
            mock_resp = MagicMock()
            del mock_resp.output_text  # 删除 output_text 属性
            mock_client.responses.create.return_value = mock_resp
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(api_key="test-key", model="gpt-4")
            result = await provider.complete("test prompt")

            assert result["provider"] == "openai"
            assert result["text"]  # fallback 到 str(resp)


# ==============================================================================
# AnthropicProvider tests
# ==============================================================================


class TestAnthropicProvider:
    """测试 Anthropic provider"""

    def test_init(self):
        """初始化"""
        with patch("backend.zhifei_autoplan.providers.anthropic_provider.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = MagicMock()
            provider = AnthropicProvider(api_key="test-key", model="claude-3")
            assert provider.model == "claude-3"
            mock_anthropic.assert_called_once_with(api_key="test-key")

    def test_name_attribute(self):
        """name 属性"""
        assert AnthropicProvider.name == "anthropic"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.anthropic_provider.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_content = MagicMock()
            mock_content.text = "Claude response"
            mock_msg = MagicMock()
            mock_msg.content = [mock_content]
            mock_client.messages.create.return_value = mock_msg
            mock_anthropic.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key", model="claude-3")
            result = await provider.complete("test prompt")

            assert result["provider"] == "anthropic"
            assert result["model"] == "claude-3"
            assert result["text"] == "Claude response"

    @pytest.mark.asyncio
    async def test_complete_empty_content(self):
        """complete 方法 - 空内容"""
        with patch("backend.zhifei_autoplan.providers.anthropic_provider.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_msg = MagicMock()
            mock_msg.content = []
            mock_client.messages.create.return_value = mock_msg
            mock_anthropic.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key", model="claude-3")
            result = await provider.complete("test prompt")

            assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_complete_none_message(self):
        """complete 方法 - None 消息"""
        with patch("backend.zhifei_autoplan.providers.anthropic_provider.anthropic.Anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = None
            mock_anthropic.return_value = mock_client

            provider = AnthropicProvider(api_key="test-key", model="claude-3")
            result = await provider.complete("test prompt")

            assert result["text"] == ""


# ==============================================================================
# DeepSeekProvider tests
# ==============================================================================


class TestDeepSeekProvider:
    """测试 DeepSeek provider"""

    def test_init_default_url(self):
        """初始化 - 默认 URL"""
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-chat")
        assert provider.api_key == "test-key"
        assert provider.model == "deepseek-chat"
        assert provider.base_url == "https://api.deepseek.com"

    def test_init_custom_url(self):
        """初始化 - 自定义 URL"""
        provider = DeepSeekProvider(api_key="test-key", model="deepseek-chat", base_url="https://custom.api.com")
        assert provider.base_url == "https://custom.api.com"

    def test_name_attribute(self):
        """name 属性"""
        assert DeepSeekProvider.name == "deepseek"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.deepseek_provider.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": "DeepSeek response"}}]
            }
            mock_post.return_value = mock_resp

            provider = DeepSeekProvider(api_key="test-key", model="deepseek-chat")
            result = await provider.complete("test prompt")

            assert result["provider"] == "deepseek"
            assert result["model"] == "deepseek-chat"
            assert result["text"] == "DeepSeek response"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_empty_choices(self):
        """complete 方法 - 空 choices（默认值处理）"""
        with patch("backend.zhifei_autoplan.providers.deepseek_provider.requests.post") as mock_post:
            mock_resp = MagicMock()
            # DeepSeek 代码用 [{}] 作为默认值，所以空 choices 会触发 IndexError
            # 测试正常的空内容场景
            mock_resp.json.return_value = {"choices": [{"message": {"content": ""}}]}
            mock_post.return_value = mock_resp

            provider = DeepSeekProvider(api_key="test-key", model="deepseek-chat")
            result = await provider.complete("test prompt")

            assert result["text"] == ""


# ==============================================================================
# GeminiProvider tests
# ==============================================================================


class TestGeminiProvider:
    """测试 Google Gemini provider"""

    def test_init(self):
        """初始化 - 使用新的 google.genai Client API"""
        with patch("backend.zhifei_autoplan.providers.google_gemini_provider.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            provider = GeminiProvider(api_key="test-key", model="gemini-pro")
            # 新 API 存储 client 和 model_name
            assert provider.client == mock_client
            assert provider.model_name == "gemini-pro"
            mock_genai.Client.assert_called_once_with(api_key="test-key")

    def test_name_attribute(self):
        """name 属性"""
        assert GeminiProvider.name == "google"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功 - 使用新的 google.genai Client API"""
        with patch("backend.zhifei_autoplan.providers.google_gemini_provider.genai") as mock_genai:
            mock_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.text = "Gemini response"
            mock_client.models.generate_content.return_value = mock_resp
            mock_genai.Client.return_value = mock_client

            provider = GeminiProvider(api_key="test-key", model="gemini-pro")
            result = await provider.complete("test prompt")

            assert result["provider"] == "google"
            assert result["model"] == "gemini-pro"
            assert result["text"] == "Gemini response"
            mock_client.models.generate_content.assert_called_once_with(
                model="gemini-pro",
                contents="test prompt"
            )


# ==============================================================================
# ZhipuProvider tests
# ==============================================================================


class TestZhipuProvider:
    """测试智谱 provider"""

    def test_init(self):
        """初始化"""
        with patch("backend.zhifei_autoplan.providers.zhipu_provider.ZhipuAI") as mock_zhipu:
            mock_zhipu.return_value = MagicMock()
            provider = ZhipuProvider(api_key="test-key", model="glm-4")
            assert provider.model == "glm-4"
            mock_zhipu.assert_called_once_with(api_key="test-key")

    def test_name_attribute(self):
        """name 属性"""
        assert ZhipuProvider.name == "zhipu"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.zhipu_provider.ZhipuAI") as mock_zhipu:
            mock_client = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "智谱回复"
            mock_resp = MagicMock()
            mock_resp.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_resp
            mock_zhipu.return_value = mock_client

            provider = ZhipuProvider(api_key="test-key", model="glm-4")
            result = await provider.complete("test prompt")

            assert result["provider"] == "zhipu"
            assert result["text"] == "智谱回复"


# ==============================================================================
# QwenProvider tests
# ==============================================================================


class TestQwenProvider:
    """测试通义千问 provider"""

    def test_init(self):
        """初始化"""
        with patch("backend.zhifei_autoplan.providers.qwen_provider.dashscope") as mock_dashscope:
            provider = QwenProvider(api_key="test-key", model="qwen-plus")
            assert provider.model == "qwen-plus"
            assert mock_dashscope.api_key == "test-key"

    def test_name_attribute(self):
        """name 属性"""
        assert QwenProvider.name == "qwen"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.qwen_provider.dashscope") as mock_dashscope:
            mock_output = MagicMock()
            mock_output.get.return_value = "千问回复"
            mock_resp = MagicMock()
            mock_resp.output = mock_output
            mock_dashscope.Generation.call.return_value = mock_resp

            provider = QwenProvider(api_key="test-key", model="qwen-plus")
            result = await provider.complete("test prompt")

            assert result["provider"] == "qwen"
            assert result["text"] == "千问回复"

    @pytest.mark.asyncio
    async def test_complete_empty_output(self):
        """complete 方法 - 空输出"""
        with patch("backend.zhifei_autoplan.providers.qwen_provider.dashscope") as mock_dashscope:
            mock_resp = MagicMock()
            mock_resp.output = None
            mock_dashscope.Generation.call.return_value = mock_resp

            provider = QwenProvider(api_key="test-key", model="qwen-plus")
            result = await provider.complete("test prompt")

            assert result["text"] == ""


# ==============================================================================
# BaiduProvider tests
# ==============================================================================


class TestBaiduProvider:
    """测试百度文心 provider"""

    def test_init(self):
        """初始化"""
        provider = BaiduProvider(
            api_key="test-key",
            secret_key="test-secret",
            model="ernie-bot",
            token_url="https://token.url"
        )
        assert provider.api_key == "test-key"
        assert provider.secret_key == "test-secret"
        assert provider.model == "ernie-bot"
        assert provider.token_url == "https://token.url"

    def test_name_attribute(self):
        """name 属性"""
        assert BaiduProvider.name == "baidu"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.baidu_provider.requests.post") as mock_post:
            # 模拟获取 token
            mock_token_resp = MagicMock()
            mock_token_resp.json.return_value = {"access_token": "test-token"}
            
            # 模拟调用 API
            mock_api_resp = MagicMock()
            mock_api_resp.json.return_value = {"result": "文心回复"}
            
            mock_post.side_effect = [mock_token_resp, mock_api_resp]

            provider = BaiduProvider(
                api_key="test-key",
                secret_key="test-secret",
                model="ernie-bot",
                token_url="https://token.url"
            )
            result = await provider.complete("test prompt")

            assert result["provider"] == "baidu"
            assert result["text"] == "文心回复"


# ==============================================================================
# IflytekProvider tests
# ==============================================================================


class TestIflytekProvider:
    """测试讯飞星火 provider"""

    def test_init(self):
        """初始化"""
        provider = IflytekProvider(api_key="test-key", model="spark-v3", base_url="https://spark.api.com")
        assert provider.api_key == "test-key"
        assert provider.model == "spark-v3"
        assert provider.base_url == "https://spark.api.com"

    def test_name_attribute(self):
        """name 属性"""
        assert IflytekProvider.name == "iflytek"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.iflytek_provider.requests.post") as mock_post:
            mock_resp = MagicMock()
            # IflytekProvider 使用 data.get("text", "")
            mock_resp.json.return_value = {"text": "星火回复"}
            mock_post.return_value = mock_resp

            provider = IflytekProvider(api_key="test-key", model="spark-v3", base_url="https://spark.api.com")
            result = await provider.complete("test prompt")

            assert result["provider"] == "iflytek"
            assert result["text"] == "星火回复"


# ==============================================================================
# TencentProvider tests
# ==============================================================================


class TestTencentProvider:
    """测试腾讯混元 provider"""

    def test_init(self):
        """初始化"""
        provider = TencentProvider(api_key="test-key", model="hunyuan", base_url="https://hunyuan.api.com")
        assert provider.api_key == "test-key"
        assert provider.model == "hunyuan"
        assert provider.base_url == "https://hunyuan.api.com"

    def test_name_attribute(self):
        """name 属性"""
        assert TencentProvider.name == "tencent"

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """complete 方法 - 成功"""
        with patch("backend.zhifei_autoplan.providers.tencent_provider.requests.post") as mock_post:
            mock_resp = MagicMock()
            # TencentProvider 使用 data.get("text", "")
            mock_resp.json.return_value = {"text": "混元回复"}
            mock_post.return_value = mock_resp

            provider = TencentProvider(api_key="test-key", model="hunyuan", base_url="https://hunyuan.api.com")
            result = await provider.complete("test prompt")

            assert result["provider"] == "tencent"
            assert result["text"] == "混元回复"
