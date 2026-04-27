from __future__ import annotations

import datetime as _dt
import json
import math
import re
from pathlib import Path
from typing import Dict, Any, List

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.shared import Cm
from docx.shared import Pt
from docx.shared import RGBColor
from docx.oxml.ns import qn
from backend.zhifei_autoplan.media import generate_section_visuals
from backend.zhifei_autoplan.terminology_guard import load_global_terminology, normalize_text_terminology


_AUTOFIX_MARK_RE = re.compile(r"【自动补充】(?P<name>[^\n]{1,80}?)(?:：|:)")
_OVERVIEW_SECTION_RE = re.compile(r"(工程概况|项目概况)")
_TOC_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百零0-9]+章")
_TOC_SECTION_RE = re.compile(r"^第[一二三四五六七八九十百零0-9]+节")
_TOC_CN_ITEM_RE = re.compile(r"^[一二三四五六七八九十百零]+[、.]")
_TOC_NUMERIC_ITEM_RE = re.compile(r"^\d+(?:\.\d+){1,3}")
_CN_DIGITS = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
_GENERIC_COVER_IMAGE_STEMS = {
    "",
    "image",
    "img",
    "photo",
    "picture",
    "cover",
    "wechat image",
    "微信图片",
    "现场照片",
    "现场图",
    "现状",
}


def _strip_internal_autofix_markers(text: str) -> str:
    """
    Internal remediation markers are useful for idempotency, but should not appear
    in the final DOCX deliverable.
    Keep the heading content, only remove the "自动补充" prefix.
    """
    s = str(text or "")
    s = _AUTOFIX_MARK_RE.sub(lambda m: f"【{m.group('name').strip()}】", s)
    s = s.replace("【自动补充】", "")
    return s


def _to_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _to_int(v: Any, default: int) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _to_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _merge_style(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base or {})
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            item = dict(merged.get(k) or {})
            item.update(v)
            merged[k] = item
        else:
            merged[k] = v
    return merged


def _resolve_alignment(v: Any):
    if not isinstance(v, str):
        return None
    key = v.strip().lower()
    mapping = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping.get(key)


def _normalize_style(style: Dict[str, Any]) -> Dict[str, Any]:
    style = style if isinstance(style, dict) else {}
    font_cfg = style.get("font") if isinstance(style.get("font"), dict) else {}
    headings_cfg = style.get("headings") if isinstance(style.get("headings"), dict) else {}
    margins_cfg = style.get("margins_cm") if isinstance(style.get("margins_cm"), dict) else {}

    body_font = (
        style.get("body_font")
        or (style.get("font") if isinstance(style.get("font"), str) else None)
        or font_cfg.get("eastAsia")
        or "宋体"
    )
    body_latin_font = style.get("body_latin_font") or font_cfg.get("latin") or body_font
    body_size = _to_float(
        style.get("body_size") or style.get("font_size") or font_cfg.get("size_pt") or 14,
        14.0,
    )
    line_spacing = _to_float(style.get("line_spacing") or font_cfg.get("line_spacing") or 1.5, 1.5)
    line_spacing_pt = style.get("line_spacing_pt") or font_cfg.get("line_spacing_pt") or 22.0
    try:
        line_spacing_pt = float(line_spacing_pt) if line_spacing_pt is not None else None
    except Exception:
        line_spacing_pt = None
    if line_spacing_pt is not None and line_spacing_pt <= 0:
        line_spacing_pt = 22.0

    title_font = style.get("title_font") or headings_cfg.get("eastAsia") or body_font
    title_latin_font = style.get("title_latin_font") or headings_cfg.get("latin") or body_latin_font
    title_size = _to_float(style.get("title_size") or headings_cfg.get("h2_size") or max(body_size + 2, 14), 14.0)
    doc_title_size = _to_float(
        style.get("doc_title_size") or headings_cfg.get("h1_size") or max(title_size + 2, 16),
        16.0,
    )

    margins_list = style.get("margins") if isinstance(style.get("margins"), list) else []
    top = _to_float(margins_cfg.get("top"), _to_float(margins_list[0] if len(margins_list) > 0 else 2.5, 2.5))
    right = _to_float(margins_cfg.get("right"), _to_float(margins_list[1] if len(margins_list) > 1 else 2.0, 2.0))
    bottom = _to_float(margins_cfg.get("bottom"), _to_float(margins_list[2] if len(margins_list) > 2 else 2.0, 2.0))
    left = _to_float(margins_cfg.get("left"), _to_float(margins_list[3] if len(margins_list) > 3 else 2.0, 2.0))

    return {
        "paper": str(style.get("paper") or style.get("paper_size") or "A4"),
        "body_font": body_font,
        "body_latin_font": body_latin_font,
        "body_size": max(8.0, min(22.0, body_size)),
        "title_font": title_font,
        "title_latin_font": title_latin_font,
        "title_size": max(10.0, min(28.0, title_size)),
        "doc_title_size": max(12.0, min(36.0, doc_title_size)),
        "line_spacing": max(1.0, min(2.5, line_spacing)),
        "line_spacing_pt": line_spacing_pt,
        "first_line_indent_cm": max(0.0, _to_float(style.get("first_line_indent_cm"), 0.0)),
        "body_align": _resolve_alignment(style.get("body_align")),
        "title_align": _resolve_alignment(style.get("title_align")),
        "margins_cm": {
            "top": max(0.5, top),
            "right": max(0.5, right),
            "bottom": max(0.5, bottom),
            "left": max(0.5, left),
        },
        "chapter_start_new_page": _to_bool(style.get("chapter_start_new_page"), False),
        "enforce_chapter_pages": _to_bool(style.get("enforce_chapter_pages"), False),
    }


def _apply_page_setup(doc: Document, style_cfg: Dict[str, Any]):
    paper = str(style_cfg.get("paper") or "A4").upper()
    margins = style_cfg.get("margins_cm") or {}
    for section in doc.sections:
        if paper == "A4":
            section.page_width = Cm(21.0)
            section.page_height = Cm(29.7)
        section.top_margin = Cm(_to_float(margins.get("top"), 2.5))
        section.right_margin = Cm(_to_float(margins.get("right"), 2.0))
        section.bottom_margin = Cm(_to_float(margins.get("bottom"), 2.0))
        section.left_margin = Cm(_to_float(margins.get("left"), 2.0))


def _set_run_font(run, east_font: str, latin_font: str, size_pt: float):
    run.font.name = latin_font or east_font
    run.font.size = Pt(size_pt)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    if east_font:
        rfonts.set(qn("w:eastAsia"), east_font)
    if latin_font:
        rfonts.set(qn("w:ascii"), latin_font)
        rfonts.set(qn("w:hAnsi"), latin_font)


def _topic_to_cover_project_name(topic: Any) -> str:
    raw = str(topic or "").strip()
    if not raw:
        return ""
    for suffix in ("施工组织设计方案", "施工组织设计", "施组方案"):
        if raw.endswith(suffix):
            return raw[: -len(suffix)].strip()
    return raw


def _to_cn_month(month: int) -> str:
    month = max(1, min(12, int(month or 1)))
    if month < 10:
        return _CN_DIGITS[str(month)]
    if month == 10:
        return "十"
    return "十" + _CN_DIGITS[str(month % 10)]


def _format_cover_year_month(dt: _dt.datetime | None = None) -> str:
    current = dt or _dt.datetime.now()
    year_cn = "".join(_CN_DIGITS.get(ch, ch) for ch in f"{int(current.year):04d}")
    return f"{year_cn}年{_to_cn_month(int(current.month))}月"


def _normalize_front_matter_page_mode(value: Any) -> str:
    return "exclude" if str(value or "").strip().lower() == "exclude" else "include"


def _normalize_full_index_enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enable", "enabled"}


def _resolve_front_matter_plan(
    *,
    style_raw: Dict[str, Any],
    data: Dict[str, Any],
    body_pages_estimate: int,
) -> Dict[str, Any]:
    style = style_raw if isinstance(style_raw, dict) else {}
    payload = data if isinstance(data, dict) else {}
    cover_pages = max(1, _to_int(style.get("cover_page_count"), 1))
    toc_pages = max(1, _to_int(style.get("toc_page_count"), 1))
    configured_index_pages = max(1, _to_int(style.get("full_index_page_count"), 1))
    full_index_enabled = _normalize_full_index_enabled(style.get("full_index_enabled"))
    count_mode = _normalize_front_matter_page_mode(style.get("front_matter_page_mode"))
    document_total_target = max(
        1,
        _to_int(style.get("document_total_pages_target"), 0)
        or _to_int(payload.get("total_pages_target"), 0)
        or int(body_pages_estimate or 1),
    )
    full_index_pages = configured_index_pages if full_index_enabled else 0
    actual_front_matter_pages = cover_pages + toc_pages + full_index_pages
    effective_document_pages = (
        document_total_target
        if count_mode == "include"
        else document_total_target + actual_front_matter_pages
    )
    return {
        "cover_pages": cover_pages,
        "toc_pages": toc_pages,
        "configured_index_pages": configured_index_pages,
        "full_index_enabled": full_index_enabled,
        "count_mode": count_mode,
        "full_index_pages": full_index_pages,
        "actual_front_matter_pages": actual_front_matter_pages,
        "document_total_target": document_total_target,
        "effective_document_pages": effective_document_pages,
    }


def _insert_full_index_page(
    doc: Document,
    apply_paragraph,
    *,
    topic: str,
    sections: List[Dict[str, Any]],
    chapter_pages: Dict[str, Any] | None,
    effective_document_pages: int,
    index_entries: List[Dict[str, Any]] | None = None,
) -> None:
    heading = doc.add_heading("全文索引", level=1)
    apply_paragraph(heading, is_title=True)
    intro = doc.add_paragraph(
        f"{str(topic or '施工组织设计').strip()}；"
        f"章节数={len(sections or [])}；"
        f"成品预计总页数={max(1, int(effective_document_pages or 1))}页。"
    )
    apply_paragraph(intro)

    normalized_entries = [item for item in (index_entries or []) if isinstance(item, dict)]
    if normalized_entries:
        for idx, item in enumerate(normalized_entries, start=1):
            title = str(item.get("title") or f"章节{idx}").strip() or f"章节{idx}"
            summary = str(item.get("summary") or "").strip()
            planned_pages = _to_int(item.get("planned_pages"), 0)
            line = summary or f"{idx:02d}. {title}"
            if planned_pages and "约" not in line:
                line += f"（约{int(planned_pages)}页）"
            paragraph = doc.add_paragraph(line)
            apply_paragraph(paragraph)
        doc.add_page_break()
        return

    if not sections:
        note = doc.add_paragraph("当前无可索引章节。")
        apply_paragraph(note)
        doc.add_page_break()
        return

    for idx, section in enumerate(sections or [], start=1):
        title = str((section or {}).get("title") or f"章节{idx}").strip() or f"章节{idx}"
        planned_pages = _extract_chapter_page_target(chapter_pages or {}, title)
        line = f"{idx:02d}. {title}"
        if planned_pages:
            line += f"（约{int(planned_pages)}页）"
        paragraph = doc.add_paragraph(line)
        apply_paragraph(paragraph)
    doc.add_page_break()


def _build_static_toc_entries(
    *,
    sections: List[Dict[str, Any]],
    section_pages: List[int],
    front_matter_plan: Dict[str, Any],
) -> List[Dict[str, Any]]:
    plan = front_matter_plan if isinstance(front_matter_plan, dict) else {}
    cover_pages = max(1, _to_int(plan.get("cover_pages"), 1))
    toc_pages = max(1, _to_int(plan.get("toc_pages"), 1))
    full_index_pages = max(0, _to_int(plan.get("full_index_pages"), 0))
    current_page = cover_pages + full_index_pages + toc_pages + 1
    entries: List[Dict[str, Any]] = []
    for idx, sec in enumerate(sections or []):
        title = str((sec or {}).get("title") or f"章节{idx + 1}").strip() or f"章节{idx + 1}"
        planned_pages = max(1, _to_int(section_pages[idx] if idx < len(section_pages) else 1, 1))
        entries.append(
            {
                "order": idx + 1,
                "title": title,
                "start_page": current_page,
                "planned_pages": planned_pages,
            }
        )
        current_page += planned_pages
    return entries


def _paginate_toc_entries(entries: List[Dict[str, Any]], toc_pages: int) -> List[List[Dict[str, Any]]]:
    page_count = max(1, int(toc_pages or 1))
    chunks: List[List[Dict[str, Any]]] = []
    cursor = 0
    total = len(entries or [])
    for page_idx in range(page_count):
        remaining_pages = page_count - page_idx
        remaining_entries = total - cursor
        if remaining_entries <= 0:
            chunks.append([])
            continue
        take = max(1, math.ceil(remaining_entries / max(1, remaining_pages)))
        chunks.append((entries or [])[cursor: cursor + take])
        cursor += take
    return chunks


def _infer_toc_level(entry: Dict[str, Any]) -> int:
    raw = _to_int(entry.get("level"), 0) if isinstance(entry, dict) else 0
    if raw > 0:
        return min(3, raw)
    title = re.sub(r"\s+", " ", str((entry or {}).get("title") or "").strip())
    if _TOC_CHAPTER_RE.match(title):
        return 1
    if _TOC_SECTION_RE.match(title):
        return 2
    if _TOC_CN_ITEM_RE.match(title) or _TOC_NUMERIC_ITEM_RE.match(title):
        return 3
    return 1


def _format_toc_display_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "").strip())
    for pattern in (_TOC_CHAPTER_RE, _TOC_SECTION_RE):
        match = pattern.match(cleaned)
        if match:
            prefix = match.group(0)
            suffix = cleaned[len(prefix):].strip(" 、.")
            return f"{prefix}、{suffix}" if suffix else prefix
    return cleaned


