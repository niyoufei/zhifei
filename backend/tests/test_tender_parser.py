"""
TenderParser 单元测试
覆盖 tender_parser.py 的所有方法
"""

from __future__ import annotations

import hashlib
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.zhifei_autoplan.models import (
    TenderDimension,
    TenderIndexItem,
    TenderIndexMatrix,
)
from backend.zhifei_autoplan.parsers.tender_parser import Section, TenderParser
from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger_from_inputs,
)

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def parser():
    """创建不带 LLM 的解析器实例"""
    return TenderParser(llm=None)


@pytest.fixture
def parser_with_llm():
    """创建带 LLM 的解析器实例"""
    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="关键词1,关键词2")
    return TenderParser(llm=mock_llm)


# ==============================================================================
# __init__ tests
# ==============================================================================


class TestInit:
    """测试 __init__ 方法"""

    def test_init_without_llm(self):
        """初始化时不提供 LLM"""
        parser = TenderParser()
        assert parser.llm is None

    def test_init_with_llm(self):
        """初始化时提供 LLM"""
        mock_llm = MagicMock()
        parser = TenderParser(llm=mock_llm)
        assert parser.llm is mock_llm


class TestStyleRequirements:
    """招标版式要求应覆盖默认值，并保持两种行距模式互斥。"""

    def test_extract_fixed_line_spacing(self, parser):
        style, _ = parser._extract_style_requirements("正文采用宋体四号，行距固定值24磅。")

        assert style["line_spacing_pt"] == 24.0
        assert "line_spacing" not in style

    def test_extract_multiple_line_spacing(self, parser):
        style, _ = parser._extract_style_requirements("正文采用宋体四号，行距为1.5倍。")

        assert style["line_spacing"] == 1.5
        assert "line_spacing_pt" not in style


class TestChapterRequirements:
    """章节要求只接受可执行条款，评分残句保留为待复核证据。"""

    def test_fragments_are_excluded_and_actionable_requirement_is_retained(
        self, parser
    ):
        title = "质量管理与验收"
        fragments = [
            "内容未提供或无任何针对性、可行性，本项不得",
            "每提供 1 个得 2 分，本项满分 4",
            "中规定提供的业绩证明材料",
        ]
        executable = "投标人必须建立质量保证体系，明确岗位职责和验收流程"
        text = "\n".join([title, *fragments, executable])

        requirements, review_rows = parser._extract_chapter_requirement_candidates(
            text, [title]
        )

        assert requirements == {title: [executable]}
        assert parser._extract_chapter_requirements(text, [title]) == requirements
        assert [row["requirement"] for row in review_rows] == fragments
        assert all(row["status"] == "NEEDS_REVIEW" for row in review_rows)
        assert all(row["mandatory"] is False for row in review_rows)
        assert all(row["prompt_eligible"] is False for row in review_rows)
        reasons = {
            row["requirement"]: set(row["reason_codes"]) for row in review_rows
        }
        assert "TRUNCATED_SUFFIX" in reasons[fragments[0]]
        assert "SCORE_ONLY_FRAGMENT" in reasons[fragments[1]]
        assert "TRUNCATED_PREFIX" in reasons[fragments[2]]

    def test_build_matrix_exposes_review_metadata_without_prompt_input(self, parser):
        title = "质量管理与验收"
        fragment = "每提供 1 个得 2 分，本项满分 4"
        executable = "施工单位应编制材料复验计划并明确验收责任人"
        text = f"{title}\n{fragment}\n{executable}"
        parser._extract_outline = lambda _text: (
            [title],
            {"source": "test", "global_requirements": []},
        )
        parser._extract_style_requirements = lambda _text: (
            {},
            {"source": "none", "global_requirements": []},
        )
        parser._extract_index_matrix_sync = lambda _sections, _sources: []

        matrix = parser._build_matrix_from_texts([("/path/tender.pdf", text)])

        assert matrix.chapter_requirements == {title: [executable]}
        review = matrix.extraction_meta["chapter_requirement_review"]
        assert review["status"] == "NEEDS_REVIEW"
        assert review["count"] == 1
        assert review["prompt_excluded_count"] == 1
        assert review["rows"][0]["requirement"] == fragment

    def test_numbered_requirement_with_arbitrary_subject_is_retained(self, parser):
        title = "进度纠偏"
        executable = "（1）施工期间应设置每日纠偏闭环"

        requirements, review_rows = parser._extract_chapter_requirement_candidates(
            f"{title}\n{executable}", [title]
        )

        assert requirements == {title: [executable]}
        assert review_rows == []


