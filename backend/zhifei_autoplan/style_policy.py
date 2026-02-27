from __future__ import annotations

from typing import Any, Dict, Tuple


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
    "chart_policy": {
        "enabled": True,
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


def _to_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
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
    keys = {"body_font", "title_font", "body_size", "title_size", "line_spacing", "line_spacing_pt", "margins_cm", "font"}
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
    if isinstance(raw.get("chart_policy"), dict):
        out["chart_policy"] = dict(raw.get("chart_policy") or {})
    return out


def resolve_style(
    *,
    user_style: Dict[str, Any] | None,
    tender_style: Dict[str, Any] | None,
) -> Tuple[Dict[str, Any], str]:
    """
    招标样式优先，用户样式次之，最后走默认值。
    """
    base = normalize_style_input(DEFAULT_STYLE)
    merged = _merge_dict(base, normalize_style_input(user_style))
    src = "default_or_user"
    if has_explicit_style(tender_style):
        merged = _merge_dict(merged, normalize_style_input(tender_style))
        src = "tender_override"
    return merged, src

