from __future__ import annotations

from pathlib import Path
from typing import Any


# Canonical project types are governed by the first-level directory names under
# 知识图谱/AI知识图谱大全.  Keep 房屋建筑 first because it is the neutral UI default;
# every value below must otherwise match its directory name byte-for-byte.
PROJECT_TYPES: list[str] = [
    "房屋建筑",
    "产业园厂房房建",
    "学校房建",
    "医院专项房建",
    "养老院房建",
    "装修改造",
    "医院装修改造",
    "养老院装修改造",
    "装修改造与室外附属同步工程",
    "室外附属工程",
    "城市更新与既有建筑改造工程",
    "市政道路",
    "市政桥梁工程",
    "市政管网与污水处理",
    "市政给排水厂站工程",
    "污水处理厂",
    "景观园林工程",
    "公路工程",
    "河道整治工程",
    "水利水电",
    "高标准农田",
    "电力工程",
    "石油化工工程",
    "全能",
]


# Compatibility aliases keep old case-library/image-library records usable.
# Public API responses are normalized to the canonical names above.
_TYPE_ALIASES: dict[str, str] = {
    "房建": "房屋建筑",
    "房建工程": "房屋建筑",
    "建筑工程": "房屋建筑",
    "装修": "装修改造",
    "装饰装修": "装修改造",
    "装修工程": "装修改造",
    "市政排水": "市政管网与污水处理",
    "市政排水工程": "市政管网与污水处理",
    "综合管廊": "市政管网与污水处理",
    "市政燃气": "市政管网与污水处理",
    "市政排水站": "市政给排水厂站工程",
    "市政给排水站": "市政给排水厂站工程",
    "室外附属": "室外附属工程",
    "城市更新": "城市更新与既有建筑改造工程",
    "景观园林": "景观园林工程",
    "市政桥梁": "市政桥梁工程",
    "河道治理": "河道整治工程",
    "电力能源": "电力工程",
    "石油化工": "石油化工工程",
    "水利枢纽": "水利水电",
    "港航工程": "水利水电",
    "数据机房": "房屋建筑",
}


_TYPE_KEYWORDS: dict[str, list[str]] = {
    "房屋建筑": ["房屋建筑", "土建", "主体结构", "住宅楼", "公共建筑", "办公楼"],
    "产业园厂房房建": ["产业园", "厂房", "工业园", "生产车间", "仓库", "工业建筑"],
    "学校房建": ["学校", "校区", "教学楼", "学生公寓", "实验楼", "体育馆"],
    "医院专项房建": ["医院", "医疗建筑", "洁净手术部", "医疗气体", "放射防护", "医用专项"],
    "养老院房建": ["养老院", "养老服务", "老年公寓", "适老化", "护理院", "无障碍"],
    "装修改造": ["装修改造", "装饰装修", "精装修", "室内改造", "内装", "幕墙"],
    "医院装修改造": ["医院改造", "医院装修", "病房改造", "门诊改造", "手术室改造", "不停诊"],
    "养老院装修改造": ["养老院改造", "养老院装修", "适老化改造", "老年公寓改造"],
    "装修改造与室外附属同步工程": ["装修与室外", "装修改造与室外附属", "室内外同步", "装修附属同步"],
    "室外附属工程": ["室外附属", "附属工程", "围墙", "大门", "广场", "铺装", "室外管线"],
    "城市更新与既有建筑改造工程": ["城市更新", "既有建筑", "老旧小区", "更新改造", "加固改造", "功能提升"],
    "市政道路": ["市政道路", "城市道路", "路基", "路面", "交通导改", "沥青"],
    "市政桥梁工程": ["市政桥梁", "城市桥梁", "桥墩", "承台", "架梁", "桥面系"],
    "市政管网与污水处理": ["市政管网", "雨污分流", "排水管网", "污水管网", "检查井", "综合管廊"],
    "市政给排水厂站工程": ["给水厂", "排水泵站", "污水提升泵站", "厂站工程", "取水泵站"],
    "污水处理厂": ["污水处理厂", "污水厂", "生化池", "二沉池", "污泥处理", "水处理构筑物"],
    "景观园林工程": ["景观园林", "园林绿化", "苗木", "景观构筑", "园路", "景观照明"],
    "公路工程": ["公路工程", "高速公路", "国道", "省道", "互通", "公路桥隧"],
    "河道整治工程": ["河道整治", "河道治理", "清淤", "护岸", "堤防", "行洪"],
    "水利水电": ["水利水电", "水利工程", "水电工程", "闸门", "渠道", "坝体", "导流度汛"],
    "高标准农田": ["高标准农田", "农田建设", "灌溉排水", "田间道路", "土地平整"],
    "电力工程": ["电力工程", "变电站", "输电线路", "电缆工程", "新能源", "并网"],
    "石油化工工程": ["石油化工", "化工装置", "储罐", "工艺管线", "危化", "联锁"],
    "全能": ["综合工程", "多专业综合", "全专业", "全能"],
}


_COMMON_CLOSED_LOOP_REQUIREMENT = (
    "质量、安全、环保管控必须按‘控制点→标准→指标→频率→责任位’闭环表达，"
    "每条必须可验证且可追溯。"
)


