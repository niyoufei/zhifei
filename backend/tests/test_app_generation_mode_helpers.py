from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_generation_mode_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_assigns = {
        "GENERATION_MODE_CATALOG",
        "GENERATION_MODE_OPTIONS",
        "GENERATION_MODE_LABELS",
        "GENERATION_ENGINE_LABELS",
    }
    wanted_funcs = {
        "_load_generation_mode_catalog",
        "_normalize_generation_mode",
        "_resolve_generation_mode_params",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in wanted_assigns for name in target_names):
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_funcs:
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(app_path), "exec"), namespace)
    return SimpleNamespace(**namespace)


def test_app_generation_mode_catalog_includes_stable_delivery():
    helpers = _load_generation_mode_helpers()

    assert helpers.GENERATION_MODE_OPTIONS == [
        "speed_fast",
        "standard_auto",
        "stable_delivery",
        "pro_polish",
    ]
    assert helpers.GENERATION_MODE_LABELS["stable_delivery"] == "稳交：优先结果一致性"
    assert helpers.GENERATION_ENGINE_LABELS["stable_delivery"] == "稳定交付执行"
    assert any(item["id"] == "stable_delivery" and item["stable_output"] is True for item in helpers.GENERATION_MODE_CATALOG)


def test_app_generation_mode_params_align_stable_delivery_policy():
    helpers = _load_generation_mode_helpers()

    assert helpers._normalize_generation_mode("quality_200") == "standard_auto"
    assert helpers._normalize_generation_mode("stable_delivery") == "stable_delivery"

    out = helpers._resolve_generation_mode_params(
        generation_mode="stable_delivery",
        planned_total_pages=88,
        quality_strict=False,
        auto_remediate=False,
        remediate_mode="llm",
        agent_parallelism=9,
        variant_parallelism=4,
        generate_images=True,
    )

    assert out["generation_mode"] == "stable_delivery"
    assert out["mode_effective"] == "stable_delivery"
    assert out["quality_strict"] is True
    assert out["auto_remediate"] is True
    assert out["remediate_mode"] == "template"
    assert out["variant_parallelism"] == 1
    assert out["agent_parallelism"] == 3
    assert out["generate_images"] is True
    assert out["compare_max_chars"] == 1600
