from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

_STANDARD_KEYWORDS = (
    "企业标准",
    "工法",
    "作业指导",
    "标准化",
    "技术标准",
    "标准图集",
    "管理标准",
)
_DRAWING_KEYWORDS = (
    "图",
    "图纸",
    "施工图",
    "平面",
    "剖面",
    "大样",
    "节点",
    "cad",
    "dwg",
    "dxf",
)


def normalize_source_hint(source_hint: Any) -> str:
    raw = str(source_hint or "").strip().lower()
    if not raw:
        return ""
    aliases = {
        "tender": "tender_qa",
        "qa": "tender_qa",
        "answer": "tender_qa",
        "答疑": "tender_qa",
        "招标": "tender_qa",
        "boq": "boq",
        "quantity": "boq",
        "drawing": "drawing_standard",
        "cad": "drawing_standard",
        "standard": "standard",
        "图纸": "drawing_standard",
        "标准": "standard",
        "photo": "site_photo",
        "site_photo": "site_photo",
        "现场照片": "site_photo",
    }
    return aliases.get(raw, raw)


def classify_document_tags(
    filename: Any,
    ext: Any,
    parsed_type: Any,
    *,
    source_hint: Any = None,
) -> list[str]:
    name = str(filename or "").strip().lower()
    extension = str(ext or "").strip().lower().lstrip(".")
    parsed = str(parsed_type or "").strip().lower()
    hint = normalize_source_hint(source_hint)
    is_site_photo = hint == "site_photo"
    is_standard = hint == "standard" or any(
        keyword in name for keyword in _STANDARD_KEYWORDS
    )
    is_explicit_drawing = any(keyword in name for keyword in _DRAWING_KEYWORDS)

    tags: list[str] = []
    if hint == "tender_qa":
        tags.extend(["tender", "qa"])
    elif hint == "boq":
        tags.append("boq")
    elif hint == "site_photo":
        tags.append("site_photo")
    elif hint == "standard":
        tags.append("standard")

    if any(keyword in name for keyword in ("logo", "标志", "标识", "徽标")):
        tags.append("logo")
    if any(keyword in name for keyword in ("清单", "工程量清单", "boq")):
        tags.append("boq")
    if any(keyword in name for keyword in ("招标", "招標", "tender")):
        tags.append("tender")
    if is_standard:
        tags.append("standard")

    drawing_extension = extension in {"pdf", "dxf", "dwg"} or parsed in {
        "pdf",
        "cad",
        "dwg",
    }
    if (
        not is_site_photo
        and not is_standard
        and (
            is_explicit_drawing
            or extension in {"dxf", "dwg"}
            or parsed in {"cad", "dwg"}
            or (hint == "drawing_standard" and drawing_extension)
        )
    ):
        tags.append("drawing")
    if not is_site_photo and not is_standard and extension in {"png", "jpg", "jpeg"}:
        tags.append("drawing")

    result: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def effective_record_tags(record: Mapping[str, Any] | None) -> list[str]:
    rec = record if isinstance(record, Mapping) else {}
    existing = rec.get("tags") if isinstance(rec.get("tags"), list) else []
    filename = str(rec.get("filename") or "")
    ext = str(rec.get("ext") or Path(filename).suffix.lstrip("."))
    source_hint = normalize_source_hint(
        rec.get("source_hint") or rec.get("library_scope")
    )
    if source_hint == "standard":
        # Historical standard imports could contain a stale drawing tag from
        # the former combined hint.  Explicit standard scope owns the record.
        existing = [tag for tag in existing if str(tag).strip() != "drawing"]
    inferred = classify_document_tags(
        filename,
        ext,
        rec.get("parsed_type"),
        source_hint=source_hint,
    )
    result: list[str] = []
    seen: set[str] = set()
    for tag in [*existing, *inferred]:
        value = str(tag).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
