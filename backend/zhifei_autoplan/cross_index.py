from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.boq_focus_policy import (
    MAX_BOQ_FOCUS_ITEMS,
    boq_focus_name_in_text,
    boq_focus_name_key,
    find_boq_focus_name_spans,
    normalize_boq_focus_items,
    normalize_boq_focus_name,
    select_boq_focus_names,
)

_EVIDENCE_RE = re.compile(r"【证据:(?P<loc>[^】]{3,160})】")
_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_GENERIC_CHAPTER_RE = re.compile(r"(工程概况|项目概况|总体部署|资源配置|组织机构|编制依据|总说明|综合说明)")
_DRAWING_LOCATOR_RE = re.compile(
    r"^(?P<filename>.+)#p(?P<page>[1-9]\d*)_(?P<sha256>[0-9a-fA-F]{64})@(?P<offset>\d+)$"
)
_GENERIC_DRAWING_TERMS = {
    "工程",
    "施工",
    "施工工艺",
    "施工方法",
    "施工方案",
    "技术措施",
    "安装",
    "作业",
    "工艺",
    "流程",
    "图纸",
    "图",
    "详图",
    "大样",
    "节点",
    "详见",
    "说明",
    "做法",
    "材料",
    "项目",
}
_DRAWING_ALIAS_GROUPS = (
    ("高强螺栓", "高强度螺栓"),
    ("天棚", "顶棚"),
    ("大便器", "坐便器"),
    ("外墙涂料", "外墙油漆"),
)
_DRAWING_REQUIREMENT_STATES = {"required", "optional", "not_applicable"}


def _to_float(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError, OverflowError):
        return None


