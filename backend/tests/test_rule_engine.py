# -*- coding: utf-8 -*-
"""
Tests for backend/app/core/rule_engine.py and gap_analyzer.py
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.rule_engine import RuleEngine
from backend.app.core.gap_analyzer import GapAnalyzer


# ============ Fixtures ============

@pytest.fixture
def sample_rules():
    """Sample rules for testing."""
    return [
        {
            "id": "R1",
            "name": "文档结构完整性",
            "description": "检查文档是否包含标题、摘要、正文和结论部分",
            "criteria": ["标题", "摘要", "正文", "结论"],
            "weight": 0.2
        },
        {
            "id": "R2",
            "name": "引用符合规范",
            "description": "文中所有引用均需含来源标注",
            "criteria": ["引用", "页码", "来源"],
            "weight": 0.3
        },
        {
            "id": "R3",
            "name": "内容覆盖评分标准",
            "description": "文档应覆盖所有既定评分点",
            "criteria": ["评分点"],
            "weight": 0.5
        }
    ]


@pytest.fixture
def temp_rules_file(tmp_path, sample_rules):
    """Create a temporary rules file."""
    rules_file = tmp_path / "test_rules.json"
    rules_file.write_text(json.dumps(sample_rules, ensure_ascii=False), encoding="utf-8")
    return str(rules_file)


@pytest.fixture
def empty_rules_file(tmp_path):
    """Create a temporary empty rules file."""
    rules_file = tmp_path / "empty_rules.json"
    rules_file.write_text("[]", encoding="utf-8")
    return str(rules_file)


@pytest.fixture
def single_rule_file(tmp_path):
    """Create a temporary file with single rule."""
    rules = [
        {
            "id": "R1",
            "name": "单一规则",
            "description": "测试单一规则",
            "criteria": ["关键词"],
            "weight": 1.0
        }
    ]
    rules_file = tmp_path / "single_rule.json"
    rules_file.write_text(json.dumps(rules, ensure_ascii=False), encoding="utf-8")
    return str(rules_file)


# ============ RuleEngine Tests ============

class TestRuleEngineInit:
    """Tests for RuleEngine.__init__ and _load_rules."""

    def test_init_with_valid_file(self, temp_rules_file, sample_rules):
        """Test initialization with valid rules file."""
        engine = RuleEngine(temp_rules_file)
        assert engine.rules == sample_rules
        assert len(engine.rules) == 3

    def test_init_with_nonexistent_file(self):
        """Test initialization with nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError) as exc_info:
            RuleEngine("/nonexistent/path/rules.json")
        assert "规则文件不存在" in str(exc_info.value)

    def test_init_with_empty_rules(self, empty_rules_file):
        """Test initialization with empty rules file."""
        engine = RuleEngine(empty_rules_file)
        assert engine.rules == []

    def test_init_loads_chinese_content(self, temp_rules_file):
        """Test that Chinese content is loaded correctly."""
        engine = RuleEngine(temp_rules_file)
        assert engine.rules[0]["name"] == "文档结构完整性"
        assert "标题" in engine.rules[0]["criteria"]


