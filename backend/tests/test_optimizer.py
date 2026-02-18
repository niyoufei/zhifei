"""
Optimizer 单元测试

测试覆盖:
- _select_variant: 变体选择逻辑
- optimize_sections: 异步章节优化
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from backend.zhifei_autoplan.optimizer import _select_variant, optimize_sections


# =============================================================================
# _select_variant 测试
# =============================================================================

class TestSelectVariant:
    """_select_variant 函数测试"""

    def test_select_variant_with_variants_list(self):
        """有 variants 列表时返回第一个"""
        data = {
            "variants": [
                {"id": 1, "name": "第一个"},
                {"id": 2, "name": "第二个"}
            ]
        }
        result = _select_variant(data)
        assert result == {"id": 1, "name": "第一个"}

    def test_select_variant_single_variant(self):
        """只有一个 variant"""
        data = {"variants": [{"content": "唯一内容"}]}
        result = _select_variant(data)
        assert result == {"content": "唯一内容"}

    def test_select_variant_empty_variants_list(self):
        """variants 为空列表"""
        data = {"variants": []}
        result = _select_variant(data)
        assert result == data

    def test_select_variant_no_variants_key(self):
        """没有 variants 键"""
        data = {"sections": [{"title": "测试"}]}
        result = _select_variant(data)
        assert result == data

    def test_select_variant_variants_not_list(self):
        """variants 不是列表"""
        data = {"variants": "not a list"}
        result = _select_variant(data)
        assert result == data

    def test_select_variant_not_dict(self):
        """输入不是字典"""
        data = ["a", "b", "c"]
        result = _select_variant(data)
        assert result == data

    def test_select_variant_none_input(self):
        """输入为 None"""
        result = _select_variant(None)
        assert result is None

    def test_select_variant_empty_dict(self):
        """输入为空字典"""
        data = {}
        result = _select_variant(data)
        assert result == {}

    def test_select_variant_variants_none(self):
        """variants 为 None"""
        data = {"variants": None}
        result = _select_variant(data)
        assert result == data


# =============================================================================
# optimize_sections 测试
# =============================================================================

class TestOptimizeSections:
    """optimize_sections 函数测试"""

    @pytest.mark.asyncio
    async def test_optimize_sections_empty_titles(self):
        """空 titles 列表返回原数据"""
        data = {"sections": [{"title": "测试", "content": "内容"}]}
        req = {"titles": []}
        result = await optimize_sections(data, req)
        assert result == data

    @pytest.mark.asyncio
    async def test_optimize_sections_no_titles_key(self):
        """没有 titles 键返回原数据"""
        data = {"sections": [{"title": "测试", "content": "内容"}]}
        req = {}
        result = await optimize_sections(data, req)
        assert result == data

    @pytest.mark.asyncio
    async def test_optimize_sections_none_titles(self):
        """titles 为 None 返回原数据"""
        data = {"sections": [{"title": "测试", "content": "内容"}]}
        req = {"titles": None}
        result = await optimize_sections(data, req)
        assert result == data

    @pytest.mark.asyncio
    async def test_optimize_sections_variant_not_dict(self):
        """variant 不是字典返回原数据"""
        data = ["not", "a", "dict"]
        req = {"titles": ["测试"]}
        result = await optimize_sections(data, req)
        assert result == data

    @pytest.mark.asyncio
    async def test_optimize_sections_with_variants(self):
        """有 variants 时使用第一个 variant"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化后的内容"})
        
        data = {
            "variants": [
                {"sections": [{"title": "章节A", "content": "原始内容A"}]}
            ]
        }
        req = {
            "titles": ["章节A"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 验证 sections 被修改
        assert result["variants"][0]["sections"][0]["content"] == "优化后的内容"
        assert result["variants"][0]["sections"][0]["optimized"] is True

    @pytest.mark.asyncio
    async def test_optimize_sections_matching_title(self):
        """只优化匹配的标题"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化后"})
        
        data = {
            "sections": [
                {"title": "章节A", "content": "内容A"},
                {"title": "章节B", "content": "内容B"}
            ]
        }
        req = {
            "titles": ["章节A"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 章节A 被优化
        assert result["sections"][0]["content"] == "优化后"
        assert result["sections"][0].get("optimized") is True
        # 章节B 未被优化
        assert result["sections"][1]["content"] == "内容B"
        assert result["sections"][1].get("optimized") is None

    @pytest.mark.asyncio
    async def test_optimize_sections_multiple_titles(self):
        """优化多个标题"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "已优化"})
        
        data = {
            "sections": [
                {"title": "A", "content": "原A"},
                {"title": "B", "content": "原B"},
                {"title": "C", "content": "原C"}
            ]
        }
        req = {
            "titles": ["A", "C"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        assert result["sections"][0]["optimized"] is True
        assert result["sections"][1].get("optimized") is None
        assert result["sections"][2]["optimized"] is True

    @pytest.mark.asyncio
    async def test_optimize_sections_llm_exception(self):
        """LLM 异常时跳过该章节"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=Exception("API Error"))
        
        data = {
            "sections": [{"title": "章节", "content": "原内容"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 异常时保持原内容
        assert result["sections"][0]["content"] == "原内容"
        assert result["sections"][0].get("optimized") is None

    @pytest.mark.asyncio
    async def test_optimize_sections_llm_returns_non_dict(self):
        """LLM 返回非字典时跳过"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value="plain string")
        
        data = {
            "sections": [{"title": "章节", "content": "原内容"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 返回非字典时保持原内容
        assert result["sections"][0]["content"] == "原内容"

    @pytest.mark.asyncio
    async def test_optimize_sections_llm_returns_dict_no_text(self):
        """LLM 返回字典但无 text 键时跳过"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"error": "something"})
        
        data = {
            "sections": [{"title": "章节", "content": "原内容"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 无 text 键时保持原内容
        assert result["sections"][0]["content"] == "原内容"

    @pytest.mark.asyncio
    async def test_optimize_sections_custom_instruction(self):
        """使用自定义指令"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        
        data = {
            "sections": [{"title": "章节", "content": "内容"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key",
            "instruction": "请简化表达"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            await optimize_sections(data, req)
        
        # 验证调用了 LLM
        mock_llm.complete.assert_called_once()
        call_args = mock_llm.complete.call_args[0][0]
        assert "请简化表达" in call_args

    @pytest.mark.asyncio
    async def test_optimize_sections_default_instruction(self):
        """使用默认指令"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        
        data = {
            "sections": [{"title": "章节", "content": "内容"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            await optimize_sections(data, req)
        
        call_args = mock_llm.complete.call_args[0][0]
        assert "请在保持证据引用的前提下优化本章表达" in call_args

    @pytest.mark.asyncio
    async def test_optimize_sections_load_defaults_when_no_provider(self):
        """无 provider 时加载默认配置"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        mock_defaults = {
            "provider": "default_provider",
            "model": "default_model",
            "api_key": "default_key"
        }
        
        data = {
            "sections": [{"title": "章节", "content": "内容"}]
        }
        req = {"titles": ["章节"]}
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient") as MockLLM:
            MockLLM.return_value = mock_llm
            MockLLM.load_defaults = MagicMock(return_value=mock_defaults)
            await optimize_sections(data, req)
        
        # 验证加载了默认配置
        MockLLM.load_defaults.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_sections_load_defaults_when_no_model(self):
        """有 provider 但无 model 时加载默认配置"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        mock_defaults = {"model": "default_model", "api_key": "default_key"}
        
        data = {
            "sections": [{"title": "章节", "content": "内容"}]
        }
        req = {"titles": ["章节"], "provider": "openai"}
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient") as MockLLM:
            MockLLM.return_value = mock_llm
            MockLLM.load_defaults = MagicMock(return_value=mock_defaults)
            await optimize_sections(data, req)
        
        MockLLM.load_defaults.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_sections_with_all_llm_params(self):
        """传递所有 LLM 参数"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        
        data = {
            "sections": [{"title": "章节", "content": "内容"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "baidu",
            "model": "ernie-4.0",
            "api_key": "ak",
            "base_url": "https://custom.url",
            "secret_key": "sk",
            "token_url": "https://token.url"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient") as MockLLM:
            MockLLM.return_value = mock_llm
            await optimize_sections(data, req)
        
        # 验证 LLMClient 使用正确的参数初始化
        MockLLM.assert_called_once_with(
            provider="baidu",
            model="ernie-4.0",
            api_key="ak",
            base_url="https://custom.url",
            secret_key="sk",
            token_url="https://token.url"
        )

    @pytest.mark.asyncio
    async def test_optimize_sections_empty_sections(self):
        """sections 为空列表"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        
        data = {"sections": []}
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        assert result["sections"] == []
        mock_llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_optimize_sections_no_sections_key(self):
        """没有 sections 键"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        
        data = {"other_key": "value"}
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        assert result == data
        mock_llm.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_optimize_sections_section_missing_title(self):
        """章节缺少 title"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "优化结果"})
        
        data = {
            "sections": [{"content": "内容无标题"}]
        }
        req = {
            "titles": [""],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 空标题匹配空 title
        assert result["sections"][0]["content"] == "优化结果"

    @pytest.mark.asyncio
    async def test_optimize_sections_section_missing_content(self):
        """章节缺少 content"""
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(return_value={"text": "生成内容"})
        
        data = {
            "sections": [{"title": "章节"}]
        }
        req = {
            "titles": ["章节"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # 空内容也会被处理
        assert result["sections"][0]["content"] == "生成内容"


# =============================================================================
# 集成测试
# =============================================================================

class TestOptimizerIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """完整工作流"""
        mock_llm = MagicMock()
        call_count = [0]
        
        async def mock_complete(prompt):
            call_count[0] += 1
            return {"text": f"优化内容{call_count[0]}"}
        
        mock_llm.complete = mock_complete
        
        data = {
            "variants": [
                {
                    "sections": [
                        {"title": "概述", "content": "原始概述"},
                        {"title": "技术方案", "content": "原始技术"},
                        {"title": "进度计划", "content": "原始进度"}
                    ]
                }
            ]
        }
        req = {
            "titles": ["概述", "技术方案"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "instruction": "优化表达"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        sections = result["variants"][0]["sections"]
        # 概述和技术方案被优化
        assert sections[0]["content"] == "优化内容1"
        assert sections[0]["optimized"] is True
        assert sections[1]["content"] == "优化内容2"
        assert sections[1]["optimized"] is True
        # 进度计划未被优化
        assert sections[2]["content"] == "原始进度"
        assert sections[2].get("optimized") is None

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        """部分章节优化失败"""
        mock_llm = MagicMock()
        call_count = [0]
        
        async def mock_complete(prompt):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("API Error")
            return {"text": f"优化内容{call_count[0]}"}
        
        mock_llm.complete = mock_complete
        
        data = {
            "sections": [
                {"title": "A", "content": "原A"},
                {"title": "B", "content": "原B"},
                {"title": "C", "content": "原C"}
            ]
        }
        req = {
            "titles": ["A", "B", "C"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "key"
        }
        
        with patch("backend.zhifei_autoplan.optimizer.LLMClient", return_value=mock_llm):
            result = await optimize_sections(data, req)
        
        # A 成功
        assert result["sections"][0]["content"] == "优化内容1"
        # B 失败，保持原内容
        assert result["sections"][1]["content"] == "原B"
        # C 成功
        assert result["sections"][2]["content"] == "优化内容3"
