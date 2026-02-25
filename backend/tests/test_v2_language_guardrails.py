from __future__ import annotations

import pytest

from backend.zhifei_autoplan.v2.language_guardrails import (
    GuardrailBugError,
    build_sentence_ast,
    enforce_guardrails,
    rewrite_with_guardrails,
    validate_guardrails,
)


def test_validate_guardrails_passes_for_action_parameter_checker() -> None:
    text = (
        "第一步（定义）：执行工序名称定义，工程量1200m3、标号C30、尺寸900mm，施工员每班次核验1次；"
        "第二步（分析）：实施质量通病与安全隐患分析，风险阈值5%，技术负责人每班次复核1次；"
        "第三步（解决）：执行控制与验证措施，偏差限值3mm、响应时限4h，质量员每班次检查2次；"
        "工序名称->参数->风险->控制->验证。"
    )
    result = validate_guardrails(text)
    assert result["ok"] is True
    assert result["violations"] == []


def test_enforce_guardrails_raises_for_vague_bug_words() -> None:
    text = "加强质量管理，注意安全。"
    with pytest.raises(GuardrailBugError):
        enforce_guardrails(text)


def test_validate_guardrails_detects_missing_checker() -> None:
    text = "执行模板安装间距900mm控制，每班次检查2次。"
    result = validate_guardrails(text)
    assert result["ok"] is False
    assert any("missing_checker" in item["reasons"] for item in result["violations"])


def test_rewrite_with_guardrails_uses_callback() -> None:
    def _rewrite(_text, _violations, _attempt):
        return (
            "第一步（定义）：执行钢筋绑扎定义，工程量100t、标号HRB400、间距150mm，施工员每班次核验1次；"
            "第二步（分析）：实施质量通病与安全隐患分析，风险阈值5%，技术负责人每班次复核1次；"
            "第三步（解决）：执行控制与验证措施，偏差限值3mm、响应时限4h，质量员每班次检查2次；"
            "工序名称->参数->风险->控制->验证。"
        )

    out = rewrite_with_guardrails("加强质量管理。", rewrite_fn=_rewrite, max_rewrite=2)
    assert out["ok"] is True
    assert "质量员" in out["text"]


def test_build_sentence_ast() -> None:
    ast = build_sentence_ast("实施防水施工厚度4mm控制，安全员每班次检查1次")
    assert ast["action"] == "实施"
    assert ast["checker"] == "安全员"
    assert ast["parameter"] is not None


def test_validate_guardrails_fails_without_three_step_logic_lock() -> None:
    text = "执行模板安装间距900mm控制，质量员每班次检查2次。"
    result = validate_guardrails(text)
    assert result["ok"] is False
    assert any("missing_step1_define" in item["reasons"] or "missing_flow_chain" in item["reasons"] for item in result["violations"])
