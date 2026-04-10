from __future__ import annotations

import re
from typing import Any, Dict, List


_BASE_STRATEGIES: dict[str, dict[str, Any]] = {
    "quantitative_gap": {
        "indicator_group": "缺量化",
        "indicator_label": "量化指标不足",
        "strategy_family": "quantitative_fill",
        "strategy_id": "quant_fill_general_v1",
        "strategy_name": "量化指标补齐卡",
        "strategy_priority": 95,
        "strategy_actions": [
            "补频次/阈值/单位数值",
            "补人数/设备型号/时长等执行参数",
            "补记录表与验收口径",
        ],
    },
    "engineering_gap": {
        "indicator_group": "缺量化",
        "indicator_label": "工程化要素不足",
        "strategy_family": "quantitative_fill",
        "strategy_id": "engineering_closure_fill_v1",
        "strategy_name": "工程落地要素补齐卡",
        "strategy_priority": 90,
        "strategy_actions": [
            "补频次/阈值/责任/验收/流程",
            "把描述改成动作+参数+频次",
            "补流程闭环与记录表",
        ],
    },
    "required_topic_detail_gap": {
        "indicator_group": "缺量化",
        "indicator_label": "专项细则不足",
        "strategy_family": "topic_detail_fill",
        "strategy_id": "required_topic_detail_fill_v1",
        "strategy_name": "专项细则补齐卡",
        "strategy_priority": 88,
        "strategy_actions": [
            "补采购/储运/领用/应急等步骤",
            "补频次/阈值/时长数值",
            "补验收动作与台账",
        ],
    },
    "boq_focus_item_closure_gap": {
        "indicator_group": "缺量化",
        "indicator_label": "重点清单项闭环不足",
        "strategy_family": "boq_focus_fill",
        "strategy_id": "boq_focus_closure_fill_v1",
        "strategy_name": "重点清单项闭环卡",
        "strategy_priority": 92,
        "strategy_actions": [
            "补重点项量化指标",
            "补风险→控制→验证",
            "补对应证据与记录表",
        ],
    },
    "risk_measure_gap": {
        "indicator_group": "缺闭环",
        "indicator_label": "风险措施链不完整",
        "strategy_family": "closed_loop_fill",
        "strategy_id": "risk_measure_closure_v1",
        "strategy_name": "风险-措施闭环卡",
        "strategy_priority": 96,
        "strategy_actions": [
            "补风险对应措施",
            "补责任岗位/频次/验收动作",
            "补记录表和偏差处置时限",
        ],
    },
    "risk_triplet_gap": {
        "indicator_group": "缺闭环",
        "indicator_label": "风险控制验证三元组不足",
        "strategy_family": "closed_loop_fill",
        "strategy_id": "risk_triplet_closure_v1",
        "strategy_name": "风险→控制→验证三元组卡",
        "strategy_priority": 98,
        "strategy_actions": [
            "补风险→控制→验证",
            "补验证阈值与方法",
            "补记录表与偏差处置",
        ],
    },
    "qse_closed_loop_gap": {
        "indicator_group": "缺闭环",
        "indicator_label": "质量安全环保闭环不足",
        "strategy_family": "closed_loop_fill",
        "strategy_id": "qse_closed_loop_card_v1",
        "strategy_name": "质量/安全/环保闭环卡",
        "strategy_priority": 99,
        "strategy_actions": [
            "补风险→控制→验证→记录→偏差处置",
            "补责任岗位和检查频次",
            "补阈值、时限和销项口径",
        ],
    },
    "logic_template_adherence_gap": {
        "indicator_group": "缺闭环",
        "indicator_label": "章内逻辑锚点不足",
        "strategy_family": "structure_fill",
        "strategy_id": "logic_template_anchor_fill_v1",
        "strategy_name": "章内逻辑锚点补齐卡",
        "strategy_priority": 84,
        "strategy_actions": [
            "补章内锚点小标题",
            "按既定模板顺序组织段落",
            "保留目录不变，只补章内结构",
        ],
    },
    "chapter_blueprint_gap": {
        "indicator_group": "缺闭环",
        "indicator_label": "章节结构蓝图锚点不足",
        "strategy_family": "structure_fill",
        "strategy_id": "chapter_blueprint_anchor_fill_v1",
        "strategy_name": "章节蓝图锚点补齐卡",
        "strategy_priority": 86,
        "strategy_actions": [
            "补蓝图锚点",
            "为锚点补量化与记录表",
            "按锚点重组章内结构",
        ],
    },
    "evidence_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "证据标注不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "evidence_locator_fill_v1",
        "strategy_name": "证据定位补齐卡",
        "strategy_priority": 97,
        "strategy_actions": [
            "补可追溯证据标注",
            "禁止占位证据",
            "每章至少保留1条有效证据",
        ],
    },
    "evidence_traceability_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "证据可追溯定位不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "traceable_locator_fill_v1",
        "strategy_name": "追溯定位补齐卡",
        "strategy_priority": 98,
        "strategy_actions": [
            "补文件名#页码_sha@offset",
            "确保评审可回查",
            "保留原结论只补定位",
        ],
    },
    "core_conclusion_evidence_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "核心结论证据不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "core_conclusion_evidence_fill_v1",
        "strategy_name": "核心结论证据补齐卡",
        "strategy_priority": 98,
        "strategy_actions": [
            "给带阈值/时限结论补证据",
            "优先补核心结论句",
            "保留结论并加定位符",
        ],
    },
    "drawing_evidence_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "图纸证据不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "drawing_evidence_binding_v1",
        "strategy_name": "图纸证据绑定卡",
        "strategy_priority": 96,
        "strategy_actions": [
            "补图纸定位符",
            "绑定构件位置/尺寸/标高",
            "保留到对应关键工序章节",
        ],
    },
    "drawing_anchor_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "图纸空间锚点不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "drawing_anchor_binding_v1",
        "strategy_name": "图纸空间锚点补齐卡",
        "strategy_priority": 96,
        "strategy_actions": [
            "补空间锚点",
            "补尺寸锚点",
            "锚点与证据定位同步出现",
        ],
    },
    "standard_evidence_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "企业标准证据不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "standard_evidence_binding_v1",
        "strategy_name": "企业标准引用补齐卡",
        "strategy_priority": 95,
        "strategy_actions": [
            "补企业标准/工法定位符",
            "条款转为可执行参数",
            "补首件确认和抽检记录",
        ],
    },
    "boq_focus_item_typed_evidence_gap": {
        "indicator_group": "缺证据",
        "indicator_label": "重点清单项类型证据不足",
        "strategy_family": "evidence_fill",
        "strategy_id": "boq_focus_typed_evidence_fill_v1",
        "strategy_name": "重点项图纸/标准证据卡",
        "strategy_priority": 97,
        "strategy_actions": [
            "补图纸定位符",
            "补企业标准定位符",
            "在重点项控制卡同窗展示",
        ],
    },
    "vague_term": {
        "indicator_group": "表达不实",
        "indicator_label": "空泛词过多",
        "strategy_family": "language_sanitize",
        "strategy_id": "vague_term_rewrite_v1",
        "strategy_name": "空泛词改写卡",
        "strategy_priority": 72,
        "strategy_actions": [
            "删除空泛词",
            "改成动作+参数+频次+责任",
            "补验收和记录",
        ],
    },
    "bureaucratic_phrase": {
        "indicator_group": "表达不实",
        "indicator_label": "官话套话过多",
        "strategy_family": "language_sanitize",
        "strategy_id": "bureaucratic_phrase_rewrite_v1",
        "strategy_name": "官话替换卡",
        "strategy_priority": 74,
        "strategy_actions": [
            "删除官话套话",
            "改成执行动作和阈值",
            "保留业务事实",
        ],
    },
}

