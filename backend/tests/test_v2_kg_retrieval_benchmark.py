from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.data_graph_ingestion import ingest_knowledge_graph
from backend.zhifei_autoplan.v2.kg_retrieval_benchmark import run_retrieval_benchmark


def test_run_retrieval_benchmark_reports_pass_metrics(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "sample.json").write_text(
        json.dumps(
            {
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {
                                "node_id": "N1",
                                "name": "质量抽检节点",
                                "keywords": ["质量", "抽检", "频次"],
                                "content": {"operation_desc_premium": {"desc": "质量抽检频次每班2次。"}},
                            }
                        ]
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    db = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db, force_reindex=True)
    assert report["ok"] is True

    dataset = tmp_path / "benchmark.json"
    dataset.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "c1",
                        "query": "质量 抽检",
                        "expected_keywords": ["质量", "抽检"],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    bm = run_retrieval_benchmark(db_path=db, dataset_path=dataset, min_pass_rate=0.5, min_avg_mrr=0.1)
    assert bm["ok"] is True
    assert int(bm.get("total_cases") or 0) == 1
    assert float(bm.get("pass_rate") or 0.0) >= 1.0

