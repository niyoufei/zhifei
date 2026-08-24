from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.image_library import normalize_text_list
from backend.zhifei_autoplan.project_types import normalize_project_type


CASE_LIBRARY_SCOPE = "case_library"
DEFAULT_CASE_TOP_K = 3
DEFAULT_AUDIT_PATH = Path("backend/data/audit/ingest.jsonl")
NON_FACT_REFERENCE_NOTICE = (
    "案例库仅用于格式、结构、表达方式参考，不得覆盖招标文件、BoQ、图纸、答疑和企业参数等高优先级事实源。"
)
CASE_REFERENCE_APPLICATION_BOUNDARY = (
    "案例提示不是本项目事实源：只可借鉴章节结构、逻辑顺序、表达风格和施工方法组织；"
    "严禁复制案例中的项目名称、地点、日期、工期、数量、金额、工程参数、企业信息、"
    "法规或规范编号及结论。凡与招标文件、澄清答疑、审查合格设计文件、工程量清单、"
    "已核验现行规范或企业参数冲突的内容，必须弃用案例提示。"
)


def normalize_reference_id_list(raw: Any) -> list[str]:
    return normalize_text_list(raw)


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


def case_library_record_id(rec: dict[str, Any] | None) -> str:
    if not isinstance(rec, dict):
        return ""
    sha256 = str(rec.get("sha256") or "").strip()
    filename = str(rec.get("filename") or "").strip()
    return f"case:{sha256[:12]}:{filename}" if sha256 and filename else ""


def is_case_library_record(rec: dict[str, Any] | None) -> bool:
    if not isinstance(rec, dict):
        return False
    scope = str(rec.get("library_scope") or "").strip()
    return scope == CASE_LIBRARY_SCOPE or scope == "template_library"


def _resolve_audit_path(audit_path: str | Path | None = None) -> Path:
    return Path(audit_path) if audit_path is not None else DEFAULT_AUDIT_PATH


@lru_cache(maxsize=16)
def _load_case_library_records(audit_path: str, mtime_ns: int) -> list[dict[str, Any]]:
    path = Path(audit_path)
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()[::-1]:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if is_case_library_record(rec):
            out.append(rec)
    return out


def _record_public_item(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_library_record_id(rec),
        "title": str(rec.get("library_title") or rec.get("title") or rec.get("filename") or "").strip(),
        "filename": rec.get("filename"),
        "project_type": normalize_project_type(rec.get("project_type")) or rec.get("project_type"),
        "tags": normalize_text_list(rec.get("library_tags")),
        "chapter_scope": normalize_text_list(rec.get("chapter_scope")),
        "summary": str(rec.get("library_summary") or rec.get("summary") or "").strip(),
        "style_profile": str(rec.get("library_style_profile") or rec.get("style_profile") or "").strip(),
        "source_file": rec.get("saved_as"),
        "storage_path": rec.get("saved_as"),
        "extract_saved_as": rec.get("extract_saved_as"),
        "preview_saved_as": rec.get("preview_saved_as"),
        "enabled": bool(rec.get("enabled", True)),
        "usable": bool(rec.get("usable", True)),
        "created_at": rec.get("ts"),
        "updated_at": rec.get("ts"),
    }


def list_case_library_items(
    *,
    project_type: str | None = None,
    tags: list[str] | None = None,
    chapter_scope: str | None = None,
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
    out: list[dict[str, Any]] = []
    for rec in _load_case_library_records(str(path), mtime_ns):
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
        out.append(item)
    out.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("title") or "")), reverse=True)
    return out[: max(1, int(limit or 20))]


def summarize_case_library(
    *,
    project_types: list[str] | None = None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_types = [normalize_project_type(x) or str(x or "").strip() for x in (project_types or [])]
    items = list_case_library_items(project_type=None, limit=500, audit_path=audit_path)
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


def build_case_reference_pack(
    *,
    options: dict[str, Any] | None,
    topic: str,
    chapter_title: str,
    project_type: str | None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized_options = normalize_case_library_options(options)
    selected_case_ids = normalized_options["selected_case_ids"]
    matched_project_type = normalize_project_type(project_type)
    pack = {
        "enabled": bool(normalized_options["enabled"]),
        "requested_selected_case_ids": list(selected_case_ids),
        "selected_case_ids": [],
        "matched_project_type": matched_project_type,
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
    pack["reference_lines"] = [NON_FACT_REFERENCE_NOTICE]
    if not matched_project_type:
        pack["match_reason"] = "invalid_project_type"
        pack["warning_list"].append("invalid_project_type")
        return pack

    items = list_case_library_items(project_type=matched_project_type, limit=120, audit_path=audit_path)
    selected_id_set = {str(x).strip() for x in selected_case_ids if str(x).strip()}
    if selected_id_set:
        hits = [item for item in items if str(item.get("case_id") or "").strip() in selected_id_set]
        pack["match_reason"] = "selected_case_ids" if hits else "selected_case_ids_no_match"
    else:
        title = str(chapter_title or "").strip()
        topic_text = str(topic or "").strip()
        hits = [
            item
            for item in items
            if title in set(item.get("chapter_scope") or [])
            or any(tag and tag in topic_text for tag in item.get("tags") or [])
        ][: normalized_options["top_k"]]
        pack["match_reason"] = "project_type_chapter_tags" if hits else "no_case_match"
    if not hits:
        pack["warning_list"].append("no_case_match")
        return pack

    pack["hits"] = hits[: normalized_options["top_k"]]
    pack["selected_case_ids"] = [str(item.get("case_id") or "").strip() for item in pack["hits"] if str(item.get("case_id") or "").strip()]
    for hit in pack["hits"]:
        summary = str(hit.get("summary") or "").strip()
        style_profile = str(hit.get("style_profile") or "").strip()
        if summary:
            pack["style_hints"].append(f"案例提示：{summary}")
        if style_profile:
            pack["style_hints"].append(f"风格画像：{style_profile}")
        scopes = [str(x).strip() for x in (hit.get("chapter_scope") or []) if str(x).strip()]
        if scopes:
            pack["structure_hints"].append("适用章节：" + "、".join(scopes[:4]))
    pack["style_hints"] = pack["style_hints"][:4]
    pack["structure_hints"] = pack["structure_hints"][:4]
    pack["reference_lines"].extend(pack["style_hints"][:2])
    pack["reference_lines"].extend(pack["structure_hints"][:2])
    pack["reference_lines"] = pack["reference_lines"][:5]
    return pack


def case_reference_prompt_requirements(pack: Any) -> list[str]:
    """Build bounded, non-factual drafting hints only for a real case hit."""

    data = pack if isinstance(pack, dict) else {}
    hits = data.get("hits") if isinstance(data.get("hits"), list) else []
    if not bool(data.get("enabled")) or not hits:
        return []

    lines: list[str] = []
    seen: set[str] = set()
    for raw in data.get("reference_lines") or []:
        line = str(raw or "").strip()
        if not line or line == NON_FACT_REFERENCE_NOTICE or line in seen:
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= 4:
            break

    return [
        "【案例库安全增强（非事实源）】",
        *lines,
        CASE_REFERENCE_APPLICATION_BOUNDARY,
    ]
