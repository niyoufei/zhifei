"""
Unit tests for zhifei_autoplan/quality_check.py
Tests cover all functions: text processing, evidence counting, score coverage,
closed loop, engineering checks, template style, remediation, and main entry.
"""

import pytest
from backend.zhifei_autoplan.agents.section_writer import compact_text_to_length_bounds
from backend.zhifei_autoplan.quality_check import (
    _normalize_text,
    _count_evidence,
    _count_evidence_by_section,
    _has_bullets,
    _avg_sentence_len,
    _check_score_coverage,
    _check_score_coverage_by_section,
    _check_closed_loop,
    _check_closed_loop_by_section,
    _check_engineering,
    _check_engineering_by_section,
    _check_template_style,
    _check_required_topics,
    _check_required_topics_detail,
    _check_qse_closed_loop_by_section,
    _extract_risk_triplets,
    apply_remediation,
    run_quality_checks,
    strip_nonconcrete_language,
)


# ========== _normalize_text ==========
class TestNormalizeText:
    def test_removes_spaces(self):
        assert _normalize_text("hello world") == "helloworld"

    def test_removes_newlines(self):
        assert _normalize_text("hello\nworld") == "helloworld"

    def test_removes_both(self):
        assert _normalize_text("hello world\ntest") == "helloworldtest"

    def test_empty_string(self):
        assert _normalize_text("") == ""

    def test_none_input(self):
        assert _normalize_text(None) == ""

    def test_no_changes_needed(self):
        assert _normalize_text("helloworld") == "helloworld"


# ========== _count_evidence ==========
class TestCountEvidence:
    def test_no_evidence(self):
        assert _count_evidence("这是普通文本") == 0

    def test_one_evidence(self):
        assert _count_evidence("这是内容【证据:文档1】结束") == 1

    def test_multiple_evidence(self):
        text = "内容【证据:文档1】中间【证据:文档2】结束【证据:文档3】"
        assert _count_evidence(text) == 3

    def test_empty_string(self):
        assert _count_evidence("") == 0

    def test_partial_match(self):
        # 不完整的证据标记不应计数
        assert _count_evidence("【证据") == 0
        assert _count_evidence("证据:文档】") == 0


# ========== _count_evidence_by_section ==========
class TestCountEvidenceBySection:
    def test_empty_sections(self):
        assert _count_evidence_by_section([]) == []

    def test_single_section_no_evidence(self):
        sections = [{"title": "章节1", "content": "普通内容"}]
        result = _count_evidence_by_section(sections)
        assert result == [{"title": "章节1", "evidence_count": 0}]

    def test_single_section_with_evidence(self):
        sections = [{"title": "章节1", "content": "内容【证据:文档1】【证据:文档2】"}]
        result = _count_evidence_by_section(sections)
        assert result == [{"title": "章节1", "evidence_count": 2}]

    def test_multiple_sections(self):
        sections = [
            {"title": "章节1", "content": "【证据:文档1】"},
            {"title": "章节2", "content": "无证据"},
            {"title": "章节3", "content": "【证据:A】【证据:B】【证据:C】"},
        ]
        result = _count_evidence_by_section(sections)
        assert result == [
            {"title": "章节1", "evidence_count": 1},
            {"title": "章节2", "evidence_count": 0},
            {"title": "章节3", "evidence_count": 3},
        ]

    def test_missing_content(self):
        sections = [{"title": "章节1"}]
        result = _count_evidence_by_section(sections)
        assert result == [{"title": "章节1", "evidence_count": 0}]

    def test_none_content(self):
        sections = [{"title": "章节1", "content": None}]
        result = _count_evidence_by_section(sections)
        assert result == [{"title": "章节1", "evidence_count": 0}]


# ========== _has_bullets ==========
class TestHasBullets:
    def test_dash_bullet(self):
        assert _has_bullets("- 项目1") is True

    def test_dot_bullet(self):
        assert _has_bullets("•项目1") is True

    def test_number_paren(self):
        assert _has_bullets("1)项目") is True
        assert _has_bullets("2)项目") is True
        assert _has_bullets("3)项目") is True

    def test_chinese_paren(self):
        assert _has_bullets("（1）项目") is True
        assert _has_bullets("（2）项目") is True
        assert _has_bullets("（3）项目") is True

    def test_circled_numbers(self):
        assert _has_bullets("①项目") is True
        assert _has_bullets("②项目") is True
        assert _has_bullets("③项目") is True

    def test_no_bullets(self):
        assert _has_bullets("这是普通文本没有项目符号") is False

    def test_empty_string(self):
        assert _has_bullets("") is False

    def test_multiple_bullet_types(self):
        text = "- 第一项\n1)第二项\n•第三项"
        assert _has_bullets(text) is True


