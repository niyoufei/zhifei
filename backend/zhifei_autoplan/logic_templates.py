from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


TEMPLATES_PATH = Path("backend/data/autoplan/logic_templates.json")
_KNOWN_DOMAINS = {"general", "qse"}


@dataclass(frozen=True)
class LogicTemplate:
    """
    Logic templates are NOT chapter skeletons.
    They only control intra-chapter reasoning/ordering so multi-variant documents
    do not look like trivial paraphrases of each other.
    """

    template_id: str
    name: str
    # A concise instruction block injected into LLM prompts.
    prompt_rules: str
    # Suggested intra-chapter headings (used by deterministic fallback only).
    fallback_headings: List[str]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.template_id,
            "name": self.name,
            "prompt_rules": self.prompt_rules,
            "fallback_headings": list(self.fallback_headings or []),
        }

def classify_chapter_domain(title: str) -> str:
    """
    Classify chapter domain to apply domain-specific logic templates.
    - "qse": quality/safety/civilized construction/environment/green/emergency chapters
    - "general": everything else
    """
    t = str(title or "").strip()
    if not t:
        return "general"
    qse_keys = (
        # 质量
        "质量",
        "质量管理",
        "质量保证",
        "检验",
        "验收",
        "试验",
        "检测",
        "实测实量",
        # 安全 / 职业健康
        "安全",
        "安全管理",
        "安全生产",
        "安全保证",
        "文明",
        "文明施工",
        "安全文明",
        "安全文明施工",
        "环保",
        "环境",
        "环境保护",
        "绿色",
        "绿色施工",
        "扬尘",
        "噪声",
        "污水",
        "固废",
        "应急",
        "消防",
        "职业健康",
        "职业卫生",
        "EHS",
        "HSE",
    )
    return "qse" if any(k in t for k in qse_keys) else "general"


def _builtin_templates_general() -> Dict[str, LogicTemplate]:
    # Keep these rules concrete; avoid any officialese/vague wording.
    a = LogicTemplate(
        template_id="A",
        name="交付清单驱动",
        prompt_rules=(
            "章内逻辑模版A（交付清单驱动）：\n"
            "- 先写“本章交付物/记录表/验收点”，让评审先看到可验收产物。\n"
            "- 再写“约束条件”（招标/图纸/清单：参数、位置、范围）。\n"
            "- 再写“执行步骤”（准备->测量复核->材料->作业->检查验收->资料归档）。\n"
            "- 最后集中输出“风险→控制→验证”闭环（必须量化：频次/阈值/时长/人数/设备型号）。\n"
            "- 每个关键结论句末追加可追溯证据【证据:文件名#p页_sha@offset】。\n"
        ),
        fallback_headings=["本章交付物", "约束条件", "执行步骤", "资源配置", "风险→控制→验证", "资料与证据"],
    )
    b = LogicTemplate(
        template_id="B",
        name="工序流程驱动",
        prompt_rules=(
            "章内逻辑模版B（工序流程驱动）：\n"
            "- 先按工序写“流程=步骤1..n”，每步都写：控制点(阈值/间距/厚度)+检查频次+责任岗位+记录表。\n"
            "- 风险三元组按步骤插入：每步至少1条“风险→控制→验证”。\n"
            "- 末尾汇总：资源峰值/节拍/接口(交叉作业)与证据台账。\n"
            "- 避免长段落，使用项目符号短句。\n"
        ),
        fallback_headings=["工序流程", "步骤控制点", "风险→控制→验证（按步骤）", "资源节拍", "接口与资料闭环"],
    )
    c = LogicTemplate(
        template_id="C",
        name="指标矩阵驱动",
        prompt_rules=(
            "章内逻辑模版C（指标矩阵驱动）：\n"
            "- 先给“控制指标矩阵”：频次/阈值/间距/厚度/时长/人数/设备型号（逐条带单位）。\n"
            "- 再按人-机-料-法-环写落地动作：谁做+怎么做+检查频次+验收阈值+记录表。\n"
            "- 风险三元组按维度分组：质量/安全/进度/成本/环保（每组至少1条闭环）。\n"
            "- 最后写信息化台账字段与上传频次，保证可追溯。\n"
        ),
        fallback_headings=["控制指标矩阵", "人机料法环落地", "风险→控制→验证（按维度）", "信息化与台账", "证据定位"],
    )
    return {t.template_id: t for t in (a, b, c)}

