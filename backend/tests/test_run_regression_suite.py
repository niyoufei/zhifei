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
