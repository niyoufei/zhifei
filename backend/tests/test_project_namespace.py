from __future__ import annotations

from backend.zhifei_autoplan.project_namespace import project_storage_key


def test_safe_ascii_project_id_keeps_legacy_storage_name() -> None:
    assert project_storage_key("P-2026_01.alpha") == "P-2026_01.alpha"


def test_chinese_project_ids_remain_readable_and_distinct() -> None:
    first = project_storage_key("合肥运康骨科医院装修改造")
    second = project_storage_key("合肥运康骨科医院扩建工程")

    assert first == "合肥运康骨科医院装修改造"
    assert second == "合肥运康骨科医院扩建工程"
    assert first != second


def test_sanitized_and_truncated_ids_get_full_identity_digest() -> None:
    unsafe_a = project_storage_key("医院/门诊楼")
    unsafe_b = project_storage_key("医院:门诊楼")
    common_prefix_a = project_storage_key("A" * 100 + "-甲")
    common_prefix_b = project_storage_key("A" * 100 + "-乙")

    assert unsafe_a != unsafe_b
    assert common_prefix_a != common_prefix_b
    assert "--" in unsafe_a
    assert len(common_prefix_a) <= 80


def test_storage_key_cannot_escape_project_root() -> None:
    key = project_storage_key("../../敏感项目")

    assert "/" not in key
    assert "\\" not in key
    assert key not in {".", ".."}
