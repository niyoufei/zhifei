from __future__ import annotations

from backend.zhifei_autoplan.v2.cross_discipline_solver import solve_cross_discipline_constraints


def test_cross_discipline_solver_detects_conflicts() -> None:
    sections = [
        {"title": "土建", "specialist_domain": "building", "content": "标高=10.50m，持续3天，投入120人。"},
        {"title": "机电", "specialist_domain": "mep", "content": "标高=11.20m，持续20天，投入130人。"},
    ]
    quant = {"cpm": {"project_duration_days": 8}}
    plan = {"chapters": [{"chapter": "质量", "coverage_ok": False}]}
    out = solve_cross_discipline_constraints(sections=sections, quant_index=quant, chapter_response_plan=plan)
    assert out["ok"] is False
    assert int(out.get("conflict_count") or 0) >= 2
    types = {str(x.get("type") or "") for x in (out.get("conflicts") or [])}
    assert "elevation_inconsistency" in types
    assert "chapter_response_plan_gap" in types


def test_cross_discipline_solver_detects_interface_contract_conflicts() -> None:
    sections = [
        {
            "title": "土建",
            "specialist_domain": "building",
            "content": "标高=10.50m，持续8天，投入40人。",
            "graph_hit": {
                "cross_discipline_interface_contract": {
                    "enabled": True,
                    "interfaces": [{"with_domain": "mep", "severity": "high"}],
                    "conflict_graph": [{"from_domain": "building", "to_domain": "mep", "status": "open"}],
                }
            },
        }
    ]
    out = solve_cross_discipline_constraints(sections=sections, quant_index={}, chapter_response_plan={})
    assert out["ok"] is False
    types = {str(x.get("type") or "") for x in (out.get("conflicts") or [])}
    assert "interface_contract_conflict" in types
    assert "interface_domain_missing" in types
