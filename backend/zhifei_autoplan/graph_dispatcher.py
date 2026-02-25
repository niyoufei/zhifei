from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend import kg_loader


_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_NUMERIC_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|t|h|小时|天|次|人|台|套|%|MPa|kN|℃|dB|m2|m3)",
    re.IGNORECASE,
)


def _norm_text(v: Any) -> str:
    return str(v or "").strip()


def _dedup_keep_order(items: Iterable[str], limit: int | None = None) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in items:
        s = _norm_text(raw)
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if limit and len(out) >= limit:
            break
    return out


def _tokenize(text: str) -> List[str]:
    toks = [t.strip() for t in _TOKEN_RE.findall(text or "")]
    toks = [t for t in toks if len(t) >= 2]
    return _dedup_keep_order(toks, limit=200)


@lru_cache(maxsize=1)
def _load_domain_map() -> Dict[str, Any]:
    path: Path | None = None
    try:
        path = kg_loader.get_domain_map_path()
    except Exception:
        fallback = Path("backend/SuperKG-DOMAIN-MAP.json")
        if fallback.exists():
            path = fallback
    if not path or not path.exists():
        return {"knowledge_graph_library": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"knowledge_graph_library": []}


@lru_cache(maxsize=1)
def _load_pack_index() -> Dict[str, Dict[str, Any]]:
    cfg: Dict[str, Any] | None = None
    try:
        cfg = kg_loader.load_kg_config()
        paths = kg_loader.get_base_pack_paths(cfg)
    except Exception:
        paths = [
            Path("backend/Universal_Base_Pack.json"),
            Path("backend/Civil_Basic_Pack.json"),
            Path("backend/Transport_Infra_Pack.json"),
            Path("backend/Energy_Industrial_Pack.json"),
            Path("backend/Risk_Specialist_Pack.json"),
            Path("backend/Special_Medical_Pack.json"),
        ]

    out: Dict[str, Dict[str, Any]] = {}
    for p in paths:
        if not p.exists():
            continue
        try:
            arr = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(arr, list):
            continue
        for it in arr:
            if not isinstance(it, dict):
                continue
            fn = _norm_text(it.get("filename"))
            if not fn:
                continue
            if fn not in out:
                out[fn] = {
                    "filename": fn,
                    "pack_path": str(p),
                    "content": it.get("content"),
                }
    return out


