from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.ingest_tags import effective_record_tags

INGEST_EVIDENCE_SET_RECEIPT_SCHEMA = "ingest-evidence-set-receipt-v1"
_FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EMPTY_TEXT_SHA256 = hashlib.sha256(b"").hexdigest()
_FULL_PAGE_OCR_POLICIES = {"drawing_full_page", "standard_full_page"}
_SUPPORTED_OCR_PAGE_PROOF_VERSIONS = {
    "ocr-page-proof-v2",
    "ocr-page-proof-v3",
}


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_regular_file_snapshot(
    path: Path,
    *,
    retain_bytes: bool,
) -> tuple[str, bytes | None]:
    """Hash one no-follow regular-file snapshot and optionally retain its bytes."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    digest = hashlib.sha256()
    chunks: list[bytes] | None = [] if retain_bytes else None
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError("evidence_path_not_regular")
        with os.fdopen(fd, "rb", closefd=True) as handle:
            fd = -1
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                if chunks is not None:
                    chunks.append(chunk)
            finished = os.fstat(handle.fileno())
        current = os.stat(path, follow_symlinks=False)
        def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
            return (
                value.st_dev,
                value.st_ino,
                value.st_mode,
                value.st_size,
                value.st_mtime_ns,
            )

        if _stat_identity(opened) != _stat_identity(finished) or (
            current.st_dev,
            current.st_ino,
            current.st_mode,
            current.st_size,
            current.st_mtime_ns,
        ) != _stat_identity(finished):
            raise OSError("evidence_path_changed_during_read")
    finally:
        if fd >= 0:
            os.close(fd)
    return digest.hexdigest(), b"".join(chunks) if chunks is not None else None


def _file_sha256(path: Path) -> str:
    digest, _ = _read_regular_file_snapshot(path, retain_bytes=False)
    return digest


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, ValueError):
        return False
    return True


def _validate_full_page_ocr_record(
    record: Mapping[str, Any],
    extract_text: str,
) -> dict[str, Any]:
    """Validate page proof and derive text eligibility from current extract bytes."""

    policy = str(record.get("ocr_cache_policy") or "").strip()
    is_pdf = (
        str(record.get("doc_type") or "").strip().lower() == "pdf"
        or Path(str(record.get("filename") or "")).suffix.lower() == ".pdf"
    )
    if policy not in _FULL_PAGE_OCR_POLICIES or not is_pdf:
        return {"ok": True, "page_eligibility": []}
    try:
        declared_pages = int(record.get("pages"))
    except (TypeError, ValueError):
        return {"ok": False, "reason": "ocr_declared_pages_invalid"}
    if isinstance(record.get("pages"), bool) or declared_pages <= 0:
        return {"ok": False, "reason": "ocr_declared_pages_invalid"}
    proof_version = str(record.get("ocr_page_proof_version") or "")
    statuses = record.get("ocr_page_statuses")
    image_sha256 = record.get("ocr_page_image_sha256")
    text_sha256 = record.get("ocr_page_text_sha256")
    extract_page_sha256 = record.get("ocr_extract_page_sha256")
    blank_pages = record.get("ocr_blank_pages")
    if (
        proof_version not in _SUPPORTED_OCR_PAGE_PROOF_VERSIONS
        or record.get("ocr_page_mapping") != "source_page_all"
        or record.get("ocr_error") not in {None, ""}
        or record.get("ocr_source_pages") != declared_pages
        or record.get("ocr_pages") != declared_pages
        or record.get("ocr_page_text_count") != declared_pages
        or not isinstance(statuses, list)
        or not isinstance(image_sha256, list)
        or not isinstance(text_sha256, list)
        or not isinstance(extract_page_sha256, list)
        or not isinstance(blank_pages, list)
        or any(
            len(values) != declared_pages
            for values in (
                statuses,
                image_sha256,
                text_sha256,
                extract_page_sha256,
            )
        )
    ):
        return {"ok": False, "reason": "ocr_page_proof_incomplete"}
    allowed_statuses = {"text", "blank"}
    if policy == "drawing_full_page" and proof_version == "ocr-page-proof-v3":
        allowed_statuses.add("graphics_only")
    for status, image_digest, text_digest in zip(
        statuses,
        image_sha256,
        text_sha256,
        strict=True,
    ):
        if status not in allowed_statuses:
            return {"ok": False, "reason": "ocr_page_status_invalid"}
        if _FULL_SHA256_RE.fullmatch(str(image_digest or "")) is None:
            return {"ok": False, "reason": "ocr_page_image_digest_invalid"}
        if _FULL_SHA256_RE.fullmatch(str(text_digest or "")) is None:
            return {"ok": False, "reason": "ocr_page_text_digest_invalid"}
        if status == "text" and text_digest == _EMPTY_TEXT_SHA256:
            return {"ok": False, "reason": "ocr_text_proof_invalid"}
        if status in {"blank", "graphics_only"} and text_digest != _EMPTY_TEXT_SHA256:
            return {"ok": False, "reason": "ocr_no_text_proof_invalid"}
    raw_pages = str(extract_text).split("\f")
    if len(raw_pages) != declared_pages:
        return {"ok": False, "reason": "ocr_extract_page_count_mismatch"}
    actual_extract_page_sha256 = [
        hashlib.sha256(page.encode("utf-8")).hexdigest()
        for page in raw_pages
    ]
    if extract_page_sha256 != actual_extract_page_sha256:
        return {"ok": False, "reason": "ocr_extract_page_digest_mismatch"}
    if blank_pages != [
        index
        for index, status in enumerate(statuses, start=1)
        if status == "blank"
    ]:
        return {"ok": False, "reason": "ocr_blank_page_manifest_invalid"}
    expected_graphics_only_pages = [
        index
        for index, status in enumerate(statuses, start=1)
        if status == "graphics_only"
    ]
    graphics_only_pages = record.get("ocr_graphics_only_pages")
    no_text_locators = record.get("ocr_no_text_locators")
    if proof_version == "ocr-page-proof-v3":
        if graphics_only_pages != expected_graphics_only_pages:
            return {"ok": False, "reason": "ocr_graphics_only_manifest_invalid"}
        expected_no_text_locators = [
            {
                "page": page,
                "status": "graphics_only",
                "reason": "no_machine_readable_text",
                "page_image_sha256": image_sha256[page - 1],
                "no_text_locator": True,
            }
            for page in expected_graphics_only_pages
        ]
        if no_text_locators != expected_no_text_locators:
            return {"ok": False, "reason": "ocr_no_text_locator_invalid"}
    elif expected_graphics_only_pages:
        return {"ok": False, "reason": "ocr_graphics_only_version_invalid"}
    return {
        "ok": True,
        "page_eligibility": [
            {
                "page": index,
                "status": status,
                "evidence_eligible": status == "text",
                "no_text_locator": status != "text",
                "page_image_sha256": image_sha256[index - 1],
            }
            for index, status in enumerate(statuses, start=1)
        ],
    }


def resolve_trusted_ingest_record(
    record: Mapping[str, Any] | None,
    *,
    workspace_root: str | Path | None = None,
    read_text: bool = False,
) -> dict[str, Any]:
    """Revalidate one ingest audit row against current source/extract bytes."""

    rec = dict(record or {})
    sha256 = str(rec.get("sha256") or "").strip().lower()
    file_id = str(rec.get("file_id") or "").strip().lower()
    extract_sha256 = str(rec.get("extract_text_sha256") or "").strip().lower()
    raw_filename = str(rec.get("filename") or "").strip()
    filename = Path(raw_filename).name
    if (
        not raw_filename
        or raw_filename != filename
        or "/" in raw_filename
        or "\\" in raw_filename
    ):
        return {"ok": False, "reason": "audit_filename_invalid"}
    if (
        _FULL_SHA256_RE.fullmatch(sha256) is None
        or _FULL_SHA256_RE.fullmatch(file_id) is None
        or sha256 != file_id
    ):
        return {"ok": False, "reason": "audit_sha_file_id_mismatch"}
    if rec.get("enabled") is False or rec.get("usable") is False:
        return {"ok": False, "reason": "audit_record_disabled"}
    if _FULL_SHA256_RE.fullmatch(extract_sha256) is None:
        return {"ok": False, "reason": "extract_text_sha256_mismatch"}

    declared_workspace = Path(str(rec.get("workspace_dir") or ""))
    if not str(rec.get("workspace_dir") or "").strip() or ".." in (
        declared_workspace.parts
    ):
        return {"ok": False, "reason": "audit_workspace_mismatch"}

    expected_workspace = Path(
        workspace_root if workspace_root is not None else declared_workspace
    ).resolve(strict=False)
    if declared_workspace.is_absolute():
        declared_matches = (
            declared_workspace.resolve(strict=False) == expected_workspace
        )
    else:
        declared_parts = declared_workspace.parts
        declared_matches = bool(
            declared_parts
            and len(expected_workspace.parts) >= len(declared_parts)
            and expected_workspace.parts[-len(declared_parts) :] == declared_parts
        )
    if not declared_matches:
        return {"ok": False, "reason": "audit_workspace_mismatch"}

    def _resolve_audit_path(raw_value: Any) -> Path:
        raw_path = Path(str(raw_value or ""))
        if raw_path.is_absolute():
            return raw_path
        if ".." in raw_path.parts:
            return raw_path
        if not declared_workspace.is_absolute():
            try:
                relative = raw_path.relative_to(declared_workspace)
            except ValueError:
                return raw_path
            return expected_workspace / relative
        return raw_path

    source_path = _resolve_audit_path(rec.get("saved_as"))
    extract_path = _resolve_audit_path(rec.get("extract_saved_as"))
    if (
        not filename
        or source_path.is_symlink()
        or not source_path.is_file()
        or not _is_within(source_path, expected_workspace / "uploads")
        or source_path.name != f"{sha256}_{filename}"
    ):
        return {
            "ok": False,
            "reason": "source_path_outside_workspace_or_not_full_sha",
        }
    if (
        extract_path.is_symlink()
        or not extract_path.is_file()
        or not _is_within(extract_path, expected_workspace / "extracts")
        or extract_path.name != f"{sha256}_{extract_sha256}.txt"
    ):
        return {
            "ok": False,
            "reason": "extract_path_outside_workspace_or_not_full_sha",
        }
    validate_page_proof = str(
        rec.get("ocr_cache_policy") or ""
    ).strip() in _FULL_PAGE_OCR_POLICIES
    retain_extract_bytes = read_text or validate_page_proof
    try:
        if _file_sha256(source_path) != sha256:
            return {"ok": False, "reason": "source_bytes_sha256_mismatch"}
        actual_extract_sha256, extract_bytes = _read_regular_file_snapshot(
            extract_path,
            retain_bytes=retain_extract_bytes,
        )
        if actual_extract_sha256 != extract_sha256:
            return {"ok": False, "reason": "extract_text_sha256_mismatch"}
        extract_text = (
            bytes(extract_bytes or b"").decode("utf-8")
            if retain_extract_bytes
            else None
        )
        page_proof = _validate_full_page_ocr_record(
            rec,
            str(extract_text or ""),
        )
        if page_proof.get("ok") is not True:
            return {
                "ok": False,
                "reason": str(
                    page_proof.get("reason") or "ocr_page_proof_invalid"
                ),
            }
        source_relative_path = str(
            source_path.resolve(strict=True).relative_to(expected_workspace)
        )
        extract_relative_path = str(
            extract_path.resolve(strict=True).relative_to(expected_workspace)
        )
    except (OSError, UnicodeError, ValueError):
        return {"ok": False, "reason": "evidence_file_unreadable"}

    result = {
        "ok": True,
        "reason": "trusted",
        "record": rec,
        "audit_row_digest": _canonical_digest(rec),
        "project_id": str(rec.get("project_id") or "").strip(),
        "filename": filename,
        "source_sha256": sha256,
        "extract_text_sha256": extract_sha256,
        "workspace_root": str(expected_workspace),
        "source_path": str(source_path),
        "extract_path": str(extract_path),
        "source_relative_path": source_relative_path,
        "extract_relative_path": extract_relative_path,
        "ocr_page_eligibility": list(
            page_proof.get("page_eligibility") or []
        ),
    }
    if read_text:
        result["extract_text"] = extract_text
    return result


def build_ingest_evidence_set_receipt(
    *,
    project_id: str,
    audit_path: str | Path,
    trusted_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Seal the exact current audit rows and source/extract byte identities."""

    path = Path(audit_path).resolve(strict=False)
    workspace_root = path.parent.parent.resolve(strict=False)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected_project_id = str(project_id or "").strip()
    for trusted in trusted_records:
        if (
            trusted.get("ok") is not True
            or str(trusted.get("project_id") or "").strip()
            != expected_project_id
        ):
            continue
        source_sha256 = str(trusted.get("source_sha256") or "").strip().lower()
        if source_sha256 in seen:
            continue
        seen.add(source_sha256)
        records.append(
            {
                "audit_row_digest": str(trusted.get("audit_row_digest") or ""),
                "project_id": str(trusted.get("project_id") or ""),
                "filename": str(trusted.get("filename") or ""),
                "source_sha256": source_sha256,
                "extract_text_sha256": str(
                    trusted.get("extract_text_sha256") or ""
                ).strip().lower(),
                "source_relative_path": str(
                    trusted.get("source_relative_path") or ""
                ),
                "extract_relative_path": str(
                    trusted.get("extract_relative_path") or ""
                ),
            }
        )
    records.sort(key=lambda row: (row["source_sha256"], row["filename"]))
    core = {
        "schema_version": INGEST_EVIDENCE_SET_RECEIPT_SCHEMA,
        "project_id": expected_project_id,
        "workspace_root": str(workspace_root),
        "audit_path": str(path),
        "records": records,
    }
    return {**core, "receipt_digest": _canonical_digest(core)}