class TestRuleEngineEvaluate:
    """Tests for RuleEngine.evaluate method."""

    def test_evaluate_all_rules_matched(self, temp_rules_file):
        """Test evaluation when all rules are matched."""
        engine = RuleEngine(temp_rules_file)
        text = "本文档包含标题、摘要、正文、结论部分，引用有页码和来源，覆盖所有评分点。"
        result = engine.evaluate(text)
        
        assert result["total_score"] == 1.0  # 0.2 + 0.3 + 0.5
        assert len(result["details"]) == 3
        assert all(d["matched"] for d in result["details"])

    def test_evaluate_no_rules_matched(self, temp_rules_file):
        """Test evaluation when no rules are matched."""
        engine = RuleEngine(temp_rules_file)
        text = "这是一段不包含任何关键词的文本。"
        result = engine.evaluate(text)
        
        assert result["total_score"] == 0.0
        assert all(not d["matched"] for d in result["details"])

    def test_evaluate_partial_match(self, temp_rules_file):
        """Test evaluation with partial rule matches."""
        engine = RuleEngine(temp_rules_file)
        # Only R3 (评分点) should match
        text = "本文档覆盖所有评分点。"
        result = engine.evaluate(text)
        
        assert result["total_score"] == 0.5
        # Check individual rules
        r1 = next(d for d in result["details"] if d["rule_id"] == "R1")
        r2 = next(d for d in result["details"] if d["rule_id"] == "R2")
        r3 = next(d for d in result["details"] if d["rule_id"] == "R3")
        
        assert not r1["matched"]
        assert not r2["matched"]
        assert r3["matched"]

    def test_evaluate_empty_text(self, temp_rules_file):
        """Test evaluation with empty text."""
        engine = RuleEngine(temp_rules_file)
        result = engine.evaluate("")
        
        assert result["total_score"] == 0.0
        assert all(not d["matched"] for d in result["details"])

    def test_evaluate_empty_rules(self, empty_rules_file):
        """Test evaluation with empty rules."""
        engine = RuleEngine(empty_rules_file)
        result = engine.evaluate("任意文本")
        
        assert result["total_score"] == 0.0
        assert result["details"] == []

    def test_evaluate_result_structure(self, temp_rules_file):
        """Test that evaluate returns correct structure."""
        engine = RuleEngine(temp_rules_file)
        result = engine.evaluate("测试文本")
        
        assert "total_score" in result
        assert "details" in result
        assert isinstance(result["total_score"], float)
        assert isinstance(result["details"], list)
        
        for detail in result["details"]:
            assert "rule_id" in detail
            assert "name" in detail
            assert "matched" in detail
            assert "score" in detail
            assert "criteria" in detail
            assert "description" in detail

    def test_evaluate_score_rounding(self, single_rule_file):
        """Test that total_score is rounded to 2 decimal places."""
        engine = RuleEngine(single_rule_file)
        text = "关键词"
        result = engine.evaluate(text)
        
        # Score should be rounded
        assert result["total_score"] == 1.0
        assert isinstance(result["total_score"], float)

    def test_evaluate_all_criteria_required(self, temp_rules_file):
        """Test that all criteria must match for a rule to be matched."""
        engine = RuleEngine(temp_rules_file)
        # Only partial criteria for R1 (missing 结论)
        text = "标题、摘要、正文"
        result = engine.evaluate(text)
        
        r1 = next(d for d in result["details"] if d["rule_id"] == "R1")
        assert not r1["matched"]  # Should not match - missing 结论


# ============ GapAnalyzer Tests ============

