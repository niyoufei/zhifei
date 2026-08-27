from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

FORMAL_ACCEPTED_STATUSES = frozenset({"verified", "derived", "approved"})


def _merge_text(*parts: Any) -> str:
    arr: list[str] = []
    for p in parts:
        if isinstance(p, str):
            arr.append(p)
        elif isinstance(p, list):
            for x in p:
                if isinstance(x, str):
                    arr.append(x)
                elif isinstance(x, dict):
                    arr.append(str(x))
        elif isinstance(p, dict):
            arr.append(str(p))
    return "\n".join(arr)


def _has_pattern(text: str, pattern: str) -> bool:
    try:
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    except re.error:
        return False


def _is_process_bound_quality_threshold(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    if str(value.get("mode") or "").strip().lower() != "process_bound":
        return False
    items = value.get("items")
    return isinstance(items, list) and bool(items) and all(
        isinstance(item, Mapping)
        and bool(str(item.get("process") or "").strip())
        and bool(str(item.get("metric") or "").strip())
        and bool(str(item.get("locator") or "").strip())
        for item in items
    )


def probe_missing_parameters(
    *,
    topic: str,
    outline: list[str],
    requirements: list[str],
    tender: dict[str, Any],
    boq: dict[str, Any],
    enterprise_profile: dict[str, Any],
    project_fact_ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build a deterministic formal-parameter readiness report before writing.

    Enterprise defaults are neither exposed nor returned through ``auto_fill``.
    A formal value must come from an approved/verified/derived ledger record;
    unresolved fields remain an explicit, value-free confirmation checklist.
    """
    txt = _merge_text(
        topic,
        outline,
        requirements,
        tender.get("global_requirements") if isinstance(tender, dict) else None,
        tender.get("style") if isinstance(tender, dict) else None,
        boq.get("stats") if isinstance(boq, dict) else None,
    )

    del enterprise_profile  # Defaults are not project evidence or safe proposals.

    checks = [
        {
            "field": "planned_duration_days",
            "key": "总工期",
            "pattern": r"工期[^\d]{0,8}\d+(?:\.\d+)?\s*(天|日|月|h|小时)",
            "reason": "进度统筹缺少可计算时长",
            "question": "请确认总工期（天）",
        },
        {
            "field": "resource_peak",
            "key": "资源峰值",
            "pattern": r"(?:资源峰值|高峰投入|人数峰值)[^\d]{0,8}\d+(?:\.\d+)?\s*(人|台|套)",
            "reason": "资源均衡与现金流测算缺少峰值",
            "question": "请确认资源峰值（人/台）",
        },
        {
            "field": "critical_interval_days",
            "key": "关键线路间隔",
            "pattern": r"关键线路(?:间隔|步距)?[^\d]{0,8}\d+(?:\.\d+)?\s*(天|日|h|小时)",
            "reason": "关键路径控制缺少节拍参数",
            "question": "请确认关键线路间隔（天）",
        },
        {
            "field": "risk_inspection_frequency",
            "key": "风险检查频次",
            "pattern": r"频次[^\d]{0,8}\d+(?:\.\d+)?\s*(次/日|次/班|次/周|次)",
            "reason": "风险闭环缺少可执行检查频次",
            "question": "请确认风险检查频次",
        },
        {
            "field": "quality_threshold",
            "key": "质量阈值",
            "pattern": r"(?:阈值|偏差|合格率)[^\d]{0,8}(?:≤|>=|≥|<|>)?\s*\d+(?:\.\d+)?\s*(mm|%|MPa)?",
            "reason": "验收判定缺少阈值",
            "question": "请确认质量阈值",
        },
        {
            "field": "deviation_action_deadline",
            "key": "偏差处置时限",
            "pattern": (
                r"(?:在监理人规定时间内按要求完成整改|"
                r"(?:偏差处置|整改|复验|复核).{0,10}"
                r"(?:\d+(?:\.\d+)?\s*(h|小时|天)|时限))"
            ),
            "reason": "闭环缺少时限约束",
            "question": "请确认偏差处置时限",
        },
    ]

    ledger = project_fact_ledger if isinstance(project_fact_ledger, Mapping) else {}
    facts = ledger.get("facts") if isinstance(ledger.get("facts"), Mapping) else {}
    resolved: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    provisional: list[dict[str, Any]] = []
    for c in checks:
        field = str(c.get("field") or "")
        key = str(c.get("key") or "参数")
        fact = facts.get(field) if isinstance(facts, Mapping) else None
        status = str(fact.get("status") or "") if isinstance(fact, Mapping) else ""
        value_is_usable = field != "quality_threshold" or (
            isinstance(fact, Mapping)
            and _is_process_bound_quality_threshold(fact.get("value"))
        )
        if (
            isinstance(fact, Mapping)
            and status in FORMAL_ACCEPTED_STATUSES
            and value_is_usable
        ):
            evidence = fact.get("evidence") if isinstance(fact.get("evidence"), Mapping) else {}
            resolved.append(
                {
                    "field": field,
                    "key": key,
                    "value": fact.get("value"),
                    "unit": str(fact.get("unit") or ""),
                    "status": status,
                    "source": str(fact.get("source_type") or ""),
                    "locator": str(evidence.get("locator") or ""),
                }
            )
            continue

        item = {
            "field": field,
            "key": key,
            "question": str(c.get("question") or ""),
            "reason": str(c.get("reason") or ""),
            "status": "missing",
            "source": "none",
            "proposed_value": None,
            "detected_unstructured": _has_pattern(txt, str(c.get("pattern") or "")),
            "usable_for_formal_delivery": False,
        }
        missing.append(item)

    return {
        "schema_version": "missing-parameter-probe-v2",
        "ok": len(missing) == 0,
        "formal_ready": len(missing) == 0,
        "accepted_statuses": sorted(FORMAL_ACCEPTED_STATUSES),
        "resolved": resolved,
        "missing": missing,
        "provisional": provisional,
        "blocked_fields": [str(item.get("field") or "") for item in missing],
        # Retained for backward-compatible consumers; fail-closed by design.
        "auto_fill": {},
    }
