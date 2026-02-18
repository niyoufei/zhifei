"""
Unit tests for backend/zhifei_autoplan/kg_store.py
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import hashlib


class TestSha256Bytes:
    """Tests for _sha256_bytes function."""

    def test_sha256_simple_bytes(self):
        """Test SHA256 hash of simple bytes."""
        from backend.zhifei_autoplan import kg_store
        
        content = b"hello world"
        expected = hashlib.sha256(content).hexdigest()
        result = kg_store._sha256_bytes(content)
        assert result == expected

    def test_sha256_empty_bytes(self):
        """Test SHA256 hash of empty bytes."""
        from backend.zhifei_autoplan import kg_store
        
        content = b""
        expected = hashlib.sha256(content).hexdigest()
        result = kg_store._sha256_bytes(content)
        assert result == expected

    def test_sha256_chinese_bytes(self):
        """Test SHA256 hash of Chinese UTF-8 bytes."""
        from backend.zhifei_autoplan import kg_store
        
        content = "知识图谱测试".encode("utf-8")
        expected = hashlib.sha256(content).hexdigest()
        result = kg_store._sha256_bytes(content)
        assert result == expected

    def test_sha256_binary_content(self):
        """Test SHA256 hash of binary content."""
        from backend.zhifei_autoplan import kg_store
        
        content = bytes(range(256))
        expected = hashlib.sha256(content).hexdigest()
        result = kg_store._sha256_bytes(content)
        assert result == expected

    def test_sha256_large_content(self):
        """Test SHA256 hash of large content."""
        from backend.zhifei_autoplan import kg_store
        
        content = b"x" * 1000000  # 1MB
        expected = hashlib.sha256(content).hexdigest()
        result = kg_store._sha256_bytes(content)
        assert result == expected

    def test_sha256_returns_hex_string(self):
        """Test SHA256 returns 64-char hex string."""
        from backend.zhifei_autoplan import kg_store
        
        result = kg_store._sha256_bytes(b"test")
        assert isinstance(result, str)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestSaveKgBytes:
    """Tests for save_kg_bytes function."""

    def test_save_simple_content(self, tmp_path):
        """Test saving simple byte content."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            content = b"test content"
            meta = kg_store.save_kg_bytes(content, "test.json")
            
            assert "kg_id" in meta
            assert meta["file_name"] == "test.json"
            assert meta["size_bytes"] == len(content)
            assert "sha256" in meta
            assert "uploaded_at" in meta
            assert kg_index.exists()

    def test_save_creates_file(self, tmp_path):
        """Test that save creates a file on disk."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            content = b"file content"
            meta = kg_store.save_kg_bytes(content, "myfile.json")
            
            stored_path = Path(meta["stored_as"])
            assert stored_path.exists()
            assert stored_path.read_bytes() == content

    def test_save_appends_to_index(self, tmp_path):
        """Test that multiple saves append to index."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            kg_store.save_kg_bytes(b"content1", "file1.json")
            kg_store.save_kg_bytes(b"content2", "file2.json")
            kg_store.save_kg_bytes(b"content3", "file3.json")
            
            lines = kg_index.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 3

    def test_save_chinese_filename(self, tmp_path):
        """Test saving with Chinese filename."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            content = b"chinese content"
            meta = kg_store.save_kg_bytes(content, "知识图谱.json")
            
            assert meta["file_name"] == "知识图谱.json"

    def test_save_filename_with_slash(self, tmp_path):
        """Test filename with slash is sanitized."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            meta = kg_store.save_kg_bytes(b"content", "path/to/file.json")
            
            # Slash should be replaced with underscore in stored filename
            assert "/" not in Path(meta["stored_as"]).name
            assert meta["file_name"] == "path/to/file.json"  # Original preserved

    def test_save_empty_content(self, tmp_path):
        """Test saving empty content."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            meta = kg_store.save_kg_bytes(b"", "empty.json")
            
            assert meta["size_bytes"] == 0

    def test_save_large_content(self, tmp_path):
        """Test saving large content."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            content = b"x" * 100000  # 100KB
            meta = kg_store.save_kg_bytes(content, "large.bin")
            
            assert meta["size_bytes"] == 100000
            stored_path = Path(meta["stored_as"])
            assert stored_path.read_bytes() == content

    def test_save_binary_content(self, tmp_path):
        """Test saving binary content."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            content = bytes(range(256))
            meta = kg_store.save_kg_bytes(content, "binary.bin")
            
            stored_path = Path(meta["stored_as"])
            assert stored_path.read_bytes() == content

    def test_save_index_contains_valid_json(self, tmp_path):
        """Test index file contains valid JSON lines."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            kg_store.save_kg_bytes(b"content", "test.json")
            
            line = kg_index.read_text(encoding="utf-8").strip()
            parsed = json.loads(line)
            assert isinstance(parsed, dict)


