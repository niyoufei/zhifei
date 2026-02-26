#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

DEFAULT_KG_ROOT = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
DEFAULT_PATTERN = "ZF-KG-*.json"
DEFAULT_REPORT_JSON = Path("build/KG_Strengthening_Report.json")
DEFAULT_REPORT_MD = Path("build/KG_Strengthening_Report.md")

AUTHORITY_CHAIN = ["答疑文件", "设计图纸", "国标", "行标", "企标"]
VALID_SOURCE_HIERARCHY = set(AUTHORITY_CHAIN)

VAGUE_WORDS = ["加强", "提高", "注意", "确保", "严格"]

DEFAULT_GUARDRAILS = {
    "enabled": True,
    "forbidden_vague_words": VAGUE_WORDS,
    "required_structure": ["action", "parameter", "checker"],
    "three_step_logic_lock": {
        "enabled": True,
        "step1": "定义工序与参数",
        "step2": "分析风险与难点",
        "step3": "控制措施与验证",
        "flow_chain": "工序名称->参数->风险->控制->验证",
    },
    "dry_content_density_lock": {
        "enabled": True,
        "min_numeric_parameters": 3,
        "must_include_checker": True,
    },
}

DEFAULT_RESPONSE_ASSERTIONS = ["must_have_action", "must_have_checker", "must_have_parameter"]

DEFAULT_DRY_CONTENT_LOCK = {
    "enabled": True,
    "forbidden_words": VAGUE_WORDS,
    "required_triplet": "Action+Parameter+Checker",
}

DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "质量": ["质量", "验收", "缺陷", "强度", "平整", "渗漏"],
    "安全": ["安全", "危大", "隐患", "应急", "临电", "事故"],
    "进度": ["进度", "工期", "里程碑", "节点", "关键线路", "穿插"],
    "环保": ["环保", "扬尘", "噪声", "pm10", "污水", "绿色"],
    "重难点": ["重难点", "难点", "复杂", "关键工序", "高风险", "异形", "超限"],
    "扣分点": ["扣分", "废标", "否决", "处罚", "失分", "一票否决"],
}

CHECKER_BY_DIMENSION = {
    "质量": "质量员",
    "安全": "安全员",
    "进度": "施工员",
    "环保": "环保员",
    "重难点": "技术负责人",
    "扣分点": "项目总工",
}

PARAMS_BY_DIMENSION: Dict[str, Dict[str, Any]] = {
    "质量": {"acceptance_pass_rate_percent": 95, "sampling_frequency_per_shift": 2, "deviation_limit_mm": 3},
    "安全": {"inspection_frequency_per_shift": 2, "emergency_response_minutes": 30, "risk_factor": 1.2},
    "进度": {"work_volume": 1200, "productivity_per_day": 240, "crew_efficiency": 0.9},
    "环保": {"pm10_value": 120, "spray_frequency_per_day": 6, "noise_day_db": 70},
    "重难点": {"complexity_index": 1.4, "risk_factor": 1.2, "specialist_workers": 12},
    "扣分点": {"non_response_items": 0, "penalty_weight": 2, "response_deadline_hours": 4},
}

FORMULA_POOL_BY_DIM: Dict[str, List[Tuple[str, List[str]]]] = {
    "质量": [
        ("pass_count / max(total_check_count, 1) * 100", ["pass_count", "total_check_count"]),
        ("100 - defect_count * 100 / max(sample_count, 1)", ["defect_count", "sample_count"]),
        (
            "max(target_strength - measured_strength, 0) / max(target_strength, 1) * 100",
            ["target_strength", "measured_strength"],
        ),
        ("rework_volume * 100 / max(total_work_volume, 1)", ["rework_volume", "total_work_volume"]),
        (
            "inspection_batches * pass_rate_percent / max(total_batches, 1)",
            ["inspection_batches", "pass_rate_percent", "total_batches"],
        ),
    ],
    "安全": [
        (
            "hazard_count * risk_factor / max(inspection_frequency_per_shift, 1)",
            ["hazard_count", "risk_factor", "inspection_frequency_per_shift"],
        ),
        ("unsafe_events * 100 / max(work_hours, 1)", ["unsafe_events", "work_hours"]),
        ("high_risk_tasks * 100 / max(total_tasks, 1)", ["high_risk_tasks", "total_tasks"]),
        (
            "emergency_response_minutes / max(target_response_minutes, 1)",
            ["emergency_response_minutes", "target_response_minutes"],
        ),
        ("near_miss_count * 100 / max(total_workers, 1)", ["near_miss_count", "total_workers"]),
    ],
    "进度": [
        (
            "work_volume / max(productivity_per_day * crew_efficiency, 1)",
            ["work_volume", "productivity_per_day", "crew_efficiency"],
        ),
        ("remaining_work / max(daily_output, 1)", ["remaining_work", "daily_output"]),
        ("delay_hours * 100 / max(planned_hours, 1)", ["delay_hours", "planned_hours"]),
        ("actual_duration_days / max(planned_duration_days, 1)", ["actual_duration_days", "planned_duration_days"]),
        ("resource_gap_hours / max(planned_resource_hours, 1)", ["resource_gap_hours", "planned_resource_hours"]),
    ],
    "环保": [
        ("pm10_value / max(spray_frequency_per_day, 1)", ["pm10_value", "spray_frequency_per_day"]),
        ("noise_day_db / max(noise_limit_db, 1)", ["noise_day_db", "noise_limit_db"]),
        (
            "max(target_recycle_percent - recycle_percent, 0)",
            ["target_recycle_percent", "recycle_percent"],
        ),
        ("max(pm10_value - pm10_limit, 0) / max(pm10_limit, 1) * 100", ["pm10_value", "pm10_limit"]),
        ("water_reuse_volume * 100 / max(total_water_volume, 1)", ["water_reuse_volume", "total_water_volume"]),
    ],
    "重难点": [
        (
            "complexity_index * risk_factor / max(specialist_workers, 1)",
            ["complexity_index", "risk_factor", "specialist_workers"],
        ),
        (
            "interface_points * coordination_factor / max(team_count, 1)",
            ["interface_points", "coordination_factor", "team_count"],
        ),
        ("risk_items / max(control_measures, 1)", ["risk_items", "control_measures"]),
        (
            "special_process_count * risk_factor / max(expert_team_size, 1)",
            ["special_process_count", "risk_factor", "expert_team_size"],
        ),
        ("cross_operation_interfaces / max(control_nodes, 1)", ["cross_operation_interfaces", "control_nodes"]),
    ],
    "扣分点": [
        (
            "non_response_items * penalty_weight + overdue_hours / max(response_deadline_hours, 1)",
            ["non_response_items", "penalty_weight", "overdue_hours", "response_deadline_hours"],
        ),
        ("missing_evidence_items * penalty_weight", ["missing_evidence_items", "penalty_weight"]),
        ("deviation_items * 100 / max(check_items, 1)", ["deviation_items", "check_items"]),
        (
            "missing_clause_count * penalty_weight * 100 / max(total_clause_count, 1)",
            ["missing_clause_count", "penalty_weight", "total_clause_count"],
        ),
        (
            "max(required_response_items - responded_items, 0) * penalty_weight",
            ["required_response_items", "responded_items", "penalty_weight"],
        ),
    ],
}

CANONICAL_POOL_EXPRESSIONS = {
    expr
    for formulas in FORMULA_POOL_BY_DIM.values()
    for expr, _vars in formulas
}

