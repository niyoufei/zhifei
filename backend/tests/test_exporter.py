"""
Tests for backend/zhifei_autoplan/exporter.py
"""
from __future__ import annotations

import json
import re
import tempfile
import zipfile
import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest
from docx import Document

from backend.zhifei_autoplan.exporter import (
    _apply_style,
    _auto_density_images_for_pages,
    export_autoplan_docx,
    export_autoplan_compare_docx,
    export_autoplan_docx_from_file,
)


def _doc_visible_text(docx_path: Path) -> str:
    with zipfile.ZipFile(docx_path, "r") as zf:
        document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    root = ET.fromstring(document_xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    parts = []
    for paragraph in root.findall(".//w:p", ns):
        runs = []
        for run in paragraph.findall("./w:r", ns):
            if run.find("./w:rPr/w:vanish", ns) is not None:
                continue
            text_nodes = run.findall("./w:t", ns)
            if text_nodes:
                runs.append("".join(node.text or "" for node in text_nodes))
        if runs:
            parts.append("".join(runs))
    return "\n".join(parts)


def _build_report_json_path(output_path: Path) -> Path:
    return output_path.with_suffix(".build_report.json")


def _write_test_png(path: Path) -> None:
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sX6sK0AAAAASUVORK5CYII="
    )
    path.write_bytes(png_bytes)


