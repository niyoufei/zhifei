from __future__ import annotations

from backend.zhifei_autoplan.qingtian_policy import (
    QINGTIAN_16_CHAPTER_OUTLINE,
    apply_qingtian_outline_policy,
    build_qingtian_chapter_requirements,
    compose_qingtian_global_instruction,
)


def test_compose_qingtian_global_instruction_contains_header_and_user_extra() -> None:
    got = compose_qingtian_global_instruction("所有工序采用A/B/C/D/E结构表达")
    assert "青天适配系统指令" in got
    assert "所有工序采用A/B/C/D/E结构表达" in got


def test_apply_qingtian_outline_policy_uses_16_when_tender_outline_is_fallback() -> None:
    outline, receipt = apply_qingtian_outline_policy(
        outline=["编制说明", "工程概况"],
        outline_source="fallback",
        strict_tender_outline=False,
        payload_outline_given=False,
    )
    assert receipt["used_fallback_16"] is True
    assert outline == QINGTIAN_16_CHAPTER_OUTLINE


def test_apply_qingtian_outline_policy_keeps_outline_when_payload_given() -> None:
    source = ["第一章", "第二章", "第三章"]
    outline, receipt = apply_qingtian_outline_policy(
        outline=source,
        outline_source="fallback",
        strict_tender_outline=False,
        payload_outline_given=True,
    )
    assert receipt["used_fallback_16"] is False
    assert outline == source


def test_build_qingtian_chapter_requirements_for_ch06_contains_fixed_header() -> None:
    reqs = build_qingtian_chapter_requirements("关键工序控制点", 6)
    merged = "\n".join(reqs)
    assert "第06章固定表头" in merged
    assert "工序内容|重点难点|措施|验收" in merged
