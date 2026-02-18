# -*- coding: utf-8 -*-
"""
Unit tests for audit_service.py
"""
import json
import hashlib
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audit_service import (
    _sha256_file,
    _file_meta,
    _safe_read_json,
    _first_str,
    build_audit_report,
)


# ==============================================================================
# TestSha256File
# ==============================================================================
class TestSha256File:
    """Tests for _sha256_file function"""

    def test_none_input(self):
        """None input returns None"""
        assert _sha256_file(None) is None

    def test_non_path_input(self):
        """Non-Path input returns None"""
        assert _sha256_file("string/path") is None
        assert _sha256_file(123) is None
        assert _sha256_file([]) is None

    def test_nonexistent_file(self):
        """Nonexistent file returns None"""
        p = Path("/nonexistent/file/path.txt")
        assert _sha256_file(p) is None

    def test_directory_input(self):
        """Directory path returns None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            assert _sha256_file(p) is None

    def test_empty_file(self):
        """Empty file returns correct sha256"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = Path(f.name)
        try:
            expected = hashlib.sha256(b"").hexdigest()
            assert _sha256_file(p) == expected
        finally:
            p.unlink()

    def test_file_with_content(self):
        """File with content returns correct sha256"""
        content = b"Hello, World!"
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            p = Path(f.name)
        try:
            expected = hashlib.sha256(content).hexdigest()
            assert _sha256_file(p) == expected
        finally:
            p.unlink()

    def test_large_file(self):
        """Large file (>1MB) returns correct sha256"""
        content = b"x" * (2 * 1024 * 1024)  # 2MB
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            p = Path(f.name)
        try:
            expected = hashlib.sha256(content).hexdigest()
            assert _sha256_file(p) == expected
        finally:
            p.unlink()

    def test_unicode_filename(self):
        """File with unicode filename works correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "测试文件.txt"
            p.write_bytes(b"test content")
            expected = hashlib.sha256(b"test content").hexdigest()
            assert _sha256_file(p) == expected

    def test_binary_content(self):
        """Binary content returns correct sha256"""
        content = bytes(range(256))
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            p = Path(f.name)
        try:
            expected = hashlib.sha256(content).hexdigest()
            assert _sha256_file(p) == expected
        finally:
            p.unlink()


# ==============================================================================
# TestFileMeta
# ==============================================================================
class TestFileMeta:
    """Tests for _file_meta function"""

    def test_nonexistent_file(self):
        """Nonexistent file returns exists=False"""
        p = Path("/nonexistent/file.txt")
        meta = _file_meta(p)
        assert meta["path"] == str(p)
        assert meta["exists"] is False
        assert "size_bytes" not in meta
        assert "mtime" not in meta

    def test_existing_file(self):
        """Existing file returns correct metadata"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            p = Path(f.name)
        try:
            meta = _file_meta(p)
            assert meta["path"] == str(p)
            assert meta["exists"] is True
            assert meta["size_bytes"] == 12
            assert "mtime" in meta
            # mtime should be ISO format
            datetime.fromisoformat(meta["mtime"])
        finally:
            p.unlink()

    def test_empty_file(self):
        """Empty file returns size_bytes=0"""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            p = Path(f.name)
        try:
            meta = _file_meta(p)
            assert meta["exists"] is True
            assert meta["size_bytes"] == 0
        finally:
            p.unlink()

    def test_directory(self):
        """Directory returns exists=True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            meta = _file_meta(p)
            assert meta["exists"] is True
            assert "size_bytes" in meta

    def test_unicode_path(self):
        """Unicode path works correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "中文文件.txt"
            p.write_text("内容", encoding="utf-8")
            meta = _file_meta(p)
            assert meta["exists"] is True
            assert "中文文件.txt" in meta["path"]


