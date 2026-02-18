from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


LIB_PATH = Path("backend/data/autoplan/four_new_tech_library.json")
ALIASES_PATH = Path("backend/data/autoplan/four_new_keyword_aliases.json")


@dataclass(frozen=True)
class FourNewTech:
    name: str
    category: str  # 新技术/新工艺/新材料/新设备/信息化/绿色
    keywords: List[str]
    always: bool = False
    # Optional execution fields (used by deterministic renderer)
    trades: List[str] | None = None  # e.g. 钢筋工/模板工/电工...
    roles: List[str] | None = None  # e.g. 施工员/质检员/安全员/材料员/资料员...
    steps: List[str] | None = None
    acceptance: List[str] | None = None
    invest: str | None = None
    min_score: float | None = None
    project_types: List[str] | None = None  # 房建/市政/桥隧/机电/通用

    def as_dict(self) -> Dict[str, Any]:
        out = {
            "name": self.name,
            "category": self.category,
            "keywords": list(self.keywords or []),
            "always": bool(self.always),
        }
        if self.trades:
            out["trades"] = list(self.trades)
        if self.roles:
            out["roles"] = list(self.roles)
        if self.steps:
            out["steps"] = list(self.steps)
        if self.acceptance:
            out["acceptance"] = list(self.acceptance)
        if self.invest:
            out["invest"] = str(self.invest)
        if self.min_score is not None:
            out["min_score"] = float(self.min_score)
        if self.project_types:
            out["project_types"] = list(self.project_types)
        return out


def _builtin_keyword_aliases() -> Dict[str, List[str]]:
    return {
        "铝合金模板": ["铝模", "铝模板"],
        "施工升降机": ["人货梯", "施工电梯"],
        "塔吊": ["塔式起重机"],
        "直螺纹": ["套筒连接", "机械连接"],
        "深基坑": ["基坑支护", "围护", "支护"],
        "冷却水管": ["冷却管", "通水冷却"],
        "预制": ["装配式", "PC", "PC构件", "叠合板"],
        "综合管线": ["机电综合", "管线综合", "综合排布"],
        "风管": ["通风管", "矩形风管", "镀锌风管"],
        "桥架": ["电缆桥架"],
        "沟槽": ["卡箍", "沟槽连接"],
        "喷涂": ["喷涂速凝", "速凝喷涂"],
        "噪声": ["噪音"],
        "扬尘": ["粉尘"],
        "BIM": ["三维模型", "模型深化", "三维"],
        "4D": ["四维", "进度模拟"],
        "二维码": ["QR", "QR码", "条码"],
        "实名制": ["门禁", "人脸", "考勤"],
        "UT": ["超声", "超声波探伤"],
        "MT": ["磁粉", "磁粉探伤"],
    }