_TYPE_FOCUS: dict[str, str] = {
    "房屋建筑": "基础、主体、二次结构、屋面、防水防渗和机电接口",
    "产业园厂房房建": "大跨度厂房、钢结构、设备基础、工业地坪和生产线接口",
    "学校房建": "教学及住宿功能、校园安全、绿色建造和交叉施工组织",
    "医院专项房建": "医疗工艺、洁净系统、医疗气体、放射防护和专项联调",
    "养老院房建": "适老化、无障碍、消防疏散、护理功能和运营移交",
    "装修改造": "拆改、样板先行、隐蔽验收、材料环保、成品保护和移交",
    "医院装修改造": "不停诊组织、感染控制、洁净改造、医疗接口和分区移交",
    "养老院装修改造": "不停业或分区施工、适老化、无障碍、降噪防尘和安全隔离",
    "装修改造与室外附属同步工程": "室内拆改与室外管网、铺装、景观的界面和同步穿插",
    "室外附属工程": "室外管线、道路铺装、围墙大门、绿化和主体工程接口",
    "城市更新与既有建筑改造工程": "既有条件复核、结构鉴定、迁改导改、分区实施和民扰控制",
    "市政道路": "路基、基层、面层、交安、管线保护和交通导改",
    "市政桥梁工程": "桩基、下部结构、上部结构架设、预应力和桥面系",
    "市政管网与污水处理": "沟槽支护、管道接口、检查井、闭水试验和系统通水",
    "市政给排水厂站工程": "厂站构筑物、设备安装、工艺管线、单机调试和联动试运行",
    "污水处理厂": "水池抗渗、工艺设备、污泥与除臭系统、联调和达标验证",
    "景观园林工程": "地形整理、土壤改良、苗木栽植、景观构筑和养护移交",
    "公路工程": "路基路面、桥涵隧道、交安、临时保通和施工交通组织",
    "河道整治工程": "导流、清淤、护岸、堤防、生态修复和行洪安全",
    "水利水电": "导流度汛、土石方、主体结构、防渗、金结机电和监测",
    "高标准农田": "土地平整、灌排工程、田间道路、农田防护和耕地质量保护",
    "电力工程": "土建接口、电气安装、保护定值、试验调试和送电并网",
    "石油化工工程": "工艺管线、设备安装、危化介质、联锁、动火及受限空间作业",
    "全能": "按招标范围识别多专业界面，并为每个专业分别形成施工与验收闭环",
}


def ordered_project_types() -> list[str]:
    return list(PROJECT_TYPES)


def project_type_catalog_root() -> Path:
    return Path(__file__).resolve().parents[2] / "知识图谱" / "AI知识图谱大全"


def normalize_project_type(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text in PROJECT_TYPES:
        return text
    if text in _TYPE_ALIASES:
        return _TYPE_ALIASES[text]

    # Prefer the longest canonical/legacy phrase to prevent a generic word such
    # as 房建 or 装修 from swallowing a more specific category.
    candidates: list[tuple[int, str]] = []
    for canonical in PROJECT_TYPES:
        if canonical in text or text in canonical:
            candidates.append((len(canonical), canonical))
    for alias, canonical in _TYPE_ALIASES.items():
        if alias in text or text in alias:
            candidates.append((len(alias), canonical))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


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
        text_parts.extend(str(x) for x in outline if str(x).strip())
    if isinstance(requirements, list):
        text_parts.extend(str(x) for x in requirements if str(x).strip())
    if isinstance(tender, dict):
        text_parts.extend(str(x) for x in (tender.get("outline") or []) if str(x).strip())
        for item in (tender.get("items") or [])[:160]:
            if isinstance(item, dict):
                text_parts.append(str(item.get("dimension") or ""))
                text_parts.extend(str(k) for k in (item.get("keywords") or [])[:10] if str(k).strip())

    corpus = "\n".join(text_parts)
    if not corpus.strip():
        return None

    scores: dict[str, int] = {project_type: 0 for project_type in PROJECT_TYPES}
    for project_type in PROJECT_TYPES:
        if project_type in corpus:
            scores[project_type] += 24
        for keyword in _TYPE_KEYWORDS.get(project_type) or []:
            if keyword and keyword in corpus:
                scores[project_type] += 3 if len(keyword) >= 4 else 2
    for alias, canonical in _TYPE_ALIASES.items():
        if alias in corpus:
            scores[canonical] += 4

    # Compound catalogue types must outrank their generic parent categories.
    # Tender titles often separate the domain and work nature with intervening
    # words (for example “医院门诊楼不停诊装修改造”), so phrase-only matching is
    # insufficient.
    if "医院" in corpus and any(word in corpus for word in ("装修", "改造")):
        scores["医院装修改造"] += 36
    if any(word in corpus for word in ("养老院", "养老服务", "老年公寓")) and any(
        word in corpus for word in ("装修", "改造")
    ):
        scores["养老院装修改造"] += 36
    if any(word in corpus for word in ("装修", "改造")) and any(
        word in corpus for word in ("室外附属", "室外工程", "室外管线")
    ):
        scores["装修改造与室外附属同步工程"] += 36

    # 全能 is an explicit fallback category, never an inference fallback.
    inferred = [(score, -PROJECT_TYPES.index(tp), tp) for tp, score in scores.items() if tp != "全能" and score > 0]
    if not inferred:
        return "全能" if "全能" in corpus else None
    inferred.sort(reverse=True)
    return inferred[0][2]


def project_type_requirements(project_type: str | None) -> list[str]:
    canonical = normalize_project_type(project_type)
    if not canonical:
        return []
    focus = _TYPE_FOCUS.get(canonical)
    requirements = []
    if focus:
        requirements.append(f"本项目类型重点覆盖：{focus}；须结合本项目资料逐项写明工序、接口和验收条件。")
    requirements.append(_COMMON_CLOSED_LOOP_REQUIREMENT)
    return requirements
