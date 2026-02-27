from __future__ import annotations

import re
from typing import Any, Dict, List


def _merge_text(*parts: Any) -> str:
    arr: List[str] = []
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
    except Exception:
        return False


def probe_missing_parameters(
    *,
    topic: str,
    outline: List[str],
    requirements: List[str],
    tender: Dict[str, Any],
    boq: Dict[str, Any],
    enterprise_profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a deterministic "missing parameter report" before writing sections.
    The pipeline can auto-fill with enterprise defaults while explicitly tagging the source.
    """
    txt = _merge_text(
        topic,
        outline,
        requirements,
        tender.get("global_requirements") if isinstance(tender, dict) else None,
        tender.get("style") if isinstance(tender, dict) else None,
        boq.get("stats") if isinstance(boq, dict) else None,
    )

    risk_defaults = enterprise_profile.get("risk_defaults") if isinstance(enterprise_profile.get("risk_defaults"), dict) else {}

    checks = [
        {
            "key": "总工期",
            "pattern": r"工期[^\d]{0,8}\d+(?:\.\d+)?\s*(天|日|月|h|小时)",
            "fallback": "120天",
            "reason": "进度统筹缺少可计算时长",
            "question": "请确认总工期（天）",
        },
        {
            "key": "资源峰值",
            "pattern": r"(?:资源峰值|高峰投入|人数峰值)[^\d]{0,8}\d+(?:\.\d+)?\s*(人|台|套)",
            "fallback": "80人",
            "reason": "资源均衡与现金流测算缺少峰值",
            "question": "请确认资源峰值（人/台）",
        },
        {
            "key": "关键线路间隔",
            "pattern": r"关键线路(?:间隔|步距)?[^\d]{0,8}\d+(?:\.\d+)?\s*(天|日|h|小时)",
            "fallback": "3天",
            "reason": "关键路径控制缺少节拍参数",
            "question": "请确认关键线路间隔（天）",
        },
        {
            "key": "风险检查频次",
            "pattern": r"频次[^\d]{0,8}\d+(?:\.\d+)?\s*(次/日|次/班|次/周|次)",
            "fallback": str(risk_defaults.get("frequency") or "2次/日"),
            "reason": "风险闭环缺少可执行检查频次",
            "question": "请确认风险检查频次",
        },
        {
            "key": "质量阈值",
            "pattern": r"(?:阈值|偏差|合格率)[^\d]{0,8}(?:≤|>=|≥|<|>)?\s*\d+(?:\.\d+)?\s*(mm|%|MPa)?",
            "fallback": str(risk_defaults.get("threshold") or "偏差≤5mm"),
            "reason": "验收判定缺少阈值",
            "question": "请确认质量阈值",
        },
        {
            "key": "偏差处置时限",
            "pattern": r"(?:偏差处置|整改|复验|复核).{0,10}(?:\d+(?:\.\d+)?\s*(h|小时|天)|时限)",
            "fallback": str(risk_defaults.get("deviation_action") or "偏差处置时限≤4h"),
            "reason": "闭环缺少时限约束",
            "question": "请确认偏差处置时限",
        },
    ]

    missing: List[Dict[str, Any]] = []
    auto_fill: Dict[str, str] = {}
    for c in checks:
        if not _has_pattern(txt, str(c.get("pattern") or "")):
            key = str(c.get("key") or "参数")
            fb = str(c.get("fallback") or "")
            missing.append(
                {
                    "key": key,
                    "question": str(c.get("question") or ""),
                    "reason": str(c.get("reason") or ""),
                    "fallback": fb,
                    "source": "enterprise_default",
                }
            )
            if fb:
                auto_fill[key] = fb

    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "auto_fill": auto_fill,
    }
