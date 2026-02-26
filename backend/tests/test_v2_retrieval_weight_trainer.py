from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan.v2.retrieval_weight_trainer import train_retrieval_weight_profile


def test_train_retrieval_weight_profile_outputs_weight_file(tmp_path: Path) -> None:
    benchmark = {
        "total_cases": 20,
        "passed_cases": 10,
        "failed_cases": 10,
        "pass_rate": 0.5,
        "avg_mrr": 0.32,
    }
    feedback = {
        "nodes": {
            "N-1": {"pass_rate": 0.62, "trace_coverage_avg": 0.71},
            "N-2": {"pass_rate": 0.66, "trace_coverage_avg": 0.68},
        }
    }
    out = tmp_path / "weights.json"
    result = train_retrieval_weight_profile(
        benchmark_report=benchmark,
        feedback_memory=feedback,
        output_path=out,
    )

    assert result["ok"] is True
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    weights = payload.get("weights") or {}
    assert float(weights.get("keyword_exact_weight") or 0.0) > 1.0
    assert float(weights.get("fts_rank_weight") or 0.0) > 1.0
    assert float(weights.get("timeline_weight") or 0.0) >= 1.0
