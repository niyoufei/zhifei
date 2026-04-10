"""Unit tests for backend/zhifei_autoplan/agents/section_writer.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.zhifei_autoplan.agents.section_writer import SectionWriter, compact_text_to_length_bounds


class TestSectionWriterInit:
    """Test SectionWriter initialization."""

    def test_init_without_llm(self):
        """Test initialization without LLM client."""
        writer = SectionWriter()
        assert writer.llm is None

    def test_init_with_llm(self):
        """Test initialization with LLM client."""
        mock_llm = MagicMock()
        writer = SectionWriter(llm=mock_llm)
        assert writer.llm is mock_llm

    def test_compact_text_to_length_bounds_reduces_long_text(self):
        """Public helper should reduce long text into configured range."""
        source = ("工序：钢筋绑扎。设备：GW40弯曲机1台。参数：间距200mm，合格率≥98%。" * 20).strip()
        compacted = compact_text_to_length_bounds(source, min_length=120, max_length=300)
        assert compacted is not None
        assert 120 <= len(compacted) <= 300
        assert "GW40弯曲机1台" in compacted


class TestBuildPrompt:
    """Test _build_prompt method."""

    def test_build_prompt_minimal_context(self):
        """Test prompt with minimal context."""
        writer = SectionWriter()
        prompt = writer._build_prompt("工程概况", {})
        assert "工程概况" in prompt
        assert "章节标题" in prompt
        assert "总负责人" in prompt  # default role

    def test_build_prompt_with_requirements(self):
        """Test prompt includes requirements."""
        writer = SectionWriter()
        context = {"requirements": ["质量要求", "安全要求"]}
        prompt = writer._build_prompt("工程概况", context)
        assert "质量要求" in prompt
        assert "安全要求" in prompt

    def test_build_prompt_with_kg_evidence(self):
        """Test prompt includes KG evidence."""
        writer = SectionWriter()
        context = {"kg_evidence": ["证据1", "证据2"]}
        prompt = writer._build_prompt("施工方案", context)
        assert "证据1" in prompt
        assert "证据2" in prompt

    def test_build_prompt_with_doc_evidence(self):
        """Test prompt includes doc evidence."""
        writer = SectionWriter()
        context = {"doc_evidence": ["招标文件第3条", "图纸说明"]}
        prompt = writer._build_prompt("施工方案", context)
        assert "招标文件第3条" in prompt
        assert "图纸说明" in prompt

    def test_build_prompt_with_checklist(self):
        """Test prompt includes checklist."""
        writer = SectionWriter()
        context = {"checklist": ["检查点1", "检查点2"]}
        prompt = writer._build_prompt("质量管理", context)
        assert "检查点1" in prompt
        assert "检查点2" in prompt

    def test_build_prompt_with_weights(self):
        """Test prompt includes weights."""
        writer = SectionWriter()
        context = {"weights": ["权重1: 10分", "权重2: 20分"]}
        prompt = writer._build_prompt("安全管理", context)
        assert "权重1" in prompt
        assert "权重2" in prompt

    def test_build_prompt_with_penalties(self):
        """Test prompt includes penalties."""
        writer = SectionWriter()
        context = {"penalties": ["扣分项1", "扣分项2"]}
        prompt = writer._build_prompt("进度计划", context)
        assert "扣分项1" in prompt
        assert "扣分项2" in prompt

    def test_build_prompt_with_custom_role(self):
        """Test prompt with custom agent role."""
        writer = SectionWriter()
        context = {"agent_role": "质量监督员"}
        prompt = writer._build_prompt("质量管理", context)
        assert "质量监督员" in prompt
        assert "总负责人" not in prompt

    def test_build_prompt_structure(self):
        """Test prompt has all expected sections."""
        writer = SectionWriter()
        context = {
            "requirements": ["req1"],
            "kg_evidence": ["kg1"],
            "doc_evidence": ["doc1"],
            "checklist": ["check1"],
            "weights": ["w1"],
            "penalties": ["p1"],
        }
        prompt = writer._build_prompt("测试章节", context)
        assert "【编制要求】" in prompt
        assert "【权重与扣分项】" in prompt
        assert "【知识图谱证据】" in prompt
        assert "【招标/清单/图纸证据】" in prompt
        assert "【合规检查要点】" in prompt
        assert "输出要求" in prompt


class TestFallback:
    """Test _fallback method."""

    def test_fallback_includes_title(self):
        """Test fallback content includes title."""
        writer = SectionWriter()
        result = writer._fallback("工程概况", {})
        assert "工程概况" in result

    def test_fallback_has_template_content(self):
        """Test fallback has template structure."""
        writer = SectionWriter()
        result = writer._fallback("施工方案", {})
        assert "本章量化控制要求如下" in result
        assert "巡检频次控制为" in result
        assert "关键偏差控制在" in result
        assert "风险→控制→验证" in result
        assert "风险：" in result and "控制：" in result and "验证：" in result
        assert "【证据:" in result
        assert "【范围】" not in result
        assert "【证据摘要】" not in result

    def test_fallback_can_use_doc_evidence_as_source(self):
        """Fallback may use doc_evidence as a traceable evidence source."""
        writer = SectionWriter()
        r1 = writer._fallback("章节A", {})
        r2 = writer._fallback("章节A", {"doc_evidence": ["样例.pdf#abcd@12: 片段"]})
        assert "章节A" in r1
        assert "章节A" in r2
        assert "【证据:" in r2
        assert "样例.pdf#abcd@12" in r2


class TestWrite:
    """Test async write method."""

    @pytest.mark.asyncio
    async def test_write_without_llm_returns_fallback(self):
        """Test write without LLM returns fallback content."""
        writer = SectionWriter(llm=None)
        result = await writer.write("工程概况", {})
        assert result["title"] == "工程概况"
        assert "prompt" in result
        assert "本章量化控制要求如下" in result["content"]
        assert "风险→控制→验证" in result["content"]
        assert "【证据:" in result["content"]

    @pytest.mark.asyncio
    async def test_write_without_llm_includes_prompt(self):
        """Test write without LLM still generates prompt."""
        writer = SectionWriter(llm=None)
        context = {"requirements": ["要求1"]}
        result = await writer.write("施工方案", context)
        assert "要求1" in result["prompt"]
        assert "施工方案" in result["prompt"]

    @pytest.mark.asyncio
    async def test_write_with_successful_llm_response(self):
        """Test write with successful LLM response."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "生成的章节内容...",
            "provider": "openai",
            "model": "gpt-4",
            "request_id": "req-1",
            "client_request_id": "client-1",
            "used_key_alias": "OPENAI_API_KEY_TEXT_MAIN",
            "latency_ms": 432,
            "token_usage": {"input_tokens": 120, "output_tokens": 66, "total_tokens": 186},
            "cache_hit": True,
            "cached_tokens": 32,
        }
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("工程概况", {})
        assert result["title"] == "工程概况"
        assert result["content"] == "生成的章节内容..."
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4"
        assert result["request_id"] == "req-1"
        assert result["client_request_id"] == "client-1"
        assert result["used_key_alias"] == "OPENAI_API_KEY_TEXT_MAIN"
        assert result["latency_ms"] == 432
        assert result["token_usage"]["total_tokens"] == 186
        assert result["cache_hit"] is True
        assert result["cached_tokens"] == 32
        assert len(result["resource_usage_attempts"]) == 1
        assert result["resource_usage_attempts"][0]["attempt"] == 1
        assert result["resource_usage_attempts"][0]["token_usage"]["input_tokens"] == 120
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_with_empty_llm_response_uses_fallback(self):
        """Test write falls back when LLM returns empty text."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "",
            "provider": "openai",
            "model": "gpt-4",
        }
        writer = SectionWriter(llm=mock_llm)
        context = {"kg_evidence": ["证据A", "证据B"], "doc_evidence": ["文档C"]}
        result = await writer.write("施工方案", context)
        assert "本章量化控制要求如下" in result["content"]
        assert "【证据摘要】" not in result["content"]
        assert "证据A" not in result["content"]
        assert "文档C" in result["content"]

    @pytest.mark.asyncio
    async def test_write_with_whitespace_only_uses_fallback(self):
        """Test write falls back when LLM returns whitespace only."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {"text": "   \n\t  "}
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("质量管理", {})
        assert "本章量化控制要求如下" in result["content"]
        assert "【证据摘要】" not in result["content"]

    @pytest.mark.asyncio
    async def test_write_with_llm_error_uses_fallback(self):
        """Test write falls back when LLM returns error."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "some text",
            "error": "API rate limit exceeded",
        }
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("安全管理", {})
        assert "本章量化控制要求如下" in result["content"]
        assert "【证据摘要】" not in result["content"]
        assert result["error"] == "API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_write_evidence_limit_in_fallback(self):
        """Fallback should use a traceable source without leaking evidence summary lists."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {"text": ""}
        writer = SectionWriter(llm=mock_llm)
        context = {
            "kg_evidence": ["kg1", "kg2", "kg3", "kg4", "kg5"],
            "doc_evidence": ["doc1", "doc2", "doc3", "doc4", "doc5"],
        }
        result = await writer.write("进度计划", context)
        content = result["content"]
        assert "kg1" not in content
        assert "doc1" in content
        assert "doc2" not in content
        assert "doc4" not in content

    @pytest.mark.asyncio
    async def test_write_result_structure(self):
        """Test write result has all expected keys."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "内容",
            "provider": "test",
            "model": "test-model",
            "error": None,
        }
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("章节", {})
        assert "title" in result
        assert "content" in result
        assert "prompt" in result
        assert "provider" in result
        assert "model" in result
        assert "error" in result

    @pytest.mark.asyncio
    async def test_write_overlong_response_is_compacted_not_failed(self):
        """Overlong but usable content should be compacted into the requested range."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": (
                "工序：钢筋绑扎。设备：GW40弯曲机1台，钢筋切断机1台。"
                "参数：间距200mm，保护层厚度25mm，抽检频次每100m2一次，合格率≥98%。"
                "责任：施工员复核，质检员每班检查，形成《钢筋检验批验收记录》。"
            )
            * 12,
            "provider": "openai",
            "model": "gpt-5.4",
        }
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("钢筋工程", {}, min_length=120, max_length=420)
        logs = result.get("constraint_log") or []
        content = str(result.get("content") or "")

        assert result.get("error") in ("", None)
        assert len(content) <= 420
        assert len(content) >= 120
        assert any(item.get("status") == "compacted" for item in logs)
        assert "GW40弯曲机1台" in content
        assert "间距200mm" in content
        assert "合格率≥98%" in content

    @pytest.mark.asyncio
    async def test_write_underlength_still_falls_back_after_retry(self):
        """Too-short output remains a hard failure and should still fall back."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "间距200mm，责任到人。",
            "provider": "openai",
            "model": "gpt-5.4",
        }
        writer = SectionWriter(llm=mock_llm, max_retry=2)
        result = await writer.write("钢筋工程", {}, min_length=80, max_length=180)
        logs = result.get("constraint_log") or []

        assert mock_llm.complete.call_count == 2
        assert "本章量化控制要求如下" in str(result.get("content") or "")
        assert any("length_out_of_range" in str(item.get("reason") or "") for item in logs)
        assert any(item.get("status") == "fallback" for item in logs)
        assert len(result["resource_usage_attempts"]) == 2
        assert result["resource_usage_attempts"][0]["attempt"] == 1
        assert result["resource_usage_attempts"][1]["attempt"] == 2


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_write_with_none_in_response(self):
        """Test handling None text in LLM response."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {"text": None}
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("章节", {})
        # None should be treated as empty, triggering fallback
        assert "【证据摘要】" not in result["content"]
        assert "本章量化控制要求如下" in result["content"]

    @pytest.mark.asyncio
    async def test_write_with_unicode_title(self):
        """Test handling Unicode characters in title."""
        writer = SectionWriter(llm=None)
        result = await writer.write("第一章：工程概况（总论）", {})
        assert result["title"] == "第一章：工程概况（总论）"
        assert "第一章" in result["content"]

    def test_build_prompt_with_empty_lists(self):
        """Test build_prompt with all empty lists."""
        writer = SectionWriter()
        context = {
            "requirements": [],
            "kg_evidence": [],
            "doc_evidence": [],
            "checklist": [],
            "weights": [],
            "penalties": [],
        }
        prompt = writer._build_prompt("空章节", context)
        assert "空章节" in prompt
        # Prompt should still be valid
        assert "章节标题" in prompt

    def test_build_prompt_with_multiline_content(self):
        """Test build_prompt with multiline evidence."""
        writer = SectionWriter()
        context = {
            "requirements": ["第一条\n  - 子条款1\n  - 子条款2"],
            "kg_evidence": ["证据1\n详细说明\n多行内容"],
        }
        prompt = writer._build_prompt("复杂章节", context)
        assert "子条款1" in prompt
        assert "子条款2" in prompt
        assert "详细说明" in prompt

    @pytest.mark.asyncio
    async def test_write_concurrent_calls(self):
        """Test multiple concurrent write calls."""
        import asyncio

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {"text": "内容"}
        writer = SectionWriter(llm=mock_llm)

        results = await asyncio.gather(
            writer.write("章节1", {}),
            writer.write("章节2", {}),
            writer.write("章节3", {}),
        )
        assert len(results) == 3
        assert results[0]["title"] == "章节1"
        assert results[1]["title"] == "章节2"
        assert results[2]["title"] == "章节3"
        assert mock_llm.complete.call_count == 3

    @pytest.mark.asyncio
    async def test_write_with_special_characters_in_context(self):
        """Test handling special characters in context."""
        writer = SectionWriter(llm=None)
        context = {
            "requirements": ["要求<script>", "要求&nbsp;"],
            "kg_evidence": ["证据'引号'", '证据"双引号"'],
        }
        result = await writer.write("特殊章节", context)
        # Should not crash
        assert result["title"] == "特殊章节"
        assert "<script>" in result["prompt"]

    def test_fallback_different_titles(self):
        """Test fallback generates different content for different titles."""
        writer = SectionWriter()
        r1 = writer._fallback("章节A", {})
        r2 = writer._fallback("章节B", {})
        assert r1 != r2
        assert "章节A" in r1
        assert "章节B" in r2
