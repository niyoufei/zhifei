from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.self_healing_agent import SelfHealingAgent


@pytest.mark.asyncio
async def test_self_healing_agent_fallback_build_and_persist(tmp_path: Path) -> None:
    gaps = [
        {
            "type": "parameter_missing",
            "dimension": "质量",
            "required_keywords": ["质量", "验收", "强度"],
            "query": "质量 验收 强度",
        },
        {
            "type": "formula_missing",
            "dimension": "进度",
            "required_keywords": ["工期", "进度", "关键线路"],
            "query": "进度 工期 公式 计算",
        },
    ]
    agent = SelfHealingAgent(provider="unknown", model="none")
    built = await agent.build_patch_nodes(gaps)

    assert built["ok"] is True
    assert built["used_fallback"] is True
    assert len(built["nodes"]) == 2

    parameter_node = built["nodes"][0]
    formula_node = built["nodes"][1]

    assert parameter_node["is_auto_generated"] is True
    assert isinstance(parameter_node.get("reference_standard"), list)
    assert parameter_node["reference_standard"]
    assert isinstance(parameter_node.get("applicable_conditions"), dict)
    assert isinstance(parameter_node.get("resource_requirements"), dict)
    assert parameter_node.get("safety_level") in {"low", "medium", "high", "critical"}

    assert formula_node["node_type"] == "FormulaNode"
    assert formula_node["is_auto_generated"] is True
    assert str(formula_node.get("formula_expression") or "").strip()
    assert isinstance(formula_node.get("formula_variables"), list)
    assert formula_node["reference_standard"]

    graph_root = tmp_path / "kg"
    graph_root.mkdir(parents=True, exist_ok=True)
    persisted = agent.persist_patch_nodes(graph_root=graph_root, nodes=built["nodes"])
    assert persisted["ok"] is True
    assert persisted["node_count"] == 2

    patch_file = Path(str(persisted["saved_at"]))
    assert patch_file.exists()
    payload = json.loads(patch_file.read_text(encoding="utf-8"))
    nodes = (
        payload.get("knowledge_database", {})
        .get("core", {})
        .get("nodes", [])
    )
    assert len(nodes) == 2
    assert all(bool(node.get("is_auto_generated")) for node in nodes)
    assert all(bool(node.get("reference_standard")) for node in nodes)
