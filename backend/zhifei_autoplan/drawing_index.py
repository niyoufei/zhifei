from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.drawing_semantic import (
    pick_chapter_anchor,
    summarize_spatial_anchors,
)
from backend.zhifei_autoplan.evidence import (
    best_drawing_hit,
    resolve_trusted_ingest_record,
)
from backend.zhifei_autoplan.ingest_tags import effective_record_tags

_HAN_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP = {
    "工程",
    "施工",
    "图纸",
    "图",
    "节点",
    "大样",
    "详见",
    "详图",
    "示意",
    "详见图纸",
    "备注",
    "说明",
    "详见说明",
    "技术",
    "要求",
    "材料",
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
    "工艺流程",
    "专项方案",
    "专项",
    "工程",
    "施工",
    "安装",
    "图纸",
    "详图",
    "大样",
    "节点",
    "做法",
    "说明",
)
_MEANINGFUL_TEXT_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")
_FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EMPTY_TEXT_SHA256 = hashlib.sha256(b"").hexdigest()
_SUPPORTED_OCR_PAGE_PROOF_VERSIONS = {
    "ocr-page-proof-v2",
    "ocr-page-proof-v3",
}


def _top_keywords(text: str, limit: int = 12) -> list[str]:
    s = (text or "").strip()
    if not s:
        return []
    toks = [t.strip() for t in _HAN_TOKEN_RE.findall(s[:8000]) if t and len(t) >= 2]
    freq: dict[str, int] = {}
    for t in toks:
        if t in _STOP:
            continue
        if len(t) >= 12:
            continue
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
    out = [k for k, _ in ranked[: max(0, int(limit or 0))]]
    return out


def _is_key_process_chapter(title: str) -> bool:
    t = str(title or "")
    keys = ("施工方法", "施工工艺", "施工方案", "主要施工", "工序", "专项", "技术措施", "作业方法", "工艺流程")
    return any(k in t for k in keys)


def _specific_query_terms(value: str) -> list[str]:
    """Return non-generic terms suitable for claim-grade drawing matching."""

    normalized = unicodedata.normalize("NFKC", str(value or ""))
    chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", normalized)
    candidates = ["".join(chunks)] if chunks else []
    candidates.extend(chunks)
    out: list[str] = []
    for candidate in candidates:
        term = candidate.strip()
        for generic in _GENERIC_QUERY_PARTS:
            term = term.replace(generic, "")
        term = term.strip()
        if len(term) < 2 or term in _STOP or term in out:
            continue
        out.append(term)
    return sorted(out, key=lambda item: (-len(item), item))


def _declared_page_count(value: Any) -> int | None:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return None
    return count if count > 0 else None


def _audit_path(workspace_dir: str | Path | None) -> Path:
    if workspace_dir is not None and str(workspace_dir).strip():
        return Path(workspace_dir) / "audit" / "ingest.jsonl"
    return Path("backend/data/audit/ingest.jsonl")


def _page_anchors(
    text: str,
    *,
    declared_pages: int | None,
    page_statuses: list[str] | None = None,
    require_full_coverage: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    """Build page anchors only from reliable page boundaries."""

    raw_text = str(text or "")
    if not raw_text:
        return [], "missing_text_or_ocr"
    if "\f" in raw_text:
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
        meaningful_count = len(_MEANINGFUL_TEXT_RE.findall(compact))
        ocr_status = (
            page_statuses[page - 1]
            if isinstance(page_statuses, list) and page <= len(page_statuses)
            else None
        )
        if require_full_coverage and ocr_status not in {
            "text",
            "blank",
            "graphics_only",
        }:
            return [], "unreliable_ocr_page_proof_incomplete"
        if ocr_status == "graphics_only":
            # Processing coverage is proven by the whole-page image digest,
            # but this page must never become a text anchor or locator.
            start = end + 1
            continue
        if meaningful_count >= 2 or (
            require_full_coverage and ocr_status in {"text", "blank"}
        ):
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
                    "no_text_locator": ocr_status == "blank",
                    "evidence_eligible": meaningful_count >= 2
                    and ocr_status in {None, "text"},
                }
            )
        # split() removes the delimiter; account for its one-character width
        # so offsets stay aligned with evidence.search_ingested_docs().
        start = end + 1
    return anchors, f"reliable_{boundary_source}"