DEFAULT_VAR_VALUES: Dict[str, float] = {
    "pass_count": 95,
    "total_check_count": 100,
    "defect_count": 2,
    "sample_count": 100,
    "target_strength": 40,
    "measured_strength": 38,
    "rework_volume": 25,
    "total_work_volume": 1200,
    "inspection_batches": 6,
    "pass_rate_percent": 96,
    "total_batches": 6,
    "hazard_count": 3,
    "risk_factor": 1.2,
    "inspection_frequency_per_shift": 2,
    "unsafe_events": 1,
    "work_hours": 8,
    "high_risk_tasks": 2,
    "total_tasks": 20,
    "emergency_response_minutes": 20,
    "target_response_minutes": 30,
    "near_miss_count": 2,
    "total_workers": 80,
    "work_volume": 1200,
    "productivity_per_day": 240,
    "crew_efficiency": 0.9,
    "remaining_work": 300,
    "daily_output": 60,
    "delay_hours": 2,
    "planned_hours": 12,
    "actual_duration_days": 9,
    "planned_duration_days": 8,
    "resource_gap_hours": 6,
    "planned_resource_hours": 120,
    "pm10_value": 120,
    "spray_frequency_per_day": 6,
    "noise_day_db": 70,
    "noise_limit_db": 70,
    "pm10_limit": 150,
    "water_reuse_volume": 300,
    "total_water_volume": 420,
    "target_recycle_percent": 80,
    "recycle_percent": 75,
    "complexity_index": 1.4,
    "specialist_workers": 12,
    "interface_points": 8,
    "coordination_factor": 1.2,
    "team_count": 4,
    "risk_items": 5,
    "control_measures": 8,
    "special_process_count": 6,
    "expert_team_size": 9,
    "cross_operation_interfaces": 10,
    "control_nodes": 14,
    "non_response_items": 0,
    "penalty_weight": 2,
    "overdue_hours": 1,
    "response_deadline_hours": 4,
    "missing_evidence_items": 1,
    "deviation_items": 1,
    "check_items": 20,
    "missing_clause_count": 1,
    "total_clause_count": 50,
    "required_response_items": 30,
    "responded_items": 29,
}

DOMAIN_BY_FILE_RULES: List[Tuple[str, str]] = [
    ("housing", "building"),
    ("hospital", "building"),
    ("decoration", "building"),
    ("exterior-ancillary", "building"),
    ("urban-renewal", "building"),
    ("landscape", "road"),
    ("municipal-road", "road"),
    ("highway", "road"),
    ("municipal-bridge", "bridge"),
    ("bridge", "bridge"),
    ("municipal-tunnel", "tunnel"),
    ("utility-tunnel", "tunnel"),
    ("tunnel", "tunnel"),
    ("railway", "railway"),
    ("rail-transit", "railway"),
    ("municipal-drainage", "hydraulic"),
    ("municipal-wtp", "hydraulic"),
    ("river-improvement", "hydraulic"),
    ("sponge-city", "hydraulic"),
    ("water-hydro", "hydraulic"),
    ("hydraulic-hub", "hydraulic"),
    ("offshorewind-marine", "hydraulic"),
    ("port-harbor", "hydraulic"),
    ("gas", "mep"),
    ("district-heating", "mep"),
    ("power-energy", "mep"),
    ("waste-to-energy", "mep"),
    ("petrochemical", "mep"),
    ("industrial-pipeline", "mep"),
    ("weak-current", "mep"),
    ("water-fire-water", "mep"),
    ("hvac", "mep"),
    ("fire-protection", "mep"),
    ("communication", "mep"),
    ("mep", "mep"),
    ("data-center", "mep"),
    ("airport", "road"),
    ("waterproofing", "building"),
    ("existing-building-reinforcement", "building"),
    ("steel-structure", "building"),
    ("prefabricated-building", "building"),
    ("deep-excavation", "earthwork"),
    ("foundationengineering", "earthwork"),
    ("crane-installation", "building"),
    ("large-lifting", "building"),
    ("demolition", "building"),
    ("curtain-wall", "building"),
    ("smartom-fm", "digital"),
    ("scaffolding-formwork", "building"),
    ("bim-digitalconstruction", "digital"),
    ("safetycivilization", "management"),
    ("general-fournew", "management"),
    ("smartsite-general", "digital"),
    ("temporaryworks-sitelayout", "management"),
    ("greenconstruction", "management"),
    ("networkgraph-quantum-carbon", "digital"),
]

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "building": ["房建", "建筑", "主体", "装修", "幕墙", "钢结构", "装配式", "医院", "机房"],
    "mep": ["机电", "电气", "暖通", "消防", "给排水", "弱电", "通信", "管道", "桥架"],
    "hydraulic": ["水利", "河道", "闸门", "泵站", "堤防", "港航", "海工", "水处理"],
    "road": ["道路", "路基", "路面", "沥青", "导改", "市政道路"],
    "bridge": ["桥梁", "箱梁", "桥墩", "盖梁", "挂篮", "桥面"],
    "tunnel": ["隧道", "盾构", "衬砌", "洞门", "暗挖", "矿山法"],
    "railway": ["铁路", "轨道", "高铁", "接触网", "营业线"],
    "earthwork": ["土方", "开挖", "回填", "基坑", "地基", "边坡", "降水"],
    "digital": ["bim", "数字化", "智慧工地", "平台", "数据中台", "物联", "传感", "算法"],
    "management": ["总平", "临建", "文明施工", "四新", "绿色施工", "组织管理", "策划", "统筹"],
}

DOMAIN_STANDARDS: Dict[str, List[str]] = {
    "building": [
        "GB 50204-2015 混凝土结构工程施工质量验收规范",
        "GB 50210-2018 建筑装饰装修工程质量验收标准",
    ],
    "road": [
        "JTG F80/1-2017 公路工程质量检验评定标准",
        "CJJ 1-2008 城镇道路工程施工与质量验收规范",
    ],
    "bridge": [
        "JTG/T 3650-2020 公路桥涵施工技术规范",
        "JTG F80/1-2017 公路工程质量检验评定标准",
    ],
    "tunnel": [
        "JTG/T 3660-2020 公路隧道施工技术规范",
        "TB 10304-2020 铁路隧道工程施工安全技术规程",
    ],
    "railway": [
        "TB 10302-2020 铁路工程施工安全技术规程",
        "TB 10424-2018 铁路混凝土工程施工质量验收标准",
    ],
    "hydraulic": [
        "SL 176-2007 水利水电工程施工质量检验与评定规程",
        "SL 398-2007 水利水电工程施工通用安全技术规程",
    ],
    "mep": [
        "GB 50242-2002 建筑给水排水及采暖工程施工质量验收规范",
        "GB 50303-2015 建筑电气工程施工质量验收规范",
    ],
    "earthwork": [
        "GB 50202-2018 建筑地基基础工程施工质量验收标准",
        "JGJ 120-2012 建筑基坑支护技术规程",
    ],
    "digital": [
        "GB/T 51212-2016 建筑信息模型应用统一标准",
        "GB/T 50314-2015 智能建筑设计标准",
    ],
    "management": [
        "GB/T 50326-2017 建设工程项目管理规范",
        "GB/T 50430-2017 工程建设施工企业质量管理规范",
    ],
}

DIMENSION_STANDARDS: Dict[str, List[str]] = {
    "质量": ["GB 50300-2013 建筑工程施工质量验收统一标准"],
    "安全": ["JGJ 59-2011 建筑施工安全检查标准"],
    "进度": ["GB/T 50326-2017 建设工程项目管理规范"],
    "环保": ["GB/T 50640-2010 建筑工程绿色施工评价标准"],
    "重难点": ["GB/T 50326-2017 建设工程项目管理规范"],
    "扣分点": ["GB/T 50326-2017 建设工程项目管理规范"],
}

RESOURCE_PROFILE_BY_DIM: Dict[str, Dict[str, Any]] = {
    "质量": {"crew_size": "8-12人/班", "checker_role": "质量员", "inspection_frequency": "2次/班"},
    "安全": {"crew_size": "8-12人/班", "checker_role": "安全员", "inspection_frequency": "2次/班"},
    "进度": {"crew_size": "10-16人/班", "checker_role": "施工员", "inspection_frequency": "1次/班"},
    "环保": {"crew_size": "6-10人/班", "checker_role": "环保员", "inspection_frequency": "2次/班"},
    "重难点": {"crew_size": "10-14人/班", "checker_role": "技术负责人", "inspection_frequency": "2次/班"},
    "扣分点": {"crew_size": "6-8人/班", "checker_role": "项目总工", "inspection_frequency": "每项必核"},
}

