from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Tuple


_EVIDENCE_RE = re.compile(r"【证据:[^】]{1,240}】")
# Evidence locator core: "#p{page}_{sha}@{offset}" (filename may be Chinese; strip the locator part).
_LOCATOR_RE = re.compile(r"#p\d{1,6}_[0-9a-fA-F]{6,16}@\d{1,10}")
_BRACKET_RE = re.compile(r"【([^】]{1,240})】")
_WS_RE = re.compile(r"[\s\u3000]+")
_PUNCT_RE = re.compile(r"[，,。．.；;：:、!！?？()\uFF08\uFF09（）\[\]{}<>《》“”‘’'\"\\-—_~`·•]+")
_FILE_RE = re.compile(r"[A-Za-z0-9_\-\u4e00-\u9fff]{1,80}\.(pdf|docx|doc|xlsx|xls|png|jpg|jpeg|dwg|dxf)", re.IGNORECASE)
_SPECIAL_BLOCK_RE = re.compile(
    r"(【清单重点项控制卡】.*?)(?=(【[^】]{1,240}】)|\Z)|"
    r"(【图纸证据定位】.*?)(?=(【[^】]{1,240}】)|\Z)|"
    r"(【企业标准证据定位】.*?)(?=(【[^】]{1,240}】)|\Z)|"
    r"(【四新技术闭环卡片[^】]{0,80}】.*?)(?=(【[^】]{1,240}】)|\Z)",
    re.S,
)


def _normalize_for_similarity(text: str) -> str:
    """
    Normalize chapter text for similarity measurement.
    - Remove evidence markers/locators which are expected to be shared across variants.
    - Collapse whitespace/punctuation so char n-grams are comparable.
    """
    s = str(text or "")
    if not s:
        return ""
    # Remove deterministic blocks that are expected to be identical across variants.
    # Similarity should focus on intra-chapter reasoning, not on fixed evidence/control-card text.
    s = _SPECIAL_BLOCK_RE.sub("", s)
    s = _EVIDENCE_RE.sub("", s)
    s = _LOCATOR_RE.sub("", s)
    s = _FILE_RE.sub("", s)
    # Keep bracket headings (they are part of intra-chapter structure), but drop the brackets.
    s = _BRACKET_RE.sub(r"\\1", s)
    s = _WS_RE.sub("", s)
    s = _PUNCT_RE.sub("", s)
    return s.strip()


def _char_ngrams(s: str, n: int) -> List[str]:
    s = s or ""
    if n <= 1:
        return list(s)
    if len(s) <= n:
        return [s] if s else []
    return [s[i : i + n] for i in range(0, len(s) - n + 1)]


def _set_jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa = set(a)
    sb = set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return float(inter) / float(union or 1)


