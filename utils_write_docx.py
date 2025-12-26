from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


def _set_paragraph(
    p,
    text,
    size_pt,
    bold=False,
    font_name="宋体",
    first_line_indent_cm=0.0,
    alignment=None,
):
    run = p.add_run(text)
    run.bold = bold
    run.font.name = font_name
    run.font.size = Pt(size_pt)

    # 设置中文字体（东亚字体）
    r = run._element
    if r.rPr is not None and r.rPr.rFonts is not None:
        r.rPr.rFonts.set(qn("w:eastAsia"), font_name)

    pf = p.paragraph_format

    # 行距：固定值 22 磅
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = Pt(22)

    # 首行缩进（正文用，标题为 0）
    if first_line_indent_cm and first_line_indent_cm > 0:
        pf.first_line_indent = Cm(first_line_indent_cm)

    # 对齐方式
    if alignment is not None:
        pf.alignment = alignment


def write_compose_to_docx(sections, style, output_path="output.docx"):
    """
    版式要求：
    - 纸张：A4
    - 页边距：上 2.5 cm，其余 2.0 cm
    - 行距：固定值 22 磅
    - 字体：宋体；标题三号（16pt，居中），正文四号（14pt，首行缩进约 2 字符）
    """
    doc = Document()

    # 页面设置：A4 + 页边距
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)

    for sec in sections:
        title = sec.get("title", "未命名章节")
        content = sec.get("content", "")

        # 标题：宋体 三号，加粗，居中，不缩进
        p_title = doc.add_paragraph()
        _set_paragraph(
            p_title,
            title,
            size_pt=16,
            bold=True,
            first_line_indent_cm=0.0,
            alignment=WD_ALIGN_PARAGRAPH.CENTER,
        )

        # 正文：宋体 四号，首行缩进约 2 字符（取 1.5cm），两端对齐
        p_body = doc.add_paragraph()
        _set_paragraph(
            p_body,
            content,
            size_pt=14,
            bold=False,
            first_line_indent_cm=1.5,
            alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
        )

    doc.save(output_path)
