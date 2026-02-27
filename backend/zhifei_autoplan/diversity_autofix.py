from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from backend.zhifei_autoplan.quality_check import strip_nonconcrete_language
from backend.zhifei_autoplan.params_runtime import get_boq_focus_card_defaults, get_qse_defaults, get_quant_defaults


_BLOCK_MARKERS = [
    "【清单重点项控制卡】",
    "【图纸证据定位】",
    "【企业标准证据定位】",
    "【四新技术闭环卡片",
]


def _extract_special_blocks(text: str) -> Tuple[str, List[str]]:
    """
    Pull out deterministic blocks that are allowed to be identical across variants:
    - BoQ focus control cards
    - Drawing/standard evidence bindings
    - Four-new cards
    Returns (base_text_without_blocks, blocks_in_original_order).
    """
    s = str(text or "")
    if not s:
        return "", []

    blocks: List[Tuple[int, int, str]] = []
    for mk in _BLOCK_MARKERS:
        start = 0
        while True:
            i = s.find(mk, start)
            if i < 0:
                break
            # Heuristic end: next marker or end.
            j = len(s)
            for mk2 in _BLOCK_MARKERS:
                if mk2 == mk:
                    continue
                k = s.find(mk2, i + len(mk))
                if k >= 0:
                    j = min(j, k)
            # Also stop at a big blank gap (paragraph break) to avoid eating too much.
            gap = s.find("\n\n\n", i + len(mk))
            if gap >= 0:
                j = min(j, gap)
            block = s[i:j].strip()
            if block:
                blocks.append((i, j, block))
            start = i + max(1, len(mk))

    if not blocks:
        return s.strip(), []
    blocks.sort(key=lambda x: x[0])
    out_blocks = [b for _, _, b in blocks]

    # Remove from back to front
    base = s
    for i, j, _ in sorted(blocks, key=lambda x: -x[0]):
        base = (base[:i] + "\n" + base[j:]).strip()
    return base.strip(), out_blocks


def _bullets_from_text(text: str, *, limit: int = 16) -> List[str]:
    """
    Extract concrete bullet points from text while avoiding headings.
    """
    s = strip_nonconcrete_language(str(text or ""))
    s = re.sub(r"【证据:[^】]{1,240}】", "", s)
    lines = [ln.strip(" \t-•·") for ln in s.splitlines() if ln.strip()]
    bullets: List[str] = []
    seen = set()
    for ln in lines:
        if len(ln) <= 3:
            continue
        if ln.endswith("：") and len(ln) <= 20:
            continue
        # Keep lines with numbers/units or key verbs, otherwise skip generic prose.
        if not (re.search(r"\\d", ln) or any(k in ln for k in ("频次", "阈值", "间距", "厚度", "时长", "人数", "设备", "记录", "台账", "验收", "复核", "抽检", "偏差", "整改"))):
            continue
        key = re.sub(r"\\s+", "", ln)[:120]
        if key in seen:
            continue
        seen.add(key)
        bullets.append(ln.rstrip("。；;") + "。")
        if len(bullets) >= max(4, int(limit or 0)):
            break
    return bullets


def _join_blocks(blocks: List[str]) -> str:
    cleaned = []
    for b in blocks or []:
        t = str(b or "").strip()
        if t:
            cleaned.append(t)
    return "\n\n".join(cleaned).strip()