# ==============================================================================
# TestSafeReadJson
# ==============================================================================
class TestSafeReadJson:
    """Tests for _safe_read_json function"""

    def test_nonexistent_file(self):
        """Nonexistent file returns (None, 'not_found')"""
        p = Path("/nonexistent/file.json")
        obj, err = _safe_read_json(p)
        assert obj is None
        assert err == "not_found"

    def test_valid_json(self):
        """Valid JSON returns parsed object"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b'{"key": "value", "num": 42}')
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert err is None
            assert obj == {"key": "value", "num": 42}
        finally:
            p.unlink()

    def test_invalid_json(self):
        """Invalid JSON returns json_error"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b'not valid json {{{')
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert obj is None
            assert err.startswith("json_error:")
        finally:
            p.unlink()

    def test_empty_file(self):
        """Empty file returns json_error"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert obj is None
            assert err.startswith("json_error:")
        finally:
            p.unlink()

    def test_json_array(self):
        """JSON array is parsed correctly"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b'[1, 2, 3, "four"]')
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert err is None
            assert obj == [1, 2, 3, "four"]
        finally:
            p.unlink()

    def test_json_with_unicode(self):
        """JSON with unicode is parsed correctly"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write('{"中文": "值"}'.encode("utf-8"))
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert err is None
            assert obj == {"中文": "值"}
        finally:
            p.unlink()

    def test_json_null(self):
        """JSON null is parsed correctly"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(b'null')
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert err is None
            assert obj is None
        finally:
            p.unlink()

    def test_nested_json(self):
        """Nested JSON is parsed correctly"""
        data = {"level1": {"level2": {"level3": [1, 2, 3]}}}
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            f.write(json.dumps(data).encode("utf-8"))
            p = Path(f.name)
        try:
            obj, err = _safe_read_json(p)
            assert err is None
            assert obj == data
        finally:
            p.unlink()


# ==============================================================================
# TestFirstStr
# ==============================================================================
class TestFirstStr:
    """Tests for _first_str function"""

    def test_none_input(self):
        """None input returns None"""
        assert _first_str(None, ["key"]) is None

    def test_non_dict_input(self):
        """Non-dict input returns None"""
        assert _first_str("string", ["key"]) is None
        assert _first_str([1, 2, 3], ["key"]) is None
        assert _first_str(123, ["key"]) is None

    def test_empty_dict(self):
        """Empty dict returns None"""
        assert _first_str({}, ["key1", "key2"]) is None

    def test_empty_keys(self):
        """Empty keys list returns None"""
        assert _first_str({"key": "value"}, []) is None

    def test_first_key_found(self):
        """First key found returns its value"""
        d = {"key1": "value1", "key2": "value2"}
        assert _first_str(d, ["key1", "key2"]) == "value1"

    def test_second_key_found(self):
        """Second key found when first is missing"""
        d = {"key2": "value2", "key3": "value3"}
        assert _first_str(d, ["key1", "key2", "key3"]) == "value2"

    def test_whitespace_stripped(self):
        """Whitespace is stripped from value"""
        d = {"key": "  value with spaces  "}
        assert _first_str(d, ["key"]) == "value with spaces"

    def test_empty_string_skipped(self):
        """Empty string values are skipped"""
        d = {"key1": "", "key2": "value2"}
        assert _first_str(d, ["key1", "key2"]) == "value2"

    def test_whitespace_only_skipped(self):
        """Whitespace-only values are skipped"""
        d = {"key1": "   ", "key2": "value2"}
        assert _first_str(d, ["key1", "key2"]) == "value2"

    def test_non_string_skipped(self):
        """Non-string values are skipped"""
        d = {"key1": 123, "key2": ["list"], "key3": "value3"}
        assert _first_str(d, ["key1", "key2", "key3"]) == "value3"

    def test_no_valid_key(self):
        """No valid key returns None"""
        d = {"key1": 123, "key2": ""}
        assert _first_str(d, ["key1", "key2"]) is None

    def test_key_not_exists(self):
        """Key not in dict returns None"""
        d = {"other": "value"}
        assert _first_str(d, ["key1", "key2"]) is None


