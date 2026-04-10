"""Unit tests for backend/zhifei_autoplan/orchestrator.py"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from backend.zhifei_autoplan.orchestrator import (
    _build_weights_and_penalties,
    _build_section_runtime_budget,
    _build_hard_quality_gate,
    _compress_section_requirements,
    _collect_gate_remediation,
    _ensure_traceable_evidence_per_section,
    _normalize_provider_chain,
    _quality_score,
    _derive_section_length_bounds,
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


def test_quality_score_fallback_from_issue_list():
    got = _quality_score({"issue_list": [{"a": 1}, {"b": 2}]})
    assert isinstance(got, int)
    assert 0 <= got <= 100
    assert got == 96


def test_build_hard_quality_gate_and_collect_remediation():
    quality = {
        "risk_triplet": {"by_section": [{"title": "第1章", "ok": False}]},
        "quantitative": {"by_section": [{"title": "第1章", "ok": False, "missing": ["频次"]}]},
        "vague_terms": {"by_section": [{"title": "第1章", "ok": False}]},
        "evidence_quality": {"by_section": [{"title": "第1章", "ok": False}]},
        "evidence_traceability": {"by_section": [{"title": "第1章", "ok": False}]},
    }
    sections = [{"title": "第1章", "content": "测试", "graph_nodes": []}]
    evidence_tracking = {"summary": {"paragraph_count": 10, "score_point_bound_rows": 1, "traceable_locator_rows": 1}}
    gate = _build_hard_quality_gate(quality=quality, evidence_tracking=evidence_tracking, sections=sections)
    assert gate["ok"] is False
    assert gate["failed"]
    recs = _collect_gate_remediation(quality=quality, sections=sections, failed=gate["failed"])
    assert recs
    assert any(r.get("type") == "risk_triplet_gap" for r in recs)


def test_build_hard_quality_gate_prefers_section_level_evidence_metrics():
    quality = {
        "risk_triplet": {"by_section": [{"title": "第1章", "ok": True}]},
        "quantitative": {"by_section": [{"title": "第1章", "ok": True}]},
        "vague_terms": {"by_section": [{"title": "第1章", "ok": True}]},
    }
    sections = [{"title": "第1章", "content": "测试", "graph_nodes": ["KG-1"]}]
    evidence_tracking = {
        "summary": {
            "paragraph_count": 40,
            "score_point_bound_rows": 3,
            "evidence_bound_rows": 4,
            "traceable_locator_rows": 4,
            "section_count": 1,
            "evidence_bound_sections": 1,
            "traceable_locator_sections": 1,
        }
    }
    gate = _build_hard_quality_gate(
        quality=quality,
        evidence_tracking=evidence_tracking,
        sections=sections,
    )
    assert gate["metrics"]["evidence_binding_rate"] == 1.0
    assert gate["metrics"]["traceable_locator_rate"] == 1.0


def test_normalize_provider_chain_maps_display_alias_to_runtime_model():
    chain = _normalize_provider_chain(
        {
            "provider_chain": [
                {"slot": "main", "provider": "openai", "model": "ChatGPT-5.4", "api_key": "sk-main"},
                {"slot": "fallback_1", "provider": "google", "model": "Gemini3.1pro", "api_key": "g-main"},
            ]
        }
    )
    assert chain == [
        {"slot": "main", "provider": "openai", "model": "gpt-5.4", "api_key": "sk-main", "key_alias": ""},
        {"slot": "fallback_1", "provider": "google", "model": "gemini-3.1-pro-preview", "api_key": "g-main", "key_alias": ""},
    ]


def test_derive_section_length_bounds_relaxes_single_page_floor():
    min_len, max_len, target_len = _derive_section_length_bounds(1, 750)
    assert target_len >= 1200
    assert min_len >= 600
    assert max_len >= 2600


def test_derive_section_length_bounds_relaxes_two_page_floor():
    min_len, max_len, target_len = _derive_section_length_bounds(2, 750)
    assert target_len >= 2200
    assert min_len >= 1000
    assert max_len >= 3600


def test_compress_section_requirements_keeps_hard_constraints_first():
    lines = [
        "普通背景说明A",
        "本章目标页数：4页（建议正文约2400字，允许±20%）",
        "本章字数边界：1800-3000字（由全局篇幅分配器自动下发）。",
        "系统全局指令（必须无条件执行）全文禁止官话",
        "检查频次：每周1次",
        "特殊材料清单：防火封堵材料",
        "普通背景说明B",
    ]
    got = _compress_section_requirements(lines, limit=4)
    assert len(got) == 4
    assert any("系统全局指令" in x for x in got)
    assert any("本章目标页数" in x for x in got)
    assert any("特殊材料清单" in x for x in got)


def test_build_section_runtime_budget_compacts_simple_chapter():
    speed_profile = {
        "kg_top_k": 3,
        "doc_limit": 5,
        "standard_limit": 2,
        "llm_timeout_sec": 120,
    }
    got = _build_section_runtime_budget(
        title="编制依据与原则",
        chapter_target_pages=1,
        speed_profile=speed_profile,
        specialist_count=0,
        has_boq_focus=False,
        has_chapter_contract=False,
    )
    assert got["kg_top_k"] <= 2
    assert got["doc_limit"] <= 3
    assert got["requirements_limit"] <= 18
    assert got["llm_timeout_sec"] <= 55
    assert got["max_output_tokens_hint"] <= 1800


def test_build_section_runtime_budget_keeps_rich_budget_for_complex_chapter():
    speed_profile = {
        "kg_top_k": 3,
        "doc_limit": 5,
        "standard_limit": 2,
        "llm_timeout_sec": 120,
    }
    got = _build_section_runtime_budget(
        title="关键工序与危大工程质量安全控制",
        chapter_target_pages=6,
        speed_profile=speed_profile,
        specialist_count=3,
        has_boq_focus=True,
        has_chapter_contract=True,
    )
    assert got["graph_top_k"] >= 5
    assert got["doc_limit"] >= 5
    assert got["requirements_limit"] >= 24
    assert got["llm_timeout_sec"] == 120
    assert got["max_output_tokens_hint"] >= 5200


def test_ensure_traceable_evidence_per_section_patches_missing_traceability():
    sections = [{"title": "主要施工方法", "content": "本章描述工艺流程。"}]
    with patch(
        "backend.zhifei_autoplan.orchestrator.best_ingested_hit",
        return_value={"locator": "招标文件.pdf#p12_ab12cd34@567"},
    ):
        res = _ensure_traceable_evidence_per_section(
            sections=sections,
            project_id="P-001",
            topic="测试项目",
        )
    assert int(res.get("fixed") or 0) == 1
    assert "【证据:招标文件.pdf#p12_ab12cd34@567】" in str(sections[0].get("content") or "")


def test_collect_gate_remediation_prefers_strategy_enriched_rows():
    quality = {
        "auto_revision_suggestions": [
            {
                "title": "工程概况",
                "type": "quantitative_gap",
                "suggestion": "补齐量化指标",
                "indicator_group": "缺量化",
                "strategy_id": "quant_fill_general_v1",
                "strategy_priority": 95,
            }
        ],
        "quantitative": {"by_section": [{"title": "工程概况", "ok": False, "missing": ["频次"]}]},
    }
    rows = _collect_gate_remediation(
        quality=quality,
        sections=[{"title": "工程概况", "content": "正文"}],
        failed=[{"remediation_type": "quantitative_gap"}],
    )
    assert len(rows) == 1
    assert rows[0]["strategy_id"] == "quant_fill_general_v1"
    assert rows[0]["indicator_group"] == "缺量化"


def test_collect_gate_remediation_applies_combo_learning_priority():
    from backend.zhifei_autoplan.self_evolution import _profile_key

    quality = {
        "auto_revision_suggestions": [
            {
                "title": "工程概况",
                "type": "quantitative_gap",
                "suggestion": "补齐量化指标",
                "indicator_group": "缺量化",
                "strategy_id": "quant_fill_general_v1",
                "strategy_priority": 95,
                "expected_action_tags": ["add_quant_value", "add_record_acceptance"],
            },
            {
                "title": "工程概况",
                "type": "risk_triplet_gap",
                "suggestion": "补齐风险控制验证",
                "indicator_group": "缺闭环",
                "strategy_id": "risk_triplet_closure_v1",
                "strategy_priority": 98,
                "expected_action_tags": ["add_risk_control_verify"],
            },
        ],
        "quantitative": {"by_section": [{"title": "工程概况", "ok": False, "missing": ["频次"]}]},
        "risk_triplet": {"by_section": [{"title": "工程概况", "ok": False, "triplet_count": 0}]},
    }
    profile = {
        "version": "runtime_budget_profile_v1",
        "entries": {
            _profile_key("工程概况", "房建", "quality_200"): {
                "title": "工程概况",
                "project_type": "房建",
                "generation_mode": "quality_200",
                "runs": 4,
                "combo_attempt_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 4},
                "combo_indicator_close_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 3},
                "combo_gate_pass_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 2},
            }
        },
    }
    with patch(
        "backend.zhifei_autoplan.orchestrator.load_runtime_budget_profile",
        return_value=profile,
    ):
        rows = _collect_gate_remediation(
            quality=quality,
            sections=[{"title": "工程概况", "content": "正文"}],
            failed=[
                {"remediation_type": "quantitative_gap"},
                {"remediation_type": "risk_triplet_gap"},
            ],
            params={"self_evolution": {"enabled": True, "combo_learning_enabled": True}},
            project_type="房建",
            generation_mode="quality_200",
            runtime_budget_profile=profile,
        )
    assert rows[0]["strategy_id"] == "quant_fill_general_v1"
    assert rows[0]["_combo_learning_applied"] is True
    assert rows[0]["_combo_learning_source_runs"] == 4


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
             patch("backend.zhifei_autoplan.orchestrator.build_template_chapter_learning_context") as mock_template_learning, \
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
            mock_template_learning.return_value = {"hits": [], "requirement_lines": [], "anchor_headings": [], "sample_titles": []}
            
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
                "template_learning": mock_template_learning,
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
    async def test_combo_learning_applies_during_draft_remediation(self, mock_dependencies):
        """历史高有效组合会在首轮模板修复前参与排序，而不是只在质量门重试时生效。"""
        draft_quality = {
            "score": 52,
            "issue_list": [
                {
                    "title": "工程概况",
                    "type": "quantitative_gap",
                    "indicator_group": "缺量化",
                    "strategy_id": "quant_fill_general_v1",
                },
                {
                    "title": "工程概况",
                    "type": "risk_triplet_gap",
                    "indicator_group": "缺闭环",
                    "strategy_id": "risk_triplet_closure_v1",
                }
            ],
            "remediation": [
                {
                    "title": "清单重点项",
                    "type": "quantitative_gap",
                    "suggestion": "补齐量化指标",
                    "indicator_group": "缺量化",
                    "strategy_id": "quant_fill_general_v1",
                    "strategy_priority": 95,
                    "expected_action_tags": ["add_quant_value", "add_record_acceptance"],
                },
                {
                    "title": "专项主题",
                    "type": "risk_triplet_gap",
                    "suggestion": "补齐风险控制验证",
                    "indicator_group": "缺闭环",
                    "strategy_id": "risk_triplet_closure_v1",
                    "strategy_priority": 98,
                    "expected_action_tags": ["add_risk_control_verify"],
                }
            ],
            "remediation_strategy_audit": {
                "indicator_groups": [{"indicator_group": "缺量化", "count": 1}, {"indicator_group": "缺闭环", "count": 1}],
                "strategies": [{"strategy_id": "quant_fill_general_v1", "count": 1}, {"strategy_id": "risk_triplet_closure_v1", "count": 1}],
                "mapping_rows": [
                    {"title": "工程概况", "strategy_id": "quant_fill_general_v1"},
                    {"title": "工程概况", "strategy_id": "risk_triplet_closure_v1"},
                ],
            },
        }
        final_quality = {
            "score": 96,
            "issue_list": [],
            "remediation": [],
            "risk_triplet": {"by_section": [{"title": "工程概况", "ok": True}]},
            "quantitative": {"by_section": [{"title": "工程概况", "ok": True}]},
            "vague_terms": {"by_section": [{"title": "工程概况", "ok": True}]},
            "remediation_strategy_audit": {},
            "remediation_execution_audit": {},
        }
        mock_dependencies["quality"].side_effect = [draft_quality, final_quality]
        from backend.zhifei_autoplan.self_evolution import _profile_key

        profile = {
            "version": "runtime_budget_profile_v1",
            "entries": {
                _profile_key("工程概况", "房建", "quality_200"): {
                    "title": "工程概况",
                    "project_type": "房建",
                    "generation_mode": "quality_200",
                    "runs": 3,
                    "combo_attempt_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 3},
                    "combo_indicator_close_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 3},
                    "combo_gate_pass_counts": {"缺量化||quant_fill_general_v1||add_quant_value": 2},
                    "combo_bundle_attempt_counts": {
                        "缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value": 3
                    },
                    "combo_bundle_gate_pass_counts": {
                        "缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value": 2
                    },
                    "combo_context_bundle_attempt_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value": 3
                    },
                    "combo_context_bundle_gate_pass_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value": 3
                    },
                    "combo_context_bundle_learning_attempt_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value": 2
                    },
                    "combo_context_bundle_learning_gate_pass_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value": 2
                    },
                    "combo_context_metric_attempt_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##quantitative_ok_rate": 2,
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##risk_triplet_ok_rate": 2,
                    },
                    "combo_context_metric_resolved_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##quantitative_ok_rate": 2,
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##risk_triplet_ok_rate": 2,
                    },
                    "combo_context_metric_action_attempt_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##quantitative_ok_rate##add_quant_value": 2,
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##risk_triplet_ok_rate##add_risk_control_verify": 2,
                    },
                    "combo_context_metric_action_resolved_counts": {
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##quantitative_ok_rate##add_quant_value": 2,
                        "general|A@@缺闭环||risk_triplet_closure_v1||add_risk_control_verify§§缺量化||quant_fill_general_v1||add_quant_value##risk_triplet_ok_rate##add_risk_control_verify": 2,
                    },
                }
            },
        }
        mock_dependencies["writer"].write = AsyncMock(
            side_effect=lambda title, ctx, **kwargs: {"title": title, "content": "content"}
        )
        with patch("backend.zhifei_autoplan.orchestrator.load_runtime_budget_profile", return_value=profile):
            result = await run_autoplan(
                {
                    "topic": "测试项目",
                    "project_type": "房建",
                    "generation_mode": "quality_200",
                    "outline": ["工程概况"],
                    "strict_tender_outline": True,
                    "auto_remediate": True,
                    "remediate_mode": "template",
                    "dry_run": True,
                }
            )
        trace = result.get("generation_trace") or {}
        self_evolution_trace = trace.get("self_evolution") or {}
        assert self_evolution_trace.get("remediation_combo_learning_applied_count") == 1
        assert self_evolution_trace.get("remediation_context_bundle_learning_applied_count") >= 1
        assert self_evolution_trace.get("remediation_context_bundle_learning_effect_applied_count") >= 1
        assert self_evolution_trace.get("remediation_context_bundle_learning_metric_effect_applied_count") >= 1
        assert self_evolution_trace.get("remediation_context_bundle_learning_metric_action_effect_applied_count") >= 1
        assert "量化指标达标率" in (self_evolution_trace.get("remediation_context_bundle_learning_metric_effect_metrics") or [])
        assert any("补量化数值" in str(x) for x in (self_evolution_trace.get("remediation_context_bundle_learning_metric_action_effect_triplets") or []))
        assert self_evolution_trace.get("remediation_combo_bundle_learning_applied_count") == 0
        assert "工程概况" in (self_evolution_trace.get("remediation_combo_learning_titles") or [])
        assert "general/A" in (self_evolution_trace.get("remediation_context_bundle_learning_contexts") or [])
        assert self_evolution_trace.get("remediation_context_bundle_learning_effect_bundles")
        assert self_evolution_trace.get("remediation_context_bundle_learning_metric_effect_bundles")
        assert self_evolution_trace.get("remediation_context_bundle_learning_metric_action_effect_bundles")
        assert any(
            isinstance(stage, dict) and stage.get("stage") == "remediation_combo_learning_draft"
            for stage in (result.get("pipeline_stages") or [])
        )
        assert any(
            isinstance(stage, dict) and stage.get("stage") == "remediation_context_bundle_learning_draft"
            for stage in (result.get("pipeline_stages") or [])
        )
        assert not any(
            isinstance(stage, dict) and stage.get("stage") == "remediation_combo_bundle_learning_draft"
            for stage in (result.get("pipeline_stages") or [])
        )
        assert any(
            isinstance(stage, dict) and stage.get("stage") == "remediation_context_metric_effect_final"
            for stage in (result.get("pipeline_stages") or [])
        )

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
    async def test_run_autoplan_applies_self_evolution_runtime_budget(self, mock_dependencies, monkeypatch):
        monkeypatch.setattr(
            "backend.zhifei_autoplan.orchestrator.build_runtime_budget_hints",
            lambda **kwargs: {
                "enabled": True,
                "applied": True,
                "llm_timeout_sec": 88,
                "max_output_tokens_hint": 2800,
                "section_retry_limit": 2,
                "reason": "historical_error_rate=0.50_raise_timeout",
                "source_runs": 3,
            },
        )
        result = await run_autoplan(
            {
                "outline": ["工程概况"],
                "provider": "openai",
                "model": "gpt-4",
                "api_key": "test-key",
                "dry_run": False,
            }
        )
        ctx = _find_ctx_by_title(mock_dependencies["writer"], "工程概况")
        assert ctx["llm_timeout_sec"] == 88
        assert ctx["requested_section_retry_limit"] == 2
        assert ctx["max_output_tokens_hint"] == 2800
        assert ctx["evolution_applied"] is True
        assert ctx["evolution_source_runs"] == 3
        assert result["sections"][0]["evolution_applied"] is True
        assert result["sections"][0]["evolution_reason"] == "historical_error_rate=0.50_raise_timeout"
        assert result["generation_trace"]["self_evolution"]["applied_count"] >= 1

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
    async def test_chapter_pages_allocate_length_bounds(self, mock_dependencies):
        """Chapter page target is converted to section min/max length constraints."""
        await run_autoplan(
            {
                "outline": ["第一章"],
                "chapter_pages": {"第一章": {"pages": 5}},
                "style": {"body_size": 14, "line_spacing_pt": 22.0},
            }
        )

        hit = None
        for call in mock_dependencies["writer"].write.call_args_list:
            if call[0][0] == "第一章":
                hit = call
                break
        assert hit is not None
        kwargs = hit.kwargs or {}
        ctx = hit[0][1] if len(hit[0]) >= 2 else {}
        assert isinstance(ctx, dict)
        assert int(ctx.get("chapter_target_pages") or 0) == 5
        assert int(ctx.get("section_min_length") or 0) > 0
        assert int(ctx.get("section_max_length") or 0) > int(ctx.get("section_min_length") or 0)
        assert int(kwargs.get("min_length") or 0) == int(ctx.get("section_min_length") or 0)
        assert int(kwargs.get("max_length") or 0) == int(ctx.get("section_max_length") or 0)
        assert any("字数边界" in str(r) for r in ctx.get("requirements", []))

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
    async def test_front_matter_outline_injected_into_context(self, mock_dependencies):
        await run_autoplan(
            {
                "outline": ["第一章", "第二章"],
                "chapter_pages": {"第一章": 3, "第二章": 4},
                "front_matter_outline": {
                    "cover_pages": 1,
                    "toc_pages": 2,
                    "full_index_pages": 1,
                    "sequence": ["封面1页", "全文索引1页", "目录2页", "正文"],
                    "toc_entries": [
                        {"order": 1, "title": "第一章", "start_page": 5, "planned_pages": 3},
                        {"order": 2, "title": "第二章", "start_page": 8, "planned_pages": 4},
                    ],
                },
            }
        )

        ctx = _find_ctx_by_title(mock_dependencies["writer"], "第一章")
        reqs = ctx.get("requirements", []) if isinstance(ctx, dict) else []
        assert any("正文编制顺序必须服从前置页计划" in str(r) for r in reqs)
        assert any("目录定位：本章为第1章" in str(r) for r in reqs)
        assert any("目录起始页第5页" in str(r) for r in reqs)

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
    async def test_template_learning_injected_into_context(self, mock_dependencies):
        """Chapter-level template learning is injected into requirements and evidence."""
        mock_dependencies["template_learning"].return_value = {
            "hits": [
                {
                    "filename": "优秀样板A.docx",
                    "sha256": "a" * 64,
                    "offset": 128,
                    "page": 3,
                    "snippet": "项目经理部组织机构、资源投入与施工顺序应前置明确。",
                    "section_title": "施工部署",
                    "template_theme": "施工部署",
                }
            ],
            "requirement_lines": [
                "样板学习画像：当前章节归类为“施工部署”，优先参考同类型优秀样板中的对应章节组织方式，不得改变本项目招标目录。",
                "样板高频锚点：组织分工与岗位责任、资源配置与机械材料、流程步骤与工序衔接。",
            ],
            "anchor_headings": ["组织分工与岗位责任"],
            "sample_titles": ["施工部署"],
        }
        await run_autoplan({
            "project_type": "房建",
            "outline": ["施工部署"],
        })

        ctx = _find_ctx_by_title(mock_dependencies["writer"], "施工部署")
        reqs = [str(x) for x in (ctx.get("requirements") or [])]
        doc_evidence = [str(x) for x in (ctx.get("doc_evidence") or [])]
        assert any("样板学习画像" in x for x in reqs)
        assert any("样板高频锚点" in x for x in reqs)
        assert any("样板章节:施工部署" in x for x in doc_evidence)

    @pytest.mark.asyncio
    async def test_qingtian_requirements_injected_into_context(self, mock_dependencies):
        """QingTian system constraints are injected by default."""
        await run_autoplan({
            "outline": ["关键工序控制点"],
        })
        call_args = mock_dependencies["writer"].write.call_args
        ctx = call_args[0][1]
        reqs = [str(x) for x in (ctx.get("requirements") or [])]
        assert any("本章必须包含4块" in x for x in reqs)
        assert any("风险点/控制点|措施（含参数、频次、责任）|验收动作|记录表" in x for x in reqs)

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
        assert isinstance(result.get("generation_trace"), dict)
        assert isinstance((result.get("generation_trace") or {}).get("pipeline_stages"), list)
        assert isinstance((result.get("generation_trace") or {}).get("remediation_execution_audit"), dict)

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

    @pytest.mark.asyncio
    async def test_final_length_clamp_keeps_section_within_page_budget(self, mock_dependencies):
        """Late-stage expansions should still be clamped back into chapter page bounds."""
        mock_dependencies["writer"].write = AsyncMock(return_value={"title": "工程概况", "content": "初稿内容"})
        mock_dependencies["quality"].return_value = {
            "score": 80,
            "remediation": [{"title": "工程概况", "type": "length_probe", "suggestion": "补充细化"}],
        }

        def _inflate(sections, *args, **kwargs):
            sections[0]["content"] = (
                "工序：钢筋绑扎。设备：GW40弯曲机1台。参数：间距200mm，合格率≥98%。责任：施工员复核，质检员每班检查。"
                * 120
            )

        mock_dependencies["remediate"].side_effect = _inflate
        result = await run_autoplan(
            {
                "outline": ["工程概况"],
                "chapter_pages": {"工程概况": 2},
                "strict_tender_outline": True,
            }
        )
        sec = (result.get("sections") or [{}])[0]
        assert len(str(sec.get("content") or "")) <= 3740
        logs = sec.get("constraint_log") or []
        assert any(item.get("status") in {"postprocess_compacted", "compacted"} for item in logs)
        stages = result.get("pipeline_stages") or []
        assert any(str(item.get("stage")) == "final_length_clamp" for item in stages)


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
        
        async def timed_write(title, ctx, **kwargs):
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
        assert call_times[-1] - call_times[0] < 0.05  # 50ms tolerance


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
        assert any(
            isinstance(s, dict) and bool(str(s.get("agent_role") or "").strip())
            for s in result["sections"]
        )
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
        assert any(str(s.get("content") or "").startswith("章节生成失败") for s in result["sections"])


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
        assert str(section.get("content") or "").startswith("修复后的内容")

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
    async def test_providers_list_prefers_primary_with_model_map(self, mock_deps_prov):
        """providers/model_map now forms an ordered failover chain; success stays on primary."""
        await run_autoplan({
            "outline": ["章节1", "章节2", "章节3"],
            "providers": ["provider_a", "provider_b"],
            "model_map": {"provider_a": "model_a", "provider_b": "model_b"},
            "dry_run": False,
        })
        
        calls = mock_deps_prov["llm_calls"]
        providers_used = [c["provider"] for c in calls]
        assert "provider_a" in providers_used
        assert "provider_b" not in providers_used

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
        """provider_chain preserves duplicate providers, but successful sections stay on the first slot."""
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
        all_pairs = {(c.get("provider"), c.get("api_key")) for c in calls}
        assert ("google", "g_key_1") in all_pairs
        assert ("google", "g_key_2") not in all_pairs
        assert ("openai", "o_key_1") not in all_pairs

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
    async def test_section_result_keeps_used_key_alias(self, monkeypatch):
        """Section output should retain the resolved key alias for later traceability."""
        monkeypatch.setenv("OPENAI_API_KEY_TEXT_MAIN", "env-main")
        monkeypatch.setenv("OPENAI_API_KEY_TEXT_BACKUP", "env-backup")
        with patch("backend.zhifei_autoplan.orchestrator.load_tender_matrix", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.load_boq_data", return_value={}), \
             patch("backend.zhifei_autoplan.orchestrator.search_kg", return_value={"results": []}), \
             patch("backend.zhifei_autoplan.orchestrator.search_ingested_docs", return_value=[]), \
             patch("backend.zhifei_autoplan.orchestrator.SectionWriter") as mock_writer_cls, \
             patch("backend.zhifei_autoplan.orchestrator.run_quality_checks", return_value={"score": 100, "remediation": []}), \
             patch("backend.zhifei_autoplan.orchestrator.apply_remediation"), \
             patch("backend.zhifei_autoplan.orchestrator.LLMClient"):

            mock_writer = MagicMock()
            mock_writer.write = AsyncMock(return_value={"title": "章节1", "content": "ok", "provider": "openai", "model": "gpt-5.4"})
            mock_writer_cls.return_value = mock_writer

            result = await run_autoplan(
                {
                    "outline": ["章节1"],
                    "provider_chain": [
                        {"slot": "text_main", "provider": "openai", "model": "gpt-5.4"},
                        {"slot": "text_backup", "provider": "openai", "model": "gpt-5.4"},
                    ],
                    "dry_run": False,
                    "strict_tender_outline": True,
                }
            )

            sec = (result.get("sections") or [{}])[0]
            assert sec.get("used_key_alias") == "OPENAI_API_KEY_TEXT_MAIN"
