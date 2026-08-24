from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn


_A4_WIDTH_CM = 21.0
_A4_HEIGHT_CM = 29.7
_EMU_PER_CM = 360_000
_INTERNAL_LEAK_PATTERNS = (
    re.compile(r"\bmain:(?:anthropic|openai|google)\b", re.IGNORECASE),
    re.compile(r"\bfallback_[0-9]+\b", re.IGNORECASE),
    re.compile(r"\bjob_id\s*=", re.IGNORECASE),
    re.compile(r"\bquality_checks\b", re.IGNORECASE),
    re.compile(r"【(?:多Agent|系统全局指令|证据与追溯|章节结构蓝图|本地导出控制表)"),
)


class DocxStructuralQualityError(RuntimeError):
    """Raised when the final Word package violates the delivery contract."""

    def __init__(self, message: str, *, report: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.report = report or {}


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


def _cm(value: Any) -> float:
    try:
        return round(float(value) / _EMU_PER_CM, 3)
    except (TypeError, ValueError):
        return 0.0


def _pt(value: Any) -> float | None:
    try:
        return round(float(value.pt), 2)
    except (AttributeError, TypeError, ValueError):
        return None


def _font_name(style: Any) -> str:
    try:
        rpr = style._element.rPr
        rfonts = rpr.rFonts if rpr is not None else None
        if rfonts is not None:
            for name in ("eastAsia", "ascii", "hAnsi"):
                value = rfonts.get(qn(f"w:{name}"))
                if value:
                    return str(value)
    except Exception:
        pass
    return str(getattr(getattr(style, "font", None), "name", "") or "")


def _normalise_font(value: Any) -> str:
    name = re.sub(r"\s+", "", str(value or "")).lower()
    aliases = {
        "宋体": "song",
        "simsun": "song",
        "stsong": "song",
        "songtisc": "song",
        "仿宋": "fangsong",
        "仿宋体": "fangsong",
        "stfangsong": "fangsong",
        "fangsong": "fangsong",
        "黑体": "heiti",
        "simhei": "heiti",
        "heitisc": "heiti",
        "stheiti": "heiti",
    }
    return aliases.get(name, name)


def _stable_digest(payload: dict[str, Any]) -> str:
    material = dict(payload)
    for key in ("created_at", "receipt", "docx"):
        material.pop(key, None)
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _read_package_xml(source: Path) -> dict[str, str]:
    with zipfile.ZipFile(source) as package:
        names = set(package.namelist())
        result: dict[str, str] = {}
        for name in ("word/document.xml", "word/settings.xml"):
            if name in names:
                result[name] = package.read(name).decode("utf-8", errors="replace")
        footer_names = sorted(name for name in names if re.fullmatch(r"word/footer[0-9]+\.xml", name))
        result["word/footers.xml"] = "\n".join(
            package.read(name).decode("utf-8", errors="replace") for name in footer_names
        )
        result["package_names"] = "\n".join(sorted(names))
        return result


def _field_present(xml: str, field_name: str) -> bool:
    name = re.escape(field_name)
    return bool(
        re.search(rf"w:instrText[^>]*>[^<]*\b{name}\b", xml, flags=re.IGNORECASE)
        or re.search(rf"w:fldSimple[^>]+w:instr=[\"'][^\"']*\b{name}\b", xml, flags=re.IGNORECASE)
    )


def _heading_level(style_name: str) -> int | None:
    match = re.search(r"(?:heading|标题)\s*([1-9])", str(style_name or ""), flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def audit_docx_structural_quality(
    docx_path: str | Path,
    *,
    expected_style: dict[str, Any] | None = None,
    figure_manifest: dict[str, Any] | None = None,
    require_heading_structure: bool = True,
    strict: bool = True,
    receipt_path: str | Path | None = None,
) -> dict[str, Any]:
    """Inspect the final DOCX package itself before it is exposed to a user.

    This gate is deliberately independent from the generator. It reads the
    saved package and verifies page geometry, named styles, Word fields,
    heading pagination, tables, figure delivery and bidder-facing cleanliness.
    """

    source = Path(docx_path)
    target_receipt = Path(receipt_path) if receipt_path else source.with_suffix(".structural_quality.json")
    hard_failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if not source.is_file() or source.stat().st_size == 0:
        report = {
            "schema": "zhifei.docx_structural_quality.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "blocked",
            "docx": str(source),
            "hard_failures": [{"code": "DOCX_MISSING_OR_EMPTY"}],
            "warnings": [],
        }
        report["decision_digest"] = _stable_digest(report)
        _atomic_write_json(target_receipt, report)
        report["receipt"] = str(target_receipt)
        if strict:
            raise DocxStructuralQualityError("最终 Word 不存在或为空", report=report)
        return report

    try:
        document = Document(str(source))
        package_xml = _read_package_xml(source)
    except Exception as exc:
        report = {
            "schema": "zhifei.docx_structural_quality.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "blocked",
            "docx": str(source),
            "hard_failures": [{"code": "DOCX_UNREADABLE", "message": str(exc)[:300]}],
            "warnings": [],
        }
        report["decision_digest"] = _stable_digest(report)
        _atomic_write_json(target_receipt, report)
        report["receipt"] = str(target_receipt)
        if strict:
            raise DocxStructuralQualityError("最终 Word 包无法读取", report=report) from exc
        return report

    visible_paragraphs = [p for p in document.paragraphs if str(p.text or "").strip()]
    visible_text = "\n".join(str(p.text or "") for p in visible_paragraphs)
    visible_chars = len(re.sub(r"\s+", "", visible_text))
    # Structural QA also runs for small deterministic regression fixtures. The
    # content-quality gate enforces chapter substance separately; this layer
    # only rejects an effectively empty Word package.
    if visible_chars < 1:
        hard_failures.append({"code": "DOCUMENT_CONTENT_TOO_THIN", "visible_chars": visible_chars})

    section_metrics: list[dict[str, Any]] = []
    expected = dict(expected_style or {})
    margins = expected.get("margins_cm") if isinstance(expected.get("margins_cm"), dict) else {}
    margins = {
        "top": expected.get("margin_top_cm", margins.get("top", 2.5)),
        "right": expected.get("margin_right_cm", margins.get("right", 2.0)),
        "bottom": expected.get("margin_bottom_cm", margins.get("bottom", 2.0)),
        "left": expected.get("margin_left_cm", margins.get("left", 2.0)),
    }
    for index, section in enumerate(document.sections, start=1):
        metric = {
            "section": index,
            "width_cm": _cm(section.page_width),
            "height_cm": _cm(section.page_height),
            "margins_cm": {
                "top": _cm(section.top_margin),
                "right": _cm(section.right_margin),
                "bottom": _cm(section.bottom_margin),
                "left": _cm(section.left_margin),
            },
        }
        section_metrics.append(metric)
        if str(expected.get("paper") or "A4").upper() == "A4":
            if abs(metric["width_cm"] - _A4_WIDTH_CM) > 0.12 or abs(metric["height_cm"] - _A4_HEIGHT_CM) > 0.12:
                hard_failures.append({"code": "PAGE_SIZE_NOT_A4", **metric})
        for name, fallback in (("top", 2.5), ("right", 2.0), ("bottom", 2.0), ("left", 2.0)):
            expected_margin = float(margins.get(name, fallback))
            actual_margin = float(metric["margins_cm"][name])
            if abs(actual_margin - expected_margin) > 0.12:
                hard_failures.append(
                    {
                        "code": "MARGIN_MISMATCH",
                        "section": index,
                        "side": name,
                        "expected_cm": expected_margin,
                        "actual_cm": actual_margin,
                    }
                )

    try:
        normal = document.styles["Normal"]
        normal_font = _font_name(normal)
        normal_size = _pt(normal.font.size)
        normal_spacing = normal.paragraph_format.line_spacing
        normal_spacing_pt = _pt(normal_spacing)
    except Exception:
        normal_font = ""
        normal_size = None
        normal_spacing_pt = None
        hard_failures.append({"code": "NORMAL_STYLE_MISSING"})
    expected_font = str(expected.get("body_font") or "宋体")
    expected_size = float(expected.get("body_size_pt") or expected.get("body_size") or 14.0)
    expected_spacing_pt = expected.get("line_spacing_pt")
    if not normal_font:
        hard_failures.append({"code": "BODY_FONT_UNDEFINED"})
    elif _normalise_font(normal_font) != _normalise_font(expected_font):
        hard_failures.append(
            {"code": "BODY_FONT_MISMATCH", "expected": expected_font, "actual": normal_font}
        )
    if normal_size is None or abs(normal_size - expected_size) > 0.2:
        hard_failures.append(
            {"code": "BODY_SIZE_MISMATCH", "expected_pt": expected_size, "actual_pt": normal_size}
        )
    if expected_spacing_pt is not None:
        expected_spacing = float(expected_spacing_pt)
        if normal_spacing_pt is None or abs(normal_spacing_pt - expected_spacing) > 0.3:
            hard_failures.append(
                {
                    "code": "LINE_SPACING_MISMATCH",
                    "expected_pt": expected_spacing,
                    "actual_pt": normal_spacing_pt,
                }
            )

    document_xml = package_xml.get("word/document.xml", "")
    settings_xml = package_xml.get("word/settings.xml", "")
    footers_xml = package_xml.get("word/footers.xml", "")
    if not _field_present(document_xml, "TOC"):
        hard_failures.append({"code": "TOC_FIELD_MISSING"})
    if not re.search(r"<w:updateFields\b[^>]*w:val=[\"'](?:true|1)[\"']", settings_xml):
        hard_failures.append({"code": "FIELD_UPDATE_DISABLED"})
    for field_name in ("PAGE", "NUMPAGES"):
        if not _field_present(footers_xml, field_name):
            hard_failures.append({"code": f"{field_name}_FIELD_MISSING"})

    heading_count = 0
    hierarchy: list[int] = []
    unsafe_headings: list[dict[str, Any]] = []
    for index, paragraph in enumerate(document.paragraphs, start=1):
        level = _heading_level(str(getattr(getattr(paragraph, "style", None), "name", "") or ""))
        if level is None:
            continue
        heading_count += 1
        hierarchy.append(level)
        fmt = paragraph.paragraph_format
        style_fmt = getattr(getattr(paragraph, "style", None), "paragraph_format", None)

        def _effective_bool(name: str) -> bool:
            direct = getattr(fmt, name, None)
            if direct is not None:
                return bool(direct)
            return bool(getattr(style_fmt, name, None)) if style_fmt is not None else False

        if not all(
            _effective_bool(name) for name in ("keep_with_next", "keep_together", "widow_control")
        ):
            unsafe_headings.append({"paragraph": index, "level": level, "text": paragraph.text[:80]})
    if require_heading_structure and heading_count == 0:
        hard_failures.append({"code": "HEADING_STRUCTURE_MISSING"})
    if unsafe_headings:
        hard_failures.append({"code": "HEADING_PAGINATION_UNSAFE", "items": unsafe_headings[:20]})
    jumps = [
        {"from": hierarchy[index - 1], "to": hierarchy[index], "position": index + 1}
        for index in range(1, len(hierarchy))
        if hierarchy[index] > hierarchy[index - 1] + 1
    ]
    if jumps:
        warnings.append({"code": "HEADING_HIERARCHY_JUMPS", "items": jumps[:20]})

    split_rows: list[dict[str, int]] = []
    headerless_tables: list[int] = []
    for table_index, table in enumerate(document.tables, start=1):
        for row_index, row in enumerate(table.rows, start=1):
            tr_pr = row._tr.trPr
            if tr_pr is None or tr_pr.find(qn("w:cantSplit")) is None:
                split_rows.append({"table": table_index, "row": row_index})
        if len(table.rows) > 1:
            tr_pr = table.rows[0]._tr.trPr
            if tr_pr is None or tr_pr.find(qn("w:tblHeader")) is None:
                headerless_tables.append(table_index)
    if split_rows:
        hard_failures.append({"code": "TABLE_ROWS_CAN_SPLIT", "items": split_rows[:40]})
    if headerless_tables:
        warnings.append({"code": "TABLE_HEADER_NOT_REPEATED", "tables": headerless_tables})

    for pattern in _INTERNAL_LEAK_PATTERNS:
        match = pattern.search(visible_text)
        if match:
            hard_failures.append(
                {"code": "INTERNAL_IMPLEMENTATION_LEAK", "sample": match.group(0)[:100]}
            )
            break

    figure_summary: dict[str, Any] = {}
    if isinstance(figure_manifest, dict):
        figure_summary = {
            "delivery_allowed": bool(figure_manifest.get("delivery_allowed")),
            "figure_count": int(figure_manifest.get("figure_count") or 0),
            "decision_digest": str(figure_manifest.get("decision_digest") or ""),
        }
        if not figure_summary["delivery_allowed"]:
            hard_failures.append({"code": "FIGURE_DELIVERY_GATE_BLOCKED"})

    report = {
        "schema": "zhifei.docx_structural_quality.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked" if hard_failures else "pass",
        "docx": str(source),
        "docx_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "visible_chars": visible_chars,
        "paragraph_count": len(document.paragraphs),
        "heading_count": heading_count,
        "table_count": len(document.tables),
        "section_metrics": section_metrics,
        "body_style": {
            "font": normal_font,
            "size_pt": normal_size,
            "line_spacing_pt": normal_spacing_pt,
        },
        "word_fields": {
            "toc": _field_present(document_xml, "TOC"),
            "page": _field_present(footers_xml, "PAGE"),
            "numpages": _field_present(footers_xml, "NUMPAGES"),
            "update_on_open": bool(
                re.search(r"<w:updateFields\b[^>]*w:val=[\"'](?:true|1)[\"']", settings_xml)
            ),
        },
        "figure_delivery": figure_summary,
        "hard_failures": hard_failures,
        "warnings": warnings,
    }
    report["decision_digest"] = _stable_digest(report)
    _atomic_write_json(target_receipt, report)
    report["receipt"] = str(target_receipt)
    if strict and report["status"] != "pass":
        codes = ", ".join(str(item.get("code")) for item in hard_failures)
        raise DocxStructuralQualityError(f"最终 Word 结构验收未通过：{codes}", report=report)
    return report
