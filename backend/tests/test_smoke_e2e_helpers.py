from __future__ import annotations

import ast
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_e2e.py"
    tree = ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))
    wanted_funcs = {
        "_poll_budget",
        "_job_status_tuple",
        "_should_extend_poll_grace",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"Any": Any, "math": math}
    exec(compile(module, str(script_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_poll_budget_uses_ceil_and_has_minimum_one():
    helpers = _load_helpers()
    assert helpers._poll_budget(150.0, 0.5) == 300
    assert helpers._poll_budget(151.0, 0.5) == 302
    assert helpers._poll_budget(0.0, 0.5) == 1


def test_should_extend_poll_grace_for_long_tail_running_stages():
    helpers = _load_helpers()
    assert helpers._should_extend_poll_grace(
        {"status": "running", "progress": {"stage": "variant_running", "percent": 15}}
    )
    assert helpers._should_extend_poll_grace(
        {"status": "running", "progress": {"stage": "exporting", "percent": 92}}
    )
    assert helpers._should_extend_poll_grace(
        {"status": "queued", "progress": {"stage": "queued", "percent": 80}}
    )
    assert not helpers._should_extend_poll_grace(
        {"status": "done", "progress": {"stage": "done", "percent": 100}}
    )
    assert not helpers._should_extend_poll_grace(
        {"status": "running", "progress": {"stage": "agent_ready", "percent": 10}}
    )
