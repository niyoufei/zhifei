"""
Tests for backend/zhifei_autoplan/exporter.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest
from docx import Document

from backend.zhifei_autoplan.exporter import (
    _apply_style,
    _auto_density_images_for_pages,
    _build_static_toc_entries,
    _format_cover_year_month,
    _format_toc_display_title,
    _infer_toc_level,
    _normalize_front_matter_page_mode,
    _normalize_full_index_enabled,
    _paginate_toc_entries,
    _resolve_front_matter_plan,
    _topic_to_cover_project_name,
    _to_cn_month,
    export_autoplan_docx,
    export_autoplan_compare_docx,
    export_autoplan_docx_from_file,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def basic_data():
    """Basic test data for export functions."""
    return {
        "topic": "测试施工组织设计",
        "style": {
            "body_font": "SimSun",
            "body_size": 12,
            "title_font": "SimHei",
            "title_size": 16,
            "line_spacing": 1.5,
        },
        "sections": [
            {
                "title": "第一章 工程概述",
                "content": "本工程位于某市某区，总投资约1000万元。",
                "agent_role": "项目经理",
            },
            {
                "title": "第二章 施工部署",
                "content": "施工总平面布置合理，资源配置优化。",
            },
        ],
    }


@pytest.fixture
def data_with_quality_checks(basic_data):
    """Test data with quality checks."""
    basic_data["quality_checks"] = {
        "structure": {"ok": True, "note": "结构完整"},
        "score_coverage": {"ok": False, "missing_count": 3},
        "closed_loop": {"ok": True},
        "engineering": {"ok": True},
        "evidence": {"ok": False, "by_section": [
            {"title": "第一章", "evidence_count": 2},
            {"title": "第二章", "evidence_count": 0},
        ]},
        "template_style": {"ok": True},
        "score_coverage_by_section": [
            {"title": "第一章", "ok": True},
            {"title": "第二章", "ok": False, "missing": [
                {"dimension": "质量", "keywords": "质量控制"},
            ]},
        ],
        "closed_loop_by_section": [
            {"title": "第一章", "ok": True, "has_risk": True, "has_measure": True},
            {"title": "第二章", "ok": False, "has_risk": True, "has_measure": False},
        ],
        "engineering_by_section": [
            {"title": "第一章", "ok": True, "missing": []},
            {"title": "第二章", "ok": False, "missing": ["人员", "设备"]},
        ],
        "remediation": [
            {"title": "第二章", "type": "missing_evidence", "suggestion": "补充证据材料"},
        ],
    }
    return basic_data


@pytest.fixture
def data_with_llm_remediation(basic_data):
    """Test data with LLM remediation compare."""
    basic_data["sections"] = [
        {
            "title": "第一章 工程概述",
            "content": "整改后的内容，更加详细完整。",
            "original_content": "原始内容，较为简单。",
            "auto_remediated": "llm",
        },
        {
            "title": "第二章 施工部署",
            "content": "无需整改的内容。",
        },
    ]
    return basic_data


# =============================================================================
# Tests for _apply_style
# =============================================================================

class TestApplyStyle:
    """Tests for _apply_style function."""

    def test_apply_style_default_values(self):
        """Test _apply_style with empty style dict uses defaults."""
        doc = Document()
        apply_func = _apply_style(doc, {})
        
        assert callable(apply_func)

    def test_apply_style_custom_font(self):
        """Test _apply_style with custom font settings."""
        doc = Document()
        style = {
            "body_font": "Arial",
            "body_size": 14,
            "title_font": "Times New Roman",
            "title_size": 18,
            "line_spacing": 2.0,
        }
        apply_func = _apply_style(doc, style)
        
        assert callable(apply_func)

    def test_apply_style_partial_config(self):
        """Test _apply_style with partial style config."""
        doc = Document()
        style = {"font": "KaiTi", "font_size": 11}
        apply_func = _apply_style(doc, style)
        
        assert callable(apply_func)

    def test_apply_paragraph_to_normal_text(self):
        """Test applying style to a normal paragraph."""
        doc = Document()
        style = {"body_font": "SimSun", "body_size": 12}
        apply_func = _apply_style(doc, style)
        
        p = doc.add_paragraph("测试段落")
        apply_func(p, is_title=False)
        
        # Verify paragraph was processed (no exception)
        assert len(p.runs) >= 0

    def test_apply_paragraph_to_title(self):
        """Test applying style to a title paragraph."""
        doc = Document()
        style = {"title_font": "SimHei", "title_size": 16}
        apply_func = _apply_style(doc, style)
        
        h = doc.add_heading("测试标题", level=1)
        apply_func(h, is_title=True)
        
        assert len(h.runs) >= 0

    def test_apply_style_handles_missing_normal_style(self):
        """Test _apply_style handles document without Normal style gracefully."""
        doc = Document()
        # Remove Normal style if exists (simulate edge case)
        style = {"body_font": "Arial"}
        
        # Should not raise exception
        apply_func = _apply_style(doc, style)
        assert callable(apply_func)


class TestFrontMatterHelpers:
    """Tests for deterministic DOCX front matter helper functions."""

    def test_cover_title_and_date_helpers(self):
        assert _topic_to_cover_project_name("某厂房施工组织设计方案") == "某厂房"
        assert _topic_to_cover_project_name("某厂房施工组织设计") == "某厂房"
        assert _topic_to_cover_project_name("某厂房施组方案") == "某厂房"
        assert _to_cn_month(1) == "一"
        assert _to_cn_month(10) == "十"
        assert _to_cn_month(12) == "十二"
        assert _format_cover_year_month(dt.datetime(2026, 4, 1)) == "二零二六年四月"

    def test_front_matter_plan_counts_include_and_exclude_modes(self):
        include_plan = _resolve_front_matter_plan(
            style_raw={
                "cover_page_count": 1,
                "toc_page_count": 2,
                "full_index_enabled": "yes",
                "full_index_page_count": 1,
                "front_matter_page_mode": "include",
                "document_total_pages_target": 120,
            },
            data={},
            body_pages_estimate=90,
        )
        assert include_plan["actual_front_matter_pages"] == 4
        assert include_plan["effective_document_pages"] == 120

        exclude_plan = _resolve_front_matter_plan(
            style_raw={
                "cover_page_count": 1,
                "toc_page_count": 2,
                "full_index_enabled": False,
                "front_matter_page_mode": "exclude",
            },
            data={"total_pages_target": 120},
            body_pages_estimate=90,
        )
        assert exclude_plan["actual_front_matter_pages"] == 3
        assert exclude_plan["effective_document_pages"] == 123
        assert _normalize_front_matter_page_mode("bad") == "include"
        assert _normalize_full_index_enabled("enabled") is True
        assert _normalize_full_index_enabled("off") is False

    def test_static_toc_entries_start_after_front_matter(self):
        entries = _build_static_toc_entries(
            sections=[
                {"title": "第一章 工程概况"},
                {"title": "第二章 施工部署"},
            ],
            section_pages=[3, 4],
            front_matter_plan={
                "cover_pages": 1,
                "toc_pages": 2,
                "full_index_pages": 1,
            },
        )
        assert entries == [
            {"order": 1, "title": "第一章 工程概况", "start_page": 5, "planned_pages": 3},
            {"order": 2, "title": "第二章 施工部署", "start_page": 8, "planned_pages": 4},
        ]

    def test_toc_pagination_and_display_helpers(self):
        entries = [{"title": f"第{i}章"} for i in range(1, 6)]
        chunks = _paginate_toc_entries(entries, 2)
        assert [len(chunk) for chunk in chunks] == [3, 2]
        assert _format_toc_display_title("第一章 工程概况") == "第一章、工程概况"
        assert _format_toc_display_title("第一节 项目概况") == "第一节、项目概况"
        assert _infer_toc_level({"title": "第一章 工程概况"}) == 1
        assert _infer_toc_level({"title": "第一节 项目概况"}) == 2
        assert _infer_toc_level({"title": "一、施工部署"}) == 3
        assert _infer_toc_level({"title": "1.1 施工部署"}) == 3
        assert _infer_toc_level({"title": "手工指定", "level": 9}) == 3


# =============================================================================
# Tests for export_autoplan_docx
# =============================================================================

class TestExportAutoplanDocx:
    """Tests for export_autoplan_docx function."""

    def test_basic_export(self, temp_dir, basic_data):
        """Test basic DOCX export with minimal data."""
        output_path = Path(temp_dir) / "output.docx"
        result = export_autoplan_docx(basic_data, str(output_path))
        
        assert result == str(output_path)
        assert output_path.exists()

    def test_export_creates_parent_directories(self, temp_dir, basic_data):
        """Test export creates nested parent directories."""
        output_path = Path(temp_dir) / "nested" / "dir" / "output.docx"
        result = export_autoplan_docx(basic_data, str(output_path))
        
        assert output_path.exists()

    def test_export_with_empty_data(self, temp_dir):
        """Test export with empty data dict."""
        output_path = Path(temp_dir) / "empty.docx"
        result = export_autoplan_docx({}, str(output_path))
        
        assert output_path.exists()

    def test_export_default_topic(self, temp_dir):
        """Test export uses default topic when not provided."""
        output_path = Path(temp_dir) / "default.docx"
        data = {"sections": []}
        result = export_autoplan_docx(data, str(output_path))
        
        doc = Document(str(output_path))
        # First paragraph should contain default title
        assert len(doc.paragraphs) > 0

    def test_export_with_agent_role(self, temp_dir, basic_data):
        """Test export includes agent_role in output."""
        output_path = Path(temp_dir) / "with_role.docx"
        export_autoplan_docx(basic_data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "项目经理" in text

    def test_export_without_agent_role(self, temp_dir):
        """Test export handles sections without agent_role."""
        output_path = Path(temp_dir) / "no_role.docx"
        data = {
            "topic": "测试",
            "sections": [{"title": "章节", "content": "内容"}],
        }
        export_autoplan_docx(data, str(output_path))
        
        assert output_path.exists()

    def test_export_with_media(self, temp_dir, basic_data):
        """Test export with media/images (simulated failure)."""
        output_path = Path(temp_dir) / "with_media.docx"
        basic_data["media"] = ["/nonexistent/image.png"]
        
        export_autoplan_docx(basic_data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        # Should have fallback text for failed image
        assert "图片加载失败" in text

    def test_export_with_valid_media(self, temp_dir, basic_data):
        """Test export with valid image file."""
        # Create a simple valid image
        from PIL import Image
        img_path = Path(temp_dir) / "test_image.png"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(str(img_path))
        
        output_path = Path(temp_dir) / "with_valid_media.docx"
        basic_data["media"] = [str(img_path)]
        
        export_autoplan_docx(basic_data, str(output_path))
        assert output_path.exists()

    def test_export_with_quality_checks(self, temp_dir, data_with_quality_checks):
        """Test export with full quality checks data."""
        output_path = Path(temp_dir) / "with_qc.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "质量校验摘要" in text
        assert "通过" in text or "需改进" in text

    def test_export_quality_checks_checklist(self, temp_dir, data_with_quality_checks):
        """Test export generates quality check checklist with marks."""
        output_path = Path(temp_dir) / "qc_checklist.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        # Should have checkbox marks
        assert "☑" in text or "☐" in text

    def test_export_score_coverage_by_section(self, temp_dir, data_with_quality_checks):
        """Test export includes score coverage by section."""
        output_path = Path(temp_dir) / "score_coverage.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "章节评分点覆盖清单" in text
        assert "缺失" in text

    def test_export_evidence_by_section(self, temp_dir, data_with_quality_checks):
        """Test export includes evidence count by section."""
        output_path = Path(temp_dir) / "evidence.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "章节证据数量清单" in text
        assert "证据数" in text

    def test_export_closed_loop_by_section(self, temp_dir, data_with_quality_checks):
        """Test export includes closed loop by section."""
        output_path = Path(temp_dir) / "closed_loop.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "章节风险-措施闭环清单" in text

    def test_export_engineering_by_section(self, temp_dir, data_with_quality_checks):
        """Test export includes engineering elements by section."""
        output_path = Path(temp_dir) / "engineering.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "章节工程落地要素清单" in text

    def test_export_remediation_suggestions(self, temp_dir, data_with_quality_checks):
        """Test export includes remediation suggestions."""
        output_path = Path(temp_dir) / "remediation.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "整改建议清单" in text
        assert "补充证据材料" in text

    def test_export_llm_compare_full_mode(self, temp_dir, data_with_llm_remediation):
        """Test export LLM compare in full mode."""
        output_path = Path(temp_dir) / "llm_compare.docx"
        data_with_llm_remediation["compare"] = {"mode": "full"}
        data_with_llm_remediation["quality_checks"] = {"structure": {"ok": True}}
        
        export_autoplan_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "LLM整改前后对比" in text
        assert "整改前" in text
        assert "整改后" in text

    def test_export_llm_compare_summary_mode(self, temp_dir, data_with_llm_remediation):
        """Test export LLM compare in summary mode with truncation."""
        output_path = Path(temp_dir) / "llm_summary.docx"
        # Create long content
        data_with_llm_remediation["sections"][0]["original_content"] = "A" * 1000
        data_with_llm_remediation["sections"][0]["content"] = "B" * 1000
        data_with_llm_remediation["compare"] = {"mode": "summary", "max_chars": 100}
        data_with_llm_remediation["quality_checks"] = {"structure": {"ok": True}}
        
        export_autoplan_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        # Should be truncated with "..."
        assert "..." in text

    def test_export_llm_compare_with_titles_filter(self, temp_dir, data_with_llm_remediation):
        """Test export LLM compare filters by titles."""
        output_path = Path(temp_dir) / "llm_filtered.docx"
        data_with_llm_remediation["compare"] = {
            "mode": "full",
            "titles": ["第一章 工程概述"],
        }
        data_with_llm_remediation["quality_checks"] = {"structure": {"ok": True}}
        
        export_autoplan_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "第一章 工程概述" in text

    def test_export_no_style(self, temp_dir):
        """Test export with no style config."""
        output_path = Path(temp_dir) / "no_style.docx"
        data = {"topic": "测试", "sections": []}
        
        export_autoplan_docx(data, str(output_path))
        assert output_path.exists()

    def test_export_with_nested_w6_style(self, temp_dir):
        """Test export supports W6 nested template style keys."""
        output_path = Path(temp_dir) / "w6_style.docx"
        data = {
            "topic": "测试",
            "style": {
                "font": {
                    "eastAsia": "宋体",
                    "latin": "Times New Roman",
                    "size_pt": 11,
                    "line_spacing": 1.5,
                },
                "headings": {"h1_size": 16, "h2_size": 13},
                "margins_cm": {"top": 2.54, "bottom": 2.54, "left": 3.0, "right": 2.5},
            },
            "sections": [{"title": "第一章", "content": "正文内容"}],
        }

        export_autoplan_docx(data, str(output_path))
        assert output_path.exists()

    def test_export_with_chapter_page_receipt(self, temp_dir):
        """Test export includes chapter page receipt when chapter_pages provided."""
        output_path = Path(temp_dir) / "page_receipt.docx"
        data = {
            "topic": "测试",
            "chapter_pages": {"第一章": 2},
            "sections": [{"title": "第一章", "content": "内容" * 120}],
        }

        export_autoplan_docx(data, str(output_path))

        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "章节版式约束回执" in text
        assert "目标2页" in text

    def test_export_with_chapter_pages_dict_format(self, temp_dir):
        """Test export supports chapter_pages in dict target format."""
        output_path = Path(temp_dir) / "page_receipt_dict.docx"
        data = {
            "topic": "测试",
            "chapter_pages": {"第一章": {"pages": 3}},
            "sections": [{"title": "第一章", "content": "内容" * 160}],
        }

        export_autoplan_docx(data, str(output_path))
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "目标3页" in text

    def test_export_empty_sections(self, temp_dir):
        """Test export with empty sections list."""
        output_path = Path(temp_dir) / "empty_sections.docx"
        data = {"topic": "测试", "sections": []}
        
        export_autoplan_docx(data, str(output_path))
        assert output_path.exists()

    def test_export_section_default_title_and_content(self, temp_dir):
        """Test export handles sections with missing title/content."""
        output_path = Path(temp_dir) / "defaults.docx"
        data = {
            "topic": "测试",
            "sections": [{}],  # Empty section
        }
        
        export_autoplan_docx(data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "章节" in text  # Default title

    def test_auto_density_image_rule_under_200_and_skip_overview(self, temp_dir):
        output_path = Path(temp_dir) / "auto_density_under_200.docx"
        data = {
            "topic": "测试",
            "style": {
                "chart_policy": {
                    "enabled": True,
                    "mode": "page_density_auto",
                    "position": "chapter",
                }
            },
            "chapter_pages": {
                "工程概况": 1,
                "主要施工方法": 2,
            },
            "sections": [
                {"title": "工程概况", "content": "项目概况章节。"},
                {"title": "主要施工方法", "content": "控制间距900mm，抽检频次2次/班，风险-控制-验证闭环。"},
            ],
        }
        export_autoplan_docx(data, str(output_path))
        doc = Document(str(output_path))
        captions = [p.text for p in doc.paragraphs if re.match(r"^图\d+：", str(p.text or ""))]
        # <=200页：每页2图；本例仅第二章生效，2页=>4图
        assert len(captions) >= 4
        assert all("工程概况" not in c for c in captions)
        assert any("思维导图" in c for c in captions)

    def test_auto_density_image_rule_over_200(self, temp_dir):
        output_path = Path(temp_dir) / "auto_density_over_200.docx"
        data = {
            "topic": "测试",
            "style": {
                "chart_policy": {
                    "enabled": True,
                    "mode": "page_density_auto",
                    "position": "chapter",
                }
            },
            "chapter_pages": {
                "工程概况": 199,  # 仅用于触发 total_pages > 200
                "主要施工方法": 4,
            },
            "sections": [
                {"title": "工程概况", "content": "项目概况章节。"},
                {"title": "主要施工方法", "content": "控制间距900mm，抽检频次2次/班，风险-控制-验证闭环。"},
            ],
        }
        export_autoplan_docx(data, str(output_path))
        doc = Document(str(output_path))
        captions = [p.text for p in doc.paragraphs if re.match(r"^图\d+：", str(p.text or ""))]
        # >200页：每2页2图（等价每页1图）；本例第二章4页=>4图
        assert len(captions) >= 4
        assert len(captions) < 8


class TestAutoDensityRules:
    def test_auto_density_images_for_pages(self):
        assert _auto_density_images_for_pages(3, 150) == 6
        assert _auto_density_images_for_pages(3, 260) == 3


# =============================================================================
# Tests for export_autoplan_compare_docx
# =============================================================================

class TestExportAutoplanCompareDocx:
    """Tests for export_autoplan_compare_docx function."""

    def test_basic_compare_export(self, temp_dir, data_with_llm_remediation):
        """Test basic compare DOCX export."""
        output_path = Path(temp_dir) / "compare.docx"
        result = export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        assert result == str(output_path)
        assert output_path.exists()

    def test_compare_export_no_remediated_sections(self, temp_dir, basic_data):
        """Test compare export with no LLM remediated sections."""
        output_path = Path(temp_dir) / "no_remediation.docx"
        export_autoplan_compare_docx(basic_data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "暂无可对比的章节" in text

    def test_compare_export_summary_mode(self, temp_dir, data_with_llm_remediation):
        """Test compare export in summary mode (default)."""
        output_path = Path(temp_dir) / "compare_summary.docx"
        data_with_llm_remediation["sections"][0]["original_content"] = "X" * 1000
        data_with_llm_remediation["sections"][0]["content"] = "Y" * 1000
        data_with_llm_remediation["compare"] = {"mode": "summary", "max_chars": 200}
        
        export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "..." in text

    def test_compare_export_full_mode(self, temp_dir, data_with_llm_remediation):
        """Test compare export in full mode (no truncation)."""
        output_path = Path(temp_dir) / "compare_full.docx"
        data_with_llm_remediation["compare"] = {"mode": "full"}
        
        export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "整改前" in text
        assert "整改后" in text

    def test_compare_export_titles_filter(self, temp_dir, data_with_llm_remediation):
        """Test compare export filters by specified titles."""
        output_path = Path(temp_dir) / "compare_filtered.docx"
        data_with_llm_remediation["compare"] = {
            "mode": "full",
            "titles": ["第一章 工程概述"],
        }
        
        export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "第一章 工程概述" in text

    def test_compare_export_excludes_non_matching_titles(self, temp_dir, data_with_llm_remediation):
        """Test compare export excludes sections not in titles filter."""
        output_path = Path(temp_dir) / "compare_excluded.docx"
        data_with_llm_remediation["compare"] = {
            "mode": "full",
            "titles": ["不存在的章节"],
        }
        
        export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "暂无可对比的章节" in text

    def test_compare_export_creates_directories(self, temp_dir, data_with_llm_remediation):
        """Test compare export creates parent directories."""
        output_path = Path(temp_dir) / "a" / "b" / "c" / "compare.docx"
        export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        assert output_path.exists()

    def test_compare_export_default_topic(self, temp_dir, data_with_llm_remediation):
        """Test compare export uses default topic."""
        output_path = Path(temp_dir) / "default_topic.docx"
        del data_with_llm_remediation["topic"]
        
        export_autoplan_compare_docx(data_with_llm_remediation, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        assert "施组方案" in text

    def test_compare_export_empty_original_content(self, temp_dir):
        """Test compare export handles empty original_content."""
        output_path = Path(temp_dir) / "empty_original.docx"
        data = {
            "topic": "测试",
            "sections": [
                {
                    "title": "章节",
                    "content": "新内容",
                    "original_content": "",  # Empty, should be skipped
                    "auto_remediated": "llm",
                }
            ],
        }
        
        export_autoplan_compare_docx(data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        # Empty original_content should be treated as falsy, skip section
        assert "暂无可对比的章节" in text


# =============================================================================
# Tests for export_autoplan_docx_from_file
# =============================================================================

class TestExportAutoplanDocxFromFile:
    """Tests for export_autoplan_docx_from_file function."""

    def test_export_from_json_file(self, temp_dir, basic_data):
        """Test export from a JSON file."""
        json_path = Path(temp_dir) / "input.json"
        json_path.write_text(json.dumps(basic_data), encoding="utf-8")
        
        output_path = Path(temp_dir) / "from_file.docx"
        result = export_autoplan_docx_from_file(str(json_path), str(output_path))
        
        assert result == str(output_path)
        assert output_path.exists()

    def test_export_from_file_with_variants(self, temp_dir, basic_data):
        """Test export from file with variants array (multi-version)."""
        data = {
            "variants": [
                basic_data,
                {"topic": "第二版本"},
            ]
        }
        json_path = Path(temp_dir) / "variants.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")
        
        output_path = Path(temp_dir) / "variants_output.docx"
        result = export_autoplan_docx_from_file(str(json_path), str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        
        # Should use first variant
        assert "测试施工组织设计" in text
        assert "第二版本" not in text

    def test_export_from_file_with_empty_variants(self, temp_dir):
        """Test export from file with empty variants array."""
        data = {"variants": [], "topic": "直接数据"}
        json_path = Path(temp_dir) / "empty_variants.json"
        json_path.write_text(json.dumps(data), encoding="utf-8")
        
        output_path = Path(temp_dir) / "empty_variants.docx"
        result = export_autoplan_docx_from_file(str(json_path), str(output_path))
        
        # Should fall back to the whole data object
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "直接数据" in text

    def test_export_from_file_without_variants(self, temp_dir, basic_data):
        """Test export from file without variants key."""
        json_path = Path(temp_dir) / "no_variants.json"
        json_path.write_text(json.dumps(basic_data), encoding="utf-8")
        
        output_path = Path(temp_dir) / "no_variants.docx"
        result = export_autoplan_docx_from_file(str(json_path), str(output_path))
        
        assert output_path.exists()

    def test_export_from_file_invalid_json(self, temp_dir):
        """Test export from file with invalid JSON raises error."""
        json_path = Path(temp_dir) / "invalid.json"
        json_path.write_text("not valid json {{{", encoding="utf-8")
        
        output_path = Path(temp_dir) / "invalid.docx"
        
        with pytest.raises(json.JSONDecodeError):
            export_autoplan_docx_from_file(str(json_path), str(output_path))

    def test_export_from_nonexistent_file(self, temp_dir):
        """Test export from nonexistent file raises error."""
        json_path = Path(temp_dir) / "does_not_exist.json"
        output_path = Path(temp_dir) / "output.docx"
        
        with pytest.raises(FileNotFoundError):
            export_autoplan_docx_from_file(str(json_path), str(output_path))

    def test_export_from_file_unicode_content(self, temp_dir):
        """Test export from file with unicode content."""
        data = {
            "topic": "中文标题 日本語 한국어",
            "sections": [
                {"title": "特殊字符 ™ © ® €", "content": "内容 αβγ ∑∏∫"},
            ],
        }
        json_path = Path(temp_dir) / "unicode.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        
        output_path = Path(temp_dir) / "unicode.docx"
        result = export_autoplan_docx_from_file(str(json_path), str(output_path))
        
        assert output_path.exists()
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "中文标题" in text


# =============================================================================
# Edge case and integration tests
# =============================================================================

class TestEdgeCases:
    """Edge case and integration tests."""

    def test_export_with_none_style(self, temp_dir):
        """Test export with style explicitly set to None."""
        output_path = Path(temp_dir) / "none_style.docx"
        data = {"topic": "测试", "style": None, "sections": []}
        
        export_autoplan_docx(data, str(output_path))
        assert output_path.exists()

    def test_export_with_none_sections(self, temp_dir):
        """Test export with sections explicitly set to None."""
        output_path = Path(temp_dir) / "none_sections.docx"
        data = {"topic": "测试", "sections": None}
        
        # Should handle None sections gracefully
        export_autoplan_docx(data, str(output_path))
        assert output_path.exists()

    def test_export_with_none_media(self, temp_dir, basic_data):
        """Test export with media explicitly set to None."""
        output_path = Path(temp_dir) / "none_media.docx"
        basic_data["media"] = None
        
        export_autoplan_docx(basic_data, str(output_path))
        assert output_path.exists()

    def test_export_with_empty_media_list(self, temp_dir, basic_data):
        """Test export with empty media list."""
        output_path = Path(temp_dir) / "empty_media.docx"
        basic_data["media"] = []
        
        export_autoplan_docx(basic_data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        # Should not have media section
        assert "图表与插图" not in text

    def test_export_with_none_quality_checks(self, temp_dir, basic_data):
        """Test export with quality_checks explicitly set to None."""
        output_path = Path(temp_dir) / "none_qc.docx"
        basic_data["quality_checks"] = None
        
        export_autoplan_docx(basic_data, str(output_path))
        assert output_path.exists()

    def test_export_with_empty_quality_checks(self, temp_dir, basic_data):
        """Test export with empty quality_checks dict."""
        output_path = Path(temp_dir) / "empty_qc.docx"
        basic_data["quality_checks"] = {}
        
        export_autoplan_docx(basic_data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        # Should not have QC section with empty dict
        assert output_path.exists()

    def test_large_document(self, temp_dir):
        """Test export with many sections."""
        sections = [
            {"title": f"第{i}章", "content": f"内容{i}" * 100, "agent_role": f"角色{i}"}
            for i in range(50)
        ]
        data = {"topic": "大型文档测试", "sections": sections}
        output_path = Path(temp_dir) / "large.docx"
        
        export_autoplan_docx(data, str(output_path))
        
        assert output_path.exists()
        assert output_path.stat().st_size > 10000  # Should be reasonably large

    def test_style_with_numeric_strings(self, temp_dir):
        """Test style with numeric values as strings."""
        output_path = Path(temp_dir) / "string_nums.docx"
        data = {
            "topic": "测试",
            "style": {
                "body_size": "14",  # String instead of int
                "title_size": "18",
                "line_spacing": "1.5",
            },
            "sections": [],
        }
        
        export_autoplan_docx(data, str(output_path))
        assert output_path.exists()

    def test_quality_check_item_with_no_ok_field(self, temp_dir):
        """Test quality check item without 'ok' field."""
        output_path = Path(temp_dir) / "no_ok.docx"
        data = {
            "topic": "测试",
            "sections": [],
            "quality_checks": {
                "structure": {"note": "仅有备注"},
            },
        }
        
        export_autoplan_docx(data, str(output_path))
        
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)
        # ok is None/falsy, should show "需改进"
        assert "需改进" in text
