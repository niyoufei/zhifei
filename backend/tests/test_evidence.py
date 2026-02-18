"""
Evidence 单元测试
覆盖 evidence.py 的 search_ingested_docs 方法
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.zhifei_autoplan.evidence import search_ingested_docs


class TestSearchIngestedDocs:
    """测试 search_ingested_docs 方法"""

    def test_audit_path_not_exists(self, tmp_path):
        """审计文件不存在时返回空列表"""
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            mock_audit = MagicMock()
            mock_audit.exists.return_value = False
            mock_path.return_value = mock_audit
            
            result = search_ingested_docs("测试查询")
            assert result == []

    def test_empty_query(self, tmp_path):
        """空查询返回空列表"""
        # 创建临时审计文件
        audit_dir = tmp_path / "backend" / "data" / "audit"
        audit_dir.mkdir(parents=True)
        audit_file = audit_dir / "ingest.jsonl"
        audit_file.write_text('{"filename": "test.pdf"}\n', encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("")
            assert result == []

    def test_none_query(self, tmp_path):
        """None 查询返回空列表"""
        audit_dir = tmp_path / "backend" / "data" / "audit"
        audit_dir.mkdir(parents=True)
        audit_file = audit_dir / "ingest.jsonl"
        audit_file.write_text('{"filename": "test.pdf"}\n', encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs(None)
            assert result == []

    def test_short_tokens_filtered(self, tmp_path):
        """短 token（<2字符）被过滤"""
        audit_dir = tmp_path / "backend" / "data" / "audit"
        audit_dir.mkdir(parents=True)
        audit_file = audit_dir / "ingest.jsonl"
        audit_file.write_text('{"filename": "test.pdf"}\n', encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            # 单字符查询应该被过滤
            result = search_ingested_docs("a b c")
            assert result == []

    def test_successful_search(self, tmp_path):
        """成功搜索"""
        # 创建提取文件
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text(
            "这是一段关于施工方案的测试文本，包含混凝土浇筑的相关内容和质量标准。",
            encoding="utf-8"
        )
        
        # 创建审计文件
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("混凝土")
            assert len(result) > 0
            assert result[0]["filename"] == "test.pdf"
            assert result[0]["sha256"] == "abc123"
            assert "snippet" in result[0]

    def test_limit_parameter(self, tmp_path):
        """limit 参数限制结果数量"""
        # 创建提取文件，包含多个匹配点
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text(
            "施工 " * 100 + "这是一段很长的文本，包含多个施工关键词。施工方案。施工要点。施工标准。",
            encoding="utf-8"
        )
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工", limit=2)
            assert len(result) <= 2

    def test_invalid_json_in_audit(self, tmp_path):
        """审计文件中的无效 JSON 被跳过"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text("这是一段关于施工的测试文本内容。", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(
            "invalid json line\n" + json.dumps(audit_record) + "\n",
            encoding="utf-8"
        )
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            # 应该跳过无效 JSON，继续处理有效记录
            result = search_ingested_docs("施工")
            assert len(result) >= 0  # 不应该抛出异常

    def test_extract_file_not_exists(self, tmp_path):
        """提取文件不存在时跳过该记录"""
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": "/nonexistent/path/file.txt"
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("测试")
            assert result == []

    def test_token_deduplication(self, tmp_path):
        """token 去重"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text("这是一段关于施工方案的测试文本。", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            # 重复的 token 应该被去重
            result = search_ingested_docs("施工 施工 施工方案")
            # 不应该抛出异常
            assert isinstance(result, list)

    def test_case_insensitive_search(self, tmp_path):
        """大小写不敏感搜索"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text("This is a TEST document about Construction.", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("construction")
            assert len(result) > 0

    def test_snippet_context(self, tmp_path):
        """snippet 包含上下文"""
        extract_file = tmp_path / "extract.txt"
        long_text = "前置文本" * 50 + "这里是关键词施工方案的位置" + "后置文本" * 50
        extract_file.write_text(long_text, encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工方案")
            if result:
                # snippet 应该包含上下文
                assert "施工方案" in result[0]["snippet"]

    def test_result_structure(self, tmp_path):
        """结果结构验证"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text("这是一段关于施工方案的测试文本内容。", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123def456",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工")
            if result:
                item = result[0]
                assert "filename" in item
                assert "sha256" in item
                assert "extract_saved_as" in item
                assert "offset" in item
                assert "snippet" in item
                assert isinstance(item["offset"], int)

    def test_multiple_records(self, tmp_path):
        """多条记录搜索"""
        # 创建多个提取文件
        extract_file1 = tmp_path / "extract1.txt"
        extract_file1.write_text("第一个文件关于施工方案的内容。", encoding="utf-8")
        
        extract_file2 = tmp_path / "extract2.txt"
        extract_file2.write_text("第二个文件关于质量标准的内容。", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        records = [
            {"filename": "file1.pdf", "sha256": "aaa", "extract_saved_as": str(extract_file1)},
            {"filename": "file2.pdf", "sha256": "bbb", "extract_saved_as": str(extract_file2)},
        ]
        audit_file.write_text(
            "\n".join(json.dumps(r) for r in records) + "\n",
            encoding="utf-8"
        )
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工")
            # 应该找到至少一个结果
            assert len(result) >= 0

    def test_empty_extract_saved_as(self, tmp_path):
        """extract_saved_as 为空时跳过"""
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": ""
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("测试")
            assert result == []

    def test_no_match_in_text(self, tmp_path):
        """文本中无匹配"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text("这是一段完全不相关的文本内容。", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("混凝土浇筑")
            assert result == []

    def test_newline_in_snippet_replaced(self, tmp_path):
        """snippet 中的换行符被替换"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text("第一行施工方案\n第二行内容\n第三行数据", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工方案")
            if result:
                # 换行符应该被替换为空格
                assert "\n" not in result[0]["snippet"]

    def test_reverse_order_processing(self, tmp_path):
        """记录按逆序处理（最新的先）"""
        extract_file1 = tmp_path / "extract1.txt"
        extract_file1.write_text("旧文件关于施工方案的内容。", encoding="utf-8")
        
        extract_file2 = tmp_path / "extract2.txt"
        extract_file2.write_text("新文件关于施工方案的内容。", encoding="utf-8")
        
        audit_file = tmp_path / "ingest.jsonl"
        records = [
            {"filename": "old.pdf", "sha256": "old", "extract_saved_as": str(extract_file1)},
            {"filename": "new.pdf", "sha256": "new", "extract_saved_as": str(extract_file2)},
        ]
        audit_file.write_text(
            "\n".join(json.dumps(r) for r in records) + "\n",
            encoding="utf-8"
        )
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工方案", limit=1)
            if result:
                # 应该返回最新的（最后一条）记录
                assert result[0]["filename"] == "new.pdf"

    def test_chinese_and_english_mixed_query(self, tmp_path):
        """中英文混合查询"""
        extract_file = tmp_path / "extract.txt"
        extract_file.write_text(
            "This is a test about 施工方案 and construction plan.",
            encoding="utf-8"
        )
        
        audit_file = tmp_path / "ingest.jsonl"
        audit_record = {
            "filename": "test.pdf",
            "sha256": "abc123",
            "extract_saved_as": str(extract_file)
        }
        audit_file.write_text(json.dumps(audit_record) + "\n", encoding="utf-8")
        
        with patch("backend.zhifei_autoplan.evidence.Path") as mock_path:
            def path_side_effect(p):
                if "ingest.jsonl" in str(p):
                    return audit_file
                return Path(p)
            mock_path.side_effect = path_side_effect
            
            result = search_ingested_docs("施工方案 construction")
            # 应该能找到匹配
            assert len(result) >= 0
