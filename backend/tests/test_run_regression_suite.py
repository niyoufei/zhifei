from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "run_regression_suite.py"
    spec = importlib.util.spec_from_file_location("run_regression_suite", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detect_project_inputs_prefers_boq_directory(tmp_path: Path) -> None:
    mod = _load_module()
    project = tmp_path / "01_真实项目测试"
    boq_dir = project / "工程量清单"
    boq_dir.mkdir(parents=True, exist_ok=True)
    (project / "招标文件.pdf").write_text("dummy", encoding="utf-8")
    (project / "答疑文件.doc").write_text("dummy", encoding="utf-8")
    (boq_dir / "1.工程量清单汇总表.csv").write_text("boq_code,name,quantity,unit\nA1,土方,10,m3\n", encoding="utf-8")

    info = mod.detect_project_inputs(project)
    assert info
    tenders = info.get("tender_paths") or []
    assert any("招标文件.pdf" in p for p in tenders)
    assert any("答疑文件.doc" in p for p in tenders)
    assert str(info.get("boq_path")).endswith("工程量清单")


def test_discover_projects_filters_non_project_dirs(tmp_path: Path) -> None:
    mod = _load_module()
    # Non-project directory should not be discovered.
    (tmp_path / "backend").mkdir(parents=True, exist_ok=True)

    project = tmp_path / "02_项目回归样本"
    boq_dir = project / "工程量清单"
    boq_dir.mkdir(parents=True, exist_ok=True)
    (project / "招标文件.docx").write_text("dummy", encoding="utf-8")
    (boq_dir / "清单.csv").write_text("boq_code,name,quantity,unit\nA1,模板,12,m2\n", encoding="utf-8")

    projects = mod.discover_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["project_name"] == "02_项目回归样本"


def test_project_gate_rejects_low_sentence_coverage() -> None:
    mod = _load_module()
    row = {
        "project_name": "P1",
        "passed": True,
        "knowledge_gap_count": 0,
        "sentence_trace_coverage": 0.7,
        "boq_failed_file_count": 0,
    }
    gate = {
        "min_sentence_coverage": 0.9,
        "max_gaps_per_project": 0,
        "max_boq_failed_files": 1,
    }
    out = mod._evaluate_project_gate(row, gate)
    assert out["passed"] is False
    assert "sentence_coverage_below_threshold" in (out.get("gate_reasons") or [])


def test_overall_gate_by_pass_rate() -> None:
    mod = _load_module()
    rows = [
        {"gate_passed": True},
        {"gate_passed": False},
        {"gate_passed": True},
    ]
    ok = mod._evaluate_overall_gate(rows, {"min_pass_rate": 0.66})
    bad = mod._evaluate_overall_gate(rows, {"min_pass_rate": 0.67})
    assert ok["ok"] is True
    assert bad["ok"] is False
