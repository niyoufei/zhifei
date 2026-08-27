from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Iterable

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
        except Exception:
            continue
    return out


@lru_cache(maxsize=64)
def _load_extract_text(extract_path: str, mtime_ns: int) -> str:
    p = Path(extract_path)
    if not p.exists() or not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def format_hit_locator(hit: Dict[str, Any]) -> str:
    """
    Convert a hit dict into a traceable locator string for evidence markers:
    - filename#p{page}_{sha8}@{offset}
    - filename#{sha8}@{offset}
    - filename
    """
    fname = str(hit.get("filename") or "unknown")
    sha8 = str(hit.get("sha256") or "")[:8]
    offset = hit.get("offset")
    page = hit.get("page")
    loc = None
    try:
        if offset is not None and sha8 and page is not None:
            loc = f"p{int(page)}_{sha8}@{int(offset)}"
        elif offset is not None and sha8:
            loc = f"{sha8}@{int(offset)}"
        elif offset is not None:
            loc = str(int(offset))
    except Exception:
        loc = None
    return f"{fname}#{loc}" if loc else fname


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
) -> List[Dict[str, Any]]:
    audit_path = Path("backend/data/audit/ingest.jsonl")
    if not audit_path.exists():
        return []
    uniq = _tokenize_query(query)
    if not uniq:
        return []
    hits: List[Dict[str, Any]] = []
    try:
        mtime_ns = int(os.stat(audit_path).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    for rec in _load_audit_records(str(audit_path), mtime_ns):
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
        except Exception:
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
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 160)
            snippet = text[start:end].replace("\n", " ").replace("\f", " ")
            page = None
            try:
                # Page boundary is stored as form-feed in extract text.
                if "\f" in text:
                    page = text[: m.start()].count("\f") + 1
            except Exception:
                page = None
            hits.append(
                {
                    "filename": rec.get("filename"),
                    "sha256": rec.get("sha256"),
                    "extract_saved_as": str(p),
                    "offset": m.start(),
                    "page": page,
                    "snippet": snippet,
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
) -> Dict[str, Any] | None:
    """
    Pick the best hit for a query. Used for auto-citing BoQ items and for evidence traceability remediation.
    """
    hits = search_ingested_docs(
        query,
        limit=limit,
        project_id=project_id,
        require_tags=require_tags,
        exclude_tags=exclude_tags,
    )
    if not hits:
        return None
    tokens = _tokenize_query(query)
    prefer = [str(x) for x in (prefer_filename_keywords or []) if str(x).strip()]

    def _score(h: Dict[str, Any]) -> float:
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


def list_ingested_filenames_by_tag(
    tag: str,
    *,
    project_id: str | None = None,
    limit: int = 80,
    exclude_tags: Iterable[str] | None = None,
) -> List[str]:
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
    except Exception:
        mtime_ns = 0
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    ex = {str(x).strip() for x in (exclude_tags or []) if str(x).strip()}
    out: List[str] = []
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