ACTION_TAG_LABELS: dict[str, str] = {
    "add_quant_value": "补量化数值",
    "add_frequency_threshold": "补频次/阈值",
    "add_record_acceptance": "补验收/记录",
    "add_risk_control_verify": "补风险→控制→验证",
    "add_frequency_responsibility": "补频次/责任岗位",
    "add_record_rectify": "补整改/销项",
    "add_evidence_locator": "补证据定位符",
    "bind_source_anchor": "补来源锚点",
    "add_anchor_heading": "补章内锚点标题",
    "add_structure_slot": "补结构槽位",
    "sanitize_banned_phrase": "清理空泛/官话",
    "rewrite_action_param": "改写为动作+参数",
}

QUALITY_GATE_METRIC_LABELS: dict[str, str] = {
    "evidence_binding_rate": "证据绑定率",
    "traceable_locator_rate": "证据追溯定位率",
    "risk_triplet_ok_rate": "风险三元组达标率",
    "quantitative_ok_rate": "量化指标达标率",
    "vague_terms_ok_rate": "空泛词清理达标率",
    "graph_binding_rate": "图谱节点绑定率",
}

QUALITY_GATE_METRIC_MAP: dict[str, list[str]] = {
    "quantitative_gap": ["quantitative_ok_rate"],
    "engineering_gap": ["quantitative_ok_rate"],
    "required_topic_detail_gap": ["quantitative_ok_rate"],
    "boq_focus_item_closure_gap": ["quantitative_ok_rate", "risk_triplet_ok_rate", "evidence_binding_rate"],
    "risk_measure_gap": ["risk_triplet_ok_rate"],
    "risk_triplet_gap": ["risk_triplet_ok_rate"],
    "qse_closed_loop_gap": ["risk_triplet_ok_rate", "quantitative_ok_rate"],
    "logic_template_adherence_gap": ["risk_triplet_ok_rate", "quantitative_ok_rate"],
    "chapter_blueprint_gap": ["risk_triplet_ok_rate", "quantitative_ok_rate"],
    "evidence_gap": ["evidence_binding_rate", "graph_binding_rate"],
    "evidence_traceability_gap": ["traceable_locator_rate"],
    "core_conclusion_evidence_gap": ["evidence_binding_rate", "traceable_locator_rate"],
    "drawing_evidence_gap": ["evidence_binding_rate", "traceable_locator_rate"],
    "drawing_anchor_gap": ["traceable_locator_rate"],
    "standard_evidence_gap": ["evidence_binding_rate", "traceable_locator_rate"],
    "boq_focus_item_typed_evidence_gap": ["evidence_binding_rate", "traceable_locator_rate"],
    "vague_term": ["vague_terms_ok_rate"],
    "bureaucratic_phrase": ["vague_terms_ok_rate"],
}