def load_keyword_aliases() -> Dict[str, List[str]]:
    """
    Load editable keyword aliases for recall improvement (reducing missed triggers).
    """
    if ALIASES_PATH.exists():
        try:
            obj = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
            if isinstance(obj, dict):
                out: Dict[str, List[str]] = {}
                for k, v in obj.items():
                    kk = str(k or "").strip()
                    if not kk:
                        continue
                    if isinstance(v, str):
                        v = [v]
                    vv = [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
                    if vv:
                        out[kk] = vv[:20]
                if out:
                    return out
        except Exception:
            pass
    return _builtin_keyword_aliases()


def _infer_project_type(*, topic: str | None, outline_text: str, proc_text: str, item_text: str) -> str:
    """
    Lightweight, conservative classifier used only to bias four-new recommendations.
    """
    t = "；".join([str(topic or ""), outline_text or "", proc_text or "", item_text or ""])[:30000]
    # 桥隧 / 轨道 / 隧道
    if any(k in t for k in ("隧道", "盾构", "桥梁", "箱梁", "预应力", "T梁", "墩", "盖梁", "承台", "桩基", "台身", "支座", "钢栈桥")):
        return "桥隧"
    # 市政（道路/管网）
    if any(k in t for k in ("道路", "路基", "沥青", "管网", "雨水", "污水", "检查井", "给水", "燃气", "人行道", "路面", "路缘石")):
        return "市政"
    # 机电（安装）
    if any(k in t for k in ("电缆", "桥架", "配电", "开关柜", "变压器", "风管", "空调", "暖通", "消防", "弱电", "管线综合", "机电")):
        return "机电"
    return "房建"


def _builtin_library() -> List[FourNewTech]:
    """
    Keep this library conservative and execution-oriented:
    - Prefer items that are broadly applicable and easy to verify
    - Avoid niche equipment unless BoQ/process signals match
    """
    return [
        FourNewTech(
            name="二维码材料批次追溯 + 扫码领料",
            category="信息化",
            keywords=["二维码", "批次", "领用", "材料", "台账", "追溯"],
            always=True,
            roles=["材料员", "资料员"],
            acceptance=[
                "批次字段齐全率=100%（供应商/合格证/复验/入库/领用）",
                "扫码领料覆盖率≥95%（按领料单统计）",
                "抽查台账=1次/周（抽查=不少于10单/周）",
            ],
            project_types=["通用"],
        ),
        FourNewTech(
            name="移动端隐蔽验收 + 影像留存（带构件定位）",
            category="信息化",
            keywords=["隐蔽", "验收", "影像", "拍照", "台账", "上传"],
            always=True,
            roles=["施工员", "质检员", "资料员"],
            acceptance=[
                "隐蔽验收影像覆盖率=100%（每检验批至少3张：全景/局部/尺量）",
                "上传时效≤24h（隐蔽验收完成后）",
                "一次验收通过率{card.一次验收通过率}",
            ],
            project_types=["通用"],
        ),
        FourNewTech(
            name="实测实量APP + 激光测距/全站仪复核",
            category="新技术",
            keywords=["实测实量", "测量", "标高", "垂直度", "平整度", "复核"],
            always=False,
            trades=["测量工"],
            roles=["质检员"],
            acceptance=[
                "关键部位复核=2次/日（测量工）",
                "偏差{quant.阈值}（以项目控制指标为准）",
                "实测数据上传=1次/日；抽查台账{card.台账抽查频次}",
            ],
            project_types=["房建", "市政", "桥隧", "机电"],
        ),
        FourNewTech(
            name="扬尘在线监测 + 喷淋联动",
            category="绿色",
            keywords=["扬尘", "PM10", "喷淋", "围挡", "道路", "冲洗"],
            always=False,
        ),
        FourNewTech(
            name="噪声在线监测 + 夜间施工限时控制",
            category="绿色",
            keywords=["噪声", "夜间", "监测", "限时", "投诉"],
            always=False,
        ),
        FourNewTech(
            name="定型化临边/洞口防护 + 可视化验收挂牌",
            category="新工艺",
            keywords=["临边", "洞口", "防护", "高处", "挂牌"],
            always=False,
        ),
        FourNewTech(
            name="钢筋集中加工（加工棚）+ 半成品配送",
            category="新工艺",
            keywords=["钢筋", "加工", "半成品", "配送", "加工棚"],
            always=False,
        ),
        FourNewTech(
            name="防水卷材热风焊接 + 焊缝检漏/抽检",
            category="新工艺",
            keywords=["防水", "卷材", "热风", "焊接", "焊缝"],
            always=False,
        ),
        FourNewTech(
            name="混凝土泵送 + 温控/坍落度过程监测",
            category="新设备",
            keywords=["混凝土", "泵送", "温度", "坍落度", "浇筑"],
            always=False,
        ),
        FourNewTech(
            name="干混砂浆（预拌砂浆）+ 计量投料控制",
            category="新材料",
            keywords=["砂浆", "抹灰", "预拌", "干混", "计量"],
            always=False,
        ),
        FourNewTech(
            name="电缆机械牵引 + 放线架成套化",
            category="新设备",
            keywords=["电缆", "桥架", "牵引", "放线"],
            always=False,
        ),
    ]


def _load_from_file() -> List[FourNewTech]:
    if not LIB_PATH.exists():
        return []
    try:
        obj = json.loads(LIB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = obj.get("items") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        return []
    out: List[FourNewTech] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        cat = str(it.get("category") or "").strip()
        kws = it.get("keywords") or []
        if isinstance(kws, str):
            kws = [kws]
        kws2 = [str(x).strip() for x in kws if str(x).strip()] if isinstance(kws, list) else []
        always = bool(it.get("always", False))
        trades = it.get("trades")
        if isinstance(trades, str):
            trades = [trades]
        trades2 = [str(x).strip() for x in trades if str(x).strip()] if isinstance(trades, list) else None

        roles = it.get("roles")
        if isinstance(roles, str):
            roles = [roles]
        roles2 = [str(x).strip() for x in roles if str(x).strip()] if isinstance(roles, list) else None

        steps = it.get("steps")
        if isinstance(steps, str):
            steps = [steps]
        steps2 = [str(x).strip() for x in steps if str(x).strip()] if isinstance(steps, list) else None

        acc = it.get("acceptance")
        if isinstance(acc, str):
            acc = [acc]
        acc2 = [str(x).strip() for x in acc if str(x).strip()] if isinstance(acc, list) else None

        invest = str(it.get("invest") or "").strip() or None

        ms = it.get("min_score")
        min_score = None
        try:
            if ms is not None:
                min_score = float(ms)
        except Exception:
            min_score = None

        if name and cat and kws2:
            project_types = it.get("project_types")
            if isinstance(project_types, str):
                project_types = [project_types]
            pt2 = [str(x).strip() for x in project_types if str(x).strip()] if isinstance(project_types, list) else None
            out.append(
                FourNewTech(
                    name=name,
                    category=cat,
                    keywords=kws2[:20],
                    always=always,
                    trades=trades2[:12] if isinstance(trades2, list) and trades2 else None,
                    roles=roles2[:12] if isinstance(roles2, list) and roles2 else None,
                    steps=steps2[:12] if isinstance(steps2, list) and steps2 else None,
                    acceptance=acc2[:12] if isinstance(acc2, list) and acc2 else None,
                    invest=invest,
                    min_score=min_score,
                    project_types=pt2[:8] if isinstance(pt2, list) and pt2 else None,
                )
            )
    return out


def load_library() -> List[FourNewTech]:
    items = _load_from_file()
    if items:
        return items
    return _builtin_library()


def recommend_four_new(
    boq: Dict[str, Any] | None,
    *,
    outline: List[str] | None = None,
    limit: int = 6,
    topic: str | None = None,
    project_type: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Recommend conservative "四新技术/新工艺/新材料/新设备" items based on BoQ/process signals.
    Returns a list of dicts (safe to JSON-serialize) with matched keywords.
    """
    boq = boq if isinstance(boq, dict) else {}
    items = boq.get("items") if isinstance(boq.get("items"), list) else []
    outline = outline if isinstance(outline, list) else []

    proc_text = "；".join([str(((it or {}).get("process") or {}).get("name") or "") for it in items if isinstance(it, dict)])
    item_text = "；".join([str((it or {}).get("name") or "") for it in items if isinstance(it, dict)])[:20000]
    outline_text = "；".join([str(x) for x in outline if str(x).strip()])
    aliases = load_keyword_aliases()
    inferred_pt = _infer_project_type(topic=topic, outline_text=outline_text, proc_text=proc_text, item_text=item_text)
    pt = str(project_type or inferred_pt).strip() or inferred_pt

    lib = load_library()
    scored: List[Dict[str, Any]] = []
    for entry in lib:
        score = 0.0
        hit: List[str] = []
        for kw in entry.keywords:
            if not kw:
                continue
            variants = [kw] + list(aliases.get(kw) or [])
            best_w = 0.0
            best_hit: str | None = None
            for v in variants[:8]:
                vv = str(v or "").strip()
                if not vv:
                    continue
                if vv in proc_text:
                    best_w = max(best_w, 2.0)
                    best_hit = vv
                elif vv in item_text:
                    best_w = max(best_w, 1.0)
                    best_hit = vv if best_hit is None else best_hit
                elif vv in outline_text:
                    best_w = max(best_w, 0.8)
                    best_hit = vv if best_hit is None else best_hit
            if best_w > 0.0:
                score += float(best_w)
                hit.append(best_hit or kw)
        if entry.always:
            score += 1.5
        # Project-type bias (do not block always=True entries).
        pts = [str(x).strip() for x in (entry.project_types or []) if str(x).strip()]
        if pts and not entry.always:
            if ("通用" in pts) or ("全部" in pts) or ("全" in pts):
                pass
            elif pt in pts:
                score += 0.8
            else:
                score -= 0.8
        min_score = float(entry.min_score) if entry.min_score is not None else 2.0
        # Filter out weak matches unless it is an "always" recommendation.
        if score < min_score and not entry.always:
            continue
        scored.append(
            {
                "name": entry.name,
                "category": entry.category,
                "score": round(score, 2),
                "matched": sorted(set(hit))[:10],
                "trades": list(entry.trades or []),
                "roles": list(entry.roles or []),
                "steps": list(entry.steps or []),
                "acceptance": list(entry.acceptance or []),
                "invest": str(entry.invest or ""),
                "project_type": pt,
                "project_types": pts,
            }
        )

    scored.sort(key=lambda x: (-float(x.get("score") or 0.0), str(x.get("category") or ""), str(x.get("name") or "")))

    # Diversity: avoid selecting too many items from the same category.
    out: List[Dict[str, Any]] = []
    cat_count: Dict[str, int] = {}
    for it in scored:
        cat = str(it.get("category") or "").strip() or "其他"
        if cat_count.get(cat, 0) >= 2:
            continue
        out.append(it)
        cat_count[cat] = cat_count.get(cat, 0) + 1
        if len(out) >= max(1, int(limit or 0)):
            break
    return out


def render_four_new_recommendations(
    recs: List[Dict[str, Any]],
    *,
    quant: Dict[str, str],
    card: Dict[str, str],
    qse: Dict[str, str],
    evidence_src: str,
) -> str:
    """
    Deterministic, execution-oriented "四新技术" blocks used by auto-remediation.
    No officialese; every item includes: 适用/投入/步骤/验收指标 + 风险→控制→验证 + 记录 + 偏差处置.
    """
    out_lines: List[str] = []
    for idx, it in enumerate(recs[:6], start=1):
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        cat = str(it.get("category") or "").strip() or "新技术"
        matched = [str(x).strip() for x in (it.get("matched") or []) if str(x).strip()]
        reason = ("触发=" + "、".join(matched[:6])) if matched else "触发=清单工序匹配"

        trades = [str(x).strip() for x in (it.get("trades") or []) if str(x).strip()]
        roles = [str(x).strip() for x in (it.get("roles") or []) if str(x).strip()]
        if not roles:
            roles = ["施工员", "质检员", "安全员"]
        resp = "；".join([f"责任岗位={'/'.join(roles[:6])}"] + ([f"责任工种={'/'.join(trades[:6])}"] if trades else []))

        # Minimal but verifiable defaults
        applicable = f"适用：触发关键词={('、'.join(matched[:6]) if matched else '清单/工序匹配')}；适用范围=对应工序的样板/首件确认、过程抽检、资料归档。"
        invest = str(it.get("invest") or "").strip()
        if not invest:
            invest = f"投入：{resp}；人数={quant.get('人数','8人/班')}；设备/工具={quant.get('设备型号','20t挖机1台')}（按工序替换）；时长={quant.get('时长','4h/作业段')}。"
        else:
            invest = f"投入：{resp}；{invest}"

        step_lines = [str(x).strip() for x in (it.get("steps") or []) if str(x).strip()]
        steps = "步骤：" + "；".join(step_lines) if step_lines else "步骤：1)样板=1处/工序；2)首件确认=1次/工序；3)过程抽检按频次；4)偏差≤24h整改复验关闭；5)资料归档。"

        acc_lines = [str(x).strip() for x in (it.get("acceptance") or []) if str(x).strip()]
        accept = ""
        if acc_lines:
            accept = "验收指标：" + "；".join(acc_lines[:6])
            # Placeholder substitution (kept tiny and deterministic).
            for ck, cv in (card or {}).items():
                if not isinstance(ck, str):
                    continue
                accept = accept.replace(f"{{card.{ck}}}", str(cv))
            for qk, qv in (quant or {}).items():
                if not isinstance(qk, str):
                    continue
                accept = accept.replace(f"{{quant.{qk}}}", str(qv))
            for ek, ev in (qse or {}).items():
                if not isinstance(ek, str):
                    continue
                accept = accept.replace(f"{{qse.{ek}}}", str(ev))
        else:
            accept = f"验收指标：一次验收通过率{card.get('一次验收通过率','≥95%')}；合格率{card.get('合格率阈值','≥98%')}；台账字段齐全率=100%；上传频次=1次/日。"

        if "扬尘" in name or "PM10" in name:
            accept = f"验收指标：PM10{qse.get('PM10阈值','≤150ug/m3')}（监测=1次/日）；投诉=0次/周；记录齐全率=100%。"
        if "噪声" in name:
            accept = f"验收指标：夜间噪声{qse.get('夜间噪声阈值','≤55dB')}（监测=1次/日）；投诉=0次/周；记录齐全率=100%。"

        risk = "风险：落地不到位导致返工/停工或数据不可追溯"
        control = f"控制：交底=1次/班(施工员)+首件确认=1次/工序(质检员)+抽检={card.get('抽检频次','每100m2 1次')}(质检员)+台账抽查={card.get('台账抽查频次','1次/周')}(资料员)"
        verify = f"验证：偏差{quant.get('阈值','偏差≤5mm')}；记录=《四新技术实施与验收台账》；偏差处置：不合格项≤24h整改复验关闭"

        out_lines.append(f"- 四新#{idx}（{cat}）：{name}（{reason}）。")
        out_lines.append(f"  - {applicable}")
        out_lines.append(f"  - {invest}")
        out_lines.append(f"  - {steps}")
        out_lines.append(f"  - {accept}")
        out_lines.append(f"  - 风险→控制→验证：{risk}；{control}；{verify}。【证据:{evidence_src}】")
    return "\n".join(out_lines).strip()


def save_library_snapshot(path: str | None = None) -> str:
    """
    Write current built-in library to JSON for user editing (idempotent).
    """
    p = Path(path) if path else LIB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"items": [it.as_dict() for it in _builtin_library()]}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)
