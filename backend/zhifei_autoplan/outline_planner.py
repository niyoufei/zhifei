from __future__ import annotations

import re
from typing import Any, Dict, List


DEFAULT_TOTAL_PAGES = 50
MAX_TOTAL_PAGES = 2000


COMMON_CHAPTERS = [
    "编制依据与原则",
    "施工部署与组织机构",
    "施工准备与资源配置",
    "施工进度计划与工期保证措施",
    "质量保证措施",
    "安全生产保证措施",
    "文明施工与环境保护措施",
    "绿色工地与信息化管理",
    "特殊材料、危险品与劳保用品管理",
    "应急预案与响应流程",
    "季节性施工措施",
    "成品保护与竣工交付",
]


PROJECT_TYPE_EXTRA: Dict[str, List[str]] = {
    "房建": ["模板支撑与脚手架专项措施", "垂直运输与交叉作业组织"],
    "维修改造": ["既有结构复核与保护措施", "拆除加固与不停用施工组织"],
    "装修": ["成品保护与污染控制", "机电末端与装修穿插组织"],
    "市政道路": ["交通导改与保通方案", "路基路面关键工序控制"],
    "市政排水": ["沟槽支护与降排水措施", "管道闭水与通水验收方案"],
    "室外附属": ["室外综合管线与交叉作业组织"],
    "城市更新": ["既有建构筑物保护措施", "不停产/不停业施工组织"],
    "景观园林": ["苗木种植与养护计划", "园建构筑物质量控制"],
    "市政桥梁": ["桥梁下部结构施工方案", "梁体架设与支架体系控制"],
    "市政燃气": ["燃气管道带气作业控制", "防爆防火专项措施"],
    "市政排水站": ["泵站设备安装调试方案", "设备联动试运行计划"],
    "河道治理": ["导流与围堰专项方案", "防洪度汛措施"],
    "水利水电": ["导流与围堰专项方案", "大体积混凝土温控措施"],
    "公路工程": ["交通导改与保通方案", "路基路面关键工序控制"],
    "电力能源": ["电气设备吊装与调试", "带电风险隔离与许可管理"],
    "水利枢纽": ["导流与截流施工组织", "闸门机电设备安装调试"],
    "石油化工": ["防火防爆与受限空间作业", "危化品仓储与动火管理"],
    "综合管廊": ["深基坑与支护专项方案", "多专业管线综合排布"],
    "港航工程": ["水上作业安全与通航组织", "沉桩与水下结构质量控制"],
    "数据机房": ["机房环境与防静电控制", "机电系统联调与切换方案"],
}


def _norm_title(s: str) -> str:
    txt = str(s or "").strip()
    txt = re.sub(r"\s+", "", txt)
    txt = txt.replace("（", "(").replace("）", ")")
    return txt


def _title_exists(outline: List[str], title: str) -> bool:
    target = _norm_title(title)
    if not target:
        return True
    for it in outline:
        cur = _norm_title(it)
        if cur == target:
            return True
        if target in cur or cur in target:
            return True
    return False


def enrich_outline(outline: List[str], project_type: str | None = None) -> List[str]:
    """
    在不破坏招标目录顺序的前提下，补齐施工组织设计常用章节。
    """
    base = [str(x).strip() for x in (outline or []) if str(x).strip()]
    if not base:
        base = []
    out = list(base)
    for t in COMMON_CHAPTERS:
        if not _title_exists(out, t):
            out.append(t)
    for t in PROJECT_TYPE_EXTRA.get(str(project_type or "").strip(), []):
        if not _title_exists(out, t):
            out.append(t)
    return out


def _clamp_page_limit(v: Any, fallback: int = DEFAULT_TOTAL_PAGES) -> int:
    try:
        n = int(float(v))
    except Exception:
        n = int(fallback)
    return max(1, min(MAX_TOTAL_PAGES, int(n)))


def _extract_tender_page_limit(tender: Dict[str, Any] | None) -> int | None:
    if not isinstance(tender, dict):
        return None
    # 1) explicit style max_pages
    try:
        v = tender.get("style", {}).get("max_pages")
        if v is not None:
            return _clamp_page_limit(v)
    except Exception:
        pass
    # 2) global_requirements text
    for line in tender.get("global_requirements") or []:
        txt = str(line or "")
        m = re.search(r"(?:总页数|篇幅|施工组织设计).{0,12}?(?:不超过|不得超过|最多)\s*(\d{1,4})\s*页", txt)
        if m:
            return _clamp_page_limit(m.group(1))
    return None


def infer_total_page_limit(
    tender: Dict[str, Any] | None,
    default: int = DEFAULT_TOTAL_PAGES,
    *,
    override: int | None = None,
    allow_exceed_tender: bool = False,
) -> int:
    tender_limit = _extract_tender_page_limit(tender)
    override_limit = None
    try:
        if override is not None and int(override) > 0:
            override_limit = _clamp_page_limit(int(override))
    except Exception:
        override_limit = None

    # 默认合规策略：若招标已有明确上限，优先招标上限。
    if tender_limit is not None:
        if override_limit is not None and allow_exceed_tender:
            return _clamp_page_limit(max(tender_limit, override_limit))
        return tender_limit

    # 招标无明确上限时，允许用用户目标页数覆盖默认值。
    if override_limit is not None:
        return override_limit
    return _clamp_page_limit(default)


