"""
Unit tests for zhifei_autoplan/quality_check.py
Tests cover all functions: text processing, evidence counting, score coverage,
closed loop, engineering checks, template style, remediation, and main entry.
"""

import pytest
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
    _check_boq_focus_item_closure,
    _check_boq_focus_item_typed_evidence,
    apply_remediation,
    ensure_local_export_mandatory_content,
    run_quality_checks,
    strip_nonconcrete_language,
)
from backend.zhifei_autoplan.boq_focus_enforcer import ensure_boq_focus_item_cards


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


class TestEnsureLocalExportMandatoryContent:
    def test_adds_both_control_tables_to_a_preferred_section(self):
        sections = [
            {"title": "第一章 工程概况", "content": "项目概况。"},
            {"title": "第十二章 安全风险与控制措施", "content": "风险识别与措施闭环。"},
        ]

        added = ensure_local_export_mandatory_content(sections)

        assert added == ["劳保用品配置矩阵", "关键工序控制点表"]
        assert "劳保用品配置矩阵" not in sections[0]["content"]
        assert "劳保用品配置矩阵" in sections[1]["content"]
        assert "关键工序控制点表" in sections[1]["content"]
        assert "不另造项目参数" in sections[1]["content"]

    def test_is_idempotent(self):
        sections = [{"title": "安全措施", "content": "风险与措施。"}]

        assert ensure_local_export_mandatory_content(sections)
        first = sections[0]["content"]
        assert ensure_local_export_mandatory_content(sections) == []
        assert sections[0]["content"] == first

    def test_preserves_existing_remediation_source(self):
        sections = [{"title": "安全措施", "content": "风险与措施。", "auto_remediated": "llm"}]

        ensure_local_export_mandatory_content(sections)

        assert sections[0]["auto_remediated"] == "llm"


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
    def test_attaches_independent_content_review_and_delivery_gate(self):
        sections = [
            {
                "title": "安全管理",
                "content": (
                    "项目部每日检查临边防护，安全员按检查表逐项验收并留存记录。"
                    "风险:护栏松动→控制:班前紧固并设置警戒区→验证:每日复测1次且偏差当天关闭。"
                    "【证据:安全检查记录.pdf#p1_ab12cd34@100】"
                ),
            }
        ]

        result = run_quality_checks(None, ["安全管理"], sections, strict=True)

        assert "score" in result
        assert "quality_gate" in result
        assert "independent_content_review" in result
        assert result["score"] == result["independent_content_review"]["score"]
        assert result["quality_gate"] == result["independent_content_review"]["quality_gate"]

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
    def test_boq_closure_checks_the_thirteenth_focus_item(self):
        first_twelve = [f"重点项{i}" for i in range(1, 13)]
        all_thirteen = [*first_twelve, "重点项13"]
        sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
        ensure_boq_focus_item_cards(
            sections,
            {"must_cover_keywords": first_twelve, "lines": []},
            evidence_src="清单.pdf#p1_abcd1234@10",
        )

        result = _check_boq_focus_item_closure(
            {"must_cover_keywords": all_thirteen},
            sections,
        )

        assert len(result["items"]) == 13
        assert result["items"][-1]["item"] == "重点项13"
        assert result["items"][-1]["reason"] == "not_mentioned"
        assert result["ok"] is False

    def test_boq_closure_matches_nfkc_and_whitespace_variants(self):
        sections = [{"title": "主要施工方案", "content": "施工方案内容。"}]
        ensure_boq_focus_item_cards(
            sections,
            {"must_cover_keywords": ["铝 方通吊顶（顶棚四）"], "lines": []},
            evidence_src="清单.pdf#p1_abcd1234@10",
        )

        result = _check_boq_focus_item_closure(
            {"must_cover_keywords": ["铝方通吊顶(顶棚四)"]},
            sections,
        )

        assert result["ok"] is True
        assert result["items"][0]["reason"] == "ok"
        assert result["items"][0]["hit_sections"][0]["mentions_checked"] >= 1

    def test_boq_typed_evidence_matches_nfkc_and_whitespace_variants(self):
        sections = [
            {
                "title": "装饰工程",
                "content": (
                    "铝 方通吊顶（顶棚四）按定位施工。"
                    "【证据:装饰施工图.pdf#p2_abcd1234@20】"
                    "【证据:吊顶标准.pdf#p3_dcba4321@30】"
                ),
            }
        ]

        result = _check_boq_focus_item_typed_evidence(
            {"must_cover_keywords": ["铝方通吊顶(顶棚四)"]},
            sections,
            drawing_names=["装饰施工图.pdf"],
            standard_names=["吊顶标准.pdf"],
        )

        assert result["ok"] is True
        assert result["items"][0]["hit_sections"][0]["has_drawing_evidence"] is True
        assert result["items"][0]["hit_sections"][0]["has_standard_evidence"] is True

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

    def test_strict_mode_does_not_multiply_repeated_project_totals_by_chapter(self):
        sections = [
            {
                "title": f"第{i}章",
                "content": "本项目总工期1216天，资源峰值8人，关键线路间隔3天。",
            }
            for i in range(1, 13)
        ]

        result = run_quality_checks(None, [], sections, strict=True)

        assert result["consistency"]["ok"] is True
        assert result["consistency"]["conflicts"] == []
        cpm = result["consistency"].get("cpm") or {}
        assert cpm.get("comparison_eligible", {}).get("工期") is False

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

    def test_strict_mode_flags_material_cross_chapter_repetition(self):
        shared_a = "项目部建立统一协调机制并持续加强过程管理，确保各专业施工活动有序衔接"
        shared_b = "施工过程中严格落实既定部署并动态优化资源配置，全面保障各项工作顺利推进"
        sections = [
            {
                "title": "第一章",
                "content": f"{shared_a}。{shared_b}。本章分析现场条件并提出组织方法。本章列出主要工作流程和实施顺序。",
            },
            {
                "title": "第二章",
                "content": f"{shared_a}。{shared_b}。本章说明技术路线并梳理关键接口。本章给出责任边界和检查安排。",
            },
        ]

        result = run_quality_checks(None, [], sections, strict=True)

        assert result["repetition_control"]["ok"] is False
        assert any(i["type"] == "repetitive_content" for i in result["issue_list"])

    def test_strict_mode_flags_long_generic_content_without_project_evidence(self):
        generic = (
            "本章围绕总体目标开展系统分析，结合现场条件统筹组织各项工作并做好相互配合。"
            "通过完善管理机制和组织体系推动各项任务有序开展，并根据实际情况持续优化实施安排。"
            "各参与方应加强沟通协调，及时研究有关事项，保障工作过程衔接顺畅并实现预期目标。"
        ) * 4
        result = run_quality_checks(None, [], [{"title": "通用方案", "content": generic}], strict=True)

        assert result["content_specificity"]["ok"] is False
        assert any(i["type"] == "low_specificity" for i in result["issue_list"])

    def test_strict_mode_accepts_long_project_specific_content(self):
        specific = (
            "钢筋进场后按60t为1批复核合格证并见证取样，质量员负责登记《材料验收台账》。"
            "风险:批次混用→控制:分区挂牌并按炉批号追溯→验证:每批核对1次复验报告，偏差当天整改。"
            "【证据:钢筋清单.pdf#p3_ab12cd34@120】"
        ) * 4
        result = run_quality_checks(None, [], [{"title": "钢筋工程", "content": specific}], strict=True)

        assert result["content_specificity"]["ok"] is True

    def test_strict_mode_flags_sparse_chapter_instead_of_encouraging_page_fill(self):
        result = run_quality_checks(
            None,
            [],
            [{"title": "施工部署", "content": "本章说明施工部署和组织安排。"}],
            strict=True,
        )

        assert result["content_density"]["ok"] is False
        assert any(i["type"] == "content_density_gap" for i in result["issue_list"])
        issue = next(i for i in result["issue_list"] if i["type"] == "content_density_gap")
        assert "空白页" in issue["suggestion"]
        assert "重复段落" in issue["suggestion"]

    def test_strict_mode_accepts_concise_but_substantive_chapter(self):
        content = (
            "钢筋进场后按60t为1批复核合格证并见证取样，质量员登记材料验收台账。"
            "风险:批次混用→控制:按炉批号分区挂牌并设置隔离标识→验证:每批核对1次复验报告。"
            "偏差在24小时内整改并由项目总工复核关闭，形成检查记录与移交清单。"
            "加工区、待检区和合格区分别设置责任牌，班组长每日巡检，周例会汇总偏差趋势并更新纠正措施。"
            "【证据:钢筋清单.pdf#p3_ab12cd34@120】"
        )
        result = run_quality_checks(None, [], [{"title": "钢筋工程", "content": content}], strict=True)

        assert result["content_density"]["ok"] is True
