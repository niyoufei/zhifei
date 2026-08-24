from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.project_types import normalize_project_type


IMAGE_LIBRARY_SCOPE = "image_library"
DEFAULT_AUDIT_PATH = Path("backend/data/audit/ingest.jsonl")
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")


def normalize_text_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = raw
    else:
        values = re.split(r"[，,、;；/\s]+", str(raw or "").strip())
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def normalize_image_library_options(raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    try:
        top_k = int(data.get("top_k") or 3)
    except Exception:
        top_k = 3
    top_k = max(1, min(8, top_k))
    return {
        "enabled": bool(data.get("enabled", False)),
        "selected_image_ids": normalize_text_list(data.get("selected_image_ids")),
        "top_k": top_k,
    }


def _resolve_audit_path(audit_path: str | Path | None = None) -> Path:
    return Path(audit_path) if audit_path is not None else DEFAULT_AUDIT_PATH


def _tokenize(value: Any) -> list[str]:
    tokens = _TOKEN_RE.findall(str(value or ""))
    out: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = str(token or "").strip().lower()
        if len(normalized) < 2 or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def image_library_record_id(rec: dict[str, Any] | None) -> str:
    if not isinstance(rec, dict):
        return ""
    sha256 = str(rec.get("sha256") or "").strip()
    filename = str(rec.get("filename") or "").strip()
    return f"image:{sha256[:12]}:{filename}" if sha256 and filename else ""


def is_image_library_record(rec: dict[str, Any] | None) -> bool:
    return isinstance(rec, dict) and str(rec.get("library_scope") or "").strip() == IMAGE_LIBRARY_SCOPE


@lru_cache(maxsize=16)
def _load_image_library_records(audit_path: str, mtime_ns: int) -> list[dict[str, Any]]:
    path = Path(audit_path)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if is_image_library_record(rec):
            out.append(rec)
    return out


def _record_public_item(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "image_id": image_library_record_id(rec),
        "title": str(rec.get("library_title") or rec.get("title") or rec.get("filename") or "").strip(),
        "filename": rec.get("filename"),
        "project_type": normalize_project_type(rec.get("project_type")) or rec.get("project_type"),
        "tags": normalize_text_list(rec.get("library_tags")),
        "chapter_scope": normalize_text_list(rec.get("chapter_scope")),
        "process_scope": normalize_text_list(rec.get("process_scope")),
        "caption": str(rec.get("library_caption") or rec.get("caption") or "").strip(),
        "description": str(rec.get("library_description") or rec.get("description") or "").strip(),
        "source_path": rec.get("saved_as"),
        "storage_path": rec.get("saved_as"),
        "preview_saved_as": rec.get("preview_saved_as"),
        "enabled": bool(rec.get("enabled", True)),
        "usable": bool(rec.get("usable", True)),
        "created_at": rec.get("ts"),
        "updated_at": rec.get("ts"),
    }


def list_image_library_items(
    *,
    project_type: str | None = None,
    tags: list[str] | None = None,
    chapter_scope: str | None = None,
    process_scope: str | None = None,
    limit: int = 20,
    audit_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    path = _resolve_audit_path(audit_path)
    if not path.exists():
        return []
    try:
        mtime_ns = int(os.stat(path).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    normalized_type = normalize_project_type(project_type)
    wanted_tags = {str(x).strip() for x in (tags or []) if str(x).strip()}
    wanted_chapter = str(chapter_scope or "").strip()
    wanted_process = str(process_scope or "").strip()
    out: list[dict[str, Any]] = []
    for rec in _load_image_library_records(str(path), mtime_ns):
        rec_type = normalize_project_type(rec.get("project_type"))
        if normalized_type and rec_type != normalized_type:
            continue
        item = _record_public_item(rec)
        if not item["enabled"] or not item["usable"]:
            continue
        if wanted_tags and not wanted_tags.intersection(set(item["tags"])):
            continue
        if wanted_chapter and wanted_chapter not in set(item["chapter_scope"]):
            continue
        if wanted_process and wanted_process not in set(item["process_scope"]):
            continue
        out.append(item)
    out.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("title") or "")), reverse=True)
    return out[: max(1, int(limit or 20))]


