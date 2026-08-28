from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from backend.zhifei_autoplan.engineering_graphics import render_engineering_graphic, spec_from_rows

CSCEC_VI = {
    "blue": "#005BAC",
    "green": "#00A65A",
    "gray": "#6B7280",
    "line": "#334155",
    "bg": "#F5F8FA",
    "white": "#FFFFFF",
}

VISUAL_TYPES = ("样板", "流程", "思维导图", "智慧绿色四新")


def _safe_name(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", str(text or "").strip()) or "visual"


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/STFangsong.ttf",
        "/System/Library/Fonts/Supplemental/FangSong.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/Library/Fonts/STFANGSO.TTF",
    ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_arrow(draw: ImageDraw.ImageDraw, start: Tuple[int, int], end: Tuple[int, int], color: str) -> None:
    draw.line([start, end], fill=color, width=3)
    x2, y2 = end
    x1, y1 = start
    dx = x2 - x1
    dy = y2 - y1
    norm = max((dx * dx + dy * dy) ** 0.5, 1.0)
    ux, uy = dx / norm, dy / norm
    left = (x2 - int(12 * ux - 6 * uy), y2 - int(12 * uy + 6 * ux))
    right = (x2 - int(12 * ux + 6 * uy), y2 - int(12 * uy - 6 * ux))
    draw.polygon([end, left, right], fill=color)


def _blank_canvas(title: str, subtitle: str) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (1600, 1000), CSCEC_VI["bg"])
    draw = ImageDraw.Draw(img)
    title_font = _load_font(44)
    sub_font = _load_font(24)
    draw.rectangle((0, 0, 1600, 110), fill=CSCEC_VI["blue"])
    draw.text((40, 26), title, fill=CSCEC_VI["white"], font=title_font)
    draw.text((40, 126), subtitle, fill=CSCEC_VI["gray"], font=sub_font)
    return img, draw


def _draw_template(index_matrix: Dict[str, Any], output: Path) -> None:
    project = str(index_matrix.get("project_name") or "施工组织设计")
    img, draw = _blank_canvas(
        "施工样板与版式示意（GB/T 50104）",
        f"{project} | CSCEC VI蓝绿灰 | 中文仿宋优先",
    )
    font = _load_font(28)
    small = _load_font(22)
    sections = [str(item.get("dimension") or "") for item in (index_matrix.get("index_matrix") or [])][:6]
    while len(sections) < 6:
        sections.append(f"章节{len(sections)+1}")
    for i, sec in enumerate(sections):
        row = i // 3
        col = i % 3
        x = 70 + col * 500
        y = 210 + row * 320
        draw.rounded_rectangle((x, y, x + 450, y + 270), radius=20, fill=CSCEC_VI["white"], outline=CSCEC_VI["line"], width=3)
        draw.text((x + 24, y + 24), f"{i+1}. {sec}", fill=CSCEC_VI["blue"], font=font)
        draw.text((x + 24, y + 88), "动作: 执行工序控制", fill=CSCEC_VI["line"], font=small)
        draw.text((x + 24, y + 130), "参数: C30 / 900mm / 2次/班", fill=CSCEC_VI["line"], font=small)
        draw.text((x + 24, y + 172), "检查人: 质量员/安全员", fill=CSCEC_VI["green"], font=small)
        draw.text((x + 24, y + 214), "验证: 复核并留痕", fill=CSCEC_VI["gray"], font=small)
    img.save(str(output), format="PNG")


