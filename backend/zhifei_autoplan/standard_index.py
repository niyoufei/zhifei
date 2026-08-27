from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.compliance_policy import (
    canonical_standard_code,
    extract_standard_codes,
    is_verified_standard_metadata,
)
from backend.zhifei_autoplan.compliance_runtime import (
    _compliance_root,
    _load_official_registry,
)
from backend.zhifei_autoplan.evidence import (
    format_hit_locator,
    resolve_trusted_ingest_record,
)
from backend.zhifei_autoplan.ingest_tags import effective_record_tags

_HAN_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_MEANINGFUL_TEXT_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")
_FULL_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_EMPTY_TEXT_SHA256 = hashlib.sha256(b"").hexdigest()
_SUPPORTED_OCR_PAGE_PROOF_VERSIONS = {
    "ocr-page-proof-v2",
    "ocr-page-proof-v3",
}
_STOP = {
    "工程",
    "施工",
    "标准",
    "企业标准",
    "作业",
    "作业指导",
    "指导",
    "工法",
    "图集",
    "规范",
    "要求",
    "技术",
    "管理",
    "项目",
}
_GENERIC_QUERY_PARTS = (
    "主要施工",
    "施工组织设计",
    "施工方法",
    "施工工艺",
    "施工方案",
    "技术措施",
    "作业方法",
    "作业指导",
    "工艺流程",
    "企业标准",
    "标准化",
    "标准",
    "规范",
    "质量验收",
    "质量",
    "专项方案",
    "专项",
    "工程",
    "施工",
    "工序",
    "工艺",
    "要求",
)


def list_verified_standard_metadata() -> list[dict[str, Any]]:
    """Read official metadata without building or mutating the runtime catalog."""

    try:
        rows = _load_official_registry(_compliance_root())
    except Exception:  # noqa: BLE001 - optional read-only enrichment fails closed
        return []
    return [
        dict(row)
        for row in rows
        if isinstance(row, dict) and is_verified_standard_metadata(row)
    ]


def _top_keywords(text: str, limit: int = 12) -> list[str]:
    source = (text or "").strip()
    if not source:
        return []
    tokens = [
        token.strip()
        for token in _HAN_TOKEN_RE.findall(source[:8000])
        if token and len(token) >= 2
    ]
    frequencies: dict[str, int] = {}
    for token in tokens:
        if token in _STOP or len(token) >= 14:
            continue
        frequencies[token] = frequencies.get(token, 0) + 1
    ranked = sorted(
        frequencies.items(),
        key=lambda item: (-item[1], -len(item[0]), item[0]),
    )
    return [keyword for keyword, _count in ranked[: max(0, int(limit or 0))]]


def _is_key_process_chapter(title: str) -> bool:
    keys = (
        "施工方法",
        "施工工艺",
        "施工方案",
        "主要施工",
        "工序",
        "专项",
        "技术措施",
        "作业方法",
        "工艺流程",
        "质量",
    )
    return any(key in str(title or "") for key in keys)


