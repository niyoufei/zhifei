from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.kg_online_learning_writeback import writeback_online_learning_profile


def test_writeback_online_learning_profile_updates_nodes(tmp_path: Path) -> None:
    kg_root = tmp_path / "kg"
    kg_root.mkdir(parents=True, exist_ok=True)
    kg_file = kg_root / "ZF-KG-01-Test.json"
    kg_file.write_text(
        json.dumps(
            {
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {"node_id": "NODE-1", "name": "节点1"},
                            {"node_id": "NODE-2", "name": "节点2"},
                        ]
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = writeback_online_learning_profile(
        graph_root=kg_root,
        node_feedback={
            "NODE-1": {
                "hit_count": 3,
                "pass_count": 2,
                "trace_coverage_avg": 0.8,
                "accepted_count": 1,
                "rejected_count": 0,
                "modified_count": 1,
                "decision_total": 2,
                "last_decision": "modify",
                "weight_adjustments": {"keyword_exact_weight": 1.15},
                "segment_overrides": [
                    {
                        "segment_type": "domain",
                        "segment_key": "building",
                        "min_hit_count": 3,
                        "weight_adjustments": {"domain_weight": 1.08},
                    }
                ],
            },
            "NODE-X": {"hit_count": 1, "pass_count": 1, "trace_coverage_avg": 1.0},
        },
        timestamp="2026-02-27T12:00:00",
    )
    assert report["ok"] is True
    assert int(report["files_changed"] or 0) == 1
    assert int(report["nodes_updated"] or 0) == 1
    assert int(report["matched_nodes"] or 0) == 1
    assert "NODE-X" in (report.get("unresolved_node_ids") or [])

    payload = json.loads(kg_file.read_text(encoding="utf-8"))
    node = payload["knowledge_database"]["sec"]["nodes"][0]
    profile = node.get("online_learning_profile") or {}
    assert int(profile.get("hit_count") or 0) == 3
    assert int(profile.get("pass_count") or 0) == 2
    assert float(profile.get("pass_rate") or 0.0) == round(2 / 3, 6)
    assert str(profile.get("last_feedback_at") or "") == "2026-02-27T12:00:00"
    assert int(profile.get("decision_total") or 0) == 2
    assert str(profile.get("last_decision") or "") == "modify"
    assert float((profile.get("weight_adjustments") or {}).get("keyword_exact_weight") or 0.0) == 1.15
    assert str(profile.get("layered_strategy") or "").strip()
    assert isinstance(profile.get("segment_overrides"), list) and profile.get("segment_overrides")


def test_writeback_online_learning_profile_returns_error_for_missing_root(tmp_path: Path) -> None:
    report = writeback_online_learning_profile(
        graph_root=tmp_path / "missing",
        node_feedback={"NODE-1": {"hit_count": 1}},
    )
    assert report["ok"] is False
    assert report["error"] == "graph_root_not_found"