EQUIPMENT_PROFILE_BY_DOMAIN: Dict[str, Dict[str, List[str]]] = {
    "building": {"primary": ["塔吊1台", "施工升降机1台"], "backup": ["发电机1台"]},
    "mep": {"primary": ["电动套丝机1台", "绝缘测试仪1台"], "backup": ["应急照明箱1套"]},
    "hydraulic": {"primary": ["潜水泵2台", "发电机1台"], "backup": ["备用泵1台"]},
    "road": {"primary": ["摊铺机1台", "压路机1台"], "backup": ["洒水车1台"]},
    "bridge": {"primary": ["汽车吊1台", "张拉设备1套"], "backup": ["备用千斤顶1套"]},
    "tunnel": {"primary": ["湿喷机1台", "通风机1台"], "backup": ["应急风机1台"]},
    "railway": {"primary": ["轨检仪1套", "捣固机1台"], "backup": ["应急轨道工具1套"]},
    "earthwork": {"primary": ["挖机1台", "装载机1台"], "backup": ["降水设备1套"]},
    "digital": {"primary": ["BIM工作站2套", "激光扫描仪1台"], "backup": ["数据采集终端1套"]},
    "management": {"primary": ["测量仪器1套", "视频巡检终端1套"], "backup": ["应急广播1套"]},
}

MATERIAL_PROFILE_BY_DIM: Dict[str, Dict[str, Any]] = {
    "质量": {"acceptance_rule": "100%批次进场验收", "wastage_rate_percent": 2.0},
    "安全": {"acceptance_rule": "危大材料专项验收", "wastage_rate_percent": 1.0},
    "进度": {"acceptance_rule": "关键材料提前锁定", "wastage_rate_percent": 2.5},
    "环保": {"acceptance_rule": "环保材料优先", "wastage_rate_percent": 1.5},
    "重难点": {"acceptance_rule": "专项样板先行", "wastage_rate_percent": 2.0},
    "扣分点": {"acceptance_rule": "证据材料闭环归档", "wastage_rate_percent": 1.0},
}

SCHEDULE_BASELINE_BY_DIM: Dict[str, Dict[str, Any]] = {
    "质量": {"min_process_interval_days": 1, "max_recovery_hours": 24},
    "安全": {"min_process_interval_days": 1, "max_recovery_hours": 12},
    "进度": {"min_process_interval_days": 2, "max_recovery_hours": 24},
    "环保": {"min_process_interval_days": 1, "max_recovery_hours": 12},
    "重难点": {"min_process_interval_days": 2, "max_recovery_hours": 12},
    "扣分点": {"min_process_interval_days": 1, "max_recovery_hours": 8},
}

CRITICAL_PATH_HINT_BY_DOMAIN: Dict[str, List[str]] = {
    "building": ["基础施工", "主体结构", "机电安装", "竣工验收"],
    "mep": ["预留预埋", "主干管线", "设备安装", "联调联试"],
    "hydraulic": ["围堰导流", "主体施工", "机电调试", "通水验收"],
    "road": ["路基处理", "基层摊铺", "面层施工", "交工验收"],
    "bridge": ["桩基施工", "下部结构", "上部结构", "桥面系"],
    "tunnel": ["超前地质预报", "开挖支护", "二衬施工", "附属安装"],
    "railway": ["路基/桥隧", "轨道铺设", "四电安装", "联调联试"],
    "earthwork": ["清表放样", "土方开挖", "边坡支护", "回填验收"],
    "digital": ["数据建模", "现场采集", "进度联动", "交付归档"],
    "management": ["现场总平部署", "临建搭设", "平面导改", "综合交付"],
}

QUANT_INDEX_BASE_BY_DIM: Dict[str, Dict[str, float]] = {
    "质量": {"duration_index": 0.88, "risk_index": 0.35, "resource_density_index": 0.52},
    "安全": {"duration_index": 0.84, "risk_index": 0.62, "resource_density_index": 0.58},
    "进度": {"duration_index": 0.92, "risk_index": 0.45, "resource_density_index": 0.66},
    "环保": {"duration_index": 0.86, "risk_index": 0.40, "resource_density_index": 0.50},
    "重难点": {"duration_index": 0.80, "risk_index": 0.68, "resource_density_index": 0.72},
    "扣分点": {"duration_index": 0.78, "risk_index": 0.70, "resource_density_index": 0.46},
}

SOURCE_CONFIDENCE = {"答疑文件": 1.0, "设计图纸": 0.92, "国标": 0.86, "行标": 0.82, "企标": 0.72}

PROCESS_STAGE_RULES: List[Tuple[int, List[str]]] = [
    (0, ["准备", "策划", "交底", "测量", "放样"]),
    (1, ["开挖", "清表", "拆除", "降水", "钻孔"]),
    (2, ["地基", "基础", "支护", "桩", "垫层"]),
    (3, ["钢筋", "模板", "浇筑", "混凝土", "砌体", "主体", "吊装"]),
    (4, ["机电", "安装", "管道", "电气", "暖通", "消防", "弱电"]),
    (5, ["调试", "联调", "试运行"]),
    (6, ["验收", "移交", "交工", "竣工"]),
]

METHOD_CONFLICT_PAIRS: List[Tuple[str, str]] = [
    ("明挖", "暗挖"),
    ("盾构", "矿山法"),
    ("装配式", "现浇"),
    ("预制", "现浇"),
]

QA_TRIGGER_TERMS = [
    "评分",
    "工期",
    "节点",
    "关键线路",
    "接口",
    "风险",
    "奖惩",
    "索赔",
    "变更",
    "响应",
]

LEGACY_GENERIC_FORMULAS = {
    "hazard_count * risk_factor / max(inspection_frequency_per_shift, 1)",
    "work_volume / max(productivity_per_day * crew_efficiency, 1)",
    "complexity_index * risk_factor / max(specialist_workers, 1)",
    "pass_count / max(total_check_count, 1) * 100",
    "max(48 - conversion_time_h, 0)",
}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


def _unique_keep_order(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        s = str(value or "").strip()
        if not s:
            continue
        key = _normalize_text(s)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _stable_index(key: str, size: int) -> int:
    if size <= 1:
        return 0
    digest = hashlib.md5(key.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:8], 16) % size


def _file_slug(file_stem: str) -> str:
    s = str(file_stem or "").strip().lower()
    s = re.sub(r"^zf-kg-\d+-", "", s)
    return s


def _infer_file_domain(file_stem: str) -> str:
    slug = _file_slug(file_stem)
    for token, domain in DOMAIN_BY_FILE_RULES:
        if token in slug:
            return domain
    return "general"


def _infer_dimension(node: Dict[str, Any]) -> str:
    existing = str(node.get("kg_dimension") or "").strip()
    if existing in {"质量", "安全", "进度", "环保", "重难点", "扣分点"}:
        return existing

    qt_tag = node.get("qt_tag")
    if isinstance(qt_tag, list):
        qt_text = " ".join(str(x) for x in qt_tag)
    else:
        qt_text = str(qt_tag or "")
    for dim in ("质量", "安全", "进度", "环保", "重难点", "扣分点"):
        if dim in qt_text:
            return dim

    text = json.dumps(node, ensure_ascii=False).lower()
    best = "质量"
    best_score = -1
    for dim, kws in DIMENSION_KEYWORDS.items():
        score = sum(1 for kw in kws if kw.lower() in text)
        if score > best_score:
            best = dim
            best_score = score
    return best


def _infer_node_domain(node: Dict[str, Any], file_domain: str) -> str:
    text = json.dumps(node, ensure_ascii=False).lower()
    best_domain = file_domain if file_domain != "general" else "building"
    best_score = -1
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if domain == file_domain:
            score += 1
        if score > best_score or (score == best_score and domain == file_domain):
            best_domain = domain
            best_score = score
    return best_domain


def _infer_domain_aliases(node: Dict[str, Any], node_domain: str) -> List[str]:
    text = json.dumps(node, ensure_ascii=False).lower()
    scored: List[Tuple[int, str]] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if domain == node_domain:
            continue
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scored.append((score, domain))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [dom for _score, dom in scored[:3]]


def _extract_formula_vars(expr: str) -> List[str]:
    try:
        tree = ast.parse(expr, mode="eval")
    except Exception:
        return []
    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id in {"max", "min", "abs", "round"}:
                continue
            names.append(node.id)
    return sorted(set(names))


