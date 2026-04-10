from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


PARAMS_PATH = Path("backend/data/autoplan/params.json")


def _default_params() -> Dict[str, Any]:
    return {
        "version": "builtin",
        "quant_defaults": {
            "频次": "2次/日（班前+收工）",
            "阈值": "偏差≤5mm",
            "间距": "1000mm",
            "厚度": "50mm",
            "时长": "4h/作业段",
            "人数": "8人/班",
            "设备型号": "20t挖机1台",
        },
        "boq_focus_card": {
            "采购比价": "≥3家/批次",
            "抽检频次": "每100m2 1次",
            "合格率阈值": "≥98%",
            "一次验收通过率": "≥95%",
            "台账抽查频次": "1次/周",
            "应急演练频次": "1次/季度",
        },
        # Quality/Safety/Environment defaults (editable). Use when tender/drawings do not specify explicit values.
        "qse_defaults": {
            "PM10阈值": "≤150ug/m3",
            "昼间噪声阈值": "≤70dB",
            "夜间噪声阈值": "≤55dB",
        },
        "image_defaults": {
            "provider": "google",
            "model": "gemini-2.5-flash-image",
            "aspect_ratio": "16:9",
        },
        # Multi-variant (A/B/C/D/E) anti-paraphrase gate (editable).
        # - chapter_threshold: flag a chapter when any pair >= threshold
        # - overall_threshold: fail gate when avg(max_pair_similarity) >= threshold
        "variant_diversity": {
            "chapter_threshold": 0.90,
            "overall_threshold": 0.85,
            "min_chars": 800,
            "ignore_title_keywords": ["封面", "目录", "投标函", "授权委托", "承诺书", "声明", "报价"],
            # Naturally similar chapters: do not fail the gate, but still report as relaxed_flagged.
            "relaxed_title_keywords": ["项目概况", "工程概况", "总体概述", "编制依据", "投标响应", "响应"],
            "relaxed_chapter_threshold": 0.97,
            "auto_fix_rounds": 1,
        },
        "self_evolution": {
            "enabled": True,
            "ignore_dry_run_learning": True,
            "runtime_profile_soft_limit": 160,
            "runtime_profile_stale_days": 21,
            "runtime_profile_min_runs_to_keep": 2,
            "min_runs_for_adjustment": 2,
            "max_timeout_delta_sec": 20,
            "max_token_delta": 600,
            "allow_retry_promotion": True,
            "quality_issue_rate_raise_retry": 0.50,
            "error_rate_raise_timeout": 0.35,
            "fallback_rate_raise_timeout": 0.35,
            "quality_issue_rate_raise_tokens": 0.50,
            "compaction_rate_trim_tokens": 0.50,
            "combo_learning_enabled": True,
            "combo_learning_min_runs": 2,
            "combo_learning_min_success_rate": 0.55,
            "combo_learning_gate_pass_bonus": 0.10,
            "combo_learning_max_priority_boost": 8,
            "combo_bundle_learning_enabled": True,
            "combo_bundle_min_runs": 2,
            "combo_bundle_min_pass_rate": 0.55,
            "combo_bundle_gate_pass_bonus": 0.10,
            "combo_bundle_max_priority_boost": 10,
            "combo_context_bundle_learning_enabled": True,
            "combo_context_bundle_min_runs": 2,
            "combo_context_bundle_min_pass_rate": 0.60,
            "combo_context_bundle_gate_pass_bonus": 0.12,
            "combo_context_bundle_max_priority_boost": 12,
            "combo_context_bundle_partial_match_enabled": True,
            "combo_context_bundle_partial_min_match_count": 2,
            "combo_context_bundle_partial_min_match_ratio": 0.50,
            "combo_context_bundle_partial_score_penalty": 0.08,
            "combo_context_metric_effect_enabled": True,
            "combo_context_metric_effect_min_runs": 2,
            "combo_context_metric_effect_resolve_bonus": 0.10,
            "combo_context_metric_action_effect_enabled": True,
            "combo_context_metric_action_effect_min_runs": 2,
            "combo_context_metric_action_effect_resolve_bonus": 0.08,
            "task_parallelism_enabled": True,
            "task_parallelism_min_runs": 2,
            "task_parallelism_max_delta": 2,
            "task_parallelism_error_rate_reduce": 0.35,
            "task_parallelism_fallback_rate_reduce": 0.40,
            "task_parallelism_quality_issue_rate_reduce": 0.50,
            "task_parallelism_profile_soft_limit": 96,
            "task_parallelism_profile_stale_days": 30,
            "task_parallelism_profile_min_runs_to_keep": 2,
        },
    }


def load_params() -> Dict[str, Any]:
    if not PARAMS_PATH.exists():
        return _default_params()
    try:
        data = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_params()
        merged = _default_params()
        merged.update(data)
        # Shallow merge nested dicts we care about.
        for k in ("quant_defaults", "boq_focus_card", "qse_defaults", "image_defaults", "variant_diversity", "self_evolution"):
            if isinstance(data.get(k), dict):
                merged[k] = {**(merged.get(k) or {}), **data.get(k)}
        return merged
    except Exception:
        return _default_params()


def save_params(update: Dict[str, Any], merge: bool = True) -> str:
    """
    Persist editable parameter registry.
    - merge=True: merge into existing params, preserving unknown keys.
    Returns the saved path.
    """
    base = load_params() if merge else _default_params()
    if not isinstance(update, dict):
        update = {}
    out = dict(base)
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = dict(out.get(k) or {})
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PARAMS_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(PARAMS_PATH)


def get_quant_defaults(params: Dict[str, Any] | None = None) -> Dict[str, str]:
    params = params if isinstance(params, dict) else load_params()
    q = params.get("quant_defaults") if isinstance(params.get("quant_defaults"), dict) else {}
    out = {}
    for k in ("频次", "阈值", "间距", "厚度", "时长", "人数", "设备型号"):
        v = q.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()
    # Ensure all keys exist.
    for k, v in _default_params()["quant_defaults"].items():
        out.setdefault(k, v)
    return out


def get_boq_focus_card_defaults(params: Dict[str, Any] | None = None) -> Dict[str, str]:
    params = params if isinstance(params, dict) else load_params()
    d = params.get("boq_focus_card") if isinstance(params.get("boq_focus_card"), dict) else {}
    out: Dict[str, str] = {}
    for k, v in d.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            out[k.strip()] = v.strip()
    for k, v in _default_params()["boq_focus_card"].items():
        out.setdefault(k, v)
    return out


def get_qse_defaults(params: Dict[str, Any] | None = None) -> Dict[str, str]:
    params = params if isinstance(params, dict) else load_params()
    d = params.get("qse_defaults") if isinstance(params.get("qse_defaults"), dict) else {}
    out: Dict[str, str] = {}
    for k, v in d.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            out[k.strip()] = v.strip()
    for k, v in _default_params()["qse_defaults"].items():
        out.setdefault(k, v)
    return out


def get_image_defaults(params: Dict[str, Any] | None = None) -> Dict[str, str]:
    params = params if isinstance(params, dict) else load_params()
    d = params.get("image_defaults") if isinstance(params.get("image_defaults"), dict) else {}
    out = {}
    for k in ("provider", "model", "aspect_ratio"):
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()
    for k, v in _default_params()["image_defaults"].items():
        out.setdefault(k, v)
    return out
