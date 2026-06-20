from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase2_final_review_issue_list import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase2e_final_review_issue_list_snapshot,
    dump_phase2e_final_review_issue_list_json,
    format_phase2e_final_review_issue_list_report,
)


def _valid_fixture() -> dict:
    return {
        "project_metadata": {
            "project_id": "demo-phase2e",
            "project_name": "Synthetic municipal road final review demo",
            "project_type": "municipal_road",
            "location": "Hefei synthetic district",
            "sanitized_demo": True,
            "real_business_material": False,
        },
        "tender_metadata": {
            "tender_doc_ref": "synthetic-ref",
            "tender_doc_version": "synthetic-v1",
            "evaluation_method": "synthetic scoring",
            "source_kind": "mock_metadata",
        },
        "scoring_item_metadata": [
            {
                "item_id": "score-traffic",
                "item_name": "Traffic organization",
                "scoring_category": "construction_organization",
                "max_score": 12,
                "requirement_summary": "Synthetic traffic response.",
                "response_strategy": "Map staged diversion metadata to response sections.",
                "evidence_needed": ["traffic plan metadata"],
                "related_engineering_object_ids": ["obj-road"],
                "qingtian_keywords": ["traffic_diversion"],
                "qingtian_parse_tags": ["scoring_clause"],
            }
        ],
        "engineering_object_metadata": [
            {
                "object_id": "obj-road",
                "object_type": "municipal_road_segment",
                "object_name": "Synthetic road",
                "synthetic_scope_summary": "Synthetic staged road works.",
            }
        ],
        "risk_clue_metadata": [
            {
                "risk_id": "risk-traffic-binding",
                "risk_type": "traffic_organization",
                "risk_title": "Traffic continuity",
                "risk_category": "traffic_organization",
                "risk_level": "medium",
                "risk_clue_id": "risk-traffic",
                "risk_hint": "Synthetic peak diversion risk.",
                "related_engineering_object_ids": ["obj-road"],
                "linked_engineering_object_ids": ["obj-road"],
                "linked_scoring_item_ids": ["score-traffic"],
                "response_control_points": ["verify staged diversion metadata"],
                "required_evidence": ["traffic plan metadata"],
                "qingtian_tags": ["traffic_diversion"],
                "expected_response_mode": "risk_control_verification",
            }
        ],
        "qingtian_checklist_metadata": [
            {
                "checklist_id": "check-traffic",
                "checklist_title": "Traffic checklist",
                "checklist_category": "ai_parseability",
                "linked_scoring_item_ids": ["score-traffic"],
                "linked_engineering_object_ids": ["obj-road"],
                "linked_risk_ids": ["risk-traffic-binding"],
                "qingtian_keywords": ["traffic_diversion"],
                "qingtian_parse_tags": ["scoring_clause"],
                "evidence_requirements": ["traffic plan metadata"],
                "traceability_requirements": ["phase2b:score-traffic", "phase2c:risk-traffic-binding"],
                "diagnosable_failure_reason": "missing traffic evidence anchors",
                "severity": "medium",
                "affects_score": False,
                "official_score_claim": False,
            }
        ],
        "final_review_issue_metadata": [
            {
                "issue_id": "issue-contract-pass",
                "issue_title": "Business input contract is reviewable",
                "issue_category": "contract_completeness",
                "severity": "info",
                "source_phase": "P2A",
                "linked_scoring_item_ids": ["score-traffic"],
                "linked_engineering_object_ids": ["obj-road"],
                "linked_risk_ids": [],
                "linked_checklist_ids": [],
                "issue_reason": "Synthetic business input contains the required review metadata.",
                "diagnostic_evidence": ["phase2a contract status is PASS"],
                "recommended_action": "Keep the static contract as preview evidence only.",
                "responsible_review_role": "technical_reviewer",
                "review_status": "pass_static",
                "blocking_level": "pass",
                "formal_writeback_allowed": False,
                "export_allowed": False,
                "official_score_claim": False,
            },
            {
                "issue_id": "issue-traffic-warning",
                "issue_title": "Traffic evidence requires human trace review",
                "issue_category": "evidence_traceability",
                "severity": "medium",
                "source_phase": "P2D",
                "linked_scoring_item_ids": ["score-traffic"],
                "linked_engineering_object_ids": ["obj-road"],
                "linked_risk_ids": ["risk-traffic-binding"],
                "linked_checklist_ids": ["check-traffic"],
                "issue_reason": "Qingtian-friendly tags are present but still require manual evidence review.",
                "diagnostic_evidence": ["check-traffic links score, object, risk, and evidence tags"],
                "recommended_action": "Review traffic evidence anchors before any later export gate.",
                "responsible_review_role": "qingtian_parseability_reviewer",
                "review_status": "warning_static",
                "blocking_level": "warning",
                "formal_writeback_allowed": False,
                "export_allowed": False,
                "official_score_claim": False,
            },
            {
                "issue_id": "issue-formal-gate-blocked",
                "issue_title": "Formal writeback and export remain blocked",
                "issue_category": "hard_gate_boundary",
                "severity": "blocking",
                "source_phase": "cross_phase",
                "linked_scoring_item_ids": ["score-traffic"],
                "linked_engineering_object_ids": ["obj-road"],
                "linked_risk_ids": ["risk-traffic-binding"],
                "linked_checklist_ids": ["check-traffic"],
                "issue_reason": "The final review issue list is preview-only and cannot become a formal result.",
                "diagnostic_evidence": ["formal_writeback_allowed=false", "export_allowed=false"],
                "recommended_action": "Open a separate hard gate before real docs, export, or writeback.",
                "responsible_review_role": "final_review_controller",
                "review_status": "blocking_static",
                "blocking_level": "blocking",
                "formal_writeback_allowed": False,
                "export_allowed": False,
                "official_score_claim": False,
            },
        ],
        "output_intent_metadata": {
            "intended_outputs": ["final_review_issue_list_static_snapshot"],
            "export_requested": False,
            "formal_writeback_requested": False,
        },
        "audit_boundary_metadata": {
            "snapshot_id": "phase2e-fixture",
            "schema_version": "phase2e.final_review_issue_list.v1",
            "input_hash_mode": "deterministic_fixture_hash_later_gate",
            "requires_human_review": True,
        },
        "qingtian_ai_review_metadata": {
            "evaluation_friendly": True,
            "scoring_clause_refs_required": True,
            "evidence_anchor_required": True,
            "preview_advisory_not_evidence": True,
            "connects_real_qingtian_system": False,
        },
        "safety_boundary": {
            "runtime_allowed": False,
            "endpoint_access_allowed": False,
            "launcher_allowed": False,
            "held_config_body_read_allowed": False,
            "real_business_doc_body_allowed": False,
            "secret_body_allowed": False,
            "fetch_pull_merge_push_allowed": False,
            "export_allowed": False,
            "formal_writeback_allowed": False,
        },
    }


