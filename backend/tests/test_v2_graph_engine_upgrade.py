from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.data_graph_ingestion import (
    EDGE_CONFLICTS_WITH,
    EDGE_MITIGATES,
    EDGE_REQUIRES,
    evaluate_formula_nodes_in_graph,
    get_graph_edges,
    ingest_knowledge_graph,
    search_graph_index,
    validate_requires_edges,
)


def _write_upgrade_sample(root: Path) -> None:
    payload = {
        "name": "upgrade-sample",
        "knowledge_database": {
            "core": {
                "nodes": [
                    {
                        "node_id": "PROC-A-GB",
                        "name": "混凝土浇筑",
                        "object_key": "concrete_pour",
                        "source_hierarchy": "国标",
                        "applicable_conditions": {"climate": "冬季"},
                        "resource_requirements": {"crew": 8, "pump": 1},
                        "safety_level": "medium",
                        "requires": ["PROC-B"],
                        "mitigates": ["RISK-1"],
                        "conflicts_with": ["PROC-C"],
                    },
                    {
                        "node_id": "PROC-A-QA",
                        "name": "混凝土浇筑",
                        "object_key": "concrete_pour",
                        "source_hierarchy": "答疑文件",
                        "applicable_conditions": {"climate": "低温"},
                        "resource_requirements": {"crew": 10, "pump": 2},
                        "safety_level": "high",
                    },
                    {
                        "node_id": "PROC-B",
                        "name": "钢筋绑扎",
                        "source_hierarchy": "设计图纸",
                        "requires": ["PROC-D"],
                    },
                    {
                        "node_id": "PROC-C",
                        "name": "大体积混凝土",
                        "source_hierarchy": "行标",
                    },
                    {
                        "node_id": "PROC-D",
                        "name": "测量放线",
                        "source_hierarchy": "企标",
                    },
                    {
                        "node_id": "RISK-1",
                        "name": "坍塌风险",
                        "source_hierarchy": "国标",
                    },
                    {
                        "node_id": "FORM-1",
                        "name": "浇筑时长计算",
                        "node_type": "FormulaNode",
                        "object_key": "pour_duration",
                        "formula_expression": "volume / productivity",
                        "formula_variables": ["volume", "productivity"],
                        "source_hierarchy": "国标",
                        "applicable_conditions": {"geology": "软土"},
                        "resource_requirements": {"crew": 6},
                        "safety_level": "low",
                    },
                ]
            }
        },
    }
    (root / "upgrade.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_authority_resolution_and_property_expansion(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    _write_upgrade_sample(root)

    db_path = tmp_path / "kg.sqlite3"
    ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)

    full = search_graph_index(
        query="concrete_pour",
        db_path=db_path,
        resolve_authority=False,
        top_k=20,
    )
    assert full["total"] >= 2

    resolved = search_graph_index(
        query="concrete_pour",
        db_path=db_path,
        resolve_authority=True,
        top_k=20,
    )
    hits = [item for item in resolved["results"] if item.get("title") == "混凝土浇筑"]
    assert len(hits) == 1
    node = hits[0]
    assert node["source_hierarchy"] == "答疑文件"
    assert node["applicable_conditions"].get("climate") == "低温"
    assert node["resource_requirements"].get("crew") == 10
    assert node["safety_level"] == "high"
    assert node["authority_resolution"]["applied"] is True


def test_relational_edges_and_requires_closure(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    _write_upgrade_sample(root)

    db_path = tmp_path / "kg.sqlite3"
    ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)

    requires = get_graph_edges(edge_type=EDGE_REQUIRES, db_path=db_path)
    mitigates = get_graph_edges(edge_type=EDGE_MITIGATES, db_path=db_path)
    conflicts = get_graph_edges(edge_type=EDGE_CONFLICTS_WITH, db_path=db_path)

    assert requires["total"] >= 2
    assert mitigates["total"] >= 1
    assert conflicts["total"] >= 1

    closure = validate_requires_edges(db_path=db_path)
    assert closure["ok"] is True
    assert closure["cycle_count"] == 0


def test_formula_node_compute(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    _write_upgrade_sample(root)

    db_path = tmp_path / "kg.sqlite3"
    ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)

    computed = evaluate_formula_nodes_in_graph(
        query="浇筑时长计算",
        variables={"volume": 1200, "productivity": 300},
        db_path=db_path,
    )

    assert computed["total"] >= 1
    assert computed["results"][0]["node_type"] == "FormulaNode"
    assert computed["results"][0]["computed_result"] == 4
