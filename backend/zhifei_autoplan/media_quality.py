from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable


_OVERVIEW_RE = re.compile(r"(工程概况|项目概况|总体部署|施工部署|编制依据)")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]{2,}|[\u4e00-\u9fff]{2,12}")


def _item_path(item: Any) -> Path:
    if isinstance(item, dict):
        raw = item.get("path") or item.get("source_path") or item.get("storage_path") or ""
    else:
        raw = item or ""
    return Path(str(raw)).expanduser()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _difference_hash(image: Any) -> str:
    """Return a stable 64-bit dHash without requiring optional image packages."""
    from PIL import Image

    gray = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            left = pixels[row * 9 + col]
            right = pixels[row * 9 + col + 1]
            bits = (bits << 1) | int(left > right)
    return f"{bits:016x}"


def perceptual_hash_distance(left: str | None, right: str | None) -> int:
    try:
        return (int(str(left), 16) ^ int(str(right), 16)).bit_count()
    except Exception:
        return 64


def validate_image_bytes(data: bytes) -> dict[str, Any]:
    """Decode image bytes and return dimensions/hashes. Never trusts an extension."""
    result: dict[str, Any] = {
        "ok": False,
        "errors": [],
        "warnings": [],
        "sha256": _sha256_bytes(data or b""),
    }
    if not data:
        result["errors"].append("empty_image_payload")
        return result
    try:
        from PIL import Image, ImageFilter, ImageStat

        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            width, height = int(image.width), int(image.height)
            result.update(
                {
                    "format": str(image.format or "").upper(),
                    "width_px": width,
                    "height_px": height,
                    "aspect_ratio": round(width / max(1, height), 4),
                    "perceptual_hash": _difference_hash(image),
                }
            )
            if width < 1 or height < 1:
                result["errors"].append("invalid_image_dimensions")
            if width < 640 or height < 360 or width * height < 350_000:
                result["errors"].append("image_resolution_below_formal_minimum")
            ratio = width / max(1, height)
            if ratio < 0.22 or ratio > 4.0:
                result["errors"].append("extreme_image_aspect_ratio")

            gray = image.convert("L")
            stat = ImageStat.Stat(gray)
            extrema = gray.getextrema()
            dynamic_range = int(extrema[1]) - int(extrema[0])
            stddev = float(stat.stddev[0] if stat.stddev else 0.0)
            result["dynamic_range"] = dynamic_range
            result["luma_stddev"] = round(stddev, 3)
            if dynamic_range < 12 and stddev < 2.5:
                result["errors"].append("blank_or_near_blank_image")

            # Blur is a warning because deliberately flat engineering diagrams
            # can have low edge variance while still being perfectly legible.
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_stddev = float(ImageStat.Stat(edges).stddev[0] or 0.0)
            result["edge_stddev"] = round(edge_stddev, 3)
            if edge_stddev < 3.0:
                result["warnings"].append("image_may_be_blurred_or_low_detail")
    except Exception as exc:
        result["errors"].append("image_decode_failed")
        result["decode_error"] = type(exc).__name__
        return result
    result["ok"] = not result["errors"]
    return result


def validate_media_item(
    item: Any,
    *,
    chapter_title: str | None = None,
    insert_width_cm: float = 16.0,
) -> dict[str, Any]:
    path = _item_path(item)
    receipt: dict[str, Any] = {
        "ok": False,
        "status": "rejected",
        "path": str(path),
        "caption": str(item.get("caption") or item.get("title") or "").strip() if isinstance(item, dict) else "",
        "required": bool(item.get("required")) if isinstance(item, dict) else False,
        "chapter_title": str(chapter_title or "").strip(),
        "errors": [],
        "warnings": [],
    }
    if not path.exists() or not path.is_file():
        receipt["errors"].append("image_file_missing")
        return receipt
    try:
        data = path.read_bytes()
    except Exception as exc:
        receipt["errors"].append("image_read_failed")
        receipt["read_error"] = type(exc).__name__
        return receipt
    decoded = validate_image_bytes(data)
    receipt.update({key: value for key, value in decoded.items() if key not in {"ok", "errors", "warnings"}})
    receipt["errors"].extend(decoded.get("errors") or [])
    receipt["warnings"].extend(decoded.get("warnings") or [])
    width = int(receipt.get("width_px") or 0)
    if width and insert_width_cm > 0:
        effective_dpi = width / (float(insert_width_cm) / 2.54)
        receipt["effective_dpi"] = round(effective_dpi, 1)
        if effective_dpi < 110:
            receipt["warnings"].append("effective_dpi_below_recommended_110")
    receipt["ok"] = not receipt["errors"]
    receipt["status"] = "accepted" if receipt["ok"] else "rejected"
    return receipt