def summarize_image_library(
    *,
    project_types: list[str] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_types = [normalize_project_type(x) or str(x or "").strip() for x in (project_types or [])]
    items = list_image_library_items(project_type=None, limit=500, audit_path=audit_path)
    by_project_type: dict[str, int] = {str(x): 0 for x in normalized_types if str(x).strip()}
    for item in items:
        key = str(item.get("project_type") or "").strip()
        if key:
            by_project_type[key] = by_project_type.get(key, 0) + 1
    return {
        "total_count": len(items),
        "by_project_type": by_project_type,
        "latest_item": items[0] if items else None,
    }


def build_image_selection_pack(
    *,
    options: dict[str, Any] | None,
    topic: str,
    chapter_title: str,
    project_type: str | None,
    tags: list[str] | None = None,
    process_scope: str | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_options = normalize_image_library_options(options)
    selected_image_ids = normalized_options["selected_image_ids"]
    matched_project_type = normalize_project_type(project_type)
    pack = {
        "enabled": bool(normalized_options["enabled"]),
        "requested_selected_image_ids": list(selected_image_ids),
        "selected_image_ids": [],
        "matched_project_type": matched_project_type,
        "matched_chapter": str(chapter_title or "").strip() or None,
        "match_reason": "disabled",
        "insertion_hint": "",
        "caption_hint": "",
        "images": [],
        "warning_list": [],
    }
    if not pack["enabled"]:
        return pack
    if not matched_project_type:
        pack["match_reason"] = "invalid_project_type"
        pack["warning_list"].append("invalid_project_type")
        return pack

    chapter_tokens = set(_tokenize(chapter_title))
    query_tokens = set(_tokenize(topic)) | chapter_tokens | {str(x).strip().lower() for x in (tags or []) if str(x).strip()}
    items = list_image_library_items(project_type=matched_project_type, limit=120, audit_path=audit_path)
    selected_id_set = {str(x).strip() for x in selected_image_ids if str(x).strip()}
    ranked: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        image_id = str(item.get("image_id") or "").strip()
        if selected_id_set and image_id not in selected_id_set:
            continue
        haystack = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("caption") or ""),
                str(item.get("description") or ""),
                " ".join(item.get("tags") or []),
                " ".join(item.get("chapter_scope") or []),
                " ".join(item.get("process_scope") or []),
            ]
        )
        haystack_tokens = set(_tokenize(haystack))
        score = 0.0
        score += 3.0 * len(query_tokens.intersection(haystack_tokens))
        if str(chapter_title or "").strip() and str(chapter_title or "").strip() in set(item.get("chapter_scope") or []):
            score += 5.0
        if process_scope and str(process_scope).strip() in set(item.get("process_scope") or []):
            score += 3.0
        score += 2.0 * len(set(item.get("tags") or []).intersection(set(tags or [])))
        if selected_id_set and image_id in selected_id_set:
            score += 10.0
        if score <= 0 and not selected_id_set:
            continue
        ranked.append((score, item))
    ranked.sort(key=lambda pair: (pair[0], str(pair[1].get("created_at") or "")), reverse=True)
    selected_items = [item for _, item in ranked[: normalized_options["top_k"]]]
    if not selected_items:
        pack["match_reason"] = "no_image_match"
        pack["warning_list"].append("no_image_match")
        return pack

    pack["match_reason"] = "selected_image_ids" if selected_id_set else "project_type_chapter_tags"
    pack["images"] = selected_items
    pack["selected_image_ids"] = [str(item.get("image_id") or "").strip() for item in selected_items if str(item.get("image_id") or "").strip()]
    pack["insertion_hint"] = f"优先在“{chapter_title}”相关章节后插入匹配图片，未命中时不强插图。"
    first_caption = str(selected_items[0].get("caption") or selected_items[0].get("title") or "").strip()
    if first_caption:
        pack["caption_hint"] = first_caption
    return pack


def image_selection_pack_media_entries(raw: Any) -> list[dict[str, Any]]:
    pack = raw if isinstance(raw, dict) else {}
    out: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    matched_chapter = str(pack.get("matched_chapter") or pack.get("chapter_title") or "").strip()
    for item in pack.get("images") or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("source_path") or item.get("storage_path") or item.get("path") or "").strip()
        if not path or path in seen_paths:
            continue
        seen_paths.add(path)
        caption = str(item.get("caption") or item.get("title") or pack.get("caption_hint") or "").strip()
        chapter_scope = item.get("chapter_scope") or ([matched_chapter] if matched_chapter else [])
        if isinstance(chapter_scope, str):
            chapter_scope = [chapter_scope]
        tags = [str(value).strip() for value in (item.get("tags") or item.get("library_tags") or []) if str(value).strip()]
        out.append(
            {
                "path": path,
                "caption": caption,
                "image_id": str(item.get("image_id") or "").strip() or None,
                "chapter_scope": [str(value).strip() for value in chapter_scope if str(value).strip()],
                "semantic_terms": tags,
                "source_kind": str(item.get("source_kind") or item.get("source_mode") or "library_image").strip(),
                "source_sha256": str(item.get("sha256") or item.get("source_sha256") or "").strip() or None,
                "source_filename": str(item.get("source_filename") or item.get("filename") or "").strip() or None,
                "source_page": item.get("source_page"),
                "is_project_source": bool(item.get("is_project_source")),
                "required": bool(item.get("required")),
                "explicit_selection": True,
            }
        )
    return out
