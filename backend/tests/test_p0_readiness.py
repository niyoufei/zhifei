from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence

from backend.zhifei_autoplan.p0_readiness import (
    build_p0_readiness_snapshot,
    format_p0_readiness_report,
)


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_git_runner(root: Path, args: Sequence[str]) -> dict[str, Any]:
    values = {
        ("branch", "--show-current"): "main\n",
        ("rev-parse", "HEAD"): "9f12e69420fbbf41730bc4f7b8ccdad5552aa464\n",
        ("rev-parse", "--show-toplevel"): f"{root}\n",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"): "origin/main\n",
        ("rev-parse", "@{u}"): "9f12e69420fbbf41730bc4f7b8ccdad5552aa464\n",
        ("status", "--porcelain=v1", "--untracked-files=all"): "",
    }
    return {"returncode": 0, "stdout": values.get(tuple(args), ""), "stderr": ""}


def _fake_dirty_git_runner(root: Path, args: Sequence[str]) -> dict[str, Any]:
    if tuple(args) == ("status", "--porcelain=v1", "--untracked-files=all"):
        return {"returncode": 0, "stdout": " M README.md\n?? backend/tests/test_p0_readiness.py\n", "stderr": ""}
    return _fake_git_runner(root, args)


def _make_minimal_root(root: Path) -> None:
    for rel in (
        "backend/app/main.py",
        "app.py",
        "tactical_dashboard.py",
        "local_launcher/v1/README.md",
        "local_launcher/v1/launcher-state.json",
        "scripts/run_web_ui.sh",
        "scripts/smoke_api.py",
        "pytest.ini",
        "requirements.txt",
    ):
        _write(root / rel, "placeholder\n")

    _write(root / "backend/app/routers/auth.py", "placeholder\n")
    _write(root / "backend/auth_store.py", "placeholder\n")
    _write(root / "data/uploads/.keep", "")
    _write(root / "backend/data/audit/.keep", "")
    _write(root / "build/clawdbot/.keep", "")
    _write(root / "知识图谱/.keep", "")
    _write(
        root / "projects/_demo_p0/project.json",
        json.dumps(
            {
                "metadata": {
                    "sanitized_demo": True,
                    "external_network_required": False,
                    "real_business_material": False,
                },
                "project_id": "demo-p0",
                "requirements": ["static only"],
                "plan": {"outline": ["overview"]},
            }
        ),
    )


class P0ReadinessTest(unittest.TestCase):
    def test_p0_readiness_passes_for_static_clean_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_root(root)

            snapshot = build_p0_readiness_snapshot(root, git_runner=_fake_git_runner)

        self.assertEqual(snapshot["status"], "PASS_P0_READINESS_STATIC")
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["reads_real_business_content"], False)
        self.assertIs(snapshot["git"]["network_refreshed"], False)
        self.assertIs(snapshot["required_entries"]["all_present"], True)
        self.assertIs(snapshot["demo_project"]["valid"], True)
        self.assertIs(snapshot["real_data_dirs"]["content_read_performed"], False)
        self.assertIs(snapshot["sensitive_files_handling"]["content_read_performed"], False)

    def test_p0_readiness_reports_sensitive_paths_by_category_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_root(root)

            snapshot = build_p0_readiness_snapshot(root, git_runner=_fake_git_runner)

        detected = snapshot["sensitive_files_handling"]["paths_detected"]
        self.assertIn(
            {"path": "backend/auth_store.py", "category": "auth_source", "content_read": False},
            detected,
        )
        self.assertIn(
            {"path": "backend/app/routers/auth.py", "category": "auth_source", "content_read": False},
            detected,
        )

    def test_p0_readiness_blocks_missing_demo_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_root(root)
            (root / "projects/_demo_p0/project.json").unlink()

            snapshot = build_p0_readiness_snapshot(root, git_runner=_fake_git_runner)

        self.assertEqual(snapshot["status"], "NO-GO_P0_READINESS_STATIC")
        self.assertIn("sanitized_demo_project_missing_or_invalid", snapshot["failures"])

    def test_p0_readiness_blocks_dirty_worktree_porcelain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_root(root)

            snapshot = build_p0_readiness_snapshot(root, git_runner=_fake_dirty_git_runner)

        self.assertEqual(snapshot["status"], "NO-GO_P0_READINESS_STATIC")
        self.assertIn("worktree_not_clean", snapshot["failures"])
        self.assertIs(snapshot["git"]["worktree_clean"], False)
        self.assertIs(snapshot["git"]["status_porcelain_nonempty"], True)

    def test_format_p0_readiness_report_includes_gate_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_minimal_root(root)
            snapshot = build_p0_readiness_snapshot(root, git_runner=_fake_git_runner)

        report = format_p0_readiness_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_P0_READINESS_STATIC_REPORT", report)
        self.assertIn("status: PASS_P0_READINESS_STATIC", report)
        self.assertIn("next_gate: P0 controlled runtime/endpoint smoke gate", report)


if __name__ == "__main__":
    unittest.main()
