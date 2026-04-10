from __future__ import annotations

from backend.zhifei_autoplan.agents.outline_manager_agent import OutlineManagerAgent


def test_outline_manager_override_toc_with_review_fallback():
    agent = OutlineManagerAgent()
    text = """目录
第一章 招标公告
第二章 投标人须知
第三章 评标及定标办法

2.2.1（2）技术文件评审标准
依据投标人提供的针对工程项目整体理解、拟采用的新技术、新工艺（如有）的内容进行评审。
依据投标人提供的工程重点难点及危大工程的保障体系与措施进行评审。
依据投标人提供的确保工期与质量的保障体系与措施、确保安全文明生产的管理体系与措施进行评审。
依据投标人提供的确保人、材、机的保障体系与措施进行评审。
2.2.1（3）报价文件评审标准"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out, source, notes = agent.finalize(
        current_outline=["招标公告", "投标人须知", "评标及定标办法", "合同条款及格式"],
        current_source="toc",
        review_outline=[],
        merged_text=text,
        lines=lines,
    )
    assert source == "review_standard"
    assert len(out) == 4
    assert out[0].startswith("工程项目整体理解")
    assert any("目录治理Agent" in n for n in notes)


def test_outline_manager_keep_clean_review_outline():
    agent = OutlineManagerAgent()
    text = "技术文件评审标准"
    lines = [text]
    review_outline = [
        "工程概况",
        "主要施工方法",
        "拟投入的主要物资计划",
        "拟投入的主要施工机械、设备计划",
    ]
    out, source, notes = agent.finalize(
        current_outline=review_outline,
        current_source="review_standard",
        review_outline=review_outline,
        merged_text=text,
        lines=lines,
    )
    assert source == "review_standard"
    assert out == review_outline
    assert notes == []


def test_outline_manager_extract_from_comprehensive_table_when_toc_is_broken():
    agent = OutlineManagerAgent()
    text = """目录
第一章 招标公告 错误!未定义书签。
第二章 投标人须知 错误!未定义书签。
第三章 评标及定标 错误!未定义书签。
第四章 合同条款及格式 错误!未定义书签。

综合评审表
施工组织设计
1、主要施工方案与技术措施：对工程建设中的重点、难点、特点是否进行分析。
2、质量控制措施：是否有相关质量管理与保证措施。
3、安全控制措施：施工安全保障体系是否健全。
4、进度控制措施：进度计划是否根据项目总工期要求逐级分解。
5、成本控制计划：成本控制计划是否做到思路科学、全面。
6、环境保护及文明施工保障体系：是否根据本工程特点制定出科学合理措施。
7、主要施工机械、设备计划：是否对设备数量、选型配置、进场时间安排合理。
8、应急处置措施：是否有应对突发状况的具体措施方案。
评标委员会结合本项目特点及招标文件要求，对投标人提供的施工组织设计进行综合评价。
以上8项，每一项最高得5分，满分40分。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out, source, notes = agent.finalize(
        current_outline=[
            "招标公告 错误!未定义书签",
            "投标人须知 错误!未定义书签",
            "评标及定标 错误!未定义书签",
            "合同条款及格式 错误!未定义书签",
        ],
        current_source="toc",
        review_outline=[],
        merged_text=text,
        lines=lines,
    )
    assert source == "review_standard"
    assert len(out) == 8
    assert out[0] == "主要施工方案与技术措施"
    assert out[-1] == "应急处置措施"
    assert any("综合评审表" in n for n in notes)
