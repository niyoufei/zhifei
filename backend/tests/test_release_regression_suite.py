from pathlib import Path

from backend.zhifei_autoplan.release_regression_suite import (
    build_release_regression_command,
    select_release_regression_cases,
    validate_release_regression_suite,
)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("fixture", encoding="utf-8")


def test_validate_release_regression_suite_accepts_existing_files(tmp_path):
    _touch(tmp_path / "scripts" / "run_actions_pipeline.py")
    _touch(tmp_path / "cases" / "tender.pdf")
    _touch(tmp_path / "cases" / "qa.doc")
    _touch(tmp_path / "cases" / "boq.pdf")
    _touch(tmp_path / "cases" / "drawing.pdf")

    validated = validate_release_regression_suite(
        {
            "suite_version": "test-v1",
            "runner": "scripts/run_actions_pipeline.py",
            "release_gate_cases": ["case_a"],
            "cases": [
                {
                    "id": "case_a",
                    "priority": "P0",
                    "release_gate": True,
                    "topic": "样本A",
                    "project_id": "reg_case_a",
                    "generation_mode": "stable_delivery",
                    "variant_id": 1,
                    "logic_template_id": "D",
                    "quality_strict": True,
                    "auto_remediate": False,
                    "strict_tender_outline": True,
                    "outline": ["工程概况", "施工部署"],
                    "tender_files": ["cases/tender.pdf", "cases/qa.doc"],
                    "boq_file": "cases/boq.pdf",
                    "ingest_files": ["cases/drawing.pdf"],
                }
            ],
        },
        root_dir=tmp_path,
    )

    assert validated["ok"] is True
    assert validated["release_gate_cases"] == ["case_a"]
    assert validated["cases"][0]["ingest_files"] == ["cases/drawing.pdf"]
    assert validated["cases"][0]["outline"] == ["工程概况", "施工部署"]
    assert validated["cases"][0]["auto_remediate"] is False
    assert validated["cases"][0]["strict_tender_outline"] is True
    assert validated["cases"][0]["generation_mode"] == "stable_delivery"
    assert validated["cases"][0]["variant_id"] == 1
    assert validated["cases"][0]["logic_template_id"] == "D"


def test_build_release_regression_command_includes_expected_files(tmp_path):
    cmd = build_release_regression_command(
        {
            "id": "case_a",
            "topic": "样本A",
            "project_id": "reg_case_a",
            "generation_mode": "stable_delivery",
            "variant_id": 1,
            "logic_template_id": "E",
            "suggested_timeout_sec": 240,
            "quality_strict": True,
            "auto_remediate": False,
            "strict_tender_outline": True,
            "outline": ["工程概况", "施工部署"],
            "tender_files": ["cases/tender.pdf", "cases/qa.doc"],
            "boq_file": "cases/boq.pdf",
            "ingest_files": ["cases/drawing.pdf"],
        },
        root_dir=tmp_path,
        base_url="http://127.0.0.1:9999",
        dry_run=True,
        download=False,
    )

    assert "--dry-run" in cmd
    assert "--no-download" in cmd
    assert "--quality-strict" in cmd
    assert "--no-auto-remediate" in cmd
    assert "--strict-tender-outline" in cmd
    assert "--generation-mode" in cmd
    assert "--variant-id" in cmd
    assert "--logic-template-id" in cmd
    assert cmd[cmd.index("--generation-mode") + 1] == "stable_delivery"
    assert cmd[cmd.index("--variant-id") + 1] == "1"
    assert cmd[cmd.index("--logic-template-id") + 1] == "E"
    assert "工程概况" in cmd
    assert "施工部署" in cmd
    assert "http://127.0.0.1:9999" in cmd
    assert str((tmp_path / "cases" / "tender.pdf").resolve()) in cmd
    assert str((tmp_path / "cases" / "qa.doc").resolve()) in cmd
    assert str((tmp_path / "cases" / "boq.pdf").resolve()) in cmd
    assert str((tmp_path / "cases" / "drawing.pdf").resolve()) in cmd


def test_select_release_regression_cases_prefers_release_gate_subset():
    validated = {
        "cases": [
            {"id": "a", "release_gate": True},
            {"id": "b", "release_gate": False},
            {"id": "c", "release_gate": True},
        ],
        "release_gate_cases": ["a", "c"],
    }

    out = select_release_regression_cases(validated, release_only=True)

    assert [item["id"] for item in out] == ["a", "c"]


def test_validate_release_regression_suite_rejects_unknown_generation_mode(tmp_path):
    _touch(tmp_path / "scripts" / "run_actions_pipeline.py")
    _touch(tmp_path / "cases" / "tender.pdf")
    _touch(tmp_path / "cases" / "boq.pdf")

    validated = validate_release_regression_suite(
        {
            "suite_version": "test-v1",
            "runner": "scripts/run_actions_pipeline.py",
            "cases": [
                {
                    "id": "case_bad",
                    "topic": "样本B",
                    "project_id": "reg_case_b",
                    "generation_mode": "unknown_mode",
                    "tender_files": ["cases/tender.pdf"],
                    "boq_file": "cases/boq.pdf",
                    "ingest_files": [],
                }
            ],
        },
        root_dir=tmp_path,
    )

    assert validated["ok"] is False
    assert any("generation_mode must be one of" in item for item in validated["errors"])
