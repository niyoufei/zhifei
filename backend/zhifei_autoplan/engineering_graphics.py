from __future__ import annotations

import html
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence


CANVAS_WIDTH_CM = 26.0
CANVAS_HEIGHT_CM = 15.7
DEFAULT_DPI = 300
CANVAS_WIDTH_PX = round(CANVAS_WIDTH_CM / 2.54 * DEFAULT_DPI)
CANVAS_HEIGHT_PX = round(CANVAS_HEIGHT_CM / 2.54 * DEFAULT_DPI)

PALETTE = {
    "background": "FFFFFF",
    "ink": "1A303F",
    "muted": "53656E",
    "primary": "0B4C75",
    "secondary": "137DB8",
    "accent": "10A9DD",
    "pale": "E8F5FA",
    "pale_alt": "F6FBFD",
    "danger": "B44227",
    "border": "8FB8C9",
}


@dataclass(frozen=True)
class GraphicNode:
    node_id: str
    title: str
    detail: str = ""
    status: str = "normal"


@dataclass(frozen=True)
class GraphicEdge:
    source: str
    target: str
    label: str = ""


@dataclass(frozen=True)
class GraphicSpec:
    title: str
    subtitle: str
    nodes: tuple[GraphicNode, ...]
    edges: tuple[GraphicEdge, ...] = ()
    layout: str = "auto"
    caption: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LayoutBox:
    node_id: str
    x: int
    y: int
    width: int
    height: int
    title_lines: tuple[str, ...]
    detail_lines: tuple[str, ...]

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


