from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Dict, Any, List

from backend.zhifei_autoplan.tender_store import load_tender_matrix
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.kg_runtime import search_kg
from backend.zhifei_autoplan.evidence import search_ingested_docs, format_hit_locator, best_ingested_hit
from backend.zhifei_autoplan.utils.llm_client import LLMClient
from backend.zhifei_autoplan.model_reliability import (
    ModelReliabilityRuntime,
    classify_provider_error,
    sanitize_provider_message,
)
from backend.zhifei_autoplan.provider_admission import (
    ProviderAdmissionManager,
    ProviderCandidate,
    canonical_digest as provider_admission_canonical_digest,
    public_snapshot as public_provider_admission_snapshot,
)
from backend.zhifei_autoplan.agents.section_writer import (
    SectionWriter,
    compact_chapter_summary,
)
from backend.zhifei_autoplan.media import generate_boq_chart, generate_ingested_previews, generate_outline_mindmap
from backend.zhifei_autoplan.quality_check import (
    run_quality_checks,
    apply_remediation,
    ensure_local_export_mandatory_content,
    strip_nonconcrete_language,
)
from backend.zhifei_autoplan.params_runtime import load_params, get_image_defaults
from backend.zhifei_autoplan.boq_focus_enforcer import ensure_boq_focus_item_cards
from backend.zhifei_autoplan.boq_focus_policy import (
    MAX_BOQ_FOCUS_ITEMS,
    normalize_boq_focus_items,
    normalize_boq_focus_name,
    select_boq_focus_names,
)
from backend.zhifei_autoplan.project_types import (
    detect_project_type,
    normalize_project_type,
    project_type_requirements,
)
from backend.zhifei_autoplan.style_policy import resolve_style_with_decisions
from backend.zhifei_autoplan.outline_planner import (
    enrich_outline,
    infer_total_page_limit,
    plan_chapter_pages,
    recommend_chart_every_n,
)
from backend.zhifei_autoplan.multi_agent_runtime import (
    build_agent_execution_ledger,
    build_multi_agent_plan,
)
from backend.zhifei_autoplan.enterprise_params import get_enterprise_profile
from backend.zhifei_autoplan.boq_schedule import (
    build_boq_wbs_cpm,
    sanitize_boq_for_generation,
)
from backend.zhifei_autoplan.missing_param_probe import probe_missing_parameters
from backend.zhifei_autoplan.agent_contract import build_agent_contract, validate_section_with_contract
from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger_from_inputs,
    project_fact_prompt_requirements,
    validate_project_fact_ledger,
)
from backend.zhifei_autoplan.score_mapper import build_score_mapping
from backend.zhifei_autoplan.evidence_tracking import build_evidence_tracking
from backend.zhifei_autoplan.requirement_evidence_matrix import (
    build_requirement_evidence_plan,
    finalize_requirement_evidence_matrix,
    requirement_prompt_lines_for_chapter,
    requirement_rows_for_chapter,
    scope_requirement_evidence_plan_to_chapters,
    validate_chapter_requirement_evidence,
    validate_requirement_evidence_matrix,
    validate_requirement_evidence_plan_readiness,
)
from backend.zhifei_autoplan.generation_checkpoint import (
    build_chapter_context_digest,
    build_generation_binding,
    checkpoint_summary,
    finalize_generation_checkpoint,
    load_section_checkpoint,
    save_section_checkpoint,
)
from backend.zhifei_autoplan.execution_control import (
    ExecutionBudgetExceededError,
    ExecutionCancelledError,
    ExecutionControlRuntime,
)
from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.case_library_service import (
    build_case_reference_pack,
    case_reference_prompt_requirements,
)
from backend.zhifei_autoplan.image_library import build_image_selection_pack
from backend.zhifei_autoplan.compliance_runtime import (
    get_compliance_registry_status,
    list_verified_standard_metadata,
    query_compliance,
)
from backend.zhifei_autoplan.compliance_policy import (
    GLOBAL_COMPLIANCE_REQUIREMENT,
    audit_standard_citations,
    build_project_applicable_standards_manifest,
    canonical_standard_code,
    filter_evidence_to_verified_standard_codes,
    replace_unverified_standard_citations,
    standard_citation_directive,
)
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


class GenerationCancelledError(RuntimeError):
    """Raised when the owning job has been cancelled by the user."""

SYSTEM_MANDATORY_REQUIREMENTS = [
    GLOBAL_COMPLIANCE_REQUIREMENT,
    "风险条目必须采用“风险→控制→验证”三元组表达，且逐条闭环。",
    "每章应包含可量化指标，优先覆盖：频次、阈值、间距、厚度、时长、人数、设备型号。",
    "不得使用空泛表述（如“加强、确保、严格”）替代可执行措施与量化参数。",
    "涉及工期、资源峰值、关键线路间隔的数据需前后保持一致。",
    "对特殊材料、危险品材料、劳保用品、技术工种配置、绿色工地、信息化管理必须有具体内容。",
    "四新技术应用需结合本项目工序与成本收益，写清适用条件、责任工种、实施步骤和验收指标。",
    f"工种名称应使用规范称谓，例如：{'、'.join(STANDARD_TRADES)}。",
    "全文禁止官话、套话、空话，不得出现“加强、确保、严格、压实责任、形成合力、高质量推进”等无落地表达。",
]

_CRITICAL_REVIEW_KEYWORDS = (
    "总体",
    "部署",
    "重难点",
    "关键",
    "质量",
    "安全",
    "进度",
    "工期",
    "专项",
    "应急",
    "消防",
    "验收",
    "风险",
)


def _is_critical_review_chapter(title: str | None) -> bool:
    normalized = str(title or "").strip()
    return bool(normalized and any(keyword in normalized for keyword in _CRITICAL_REVIEW_KEYWORDS))


def _has_tiered_anthropic_route(chain: List[Dict[str, Any]]) -> bool:
    slots = {str(item.get("slot") or "").strip() for item in chain if isinstance(item, dict)}
    return "text_draft" in slots and "text_review" in slots


def _provider_chain_for_role(
    chain: List[Dict[str, Any]],
    role: str,
    *,
    allow_fable_escalation: bool = False,
) -> List[Dict[str, Any]]:
    """Return a stable role-aware chain while keeping Fable opt-in only."""
    if not _has_tiered_anthropic_route(chain):
        return [dict(item) for item in chain if isinstance(item, dict)]

    if role == "review":
        order = ["text_review"]
        if allow_fable_escalation:
            order.append("text_escalation")
        order.extend(["text_backup", "text_draft", "text_main", "text_compat_google"])
    else:
        order = ["text_draft", "text_backup", "text_review", "text_main", "text_compat_google"]
        if allow_fable_escalation:
            order.append("text_escalation")

    slot_map = {
        str(item.get("slot") or "").strip(): dict(item)
        for item in chain
        if isinstance(item, dict) and str(item.get("slot") or "").strip()
    }
    ordered: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for slot in order:
        item = slot_map.get(slot)
        if item is None:
            continue
        seen.add(slot)
        ordered.append(item)
    for item in chain:
        if not isinstance(item, dict):
            continue
        slot = str(item.get("slot") or "").strip()
        if slot in seen or (slot == "text_escalation" and not allow_fable_escalation):
            continue
        seen.add(slot)
        ordered.append(dict(item))
    return ordered


def _model_role_for_slot(slot_id: str | None) -> str:
    return {
        "text_draft": "draft",
        "text_review": "review",
        "text_escalation": "escalation",
        "text_backup": "fallback",
        "text_compat_google": "fallback",
    }.get(str(slot_id or "").strip(), "legacy")


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


def _normalize_delivery_scope(value: Any) -> str:
    scope = str(value or "document").strip().lower()
    if scope not in {"document", "chapter_validation"}:
        raise ValueError("交付范围无效：delivery_scope 必须为 document 或 chapter_validation。")
    return scope


def _validate_strict_outline_for_scope(
    requested_outline: List[str],
    tender_outline: List[str],
    *,
    delivery_scope: str,
) -> None:
    if not tender_outline:
        return
    if delivery_scope == "document":
        if requested_outline != tender_outline:
            raise ValueError(
                "TENDER_OUTLINE_MISMATCH："
                "严格正式交付目录与招标目录不一致，已在模型调用前停止。"
            )
        return
    unknown = [title for title in requested_outline if title not in tender_outline]
    if unknown:
        raise ValueError(
            "CHAPTER_VALIDATION_OUTLINE_INVALID："
            "章节验证目录包含招标目录外章节，已在模型调用前停止："
            + "、".join(unknown[:20])
        )


def _build_chapter_validation_quality_gate(
    *,
    quality: Dict[str, Any],
    contract_checks: Dict[str, Any],
    delivery_quality_gate: Dict[str, Any],
) -> Dict[str, Any]:
    """Enforce chapter-level quality without pretending to validate a document."""

    checks: List[Dict[str, Any]] = []
    blocker_codes: List[str] = []
    for key in (
        "structure",
        "officialese",
        "risk_triplet",
        "logic_template_adherence",
        "quantitative",
        "required_topics_detail",
        "evidence_traceability",
        "standard_evidence",
    ):
        value = quality.get(key) if isinstance(quality.get(key), dict) else {}
        passed = value.get("ok") is True
        checks.append({"name": key, "pass": passed})
        if not passed:
            blocker_codes.append(f"CHAPTER_CHECK_{key.upper()}_BLOCKED")

    review = (
        quality.get("independent_content_review")
        if isinstance(quality.get("independent_content_review"), dict)
        else {}
    )
    section_threshold = int(review.get("section_threshold") or 60)
    section_rows = [
        row for row in (review.get("by_section") or []) if isinstance(row, dict)
    ]
    sections_ok = bool(section_rows) and all(
        int(row.get("score") or 0) >= section_threshold
        and str(row.get("status") or "").lower() != "blocked"
        for row in section_rows
    )
    checks.append(
        {
            "name": "independent_section_quality",
            "pass": sections_ok,
            "threshold": section_threshold,
            "section_count": len(section_rows),
        }
    )
    if not sections_ok:
        blocker_codes.append("CHAPTER_SECTION_QUALITY_BLOCKED")

    contract_ok = bool(contract_checks.get("ok"))
    checks.append({"name": "agent_contract", "pass": contract_ok})
    if not contract_ok:
        blocker_codes.append("CHAPTER_AGENT_CONTRACT_BLOCKED")

    model_check = next(
        (
            row
            for row in (delivery_quality_gate.get("checks") or [])
            if isinstance(row, dict) and row.get("name") == "independent_model_review"
        ),
        {},
    )
    model_ok = bool(model_check.get("pass"))
    checks.append({"name": "independent_model_review", "pass": model_ok})
    if not model_ok:
        blocker_codes.append("CHAPTER_MODEL_REVIEW_BLOCKED")

    blocker_codes = list(dict.fromkeys(blocker_codes))
    return {
        "schema_version": "chapter-validation-quality-v1",
        "pass": not blocker_codes,
        "checks": checks,
        "blocker_codes": blocker_codes,
    }


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


