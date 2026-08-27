from __future__ import annotations

import re
from typing import Any

TRACE_LOC_RE = re.compile(r"#(?:p\d+_)?[0-9a-f]{6,}@\d+", re.IGNORECASE)


def build_agent_contract(
    *,
    topic: str,
    outline: list[str],
    chapter_pages: dict[str, Any] | None,
    chapter_requirements: dict[str, Any] | None,
    multi_agent_summary: dict[str, Any] | None,
    chapter_specialties: dict[str, list[dict[str, Any]]] | None,
    project_fact_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cp = chapter_pages if isinstance(chapter_pages, dict) else {}
    cr = chapter_requirements if isinstance(chapter_requirements, dict) else {}
    mas = multi_agent_summary if isinstance(multi_agent_summary, dict) else {}
    csp = chapter_specialties if isinstance(chapter_specialties, dict) else {}
    chapter_aux = mas.get("chapter_auxiliary_agents") if isinstance(mas.get("chapter_auxiliary_agents"), dict) else {}
    role_catalog = mas.get("agent_role_catalog") if isinstance(mas.get("agent_role_catalog"), list) else []

    chapters: list[dict[str, Any]] = []
    for i, t in enumerate([str(x).strip() for x in (outline or []) if str(x).strip()]):
        raw_page = cp.get(t)
        if isinstance(raw_page, dict):
            raw_page = raw_page.get("target") or raw_page.get("pages") or raw_page.get("page_target")
        try:
            page_target = int(raw_page) if raw_page is not None else None
        except (TypeError, ValueError, OverflowError):
            page_target = None

        req = cr.get(t)
        if isinstance(req, str):
            reqs = [req]
        elif isinstance(req, list):
            reqs = [str(x).strip() for x in req if str(x).strip()]
        elif isinstance(req, dict):
            reqs = [f"{k}:{v}" for k, v in req.items() if str(v).strip()]
        else:
            reqs = []

        specs = csp.get(t) if isinstance(csp.get(t), list) else []
        specialist_agents = []
        for s in specs:
            if not isinstance(s, dict):
                continue
            g = str(s.get("graph_name") or s.get("filename") or "").strip()
            if g:
                specialist_agents.append(f"专业Agent:{g}")
        if not specialist_agents:
            specialist_agents = ["专业Agent:通用施工"]
        auxiliary_agents = [
            dict(x)
            for x in (chapter_aux.get(t) or [])
            if isinstance(x, dict) and str(x.get("name") or "").strip()
        ]

        chapters.append(
            {
                "chapter_id": f"CH-{i + 1:03d}",
                "title": t,
                "page_target": page_target,
                "requirements": reqs,
                "agents": {
                    "master": str(mas.get("master_agent") or "主控Agent"),
                    "specialists": specialist_agents,
                    "auxiliary": auxiliary_agents,
                    "compliance": str(mas.get("compliance_agent") or "合规Agent"),
                },
                "required_outputs": {
                    "content": "non_empty",
                    "evidence_locator": ">=1",
                    "traceable_evidence": ">=1",
                    "risk_triplet": "recommended>=1",
                    "quant_metrics": "recommended>=3",
                },
            }
        )

    fact_ledger = project_fact_ledger if isinstance(project_fact_ledger, dict) else {}
    fact_rows = fact_ledger.get("facts") if isinstance(fact_ledger.get("facts"), dict) else {}
    fact_snapshot = {
        str(field): {
            "value": row.get("value"),
            "unit": row.get("unit") or "",
            "status": row.get("status"),
            "source_type": row.get("source_type"),
            "evidence": {
                "locator": row.get("evidence", {}).get("locator"),
                "evidence_digest": row.get("evidence", {}).get("evidence_digest"),
            }
            if isinstance(row.get("evidence"), dict)
            else {},
        }
        for field, row in fact_rows.items()
        if isinstance(row, dict)
    }

    return {
        "schema_version": "1.2",
        "topic": str(topic or ""),
        "project_fact_ledger": {
            "status": fact_ledger.get("status"),
            "ledger_digest": fact_ledger.get("ledger_digest"),
            "facts": fact_snapshot,
        },
        "global_agents": {
            "master": str(mas.get("master_agent") or "主控Agent"),
            "compliance": str(mas.get("compliance_agent") or "合规Agent"),
            "role_catalog": [dict(x) for x in role_catalog if isinstance(x, dict)],
        },
        "chapters": chapters,
    }


def _extract_evidence(content: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"【证据:([^】]{1,180})】", str(content or "")) if m.group(1).strip()]


def validate_section_with_contract(section: dict[str, Any], chapter_contract: dict[str, Any]) -> dict[str, Any]:
    content = str(section.get("content") or "")
    errors: list[str] = []
    warns: list[str] = []

    if not content.strip():
        errors.append("content_empty")

    evidence = _extract_evidence(content)
    traceable = [e for e in evidence if TRACE_LOC_RE.search(e or "")]

    if len(evidence) < 1:
        errors.append("evidence_locator_missing")
    if len(traceable) < 1:
        errors.append("traceable_evidence_missing")

    triplet_count = len(re.findall(r"风险[:：].{0,120}?(?:控制|措施)[:：].{0,120}?验证[:：]", content, flags=re.DOTALL))
    quant_count = 0
    for k in ("频次", "阈值", "间距", "厚度", "时长", "人数", "设备型号"):
        if k in content:
            quant_count += 1
    if triplet_count < 1:
        warns.append("risk_triplet_recommended")
    if quant_count < 3:
        warns.append("quant_metrics_recommended")

    return {
        "ok": len(errors) == 0,
        "chapter_id": chapter_contract.get("chapter_id"),
        "title": chapter_contract.get("title"),
        "errors": errors,
        "warnings": warns,
        "metrics": {
            "evidence_count": len(evidence),
            "traceable_evidence_count": len(traceable),
            "triplet_count": triplet_count,
            "quant_metric_count": quant_count,
        },
    }
