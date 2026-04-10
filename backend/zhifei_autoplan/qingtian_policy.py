from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


QINGTIAN_POLICY_VERSION = "2026.03.06"


# 用户明确要求的禁语（含常见变体）
QINGTIAN_BANNED_PHRASES: List[str] = [
    "按照",
    "符合",
    "确保",
    "保障",
    "严格落实",
    "加强管理",
    "有效措施",
    "合理安排",
    "现场实际情况",
    "相关规范",
    "有关规定",
]


# 无完整目录时的 16 章适配目录（保持用户给定顺序）
QINGTIAN_16_CHAPTER_OUTLINE: List[str] = [
    "总体部署与信息化管理",
    "安全管理与劳保用品配置",
    "文明施工与绿色工地",
    "材料采购、进场验收与特殊材料闭环",
    "四新技术应用",
    "关键工序控制点",
    "危大工程闭环管理",
    "质量管理体系与ITP简表",
    "进度计划体系与纠偏阈值",
    "专项方案管理与审批验收节点",
    "人力配置与培训",
    "施工流程、专业穿插与移交条件",
    "机械设备配置、验收与维保",
    "图纸会审、深化设计与变更闭环",
    "资源总控与动态调配",
    "可行性验证、样板先行与落地清单",
]


QINGTIAN_PUBLIC_TABLES: List[str] = [
    "总表A：项目总控参数表",
    "总表B：检查与会议频次表",
    "总表C：责任岗位总表",
    "总表D：风险控制总表",
    "总表E：表单台账索引",
]


QINGTIAN_GLOBAL_REQUIREMENTS: List[str] = [
    "角色=施工一线总工程师+技术交底编制人+AI评标适配优化器；输出必须可执行、可检查、可验收、可留痕。",
    "目录规则：招标文件已给出技术标目录时，严格按原顺序输出；仅允许章内补充小节/表格/控制点。",
    "目录兜底：招标目录不完整时，按系统16章适配目录编制。",
    "结构骨架：每章固定包含“适用范围与关键参数、重点难点/风险点及措施、验收与记录、引用关系”。",
    "表达骨架：控制对象→工序/场景→参数或阈值→执行动作→检查人→频次→合格标准→记录载体。",
    "缺参规则：缺少图纸/清单/参数时写“需补充（缺：××）”；可给暂定值但必须标注“【暂定】+需确认来源”。",
    "去重规则：组织架构、会议频次、整改闭环、通用台账索引只写一次，其他章节统一引用。",
    "第06章关键工序控制点表头必须固定为：工序内容|重点难点|措施|验收。",
    "每章至少1张风险控制表，表头固定为：风险点/控制点|措施（含参数、频次、责任）|验收动作|记录表。",
    "强制标题：第01章必须出现“信息化管理”；第03章必须出现“绿色工地”。",
    "参数优先级：招标文件>图纸与设计说明>工程量清单>补遗答疑>用户项目锚点>暂定值。",
    "禁止编造：工期、面积、结构形式、材料强度、设备型号数量、关键尺寸标高、试验标准值、合同节点时间。",
    "禁语命中数必须为0；遇到禁语必须改写为“控制标准+量化指标+检查频次+责任岗位+验收动作+记录载体”。",
]