def _draw_flow(index_matrix: Dict[str, Any], output: Path) -> None:
    project = str(index_matrix.get("project_name") or "施工组织设计")
    img, draw = _blank_canvas(
        "施工流程图（样板工序）",
        f"{project} | 工序名称->参数->风险->控制->验证",
    )
    font = _load_font(28)
    nodes = ["工序名称", "参数", "风险", "控制", "验证"]
    x = 90
    y = 420
    w = 250
    h = 130
    for i, name in enumerate(nodes):
        fill = CSCEC_VI["white"] if i % 2 == 0 else "#EAF4FF"
        draw.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=fill, outline=CSCEC_VI["blue"], width=3)
        draw.text((x + 70, y + 45), name, fill=CSCEC_VI["blue"], font=font)
        if i < len(nodes) - 1:
            _draw_arrow(draw, (x + w + 10, y + h // 2), (x + w + 60, y + h // 2), CSCEC_VI["green"])
        x += 300
    img.save(str(output), format="PNG")


def _draw_mindmap(index_matrix: Dict[str, Any], output: Path) -> None:
    project = str(index_matrix.get("project_name") or "施工组织设计")
    img, draw = _blank_canvas(
        "施组思维导图",
        f"{project} | 质量/安全/进度/环保/重难点/扣分点",
    )
    title_font = _load_font(30)
    small = _load_font(22)
    cx, cy = 800, 500
    draw.ellipse((640, 430, 960, 570), fill=CSCEC_VI["white"], outline=CSCEC_VI["blue"], width=4)
    draw.text((700, 486), "施组核心", fill=CSCEC_VI["blue"], font=title_font)
    dims = [str(item.get("dimension") or "") for item in (index_matrix.get("index_matrix") or [])][:6]
    while len(dims) < 6:
        dims.append(f"维度{len(dims)+1}")
    points = [(320, 280), (320, 700), (570, 160), (1030, 160), (1280, 280), (1280, 700)]
    for dim, (x, y) in zip(dims, points):
        draw.rounded_rectangle((x - 120, y - 45, x + 120, y + 45), radius=12, fill=CSCEC_VI["white"], outline=CSCEC_VI["green"], width=3)
        draw.text((x - 40, y - 15), dim, fill=CSCEC_VI["green"], font=small)
        _draw_arrow(draw, (cx, cy), (x, y), CSCEC_VI["gray"])
    img.save(str(output), format="PNG")


def _draw_innovation(index_matrix: Dict[str, Any], output: Path) -> None:
    project = str(index_matrix.get("project_name") or "施工组织设计")
    img, draw = _blank_canvas(
        "智慧/绿色/四新专题图",
        f"{project} | 智慧工地 + 绿色施工 + 新技术新工艺新材料新设备",
    )
    font = _load_font(30)
    small = _load_font(22)
    cards = [
        ("智慧工地", "BIM+IoT联动，数据闭环"),
        ("绿色施工", "PM10/噪声/能耗指标化"),
        ("四新技术", "新技术/新工艺/新材料/新设备"),
        ("质量提升", "关键参数在线监控+复核"),
    ]
    for i, (title, desc) in enumerate(cards):
        row = i // 2
        col = i % 2
        x = 120 + col * 720
        y = 250 + row * 300
        draw.rounded_rectangle((x, y, x + 640, y + 240), radius=18, fill=CSCEC_VI["white"], outline=CSCEC_VI["blue"], width=3)
        draw.text((x + 24, y + 28), title, fill=CSCEC_VI["blue"], font=font)
        draw.text((x + 24, y + 96), desc, fill=CSCEC_VI["line"], font=small)
        draw.text((x + 24, y + 146), "标准: GB/T 50104  |  字体: 仿宋", fill=CSCEC_VI["green"], font=small)
        draw.text((x + 24, y + 186), "三步锁: 定义->分析->解决", fill=CSCEC_VI["gray"], font=small)
    img.save(str(output), format="PNG")


def _write_fallback_png(output: Path) -> None:
    data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7ZfS8AAAAASUVORK5CYII="
    )
    output.write_bytes(data)


def _extract_image_bytes(resp: Any) -> bytes | None:
    try:
        generated = getattr(resp, "generated_images", None) or getattr(resp, "images", None) or []
        for item in generated:
            image_obj = getattr(item, "image", None) or item
            raw = (
                getattr(image_obj, "image_bytes", None)
                or getattr(image_obj, "bytes", None)
                or getattr(image_obj, "data", None)
            )
            if isinstance(raw, (bytes, bytearray)) and len(raw) > 0:
                return bytes(raw)
            b64 = (
                getattr(image_obj, "image_base64", None)
                or getattr(image_obj, "b64_json", None)
                or getattr(image_obj, "base64", None)
            )
            if isinstance(b64, str) and b64.strip():
                return base64.b64decode(b64)
    except Exception:
        return None
    return None


def _try_gemini_imagen(prompt: str, output: Path, *, model: str, api_key: str | None) -> Dict[str, Any]:
    if not api_key:
        return {"ok": False, "provider": "google", "model": model, "error": "missing_api_key"}
    client = None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        if hasattr(client.models, "generate_images"):
            resp = client.models.generate_images(model=model, prompt=prompt)
            raw = _extract_image_bytes(resp)
            if raw:
                output.write_bytes(raw)
                return {"ok": True, "provider": "google", "model": model, "mode": "imagen"}
        return {"ok": False, "provider": "google", "model": model, "error": "generate_images_unavailable"}
    except Exception:
        return {
            "ok": False,
            "provider": "google",
            "model": model,
            "error": "IMAGE_PROVIDER_REQUEST_FAILED",
        }
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def _build_prompt(*, visual_type: str, index_matrix: Dict[str, Any]) -> str:
    project = str(index_matrix.get("project_name") or "施工组织设计项目")
    return (
        f"请生成{visual_type}工程图，项目={project}。"
        "要求：符合GB/T 50104建筑制图标准；VI配色采用中建蓝/绿/灰；"
        "字体采用中文仿宋；内容专业且可用于施组文档。"
    )


def _fallback_draw(visual_type: str, index_matrix: Dict[str, Any], output: Path) -> None:
    rows = []
    for index, item in enumerate(index_matrix.get("index_matrix") or []):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "point": str(item.get("dimension") or f"控制维度{index + 1}"),
                "verify": str(
                    item.get("response_strategy")
                    or item.get("evidence_requirement")
                    or "按项目事实台账复核"
                ),
            }
        )
    if not rows:
        rows = [
            {"point": "工程特点", "verify": "项目事实台账"},
            {"point": "施工准备", "verify": "资源与条件核验"},
            {"point": "过程控制", "verify": "检查检测记录"},
            {"point": "验收关闭", "verify": "责任人签认"},
        ]
    layout = "tree" if visual_type == "思维导图" else ("two_row" if len(rows) > 4 else "auto")
    spec = spec_from_rows(
        title=f"{visual_type}工程图示",
        subtitle=str(index_matrix.get("project_name") or "施工组织设计")[:36],
        rows=rows,
        layout=layout,
        caption="中文文字由程序化矢量层排版，参数以项目资料为准",
    )
    render_engineering_graphic(spec, png_path=output, svg_path=output.with_suffix(".svg"))