def _write_fixture(root: Path, data: dict) -> Path:
    path = root / "fixture.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class Phase2FinalReviewIssueListTest(unittest.TestCase):
    def test_phase2e_final_review_issue_list_passes_for_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["failures"], [])
        self.assertEqual(snapshot["phase2a_contract"]["status"], "PASS_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC")
        self.assertEqual(snapshot["phase2b_matrix"]["status"], "PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC")
        self.assertEqual(snapshot["phase2c_binding"]["status"], "PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC")
        self.assertEqual(snapshot["phase2d_checklist"]["status"], "PASS_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC")
        self.assertEqual(snapshot["issue_summary"]["row_count"], 3)
        self.assertEqual(snapshot["issue_summary"]["blocking_level_counts"]["pass"], 1)
        self.assertEqual(snapshot["issue_summary"]["blocking_level_counts"]["warning"], 1)
        self.assertEqual(snapshot["issue_summary"]["blocking_level_counts"]["blocking"], 1)
        self.assertIs(snapshot["scope"]["preview_only"], True)
        self.assertIs(snapshot["scope"]["formal_writeback_performed"], False)
        self.assertIs(snapshot["scope"]["export_performed"], False)
        self.assertIs(snapshot["scope"]["generates_official_score"], False)
        self.assertEqual(snapshot["official_score_blocking"]["official_score_like_paths"], [])
        self.assertEqual(snapshot["forbidden_actions_performed"], [])

    def test_phase2e_final_review_issue_list_blocks_duplicate_issue_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][1]["issue_id"] = "issue-contract-pass"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("issue_ids_unique", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_invalid_severity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["severity"] = "critical"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("severity_values_valid", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_unknown_scoring_item_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["linked_scoring_item_ids"] = ["score-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_scoring_items_known", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_unknown_engineering_object_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][1]["linked_engineering_object_ids"] = ["obj-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_engineering_objects_known", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_unknown_risk_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][1]["linked_risk_ids"] = ["risk-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_risks_known", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_unknown_checklist_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][1]["linked_checklist_ids"] = ["check-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_checklists_known", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_missing_diagnostic_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["diagnostic_evidence"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("diagnostic_evidence_present", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_missing_recommended_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["recommended_action"] = " "
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("recommended_action_present", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_formal_writeback_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["formal_writeback_allowed"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("formal_writeback_allowed_false", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_export_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["export_allowed"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("export_allowed_false", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_official_score_claim_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["official_score_claim"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("official_score_claim_false", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_score_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["final_review_issue_metadata"][0]["official_evaluation_score"] = 99
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_official_score_like_fields", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_real_doc_body_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["tender_metadata"]["tender_body"] = "synthetic text is still not allowed under this key"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_real_doc_body_like_fields", snapshot["failures"])

    def test_phase2e_final_review_issue_list_blocks_secret_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["audit_boundary_metadata"]["api_key"] = "placeholder"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_secret_like_fields", snapshot["failures"])

    def test_phase2e_final_review_issue_list_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            first = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)
            second = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        self.assertEqual(
            dump_phase2e_final_review_issue_list_json(first),
            dump_phase2e_final_review_issue_list_json(second),
        )

    def test_phase2e_final_review_issue_list_report_includes_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())
            snapshot = build_phase2e_final_review_issue_list_snapshot(root, fixture_path=fixture)

        report = format_phase2e_final_review_issue_list_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC", report)
        self.assertIn("formal_writeback_performed: False", report)
        self.assertIn("export_performed: False", report)
        self.assertIn("official_score_generated: False", report)
        self.assertIn("next_gate: PHASE2F_OUTPUT_PRE_INDEX_PLAN_OR_WRITE_GATE", report)


if __name__ == "__main__":
    unittest.main()
