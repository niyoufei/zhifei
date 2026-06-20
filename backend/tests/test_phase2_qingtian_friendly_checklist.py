from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase2_qingtian_friendly_checklist import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase2d_qingtian_friendly_checklist_snapshot,
    dump_phase2d_qingtian_friendly_checklist_json,
    format_phase2d_qingtian_friendly_checklist_report,
)


def _valid_fixture() -> dict:
    return {
        "project_metadata": {
            "project_id": "demo-phase2d",
            "project_name": "Synthetic municipal road Qingtian checklist demo",
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
                "risk_title": "Traffic continuity",
                "risk_category": "traffic_organization",
                "risk_level": "medium",
                "risk_clue_id": "risk-traffic",
                "risk_hint": "Synthetic peak diversion risk.",
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
        "output_intent_metadata": {
            "intended_outputs": ["qingtian_friendly_static_checklist_snapshot"],
            "export_requested": False,
            "formal_writeback_requested": False,
        },
        "audit_boundary_metadata": {
            "snapshot_id": "phase2d-fixture",
            "schema_version": "phase2d.qingtian_friendly_checklist.v1",
            "input_hash_mode": "deterministic_fixture_hash_later_gate",
            "requires_human_review": True,
        },
        "qingtian_ai_review_metadata": {
            "evaluation_friendly": True,
            "scoring_clause_refs_required": True,
            "evidence_anchor_required": True,
            "preview_advisory_not_evidence": True,
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


class Phase2QingtianFriendlyChecklistTest(unittest.TestCase):
    def test_phase2d_qingtian_friendly_checklist_passes_for_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["failures"], [])
        self.assertEqual(snapshot["checklist_summary"]["row_count"], 1)
        self.assertEqual(snapshot["checklist_rows"][0]["checklist_id"], "check-traffic")
        self.assertEqual(snapshot["checklist_rows"][0]["checklist_status"], "ready_static")
        self.assertEqual(snapshot["phase2b_matrix"]["status"], "PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC")
        self.assertEqual(snapshot["phase2c_binding"]["status"], "PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC")
        self.assertIs(snapshot["scope"]["preview_only"], True)
        self.assertIs(snapshot["scope"]["connects_real_qingtian_system"], False)
        self.assertIs(snapshot["scope"]["generates_official_score"], False)
        self.assertEqual(snapshot["official_score_blocking"]["official_score_like_paths"], [])
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["reads_held_config_content"], False)
        self.assertIs(snapshot["fixture"]["real_business_doc_body_read"], False)

    def test_phase2d_qingtian_friendly_checklist_blocks_missing_qingtian_keywords(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["qingtian_keywords"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("qingtian_keywords_present", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_missing_qingtian_parse_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["qingtian_parse_tags"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("qingtian_parse_tags_present", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_missing_evidence_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["evidence_requirements"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("evidence_requirements_present", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_missing_traceability_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["traceability_requirements"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("traceability_requirements_present", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_unknown_scoring_item_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["linked_scoring_item_ids"] = ["score-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_scoring_items_known", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_unknown_engineering_object_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["linked_engineering_object_ids"] = ["obj-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_engineering_objects_known", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_unknown_risk_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["linked_risk_ids"] = ["risk-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_risks_known", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_affects_score_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["affects_score"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("affects_score_false", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_official_score_claim_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["official_score_claim"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("official_score_claim_false", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_score_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["qingtian_checklist_metadata"][0]["official_evaluation_score"] = 99
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_official_score_like_fields", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_real_doc_body_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["tender_metadata"]["tender_body"] = "synthetic text is still not allowed under this key"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_real_doc_body_like_fields", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_blocks_secret_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["audit_boundary_metadata"]["api_key"] = "placeholder"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_secret_like_fields", snapshot["failures"])

    def test_phase2d_qingtian_friendly_checklist_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            first = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)
            second = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        self.assertEqual(
            dump_phase2d_qingtian_friendly_checklist_json(first),
            dump_phase2d_qingtian_friendly_checklist_json(second),
        )

    def test_phase2d_qingtian_friendly_checklist_report_includes_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())
            snapshot = build_phase2d_qingtian_friendly_checklist_snapshot(root, fixture_path=fixture)

        report = format_phase2d_qingtian_friendly_checklist_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC", report)
        self.assertIn("score_generation_performed: False", report)
        self.assertIn("next_gate: PHASE2E_FINAL_REVIEW_ISSUE_LIST_PLAN_OR_WRITE_GATE", report)


if __name__ == "__main__":
    unittest.main()
