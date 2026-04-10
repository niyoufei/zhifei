from __future__ import annotations

from typing import Any


# Keep strict order as requested by the product requirement.
PROJECT_TYPES: list[str] = [
    "房建",
    "维修改造",
    "装修",
    "市政道路",
    "市政排水",
    "室外附属",
    "城市更新",
    "景观园林",
    "市政桥梁",
    "市政燃气",
    "市政排水站",
    "河道治理",
    "水利水电",
    "公路工程",
    "电力能源",
    "水利枢纽",
    "石油化工",
    "综合管廊",
    "港航工程",
    "数据机房",
]


_TYPE_KEYWORDS: dict[str, list[str]] = {
    "房建": ["房建", "建房", "房屋建筑", "土建", "主体结构", "住宅楼", "公共建筑"],
    "维修改造": ["维修改造", "维修", "改造", "翻新", "加固改造", "既有建筑改造", "修缮"],
    "装修": ["装修", "装饰", "精装修", "幕墙", "内装"],
    "市政道路": ["道路", "路基", "路面", "交安", "导改", "沥青"],
    "市政排水": ["排水", "雨污", "污水", "雨水", "管网", "检查井"],
    "室外附属": ["室外附属", "附属工程", "围墙", "大门", "广场", "铺装"],
    "城市更新": ["城市更新", "改造提升", "老旧小区", "更新改造"],
    "景观园林": ["景观", "园林", "绿化", "苗木", "景观照明"],
    "市政桥梁": ["桥梁", "桥墩", "承台", "桩基", "架梁", "预应力"],
    "市政燃气": ["燃气", "燃气管道", "调压", "燃气站", "阀井"],
    "市政排水站": ["排水站", "泵站", "污水提升", "提升泵"],
    "河道治理": ["河道", "清淤", "护岸", "堤防", "行洪"],
    "水利水电": ["水利", "水电", "闸门", "渠道", "坝体"],
    "公路工程": ["公路", "高速", "国道", "省道", "互通", "隧道"],
    "电力能源": ["电力", "能源", "变电", "电缆", "输电", "新能源"],
    "水利枢纽": ["水利枢纽", "船闸", "泄洪", "引水", "枢纽"],
    "石油化工": ["石油化工", "化工", "储罐", "工艺管线", "危化"],
    "综合管廊": ["综合管廊", "管廊", "舱室", "廊体", "支吊架"],
    "港航工程": ["港航", "码头", "航道", "疏浚", "泊位", "港池"],
    "数据机房": ["数据机房", "机房", "机柜", "UPS", "弱电", "精密空调"],
}


_COMMON_CLOSED_LOOP_REQUIREMENT = (
    "质量、安全、环保管控必须按“控制点→标准→指标→频率→责任位”闭环表达，"
    "每条必须可验证且可追溯。"
)


_TYPE_REQUIREMENTS: dict[str, list[str]] = {
    "房建": [
        "重点覆盖基础、主体、二次结构、屋面与防渗，写清关键工序控制点与验收指标。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "维修改造": [
        "重点覆盖拆除保护、既有结构复核、加固修缮、成品保护与不停用/少扰民施工组织。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "装修": [
        "重点覆盖材料进场、样板先行、隐蔽验收、成品保护与移交标准。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "市政道路": [
        "重点覆盖路基、基层、面层、交安与交通导改，给出压实度/平整度/厚度等指标。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "市政排水": [
        "重点覆盖沟槽、管道、检查井、闭水试验与通水验证。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "室外附属": [
        "重点覆盖围墙、铺装、附属设施施工与接口协调。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "城市更新": [
        "重点覆盖既有条件约束、迁改导改、分区分段与民扰控制。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "景观园林": [
        "重点覆盖地形整理、苗木栽植、土壤改良、景观构筑与养护。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "市政桥梁": [
        "重点覆盖桩基、下部结构、上部结构架设与桥面系。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "市政燃气": [
        "重点覆盖管道焊接、防腐、强度严密性试验与通气条件。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "市政排水站": [
        "重点覆盖泵站土建、机电安装、联调联试与应急工况。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "河道治理": [
        "重点覆盖清淤、护岸、堤防与行洪安全。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "水利水电": [
        "重点覆盖导流度汛、主体结构、防渗与监测。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "公路工程": [
        "重点覆盖路基路面、桥隧、交安、施工组织与保通。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "电力能源": [
        "重点覆盖电气安装、调试试运行、保护定值与并网条件。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "水利枢纽": [
        "重点覆盖枢纽调度条件、闸门启闭、泄洪与结构监测。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "石油化工": [
        "重点覆盖危化介质管理、工艺管线、联锁与动火受限空间作业。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "综合管廊": [
        "重点覆盖廊体结构、防水、舱室设备安装与运维接口。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "港航工程": [
        "重点覆盖水工结构、疏浚、航道组织与海事协同。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
    "数据机房": [
        "重点覆盖机电暖通、供配电、消防、弱电与高可用保障。",
        _COMMON_CLOSED_LOOP_REQUIREMENT,
    ],
}


def ordered_project_types() -> list[str]:
    return list(PROJECT_TYPES)


def normalize_project_type(value: str | None) -> str | None:
    s = str(value or "").strip()
    if not s:
        return None
    aliases = {
        "建房": "房建",
        "房屋建筑": "房建",
        "房屋建筑工程": "房建",
        "维修": "维修改造",
        "改造": "维修改造",
        "维修工程": "维修改造",
        "改造工程": "维修改造",
        "修缮": "维修改造",
    }
    s = aliases.get(s, s)
    if s in PROJECT_TYPES:
        return s
    for tp in PROJECT_TYPES:
        if s in tp or tp in s:
            return tp
    return None


def detect_project_type(
    *,
    topic: str | None = None,
    outline: list[str] | None = None,
    requirements: list[str] | None = None,
    tender: dict[str, Any] | None = None,
) -> str | None:
    text_parts: list[str] = []
    if topic:
        text_parts.append(str(topic))
    if isinstance(outline, list):
        text_parts.extend([str(x) for x in outline if str(x).strip()])
    if isinstance(requirements, list):
        text_parts.extend([str(x) for x in requirements if str(x).strip()])
    if isinstance(tender, dict):
        text_parts.extend([str(x) for x in (tender.get("outline") or []) if str(x).strip()])
        for it in (tender.get("items") or [])[:120]:
            if isinstance(it, dict):
                text_parts.append(str(it.get("dimension") or ""))
                text_parts.extend([str(k) for k in (it.get("keywords") or [])[:8] if str(k).strip()])

    corpus = "\n".join(text_parts)
    if not corpus.strip():
        return None

    best_tp = None
    best_score = 0
    for tp in PROJECT_TYPES:
        kws = _TYPE_KEYWORDS.get(tp) or []
        score = 0
        for kw in kws:
            if kw and kw in corpus:
                score += 1
        if score > best_score:
            best_tp = tp
            best_score = score

    return best_tp if best_score > 0 else None


def project_type_requirements(project_type: str | None) -> list[str]:
    tp = normalize_project_type(project_type)
    if not tp:
        return []
    return list(_TYPE_REQUIREMENTS.get(tp) or [_COMMON_CLOSED_LOOP_REQUIREMENT])