def _general_template_text(template_id: str, params: Dict[str, Any]) -> str:
    q = get_quant_defaults(params)
    card = get_boq_focus_card_defaults(params)
    tid = str(template_id or "").strip().upper() or "A"

    if tid == "B":
        return (
            "工序流程\n"
            "- 步骤1 准备：样板=1处/工序；交底=1次/班；记录=《班前交底记录》。\n"
            f"- 步骤2 测量复核：复核=2次/日；阈值={q.get('阈值')}；记录=《测量复核记录》。\n"
            "- 步骤3 材料进场：到货验收=1次/批次；批次追溯=二维码；记录=《材料进场验收台账》。\n"
            f"- 步骤4 作业：关键参数=间距{q.get('间距')}/厚度{q.get('厚度')}；过程抽检={card.get('抽检频次')}；记录=《过程检查记录》。\n"
            f"- 步骤5 验收：一次验收通过率{card.get('一次验收通过率')}；合格率{card.get('合格率阈值')}；记录=《检验批验收记录》。\n"
            "- 步骤6 资料归档：影像+签认≤24h归档；记录=《资料移交清单》。\n"
            "\n步骤控制点表（摘要）\n"
            f"- 频次={q.get('频次')}；阈值={q.get('阈值')}；间距={q.get('间距')}；厚度={q.get('厚度')}；时长={q.get('时长')}；人数={q.get('人数')}；设备型号={q.get('设备型号')}。\n"
            "\n风险→控制→验证（按步骤）\n"
            f"- 风险：测量基准误差累积→控制：复核=2次/日+首件确认=1次/工序→验证：偏差{q.get('阈值')}；记录=《测量复核记录》；不合格≤24h复验关闭。\n"
            f"- 风险：材料批次混用→控制：批次码入库+扫码领料覆盖率≥95%→验证：台账抽查{card.get('台账抽查频次')}；记录=《材料台账》；异常≤24h闭环。\n"
        )
    if tid == "C":
        return (
            "控制指标矩阵\n"
            f"- 频次={q.get('频次')}（检查/抽检/复核）\n"
            f"- 阈值={q.get('阈值')}（偏差判定）\n"
            f"- 间距={q.get('间距')}（构造/布置）\n"
            f"- 厚度={q.get('厚度')}（保护层/做法）\n"
            f"- 时长={q.get('时长')}（作业段节拍）\n"
            f"- 人数={q.get('人数')}（班组配置）\n"
            f"- 设备型号={q.get('设备型号')}（机具能力）\n"
            "\n人机料法环落地\n"
            "- 人：岗位=施工员/质检员/安全员/材料员/资料员；交底=1次/班；复核=2次/日。\n"
            f"- 机：设备/机具按型号清单配置；日检=1次/日；异常停机≤30min处置。\n"
            f"- 料：到货验收=1次/批次；复验按规范；批次追溯=二维码。\n"
            "- 法：样板=1处/工序；首件确认=1次/工序；过程抽检按频次。\n"
            "- 环：扬尘/噪声按阈值监测；夜间施工按审批时段执行。\n"
            "\n风险→控制→验证（按维度）\n"
            f"- 质量：风险=偏差超限→控制=复核+抽检→验证=偏差{q.get('阈值')}；记录=《质量检查记录》；不合格≤24h复验关闭。\n"
            f"- 安全：风险=交叉作业碰撞→控制=区域隔离+指挥→验证=巡检{q.get('频次')}；记录=《安全巡检记录》；问题≤2h闭环。\n"
            f"- 进度：风险=节拍失衡→控制=3周滚动+资源峰值约束→验证=周计划兑现率≥90%；记录=《周计划看板》；偏差>2天触发纠偏。\n"
            f"- 成本：风险=材料损耗超标→控制=限额领料+批次追溯→验证=月度差异率≤1%；记录=《材料消耗台账》；异常≤48h纠偏。\n"
            f"- 环保：风险=PM10/噪声超阈值→控制=联动喷淋/限时→验证=阈值达标；记录=《环保监测台账》；超阈值≤30min处置。\n"
            "\n信息化与台账\n"
            "- 台账字段：部位/轴线/标高/批次/责任人/验收结论/证据定位。\n"
            "- 上传频次：1次/日；影像留存：每检验批≥3张（全景/局部/尺量）。\n"
        )
    if tid == "D":
        return (
            "资源-工序耦合表\n"
            f"- 工序=测量复核；班组={q.get('人数')}；设备={q.get('设备型号')}；单段时长={q.get('时长')}；验收阈值={q.get('阈值')}。\n"
            f"- 工序=材料进场与复验；班组=材料员+质检员；设备=扫码终端；频次={q.get('频次')}；抽检={card.get('抽检频次')}。\n"
            "- 工序=关键作业与验收；班组=施工员+质检员+安全员；资源切换=按交叉窗口执行。\n"
            "\n接口冲突清单\n"
            "- 冲突1：交叉作业抢占作业面→窗口：错峰2h→责任：施工员。\n"
            "- 冲突2：吊装与地面工序交叉→窗口：分区封锁+专人指挥→责任：安全员。\n"
            "- 冲突3：材料到场与作业面堆载冲突→窗口：分批到货+限量堆放→责任：材料员。\n"
            "\n关键路径纠偏卡\n"
            "- 触发：节点滞后>1天；动作：增配1个班组+延长作业时段；时限：24h内启动；复核：次日兑现率≥95%。\n"
            "- 触发：关键设备故障>2h；动作：启用备机+调整工序顺排；时限：2h内切换；复核：关键线路不漂移。\n"
            "\n风险→控制→验证（资源视角）\n"
            f"- 风险：资源错配导致返工；控制：班组-工序绑定+交接清单；验证：偏差{q.get('阈值')}，记录=《资源耦合检查表》；超差≤2h复验关闭。\n"
            f"- 风险：节拍失衡导致堆压；控制：滚动排产=1次/日；验证：峰值资源利用率≤95%，记录=《日排产看板》；异常≤24h纠偏关闭。\n"
        )
    if tid == "E":
        return (
            "实施场景卡片\n"
            "- 场景1 主体作业面：目标=关键工序连续作业；边界=轴线/标高/作业面编号。\n"
            "- 场景2 材料中转区：目标=批次追溯与限量堆放；边界=库区编号/通道。\n"
            "- 场景3 交叉作业区：目标=人机分流与风险隔离；边界=封控线/时间窗。\n"
            "\n参数对照表\n"
            f"- 主体作业面：频次={q.get('频次')}；阈值={q.get('阈值')}；间距={q.get('间距')}；厚度={q.get('厚度')}。\n"
            f"- 材料中转区：时长={q.get('时长')}；人数={q.get('人数')}；设备型号={q.get('设备型号')}；抽检={card.get('抽检频次')}。\n"
            "- 交叉作业区：封控半径=2m；旁站=1人/班；交接=1次/班。\n"
            "\n验收样表\n"
            "- 字段：场景编号/责任岗位/关键参数/实测值/结论/整改时限/复核人/证据定位。\n"
            "- 规则：每个场景至少1张样表，且当日归档。\n"
            "\n风险→控制→验证（场景）\n"
            f"- 场景=主体作业面；风险：参数超差；控制：首件确认+过程抽检；验证：偏差{q.get('阈值')}，记录=《场景验收样表》。\n"
            f"- 场景=材料中转区；风险：批次混用；控制：扫码领用+双人复核；验证：抽查{card.get('台账抽查频次')}，记录=《材料台账》。\n"
            "- 场景=交叉作业区；风险：人机碰撞；控制：分时分区+封控线；验证：违章=0次/日，记录=《交叉作业巡检表》。\n"
        )
    # A
    return (
        "本章交付物（可验收）\n"
        "- 样板验收记录=1份/工序；首件确认记录=1份/工序。\n"
        "- 测量复核记录=2次/日；过程检查记录按频次。\n"
        "- 材料批次台账（含合格证/复验/入库/领用）；隐蔽验收记录（影像≥3张/检验批）。\n"
        "\n约束条件（来自招标/图纸/清单）\n"
        "- 关键参数必须写入台账字段并可追溯到图纸/标准定位符。\n"
        "\n执行步骤\n"
        "- 准备：交底=1次/班；样板=1处/工序。\n"
        "- 测量复核：复核=2次/日；阈值=偏差≤5mm；记录=《测量复核记录》。\n"
        "- 材料：到货验收=1次/批次；批次追溯=二维码；记录=《材料进场验收台账》。\n"
        "- 作业：关键参数=间距/厚度；过程抽检按频次；记录=《过程检查记录》。\n"
        f"- 验收：一次验收通过率{card.get('一次验收通过率')}；资料归档≤24h。\n"
        "\n风险→控制→验证\n"
        f"- 风险：测量复核缺失→控制：复核=2次/日(测量工)+首件确认=1次/工序(质检员)→验证：偏差{q.get('阈值')}；记录=《测量复核记录》；不合格≤24h复验关闭。\n"
        f"- 风险：材料批次混用→控制：批次码入库+扫码领料覆盖率≥95%→验证：台账抽查{card.get('台账抽查频次')}；记录=《材料台账》；异常≤24h闭环。\n"
    )