# ==============================================================================
# TestBuildAuditReport
# ==============================================================================
class TestBuildAuditReport:
    """Tests for build_audit_report function"""

    @pytest.fixture
    def mock_kg_loader(self):
        """Mock kg_loader module"""
        with patch("audit_service.kg_loader") as mock:
            mock.load_kg_config.return_value = {}
            mock.get_project_profile_rule_path.return_value = Path("/mock/pp_rule.json")
            mock.get_precheck_guard_rule_path.return_value = Path("/mock/pg_rule.json")
            mock.get_region_upgrade_rule.return_value = Path("/mock/ru_rule.json")
            mock.get_domain_map_path.return_value = Path("/mock/domain_map.json")
            mock.get_base_pack_paths.return_value = []
            yield mock

    @pytest.fixture
    def temp_build_dir(self):
        """Create temp build directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_report_has_generated_at(self, mock_kg_loader, temp_build_dir):
        """Report contains generated_at timestamp"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert "generated_at" in report
            # Should be ISO format
            datetime.fromisoformat(report["generated_at"].replace("Z", "+00:00"))

    def test_report_has_all_sections(self, mock_kg_loader, temp_build_dir):
        """Report contains all required sections"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert "project_profile" in report
            assert "kg_context" in report
            assert "region_upgrade" in report
            assert "precheck_guard" in report
            assert "compose" in report
            assert "checks" in report
            assert "replay" in report

    def test_report_checks_is_list(self, mock_kg_loader, temp_build_dir):
        """Report checks is a list"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert isinstance(report["checks"], list)

    def test_report_replay_section(self, mock_kg_loader, temp_build_dir):
        """Report replay section has correct structure"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert "replayable" in report["replay"]
            assert "missing" in report["replay"]
            assert isinstance(report["replay"]["missing"], list)

    def test_with_existing_artifacts(self, mock_kg_loader, temp_build_dir):
        """Report reads existing artifact files"""
        # Create a project_profile.json
        pp_file = temp_build_dir / "project_profile.json"
        pp_file.write_text(json.dumps({
            "decision": "accept",
            "project_type": "市政",
            "input_sha256": "abc123"
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert report["project_profile"]["exists"] is True
            assert report["project_profile"]["decision"] == "accept"
            assert report["project_profile"]["project_type"] == "市政"

    def test_input_sha256_consistency_check(self, mock_kg_loader, temp_build_dir):
        """Report includes input_sha256 consistency check"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check_names = [c["check"] for c in report["checks"]]
            assert "input_sha256_consistency" in check_names

    def test_rule_file_checks(self, mock_kg_loader, temp_build_dir):
        """Report includes rule file checks"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check_names = [c["check"] for c in report["checks"]]
            assert "project_profile_rule_file" in check_names
            assert "precheck_guard_rule_file" in check_names
            assert "region_upgrade_rule_file" in check_names
            assert "domain_map_rule_file" in check_names
            assert "base_pack_files" in check_names

    def test_quality_metrics_soft_check(self, mock_kg_loader, temp_build_dir):
        """Report includes quality_metrics_soft check"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check_names = [c["check"] for c in report["checks"]]
            assert "quality_metrics_soft" in check_names

    def test_compose_sections_count(self, mock_kg_loader, temp_build_dir):
        """Report counts compose sections correctly"""
        compose_file = temp_build_dir / "compose.json"
        compose_file.write_text(json.dumps({
            "status": "success",
            "sections": [
                {"title": "Section 1", "content": "Content 1"},
                {"title": "Section 2", "content": "Content 2"},
            ]
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert report["compose"]["sections_count"] == 2

    def test_missing_artifacts_tracked(self, mock_kg_loader, temp_build_dir):
        """Report tracks missing artifacts"""
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            # All artifacts should be missing in empty dir
            assert len(report["replay"]["missing"]) > 0

    def test_retrieve_trace(self, mock_kg_loader, temp_build_dir):
        """Report includes retrieve trace"""
        retrieve_file = temp_build_dir / "retrieve.json"
        retrieve_file.write_text(json.dumps({
            "query": "test query",
            "tokens": 100,
            "top_k": 5,
            "docs_scanned": 10,
            "results": [{"doc": "doc1"}, {"doc": "doc2"}]
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            assert report["retrieve"]["query"] == "test query"
            assert report["retrieve"]["results_count"] == 2


# ==============================================================================
# TestQualityMetrics
# ==============================================================================
class TestQualityMetrics:
    """Tests for quality metrics computation in build_audit_report"""

    @pytest.fixture
    def mock_kg_loader(self):
        """Mock kg_loader module"""
        with patch("audit_service.kg_loader") as mock:
            mock.load_kg_config.return_value = {}
            mock.get_project_profile_rule_path.return_value = Path("/mock/pp_rule.json")
            mock.get_precheck_guard_rule_path.return_value = Path("/mock/pg_rule.json")
            mock.get_region_upgrade_rule.return_value = Path("/mock/ru_rule.json")
            mock.get_domain_map_path.return_value = Path("/mock/domain_map.json")
            mock.get_base_pack_paths.return_value = []
            yield mock

    @pytest.fixture
    def temp_build_dir(self):
        """Create temp build directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_evidence_coverage_ratio(self, mock_kg_loader, temp_build_dir):
        """Evidence coverage ratio is calculated correctly"""
        compose_file = temp_build_dir / "compose.json"
        compose_file.write_text(json.dumps({
            "sections": [
                {"title": "Section 1", "content": "内容包含来源引用"},
                {"title": "Section 2", "content": "普通内容"},
                {"title": "Section 3", "content": "包含证据说明"},
            ]
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            soft_check = next(c for c in report["checks"] if c["check"] == "quality_metrics_soft")
            # Should find 2 sections with evidence keywords
            assert soft_check["value"]["evidence_sections_count"] == 2

    def test_param_coverage_ratio(self, mock_kg_loader, temp_build_dir):
        """Param coverage ratio is calculated correctly"""
        compose_file = temp_build_dir / "compose.json"
        compose_file.write_text(json.dumps({
            "sections": [
                {"title": "Section 1", "content": "厚度 100mm"},
                {"title": "Section 2", "content": "普通内容"},
                {"title": "Section 3", "content": "强度 30 MPa"},
            ]
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            soft_check = next(c for c in report["checks"] if c["check"] == "quality_metrics_soft")
            assert soft_check["value"]["param_coverage_sections_count"] == 2

    def test_compose_nonempty_ratio(self, mock_kg_loader, temp_build_dir):
        """Compose nonempty ratio is calculated correctly"""
        compose_file = temp_build_dir / "compose.json"
        compose_file.write_text(json.dumps({
            "sections": [
                {"title": "Section 1", "content": "有内容"},
                {"title": "Section 2", "content": ""},
                {"title": "Section 3", "content": "也有内容"},
            ]
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            soft_check = next(c for c in report["checks"] if c["check"] == "quality_metrics_soft")
            # 2 out of 3 sections have content
            assert soft_check["value"]["compose_nonempty_sections_count"] == 2
            assert soft_check["value"]["compose_nonempty_ratio"] == pytest.approx(2/3)


# ==============================================================================
# TestConsistencyChecks
# ==============================================================================
class TestConsistencyChecks:
    """Tests for consistency checks in build_audit_report"""

    @pytest.fixture
    def mock_kg_loader(self):
        """Mock kg_loader module"""
        with patch("audit_service.kg_loader") as mock:
            mock.load_kg_config.return_value = {}
            mock.get_project_profile_rule_path.return_value = Path("/mock/pp_rule.json")
            mock.get_precheck_guard_rule_path.return_value = Path("/mock/pg_rule.json")
            mock.get_region_upgrade_rule.return_value = Path("/mock/ru_rule.json")
            mock.get_domain_map_path.return_value = Path("/mock/domain_map.json")
            mock.get_base_pack_paths.return_value = []
            yield mock

    @pytest.fixture
    def temp_build_dir(self):
        """Create temp build directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_input_sha256_consistent(self, mock_kg_loader, temp_build_dir):
        """Input sha256 consistency check passes when all match"""
        same_sha = "abc123def456"
        for name in ["project_profile", "kg_context", "region_upgrade", "precheck_guard"]:
            (temp_build_dir / f"{name}.json").write_text(json.dumps({"input_sha256": same_sha}))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check = next(c for c in report["checks"] if c["check"] == "input_sha256_consistency")
            assert check["value"]["ok"] is True
            assert len(check["value"]["unique"]) == 1

    def test_input_sha256_inconsistent(self, mock_kg_loader, temp_build_dir):
        """Input sha256 consistency check fails when different"""
        (temp_build_dir / "project_profile.json").write_text(json.dumps({"input_sha256": "sha1"}))
        (temp_build_dir / "kg_context.json").write_text(json.dumps({"input_sha256": "sha2"}))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check = next(c for c in report["checks"] if c["check"] == "input_sha256_consistency")
            assert check["value"]["ok"] is False
            assert len(check["value"]["unique"]) == 2


# ==============================================================================
# TestEdgeCases
# ==============================================================================
class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.fixture
    def mock_kg_loader(self):
        """Mock kg_loader module"""
        with patch("audit_service.kg_loader") as mock:
            mock.load_kg_config.return_value = {}
            mock.get_project_profile_rule_path.return_value = Path("/mock/pp_rule.json")
            mock.get_precheck_guard_rule_path.return_value = Path("/mock/pg_rule.json")
            mock.get_region_upgrade_rule.return_value = Path("/mock/ru_rule.json")
            mock.get_domain_map_path.return_value = Path("/mock/domain_map.json")
            mock.get_base_pack_paths.return_value = []
            yield mock

    @pytest.fixture
    def temp_build_dir(self):
        """Create temp build directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_corrupted_json_handled(self, mock_kg_loader, temp_build_dir):
        """Corrupted JSON files are handled gracefully"""
        (temp_build_dir / "project_profile.json").write_text("not valid json {{{")
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            # Should not raise, should mark as error
            assert report["project_profile"]["exists"] is True

    def test_empty_json_handled(self, mock_kg_loader, temp_build_dir):
        """Empty JSON files are handled gracefully"""
        (temp_build_dir / "compose.json").write_text("")
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            # Empty JSON file results in sections_count=0 (fallback behavior)
            assert report["compose"]["sections_count"] == 0 or report["compose"]["sections_count"] is None

    def test_kg_loader_exception_handled(self, mock_kg_loader, temp_build_dir):
        """kg_loader exceptions are handled gracefully"""
        mock_kg_loader.get_project_profile_rule_path.side_effect = Exception("Test error")
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check = next(c for c in report["checks"] if c["check"] == "project_profile_rule_file")
            assert "error" in check["value"]

    def test_selected_packs_non_list(self, mock_kg_loader, temp_build_dir):
        """selected_packs as non-list is handled"""
        (temp_build_dir / "kg_context.json").write_text(json.dumps({
            "selected_packs": "not a list"
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            check = next(c for c in report["checks"] if c["check"] == "selected_pack_files")
            assert check["value"] is None

    def test_sections_as_count(self, mock_kg_loader, temp_build_dir):
        """sections_count without sections list is handled"""
        (temp_build_dir / "compose.json").write_text(json.dumps({
            "sections_count": 5,
            "sections": []  # Empty list to trigger fallback
        }))
        
        with patch("audit_service.BUILD_DIR", temp_build_dir):
            report = build_audit_report()
            soft_check = next(c for c in report["checks"] if c["check"] == "quality_metrics_soft")
            # With empty sections list, count should be 0
            assert soft_check["value"]["compose_sections_count"] == 0
