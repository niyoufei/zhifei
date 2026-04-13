from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.project_types import normalize_project_type
from backend.zhifei_autoplan.template_library import (
    build_template_chapter_learning_context,
    list_template_library_items,
)


DEFAULT_CASE_TOP_K = 3
DEFAULT_AUDIT_PATH = Path("backend/data/audit/ingest.jsonl")
NON_FACT_REFERENCE_NOTICE = (
    "案例库仅用于格式、结构、表达方式参考，不得覆盖招标文件、BoQ、图纸、答疑和企业参数等高优先级事实源。"
)


def normalize_reference_id_list(raw: Any) -> list[str]:
    values = raw if isinstance(raw, list) else []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def normalize_case_library_options(raw: Any) -> dict[str, Any]:
    data = raw if isinstance(raw, dict) else {}
    try:
        top_k = int(data.get("top_k") or DEFAULT_CASE_TOP_K)
    except Exception:
        top_k = DEFAULT_CASE_TOP_K
    top_k = max(1, min(8, top_k))
    return {
        "enabled": bool(data.get("enabled", False)),
        "selected_case_ids": normalize_reference_id_list(data.get("selected_case_ids")),
        "top_k": top_k,
    }


def _selected_case_hits(
    *,
    project_type: str,
    template_page_bucket: str | None,
    selected_case_ids: list[str],
    audit_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not selected_case_ids:
        return [], []
    items = list_template_library_items(
        project_type=project_type,
        template_page_bucket=template_page_bucket,
        limit=max(20, len(selected_case_ids) * 4),
        audit_path=audit_path,
    )
    by_id = {
        str(item.get("record_id") or "").strip(): item
        for item in items
        if isinstance(item, dict) and str(item.get("record_id") or "").strip()
    }
    hits: list[dict[str, Any]] = []
    missing: list[str] = []
    for case_id in selected_case_ids:
        item = by_id.get(case_id)
        if not item:
            missing.append(case_id)
            continue
        hits.append(
            {
                "case_id": case_id,
                "title": str(item.get("title") or item.get("filename") or "").strip(),
                "filename": item.get("filename"),
                "project_type": item.get("project_type"),
                "chapter_scope": item.get("chapter_scope") if isinstance(item.get("chapter_scope"), list) else [],
                "library_tags": item.get("library_tags") if isinstance(item.get("library_tags"), list) else [],
                "style_profile": str(item.get("library_style_profile") or "").strip(),
                "summary": str(item.get("library_summary") or item.get("library_note") or "").strip(),
                "source_file": item.get("source_file"),
                "storage_path": item.get("storage_path"),
                "preview_saved_as": item.get("preview_saved_as"),
                "extract_saved_as": item.get("extract_saved_as"),
                "match_mode": "selected_case_ids",
                "match_reason": "explicit_case_selection",
            }
        )
    return hits, missing


def _learning_hits_to_case_hits(raw_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for item in raw_hits:
        if not isinstance(item, dict):
            continue
        record_id = str(item.get("record_id") or "").strip()
        hits.append(
            {
                "case_id": record_id or None,
                "title": str(item.get("filename") or item.get("title") or "").strip(),
                "filename": item.get("filename"),
                "project_type": item.get("project_type"),
                "chapter_scope": [str(item.get("section_title") or "").strip()] if str(item.get("section_title") or "").strip() else [],
                "library_tags": item.get("template_scene_tags") if isinstance(item.get("template_scene_tags"), list) else [],
                "style_profile": "",
                "summary": str(item.get("snippet") or "").strip(),
                "source_file": item.get("file_path"),
                "storage_path": item.get("file_path"),
                "preview_saved_as": item.get("preview_saved_as"),
                "extract_saved_as": item.get("extract_saved_as"),
                "match_mode": str(item.get("match_mode") or "template_learning").strip() or "template_learning",
                "match_reason": str(item.get("match_mode") or "template_learning").strip() or "template_learning",
            }
        )
    return hits


def build_case_reference_pack(
    *,
    options: dict[str, Any] | None,
    topic: str,
    chapter_title: str,
    project_type: str | None,
    template_page_bucket: str | None = None,
    scene_tags: list[str] | None = None,
    template_learning: dict[str, Any] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_options = normalize_case_library_options(options)
    selected_case_ids = normalized_options["selected_case_ids"]
    pack = {
        "enabled": bool(normalized_options["enabled"]),
        "requested_selected_case_ids": list(selected_case_ids),
        "selected_case_ids": [],
        "matched_project_type": normalize_project_type(project_type),
        "matched_chapter": str(chapter_title or "").strip() or None,
        "match_reason": "disabled",
        "style_hints": [],
        "structure_hints": [],
        "reference_lines": [],
        "non_fact_reference_notice": NON_FACT_REFERENCE_NOTICE,
        "hits": [],
        "warning_list": [],
    }
    if not pack["enabled"]:
        return pack
    if not pack["matched_project_type"]:
        pack["match_reason"] = "invalid_project_type"
        pack["warning_list"].append("invalid_project_type")
        pack["reference_lines"] = [NON_FACT_REFERENCE_NOTICE]
        return pack

    hits: list[dict[str, Any]] = []
    if selected_case_ids:
        hits, missing = _selected_case_hits(
            project_type=pack["matched_project_type"],
            template_page_bucket=template_page_bucket,
            selected_case_ids=selected_case_ids,
            audit_path=audit_path,
        )
        if missing:
            pack["warning_list"].append(f"selected_case_ids_missing:{','.join(missing)}")
        pack["match_reason"] = "selected_case_ids" if hits else "selected_case_ids_no_match"
    else:
        learning = template_learning if isinstance(template_learning, dict) else build_template_chapter_learning_context(
            f"{topic} {chapter_title}".strip(),
            chapter_title=chapter_title,
            project_type=pack["matched_project_type"],
            template_page_bucket=template_page_bucket,
            scene_tags=scene_tags,
            limit=normalized_options["top_k"],
            audit_path=audit_path,
        )
        raw_hits = learning.get("hits") if isinstance(learning.get("hits"), list) else []
        hits = _learning_hits_to_case_hits(raw_hits[: normalized_options["top_k"]])
        style_hints = []
        for line in learning.get("requirement_lines") or []:
            text = str(line or "").strip()
            if text:
                style_hints.append(text)
        structure_hints: list[str] = []
        theme = str(learning.get("theme") or "").strip()
        if theme:
            structure_hints.append(f"优先对齐“{theme}”类章节的组织方式，不改变本项目目录。")
        anchors = [str(x).strip() for x in (learning.get("anchor_headings") or []) if str(x).strip()]
        if anchors:
            structure_hints.append("推荐结构锚点：" + "、".join(anchors[:4]))
        sample_titles = [str(x).strip() for x in (learning.get("sample_titles") or []) if str(x).strip()]
        if sample_titles:
            structure_hints.append("代表样板章节：" + "；".join(sample_titles[:3]))
        pack["style_hints"] = style_hints[:4]
        pack["structure_hints"] = structure_hints[:4]
        pack["match_reason"] = "template_learning" if hits else "template_learning_no_match"

    if selected_case_ids:
        style_hints = []
        structure_hints = []
        for hit in hits[: normalized_options["top_k"]]:
            summary = str(hit.get("summary") or "").strip()
            style_profile = str(hit.get("style_profile") or "").strip()
            if summary:
                style_hints.append(f"案例提示：{summary}")
            if style_profile:
                style_hints.append(f"风格画像：{style_profile}")
            scopes = [str(x).strip() for x in (hit.get("chapter_scope") or []) if str(x).strip()]
            if scopes:
                structure_hints.append("适用章节：" + "、".join(scopes[:4]))
        pack["style_hints"] = style_hints[:4]
        pack["structure_hints"] = structure_hints[:4]

    pack["hits"] = hits[: normalized_options["top_k"]]
    pack["selected_case_ids"] = [
        str(hit.get("case_id") or "").strip()
        for hit in pack["hits"]
        if str(hit.get("case_id") or "").strip()
    ]
    if not pack["hits"]:
        pack["warning_list"].append("no_case_match")
    reference_lines = [NON_FACT_REFERENCE_NOTICE]
    reference_lines.extend(pack["style_hints"][:2])
    reference_lines.extend(pack["structure_hints"][:2])
    pack["reference_lines"] = reference_lines[:5]
    return pack


def summarize_case_reference_pack(raw: Any) -> dict[str, Any]:
    pack = raw if isinstance(raw, dict) else {}
    hits = pack.get("hits") if isinstance(pack.get("hits"), list) else []
    return {
        "enabled": bool(pack.get("enabled", False)),
        "selected_case_ids": [
            str(x).strip()
            for x in (pack.get("selected_case_ids") or [])
            if str(x).strip()
        ],
        "matched_project_type": str(pack.get("matched_project_type") or "").strip() or None,
        "matched_chapter": str(pack.get("matched_chapter") or "").strip() or None,
        "match_reason": str(pack.get("match_reason") or "").strip() or None,
        "hit_count": len(hits),
        "warning_list": [
            str(x).strip()
            for x in (pack.get("warning_list") or [])
            if str(x).strip()
        ],
    }
