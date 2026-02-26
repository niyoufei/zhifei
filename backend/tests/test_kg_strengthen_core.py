from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "scripts" / "strengthen_kg_core.py"
    spec = importlib.util.spec_from_file_location("strengthen_kg_core", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _formula_vars(expr: str) -> list[str]:
    tree = ast.parse(expr, mode="eval")
    return sorted(
        {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id not in {"max", "min", "abs", "round"}
        }
    )


def test_strengthen_file_repairs_core_fields(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-99-Railway-Test.json"
    data = {
        "name": "test",
        "meta": {"activation_key": "智飞工程"},
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "N1",
                        "name": "首节点",
                        "qt_tag": ["质量"],
                        "content": {"operation_desc_premium": {"desc": "注意质量，确保达标。"}},
                        "formula_expression": "hazard_count * risk_factor / max(inspection_frequency_per_shift, 1)",
                        "formula_variables": ["quantity", "productivity_per_day"],
                        "requires": [],
                        "mitigates": [],
                        "conflicts_with": [],
                        "reference_standard": ["GB 50300-2013 建筑工程施工质量验收统一标准"],
                    },
                    {
                        "node_id": "N2",
                        "name": "次节点",
                        "qt_tag": ["安全"],
                        "content": {},
                        "formula_expression": "",
                        "formula_variables": [],
                        "requires": [],
                    },
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod.strengthen_file(kg_file)
    assert row["changed"] is True

    out = json.loads(kg_file.read_text(encoding="utf-8"))
    nodes = out["knowledge_database"]["sec"]["nodes"]
    n1, n2 = nodes[0], nodes[1]

    assert n1["professional_domain"] == "railway"
    assert n2["professional_domain"] == "railway"

    assert isinstance(n1["language_guardrails"], dict) and n1["language_guardrails"]["enabled"] is True
    assert n1["response_assertions"] == ["must_have_action", "must_have_checker", "must_have_parameter"]
    assert isinstance(n1["dry_content_lock"], dict) and n1["dry_content_lock"]["enabled"] is True

    assert isinstance(n1["content"]["operation_desc_premium"]["bid_response_strategy"], dict)
    assert isinstance(n1["content"]["operation_desc_premium"]["competitor_shield"], dict)
    assert isinstance(n1["content"]["operation_desc_premium"]["qt_score_booster"], dict)
    assert n1["content"]["logic_execution"] == "IF Active THEN Premium ELSE Mediocre"
    assert n2["content"]["logic_execution"] == "IF Active THEN Premium ELSE Mediocre"

    assert "N1" in n2["requires"]
    assert isinstance(n1["relations"], list) and n1["relations"]
    assert isinstance(n2["relations"], list) and n2["relations"]

    for node in nodes:
        expr = str(node.get("formula_expression") or "").strip()
        assert expr
        assert sorted(node.get("formula_variables") or []) == _formula_vars(expr)
        assert isinstance(node.get("reference_standard_codes"), list)
        assert int(node.get("reference_standard_count") or 0) >= 1
        assert isinstance(node.get("authority_resolution"), dict)
        assert node["authority_resolution"]["selected_source_hierarchy"] == node["source_hierarchy"]
        assert int(node.get("source_hierarchy_weight") or 0) >= 1
        assert int(node.get("authority_rank") or 0) >= 1


def test_strengthen_file_source_hierarchy_mixed(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-88-Mixed-Test.json"
    data = {
        "name": "mixed",
        "meta": {"activation_key": "智飞工程"},
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "A1",
                        "name": "扣分响应节点",
                        "qt_tag": ["扣分点"],
                        "content": {"operation_desc_premium": {"desc": "扣分风险处置"}},
                    },
                    {
                        "node_id": "A2",
                        "name": "桥梁节点",
                        "qt_tag": ["安全"],
                        "reference_standard": ["JTG/T 3650-2020 公路桥涵施工技术规范"],
                        "content": {"operation_desc_premium": {"desc": "桥梁安全控制"}},
                    },
                    {
                        "node_id": "A3",
                        "name": "质量节点",
                        "qt_tag": ["质量"],
                        "reference_standard": ["GB 50300-2013 建筑工程施工质量验收统一标准"],
                        "content": {"operation_desc_premium": {"desc": "质量验收控制"}},
                    },
                    {
                        "node_id": "A4",
                        "name": "图纸节点",
                        "qt_tag": ["重难点"],
                        "data_source_type": "DXF",
                        "content": {"operation_desc_premium": {"desc": "图纸约束"}},
                    },
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod.strengthen_file(kg_file)
    assert row["changed"] is True

    out = json.loads(kg_file.read_text(encoding="utf-8"))
    nodes = out["knowledge_database"]["sec"]["nodes"]
    by_id = {str(n["node_id"]): n for n in nodes}

    assert by_id["A1"]["source_hierarchy"] == "答疑文件"
    assert by_id["A2"]["source_hierarchy"] == "行标"
    assert by_id["A3"]["source_hierarchy"] == "国标"
    assert by_id["A4"]["source_hierarchy"] == "设计图纸"
    assert by_id["A1"]["source_hierarchy_weight"] > by_id["A4"]["source_hierarchy_weight"] > by_id["A3"]["source_hierarchy_weight"] > by_id["A2"]["source_hierarchy_weight"]
    assert by_id["A1"]["authority_rank"] < by_id["A4"]["authority_rank"] < by_id["A3"]["authority_rank"] < by_id["A2"]["authority_rank"]


def test_strengthen_file_is_idempotent_on_second_run(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-77-Idempotent-Test.json"
    data = {
        "name": "idem",
        "meta": {"activation_key": "智飞工程"},
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "I1",
                        "name": "质量控制节点",
                        "qt_tag": ["质量"],
                        "content": {"operation_desc_premium": {"desc": "首轮补强"}},
                    }
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    first = mod.strengthen_file(kg_file)
    assert first["changed"] is True
    first_payload = kg_file.read_text(encoding="utf-8")

    second = mod.strengthen_file(kg_file)
    assert second["changed"] is False
    second_payload = kg_file.read_text(encoding="utf-8")

    assert second_payload == first_payload


def test_strengthen_file_reassigns_canonical_formula_to_deterministic_slot(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-66-Railway-Formula-Test.json"
    node_id = "F1"
    node_name = "进度控制节点"
    expected_expr, _ = mod._choose_formula(dim="进度", node_domain="railway", node_id=node_id, node_name=node_name)
    pool_exprs = [expr for expr, _vars in mod.FORMULA_POOL_BY_DIM["进度"]]
    initial_expr = next(expr for expr in pool_exprs if expr != expected_expr)

    data = {
        "name": "formula-slot",
        "meta": {"activation_key": "智飞工程"},
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": node_id,
                        "name": node_name,
                        "qt_tag": ["进度"],
                        "content": {"operation_desc_premium": {"desc": "进度闭环控制"}},
                        "formula_expression": initial_expr,
                        "formula_variables": ["delay_hours", "planned_hours"],
                    }
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod.strengthen_file(kg_file)
    assert row["changed"] is True

    out = json.loads(kg_file.read_text(encoding="utf-8"))
    node = out["knowledge_database"]["sec"]["nodes"][0]
    assert node["formula_expression"] == expected_expr
    assert sorted(node.get("formula_variables") or []) == _formula_vars(expected_expr)


def test_strengthen_file_domain_mapping_for_digital_and_management(tmp_path: Path) -> None:
    mod = _load_module()
    digital_file = tmp_path / "ZF-KG-56-SmartOM-FM-Universe-SuperKG.json"
    management_file = tmp_path / "ZF-KG-54-TemporaryWorks-SiteLayout.json"

    base = {
        "meta": {"activation_key": "智飞工程"},
        "knowledge_database": {"sec": {"nodes": [{"node_id": "D1", "name": "节点", "qt_tag": ["进度"], "content": {}}]}},
    }
    digital_file.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    management_file.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")

    mod.strengthen_file(digital_file)
    mod.strengthen_file(management_file)

    digital_out = json.loads(digital_file.read_text(encoding="utf-8"))
    management_out = json.loads(management_file.read_text(encoding="utf-8"))
    digital_node = digital_out["knowledge_database"]["sec"]["nodes"][0]
    management_node = management_out["knowledge_database"]["sec"]["nodes"][0]

    assert digital_node["professional_domain"] == "digital"
    assert management_node["professional_domain"] == "management"


def test_strengthen_file_promotes_key_node_to_qa_authority(tmp_path: Path) -> None:
    mod = _load_module()
    file_stem = "ZF-KG-90-Progress-QA-Boost"
    node_name = "关键线路风险响应"
    node_id = None
    for i in range(1, 2000):
        nid = f"Q{i}"
        key = f"{file_stem}|{nid}|{node_name}|重难点|building"
        if mod._stable_index(key, 100) < 22:
            node_id = nid
            break
    assert node_id is not None

    kg_file = tmp_path / f"{file_stem}.json"
    data = {
        "name": "qa-boost",
        "meta": {"activation_key": "智飞工程"},
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": node_id,
                        "name": node_name,
                        "qt_tag": ["重难点"],
                        "content": {"operation_desc_premium": {"desc": "关注关键线路节点工期与接口风险控制"}},
                    }
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    mod.strengthen_file(kg_file)
    out = json.loads(kg_file.read_text(encoding="utf-8"))
    node = out["knowledge_database"]["sec"]["nodes"][0]
    assert node["source_hierarchy"] == "答疑文件"
