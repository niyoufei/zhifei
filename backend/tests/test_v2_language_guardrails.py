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
    text = "实施混凝土浇筑厚度30cm控制，质量员每班次检查2次。"
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
        return "执行钢筋绑扎间距150mm控制，质量员每班次检查2次。"

    out = rewrite_with_guardrails("加强质量管理。", rewrite_fn=_rewrite, max_rewrite=2)
    assert out["ok"] is True
    assert "质量员" in out["text"]


def test_build_sentence_ast() -> None:
    ast = build_sentence_ast("实施防水施工厚度4mm控制，安全员每班次检查1次")
    assert ast["action"] == "实施"
    assert ast["checker"] == "安全员"
    assert ast["parameter"] is not None