def _append_field_run(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    r = run._r
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = str(instruction or "")
    fld_separate = OxmlElement("w:fldChar")
    fld_separate.set(qn("w:fldCharType"), "separate")
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r.append(fld_begin)
    r.append(instr)
    r.append(fld_separate)
    r.append(fld_end)


def _hide_paragraph(paragraph) -> None:
    if not getattr(paragraph, "runs", None):
        paragraph.add_run()
    for run in paragraph.runs:
        try:
            rpr = run._element.get_or_add_rPr()
            if rpr.find(qn("w:vanish")) is None:
                rpr.append(OxmlElement("w:vanish"))
        except Exception:
            continue


def _toc_entry_style(style_cfg: Dict[str, Any], level: int) -> Dict[str, Any]:
    style = style_cfg if isinstance(style_cfg, dict) else {}
    body_font = str(style.get("body_font") or "宋体")
    body_latin = str(style.get("body_latin_font") or body_font)
    title_font = str(style.get("title_font") or body_font)
    title_latin = str(style.get("title_latin_font") or body_latin)
    body_size = _to_float(style.get("body_size"), 14.0)
    title_size = _to_float(style.get("title_size"), body_size + 2.0)
    if level <= 1:
        return {
            "font_east": title_font,
            "font_latin": title_latin,
            "size_pt": max(title_size, body_size + 2.0),
            "bold": True,
            "left_indent_cm": 0.0,
            "color_rgb": (0, 0, 0),
        }
    if level == 2:
        return {
            "font_east": body_font,
            "font_latin": body_latin,
            "size_pt": max(body_size + 1.0, 14.5),
            "bold": False,
            "left_indent_cm": 1.0,
            "color_rgb": (16, 158, 170),
        }
    return {
        "font_east": body_font,
        "font_latin": body_latin,
        "size_pt": max(body_size, 13.5),
        "bold": False,
        "left_indent_cm": 2.0,
        "color_rgb": (0, 0, 0),
    }


def _render_toc_line(
    doc: Document,
    entry: Dict[str, Any],
    *,
    style_cfg: Dict[str, Any],
):
    level = _infer_toc_level(entry)
    line_cfg = _toc_entry_style(style_cfg, level)
    title = _format_toc_display_title(str((entry or {}).get("title") or "章节"))
    page_number = int(_to_int((entry or {}).get("start_page"), 1) or 1)
    dot_count = max(10, 52 - len(title) - max(0, level - 1) * 4)
    paragraph = doc.add_paragraph()
    try:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.left_indent = Cm(float(line_cfg["left_indent_cm"]))
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(4 if level == 1 else 2)
        paragraph.paragraph_format.line_spacing = Pt(22)
    except Exception:
        pass
    run = paragraph.add_run(f"{title}{'·' * dot_count}{page_number}")
    _set_run_font(run, str(line_cfg["font_east"]), str(line_cfg["font_latin"]), float(line_cfg["size_pt"]))
    try:
        run.bold = bool(line_cfg["bold"])
        color = tuple(line_cfg.get("color_rgb") or (0, 0, 0))
        run.font.color.rgb = RGBColor(int(color[0]), int(color[1]), int(color[2]))
    except Exception:
        pass
    return paragraph


def _insert_auto_toc(
    doc: Document,
    apply_paragraph,
    *,
    style_cfg: Dict[str, Any],
    toc_pages: int = 1,
    toc_entries: List[Dict[str, Any]] | None = None,
) -> None:
    page_chunks = _paginate_toc_entries(toc_entries or [], max(1, int(toc_pages or 1)))
    style = style_cfg if isinstance(style_cfg, dict) else {}
    title_font = str(style.get("title_font") or "宋体")
    title_latin = str(style.get("title_latin_font") or style.get("body_latin_font") or title_font)
    title_size = max(_to_float(style.get("doc_title_size"), 18.0), 18.0)
    for page_idx, page_entries in enumerate(page_chunks):
        heading = doc.add_paragraph()
        try:
            heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
            heading.paragraph_format.first_line_indent = Cm(0)
            heading.paragraph_format.space_before = Pt(6)
            heading.paragraph_format.space_after = Pt(10)
            heading.paragraph_format.line_spacing = Pt(24)
        except Exception:
            pass
        title_run = heading.add_run("目录" if page_idx == 0 else "目录（续）")
        _set_run_font(title_run, title_font, title_latin, title_size)
        try:
            title_run.bold = True
            title_run.font.color.rgb = RGBColor(16, 158, 170)
        except Exception:
            pass

        field_paragraph = doc.add_paragraph()
        _append_field_run(field_paragraph, 'TOC \\o "1-2" \\h \\z \\u')
        apply_paragraph(field_paragraph)
        _hide_paragraph(field_paragraph)
        try:
            field_paragraph.paragraph_format.first_line_indent = Cm(0)
        except Exception:
            pass

        if page_entries:
            for entry in page_entries:
                _render_toc_line(doc, entry, style_cfg=style)
        elif page_idx == 0:
            empty = doc.add_paragraph("当前无章节目录。")
            apply_paragraph(empty)
            try:
                empty.paragraph_format.first_line_indent = Cm(0)
                empty.paragraph_format.left_indent = Cm(0)
            except Exception:
                pass
        doc.add_page_break()


def _usable_page_width_cm(doc: Document) -> float:
    try:
        section = doc.sections[-1]
        width_emu = int(section.page_width) - int(section.left_margin) - int(section.right_margin)
        return max(8.0, float(width_emu) / 360000.0)
    except Exception:
        return 17.0


def _clear_block_container(container) -> None:
    try:
        for paragraph in list(container.paragraphs):
            element = paragraph._element
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
    except Exception:
        pass
    try:
        for table in list(container.tables):
            element = table._element
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
    except Exception:
        pass


def _set_cell_width(cell, width_cm: float) -> None:
    try:
        cell.width = Cm(float(width_cm))
    except Exception:
        pass
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_w = tc_pr.first_child_found_in("w:tcW")
        if tc_w is None:
            tc_w = OxmlElement("w:tcW")
            tc_pr.append(tc_w)
        tc_w.set(qn("w:w"), str(int(float(width_cm) * 567)))
        tc_w.set(qn("w:type"), "dxa")
    except Exception:
        pass


def _set_cell_shading(cell, fill: str) -> None:
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
        for child in list(tc_pr):
            if child.tag == qn("w:shd"):
                tc_pr.remove(child)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), str(fill or "").strip() or "FFFFFF")
        tc_pr.append(shd)
    except Exception:
        pass


def _set_cell_border(cell, **kwargs) -> None:
    try:
        tc_pr = cell._tc.get_or_add_tcPr()
        tc_borders = tc_pr.first_child_found_in("w:tcBorders")
        if tc_borders is None:
            tc_borders = OxmlElement("w:tcBorders")
            tc_pr.append(tc_borders)
        for edge, cfg in kwargs.items():
            edge_el = tc_borders.find(qn(f"w:{edge}"))
            if edge_el is None:
                edge_el = OxmlElement(f"w:{edge}")
                tc_borders.append(edge_el)
            edge_el.set(qn("w:val"), str(cfg.get("val", "single")))
            edge_el.set(qn("w:sz"), str(cfg.get("sz", 6)))
            edge_el.set(qn("w:space"), str(cfg.get("space", 0)))
            edge_el.set(qn("w:color"), str(cfg.get("color", "D9EAF0")))
    except Exception:
        pass


def _set_table_all_borders(table, *, color: str, sz: int = 6, top: bool = False, bottom: bool = False) -> None:
    for row in table.rows:
        for cell in row.cells:
            edges: Dict[str, Dict[str, Any]] = {}
            if top:
                edges["top"] = {"color": color, "sz": sz}
            if bottom:
                edges["bottom"] = {"color": color, "sz": sz}
            if edges:
                _set_cell_border(cell, **edges)


def _apply_footer_page_numbers(
    doc: Document,
    style_cfg: Dict[str, Any],
    *,
    bidder_company: str,
    logo_path: str | None,
) -> None:
    font_east = str((style_cfg or {}).get("body_font") or "宋体")
    font_latin = str((style_cfg or {}).get("body_latin_font") or font_east)
    company = str(bidder_company or "").strip()
    logo = str(logo_path or "").strip()
    if logo and not Path(logo).exists():
        logo = ""
    usable_width = _usable_page_width_cm(doc)
    for section in doc.sections:
        try:
            section.different_first_page_header_footer = True
        except Exception:
            pass
        try:
            footer = section.footer
            footer.is_linked_to_previous = False
        except Exception:
            continue
        _clear_block_container(footer)
        table = footer.add_table(rows=1, cols=2, width=Cm(usable_width))
        try:
            table.autofit = False
        except Exception:
            pass
        _set_table_all_borders(table, color="14A6AE", sz=10, top=True)
        left_cell = table.cell(0, 0)
        right_cell = table.cell(0, 1)
        _set_cell_width(left_cell, usable_width * 0.72)
        _set_cell_width(right_cell, usable_width * 0.28)
        try:
            left_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            right_cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        except Exception:
            pass
        p_left = left_cell.paragraphs[0] if left_cell.paragraphs else left_cell.add_paragraph()
        p_right = right_cell.paragraphs[0] if right_cell.paragraphs else right_cell.add_paragraph()
        try:
            p_left.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p_right.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p_left.paragraph_format.space_before = Pt(4)
            p_left.paragraph_format.space_after = Pt(0)
            p_right.paragraph_format.space_before = Pt(4)
            p_right.paragraph_format.space_after = Pt(0)
        except Exception:
            pass
        if logo:
            try:
                p_left.add_run().add_picture(logo, width=Cm(1.0))
            except Exception:
                pass
        if company:
            run_company = p_left.add_run(f" {company}" if logo else company)
            _set_run_font(run_company, font_east, font_latin, 12.0)
            try:
                run_company.bold = True
            except Exception:
                pass
        _append_field_run(p_right, "PAGE")
        for run in p_right.runs:
            _set_run_font(run, font_east, font_latin, 14.0)


def _style_cover_paragraph(
    paragraph,
    *,
    east_font: str,
    latin_font: str,
    size_pt: float,
    text: Any = "",
    bold: bool = False,
    color_rgb: tuple[int, int, int] | None = None,
    space_before_pt: float = 0.0,
    space_after_pt: float = 0.0,
    line_spacing_pt: float | None = None,
):
    try:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.space_before = Pt(float(space_before_pt or 0))
        paragraph.paragraph_format.space_after = Pt(float(space_after_pt or 0))
        if line_spacing_pt is not None:
            paragraph.paragraph_format.line_spacing = Pt(float(line_spacing_pt))
    except Exception:
        pass
    run = paragraph.add_run(str(text or ""))
    _set_run_font(run, str(east_font or "宋体"), str(latin_font or east_font or "宋体"), float(size_pt or 12))
    try:
        run.bold = bool(bold)
        if color_rgb is not None:
            run.font.color.rgb = RGBColor(int(color_rgb[0]), int(color_rgb[1]), int(color_rgb[2]))
    except Exception:
        pass
    return run


def _cover_image_caption(project_name: Any, filename: Any, source_hint: Any = "") -> str:
    name = str(project_name or "").strip()
    source = str(source_hint or "").strip().lower()
    stem = Path(str(filename or "")).stem.strip()
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    stem = re.sub(r"(?:\(|（)\d+(?:\)|）)$", "", stem).strip()
    stem = re.sub(r"^微信图片\s*\d{6,}$", "微信图片", stem).strip()
    stem_key = stem.lower()

    if stem and stem_key not in _GENERIC_COVER_IMAGE_STEMS:
        label = stem
    elif source in {"site_photo", "site", "scene", "现场", "现场照片"}:
        label = "现场实景图"
    else:
        label = "项目效果图"
    return f"{name} · {label}" if name else label