class TestListKg:
    """Tests for list_kg function."""

    def test_list_empty_index(self, tmp_path):
        """Test listing when index doesn't exist."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            result = kg_store.list_kg()
            assert result == []

    def test_list_one_entry(self, tmp_path):
        """Test listing with one entry."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            kg_store.save_kg_bytes(b"content", "file.json")
            
            result = kg_store.list_kg()
            assert len(result) == 1
            assert result[0]["file_name"] == "file.json"

    def test_list_multiple_entries(self, tmp_path):
        """Test listing with multiple entries."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            kg_store.save_kg_bytes(b"content1", "file1.json")
            kg_store.save_kg_bytes(b"content2", "file2.json")
            kg_store.save_kg_bytes(b"content3", "file3.json")
            
            result = kg_store.list_kg()
            assert len(result) == 3
            filenames = [r["file_name"] for r in result]
            assert "file1.json" in filenames
            assert "file2.json" in filenames
            assert "file3.json" in filenames

    def test_list_skips_invalid_json(self, tmp_path):
        """Test listing skips invalid JSON lines."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        # Write mix of valid and invalid lines
        kg_index.write_text(
            '{"kg_id": "abc", "file_name": "valid.json"}\n'
            'invalid json line\n'
            '{"kg_id": "def", "file_name": "valid2.json"}\n',
            encoding="utf-8"
        )
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            result = kg_store.list_kg()
            assert len(result) == 2

    def test_list_handles_empty_lines(self, tmp_path):
        """Test listing handles empty lines in index."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        kg_index.write_text(
            '{"kg_id": "abc", "file_name": "file.json"}\n\n\n',
            encoding="utf-8"
        )
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            result = kg_store.list_kg()
            assert len(result) == 1

    def test_list_returns_dicts(self, tmp_path):
        """Test list returns list of dicts."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index):
            kg_store.save_kg_bytes(b"content", "file.json")
            
            result = kg_store.list_kg()
            assert isinstance(result, list)
            assert all(isinstance(r, dict) for r in result)


class TestSetActiveKg:
    """Tests for set_active_kg function."""

    def test_set_active_existing_kg(self, tmp_path):
        """Test setting active KG for existing kg_id."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            meta = kg_store.save_kg_bytes(b"content", "file.json")
            kg_id = meta["kg_id"]
            
            result = kg_store.set_active_kg(kg_id)
            
            assert result["kg_id"] == kg_id
            assert kg_active.exists()

    def test_set_active_writes_file(self, tmp_path):
        """Test set_active_kg writes to active file."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            meta = kg_store.save_kg_bytes(b"content", "myfile.json")
            kg_id = meta["kg_id"]
            
            kg_store.set_active_kg(kg_id)
            
            active_data = json.loads(kg_active.read_text(encoding="utf-8"))
            assert active_data["kg_id"] == kg_id
            assert active_data["file_name"] == "myfile.json"

    def test_set_active_nonexistent_raises(self, tmp_path):
        """Test setting nonexistent kg_id raises ValueError."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            with pytest.raises(ValueError, match="kg_id not found"):
                kg_store.set_active_kg("nonexistent_id")

    def test_set_active_chooses_latest(self, tmp_path):
        """Test set_active chooses latest entry for duplicate kg_id."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        # Write two entries with same kg_id but different stored_as
        kg_index.write_text(
            '{"kg_id": "abc123", "file_name": "old.json", "stored_as": "path1"}\n'
            '{"kg_id": "abc123", "file_name": "new.json", "stored_as": "path2"}\n',
            encoding="utf-8"
        )
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            result = kg_store.set_active_kg("abc123")
            
            # Should choose latest (reversed list)
            assert result["file_name"] == "new.json"

    def test_set_active_returns_meta(self, tmp_path):
        """Test set_active returns the metadata dict."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            meta = kg_store.save_kg_bytes(b"content", "test.json")
            
            result = kg_store.set_active_kg(meta["kg_id"])
            
            assert result == meta

    def test_set_active_overwrites_previous(self, tmp_path):
        """Test set_active overwrites previous active."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            meta1 = kg_store.save_kg_bytes(b"content1", "file1.json")
            meta2 = kg_store.save_kg_bytes(b"content2", "file2.json")
            
            kg_store.set_active_kg(meta1["kg_id"])
            kg_store.set_active_kg(meta2["kg_id"])
            
            active_data = json.loads(kg_active.read_text(encoding="utf-8"))
            assert active_data["file_name"] == "file2.json"


