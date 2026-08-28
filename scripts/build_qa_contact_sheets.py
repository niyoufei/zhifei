#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = REPO_ROOT / "artifacts" / "qa"
RENDERED_ROOT = QA_ROOT / "rendered_final"
CONTACT_ROOT = QA_ROOT / "contact_sheets"
SAMPLES = ("sample_A", "sample_B", "sample_C", "sample_D", "sample_E")


def _page_number(path: Path) -> int:
    match = re.search(r"-([0-9]+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ):
        try:
            return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def main() -> int:
    CONTACT_ROOT.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, object]] = []
    label_font = _font(24)
    title_font = _font(30)
    columns, rows = 4, 4
    cell_width, cell_height = 500, 730
    title_height = 54
    for sample in SAMPLES:
        page_paths = sorted((RENDERED_ROOT / sample).glob("page-*.png"), key=_page_number)
        output_dir = CONTACT_ROOT / sample
        output_dir.mkdir(parents=True, exist_ok=True)
        sheets: list[str] = []
        landscape_pages: list[int] = []
        for batch_index in range(0, len(page_paths), columns * rows):
            batch = page_paths[batch_index : batch_index + columns * rows]
            canvas = Image.new(
                "RGB",
                (columns * cell_width, title_height + rows * cell_height),
                "#DCE5EA",
            )
            draw = ImageDraw.Draw(canvas)
            first_page = _page_number(batch[0])
            last_page = _page_number(batch[-1])
            draw.text(
                (18, 10),
                f"{sample} · pages {first_page:03d}–{last_page:03d}",
                fill="#173647",
                font=title_font,
            )
            for item_index, page_path in enumerate(batch):
                page_number = _page_number(page_path)
                with Image.open(page_path) as page:
                    page = page.convert("RGB")
                    if page.width > page.height:
                        landscape_pages.append(page_number)
                    thumb = ImageOps.contain(page, (cell_width - 24, cell_height - 62))
                x = (item_index % columns) * cell_width
                y = title_height + (item_index // columns) * cell_height
                draw.rectangle(
                    (x + 4, y + 4, x + cell_width - 4, y + cell_height - 4),
                    fill="#F4F7F8",
                    outline="#8FA8B4",
                    width=2,
                )
                paste_x = x + (cell_width - thumb.width) // 2
                paste_y = y + 38 + (cell_height - 50 - thumb.height) // 2
                canvas.paste(thumb, (paste_x, paste_y))
                draw.text((x + 14, y + 8), f"Page {page_number}", fill="#173647", font=label_font)
            sheet_path = output_dir / f"contact_{batch_index // (columns * rows) + 1:03d}_{first_page:03d}-{last_page:03d}.png"
            canvas.save(sheet_path, format="PNG", optimize=True)
            sheets.append(str(sheet_path))
        summary.append(
            {
                "sample": sample,
                "page_count": len(page_paths),
                "contact_sheet_count": len(sheets),
                "contact_sheets": sheets,
                "landscape_pages": sorted(set(landscape_pages)),
            }
        )
    (CONTACT_ROOT / "contact_sheet_manifest.json").write_text(
        json.dumps(
            {"schema": "zhifei.qa.contact_sheets.v1", "samples": summary},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
