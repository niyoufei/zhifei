from __future__ import annotations

from typing import Any, Dict, List


def _extract_evidence_count(text: str) -> int:
    return str(text or "").count("【证据:")


def _extract_traceable_count(text: str) -> int:
    import re

    return len(re.findall(r"【证据:[^】]{1,120}#(?:p\d+_)?[0-9a-f]{6,}@\d+】", str(text or ""), flags=re.IGNORECASE))


def build_score_mapping(
    *,
    tender: Dict[str, Any],
    sections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    items = tender.get("items") if isinstance(tender, dict) and isinstance(tender.get("items"), list) else []
    sec_rows = [
        {
            "title": str(s.get("title") or "").strip() or "章节",
            "text": str(s.get("content") or ""),
            "evidence_count": _extract_evidence_count(str(s.get("content") or "")),
            "traceable_count": _extract_traceable_count(str(s.get("content") or "")),
        }
        for s in sections or []
        if isinstance(s, dict)
    ]

    item_cards: List[Dict[str, Any]] = []
    total_estimated = 0.0
    total_weight = 0.0
    high_risk: List[Dict[str, Any]] = []

    for idx, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        dim = str(it.get("dimension") or "评分项")
        kws = [str(x).strip() for x in (it.get("keywords") or []) if str(x).strip()]
        if not kws:
            continue

        matched_kw = []
        matched_sections = []
        evidence_sum = 0
        traceable_sum = 0

        for s in sec_rows:
            hit = [kw for kw in kws if kw in s["text"]]
            if hit:
                matched_sections.append(s["title"])
                evidence_sum += int(s.get("evidence_count") or 0)
                traceable_sum += int(s.get("traceable_count") or 0)
                for h in hit:
                    if h not in matched_kw:
                        matched_kw.append(h)

        coverage = len(matched_kw) / max(1, len(kws))
        evidence_factor = min(1.0, (evidence_sum / max(1, len(matched_sections))) / 3.0) if matched_sections else 0.0
        trace_factor = min(1.0, (traceable_sum / max(1, len(matched_sections))) / 1.0) if matched_sections else 0.0

        raw_weight = it.get("weight")
        try:
            w = float(raw_weight)
        except Exception:
            w = 0.5

        # Support two weight conventions:
        # - [0,1]: normalized weight
        # - >1: point-based weight in raw tender matrix
        normalized_weight = w if 0 <= w <= 1 else min(1.0, w / 100.0)
        estimated = 100.0 * normalized_weight * coverage * (0.75 + 0.15 * evidence_factor + 0.10 * trace_factor)

        missed = [kw for kw in kws if kw not in matched_kw]
        penalty_risk = (1.0 - coverage) + (0.3 if trace_factor < 0.5 else 0.0)

        card = {
            "item_id": f"ITEM-{idx + 1:03d}",
            "dimension": dim,
            "weight_raw": w,
            "weight_normalized": round(normalized_weight, 4),
            "keywords": kws,
            "matched_keywords": matched_kw,
            "missing_keywords": missed,
            "matched_sections": sorted(list(set(matched_sections))),
            "evidence_count": evidence_sum,
            "traceable_evidence_count": traceable_sum,
            "coverage_ratio": round(coverage, 4),
            "estimated_score": round(estimated, 3),
            "deduction_risk": round(max(0.0, min(1.0, penalty_risk)), 4),
        }
        item_cards.append(card)
        total_estimated += estimated
        total_weight += normalized_weight
        if card["deduction_risk"] >= 0.45:
            high_risk.append(card)

    max_possible = 100.0 * max(0.01, total_weight)
    total_ratio = min(1.0, total_estimated / max_possible)

    return {
        "ok": True,
        "item_cards": item_cards,
        "summary": {
            "item_count": len(item_cards),
            "total_weight": round(total_weight, 4),
            "estimated_score": round(total_estimated, 3),
            "estimated_ratio": round(total_ratio, 4),
            "high_risk_item_count": len(high_risk),
        },
        "high_risk_items": high_risk[:24],
    }
