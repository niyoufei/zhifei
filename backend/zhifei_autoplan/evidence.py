from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.ingest_tags import effective_record_tags


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
    if not resolved_audit_path.exists():
        return []
    uniq = _tokenize_query(query)
    if not uniq:
        return []
    hits: list[dict[str, Any]] = []
    try:
        mtime_ns = int(os.stat(resolved_audit_path).st_mtime_ns)
    except OSError:
        mtime_ns = 0
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    for rec in _load_audit_records(str(resolved_audit_path), mtime_ns):
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        if not _tags_match(
            effective_record_tags(rec),
            require_tags=require_tags,
            exclude_tags=exclude_tags,
        ):
            continue
        p = Path(rec.get("extract_saved_as") or "")
        if not p.exists() or not p.is_file():
            continue
        try:
            p_mtime_ns = int(os.stat(p).st_mtime_ns)
        except OSError:
            p_mtime_ns = 0
        text = _load_extract_text(str(p), p_mtime_ns)
        if not text:
            continue
        lower = text.lower()
        for tok in uniq:
            if tok.lower() not in lower:
                continue
            m = re.search(re.escape(tok), text, flags=re.IGNORECASE)
            if not m:
                continue
            page_context = _match_page_context(
                text,
                match_start=m.start(),
                match_end=m.end(),
                declared_pages=_declared_page_count(rec),
            )
            match_window = page_context.get("match_window")
            snippet = (
                str(match_window.get("summary") or "")
                if isinstance(match_window, dict)
                else " ".join(text[max(0, m.start() - 80) : min(len(text), m.end() + 160)].split())
            )
            hits.append(
                {
                    "filename": rec.get("filename"),
                    "sha256": rec.get("sha256"),
                    "extract_saved_as": str(p),
                    "offset": m.start(),
                    "snippet": snippet,
                    "matched_token": tok,
                    **page_context,
                }
            )
            if len(hits) >= limit:
                return hits
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
