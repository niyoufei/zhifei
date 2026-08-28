from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any


APP_PATH = Path(__file__).resolve().parents[2] / "app.py"


def _app_tree() -> ast.Module:
    return ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))


def _literal_assignment(name: str) -> Any:
    for node in _app_tree().body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing literal assignment: {name}")


def _load_template_helpers() -> SimpleNamespace:
    tree = _app_tree()
    wanted = {"_normalize_template_selection"}
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace: dict[str, Any] = {
        "Any": Any,
        "LOGIC_TEMPLATE_OPTIONS": _literal_assignment("LOGIC_TEMPLATE_OPTIONS"),
        "st": SimpleNamespace(session_state={}),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(APP_PATH), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_template_selection_normalizer_preserves_empty_selection() -> None:
    helpers = _load_template_helpers()
    assert helpers._normalize_template_selection([]) == []


def test_template_selection_normalizer_handles_aliases_and_duplicates() -> None:
    helpers = _load_template_helpers()
    assert helpers._normalize_template_selection(["方案B", "B", "template_c"]) == ["B", "C"]


def test_template_options_and_selected_chip_remain_canonical_ascii() -> None:
    assert _literal_assignment("LOGIC_TEMPLATE_OPTIONS") == ["A", "B", "C", "D", "E"]
    helpers = _load_template_helpers()
    assert helpers._normalize_template_selection(["A", "B", "C", "D", "E"]) == [
        "A",
        "B",
        "C",
        "D",
        "E",
    ]

    tree = _app_tree()
    widgets = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "multiselect"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "版本选择（A/B/C/D/E，可多选）"
    ]
    assert len(widgets) == 1
    widget = widgets[0]
    keywords = {item.arg: item.value for item in widget.keywords if item.arg}
    assert isinstance(keywords.get("options"), ast.Name)
    assert keywords["options"].id == "LOGIC_TEMPLATE_OPTIONS"
    assert "format_func" not in keywords


def test_page_language_guard_precedes_app_content_and_disables_translation() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    guard_html = _literal_assignment("_PAGE_LANGUAGE_GUARD_HTML")

    assert source.index("st.set_page_config(") < source.index("\n_inject_page_language_guard()\n")
    assert source.index("\n_inject_page_language_guard()\n") < source.index("\ndef _load_project_types()")
    assert '<html lang="zh-CN" translate="no" class="notranslate">' in guard_html
    assert 'window.parent.document' in guard_html
    assert 'root.setAttribute("lang", "zh-CN")' in guard_html
    assert 'root.setAttribute("translate", "no")' in guard_html
    assert 'root.classList.add("notranslate")' in guard_html
    assert 'meta[name="google"][content="notranslate"]' in guard_html
    assert "fetch(" not in guard_html
    assert "XMLHttpRequest" not in guard_html

    tree = _app_tree()
    guard_function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_inject_page_language_guard"
    )
    html_call = next(
        node
        for node in ast.walk(guard_function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "html"
    )
    keywords = {item.arg: ast.literal_eval(item.value) for item in html_call.keywords if item.arg}
    assert keywords == {"height": 0, "scrolling": False, "tab_index": -1}


def test_widget_key_is_never_assigned_after_render() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    label = '"版本选择（A/B/C/D/E，可多选）"'
    rendered = source[source.index(label) :]

    assert "on_change=_ensure_selected_templates_state" not in rendered
    assert 'st.session_state["selected_templates"] =' not in rendered


def test_state_initialization_does_not_assign_widget_key() -> None:
    source = APP_PATH.read_text(encoding="utf-8")
    init_state = source.split("def _init_state() -> None:", 1)[1].split("def _set_outline_items", 1)[0]

    assert 'st.session_state["selected_templates"] =' not in init_state