def generate_document_visual_assets(
    *,
    index_matrix: Dict[str, Any],
    sections: List[Dict[str, Any]],
    output_dir: Path | str,
    provider: str = "google",
    model: str = "imagen-3.0-generate-002",
    api_key: str | None = None,
) -> Dict[str, Any]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets: List[Dict[str, Any]] = []
    provider_used = provider
    model_used = model
    for idx, visual_type in enumerate(VISUAL_TYPES, start=1):
        name = _safe_name(f"{idx:02d}_{visual_type}.png")
        path = out_dir / name
        prompt = _build_prompt(visual_type=visual_type, index_matrix=index_matrix)
        result = {"ok": False, "provider": provider, "model": model, "error": "fallback_only"}
        # External image models are disabled until a dedicated image-provider
        # admission capability is implemented.  A raw caller/env key is not a
        # substitute for admission.  The deterministic engineering renderer
        # remains available and produces the deliverable asset below.
        if provider == "google" and api_key:
            result = {
                "ok": False,
                "provider": provider,
                "model": model,
                "error": "IMAGE_PROVIDER_ADMISSION_REQUIRED",
            }
        if not result.get("ok"):
            _fallback_draw(visual_type, index_matrix, path)
        assets.append(
            {
                "asset_id": f"VIS-{idx:02d}",
                "dimension": "GLOBAL",
                "visual_type": visual_type,
                "title": f"{visual_type}图",
                "caption": f"{visual_type}图（GB/T 50104, CSCEC VI蓝绿灰, 仿宋）",
                "image_path": str(path),
                "prompt": prompt,
                "generation": result,
            }
        )

    return {
        "ok": True,
        "assets": assets,
        "output_dir": str(out_dir),
        "provider": provider_used,
        "model": model_used,
        "count": len(assets),
    }
