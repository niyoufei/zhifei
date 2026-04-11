from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_funcs = {
        "_coerce_variant_position",
        "_normalize_variant_dict_map",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(app_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_coerce_variant_position_accepts_variant_labels():
    helpers = _load_helpers()

    assert helpers._coerce_variant_position(3) == 3
    assert helpers._coerce_variant_position("7") == 7
    assert helpers._coerce_variant_position("v12") == 12
    assert helpers._coerce_variant_position(" V5 ") == 5
    assert helpers._coerce_variant_position("bad") is None
    assert helpers._coerce_variant_position(0) is None


def test_normalize_variant_dict_map_prefers_variant_index_then_key_then_variant_id():
    helpers = _load_helpers()

    out = helpers._normalize_variant_dict_map(
        {
            "47": {"variant_index": 1, "variant_id": 47, "quality_score": 98},
            "v2": {"variant_id": 99, "quality_score": 95},
            "bad": {"variant_id": 3, "quality_score": 92},
            "skip": "not-a-dict",
        }
    )

    assert sorted(out.keys()) == [1, 2, 3]
    assert out[1]["quality_score"] == 98
    assert out[2]["variant_id"] == 99
    assert out[3]["quality_score"] == 92