# ========== _avg_sentence_len ==========
class TestAvgSentenceLen:
    def test_single_sentence(self):
        text = "这是一个测试句子。"
        result = _avg_sentence_len(text)
        assert result == pytest.approx(9.0, rel=0.1)

    def test_multiple_sentences(self):
        text = "短句。这是一个较长的句子。"
        result = _avg_sentence_len(text)
        # "短句。" -> "短句" (2 chars), "这是一个较长的句子。" -> "这是一个较长的句子" (9 chars)
        # But the function splits on "。\n" after replace, so "短句。\n" becomes ["短句", "这是一个较长的句子"]
        # Total: 2 + 11 = 13, parts = 2, avg = 6.5
        assert result == pytest.approx(6.5, rel=0.1)

    def test_semicolon_delimiter(self):
        text = "句子一；句子二"
        result = _avg_sentence_len(text)
        # "句子一；" -> "句子一" (3 chars), "句子二" (3 chars) + trailing "。\n" creates ["句子一", "句子二"]
        # After replace: "句子一。\n句子二" -> ["句子一", "句子二"] = 3+4=7, avg=3.5
        assert result == pytest.approx(3.5, rel=0.1)

    def test_empty_string(self):
        assert _avg_sentence_len("") == 0.0

    def test_no_delimiters(self):
        text = "没有句号或分号的文本"
        result = _avg_sentence_len(text)
        assert result == pytest.approx(10.0, rel=0.1)

    def test_whitespace_only(self):
        assert _avg_sentence_len("   \n  ") == 0.0


# ========== _check_score_coverage ==========
class TestCheckScoreCoverage:
    def test_no_tender(self):
        result = _check_score_coverage(None, [])
        assert result == {"ok": False, "missing": [], "reason": "tender_matrix_missing"}

    def test_empty_tender(self):
        # Empty dict {} is falsy in `if not tender:` check, so returns tender_matrix_missing
        result = _check_score_coverage({}, [{"content": "测试内容"}])
        assert result == {"ok": False, "missing": [], "reason": "tender_matrix_missing"}

    def test_all_keywords_found(self):
        tender = {
            "items": [
                {"dimension": "质量", "keywords": ["质量控制", "检验"]},
                {"dimension": "安全", "keywords": ["安全管理", "防护"]},
            ]
        }
        sections = [{"content": "质量控制措施和安全管理规范"}]
        result = _check_score_coverage(tender, sections)
        assert result["ok"] is True
        assert result["missing"] == []

    def test_some_keywords_missing(self):
        tender = {
            "items": [
                {"dimension": "质量", "keywords": ["质量控制", "检验"]},
                {"dimension": "环保", "keywords": ["环境保护", "绿色施工"]},
            ]
        }
        sections = [{"content": "质量控制措施"}]
        result = _check_score_coverage(tender, sections)
        assert result["ok"] is False
        assert len(result["missing"]) == 1
        assert result["missing"][0]["dimension"] == "环保"

    def test_keywords_limited_to_six(self):
        tender = {
            "items": [
                {
                    "dimension": "测试",
                    "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8"],
                }
            ]
        }
        sections = [{"content": "无相关关键词"}]
        result = _check_score_coverage(tender, sections)
        # Should only check first 6 keywords
        assert len(result["missing"][0]["keywords"]) == 6

    def test_empty_sections(self):
        tender = {"items": [{"dimension": "质量", "keywords": ["质量"]}]}
        result = _check_score_coverage(tender, [])
        assert result["ok"] is False


# ========== _check_score_coverage_by_section ==========
class TestCheckScoreCoverageBySection:
    def test_no_tender(self):
        result = _check_score_coverage_by_section(None, [{"title": "章节1"}])
        assert result == []

    def test_single_section_all_covered(self):
        tender = {"items": [{"dimension": "质量", "keywords": ["质量控制"]}]}
        sections = [{"title": "章节1", "content": "质量控制措施"}]
        result = _check_score_coverage_by_section(tender, sections)
        assert len(result) == 1
        assert result[0]["title"] == "章节1"
        assert result[0]["ok"] is True
        assert result[0]["missing"] == []

    def test_single_section_missing(self):
        tender = {"items": [{"dimension": "质量", "keywords": ["质量控制"]}]}
        sections = [{"title": "章节1", "content": "普通内容"}]
        result = _check_score_coverage_by_section(tender, sections)
        assert result[0]["ok"] is False
        assert len(result[0]["missing"]) == 1

    def test_multiple_sections(self):
        tender = {"items": [{"dimension": "质量", "keywords": ["质量"]}]}
        sections = [
            {"title": "章节1", "content": "质量内容"},
            {"title": "章节2", "content": "其他内容"},
        ]
        result = _check_score_coverage_by_section(tender, sections)
        assert result[0]["ok"] is True
        assert result[1]["ok"] is False