def _builtin_templates_qse() -> Dict[str, LogicTemplate]:
    """
    Domain-specific templates for 质量/安全/文明环保等章节。
    These templates enforce a closed-loop structure with quantifiable gates and records.
    """
    a = LogicTemplate(
        template_id="A",
        name="闭环清单驱动（质量/安全/环保）",
        prompt_rules=(
            "章内逻辑模版A（质量/安全/文明环保闭环清单驱动）：\n"
            "- 先输出“闭环清单”（至少6条）：每条必须按固定字段写：\n"
            "  风险/问题 -> 控制动作(责任岗位+频次) -> 验证方法(阈值+抽检/监测频次) -> 记录表/台账字段 -> 偏差处置(时限)。\n"
            "- 再写“关键控制点”与证据定位：每条控制点后追加【证据:文件名#p页_sha@offset】。\n"
            "- 避免空话，禁止出现“加强/确保/严格”。\n"
        ),
        fallback_headings=["闭环清单", "关键控制点", "偏差处置", "记录与证据"],
    )
    b = LogicTemplate(
        template_id="B",
        name="场景闭环驱动（质量/安全/环保）",
        prompt_rules=(
            "章内逻辑模版B（质量/安全/文明环保场景闭环驱动）：\n"
            "- 先按施工场景拆分（例如：夜间施工/高处作业/混凝土浇筑/材料堆放/临电），每个场景至少写2条闭环。\n"
            "- 每条闭环用同一结构：风险/问题 -> 控制(动作+责任岗位+频次) -> 验证(阈值+方法+记录表) -> 偏差处置(时限)。\n"
            "- 末尾汇总“检查频次总表”（日/周/月）与“记录表清单”。\n"
        ),
        fallback_headings=["场景拆分", "闭环卡片（按场景）", "检查频次总表", "记录表清单"],
    )
    c = LogicTemplate(
        template_id="C",
        name="指标监测闭环（质量/安全/环保）",
        prompt_rules=(
            "章内逻辑模版C（质量/安全/文明环保指标监测闭环）：\n"
            "- 先给“指标矩阵”：指标名/阈值/频次/责任岗位/记录表。\n"
            "- 再写“数据闭环”：采集(谁/工具/频次)->判定(阈值)->处置(动作+时限)->复核(方法)->归档(台账字段/上传频次)。\n"
            "- 每个指标至少绑定1条证据定位符【证据:文件名#p页_sha@offset】。\n"
        ),
        fallback_headings=["指标矩阵", "数据闭环", "处置与复核", "证据定位"],
    )
    return {t.template_id: t for t in (a, b, c)}


def _parse_templates_dict(obj: Dict[str, Any]) -> Dict[str, LogicTemplate]:
    out: Dict[str, LogicTemplate] = {}
    for k, v in (obj or {}).items():
        if not isinstance(v, dict):
            continue
        tid = str(v.get("id") or k or "").strip().upper()
        if tid not in {"A", "B", "C"}:
            continue
        name = str(v.get("name") or "").strip() or tid
        rules = str(v.get("prompt_rules") or "").strip()
        heads = v.get("fallback_headings") if isinstance(v.get("fallback_headings"), list) else []
        heads2 = [str(x).strip() for x in heads if str(x).strip()]
        if not rules:
            continue
        out[tid] = LogicTemplate(tid, name, rules, heads2)
    return out


def _load_templates_from_file(domain: str) -> Dict[str, LogicTemplate]:
    if not TEMPLATES_PATH.exists():
        return {}
    try:
        obj = json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return {}
        dom = (domain or "general").strip().lower()
        if dom not in _KNOWN_DOMAINS:
            dom = "general"

        # Backward compatible:
        # - Flat format: {"A": {...}, "B": {...}, "C": {...}} -> general
        # - Domain format: {"general": {...}, "qse": {...}}
        if any(k in obj for k in _KNOWN_DOMAINS):
            sub = obj.get(dom)
            if isinstance(sub, dict):
                return _parse_templates_dict(sub)
            return {}
        if dom != "general":
            return {}
        return _parse_templates_dict(obj)
    except Exception:
        return {}

def load_logic_templates(domain: str = "general") -> Dict[str, LogicTemplate]:
    """
    Load templates from optional JSON file; fallback to built-ins.
    The system always guarantees A/B/C exist.
    """
    dom = (domain or "general").strip().lower()
    if dom not in _KNOWN_DOMAINS:
        dom = "general"
    builtins = _builtin_templates_qse() if dom == "qse" else _builtin_templates_general()
    file_tmpls = _load_templates_from_file(dom)
    merged = dict(builtins)
    merged.update(file_tmpls)
    # Ensure all exist
    for k, v in builtins.items():
        merged.setdefault(k, v)
    return merged


def normalize_template_id(tid: str | None) -> str | None:
    if not isinstance(tid, str):
        return None
    s = tid.strip().upper()
    if not s:
        return None
    if s in {"A", "B", "C"}:
        return s
    # Accept common aliases
    alias = {
        "TEMPLATE_A": "A",
        "TEMPLATE_B": "B",
        "TEMPLATE_C": "C",
        "方案A": "A",
        "方案B": "B",
        "方案C": "C",
    }
    return alias.get(s)


def pick_logic_template(
    *,
    variant_id: int | None = None,
    explicit_template_id: str | None = None,
    domain: str = "general",
) -> LogicTemplate:
    """
    Pick A/B/C deterministically.
    - If explicit_template_id is provided, honor it.
    - Else pick by variant_id order: 1->A, 2->B, 3->C, 4->A...
    """
    tmpls = load_logic_templates(domain=domain)
    exp = normalize_template_id(explicit_template_id)
    if exp and exp in tmpls:
        return tmpls[exp]
    try:
        vid = int(variant_id or 1)
    except Exception:
        vid = 1
    if vid <= 0:
        vid = 1
    order = ["A", "B", "C"]
    key = order[(vid - 1) % 3]
    return tmpls[key]
