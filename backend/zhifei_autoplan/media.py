from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List
import time
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import json
import re

from backend.zhifei_autoplan.engineering_graphics import render_engineering_graphic, spec_from_rows

# 设置中文字体支持，避免字体缺失警告
# macOS 使用 STHeiti/Hiragino Sans GB，Linux 使用 SimHei/WenQuanYi，最后回退到 DejaVu Sans
_CHINESE_FONTS = ["STHeiti", "Hiragino Sans GB", "Heiti TC", "Songti SC", "SimHei", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["font.sans-serif"] = _CHINESE_FONTS
plt.rcParams["axes.unicode_minus"] = False  # 正确显示负号


MEDIA_DIR = Path("backend/data/autoplan/media")


def _ensure_media_dir() -> Path:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR


def _safe_slug(text: str, limit: int = 48) -> str:
    raw = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", str(text or "").strip())
    raw = raw.strip("_")
    if not raw:
        raw = "section"
    return raw[:limit]


def _pick_cn_font(size: int):
    try:
        from PIL import ImageFont

        font_paths = [
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/Supplemental/STHeiti Medium.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Supplemental/FangSong.ttf",
            "/Library/Fonts/STFANGSO.TTF",
        ]
        for p in font_paths:
            pp = Path(p)
            if pp.exists():
                try:
                    return ImageFont.truetype(str(pp), size=size)
                except Exception:
                    continue
        return ImageFont.load_default()
    except Exception:
        return None


def _extract_key_points(content: str, limit: int = 8) -> List[str]:
    txt = str(content or "").replace("\r", "\n")
    lines = [x.strip(" ；;。,.，:：") for x in re.split(r"[\n]+", txt) if str(x).strip()]
    parts: List[str] = []
    for ln in lines:
        for seg in re.split(r"[；;。.!！?？]", ln):
            s = str(seg).strip(" ，,;；")
            if s:
                parts.append(s)
    # Prefer parameter-like phrases with numeric + unit.
    unit_pat = re.compile(r"(\d+(?:\.\d+)?)\s*(mm|cm|m|kg|t|MPa|kN|小时|天|人|台|次|%|℃|米|吨)")
    scored: List[tuple[int, str]] = []
    for p in parts:
        if len(p) < 6:
            continue
        score = 0
        if unit_pat.search(p):
            score += 3
        if any(k in p for k in ("风险", "控制", "验证", "频次", "阈值", "间距", "厚度", "时长", "人数", "设备")):
            score += 2
        if len(p) <= 36:
            score += 1
        scored.append((score, p[:42]))
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    out: List[str] = []
    seen = set()
    for _, p in scored:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
        if len(out) >= max(2, int(limit or 8)):
            break
    if not out:
        out = ["工序要点量化控制", "风险-控制-验证闭环", "证据定位与验收记录"]
    return [_clean_visual_text(item) for item in out if _clean_visual_text(item)]


def _clean_visual_text(value: Any) -> str:
    """Return bidder-facing text that is safe to place inside an image.

    Generated figures cannot render Markdown semantics and must never expose
    internal notation.  This helper deliberately preserves source numbers but
    does not invent, reinterpret, or calculate new engineering parameters.
    """
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = re.sub(r"^\s*[-*+]\s+", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = text.replace("`", "")
    text = text.replace("=>", "→").replace("->", "→")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ；;。,.，:：")


_VISUAL_CONTROL_TERMS = (
    "措施",
    "控制",
    "组织",
    "施工",
    "顺序",
    "责任",
    "频次",
    "阈值",
    "间距",
    "厚度",
    "时限",
)
_VISUAL_VERIFY_TERMS = (
    "验收",
    "检查",
    "复核",
    "记录",
    "检测",
    "试验",
    "留痕",
    "合格",
    "偏差",
    "签认",
    "关闭",
)


def _split_visual_fragments(content: str) -> List[str]:
    """Split section prose into safe, source-backed visual fragments."""
    raw = str(content or "").replace("\r", "\n")
    fragments: List[str] = []
    seen: set[str] = set()
    for part in re.split(r"[\n；;。!?\uFF01？]+", raw):
        cleaned = _clean_visual_text(part)
        if len(cleaned) < 6:
            continue
        key = re.sub(r"\s+", "", cleaned)
        if key in seen:
            continue
        seen.add(key)
        fragments.append(cleaned[:72])
    return fragments


def _visual_overlap(a: str, b: str) -> int:
    left = {char for char in str(a or "") if "\u4e00" <= char <= "\u9fff"}
    right = {char for char in str(b or "") if "\u4e00" <= char <= "\u9fff"}
    return len(left & right)


def _best_visual_fragment(point: str, fragments: List[str], terms: tuple[str, ...]) -> str:
    candidates = [item for item in fragments if any(term in item for term in terms)]
    if not candidates:
        return ""
    candidates.sort(
        key=lambda item: (
            -_visual_overlap(point, item),
            -sum(1 for term in terms if term in item),
            len(item),
        )
    )
    return _clean_visual_text(candidates[0])[:46]


def _build_visual_rows(content: str, points: List[str], limit: int = 6) -> List[Dict[str, str]]:
    """Build an evidence-oriented work/control/verification matrix.

    Explicit ``风险→控制→验证`` triples are preferred.  When the prose does
    not supply a verification rule, the figure says so instead of inventing a
    threshold, frequency, responsible party or acceptance fact.
    """
    text = str(content or "")
    rows: List[Dict[str, str]] = []
    triplet_pattern = re.compile(
        r"风险\s*[:：]\s*(?P<risk>[^\n；;]{4,90})"
        r"(?:\s*(?:→|->|=>|[,\uFF0C；;])\s*)"
        r"控制\s*[:：]\s*(?P<control>[^\n；;]{4,110})"
        r"(?:\s*(?:→|->|=>|[,\uFF0C；;])\s*)"
        r"验证\s*[:：]\s*(?P<verify>[^\n；;]{4,110})",
        re.IGNORECASE,
    )
    for match in triplet_pattern.finditer(text):
        rows.append(
            {
                "point": _clean_visual_text(match.group("risk"))[:42],
                "control": _clean_visual_text(match.group("control"))[:46],
                "verify": _clean_visual_text(match.group("verify"))[:46],
                "source_status": "explicit_triplet",
            }
        )
        if len(rows) >= max(1, int(limit or 6)):
            return rows

    fragments = _split_visual_fragments(text)
    used_points = {row["point"] for row in rows}
    for raw_point in points:
        point = _clean_visual_text(raw_point)[:42]
        if not point or point in used_points:
            continue
        control = _best_visual_fragment(point, fragments, _VISUAL_CONTROL_TERMS)
        verify = _best_visual_fragment(point, fragments, _VISUAL_VERIFY_TERMS)
        rows.append(
            {
                "point": point,
                "control": control or point,
                "verify": verify or "本章未单列验收口径，需复核补齐",
                "source_status": "source_backed" if verify else "verification_gap",
            }
        )
        used_points.add(point)
        if len(rows) >= max(1, int(limit or 6)):
            break
    if not rows:
        rows.append(
            {
                "point": "本章施工组织要求",
                "control": "正文内容不足，不自动补写技术事实",
                "verify": "生成前需依据项目文件复核补齐",
                "source_status": "content_gap",
            }
        )
    return rows


def _draw_cn_wrapped(draw, text: str, *, x: int, y: int, max_chars: int, line_h: int, fill, font) -> int:
    s = str(text or "").strip()
    if not s:
        return y
    lines = [s[i : i + max_chars] for i in range(0, len(s), max_chars)]
    yy = y
    for ln in lines:
        draw.text((x, yy), ln, fill=fill, font=font)
        yy += line_h
    return yy


def _draw_section_mindmap(title: str, points: List[str], out: Path) -> None:
    from PIL import Image, ImageDraw

    w, h = 1600, 1000
    im = Image.new("RGB", (w, h), color=(247, 250, 255))
    d = ImageDraw.Draw(im)
    f_title = _pick_cn_font(42)
    f_node = _pick_cn_font(26)
    f_small = _pick_cn_font(22)

    d.rectangle((0, 0, w, 120), fill=(14, 72, 160))
    d.text((42, 34), "施工组织设计思维导图", fill=(255, 255, 255), font=f_title)
    d.text((44, 132), f"章节：{title}", fill=(42, 65, 98), font=f_node)
    d.text((44, 168), "图中要点仅摘录自本章正文，具体参数以招标文件和图纸为准", fill=(70, 94, 128), font=f_small)

    cx, cy = w // 2, 580
    d.ellipse((cx - 160, cy - 72, cx + 160, cy + 72), fill=(233, 244, 255), outline=(25, 97, 181), width=4)
    center_title = _clean_visual_text(title)[:20]
    _draw_cn_wrapped(
        d,
        center_title,
        x=cx - 130,
        y=cy - 32,
        max_chars=10,
        line_h=32,
        fill=(18, 66, 128),
        font=f_node,
    )

    use = points[:6] if points else ["工序控制", "质量验收", "安全管理", "资源配置", "进度计划", "证据闭环"]
    n = max(1, len(use))
    r = 300
    for i, p in enumerate(use):
        ang = (2 * math.pi) * (i / n) - math.pi / 2
        x = int(cx + r * math.cos(ang))
        y = int(cy + r * math.sin(ang))
        d.line((cx, cy, x, y), fill=(121, 162, 214), width=4)
        bw, bh = 350, 96
        bx0, by0 = x - bw // 2, y - bh // 2
        bx1, by1 = bx0 + bw, by0 + bh
        d.rounded_rectangle((bx0, by0, bx1, by1), radius=16, fill=(255, 255, 255), outline=(51, 111, 184), width=3)
        _draw_cn_wrapped(d, p, x=bx0 + 16, y=by0 + 22, max_chars=14, line_h=30, fill=(27, 61, 109), font=f_small)

    im.save(out, format="PNG")


def _draw_section_control_board(title: str, points: List[str], out: Path, *, variant: int = 0) -> None:
    from PIL import Image, ImageDraw

    w, h = 1600, 1000
    im = Image.new("RGB", (w, h), color=(245, 250, 247))
    d = ImageDraw.Draw(im)
    f_title = _pick_cn_font(40)
    f_head = _pick_cn_font(27)
    f_text = _pick_cn_font(22)

    d.rectangle((0, 0, w, 120), fill=(21, 128, 61))
    d.text((42, 34), "章节控制要点索引", fill=(255, 255, 255), font=f_title)
    d.text((44, 136), f"章节：{title}", fill=(34, 74, 43), font=f_head)
    d.text((44, 172), "仅摘录正文控制要点，不新增技术参数；执行前须与招标文件、清单和图纸复核", fill=(58, 94, 64), font=f_text)

    box_x0, box_y0 = 60, 230
    box_x1, box_y1 = 1540, 930
    d.rounded_rectangle((box_x0, box_y0, box_x1, box_y1), radius=18, fill=(255, 255, 255), outline=(62, 117, 77), width=3)
    d.line((box_x0, box_y0 + 72, box_x1, box_y0 + 72), fill=(62, 117, 77), width=2)
    d.text((85, box_y0 + 22), "序号", fill=(25, 70, 34), font=f_text)
    d.text((190, box_y0 + 22), "控制要点", fill=(25, 70, 34), font=f_text)
    d.text((760, box_y0 + 22), "核验依据", fill=(25, 70, 34), font=f_text)
    d.text((1090, box_y0 + 22), "使用要求", fill=(25, 70, 34), font=f_text)
    d.text((1320, box_y0 + 22), "留痕", fill=(25, 70, 34), font=f_text)

    rows = points[:8] if points else ["关键工序参数控制", "风险源辨识与闭环", "证据定位与验收记录"]
    while len(rows) < 8:
        rows.append(f"施工控制项{len(rows)+1}")
    row_h = 78
    for i, p in enumerate(rows[:8]):
        yy = box_y0 + 78 + i * row_h
        d.line((box_x0, yy, box_x1, yy), fill=(215, 232, 220), width=1)
        d.text((92, yy + 22), str(i + 1), fill=(42, 84, 50), font=f_text)
        _draw_cn_wrapped(d, p, x=190, y=yy + 16, max_chars=24, line_h=26, fill=(30, 72, 40), font=f_text)
        d.text((760, yy + 22), "本章正文对应条款", fill=(30, 72, 40), font=f_text)
        d.text((1090, yy + 22), "实施前复核", fill=(30, 72, 40), font=f_text)
        d.text((1320, yy + 22), "按约定记录", fill=(30, 72, 40), font=f_text)

    im.save(out, format="PNG")


def _draw_section_flow(title: str, points: List[str], out: Path) -> None:
    from PIL import Image, ImageDraw

    w, h = 1600, 1000
    im = Image.new("RGB", (w, h), color=(250, 248, 255))
    d = ImageDraw.Draw(im)
    f_title = _pick_cn_font(40)
    f_text = _pick_cn_font(24)
    d.rectangle((0, 0, w, 120), fill=(99, 63, 173))
    d.text((42, 34), "施工流程与闭环图", fill=(255, 255, 255), font=f_title)
    d.text((44, 138), f"章节：{title}", fill=(74, 53, 123), font=f_text)

    nodes = ["工序输入", "过程控制", "质量验收", "风险复核", "资料归档"]
    if points:
        nodes[1] = points[0][:8] or nodes[1]
        nodes[2] = points[min(1, len(points)-1)][:8] if len(points) >= 2 else nodes[2]
    x = 100
    y = 470
    w_box = 250
    for i, n in enumerate(nodes):
        fill = (236, 228, 252) if i % 2 == 0 else (255, 255, 255)
        d.rounded_rectangle((x, y, x + w_box, y + 120), radius=16, fill=fill, outline=(109, 76, 177), width=3)
        _draw_cn_wrapped(d, n, x=x + 34, y=y + 40, max_chars=7, line_h=28, fill=(77, 52, 126), font=f_text)
        if i < len(nodes) - 1:
            d.line((x + w_box + 8, y + 60, x + w_box + 62, y + 60), fill=(109, 76, 177), width=5)
            d.polygon(
                [(x + w_box + 62, y + 60), (x + w_box + 46, y + 50), (x + w_box + 46, y + 70)],
                fill=(109, 76, 177),
            )
        x += 290
    im.save(out, format="PNG")


def _draw_section_risk_loop(title: str, points: List[str], out: Path, *, variant: int = 0) -> None:
    from PIL import Image, ImageDraw

    w, h = 1600, 1000
    im = Image.new("RGB", (w, h), color=(255, 248, 246))
    d = ImageDraw.Draw(im)
    f_title = _pick_cn_font(40)
    f_text = _pick_cn_font(24)
    d.rectangle((0, 0, w, 120), fill=(180, 66, 39))
    d.text((42, 34), "风险→控制→验证闭环图", fill=(255, 255, 255), font=f_title)
    d.text((44, 138), f"章节：{title}", fill=(116, 57, 42), font=f_text)

    d.text((44, 176), "通用闭环流程；具体阈值、频次和责任主体以本章正文及项目文件为准", fill=(116, 57, 42), font=f_text)

    nodes = ["风险识别", "措施确认", "过程检查", "复核关闭", "资料归档"]
    x = 100
    y = 470
    w_box = 250
    for i, node in enumerate(nodes):
        fill = (255, 238, 232) if i % 2 == 0 else (255, 255, 255)
        d.rounded_rectangle((x, y, x + w_box, y + 120), radius=16, fill=fill, outline=(179, 83, 52), width=3)
        _draw_cn_wrapped(d, node, x=x + 60, y=y + 42, max_chars=6, line_h=30, fill=(120, 56, 38), font=f_text)
        if i < len(nodes) - 1:
            d.line((x + w_box + 8, y + 60, x + w_box + 62, y + 60), fill=(179, 83, 52), width=5)
            d.polygon(
                [(x + w_box + 62, y + 60), (x + w_box + 46, y + 50), (x + w_box + 46, y + 70)],
                fill=(179, 83, 52),
            )
        x += 290
    im.save(out, format="PNG")


def _draw_professional_section_visual(
    title: str,
    rows: List[Dict[str, str]],
    out: Path,
    *,
    variant: int = 0,
) -> str:
    """Render a restrained blue/cyan engineering figure from section facts.

    The former generator rotated four unrelated poster styles and padded sparse
    content with invented-looking rows.  Submission figures now share one
    visual system and only display facts extracted from the section text.
    """
    from PIL import Image, ImageDraw

    width, height = 1600, 1000
    navy = (11, 76, 117)
    blue = (19, 125, 184)
    cyan = (16, 169, 221)
    pale = (232, 247, 252)
    pale_alt = (246, 251, 253)
    ink = (26, 48, 63)
    muted = (88, 111, 124)
    white = (255, 255, 255)

    image = Image.new("RGB", (width, height), color=white)
    draw = ImageDraw.Draw(image)
    font_title = _pick_cn_font(44)
    font_subtitle = _pick_cn_font(25)
    font_head = _pick_cn_font(27)
    font_text = _pick_cn_font(22)
    font_small = _pick_cn_font(19)

    cleaned_title = _clean_visual_text(title) or "施工组织章节"
    normalized_rows = [row for row in rows if isinstance(row, dict) and _clean_visual_text(row.get("point"))][:6]
    if not normalized_rows:
        normalized_rows = _build_visual_rows("", [], limit=1)

    title_texts = (
        "本章实施控制矩阵",
        "本章施工与验收路径",
        "本章证据闭环矩阵",
    )
    title_text = title_texts[int(variant or 0) % len(title_texts)]

    draw.rectangle((0, 0, width, 122), fill=navy)
    draw.rectangle((0, 122, width, 136), fill=cyan)
    draw.text((54, 34), title_text, fill=white, font=font_title)
    draw.text((56, 160), f"章节：{cleaned_title[:30]}", fill=navy, font=font_head)
    draw.text(
        (56, 204),
        "图示内容摘自本章正文；技术参数、实施边界和验收要求以项目文件为准。",
        fill=muted,
        font=font_small,
    )

    left, top, right, bottom = 56, 270, 1544, 914
    draw.rounded_rectangle((left, top, right, bottom), radius=18, fill=white, outline=blue, width=3)
    column_x = (left, 670, 1080, right)
    headers = ("工作要点", "组织与控制", "验证与留痕")
    for index, header in enumerate(headers):
        x0, x1 = column_x[index], column_x[index + 1]
        draw.rectangle((x0, top, x1, top + 78), fill=navy if index == 0 else blue)
        draw.text((x0 + 28, top + 24), header, fill=white, font=font_head)

    row_height = max(82, int((bottom - top - 78) / max(1, len(normalized_rows))))
    for row_index, row_data in enumerate(normalized_rows):
        point = _clean_visual_text(row_data.get("point"))
        control_text = _clean_visual_text(row_data.get("control"))
        verify_text = _clean_visual_text(row_data.get("verify"))
        y0 = top + 78 + row_index * row_height
        y1 = bottom if row_index == len(normalized_rows) - 1 else min(bottom, y0 + row_height)
        if row_index % 2:
            draw.rectangle((left + 2, y0, right - 2, y1), fill=pale_alt)
        draw.line((left, y0, right, y0), fill=(195, 224, 236), width=2)
        draw.ellipse((left + 24, y0 + 25, left + 52, y0 + 53), fill=cyan)
        _draw_cn_wrapped(
            draw,
            point,
            x=left + 70,
            y=y0 + 20,
            max_chars=22,
            line_h=29,
            fill=ink,
            font=font_text,
        )
        _draw_cn_wrapped(
            draw,
            control_text,
            x=column_x[1] + 28,
            y=y0 + 24,
            max_chars=15,
            line_h=29,
            fill=ink,
            font=font_text,
        )
        _draw_cn_wrapped(
            draw,
            verify_text,
            x=column_x[2] + 28,
            y=y0 + 24,
            max_chars=15,
            line_h=29,
            fill=ink,
            font=font_text,
        )

    draw.rectangle((56, 944, 1544, 948), fill=cyan)
    draw.text((56, 958), "施工组织设计 · 项目专属章节图示", fill=blue, font=font_small)
    image.save(out, format="PNG")
    return title_text


def generate_section_visuals(
    title: str,
    content: str,
    image_count: int,
    *,
    include_mindmap: bool = True,
) -> List[Dict[str, Any]]:
    """Generate project-specific PNG+SVG figures from one semantic layout model."""
    _ensure_media_dir()
    n = max(0, int(image_count or 0))
    if n <= 0:
        return []
    sec_title = str(title or "章节").strip() or "章节"
    points = _extract_key_points(content, limit=10)
    rows = _build_visual_rows(content, points, limit=6)
    slug = _safe_slug(sec_title)

    out: List[Dict[str, Any]] = []
    for i in range(n):
        kind = ("control_matrix", "delivery_path", "evidence_matrix")[i % 3]
        stem = f"sec_{slug}_{kind}_{i + 1}_{int(time.time() * 1000)}"
        png_path = MEDIA_DIR / f"{stem}.png"
        svg_path = MEDIA_DIR / f"{stem}.svg"
        try:
            if kind == "control_matrix":
                visual_title = "本章实施控制矩阵"
                graphic_rows = [
                    {"point": row.get("point"), "verify": row.get("control")}
                    for row in rows
                ]
                layout = "two_row"
            elif kind == "delivery_path":
                visual_title = "本章施工与验收路径"
                graphic_rows = [
                    {"point": row.get("point"), "verify": row.get("verify")}
                    for row in rows
                ]
                layout = "auto"
            else:
                visual_title = "本章证据闭环矩阵"
                graphic_rows = [
                    {
                        "point": row.get("point"),
                        "verify": f"{row.get('control') or ''}；{row.get('verify') or ''}".strip("；"),
                    }
                    for row in rows
                ]
                layout = "tree"
            spec = spec_from_rows(
                title=visual_title,
                subtitle=f"章节：{sec_title[:36]}",
                rows=graphic_rows,
                layout=layout,
                caption="技术参数、实施边界和验收要求以项目事实台账及正文为准",
            )
            render_receipt = render_engineering_graphic(
                spec,
                png_path=png_path,
                svg_path=svg_path,
            )
            out.append(
                {
                    "path": str(png_path),
                    "svg_path": str(svg_path),
                    "caption": f"{sec_title}—{visual_title}",
                    "source_kind": "deterministic_project_diagram",
                    "visual_kind": kind,
                    "chapter_title": sec_title,
                    "text_verified": True,
                    "source_backed_rows": sum(1 for row in rows if row.get("source_status") != "verification_gap"),
                    "verification_gaps": sum(1 for row in rows if row.get("source_status") == "verification_gap"),
                    "render_receipt": render_receipt,
                }
            )
        except Exception:
            continue
    return out


def generate_boq_chart(boq_stats: Dict[str, Any]) -> List[str]:
    _ensure_media_dir()
    paths: List[str] = []
    if not boq_stats:
        return paths
    from PIL import Image, ImageDraw

    values = (
        float(boq_stats.get("item_count") or 0),
        float(boq_stats.get("total_quantity") or 0),
        float(boq_stats.get("density") or 0),
    )
    width, height = 1600, 900
    navy = (11, 76, 117)
    blue = (19, 125, 184)
    cyan = (16, 169, 221)
    orange = (217, 121, 43)
    pale = (238, 247, 251)
    ink = (25, 49, 64)
    muted = (88, 111, 124)
    white = (255, 255, 255)
    image = Image.new("RGB", (width, height), color=(248, 251, 253))
    draw = ImageDraw.Draw(image)
    font_title = _pick_cn_font(44)
    font_subtitle = _pick_cn_font(23)
    font_label = _pick_cn_font(27)
    font_value = _pick_cn_font(50)
    font_small = _pick_cn_font(20)

    draw.rectangle((0, 0, width, 122), fill=navy)
    draw.rectangle((0, 122, width, 136), fill=cyan)
    draw.text((56, 34), "工程量清单关键指标", fill=white, font=font_title)
    draw.text((56, 164), "用于识别资源组织与重点工序；统计口径以已解析清单为准", fill=muted, font=font_subtitle)

    cards = (
        ("清单项数", values[0], "项", navy),
        ("工程量汇总", values[1], "按原清单量纲统计", blue),
        ("清单密度", values[2], "解析统计值", orange),
    )
    card_top, card_bottom = 260, 690
    gap = 36
    card_width = int((width - 112 - gap * 2) / 3)
    for index, (label, value, note, color) in enumerate(cards):
        x0 = 56 + index * (card_width + gap)
        x1 = x0 + card_width
        draw.rounded_rectangle((x0, card_top, x1, card_bottom), radius=24, fill=white, outline=color, width=4)
        draw.rectangle((x0, card_top, x1, card_top + 18), fill=color)
        draw.text((x0 + 34, card_top + 58), label, fill=ink, font=font_label)
        formatted = f"{value:,.2f}".rstrip("0").rstrip(".")
        draw.text((x0 + 34, card_top + 148), formatted, fill=color, font=font_value)
        draw.rounded_rectangle((x0 + 34, card_top + 266, x1 - 34, card_top + 338), radius=12, fill=pale)
        draw.text((x0 + 54, card_top + 289), note, fill=muted, font=font_small)

    draw.rectangle((56, 758, 1544, 762), fill=cyan)
    draw.text((56, 790), "说明：三项指标量纲不同，采用独立卡片展示，不进行同轴比较。", fill=muted, font=font_small)
    fname = f"boq_stats_{int(time.time())}.png"
    out = MEDIA_DIR / fname
    image.save(out, format="PNG")
    paths.append(str(out))
    return paths


def generate_ingested_previews(
    limit: int = 6,
    project_id: str | None = None,
    *,
    audit_path: str | Path | None = None,
) -> List[Dict[str, Any]]:
    """
    Build a deduplicated project-source gallery for formal DOCX exports.
    Sources:
    - backend/data/audit/ingest.jsonl records (latest first)
    - Prefer `preview_saved_as` generated by ingest; fallback to generate on the fly
    """
    _ensure_media_dir()
    audit_file = Path(audit_path) if audit_path is not None else Path("backend/data/audit/ingest.jsonl")
    if not audit_file.exists():
        return []

    try:
        with audit_file.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()[::-1]
    except Exception:
        return []
    site_picks: List[dict] = []
    drawing_picks: List[dict] = []
    seen_sources: set[str] = set()
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    for ln in lines:
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        filename = (rec.get("filename") or "").strip()
        if not filename:
            continue
        name = filename.lower()
        tags = {str(item).strip().lower() for item in (rec.get("tags") or []) if str(item).strip()}
        if "logo" in tags:
            continue
        is_site_photo = bool(tags.intersection({"site_photo", "site", "scene", "现场", "现场照片"}))
        suffix = Path(filename).suffix.lower()
        is_drawing = ("drawing" in tags) or any(k in filename for k in ("图", "图纸", "施工图", "平面", "剖面", "大样", "节点"))
        is_excluded = any(k in filename for k in ("招标", "招標", "清单", "工程量清单")) or any(k in name for k in ("tender", "boq"))
        if not is_site_photo and not is_drawing and suffix == ".pdf" and not is_excluded:
            is_drawing = True
        if (not is_site_photo and not is_drawing) or is_excluded:
            continue
        saved_as = rec.get("saved_as")
        if not saved_as:
            continue
        sp = Path(saved_as)
        if not sp.exists():
            continue
        source_key = str(rec.get("sha256") or "").strip() or str(sp.resolve())
        if source_key in seen_sources:
            continue
        seen_sources.add(source_key)
        rec = dict(rec)
        rec["_source_kind"] = "site_photo" if is_site_photo else "drawing"
        (site_picks if is_site_photo else drawing_picks).append(rec)

    requested = max(0, int(limit or 0))
    if requested <= 0:
        return []
    # Keep the gallery useful: real site context first, but always leave room
    # for at least two design/drawing references when available.
    site_quota = min(len(site_picks), max(1, requested - min(2, len(drawing_picks))))
    picks = site_picks[:site_quota]
    picks.extend(drawing_picks[: max(0, requested - len(picks))])
    if len(picks) < requested:
        picks.extend(site_picks[site_quota : site_quota + (requested - len(picks))])

    out_paths: List[Dict[str, Any]] = []
    for rec in picks:
        if len(out_paths) >= requested:
            break
        preview_path = rec.get("preview_saved_as")
        # On-the-fly preview (best-effort)
        saved_as = Path(rec.get("saved_as") or "")
        if not saved_as.exists():
            continue
        if not (isinstance(preview_path, str) and preview_path.strip() and Path(preview_path).exists()):
            suffix = saved_as.suffix.lower()
            safe_name = re.sub(r"[^A-Za-z0-9_\\-\\.]+", "_", (rec.get("filename") or "doc"))[:80]
            generated_preview = MEDIA_DIR / f"ingest_{str(rec.get('sha256') or '')[:8]}_{safe_name}.png"
            try:
                if suffix in {".png", ".jpg", ".jpeg"}:
                    from PIL import Image

                    with Image.open(saved_as) as im:
                        im = im.convert("RGB")
                        if im.width > 1400:
                            h = int(im.height * (1400 / max(1, im.width)))
                            im = im.resize((1400, max(1, h)))
                        im.save(generated_preview, format="PNG")
                    preview_path = str(generated_preview)
                elif suffix == ".pdf":
                    import pypdfium2 as pdfium

                    pdf = pdfium.PdfDocument(str(saved_as))
                    if len(pdf) <= 0:
                        continue
                    page = pdf[0]
                    bitmap = page.render(scale=2.0)
                    im = bitmap.to_pil()
                    try:
                        pdf.close()
                    except Exception:
                        pass
                    if im.width > 1600:
                        from PIL import Image

                        h = int(im.height * (1600 / max(1, im.width)))
                        im = im.resize((1600, max(1, h)), resample=Image.BICUBIC)
                    im.save(generated_preview, format="PNG")
                    preview_path = str(generated_preview)
            except Exception:
                continue
        if not (isinstance(preview_path, str) and Path(preview_path).exists()):
            continue

        source_kind = str(rec.get("_source_kind") or "drawing")
        filename = str(rec.get("filename") or "项目资料")
        stem = Path(filename).stem.strip()
        stem = re.sub(r"(?:\(|（)\d+(?:\)|）)$", "", stem).strip()
        if source_kind == "site_photo":
            if re.fullmatch(r"(?:DJI|IMG|DSC)[-_ ]?\d+", stem, flags=re.IGNORECASE):
                caption = "项目现场航拍"
            else:
                caption = f"项目现场：{stem or '现场实景'}"
        else:
            caption = f"项目图纸：{stem or '设计图纸'}"
        out_paths.append(
            {
                "path": str(preview_path),
                "caption": caption,
                "project_id": pid,
                # Ingested photos/drawings are trustworthy project evidence,
                # but no chapter claim is made until the exporter binds them.
                "chapter_scope": [],
                "semantic_terms": [
                    str(value).strip()
                    for value in (rec.get("tags") or [])
                    if str(value).strip()
                ] + [stem],
                "source_kind": source_kind,
                "source_sha256": str(rec.get("sha256") or ""),
                "source_filename": filename,
                "source_page": 1 if Path(filename).suffix.lower() == ".pdf" else None,
                "is_project_source": True,
                "unbound_project_source": True,
                "text_verified": True,
            }
        )
    return out_paths[:requested]


def generate_outline_mindmap(
    topic: str,
    outline: List[str],
    *,
    provider: str = "google",
    api_key: str | None = None,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    logo_path: str | None = None,
    bidder_company: str | None = None,
    logo_url: str | None = None,
    bidder_domain: str | None = None,
    fallback_to_deterministic: bool = True,
) -> Dict[str, Any] | None:
    """
    Generate a mindmap image for the tender-derived outline.
    - Prefer the configured external image provider when api_key is provided.
    - Fallback to deterministic matplotlib drawing if not.
    Returns a media dict: {"path": "...png", "caption": "..."}.
    """
    _ensure_media_dir()
    topic = str(topic or "施组方案").strip()
    outline = [str(x).strip() for x in (outline or []) if str(x).strip()][:18]
    if not outline:
        return None

    # Resolve logo (optional)
    if logo_path:
        try:
            from pathlib import Path as _P

            if not _P(str(logo_path)).exists():
                logo_path = None
        except Exception:
            logo_path = None
    if not logo_path and (bidder_company or logo_url or bidder_domain):
        try:
            from backend.zhifei_autoplan.logo_runtime import resolve_logo

            logo_path = resolve_logo(bidder_company=bidder_company, logo_url=logo_url, bidder_domain=bidder_domain)
        except Exception:
            logo_path = None

    # Try the configured external image model first.
    if api_key:
        try:
            from backend.zhifei_autoplan.image_runtime import generate_image
            from backend.zhifei_autoplan.ocr_runtime import is_tesseract_available, guess_ocr_lang

            banned = "加强、确保、严格、压实责任、形成合力、高质量推进、提高政治站位、全力以赴"
            outline_text = "；".join(outline)
            prompt = (
                "生成一张中文信息图：标题为“施工组织设计思维导图”。"
                "画面风格：白底、蓝灰线条、工程图纸风格；结构清晰。"
                f"根节点：{topic}。"
                f"一级节点（必须全部出现）：{outline_text}。"
                "每个一级节点下给出3个二级节点：量化指标、风险闭环、证据台账（用短句）。"
                f"文字要求：不得出现官话/套话，禁用词：{banned}。"
                "如果提供了公司LOGO图片，请把该LOGO放在右上角，不改变LOGO形状。"
            )
            resp = generate_image(
                provider=str(provider or "google"),
                prompt=prompt,
                api_key=str(api_key),
                model=model,
                aspect_ratio=aspect_ratio,
                input_image_paths=[logo_path] if logo_path else None,
                out_dir=str(MEDIA_DIR),
            )
            if isinstance(resp, dict) and resp.get("ok") and resp.get("paths"):
                # Optional OCR gate: if the generated image contains banned phrases, fallback to deterministic drawing.
                try:
                    if is_tesseract_available():
                        import pytesseract
                        from PIL import Image
                        from backend.zhifei_autoplan.quality_check import OFFICIALESE_PHRASES, HARD_BANNED_WORDS

                        img_path = resp["paths"][0]
                        with Image.open(img_path) as im:
                            txt = pytesseract.image_to_string(im, lang=guess_ocr_lang(prefer_chinese=True))
                        if any(p in (txt or "") for p in (OFFICIALESE_PHRASES + HARD_BANNED_WORDS)):
                            raise ValueError("banned_phrase_in_image")
                except Exception:
                    resp = None
                if resp and resp.get("paths"):
                    display_provider = "OpenAI" if str(provider or "").strip().lower() == "openai" else "Gemini"
                    return {
                        "path": resp["paths"][0],
                        "caption": f"施工组织设计思维导图（{display_provider}）",
                        "source_kind": "external_ai",
                        "text_verified": False,
                    }
        except Exception:
            pass

    if not fallback_to_deterministic:
        return None

    # Fallback: deterministic diagram (no external API)
    try:
        import math
        from PIL import Image, ImageDraw, ImageFont

        w, h = 1600, 900
        im = Image.new("RGB", (w, h), color=(255, 255, 255))
        draw = ImageDraw.Draw(im)

        # Fonts: best-effort; do not hard-fail on missing fonts.
        def _load_font(size: int):
            for name in ("PingFang SC", "Hiragino Sans GB", "STHeiti", "SimHei", "Arial Unicode MS"):
                try:
                    return ImageFont.truetype(name, size=size)
                except Exception:
                    continue
            return ImageFont.load_default()

        f_title = _load_font(44)
        f_node = _load_font(28)
        f_sub = _load_font(22)

        # Title
        draw.text((60, 40), "施工组织设计思维导图", fill=(20, 40, 70), font=f_title)
        draw.text((60, 96), topic, fill=(40, 60, 90), font=f_node)

        # Simple radial layout for chapter nodes
        cx, cy = w // 2, h // 2 + 60
        r = 260
        n = max(1, len(outline))
        for i, title in enumerate(outline):
            ang = (2 * math.pi) * (i / n) - math.pi / 2
            x = int(cx + r * math.cos(ang))
            y = int(cy + r * math.sin(ang))

            # connector
            draw.line((cx, cy, x, y), fill=(160, 190, 220), width=4)

            # node box
            box_w, box_h = 360, 120
            bx0 = x - box_w // 2
            by0 = y - box_h // 2
            bx1 = bx0 + box_w
            by1 = by0 + box_h
            draw.rounded_rectangle((bx0, by0, bx1, by1), radius=18, outline=(60, 110, 170), width=4, fill=(245, 250, 255))
            draw.text((bx0 + 16, by0 + 12), title[:14], fill=(20, 40, 70), font=f_node)
            draw.text((bx0 + 16, by0 + 56), "量化指标 | 风险闭环 | 证据台账", fill=(60, 80, 110), font=f_sub)

        # center node
        draw.ellipse((cx - 120, cy - 70, cx + 120, cy + 70), outline=(20, 80, 140), width=6, fill=(230, 245, 255))
        draw.text((cx - 92, cy - 18), "总体", fill=(20, 40, 70), font=f_node)

        # Paste logo (optional) at top-right
        if logo_path:
            try:
                from PIL import Image as PILImage

                lp = Path(logo_path)
                if lp.exists():
                    with PILImage.open(lp) as logo:
                        logo = logo.convert("RGBA")
                        # scale to fit
                        max_w = 220
                        if logo.width > max_w:
                            hh = int(logo.height * (max_w / max(1, logo.width)))
                            logo = logo.resize((max_w, max(1, hh)))
                        x0 = w - logo.width - 60
                        y0 = 40
                        im.paste(logo, (x0, y0), mask=logo)
            except Exception:
                pass

        fname = f"mindmap_{int(time.time())}.png"
        out = MEDIA_DIR / fname
        im.save(out, format="PNG")
        return {
            "path": str(out),
            "caption": "施工组织设计目录结构图（自动绘制）",
            "source_kind": "outline_mindmap",
            "text_verified": True,
        }
    except Exception:
        return None
