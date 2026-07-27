"""Tests for utils_write_docx module."""
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from backend.tests.export_test_contract_fixtures import (
    isolated_test_module_bindings,
)


_WRITE_DOCX_RUNTIME_BINDINGS = {
    "Document": ("docx", "Document"),
    "Pt": ("docx.shared", "Pt"),
    "Cm": ("docx.shared", "Cm"),
    "WD_LINE_SPACING": ("docx.enum.text", "WD_LINE_SPACING"),
    "WD_ALIGN_PARAGRAPH": ("docx.enum.text", "WD_ALIGN_PARAGRAPH"),
    "_set_paragraph": ("backend.utils_write_docx", "_set_paragraph"),
    "write_compose_to_docx": (
        "backend.utils_write_docx",
        "write_compose_to_docx",
    ),
}


@pytest.fixture(scope="module", autouse=True)
def _isolate_write_docx_runtime_modules():
    with isolated_test_module_bindings(
        globals(),
        _WRITE_DOCX_RUNTIME_BINDINGS,
        module_prefixes=("backend.utils_write_docx",),
    ):
        yield


def approx_emu(expected_cm, tolerance=0.01):
    """Compare EMU values with tolerance for floating point precision."""
    expected_emu = Cm(expected_cm)
    return pytest.approx(expected_emu, rel=tolerance)


