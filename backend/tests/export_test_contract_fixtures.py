from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


_ADMISSIBLE_EXPORT_SECTION: dict[str, Any] = {
    "title": "第十六章 风险与措施",
    "content": (
        "信息化管理、绿色工地、劳保用品、劳保用品配置矩阵和关键工序控制点表"
        "均纳入本测试输入。参数采用脱敏测试值；检查频次为每班一次；责任人为测试角色；"
        "验收仅核对测试合同；记录写入临时测试目录。风险为测试输入不完整，措施为执行"
        "mandatory-content gate 并保留结构化拒绝结果。"
    ),
    "evidence_refs": ["user_param:r144_export_contract_fixture"],
}


def export_admissible_sections(
    sections: Iterable[Mapping[str, Any]] | None = None,
    *,
    preserve_section_count: bool = False,
) -> list[dict[str, Any]]:
    """Return isolated test sections that satisfy the real export gate."""
    result = [deepcopy(dict(section)) for section in sections or ()]
    if preserve_section_count and result:
        existing = str(result[0].get("content") or "")
        contract_text = (
            f"{_ADMISSIBLE_EXPORT_SECTION['title']}。"
            f"{_ADMISSIBLE_EXPORT_SECTION['content']}"
        )
        result[0]["content"] = f"{existing}\n{contract_text}".strip()
        result[0]["evidence_refs"] = deepcopy(
            _ADMISSIBLE_EXPORT_SECTION["evidence_refs"]
        )
        return result
    result.append(deepcopy(_ADMISSIBLE_EXPORT_SECTION))
    return result
