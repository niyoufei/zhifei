from __future__ import annotations

from backend.zhifei_autoplan.agents.section_writer import SectionWriter
from backend.zhifei_autoplan.quality_check import (
    _check_qse_closed_loop_by_section,
    _check_required_topics,
    _check_required_topics_detail,
)


def test_qse_fallback_meets_closed_loop_gate() -> None:
    writer = SectionWriter(llm=None)
    content = writer._fallback(
        "确保工程质量的技术组织措施",
        {
            "agent_role": "质量负责人",
            "project_type": "房建工程",
            "global_instruction": "规则生成优先",
            "logic_template": {"id": "A"},
            "doc_evidence": ["招标文件#p1_ab12cd34@128: 质量要求"],
            "boq_focus": {},
            "standard_trades": ["测量工", "钢筋工", "模板工", "混凝土工", "电工", "焊工"],
            "params": {},
        },
    )

    result = _check_qse_closed_loop_by_section(
        [
            {
                "title": "确保工程质量的技术组织措施",
                "content": content,
            }
        ]
    )

    assert result["ok"] is True
    assert result["by_section"][0]["closed_card_count"] >= result["by_section"][0]["target_cards"]


def test_safety_qse_fallback_scales_to_six_closed_loop_cards() -> None:
    writer = SectionWriter(llm=None)
    content = writer._fallback(
        "确保安全生产的技术组织措施",
        {
            "agent_role": "安全负责人",
            "project_type": "房建工程",
            "global_instruction": "规则生成优先",
            "logic_template": {"id": "A"},
            "doc_evidence": ["招标文件.pdf#p1_ab12cd34@128: 安全要求"],
            "boq_focus": {},
            "standard_trades": ["测量工", "钢筋工", "模板工", "混凝土工", "电工", "焊工"],
            "params": {},
        },
    )

    result = _check_qse_closed_loop_by_section(
        [
            {
                "title": "确保安全生产的技术组织措施",
                "content": content,
            }
        ]
    )

    assert result["ok"] is True
    assert result["by_section"][0]["closed_card_count"] >= result["by_section"][0]["target_cards"]


def test_general_fallback_includes_technical_trades_topic_details() -> None:
    writer = SectionWriter(llm=None)
    content = writer._fallback(
        "施工部署",
        {
            "agent_role": "技术负责人",
            "project_type": "房建工程",
            "global_instruction": "规则生成优先",
            "logic_template": {"id": "A"},
            "doc_evidence": ["招标文件.pdf#p1_ab12cd34@128: 施工部署要求"],
            "boq_focus": {},
            "standard_trades": ["测量工", "钢筋工", "模板工", "混凝土工", "电工", "焊工"],
            "params": {},
        },
    )

    required = _check_required_topics(content)
    detail = _check_required_topics_detail([{"title": "施工部署", "content": content}])
    trade_row = next(row for row in detail["by_topic"] if row["topic"] == "技术工种配置")

    assert required["covered"]["技术工种配置"]
    assert trade_row["ok"] is True
    assert "技术工种配置" in content


def test_deployment_fallback_mentions_progress_nodes_and_penalty_controls() -> None:
    writer = SectionWriter(llm=None)
    content = writer._fallback(
        "施工部署",
        {
            "agent_role": "技术负责人",
            "project_type": "装修工程",
            "global_instruction": "规则生成优先",
            "logic_template": {"id": "D"},
            "doc_evidence": ["招标文件.pdf#p1_ab12cd34@128: 施工部署要求"],
            "boq_focus": {},
            "standard_trades": ["测量工", "钢筋工", "模板工", "混凝土工", "电工", "焊工"],
            "params": {},
        },
    )

    assert "工期" in content
    assert "节点" in content
    assert "重难点" in content
    assert "扣分项" in content
    assert "重大偏差" in content
    assert "否决项" in content


def test_qse_e_fallback_includes_behavior_and_redyellow_anchors() -> None:
    writer = SectionWriter(llm=None)
    content = writer._fallback(
        "确保安全生产的技术组织措施",
        {
            "agent_role": "安全负责人",
            "project_type": "装修工程",
            "global_instruction": "规则生成优先",
            "logic_template": {"id": "E"},
            "doc_evidence": ["招标文件.pdf#p1_ab12cd34@128: 安全要求"],
            "boq_focus": {},
            "standard_trades": ["测量工", "钢筋工", "模板工", "混凝土工", "电工", "焊工"],
            "params": {},
        },
    )

    assert "区域网格" in content
    assert "班组行为清单" in content
    assert "红黄牌处置" in content
    assert "重难点" in content
    assert "扣分项" in content
    assert "重大偏差" in content
    assert "否决项" in content
