from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.zhifei_autoplan.v2.data_graph_ingestion import (
    KnowledgeGraphIndex,
    ingest_knowledge_graph,
    search_graph_index,
)


def _build_sample_files(root: Path) -> None:
    (root / "sample.json").write_text(
        json.dumps(
            {
                "name": "Municipal-Road-KG",
                "domain": "市政道路",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "ROAD-01",
                                "name": "混凝土摊铺",
                                "qt_tag": ["quality", "schedule"],
                                "content": {
                                    "operation_desc_premium": {
                                        "desc": "分层摊铺，厚度 30cm，平整度控制。",
                                        "bid_response_strategy": {
                                            "trigger_keywords": ["混凝土", "摊铺", "平整度"]
                                        },
                                    }
                                },
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (root / "sample.md").write_text(
        "# 绿色施工\n\n采取喷淋降尘，PM10 阈值控制。\n\n## 检查\n\n安全员每日检查并记录。\n",
        encoding="utf-8",
    )

    (root / "sample.xml").write_text(
        """
        <root name="xml-demo">
          <node id="x1" name="危化品储运">危化品双人领用复核，每班次一次。</node>
        </root>
        """,
        encoding="utf-8",
    )

    (root / "sample.csv").write_text(
        "name,action,checker,parameter\n"
        "劳保用品发放,发放安全帽,安全员,1套/人\n",
        encoding="utf-8",
    )


def test_ingest_and_search_multi_format(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    _build_sample_files(root)

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path)

    assert report["ok"] is True
    assert report["files_total"] == 4
    assert report["nodes_indexed"] >= 4

    by_tag = search_graph_index(tags=["quality"], db_path=db_path)
    assert by_tag["ok"] is True
    assert by_tag["total"] >= 1

    by_keyword = search_graph_index(keywords=["混凝土"], db_path=db_path)
    assert by_keyword["total"] >= 1
    assert any("混凝土" in (it["title"] + it["snippet"]) for it in by_keyword["results"])

    by_query = search_graph_index(query="危化品 储运", db_path=db_path)
    assert by_query["total"] >= 1


def test_reindex_skips_unchanged_file(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    _build_sample_files(root)

    db_path = tmp_path / "kg.sqlite3"
    first = ingest_knowledge_graph(root, db_path=db_path)
    second = ingest_knowledge_graph(root, db_path=db_path)

    assert first["files_parsed"] == 4
    assert second["files_skipped"] == 4


def test_real_desktop_kg_path_can_be_scanned_if_exists(tmp_path: Path) -> None:
    desktop_path = Path("/Users/youfeini/Desktop/文档生成系统/知识图谱")
    if not desktop_path.exists():
        pytest.skip("desktop knowledge graph path is not present in this environment")

    db_path = tmp_path / "desktop.sqlite3"
    report = ingest_knowledge_graph(desktop_path, db_path=db_path)

    assert report["ok"] is True
    assert report["files_total"] > 0

    result = search_graph_index(query="质量 安全 进度", top_k=5, db_path=db_path)
    assert result["ok"] is True


def test_class_api_search_returns_ranked_results(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    _build_sample_files(root)

    index = KnowledgeGraphIndex(db_path=tmp_path / "kg.sqlite3")
    index.ingest_directory(root)

    res = index.search(query="平整度", tags=["schedule"], top_k=3)
    assert res["ok"] is True
    assert len(res["results"]) <= 3
    if len(res["results"]) >= 2:
        assert res["results"][0]["score"] >= res["results"][1]["score"]


def test_tactical_fields_are_mapped_from_json(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "tactical.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-45-Curtain-Wall",
                "meta": {"activation_key": "智飞工程"},
                "knowledge_database": {
                    "advanced": {
                        "nodes": [
                            {
                                "node_id": "CURT-FN-001-V20.1",
                                "name": "异形曲面幕墙参数化设计",
                                "content": {
                                    "environment_sensing": {
                                        "activation_signal": "Context CONTAINS '智飞工程'"
                                    },
                                    "operation_desc_mediocre": "传统CAD放样，误差大，废料多。",
                                    "operation_desc_premium": {
                                        "desc": "Rhino+Grasshopper 算法优化。",
                                        "bid_response_strategy": {
                                            "trigger_keywords": ["双曲面", "加工精度"],
                                            "response_template": "利用参数化算法优化面板分割。",
                                        },
                                        "competitor_shield": {
                                            "trap_logic": "建议考察异形幕墙参数化优化案例。"
                                        },
                                        "qt_score_booster": {
                                            "policy_alignment": ["建筑美学"],
                                            "score_weight": "+3_Points",
                                        },
                                    },
                                },
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(query="双曲面 参数化", db_path=db_path, resolve_authority=False, top_k=20)
    assert result["total"] >= 1
    node = next(
        (
            item
            for item in (result.get("results") or [])
            if str(item.get("title") or "") == "混凝土浇筑增强节点"
        ),
        (result.get("results") or [{}])[0],
    )
    assert node["dna_verified"] is True
    assert node["tactical_mode"] == "premium"
    assert node["bid_response_strategy"]["trigger_keywords"] == ["双曲面", "加工精度"]
    assert "trap_logic" in node["competitor_shield"]
    assert node["qt_score_booster"]["score_weight"] == "+3_Points"


def test_dna_verification_fallback_to_mediocre(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "tactical_fail.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-FAIL",
                "meta": {"activation_key": "智飞工程"},
                "knowledge_database": {
                    "advanced": {
                        "nodes": [
                            {
                                "node_id": "CURT-FN-002-V20.1",
                                "name": "高层幕墙安装机器人",
                                "content": {
                                    "environment_sensing": {
                                        "activation_signal": "Context CONTAINS 'NOT-MATCHED-KEY'"
                                    },
                                    "operation_desc_mediocre": "传统吊篮作业，效率低，风险高。",
                                    "operation_desc_premium": {
                                        "desc": "自动吸附安装，精度1mm内。",
                                        "bid_response_strategy": {
                                            "trigger_keywords": ["高空作业"],
                                            "response_template": "机器人替代人工。",
                                        },
                                    },
                                },
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(query="高层幕墙 机器人", db_path=db_path, resolve_authority=False, top_k=20)
    assert result["total"] >= 1
    node = result["results"][0]
    assert node["dna_verified"] is False
    assert node["tactical_mode"] == "mediocre"
    assert "传统吊篮作业" in node["snippet"]


def test_quantitative_fields_are_mapped_from_json(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "quant.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-QUANT",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "Q-001",
                                "name": "关键工序量化控制",
                                "safety_level": "high",
                                "resource_requirements": {"manpower": {"crew_size": "10人/班"}},
                                "formula_expression": "quantity / max(productivity_per_day, 1)",
                                "formula_variables": ["quantity", "productivity_per_day"],
                                "numeric_sources": [
                                    {
                                        "parameter": "inspection_frequency",
                                        "value": "2",
                                        "unit": "次/班",
                                        "source_text": "专项方案条款",
                                    }
                                ],
                                "quantitative_indices": {
                                    "duration_index": 0.63,
                                    "risk_index": 0.77,
                                    "resource_density_index": 0.71,
                                },
                                "schedule_constraints": {
                                    "critical_path_hint": ["测量放线", "基础工程", "主体结构"],
                                    "min_process_interval_days": 2,
                                },
                                "content": {
                                    "operation_desc_premium": {
                                        "desc": "每班次检查2次，偏差在4h内闭环。",
                                    }
                                },
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(query="量化控制 关键工序", db_path=db_path, resolve_authority=False, top_k=20)
    assert result["total"] >= 1
    node = result["results"][0]

    assert isinstance(node.get("numeric_sources"), list) and len(node["numeric_sources"]) >= 1
    assert isinstance(node.get("quantitative_indices"), dict)
    assert isinstance(node.get("schedule_constraints"), dict)
    assert node["quantitative_indices"]["risk_index"] == pytest.approx(0.77, rel=1e-6)
    assert node["schedule_constraints"]["min_process_interval_days"] == 2


def test_search_supports_professional_domain_filter_and_gemini_score(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "domain.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-DOMAIN",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "MEP-001",
                                "name": "机电综合管线深化",
                                "keywords": ["机电", "管线", "综合支吊架"],
                                "source_hierarchy": "国标",
                                "formula_expression": "work_volume / max(productivity_per_day * crew_efficiency, 1)",
                                "formula_variables": ["work_volume", "productivity_per_day", "crew_efficiency"],
                                "resource_requirements": {"crew_size": "12人/班"},
                                "numeric_sources": [{"parameter": "inspection_frequency", "value": "2", "unit": "次/班"}],
                                "content": {
                                    "environment_sensing": {"activation_signal": "Context CONTAINS '智飞工程'"},
                                    "operation_desc_premium": {"desc": "机电管线综合排布，BIM复核。"},
                                },
                            },
                            {
                                "node_id": "ROAD-001",
                                "name": "道路路基压实",
                                "keywords": ["道路", "路基", "压实度"],
                                "source_hierarchy": "企标",
                                "content": {"operation_desc_premium": {"desc": "常规压实施工。"}},
                            },
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    mep_result = search_graph_index(
        query="管线 深化",
        professional_domains=["mep"],
        db_path=db_path,
        resolve_authority=False,
        top_k=10,
    )
    assert mep_result["total"] >= 1
    assert all("mep" in (item.get("professional_domain_matches") or []) for item in mep_result["results"])

    high_score_result = search_graph_index(
        query="压实 管线",
        min_gemini_usefulness_score=55,
        db_path=db_path,
        resolve_authority=False,
        top_k=10,
    )
    assert high_score_result["total"] >= 1
    assert all(float(item.get("gemini_usefulness_score") or 0.0) >= 55 for item in high_score_result["results"])


def test_search_supports_enhanced_capability_fields_and_filters(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "enhanced.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-ENHANCED",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "ENH-001",
                                "name": "混凝土浇筑增强节点",
                                "source_hierarchy": "国标",
                                "is_auto_generated": True,
                                "formula_expression": "volume / max(productivity, 1)",
                                "formula_variables": ["volume", "productivity"],
                                "numeric_sources": [
                                    {
                                        "parameter": "volume",
                                        "value": "120",
                                        "unit": "m3",
                                        "source_hierarchy": "国标",
                                        "effective_date": "2024-01-01",
                                        "clause_ref": "第1条",
                                        "clause_path": "GB 50300-2013/第1条/S1.0/P1",
                                        "anchor_hash": "abc123ef45678900",
                                        "evidence_anchor_id": "EA-1",
                                    }
                                ],
                                "standard_validity_timeline": {
                                    "timeline_status": "active",
                                    "records": [{"standard_code": "GB 50300-2013"}],
                                },
                                "regional_policy_layers": {
                                    "default_region": "CN",
                                    "layers": [{"level": "national", "policy_code": "GB 50300-2013"}],
                                },
                                "unit_dimension_model": {
                                    "parameters": [{"parameter": "volume", "unit": "m3", "dimension": "volume"}]
                                },
                                "evidence_anchors": [{"anchor_id": "EA-1", "parameter": "volume"}],
                                "cross_discipline_constraints": {"enabled": True},
                                "process_parameter_pack": {
                                    "enabled": True,
                                    "steps": [{"seq": 1, "parameter": "volume", "default_value": 120}],
                                },
                                "resource_productivity_model": {"enabled": True, "unit_output_per_day": 320.0},
                                "risk_trigger_matrix": {"enabled": True, "items": [{"trigger_id": "R-1"}]},
                                "clause_locator": {
                                    "enabled": True,
                                    "anchors": [{"clause_ref": "第1条", "standard_code": "GB 50300-2013"}],
                                },
                                "cross_discipline_interface_contract": {
                                    "enabled": True,
                                    "interfaces": [{"with_domain": "mep"}],
                                    "conflict_graph": [{"from_domain": "building", "to_domain": "mep", "status": "resolved"}],
                                },
                                "optimization_objectives_ext": {
                                    "enabled": True,
                                    "objectives": {"duration": 0.4, "risk": 0.3, "cost": 0.3},
                                },
                                "online_learning_profile": {"enabled": True, "strategy": "ema_feedback_v1"},
                                "retrieval_benchmark": {"quality_score": 88, "minimum_quality_score": 70},
                                "approval_workflow": {"required": True, "status": "approved"},
                                "formula_sensitivity": {"enabled": True, "baseline_result": 4.0},
                                "formula_safety_profile": {"enabled": True, "safe": True, "warnings": []},
                                "evidence_completeness": {
                                    "enabled": True,
                                    "completeness_ratio": 1.0,
                                    "completeness_score": 100,
                                    "source_hierarchy": "国标",
                                    "effective_date": "2024-01-01",
                                    "has_clause_anchor": True,
                                    "status": "pass",
                                    "verification_ratio": 1.0,
                                    "verification_status": "pass",
                                },
                                "entity_master_key": "EMK-ENH-001",
                                "source_provenance": {
                                    "resolved_source_hierarchy": "国标",
                                    "reference_tiers": ["国标"],
                                    "reference_codes": ["GB 50300-2013"],
                                },
                                "entity_alignment": {
                                    "enabled": True,
                                    "entity_master_key": "EMK-ENH-001",
                                    "entity_type": "engineering_object",
                                    "aliases": ["混凝土浇筑增强节点"],
                                },
                                "regional_standard_timeline": {
                                    "enabled": True,
                                    "default_region": "CN",
                                    "records": [{"region_code": "CN", "policy_code": "GB 50300-2013"}],
                                },
                                "abnormal_scenario_playbook": {
                                    "enabled": True,
                                    "dimension": "质量",
                                    "domain": "building",
                                    "items": [{"scenario": "降雨中断", "response_sla_hours": 4}],
                                },
                                "deduction_counterexample_library": {
                                    "enabled": True,
                                    "dimension": "质量",
                                    "items": [{"counterexample_id": "质量-CE-1", "issue": "缺少复检"}],
                                },
                                "bim_ifc_context": {"ifc_entities": ["IfcBuilding"]},
                                "incremental_fingerprint": "fingerprint-001",
                                "incremental_update": {"strategy": "fingerprint_diff"},
                                "content": {
                                    "environment_sensing": {"activation_signal": "Context CONTAINS '智飞工程'"},
                                    "operation_desc_premium": {"desc": "混凝土浇筑参数化控制。"},
                                },
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(
        query="混凝土 浇筑",
        min_retrieval_quality_score=80,
        region_context="CN",
        require_approved_auto=True,
        db_path=db_path,
        resolve_authority=False,
        top_k=5,
    )
    assert result["total"] >= 1
    node = result["results"][0]
    assert node["retrieval_quality_score"] >= 80
    assert node["standard_validity_timeline"]["timeline_status"] == "active"
    assert node["regional_policy_layers"]["default_region"] == "CN"
    assert isinstance(node["unit_dimension_model"]["parameters"], list)
    assert isinstance(node["evidence_anchors"], list) and node["evidence_anchors"]
    assert node["approval_workflow"]["status"] == "approved"
    assert isinstance(node["bim_ifc_context"]["ifc_entities"], list)
    assert str(node["incremental_fingerprint"]).strip()
    assert bool((node.get("process_parameter_pack") or {}).get("enabled"))
    assert bool((node.get("resource_productivity_model") or {}).get("enabled"))
    assert bool((node.get("risk_trigger_matrix") or {}).get("enabled"))
    assert bool((node.get("clause_locator") or {}).get("enabled"))
    first_anchor = ((node.get("clause_locator") or {}).get("anchors") or [{}])[0]
    assert str(first_anchor.get("anchor_hash") or "").strip()
    assert str(first_anchor.get("clause_path") or "").strip()
    assert str(first_anchor.get("source_excerpt") or "").strip()
    assert bool((node.get("cross_discipline_interface_contract") or {}).get("enabled"))
    assert bool((node.get("optimization_objectives_ext") or {}).get("enabled"))
    assert bool((node.get("online_learning_profile") or {}).get("enabled"))
    assert bool((node.get("formula_safety_profile") or {}).get("safe"))
    assert float((node.get("evidence_completeness") or {}).get("completeness_ratio") or 0.0) >= 0.8
    assert float((node.get("evidence_completeness") or {}).get("verification_ratio") or 0.0) >= 0.5
    assert str(node.get("entity_master_key") or "").strip() == "EMK-ENH-001"
    assert str((node.get("entity_alignment") or {}).get("entity_master_key") or "").strip() == "EMK-ENH-001"
    assert bool((node.get("regional_standard_timeline") or {}).get("records"))
    assert bool((node.get("abnormal_scenario_playbook") or {}).get("items"))
    assert bool((node.get("deduction_counterexample_library") or {}).get("items"))


def test_search_supports_bid_date_timeline_effective_filter(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "timeline.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-TIMELINE",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "TIME-OLD",
                                "name": "旧版质量条款",
                                "keywords": ["质量", "抽检"],
                                "source_hierarchy": "国标",
                                "standard_validity_timeline": {
                                    "timeline_status": "review_required",
                                    "records": [
                                        {
                                            "standard_code": "GB 50300-2010",
                                            "effective_date": "2010-01-01",
                                            "expiry_date": "2034-12-31",
                                            "status": "superseded",
                                            "superseded_by": "GB 50300-2024",
                                        }
                                    ],
                                },
                                "content": {"operation_desc_premium": {"desc": "旧版抽检条款"}},
                            },
                            {
                                "node_id": "TIME-NEW",
                                "name": "新版质量条款",
                                "keywords": ["质量", "抽检"],
                                "source_hierarchy": "国标",
                                "standard_validity_timeline": {
                                    "timeline_status": "active",
                                    "records": [
                                        {
                                            "standard_code": "GB 50300-2024",
                                            "effective_date": "2024-01-01",
                                            "expiry_date": "2034-12-31",
                                            "status": "active",
                                        }
                                    ],
                                },
                                "content": {"operation_desc_premium": {"desc": "新版抽检条款"}},
                            },
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    current = search_graph_index(
        query="质量 抽检",
        bid_date="2026-06-01",
        allow_superseded=False,
        db_path=db_path,
        resolve_authority=False,
        top_k=10,
    )
    titles = [str(item.get("title") or "") for item in current.get("results") or []]
    assert "新版质量条款" in titles
    assert "旧版质量条款" not in titles

    allowed = search_graph_index(
        query="质量 抽检",
        bid_date="2026-06-01",
        allow_superseded=True,
        db_path=db_path,
        resolve_authority=False,
        top_k=10,
    )
    titles_allowed = [str(item.get("title") or "") for item in allowed.get("results") or []]
    assert "旧版质量条款" in titles_allowed


def test_search_supports_regional_policy_plugins(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "shanghai.json").write_text(
        json.dumps(
            {
                "plugin_name": "ShanghaiPolicyPlugin",
                "region_code": "SH",
                "aliases": ["上海", "31"],
                "region_bonus": 1.2,
                "require_any_policy_codes": ["DB31"],
                "prefer_policy_codes": ["DB31/T"],
                "source_hierarchy_min": "行标",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "regional.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-REGIONAL",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "REGION-SH-OK",
                                "name": "上海地区节点",
                                "keywords": ["环保", "噪声"],
                                "source_hierarchy": "行标",
                                "regional_policy_layers": {
                                    "default_region": "SH",
                                    "layers": [{"level": "city", "policy_code": "DB31/T 1234-2024"}],
                                },
                                "reference_standard_codes": ["DB31/T 1234-2024"],
                                "content": {"operation_desc_premium": {"desc": "按上海地标控制噪声。"}},
                            },
                            {
                                "node_id": "REGION-SH-BAD",
                                "name": "非上海地标节点",
                                "keywords": ["环保", "噪声"],
                                "source_hierarchy": "行标",
                                "regional_policy_layers": {
                                    "default_region": "SH",
                                    "layers": [{"level": "city", "policy_code": "Q/ABC 01-2020"}],
                                },
                                "content": {"operation_desc_premium": {"desc": "非地标条款。"}},
                            },
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(
        query="环保 噪声",
        region_context="SH",
        regional_plugin_dir=plugin_dir,
        db_path=db_path,
        resolve_authority=False,
        top_k=10,
    )
    titles = [str(item.get("title") or "") for item in result.get("results") or []]
    assert "上海地区节点" in titles
    assert "非上海地标节点" not in titles
    plugin_item = next(item for item in result["results"] if str(item.get("title") or "") == "上海地区节点")
    assert float((plugin_item.get("regional_policy_plugin") or {}).get("bonus") or 0.0) >= 1.2


def test_search_can_load_retrieval_weight_profile(tmp_path: Path) -> None:
    profile = tmp_path / "weight_profile.json"
    profile.write_text(
        json.dumps(
            {
                "version": "v1",
                "weights": {"query_token_weight": 1.7, "keyword_exact_weight": 1.3},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "simple.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-SIMPLE",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "W-001",
                                "name": "质量抽检节点",
                                "keywords": ["质量", "抽检"],
                                "content": {"operation_desc_premium": {"desc": "每班次检查2次。"}},
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(
        query="质量 抽检",
        retrieval_weight_profile_path=profile,
        db_path=db_path,
        resolve_authority=False,
    )
    assert result["total"] >= 1
    weights = result.get("retrieval_score_weights") or {}
    assert float(weights.get("query_token_weight") or 0.0) == 1.7
    assert float(weights.get("keyword_exact_weight") or 0.0) == 1.3


def test_authority_resolution_prefers_entity_master_key_grouping(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "authority_entity.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-AUTH-ENTITY",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "AUTH-LOW",
                                "name": "模板方案A",
                                "object_key": "obj-low",
                                "source_hierarchy": "行标",
                                "entity_master_key": "EMK-AUTH-001",
                                "entity_alignment": {"enabled": True, "entity_master_key": "EMK-AUTH-001"},
                                "keywords": ["模板", "支撑"],
                                "content": {"operation_desc_premium": {"desc": "旧版模板支撑方案。"}},
                            },
                            {
                                "node_id": "AUTH-HIGH",
                                "name": "模板方案B",
                                "object_key": "obj-high",
                                "source_hierarchy": "答疑文件",
                                "entity_master_key": "EMK-AUTH-001",
                                "entity_alignment": {"enabled": True, "entity_master_key": "EMK-AUTH-001"},
                                "keywords": ["模板", "支撑"],
                                "content": {"operation_desc_premium": {"desc": "答疑明确模板支撑参数。"}},
                            },
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(query="模板 支撑", db_path=db_path, top_k=10, resolve_authority=True)
    matched = [item for item in (result.get("results") or []) if str(item.get("entity_master_key") or "") == "EMK-AUTH-001"]
    assert len(matched) == 1
    node = matched[0]
    assert str(node.get("source_hierarchy") or "") == "答疑文件"


def test_search_supports_long_tail_domain_transfer_and_segment_learning(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "long_tail.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-LONGTAIL",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "LT-001",
                                "name": "机场飞行区排水控制",
                                "keywords": ["飞行区", "机场", "排水", "道面"],
                                "source_hierarchy": "国标",
                                "long_tail_profile": {
                                    "enabled": True,
                                    "specialty_tag": "airport",
                                    "fallback_domains": ["road", "building", "mep"],
                                    "transfer_factor": 0.95,
                                },
                                "online_learning_profile": {
                                    "enabled": True,
                                    "layered_strategy": "global+domain+region+dimension",
                                    "weight_adjustments": {"query_token_weight": 1.05},
                                    "segment_overrides": [
                                        {
                                            "segment_type": "domain",
                                            "segment_key": "airport",
                                            "min_hit_count": 0,
                                            "weight_adjustments": {"domain_weight": 1.25},
                                        }
                                    ],
                                },
                                "content": {"operation_desc_premium": {"desc": "飞行区排水系统参数化控制。"}},
                            },
                            {
                                "node_id": "RD-001",
                                "name": "市政道路排水控制",
                                "keywords": ["道路", "排水", "雨污分流"],
                                "source_hierarchy": "国标",
                                "content": {"operation_desc_premium": {"desc": "道路排水常规控制。"}},
                            },
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(
        query="飞行区 排水",
        professional_domains=["airport"],
        db_path=db_path,
        resolve_authority=False,
        top_k=10,
    )
    assert result["total"] >= 1
    best = result["results"][0]
    assert "机场飞行区排水控制" in str(best.get("title") or "")
    assert bool((best.get("long_tail_match") or {}).get("matched"))
    assert "airport" in (best.get("professional_domain_matches") or [])
    assert bool((best.get("retrieval_learning_adjustment") or {}).get("applied"))


def test_search_outputs_uncertainty_interval_bundle(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "uncertainty.json").write_text(
        json.dumps(
            {
                "name": "ZF-KG-UNCERTAINTY",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "UC-001",
                                "name": "浇筑时长推导节点",
                                "keywords": ["浇筑", "时长", "推导"],
                                "source_hierarchy": "国标",
                                "formula_expression": "volume / max(productivity, 1)",
                                "formula_variables": ["volume", "productivity"],
                                "formula_sensitivity": {"enabled": True, "baseline_result": 10.0},
                                "uncertainty_profile": {
                                    "enabled": True,
                                    "confidence_level": 0.72,
                                    "relative_interval": 0.2,
                                    "baseline_result": 10.0,
                                },
                                "content": {"operation_desc_premium": {"desc": "按方量推导浇筑时长。"}},
                            }
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    db_path = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db_path, force_reindex=True)
    assert report["ok"] is True

    result = search_graph_index(
        query="浇筑 时长 推导",
        db_path=db_path,
        resolve_authority=False,
        top_k=5,
    )
    assert result["total"] >= 1
    node = result["results"][0]
    interval = node.get("uncertainty_interval") or {}
    assert bool(interval.get("enabled"))
    assert float(interval.get("confidence_level") or 0.0) == pytest.approx(0.72, rel=1e-6)
    assert float(interval.get("lower") or 0.0) == pytest.approx(8.0, rel=1e-6)
    assert float(interval.get("upper") or 0.0) == pytest.approx(12.0, rel=1e-6)
