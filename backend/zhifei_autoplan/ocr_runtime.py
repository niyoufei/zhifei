from __future__ import annotations

import hashlib
import logging
import math
import re
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_HAN_RE = re.compile(r"[\u4e00-\u9fff]")
logger = logging.getLogger(__name__)

_OCR_ENGINE = "tesseract"
_DEFAULT_PAGE_TIMEOUT_SECONDS = 45.0
_DEFAULT_ATTEMPT_TIMEOUT_SECONDS = 20.0
_MAX_PAGE_TIMEOUT_SECONDS = 60.0
_MAX_ATTEMPT_TIMEOUT_SECONDS = 30.0
_MIN_OCR_TIMEOUT_SECONDS = 0.05
_SECOND_PASS_MIN_SCALE = 3.0
_SECOND_PASS_MAX_SCALE = 3.5
_SECOND_PASS_MAX_PIXELS = 24_000_000
_MAX_DIAGNOSTIC_PAGE_NUMBERS = 64

# The fallback is deliberately fixed and small.  Sparse CAD labels commonly
# benefit from PSM 11/12, while quarter-turns recover vertical annotations.
# The enclosing per-page deadline prevents the four fallback attempts from
# multiplying into an unbounded runtime.
_SECOND_PASS_STRATEGIES: tuple[tuple[str, int], ...] = (
    ("--psm 11", 0),
    ("--psm 12", 0),
    ("--psm 11", 90),
    ("--psm 11", 270),
)


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
    # Per-page proof distinguishes successful OCR text, proven blank pages,
    # unreadable non-blank pages, and renderer/OCR failures.  Empty text alone
    # is never accepted as proof of a blank source page.
    page_statuses: tuple[str, ...] = ()
    page_image_sha256: tuple[str, ...] = ()
    # Total pages reported by the PDF renderer before ``max_pages`` is applied.
    # Strict full-page callers use this to detect a truncated declaration.
    source_pages: int | None = None
    # Bounded operational evidence only.  It must never contain OCR body text,
    # raw stderr, exception reprs, source paths, or other unbounded payloads.
    diagnostics: dict[str, Any] = field(default_factory=dict)


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def _available_tesseract_languages() -> set[str] | None:
    """Return installed language identifiers without exposing command output."""

    if not is_tesseract_available():
        return set()
    try:
        proc = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return {
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.lower().startswith("list of")
    }


def guess_ocr_lang(prefer_chinese: bool = True) -> str:
    """
    Prefer Chinese+English and fail closed later when the preferred pack is absent.

    Returning the requested Chinese profile is intentional: callers that need
    Chinese construction-document OCR must not silently relabel an English-only
    attempt as complete evidence.  ``ocr_pdf_path`` validates the installed
    packs before launching OCR and emits ``OCR_LANGUAGE_UNAVAILABLE``.
    """
    langs = _available_tesseract_languages()
    if langs is None:
        logger.warning(
            "ocr_language_detection_failed machine_code=%s",
            "OCR_LANGUAGE_LIST_UNAVAILABLE",
        )
        return "chi_sim+eng" if prefer_chinese else "eng"
    if prefer_chinese and ("chi_sim" in langs or "chi_tra" in langs):
        if "chi_sim" in langs:
            return "chi_sim+eng"
        return "chi_tra+eng"
    if prefer_chinese:
        return "chi_sim+eng"
    return "eng"


def _preprocess_pil_for_ocr(im):
    # Minimal preprocessing to improve OCR robustness without adding heavy deps.
    grayscale = None
    try:
        from PIL import ImageOps

        grayscale = im.convert("L")
        prepared = ImageOps.autocontrast(grayscale)
        if prepared is not grayscale and grayscale is not im:
            _safe_close(grayscale)
        return prepared
    except (AttributeError, OSError, TypeError, ValueError):
        if grayscale is not None and grayscale is not im:
            _safe_close(grayscale)
        return im


def _image_sha256(image) -> str:
    """Hash rendered pixels so a blank/text page status has source proof."""

    try:
        mode = str(getattr(image, "mode", ""))
        size = tuple(getattr(image, "size", ()))
        pixels = image.tobytes()
    except (AttributeError, OSError, TypeError, ValueError):
        return ""
    payload = f"{mode}:{size}".encode() + b"\0" + pixels
    return hashlib.sha256(payload).hexdigest()