def _ensure_guardrails(node: Dict[str, Any]) -> int:
    changed = 0
    guardrails = node.get("language_guardrails")
    if not isinstance(guardrails, dict) or not guardrails:
        node["language_guardrails"] = json.loads(json.dumps(DEFAULT_GUARDRAILS, ensure_ascii=False))
        changed += 1
    response_assertions = node.get("response_assertions")
    if not isinstance(response_assertions, list) or not response_assertions:
        node["response_assertions"] = list(DEFAULT_RESPONSE_ASSERTIONS)
        changed += 1
    dry_lock = node.get("dry_content_lock")
    if not isinstance(dry_lock, dict) or not dry_lock:
        node["dry_content_lock"] = dict(DEFAULT_DRY_CONTENT_LOCK)
        changed += 1
    return changed


def _ensure_domain_and_conditions(node: Dict[str, Any], node_domain: str) -> int:
    changed = 0
    if node_domain and str(node.get("professional_domain") or "").strip() != node_domain:
        node["professional_domain"] = node_domain
        changed += 1
    aliases = _infer_domain_aliases(node=node, node_domain=node_domain)
    if node.get("professional_domain_aliases") != aliases:
        node["professional_domain_aliases"] = aliases
        changed += 1

    if not isinstance(node.get("applicable_conditions"), dict) or not node.get("applicable_conditions"):
        node["applicable_conditions"] = {"scenario": "常规施工场景", "climate": "常规", "geology": "按勘察报告"}
        changed += 1

    if not isinstance(node.get("resource_requirements"), dict) or not node.get("resource_requirements"):
        node["resource_requirements"] = {
            "manpower": "按工序配置",
            "equipment": "按方案配置",
            "material": "按清单及损耗率配置",
        }
        changed += 1

    safety = str(node.get("safety_level") or "").strip().lower()
    if safety in {"", "unknown", "none"}:
        node["safety_level"] = "medium"
        changed += 1

    return changed


def _reference_tier(ref: str) -> str:
    r = str(ref or "").strip().upper()
    if not r:
        return ""
    if r.startswith("GB"):
        return "国标"
    if r.startswith(("JGJ", "SL", "TB", "CJJ", "JTG", "DL", "SY", "NY")):
        return "行标"
    if r.startswith(("Q/", "Q", "T/")):
        return "企标"
    return ""


def _is_answer_related(node: Dict[str, Any], dim: str, merged_text: str, node_domain: str, file_stem: str) -> bool:
    if dim == "扣分点" and any(k in merged_text for k in ("扣分", "废标", "否决", "处罚", "失分", "一票否决")):
        return True
    if any(k in merged_text for k in ("答疑", "澄清", "补遗", "clarification", "q&a")):
        return True
    if dim not in {"重难点", "进度", "安全"}:
        return False
    has_trigger = any(k in merged_text for k in QA_TRIGGER_TERMS)
    key = "|".join(
        [
            str(file_stem or ""),
            str(node.get("node_id") or ""),
            str(node.get("name") or node.get("title") or ""),
            dim,
            node_domain,
        ]
    )
    bucket = _stable_index(key, 100)
    if dim == "重难点":
        threshold = 22 if has_trigger else 0
    elif dim == "进度":
        threshold = 12 if has_trigger else 0
    else:
        threshold = 10 if has_trigger else 0
    if node_domain in {"digital", "management", "mep", "hydraulic"}:
        threshold += 3
    return bucket < threshold


def _is_drawing_related(node: Dict[str, Any], merged_text: str) -> bool:
    if any(k in merged_text for k in ("图纸", "cad", "dxf", "图层", "尺寸线")):
        return True
    if str(node.get("data_source_type") or "").upper() == "DXF":
        return True
    return False


def _choose_source_hierarchy(node: Dict[str, Any], dim: str, node_domain: str, file_stem: str) -> str:
    refs_raw = node.get("reference_standard")
    refs: List[str] = []
    if isinstance(refs_raw, list):
        refs = [str(x).strip() for x in refs_raw if str(x).strip()]
    elif isinstance(refs_raw, str) and refs_raw.strip():
        refs = [refs_raw.strip()]

    merged = " ".join(
        [
            str(file_stem or ""),
            str(node.get("name") or ""),
            str(node.get("title") or ""),
            json.dumps(node.get("content") or {}, ensure_ascii=False),
            json.dumps(node.get("qt_tag") or [], ensure_ascii=False),
            json.dumps(node.get("keywords") or [], ensure_ascii=False),
        ]
    ).lower()

    if _is_answer_related(node=node, dim=dim, merged_text=merged, node_domain=node_domain, file_stem=file_stem):
        return "答疑文件"
    if _is_drawing_related(node, merged):
        return "设计图纸"

    tiers = [_reference_tier(ref) for ref in refs]
    has_gb = "国标" in tiers
    has_industry = "行标" in tiers
    has_enterprise = "企标" in tiers

    if dim in {"安全", "环保"} and has_industry:
        return "行标"
    if node_domain in {"road", "bridge", "tunnel", "railway", "hydraulic", "earthwork"} and has_industry:
        return "行标"
    if has_gb:
        return "国标"
    if has_industry:
        return "行标"
    if has_enterprise:
        return "企标"
    return "企标"


def _ensure_source_hierarchy(node: Dict[str, Any], dim: str, node_domain: str, file_stem: str) -> Tuple[int, str]:
    changed = 0
    derived = _choose_source_hierarchy(node=node, dim=dim, node_domain=node_domain, file_stem=file_stem)
    current = str(node.get("source_hierarchy") or "").strip()
    if current in AUTHORITY_CHAIN:
        source = derived if derived in {"答疑文件", "设计图纸"} else current
    else:
        source = derived

    if node.get("source_hierarchy") != source:
        node["source_hierarchy"] = source
        changed += 1

    if node.get("source_hierarchy_chain") != AUTHORITY_CHAIN:
        node["source_hierarchy_chain"] = list(AUTHORITY_CHAIN)
        changed += 1

    source_candidates = [source]
    refs_raw = node.get("reference_standard")
    refs = refs_raw if isinstance(refs_raw, list) else [refs_raw] if isinstance(refs_raw, str) else []
    for ref in refs:
        tier = _reference_tier(str(ref))
        if tier and tier not in source_candidates:
            source_candidates.append(tier)

    if node.get("source_candidates") != source_candidates:
        node["source_candidates"] = source_candidates
        changed += 1

    return changed, source


def _build_operation_desc(node_name: str, dim: str, checker: str, params: Dict[str, Any]) -> str:
    param_items = [f"{k}={v}" for k, v in list(params.items())[:3]]
    param_text = "、".join(param_items) if param_items else "关键参数=基线值"
    risk_hint = "质量通病与安全隐患" if dim in {"质量", "安全", "重难点"} else "工期偏差与资源冲突"
    return (
        f"第一步（定义）：执行{node_name}{dim}工序定义，参数{param_text}，{checker}每班次核验1次；"
        f"第二步（分析）：识别{risk_hint}，风险阈值5%，技术负责人复核；"
        f"第三步（解决）：执行参数化控制与验证，偏差处置时限4h，{checker}每班次检查2次；"
        "工序名称->参数->风险->控制->验证"
    )


def _build_activation_signal(dim: str, node_domain: str, node_name: str) -> str:
    base = "Context CONTAINS '智飞工程'"
    dim_part = f"AND query_keywords_hit >= 2 AND keyword_any({dim})"
    domain_part = f"AND domain_hint == '{node_domain}'"
    name_part = f"AND node_hint CONTAINS '{str(node_name)[:8]}'"
    return f"{base} {dim_part} {domain_part} {name_part}"