# ==============================================================================
# _is_qa_file tests
# ==============================================================================


class TestIsQaFile:
    """测试 _is_qa_file 方法"""

    def test_qa_file_by_path_dyi(self, parser):
        """路径包含'答疑'"""
        result = parser._is_qa_file("/path/to/答疑文件.pdf", "普通内容")
        assert result is True

    def test_qa_file_by_path_chengqing(self, parser):
        """路径包含'澄清'"""
        result = parser._is_qa_file("/path/to/澄清说明.pdf", "普通内容")
        assert result is True

    def test_qa_file_by_path_buyi(self, parser):
        """路径包含'补遗'"""
        result = parser._is_qa_file("/path/to/补遗文件.pdf", "普通内容")
        assert result is True

    def test_qa_file_by_path_biangeng(self, parser):
        """路径包含'变更'"""
        result = parser._is_qa_file("/path/to/变更通知.pdf", "普通内容")
        assert result is True

    def test_qa_file_by_text_dyi(self, parser):
        """内容包含'答疑'"""
        result = parser._is_qa_file("/path/to/normal.pdf", "这是答疑内容")
        assert result is True

    def test_qa_file_by_text_chengqing(self, parser):
        """内容包含'澄清'"""
        result = parser._is_qa_file("/path/to/normal.pdf", "澄清说明如下")
        assert result is True

    def test_qa_file_by_text_buyi(self, parser):
        """内容包含'补遗'"""
        result = parser._is_qa_file("/path/to/normal.pdf", "补遗第一条")
        assert result is True

    def test_qa_file_by_text_biangeng(self, parser):
        """内容包含'变更'"""
        result = parser._is_qa_file("/path/to/normal.pdf", "工程变更通知")
        assert result is True

    def test_not_qa_file(self, parser):
        """普通文件（路径和内容都不匹配）"""
        result = parser._is_qa_file("/path/to/tender.pdf", "招标文件正文")
        assert result is False

    def test_qa_file_both_match(self, parser):
        """路径和内容都匹配"""
        result = parser._is_qa_file("/path/答疑.pdf", "答疑内容")
        assert result is True


# ==============================================================================
# _split_sections tests
# ==============================================================================


class TestSplitSections:
    """测试 _split_sections 方法"""

    def test_empty_text(self, parser):
        """空文本 - 返回空列表"""
        result = parser._split_sections("")
        assert len(result) == 0

    def test_no_section_match(self, parser):
        """没有匹配到任何章节标题"""
        text = "这是一段普通文本\n没有任何章节标题"
        result = parser._split_sections(text)
        assert len(result) == 1
        assert result[0].title == "未分类"
        assert "普通文本" in result[0].text

    def test_single_section_qianyan(self, parser):
        """单个章节 - 前言（后续内容不含关键词）"""
        text = "第一章 前言\n这是内容"
        result = parser._split_sections(text)
        assert len(result) == 1
        assert result[0].title == "前言"

    def test_single_section_gaikuang(self, parser):
        """单个章节 - 工程概况"""
        text = "第二章 工程概况\n项目位于XX市"
        result = parser._split_sections(text)
        assert len(result) == 1
        assert result[0].title == "工程概况"

    def test_multiple_sections(self, parser):
        """多个章节（内容不含关键词）"""
        text = """第一章 前言
第一部分内容
第二章 工程概况
第二部分内容
第三章 技术标准
第三部分内容"""
        result = parser._split_sections(text)
        assert len(result) == 3
        assert result[0].title == "前言"
        assert result[1].title == "工程概况"
        assert result[2].title == "技术标准"

    def test_section_jishu_biaozhun(self, parser):
        """技术标准章节"""
        text = "一、技术标准\n执行国家标准"
        result = parser._split_sections(text)
        assert result[0].title == "技术标准"

    def test_section_anquan(self, parser):
        """安全章节"""
        text = "第五章 安全文明施工\n安全措施要求"
        result = parser._split_sections(text)
        assert result[0].title == "安全"

    def test_section_jindu(self, parser):
        """进度计划章节"""
        text = "第六章 进度计划\n工期为120天"
        result = parser._split_sections(text)
        assert result[0].title == "进度计划"

    def test_section_huanbao(self, parser):
        """环保章节"""
        text = "第七章 环境保护\n减少扬尘污染"
        result = parser._split_sections(text)
        assert result[0].title == "环境保护"

    def test_section_pingfen(self, parser):
        """评分章节"""
        text = "附件 评分标准\n技术标得分"
        result = parser._split_sections(text)
        assert result[0].title == "评分"

    def test_section_koufen(self, parser):
        """扣分章节"""
        text = "第八章 扣分项\n缺失资料扣5分"
        result = parser._split_sections(text)
        assert result[0].title == "扣分"

    def test_section_feibiao(self, parser):
        """废标章节"""
        text = "第九章 废标条款\n资质不符废标"
        result = parser._split_sections(text)
        assert result[0].title == "废标"

    def test_section_content_preserved(self, parser):
        """章节内容完整保留"""
        text = """工程概况
第一行内容
第二行内容
第三行内容"""
        result = parser._split_sections(text)
        assert "第一行内容" in result[0].text
        assert "第二行内容" in result[0].text
        assert "第三行内容" in result[0].text


