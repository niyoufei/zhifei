from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.zhifei_autoplan.phase2_output_pre_index import (
    NO_GO_STATUS,
    PASS_STATUS,
    build_phase2f_output_pre_index_snapshot,
    dump_phase2f_output_pre_index_json,
    format_phase2f_output_pre_index_report,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = REPO_ROOT / "projects/_demo_phase2_output_pre_index/project.json"


def _valid_fixture() -> dict:
    return json.loads(DEFAULT_FIXTURE.read_text(encoding="utf-8"))


def _write_fixture(root: Path, data: dict) -> Path:
    path = root / "fixture.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class Phase2OutputPreIndexTest(unittest.TestCase):
    def test_phase2f_output_pre_index_passes_for_synthetic_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], PASS_STATUS)
        self.assertEqual(snapshot["failures"], [])
        self.assertEqual(snapshot["phase2a_contract"]["status"], "PASS_PHASE2A_BUSINESS_INPUT_CONTRACT_STATIC")
        self.assertEqual(snapshot["phase2b_matrix"]["status"], "PASS_PHASE2B_SCORING_RESPONSE_MATRIX_STATIC")
        self.assertEqual(snapshot["phase2c_binding"]["status"], "PASS_PHASE2C_RISK_OBJECT_BINDING_STATIC")
        self.assertEqual(snapshot["phase2d_checklist"]["status"], "PASS_PHASE2D_QINGTIAN_FRIENDLY_CHECKLIST_STATIC")
        self.assertEqual(snapshot["phase2e_issue_list"]["status"], "PASS_PHASE2E_FINAL_REVIEW_ISSUE_LIST_STATIC")
        self.assertEqual(snapshot["output_summary"]["row_count"], 7)
        self.assertEqual(set(snapshot["output_type_enum"]), set(snapshot["output_summary"]["output_type_counts"]))
        self.assertEqual(snapshot["forbidden_actions_performed"], [])
        self.assertIs(snapshot["scope"]["preview_only"], True)
        self.assertIs(snapshot["scope"]["export_performed"], False)
        self.assertIs(snapshot["scope"]["artifact_generation_performed"], False)
        self.assertIs(snapshot["scope"]["formal_writeback_performed"], False)
        self.assertIs(snapshot["scope"]["official_score_generated"], False)

    def test_phase2f_output_pre_index_blocks_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            del data["output_pre_index_metadata"][0]["output_id"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("required_output_entry_fields_present", snapshot["failures"])
        self.assertTrue(any("output_id" in item for item in snapshot["validation_errors"]))

    def test_phase2f_output_pre_index_blocks_invalid_output_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["output_type"] = "formal_export_bundle"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("output_types_valid", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_export_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["export_status"] = "generated"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("export_status_allowed", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_artifact_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["artifact_generation_status"] = "generated"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("artifact_generation_not_generated", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_formal_writeback_performed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["writeback_status"] = "performed"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("writeback_not_performed", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_official_score_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["official_score_status"] = "generated"
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("official_score_not_generated", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_held_config_body_read_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["data_boundary"]["held_config_body_read"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("data_boundary_blocks_forbidden_reads", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_real_business_doc_body_read_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["data_boundary"]["real_business_doc_body_read"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("data_boundary_blocks_forbidden_reads", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_runtime_endpoint_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["data_boundary"]["runtime_started"] = True
            data["output_pre_index_metadata"][0]["data_boundary"]["endpoint_accessed"] = True
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("data_boundary_blocks_forbidden_reads", snapshot["failures"])

    def test_phase2f_output_pre_index_blocks_missing_trace_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _valid_fixture()
            data["output_pre_index_metadata"][0]["trace_links"] = ["phase2e:missing-issue"]
            fixture = _write_fixture(root, data)

            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(snapshot["status"], NO_GO_STATUS)
        self.assertIn("trace_links_known", snapshot["failures"])

    def test_phase2f_output_pre_index_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())

            first = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)
            second = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        self.assertEqual(
            dump_phase2f_output_pre_index_json(first),
            dump_phase2f_output_pre_index_json(second),
        )

    def test_phase2f_output_pre_index_report_includes_static_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())
            snapshot = build_phase2f_output_pre_index_snapshot(root, fixture_path=fixture)

        report = format_phase2f_output_pre_index_report(snapshot)

        self.assertIn("OPENCLAW_ZHIFEI_DOC_PHASE2F_OUTPUT_PRE_INDEX_STATIC_REPORT", report)
        self.assertIn("status: PASS_PHASE2F_OUTPUT_PRE_INDEX_STATIC", report)
        self.assertIn("artifact_generation_performed: False", report)
        self.assertIn("formal_writeback_performed: False", report)
        self.assertIn("export_performed: False", report)
        self.assertIn("official_score_generated: False", report)

    def test_phase2f_cli_preview_does_not_write_artifact_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixture = _write_fixture(root, _valid_fixture())
            before = _artifact_paths(root)
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["PYTHONPATH"] = str(REPO_ROOT)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts/phase2_output_pre_index.py"),
                    "--root",
                    str(root),
                    "--fixture",
                    str(fixture),
                    "--json",
                ],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            after = _artifact_paths(root)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS_PHASE2F_OUTPUT_PRE_INDEX_STATIC", result.stdout)
        self.assertEqual(before, after)


def _artifact_paths(root: Path) -> set[Path]:
    artifact_suffixes = {".docx", ".pdf", ".xlsx", ".pptx", ".html", ".md"}
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in artifact_suffixes
    }


if __name__ == "__main__":
    unittest.main()
