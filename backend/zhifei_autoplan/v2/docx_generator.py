from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from backend.zhifei_autoplan.terminology_guard import load_global_terminology, normalize_text_terminology


def _setup_doc_style(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.8)
    section.right_margin = Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.name = "宋体"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def _is_auto_generated_section(section: Dict[str, Any]) -> bool:
    if not isinstance(section, dict):
        return False
    if bool(section.get("auto_generated_support")):
        return True
    graph_hit = section.get("graph_hit")
    if not isinstance(graph_hit, dict):
        return False
    source_path = str(graph_hit.get("source_path") or "").lower()
    if "self_healing_patch_nodes" in source_path:
        return True
    snippet = str(graph_hit.get("snippet") or "").lower()
    return "is_auto_generated" in snippet


def _render_section_paragraph(
    doc: Document,
    *,
    text: str,
    highlight: bool,
) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(str(text or "").strip() or "（无内容）")
    if highlight:
        # Visual guardrail: mark sentences backed by self-healing auto-generated KG nodes.
        run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def _resource_items(resource_requirements: Any) -> List[str]:
    if not isinstance(resource_requirements, dict):
        return []
    out: List[str] = []
    for key, value in resource_requirements.items():
        out.append(f"{key}: {value}")
    return out


def _render_visual_assets(doc: Document, visual_assets: List[Dict[str, Any]]) -> Dict[str, int]:
    if not visual_assets:
        return {"embedded": 0, "missing": 0}
    embedded = 0
    missing = 0
    doc.add_page_break()
    doc.add_heading("附图与视觉生成", level=1)
    for asset in visual_assets:
        title = str(asset.get("title") or "自动生成图").strip()
        caption = str(asset.get("caption") or "").strip()
        image_path = str(asset.get("image_path") or "").strip()
        doc.add_paragraph(title)
        p = Path(image_path)
        if p.exists():
            doc.add_picture(str(p), width=Cm(15.5))
            embedded += 1
        else:
            doc.add_paragraph(f"图像缺失: {image_path or 'unknown'}")
            missing += 1
        if caption:
            doc.add_paragraph(caption)
    return {"embedded": embedded, "missing": missing}


def generate_v2_docx(
    *,
    index_matrix: Dict[str, Any],
    sections: List[Dict[str, Any]],
    visual_assets: List[Dict[str, Any]] | None = None,
    output_path: Path | str,
    title_hint: str = "施工组织设计草案",
) -> Dict[str, Any]:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    _setup_doc_style(doc)

    title = str(index_matrix.get("project_name") or title_hint or "施工组织设计草案").strip()
    h = doc.add_heading(title, level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph(
        f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} | "
        "标黄内容=AI自动补全参数(需人工复核)"
    )
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    section_by_title: Dict[str, Dict[str, Any]] = {}
    terminology_entries = load_global_terminology()
    for sec in sections:
        key = str(sec.get("title") or "").strip()
        if key and key not in section_by_title:
            section_by_title[key] = sec

    highlighted_paragraphs = 0
    auto_generated_sections = 0

    for idx, item in enumerate(index_matrix.get("index_matrix") or [], start=1):
        dimension = str(item.get("dimension") or f"章节{idx}").strip()
        keywords = "、".join([str(x) for x in (item.get("keywords") or [])[:10]])

        doc.add_heading(f"{idx}. {dimension}", level=1)
        doc.add_paragraph(f"响应关键词: {keywords}")

        sec = section_by_title.get(dimension) or {}
        highlight = _is_auto_generated_section(sec)
        if highlight:
            auto_generated_sections += 1

        content = str(sec.get("content") or "").strip()
        try:
            content, _ = normalize_text_terminology(content, terminology_entries)
        except Exception:
            pass
        _render_section_paragraph(doc, text=content or "该章节暂无可用内容。", highlight=highlight)
        if highlight:
            highlighted_paragraphs += 1

        graph_hit = sec.get("graph_hit") if isinstance(sec.get("graph_hit"), dict) else {}
        evidence_title = str(graph_hit.get("title") or "未命中")
        evidence_file = str(graph_hit.get("source_file") or "")
        evidence_para = doc.add_paragraph()
        evidence_run = evidence_para.add_run(f"证据节点: {evidence_title}  来源文件: {evidence_file}")
        if highlight:
            evidence_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            highlighted_paragraphs += 1

        resources = _resource_items(graph_hit.get("resource_requirements"))
        if resources:
            doc.add_paragraph("参数清单:")
            for line in resources[:12]:
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(line)
                if highlight:
                    run.font.highlight_color = WD_COLOR_INDEX.YELLOW
                    highlighted_paragraphs += 1

        if highlight:
            warning = doc.add_paragraph()
            warning_run = warning.add_run("AI审校信标: 本章节包含自愈引擎自动补全参数，请重点人工复核。")
            warning_run.bold = True
            warning_run.font.highlight_color = WD_COLOR_INDEX.YELLOW
            highlighted_paragraphs += 1

    visuals_meta = _render_visual_assets(doc, list(visual_assets or []))
    doc.save(str(out))
    return {
        "ok": True,
        "saved_at": str(out),
        "highlighted_paragraphs": highlighted_paragraphs,
        "auto_generated_sections": auto_generated_sections,
        "visual_assets_embedded": int(visuals_meta["embedded"]),
        "visual_assets_missing": int(visuals_meta["missing"]),
    }