def _pick_best_boq_item(items: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    target_key = boq_focus_name_key(name)
    cands = [
        it
        for it in (items or [])
        if boq_focus_name_key(it.get("name")) == target_key
    ]
    if not cands:
        return None

    def _score(it: dict[str, Any]) -> float:
        # Prefer higher total price; fall back to quantity.
        tp = _to_float(it.get("total_price")) or 0.0
        qty = _to_float(it.get("quantity")) or 0.0
        return tp * 1.0 + qty * 1e-6

    return max(cands, key=_score)


def _index_boq_stats(boq: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """
    Build:
    - metrics_by_name: {name: {boq_code, quantity, unit, unit_price, total_price}}
    - categories_by_name: {name: [category labels...]}
    """
    stats = boq.get("stats") if isinstance(boq.get("stats"), dict) else {}
    metrics_by_key: dict[str, dict[str, Any]] = {}
    cats_by_key: dict[str, set[str]] = {}
    display_by_key: dict[str, str] = {}

    def _merge_metrics(name: str, it: dict[str, Any]):
        key = boq_focus_name_key(name)
        if not key:
            return
        display_by_key.setdefault(key, normalize_boq_focus_name(name))
        m = metrics_by_key.setdefault(key, {})
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
            name = normalize_boq_focus_name(it.get("name"))
            key_name = boq_focus_name_key(name)
            if not name or not key_name:
                continue
            display_by_key.setdefault(key_name, name)
            cats_by_key.setdefault(key_name, set()).add(label)
            _merge_metrics(name, it)

    _add_cat("top_quantity_items", "工程量大")
    _add_cat("top_material_demand_items", "材料需求量大")
    _add_cat("top_total_price_items", "单体造价高")
    _add_cat("top_unit_price_items", "材料单价高")
    _add_cat("special_material_items", "特殊材料")
    _add_cat("hazardous_material_items", "危险品材料")
    _add_cat("ppe_items", "劳保用品")

    metrics_by_name = {
        display_by_key[key]: value for key, value in metrics_by_key.items()
    }
    categories_by_name: dict[str, list[str]] = {
        display_by_key[key]: sorted(values)
        for key, values in cats_by_key.items()
    }
    return metrics_by_name, categories_by_name


def _lookup_normalized_name(mapping: dict[str, Any], name: str, default: Any) -> Any:
    """Resolve data indexed by a human-readable BoQ name using its stable key."""

    target_key = boq_focus_name_key(name)
    for candidate, value in mapping.items():
        if boq_focus_name_key(candidate) == target_key:
            return value
    return default


def _index_chapter_locators(index_obj: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
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


def _index_chapter_bindings(index_obj: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    idx = index_obj or {}
    binds = idx.get("chapter_bindings") if isinstance(idx.get("chapter_bindings"), list) else []
    for binding in binds:
        if not isinstance(binding, dict):
            continue
        chapter = str(binding.get("chapter") or "").strip()
        locator = str(binding.get("locator") or "").strip()
        if chapter and locator:
            out.setdefault(chapter, []).append(dict(binding))
    return out


def _index_focus_drawing_bindings(
    boq_focus: dict[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Index deterministic item-specific bindings without trusting them."""

    out: dict[str, list[dict[str, Any]]] = {}
    raw = (boq_focus or {}).get("drawing_bindings")
    for binding in raw if isinstance(raw, list) else []:
        if not isinstance(binding, dict):
            continue
        focus_key = boq_focus_name_key(binding.get("focus_item"))
        locator = str(binding.get("locator") or "").strip()
        if focus_key and locator:
            out.setdefault(focus_key, []).append(dict(binding))
    return out


def _validate_focus_binding_relation(
    binding: dict[str, Any],
    *,
    name: str,
    chapter: str,
    project_id: str | None,
) -> tuple[bool, dict[str, Any]]:
    relation = binding.get("source_relation")
    if not isinstance(relation, dict):
        return False, {"reason": "focus_binding_source_relation_missing"}
    if str(relation.get("type") or "").strip() != "boq_focus_item_drawing":
        return False, {"reason": "focus_binding_source_relation_invalid"}
    if boq_focus_name_key(binding.get("focus_item")) != boq_focus_name_key(name):
        return False, {"reason": "focus_binding_item_mismatch"}
    if boq_focus_name_key(relation.get("focus_item")) != boq_focus_name_key(name):
        return False, {"reason": "focus_binding_relation_item_mismatch"}
    binding_chapter = str(binding.get("chapter") or "").strip()
    relation_chapter = str(relation.get("chapter") or "").strip()
    if binding_chapter != chapter or relation_chapter != chapter:
        return False, {"reason": "focus_binding_chapter_mismatch"}
    if project_id:
        binding_project = str(binding.get("project_id") or "").strip()
        relation_project = str(relation.get("project_id") or "").strip()
        if binding_project != project_id or relation_project != project_id:
            return False, {"reason": "focus_binding_project_mismatch"}
    return True, {"reason": "validated"}


def _compact_text(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(char for char in normalized if char.isalnum() or "\u4e00" <= char <= "\u9fff")


def _specific_drawing_terms(*values: Any) -> list[str]:
    terms: list[str] = []
    for value in values:
        raw = unicodedata.normalize("NFKC", str(value or ""))
        for token in _TOKEN_RE.findall(raw):
            compact = _compact_text(token)
            if len(compact) < 2 or compact in _GENERIC_DRAWING_TERMS:
                continue
            reduced = compact
            for generic in sorted(_GENERIC_DRAWING_TERMS, key=len, reverse=True):
                reduced = reduced.replace(_compact_text(generic), "")
            for candidate in (compact, reduced):
                if len(candidate) >= 2 and candidate not in _GENERIC_DRAWING_TERMS and candidate not in terms:
                    terms.append(candidate)

    expanded = list(terms)
    for term in terms:
        for aliases in _DRAWING_ALIAS_GROUPS:
            compact_aliases = [_compact_text(alias) for alias in aliases]
            for alias in compact_aliases:
                if alias and alias in term:
                    for replacement in compact_aliases:
                        candidate = term.replace(alias, replacement)
                        if len(candidate) >= 2 and candidate not in expanded:
                            expanded.append(candidate)
    return sorted(expanded, key=lambda item: (-len(item), item))


def _drawing_catalog(index_obj: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    catalog: dict[str, list[dict[str, Any]]] = {}
    drawings = (index_obj or {}).get("drawings")
    for drawing in drawings if isinstance(drawings, list) else []:
        if not isinstance(drawing, dict):
            continue
        filename = str(drawing.get("filename") or "").strip()
        sha256 = str(drawing.get("sha256") or "").strip().lower()
        if not filename or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
            continue
        catalog.setdefault(filename, []).append(dict(drawing))
    return catalog


def _drawing_requirement_for(
    boq_focus: dict[str, Any] | None,
    name: str,
    *,
    project_id: str | None,
) -> dict[str, Any]:
    """Resolve an explicit exemption or fail closed to required evidence."""

    raw_requirements = (boq_focus or {}).get("drawing_requirements")
    candidate: Any = None
    if isinstance(raw_requirements, dict):
        target_key = boq_focus_name_key(name)
        for raw_name, raw_value in raw_requirements.items():
            if boq_focus_name_key(raw_name) == target_key:
                candidate = raw_value
                break
    elif isinstance(raw_requirements, list):
        target_key = boq_focus_name_key(name)
        for raw_value in raw_requirements:
            if not isinstance(raw_value, dict):
                continue
            if boq_focus_name_key(raw_value.get("name")) == target_key:
                candidate = raw_value
                break

    if isinstance(candidate, str):
        status = candidate.strip().lower()
        reason = ""
    elif isinstance(candidate, dict):
        status = str(candidate.get("status") or candidate.get("requirement") or "").strip().lower()
        reason = str(candidate.get("reason") or "").strip()
    else:
        status = "required"
        reason = "focus_item_default"

    if status not in _DRAWING_REQUIREMENT_STATES:
        return {"status": "required", "reason": "invalid_requirement_status_fail_closed"}
    if status in {"optional", "not_applicable"} and not reason:
        return {"status": "required", "reason": "missing_exemption_reason_fail_closed"}
    if status in {"optional", "not_applicable"}:
        if not isinstance(candidate, dict):
            return {
                "status": "required",
                "reason": "exemption_receipt_missing_fail_closed",
                "requested_status": status,
            }
        receipt = candidate.get("approval_receipt")
        if not isinstance(receipt, dict):
            return {
                "status": "required",
                "reason": "exemption_receipt_missing_fail_closed",
                "requested_status": status,
            }
        receipt_status = str(receipt.get("status") or "").strip().lower()
        receipt_project_id = str(receipt.get("project_id") or "").strip()
        if receipt_status != "approved":
            return {
                "status": "required",
                "reason": "exemption_receipt_not_approved_fail_closed",
                "requested_status": status,
            }
        if not project_id:
            return {
                "status": "required",
                "reason": "exemption_project_identity_missing_fail_closed",
                "requested_status": status,
            }
        if receipt_project_id != project_id:
            return {
                "status": "required",
                "reason": "exemption_receipt_project_mismatch_fail_closed",
                "requested_status": status,
            }
        required_receipt_fields = ("receipt_id", "summary", "approved_by", "approved_at")
        if any(not str(receipt.get(field) or "").strip() for field in required_receipt_fields):
            return {
                "status": "required",
                "reason": "exemption_receipt_incomplete_fail_closed",
                "requested_status": status,
            }
        normalized_receipt = {
            "receipt_id": str(receipt.get("receipt_id") or "").strip(),
            "status": "approved",
            "project_id": receipt_project_id,
            "summary": str(receipt.get("summary") or "").strip(),
            "approved_by": str(receipt.get("approved_by") or "").strip(),
            "approved_at": str(receipt.get("approved_at") or "").strip(),
        }
        return {
            "status": status,
            "reason": reason,
            "approval_receipt": normalized_receipt,
        }
    return {"status": status, "reason": reason or "focus_item_default"}


def _pick_best_hit_section(hit_sections: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not hit_sections:
        return None

    def _score(h: dict[str, Any]) -> int:
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


def _chapter_relevance_score(name: str, process_name: str | None, categories: list[str], chapter_title: str) -> int:
    t = str(chapter_title or "").strip()
    low_t = t.lower()
    score = 0
    if name and boq_focus_name_in_text(name, t):
        score += 48
    if process_name and process_name in t:
        score += 72
    if _GENERIC_CHAPTER_RE.search(t):
        score -= 20

    q = " ".join([str(name or ""), str(process_name or ""), " ".join(categories or [])]).strip()
    sim = _jaccard(_tokenize_text(q), _tokenize_text(low_t))
    score += int(sim * 100)
    return score


def _typed_locator_hits(locs: list[str], drawing_files: set[str], standard_files: set[str]) -> int:
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
    hit_sections: list[dict[str, Any]],
    *,
    name: str,
    process_name: str | None,
    categories: list[str],
    section_text_by_title: dict[str, str],
    drawing_files: set[str],
    standard_files: set[str],
) -> dict[str, Any] | None:
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


def _validate_drawing_locator(
    locator: str,
    *,
    catalog: dict[str, list[dict[str, Any]]],
    binding: dict[str, Any] | None,
    relevance_values: list[Any],
) -> tuple[bool, dict[str, Any]]:
    """Reverse-check locator identity, page anchor and item/process relevance."""

    match = _DRAWING_LOCATOR_RE.fullmatch(str(locator or "").strip())
    if not match:
        return False, {"reason": "locator_format_invalid"}
    filename = str(match.group("filename") or "").strip()
    locator_sha256 = str(match.group("sha256") or "").lower()
    page = int(match.group("page"))
    offset = int(match.group("offset"))
    records = catalog.get(filename) or []
    identity_matches = [
        record
        for record in records
        if str(record.get("sha256") or "").strip().lower() == locator_sha256
    ]
    if len(identity_matches) != 1:
        return False, {
            "reason": (
                "drawing_identity_unknown"
                if not identity_matches
                else "drawing_identity_ambiguous"
            ),
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
        }
    drawing = identity_matches[0]
    if not isinstance(binding, dict):
        return False, {
            "reason": "drawing_binding_missing",
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
        }
    binding_filename = str(binding.get("filename") or "").strip()
    binding_sha = str(binding.get("sha256") or "").strip().lower()
    binding_locator = str(binding.get("locator") or "").strip()
    if binding_filename != filename:
        return False, {"reason": "binding_filename_mismatch", "filename": filename, "page": page}
    if binding_sha != locator_sha256:
        return False, {"reason": "binding_hash_mismatch", "filename": filename, "page": page}
    if binding_locator != str(locator or "").strip():
        return False, {"reason": "binding_locator_mismatch", "filename": filename, "page": page}
    try:
        if int(binding.get("page")) != page:
            return False, {"reason": "binding_page_mismatch", "filename": filename, "page": page}
    except (TypeError, ValueError):
        return False, {"reason": "binding_page_invalid", "filename": filename, "page": page}
    try:
        binding_offset = int(binding.get("offset"))
    except (TypeError, ValueError):
        return False, {"reason": "binding_offset_invalid", "filename": filename, "page": page}
    if binding_offset != offset:
        return False, {"reason": "binding_offset_mismatch", "filename": filename, "page": page}
    if str(drawing.get("text_status") or "") != "indexed":
        return False, {
            "reason": "drawing_text_or_ocr_missing",
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
        }

    anchors = drawing.get("page_anchors") if isinstance(drawing.get("page_anchors"), list) else []
    anchor = None
    for item in anchors:
        if not isinstance(item, dict):
            continue
        try:
            anchor_page = int(item.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if anchor_page == page:
            anchor = item
            break
    if not anchor:
        return False, {
            "reason": "drawing_page_anchor_unknown",
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
        }
    if (
        anchor.get("evidence_eligible") is not True
        or (
            str(anchor.get("ocr_status") or "").strip()
            and str(anchor.get("ocr_status") or "").strip() != "text"
        )
        or anchor.get("no_text_locator") is True
    ):
        return False, {
            "reason": "drawing_page_not_text_evidence",
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
        }
    if (
        not str(drawing.get("page_boundary_status") or "").startswith("reliable_")
        or str(anchor.get("boundary_source") or "")
        not in {"form_feed", "declared_single_page"}
    ):
        return False, {
            "reason": "drawing_page_boundary_unreliable",
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
        }
    try:
        start_offset = int(anchor.get("start_offset"))
        end_offset = int(anchor.get("end_offset"))
    except (TypeError, ValueError):
        return False, {"reason": "drawing_page_offset_bounds_invalid", "filename": filename, "page": page}
    if not (0 <= start_offset <= offset <= end_offset):
        return False, {
            "reason": "drawing_locator_offset_outside_page",
            "filename": filename,
            "page": page,
        }

    anchor_hash = str(anchor.get("text_sha256") or "").strip().lower()
    binding_page_hash = str(binding.get("page_text_sha256") or "").strip().lower()
    anchor_summary = str(anchor.get("snippet") or "").strip()
    binding_page_summary = str(binding.get("page_summary") or "").strip()
    if (
        re.fullmatch(r"[0-9a-f]{64}", anchor_hash) is None
        or binding_page_hash != anchor_hash
    ):
        return False, {"reason": "binding_page_hash_mismatch", "filename": filename, "page": page}
    if not anchor_summary or binding_page_summary != anchor_summary:
        return False, {"reason": "binding_page_summary_mismatch", "filename": filename, "page": page}
    if not str(binding.get("page_boundary_status") or "").startswith("reliable_"):
        return False, {"reason": "binding_page_boundary_unreliable", "filename": filename, "page": page}

    match_window = binding.get("match_window")
    if not isinstance(match_window, dict):
        return False, {"reason": "binding_match_window_missing", "filename": filename, "page": page}
    try:
        window_start = int(match_window.get("start_offset"))
        window_end = int(match_window.get("end_offset"))
        match_start = int(binding.get("match_start"))
        match_end = int(binding.get("match_end"))
    except (TypeError, ValueError):
        return False, {"reason": "binding_match_window_invalid", "filename": filename, "page": page}
    window_text = str(match_window.get("text") or "")
    window_hash = str(match_window.get("text_sha256") or "").strip().lower()
    matched_text = str(binding.get("matched_text") or "")
    if (
        not window_text
        or window_end - window_start != len(window_text)
        or len(window_text) > 640
        or not (start_offset <= window_start <= match_start < match_end <= window_end <= end_offset)
        or match_start != offset
        or match_start - window_start > 80
        or window_end - match_end > 160
    ):
        return False, {"reason": "binding_match_window_out_of_bounds", "filename": filename, "page": page}
    if hashlib.sha256(window_text.encode("utf-8")).hexdigest() != window_hash:
        return False, {"reason": "binding_match_window_hash_mismatch", "filename": filename, "page": page}
    relative_start = match_start - window_start
    relative_end = match_end - window_start
    if not matched_text or window_text[relative_start:relative_end] != matched_text:
        return False, {"reason": "binding_matched_text_mismatch", "filename": filename, "page": page}

    # Binding hashes attest only to the binding object.  Re-read the current
    # indexed extract and reverse-check every offset against those trusted
    # bytes so a self-consistent forged window cannot become formal evidence.
    extract_ref = str(drawing.get("extract_saved_as") or "").strip()
    expected_bytes_hash = str(drawing.get("extract_bytes_sha256") or "").strip().lower()
    expected_text_hash = str(drawing.get("extract_text_sha256") or "").strip().lower()
    if (
        not extract_ref
        or re.fullmatch(r"[0-9a-f]{64}", expected_bytes_hash) is None
        or re.fullmatch(r"[0-9a-f]{64}", expected_text_hash) is None
    ):
        return False, {
            "reason": "drawing_extract_reference_missing",
            "filename": filename,
            "page": page,
        }
    try:
        extract_path = Path(extract_ref)
        if not extract_path.is_file():
            return False, {
                "reason": "drawing_extract_reference_missing",
                "filename": filename,
                "page": page,
            }
        extract_bytes = extract_path.read_bytes()
    except OSError:
        return False, {
            "reason": "drawing_extract_read_failed",
            "filename": filename,
            "page": page,
        }
    extract_text = extract_bytes.decode("utf-8", errors="ignore")
    if (
        hashlib.sha256(extract_bytes).hexdigest() != expected_bytes_hash
        or hashlib.sha256(extract_text.encode("utf-8")).hexdigest()
        != expected_text_hash
    ):
        return False, {
            "reason": "drawing_extract_hash_mismatch",
            "filename": filename,
            "page": page,
        }
    actual_page_text = extract_text[start_offset:end_offset]
    if hashlib.sha256(actual_page_text.encode("utf-8")).hexdigest() != anchor_hash:
        return False, {
            "reason": "drawing_page_extract_hash_mismatch",
            "filename": filename,
            "page": page,
        }
    if extract_text[window_start:window_end] != window_text:
        return False, {
            "reason": "drawing_match_window_extract_mismatch",
            "filename": filename,
            "page": page,
        }
    if extract_text[match_start:match_end] != matched_text:
        return False, {
            "reason": "drawing_matched_text_extract_mismatch",
            "filename": filename,
            "page": page,
        }

    # Filename, chapter scope and discipline metadata may rank candidates but
    # never prove relevance.  Formal relevance comes solely from the bounded
    # text window around the recorded offset on the anchored page.
    evidence_text = _compact_text(window_text)
    item_terms = _specific_drawing_terms(relevance_values[0] if relevance_values else "")
    process_terms = _specific_drawing_terms(relevance_values[1] if len(relevance_values) > 1 else "")
    chapter_terms = _specific_drawing_terms(relevance_values[2] if len(relevance_values) > 2 else "")
    terms = list(dict.fromkeys([*item_terms, *process_terms, *chapter_terms]))
    matched_item_terms = [term for term in item_terms if term and term in evidence_text]
    matched_process_terms = [term for term in process_terms if term and term in evidence_text]
    matched_chapter_terms = [term for term in chapter_terms if term and term in evidence_text]
    matched_terms = list(
        dict.fromkeys([*matched_item_terms, *matched_process_terms, *matched_chapter_terms])
    )
    if not matched_item_terms and not matched_process_terms:
        return False, {
            "reason": (
                "drawing_locator_chapter_only"
                if matched_chapter_terms
                else "drawing_locator_irrelevant"
            ),
            "filename": filename,
            "sha256": locator_sha256,
            "page": page,
            "candidate_terms": terms[:12],
        }
    return True, {
        "reason": "validated",
        "filename": filename,
        "sha256": locator_sha256,
        "page": page,
        "offset": offset,
        "matched_terms": matched_terms[:8],
        "matched_item_terms": matched_item_terms[:8],
        "matched_process_terms": matched_process_terms[:8],
        "matched_chapter_terms": matched_chapter_terms[:8],
    }


def _pick_locator_by_known_filenames(locs: list[str], known: set[str]) -> str | None:
    if not locs or not known:
        return None
    for loc in locs:
        fn = _extract_filename_from_locator(loc)
        if fn and fn in known:
            return loc
    return None


def _extract_evidence_locators_near(text: str, needle: str, window: int = 520, max_locs: int = 4) -> list[str]:
    if not text or not needle:
        return []
    spans = find_boq_focus_name_spans(needle, text, limit=1)
    if not spans:
        return []
    pos, match_end = spans[0]
    start = max(0, pos - window)
    end = min(len(text), match_end + window)
    snippet = text[start:end]
    locs: list[str] = []
    for m in _EVIDENCE_RE.finditer(snippet):
        loc = str(m.group("loc") or "").strip()
        if not loc:
            continue
        if loc not in locs:
            locs.append(loc)
        if len(locs) >= max_locs:
            break
    return locs


def validate_cross_index_contract(
    value: Any,
    *,
    expected_names: list[Any] | None,
) -> dict[str, Any]:
    """Validate cross-index identity and bounded counters before delivery use."""

    expected = normalize_boq_focus_items(
        expected_names or [],
        limit=MAX_BOQ_FOCUS_ITEMS,
    )
    if not isinstance(value, dict):
        # Contract validation exposes one stable ValueError family to callers,
        # including schema and value failures after this initial type guard.
        raise ValueError("cross_index_not_object")  # noqa: TRY004
    required = {
        "focus_count",
        "mentioned_count",
        "closed_ok_count",
        "missing_drawing_locator_count",
        "missing_standard_locator_count",
        "focus_items",
    }
    if not required.issubset(value):
        raise ValueError("cross_index_schema_incomplete")
    if bool(value.get("build_failed")):
        raise ValueError("cross_index_build_failed")

    rows = value.get("focus_items")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("cross_index_focus_items_invalid")
    try:
        focus_count = int(value.get("focus_count"))
        mentioned_count = int(value.get("mentioned_count"))
        closed_count = int(value.get("closed_ok_count"))
        missing_drawing = int(value.get("missing_drawing_locator_count"))
        missing_standard = int(value.get("missing_standard_locator_count"))
    except (TypeError, ValueError) as exc:
        raise ValueError("cross_index_counter_invalid") from exc

    if focus_count != len(expected) or len(rows) != len(expected):
        raise ValueError("cross_index_focus_count_mismatch")
    if expected and value.get("ok") is not True:
        raise ValueError("cross_index_not_ok")
    row_keys = [boq_focus_name_key(row.get("name")) for row in rows]
    expected_keys = [boq_focus_name_key(name) for name in expected]
    if row_keys != expected_keys:
        raise ValueError("cross_index_focus_identity_mismatch")
    if not (
        0 <= closed_count <= mentioned_count <= focus_count
        and 0 <= missing_drawing <= mentioned_count
        and 0 <= missing_standard <= mentioned_count
    ):
        raise ValueError("cross_index_counter_out_of_range")
    if expected:
        calculated_mentioned = 0
        calculated_closed = 0
        calculated_missing_drawing = 0
        calculated_missing_standard = 0
        for row in rows:
            closure = row.get("closure") if isinstance(row.get("closure"), dict) else None
            requirement = (
                row.get("drawing_requirement")
                if isinstance(row.get("drawing_requirement"), dict)
                else None
            )
            validation = (
                row.get("drawing_validation")
                if isinstance(row.get("drawing_validation"), dict)
                else None
            )
            if closure is None or requirement is None or validation is None:
                raise ValueError("cross_index_row_schema_incomplete")
            requirement_status = str(requirement.get("status") or "")
            requirement_reason = str(requirement.get("reason") or "").strip()
            if requirement_status not in _DRAWING_REQUIREMENT_STATES:
                raise ValueError("cross_index_drawing_requirement_invalid")
            if requirement_status in {"optional", "not_applicable"} and not requirement_reason:
                raise ValueError("cross_index_drawing_exemption_reason_missing")
            if requirement_status in {"optional", "not_applicable"}:
                receipt = requirement.get("approval_receipt")
                if not isinstance(receipt, dict):
                    raise ValueError("cross_index_drawing_exemption_receipt_missing")
                if str(receipt.get("status") or "").strip().lower() != "approved":
                    raise ValueError("cross_index_drawing_exemption_not_approved")
                project_id = str(value.get("project_id") or "").strip()
                if (
                    not project_id
                    or str(receipt.get("project_id") or "").strip() != project_id
                ):
                    raise ValueError("cross_index_drawing_exemption_project_mismatch")
                for field in ("receipt_id", "summary", "approved_by", "approved_at"):
                    if not str(receipt.get(field) or "").strip():
                        raise ValueError("cross_index_drawing_exemption_receipt_incomplete")

            chapter_present = bool(str(row.get("chapter") or "").strip())
            drawing_locator = str(row.get("drawing_locator") or "").strip()
            if chapter_present:
                calculated_mentioned += 1
            if bool(closure.get("ok")):
                calculated_closed += 1
            if chapter_present and requirement_status == "required" and not drawing_locator:
                calculated_missing_drawing += 1
            flags = row.get("flags") if isinstance(row.get("flags"), list) else []
            if chapter_present and "缺标准定位" in flags:
                calculated_missing_standard += 1
            if drawing_locator and validation.get("ok") is not True:
                raise ValueError("cross_index_drawing_locator_unvalidated")
            if bool(closure.get("ok")) and (
                requirement_status == "required" and not drawing_locator
            ):
                raise ValueError("cross_index_closed_without_required_drawing")

        if (
            calculated_mentioned != mentioned_count
            or calculated_closed != closed_count
            or calculated_missing_drawing != missing_drawing
            or calculated_missing_standard != missing_standard
        ):
            raise ValueError("cross_index_counter_row_mismatch")
    return value


def _pick_best_mention_section(
    *,
    name: str,
    process_name: str | None,
    categories: list[str],
    sections: list[dict[str, Any]],
    drawing_files: set[str],
    standard_files: set[str],
) -> tuple[str | None, list[str], str]:
    """
    Fallback when quality closure did not return hit sections:
    choose the section with strongest process/title relevance + nearby typed evidence.
    """
    best_title: str | None = None
    best_locs: list[str] = []
    best_score = -10**9
    for sec in sections or []:
        title = str(sec.get("title") or "").strip()
        text = str(sec.get("content") or "")
        if not name or not boq_focus_name_in_text(name, text):
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
    boq: dict[str, Any] | None,
    sections: list[dict[str, Any]] | None,
    boq_focus: dict[str, Any] | None = None,
    drawing_index: dict[str, Any] | None = None,
    standard_index: dict[str, Any] | None = None,
    quality_checks: dict[str, Any] | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    """
    Cross-index table for BoQ focus items:
    - item -> (metrics/categories/process) -> best chapter -> (drawing locator / standard locator) -> closure flags
    This is designed for traceability and fast review.
    """
    boq = boq if isinstance(boq, dict) else {}
    sections = sections if isinstance(sections, list) else []
    pid = str(project_id).strip() if isinstance(project_id, str) and project_id.strip() else None

    metrics_by_name, categories_by_name = _index_boq_stats(boq)
    raw_boq_items = boq.get("items") if isinstance(boq.get("items"), list) else []
    boq_items = [item for item in raw_boq_items if isinstance(item, dict)]

    focus_names = []
    if isinstance(boq_focus, dict):
        focus_names = normalize_boq_focus_items(
            boq_focus.get("must_cover_keywords") or [],
            limit=MAX_BOQ_FOCUS_ITEMS,
        )
    if not focus_names:
        # Fallback to stats-derived order if focus list is not available.
        focus_names = select_boq_focus_names(
            boq.get("stats") if isinstance(boq.get("stats"), dict) else {},
            limit=MAX_BOQ_FOCUS_ITEMS,
        )

    closure_map: dict[str, dict[str, Any]] = {}
    quality_root = quality_checks if isinstance(quality_checks, dict) else {}
    closure_root = quality_root.get("boq_focus_item_closure")
    closure_root = closure_root if isinstance(closure_root, dict) else {}
    closure_items = closure_root.get("items")
    closure_items = closure_items if isinstance(closure_items, list) else []
    for item in closure_items:
        if not isinstance(item, dict):
            continue
        name = normalize_boq_focus_name(item.get("item"))
        if name:
            closure_map[boq_focus_name_key(name)] = item

    draw_bind_by_chapter = _index_chapter_bindings(drawing_index)
    draw_bind_by_focus = _index_focus_drawing_bindings(boq_focus)
    std_loc_by_chapter = _index_chapter_locators(standard_index)

    drawing_project_id = str((drawing_index or {}).get("project_id") or "").strip()
    drawing_project_matches = not pid or (bool(drawing_project_id) and drawing_project_id == pid)
    drawing_catalog = _drawing_catalog(drawing_index) if drawing_project_matches else {}
    drawing_files: set[str] = set(drawing_catalog)

    standard_files: set[str] = set()
    standard_root = standard_index if isinstance(standard_index, dict) else {}
    standard_rows = standard_root.get("standards")
    standard_rows = standard_rows if isinstance(standard_rows, list) else []
    for row in standard_rows:
        if not isinstance(row, dict):
            continue
        filename = str(row.get("filename") or "").strip()
        if filename:
            standard_files.add(filename)

    has_standards = bool(standard_files)
    section_text_by_title: dict[str, str] = {}
    for sec in sections:
        title = str(sec.get("title") or "").strip()
        if not title or title in section_text_by_title:
            continue
        section_text_by_title[title] = str(sec.get("content") or "")

    focus_rows: list[dict[str, Any]] = []
    mentioned = 0
    closed_ok = 0
    missing_drawing = 0
    missing_standard = 0
    accepted_drawing_locator_claims: dict[str, list[str]] = {}

    for name in focus_names:
        # Metrics + categories
        m = dict(_lookup_normalized_name(metrics_by_name, name, {}) or {})
        cats = list(_lookup_normalized_name(categories_by_name, name, []) or [])

        # Process name (from BoQ items list)
        proc_name = None
        best_boq_item = _pick_best_boq_item(boq_items, name) or {}
        raw_process = best_boq_item.get("process")
        process = raw_process if isinstance(raw_process, dict) else {}
        proc_name = str(process.get("name") or "").strip() or None
        if "boq_code" not in m and best_boq_item.get("boq_code"):
            m["boq_code"] = best_boq_item.get("boq_code")

        # Closure + best chapter
        closure_item = closure_map.get(boq_focus_name_key(name)) or {}
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
        near_locs_prefill: list[str] = []
        selection_meta: dict[str, Any] = {}

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

        # Evidence locators. Drawing evidence is never trusted solely because
        # a chapter binding exists: the locator must resolve to the current
        # project's known file/hash/page and be relevant to this exact item or
        # process.
        drawing_requirement = _drawing_requirement_for(
            boq_focus,
            name,
            project_id=pid,
        )
        drawing_loc = None
        drawing_validation: dict[str, Any] = {
            "ok": False,
            "reason": "not_evaluated",
        }
        standard_loc = std_loc_by_chapter.get(chapter) if chapter else None

        # Extract evidence markers near the first mention in chapter content (best-effort).
        near_locs: list[str] = []
        if near_locs_prefill:
            near_locs = list(near_locs_prefill)
        elif chapter:
            for sec in sections:
                if str(sec.get("title") or "").strip() != chapter:
                    continue
                near_locs = _extract_evidence_locators_near(str(sec.get("content") or ""), name)
                break

        if drawing_requirement["status"] == "not_applicable":
            drawing_validation = {"ok": True, "reason": "not_applicable"}
        elif chapter:
            drawing_candidates: list[tuple[str, dict[str, Any] | None, str]] = []
            for binding in draw_bind_by_focus.get(boq_focus_name_key(name), []):
                locator = str(binding.get("locator") or "").strip()
                if locator:
                    drawing_candidates.append((locator, binding, "focus"))
            for binding in draw_bind_by_chapter.get(chapter, []):
                locator = str(binding.get("locator") or "").strip()
                if locator:
                    drawing_candidates.append((locator, binding, "chapter"))
            for locator in near_locs:
                if locator:
                    drawing_candidates.append((locator, None, "content"))

            rejected: list[dict[str, Any]] = []
            relevance_values: list[Any] = [name, proc_name, chapter]
            for locator, binding, candidate_source in drawing_candidates:
                if candidate_source == "focus" and isinstance(binding, dict):
                    relation_ok, relation_detail = _validate_focus_binding_relation(
                        binding,
                        name=name,
                        chapter=chapter,
                        project_id=pid,
                    )
                    if not relation_ok:
                        rejected.append({"locator": locator, **relation_detail})
                        continue
                valid, detail = _validate_drawing_locator(
                    locator,
                    catalog=drawing_catalog,
                    binding=binding,
                    relevance_values=relevance_values,
                )
                prior_claims = accepted_drawing_locator_claims.get(locator) or []
                if (
                    valid
                    and prior_claims
                    and not detail.get("matched_item_terms")
                    and not detail.get("matched_process_terms")
                ):
                    valid = False
                    detail = {
                        **detail,
                        "reason": "drawing_locator_shared_without_item_or_process_match",
                        "prior_claims": prior_claims[:8],
                    }
                if valid:
                    drawing_loc = locator
                    drawing_validation = {
                        "ok": True,
                        **detail,
                        "binding_basis": (
                            str((binding or {}).get("binding_basis") or "").strip()
                            or candidate_source
                        ),
                    }
                    accepted_drawing_locator_claims.setdefault(locator, []).append(name)
                    break
                rejected.append({"locator": locator, **detail})
            if drawing_loc is None:
                reason_code = "drawing_locator_missing"
                if not drawing_project_matches:
                    reason_code = "drawing_project_identity_mismatch"
                elif not drawing_catalog:
                    reason_code = "drawing_index_empty"
                elif rejected:
                    reason_code = str(rejected[0].get("reason") or "drawing_locator_invalid")
                drawing_validation = {
                    "ok": drawing_requirement["status"] == "optional",
                    "reason": reason_code,
                    "rejected": rejected[:4],
                }
        if chapter and not standard_loc and has_standards:
            standard_loc = _pick_locator_by_known_filenames(near_locs, standard_files) or None

        # Missing parts for readability
        missing_parts: list[str] = []
        if not chapter:
            missing_parts.append("未出现")
        else:
            if triplet_count <= 0:
                missing_parts.append("三元组")
            if (len(hit_keys) < 3) or (not has_units):
                missing_parts.append("量化")
            if evidence_count <= 0 and not near_locs:
                missing_parts.append("证据")

        flags: list[str] = []
        if chapter and drawing_requirement["status"] == "required" and not drawing_loc:
            missing_drawing += 1
            flags.append("缺图纸定位")
        if chapter and has_standards and not standard_loc:
            missing_standard += 1
            flags.append("缺标准定位")
        if missing_parts and missing_parts != ["未出现"]:
            flags.append("闭环缺口:" + ",".join(missing_parts))

        evidence_complete = (
            drawing_requirement["status"] != "required" or bool(drawing_loc)
        ) and (not has_standards or bool(standard_loc))
        overall_closure_ok = bool(closure_ok and evidence_complete)
        if overall_closure_ok:
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
                "drawing_requirement": drawing_requirement,
                "drawing_validation": drawing_validation,
                "standard_locator": standard_loc,
                "evidence_locators_near": near_locs,
                "closure": {
                    "ok": overall_closure_ok,
                    "content_ok": closure_ok,
                    "evidence_complete": evidence_complete,
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
