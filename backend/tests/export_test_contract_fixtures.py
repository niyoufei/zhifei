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

_ISOLATED_TEST_MODULE_PREFIXES = (
    "PIL",
    "backend.app",
    "backend.kg_loader",
    "backend.utils_write_docx",
    "backend.zhifei_autoplan",
    "compose_engine",
    "docx",
    "fastapi",
    "httpx",
    "openpyxl",
    "starlette",
    "utils_write_docx",
)
_MISSING = object()


def _matches_test_module_scope(
    module_name: str,
    module_prefixes: tuple[str, ...],
) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in module_prefixes
    )


@contextmanager
def isolated_test_module_bindings(
    namespace: dict[str, Any],
    bindings: Mapping[str, tuple[str, str | None]],
    *,
    module_prefixes: Iterable[str] = (),
):
    """Lazily bind dependencies and restore exact scoped modules and globals."""
    effective_prefixes = tuple(
        dict.fromkeys((*_ISOLATED_TEST_MODULE_PREFIXES, *module_prefixes))
    )
    if any(not prefix for prefix in effective_prefixes):
        raise ValueError("module isolation prefixes must be non-empty")

    baseline_modules = {
        module_name: module
        for module_name, module in sys.modules.items()
        if _matches_test_module_scope(module_name, effective_prefixes)
    }
    previous_bindings = {
        binding_name: namespace.get(binding_name, _MISSING)
        for binding_name in bindings
    }
    action_error: BaseException | None = None

    try:
        for binding_name, (module_name, attribute_name) in bindings.items():
            module = import_module(module_name)
            namespace[binding_name] = (
                module if attribute_name is None else getattr(module, attribute_name)
            )
        yield
    except BaseException as exc:
        action_error = exc
        raise
    finally:
        cleanup_errors: list[BaseException] = []

        for binding_name, previous_value in previous_bindings.items():
            try:
                if previous_value is _MISSING:
                    namespace.pop(binding_name, None)
                else:
                    namespace[binding_name] = previous_value
            except BaseException as exc:
                cleanup_errors.append(exc)

        introduced_modules = [
            module_name
            for module_name in tuple(sys.modules)
            if module_name not in baseline_modules
            and _matches_test_module_scope(module_name, effective_prefixes)
        ]
        for module_name in sorted(
            introduced_modules,
            key=lambda name: (name.count("."), len(name)),
            reverse=True,
        ):
            try:
                sys.modules.pop(module_name, None)
            except BaseException as exc:
                cleanup_errors.append(exc)

        for module_name, baseline_module in baseline_modules.items():
            try:
                if (
                    module_name not in sys.modules
                    or sys.modules[module_name] is not baseline_module
                ):
                    sys.modules[module_name] = baseline_module
            except BaseException as exc:
                cleanup_errors.append(exc)

        for binding_name, previous_value in previous_bindings.items():
            try:
                if previous_value is _MISSING:
                    if binding_name in namespace:
                        raise AssertionError(
                            f"test module cleanup left global bound: {binding_name}"
                        )
                elif (
                    binding_name not in namespace
                    or namespace[binding_name] is not previous_value
                ):
                    raise AssertionError(
                        f"test module cleanup did not restore global: {binding_name}"
                    )
            except BaseException as exc:
                cleanup_errors.append(exc)

        remaining_modules = {
            module_name: module
            for module_name, module in sys.modules.items()
            if _matches_test_module_scope(module_name, effective_prefixes)
        }
        if set(remaining_modules) != set(baseline_modules):
            cleanup_errors.append(
                AssertionError(
                    "test module cleanup left an unexpected scoped module set: "
                    f"{sorted(set(remaining_modules) ^ set(baseline_modules))}"
                )
            )
        replaced_modules = sorted(
            module_name
            for module_name, baseline_module in baseline_modules.items()
            if remaining_modules.get(module_name, _MISSING) is not baseline_module
        )
        if replaced_modules:
            cleanup_errors.append(
                AssertionError(
                    "test module cleanup did not restore scoped module objects: "
                    f"{replaced_modules}"
                )
            )

        if cleanup_errors:
            if action_error is not None:
                action_error.add_note(
                    "suppressed module-isolation cleanup errors: "
                    + "; ".join(repr(exc) for exc in cleanup_errors)
                )
            else:
                raise BaseExceptionGroup(
                    "module-isolation cleanup failed",
                    cleanup_errors,
                )


@contextmanager
def isolated_export_module_bindings(
    namespace: dict[str, Any],
    bindings: Mapping[str, tuple[str, str | None]],
):
    """Backward-compatible Export-specific wrapper."""
    with isolated_test_module_bindings(namespace, bindings):
        yield


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
