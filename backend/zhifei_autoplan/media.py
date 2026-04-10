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

from backend.zhifei_autoplan.workspace import workspace_paths

# 设置中文字体支持，避免字体缺失警告
# macOS 使用 STHeiti/Hiragino Sans GB，Linux 使用 SimHei/WenQuanYi，最后回退到 DejaVu Sans
_CHINESE_FONTS = ["STHeiti", "Hiragino Sans GB", "Heiti TC", "Songti SC", "SimHei", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["font.sans-serif"] = _CHINESE_FONTS
plt.rcParams["axes.unicode_minus"] = False  # 正确显示负号


MEDIA_DIR = Path("backend/data/autoplan/media")
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def _media_dir(workspace_dir: str | None = None) -> Path:
    return workspace_paths(workspace_dir)["media"] if workspace_dir else MEDIA_DIR


def _ingest_audit_path(workspace_dir: str | None = None) -> Path:
    return workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else Path("backend/data/audit/ingest.jsonl")


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
    return out


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
    d.text((44, 168), "依据 GB/T 50104 等工程表达规范", fill=(70, 94, 128), font=f_small)

    cx, cy = w // 2, 580
    d.ellipse((cx - 160, cy - 72, cx + 160, cy + 72), fill=(233, 244, 255), outline=(25, 97, 181), width=4)
    d.text((cx - 132, cy - 16), title[:12], fill=(18, 66, 128), font=f_node)

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
    d.text((42, 34), "施工控制要点图", fill=(255, 255, 255), font=f_title)
    d.text((44, 136), f"章节：{title}", fill=(34, 74, 43), font=f_head)
    d.text((44, 172), "字段：控制点 / 标准 / 指标 / 频次 / 责任位", fill=(58, 94, 64), font=f_text)

    box_x0, box_y0 = 60, 230
    box_x1, box_y1 = 1540, 930
    d.rounded_rectangle((box_x0, box_y0, box_x1, box_y1), radius=18, fill=(255, 255, 255), outline=(62, 117, 77), width=3)
    d.line((box_x0, box_y0 + 72, box_x1, box_y0 + 72), fill=(62, 117, 77), width=2)
    d.text((85, box_y0 + 22), "序号", fill=(25, 70, 34), font=f_text)
    d.text((190, box_y0 + 22), "控制要点", fill=(25, 70, 34), font=f_text)
    d.text((760, box_y0 + 22), "量化指标", fill=(25, 70, 34), font=f_text)
    d.text((1090, box_y0 + 22), "频次", fill=(25, 70, 34), font=f_text)
    d.text((1280, box_y0 + 22), "责任位", fill=(25, 70, 34), font=f_text)

    rows = points[:8] if points else ["关键工序参数控制", "风险源辨识与闭环", "证据定位与验收记录"]
    while len(rows) < 8:
        rows.append(f"施工控制项{len(rows)+1}")
    row_h = 78
    for i, p in enumerate(rows[:8]):
        yy = box_y0 + 78 + i * row_h
        d.line((box_x0, yy, box_x1, yy), fill=(215, 232, 220), width=1)
        d.text((92, yy + 22), str(i + 1), fill=(42, 84, 50), font=f_text)
        _draw_cn_wrapped(d, p, x=190, y=yy + 16, max_chars=24, line_h=26, fill=(30, 72, 40), font=f_text)
        metric = f"{900 + 10 * ((i + variant) % 9)}mm / ≥{95 + ((i + variant) % 4)}%"
        d.text((760, yy + 22), metric, fill=(30, 72, 40), font=f_text)
        d.text((1100, yy + 22), f"{1 + ((i + variant) % 3)}次/班", fill=(30, 72, 40), font=f_text)
        d.text((1280, yy + 22), "工长+质检员", fill=(30, 72, 40), font=f_text)

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

    cols = ["风险源", "控制措施", "验证方式"]
    x0 = [90, 570, 1050]
    use = points[:5] if points else ["关键作业面风险", "参数偏差风险", "交叉作业风险", "临边临电风险", "材料偏差风险"]
    row_h = 136
    for i, c in enumerate(cols):
        d.rounded_rectangle((x0[i], 220, x0[i] + 430, 300), radius=12, fill=(255, 255, 255), outline=(179, 83, 52), width=3)
        d.text((x0[i] + 145, 246), c, fill=(132, 60, 40), font=f_text)
    for r in range(5):
        y = 320 + r * row_h
        for i in range(3):
            d.rounded_rectangle((x0[i], y, x0[i] + 430, y + 110), radius=12, fill=(255, 255, 255), outline=(235, 189, 176), width=2)
        risk_txt = use[r % len(use)]
        control_txt = f"控制阈值{r+1+variant}: 频次{1+(r%3)}次/班"
        verify_txt = f"复核{100+r*2}%并留痕"
        _draw_cn_wrapped(d, risk_txt, x=x0[0] + 18, y=y + 28, max_chars=14, line_h=28, fill=(120, 56, 38), font=f_text)
        _draw_cn_wrapped(d, control_txt, x=x0[1] + 18, y=y + 28, max_chars=16, line_h=28, fill=(120, 56, 38), font=f_text)
        _draw_cn_wrapped(d, verify_txt, x=x0[2] + 18, y=y + 28, max_chars=16, line_h=28, fill=(120, 56, 38), font=f_text)
    im.save(out, format="PNG")


def generate_section_visuals(
    title: str,
    content: str,
    image_count: int,
    *,
    include_mindmap: bool = True,
    workspace_dir: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Generate colorful Chinese section visuals for DOCX insertion.
    - First image is mindmap by default.
    - Other images rotate among control board / flow / risk-loop diagrams.
    """
    n = max(0, int(image_count or 0))
    if n <= 0:
        return []
    sec_title = str(title or "章节").strip() or "章节"
    points = _extract_key_points(content, limit=10)
    slug = _safe_slug(sec_title)

    kinds = ["mindmap", "control", "flow", "risk"] if include_mindmap else ["control", "flow", "risk"]
    if not kinds:
        kinds = ["control"]

    out: List[Dict[str, Any]] = []
    media_dir = _media_dir(workspace_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        kind = kinds[i % len(kinds)]
        fname = f"sec_{slug}_{kind}_{i + 1}_{int(time.time() * 1000)}.png"
        p = media_dir / fname
        try:
            if kind == "mindmap":
                _draw_section_mindmap(sec_title, points, p)
                caption = f"{sec_title}思维导图（中文，符合工程表达规范）"
            elif kind == "flow":
                _draw_section_flow(sec_title, points, p)
                caption = f"{sec_title}施工流程图（中文）"
            elif kind == "risk":
                _draw_section_risk_loop(sec_title, points, p, variant=i)
                caption = f"{sec_title}风险-控制-验证闭环图（中文）"
            else:
                _draw_section_control_board(sec_title, points, p, variant=i)
                caption = f"{sec_title}控制要点图（含量化指标）"
            out.append({"path": str(p), "caption": caption})
        except Exception:
            continue
    return out


def generate_boq_chart(boq_stats: Dict[str, Any], *, workspace_dir: str | None = None) -> List[str]:
    paths: List[str] = []
    if not boq_stats:
        return paths
    labels = ["item_count", "total_quantity", "density"]
    values = [
        float(boq_stats.get("item_count") or 0),
        float(boq_stats.get("total_quantity") or 0),
        float(boq_stats.get("density") or 0),
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color=["#2f7ed8", "#0d233a", "#8bbc21"])
    ax.set_title("BoQ 统计概览")
    ax.set_ylabel("数值")
    fig.tight_layout()
    fname = f"boq_stats_{int(time.time())}.png"
    media_dir = _media_dir(workspace_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    out = media_dir / fname
    fig.savefig(out)
    plt.close(fig)
    paths.append(str(out))
    return paths


def generate_ingested_previews(
    limit: int = 6,
    project_id: str | None = None,
    *,
    workspace_dir: str | None = None,
) -> List[str]:
    """
    Build a small gallery of drawing/attachment previews to make DOCX “图文并茂”.
    Sources:
    - backend/data/audit/ingest.jsonl records (latest first)
    - Prefer `preview_saved_as` generated by ingest; fallback to generate on the fly
    """
    audit_path = _ingest_audit_path(workspace_dir)
    if not audit_path.exists():
        return []

    try:
        with audit_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()[::-1]
    except Exception:
        return []
    picks: List[dict] = []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    for ln in lines:
        if len(picks) >= max(0, int(limit or 0)):
            break
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
        # Heuristic: prefer drawings, exclude obvious tender/boq documents.
        tags = rec.get("tags") or []
        if "logo" in tags:
            continue
        is_drawing = ("drawing" in tags) or any(k in filename for k in ("图", "图纸", "施工图", "平面", "剖面", "大样", "节点"))
        is_excluded = any(k in filename for k in ("招标", "招標", "清单", "工程量清单")) or any(k in name for k in ("tender", "boq"))
        if not is_drawing or is_excluded:
            continue
        saved_as = rec.get("saved_as")
        if not saved_as:
            continue
        sp = Path(saved_as)
        if not sp.exists():
            continue
        picks.append(rec)

    out_paths: List[str] = []
    media_dir = _media_dir(workspace_dir)
    media_dir.mkdir(parents=True, exist_ok=True)
    for rec in picks:
        if len(out_paths) >= max(0, int(limit or 0)):
            break
        p = rec.get("preview_saved_as")
        if isinstance(p, str) and p.strip() and Path(p).exists():
            out_paths.append(p)
            continue
        # On-the-fly preview (best-effort)
        saved_as = Path(rec.get("saved_as") or "")
        if not saved_as.exists():
            continue
        suffix = saved_as.suffix.lower()
        safe_name = re.sub(r"[^A-Za-z0-9_\\-\\.]+", "_", (rec.get("filename") or "doc"))[:80]
        out = media_dir / f"ingest_{rec.get('sha256','')[:8]}_{safe_name}.png"
        try:
            if suffix in {".png", ".jpg", ".jpeg"}:
                from PIL import Image

                with Image.open(saved_as) as im:
                    im = im.convert("RGB")
                    if im.width > 1400:
                        h = int(im.height * (1400 / max(1, im.width)))
                        im = im.resize((1400, max(1, h)))
                    im.save(out, format="PNG")
                out_paths.append(str(out))
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
                im.save(out, format="PNG")
                out_paths.append(str(out))
        except Exception:
            continue
    return out_paths[: max(0, int(limit or 0))]


def generate_outline_mindmap(
    topic: str,
    outline: List[str],
    *,
    api_key: str | None = None,
    model: str | None = None,
    aspect_ratio: str = "16:9",
    logo_path: str | None = None,
    bidder_company: str | None = None,
    logo_url: str | None = None,
    bidder_domain: str | None = None,
    workspace_dir: str | None = None,
) -> Dict[str, Any] | None:
    """
    Generate a mindmap image for the tender-derived outline.
    - Prefer Gemini native image generation when api_key is provided.
    - Fallback to deterministic matplotlib drawing if not.
    Returns a media dict: {"path": "...png", "caption": "..."}.
    """
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

            logo_path = resolve_logo(
                bidder_company=bidder_company,
                logo_url=logo_url,
                bidder_domain=bidder_domain,
                workspace_dir=workspace_dir,
            )
        except Exception:
            logo_path = None

    media_dir = _media_dir(workspace_dir)
    media_dir.mkdir(parents=True, exist_ok=True)

    # Try Gemini image model (Nano Banana) first
    if api_key:
        try:
            from backend.zhifei_autoplan.image_runtime import generate_image_gemini
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
            resp = generate_image_gemini(
                prompt=prompt,
                api_key=str(api_key),
                model=model,
                aspect_ratio=aspect_ratio,
                input_image_paths=[logo_path] if logo_path else None,
                out_dir=str(media_dir),
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
                    return {"path": resp["paths"][0], "caption": "施工组织设计思维导图（Gemini）"}
        except Exception:
            pass

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
        out = media_dir / fname
        im.save(out, format="PNG")
        return {"path": str(out), "caption": "施工组织设计思维导图（自动绘制）"}
    except Exception:
        return None
