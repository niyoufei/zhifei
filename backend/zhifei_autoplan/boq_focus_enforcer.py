from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from backend.zhifei_autoplan.evidence import best_ingested_hit
from backend.zhifei_autoplan.workspace import workspace_paths
from backend.zhifei_autoplan.params_runtime import get_quant_defaults, get_boq_focus_card_defaults


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


def _parse_focus_lines(lines: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Parse `boq_focus["lines"]` which contains mixed headers and "- item / 工程量=... / 单价=... / 合价=..."
    Returns a map: name -> {qty, unit_price, total_price, raw}
    """
    out: Dict[str, Dict[str, str]] = {}
    for ln in lines or []:
        s = str(ln or "").strip()
        if not s.startswith("- "):
            continue
        body = s[2:].strip()
        m = _FOCUS_ITEM_LINE_RE.match(s)
        if m:
            name = (m.group("name") or "").strip()
            if not name:
                continue
            out[name] = {
                "name": name,
                "qty": (m.group("qty") or "").strip(),
                "unit_price": (m.group("unit_price") or "").strip(),
                "total_price": (m.group("total_price") or "").strip(),
                "raw": body,
            }
            continue
        # Fallback: name is left part
        name = body.split(" / ", 1)[0].strip()
        if name:
            out.setdefault(name, {"name": name, "raw": body})
    return out


def _pick_host_section_index(sections: List[Dict[str, Any]]) -> int:
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


def _extract_evidence_sources(text: str) -> List[str]:
    out: List[str] = []
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


def _item_is_closed_in_text(name: str, text: str, window: int = 420, max_mentions: int = 10) -> bool:
    """
    Determine whether an item is already "closed" in a section without duplicating cards.
    Scan multiple mentions because the first mention may be outside the control-card block.
    """
    sname = str(name or "").strip()
    if not sname or sname not in (text or ""):
        return False
    idx = 0
    checked = 0
    while True:
        pos = (text or "").find(sname, idx)
        if pos < 0:
            break
        checked += 1
        start = max(0, pos - window)
        end = min(len(text or ""), pos + len(sname) + window)
        snippet = (text or "")[start:end]
        if _has_closed_loop_triplet(snippet) and _has_quant_metrics(snippet) and ("【证据:" in snippet):
            return True
        if checked >= max(1, int(max_mentions or 0)):
            break
        idx = pos + max(1, len(sname))
    return False


def _item_is_closed_with_typed_evidence(
    name: str,
    text: str,
    *,
    drawing_names: List[str] | None = None,
    standard_names: List[str] | None = None,
    window: int = 520,
) -> bool:
    """
    Stricter closure for focus items when a project has drawings/standards:
    - base closure (triplet + quant keys + evidence marker)
    - if drawings exist: require at least 1 drawing evidence source near the item
    - if standards exist: require at least 1 standard evidence source near the item
    """
    sname = str(name or "").strip()
    if not sname or sname not in (text or ""):
        return False
    dset = {str(x).strip() for x in (drawing_names or []) if str(x).strip()}
    sset = {str(x).strip() for x in (standard_names or []) if str(x).strip()}
    idx = 0
    checked = 0
    while True:
        pos = (text or "").find(sname, idx)
        if pos < 0:
            break
        checked += 1
        start = max(0, pos - window)
        end = min(len(text or ""), pos + len(sname) + window)
        snippet = (text or "")[start:end]
        if not (_has_closed_loop_triplet(snippet) and _has_quant_metrics(snippet) and ("【证据:" in snippet)):
            if checked >= 10:
                break
            idx = pos + max(1, len(sname))
            continue
        if dset and (not _evidence_has_any(snippet, dset)):
            if checked >= 10:
                break
            idx = pos + max(1, len(sname))
            continue
        if sset and (not _evidence_has_any(snippet, sset)):
            if checked >= 10:
                break
            idx = pos + max(1, len(sname))
            continue
        return True
    return False


def _tokenize_item_name(name: str) -> List[str]:
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


def _tokenize_snippet(snippet: str) -> List[str]:
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
    sections: List[Dict[str, Any]],
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
    sname = str(name or "").strip()
    if not sections:
        return 0

    for i, sec in enumerate(sections):
        title = str(sec.get("title") or "")
        if sname and sname in title:
            return i

    for i, sec in enumerate(sections):
        text = str(sec.get("content") or "")
        if sname and sname in text:
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
    item: Dict[str, str],
    evidence_src: str,
    quant: Dict[str, str],
    card_defaults: Dict[str, str],
    drawing_locator: str | None = None,
    standard_locator: str | None = None,
    categories: List[str] | None = None,
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
        f"量化指标：频次={quant['频次']}；阈值={quant['阈值']}；间距={quant['间距']}；厚度={quant['厚度']}；"
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
        risk = f"{proc_prefix}挥发/燃爆/泄漏导致人员伤害与停工"
        control = (
            "MSDS随货(材料员)+专柜/专库通风(库管)+动火审批(安全员)"
            "+可燃气体检测=1次/班(安全员)+领用双人复核=1次/单(库管+领用人)"
        )
        verify = (
            "检测记录齐全率=100%+违章=0次/月"
            f"+应急演练频次={card_defaults.get('应急演练频次','1次/季度')}+记录=《危险品检查与应急台账》"
        )
    elif is_special:
        risk = f"{proc_prefix}规格/批次不符导致返工或性能不达标"
        control = "到货验收=1次/批(材料员+质检员)+复验=每批次1次(质检员)+批次隔离+二维码批次追溯(材料员)"
        verify = f"复验合格率{card_defaults['合格率阈值']}+批次追溯完整率=100%+记录=《特殊材料到货验收+复验台账》"
    elif is_ppe:
        risk = "未佩戴或用品失效导致伤害"
        control = f"发放=1套/人(安全员)+佩戴抽查={quant['频次']}(安全员)+破损48h内更换(库管)"
        verify = "抽查覆盖率=100%+不佩戴=0次/日+记录=《劳保发放与抽查台账》"
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
            "首件确认=1次/工序(质检员+施工员)",
            f"过程抽检={card_defaults['抽检频次']}(质检员)",
            f"阈值按图纸/标准执行({quant['阈值']})",
        ]
        if "工程量大" in cats_set:
            control_parts.append("日计划分解=1次/日(施工员)")
            control_parts.append("资源峰值周滚动校核=1次/周(施工员)")
        if "材料需求量大" in cats_set:
            control_parts.append("采购下单提前期≥7天(材料员)")
            control_parts.append("库存下限=3天用量(库管)")
        if ("材料单价高" in cats_set) or ("单体造价高" in cats_set):
            control_parts.append(f"采购比价{card_defaults['采购比价']}(材料员)")
            control_parts.append("领用按构件/班组核算=1次/日(材料员)")
        control = "+".join(control_parts[:8])

        verify_parts = [
            f"抽检合格率{card_defaults['合格率阈值']}+一次验收通过率{card_defaults['一次验收通过率']}+记录=《抽检与验收记录》",
        ]
        if "工程量大" in cats_set:
            verify_parts.append("完成量/计划量≥0.95(日统计)")
        if "材料需求量大" in cats_set:
            verify_parts.append("缺料停工=0次/月+到货准时率≥95%(周统计)")
        if ("材料单价高" in cats_set) or ("单体造价高" in cats_set):
            verify_parts.append("材料超耗≤2%(周统计)+盘点差异=0(周盘点)")
        verify = "+".join(verify_parts[:4])

    rline = f"风险：{risk}；控制：{control}；验证：{verify}。【证据:{evidence_src}】"
    parts = [f"- {head}", f"  {qline}"]
    if dwg_line:
        parts.append(f"  {dwg_line}")
    if std_line:
        parts.append(f"  {std_line}")
    parts.append(f"  风险→控制→验证：{rline}")
    return "\n".join(parts)


def _find_focus_card_span(text: str, item_name: str) -> Tuple[int, int, int] | None:
    """
    Locate a focus card block for an item in a section.
    Returns (block_start, block_end, first_line_end).
    """
    name = str(item_name or "").strip()
    if not name:
        return None
    pattern = re.compile(rf"(?m)^-\\s*清单项：\\s*{re.escape(name)}(?:[；\\s]|$)")
    m = pattern.search(text or "")
    if not m:
        return None
    start = m.start()
    nxt = re.search(r"(?m)^-\\s*清单项：", (text or "")[m.end() :])
    end = (m.end() + nxt.start()) if nxt else len(text or "")
    line_end = (text or "").find("\n", start)
    if line_end < 0:
        line_end = len(text or "")
    return start, end, line_end


def ensure_boq_focus_item_cards(
    sections: List[Dict[str, Any]],
    boq_focus: Dict[str, Any],
    evidence_src: str,
    params: Dict[str, Any] | None = None,
    project_id: str | None = None,
    boq_data: Dict[str, Any] | None = None,
    workspace_dir: str | None = None,
) -> Tuple[bool, List[str]]:
    """
    Enforce that each focus item has a concrete control card (quant + triplet + evidence).
    - Does not create new top-level chapters (tender decides outline).
    - Prefer placing cards into the most relevant existing chapter (by mention/title match).
    Returns (changed, injected_items)
    """
    if not sections or not isinstance(boq_focus, dict):
        return False, []

    focus_items = [str(x).strip() for x in (boq_focus.get("must_cover_keywords") or []) if str(x).strip()]
    if not focus_items:
        return False, []

    quant = get_quant_defaults(params)
    card_defaults = get_boq_focus_card_defaults(params)
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
            n = str(it.get("name") or "").strip()
            if n:
                out.add(n)
        return out

    # Categories used to expand risk triplets for focus cards.
    try:
        cat_sets: Dict[str, set[str]] = {
            "工程量大": _name_set((stats or {}).get("top_quantity_items") or []),
            "材料需求量大": _name_set((stats or {}).get("top_material_demand_items") or []),
            "单体造价高": _name_set((stats or {}).get("top_total_price_items") or []),
            "材料单价高": _name_set((stats or {}).get("top_unit_price_items") or []),
            "特殊材料": set([str(x).strip() for x in (boq_focus.get("special_materials") or []) if str(x).strip()]),
            "危险品材料": set([str(x).strip() for x in (boq_focus.get("hazardous_materials") or []) if str(x).strip()]),
            "劳保用品": set([str(x).strip() for x in (boq_focus.get("ppe_items") or []) if str(x).strip()]),
        }
    except Exception:
        cat_sets = {}

    def _cats_for(name: str) -> List[str]:
        sname = str(name or "").strip()
        if not sname:
            return []
        out: List[str] = []
        for k, s in (cat_sets or {}).items():
            try:
                if sname in (s or set()):
                    out.append(k)
            except Exception:
                continue
        return out

    # Only do drawing/standard typed-evidence enforcement when project_id is set,
    # to avoid cross-project contamination in global runs.
    drawing_names: List[str] = []
    standard_names: List[str] = []
    audit_path = workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else None
    if project_id:
        try:
            from backend.zhifei_autoplan.evidence import list_ingested_filenames_by_tag

            drawing_names = list_ingested_filenames_by_tag(
                "drawing",
                project_id=str(project_id),
                limit=80,
                exclude_tags=["logo"],
                audit_path=audit_path,
            )
            standard_names = list_ingested_filenames_by_tag(
                "standard",
                project_id=str(project_id),
                limit=80,
                exclude_tags=["logo"],
                audit_path=audit_path,
            )
        except Exception:
            drawing_names = []
            standard_names = []

    def _process_hint_for_item(name: str) -> str:
        sname = str(name or "").strip()
        if not sname:
            return ""
        for rec in items[:2000]:
            if not isinstance(rec, dict):
                continue
            iname = str(rec.get("name") or "").strip()
            if not iname:
                continue
            if iname == sname or (sname in iname) or (iname in sname):
                proc = rec.get("process") if isinstance(rec.get("process"), dict) else {}
                pname = str((proc or {}).get("name") or "").strip()
                if pname:
                    return pname
        return ""

    injected: List[str] = []
    changed = False

    host_idx = _pick_host_section_index(sections)
    blocks_by_idx: Dict[int, List[str]] = {}
    for name in focus_items[:12]:
        process_hint = _process_hint_for_item(name)
        cats = _cats_for(name)
        dwg_loc = None
        std_loc = None
        if project_id and drawing_names:
            try:
                hit = best_ingested_hit(
                    f"{name} {process_hint} 图纸",
                    limit=10,
                    prefer_filename_keywords=["图", "图纸", "施工图", "平面", "剖面", "大样", "节点"],
                    project_id=project_id,
                    require_tags=["drawing"],
                    exclude_tags=["logo"],
                    audit_path=audit_path,
                )
                if hit and hit.get("locator"):
                    dwg_loc = str(hit.get("locator"))
            except Exception:
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
                    audit_path=audit_path,
                )
                if hit and hit.get("locator"):
                    std_loc = str(hit.get("locator"))
            except Exception:
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
                inserts: List[str] = []
                if dwg_loc and drawing_names:
                    dset = {str(x).strip() for x in drawing_names if str(x).strip()}
                    if ("图纸定位：" not in block) and (not _evidence_has_any(block, dset)):
                        inserts.append(f"  图纸定位：{dwg_loc}；校核点=构件位置/尺寸/标高/做法。【证据:{dwg_loc}】")
                if std_loc and standard_names:
                    sset = {str(x).strip() for x in standard_names if str(x).strip()}
                    if ("标准引用：" not in block) and (not _evidence_has_any(block, sset)):
                        inserts.append(f"  标准引用：{std_loc}；条款对照入台账。【证据:{std_loc}】")
                if inserts:
                    sec["content"] = txt[:le] + "\n" + "\n".join(inserts) + txt[le:]
                    changed = True
                break

        # Search other sections to avoid duplication.
        already_ok = False
        for sec in sections:
            txt = str(sec.get("content") or "")
            if project_id and (drawing_names or standard_names):
                if _item_is_closed_with_typed_evidence(
                    name,
                    txt,
                    drawing_names=drawing_names,
                    standard_names=standard_names,
                ):
                    already_ok = True
                    break
            elif _item_is_closed_in_text(name, txt):
                already_ok = True
                break
        if already_ok:
            continue

        it = details.get(name) or {"name": name}
        item_hit = None
        item_ev = evidence_src
        try:
            item_hit = best_ingested_hit(
                name,
                limit=10,
                prefer_filename_keywords=["清单", "工程量", "BOQ", "bill", "报价"],
                project_id=project_id,
                audit_path=audit_path,
            )
            if item_hit and item_hit.get("locator"):
                item_ev = str(item_hit.get("locator"))
        except Exception:
            item_hit = None
        idx = _pick_section_for_item(
            name,
            sections,
            host_idx,
            hint_snippet=str((item_hit or {}).get("snippet") or ""),
            process_hint=process_hint,
        )
        blocks_by_idx.setdefault(idx, []).append(
            _build_focus_card(
                it,
                item_ev,
                quant,
                card_defaults,
                drawing_locator=dwg_loc,
                standard_locator=std_loc,
                categories=cats,
                process_hint=process_hint,
            )
        )
        injected.append(name)

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

    return changed, injected
