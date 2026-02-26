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
                "source_trace": {"node_id": "NODE-1"},
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

