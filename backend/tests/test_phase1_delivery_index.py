from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase1_delivery_index import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase1c_delivery_index_snapshot,
    format_phase1c_delivery_index_report,
)


PASS_P0 = {"status": "PASS_P0_READINESS_STATIC", "failures": []}
NO_GO_P0 = {"status": "NO-GO_P0_READINESS_STATIC", "failures": ["worktree_not_clean"]}
PASS_PHASE1B = {
    "status": "PASS_PHASE1B_DEMO_WORKFLOW_STATIC",
    "failures": [],
    "output_index": {"output_generation_performed": False, "materialized_outputs": []},
}
NO_GO_PHASE1B = {
    "status": "NO-GO_PHASE1B_DEMO_WORKFLOW_STATIC",
    "failures": ["p0_readiness_static_pass"],
    "output_index": {"output_generation_performed": False, "materialized_outputs": []},
}


class Phase1DeliveryIndexTest(unittest.TestCase):
    def test_phase1c_delivery_index_passes_for_p0_and_phase1b_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            snapshot = build_phase1c_delivery_index_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=PASS_PHASE1B,
            )

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["runs_launcher"], False)
        self.assertIs(snapshot["scope"]["reads_held_config_content"], False)
        self.assertIs(snapshot["scope"]["materializes_business_outputs"], False)
        self.assertIn("Phase 1D docs / RUNBOOK closure", snapshot["next_gate"])

    def test_phase1c_delivery_index_blocks_when_p0_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            snapshot = build_phase1c_delivery_index_snapshot(
                root,
                p0_snapshot=NO_GO_P0,
                phase1b_snapshot=PASS_PHASE1B,
            )

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("p0_readiness_static_pass", snapshot["failures"])

    def test_phase1c_delivery_index_blocks_when_phase1b_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            snapshot = build_phase1c_delivery_index_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=NO_GO_PHASE1B,
            )

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("phase1b_static_demo_workflow_pass", snapshot["failures"])

    def test_phase1c_delivery_index_includes_static_artifact_rules_and_hard_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = build_phase1c_delivery_index_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=PASS_PHASE1B,
            )

        rules = {item["rule_id"]: item for item in snapshot["artifact_index_rules"]}
        gates = {item["action"]: item for item in snapshot["hard_gate_matrix"]}

        self.assertIs(rules["static_evidence_only_before_runtime_gate"]["allowed"], True)
        self.assertIs(rules["no_business_output_materialization"]["allowed"], False)
        self.assertEqual(gates["endpoint_access"]["status"], "blocked_until_manual_gate")
        self.assertEqual(gates["held_config_content_read"]["status"], "blocked_until_manual_gate")

    def test_phase1c_delivery_index_report_includes_evidence_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = build_phase1c_delivery_index_snapshot(
                root,
                p0_snapshot=PASS_P0,
                phase1b_snapshot=PASS_PHASE1B,
            )

        report = format_phase1c_delivery_index_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE1C_READINESS_DELIVERY_INDEX_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE1C_READINESS_DELIVERY_INDEX_STATIC", report)
        self.assertIn("p0_readiness_status: PASS_P0_READINESS_STATIC", report)
        self.assertIn("phase1b_status: PASS_PHASE1B_DEMO_WORKFLOW_STATIC", report)


if __name__ == "__main__":
    unittest.main()
