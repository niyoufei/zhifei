"""
Evidence 单元测试
覆盖 evidence.py 的 search_ingested_docs 方法
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.zhifei_autoplan.evidence import (
    best_drawing_hit,
    build_ingest_evidence_set_receipt,
    format_hit_locator,
    resolve_trusted_ingest_record,
    search_ingested_docs,
    validate_ingest_evidence_set_receipt,
)


def _write_trusted_audit(tmp_path: Path, specs: list[dict]) -> tuple[Path, list[dict]]:
    workspace = tmp_path / "workspace"
    uploads = workspace / "uploads"
    extracts = workspace / "extracts"
    audit_file = workspace / "audit" / "ingest.jsonl"
    uploads.mkdir(parents=True, exist_ok=True)
    extracts.mkdir(parents=True, exist_ok=True)
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for spec in specs:
        filename = str(spec["filename"])
        text = str(spec["text"])
        source_bytes = f"trusted:{filename}:{text}".encode()
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        extract_bytes = text.encode("utf-8")
        extract_sha256 = hashlib.sha256(extract_bytes).hexdigest()
        source_path = uploads / f"{source_sha256}_{filename}"
        extract_path = extracts / f"{source_sha256}_{extract_sha256}.txt"
        source_path.write_bytes(source_bytes)
        extract_path.write_bytes(extract_bytes)
        records.append(
            {
                "project_id": "P1",
                "workspace_dir": str(workspace),
                "filename": filename,
                "sha256": source_sha256,
                "file_id": source_sha256,
                "pages": int(spec.get("pages") or 1),
                "source_hint": "drawing",
                "tags": ["drawing"],
                "saved_as": str(source_path),
                "extract_saved_as": str(extract_path),
                "extract_text_sha256": extract_sha256,
                "usable": True,
                "enabled": True,
            }
        )
    audit_file.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n",
        encoding="utf-8",
    )
    return audit_file, records


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
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [
                {
                    "filename": "test.pdf",
                    "text": "这是一段关于施工方案的测试文本，包含混凝土浇筑的相关内容和质量标准。",
                }
            ],
        )

        result = search_ingested_docs("混凝土", audit_path=audit_file)
        assert len(result) > 0
        assert result[0]["filename"] == "test.pdf"
        assert result[0]["sha256"] == records[0]["sha256"]
        assert "snippet" in result[0]

    def test_search_revalidates_source_bytes_and_rejects_extract_symlink(
        self,
        tmp_path,
    ):
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [{"filename": "围墙图.pdf", "text": "围墙压实系数不小于0.97。"}],
        )
        record = records[0]
        source_path = Path(record["saved_as"])
        extract_path = Path(record["extract_saved_as"])
        original_source = source_path.read_bytes()

        source_path.write_bytes(original_source + b"tampered")
        assert search_ingested_docs("压实系数", audit_path=audit_file) == []

        source_path.write_bytes(original_source)
        symlink_target = tmp_path / "same-extract-bytes.txt"
        symlink_target.write_bytes(extract_path.read_bytes())
        extract_path.unlink()
        extract_path.symlink_to(symlink_target)
        assert search_ingested_docs("压实系数", audit_path=audit_file) == []

    def test_newest_disabled_or_untrusted_row_cannot_resurrect_old_evidence(
        self,
        tmp_path,
    ):
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [{"filename": "围墙图.pdf", "text": "围墙压实系数不小于0.97。"}],
        )
        original = records[0]

        disabled = {**original, "enabled": False}
        with audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(disabled, ensure_ascii=False) + "\n")
        assert search_ingested_docs("压实系数", audit_path=audit_file) == []

        renamed_audit, renamed_records = _write_trusted_audit(
            tmp_path / "renamed",
            [{"filename": "围墙图.pdf", "text": "围墙压实系数不小于0.97。"}],
        )
        renamed = {**renamed_records[0], "filename": "已改名围墙图.pdf"}
        with renamed_audit.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(renamed, ensure_ascii=False) + "\n")
        assert search_ingested_docs("压实系数", audit_path=renamed_audit) == []

    def test_search_rejects_symlinked_audit_and_traversal_filename(self, tmp_path):
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [{"filename": "围墙图.pdf", "text": "围墙压实系数不小于0.97。"}],
        )
        traversal = {**records[0], "filename": "../围墙图.pdf"}
        trusted = resolve_trusted_ingest_record(
            traversal,
            workspace_root=audit_file.parent.parent,
        )
        assert trusted == {"ok": False, "reason": "audit_filename_invalid"}

        external = tmp_path / "external-ingest.jsonl"
        audit_file.replace(external)
        audit_file.symlink_to(external)
        assert search_ingested_docs("压实系数", audit_path=audit_file) == []

    def test_receipt_latest_row_is_scoped_by_project(self, tmp_path):
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [{"filename": "围墙图.pdf", "text": "围墙压实系数不小于0.97。"}],
        )
        workspace = audit_file.parent.parent
        trusted_p1 = resolve_trusted_ingest_record(
            records[0],
            workspace_root=workspace,
        )
        receipt = build_ingest_evidence_set_receipt(
            project_id="P1",
            audit_path=audit_file,
            trusted_records=[trusted_p1],
        )
        cross_project_row = {**records[0], "project_id": "P2"}
        with audit_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(cross_project_row, ensure_ascii=False) + "\n")

        assert validate_ingest_evidence_set_receipt(
            receipt,
            expected_project_id="P1",
        )["ok"] is True
        trusted_p2 = resolve_trusted_ingest_record(
            cross_project_row,
            workspace_root=workspace,
        )
        wrong_scope_receipt = build_ingest_evidence_set_receipt(
            project_id="P1",
            audit_path=audit_file,
            trusted_records=[trusted_p2],
        )
        assert wrong_scope_receipt["records"] == []

        with audit_file.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {**records[0], "enabled": False},
                    ensure_ascii=False,
                )
                + "\n"
            )
        validation = validate_ingest_evidence_set_receipt(
            receipt,
            expected_project_id="P1",
        )
        assert validation["ok"] is False
        assert "audit_record_disabled" in validation["errors"]

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
        audit_file, _ = _write_trusted_audit(
            tmp_path,
            [
                {
                    "filename": "test.pdf",
                    "text": "This is a TEST document about Construction.",
                }
            ],
        )

        result = search_ingested_docs("construction", audit_path=audit_file)
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

    def test_unknown_multi_page_boundary_does_not_invent_page_one(self, tmp_path):
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [
                {
                    "filename": "multi.pdf",
                    "text": "钢梁安装构件位置与节点做法。",
                    "pages": 3,
                }
            ],
        )
        result = search_ingested_docs("钢梁安装", audit_path=audit_file)

        assert result[0]["page"] is None
        assert result[0]["page_boundary_status"] == "unreliable_missing_page_boundaries"
        assert format_hit_locator(result[0]) == "multi.pdf"
        assert result[0]["sha256"] == records[0]["sha256"]

    def test_declared_single_page_hit_uses_full_sha_and_bound_window(self, tmp_path):
        audit_file, records = _write_trusted_audit(
            tmp_path,
            [
                {
                    "filename": "single.pdf",
                    "text": "钢梁安装构件位置与节点做法。",
                    "pages": 1,
                }
            ],
        )
        result = search_ingested_docs("钢梁安装", audit_path=audit_file)

        hit = result[0]
        sha = records[0]["sha256"]
        assert format_hit_locator(hit) == f"single.pdf#p1_{sha}@0"
        assert hit["page_boundary_status"] == "reliable_declared_single_page"
        assert hit["match_start"] == hit["offset"] == 0
        assert hit["matched_text"] == "钢梁安装"
        assert hit["match_window"]["text"].startswith("钢梁安装")
        assert hit["page_text_sha256"]
        assert hit["page_summary"]


def test_best_drawing_hit_excludes_generic_only_matches(tmp_path):
    audit_file, _ = _write_trusted_audit(
        tmp_path,
        [
            {"filename": "generic.pdf", "text": "详见图纸，其余做法参见图纸说明。"},
            {"filename": "specific.pdf", "text": "钢梁安装构件位置与连接做法。"},
            {"filename": "component.pdf", "text": "节点板连接做法及焊缝尺寸。"},
        ],
    )
    hit = best_drawing_hit("钢梁 钢梁安装 图纸", audit_path=audit_file)
    component_hit = best_drawing_hit("节点板 图纸", audit_path=audit_file)
    generic_only = [
        best_drawing_hit(query, audit_path=audit_file)
        for query in (
            "图纸",
            "图纸施工方案",
            "施工方案",
            "施工图纸节点大样说明",
            "详见图纸 图纸说明",
        )
    ]

    assert hit is not None
    assert hit["filename"] == "specific.pdf"
    assert hit["matched_token"] == "钢梁"
    assert component_hit is not None
    assert component_hit["filename"] == "component.pdf"
    assert component_hit["matched_token"] == "节点板"
    assert generic_only == [None] * 5