def _qse_template_text(template_id: str, params: Dict[str, Any]) -> str:
    q = get_quant_defaults(params)
    card = get_boq_focus_card_defaults(params)
    qse = get_qse_defaults(params)
    tid = str(template_id or "").strip().upper() or "A"

    if tid == "B":
        return (
            "场景拆分\n"
            "- 场景1 夜间施工：噪声/照明/人员疲劳。\n"
            "- 场景2 高处作业：临边/洞口/坠落。\n"
            "- 场景3 临时用电：漏保/接地/乱拉。\n"
            "- 场景4 材料堆放与危化品：储存/标识/领用。\n"
            "\n闭环卡片（按场景）\n"
            f"- 夜间噪声：风险=噪声超标→控制=限时计划+高噪设备禁用→验证=夜间噪声{qse.get('夜间噪声阈值')}；监测=1次/日；记录=《噪声监测台账》；投诉≤2h闭环。\n"
            f"- 高处作业：风险=临边缺防护→控制=定型化防护+验收挂牌→验证=日巡检=1次/日；记录=《临边洞口验收表》；缺失≤30min补齐复验。\n"
            f"- 临时用电：风险=漏保失效→控制=漏保试跳=1次/周→验证=试跳记录齐全率=100%；记录=《临电检查表》；异常≤2h整改复检关闭。\n"
            f"- 危化品：风险=混放/泄漏→控制=分区储存+MSDS+领用登记→验证=台账抽查{card.get('台账抽查频次')}；记录=《危化品台账》；异常≤24h处置关闭。\n"
            "\n检查频次总表\n"
            f"- 日：安全巡检{q.get('频次')}；临边洞口巡检=1次/日；扬尘/噪声监测=1次/日。\n"
            "- 周：临电专项检查=1次/周；危化品台账抽查=1次/周。\n"
            "- 月：应急演练=1次/月（如招标另有要求，以招标为准）。\n"
            "\n记录表清单\n"
            "- 《安全巡检记录》/《临边洞口验收表》/《临电检查表》/《危化品台账》/《噪声监测台账》/《扬尘监测台账》。\n"
        )
    if tid == "C":
        return (
            "指标矩阵\n"
            f"- 扬尘：PM10阈值{qse.get('PM10阈值')}；频次=1次/日；责任=环保负责人；记录=《扬尘监测台账》。\n"
            f"- 噪声：夜间噪声阈值{qse.get('夜间噪声阈值')}；频次=1次/日；责任=环保负责人；记录=《噪声监测台账》。\n"
            f"- 临电：漏保试跳=1次/周；责任=电工/安全员；记录=《临电检查表》。\n"
            f"- 临边洞口：完好率=100%；巡检=1次/日；责任=安全员；记录=《临边洞口验收表》。\n"
            "\n数据闭环\n"
            "- 采集：谁=责任岗位；工具=监测设备/检查表；频次=按指标矩阵。\n"
            "- 判定：按阈值/频次判定；超阈值即触发处置。\n"
            "- 处置：动作=停工/隔离/喷淋联动/整改；时限=≤30min（高风险）或≤24h（一般）。\n"
            "- 复核：复测/复查=1次；达标后关闭。\n"
            "- 归档：台账字段齐全率=100%；上传频次=1次/日。\n"
            "\n处置与复核\n"
            f"- PM10超阈值：喷淋联动→复测≤1h；记录齐全率=100%。\n"
            f"- 临边缺防护：立即隔离→≤30min补齐→复验挂牌。\n"
        )
    if tid == "D":
        return (
            "监管红线清单\n"
            "- 红线1：高处作业未防护即作业（触发即停工）。\n"
            "- 红线2：临时用电漏保失效继续运行（触发即停用）。\n"
            "- 红线3：危化品混放/无MSDS（触发即封存整改）。\n"
            "- 红线4：扬尘噪声连续超阈值未处置（触发即升级管控）。\n"
            "\n岗位联签链\n"
            "- 发现人=班组长；处置人=施工员/电工；复核人=安全员/质检员；关闭批准=项目经理。\n"
            "- 任何红线事件必须形成联签闭环单，未联签不得销项。\n"
            "\n闭环时限表\n"
            "- 高风险：10min内处置启动，2h内复核关闭。\n"
            "- 中风险：30min内处置启动，8h内复核关闭。\n"
            "- 一般风险：2h内处置启动，24h内复核关闭。\n"
            "\n闭环卡片\n"
            f"- 风险：临边防护缺失；控制：停工隔离+补齐防护+班前复核；验证：巡检={q.get('频次')}，违章=0次/日，记录=《红线联签闭环单》；偏差处置：按高风险时限执行。\n"
            f"- 风险：噪声超限；控制：高噪设备禁用+隔声+监测；验证：夜间噪声{qse.get('夜间噪声阈值')}，记录=《噪声监测记录》；偏差处置：30min内复测达标。\n"
        )
    if tid == "E":
        return (
            "区域网格\n"
            "- 网格A：主体作业区；责任=安全员A；巡检=2次/日。\n"
            "- 网格B：材料与危化品区；责任=材料员B；巡检=2次/日。\n"
            "- 网格C：临电与设备区；责任=电工C；巡检=2次/日。\n"
            "\n班组行为清单\n"
            "- 必做：班前交底、PPE自检、作业许可确认。\n"
            "- 禁做：无证上岗、超时高噪作业、危化品混放。\n"
            "- 抽查：每班随机抽查1次，抽查记录当日归档。\n"
            "\n红黄牌处置\n"
            "- 黄牌：一般违章，2h内整改+复核。\n"
            "- 红牌：重大违章，立即停工+责任复盘，复工需项目经理签批。\n"
            "\n复核与销项\n"
            f"- 风险：PPE未按标准佩戴；控制：入场发放+班前检查=1次/班；验证：抽查{q.get('频次')}，记录=《PPE台账》；偏差处置：黄牌闭环≤2h。\n"
            f"- 风险：危化品管理缺失；控制：分区储存+MSDS+双人领用；验证：台账抽查{card.get('台账抽查频次')}，记录=《危化品台账》；偏差处置：红牌停工整改后复核销项。\n"
        )
    # A
    return (
        "闭环清单\n"
        f"- 扬尘：风险=PM10超阈值→控制=喷淋/雾炮联动→验证=PM10{qse.get('PM10阈值')}；监测=1次/日；记录=《扬尘监测台账》；超阈值≤30min处置。\n"
        f"- 噪声：风险=夜间噪声超标→控制=限时计划+设备清单→验证=夜间噪声{qse.get('夜间噪声阈值')}；监测=1次/日；记录=《噪声监测台账》；投诉≤2h闭环。\n"
        f"- 临边洞口：风险=防护缺失→控制=定型化防护+验收挂牌→验证=日巡检=1次/日；记录=《临边洞口验收表》；缺失≤30min补齐复验。\n"
        f"- 临时用电：风险=漏保失效→控制=试跳=1次/周→验证=记录齐全率=100%；记录=《临电检查表》；异常≤2h整改复检。\n"
        f"- 危化品：风险=混放/泄漏→控制=分区储存+MSDS+领用登记→验证=台账抽查{card.get('台账抽查频次')}；记录=《危化品台账》；异常≤24h处置关闭。\n"
        f"- PPE：风险=未按标准佩戴→控制=入场发放+班前检查=1次/班→验证=抽查{q.get('频次')}；记录=《PPE发放与检查台账》；违规≤2h闭环。\n"
        "\n关键控制点\n"
        "- 任何“超阈值/缺失/违规”必须生成工单并记录：问题-处置-复核-关闭。\n"
    )


