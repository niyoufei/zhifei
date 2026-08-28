"""Unit tests for backend/zhifei_autoplan/agents/section_writer.py"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.zhifei_autoplan.agents.section_writer import SectionWriter
from backend.zhifei_autoplan.requirement_evidence_matrix import (
    validate_chapter_requirement_evidence,
)


@pytest.mark.asyncio
async def test_token_limited_chapter_gets_one_evidence_aware_continuation():
    llm = MagicMock()
    llm.provider = "anthropic"
    llm.complete = AsyncMock(
        side_effect=[
            {
                "text": "第一段正文达到上限",
                "provider": "anthropic",
                "model": "draft",
                "stop_reason": "max_tokens",
            },
            {
                "text": (
                    "【要求:REQ-505-A】续写闭合"
                    "【证据:招标文件.pdf#p2_deadbeef@120】"
                ),
                "provider": "anthropic",
                "model": "draft",
                "stop_reason": "end_turn",
            },
        ]
    )
    writer = SectionWriter(llm=llm)

    evidence_row = {
        "requirement_id": "REQ-505-A",
        "requirement": "必须落实工期控制",
        "target_chapters": ["工期与质量"],
        "mandatory": True,
        "evidence_required": True,
        "responsibility": [],
        "source_evidence": [
            {"traceable_locator": "招标文件.pdf#p2_deadbeef@120"}
        ],
    }

    result = await writer.write(
        "工期与质量",
        {
            "requirements": [
                (
                    "【要求绑定:REQ-505-A】必须落实工期控制；落实段落必须保留"
                    "【要求:REQ-505-A】标记，并引用"
                    "【证据:招标文件.pdf#p2_deadbeef@120】。"
                )
            ],
            "requirement_evidence_rows": [evidence_row],
            "max_chapter_output_tokens": 8192,
        },
    )

    assert result["error"] is None
    assert result["continuation_count"] == 1
    assert "第一段正文" in result["content"]
    assert "【要求:REQ-505-A】" in result["content"]
    continuation_prompt = llm.complete.await_args_list[1].args[0]
    assert "只续写" in continuation_prompt
    assert "REQ-505-A" in continuation_prompt
    gate = validate_chapter_requirement_evidence(
        plan={"rows": [evidence_row]},
        title="工期与质量",
        section={"content": result["content"]},
    )
    assert gate["ok"] is True


def test_continuation_prompt_does_not_drop_requirement_after_twentieth_row():
    rows = []
    for index in range(1, 22):
        requirement_id = f"REQ-{index:02d}"
        rows.append(
            {
                "requirement_id": requirement_id,
                "requirement": f"落实第{index}项控制要求",
                "target_chapters": ["综合管理"],
                "mandatory": True,
                "evidence_required": True,
                "responsibility": [],
                "source_evidence": [
                    {
                        "traceable_locator": (
                            f"招标文件.pdf#p1_{index:06x}@{index}"
                        )
                    }
                ],
            }
        )

    prompt = SectionWriter()._build_continuation_prompt(
        "综合管理",
        {"requirement_evidence_rows": rows},
        partial_text="尚未落实任何强制要求",
    )

    assert "【要求绑定:REQ-01】" in prompt
    assert "【要求绑定:REQ-21】" in prompt


@pytest.mark.asyncio
async def test_continuation_repeats_marker_when_token_stop_splits_evidence_pair():
    llm = MagicMock()
    llm.provider = "anthropic"
    llm.complete = AsyncMock(
        side_effect=[
            {"text": "工期闭环【要求:REQ-A】", "stop_reason": "max_tokens"},
            {
                "text": "工期闭环【要求:REQ-A】【证据:招标文件.pdf#p3_cafebabe@88】",
                "stop_reason": "end_turn",
            },
        ]
    )
    row = {
        "requirement_id": "REQ-A",
        "requirement": "落实工期闭环",
        "target_chapters": ["进度管理"],
        "mandatory": True,
        "evidence_required": True,
        "responsibility": [],
        "source_evidence": [
            {"traceable_locator": "招标文件.pdf#p3_cafebabe@88"}
        ],
    }

    result = await SectionWriter(llm=llm).write(
        "进度管理", {"requirement_evidence_rows": [row]}
    )

    continuation_prompt = llm.complete.await_args_list[1].args[0]
    assert "【要求绑定:REQ-A】" in continuation_prompt
    gate = validate_chapter_requirement_evidence(
        plan={"rows": [row]},
        title="进度管理",
        section={"content": result["content"]},
    )
    assert gate["ok"] is True


@pytest.mark.asyncio
async def test_second_token_stop_fails_closed_as_output_truncated():
    llm = MagicMock()
    llm.provider = "anthropic"
    llm.complete = AsyncMock(
        side_effect=[
            {"text": "第一段", "stop_reason": "max_tokens"},
            {"text": "第二段", "stop_reason": "max_tokens"},
        ]
    )
    writer = SectionWriter(llm=llm)

    result = await writer.write("长章节", {})

    assert result["error"] == "output_truncated"
    assert result["continuation_count"] == 1


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

    def test_global_instruction_is_a_compliance_floor_not_a_tender_override(self):
        writer = SectionWriter()
        context = {"global_instruction": "仅引用现行有效且可追溯的规范。"}

        prompt = writer._build_prompt("工程概况", context)

        assert "【系统级合规底线】" in prompt
        assert "仅引用现行有效且可追溯的规范。" in prompt
        assert "不得覆盖招标文件、澄清答疑" in prompt
        assert "发生冲突时必须标记并停止自行裁决" in prompt

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
        assert "不得输出字典/JSON" in prompt

    def test_build_prompt_includes_actionable_auxiliary_agent_roles(self):
        writer = SectionWriter()
        prompt = writer._build_prompt(
            "道路施工方案",
            {
                "master_agent": "主控Agent",
                "compliance_agent": "合规Agent",
                "auxiliary_agents": [
                    {"name": "证据溯源Agent", "directive": "关键结论绑定证据。"},
                    {"name": "图纸接口Agent", "directive": "核对预留预埋和交叉作业。"},
                ],
            },
        )
        assert "专项复核职责" in prompt
        assert "证据溯源Agent：关键结论绑定证据" in prompt
        assert "图纸接口Agent：核对预留预埋和交叉作业" in prompt


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
        assert "【量化指标】" in result
        assert "频次" in result
        assert "阈值" in result
        assert "间距" in result
        assert "【风险→控制→验证】" in result
        assert "风险：" in result and "控制：" in result and "验证：" in result
        assert "【证据:" in result

    def test_fallback_does_not_inject_unverified_legacy_defaults(self):
        writer = SectionWriter()
        result = writer._fallback(
            "施工方案",
            {
                "params": {
                    "quant_defaults": {
                        "频次": "2次/日",
                        "阈值": "偏差≤5mm",
                        "时长": "4h/作业段",
                        "人数": "8人/班",
                        "设备型号": "20t挖机1台",
                    }
                }
            },
        )

        for legacy in ("2次/日", "偏差≤5mm", "4h/作业段", "8人/班", "20t挖机"):
            assert legacy not in result
        assert "待依据图纸/规范/批准制度确认" in result

    def test_fallback_uses_source_bound_accepted_values_not_legacy_defaults(self):
        writer = SectionWriter()
        ledger = {
            "facts": {
                "risk_inspection_frequency": {
                    "value": "3次/班",
                    "status": "approved",
                    "evidence": {"locator": "确认单.pdf#p2_deadbeef@20"},
                },
                "quality_threshold": {
                    "value": "偏差≤3mm",
                    "status": "verified",
                    "evidence": {"locator": "结构图.pdf#p8_cafebabe@80"},
                },
                "deviation_action_deadline": {
                    "value": "6小时",
                    "status": "approved",
                    "evidence": {"locator": "制度.pdf#p3_feedface@30"},
                },
                "resource_peak": {
                    "value": 72,
                    "unit": "人",
                    "status": "derived",
                    "evidence": {"locator": "资源计划.xlsx#p1_aabbccdd@1"},
                },
            }
        }

        result = writer._fallback("施工方案", {"project_fact_ledger": ledger})

        assert "频次：3次/班" in result
        assert "阈值：偏差≤3mm" in result
        assert "时长：待依据图纸/规范/批准制度确认" in result
        assert "整改时限=6小时" in result
        assert "时长：6小时" not in result
        assert "人数：72人" in result
        assert "2次/日" not in result
        assert "偏差≤5mm" not in result
        assert "4h/作业段" not in result
        assert "8人/班" not in result
        assert "20t挖机" not in result

    def test_process_bound_quality_bundle_is_rendered_per_process_not_as_dict(self):
        writer = SectionWriter()
        locator = f"围墙图.pdf#p1_{'a' * 64}@42"
        ledger = {
            "facts": {
                "quality_threshold": {
                    "value": {
                        "mode": "process_bound",
                        "items": [
                            {
                                "id": "wall-foundation-compaction",
                                "process": "围墙基础持力层压实",
                                "metric": "压实系数",
                                "operator": ">=",
                                "value": 0.97,
                                "unit": "",
                                "status": "verified",
                                "source": "reviewed_design",
                                "locator": locator,
                            }
                        ],
                    },
                    "status": "derived",
                    "evidence": {"locator": "project_parameter_evidence.quality_threshold"},
                }
            }
        }

        quality_prompt = writer._build_prompt(
            "质量管理与验收", {"project_fact_ledger": ledger}
        )
        unrelated_prompt = writer._build_prompt(
            "施工进度计划", {"project_fact_ledger": ledger}
        )
        fallback = writer._fallback(
            "质量管理与验收", {"project_fact_ledger": ledger}
        )

        expected = f"围墙基础持力层压实：压实系数>=0.97【证据:{locator}】"
        assert expected in quality_prompt
        assert expected in fallback
        assert "围墙基础持力层压实" not in unrelated_prompt
        assert "{'mode':" not in quality_prompt
        assert '"mode":"process_bound"' not in unrelated_prompt

    def test_fallback_preserves_an_approved_value_equal_to_old_default(self):
        writer = SectionWriter()
        ledger = {
            "facts": {
                "risk_inspection_frequency": {
                    "value": "2次/日",
                    "status": "approved",
                    "evidence": {"locator": "确认单.pdf#p2_deadbeef@20"},
                }
            }
        }

        result = writer._fallback("安全管理", {"project_fact_ledger": ledger})

        assert "频次：2次/日" in result

    def test_fallback_neutralizes_unapproved_constraints_from_its_own_templates(self):
        writer = SectionWriter()

        matrix_content = writer._fallback(
            "质量安全环保管理", {"logic_template": {"id": "C"}}
        )
        redline_content = writer._fallback(
            "安全管理", {"logic_template": {"id": "D"}}
        )

        for unapproved in ("1次/周", "2次/日", "48h", "≤55dB"):
            assert unapproved not in matrix_content
        for unapproved in ("10min", "2h", "24h"):
            assert unapproved not in redline_content
        assert "频次待依据项目事实台账/批准制度确认" in matrix_content
        assert "阈值待依据项目事实台账/图纸规范确认" in matrix_content
        assert "时限待依据项目事实台账/批准制度确认" in redline_content

    def test_fallback_preserves_only_exact_source_bound_constraint_values(self):
        writer = SectionWriter()
        digest = "a" * 64
        ledger = {
            "facts": {
                "risk_inspection_frequency": {
                    "value": "1次/周",
                    "status": "approved",
                    "evidence": {"locator": f"风险制度.pdf#p2_{digest}@20"},
                },
                "deviation_action_deadline": {
                    "value": "24h",
                    "status": "approved",
                    "evidence": {"locator": f"整改制度.pdf#p3_{digest}@30"},
                },
                "quality_threshold": {
                    "value": {
                        "mode": "process_bound",
                        "items": [
                            {
                                "id": "night-noise-limit",
                                "process": "夜间施工噪声控制",
                                "metric": "噪声限值",
                                "operator": "≤",
                                "value": 55,
                                "unit": "dB",
                                "status": "verified",
                                "source": "reviewed_design",
                                "locator": f"环保图.pdf#p4_{digest}@40",
                            }
                        ],
                    },
                    "status": "derived",
                    "evidence": {
                        "locator": "project_parameter_evidence.quality_threshold"
                    },
                },
            }
        }

        content = writer._fallback(
            "质量安全环保管理",
            {"logic_template": {"id": "C"}, "project_fact_ledger": ledger},
        )

        assert "频次：1次/周" in content
        assert "整改时限=24h" in content
        assert (
            "夜间施工噪声控制：噪声限值≤55dB"
            f"【证据:环保图.pdf#p4_{digest}@40】"
        ) in content
        for unapproved in ("2次/日", "48h", "10min"):
            assert unapproved not in content

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
        assert "prompt" not in result
        assert len(result["prompt_digest"]) == 64
        assert result["prompt_char_count"] > 0
        assert result["prompt_layout_version"] == "section-envelope-v3"
        assert "【量化指标】" in result["content"]
        assert "【风险→控制→验证】" in result["content"]
        assert "【证据:" in result["content"]
        assert result["generation_mode"] == "fallback"

    @pytest.mark.asyncio
    async def test_write_without_llm_keeps_prompt_ephemeral(self):
        """Prompt content is used to derive metadata but never returned or persisted."""
        writer = SectionWriter(llm=None)
        context = {"requirements": ["要求1"]}
        prompt = writer._build_prompt("施工方案", context)
        result = await writer.write("施工方案", context)
        assert "要求1" in prompt
        assert "施工方案" in prompt
        assert "prompt" not in result
        assert result["prompt_char_count"] == len(prompt)

    @pytest.mark.asyncio
    async def test_write_with_successful_llm_response(self):
        """Test write with successful LLM response."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "生成的章节内容...",
            "provider": "openai",
            "model": "gpt-4",
        }
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("工程概况", {})
        assert result["title"] == "工程概况"
        assert result["content"] == "生成的章节内容..."
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4"
        assert result["generation_mode"] == "llm"
        mock_llm.complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_llm_output_neutralizes_unaccepted_legacy_defaults(self):
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": (
                "总工期120天，资源峰值80人，关键线路间隔3天；"
                "巡检2次/日，偏差≤5mm，处置≤4h；"
                "每班8人/班，配置20t挖机1台。"
            ),
            "provider": "openai",
            "model": "test-model",
        }

        result = await SectionWriter(llm=mock_llm).write("施工部署", {})

        content = result["content"]
        for legacy in (
            "总工期120天",
            "资源峰值80人",
            "关键线路间隔3天",
            "2次/日",
            "偏差≤5mm",
            "≤4h",
            "8人/班",
            "20t挖机",
        ):
            assert legacy not in content
        assert "待依据" in content
        assert result["generation_mode"] == "llm"

    @pytest.mark.asyncio
    async def test_llm_output_neutralizes_unlisted_numeric_constraints_systemically(self):
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": (
                "风险检查频次1次/周；一般风险24h关闭；"
                "夜间噪声≤55dB。"
                f"【证据:环保制度.pdf#p1_{'b' * 64}@12】"
            ),
            "provider": "openai",
            "model": "test-model",
        }

        result = await SectionWriter(llm=mock_llm).write("安全环保管理", {})

        content = result["content"]
        for unapproved in ("1次/周", "24h", "≤55dB"):
            assert unapproved not in content
        assert "频次待依据项目事实台账/批准制度确认" in content
        assert "时限待依据项目事实台账/批准制度确认" in content
        assert "阈值待依据项目事实台账/图纸规范确认" in content
        assert f"【证据:环保制度.pdf#p1_{'b' * 64}@12】" in content

    @pytest.mark.asyncio
    async def test_similar_approved_values_do_not_authorize_different_constraints(self):
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {
            "text": "检查1次/周；一般风险24h关闭；夜间噪声≤55dB。",
            "provider": "openai",
            "model": "test-model",
        }
        digest = "c" * 64
        ledger = {
            "facts": {
                "risk_inspection_frequency": {
                    "value": "1次/班",
                    "status": "approved",
                    "evidence": {"locator": f"风险制度.pdf#p1_{digest}@10"},
                },
                "deviation_action_deadline": {
                    "value": "6h",
                    "status": "approved",
                    "evidence": {"locator": f"整改制度.pdf#p2_{digest}@20"},
                },
                "quality_threshold": {
                    "value": "≤50dB",
                    "status": "verified",
                    "evidence": {"locator": f"环保图.pdf#p3_{digest}@30"},
                },
            }
        }

        result = await SectionWriter(llm=mock_llm).write(
            "安全环保管理", {"project_fact_ledger": ledger}
        )

        for unapproved in ("1次/周", "24h", "≤55dB"):
            assert unapproved not in result["content"]

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
        # Fallback keeps deterministic prose but never dumps raw evidence arrays.
        assert "【量化指标】" in result["content"]
        assert "【证据摘要】" not in result["content"]
        assert "证据A" not in result["content"]
        assert "【证据:文档C】" in result["content"]
        assert result["generation_mode"] == "fallback"

    @pytest.mark.asyncio
    async def test_write_with_whitespace_only_uses_fallback(self):
        """Test write falls back when LLM returns whitespace only."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {"text": "   \n\t  "}
        writer = SectionWriter(llm=mock_llm)
        result = await writer.write("质量管理", {})
        assert "【量化指标】" in result["content"]
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
        assert "【量化指标】" in result["content"]
        assert "【证据摘要】" not in result["content"]
        assert result["error"] == "API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_write_failure_does_not_dump_raw_evidence_context(self):
        """Provider failure must not copy raw evidence arrays into prose."""
        mock_llm = AsyncMock()
        mock_llm.complete.return_value = {"text": ""}
        writer = SectionWriter(llm=mock_llm)
        context = {
            "kg_evidence": ["kg1", "kg2", "kg3", "kg4", "kg5"],
            "doc_evidence": ["doc1", "doc2", "doc3", "doc4", "doc5"],
        }
        result = await writer.write("进度计划", context)
        content = result["content"]
        assert "【证据摘要】" not in content
        assert not any(token in content for token in ("kg1", "kg2", "kg3", "kg4", "doc2", "doc3", "doc4"))
        assert "【证据:doc1】" in content

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
        assert "prompt" not in result
        assert len(result["prompt_digest"]) == 64
        assert result["prompt_char_count"] > 0
        assert set(result["prompt_segment_chars"]) == {"stable", "shared", "dynamic"}
        assert result["prompt_layout_version"] == "section-envelope-v3"
        assert "provider" in result
        assert "model" in result
        assert "error" in result
        assert result["generation_mode"] == "llm"


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
        assert result["generation_mode"] == "fallback"

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
        assert "<script>" in writer._build_prompt("特殊章节", context)
        assert "prompt" not in result

    def test_fallback_different_titles(self):
        """Test fallback generates different content for different titles."""
        writer = SectionWriter()
        r1 = writer._fallback("章节A", {})
        r2 = writer._fallback("章节B", {})
        assert r1 != r2
        assert "章节A" in r1
        assert "章节B" in r2