QINGTIAN_CHAPTER_RULES: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "总体部署与信息化管理",
        "must": [
            "必须输出项目总控参数表并写明总体部署逻辑。",
            "必须包含完整标题“信息化管理”，且至少覆盖2项：模块名称/数据采集内容/更新频次/预警阈值/责任岗位/闭环时限。",
        ],
    },
    2: {
        "name": "安全管理与劳保用品配置",
        "must": [
            "必须包含安全风险场景控制表、班前交底与巡查闭环、劳保用品配置矩阵。",
            "术语固定使用“劳保用品”，不得用PPE替代。",
        ],
    },
    3: {
        "name": "文明施工与绿色工地",
        "must": [
            "必须包含完整标题“绿色工地”。",
            "扬尘/噪声/污水/固废/节能/节水/节材中至少覆盖3类，每类均写控制措施+验收动作+记录表。",
        ],
    },
    4: {
        "name": "材料采购、进场验收与特殊材料闭环",
        "must": [
            "必须覆盖计划提报、采购审查、进场验收、见证取样、复验判定、不合格隔离退场、批次追溯、特殊材料与危化材料闭环。",
        ],
    },
    5: {
        "name": "四新技术应用",
        "must": [
            "必须写成落地清单，不得写概念展示。",
            "每项四新必须写清：类别、采用内容、适用部位、实施参数、预期效果、验证方式、管控要点。",
        ],
    },
    6: {
        "name": "关键工序控制点",
        "must": [
            "必须使用固定表头：工序内容|重点难点|措施|验收。",
            "每行单元格必须包含：参数、频次、责任岗位、验收动作、记录表。",
        ],
    },
    7: {
        "name": "危大工程闭环管理",
        "must": [
            "必须包含：危大工程清单、专项方案节点、交底节点、实施验收、监测项目、预警阈值、停工条件、复工条件、签认闭环。",
        ],
    },
    8: {
        "name": "质量管理体系与ITP简表",
        "must": [
            "必须体现见证点、停检点、旁站点、检验批、隐蔽验收、整改销项。",
        ],
    },
    9: {
        "name": "进度计划体系与纠偏阈值",
        "must": [
            "必须写清一级/二级/三级计划衔接、关键节点、偏差阈值、触发条件、纠偏动作、闭环时限。",
        ],
    },
    10: {
        "name": "专项方案管理与审批验收节点",
        "must": [
            "必须覆盖编制时点、审批时点、交底时点、验收时点、销项资料。",
        ],
    },
    11: {
        "name": "人力配置与培训",
        "must": [
            "必须覆盖分阶段劳动力投入、高峰配置、特种作业人员、培训计划、考核不合格复训规则。",
        ],
    },
    12: {
        "name": "施工流程、专业穿插与移交条件",
        "must": [
            "必须写成流程衔接表，覆盖前置条件、可穿插工序、禁止交叉情形、移交条件、记录表。",
        ],
    },
    13: {
        "name": "机械设备配置、验收与维保",
        "must": [
            "必须写设备名称、型号规格、数量、进场阶段、验收内容、维保频次、停机替补方案。",
        ],
    },
    14: {
        "name": "图纸会审、深化设计与变更闭环",
        "must": [
            "必须形成问题单闭环：问题发现→会审提出→责任分配→深化处理→变更确认→关闭条件→复核签认。",
        ],
    },
    15: {
        "name": "资源总控与动态调配",
        "must": [
            "必须写触发式调配：人员缺口、材料延误、设备故障、夜间施工、高峰抢工触发条件与调配动作。",
        ],
    },
    16: {
        "name": "可行性验证、样板先行与落地清单",
        "must": [
            "必须覆盖样板段计划、首件验收、试验验证、通过标准、推广条件、落地清单。",
        ],
    },
}


QINGTIAN_CHAPTER_MAPPING: List[Tuple[List[str], int]] = [
    (["施工总体部署", "总体部署", "部署"], 1),
    (["信息化", "智慧工地", "数字化", "BIM"], 1),
    (["安全文明施工", "安全管理", "劳保"], 2),
    (["绿色施工", "绿色工地", "环保", "文明施工"], 3),
    (["材料采购", "进场验收", "特殊材料", "危化"], 4),
    (["四新", "新技术", "新工艺", "新材料", "新设备"], 5),
    (["施工工艺", "施工方法", "关键工序", "工序控制"], 6),
    (["危大工程", "危险性较大工程"], 7),
    (["质量保证", "质量管理", "ITP", "检验与试验"], 8),
    (["进度", "工期", "纠偏", "关键线路"], 9),
    (["专项方案", "审批", "验收节点"], 10),
    (["劳动力", "人员配置", "培训"], 11),
    (["穿插", "移交", "施工流程"], 12),
    (["机械设备", "设备配置", "维保"], 13),
    (["图纸会审", "深化设计", "变更"], 14),
    (["资源总控", "动态调配", "资源配置计划"], 15),
    (["样板先行", "可行性验证", "落地清单"], 16),
]