def apply_diversity_autofix(
    section: Dict[str, Any],
    *,
    params: Dict[str, Any],
    evidence_hint: str | None = None,
) -> bool:
    """
    Rewrite/reshape a single section to increase structural diversity across variants.
    Deterministic and no-officialese:
    - Keep special deterministic blocks (BoQ control cards/evidence bindings/four-new) but separate them.
    - Replace narrative core with template-driven structure (A/B/C/D/E) based on section metadata.
    - Append "补充说明（来自原文要点）" as bullets extracted from the original to avoid losing specifics.
    """
    if not isinstance(section, dict):
        return False
    title = str(section.get("title") or "").strip()
    content = str(section.get("content") or "")
    if not title or not content:
        return False

    template_id = str(section.get("logic_template_id") or "").strip().upper() or "A"
    dom = str(section.get("chapter_domain") or "").strip().lower()
    dom = dom if dom in {"general", "qse"} else "general"

    base, blocks = _extract_special_blocks(content)
    bullets = _bullets_from_text(base, limit=18)

    # Preserve chapter blueprint anchors (when available) so we don't break
    # "章内结构" constraints (e.g., 工程特点/总体部署) while diversifying structure.
    bp_anchors: List[str] = []
    bp_name: str = ""
    try:
        from backend.zhifei_autoplan.chapter_blueprints import match_chapter_blueprint

        bp = match_chapter_blueprint(title)
        if isinstance(bp, dict):
            bp_name = str(bp.get("name") or "").strip()
            raw = bp.get("anchors") if isinstance(bp.get("anchors"), list) else []
            bp_anchors = [str(x).strip() for x in raw if str(x).strip()]
    except Exception:
        bp_anchors = []
        bp_name = ""

    header = ""
    if evidence_hint:
        eh = str(evidence_hint).strip()
        if eh:
            header = f"证据定位提示：{eh}（用于复核，不替代正文闭环）。\n\n"

    bp_block = ""
    if bp_anchors:
        q = get_quant_defaults(params)
        lines = []
        if bp_name:
            lines.append(f"章节结构蓝图锚点（{bp_name}）")
        else:
            lines.append("章节结构蓝图锚点")
        used = set()
        for i, anc in enumerate(bp_anchors[:6]):
            lines.append(str(anc))
            pick = ""
            for b in bullets:
                if not b or b in used:
                    continue
                if anc in b:
                    pick = b
                    break
            if not pick:
                for b in bullets:
                    if not b or b in used:
                        continue
                    pick = b
                    break
            if pick:
                used.add(pick)
                lines.append(f"- {pick.rstrip('。；;')}" + "。")
            # Always add an executable, measurable line (keeps the anchor non-empty even when bullets are scarce).
            lines.append(
                f"- 量化：频次={q.get('频次')}；阈值={q.get('阈值')}；时长={q.get('时长')}；记录=《{anc}检查表》；偏差处置=超差≤2h整改复验关闭。"
            )
        bp_block = "\n".join([ln for ln in lines if str(ln).strip()]).strip()

    if dom == "qse":
        core = _qse_template_text(template_id, params)
    else:
        core = _general_template_text(template_id, params)

    extra = ""
    if bullets:
        extra = "补充说明（来自原文要点）\n" + "\n".join([f"- {b}" for b in bullets[:18]])
    special = _join_blocks(blocks)

    parts = [header.strip(), bp_block.strip(), core.strip(), extra.strip(), special.strip()]
    new_text = "\n\n".join([p for p in parts if p]).strip() + "\n"
    new_text = strip_nonconcrete_language(new_text)

    # Only apply when it meaningfully changes structure.
    if len(new_text) < 200:
        return False
    if new_text == content.strip():
        return False

    section["content"] = new_text
    section["auto_remediated"] = "diversity_autofix"
    return True
