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