class TestGapAnalyzerInit:
    """Tests for GapAnalyzer.__init__."""

    def test_init_creates_rule_engine(self, temp_rules_file):
        """Test that GapAnalyzer creates a RuleEngine instance."""
        analyzer = GapAnalyzer(temp_rules_file)
        assert isinstance(analyzer.engine, RuleEngine)
        assert len(analyzer.engine.rules) == 3

    def test_init_with_nonexistent_file(self):
        """Test initialization with nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            GapAnalyzer("/nonexistent/path/rules.json")


class TestGapAnalyzerAnalyze:
    """Tests for GapAnalyzer.analyze method."""

    def test_analyze_full_coverage(self, temp_rules_file):
        """Test analysis with full coverage."""
        analyzer = GapAnalyzer(temp_rules_file)
        text = "标题、摘要、正文、结论、引用、页码、来源、评分点"
        result = analyzer.analyze(text)
        
        assert result["summary"]["coverage_ratio"] == 1.0
        assert result["summary"]["covered_weight"] == 1.0
        assert result["summary"]["total_weight"] == 1.0
        assert all(d["matched"] for d in result["details"])
        assert all(d["missing_criteria"] == [] for d in result["details"])

    def test_analyze_no_coverage(self, temp_rules_file):
        """Test analysis with no coverage."""
        analyzer = GapAnalyzer(temp_rules_file)
        text = "不相关的文本内容"
        result = analyzer.analyze(text)
        
        assert result["summary"]["coverage_ratio"] == 0.0
        assert result["summary"]["covered_weight"] == 0.0
        assert not any(d["matched"] for d in result["details"])

    def test_analyze_partial_coverage(self, temp_rules_file):
        """Test analysis with partial coverage."""
        analyzer = GapAnalyzer(temp_rules_file)
        # Only R3 matches (weight 0.5)
        text = "评分点"
        result = analyzer.analyze(text)
        
        assert result["summary"]["coverage_ratio"] == 0.5
        assert result["summary"]["covered_weight"] == 0.5
        assert result["summary"]["total_weight"] == 1.0

    def test_analyze_missing_criteria_identified(self, temp_rules_file):
        """Test that missing criteria are correctly identified."""
        analyzer = GapAnalyzer(temp_rules_file)
        # Missing "结论" for R1
        text = "标题、摘要、正文"
        result = analyzer.analyze(text)
        
        r1 = next(d for d in result["details"] if d["rule_id"] == "R1")
        assert not r1["matched"]
        assert "结论" in r1["missing_criteria"]
        assert "标题" not in r1["missing_criteria"]

    def test_analyze_result_structure(self, temp_rules_file):
        """Test that analyze returns correct structure."""
        analyzer = GapAnalyzer(temp_rules_file)
        result = analyzer.analyze("测试")
        
        # Check summary structure
        assert "summary" in result
        assert "details" in result
        assert "covered_weight" in result["summary"]
        assert "total_weight" in result["summary"]
        assert "coverage_ratio" in result["summary"]
        
        # Check details structure
        for detail in result["details"]:
            assert "rule_id" in detail
            assert "name" in detail
            assert "weight" in detail
            assert "criteria" in detail
            assert "matched" in detail
            assert "missing_criteria" in detail

    def test_analyze_empty_rules(self, empty_rules_file):
        """Test analysis with empty rules."""
        analyzer = GapAnalyzer(empty_rules_file)
        result = analyzer.analyze("任意文本")
        
        # Division by zero protection
        assert result["summary"]["coverage_ratio"] == 0.0
        assert result["summary"]["total_weight"] == 0.0
        assert result["details"] == []

    def test_analyze_empty_text(self, temp_rules_file):
        """Test analysis with empty text."""
        analyzer = GapAnalyzer(temp_rules_file)
        result = analyzer.analyze("")
        
        assert result["summary"]["coverage_ratio"] == 0.0
        # All criteria should be missing
        for detail in result["details"]:
            assert not detail["matched"]
            assert detail["missing_criteria"] == detail["criteria"]

    def test_analyze_weight_calculation(self, temp_rules_file):
        """Test that weight calculation is correct."""
        analyzer = GapAnalyzer(temp_rules_file)
        # R1 (0.2) + R3 (0.5) = 0.7
        text = "标题、摘要、正文、结论、评分点"
        result = analyzer.analyze(text)
        
        assert result["summary"]["covered_weight"] == 0.7
        assert result["summary"]["total_weight"] == 1.0
        assert result["summary"]["coverage_ratio"] == 0.7

    def test_analyze_rounding(self, temp_rules_file):
        """Test that results are properly rounded."""
        analyzer = GapAnalyzer(temp_rules_file)
        result = analyzer.analyze("标题、摘要、正文、结论")  # Only R1 matches
        
        # covered_weight should be 0.2, rounded to 4 decimal places
        assert result["summary"]["covered_weight"] == 0.2
        assert result["summary"]["coverage_ratio"] == 0.2


# ============ Integration Tests ============

class TestIntegration:
    """Integration tests for RuleEngine and GapAnalyzer."""

    def test_rule_engine_and_gap_analyzer_consistency(self, temp_rules_file):
        """Test that RuleEngine and GapAnalyzer give consistent results."""
        engine = RuleEngine(temp_rules_file)
        analyzer = GapAnalyzer(temp_rules_file)
        
        text = "标题、摘要、正文、结论、评分点"
        
        engine_result = engine.evaluate(text)
        analyzer_result = analyzer.analyze(text)
        
        # Both should report same matched rules
        for i, detail in enumerate(engine_result["details"]):
            analyzer_detail = analyzer_result["details"][i]
            assert detail["matched"] == analyzer_detail["matched"]
            assert detail["rule_id"] == analyzer_detail["rule_id"]

    def test_chinese_text_handling(self, temp_rules_file):
        """Test that Chinese text is handled correctly."""
        analyzer = GapAnalyzer(temp_rules_file)
        
        # Full Chinese text
        text = """
        本报告标题为《项目文档》，摘要概述了项目概况。
        正文部分详细描述了实施方案。
        结论总结了项目成果。
        所有引用均标注了页码和来源。
        本文档覆盖所有评分点。
        """
        
        result = analyzer.analyze(text)
        assert result["summary"]["coverage_ratio"] == 1.0
