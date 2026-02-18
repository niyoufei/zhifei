from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_EVIDENCE_RE = re.compile(r"【证据:(?P<loc>[^】]{3,160})】")
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_GENERIC_CHAPTER_RE = re.compile(r"(工程概况|项目概况|总体部署|资源配置|组织机构|编制依据|总说明|综合说明)")


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _pick_best_boq_item(items: List[Dict[str, Any]], name: str) -> Dict[str, Any] | None:
    cands = [it for it in (items or []) if str(it.get("name") or "").strip() == name]
    if not cands:
        return None

    def _score(it: Dict[str, Any]) -> float:
        # Prefer higher total price; fall back to quantity.
        tp = _to_float(it.get("total_price")) or 0.0
        qty = _to_float(it.get("quantity")) or 0.0
        return tp * 1.0 + qty * 1e-6

    return max(cands, key=_score)


def _index_boq_stats(boq: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    """
    Build:
    - metrics_by_name: {name: {boq_code, quantity, unit, unit_price, total_price}}
    - categories_by_name: {name: [category labels...]}
    """
    stats = boq.get("stats") if isinstance(boq.get("stats"), dict) else {}
    metrics_by_name: Dict[str, Dict[str, Any]] = {}
    cats: Dict[str, set[str]] = {}

    def _merge_metrics(name: str, it: Dict[str, Any]):
        if not name:
            return
        m = metrics_by_name.setdefault(name, {})
        for k in ("boq_code", "quantity", "unit", "unit_price", "total_price"):
            if m.get(k) is None and it.get(k) is not None:
                m[k] = it.get(k)

    def _add_cat(key: str, label: str):
        arr = stats.get(key) or []
        if not isinstance(arr, list):
            return
        for it in arr:
            if not isinstance(it, dict):
                continue
            name = str(it.get("name") or "").strip()
            if not name:
                continue
            cats.setdefault(name, set()).add(label)
            _merge_metrics(name, it)

    _add_cat("top_quantity_items", "工程量大")
    _add_cat("top_material_demand_items", "材料需求量大")
    _add_cat("top_total_price_items", "单体造价高")
    _add_cat("top_unit_price_items", "材料单价高")
    _add_cat("special_material_items", "特殊材料")
    _add_cat("hazardous_material_items", "危险品材料")
    _add_cat("ppe_items", "劳保用品")

    categories_by_name: Dict[str, List[str]] = {}
    for name, s in cats.items():
        categories_by_name[name] = sorted(s)
    return metrics_by_name, categories_by_name


def _index_chapter_locators(index_obj: Dict[str, Any] | None) -> Dict[str, str]:
    out: Dict[str, str] = {}
    idx = index_obj or {}
    binds = idx.get("chapter_bindings") if isinstance(idx.get("chapter_bindings"), list) else []
    for b in binds:
        if not isinstance(b, dict):
            continue
        ch = str(b.get("chapter") or "").strip()
        loc = str(b.get("locator") or "").strip()
        if ch and loc and ch not in out:
            out[ch] = loc
    return out


def _pick_best_hit_section(hit_sections: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not hit_sections:
        return None

    def _score(h: Dict[str, Any]) -> int:
        ok = 1 if h.get("ok") else 0
        trip = int(h.get("triplet_count") or 0)
        keys = len(h.get("hit_keys") or [])
        units = 1 if h.get("has_units") else 0
        ev = int(h.get("evidence_count") or 0)
        # Keep this simple and stable: ok dominates; others are tie-breakers.
        return ok * 1000 + trip * 30 + keys * 8 + units * 10 + ev * 15

    return max(hit_sections, key=_score)


def _tokenize_text(s: str) -> set[str]:
    toks = [str(x).strip().lower() for x in _TOKEN_RE.findall(s or "")]
    return {t for t in toks if len(t) >= 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    if inter <= 0:
        return 0.0
    uni = len(a.union(b))
    return float(inter) / float(max(1, uni))


def _chapter_relevance_score(name: str, process_name: str | None, categories: List[str], chapter_title: str) -> int:
    t = str(chapter_title or "").strip()
    low_t = t.lower()
    score = 0
    if name and name in t:
        score += 48
    if process_name and process_name in t:
        score += 72
    if _GENERIC_CHAPTER_RE.search(t):
        score -= 20

    q = " ".join([str(name or ""), str(process_name or ""), " ".join(categories or [])]).strip()
    sim = _jaccard(_tokenize_text(q), _tokenize_text(low_t))
    score += int(sim * 100)
    return score


def _typed_locator_hits(locs: List[str], drawing_files: set[str], standard_files: set[str]) -> int:
    if not locs:
        return 0
    hit = 0
    for loc in locs:
        fn = _extract_filename_from_locator(loc)
        if not fn:
            continue
        if fn in drawing_files:
            hit += 1
        if fn in standard_files:
            hit += 1
    return hit


def _pick_best_hit_section_precise(
    hit_sections: List[Dict[str, Any]],
    *,
    name: str,
    process_name: str | None,
    categories: List[str],
    section_text_by_title: Dict[str, str],
    drawing_files: set[str],
    standard_files: set[str],
) -> Dict[str, Any] | None:
    """
    Prefer chapters that are both "closed-loop valid" and closer to the real process chapter:
    - closure quality (triplet/quant/evidence)
    - chapter title relevance (item/process/category similarity)
    - typed evidence locators near item mention (drawing/standard)
    """
    if not hit_sections:
        return None

    best = None
    best_score = -10**9
    for h in hit_sections:
        if not isinstance(h, dict):
            continue
        title = str(h.get("title") or "").strip()
        text = section_text_by_title.get(title, "")
        near_locs = _extract_evidence_locators_near(text, name, window=620, max_locs=6) if title else []

        base = int(_pick_best_hit_section([h]).get("ok", False)) * 1000
        base += int(h.get("triplet_count") or 0) * 30
        base += len(h.get("hit_keys") or []) * 8
        base += (10 if h.get("has_units") else 0)
        base += int(h.get("evidence_count") or 0) * 15

        rel = _chapter_relevance_score(name, process_name, categories, title)
        typed = _typed_locator_hits(near_locs, drawing_files, standard_files)
        score = base + rel * 3 + typed * 45 + min(3, len(near_locs)) * 10

        if score > best_score:
            best_score = score
            best = dict(h)
            best["_selection_score"] = score
            best["_selection_base"] = base
            best["_selection_relevance"] = rel
            best["_selection_typed_locator_hits"] = typed
            best["_selection_near_locator_count"] = len(near_locs)

    return best


def _extract_filename_from_locator(loc: str) -> str:
    s = str(loc or "").strip()
    if not s:
        return ""
    return s.split("#", 1)[0].strip() if "#" in s else s


def _pick_locator_by_known_filenames(locs: List[str], known: set[str]) -> str | None:
    if not locs or not known:
        return None
    for loc in locs:
        fn = _extract_filename_from_locator(loc)
        if fn and fn in known:
            return loc
    return None


def _extract_evidence_locators_near(text: str, needle: str, window: int = 520, max_locs: int = 4) -> List[str]:
    if not text or not needle:
        return []
    pos = text.find(needle)
    if pos < 0:
        return []
    start = max(0, pos - window)
    end = min(len(text), pos + len(needle) + window)
    snippet = text[start:end]
    locs: List[str] = []
    for m in _EVIDENCE_RE.finditer(snippet):
        loc = str(m.group("loc") or "").strip()
        if not loc:
            continue
        if loc not in locs:
            locs.append(loc)
        if len(locs) >= max_locs:
            break
    return locs


def _pick_best_mention_section(
    *,
    name: str,
    process_name: str | None,
    categories: List[str],
    sections: List[Dict[str, Any]],
    drawing_files: set[str],
    standard_files: set[str],
) -> Tuple[str | None, List[str], str]:
    """
    Fallback when quality closure did not return hit sections:
    choose the section with strongest process/title relevance + nearby typed evidence.
    """
    best_title: str | None = None
    best_locs: List[str] = []
    best_score = -10**9
    for sec in sections or []:
        title = str(sec.get("title") or "").strip()
        text = str(sec.get("content") or "")
        if not name or (name not in text):
            continue
        near_locs = _extract_evidence_locators_near(text, name, window=620, max_locs=6)
        rel = _chapter_relevance_score(name, process_name, categories, title)
        typed = _typed_locator_hits(near_locs, drawing_files, standard_files)
        score = rel * 3 + typed * 35 + min(3, len(near_locs)) * 8
        if score > best_score:
            best_score = score
            best_title = title or None
            best_locs = near_locs

    if best_title:
        return best_title, best_locs, "mentioned"
    return None, [], "not_mentioned"


def build_cross_index(
    *,
    boq: Dict[str, Any] | None,
    sections: List[Dict[str, Any]] | None,
    boq_focus: Dict[str, Any] | None = None,
    drawing_index: Dict[str, Any] | None = None,
    standard_index: Dict[str, Any] | None = None,
    quality_checks: Dict[str, Any] | None = None,
    project_id: str | None = None,
) -> Dict[str, Any]:
    """
    Cross-index table for BoQ focus items:
    - item -> (metrics/categories/process) -> best chapter -> (drawing locator / standard locator) -> closure flags
    This is designed for traceability and fast review.
    """
    boq = boq if isinstance(boq, dict) else {}
    sections = sections if isinstance(sections, list) else []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None

    metrics_by_name, categories_by_name = _index_boq_stats(boq)
    boq_items = boq.get("items") if isinstance(boq.get("items"), list) else []

    focus_names = []
    if isinstance(boq_focus, dict):
        focus_names = [str(x).strip() for x in (boq_focus.get("must_cover_keywords") or []) if str(x).strip()]
    if not focus_names:
        # Fallback to stats-derived order if focus list is not available.
        focus_names = list(categories_by_name.keys())
    # Stable unique
    seen = set()
    uniq_focus = []
    for n in focus_names:
        if n not in seen:
            seen.add(n)
            uniq_focus.append(n)
    focus_names = uniq_focus[:24]

    closure_map: Dict[str, Dict[str, Any]] = {}
    try:
        items = ((quality_checks or {}).get("boq_focus_item_closure") or {}).get("items") or []
        if isinstance(items, list):
            for it in items:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("item") or "").strip()
                if name:
                    closure_map[name] = it
    except Exception:
        closure_map = {}

    draw_loc_by_chapter = _index_chapter_locators(drawing_index)
    std_loc_by_chapter = _index_chapter_locators(standard_index)

    drawing_files: set[str] = set()
    try:
        for d in (drawing_index or {}).get("drawings") or []:
            if not isinstance(d, dict):
                continue
            fn = str(d.get("filename") or "").strip()
            if fn:
                drawing_files.add(fn)
    except Exception:
        drawing_files = set()

    standard_files: set[str] = set()
    try:
        for d in (standard_index or {}).get("standards") or []:
            if not isinstance(d, dict):
                continue
            fn = str(d.get("filename") or "").strip()
            if fn:
                standard_files.add(fn)
    except Exception:
        standard_files = set()

    has_drawings = bool(drawing_files)
    has_standards = bool(standard_files)
    section_text_by_title: Dict[str, str] = {}
    for sec in sections:
        title = str(sec.get("title") or "").strip()
        if not title or title in section_text_by_title:
            continue
        section_text_by_title[title] = str(sec.get("content") or "")

    focus_rows: List[Dict[str, Any]] = []
    mentioned = 0
    closed_ok = 0
    missing_drawing = 0
    missing_standard = 0

    for name in focus_names:
        # Metrics + categories
        m = dict(metrics_by_name.get(name) or {})
        cats = categories_by_name.get(name) or []

        # Process name (from BoQ items list)
        proc_name = None
        try:
            best_boq_item = _pick_best_boq_item(boq_items, name) or {}
            proc = best_boq_item.get("process") if isinstance(best_boq_item.get("process"), dict) else {}
            proc_name = str(proc.get("name") or "").strip() or None
            if "boq_code" not in m and best_boq_item.get("boq_code"):
                m["boq_code"] = best_boq_item.get("boq_code")
        except Exception:
            proc_name = None

        # Closure + best chapter
        closure_item = closure_map.get(name) or {}
        reason = str(closure_item.get("reason") or "")
        hit_sections = closure_item.get("hit_sections") if isinstance(closure_item.get("hit_sections"), list) else []
        best_hit = (
            _pick_best_hit_section_precise(
                [h for h in hit_sections if isinstance(h, dict)],
                name=name,
                process_name=proc_name,
                categories=cats,
                section_text_by_title=section_text_by_title,
                drawing_files=drawing_files,
                standard_files=standard_files,
            )
            if hit_sections
            else None
        )

        chapter = None
        closure_ok = False
        triplet_count = 0
        hit_keys: list[str] = []
        has_units = False
        evidence_count = 0
        near_locs_prefill: List[str] = []
        selection_meta: Dict[str, Any] = {}

        if best_hit:
            chapter = str(best_hit.get("title") or "").strip() or None
            closure_ok = bool(best_hit.get("ok"))
            triplet_count = int(best_hit.get("triplet_count") or 0)
            hit_keys = [str(x) for x in (best_hit.get("hit_keys") or []) if str(x).strip()]
            has_units = bool(best_hit.get("has_units"))
            evidence_count = int(best_hit.get("evidence_count") or 0)
            selection_meta = {
                "mode": "quality_hit+relevance",
                "score": best_hit.get("_selection_score"),
                "base": best_hit.get("_selection_base"),
                "title_relevance": best_hit.get("_selection_relevance"),
                "typed_locator_hits": best_hit.get("_selection_typed_locator_hits"),
                "near_locator_count": best_hit.get("_selection_near_locator_count"),
            }
        else:
            # Fallback: best chapter that mentions the item (not simply first mention).
            chapter, near_locs_prefill, fb_reason = _pick_best_mention_section(
                name=name,
                process_name=proc_name,
                categories=cats,
                sections=sections,
                drawing_files=drawing_files,
                standard_files=standard_files,
            )
            reason = reason or fb_reason
            selection_meta = {
                "mode": "fallback_mentioned",
                "score_basis": "title_relevance+typed_locator_hits+near_locator_count",
            }

        if chapter:
            mentioned += 1

        # Evidence locators
        drawing_loc = draw_loc_by_chapter.get(chapter) if chapter else None
        standard_loc = std_loc_by_chapter.get(chapter) if chapter else None

        # Extract evidence markers near the first mention in chapter content (best-effort).
        near_locs: List[str] = []
        if near_locs_prefill:
            near_locs = list(near_locs_prefill)
        elif chapter:
            for sec in sections:
                if str(sec.get("title") or "").strip() != chapter:
                    continue
                near_locs = _extract_evidence_locators_near(str(sec.get("content") or ""), name)
                break

        # If chapter bindings are missing, fall back to locators found near the item mention.
        if chapter and not drawing_loc and has_drawings:
            drawing_loc = _pick_locator_by_known_filenames(near_locs, drawing_files) or None
        if chapter and not standard_loc and has_standards:
            standard_loc = _pick_locator_by_known_filenames(near_locs, standard_files) or None

        # Missing parts for readability
        missing_parts: List[str] = []
        if not chapter:
            missing_parts.append("未出现")
        else:
            if triplet_count <= 0:
                missing_parts.append("三元组")
            if (len(hit_keys) < 3) or (not has_units):
                missing_parts.append("量化")
            if evidence_count <= 0 and not near_locs:
                missing_parts.append("证据")

        flags: List[str] = []
        if chapter and has_drawings and not drawing_loc:
            missing_drawing += 1
            flags.append("缺图纸定位")
        if chapter and has_standards and not standard_loc:
            missing_standard += 1
            flags.append("缺标准定位")
        if missing_parts and missing_parts != ["未出现"]:
            flags.append("闭环缺口:" + ",".join(missing_parts))

        if closure_ok:
            closed_ok += 1

        focus_rows.append(
            {
                "name": name,
                "categories": cats,
                "boq_code": m.get("boq_code"),
                "quantity": m.get("quantity"),
                "unit": m.get("unit"),
                "unit_price": m.get("unit_price"),
                "total_price": m.get("total_price"),
                "process_name": proc_name,
                "chapter": chapter,
                "drawing_locator": drawing_loc,
                "standard_locator": standard_loc,
                "evidence_locators_near": near_locs,
                "closure": {
                    "ok": closure_ok,
                    "reason": reason or ("ok" if closure_ok else "unknown"),
                    "triplet_count": triplet_count,
                    "hit_keys": hit_keys,
                    "has_units": has_units,
                    "evidence_count": evidence_count,
                    "missing_parts": missing_parts,
                },
                "chapter_selection": selection_meta,
                "flags": flags,
            }
        )

    return {
        "ok": bool(focus_rows),
        "project_id": pid,
        "focus_count": len(focus_rows),
        "mentioned_count": mentioned,
        "closed_ok_count": closed_ok,
        "missing_drawing_locator_count": missing_drawing,
        "missing_standard_locator_count": missing_standard,
        "focus_items": focus_rows,
    }
