from __future__ import annotations

import asyncio
import os
from typing import Dict, Any, List

from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.kg_runtime import search_kg
from backend.zhifei_autoplan.evidence import search_ingested_docs, format_hit_locator, best_ingested_hit
from backend.zhifei_autoplan.utils.llm_client import LLMClient
from backend.zhifei_autoplan.agents.section_writer import SectionWriter
from backend.zhifei_autoplan.media import generate_boq_chart, generate_ingested_previews, generate_outline_mindmap
from backend.zhifei_autoplan.quality_check import run_quality_checks, apply_remediation, strip_nonconcrete_language
from backend.zhifei_autoplan.params_runtime import load_params, get_image_defaults
from backend.zhifei_autoplan.boq_focus_enforcer import ensure_boq_focus_item_cards
from backend.zhifei_autoplan.project_types import (
    detect_project_type,
    normalize_project_type,
    project_type_requirements,
)
from backend.zhifei_autoplan.style_policy import resolve_style
from backend.zhifei_autoplan.outline_planner import (
    enrich_outline,
    infer_total_page_limit,
    plan_chapter_pages,
    recommend_chart_every_n,
)
from backend.zhifei_autoplan.multi_agent_runtime import build_multi_agent_plan


STANDARD_TRADES = [
    "测量工",
    "钢筋工",
    "模板工",
    "混凝土工",
    "架子工",
    "防水工",
    "电工",
    "焊工",
    "管道工",
    "起重信号司索工",
    "机械设备操作工",
]

SYSTEM_MANDATORY_REQUIREMENTS = [
    "风险条目必须采用“风险→控制→验证”三元组表达，且逐条闭环。",
    "每章应包含可量化指标，优先覆盖：频次、阈值、间距、厚度、时长、人数、设备型号。",
    "不得使用空泛表述（如“加强、确保、严格”）替代可执行措施与量化参数。",
    "涉及工期、资源峰值、关键线路间隔的数据需前后保持一致。",
    "对特殊材料、危险品材料、劳保用品、技术工种配置、绿色工地、信息化管理必须有具体内容。",
    "四新技术应用需结合本项目工序与成本收益，写清适用条件、责任工种、实施步骤和验收指标。",
    f"工种名称应使用规范称谓，例如：{'、'.join(STANDARD_TRADES)}。",
    "全文禁止官话、套话、空话，不得出现“加强、确保、严格、压实责任、形成合力、高质量推进”等无落地表达。",
]


def _dedup_lines(lines: List[str], limit: int | None = None) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in lines:
        s = str(raw or "").strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if limit and len(out) >= limit:
            break
    return out


def _build_weights_and_penalties(tender: Dict[str, Any]) -> tuple[list[str], list[str]]:
    weights = []
    penalties = []
    for it in tender.get("items", []):
        dim = str(it.get("dimension"))
        kws = it.get("keywords") or []
        w = it.get("weight")
        if dim in ("扣分项", "PENALTY"):
            penalties.append(f"- 扣分项：{';'.join(kws[:10])}")
        else:
            weights.append(f"- {dim}（权重={w}）：{';'.join(kws[:8])}")
    return weights, penalties


def _to_int_or_none(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def _extract_chapter_page_target(chapter_pages: Dict[str, Any], title: str) -> int | None:
    if not isinstance(chapter_pages, dict):
        return None
    raw = chapter_pages.get(title)
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = (
            raw.get("target")
            or raw.get("pages")
            or raw.get("page_target")
            or raw.get("count")
        )
    return _to_int_or_none(raw)


def _chapter_requirements_for_title(chapter_requirements: Dict[str, Any], title: str) -> list[str]:
    if not isinstance(chapter_requirements, dict):
        return []
    raw = chapter_requirements.get(title)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw.strip()] if raw.strip() else []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, dict):
        lines: list[str] = []
        for k, v in raw.items():
            if v is None:
                continue
            text = str(v).strip()
            if text:
                lines.append(f"{k}：{text}")
        return lines
    text = str(raw).strip()
    return [text] if text else []


