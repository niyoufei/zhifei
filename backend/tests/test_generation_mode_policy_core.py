from __future__ import annotations

from backend.zhifei_autoplan.generation_mode_policy import (
    apply_generation_mode_policy,
    generation_mode_catalog,
    normalize_logic_template_id,
    planned_total_pages,
)


def test_generation_mode_policy_core_normalizes_logic_template_aliases():
    assert normalize_logic_template_id("template_a") == "A"
    assert normalize_logic_template_id("方案S") == "C"
    assert normalize_logic_template_id("unknown") is None


def test_generation_mode_policy_core_computes_planned_pages_and_stable_delivery_defaults():
    payload = {
        "generation_mode": "stable_delivery",
        "chapter_pages": {"工程概况": 4, "施工部署": {"target": 6}},
        "variants": 1,
    }

    out = apply_generation_mode_policy(payload)

    assert planned_total_pages(payload) == 10
    assert out["generation_mode"] == "stable_delivery"
    assert out["_mode_policy"]["profile"] == "stable_delivery"
    assert out["_mode_policy"]["deterministic_variant_forced"] is True
    assert out["logic_template_id"] == "A"
    assert out["variant_id"] == 1


def test_generation_mode_policy_core_catalog_contains_stable_delivery():
    modes = generation_mode_catalog()

    assert any(item["id"] == "stable_delivery" for item in modes)