def _ensure_tactical(node: Dict[str, Any], dim: str, node_domain: str) -> int:
    changed = 0
    content = node.get("content")
    if not isinstance(content, dict):
        content = {}
        node["content"] = content
        changed += 1

    env = content.get("environment_sensing")
    if not isinstance(env, dict):
        env = {}
        content["environment_sensing"] = env
        changed += 1

    node_name = str(node.get("name") or node.get("title") or "关键工序").strip()
    signal = _build_activation_signal(dim=dim, node_domain=node_domain, node_name=node_name)
    if str(env.get("activation_signal") or "").strip() != signal:
        env["activation_signal"] = signal
        changed += 1

    premium = content.get("operation_desc_premium")
    if not isinstance(premium, dict):
        premium = {}
        content["operation_desc_premium"] = premium
        changed += 1

    checker = CHECKER_BY_DIMENSION.get(dim, "施工员")
    params = PARAMS_BY_DIMENSION.get(dim, PARAMS_BY_DIMENSION["质量"])

    desc = str(premium.get("desc") or "").strip()
    if (not desc) or (any(w in desc for w in VAGUE_WORDS) and not re.search(r"\d", desc)):
        premium["desc"] = _build_operation_desc(node_name=node_name, dim=dim, checker=checker, params=params)
        changed += 1

    if not str(content.get("operation_desc_mediocre") or "").strip():
        content["operation_desc_mediocre"] = f"执行{node_name}常规作业，按参数阈值与检查岗位完成闭环复核。"
        changed += 1

    strategy = premium.get("bid_response_strategy")
    if not isinstance(strategy, dict) or not strategy:
        strategy = {
            "response_template": f"围绕{node_name}执行 Action+Parameter+Checker 闭环，优先响应{dim}评分点。",
            "dimension": dim,
            "domain": node_domain,
            "evidence_binding": "numeric_sources + formula_expression",
        }
        premium["bid_response_strategy"] = strategy
        changed += 1

    shield = premium.get("competitor_shield")
    if not isinstance(shield, dict) or not shield:
        shield = {
            "target_rival": "Competitor_Generic",
            "trap_logic": f"若{node_name}缺少参数来源或检查岗位将触发失分；本节点通过量化阈值+复核闭环进行防御。",
            "defense_action": "参数化证据链锁定",
        }
        premium["competitor_shield"] = shield
        changed += 1

    booster = premium.get("qt_score_booster")
    if not isinstance(booster, dict) or not booster:
        booster = {
            "policy_alignment": [dim, node_domain, "数字建造"],
            "score_weight": "+3_Points",
        }
        premium["qt_score_booster"] = booster
        changed += 1

    if not isinstance(node.get("bid_response_strategy"), dict) or not node.get("bid_response_strategy"):
        node["bid_response_strategy"] = strategy
        changed += 1
    if not isinstance(node.get("competitor_shield"), dict) or not node.get("competitor_shield"):
        node["competitor_shield"] = shield
        changed += 1
    if not isinstance(node.get("qt_score_booster"), dict) or not node.get("qt_score_booster"):
        node["qt_score_booster"] = booster
        changed += 1

    return changed


def _choose_formula(dim: str, node_domain: str, node_id: str, node_name: str) -> Tuple[str, List[str]]:
    pool = FORMULA_POOL_BY_DIM.get(dim, FORMULA_POOL_BY_DIM["质量"])
    idx = _stable_index(f"{dim}|{node_domain}|{node_id}|{node_name}", len(pool))
    return pool[idx]


def _ensure_formula(node: Dict[str, Any], dim: str, node_domain: str) -> Tuple[int, int, bool]:
    changed = 0
    var_fix = 0
    diversified = False

    node_id = str(node.get("node_id") or "")
    node_name = str(node.get("name") or node.get("title") or "")
    desired_expr, desired_vars = _choose_formula(dim=dim, node_domain=node_domain, node_id=node_id, node_name=node_name)

    expr = str(node.get("formula_expression") or "").strip()
    if (not expr) or (expr in LEGACY_GENERIC_FORMULAS):
        if expr != desired_expr:
            node["formula_expression"] = desired_expr
            expr = desired_expr
            changed += 1
            diversified = True
    elif expr in CANONICAL_POOL_EXPRESSIONS and expr != desired_expr:
        # Canonical default formulas should follow deterministic distribution to improve diversity.
        node["formula_expression"] = desired_expr
        expr = desired_expr
        changed += 1
        diversified = True

    vars_in_expr = _extract_formula_vars(expr)
    if not vars_in_expr:
        vars_in_expr = list(desired_vars)
        node["formula_expression"] = desired_expr
        changed += 1

    current_vars = [str(x).strip() for x in _coerce_list(node.get("formula_variables")) if str(x).strip()]
    if sorted(set(current_vars)) != sorted(vars_in_expr):
        node["formula_variables"] = list(vars_in_expr)
        changed += 1
        var_fix += 1

    numeric_sources = node.get("numeric_sources")
    if not isinstance(numeric_sources, list):
        numeric_sources = []
        node["numeric_sources"] = numeric_sources
        changed += 1

    existing_params = {
        _normalize_text(item.get("parameter"))
        for item in numeric_sources
        if isinstance(item, dict) and str(item.get("parameter") or "").strip()
    }
    for var in vars_in_expr:
        if _normalize_text(var) in existing_params:
            continue
        default_value = DEFAULT_VAR_VALUES.get(var, 1)
        numeric_sources.append(
            {
                "parameter": var,
                "value": str(default_value),
                "unit": "",
                "source_text": "kg_strengthen_v2_default",
            }
        )
        changed += 1

    return changed, var_fix, diversified


def _ensure_resource_model(
    node: Dict[str, Any],
    *,
    dim: str,
    node_domain: str,
    source_hierarchy: str,
    formula_vars: List[str],
) -> int:
    current = node.get("resource_requirements")
    base = current if isinstance(current, dict) else {}
    before = json.dumps(base, ensure_ascii=False, sort_keys=True)
    req = dict(base)

    profile = RESOURCE_PROFILE_BY_DIM.get(dim, RESOURCE_PROFILE_BY_DIM["质量"])
    man = req.get("manpower")
    man = dict(man) if isinstance(man, dict) else {}
    man.setdefault("checker_role", profile["checker_role"])
    man.setdefault("crew_size", profile["crew_size"])
    req["manpower"] = man

    eq = req.get("equipment")
    eq = dict(eq) if isinstance(eq, dict) else {}
    eq_profile = EQUIPMENT_PROFILE_BY_DOMAIN.get(node_domain, EQUIPMENT_PROFILE_BY_DOMAIN["building"])
    eq.setdefault("primary", list(eq_profile["primary"]))
    eq.setdefault("backup", list(eq_profile["backup"]))
    req["equipment"] = eq

    mat = req.get("material")
    mat = dict(mat) if isinstance(mat, dict) else {}
    mat_profile = MATERIAL_PROFILE_BY_DIM.get(dim, MATERIAL_PROFILE_BY_DIM["质量"])
    for k, v in mat_profile.items():
        mat.setdefault(k, v)
    req["material"] = mat

    req.setdefault("inspection_frequency", profile["inspection_frequency"])

    model = req.get("productivity_model")
    model = dict(model) if isinstance(model, dict) else {}
    model.setdefault("formula_variables", list(formula_vars))
    model.setdefault("calibration_source", source_hierarchy)
    model.setdefault("assumption", "资源随工序强度动态调整")
    req["productivity_model"] = model

    after = json.dumps(req, ensure_ascii=False, sort_keys=True)
    if before != after or not isinstance(current, dict):
        node["resource_requirements"] = req
        return 1
    return 0