class TestExtractProjectMeta:
    """测试项目名称/编号抽取"""

    def test_extract_project_meta_with_colon(self, parser):
        text = """项目名称：长山路（县界—岱河路）建设工程
项目编号：CSL-2026-001
招标文件"""
        name, code = parser._extract_project_meta(text)
        assert name == "长山路（县界—岱河路）建设工程"
        assert code == "CSL-2026-001"

    def test_extract_project_meta_from_title_fallback(self, parser):
        text = """长山路建设工程招标文件
第一章 编制说明"""
        name, code = parser._extract_project_meta(text)
        assert name == "长山路建设工程"
        assert code is None

    def test_extract_project_meta_rebuilds_wrapped_road_title(self, parser):
        text = """包河经开区延边路（繁华大道-沈阳路）、
月谭路（饮马井路-南淝河路）、饮马井路（月谭路-长
春路）等3条道路工程补疑2
招标项目编号：2025BFBGZ50935
"""
        name, code = parser._extract_project_meta(text)
        assert name == (
            "包河经开区延边路（繁华大道-沈阳路）、"
            "月谭路（饮马井路-南淝河路）、"
            "饮马井路（月谭路-长春路）等3条道路工程"
        )
        assert code == "2025BFBGZ50935"

    def test_extract_project_meta_ignores_unbalanced_label_tail(self, parser):
        text = """项目名称：春路）等3条道路工程补疑2
包河经开区延边路（繁华大道-沈阳路）、月谭路（饮马井路-南淝河路）、
饮马井路（月谭路-长春路）等3条道路工程
"""
        name, _ = parser._extract_project_meta(text)
        assert name.startswith("包河经开区延边路")
        assert name.endswith("等3条道路工程")

    def test_extract_outline_from_review_standard_block(self, parser):
        text = """技术文件详细评审标准
依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
1）工程概况
2）主要施工方法
3）拟投入的主要物资计划
4）拟投入的主要施工机械、设备计划
5）劳动力安排计划
6）确保工程质量的技术组织措施
7）确保安全生产的技术组织措施
8）确保工期的技术组织措施
9）确保文明施工的技术组织措施
10）施工总平面布置图
一般得0分<F≤60分，良好得60分<F<90分，优秀得90分≤F≤100分。"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert len(outline) == 10
        assert outline[0] == "工程概况"
        assert outline[-1] == "施工总平面布置图"

    def test_extract_outline_prefers_review_standard_over_toc(self, parser):
        text = """目录
第一章 编制说明
第二章 施工部署
第三章 质量管理

