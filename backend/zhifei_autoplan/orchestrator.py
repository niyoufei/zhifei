from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, Any, List

from backend.zhifei_autoplan.tender_store import load_tender_matrix, load_bidding_format_config
from backend.zhifei_autoplan.boq_store import load_boq_data
from backend.zhifei_autoplan.kg_runtime import search_kg
from backend.zhifei_autoplan.evidence import (
    search_ingested_docs,
    format_hit_locator,
    best_ingested_hit,
    search_tender_source_spans,
    best_tender_source_span_hit,
)
from backend.zhifei_autoplan.utils.llm_client import LLMClient
from backend.zhifei_autoplan.agents.section_writer import SectionWriter, compact_text_to_length_bounds
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
from backend.zhifei_autoplan.compliance_runtime import query_compliance
from backend.zhifei_autoplan.async_cache import AsyncThreadCache
from backend.zhifei_autoplan.terminology_guard import (
    load_labor_allocation_matrix,
    normalize_sections_terminology_async,
    suggest_labor_ratio_for_chapter,
)
from backend.zhifei_autoplan.qingtian_policy import (
    QINGTIAN_GLOBAL_REQUIREMENTS,
    apply_qingtian_outline_policy,
    build_qingtian_chapter_requirements,
    compose_qingtian_global_instruction,
)
from backend.zhifei_autoplan.template_library import (
    build_template_chapter_learning_context,
    infer_template_page_bucket,
    infer_template_scene_tags,
)
from backend.zhifei_autoplan.self_evolution import (
    build_runtime_budget_hints,
    load_runtime_budget_profile,
    prioritize_remediation_rows_with_learning,
)
from backend.zhifei_autoplan.model_aliases import normalize_provider_model_pair
from backend.zhifei_autoplan.provider_runtime import (
    iterate_image_failover_slots,
    resolve_automation_credentials,
    resolve_text_slot_credentials,
)
from backend.zhifei_autoplan.remediation_strategy import ACTION_TAG_LABELS, QUALITY_GATE_METRIC_LABELS, enrich_strategy_rows
from backend.zhifei_autoplan.resource_audit import (
    append_resource_events,
    build_llm_usage_events,
    summarize_sections,
)
from backend.zhifei_autoplan.workspace import (
    maybe_cleanup_expired_workspaces,
    resolve_workspace_dir,
    workspace_paths,
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

SECTION_CACHE_DIR = Path("backend/data/autoplan/cache/sections")
SECTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
TRACEABLE_EVIDENCE_RE = re.compile(r"#(?:p\d+_)?[0-9a-f]{6,16}@\d+", re.IGNORECASE)


def _section_cache_dir(workspace_dir: str | None = None) -> Path:
    return workspace_paths(workspace_dir)["section_cache"] if workspace_dir else SECTION_CACHE_DIR


def _trace_runtime(payload: Dict[str, Any], event: str, **fields: Any) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    job_id = str(payload.get("_job_id") or payload.get("job_id") or "").strip()
    trace_id = str(payload.get("trace_id") or payload.get("request_id") or "").strip()
    prefix = f"[{stamp}][autoplan]"
    if job_id:
        prefix += f"[job:{job_id}]"
    if trace_id:
        prefix += f"[trace:{trace_id}]"
    parts = [str(event or "").strip()]
    for key, value in fields.items():
        text = str(value or "").strip()
        if not text:
            continue
        parts.append(f"{key}={text}")
    print(f"{prefix} {' '.join(parts)}".strip(), flush=True)


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


def _build_section_checklist(
    tender: Dict[str, Any],
    title: str,
    *,
    limit: int = 24,
) -> List[str]:
    items = tender.get("items") if isinstance(tender, dict) else []
    if not isinstance(items, list) or not items:
        return []
    chapter = str(title or "").strip()
    scored: List[tuple[int, str]] = []
    for it in items[:300]:
        if not isinstance(it, dict):
            continue
        dim = str(it.get("dimension") or "").strip()
        kws = [str(x).strip() for x in (it.get("keywords") or []) if str(x).strip()]
        if not dim and not kws:
            continue
        weight = _to_int_or_none(it.get("weight")) or 0
        hit = 0
        if dim and dim in chapter:
            hit += 3
        for kw in kws[:8]:
            if kw and kw in chapter:
                hit += 2
        score = hit * 10 + max(0, weight)
        line = f"{dim or '评分点'}: {';'.join(kws[:6])}" if kws else f"{dim}:（无关键词）"
        scored.append((score, line))

    # 先保留高相关，再补高权重项，避免每章重复注入全量评分点导致 prompt 过长。
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[str] = []
    seen: set[str] = set()
    for _, line in scored:
        if not line or line in seen:
            continue
        seen.add(line)
        out.append(line)
        if len(out) >= max(1, int(limit or 24)):
            break
    return out


def _resolve_runtime_speed_profile(
    *,
    mode_effective: str,
    total_pages_limit: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    # 质量闸门不动，仅压缩“生成路径”的输入和长尾重试。
    defaults = {
        "speed_fast": {
            "kg_top_k": 2,
            "doc_limit": 3,
            "standard_limit": 1,
            "section_retry_limit": 1,
            "llm_timeout_sec": 60,
            "chars_per_page_factor": 0.58,
        },
        "quality_200": {
            "kg_top_k": 3,
            "doc_limit": 5,
            "standard_limit": 2,
            "section_retry_limit": 2,
            "llm_timeout_sec": 120,
            "chars_per_page_factor": 0.82,
        },
        "hq_speed_500": {
            "kg_top_k": 2,
            "doc_limit": 4,
            "standard_limit": 2,
            "section_retry_limit": 1,
            "llm_timeout_sec": 80,
            "chars_per_page_factor": 0.68,
        },
        "pro_polish": {
            "kg_top_k": 4,
            "doc_limit": 6,
            "standard_limit": 3,
            "section_retry_limit": 3,
            "llm_timeout_sec": 150,
            "chars_per_page_factor": 0.90,
        },
    }
    mode = str(mode_effective or "quality_200").strip() or "quality_200"
    profile = dict(defaults.get(mode, defaults["quality_200"]))
    # 大篇幅自动更激进，但保留最低质量兜底。
    if int(total_pages_limit or 0) > 200:
        profile["section_retry_limit"] = min(int(profile["section_retry_limit"]), 1)
        profile["chars_per_page_factor"] = min(float(profile["chars_per_page_factor"]), 0.70)
    custom = payload.get("speed_profile") if isinstance(payload.get("speed_profile"), dict) else {}
    for k in ("kg_top_k", "doc_limit", "standard_limit", "section_retry_limit", "llm_timeout_sec"):
        if k in custom:
            v = _to_int_or_none(custom.get(k))
            if v:
                profile[k] = int(v)
    if "chars_per_page_factor" in custom:
        try:
            f = float(custom.get("chars_per_page_factor"))
            if 0.4 <= f <= 1.2:
                profile["chars_per_page_factor"] = f
        except Exception:
            pass
    profile["kg_top_k"] = max(1, min(6, int(profile["kg_top_k"])))
    profile["doc_limit"] = max(2, min(10, int(profile["doc_limit"])))
    profile["standard_limit"] = max(1, min(6, int(profile["standard_limit"])))
    profile["section_retry_limit"] = max(1, min(3, int(profile["section_retry_limit"])))
    profile["llm_timeout_sec"] = max(40, min(240, int(profile["llm_timeout_sec"])))
    return profile


def _compress_section_requirements(
    lines: List[str],
    limit: int = 26,
    preserve: List[str] | None = None,
) -> List[str]:
    """
    Keep prompt grounding dense and deterministic.
    Priority order:
    1) hard constraints / style / page-length limits
    2) safety-quality-compliance / evidence / risk-triplet
    3) chapter-specific quantitative requirements
    4) remaining context, deduped and capped
    """
    if not isinstance(lines, list):
        return []
    hard_markers = (
        "系统全局指令",
        "项目类型",
        "本章目标页数",
        "本章字数边界",
        "章内结构",
        "合同要求",
        "风险",
        "控制",
        "验证",
        "闭环",
        "证据",
        "规范强条",
        "规范参数建议",
        "经验值",
        "劳动力配比",
        "特殊材料",
        "危险品材料",
        "劳保用品",
        "四新技术",
        "图谱",
        "QINGTIAN",
    )
    soft_markers = (
        "检查",
        "频次",
        "阈值",
        "工期",
        "质量",
        "安全",
        "文明",
        "绿色工地",
        "信息化",
        "机械",
        "材料",
        "清单重点",
        "计划口径统一",
    )
    seen: set[str] = set()
    buckets: list[list[str]] = [[], [], []]
    for raw in lines:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        if any(marker in text for marker in hard_markers):
            buckets[0].append(text)
        elif any(marker in text for marker in soft_markers) or any(ch.isdigit() for ch in text):
            buckets[1].append(text)
        else:
            buckets[2].append(text)
    preserve_order = [str(x or "").strip() for x in (preserve or []) if str(x or "").strip()]
    out: List[str] = []
    out_seen: set[str] = set()
    for text in preserve_order:
        if text in seen and text not in out_seen:
            out.append(text)
            out_seen.add(text)
            if len(out) >= max(1, int(limit or 0)):
                return out
    for group in buckets:
        for text in group:
            if text in out_seen:
                continue
            out.append(text)
            out_seen.add(text)
            if len(out) >= max(1, int(limit or 0)):
                return out
    return out


def _build_section_runtime_budget(
    *,
    title: str,
    chapter_target_pages: int | None,
    speed_profile: Dict[str, Any],
    specialist_count: int = 0,
    has_boq_focus: bool = False,
    has_chapter_contract: bool = False,
) -> Dict[str, int]:
    """
    Adaptive per-section context budget.
    Goal: preserve quality gates while shrinking slow-path context for low-complexity chapters.
    """
    base_kg = max(1, int(speed_profile.get("kg_top_k") or 3))
    base_doc = max(2, int(speed_profile.get("doc_limit") or 5))
    base_std = max(1, int(speed_profile.get("standard_limit") or 2))
    base_retry = max(1, min(3, int(speed_profile.get("section_retry_limit") or 2)))
    pages = max(1, int(_to_int_or_none(chapter_target_pages) or 1))
    ttl = str(title or "").strip()
    complexity = 0
    if pages >= 5:
        complexity += 2
    elif pages >= 3:
        complexity += 1
    if specialist_count >= 2:
        complexity += 1
    if has_boq_focus:
        complexity += 1
    if has_chapter_contract:
        complexity += 1
    if any(k in ttl for k in ("关键", "危大", "质量", "安全", "工期", "文明", "绿色", "材料", "机械", "劳动力", "平面")):
        complexity += 1

    # Low-complexity chapters: more aggressive compression.
    if complexity <= 1:
        timeout_cap = 55 if pages <= 1 else 70 if pages <= 2 else 85
        token_cap = 1800 if pages <= 1 else 2600 if pages <= 2 else 3400
        return {
            "kg_top_k": max(1, base_kg - 1),
            "graph_top_k": max(2, base_kg),
            "doc_limit": max(2, base_doc - 2),
            "standard_limit": max(1, base_std - 1),
            "checklist_limit": 10,
            "requirements_limit": 18,
            "kg_evidence_limit": 8,
            "doc_evidence_limit": 6,
            "section_retry_limit": 1,
            "llm_timeout_sec": min(int(speed_profile.get("llm_timeout_sec") or 120), timeout_cap),
            "max_output_tokens_hint": token_cap,
            "runtime_budget_reason": "low_complexity_small_section",
        }
    if complexity <= 3:
        timeout_cap = 95 if pages <= 3 else 110
        token_cap = 3600 if pages <= 3 else 4400
        retry_cap = 1 if pages <= 2 else min(base_retry, 2)
        return {
            "kg_top_k": base_kg,
            "graph_top_k": max(3, base_kg + 1),
            "doc_limit": max(2, base_doc - 1),
            "standard_limit": base_std,
            "checklist_limit": 14,
            "requirements_limit": 24,
            "kg_evidence_limit": 10,
            "doc_evidence_limit": 8,
            "section_retry_limit": retry_cap,
            "llm_timeout_sec": min(int(speed_profile.get("llm_timeout_sec") or 120), timeout_cap),
            "max_output_tokens_hint": token_cap,
            "runtime_budget_reason": "medium_complexity_tightened_budget",
        }
    return {
        "kg_top_k": min(6, base_kg + 1),
        "graph_top_k": min(8, base_kg + 2),
        "doc_limit": base_doc,
        "standard_limit": base_std,
        "checklist_limit": 18,
        "requirements_limit": 32,
        "kg_evidence_limit": 14,
        "doc_evidence_limit": 10,
        "section_retry_limit": base_retry,
        "llm_timeout_sec": int(speed_profile.get("llm_timeout_sec") or 120),
        "max_output_tokens_hint": 5200,
        "runtime_budget_reason": "complex_section_full_budget",
    }


def _section_cache_key(data: Dict[str, Any]) -> str:
    digest = hashlib.sha1(
        json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return digest


def _load_section_cache(
    cache_key: str,
    *,
    max_age_sec: int = 7 * 24 * 3600,
    workspace_dir: str | None = None,
) -> Dict[str, Any] | None:
    path = _section_cache_dir(workspace_dir) / f"{cache_key}.json"
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    try:
        ts = float(obj.get("_cached_at") or 0.0)
    except Exception:
        ts = 0.0
    if ts <= 0 or (time.time() - ts) > max(60, int(max_age_sec or 0)):
        return None
    sec = obj.get("section")
    return sec if isinstance(sec, dict) else None


def _save_section_cache(cache_key: str, section: Dict[str, Any], *, workspace_dir: str | None = None) -> None:
    if not isinstance(section, dict):
        return
    try:
        cache_dir = _section_cache_dir(workspace_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{cache_key}.json"
        payload = {"_cached_at": time.time(), "section": section}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


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


def _derive_section_length_bounds(
    chapter_target_pages: int | None,
    chars_per_page_hint: int,
) -> tuple[int | None, int | None, int | None]:
    """
    Convert planned chapter pages to deterministic length bounds for SectionWriter.
    Returns: (min_length, max_length, target_length)
    """
    pages = _to_int_or_none(chapter_target_pages)
    if not pages:
        return None, None, None
    cpp = max(350, min(2200, int(_to_int_or_none(chars_per_page_hint) or 900)))
    target = max(200, int(pages) * cpp)
    # Small one-page chapters (for example "工程概况") were being over-compressed by
    # runtime speed factors, causing valid engineering content to fail at ~900 chars.
    # Keep multi-page behavior unchanged, but give 1-page chapters a safer floor.
    if int(pages) <= 1:
        # One-page chapter targets are planning hints, not hard editorial ceilings.
        # "工程概况" / "编制依据" / "施工部署" often need ~1.8-2.4k Chinese chars
        # once quantified controls and闭环 actions are added. Keep 1-page as a planning
        # hint, but avoid failing valid drafts before quality remediation can run.
        target = max(target, 1200)
        min_len = max(600, int(target * 0.65))
        max_len = max(min_len + 240, int(target * 2.15), 2600)
        return min_len, max_len, target
    if int(pages) == 2:
        # Two-page chapters still need enough room for process steps + quantified controls.
        target = max(target, 2200)
        min_len = max(1000, int(target * 0.72))
        max_len = max(min_len + 280, int(target * 1.7), 3600)
        return min_len, max_len, target
    min_len = max(120, int(target * 0.8))
    max_len = max(min_len + 120, int(target * 1.2))
    return min_len, max_len, target


def _global_length_allocator(
    outline: List[str],
    chapter_pages: Dict[str, Any],
    chars_per_page_hint: int,
) -> Dict[str, Dict[str, int]]:
    """
    Allocate per-chapter text length limits from chapter page plan.
    """
    out: Dict[str, Dict[str, int]] = {}
    for raw_title in outline or []:
        title = str(raw_title or "").strip()
        if not title:
            continue
        page_target = _extract_chapter_page_target(chapter_pages, title)
        min_len, max_len, target_len = _derive_section_length_bounds(page_target, chars_per_page_hint)
        out[title] = {
            "page_target": int(page_target or 0),
            "target_length": int(target_len or 0),
            "min_length": int(min_len or 0),
            "max_length": int(max_len or 0),
        }
    return out


def _apply_final_length_bounds(
    sections: List[Dict[str, Any]],
    chapter_length_limits: Dict[str, Dict[str, int]],
) -> Dict[str, Any]:
    trimmed = 0
    skipped = 0
    failed = 0
    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip()
        text = str(sec.get("content") or "").strip()
        if not title or not text:
            skipped += 1
            continue
        cfg = chapter_length_limits.get(title) if isinstance(chapter_length_limits, dict) else None
        if not isinstance(cfg, dict):
            skipped += 1
            continue
        min_len = _to_int_or_none(cfg.get("min_length"))
        max_len = _to_int_or_none(cfg.get("max_length"))
        if not max_len or len(text) <= max_len:
            skipped += 1
            continue
        compacted = compact_text_to_length_bounds(
            text,
            min_length=min_len,
            max_length=max_len,
        )
        if compacted and compacted != text:
            sec["content"] = compacted
            logs = sec.get("constraint_log")
            if not isinstance(logs, list):
                logs = []
            logs.append(
                {
                    "attempt": 999,
                    "status": "postprocess_compacted",
                    "reason": f"final_length_out_of_range:{len(text)}>max{max_len}",
                    "clean_length": len(compacted),
                    "original_length": len(text),
                }
            )
            sec["constraint_log"] = logs
            trimmed += 1
            continue
        failed += 1
    return {"trimmed": trimmed, "skipped": skipped, "failed": failed}


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


def _has_quantitative_clause(text: str) -> bool:
    if not str(text or "").strip():
        return False
    if re.search(r"\d", text or "") and re.search(r"(次|天|h|小时|mm|cm|m|kg|%|人|台|套|MPa|kN|℃)", text or "", flags=re.IGNORECASE):
        return True
    return bool(re.search(r"每[^\n，。；;]{0,20}(次|天|班|周|月)", text or ""))


def _run_light_quality_draft(
    *,
    tender: Dict[str, Any],
    outline: List[str],
    sections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    remediation: List[Dict[str, Any]] = []
    issue_list: List[Dict[str, Any]] = []
    sec_titles = {str(s.get("title") or "").strip() for s in (sections or []) if str(s.get("title") or "").strip()}
    missing_titles = [str(t).strip() for t in (outline or []) if str(t).strip() and str(t).strip() not in sec_titles]
    if missing_titles:
        for t in missing_titles:
            issue_list.append(
                {
                    "title": t,
                    "type": "outline_missing",
                    "severity": "high",
                    "problem": "章节缺失",
                    "suggestion": "补齐招标目录章节并填充可执行内容。",
                }
            )

    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip() or "章节"
        text = str(sec.get("content") or "")
        if "【证据:" not in text:
            rec = {"title": title, "type": "evidence_gap", "suggestion": "为关键结论补充可追溯证据标注。"}
            remediation.append(rec)
            issue_list.append({"title": title, "type": "evidence_gap", "severity": "high", "problem": "证据标注不足", "suggestion": rec["suggestion"]})
        if "风险" in text and (("控制" not in text and "措施" not in text) or ("验证" not in text and "验收" not in text)):
            rec = {"title": title, "type": "risk_triplet_gap", "suggestion": "补齐“风险→控制→验证”闭环条目。"}
            remediation.append(rec)
            issue_list.append({"title": title, "type": "risk_triplet_gap", "severity": "high", "problem": "风险闭环不完整", "suggestion": rec["suggestion"]})
        if not _has_quantitative_clause(text):
            rec = {"title": title, "type": "quantitative_gap", "suggestion": "补充频次/阈值/间距/厚度/时长/人数等量化指标。"}
            remediation.append(rec)
            issue_list.append({"title": title, "type": "quantitative_gap", "severity": "medium", "problem": "量化指标不足", "suggestion": rec["suggestion"]})
        if any(w in text for w in ("加强", "确保", "严格")) and not _has_quantitative_clause(text):
            rec = {"title": title, "type": "vague_term", "suggestion": "删除空泛词，改为可执行措施+量化阈值。"}
            remediation.append(rec)
            issue_list.append({"title": title, "type": "vague_term", "severity": "medium", "problem": "存在空泛表达", "suggestion": rec["suggestion"]})

        if isinstance(tender, dict):
            missing_dims: List[str] = []
            for it in (tender.get("items") or [])[:120]:
                if not isinstance(it, dict):
                    continue
                kws = [str(x).strip() for x in (it.get("keywords") or []) if str(x).strip()]
                if not kws:
                    continue
                if not any(k in text for k in kws[:6]):
                    dim = str(it.get("dimension") or "").strip()
                    if dim and dim not in missing_dims:
                        missing_dims.append(dim)
            if missing_dims:
                rec = {
                    "title": title,
                    "type": "score_point_missing",
                    "missing_dimensions": missing_dims,
                    "suggestion": f"补齐评分点覆盖：{';'.join(missing_dims[:8])}",
                }
                remediation.append(rec)
                issue_list.append(
                    {
                        "title": title,
                        "type": "score_point_missing",
                        "severity": "high",
                        "problem": f"评分点覆盖不足：{';'.join(missing_dims[:8])}",
                        "suggestion": rec["suggestion"],
                    }
                )

    dedup = {}
    for rec in remediation:
        key = (str(rec.get("title") or ""), str(rec.get("type") or ""), str(rec.get("suggestion") or ""))
        dedup[key] = rec
    remediation = list(dedup.values())
    issue_count = len(issue_list)
    score = max(0, 100 - issue_count * 3)
    return {
        "mode": "light",
        "score": score,
        "structure": {"ok": len(missing_titles) == 0, "missing_titles": missing_titles},
        "issue_list": issue_list,
        "auto_revision_suggestions": remediation,
        "remediation": remediation,
    }


def _safe_ratio(num: Any, den: Any) -> float:
    try:
        n = float(num)
        d = float(den)
        if d <= 0:
            return 0.0
        return max(0.0, min(1.0, n / d))
    except Exception:
        return 0.0


def _ok_ratio(by_section: Any) -> float:
    if not isinstance(by_section, list) or not by_section:
        return 0.0
    total = 0
    ok = 0
    for x in by_section:
        if not isinstance(x, dict):
            continue
        total += 1
        if bool(x.get("ok")):
            ok += 1
    return _safe_ratio(ok, total)


def _build_hard_quality_gate(
    *,
    quality: Dict[str, Any],
    evidence_tracking: Dict[str, Any],
    sections: List[Dict[str, Any]],
    thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    summary = evidence_tracking.get("summary") if isinstance(evidence_tracking, dict) else {}
    paragraph_count = int(summary.get("paragraph_count") or 0)
    score_point_bound_rows = int(summary.get("score_point_bound_rows") or 0)
    evidence_bound_rows = int(summary.get("evidence_bound_rows") or 0)
    traceable_rows = int(summary.get("traceable_locator_rows") or 0)
    section_count = int(summary.get("section_count") or 0)
    evidence_bound_sections = int(summary.get("evidence_bound_sections") or 0)
    traceable_locator_sections = int(summary.get("traceable_locator_sections") or 0)
    graph_bound = sum(1 for s in (sections or []) if isinstance(s, dict) and list(s.get("graph_nodes") or []))
    chapter_count = max(1, len([s for s in (sections or []) if isinstance(s, dict)]))
    section_den = section_count if section_count > 0 else chapter_count

    t = {
        "evidence_binding_rate": 0.98,
        "traceable_locator_rate": 0.85,
        "risk_triplet_ok_rate": 0.95,
        "quantitative_ok_rate": 0.95,
        "vague_terms_ok_rate": 0.95,
        "graph_binding_rate": 0.90,
    }
    if isinstance(thresholds, dict):
        for k, v in thresholds.items():
            try:
                vv = float(v)
            except Exception:
                continue
            if 0 <= vv <= 1:
                t[str(k)] = vv

    # 证据硬闸门按“章节口径”判定，避免段落拆分数量导致误判。
    # 回退兼容：若章节级统计缺失，再使用段落级统计。
    evidence_binding_rate = (
        _safe_ratio(evidence_bound_sections, section_den)
        if evidence_bound_sections > 0
        else _safe_ratio(evidence_bound_rows, paragraph_count)
    )
    traceable_locator_rate = (
        _safe_ratio(traceable_locator_sections, section_den)
        if traceable_locator_sections > 0
        else _safe_ratio(traceable_rows, paragraph_count)
    )

    metrics = {
        "evidence_binding_rate": evidence_binding_rate,
        "traceable_locator_rate": traceable_locator_rate,
        "risk_triplet_ok_rate": _ok_ratio((quality.get("risk_triplet") or {}).get("by_section")),
        "quantitative_ok_rate": _ok_ratio((quality.get("quantitative") or {}).get("by_section")),
        "vague_terms_ok_rate": _ok_ratio((quality.get("vague_terms") or {}).get("by_section")),
        "graph_binding_rate": _safe_ratio(graph_bound, chapter_count),
    }
    failed = []
    type_map = {
        "evidence_binding_rate": "evidence_gap",
        "traceable_locator_rate": "evidence_traceability_gap",
        "risk_triplet_ok_rate": "risk_triplet_gap",
        "quantitative_ok_rate": "quantitative_gap",
        "vague_terms_ok_rate": "vague_term",
        "graph_binding_rate": "evidence_gap",
    }
    for k, v in metrics.items():
        th = float(t.get(k) or 0.0)
        if v < th:
            failed.append(
                {
                    "metric": k,
                    "value": round(v, 4),
                    "threshold": round(th, 4),
                    "gap": round(th - v, 4),
                    "remediation_type": type_map.get(k, "evidence_gap"),
                }
            )
    return {
        "ok": len(failed) == 0,
        "metrics": metrics,
        "thresholds": t,
        "failed": failed,
    }


def _failed_gate_metrics(gate: Dict[str, Any] | None) -> set[str]:
    if not isinstance(gate, dict):
        return set()
    failed = gate.get("failed") if isinstance(gate.get("failed"), list) else []
    return {
        str(item.get("metric") or "").strip()
        for item in failed
        if isinstance(item, dict) and str(item.get("metric") or "").strip()
    }


def _candidate_failed_metrics_from_rows(rows: List[Dict[str, Any]] | None) -> set[str]:
    metrics: set[str] = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        for metric_name in row.get("expected_quality_gate_metrics") or []:
            metric_text = str(metric_name or "").strip()
            if metric_text:
                metrics.add(metric_text)
    return metrics


def _quality_score(report: Dict[str, Any] | None) -> int:
    if not isinstance(report, dict):
        return 0
    try:
        explicit = report.get("score")
        if explicit is not None:
            return max(0, min(100, int(float(explicit))))
    except Exception:
        pass
    issue_cnt = len(report.get("issue_list") or []) if isinstance(report.get("issue_list"), list) else 0
    structure = report.get("structure") if isinstance(report.get("structure"), dict) else {}
    missing_titles = len(structure.get("missing_titles") or []) if isinstance(structure.get("missing_titles"), list) else 0
    base = 100 - issue_cnt * 2 - missing_titles * 5
    return max(0, min(100, int(base)))


def _collect_gate_remediation(
    *,
    quality: Dict[str, Any],
    sections: List[Dict[str, Any]],
    failed: List[Dict[str, Any]],
    params: Dict[str, Any] | None = None,
    project_type: str = "",
    generation_mode: str = "",
    runtime_budget_profile: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if not failed:
        return []

    failed_types = {str(x.get("remediation_type") or "").strip() for x in failed if isinstance(x, dict)}
    out: List[Dict[str, Any]] = []
    existing = quality.get("auto_revision_suggestions") if isinstance(quality.get("auto_revision_suggestions"), list) else []
    covered_types: set[str] = set()
    for rec in existing:
        if not isinstance(rec, dict):
            continue
        rtype = str(rec.get("type") or "").strip()
        if rtype and rtype in failed_types:
            out.append(dict(rec))
            covered_types.add(rtype)
    failed_types = {x for x in failed_types if x and x not in covered_types}

    if "risk_triplet_gap" in failed_types:
        for row in (quality.get("risk_triplet") or {}).get("by_section") or []:
            if not isinstance(row, dict) or row.get("ok"):
                continue
            out.append(
                {
                    "title": str(row.get("title") or "章节"),
                    "type": "risk_triplet_gap",
                    "suggestion": "补齐“风险→控制→验证”三元组，并写明验证阈值与记录表。",
                }
            )

    if "quantitative_gap" in failed_types:
        for row in (quality.get("quantitative") or {}).get("by_section") or []:
            if not isinstance(row, dict) or row.get("ok"):
                continue
            missing = [str(x).strip() for x in (row.get("missing") or []) if str(x).strip()]
            out.append(
                {
                    "title": str(row.get("title") or "章节"),
                    "type": "quantitative_gap",
                    "suggestion": f"补齐量化指标（优先：{','.join(missing[:5]) or '频次/阈值/间距/厚度/时长'}）。",
                }
            )

    if "vague_term" in failed_types:
        for row in (quality.get("vague_terms") or {}).get("by_section") or []:
            if not isinstance(row, dict) or row.get("ok"):
                continue
            out.append(
                {
                    "title": str(row.get("title") or "章节"),
                    "type": "vague_term",
                    "suggestion": "删除空泛词，改写为动作+参数+频次+责任+验收。",
                }
            )

    if "evidence_gap" in failed_types:
        for row in (quality.get("evidence_quality") or {}).get("by_section") or []:
            if not isinstance(row, dict) or row.get("ok"):
                continue
            out.append(
                {
                    "title": str(row.get("title") or "章节"),
                    "type": "evidence_gap",
                    "suggestion": "补齐可追溯证据标注（文件名#p页_sha@offset），每章至少1条。",
                }
            )

    if "evidence_traceability_gap" in failed_types:
        for row in (quality.get("evidence_traceability") or {}).get("by_section") or []:
            if not isinstance(row, dict) or row.get("ok"):
                continue
            out.append(
                {
                    "title": str(row.get("title") or "章节"),
                    "type": "evidence_traceability_gap",
                    "suggestion": "补齐定位符证据（文件名#p页_sha@offset），用于评审追溯。",
                }
            )

    if "evidence_gap" in failed_types:
        for sec in sections or []:
            if not isinstance(sec, dict):
                continue
            title = str(sec.get("title") or "").strip()
            if not title:
                continue
            if list(sec.get("graph_nodes") or []):
                continue
            out.append(
                {
                    "title": title,
                    "type": "evidence_gap",
                    "suggestion": "本章需至少绑定1个图谱逻辑节点，并在正文中保留图谱节点标注。",
                }
            )

    dedup: Dict[tuple[str, str, str, str], Dict[str, Any]] = {}
    for rec in out:
        key = (
            str(rec.get("title") or ""),
            str(rec.get("type") or ""),
            str(rec.get("strategy_id") or ""),
            str(rec.get("suggestion") or ""),
        )
        dedup[key] = rec
    rows = list(dedup.values())
    sec_by_title: Dict[str, Dict[str, Any]] = {}
    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip()
        if title:
            sec_by_title.setdefault(title, sec)
    rows = enrich_strategy_rows(rows, sec_by_title=sec_by_title)
    rows = _attach_remediation_target_section_titles(rows, sections)
    learning_hint = prioritize_remediation_rows_with_learning(
        params=params,
        project_type=project_type,
        generation_mode=generation_mode,
        rows=rows,
        profile=runtime_budget_profile,
    )
    prioritized = learning_hint.get("rows") if isinstance(learning_hint.get("rows"), list) else rows
    return [dict(row) for row in prioritized if isinstance(row, dict)]


def _resolve_remediation_target_section_title(
    *,
    sections: List[Dict[str, Any]],
    title: str | None,
    rtype: str | None,
) -> str:
    target_title = str(title or "").strip()
    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        sec_title = str(sec.get("title") or "").strip()
        if target_title and sec_title == target_title:
            return sec_title

    virtual_titles = {"全局一致性", "清单重点项", "专项主题"}
    virtual_types = {"consistency_conflict", "boq_focus_item_closure_gap", "required_topic_detail_gap", "special_topic_missing"}
    normalized_type = str(rtype or "").strip()
    if (target_title not in virtual_titles) and (normalized_type not in virtual_types):
        return ""

    if normalized_type == "consistency_conflict" or target_title == "全局一致性":
        prefer = ["进度", "工期", "计划", "资源", "关键线路"]
    elif normalized_type == "boq_focus_item_closure_gap" or target_title == "清单重点项":
        prefer = ["施工方案", "施工方法", "主要施工", "施工工艺", "技术措施", "资源", "材料", "设备"]
    else:
        prefer = ["安全", "文明", "环保", "绿色", "信息化", "材料", "资源", "技术措施", "施工方案"]

    for keyword in prefer:
        for sec in sections or []:
            if keyword in str(sec.get("title") or ""):
                return str(sec.get("title") or "").strip()

    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        sec_title = str(sec.get("title") or "").strip()
        if sec_title:
            return sec_title
    return ""


def _attach_remediation_target_section_titles(
    rows: List[Dict[str, Any]],
    sections: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    section_meta_map: Dict[str, Dict[str, str]] = {}
    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        sec_title = str(sec.get("title") or "").strip()
        if not sec_title or sec_title in section_meta_map:
            continue
        section_meta_map[sec_title] = {
            "chapter_domain": str(sec.get("chapter_domain") or "").strip().lower(),
            "template_id": str(sec.get("logic_template_id") or "").strip().upper(),
        }
    attached: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        target_section_title = _resolve_remediation_target_section_title(
            sections=sections,
            title=item.get("title"),
            rtype=item.get("type"),
        )
        if target_section_title:
            item["target_section_title"] = target_section_title
            meta = section_meta_map.get(target_section_title) or {}
            if meta.get("chapter_domain") and not str(item.get("chapter_domain") or "").strip():
                item["chapter_domain"] = str(meta.get("chapter_domain") or "").strip()
            if meta.get("template_id") and not str(item.get("template_id") or "").strip():
                item["template_id"] = str(meta.get("template_id") or "").strip()
        attached.append(item)
    return attached


def _ensure_traceable_evidence_per_section(
    *,
    sections: List[Dict[str, Any]],
    project_id: str,
    topic: str,
    workspace_dir: str | None = None,
) -> Dict[str, Any]:
    """
    Fast deterministic post-process:
    ensure each section contains at least one traceable evidence locator
    (filename#p{page}_{sha}@offset). This improves evidence traceability
    stability without extra LLM calls.
    """
    fixed = 0
    skipped = 0
    failed = 0
    cache: Dict[str, str] = {}

    def _pick_locator(title: str) -> str:
        key = title.strip() or "__default__"
        if key in cache:
            return cache[key]
        hit = best_ingested_hit(
            f"{topic} {title} 施工组织设计",
            limit=8,
            project_id=project_id,
            audit_path=workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else None,
        )
        loc = str((hit or {}).get("locator") or "").strip()
        if not loc or "@" not in loc or "#" not in loc:
            hit = best_ingested_hit(
                f"{title} 施工 质量 安全 证据",
                limit=8,
                project_id=project_id,
                audit_path=workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else None,
            )
            loc = str((hit or {}).get("locator") or "").strip()
        if (not loc or "@" not in loc or "#" not in loc) and isinstance(tender, dict):
            hit = best_tender_source_span_hit(
                tender,
                f"{title} {topic} 招标要求",
                prefer_filename_keywords=["招标", "清单", "BOQ", "工程量"],
            )
            loc = str((hit or {}).get("locator") or "").strip()
        cache[key] = loc
        return loc

    for sec in sections or []:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "").strip() or "章节"
        text = str(sec.get("content") or "")
        if not text.strip() or "章节生成失败" in text:
            failed += 1
            continue
        if TRACEABLE_EVIDENCE_RE.search(text):
            skipped += 1
            continue
        loc = _pick_locator(title)
        if not loc or "@" not in loc or "#" not in loc:
            failed += 1
            continue
        addon = (
            "\n\n【证据追溯校核】\n"
            f"- 本章最小追溯定位符：{loc}；核验动作=抽检1次/章，记录表=《章节证据定位表》。"
            f"【证据:{loc}】\n"
        )
        sec["content"] = (text.rstrip() + addon).strip() + "\n"
        fixed += 1
    return {"fixed": fixed, "skipped": skipped, "failed": failed}


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
    4) payload.api_key（仅当provider一致，避免跨Provider误用）
    5) provider-specific env vars
    """
    if isinstance(explicit_key, str) and explicit_key.strip():
        return explicit_key.strip()

    key_from_slot, _ = resolve_text_slot_credentials(slot_id, provider)
    if key_from_slot:
        return key_from_slot

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
        default_provider = str(payload.get("provider") or "").strip().lower()
        if not default_provider or default_provider == p:
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


def _resolve_provider_credentials(
    payload: Dict[str, Any],
    provider: str | None,
    *,
    slot_id: str | None = None,
    explicit_key: str | None = None,
    explicit_alias: str | None = None,
) -> tuple[str | None, str | None]:
    key = _resolve_provider_api_key(
        payload,
        provider,
        slot_id=slot_id,
        explicit_key=explicit_key,
    )
    if isinstance(explicit_alias, str) and explicit_alias.strip():
        return key, explicit_alias.strip()
    _, alias = resolve_text_slot_credentials(slot_id, provider)
    return key, alias


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
            provider, model = normalize_provider_model_pair(
                item.get("provider"),
                item.get("model"),
            )
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
            provider, model = normalize_provider_model_pair(
                p,
                str(model_map.get(str(p or "").strip().lower()) or payload.get("model") or "").strip(),
            )
            if not provider:
                continue
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

    provider, model = normalize_provider_model_pair(
        payload.get("provider"),
        payload.get("model"),
    )
    if provider and model:
        chain.append({"slot": "legacy_primary", "provider": provider, "model": model, "api_key": ""})
    return chain


async def run_autoplan(payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = payload.get("topic") or "未命名项目"
    raw_payload_outline = payload.get("outline")
    outline = raw_payload_outline or []
    payload_outline_given = bool(isinstance(raw_payload_outline, list) and len(raw_payload_outline) > 0)
    requirements = payload.get("requirements") or []
    global_instruction = str(payload.get("global_instruction") or "").strip()
    qingtian_policy_enabled = bool(payload.get("qingtian_policy_enabled", True))
    chapter_requirements = payload.get("chapter_requirements") or {}
    style = payload.get("style") or {}
    chapter_pages = payload.get("chapter_pages") or {}
    provider, model = normalize_provider_model_pair(
        payload.get("provider"),
        payload.get("model"),
    )
    providers = payload.get("providers") or []
    model_map = payload.get("model_map") or {}
    provider_chain = _normalize_provider_chain(payload)
    if provider_chain:
        provider = provider_chain[0].get("provider") or provider
        model = provider_chain[0].get("model") or model
    has_llm_runtime = bool(provider_chain or providers or (provider and model))
    dry_run = bool(payload.get("dry_run", False))
    generate_images = bool(payload.get("generate_images", True))
    strict_quality = bool(payload.get("quality_strict", True))
    mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    mode_effective = str(mode_policy.get("mode_effective") or payload.get("generation_mode") or "quality_200").strip() or "quality_200"
    draft_quality_mode = str(payload.get("draft_quality_mode") or "").strip().lower()
    if draft_quality_mode not in {"full", "light"}:
        draft_quality_mode = "light" if mode_effective in {"hq_speed_500", "speed_fast"} else "full"
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
    session_id = str(payload.get("session_id") or "").strip() or None
    workspace_dir = str(
        resolve_workspace_dir(
            session_id=session_id,
            workspace_dir=str(payload.get("workspace_dir") or "").strip() or None,
        )
    )
    payload["workspace_dir"] = workspace_dir
    if session_id:
        payload["session_id"] = session_id
    maybe_cleanup_expired_workspaces(exclude_workspace=workspace_dir)
    _trace_runtime(
        payload,
        "run_autoplan_started",
        project_id=project_id or "",
        topic=topic,
        generation_mode=str(payload.get("generation_mode") or ""),
        provider_chain=str(len(provider_chain) if isinstance(provider_chain, list) else 0),
    )
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
                workspace_dir=workspace_dir,
            )
            if logo_raw:
                logo_raw_path = str(logo_raw)
                logo_embed = prepare_logo_for_embedding(logo_raw, workspace_dir=workspace_dir) or None
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
                    workspace_dir=workspace_dir,
                )
        except Exception:
            pass

    tender = payload.get("tender_matrix") or load_tender_matrix(project_id=project_id, workspace_dir=workspace_dir) or {}
    project_name = str(payload.get("project_name") or tender.get("project_name") or "").strip()
    project_code = str(payload.get("project_code") or tender.get("project_code") or "").strip()
    bidding_format_config = tender.get("bidding_format_config") if isinstance(tender, dict) else None
    if not isinstance(bidding_format_config, dict):
        bidding_format_config = load_bidding_format_config(project_id=project_id, workspace_dir=workspace_dir) or {}
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
    self_evolution_profile = load_runtime_budget_profile()
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
    qingtian_receipt: Dict[str, Any] = {"enabled": False, "used_fallback_16": False}
    if qingtian_policy_enabled:
        outline, qingtian_receipt = apply_qingtian_outline_policy(
            outline=[str(x).strip() for x in (outline or []) if str(x).strip()],
            outline_source=str(tender.get("outline_source") or ""),
            strict_tender_outline=bool(strict_tender_outline),
            payload_outline_given=payload_outline_given,
        )
        if bool(qingtian_receipt.get("used_fallback_16")):
            tender_globals.append("目录识别到非完整技术标目录，已自动切换为16章施组适配目录。")
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
    template_page_bucket = infer_template_page_bucket(total_pages_limit)
    speed_profile = _resolve_runtime_speed_profile(
        mode_effective=mode_effective,
        total_pages_limit=int(total_pages_limit or 0),
        payload=payload,
    )
    chapter_pages = plan_chapter_pages(
        outline,
        total_pages=total_pages_limit,
        chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
    )
    front_matter_outline = payload.get("front_matter_outline") if isinstance(payload.get("front_matter_outline"), dict) else {}
    front_matter_toc_entries: List[Dict[str, Any]] = []
    for idx, item in enumerate(front_matter_outline.get("toc_entries") or [], start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        front_matter_toc_entries.append(
            {
                "order": _to_int_or_none(item.get("order")) or idx,
                "title": title,
                "start_page": _to_int_or_none(item.get("start_page")) or 1,
                "planned_pages": _to_int_or_none(item.get("planned_pages")) or _extract_chapter_page_target(chapter_pages, title) or 1,
            }
        )
    front_matter_toc_map = {
        str(item.get("title") or "").strip(): item
        for item in front_matter_toc_entries
        if str(item.get("title") or "").strip()
    }
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
    boq = payload.get("boq_data") or load_boq_data(project_id=project_id, workspace_dir=workspace_dir) or {}
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

    effective_global_instruction = (
        compose_qingtian_global_instruction(global_instruction)
        if qingtian_policy_enabled
        else global_instruction
    )

    base_requirements: list[str] = []
    front_matter_requirement_seed: list[str] = []
    if effective_global_instruction:
        base_requirements.append(f"【系统全局指令（必须无条件执行）】{effective_global_instruction}")
    if project_type:
        base_requirements.append(f"【项目类型】{project_type}（按该行业专项逻辑编制）")
        base_requirements.extend(type_requirements)
    base_requirements.extend(list(requirements))
    base_requirements.extend(tender_globals)
    base_requirements.extend(schedule_constraints)
    if front_matter_toc_entries:
        sequence = [str(x).strip() for x in (front_matter_outline.get("sequence") or []) if str(x).strip()]
        if sequence:
            line = f"正文编制顺序必须服从前置页计划：{' -> '.join(sequence)}。"
            base_requirements.append(line)
            front_matter_requirement_seed.append(line)
        chapter_line = f"正文必须严格覆盖预生成目录，共{len(front_matter_toc_entries)}章；不得改动目录章节标题与顺序。"
        base_requirements.append(
            chapter_line
        )
        front_matter_requirement_seed.append(chapter_line)
        toc_preview = "；".join(
            [
                f"{int(item.get('order') or 0):02d}.{item.get('title')}@第{int(item.get('start_page') or 1)}页/约{int(item.get('planned_pages') or 1)}页"
                for item in front_matter_toc_entries[:6]
            ]
        )
        if toc_preview:
            preview_line = f"预生成目录锚点：{toc_preview}"
            base_requirements.append(preview_line)
            front_matter_requirement_seed.append(preview_line)
    base_requirements.extend(SYSTEM_MANDATORY_REQUIREMENTS)
    if qingtian_policy_enabled:
        base_requirements.extend(QINGTIAN_GLOBAL_REQUIREMENTS)
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
    shared_cache_obj = payload.get("_shared_retrieval_cache_obj")
    cache_enabled = bool(payload.get("enable_retrieval_cache", True))
    if not isinstance(shared_cache_obj, dict):
        shared_cache_obj = {"items": {}, "stats": {"hits": 0, "misses": 0, "stores": 0}}
    cache_items = shared_cache_obj.setdefault("items", {})
    cache_stats = shared_cache_obj.setdefault("stats", {})
    cache_stats.setdefault("hits", 0)
    cache_stats.setdefault("misses", 0)
    cache_stats.setdefault("stores", 0)
    retrieval_cache = AsyncThreadCache(
        items=cache_items,
        stats=cache_stats,
        enabled=cache_enabled,
    )

    def _cache_key(kind: str, payload_obj: Dict[str, Any]) -> str:
        safe = {
            "kind": str(kind or "").strip(),
            "data": payload_obj,
        }
        digest = hashlib.sha1(
            json.dumps(safe, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return f"{safe['kind']}:{digest}"

    async def _cached_to_thread(
        kind: str,
        key_data: Dict[str, Any],
        fn,
        *args,
        **kwargs,
    ):
        key = _cache_key(kind, key_data)
        return await retrieval_cache.get_or_run(key, fn, *args, **kwargs)

    def _pick_provider(idx: int) -> tuple[str | None, str | None, str | None, str | None, str | None]:
        if provider_chain:
            entry = provider_chain[idx % len(provider_chain)]
            return (
                str(entry.get("provider") or "").strip().lower() or None,
                str(entry.get("model") or "").strip() or None,
                str(entry.get("api_key") or "").strip() or None,
                str(entry.get("slot") or "").strip() or None,
                str(entry.get("key_alias") or "").strip() or None,
            )
        if providers:
            p = providers[idx % len(providers)]
            m = model_map.get(p) or model
            return p, m, None, None, None
        return provider, model, None, None, None

    weights, penalties = _build_weights_and_penalties(tender)
    chars_per_page_hint = _estimate_chars_per_page(style)
    try:
        chars_per_page_hint = int(
            max(320, min(1600, round(chars_per_page_hint * float(speed_profile.get("chars_per_page_factor") or 1.0))))
        )
    except Exception:
        pass
    chapter_length_limits = _global_length_allocator(
        outline if isinstance(outline, list) else [],
        chapter_pages if isinstance(chapter_pages, dict) else {},
        chars_per_page_hint,
    )
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

    async def build_section(idx: int, title: str):
        # 章节级重试：多模型轮询重试，最多尝试 3 个 provider（主+备1+备2）
        tries = []
        if provider_chain:
            for i in range(len(provider_chain)):
                p, m, k, sid, kalias = _pick_provider(i)
                tries.append((p, m, k, sid, kalias))
        elif providers:
            for i in range(len(providers)):
                p, m, k, sid, kalias = _pick_provider(i)
                tries.append((p, m, k, sid, kalias))
        else:
            tries.append((provider, model, None, None, None))
        tries = tries[:5]
        chapter_contract = chapter_contract_map.get(str(title).strip()) if isinstance(chapter_contract_map, dict) else None
        chapter_len_cfg = chapter_length_limits.get(str(title).strip()) if isinstance(chapter_length_limits, dict) else {}
        chapter_target_pages = _to_int_or_none((chapter_len_cfg or {}).get("page_target"))
        if chapter_target_pages is None and isinstance(chapter_contract, dict):
            chapter_target_pages = _to_int_or_none(chapter_contract.get("page_target"))
        runtime_budget = _build_section_runtime_budget(
            title=title,
            chapter_target_pages=chapter_target_pages,
            speed_profile=speed_profile,
            specialist_count=len(multi_agent_plan.chapter_agents(title).get("specialists") or []),
            has_boq_focus=bool(boq_focus.get("must_cover_keywords")),
            has_chapter_contract=isinstance(chapter_contract, dict) and bool(chapter_contract),
        )
        evolution_hint = build_runtime_budget_hints(
            params=params,
            title=title,
            project_type=project_type,
            generation_mode=mode_effective,
            runtime_budget=runtime_budget,
            profile=self_evolution_profile,
        )
        if bool(evolution_hint.get("applied")):
            for key in ("llm_timeout_sec", "max_output_tokens_hint", "section_retry_limit"):
                if evolution_hint.get(key) is not None:
                    runtime_budget[key] = evolution_hint.get(key)
        kg_top_k = int(runtime_budget.get("kg_top_k") or speed_profile.get("kg_top_k") or 3)
        doc_limit = int(runtime_budget.get("doc_limit") or speed_profile.get("doc_limit") or 5)
        standard_limit = int(runtime_budget.get("standard_limit") or speed_profile.get("standard_limit") or 2)
        graph_top_k = int(runtime_budget.get("graph_top_k") or max(3, kg_top_k))
        checklist_limit = int(runtime_budget.get("checklist_limit") or 14)
        requirements_limit = int(runtime_budget.get("requirements_limit") or 24)
        kg_evidence_limit = int(runtime_budget.get("kg_evidence_limit") or 10)
        doc_evidence_limit = int(runtime_budget.get("doc_evidence_limit") or 8)
        section_retry_limit = int(runtime_budget.get("section_retry_limit") or speed_profile.get("section_retry_limit") or 2)
        llm_timeout_sec = int(runtime_budget.get("llm_timeout_sec") or speed_profile.get("llm_timeout_sec") or 120)
        max_output_tokens_hint = _to_int_or_none(runtime_budget.get("max_output_tokens_hint"))
        runtime_budget_reason = str(runtime_budget.get("runtime_budget_reason") or "").strip()
        evolution_applied = bool(evolution_hint.get("applied"))
        evolution_reason = str(evolution_hint.get("reason") or "").strip()
        evolution_source_runs = int(evolution_hint.get("source_runs") or 0)
        kg_query = f"{topic} {title} 施工组织 质量 安全 工期"
        doc_query = f"{topic} {title} 招标 清单 图纸 质量 安全 工期"
        kg_task = _cached_to_thread(
            "kg_search",
            {
                "project_id": project_id,
                "query": kg_query,
                "top_k": kg_top_k,
            },
            search_kg,
            kg_query,
            top_k=kg_top_k,
        )
        doc_task = _cached_to_thread(
            "doc_search",
            {
                "project_id": project_id,
                "query": doc_query,
                "limit": doc_limit,
                "require_tags": [],
            },
            search_ingested_docs,
            doc_query,
            limit=doc_limit,
            project_id=project_id,
        )
        # Prefer enterprise standards / work instructions when provided (to raise output quality and reduce hallucination).
        # Only do this when project_id is set, otherwise global audit may cross-contaminate between projects.
        standard_task = None
        if project_id:
            std_query = f"{topic} {title} 企业标准 工法 作业指导 标准化 质量验收"
            standard_task = _cached_to_thread(
                "doc_search_standard",
                {
                    "project_id": project_id,
                    "query": std_query,
                    "limit": standard_limit,
                    "require_tags": ["standard"],
                },
                search_ingested_docs,
                std_query,
                limit=standard_limit,
                project_id=project_id,
                require_tags=["standard"],
            )
        template_learning_task = None
        if project_type:
            template_scene_tags = infer_template_scene_tags(
                topic,
                payload.get("project_name"),
                payload.get("project_title"),
                title,
                payload.get("global_instruction"),
                project_type=project_type,
            )
            project_reference_parts: list[str] = []
            for value in (
                project_id,
                topic,
                payload.get("project_name"),
                payload.get("project_title"),
            ):
                text = str(value or "").strip()
                if not text or text in project_reference_parts:
                    continue
                project_reference_parts.append(text)
            project_reference = " ".join(project_reference_parts[:3]).strip()
            scene_query = " ".join(template_scene_tags[:4]).strip()
            template_query = f"{project_type} {project_reference} {scene_query} {title} 施工组织设计 样板 案例".strip()
            template_limit = max(1, min(3, standard_limit + 1))
            template_learning_task = _cached_to_thread(
                "template_chapter_learning",
                {
                    "project_type": project_type,
                    "template_page_bucket": template_page_bucket,
                    "chapter_title": title,
                    "scene_tags": template_scene_tags,
                    "query": template_query,
                    "limit": template_limit,
                },
                build_template_chapter_learning_context,
                template_query,
                chapter_title=title,
                project_type=project_type,
                template_page_bucket=template_page_bucket,
                scene_tags=template_scene_tags,
                limit=template_limit,
            )
        if standard_task is not None and template_learning_task is not None:
            kg_hits, doc_hits, standard_hits, template_learning = await asyncio.gather(
                kg_task,
                doc_task,
                standard_task,
                template_learning_task,
            )
        elif standard_task is not None:
            kg_hits, doc_hits, standard_hits = await asyncio.gather(kg_task, doc_task, standard_task)
            template_learning = {}
        elif template_learning_task is not None:
            kg_hits, doc_hits, template_learning = await asyncio.gather(kg_task, doc_task, template_learning_task)
            standard_hits = []
        else:
            kg_hits, doc_hits = await asyncio.gather(kg_task, doc_task)
            standard_hits = []
            template_learning = {}
        template_hits = template_learning.get("hits") if isinstance(template_learning, dict) else []
        if not isinstance(template_hits, list):
            template_hits = []
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
            if len(doc_evidence) >= doc_evidence_limit:
                break
        if not doc_evidence and isinstance(tender, dict):
            for h in search_tender_source_spans(
                tender,
                f"{title} {topic}",
                limit=doc_evidence_limit,
                prefer_filename_keywords=["招标", "清单", "BOQ", "工程量"],
            ):
                prefix = str(h.get("locator") or "").strip()
                if not prefix or prefix in seen_loc:
                    continue
                seen_loc.add(prefix)
                doc_evidence.append(f"{prefix}: {h.get('snippet')}")
                if len(doc_evidence) >= doc_evidence_limit:
                    break
        template_evidence_count = 0
        for h in template_hits or []:
            prefix = format_hit_locator(h)
            section_hint = str(h.get("section_title") or "").strip()
            template_prefix = f"样板案例/{prefix}"
            if section_hint:
                template_prefix += f"【样板章节:{section_hint}】"
            if template_prefix in seen_loc:
                continue
            seen_loc.add(template_prefix)
            doc_evidence.append(f"{template_prefix}: {h.get('snippet')}")
            template_evidence_count += 1
            if template_evidence_count >= 2:
                break
        checklist = _build_section_checklist(
            tender if isinstance(tender, dict) else {},
            title,
            limit=checklist_limit,
        )

        explicit_chapter_requirements = _chapter_requirements_for_title(chapter_requirements, title)
        section_requirements = list(base_requirements)
        front_matter_entry = front_matter_toc_map.get(str(title).strip()) if isinstance(front_matter_toc_map, dict) else None
        front_matter_chapter_requirements: List[str] = []
        if qingtian_policy_enabled:
            section_requirements.extend(
                build_qingtian_chapter_requirements(
                    title=str(title),
                    chapter_no=idx + 1,
                )
            )
        section_requirements.extend(explicit_chapter_requirements)
        if isinstance(chapter_contract, dict):
            for req_line in chapter_contract.get("requirements") or []:
                line = str(req_line).strip()
                if line:
                    section_requirements.append(f"本章合同要求：{line}")
        if isinstance(front_matter_entry, dict):
            front_matter_chapter_requirements.append(
                f"目录定位：本章为第{int(front_matter_entry.get('order') or idx + 1)}章，目录起始页第{int(front_matter_entry.get('start_page') or 1)}页，计划篇幅约{int(front_matter_entry.get('planned_pages') or 1)}页。"
            )
            section_requirements.extend(front_matter_chapter_requirements)
            if int(front_matter_outline.get("full_index_pages") or 0) > 0:
                line = "全文索引已收录本章，正文首段需准确概括本章覆盖范围，便于索引回查。"
                front_matter_chapter_requirements.append(line)
                section_requirements.append(line)
        # Chapter blueprint: when the tender outline contains a known chapter theme,
        # inject the corresponding "章内结构" guidance (does not change outline).
        bp = None
        try:
            from backend.zhifei_autoplan.chapter_blueprints import match_chapter_blueprint
            bp = match_chapter_blueprint(title)
        except Exception:
            bp = None
        section_min_length = _to_int_or_none((chapter_len_cfg or {}).get("min_length"))
        section_max_length = _to_int_or_none((chapter_len_cfg or {}).get("max_length"))
        target_chars = _to_int_or_none((chapter_len_cfg or {}).get("target_length"))
        if chapter_target_pages and (section_min_length is None or section_max_length is None or target_chars is None):
            section_min_length, section_max_length, target_chars = _derive_section_length_bounds(
                chapter_target_pages,
                chars_per_page_hint,
            )
        if chapter_target_pages and target_chars:
            section_requirements.append(
                f"本章目标页数：{chapter_target_pages}页（建议正文约{target_chars}字，允许±20%）"
            )
        if section_min_length and section_max_length:
            section_requirements.append(
                f"本章字数边界：{section_min_length}-{section_max_length}字（由全局篇幅分配器自动下发）。"
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
        template_requirement_lines = template_learning.get("requirement_lines") if isinstance(template_learning, dict) else []
        if isinstance(template_requirement_lines, list):
            section_requirements.extend([str(x).strip() for x in template_requirement_lines if str(x).strip()])
        if template_hits:
            section_requirements.append(
                f"同类型同篇幅档位样板库已命中 {len(template_hits)} 条，可吸收其结构与短句表达，但不得覆盖本项目招标目录、硬约束与证据。"
            )
        if has_llm_runtime:
            graph_query = f"{topic} {title} 施工组织 质量 安全 工期 图纸 清单"
            graph_ctx = await _cached_to_thread(
                "graph_context",
                {
                    "project_id": project_id,
                    "title": title,
                    "query": graph_query,
                    "top_k": graph_top_k,
                    "req_digest": hashlib.sha1(
                        "\n".join(section_requirements).encode("utf-8", errors="ignore")
                    ).hexdigest(),
                },
                multi_agent_plan.chapter_graph_context,
                title=title,
                query=graph_query,
                section_requirements=section_requirements,
                top_k=graph_top_k,
            )
        else:
            # Fast path for no-model dry/template runs: avoid heavy graph dispatch scanning.
            graph_ctx = {
                "hits": [],
                "node_bindings": [],
                "experience_values": [],
                "need_experience": False,
                "agents": multi_agent_plan.chapter_agents(title),
            }
        graph_hits = graph_ctx.get("hits") or []
        for gh in graph_hits[:6]:
            gname = str(gh.get("graph_name") or gh.get("graph_file") or "图谱").strip()
            gtitle = str(gh.get("title") or "节点").strip()
            gtext = str(gh.get("text") or "").strip()
            if not gtext:
                continue
            kg_evidence.append(f"{gname}/{gtitle}: {gtext}")
        kg_evidence = _dedup_lines(kg_evidence, limit=kg_evidence_limit)
        exp_values = [str(x).strip() for x in (graph_ctx.get("experience_values") or []) if str(x).strip()]
        if exp_values:
            section_requirements.append("招标文件未明确给值的参数，按图谱同类工程经验值补位并显式标注：")
            section_requirements.extend(exp_values[:4])
            section_requirements.append("凡经验值必须保留“【经验值:...】”与“【图谱经验值:...】”标记。")
        # Compliance retrieval: pre-filter by involved domain + prefer latest standard version.
        compliance_domains = [str(x).strip() for x in (graph_ctx.get("agents", {}).get("domain_tags") or []) if str(x).strip()]
        if not compliance_domains:
            compliance_domains = [str(x).strip() for x in (multi_agent_plan.dispatch.get("involved_domains") or []) if str(x).strip()]
        if has_llm_runtime:
            compliance_query = f"{topic} {title} 质量 安全 工期 验收 允许偏差 抽检 频次"
            compliance_hits = await _cached_to_thread(
                "compliance_search",
                {
                    "query": compliance_query,
                    "domain_tags": compliance_domains or [],
                    "top_k": 4,
                    "prefer_latest": True,
                },
                query_compliance,
                compliance_query,
                domain_tags=compliance_domains or None,
                top_k=4,
                prefer_latest=True,
            )
        else:
            compliance_hits = []
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
        kg_evidence = _dedup_lines(kg_evidence, limit=kg_evidence_limit + 2)
        preserve_lines = list(requirements) + explicit_chapter_requirements
        preserve_lines.extend(front_matter_requirement_seed)
        preserve_lines.extend(front_matter_chapter_requirements)
        if isinstance(chapter_contract, dict):
            preserve_lines.extend(
                [f"本章合同要求：{str(req_line).strip()}" for req_line in (chapter_contract.get("requirements") or []) if str(req_line).strip()]
            )
        if isinstance(template_requirement_lines, list):
            preserve_lines.extend([str(x).strip() for x in template_requirement_lines if str(x).strip()])
        section_requirements = _compress_section_requirements(
            section_requirements,
            limit=requirements_limit,
            preserve=preserve_lines,
        )

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
            "section_target_length": target_chars,
            "section_min_length": section_min_length,
            "section_max_length": section_max_length,
            "min_length": section_min_length,
            "max_length": section_max_length,
            "boq_focus": boq_focus,
            "standard_trades": STANDARD_TRADES,
            "params": params,
            "project_type": project_type,
            "global_instruction": effective_global_instruction,
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
            "front_matter_entry": front_matter_entry or {},
            "front_matter_outline": front_matter_outline if isinstance(front_matter_outline, dict) else {},
            "enterprise_profile": enterprise_profile,
            "missing_param_probe": missing_param_probe,
            "boq_wbs_cpm_summary": cpm_summary if isinstance(cpm_summary, dict) else {},
            "boq_wbs_top_process": (boq_wbs_cpm.get("wbs") or [])[:8] if isinstance(boq_wbs_cpm, dict) else [],
            "labor_hint": labor_hint if isinstance(labor_hint, dict) else {},
            "compliance_hits": compliance_hits if isinstance(compliance_hits, list) else [],
            "llm_timeout_sec": llm_timeout_sec,
            "max_output_tokens_hint": max_output_tokens_hint,
            "requested_section_retry_limit": section_retry_limit,
            "runtime_budget_reason": runtime_budget_reason,
            "evolution_applied": evolution_applied,
            "evolution_reason": evolution_reason,
            "evolution_source_runs": evolution_source_runs,
            "qingtian_policy_enabled": qingtian_policy_enabled,
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
            rec.setdefault("used_key_alias", ctx.get("used_key_alias"))
            rec.setdefault("chapter_domain", dom)
            rec.setdefault("requested_section_retry_limit", ctx.get("requested_section_retry_limit"))
            rec.setdefault("runtime_budget_reason", ctx.get("runtime_budget_reason"))
            rec.setdefault("evolution_applied", bool(ctx.get("evolution_applied", False)))
            rec.setdefault("evolution_reason", ctx.get("evolution_reason"))
            rec.setdefault("evolution_source_runs", ctx.get("evolution_source_runs"))
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
        cache_key = ""
        if bool(payload.get("enable_section_cache", False)):
            cache_key = _section_cache_key(
                {
                    "project_id": project_id,
                    "topic": topic,
                    "title": title,
                    "provider_chain": provider_chain if provider_chain else providers or [provider],
                    "mode_effective": mode_effective,
                    # Cache should be reusable across repeated runs even if variant_id rotates (A/B/C/D/E cycle).
                    # Keep logic template identity for content-shape separation.
                    "template_id": str((ctx.get("logic_template") or {}).get("id") or ""),
                    "logic_template": ctx.get("logic_template"),
                    "req_digest": hashlib.sha1(
                        "\n".join([str(x) for x in section_requirements]).encode("utf-8", errors="ignore")
                    ).hexdigest(),
                    "kg_digest": hashlib.sha1("\n".join(kg_evidence).encode("utf-8", errors="ignore")).hexdigest(),
                    "doc_digest": hashlib.sha1("\n".join(doc_evidence).encode("utf-8", errors="ignore")).hexdigest(),
                    "length": {
                        "min": section_min_length,
                        "max": section_max_length,
                        "target": target_chars,
                    },
                }
            )
            hit = _load_section_cache(cache_key, workspace_dir=workspace_dir)
            if isinstance(hit, dict) and str(hit.get("content") or "").strip():
                hit = _attach_section_meta(hit)
                if isinstance(hit, dict):
                    hit["cache_hit"] = True
                    return hit
        for attempt_idx, (p, m, key_override, slot_id, key_alias_hint) in enumerate(tries, start=1):
            resolved_key, resolved_key_alias = _resolve_provider_credentials(
                payload,
                p,
                slot_id=slot_id,
                explicit_key=key_override,
                explicit_alias=key_alias_hint,
            )
            _trace_runtime(
                payload,
                "section_provider_attempt",
                title=title,
                attempt=f"{attempt_idx}/{len(tries)}",
                provider=p,
                model=m,
                slot=slot_id or "",
                used_key_alias=resolved_key_alias or "",
                llm_timeout_sec=str(llm_timeout_sec),
                max_output_tokens_hint=str(max_output_tokens_hint or ""),
                chapter_target_pages=str(chapter_target_pages or ""),
                section_retry_limit=str(section_retry_limit),
                runtime_budget_reason=runtime_budget_reason,
                evolution_applied=str(evolution_applied),
                evolution_reason=evolution_reason,
                evolution_source_runs=str(evolution_source_runs),
            )
            llm = None
            if p and m and not dry_run:
                try:
                    llm = LLMClient(
                        provider=p,
                        model=m,
                        api_key=resolved_key,
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
                            "used_key_alias": resolved_key_alias,
                            "error": f"provider_init_failed: {e}",
                        }
                    )
                    _trace_runtime(
                        payload,
                        "provider_init_failed",
                        title=title,
                        provider=p,
                        model=m,
                        slot=slot_id or "",
                        used_key_alias=resolved_key_alias or "",
                        error=repr(e),
                    )
                    continue
            ctx["task_type"] = "section_generation"
            ctx["used_key_alias"] = resolved_key_alias or ""
            writer = SectionWriter(llm=llm)
            try:
                last = _attach_section_meta(
                    await writer.write(
                        title,
                        ctx,
                        min_length=section_min_length,
                        max_length=section_max_length,
                        max_retry=section_retry_limit,
                    )
                )
            except Exception as e:
                last = _attach_section_meta(
                    {
                        "title": title,
                        "content": "",
                        "provider": p,
                        "model": m,
                        "used_key_alias": resolved_key_alias,
                        "error": f"section_write_failed: {e}",
                    }
                )
                _trace_runtime(
                    payload,
                    "section_write_failed",
                    title=title,
                    provider=p,
                    model=m,
                    slot=slot_id or "",
                    used_key_alias=resolved_key_alias or "",
                    error=repr(e),
                )
                continue
            if last and not last.get("error"):
                _trace_runtime(
                    payload,
                    "section_write_ok",
                    title=title,
                    provider=p,
                    model=m,
                    slot=slot_id or "",
                    used_key_alias=resolved_key_alias or "",
                    latency=str(last.get("latency_ms") or ""),
                    cache_hit=str(last.get("cache_hit") or ""),
                    requested_timeout_sec=str(last.get("requested_timeout_sec") or ""),
                    requested_max_output_tokens=str(last.get("requested_max_output_tokens") or ""),
                    requested_section_retry_limit=str(last.get("requested_section_retry_limit") or section_retry_limit),
                    runtime_budget_reason=str(last.get("runtime_budget_reason") or runtime_budget_reason),
                    evolution_applied=str(last.get("evolution_applied") or evolution_applied),
                    evolution_reason=str(last.get("evolution_reason") or evolution_reason),
                    evolution_source_runs=str(last.get("evolution_source_runs") or evolution_source_runs),
                )
                if cache_key:
                    _save_section_cache(cache_key, last, workspace_dir=workspace_dir)
                return last
            err_text = str((last or {}).get("error") or "").lower()
            if "429" in err_text or "quota" in err_text or "resource_exhausted" in err_text:
                await asyncio.sleep(min(8.0, 0.8 * (2 ** max(0, attempt_idx - 1))) + random.random() * 0.4)
        if last:
            _trace_runtime(
                payload,
                "section_write_exhausted",
                title=title,
                error=str(last.get("error") or ""),
            )
            return last
        return _attach_section_meta({"title": title, "content": "章节生成失败"}) or {"title": title, "content": "章节生成失败"}

    async def _build_section_with_limit(idx: int, title: str):
        async with section_sem:
            return await build_section(idx, title)

    sections = await asyncio.gather(*[_build_section_with_limit(i, t) for i, t in enumerate(outline)])
    for sec in sections:
        sec["content"] = strip_nonconcrete_language(sec.get("content") or "")
    evolution_applied_count = sum(1 for sec in sections if isinstance(sec, dict) and bool(sec.get("evolution_applied")))
    pipeline_stages: List[Dict[str, Any]] = [
        {
            "stage": "self_evolution_runtime_budget",
            "ok": True,
            "enabled": bool(((params or {}).get("self_evolution") or {}).get("enabled", True)),
            "applied_count": int(evolution_applied_count),
        },
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
                audit_path=workspace_paths(workspace_dir)["ingest_audit"] if workspace_dir else None,
            )
            evidence_src = str((hit or {}).get("locator") or "工程量清单(解析统计)")
        if (not evidence_src or "@" not in evidence_src or "#" not in evidence_src) and isinstance(tender, dict):
            hit = best_tender_source_span_hit(
                tender,
                "工程量清单 报价 清单 招标要求",
                prefer_filename_keywords=["招标", "清单", "BOQ", "工程量"],
            )
            evidence_src = str((hit or {}).get("locator") or evidence_src or "工程量清单(解析统计)")
        ensure_boq_focus_item_cards(
            sections,
            boq_focus,
            evidence_src=evidence_src,
            params=params,
            project_id=project_id,
            boq_data=boq,
            workspace_dir=workspace_dir,
        )
    except Exception:
        pass

    media = []
    if generate_images:
        stats = boq.get("stats") if isinstance(boq, dict) else None
        if stats:
            media.extend(generate_boq_chart(stats, workspace_dir=workspace_dir))
        # Drawings/attachments previews from ingested docs
        media.extend(generate_ingested_previews(limit=6, project_id=project_id, workspace_dir=workspace_dir))
        # Mindmap (prefer Gemini "banana" image model when key is configured)
        try:
            img_defaults = get_image_defaults(params)
            aspect_ratio = (payload.get("image_aspect_ratio") or img_defaults.get("aspect_ratio") or "16:9").strip()

            # Resolve bidder logo once; embed it into DOCX and pass into mindmap generation if possible.
            if logo_embed:
                media.append({"path": logo_embed, "caption": "投标单位LOGO"})

            mm = None
            for image_slot in iterate_image_failover_slots():
                if image_slot.provider != "google":
                    continue
                mm = generate_outline_mindmap(
                    topic,
                    outline,
                    api_key=image_slot.api_key,
                    model=image_slot.model,
                    aspect_ratio=aspect_ratio,
                    logo_path=logo_embed,
                    bidder_company=payload.get("bidder_company"),
                    logo_url=payload.get("logo_url"),
                    bidder_domain=payload.get("bidder_domain"),
                    workspace_dir=workspace_dir,
                )
                if mm:
                    _trace_runtime(
                        payload,
                        "image_generation_ok",
                        provider=image_slot.provider,
                        model=image_slot.model,
                        used_key_alias=image_slot.key_alias,
                    )
                    media.append(mm)
                    break
        except Exception:
            pass

    remediation_combo_learning_summary: Dict[str, Any] = {
        "enabled": True,
        "applied_count": 0,
        "source_runs": 0,
        "titles": [],
        "reasons": [],
        "combos": [],
    }
    remediation_combo_bundle_learning_summary: Dict[str, Any] = {
        "enabled": True,
        "applied_count": 0,
        "source_runs": 0,
        "titles": [],
        "reasons": [],
        "bundles": [],
    }
    remediation_context_bundle_learning_summary: Dict[str, Any] = {
        "enabled": True,
        "applied_count": 0,
        "source_runs": 0,
        "titles": [],
        "contexts": [],
        "reasons": [],
        "bundles": [],
        "effect_applied_count": 0,
        "effect_source_runs": 0,
        "effect_titles": [],
        "effect_reasons": [],
        "effect_bundles": [],
        "details": [],
        "metric_effect_applied_count": 0,
        "metric_effect_source_runs": 0,
        "metric_effect_titles": [],
        "metric_effect_metrics": [],
        "metric_effect_reasons": [],
        "metric_effect_bundles": [],
        "metric_details": [],
        "metric_action_effect_applied_count": 0,
        "metric_action_effect_source_runs": 0,
        "metric_action_effect_titles": [],
        "metric_action_effect_triplets": [],
        "metric_action_effect_reasons": [],
        "metric_action_effect_bundles": [],
        "metric_action_details": [],
    }

    def _record_remediation_combo_learning(rows: List[Dict[str, Any]], *, stage_name: str, round_no: int | None = None) -> None:
        learning_applied_count = sum(
            1 for row in rows if isinstance(row, dict) and bool(row.get("_combo_learning_applied"))
        )
        if learning_applied_count <= 0:
            return
        reasons = [
            str(row.get("_combo_learning_reason") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("_combo_learning_reason") or "").strip()
        ]
        combos = [
            str(row.get("_combo_learning_best_combo") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("_combo_learning_best_combo") or "").strip()
        ]
        titles = [
            str(row.get("target_section_title") or row.get("title") or "").strip()
            for row in rows
            if isinstance(row, dict)
            and bool(row.get("_combo_learning_applied"))
            and str(row.get("target_section_title") or row.get("title") or "").strip()
        ]
        source_runs = max(
            [
                int(row.get("_combo_learning_source_runs") or 0)
                for row in rows
                if isinstance(row, dict)
            ]
            or [0]
        )
        remediation_combo_learning_summary["applied_count"] = int(remediation_combo_learning_summary.get("applied_count") or 0) + learning_applied_count
        remediation_combo_learning_summary["source_runs"] = max(int(remediation_combo_learning_summary.get("source_runs") or 0), source_runs)
        remediation_combo_learning_summary["titles"] = sorted(
            set(list(remediation_combo_learning_summary.get("titles") or []) + titles)
        )[:8]
        remediation_combo_learning_summary["reasons"] = list(
            dict.fromkeys(list(remediation_combo_learning_summary.get("reasons") or []) + reasons)
        )[:8]
        remediation_combo_learning_summary["combos"] = list(
            dict.fromkeys(list(remediation_combo_learning_summary.get("combos") or []) + combos)
        )[:8]
        stage_row = {
            "stage": stage_name,
            "ok": True,
            "applied_count": learning_applied_count,
            "source_runs": source_runs,
            "title_count": len(titles),
        }
        if round_no is not None:
            stage_row["round"] = int(round_no)
        pipeline_stages.append(stage_row)

    def _record_remediation_combo_bundle_learning(rows: List[Dict[str, Any]], *, stage_name: str, round_no: int | None = None) -> None:
        learning_applied_count = sum(
            1 for row in rows if isinstance(row, dict) and bool(row.get("_combo_bundle_learning_applied"))
        )
        if learning_applied_count <= 0:
            return
        reasons = [
            str(row.get("_combo_bundle_learning_reason") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("_combo_bundle_learning_reason") or "").strip()
        ]
        bundles = [
            str(row.get("_combo_bundle_learning_best_bundle") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("_combo_bundle_learning_best_bundle") or "").strip()
        ]
        titles = [
            str(row.get("target_section_title") or row.get("title") or "").strip()
            for row in rows
            if isinstance(row, dict)
            and bool(row.get("_combo_bundle_learning_applied"))
            and str(row.get("target_section_title") or row.get("title") or "").strip()
        ]
        source_runs = max(
            [
                int(row.get("_combo_bundle_learning_source_runs") or 0)
                for row in rows
                if isinstance(row, dict)
            ]
            or [0]
        )
        remediation_combo_bundle_learning_summary["applied_count"] = int(remediation_combo_bundle_learning_summary.get("applied_count") or 0) + learning_applied_count
        remediation_combo_bundle_learning_summary["source_runs"] = max(int(remediation_combo_bundle_learning_summary.get("source_runs") or 0), source_runs)
        remediation_combo_bundle_learning_summary["titles"] = sorted(
            set(list(remediation_combo_bundle_learning_summary.get("titles") or []) + titles)
        )[:8]
        remediation_combo_bundle_learning_summary["reasons"] = list(
            dict.fromkeys(list(remediation_combo_bundle_learning_summary.get("reasons") or []) + reasons)
        )[:8]
        remediation_combo_bundle_learning_summary["bundles"] = list(
            dict.fromkeys(list(remediation_combo_bundle_learning_summary.get("bundles") or []) + bundles)
        )[:8]
        stage_row = {
            "stage": stage_name,
            "ok": True,
            "applied_count": learning_applied_count,
            "source_runs": source_runs,
            "title_count": len(titles),
        }
        if round_no is not None:
            stage_row["round"] = int(round_no)
        pipeline_stages.append(stage_row)

    def _record_remediation_context_bundle_learning(rows: List[Dict[str, Any]], *, stage_name: str, round_no: int | None = None) -> None:
        learning_applied_count = sum(
            1 for row in rows if isinstance(row, dict) and bool(row.get("_combo_context_bundle_learning_applied"))
        )
        if learning_applied_count <= 0:
            return
        reasons = [
            str(row.get("_combo_context_bundle_learning_reason") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("_combo_context_bundle_learning_reason") or "").strip()
        ]
        bundles = [
            str(row.get("_combo_context_bundle_learning_best_bundle") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("_combo_context_bundle_learning_best_bundle") or "").strip()
        ]
        titles = [
            str(row.get("target_section_title") or row.get("title") or "").strip()
            for row in rows
            if isinstance(row, dict)
            and bool(row.get("_combo_context_bundle_learning_applied"))
            and str(row.get("target_section_title") or row.get("title") or "").strip()
        ]
        contexts = []
        detail_map: Dict[tuple[str, str], Dict[str, Any]] = {}
        effect_applied_count = 0
        effect_reasons = []
        effect_bundles = []
        effect_titles = []
        effect_source_runs = 0
        for row in rows:
            if not isinstance(row, dict) or not bool(row.get("_combo_context_bundle_learning_applied")):
                continue
            reason = str(row.get("_combo_context_bundle_learning_reason") or "").strip()
            if "context=" not in reason:
                continue
            context_text = reason.split("context=", 1)[1].split(";", 1)[0].strip()
            if context_text:
                contexts.append(context_text)
            title = str(row.get("target_section_title") or row.get("title") or "").strip()
            context_bundle_id = str(row.get("_combo_context_bundle_learning_key") or "").strip()
            bundle_display = str(row.get("_combo_context_bundle_learning_best_bundle") or "").strip()
            context_signature = str(row.get("_combo_context_bundle_learning_context_signature") or "").strip()
            bundle_combos = [str(x).strip() for x in (row.get("_combo_context_bundle_learning_bundle_combos") or []) if str(x).strip()]
            attribution_applied = bool(row.get("_combo_context_bundle_learning_attribution_applied"))
            attribution_reason = str(row.get("_combo_context_bundle_learning_attribution_reason") or "").strip()
            attribution_source_runs = int(row.get("_combo_context_bundle_learning_attribution_source_runs") or 0)
            attributed_gate_pass_rate = float(row.get("_combo_context_bundle_learning_attributed_gate_pass_rate") or 0.0)
            if title and context_bundle_id:
                detail_key = (title, context_bundle_id)
                detail = detail_map.setdefault(
                    detail_key,
                    {
                        "title": title,
                        "context": context_text,
                        "context_signature": context_signature,
                        "context_bundle_id": context_bundle_id,
                        "bundle": bundle_display,
                        "bundle_combos": bundle_combos,
                        "source_runs": int(row.get("_combo_context_bundle_learning_source_runs") or 0),
                        "applied_count": 0,
                        "attribution_applied": False,
                        "attributed_gate_pass_rate": 0.0,
                        "attribution_runs": 0,
                        "attribution_reason": "",
                        "reasons": [],
                    },
                )
                detail["applied_count"] = int(detail.get("applied_count") or 0) + 1
                if reason and reason not in detail["reasons"]:
                    detail["reasons"].append(reason)
                if attribution_applied:
                    detail["attribution_applied"] = True
                    detail["attributed_gate_pass_rate"] = max(
                        float(detail.get("attributed_gate_pass_rate") or 0.0),
                        attributed_gate_pass_rate,
                    )
                    detail["attribution_runs"] = max(
                        int(detail.get("attribution_runs") or 0),
                        attribution_source_runs,
                    )
                    if attribution_reason:
                        detail["attribution_reason"] = attribution_reason
                    effect_applied_count += 1
                    effect_titles.append(title)
                    effect_source_runs = max(effect_source_runs, attribution_source_runs)
                    if attribution_reason:
                        effect_reasons.append(f"{title}: {attribution_reason}")
                    if bundle_display:
                        effect_bundles.append(bundle_display)
        source_runs = max(
            [
                int(row.get("_combo_context_bundle_learning_source_runs") or 0)
                for row in rows
                if isinstance(row, dict)
            ]
            or [0]
        )
        remediation_context_bundle_learning_summary["applied_count"] = int(remediation_context_bundle_learning_summary.get("applied_count") or 0) + learning_applied_count
        remediation_context_bundle_learning_summary["source_runs"] = max(int(remediation_context_bundle_learning_summary.get("source_runs") or 0), source_runs)
        remediation_context_bundle_learning_summary["titles"] = sorted(
            set(list(remediation_context_bundle_learning_summary.get("titles") or []) + titles)
        )[:8]
        remediation_context_bundle_learning_summary["contexts"] = sorted(
            set(list(remediation_context_bundle_learning_summary.get("contexts") or []) + contexts)
        )[:8]
        remediation_context_bundle_learning_summary["reasons"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("reasons") or []) + reasons)
        )[:8]
        remediation_context_bundle_learning_summary["bundles"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("bundles") or []) + bundles)
        )[:8]
        remediation_context_bundle_learning_summary["effect_applied_count"] = int(
            remediation_context_bundle_learning_summary.get("effect_applied_count") or 0
        ) + effect_applied_count
        remediation_context_bundle_learning_summary["effect_source_runs"] = max(
            int(remediation_context_bundle_learning_summary.get("effect_source_runs") or 0),
            effect_source_runs,
        )
        remediation_context_bundle_learning_summary["effect_titles"] = sorted(
            set(list(remediation_context_bundle_learning_summary.get("effect_titles") or []) + effect_titles)
        )[:8]
        remediation_context_bundle_learning_summary["effect_reasons"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("effect_reasons") or []) + effect_reasons)
        )[:8]
        remediation_context_bundle_learning_summary["effect_bundles"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("effect_bundles") or []) + effect_bundles)
        )[:8]
        existing_details = remediation_context_bundle_learning_summary.get("details") if isinstance(remediation_context_bundle_learning_summary.get("details"), list) else []
        merged_details = list(existing_details)
        for detail in detail_map.values():
            if detail not in merged_details:
                merged_details.append(detail)
        remediation_context_bundle_learning_summary["details"] = merged_details[:12]
        stage_row = {
            "stage": stage_name,
            "ok": True,
            "applied_count": learning_applied_count,
            "source_runs": source_runs,
            "title_count": len(titles),
            "context_count": len(contexts),
            "effect_applied_count": effect_applied_count,
        }
        if round_no is not None:
            stage_row["round"] = int(round_no)
        pipeline_stages.append(stage_row)

    def _record_remediation_context_metric_effect(
        rows: List[Dict[str, Any]],
        *,
        before_failed_metrics: set[str],
        after_failed_metrics: set[str],
        stage_name: str,
        round_no: int | None = None,
    ) -> None:
        if not before_failed_metrics:
            return
        applied_count = 0
        source_runs = 0
        titles: list[str] = []
        metrics: list[str] = []
        reasons: list[str] = []
        bundles: list[str] = []
        detail_rows: list[Dict[str, Any]] = []
        action_applied_count = 0
        action_titles: list[str] = []
        action_triplets: list[str] = []
        action_reasons: list[str] = []
        action_bundles: list[str] = []
        action_detail_rows: list[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict) or not bool(row.get("_combo_context_bundle_learning_applied")):
                continue
            expected_metrics = [
                str(x).strip()
                for x in (row.get("expected_quality_gate_metrics") or [])
                if str(x).strip()
            ]
            relevant_failed_metrics = sorted(set(expected_metrics).intersection(before_failed_metrics))
            if not relevant_failed_metrics:
                continue
            resolved_failed_metrics = [metric for metric in relevant_failed_metrics if metric not in after_failed_metrics]
            remaining_failed_metrics = [metric for metric in relevant_failed_metrics if metric in after_failed_metrics]
            title = str(row.get("target_section_title") or row.get("title") or "").strip()
            bundle_display = str(row.get("_combo_context_bundle_learning_best_bundle") or "").strip()
            context_signature = str(row.get("_combo_context_bundle_learning_context_signature") or "").strip()
            context_bundle_id = str(row.get("_combo_context_bundle_learning_key") or "").strip()
            source_runs = max(
                source_runs,
                int(row.get("_combo_context_metric_effect_source_runs") or 0),
                int(row.get("_combo_context_bundle_learning_source_runs") or 0),
            )
            effect_reason = str(row.get("_combo_context_metric_effect_reason") or "").strip()
            learning_reason = str(row.get("_combo_context_bundle_learning_reason") or "").strip()
            action_effect_reason = str(row.get("_combo_context_metric_action_effect_reason") or "").strip()
            action_effect_details = (
                row.get("_combo_context_metric_action_effect_details")
                if isinstance(row.get("_combo_context_metric_action_effect_details"), list)
                else []
            )
            for metric_name in relevant_failed_metrics:
                metric_label = str(QUALITY_GATE_METRIC_LABELS.get(metric_name) or metric_name).strip()
                metric_resolved = metric_name in resolved_failed_metrics
                matched_action_details = [
                    detail
                    for detail in action_effect_details
                    if isinstance(detail, dict) and str(detail.get("metric") or "").strip() == metric_name
                ]
                action_tags = [
                    str(detail.get("action_tag") or "").strip()
                    for detail in matched_action_details
                    if str(detail.get("action_tag") or "").strip()
                ]
                if not action_tags:
                    action_tags = [
                        str(x).strip()
                        for x in (row.get("expected_action_tags") or [])
                        if str(x).strip()
                    ]
                action_labels = []
                if matched_action_details:
                    action_labels = [
                        str(detail.get("action_label") or ACTION_TAG_LABELS.get(str(detail.get("action_tag") or "").strip()) or str(detail.get("action_tag") or "").strip()).strip()
                        for detail in matched_action_details
                        if str(detail.get("action_tag") or "").strip()
                    ]
                if not action_labels:
                    action_labels = [
                        str(ACTION_TAG_LABELS.get(tag) or tag).strip()
                        for tag in action_tags
                        if str(tag).strip()
                    ]
                detail = {
                    "title": title,
                    "context_signature": context_signature,
                    "context_bundle_id": context_bundle_id,
                    "bundle": bundle_display,
                    "metric": metric_name,
                    "metric_label": metric_label,
                    "metric_resolved": metric_resolved,
                    "candidate_failed_metrics": relevant_failed_metrics,
                    "resolved_failed_metrics": resolved_failed_metrics,
                    "remaining_failed_metrics": remaining_failed_metrics,
                    "source_runs": int(row.get("_combo_context_bundle_learning_source_runs") or 0),
                    "attribution_runs": int(row.get("_combo_context_metric_effect_source_runs") or 0),
                    "action_tags": action_tags,
                    "action_labels": action_labels,
                    "metric_action_triplets": [
                        f"{metric_label}/{label}" for label in action_labels if str(label).strip()
                    ],
                    "reason": effect_reason or learning_reason,
                    "display": f"{metric_label} | {bundle_display}".strip(" |"),
                }
                detail_rows.append(detail)
                if not metric_resolved:
                    continue
                applied_count += 1
                if title:
                    titles.append(title)
                metrics.append(metric_label)
                if bundle_display:
                    bundles.append(bundle_display)
                reason_text = f"{title or '章节'}: {metric_label}已拉平"
                if effect_reason:
                    reason_text += f"; {effect_reason}"
                elif learning_reason:
                    reason_text += f"; {learning_reason}"
                reasons.append(reason_text)
                action_iter = matched_action_details or [
                    {"action_tag": tag, "action_label": ACTION_TAG_LABELS.get(tag) or tag}
                    for tag in action_tags
                    if str(tag).strip()
                ]
                for action_detail in action_iter:
                    action_tag = str(action_detail.get("action_tag") or "").strip()
                    action_label = str(action_detail.get("action_label") or ACTION_TAG_LABELS.get(action_tag) or action_tag).strip()
                    if not action_tag or not action_label:
                        continue
                    action_applied_count += 1
                    if title:
                        action_titles.append(title)
                    triplet_label = f"{metric_label}/{action_label}"
                    action_triplets.append(triplet_label)
                    if bundle_display:
                        action_bundles.append(bundle_display)
                    action_reason_text = f"{title or '章节'}: {triplet_label}已拉平"
                    if action_effect_reason:
                        action_reason_text += f"; {action_effect_reason}"
                    elif effect_reason:
                        action_reason_text += f"; {effect_reason}"
                    elif learning_reason:
                        action_reason_text += f"; {learning_reason}"
                    action_reasons.append(action_reason_text)
                    action_detail_rows.append(
                        {
                            "title": title,
                            "context_signature": context_signature,
                            "context_bundle_id": context_bundle_id,
                            "bundle": bundle_display,
                            "metric": metric_name,
                            "metric_label": metric_label,
                            "action_tag": action_tag,
                            "action_label": action_label,
                            "metric_action_triplet": triplet_label,
                            "metric_resolved": metric_resolved,
                            "candidate_failed_metrics": relevant_failed_metrics,
                            "resolved_failed_metrics": resolved_failed_metrics,
                            "remaining_failed_metrics": remaining_failed_metrics,
                            "source_runs": int(row.get("_combo_context_bundle_learning_source_runs") or 0),
                            "attribution_runs": max(
                                int(row.get("_combo_context_metric_action_effect_source_runs") or 0),
                                int(row.get("_combo_context_metric_effect_source_runs") or 0),
                            ),
                            "reason": action_effect_reason or effect_reason or learning_reason,
                        }
                    )
        if applied_count <= 0 and not detail_rows:
            return
        remediation_context_bundle_learning_summary["metric_effect_applied_count"] = int(
            remediation_context_bundle_learning_summary.get("metric_effect_applied_count") or 0
        ) + applied_count
        remediation_context_bundle_learning_summary["metric_effect_source_runs"] = max(
            int(remediation_context_bundle_learning_summary.get("metric_effect_source_runs") or 0),
            source_runs,
        )
        remediation_context_bundle_learning_summary["metric_effect_titles"] = sorted(
            set(list(remediation_context_bundle_learning_summary.get("metric_effect_titles") or []) + titles)
        )[:8]
        remediation_context_bundle_learning_summary["metric_effect_metrics"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("metric_effect_metrics") or []) + metrics)
        )[:8]
        remediation_context_bundle_learning_summary["metric_effect_reasons"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("metric_effect_reasons") or []) + reasons)
        )[:8]
        remediation_context_bundle_learning_summary["metric_effect_bundles"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("metric_effect_bundles") or []) + bundles)
        )[:8]
        existing_details = remediation_context_bundle_learning_summary.get("metric_details") if isinstance(remediation_context_bundle_learning_summary.get("metric_details"), list) else []
        merged_details = list(existing_details)
        for detail in detail_rows:
            if detail not in merged_details:
                merged_details.append(detail)
        remediation_context_bundle_learning_summary["metric_details"] = merged_details[:16]
        remediation_context_bundle_learning_summary["metric_action_effect_applied_count"] = int(
            remediation_context_bundle_learning_summary.get("metric_action_effect_applied_count") or 0
        ) + action_applied_count
        remediation_context_bundle_learning_summary["metric_action_effect_source_runs"] = max(
            int(remediation_context_bundle_learning_summary.get("metric_action_effect_source_runs") or 0),
            source_runs,
        )
        remediation_context_bundle_learning_summary["metric_action_effect_titles"] = sorted(
            set(list(remediation_context_bundle_learning_summary.get("metric_action_effect_titles") or []) + action_titles)
        )[:8]
        remediation_context_bundle_learning_summary["metric_action_effect_triplets"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("metric_action_effect_triplets") or []) + action_triplets)
        )[:10]
        remediation_context_bundle_learning_summary["metric_action_effect_reasons"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("metric_action_effect_reasons") or []) + action_reasons)
        )[:10]
        remediation_context_bundle_learning_summary["metric_action_effect_bundles"] = list(
            dict.fromkeys(list(remediation_context_bundle_learning_summary.get("metric_action_effect_bundles") or []) + action_bundles)
        )[:8]
        existing_action_details = remediation_context_bundle_learning_summary.get("metric_action_details") if isinstance(remediation_context_bundle_learning_summary.get("metric_action_details"), list) else []
        merged_action_details = list(existing_action_details)
        for detail in action_detail_rows:
            if detail not in merged_action_details:
                merged_action_details.append(detail)
        remediation_context_bundle_learning_summary["metric_action_details"] = merged_action_details[:20]
        stage_row = {
            "stage": stage_name,
            "ok": applied_count > 0,
            "applied_count": applied_count,
            "source_runs": source_runs,
            "metric_count": len(set(metrics)),
            "metric_action_count": len(set(action_triplets)),
        }
        if round_no is not None:
            stage_row["round"] = int(round_no)
        pipeline_stages.append(stage_row)

    quality: Dict[str, Any] = {}
    quality_draft: Dict[str, Any] | None = None
    quality_gate_thresholds = payload.get("quality_gate_thresholds") if isinstance(payload.get("quality_gate_thresholds"), dict) else None
    draft_quality_gate: Dict[str, Any] | None = None
    if payload.get("auto_remediate", True):
        if draft_quality_mode == "light":
            quality_draft = _run_light_quality_draft(
                tender=tender if isinstance(tender, dict) else {},
                outline=[str(x).strip() for x in (outline or []) if str(x).strip()],
                sections=sections,
            )
        else:
            quality_draft = run_quality_checks(
                tender,
                outline,
                sections,
                boq=boq,
                boq_focus=boq_focus,
                project_id=project_id,
                strict=strict_quality,
                workspace_dir=workspace_dir,
            )
        draft_score = _quality_score(quality_draft)
        if isinstance(quality_draft, dict):
            quality_draft.setdefault("score", draft_score)
        pipeline_stages.append(
            {
                "stage": "quality_draft",
                "mode": draft_quality_mode,
                "ok": bool(draft_score >= 60) if isinstance(quality_draft, dict) else True,
                "score": draft_score if isinstance(quality_draft, dict) else None,
            }
        )
        remediation_strategy_audit_draft = (
            quality_draft.get("remediation_strategy_audit") if isinstance(quality_draft.get("remediation_strategy_audit"), dict) else {}
        )
        if remediation_strategy_audit_draft:
            pipeline_stages.append(
                {
                    "stage": "remediation_strategy_mapping_draft",
                    "ok": True,
                    "indicator_group_count": len(remediation_strategy_audit_draft.get("indicator_groups") or []),
                    "strategy_count": len(remediation_strategy_audit_draft.get("strategies") or []),
                    "mapping_row_count": len(remediation_strategy_audit_draft.get("mapping_rows") or []),
                }
            )
        draft_recs = quality_draft.get("remediation") if isinstance(quality_draft.get("remediation"), list) else []
        if draft_recs:
            sec_by_title: Dict[str, Dict[str, Any]] = {}
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                title = str(sec.get("title") or "").strip()
                if title:
                    sec_by_title.setdefault(title, sec)
            draft_rows = enrich_strategy_rows(draft_recs, sec_by_title=sec_by_title)
            draft_rows = _attach_remediation_target_section_titles(draft_rows, sections)
            draft_learning_hint = prioritize_remediation_rows_with_learning(
                params=params,
                project_type=project_type,
                generation_mode=str(payload.get("generation_mode") or ""),
                rows=draft_rows,
                profile=self_evolution_profile,
            )
            quality_draft["remediation"] = (
                draft_learning_hint.get("rows")
                if isinstance(draft_learning_hint.get("rows"), list)
                else draft_rows
            )
            _record_remediation_combo_learning(
                quality_draft.get("remediation") if isinstance(quality_draft.get("remediation"), list) else [],
                stage_name="remediation_combo_learning_draft",
            )
            _record_remediation_context_bundle_learning(
                quality_draft.get("remediation") if isinstance(quality_draft.get("remediation"), list) else [],
                stage_name="remediation_context_bundle_learning_draft",
            )
            _record_remediation_combo_bundle_learning(
                quality_draft.get("remediation") if isinstance(quality_draft.get("remediation"), list) else [],
                stage_name="remediation_combo_bundle_learning_draft",
            )
        try:
            draft_evidence_tracking = build_evidence_tracking(
                sections=sections,
                tender=tender if isinstance(tender, dict) else {},
                chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
            )
        except Exception:
            draft_evidence_tracking = {"rows": [], "summary": {}}
        draft_quality_gate = _build_hard_quality_gate(
            quality=quality_draft if isinstance(quality_draft, dict) else {},
            evidence_tracking=draft_evidence_tracking if isinstance(draft_evidence_tracking, dict) else {},
            sections=sections,
            thresholds=quality_gate_thresholds,
        )
        pipeline_stages.append(
            {
                "stage": "quality_gate_draft",
                "ok": bool(draft_quality_gate.get("ok", False)),
                "failed_count": len(draft_quality_gate.get("failed") or []),
                "mode": draft_quality_mode,
            }
        )
        remediate_mode = payload.get("remediate_mode") or "template"

        async def _remediate_with_llm(sec: Dict[str, Any], recs: List[Dict[str, Any]]):
            if not recs:
                return
            llm = None
            auto_provider, auto_model, auto_key = resolve_automation_credentials()
            runtime_provider = auto_provider or provider
            runtime_model = auto_model or model
            runtime_key = auto_key or _resolve_provider_api_key(payload, provider)
            if runtime_provider and runtime_model and runtime_key and not dry_run:
                try:
                    llm = LLMClient(
                        provider=runtime_provider,
                        model=runtime_model,
                        api_key=runtime_key,
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
            resp = await llm.complete(
                prompt,
                temperature=0.0,
                used_key_alias="OPENAI_API_KEY_AUTOMATION" if auto_key else "",
                client_request_id=f"zhifei-remediate-{int(time.time())}",
            )
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
                tender=tender if isinstance(tender, dict) else None,
                project_id=project_id,
                boq_focus=boq_focus,
                params=params,
                workspace_dir=workspace_dir,
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

        drawing_index = build_drawing_index(
            topic,
            outline,
            project_id=str(project_id) if project_id else None,
            workspace_dir=workspace_dir,
        )
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

        standard_index = build_standard_index(
            topic,
            outline,
            project_id=str(project_id) if project_id else None,
            workspace_dir=workspace_dir,
        )
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

    traceability_patch = {"fixed": 0, "skipped": 0, "failed": 0}
    try:
        traceability_patch = _ensure_traceable_evidence_per_section(
            sections=sections,
            project_id=str(project_id) if project_id else "",
            topic=str(topic or ""),
            workspace_dir=workspace_dir,
        )
    except Exception:
        traceability_patch = {"fixed": 0, "skipped": 0, "failed": 0}
    pipeline_stages.append(
        {
            "stage": "traceability_patch",
            "ok": int(traceability_patch.get("failed") or 0) == 0,
            "fixed": int(traceability_patch.get("fixed") or 0),
            "skipped": int(traceability_patch.get("skipped") or 0),
            "failed": int(traceability_patch.get("failed") or 0),
        }
    )
    final_length_pass = _apply_final_length_bounds(sections, chapter_length_limits)
    pipeline_stages.append(
        {
            "stage": "final_length_clamp",
            "ok": int(final_length_pass.get("failed") or 0) == 0,
            "trimmed": int(final_length_pass.get("trimmed") or 0),
            "skipped": int(final_length_pass.get("skipped") or 0),
            "failed": int(final_length_pass.get("failed") or 0),
        }
    )

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
        workspace_dir=workspace_dir,
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
    final_score = _quality_score(quality)
    quality.setdefault("score", final_score)
    remediation_strategy_audit = quality.get("remediation_strategy_audit") if isinstance(quality.get("remediation_strategy_audit"), dict) else {}
    remediation_execution_audit = quality.get("remediation_execution_audit") if isinstance(quality.get("remediation_execution_audit"), dict) else {}
    pipeline_stages.append(
        {
            "stage": "quality_final",
            "ok": bool(final_score >= 60) and bool(contract_checks.get("ok", True)),
            "score": final_score,
            "contract_ok": bool(contract_checks.get("ok", True)),
        }
    )
    if remediation_strategy_audit:
        pipeline_stages.append(
            {
                "stage": "remediation_strategy_mapping_final",
                "ok": True,
                "indicator_group_count": len(remediation_strategy_audit.get("indicator_groups") or []),
                "strategy_count": len(remediation_strategy_audit.get("strategies") or []),
                "mapping_row_count": len(remediation_strategy_audit.get("mapping_rows") or []),
            }
        )
    if remediation_execution_audit:
        pipeline_stages.append(
            {
                "stage": "remediation_execution_profile_final",
                "ok": True,
                "trace_count": int(remediation_execution_audit.get("trace_count") or 0),
                "action_tag_count": len(remediation_execution_audit.get("action_tags") or []),
                "strategy_count": len(remediation_execution_audit.get("strategies") or []),
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
        param_receipt_path = save_latest_receipt(
            param_receipt,
            project_id=str(project_id) if project_id else None,
            workspace_dir=workspace_dir,
        )
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
    quality_gate = _build_hard_quality_gate(
        quality=quality if isinstance(quality, dict) else {},
        evidence_tracking=evidence_tracking if isinstance(evidence_tracking, dict) else {},
        sections=sections,
        thresholds=quality_gate_thresholds,
    )
    quality_gate_retry_rounds = 0
    pipeline_stages.append(
        {
            "stage": "quality_gate",
            "ok": bool(quality_gate.get("ok", False)),
            "failed_count": len(quality_gate.get("failed") or []),
            "mode": mode_effective,
        }
    )
    draft_metric_candidates = _failed_gate_metrics(draft_quality_gate)
    if not draft_metric_candidates and isinstance(quality_draft, dict):
        draft_metric_candidates = _candidate_failed_metrics_from_rows(
            quality_draft.get("remediation") if isinstance(quality_draft.get("remediation"), list) else [],
        )
    _record_remediation_context_metric_effect(
        quality_draft.get("remediation") if isinstance(quality_draft, dict) and isinstance(quality_draft.get("remediation"), list) else [],
        before_failed_metrics=draft_metric_candidates,
        after_failed_metrics=_failed_gate_metrics(quality_gate),
        stage_name="remediation_context_metric_effect_final",
    )
    try:
        max_gate_retry_rounds = int(payload.get("quality_gate_retry_rounds") or 0)
    except Exception:
        max_gate_retry_rounds = 0
    max_gate_retry_rounds = max(0, min(2, max_gate_retry_rounds))
    if payload.get("auto_remediate", True) and (not quality_gate.get("ok")) and max_gate_retry_rounds > 0:
        while quality_gate_retry_rounds < max_gate_retry_rounds and not quality_gate.get("ok"):
            before_retry_failed_metrics = _failed_gate_metrics(quality_gate)
            gate_recs = _collect_gate_remediation(
                quality=quality if isinstance(quality, dict) else {},
                sections=sections,
                failed=quality_gate.get("failed") if isinstance(quality_gate.get("failed"), list) else [],
                params=params,
                project_type=project_type,
                generation_mode=str(payload.get("generation_mode") or ""),
                runtime_budget_profile=self_evolution_profile,
            )
            if not gate_recs:
                break
            _record_remediation_combo_learning(
                gate_recs,
                stage_name="remediation_combo_learning_retry",
                round_no=quality_gate_retry_rounds + 1,
            )
            _record_remediation_context_bundle_learning(
                gate_recs,
                stage_name="remediation_context_bundle_learning_retry",
                round_no=quality_gate_retry_rounds + 1,
            )
            _record_remediation_combo_bundle_learning(
                gate_recs,
                stage_name="remediation_combo_bundle_learning_retry",
                round_no=quality_gate_retry_rounds + 1,
            )
            apply_remediation(
                sections,
                gate_recs,
                tender=tender if isinstance(tender, dict) else None,
                project_id=project_id,
                boq_focus=boq_focus,
                params=params,
                workspace_dir=workspace_dir,
            )
            for sec in sections:
                if isinstance(sec, dict):
                    sec["content"] = strip_nonconcrete_language(sec.get("content") or "")
            try:
                _ensure_traceable_evidence_per_section(
                    sections=sections,
                    project_id=str(project_id) if project_id else "",
                    topic=str(topic or ""),
                    workspace_dir=workspace_dir,
                )
            except Exception:
                pass
            final_length_retry = _apply_final_length_bounds(sections, chapter_length_limits)
            pipeline_stages.append(
                {
                    "stage": "final_length_clamp_retry",
                    "round": quality_gate_retry_rounds + 1,
                    "ok": int(final_length_retry.get("failed") or 0) == 0,
                    "trimmed": int(final_length_retry.get("trimmed") or 0),
                    "failed": int(final_length_retry.get("failed") or 0),
                }
            )

            quality = run_quality_checks(
                tender,
                outline,
                sections,
                boq=boq,
                boq_focus=boq_focus,
                project_id=project_id,
                strict=strict_quality,
                workspace_dir=workspace_dir,
            )
            contract_checks = _run_contract_checks(sections)
            quality["agent_contract"] = contract_checks
            quality["score"] = _quality_score(quality)
            try:
                evidence_tracking = build_evidence_tracking(
                    sections=sections,
                    tender=tender if isinstance(tender, dict) else {},
                    chapter_pages=chapter_pages if isinstance(chapter_pages, dict) else {},
                )
            except Exception:
                evidence_tracking = {"rows": [], "summary": {}}
            quality_gate = _build_hard_quality_gate(
                quality=quality if isinstance(quality, dict) else {},
                evidence_tracking=evidence_tracking if isinstance(evidence_tracking, dict) else {},
                sections=sections,
                thresholds=quality_gate_thresholds,
            )
            quality_gate_retry_rounds += 1
            pipeline_stages.append(
                {
                    "stage": "quality_gate_retry",
                    "round": quality_gate_retry_rounds,
                    "ok": bool(quality_gate.get("ok", False)),
                    "failed_count": len(quality_gate.get("failed") or []),
                }
            )
            _record_remediation_context_metric_effect(
                gate_recs,
                before_failed_metrics=before_retry_failed_metrics,
                after_failed_metrics=_failed_gate_metrics(quality_gate),
                stage_name="remediation_context_metric_effect_retry",
                round_no=quality_gate_retry_rounds,
            )
            if quality_gate.get("ok"):
                break

    # After quality-gate retry, refresh score mapping and cross-index so exports follow final text.
    score_mapping = build_score_mapping(tender=tender if isinstance(tender, dict) else {}, sections=sections)
    if quality_gate_retry_rounds > 0:
        pipeline_stages.append(
            {
                "stage": "score_mapping_refresh",
                "ok": bool(score_mapping.get("ok", False)),
                "high_risk_item_count": (
                    (score_mapping.get("summary") or {}).get("high_risk_item_count")
                    if isinstance(score_mapping, dict)
                    else None
                ),
            }
        )
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
        pass

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
    request_id = str(payload.get("request_id") or "").strip()
    trace_id = str(payload.get("trace_id") or request_id).strip()
    provider_chain_summary = []
    for entry in provider_chain if isinstance(provider_chain, list) else []:
        if not isinstance(entry, dict):
            continue
        provider_chain_summary.append(
            {
                "slot": str(entry.get("slot") or "").strip(),
                "provider": str(entry.get("provider") or "").strip(),
                "model": str(entry.get("model") or "").strip(),
                "key_alias": str(entry.get("key_alias") or "").strip(),
            }
        )
    resource_usage_summary = summarize_sections(sections)
    resource_usage_summary["variant_id"] = variant_index
    resource_usage_summary["request_id"] = request_id
    resource_usage_summary["trace_id"] = trace_id
    resource_usage_summary["project_id"] = str(project_id or "")
    resource_usage_summary["topic"] = str(topic or "")
    resource_usage_summary["session_id"] = str(session_id or "")
    resource_usage_summary["workspace_dir"] = str(workspace_dir or "")
    llm_usage_events = build_llm_usage_events(
        sections,
        session_id=session_id,
        workspace_dir=workspace_dir,
        user_id=payload.get("user_id"),
        job_id=payload.get("_job_id") or payload.get("job_id"),
        request_id=request_id,
        trace_id=trace_id,
        project_id=project_id,
        topic=topic,
        variant_id=variant_index,
    )
    if llm_usage_events:
        append_resource_events(llm_usage_events, workspace_dir=workspace_dir)
    generation_trace = {
        "request_id": request_id,
        "trace_id": trace_id,
        "topic": str(topic or ""),
        "project_id": str(project_id or ""),
        "project_name": str(project_name or ""),
        "project_code": str(project_code or ""),
        "generation_mode": str(payload.get("generation_mode") or ""),
        "strict_catalog_mode": bool(strict_tender_outline),
        "provider_chain": provider_chain_summary,
        "retrieval_cache": shared_cache_obj.get("stats") if isinstance(shared_cache_obj, dict) else {},
        "pipeline_stages": pipeline_stages,
        "terminology_audit": {
            "ok": bool(terminology_audit.get("ok", True)),
            "changed_sections": int(terminology_audit.get("changed_sections") or 0),
            "replacement_count": int(terminology_audit.get("replacement_count") or 0),
        },
        "quality_gate": {
            "ok": bool(quality_gate.get("ok", False)),
            "failed_count": len(quality_gate.get("failed") or []) if isinstance(quality_gate.get("failed"), list) else 0,
            "retry_rounds": int(quality_gate_retry_rounds or 0),
        },
        "remediation_strategy_audit": remediation_strategy_audit if isinstance(remediation_strategy_audit, dict) else {},
        "remediation_execution_audit": remediation_execution_audit if isinstance(remediation_execution_audit, dict) else {},
        "self_evolution": {
            "enabled": bool(((params or {}).get("self_evolution") or {}).get("enabled", True)),
            "applied_count": int(evolution_applied_count),
            "applied_titles": [
                str(sec.get("title") or "").strip()
                for sec in sections
                if isinstance(sec, dict) and bool(sec.get("evolution_applied"))
            ][:8],
            "remediation_combo_learning_applied_count": int(remediation_combo_learning_summary.get("applied_count") or 0),
            "remediation_combo_learning_source_runs": int(remediation_combo_learning_summary.get("source_runs") or 0),
            "remediation_combo_learning_titles": [
                str(x).strip()
                for x in (remediation_combo_learning_summary.get("titles") or [])
                if str(x).strip()
            ][:8],
            "remediation_combo_learning_reasons": [
                str(x).strip()
                for x in (remediation_combo_learning_summary.get("reasons") or [])
                if str(x).strip()
            ][:8],
            "remediation_combo_learning_combos": [
                str(x).strip()
                for x in (remediation_combo_learning_summary.get("combos") or [])
                if str(x).strip()
            ][:8],
            "remediation_combo_bundle_learning_applied_count": int(remediation_combo_bundle_learning_summary.get("applied_count") or 0),
            "remediation_combo_bundle_learning_source_runs": int(remediation_combo_bundle_learning_summary.get("source_runs") or 0),
            "remediation_combo_bundle_learning_titles": [
                str(x).strip()
                for x in (remediation_combo_bundle_learning_summary.get("titles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_applied_count": int(remediation_context_bundle_learning_summary.get("applied_count") or 0),
            "remediation_context_bundle_learning_source_runs": int(remediation_context_bundle_learning_summary.get("source_runs") or 0),
            "remediation_context_bundle_learning_titles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("titles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_contexts": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("contexts") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_reasons": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("reasons") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_bundles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("bundles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_effect_applied_count": int(remediation_context_bundle_learning_summary.get("effect_applied_count") or 0),
            "remediation_context_bundle_learning_effect_source_runs": int(remediation_context_bundle_learning_summary.get("effect_source_runs") or 0),
            "remediation_context_bundle_learning_effect_titles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("effect_titles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_effect_reasons": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("effect_reasons") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_effect_bundles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("effect_bundles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_details": [
                detail
                for detail in (remediation_context_bundle_learning_summary.get("details") or [])
                if isinstance(detail, dict)
            ][:12],
            "remediation_context_bundle_learning_metric_effect_applied_count": int(remediation_context_bundle_learning_summary.get("metric_effect_applied_count") or 0),
            "remediation_context_bundle_learning_metric_effect_source_runs": int(remediation_context_bundle_learning_summary.get("metric_effect_source_runs") or 0),
            "remediation_context_bundle_learning_metric_effect_titles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_effect_titles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_metric_effect_metrics": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_effect_metrics") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_metric_effect_reasons": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_effect_reasons") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_metric_effect_bundles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_effect_bundles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_metric_details": [
                detail
                for detail in (remediation_context_bundle_learning_summary.get("metric_details") or [])
                if isinstance(detail, dict)
            ][:16],
            "remediation_context_bundle_learning_metric_action_effect_applied_count": int(remediation_context_bundle_learning_summary.get("metric_action_effect_applied_count") or 0),
            "remediation_context_bundle_learning_metric_action_effect_source_runs": int(remediation_context_bundle_learning_summary.get("metric_action_effect_source_runs") or 0),
            "remediation_context_bundle_learning_metric_action_effect_titles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_action_effect_titles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_metric_action_effect_triplets": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_action_effect_triplets") or [])
                if str(x).strip()
            ][:10],
            "remediation_context_bundle_learning_metric_action_effect_reasons": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_action_effect_reasons") or [])
                if str(x).strip()
            ][:10],
            "remediation_context_bundle_learning_metric_action_effect_bundles": [
                str(x).strip()
                for x in (remediation_context_bundle_learning_summary.get("metric_action_effect_bundles") or [])
                if str(x).strip()
            ][:8],
            "remediation_context_bundle_learning_metric_action_details": [
                detail
                for detail in (remediation_context_bundle_learning_summary.get("metric_action_details") or [])
                if isinstance(detail, dict)
            ][:20],
            "remediation_combo_bundle_learning_reasons": [
                str(x).strip()
                for x in (remediation_combo_bundle_learning_summary.get("reasons") or [])
                if str(x).strip()
            ][:8],
            "remediation_combo_bundle_learning_bundles": [
                str(x).strip()
                for x in (remediation_combo_bundle_learning_summary.get("bundles") or [])
                if str(x).strip()
            ][:8],
        },
        "front_matter_sequence": [str(x).strip() for x in (front_matter_outline.get("sequence") or []) if str(x).strip()],
        "chapter_count": len(sections),
        "outline_count": len(outline),
        "version_mode": str(raw_variant_id or ""),
        "resource_usage_summary": resource_usage_summary,
    }
    return {
        "topic": topic,
        "project_id": project_id,
        "session_id": session_id,
        "workspace_dir": workspace_dir,
        "project_name": project_name,
        "project_code": project_code,
        "generation_mode": payload.get("generation_mode"),
        "mode_policy": payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else None,
        "draft_quality_mode": draft_quality_mode,
        "project_type": project_type,
        "global_instruction": effective_global_instruction,
        "qingtian_policy": qingtian_receipt if isinstance(qingtian_receipt, dict) else {"enabled": False},
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
        "front_matter_outline": front_matter_outline if isinstance(front_matter_outline, dict) else {},
        "chapter_length_limits": chapter_length_limits,
        "total_pages_target": user_total_pages_target,
        "total_pages_limit": total_pages_limit,
        "style": style,
        "bidding_format_config": bidding_format_config,
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
        "quality_gate": quality_gate,
        "quality_gate_retry_rounds": quality_gate_retry_rounds,
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
        "retrieval_cache": shared_cache_obj.get("stats") if isinstance(shared_cache_obj, dict) else {},
        "speed_profile": speed_profile,
        "pipeline_stages": pipeline_stages,
        "generation_trace": generation_trace,
        "resource_usage_summary": resource_usage_summary,
        "params_used": params_used,
    }