def _dedup_keep_order(lines: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in lines:
        s = str(raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _norm_title(text: str) -> str:
    t = str(text or "").strip()
    t = t.replace("（", "(").replace("）", ")")
    t = re.sub(r"[\s\u3000]+", "", t)
    t = re.sub(r"^第?\d+[章节篇部分、.．)]*", "", t)
    return t


def compose_qingtian_global_instruction(user_instruction: str) -> str:
    blocks = [
        f"【青天适配系统指令 v{QINGTIAN_POLICY_VERSION}】",
        "输出目标：可执行、可检查、可验收、可留痕、可被AI评标稳定抽取。",
        "硬约束：每章必须采用“参数+频次+责任+验收+记录”闭环表达；缺参必须显式标注“需补充（缺：××）”。",
        "目录策略：有招标目录则严格对标；无完整目录则自动映射16章。",
        "去重策略：通用机制仅写一次，章节仅写本章独有控制点，其余用“引用：见××”。",
        "禁语策略：禁语命中=0，出现即改写为量化动作。",
    ]
    extra = str(user_instruction or "").strip()
    if extra:
        blocks.append("【用户附加指令】" + extra)
    return "\n".join(blocks)


def apply_qingtian_outline_policy(
    *,
    outline: List[str],
    outline_source: str | None,
    strict_tender_outline: bool,
    payload_outline_given: bool,
) -> tuple[List[str], Dict[str, Any]]:
    """
    目录规则：
    - 严格模式：完全保留调用侧目录；
    - 非严格模式：
      - 调用侧显式给目录：尊重调用侧；
      - 否则若招标目录来源不可靠（fallback/none）或目录过短：切到16章适配目录；
      - 其他情况保留招标目录。
    """
    cleaned = _dedup_keep_order([str(x).strip() for x in (outline or []) if str(x).strip()])
    src = str(outline_source or "").strip().lower()
    receipt = {
        "enabled": True,
        "outline_source": src or None,
        "strict_tender_outline": bool(strict_tender_outline),
        "payload_outline_given": bool(payload_outline_given),
        "used_fallback_16": False,
    }
    if strict_tender_outline:
        return cleaned, receipt
    if payload_outline_given:
        return cleaned, receipt

    weak_source = src in {"fallback", "none"}
    too_short = len(cleaned) < 8
    if weak_source or too_short:
        receipt["used_fallback_16"] = True
        receipt["reason"] = "outline_source_weak_or_short"
        return list(QINGTIAN_16_CHAPTER_OUTLINE), receipt
    return cleaned, receipt


def resolve_qingtian_module_id(title: str, chapter_no: int | None = None) -> int | None:
    t = _norm_title(title)
    for keys, idx in QINGTIAN_CHAPTER_MAPPING:
        if any(k and k in t for k in keys):
            return idx
    if isinstance(chapter_no, int) and 1 <= chapter_no <= 16:
        return int(chapter_no)
    return None


def build_qingtian_chapter_requirements(title: str, chapter_no: int) -> List[str]:
    module_id = resolve_qingtian_module_id(title, chapter_no=chapter_no)
    lines: List[str] = [
        "本章必须包含4块：①适用范围与关键参数 ②重点难点/风险点及措施 ③验收与记录 ④引用关系。",
        "本章至少设置1张风险控制表，表头=风险点/控制点|措施（含参数、频次、责任）|验收动作|记录表。",
        "本章关键段落必须同时具备：怎么干/用什么/量化标准/谁检查+频次/留痕载体。",
        "工序写法必须采用：工序名称→步骤→设备材料→关键参数→风险→措施→验收验证。",
        "缺失参数不得编造，必须标注“需补充（缺：××）”；若给默认值必须标注“【暂定】+需确认来源”。",
        "遇到通用机制内容必须改写为“引用：见总表A~E/相关章节”，不得重复展开。",
    ]
    if module_id in QINGTIAN_CHAPTER_RULES:
        lines.extend(QINGTIAN_CHAPTER_RULES[module_id].get("must") or [])
    if module_id == 1:
        lines.append("本章必须出现完整标题：信息化管理。")
    if module_id == 3:
        lines.append("本章必须出现完整标题：绿色工地。")
    if module_id == 6:
        lines.append("第06章固定表头：工序内容|重点难点|措施|验收；每个单元格必须写参数+频次+责任岗位+验收动作+记录表。")
    return _dedup_keep_order(lines)