def _resolve_cover_meta(data: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = data if isinstance(data, dict) else {}
    branding = raw.get("branding") if isinstance(raw.get("branding"), dict) else {}
    topic = str(raw.get("topic") or "施工组织设计").strip() or "施工组织设计"
    project_name = str(raw.get("project_name") or "").strip() or _topic_to_cover_project_name(topic)
    project_code = str(raw.get("project_code") or "").strip()
    bidder_company = str(branding.get("bidder_company") or raw.get("bidder_company") or "").strip()

    logo_path = str(branding.get("logo_path") or raw.get("logo_path") or "").strip()
    if logo_path and not Path(logo_path).exists():
        logo_path = ""
    cover_image_path = str(raw.get("cover_image_path") or branding.get("cover_image_path") or "").strip()
    if cover_image_path and not Path(cover_image_path).exists():
        cover_image_path = ""

    cover_image_caption = str(raw.get("cover_image_caption") or branding.get("cover_image_caption") or "").strip()
    if cover_image_path and not cover_image_caption:
        cover_image_caption = _cover_image_caption(project_name, Path(cover_image_path).name, "site_photo")

    return {
        "project_id": str(raw.get("project_id") or branding.get("project_id") or "").strip(),
        "project_name": project_name,
        "project_code": project_code,
        "topic": topic,
        "cover_title": str(raw.get("cover_title") or "施工组织设计").strip() or "施工组织设计",
        "cover_image_path": cover_image_path,
        "cover_image_caption": cover_image_caption,
        "bidder_company": bidder_company,
        "logo_path": logo_path,
        "issue_year_month": str(raw.get("issue_year_month") or branding.get("issue_year_month") or "").strip()
        or _format_cover_year_month(),
    }


def _insert_cover_page(doc: Document, style_cfg: Dict[str, Any], cover_meta: Dict[str, Any] | None) -> None:
    cfg = _normalize_style(style_cfg or {})
    meta = cover_meta if isinstance(cover_meta, dict) else {}
    title_font = str(cfg.get("title_font") or "黑体")
    title_latin = str(cfg.get("title_latin_font") or cfg.get("body_latin_font") or title_font)
    body_font = str(cfg.get("body_font") or "宋体")
    body_latin = str(cfg.get("body_latin_font") or body_font)
    accent = (16, 158, 170)

    project_name = str(meta.get("project_name") or "").strip()
    project_code = str(meta.get("project_code") or "").strip()
    cover_title = str(meta.get("cover_title") or "施工组织设计").strip() or "施工组织设计"
    bidder_company = str(meta.get("bidder_company") or "").strip()
    issue_year_month = str(meta.get("issue_year_month") or "").strip()

    if project_name:
        _style_cover_paragraph(
            doc.add_paragraph(),
            east_font=title_font,
            latin_font=title_latin,
            size_pt=max(float(cfg.get("doc_title_size") or 20), 20.0),
            text=project_name,
            bold=True,
            color_rgb=accent,
            space_before_pt=42,
            space_after_pt=10,
            line_spacing_pt=30,
        )
    if project_code:
        _style_cover_paragraph(
            doc.add_paragraph(),
            east_font=body_font,
            latin_font=body_latin,
            size_pt=12,
            text=f"项目编号：{project_code}",
            space_after_pt=18,
        )
    _style_cover_paragraph(
        doc.add_paragraph(),
        east_font=title_font,
        latin_font=title_latin,
        size_pt=28,
        text=cover_title,
        bold=True,
        space_before_pt=18,
        space_after_pt=24,
        line_spacing_pt=36,
    )

    cover_image_path = str(meta.get("cover_image_path") or "").strip()
    if cover_image_path and Path(cover_image_path).exists():
        try:
            doc.add_picture(cover_image_path, width=Cm(12))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass
    cover_image_caption = str(meta.get("cover_image_caption") or "").strip()
    if cover_image_caption:
        _style_cover_paragraph(
            doc.add_paragraph(),
            east_font=body_font,
            latin_font=body_latin,
            size_pt=10.5,
            text=cover_image_caption,
            color_rgb=(90, 98, 102),
            space_before_pt=4,
            space_after_pt=20,
        )

    logo_path = str(meta.get("logo_path") or "").strip()
    if logo_path and Path(logo_path).exists():
        try:
            doc.add_picture(logo_path, width=Cm(2.4))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass
    if bidder_company:
        _style_cover_paragraph(
            doc.add_paragraph(),
            east_font=body_font,
            latin_font=body_latin,
            size_pt=14,
            text=bidder_company,
            bold=True,
            space_before_pt=18,
            space_after_pt=8,
        )
    if issue_year_month:
        _style_cover_paragraph(
            doc.add_paragraph(),
            east_font=body_font,
            latin_font=body_latin,
            size_pt=12,
            text=issue_year_month,
            space_after_pt=12,
        )
    doc.add_page_break()


def _apply_style(doc: Document, style: Dict[str, Any]):
    cfg = _normalize_style(style)
    try:
        st = doc.styles["Normal"]
        st.font.name = cfg["body_latin_font"] or cfg["body_font"]
        st.font.size = Pt(cfg["body_size"])
        if cfg.get("line_spacing_pt") is not None:
            st.paragraph_format.line_spacing = Pt(cfg["line_spacing_pt"])
        else:
            st.paragraph_format.line_spacing = cfg["line_spacing"]
    except Exception:
        pass

    def apply_paragraph(p, is_title: bool = False):
        font_east = cfg["title_font"] if is_title else cfg["body_font"]
        font_latin = cfg["title_latin_font"] if is_title else cfg["body_latin_font"]
        size = cfg["title_size"] if is_title else cfg["body_size"]
        try:
            if cfg.get("line_spacing_pt") is not None:
                p.paragraph_format.line_spacing = Pt(cfg["line_spacing_pt"])
            else:
                p.paragraph_format.line_spacing = cfg["line_spacing"]
            if not is_title and cfg["first_line_indent_cm"] > 0:
                p.paragraph_format.first_line_indent = Cm(cfg["first_line_indent_cm"])
            align = cfg["title_align"] if is_title else cfg["body_align"]
            if align is not None:
                p.paragraph_format.alignment = align
        except Exception:
            pass
        for r in p.runs:
            _set_run_font(r, font_east, font_latin, size)

    return apply_paragraph


def _apply_branding_header(doc: Document, style_cfg: Dict[str, Any], *, topic: str, bidder_company: str, logo_path: str | None):
    """
    Best-effort brand output:
    - Put company name (and logo if available) into page header.
    This is intentionally lightweight: it should not affect tender-driven chapter structure.
    """
    company = str(bidder_company or "").strip()
    logo = str(logo_path or "").strip()
    if logo and not Path(logo).exists():
        logo = ""
    if not company and not logo:
        return

    font_east = str(style_cfg.get("body_font") or "宋体")
    font_latin = str(style_cfg.get("body_latin_font") or font_east)
    size_pt = 9.0

    for sec in doc.sections:
        try:
            header = sec.header
        except Exception:
            continue
        try:
            # Avoid duplicate branding if caller exports multiple times into same doc instance.
            if getattr(header, "_zf_branding", False):
                continue
            setattr(header, "_zf_branding", True)
        except Exception:
            pass

        try:
            table = header.add_table(rows=1, cols=2)
            try:
                table.autofit = True
            except Exception:
                pass
            cell_logo = table.cell(0, 0)
            cell_text = table.cell(0, 1)

            # Logo (left)
            if logo:
                p0 = cell_logo.paragraphs[0] if cell_logo.paragraphs else cell_logo.add_paragraph()
                try:
                    p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
                except Exception:
                    pass
                try:
                    r0 = p0.add_run()
                    r0.add_picture(logo, width=Cm(2.0))
                except Exception:
                    pass

            # Text (right)
            p1 = cell_text.paragraphs[0] if cell_text.paragraphs else cell_text.add_paragraph()
            try:
                p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            except Exception:
                pass
            header_text = company or ""
            if header_text and topic:
                header_text = f"{header_text} | {topic}"
            elif topic:
                header_text = str(topic)
            if header_text:
                r1 = p1.add_run(header_text)
                try:
                    _set_run_font(r1, font_east, font_latin, size_pt)
                except Exception:
                    pass
        except Exception:
            continue


def _extract_chapter_page_target(chapter_pages: Dict[str, Any], title: str) -> int | None:
    if not isinstance(chapter_pages, dict):
        return None
    raw = chapter_pages.get(title)
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = (
            raw.get("target")
            or raw.get("pages")
            or raw.get("page_target")
            or raw.get("count")
        )
    target = _to_int(raw, 0)
    return target if target > 0 else None


def _estimate_chars_per_page(style_cfg: Dict[str, Any]) -> int:
    body_size = _to_float(style_cfg.get("body_size"), 14.0)
    line_spacing = _to_float(style_cfg.get("line_spacing"), 1.5)
    line_spacing_pt = style_cfg.get("line_spacing_pt")
    if line_spacing_pt is not None:
        try:
            line_spacing = max(1.0, min(3.0, float(line_spacing_pt) / max(8.0, body_size)))
        except Exception:
            pass
    margins = style_cfg.get("margins_cm") or {}
    left = _to_float(margins.get("left"), 2.0)
    right = _to_float(margins.get("right"), 2.0)
    top = _to_float(margins.get("top"), 2.5)
    bottom = _to_float(margins.get("bottom"), 2.0)

    width_factor = 5.5 / max(2.0, left + right)
    height_factor = 5.0 / max(2.0, top + bottom)
    margin_factor = max(0.75, min(1.25, (width_factor + height_factor) / 2.0))
    est = int(900 * (12.0 / max(8.0, body_size)) * (1.5 / max(1.0, line_spacing)) * margin_factor)
    return max(350, min(1800, est))


def _estimate_content_pages(content: str, chars_per_page: int) -> int:
    text = (content or "").replace("\n", "")
    if not text:
        return 1
    return max(1, math.ceil(len(text) / max(1, chars_per_page)))


def _is_overview_section(title: str) -> bool:
    return bool(_OVERVIEW_SECTION_RE.search(str(title or "").strip()))


def _auto_density_images_for_pages(chapter_pages: int, total_pages: int) -> int:
    """
    Auto image density policy:
    - total <= 200: 2 images per page
    - total > 200: 2 images per 2 pages (i.e. 1 image per page)
    """
    cp = max(0, int(chapter_pages or 0))
    tp = max(0, int(total_pages or 0))
    if cp <= 0:
        return 0
    if tp <= 200:
        return cp * 2
    return cp


def export_autoplan_docx(data: Dict[str, Any], output_path: str) -> str:
    style_raw = data.get("style") or {}
    style_cfg = _normalize_style(style_raw)
    chapter_pages = data.get("chapter_pages") or {}
    chapter_styles = style_raw.get("chapter_styles") if isinstance(style_raw, dict) else {}

    doc = Document()
    _apply_page_setup(doc, style_cfg)
    apply_paragraph = _apply_style(doc, style_raw)

    topic = data.get("topic") or "施组方案"
    cover_meta = _resolve_cover_meta(data)
    bidder_company = str(cover_meta.get("bidder_company") or "").strip()
    logo_path = cover_meta.get("logo_path")

    def _brand_image_with_logo(src_path: str) -> str:
        """
        Add a small logo corner mark to an image (best-effort) to unify brand output.
        Returns the branded image path or the original path when branding is not possible.
        """
        try:
            if not isinstance(logo_path, str) or not logo_path.strip():
                return src_path
            if not src_path or str(src_path) == str(logo_path):
                return src_path
            sp = Path(str(src_path))
            lp = Path(str(logo_path))
            if not sp.exists() or not sp.is_file() or not lp.exists() or not lp.is_file():
                return src_path

            # Create a stable output name next to the source image (avoid touching originals).
            out = sp.with_name(f"{sp.stem}_brand.png")
            if out.exists() and out.is_file():
                return str(out)

            from PIL import Image

            with Image.open(sp) as base_im:
                base = base_im.convert("RGBA")
                with Image.open(lp) as logo_im:
                    logo = logo_im.convert("RGBA")
                    # Scale logo: up to 12% width, capped.
                    max_w = min(220, max(80, int(base.width * 0.12)))
                    if logo.width > max_w:
                        hh = int(logo.height * (max_w / max(1, logo.width)))
                        logo = logo.resize((max_w, max(1, hh)))
                    margin = max(12, int(base.width * 0.015))
                    x0 = max(0, base.width - logo.width - margin)
                    y0 = max(0, margin)
                    base.alpha_composite(logo, (x0, y0))
                # Save as PNG for docx compatibility.
                base.convert("RGB").save(out, format="PNG")
            return str(out)
        except Exception:
            return src_path

    layout_receipts = []
    sections = data.get("sections") or []
    terminology_entries = load_global_terminology()
    media_all = data.get("media") or []
    chart_policy = style_raw.get("chart_policy") if isinstance(style_raw, dict) and isinstance(style_raw.get("chart_policy"), dict) else {}
    chart_enabled = _to_bool(chart_policy.get("enabled"), True)
    chart_mode = str(chart_policy.get("mode") or "").strip().lower()
    chart_position = str(chart_policy.get("position") or "end").strip().lower()  # end|chapter
    chart_every_n = max(1, _to_int(chart_policy.get("every_n_chapters"), 2))
    chart_mode_auto_density = chart_mode in {"page_density_auto", "page_density", "auto_density"}
    if not chart_enabled:
        chart_mode_auto_density = False

    # Planned total pages are used for automatic image density policy.
    def _effective_pages_for_section(title: str, content_doc: str, section_style_cfg: Dict[str, Any]) -> int:
        t = _extract_chapter_page_target(chapter_pages, title)
        if t:
            return int(t)
        chars_per_page = _estimate_chars_per_page(section_style_cfg)
        return _estimate_content_pages(content_doc, chars_per_page)

    total_planned_pages = 0
    section_pages: List[int] = []
    for sec in sections:
        title = str(sec.get("title") or "章节")
        content = _strip_internal_autofix_markers(sec.get("content") or "")
        pages = _effective_pages_for_section(title, content, style_cfg)
        section_pages.append(pages)
        total_planned_pages += pages
    total_planned_pages = max(1, int(total_planned_pages))

    front_matter_plan = _resolve_front_matter_plan(
        style_raw=style_raw,
        data=data,
        body_pages_estimate=total_planned_pages,
    )
    _apply_branding_header(doc, style_cfg, topic=str(topic), bidder_company=bidder_company, logo_path=logo_path)
    _apply_footer_page_numbers(
        doc,
        style_cfg,
        bidder_company=bidder_company,
        logo_path=str(logo_path or ""),
    )
    _insert_cover_page(doc, style_cfg, cover_meta)
    if int(front_matter_plan.get("full_index_pages") or 0) > 0:
        _insert_full_index_page(
            doc,
            apply_paragraph,
            topic=str(topic),
            sections=sections,
            chapter_pages=chapter_pages,
            effective_document_pages=int(front_matter_plan.get("effective_document_pages") or total_planned_pages),
        )
    _insert_auto_toc(
        doc,
        apply_paragraph,
        style_cfg=style_cfg,
        toc_pages=int(front_matter_plan.get("toc_pages") or 1),
        toc_entries=_build_static_toc_entries(
            sections=sections,
            section_pages=section_pages,
            front_matter_plan=front_matter_plan,
        ),
    )

    media_cursor = 0
    media_index = 0
    chapter_media_started = False

    def _append_media_item(item: Any):
        nonlocal media_index
        path = item.get("path") if isinstance(item, dict) else item
        caption = item.get("caption") if isinstance(item, dict) else None
        try:
            branded_path = _brand_image_with_logo(str(path))
            path_to_add = branded_path or str(path)
            doc.add_picture(str(path_to_add), width=Cm(14))
            try:
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception:
                pass
            media_index += 1
            if not caption:
                try:
                    name = Path(str(path)).name
                except Exception:
                    name = str(path)
                if "boq_stats_" in str(name):
                    caption = "BoQ 统计概览"
                else:
                    caption = name
            pc = doc.add_paragraph(f"图{media_index}：{caption}")
            apply_paragraph(pc)
            try:
                pc.alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception:
                pass
        except Exception:
            pe = doc.add_paragraph(f"图片加载失败：{path}")
            apply_paragraph(pe)

    # 目录/章节内容
    for idx, sec in enumerate(sections):
        title = sec.get("title") or "章节"
        content = sec.get("content") or ""
        content_doc = _strip_internal_autofix_markers(content)
        try:
            content_doc, _ = normalize_text_terminology(content_doc, terminology_entries)
        except Exception:
            pass
        role = sec.get("agent_role")

        apply_this = apply_paragraph
        section_style_cfg = style_cfg
        if isinstance(chapter_styles, dict) and isinstance(chapter_styles.get(title), dict):
            merged_style = _merge_style(style_raw, chapter_styles.get(title) or {})
            apply_this = _apply_style(doc, merged_style)
            section_style_cfg = _normalize_style(merged_style)

        if idx > 0 and style_cfg.get("chapter_start_new_page"):
            doc.add_page_break()

        h2 = doc.add_heading(title, level=2)
        apply_this(h2, is_title=True)
        if role:
            p = doc.add_paragraph(f"负责人：{role}")
            apply_this(p)
        p = doc.add_paragraph(content_doc)
        apply_this(p)

        target_pages = _extract_chapter_page_target(chapter_pages, title)
        if target_pages:
            chars_per_page = _estimate_chars_per_page(section_style_cfg)
            estimated_pages = _estimate_content_pages(content_doc, chars_per_page)
            delta = estimated_pages - target_pages
            layout_receipts.append(
                {
                    "title": title,
                    "target_pages": target_pages,
                    "estimated_pages": estimated_pages,
                    "delta": delta,
                }
            )
            if style_cfg.get("enforce_chapter_pages") and estimated_pages < target_pages:
                for _ in range(target_pages - estimated_pages):
                    doc.add_page_break()
        else:
            chars_per_page = _estimate_chars_per_page(section_style_cfg)
            estimated_pages = _estimate_content_pages(content_doc, chars_per_page)

        # Auto density policy: image count follows planned pages and excludes overview chapters.
        if chart_mode_auto_density and chart_position in {"chapter", "per_chapter", "by_chapter"}:
            if not _is_overview_section(title):
                effective_pages = target_pages if target_pages else estimated_pages
                need_images = _auto_density_images_for_pages(effective_pages, total_planned_pages)
                if need_images > 0:
                    if not chapter_media_started:
                        hmc = doc.add_heading("图表与插图（按页密度自动分布）", level=2)
                        apply_paragraph(hmc, is_title=True)
                        chapter_media_started = True
                    # Generate a small section-specific image pool, then reuse cyclically to meet page density.
                    pool_size = max(2, min(8, need_images))
                    section_pool = generate_section_visuals(
                        title=title,
                        content=content_doc,
                        image_count=pool_size,
                        include_mindmap=True,
                    )
                    if section_pool:
                        for k in range(need_images):
                            _append_media_item(section_pool[k % len(section_pool)])
                    elif media_all:
                        for _ in range(need_images):
                            _append_media_item(media_all[media_cursor % len(media_all)])
                            media_cursor += 1
        # Legacy chapter frequency policy (backward compatibility).
        elif media_all and chart_enabled and chart_position in {"chapter", "per_chapter", "by_chapter"}:
            if ((idx + 1) % chart_every_n == 0) and media_cursor < len(media_all):
                if not chapter_media_started:
                    hmc = doc.add_heading("图表与插图（按章节分布）", level=2)
                    apply_paragraph(hmc, is_title=True)
                    chapter_media_started = True
                _append_media_item(media_all[media_cursor])
                media_cursor += 1

    # 图纸证据索引（可追溯）
    drawing_index = data.get("drawing_index") or {}
    if isinstance(drawing_index, dict) and (drawing_index.get("drawings") or drawing_index.get("chapter_bindings")):
        doc.add_page_break()
        hd = doc.add_heading("图纸证据索引（自动生成）", level=1)
        apply_paragraph(hd, is_title=True)

        drawings = drawing_index.get("drawings") or []
        if drawings:
            h1 = doc.add_heading("图纸清单", level=2)
            apply_paragraph(h1, is_title=True)
            for d in drawings[:30]:
                fn = d.get("filename") or ""
                pages = d.get("pages")
                kws = d.get("keywords") or []
                line = f"- {fn}"
                if pages:
                    line += f"（页数={pages}）"
                if kws:
                    line += f"；关键词={'、'.join([str(x) for x in kws[:8] if str(x).strip()])}"
                p = doc.add_paragraph(line)
                apply_paragraph(p)

        binds = drawing_index.get("chapter_bindings") or []
        if binds:
            h2 = doc.add_heading("章节-图纸绑定", level=2)
            apply_paragraph(h2, is_title=True)
            for b in binds[:40]:
                ch = b.get("chapter") or ""
                loc = b.get("locator") or ""
                p = doc.add_paragraph(f"- {ch} -> {loc}")
                apply_paragraph(p)

    # 企业标准证据索引（可追溯）
    standard_index = data.get("standard_index") or {}
    if isinstance(standard_index, dict) and (standard_index.get("standards") or standard_index.get("chapter_bindings")):
        doc.add_page_break()
        hd = doc.add_heading("企业标准证据索引（自动生成）", level=1)
        apply_paragraph(hd, is_title=True)

        standards = standard_index.get("standards") or []
        if standards:
            h1 = doc.add_heading("标准文件清单", level=2)
            apply_paragraph(h1, is_title=True)
            for d in standards[:40]:
                fn = d.get("filename") or ""
                pages = d.get("pages")
                kws = d.get("keywords") or []
                line = f"- {fn}"
                if pages:
                    line += f"（页数={pages}）"
                if kws:
                    line += f"；关键词={'、'.join([str(x) for x in kws[:8] if str(x).strip()])}"
                p = doc.add_paragraph(line)
                apply_paragraph(p)

        binds = standard_index.get("chapter_bindings") or []
        if binds:
            h2 = doc.add_heading("章节-标准绑定", level=2)
            apply_paragraph(h2, is_title=True)
            for b in binds[:60]:
                ch = b.get("chapter") or ""
                loc = b.get("locator") or ""
                p = doc.add_paragraph(f"- {ch} -> {loc}")
                apply_paragraph(p)

    # 重点项证据闭环索引（BoQ focus cross-index）
    cross_index = data.get("cross_index") or {}
    if isinstance(cross_index, dict) and isinstance(cross_index.get("focus_items"), list) and cross_index.get("focus_items"):
        doc.add_page_break()
        hd = doc.add_heading("重点项证据闭环索引（自动生成）", level=1)
        apply_paragraph(hd, is_title=True)

        fc = int(cross_index.get("focus_count") or 0)
        mc = int(cross_index.get("mentioned_count") or 0)
        okc = int(cross_index.get("closed_ok_count") or 0)
        md = int(cross_index.get("missing_drawing_locator_count") or 0)
        ms = int(cross_index.get("missing_standard_locator_count") or 0)
        p0 = doc.add_paragraph(f"重点项={fc}；出现={mc}；闭环OK={okc}；缺图纸定位={md}；缺标准定位={ms}。")
        apply_paragraph(p0)
        p1 = doc.add_paragraph("闭环OK判定：同一章节内同时满足=量化（含单位数值）+风险→控制→验证+证据定位。")
        apply_paragraph(p1)

        items = cross_index.get("focus_items") or []
        # Keep table compact to avoid layout explosion on A4.
        table = doc.add_table(rows=1, cols=9)
        hdr = table.rows[0].cells
        headers = ["清单项", "类别/工序", "工程量", "单价", "合价", "落位章节", "图纸定位", "标准定位", "闭环"]
        for i, h in enumerate(headers):
            try:
                hdr[i].text = h
            except Exception:
                pass

        def _fmt_num(v: Any) -> str:
            try:
                if v is None:
                    return ""
                f = float(v)
                if abs(f - int(f)) < 1e-6:
                    return str(int(f))
                return f"{f:.4g}"
            except Exception:
                return str(v)

        for it in items[:24]:
            if not isinstance(it, dict):
                continue
            name = str(it.get("name") or "").strip()
            cats = it.get("categories") or []
            if isinstance(cats, list):
                cats = "、".join([str(x) for x in cats if str(x).strip()][:4])
            else:
                cats = str(cats) if cats else ""
            proc = str(it.get("process_name") or "").strip()
            cat_proc = cats
            if proc:
                cat_proc = (cat_proc + ("；" if cat_proc else "") + f"工序={proc}").strip()

            qty = _fmt_num(it.get("quantity"))
            unit = str(it.get("unit") or "").strip()
            qty_disp = (qty + unit).strip()
            up = _fmt_num(it.get("unit_price"))
            tp = _fmt_num(it.get("total_price"))
            ch = str(it.get("chapter") or "").strip()
            dwg = str(it.get("drawing_locator") or "").strip()
            std = str(it.get("standard_locator") or "").strip()
            clo = it.get("closure") if isinstance(it.get("closure"), dict) else {}
            clo_ok = bool(clo.get("ok"))
            missing = clo.get("missing_parts") or []
            if isinstance(missing, list):
                missing = [str(x) for x in missing if str(x).strip()]
            else:
                missing = []
            clo_disp = "OK" if clo_ok else ("缺:" + ",".join(missing) if missing else "缺")

            row = table.add_row().cells
            vals = [name, cat_proc, qty_disp, up, tp, ch, dwg, std, clo_disp]
            for i, v in enumerate(vals):
                try:
                    row[i].text = str(v or "")
                except Exception:
                    pass

    # 可编辑参数影响回执（参数键 -> 出现位置/影响章节）
    param_trace = data.get("param_trace") or {}
    receipt = param_trace.get("receipt") if isinstance(param_trace, dict) else None
    if isinstance(receipt, dict) and isinstance(receipt.get("keys"), dict) and receipt.get("keys"):
        doc.add_page_break()
        hd = doc.add_heading("可编辑参数影响回执（自动生成）", level=1)
        apply_paragraph(hd, is_title=True)
        ver = str(receipt.get("version") or "").strip()
        keys = receipt.get("keys") or {}
        try:
            impacted = set()
            for _, item in keys.items():
                for t in (item or {}).get("impacted_chapters") or []:
                    if str(t).strip():
                        impacted.add(str(t).strip())
            impacted_count = len(impacted)
        except Exception:
            impacted_count = 0
        p0 = doc.add_paragraph(
            f"参数版本={ver or '-'}；参数键={len(keys)}；影响章节数={impacted_count}。"
        )
        apply_paragraph(p0)

        table = doc.add_table(rows=1, cols=3)
        hdr = table.rows[0].cells
        hdr[0].text = "参数键"
        hdr[1].text = "当前值"
        hdr[2].text = "影响章节"

        # Keep compact to reduce DOCX size. Keys are already limited (quant_defaults + boq_focus_card).
        for k in sorted(keys.keys())[:60]:
            item = keys.get(k) or {}
            val = str(item.get("value") or "").strip()
            chs = item.get("impacted_chapters") or []
            if isinstance(chs, list):
                chs = "；".join([str(x).strip() for x in chs if str(x).strip()][:10])
            else:
                chs = str(chs) if chs else ""
            row = table.add_row().cells
            row[0].text = str(k)
            row[1].text = val
            row[2].text = chs

    # Remaining chart/images (default: append at end, or chapter mode leftover).
    remaining_media = [] if chart_mode_auto_density else (media_all[media_cursor:] if isinstance(media_all, list) else [])
    if remaining_media:
        doc.add_page_break()
        hm = doc.add_heading("图表与插图", level=1)
        apply_paragraph(hm, is_title=True)
        for item in remaining_media:
            _append_media_item(item)

    # 章节版式回执
    if layout_receipts:
        doc.add_page_break()
        hl = doc.add_heading("章节版式约束回执", level=1)
        apply_paragraph(hl, is_title=True)
        for item in layout_receipts:
            title = item["title"]
            target = item["target_pages"]
            estimated = item["estimated_pages"]
            delta = item["delta"]
            if delta == 0:
                status = "达成"
            elif delta > 0:
                status = f"超出{abs(delta)}页"
            else:
                status = f"不足{abs(delta)}页"
            p = doc.add_paragraph(f"- {title}: 目标{target}页，估算{estimated}页（{status}）")
            apply_paragraph(p)

    # 质量校验摘要
    qc = data.get("quality_checks") or {}
    if qc:
        doc.add_page_break()
        hq = doc.add_heading("质量校验摘要", level=1)
        apply_paragraph(hq, is_title=True)
        for key in (
            "structure",
            "score_coverage",
            "closed_loop",
            "engineering",
            "risk_triplet",
            "qse_closed_loop",
            "logic_template_adherence",
            "quantitative",
            "vague_terms",
            "officialese",
            "consistency",
            "boq_focus_coverage",
            "boq_focus_item_closure",
            "boq_focus_item_typed_evidence",
            "required_topics",
            "required_topics_detail",
            "trade_names",
            "evidence",
            "evidence_quality",
            "evidence_traceability",
            "drawing_evidence",
            "standard_evidence",
            "template_style",
        ):
            item = qc.get(key) or {}
            ok = item.get("ok")
            p = doc.add_paragraph(f"{key}：{'通过' if ok else '需改进'}")
            apply_paragraph(p)
            for k, v in item.items():
                if k == "ok":
                    continue
                p2 = doc.add_paragraph(f"- {k}: {v}")
                apply_paragraph(p2)
        # 可勾选清单（便于评审）
        hqc = doc.add_heading("质量校验清单", level=2)
        apply_paragraph(hqc, is_title=True)
        for key in (
            "structure",
            "score_coverage",
            "closed_loop",
            "engineering",
            "risk_triplet",
            "qse_closed_loop",
            "logic_template_adherence",
            "quantitative",
            "vague_terms",
            "officialese",
            "consistency",
            "boq_focus_coverage",
            "boq_focus_item_closure",
            "boq_focus_item_typed_evidence",
            "required_topics",
            "required_topics_detail",
            "trade_names",
            "evidence",
            "evidence_quality",
            "evidence_traceability",
            "drawing_evidence",
            "standard_evidence",
            "template_style",
        ):
            item = qc.get(key) or {}
            ok = item.get("ok")
            mark = "☑" if ok else "☐"
            p = doc.add_paragraph(f"{mark} {key}")
            apply_paragraph(p)
            details = {k: v for k, v in item.items() if k != "ok"}
            if details and not ok:
                for k, v in details.items():
                    p2 = doc.add_paragraph(f"  - {k}: {v}")
                    apply_paragraph(p2)

        # 章节评分点覆盖清单
        by_section = qc.get("score_coverage_by_section") or []
        if by_section:
            hsc = doc.add_heading("章节评分点覆盖清单", level=2)
            apply_paragraph(hsc, is_title=True)
            for sec in by_section:
                title = sec.get("title") or "章节"
                ok = sec.get("ok")
                mark = "☑" if ok else "☐"
                p = doc.add_paragraph(f"{mark} {title}")
                apply_paragraph(p)
                if not ok:
                    for miss in sec.get("missing", []):
                        p2 = doc.add_paragraph(f"  - 缺失：{miss.get('dimension')} / {miss.get('keywords')}")
                        apply_paragraph(p2)

        # 章节证据数量清单
        by_evidence = (qc.get("evidence") or {}).get("by_section") or []
        if by_evidence:
            hce = doc.add_heading("章节证据数量清单", level=2)
            apply_paragraph(hce, is_title=True)
            for sec in by_evidence:
                title = sec.get("title") or "章节"
                cnt = sec.get("evidence_count")
                p = doc.add_paragraph(f"- {title}: 证据数 {cnt}")
                apply_paragraph(p)

        # 问题清单 + 自动修订建议（便于评审/二次编辑）
        issues = qc.get("issue_list") or []
        hi = doc.add_heading("问题清单（自动检测）", level=2)
        apply_paragraph(hi, is_title=True)
        if issues:
            for it in issues[:200]:
                sev = it.get("severity") or "medium"
                title = it.get("title") or "章节"
                typ = it.get("type") or "issue"
                prob = it.get("problem") or ""
                sugg = it.get("suggestion") or ""
                p = doc.add_paragraph(f"- [{sev}] {title} / {typ}: {prob}")
                apply_paragraph(p)
                if sugg:
                    p2 = doc.add_paragraph(f"  建议：{sugg}")
                    apply_paragraph(p2)
        else:
            p = doc.add_paragraph("- 无")
            apply_paragraph(p)

        recs = qc.get("auto_revision_suggestions") or []
        hr = doc.add_heading("自动修订建议（按章节聚合）", level=2)
        apply_paragraph(hr, is_title=True)
        if recs:
            # De-dup by (title,type,suggestion)
            seen = set()
            for r in recs[:300]:
                title = r.get("title") or "章节"
                typ = r.get("type") or "issue"
                sugg = r.get("suggestion") or ""
                key = (title, typ, sugg)
                if key in seen:
                    continue
                seen.add(key)
                p = doc.add_paragraph(f"- {title} / {typ}: {sugg}")
                apply_paragraph(p)
        else:
            p = doc.add_paragraph("- 无")
            apply_paragraph(p)

        # 章节风险-措施闭环清单
        by_closed = qc.get("closed_loop_by_section") or []
        if by_closed:
            hcl = doc.add_heading("章节风险-措施闭环清单", level=2)
            apply_paragraph(hcl, is_title=True)
            for sec in by_closed:
                title = sec.get("title") or "章节"
                ok = sec.get("ok")
                mark = "☑" if ok else "☐"
                p = doc.add_paragraph(f"{mark} {title}（风险: {sec.get('has_risk')} / 措施: {sec.get('has_measure')}）")
                apply_paragraph(p)

        # 章节工程落地要素清单
        by_eng = qc.get("engineering_by_section") or []
        if by_eng:
            heg = doc.add_heading("章节工程落地要素清单", level=2)
            apply_paragraph(heg, is_title=True)
            for sec in by_eng:
                title = sec.get("title") or "章节"
                ok = sec.get("ok")
                mark = "☑" if ok else "☐"
                missing = sec.get("missing") or []
                p = doc.add_paragraph(f"{mark} {title}（缺失: {missing}）")
                apply_paragraph(p)

        # 整改建议清单
        remediation = qc.get("remediation") or []
        if remediation:
            hrs = doc.add_heading("整改建议清单", level=2)
            apply_paragraph(hrs, is_title=True)
            for rec in remediation:
                title = rec.get("title") or "章节"
                rtype = rec.get("type") or "issue"
                suggestion = rec.get("suggestion") or ""
                p = doc.add_paragraph(f"- {title} / {rtype}: {suggestion}")
                apply_paragraph(p)

        issue_list = qc.get("issue_list") or []
        if issue_list:
            hi = doc.add_heading("问题清单", level=2)
            apply_paragraph(hi, is_title=True)
            for it in issue_list:
                title = it.get("title") or "章节"
                itype = it.get("type") or "issue"
                sev = it.get("severity") or "medium"
                prob = it.get("problem") or ""
                p = doc.add_paragraph(f"- [{sev}] {title} / {itype}: {prob}")
                apply_paragraph(p)

        auto_revision = qc.get("auto_revision_suggestions") or []
        if auto_revision:
            ha = doc.add_heading("自动修订建议", level=2)
            apply_paragraph(ha, is_title=True)
            for rec in auto_revision:
                title = rec.get("title") or "章节"
                rtype = rec.get("type") or "issue"
                suggestion = rec.get("suggestion") or ""
                p = doc.add_paragraph(f"- {title} / {rtype}: {suggestion}")
                apply_paragraph(p)

        # LLM整改前后对比
        has_compare = False
        for sec in sections:
            if sec.get("auto_remediated") == "llm" and sec.get("original_content"):
                has_compare = True
                break
        if has_compare:
            hcp = doc.add_heading("LLM整改前后对比", level=2)
            apply_paragraph(hcp, is_title=True)
            compare_cfg = data.get("compare") or {}
            mode = compare_cfg.get("mode", "full")
            max_chars = _to_int(compare_cfg.get("max_chars"), 800)
            titles_filter = compare_cfg.get("titles")
            for sec in sections:
                if sec.get("auto_remediated") != "llm" or not sec.get("original_content"):
                    continue
                if isinstance(titles_filter, list) and sec.get("title") not in titles_filter:
                    continue
                title = sec.get("title") or "章节"
                h3 = doc.add_heading(title, level=3)
                apply_paragraph(h3, is_title=True)
                p1 = doc.add_paragraph("整改前：")
                apply_paragraph(p1)
                before = sec.get("original_content") or ""
                after = sec.get("content") or ""
                if mode == "summary":
                    before = before[:max_chars] + ("..." if len(before) > max_chars else "")
                    after = after[:max_chars] + ("..." if len(after) > max_chars else "")
                p2 = doc.add_paragraph(before)
                apply_paragraph(p2)
                p3 = doc.add_paragraph("整改后：")
                apply_paragraph(p3)
                p4 = doc.add_paragraph(after)
                apply_paragraph(p4)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path


def export_autoplan_compare_docx(data: Dict[str, Any], output_path: str) -> str:
    style_raw = data.get("style") or {}
    style_cfg = _normalize_style(style_raw)
    doc = Document()
    _apply_page_setup(doc, style_cfg)
    apply_paragraph = _apply_style(doc, style_raw)

    h = doc.add_heading((data.get("topic") or "施组方案") + " - 整改对比", level=1)
    apply_paragraph(h, is_title=True)

    compare_cfg = data.get("compare") or {}
    mode = compare_cfg.get("mode", "summary")
    max_chars = _to_int(compare_cfg.get("max_chars"), 800)
    titles_filter = compare_cfg.get("titles")

    has_any = False
    for sec in data.get("sections", []):
        if sec.get("auto_remediated") != "llm" or not sec.get("original_content"):
            continue
        if isinstance(titles_filter, list) and sec.get("title") not in titles_filter:
            continue
        has_any = True
        title = sec.get("title") or "章节"
        h2 = doc.add_heading(title, level=2)
        apply_paragraph(h2, is_title=True)
        before = sec.get("original_content") or ""
        after = sec.get("content") or ""
        if mode == "summary":
            before = before[:max_chars] + ("..." if len(before) > max_chars else "")
            after = after[:max_chars] + ("..." if len(after) > max_chars else "")
        p1 = doc.add_paragraph("整改前：")
        apply_paragraph(p1)
        p2 = doc.add_paragraph(before)
        apply_paragraph(p2)
        p3 = doc.add_paragraph("整改后：")
        apply_paragraph(p3)
        p4 = doc.add_paragraph(after)
        apply_paragraph(p4)

    if not has_any:
        p = doc.add_paragraph("暂无可对比的章节（需使用 LLM 整改且保留 original_content）。")
        apply_paragraph(p)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return output_path


def export_autoplan_focus_xlsx(data: Dict[str, Any], output_path: str) -> str:
    """
    Export a reviewer-friendly XLSX for BoQ focus closure:
    - focus items cross-index (chapter + drawing/std locator + closure gaps)
    - issue list + auto revision suggestions (for quick triage)
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except Exception:
        return ""

    cross_index = data.get("cross_index") if isinstance(data.get("cross_index"), dict) else {}
    focus_items = cross_index.get("focus_items") if isinstance(cross_index.get("focus_items"), list) else []
    qc = data.get("quality_checks") if isinstance(data.get("quality_checks"), dict) else {}
    issues = qc.get("issue_list") if isinstance(qc.get("issue_list"), list) else []
    recs = qc.get("auto_revision_suggestions") if isinstance(qc.get("auto_revision_suggestions"), list) else []
    param_trace = data.get("param_trace") if isinstance(data.get("param_trace"), dict) else {}
    plan_consistency = data.get("plan_consistency") if isinstance(data.get("plan_consistency"), dict) else {}
    cpm_receipt = plan_consistency.get("cpm") if isinstance(plan_consistency.get("cpm"), dict) else {}
    boq_focus = data.get("boq_focus") if isinstance(data.get("boq_focus"), dict) else {}
    four_new_recs = boq_focus.get("four_new_recommendations") if isinstance(boq_focus.get("four_new_recommendations"), list) else []
    variant_similarity = data.get("variant_similarity") if isinstance(data.get("variant_similarity"), dict) else {}
    drawing_index = data.get("drawing_index") if isinstance(data.get("drawing_index"), dict) else {}
    standard_index = data.get("standard_index") if isinstance(data.get("standard_index"), dict) else {}
    branding = data.get("branding") if isinstance(data.get("branding"), dict) else {}

    drawings = drawing_index.get("drawings") if isinstance(drawing_index.get("drawings"), list) else []
    drawing_binds = drawing_index.get("chapter_bindings") if isinstance(drawing_index.get("chapter_bindings"), list) else []
    standards = standard_index.get("standards") if isinstance(standard_index.get("standards"), list) else []
    standard_binds = standard_index.get("chapter_bindings") if isinstance(standard_index.get("chapter_bindings"), list) else []
    has_drawing_index = bool(drawings or drawing_binds)
    has_standard_index = bool(standards or standard_binds)

    # Parse structured focus cards from section text so reviewers can verify quant + triplet + typed evidence.
    focus_cards = []
    try:
        from backend.zhifei_autoplan.focus_card_parser import extract_focus_cards

        focus_cards = extract_focus_cards(data.get("sections") or [])
    except Exception:
        focus_cards = []

    # Param trace may exist even when focus items are empty.
    receipt = param_trace.get("receipt") if isinstance(param_trace.get("receipt"), dict) else {}
    receipt_keys = receipt.get("keys") if isinstance(receipt.get("keys"), dict) else {}

    has_plan_consistency = bool(plan_consistency and (plan_consistency.get("canonical") or plan_consistency.get("changed")))
    has_cpm_receipt = bool(cpm_receipt and (cpm_receipt.get("computed") or cpm_receipt.get("activities")))
    has_variant_similarity = bool(variant_similarity and int(variant_similarity.get("variant_count") or 0) >= 2)

    # Sync variant-similarity findings into issues/revision sheets so reviewers don't need JSON.
    issues = list(issues) if isinstance(issues, list) else []
    recs = list(recs) if isinstance(recs, list) else []
    if has_variant_similarity:
        try:
            chapter_thr = float(variant_similarity.get("chapter_threshold") or 0.90)
        except Exception:
            chapter_thr = 0.90
        strict_flagged = variant_similarity.get("flagged") if isinstance(variant_similarity.get("flagged"), list) else []
        if strict_flagged and (variant_similarity.get("ok") is False):
            for f in strict_flagged[:24]:
                if not isinstance(f, dict):
                    continue
                title = str(f.get("title") or "").strip() or "章节"
                pair = str(f.get("pair") or "").strip() or "pair"
                sim = f.get("similarity")
                thr = f.get("threshold") if f.get("threshold") is not None else chapter_thr
                problem = f"多方案相似度过高：{pair}={sim}（阈值={thr}）。"
                suggestion = (
                    "不改招标目录，重写本章章内逻辑：A=交付物/约束/步骤/闭环；"
                    "B=工序流程/控制点表/资源节拍；C=指标矩阵/人机料法环/闭环分组；"
                    "用短句卡片表达，避免长段复述。"
                )
                issues.append(
                    {
                        "severity": "high",
                        "title": title,
                        "type": "variant_diversity_gap",
                        "problem": problem,
                        "suggestion": suggestion,
                    }
                )
                recs.append({"title": title, "type": "variant_diversity_gap", "suggestion": suggestion})

        relaxed_flagged = (
            variant_similarity.get("relaxed_flagged")
            if isinstance(variant_similarity.get("relaxed_flagged"), list)
            else []
        )
        # Informational: relaxed chapters are excluded from gate, but still shown for reviewers.
        for f in relaxed_flagged[:12]:
            if not isinstance(f, dict):
                continue
            title = str(f.get("title") or "").strip() or "章节"
            pair = str(f.get("pair") or "").strip() or "pair"
            sim = f.get("similarity")
            thr = f.get("threshold")
            problem = f"多方案相似度偏高（白名单/放宽章节）：{pair}={sim}（放宽阈值={thr}）。"
            suggestion = "可选优化：用“表/矩阵/闭环卡片”替代叙述段，保留事实数据与证据定位。"
            issues.append(
                {
                    "severity": "low",
                    "title": title,
                    "type": "variant_diversity_relaxed_note",
                    "problem": problem,
                    "suggestion": suggestion,
                }
            )

    # If chapters were auto-fixed for diversity, record as low-severity reviewer notes.
    try:
        secs = data.get("sections") if isinstance(data.get("sections"), list) else []
        notes = []
        for s in secs:
            if not isinstance(s, dict):
                continue
            if str(s.get("auto_remediated") or "") != "diversity_autofix":
                continue
            title = str(s.get("title") or "").strip()
            if not title:
                continue
            tid = str(s.get("logic_template_id") or "").strip().upper()
            dom = str(s.get("chapter_domain") or "").strip().lower()
            notes.append((title, tid, dom))
        seen = set()
        for title, tid, dom in notes[:24]:
            key = (title, tid, dom)
            if key in seen:
                continue
            seen.add(key)
            issues.append(
                {
                    "severity": "low",
                    "title": title,
                    "type": "variant_diversity_autofixed",
                    "problem": f"本章已执行多方案差异化结构重排（模版={tid or '-'}；domain={dom or '-'}）。",
                    "suggestion": "复核：清单重点项/量化指标/风险→控制→验证闭环/证据定位是否仍匹配本章内容。",
                }
            )
    except Exception:
        pass

    # Deduplicate (keeps sheets readable).
    try:
        dedup = {}
        for it in issues:
            if not isinstance(it, dict):
                continue
            key = (it.get("title"), it.get("type"), it.get("problem"))
            dedup[key] = it
        issues = list(dedup.values())
    except Exception:
        pass
    try:
        dedup2 = {}
        for it in recs:
            if not isinstance(it, dict):
                continue
            key = (it.get("title"), it.get("type"), it.get("suggestion"))
            dedup2[key] = it
        recs = list(dedup2.values())
    except Exception:
        pass

    # If nothing to export, do not create a file.
    if not (
        focus_items
        or issues
        or recs
        or focus_cards
        or four_new_recs
        or receipt_keys
        or has_plan_consistency
        or has_cpm_receipt
        or has_variant_similarity
        or has_drawing_index
        or has_standard_index
    ):
        return ""

    def _fmt_num(v: Any) -> Any:
        try:
            if v is None:
                return ""
            f = float(v)
            if abs(f - int(f)) < 1e-9:
                return int(f)
            return f
        except Exception:
            return str(v) if v is not None else ""

    def _join_list(v: Any, sep: str = "；", limit: int = 10) -> str:
        if isinstance(v, list):
            parts = [str(x).strip() for x in v if str(x).strip()]
            return sep.join(parts[: max(0, int(limit or 0))])
        return str(v).strip() if isinstance(v, str) else ""

    def _clean_val(v: Any) -> str:
        s = str(v or "").strip()
        # Focus-card values often end with '。' from sentence punctuation.
        return s.rstrip("。.;；")

    cards_by_key = {}
    cards_by_name = {}
    try:
        import re as _re

        def _norm_name(s: Any) -> str:
            t = str(s or "").strip()
            t = _re.sub(r"[\\s\\u3000]+", "", t)
            t = t.strip("，,。．.；;：:、")
            return t

        def _pick_better(a: dict | None, b: dict) -> dict:
            if not a:
                return b
            ae = len(a.get("evidence_sources") or [])
            be = len(b.get("evidence_sources") or [])
            if be != ae:
                return b if be > ae else a
            ar = len(str(a.get("raw") or ""))
            br = len(str(b.get("raw") or ""))
            return b if br > ar else a

        for c in focus_cards or []:
            if not isinstance(c, dict):
                continue
            ch = str(c.get("chapter") or "").strip()
            name = _norm_name(c.get("name"))
            if not name:
                continue
            key = (ch, name)
            cards_by_key[key] = _pick_better(cards_by_key.get(key), c)
            cards_by_name[name] = _pick_better(cards_by_name.get(name), c)
    except Exception:
        cards_by_key = {}
        cards_by_name = {}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    hdr_font = Font(bold=True)
    hdr_fill = PatternFill("solid", fgColor="F2F2F2")
    warn_fill = PatternFill("solid", fgColor="FFF2CC")
    wrap = Alignment(wrap_text=True, vertical="top")

    def _write(ws, r: int, c: int, v: Any, header: bool = False):
        cell = ws.cell(row=r, column=c, value=v)
        cell.alignment = wrap
        if header:
            cell.font = hdr_font
            cell.fill = hdr_fill
        return cell

    def _set_width(ws, col: int, width: float):
        try:
            ws.column_dimensions[get_column_letter(int(col))].width = float(width)
        except Exception:
            pass

    # Summary sheet
    ws = wb.active
    ws.title = "summary"
    row = 1
    logic = data.get("logic_template") if isinstance(data.get("logic_template"), dict) else {}
    logic_id = str(logic.get("id") or "").strip()
    logic_name = str(logic.get("name") or "").strip()
    summary_pairs = [
        ("topic", data.get("topic") or ""),
        ("project_id", (cross_index.get("project_id") or data.get("project_id") or "")),
        ("logic_template_id", logic_id),
        ("logic_template_name", logic_name),
        ("bidder_company", str(branding.get("bidder_company") or "")),
        ("bidder_domain", str(branding.get("bidder_domain") or "")),
        ("logo_path", str(branding.get("logo_path") or "")),
        ("focus_count", cross_index.get("focus_count") or 0),
        ("mentioned_count", cross_index.get("mentioned_count") or 0),
        ("closed_ok_count", cross_index.get("closed_ok_count") or 0),
        ("missing_drawing_locator_count", cross_index.get("missing_drawing_locator_count") or 0),
        ("missing_standard_locator_count", cross_index.get("missing_standard_locator_count") or 0),
        ("focus_cards_count", len(focus_cards or [])),
        ("four_new_recommendations_count", len(four_new_recs or [])),
        ("drawing_files_count", len(drawings or [])),
        ("drawing_bindings_count", len(drawing_binds or [])),
        ("standard_files_count", len(standards or [])),
        ("standard_bindings_count", len(standard_binds or [])),
    ]
    if has_variant_similarity:
        summary_pairs.extend(
            [
                ("variant_similarity_ok", bool(variant_similarity.get("ok"))),
                ("variant_similarity_avg_max_strict", variant_similarity.get("avg_max_similarity")),
                ("variant_similarity_avg_max_all", variant_similarity.get("avg_max_similarity_all")),
                ("variant_similarity_flagged_count", variant_similarity.get("flagged_count")),
                ("variant_similarity_relaxed_flagged_count", variant_similarity.get("relaxed_flagged_count")),
            ]
        )
    if has_cpm_receipt:
        computed = cpm_receipt.get("computed") if isinstance(cpm_receipt.get("computed"), dict) else {}
        cpm_conflicts = cpm_receipt.get("conflicts") if isinstance(cpm_receipt.get("conflicts"), list) else []
        summary_pairs.extend(
            [
                ("cpm_ok", bool(cpm_receipt.get("ok"))),
                ("cpm_algorithm", str(cpm_receipt.get("algorithm") or "")),
                ("cpm_duration_days", computed.get("project_duration_days")),
                ("cpm_resource_peak", computed.get("resource_peak")),
                ("cpm_critical_interval_days", computed.get("critical_interval_days")),
                ("cpm_conflict_count", len(cpm_conflicts)),
            ]
        )

    for k, v in summary_pairs:
        _write(ws, row, 1, str(k), header=True)
        _write(ws, row, 2, v if not isinstance(v, (dict, list)) else _join_list(v))
        row += 1
    _set_width(ws, 1, 28)
    _set_width(ws, 2, 80)

    # Variant similarity (cross-variant anti-paraphrase report)
    if has_variant_similarity:
        ws = wb.create_sheet("variant_similarity")
        row = 1
        for k, v in [
            ("ok", bool(variant_similarity.get("ok"))),
            ("variant_count", int(variant_similarity.get("variant_count") or 0)),
            ("avg_max_similarity_strict", variant_similarity.get("avg_max_similarity")),
            ("avg_max_similarity_all", variant_similarity.get("avg_max_similarity_all")),
            ("strict_chapter_count", variant_similarity.get("strict_chapter_count")),
            ("relaxed_chapter_count", variant_similarity.get("relaxed_chapter_count")),
            ("chapter_threshold", variant_similarity.get("chapter_threshold")),
            ("relaxed_chapter_threshold", variant_similarity.get("relaxed_chapter_threshold")),
            ("overall_threshold", variant_similarity.get("overall_threshold")),
            ("min_chars", variant_similarity.get("min_chars")),
            ("flagged_count", variant_similarity.get("flagged_count")),
            ("relaxed_flagged_count", variant_similarity.get("relaxed_flagged_count")),
        ]:
            _write(ws, row, 1, str(k), header=True)
            _write(ws, row, 2, v)
            row += 1
        row += 1

        vcount = int(variant_similarity.get("variant_count") or 0)
        pairs = []
        for i in range(1, vcount + 1):
            for j in range(i + 1, vcount + 1):
                pairs.append((i, j))

        headers = ["title", "relaxed", "threshold", "max_pair", "max_combined"]
        for i in range(1, vcount + 1):
            headers.append(f"len_v{i}")
        for i, j in pairs:
            headers.extend([f"v{i}_v{j}_combined", f"v{i}_v{j}_jaccard3", f"v{i}_v{j}_cosine2"])
        for c, h in enumerate(headers, start=1):
            _write(ws, row, c, h, header=True)
        row += 1

        chapter_thr = float(variant_similarity.get("chapter_threshold") or 0.90)
        for rec in (variant_similarity.get("by_chapter") or [])[:300]:
            if not isinstance(rec, dict):
                continue
            title = str(rec.get("title") or "")
            is_relaxed = bool(rec.get("relaxed"))
            thr_used = rec.get("threshold")
            max_pair = str(rec.get("max_pair") or "")
            max_combined = rec.get("max_combined")
            lens = rec.get("lens") if isinstance(rec.get("lens"), list) else []
            values = [title, "Y" if is_relaxed else "N", _fmt_num(thr_used), max_pair, _fmt_num(max_combined)]
            for i in range(1, vcount + 1):
                values.append(_fmt_num(lens[i - 1] if i - 1 < len(lens) else ""))
            for i, j in pairs:
                key = f"v{i}_v{j}"
                ps = rec.get(key) if isinstance(rec.get(key), dict) else {}
                values.extend([_fmt_num(ps.get("combined")), _fmt_num(ps.get("jaccard3")), _fmt_num(ps.get("cosine2"))])
            for c, v in enumerate(values, start=1):
                cell = _write(ws, row, c, v)
                try:
                    # Highlight only strict chapters; relaxed chapters are informational.
                    thr = float(thr_used or chapter_thr)
                    if (not is_relaxed) and float(max_combined or 0.0) >= thr:
                        cell.fill = warn_fill
                except Exception:
                    pass
            row += 1

        _set_width(ws, 1, 22)
        _set_width(ws, 2, 10)
        _set_width(ws, 3, 12)
        _set_width(ws, 4, 10)
        _set_width(ws, 5, 12)
        base = 6
        for i in range(1, vcount + 1):
            _set_width(ws, base + i - 1, 10)
        # Pair columns
        for c in range(base + vcount, base + vcount + (len(pairs) * 3)):
            _set_width(ws, c, 14)

    # Drawings index (files + chapter bindings)
    if has_drawing_index:
        if drawings:
            ws = wb.create_sheet("drawings")
            headers = [
                "filename",
                "sha256",
                "pages",
                "keywords",
                "topology_nodes",
                "topology_edges",
                "topology_components",
                "topology_endpoints",
                "topology_trunk_length",
                "topology_suggested_flow_segments",
                "topology_confidence",
                "preview",
            ]
            for c, h in enumerate(headers, start=1):
                _write(ws, 1, c, h, header=True)
            for r, d in enumerate(drawings[:300], start=2):
                if not isinstance(d, dict):
                    continue
                kws = _join_list(d.get("keywords") or [], sep="、", limit=12)
                topo = d.get("topology") if isinstance(d.get("topology"), dict) else {}
                vals = [
                    str(d.get("filename") or ""),
                    str(d.get("sha256") or "")[:12],
                    _fmt_num(d.get("pages")),
                    kws,
                    _fmt_num(topo.get("nodes_count")),
                    _fmt_num(topo.get("edges_count")),
                    _fmt_num(topo.get("components_count")),
                    _fmt_num(topo.get("endpoint_count")),
                    _fmt_num(topo.get("trunk_length")),
                    _fmt_num(topo.get("suggested_flow_segments")),
                    str(topo.get("topology_confidence") or ""),
                    str(d.get("preview") or ""),
                ]
                for c, v in enumerate(vals, start=1):
                    _write(ws, r, c, v)
            _set_width(ws, 1, 54)
            _set_width(ws, 2, 18)
            _set_width(ws, 3, 10)
            _set_width(ws, 4, 48)
            _set_width(ws, 5, 12)
            _set_width(ws, 6, 12)
            _set_width(ws, 7, 12)
            _set_width(ws, 8, 12)
            _set_width(ws, 9, 14)
            _set_width(ws, 10, 16)
            _set_width(ws, 11, 14)
            _set_width(ws, 12, 78)

        if drawing_binds:
            ws = wb.create_sheet("drawing_bindings")
            headers = ["chapter", "locator", "filename", "page", "offset", "snippet"]
            for c, h in enumerate(headers, start=1):
                _write(ws, 1, c, h, header=True)
            for r, b in enumerate(drawing_binds[:600], start=2):
                if not isinstance(b, dict):
                    continue
                vals = [
                    str(b.get("chapter") or ""),
                    str(b.get("locator") or ""),
                    str(b.get("filename") or ""),
                    _fmt_num(b.get("page")),
                    _fmt_num(b.get("offset")),
                    str(b.get("snippet") or ""),
                ]
                for c, v in enumerate(vals, start=1):
                    _write(ws, r, c, v)
            _set_width(ws, 1, 28)
            _set_width(ws, 2, 46)
            _set_width(ws, 3, 54)
            _set_width(ws, 4, 10)
            _set_width(ws, 5, 12)
            _set_width(ws, 6, 90)

    # Enterprise standards index (files + chapter bindings)
    if has_standard_index:
        if standards:
            ws = wb.create_sheet("standards")
            headers = ["filename", "sha256", "pages", "keywords"]
            for c, h in enumerate(headers, start=1):
                _write(ws, 1, c, h, header=True)
            for r, d in enumerate(standards[:400], start=2):
                if not isinstance(d, dict):
                    continue
                kws = _join_list(d.get("keywords") or [], sep="、", limit=12)
                vals = [
                    str(d.get("filename") or ""),
                    str(d.get("sha256") or "")[:12],
                    _fmt_num(d.get("pages")),
                    kws,
                ]
                for c, v in enumerate(vals, start=1):
                    _write(ws, r, c, v)
            _set_width(ws, 1, 58)
            _set_width(ws, 2, 18)
            _set_width(ws, 3, 10)
            _set_width(ws, 4, 80)

        if standard_binds:
            ws = wb.create_sheet("standard_bindings")
            headers = ["chapter", "locator", "filename", "page", "offset", "snippet"]
            for c, h in enumerate(headers, start=1):
                _write(ws, 1, c, h, header=True)
            for r, b in enumerate(standard_binds[:800], start=2):
                if not isinstance(b, dict):
                    continue
                vals = [
                    str(b.get("chapter") or ""),
                    str(b.get("locator") or ""),
                    str(b.get("filename") or ""),
                    _fmt_num(b.get("page")),
                    _fmt_num(b.get("offset")),
                    str(b.get("snippet") or ""),
                ]
                for c, v in enumerate(vals, start=1):
                    _write(ws, r, c, v)
            _set_width(ws, 1, 28)
            _set_width(ws, 2, 46)
            _set_width(ws, 3, 58)
            _set_width(ws, 4, 10)
            _set_width(ws, 5, 12)
            _set_width(ws, 6, 90)

    # Param trace (editable parameter -> impacted chapters)
    if receipt_keys:
        ws = wb.create_sheet("param_trace")
        headers = [
            "param_key",
            "value",
            "impacted_chapters",
            "placeholder_hits",
            "value_hits",
            "placeholder_occurrences",
            "value_occurrences",
        ]
        for c, h in enumerate(headers, start=1):
            _write(ws, 1, c, h, header=True)

        def _occ_list(arr: Any, limit: int = 24) -> str:
            if not isinstance(arr, list):
                return ""
            out = []
            for it in arr[: max(1, int(limit or 0))]:
                if not isinstance(it, dict):
                    continue
                t = str(it.get("title") or "").strip()
                off = it.get("offset")
                if t and off is not None:
                    out.append(f"{t}@{off}")
            return "；".join(out)

        for r, (k, item) in enumerate(sorted(receipt_keys.items(), key=lambda x: x[0]), start=2):
            if not isinstance(item, dict):
                continue
            impacted = _join_list(item.get("impacted_chapters") or [], sep="；", limit=40)
            ph = item.get("placeholder_occurrences") or []
            vh = item.get("value_occurrences") or []
            values = [
                str(k),
                str(item.get("value") or ""),
                impacted,
                len(ph) if isinstance(ph, list) else 0,
                len(vh) if isinstance(vh, list) else 0,
                _occ_list(ph),
                _occ_list(vh),
            ]
            for c, v in enumerate(values, start=1):
                _write(ws, r, c, v)
        _set_width(ws, 1, 32)
        _set_width(ws, 2, 28)
        _set_width(ws, 3, 60)
        _set_width(ws, 4, 14)
        _set_width(ws, 5, 14)
        _set_width(ws, 6, 80)
        _set_width(ws, 7, 80)

    # Plan consistency receipt (工期/资源峰值/关键线路间隔)
    if plan_consistency and (plan_consistency.get("canonical") or plan_consistency.get("changed")):
        ws = wb.create_sheet("plan_consistency")
        _write(ws, 1, 1, "metric", header=True)
        _write(ws, 1, 2, "canonical_value", header=True)
        row = 2
        can = plan_consistency.get("canonical") if isinstance(plan_consistency.get("canonical"), dict) else {}
        for k, v in (can or {}).items():
            _write(ws, row, 1, str(k))
            _write(ws, row, 2, str(v))
            row += 1
        row += 1
        _write(ws, row, 1, "changed_chapters", header=True)
        changed = plan_consistency.get("changed") if isinstance(plan_consistency.get("changed"), list) else []
        ch_titles = [str(it.get("title") or "").strip() for it in changed if isinstance(it, dict) and str(it.get("title") or "").strip()]
        _write(ws, row, 2, "；".join(ch_titles[:60]))
        _set_width(ws, 1, 24)
        _set_width(ws, 2, 90)

    # CPM deterministic schedule receipt (NetworkX DAG + critical path)
    if has_cpm_receipt:
        ws = wb.create_sheet("cpm")
        row = 1
        computed = cpm_receipt.get("computed") if isinstance(cpm_receipt.get("computed"), dict) else {}
        mentioned = cpm_receipt.get("mentioned") if isinstance(cpm_receipt.get("mentioned"), dict) else {}
        graph = cpm_receipt.get("graph") if isinstance(cpm_receipt.get("graph"), dict) else {}
        critical_path = cpm_receipt.get("critical_path") if isinstance(cpm_receipt.get("critical_path"), list) else []
        conflict_rows = cpm_receipt.get("conflicts") if isinstance(cpm_receipt.get("conflicts"), list) else []
        for k, v in [
            ("ok", bool(cpm_receipt.get("ok"))),
            ("algorithm", str(cpm_receipt.get("algorithm") or "")),
            ("mentioned_工期", mentioned.get("工期")),
            ("mentioned_资源峰值", mentioned.get("资源峰值")),
            ("mentioned_关键线路间隔", mentioned.get("关键线路间隔")),
            ("computed_project_duration_days", computed.get("project_duration_days")),
            ("computed_resource_peak", computed.get("resource_peak")),
            ("computed_critical_interval_days", computed.get("critical_interval_days")),
            ("critical_path", " -> ".join([str(x) for x in critical_path[:40]])),
            ("graph_node_count", graph.get("node_count")),
            ("graph_edge_count", graph.get("edge_count")),
            ("cycle_edges_removed", _join_list(graph.get("cycle_edges_removed") or [], sep="；", limit=20)),
            ("conflict_count", len(conflict_rows)),
        ]:
            _write(ws, row, 1, str(k), header=True)
            _write(ws, row, 2, v if not isinstance(v, (dict, list)) else _join_list(v))
            row += 1
        row += 1
        _write(ws, row, 1, "metric", header=True)
        _write(ws, row, 2, "mentioned", header=True)
        _write(ws, row, 3, "computed", header=True)
        _write(ws, row, 4, "tolerance", header=True)
        _write(ws, row, 5, "delta", header=True)
        row += 1
        for c in conflict_rows[:60]:
            if not isinstance(c, dict):
                continue
            _write(ws, row, 1, str(c.get("metric") or ""))
            _write(ws, row, 2, _fmt_num(c.get("mentioned")))
            _write(ws, row, 3, _fmt_num(c.get("computed")))
            _write(ws, row, 4, _fmt_num(c.get("tolerance")))
            _write(ws, row, 5, _fmt_num(c.get("delta")))
            row += 1
        row += 1
        _write(ws, row, 1, "activity_id", header=True)
        _write(ws, row, 2, "name", header=True)
        _write(ws, row, 3, "deps", header=True)
        _write(ws, row, 4, "duration_days", header=True)
        _write(ws, row, 5, "resource_units", header=True)
        _write(ws, row, 6, "ES", header=True)
        _write(ws, row, 7, "EF", header=True)
        _write(ws, row, 8, "LS", header=True)
        _write(ws, row, 9, "LF", header=True)
        _write(ws, row, 10, "total_float", header=True)
        _write(ws, row, 11, "critical", header=True)
        row += 1
        for act in (cpm_receipt.get("activities") or [])[:600]:
            if not isinstance(act, dict):
                continue
            vals = [
                str(act.get("id") or ""),
                str(act.get("name") or ""),
                _join_list(act.get("deps") or [], sep="、", limit=20),
                _fmt_num(act.get("duration_days")),
                _fmt_num(act.get("resource_units")),
                _fmt_num(act.get("es")),
                _fmt_num(act.get("ef")),
                _fmt_num(act.get("ls")),
                _fmt_num(act.get("lf")),
                _fmt_num(act.get("total_float")),
                "Y" if act.get("critical") else "N",
            ]
            for c, v in enumerate(vals, start=1):
                _write(ws, row, c, v)
            row += 1
        _set_width(ws, 1, 18)
        _set_width(ws, 2, 28)
        _set_width(ws, 3, 22)
        _set_width(ws, 4, 12)
        _set_width(ws, 5, 12)
        _set_width(ws, 6, 10)
        _set_width(ws, 7, 10)
        _set_width(ws, 8, 10)
        _set_width(ws, 9, 10)
        _set_width(ws, 10, 12)
        _set_width(ws, 11, 10)

    # Four-new recommendations (editable library + BoQ/process matching)
    if isinstance(four_new_recs, list) and four_new_recs:
        ws = wb.create_sheet("four_new")
        headers = ["category", "name", "project_type", "project_types", "score", "matched_keywords", "trades", "roles", "acceptance_preview"]
        for c, h in enumerate(headers, start=1):
            _write(ws, 1, c, h, header=True)
        for r, it in enumerate(four_new_recs[:24], start=2):
            if not isinstance(it, dict):
                continue
            cat = str(it.get("category") or "").strip()
            name = str(it.get("name") or "").strip()
            pt = str(it.get("project_type") or "").strip()
            pts = _join_list(it.get("project_types") or [], sep="、", limit=8)
            score = it.get("score")
            matched = _join_list(it.get("matched") or [], sep="、", limit=12)
            trades = _join_list(it.get("trades") or [], sep="、", limit=12)
            roles = _join_list(it.get("roles") or [], sep="、", limit=12)
            acc = _join_list(it.get("acceptance") or [], sep="；", limit=2)
            vals = [cat, name, pt, pts, _fmt_num(score), matched, trades, roles, acc]
            for c, v in enumerate(vals, start=1):
                _write(ws, r, c, v)
        _set_width(ws, 1, 16)
        _set_width(ws, 2, 58)
        _set_width(ws, 3, 12)
        _set_width(ws, 4, 24)
        _set_width(ws, 5, 10)
        _set_width(ws, 6, 40)
        _set_width(ws, 7, 28)
        _set_width(ws, 8, 28)
        _set_width(ws, 9, 68)

    # Focus index
    if focus_items:
        ws = wb.create_sheet("focus_index")
        headers = [
            "清单项",
            "类别",
            "工序",
            "清单编码",
            "工程量",
            "单位",
            "单价",
            "合价",
            "落位章节",
            "图纸定位",
            "标准定位",
            "闭环OK",
            "缺口",
            "flags",
            "近邻证据",
            "卡-工程量",
            "卡-单价",
            "卡-合价",
            "卡-频次",
            "卡-阈值",
            "卡-间距",
            "卡-厚度",
            "卡-时长",
            "卡-人数",
            "卡-设备型号",
            "卡-图纸定位",
            "卡-标准引用",
            "卡-风险",
            "卡-控制",
            "卡-验证",
            "卡-证据来源",
        ]
        for c, h in enumerate(headers, start=1):
            _write(ws, 1, c, h, header=True)

        for r, it in enumerate(focus_items[:300], start=2):
            if not isinstance(it, dict):
                continue
            clo = it.get("closure") if isinstance(it.get("closure"), dict) else {}
            # Find the best-matching control card by (chapter, name), fallback to name-only.
            card = None
            try:
                name_norm = _norm_name(it.get("name"))
                ch_norm = str(it.get("chapter") or "").strip()
                card = cards_by_key.get((ch_norm, name_norm)) or cards_by_name.get(name_norm)
            except Exception:
                card = None
            head = card.get("head") if isinstance(card, dict) and isinstance(card.get("head"), dict) else {}
            quant = card.get("quant") if isinstance(card, dict) and isinstance(card.get("quant"), dict) else {}

            values = [
                str(it.get("name") or ""),
                _join_list(it.get("categories") or [], sep="、", limit=8),
                str(it.get("process_name") or ""),
                str(it.get("boq_code") or ""),
                _fmt_num(it.get("quantity")),
                str(it.get("unit") or ""),
                _fmt_num(it.get("unit_price")),
                _fmt_num(it.get("total_price")),
                str(it.get("chapter") or ""),
                str(it.get("drawing_locator") or ""),
                str(it.get("standard_locator") or ""),
                "OK" if clo.get("ok") else "NO",
                _join_list(clo.get("missing_parts") or [], sep=",", limit=8),
                _join_list(it.get("flags") or [], sep="；", limit=8),
                _join_list(it.get("evidence_locators_near") or [], sep="；", limit=8),
                _clean_val(head.get("工程量") or ""),
                _clean_val(head.get("单价") or ""),
                _clean_val(head.get("合价") or ""),
                _clean_val(quant.get("频次") or ""),
                _clean_val(quant.get("阈值") or ""),
                _clean_val(quant.get("间距") or ""),
                _clean_val(quant.get("厚度") or ""),
                _clean_val(quant.get("时长") or ""),
                _clean_val(quant.get("人数") or ""),
                _clean_val(quant.get("设备型号") or ""),
                _clean_val((card or {}).get("drawing_locator") or ""),
                _clean_val((card or {}).get("standard_locator") or ""),
                _clean_val((card or {}).get("risk") or ""),
                _clean_val((card or {}).get("control") or ""),
                _clean_val((card or {}).get("verify") or ""),
                _join_list((card or {}).get("evidence_sources") or [], sep="；", limit=10),
            ]
            for c, v in enumerate(values, start=1):
                _write(ws, r, c, v)

        # Column widths (best-effort)
        _set_width(ws, 1, 26)
        _set_width(ws, 2, 18)
        _set_width(ws, 3, 18)
        for c in range(4, 9):
            _set_width(ws, c, 12)
        _set_width(ws, 9, 28)
        _set_width(ws, 10, 44)
        _set_width(ws, 11, 44)
        _set_width(ws, 12, 12)
        _set_width(ws, 13, 12)
        _set_width(ws, 14, 34)
        _set_width(ws, 15, 34)
        for c in range(16, 19):
            _set_width(ws, c, 14)
        for c in range(19, 26):
            _set_width(ws, c, 18)
        _set_width(ws, 26, 44)
        _set_width(ws, 27, 44)
        for c in range(28, 32):
            _set_width(ws, c, 44)

    # Focus cards (raw structured export)
    if focus_cards:
        ws = wb.create_sheet("focus_cards")
        headers = [
            "chapter",
            "name",
            "工程量",
            "单价",
            "合价",
            "图纸定位",
            "标准引用",
            "频次",
            "阈值",
            "间距",
            "厚度",
            "时长",
            "人数",
            "设备型号",
            "风险",
            "控制",
            "验证",
            "evidence_sources",
            "raw",
        ]
        for c, h in enumerate(headers, start=1):
            _write(ws, 1, c, h, header=True)
        for r, card in enumerate((focus_cards or [])[:600], start=2):
            if not isinstance(card, dict):
                continue
            head = card.get("head") if isinstance(card.get("head"), dict) else {}
            quant = card.get("quant") if isinstance(card.get("quant"), dict) else {}
            values = [
                str(card.get("chapter") or ""),
                str(card.get("name") or ""),
                _clean_val(head.get("工程量") or ""),
                _clean_val(head.get("单价") or ""),
                _clean_val(head.get("合价") or ""),
                _clean_val(card.get("drawing_locator") or ""),
                _clean_val(card.get("standard_locator") or ""),
                _clean_val(quant.get("频次") or ""),
                _clean_val(quant.get("阈值") or ""),
                _clean_val(quant.get("间距") or ""),
                _clean_val(quant.get("厚度") or ""),
                _clean_val(quant.get("时长") or ""),
                _clean_val(quant.get("人数") or ""),
                _clean_val(quant.get("设备型号") or ""),
                _clean_val(card.get("risk") or ""),
                _clean_val(card.get("control") or ""),
                _clean_val(card.get("verify") or ""),
                _join_list(card.get("evidence_sources") or [], sep="；", limit=12),
                str(card.get("raw") or ""),
            ]
            for c, v in enumerate(values, start=1):
                _write(ws, r, c, v)
        _set_width(ws, 1, 28)
        _set_width(ws, 2, 28)
        for c in range(3, 8):
            _set_width(ws, c, 22)
        for c in range(8, 15):
            _set_width(ws, c, 18)
        for c in range(15, 20):
            _set_width(ws, c, 70)

    # Issues
    if issues:
        ws = wb.create_sheet("issues")
        headers = ["severity", "title", "type", "problem", "suggestion"]
        for c, h in enumerate(headers, start=1):
            _write(ws, 1, c, h, header=True)
        for r, it in enumerate(issues[:800], start=2):
            if not isinstance(it, dict):
                continue
            values = [
                str(it.get("severity") or ""),
                str(it.get("title") or ""),
                str(it.get("type") or ""),
                str(it.get("problem") or ""),
                str(it.get("suggestion") or ""),
            ]
            for c, v in enumerate(values, start=1):
                _write(ws, r, c, v)
        _set_width(ws, 1, 18)
        _set_width(ws, 2, 22)
        _set_width(ws, 3, 18)
        _set_width(ws, 4, 90)
        _set_width(ws, 5, 90)

    # Auto revision suggestions (chapter-aggregated)
    if recs:
        ws = wb.create_sheet("auto_revision")
        headers = ["title", "type", "suggestion"]
        for c, h in enumerate(headers, start=1):
            _write(ws, 1, c, h, header=True)
        for r, it in enumerate(recs[:1000], start=2):
            if not isinstance(it, dict):
                continue
            values = [str(it.get("title") or ""), str(it.get("type") or ""), str(it.get("suggestion") or "")]
            for c, v in enumerate(values, start=1):
                _write(ws, r, c, v)
        _set_width(ws, 1, 22)
        _set_width(ws, 2, 22)
        _set_width(ws, 3, 110)

    wb.save(str(output_path))
    return str(output_path)


def export_autoplan_docx_from_file(json_path: str, output_path: str) -> str:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    # 若为多版本，默认导出第一个版本
    if isinstance(data, dict) and isinstance(data.get("variants"), list) and data["variants"]:
        return export_autoplan_docx(data["variants"][0], output_path)
    return export_autoplan_docx(data, output_path)


def export_scoring_evidence_overview_xlsx(data: Dict[str, Any], output_path: str) -> str:
    """
    评分点覆盖与证据引用总览
    - 评分点覆盖: score_mapping item_cards
    - 段落证据链: evidence_tracking rows
    - 评分点×证据矩阵: 便于评审定位“第几页用哪条证据响应了哪个评分点”
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except Exception:
        return ""

    evidence_tracking = data.get("evidence_tracking") if isinstance(data.get("evidence_tracking"), dict) else {}
    rows = evidence_tracking.get("rows") if isinstance(evidence_tracking.get("rows"), list) else []
    summary = evidence_tracking.get("summary") if isinstance(evidence_tracking.get("summary"), dict) else {}
    score_mapping = data.get("score_mapping") if isinstance(data.get("score_mapping"), dict) else {}
    item_cards = score_mapping.get("item_cards") if isinstance(score_mapping.get("item_cards"), list) else []
    high_risk_items = score_mapping.get("high_risk_items") if isinstance(score_mapping.get("high_risk_items"), list) else []

    def _s(v: Any) -> str:
        return str(v or "").strip()

    def _join_list(v: Any, sep: str = "；", limit: int = 20) -> str:
        if isinstance(v, list):
            out = [_s(x) for x in v if _s(x)]
            return sep.join(out[: max(1, int(limit or 1))])
        return _s(v)

    def _sheet_set_width(ws, col: int, width: float) -> None:
        try:
            ws.column_dimensions[get_column_letter(int(col))].width = float(width)
        except Exception:
            pass

    def _infer_src_type(src: str, typed: Dict[str, Any]) -> str:
        s = _s(src).lower()
        if not s:
            return ""
        graph_nodes = [_s(x) for x in (typed.get("graph_nodes") or []) if _s(x)]
        drawing_refs = [_s(x) for x in (typed.get("drawing_refs") or []) if _s(x)]
        standard_refs = [_s(x) for x in (typed.get("standard_refs") or []) if _s(x)]
        if src in drawing_refs:
            return "drawing_dxf"
        if src in standard_refs:
            return "standard"
        if src in graph_nodes or s.startswith("图谱节点:"):
            return "graph"
        return "other"

    wb = Workbook()
    hdr_font = Font(bold=True)
    hdr_fill = PatternFill("solid", fgColor="F2F2F2")
    wrap = Alignment(wrap_text=True, vertical="top")

    def _write(ws, r: int, c: int, v: Any, *, header: bool = False):
        cell = ws.cell(row=r, column=c, value=v)
        cell.alignment = wrap
        if header:
            cell.font = hdr_font
            cell.fill = hdr_fill
        return cell

    # 1) summary
    ws = wb.active
    ws.title = "summary"
    meta_rows = [
        ("topic", _s(data.get("topic"))),
        ("project_id", _s(data.get("project_id"))),
        ("paragraph_count", int(summary.get("paragraph_count") or 0)),
        ("score_point_bound_rows", int(summary.get("score_point_bound_rows") or 0)),
        ("evidence_bound_rows", int(summary.get("evidence_bound_rows") or 0)),
        ("traceable_locator_rows", int(summary.get("traceable_locator_rows") or 0)),
        ("score_item_count", len(item_cards)),
        ("high_risk_item_count", len(high_risk_items)),
    ]
    for i, (k, v) in enumerate(meta_rows, start=1):
        _write(ws, i, 1, k, header=True)
        _write(ws, i, 2, v)
    _sheet_set_width(ws, 1, 32)
    _sheet_set_width(ws, 2, 80)

    # 2) 评分点覆盖
    ws = wb.create_sheet("score_items")
    headers = [
        "item_id",
        "dimension",
        "keywords",
        "matched_keywords",
        "missing_keywords",
        "coverage_ratio",
        "estimated_score",
        "deduction_risk",
        "matched_sections",
    ]
    for c, h in enumerate(headers, start=1):
        _write(ws, 1, c, h, header=True)
    for r, it in enumerate(item_cards[:800], start=2):
        if not isinstance(it, dict):
            continue
        values = [
            _s(it.get("item_id")),
            _s(it.get("dimension")),
            _join_list(it.get("keywords"), sep="、", limit=50),
            _join_list(it.get("matched_keywords"), sep="、", limit=50),
            _join_list(it.get("missing_keywords"), sep="、", limit=50),
            it.get("coverage_ratio"),
            it.get("estimated_score"),
            it.get("deduction_risk"),
            _join_list(it.get("matched_sections"), sep="；", limit=50),
        ]
        for c, v in enumerate(values, start=1):
            _write(ws, r, c, v)
    _sheet_set_width(ws, 1, 14)
    _sheet_set_width(ws, 2, 18)
    _sheet_set_width(ws, 3, 42)
    _sheet_set_width(ws, 4, 42)
    _sheet_set_width(ws, 5, 42)
    _sheet_set_width(ws, 6, 14)
    _sheet_set_width(ws, 7, 14)
    _sheet_set_width(ws, 8, 14)
    _sheet_set_width(ws, 9, 40)

    # 3) 评分点 × 证据矩阵
    ws = wb.create_sheet("score_evidence_matrix")
    headers = [
        "score_rule_id",
        "score_dimension",
        "matched_keywords",
        "page_estimate",
        "section_title",
        "paragraph_id",
        "evidence_source",
        "evidence_type",
        "response_excerpt",
    ]
    for c, h in enumerate(headers, start=1):
        _write(ws, 1, c, h, header=True)

    row_no = 2
    for rec in rows[:8000]:
        if not isinstance(rec, dict):
            continue
        score_hits = rec.get("tender_score_points") if isinstance(rec.get("tender_score_points"), list) else []
        score_hits = score_hits or [{"rule_id": "", "dimension": "", "matched_keywords": []}]
        sources = rec.get("evidence_sources") if isinstance(rec.get("evidence_sources"), list) else []
        sources = sources or [""]
        typed = rec.get("evidence_typed") if isinstance(rec.get("evidence_typed"), dict) else {}
        excerpt = _s(rec.get("system_response"))[:400]
        for sp in score_hits:
            if not isinstance(sp, dict):
                continue
            for src in sources:
                values = [
                    _s(sp.get("rule_id")),
                    _s(sp.get("dimension")),
                    _join_list(sp.get("matched_keywords"), sep="、", limit=20),
                    rec.get("page_estimate"),
                    _s(rec.get("section_title")),
                    _s(rec.get("paragraph_id")),
                    _s(src),
                    _infer_src_type(_s(src), typed),
                    excerpt,
                ]
                for c, v in enumerate(values, start=1):
                    _write(ws, row_no, c, v)
                row_no += 1

    _sheet_set_width(ws, 1, 16)
    _sheet_set_width(ws, 2, 20)
    _sheet_set_width(ws, 3, 32)
    _sheet_set_width(ws, 4, 12)
    _sheet_set_width(ws, 5, 28)
    _sheet_set_width(ws, 6, 16)
    _sheet_set_width(ws, 7, 68)
    _sheet_set_width(ws, 8, 16)
    _sheet_set_width(ws, 9, 90)

    # 4) 段落证据链明细
    ws = wb.create_sheet("paragraph_evidence")
    headers = [
        "paragraph_id",
        "section_title",
        "paragraph_index",
        "page_estimate",
        "tender_score_points",
        "evidence_sources",
        "graph_nodes",
        "drawing_refs",
        "standard_refs",
        "other_refs",
        "system_response",
    ]
    for c, h in enumerate(headers, start=1):
        _write(ws, 1, c, h, header=True)
    for r, rec in enumerate(rows[:4000], start=2):
        if not isinstance(rec, dict):
            continue
        typed = rec.get("evidence_typed") if isinstance(rec.get("evidence_typed"), dict) else {}
        score_points = rec.get("tender_score_points") if isinstance(rec.get("tender_score_points"), list) else []
        score_text = []
        for sp in score_points:
            if not isinstance(sp, dict):
                continue
            score_text.append(f"{_s(sp.get('rule_id'))}|{_s(sp.get('dimension'))}|{_join_list(sp.get('matched_keywords'), sep='、', limit=10)}")
        values = [
            _s(rec.get("paragraph_id")),
            _s(rec.get("section_title")),
            rec.get("paragraph_index"),
            rec.get("page_estimate"),
            _join_list(score_text, sep="\n", limit=100),
            _join_list(rec.get("evidence_sources"), sep="\n", limit=100),
            _join_list(typed.get("graph_nodes"), sep="\n", limit=100),
            _join_list(typed.get("drawing_refs"), sep="\n", limit=100),
            _join_list(typed.get("standard_refs"), sep="\n", limit=100),
            _join_list(typed.get("other_refs"), sep="\n", limit=100),
            _s(rec.get("system_response"))[:800],
        ]
        for c, v in enumerate(values, start=1):
            _write(ws, r, c, v)
    _sheet_set_width(ws, 1, 16)
    _sheet_set_width(ws, 2, 24)
    _sheet_set_width(ws, 3, 10)
    _sheet_set_width(ws, 4, 10)
    _sheet_set_width(ws, 5, 48)
    _sheet_set_width(ws, 6, 48)
    _sheet_set_width(ws, 7, 36)
    _sheet_set_width(ws, 8, 36)
    _sheet_set_width(ws, 9, 36)
    _sheet_set_width(ws, 10, 36)
    _sheet_set_width(ws, 11, 90)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    return str(output_path)


def export_expert_review_brief_docx(data: Dict[str, Any], output_path: str) -> str:
    """
    10%专家复核提要版
    仅保留: 工期关键节点、资源峰值、重大安质风控、加分策略触发摘要。
    """
    style_raw = data.get("style") if isinstance(data.get("style"), dict) else {}
    style_cfg = _normalize_style(style_raw)
    doc = Document()
    _apply_page_setup(doc, style_cfg)
    apply_paragraph = _apply_style(doc, style_raw)

    topic = str(data.get("topic") or "施工组织设计").strip()
    h1 = doc.add_heading(f"{topic} - 专家复核提要版", level=1)
    apply_paragraph(h1, is_title=True)
    p_intro = doc.add_paragraph("本稿为高浓度复核摘要，仅保留关键指标、闭环措施与加分策略触发信息。")
    apply_paragraph(p_intro)

    sections = data.get("sections") if isinstance(data.get("sections"), list) else []
    quality_checks = data.get("quality_checks") if isinstance(data.get("quality_checks"), dict) else {}
    plan_consistency = data.get("plan_consistency") if isinstance(data.get("plan_consistency"), dict) else {}
    boq_wbs_cpm = data.get("boq_wbs_cpm") if isinstance(data.get("boq_wbs_cpm"), dict) else {}
    cpm = plan_consistency.get("cpm") if isinstance(plan_consistency.get("cpm"), dict) else {}
    cpm_summary = boq_wbs_cpm.get("summary") if isinstance(boq_wbs_cpm.get("summary"), dict) else {}
    cpm_critical_names = [str(x).strip() for x in (cpm_summary.get("critical_path_names") or []) if str(x).strip()]
    if not cpm_critical_names:
        cpm_critical_names = [str(x).strip() for x in (cpm.get("critical_path") or []) if str(x).strip()]

    duration_days = cpm_summary.get("project_duration_days")
    if duration_days in (None, ""):
        duration_days = ((cpm.get("computed") or {}).get("project_duration_days") if isinstance(cpm.get("computed"), dict) else None)
    resource_peak = cpm_summary.get("resource_peak")
    if resource_peak in (None, ""):
        resource_peak = ((cpm.get("computed") or {}).get("resource_peak") if isinstance(cpm.get("computed"), dict) else None)
    critical_gap = cpm_summary.get("critical_interval_days")
    if critical_gap in (None, ""):
        critical_gap = ((cpm.get("computed") or {}).get("critical_interval_days") if isinstance(cpm.get("computed"), dict) else None)

    h = doc.add_heading("1. 核心工期网络节点", level=2)
    apply_paragraph(h, is_title=True)
    for line in [
        f"- 项目总工期(天): {duration_days if duration_days not in (None, '') else '未提取'}",
        f"- 关键线路最小间隔(天): {critical_gap if critical_gap not in (None, '') else '未提取'}",
        f"- 关键线路节点: {' -> '.join(cpm_critical_names[:20]) if cpm_critical_names else '未提取'}",
    ]:
        p = doc.add_paragraph(line)
        apply_paragraph(p)

    h = doc.add_heading("2. 资源投入峰值", level=2)
    apply_paragraph(h, is_title=True)
    for line in [
        f"- 资源峰值: {resource_peak if resource_peak not in (None, '') else '未提取'}",
        f"- WBS工序数量: {len(boq_wbs_cpm.get('wbs') or []) if isinstance(boq_wbs_cpm, dict) else 0}",
    ]:
        p = doc.add_paragraph(line)
        apply_paragraph(p)

    h = doc.add_heading("3. 重大安全/质量风控闭环", level=2)
    apply_paragraph(h, is_title=True)
    issue_list = quality_checks.get("issue_list") if isinstance(quality_checks.get("issue_list"), list) else []
    picked = []
    for it in issue_list:
        if not isinstance(it, dict):
            continue
        sev = str(it.get("severity") or "").strip().lower()
        txt = f"{it.get('title') or '章节'}|{it.get('type') or ''}|{it.get('problem') or ''}|{it.get('suggestion') or ''}"
        if sev in {"high", "critical"} or ("安全" in txt) or ("质量" in txt) or ("风险" in txt):
            picked.append(it)
    if not picked:
        p = doc.add_paragraph("- 当前质量审计未检出高风险问题。")
        apply_paragraph(p)
    else:
        for it in picked[:12]:
            line = (
                f"- [{it.get('severity') or 'medium'}] {it.get('title') or '章节'}: "
                f"{it.get('problem') or ''}；建议: {it.get('suggestion') or ''}"
            )
            p = doc.add_paragraph(line)
            apply_paragraph(p)

    h = doc.add_heading("4. qt_score_booster 加分策略触发", level=2)
    apply_paragraph(h, is_title=True)
    booster_hits = []
    # 1) 从章节内容中捕捉显式触发
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip() or "章节"
        txt = str(sec.get("content") or "")
        if "qt_score_booster" in txt or "加分项" in txt or "加分策略" in txt:
            booster_hits.append(f"{title}: 命中章节文本策略标记")
        m = re.findall(r"(?:\+|加分)\s*(\d+(?:\.\d+)?)\s*分", txt)
        if m:
            booster_hits.append(f"{title}: 检测到分值表达 {','.join(m[:3])} 分")
    # 2) 从图谱调度摘要补充
    multi_agent = data.get("multi_agent") if isinstance(data.get("multi_agent"), dict) else {}
    selected_graphs = multi_agent.get("selected_graphs") if isinstance(multi_agent.get("selected_graphs"), list) else []
    for g in selected_graphs:
        if not isinstance(g, dict):
            continue
        booster = g.get("qt_score_booster") if isinstance(g.get("qt_score_booster"), dict) else {}
        if booster:
            gname = str(g.get("graph_name") or g.get("filename") or "图谱").strip()
            booster_hits.append(
                f"{gname}: {str(booster.get('strategy') or booster.get('score_weight') or booster.get('weight') or '已配置加分策略')}"
            )
    # 去重
    dedup = []
    for x in booster_hits:
        if x not in dedup:
            dedup.append(x)
    if dedup:
        for ln in dedup[:16]:
            p = doc.add_paragraph(f"- {ln}")
            apply_paragraph(p)
    else:
        p = doc.add_paragraph("- 未检测到显式 qt_score_booster 触发项（建议在图谱节点或章节中补充加分策略表达）。")
        apply_paragraph(p)

    # 10%章节摘录（供总工快速定位）
    h = doc.add_heading("5. 10%章节快速摘录", level=2)
    apply_paragraph(h, is_title=True)
    if not sections:
        p = doc.add_paragraph("- 无章节数据。")
        apply_paragraph(p)
    else:
        ranked = []
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get("title") or "").strip()
            content = str(sec.get("content") or "")
            score = 0
            for kw, w in [
                ("工期", 3),
                ("进度", 3),
                ("关键线路", 4),
                ("资源", 3),
                ("质量", 3),
                ("安全", 3),
                ("风险", 3),
                ("控制", 2),
                ("验证", 2),
            ]:
                if kw in content or kw in title:
                    score += w
            score += min(6, int(len(content) / 800))
            ranked.append((score, title, content))
        ranked.sort(key=lambda x: x[0], reverse=True)
        keep = max(1, min(12, math.ceil(len(ranked) * 0.10)))
        for _, title, content in ranked[:keep]:
            p1 = doc.add_paragraph(f"- {title}")
            apply_paragraph(p1)
            p2 = doc.add_paragraph((content[:360] + "...") if len(content) > 360 else content)
            apply_paragraph(p2)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    return str(output_path)