class TestRequiredTopicsAliases:
    def test_required_topics_accept_aliases(self):
        text = (
            "非标材料；危化品；PPE；劳动力计划；绿色施工；智慧工地；新技术。"
        )
        res = _check_required_topics(text)
        assert res.get("ok") is True
        assert res.get("missing") == []

    def test_required_topics_detail_strict_for_four_new(self):
        sections = [
            {
                "title": "专项",
                "content": (
                    "非标材料：到货验收=1次/批；复验=每批次1次；批次隔离=100%。\n"
                    "危化品：采购资质；储存专库；领用双人复核=1次/单；应急演练=1次/季度。\n"
                    "劳保用品：发放=1套/人；检查=1次/周；更换≤48h。\n"
                    "劳动力计划：钢筋工2人/班；模板工2人/班。\n"
                    "绿色施工：PM10≤150ug/m3；夜间噪声≤55dB；污水pH=6~9。\n"
                    "智慧工地：二维码台账上传频次=1次/日。\n"
                    # Four-new: intentionally missing “投入/步骤/记录”等，应该判定不通过
                    "新技术：适用=材料批次多；验收=台账字段齐全率100%。\n"
                ),
            }
        ]
        res = _check_required_topics_detail(sections)
        assert res.get("ok") is False
        by = res.get("by_topic") or []
        four = [x for x in by if x.get("topic") == "四新技术"][0]
        assert four.get("ok") is False
        assert "投入" in (four.get("missing") or [])

    def test_required_topics_detail_passes_with_executable_four_new(self):
        sections = [
            {
                "title": "专项",
                "content": (
                    "特殊构配件：到货验收=1次/批；复验=每批次1次；批次隔离=100%。\n"
                    "危险化学品：采购资质；储存专库；领用双人复核=1次/单；应急演练=1次/季度。\n"
                    "个人防护：发放=1套/人；检查=1次/周；更换≤48h。\n"
                    "人员配置：钢筋工2人/班；模板工2人/班。\n"
                    "文明环保：扬尘PM10≤150ug/m3；夜间噪声≤55dB；污水pH=6~9。\n"
                    "信息化：二维码台账上传频次=1次/日。\n"
                    "新工艺：适用=防水卷材；投入：人数=8人/班；设备型号=热风焊枪2套；时长=4h/段；"
                    "步骤：1)样板；2)首件；3)焊缝抽检=每100m 1次；"
                    "验收：焊缝抽检合格率≥98%；"
                    "风险：焊缝漏水导致返工；控制：焊缝抽检=每100m 1次；验证：渗漏=0处，记录=《焊缝抽检记录》；偏差处置：不合格≤24h返修复验关闭。\n"
                ),
            }
        ]
        res = _check_required_topics_detail(sections)
        assert res.get("ok") is True


# ========== _check_closed_loop ==========
class TestCheckClosedLoop:
    def test_no_risk(self):
        # Note: "没有风险" contains "风险", so it triggers the risk check
        sections = [{"title": "章节1", "content": "普通内容正常"}]
        result = _check_closed_loop(sections)
        assert result["ok"] is True
        assert result["issues"] == []

    def test_risk_with_measure(self):
        sections = [{"title": "章节1", "content": "存在风险，需采取措施防范"}]
        result = _check_closed_loop(sections)
        assert result["ok"] is True

    def test_risk_with_corresponding(self):
        sections = [{"title": "章节1", "content": "存在风险，有对应方案"}]
        result = _check_closed_loop(sections)
        assert result["ok"] is True

    def test_risk_without_measure(self):
        sections = [{"title": "质量章节", "content": "存在风险需要关注"}]
        result = _check_closed_loop(sections)
        assert result["ok"] is False
        assert len(result["issues"]) == 1
        assert "质量章节" in result["issues"][0]

    def test_multiple_sections_mixed(self):
        sections = [
            {"title": "章节1", "content": "风险分析和措施"},
            {"title": "章节2", "content": "仅提及风险"},
            {"title": "章节3", "content": "普通内容"},
        ]
        result = _check_closed_loop(sections)
        assert result["ok"] is False
        assert len(result["issues"]) == 1

    def test_empty_sections(self):
        result = _check_closed_loop([])
        assert result["ok"] is True
        assert result["issues"] == []


# ========== _check_closed_loop_by_section ==========
class TestCheckClosedLoopBySection:
    def test_no_risk_section(self):
        sections = [{"title": "章节1", "content": "普通内容"}]
        result = _check_closed_loop_by_section(sections)
        assert result[0]["ok"] is True
        assert result[0]["has_risk"] is False
        assert result[0]["has_measure"] is False

    def test_risk_with_measure_section(self):
        sections = [{"title": "章节1", "content": "风险和措施"}]
        result = _check_closed_loop_by_section(sections)
        assert result[0]["ok"] is True
        assert result[0]["has_risk"] is True
        assert result[0]["has_measure"] is True

    def test_risk_without_measure_section(self):
        sections = [{"title": "章节1", "content": "只有风险"}]
        result = _check_closed_loop_by_section(sections)
        assert result[0]["ok"] is False
        assert result[0]["has_risk"] is True
        assert result[0]["has_measure"] is False

    def test_multiple_sections(self):
        sections = [
            {"title": "A", "content": "风险和措施"},
            {"title": "B", "content": "只有风险"},
            {"title": "C", "content": "正常内容"},
        ]
        result = _check_closed_loop_by_section(sections)
        assert result[0]["ok"] is True
        assert result[1]["ok"] is False
        assert result[2]["ok"] is True


