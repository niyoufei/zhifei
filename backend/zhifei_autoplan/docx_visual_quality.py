from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image
from pypdf import PdfReader


_HEADING_RE = re.compile(
    r"^(?:第\s*[一二三四五六七八九十百零〇0-9]+\s*[章节篇]|"
    r"[0-9]+(?:\.[0-9]+){0,4}\s*[、.．]?\s*[\u4e00-\u9fff])"
)
_PAGE_NUMBER_RE = re.compile(r"^(?:第\s*)?[0-9一二三四五六七八九十百零〇]+(?:\s*页)?$")
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_DEFAULT_PREVIEW_PAGE_LIMIT = 8


class DocxVisualQualityError(RuntimeError):
    """Raised when the rendered Word document is unsafe to deliver."""

    def __init__(self, message: str, *, report: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.report = report or {}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.chmod(0o600)
        os.replace(temp_path, path)
        path.chmod(0o600)
    finally:
        temp_path.unlink(missing_ok=True)


def _resolve_executable(env_name: str, names: Iterable[str], candidates: Iterable[Path]) -> Path | None:
    configured = str(os.getenv(env_name) or "").strip()
    if configured:
        path = Path(configured).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return path
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return Path(resolved)
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _soffice_binary() -> Path | None:
    return _resolve_executable(
        "SOFFICE_BIN",
        ("soffice", "libreoffice"),
        (
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path(
                "/Users/fei/.cache/codex-runtimes/codex-primary-runtime/"
                "dependencies/bin/override/soffice"
            ),
        ),
    )


def _pdftoppm_binary() -> Path | None:
    return _resolve_executable(
        "PDFTOPPM_BIN",
        ("pdftoppm",),
        (Path("/opt/homebrew/bin/pdftoppm"), Path("/usr/local/bin/pdftoppm")),
    )


def _run(
    command: list[str],
    *,
    timeout: int,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout)),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise DocxVisualQualityError(f"页面渲染超时（{timeout} 秒）") from exc
    except OSError as exc:
        raise DocxVisualQualityError(f"无法启动页面渲染工具：{exc}") from exc


