from __future__ import annotations

from backend.zhifei_autoplan.agents.outline_guard_agent import OutlineGuardAgent


def test_outline_guard_truncates_scoring_tail_after_valid_outline():
    agent = OutlineGuardAgent()
    raw_items = [
        "工程概况",
        "主要施工方法",
        "拟投入的主要物资计划",
        "拟投入的主要施工机械、设备计划",
        "劳动力安排计划",
        "确保工程质量的技术组织措施",
        "确保安全生产的技术组织措施",
        "确保工期的技术组织措施",
        "确保文明施工的技术组织措施",
        "施工总平面布置图",
        "重点、难点",
        "确保危险性较大工程施工的管理体系与措施（如有）",
        "本项评委打分为一般或优秀的，评委要提出充足的理由，并在评标报告中书面记录。",
        "本项满分5分",
        "对于",
        "投标人业绩（如有）",
        "项目经理业绩（如有）",
    ]
    result = agent.sanitize_review_outline(raw_items)
    assert len(result) == 12
    assert result[-1] == "确保危险性较大工程施工的管理体系与措施（如有）"
    assert not any("评委打分" in x for x in result)
    assert not any("投标人业绩" in x for x in result)
