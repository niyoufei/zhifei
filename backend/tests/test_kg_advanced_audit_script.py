from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "scripts" / "generate_kg_advanced_audit.py"
    spec = importlib.util.spec_from_file_location("generate_kg_advanced_audit", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_node(node_id: str) -> dict:
    return {
        "node_id": node_id,
        "name": "测试节点",
        "node_type": "FormulaNode",
        "requires": [],
        "mitigates": [],
        "conflicts_with": [],
        "reference_standard": ["GB/T 50326-2017 建设工程项目管理规范"],
        "content": {"environment_sensing": {"activation_signal": "Context CONTAINS '智飞工程'"}},
        "formula_expression": "a / max(b, 1)",
        "formula_variables": ["a", "b"],
        "reference_standard_codes": ["GB/T 50326-2017"],
        "reference_standard_count": 1,
        "reference_standard_primary": "GB/T 50326-2017 建设工程项目管理规范",
        "source_hierarchy": "国标",
        "source_hierarchy_weight": 3,
        "authority_rank": 3,
        "authority_resolution": {
            "rule": "答疑文件 > 设计图纸 > 国标 > 行标 > 企标",
            "selected_source_hierarchy": "国标",
            "selected_weight": 3,
            "selected_rank": 3,
            "candidates": ["国标"],
        },
        "standard_validity_timeline": {
            "version": "v1",
            "timeline_status": "active",
            "records": [
                {
                    "standard_code": "GB/T 50326-2017",
                    "tier": "国标",
                    "effective_date": "2017-01-01",
                    "expiry_date": "2027-12-31",
                    "review_cycle_years": 10,
                    "status": "active",
                }
            ],
        },
        "regional_policy_layers": {
            "default_region": "CN",
            "layers": [{"level": "national", "policy_code": "GB/T 50326-2017", "status": "active"}],
            "numeric_redlines": {"enabled": True, "active_region": "CN", "active_values": {"pm10_limit_ug_m3": 150}},
        },
        "unit_dimension_model": {
            "enabled": True,
            "parameters": [{"parameter": "a", "unit": "次/班", "dimension": "frequency"}],
            "consistency_check": {"required": True, "status": "pass"},
        },
        "evidence_anchors": [{"anchor_id": "EA-TEST0001", "parameter": "a"}],
        "cross_discipline_constraints": {"enabled": True},
        "process_parameter_pack": {"enabled": True, "steps": [{"seq": 1, "parameter": "a"}]},
        "resource_productivity_model": {"enabled": True, "unit_output_per_day": 100},
        "risk_trigger_matrix": {"enabled": True, "items": [{"trigger_id": "R1"}]},
        "clause_locator": {"enabled": True, "anchors": [{"clause_ref": "第1条"}]},
        "cross_discipline_interface_contract": {"enabled": True, "interfaces": [{"with_domain": "mep"}]},
        "optimization_objectives_ext": {"enabled": True, "objectives": {"duration": 0.4, "risk": 0.6}},
        "online_learning_profile": {"enabled": True, "strategy": "ema_feedback_v1"},
        "retrieval_benchmark": {"quality_score": 88, "minimum_quality_score": 70},
        "approval_workflow": {"required": True, "status": "approved"},
        "formula_sensitivity": {"enabled": True, "baseline_result": 1.0},
        "bim_ifc_context": {"enabled": True, "ifc_entities": ["IfcProject"]},
        "incremental_fingerprint": "abc123",
        "visual_specs": {"enabled": True},
        "fail_fast_hooks": {"enabled": True},
        "response_assertions": ["must_have_action", "must_have_parameter", "must_have_checker"],
    }


def test_advanced_audit_detects_issues(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-01-Test.json"
    node = _base_node("N1")
    node["requires"] = ["UNKNOWN_ID"]
    node["formula_variables"] = ["a"]  # mismatch
    node["content"] = {"environment_sensing": {"activation_signal": ""}}  # missing signal
    kg_file.write_text(json.dumps({"knowledge_database": {"sec": {"nodes": [node]}}}, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod._check_file(kg_file)
    assert row["ready"] is False
    assert row["issues"]["unresolved_relations"] == 1
    assert row["issues"]["formula_var_mismatch"] == 1
    assert row["issues"]["missing_activation_signal"] == 1
    assert row["total_issues"] >= 3


def test_advanced_audit_passes_clean_file(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-02-Test.json"
    node = _base_node("N1")
    kg_file.write_text(json.dumps({"knowledge_database": {"sec": {"nodes": [node]}}}, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod._check_file(kg_file)
    assert row["ready"] is True
    assert row["total_issues"] == 0
