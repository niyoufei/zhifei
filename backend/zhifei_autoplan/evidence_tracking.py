from __future__ import annotations

import math
import re
from typing import Any, Dict, List


_EVID_RE = re.compile(r"【证据:([^】]{1,260})】")
_GRAPH_RE = re.compile(r"【图谱节点:([^】]{1,200})】")
_SPACE_RE = re.compile(r"\s+")


def _clean(s: Any) -> str:
    return str(s or "").strip()


def _split_paragraphs(text: str) -> List[str]:
    raw = str(text or "").replace("\r", "\n")
    rows = [x.strip() for x in re.split(r"\n{1,}", raw)]
    return [x for x in rows if x]


def _to_pos_int(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def _chapter_target_pages(chapter_pages: Dict[str, Any], title: str, content: str) -> int:
    raw = chapter_pages.get(title) if isinstance(chapter_pages, dict) else None
    if isinstance(raw, dict):
        raw = raw.get("target") or raw.get("pages") or raw.get("page_target") or raw.get("count")
    n = _to_pos_int(raw)
    if n:
        return n
    chars = len(str(content or ""))
    return max(1, math.ceil(chars / 900))


def _classify_evidence(src: str) -> str:
    s = _clean(src).lower()
    if not s:
        return "unknown"
    if ".dxf" in s or "dxf" in s:
        return "drawing_dxf"
    if "gb" in s or "jgj" in s or "cecs" in s or "标准" in s or "规范" in s:
        return "standard"
    if "图谱节点" in s or "graph" in s or "kg" in s:
        return "graph"
    return "other"


def _collect_score_points(tender: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = tender.get("items") if isinstance(tender, dict) and isinstance(tender.get("items"), list) else []
    out: List[Dict[str, Any]] = []
    for idx, it in enumerate(items, start=1):
        if not isinstance(it, dict):
            continue
        kws = [str(x).strip() for x in (it.get("keywords") or []) if str(x).strip()]
        dim = str(it.get("dimension") or "评分点").strip() or "评分点"
        rule_id = str(it.get("rule_id") or f"ITEM-{idx:03d}").strip() or f"ITEM-{idx:03d}"
        if not kws and not dim:
            continue
        out.append({"rule_id": rule_id, "dimension": dim, "keywords": kws})
    return out


def _detect_score_hits(paragraph: str, score_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    p = _SPACE_RE.sub("", str(paragraph or "")).lower()
    if not p:
        return []
    hits: List[Dict[str, Any]] = []
    for sp in score_points:
        kws = [str(x).strip() for x in (sp.get("keywords") or []) if str(x).strip()]
        matched = []
        for kw in kws:
            if _SPACE_RE.sub("", kw).lower() in p:
                matched.append(kw)
        if not matched:
            continue
        hits.append(
            {
                "rule_id": str(sp.get("rule_id") or "").strip(),
                "dimension": str(sp.get("dimension") or "").strip(),
                "matched_keywords": matched,
            }
        )
    return hits


def _extract_evidence(paragraph: str, section_graph_nodes: List[str]) -> Dict[str, Any]:
    evid = [x.strip() for x in _EVID_RE.findall(str(paragraph or "")) if x.strip()]
    graph_inline = [x.strip() for x in _GRAPH_RE.findall(str(paragraph or "")) if x.strip()]
    graph_nodes = []
    for g in graph_inline + [x for x in section_graph_nodes if x]:
        if g not in graph_nodes:
            graph_nodes.append(g)

    typed = {"graph_nodes": [], "drawing_refs": [], "standard_refs": [], "other_refs": []}
    sources: List[str] = []

    for g in graph_nodes:
        ref = f"图谱节点:{g}"
        if ref not in sources:
            sources.append(ref)
        if g not in typed["graph_nodes"]:
            typed["graph_nodes"].append(g)

    for s in evid:
        if s not in sources:
            sources.append(s)
        c = _classify_evidence(s)
        if c == "drawing_dxf":
            typed["drawing_refs"].append(s)
        elif c == "standard":
            typed["standard_refs"].append(s)
        elif c == "graph":
            # 如果正文把图谱节点放进【证据:...】，仍归并到图谱侧
            typed["graph_nodes"].append(s)
        else:
            typed["other_refs"].append(s)

    if not sources:
        sources = ["AUTO://no_explicit_evidence"]
        typed["other_refs"] = ["AUTO://no_explicit_evidence"]

    # 去重保序
    for k in typed.keys():
        dedup = []
        for x in typed[k]:
            xx = _clean(x)
            if xx and xx not in dedup:
                dedup.append(xx)
        typed[k] = dedup

    return {"sources": sources, "typed": typed}


def build_evidence_tracking(
    *,
    sections: List[Dict[str, Any]],
    tender: Dict[str, Any],
    chapter_pages: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    score_points = _collect_score_points(tender if isinstance(tender, dict) else {})
    chapter_pages = chapter_pages if isinstance(chapter_pages, dict) else {}

    page_cursor = 1
    for s_idx, sec in enumerate(sections or [], start=1):
        if not isinstance(sec, dict):
            continue
        title = _clean(sec.get("title")) or f"章节{s_idx}"
        content = str(sec.get("content") or "")
        paras = _split_paragraphs(content)
        sec_pages = _chapter_target_pages(chapter_pages, title, content)
        sec_para_count = max(1, len(paras))
        section_graph_nodes = [str(x).strip() for x in (sec.get("graph_nodes") or []) if str(x).strip()]

        for p_idx, para in enumerate(paras, start=1):
            ev = _extract_evidence(para, section_graph_nodes)
            score_hits = _detect_score_hits(para, score_points)
            page_est = page_cursor + min(sec_pages - 1, math.floor((p_idx - 1) * sec_pages / sec_para_count))
            explicit_sources = [
                source
                for source in ev["sources"]
                if source and not str(source).startswith("AUTO://")
            ]
            rows.append(
                {
                    "section_index": s_idx,
                    "section_title": title,
                    "paragraph_index": p_idx,
                    "paragraph_id": f"S{s_idx:02d}-P{p_idx:03d}",
                    "page_estimate": int(page_est),
                    "tender_score_points": score_hits,
                    "system_response": para,
                    "evidence_sources": ev["sources"],
                    "explicit_evidence_sources": explicit_sources,
                    "has_explicit_evidence": bool(explicit_sources),
                    "evidence_typed": ev["typed"],
                }
            )
        page_cursor += max(1, sec_pages)

    matched_rows = sum(1 for r in rows if (r.get("tender_score_points") or []))
    evidence_rows = sum(1 for r in rows if (r.get("explicit_evidence_sources") or []))
    trace_rows = sum(
        1
        for r in rows
        if any(("#" in str(x) and "@" in str(x)) for x in (r.get("explicit_evidence_sources") or []))
    )
    return {
        "rows": rows,
        "summary": {
            "paragraph_count": len(rows),
            "score_point_bound_rows": matched_rows,
            "evidence_bound_rows": evidence_rows,
            "traceable_locator_rows": trace_rows,
        },
    }
