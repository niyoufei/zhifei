from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from backend.zhifei_autoplan.requirement_decisions import (
    build_requirement_decision_matrix,
    matrix_sources,
    style_from_requirement_matrix,
)


DEFAULT_STYLE: Dict[str, Any] = {
    "paper": "A4",
    "body_font": "宋体",
    "title_font": "宋体",
    "body_size": 14,   # 四号
    "title_size": 16,  # 三号
    "line_spacing_pt": 22.0,
    "margins_cm": {
        "top": 2.5,
        "right": 2.0,
        "bottom": 2.0,
        "left": 2.0,
    },
    # Behavioral layout flags are kept here as explicit safe defaults so they
    # survive style resolution just like fonts, spacing and margins.
    "chapter_start_new_page": False,
    "enforce_chapter_pages": False,
    "chart_policy": {
        "enabled": True,
        "mode": "page_density_auto",
        "every_n_chapters": 2,
        "position": "chapter",
    },
}


def _merge_dict(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a or {})
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            child = dict(out.get(k) or {})
            child.update(v)
            out[k] = child
        else:
            out[k] = v
    return out


def _merge_style_layer(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Merge one style layer while keeping the two line-spacing modes exclusive."""
    out = _merge_dict(base, override)
    if "line_spacing_pt" in override:
        out.pop("line_spacing", None)
    elif "line_spacing" in override:
        out.pop("line_spacing_pt", None)
    return out


def _to_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _to_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return bool(v)
    text = str(v).strip().lower()
    if text in {"1", "true", "yes", "on", "是", "启用"}:
        return True
    if text in {"0", "false", "no", "off", "否", "禁用"}:
        return False
    return default


def normalize_cn_font_name(v: Any) -> str:
    s = str(v or "").strip()
    if not s:
        return ""
    if s in {"SimSun", "宋体"}:
        return "宋体"
    if s in {"仿宋", "仿宋体", "FangSong"}:
        return "仿宋体"
    return s


def has_explicit_style(style: Dict[str, Any] | None) -> bool:
    if not isinstance(style, dict) or not style:
        return False
    keys = {
        "body_font",
        "title_font",
        "body_size",
        "title_size",
        "line_spacing",
        "line_spacing_pt",
        "margins_cm",
        "font",
        "chapter_start_new_page",
        "enforce_chapter_pages",
    }
    return any(k in style for k in keys)


def normalize_style_input(style: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = style if isinstance(style, dict) else {}
    out: Dict[str, Any] = {}
    font_cfg = raw.get("font") if isinstance(raw.get("font"), dict) else {}

    body_font = normalize_cn_font_name(raw.get("body_font") or font_cfg.get("eastAsia") or raw.get("font"))
    title_font = normalize_cn_font_name(raw.get("title_font") or body_font)
    if body_font:
        out["body_font"] = body_font
    if title_font:
        out["title_font"] = title_font

    body_size = raw.get("body_size") or raw.get("font_size") or font_cfg.get("size_pt")
    title_size = raw.get("title_size")
    if body_size is not None:
        out["body_size"] = max(9.0, min(24.0, _to_float(body_size, 14.0)))
    if title_size is not None:
        out["title_size"] = max(10.0, min(36.0, _to_float(title_size, 16.0)))

    if raw.get("line_spacing_pt") is not None or font_cfg.get("line_spacing_pt") is not None:
        out["line_spacing_pt"] = max(10.0, min(60.0, _to_float(raw.get("line_spacing_pt") or font_cfg.get("line_spacing_pt"), 22.0)))
    elif raw.get("line_spacing") is not None or font_cfg.get("line_spacing") is not None:
        out["line_spacing"] = max(1.0, min(3.0, _to_float(raw.get("line_spacing") or font_cfg.get("line_spacing"), 1.5)))

    margins = raw.get("margins_cm") if isinstance(raw.get("margins_cm"), dict) else {}
    if margins:
        out["margins_cm"] = {
            "top": max(0.5, _to_float(margins.get("top"), DEFAULT_STYLE["margins_cm"]["top"])),
            "right": max(0.5, _to_float(margins.get("right"), DEFAULT_STYLE["margins_cm"]["right"])),
            "bottom": max(0.5, _to_float(margins.get("bottom"), DEFAULT_STYLE["margins_cm"]["bottom"])),
            "left": max(0.5, _to_float(margins.get("left"), DEFAULT_STYLE["margins_cm"]["left"])),
        }
    if raw.get("paper"):
        out["paper"] = str(raw.get("paper"))
    if raw.get("chapter_start_new_page") is not None:
        out["chapter_start_new_page"] = _to_bool(raw.get("chapter_start_new_page"), False)
    if raw.get("enforce_chapter_pages") is not None:
        # Backward-compatible key; its current meaning is content enrichment,
        # never mechanical insertion of page breaks.
        out["enforce_chapter_pages"] = _to_bool(raw.get("enforce_chapter_pages"), False)
    if isinstance(raw.get("chart_policy"), dict):
        out["chart_policy"] = dict(raw.get("chart_policy") or {})
    return out


def resolve_line_spacing(
    style: Dict[str, Any] | None,
    *,
    default_pt: float = 22.0,
) -> Tuple[float, float | None]:
    """Return (multiple, fixed_pt) with fixed and multiple modes kept exclusive."""
    raw = style if isinstance(style, dict) else {}
    font_cfg = raw.get("font") if isinstance(raw.get("font"), dict) else {}
    multiple_raw = raw.get("line_spacing")
    if multiple_raw is None:
        multiple_raw = font_cfg.get("line_spacing")
    fixed_raw = raw.get("line_spacing_pt")
    if fixed_raw is None:
        fixed_raw = font_cfg.get("line_spacing_pt")

    multiple = max(1.0, min(3.0, _to_float(multiple_raw, 1.5)))
    if fixed_raw is not None:
        fixed_pt = max(10.0, min(60.0, _to_float(fixed_raw, default_pt)))
        return multiple, fixed_pt
    if multiple_raw is not None:
        return multiple, None
    return multiple, max(10.0, min(60.0, _to_float(default_pt, 22.0)))


def resolve_style(
    *,
    user_style: Dict[str, Any] | None,
    tender_style: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], str]:
    """
    招标样式优先，用户样式次之，最后走默认值。
    """
    base = normalize_style_input(DEFAULT_STYLE)
    merged = _merge_style_layer(base, normalize_style_input(user_style))
    src = "default_or_user"
    if has_explicit_style(tender_style):
        merged = _merge_style_layer(merged, normalize_style_input(tender_style))
        src = "tender_override"
    return merged, src


def resolve_style_with_decisions(
    *,
    user_style: Dict[str, Any] | None,
    tender_style: Dict[str, Any] | None,
    tender_decision_matrix: Mapping[str, Any] | None = None,
    approved_resolutions: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], str, Dict[str, Any]]:
    """Resolve style and return the complete field-level provenance receipt."""
    sources = [
        {
            "source_id": "system_default",
            "source_type": "system_default",
            "priority": 100,
            "confidence": 1.0,
            "values": normalize_style_input(DEFAULT_STYLE),
            "evidence": {"kind": "built_in_policy"},
        }
    ]
    normalized_user = normalize_style_input(user_style)
    if normalized_user:
        sources.append(
            {
                "source_id": "user_configuration",
                "source_type": "user",
                "priority": 200,
                "confidence": 1.0,
                "values": normalized_user,
                "evidence": {"kind": "generation_request"},
            }
        )
    tender_sources = matrix_sources(tender_decision_matrix)
    if tender_sources:
        sources.extend(tender_sources)
    else:
        normalized_tender = normalize_style_input(tender_style)
        if normalized_tender:
            sources.append(
                {
                    "source_id": "tender_aggregate",
                    "source_type": "tender",
                    "priority": 300,
                    "confidence": 0.85,
                    "values": normalized_tender,
                    "evidence": {"kind": "legacy_tender_matrix"},
                }
            )
    normalized_approved = normalize_style_input(approved_resolutions)
    if normalized_approved:
        sources.append(
            {
                "source_id": "approved_resolution",
                "source_type": "approved_resolution",
                "priority": 500,
                "confidence": 1.0,
                "values": normalized_approved,
                "evidence": {"kind": "explicit_human_resolution"},
            }
        )
    matrix = build_requirement_decision_matrix(sources)
    resolved = style_from_requirement_matrix(matrix)
    has_tender = any(str(item.get("source_type")) in {"tender", "clarification"} for item in sources)
    source = "tender_override" if has_tender else "default_or_user"
    return resolved, source, matrix
