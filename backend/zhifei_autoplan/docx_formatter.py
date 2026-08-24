from __future__ import annotations

import re
from typing import Any, Dict

from backend.zhifei_autoplan.style_policy import normalize_cn_font_name


DEFAULT_FORMAT_CONFIG: Dict[str, Any] = {
    "body_font": "宋体",
    "title_font": "黑体",
    "body_size_pt": 14.0,
    "title_size_pt": 16.0,
    "line_spacing_pt": 22.0,
    "margins_cm": {
        "top": 2.5,
        "right": 2.0,
        "bottom": 2.0,
        "left": 2.0,
    },
    "cover_page_count": 1,
    "toc_page_count": 2,
    "front_matter_page_mode": "include",
}

_EVIDENCE_TAG_RE = re.compile(r"【证据:(.+?)】")
_INTERNAL_TAG_RE = re.compile(r"【(?:图谱节点|经验值|图谱经验值):[^】]+】")
_WRAPPED_LABEL_RE = re.compile(r"^【([^】]{1,60})】[:：]?\s*")
_KV_TOKEN_RE = re.compile(r"([^=：:；;，,\s]{1,20})\s*(?:=|：|:)\s*([^；;，,\n]+)")
_RISK_ROW_RE = re.compile(
    r"(?:^[-*•]?\s*)?风险[:：]\s*(?P<risk>.+?)\s*[；;]\s*控制[:：]\s*(?P<control>.+?)\s*[；;]\s*验证[:：]\s*(?P<verify>.+)$"
)

_SYSTEM_ONLY_LABELS = {
    "系统全局指令",
    "系统全局指令（必须无条件执行）",
    "图谱节点绑定",
    "图谱逻辑节点（必须绑定）",
    "证据摘要",
    "证据与追溯",
    "编制要求",
    "章节结构蓝图",
    "合规检查要点",
    "文风硬约束（必须）",
}
_TABLE_ONLY_LABELS = {
    "风险→控制→验证",
    "风险-控制-验证",
    "风险控制验证表",
    "资源-工序耦合表",
    "资源-工序耦合",
}
_SCAFFOLD_LINE_PATTERNS = [
    re.compile(r"^\s*角色定位[:：]"),
    re.compile(r"^\s*章节标题[:：]"),
    re.compile(r"^\s*方案版本[:：]"),
    re.compile(r"^\s*输出要求[:：]"),
    re.compile(r"^\s*provider\s*[:=]", re.IGNORECASE),
    re.compile(r"^\s*model\s*[:=]", re.IGNORECASE),
]


def _normalize_docx_font_name(value: Any) -> str:
    raw = str(value or "").strip()
    aliases = {
        "宋": "宋体",
        "黑": "黑体",
        "楷": "楷体",
        "仿宋": "仿宋体",
        "fangsong": "仿宋体",
        "simsun": "宋体",
    }
    return aliases.get(raw.lower(), aliases.get(raw, normalize_cn_font_name(raw)))


def _style_scalar(style: Dict[str, Any], key: str, nested_key: str | None = None) -> Any:
    if style.get(key) is not None:
        return style.get(key)
    if nested_key and isinstance(style.get("font"), dict) and style["font"].get(nested_key) is not None:
        return style["font"].get(nested_key)
    return None