def validate_ingest_evidence_set_receipt(
    receipt: Mapping[str, Any] | None,
    *,
    expected_project_id: str | None = None,
    audit_lines: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Re-read the latest audit rows and current bytes bound by a receipt."""

    value = dict(receipt or {})
    errors: list[str] = []
    core = {key: item for key, item in value.items() if key != "receipt_digest"}
    claimed_digest = str(value.get("receipt_digest") or "").strip().lower()
    if value.get("schema_version") != INGEST_EVIDENCE_SET_RECEIPT_SCHEMA:
        errors.append("receipt_schema_invalid")
    if (
        _FULL_SHA256_RE.fullmatch(claimed_digest) is None
        or claimed_digest != _canonical_digest(core)
    ):
        errors.append("receipt_digest_mismatch")
    project_id = str(value.get("project_id") or "").strip()
    if not project_id or (
        expected_project_id is not None
        and project_id != str(expected_project_id or "").strip()
    ):
        errors.append("receipt_project_mismatch")

    workspace_root = Path(str(value.get("workspace_root") or ""))
    audit_path = Path(str(value.get("audit_path") or ""))
    records = value.get("records") if isinstance(value.get("records"), list) else []
    if not records:
        errors.append("receipt_records_missing")
    if (
        not workspace_root.is_absolute()
        or not audit_path.is_absolute()
        or audit_path.is_symlink()
        or not audit_path.is_file()
        or not _is_within(audit_path, workspace_root / "audit")
        or audit_path.parent.resolve(strict=False)
        != (workspace_root / "audit").resolve(strict=False)
        or audit_path.name != "ingest.jsonl"
    ):
        errors.append("receipt_audit_path_invalid")
        current_rows: dict[tuple[str, str], dict[str, Any]] = {}
    else:
        current_rows = {}
        if audit_lines is not None:
            lines = list(audit_lines)
        else:
            try:
                lines = audit_path.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
            except OSError:
                errors.append("receipt_audit_unreadable")
                lines = []
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            sha256 = str(row.get("sha256") or "").strip().lower()
            row_project_id = str(row.get("project_id") or "").strip()
            content_id = (row_project_id, sha256)
            if sha256 and content_id not in current_rows:
                current_rows[content_id] = row

    seen: set[str] = set()
    for raw in records:
        if not isinstance(raw, Mapping):
            errors.append("receipt_record_invalid")
            continue
        source_sha256 = str(raw.get("source_sha256") or "").strip().lower()
        if source_sha256 in seen:
            errors.append("receipt_record_duplicate")
            continue
        seen.add(source_sha256)
        current = current_rows.get((project_id, source_sha256))
        if not isinstance(current, dict):
            errors.append("receipt_audit_row_missing")
            continue
        trusted = resolve_trusted_ingest_record(
            current,
            workspace_root=workspace_root,
        )
        if trusted.get("ok") is not True:
            errors.append(str(trusted.get("reason") or "receipt_record_untrusted"))
            continue
        if str(trusted.get("project_id") or "").strip() != project_id:
            errors.append("receipt_record_project_mismatch")
            continue
        expected = {
            "audit_row_digest": trusted["audit_row_digest"],
            "project_id": trusted["project_id"],
            "filename": trusted["filename"],
            "source_sha256": trusted["source_sha256"],
            "extract_text_sha256": trusted["extract_text_sha256"],
            "source_relative_path": trusted["source_relative_path"],
            "extract_relative_path": trusted["extract_relative_path"],
        }
        if dict(raw) != expected:
            errors.append("receipt_record_mismatch")

    return {
        "ok": not errors,
        "errors": list(dict.fromkeys(errors)),
        "claimed_digest": claimed_digest,
        "computed_digest": _canonical_digest(core),
        "record_count": len(records),
    }


def _tokenize_query(query: str) -> list[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+", query or "")
    uniq: list[str] = []
    seen = set()
    for t in tokens:
        tt = t.strip()
        if len(tt) < 2:
            continue
        if tt not in seen:
            seen.add(tt)
            uniq.append(tt)
    return uniq


_GENERIC_DRAWING_MATCH_TOKENS = {
    "工程",
    "施工",
    "施工工艺",
    "施工方法",
    "施工方案",
    "技术措施",
    "安装",
    "作业",
    "工艺",
    "工序",
    "流程",
    "通用",
    "图纸",
    "图",
    "详见图纸",
    "施工图纸",
    "施工图",
    "图纸说明",
    "详图",
    "大样",
    "节点",
    "详见",
    "说明",
    "做法",
    "材料",
    "项目",
}


def _drawing_specific_query(query: str) -> str:
    """Drop tokens that can only prove that a document is drawing-like.

    A drawing lookup must be anchored by an item/process term.  Generic words
    such as ``图纸`` and ``详见图纸`` may be useful filename hints, but they
    must never become the matched evidence token.
    """

    def _fully_decomposable_as_generic(token: str) -> bool:
        normalized = token.casefold()
        reachable = [False] * (len(normalized) + 1)
        reachable[0] = True
        for start in range(len(normalized)):
            if not reachable[start]:
                continue
            for generic in _GENERIC_DRAWING_MATCH_TOKENS:
                if normalized.startswith(generic.casefold(), start):
                    reachable[start + len(generic)] = True
        return reachable[-1]

    tokens: list[str] = []
    for token in _tokenize_query(query):
        if not _fully_decomposable_as_generic(token):
            tokens.append(token)
    return " ".join(tokens)


@lru_cache(maxsize=8)
def _load_audit_records(audit_path: str, mtime_ns: int) -> list[dict]:
    # Cache parsed audit records for repeated searches during one autoplan run.
    p = Path(audit_path)
    if not p.exists():
        return []
    out: list[dict] = []
    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


@lru_cache(maxsize=64)
def _load_extract_text(extract_path: str, mtime_ns: int) -> str:
    p = Path(extract_path)
    if not p.exists() or not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def format_hit_locator(hit: dict[str, Any]) -> str:
    """
    Convert a hit dict into a traceable locator string for evidence markers:
    - filename#p{page}_{full_sha256}@{offset}
    - filename

    A page locator is emitted only when the source identity is a complete
    SHA-256 and the page boundary was established by the extractor.  Short
    hash prefixes and page-less offsets are not reversible identities.
    """
    fname = str(hit.get("filename") or "unknown")
    sha256 = str(hit.get("sha256") or "").strip().lower()
    offset = hit.get("offset")
    page = hit.get("page")
    loc = None
    try:
        if (
            offset is not None
            and page is not None
            and re.fullmatch(r"[0-9a-f]{64}", sha256)
        ):
            loc = f"p{int(page)}_{sha256}@{int(offset)}"
    except (TypeError, ValueError, OverflowError):
        loc = None
    return f"{fname}#{loc}" if loc else fname


def _declared_page_count(record: dict[str, Any]) -> int | None:
    raw = record.get("pages")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _match_page_context(
    text: str,
    *,
    match_start: int,
    match_end: int,
    declared_pages: int | None,
) -> dict[str, Any]:
    """Return a bounded hit window only when page boundaries are reliable."""

    if "\f" in text:
        page_parts = text.split("\f")
        if declared_pages is not None and len(page_parts) != declared_pages:
            return {
                "page": None,
                "page_boundary_status": "unreliable_page_count_mismatch",
            }
        page = text[:match_start].count("\f") + 1
        page_start = text.rfind("\f", 0, match_start) + 1
        next_boundary = text.find("\f", match_end)
        page_end = len(text) if next_boundary < 0 else next_boundary
        boundary_source = "form_feed"
    elif declared_pages == 1:
        page = 1
        page_start = 0
        page_end = len(text)
        boundary_source = "declared_single_page"
    else:
        return {
            "page": None,
            "page_boundary_status": "unreliable_missing_page_boundaries",
        }

    page_text = text[page_start:page_end]
    window_start = max(page_start, match_start - 80)
    window_end = min(page_end, match_end + 160)
    window_text = text[window_start:window_end]
    compact_window = " ".join(window_text.replace("\f", " ").split())
    compact_page = " ".join(page_text.replace("\f", " ").split())
    matched_text = text[match_start:match_end]
    return {
        "page": page,
        "page_start_offset": page_start,
        "page_end_offset": page_end,
        "page_text_sha256": hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
        "page_summary": compact_page[:360],
        "page_boundary_status": f"reliable_{boundary_source}",
        "match_start": match_start,
        "match_end": match_end,
        "matched_text": matched_text,
        "match_window": {
            "start_offset": window_start,
            "end_offset": window_end,
            "text": window_text,
            "text_sha256": hashlib.sha256(window_text.encode("utf-8")).hexdigest(),
            "summary": compact_window,
        },
    }


def _ocr_text_evidence_allowed(
    record: dict[str, Any],
    page_context: dict[str, Any],
) -> bool:
    """Fail closed when a full-page OCR slot is not eligible text evidence."""

    policy = str(record.get("ocr_cache_policy") or "").strip()
    is_pdf = (
        str(record.get("doc_type") or "").strip().lower() == "pdf"
        or Path(str(record.get("filename") or "")).suffix.lower() == ".pdf"
    )
    if policy not in _FULL_PAGE_OCR_POLICIES or not is_pdf:
        return True
    page = page_context.get("page")
    declared_pages = _declared_page_count(record)
    statuses = record.get("ocr_page_statuses")
    text_sha256 = record.get("ocr_page_text_sha256")
    extract_page_sha256 = record.get("ocr_extract_page_sha256")
    try:
        page_number = int(page)
    except (TypeError, ValueError):
        return False
    if (
        record.get("ocr_page_proof_version")
        not in {"ocr-page-proof-v2", "ocr-page-proof-v3"}
        or record.get("ocr_page_mapping") != "source_page_all"
        or declared_pages is None
        or not 1 <= page_number <= declared_pages
        or not isinstance(statuses, list)
        or not isinstance(text_sha256, list)
        or not isinstance(extract_page_sha256, list)
        or len(statuses) != declared_pages
        or len(text_sha256) != declared_pages
        or len(extract_page_sha256) != declared_pages
        or statuses[page_number - 1] != "text"
        or text_sha256[page_number - 1] == hashlib.sha256(b"").hexdigest()
        or extract_page_sha256[page_number - 1]
        != page_context.get("page_text_sha256")
    ):
        return False
    if record.get("ocr_page_proof_version") == "ocr-page-proof-v3":
        graphics_only_pages = record.get("ocr_graphics_only_pages")
        no_text_locators = record.get("ocr_no_text_locators")
        if not isinstance(graphics_only_pages, list) or not isinstance(
            no_text_locators,
            list,
        ):
            return False
        if page_number in graphics_only_pages or any(
            isinstance(item, Mapping) and item.get("page") == page_number
            for item in no_text_locators
        ):
            return False
    return True


def _tags_match(
    rec_tags: Any,
    *,
    require_tags: Iterable[str] | None = None,
    exclude_tags: Iterable[str] | None = None,
) -> bool:
    tags = rec_tags if isinstance(rec_tags, list) else []
    tags_set = {str(t).strip() for t in tags if str(t).strip()}
    if require_tags:
        req = {str(t).strip() for t in require_tags if str(t).strip()}
        if req and not req.issubset(tags_set):
            return False
    if exclude_tags:
        ex = {str(t).strip() for t in exclude_tags if str(t).strip()}
        if ex and tags_set.intersection(ex):
            return False
    return True


def search_ingested_docs(
    query: str,
    limit: int = 6,
    *,
    project_id: str | None = None,
    require_tags: Iterable[str] | None = None,
    exclude_tags: Iterable[str] | None = None,
    audit_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    resolved_audit_path = (
        Path(audit_path)
        if audit_path is not None and str(audit_path).strip()
        else Path("backend/data/audit/ingest.jsonl")
    )
    if (
        resolved_audit_path.is_symlink()
        or not resolved_audit_path.is_file()
        or resolved_audit_path.name != "ingest.jsonl"
        or resolved_audit_path.parent.name != "audit"
    ):
        return []
    uniq = _tokenize_query(query)
    if not uniq:
        return []
    hits: list[dict[str, Any]] = []
    try:
        mtime_ns = int(os.stat(resolved_audit_path).st_mtime_ns)
    except OSError:
        mtime_ns = 0
    workspace_root = resolved_audit_path.parent.parent.resolve(strict=False)
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    seen_content_ids: set[tuple[str, str]] = set()
    for rec in _load_audit_records(str(resolved_audit_path), mtime_ns):
        record_project_id = str(rec.get("project_id") or "").strip()
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        source_sha256 = str(rec.get("sha256") or "").strip().lower()
        if _FULL_SHA256_RE.fullmatch(source_sha256) is None:
            continue
        content_id = (record_project_id, source_sha256)
        if content_id in seen_content_ids:
            continue
        # Audit rows are newest-first.  Occupy the content identity before
        # status, tag, and byte validation so a stale row cannot resurrect
        # evidence disabled or superseded by the newest row.
        seen_content_ids.add(content_id)
        if not _tags_match(
            effective_record_tags(rec),
            require_tags=require_tags,
            exclude_tags=exclude_tags,
        ):
            continue
        trusted = resolve_trusted_ingest_record(
            rec,
            workspace_root=workspace_root,
            read_text=True,
        )
        if trusted.get("ok") is not True:
            continue
        p = Path(str(trusted["extract_path"]))
        text = str(trusted.get("extract_text") or "")
        if not text:
            continue
        for tok in uniq:
            for match in re.finditer(re.escape(tok), text, flags=re.IGNORECASE):
                page_context = _match_page_context(
                    text,
                    match_start=match.start(),
                    match_end=match.end(),
                    declared_pages=_declared_page_count(rec),
                )
                if not _ocr_text_evidence_allowed(rec, page_context):
                    continue
                match_window = page_context.get("match_window")
                snippet = (
                    str(match_window.get("summary") or "")
                    if isinstance(match_window, dict)
                    else " ".join(
                        text[
                            max(0, match.start() - 80) : min(
                                len(text),
                                match.end() + 160,
                            )
                        ].split()
                    )
                )
                hits.append(
                    {
                        "filename": rec.get("filename"),
                        "sha256": trusted["source_sha256"],
                        "extract_saved_as": str(p),
                        "extract_text_sha256": trusted["extract_text_sha256"],
                        "audit_row_digest": trusted["audit_row_digest"],
                        "offset": match.start(),
                        "snippet": snippet,
                        "matched_token": tok,
                        **page_context,
                    }
                )
                if len(hits) >= limit:
                    return hits
                break
    return hits


def best_ingested_hit(
    query: str,
    limit: int = 8,
    prefer_filename_keywords: Iterable[str] | None = None,
    project_id: str | None = None,
    require_tags: Iterable[str] | None = None,
    exclude_tags: Iterable[str] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """
    Pick the best hit for a query. Used for auto-citing BoQ items and for evidence traceability remediation.
    """
    hits = search_ingested_docs(
        query,
        limit=limit,
        project_id=project_id,
        require_tags=require_tags,
        exclude_tags=exclude_tags,
        audit_path=audit_path,
    )
    if not hits:
        return None
    tokens = _tokenize_query(query)
    prefer = [str(x) for x in (prefer_filename_keywords or []) if str(x).strip()]

    def _score(h: dict[str, Any]) -> float:
        fname = str(h.get("filename") or "")
        snippet = str(h.get("snippet") or "")
        low_snip = snippet.lower()
        sc = 0.0
        for t in tokens:
            tl = t.lower()
            if tl and tl in low_snip:
                sc += 2.0
            elif t and t in fname:
                sc += 0.8
        for k in prefer:
            if k and k in fname:
                sc += 2.5
        if h.get("page") is not None:
            sc += 0.4
        if h.get("offset") is not None and h.get("sha256"):
            sc += 1.2
        return sc

    best = max(hits, key=_score)
    out = dict(best)
    out["locator"] = format_hit_locator(best)
    return out


def best_drawing_hit(
    query: str,
    limit: int = 8,
    prefer_filename_keywords: Iterable[str] | None = None,
    project_id: str | None = None,
    require_tags: Iterable[str] | None = None,
    exclude_tags: Iterable[str] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Return a drawing hit only when a non-generic query token matched.

    This intentionally delegates identity/page-window construction and score
    ordering to :func:`best_ingested_hit`; only the candidate query is
    narrowed.  If every token is generic, the lookup fails closed.
    """

    specific_query = _drawing_specific_query(query)
    if not specific_query:
        return None
    return best_ingested_hit(
        specific_query,
        limit=limit,
        prefer_filename_keywords=prefer_filename_keywords,
        project_id=project_id,
        require_tags=require_tags,
        exclude_tags=exclude_tags,
        audit_path=audit_path,
    )


def list_ingested_filenames_by_tag(
    tag: str,
    *,
    project_id: str | None = None,
    limit: int = 80,
    exclude_tags: Iterable[str] | None = None,
) -> list[str]:
    """
    List unique ingested filenames for a given tag from ingest audit.
    Useful for:
    - checking whether drawings/standards exist for a project
    - cross-index evidence typing (drawing vs standard)
    """
    audit_path = Path("backend/data/audit/ingest.jsonl")
    if not audit_path.exists():
        return []
    t = str(tag or "").strip()
    if not t:
        return []
    try:
        mtime_ns = int(os.stat(audit_path).st_mtime_ns)
    except OSError:
        mtime_ns = 0
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    ex = {str(x).strip() for x in (exclude_tags or []) if str(x).strip()}
    out: list[str] = []
    seen = set()
    for rec in _load_audit_records(str(audit_path), mtime_ns):
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        tags = effective_record_tags(rec)
        tags_set = {str(x).strip() for x in tags if str(x).strip()}
        if t not in tags_set:
            continue
        if ex and tags_set.intersection(ex):
            continue
        fn = str(rec.get("filename") or "").strip()
        if not fn or fn in seen:
            continue
        seen.add(fn)
        out.append(fn)
        if len(out) >= max(1, int(limit or 0)):
            break
    return out
