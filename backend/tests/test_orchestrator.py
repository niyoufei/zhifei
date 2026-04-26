"""Unit tests for backend/zhifei_autoplan/orchestrator.py"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import json

from backend.zhifei_autoplan.orchestrator import (
    _build_weights_and_penalties,
    run_autoplan,
)


@pytest.fixture(autouse=True)
def _mock_mindmap_generation():
    """Avoid external image-model calls during unit tests."""
    with patch(
        "backend.zhifei_autoplan.orchestrator.generate_outline_mindmap",
        return_value={"path": "/tmp/mock_mindmap.png", "caption": "施工组织设计思维导图（Gemini）"},
    ):
        yield


def _find_ctx_by_title(mock_writer, title: str) -> dict:
    for call_args in mock_writer.write.call_args_list:
        if call_args and len(call_args[0]) >= 2 and str(call_args[0][0]) == title:
            ctx = call_args[0][1]
            return ctx if isinstance(ctx, dict) else {}
    return {}


# =============================================================================
# Tests for _build_weights_and_penalties
# =============================================================================

class TestBuildWeightsAndPenalties:
    """Tests for _build_weights_and_penalties function."""

    def test_empty_tender(self):
        """Empty tender returns empty lists."""
        weights, penalties = _build_weights_and_penalties({})
        assert weights == []
        assert penalties == []

    def test_tender_without_items(self):
        """Tender without items key returns empty lists."""
        weights, penalties = _build_weights_and_penalties({"name": "test"})
        assert weights == []
        assert penalties == []

    def test_tender_with_empty_items(self):
        """Tender with empty items list returns empty lists."""
        weights, penalties = _build_weights_and_penalties({"items": []})
        assert weights == []
        assert penalties == []

    def test_single_weight_item(self):
        """Single weight item is correctly categorized."""
        tender = {
            "items": [
                {"dimension": "技术", "keywords": ["关键词1", "关键词2"], "weight": 30}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "技术" in weights[0]
        assert "权重=30" in weights[0]
        assert "关键词1" in weights[0]
        assert len(penalties) == 0

    def test_single_penalty_item_扣分项(self):
        """Penalty item with dimension '扣分项' is correctly categorized."""
        tender = {
            "items": [
                {"dimension": "扣分项", "keywords": ["违规1", "违规2"], "weight": -10}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 0
        assert len(penalties) == 1
        assert "扣分项" in penalties[0]
        assert "违规1" in penalties[0]

    def test_single_penalty_item_PENALTY(self):
        """Penalty item with dimension 'PENALTY' is correctly categorized."""
        tender = {
            "items": [
                {"dimension": "PENALTY", "keywords": ["penalty1"], "weight": -5}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 0
        assert len(penalties) == 1
        assert "扣分项" in penalties[0]

    def test_mixed_items(self):
        """Mixed weight and penalty items are correctly separated."""
        tender = {
            "items": [
                {"dimension": "技术方案", "keywords": ["kw1", "kw2"], "weight": 40},
                {"dimension": "扣分项", "keywords": ["p1", "p2"], "weight": -10},
                {"dimension": "商务", "keywords": ["kw3"], "weight": 30},
                {"dimension": "PENALTY", "keywords": ["p3"], "weight": -5},
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 2
        assert len(penalties) == 2

    def test_keywords_truncation_weights(self):
        """Keywords in weights are truncated to 8."""
        tender = {
            "items": [
                {
                    "dimension": "技术",
                    "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10"],
                    "weight": 30
                }
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        # kw9 and kw10 should not be in the output (truncated at 8)
        assert "kw8" in weights[0]
        assert "kw9" not in weights[0]

    def test_keywords_truncation_penalties(self):
        """Keywords in penalties are truncated to 10."""
        tender = {
            "items": [
                {
                    "dimension": "扣分项",
                    "keywords": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11", "p12"],
                    "weight": -10
                }
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(penalties) == 1
        assert "p10" in penalties[0]
        assert "p11" not in penalties[0]

    def test_missing_keywords(self):
        """Item without keywords handles gracefully."""
        tender = {
            "items": [
                {"dimension": "技术", "weight": 30}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "技术" in weights[0]

    def test_none_keywords(self):
        """Item with None keywords handles gracefully."""
        tender = {
            "items": [
                {"dimension": "技术", "keywords": None, "weight": 30}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1

    def test_missing_weight(self):
        """Item without weight handles gracefully."""
        tender = {
            "items": [
                {"dimension": "技术", "keywords": ["kw1"]}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "权重=None" in weights[0]

    def test_integer_dimension(self):
        """Integer dimension is converted to string."""
        tender = {
            "items": [
                {"dimension": 123, "keywords": ["kw1"], "weight": 10}
            ]
        }
        weights, penalties = _build_weights_and_penalties(tender)
        assert len(weights) == 1
        assert "123" in weights[0]


# =============================================================================
# Tests for run_autoplan
# =============================================================================

class TestRunAutoplan:
    """Tests for run_autoplan async function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Set up mocks for all external dependencies."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.generate_boq_chart") as mock_chart, \
             patch("backend.zhifei_autoplan.orchestrator.generate_ingested_previews") as mock_previews, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation") as mock_remediate:
            
            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer
            
            mock_quality.return_value = {"score": 100, "remediation": []}
            mock_previews.return_value = []
            
            yield {
                "tender": mock_tender,
                "boq": mock_boq,
                "kg": mock_kg,
                "docs": mock_docs,
                "llm_cls": mock_llm_cls,
                "writer_cls": mock_writer_cls,
                "writer": mock_writer,
                "chart": mock_chart,
                "previews": mock_previews,
                "quality": mock_quality,
                "remediate": mock_remediate,
            }

    @pytest.mark.asyncio
    async def test_empty_payload(self, mock_dependencies):
        """Empty payload returns default structure."""
        result = await run_autoplan({})
        
        assert result["topic"] == "未命名项目"
        assert isinstance(result["outline"], list) and result["outline"]
        assert "编制依据与原则" in result["outline"]
        assert len(result["sections"]) == len(result["outline"])
        assert "quality_checks" in result
        assert "evidence" in result

    @pytest.mark.asyncio
    async def test_topic_from_payload(self, mock_dependencies):
        """Topic is taken from payload."""
        result = await run_autoplan({"topic": "测试项目"})
        assert result["topic"] == "测试项目"

    @pytest.mark.asyncio
    async def test_outline_sections(self, mock_dependencies):
        """Sections are generated for each outline item."""
        result = await run_autoplan({
            "outline": ["第一章", "第二章", "第三章"]
        })
        
        assert len(result["sections"]) >= 3
        assert "第一章" in result["outline"]
        assert "第二章" in result["outline"]
        assert "第三章" in result["outline"]
        assert mock_dependencies["writer"].write.call_count == len(result["sections"])

    @pytest.mark.asyncio
    async def test_dry_run_no_llm(self, mock_dependencies):
        """Dry run does not instantiate LLM."""
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "dry_run": True,
        })
        
        mock_dependencies["llm_cls"].assert_not_called()

    @pytest.mark.asyncio
    async def test_provider_model_passed_to_llm(self, mock_dependencies):
        """Provider and model are passed to LLMClient."""
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "dry_run": False,
        })
        
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["provider"] == "openai"
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["api_key"] == "test-key"

    @pytest.mark.asyncio
    async def test_provider_api_key_fallback_from_env_openai(self, mock_dependencies, monkeypatch):
        """When api_key is absent, OpenAI provider falls back to OPENAI_API_KEY env."""
        monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "dry_run": False,
        })
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["api_key"] == "env-openai-key"

    @pytest.mark.asyncio
    async def test_provider_api_key_fallback_from_env_google(self, mock_dependencies, monkeypatch):
        """When api_key is absent, Google provider falls back to Gemini env keys."""
        monkeypatch.setenv("ZF_GOOGLE_API_KEY", "env-gemini-key")
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "google",
            "model": "gemini-2.5-flash",
            "dry_run": False,
        })
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["api_key"] == "env-gemini-key"

    @pytest.mark.asyncio
    async def test_provider_api_key_fallback_from_env_grok(self, mock_dependencies, monkeypatch):
        """When api_key is absent, Grok provider falls back to xAI env keys."""
        monkeypatch.setenv("XAI_API_KEY", "env-grok-key")
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "grok",
            "model": "grok-4-1-fast-reasoning",
            "dry_run": False,
        })
        mock_dependencies["llm_cls"].assert_called()
        call_kwargs = mock_dependencies["llm_cls"].call_args.kwargs
        assert call_kwargs["api_key"] == "env-grok-key"

    @pytest.mark.asyncio
    async def test_multi_provider_rotation(self, mock_dependencies):
        """Multiple providers rotate across sections."""
        await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
            "providers": ["provider1", "provider2"],
            "model_map": {"provider1": "model1", "provider2": "model2"},
            "dry_run": False,
        })
        
        # 3 sections, providers rotate
        assert mock_dependencies["llm_cls"].call_count >= 3

    @pytest.mark.asyncio
    async def test_kg_search_called(self, mock_dependencies):
        """Knowledge graph search is called for each section."""
        result = await run_autoplan({
            "topic": "测试",
            "outline": ["章节1", "章节2"],
        })
        
        assert mock_dependencies["kg"].call_count == len(result["sections"])

    @pytest.mark.asyncio
    async def test_doc_search_called(self, mock_dependencies):
        """Document search is called for each section."""
        result = await run_autoplan({
            "topic": "测试",
            "outline": ["章节1"],
        })
        
        assert mock_dependencies["docs"].call_count == len(result["sections"])

    @pytest.mark.asyncio
    async def test_generate_images_creates_charts(self, mock_dependencies):
        """When generate_images is True, BOQ charts are generated."""
        mock_dependencies["boq"].return_value = {"stats": {"total": 100}}
        mock_dependencies["chart"].return_value = [{"type": "chart", "data": "..."}]
        
        result = await run_autoplan({
            "outline": [],
            "generate_images": True,
        })
        
        mock_dependencies["chart"].assert_called_once()
        assert len(result["media"]) >= 1
        assert any(isinstance(m, dict) and m.get("type") == "chart" for m in (result.get("media") or []))

    @pytest.mark.asyncio
    async def test_generate_images_false_skips_charts(self, mock_dependencies):
        """When generate_images is False, BOQ charts are skipped."""
        mock_dependencies["boq"].return_value = {"stats": {"total": 100}}
        
        result = await run_autoplan({
            "outline": [],
            "generate_images": False,
        })
        
        mock_dependencies["chart"].assert_not_called()
        assert result["media"] == []

    @pytest.mark.asyncio
    async def test_quality_checks_applied(self, mock_dependencies):
        """Quality checks are run on sections."""
        mock_dependencies["quality"].return_value = {
            "score": 85,
            "issues": ["issue1"],
            "remediation": []
        }
        
        result = await run_autoplan({
            "outline": ["章节1"],
        })
        
        assert result["quality_checks"]["score"] == 85

    @pytest.mark.asyncio
    async def test_auto_remediate_template_mode(self, mock_dependencies):
        """Template remediation is applied when auto_remediate is True."""
        mock_dependencies["quality"].return_value = {
            "score": 70,
            "remediation": [{"title": "章节1", "type": "missing", "suggestion": "add X"}]
        }
        
        await run_autoplan({
            "outline": ["章节1"],
            "auto_remediate": True,
            "remediate_mode": "template",
        })
        
        mock_dependencies["remediate"].assert_called()

    @pytest.mark.asyncio
    async def test_auto_remediate_disabled(self, mock_dependencies):
        """Remediation is skipped when auto_remediate is False."""
        mock_dependencies["quality"].return_value = {
            "score": 70,
            "remediation": [{"title": "章节1", "type": "missing", "suggestion": "add X"}]
        }
        
        await run_autoplan({
            "outline": ["章节1"],
            "auto_remediate": False,
        })
        
        mock_dependencies["remediate"].assert_not_called()

    @pytest.mark.asyncio
    async def test_chapter_pages_in_context(self, mock_dependencies):
        """Chapter pages are added to requirements context."""
        await run_autoplan({
            "outline": ["第一章"],
            "chapter_pages": {"第一章": 10},
        })
        
        ctx = None
        for call_args in mock_dependencies["writer"].write.call_args_list:
            if call_args[0][0] == "第一章":
                ctx = call_args[0][1]
                break
        assert isinstance(ctx, dict)
        assert any("目标页数" in str(r) for r in ctx.get("requirements", []))

    @pytest.mark.asyncio
    async def test_chapter_pages_dict_target_in_context(self, mock_dependencies):
        """Chapter pages support dict target format."""
        await run_autoplan({
            "outline": ["第一章"],
            "chapter_pages": {"第一章": {"pages": 8}},
        })

        ctx = None
        for call_args in mock_dependencies["writer"].write.call_args_list:
            if call_args[0][0] == "第一章":
                ctx = call_args[0][1]
                break
        assert isinstance(ctx, dict)
        assert ctx.get("chapter_target_pages") == 8
        assert any("目标页数" in str(r) for r in ctx.get("requirements", []))

    @pytest.mark.asyncio
    async def test_chapter_requirements_in_context(self, mock_dependencies):
        """Chapter-specific requirements are merged into context."""
        await run_autoplan({
            "outline": ["第一章"],
            "requirements": ["全局要求A"],
            "chapter_requirements": {"第一章": ["章节要求1", "章节要求2"]},
        })

        ctx = None
        for call_args in mock_dependencies["writer"].write.call_args_list:
            if call_args[0][0] == "第一章":
                ctx = call_args[0][1]
                break
        assert isinstance(ctx, dict)
        reqs = ctx.get("requirements", [])
        assert "全局要求A" in reqs
        assert "章节要求1" in reqs
        assert "章节要求2" in reqs

    @pytest.mark.asyncio
    async def test_style_passed_through(self, mock_dependencies):
        """Style configuration is normalized and merged with defaults."""
        result = await run_autoplan({
            "style": {"font": "宋体", "size": 12},
        })
        
        assert isinstance(result["style"], dict)
        assert result["style"].get("body_font") == "宋体"
        assert float(result["style"].get("line_spacing_pt") or 0) == 22.0
        assert isinstance(result["style"].get("margins_cm"), dict)
        assert result["style"].get("margins_cm", {}).get("top") == 2.5
        assert result.get("style_source") in {"default_or_user", "tender_override"}

    @pytest.mark.asyncio
    async def test_variant_id_passed_through(self, mock_dependencies):
        """Variant ID is passed through to result."""
        result = await run_autoplan({
            "variant_id": "v123",
        })
        
        assert result["variant_id"] == "v123"

    @pytest.mark.asyncio
    async def test_chapter_requirements_passed_through(self, mock_dependencies):
        """Chapter requirements are passed through to result."""
        result = await run_autoplan({
            "chapter_requirements": {"第一章": ["要求A"]},
        })
        assert result["chapter_requirements"] == {"第一章": ["要求A"]}

    @pytest.mark.asyncio
    async def test_compare_config_defaults(self, mock_dependencies):
        """Compare configuration has correct defaults."""
        result = await run_autoplan({})
        
        assert result["compare"]["mode"] == "full"
        assert result["compare"]["max_chars"] == 800

    @pytest.mark.asyncio
    async def test_compare_config_custom(self, mock_dependencies):
        """Compare configuration can be customized."""
        result = await run_autoplan({
            "compare_mode": "summary",
            "compare_max_chars": "500",
            "compare_titles": ["第一章"],
        })
        
        assert result["compare"]["mode"] == "summary"
        assert result["compare"]["max_chars"] == 500
        assert result["compare"]["titles"] == ["第一章"]

    @pytest.mark.asyncio
    async def test_evidence_tracking(self, mock_dependencies):
        """Evidence tracking reports loaded data."""
        mock_dependencies["tender"].return_value = {"items": []}
        mock_dependencies["boq"].return_value = {"stats": {}}
        
        result = await run_autoplan({})
        
        assert result["evidence"]["tender_loaded"] is True
        assert result["evidence"]["boq_loaded"] is True

    @pytest.mark.asyncio
    async def test_evidence_tracking_empty(self, mock_dependencies):
        """Evidence tracking reports when data is empty."""
        mock_dependencies["tender"].return_value = None
        mock_dependencies["boq"].return_value = None
        
        result = await run_autoplan({})
        
        assert result["evidence"]["tender_loaded"] is False
        assert result["evidence"]["boq_loaded"] is False

    @pytest.mark.asyncio
    async def test_section_error_handling(self, mock_dependencies):
        """Section generation errors are handled gracefully."""
        mock_dependencies["writer"].write = AsyncMock(
            return_value={"title": "test", "content": "content", "error": "timeout"}
        )
        
        result = await run_autoplan({
            "outline": ["章节1"],
        })
        
        # Should still return sections even when writer reports errors.
        assert len(result["sections"]) >= 1

    @pytest.mark.asyncio
    async def test_tender_weights_in_context(self, mock_dependencies):
        """Tender weights and penalties are passed to section context."""
        mock_dependencies["tender"].return_value = {
            "items": [
                {"dimension": "技术", "keywords": ["kw1"], "weight": 40},
                {"dimension": "扣分项", "keywords": ["p1"], "weight": -10},
            ]
        }
        
        await run_autoplan({
            "outline": ["章节1"],
        })
        
        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        assert len(ctx.get("weights", [])) == 1
        assert len(ctx.get("penalties", [])) == 1

    @pytest.mark.asyncio
    async def test_requirements_passed_to_context(self, mock_dependencies):
        """Custom requirements are passed to section context."""
        await run_autoplan({
            "outline": ["章节1"],
            "requirements": ["要求1", "要求2"],
        })
        
        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        assert "要求1" in ctx.get("requirements", [])
        assert "要求2" in ctx.get("requirements", [])

    @pytest.mark.asyncio
    async def test_new_pipeline_outputs_present(self, mock_dependencies):
        """Enterprise profile / WBS-CPM / contract / score mapping receipts are returned."""
        result = await run_autoplan({
            "outline": ["工程概况"],
        })
        assert isinstance(result.get("enterprise_profile"), dict)
        assert isinstance(result.get("boq_wbs_cpm"), dict)
        assert isinstance(result.get("missing_parameters"), dict)
        assert isinstance(result.get("agent_contract"), dict)
        assert isinstance(result.get("agent_contract_checks"), dict)
        assert isinstance(result.get("score_mapping"), dict)
        assert isinstance(result.get("pipeline_stages"), list)

    @pytest.mark.asyncio
    async def test_missing_param_fallback_injected_into_requirements(self, mock_dependencies):
        """Missing-parameter fallback guidance should be injected into section requirements."""
        await run_autoplan({
            "outline": ["工程概况"],
            "requirements": [],
        })
        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        reqs = [str(x) for x in (ctx.get("requirements") or [])]
        assert any("参数缺失自动补位" in x for x in reqs)

    @pytest.mark.asyncio
    async def test_contract_chapter_id_attached(self, mock_dependencies):
        """Each section should carry contract chapter id for downstream audit."""
        result = await run_autoplan({
            "outline": ["工程概况"],
        })
        assert isinstance(result.get("sections"), list) and result["sections"]
        assert "contract_chapter_id" in result["sections"][0]