技术文件详细评审标准
依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
1）工程概况
2）主要施工方法
3）拟投入的主要物资计划"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert outline == ["工程概况", "主要施工方法", "拟投入的主要物资计划"]

    def test_extract_outline_review_standard_with_spaced_anchor(self, parser):
        text = """技 术 文 件 详 细 评 审 标 准
依据投标人提供的施工组织设计进行评审，包 括 但 不 限 于 以 下 内 容：
1）工程概况
2）主要施工方法
3）拟投入的主要物资计划
4）拟投入的主要施工机械、设备计划"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert outline[:2] == ["工程概况", "主要施工方法"]

    def test_extract_outline_review_standard_not_polluted_by_other_numbered_rules(self, parser):
        text = """技术文件详细评审标准
依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
1）工程概况2）主要施工方法3）拟投入的主要物资计划4）拟投入的主要施工机械、设备计划
5）劳动力安排计划6）确保工程质量的技术组织措施7）确保安全生产的技术组织措施
8）确保工期的技术组织措施9）确保文明施工的技术组织措施10）施工总平面布置图
一般得0分<F≤60分，良好得60分<F<90分，优秀得90分≤F≤100分。未提供的，不得分。
注：施工组织设计编制建议……
评标程序：
1项、第2项、第3项；投标文件在符合性、响应性等方面存在的偏差；
2否决投标的其他情形；3投标文件澄清与说明。"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert len(outline) == 10
        assert outline[0] == "工程概况"
        assert outline[-1] == "施工总平面布置图"

    def test_extract_outline_review_standard_stops_before_scoring_and_proof_prose(self, parser):
        text = """技术文件详细评审标准
依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
1）针对工程项目整体理解
2）工程重点难点的保障体系与措施
3）拟采用的新技术、新工艺（如有）
4）确保工期与质量的保障体系与措施
5）确保人、材、机的保障体系与措施
6）确保安全文明生产的管理体系与措施
7）本项评委打分为一般或优秀的，评委须提出充足的理由并在评标报告中陈述
8）本项满分5分
9）投标人提供的项目经理业绩证明材料应反映岗位信息
"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert outline == [
            "针对工程项目整体理解",
            "工程重点难点的保障体系与措施",
            "拟采用的新技术、新工艺（如有）",
            "确保工期与质量的保障体系与措施",
            "确保人、材、机的保障体系与措施",
            "确保安全文明生产的管理体系与措施",
        ]

    def test_extract_outline_stops_before_compilation_note_and_bid_price_formula(self, parser):
        text = """技术文件详细评审标准
依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
1）针对工程项目整体理解
2）工程重点难点及危大工程的保障体系与措施
3）拟采用的新技术、新工艺（如有）
4）确保工期与质量的保障体系与措施
5）确保人、材、机的保障体系与措施
6）确保安全文明生产的管理体系与措施
7）投标结合工程实际特点及需要，国家及地方现有工法规范已有的内容无需重复编制
8）项目经理业绩提供的业绩证明资料同投标人须知前附表附录5中规定提供的业绩证明材料
9）确定评标基准价，评标价平均值等于评标基准价
10）报价文件，投标报价85分
11）若T大于等于Z的60%，按照T从高到低确定规定数量
"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert outline == [
            "针对工程项目整体理解",
            "工程重点难点及危大工程的保障体系与措施",
            "拟采用的新技术、新工艺（如有）",
            "确保工期与质量的保障体系与措施",
            "确保人、材、机的保障体系与措施",
            "确保安全文明生产的管理体系与措施",
        ]

    def test_extract_outline_review_standard_not_polluted_by_contract_list(self, parser):
        text = """技术文件详细评审标准
依据投标人提供的施工组织设计进行评审，包括但不限于以下内容：
1）工程概况
2）主要施工方法
3）拟投入的主要物资计划
4）拟投入的主要施工机械、设备计划
5）劳动力安排计划
6）确保工程质量的技术组织措施
7）确保安全生产的技术组织措施
8）确保工期的技术组织措施
9）确保文明施工的技术组织措施
10）施工总平面布置图
注：未提供的，不得分。

合同文件构成包括但不限于以下内容：
1）中标通知书
2）投标函及其附录
3）专用合同条款及其附件
4）通用合同条款
5）图纸
6）已标价工程量清单或预算书
"""
        outline, meta = parser._extract_outline(text)
        assert meta.get("source") == "review_standard"
        assert len(outline) == 10
        assert "中标通知书" not in outline
        assert "投标函及其附录" not in outline


