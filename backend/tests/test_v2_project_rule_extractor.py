from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.v2.project_rule_extractor import build_project_rule_matrix


def test_build_project_rule_matrix_prefers_qa_source(tmp_path: Path) -> None:
    tender = tmp_path / "招标文件.txt"
    tender.write_text(
        "进度控制应在8小时内完成响应。关键线路工序间隔不小于2天。",
        encoding="utf-8",
    )
    qa = tmp_path / "答疑文件.txt"
    qa.write_text(
        "针对同类问题，以答疑为准：关键线路工序间隔不小于3天。",
        encoding="utf-8",
    )
    matrix = build_project_rule_matrix([str(tender), str(qa)])
    assert matrix["ok"] is True
    assert int(matrix.get("rules_total") or 0) >= 2

    override = (matrix.get("dimension_overrides") or {}).get("进度") or {}
    assert str(override.get("source_type") or "") == "答疑文件"
    assert float(override.get("value") or 0.0) >= 3.0
