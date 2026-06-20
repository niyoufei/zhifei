from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase1_demo_workflow import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase1b_demo_workflow_snapshot,
    format_phase1b_demo_workflow_report,
)


PASS_P0 = {"status": "PASS_P0_READINESS_STATIC", "failures": []}
NO_GO_P0 = {"status": "NO-GO_P0_READINESS_STATIC", "failures": ["worktree_not_clean"]}


def _write_demo_project(root: Path, *, sanitized_demo: bool = True) -> None:
    path = root / "projects/_demo_p0/project.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "metadata": {
                    "sanitized_demo": sanitized_demo,
                    "real_business_material": False,
                    "external_network_required": False,
                    "secret_required": False,
                    "safe_to_commit": True,
                },
                "topic": "Sanitized municipal drainage demo",
                "project_id": "demo-p0-sanitized-municipal-drainage",
                "requirements": ["Use sanitized metadata only."],
                "plan": {
                    "outline": [
                        "Project overview",
                        "Key and difficult works",
                        "Final review checklist",
                    ],
                    "chapter_requirements": {
                        "Final review checklist": ["Check static delivery readiness."]
                    },
                },
            }
        ),
        encoding="utf-8",
    )


class Phase1DemoWorkflowTest(unittest.TestCase):
    def test_phase1b_demo_workflow_passes_for_sanitized_demo_and_p0_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_demo_project(root)

            snapshot = build_phase1b_demo_workflow_snapshot(root, p0_snapshot=PASS_P0)

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["runs_launcher"], False)
        self.assertIs(snapshot["scope"]["reads_held_config_content"], False)
        self.assertEqual(snapshot["output_index"]["materialized_outputs"], [])
        self.assertIs(snapshot["output_index"]["runtime_gate_required"], True)
        self.assertIn("Phase 1C readiness / delivery index", snapshot["next_gate"])

    def test_phase1b_demo_workflow_requires_sanitized_demo_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_demo_project(root, sanitized_demo=False)

            snapshot = build_phase1b_demo_workflow_snapshot(root, p0_snapshot=PASS_P0)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("demo_contract_valid", snapshot["failures"])

    def test_phase1b_demo_workflow_requires_p0_static_readiness_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_demo_project(root)

            snapshot = build_phase1b_demo_workflow_snapshot(root, p0_snapshot=NO_GO_P0)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("p0_readiness_static_pass", snapshot["failures"])
        self.assertEqual(snapshot["p0_readiness"]["failures"], ["worktree_not_clean"])

    def test_phase1b_demo_workflow_report_includes_runtime_gate_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_demo_project(root)
            snapshot = build_phase1b_demo_workflow_snapshot(root, p0_snapshot=PASS_P0)

        report = format_phase1b_demo_workflow_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE1B_DEMO_WORKFLOW_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE1B_DEMO_WORKFLOW_STATIC", report)
        self.assertIn("runtime_gate_required: True", report)
        self.assertIn("forbidden_actions_performed: []", report)


if __name__ == "__main__":
    unittest.main()