def _chapter_deadline_seconds(
    payload: Dict[str, Any],
    *,
    target_pages: int | None,
) -> int:
    """Return one bounded chapter deadline that can include a continuation.

    A long chapter may legitimately need two provider requests when the first
    response stops at the output-token limit.  The former 480-second ceiling
    could cancel that bounded continuation (or the next admitted provider)
    even though each individual request respected its 240-second deadline.
    """

    # 900 seconds leaves bounded room for initial+continuation plus one
    # admitted fallback request (each individual request remains <=240s).
    default_seconds = 900 if int(target_pages or 0) >= 8 else 480
    raw = payload.get("chapter_deadline_seconds")
    try:
        requested = int(raw) if raw is not None else default_seconds
    except (TypeError, ValueError):
        requested = default_seconds
    return max(60, min(900, requested))


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
            name = normalize_boq_focus_name(it.get("name"))
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
            if name:
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
        "must_cover_keywords": select_boq_focus_names(
            stats,
            limit=MAX_BOQ_FOCUS_ITEMS,
        ),
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

    # Production chains persist only a key alias.  Resolve the credential from
    # the server-owned slot at call time so plaintext never enters job payloads,
    # checkpoints, events, or output JSON.
    try:
        from backend.zhifei_autoplan.provider_runtime import (
            resolve_provider_slot_credentials,
        )

        server_key, _server_alias = resolve_provider_slot_credentials(slot_id, p)
        if isinstance(server_key, str) and server_key.strip():
            return server_key.strip()
    except Exception:
        pass

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
            key_alias = str(item.get("key_alias") or "").strip()
            chain.append(
                {
                    "slot": slot,
                    "provider": provider,
                    "model": model,
                    "api_key": api_key,
                    "key_alias": key_alias,
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


_PROVIDER_ADMISSION_MANAGERS: Dict[tuple[str, float], ProviderAdmissionManager] = {}
# Test modules may patch this in-process boolean.  It is deliberately not an
# environment variable or payload field, so HTTP clients and launch scripts
# cannot turn provider admission off.
_ALLOW_UNADMITTED_PROVIDER_CALLS_FOR_TESTS = False


class ProviderAdmissionRunCoordinator:
    """One fresh admission task shared by every variant in one generation run."""

    def __init__(self, manager: ProviderAdmissionManager) -> None:
        self.manager = manager
        self._task: asyncio.Task[Dict[str, Any]] | None = None
        self._candidates: tuple[ProviderCandidate, ...] = ()
        self._required_roles: tuple[str, ...] = ()
        self._snapshot: Dict[str, Any] | None = None
        self._events_claimed = False

    @property
    def bound_candidates(self) -> tuple[ProviderCandidate, ...]:
        return self._candidates

    def claim_event_emitter(self) -> bool:
        if self._events_claimed:
            return False
        self._events_claimed = True
        return True

    def admitted_candidate(self, role: str) -> ProviderCandidate | None:
        if not isinstance(self._snapshot, dict):
            return None
        admitted = {
            str(item.get("identity_digest") or "")
            for item in (self._snapshot.get("admitted_chain") or [])
            if isinstance(item, dict)
        }
        normalized_role = str(role or "").strip().lower()
        return next(
            (
                candidate
                for candidate in self._candidates
                if candidate.role == normalized_role
                and candidate.identity_digest in admitted
            ),
            None,
        )

    async def admit_chain_once(
        self,
        *,
        candidates: List[ProviderCandidate],
        probe: Any,
        required_roles: List[str],
    ) -> Dict[str, Any]:
        if self._snapshot is not None:
            if (
                tuple(candidate.identity_digest for candidate in candidates)
                != tuple(candidate.identity_digest for candidate in self._candidates)
                or tuple(required_roles) != self._required_roles
            ):
                raise RuntimeError("provider_admission_route_changed_during_run")
            return dict(self._snapshot)
        loop = asyncio.get_running_loop()
        if self._task is not None and self._task.get_loop() is not loop:
            raise RuntimeError("provider_admission_run_loop_mismatch")
        if self._task is None:
            self._candidates = tuple(candidates)
            self._required_roles = tuple(required_roles)
            self._task = loop.create_task(
                self.manager.admit_chain(
                    candidates=self._candidates,
                    probe=probe,
                    required_roles=self._required_roles,
                    force=True,
                )
            )
        elif (
            tuple(candidate.identity_digest for candidate in candidates)
            != tuple(candidate.identity_digest for candidate in self._candidates)
            or tuple(required_roles) != self._required_roles
        ):
            raise RuntimeError("provider_admission_route_changed_during_run")
        result = await asyncio.shield(self._task)
        self._snapshot = dict(result)
        return result


def _provider_admission_manager(payload: Dict[str, Any]) -> ProviderAdmissionManager:
    supplied = payload.get("_provider_admission_manager")
    if isinstance(supplied, ProviderAdmissionManager):
        return supplied
    configured_root = payload.get("_provider_admission_root") or os.environ.get(
        "ZF_PROVIDER_ADMISSION_STATE_DIR"
    )
    root = str(configured_root or "").strip() or None
    try:
        ttl = max(
            30.0,
            min(
                1800.0,
                float(
                    payload.get("provider_admission_ttl_seconds")
                    or os.environ.get("ZF_PROVIDER_ADMISSION_TTL_SECONDS")
                    or 300.0
                ),
            ),
        )
    except (TypeError, ValueError):
        ttl = 300.0
    key = (root or "<module-default>", ttl)
    manager = _PROVIDER_ADMISSION_MANAGERS.get(key)
    if manager is None:
        manager = ProviderAdmissionManager(root=root, ttl_seconds=ttl)
        _PROVIDER_ADMISSION_MANAGERS[key] = manager
    return manager


def new_provider_admission_run_coordinator(
    payload: Dict[str, Any],
) -> ProviderAdmissionRunCoordinator:
    return ProviderAdmissionRunCoordinator(_provider_admission_manager(payload))


def _provider_admission_candidates(
    payload: Dict[str, Any],
    provider_chain: List[Dict[str, Any]],
) -> List[ProviderCandidate]:
    raw_candidates = list(provider_chain)
    extra = payload.get("_provider_admission_extra_slots")
    if isinstance(extra, list):
        raw_candidates.extend(item for item in extra if isinstance(item, dict))
    candidates: List[ProviderCandidate] = []
    for item in raw_candidates:
        provider = str(item.get("provider") or "").strip().lower()
        model = str(item.get("model") or "").strip()
        slot = str(item.get("slot") or "").strip().lower()
        if not provider or not model or not slot:
            continue
        credential = _resolve_provider_api_key(
            payload,
            provider,
            slot_id=slot,
            explicit_key=str(item.get("api_key") or "").strip() or None,
        )
        role = str(item.get("role") or slot).strip().lower()
        if role == "text_escalation" and not bool(
            payload.get("allow_fable_escalation", False)
        ):
            continue
        stream_required = role.startswith("text_")
        candidates.append(
            ProviderCandidate(
                slot=slot,
                role=role,
                provider=provider,
                model=model,
                credential=str(credential or ""),
                key_alias=str(item.get("key_alias") or ""),
                stream_required=stream_required,
                stream_supported=(
                    provider in {"openai", "anthropic", "google"}
                    if stream_required
                    else True
                ),
            )
        )
    return candidates


async def probe_provider_candidate(
    candidate: ProviderCandidate,
    *,
    reliability_runtime: ModelReliabilityRuntime | None = None,
    execution_runtime: ExecutionControlRuntime | None = None,
) -> Dict[str, Any]:
    """Run one minimal, streamed, credential-bound admission probe."""

    started = time.monotonic()
    client = LLMClient(
        provider=candidate.provider,
        model=candidate.model,
        api_key=candidate.credential,
        reliability_runtime=reliability_runtime,
        reliability_identity=candidate.identity_digest,
        retry_attempts=1,
        execution_runtime=execution_runtime,
    )
    try:
        receipt = await client.preflight(timeout=60.0)
    finally:
        client.close()
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    if bool(receipt.get("ok")):
        if candidate.stream_required and not bool(receipt.get("streamed")):
            return {
                "ok": False,
                "code": "stream_unavailable",
                "stream": {"status": "fail", "code": "stream_unavailable"},
                "elapsed_ms": elapsed_ms,
            }
        return {
            "ok": True,
            "code": "probe_passed",
            "stream": (
                {"status": "pass", "code": "stream_ready"}
                if candidate.stream_required
                else {"status": "skipped", "code": "stream_not_required"}
            ),
            "elapsed_ms": elapsed_ms,
        }
    error_info = classify_provider_error(
        receipt.get("error_info") or receipt.get("error") or "provider_error",
        provider=candidate.provider,
        model=candidate.model,
    )
    return {
        "ok": False,
        "code": str(error_info.get("code") or "provider_error"),
        "elapsed_ms": elapsed_ms,
    }


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
    try:
        agent_parallelism = int(payload.get("agent_parallelism") or 4)
    except Exception:
        agent_parallelism = 4
    agent_parallelism = max(1, min(16, agent_parallelism))
    try:
        requested_model_parallelism = int(
            payload.get("max_model_parallelism") or min(agent_parallelism, 2)
        )
    except Exception:
        requested_model_parallelism = min(agent_parallelism, 2)
    max_model_parallelism = max(
        1, min(8, agent_parallelism, requested_model_parallelism)
    )
    try:
        requested_failure_threshold = int(
            payload.get("model_circuit_failure_threshold")
            or 2
        )
    except Exception:
        requested_failure_threshold = 2
    model_circuit_failure_threshold = max(
        2, min(16, requested_failure_threshold)
    )
    model_reliability = ModelReliabilityRuntime(
        failure_threshold=model_circuit_failure_threshold
    )
    model_preflight_receipts: List[Dict[str, Any]] = []
    progress_callback = payload.get("_progress_callback")
    cancel_callback = payload.get("_cancel_callback")
    checkpoint_write_guard = payload.get("_checkpoint_write_guard")
    execution_runtime = payload.get("_execution_runtime")
    if not isinstance(execution_runtime, ExecutionControlRuntime):
        execution_runtime = ExecutionControlRuntime(
            max_concurrency=max_model_parallelism,
            max_model_attempts=int(payload.get("max_model_attempts") or 256),
            max_input_chars=int(payload.get("max_model_input_chars") or 24_000_000),
            max_requested_output_tokens=int(
                payload.get("max_model_output_tokens") or 3_000_000
            ),
            cancel_callback=cancel_callback if callable(cancel_callback) else None,
        )

    def _raise_if_cancelled(stage: str) -> None:
        if not callable(cancel_callback):
            return
        try:
            cancelled = bool(cancel_callback())
        except Exception:
            # Cancellation is a control-plane decision.  A broken probe must not
            # silently cancel or change the generated document.
            cancelled = False
        if cancelled:
            raise GenerationCancelledError(f"cancelled_by_user:{stage}")

    def _write_checkpoint(callback: Any, **kwargs: Any) -> Dict[str, Any]:
        _raise_if_cancelled("before_checkpoint_write")
        if callable(checkpoint_write_guard):
            return checkpoint_write_guard(callback, **kwargs)
        return callback(**kwargs)

    def _emit_progress(event: str, **data: Any) -> None:
        if not callable(progress_callback):
            return
        try:
            progress_callback({"event": str(event or ""), **data})
        except Exception:
            # Observability must never change the generated document outcome.
            pass
    _raise_if_cancelled("run_started")
    _emit_progress("preflight_started", stage="project_context")
    if provider_chain:
        provider = provider_chain[0].get("provider") or provider
        model = provider_chain[0].get("model") or model
    tiered_anthropic_route = _has_tiered_anthropic_route(provider_chain)
    allow_fable_escalation = bool(payload.get("allow_fable_escalation", False))
    dry_run = bool(payload.get("dry_run", False))

    def _emit_provider_progress(event: str, **data: Any) -> None:
        # Dry-run intentionally constructs deterministic fallback sections and
        # never sends a provider request.  Suppress provider-attempt telemetry
        # so monitoring cannot report a cache/model call that did not happen.
        if dry_run:
            return
        _emit_progress(event, **data)

    no_write_preview = bool(payload.get("no_write") or payload.get("preview_only"))
    strict_loopback_local_preview = bool(
        not dry_run
        and str(provider or "").strip().lower() == "ollama"
        and bool(payload.get("no_write"))
        and bool(payload.get("preview_only"))
        and str(payload.get("base_url") or "").strip().rstrip("/")
        == "http://127.0.0.1:11434"
        and not bool(payload.get("generate_images", False))
    )
    mandatory_provider_admission = bool(
        not dry_run
        and not strict_loopback_local_preview
        and not _ALLOW_UNADMITTED_PROVIDER_CALLS_FOR_TESTS
    )
    generate_images = (
        bool(payload.get("generate_images", True))
        and not no_write_preview
        and not dry_run
    )
    strict_quality = bool(payload.get("quality_strict", True))
    delivery_scope = _normalize_delivery_scope(payload.get("delivery_scope"))
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
    tender_outline = _dedup_lines(
        tender.get("outline") if isinstance(tender.get("outline"), list) else [],
        limit=80,
    )
    if strict_tender_outline or delivery_scope == "chapter_validation" or tender_outline:
        # 严格模式：目录与招标/评审标准保持一致，不自动补章、不改名。
        outline = _dedup_lines(outline if isinstance(outline, list) else [], limit=80)
    else:
        # 非严格模式：可按项目类型补齐缺失章节。
        outline = enrich_outline(outline if isinstance(outline, list) else [], project_type=project_type)
    if tender_outline:
        _validate_strict_outline_for_scope(
            outline,
            tender_outline,
            delivery_scope=delivery_scope,
        )
    # 版式策略：招标有明确要求时覆盖；否则用系统默认（22磅+2.5/2.0边距+宋体三号/四号）。
    tender_extraction_meta = tender.get("extraction_meta") if isinstance(tender.get("extraction_meta"), dict) else {}
    tender_requirement_matrix = (
        tender_extraction_meta.get("requirement_decision_matrix")
        if isinstance(tender_extraction_meta.get("requirement_decision_matrix"), dict)
        else None
    )
    approved_style_resolutions = payload.get("approved_style_resolutions")
    style, style_source, requirement_decision_matrix = resolve_style_with_decisions(
        user_style=style,
        tender_style=tender_style,
        tender_decision_matrix=tender_requirement_matrix,
        approved_resolutions=approved_style_resolutions if isinstance(approved_style_resolutions, dict) else None,
    )
    unresolved_style_fields = list(requirement_decision_matrix.get("unresolved_fields") or [])
    if unresolved_style_fields:
        raise ValueError(
            "招标文件/澄清答疑存在同优先级版式冲突，系统已停止自行裁决："
            + "、".join(str(field) for field in unresolved_style_fields)
            + "。请通过 approved_style_resolutions 提供经确认的冲突处理值。"
        )
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
    boq_source = payload.get("boq_data") or load_boq_data(project_id=project_id) or {}
    _emit_progress(
        "boq_schedule_started",
        item_count=(
            len(boq_source.get("items") or []) if isinstance(boq_source, dict) else 0
        ),
    )
    boq_wbs_cpm = build_boq_wbs_cpm(
        boq_source,
        enterprise_profile=enterprise_profile,
    )
    raw_cpm_summary = (
        boq_wbs_cpm.get("summary")
        if isinstance(boq_wbs_cpm.get("summary"), dict)
        else {}
    )
    if bool(raw_cpm_summary.get("schedule_fact_eligible", True)):
        cpm_summary = dict(raw_cpm_summary)
    else:
        # Keep the diagnostic state visible to downstream agents without
        # presenting an implausible derived duration as a usable project fact.
        cpm_summary = {
            "schedule_fact_eligible": False,
            "schedule_fact_ineligibility_reasons": list(
                raw_cpm_summary.get("schedule_fact_ineligibility_reasons") or []
            ),
        }
    boq = sanitize_boq_for_generation(boq_source)
    _emit_progress(
        "boq_schedule_completed",
        process_count=len(boq_wbs_cpm.get("wbs") or []),
        warning_count=len(boq_wbs_cpm.get("schedule_input_warnings") or []),
    )
    project_fact_ledger = build_project_fact_ledger_from_inputs(
        payload=payload,
        tender=tender if isinstance(tender, dict) else {},
        boq_wbs_cpm=boq_wbs_cpm if isinstance(boq_wbs_cpm, dict) else {},
    )
    project_fact_validation = validate_project_fact_ledger(project_fact_ledger)
    if strict_quality and not project_fact_validation.get("ok"):
        unresolved = [
            str(field)
            for field in (project_fact_validation.get("unresolved_fields") or [])
            if str(field)
        ]
        if unresolved:
            raise ValueError(
                "项目事实台账存在同优先级冲突，系统已在调用大模型前停止："
                + "、".join(unresolved)
                + "。请通过 approved_project_fact_resolutions 提供经确认的唯一值。"
            )
        raise ValueError("项目事实台账完整性校验未通过，系统已在调用大模型前停止。")
    _emit_progress(
        "project_facts_ready",
        status=project_fact_ledger.get("status"),
        ledger_digest=project_fact_ledger.get("ledger_digest"),
        fact_count=len(project_fact_ledger.get("facts") or {}),
    )
    missing_param_probe = probe_missing_parameters(
        topic=str(topic),
        outline=[str(x) for x in (outline or []) if str(x).strip()],
        requirements=[str(x) for x in (requirements or []) if str(x).strip()] + tender_globals,
        tender=tender if isinstance(tender, dict) else {},
        boq=boq if isinstance(boq, dict) else {},
        enterprise_profile=enterprise_profile if isinstance(enterprise_profile, dict) else {},
    )
    schedule_constraints: List[str] = []
    ledger_facts = (
        project_fact_ledger.get("facts")
        if isinstance(project_fact_ledger.get("facts"), dict)
        else {}
    )
    if ledger_facts:
        def _fact_value(field: str):
            row = ledger_facts.get(field)
            return row.get("value") if isinstance(row, dict) else None

        est_days = _fact_value("planned_duration_days")
        peak = _fact_value("resource_peak")
        cp_gap = _fact_value("critical_interval_days")
        raw_cp_names = _fact_value("critical_path_names")
        cp_names = [
            str(x).strip()
            for x in (raw_cp_names if isinstance(raw_cp_names, list) else [])
            if str(x).strip()
        ]
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
    base_requirements.extend(project_fact_prompt_requirements(project_fact_ledger))
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
    compliance_domains = _dedup_lines(
        [project_type]
        + [
            str(x).strip()
            for x in (multi_agent_plan.dispatch.get("involved_domains") or [])
            if str(x).strip()
        ],
        limit=40,
    )
    compliance_registry_status = get_compliance_registry_status()
    verified_project_standards = list_verified_standard_metadata(
        domain_tags=compliance_domains or None,
    )
    verified_standard_codes = [
        str(row.get("standard_code") or "").strip()
        for row in verified_project_standards
        if isinstance(row, dict) and str(row.get("standard_code") or "").strip()
    ]
    _emit_progress("chapters_ready", chapters_total=len(outline))
    _emit_progress(
        "compliance_preflight",
        ready=bool(compliance_registry_status.get("ready")),
        verified_standard_count=len(verified_standard_codes),
        project_domains=compliance_domains,
    )
    if strict_quality and (
        not bool(compliance_registry_status.get("ready"))
        or not verified_standard_codes
    ):
        warnings = "、".join(
            str(x) for x in (compliance_registry_status.get("warnings") or []) if str(x)
        )
        raise ValueError(
            "项目适用规范生成前预检未通过，未调用大模型："
            + (warnings or "当前项目没有可由官方来源复核的现行规范元数据")
        )
    agent_contract = build_agent_contract(
        topic=str(topic),
        outline=outline if isinstance(outline, list) else [],
        chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
        chapter_requirements=chapter_requirements if isinstance(chapter_requirements, dict) else {},
        multi_agent_summary=multi_agent_plan.summary(),
        chapter_specialties=multi_agent_plan.chapter_specialties,
        project_fact_ledger=project_fact_ledger,
    )
    chapter_contract_map = {
        str(ch.get("title") or "").strip(): ch
        for ch in (agent_contract.get("chapters") or [])
        if isinstance(ch, dict) and str(ch.get("title") or "").strip()
    }
    requirement_evidence_hard_gate = bool(
        payload.get("requirement_evidence_hard_gate", bool(tender))
    )
    requirement_plan_agent_contract = agent_contract
    if (
        delivery_scope == "chapter_validation"
        and tender_outline
        and tender_outline != outline
    ):
        # Determine requirement ownership against the complete tender outline
        # first.  Otherwise a score item belonging to an omitted chapter can
        # fall back onto the first selected validation chapter.
        requirement_plan_agent_contract = build_agent_contract(
            topic=str(topic),
            outline=tender_outline,
            chapter_pages=(
                tender_chapter_pages
                if isinstance(tender_chapter_pages, dict)
                else {}
            ),
            chapter_requirements=(
                chapter_requirements
                if isinstance(chapter_requirements, dict)
                else {}
            ),
            multi_agent_summary=multi_agent_plan.summary(),
            chapter_specialties=multi_agent_plan.chapter_specialties,
            project_fact_ledger=project_fact_ledger,
        )
    requirement_evidence_plan = build_requirement_evidence_plan(
        tender=tender if isinstance(tender, dict) else {},
        chapter_requirements=chapter_requirements if isinstance(chapter_requirements, dict) else {},
        global_requirements=tender_globals,
        agent_contract=requirement_plan_agent_contract,
    )
    if delivery_scope == "chapter_validation":
        requirement_evidence_plan = scope_requirement_evidence_plan_to_chapters(
            requirement_evidence_plan,
            outline,
        )
    requirement_evidence_plan_validation = validate_requirement_evidence_matrix(
        requirement_evidence_plan
    )
    if not requirement_evidence_plan_validation.get("ok"):
        raise ValueError(
            "招标要求—证据计划完整性校验失败，未调用章节Agent："
            + "、".join(requirement_evidence_plan_validation.get("errors") or [])
        )
    requirement_evidence_plan_readiness = validate_requirement_evidence_plan_readiness(
        requirement_evidence_plan
    )
    _emit_progress(
        "requirement_evidence_preflight",
        ok=bool(requirement_evidence_plan_readiness.get("ok")),
        blocking_requirement_ids=requirement_evidence_plan_readiness.get(
            "blocking_requirement_ids"
        )
        or [],
        warning_requirement_ids=requirement_evidence_plan_readiness.get(
            "warning_requirement_ids"
        )
        or [],
    )
    if (
        not requirement_evidence_plan_readiness.get("ok")
        and (
            mandatory_provider_admission
            or bool(payload.get("_provider_admission_required", False))
            or (strict_quality and requirement_evidence_hard_gate)
        )
    ):
        raise ValueError(
            "招标要求—证据生成前准入失败，未调用模型；阻断要求："
            + "、".join(
                requirement_evidence_plan_readiness.get("blocking_requirement_ids")
                or ["UNKNOWN"]
            )
        )

    provider_admission_public: Dict[str, Any] = {
        "schema_version": "provider-admission-v1",
        "status": "not_required",
        "generation_allowed": True,
        "degraded": False,
        "slots": [],
        "admitted_chain": [],
        "missing_roles": [],
    }
    provider_admission_digest: str | None = None
    provider_admission_binding_digest: str | None = None
    provider_admission_required = bool(
        not dry_run
        and (
            mandatory_provider_admission
            or bool(payload.get("_provider_admission_required", False))
        )
    )
    if provider_admission_required:
        _raise_if_cancelled("provider_admission_started")
        candidates = _provider_admission_candidates(payload, provider_chain)
        required_roles = [
            str(role or "").strip().lower()
            for role in (payload.get("_provider_admission_required_roles") or ["text_draft"])
            if str(role or "").strip()
        ]
        coordinator = payload.get("_provider_admission_run_coordinator")
        if not isinstance(coordinator, ProviderAdmissionRunCoordinator):
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "MODEL_PROVIDER_ADMISSION_CONTEXT_MISSING",
                        "message": "生成任务缺少运行级供应商准入上下文，已安全停止。",
                        "action": "请从系统生成入口重新发起任务。",
                    },
                    ensure_ascii=False,
                )
            )
        emit_admission_events = coordinator.claim_event_emitter()
        if emit_admission_events:
            _emit_progress(
                "provider_admission_started",
                candidate_count=len(candidates),
                required_roles=required_roles,
            )

        async def _probe_provider_candidate(candidate: ProviderCandidate) -> Dict[str, Any]:
            return await probe_provider_candidate(
                candidate,
                reliability_runtime=model_reliability,
                execution_runtime=execution_runtime,
            )

        try:
            internal_snapshot = await coordinator.admit_chain_once(
                candidates=candidates,
                probe=_probe_provider_candidate,
                required_roles=required_roles,
            )
        except GenerationCancelledError:
            raise
        except Exception as exc:
            if emit_admission_events:
                _emit_progress(
                    "provider_admission_failed",
                    code="MODEL_PROVIDER_ADMISSION_UNAVAILABLE",
                    error_type=type(exc).__name__,
                )
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "MODEL_PROVIDER_ADMISSION_UNAVAILABLE",
                        "message": "模型供应商准入检查未能形成可信回执，已阻止生成。",
                        "action": "请检查本机模型配置和准入状态后重试。",
                    },
                    ensure_ascii=False,
                )
            ) from exc
        provider_admission_digest = str(
            internal_snapshot.get("admission_digest") or ""
        ).strip() or None
        provider_admission_binding_digest = provider_admission_canonical_digest(
            {
                "schema_version": "provider-admission-binding-v1",
                "required_roles": list(internal_snapshot.get("required_roles") or []),
                "admitted_route_identities": [
                    {
                        "slot": item.get("slot"),
                        "role": item.get("role"),
                        "provider": item.get("provider"),
                        "model": item.get("model"),
                        "identity_digest": item.get("identity_digest"),
                    }
                    for item in (internal_snapshot.get("admitted_chain") or [])
                    if isinstance(item, dict)
                ],
            }
        )
        provider_admission_public = public_provider_admission_snapshot(
            internal_snapshot
        )
        if emit_admission_events:
            _emit_progress(
                "provider_admission_completed",
                status=provider_admission_public.get("status"),
                generation_allowed=bool(
                    provider_admission_public.get("generation_allowed")
                ),
                degraded=bool(provider_admission_public.get("degraded")),
                admitted_chain=provider_admission_public.get("admitted_chain") or [],
                missing_roles=provider_admission_public.get("missing_roles") or [],
                public_digest=provider_admission_public.get("public_digest"),
            )
        if not bool(provider_admission_public.get("generation_allowed")):
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "MODEL_PROVIDER_ADMISSION_BLOCKED",
                        "message": "模型供应商未通过生成前准入，已在调用章节模型前停止。",
                        "action": "请按准入详情修复凭据、模型、配额、流式能力或文档渲染槽位。",
                        "admission": provider_admission_public,
                    },
                    ensure_ascii=False,
                )
            )

        admitted_by_identity = {
            str(item.get("identity_digest") or ""): item
            for item in (internal_snapshot.get("admitted_chain") or [])
            if isinstance(item, dict) and str(item.get("identity_digest") or "")
        }
        admitted_text_chain: List[Dict[str, Any]] = []
        text_slots = {str(item.get("slot") or "") for item in provider_chain}
        for candidate in coordinator.bound_candidates:
            if candidate.slot not in text_slots:
                continue
            admitted = admitted_by_identity.get(candidate.identity_digest)
            if admitted:
                admitted_text_chain.append(
                    {
                        **dict(admitted),
                        # Ephemeral only. Generation bindings, checkpoints,
                        # progress events and final output project an allowlist
                        # that never serializes this credential.
                        "api_key": candidate.credential,
                    }
                )
        provider_chain = admitted_text_chain
        if provider_chain:
            provider = provider_chain[0].get("provider") or provider
            model = provider_chain[0].get("model") or model
        tiered_anthropic_route = _has_tiered_anthropic_route(provider_chain)

    # Optional logo lookup may perform DNS/HTTP. It is deliberately deferred
    # until both the evidence gate and mandatory provider admission have passed.
    try:
        from backend.zhifei_autoplan.logo_runtime import (
            prepare_logo_for_embedding,
            resolve_logo,
        )

        if (
            payload.get("bidder_company")
            or payload.get("logo_url")
            or payload.get("bidder_domain")
            or project_id
        ):
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

    def _chapter_evidence_gate(section: Dict[str, Any], title: str | None = None) -> Dict[str, Any]:
        chapter_title = str(title or section.get("title") or "").strip()
        return validate_chapter_requirement_evidence(
            plan=requirement_evidence_plan,
            title=chapter_title,
            section=section,
        )

    def _assign_evidence_safe_content(
        section: Dict[str, Any],
        content: Any,
        *,
        stage: str,
    ) -> bool:
        candidate = dict(section)
        candidate["content"] = str(content or "")
        gate = _chapter_evidence_gate(candidate)
        if strict_quality and requirement_evidence_hard_gate and not gate.get("ok"):
            section.setdefault("evidence_guard_rejections", []).append(
                {
                    "stage": stage,
                    "blocking_requirement_ids": gate.get("blocking_requirement_ids") or [],
                }
            )
            _emit_progress(
                "chapter_evidence_regression_rejected",
                chapter_title=str(section.get("title") or ""),
                stage=stage,
                blocking_requirement_ids=gate.get("blocking_requirement_ids") or [],
            )
            return False
        section["content"] = candidate["content"]
        section["requirement_evidence_gate"] = gate
        return True

    checkpoint_namespace = str(
        payload.get("_checkpoint_namespace") or payload.get("_job_id") or ""
    ).strip()
    resume_checkpoint_namespace = str(
        payload.get("_resume_checkpoint_namespace")
        or payload.get("resume_from_job_id")
        or ""
    ).strip()
    checkpoint_scope = f"variant-{variant_index}"
    checkpoint_enabled = bool(checkpoint_namespace) and not dry_run and not no_write_preview
    generation_binding = build_generation_binding(
        topic=topic,
        project_id=project_id,
        project_type=project_type,
        outline=outline,
        style=style,
        chapter_pages=chapter_pages,
        variant_id=variant_index,
        project_fact_digest=project_fact_ledger.get("ledger_digest"),
        requirement_plan_digest=requirement_evidence_plan.get("matrix_digest"),
        provider_routes=provider_chain,
        delivery_scope=delivery_scope,
        provider_admission_digest=provider_admission_binding_digest,
        prompt_contract={
            "prompt_layout_version": "section-envelope-v3",
            "requirements": base_requirements,
            "global_instruction": global_instruction,
            "chapter_requirements": chapter_requirements,
            "logic_templates": {
                "general": logic_template_general.as_dict() if logic_template_general else None,
                "qse": logic_template_qse.as_dict() if logic_template_qse else None,
            },
            "effective_params": params,
            "tender": tender,
            "boq_focus": boq_focus,
            "case_library": case_library_options,
            "image_library": image_library_options,
            "chapter_summaries": payload.get("chapter_summaries") or [],
            "project_stage_context": str(payload.get("project_stage_context") or ""),
            "common_construction_requirements": payload.get(
                "common_construction_requirements"
            )
            or [],
        },
    )
    generation_checkpoint: Dict[str, Any] = {
        "schema_version": "generation-checkpoint-v3",
        "binding_digest": generation_binding.get("binding_digest"),
        "status": "disabled" if not checkpoint_enabled else "ready",
        "saved_chapter_count": 0,
        "saved_chapter_indexes": [],
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

    def _role_attempts(role: str) -> List[tuple[str | None, str | None, str | None, str | None]]:
        entries = _provider_chain_for_role(
            provider_chain,
            role,
            allow_fable_escalation=allow_fable_escalation,
        )
        return [
            (
                str(entry.get("provider") or "").strip().lower() or None,
                str(entry.get("model") or "").strip() or None,
                str(entry.get("api_key") or "").strip() or None,
                str(entry.get("slot") or "").strip() or None,
            )
            for entry in entries
        ]

    if (
        bool(payload.get("model_preflight", False))
        and not dry_run
        and not provider_admission_required
    ):
        _raise_if_cancelled("model_preflight_started")
        _emit_progress("model_preflight_started")
        unique_candidates: Dict[tuple[str, str], tuple[str, str, str | None, str | None]] = {}
        for role in ("draft", "review"):
            for p, m, key_override, slot_id in _role_attempts(role):
                if not p or not m:
                    continue
                unique_candidates.setdefault((p, m), (p, m, key_override, slot_id))
        if not unique_candidates and provider and model:
            unique_candidates[(str(provider), str(model))] = (
                str(provider),
                str(model),
                None,
                None,
            )
        for p, m, key_override, slot_id in unique_candidates.values():
            _raise_if_cancelled("model_preflight_candidate")
            client = LLMClient(
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
                reliability_runtime=model_reliability,
                retry_attempts=2,
                execution_runtime=execution_runtime,
            )
            try:
                receipt = await client.preflight(timeout=30.0)
            finally:
                client.close()
            receipt["slot"] = slot_id
            model_preflight_receipts.append(receipt)
        draft_keys = {
            (str(p), str(m))
            for p, m, _key_override, _slot_id in _role_attempts("draft")
            if p and m
        }
        if not draft_keys and provider and model:
            draft_keys = {(str(provider), str(model))}
        healthy_draft = any(
            bool(row.get("ok"))
            and (str(row.get("provider")), str(row.get("model"))) in draft_keys
            for row in model_preflight_receipts
        )
        _emit_progress(
            "model_preflight_completed",
            candidates=len(model_preflight_receipts),
            healthy=sum(1 for row in model_preflight_receipts if row.get("ok")),
        )
        if bool(payload.get("fail_on_model_exhaustion", False)) and draft_keys and not healthy_draft:
            safe_failures = [
                {
                    "slot": row.get("slot"),
                    "provider": row.get("provider"),
                    "model": row.get("model"),
                    "code": (row.get("error_info") or {}).get("code") or row.get("error"),
                    "message": sanitize_provider_message(
                        (row.get("error_info") or {}).get("message") or row.get("error")
                    ),
                }
                for row in model_preflight_receipts
            ]
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "MODEL_PREFLIGHT_EXHAUSTED",
                        "message": "所有正文模型候选均未通过生成前验证，已停止任务。",
                        "failures": safe_failures,
                    },
                    ensure_ascii=False,
                )
            )

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

    section_sem = asyncio.Semaphore(agent_parallelism)
    rolling_chapter_summaries: list[dict[str, str]] = [
        dict(item)
        for item in (payload.get("chapter_summaries") or [])
        if isinstance(item, dict) and str(item.get("summary") or "").strip()
    ][-30:]

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

    async def build_section(idx: int, title: str, checkpoint_resolver=None):
        # 章节级重试：多模型轮询重试，最多尝试 3 个 provider（主+备1+备2）
        tries = []
        if tiered_anthropic_route:
            tries.extend(_role_attempts("draft"))
        elif provider_chain:
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
        section_case_reference_pack = _build_case_pack_for_section(title)
        section_image_selection_pack = _build_image_pack_for_section(title)
        kg_hits = search_kg(f"{topic} {title} 施工组织 质量 安全 工期", top_k=4)
        doc_hits = (
            search_ingested_docs(
                f"{topic} {title} 招标 清单 图纸 质量 安全 工期",
                limit=6,
                project_id=project_id,
            )
            if str(project_id or "").strip()
            else []
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
        chapter_requirement_evidence_rows = requirement_rows_for_chapter(
            requirement_evidence_plan,
            title,
        )
        section_requirements.extend(
            requirement_prompt_lines_for_chapter(requirement_evidence_plan, title)
        )
        section_requirements.extend(
            case_reference_prompt_requirements(section_case_reference_pack)
        )
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
            if style.get("enforce_chapter_pages"):
                section_requirements.append(
                    "页数不足时只能通过本项目相关的施工工序、适用参数、资源配置、接口协调、"
                    "风险→控制→验证闭环以及检验验收证据深化正文；禁止空白页、重复段落、"
                    "无关内容和未经证据支持的事实、规范或参数。"
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
        section_compliance_domains = [str(x).strip() for x in (graph_ctx.get("agents", {}).get("domain_tags") or []) if str(x).strip()]
        if not section_compliance_domains:
            section_compliance_domains = list(compliance_domains)
        clause_hits = query_compliance(
            f"{topic} {title} 质量 安全 工期 验收 允许偏差 抽检 频次",
            domain_tags=section_compliance_domains or None,
            top_k=4,
            prefer_latest=True,
            verified_only=True,
        )
        compliance_hits: List[Dict[str, Any]] = []
        seen_compliance_rows: set[tuple[str, str]] = set()
        for raw_hit in [*verified_project_standards, *clause_hits]:
            if not isinstance(raw_hit, dict):
                continue
            key = (
                canonical_standard_code(raw_hit.get("standard_code")),
                str(raw_hit.get("locator") or "metadata").strip(),
            )
            if not key[0] or key in seen_compliance_rows:
                continue
            seen_compliance_rows.add(key)
            compliance_hits.append(dict(raw_hit))
        section_requirements.append(standard_citation_directive(verified_project_standards))
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
        kg_evidence_filter = filter_evidence_to_verified_standard_codes(
            kg_evidence,
            verified_standard_codes,
        )
        doc_evidence_filter = filter_evidence_to_verified_standard_codes(
            doc_evidence,
            verified_standard_codes,
        )
        kg_evidence = list(kg_evidence_filter.get("lines") or [])
        doc_evidence = list(doc_evidence_filter.get("lines") or [])

        ctx = {
            "project_id": project_id,
            "requirements": section_requirements,
            "common_requirements": list(base_requirements),
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
            "auxiliary_agents": graph_ctx.get("agents", {}).get("auxiliary") or [],
            "compliance_agent": graph_ctx.get("agents", {}).get("compliance") or multi_agent_plan.compliance_agent,
            "specialty_tags": graph_ctx.get("agents", {}).get("specialty_tags") or [],
            "graph_nodes": graph_ctx.get("node_bindings") or [],
            "graph_experience_values": exp_values,
            "chapter_contract": chapter_contract or {},
            "enterprise_profile": enterprise_profile,
            "missing_param_probe": missing_param_probe,
            "boq_wbs_cpm_summary": cpm_summary if isinstance(cpm_summary, dict) else {},
            "project_fact_ledger_digest": project_fact_ledger.get("ledger_digest"),
            "project_fact_snapshot": agent_contract.get("project_fact_ledger") or {},
            "word_format_rules": style if isinstance(style, dict) else {},
            "graphics_rules": chart_policy if isinstance(chart_policy, dict) else {},
            # The list is updated only between bounded chapter waves. Every
            # chapter in one wave therefore sees an identical medium-lived
            # prefix, while the next wave receives compact summaries instead
            # of full historical chapter bodies.
            "chapter_summaries": [dict(item) for item in rolling_chapter_summaries],
            "project_stage_context": str(payload.get("project_stage_context") or "")[:12000],
            "common_construction_requirements": payload.get("common_construction_requirements")
            if isinstance(payload.get("common_construction_requirements"), list)
            else [],
            "requirement_evidence_plan_digest": requirement_evidence_plan.get("matrix_digest"),
            "requirement_evidence_rows": chapter_requirement_evidence_rows,
            "boq_wbs_top_process": (boq_wbs_cpm.get("wbs") or [])[:8] if isinstance(boq_wbs_cpm, dict) else [],
            "labor_hint": labor_hint if isinstance(labor_hint, dict) else {},
            "compliance_hits": compliance_hits if isinstance(compliance_hits, list) else [],
            "verified_standard_codes": list(verified_standard_codes),
            "standard_citation_policy": standard_citation_directive(verified_project_standards),
            "case_reference_pack": section_case_reference_pack,
            "image_selection_pack": section_image_selection_pack,
            "model_request_timeout_seconds": max(
                30,
                min(240, int(payload.get("model_request_timeout_seconds") or 240)),
            ),
            "max_chapter_output_tokens": max(
                256,
                min(16384, int(payload.get("max_chapter_output_tokens") or 8192)),
            ),
            "dropped_unverified_standard_evidence": int(kg_evidence_filter.get("dropped_count") or 0)
            + int(doc_evidence_filter.get("dropped_count") or 0),
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

        chapter_context_digest = build_chapter_context_digest(
            chapter_index=idx,
            chapter_title=title,
            delivery_scope=delivery_scope,
            writer_context=ctx,
        )
        if checkpoint_resolver is not None:
            resumed = checkpoint_resolver(chapter_context_digest)
            if isinstance(resumed, dict):
                return {
                    **dict(resumed),
                    "_checkpoint_resumed": True,
                    "_chapter_context_digest": chapter_context_digest,
                }

        def _attach_context_identity(rec: Dict[str, Any] | None) -> Dict[str, Any] | None:
            if isinstance(rec, dict):
                rec["_chapter_context_digest"] = chapter_context_digest
            return rec

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
            rec.setdefault("auxiliary_agents", [dict(x) for x in (ctx.get("auxiliary_agents") or []) if isinstance(x, dict)])
            rec.setdefault("compliance_agent", ctx.get("compliance_agent"))
            rec.setdefault("specialty_tags", list(ctx.get("specialty_tags") or []))
            rec.setdefault("graph_nodes", list(ctx.get("graph_nodes") or []))
            rec.setdefault("compliance_hits", [dict(x) for x in (ctx.get("compliance_hits") or []) if isinstance(x, dict)])
            rec.setdefault("case_reference_pack", section_case_reference_pack)
            rec.setdefault("image_selection_pack", section_image_selection_pack)
            rec.setdefault(
                "assigned_requirement_ids",
                [
                    str(row.get("requirement_id") or "").strip()
                    for row in chapter_requirement_evidence_rows
                    if isinstance(row, dict) and str(row.get("requirement_id") or "").strip()
                ],
            )
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
                        reliability_runtime=model_reliability,
                        retry_attempts=1,
                        execution_runtime=execution_runtime,
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
            _emit_provider_progress(
                "provider_attempt_started",
                chapter_index=int(idx) + 1,
                chapter_title=str(title or ""),
                chapters_total=len(outline),
                provider=str(p or ""),
                model=str(m or ""),
                slot=str(slot_id or ""),
                request_timeout_seconds=240,
            )
            writer = SectionWriter(llm=llm)
            try:
                last = _attach_section_meta(await writer.write(title, ctx))
                if isinstance(last, dict):
                    last.setdefault("model_slot", slot_id)
                    last.setdefault("model_role", _model_role_for_slot(slot_id))
            except ExecutionCancelledError:
                raise
            except Exception as e:
                budget_exhausted = isinstance(e, ExecutionBudgetExceededError)
                error_info = classify_provider_error(
                    e.as_dict() if budget_exhausted else e,
                    provider=str(p or ""),
                    model=str(m or ""),
                )
                error_code = str(error_info.get("code") or "provider_error")
                last = _attach_section_meta(
                    {
                        "title": title,
                        "content": "",
                        "provider": p,
                        "model": m,
                        "model_slot": slot_id,
                        "model_role": _model_role_for_slot(slot_id),
                        "error": error_code,
                        "error_info": error_info,
                        "code": error_code,
                        "failure_kind": (
                            "execution_control" if budget_exhausted else "provider"
                        ),
                    }
                )
                _emit_provider_progress(
                    "provider_attempt_finished",
                    chapter_index=int(idx) + 1,
                    chapter_title=str(title or ""),
                    chapters_total=len(outline),
                    provider=str(p or ""),
                    model=str(m or ""),
                    slot=str(slot_id or ""),
                    ok=False,
                    error_type=type(e).__name__,
                    error_code=error_code,
                    circuits=model_reliability.snapshot(),
                )
                if budget_exhausted:
                    break
                continue
            finally:
                if llm is not None:
                    llm.close()
            if last and not last.get("error"):
                evidence_gate = _chapter_evidence_gate(last, title)
                last["requirement_evidence_gate"] = evidence_gate
                if (
                    strict_quality
                    and requirement_evidence_hard_gate
                    and not evidence_gate.get("ok")
                ):
                    blocking_ids = evidence_gate.get("blocking_requirement_ids") or []
                    last["error"] = (
                        "requirement_evidence_precheckpoint_blocked:"
                        + ",".join(str(value) for value in blocking_ids[:20])
                    )
                    last["failure_kind"] = "quality_gate"
                    last["code"] = "requirement_evidence_failed"
                    last["blocking_requirement_ids"] = [
                        str(value)[:160]
                        for value in blocking_ids[:20]
                        if str(value).strip()
                    ]
                    _emit_progress(
                        "chapter_evidence_gate_failed",
                        chapter_index=int(idx) + 1,
                        chapter_title=str(title or ""),
                        chapters_total=len(outline),
                        provider=str(p or ""),
                        model=str(m or ""),
                        slot=str(slot_id or ""),
                        blocking_requirement_ids=blocking_ids,
                    )
                else:
                    _emit_progress(
                        "chapter_evidence_gate_passed",
                        chapter_index=int(idx) + 1,
                        chapter_title=str(title or ""),
                        chapters_total=len(outline),
                        provider=str(p or ""),
                        model=str(m or ""),
                        slot=str(slot_id or ""),
                        warning_requirement_ids=evidence_gate.get(
                            "warning_requirement_ids"
                        )
                        or [],
                    )
            if last and not last.get("error"):
                _emit_provider_progress(
                    "provider_attempt_finished",
                    chapter_index=int(idx) + 1,
                    chapter_title=str(title or ""),
                    chapters_total=len(outline),
                    provider=str(p or ""),
                    model=str(m or ""),
                    slot=str(slot_id or ""),
                    ok=True,
                    circuits=model_reliability.snapshot(),
                )
                return _attach_context_identity(last)
            _emit_provider_progress(
                "provider_attempt_finished",
                chapter_index=int(idx) + 1,
                chapter_title=str(title or ""),
                chapters_total=len(outline),
                provider=str(p or ""),
                model=str(m or ""),
                slot=str(slot_id or ""),
                ok=False,
                error=str((last or {}).get("error") or "no_visible_text"),
                circuits=model_reliability.snapshot(),
            )
        if last:
            return _attach_context_identity(last)
        return _attach_context_identity(
            _attach_section_meta({"title": title, "content": "章节生成失败"})
            or {"title": title, "content": "章节生成失败"}
        )

    async def _build_section_with_limit(idx: int, title: str):
        nonlocal generation_checkpoint
        async with section_sem:
            _raise_if_cancelled("before_chapter")
            _emit_progress(
                "chapter_started",
                chapter_index=int(idx) + 1,
                chapter_title=str(title or ""),
                chapters_total=len(outline),
            )

            def _resolve_checkpoint(
                chapter_context_digest: str,
            ) -> Dict[str, Any] | None:
                nonlocal generation_checkpoint
                if not checkpoint_enabled:
                    return None
                resumed = load_section_checkpoint(
                    namespace=resume_checkpoint_namespace or checkpoint_namespace,
                    scope=checkpoint_scope,
                    binding=generation_binding,
                    chapter_index=idx,
                    chapter_title=str(title or ""),
                    chapter_context_digest=chapter_context_digest,
                )
                if resumed is None:
                    return None
                resumed_gate = _chapter_evidence_gate(resumed, title)
                resumed["requirement_evidence_gate"] = resumed_gate
                if (
                    strict_quality
                    and requirement_evidence_hard_gate
                    and not resumed_gate.get("ok")
                ):
                    _emit_progress(
                        "chapter_checkpoint_rejected",
                        chapter_index=int(idx) + 1,
                        chapter_title=str(title or ""),
                        chapters_total=len(outline),
                        reason="requirement_evidence_invalid",
                        blocking_requirement_ids=resumed_gate.get(
                            "blocking_requirement_ids"
                        )
                        or [],
                    )
                    return None
                if (
                    resume_checkpoint_namespace
                    and resume_checkpoint_namespace != checkpoint_namespace
                ):
                    generation_checkpoint = _write_checkpoint(
                        save_section_checkpoint,
                        namespace=checkpoint_namespace,
                        scope=checkpoint_scope,
                        binding=generation_binding,
                        chapter_index=idx,
                        chapter_title=str(title or ""),
                        chapter_context_digest=chapter_context_digest,
                        result=resumed,
                    )
                _emit_progress(
                    "chapter_resumed",
                    chapter_index=int(idx) + 1,
                    chapter_title=str(title or ""),
                    chapters_total=len(outline),
                )
                return resumed
            target_pages = _extract_chapter_page_target(chapter_pages, title)
            chapter_contract = (
                chapter_contract_map.get(str(title).strip())
                if isinstance(chapter_contract_map, dict)
                else None
            )
            if target_pages is None and isinstance(chapter_contract, dict):
                target_pages = _to_int_or_none(chapter_contract.get("page_target"))
            chapter_deadline = _chapter_deadline_seconds(
                payload,
                target_pages=target_pages,
            )
            try:
                result = await asyncio.wait_for(
                    build_section(
                        idx,
                        title,
                        checkpoint_resolver=_resolve_checkpoint,
                    ),
                    timeout=float(chapter_deadline),
                )
            except asyncio.TimeoutError:
                result = {
                    "title": str(title or ""),
                    "content": "",
                    "provider": "",
                    "model": "",
                    "error": "chapter_deadline_exceeded",
                    "failure_kind": "provider",
                    "code": "timeout",
                }
            chapter_context_digest = ""
            resumed_from_checkpoint = False
            if isinstance(result, dict):
                chapter_context_digest = str(
                    result.pop("_chapter_context_digest", "") or ""
                ).strip()
                resumed_from_checkpoint = bool(
                    result.pop("_checkpoint_resumed", False)
                )
            if resumed_from_checkpoint:
                _emit_progress(
                    "chapter_completed",
                    chapter_index=int(idx) + 1,
                    chapter_title=str(title or ""),
                    chapters_total=len(outline),
                    ok=True,
                    resumed=True,
                )
                return result
            if (
                checkpoint_enabled
                and isinstance(result, dict)
                and not result.get("error")
                and str(result.get("content") or "").strip()
            ):
                if not chapter_context_digest:
                    raise RuntimeError("chapter_context_digest_missing")
                generation_checkpoint = _write_checkpoint(
                    save_section_checkpoint,
                    namespace=checkpoint_namespace,
                    scope=checkpoint_scope,
                    binding=generation_binding,
                    chapter_index=idx,
                    chapter_title=str(title or ""),
                    chapter_context_digest=chapter_context_digest,
                    result=result,
                )
                _emit_progress(
                    "chapter_checkpoint_saved",
                    chapter_index=int(idx) + 1,
                    chapter_title=str(title or ""),
                    saved_chapter_count=generation_checkpoint.get("saved_chapter_count"),
                )
            _emit_progress(
                "chapter_completed",
                chapter_index=int(idx) + 1,
                chapter_title=str(title or ""),
                chapters_total=len(outline),
                ok=not bool(result.get("error")) if isinstance(result, dict) else False,
            )
            _raise_if_cancelled("after_chapter")
            return result

    async def _gather_with_cancellation(coroutines: List[Any]) -> List[Any]:
        """Gather tasks in input order while polling the durable cancel flag."""

        tasks = [asyncio.create_task(coro) for coro in coroutines]
        pending = set(tasks)
        try:
            while pending:
                _done, pending = await asyncio.wait(
                    pending,
                    timeout=0.5,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                _raise_if_cancelled("chapter_batch")
                # Surface the first completed exception promptly instead of
                # waiting for every sibling chapter.
                for task in _done:
                    if task.cancelled():
                        raise GenerationCancelledError("cancelled_by_user:chapter_task")
                    error = task.exception()
                    if error is not None:
                        raise error
            return [task.result() for task in tasks]
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    async def _complete_with_role(prompt: str, role: str) -> tuple[str, Dict[str, Any]]:
        failures: List[Dict[str, str]] = []
        if dry_run:
            return "", {"ok": False, "reason": "dry_run", "failures": failures}
        for p, m, key_override, slot_id in _role_attempts(role)[:5]:
            if not p or not m:
                continue
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
                    reliability_runtime=model_reliability,
                    retry_attempts=1,
                    execution_runtime=execution_runtime,
                )
                try:
                    response = await llm.complete(
                        prompt,
                        timeout=240.0,
                        project_id=project_id,
                        task_type=f"{str(role or 'generic').strip().lower()}_agent_task",
                    )
                finally:
                    llm.close()
                text = str(response.get("text") or "").strip() if isinstance(response, dict) else ""
                if text:
                    return text, {
                        "ok": True,
                        "slot": slot_id,
                        "role": _model_role_for_slot(slot_id),
                        "provider": p,
                        "model": m,
                        "failures": failures,
                    }
                error_info = response.get("error_info") if isinstance(response, dict) else None
                failures.append(
                    {
                        "slot": str(slot_id or ""),
                        "provider": p,
                        "model": m,
                        "error": str((error_info or {}).get("code") or response.get("error") or "no_visible_text"),
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "slot": str(slot_id or ""),
                        "provider": p,
                        "model": m,
                        "error": type(exc).__name__,
                    }
                )
        return "", {"ok": False, "reason": "all_role_candidates_failed", "failures": failures}

    sections: list[dict[str, Any]] = []
    for batch_start in range(0, len(outline), agent_parallelism):
        batch_outline = outline[batch_start : batch_start + agent_parallelism]
        batch_sections = await _gather_with_cancellation(
            [
                _build_section_with_limit(batch_start + offset, title)
                for offset, title in enumerate(batch_outline)
            ]
        )
        sections.extend(batch_sections)
        for section in batch_sections:
            if not isinstance(section, dict):
                continue
            title = str(section.get("title") or "章节").strip()
            summary = str(section.get("chapter_summary") or "").strip()
            if not summary:
                summary = compact_chapter_summary(title, section.get("content"))
                section["chapter_summary"] = summary
            if summary:
                rolling_chapter_summaries.append(
                    {"title": title, "summary": summary[:800]}
                )
        rolling_chapter_summaries[:] = rolling_chapter_summaries[-30:]
    failed_sections = []
    for sec in sections:
        if not isinstance(sec, dict) or not sec.get("error"):
            continue
        raw_error = sanitize_provider_message(sec.get("error"))
        error_info = sec.get("error_info") if isinstance(sec.get("error_info"), dict) else {}
        failure_kind = str(sec.get("failure_kind") or "").strip()
        failure_code = str(sec.get("code") or error_info.get("code") or "").strip()
        if raw_error.startswith("requirement_evidence_precheckpoint_blocked"):
            failure_kind = "quality_gate"
            failure_code = "requirement_evidence_failed"
        if not failure_kind:
            failure_kind = "provider"
        blocking_ids = [
            str(value)[:160]
            for value in (sec.get("blocking_requirement_ids") or [])[:20]
            if str(value).strip()
        ]
        failed_sections.append(
            {
                "title": str(sec.get("title") or ""),
                "provider": str(sec.get("provider") or ""),
                "model": str(sec.get("model") or ""),
                "failure_kind": failure_kind,
                "code": failure_code or "provider_error",
                "error": raw_error,
                **(
                    {"blocking_requirement_ids": blocking_ids}
                    if blocking_ids
                    else {}
                ),
            }
        )
    succeeded_sections = [
        sec
        for sec in sections
        if isinstance(sec, dict)
        and not sec.get("error")
        and str(sec.get("content") or "").strip()
    ]
    if failed_sections:
        checkpoint_terminal_status = (
            "failed_partial" if succeeded_sections else "failed_empty"
        )
        progress_event = "draft_failed"
    else:
        checkpoint_terminal_status = "draft_complete"
        progress_event = "draft_complete"
    if checkpoint_enabled:
        generation_checkpoint = _write_checkpoint(
            finalize_generation_checkpoint,
            namespace=checkpoint_namespace,
            scope=checkpoint_scope,
            binding=generation_binding,
            status=checkpoint_terminal_status,
        )
    _emit_progress(
        progress_event,
        chapters_total=len(outline),
        chapters_done=len(succeeded_sections),
        chapters_succeeded=len(succeeded_sections),
        chapters_failed=len(failed_sections),
        saved_chapter_count=generation_checkpoint.get("saved_chapter_count"),
        checkpoint_status=checkpoint_terminal_status,
    )
    if bool(payload.get("fail_on_model_exhaustion", False)) and failed_sections and not dry_run:
        evidence_failures = [
            row
            for row in failed_sections
            if str(row.get("error") or "").startswith(
                "requirement_evidence_precheckpoint_blocked"
            )
        ]
        if evidence_failures:
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "REQUIREMENT_EVIDENCE_CHAPTER_BLOCKED",
                        "message": "章节要求证据未通过成功检查点前校验；不合格章节未保存为成功。",
                        # Keep provider/timeout failures from the same wave.  A
                        # local quality-gate failure must not erase independent
                        # model-chain evidence needed for a truthful retry.
                        "failures": failed_sections,
                    },
                    ensure_ascii=False,
                )
            )
        execution_budget_failures = [
            row
            for row in failed_sections
            if str(row.get("code") or "") == "EXECUTION_BUDGET_EXCEEDED"
        ]
        if execution_budget_failures:
            raise RuntimeError(
                json.dumps(
                    {
                        "code": "EXECUTION_BUDGET_EXCEEDED",
                        "message": "本次任务的模型调用安全预算已用尽，正文生成已停止。",
                        "failures": failed_sections,
                    },
                    ensure_ascii=False,
                )
            )
        raise RuntimeError(
            json.dumps(
                {
                    "code": "MODEL_CHAIN_EXHAUSTED",
                    "message": "至少一个章节未获得真实模型正文，已停止任务，未将模板回退稿作为成功产物。",
                    "failures": failed_sections,
                },
                ensure_ascii=False,
            )
        )
    for sec in sections:
        _assign_evidence_safe_content(
            sec,
            strip_nonconcrete_language(sec.get("content") or ""),
            stage="strip_nonconcrete_language_after_draft",
        )

    page_target_enrichment: Dict[str, Any] = {
        "enabled": bool(style.get("enforce_chapter_pages")),
        "policy": "technical_content_only_no_page_padding",
        "candidates": [],
        "enhanced": [],
        "skipped": [],
    }
    if page_target_enrichment["enabled"] and not dry_run:
        enrichment_sem = asyncio.Semaphore(2)

        async def _enrich_short_section(sec: Dict[str, Any]) -> Dict[str, Any]:
            title = str(sec.get("title") or "章节").strip()
            content = str(sec.get("content") or "").strip()
            target_pages = _extract_chapter_page_target(chapter_pages, title)
            if not target_pages:
                return {"title": title, "ok": False, "reason": "no_page_target"}
            target_chars = max(200, target_pages * chars_per_page_hint)
            minimum_effective_chars = max(160, int(target_chars * 0.8))
            current_effective_chars = len("".join(content.split()))
            if sec.get("error") or not content:
                return {
                    "title": title,
                    "ok": False,
                    "reason": "draft_unavailable",
                    "current_effective_chars": current_effective_chars,
                    "minimum_effective_chars": minimum_effective_chars,
                }
            if current_effective_chars >= minimum_effective_chars:
                return {
                    "title": title,
                    "ok": False,
                    "reason": "content_sufficient",
                    "current_effective_chars": current_effective_chars,
                    "minimum_effective_chars": minimum_effective_chars,
                }

            prompt = (
                "你是施工组织设计技术深化专家。当前章节的有效技术内容低于规划下限，请在不改变"
                "招标目录层级的前提下，输出深化后的完整章节正文。\n"
                "只允许补充与本项目和本章直接相关的施工工序、工艺衔接、资源配置、接口协调、"
                "风险→控制→验证闭环、检查频次、验收方法及可追溯证据。保留原文中的有效内容及"
                "【证据:...】、【经验值:...】标记。\n"
                "严禁用空白页、分页符、重复段落、同义改写、套话或无关内容增加篇幅；严禁虚构"
                "规范编号、项目事实、参数、工期、数量或验收结论。资料未提供的参数必须明确标为"
                "待核验，不得自行猜测。质量优先于页数，不足以安全扩写时保持原文。\n"
                f"章节标题：{title}\n"
                f"规划目标：{target_pages}页，建议正文约{target_chars}字，最低有效内容约"
                f"{minimum_effective_chars}字；当前有效内容约{current_effective_chars}字。\n\n"
                f"原文：\n{content}\n\n只输出深化后的完整章节正文："
            )
            async with enrichment_sem:
                enriched, audit = await _complete_with_role(prompt, "draft")
            enriched = strip_nonconcrete_language(enriched or "")
            enriched_effective_chars = len("".join(enriched.split()))
            minimum_gain = max(100, int(current_effective_chars * 0.05))
            if not enriched or enriched_effective_chars < current_effective_chars + minimum_gain:
                return {
                    "title": title,
                    "ok": False,
                    "reason": "no_material_quality_gain",
                    "current_effective_chars": current_effective_chars,
                    "candidate_effective_chars": enriched_effective_chars,
                    "minimum_effective_chars": minimum_effective_chars,
                    "model_audit": audit,
                }
            if not _assign_evidence_safe_content(
                sec,
                enriched,
                stage="page_target_enrichment",
            ):
                return {
                    "title": title,
                    "ok": False,
                    "reason": "requirement_evidence_regression",
                    "blocking_requirement_ids": (
                        _chapter_evidence_gate({**sec, "content": enriched}, title).get(
                            "blocking_requirement_ids"
                        )
                        or []
                    ),
                    "model_audit": audit,
                }
            sec.setdefault("pre_page_target_enrichment_content", content)
            sec["page_target_enriched"] = True
            sec["page_target_enrichment_model_slot"] = audit.get("slot")
            return {
                "title": title,
                "ok": True,
                "current_effective_chars": current_effective_chars,
                "enhanced_effective_chars": enriched_effective_chars,
                "minimum_effective_chars": minimum_effective_chars,
                "model_slot": audit.get("slot"),
            }

        page_target_enrichment["candidates"] = _dedup_lines(
            [
                str(sec.get("title") or "").strip()
                for sec in sections
                if isinstance(sec, dict)
                and _extract_chapter_page_target(chapter_pages, str(sec.get("title") or "").strip())
                and len("".join(str(sec.get("content") or "").split()))
                < max(
                    160,
                    int(
                        max(
                            200,
                            int(_extract_chapter_page_target(chapter_pages, str(sec.get("title") or "").strip()) or 0)
                            * chars_per_page_hint,
                        )
                        * 0.8
                    ),
                )
            ]
        )
        if page_target_enrichment["candidates"]:
            _emit_progress(
                "page_target_enrichment_started",
                chapter_count=len(page_target_enrichment["candidates"]),
            )
        enrichment_results = await asyncio.gather(
            *[_enrich_short_section(sec) for sec in sections if isinstance(sec, dict)]
        )
        page_target_enrichment["enhanced"] = [
            row for row in enrichment_results if row.get("ok")
        ]
        page_target_enrichment["skipped"] = [
            row for row in enrichment_results if not row.get("ok")
        ]
        if page_target_enrichment["candidates"]:
            _emit_progress(
                "page_target_enrichment_complete",
                candidate_count=len(page_target_enrichment["candidates"]),
                enhanced_count=len(page_target_enrichment["enhanced"]),
            )

    model_review_audit: Dict[str, Any] = {
        "enabled": bool(tiered_anthropic_route),
        "fable_escalation_enabled": bool(allow_fable_escalation),
        "critical_chapters": [],
        "reviewed_chapters": [],
        "failed_chapters": [],
        "consistency_review": {"ok": False, "reason": "tiered_route_not_enabled"},
    }
    if tiered_anthropic_route and not dry_run:
        critical_sections = [
            sec
            for sec in sections
            if isinstance(sec, dict) and _is_critical_review_chapter(sec.get("title"))
        ]
        model_review_audit["critical_chapters"] = [
            str(sec.get("title") or "").strip() for sec in critical_sections
        ]
        review_sem = asyncio.Semaphore(2)

        async def _review_critical_section(sec: Dict[str, Any]) -> Dict[str, Any]:
            title = str(sec.get("title") or "章节").strip()
            content = str(sec.get("content") or "").strip()
            if not content or sec.get("error"):
                return {"title": title, "ok": False, "reason": "draft_unavailable"}
            prompt = (
                "你是施工组织设计的高级总审专家。请复核并精修以下关键章节。\n"
                "硬性约束：不得改变招标文件目录层级；不得新增未经证据支持的事实、规范编号或参数；"
                "保留全部【证据:...】与【经验值:...】标记；统一工期、资源、关键线路及验收口径；"
                "删除套话，强化风险→控制→验证闭环和可执行量化指标。\n"
                "只输出精修后的完整章节正文，不输出说明。\n\n"
                f"章节标题：{title}\n\n原文：\n{content}"
            )
            async with review_sem:
                reviewed, audit = await _complete_with_role(prompt, "review")
            if reviewed:
                reviewed = strip_nonconcrete_language(reviewed)
                if not _assign_evidence_safe_content(
                    sec,
                    reviewed,
                    stage="tiered_model_review",
                ):
                    return {
                        "title": title,
                        "ok": False,
                        "reason": "requirement_evidence_regression",
                        "blocking_requirement_ids": (
                            _chapter_evidence_gate(
                                {**sec, "content": reviewed}, title
                            ).get("blocking_requirement_ids")
                            or []
                        ),
                        **audit,
                    }
                sec.setdefault("pre_review_content", content)
                sec["review_model_slot"] = audit.get("slot")
                sec["review_model_role"] = audit.get("role")
                sec["review_provider"] = audit.get("provider")
                sec["review_model"] = audit.get("model")
                return {"title": title, **audit}
            return {"title": title, **audit}

        review_results = await asyncio.gather(
            *[_review_critical_section(sec) for sec in critical_sections]
        )
        model_review_audit["reviewed_chapters"] = [
            row for row in review_results if bool(row.get("ok"))
        ]
        model_review_audit["failed_chapters"] = [
            row for row in review_results if not bool(row.get("ok"))
        ]

        consistency_material = []
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get("title") or "").strip()
            content = str(sec.get("content") or "").strip()
            consistency_material.append(f"## {title}\n{content[:900]}")
        consistency_prompt = (
            "你是施工组织设计终审专家。仅基于以下章节摘要做全文一致性复核，重点检查工期、"
            "资源峰值、关键线路、质量验收、安全责任和规范引用是否前后冲突。不得补造事实。"
            "请输出简短的终审问题清单；无冲突时明确写“未发现实质性冲突”。\n\n"
            + "\n\n".join(consistency_material)
        )[:24000]
        consistency_text, consistency_audit = await _complete_with_role(consistency_prompt, "review")
        if consistency_text:
            consistency_audit["summary"] = consistency_text[:4000]
        model_review_audit["consistency_review"] = consistency_audit

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
        {
            "stage": "compliance_preflight",
            "ok": bool(compliance_registry_status.get("ready")) and bool(verified_standard_codes),
            "verified_standard_count": len(verified_standard_codes),
            "project_domains": list(compliance_domains),
            "warnings": list(compliance_registry_status.get("warnings") or []),
        },
        {"stage": "draft_generation", "ok": True, "chapter_count": len(sections)},
        {
            "stage": "requirement_evidence_plan",
            "ok": bool(requirement_evidence_plan_validation.get("ok"))
            and bool(requirement_evidence_plan_readiness.get("ok")),
            "matrix_digest": requirement_evidence_plan.get("matrix_digest"),
            "requirement_count": (requirement_evidence_plan.get("summary") or {}).get("requirement_count"),
            "mandatory_count": (requirement_evidence_plan.get("summary") or {}).get("mandatory_count"),
            "source_bound_count": (requirement_evidence_plan.get("summary") or {}).get("source_bound_count"),
            "unmapped_count": (requirement_evidence_plan.get("summary") or {}).get("unmapped_count"),
            "blocking_requirement_ids": requirement_evidence_plan_readiness.get(
                "blocking_requirement_ids"
            )
            or [],
            "warning_requirement_ids": requirement_evidence_plan_readiness.get(
                "warning_requirement_ids"
            )
            or [],
        },
        {
            "stage": "page_target_enrichment",
            "ok": True,
            "enabled": bool(page_target_enrichment.get("enabled")),
            "candidate_count": len(page_target_enrichment.get("candidates") or []),
            "enhanced_count": len(page_target_enrichment.get("enhanced") or []),
            "mechanical_padding_applied": False,
        },
        {
            "stage": "reference_library_enrichment",
            "ok": True,
            "case_library_enabled": bool(case_reference_pack.get("enabled")),
            "case_hit_count": len(case_reference_pack.get("selected_case_ids") or []),
            "case_prompt_injection": bool(case_reference_pack.get("selected_case_ids")),
            "image_library_enabled": bool(image_selection_pack.get("enabled")),
            "image_hit_count": len(image_selection_pack.get("selected_image_ids") or []),
        },
        {
            "stage": "tiered_model_review",
            "ok": not bool(model_review_audit.get("failed_chapters")),
            "enabled": bool(model_review_audit.get("enabled")),
            "critical_chapter_count": len(model_review_audit.get("critical_chapters") or []),
            "reviewed_chapter_count": len(model_review_audit.get("reviewed_chapters") or []),
            "fable_escalation_enabled": bool(allow_fable_escalation),
        },
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
        project_source_media = generate_ingested_previews(limit=6, project_id=project_id)
        media.extend(project_source_media)
        # Mindmap (server-side image chain; OpenAI primary, Gemini fallback when configured).
        try:
            img_defaults = get_image_defaults(params)
            aspect_ratio = (payload.get("image_aspect_ratio") or img_defaults.get("aspect_ratio") or "16:9").strip()

            mm = None
            include_outline_mindmap = bool(payload.get("include_outline_mindmap")) or not project_source_media
            if include_outline_mindmap:
                # External image generation is fail-closed until an
                # image-specific admission probe has bound an in-memory slot
                # to this run.  Text-model admission must never be treated as
                # permission to call a separate image model/API.
                admitted_image_slots = payload.get(
                    "_provider_admitted_image_slots"
                )
                if not isinstance(admitted_image_slots, list):
                    admitted_image_slots = []
                for image_slot in admitted_image_slots:
                    mm = generate_outline_mindmap(
                        topic,
                        outline,
                        provider=image_slot.provider,
                        api_key=image_slot.api_key,
                        model=image_slot.model,
                        aspect_ratio=aspect_ratio,
                        logo_path=logo_embed,
                        bidder_company=payload.get("bidder_company"),
                        logo_url=payload.get("logo_url"),
                        bidder_domain=payload.get("bidder_domain"),
                        fallback_to_deterministic=False,
                    )
                    if mm:
                        break
                if not mm:
                    mm = generate_outline_mindmap(
                        topic,
                        outline,
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
                "ok": bool(
                    ((quality_draft.get("quality_gate") or {}).get("pass", True))
                    if isinstance(quality_draft, dict)
                    else True
                ),
                "score": quality_draft.get("score") if isinstance(quality_draft, dict) else None,
                "threshold": (
                    (quality_draft.get("independent_content_review") or {}).get("threshold")
                    if isinstance(quality_draft, dict)
                    else None
                ),
            }
        )
        remediate_mode = payload.get("remediate_mode") or "template"
        pre_remediation_content = {
            id(sec): str(sec.get("content") or "")
            for sec in sections
            if isinstance(sec, dict)
        }

        async def _remediate_with_llm(sec: Dict[str, Any], recs: List[Dict[str, Any]]):
            if not recs:
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
            revised, audit = await _complete_with_role(prompt, "review")
            if revised:
                if _assign_evidence_safe_content(
                    sec,
                    strip_nonconcrete_language(revised),
                    stage="quality_llm_remediation",
                ):
                    sec["auto_remediated"] = "llm"
                    sec["remediation_model_slot"] = audit.get("slot")
                    sec["remediation_provider"] = audit.get("provider")
                    sec["remediation_model"] = audit.get("model")

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
            candidate_content = strip_nonconcrete_language(sec.get("content") or "")
            original_content = pre_remediation_content.get(id(sec), "")
            sec["content"] = original_content
            _assign_evidence_safe_content(
                sec,
                candidate_content,
                stage=f"quality_{remediate_mode}_remediation",
            )

        mandatory_supplements = ensure_local_export_mandatory_content(sections)
        pipeline_stages.append(
            {
                "stage": "local_export_mandatory_content",
                "ok": True,
                "added": mandatory_supplements,
            }
        )

    # Plan consistency: normalize duplicated metrics (工期/资源峰值/关键线路间隔) to a single canonical value.
    plan_receipt = None
    try:
        from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections

        pre_plan_consistency_content = {
            id(sec): str(sec.get("content") or "")
            for sec in sections
            if isinstance(sec, dict)
        }
        plan_receipt = normalize_metrics_in_sections(sections)
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            candidate_content = str(sec.get("content") or "")
            sec["content"] = pre_plan_consistency_content.get(id(sec), "")
            _assign_evidence_safe_content(
                sec,
                candidate_content,
                stage="plan_consistency",
            )
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
        terminology_attempts = _role_attempts("review") or _role_attempts("draft")
        terminology_provider = ""
        terminology_model = ""
        terminology_key = None
        if terminology_attempts:
            (
                terminology_provider,
                terminology_model,
                terminology_key,
                _terminology_slot,
            ) = terminology_attempts[0]
        pre_terminology_content = {
            id(sec): str(sec.get("content") or "")
            for sec in sections
            if isinstance(sec, dict)
        }
        terminology_audit = await normalize_sections_terminology_async(
            sections,
            provider=str(terminology_provider or ""),
            model=str(terminology_model or ""),
            api_key=terminology_key,
            use_llm=bool(terminology_key) and not dry_run,
        )
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            candidate_content = str(sec.get("content") or "")
            sec["content"] = pre_terminology_content.get(id(sec), "")
            _assign_evidence_safe_content(
                sec,
                candidate_content,
                stage="terminology_audit",
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
            _assign_evidence_safe_content(
                sec,
                strip_nonconcrete_language(sec.get("content") or ""),
                stage="strip_nonconcrete_language_final",
            )
    except Exception:
        pass
    standard_citation_sanitization: List[Dict[str, Any]] = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        sanitized = replace_unverified_standard_citations(
            sec.get("content"),
            verified_standard_codes,
        )
        if not bool(sanitized.get("changed")):
            continue
        if not _assign_evidence_safe_content(
            sec,
            str(sanitized.get("text") or ""),
            stage="standard_citation_sanitization",
        ):
            continue
        sec["removed_unverified_standard_codes"] = list(sanitized.get("removed_codes") or [])
        standard_citation_sanitization.append(
            {
                "chapter": str(sec.get("title") or "").strip(),
                "removed_codes": list(sanitized.get("removed_codes") or []),
            }
        )
    pipeline_stages.append(
        {
            "stage": "standard_citation_sanitization",
            "ok": True,
            "changed_chapter_count": len(standard_citation_sanitization),
            "removed_code_count": sum(
                len(row.get("removed_codes") or []) for row in standard_citation_sanitization
            ),
        }
    )
    project_standard_registry_section = {
        "title": "项目适用规范清单",
        "content": "",
        "compliance_hits": [dict(row) for row in verified_project_standards],
    }
    project_applicable_standards = build_project_applicable_standards_manifest(
        [project_standard_registry_section, *sections]
    )
    standard_citation_audit = audit_standard_citations(sections, project_applicable_standards)
    pipeline_stages.append(
        {
            "stage": "project_applicable_standards",
            "ok": bool(standard_citation_audit.get("ok", False)),
            "verified_standard_count": project_applicable_standards.get("verified_count", 0),
            "unverified_standard_count": project_applicable_standards.get("unverified_count", 0),
            "citation_violation_count": standard_citation_audit.get("violation_count", 0),
        }
    )
    if strict_quality and not bool(standard_citation_audit.get("ok", False)):
        sample = (standard_citation_audit.get("violations") or [])[:5]
        details = "；".join(
            f"{str(row.get('chapter') or '未命名章节')}:{str(row.get('standard_code') or '未知规范')}"
            for row in sample
            if isinstance(row, dict)
        )
        raise ValueError(f"项目适用规范核验未通过，已停止生成：{details or '存在未核验规范或未解决冲突'}")
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
            "ok": bool((quality.get("quality_gate") or {}).get("pass", True))
            and bool(contract_checks.get("ok", True)),
            "score": quality.get("score"),
            "threshold": (quality.get("independent_content_review") or {}).get("threshold"),
            "blocking_issue_count": (quality.get("quality_gate") or {}).get("blocking_issue_count", 0),
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
        if not no_write_preview:
            param_receipt_path = save_latest_receipt(param_receipt, project_id=str(project_id) if project_id else None)
    except Exception:
        param_receipt = None
        param_receipt_path = None

    # Cross-index: BoQ focus item -> chapter -> drawing/standard locator -> closure flags.
    cross_index = None
    expected_focus_count = len(
        normalize_boq_focus_items(
            (boq_focus or {}).get("must_cover_keywords") or [],
            limit=MAX_BOQ_FOCUS_ITEMS,
        )
    )
    try:
        from backend.zhifei_autoplan.cross_index import (
            build_cross_index,
            validate_cross_index_contract,
        )

        cross_index = build_cross_index(
            boq=boq,
            sections=sections,
            boq_focus=boq_focus,
            drawing_index=drawing_index,
            standard_index=standard_index,
            quality_checks=quality,
            project_id=str(project_id) if project_id else None,
        )
        cross_index = validate_cross_index_contract(
            cross_index,
            expected_names=(boq_focus or {}).get("must_cover_keywords") or [],
        )
    except Exception:
        cross_index = {
            "ok": expected_focus_count == 0,
            "build_failed": expected_focus_count > 0,
            "reason": (
                "cross_index_build_failed"
                if expected_focus_count > 0
                else "no_boq_focus_items"
            ),
            "focus_count": expected_focus_count,
            "mentioned_count": 0,
            "closed_ok_count": 0,
            "missing_drawing_locator_count": 0,
            "missing_standard_locator_count": 0,
            "focus_items": [],
        }
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
    requirement_evidence_matrix = finalize_requirement_evidence_matrix(
        plan=requirement_evidence_plan,
        sections=sections,
        evidence_tracking=evidence_tracking,
        document_control_evidence={
            "page_plan": {
                "planned_total_pages": sum(
                    max(0, int(value or 0))
                    for value in chapter_pages.values()
                )
                if isinstance(chapter_pages, dict)
                else 0,
                "limit": int(total_pages_limit or 0),
                "verified": bool(chapter_pages) and bool(total_pages_limit),
            },
            "format_policy": {
                "source": str(style_source or ""),
                "verified": bool(style)
                and not bool(requirement_decision_matrix.get("unresolved_fields")),
            },
        },
    )
    requirement_evidence_validation = validate_requirement_evidence_matrix(
        requirement_evidence_matrix
    )
    requirement_evidence_summary = requirement_evidence_matrix.get("summary") or {}
    pipeline_stages.append(
        {
            "stage": "requirement_evidence_matrix",
            "ok": bool(requirement_evidence_validation.get("ok"))
            and bool(requirement_evidence_summary.get("strict_delivery_allowed", False)),
            "matrix_digest": requirement_evidence_matrix.get("matrix_digest"),
            "covered_count": requirement_evidence_summary.get("covered_count"),
            "traceable_count": requirement_evidence_summary.get("traceable_count"),
            "blocking_count": requirement_evidence_summary.get("blocking_count"),
            "warning_count": requirement_evidence_summary.get("warning_count"),
        }
    )
    if strict_quality and requirement_evidence_hard_gate:
        if not requirement_evidence_validation.get("ok"):
            raise ValueError(
                "招标要求—证据矩阵完整性校验失败："
                + "、".join(requirement_evidence_validation.get("errors") or [])
            )
        blocking_ids = requirement_evidence_summary.get("blocking_requirement_ids") or []
        if blocking_ids:
            raise ValueError(
                "招标要求—证据交付硬门未通过，已停止交付；缺失或不可反查要求："
                + "、".join(str(value) for value in blocking_ids[:20])
            )
    delivery_quality_gate = build_delivery_quality_gate(
        strict=strict_quality,
        content_review=(
            quality.get("independent_content_review")
            if isinstance(quality.get("independent_content_review"), dict)
            else {}
        ),
        plan_consistency=plan_receipt if isinstance(plan_receipt, dict) else {},
        model_review_audit=model_review_audit,
        requirement_matrix=requirement_evidence_matrix,
        standard_audit=standard_citation_audit,
        cross_index=cross_index if isinstance(cross_index, dict) else {},
        model_review_required=bool(tiered_anthropic_route and not dry_run),
    )
    quality["delivery_quality_gate"] = delivery_quality_gate
    pipeline_stages.append(
        {
            "stage": "delivery_quality_gate",
            "ok": bool(delivery_quality_gate.get("delivery_allowed")),
            "decision_digest": delivery_quality_gate.get("decision_digest"),
            "blocker_count": delivery_quality_gate.get("blocker_count"),
            "warning_count": delivery_quality_gate.get("warning_count"),
        }
    )
    if (
        strict_quality
        and delivery_scope == "document"
        and not bool(delivery_quality_gate.get("delivery_allowed"))
    ):
        blocker_codes = [
            str(row.get("code") or "DELIVERY_QUALITY_BLOCKED")
            for row in (delivery_quality_gate.get("blockers") or [])
            if isinstance(row, dict)
        ]
        raise ValueError(
            "最终专业交付质量门未通过，已停止交付："
            + "、".join(blocker_codes[:20])
        )
    chapter_validation_gate = None
    if delivery_scope == "chapter_validation":
        chapter_validation_gate = _build_chapter_validation_quality_gate(
            quality=quality,
            contract_checks=contract_checks,
            delivery_quality_gate=delivery_quality_gate,
        )
        quality["chapter_validation_gate"] = chapter_validation_gate
        pipeline_stages.append(
            {
                "stage": "chapter_validation_quality_gate",
                "ok": bool(chapter_validation_gate.get("pass")),
                "blocker_codes": chapter_validation_gate.get("blocker_codes") or [],
            }
        )
        if strict_quality and not bool(chapter_validation_gate.get("pass")):
            raise ValueError(
                "CHAPTER_VALIDATION_QUALITY_BLOCKED："
                "章节真实模型验证质量门未通过："
                + "、".join(chapter_validation_gate.get("blocker_codes") or [])
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
    agent_execution_ledger = build_agent_execution_ledger(
        plan_summary=multi_agent_plan.summary(),
        content_review=(
            quality.get("independent_content_review")
            if isinstance(quality.get("independent_content_review"), dict)
            else {}
        ),
        contract_checks=contract_checks,
        standard_audit=standard_citation_audit,
        media_quality=(quality.get("media_quality") if isinstance(quality.get("media_quality"), dict) else {}),
        fact_ledger=project_fact_ledger,
        requirement_matrix=requirement_evidence_matrix,
        cross_index=(cross_index if isinstance(cross_index, dict) else {}),
    )
    pipeline_stages.append(
        {
            "stage": "multi_agent_quality_review",
            "ok": int(agent_execution_ledger.get("blocked_count") or 0) == 0,
            "role_count": agent_execution_ledger.get("role_count"),
            "completed_count": agent_execution_ledger.get("completed_count"),
            "needs_attention_count": agent_execution_ledger.get("needs_attention_count"),
            "blocked_count": agent_execution_ledger.get("blocked_count"),
            "not_executed_count": agent_execution_ledger.get("not_executed_count"),
        }
    )
    _raise_if_cancelled("before_result_delivery")
    if checkpoint_enabled and checkpoint_terminal_status == "draft_complete":
        generation_checkpoint = _write_checkpoint(
            finalize_generation_checkpoint,
            namespace=checkpoint_namespace,
            scope=checkpoint_scope,
            binding=generation_binding,
            status="complete",
        )
    return {
        "topic": topic,
        "generation_mode": payload.get("generation_mode"),
        "mode_policy": payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else None,
        "project_type": project_type,
        "global_instruction": global_instruction,
        "outline": outline,
        "sections": sections,
        "chapter_summaries": rolling_chapter_summaries,
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
        "page_target_enrichment": page_target_enrichment,
        "total_pages_target": user_total_pages_target,
        "total_pages_limit": total_pages_limit,
        "style": style,
        "style_source": style_source,
        "requirement_decision_matrix": requirement_decision_matrix,
        "quality_strict": strict_quality,
        "delivery_scope": delivery_scope,
        "delivery_ready": bool(
            delivery_scope == "document"
            and not dry_run
            and delivery_quality_gate.get("delivery_allowed")
        ),
        "compliance_registry_status": compliance_registry_status,
        "standard_citation_sanitization": standard_citation_sanitization,
        "boq_focus": boq_focus,
        "boq_wbs_cpm": boq_wbs_cpm,
        "project_fact_ledger": project_fact_ledger,
        "project_fact_validation": project_fact_validation,
        "missing_parameters": missing_param_probe,
        "enterprise_profile": enterprise_profile,
        "agent_contract": agent_contract,
        "agent_contract_checks": contract_checks,
        "requirement_evidence_plan": requirement_evidence_plan,
        "requirement_evidence_plan_validation": requirement_evidence_plan_validation,
        "requirement_evidence_plan_readiness": requirement_evidence_plan_readiness,
        "requirement_evidence_matrix": requirement_evidence_matrix,
        "requirement_evidence_validation": requirement_evidence_validation,
        "generation_checkpoint": generation_checkpoint,
        "score_mapping": score_mapping,
        "compare": {
            "mode": payload.get("compare_mode", "full"),
            "max_chars": int(payload.get("compare_max_chars") or 800),
            "titles": payload.get("compare_titles"),
        },
        "quality_checks": quality,
        "delivery_quality_gate": delivery_quality_gate,
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
        "project_applicable_standards": project_applicable_standards,
        "standard_citation_audit": standard_citation_audit,
        "cross_index": cross_index,
        "evidence_tracking": evidence_tracking,
        "plan_consistency": plan_receipt,
        "execution_control": execution_runtime.snapshot(),
        "model_routing": {
            "mode": "anthropic_tiered" if tiered_anthropic_route else "legacy_failover",
            "provider_admission": provider_admission_public,
            "draft": [
                {
                    "slot": item.get("slot"),
                    "provider": item.get("provider"),
                    "model": item.get("model"),
                }
                for item in _provider_chain_for_role(
                    provider_chain,
                    "draft",
                    allow_fable_escalation=allow_fable_escalation,
                )
            ],
            "review": [
                {
                    "slot": item.get("slot"),
                    "provider": item.get("provider"),
                    "model": item.get("model"),
                }
                for item in _provider_chain_for_role(
                    provider_chain,
                    "review",
                    allow_fable_escalation=allow_fable_escalation,
                )
            ],
            "fable_escalation_enabled": bool(allow_fable_escalation),
            "review_audit": model_review_audit,
            "reliability": {
                "preflight_enabled": bool(payload.get("model_preflight", False))
                and not provider_admission_required,
                "preflight": model_preflight_receipts,
                "circuits": model_reliability.snapshot(),
            },
        },
        "multi_agent": {
            **multi_agent_plan.summary(),
            "execution": {
                "parallel": True,
                "specialist_role_count": len(multi_agent_plan.summary().get("agent_role_catalog") or []),
                "agent_parallelism": agent_parallelism,
                "parallelism_semantics": "bounded_chapter_tasks_not_agent_count",
                "chapter_count": len(outline),
            },
            "compliance": multi_agent_compliance,
            "execution_ledger": agent_execution_ledger,
        },
        "terminology_audit": terminology_audit,
        "pipeline_stages": pipeline_stages,
        "params_used": params_used,
    }