def _extract_graph_docs(
    obj: Any,
    *,
    graph_file: str,
    graph_name: str,
    path: str = "$",
) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []

    def add_doc(title: str, text: str, p: str) -> None:
        t = _norm_text(text)
        if len(t) < 20:
            return
        docs.append(
            {
                "title": _norm_text(title) or "图谱节点",
                "text": t[:1400],
                "path": p,
                "graph_file": graph_file,
                "graph_name": graph_name or graph_file,
                "logical_node": f"{graph_file}#{p}",
            }
        )

    def walk(x: Any, p: str) -> None:
        if isinstance(x, dict):
            title = (
                x.get("工序名称")
                or x.get("节点")
                or x.get("name")
                or x.get("title")
                or x.get("章节")
                or x.get("内容")
            )
            parts: List[str] = []
            for k, v in x.items():
                if v in (None, "", [], {}):
                    continue
                if isinstance(v, (dict, list)):
                    continue
                vs = _norm_text(v)
                if not vs:
                    continue
                parts.append(f"{k}: {vs}")
            if title and parts:
                add_doc(str(title), "\n".join(parts), p)
            for k, v in x.items():
                if isinstance(v, (dict, list)):
                    walk(v, f"{p}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                walk(v, f"{p}[{i}]")

    walk(obj, path)
    return docs


@lru_cache(maxsize=256)
def _docs_for_graph_file(graph_file: str, graph_name: str) -> List[Dict[str, Any]]:
    content = (_load_pack_index().get(graph_file) or {}).get("content")
    if content is None:
        return []
    return _extract_graph_docs(content, graph_file=graph_file, graph_name=graph_name)


def extract_engineering_keywords(
    *,
    topic: str | None = None,
    outline: List[str] | None = None,
    requirements: List[str] | None = None,
    tender: Dict[str, Any] | None = None,
) -> List[str]:
    parts: List[str] = []
    if topic:
        parts.append(str(topic))
    if isinstance(outline, list):
        parts.extend([_norm_text(x) for x in outline if _norm_text(x)])
    if isinstance(requirements, list):
        parts.extend([_norm_text(x) for x in requirements if _norm_text(x)])
    if isinstance(tender, dict):
        parts.extend([_norm_text(x) for x in (tender.get("outline") or []) if _norm_text(x)])
        for it in (tender.get("items") or [])[:240]:
            if not isinstance(it, dict):
                continue
            parts.append(_norm_text(it.get("dimension")))
            parts.extend([_norm_text(k) for k in (it.get("keywords") or [])[:20] if _norm_text(k)])
    corpus = "\n".join(parts)
    if not corpus.strip():
        return []

    base_tokens = _tokenize(corpus)
    # Pull in domain-map keywords that are actually present in the corpus.
    dm = _load_domain_map()
    map_tokens: List[str] = []
    for grp in dm.get("knowledge_graph_library") or []:
        if not isinstance(grp, dict):
            continue
        for m in grp.get("maps") or []:
            if not isinstance(m, dict):
                continue
            for kw in m.get("keywords") or []:
                kws = _norm_text(kw)
                if kws and kws in corpus:
                    map_tokens.append(kws)
    return _dedup_keep_order(base_tokens + map_tokens, limit=160)


def _score_map_hit(corpus: str, kws: List[str]) -> tuple[int, List[str]]:
    hits = [kw for kw in kws if _norm_text(kw) and _norm_text(kw) in corpus]
    return len(hits), _dedup_keep_order(hits, limit=20)


def detect_specialty_dispatch(
    *,
    topic: str | None = None,
    outline: List[str] | None = None,
    requirements: List[str] | None = None,
    tender: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    keywords = extract_engineering_keywords(
        topic=topic,
        outline=outline,
        requirements=requirements,
        tender=tender,
    )
    corpus = "\n".join(keywords)
    dm = _load_domain_map()
    packs = _load_pack_index()

    tier_hits: Dict[int, List[Dict[str, Any]]] = {0: [], 1: [], 2: []}
    missing_files: List[str] = []
    for i, grp in enumerate(dm.get("knowledge_graph_library") or []):
        if i > 2 or not isinstance(grp, dict):
            continue
        for m in grp.get("maps") or []:
            if not isinstance(m, dict):
                continue
            filename = _norm_text(m.get("filename"))
            kws = [str(x).strip() for x in (m.get("keywords") or []) if str(x).strip()]
            score, hits = _score_map_hit(corpus, kws)
            if score <= 0:
                continue
            rec = {
                "tier": i,
                "filename": filename,
                "graph_name": _norm_text(m.get("cn_name")) or filename,
                "keywords": kws,
                "hit_keywords": hits,
                "score": score,
                "available": filename in packs,
            }
            if rec["available"]:
                tier_hits[i].append(rec)
            else:
                missing_files.append(filename)

    for arr in tier_hits.values():
        arr.sort(key=lambda x: (int(x.get("score") or 0), len(x.get("hit_keywords") or [])), reverse=True)

    master = tier_hits[0][0] if tier_hits[0] else None
    specialists = tier_hits[1][:8]
    universals = tier_hits[2][:5]

    # Hard fallback: always attach universal base if available, even when no keyword matched.
    if not universals:
        for fn, meta in packs.items():
            if "Universal" in fn or "SafetyCivilization" in fn or "GreenConstruction" in fn:
                universals.append(
                    {
                        "tier": 2,
                        "filename": fn,
                        "graph_name": fn,
                        "keywords": [],
                        "hit_keywords": [],
                        "score": 0,
                        "available": True,
                    }
                )
            if len(universals) >= 5:
                break

    selected: List[Dict[str, Any]] = []
    if master:
        selected.append({"role": "master", **master})
    selected.extend([{"role": "specialist", **x} for x in specialists])
    selected.extend([{"role": "universal", **x} for x in universals])

    # If nothing matched, keep deterministic fallback from available packs.
    if not selected:
        for fn, _ in list(packs.items())[:3]:
            selected.append(
                {
                    "role": "fallback",
                    "tier": 2,
                    "filename": fn,
                    "graph_name": fn,
                    "keywords": [],
                    "hit_keywords": [],
                    "score": 0,
                    "available": True,
                }
            )

    detected_keywords = _dedup_keep_order(
        [x for x in keywords] + [x for it in selected for x in (it.get("hit_keywords") or [])],
        limit=120,
    )
    discipline_tags = _dedup_keep_order(
        [
            str(it.get("graph_name") or "").replace("图谱", "").replace("终极", "").strip()
            for it in selected
        ],
        limit=24,
    )
    return {
        "detected_keywords": detected_keywords,
        "master": master,
        "specialists": specialists,
        "universals": universals,
        "selected_graphs": selected,
        "missing_graphs": _dedup_keep_order(missing_files, limit=40),
    }


def assign_specialties_to_outline(
    outline: List[str],
    dispatch: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    chapters = [str(x).strip() for x in (outline or []) if str(x).strip()]
    specialists = list(dispatch.get("specialists") or [])
    master = dispatch.get("master")
    universals = list(dispatch.get("universals") or [])

    out: Dict[str, List[Dict[str, Any]]] = {}
    for title in chapters:
        ranked: List[tuple[int, Dict[str, Any]]] = []
        for sp in specialists:
            kws = [str(x).strip() for x in (sp.get("keywords") or []) if str(x).strip()]
            hit = sum(1 for kw in kws if kw and kw in title)
            if hit > 0:
                ranked.append((hit, sp))
        ranked.sort(key=lambda x: x[0], reverse=True)
        picks: List[Dict[str, Any]] = [x[1] for x in ranked[:2]]
        if not picks and master:
            picks = [master]
        if universals:
            picks.extend(universals[:1])
        out[title] = picks
    return out


def search_dispatch_graphs(
    *,
    query: str,
    graphs: List[Dict[str, Any]],
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    tokens = _tokenize(query)
    if not tokens:
        return []
    scored: List[tuple[float, Dict[str, Any]]] = []
    for g in graphs:
        fn = _norm_text(g.get("filename"))
        gn = _norm_text(g.get("graph_name")) or fn
        if not fn:
            continue
        docs = _docs_for_graph_file(fn, gn)
        if not docs:
            continue
        g_keywords = [str(x).strip() for x in (g.get("keywords") or []) if str(x).strip()]
        for d in docs:
            text = f"{d.get('title')}\n{d.get('text')}\n{gn}"
            score = 0.0
            for t in tokens:
                if t in text:
                    score += 1.0
            for kw in g_keywords:
                if kw and kw in query:
                    score += 0.4
            if score <= 0:
                continue
            scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for score, d in scored:
        key = f"{d.get('logical_node')}:{d.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        item = dict(d)
        item["score"] = score
        out.append(item)
        if len(out) >= max(1, int(top_k)):
            break
    return out


def extract_experience_values(
    graph_hits: List[Dict[str, Any]],
    *,
    limit: int = 4,
) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for hit in graph_hits:
        txt = _norm_text(hit.get("text"))
        if not txt:
            continue
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        for ln in lines:
            if not _NUMERIC_UNIT_RE.search(ln):
                continue
            normalized = re.sub(r"\s+", " ", ln)
            if normalized in seen:
                continue
            seen.add(normalized)
            src = f"{hit.get('graph_file')}#{hit.get('path')}"
            out.append(f"【经验值】{normalized}【图谱经验值:{src}】")
            if len(out) >= limit:
                return out
    return out