def build_bidding_format_config_from_style(style: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = style if isinstance(style, dict) else {}
    font_cfg = raw.get("font") if isinstance(raw.get("font"), dict) else {}
    headings_cfg = raw.get("headings") if isinstance(raw.get("headings"), dict) else {}
    margins_cfg = raw.get("margins_cm") if isinstance(raw.get("margins_cm"), dict) else {}
    margins_list = raw.get("margins") if isinstance(raw.get("margins"), list) else []

    def _margin_value(name: str, index: int) -> Any:
        if margins_cfg.get(name) is not None:
            return margins_cfg.get(name)
        if index < len(margins_list):
            return margins_list[index]
        return None

    body_font = raw.get("body_font") or (raw.get("font") if isinstance(raw.get("font"), str) else None) or font_cfg.get("eastAsia")
    title_font = raw.get("title_font") or headings_cfg.get("eastAsia")
    return {
        "body_font": _normalize_docx_font_name(body_font) or None,
        "title_font": _normalize_docx_font_name(title_font) or None,
        "body_size_pt": raw.get("body_size") or raw.get("font_size") or font_cfg.get("size_pt"),
        "title_size_pt": raw.get("title_size") or headings_cfg.get("h2_size") or headings_cfg.get("h1_size"),
        "line_spacing_pt": raw.get("line_spacing_pt") or font_cfg.get("line_spacing_pt"),
        "line_spacing": raw.get("line_spacing") or font_cfg.get("line_spacing"),
        "margins_cm": {
            "top": _margin_value("top", 0),
            "right": _margin_value("right", 1),
            "bottom": _margin_value("bottom", 2),
            "left": _margin_value("left", 3),
        },
        "cover_page_count": raw.get("cover_page_count"),
        "toc_page_count": raw.get("toc_page_count"),
        "front_matter_page_mode": raw.get("front_matter_page_mode"),
        "document_total_pages_target": raw.get("document_total_pages_target"),
    }


def merge_style_with_bidding_fallback(
    *,
    user_style: Dict[str, Any] | None,
    bidding_format_config: Dict[str, Any] | None,
) -> Dict[str, Any]:
    user = user_style if isinstance(user_style, dict) else {}
    bidding = bidding_format_config if isinstance(bidding_format_config, dict) else {}
    merged = dict(user)

    bidding_body_font = _normalize_docx_font_name(bidding.get("body_font"))
    bidding_title_font = _normalize_docx_font_name(bidding.get("title_font"))
    user_body_font = _normalize_docx_font_name(_style_scalar(user, "body_font", "eastAsia"))
    user_title_font = _normalize_docx_font_name(user.get("title_font"))
    merged["body_font"] = bidding_body_font or user_body_font or DEFAULT_FORMAT_CONFIG["body_font"]
    merged["title_font"] = bidding_title_font or user_title_font or DEFAULT_FORMAT_CONFIG["title_font"]
    merged["body_size"] = (
        bidding.get("body_size_pt")
        or user.get("body_size")
        or user.get("font_size")
        or DEFAULT_FORMAT_CONFIG["body_size_pt"]
    )
    merged["title_size"] = bidding.get("title_size_pt") or user.get("title_size") or DEFAULT_FORMAT_CONFIG["title_size_pt"]
    if bidding.get("line_spacing_pt") is not None:
        merged["line_spacing_pt"] = bidding["line_spacing_pt"]
        merged.pop("line_spacing", None)
    elif bidding.get("line_spacing") is not None:
        merged["line_spacing"] = bidding["line_spacing"]
        merged.pop("line_spacing_pt", None)
    elif user.get("line_spacing_pt") is not None:
        merged["line_spacing_pt"] = user["line_spacing_pt"]
        merged.pop("line_spacing", None)
    elif user.get("line_spacing") is not None:
        merged["line_spacing"] = user["line_spacing"]
        merged.pop("line_spacing_pt", None)
    else:
        merged["line_spacing_pt"] = DEFAULT_FORMAT_CONFIG["line_spacing_pt"]
        merged.pop("line_spacing", None)

    merged_margins = dict(DEFAULT_FORMAT_CONFIG["margins_cm"])
    if isinstance(user.get("margins_cm"), dict):
        for key, value in user["margins_cm"].items():
            if value is not None:
                merged_margins[key] = value
    if isinstance(bidding.get("margins_cm"), dict):
        for key, value in bidding["margins_cm"].items():
            if value is not None:
                merged_margins[key] = value
    merged["margins_cm"] = merged_margins

    for key in ("cover_page_count", "toc_page_count", "front_matter_page_mode", "document_total_pages_target"):
        if bidding.get(key) is not None:
            merged[key] = bidding.get(key)
        elif user.get(key) is not None:
            merged[key] = user.get(key)
        elif key in DEFAULT_FORMAT_CONFIG:
            merged[key] = DEFAULT_FORMAT_CONFIG[key]
    return merged


def _strip_wrapped_label(line: str) -> tuple[str, str]:
    match = _WRAPPED_LABEL_RE.match(str(line or "").strip())
    if not match:
        return "", str(line or "").strip()
    return match.group(1).strip(), str(line or "").strip()[match.end():].strip()


def is_system_scaffold_line(line: str) -> bool:
    raw = str(line or "").strip()
    if not raw:
        return False
    label, _ = _strip_wrapped_label(raw)
    if label.lower() in {x.lower() for x in _SYSTEM_ONLY_LABELS}:
        return True
    if raw.startswith("【系统") or raw.startswith("【图谱") or raw.startswith("【证据摘要】"):
        return True
    if raw.startswith("{") and raw.endswith("}"):
        return True
    return any(pattern.search(raw) for pattern in _SCAFFOLD_LINE_PATTERNS)


def _normalize_threshold(value: str) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^偏差\s*[≤<=]*\s*", "", text)
    return text


def naturalize_machine_text(text: str) -> str:
    raw = str(text or "").strip()
    label, rest = _strip_wrapped_label(raw)
    if label and rest:
        raw = rest
    parts: list[str] = []
    for key, value in _KV_TOKEN_RE.findall(raw):
        k = str(key or "").strip()
        v = str(value or "").strip()
        if not k or not v:
            continue
        if k in {"频次", "抽检频次"}:
            parts.append(f"巡检频次控制为{v}")
        elif k in {"阈值", "偏差"}:
            parts.append(f"关键偏差控制在{_normalize_threshold(v)}以内")
        elif k in {"人数", "班组人数"}:
            parts.append(f"现场安排{v}组织施工")
        elif k in {"设备", "设备型号", "机械"}:
            parts.append(f"配置{v}")
        elif k in {"时长", "节拍"}:
            parts.append(f"作业节拍控制为{v}")
        else:
            parts.append(f"{k}为{v}")
    if parts:
        return "；".join(parts) + "。"
    return raw


def sanitize_delivery_line(line: str) -> Dict[str, Any]:
    raw = str(line or "").strip()
    anchors = [str(item).strip() for item in _EVIDENCE_TAG_RE.findall(raw) if str(item).strip()]
    if is_system_scaffold_line(raw):
        return {"visible": "", "anchors": anchors, "stripped": True}
    visible = _EVIDENCE_TAG_RE.sub("", raw)
    visible = _INTERNAL_TAG_RE.sub("", visible)
    visible = re.sub(r"\s+", " ", visible).strip()
    visible = re.sub(r"\s+([。；;，,])", r"\1", visible)
    return {"visible": visible, "anchors": anchors, "stripped": False}


def _parse_kv_map(line: str) -> dict[str, str]:
    return {str(k).strip(): str(v).strip() for k, v in _KV_TOKEN_RE.findall(str(line or "")) if str(k).strip()}


def prepare_delivery_render(text: str) -> Dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    current_table: str | None = None
    for raw_line in str(text or "").splitlines():
        raw = raw_line.strip()
        if not raw:
            continue
        label, rest = _strip_wrapped_label(raw)
        if label in {"风险→控制→验证", "风险-控制-验证", "风险控制验证表"}:
            current_table = "risk"
            if not rest:
                continue
            raw = rest
        elif label in {"资源-工序耦合表", "资源-工序耦合"}:
            current_table = "resource"
            if not rest:
                continue
            raw = rest

        item = sanitize_delivery_line(raw)
        if item.get("stripped") or not item.get("visible"):
            continue
        visible = str(item.get("visible") or "")
        anchors = item.get("anchors") or []

        risk_match = _RISK_ROW_RE.match(visible)
        if current_table == "risk" or risk_match:
            if not risk_match:
                continue
            blocks.append(
                {
                    "type": "table",
                    "headers": ["风险源", "控制措施", "验证方式"],
                    "rows": [[risk_match.group("risk").strip(), risk_match.group("control").strip(), risk_match.group("verify").strip()]],
                    "anchors": anchors,
                }
            )
            continue

        if current_table == "resource":
            kv = _parse_kv_map(visible)
            if not kv:
                continue
            resource_values = [kv.get("班组人数") or kv.get("人数"), kv.get("设备") or kv.get("设备型号") or kv.get("机械")]
            control_values = [kv.get("节拍"), kv.get("频次"), kv.get("阈值")]
            blocks.append(
                {
                    "type": "table",
                    "headers": ["工序", "资源配置", "控制要求"],
                    "rows": [
                        [
                            kv.get("工序") or "",
                            "；".join([x for x in resource_values if x]),
                            "；".join([x for x in control_values if x]),
                        ]
                    ],
                    "anchors": anchors,
                }
            )
            continue

        blocks.append({"type": "paragraph", "text": naturalize_machine_text(visible), "anchors": anchors})
    return {"blocks": blocks}