# ========== _check_engineering ==========
class TestCheckEngineering:
    def test_all_keys_present(self):
        text = "频次每天，阈值为10，责任人张三，验收标准，流程完整"
        result = _check_engineering(text)
        assert result["ok"] is True
        assert result["missing"] == []

    def test_missing_more_than_two(self):
        text = "频次每天，阈值为10"  # missing: 责任、验收、流程
        result = _check_engineering(text)
        assert result["ok"] is False
        assert len(result["missing"]) == 3

    def test_missing_exactly_two(self):
        text = "频次每天，阈值10，责任人"  # missing: 验收、流程
        result = _check_engineering(text)
        assert result["ok"] is True
        assert len(result["missing"]) == 2

    def test_empty_text(self):
        result = _check_engineering("")
        assert result["ok"] is False
        assert len(result["missing"]) == 5


# ========== _check_engineering_by_section ==========
class TestCheckEngineeringBySection:
    def test_section_all_present(self):
        sections = [{"title": "章节1", "content": "频次阈值责任验收流程"}]
        result = _check_engineering_by_section(sections)
        assert result[0]["ok"] is True
        assert result[0]["missing"] == []

    def test_section_missing_keys(self):
        sections = [{"title": "章节1", "content": "频次"}]
        result = _check_engineering_by_section(sections)
        assert result[0]["ok"] is False
        assert len(result[0]["missing"]) == 4

    def test_multiple_sections(self):
        sections = [
            {"title": "A", "content": "频次阈值责任验收流程"},
            {"title": "B", "content": "只有频次"},
        ]
        result = _check_engineering_by_section(sections)
        assert result[0]["ok"] is True
        assert result[1]["ok"] is False


# ========== _check_template_style ==========
class TestCheckTemplateStyle:
    def test_good_style(self):
        text = "- 项目1\n- 项目2\n- 项目3"  # has bullets, short sentences
        result = _check_template_style(text)
        assert result["ok"] is True
        assert result["has_bullets"] is True

    def test_no_bullets(self):
        text = "这是一段没有项目符号的文本。"
        result = _check_template_style(text)
        assert result["ok"] is False
        assert result["has_bullets"] is False

    def test_long_sentences(self):
        # Sentence > 40 chars - need longer text to exceed avg 40
        long_sentence = "这" * 50 + "。"
        text = "- " + long_sentence
        result = _check_template_style(text)
        # With bullet, avg_sentence_len > 40 should make ok=False
        assert result["has_bullets"] is True
        assert result["avg_sentence_len"] > 40
        assert result["ok"] is False

    def test_empty_text(self):
        result = _check_template_style("")
        assert result["ok"] is False  # no bullets
        assert result["avg_sentence_len"] == 0.0
        assert result["has_bullets"] is False

    def test_ignores_traceability_noise_and_long_codes(self):
        text = (
            "- 项目控制卡【证据:招标文件.pdf#p1_ab12cd34@12】\n"
            "- 工程量=1.1006058002123101e+27m2；编码=ABCDEF1234567890；"
            "参数对照表、验收样表均已建立。【证据:招标文件.pdf#p1_ab12cd34@12】\n"
            "- 责任岗位、验收动作和记录表明确。"
        )
        result = _check_template_style(text)
        assert result["has_bullets"] is True
        assert result["avg_sentence_len"] < 40
        assert result["ok"] is True