class TestGetActiveKg:
    """Tests for get_active_kg function."""

    def test_get_active_nonexistent(self, tmp_path):
        """Test get_active returns None when no active file."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_ACTIVE', kg_active):
            result = kg_store.get_active_kg()
            assert result is None

    def test_get_active_existing(self, tmp_path):
        """Test get_active returns data when active file exists."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            meta = kg_store.save_kg_bytes(b"content", "test.json")
            kg_store.set_active_kg(meta["kg_id"])
            
            result = kg_store.get_active_kg()
            
            assert result is not None
            assert result["kg_id"] == meta["kg_id"]
            assert result["file_name"] == "test.json"

    def test_get_active_invalid_json(self, tmp_path):
        """Test get_active returns None for invalid JSON."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_active = kg_dir / "active_kg.json"
        kg_active.write_text("invalid json {", encoding="utf-8")
        
        with patch.object(kg_store, 'KG_ACTIVE', kg_active):
            result = kg_store.get_active_kg()
            assert result is None

    def test_get_active_empty_file(self, tmp_path):
        """Test get_active returns None for empty file."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_active = kg_dir / "active_kg.json"
        kg_active.write_text("", encoding="utf-8")
        
        with patch.object(kg_store, 'KG_ACTIVE', kg_active):
            result = kg_store.get_active_kg()
            assert result is None

    def test_get_active_returns_dict(self, tmp_path):
        """Test get_active returns a dict."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            meta = kg_store.save_kg_bytes(b"content", "test.json")
            kg_store.set_active_kg(meta["kg_id"])
            
            result = kg_store.get_active_kg()
            assert isinstance(result, dict)


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_kg_dir_is_path(self):
        """Test KG_DIR is a Path object."""
        from backend.zhifei_autoplan import kg_store
        assert isinstance(kg_store.KG_DIR, Path)

    def test_kg_index_is_path(self):
        """Test KG_INDEX is a Path object."""
        from backend.zhifei_autoplan import kg_store
        assert isinstance(kg_store.KG_INDEX, Path)

    def test_kg_active_is_path(self):
        """Test KG_ACTIVE is a Path object."""
        from backend.zhifei_autoplan import kg_store
        assert isinstance(kg_store.KG_ACTIVE, Path)

    def test_kg_index_in_kg_dir(self):
        """Test KG_INDEX is inside KG_DIR."""
        from backend.zhifei_autoplan import kg_store
        assert kg_store.KG_INDEX.parent == kg_store.KG_DIR

    def test_kg_active_in_kg_dir(self):
        """Test KG_ACTIVE is inside KG_DIR."""
        from backend.zhifei_autoplan import kg_store
        assert kg_store.KG_ACTIVE.parent == kg_store.KG_DIR


class TestIntegration:
    """Integration tests for kg_store workflow."""

    def test_save_list_set_get_workflow(self, tmp_path):
        """Test complete workflow: save -> list -> set_active -> get_active."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            # Save
            meta = kg_store.save_kg_bytes(b'{"nodes": [], "edges": []}', "kg.json")
            kg_id = meta["kg_id"]
            
            # List
            items = kg_store.list_kg()
            assert len(items) == 1
            assert items[0]["kg_id"] == kg_id
            
            # Set active
            kg_store.set_active_kg(kg_id)
            
            # Get active
            active = kg_store.get_active_kg()
            assert active["kg_id"] == kg_id
            assert active["file_name"] == "kg.json"

    def test_multiple_kg_workflow(self, tmp_path):
        """Test workflow with multiple KGs."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            # Save multiple KGs
            meta1 = kg_store.save_kg_bytes(b"kg1 content", "kg_v1.json")
            meta2 = kg_store.save_kg_bytes(b"kg2 content", "kg_v2.json")
            meta3 = kg_store.save_kg_bytes(b"kg3 content", "kg_v3.json")
            
            # List all
            items = kg_store.list_kg()
            assert len(items) == 3
            
            # Set active to v2
            kg_store.set_active_kg(meta2["kg_id"])
            active = kg_store.get_active_kg()
            assert active["file_name"] == "kg_v2.json"
            
            # Change active to v3
            kg_store.set_active_kg(meta3["kg_id"])
            active = kg_store.get_active_kg()
            assert active["file_name"] == "kg_v3.json"

    def test_chinese_kg_content(self, tmp_path):
        """Test workflow with Chinese content."""
        from backend.zhifei_autoplan import kg_store
        
        kg_dir = tmp_path / "kg"
        kg_dir.mkdir()
        kg_index = kg_dir / "kg_index.jsonl"
        kg_active = kg_dir / "active_kg.json"
        
        with patch.object(kg_store, 'KG_DIR', kg_dir), \
             patch.object(kg_store, 'KG_INDEX', kg_index), \
             patch.object(kg_store, 'KG_ACTIVE', kg_active):
            content = json.dumps({
                "节点": ["施工准备", "主体施工", "竣工验收"],
                "关系": [{"from": "施工准备", "to": "主体施工"}]
            }, ensure_ascii=False).encode("utf-8")
            
            meta = kg_store.save_kg_bytes(content, "知识图谱.json")
            kg_store.set_active_kg(meta["kg_id"])
            
            active = kg_store.get_active_kg()
            assert active["file_name"] == "知识图谱.json"
            
            # Verify stored content
            stored_path = Path(meta["stored_as"])
            loaded = json.loads(stored_path.read_bytes().decode("utf-8"))
            assert "节点" in loaded
            assert len(loaded["节点"]) == 3