QUANT_UNIT_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mm|cm|m|km|kg|t|h|小时|天|min|分钟|次|人|台|套|%|MPa|kN|m2|m3|dB|db|ug/m3|μg/m3|m/s|℃)",
    re.IGNORECASE,
)
TRACEABLE_EVIDENCE_RE = re.compile(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", re.IGNORECASE)
ANCHOR_HEADINGS = [
    "【工序名称】",
    "【操作步骤】",
    "【控制点】",
    "【量化指标】",
    "【责任岗位】",
    "【检查频次】",
    "【记录表】",
    "【场景拆分】",
    "【指标矩阵】",
    "【闭环卡片】",
    "【监管红线清单】",
    "【区域网格】",
]
BANNED_PHRASES = ["按照", "符合", "确保", "保障", "严格落实", "加强管理", "有效措施", "合理安排", "现场实际情况", "相关规范", "有关规定"]


def _section_meta(sec_by_title: Dict[str, Dict[str, Any]], title: str) -> Dict[str, str]:
    sec = sec_by_title.get(title) if isinstance(sec_by_title, dict) else None
    if not isinstance(sec, dict):
        return {"chapter_domain": "", "template_id": "", "blueprint_id": ""}
    return {
        "chapter_domain": str(sec.get("chapter_domain") or "").strip().lower(),
        "template_id": str(sec.get("logic_template_id") or "").strip().upper(),
        "blueprint_id": str(sec.get("chapter_blueprint_id") or "").strip(),
    }


def _dynamic_strategy(base: Dict[str, Any], title: str, meta: Dict[str, str]) -> Dict[str, Any]:
    chapter_domain = str(meta.get("chapter_domain") or "").strip().lower()
    template_id = str(meta.get("template_id") or "").strip().upper()
    out = dict(base)
    out["chapter_domain"] = chapter_domain
    out["template_id"] = template_id
    if out.get("strategy_id") == "quant_fill_general_v1" and chapter_domain == "qse":
        out["strategy_id"] = "quant_fill_qse_v1"
        out["strategy_name"] = "质量/安全/环保量化补齐卡"
    elif out.get("strategy_id") == "risk_triplet_closure_v1" and chapter_domain == "qse":
        out["strategy_id"] = "risk_triplet_qse_closure_v1"
        out["strategy_name"] = "质量/安全/环保三元组闭环卡"
    elif out.get("strategy_id") == "logic_template_anchor_fill_v1" and template_id:
        out["strategy_id"] = f"logic_template_{template_id.lower()}_anchor_fill_v1"
        out["strategy_name"] = f"章内逻辑锚点补齐卡-{template_id}"
    elif out.get("strategy_id") == "chapter_blueprint_anchor_fill_v1" and meta.get("blueprint_id"):
        out["strategy_name"] = "章节蓝图锚点补齐卡"
    out["audit_key"] = f"{out.get('indicator_group')}/{out.get('strategy_id')}/{title or '章节'}"
    return out


def enrich_strategy_record(
    record: Dict[str, Any],
    *,
    sec_by_title: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {}
    title = str(record.get("title") or "章节").strip() or "章节"
    rtype = str(record.get("type") or "").strip()
    meta = _section_meta(sec_by_title or {}, title)
    base = dict(_BASE_STRATEGIES.get(rtype) or {})
    if not base:
        base = {
            "indicator_group": "其他问题",
            "indicator_label": rtype or "未分类问题",
            "strategy_family": "generic_patch",
            "strategy_id": f"{rtype or 'generic'}_patch_v1",
            "strategy_name": "通用修订补丁",
            "strategy_priority": 60,
            "strategy_actions": [
                "保留原结构",
                "只补缺失项",
                "补可执行动作和记录",
            ],
        }
    enriched = dict(record)
    enriched.update(_dynamic_strategy(base, title, meta))
    enriched["expected_action_tags"] = _expected_action_tags(enriched)
    enriched["expected_quality_gate_metrics"] = expected_quality_gate_metrics(enriched)
    return enriched


def enrich_strategy_rows(
    rows: List[Dict[str, Any]] | None,
    *,
    sec_by_title: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows or []:
        enriched = enrich_strategy_record(row, sec_by_title=sec_by_title)
        if not enriched:
            continue
        key = (
            str(enriched.get("title") or "").strip(),
            str(enriched.get("type") or "").strip(),
            str(enriched.get("strategy_id") or "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(enriched)
    out.sort(
        key=lambda item: (
            -int(item.get("strategy_priority") or 0),
            str(item.get("indicator_group") or ""),
            str(item.get("title") or ""),
            str(item.get("type") or ""),
        )
    )
    return out


def _expected_action_tags(row: Dict[str, Any]) -> List[str]:
    family = str(row.get("strategy_family") or "").strip()
    rtype = str(row.get("type") or "").strip()
    if family == "quantitative_fill":
        return ["add_quant_value", "add_frequency_threshold", "add_record_acceptance"]
    if family == "topic_detail_fill":
        return ["add_quant_value", "add_record_acceptance", "add_structure_slot"]
    if family == "boq_focus_fill":
        return ["add_quant_value", "add_risk_control_verify", "add_evidence_locator"]
    if family == "closed_loop_fill":
        return ["add_risk_control_verify", "add_frequency_responsibility", "add_record_rectify"]
    if family == "evidence_fill":
        return ["add_evidence_locator", "bind_source_anchor"]
    if family == "structure_fill":
        return ["add_anchor_heading", "add_structure_slot", "add_record_acceptance"]
    if family == "language_sanitize":
        return ["sanitize_banned_phrase", "rewrite_action_param"]
    if rtype == "engineering_gap":
        return ["add_frequency_threshold", "add_record_acceptance", "rewrite_action_param"]
    return ["rewrite_action_param", "add_record_acceptance"]


def expected_quality_gate_metrics(row: Dict[str, Any]) -> List[str]:
    metrics = QUALITY_GATE_METRIC_MAP.get(str(row.get("type") or "").strip()) or []
    out: List[str] = []
    seen: set[str] = set()
    for raw in metrics:
        metric = str(raw or "").strip()
        if not metric or metric in seen:
            continue
        seen.add(metric)
        out.append(metric)
    return out


def _diff_tail(before_text: str, after_text: str) -> str:
    before = str(before_text or "")
    after = str(after_text or "")
    if not before:
        return after
    if after.startswith(before):
        return after[len(before):]
    if before in after:
        idx = after.find(before)
        tail = after[idx + len(before):]
        if tail.strip():
            return tail
    return after


def _contains_any(text: str, words: List[str]) -> bool:
    hay = str(text or "")
    return any(str(word or "").strip() and str(word) in hay for word in words)


def _detect_action_tags(delta_text: str, row: Dict[str, Any], before_text: str, after_text: str) -> List[str]:
    delta = str(delta_text or "")
    before = str(before_text or "")
    after = str(after_text or "")
    tags: List[str] = []
    if QUANT_UNIT_RE.search(delta) or _contains_any(delta, ["频次", "阈值", "间距", "厚度", "时长", "人数", "设备型号", "合格率", "一次验收通过率"]):
        tags.append("add_quant_value")
    if _contains_any(delta, ["频次", "阈值", "每100m2", "1次/日", "1次/班", "每批次", "合格率"]):
        tags.append("add_frequency_threshold")
    if _contains_any(delta, ["记录", "台账", "验收", "抽检", "复验", "首件确认", "销项"]):
        tags.append("add_record_acceptance")
    if ("风险" in delta) and (("控制" in delta) or ("措施" in delta)) and ("验证" in delta):
        tags.append("add_risk_control_verify")
    if _contains_any(delta, ["责任岗位", "责任人", "安全员", "质量员", "工长", "材料员"]) and _contains_any(delta, ["频次", "1次/日", "1次/班", "抽检"]):
        tags.append("add_frequency_responsibility")
    if _contains_any(delta, ["偏差处置", "整改", "复验关闭", "销项", "复核关闭", "停工整改"]):
        tags.append("add_record_rectify")
    if ("【证据:" in delta) or TRACEABLE_EVIDENCE_RE.search(delta):
        tags.append("add_evidence_locator")
    if _contains_any(delta, ["图纸", "标准", "工法", "清单", "标高", "尺寸锚点", "空间锚点", "构件"]):
        tags.append("bind_source_anchor")
    if any(anchor in delta for anchor in ANCHOR_HEADINGS):
        tags.append("add_anchor_heading")
    if _contains_any(delta, ["场景拆分", "指标矩阵", "闭环卡片", "监管红线清单", "区域网格", "执行步骤", "工序流程", "资源-工序耦合表"]):
        tags.append("add_structure_slot")
    if any(p in before and p not in after for p in BANNED_PHRASES):
        tags.append("sanitize_banned_phrase")
    if str(row.get("type") or "").strip() in {"vague_term", "bureaucratic_phrase"} or (
        _contains_any(delta, ["动作", "参数", "责任岗位", "验收标准"]) and QUANT_UNIT_RE.search(after)
    ):
        tags.append("rewrite_action_param")
    out: List[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out


def build_execution_profile(
    row: Dict[str, Any],
    *,
    before_text: str,
    after_text: str,
) -> Dict[str, Any]:
    title = str(row.get("title") or "章节").strip() or "章节"
    expected = _expected_action_tags(row)
    delta = _diff_tail(before_text, after_text)
    detected = _detect_action_tags(delta, row, before_text, after_text)
    matched = [tag for tag in expected if tag in detected]
    unmatched = [tag for tag in expected if tag not in detected]
    return {
        "title": title,
        "type": str(row.get("type") or "").strip(),
        "indicator_group": str(row.get("indicator_group") or "").strip(),
        "strategy_id": str(row.get("strategy_id") or "").strip(),
        "strategy_name": str(row.get("strategy_name") or "").strip(),
        "strategy_family": str(row.get("strategy_family") or "").strip(),
        "strategy_priority": int(row.get("strategy_priority") or 0),
        "chapter_domain": str(row.get("chapter_domain") or "").strip(),
        "template_id": str(row.get("template_id") or "").strip(),
        "audit_key": str(row.get("audit_key") or "").strip(),
        "expected_action_tags": expected,
        "detected_action_tags": detected,
        "matched_action_tags": matched,
        "unmatched_action_tags": unmatched,
        "delta_chars": len(delta),
        "delta_lines": max(0, len([ln for ln in delta.splitlines() if ln.strip()])),
        "delta_preview": delta.strip()[:240],
        "execution_status": "matched" if matched else ("detected" if detected else "unknown"),
    }


def build_execution_audit(sections: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    traces: List[Dict[str, Any]] = []
    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        rows = sec.get("remediation_execution_trace") if isinstance(sec.get("remediation_execution_trace"), list) else []
        for row in rows:
            if isinstance(row, dict):
                traces.append(row)
    action_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    title_map: dict[str, dict[str, set[str]]] = {}
    for row in traces:
        status = str(row.get("execution_status") or "unknown").strip() or "unknown"
        status_counts[status] = int(status_counts.get(status) or 0) + 1
        strategy_id = str(row.get("strategy_id") or "").strip()
        if strategy_id:
            strategy_counts[strategy_id] = int(strategy_counts.get(strategy_id) or 0) + 1
        title = str(row.get("title") or "章节").strip() or "章节"
        slot = title_map.setdefault(title, {"action_tags": set(), "strategy_ids": set()})
        for tag in row.get("detected_action_tags") or []:
            name = str(tag or "").strip()
            if not name:
                continue
            action_counts[name] = int(action_counts.get(name) or 0) + 1
            slot["action_tags"].add(name)
        if strategy_id:
            slot["strategy_ids"].add(strategy_id)
    return {
        "trace_count": len(traces),
        "status_counts": [{"status": k, "count": v} for k, v in sorted(status_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))],
        "action_tags": [{"action_tag": k, "label": ACTION_TAG_LABELS.get(k, k), "count": v} for k, v in sorted(action_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))],
        "strategies": [{"strategy_id": k, "count": v} for k, v in sorted(strategy_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))],
        "by_title": [
            {
                "title": title,
                "action_tags": sorted(payload.get("action_tags") or []),
                "strategy_ids": sorted(payload.get("strategy_ids") or []),
            }
            for title, payload in sorted(title_map.items(), key=lambda item: str(item[0]))
        ],
    }


def build_strategy_audit(
    remediation: List[Dict[str, Any]] | None,
    *,
    issue_list: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    rem_rows = [r for r in (remediation or []) if isinstance(r, dict)]
    issue_rows = [r for r in (issue_list or []) if isinstance(r, dict)]
    indicator_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    title_map: dict[str, dict[str, set[str]]] = {}
    mapping_rows: list[dict[str, Any]] = []

    for row in rem_rows:
        indicator_group = str(row.get("indicator_group") or "其他问题").strip() or "其他问题"
        strategy_id = str(row.get("strategy_id") or "").strip() or "generic_patch_v1"
        title = str(row.get("title") or "章节").strip() or "章节"
        indicator_counts[indicator_group] = int(indicator_counts.get(indicator_group) or 0) + 1
        strategy_counts[strategy_id] = int(strategy_counts.get(strategy_id) or 0) + 1
        slot = title_map.setdefault(title, {"indicator_groups": set(), "strategy_ids": set()})
        slot["indicator_groups"].add(indicator_group)
        slot["strategy_ids"].add(strategy_id)
        mapping_rows.append(
            {
                "title": title,
                "type": str(row.get("type") or "").strip(),
                "indicator_group": indicator_group,
                "strategy_id": strategy_id,
                "strategy_name": str(row.get("strategy_name") or "").strip(),
                "strategy_family": str(row.get("strategy_family") or "").strip(),
                "strategy_priority": int(row.get("strategy_priority") or 0),
                "chapter_domain": str(row.get("chapter_domain") or "").strip(),
                "template_id": str(row.get("template_id") or "").strip(),
                "expected_quality_gate_metrics": [
                    str(x).strip()
                    for x in (row.get("expected_quality_gate_metrics") or [])
                    if str(x).strip()
                ],
            }
        )

    title_rows = []
    for title, payload in title_map.items():
        title_rows.append(
            {
                "title": title,
                "indicator_groups": sorted(str(x) for x in payload.get("indicator_groups") or [] if str(x).strip()),
                "strategy_ids": sorted(str(x) for x in payload.get("strategy_ids") or [] if str(x).strip()),
            }
        )
    title_rows.sort(key=lambda item: (-len(item.get("indicator_groups") or []), str(item.get("title") or "")))

    indicator_rows = [
        {"indicator_group": name, "count": count}
        for name, count in sorted(indicator_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
    ]
    strategy_rows = [
        {"strategy_id": name, "count": count}
        for name, count in sorted(strategy_counts.items(), key=lambda item: (-int(item[1]), str(item[0])))
    ]

    return {
        "issue_count": len(issue_rows),
        "remediation_count": len(rem_rows),
        "indicator_groups": indicator_rows,
        "strategies": strategy_rows,
        "by_title": title_rows,
        "mapping_rows": mapping_rows,
    }
