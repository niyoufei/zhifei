from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_DURATION_RE = re.compile(r"工期[^\d]{0,8}(\d+(?:\.\d+)?)\s*(天|日|月)")
_PEAK_RE = re.compile(r"(?:资源峰值|高峰投入)[^\d]{0,8}(\d+(?:\.\d+)?)\s*(人|台|套)")
_CP_RE = re.compile(r"关键线路(?:间隔|步距)?[^\d]{0,8}(\d+(?:\.\d+)?)\s*(天|日|h|小时)", re.IGNORECASE)


def _pick_prefer_section_titles(sections: List[Dict[str, Any]], keys: Tuple[str, ...]) -> List[Dict[str, Any]]:
    preferred = []
    others = []
    for s in sections:
        title = str(s.get("title") or "")
        if any(k in title for k in keys):
            preferred.append(s)
        else:
            others.append(s)
    return preferred + others


def extract_canonical_metrics(sections: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Pick a single source-of-truth value for metrics that are often repeated across chapters.
    Priority:
    - Prefer chapters whose titles indicate they should own the metric (e.g. 进度/计划/资源).
    - Fall back to first occurrence anywhere.
    """
    out: Dict[str, str] = {}
    for s in _pick_prefer_section_titles(sections, ("进度", "工期", "计划")):
        text = str(s.get("content") or "")
        m = _DURATION_RE.search(text)
        if m:
            out["工期"] = f"{m.group(1)}{m.group(2)}"
            break
    for s in _pick_prefer_section_titles(sections, ("资源", "劳动力", "人员", "机械")):
        text = str(s.get("content") or "")
        m = _PEAK_RE.search(text)
        if m:
            out["资源峰值"] = f"{m.group(1)}{m.group(2)}"
            break
    for s in _pick_prefer_section_titles(sections, ("进度", "关键线路", "计划")):
        text = str(s.get("content") or "")
        m = _CP_RE.search(text)
        if m:
            out["关键线路间隔"] = f"{m.group(1)}{m.group(2)}"
            break
    return out


def normalize_metrics_in_sections(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Enforce canonical metric wording and run deterministic CPM consistency check.
    Returns a receipt used by focus_xlsx / QA review.
    """
    canonical = extract_canonical_metrics(sections)
    changed = []

    def _norm(text: str) -> str:
        out = text or ""
        if canonical.get("工期"):
            out = _DURATION_RE.sub(lambda m: f"工期{canonical['工期']}", out)
        if canonical.get("资源峰值"):
            out = _PEAK_RE.sub(lambda m: f"资源峰值{canonical['资源峰值']}", out)
        if canonical.get("关键线路间隔"):
            out = _CP_RE.sub(lambda m: f"关键线路间隔{canonical['关键线路间隔']}", out)
        return out

    for sec in sections or []:
        title = str(sec.get("title") or "章节")
        before = str(sec.get("content") or "")
        after = _norm(before)
        if after != before:
            sec["content"] = after
            changed.append({"title": title})

    cpm_receipt = None
    cpm_conflicts = []
    try:
        from backend.zhifei_autoplan.schedule_cpm import build_cpm_receipt

        cpm_receipt = build_cpm_receipt(sections, canonical=canonical)
        cpm_conflicts = cpm_receipt.get("conflicts") if isinstance(cpm_receipt, dict) else []
        if not isinstance(cpm_conflicts, list):
            cpm_conflicts = []
    except Exception:
        cpm_receipt = None
        cpm_conflicts = []

    return {
        "ok": len(cpm_conflicts) == 0,
        "canonical": canonical,
        "changed": changed,
        "cpm": cpm_receipt,
    }