# ==============================================================================
# _read_pdf tests (with mocking)
# ==============================================================================


class TestReadPdf:
    """测试 _read_pdf 方法"""

    def test_read_pdf_single_page(self, parser):
        """读取单页 PDF"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "页面内容"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            path, text = parser._read_pdf("/path/to/file.pdf")
            assert path == "/path/to/file.pdf"
            assert text == "页面内容"

    def test_read_pdf_multiple_pages(self, parser):
        """读取多页 PDF"""
        mock_pages = []
        for i in range(3):
            page = MagicMock()
            page.extract_text.return_value = f"第{i+1}页内容"
            mock_pages.append(page)

        mock_pdf = MagicMock()
        mock_pdf.pages = mock_pages
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            _path, text = parser._read_pdf("/path/to/file.pdf")
            assert text == "第1页内容\f第2页内容\f第3页内容"

    def test_read_pdf_empty_page(self, parser):
        """读取空页面"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            _path, text = parser._read_pdf("/path/to/file.pdf")
            assert text == ""

    def test_read_pdf_mixed_pages(self, parser):
        """读取混合页面（有内容和空页面）"""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "有内容"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = None
        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = "又有内容"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            _path, text = parser._read_pdf("/path/to/file.pdf")
            assert text == "有内容\f\f又有内容"

    def test_projects_p92_procedural_deadline_with_reversible_locator(
        self, parser, tmp_path
    ):
        source = tmp_path / "招标文件.pdf"
        source_bytes = b"content-addressed-test-pdf"
        source.write_bytes(source_bytes)
        pages = [f"第{page}页普通条款" for page in range(1, 93)]
        pages[90] = "隐蔽工程检查通知应提前48小时提交，不合格项另行通知。"
        pages[91] = (
            "承包人在收到监理人发出的《不合格分项报告》或监理通知单后，"
            "必须在监\n理人规定时间内按要求完成整改，并申请复验。"
        )
        text = "\f".join(pages)

        matrix = parser._build_matrix_from_texts([(str(source), text)])

        fact = matrix.extraction_meta["project_facts"][
            "deviation_action_deadline"
        ]
        evidence = fact["evidence"]
        target = "在监理人规定时间内按要求完成整改"
        source_target = "在监\n理人规定时间内按要求完成整改"
        document_sha256 = hashlib.sha256(source_bytes).hexdigest()
        page_text_sha256 = hashlib.sha256(pages[91].encode("utf-8")).hexdigest()
        expected_start = text.index(source_target)
        assert fact["value"] == target
        assert fact["unit"] == ""
        assert fact["status"] == "verified"
        assert evidence["page"] == 92
        assert evidence["document_sha256"] == document_sha256
        assert evidence["page_text_sha256"] == page_text_sha256
        assert evidence["start"] == expected_start
        assert evidence["page_start"] == pages[91].index(source_target)
        assert evidence["locator"] == (
            f"招标文件.pdf#document_sha256={document_sha256}"
            f"&page=92&page_text_sha256={page_text_sha256}"
            f"&offset={expected_start}"
        )
        assert "48" not in fact["value"]

    def test_directory_schedule_heading_cannot_hide_verified_150_day_fact(
        self,
        parser,
        tmp_path,
    ):
        source = tmp_path / "招标文件.pdf"
        source_bytes = b"tender-duration-source"
        source.write_bytes(source_bytes)
        pages = [
            "目录\n第五章 确保工期的技术组织措施\n第六章 进度计划",
            "2.8 计划工期：150 日历天。投标人应据此编制总进度计划。",
        ]
        text = "\f".join(pages)

        matrix = parser._build_matrix_from_texts([(str(source), text)])
        fact = matrix.extraction_meta["project_facts"][
            "planned_duration_days"
        ]
        evidence = fact["evidence"]
        document_sha256 = hashlib.sha256(source_bytes).hexdigest()
        page_text_sha256 = hashlib.sha256(pages[1].encode("utf-8")).hexdigest()
        expected_start = text.index("计划工期：150 日历天")

        assert fact["value"] == 150
        assert fact["unit"] == "天"
        assert fact["status"] == "verified"
        assert evidence["page"] == 2
        assert evidence["document_sha256"] == document_sha256
        assert evidence["page_text_sha256"] == page_text_sha256
        assert evidence["start"] == expected_start
        assert evidence["page_start"] == pages[1].index(
            "计划工期：150 日历天"
        )

        schedule_item = next(
            item
            for item in matrix.items
            if item.dimension == TenderDimension.SCHEDULE
        )
        duration_span = next(
            span
            for span in schedule_item.source_spans
            if "150 日历天" in span.snippet
        )
        assert duration_span.page == 2
        assert duration_span.page_text_sha256 == page_text_sha256

        ledger = build_project_fact_ledger_from_inputs(
            payload={"project_id": "P-150-DAYS"},
            tender=matrix.model_dump(mode="json"),
            boq_wbs_cpm={},
        )
        ledger_fact = ledger["facts"]["planned_duration_days"]
        assert ledger_fact["value"] == 150
        assert ledger_fact["unit"] == "天"
        assert ledger_fact["status"] == "verified"
        assert ledger_fact["evidence"]["page"] == 2
        assert ledger_fact["evidence"]["document_sha256"] == document_sha256
        assert ledger_fact["evidence"]["page_text_sha256"] == page_text_sha256


