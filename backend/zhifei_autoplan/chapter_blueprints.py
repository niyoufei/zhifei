from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BLUEPRINT_PATH = Path("backend/data/autoplan/chapter_blueprints.json")

_CACHE: dict | None = None
_CACHE_MTIME_NS: int | None = None


def _safe_title(title: str) -> str:
    t = str(title or "").strip()
    # Strip common numbering prefixes: "01 ", "1、", "第1章" etc.
    t = re.sub(r"^第\\s*[一二三四五六七八九十百0-9]+\\s*章\\s*", "", t)
    t = re.sub(r"^[0-9]{1,2}\\s*[\\.、\\)）]\\s*", "", t)
    t = re.sub(r"^[（\\(]?[0-9]{1,2}[）\\)]\\s*", "", t)
    return t.strip()


def load_blueprint_pack() -> dict:
    """
    Load chapter blueprints pack.
    File is user-editable and intended to control "章内结构" without changing tender outline.
    """
    global _CACHE, _CACHE_MTIME_NS
    if not BLUEPRINT_PATH.exists() or not BLUEPRINT_PATH.is_file():
        return {"version": "", "min_score": 4, "blueprints": []}
    try:
        mtime_ns = int(BLUEPRINT_PATH.stat().st_mtime_ns)
    except Exception:
        mtime_ns = None
    if _CACHE is not None and mtime_ns is not None and _CACHE_MTIME_NS == mtime_ns:
        return _CACHE
    try:
        obj = json.loads(BLUEPRINT_PATH.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            obj = {}
    except Exception:
        obj = {}
    obj.setdefault("min_score", 4)
    obj.setdefault("blueprints", [])
    _CACHE = obj
    _CACHE_MTIME_NS = mtime_ns
    return obj


def list_blueprints() -> List[Dict[str, Any]]:
    pack = load_blueprint_pack()
    bps = pack.get("blueprints")
    return bps if isinstance(bps, list) else []


def _score_blueprint(title: str, bp: Dict[str, Any]) -> float:
    t = _safe_title(title)
    if not t:
        return 0.0
    match = bp.get("match") if isinstance(bp.get("match"), dict) else {}
    any_k = match.get("any") if isinstance(match.get("any"), list) else []
    all_k = match.get("all") if isinstance(match.get("all"), list) else []
    regexes = match.get("regex") if isinstance(match.get("regex"), list) else []

    any_k = [str(x).strip() for x in any_k if str(x).strip()]
    all_k = [str(x).strip() for x in all_k if str(x).strip()]
    regexes = [str(x).strip() for x in regexes if str(x).strip()]

    # Hard filter: all keywords must appear when configured.
    for k in all_k:
        if k not in t:
            return 0.0

    score = 0.0
    for k in any_k:
        if k and k in t:
            score += float(min(10, max(2, len(k))))

    for pat in regexes:
        try:
            if re.search(pat, t):
                score += 8.0
        except Exception:
            continue

    # Light boost when the blueprint name itself overlaps.
    name = str(bp.get("name") or "").strip()
    if name and (name in t or t in name):
        score += 6.0
    return score


def match_chapter_blueprint(title: str) -> Optional[Dict[str, Any]]:
    """
    Match a blueprint for a chapter title (best-effort).
    Returns the matched blueprint dict or None.
    """
    pack = load_blueprint_pack()
    bps = pack.get("blueprints")
    if not isinstance(bps, list) or not bps:
        return None
    try:
        min_score = float(pack.get("min_score") or 4)
    except Exception:
        min_score = 4.0

    best: Tuple[float, Dict[str, Any]] | None = None
    for bp in bps:
        if not isinstance(bp, dict):
            continue
        sc = _score_blueprint(title, bp)
        if sc <= 0:
            continue
        if best is None or sc > best[0]:
            best = (sc, bp)
    if not best:
        return None
    if float(best[0]) < float(min_score):
        return None
    return dict(best[1])


def render_blueprint_requirements(bp: Dict[str, Any]) -> List[str]:
    """
    Render blueprint guidance into requirement lines suitable for SectionWriter prompt.
    Keep it short, concrete, and free of placeholder language.
    """
    if not isinstance(bp, dict):
        return []
    name = str(bp.get("name") or "").strip()
    anchors = bp.get("anchors") if isinstance(bp.get("anchors"), list) else []
    anchors = [str(x).strip() for x in anchors if str(x).strip()]
    guidance = bp.get("guidance") if isinstance(bp.get("guidance"), list) else []
    guidance = [str(x).strip() for x in guidance if str(x).strip()]
    out = []
    if name:
        out.append(f"章节结构参考（来自章节蓝图）：{name}")
    if anchors:
        out.append("本章必须出现的小标题/锚点：" + "、".join(anchors[:8]))
    for g in guidance[:10]:
        out.append(g)
    return out

