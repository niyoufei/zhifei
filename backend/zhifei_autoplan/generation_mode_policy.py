from __future__ import annotations

from typing import Any, Dict, List


GENERATION_MODE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "standard_auto",
        "profile": "standard_auto",
        "label": "Standard Auto",
        "legacy": False,
        "stable_output": False,
        "description": "Default mode that uses quality_200 or hq_speed_500 based on planned total pages.",
    },
    {
        "id": "quality_200",
        "profile": "standard_auto",
        "label": "Quality 200",
        "legacy": True,
        "stable_output": False,
        "description": "Legacy alias that prefers high quality under 200 planned pages and auto-switches above that.",
    },
    {
        "id": "hq_speed_500",
        "profile": "standard_auto",
        "label": "HQ Speed 500",
        "legacy": True,
        "stable_output": False,
        "description": "Legacy alias for the large-document speed profile with stricter template remediation defaults.",
    },
    {
        "id": "speed_fast",
        "profile": "speed_fast",
        "label": "Speed Fast",
        "legacy": False,
        "stable_output": False,
        "description": "Fastest deterministic template-first mode with lower compare budget and no image generation.",
    },
    {
        "id": "pro_polish",
        "profile": "pro_polish",
        "label": "Pro Polish",
        "legacy": False,
        "stable_output": False,
        "description": "Higher-polish mode with stricter review retries and LLM remediation enabled.",
    },
    {
        "id": "stable_delivery",
        "profile": "stable_delivery",
        "label": "Stable Delivery",
        "legacy": False,
        "stable_output": True,
        "description": "Deterministic delivery mode that fixes variant/template selection when the request leaves them unspecified.",
    },
)