class TestSetParagraph:
    """Tests for _set_paragraph helper function."""

    def test_basic_text_and_font(self):
        """Test basic text addition with font settings."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "测试文本", size_pt=14)
        
        run = p.runs[0]
        assert run.text == "测试文本"
        assert run.font.size == Pt(14)
        assert run.font.name == "宋体"
        assert run.bold is False

    def test_bold_text(self):
        """Test bold text setting."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "加粗文本", size_pt=16, bold=True)
        
        run = p.runs[0]
        assert run.bold is True

    def test_custom_font_name(self):
        """Test custom font name setting."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "自定义字体", size_pt=12, font_name="黑体")
        
        run = p.runs[0]
        assert run.font.name == "黑体"

    def test_line_spacing(self):
        """Test that line spacing is set to exactly 22pt."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "测试行距", size_pt=14)
        
        pf = p.paragraph_format
        assert pf.line_spacing_rule == WD_LINE_SPACING.EXACTLY
        assert pf.line_spacing == Pt(22)

    def test_first_line_indent_positive(self):
        """Test first line indent with positive value."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "首行缩进测试", size_pt=14, first_line_indent_cm=1.5)
        
        pf = p.paragraph_format
        assert pf.first_line_indent == approx_emu(1.5)

    def test_first_line_indent_zero(self):
        """Test first line indent with zero value (no indent)."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "无缩进标题", size_pt=16, first_line_indent_cm=0.0)
        
        pf = p.paragraph_format
        # When indent is 0, it should not be explicitly set
        assert pf.first_line_indent is None or pf.first_line_indent == Cm(0)

    def test_alignment_center(self):
        """Test center alignment."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "居中文本", size_pt=16, alignment=WD_ALIGN_PARAGRAPH.CENTER)
        
        pf = p.paragraph_format
        assert pf.alignment == WD_ALIGN_PARAGRAPH.CENTER

    def test_alignment_justify(self):
        """Test justify alignment."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "两端对齐文本", size_pt=14, alignment=WD_ALIGN_PARAGRAPH.JUSTIFY)
        
        pf = p.paragraph_format
        assert pf.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY

    def test_alignment_none(self):
        """Test that alignment is not set when None."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(p, "默认对齐", size_pt=14, alignment=None)
        
        # When alignment is None, it should remain default (None or LEFT)
        pf = p.paragraph_format
        assert pf.alignment is None or pf.alignment == WD_ALIGN_PARAGRAPH.LEFT

    def test_full_parameters(self):
        """Test with all parameters specified."""
        doc = Document()
        p = doc.add_paragraph()
        
        _set_paragraph(
            p,
            "完整参数测试",
            size_pt=18,
            bold=True,
            font_name="楷体",
            first_line_indent_cm=2.0,
            alignment=WD_ALIGN_PARAGRAPH.RIGHT,
        )
        
        run = p.runs[0]
        assert run.text == "完整参数测试"
        assert run.font.size == Pt(18)
        assert run.bold is True
        assert run.font.name == "楷体"
        
        pf = p.paragraph_format
        assert pf.first_line_indent == approx_emu(2.0)
        assert pf.alignment == WD_ALIGN_PARAGRAPH.RIGHT


class TestWriteComposeToDocx:
    """Tests for write_compose_to_docx function."""

    def test_creates_docx_file(self):
        """Test that a DOCX file is created."""
        sections = [{"title": "测试章节", "content": "测试内容"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            assert os.path.exists(output_path)
            assert os.path.getsize(output_path) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_page_setup_a4(self):
        """Test that page is set up as A4."""
        sections = [{"title": "测试", "content": "内容"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            section = doc.sections[0]
            
            # A4 dimensions (with tolerance for EMU precision)
            assert section.page_width == approx_emu(21.0)
            assert section.page_height == approx_emu(29.7)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_page_margins(self):
        """Test page margins are correctly set."""
        sections = [{"title": "测试", "content": "内容"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            section = doc.sections[0]
            
            assert section.top_margin == approx_emu(2.5)
            assert section.bottom_margin == approx_emu(2.0)
            assert section.left_margin == approx_emu(2.0)
            assert section.right_margin == approx_emu(2.0)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_single_section(self):
        """Test with a single section."""
        sections = [{"title": "第一章 概述", "content": "这是概述的内容。"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            paragraphs = doc.paragraphs
            
            # Should have 2 paragraphs: title + content
            assert len(paragraphs) >= 2
            
            # Title paragraph
            title_text = paragraphs[0].text
            assert title_text == "第一章 概述"
            
            # Content paragraph
            content_text = paragraphs[1].text
            assert content_text == "这是概述的内容。"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_multiple_sections(self):
        """Test with multiple sections."""
        sections = [
            {"title": "第一章", "content": "第一章内容"},
            {"title": "第二章", "content": "第二章内容"},
            {"title": "第三章", "content": "第三章内容"},
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            paragraphs = doc.paragraphs
            
            # Should have 6 paragraphs: 3 titles + 3 contents
            assert len(paragraphs) >= 6
            
            # Check titles
            assert paragraphs[0].text == "第一章"
            assert paragraphs[2].text == "第二章"
            assert paragraphs[4].text == "第三章"
            
            # Check contents
            assert paragraphs[1].text == "第一章内容"
            assert paragraphs[3].text == "第二章内容"
            assert paragraphs[5].text == "第三章内容"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_missing_title_uses_default(self):
        """Test that missing title uses default value."""
        sections = [{"content": "只有内容没有标题"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            paragraphs = doc.paragraphs
            
            # Title should be default
            assert paragraphs[0].text == "未命名章节"
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_missing_content_uses_empty(self):
        """Test that missing content uses empty string."""
        sections = [{"title": "只有标题"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            paragraphs = doc.paragraphs
            
            # Content should be empty
            assert paragraphs[1].text == ""
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_empty_sections_list(self):
        """Test with empty sections list."""
        sections = []
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            # File should be created even if empty
            assert os.path.exists(output_path)
            
            doc = Document(output_path)
            # Should have no content paragraphs (only default empty paragraph)
            assert len(doc.paragraphs) <= 1
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_title_formatting(self):
        """Test that title is formatted correctly (16pt, bold, center)."""
        sections = [{"title": "测试标题", "content": "内容"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            title_para = doc.paragraphs[0]
            
            # Check font size and bold
            run = title_para.runs[0]
            assert run.font.size == Pt(16)
            assert run.bold is True
            
            # Check alignment
            assert title_para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_content_formatting(self):
        """Test that content is formatted correctly (14pt, justify, indent)."""
        sections = [{"title": "标题", "content": "正文内容测试"}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            content_para = doc.paragraphs[1]
            
            # Check font size and not bold
            run = content_para.runs[0]
            assert run.font.size == Pt(14)
            assert run.bold is False
            
            # Check alignment
            assert content_para.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
            
            # Check first line indent
            assert content_para.paragraph_format.first_line_indent == approx_emu(1.5)
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_default_output_path(self):
        """Test with default output path."""
        sections = [{"title": "测试", "content": "内容"}]
        default_path = "output.docx"
        
        try:
            # Clean up if exists
            if os.path.exists(default_path):
                os.unlink(default_path)
            
            write_compose_to_docx(sections, style={})
            
            assert os.path.exists(default_path)
        finally:
            if os.path.exists(default_path):
                os.unlink(default_path)

    def test_long_content(self):
        """Test with long content."""
        long_content = "这是一段很长的测试内容。" * 100
        sections = [{"title": "长内容测试", "content": long_content}]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            content_para = doc.paragraphs[1]
            
            assert content_para.text == long_content
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_special_characters(self):
        """Test with special characters in content."""
        sections = [
            {
                "title": "特殊字符测试：<>&\"'",
                "content": "内容包含特殊字符：\n换行\t制表符\r回车"
            }
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            assert "特殊字符测试" in doc.paragraphs[0].text
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_unicode_content(self):
        """Test with Unicode content."""
        sections = [
            {
                "title": "Unicode测试：日本語・한국어・العربية",
                "content": "混合内容：emoji 😀 数学符号 ∑∏∫ 希腊字母 αβγ"
            }
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = f.name
        
        try:
            write_compose_to_docx(sections, style={}, output_path=output_path)
            
            doc = Document(output_path)
            assert "Unicode测试" in doc.paragraphs[0].text
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestSetParagraphEastAsiaFont:
    """Tests for East Asian font setting in _set_paragraph."""

    def test_east_asia_font_set_when_rpr_exists(self):
        """Test that East Asian font is set when rPr element exists."""
        doc = Document()
        p = doc.add_paragraph()
        
        # Add run first to create rPr
        run = p.add_run("初始文本")
        
        # Now call _set_paragraph on a new paragraph
        p2 = doc.add_paragraph()
        _set_paragraph(p2, "东亚字体测试", size_pt=14, font_name="黑体")
        
        # Verify the run has the font set
        run2 = p2.runs[0]
        assert run2.font.name == "黑体"

    def test_multiple_paragraphs_different_fonts(self):
        """Test multiple paragraphs with different fonts."""
        doc = Document()
        
        p1 = doc.add_paragraph()
        _set_paragraph(p1, "宋体文本", size_pt=14, font_name="宋体")
        
        p2 = doc.add_paragraph()
        _set_paragraph(p2, "黑体文本", size_pt=14, font_name="黑体")
        
        p3 = doc.add_paragraph()
        _set_paragraph(p3, "楷体文本", size_pt=14, font_name="楷体")
        
        assert p1.runs[0].font.name == "宋体"
        assert p2.runs[0].font.name == "黑体"
        assert p3.runs[0].font.name == "楷体"