def _specific_query_terms(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", normalized)
    candidates = ["".join(chunks)] if chunks else []
    candidates.extend(chunks)
    terms: list[str] = []
    for candidate in candidates:
        term = candidate.strip()
        for generic in _GENERIC_QUERY_PARTS:
            term = term.replace(generic, "")
        term = term.strip()
        if len(term) < 2 or term in _STOP or term in terms:
            continue
        terms.append(term)
    return sorted(terms, key=lambda term: (-len(term), term))


def _declared_page_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value > 0 else None


def _normalized_identity_name(value: Any) -> str:
    return re.sub(
        r"[^0-9a-zA-Z\u4e00-\u9fff]+",
        "",
        unicodedata.normalize("NFKC", str(value or "")).casefold(),
    )


def _unique_standard_codes(value: Any) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for code in extract_standard_codes(value):
        canonical = canonical_standard_code(code)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        result.append(code)
    return result


def _document_standard_identity(
    filename: str,
    extract_text: str,
) -> dict[str, Any]:
    # Registry identity is deliberately limited to the filename and the title
    # region of the cover.  Codes appearing later in the document remain
    # references and cannot verify this document's identity.
    cover_text = str(extract_text or "").split("\f", 1)[0][:1600]
    filename_codes = _unique_standard_codes(Path(filename).stem)
    cover_codes = _unique_standard_codes(cover_text)
    filename_primary = filename_codes[0] if len(filename_codes) == 1 else None
    cover_primary = cover_codes[0] if len(cover_codes) == 1 else None
    status = "identified"
    if len(filename_codes) > 1 or len(cover_codes) > 1:
        primary = None
        status = "primary_identity_ambiguous"
    elif filename_primary and cover_primary and canonical_standard_code(
        filename_primary
    ) != canonical_standard_code(cover_primary):
        primary = None
        status = "primary_identity_conflict"
    else:
        primary = filename_primary or cover_primary
        if primary is None:
            status = "primary_identity_missing"
    all_codes = _unique_standard_codes(
        f"{filename}\n{str(extract_text or '')[:1_000_000]}"
    )
    primary_canonical = canonical_standard_code(primary)
    referenced_codes = [
        code
        for code in all_codes
        if canonical_standard_code(code) != primary_canonical
    ]
    cover_identity_text = cover_text[:600]
    if primary:
        primary_offset = cover_text.casefold().find(str(primary).casefold())
        if primary_offset >= 0:
            cover_identity_text = cover_text[
                max(0, primary_offset - 120) : primary_offset + len(primary) + 600
            ]
    return {
        "primary_code": primary,
        "status": status,
        "filename_codes": filename_codes,
        "cover_codes": cover_codes,
        "all_codes": all_codes,
        "referenced_codes": referenced_codes,
        "identity_text": f"{Path(filename).stem}\n{cover_identity_text}",
    }


def _standard_pdf_ocr_proof(
    record: dict[str, Any],
    declared_pages: int | None,
    extract_text: str,
) -> tuple[list[str], str]:
    if declared_pages is None:
        return [], "ocr_declared_pages_missing"
    statuses = record.get("ocr_page_statuses")
    image_sha256 = record.get("ocr_page_image_sha256")
    text_sha256 = record.get("ocr_page_text_sha256")
    extract_page_sha256 = record.get("ocr_extract_page_sha256")
    blank_pages = record.get("ocr_blank_pages")
    proof_version = record.get("ocr_page_proof_version")
    if (
        record.get("ocr_cache_policy") != "standard_full_page"
        or proof_version not in _SUPPORTED_OCR_PAGE_PROOF_VERSIONS
        or record.get("ocr_page_mapping") != "source_page_all"
        or record.get("ocr_error") not in {None, ""}
        or _declared_page_count(record.get("ocr_source_pages"))
        != declared_pages
        or _declared_page_count(record.get("ocr_pages")) != declared_pages
        or _declared_page_count(record.get("ocr_page_text_count"))
        != declared_pages
        or not isinstance(statuses, list)
        or not isinstance(image_sha256, list)
        or not isinstance(text_sha256, list)
        or not isinstance(extract_page_sha256, list)
        or not isinstance(blank_pages, list)
        or len(statuses) != declared_pages
        or len(image_sha256) != declared_pages
        or len(text_sha256) != declared_pages
        or len(extract_page_sha256) != declared_pages
    ):
        return [], "ocr_page_proof_incomplete"
    if proof_version == "ocr-page-proof-v3" and (
        record.get("ocr_graphics_only_pages") != []
        or record.get("ocr_no_text_locators") != []
    ):
        return [], "ocr_page_proof_incomplete"
    for status, image_digest, text_digest in zip(
        statuses,
        image_sha256,
        text_sha256,
        strict=True,
    ):
        if status not in {"text", "blank"}:
            return [], "ocr_page_failed_or_unreadable"
        if not isinstance(image_digest, str) or not _FULL_SHA256_RE.fullmatch(
            image_digest
        ):
            return [], "ocr_image_proof_invalid"
        if not isinstance(text_digest, str) or not _FULL_SHA256_RE.fullmatch(
            text_digest
        ):
            return [], "ocr_text_proof_invalid"
        if status == "blank" and text_digest != _EMPTY_TEXT_SHA256:
            return [], "ocr_blank_proof_invalid"
        if status == "text" and text_digest == _EMPTY_TEXT_SHA256:
            return [], "ocr_text_proof_invalid"
    raw_pages = str(extract_text).split("\f")
    if len(raw_pages) != declared_pages:
        return [], "ocr_extract_page_proof_incomplete"
    actual_extract_page_sha256 = [
        hashlib.sha256(page.encode("utf-8")).hexdigest()
        for page in raw_pages
    ]
    if extract_page_sha256 != actual_extract_page_sha256:
        return [], "ocr_extract_page_digest_mismatch"
    if blank_pages != [
        index
        for index, status in enumerate(statuses, start=1)
        if status == "blank"
    ]:
        return [], "ocr_blank_page_manifest_mismatch"
    return [str(status) for status in statuses], "complete"


def _page_anchors(
    text: str,
    *,
    filename: str,
    sha256: str,
    declared_pages: int | None,
    page_statuses: list[str] | None = None,
    require_full_coverage: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    raw_text = str(text or "")
    if (
        not raw_text
        and require_full_coverage
        and declared_pages == 1
        and page_statuses == ["blank"]
    ):
        raw_pages = [""]
        boundary_source = "declared_single_page"
    elif not raw_text:
        return [], "missing_text_or_ocr"
    elif "\f" in raw_text:
        raw_pages = raw_text.split("\f")
        if declared_pages is not None and len(raw_pages) != declared_pages:
            return [], "unreliable_page_count_mismatch"
        boundary_source = "form_feed"
    elif declared_pages == 1:
        raw_pages = [raw_text]
        boundary_source = "declared_single_page"
    else:
        return [], "unreliable_missing_page_boundaries"

    anchors: list[dict[str, Any]] = []
    start = 0
    for page, raw_page in enumerate(raw_pages, start=1):
        end = start + len(raw_page)
        compact = " ".join(raw_page.split())
        meaningful = len(_MEANINGFUL_TEXT_RE.findall(compact)) >= 2
        ocr_status = (
            page_statuses[page - 1]
            if isinstance(page_statuses, list) and page <= len(page_statuses)
            else None
        )
        if require_full_coverage and ocr_status not in {"text", "blank"}:
            return [], "unreliable_ocr_page_proof_incomplete"
        if meaningful or (require_full_coverage and ocr_status in {"text", "blank"}):
            anchors.append(
                {
                    "page": page,
                    "start_offset": start,
                    "end_offset": end,
                    "text_sha256": hashlib.sha256(raw_page.encode("utf-8")).hexdigest(),
                    "keywords": _top_keywords(raw_page, limit=10),
                    "snippet": compact[:360],
                    "boundary_source": boundary_source,
                    "ocr_status": ocr_status,
                    "blank_proven": ocr_status == "blank",
                    "evidence_eligible": meaningful and ocr_status != "blank",
                    "locator": format_hit_locator(
                        {
                            "filename": filename,
                            "sha256": sha256,
                            "page": page,
                            "offset": start,
                        }
                    ),
                }
            )
        start = end + 1
    if (
        require_full_coverage
        and declared_pages is not None
        and len(anchors) != declared_pages
    ):
        return [], "unreliable_page_anchor_coverage_incomplete"
    return anchors, f"reliable_{boundary_source}"


def _audit_path(workspace_dir: str | Path | None) -> Path:
    if workspace_dir is not None and str(workspace_dir).strip():
        return Path(workspace_dir) / "audit" / "ingest.jsonl"
    return Path("backend/data/audit/ingest.jsonl")


def _empty_index(
    *,
    project_id: str | None,
    reason: str,
    audit_path: Path,
) -> dict[str, Any]:
    return {
        "ok": False,
        "project_id": project_id,
        "audit_path": str(audit_path),
        "standards": [],
        "chapter_bindings": [],
        "indexed_standard_count": 0,
        "missing_text_or_ocr_count": 0,
        "locator_unavailable_count": 0,
        "official_registry_verified_count": 0,
        "metadata_only_registry_count": 0,
        "invalid_identity_count": 0,
        "integrity_rejection_count": 0,
        "integrity_rejections": [],
        "text_index_status": reason,
        "chapter_binding_status": reason,
        "clause_evidence_policy": (
            "ingested_page_anchor_required; registry_metadata_alone_is_not_clause_evidence"
        ),
        "reason": reason,
    }


def _official_registry_map() -> dict[str, dict[str, Any]]:
    try:
        rows = list_verified_standard_metadata()
    except Exception:  # noqa: BLE001 - optional registry enrichment fails closed
        rows = []
    registry: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        canonical = canonical_standard_code(row.get("standard_code"))
        if not canonical:
            continue
        current = registry.get(canonical)
        if current is None:
            registry[canonical] = dict(row)
            continue
        if current.get("_registry_ambiguous") is True:
            continue
        current_name = _normalized_identity_name(
            current.get("source_name") or current.get("standard_name")
        )
        candidate_name = _normalized_identity_name(
            row.get("source_name") or row.get("standard_name")
        )
        current_version = canonical_standard_code(current.get("current_version"))
        candidate_version = canonical_standard_code(row.get("current_version"))
        if (
            not current_name
            or not candidate_name
            or current_name != candidate_name
            or current_version != candidate_version
        ):
            registry[canonical] = {
                "standard_code": row.get("standard_code"),
                "_registry_ambiguous": True,
            }
            continue
        if bool(current.get("metadata_only")) and not bool(
            row.get("metadata_only")
        ):
            registry[canonical] = dict(row)
    return registry


def _registry_projection(
    identity: dict[str, Any],
    registry: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    primary_code = str(identity.get("primary_code") or "").strip()
    identity_status = str(identity.get("status") or "primary_identity_missing")
    if identity_status != "identified" or not primary_code:
        return {
            "status": identity_status,
            "standard_code": primary_code or None,
            "official_source": None,
            "effective_status": None,
            "current_version": None,
            "metadata_only": None,
            "clause_evidence_eligible": False,
        }
    matched = registry.get(canonical_standard_code(primary_code))
    if not isinstance(matched, dict):
        return {
            "status": "not_verified",
            "standard_code": primary_code,
            "official_source": None,
            "effective_status": None,
            "current_version": None,
            "metadata_only": None,
            "clause_evidence_eligible": False,
        }
    if matched.get("_registry_ambiguous") is True:
        return {
            "status": "registry_identity_ambiguous",
            "standard_code": primary_code,
            "official_source": None,
            "effective_status": None,
            "current_version": None,
            "metadata_only": None,
            "clause_evidence_eligible": False,
        }
    source_name = str(
        matched.get("source_name") or matched.get("standard_name") or ""
    ).strip()
    normalized_source_name = _normalized_identity_name(source_name)
    normalized_document_identity = _normalized_identity_name(
        identity.get("identity_text")
    )
    if (
        not normalized_source_name
        or normalized_source_name not in normalized_document_identity
    ):
        return {
            "status": "source_name_mismatch",
            "standard_code": primary_code,
            "official_source": str(matched.get("official_source") or "").strip()
            or None,
            "effective_status": str(
                matched.get("effective_status") or ""
            ).strip()
            or None,
            "current_version": str(matched.get("current_version") or "").strip()
            or None,
            "metadata_only": bool(matched.get("metadata_only")),
            "clause_evidence_eligible": False,
        }
    metadata_only = bool(matched.get("metadata_only"))
    return {
        "status": (
            "verified_metadata_only" if metadata_only else "verified_clause_source"
        ),
        "standard_code": str(matched.get("standard_code") or "").strip() or None,
        "official_source": str(matched.get("official_source") or "").strip() or None,
        "effective_status": str(matched.get("effective_status") or "").strip() or None,
        "current_version": str(matched.get("current_version") or "").strip() or None,
        "metadata_only": metadata_only,
        # This field applies to the registry record itself.  The independently
        # ingested PDF may still provide page-anchored text evidence below.
        "clause_evidence_eligible": not metadata_only,
    }


def _match_context(
    text: str,
    *,
    term: str,
    page_anchors: list[dict[str, Any]],
) -> dict[str, Any] | None:
    match = re.search(re.escape(term), text, flags=re.IGNORECASE)
    if match is None:
        return None
    anchor = next(
        (
            item
            for item in page_anchors
            if isinstance(item, dict)
            and int(item.get("start_offset") or 0) <= match.start()
            and match.start() <= int(item.get("end_offset") or -1)
        ),
        None,
    )
    if not isinstance(anchor, dict):
        return None
    page_start = int(anchor.get("start_offset") or 0)
    page_end = int(anchor.get("end_offset") or 0)
    window_start = max(page_start, match.start() - 80)
    window_end = min(page_end, match.end() + 160)
    window_text = text[window_start:window_end]
    return {
        "page": anchor.get("page"),
        "offset": match.start(),
        "match_start": match.start(),
        "match_end": match.end(),
        "matched_text": text[match.start() : match.end()],
        "match_window": {
            "start_offset": window_start,
            "end_offset": window_end,
            "text": window_text,
            "text_sha256": hashlib.sha256(window_text.encode("utf-8")).hexdigest(),
            "summary": " ".join(window_text.split()),
        },
        "page_text_sha256": anchor.get("text_sha256"),
        "page_summary": anchor.get("snippet"),
        "page_boundary_status": f"reliable_{anchor.get('boundary_source')}",
        "page_anchor": dict(anchor),
    }


def build_standard_index(
    topic: str,
    outline: list[str],
    project_id: str | None = None,
    workspace_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Build a project-isolated, page-addressable standard evidence index.

    Official-registry rows enrich version/status metadata only.  A registry row
    marked ``metadata_only`` is never promoted to clause evidence; chapter
    bindings require a term hit in an independently ingested local extract and
    a reversible page/full-SHA anchor.
    """

    del topic  # Chapter bindings deliberately require chapter-specific terms.
    audit_path = _audit_path(workspace_dir)
    pid = (
        str(project_id).strip()
        if isinstance(project_id, str) and project_id.strip()
        else None
    )
    if pid is None:
        return _empty_index(
            project_id=None,
            reason="missing_project_id",
            audit_path=audit_path,
        )
    if audit_path.is_symlink():
        return _empty_index(
            project_id=pid,
            reason="ingest_audit_path_untrusted",
            audit_path=audit_path,
        )
    if not audit_path.is_file():
        return _empty_index(
            project_id=pid,
            reason="no_ingest_audit",
            audit_path=audit_path,
        )

    try:
        lines = audit_path.read_text(
            encoding="utf-8",
        ).splitlines()[::-1]
    except (OSError, UnicodeError):
        return _empty_index(
            project_id=pid,
            reason="ingest_audit_unreadable",
            audit_path=audit_path,
        )
    workspace_root = (
        Path(workspace_dir)
        if workspace_dir is not None and str(workspace_dir).strip()
        else audit_path.parent.parent
    ).resolve(strict=False)
    registry = _official_registry_map()
    standards: list[dict[str, Any]] = []
    indexed_sources: list[dict[str, Any]] = []
    seen_content_ids: set[str] = set()
    invalid_identity_count = 0
    integrity_rejections: list[dict[str, str]] = []

    def _reject(filename: Any, code: str) -> None:
        integrity_rejections.append(
            {
                "filename": str(filename or "").strip(),
                "code": code,
            }
        )

    for line in lines:
        if len(standards) >= 60:
            break
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            _reject("", "audit_record_invalid_json")
            continue
        if not isinstance(record, dict):
            _reject("", "audit_record_invalid_type")
            continue
        if str(record.get("project_id") or "").strip() != pid:
            continue
        filename = str(record.get("filename") or "").strip()
        raw_sha = str(record.get("sha256") or "").strip().lower()
        raw_file_id = str(record.get("file_id") or "").strip().lower()
        if (
            not _FULL_SHA256_RE.fullmatch(raw_sha)
            or not _FULL_SHA256_RE.fullmatch(raw_file_id)
            or raw_sha != raw_file_id
        ):
            invalid_identity_count += 1
            _reject(filename, "audit_sha_file_id_mismatch")
            continue
        sha256 = raw_sha
        if sha256 in seen_content_ids:
            continue
        # The newest audit row owns this content identity even if it disables
        # the source, so an older row cannot resurrect it.
        seen_content_ids.add(sha256)
        if record.get("enabled") is False or record.get("usable") is False:
            continue
        raw_tag_values = record.get("tags")
        if not isinstance(raw_tag_values, list):
            _reject(filename, "audit_tags_invalid")
            continue
        raw_tags = {
            str(tag).strip().casefold()
            for tag in raw_tag_values
            if str(tag).strip()
        }
        if "standard" in raw_tags and "drawing" in raw_tags:
            _reject(filename, "ambiguous_standard_drawing_tags")
            continue
        tags = effective_record_tags(record)
        if "standard" not in tags or "logo" in tags:
            continue
        if not filename:
            continue

        trusted = resolve_trusted_ingest_record(
            record,
            workspace_root=workspace_root,
            read_text=True,
        )
        if trusted.get("ok") is not True:
            _reject(
                filename,
                str(trusted.get("reason") or "evidence_file_unreadable"),
            )
            continue
        expected_extract_sha256 = str(trusted["extract_text_sha256"])
        extract_text = str(trusted.get("extract_text") or "")
        declared_pages = _declared_page_count(record.get("pages"))
        standard_pdf = (
            str(record.get("doc_type") or "").strip().lower() == "pdf"
            or Path(filename).suffix.lower() == ".pdf"
        )
        page_statuses: list[str] = []
        if standard_pdf:
            page_statuses, ocr_proof_status = _standard_pdf_ocr_proof(
                record,
                declared_pages,
                extract_text,
            )
            if ocr_proof_status != "complete":
                _reject(filename, ocr_proof_status)
                continue
        page_anchors, page_boundary_status = _page_anchors(
            extract_text,
            filename=filename,
            sha256=sha256,
            declared_pages=declared_pages,
            page_statuses=page_statuses,
            require_full_coverage=standard_pdf,
        )
        if standard_pdf and (
            declared_pages is None or len(page_anchors) != declared_pages
        ):
            _reject(filename, "page_anchor_coverage_incomplete")
            continue
        identity = _document_standard_identity(filename, extract_text)
        standard_codes = identity.get("all_codes") or []
        registry_metadata = _registry_projection(identity, registry)
        eligible_anchors = [
            anchor
            for anchor in page_anchors
            if isinstance(anchor, dict) and anchor.get("evidence_eligible") is True
        ]
        text_status = (
            "indexed"
            if page_anchors and (not standard_pdf or len(page_anchors) == declared_pages)
            else (
                "locator_unavailable"
                if page_boundary_status.startswith("unreliable_")
                else "missing_text_or_ocr"
            )
        )
        standard = {
            "filename": filename,
            "sha256": sha256,
            "file_id": raw_file_id,
            "pages": record.get("pages"),
            "standard_code": identity.get("primary_code"),
            "primary_identity_status": identity.get("status"),
            "standard_codes": standard_codes,
            "referenced_standard_codes": identity.get("referenced_codes") or [],
            "keywords": _top_keywords(extract_text, limit=10),
            "page_anchors": page_anchors,
            "text_status": text_status,
            "page_boundary_status": page_boundary_status,
            "official_registry_status": registry_metadata.get("status"),
            "official_source": registry_metadata.get("official_source"),
            "official_registry": registry_metadata,
            "clause_evidence_eligible": bool(eligible_anchors),
            "clause_evidence_source": (
                "ingested_standard_text" if eligible_anchors else None
            ),
            "registry_metadata_used_as_clause_evidence": False,
            "source_integrity_status": "verified",
            "extract_text_sha256": expected_extract_sha256,
            "ocr_page_proof_status": "complete" if standard_pdf else "not_required",
        }
        standards.append(standard)
        indexed_sources.append({**standard, "_extract_text": extract_text})

    key_chapters = [
        str(title).strip()
        for title in (outline or [])
        if str(title).strip() and _is_key_process_chapter(str(title))
    ]
    bindings: list[dict[str, Any]] = []
    for title in key_chapters[:30]:
        matched: dict[str, Any] | None = None
        matched_term: str | None = None
        for term in _specific_query_terms(title):
            for source in indexed_sources:
                if not source.get("clause_evidence_eligible"):
                    continue
                context = _match_context(
                    str(source.get("_extract_text") or ""),
                    term=term,
                    page_anchors=source.get("page_anchors") or [],
                )
                if context is None:
                    continue
                matched = {**source, **context}
                matched_term = term
                break
            if matched is not None:
                break
        if matched is None:
            continue
        locator = format_hit_locator(
            {
                "filename": matched.get("filename"),
                "sha256": matched.get("sha256"),
                "page": matched.get("page"),
                "offset": matched.get("offset"),
            }
        )
        if "#p" not in locator:
            continue
        bindings.append(
            {
                "chapter": title,
                "locator": locator,
                "filename": matched.get("filename"),
                "sha256": matched.get("sha256"),
                "standard_code": matched.get("standard_code"),
                "page": matched.get("page"),
                "offset": matched.get("offset"),
                "matched_text": matched.get("matched_text"),
                "match_start": matched.get("match_start"),
                "match_end": matched.get("match_end"),
                "match_window": matched.get("match_window"),
                "page_text_sha256": matched.get("page_text_sha256"),
                "page_summary": matched.get("page_summary"),
                "page_boundary_status": matched.get("page_boundary_status"),
                "page_anchor": matched.get("page_anchor"),
                "binding_basis": "chapter_specific_ingested_standard_text",
                "matched_terms": [matched_term] if matched_term else [],
                "official_registry_status": matched.get("official_registry_status"),
                "official_source": matched.get("official_source"),
                "clause_evidence_eligible": True,
                "clause_evidence_source": "ingested_standard_text",
                "registry_metadata_used_as_clause_evidence": False,
            }
        )

    indexed_standard_count = sum(
        1 for standard in standards if standard.get("text_status") == "indexed"
    )
    missing_text_or_ocr_count = sum(
        1
        for standard in standards
        if standard.get("text_status") == "missing_text_or_ocr"
    )
    locator_unavailable_count = sum(
        1
        for standard in standards
        if standard.get("text_status") == "locator_unavailable"
    )
    registry_verified_count = sum(
        1
        for standard in standards
        if str(standard.get("official_registry_status") or "").startswith("verified_")
    )
    metadata_only_registry_count = sum(
        1
        for standard in standards
        if (standard.get("official_registry") or {}).get("metadata_only") is True
    )
    index_complete = bool(standards) and indexed_standard_count == len(
        standards
    ) and not integrity_rejections
    if index_complete:
        text_index_status = "complete"
    elif standards:
        text_index_status = "incomplete"
    elif integrity_rejections:
        text_index_status = "integrity_rejected"
    else:
        text_index_status = "no_standards"

    if bindings:
        chapter_binding_status = "bound"
    elif integrity_rejections and not standards:
        chapter_binding_status = "standard_integrity_rejected"
    elif (
        standards
        and locator_unavailable_count > 0
        and indexed_standard_count == 0
    ):
        chapter_binding_status = "standard_locator_unavailable"
    elif standards and indexed_standard_count == 0:
        chapter_binding_status = "standard_text_or_ocr_missing"
    elif standards:
        chapter_binding_status = "no_chapter_specific_evidence"
    else:
        chapter_binding_status = "no_standards"

    return {
        "ok": index_complete,
        "project_id": pid,
        "audit_path": str(audit_path),
        "standards": standards[:40],
        "chapter_bindings": bindings[:30],
        "indexed_standard_count": indexed_standard_count,
        "missing_text_or_ocr_count": missing_text_or_ocr_count,
        "locator_unavailable_count": locator_unavailable_count,
        "official_registry_verified_count": registry_verified_count,
        "metadata_only_registry_count": metadata_only_registry_count,
        "invalid_identity_count": invalid_identity_count,
        "integrity_rejection_count": len(integrity_rejections),
        "integrity_rejections": integrity_rejections[:60],
        "text_index_status": text_index_status,
        "chapter_binding_status": chapter_binding_status,
        "clause_evidence_policy": (
            "ingested_page_anchor_required; registry_metadata_alone_is_not_clause_evidence"
        ),
    }
