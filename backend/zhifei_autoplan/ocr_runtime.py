from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

_HAN_RE = re.compile(r"[\u4e00-\u9fff]")
logger = logging.getLogger(__name__)


@dataclass
class OcrResult:
    text: str
    pages: int
    lang: str
    engine: str = "tesseract"
    error: str | None = None
    # One entry for every attempted source page, including empty/failed OCR
    # pages.  Keeping those placeholders is essential: downstream evidence
    # locators must never renumber later pages merely because an earlier page
    # contained no machine-readable text.
    page_texts: tuple[str, ...] = ()


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def guess_ocr_lang(prefer_chinese: bool = True) -> str:
    """
    Prefer Chinese+English when language packs exist; fallback to English only.
    """
    if not is_tesseract_available():
        return "eng"
    try:
        import subprocess

        proc = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (proc.stdout or "") + "\n" + (proc.stderr or "")
        langs = {ln.strip() for ln in out.splitlines() if ln.strip() and not ln.lower().startswith("list of")}
        if prefer_chinese and ("chi_sim" in langs or "chi_tra" in langs):
            if "chi_sim" in langs:
                return "chi_sim+eng"
            return "chi_tra+eng"
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(
            "ocr_language_detection_failed error_type=%s",
            type(exc).__name__,
        )
    return "eng"


def _preprocess_pil_for_ocr(im):
    # Minimal preprocessing to improve OCR robustness without adding heavy deps.
    try:
        from PIL import ImageOps

        g = im.convert("L")
        g = ImageOps.autocontrast(g)
        return g
    except (AttributeError, OSError, TypeError, ValueError):
        return im


def ocr_pdf_path(
    pdf_path: str,
    max_pages: int = 12,
    scale: float = 2.0,
    lang: str | None = None,
    stop_on_catalog: bool = True,
) -> OcrResult:
    """
    OCR a PDF file by rasterizing pages with pypdfium2 and running pytesseract.
    - Designed for scanned PDFs where text extraction returns near-empty content.
    """
    p = Path(pdf_path)
    if not p.exists():
        return OcrResult(text="", pages=0, lang=lang or "eng", error="pdf_not_found")
    if not is_tesseract_available():
        return OcrResult(text="", pages=0, lang=lang or "eng", error="tesseract_not_installed")

    try:
        import pypdfium2 as pdfium
        import pytesseract
    except Exception as e:  # noqa: BLE001 - optional native dependency boundary
        return OcrResult(text="", pages=0, lang=lang or "eng", error=f"ocr_deps_missing:{e!r}")

    use_lang = lang or guess_ocr_lang(prefer_chinese=True)

    try:
        pdf = pdfium.PdfDocument(str(p))
    except Exception as e:  # noqa: BLE001 - native PDF parser boundary
        return OcrResult(text="", pages=0, lang=use_lang, error=f"pdf_open_failed:{e!r}")

    out_parts: list[str] = []
    pages_done = 0
    try:
        total = len(pdf)
        for i in range(min(max(1, int(max_pages or 1)), total)):
            try:
                page = pdf[i]
                bitmap = page.render(scale=float(scale or 2.0))
                im = bitmap.to_pil()
                im = _preprocess_pil_for_ocr(im)
                txt = pytesseract.image_to_string(im, lang=use_lang)
                out_parts.append(str(txt or "").strip())
                pages_done += 1
                if stop_on_catalog:
                    joined = "\n".join(out_parts)
                    if (
                        "目录" in joined or "目 录" in joined or "目錄" in joined
                    ) and pages_done >= 2:
                        # 目录一般在前几页，找到后即可提前结束
                        break
            except Exception as exc:  # noqa: BLE001 - per-page OCR isolation boundary
                # Preserve the failed page's ordinal.  Omitting it would shift
                # every later OCR hit to the wrong PDF page.
                logger.warning(
                    "ocr_page_failed page=%s error_type=%s",
                    i + 1,
                    type(exc).__name__,
                )
                out_parts.append("")
                pages_done += 1
                continue
    finally:
        try:
            pdf.close()
        except Exception as exc:  # noqa: BLE001 - native close must not mask OCR result
            logger.warning(
                "ocr_pdf_close_failed error_type=%s",
                type(exc).__name__,
            )

    # Use form-feed as a page boundary so downstream evidence search can infer page numbers.
    text = "\n\n\f\n\n".join(out_parts)
    return OcrResult(
        text=text,
        pages=pages_done,
        lang=use_lang,
        error=None,
        page_texts=tuple(out_parts),
    )


def is_text_probably_scanned(text: str, min_han: int = 30, min_alnum: int = 80) -> bool:
    """
    Heuristic: if extracted text has too few meaningful characters, likely scanned PDF.
    """
    s = text or ""
    han = len(_HAN_RE.findall(s))
    alnum = len(re.findall(r"[A-Za-z0-9]", s))
    # If either Chinese or alnum is present in reasonable amount, treat as non-scanned.
    return han < int(min_han) and alnum < int(min_alnum)
