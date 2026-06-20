from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase2_business_input_contract import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase2a_business_input_contract_snapshot,
    format_phase2a_business_input_contract_report,
)


def _valid_fixture() -> dict:
    return {
        "project_metadata": {
            "project_id": "demo-phase2a",
            "project_name": "Synthetic municipal road demo",
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
                "max_score": 12,
                "requirement_summary": "Synthetic traffic response.",
                "evidence_needed": ["traffic plan metadata"],
                "related_engineering_object_ids": ["obj-road"],
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
                "risk_id": "risk-traffic",
                "risk_type": "traffic_continuity",
                "risk_hint": "Synthetic peak diversion risk.",
                "related_engineering_object_ids": ["obj-road"],
                "expected_response_mode": "risk_control_verification",
            }
        ],
        "output_intent_metadata": {
            "intended_outputs": ["business_input_contract_snapshot"],
            "export_requested": False,
            "formal_writeback_requested": False,
        },
        "audit_boundary_metadata": {
            "snapshot_id": "phase2a-fixture",
            "schema_version": "phase2a.business_input_contract.v1",
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


class Phase2BusinessInputContractTest(unittest.TestCase):
    def test_phase2a_business_input_contract_passes_for_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            snapshot = build_phase2a_business_input_contract_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["failures"], [])
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["starts_runtime"], False)
        self.assertIs(snapshot["scope"]["visits_endpoint"], False)
        self.assertIs(snapshot["scope"]["reads_held_config_content"], False)
        self.assertIs(snapshot["fixture"]["real_business_doc_body_read"], False)

    def test_phase2a_business_input_contract_blocks_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            del data["tender_metadata"]["evaluation_method"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2a_business_input_contract_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("required_nested_fields_present", snapshot["failures"])

    def test_phase2a_business_input_contract_blocks_real_doc_body_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["tender_metadata"]["tender_body"] = "synthetic text is still not allowed under this key"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2a_business_input_contract_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_real_doc_body_like_fields", snapshot["failures"])

    def test_phase2a_business_input_contract_blocks_secret_like_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["audit_boundary_metadata"]["api_key"] = "placeholder"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2a_business_input_contract_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("no_secret_like_fields", snapshot["failures"])

    def test_phase2a_business_input_contract_blocks_forbidden_action_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["safety_boundary"]["runtime_allowed"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2a_business_input_contract_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("forbidden_action_flags_false", snapshot["failures"])

    def test_phase2a_business_input_contract_report_includes_next_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())
            snapshot = build_phase2a_business_input_contract_snapshot(root, fixture_path=fixture)

        report = format_phase2a_business_input_contract_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC", report)
        self.assertIn("next_gate: PHASE2B_SCORING_RESPONSE_MATRIX_PLAN_OR_WRITE_GATE", report)


if __name__ == "__main__":
    unittest.main()
