from __future__ import annotations

from backend.zhifei_autoplan.agent_contract import build_agent_contract
from backend.zhifei_autoplan.multi_agent_runtime import build_multi_agent_plan


def test_agent_contract_carries_active_quality_roles(monkeypatch):
    from backend.zhifei_autoplan import multi_agent_runtime as mar

    monkeypatch.setattr(
        mar,
        "detect_specialty_dispatch",
        lambda **kwargs: {"selected_graphs": [], "missing_graphs": []},
    )
    monkeypatch.setattr(
        mar,
        "assign_specialties_to_outline",
        lambda outline, dispatch: {"道路施工方案": []},
    )
    plan = build_multi_agent_plan(topic="道路工程", outline=["道路施工方案"])

    contract = build_agent_contract(
        topic="道路工程",
        outline=["道路施工方案"],
        chapter_pages={},
        chapter_requirements={},
        multi_agent_summary=plan.summary(),
        chapter_specialties=plan.chapter_specialties,
    )

    assert contract["schema_version"] == "1.2"
    chapter = contract["chapters"][0]
    names = [x["name"] for x in chapter["agents"]["auxiliary"]]
    assert "证据溯源Agent" in names
    assert "清单响应Agent" in names
    assert "图纸接口Agent" in names
    assert "风险闭环Agent" in names
    assert "全篇一致性Agent" in names
    assert any(
        x.get("name") == "专业渲染Agent"
        for x in contract["global_agents"]["role_catalog"]
    )