def _to_positive_int(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except Exception:
        return None


def normalize_logic_template_id(raw: Any) -> str | None:
    s = str(raw or "").strip().upper()
    if not s:
        return None
    if s in {"A", "B", "C", "D", "E"}:
        return s
    alias = {
        "TEMPLATE_A": "A",
        "TEMPLATE_B": "B",
        "TEMPLATE_C": "C",
        "TEMPLATE_D": "D",
        "TEMPLATE_E": "E",
        "方案A": "A",
        "方案B": "B",
        "方案C": "C",
        "方案D": "D",
        "方案E": "E",
        "S": "C",
        "方案S": "C",
        "TEMPLATE_S": "C",
    }
    return alias.get(s)


def normalize_selected_templates(raw: Any) -> List[str]:
    arr = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
    out: List[str] = []
    seen = set()
    for x in arr:
        tid = normalize_logic_template_id(x)
        if not tid or tid in seen:
            continue
        seen.add(tid)
        out.append(tid)
        if len(out) >= 5:
            break
    return out


def page_target_value(v: Any) -> int | None:
    if isinstance(v, dict):
        v = v.get("target") or v.get("pages") or v.get("page_target") or v.get("count")
    return _to_positive_int(v)


def planned_total_pages(payload: dict) -> int:
    hard = _to_positive_int(payload.get("total_pages_target"))
    if hard:
        return int(hard)
    chapter_pages = payload.get("chapter_pages") if isinstance(payload.get("chapter_pages"), dict) else {}
    if not chapter_pages:
        return 0
    s = 0
    for _, raw in chapter_pages.items():
        n = page_target_value(raw)
        if n:
            s += int(n)
    return int(s)


def generation_mode_catalog() -> List[Dict[str, Any]]:
    return [dict(item) for item in GENERATION_MODE_CATALOG]


def normalize_generation_mode_profile(raw: str | None) -> tuple[str, str | None]:
    mode = str(raw or "").strip()
    for item in GENERATION_MODE_CATALOG:
        if mode != item["id"]:
            continue
        profile = str(item.get("profile") or "standard_auto").strip() or "standard_auto"
        if bool(item.get("legacy")):
            return profile, str(item["id"])
        return profile, None
    return "standard_auto", None


def apply_generation_mode_policy(payload: dict) -> dict:
    mode_profile, legacy_mode = normalize_generation_mode_profile(payload.get("generation_mode"))
    pages = planned_total_pages(payload)
    existing_mode_policy = payload.get("_mode_policy") if isinstance(payload.get("_mode_policy"), dict) else {}
    auto_switched = False
    if legacy_mode == "hq_speed_500":
        mode_effective = "hq_speed_500"
    elif legacy_mode == "quality_200":
        mode_effective = "hq_speed_500" if pages > 200 else "quality_200"
        auto_switched = pages > 200
    elif mode_profile == "speed_fast":
        mode_effective = "speed_fast"
    elif mode_profile == "stable_delivery":
        mode_effective = "stable_delivery"
    elif mode_profile == "pro_polish":
        mode_effective = "pro_polish"
    else:
        mode_effective = "hq_speed_500" if pages > 200 else "quality_200"
        auto_switched = pages > 200

    explicit_template_id = normalize_logic_template_id(payload.get("logic_template_id") or payload.get("logic_template"))
    explicit_selected_templates = normalize_selected_templates(payload.get("selected_templates"))
    explicit_variant_id = _to_positive_int(payload.get("variant_id"))
    try:
        variants_requested = int(payload.get("variants") or 1)
    except Exception:
        variants_requested = 1
    variants_requested = max(1, min(5, variants_requested))
    stable_variant_forced = bool(existing_mode_policy.get("deterministic_variant_forced", False))
    deterministic_logic_template_id = str(
        existing_mode_policy.get("deterministic_logic_template_id")
        or payload.get("logic_template_id")
        or ""
    ).strip() or None
    if (
        mode_profile == "stable_delivery"
        and not explicit_template_id
        and not explicit_selected_templates
        and not explicit_variant_id
        and variants_requested == 1
    ):
        payload["variant_id"] = 1
        payload["logic_template_id"] = "A"
        stable_variant_forced = True

    if mode_effective == "quality_200":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 1
        if str(payload.get("remediate_mode") or "").strip() not in {"template", "llm"}:
            payload["remediate_mode"] = "template"
        ap = _to_positive_int(payload.get("agent_parallelism")) or 4
        payload["agent_parallelism"] = max(1, min(16, int(ap)))
    elif mode_effective == "hq_speed_500":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["remediate_mode"] = "template"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 1
        ap = _to_positive_int(payload.get("agent_parallelism")) or 6
        payload["agent_parallelism"] = max(6, min(16, int(ap)))
        vp = _to_positive_int(payload.get("variant_parallelism")) or 1
        payload["variant_parallelism"] = max(1, min(5, int(vp)))
        if payload.get("generate_images") is None:
            payload["generate_images"] = False
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 800
    elif mode_effective == "speed_fast":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["remediate_mode"] = "template"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 0
        ap = _to_positive_int(payload.get("agent_parallelism")) or 8
        payload["agent_parallelism"] = max(8, min(16, int(ap)))
        vp = _to_positive_int(payload.get("variant_parallelism")) or 1
        payload["variant_parallelism"] = max(1, min(5, int(vp)))
        if payload.get("generate_images") is None:
            payload["generate_images"] = False
        else:
            payload["generate_images"] = False
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 600
    elif mode_effective == "pro_polish":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        payload["remediate_mode"] = "llm"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 2
        ap = _to_positive_int(payload.get("agent_parallelism")) or 3
        payload["agent_parallelism"] = max(1, min(4, int(ap)))
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 1600
    elif mode_effective == "stable_delivery":
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 1
        if str(payload.get("remediate_mode") or "").strip() not in {"template", "llm"}:
            payload["remediate_mode"] = "template"
        else:
            payload["remediate_mode"] = "template"
        ap = _to_positive_int(payload.get("agent_parallelism")) or 2
        payload["agent_parallelism"] = max(1, min(3, int(ap)))
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 1600
    else:
        payload["quality_strict"] = True
        payload["auto_remediate"] = True
        payload["variant_parallelism"] = 1
        payload["remediate_mode"] = "llm"
        if payload.get("enable_section_cache") is None:
            payload["enable_section_cache"] = True
        if payload.get("quality_gate_retry_rounds") is None:
            payload["quality_gate_retry_rounds"] = 2
        ap = _to_positive_int(payload.get("agent_parallelism")) or 3
        payload["agent_parallelism"] = max(1, min(4, int(ap)))
        if payload.get("compare_max_chars") is None:
            payload["compare_max_chars"] = 1600

    style = payload.get("style") if isinstance(payload.get("style"), dict) else {}
    chart_policy = style.get("chart_policy") if isinstance(style.get("chart_policy"), dict) else {}
    if mode_effective in {"quality_200", "pro_polish", "stable_delivery"}:
        chart_policy.setdefault("enabled", True)
        chart_policy.setdefault("mode", "page_density_auto")
        chart_policy.setdefault("position", "chapter")
    elif mode_effective in {"hq_speed_500", "speed_fast"}:
        chart_policy.setdefault("enabled", True)
        chart_policy.setdefault("mode", "page_density_auto")
        chart_policy.setdefault("position", "chapter")
        if "max_images_total" not in chart_policy:
            chart_policy["max_images_total"] = max(240, min(900, pages))
    if chart_policy:
        style["chart_policy"] = chart_policy
        payload["style"] = style

    degrade_plan = payload.get("_admission_degrade_plan") if isinstance(payload.get("_admission_degrade_plan"), dict) else {}
    if degrade_plan.get("applied"):
        degraded_ap = _to_positive_int(degrade_plan.get("agent_parallelism_after"))
        degraded_vp = _to_positive_int(degrade_plan.get("variant_parallelism_after"))
        if degraded_ap:
            payload["agent_parallelism"] = max(1, min(16, int(degraded_ap)))
        if degraded_vp:
            payload["variant_parallelism"] = max(1, min(5, int(degraded_vp)))

    payload["generation_mode"] = str(mode_effective if legacy_mode else mode_profile)
    payload["_mode_policy"] = {
        "profile": mode_profile,
        "mode_effective": mode_effective,
        "auto_switched": bool(auto_switched),
        "planned_total_pages": int(pages),
        "stable_output": mode_profile == "stable_delivery",
    }
    if stable_variant_forced:
        payload["_mode_policy"]["deterministic_variant_forced"] = True
        payload["_mode_policy"]["deterministic_logic_template_id"] = deterministic_logic_template_id or "A"
    if degrade_plan.get("applied"):
        payload["_mode_policy"]["admission_degrade_applied"] = True
        payload["_mode_policy"]["admission_degrade_reason"] = str(degrade_plan.get("reason") or "").strip()
        payload["_mode_policy"]["admission_degrade_warning_level"] = str(degrade_plan.get("warning_level") or "").strip()
    return payload
