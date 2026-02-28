from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.data_graph_ingestion import ingest_knowledge_graph
from backend.zhifei_autoplan.v2.kg_retrieval_benchmark import ensure_benchmark_dataset, run_retrieval_benchmark


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


def test_ensure_benchmark_dataset_can_auto_expand_from_kg(tmp_path: Path) -> None:
    kg_root = tmp_path / "kg"
    kg_root.mkdir(parents=True, exist_ok=True)
    (kg_root / "ZF-KG-01.json").write_text(
        json.dumps(
            {
                "name": "kg-01",
                "domain": "房建",
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {"node_id": "N1", "name": "质量抽检参数", "keywords": ["质量", "抽检", "频次"]},
                            {"node_id": "N2", "name": "安全巡检时限", "keywords": ["安全", "巡检", "时限"]},
                            {"node_id": "N3", "name": "进度关键线路", "keywords": ["进度", "关键线路", "工期"]},
                            {"node_id": "N4", "name": "环保噪声控制", "keywords": ["环保", "噪声", "阈值"]},
                            {"node_id": "N5", "name": "重难点专项方案", "keywords": ["重难点", "专项", "风险"]},
                            {"node_id": "N6", "name": "扣分点闭环", "keywords": ["扣分", "闭环", "验收"]},
                        ]
                    }
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"cases": []}, ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "auto.json"

    expanded = ensure_benchmark_dataset(
        dataset_path=seed,
        kg_root=kg_root,
        min_cases=5,
        max_cases=10,
        output_path=out,
    )
    assert expanded["ok"] is True
    assert expanded["expanded"] is True
    assert int(expanded.get("cases_total") or 0) >= 5
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(payload.get("cases"), list)
    assert len(payload["cases"]) >= 5
    coverage = expanded.get("coverage") or {}
    assert int(coverage.get("domains_total") or 0) >= 1
    assert isinstance(coverage.get("domain_counts"), dict)


def test_run_retrieval_benchmark_emits_domain_summary(tmp_path: Path) -> None:
    root = tmp_path / "kg"
    root.mkdir(parents=True, exist_ok=True)
    (root / "sample.json").write_text(
        json.dumps(
            {
                "name": "Municipal-Road-KG",
                "domain": "市政道路",
                "knowledge_database": {
                    "core": {
                        "nodes": [
                            {
                                "node_id": "ROAD-001",
                                "name": "道路压实度抽检",
                                "keywords": ["道路", "压实", "抽检"],
                                "content": {"operation_desc_premium": {"desc": "压实度>=95%，每班次抽检2次。"}},
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
    db = tmp_path / "kg.sqlite3"
    report = ingest_knowledge_graph(root, db_path=db, force_reindex=True)
    assert report["ok"] is True

    dataset = tmp_path / "benchmark_domain.json"
    dataset.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "d1",
                        "query": "道路 压实 抽检",
                        "expected_keywords": ["道路", "压实"],
                        "domain_hint": "road",
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    bm = run_retrieval_benchmark(db_path=db, dataset_path=dataset, min_pass_rate=0.1, min_avg_mrr=0.1)
    assert bm["ok"] is True
    summary = bm.get("domain_summary") or []
    assert isinstance(summary, list) and summary
    first = summary[0]
    assert first.get("domain")
    assert int(first.get("total_cases") or 0) >= 1