def _ensure_schedule_indices_and_scoring(
    node: Dict[str, Any],
    *,
    dim: str,
    node_domain: str,
    source_hierarchy: str,
) -> int:
    changed = 0

    schedule_raw = node.get("schedule_constraints")
    schedule = dict(schedule_raw) if isinstance(schedule_raw, dict) else {}
    before_schedule = json.dumps(schedule, ensure_ascii=False, sort_keys=True)

    sched_profile = SCHEDULE_BASELINE_BY_DIM.get(dim, SCHEDULE_BASELINE_BY_DIM["质量"])
    schedule.setdefault("min_process_interval_days", int(sched_profile["min_process_interval_days"]))
    schedule.setdefault("max_recovery_hours", int(sched_profile["max_recovery_hours"]))
    schedule.setdefault(
        "critical_path_hint",
        list(CRITICAL_PATH_HINT_BY_DOMAIN.get(node_domain, CRITICAL_PATH_HINT_BY_DOMAIN["building"])),
    )
    schedule.setdefault("risk_trigger_threshold_percent", 5 if dim in {"质量", "安全", "重难点"} else 8)
    schedule.setdefault("source_hierarchy", source_hierarchy)

    after_schedule = json.dumps(schedule, ensure_ascii=False, sort_keys=True)
    if before_schedule != after_schedule or not isinstance(schedule_raw, dict):
        node["schedule_constraints"] = schedule
        changed += 1

    idx_raw = node.get("quantitative_indices")
    idx_map = dict(idx_raw) if isinstance(idx_raw, dict) else {}
    before_idx = json.dumps(idx_map, ensure_ascii=False, sort_keys=True)
    idx_profile = QUANT_INDEX_BASE_BY_DIM.get(dim, QUANT_INDEX_BASE_BY_DIM["质量"])
    idx_map.setdefault("duration_index", round(float(idx_profile["duration_index"]), 4))
    idx_map.setdefault("risk_index", round(float(idx_profile["risk_index"]), 4))
    idx_map.setdefault("resource_density_index", round(float(idx_profile["resource_density_index"]), 4))
    idx_map.setdefault("source_confidence_index", round(float(SOURCE_CONFIDENCE.get(source_hierarchy, 0.7)), 4))
    after_idx = json.dumps(idx_map, ensure_ascii=False, sort_keys=True)
    if before_idx != after_idx or not isinstance(idx_raw, dict):
        node["quantitative_indices"] = idx_map
        changed += 1

    sp_raw = node.get("scoring_points")
    if isinstance(sp_raw, dict):
        sp = dict(sp_raw)
        raw_checkpoints = sp.get("checkpoints")
        if not isinstance(raw_checkpoints, list):
            raw_checkpoints = []
    elif isinstance(sp_raw, list):
        sp = {}
        raw_checkpoints = list(sp_raw)
    else:
        sp = {}
        raw_checkpoints = []
    before_sp = json.dumps(sp, ensure_ascii=False, sort_keys=True)
    checkpoints: List[Dict[str, Any]] = []
    for idx, cp in enumerate(raw_checkpoints, start=1):
        item = cp
        if isinstance(cp, str):
            raw = cp.strip()
            if not raw:
                continue
            if raw.startswith("{") and raw.endswith("}"):
                try:
                    parsed = ast.literal_eval(raw)
                except (SyntaxError, ValueError):
                    parsed = None
                if isinstance(parsed, dict):
                    item = parsed
                else:
                    item = {"description": raw}
            else:
                item = {"description": raw}
        if not isinstance(item, dict):
            continue
        point_dim = str(item.get("dimension") or dim).strip()
        if point_dim not in DIMENSION_KEYWORDS:
            point_dim = dim
        req_keywords = item.get("required_keywords")
        if not isinstance(req_keywords, list):
            req_keywords = item.get("keywords")
        req_keywords = [str(k).strip() for k in (req_keywords or []) if str(k).strip()]
        if not req_keywords:
            req_keywords = list(DIMENSION_KEYWORDS.get(point_dim, DIMENSION_KEYWORDS["质量"])[:6])
        checkpoints.append(
            {
                "point_id": str(item.get("point_id") or f"{point_dim}-NODE-{idx}"),
                "dimension": point_dim,
                "description": str(item.get("description") or f"{point_dim}评分点响应"),
                "required_keywords": req_keywords,
                "match_mode": str(item.get("match_mode") or "any"),
                "boolean_rule": str(item.get("boolean_rule") or "any_keyword_hit"),
            }
        )
    if not checkpoints:
        checkpoints.append(
            {
                "point_id": f"{dim}-NODE",
                "dimension": dim,
                "description": f"{dim}评分点响应",
                "required_keywords": list(DIMENSION_KEYWORDS.get(dim, DIMENSION_KEYWORDS["质量"])[:6]),
                "match_mode": "any",
                "boolean_rule": "any_keyword_hit",
            }
        )
    sp["checkpoints"] = checkpoints
    sp.setdefault("dimension", dim)
    sp.setdefault("expected_gain", "+2~+5")
    sp.setdefault("deduction_risk", "缺少参数来源、缺少检查岗位或缺少响应闭环将触发扣分")
    sp.setdefault("score_path", "工序名称->参数->风险->控制->验证")
    after_sp = json.dumps(sp, ensure_ascii=False, sort_keys=True)
    if before_sp != after_sp or not isinstance(sp_raw, dict):
        node["scoring_points"] = sp
        changed += 1

    hooks_raw = node.get("fail_fast_hooks")
    if isinstance(hooks_raw, dict):
        hooks = dict(hooks_raw)
        events_raw = hooks.get("events")
    elif isinstance(hooks_raw, list):
        hooks = {}
        events_raw = hooks_raw
    else:
        hooks = {}
        events_raw = []
    events = [str(x).strip() for x in (events_raw or []) if str(x).strip()]
    before_hooks = json.dumps(hooks, ensure_ascii=False, sort_keys=True)
    for hook in ("missing_numeric_source", "missing_formula_expression", "missing_checker"):
        if hook not in events:
            events.append(hook)
    hooks["events"] = events
    hooks.setdefault("enabled", True)
    hooks.setdefault("on_missing_response", "raise_exception_and_retry")
    hooks.setdefault("cache_policy", "clear_failed_dimension_cache")
    hooks.setdefault("max_retry", 3)
    after_hooks = json.dumps(hooks, ensure_ascii=False, sort_keys=True)
    if before_hooks != after_hooks or not isinstance(hooks_raw, dict):
        node["fail_fast_hooks"] = hooks
        changed += 1

    return changed


def _ensure_retrieval_hints(node: Dict[str, Any], *, dim: str, node_domain: str) -> int:
    hints_raw = node.get("retrieval_hints")
    hints = dict(hints_raw) if isinstance(hints_raw, dict) else {}
    before = json.dumps(hints, ensure_ascii=False, sort_keys=True)

    node_name = str(node.get("name") or node.get("title") or "").strip()
    qt_tag = node.get("qt_tag")
    if isinstance(qt_tag, list):
        qt_terms = [str(x).strip() for x in qt_tag if str(x).strip()]
    elif str(qt_tag or "").strip():
        qt_terms = [str(qt_tag).strip()]
    else:
        qt_terms = []

    must = hints.get("must_keywords")
    if isinstance(must, list):
        must_terms = [str(x).strip() for x in must if str(x).strip()]
    else:
        must_terms = []
    must_terms.extend([dim, node_domain])
    if node_name:
        must_terms.append(node_name[:8])
    hints["must_keywords"] = _unique_keep_order(must_terms)[:10]

    optional = hints.get("optional_keywords")
    if isinstance(optional, list):
        optional_terms = [str(x).strip() for x in optional if str(x).strip()]
    else:
        optional_terms = []
    optional_terms.extend(qt_terms)
    hints["optional_keywords"] = _unique_keep_order(optional_terms)[:12]

    negative = hints.get("negative_keywords")
    if isinstance(negative, list):
        negative_terms = [str(x).strip() for x in negative if str(x).strip()]
    else:
        negative_terms = []
    negative_terms.extend(["空话", "套话", "无参数", "泛化描述"])
    hints["negative_keywords"] = _unique_keep_order(negative_terms)

    after = json.dumps(hints, ensure_ascii=False, sort_keys=True)
    if before != after or not isinstance(hints_raw, dict):
        node["retrieval_hints"] = hints
        return 1
    return 0


def _ensure_standards(node: Dict[str, Any], node_domain: str, dim: str, source_hierarchy: str, node_key: str) -> int:
    changed = 0
    refs_raw = node.get("reference_standard")
    refs: List[str] = []
    if isinstance(refs_raw, list):
        refs = [str(x).strip() for x in refs_raw if str(x).strip()]
    elif isinstance(refs_raw, str) and refs_raw.strip():
        refs = [refs_raw.strip()]

    domain_candidates = DOMAIN_STANDARDS.get(node_domain, [])
    dim_candidates = DIMENSION_STANDARDS.get(dim, [])

    refs = [x for x in refs if ("Q&A-项目答疑纪要" not in x and "设计图纸-施工图版本" not in x)]

    if domain_candidates:
        refs.append(domain_candidates[_stable_index(f"{node_key}|domain", len(domain_candidates))])
    if dim_candidates:
        refs.append(dim_candidates[_stable_index(f"{node_key}|dim", len(dim_candidates))])

    if source_hierarchy == "答疑文件":
        refs.append("Q&A-项目答疑纪要(以最新答疑为准)")
    elif source_hierarchy == "设计图纸":
        refs.append("设计图纸-施工图版本(以最新设计变更为准)")

    refs = _unique_keep_order(refs)
    if not refs:
        refs = ["GB/T 50326-2017 建设工程项目管理规范"]

    if node.get("reference_standard") != refs:
        node["reference_standard"] = refs
        changed += 1

    if "is_auto_generated" not in node:
        node["is_auto_generated"] = False
        changed += 1

    return changed


