from __future__ import annotations

import re
from typing import Any

from backend.zhifei_autoplan.boq_focus_policy import (
    MAX_BOQ_FOCUS_ITEMS,
    boq_focus_name_in_text,
    boq_focus_name_key,
    find_boq_focus_name_spans,
    normalize_boq_focus_items,
    normalize_boq_focus_name,
)
from backend.zhifei_autoplan.evidence import best_drawing_hit, best_ingested_hit
from backend.zhifei_autoplan.project_fact_ledger import (
    FORMAL_ACCEPTED_STATUSES,
    validate_project_fact_ledger,
)

_FOCUS_ITEM_LINE_RE = re.compile(
    r"^\-\s*(?P<name>[^/]+?)\s*(?:/\s*工程量=(?P<qty>[^/]+?))?\s*(?:/\s*单价=(?P<unit_price>[^/]+?))?\s*(?:/\s*合价=(?P<total_price>[^/]+?))?\s*$"
)
_HAN_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_STOP_TOKENS = {
    "工程",
    "施工",
    "材料",
    "管理",
    "措施",
    "技术",
    "要求",
    "项目",
    "作业",
    "方案",
    "工序",
    "质量",
    "安全",
    "进度",
    "环保",
}
_EVIDENCE_SRC_RE = re.compile(r"【证据:(?P<src>[^】]{2,200})】")
_FULL_DRAWING_LOCATOR_RE = re.compile(
    r"^(?P<filename>.+)#p(?P<page>[1-9]\d*)_(?P<sha256>[0-9a-fA-F]{64})@(?P<offset>\d+)$"
)
_DRAWING_LOCATOR_LINE_RE = re.compile(
    r"(?m)^(?P<indent>[ \t]*)图纸定位：[^\r\n]*(?P<newline>\r?\n|$)"
)
_HAZARDOUS_MATERIAL_BASELINE_MARKER = "【危险品材料统一管理基线】"
_PENDING_QUANT_CONTROLS = {
    "频次": "待依据经批准项目制度确认",
    "阈值": "待按图纸及适用规范逐工序确认",
    "间距": "待按图纸定位逐项确认",
    "厚度": "待按图纸做法逐项确认",
    "时长": "待依据经批准施工方案确认",
    "人数": "待依据经批准资源计划确认",
    "设备型号": "待依据经批准机械配置确认",
    "偏差处置时限": "待依据经批准项目制度确认",
}


def _format_fact_value(fact: dict[str, Any]) -> str:
    value = str(fact.get("value") or "").strip()
    unit = str(fact.get("unit") or "").strip()
    if value and unit and not value.endswith(unit):
        value = f"{value}{unit}"
    evidence = fact.get("evidence") if isinstance(fact.get("evidence"), dict) else {}
    locator = str(evidence.get("locator") or "").strip()
    return f"{value}【证据:{locator}】" if value and locator else value


def _without_evidence_annotations(value: Any) -> str:
    return _EVIDENCE_SRC_RE.sub("", str(value or "")).strip()