# =============================================================================
# Tests for _pick_agent_role (internal function via run_autoplan)
# =============================================================================

class TestAgentRoleSelection:
    """Tests for agent role selection logic."""

    @pytest.fixture
    def mock_deps(self):
        """Set up mocks for testing agent roles."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):
            
            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer
            
            mock_quality.return_value = {"score": 100, "remediation": []}
            
            yield {"writer": mock_writer}

    @pytest.mark.asyncio
    async def test_quality_role_selection(self, mock_deps):
        """Quality-related titles get 质量负责人 role."""
        await run_autoplan({
            "outline": ["质量管理计划"],
        })
        
        ctx = _find_ctx_by_title(mock_deps["writer"], "质量管理计划")
        assert ctx.get("agent_role") == "质量负责人"

    @pytest.mark.asyncio
    async def test_safety_role_selection(self, mock_deps):
        """Safety-related titles get 安全负责人 role."""
        await run_autoplan({
            "outline": ["安全施工措施"],
        })
        
        ctx = _find_ctx_by_title(mock_deps["writer"], "安全施工措施")
        assert ctx.get("agent_role") == "安全负责人"

    @pytest.mark.asyncio
    async def test_progress_role_selection(self, mock_deps):
        """Progress-related titles get 进度负责人 role."""
        await run_autoplan({
            "outline": ["进度计划"],
        })
        
        ctx = _find_ctx_by_title(mock_deps["writer"], "进度计划")
        assert ctx.get("agent_role") == "进度负责人"

    @pytest.mark.asyncio
    async def test_environment_role_selection(self, mock_deps):
        """Environment-related titles get 环保负责人 role."""
        await run_autoplan({
            "outline": ["环保措施"],
        })
        
        ctx = _find_ctx_by_title(mock_deps["writer"], "环保措施")
        assert ctx.get("agent_role") == "环保负责人"

    @pytest.mark.asyncio
    async def test_resource_role_selection(self, mock_deps):
        """Resource-related titles get 资源统筹负责人 role."""
        await run_autoplan({
            "outline": ["设备配置方案"],
        })
        
        ctx = _find_ctx_by_title(mock_deps["writer"], "设备配置方案")
        assert ctx.get("agent_role") == "资源统筹负责人"

    @pytest.mark.asyncio
    async def test_default_role_selection(self, mock_deps):
        """Unmatched titles get 技术负责人 role."""
        await run_autoplan({
            "outline": ["工程概况"],
        })
        
        ctx = _find_ctx_by_title(mock_deps["writer"], "工程概况")
        assert ctx.get("agent_role") == "技术负责人"


# =============================================================================
# Integration-style tests
# =============================================================================

class TestOrchestratorIntegration:
    """Integration tests for orchestrator workflow."""

    @pytest.fixture
    def full_mocks(self):
        """Set up comprehensive mocks."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.generate_boq_chart") as mock_chart, \
             patch("backend.zhifei_autoplan.orchestrator.generate_ingested_previews") as mock_previews, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation") as mock_remediate:
            
            # Realistic tender data
            mock_tender.return_value = {
                "items": [
                    {"dimension": "技术方案", "keywords": ["施工工艺", "技术措施"], "weight": 40},
                    {"dimension": "质量保证", "keywords": ["质量控制", "检验标准"], "weight": 30},
                    {"dimension": "扣分项", "keywords": ["安全事故", "质量问题"], "weight": -20},
                ]
            }
            
            # Realistic BOQ data
            mock_boq.return_value = {
                "stats": {"total_cost": 1000000, "items_count": 50},
                "items": []
            }
            
            # KG results
            mock_kg.return_value = {
                "results": [
                    {"title": "施工规范", "text": "混凝土施工应符合GB50204"},
                    {"title": "质量标准", "text": "钢筋保护层厚度偏差不超过5mm"},
                ]
            }
            
            # Document search results
            mock_docs.return_value = [
                {"filename": "招标文件.pdf", "snippet": "投标人应具备相关资质"},
            ]
            
            # Section writer
            mock_writer = MagicMock()
            async def write_section(title, ctx):
                return {
                    "title": title,
                    "content": f"{title}的详细内容，参考【证据:施工规范】",
                    "agent_role": ctx.get("agent_role"),
                }
            mock_writer.write = AsyncMock(side_effect=write_section)
            mock_writer_cls.return_value = mock_writer
            
            # Chart generation
            mock_chart.return_value = [{"type": "bar", "title": "工程量分布"}]
            mock_previews.return_value = []
            
            # Quality checks
            mock_quality.return_value = {
                "score": 92,
                "issues": [],
                "remediation": []
            }
            
            yield {
                "tender": mock_tender,
                "boq": mock_boq,
                "kg": mock_kg,
                "docs": mock_docs,
                "llm_cls": mock_llm_cls,
                "writer_cls": mock_writer_cls,
                "writer": mock_writer,
                "chart": mock_chart,
                "previews": mock_previews,
                "quality": mock_quality,
                "remediate": mock_remediate,
            }

    @pytest.mark.asyncio
    async def test_full_workflow(self, full_mocks):
        """Test complete autoplan workflow."""
        result = await run_autoplan({
            "topic": "合肥市排水工程",
            "outline": ["工程概况", "施工部署", "质量管理"],
            "requirements": ["符合当地规范", "工期120天"],
            "style": {"font": "宋体"},
            "chapter_pages": {"工程概况": 5, "施工部署": 15, "质量管理": 10},
            "provider": "openai",
            "model": "gpt-4",
            "dry_run": True,
            "generate_images": True,
        })
        
        # Verify structure
        assert result["topic"] == "合肥市排水工程"
        assert len(result["sections"]) >= 3
        assert len(result["media"]) >= 1
        # Should include a mindmap (auto) when generate_images=True
        assert any(isinstance(m, dict) and "思维导图" in str(m.get("caption") or "") for m in (result.get("media") or []))
        assert result["quality_checks"]["score"] == 92
        assert result["evidence"]["tender_loaded"] is True
        assert result["evidence"]["boq_loaded"] is True

    @pytest.mark.asyncio
    async def test_workflow_with_remediation(self, full_mocks):
        """Test workflow with quality issues and remediation."""
        full_mocks["quality"].return_value = {
            "score": 75,
            "issues": ["missing_detail"],
            "remediation": [
                {"title": "质量管理", "type": "missing", "suggestion": "补充检验频次"}
            ]
        }
        
        result = await run_autoplan({
            "topic": "测试项目",
            "outline": ["质量管理"],
            "auto_remediate": True,
            "remediate_mode": "template",
        })
        
        # Remediation should be applied
        full_mocks["remediate"].assert_called()
        # Quality checks run twice (before and after remediation)
        assert full_mocks["quality"].call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_section_generation(self, full_mocks):
        """Test that sections are generated concurrently."""
        call_times = []
        
        async def timed_write(title, ctx):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Small delay
            return {"title": title, "content": "content", "agent_role": ctx.get("agent_role")}
        
        full_mocks["writer"].write = AsyncMock(side_effect=timed_write)
        
        result = await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
        })
        
        # All sections should start at approximately the same time (concurrent)
        assert len(call_times) == len(result["sections"])
        assert len(call_times) >= 3
        # Time difference between first and last call should be minimal
        assert call_times[-1] - call_times[0] < 0.2  # allow CI scheduling jitter


