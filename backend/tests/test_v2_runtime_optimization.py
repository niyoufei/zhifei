from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.v2.runtime_optimization import (
    build_hit_rate_dashboard,
    write_hit_rate_dashboard,
)


def test_build_hit_rate_dashboard_contains_gate_breakdown_and_boq_metrics(tmp_path: Path) -> None:
    dashboard = build_hit_rate_dashboard(
        index_matrix={"index_matrix": [{"dimension": "质量"}, {"dimension": "安全"}]},
        audit_result={"checks": [{"score_point_total": 6, "score_point_hit": 5}]},
        graph_audit={"checks": [{"ok": True}, {"ok": False}]},
        compliance_audit={"inconsistency_count": 1, "inconsistency_severity": {"blocker": 0, "major": 1, "minor": 0}},
        sentence_evidence_stats={"trace_coverage_ratio": 0.91},
        sections=[
            {"content": "每班次2次抽检，质量员复核。", "graph_hit": {"node_id": "N1", "evidence_strength": {"grade": "A"}}},
            {"content": "安全巡检频次1次/班。", "graph_hit": {"node_id": "N2", "evidence_strength": {"grade": "B"}}},
        ],
        gaps=[
            {"type": "numeric_density_insufficient", "suggested_parameters": ["numeric_sentence_density >= 0.95"]},
            {"type": "retrieval_benchmark_gate_failed", "suggested_parameters": ["提升图谱检索精度与MRR后再发布"]},
        ],
        pre_healing_gap_count=4,
        self_healing={"triggered": True},
        boq_governance={"enabled": True, "trusted": False, "overall_trust_score": 0.64, "trust_threshold": 0.78, "parse_error_rate": 0.12},
    )

    assert isinstance(dashboard.get("gate_breakdown"), dict)
    assert int((dashboard.get("gate_breakdown") or {}).get("numeric_density_insufficient") or 0) >= 1
    metrics = dashboard.get("metrics") or {}
    assert bool(metrics.get("boq_trust_enabled")) is True
    assert float(metrics.get("boq_trust_score") or 0.0) == 0.64
    checks = dashboard.get("checks") or {}
    assert bool(checks.get("boq_trust_ok")) is False
    actions = dashboard.get("recommended_actions") or []
    assert actions

    saved = write_hit_rate_dashboard(
        dashboard=dashboard,
        out_json=tmp_path / "dash.json",
        out_md=tmp_path / "dash.md",
    )
    assert Path(str(saved.get("json_path") or "")).exists()
    md = Path(str(saved.get("md_path") or "")).read_text(encoding="utf-8")
    assert "Gate Breakdown" in md
    assert "Recommended Actions" in md