# ========== apply_remediation ==========
class TestApplyRemediation:
    def test_empty_remediation(self):
        sections = [{"title": "章节1", "content": "原内容"}]
        apply_remediation(sections, [])
        assert sections[0]["content"] == "原内容"
        assert "auto_remediated" not in sections[0]

    def test_none_remediation(self):
        sections = [{"title": "章节1", "content": "原内容"}]
        apply_remediation(sections, None)
        assert sections[0]["content"] == "原内容"

    def test_score_point_missing(self):
        sections = [{"title": "章节1", "content": "原内容"}]
        remediation = [
            {"title": "章节1", "type": "score_point_missing", "suggestion": "补充质量"}
        ]
        apply_remediation(sections, remediation)
        assert "【自动补充】评分点覆盖建议" in sections[0]["content"]
        assert "补充质量" in sections[0]["content"]
        assert sections[0]["auto_remediated"] is True

    def test_score_point_missing_qse_safety_seeds_tail_keywords_for_final_recheck(self):
        sections = [
            {
                "title": "确保安全生产的技术组织措施",
                "content": "监管红线清单。\n高处和临边防护缺失、临时用电漏保失效、危化品混放一经发现立即停工整改。\n" + "安全巡检记录。" * 900,
                "chapter_domain": "qse",
                "logic_template_id": "D",
            }
        ]
        remediation = [
            {
                "title": "确保安全生产的技术组织措施",
                "type": "score_point_missing",
                "suggestion": "补充评分点覆盖：进度节点，使用短句+要点+量化指标表达。",
                "missing_dimensions": ["进度节点"],
                "missing_keywords": ["工期", "节点", "计划", "进度"],
                "chapter_domain": "qse",
                "template_id": "D",
            }
        ]

        apply_remediation(sections, remediation)

        compacted = compact_text_to_length_bounds(sections[0]["content"], min_length=3000, max_length=8100)
        assert compacted is not None
        assert "重难点" in compacted
        assert "复杂" in compacted
        assert "扣分项" in compacted
        assert "否决项" in compacted
        assert "重大偏差" in compacted

        tender = {
            "items": [
                {"dimension": "重难点", "keywords": ["复杂"]},
                {"dimension": "扣分项", "keywords": ["否决", "重大偏差"]},
            ]
        }
        result = _check_score_coverage_by_section(
            tender,
            [{"title": "确保安全生产的技术组织措施", "content": compacted}],
        )
        assert result[0]["ok"] is True

    def test_risk_measure_gap(self):
        sections = [{"title": "章节1", "content": "原内容"}]
        remediation = [{"title": "章节1", "type": "risk_measure_gap", "suggestion": ""}]
        apply_remediation(sections, remediation)
        assert "【自动补充】风险-措施对应" in sections[0]["content"]
        assert "风险：" in sections[0]["content"]
        assert "措施：" in sections[0]["content"]

    def test_engineering_gap(self):
        sections = [{"title": "章节1", "content": "原内容"}]
        remediation = [{"title": "章节1", "type": "engineering_gap", "suggestion": ""}]
        apply_remediation(sections, remediation)
        assert "【自动补充】工程落地要素" in sections[0]["content"]
        assert "频次" in sections[0]["content"]
        assert "阈值" in sections[0]["content"]

    def test_skip_already_remediated(self):
        sections = [{"title": "章节1", "content": "原内容\n\n【自动补充】评分点覆盖建议：\n- 已有"}]
        remediation = [
            {"title": "章节1", "type": "score_point_missing", "suggestion": "新建议"}
        ]
        apply_remediation(sections, remediation)
        # Should not add more content
        assert sections[0]["content"].count("【自动补充】") == 1
        assert "auto_remediated" not in sections[0]

    def test_title_not_found(self):
        sections = [{"title": "章节1", "content": "原内容"}]
        remediation = [
            {"title": "不存在的章节", "type": "score_point_missing", "suggestion": ""}
        ]
        apply_remediation(sections, remediation)
        assert sections[0]["content"] == "原内容"

    def test_multiple_remediations(self):
        sections = [
            {"title": "章节1", "content": "内容1"},
            {"title": "章节2", "content": "内容2"},
        ]
        remediation = [
            {"title": "章节1", "type": "score_point_missing", "suggestion": "建议1"},
            {"title": "章节2", "type": "engineering_gap", "suggestion": "建议2"},
        ]
        apply_remediation(sections, remediation)
        assert "评分点" in sections[0]["content"]
        assert "工程落地" in sections[1]["content"]

    def test_risk_triplet_gap_remediation_closes_long_qse_section(self):
        filler = "质量过程控制说明。" * 120
        base_content = (
            "【闭环卡片】\n"
            "- 风险：模板位移导致轴线偏差；控制：测量复核频次=2次/日，间距=1000mm；"
            "验证：轴线偏差≤5mm，记录=《测量复核记录表》；偏差处置：超差立即整改，复验合格后关闭。【证据:质检记录#p1_ab12cd34@12】\n"
            "- 风险：钢筋保护层厚度不足；控制：抽检频次=每100m2 1次，保护层垫块厚度=50mm；"
            "验证：保护层偏差≤5mm，记录=《钢筋隐蔽验收记录表》；偏差处置：发现超差立即返工，复查合格后关闭。【证据:隐蔽验收#p2_bc23de45@18】\n"
            "- 风险：混凝土养护时长不足；控制：养护时长=7d，巡检频次=2次/日；"
            "验证：回弹强度满足设计要求，记录=《混凝土养护检查表》；偏差处置：未达标立即补养护，复验通过后关闭。【证据:施工日志#p3_cd34ef56@25】\n"
            + filler
        )
        sections = [{"title": "确保工程质量的技术组织措施", "content": base_content}]
        remediation = [{"title": "确保工程质量的技术组织措施", "type": "risk_triplet_gap", "suggestion": ""}]

        apply_remediation(sections, remediation)

        assert "偏差处置" in sections[0]["content"]
        result = _check_qse_closed_loop_by_section(sections)
        assert result["ok"] is True
        assert result["by_section"][0]["closed_card_count"] >= result["by_section"][0]["target_cards"]

    def test_extract_risk_triplets_accepts_legacy_an_separator(self):
        text = (
            "本章控制要求如下：风险按关键工序质量偏差超限执行，"
            "控制按首件确认=1次/工序并按每100m2 1次实施过程抽检执行，"
            "验证按偏差控制在偏差≤5mm以内执行，记录按《质量抽检记录》执行，"
            "偏差处置按超限后30min内复检执行，未达标立即整改并在2h内关闭。"
        )
        triplets = _extract_risk_triplets(text)
        assert len(triplets) == 1
        assert "关键工序质量偏差超限" in triplets[0]["risk"]
        assert "首件确认=1次/工序" in triplets[0]["control"]
        assert "偏差≤5mm" in triplets[0]["verify"]

    def test_logic_template_anchor_prepended_survives_compaction(self):
        sections = [
            {
                "title": "施工部署",
                "content": "施工部署正文。" * 380,
                "logic_template_id": "A",
                "chapter_domain": "general",
            }
        ]
        remediation = [
            {
                "title": "施工部署",
                "type": "logic_template_adherence_gap",
                "suggestion": "",
                "template_id": "A",
                "chapter_domain": "general",
            }
        ]

        apply_remediation(sections, remediation)
        compacted = compact_text_to_length_bounds(sections[0]["content"], min_length=3000, max_length=4500)

        assert compacted is not None
        assert "本章交付物" in compacted
        assert "约束条件" in compacted

    def test_required_topic_detail_remediation_includes_four_new_investment(self):
        sections = [{"title": "确保安全生产的技术组织措施", "content": "原内容"}]
        remediation = [{"title": "专项主题", "type": "required_topic_detail_gap", "suggestion": "补齐专项细则"}]

        apply_remediation(sections, remediation)

        content = sections[0]["content"]
        assert "四新技术" in content
        assert "投入=" in content
        assert "步骤=" in content
        assert "记录=《四新技术应用台账》" in content

    def test_bureaucratic_phrase_remediation(self):
        sections = [{"title": "章节1", "content": "压实责任，形成工作合力，并加强检查。"}]
        remediation = [
            {"title": "章节1", "type": "bureaucratic_phrase", "suggestion": "改为量化动作"}
        ]
        apply_remediation(sections, remediation)
        assert "压实责任" not in sections[0]["content"]
        assert "形成工作合力" not in sections[0]["content"]
        assert "加强" not in sections[0]["content"]
        assert "【自动补充】替换空话为可执行项" in sections[0]["content"]


