from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase2_risk_object_binding import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase2c_risk_object_binding_snapshot,
    dump_phase2c_risk_object_binding_json,
    format_phase2c_risk_object_binding_report,
)


def _valid_fixture() -> dict:
    return {
        "project_metadata": {
            "project_id": "demo-phase2c",
            "project_name": "Synthetic municipal road risk binding demo",
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
        "output_intent_metadata": {
            "intended_outputs": ["risk_object_binding_snapshot"],
            "export_requested": False,
            "formal_writeback_requested": False,
        },
        "audit_boundary_metadata": {
            "snapshot_id": "phase2c-fixture",
            "schema_version": "phase2c.risk_object_binding.v1",
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


class Phase2RiskObjectBindingTest(unittest.TestCase):
    def test_phase2c_risk_object_binding_passes_for_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["failures"], [])
        self.assertEqual(snapshot["binding_summary"]["row_count"], 1)
        self.assertEqual(snapshot["binding_rows"][0]["risk_id"], "risk-traffic-binding")
        self.assertEqual(snapshot["binding_rows"][0]["binding_status"], "ready_static")
        self.assertEqual(snapshot["phase2b_matrix"]["status"], "PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC")
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["reads_held_config_content"], False)
        self.assertIs(snapshot["fixture"]["real_business_doc_body_read"], False)

    def test_phase2c_risk_object_binding_blocks_missing_risk_clue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("risk_clues_present", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_duplicate_risk_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"].append(dict(data["risk_clue_metadata"][0]))
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("risk_ids_unique", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_invalid_risk_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"][0]["risk_level"] = "urgent"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("risk_levels_valid", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_unknown_engineering_object_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"][0]["linked_engineering_object_ids"] = ["obj-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_engineering_objects_known", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_unknown_scoring_item_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"][0]["linked_scoring_item_ids"] = ["score-missing"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("linked_scoring_items_known", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_missing_response_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"][0]["response_control_points"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("response_control_points_present", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_missing_required_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"][0]["required_evidence"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("required_evidence_present", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_missing_qingtian_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["risk_clue_metadata"][0]["qingtian_tags"] = []
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("qingtian_tags_present", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_real_doc_body_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["tender_metadata"]["tender_body"] = "synthetic text is still not allowed under this key"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_real_doc_body_like_fields", snapshot["failures"])

    def test_phase2c_risk_object_binding_blocks_secret_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["audit_boundary_metadata"]["api_key"] = "placeholder"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_secret_like_fields", snapshot["failures"])

    def test_phase2c_risk_object_binding_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            first = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)
            second = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        self.assertEqual(dump_phase2c_risk_object_binding_json(first), dump_phase2c_risk_object_binding_json(second))

    def test_phase2c_risk_object_binding_report_includes_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())
            snapshot = build_phase2c_risk_object_binding_snapshot(root, fixture_path=fixture)

        report = format_phase2c_risk_object_binding_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE2C_RISK_OBJECT_BINDING_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC", report)
        self.assertIn("next_gate: PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_PLAN_OR_WRITE_GATE", report)


if __name__ == "__main__":
    unittest.main()