def _is_proven_blank_image(image) -> bool:
    """Return True only for a rendered page with a negligible ink ratio."""

    grayscale = None
    try:
        grayscale = image.convert("L")
        histogram = grayscale.histogram()
        total = sum(int(value) for value in histogram)
        if total <= 0:
            return False
        # Pixels below 245 are treated as ink.  A tiny amount of raster noise
        # is tolerated, but a non-blank page with failed OCR remains unreadable.
        ink = sum(int(value) for value in histogram[:245])
        return (ink / total) <= 0.0001
    except (AttributeError, OSError, TypeError, ValueError):
        return False
    finally:
        if grayscale is not None and grayscale is not image:
            _safe_close(grayscale)


def _bounded_timeout(value: Any, *, default: float, maximum: float) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        normalized = default
    if not math.isfinite(normalized) or normalized <= 0:
        normalized = default
    return min(max(normalized, _MIN_OCR_TIMEOUT_SECONDS), maximum)


def _safe_close(*resources: Any) -> None:
    """Best-effort close for native PDF/PIL resources without masking results."""

    seen: set[int] = set()
    for resource in resources:
        if resource is None or id(resource) in seen:
            continue
        seen.add(id(resource))
        close = getattr(resource, "close", None)
        if not callable(close):
            continue
        try:
            close()
        except Exception as exc:  # noqa: BLE001 - cleanup isolation boundary
            logger.warning(
                "ocr_resource_close_failed error_type=%s",
                type(exc).__name__,
            )


def _classify_ocr_exception(exc: Exception) -> str:
    """Map provider exceptions to stable codes without returning raw messages."""

    class_name = type(exc).__name__.lower()
    message = str(exc).lower()
    if (
        isinstance(exc, TimeoutError)
        or "timeout" in class_name
        or "timed out" in message
        or "process timeout" in message
    ):
        return "ocr_page_timeout"
    if (
        "failed loading language" in message
        or "couldn't load any languages" in message
        or "could not initialize tesseract" in message
        or "error opening data file" in message
        or "traineddata" in message
    ):
        return "ocr_language_unavailable"
    if "tesseractnotfound" in class_name or "not installed" in message:
        return "tesseract_not_installed"
    return "ocr_engine_failed"


