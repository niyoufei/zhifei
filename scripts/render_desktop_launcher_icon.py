#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ICONSET_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def vertical_gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", size, 0)
    top_layer = Image.new("RGBA", size, top + (255,))
    bottom_layer = Image.new("RGBA", size, bottom + (255,))
    mask = Image.linear_gradient("L").resize(size)
    return Image.composite(bottom_layer, top_layer, mask)


def diagonal_gloss(size: tuple[int, int]) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    w, h = size
    draw.polygon(
        [
            (0, int(h * 0.86)),
            (0, int(h * 0.68)),
            (int(w * 0.62), int(h * 0.06)),
            (int(w * 0.78), int(h * 0.06)),
        ],
        fill=(255, 255, 255, 34),
    )
    draw.polygon(
        [
            (int(w * 0.58), 0),
            (int(w * 0.92), 0),
            (w, int(h * 0.14)),
            (w, int(h * 0.28)),
        ],
        fill=(255, 255, 255, 28),
    )
    return layer.filter(ImageFilter.GaussianBlur(18))


def radial_glow(size: tuple[int, int], bbox: tuple[int, int, int, int], color: tuple[int, int, int, int], blur: int) -> Image.Image:
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(bbox, fill=color)
    return layer.filter(ImageFilter.GaussianBlur(blur))