def _drawing_pdf_ocr_proof(
    record: Mapping[str, Any],
    declared_pages: int | None,
) -> tuple[list[str], str]:
    if declared_pages is None:
        return [], "ocr_declared_pages_missing"
    statuses = record.get("ocr_page_statuses")
    image_sha256 = record.get("ocr_page_image_sha256")
    text_sha256 = record.get("ocr_page_text_sha256")
    extract_page_sha256 = record.get("ocr_extract_page_sha256")
    blank_pages = record.get("ocr_blank_pages")
    proof_version = record.get("ocr_page_proof_version")
    graphics_only_pages = record.get("ocr_graphics_only_pages")
    no_text_locators = record.get("ocr_no_text_locators")
    if (
        record.get("ocr_cache_policy") != "drawing_full_page"
        or proof_version not in _SUPPORTED_OCR_PAGE_PROOF_VERSIONS
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
        or len(statuses) != declared_pages
        or len(image_sha256) != declared_pages
        or len(text_sha256) != declared_pages
        or len(extract_page_sha256) != declared_pages
    ):
        return [], "ocr_page_proof_incomplete"
    if proof_version == "ocr-page-proof-v3" and (
        not isinstance(graphics_only_pages, list)
        or not isinstance(no_text_locators, list)
    ):
        return [], "ocr_page_proof_incomplete"
    if proof_version != "ocr-page-proof-v3":
        graphics_only_pages = []
        no_text_locators = []
    for status, image_digest, text_digest in zip(
        statuses,
        image_sha256,
        text_sha256,
        strict=True,
    ):
        if status not in {"text", "blank", "graphics_only"}:
            return [], "ocr_page_failed_or_unreadable"
        if status == "graphics_only" and proof_version != "ocr-page-proof-v3":
            return [], "ocr_page_failed_or_unreadable"
        if _FULL_SHA256_RE.fullmatch(str(image_digest or "")) is None:
            return [], "ocr_image_proof_invalid"
        if _FULL_SHA256_RE.fullmatch(str(text_digest or "")) is None:
            return [], "ocr_text_proof_invalid"
        if status in {"blank", "graphics_only"} and text_digest != _EMPTY_TEXT_SHA256:
            return [], "ocr_blank_proof_invalid"
        if status == "text" and text_digest == _EMPTY_TEXT_SHA256:
            return [], "ocr_text_proof_invalid"
    if any(
        _FULL_SHA256_RE.fullmatch(str(digest or "")) is None
        for digest in extract_page_sha256
    ):
        return [], "ocr_extract_page_proof_invalid"
    if blank_pages != [
        index
        for index, status in enumerate(statuses, start=1)
        if status == "blank"
    ]:
        return [], "ocr_blank_page_proof_invalid"
    expected_graphics_only_pages = [
        index
        for index, status in enumerate(statuses, start=1)
        if status == "graphics_only"
    ]
    if graphics_only_pages != expected_graphics_only_pages:
        return [], "ocr_graphics_only_page_proof_invalid"
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
        return [], "ocr_no_text_locator_proof_invalid"
    return [str(status) for status in statuses], "complete"