def _pick_cn_font(size: int):
    from PIL import ImageFont

    candidates = (
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/SimSun.ttf",
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_width(draw: Any, text: str, font: Any) -> int:
    box = draw.textbbox((0, 0), str(text or ""), font=font)
    return max(0, int(box[2] - box[0]))


def wrap_text_measured(draw: Any, text: str, *, font: Any, max_width: int, max_lines: int) -> tuple[str, ...]:
    """Wrap Chinese/mixed text by measured glyph width, never character count."""

    raw = " ".join(str(text or "").replace("\n", " ").split())
    if not raw:
        return ()
    lines: list[str] = []
    current = ""
    for char in raw:
        candidate = current + char
        if current and _text_width(draw, candidate, font) > max_width:
            lines.append(current.rstrip())
            current = char.lstrip()
            if len(lines) >= max_lines:
                break
        else:
            current = candidate
    if len(lines) < max_lines and current:
        lines.append(current.rstrip())
    consumed = "".join(lines)
    if len(consumed.replace(" ", "")) < len(raw.replace(" ", "")) and lines:
        last = lines[-1]
        while last and _text_width(draw, last + "…", font) > max_width:
            last = last[:-1]
        lines[-1] = (last.rstrip() + "…") if last else "…"
    return tuple(line for line in lines if line)


def choose_layout(node_count: int, requested: str = "auto") -> tuple[int, ...]:
    if node_count <= 0:
        return ()
    requested = str(requested or "auto").lower()
    if requested in {"tree", "org", "organization"}:
        if node_count == 1:
            return (1,)
        second = min(4, node_count - 1)
        remaining = node_count - 1 - second
        return (1, second, remaining) if remaining else (1, second)
    if requested in {"three_row", "matrix3", "three-row"}:
        # A balanced three-band layout is deliberately distinct from the
        # two-row flow and hierarchy layouts.  It is used by long-form
        # acceptance suites to exercise node sizing, routing and text wrapping
        # across a materially different geometry.
        base, remainder = divmod(node_count, 3)
        rows = tuple(base + int(index < remainder) for index in range(3))
        return tuple(value for value in rows if value)
    if requested in {"two_row", "matrix"} or node_count > 4:
        first = math.ceil(node_count / 2)
        return (first, node_count - first) if node_count - first else (first,)
    return (node_count,)


def _layout_boxes(spec: GraphicSpec, draw: Any) -> tuple[LayoutBox, ...]:
    node_count = len(spec.nodes)
    rows = choose_layout(node_count, spec.layout)
    if not rows:
        return ()
    left, right = 120, CANVAS_WIDTH_PX - 120
    top, bottom = 430, CANVAS_HEIGHT_PX - 190
    row_gap = 110
    available_h = bottom - top - row_gap * (len(rows) - 1)
    box_h = max(270, min(400, available_h // max(1, len(rows))))
    title_font = _pick_cn_font(58)
    detail_font = _pick_cn_font(44)
    boxes: list[LayoutBox] = []
    cursor = 0
    for row_index, count in enumerate(rows):
        if count <= 0:
            continue
        gap = max(80, min(150, 520 // max(1, count)))
        box_w = min(650, (right - left - gap * (count - 1)) // count)
        row_width = box_w * count + gap * (count - 1)
        start_x = (CANVAS_WIDTH_PX - row_width) // 2
        y = top + row_index * (box_h + row_gap)
        row_nodes = list(spec.nodes[cursor : cursor + count])
        if row_index % 2 == 1 and spec.layout not in {"tree", "org", "organization"}:
            row_nodes.reverse()
        for column_index, node in enumerate(row_nodes):
            x = start_x + column_index * (box_w + gap)
            title_lines = wrap_text_measured(
                draw, node.title, font=title_font, max_width=box_w - 70, max_lines=2
            )
            detail_lines = wrap_text_measured(
                draw, node.detail, font=detail_font, max_width=box_w - 70, max_lines=3
            )
            boxes.append(
                LayoutBox(
                    node_id=node.node_id,
                    x=x,
                    y=y,
                    width=box_w,
                    height=box_h,
                    title_lines=title_lines,
                    detail_lines=detail_lines,
                )
            )
        cursor += count
    # Preserve semantic order for edges even when a row is visually reversed.
    by_id = {box.node_id: box for box in boxes}
    return tuple(by_id[node.node_id] for node in spec.nodes if node.node_id in by_id)


def _boxes_overlap(left: LayoutBox, right: LayoutBox, safety: int = 20) -> bool:
    return not (
        left.right + safety <= right.x
        or right.right + safety <= left.x
        or left.bottom + safety <= right.y
        or right.bottom + safety <= left.y
    )


def _point_inside_box(point: tuple[int, int], box: LayoutBox, padding: int = 8) -> bool:
    x, y = point
    return box.x + padding < x < box.right - padding and box.y + padding < y < box.bottom - padding


def validate_layout(boxes: Sequence[LayoutBox]) -> dict[str, Any]:
    overlaps: list[tuple[str, str]] = []
    overflows: list[str] = []
    for index, box in enumerate(boxes):
        if box.x < 80 or box.y < 360 or box.right > CANVAS_WIDTH_PX - 80 or box.bottom > CANVAS_HEIGHT_PX - 120:
            overflows.append(box.node_id)
        for other in boxes[index + 1 :]:
            if _boxes_overlap(box, other):
                overlaps.append((box.node_id, other.node_id))
    return {"ok": not overlaps and not overflows, "overlaps": overlaps, "overflows": overflows}


def _edge_points(source: LayoutBox, target: LayoutBox) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    sx, sy = source.center
    tx, ty = target.center
    if abs(tx - sx) >= abs(ty - sy):
        start = (source.right, sy) if tx >= sx else (source.x, sy)
        end = (target.x, ty) if tx >= sx else (target.right, ty)
        bend = ((start[0] + end[0]) // 2, start[1])
    else:
        start = (sx, source.bottom) if ty >= sy else (sx, source.y)
        end = (tx, target.y) if ty >= sy else (tx, target.bottom)
        bend = (start[0], (start[1] + end[1]) // 2)
    return start, bend, end


def _hex_rgb(value: str) -> tuple[int, int, int]:
    clean = str(value or "000000").lstrip("#")
    return tuple(int(clean[index : index + 2], 16) for index in (0, 2, 4))


def _draw_arrow(draw: Any, points: tuple[tuple[int, int], ...], color: tuple[int, int, int]) -> None:
    draw.line(points, fill=color, width=7, joint="curve")
    x2, y2 = points[-1]
    x1, y1 = points[-2]
    angle = math.atan2(y2 - y1, x2 - x1)
    length = 24
    spread = math.pi / 7
    left = (int(x2 - length * math.cos(angle - spread)), int(y2 - length * math.sin(angle - spread)))
    right = (int(x2 - length * math.cos(angle + spread)), int(y2 - length * math.sin(angle + spread)))
    draw.polygon((points[-1], left, right), fill=color)


def _draw_centered_lines(draw: Any, box: LayoutBox, *, title_font: Any, detail_font: Any) -> None:
    title_line_h = 70
    detail_line_h = 56
    total_h = len(box.title_lines) * title_line_h + len(box.detail_lines) * detail_line_h
    if box.detail_lines:
        total_h += 20
    y = box.y + max(30, (box.height - total_h) // 2)
    for line in box.title_lines:
        width = _text_width(draw, line, title_font)
        draw.text((box.x + (box.width - width) // 2, y), line, fill=_hex_rgb(PALETTE["primary"]), font=title_font)
        y += title_line_h
    if box.detail_lines:
        y += 20
    for line in box.detail_lines:
        width = _text_width(draw, line, detail_font)
        draw.text((box.x + (box.width - width) // 2, y), line, fill=_hex_rgb(PALETTE["ink"]), font=detail_font)
        y += detail_line_h


def _svg_text(lines: Sequence[str], *, x: int, y: int, size: int, color: str, line_h: int, weight: int = 400) -> str:
    spans = []
    for index, line in enumerate(lines):
        dy = "0" if index == 0 else str(line_h)
        spans.append(f'<tspan x="{x}" dy="{dy}">{html.escape(line)}</tspan>')
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" fill="#{color}" '
        f'font-family="SimSun, STSong, Songti SC, serif" font-size="{size}" font-weight="{weight}">'
        + "".join(spans)
        + "</text>"
    )


def _render_svg(spec: GraphicSpec, boxes: Sequence[LayoutBox], path: Path) -> None:
    by_id = {box.node_id: box for box in boxes}
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH_CM}cm" height="{CANVAS_HEIGHT_CM}cm" '
        f'viewBox="0 0 {CANVAS_WIDTH_PX} {CANVAS_HEIGHT_PX}">',
        '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="5" orient="auto" '
        'markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="#137DB8"/></marker></defs>',
        f'<rect width="100%" height="100%" fill="#{PALETTE["background"]}"/>',
        f'<rect width="100%" height="230" fill="#{PALETTE["primary"]}"/>',
        _svg_text((spec.title,), x=CANVAS_WIDTH_PX // 2, y=105, size=76, color="FFFFFF", line_h=86, weight=700),
        _svg_text((spec.subtitle,), x=CANVAS_WIDTH_PX // 2, y=188, size=48, color="FFFFFF", line_h=60),
    ]
    for edge in spec.edges:
        source, target = by_id.get(edge.source), by_id.get(edge.target)
        if source is None or target is None:
            continue
        start, bend, end = _edge_points(source, target)
        points = f"{start[0]},{start[1]} {bend[0]},{bend[1]} {end[0]},{end[1]}"
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="#{PALETTE["secondary"]}" stroke-width="7" marker-end="url(#arrow)"/>'
        )
    for index, box in enumerate(boxes):
        fill = PALETTE["pale"] if index % 2 == 0 else PALETTE["pale_alt"]
        parts.append(
            f'<rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" rx="28" '
            f'fill="#{fill}" stroke="#{PALETTE["border"]}" stroke-width="5"/>'
        )
        total_h = len(box.title_lines) * 70 + len(box.detail_lines) * 56 + (20 if box.detail_lines else 0)
        y = box.y + max(30, (box.height - total_h) // 2) + 52
        parts.append(_svg_text(box.title_lines, x=box.center[0], y=y, size=58, color=PALETTE["primary"], line_h=70, weight=700))
        if box.detail_lines:
            detail_y = y + len(box.title_lines) * 70 + 18
            parts.append(_svg_text(box.detail_lines, x=box.center[0], y=detail_y, size=44, color=PALETTE["ink"], line_h=56))
    footer = spec.caption or "施工组织设计工程图示 · 程序化中文文字层"
    parts.append(_svg_text((footer,), x=CANVAS_WIDTH_PX // 2, y=CANVAS_HEIGHT_PX - 72, size=42, color=PALETTE["muted"], line_h=50))
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def render_engineering_graphic(spec: GraphicSpec, *, png_path: str | Path, svg_path: str | Path) -> dict[str, Any]:
    from PIL import Image, ImageDraw

    png_target = Path(png_path)
    svg_target = Path(svg_path)
    png_target.parent.mkdir(parents=True, exist_ok=True)
    svg_target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX), _hex_rgb(PALETTE["background"]))
    draw = ImageDraw.Draw(image)
    boxes = _layout_boxes(spec, draw)
    layout_receipt = validate_layout(boxes)
    if not layout_receipt["ok"]:
        raise ValueError(f"engineering graphic layout invalid: {layout_receipt}")
    by_id = {box.node_id: box for box in boxes}
    draw.rectangle((0, 0, CANVAS_WIDTH_PX, 230), fill=_hex_rgb(PALETTE["primary"]))
    title_font = _pick_cn_font(76)
    subtitle_font = _pick_cn_font(48)
    node_title_font = _pick_cn_font(58)
    node_detail_font = _pick_cn_font(44)
    footer_font = _pick_cn_font(42)
    title_width = _text_width(draw, spec.title, title_font)
    subtitle_width = _text_width(draw, spec.subtitle, subtitle_font)
    draw.text(((CANVAS_WIDTH_PX - title_width) // 2, 50), spec.title, fill=(255, 255, 255), font=title_font)
    draw.text(((CANVAS_WIDTH_PX - subtitle_width) // 2, 148), spec.subtitle, fill=(255, 255, 255), font=subtitle_font)
    for edge in spec.edges:
        source, target = by_id.get(edge.source), by_id.get(edge.target)
        if source is None or target is None:
            continue
        _draw_arrow(draw, _edge_points(source, target), _hex_rgb(PALETTE["secondary"]))
    for index, box in enumerate(boxes):
        fill = _hex_rgb(PALETTE["pale"] if index % 2 == 0 else PALETTE["pale_alt"])
        draw.rounded_rectangle(
            (box.x, box.y, box.right, box.bottom), radius=28, fill=fill,
            outline=_hex_rgb(PALETTE["border"]), width=5,
        )
        _draw_centered_lines(draw, box, title_font=node_title_font, detail_font=node_detail_font)
    footer = spec.caption or "施工组织设计工程图示 · 程序化中文文字层"
    footer_width = _text_width(draw, footer, footer_font)
    draw.text(((CANVAS_WIDTH_PX - footer_width) // 2, CANVAS_HEIGHT_PX - 118), footer, fill=_hex_rgb(PALETTE["muted"]), font=footer_font)
    image.save(png_target, format="PNG", dpi=(DEFAULT_DPI, DEFAULT_DPI), optimize=True)
    _render_svg(spec, boxes, svg_target)
    return {
        "status": "pass",
        "png": str(png_target),
        "svg": str(svg_target),
        "canvas_cm": [CANVAS_WIDTH_CM, CANVAS_HEIGHT_CM],
        "pixel_size": [CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX],
        "dpi": DEFAULT_DPI,
        "node_count": len(spec.nodes),
        "edge_count": len(spec.edges),
        "layout_rows": list(choose_layout(len(spec.nodes), spec.layout)),
        **layout_receipt,
    }


def spec_from_rows(
    *,
    title: str,
    subtitle: str,
    rows: Iterable[dict[str, Any]],
    layout: str = "auto",
    caption: str = "",
) -> GraphicSpec:
    normalized = [dict(row) for row in rows if isinstance(row, dict)][:8]
    nodes = tuple(
        GraphicNode(
            node_id=f"N{index + 1}",
            title=str(row.get("point") or row.get("title") or f"控制点{index + 1}"),
            detail=str(row.get("verify") or row.get("control") or row.get("detail") or ""),
        )
        for index, row in enumerate(normalized)
    )
    edges = tuple(
        GraphicEdge(source=nodes[index].node_id, target=nodes[index + 1].node_id)
        for index in range(max(0, len(nodes) - 1))
    )
    return GraphicSpec(
        title=title,
        subtitle=subtitle,
        nodes=nodes,
        edges=edges,
        layout=layout,
        caption=caption,
    )
