from __future__ import annotations

import re
from typing import Any, Dict, List

ELEVATION_RE = re.compile(r"(?:标高|高程|EL)\s*(?:=|:|：)?\s*([-\d.]+)\s*m?", flags=re.IGNORECASE)
DURATION_RE = re.compile(r"(?:持续|工期)\s*(\d+)\s*天")
RESOURCE_RE = re.compile(r"(投入|配置)\s*(\d+)\s*(人|台|套)")


def _parse_elevations(text: str) -> List[float]:
    out: List[float] = []
    for m in ELEVATION_RE.finditer(text or ""):
        try:
            out.append(float(m.group(1)))
        except Exception:
            continue
    return out


def _parse_duration_days(text: str) -> List[int]:
    out: List[int] = []
    for m in DURATION_RE.finditer(text or ""):
        try:
            out.append(int(m.group(1)))
        except Exception:
            continue
    return out


def _parse_resources(text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in RESOURCE_RE.finditer(text or ""):
        out.append({"amount": int(m.group(2)), "unit": str(m.group(3)), "text": str(m.group(0))})
    return out


def solve_cross_discipline_constraints(
    *,
    sections: List[Dict[str, Any]],
    quant_index: Dict[str, Any] | None = None,
    chapter_response_plan: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    quant_index = quant_index or {}
    cpm = quant_index.get("cpm") if isinstance(quant_index.get("cpm"), dict) else {}
    cpm_duration = int(cpm.get("project_duration_days") or 0)

    conflicts: List[Dict[str, Any]] = []
    recommendations: List[str] = []
    elevations: List[Dict[str, Any]] = []
    durations: List[Dict[str, Any]] = []
    resource_sum: Dict[str, int] = {}

    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = str(sec.get("title") or "untitled")
        domain = str(sec.get("specialist_domain") or "general")
        text = str(sec.get("content") or "")
        for val in _parse_elevations(text):
            elevations.append({"title": title, "domain": domain, "value": val})
        for val in _parse_duration_days(text):
            durations.append({"title": title, "domain": domain, "days": val})
        for rec in _parse_resources(text):
            key = str(rec.get("unit") or "")
            resource_sum[key] = int(resource_sum.get(key) or 0) + int(rec.get("amount") or 0)

    if elevations:
        uniq = sorted({round(float(item["value"]), 4) for item in elevations})
        if len(uniq) > 1:
            conflicts.append(
                {
                    "type": "elevation_inconsistency",
                    "values": uniq,
                    "refs": elevations[:20],
                    "severity": "high",
                }
            )
            recommendations.append("统一标高/高程基准，按坐标控制网回写全部专业章节。")

    if cpm_duration > 0 and durations:
        vals = [int(item["days"]) for item in durations]
        max_day = max(vals)
        min_day = min(vals)
        if max_day > cpm_duration * 2 or min_day < max(1, cpm_duration // 3):
            conflicts.append(
                {
                    "type": "duration_vs_cpm_conflict",
                    "values": {"section_min": min_day, "section_max": max_day, "cpm_duration": cpm_duration},
                    "refs": durations[:20],
                    "severity": "high",
                }
            )
            recommendations.append("按CPM关键线路重新校正章节工期表达，保持与总工期一致。")

    if resource_sum:
        heavy = {k: v for k, v in resource_sum.items() if v > 200}
        if heavy:
            conflicts.append(
                {
                    "type": "resource_peak_conflict",
                    "values": heavy,
                    "refs": [{"unit": k, "amount": v} for k, v in heavy.items()],
                    "severity": "medium",
                }
            )
            recommendations.append("对峰值资源执行错峰与分仓调度，避免同窗口资源双占。")

    plan = chapter_response_plan if isinstance(chapter_response_plan, dict) else {}
    missing_plan = [
        x for x in (plan.get("chapters") or []) if isinstance(x, dict) and not bool(x.get("coverage_ok"))
    ]
    if missing_plan:
        conflicts.append(
            {
                "type": "chapter_response_plan_gap",
                "values": [str(x.get("chapter") or "") for x in missing_plan],
                "refs": missing_plan[:20],
                "severity": "medium",
            }
        )
        recommendations.append("先补齐评分点->章节->证据锚点映射，再进行段落生成。")

    return {
        "ok": len(conflicts) == 0,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "recommendations": recommendations,
        "cpm_duration_days": cpm_duration,
    }