def make_pill(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    pill = vertical_gradient(size, top, bottom)
    mask = rounded_mask(size, radius=min(size) // 2)
    shaded = Image.new("RGBA", size, (0, 0, 0, 0))
    shaded.paste(pill, (0, 0), mask)

    highlight = Image.new("RGBA", size, (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlight)
    hdraw.rounded_rectangle(
        (int(size[0] * 0.12), int(size[1] * 0.08), int(size[0] * 0.72), int(size[1] * 0.44)),
        radius=max(8, min(size) // 5),
        fill=(255, 255, 255, 70),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(max(4, size[0] // 24)))
    return Image.alpha_composite(shaded, highlight)


def paste_center(canvas: Image.Image, overlay: Image.Image, xy: tuple[int, int]) -> None:
    canvas.alpha_composite(overlay, xy)


def render_icon(size: int = 1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    outer_box = (96, 72, size - 96, size - 40)
    outer_w = outer_box[2] - outer_box[0]
    outer_h = outer_box[3] - outer_box[1]
    outer_size = (outer_w, outer_h)

    bg = vertical_gradient(outer_size, (174, 112, 82), (103, 43, 28))
    bg_mask = rounded_mask(outer_size, radius=170)
    bg_round = Image.new("RGBA", outer_size, (0, 0, 0, 0))
    bg_round.paste(bg, (0, 0), bg_mask)
    bg_round = Image.alpha_composite(bg_round, diagonal_gloss(outer_size))
    bg_round = Image.alpha_composite(
        bg_round,
        radial_glow(outer_size, (int(outer_w * 0.56), int(outer_h * 0.08), int(outer_w * 0.98), int(outer_h * 0.46)), (255, 255, 255, 62), 46),
    )
    bg_round = Image.alpha_composite(
        bg_round,
        radial_glow(outer_size, (int(outer_w * 0.1), int(outer_h * 0.58), int(outer_w * 0.76), int(outer_h * 1.08)), (68, 18, 12, 48), 72),
    )
    paste_center(canvas, bg_round, outer_box[:2])

    inner_box = (256, 168, size - 256, 636)
    inner_size = (inner_box[2] - inner_box[0], inner_box[3] - inner_box[1])
    inner_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(inner_shadow)
    shadow_draw.rounded_rectangle(
        (inner_box[0] + 8, inner_box[1] + 16, inner_box[2] + 8, inner_box[3] + 24),
        radius=108,
        fill=(60, 34, 25, 56),
    )
    inner_shadow = inner_shadow.filter(ImageFilter.GaussianBlur(28))
    canvas = Image.alpha_composite(canvas, inner_shadow)

    inner = vertical_gradient(inner_size, (255, 255, 255), (232, 236, 244))
    inner_mask = rounded_mask(inner_size, radius=104)
    inner_round = Image.new("RGBA", inner_size, (0, 0, 0, 0))
    inner_round.paste(inner, (0, 0), inner_mask)
    inner_round = Image.alpha_composite(
        inner_round,
        radial_glow(inner_size, (-30, -10, int(inner_size[0] * 0.75), int(inner_size[1] * 0.72)), (255, 255, 255, 76), 34),
    )
    inner_round = Image.alpha_composite(
        inner_round,
        radial_glow(inner_size, (int(inner_size[0] * 0.48), int(inner_size[1] * 0.48), int(inner_size[0] * 1.08), int(inner_size[1] * 1.08)), (182, 192, 208, 44), 42),
    )
    paste_center(canvas, inner_round, inner_box[:2])

    emblem = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    emblem_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    top_pill = make_pill((146, 54), (248, 250, 252), (219, 225, 233)).rotate(-58, expand=True, resample=Image.Resampling.BICUBIC)
    middle_pill = make_pill((160, 62), (250, 252, 254), (221, 226, 233)).rotate(56, expand=True, resample=Image.Resampling.BICUBIC)
    base_pill = make_pill((254, 78), (250, 251, 253), (214, 220, 228))

    top_xy = (344, 244)
    mid_xy = (454, 314)
    base_xy = (386, 490)

    for asset, xy in ((top_pill, top_xy), (middle_pill, mid_xy), (base_pill, base_xy)):
        shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        shadow.alpha_composite(asset, (xy[0] + 10, xy[1] + 14))
        shadow = shadow.filter(ImageFilter.GaussianBlur(20))
        emblem_shadow = Image.alpha_composite(emblem_shadow, Image.new("RGBA", (size, size), (0, 0, 0, 0)))
        emblem_shadow = Image.alpha_composite(emblem_shadow, ImageChops.multiply(shadow, Image.new("RGBA", (size, size), (132, 142, 160, 120))))
        emblem.alpha_composite(asset, xy)

    connector_shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    csdraw = ImageDraw.Draw(connector_shadow)
    csdraw.rounded_rectangle((438, 322, 524, 404), radius=38, fill=(128, 137, 150, 66))
    connector_shadow = connector_shadow.filter(ImageFilter.GaussianBlur(18))
    emblem_shadow = Image.alpha_composite(emblem_shadow, connector_shadow)

    connector = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(connector)
    cdraw.rounded_rectangle((444, 328, 516, 394), radius=34, fill=(244, 246, 249, 228))
    connector = connector.filter(ImageFilter.GaussianBlur(5))
    emblem = Image.alpha_composite(emblem, connector)

    bar_shadow = radial_glow((size, size), (356, 516, 710, 664), (120, 130, 144, 72), 36)
    emblem_shadow = Image.alpha_composite(emblem_shadow, bar_shadow)

    canvas = Image.alpha_composite(canvas, emblem_shadow)
    canvas = Image.alpha_composite(canvas, emblem)
    return canvas


def save_iconset(img: Image.Image, iconset_dir: Path) -> None:
    iconset_dir.mkdir(parents=True, exist_ok=True)
    for filename, target in ICONSET_SIZES:
        out = img.resize((target, target), Image.Resampling.LANCZOS)
        out.save(iconset_dir / filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a macOS launcher icon in the reference style.")
    parser.add_argument("--iconset-dir", required=True, help="Output .iconset directory")
    parser.add_argument("--preview-png", help="Optional preview PNG path")
    args = parser.parse_args()

    iconset_dir = Path(args.iconset_dir).expanduser().resolve()
    preview_png = Path(args.preview_png).expanduser().resolve() if args.preview_png else None

    img = render_icon()
    save_iconset(img, iconset_dir)
    if preview_png is not None:
        preview_png.parent.mkdir(parents=True, exist_ok=True)
        img.save(preview_png)


if __name__ == "__main__":
    main()
