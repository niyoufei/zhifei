from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.project_feedback_learning import update_feedback_memory


def test_update_feedback_memory_accumulates_node_stats(tmp_path: Path) -> None:
    out = tmp_path / "feedback.json"
    payload = {
        "intercepted": False,
        "sentence_evidence_stats": {"trace_coverage_ratio": 0.9},
        "sections": [
            {
                "title": "质量",
                "specialist_domain": "building",
                "content": "阈值=95%，每班次检查2次，偏差处置时限=4h。",
                "source_trace": {"node_id": "node_uid_abc", "kg_node_ref": "NODE-1"},
            }
        ],
    }
    first = update_feedback_memory(result_payload=payload, output_path=out)
    second = update_feedback_memory(result_payload=payload, output_path=out)
    assert first["ok"] is True and second["ok"] is True

    data = json.loads(out.read_text(encoding="utf-8"))
    node = data["nodes"]["NODE-1"]
    assert int(node.get("hit_count") or 0) == 2
    assert int(node.get("pass_count") or 0) == 2
    assert float(node.get("pass_rate") or 0.0) == 1.0
    assert int((node.get("recommended_defaults") or {}).get("inspection_frequency_per_shift") or 0) == 2


def test_update_feedback_memory_writes_back_to_kg_nodes(tmp_path: Path) -> None:
    out = tmp_path / "feedback.json"
    kg_root = tmp_path / "kg"
    kg_root.mkdir(parents=True, exist_ok=True)
    kg_file = kg_root / "ZF-KG-01-Test.json"
    kg_file.write_text(
        json.dumps(
            {
                "name": "ZF-KG-01-Test",
                "knowledge_database": {
                    "sec": {
                        "nodes": [
                            {
                                "node_id": "NODE-1",
                                "name": "质量节点",
                                "online_learning_profile": {"enabled": True, "strategy": "ema_feedback_v1"},
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

    payload = {
        "intercepted": False,
        "sentence_evidence_stats": {"trace_coverage_ratio": 0.85},
        "sections": [
            {
                "title": "质量",
                "specialist_domain": "building",
                "content": "阈值=95%，每班次检查2次，偏差处置时限=4h。",
                "source_trace": {"node_id": "NODE-1"},
            }
        ],
    }
    result = update_feedback_memory(
        result_payload=payload,
        output_path=out,
        writeback_graph=True,
        graph_root=kg_root,
    )
    assert result["ok"] is True
    writeback = result.get("writeback") or {}
    assert writeback.get("triggered") is True
    assert writeback.get("ok") is True
    assert int(writeback.get("nodes_updated") or 0) == 1

    updated = json.loads(kg_file.read_text(encoding="utf-8"))
    node = updated["knowledge_database"]["sec"]["nodes"][0]
    profile = node.get("online_learning_profile") or {}
    assert int(profile.get("hit_count") or 0) == 1
    assert int(profile.get("pass_count") or 0) == 1
    assert float(profile.get("trace_coverage_avg") or 0.0) == 0.85
    assert float(profile.get("pass_rate") or 0.0) == 1.0
    assert str(profile.get("last_feedback_at") or "").strip()


def test_update_feedback_memory_supports_review_decisions(tmp_path: Path) -> None:
    out = tmp_path / "feedback.json"
    payload = {
        "intercepted": False,
        "sentence_evidence_stats": {"trace_coverage_ratio": 0.8},
        "sections": [{"title": "质量", "specialist_domain": "building", "content": "每班次检查2次。", "source_trace": {"node_id": "NODE-2"}}],
        "review_decisions": [
            {"node_id": "NODE-2", "decision": "accept", "note": "参数准确"},
            {"node_id": "NODE-2", "decision": "modify", "corrected_values": {"inspection_frequency_per_shift": 3}},
        ],
    }
    result = update_feedback_memory(result_payload=payload, output_path=out)
    assert result["ok"] is True
    assert int(result.get("decision_updates") or 0) == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    node = data["nodes"]["NODE-2"]
    assert int(node.get("accepted_count") or 0) == 1
    assert int(node.get("modified_count") or 0) == 1
    assert int(node.get("decision_total") or 0) == 2
    assert str(node.get("last_decision") or "") == "modify"
    assert int((node.get("recommended_defaults") or {}).get("inspection_frequency_per_shift") or 0) == 3