def _normalised_tokens(values: Iterable[Any]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = str(value or "").strip().lower()
        if not text:
            continue
        tokens.add(text)
        tokens.update(token.lower() for token in _TOKEN_RE.findall(text))
    return tokens


def media_matches_chapter(
    item: Any,
    chapter_title: str,
    *,
    allow_unbound_project_source: bool = False,
) -> bool:
    if not isinstance(item, dict):
        return bool(allow_unbound_project_source and _OVERVIEW_RE.search(str(chapter_title or "")))
    chapter = str(chapter_title or "").strip()
    explicit_scope = item.get("chapter_scope") or item.get("chapter_title") or []
    if isinstance(explicit_scope, str):
        explicit_scope = [explicit_scope]
    scopes = [str(value or "").strip() for value in explicit_scope if str(value or "").strip()]
    if scopes:
        if any(scope == chapter or scope in chapter or chapter in scope for scope in scopes):
            return True
        chapter_tokens = _normalised_tokens([chapter])
        return bool(chapter_tokens.intersection(_normalised_tokens(scopes)))
    source_kind = str(item.get("source_kind") or item.get("source_mode") or "").strip().lower()
    if bool(
        item.get("unbound_project_source")
        or item.get("is_project_source")
        or source_kind in {"site_photo", "drawing"}
    ):
        return bool(allow_unbound_project_source and _OVERVIEW_RE.search(chapter))
    chapter_tokens = _normalised_tokens([chapter])
    media_tokens = _normalised_tokens(
        [
            item.get("caption"),
            item.get("title"),
            item.get("source_filename"),
            *(item.get("tags") or []),
            *(item.get("semantic_terms") or []),
        ]
    )
    return bool(chapter_tokens.intersection(media_tokens))


def _selection_priority(item: dict[str, Any]) -> tuple[int, int]:
    source_kind = str(item.get("source_kind") or item.get("source_mode") or "").lower()
    if item.get("explicit_selection"):
        primary = 5
    elif item.get("is_project_source") or source_kind in {"site_photo", "drawing"}:
        primary = 4
    elif "semantic_generated" in source_kind:
        primary = 3
    elif "deterministic" in source_kind:
        primary = 2
    else:
        primary = 1
    return primary, int(bool(item.get("required")))


def validate_media_collection(items: Iterable[Any]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in items or []:
        item = dict(raw) if isinstance(raw, dict) else {"path": str(raw or "")}
        receipt = validate_media_item(item)
        enriched = dict(item)
        enriched["quality_receipt"] = receipt
        if receipt.get("ok"):
            enriched["asset_sha256"] = receipt.get("sha256")
            enriched["perceptual_hash"] = receipt.get("perceptual_hash")
            candidates.append(enriched)
        else:
            rejected.append({"item": enriched, "reason": list(receipt.get("errors") or [])})

    # Prefer explicit/project evidence over generated alternatives when exact or
    # perceptual duplicates compete for a single formal-document slot.
    candidates.sort(key=_selection_priority, reverse=True)
    accepted: list[dict[str, Any]] = []
    seen_sha: set[str] = set()
    seen_phash: list[str] = []
    for item in candidates:
        sha = str(item.get("asset_sha256") or "")
        phash = str(item.get("perceptual_hash") or "")
        duplicate_reason = ""
        if sha and sha in seen_sha:
            duplicate_reason = "exact_duplicate_image"
        elif phash and any(perceptual_hash_distance(phash, prior) <= 3 for prior in seen_phash):
            duplicate_reason = "near_duplicate_image"
        if duplicate_reason:
            rejected.append({"item": item, "reason": [duplicate_reason]})
            continue
        accepted.append(item)
        if sha:
            seen_sha.add(sha)
        if phash:
            seen_phash.append(phash)

    required_failures = [entry for entry in rejected if bool((entry.get("item") or {}).get("required"))]
    return {
        "status": "blocked" if required_failures else "pass",
        "accepted": accepted,
        "rejected": rejected,
        "required_failures": required_failures,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
    }


def docx_embedded_media_hashes(docx_path: str | Path) -> dict[str, str]:
    path = Path(docx_path)
    hashes: dict[str, str] = {}
    with zipfile.ZipFile(path, "r") as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith("word/media/") or name.endswith("/"):
                continue
            hashes[name] = _sha256_bytes(archive.read(name))
    return hashes


def verify_docx_media_hashes(docx_path: str | Path, expected_hashes: Iterable[str]) -> dict[str, Any]:
    embedded = docx_embedded_media_hashes(docx_path)
    embedded_values = set(embedded.values())
    expected = {str(value or "").strip() for value in expected_hashes if str(value or "").strip()}
    missing = sorted(expected - embedded_values)
    return {
        "ok": not missing,
        "expected_hashes": sorted(expected),
        "embedded_media": embedded,
        "missing_hashes": missing,
    }


def build_media_delivery_manifest(
    *,
    source_media: dict[str, Any] | None,
    insertions: Iterable[dict[str, Any]],
    insertion_failures: Iterable[dict[str, Any]],
    embedded_media_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the final, fail-closed figure delivery decision.

    A formal technical-bid figure is deliverable only when its sequence,
    chapter/caption, source class, source reference, asset digest and embedded
    DOCX media digest are all traceable. Optional rejected figures remain a
    warning; required failures and malformed/unenclosed insertions block export.
    """

    rows = [dict(row) for row in insertions or [] if isinstance(row, dict)]
    failures = [dict(row) for row in insertion_failures or [] if isinstance(row, dict)]
    verification = dict(embedded_media_verification or {})
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    seen_numbers: set[int] = set()
    seen_hashes: set[str] = set()

    for index, row in enumerate(rows, start=1):
        number = int(row.get("figure_number") or 0)
        missing_fields = [
            name
            for name in ("caption", "chapter_title", "source_kind", "source_ref", "asset_sha256")
            if not str(row.get(name) or "").strip()
        ]
        if number < 1 or number in seen_numbers:
            issues.append(
                {
                    "code": "FIGURE_NUMBER_INVALID",
                    "index": index,
                    "figure_number": number,
                }
            )
        else:
            seen_numbers.add(number)
        if missing_fields:
            issues.append(
                {
                    "code": "FIGURE_TRACEABILITY_INCOMPLETE",
                    "index": index,
                    "figure_number": number,
                    "missing_fields": missing_fields,
                }
            )
        digest = str(row.get("asset_sha256") or "").strip()
        if digest and not re.fullmatch(r"[0-9a-f]{64}", digest):
            issues.append(
                {
                    "code": "FIGURE_ASSET_DIGEST_INVALID",
                    "index": index,
                    "figure_number": number,
                }
            )
        elif digest and digest in seen_hashes:
            issues.append(
                {
                    "code": "FIGURE_ASSET_DUPLICATED",
                    "index": index,
                    "figure_number": number,
                }
            )
        elif digest:
            seen_hashes.add(digest)

    expected_numbers = list(range(1, len(rows) + 1))
    if sorted(seen_numbers) != expected_numbers:
        issues.append(
            {
                "code": "FIGURE_NUMBER_SEQUENCE_BROKEN",
                "expected": expected_numbers,
                "actual": sorted(seen_numbers),
            }
        )

    for failure in failures:
        item = {
            "code": "REQUIRED_FIGURE_INSERTION_FAILED"
            if bool(failure.get("required"))
            else "OPTIONAL_FIGURE_INSERTION_SKIPPED",
            "caption": str(failure.get("caption") or ""),
            "chapter_title": str(failure.get("chapter_title") or ""),
            "reason": list(failure.get("reason") or []),
        }
        (issues if bool(failure.get("required")) else warnings).append(item)

    if not bool(verification.get("ok")):
        issues.append(
            {
                "code": "DOCX_EMBEDDED_MEDIA_MISMATCH",
                "missing_hashes": list(verification.get("missing_hashes") or []),
            }
        )

    payload = {
        "schema_version": "docx_figure_delivery.v2",
        "source_media": dict(source_media or {}),
        "insertions": rows,
        "insertion_failures": failures,
        "embedded_media_verification": verification,
        "issues": issues,
        "warnings": warnings,
        "delivery_allowed": not issues,
        "status": "pass" if not issues else "blocked",
    }
    digest_payload = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    payload["decision_digest"] = hashlib.sha256(digest_payload).hexdigest()
    return payload
