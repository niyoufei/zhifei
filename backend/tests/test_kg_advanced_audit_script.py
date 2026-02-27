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
        "numeric_sources": [
            {
                "parameter": "a",
                "value": "2",
                "unit": "次/班",
                "source_hierarchy": "国标",
                "effective_date": "2017-01-01",
                "clause_ref": "第1条",
                "clause_path": "GB/T 50326-2017/第1条/S1.0/P1",
                "anchor_hash": "abc123ef45678900",
                "evidence_anchor_id": "EA-TEST0001",
            }
        ],
        "evidence_anchors": [{"anchor_id": "EA-TEST0001", "parameter": "a"}],
        "cross_discipline_constraints": {"enabled": True},
        "process_parameter_pack": {"enabled": True, "steps": [{"seq": 1, "parameter": "a"}]},
        "resource_productivity_model": {"enabled": True, "unit_output_per_day": 100},
        "risk_trigger_matrix": {"enabled": True, "items": [{"trigger_id": "R1"}]},
        "clause_locator": {
            "enabled": True,
            "anchors": [
                {
                    "clause_ref": "第1条",
                    "clause_path": "GB/T 50326-2017/第1条/S1.0/P1",
                    "source_excerpt": "第1条 项目管理基本要求",
                    "anchor_hash": "abc123ef45678900",
                }
            ],
        },
        "cross_discipline_interface_contract": {
            "enabled": True,
            "interfaces": [{"with_domain": "mep"}],
            "conflict_graph": [{"from_domain": "building", "to_domain": "mep", "status": "resolved"}],
        },
        "optimization_objectives_ext": {"enabled": True, "objectives": {"duration": 0.4, "risk": 0.6}},
        "online_learning_profile": {"enabled": True, "strategy": "ema_feedback_v1"},
        "retrieval_benchmark": {"quality_score": 88, "minimum_quality_score": 70},
        "approval_workflow": {"required": True, "status": "approved"},
        "formula_sensitivity": {"enabled": True, "baseline_result": 1.0},
        "formula_safety_profile": {"enabled": True, "safe": True, "warnings": []},
        "evidence_completeness": {
            "enabled": True,
            "completeness_ratio": 1.0,
            "has_clause_anchor": True,
            "effective_date": "2017-01-01",
            "source_hierarchy": "国标",
        },
        "entity_alignment": {
            "enabled": True,
            "entity_master_key": "EMK-TEST001",
            "entity_type": "engineering_object",
            "aliases": ["测试节点", "N1"],
        },
        "entity_master_key": "EMK-TEST001",
        "regional_standard_timeline": {
            "enabled": True,
            "default_region": "CN",
            "records": [{"region_code": "CN", "policy_code": "GB/T 50326-2017", "status": "active"}],
        },
        "abnormal_scenario_playbook": {
            "enabled": True,
            "domain": "building",
            "dimension": "质量",
            "items": [{"scenario": "降雨中断", "response_sla_hours": 4}],
        },
        "deduction_counterexample_library": {
            "enabled": True,
            "dimension": "质量",
            "items": [{"counterexample_id": "质量-CE-1", "issue": "缺少复检"}],
        },
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


def test_advanced_audit_detects_p0_profile_gaps(tmp_path: Path) -> None:
    mod = _load_module()
    kg_file = tmp_path / "ZF-KG-03-Test.json"
    node = _base_node("N1")
    node.pop("entity_alignment", None)
    node["entity_master_key"] = ""
    node["formula_safety_profile"] = {"enabled": True, "safe": False}
    node["evidence_completeness"] = {
        "enabled": True,
        "completeness_ratio": 0.45,
        "has_clause_anchor": False,
        "effective_date": "",
        "source_hierarchy": "",
    }
    node["cross_discipline_interface_contract"] = {
        "enabled": True,
        "interfaces": [{"with_domain": "mep"}],
        "conflict_graph": [{"from_domain": "building", "to_domain": "mep", "status": "open"}],
    }
    kg_file.write_text(json.dumps({"knowledge_database": {"sec": {"nodes": [node]}}}, ensure_ascii=False, indent=2), encoding="utf-8")

    row = mod._check_file(kg_file)
    assert row["ready"] is False
    assert row["issues"]["missing_entity_alignment"] == 1
    assert row["issues"]["missing_entity_master_key"] == 1
    assert row["issues"]["unsafe_formula_safety_profile"] == 1
    assert row["issues"]["low_evidence_completeness_ratio"] == 1
    assert row["issues"]["missing_numeric_source_evidence"] == 1
    assert row["issues"]["open_interface_conflict"] == 1