def _infer_stage(node: Dict[str, Any]) -> int:
    text = json.dumps(node, ensure_ascii=False).lower()
    best_stage = 3
    best_score = -1
    for stage, kws in PROCESS_STAGE_RULES:
        score = sum(1 for kw in kws if kw.lower() in text)
        if score > best_score:
            best_stage = stage
            best_score = score
    return best_stage


def _normalize_rel_targets(value: Any) -> List[str]:
    raw = _coerce_list(value)
    out = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return _unique_keep_order(out)


def _nearest_index(candidates: List[int], idx: int) -> int:
    if not candidates:
        return -1
    best = candidates[0]
    best_dist = abs(candidates[0] - idx)
    for i in candidates[1:]:
        dist = abs(i - idx)
        if dist < best_dist:
            best = i
            best_dist = dist
    return best


def _ensure_relations(section_nodes: List[Dict[str, Any]]) -> int:
    changed = 0

    node_ids: List[str] = []
    stages: List[int] = []
    dims: List[str] = []
    texts: List[str] = []

    for idx, node in enumerate(section_nodes):
        node_id = str(node.get("node_id") or "").strip()
        if not node_id:
            node_id = f"AUTO-NODE-{idx + 1:03d}"
            node["node_id"] = node_id
            changed += 1
        node_ids.append(node_id)
        stages.append(_infer_stage(node))
        dims.append(_infer_dimension(node))
        texts.append(json.dumps(node, ensure_ascii=False))

    safety_nodes = [i for i, d in enumerate(dims) if d in {"安全", "环保"}]
    quality_nodes = [i for i, d in enumerate(dims) if d == "质量"]

    for idx, node in enumerate(section_nodes):
        cur_id = node_ids[idx]
        cur_stage = stages[idx]
        cur_dim = dims[idx]
        cur_text = texts[idx]

        requires = _normalize_rel_targets(node.get("requires"))
        mitigates = _normalize_rel_targets(node.get("mitigates"))
        conflicts = _normalize_rel_targets(node.get("conflicts_with"))

        if not requires:
            prev_candidates = [j for j in range(idx) if stages[j] <= cur_stage]
            if prev_candidates:
                prev_idx = max(prev_candidates, key=lambda j: (stages[j], j))
                requires.append(node_ids[prev_idx])
            elif idx > 0:
                requires.append(node_ids[idx - 1])

        if cur_dim in {"安全", "环保"}:
            prev_non_safety = [j for j in range(idx - 1, -1, -1) if dims[j] not in {"安全", "环保"}]
            next_non_safety = [j for j in range(idx + 1, len(section_nodes)) if dims[j] not in {"安全", "环保"}]
            if prev_non_safety:
                mitigates.append(node_ids[prev_non_safety[0]])
            if next_non_safety:
                mitigates.append(node_ids[next_non_safety[0]])
        else:
            if safety_nodes:
                near = _nearest_index(safety_nodes, idx)
                if near >= 0:
                    mitigates.append(node_ids[near])
            elif quality_nodes and cur_dim != "质量":
                near = _nearest_index(quality_nodes, idx)
                if near >= 0:
                    mitigates.append(node_ids[near])

        for a, b in METHOD_CONFLICT_PAIRS:
            has_a = a in cur_text
            has_b = b in cur_text
            if not has_a and not has_b:
                continue
            target_kw = b if has_a else a
            for j, text in enumerate(texts):
                if j == idx:
                    continue
                if target_kw in text:
                    conflicts.append(node_ids[j])

        if not conflicts and idx + 1 < len(section_nodes) and stages[idx + 1] == cur_stage:
            conflicts.append(node_ids[idx + 1])

        requires = [x for x in _unique_keep_order(requires) if x != cur_id]
        mitigates = [x for x in _unique_keep_order(mitigates) if x != cur_id]
        conflicts = [x for x in _unique_keep_order(conflicts) if x != cur_id]

        if node.get("requires") != requires:
            node["requires"] = requires
            changed += 1
        if node.get("mitigates") != mitigates:
            node["mitigates"] = mitigates
            changed += 1
        if node.get("conflicts_with") != conflicts:
            node["conflicts_with"] = conflicts
            changed += 1

        rel_list = [r for r in _coerce_list(node.get("relations")) if isinstance(r, dict)]
        existing = {
            (_normalize_text(r.get("type") or r.get("edge_type") or ""), _normalize_text(r.get("target") or r.get("to") or ""))
            for r in rel_list
        }

        for edge_type, targets, label in (
            ("REQUIRES", requires, "stage_predecessor"),
            ("MITIGATES", mitigates, "risk_control"),
            ("CONFLICTS_WITH", conflicts, "method_conflict"),
        ):
            for target in targets:
                key = (_normalize_text(edge_type), _normalize_text(target))
                if key in existing:
                    continue
                rel_list.append({"type": edge_type, "target": target, "edge_label": label})
                existing.add(key)
                changed += 1

        if node.get("relations") != rel_list:
            node["relations"] = rel_list
            changed += 1

    return changed


def _iter_sections(raw: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    kg = raw.get("knowledge_database")
    if not isinstance(kg, dict):
        return []
    sections: List[Tuple[str, Dict[str, Any]]] = []
    for name, section in kg.items():
        if not isinstance(section, dict):
            continue
        nodes = section.get("nodes")
        if not isinstance(nodes, list):
            section["nodes"] = []
        sections.append((str(name), section))
    return sections


def strengthen_file(path: Path) -> Dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    changed = False
    run_ts = _now_iso()

    meta = raw.get("meta")
    if not isinstance(meta, dict):
        raw["meta"] = {}
        meta = raw["meta"]
        changed = True

    if not str(meta.get("version") or "").strip():
        meta["version"] = "2.3.0"
        changed = True
    if not str(meta.get("updated_at") or "").strip():
        meta["updated_at"] = run_ts
        changed = True
    if not str(meta.get("activation_key") or "").strip():
        meta["activation_key"] = "智飞工程"
        changed = True
    if meta.get("authority_chain") != AUTHORITY_CHAIN:
        meta["authority_chain"] = list(AUTHORITY_CHAIN)
        changed = True

    sections = _iter_sections(raw)
    file_domain = _infer_file_domain(path.stem)

    node_total = 0
    node_touched = 0
    relation_changes = 0
    formula_var_fixed = 0
    formula_diversified = 0
    tactical_filled = 0
    guardrail_filled = 0
    resource_model_filled = 0
    schedule_scoring_filled = 0
    retrieval_hint_filled = 0

    source_dist = {"答疑文件": 0, "设计图纸": 0, "国标": 0, "行标": 0, "企标": 0}
    domain_dist: Dict[str, int] = {}

    for _, section in sections:
        nodes = section.get("nodes")
        if not isinstance(nodes, list):
            continue

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_total += 1
            node_changed = 0

            dim = _infer_dimension(node)
            if node.get("kg_dimension") != dim:
                node["kg_dimension"] = dim
                node_changed += 1
            node_domain = _infer_node_domain(node=node, file_domain=file_domain)
            node_changed += _ensure_domain_and_conditions(node=node, node_domain=node_domain)

            src_changed, source_hierarchy = _ensure_source_hierarchy(
                node=node,
                dim=dim,
                node_domain=node_domain,
                file_stem=path.stem,
            )
            node_changed += src_changed

            tactical_change = _ensure_tactical(node=node, dim=dim, node_domain=node_domain)
            node_changed += tactical_change
            if tactical_change > 0:
                tactical_filled += 1

            guard_change = _ensure_guardrails(node)
            node_changed += guard_change
            if guard_change > 0:
                guardrail_filled += 1

            formula_change, var_fix, diversified = _ensure_formula(node=node, dim=dim, node_domain=node_domain)
            node_changed += formula_change
            formula_var_fixed += var_fix
            if diversified:
                formula_diversified += 1

            formula_vars = [str(x).strip() for x in _coerce_list(node.get("formula_variables")) if str(x).strip()]
            resource_change = _ensure_resource_model(
                node=node,
                dim=dim,
                node_domain=node_domain,
                source_hierarchy=source_hierarchy,
                formula_vars=formula_vars,
            )
            node_changed += resource_change
            if resource_change > 0:
                resource_model_filled += 1

            schedule_change = _ensure_schedule_indices_and_scoring(
                node=node,
                dim=dim,
                node_domain=node_domain,
                source_hierarchy=source_hierarchy,
            )
            node_changed += schedule_change
            if schedule_change > 0:
                schedule_scoring_filled += 1

            retrieval_change = _ensure_retrieval_hints(node=node, dim=dim, node_domain=node_domain)
            node_changed += retrieval_change
            if retrieval_change > 0:
                retrieval_hint_filled += 1

            node_key = f"{path.stem}|{node.get('node_id') or node.get('name') or node_total}"
            node_changed += _ensure_standards(
                node=node,
                node_domain=node_domain,
                dim=dim,
                source_hierarchy=source_hierarchy,
                node_key=node_key,
            )

            # Standards enrichment can introduce new domain signals; normalize aliases in the same run.
            node_changed += _ensure_domain_and_conditions(node=node, node_domain=node_domain)

            post_source_change, source_hierarchy = _ensure_source_hierarchy(
                node=node,
                dim=dim,
                node_domain=node_domain,
                file_stem=path.stem,
            )
            node_changed += post_source_change

            source_dist[source_hierarchy] = source_dist.get(source_hierarchy, 0) + 1
            domain_dist[node_domain] = domain_dist.get(node_domain, 0) + 1

            if node_changed > 0:
                node_touched += 1
                changed = True

        rel_change = _ensure_relations(nodes)
        relation_changes += rel_change
        if rel_change > 0:
            changed = True

    if changed:
        if meta.get("updated_at") != run_ts:
            meta["updated_at"] = run_ts
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "file": path.name,
        "changed": changed,
        "nodes": node_total,
        "nodes_touched": node_touched,
        "relation_changes": relation_changes,
        "formula_var_fixed": formula_var_fixed,
        "formula_diversified": formula_diversified,
        "tactical_filled_nodes": tactical_filled,
        "guardrail_filled_nodes": guardrail_filled,
        "resource_model_filled_nodes": resource_model_filled,
        "schedule_scoring_filled_nodes": schedule_scoring_filled,
        "retrieval_hint_filled_nodes": retrieval_hint_filled,
        "domain": file_domain,
        "source_distribution": source_dist,
        "node_domain_distribution": domain_dist,
    }