class TestStripNonconcreteLanguage:
    def test_strip_nonconcrete_language(self):
        text = "压实责任，形成工作合力，严格检查并确保落实。"
        out = strip_nonconcrete_language(text)
        assert "压实责任" not in out
        assert "形成工作合力" not in out
        assert "严格" not in out
        assert "确保" not in out


# ========== run_quality_checks ==========
class TestRunQualityChecks:
    def test_empty_inputs(self):
        result = run_quality_checks(None, [], [])
        assert "structure" in result
        assert "score_coverage" in result
        assert "closed_loop" in result
        assert "engineering" in result
        assert "evidence" in result
        assert "template_style" in result
        assert "remediation" in result

    def test_structure_check_pass(self):
        outline = ["章节1", "章节2"]
        sections = [
            {"title": "章节1", "content": "内容1"},
            {"title": "章节2", "content": "内容2"},
        ]
        result = run_quality_checks(None, outline, sections)
        assert result["structure"]["ok"] is True
        assert result["structure"]["missing_titles"] == []

    def test_structure_check_fail(self):
        outline = ["章节1", "章节2", "章节3"]
        sections = [{"title": "章节1", "content": "内容1"}]
        result = run_quality_checks(None, outline, sections)
        assert result["structure"]["ok"] is False
        assert "章节2" in result["structure"]["missing_titles"]
        assert "章节3" in result["structure"]["missing_titles"]

    def test_evidence_count(self):
        sections = [
            {"title": "章节1", "content": "【证据:A】【证据:B】"},
            {"title": "章节2", "content": "【证据:C】"},
        ]
        result = run_quality_checks(None, [], sections)
        assert result["evidence"]["evidence_count"] == 3
        assert result["evidence"]["ok"] is True  # 3 >= 2 sections

    def test_evidence_insufficient(self):
        sections = [
            {"title": "章节1", "content": "无证据"},
            {"title": "章节2", "content": "无证据"},
            {"title": "章节3", "content": "无证据"},
        ]
        result = run_quality_checks(None, [], sections)
        assert result["evidence"]["ok"] is False  # 0 < 3 sections

    def test_remediation_score_point(self):
        tender = {"items": [{"dimension": "质量", "keywords": ["质量控制"]}]}
        sections = [{"title": "章节1", "content": "普通内容"}]
        result = run_quality_checks(tender, [], sections)
        assert len(result["remediation"]) >= 1
        assert any(r["type"] == "score_point_missing" for r in result["remediation"])

    def test_remediation_risk_gap(self):
        sections = [{"title": "章节1", "content": "存在风险需要关注"}]
        result = run_quality_checks(None, [], sections)
        assert any(r["type"] == "risk_measure_gap" for r in result["remediation"])

    def test_remediation_risk_gap_skips_when_triplet_exists(self):
        sections = [
            {
                "title": "章节1",
                "content": "风险→控制→验证：风险：交叉作业导致碰撞；控制：错峰作业=1次/班；验证：违章=0次，记录=《巡检表》。",
            }
        ]
        result = run_quality_checks(None, [], sections)
        assert not any(r["type"] == "risk_measure_gap" for r in result["remediation"])

    def test_remediation_engineering_gap(self):
        sections = [{"title": "章节1", "content": "普通内容"}]
        result = run_quality_checks(None, [], sections)
        assert any(r["type"] == "engineering_gap" for r in result["remediation"])

    def test_no_remediation_needed(self):
        tender = {"items": [{"dimension": "质量", "keywords": ["质量"]}]}
        sections = [
            {
                "title": "章节1",
                # Avoid "风险" keyword to prevent risk_measure_gap
                "content": "质量内容正常，频次阈值责任验收流程",
            }
        ]
        result = run_quality_checks(tender, ["章节1"], sections)
        # Should have no remediation for this well-formed section
        assert len(result["remediation"]) == 0

    def test_full_integration(self):
        """Integration test with complete inputs"""
        tender = {
            "items": [
                {"dimension": "质量管理", "keywords": ["质量控制", "质量检验"]},
                {"dimension": "安全管理", "keywords": ["安全措施", "安全防护"]},
            ]
        }
        outline = ["质量章节", "安全章节", "进度章节"]
        sections = [
            {
                "title": "质量章节",
                "content": "- 质量控制措施\n- 频次每日，阈值95%，责任人质检员，验收标准，流程完整【证据:质检报告】",
            },
            {
                "title": "安全章节",
                "content": "- 安全措施\n- 风险分析和对应措施\n- 频次阈值责任验收流程【证据:安全方案】",
            },
        ]
        result = run_quality_checks(tender, outline, sections)

        # Structure: missing "进度章节"
        assert result["structure"]["ok"] is False
        assert "进度章节" in result["structure"]["missing_titles"]

        # Score coverage: both dimensions covered
        assert result["score_coverage"]["ok"] is True

        # Closed loop: all sections have measures
        assert result["closed_loop"]["ok"] is True

        # Evidence: 2 evidence markers for 2 sections
        assert result["evidence"]["ok"] is True

        # Verify by_section results exist
        assert len(result["score_coverage_by_section"]) == 2
        assert len(result["closed_loop_by_section"]) == 2
        assert len(result["engineering_by_section"]) == 2
        assert len(result["evidence"]["by_section"]) == 2