def _render_docx_to_pdf(source: Path, destination: Path, *, timeout: int) -> None:
    soffice = _soffice_binary()
    if soffice is None:
        raise DocxVisualQualityError("缺少 LibreOffice headless，无法执行最终 Word 页面验收")
    with tempfile.TemporaryDirectory(prefix="zhifei-lo-profile-") as profile_dir, tempfile.TemporaryDirectory(
        prefix="zhifei-lo-output-"
    ) as output_dir, tempfile.TemporaryDirectory(prefix="zhifei-fontconfig-") as fontconfig_dir:
        profile_uri = Path(profile_dir).resolve().as_uri()
        render_env = os.environ.copy()
        if platform.system() == "Darwin":
            # The bundled headless LibreOffice runtime ships with an isolated
            # Fontconfig configuration.  Without an explicit bridge to macOS
            # system fonts it writes valid Unicode into the PDF text layer but
            # renders Chinese as blank/tofu glyphs.  That can fool text-only QA.
            # Keep the delivered DOCX untouched and make the validation renderer
            # use the same installed Chinese faces that Word uses on this Mac.
            fontconfig_root = Path(fontconfig_dir)
            fontconfig_file = fontconfig_root / "fonts.conf"
            cache_dir = fontconfig_root / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            fontconfig_file.write_text(
                "\n".join(
                    (
                        '<?xml version="1.0"?>',
                        '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">',
                        "<fontconfig>",
                        "  <dir>/System/Library/Fonts</dir>",
                        "  <dir>/System/Library/Fonts/Supplemental</dir>",
                        "  <dir>/Library/Fonts</dir>",
                        f"  <cachedir>{cache_dir}</cachedir>",
                        "</fontconfig>",
                    )
                ),
                encoding="utf-8",
            )
            fontconfig_file.chmod(0o600)
            render_env["FONTCONFIG_FILE"] = str(fontconfig_file)
        completed = _run(
            [
                str(soffice),
                f"-env:UserInstallation={profile_uri}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                str(source.resolve()),
            ],
            timeout=timeout,
            env=render_env,
        )
        converted = Path(output_dir) / f"{source.stem}.pdf"
        if completed.returncode != 0 or not converted.is_file() or converted.stat().st_size == 0:
            detail = (completed.stderr or completed.stdout or "未知转换错误").strip()
            raise DocxVisualQualityError(f"Word 转 PDF 失败：{detail[:500]}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(converted, destination)


def _render_pdf_pages(pdf_path: Path, output_dir: Path, *, timeout: int) -> list[Path]:
    pdftoppm = _pdftoppm_binary()
    if pdftoppm is None:
        raise DocxVisualQualityError("缺少 pdftoppm，无法执行最终页面像素验收")
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / "page"
    completed = _run(
        [str(pdftoppm), "-gray", "-png", "-r", "72", str(pdf_path), str(prefix)],
        timeout=timeout,
    )
    pages = sorted(output_dir.glob("page-*.png"), key=_page_number_from_path)
    if completed.returncode != 0 or not pages:
        detail = (completed.stderr or completed.stdout or "未知渲染错误").strip()
        raise DocxVisualQualityError(f"PDF 页面图像生成失败：{detail[:500]}")
    return pages


def _page_number_from_path(path: Path) -> int:
    match = re.search(r"-([0-9]+)\.png$", path.name)
    return int(match.group(1)) if match else 0


def _ink_ratio(image: Image.Image, *, threshold: int = 245) -> float:
    gray = image.convert("L")
    histogram = gray.histogram()
    total = max(1, gray.width * gray.height)
    return round(sum(histogram[:threshold]) / total, 6)


def _edge_ink_ratio(image: Image.Image, *, threshold: int = 245) -> float:
    gray = image.convert("L")
    width, height = gray.size
    edge_x = max(2, int(width * 0.012))
    edge_y = max(2, int(height * 0.012))
    regions = (
        gray.crop((0, 0, edge_x, height)),
        gray.crop((width - edge_x, 0, width, height)),
        gray.crop((0, 0, width, edge_y)),
        gray.crop((0, height - edge_y, width, height)),
    )
    ink = 0
    pixels = 0
    for region in regions:
        histogram = region.histogram()
        ink += sum(histogram[:threshold])
        pixels += region.width * region.height
    return round(ink / max(1, pixels), 6)


def _normalise_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def assess_cjk_glyph_integrity(
    character_shapes: dict[str, set[str]],
    *,
    empty_glyphs: int = 0,
    inspected_glyphs: int = 0,
) -> dict[str, Any]:
    """Decide whether distinct Chinese characters collapsed to blank/tofu glyphs.

    ``character_shapes`` maps each extracted CJK character to the normalised
    bitmap hashes observed for it.  A healthy Chinese font produces many
    distinct shapes; a missing font produces either empty crops or one repeated
    replacement-box shape for many unrelated characters.
    """

    unique_characters = len(character_shapes)
    shape_characters: dict[str, set[str]] = defaultdict(set)
    for character, shapes in character_shapes.items():
        for shape in shapes:
            if shape:
                shape_characters[str(shape)].add(str(character))
    unique_shapes = len(shape_characters)
    shape_retention = round(unique_shapes / max(1, unique_characters), 4)
    largest_collision = max((len(chars) for chars in shape_characters.values()), default=0)
    empty_ratio = round(int(empty_glyphs) / max(1, int(inspected_glyphs)), 4)
    blocked = bool(
        unique_characters >= 16
        and (
            shape_retention < 0.35
            or largest_collision >= 8
            or empty_ratio > 0.2
        )
    )
    return {
        "status": "blocked" if blocked else "pass",
        "inspected_glyphs": int(inspected_glyphs),
        "empty_glyphs": int(empty_glyphs),
        "empty_glyph_ratio": empty_ratio,
        "unique_cjk_characters": unique_characters,
        "unique_glyph_shapes": unique_shapes,
        "shape_retention": shape_retention,
        "largest_shape_collision": largest_collision,
        "hard_failures": ([{"code": "CJK_GLYPH_COLLAPSE"}] if blocked else []),
    }


def _normalised_glyph_hash(image: Image.Image) -> str | None:
    gray = image.convert("L")
    mask = gray.point(lambda value: 0 if value < 220 else 255, mode="1").convert("L")
    inverted = mask.point(lambda value: 255 - value)
    bbox = inverted.getbbox()
    if bbox is None:
        return None
    glyph = inverted.crop(bbox).resize((20, 20), Image.Resampling.LANCZOS)
    return hashlib.sha256(glyph.tobytes()).hexdigest()


def _inspect_cjk_glyphs(
    pdf_path: Path,
    rendered_pages: list[Path],
    *,
    max_glyphs: int = 3000,
) -> dict[str, Any]:
    """Compare PDF Unicode characters with their actual rendered bitmaps."""

    try:
        import pdfplumber
    except Exception as exc:  # pragma: no cover - production dependency gate
        raise DocxVisualQualityError(f"缺少 pdfplumber，无法执行中文逐字形验收：{exc}") from exc

    character_shapes: dict[str, set[str]] = defaultdict(set)
    empty_glyphs = 0
    inspected = 0
    try:
        with pdfplumber.open(str(pdf_path)) as document:
            for page_index, page in enumerate(document.pages):
                if page_index >= len(rendered_pages) or inspected >= max_glyphs:
                    break
                with Image.open(rendered_pages[page_index]) as rendered:
                    width_scale = rendered.width / max(1.0, float(page.width))
                    height_scale = rendered.height / max(1.0, float(page.height))
                    for item in page.chars or []:
                        text = str(item.get("text") or "")
                        match = _CJK_CHAR_RE.search(text)
                        if not match:
                            continue
                        character = match.group(0)
                        x0 = max(0, int(float(item.get("x0") or 0) * width_scale) - 1)
                        x1 = min(
                            rendered.width,
                            int(float(item.get("x1") or 0) * width_scale) + 2,
                        )
                        top = max(0, int(float(item.get("top") or 0) * height_scale) - 1)
                        bottom = min(
                            rendered.height,
                            int(float(item.get("bottom") or 0) * height_scale) + 2,
                        )
                        inspected += 1
                        if x1 <= x0 or bottom <= top:
                            empty_glyphs += 1
                            continue
                        shape = _normalised_glyph_hash(rendered.crop((x0, top, x1, bottom)))
                        if shape is None:
                            empty_glyphs += 1
                        else:
                            character_shapes[character].add(shape)
                        if inspected >= max_glyphs:
                            break
    except DocxVisualQualityError:
        raise
    except Exception as exc:
        raise DocxVisualQualityError(f"中文逐字形验收失败：{exc}") from exc
    return assess_cjk_glyph_integrity(
        dict(character_shapes),
        empty_glyphs=empty_glyphs,
        inspected_glyphs=inspected,
    )


def _looks_like_divider_page(text: str) -> bool:
    compact = _normalise_text(text)
    if len(compact) > 120:
        return False
    return bool(re.search(r"第[一二三四五六七八九十百零〇0-9]+[章节篇]", compact))


def _orphan_heading_pages(pdf_path: Path) -> list[int]:
    """Best-effort detection of a heading stranded at the bottom of a page."""

    try:
        import pdfplumber
    except Exception:
        return []
    flagged: list[int] = []
    try:
        with pdfplumber.open(str(pdf_path)) as document:
            for page_number, page in enumerate(document.pages, start=1):
                words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
                if not words:
                    continue
                lines: dict[int, list[dict[str, Any]]] = {}
                for word in words:
                    top = int(round(float(word.get("top") or 0) / 3.0) * 3)
                    lines.setdefault(top, []).append(word)
                line_items: list[tuple[int, str]] = []
                for top, line_words in lines.items():
                    ordered = sorted(line_words, key=lambda item: float(item.get("x0") or 0))
                    text = "".join(str(item.get("text") or "") for item in ordered).strip()
                    if text:
                        line_items.append((top, text))
                if not line_items:
                    continue
                top, last_text = sorted(line_items)[-1]
                compact = _normalise_text(last_text)
                if _PAGE_NUMBER_RE.fullmatch(compact):
                    if len(line_items) < 2:
                        continue
                    top, last_text = sorted(line_items)[-2]
                    compact = _normalise_text(last_text)
                if (
                    top >= float(page.height) * 0.82
                    and len(compact) <= 48
                    and not compact.endswith(("。", "；", "，", ":", "："))
                    and _HEADING_RE.match(compact)
                ):
                    flagged.append(page_number)
    except Exception:
        # Text-position extraction is an advisory signal. Pixel/page checks still run.
        return []
    return flagged


def _select_preview_pages(page_count: int, flagged: Iterable[int], limit: int) -> list[int]:
    selected = {1, 2, page_count - 1, page_count}
    selected.update(int(page) for page in flagged)
    valid = sorted(page for page in selected if 1 <= page <= page_count)
    return valid[: max(1, int(limit))]


def evaluate_page_quality(page_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Pure decision layer used by the renderer and regression tests."""

    page_count = len(page_metrics)
    blank_pages = [int(item["page"]) for item in page_metrics if item.get("blank")]
    sparse_pages = [int(item["page"]) for item in page_metrics if item.get("sparse")]
    orphan_pages = [int(item["page"]) for item in page_metrics if item.get("orphan_heading")]
    clipping_pages = [int(item["page"]) for item in page_metrics if item.get("edge_clipping_risk")]
    sparse_budget = max(1, int(page_count * 0.04)) if page_count else 0
    excessive_sparse = len(sparse_pages) > sparse_budget
    sparse_set = set(sparse_pages)
    sparse_streaks: list[list[int]] = []
    current_streak: list[int] = []
    for page_number in range(1, page_count + 1):
        if page_number in sparse_set:
            current_streak.append(page_number)
            continue
        if len(current_streak) >= 2:
            sparse_streaks.append(current_streak)
        current_streak = []
    if len(current_streak) >= 2:
        sparse_streaks.append(current_streak)

    page_ratios: list[tuple[int, float]] = []
    for item in page_metrics:
        try:
            width = float(item.get("pixel_width") or 0)
            height = float(item.get("pixel_height") or 0)
        except (TypeError, ValueError):
            continue
        if width > 0 and height > 0:
            page_ratios.append((int(item["page"]), round(width / height, 6)))
    geometry_outliers: list[int] = []
    if page_ratios:
        baseline_ratio = sorted(ratio for _, ratio in page_ratios)[len(page_ratios) // 2]
        geometry_outliers = [
            page for page, ratio in page_ratios if abs(ratio - baseline_ratio) > 0.01
        ]
    hard_failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if blank_pages:
        hard_failures.append({"code": "BLANK_PAGES", "pages": blank_pages})
    if orphan_pages:
        hard_failures.append({"code": "ORPHAN_HEADINGS", "pages": orphan_pages})
    if excessive_sparse:
        hard_failures.append(
            {"code": "EXCESSIVE_SPARSE_PAGES", "pages": sparse_pages, "allowed": sparse_budget}
        )
    elif sparse_streaks:
        hard_failures.append(
            {"code": "CONSECUTIVE_SPARSE_PAGES", "streaks": sparse_streaks}
        )
    elif sparse_pages:
        warnings.append({"code": "SPARSE_PAGES_WITHIN_BUDGET", "pages": sparse_pages})
    if len(clipping_pages) >= 2:
        hard_failures.append({"code": "SYSTEMIC_EDGE_CLIPPING_RISK", "pages": clipping_pages})
    elif clipping_pages:
        warnings.append({"code": "EDGE_CLIPPING_RISK", "pages": clipping_pages})
    if geometry_outliers:
        hard_failures.append({"code": "INCONSISTENT_PAGE_GEOMETRY", "pages": geometry_outliers})
    return {
        "status": "blocked" if hard_failures else "pass",
        "page_count": page_count,
        "blank_pages": blank_pages,
        "sparse_pages": sparse_pages,
        "sparse_page_budget": sparse_budget,
        "orphan_heading_pages": orphan_pages,
        "edge_clipping_risk_pages": clipping_pages,
        "sparse_page_streaks": sparse_streaks,
        "page_geometry_outliers": geometry_outliers,
        "hard_failures": hard_failures,
        "warnings": warnings,
    }


def validate_docx_visual_quality(
    docx_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    render_timeout: int = 300,
    preview_page_limit: int = _DEFAULT_PREVIEW_PAGE_LIMIT,
    strict: bool = True,
) -> dict[str, Any]:
    """Render a DOCX, inspect every page, and persist auditable QA artifacts."""

    source = Path(docx_path)
    if not source.is_file() or source.stat().st_size == 0:
        raise DocxVisualQualityError(f"待验收 Word 不存在或为空：{source}")
    artifact_dir = Path(output_dir) if output_dir else source.parent / f"{source.stem}.visual_qa"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = artifact_dir / f"{source.stem}.pdf"
    receipt_path = artifact_dir / "visual_quality.json"

    try:
        _render_docx_to_pdf(source, pdf_path, timeout=render_timeout)
        reader = PdfReader(str(pdf_path))
        page_texts = [str(page.extract_text() or "") for page in reader.pages]
        if not page_texts:
            raise DocxVisualQualityError("Word 渲染结果没有任何页面")
        orphan_pages = set(_orphan_heading_pages(pdf_path))
        with tempfile.TemporaryDirectory(prefix="zhifei-page-render-") as page_dir:
            rendered_pages = _render_pdf_pages(pdf_path, Path(page_dir), timeout=render_timeout)
            if len(rendered_pages) != len(page_texts):
                raise DocxVisualQualityError(
                    f"页面计数不一致：PDF={len(page_texts)}，图像={len(rendered_pages)}"
                )
            metrics: list[dict[str, Any]] = []
            for index, image_path in enumerate(rendered_pages, start=1):
                with Image.open(image_path) as image:
                    ink = _ink_ratio(image)
                    edge_ink = _edge_ink_ratio(image)
                    width, height = image.size
                compact_text = _normalise_text(page_texts[index - 1])
                blank = len(compact_text) <= 12 and ink < 0.002
                sparse = (
                    not blank
                    and index not in {1, len(rendered_pages)}
                    and not _looks_like_divider_page(page_texts[index - 1])
                    and len(compact_text) < 100
                    and ink < 0.012
                )
                metrics.append(
                    {
                        "page": index,
                        "text_chars": len(compact_text),
                        "ink_ratio": ink,
                        "edge_ink_ratio": edge_ink,
                        "pixel_width": width,
                        "pixel_height": height,
                        "blank": blank,
                        "sparse": sparse,
                        "orphan_heading": index in orphan_pages,
                        "edge_clipping_risk": index > 1 and edge_ink > 0.035,
                    }
                )
            decision = evaluate_page_quality(metrics)
            glyph_integrity = _inspect_cjk_glyphs(pdf_path, rendered_pages)
            if glyph_integrity["status"] != "pass":
                decision["status"] = "blocked"
                decision["hard_failures"].extend(glyph_integrity["hard_failures"])
            flagged = (
                decision["blank_pages"]
                + decision["sparse_pages"]
                + decision["orphan_heading_pages"]
                + decision["edge_clipping_risk_pages"]
            )
            preview_dir = artifact_dir / "preview_pages"
            preview_dir.mkdir(parents=True, exist_ok=True)
            for page_number in _select_preview_pages(len(rendered_pages), flagged, preview_page_limit):
                source_image = rendered_pages[page_number - 1]
                shutil.copy2(source_image, preview_dir / f"page-{page_number:04d}.png")
    except DocxVisualQualityError as exc:
        report = {
            "schema": "zhifei.docx_visual_quality.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "blocked",
            "docx": str(source),
            "docx_sha256": _sha256_file(source),
            "pdf": str(pdf_path) if pdf_path.exists() else None,
            "hard_failures": [{"code": "RENDER_OR_ANALYSIS_FAILED", "message": str(exc)}],
            "warnings": [],
        }
        _atomic_write_json(receipt_path, report)
        raise DocxVisualQualityError(str(exc), report=report) from exc

    report = {
        "schema": "zhifei.docx_visual_quality.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "docx": str(source),
        "docx_sha256": _sha256_file(source),
        "pdf": str(pdf_path),
        "preview_dir": str(artifact_dir / "preview_pages"),
        "receipt": str(receipt_path),
        **decision,
        "cjk_glyph_integrity": glyph_integrity,
        "page_metrics": metrics,
    }
    _atomic_write_json(receipt_path, report)
    if strict and report["status"] != "pass":
        codes = ", ".join(str(item.get("code")) for item in report["hard_failures"])
        raise DocxVisualQualityError(f"最终 Word 页面验收未通过：{codes}", report=report)
    return report
