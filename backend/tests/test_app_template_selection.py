from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any


APP_PATH = Path(__file__).resolve().parents[2] / "app.py"


def _load_template_helpers() -> SimpleNamespace:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))
    wanted = {"_normalize_template_selection"}
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace: dict[str, Any] = {
        "Any": Any,
        "LOGIC_TEMPLATE_OPTIONS": ["A", "B", "C", "D", "E"],
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