def _cosine_sim_freq(a: List[str], b: List[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    fa: Dict[str, int] = {}
    fb: Dict[str, int] = {}
    for t in a:
        fa[t] = fa.get(t, 0) + 1
    for t in b:
        fb[t] = fb.get(t, 0) + 1
    # dot product on intersection
    dot = 0.0
    for k, va in fa.items():
        vb = fb.get(k)
        if vb:
            dot += float(va * vb)
    na = math.sqrt(sum(float(v * v) for v in fa.values()))
    nb = math.sqrt(sum(float(v * v) for v in fb.values()))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return float(dot) / float(na * nb)


def pair_similarity(text_a: str, text_b: str) -> Dict[str, Any]:
    """
    Return multiple similarity signals:
    - jaccard3: Jaccard similarity on 3-char shingles (structure/phrase sensitivity).
    - cosine2: cosine similarity on 2-char n-gram frequency (robust to small edits).
    - combined: weighted blend used for gating/reporting.
    """
    a = _normalize_for_similarity(text_a)
    b = _normalize_for_similarity(text_b)
    grams3_a = _char_ngrams(a, 3)
    grams3_b = _char_ngrams(b, 3)
    grams2_a = _char_ngrams(a, 2)
    grams2_b = _char_ngrams(b, 2)
    j3 = _set_jaccard(grams3_a, grams3_b)
    c2 = _cosine_sim_freq(grams2_a, grams2_b)
    combined = (0.60 * j3) + (0.40 * c2)
    return {
        "len_a": len(a),
        "len_b": len(b),
        "jaccard3": round(j3, 4),
        "cosine2": round(c2, 4),
        "combined": round(combined, 4),
    }


def compute_variant_similarity(
    variants: List[Dict[str, Any]],
    *,
    chapter_threshold: float = 0.90,
    overall_threshold: float = 0.85,
    min_chars: int = 800,
    ignore_title_keywords: List[str] | None = None,
    relaxed_title_keywords: List[str] | None = None,
    relaxed_chapter_threshold: float | None = None,
) -> Dict[str, Any]:
    """
    Compute cross-variant similarity per chapter and overall.
    Goal: detect "variants differ only by word swaps" while allowing factual overlap.
    """
    ignore_title_keywords = ignore_title_keywords or ["封面", "目录", "投标函", "授权委托", "承诺书", "声明", "报价"]
    relaxed_title_keywords = relaxed_title_keywords or ["项目概况", "工程概况", "总体概述", "编制依据", "投标响应", "响应"]
    if relaxed_chapter_threshold is None:
        relaxed_chapter_threshold = min(0.97, float(chapter_threshold) + 0.05)
    if not isinstance(variants, list) or len(variants) < 2:
        return {"ok": True, "reason": "variants<2", "variant_count": len(variants or [])}

    # Stable ordering (v1..vn).
    ordered = [v for v in variants if isinstance(v, dict)]
    if len(ordered) < 2:
        return {"ok": True, "reason": "variants_not_dict", "variant_count": len(variants or [])}

    outline = ordered[0].get("outline") if isinstance(ordered[0].get("outline"), list) else []
    if not outline:
        # Fallback: union titles in v1
        outline = [str(s.get("title") or "").strip() for s in (ordered[0].get("sections") or []) if isinstance(s, dict) and str(s.get("title") or "").strip()]

    def _sections_map(v: Dict[str, Any]) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for s in v.get("sections") or []:
            if not isinstance(s, dict):
                continue
            t = str(s.get("title") or "").strip()
            if not t:
                continue
            out[t] = str(s.get("content") or "")
        return out

    by_variant = [_sections_map(v) for v in ordered]

    pairs: List[Tuple[int, int]] = []
    for i in range(len(by_variant)):
        for j in range(i + 1, len(by_variant)):
            pairs.append((i + 1, j + 1))

    by_chapter: List[Dict[str, Any]] = []
    flagged: List[Dict[str, Any]] = []
    relaxed_flagged: List[Dict[str, Any]] = []
    strict_scores: List[float] = []
    all_scores: List[float] = []
    relaxed_count = 0

    for title in outline:
        t = str(title or "").strip()
        if not t:
            continue
        if any(k in t for k in ignore_title_keywords if k):
            continue
        is_relaxed = any(k in t for k in relaxed_title_keywords if k)
        texts = [m.get(t) for m in by_variant]
        if any(x is None for x in texts):
            continue
        # Skip very short chapters to avoid noisy similarity.
        lens = [len(_normalize_for_similarity(x or "")) for x in texts]
        if max(lens or [0]) < max(120, int(min_chars or 0)):
            continue

        rec: Dict[str, Any] = {"title": t, "lens": lens, "relaxed": bool(is_relaxed)}
        max_sim = 0.0
        max_pair = None
        sims = []
        for a, b in pairs:
            ps = pair_similarity(texts[a - 1] or "", texts[b - 1] or "")
            key = f"v{a}_v{b}"
            rec[key] = ps
            sims.append((key, float(ps.get("combined") or 0.0)))
            if float(ps.get("combined") or 0.0) > max_sim:
                max_sim = float(ps.get("combined") or 0.0)
                max_pair = key
        rec["max_pair"] = max_pair
        rec["max_combined"] = round(max_sim, 4)
        thr_used = float(relaxed_chapter_threshold) if is_relaxed else float(chapter_threshold)
        rec["threshold"] = round(thr_used, 4)
        by_chapter.append(rec)
        all_scores.append(float(max_sim))
        if is_relaxed:
            relaxed_count += 1
            if max_sim >= float(relaxed_chapter_threshold):
                relaxed_flagged.append(
                    {
                        "title": t,
                        "pair": max_pair,
                        "similarity": round(max_sim, 4),
                        "lens": lens,
                        "relaxed": True,
                        "threshold": round(float(relaxed_chapter_threshold), 4),
                    }
                )
        else:
            strict_scores.append(float(max_sim))
            if max_sim >= float(chapter_threshold):
                flagged.append(
                    {
                        "title": t,
                        "pair": max_pair,
                        "similarity": round(max_sim, 4),
                        "lens": lens,
                        "relaxed": False,
                        "threshold": round(float(chapter_threshold), 4),
                    }
                )

    # Overall: average of per-chapter max similarity.
    avg_max_all = 0.0
    if all_scores:
        avg_max_all = sum(all_scores) / float(len(all_scores))
    avg_max_strict = 0.0
    if strict_scores:
        avg_max_strict = sum(strict_scores) / float(len(strict_scores))

    ok = (avg_max_strict < float(overall_threshold)) and (len(flagged) == 0)
    return {
        "ok": bool(ok),
        "variant_count": len(by_variant),
        "chapter_threshold": float(chapter_threshold),
        "overall_threshold": float(overall_threshold),
        "min_chars": int(min_chars or 0),
        # Gate uses strict chapters; relaxed chapters are excluded from failing the diversity gate.
        "avg_max_similarity": round(float(avg_max_strict), 4),
        "avg_max_similarity_all": round(float(avg_max_all), 4),
        "relaxed_chapter_threshold": float(relaxed_chapter_threshold),
        "strict_chapter_count": int(len(strict_scores)),
        "relaxed_chapter_count": int(relaxed_count),
        "flagged_count": len(flagged),
        "flagged": flagged[:24],
        "relaxed_flagged_count": int(len(relaxed_flagged)),
        "relaxed_flagged": relaxed_flagged[:24],
        "by_chapter": by_chapter[:200],
    }
