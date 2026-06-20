from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase1_static_matrix import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase1e_static_matrix_snapshot,
    format_phase1e_static_matrix_report,
)


PASS_P0 = {"status": "PASS_P0_READINESS_STATIC", "failures": []}
DIRTY_P0 = {"status": "NO-GO_P0_READINESS_STATIC", "failures": ["worktree_not_clean"]}
PASS_PHASE1B = {
    "status": "PASS_PHASE1B_DEMO_WORKFLOW_STATIC",
    "failures": [],
    "output_index": {"output_generation_performed": False, "materialized_outputs": []},
}
PASS_PHASE1C = {"status": "PASS_PHASE1C_READINESS_DELIVERY_INDEX_STATIC", "failures": []}


def _write_docs(root: Path, *, include_phase1e_doc: bool = True) -> None:
    docs = [
        "docs/openclaw-zhifei-doc-p0-readiness.md",
        "docs/openclaw-zhifei-doc-phase1-local-baseline.md",
        "docs/openclaw-zhifei-doc-phase1b-demo-workflow.md",
        "docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md",
        "docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md",
    ]
    if include_phase1e_doc:
        docs.append("docs/openclaw-zhifei-doc-phase1e-static-test-matrix.md")
    for doc in docs:
        path = root / doc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {doc}\n", encoding="utf-8")

    refs = "\n".join(
        [
            "docs/openclaw-zhifei-doc-phase1b-demo-workflow.md",
            "docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md",
            "docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md",
            "docs/openclaw-zhifei-doc-phase1e-static-test-matrix.md",
        ]
    )
    (root / "README.md").write_text(refs, encoding="utf-8")
    runbook = root / "backend/RUNBOOK.md"
    runbook.parent.mkdir(parents=True, exist_ok=True)
    runbook.write_text(refs, encoding="utf-8")
    phase1d = root / "docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md"
    phase1d.write_text(refs, encoding="utf-8")


class Phase1StaticMatrixTest(unittest.TestCase):
    def test_phase1e_static_matrix_passes_for_clean_static_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_docs(root)

            snapshot = build_phase1e_static_matrix_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=PASS_PHASE1B,
                phase1c_snapshot=PASS_PHASE1C,
            )

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["runs_launcher"], False)
        self.assertIs(snapshot["scope"]["reads_held_config_content"], False)
        self.assertIn("PHASE1_LOCAL_STATIC_BASELINE_CLOSEOUT_READONLY", snapshot["next_gate"])

    def test_phase1e_static_matrix_blocks_dirty_p0_but_keeps_dirty_no_go_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_docs(root)

            snapshot = build_phase1e_static_matrix_snapshot(
                root,
                p0_snapshot=DIRTY_P0,
                phase1b_snapshot=PASS_PHASE1B,
                phase1c_snapshot=PASS_PHASE1C,
            )

        matrix_ids = {item["matrix_id"] for item in snapshot["matrix_entries"]}
        diagnostics = {item["failure"] for item in snapshot["failure_diagnostics"]}
        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("p0_readiness_clean_pass", snapshot["failures"])
        self.assertIn("dirty_worktree_no_go_expected", matrix_ids)
        self.assertIn("worktree_not_clean", diagnostics)

    def test_phase1e_static_matrix_requires_docs_presence_and_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_docs(root, include_phase1e_doc=False)

            snapshot = build_phase1e_static_matrix_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=PASS_PHASE1B,
                phase1c_snapshot=PASS_PHASE1C,
            )

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("docs_presence_complete", snapshot["failures"])

    def test_phase1e_static_matrix_report_includes_statuses_and_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_docs(root)
            snapshot = build_phase1e_static_matrix_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=PASS_PHASE1B,
                phase1c_snapshot=PASS_PHASE1C,
            )

        report = format_phase1e_static_matrix_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE1E_STATIC_TEST_MATRIX_REPORT", report)
        self.assertIn("status: PASS_PHASE1E_STATIC_TEST_MATRIX", report)
        self.assertIn("p0_readiness_status: PASS_P0_READINESS_STATIC", report)
        self.assertIn("next_gate: PHASE1_LOCAL_STATIC_BASELINE_CLOSEOUT_READONLY", report)


if __name__ == "__main__":
    unittest.main()