# ========== Edge Cases ==========
class TestEdgeCases:
    def test_section_with_none_values(self):
        sections = [{"title": None, "content": None}]
        result = run_quality_checks(None, [], sections)
        # Should not raise exception
        assert "structure" in result

    def test_tender_with_empty_items(self):
        tender = {"items": []}
        sections = [{"title": "章节1", "content": "内容"}]
        result = run_quality_checks(tender, [], sections)
        assert result["score_coverage"]["ok"] is True

    def test_tender_item_with_no_keywords(self):
        tender = {"items": [{"dimension": "测试", "keywords": []}]}
        sections = [{"title": "章节1", "content": "内容"}]
        result = run_quality_checks(tender, [], sections)
        # No keywords means no hit required: skip score coverage to avoid false alarms
        assert result["score_coverage"]["ok"] is True
        assert result["score_coverage"]["missing"] == []

    def test_unicode_content(self):
        sections = [{"title": "中文标题", "content": "中文内容【证据:中文证据】"}]
        result = run_quality_checks(None, ["中文标题"], sections)
        assert result["structure"]["ok"] is True
        assert result["evidence"]["evidence_count"] == 1

    def test_very_long_content(self):
        long_content = "内容" * 10000 + "【证据:文档】"
        sections = [{"title": "章节1", "content": long_content}]
        result = run_quality_checks(None, [], sections)
        assert result["evidence"]["evidence_count"] == 1

    def test_special_characters_in_content(self):
        content = "内容包含特殊字符：@#$%^&*(){}[]|\\:\";<>?/`~"
        sections = [{"title": "章节1", "content": content}]
        result = run_quality_checks(None, [], sections)
        # Should not raise exception
        assert "structure" in result


