from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List, Iterable

_TEXT_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")


def _tokenize_query(query: str) -> list[str]:
    tokens = _TEXT_TOKEN_RE.findall(query or "")
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


@lru_cache(maxsize=128)
def _load_extract_token_offsets(extract_path: str, mtime_ns: int) -> dict[str, int]:
    """
    Build per-document token -> first_offset index.
    This avoids scanning full text for each query token repeatedly.
    """
    text = _load_extract_text(extract_path, mtime_ns)
    if not text:
        return {}
    offsets: dict[str, int] = {}
    # Guard memory growth on super-large files.
    token_cap = 120_000
    for m in _TEXT_TOKEN_RE.finditer(text):
        tok = m.group(0).strip()
        if len(tok) < 2:
            continue
        key = tok.lower()
        if key not in offsets:
            offsets[key] = int(m.start())
            if len(offsets) >= token_cap:
                break
    return offsets


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


@lru_cache(maxsize=128)
def _file_sha256(path_str: str, mtime_ns: int) -> str:
    p = Path(path_str)
    if not p.exists() or not p.is_file():
        return ""
    digest = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def search_tender_source_spans(
    tender: Dict[str, Any] | None,
    query: str,
    limit: int = 6,
    *,
    prefer_filename_keywords: Iterable[str] | None = None,
) -> List[Dict[str, Any]]:
    items = tender.get("items") if isinstance(tender, dict) else None
    if not isinstance(items, list) or not items:
        return []
    tokens = _tokenize_query(query)
    prefer = [str(x).strip() for x in (prefer_filename_keywords or []) if str(x).strip()]
    hits: List[Dict[str, Any]] = []
    seen = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        dim = str(item.get("dimension") or "").strip()
        keywords = [str(x).strip() for x in (item.get("keywords") or []) if str(x).strip()]
        try:
            weight = float(item.get("weight") or 0.0)
        except Exception:
            weight = 0.0
        spans = item.get("source_spans") if isinstance(item.get("source_spans"), list) else []
        for span in spans[:8]:
            if not isinstance(span, dict):
                continue
            file_name = str(span.get("file_name") or span.get("filename") or "").strip()
            snippet = str(span.get("snippet") or "").strip()
            if not file_name or not snippet:
                continue
            path = Path(file_name)
            if not path.exists() or not path.is_file():
                continue
            try:
                offset = int(span.get("start") if span.get("start") is not None else span.get("offset") or 0)
            except Exception:
                offset = 0
            page = None
            try:
                raw_page = span.get("page")
                if raw_page is not None:
                    page = int(raw_page)
                    if page >= 0:
                        page += 1
            except Exception:
                page = None
            try:
                mtime_ns = int(os.stat(path).st_mtime_ns)
            except Exception:
                mtime_ns = 0
            sha256 = _file_sha256(str(path), mtime_ns)
            hit = {
                "filename": path.name,
                "file_path": str(path),
                "sha256": sha256,
                "offset": offset,
                "page": page,
                "snippet": snippet,
                "dimension": dim,
                "keywords": keywords,
                "weight": weight,
            }
            locator = format_hit_locator(hit)
            if not locator or locator in seen:
                continue
            hay = " ".join([dim, " ".join(keywords), snippet, path.name]).lower()
            score = weight
            for t in tokens:
                tl = t.lower()
                if tl and tl in hay:
                    score += 2.0
                elif t and t in path.name:
                    score += 0.8
            for k in prefer:
                if k and k in path.name:
                    score += 2.5
            if page is not None:
                score += 0.4
            if offset is not None and sha256:
                score += 1.2
            hit["locator"] = locator
            hit["_score"] = score
            hits.append(hit)
            seen.add(locator)

    hits.sort(key=lambda row: float(row.get("_score") or 0.0), reverse=True)
    return hits[: max(1, int(limit or 1))]


def best_tender_source_span_hit(
    tender: Dict[str, Any] | None,
    query: str,
    limit: int = 8,
    *,
    prefer_filename_keywords: Iterable[str] | None = None,
) -> Dict[str, Any] | None:
    hits = search_tender_source_spans(
        tender,
        query,
        limit=limit,
        prefer_filename_keywords=prefer_filename_keywords,
    )
    return hits[0] if hits else None


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
    record_project_type: str | None = None,
    record_filters: Dict[str, Any] | None = None,
    audit_path: str | Path | None = None,
) -> List[Dict[str, Any]]:
    audit_file = Path(audit_path or "backend/data/audit/ingest.jsonl")
    if not audit_file.exists():
        return []
    uniq = _tokenize_query(query)
    if not uniq:
        return []
    hits: List[Dict[str, Any]] = []
    try:
        mtime_ns = int(os.stat(audit_file).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    filter_project_type = str(record_project_type or "").strip()
    normalized_filters = {
        str(k).strip(): str(v).strip()
        for k, v in (record_filters or {}).items()
        if str(k).strip() and str(v).strip()
    }
    for rec in _load_audit_records(str(audit_file), mtime_ns):
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        if filter_project_type and str(rec.get("project_type") or "").strip() != filter_project_type:
            continue
        if normalized_filters:
            mismatch = False
            for key, expected in normalized_filters.items():
                if str(rec.get(key) or "").strip() != expected:
                    mismatch = True
                    break
            if mismatch:
                continue
        if not _tags_match(rec.get("tags"), require_tags=require_tags, exclude_tags=exclude_tags):
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
        offsets = _load_extract_token_offsets(str(p), p_mtime_ns)
        if not offsets:
            continue
        lower_text = ""
        for tok in uniq:
            m_start = offsets.get(tok.lower())
            if m_start is None:
                # Chinese continuous text may be indexed as long phrase tokens;
                # fallback to direct substring search to keep recall.
                if not lower_text:
                    lower_text = text.lower()
                idx = lower_text.find(tok.lower())
                if idx < 0:
                    continue
                m_start = int(idx)
            start = max(0, int(m_start) - 80)
            end = min(len(text), int(m_start) + len(tok) + 160)
            snippet = text[start:end].replace("\n", " ").replace("\f", " ")
            page = None
            try:
                # Page boundary is stored as form-feed in extract text.
                if "\f" in text:
                    page = text[: int(m_start)].count("\f") + 1
            except Exception:
                page = None
            hits.append(
                {
                    "filename": rec.get("filename"),
                    "sha256": rec.get("sha256"),
                    "extract_saved_as": str(p),
                    "offset": int(m_start),
                    "page": page,
                    "snippet": snippet,
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
        audit_path=audit_path,
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
    audit_path: str | Path | None = None,
) -> List[str]:
    """
    List unique ingested filenames for a given tag from ingest audit.
    Useful for:
    - checking whether drawings/standards exist for a project
    - cross-index evidence typing (drawing vs standard)
    """
    audit_file = Path(audit_path or "backend/data/audit/ingest.jsonl")
    if not audit_file.exists():
        return []
    t = str(tag or "").strip()
    if not t:
        return []
    try:
        mtime_ns = int(os.stat(audit_file).st_mtime_ns)
    except Exception:
        mtime_ns = 0
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None
    ex = {str(x).strip() for x in (exclude_tags or []) if str(x).strip()}
    out: List[str] = []
    seen = set()
    for rec in _load_audit_records(str(audit_file), mtime_ns):
        if pid is not None and str(rec.get("project_id") or "").strip() != pid:
            continue
        tags = rec.get("tags") if isinstance(rec.get("tags"), list) else []
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