def _chapter_weight(title: str) -> float:
    t = str(title or "")
    w = 1.0
    if any(k in t for k in ("主要施工方法", "施工方案", "关键工序", "技术措施")):
        w += 2.2
    if any(k in t for k in ("工程概况", "工程特点", "总体部署")):
        w += 1.5
    if any(k in t for k in ("进度", "工期", "关键线路")):
        w += 1.2
    if any(k in t for k in ("质量", "验收")):
        w += 1.0
    if any(k in t for k in ("安全", "文明", "环保", "绿色")):
        w += 1.0
    if any(k in t for k in ("平面布置图", "总平面")):
        w += 0.8
    if any(k in t for k in ("资源", "材料", "机械", "设备", "劳动力")):
        w += 0.9
    if any(k in t for k in ("应急", "季节性", "成品保护", "交付")):
        w += 0.6
    return w


def _extract_target(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, dict):
        v = v.get("target") or v.get("pages") or v.get("page_target") or v.get("max")
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def plan_chapter_pages(
    outline: List[str],
    *,
    total_pages: int = DEFAULT_TOTAL_PAGES,
    chapter_pages: Dict[str, Any] | None = None,
) -> Dict[str, int]:
    """
    自动做章节页数规划：
    - 先尊重明确给出的章节页数；
    - 再按章节权重分配剩余页数；
    - 保证总页数不超过 total_pages。
    """
    titles = [str(x).strip() for x in (outline or []) if str(x).strip()]
    if not titles:
        return {}
    limit = max(len(titles), int(total_pages or DEFAULT_TOTAL_PAGES))
    existing = chapter_pages if isinstance(chapter_pages, dict) else {}

    result: Dict[str, int] = {}
    weights: Dict[str, float] = {}
    locked_sum = 0
    unlocked: List[str] = []

    for t in titles:
        n = _extract_target(existing.get(t))
        if n is not None:
            result[t] = max(1, n)
            locked_sum += result[t]
        else:
            unlocked.append(t)
        weights[t] = _chapter_weight(t)

    # 如果明确值已超上限，按比例压缩（每章至少1页）
    if locked_sum > limit and result:
        scale = limit / float(locked_sum)
        scaled = {k: max(1, int(round(v * scale))) for k, v in result.items()}
        cur = sum(scaled.values())
        # 调整到不超过 limit
        if cur > limit:
            order = sorted(scaled.keys(), key=lambda x: (scaled[x], weights.get(x, 1.0)), reverse=True)
            idx = 0
            while cur > limit and idx < len(order):
                key = order[idx]
                if scaled[key] > 1:
                    scaled[key] -= 1
                    cur -= 1
                else:
                    idx += 1
        result = scaled
        locked_sum = sum(result.values())

    remaining = max(0, limit - locked_sum)

    # 未锁定章节至少 1 页
    for t in unlocked:
        result[t] = 1
    remaining -= len(unlocked)
    if remaining < 0:
        # 章节太多导致超限，逐章压缩到总和=limit
        order = sorted(titles, key=lambda x: (weights.get(x, 1.0), result.get(x, 1.0)))
        cur = sum(result.values())
        idx = 0
        while cur > limit and idx < len(order):
            key = order[idx]
            if result.get(key, 1) > 1:
                result[key] -= 1
                cur -= 1
            else:
                idx += 1
        return {t: max(1, int(result.get(t, 1))) for t in titles}

    # 按权重分配剩余页数（优先分配给未显式给页数的章节）
    if remaining > 0 and unlocked:
        recipients = list(unlocked)
        sum_w = sum(weights.get(t, 1.0) for t in recipients)
        if sum_w <= 0:
            sum_w = float(len(recipients))
        extra: Dict[str, int] = {t: 0 for t in recipients}
        frac: List[tuple[float, str]] = []
        used = 0
        for t in recipients:
            raw = remaining * (weights.get(t, 1.0) / sum_w)
            n = int(raw)
            extra[t] += n
            used += n
            frac.append((raw - n, t))
        left = remaining - used
        frac.sort(reverse=True)
        for _, t in frac[:left]:
            extra[t] += 1
        for t in recipients:
            result[t] = int(result.get(t, 1) + extra.get(t, 0))

    # 兜底：确保总和不超限
    total = sum(result.values())
    if total > limit:
        order = sorted(titles, key=lambda x: (result[x], weights.get(x, 1.0)), reverse=True)
        i = 0
        while total > limit and i < len(order):
            k = order[i]
            if result[k] > 1:
                result[k] -= 1
                total -= 1
            else:
                i += 1

    return {t: max(1, int(result.get(t, 1))) for t in titles}


def recommend_chart_every_n(outline: List[str], chapter_pages: Dict[str, Any] | None = None) -> int:
    titles = [str(x).strip() for x in (outline or []) if str(x).strip()]
    if not titles:
        return 2
    pages = chapter_pages if isinstance(chapter_pages, dict) else {}
    heavy = 0
    for t in titles:
        n = _extract_target(pages.get(t)) or 1
        if n >= 4:
            heavy += 1
    ratio = heavy / max(1, len(titles))
    if ratio >= 0.45:
        return 1
    if ratio >= 0.25:
        return 2
    return 3
