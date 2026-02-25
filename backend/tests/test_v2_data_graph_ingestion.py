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
    node = result["results"][0]
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