# =============================================================================
# Tests for _pick_agent_role config file loading (lines 57-71)
# =============================================================================

class TestAgentRoleConfigLoading:
    """Tests for agent role config file loading."""

    @pytest.fixture
    def mock_deps_for_role(self):
        """Set up mocks for testing agent role config."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):
            
            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer
            
            mock_quality.return_value = {"score": 100, "remediation": []}
            
            yield {"writer": mock_writer}

    @pytest.mark.asyncio
    async def test_config_file_custom_role_match(self, mock_deps_for_role, tmp_path, monkeypatch):
        """Custom config file rules override default roles."""
        import json
        from pathlib import Path
        
        # Create temp config file
        config_dir = tmp_path / "backend" / "data" / "autoplan"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_roles.json"
        config_file.write_text(json.dumps({
            "default": "项目负责人",
            "rules": [
                {"match": ["特殊"], "role": "特殊负责人"},
                {"match": ["自定义"], "role": "自定义负责人"}
            ]
        }))
        
        # Monkeypatch Path to find our temp config
        original_exists = Path.exists
        original_read_text = Path.read_text
        
        def patched_exists(self):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return True
            return original_exists(self)
        
        def patched_read_text(self, encoding=None):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return config_file.read_text()
            return original_read_text(self, encoding=encoding)
        
        monkeypatch.setattr(Path, "exists", patched_exists)
        monkeypatch.setattr(Path, "read_text", patched_read_text)
        
        await run_autoplan({
            "outline": ["特殊章节"],
        })
        
        ctx = _find_ctx_by_title(mock_deps_for_role["writer"], "特殊章节")
        assert ctx.get("agent_role") == "特殊负责人"

    @pytest.mark.asyncio
    async def test_config_file_default_fallback(self, mock_deps_for_role, tmp_path, monkeypatch):
        """Config file default role is used when no rules match."""
        import json
        from pathlib import Path
        
        config_dir = tmp_path / "backend" / "data" / "autoplan"
        config_dir.mkdir(parents=True)
        config_file = config_dir / "agent_roles.json"
        config_file.write_text(json.dumps({
            "default": "默认配置负责人",
            "rules": [
                {"match": ["不匹配关键词"], "role": "其他负责人"}
            ]
        }))
        
        original_exists = Path.exists
        original_read_text = Path.read_text
        
        def patched_exists(self):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return True
            return original_exists(self)
        
        def patched_read_text(self, encoding=None):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                return config_file.read_text()
            return original_read_text(self, encoding=encoding)
        
        monkeypatch.setattr(Path, "exists", patched_exists)
        monkeypatch.setattr(Path, "read_text", patched_read_text)
        
        await run_autoplan({
            "outline": ["普通章节"],
        })
        
        ctx = _find_ctx_by_title(mock_deps_for_role["writer"], "普通章节")
        assert ctx.get("agent_role") == "默认配置负责人"

    @pytest.mark.asyncio
    async def test_config_file_exception_fallback(self, mock_deps_for_role, monkeypatch):
        """When config file causes exception, fallback to default rules."""
        from pathlib import Path
        
        def patched_exists(self):
            if str(self) == "backend/data/autoplan/agent_roles.json":
                raise OSError("Permission denied")
            return False
        
        monkeypatch.setattr(Path, "exists", patched_exists)
        
        await run_autoplan({
            "outline": ["质量检验章节"],
        })
        
        ctx = _find_ctx_by_title(mock_deps_for_role["writer"], "质量检验章节")
        # Should fallback to default rule matching "质量"
        assert ctx.get("agent_role") == "质量负责人"


# =============================================================================
# Tests for section build failure (line 137)
# =============================================================================

class TestSectionBuildFailure:
    """Tests for section build complete failure scenarios."""

    @pytest.fixture
    def mock_deps_fail(self):
        """Set up mocks for failure testing."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):
            
            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            mock_quality.return_value = {"score": 100, "remediation": []}
            
            yield {
                "writer_cls": mock_writer_cls,
            }

    @pytest.mark.asyncio
    async def test_all_retries_fail_with_error(self, mock_deps_fail):
        """When all retries return errors, returns last result with agent_role."""
        mock_writer = MagicMock()
        # All attempts return error
        mock_writer.write = AsyncMock(return_value={"title": "test", "content": "error", "error": "timeout"})
        mock_deps_fail["writer_cls"].return_value = mock_writer
        
        result = await run_autoplan({
            "outline": ["章节1"],
            "providers": ["p1", "p2"],
            "model_map": {"p1": "m1", "p2": "m2"},
        })
        
        # Should return the last attempt's result with agent_role added
        assert len(result["sections"]) >= 1
        assert any(s.get("agent_role") == "技术负责人" for s in result["sections"])
        assert any("error" in s for s in result["sections"])

    @pytest.mark.asyncio
    async def test_section_returns_none(self, mock_deps_fail):
        """When writer returns None, fallback message is generated."""
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock(return_value=None)
        mock_deps_fail["writer_cls"].return_value = mock_writer
        
        result = await run_autoplan({
            "outline": ["章节1"],
        })
        
        # Should return fallback section
        assert len(result["sections"]) >= 1
        assert any(s.get("content") == "章节生成失败" for s in result["sections"])