# ==============================================================================
# _extract_index_matrix tests
# ==============================================================================


class TestExtractIndexMatrix:
    """测试 _extract_index_matrix 方法"""

    @pytest.mark.asyncio
    async def test_extract_empty_sections(self, parser):
        """空章节列表"""
        sections = []
        sources = []
        result = await parser._extract_index_matrix(sections, sources)
        assert len(result) == 6  # 6 个维度
        for item in result:
            assert item.keywords == []

    @pytest.mark.asyncio
    async def test_extract_quality_dimension(self, parser):
        """提取质量维度"""
        sections = [Section("技术标准", "质量验收标准要求合格", [])]
        sources = [("/path/file.pdf", "质量标准内容")]
        result = await parser._extract_index_matrix(sections, sources)

        quality_item = next(i for i in result if i.dimension == TenderDimension.QUALITY)
        assert "质量" in quality_item.keywords
        assert quality_item.weight >= 0.2

    @pytest.mark.asyncio
    async def test_extract_safety_dimension(self, parser):
        """提取安全维度"""
        sections = [Section("安全", "安全文明施工风险防控", [])]
        sources = [("/path/file.pdf", "安全要求")]
        result = await parser._extract_index_matrix(sections, sources)

        safety_item = next(i for i in result if i.dimension == TenderDimension.SAFETY)
        assert "安全" in safety_item.keywords

    @pytest.mark.asyncio
    async def test_extract_schedule_dimension(self, parser):
        """提取进度维度"""
        sections = [Section("进度计划", "工期120天进度节点要求", [])]
        sources = [("/path/file.pdf", "工期计划")]
        result = await parser._extract_index_matrix(sections, sources)

        schedule_item = next(i for i in result if i.dimension == TenderDimension.SCHEDULE)
        assert "工期" in schedule_item.keywords or "进度" in schedule_item.keywords

    @pytest.mark.asyncio
    async def test_extract_environment_dimension(self, parser):
        """提取环保维度"""
        sections = [Section("环保", "环保要求扬尘噪声控制", [])]
        sources = [("/path/file.pdf", "环保措施")]
        result = await parser._extract_index_matrix(sections, sources)

        env_item = next(i for i in result if i.dimension == TenderDimension.ENVIRONMENT)
        assert "环保" in env_item.keywords or "扬尘" in env_item.keywords

    @pytest.mark.asyncio
    async def test_extract_difficulty_dimension(self, parser):
        """提取重难点维度"""
        sections = [Section("重难点", "重难点分析关键工序", [])]
        sources = [("/path/file.pdf", "重难点内容")]
        result = await parser._extract_index_matrix(sections, sources)

        diff_item = next(i for i in result if i.dimension == TenderDimension.DIFFICULTY)
        assert "重难点" in diff_item.keywords

    @pytest.mark.asyncio
    async def test_extract_penalty_dimension(self, parser):
        """提取扣分维度"""
        sections = [Section("扣分", "扣分项废标条款", [])]
        sources = [("/path/file.pdf", "扣分规则")]
        result = await parser._extract_index_matrix(sections, sources)

        penalty_item = next(i for i in result if i.dimension == TenderDimension.PENALTY)
        assert "扣分" in penalty_item.keywords or "废标" in penalty_item.keywords

    @pytest.mark.asyncio
    async def test_weight_increases_with_keywords(self, parser):
        """权重随关键词增加"""
        sections = [Section("质量", "质量验收标准合格优良", [])]  # 5个关键词
        sources = []
        result = await parser._extract_index_matrix(sections, sources)

        quality_item = next(i for i in result if i.dimension == TenderDimension.QUALITY)
        # 初始 0.2，每个关键词 +0.1，最多 1.0
        assert quality_item.weight > 0.2

    @pytest.mark.asyncio
    async def test_weight_capped_at_1(self, parser):
        """权重上限为 1.0"""
        # 大量关键词
        text = "质量 验收 标准 合格 优良 " * 10
        sections = [Section("质量", text, [])]
        sources = []
        result = await parser._extract_index_matrix(sections, sources)

        quality_item = next(i for i in result if i.dimension == TenderDimension.QUALITY)
        assert quality_item.weight <= 1.0

    @pytest.mark.asyncio
    async def test_source_spans_created(self, parser, tmp_path):
        """创建源文件位置引用"""
        sections = [Section("质量", "质量要求", [])]
        source = tmp_path / "tender.pdf"
        source.write_bytes(b"tender-source")
        sources = [(str(source), "这是质量标准文本")]
        result = await parser._extract_index_matrix(sections, sources)

        quality_item = next(i for i in result if i.dimension == TenderDimension.QUALITY)
        assert len(quality_item.source_spans) > 0
        span = quality_item.source_spans[0]
        assert span.file_name == str(source)
        expected_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        assert span.document_sha256 == expected_sha256
        assert span.source_sha256 == expected_sha256

    @pytest.mark.asyncio
    async def test_source_spans_limit(self, parser, tmp_path):
        """源文件引用最多 5 个"""
        sections = [Section("质量", "质量要求", [])]
        # 创建大量源文件
        sources = []
        for index in range(10):
            source = tmp_path / f"file{index}.pdf"
            source.write_bytes(f"source-{index}".encode())
            sources.append((str(source), "质量标准"))
        result = await parser._extract_index_matrix(sections, sources)

        quality_item = next(i for i in result if i.dimension == TenderDimension.QUALITY)
        assert quality_item.source_spans
        assert len(quality_item.source_spans) <= 5

    @pytest.mark.asyncio
    async def test_with_llm_client(self, parser_with_llm):
        """使用 LLM 客户端"""
        sections = [Section("质量", "质量要求", [])]
        sources = [("/path/file.pdf", "质量内容")]
        result = await parser_with_llm._extract_index_matrix(sections, sources)

        # 验证 LLM 被调用
        assert parser_with_llm.llm.complete.called
        assert len(result) == 6