def _invoke_tesseract(
    pytesseract: Any,
    image: Any,
    *,
    lang: str,
    config: str,
    deadline: float,
    attempt_timeout_seconds: float,
) -> tuple[str, str | None]:
    """Run one OCR child process within both attempt and page deadlines."""

    remaining = deadline - time.monotonic()
    if remaining < _MIN_OCR_TIMEOUT_SECONDS:
        return "", "ocr_page_timeout"
    timeout = min(attempt_timeout_seconds, remaining)
    try:
        text = pytesseract.image_to_string(
            image,
            lang=lang,
            config=config,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - external OCR process boundary
        return "", _classify_ocr_exception(exc)
    return str(text or "").strip(), None


def _second_pass_scale(image: Any, base_scale: float) -> float:
    """Choose a higher scale while capping the rendered pixel allocation."""

    requested = min(
        max(base_scale * 1.5, _SECOND_PASS_MIN_SCALE),
        _SECOND_PASS_MAX_SCALE,
    )
    try:
        width, height = image.size
        pixels = max(1, int(width) * int(height))
    except (AttributeError, TypeError, ValueError):
        return requested
    permitted_factor = math.sqrt(_SECOND_PASS_MAX_PIXELS / pixels)
    return max(base_scale, min(requested, base_scale * permitted_factor))


def _rotate_for_ocr(image: Any, degrees: int) -> Any | None:
    if not degrees:
        return image
    rotate = getattr(image, "rotate", None)
    if not callable(rotate):
        return None
    try:
        return rotate(degrees, expand=True, fillcolor=255)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _run_second_pass(
    *,
    page: Any,
    source_image: Any,
    base_scale: float,
    pytesseract: Any,
    lang: str,
    deadline: float,
    attempt_timeout_seconds: float,
) -> tuple[str, str | None]:
    """Bounded sparse/CAD recovery pass; empty success is still unreadable."""

    bitmap = None
    high_res_image = None
    prepared = None
    try:
        scale = _second_pass_scale(source_image, base_scale)
        if scale > base_scale + 0.01:
            if deadline - time.monotonic() < _MIN_OCR_TIMEOUT_SECONDS:
                return "", "ocr_page_timeout"
            bitmap = page.render(scale=scale)
            high_res_image = bitmap.to_pil()
        else:
            high_res_image = source_image
        prepared = _preprocess_pil_for_ocr(high_res_image)
        for config, degrees in _SECOND_PASS_STRATEGIES:
            candidate = _rotate_for_ocr(prepared, degrees)
            if candidate is None:
                continue
            try:
                text, error_code = _invoke_tesseract(
                    pytesseract,
                    candidate,
                    lang=lang,
                    config=config,
                    deadline=deadline,
                    attempt_timeout_seconds=attempt_timeout_seconds,
                )
            finally:
                if candidate is not prepared:
                    _safe_close(candidate)
            if text:
                return text, None
            if error_code is not None:
                return "", error_code
        return "", None
    except Exception as exc:  # noqa: BLE001 - native rerender isolation boundary
        return "", _classify_ocr_exception(exc)
    finally:
        closable_prepared = prepared if prepared is not high_res_image else None
        closable_high_res = (
            high_res_image if high_res_image is not source_image else None
        )
        _safe_close(
            closable_prepared,
            closable_high_res,
            bitmap,
        )


def _bounded_page_numbers(values: list[int] | tuple[int, ...]) -> list[int]:
    return sorted({int(value) for value in values if int(value) >= 1})[
        :_MAX_DIAGNOSTIC_PAGE_NUMBERS
    ]


def _diagnostics(
    *,
    lang: str,
    declared_pages: int | None,
    statuses: list[str] | tuple[str, ...] = (),
    error_code: str,
    recovered_pages: list[int] | tuple[int, ...] = (),
) -> dict[str, Any]:
    """Create a small, text-free diagnostics object safe for persistence."""

    normalized_statuses = tuple(str(status or "")[:24] for status in statuses)
    counts = Counter(normalized_statuses)
    machine_codes = {
        "none": "OCR_COMPLETE",
        "pdf_not_found": "OCR_PDF_NOT_FOUND",
        "tesseract_not_installed": "OCR_ENGINE_UNAVAILABLE",
        "ocr_dependencies_unavailable": "OCR_DEPENDENCIES_UNAVAILABLE",
        "pdf_open_failed": "OCR_PDF_OPEN_FAILED",
        "ocr_language_list_unavailable": "OCR_LANGUAGE_LIST_UNAVAILABLE",
        "ocr_language_unavailable": "OCR_LANGUAGE_UNAVAILABLE",
        "ocr_page_timeout": "OCR_PAGE_TIMEOUT",
        "ocr_engine_failed": "OCR_ENGINE_FAILED",
        "ocr_zero_text_nonblank": "OCR_NONBLANK_ZERO_TEXT",
        "page_ocr_incomplete": "OCR_PAGE_PROOF_INCOMPLETE",
    }
    all_page_lists = {
        "unreadable_pages": [
            index
            for index, status in enumerate(normalized_statuses, start=1)
            if status == "unreadable"
        ],
        "failed_pages": [
            index
            for index, status in enumerate(normalized_statuses, start=1)
            if status == "failed"
        ],
        "timeout_pages": [
            index
            for index, status in enumerate(normalized_statuses, start=1)
            if status == "timeout"
        ],
        "recovered_pages": list(recovered_pages),
    }
    return {
        "schema_version": "ocr-diagnostics-v1",
        "engine": _OCR_ENGINE,
        "lang": str(lang or "")[:80],
        "declared_pages": declared_pages,
        "attempted_pages": len(normalized_statuses),
        "status_counts": dict(sorted(counts.items())),
        **{
            key: _bounded_page_numbers(values) for key, values in all_page_lists.items()
        },
        "page_lists_truncated": any(
            len(set(values)) > _MAX_DIAGNOSTIC_PAGE_NUMBERS
            for values in all_page_lists.values()
        ),
        "error_code": str(error_code or "ocr_engine_failed")[:80],
        "machine_code": machine_codes.get(error_code, "OCR_RUNTIME_FAILED"),
    }


def _requested_languages_available(lang: str) -> bool | None:
    available = _available_tesseract_languages()
    if available is None:
        return None
    requested = {part.strip() for part in str(lang or "").split("+") if part.strip()}
    return bool(requested) and requested.issubset(available)


def ocr_pdf_path(
    pdf_path: str,
    max_pages: int = 12,
    scale: float = 2.0,
    lang: str | None = None,
    stop_on_catalog: bool = True,
    *,
    page_timeout_seconds: float = _DEFAULT_PAGE_TIMEOUT_SECONDS,
    attempt_timeout_seconds: float = _DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
) -> OcrResult:
    """
    OCR a PDF file by rasterizing pages with pypdfium2 and running pytesseract.
    - Designed for scanned PDFs where text extraction returns near-empty content.
    """
    p = Path(pdf_path)
    requested_lang = str(lang or "eng")[:80]
    if not p.exists():
        return OcrResult(
            text="",
            pages=0,
            lang=requested_lang,
            error="pdf_not_found",
            diagnostics=_diagnostics(
                lang=requested_lang,
                declared_pages=None,
                error_code="pdf_not_found",
            ),
        )
    if not is_tesseract_available():
        return OcrResult(
            text="",
            pages=0,
            lang=requested_lang,
            error="tesseract_not_installed",
            diagnostics=_diagnostics(
                lang=requested_lang,
                declared_pages=None,
                error_code="tesseract_not_installed",
            ),
        )

    try:
        import pypdfium2 as pdfium
        import pytesseract
    except Exception:  # noqa: BLE001 - optional native dependency boundary
        return OcrResult(
            text="",
            pages=0,
            lang=requested_lang,
            error="ocr_deps_missing",
            diagnostics=_diagnostics(
                lang=requested_lang,
                declared_pages=None,
                error_code="ocr_dependencies_unavailable",
            ),
        )

    use_lang = lang or guess_ocr_lang(prefer_chinese=True)
    pdf = None
    try:
        pdf = pdfium.PdfDocument(str(p))
        total = len(pdf)
    except Exception:  # noqa: BLE001 - native PDF parser boundary
        _safe_close(pdf)
        return OcrResult(
            text="",
            pages=0,
            lang=use_lang,
            error="pdf_open_failed",
            diagnostics=_diagnostics(
                lang=use_lang,
                declared_pages=None,
                error_code="pdf_open_failed",
            ),
        )
    language_ready = _requested_languages_available(use_lang)
    if language_ready is not True:
        language_error = (
            "ocr_language_unavailable"
            if language_ready is False
            else "ocr_language_list_unavailable"
        )
        _safe_close(pdf)
        return OcrResult(
            text="",
            pages=0,
            lang=use_lang,
            error=language_error,
            source_pages=total,
            diagnostics=_diagnostics(
                lang=use_lang,
                declared_pages=total,
                error_code=language_error,
            ),
        )

    out_parts: list[str] = []
    page_statuses: list[str] = []
    page_image_sha256: list[str] = []
    page_error_codes: list[str] = []
    recovered_pages: list[int] = []
    pages_done = 0
    page_timeout = _bounded_timeout(
        page_timeout_seconds,
        default=_DEFAULT_PAGE_TIMEOUT_SECONDS,
        maximum=_MAX_PAGE_TIMEOUT_SECONDS,
    )
    attempt_timeout = _bounded_timeout(
        attempt_timeout_seconds,
        default=_DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
        maximum=min(_MAX_ATTEMPT_TIMEOUT_SECONDS, page_timeout),
    )
    base_scale = _bounded_timeout(
        scale,
        default=2.0,
        maximum=_SECOND_PASS_MAX_SCALE,
    )
    try:
        for i in range(min(max(1, int(max_pages or 1)), total)):
            page = None
            bitmap = None
            source_image = None
            ocr_image = None
            page_deadline = time.monotonic() + page_timeout
            try:
                page = pdf[i]
                bitmap = page.render(scale=base_scale)
                source_image = bitmap.to_pil()
                image_sha256 = _image_sha256(source_image)
                ocr_image = _preprocess_pil_for_ocr(source_image)
                page_text, page_error = _invoke_tesseract(
                    pytesseract,
                    ocr_image,
                    lang=use_lang,
                    config="",
                    deadline=page_deadline,
                    attempt_timeout_seconds=attempt_timeout,
                )
                status = "text"
                if page_error == "ocr_page_timeout" and _is_proven_blank_image(
                    source_image
                ):
                    status = "blank"
                elif page_error == "ocr_page_timeout":
                    page_text, retry_error = _run_second_pass(
                        page=page,
                        source_image=source_image,
                        base_scale=base_scale,
                        pytesseract=pytesseract,
                        lang=use_lang,
                        deadline=page_deadline,
                        attempt_timeout_seconds=attempt_timeout,
                    )
                    if page_text:
                        recovered_pages.append(i + 1)
                        status = "text"
                    else:
                        final_error = retry_error or "ocr_zero_text_nonblank"
                        page_error_codes.append(final_error)
                        status = (
                            "timeout"
                            if final_error == "ocr_page_timeout"
                            else "unreadable"
                        )
                elif page_error is not None:
                    page_error_codes.append(page_error)
                    status = "timeout" if page_error == "ocr_page_timeout" else "failed"
                elif not page_text and _is_proven_blank_image(source_image):
                    status = "blank"
                elif not page_text:
                    page_text, page_error = _run_second_pass(
                        page=page,
                        source_image=source_image,
                        base_scale=base_scale,
                        pytesseract=pytesseract,
                        lang=use_lang,
                        deadline=page_deadline,
                        attempt_timeout_seconds=attempt_timeout,
                    )
                    if page_text:
                        recovered_pages.append(i + 1)
                        status = "text"
                    elif page_error == "ocr_page_timeout":
                        page_error_codes.append(page_error)
                        status = "timeout"
                    elif page_error is not None:
                        page_error_codes.append(page_error)
                        status = "failed"
                    else:
                        page_error_codes.append("ocr_zero_text_nonblank")
                        status = "unreadable"
                out_parts.append(page_text)
                page_image_sha256.append(image_sha256)
                page_statuses.append(status)
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
                error_code = _classify_ocr_exception(exc)
                logger.warning(
                    "ocr_page_failed page=%s machine_code=%s error_type=%s",
                    i + 1,
                    error_code.upper(),
                    type(exc).__name__,
                )
                out_parts.append("")
                page_statuses.append(
                    "timeout" if error_code == "ocr_page_timeout" else "failed"
                )
                page_image_sha256.append("")
                page_error_codes.append(error_code)
                pages_done += 1
                continue
            finally:
                closable_ocr_image = (
                    ocr_image if ocr_image is not source_image else None
                )
                _safe_close(
                    closable_ocr_image,
                    source_image,
                    bitmap,
                    page,
                )
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
    error_code = "none"
    if "ocr_language_unavailable" in page_error_codes:
        error_code = "ocr_language_unavailable"
    elif "tesseract_not_installed" in page_error_codes:
        error_code = "tesseract_not_installed"
    elif "ocr_page_timeout" in page_error_codes:
        error_code = "ocr_page_timeout"
    elif "ocr_engine_failed" in page_error_codes:
        error_code = "ocr_engine_failed"
    elif "ocr_zero_text_nonblank" in page_error_codes:
        error_code = "ocr_zero_text_nonblank"
    elif any(status in {"failed", "unreadable", "timeout"} for status in page_statuses):
        error_code = "page_ocr_incomplete"
    return OcrResult(
        text=text,
        pages=pages_done,
        lang=use_lang,
        error=(
            "page_ocr_incomplete"
            if any(
                status in {"failed", "unreadable", "timeout"}
                for status in page_statuses
            )
            else None
        ),
        page_texts=tuple(out_parts),
        page_statuses=tuple(page_statuses),
        page_image_sha256=tuple(page_image_sha256),
        source_pages=total,
        diagnostics=_diagnostics(
            lang=use_lang,
            declared_pages=total,
            statuses=page_statuses,
            error_code=error_code,
            recovered_pages=recovered_pages,
        ),
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
