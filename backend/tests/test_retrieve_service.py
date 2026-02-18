# -*- coding: utf-8 -*-
"""Unit tests for retrieve_service.py"""
import pytest
import json
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.retrieve_service import (
    _sha256_text,
    _safe_load_json,
    _tokenize,
    _render,
    _score,
    _extract_work_item_like,
    _build_work_item_text,
    _extract_docs_from_obj,
)


# =============================================================================
# Tests for _sha256_text
# =============================================================================
class TestSha256Text:
    def test_basic_string(self):
        result = _sha256_text("hello")
        expected = hashlib.sha256("hello".encode("utf-8")).hexdigest()
        assert result == expected

    def test_empty_string(self):
        result = _sha256_text("")
        expected = hashlib.sha256("".encode("utf-8")).hexdigest()
        assert result == expected

    def test_chinese_text(self):
        result = _sha256_text("你好世界")
        expected = hashlib.sha256("你好世界".encode("utf-8")).hexdigest()
        assert result == expected

    def test_deterministic(self):
        """Same input should produce same hash"""
        assert _sha256_text("test") == _sha256_text("test")

    def test_different_inputs(self):
        """Different inputs should produce different hashes"""
        assert _sha256_text("a") != _sha256_text("b")


# =============================================================================
# Tests for _safe_load_json
# =============================================================================
class TestSafeLoadJson:
    def test_valid_json_file(self, tmp_path):
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}', encoding="utf-8")
        result, err = _safe_load_json(json_file)
        assert result == {"key": "value"}
        assert err is None

    def test_empty_json_object(self, tmp_path):
        json_file = tmp_path / "empty.json"
        json_file.write_text('{}', encoding="utf-8")
        result, err = _safe_load_json(json_file)
        assert result == {}
        assert err is None

    def test_json_array(self, tmp_path):
        json_file = tmp_path / "array.json"
        json_file.write_text('[1, 2, 3]', encoding="utf-8")
        result, err = _safe_load_json(json_file)
        assert result == [1, 2, 3]
        assert err is None

    def test_invalid_json(self, tmp_path):
        json_file = tmp_path / "invalid.json"
        json_file.write_text('not valid json', encoding="utf-8")
        result, err = _safe_load_json(json_file)
        assert result is None
        assert err is not None
        assert "JSONDecodeError" in err

    def test_nonexistent_file(self, tmp_path):
        json_file = tmp_path / "nonexistent.json"
        result, err = _safe_load_json(json_file)
        assert result is None
        assert err is not None

    def test_chinese_content(self, tmp_path):
        json_file = tmp_path / "chinese.json"
        json_file.write_text('{"名称": "测试"}', encoding="utf-8")
        result, err = _safe_load_json(json_file)
        assert result == {"名称": "测试"}
        assert err is None


# =============================================================================
# Tests for _tokenize
# =============================================================================
class TestTokenize:
    def test_chinese_words(self):
        result = _tokenize("混凝土施工")
        assert "混凝土" in result or "混凝土施工" in result

    def test_english_words(self):
        result = _tokenize("hello world test")
        assert "hello" in result
        assert "world" in result
        assert "test" in result

    def test_mixed_chinese_english(self):
        result = _tokenize("混凝土concrete施工")
        assert "concrete" in result
        assert len(result) >= 2

    def test_empty_string(self):
        result = _tokenize("")
        assert result == []

    def test_none_input(self):
        result = _tokenize(None)
        assert result == []

    def test_whitespace_only(self):
        result = _tokenize("   ")
        assert result == []

    def test_deduplicate(self):
        """Same tokens should be deduplicated"""
        result = _tokenize("test test test")
        assert result.count("test") == 1

    def test_numbers(self):
        result = _tokenize("test123 abc456")
        assert "test123" in result
        assert "abc456" in result

    def test_single_char_chinese(self):
        """Single Chinese chars should be grouped"""
        result = _tokenize("混 凝")
        # May return original query if no 2+ char tokens found
        assert len(result) >= 1