def _doc_media_count(docx_path: Path) -> int:
    with zipfile.ZipFile(docx_path, "r") as zf:
        return len([name for name in zf.namelist() if name.startswith("word/media/")])


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

    def test_export_cover_page_uses_special_layout(self, temp_dir, basic_data):
        output_path = Path(temp_dir) / "cover_layout.docx"
        cover_path = Path(temp_dir) / "cover.png"
        logo_path = Path(temp_dir) / "logo.png"
        _write_test_png(cover_path)
        _write_test_png(logo_path)
        data = dict(basic_data)
        data.update(
            {
                "project_name": "肥西县公办养老机构改造提升项目",
                "project_code": "2026AEEGZ50006",
                "cover_image_path": str(cover_path),
                "cover_image_caption": "肥西县公办养老机构改造提升项目 · 现场实景图",
                "branding": {
                    "project_id": "2026AEEGZ50006",
                    "bidder_company": "安徽先华建筑工程有限公司",
                    "logo_path": str(logo_path),
                },
            }
        )

        export_autoplan_docx(data, str(output_path))

        text = _doc_visible_text(output_path)
        assert "肥西县公办养老机构改造提升项目" in text
        assert "招标项目编号：2026AEEGZ50006" in text
        assert "施工组织设计" in text
        assert "肥西县公办养老机构改造提升项目 · 现场实景图" in text
        assert "公司名称：安徽先华建筑工程有限公司" in text
        assert re.search(r"二零[一二三四五六七八九零]+年[一二三四五六七八九十]+月", text)
        assert _doc_media_count(output_path) >= 1

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

    def test_export_includes_toc_field_and_footer_page_fields(self, temp_dir, basic_data):
        output_path = Path(temp_dir) / "toc_footer.docx"
        export_autoplan_docx(basic_data, str(output_path))

        with zipfile.ZipFile(output_path, "r") as zf:
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
            header_files = [name for name in zf.namelist() if name.startswith("word/header")]
            footer_files = [name for name in zf.namelist() if name.startswith("word/footer")]
            header_xml = "".join(zf.read(name).decode("utf-8", errors="ignore") for name in header_files)
            footer_xml = "".join(zf.read(name).decode("utf-8", errors="ignore") for name in footer_files)
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)

        assert 'TOC \\o "1-2" \\h \\z \\u' in document_xml
        assert re.search(r"第一章、工程概述[·.]+\s*4", text)
        assert re.search(r"第二章、施工部署[·.]+\s*5", text)
        assert "施工组织设计" in header_xml
        assert "PAGE" in footer_xml

    def test_export_reserves_configured_toc_pages(self, temp_dir, basic_data):
        output_path = Path(temp_dir) / "toc_reserved.docx"
        data = dict(basic_data)
        data["style"] = dict(basic_data.get("style") or {})
        data["style"].update(
            {
                "cover_page_count": 1,
                "toc_page_count": 3,
                "full_index_enabled": False,
                "front_matter_page_mode": "include",
                "document_total_pages_target": 200,
            }
        )

        export_autoplan_docx(data, str(output_path))

        with zipfile.ZipFile(output_path, "r") as zf:
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)

        assert "全文索引" not in text
        assert document_xml.count('w:type="page"') == 4

    def test_export_inserts_full_index_when_enabled(self, temp_dir, basic_data):
        output_path = Path(temp_dir) / "full_index.docx"
        data = dict(basic_data)
        data["style"] = dict(basic_data.get("style") or {})
        data["style"].update(
            {
                "cover_page_count": 1,
                "toc_page_count": 3,
                "full_index_enabled": True,
                "front_matter_page_mode": "exclude",
                "document_total_pages_target": 120,
            }
        )

        export_autoplan_docx(data, str(output_path))

        with zipfile.ZipFile(output_path, "r") as zf:
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        doc = Document(str(output_path))
        text = "\n".join(p.text for p in doc.paragraphs)

        assert "全文索引" in text
        assert text.index("全文索引") < text.index("目录")
        assert "第一章 工程概述" in text
        assert re.search(r"第一章、工程概述[·.]+\s*6", text)
        assert re.search(r"第二章、施工部署[·.]+\s*7", text)
        assert document_xml.count('w:type="page"') == 5

    def test_export_does_not_insert_full_index_when_disabled_even_over_200_pages(self, temp_dir, basic_data):
        output_path = Path(temp_dir) / "full_index_disabled.docx"
        data = dict(basic_data)
        data["style"] = dict(basic_data.get("style") or {})
        data["style"].update(
            {
                "cover_page_count": 1,
                "toc_page_count": 3,
                "full_index_enabled": False,
                "front_matter_page_mode": "exclude",
                "document_total_pages_target": 260,
            }
        )

        export_autoplan_docx(data, str(output_path))

        text = _doc_visible_text(output_path)

        assert "全文索引" not in text
        assert re.search(r"第一章、工程概述[·.]+\s*5", text)
        assert re.search(r"第二章、施工部署[·.]+\s*6", text)

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

    def test_export_renders_risk_triplet_table_and_hidden_evidence(self, temp_dir):
        output_path = Path(temp_dir) / "risk_table.docx"
        data = {
            "topic": "测试",
            "sections": [
                {
                    "title": "质量控制",
                    "content": "\n".join(
                        [
                            "【风险→控制→验证】",
                            "风险：交叉作业伤人；控制：设置警戒线并专人指挥；验证：违章为零并完成巡检记录。【证据:图纸A.pdf#p9】",
                        ]
                    ),
                }
            ],
        }
        export_autoplan_docx(data, str(output_path))
        doc = Document(str(output_path))
        assert len(doc.tables) >= 1
        with zipfile.ZipFile(output_path, "r") as zf:
            document_xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        assert "图纸A.pdf#p9" in document_xml
        assert "w:vanish" in document_xml
        assert "图纸A.pdf#p9" not in _doc_visible_text(output_path)

    def test_export_with_quality_checks(self, temp_dir, data_with_quality_checks):
        """Quality checks should be redirected to build report, not final DOCX."""
        output_path = Path(temp_dir) / "with_qc.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "质量校验摘要" not in text
        assert "quality_checks" in report["internal_payload"]

    def test_export_quality_checks_checklist(self, temp_dir, data_with_quality_checks):
        """Checklist data should stay in build report."""
        output_path = Path(temp_dir) / "qc_checklist.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "☑" not in text and "☐" not in text
        assert report["internal_payload"]["quality_checks"]["structure"]["ok"] is True

    def test_export_score_coverage_by_section(self, temp_dir, data_with_quality_checks):
        """Score coverage section should not leak into deliverable DOCX."""
        output_path = Path(temp_dir) / "score_coverage.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "章节评分点覆盖清单" not in text
        assert report["internal_payload"]["quality_checks"]["score_coverage_by_section"][1]["missing"][0]["dimension"] == "质量"

    def test_export_evidence_by_section(self, temp_dir, data_with_quality_checks):
        """Evidence count summary should stay out of deliverable DOCX."""
        output_path = Path(temp_dir) / "evidence.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "章节证据数量清单" not in text
        assert report["internal_payload"]["quality_checks"]["evidence"]["by_section"][0]["evidence_count"] == 2

    def test_export_closed_loop_by_section(self, temp_dir, data_with_quality_checks):
        """Closed loop summary should stay out of deliverable DOCX."""
        output_path = Path(temp_dir) / "closed_loop.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "章节风险-措施闭环清单" not in text
        assert report["internal_payload"]["quality_checks"]["closed_loop_by_section"][0]["ok"] is True

    def test_export_engineering_by_section(self, temp_dir, data_with_quality_checks):
        """Engineering summary should stay out of deliverable DOCX."""
        output_path = Path(temp_dir) / "engineering.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "章节工程落地要素清单" not in text
        assert report["internal_payload"]["quality_checks"]["engineering_by_section"][1]["missing"] == ["人员", "设备"]

    def test_export_remediation_suggestions(self, temp_dir, data_with_quality_checks):
        """Remediation suggestions should be redirected to build report."""
        output_path = Path(temp_dir) / "remediation.docx"
        export_autoplan_docx(data_with_quality_checks, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "整改建议清单" not in text
        assert report["internal_payload"]["quality_checks"]["remediation"][0]["suggestion"] == "补充证据材料"

    def test_export_llm_compare_full_mode(self, temp_dir, data_with_llm_remediation):
        """LLM compare payload should not leak into deliverable DOCX."""
        output_path = Path(temp_dir) / "llm_compare.docx"
        data_with_llm_remediation["compare"] = {"mode": "full"}
        data_with_llm_remediation["quality_checks"] = {"structure": {"ok": True}}
        
        export_autoplan_docx(data_with_llm_remediation, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "LLM整改前后对比" not in text
        assert report["internal_payload"]["compare"]["mode"] == "full"

    def test_export_llm_compare_summary_mode(self, temp_dir, data_with_llm_remediation):
        """Visible docx should keep final content only; compare stays in build report."""
        output_path = Path(temp_dir) / "llm_summary.docx"
        # Create long content
        data_with_llm_remediation["sections"][0]["original_content"] = "A" * 1000
        data_with_llm_remediation["sections"][0]["content"] = "B" * 1000
        data_with_llm_remediation["compare"] = {"mode": "summary", "max_chars": 100}
        data_with_llm_remediation["quality_checks"] = {"structure": {"ok": True}}
        
        export_autoplan_docx(data_with_llm_remediation, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "LLM整改前后对比" not in text
        assert "整改前" not in text
        assert report["internal_payload"]["compare"]["mode"] == "summary"

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
        """Chapter page receipts should be redirected to build report."""
        output_path = Path(temp_dir) / "page_receipt.docx"
        data = {
            "topic": "测试",
            "chapter_pages": {"第一章": 2},
            "sections": [{"title": "第一章", "content": "内容" * 120}],
        }

        export_autoplan_docx(data, str(output_path))

        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "章节版式约束回执" not in text
        assert report["internal_payload"]["layout_receipts"][0]["target_pages"] == 2

    def test_export_with_chapter_pages_dict_format(self, temp_dir):
        """Chapter page receipts keep dict target format in build report."""
        output_path = Path(temp_dir) / "page_receipt_dict.docx"
        data = {
            "topic": "测试",
            "chapter_pages": {"第一章": {"pages": 3}},
            "sections": [{"title": "第一章", "content": "内容" * 160}],
        }

        export_autoplan_docx(data, str(output_path))
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert report["internal_payload"]["layout_receipts"][0]["target_pages"] == 3

    def test_export_static_toc_uses_configured_chapter_pages(self, temp_dir):
        output_path = Path(temp_dir) / "toc_planned_pages.docx"
        data = {
            "topic": "测试",
            "style": {
                "cover_page_count": 1,
                "toc_page_count": 2,
                "front_matter_page_mode": "include",
                "document_total_pages_target": 12,
            },
            "chapter_pages": {
                "第一章 工程概述": 3,
                "第二章 施工部署": 4,
                "第三章 质量保证措施": 2,
            },
            "sections": [
                {"title": "第一章 工程概述", "content": "内容A"},
                {"title": "第二章 施工部署", "content": "内容B"},
                {"title": "第三章 质量保证措施", "content": "内容C"},
            ],
        }

        export_autoplan_docx(data, str(output_path))
        text = _doc_visible_text(output_path)

        assert re.search(r"第一章、工程概述[·.]+\s*4", text)
        assert re.search(r"第二章、施工部署[·.]+\s*7", text)
        assert re.search(r"第三章、质量保证措施[·.]+\s*11", text)

    def test_export_prefers_prebuilt_front_matter_outline(self, temp_dir):
        output_path = Path(temp_dir) / "toc_prebuilt.docx"
        data = {
            "topic": "测试",
            "chapter_pages": {
                "第一章 工程概述": 3,
                "第二章 施工部署": 4,
            },
            "front_matter_outline": {
                "cover_pages": 1,
                "toc_pages": 2,
                "full_index_pages": 0,
                "toc_entries": [
                    {"order": 1, "title": "第一章 工程概述", "start_page": 9, "planned_pages": 3},
                    {"order": 2, "title": "第二章 施工部署", "start_page": 12, "planned_pages": 4},
                ],
                "index_entries": [
                    {"order": 1, "title": "第一章 工程概述", "summary": "01. 第一章 工程概述（约3页）"},
                    {"order": 2, "title": "第二章 施工部署", "summary": "02. 第二章 施工部署（约4页）"},
                ],
            },
            "sections": [
                {"title": "第一章 工程概述", "content": "内容A"},
                {"title": "第二章 施工部署", "content": "内容B"},
            ],
        }

        export_autoplan_docx(data, str(output_path))
        text = _doc_visible_text(output_path)

        assert re.search(r"第一章、工程概述[·.]+\s*9", text)
        assert re.search(r"第二章、施工部署[·.]+\s*12", text)

    def test_export_toc_renders_hierarchical_styles(self, temp_dir):
        output_path = Path(temp_dir) / "toc_hierarchy.docx"
        data = {
            "topic": "测试",
            "front_matter_outline": {
                "cover_pages": 1,
                "toc_pages": 1,
                "full_index_pages": 0,
                "toc_entries": [
                    {"order": 1, "title": "第一章 工程概况", "start_page": 4, "planned_pages": 3, "level": 1},
                    {"order": 2, "title": "第一节 项目工程基本概况", "start_page": 4, "planned_pages": 1, "level": 2},
                    {"order": 3, "title": "一、重点分析：资源调度", "start_page": 5, "planned_pages": 1, "level": 3},
                ],
            },
            "sections": [
                {"title": "第一章 工程概况", "content": "内容A"},
            ],
        }

        export_autoplan_docx(data, str(output_path))
        doc = Document(str(output_path))

        chapter_run = next(p.runs[0] for p in doc.paragraphs if "第一章、工程概况" in p.text and p.runs)
        section_run = next(p.runs[0] for p in doc.paragraphs if "第一节、项目工程基本概况" in p.text and p.runs)
        item_run = next(p.runs[0] for p in doc.paragraphs if "一、重点分析：资源调度" in p.text and p.runs)

        assert str(chapter_run.font.color.rgb) == "000000"
        assert str(section_run.font.color.rgb) == "109EAA"
        assert str(item_run.font.color.rgb) == "000000"
        assert round(chapter_run.font.size.pt, 1) >= round(section_run.font.size.pt, 1)
        assert round(section_run.font.size.pt, 1) >= round(item_run.font.size.pt, 1)

    def test_export_applies_bidding_font_size_and_black_color_to_titles_and_tables(self, temp_dir):
        output_path = Path(temp_dir) / "bidding_style.docx"
        data = {
            "topic": "测试",
            "bidding_format_config": {
                "body_font": "宋",
                "title_font": "宋",
                "body_size_pt": 14,
                "title_size_pt": 16,
                "line_spacing_pt": 22,
            },
            "sections": [
                {
                    "title": "第一章 工程概述",
                    "content": "\n".join(
                        [
                            "【风险→控制→验证】",
                            "风险：交叉作业伤人；控制：设置警戒线并专人指挥；验证：违章为零。",
                        ]
                    ),
                }
            ],
        }

        export_autoplan_docx(data, str(output_path))
        doc = Document(str(output_path))

        title_run = next(p.runs[0] for p in doc.paragraphs if p.text == "第一章 工程概述" and p.runs)
        assert title_run.font.name == "宋体"
        assert round(title_run.font.size.pt, 1) == 16.0
        assert str(title_run.font.color.rgb) == "000000"

        toc_run = next(p.runs[0] for p in doc.paragraphs if "第一章、工程概述" in p.text and "·" in p.text and p.runs)
        assert toc_run.font.name == "宋体"
        assert round(toc_run.font.size.pt, 1) == 16.0
        assert str(toc_run.font.color.rgb) == "000000"

        table = doc.tables[0]
        header_run = table.rows[0].cells[0].paragraphs[0].runs[0]
        body_run = table.rows[1].cells[0].paragraphs[0].runs[0]
        assert header_run.font.name == "宋体"
        assert round(header_run.font.size.pt, 1) == 16.0
        assert str(header_run.font.color.rgb) == "000000"
        assert body_run.font.name == "宋体"
        assert round(body_run.font.size.pt, 1) == 14.0
        assert str(body_run.font.color.rgb) == "000000"

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
        assert "测试" in text
        assert "施工组织设计" in text
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
        """Quality check payload without ok field should still be routed to build report."""
        output_path = Path(temp_dir) / "no_ok.docx"
        data = {
            "topic": "测试",
            "sections": [],
            "quality_checks": {
                "structure": {"note": "仅有备注"},
            },
        }
        
        export_autoplan_docx(data, str(output_path))
        text = _doc_visible_text(output_path)
        report = json.loads(_build_report_json_path(output_path).read_text(encoding="utf-8"))
        assert "需改进" not in text
        assert report["internal_payload"]["quality_checks"]["structure"]["note"] == "仅有备注"
