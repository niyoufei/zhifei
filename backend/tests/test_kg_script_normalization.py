from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_script(name: str):
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module4_fix_normalizes_legacy_node_shapes(tmp_path: Path) -> None:
    mod = _load_script("fix_kg_module4_gaps.py")
    kg_file = tmp_path / "ZF-KG-99-Test.json"
    payload = {
        "module4_validation": mod._build_root_module4(),
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "N1",
                        "name": "测试节点",
                        "qt_tag": ["安全"],
                        "scoring_points": {
                            "dimension": "安全",
                            "checkpoints": [
                                "{'point_id':'安全-NODE','dimension':'安全','required_keywords':['安全','防护']}"
                            ],
                        },
                        "fail_fast_hooks": ["missing_numeric_source"],
                    }
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod.fix_file(kg_file)
    assert row["changed"] is True

    out = json.loads(kg_file.read_text(encoding="utf-8"))
    node = out["knowledge_database"]["sec"]["nodes"][0]

    scoring = node["scoring_points"]
    assert isinstance(scoring, dict)
    assert isinstance(scoring.get("checkpoints"), list) and scoring["checkpoints"]
    first = scoring["checkpoints"][0]
    assert isinstance(first, dict)
    assert isinstance(first.get("required_keywords"), list) and first["required_keywords"]

    hooks = node["fail_fast_hooks"]
    assert isinstance(hooks, dict)
    assert hooks.get("enabled") is True
    events = hooks.get("events") or []
    assert "missing_numeric_source" in events
    assert "missing_formula_expression" in events
    assert "missing_checker" in events

    assert isinstance(node.get("auto_rewrite"), dict) and node["auto_rewrite"].get("enabled") is True
    assertions = set(node.get("response_assertions") or [])
    assert {"must_have_action", "must_have_parameter", "must_have_checker"}.issubset(assertions)


def test_module4_report_accepts_dict_scoring_points_and_list_hooks(tmp_path: Path) -> None:
    fix_mod = _load_script("fix_kg_module4_gaps.py")
    report_mod = _load_script("generate_kg_module4_report.py")
    kg_file = tmp_path / "ZF-KG-98-Test.json"
    payload = {
        "module4_validation": fix_mod._build_root_module4(),
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "N1",
                        "name": "质量节点",
                        "qt_tag": ["质量"],
                        "scoring_points": {
                            "dimension": "质量",
                            "checkpoints": [
                                {
                                    "point_id": "质量-NODE",
                                    "dimension": "质量",
                                    "required_keywords": ["质量", "验收"],
                                    "match_mode": "any",
                                    "boolean_rule": "any_keyword_hit",
                                }
                            ],
                        },
                        "fail_fast_hooks": ["missing_numeric_source"],
                        "auto_rewrite": {
                            "enabled": True,
                            "strategy": "targeted_dimension_rewrite",
                            "template": "执行质量控制，参数阈值=95%，检查频次=2次/班，由质量员复核。",
                        },
                        "response_assertions": ["must_have_action", "must_have_parameter", "must_have_checker"],
                    }
                ]
            }
        },
    }
    kg_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    row = report_mod.analyze_file(kg_file)
    assert row["root_ready"] is True
    assert row["node_ready"] == row["node_total"] == 1
    assert row["overall_ready"] is True


def test_gemini_fix_new_formula_nodes_include_guardrail_fields(tmp_path: Path) -> None:
    mod = _load_script("fix_kg_gemini_enablement.py")
    kg_file = tmp_path / "ZF-KG-97-Test.json"
    payload = {
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "B1",
                        "name": "普通节点",
                        "qt_tag": ["进度"],
                        "content": {"operation_desc_premium": {"desc": "第一步（定义）：执行进度工序定义，工程量1200m3，施工员核验。"}},
                    }
                ]
            }
        }
    }
    kg_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod.fix_file(kg_file)
    assert row["changed"] is True
    assert row["formula_nodes_added"] >= 1

    out = json.loads(kg_file.read_text(encoding="utf-8"))
    nodes = out["knowledge_database"]["sec"]["nodes"]
    formula_nodes = [n for n in nodes if str(n.get("node_type") or "") == "FormulaNode"]
    assert formula_nodes
    for node in formula_nodes:
        assert isinstance(node.get("auto_rewrite"), dict) and node["auto_rewrite"].get("enabled") is True
        hooks = node.get("fail_fast_hooks")
        assert isinstance(hooks, dict) and hooks.get("enabled") is True
        assert "missing_numeric_source" in (hooks.get("events") or [])
        assertions = set(node.get("response_assertions") or [])
        assert {"must_have_action", "must_have_parameter", "must_have_checker"}.issubset(assertions)
        spec = node.get("visual_specs")
        assert isinstance(spec, dict) and spec.get("docx_embed") is True
        assert "样板" in (spec.get("visual_types") or [])


def test_gemini_fix_file_is_idempotent_on_second_run(tmp_path: Path) -> None:
    mod = _load_script("fix_kg_gemini_enablement.py")
    kg_file = tmp_path / "ZF-KG-96-Test.json"
    payload = {
        "knowledge_database": {
            "sec": {
                "nodes": [
                    {
                        "node_id": "N1",
                        "name": "质量节点",
                        "qt_tag": ["质量"],
                        "content": {"operation_desc_premium": {"desc": "注意质量，确保达标。"}},
                    }
                ]
            }
        }
    }
    kg_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    first = mod.fix_file(kg_file)
    assert first["changed"] is True
    first_payload = kg_file.read_text(encoding="utf-8")

    second = mod.fix_file(kg_file)
    assert second["changed"] is False
    second_payload = kg_file.read_text(encoding="utf-8")
    assert first_payload == second_payload