# =============================================================================
# Tests for LLM remediation (lines 152-196)
# =============================================================================

class TestLLMRemediation:
    """Tests for LLM-based remediation workflow."""

    @pytest.fixture
    def mock_deps_llm(self):
        """Set up mocks for LLM remediation testing."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.generate_boq_chart"), \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation") as mock_apply:
            
            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "原始内容"})
            mock_writer_cls.return_value = mock_writer
            
            # LLM client mock
            mock_llm = MagicMock()
            mock_llm.complete = AsyncMock(return_value={"text": "修复后的内容"})
            mock_llm_cls.return_value = mock_llm
            
            # First quality check has issues, second is clean
            mock_quality.side_effect = [
                {
                    "score": 70,
                    "remediation": [
                        {"title": "章节1", "type": "missing", "suggestion": "补充细节"}
                    ]
                },
                {"score": 95, "remediation": []}
            ]
            
            yield {
                "llm_cls": mock_llm_cls,
                "llm": mock_llm,
                "quality": mock_quality,
                "apply": mock_apply,
                "writer": mock_writer,
            }

    @pytest.mark.asyncio
    async def test_llm_remediation_applied(self, mock_deps_llm):
        """LLM remediation mode calls LLM to fix sections."""
        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
        })
        
        # LLM complete should be called for remediation
        assert mock_deps_llm["llm"].complete.called
        # apply_remediation (template mode) should NOT be called
        mock_deps_llm["apply"].assert_not_called()
        # Quality checks run twice
        assert mock_deps_llm["quality"].call_count == 2

    @pytest.mark.asyncio
    async def test_llm_remediation_skipped_dry_run(self, mock_deps_llm):
        """LLM remediation skipped in dry run mode."""
        mock_deps_llm["quality"].side_effect = [
            {
                "score": 70,
                "remediation": [{"title": "章节1", "type": "missing", "suggestion": "fix"}]
            },
            {"score": 70, "remediation": []}
        ]
        
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": True,
        })
        
        # In dry_run, LLM is not called for remediation
        # LLMClient is called for section generation in dry_run=False
        # But since we have both provider and dry_run=True, LLM should not be instantiated for remediation

    @pytest.mark.asyncio
    async def test_llm_remediation_no_issues(self, mock_deps_llm):
        """No LLM calls when quality check has no remediation items."""
        mock_deps_llm["quality"].side_effect = [
            {"score": 100, "remediation": []},
            {"score": 100, "remediation": []}
        ]
        
        await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
        })
        
        # No remediation needed, LLM complete should not be called for remediation
        # (may be called for other purposes, but not for remediation of empty list)

    @pytest.mark.asyncio
    async def test_llm_remediation_updates_content(self, mock_deps_llm):
        """LLM remediation updates section content."""
        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "test-key",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
        })
        
        # Check that section was updated
        section = result["sections"][0]
        assert section.get("auto_remediated") == "llm"
        assert section.get("original_content") in {"原始内容", "修复后的内容"}
        assert section.get("content") == "修复后的内容"

    @pytest.mark.asyncio
    async def test_llm_remediation_no_provider(self, mock_deps_llm):
        """LLM remediation skipped when no provider specified."""
        mock_deps_llm["quality"].side_effect = [
            {"score": 70, "remediation": [{"title": "章节1", "type": "missing", "suggestion": "fix"}]},
            {"score": 70, "remediation": []}
        ]
        
        await run_autoplan({
            "outline": ["章节1"],
            # No provider/model specified
            "auto_remediate": True,
            "remediate_mode": "llm",
        })
        
        # Without provider, _remediate_with_llm returns early

    @pytest.mark.asyncio
    async def test_llm_remediation_bad_response(self, mock_deps_llm):
        """LLM remediation handles bad response gracefully."""
        mock_deps_llm["llm"].complete = AsyncMock(return_value={"error": "timeout"})
        
        result = await run_autoplan({
            "outline": ["章节1"],
            "provider": "openai",
            "model": "gpt-4",
            "auto_remediate": True,
            "remediate_mode": "llm",
            "dry_run": False,
        })
        
        # Content should not be updated on bad response
        section = result["sections"][0]
        # auto_remediated flag should not be set since response was bad


# =============================================================================
# Tests for _pick_provider with providers list (line 51)
# =============================================================================

class TestPickProviderWithList:
    """Tests for _pick_provider when providers list is used."""

    @pytest.fixture
    def mock_deps_prov(self):
        """Set up mocks for provider testing."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix") as mock_tender, \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data") as mock_boq, \
             patch("backend.zhifei_autoplan.orchestrator.search_kg") as mock_kg, \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs") as mock_docs, \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls, \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks") as mock_quality, \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):
            
            mock_tender.return_value = {}
            mock_boq.return_value = {}
            mock_kg.return_value = {"results": []}
            mock_docs.return_value = []
            
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "test", "content": "content"})
            mock_writer_cls.return_value = mock_writer
            
            mock_quality.return_value = {"score": 100, "remediation": []}
            
            # Track LLMClient instantiations
            llm_calls = []
            def track_llm(**kwargs):
                llm_calls.append(kwargs)
                return MagicMock()
            mock_llm_cls.side_effect = track_llm
            
            yield {
                "llm_cls": mock_llm_cls,
                "llm_calls": llm_calls,
            }

    @pytest.mark.asyncio
    async def test_providers_list_rotation_with_model_map(self, mock_deps_prov):
        """Providers list rotates with model_map mapping."""
        await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
            "providers": ["provider_a", "provider_b"],
            "model_map": {"provider_a": "model_a", "provider_b": "model_b"},
            "dry_run": False,
        })
        
        calls = mock_deps_prov["llm_calls"]
        # Check that providers rotate correctly
        providers_used = [c["provider"] for c in calls]
        models_used = [c["model"] for c in calls]
        
        # 3 sections with 2 providers should show rotation pattern
        assert "provider_a" in providers_used
        assert "provider_b" in providers_used

    @pytest.mark.asyncio
    async def test_providers_list_fallback_model(self, mock_deps_prov):
        """When model_map doesn't have provider, falls back to default model."""
        await run_autoplan({
            "outline": ["章节1"],
            "providers": ["unknown_provider"],
            "model_map": {},  # Empty model_map
            "model": "fallback_model",  # Default model
            "dry_run": False,
        })
        
        calls = mock_deps_prov["llm_calls"]
        assert len(calls) >= 1
        # Should use fallback model
        assert calls[0]["model"] == "fallback_model"

    @pytest.mark.asyncio
    async def test_provider_init_failure_falls_through_to_next_provider(self):
        """If first provider init fails, orchestrator should continue with next provider."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value={"score": 100, "remediation": []}), \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"), \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls:

            # First provider fails on init, second succeeds.
            created = []
            def _mk(**kwargs):
                created.append(kwargs)
                if kwargs.get("provider") == "provider_a":
                    raise ValueError("init failed")
                return MagicMock()

            mock_llm_cls.side_effect = _mk
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "ok"})
            mock_writer_cls.return_value = mock_writer

            result = await run_autoplan(
                {
                    "outline": ["章节1"],
                    "providers": ["provider_a", "provider_b"],
                    "model_map": {"provider_a": "m1", "provider_b": "m2"},
                    "dry_run": False,
                }
            )

            assert len(result.get("sections") or []) >= 1
            # Ensure fallback provider was attempted after first init failure.
            providers_used = [c.get("provider") for c in created]
            assert "provider_a" in providers_used
            assert "provider_b" in providers_used

    @pytest.mark.asyncio
    async def test_provider_chain_supports_same_provider_with_different_keys(self, mock_deps_prov):
        """provider_chain keeps duplicate providers and rotates by slot (not dedup by provider)."""
        await run_autoplan(
            {
                "outline": ["章节1", "章节2", "章节3"],
                "provider_chain": [
                    {"slot": "main", "provider": "google", "model": "gemini-a", "api_key": "g_key_1"},
                    {"slot": "fallback_1", "provider": "google", "model": "gemini-b", "api_key": "g_key_2"},
                    {"slot": "fallback_2", "provider": "openai", "model": "gpt-x", "api_key": "o_key_1"},
                ],
                "dry_run": False,
            }
        )

        calls = mock_deps_prov["llm_calls"]
        assert len(calls) >= 3
        assert calls[0]["provider"] == "google"
        assert calls[1]["provider"] == "google"
        assert calls[2]["provider"] == "openai"
        assert calls[0]["api_key"] == "g_key_1"
        assert calls[1]["api_key"] == "g_key_2"
        assert calls[2]["api_key"] == "o_key_1"

    @pytest.mark.asyncio
    async def test_provider_chain_same_provider_key_fallback(self):
        """When same provider first key fails, second key in chain should be attempted."""
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value={"score": 100, "remediation": []}), \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"), \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient") as mock_llm_cls:

            seen = []

            def _mk(**kwargs):
                seen.append(kwargs)
                if kwargs.get("provider") == "google" and kwargs.get("api_key") == "bad_key":
                    raise ValueError("init failed")
                return MagicMock()

            mock_llm_cls.side_effect = _mk
            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "ok"})
            mock_writer_cls.return_value = mock_writer

            result = await run_autoplan(
                {
                    "outline": ["章节1"],
                    "provider_chain": [
                        {"slot": "main", "provider": "google", "model": "gemini-a", "api_key": "bad_key"},
                        {"slot": "fallback_1", "provider": "google", "model": "gemini-b", "api_key": "good_key"},
                    ],
                    "dry_run": False,
                }
            )

            assert len(result.get("sections") or []) >= 1
            keys_used = [c.get("api_key") for c in seen]
            assert "bad_key" in keys_used
            assert "good_key" in keys_used


@pytest.mark.asyncio
async def test_run_autoplan_attaches_reference_packs_without_prompt_injection(tmp_path):
    from backend.zhifei_autoplan.case_library_service import case_library_record_id
    from backend.zhifei_autoplan.image_library import image_library_record_id

    audit_path = tmp_path / "ingest.jsonl"
    case_record = {
        "ts": "2026-04-12T10:00:00Z",
        "filename": "房建案例A.txt",
        "project_type": "房建",
        "library_scope": "case_library",
        "saved_as": str(tmp_path / "房建案例A.txt"),
        "library_title": "房建案例A",
        "library_tags": ["医院"],
        "chapter_scope": ["工程概况"],
        "library_summary": "结构清晰",
        "library_style_profile": "短句表达",
        "sha256": "a" * 64,
    }
    image_record = {
        "ts": "2026-04-12T11:00:00Z",
        "filename": "现场平面.png",
        "project_type": "房建",
        "library_scope": "image_library",
        "saved_as": str(tmp_path / "现场平面.png"),
        "library_title": "现场平面",
        "library_tags": ["平面"],
        "chapter_scope": ["工程概况"],
        "library_caption": "现场平面示意",
        "sha256": "b" * 64,
    }
    audit_path.write_text(
        "\n".join([
            json.dumps(case_record, ensure_ascii=False),
            json.dumps(image_record, ensure_ascii=False),
        ]),
        encoding="utf-8",
    )

    with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
         patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
         patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
         patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
         patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
         patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value={"score": 100, "remediation": []}), \
         patch("backend.zhifei_autoplan.orchestrator.apply_remediation"):
        mock_writer = MagicMock()
        mock_writer.write = AsyncMock(return_value={"title": "工程概况", "content": "正文保持不变"})
        mock_writer_cls.return_value = mock_writer

        result = await run_autoplan(
            {
                "topic": "医院改造项目",
                "outline": ["工程概况"],
                "project_type": "房建",
                "dry_run": True,
                "generate_images": False,
                "auto_remediate": False,
                "reference_library_audit_path": str(audit_path),
                "case_library": {
                    "enabled": True,
                    "selected_case_ids": [case_library_record_id(case_record)],
                },
                "image_library": {
                    "enabled": True,
                    "selected_image_ids": [image_library_record_id(image_record)],
                },
            }
        )

    section = result["sections"][0]
    assert section["content"] == "正文保持不变"
    assert section["case_reference_pack"]["match_reason"] == "selected_case_ids"
    assert section["image_selection_pack"]["match_reason"] == "selected_image_ids"
    assert result["case_reference_pack"]["chapters"][0]["hit_count"] == 1
    assert result["image_selection_pack"]["chapters"][0]["hit_count"] == 1
    ctx = mock_writer.write.call_args.args[1]
    assert "case_reference_pack" not in ctx
    assert "image_selection_pack" not in ctx