# ==============================================================================
# parse tests (integration)
# ==============================================================================


class TestParse:
    """测试 parse 方法（集成测试）"""

    @pytest.mark.asyncio
    async def test_parse_single_pdf(self, parser):
        """解析单个 PDF"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "工程概况\n项目位于XX市\n质量标准要求"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await parser.parse(["/path/to/tender.pdf"])

        assert isinstance(result, TenderIndexMatrix)
        assert len(result.items) == 6

    @pytest.mark.asyncio
    async def test_cpu_rules_pipeline_runs_off_event_loop_thread(self, parser):
        event_loop_thread = threading.get_ident()
        worker_threads = []
        original = parser._build_matrix_from_texts

        def tracked_build(texts):
            worker_threads.append(threading.get_ident())
            return original(texts)

        parser._build_matrix_from_texts = tracked_build
        parser._read_source_text = lambda path: (path, "工程概况\n质量标准要求")

        result = await parser.parse(["/path/to/tender.pdf"])

        assert isinstance(result, TenderIndexMatrix)
        assert worker_threads
        assert worker_threads[0] != event_loop_thread

    @pytest.mark.asyncio
    async def test_validated_cached_text_skips_source_parser(self, parser):
        calls = []
        parser._read_source_text = lambda path: calls.append(path) or (path, "unexpected")

        result = await parser.parse(
            ["/path/to/tender.pdf", "/path/to/clarification.docx"],
            cached_texts={
                "/path/to/tender.pdf": "工程概况\n质量标准要求",
                "/path/to/clarification.docx": "答疑：质量要求修正",
            },
        )

        assert isinstance(result, TenderIndexMatrix)
        assert calls == []

    @pytest.mark.asyncio
    async def test_parse_multiple_pdfs(self, parser):
        """解析多个 PDF"""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "招标文件正文"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "技术标准内容"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await parser.parse(["/path/to/tender1.pdf", "/path/to/tender2.pdf"])

        assert isinstance(result, TenderIndexMatrix)

    @pytest.mark.asyncio
    async def test_parse_with_qa_file(self, parser):
        """解析带答疑文件"""
        call_count = [0]

        def mock_open(path):
            mock_page = MagicMock()
            if "答疑" in path:
                mock_page.extract_text.return_value = "答疑内容：质量要求修正"
            else:
                mock_page.extract_text.return_value = "招标正文"

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=None)
            call_count[0] += 1
            return mock_pdf

        with patch("pdfplumber.open", side_effect=mock_open):
            result = await parser.parse(["/path/tender.pdf", "/path/答疑.pdf"])

        assert isinstance(result, TenderIndexMatrix)

    @pytest.mark.asyncio
    async def test_parse_style_matrix_uses_clarification_over_tender(self, parser):
        def mock_open(path):
            mock_page = MagicMock()
            if "答疑" in path:
                mock_page.extract_text.return_value = "澄清：正文采用仿宋体小四，行距固定值24磅。"
            else:
                mock_page.extract_text.return_value = "招标要求：正文采用宋体四号，行距固定值22磅。"
            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=None)
            return mock_pdf

        with patch("pdfplumber.open", side_effect=mock_open):
            result = await parser.parse(["/path/tender.pdf", "/path/答疑.pdf"])

        matrix = result.extraction_meta["requirement_decision_matrix"]
        assert matrix["status"] == "resolved"
        assert matrix["fields"]["line_spacing"]["selected"]["source_type"] == "clarification"
        assert result.style["line_spacing_pt"] == 24.0

    @pytest.mark.asyncio
    async def test_parse_returns_matrix_structure(self, parser):
        """验证返回的矩阵结构"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "工程概况"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await parser.parse(["/path/to/tender.pdf"])

        # 验证结构
        assert hasattr(result, "project_name")
        assert hasattr(result, "project_code")
        assert hasattr(result, "items")
        assert result.project_name is None
        assert result.project_code is None
        for item in result.items:
            assert isinstance(item, TenderIndexItem)
            assert isinstance(item.dimension, TenderDimension)

    @pytest.mark.asyncio
    async def test_parse_all_dimensions_present(self, parser):
        """验证所有 6 个维度都存在"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "招标文件"

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=None)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = await parser.parse(["/path/to/tender.pdf"])

        dimensions = {item.dimension for item in result.items}
        assert TenderDimension.QUALITY in dimensions
        assert TenderDimension.SAFETY in dimensions
        assert TenderDimension.SCHEDULE in dimensions
        assert TenderDimension.ENVIRONMENT in dimensions
        assert TenderDimension.DIFFICULTY in dimensions
        assert TenderDimension.PENALTY in dimensions


# ==============================================================================
# Section dataclass tests
# ==============================================================================


class TestSection:
    """测试 Section 数据类"""

    def test_section_creation(self):
        """创建 Section"""
        section = Section(
            title="工程概况",
            text="项目位于XX市",
            page_spans=[(1, 0, 100)]
        )
        assert section.title == "工程概况"
        assert section.text == "项目位于XX市"
        assert section.page_spans == [(1, 0, 100)]

    def test_section_empty_spans(self):
        """空 page_spans"""
        section = Section(title="前言", text="内容", page_spans=[])
        assert section.page_spans == []

    def test_section_multiple_spans(self):
        """多个 page_spans"""
        spans = [(1, 0, 100), (2, 0, 200), (3, 50, 150)]
        section = Section(title="技术标准", text="内容", page_spans=spans)
        assert len(section.page_spans) == 3