class TestStrictQualityGate:
    def test_strict_mode_risk_triplet_and_quantitative(self):
        sections = [
            {
                "title": "安全管理",
                "content": "存在风险，但仅写了措施，没有验证。加强管理。",
            }
        ]
        result = run_quality_checks(None, [], sections, strict=True)
        assert result["risk_triplet"]["ok"] is False
        assert result["quantitative"]["ok"] is False
        assert len(result["issue_list"]) >= 1
        assert any(r["type"] in ("risk_triplet_gap", "quantitative_gap") for r in result["remediation"])

    def test_strict_mode_consistency_conflict(self):
        sections = [
            {"title": "进度计划", "content": "总工期120天，关键线路间隔3天。"},
            {"title": "施工部署", "content": "本项目工期150天，关键线路间隔5天。"},
        ]
        result = run_quality_checks(None, [], sections, strict=True)
        assert result["consistency"]["ok"] is False
        assert any(r["type"] == "consistency_conflict" for r in result["remediation"])

    def test_strict_mode_boq_focus_coverage(self):
        sections = [{"title": "工程概况", "content": "本章未覆盖重点清单项。"}]
        boq_focus = {"must_cover_keywords": ["钢筋混凝土管", "防水卷材"]}
        result = run_quality_checks(None, [], sections, boq_focus=boq_focus, strict=True)
        assert result["boq_focus_coverage"]["ok"] is False
        assert any(i["type"] == "boq_focus_missing" for i in result["issue_list"])

    def test_strict_mode_officialese(self):
        sections = [{"title": "组织保障", "content": "压实责任，形成工作合力，高质量推进。"}]
        result = run_quality_checks(None, [], sections, strict=True)
        assert result["officialese"]["ok"] is False
        assert any(i["type"] == "bureaucratic_phrase" for i in result["issue_list"])

    def test_remediation_strategy_audit_groups_quant_closure_and_evidence(self):
        sections = [
            {
                "title": "安全管理",
                "content": "存在风险，但仅写了措施，没有验证。待补充。【证据:待补充】",
                "chapter_domain": "qse",
                "logic_template_id": "B",
            }
        ]
        result = run_quality_checks(None, [], sections, strict=True)
        audit = result["remediation_strategy_audit"]
        assert isinstance(audit, dict)
        indicator_names = {row["indicator_group"] for row in audit["indicator_groups"]}
        assert "缺量化" in indicator_names
        assert "缺闭环" in indicator_names
        assert "缺证据" in indicator_names
        quant_rec = next(r for r in result["remediation"] if r["type"] == "quantitative_gap")
        assert quant_rec["strategy_id"] == "quant_fill_qse_v1"
        assert quant_rec["indicator_group"] == "缺量化"
        closure_rec = next(r for r in result["remediation"] if r["type"] == "risk_triplet_gap")
        assert closure_rec["strategy_id"] == "risk_triplet_qse_closure_v1"
        evidence_rec = next(r for r in result["remediation"] if r["type"] == "evidence_gap")
        assert evidence_rec["indicator_group"] == "缺证据"

    def test_apply_remediation_writes_strategy_trace(self):
        sections = [{"title": "工程概况", "content": "存在风险。"}]
        remediation = [
            {
                "title": "工程概况",
                "type": "quantitative_gap",
                "suggestion": "补齐量化指标",
                "indicator_group": "缺量化",
                "strategy_id": "quant_fill_general_v1",
                "strategy_name": "量化指标补齐卡",
                "strategy_family": "quantitative_fill",
                "strategy_priority": 95,
                "audit_key": "缺量化/quant_fill_general_v1/工程概况",
            }
        ]
        apply_remediation(sections, remediation)
        trace = sections[0].get("remediation_strategy_trace")
        assert isinstance(trace, list) and trace
        assert trace[0]["strategy_id"] == "quant_fill_general_v1"
        exec_trace = sections[0].get("remediation_execution_trace")
        assert isinstance(exec_trace, list) and exec_trace
        assert "add_quant_value" in exec_trace[0]["detected_action_tags"]
        assert "add_evidence_locator" in exec_trace[0]["detected_action_tags"]
        assert sections[0]["auto_remediated"] is True

    def test_run_quality_checks_includes_remediation_execution_audit(self):
        sections = [
            {
                "title": "工程概况",
                "content": "存在风险。频次：2次/日。【证据:招标文件#p1_ab12cd@12】",
                "remediation_execution_trace": [
                    {
                        "title": "工程概况",
                        "strategy_id": "quant_fill_general_v1",
                        "execution_status": "matched",
                        "detected_action_tags": ["add_quant_value", "add_record_acceptance"],
                    }
                ],
            }
        ]
        result = run_quality_checks(None, [], sections, strict=False)
        audit = result["remediation_execution_audit"]
        assert audit["trace_count"] == 1
        assert audit["action_tags"][0]["action_tag"] == "add_quant_value"
        assert audit["status_counts"][0]["status"] == "matched"