def render_report(rows: List[Dict[str, Any]], report_json: Path, report_md: Path, kg_root: Path) -> None:
    source_distribution = {k: 0 for k in AUTHORITY_CHAIN}
    domain_distribution: Dict[str, int] = {}

    for row in rows:
        for k, v in (row.get("source_distribution") or {}).items():
            source_distribution[k] = source_distribution.get(k, 0) + int(v)
        for k, v in (row.get("node_domain_distribution") or {}).items():
            domain_distribution[k] = domain_distribution.get(k, 0) + int(v)

    summary = {
        "generated_at": _now_iso(),
        "kg_root": str(kg_root),
        "files_total": len(rows),
        "files_changed": sum(1 for r in rows if r.get("changed")),
        "nodes_total": sum(int(r.get("nodes", 0)) for r in rows),
        "nodes_touched": sum(int(r.get("nodes_touched", 0)) for r in rows),
        "relation_changes": sum(int(r.get("relation_changes", 0)) for r in rows),
        "formula_var_fixed": sum(int(r.get("formula_var_fixed", 0)) for r in rows),
        "formula_diversified": sum(int(r.get("formula_diversified", 0)) for r in rows),
        "tactical_filled_nodes": sum(int(r.get("tactical_filled_nodes", 0)) for r in rows),
        "guardrail_filled_nodes": sum(int(r.get("guardrail_filled_nodes", 0)) for r in rows),
        "resource_model_filled_nodes": sum(int(r.get("resource_model_filled_nodes", 0)) for r in rows),
        "schedule_scoring_filled_nodes": sum(int(r.get("schedule_scoring_filled_nodes", 0)) for r in rows),
        "retrieval_hint_filled_nodes": sum(int(r.get("retrieval_hint_filled_nodes", 0)) for r in rows),
        "source_distribution": source_distribution,
        "domain_distribution": domain_distribution,
    }

    payload = {
        "summary": summary,
        "files": rows,
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# KG Strengthening Report v2")
    lines.append("")
    lines.append(f"- Generated At: {summary['generated_at']}")
    lines.append(f"- KG Root: {summary['kg_root']}")
    lines.append(f"- Files Total: {summary['files_total']}")
    lines.append(f"- Files Changed: {summary['files_changed']}")
    lines.append(f"- Nodes Total: {summary['nodes_total']}")
    lines.append(f"- Nodes Touched: {summary['nodes_touched']}")
    lines.append(f"- Relation Changes: {summary['relation_changes']}")
    lines.append(f"- Formula Variable Fixes: {summary['formula_var_fixed']}")
    lines.append(f"- Formula Diversified Nodes: {summary['formula_diversified']}")
    lines.append(f"- Tactical Filled Nodes: {summary['tactical_filled_nodes']}")
    lines.append(f"- Guardrail Filled Nodes: {summary['guardrail_filled_nodes']}")
    lines.append(f"- Resource Model Filled Nodes: {summary['resource_model_filled_nodes']}")
    lines.append(f"- Schedule/Scoring Filled Nodes: {summary['schedule_scoring_filled_nodes']}")
    lines.append(f"- Retrieval Hints Filled Nodes: {summary['retrieval_hint_filled_nodes']}")
    lines.append(f"- Source Distribution: {summary['source_distribution']}")
    lines.append(f"- Domain Distribution: {summary['domain_distribution']}")
    lines.append("")
    lines.append("| File | Domain | Changed | Nodes | Touched | Relations | FormulaVarFix | FormulaDiversified |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|")
    for row in rows:
        lines.append(
            f"| {row['file']} | {row['domain']} | {row['changed']} | {row['nodes']} | {row['nodes_touched']} | {row['relation_changes']} | {row['formula_var_fixed']} | {row['formula_diversified']} |"
        )

    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Strengthen tactical KG json files for production retrieval quality.")
    parser.add_argument("--kg-root", default=str(DEFAULT_KG_ROOT), help="Knowledge graph root directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="Glob pattern for KG files")
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON), help="JSON report output path")
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD), help="Markdown report output path")
    args = parser.parse_args()

    kg_root = Path(args.kg_root).expanduser().resolve()
    if not kg_root.exists() or not kg_root.is_dir():
        raise FileNotFoundError(f"KG root not found: {kg_root}")

    files = sorted(kg_root.glob(args.pattern))
    if not files:
        raise FileNotFoundError(f"No files matched: {kg_root}/{args.pattern}")

    rows = [strengthen_file(path) for path in files]

    report_json = Path(args.report_json).expanduser().resolve()
    report_md = Path(args.report_md).expanduser().resolve()
    render_report(rows, report_json=report_json, report_md=report_md, kg_root=kg_root)

    print(f"files_total={len(rows)}")
    print(f"files_changed={sum(1 for r in rows if r.get('changed'))}")
    print(f"nodes_total={sum(int(r.get('nodes', 0)) for r in rows)}")
    print(f"nodes_touched={sum(int(r.get('nodes_touched', 0)) for r in rows)}")
    print(f"relation_changes={sum(int(r.get('relation_changes', 0)) for r in rows)}")
    print(f"formula_var_fixed={sum(int(r.get('formula_var_fixed', 0)) for r in rows)}")
    print(f"formula_diversified={sum(int(r.get('formula_diversified', 0)) for r in rows)}")
    print(f"resource_model_filled={sum(int(r.get('resource_model_filled_nodes', 0)) for r in rows)}")
    print(f"schedule_scoring_filled={sum(int(r.get('schedule_scoring_filled_nodes', 0)) for r in rows)}")
    print(f"retrieval_hint_filled={sum(int(r.get('retrieval_hint_filled_nodes', 0)) for r in rows)}")
    print(f"report_json={report_json}")
    print(f"report_md={report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
