from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import sys
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

_EXPORT_TEST_MODULE_PREFIXES = (
    "backend.app",
    "backend.kg_loader",
    "backend.zhifei_autoplan",
    "docx",
    "openpyxl",
)
_MISSING = object()


def _matches_export_test_module_scope(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in _EXPORT_TEST_MODULE_PREFIXES
    )


@contextmanager
def isolated_export_module_bindings(
    namespace: dict[str, Any],
    bindings: Mapping[str, tuple[str, str]],
):
    """Lazily bind Export dependencies and restore their exact module delta."""
    baseline_modules = frozenset(sys.modules)
    previous_bindings = {
        binding_name: namespace.get(binding_name, _MISSING)
        for binding_name in bindings
    }

    try:
        for binding_name, (module_name, attribute_name) in bindings.items():
            module = import_module(module_name)
            namespace[binding_name] = getattr(module, attribute_name)
        yield
    finally:
        for binding_name, previous_value in previous_bindings.items():
            if previous_value is _MISSING:
                namespace.pop(binding_name, None)
            else:
                namespace[binding_name] = previous_value

        introduced_modules = {
            module_name
            for module_name in sys.modules
            if module_name not in baseline_modules
            and _matches_export_test_module_scope(module_name)
        }
        for module_name in sorted(
            introduced_modules,
            key=lambda name: (name.count("."), len(name)),
            reverse=True,
        ):
            sys.modules.pop(module_name, None)

        remaining_modules = sorted(
            module_name
            for module_name in sys.modules
            if module_name not in baseline_modules
            and _matches_export_test_module_scope(module_name)
        )
        if remaining_modules:
            raise AssertionError(
                "Export test module cleanup left scoped modules loaded: "
                f"{remaining_modules}"
            )


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