def _estimate_chars_per_page(style: Dict[str, Any]) -> int:
    default_chars = 900
    if not isinstance(style, dict):
        return default_chars
    font_cfg = style.get("font") if isinstance(style.get("font"), dict) else {}
    margins_cfg = style.get("margins_cm") if isinstance(style.get("margins_cm"), dict) else {}

    def _to_float(v: Any, default: float) -> float:
        try:
            return float(v)
        except Exception:
            return default

    body_size = style.get("body_size") or style.get("font_size")
    if body_size is None:
        body_size = font_cfg.get("size_pt")
    line_spacing = style.get("line_spacing")
    if line_spacing is None:
        line_spacing = font_cfg.get("line_spacing")
    line_spacing_pt = style.get("line_spacing_pt")
    if line_spacing_pt is None:
        line_spacing_pt = font_cfg.get("line_spacing_pt")

    size = max(8.0, min(22.0, _to_float(body_size, 14.0)))
    spacing = max(1.0, min(2.5, _to_float(line_spacing, 1.5)))
    if line_spacing_pt is None:
        line_spacing_pt = 22.0
    # 固定值行距（磅）转近似倍数，用于估算字数/页
    if line_spacing_pt is not None:
        try:
            spacing = max(1.0, min(3.0, float(line_spacing_pt) / max(8.0, size)))
        except Exception:
            pass

    left = _to_float(margins_cfg.get("left"), 2.0)
    right = _to_float(margins_cfg.get("right"), 2.0)
    top = _to_float(margins_cfg.get("top"), 2.5)
    bottom = _to_float(margins_cfg.get("bottom"), 2.0)

    width_factor = 5.5 / max(2.0, left + right)
    height_factor = 5.0 / max(2.0, top + bottom)
    margin_factor = max(0.75, min(1.25, (width_factor + height_factor) / 2.0))

    est = int(default_chars * (12.0 / size) * (1.5 / spacing) * margin_factor)
    return max(350, min(1800, est))


