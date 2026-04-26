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
from backend.zhifei_autoplan.enterprise_params import get_enterprise_profile
from backend.zhifei_autoplan.boq_schedule import build_boq_wbs_cpm
from backend.zhifei_autoplan.missing_param_probe import probe_missing_parameters
from backend.zhifei_autoplan.agent_contract import build_agent_contract, validate_section_with_contract
from backend.zhifei_autoplan.score_mapper import build_score_mapping
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.case_library_service import build_case_reference_pack
from backend.zhifei_autoplan.image_library import build_image_selection_pack
from backend.zhifei_autoplan.compliance_runtime import query_compliance
from backend.zhifei_autoplan.terminology_guard import (
    load_labor_allocation_matrix,
    normalize_sections_terminology_async,
    suggest_labor_ratio_for_chapter,
)


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


def _deep_merge_dict(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(dst or {})
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge_dict(out.get(k) or {}, v)
        else:
            out[k] = v
    return out


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


def _resolve_provider_api_key(
    payload: Dict[str, Any],
    provider: str | None,
    *,
    slot_id: str | None = None,
    explicit_key: str | None = None,
) -> str | None:
    """
    Resolve text-model API key with clear precedence:
    1) explicit_key (provider_chain per-slot key)
    2) payload.api_keys[slot_id] (slot-scoped key)
    3) payload.api_keys[provider]
    4) payload.api_key
    5) provider-specific env vars
    """
    if isinstance(explicit_key, str) and explicit_key.strip():
        return explicit_key.strip()

    p = str(provider or "").strip().lower()
    if not p:
        v0 = payload.get("api_key")
        return str(v0).strip() if isinstance(v0, str) and v0.strip() else None

    amap = payload.get("api_keys")
    if isinstance(amap, dict):
        if isinstance(slot_id, str) and slot_id.strip():
            vs = amap.get(slot_id.strip())
            if isinstance(vs, str) and vs.strip():
                return vs.strip()
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


def _normalize_provider_chain(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize provider chain to support multiple keys for same provider.
    Preferred input schema:
      provider_chain = [{"slot":"primary","provider":"google","model":"...", "api_key":"..."}]
    Backward compatible with legacy providers/model_map/provider fields.
    """
    chain: List[Dict[str, Any]] = []

    raw_chain = payload.get("provider_chain")
    if isinstance(raw_chain, list):
        for idx, item in enumerate(raw_chain):
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "").strip().lower()
            model = str(item.get("model") or "").strip()
            if not provider or not model:
                continue
            slot = str(item.get("slot") or f"slot_{idx + 1}").strip()
            api_key = str(item.get("api_key") or "").strip()
            chain.append(
                {
                    "slot": slot,
                    "provider": provider,
                    "model": model,
                    "api_key": api_key,
                }
            )
    if chain:
        return chain

    providers = payload.get("providers") or []
    model_map = payload.get("model_map") or {}
    if isinstance(providers, list) and providers:
        for idx, p in enumerate(providers):
            provider = str(p or "").strip().lower()
            if not provider:
                continue
            model = str(model_map.get(provider) or payload.get("model") or "").strip()
            if not model:
                continue
            chain.append(
                {
                    "slot": f"legacy_{idx + 1}",
                    "provider": provider,
                    "model": model,
                    "api_key": "",
                }
            )
        if chain:
            return chain

    provider = str(payload.get("provider") or "").strip().lower()
    model = str(payload.get("model") or "").strip()
    if provider and model:
        chain.append({"slot": "legacy_primary", "provider": provider, "model": model, "api_key": ""})
    return chain


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
    provider_chain = _normalize_provider_chain(payload)
    if provider_chain:
        provider = provider_chain[0].get("provider") or provider
        model = provider_chain[0].get("model") or model
    dry_run = bool(payload.get("dry_run", False))
    generate_images = bool(payload.get("generate_images", True))
    strict_quality = bool(payload.get("quality_strict", True))
    case_library_options = payload.get("case_library") if isinstance(payload.get("case_library"), dict) else {}
    image_library_options = payload.get("image_library") if isinstance(payload.get("image_library"), dict) else {}
    reference_library_audit_path = (
        payload.get("reference_library_audit_path")
        or payload.get("ingest_audit_path")
        or payload.get("audit_path")
    )
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
    # Multi-variant logic templates (A/B/C/D/E) are used to change intra-chapter reasoning,
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
    enterprise_profile = get_enterprise_profile(project_type)
    enterprise_override = payload.get("enterprise_profile_override")
    if isinstance(enterprise_override, dict) and enterprise_override:
        enterprise_profile = _deep_merge_dict(enterprise_profile, enterprise_override)
    strict_tender_outline = bool(payload.get("strict_tender_outline", False))
    if strict_tender_outline:
        # 严格模式：目录与招标/评审标准保持一致，不自动补章、不改名。
        outline = _dedup_lines(outline if isinstance(outline, list) else [], limit=80)
    else:
        # 非严格模式：可按项目类型补齐缺失章节。
        outline = enrich_outline(outline if isinstance(outline, list) else [], project_type=project_type)
    # 版式策略：招标有明确要求时覆盖；否则用系统默认（22磅+2.5/2.0边距+宋体三号/四号）。
    style, style_source = resolve_style(user_style=style, tender_style=tender_style)
    # 页数策略：默认按 50 页规划；若招标明确上限则以招标为准；
    # 若招标未明确上限，可使用 total_pages_target（例如 2000 页）作为目标。
    user_total_pages_target = None
    try:
        _raw_tp = payload.get("total_pages_target")
        if _raw_tp is not None and int(_raw_tp) > 0:
            user_total_pages_target = int(_raw_tp)
    except Exception:
        user_total_pages_target = None
    total_pages_limit = infer_total_page_limit(
        tender,
        default=50,
        override=user_total_pages_target,
    )
    chapter_pages = plan_chapter_pages(
        outline,
        total_pages=total_pages_limit,
        chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
    )
    # 图表策略：若调用方未设置频率，按章页权重自动建议。
    chart_policy = style.get("chart_policy") if isinstance(style.get("chart_policy"), dict) else {}
    chart_policy = dict(chart_policy or {})
    chart_policy["enabled"] = bool(chart_policy.get("enabled", True))
    chart_policy["mode"] = str(chart_policy.get("mode") or "page_density_auto").strip() or "page_density_auto"
    chart_policy["position"] = chart_policy.get("position") or "chapter"
    # Backward-compatibility: legacy chapter-frequency mode still works.
    if chart_policy["mode"] in {"chapter_frequency", "legacy_every_n"}:
        if "every_n_chapters" not in chart_policy:
            chart_policy["every_n_chapters"] = recommend_chart_every_n(outline, chapter_pages)
    else:
        chart_policy["every_n_chapters"] = int(chart_policy.get("every_n_chapters") or 2)
    style["chart_policy"] = chart_policy
    if total_pages_limit:
        tender_globals.append(f"总页数不超过{total_pages_limit}页。")
    if style_source == "tender_override":
        tender_globals.append("字体/字号/行距/页边距等版式参数必须严格按招标文件要求执行，不得改写。")
    boq = payload.get("boq_data") or load_boq_data(project_id=project_id) or {}
    boq_wbs_cpm = build_boq_wbs_cpm(boq, enterprise_profile=enterprise_profile)
    missing_param_probe = probe_missing_parameters(
        topic=str(topic),
        outline=[str(x) for x in (outline or []) if str(x).strip()],
        requirements=[str(x) for x in (requirements or []) if str(x).strip()] + tender_globals,
        tender=tender if isinstance(tender, dict) else {},
        boq=boq if isinstance(boq, dict) else {},
        enterprise_profile=enterprise_profile if isinstance(enterprise_profile, dict) else {},
    )
    schedule_constraints: List[str] = []
    cpm_summary = boq_wbs_cpm.get("summary") if isinstance(boq_wbs_cpm, dict) else {}
    if isinstance(cpm_summary, dict) and cpm_summary:
        est_days = cpm_summary.get("estimated_duration_days")
        peak = cpm_summary.get("resource_peak")
        cp_gap = cpm_summary.get("critical_interval_days")
        cp_names = [str(x).strip() for x in (cpm_summary.get("critical_path_names") or []) if str(x).strip()]
        if est_days:
            schedule_constraints.append(f"计划口径统一：总工期={est_days}天。")
        if peak:
            schedule_constraints.append(f"计划口径统一：资源峰值={peak}人（当量）。")
        if cp_gap:
            schedule_constraints.append(f"计划口径统一：关键线路间隔={cp_gap}天。")
        if cp_names:
            schedule_constraints.append(f"关键线路工序：{'→'.join(cp_names[:8])}。")
    missing_defaults = missing_param_probe.get("auto_fill") if isinstance(missing_param_probe, dict) else {}
    if isinstance(missing_defaults, dict):
        for k, v in missing_defaults.items():
            kk = str(k).strip()
            vv = str(v).strip()
            if kk and vv:
                schedule_constraints.append(f"参数缺失自动补位：{kk}={vv}【经验值:企业参数库】")
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
    base_requirements.extend(schedule_constraints)
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
    agent_contract = build_agent_contract(
        topic=str(topic),
        outline=outline if isinstance(outline, list) else [],
        chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
        chapter_requirements=chapter_requirements if isinstance(chapter_requirements, dict) else {},
        multi_agent_summary=multi_agent_plan.summary(),
        chapter_specialties=multi_agent_plan.chapter_specialties,
    )
    chapter_contract_map = {
        str(ch.get("title") or "").strip(): ch
        for ch in (agent_contract.get("chapters") or [])
        if isinstance(ch, dict) and str(ch.get("title") or "").strip()
    }

    def _pick_provider(idx: int) -> tuple[str | None, str | None, str | None, str | None]:
        if provider_chain:
            entry = provider_chain[idx % len(provider_chain)]
            return (
                str(entry.get("provider") or "").strip().lower() or None,
                str(entry.get("model") or "").strip() or None,
                str(entry.get("api_key") or "").strip() or None,
                str(entry.get("slot") or "").strip() or None,
            )
        if providers:
            p = providers[idx % len(providers)]
            m = model_map.get(p) or model
            return p, m, None, None
        return provider, model, None, None

    weights, penalties = _build_weights_and_penalties(tender)
    chars_per_page_hint = _estimate_chars_per_page(style)
    labor_matrix_cfg = load_labor_allocation_matrix()

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

    try:
        agent_parallelism = int(payload.get("agent_parallelism") or 4)
    except Exception:
        agent_parallelism = 4
    agent_parallelism = max(1, min(16, agent_parallelism))
    section_sem = asyncio.Semaphore(agent_parallelism)

    def _build_case_pack_for_section(title: str) -> dict[str, Any]:
        try:
            return build_case_reference_pack(
                options=case_library_options,
                topic=str(topic),
                chapter_title=str(title),
                project_type=project_type,
                audit_path=reference_library_audit_path,
            )
        except Exception as e:
            return {
                "enabled": bool(case_library_options.get("enabled")),
                "requested_selected_case_ids": [],
                "selected_case_ids": [],
                "matched_project_type": project_type,
                "matched_chapter": str(title or "").strip() or None,
                "match_reason": "reference_pack_error",
                "style_hints": [],
                "structure_hints": [],
                "reference_lines": [],
                "non_fact_reference_notice": "",
                "hits": [],
                "warning_list": [f"case_reference_pack_error:{repr(e)}"],
            }

    def _build_image_pack_for_section(title: str) -> dict[str, Any]:
        try:
            return build_image_selection_pack(
                options=image_library_options,
                topic=str(topic),
                chapter_title=str(title),
                project_type=project_type,
                tags=[str(title)],
                audit_path=reference_library_audit_path,
            )
        except Exception as e:
            return {
                "enabled": bool(image_library_options.get("enabled")),
                "requested_selected_image_ids": [],
                "selected_image_ids": [],
                "matched_project_type": project_type,
                "matched_chapter": str(title or "").strip() or None,
                "match_reason": "reference_pack_error",
                "insertion_hint": "",
                "caption_hint": "",
                "images": [],
                "warning_list": [f"image_selection_pack_error:{repr(e)}"],
            }

    def _reference_pack_summary(pack: Any, *, id_key: str, item_key: str) -> dict[str, Any]:
        data = pack if isinstance(pack, dict) else {}
        items = data.get(item_key) if isinstance(data.get(item_key), list) else []
        return {
            "enabled": bool(data.get("enabled", False)),
            id_key: [
                str(x).strip()
                for x in (data.get(id_key) or [])
                if str(x).strip()
            ],
            "matched_project_type": str(data.get("matched_project_type") or "").strip() or None,
            "matched_chapter": str(data.get("matched_chapter") or "").strip() or None,
            "match_reason": str(data.get("match_reason") or "").strip() or None,
            "hit_count": len(items),
            "warning_list": [
                str(x).strip()
                for x in (data.get("warning_list") or [])
                if str(x).strip()
            ],
        }

    def _aggregate_reference_packs(rows: list[dict[str, Any]], *, pack_key: str, id_key: str, item_key: str) -> dict[str, Any]:
        chapter_summaries: list[dict[str, Any]] = []
        selected_ids: list[str] = []
        warnings: list[str] = []
        enabled = False
        seen_ids: set[str] = set()
        seen_warnings: set[str] = set()
        for row in rows:
            pack = row.get(pack_key) if isinstance(row, dict) else None
            summary = _reference_pack_summary(pack, id_key=id_key, item_key=item_key)
            enabled = enabled or bool(summary.get("enabled"))
            chapter_summaries.append(summary)
            for item_id in summary.get(id_key) or []:
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                selected_ids.append(item_id)
            for warning in summary.get("warning_list") or []:
                if warning in seen_warnings:
                    continue
                seen_warnings.add(warning)
                warnings.append(warning)
        return {
            "enabled": bool(enabled),
            id_key: selected_ids,
            "chapters": chapter_summaries,
            "warning_list": warnings,
        }

    async def build_section(idx: int, title: str):
        # 章节级重试：多模型轮询重试，最多尝试 3 个 provider（主+备1+备2）
        tries = []
        if provider_chain:
            for i in range(len(provider_chain)):
                p, m, k, sid = _pick_provider(idx + i)
                tries.append((p, m, k, sid))
        elif providers:
            for i in range(len(providers)):
                p, m, k, sid = _pick_provider(idx + i)
                tries.append((p, m, k, sid))
        else:
            tries.append((provider, model, None, None))
        tries = tries[:5]
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
        chapter_contract = chapter_contract_map.get(str(title).strip()) if isinstance(chapter_contract_map, dict) else None
        if isinstance(chapter_contract, dict):
            for req_line in chapter_contract.get("requirements") or []:
                line = str(req_line).strip()
                if line:
                    section_requirements.append(f"本章合同要求：{line}")
        # Chapter blueprint: when the tender outline contains a known chapter theme,
        # inject the corresponding "章内结构" guidance (does not change outline).
        bp = None
        try:
            from backend.zhifei_autoplan.chapter_blueprints import match_chapter_blueprint
            bp = match_chapter_blueprint(title)
        except Exception:
            bp = None
        chapter_target_pages = _extract_chapter_page_target(chapter_pages, title)
        if chapter_target_pages is None and isinstance(chapter_contract, dict):
            chapter_target_pages = _to_int_or_none(chapter_contract.get("page_target"))
        if chapter_target_pages:
            target_chars = max(200, chapter_target_pages * chars_per_page_hint)
            section_requirements.append(
                f"本章目标页数：{chapter_target_pages}页（建议正文约{target_chars}字，允许±20%）"
            )
        labor_hint = suggest_labor_ratio_for_chapter(
            labor_matrix_cfg,
            project_type=project_type,
            chapter_title=title,
        )
        if labor_hint and any(k in title for k in ("劳动力", "资源", "班组", "人员", "组织机构", "施工部署")):
            skill_ratio = labor_hint.get("skill_ratio") if isinstance(labor_hint.get("skill_ratio"), dict) else {}
            trade_ratio = labor_hint.get("trade_ratio") if isinstance(labor_hint.get("trade_ratio"), dict) else {}
            section_requirements.append(
                "劳动力配比应按《安徽技能工人配备标准》算法矩阵编制（允许结合项目特征微调，但需说明依据）。"
            )
            section_requirements.append(
                f"建议矩阵：项目类型={labor_hint.get('project_type')}；规模={labor_hint.get('size')}；阶段={labor_hint.get('stage')}；阶段说明={labor_hint.get('stage_detail')}"
            )
            if skill_ratio:
                section_requirements.append(
                    "技能等级比例："
                    + "；".join([f"{k}={v}" for k, v in skill_ratio.items() if str(k).strip() and str(v).strip()][:8])
                )
            if trade_ratio:
                section_requirements.append(
                    "工种配置比例："
                    + "；".join([f"{k}={v}" for k, v in trade_ratio.items() if str(k).strip() and str(v).strip()][:10])
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
        # Compliance retrieval: pre-filter by involved domain + prefer latest standard version.
        compliance_domains = [str(x).strip() for x in (graph_ctx.get("agents", {}).get("domain_tags") or []) if str(x).strip()]
        if not compliance_domains:
            compliance_domains = [str(x).strip() for x in (multi_agent_plan.dispatch.get("involved_domains") or []) if str(x).strip()]
        compliance_hits = query_compliance(
            f"{topic} {title} 质量 安全 工期 验收 允许偏差 抽检 频次",
            domain_tags=compliance_domains or None,
            top_k=4,
            prefer_latest=True,
        )
        if compliance_hits:
            section_requirements.append("本章应优先引用适配专业且最新版本的规范条款（禁止跨专业串用规范）。")
            for ch in compliance_hits[:4]:
                ctype = str(ch.get("type") or "").strip()
                code = str(ch.get("standard_code") or "").strip()
                locator = str(ch.get("locator") or "").strip()
                if ctype == "parameter":
                    p_name = str(ch.get("parameter_name") or "参数").strip()
                    p_val = str(ch.get("value") or "").strip()
                    p_unit = str(ch.get("unit") or "").strip()
                    section_requirements.append(
                        f"规范参数建议：{code} {p_name}={p_val}{p_unit}【证据:{locator}】"
                    )
                else:
                    c_no = str(ch.get("clause_no") or "").strip()
                    c_text = str(ch.get("text") or "").strip()
                    preview = c_text[:90]
                    if c_no:
                        section_requirements.append(
                            f"规范强条：{code} {c_no} {preview}【证据:{locator}】"
                        )
                    else:
                        section_requirements.append(
                            f"规范强条：{code} {preview}【证据:{locator}】"
                        )
                # Merge as evidence context for writer prompt grounding.
                txt = str(ch.get("text") or "").strip()
                if txt:
                    kg_evidence.append(f"规范/{code}: {txt}")
        kg_evidence = _dedup_lines(kg_evidence, limit=16)

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
            # Use numeric index for templates so v1..vN can map to A/B/C/D/E deterministically.
            "variant_id": variant_index,
            "logic_template": {"id": "A", "name": "交付清单驱动"},
            "chapter_domain": "general",
            "master_agent": graph_ctx.get("agents", {}).get("master") or multi_agent_plan.master_agent,
            "specialist_agents": graph_ctx.get("agents", {}).get("specialists") or [],
            "compliance_agent": graph_ctx.get("agents", {}).get("compliance") or multi_agent_plan.compliance_agent,
            "specialty_tags": graph_ctx.get("agents", {}).get("specialty_tags") or [],
            "graph_nodes": graph_ctx.get("node_bindings") or [],
            "graph_experience_values": exp_values,
            "chapter_contract": chapter_contract or {},
            "enterprise_profile": enterprise_profile,
            "missing_param_probe": missing_param_probe,
            "boq_wbs_cpm_summary": cpm_summary if isinstance(cpm_summary, dict) else {},
            "boq_wbs_top_process": (boq_wbs_cpm.get("wbs") or [])[:8] if isinstance(boq_wbs_cpm, dict) else [],
            "labor_hint": labor_hint if isinstance(labor_hint, dict) else {},
            "compliance_hits": compliance_hits if isinstance(compliance_hits, list) else [],
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
            if isinstance(chapter_contract, dict):
                ccid = str(chapter_contract.get("chapter_id") or "").strip()
                if ccid:
                    rec.setdefault("contract_chapter_id", ccid)
            return rec

        last = None
        for p, m, key_override, slot_id in tries:
            llm = None
            if p and m and not dry_run:
                try:
                    llm = LLMClient(
                        provider=p,
                        model=m,
                        api_key=_resolve_provider_api_key(
                            payload,
                            p,
                            slot_id=slot_id,
                            explicit_key=key_override,
                        ),
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

    async def _build_section_with_limit(idx: int, title: str):
        async with section_sem:
            return await build_section(idx, title)

    sections = await asyncio.gather(*[_build_section_with_limit(i, t) for i, t in enumerate(outline)])
    for sec in sections:
        sec["content"] = strip_nonconcrete_language(sec.get("content") or "")
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip()
        sec.setdefault("case_reference_pack", _build_case_pack_for_section(title))
        sec.setdefault("image_selection_pack", _build_image_pack_for_section(title))
    case_reference_pack = _aggregate_reference_packs(
        sections,
        pack_key="case_reference_pack",
        id_key="selected_case_ids",
        item_key="hits",
    )
    image_selection_pack = _aggregate_reference_packs(
        sections,
        pack_key="image_selection_pack",
        id_key="selected_image_ids",
        item_key="images",
    )
    pipeline_stages: List[Dict[str, Any]] = [
        {"stage": "draft_generation", "ok": True, "chapter_count": len(sections)}
    ]

    def _run_contract_checks(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for sec in rows:
            title = str(sec.get("title") or "").strip()
            if not title:
                continue
            ch_contract = chapter_contract_map.get(title)
            if not isinstance(ch_contract, dict):
                continue
            results.append(validate_section_with_contract(sec, ch_contract))
        err_cnt = sum(len(r.get("errors") or []) for r in results)
        warn_cnt = sum(len(r.get("warnings") or []) for r in results)
        return {
            "ok": all(bool(r.get("ok")) for r in results) if results else True,
            "error_count": int(err_cnt),
            "warning_count": int(warn_cnt),
            "by_section": results,
        }

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
    quality_draft: Dict[str, Any] | None = None
    if payload.get("auto_remediate", True):
        quality_draft = run_quality_checks(
            tender,
            outline,
            sections,
            boq=boq,
            boq_focus=boq_focus,
            project_id=project_id,
            strict=strict_quality,
        )
        pipeline_stages.append(
            {
                "stage": "quality_draft",
                "ok": bool(quality_draft.get("score", 0) >= 60) if isinstance(quality_draft, dict) else True,
                "score": quality_draft.get("score") if isinstance(quality_draft, dict) else None,
            }
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
            for r in quality_draft.get("remediation") or []:
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
                quality_draft.get("remediation") or [],
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
        pipeline_stages.append(
            {
                "stage": "plan_consistency",
                "ok": bool((plan_receipt or {}).get("ok", True)),
            }
        )
    except Exception:
        plan_receipt = None
        pipeline_stages.append({"stage": "plan_consistency", "ok": False, "reason": "plan_consistency_exception"})

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

    terminology_audit = {"ok": True, "terminology_loaded": False, "entry_count": 0, "changed_sections": 0, "replacement_count": 0}
    try:
        terminology_audit = await normalize_sections_terminology_async(
            sections,
            provider=str(provider or ""),
            model=str(model or ""),
            api_key=_resolve_provider_api_key(payload, provider),
            use_llm=True,
        )
        pipeline_stages.append(
            {
                "stage": "terminology_audit",
                "ok": bool(terminology_audit.get("ok", True)),
                "terminology_loaded": bool(terminology_audit.get("terminology_loaded", False)),
                "entry_count": int(terminology_audit.get("entry_count") or 0),
                "changed_sections": int(terminology_audit.get("changed_sections") or 0),
                "replacement_count": int(terminology_audit.get("replacement_count") or 0),
            }
        )
    except Exception:
        terminology_audit = {"ok": False, "terminology_loaded": False, "entry_count": 0, "changed_sections": 0, "replacement_count": 0}
        pipeline_stages.append({"stage": "terminology_audit", "ok": False, "reason": "terminology_guard_exception"})

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
    contract_checks = _run_contract_checks(sections)
    quality["agent_contract"] = contract_checks
    if not bool(contract_checks.get("ok", True)):
        quality.setdefault("remediation", [])
        for row in contract_checks.get("by_section") or []:
            title = str(row.get("title") or "")
            for err in row.get("errors") or []:
                quality["remediation"].append(
                    {
                        "title": title,
                        "type": "agent_contract_gap",
                        "suggestion": f"章节未满足Agent合同：{err}",
                    }
                )
            for warn in row.get("warnings") or []:
                quality["remediation"].append(
                    {
                        "title": title,
                        "type": "agent_contract_warn",
                        "suggestion": f"建议增强章节合同项：{warn}",
                    }
                )
    pipeline_stages.append(
        {
            "stage": "quality_final",
            "ok": bool((quality.get("score") or 0) >= 60) and bool(contract_checks.get("ok", True)),
            "score": quality.get("score"),
            "contract_ok": bool(contract_checks.get("ok", True)),
        }
    )
    score_mapping = build_score_mapping(tender=tender if isinstance(tender, dict) else {}, sections=sections)
    pipeline_stages.append(
        {
            "stage": "score_mapping",
            "ok": bool(score_mapping.get("ok", False)),
            "high_risk_item_count": (
                (score_mapping.get("summary") or {}).get("high_risk_item_count")
                if isinstance(score_mapping, dict)
                else None
            ),
        }
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
    evidence_tracking = {}
    try:
        evidence_tracking = build_evidence_tracking(
            sections=sections,
            tender=tender if isinstance(tender, dict) else {},
            chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
        )
    except Exception:
        evidence_tracking = {"rows": [], "summary": {}}
    pipeline_stages.append(
        {
            "stage": "evidence_tracking",
            "ok": bool((evidence_tracking.get("summary") or {}).get("paragraph_count", 0) > 0),
            "paragraph_count": (evidence_tracking.get("summary") or {}).get("paragraph_count"),
            "score_point_bound_rows": (evidence_tracking.get("summary") or {}).get("score_point_bound_rows"),
            "traceable_locator_rows": (evidence_tracking.get("summary") or {}).get("traceable_locator_rows"),
        }
    )
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
        "generation_mode": payload.get("generation_mode"),
        "mode_policy": payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else None,
        "project_type": project_type,
        "global_instruction": global_instruction,
        "outline": outline,
        "sections": sections,
        "case_reference_pack": case_reference_pack,
        "image_selection_pack": image_selection_pack,
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
        "total_pages_target": user_total_pages_target,
        "total_pages_limit": total_pages_limit,
        "style": style,
        "style_source": style_source,
        "quality_strict": strict_quality,
        "boq_focus": boq_focus,
        "boq_wbs_cpm": boq_wbs_cpm,
        "missing_parameters": missing_param_probe,
        "enterprise_profile": enterprise_profile,
        "agent_contract": agent_contract,
        "agent_contract_checks": contract_checks,
        "score_mapping": score_mapping,
        "compare": {
            "mode": payload.get("compare_mode", "full"),
            "max_chars": int(payload.get("compare_max_chars") or 800),
            "titles": payload.get("compare_titles"),
        },
        "quality_checks": quality,
        "quality_checks_draft": quality_draft,
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
        "evidence_tracking": evidence_tracking,
        "plan_consistency": plan_receipt,
        "multi_agent": {
            **multi_agent_plan.summary(),
            "execution": {
                "parallel": True,
                "agent_parallelism": agent_parallelism,
                "chapter_count": len(outline),
            },
            "compliance": multi_agent_compliance,
        },
        "terminology_audit": terminology_audit,
        "pipeline_stages": pipeline_stages,
        "params_used": params_used,
    }