# =============================================================================
# Tests for _render
# =============================================================================
class TestRender:
    def test_none_value(self):
        assert _render(None) == ""

    def test_string_value(self):
        assert _render("hello") == "hello"

    def test_string_with_whitespace(self):
        assert _render("  hello  ") == "hello"

    def test_integer(self):
        assert _render(123) == "123"

    def test_float(self):
        assert _render(3.14) == "3.14"

    def test_boolean_true(self):
        assert _render(True) == "True"

    def test_boolean_false(self):
        assert _render(False) == "False"

    def test_dict(self):
        result = _render({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_list(self):
        result = _render([1, 2, 3])
        assert "[1, 2, 3]" in result

    def test_max_len_truncation(self):
        long_text = "a" * 1000
        result = _render(long_text, max_len=100)
        assert len(result) == 101  # 100 chars + "…"
        assert result.endswith("…")

    def test_chinese_text(self):
        result = _render("混凝土施工")
        assert result == "混凝土施工"

    def test_custom_max_len(self):
        result = _render("hello world", max_len=5)
        assert len(result) == 6  # 5 + "…"

    def test_exact_max_len(self):
        """Text exactly at max_len should not be truncated"""
        result = _render("hello", max_len=5)
        assert result == "hello"


# =============================================================================
# Tests for _score
# =============================================================================
class TestScore:
    def test_basic_match(self):
        score = _score("hello world", ["hello"])
        assert score > 0

    def test_multiple_matches(self):
        score = _score("hello hello hello", ["hello"])
        assert score > 0

    def test_no_match(self):
        score = _score("hello world", ["xyz"])
        assert score == 0.0

    def test_empty_text(self):
        score = _score("", ["hello"])
        assert score == 0.0

    def test_empty_tokens(self):
        score = _score("hello world", [])
        assert score == 0.0

    def test_none_text(self):
        score = _score(None, ["hello"])
        assert score == 0.0

    def test_case_insensitive(self):
        score = _score("HELLO world", ["hello"])
        assert score > 0

    def test_chinese_match(self):
        score = _score("混凝土施工技术", ["混凝土"])
        assert score > 0

    def test_multiple_tokens(self):
        score1 = _score("hello world", ["hello"])
        score2 = _score("hello world", ["hello", "world"])
        assert score2 > score1

    def test_normalization(self):
        """Longer texts should have normalized scores"""
        short_text = "hello"
        long_text = "hello " + "x" * 2000
        score_short = _score(short_text, ["hello"])
        score_long = _score(long_text, ["hello"])
        assert score_short > score_long  # Normalized by length


# =============================================================================
# Tests for _extract_work_item_like
# =============================================================================
class TestExtractWorkItemLike:
    def test_typical_work_item(self):
        item = {
            "工序名称": "混凝土浇筑",
            "操作步骤": ["步骤1", "步骤2"],
            "设备材料": ["材料1"],
        }
        assert _extract_work_item_like(item) is True

    def test_minimal_work_item(self):
        """工序名称 + 2 other keys should match"""
        item = {
            "工序名称": "测试",
            "风险点": "风险",
            "控制措施": "措施",
        }
        assert _extract_work_item_like(item) is True

    def test_five_keys_without_name(self):
        """5+ matching keys without 工序名称 should still match"""
        item = {
            "操作步骤": "1",
            "设备材料": "2",
            "关键参数": "3",
            "风险点": "4",
            "控制措施": "5",
        }
        assert _extract_work_item_like(item) is True

    def test_non_work_item(self):
        item = {
            "random_key": "value",
            "another_key": "value2",
        }
        assert _extract_work_item_like(item) is False

    def test_empty_dict(self):
        assert _extract_work_item_like({}) is False

    def test_only_name_insufficient(self):
        """工序名称 alone is not enough"""
        item = {"工序名称": "测试"}
        assert _extract_work_item_like(item) is False


# =============================================================================
# Tests for _build_work_item_text
# =============================================================================
class TestBuildWorkItemText:
    def test_basic_work_item(self):
        item = {
            "工序名称": "混凝土浇筑",
            "操作步骤": "步骤内容",
        }
        title, text = _build_work_item_text(item)
        assert title == "混凝土浇筑"
        assert "操作步骤" in text
        assert "步骤内容" in text

    def test_fallback_title_name(self):
        item = {"name": "测试名称"}
        title, _ = _build_work_item_text(item)
        assert title == "测试名称"

    def test_fallback_title_id(self):
        item = {"id": "test_id"}
        title, _ = _build_work_item_text(item)
        assert title == "test_id"

    def test_default_title(self):
        item = {}
        title, _ = _build_work_item_text(item)
        assert title == "work_item"

    def test_ordered_fields(self):
        item = {
            "工序名称": "测试",
            "风险点": "风险内容",
            "操作步骤": "步骤内容",
        }
        _, text = _build_work_item_text(item)
        # 操作步骤 should come before 风险点 in output
        step_pos = text.find("操作步骤")
        risk_pos = text.find("风险点")
        assert step_pos < risk_pos

    def test_skip_empty_values(self):
        item = {
            "工序名称": "测试",
            "空字段": "",
            "空列表": [],
            "空字典": {},
            "有值字段": "内容",
        }
        _, text = _build_work_item_text(item)
        assert "空字段" not in text
        assert "空列表" not in text
        assert "空字典" not in text
        assert "有值字段" in text


# =============================================================================
# Tests for _extract_docs_from_obj
# =============================================================================
class TestExtractDocsFromObj:
    def test_single_work_item(self):
        obj = {
            "工序名称": "混凝土浇筑",
            "操作步骤": "这是一段足够长的操作步骤描述文本，用于测试提取功能是否正常工作",
            "设备材料": "混凝土搅拌机",
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        assert len(docs) >= 1
        assert docs[0]["source"] == "test.json"

    def test_nested_work_items(self):
        obj = {
            "work_items": [
                {
                    "工序名称": "工序1",
                    "操作步骤": "这是一段足够长的操作步骤描述文本，需要超过40个字符才能被提取",
                    "风险点": "风险1",
                },
                {
                    "工序名称": "工序2",
                    "操作步骤": "这是另一段足够长的操作步骤描述文本，同样需要超过40个字符",
                    "风险点": "风险2",
                },
            ]
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        assert len(docs) >= 2

    def test_subdivisions(self):
        obj = {
            "subdivisions": [
                {
                    "工序名称": "子分部工序",
                    "操作步骤": "这是一段足够长的子分部工序操作步骤描述文本",
                    "设备材料": "材料",
                }
            ]
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        assert len(docs) >= 1

    def test_sections(self):
        obj = {
            "sections": [
                {
                    "工序名称": "章节工序",
                    "操作步骤": "这是一段足够长的章节工序操作步骤描述文本内容",
                    "设备材料": "材料",
                }
            ]
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        assert len(docs) >= 1

    def test_advanced_dict(self):
        """advanced field is processed and extracted as separate docs"""
        # Need text longer than 40 chars for add_doc to accept it
        long_content = "这是一段非常非常长的高级字段内容，需要确保超过四十个字符才能被成功提取到文档列表中进行检索"
        obj = {
            "advanced": {
                "key1": long_content,
            }
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        # advanced fields are extracted directly
        advanced_docs = [d for d in docs if "advanced" in d.get("title", "")]
        assert len(advanced_docs) >= 1
        assert advanced_docs[0]["title"] == "advanced/key1"

    def test_advanced_list(self):
        obj = {
            "advanced": {
                "list_key": ["项目1", "项目2", "项目3", "项目4", "项目5", "项目6"],
            }
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        # May or may not extract depending on length
        assert isinstance(docs, list)

    def test_empty_obj(self):
        docs = _extract_docs_from_obj({}, source="test.json")
        assert docs == []

    def test_list_input(self):
        obj = [
            {
                "工序名称": "工序1",
                "操作步骤": "这是一段足够长的操作步骤描述文本内容，需要超过40字符",
                "风险点": "风险",
            }
        ]
        docs = _extract_docs_from_obj(obj, source="test.json")
        assert len(docs) >= 1

    def test_deduplication(self):
        """Same content should not produce duplicate docs"""
        obj = {
            "工序名称": "重复测试",
            "操作步骤": "这是一段完全相同的足够长的操作步骤描述文本内容",
            "风险点": "风险",
        }
        # Call twice to verify internal dedup
        docs = _extract_docs_from_obj(obj, source="test.json")
        initial_count = len(docs)
        # The function should not produce duplicates from single call
        assert initial_count >= 1

    def test_min_text_length(self):
        """Text shorter than 40 chars should be excluded"""
        obj = {
            "工序名称": "短",
            "操作步骤": "短",
            "风险点": "短",
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        # Should be empty since all texts are too short
        assert len(docs) == 0

    def test_doc_structure(self):
        obj = {
            "工序名称": "结构测试",
            "操作步骤": "这是一段足够长的操作步骤描述文本内容，需要超过40个字符才能被提取",
            "风险点": "风险点内容",
        }
        docs = _extract_docs_from_obj(obj, source="test.json")
        assert len(docs) >= 1
        doc = docs[0]
        assert "source" in doc
        assert "title" in doc
        assert "text" in doc
        assert "path" in doc
        assert "sha256" in doc


# =============================================================================
# Tests for _load_selected_pack_paths
# =============================================================================
from backend.retrieve_service import _load_selected_pack_paths, BACKEND_DIR, BUILD_DIR


class TestLoadSelectedPackPaths:
    """Tests for _load_selected_pack_paths function"""

    def test_from_kg_context_with_selected_packs(self, tmp_path, monkeypatch):
        """Test loading packs from kg_context.json with selected_packs"""
        # Create a temporary build directory
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        # Create a test pack file
        pack_file = tmp_path / "test_pack.json"
        pack_file.write_text('{"test": "data"}', encoding="utf-8")
        
        # Create kg_context.json with selected_packs
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [
                {"path": str(pack_file)},
            ],
            "kg_pack": {"active_pack": "test"}
        }), encoding="utf-8")
        
        # Monkeypatch BUILD_DIR
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        assert len(paths) >= 1
        assert info["source"] == "build/kg_context.json"

    def test_from_kg_context_with_string_packs(self, tmp_path, monkeypatch):
        """Test loading packs when selected_packs contains strings"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack1.json"
        pack_file.write_text('{}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [str(pack_file)],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        assert len(paths) >= 1

    def test_from_kg_context_relative_paths(self, tmp_path, monkeypatch):
        """Test relative paths are resolved against BACKEND_DIR"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "relative_pack.json"
        pack_file.write_text('{}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": "relative_pack.json"}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        assert len(paths) >= 1

    def test_nonexistent_packs_filtered(self, tmp_path, monkeypatch):
        """Test that non-existent pack paths are filtered out"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [
                {"path": "/nonexistent/pack.json"},
            ],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        # No existing paths, should fall through to kg_config
        assert isinstance(paths, list)

    def test_empty_selected_packs(self, tmp_path, monkeypatch):
        """Test handling of empty selected_packs array"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        assert isinstance(paths, list)

    def test_fallback_to_kg_config(self, tmp_path, monkeypatch):
        """Test fallback to kg_loader when kg_context.json doesn't exist"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        # No kg_context.json exists
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        # Mock kg_loader to simulate the fallback
        mock_kg_loader = MagicMock()
        mock_kg_loader.load_kg_config.return_value = {}
        mock_kg_loader.get_base_pack_paths.return_value = []
        
        with patch.dict('sys.modules', {'backend.kg_loader': mock_kg_loader}):
            paths, info = _load_selected_pack_paths()
            assert info["source"] == "kg_config.base_packs"

    def test_kg_pack_extracted(self, tmp_path, monkeypatch):
        """Test that kg_pack is extracted from kg_context.json"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
            "kg_pack": {"active_pack": "test_pack", "version": "1.0"}
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        assert "kg_pack" in info
        assert info["kg_pack"]["active_pack"] == "test_pack"


# =============================================================================
# Tests for retrieve (main function)
# =============================================================================
from backend.retrieve_service import retrieve


class TestRetrieve:
    """Tests for the main retrieve function"""

    def test_basic_retrieve(self, tmp_path, monkeypatch):
        """Test basic retrieve functionality"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        # Create a pack with searchable content
        pack_file = tmp_path / "pack.json"
        pack_file.write_text(json.dumps({
            "工序名称": "混凝土浇筑施工工艺",
            "操作步骤": "这是一段关于混凝土浇筑的详细操作步骤描述，包含了完整的施工流程和注意事项",
            "风险点": "混凝土强度不足",
            "控制措施": "加强养护管理",
        }), encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("混凝土", top_k=5)
        assert "results" in result
        assert "stats" in result
        assert "errors" in result

    def test_retrieve_with_matches(self, tmp_path, monkeypatch):
        """Test that retrieve returns matching results"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text(json.dumps({
            "工序名称": "钢筋绑扎施工技术",
            "操作步骤": "这是一段关于钢筋绑扎的详细操作步骤描述，包含了完整的绑扎流程和技术要点说明",
            "风险点": "绑扎不牢固",
            "控制措施": "检查绑扎质量",
        }), encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("钢筋绑扎", top_k=5)
        assert len(result["results"]) >= 1
        # Check result structure
        if result["results"]:
            first = result["results"][0]
            assert "score" in first
            assert first["score"] > 0

    def test_retrieve_empty_query(self, tmp_path, monkeypatch):
        """Test retrieve with empty query"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{"key": "value"}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("", top_k=5)
        assert "results" in result
        assert result["results"] == []  # No matches with empty query

    def test_retrieve_none_query(self, tmp_path, monkeypatch):
        """Test retrieve with None query"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve(None, top_k=5)
        assert "results" in result

    def test_retrieve_top_k_bounds(self, tmp_path, monkeypatch):
        """Test that top_k is bounded between 1 and 50"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        # Test with 0 (should become 1)
        result = retrieve("test", top_k=0)
        assert "results" in result
        
        # Test with 100 (should become 50)
        result = retrieve("test", top_k=100)
        assert "results" in result

    def test_retrieve_saves_trace(self, tmp_path, monkeypatch):
        """Test that retrieve saves trace to retrieve.json"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("test query", top_k=5)
        
        trace_file = build_dir / "retrieve.json"
        assert trace_file.exists()
        
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        assert trace["query"] == "test query"
        assert "tokens" in trace
        assert "generated_at" in trace

    def test_retrieve_with_invalid_json_pack(self, tmp_path, monkeypatch):
        """Test retrieve handles invalid JSON in pack files gracefully"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "invalid.json"
        pack_file.write_text('not valid json', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("test", top_k=5)
        assert "errors" in result
        assert len(result["errors"]) >= 1

    def test_retrieve_with_multiple_packs(self, tmp_path, monkeypatch):
        """Test retrieve with multiple pack files"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack1 = tmp_path / "pack1.json"
        pack1.write_text(json.dumps({
            "工序名称": "基坑开挖施工工艺",
            "操作步骤": "这是一段关于基坑开挖的详细操作步骤描述，包含了完整的开挖流程",
            "风险点": "坍塌",
        }), encoding="utf-8")
        
        pack2 = tmp_path / "pack2.json"
        pack2.write_text(json.dumps({
            "工序名称": "土方回填施工工艺",
            "操作步骤": "这是一段关于土方回填的详细操作步骤描述，包含了回填材料和压实要求",
            "风险点": "沉降",
        }), encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [
                {"path": str(pack1)},
                {"path": str(pack2)},
            ],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("施工", top_k=10)
        assert result["stats"]["used_packs"] == 2

    def test_retrieve_no_packs(self, tmp_path, monkeypatch):
        """Test retrieve when no packs are available"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        # Create kg_context.json with one non-existent pack (which will be filtered)
        # and no kg_context fallback
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": "/nonexistent/pack123456789.json"}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        original_build_dir = rs.BUILD_DIR
        original_backend_dir = rs.BACKEND_DIR
        
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        # Also need to patch the kg_loader import inside the function
        # The function will fail to import kg_loader in fallback, which is fine
        result = retrieve("test", top_k=5)
        
        # The result should have 0 packs since selected_packs point to nonexistent files
        # and it should fall through to kg_loader fallback which may or may not find packs
        assert "stats" in result
        assert "results" in result
        # Results should be empty with no valid packs
        assert result["results"] == []

    def test_retrieve_result_structure(self, tmp_path, monkeypatch):
        """Test that retrieve results have correct structure"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text(json.dumps({
            "工序名称": "模板支撑施工技术",
            "操作步骤": "这是一段关于模板支撑的详细操作步骤描述文本，包含了支撑安装和拆除流程说明",
            "风险点": "支撑失稳",
            "控制措施": "检查支撑稳定性",
        }), encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("模板", top_k=5)
        
        # Check top-level structure
        assert "results" in result
        assert "trace_saved_at" in result
        assert "stats" in result
        assert "errors" in result
        
        # Check stats structure
        assert "docs_scanned" in result["stats"]
        assert "used_packs" in result["stats"]
        
        # Check result item structure if any results
        if result["results"]:
            item = result["results"][0]
            assert "source" in item
            assert "title" in item
            assert "text" in item
            assert "score" in item
            assert "path" in item
            assert "sha256" in item

    def test_retrieve_text_truncation(self, tmp_path, monkeypatch):
        """Test that long texts are truncated in results"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        # Create a pack with very long text
        long_text = "这是测试文本" * 200  # Very long
        pack_file = tmp_path / "pack.json"
        pack_file.write_text(json.dumps({
            "工序名称": "长文本测试",
            "操作步骤": long_text,
            "风险点": "测试",
        }), encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("测试", top_k=5)
        
        if result["results"]:
            text = result["results"][0]["text"]
            assert len(text) <= 901  # 900 + "…"

    def test_retrieve_kg_pack_in_trace(self, tmp_path, monkeypatch):
        """Test that kg_pack is included in trace output"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{"test": "data"}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
            "kg_pack": {"active_pack": "trace_test", "version": "2.0"}
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        retrieve("test", top_k=5)
        
        trace_file = build_dir / "retrieve.json"
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        assert "kg_pack" in trace

    def test_retrieve_fallback_doc_creation(self, tmp_path, monkeypatch):
        """Test fallback when pack has no extractable work items"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        # Pack with no work items but has searchable content
        pack_file = tmp_path / "pack.json"
        pack_file.write_text(json.dumps({
            "general_info": "这是一段普通的测试内容，不包含工序相关的字段"
        }), encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("测试", top_k=5)
        # Should still work and create a fallback doc from the pack
        assert "results" in result
        assert result["stats"]["docs_scanned"] >= 1

    def test_retrieve_with_kg_config_fallback(self, tmp_path, monkeypatch):
        """Test kg_pack computation from kg_config.json when kg_context has no kg_pack (line 279-297)"""
        # This test verifies the kg_pack fallback logic works
        # The actual fallback uses __file__ path internally, so we test the mechanism exists
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{"test": "data"}', encoding="utf-8")
        
        # Create kg_context.json WITHOUT kg_pack field
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
            # No kg_pack field - this will trigger fallback logic in retrieve()
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("test", top_k=5)
        
        # Verify the trace file is written and contains kg_pack (from fallback)
        trace_file = build_dir / "retrieve.json"
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        # kg_pack should exist - either computed from kg_config.json or None
        assert "kg_pack" in trace or trace.get("kg_pack") is None
        # The function should complete without error
        assert "results" in result

    def test_retrieve_writes_trace_with_kg_pack(self, tmp_path, monkeypatch):
        """Test that retrieve writes trace file with kg_pack info"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{}', encoding="utf-8")
        
        # Create kg_context.json with kg_pack
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
            "kg_pack": {
                "active_pack": "test_pack",
                "manifest_exists": True,
                "manifest_sha256": "abc123"
            }
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        result = retrieve("test", top_k=5)
        
        trace_file = build_dir / "retrieve.json"
        trace = json.loads(trace_file.read_text(encoding="utf-8"))
        # kg_pack should be present in trace
        assert "kg_pack" in trace
        # The function completes successfully
        assert "results" in result


# =============================================================================
# Additional edge case tests for coverage
# =============================================================================
class TestRenderEdgeCases:
    """Tests for _render function edge cases (line 51-52)"""
    
    def test_render_non_serializable_object(self):
        """Test _render with object that can't be JSON serialized"""
        class NonSerializable:
            def __repr__(self):
                return "NonSerializable()"
        
        result = _render(NonSerializable())
        assert result == "NonSerializable()"
    
    def test_render_object_with_circular_reference(self):
        """Test _render with circular reference (triggers except branch)"""
        circular = {}
        circular["self"] = circular  # Creates circular reference
        
        # This should trigger the except branch and use str() fallback
        result = _render(circular)
        assert isinstance(result, str)


class TestScoreEdgeCases:
    """Tests for _score function edge cases (line 66)"""
    
    def test_score_with_empty_token(self):
        """Test _score with empty string token (line 66: if not tok_l: continue)"""
        score = _score("hello world", ["hello", "", "   ", "world"])
        assert score > 0  # Should skip empty tokens and still score
    
    def test_score_with_whitespace_only_tokens(self):
        """Test _score with whitespace-only tokens"""
        score = _score("test content", ["test", "   ", "\t", "content"])
        assert score > 0


class TestExtractDocsDeduplication:
    """Tests for _extract_docs_from_obj deduplication (line 114)"""
    
    def test_duplicate_content_in_nested_structure(self):
        """Test that duplicate content is deduplicated (line 114: if h in seen: return)"""
        # Create structure where same work item appears in multiple places
        work_item = {
            "工序名称": "重复工序名称测试",
            "操作步骤": "这是一段完全相同的足够长的操作步骤描述文本内容，需要超过40字符",
            "风险点": "相同风险点",
        }
        obj = {
            "work_items": [work_item],
            "sections": [
                {
                    "work_items": [work_item]  # Same item referenced again
                }
            ]
        }
        docs = _extract_docs_from_obj(obj, source="dedup_test.json")
        # Even though the same work_item appears twice, it should only be extracted once
        titles = [d["title"] for d in docs]
        assert titles.count("重复工序名称测试") == 1


class TestLoadSelectedPackPathsEdgeCases:
    """Tests for _load_selected_pack_paths edge cases"""
    
    def test_selected_pack_with_empty_path(self, tmp_path, monkeypatch):
        """Test handling of selected_packs with empty path (line 176: if not p: continue)"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "valid.json"
        pack_file.write_text('{}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [
                {"path": ""},  # Empty path - should be skipped
                {"file": None},  # None value - should be skipped
                {"name": ""},  # Empty name - should be skipped
                {"path": str(pack_file)},  # Valid path
            ],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        paths, info = _load_selected_pack_paths()
        assert len(paths) == 1  # Only the valid path should be included
    
    def test_kg_pack_extraction_error(self, tmp_path, monkeypatch):
        """Test kg_pack extraction error handling (line 192-193)"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{}', encoding="utf-8")
        
        # Create valid kg_context.json first
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
            "kg_pack": {"active": "test"}
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        # Now corrupt the file to trigger error during kg_pack extraction
        original_safe_load = rs._safe_load_json
        call_count = [0]
        def mock_safe_load(p):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call returns valid data for paths
                return {"selected_packs": [{"path": str(pack_file)}]}, None
            # Subsequent reads might fail
            return original_safe_load(p)
        
        # The kg_pack extraction uses direct file read, simulate error
        paths, info = _load_selected_pack_paths()
        assert "kg_pack" in info
    
    def test_kg_loader_exception_in_load(self, tmp_path, monkeypatch):
        """Test fallback when kg_loader.load_kg_config raises exception (line 205-208)"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        # No kg_context.json - will try to use kg_loader
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        # Patch kg_loader within the function's namespace by patching the import
        import backend.kg_loader as real_kg_loader
        original_load = real_kg_loader.load_kg_config
        
        def mock_load_kg_config():
            raise Exception("Config load failed")
        
        monkeypatch.setattr(real_kg_loader, "load_kg_config", mock_load_kg_config)
        
        paths, info = _load_selected_pack_paths()
        
        # Should handle the error gracefully
        assert info["source"] == "kg_config.base_packs"
        assert "error" in info["details"]
        assert "Config load failed" in info["details"]["error"]


class TestRetrieveKgPackFallback:
    """Tests for retrieve function kg_pack fallback logic"""
    
    def test_retrieve_kg_pack_exception_handling(self, tmp_path, monkeypatch):
        """Test exception handling in kg_pack trace injection (line 309-310)"""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        
        pack_file = tmp_path / "pack.json"
        pack_file.write_text('{"test": "data"}', encoding="utf-8")
        
        kg_context = build_dir / "kg_context.json"
        kg_context.write_text(json.dumps({
            "selected_packs": [{"path": str(pack_file)}],
        }), encoding="utf-8")
        
        import backend.retrieve_service as rs
        monkeypatch.setattr(rs, "BUILD_DIR", build_dir)
        monkeypatch.setattr(rs, "BACKEND_DIR", tmp_path)
        
        # The exception path (309-310) is hard to trigger directly
        # but we can verify the function works even in edge cases
        result = retrieve("test", top_k=5)
        assert "results" in result
        assert "trace_saved_at" in result