def _build_boq_focus(boq: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(boq, dict):
        return {
            "lines": [],
            "must_cover_keywords": [],
            "special_materials": [],
            "hazardous_materials": [],
            "ppe_items": [],
        }
    stats = boq.get("stats") if isinstance(boq.get("stats"), dict) else {}
    focus_lines: list[str] = []
    must_cover: list[str] = []

    def _pick_lines(items: List[Dict[str, Any]], title: str, key: str):
        if not items:
            return
        focus_lines.append(f"{title}：")
        for it in items[:5]:
            name = (it.get("name") or "").strip()
            qty = it.get("quantity")
            unit = it.get("unit") or ""
            unit_price = it.get("unit_price")
            total_price = it.get("total_price")
            seg = f"- {name}"
            if qty is not None:
                seg += f" / 工程量={qty}{unit}"
            if unit_price is not None:
                seg += f" / 单价={unit_price}"
            if total_price is not None:
                seg += f" / 合价={total_price}"
            focus_lines.append(seg)
            if name and name not in must_cover:
                must_cover.append(name)

    _pick_lines(stats.get("top_quantity_items") or [], "清单重点（单项工程量大）", "top_quantity_items")
    _pick_lines(stats.get("top_material_demand_items") or [], "清单重点（材料需求量大）", "top_material_demand_items")
    _pick_lines(stats.get("top_total_price_items") or [], "清单重点（单体造价高）", "top_total_price_items")
    _pick_lines(stats.get("top_unit_price_items") or [], "清单重点（材料价格高）", "top_unit_price_items")

    special_items = stats.get("special_material_items") or []
    hazard_items = stats.get("hazardous_material_items") or []
    ppe_items = stats.get("ppe_items") or []
    if special_items:
        focus_lines.append("专项：特殊材料控制要求必须单列章节或子章节。")
    if hazard_items:
        focus_lines.append("专项：危险品材料需单列“采购-储运-领用-作业-应急处置”闭环措施。")
    if ppe_items:
        focus_lines.append("专项：劳保用品需明确发放标准、检查频次、替换周期、责任人。")

    return {
        "lines": focus_lines,
        "must_cover_keywords": must_cover[:20],
        "special_materials": [it.get("name") for it in special_items[:12] if it.get("name")],
        "hazardous_materials": [it.get("name") for it in hazard_items[:12] if it.get("name")],
        "ppe_items": [it.get("name") for it in ppe_items[:12] if it.get("name")],
    }


def _resolve_provider_api_key(payload: Dict[str, Any], provider: str | None) -> str | None:
    """
    Resolve text-model API key with clear precedence:
    1) payload.api_keys[provider]
    2) payload.api_key
    3) provider-specific env vars
    """
    p = str(provider or "").strip().lower()
    if not p:
        v0 = payload.get("api_key")
        return str(v0).strip() if isinstance(v0, str) and v0.strip() else None

    amap = payload.get("api_keys")
    if isinstance(amap, dict):
        v1 = amap.get(p)
        if isinstance(v1, str) and v1.strip():
            return v1.strip()

    v2 = payload.get("api_key")
    if isinstance(v2, str) and v2.strip():
        return v2.strip()

    env_map = {
        "openai": ("OPENAI_API_KEY", "ZF_OPENAI_API_KEY"),
        "google": ("ZF_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"),
        "grok": ("XAI_API_KEY", "GROK_API_KEY", "ZF_GROK_API_KEY"),
        "anthropic": ("ANTHROPIC_API_KEY",),
        "zhipu": ("ZHIPU_API_KEY",),
        "qwen": ("DASHSCOPE_API_KEY", "QWEN_API_KEY"),
        "deepseek": ("DEEPSEEK_API_KEY",),
        "baidu": ("BAIDU_API_KEY",),
        "iflytek": ("IFLYTEK_API_KEY",),
        "tencent": ("TENCENT_API_KEY",),
    }
    for ek in env_map.get(p, ()):
        vv = os.environ.get(ek)
        if isinstance(vv, str) and vv.strip():
            return vv.strip()
    return None


async def run_autoplan(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = payload.get("topic") or "未命名项目"
    outline = payload.get("outline") or []
    requirements = payload.get("requirements") or []
    global_instruction = str(payload.get("global_instruction") or "").strip()
    chapter_requirements = payload.get("chapter_requirements") or {}
    style = payload.get("style") or {}
    chapter_pages = payload.get("chapter_pages") or {}
    provider = payload.get("provider")
    model = payload.get("model")
    providers = payload.get("providers") or []
    model_map = payload.get("model_map") or {}
    dry_run = bool(payload.get("dry_run", False))
    generate_images = bool(payload.get("generate_images", True))
    strict_quality = bool(payload.get("quality_strict", True))
    params = load_params()
    # Per-run parameter overrides (do not persist). Used for:
    # - tuning quant/qse defaults for one tender
    # - adjusting image model/provider
    # This keeps outline tender-driven while allowing editable numeric requirements.
    overrides = payload.get("params_override")
    if isinstance(overrides, dict) and overrides:
        for k, v in overrides.items():
            if isinstance(v, dict) and isinstance(params.get(k), dict):
                merged = dict(params.get(k) or {})
                merged.update(v)
                params[k] = merged
            else:
                params[k] = v
    project_id = payload.get("project_id")
    # Multi-variant logic templates (A/B/C) are used to change intra-chapter reasoning,
    # not to impose a fixed chapter skeleton (outline stays tender-driven).
    raw_variant_id = payload.get("variant_id")
    try:
        variant_index = int(raw_variant_id or 1)
    except Exception:
        variant_index = 1
    if variant_index <= 0:
        variant_index = 1
    try:
        from backend.zhifei_autoplan.logic_templates import pick_logic_template

        explicit_logic = payload.get("logic_template_id") or payload.get("logic_template")
        logic_template_general = pick_logic_template(
            variant_id=variant_index,
            explicit_template_id=explicit_logic,
            domain="general",
        )
        logic_template_qse = pick_logic_template(
            variant_id=variant_index,
            explicit_template_id=explicit_logic,
            domain="qse",
        )
    except Exception:
        logic_template_general = None
        logic_template_qse = None

    # Branding (logo/company) is optional but should be stable within one project run.
    branding: Dict[str, Any] = {
        "bidder_company": payload.get("bidder_company"),
        "bidder_domain": payload.get("bidder_domain"),
        "logo_url": payload.get("logo_url"),
        "project_id": project_id,
    }
    logo_embed: str | None = None
    logo_raw_path: str | None = None
    try:
        from backend.zhifei_autoplan.logo_runtime import resolve_logo, prepare_logo_for_embedding

        # Only resolve when bidder info is provided OR project_id is set (so we can scope to this project).
        if payload.get("bidder_company") or payload.get("logo_url") or payload.get("bidder_domain") or project_id:
            logo_raw = resolve_logo(
                bidder_company=payload.get("bidder_company"),
                logo_url=payload.get("logo_url"),
                bidder_domain=payload.get("bidder_domain"),
                project_id=project_id,
            )
            if logo_raw:
                logo_raw_path = str(logo_raw)
                logo_embed = prepare_logo_for_embedding(logo_raw) or None
    except Exception:
        logo_embed = None
    if logo_embed:
        branding["logo_path"] = logo_embed
        try:
            if project_id:
                from backend.zhifei_autoplan.branding_store import update_branding

                update_branding(
                    str(project_id),
                    {
                        "bidder_company": branding.get("bidder_company"),
                        "bidder_domain": branding.get("bidder_domain"),
                        "logo_url": branding.get("logo_url"),
                        "logo_raw_path": logo_raw_path,
                        "logo_embed_path": str(logo_embed),
                        "logo_path": str(logo_embed),
                    },
                    merge=True,
                )
        except Exception:
            pass

    tender = payload.get("tender_matrix") or load_tender_matrix(project_id=project_id) or {}
    # 若调用方未显式给出目录/版式/页数约束，优先使用招标文件抽取结果兜底
    if not outline:
        outline = tender.get("outline") or []
    tender_style = tender.get("style") if isinstance(tender.get("style"), dict) else {}
    tender_chapter_pages = tender.get("chapter_pages") if isinstance(tender.get("chapter_pages"), dict) else {}
    if not chapter_pages:
        chapter_pages = tender_chapter_pages
    if not chapter_requirements:
        chapter_requirements = tender.get("chapter_requirements") or {}
    tender_globals = tender.get("global_requirements") if isinstance(tender, dict) else None
    if not isinstance(tender_globals, list):
        tender_globals = []
    tender_globals = [strip_nonconcrete_language(str(x)) for x in tender_globals if str(x).strip()]
    project_type = normalize_project_type(payload.get("project_type")) or detect_project_type(
        topic=str(topic),
        outline=outline if isinstance(outline, list) else [],
        requirements=requirements if isinstance(requirements, list) else [],
        tender=tender if isinstance(tender, dict) else {},
    )
    # 在不破坏招标目录的前提下，按项目类型补齐缺失章节。
    outline = enrich_outline(outline if isinstance(outline, list) else [], project_type=project_type)
    # 版式策略：招标有明确要求时覆盖；否则用系统默认（22磅+2.5/2.0边距+宋体三号/四号）。
    style, style_source = resolve_style(user_style=style, tender_style=tender_style)
    # 页数策略：默认按 50 页规划；若招标明确上限则以招标为准；始终保证不超上限。
    total_pages_limit = infer_total_page_limit(tender, default=50)
    chapter_pages = plan_chapter_pages(
        outline,
        total_pages=total_pages_limit,
        chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
    )
    # 图表策略：若调用方未设置频率，按章页权重自动建议。
    chart_policy = style.get("chart_policy") if isinstance(style.get("chart_policy"), dict) else {}
    if "every_n_chapters" not in chart_policy:
        chart_policy = dict(chart_policy)
        chart_policy["enabled"] = bool(chart_policy.get("enabled", True))
        chart_policy["every_n_chapters"] = recommend_chart_every_n(outline, chapter_pages)
        chart_policy["position"] = chart_policy.get("position") or "chapter"
        style["chart_policy"] = chart_policy
    if total_pages_limit:
        tender_globals.append(f"总页数不超过{total_pages_limit}页。")
    boq = payload.get("boq_data") or load_boq_data(project_id=project_id) or {}
    boq_focus = _build_boq_focus(boq)
    # 四新技术（可编辑库+按清单/工序匹配）建议清单：用于章节写作与自动补齐，避免“新技术”泛泛而谈。
    try:
        from backend.zhifei_autoplan.four_new_tech import recommend_four_new

        recs = recommend_four_new(boq, outline=outline, limit=6, topic=str(topic))
        if isinstance(recs, list) and recs:
            boq_focus["four_new_recommendations"] = recs
    except Exception:
        pass
    type_requirements = project_type_requirements(project_type)

    base_requirements: list[str] = []
    if global_instruction:
        base_requirements.append(f"【系统全局指令（必须无条件执行）】{global_instruction}")
    if project_type:
        base_requirements.append(f"【项目类型】{project_type}（按该行业专项逻辑编制）")
        base_requirements.extend(type_requirements)
    base_requirements.extend(list(requirements))
    base_requirements.extend(tender_globals)
    base_requirements.extend(SYSTEM_MANDATORY_REQUIREMENTS)
    # Stable de-dup while preserving order.
    _seen = set()
    _deduped = []
    for it in base_requirements:
        txt = str(it).strip()
        if not txt or txt in _seen:
            continue
        _seen.add(txt)
        _deduped.append(txt)
    base_requirements = _deduped
    multi_agent_plan = build_multi_agent_plan(
        topic=str(topic),
        outline=outline if isinstance(outline, list) else [],
        requirements=base_requirements,
        tender=tender if isinstance(tender, dict) else {},
    )

    def _pick_provider(idx: int) -> tuple[str | None, str | None]:
        if providers:
            p = providers[idx % len(providers)]
            m = model_map.get(p) or model
            return p, m
        return provider, model

    weights, penalties = _build_weights_and_penalties(tender)
    chars_per_page_hint = _estimate_chars_per_page(style)

    def _pick_agent_role(title: str) -> str:
        # 可配置角色规则（优先）
        try:
            from pathlib import Path
            import json
            cfg_path = Path("backend/data/autoplan/agent_roles.json")
            if cfg_path.exists():
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                default_role = cfg.get("default") or "技术负责人"
                rules = cfg.get("rules") or []
                for r in rules:
                    keys = r.get("match") or []
                    if any(k in title for k in keys):
                        return r.get("role") or default_role
                return default_role
        except Exception:
            pass
        # 回退默认规则
        t = title
        if any(k in t for k in ("质量", "检验", "验收")):
            return "质量负责人"
        if any(k in t for k in ("安全", "文明", "应急")):
            return "安全负责人"
        if any(k in t for k in ("进度", "工期", "计划")):
            return "进度负责人"
        if any(k in t for k in ("环保", "绿", "水土", "文明施工")):
            return "环保负责人"
        if any(k in t for k in ("资源", "设备", "材料")):
            return "资源统筹负责人"
        return "技术负责人"

    async def build_section(idx: int, title: str):
        # 章节级重试：多模型轮询重试，最多尝试 3 个 provider（主+备1+备2）
        tries = []
        if providers:
            for i in range(len(providers)):
                p, m = _pick_provider(idx + i)
                tries.append((p, m))
        else:
            tries.append((provider, model))
        tries = tries[:3]
        kg_hits = search_kg(f"{topic} {title} 施工组织 质量 安全 工期", top_k=4)
        doc_hits = search_ingested_docs(
            f"{topic} {title} 招标 清单 图纸 质量 安全 工期",
            limit=6,
            project_id=project_id,
        )
        # Prefer enterprise standards / work instructions when provided (to raise output quality and reduce hallucination).
        # Only do this when project_id is set, otherwise global audit may cross-contaminate between projects.
        standard_hits = []
        if project_id:
            standard_hits = search_ingested_docs(
                f"{topic} {title} 企业标准 工法 作业指导 标准化 质量验收",
                limit=3,
                project_id=project_id,
                require_tags=["standard"],
            )
        kg_evidence = [f"{r.get('title')}: {r.get('text')}" for r in kg_hits.get("results", [])]
        # Include a lightweight evidence locator (sha@offset) to make "【证据:...】" traceable.
        doc_evidence = []
        seen_loc = set()
        for h in (doc_hits or []) + (standard_hits or []):
            prefix = format_hit_locator(h)
            if prefix in seen_loc:
                continue
            seen_loc.add(prefix)
            doc_evidence.append(f"{prefix}: {h.get('snippet')}")
        checklist = []
        for it in tender.get("items", []):
            dim = it.get("dimension")
            kws = it.get("keywords") or []
            checklist.append(f"{dim}: {';'.join(kws[:6])}")

        section_requirements = list(base_requirements)
        section_requirements.extend(_chapter_requirements_for_title(chapter_requirements, title))
        # Chapter blueprint: when the tender outline contains a known chapter theme,
        # inject the corresponding "章内结构" guidance (does not change outline).
        bp = None
        try:
            from backend.zhifei_autoplan.chapter_blueprints import match_chapter_blueprint
            bp = match_chapter_blueprint(title)
        except Exception:
            bp = None
        chapter_target_pages = _extract_chapter_page_target(chapter_pages, title)
        if chapter_target_pages:
            target_chars = max(200, chapter_target_pages * chars_per_page_hint)
            section_requirements.append(
                f"本章目标页数：{chapter_target_pages}页（建议正文约{target_chars}字，允许±20%）"
            )
        if boq_focus.get("lines"):
            section_requirements.append("以下清单重点项应作为重点编制对象：")
            section_requirements.extend(boq_focus.get("lines")[:20])
        if boq_focus.get("special_materials"):
            section_requirements.append(f"特殊材料清单：{'；'.join(boq_focus.get('special_materials')[:10])}")
        if boq_focus.get("hazardous_materials"):
            section_requirements.append(f"危险品材料清单：{'；'.join(boq_focus.get('hazardous_materials')[:10])}")
        if boq_focus.get("ppe_items"):
            section_requirements.append(f"劳保用品清单：{'；'.join(boq_focus.get('ppe_items')[:10])}")
        graph_ctx = multi_agent_plan.chapter_graph_context(
            title=title,
            query=f"{topic} {title} 施工组织 质量 安全 工期 图纸 清单",
            section_requirements=section_requirements,
            top_k=6,
        )
        graph_hits = graph_ctx.get("hits") or []
        for gh in graph_hits[:6]:
            gname = str(gh.get("graph_name") or gh.get("graph_file") or "图谱").strip()
            gtitle = str(gh.get("title") or "节点").strip()
            gtext = str(gh.get("text") or "").strip()
            if not gtext:
                continue
            kg_evidence.append(f"{gname}/{gtitle}: {gtext}")
        kg_evidence = _dedup_lines(kg_evidence, limit=12)
        exp_values = [str(x).strip() for x in (graph_ctx.get("experience_values") or []) if str(x).strip()]
        if exp_values:
            section_requirements.append("招标文件未明确给值的参数，按图谱同类工程经验值补位并显式标注：")
            section_requirements.extend(exp_values[:4])
            section_requirements.append("凡经验值必须保留“【经验值:...】”与“【图谱经验值:...】”标记。")

        ctx = {
            "requirements": section_requirements,
            "kg_evidence": kg_evidence,
            "doc_evidence": doc_evidence,
            "checklist": checklist,
            "weights": weights,
            "penalties": penalties,
            "agent_role": _pick_agent_role(title),
            "chapter_target_pages": chapter_target_pages,
            "chapter_chars_per_page_hint": chars_per_page_hint,
            "boq_focus": boq_focus,
            "standard_trades": STANDARD_TRADES,
            "params": params,
            "project_type": project_type,
            "global_instruction": global_instruction,
            # Use numeric index for templates so v1/v2/v3 can map to A/B/C deterministically.
            "variant_id": variant_index,
            "logic_template": {"id": "A", "name": "交付清单驱动"},
            "chapter_domain": "general",
            "master_agent": graph_ctx.get("agents", {}).get("master") or multi_agent_plan.master_agent,
            "specialist_agents": graph_ctx.get("agents", {}).get("specialists") or [],
            "compliance_agent": graph_ctx.get("agents", {}).get("compliance") or multi_agent_plan.compliance_agent,
            "specialty_tags": graph_ctx.get("agents", {}).get("specialty_tags") or [],
            "graph_nodes": graph_ctx.get("node_bindings") or [],
            "graph_experience_values": exp_values,
        }
        if bp:
            ctx["chapter_blueprint"] = bp
        # Pick domain-specific logic template per chapter (质量/安全/文明环保等章节使用闭环结构模版)。
        try:
            from backend.zhifei_autoplan.logic_templates import classify_chapter_domain

            dom = classify_chapter_domain(title)
        except Exception:
            dom = "general"
        lt = logic_template_qse if dom == "qse" else logic_template_general
        if lt:
            ctx["logic_template"] = lt.as_dict()
        ctx["chapter_domain"] = dom

        def _attach_section_meta(rec: Dict[str, Any] | None) -> Dict[str, Any] | None:
            if not isinstance(rec, dict):
                return rec
            # Always keep deterministic metadata for downstream quality gates and exports.
            rec.setdefault("agent_role", ctx.get("agent_role"))
            rec.setdefault("chapter_domain", dom)
            lt_ctx = ctx.get("logic_template") if isinstance(ctx.get("logic_template"), dict) else {}
            tid = str(lt_ctx.get("id") or "").strip()
            tname = str(lt_ctx.get("name") or "").strip()
            if tid:
                rec.setdefault("logic_template_id", tid)
            if tname:
                rec.setdefault("logic_template_name", tname)
            if isinstance(bp, dict):
                bid = str(bp.get("id") or "").strip()
                bname = str(bp.get("name") or "").strip()
                if bid:
                    rec.setdefault("chapter_blueprint_id", bid)
                if bname:
                    rec.setdefault("chapter_blueprint_name", bname)
            rec.setdefault("master_agent", ctx.get("master_agent"))
            rec.setdefault("specialist_agents", list(ctx.get("specialist_agents") or []))
            rec.setdefault("compliance_agent", ctx.get("compliance_agent"))
            rec.setdefault("specialty_tags", list(ctx.get("specialty_tags") or []))
            rec.setdefault("graph_nodes", list(ctx.get("graph_nodes") or []))
            return rec

        last = None
        for p, m in tries:
            llm = None
            if p and m and not dry_run:
                try:
                    llm = LLMClient(
                        provider=p,
                        model=m,
                        api_key=_resolve_provider_api_key(payload, p),
                        base_url=payload.get("base_url"),
                        secret_key=payload.get("secret_key"),
                        token_url=payload.get("token_url"),
                    )
                except Exception as e:
                    last = _attach_section_meta(
                        {
                            "title": title,
                            "content": "",
                            "provider": p,
                            "model": m,
                            "error": f"provider_init_failed: {e}",
                        }
                    )
                    continue
            writer = SectionWriter(llm=llm)
            try:
                last = _attach_section_meta(await writer.write(title, ctx))
            except Exception as e:
                last = _attach_section_meta(
                    {
                        "title": title,
                        "content": "",
                        "provider": p,
                        "model": m,
                        "error": f"section_write_failed: {e}",
                    }
                )
                continue
            if last and not last.get("error"):
                return last
        if last:
            return last
        return _attach_section_meta({"title": title, "content": "章节生成失败"}) or {"title": title, "content": "章节生成失败"}

    sections = await asyncio.gather(*[build_section(i, t) for i, t in enumerate(outline)])
    for sec in sections:
        sec["content"] = strip_nonconcrete_language(sec.get("content") or "")

    # Enforce focus items control cards into the most relevant host chapter (no new top-level chapters).
    try:
        # Note: sections do not store doc_evidence; auto-pick a traceable locator for "工程量清单" if ingested docs exist.
        evidence_src = str(payload.get("evidence_src") or "").strip()
        if not evidence_src:
            hit = best_ingested_hit(
                "工程量清单 报价 清单",
                limit=10,
                prefer_filename_keywords=["清单", "BOQ", "报价", "工程量"],
                project_id=project_id,
            )
            evidence_src = str((hit or {}).get("locator") or "工程量清单(解析统计)")
        ensure_boq_focus_item_cards(
            sections,
            boq_focus,
            evidence_src=evidence_src,
            params=params,
            project_id=project_id,
            boq_data=boq,
        )
    except Exception:
        pass

    media = []
    if generate_images:
        stats = boq.get("stats") if isinstance(boq, dict) else None
        if stats:
            media.extend(generate_boq_chart(stats))
        # Drawings/attachments previews from ingested docs
        media.extend(generate_ingested_previews(limit=6, project_id=project_id))
        # Mindmap (prefer Gemini "banana" image model when key is configured)
        try:
            img_defaults = get_image_defaults(params)
            image_provider = (payload.get("image_provider") or img_defaults.get("provider") or "").strip()
            image_model = (payload.get("image_model") or img_defaults.get("model") or "").strip()
            aspect_ratio = (payload.get("image_aspect_ratio") or img_defaults.get("aspect_ratio") or "16:9").strip()
            image_api_key = (
                payload.get("image_api_key")
                or os.environ.get("ZF_GOOGLE_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
                or os.environ.get("GEMINI_API_KEY")
            )
            if not image_api_key and image_provider == "google" and payload.get("provider") == "google":
                image_api_key = payload.get("api_key")

            # Resolve bidder logo once; embed it into DOCX and pass into mindmap generation if possible.
            if logo_embed:
                media.append({"path": logo_embed, "caption": "投标单位LOGO"})

            mm = None
            if image_provider == "google":
                mm = generate_outline_mindmap(
                    topic,
                    outline,
                    api_key=image_api_key,
                    model=image_model,
                    aspect_ratio=aspect_ratio,
                    logo_path=logo_embed,
                    bidder_company=payload.get("bidder_company"),
                    logo_url=payload.get("logo_url"),
                    bidder_domain=payload.get("bidder_domain"),
                )
            if mm:
                media.append(mm)
        except Exception:
            pass

    quality: Dict[str, Any] = {}
    if payload.get("auto_remediate", True):
        quality = run_quality_checks(
            tender,
            outline,
            sections,
            boq=boq,
            boq_focus=boq_focus,
            project_id=project_id,
            strict=strict_quality,
        )
        remediate_mode = payload.get("remediate_mode") or "template"

        async def _remediate_with_llm(sec: Dict[str, Any], recs: List[Dict[str, Any]]):
            if not recs:
                return
            llm = None
            if provider and model and not dry_run:
                try:
                    llm = LLMClient(
                        provider=provider,
                        model=model,
                        api_key=_resolve_provider_api_key(payload, provider),
                        base_url=payload.get("base_url"),
                        secret_key=payload.get("secret_key"),
                        token_url=payload.get("token_url"),
                    )
                except Exception:
                    llm = None
            if llm is None:
                return
            title = sec.get("title") or "章节"
            content = sec.get("content") or ""
            sec["original_content"] = content
            problems = "\n".join([f"- {r.get('type')}: {r.get('suggestion')}" for r in recs])
            prompt = (
                "你是施工组织设计专家，请在不丢失证据标注的前提下对章节进行修复与优化。\n"
                "要求：\n"
                "1) 风险内容改写为“风险→控制→验证”三元组并闭环\n"
                "2) 补齐频次/阈值/间距/厚度/时长/人数/设备型号等量化指标\n"
                "3) 补齐责任/验收/流程，避免空泛词（加强/确保/严格）\n"
                "4) 保留或补全“【证据:来源】”标注\n"
                "5) 涉及专项时补齐：特殊材料、危险品材料、劳保用品、技术工种配置、绿色工地、信息化管理、四新技术\n"
                "6) 全文禁止官话、套话、空话，不得出现“加强、确保、严格、压实责任、形成合力、高质量推进”等词\n"
                f"\n章节标题：{title}\n"
                f"需修复项：\n{problems}\n"
                f"\n原文：\n{content}\n\n"
                "请输出修复后的正文："
            )
            resp = await llm.complete(prompt)
            if isinstance(resp, dict) and resp.get("text"):
                sec["content"] = strip_nonconcrete_language(resp["text"])
                sec["auto_remediated"] = "llm"

        if remediate_mode == "llm":
            recs_by_title = {}
            for r in quality.get("remediation") or []:
                recs_by_title.setdefault(r.get("title"), []).append(r)
            await asyncio.gather(
                *[
                    _remediate_with_llm(sec, recs_by_title.get(sec.get("title"), []))
                    for sec in sections
                ]
            )
        else:
            apply_remediation(
                sections,
                quality.get("remediation") or [],
                project_id=project_id,
                boq_focus=boq_focus,
                params=params,
            )
        for sec in sections:
            sec["content"] = strip_nonconcrete_language(sec.get("content") or "")

    # Plan consistency: normalize duplicated metrics (工期/资源峰值/关键线路间隔) to a single canonical value.
    plan_receipt = None
    try:
        from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections

        plan_receipt = normalize_metrics_in_sections(sections)
    except Exception:
        plan_receipt = None

    # Drawing evidence index + bind at least 1 drawing locator to each key process chapter (best-effort).
    drawing_index = None
    try:
        from backend.zhifei_autoplan.drawing_index import build_drawing_index

        drawing_index = build_drawing_index(topic, outline, project_id=str(project_id) if project_id else None)
        for b in (drawing_index or {}).get("chapter_bindings") or []:
            ch = str(b.get("chapter") or "").strip()
            loc = str(b.get("locator") or "").strip()
            if not ch or not loc:
                continue
            for sec in sections:
                if str(sec.get("title") or "").strip() != ch:
                    continue
                text = str(sec.get("content") or "")
                if loc in text:
                    break
                add = (
                    "\n\n【图纸证据定位】\n"
                    f"- 本章对应图纸定位：{loc}；校核点=构件位置/尺寸/标高/做法。"
                    f"【证据:{loc}】\n"
                )
                sec["content"] = (text.rstrip() + add).strip() + "\n"
                break
    except Exception:
        drawing_index = None

    # Enterprise standards index (best-effort): list standard docs + chapter bindings for traceability.
    standard_index = None
    try:
        from backend.zhifei_autoplan.standard_index import build_standard_index

        standard_index = build_standard_index(topic, outline, project_id=str(project_id) if project_id else None)
        # Bind best-effort standard locators into key chapters to make "按企业标准执行" traceable.
        for b in (standard_index or {}).get("chapter_bindings") or []:
            ch = str(b.get("chapter") or "").strip()
            loc = str(b.get("locator") or "").strip()
            if not ch or not loc:
                continue
            for sec in sections:
                if str(sec.get("title") or "").strip() != ch:
                    continue
                text = str(sec.get("content") or "")
                if loc in text:
                    break
                add = (
                    "\n\n【企业标准证据定位】\n"
                    f"- 本章对应企业标准/工法定位：{loc}；落地=关键参数/验收点写入台账并首件确认=1次/工序。"
                    f"【证据:{loc}】\n"
                )
                sec["content"] = (text.rstrip() + add).strip() + "\n"
                break
    except Exception:
        standard_index = None

    # Final quality check after remediation + normalization + drawing binding.
    try:
        for sec in sections:
            sec["content"] = strip_nonconcrete_language(sec.get("content") or "")
    except Exception:
        pass
    quality = run_quality_checks(
        tender,
        outline,
        sections,
        boq=boq,
        boq_focus=boq_focus,
        project_id=project_id,
        strict=strict_quality,
    )

    # Parameter trace receipt (key -> occurrences -> impacted chapters). Useful for “改一处参数生成差异清单”.
    param_receipt = None
    param_receipt_path = None
    try:
        from backend.zhifei_autoplan.param_trace import build_param_receipt, save_latest_receipt

        param_receipt = build_param_receipt(sections, params)
        param_receipt_path = save_latest_receipt(param_receipt, project_id=str(project_id) if project_id else None)
    except Exception:
        param_receipt = None
        param_receipt_path = None

    # Cross-index: BoQ focus item -> chapter -> drawing/standard locator -> closure flags.
    cross_index = None
    try:
        from backend.zhifei_autoplan.cross_index import build_cross_index

        cross_index = build_cross_index(
            boq=boq,
            sections=sections,
            boq_focus=boq_focus,
            drawing_index=drawing_index,
            standard_index=standard_index,
            quality_checks=quality,
            project_id=str(project_id) if project_id else None,
        )
    except Exception:
        cross_index = None
    params_used = None
    try:
        from backend.zhifei_autoplan.params_runtime import (
            get_quant_defaults,
            get_boq_focus_card_defaults,
            get_qse_defaults,
        )

        params_used = {
            "version": str(params.get("version") or ""),
            "quant_defaults": get_quant_defaults(params),
            "boq_focus_card": get_boq_focus_card_defaults(params),
            "qse_defaults": get_qse_defaults(params),
            # Use the module-level import to avoid local-scope shadowing (which would break mindmap generation).
            "image_defaults": get_image_defaults(params),
        }
    except Exception:
        params_used = None
    graph_binding_missing = [
        str(sec.get("title") or "")
        for sec in sections
        if not list(sec.get("graph_nodes") or [])
    ]
    multi_agent_compliance = {
        "agent": multi_agent_plan.compliance_agent,
        "graph_binding": {
            "ok": len(graph_binding_missing) == 0,
            "missing_titles": graph_binding_missing,
        },
        "consistency": {
            "ok": bool((plan_receipt or {}).get("ok", True)),
            "canonical": (plan_receipt or {}).get("canonical") if isinstance(plan_receipt, dict) else {},
        },
    }
    return {
        "topic": topic,
        "project_type": project_type,
        "global_instruction": global_instruction,
        "outline": outline,
        "sections": sections,
        "media": media,
        "branding": branding,
        # Keep the raw value for API backward-compatibility (some callers pass a string).
        "variant_id": raw_variant_id,
        "logic_template": logic_template_general.as_dict() if logic_template_general else None,
        "logic_templates": {
            "general": logic_template_general.as_dict() if logic_template_general else None,
            "qse": logic_template_qse.as_dict() if logic_template_qse else None,
        },
        "chapter_requirements": chapter_requirements,
        "chapter_pages": chapter_pages,
        "style": style,
        "style_source": style_source,
        "quality_strict": strict_quality,
        "boq_focus": boq_focus,
        "compare": {
            "mode": payload.get("compare_mode", "full"),
            "max_chars": int(payload.get("compare_max_chars") or 800),
            "titles": payload.get("compare_titles"),
        },
        "quality_checks": quality,
        "evidence": {
            "tender_loaded": bool(tender),
            "boq_loaded": bool(boq),
        },
        "param_trace": {
            "ok": bool(param_receipt),
            "saved_at": param_receipt_path,
            "receipt": param_receipt,
        },
        "drawing_index": drawing_index,
        "standard_index": standard_index,
        "cross_index": cross_index,
        "plan_consistency": plan_receipt,
        "multi_agent": {
            **multi_agent_plan.summary(),
            "compliance": multi_agent_compliance,
        },
        "params_used": params_used,
    }