def build_drawing_index(
    topic: str,
    outline: list[str],
    project_id: str | None = None,
    workspace_dir: str | Path | None = None,
    *,
    audit_lines: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """
    Build a lightweight “图纸目录/关键构件-章节映射表”.
    - Drawings are taken from ingest audit records where tags include 'drawing'.
    - For key process chapters, bind at least one drawing evidence locator (best-effort).
    """
    audit_path = _audit_path(workspace_dir)
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    if pid is None:
        return {
            "ok": False,
            "project_id": None,
            "audit_path": str(audit_path),
            "drawings": [],
            "chapter_bindings": [],
            "indexed_drawing_count": 0,
            "processed_drawing_count": 0,
            "graphics_only_drawing_count": 0,
            "graphics_only_page_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "invalid_identity_count": 0,
            "integrity_rejection_count": 0,
            "integrity_rejections": [],
            "text_index_status": "missing_project_id",
            "page_coverage_status": "missing_project_id",
            "chapter_binding_status": "missing_project_id",
            "reason": "missing_project_id",
        }
    if audit_lines is None and (audit_path.is_symlink() or not audit_path.is_file()):
        reason = (
            "ingest_audit_path_untrusted"
            if audit_path.is_symlink()
            else "no_ingest_audit"
        )
        return {
            "ok": False,
            "project_id": pid,
            "audit_path": str(audit_path),
            "drawings": [],
            "chapter_bindings": [],
            "indexed_drawing_count": 0,
            "processed_drawing_count": 0,
            "graphics_only_drawing_count": 0,
            "graphics_only_page_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "invalid_identity_count": 0,
            "integrity_rejection_count": 0,
            "integrity_rejections": [],
            "text_index_status": reason,
            "page_coverage_status": reason,
            "chapter_binding_status": reason,
            "reason": reason,
        }

    workspace_root = (
        Path(workspace_dir)
        if workspace_dir is not None and str(workspace_dir).strip()
        else audit_path.parent.parent
    ).resolve(strict=False)
    drawings: list[dict[str, Any]] = []
    integrity_rejections: list[dict[str, str]] = []
    invalid_identity_count = 0

    def _reject(filename: str, reason: str) -> None:
        integrity_rejections.append(
            {"filename": str(filename or ""), "reason": reason}
        )

    if audit_lines is not None:
        lines = list(reversed(audit_lines))
    else:
        try:
            lines = audit_path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()[::-1]
        except OSError:
            lines = []
    seen_content_ids: set[str] = set()
    for ln in lines:
        if len(drawings) >= 40:
            break
        try:
            rec = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        fname = str(rec.get("filename") or "").strip()
        sha = str(rec.get("sha256") or "").strip().lower()
        file_id = str(rec.get("file_id") or "").strip().lower()
        if (
            _FULL_SHA256_RE.fullmatch(sha) is None
            or _FULL_SHA256_RE.fullmatch(file_id) is None
            or sha != file_id
        ):
            invalid_identity_count += 1
            _reject(fname, "audit_sha_file_id_mismatch")
            continue
        content_id = sha
        if content_id in seen_content_ids:
            continue
        # Audit is newest-first.  Occupy the identity before status/tag checks
        # so an older active row cannot resurrect content disabled later.
        seen_content_ids.add(content_id)
        if rec.get("enabled") is False or rec.get("usable") is False:
            continue
        raw_tags = {
            str(tag).strip()
            for tag in (rec.get("tags") or [])
            if str(tag).strip()
        }
        if "standard" in raw_tags and "drawing" in raw_tags:
            _reject(fname, "ambiguous_standard_drawing_tags")
            continue
        tags = effective_record_tags(rec)
        if "drawing" not in tags:
            continue
        if "logo" in tags:
            continue
        if not fname or not sha:
            continue
        trusted = resolve_trusted_ingest_record(
            rec,
            workspace_root=workspace_root,
            read_text=True,
        )
        if trusted.get("ok") is not True:
            _reject(fname, str(trusted.get("reason") or "evidence_file_unreadable"))
            continue
        extract_path = str(trusted["extract_path"])
        preview = str(rec.get("preview_saved_as") or "")
        kw = []
        page_anchors: list[dict[str, Any]] = []
        page_boundary_status = "missing_text_or_ocr"
        trusted_extract_path: str | None = None
        extract_bytes_sha256: str | None = None
        extract_text_sha256: str | None = None
        ocr_page_proof_status = "not_required"
        graphics_only_pages: list[int] = []
        no_text_locators: list[dict[str, Any]] = []
        topo = {}
        sem = {}
        try:
            if extract_path:
                extract_text = str(trusted.get("extract_text") or "")
                trusted_extract_path = extract_path
                extract_bytes_sha256 = str(trusted["extract_text_sha256"])
                extract_text_sha256 = extract_bytes_sha256
                kw = _top_keywords(extract_text, limit=10)
                declared_pages = _declared_page_count(rec.get("pages"))
                drawing_pdf = (
                    str(rec.get("doc_type") or "").strip().lower() == "pdf"
                    or Path(fname).suffix.lower() == ".pdf"
                )
                page_statuses: list[str] = []
                if drawing_pdf:
                    page_statuses, ocr_page_proof_status = (
                        _drawing_pdf_ocr_proof(rec, declared_pages)
                    )
                    if ocr_page_proof_status == "complete":
                        raw_extract_pages = extract_text.split("\f")
                        kw = _top_keywords(
                            "\n".join(
                                raw_extract_pages[index]
                                for index, status in enumerate(page_statuses)
                                if status == "text"
                                and index < len(raw_extract_pages)
                            ),
                            limit=10,
                        )
                        graphics_only_pages = [
                            index
                            for index, status in enumerate(
                                page_statuses,
                                start=1,
                            )
                            if status == "graphics_only"
                        ]
                        raw_no_text_locators = rec.get(
                            "ocr_no_text_locators"
                        )
                        if isinstance(raw_no_text_locators, list):
                            no_text_locators = [
                                dict(item)
                                for item in raw_no_text_locators
                                if isinstance(item, Mapping)
                            ]
                page_anchors, page_boundary_status = _page_anchors(
                    extract_text,
                    declared_pages=declared_pages,
                    page_statuses=page_statuses,
                    require_full_coverage=drawing_pdf,
                )
                if drawing_pdf and ocr_page_proof_status != "complete":
                    page_anchors = []
                    page_boundary_status = (
                        f"unreliable_{ocr_page_proof_status}"
                    )
                elif drawing_pdf:
                    proof_extract_page_sha256 = rec.get(
                        "ocr_extract_page_sha256"
                    )
                    if not isinstance(proof_extract_page_sha256, list) or any(
                        str(anchor.get("text_sha256") or "")
                        != str(
                            proof_extract_page_sha256[
                                int(anchor.get("page") or 0) - 1
                            ]
                            or ""
                        )
                        for anchor in page_anchors
                    ):
                        page_anchors = []
                        page_boundary_status = (
                            "unreliable_ocr_extract_page_digest_mismatch"
                        )
                        ocr_page_proof_status = (
                            "extract_page_digest_mismatch"
                        )
        except (OSError, TypeError, ValueError):
            kw = []
            page_anchors = []
            page_boundary_status = "page_index_error"
        try:
            pm = rec.get("parsed_meta") if isinstance(rec.get("parsed_meta"), dict) else {}
            topo = pm.get("topology") if isinstance(pm.get("topology"), dict) else {}
            sem = summarize_spatial_anchors(pm, limit=6)
        except (AttributeError, TypeError, ValueError):
            topo = {}
            sem = {}
        has_text_anchor = any(
            bool(anchor.get("evidence_eligible"))
            for anchor in page_anchors
            if isinstance(anchor, dict)
        )
        declared_page_count = _declared_page_count(rec.get("pages"))
        graphics_only_document = bool(graphics_only_pages) and (
            declared_page_count == len(graphics_only_pages)
        )
        text_status = (
            "indexed"
            if has_text_anchor
            else (
                "processed_no_text_locator"
                if graphics_only_document
                else (
                    "locator_unavailable"
                    if page_boundary_status.startswith("unreliable_")
                    else "missing_text_or_ocr"
                )
            )
        )
        drawings.append(
            {
                "filename": fname,
                "sha256": sha,
                "pages": rec.get("pages"),
                "preview": preview if preview and Path(preview).exists() else None,
                "extract_saved_as": trusted_extract_path,
                "extract_bytes_sha256": extract_bytes_sha256,
                "extract_text_sha256": extract_text_sha256,
                "keywords": kw,
                "page_anchors": page_anchors,
                "text_status": text_status,
                "page_boundary_status": page_boundary_status,
                "ocr_page_proof_status": ocr_page_proof_status,
                "graphics_only_pages": graphics_only_pages,
                "no_text_locators": no_text_locators,
                "chapter_scope": str(rec.get("chapter_scope") or "").strip() or None,
                "process_scope": str(rec.get("process_scope") or "").strip() or None,
                "discipline_tags": [
                    str(tag).strip()
                    for tag in (rec.get("library_tags") or [])
                    if str(tag).strip()
                ]
                if isinstance(rec.get("library_tags"), list)
                else [],
                "topology": {
                    "nodes_count": topo.get("nodes_count"),
                    "edges_count": topo.get("edges_count"),
                    "components_count": topo.get("components_count"),
                    "endpoint_count": topo.get("endpoint_count"),
                    "trunk_length": topo.get("trunk_length"),
                    "suggested_flow_segments": topo.get("suggested_flow_segments"),
                    "topology_confidence": topo.get("topology_confidence"),
                }
                if topo
                else {},
                "spatial_anchors": sem.get("component_anchors") if isinstance(sem, dict) else [],
                "dimension_anchors": sem.get("dimension_anchors") if isinstance(sem, dict) else [],
                "elevation_anchors": sem.get("elevation_anchors") if isinstance(sem, dict) else [],
            }
        )

    key_chapters = [str(t).strip() for t in (outline or []) if str(t).strip() and _is_key_process_chapter(str(t))]
    bindings: list[dict[str, Any]] = []
    for title in key_chapters[:24]:
        query_terms = _specific_query_terms(title)
        hit = None
        matched_term = None
        for query_term in query_terms:
            candidate = best_drawing_hit(
                query_term,
                limit=10,
                prefer_filename_keywords=["图", "图纸", "施工图", "平面", "剖面", "大样", "节点"],
                project_id=pid,
                require_tags=["drawing"],
                exclude_tags=["logo"],
                audit_path=audit_path,
            )
            if candidate and candidate.get("locator") and candidate.get("page") is not None:
                hit = candidate
                matched_term = query_term
                break
        if not hit or not hit.get("locator"):
            continue
        hit_filename = str(hit.get("filename") or "").strip()
        hit_sha = str(hit.get("sha256") or "").strip()
        matching_drawings = [
            drawing
            for drawing in drawings
            if str(drawing.get("filename") or "").strip() == hit_filename
            and str(drawing.get("sha256") or "").strip() == hit_sha
            and drawing.get("text_status") == "indexed"
        ]
        if not matching_drawings:
            continue
        drawing = matching_drawings[0]
        page_anchor = next(
            (
                item
                for item in (drawing.get("page_anchors") or [])
                if isinstance(item, dict) and item.get("page") == hit.get("page")
            ),
            None,
        )
        match_window = hit.get("match_window") if isinstance(hit.get("match_window"), dict) else None
        if (
            not isinstance(page_anchor, dict)
            or page_anchor.get("evidence_eligible") is not True
            or not isinstance(match_window, dict)
            or str(hit.get("page_text_sha256") or "") != str(page_anchor.get("text_sha256") or "")
            or str(hit.get("page_summary") or "") != str(page_anchor.get("snippet") or "")
        ):
            continue
        anchor = pick_chapter_anchor(title, matching_drawings)
        bindings.append(
            {
                "chapter": title,
                "locator": hit.get("locator"),
                "filename": hit_filename,
                "sha256": hit_sha,
                "page": hit.get("page"),
                "offset": hit.get("offset"),
                "snippet": hit.get("snippet"),
                "matched_text": hit.get("matched_text"),
                "match_start": hit.get("match_start"),
                "match_end": hit.get("match_end"),
                "match_window": dict(match_window),
                "page_text_sha256": hit.get("page_text_sha256"),
                "page_summary": hit.get("page_summary"),
                "page_boundary_status": hit.get("page_boundary_status"),
                "binding_basis": "chapter_specific_extract_hit",
                "matched_terms": [matched_term] if matched_term else [],
                "spatial_anchor": anchor.get("spatial_anchor"),
                "dimension_anchor": anchor.get("dimension_anchor"),
                "topology": anchor.get("topology") if isinstance(anchor.get("topology"), dict) else {},
            }
        )

    indexed_drawing_count = sum(1 for drawing in drawings if drawing.get("text_status") == "indexed")
    processed_drawing_count = sum(
        1
        for drawing in drawings
        if drawing.get("text_status")
        in {"indexed", "processed_no_text_locator"}
    )
    graphics_only_drawing_count = sum(
        1
        for drawing in drawings
        if drawing.get("text_status") == "processed_no_text_locator"
    )
    graphics_only_page_count = sum(
        len(drawing.get("graphics_only_pages") or [])
        for drawing in drawings
    )
    missing_text_or_ocr_count = sum(
        1 for drawing in drawings if drawing.get("text_status") == "missing_text_or_ocr"
    )
    locator_unavailable_count = sum(
        1 for drawing in drawings if drawing.get("text_status") == "locator_unavailable"
    )
    return {
        "ok": bool(drawings)
        and processed_drawing_count == len(drawings)
        and not integrity_rejections,
        "project_id": pid,
        "drawings": drawings,
        "chapter_bindings": bindings[:24],
        "indexed_drawing_count": indexed_drawing_count,
        "processed_drawing_count": processed_drawing_count,
        "graphics_only_drawing_count": graphics_only_drawing_count,
        "graphics_only_page_count": graphics_only_page_count,
        "missing_text_or_ocr_count": missing_text_or_ocr_count,
        "locator_unavailable_count": locator_unavailable_count,
        "invalid_identity_count": invalid_identity_count,
        "integrity_rejection_count": len(integrity_rejections),
        "integrity_rejections": integrity_rejections[:40],
        "audit_path": str(audit_path),
        "text_index_status": (
            "complete"
            if drawings
            and indexed_drawing_count == len(drawings)
            and not integrity_rejections
            else (
                "partial"
                if drawings
                and indexed_drawing_count > 0
                and processed_drawing_count == len(drawings)
                and not integrity_rejections
                else (
                    "no_text_locator"
                    if drawings
                    and graphics_only_drawing_count == len(drawings)
                    and not integrity_rejections
                    else ("incomplete" if drawings else "no_drawings")
                )
            )
        ),
        "page_coverage_status": (
            "complete"
            if drawings
            and processed_drawing_count == len(drawings)
            and not integrity_rejections
            else ("incomplete" if drawings else "no_drawings")
        ),
        "chapter_binding_status": (
            "bound"
            if bindings
            else (
                "drawing_locator_unavailable"
                if drawings and locator_unavailable_count > 0 and indexed_drawing_count == 0
                else (
                    "drawing_no_text_locator"
                    if drawings
                    and graphics_only_drawing_count == len(drawings)
                    else (
                    "drawing_text_or_ocr_missing"
                    if drawings and indexed_drawing_count == 0
                    else ("no_chapter_specific_evidence" if drawings else "no_drawings")
                    )
                )
            )
        ),
    }