def _source_bound_quant_controls(
    project_fact_ledger: dict[str, Any] | None,
    *,
    focus_item: str = "",
    process_hint: str = "",
) -> dict[str, str]:
    """Use only formally accepted project facts; never promote registry defaults."""

    controls = dict(_PENDING_QUANT_CONTROLS)
    if not isinstance(project_fact_ledger, dict):
        return controls
    if not validate_project_fact_ledger(project_fact_ledger).get("ok"):
        return controls
    facts = (
        project_fact_ledger.get("facts")
        if isinstance(project_fact_ledger.get("facts"), dict)
        else {}
    )
    bindings = {
        "risk_inspection_frequency": "频次",
        "deviation_action_deadline": "偏差处置时限",
    }
    for field, label in bindings.items():
        fact = facts.get(field)
        if not isinstance(fact, dict):
            continue
        if str(fact.get("status") or "").strip() not in FORMAL_ACCEPTED_STATUSES:
            continue
        rendered = _format_fact_value(fact)
        if rendered:
            controls[label] = rendered

    quality_fact = facts.get("quality_threshold")
    if not isinstance(quality_fact, dict):
        return controls
    if str(quality_fact.get("status") or "").strip() not in FORMAL_ACCEPTED_STATUSES:
        return controls
    bundle = quality_fact.get("value")
    if (
        not isinstance(bundle, dict)
        or str(bundle.get("mode") or "").strip().lower() != "process_bound"
    ):
        return controls
    target_keys = {
        key
        for key in (
            boq_focus_name_key(focus_item),
            boq_focus_name_key(process_hint),
        )
        if key
    }
    if not target_keys:
        return controls
    rendered_thresholds: list[str] = []
    rows = bundle.get("items") if isinstance(bundle.get("items"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "").strip() not in FORMAL_ACCEPTED_STATUSES:
            continue
        if boq_focus_name_key(row.get("process")) not in target_keys:
            continue
        source = str(row.get("source") or "").strip()
        locator = str(row.get("locator") or "").strip()
        metric = str(row.get("metric") or "").strip()
        operator = str(row.get("operator") or "").strip()
        value = row.get("value")
        value_text = "" if value is None else str(value).strip()
        unit = str(row.get("unit") or "").strip()
        if not source or not locator or not metric or not operator or not value_text:
            continue
        rendered_thresholds.append(
            f"{metric}{operator}{value_text}{unit}【证据:{locator}】"
        )
    if rendered_thresholds:
        controls["阈值"] = "；".join(dict.fromkeys(rendered_thresholds))
    return controls


def _parse_focus_lines(lines: list[str]) -> dict[str, dict[str, str]]:
    """
    Parse `boq_focus["lines"]` which contains mixed headers and "- item / 工程量=... / 单价=... / 合价=..."
    Returns a map keyed by the canonical item name so line-wrapped/NFKC
    variants still attach their quantities to the right generated card.
    """
    out: dict[str, dict[str, str]] = {}
    for ln in lines or []:
        s = str(ln or "").strip()
        if not s.startswith("- "):
            continue
        body = s[2:].strip()
        m = _FOCUS_ITEM_LINE_RE.match(s)
        if m:
            name = normalize_boq_focus_name(m.group("name"))
            key = boq_focus_name_key(name)
            if not name or not key:
                continue
            out[key] = {
                "name": name,
                "qty": (m.group("qty") or "").strip(),
                "unit_price": (m.group("unit_price") or "").strip(),
                "total_price": (m.group("total_price") or "").strip(),
                "raw": body,
            }
            continue
        # Fallback: name is left part
        name = normalize_boq_focus_name(body.split(" / ", 1)[0])
        key = boq_focus_name_key(name)
        if name and key:
            out.setdefault(key, {"name": name, "raw": body})
    return out


def _pick_host_section_index(sections: list[dict[str, Any]]) -> int:
    """
    Choose a section to host focus item control cards without changing the tender-derived outline.
    Heuristic: prefer '施工方案/施工方法/技术措施/施工部署/资源' chapters.
    """
    if not sections:
        return 0
    prefer_keys = ["施工方案", "施工方法", "主要施工", "技术措施", "施工工艺", "施工部署", "资源", "材料", "设备"]
    for i, sec in enumerate(sections):
        t = str(sec.get("title") or "")
        if any(k in t for k in prefer_keys):
            return i
    return 0


def _has_closed_loop_triplet(text: str) -> bool:
    return ("风险" in text) and (("控制" in text) or ("措施" in text)) and ("验证" in text)


def _has_quant_metrics(text: str) -> bool:
    # Lightweight: the quality gate will do strict checks; here we just avoid duplicating blocks.
    return any(k in text for k in ("频次", "阈值", "间距", "厚度", "时长", "人数", "设备型号"))


def _extract_evidence_sources(text: str) -> list[str]:
    out: list[str] = []
    for m in _EVIDENCE_SRC_RE.finditer(text or ""):
        src = str(m.group("src") or "").strip()
        if not src:
            continue
        out.append(src)
    return out


def _evidence_has_any(text: str, names_set: set[str]) -> bool:
    if not names_set:
        return False
    for src in _extract_evidence_sources(text or ""):
        base = src.split("#", 1)[0].strip() if "#" in src else src.strip()
        if base in names_set:
            return True
    return False


def _focus_drawing_binding_from_hit(
    hit: dict[str, Any] | None,
    *,
    focus_item: str,
    chapter: str,
    project_id: str,
) -> dict[str, Any] | None:
    """Preserve the reversible hit contract for the formal cross-index gate."""

    if not isinstance(hit, dict):
        return None
    locator = str(hit.get("locator") or "").strip()
    match = _FULL_DRAWING_LOCATOR_RE.fullmatch(locator)
    if not match:
        return None
    filename = str(hit.get("filename") or "").strip()
    sha256 = str(hit.get("sha256") or "").strip().lower()
    try:
        page = int(hit.get("page"))
        offset = int(hit.get("offset"))
    except (TypeError, ValueError):
        return None
    if (
        filename != str(match.group("filename") or "").strip()
        or sha256 != str(match.group("sha256") or "").lower()
        or page != int(match.group("page"))
        or offset != int(match.group("offset"))
        or not str(hit.get("page_boundary_status") or "").startswith("reliable_")
        or not isinstance(hit.get("match_window"), dict)
    ):
        return None

    normalized_item = normalize_boq_focus_name(focus_item)
    normalized_chapter = str(chapter or "").strip()
    normalized_project = str(project_id or "").strip()
    if not normalized_item or not normalized_chapter or not normalized_project:
        return None
    return {
        "focus_item": normalized_item,
        "chapter": normalized_chapter,
        "project_id": normalized_project,
        "locator": locator,
        "filename": filename,
        "sha256": sha256,
        "page": page,
        "offset": offset,
        "snippet": hit.get("snippet"),
        "matched_token": hit.get("matched_token"),
        "matched_text": hit.get("matched_text"),
        "match_start": hit.get("match_start"),
        "match_end": hit.get("match_end"),
        "match_window": dict(hit.get("match_window") or {}),
        "page_text_sha256": hit.get("page_text_sha256"),
        "page_summary": hit.get("page_summary"),
        "page_boundary_status": hit.get("page_boundary_status"),
        "binding_basis": "focus_item_specific_extract_hit",
        "source_relation": {
            "type": "boq_focus_item_drawing",
            "focus_item": normalized_item,
            "chapter": normalized_chapter,
            "project_id": normalized_project,
        },
    }


def _item_is_closed_in_text(name: str, text: str, window: int = 420, max_mentions: int = 10) -> bool:
    """
    Determine whether an item is already "closed" in a section without duplicating cards.
    Scan multiple mentions because the first mention may be outside the control-card block.
    """
    source_text = text or ""
    spans = find_boq_focus_name_spans(name, source_text, limit=max_mentions)
    for pos, match_end in spans:
        start = max(0, pos - window)
        end = min(len(source_text), match_end + window)
        snippet = source_text[start:end]
        if _has_closed_loop_triplet(snippet) and _has_quant_metrics(snippet) and ("【证据:" in snippet):
            return True
    return False


def _item_is_closed_with_typed_evidence(
    name: str,
    text: str,
    *,
    drawing_names: list[str] | None = None,
    standard_names: list[str] | None = None,
    window: int = 520,
) -> bool:
    """
    Stricter closure for focus items when a project has drawings/standards:
    - base closure (triplet + quant keys + evidence marker)
    - if drawings exist: require at least 1 drawing evidence source near the item
    - if standards exist: require at least 1 standard evidence source near the item
    """
    source_text = text or ""
    dset = {str(x).strip() for x in (drawing_names or []) if str(x).strip()}
    sset = {str(x).strip() for x in (standard_names or []) if str(x).strip()}
    for pos, match_end in find_boq_focus_name_spans(name, source_text, limit=10):
        start = max(0, pos - window)
        end = min(len(source_text), match_end + window)
        snippet = source_text[start:end]
        if not (_has_closed_loop_triplet(snippet) and _has_quant_metrics(snippet) and ("【证据:" in snippet)):
            continue
        if dset and (not _evidence_has_any(snippet, dset)):
            continue
        if sset and (not _evidence_has_any(snippet, sset)):
            continue
        return True
    return False


def _tokenize_item_name(name: str) -> list[str]:
    """
    Extract stable tokens from a BoQ item name for title matching.
    - Prefer longer Chinese sequences; fall back to the full name.
    """
    s = str(name or "").strip()
    if not s:
        return []
    base = [t for t in _HAN_TOKEN_RE.findall(s) if t and len(t) >= 2]
    toks: set[str] = set()
    for t in base:
        toks.add(t)
        # Add short keywords for chapter-title matching (e.g. 防水卷材 -> 防水, 卷材)
        if len(t) >= 4:
            toks.add(t[:2])
            toks.add(t[1:3])
            toks.add(t[-2:])
        if len(t) >= 6:
            toks.add(t[:3])
            toks.add(t[-3:])
    out = sorted(toks, key=lambda x: (-len(x), x))
    return out[:8] if out else [s]


def _tokenize_snippet(snippet: str) -> list[str]:
    s = str(snippet or "").strip()
    if not s:
        return []
    toks: set[str] = set()
    for t in _HAN_TOKEN_RE.findall(s):
        tt = t.strip()
        if len(tt) < 2 or tt in _STOP_TOKENS:
            continue
        toks.add(tt)
        if len(tt) >= 4:
            toks.add(tt[:2])
            toks.add(tt[-2:])
    out = sorted(toks, key=lambda x: (-len(x), x))
    return out[:10]


def _pick_section_for_item(
    name: str,
    sections: list[dict[str, Any]],
    host_idx: int,
    hint_snippet: str = "",
    process_hint: str = "",
) -> int:
    """
    Choose the best section to place the item's control card without changing the tender-derived outline:
    1) Exact mention in title
    2) Mention in content (place near where it is discussed)
    3) Token match in title (heuristic), optionally boosted by evidence snippet tokens
    4) Host fallback
    """
    sname = normalize_boq_focus_name(name)
    if not sections:
        return 0

    for i, sec in enumerate(sections):
        title = str(sec.get("title") or "")
        if sname and boq_focus_name_in_text(sname, title):
            return i

    for i, sec in enumerate(sections):
        text = str(sec.get("content") or "")
        if sname and boq_focus_name_in_text(sname, text):
            return i

    tokens = _tokenize_item_name(sname)
    hint_tokens = _tokenize_snippet(hint_snippet)
    proc_tokens = _tokenize_item_name(process_hint) if process_hint else []
    prefer_keys = ["施工方案", "施工方法", "主要施工", "技术措施", "施工工艺", "施工部署", "资源", "材料", "设备"]
    best_i = host_idx
    best_score = 0.0
    for i, sec in enumerate(sections):
        title = str(sec.get("title") or "")
        score = float(sum(1 for t in tokens if t in title))
        score += float(sum(0.3 for t in hint_tokens if t in title))
        # Process names are usually a more stable "host chapter" signal than raw item names.
        score += float(sum(1.2 for t in proc_tokens if t in title))
        if any(k in title for k in prefer_keys):
            score += 0.5
        if score > best_score:
            best_score = score
            best_i = i
    return best_i


def _build_focus_card(
    item: dict[str, str],
    evidence_src: str,
    quant: dict[str, str],
    drawing_locator: str | None = None,
    standard_locator: str | None = None,
    categories: list[str] | None = None,
    process_hint: str | None = None,
) -> str:
    name = item.get("name") or ""
    qty = item.get("qty") or ""
    unit_price = item.get("unit_price") or ""
    total_price = item.get("total_price") or ""

    parts = [f"清单项：{name}"]
    if qty:
        parts.append(f"工程量={qty}")
    if unit_price:
        parts.append(f"单价={unit_price}")
    if total_price:
        parts.append(f"合价={total_price}")
    cats = [str(x).strip() for x in (categories or []) if str(x).strip()]
    if cats:
        parts.append(f"重点={','.join(cats[:6])}")
    head = "；".join(parts)

    qline = (
        f"量化指标（{name}）：频次={quant['频次']}；阈值={quant['阈值']}；间距={quant['间距']}；厚度={quant['厚度']}；"
        f"时长={quant['时长']}；人数={quant['人数']}；设备型号={quant['设备型号']}。"
    )
    dwg_line = ""
    if isinstance(drawing_locator, str) and drawing_locator.strip():
        dwg = drawing_locator.strip()
        dwg_line = f"图纸定位：{dwg}；校核点=构件位置/尺寸/标高/做法。【证据:{dwg}】"
    std_line = ""
    if isinstance(standard_locator, str) and standard_locator.strip():
        std = standard_locator.strip()
        std_line = f"标准引用：{std}；条款对照入台账。【证据:{std}】"
    # Risk triplet: concrete, quantifiable, no empty words.
    proc = str(process_hint or "").strip()
    proc_prefix = (proc + "：") if proc else ""
    cats_set = set(cats)
    is_special = "特殊材料" in cats_set
    is_hazard = "危险品材料" in cats_set
    is_ppe = "劳保用品" in cats_set

    if is_hazard:
        risk = f"{proc_prefix}{name}挥发/燃爆/泄漏导致人员伤害与停工"
        control = f"执行《危险品材料统一管理基线》+{name}到货逐批核对(材料员)+{name}领用逐单核验(库管+领用人)"
        verify = (
            f"逐批核对{name}的MSDS/批次/领用记录并记录检测异常"
            f"+记录=《{name}风险与领用核验记录》"
        )
    elif is_special:
        risk = f"{proc_prefix}规格/批次不符导致返工或性能不达标"
        control = "到货逐批验收(材料员+质检员)+逐批复验(质检员)+批次隔离+二维码批次追溯(材料员)"
        verify = f"复验阈值={quant['阈值']}+逐批反查批次记录+记录=《特殊材料到货验收+复验台账》"
    elif is_ppe:
        risk = "未佩戴或用品失效导致伤害"
        control = f"逐人登记发放(安全员)+佩戴抽查={quant['频次']}(安全员)+发现破损立即停用更换(库管)"
        verify = "逐人核对发放与抽查记录+发现未佩戴立即纠正并复核+记录=《劳保发放与抽查台账》"
    else:
        risk_parts = [f"{proc_prefix}关键参数超差导致返工"]
        if "工程量大" in cats_set:
            risk_parts.append("工程量大导致关键线路滞后")
        if "材料需求量大" in cats_set:
            risk_parts.append("材料到货不及时导致停工")
        if ("材料单价高" in cats_set) or ("单体造价高" in cats_set):
            risk_parts.append("高单价或高合价导致成本偏差")
        risk = "+".join([x for x in risk_parts if x][:3])

        control_parts = [
            "逐工序完成首件确认(质检员+施工员)",
            f"过程抽检={quant['频次']}(质检员)",
            f"阈值={quant['阈值']}",
        ]
        if "工程量大" in cats_set:
            control_parts.append("按经批准进度计划分解并滚动校核(施工员)")
        if "材料需求量大" in cats_set:
            control_parts.append("采购提前期按经批准物资计划执行(材料员)")
            control_parts.append("库存下限按经批准物资计划执行(库管)")
        if ("材料单价高" in cats_set) or ("单体造价高" in cats_set):
            control_parts.append("采购比价按经批准采购制度执行(材料员)")
            control_parts.append("领用按构件和班组逐笔核算(材料员)")
        control = "+".join(control_parts[:8])

        verify_parts = [
            f"验收阈值={quant['阈值']}+逐批形成验收结论+记录=《抽检与验收记录》",
        ]
        if "工程量大" in cats_set:
            verify_parts.append("完成量与经批准计划逐日核对")
        if "材料需求量大" in cats_set:
            verify_parts.append("到货日期与经批准物资计划逐批核对")
        if ("材料单价高" in cats_set) or ("单体造价高" in cats_set):
            verify_parts.append("材料消耗与经批准定额逐项核对并形成盘点记录")
        verify = "+".join(verify_parts[:4])

    operational_frequency = _without_evidence_annotations(quant["频次"])
    operational_threshold = _without_evidence_annotations(quant["阈值"])
    operational_deadline = _without_evidence_annotations(
        quant["偏差处置时限"]
    )
    rline = (
        f"风险：{risk}；控制：{control}；验证：{verify}"
        f"；过程控制频次（{name}）={operational_frequency}"
        f"；过程控制阈值（{name}）={operational_threshold}"
        f"；过程责任岗位（{name}）=质量员+施工员"
        f"；过程记录（{name}）=《重点项过程检查台账》"
        f"；过程闭环（{name}）偏差处置时限={operational_deadline}"
        f"。【证据:{evidence_src}】"
    )
    trace_line = (
        f"风险：{name}的批次、构件或验收记录无法反查；"
        f"控制：{name}在进场、施工、验收三阶段使用同一清单编码并逐批核对；"
        f"验证：逐批反查{name}编码且按已确认阈值验收"
        f"；追溯核验频次（{name}）={operational_frequency}"
        f"；追溯验收阈值（{name}）={operational_threshold}"
        f"；追溯责任岗位（{name}）=质量员+材料员"
        f"；追溯记录（{name}）=《重点项编码追溯台账》"
        f"；追溯闭环（{name}）偏差处置时限={operational_deadline}"
        f"。【证据:{evidence_src}】"
    )
    parts = [
        f"- {head}",
        f"  {qline}",
        f"  闭环参数（{name}）：偏差处置时限={quant['偏差处置时限']}。",
    ]
    if dwg_line:
        parts.append(f"  {dwg_line}")
    if std_line:
        parts.append(f"  {std_line}")
    parts.append(f"  风险→控制→验证：{rline}")
    parts.append(f"  风险→控制→验证：{trace_line}")
    return "\n".join(parts)


def _build_hazardous_material_baseline(
    *,
    evidence_src: str,
    quant: dict[str, str],
) -> str:
    """Render document-wide hazardous-material boilerplate exactly once."""

    return (
        f"{_HAZARDOUS_MATERIAL_BASELINE_MARKER}\n"
        "- 适用范围：本文件清单列明的全部危险品材料；各材料的特有风险、批次核验和验证记录见对应清单重点项控制卡。\n"
        "- 统一控制：逐供应商核验采购资质；MSDS随货逐批核验；专柜/专库通风逐班巡检；"
        "动火逐作业审批；可燃气体逐班检测；领用逐单双人复核。\n"
        "- 统一验证：逐项核对入库、巡检、检测和领用记录；发现违章立即处置并复核；"
        f"检查频次={quant['频次']}；记录=《危险品检查与应急台账》。"
        f"【证据:{evidence_src}】"
    )


def _find_focus_card_span(text: str, item_name: str) -> tuple[int, int, int] | None:
    """
    Locate a focus card block for an item in a section.
    Returns (block_start, block_end, first_line_end).
    """
    name_key = boq_focus_name_key(item_name)
    if not name_key:
        return None
    source_text = text or ""
    starts = list(re.finditer(r"(?m)^-\s*清单项\s*[：:]\s*", source_text))
    for index, match in enumerate(starts):
        newline = re.search(r"\r?\n", source_text[match.end() :])
        line_end = match.end() + newline.start() if newline else len(source_text)
        header = source_text[match.end() : line_end]
        header_name = re.split(r"[；;]", header, maxsplit=1)[0]
        if boq_focus_name_key(header_name) != name_key:
            continue
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(source_text)
        return match.start(), block_end, line_end
    return None


def ensure_boq_focus_item_cards(
    sections: list[dict[str, Any]],
    boq_focus: dict[str, Any],
    evidence_src: str,
    params: dict[str, Any] | None = None,
    project_id: str | None = None,
    boq_data: dict[str, Any] | None = None,
    project_fact_ledger: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """
    Enforce that each focus item has a concrete control card (quant + triplet + evidence).
    - Does not create new top-level chapters (tender decides outline).
    - Prefer placing cards into the most relevant existing chapter (by mention/title match).
    Returns (changed, injected_items)
    """
    if not sections or not isinstance(boq_focus, dict):
        return False, []

    focus_items = normalize_boq_focus_items(
        boq_focus.get("must_cover_keywords") or [],
        limit=MAX_BOQ_FOCUS_ITEMS,
    )
    if not focus_items:
        return False, []

    # Keep ``params`` in the call shape for compatibility, but a mutable
    # registry is not an authoritative project-fact source.
    _ = params
    baseline_quant = _source_bound_quant_controls(project_fact_ledger)
    details = _parse_focus_lines(boq_focus.get("lines") or [])
    items = (boq_data or {}).get("items") if isinstance(boq_data, dict) else None
    items = items if isinstance(items, list) else []
    stats = (boq_data or {}).get("stats") if isinstance(boq_data, dict) else {}

    def _name_set(arr: Any) -> set[str]:
        out: set[str] = set()
        if not isinstance(arr, list):
            return out
        for it in arr:
            if not isinstance(it, dict):
                continue
            n = normalize_boq_focus_name(it.get("name"))
            key = boq_focus_name_key(n)
            if key:
                out.add(key)
        return out

    # Categories used to expand risk triplets for focus cards.
    try:
        cat_sets: dict[str, set[str]] = {
            "工程量大": _name_set((stats or {}).get("top_quantity_items") or []),
            "材料需求量大": _name_set((stats or {}).get("top_material_demand_items") or []),
            "单体造价高": _name_set((stats or {}).get("top_total_price_items") or []),
            "材料单价高": _name_set((stats or {}).get("top_unit_price_items") or []),
            "特殊材料": {boq_focus_name_key(x) for x in (boq_focus.get("special_materials") or []) if boq_focus_name_key(x)},
            "危险品材料": {boq_focus_name_key(x) for x in (boq_focus.get("hazardous_materials") or []) if boq_focus_name_key(x)},
            "劳保用品": {boq_focus_name_key(x) for x in (boq_focus.get("ppe_items") or []) if boq_focus_name_key(x)},
        }
    # BoQ statistics are deserialized input; a malformed optional category
    # must not prevent the focus closure report from being produced.
    except Exception:  # noqa: BLE001
        cat_sets = {}

    def _cats_for(name: str) -> list[str]:
        sname = normalize_boq_focus_name(name)
        if not sname:
            return []
        out: list[str] = []
        name_key = boq_focus_name_key(sname)
        for k, s in (cat_sets or {}).items():
            if isinstance(s, set) and name_key in s:
                out.append(k)
        return out

    # Only do drawing/standard typed-evidence enforcement when project_id is set,
    # to avoid cross-project contamination in global runs.
    drawing_names: list[str] = []
    standard_names: list[str] = []
    if project_id:
        try:
            from backend.zhifei_autoplan.evidence import list_ingested_filenames_by_tag

            drawing_names = list_ingested_filenames_by_tag(
                "drawing",
                project_id=str(project_id),
                limit=80,
                exclude_tags=["logo"],
            )
            standard_names = list_ingested_filenames_by_tag(
                "standard",
                project_id=str(project_id),
                limit=80,
                exclude_tags=["logo"],
            )
        # The ingest audit is an optional evidence boundary; empty lists make
        # the downstream typed-evidence gate fail closed.
        except Exception:  # noqa: BLE001
            drawing_names = []
            standard_names = []

    def _process_hint_for_item(name: str) -> str:
        sname = normalize_boq_focus_name(name)
        if not sname:
            return ""
        for rec in items[:2000]:
            if not isinstance(rec, dict):
                continue
            iname = normalize_boq_focus_name(rec.get("name"))
            if not iname:
                continue
            iname_key = boq_focus_name_key(iname)
            sname_key = boq_focus_name_key(sname)
            if iname_key == sname_key or (sname_key in iname_key) or (iname_key in sname_key):
                proc = rec.get("process") if isinstance(rec.get("process"), dict) else {}
                pname = str((proc or {}).get("name") or "").strip()
                if pname:
                    return pname
        return ""

    injected: list[str] = []
    changed = False
    drawing_hits_by_key: dict[str, dict[str, Any]] = {}

    host_idx = _pick_host_section_index(sections)
    blocks_by_idx: dict[int, list[str]] = {}
    hazardous_focus_present = False
    hazardous_baseline_target_idx: int | None = None
    for name in focus_items:
        process_hint = _process_hint_for_item(name)
        quant = _source_bound_quant_controls(
            project_fact_ledger,
            focus_item=name,
            process_hint=process_hint,
        )
        cats = _cats_for(name)
        is_hazardous_focus = "危险品材料" in set(cats)
        hazardous_focus_present = hazardous_focus_present or is_hazardous_focus
        dwg_loc = None
        dwg_hit = None
        std_loc = None
        if project_id and drawing_names:
            try:
                hit = best_drawing_hit(
                    f"{name} {process_hint}",
                    limit=10,
                    prefer_filename_keywords=["图", "图纸", "施工图", "平面", "剖面", "大样", "节点"],
                    project_id=project_id,
                    require_tags=["drawing"],
                    exclude_tags=["logo"],
                )
                if hit and _FULL_DRAWING_LOCATOR_RE.fullmatch(str(hit.get("locator") or "").strip()):
                    dwg_hit = dict(hit)
                    dwg_loc = str(hit.get("locator"))
                    item_key = boq_focus_name_key(name)
                    if item_key:
                        drawing_hits_by_key[item_key] = dwg_hit
            # Evidence lookup failures leave the required drawing locator
            # absent, which is reported by the formal closure gate.
            except Exception:  # noqa: BLE001
                dwg_hit = None
                dwg_loc = None
        if project_id and standard_names:
            try:
                hit = best_ingested_hit(
                    f"{name} {process_hint} 企业标准 工法 作业指导 标准化",
                    limit=10,
                    prefer_filename_keywords=["标准", "企业标准", "工法", "作业指导", "标准化"],
                    project_id=project_id,
                    require_tags=["standard"],
                    exclude_tags=["logo"],
                )
                if hit and hit.get("locator"):
                    std_loc = str(hit.get("locator"))
            # Evidence lookup failures leave the required standard locator
            # absent, which is reported by the formal closure gate.
            except Exception:  # noqa: BLE001
                std_loc = None

        # If a focus card already exists, patch it in-place to include drawing/standard locators.
        if project_id and (dwg_loc or std_loc):
            for sec in sections:
                txt = str(sec.get("content") or "")
                span = _find_focus_card_span(txt, name)
                if not span:
                    continue
                bs, be, le = span
                block = txt[bs:be]
                inserts: list[str] = []
                if dwg_loc and drawing_names:
                    locator_line = _DRAWING_LOCATOR_LINE_RE.search(block)
                    if locator_line and dwg_loc not in locator_line.group(0):
                        replacement = (
                            f"{locator_line.group('indent')}图纸定位：{dwg_loc}；"
                            f"校核点=构件位置/尺寸/标高/做法。【证据:{dwg_loc}】"
                            f"{locator_line.group('newline')}"
                        )
                        block = (
                            block[: locator_line.start()]
                            + replacement
                            + block[locator_line.end() :]
                        )
                        txt = txt[:bs] + block + txt[be:]
                        sec["content"] = txt
                        changed = True
                    elif not locator_line and dwg_loc not in block:
                        inserts.append(f"  图纸定位：{dwg_loc}；校核点=构件位置/尺寸/标高/做法。【证据:{dwg_loc}】")
                if std_loc and standard_names:
                    sset = {str(x).strip() for x in standard_names if str(x).strip()}
                    if ("标准引用：" not in block) and (not _evidence_has_any(block, sset)):
                        inserts.append(f"  标准引用：{std_loc}；条款对照入台账。【证据:{std_loc}】")
                if inserts:
                    sec["content"] = txt[:le] + "\n" + "\n".join(inserts) + txt[le:]
                    changed = True
                break

        # Card identity and typed-evidence closure are separate concerns.  A
        # missing drawing/standard hit must keep formal delivery on HOLD, but
        # rerunning deterministic supplementation must never append a second
        # card for the same BoQ item.
        existing_card_section_idx: int | None = None
        for section_idx, sec in enumerate(sections):
            if _find_focus_card_span(str(sec.get("content") or ""), name):
                existing_card_section_idx = section_idx
                break
        if existing_card_section_idx is not None:
            if is_hazardous_focus and hazardous_baseline_target_idx is None:
                hazardous_baseline_target_idx = existing_card_section_idx
            continue

        # Search other sections to avoid duplication.
        already_ok = False
        closed_section_idx: int | None = None
        for section_idx, sec in enumerate(sections):
            txt = str(sec.get("content") or "")
            if project_id and (drawing_names or standard_names):
                if _item_is_closed_with_typed_evidence(
                    name,
                    txt,
                    drawing_names=drawing_names,
                    standard_names=standard_names,
                ):
                    already_ok = True
                    closed_section_idx = section_idx
                    break
            elif _item_is_closed_in_text(name, txt):
                already_ok = True
                closed_section_idx = section_idx
                break
        if already_ok:
            if is_hazardous_focus and hazardous_baseline_target_idx is None:
                hazardous_baseline_target_idx = closed_section_idx
            continue

        it = details.get(boq_focus_name_key(name)) or {"name": name}
        item_hit = None
        item_ev = evidence_src
        if project_id:
            try:
                item_hit = best_ingested_hit(
                    name,
                    limit=10,
                    prefer_filename_keywords=["清单", "工程量", "BOQ", "bill", "报价"],
                    project_id=project_id,
                )
                if item_hit and item_hit.get("locator"):
                    item_ev = str(item_hit.get("locator"))
            # A failed ingest lookup cannot synthesize evidence; retain the
            # parsed-BoQ locator and let formal evidence validation decide.
            except Exception:  # noqa: BLE001
                item_hit = None
        idx = _pick_section_for_item(
            name,
            sections,
            host_idx,
            hint_snippet=str((item_hit or {}).get("snippet") or ""),
            process_hint=process_hint,
        )
        if is_hazardous_focus and hazardous_baseline_target_idx is None:
            hazardous_baseline_target_idx = idx
        blocks_by_idx.setdefault(idx, []).append(
            _build_focus_card(
                it,
                item_ev,
                quant,
                drawing_locator=dwg_loc,
                standard_locator=std_loc,
                categories=cats,
                process_hint=process_hint,
            )
        )
        injected.append(name)

    baseline_exists = any(
        _HAZARDOUS_MATERIAL_BASELINE_MARKER in str(sec.get("content") or "")
        for sec in sections
        if isinstance(sec, dict)
    )
    if hazardous_focus_present and not baseline_exists:
        target_idx = (
            hazardous_baseline_target_idx
            if hazardous_baseline_target_idx is not None
            else host_idx
        )
        target = sections[target_idx]
        baseline = _build_hazardous_material_baseline(
            evidence_src=evidence_src,
            quant=baseline_quant,
        )
        target_text = str(target.get("content") or "").rstrip()
        target["content"] = (target_text + "\n\n" + baseline).strip() + "\n"
        changed = True

    for idx, blocks in blocks_by_idx.items():
        if not blocks:
            continue
        sec = sections[idx]
        text = str(sec.get("content") or "")
        add = "\n\n【清单重点项控制卡】\n" + "\n".join(blocks) + "\n"
        if "【清单重点项控制卡】" not in text:
            text = (text.rstrip() + "\n\n" + add.strip() + "\n").strip() + "\n"
        else:
            text = (text.rstrip() + "\n\n" + "\n".join(blocks) + "\n").strip() + "\n"
        sec["content"] = text
        changed = True

    # Keep the full page-window identity beside the human-readable card.  The
    # cross-index consumes this structure and independently reverse-validates
    # it against the current drawing catalog; a locator string alone is never
    # promoted to formal evidence.
    if project_id:
        focus_drawing_bindings: list[dict[str, Any]] = []
        for name in focus_items:
            item_key = boq_focus_name_key(name)
            hit = drawing_hits_by_key.get(item_key)
            if not hit:
                continue
            chapter = ""
            for sec in sections:
                section_text = str(sec.get("content") or "")
                if _find_focus_card_span(section_text, name):
                    chapter = str(sec.get("title") or "").strip()
                    break
            if not chapter:
                for sec in sections:
                    if boq_focus_name_in_text(name, str(sec.get("content") or "")):
                        chapter = str(sec.get("title") or "").strip()
                        break
            binding = _focus_drawing_binding_from_hit(
                hit,
                focus_item=name,
                chapter=chapter,
                project_id=str(project_id),
            )
            if binding:
                focus_drawing_bindings.append(binding)

        existing_bindings = (
            boq_focus.get("drawing_bindings")
            if isinstance(boq_focus.get("drawing_bindings"), list)
            else []
        )
        if (
            focus_drawing_bindings or "drawing_bindings" in boq_focus
        ) and existing_bindings != focus_drawing_bindings:
            boq_focus["drawing_bindings"] = focus_drawing_bindings
            changed = True

    return changed, injected
