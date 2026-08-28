from __future__ import annotations

import unicodedata
from typing import Any, Iterable, List, Tuple


# Every producer and consumer of the BoQ focus list must use the same bound.
# A larger downstream bound makes strict delivery mathematically impossible
# when the enforcer and quality checks only process a prefix of the list.
MAX_BOQ_FOCUS_ITEMS = 20

BOQ_FOCUS_STAT_PRIORITY = (
    "hazardous_material_items",
    "ppe_items",
    "special_material_items",
    "top_total_price_items",
    "top_quantity_items",
    "top_material_demand_items",
    "top_unit_price_items",
)


def normalize_boq_focus_name(value: Any) -> str:
    """Remove spreadsheet line wrapping while retaining human-readable spaces."""

    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.replace("\r", "").replace("\n", "").replace("\t", "")
    return " ".join(text.split())


def boq_focus_name_key(value: Any) -> str:
    """Return a stable matching/de-duplication key for a BoQ item name."""

    return "".join(normalize_boq_focus_name(value).split()).casefold()


def _canonical_text_with_offsets(value: Any) -> Tuple[str, List[int], List[int]]:
    """Return canonical text plus a canonical-character -> source span map.

    NFKC and case-folding can expand one source character into several
    canonical characters (for example, a ligature), while combining marks can
    collapse several source characters into one.  Grouping a base character
    with its combining marks keeps returned offsets anchored to the complete
    source grapheme.  Whitespace is omitted from the canonical stream but
    remains inside the returned source span between adjacent matched tokens.
    """

    source = str(value or "")
    canonical: List[str] = []
    starts: List[int] = []
    ends: List[int] = []
    index = 0
    while index < len(source):
        cluster_end = index + 1
        while cluster_end < len(source) and unicodedata.combining(source[cluster_end]):
            cluster_end += 1
        normalized = unicodedata.normalize("NFKC", source[index:cluster_end]).casefold()
        for char in normalized:
            if char.isspace():
                continue
            canonical.append(char)
            starts.append(index)
            ends.append(cluster_end)
        index = cluster_end
    return "".join(canonical), starts, ends


def find_boq_focus_name_spans(
    name: Any,
    text: Any,
    *,
    limit: int | None = None,
) -> List[Tuple[int, int]]:
    """Find a BoQ name canonically and return non-overlapping source spans.

    Matching applies NFKC, case-folding and whitespace removal to both values.
    Each ``(start, end)`` pair indexes the original, unnormalised ``text`` so
    callers can safely take local evidence windows without losing alignment.
    ``limit=0`` (and any negative limit) deliberately returns no matches.
    """

    if limit is not None:
        match_limit = max(0, int(limit))
        if match_limit == 0:
            return []
    else:
        match_limit = None

    needle = boq_focus_name_key(name)
    if not needle:
        return []
    haystack, starts, ends = _canonical_text_with_offsets(text)
    if not haystack or len(needle) > len(haystack):
        return []

    spans: List[Tuple[int, int]] = []
    canonical_offset = 0
    while canonical_offset <= len(haystack) - len(needle):
        match_at = haystack.find(needle, canonical_offset)
        if match_at < 0:
            break
        canonical_end = match_at + len(needle)
        spans.append((starts[match_at], ends[canonical_end - 1]))
        if match_limit is not None and len(spans) >= match_limit:
            break
        canonical_offset = canonical_end
    return spans


def normalize_boq_focus_items(
    values: Iterable[Any] | None,
    *,
    limit: int = MAX_BOQ_FOCUS_ITEMS,
) -> List[str]:
    item_limit = max(0, int(limit))
    if item_limit == 0:
        return []
    result: List[str] = []
    seen: set[str] = set()
    for value in values or []:
        name = normalize_boq_focus_name(value)
        key = boq_focus_name_key(name)
        if not name or not key or key in seen:
            continue
        seen.add(key)
        result.append(name)
        if len(result) >= item_limit:
            break
    return result


def select_boq_focus_names(
    stats: Any,
    *,
    limit: int = MAX_BOQ_FOCUS_ITEMS,
) -> List[str]:
    """Select the one effective focus list shared by every strict consumer.

    Safety-sensitive materials are deliberately selected before commercial
    rankings so they cannot disappear merely because the global bound is full.
    """

    source = stats if isinstance(stats, dict) else {}
    candidates: List[Any] = []
    for key in BOQ_FOCUS_STAT_PRIORITY:
        rows = source.get(key) if isinstance(source.get(key), list) else []
        candidates.extend(
            row.get("name")
            for row in rows
            if isinstance(row, dict) and row.get("name")
        )
    return normalize_boq_focus_items(candidates, limit=limit)


def boq_focus_name_in_text(name: Any, text: Any) -> bool:
    return bool(find_boq_focus_name_spans(name, text, limit=1))
