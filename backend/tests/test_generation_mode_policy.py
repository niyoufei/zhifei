from unittest.mock import patch

from backend.app.routers.actions_bridge import _apply_generation_mode_policy, _merge_plan_defaults, _planned_total_pages


def test_planned_total_pages_prefers_total_pages_target():
    payload = {
        "total_pages_target": 1200,
        "chapter_pages": {"第1章": 2, "第2章": 3},
    }
    assert _planned_total_pages(payload) == 1200


def test_planned_total_pages_from_chapter_pages():
    payload = {
        "chapter_pages": {
            "第1章": 2,
            "第2章": {"pages": 3},
            "第3章": {"target": 5},
        }
    }
    assert _planned_total_pages(payload) == 10


def test_generation_mode_quality_forces_defaults():
    payload = {
        "generation_mode": "quality_200",
        "total_pages_target": 180,
        "agent_parallelism": 2,
        "variant_parallelism": 3,
        "quality_strict": False,
        "auto_remediate": False,
        "remediate_mode": "foo",
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "quality_200"
    assert out["quality_strict"] is True
    assert out["auto_remediate"] is True
    assert out["variant_parallelism"] == 1
    assert out["remediate_mode"] == "template"
    assert out["agent_parallelism"] == 2
    assert out["_mode_policy"]["auto_switched"] is False


def test_generation_mode_auto_switch_when_pages_gt_200():
    payload = {
        "generation_mode": "quality_200",
        "total_pages_target": 220,
        "agent_parallelism": 4,
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "hq_speed_500"
    assert out["agent_parallelism"] >= 6
    assert out["remediate_mode"] == "template"
    assert out["_mode_policy"]["auto_switched"] is True


def test_generation_mode_hq_speed_policy():
    payload = {
        "generation_mode": "hq_speed_500",
        "total_pages_target": 1200,
        "generate_images": None,
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "hq_speed_500"
    assert out["quality_strict"] is True
    assert out["auto_remediate"] is True
    assert out["remediate_mode"] == "template"
    assert out["agent_parallelism"] >= 6
    assert out["variant_parallelism"] >= 1
    assert out["generate_images"] is False


def test_generation_mode_standard_auto_tracks_profile_and_effective_mode():
    payload = {
        "generation_mode": "standard_auto",
        "total_pages_target": 240,
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "standard_auto"
    assert out["_mode_policy"]["profile"] == "standard_auto"
    assert out["_mode_policy"]["mode_effective"] == "hq_speed_500"
    assert out["_mode_policy"]["auto_switched"] is True


def test_generation_mode_speed_fast_policy():
    payload = {
        "generation_mode": "speed_fast",
        "total_pages_target": 80,
        "generate_images": True,
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "speed_fast"
    assert out["_mode_policy"]["mode_effective"] == "speed_fast"
    assert out["agent_parallelism"] >= 8
    assert out["quality_gate_retry_rounds"] == 0
    assert out["generate_images"] is False


def test_generation_mode_pro_polish_policy():
    payload = {
        "generation_mode": "pro_polish",
        "total_pages_target": 80,
        "remediate_mode": "template",
        "agent_parallelism": 9,
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "pro_polish"
    assert out["_mode_policy"]["mode_effective"] == "pro_polish"
    assert out["remediate_mode"] == "llm"
    assert out["quality_gate_retry_rounds"] == 2
    assert out["variant_parallelism"] == 1
    assert out["agent_parallelism"] <= 4


def test_generation_mode_stable_delivery_forces_single_template_when_unspecified():
    payload = {
        "generation_mode": "stable_delivery",
        "total_pages_target": 80,
        "variants": 1,
        "quality_strict": False,
        "auto_remediate": False,
        "remediate_mode": "llm",
    }
    out = _apply_generation_mode_policy(payload)
    assert out["generation_mode"] == "stable_delivery"
    assert out["_mode_policy"]["profile"] == "stable_delivery"
    assert out["_mode_policy"]["mode_effective"] == "stable_delivery"
    assert out["_mode_policy"]["stable_output"] is True
    assert out["_mode_policy"]["deterministic_variant_forced"] is True
    assert out["_mode_policy"]["deterministic_logic_template_id"] == "A"
    assert out["variant_id"] == 1
    assert out["logic_template_id"] == "A"
    assert out["quality_strict"] is True
    assert out["auto_remediate"] is True
    assert out["remediate_mode"] == "template"
    assert out["variant_parallelism"] == 1
    assert out["agent_parallelism"] <= 3


def test_generation_mode_stable_delivery_preserves_explicit_template_selection():
    payload = {
        "generation_mode": "stable_delivery",
        "total_pages_target": 80,
        "variants": 1,
        "logic_template_id": "D",
        "variant_id": 4,
    }
    out = _apply_generation_mode_policy(payload)
    assert out["logic_template_id"] == "D"
    assert out["variant_id"] == 4
    assert out["_mode_policy"]["stable_output"] is True
    assert out["_mode_policy"].get("deterministic_variant_forced") is None


def test_generation_mode_stable_delivery_preserves_forced_marker_on_reapply():
    payload = {
        "generation_mode": "stable_delivery",
        "total_pages_target": 80,
        "variants": 1,
    }
    first = _apply_generation_mode_policy(dict(payload))
    second = _apply_generation_mode_policy(dict(first))
    assert first["_mode_policy"]["deterministic_variant_forced"] is True
    assert first["_mode_policy"]["deterministic_logic_template_id"] == "A"
    assert second["_mode_policy"]["deterministic_variant_forced"] is True
    assert second["_mode_policy"]["deterministic_logic_template_id"] == "A"
    assert second["variant_id"] == 1
    assert second["logic_template_id"] == "A"


def test_merge_plan_defaults_ignores_legacy_scalar_plan():
    payload = {
        "topic": "测试项目",
        "outline": ["工程概况"],
        "chapter_requirements": {},
        "style": {},
        "chapter_pages": {},
    }
    with patch("backend.app.routers.actions_bridge.load_plan", return_value="legacy_plan_id"):
        with patch("backend.app.routers.actions_bridge.load_tender_matrix", return_value={}):
            out = _merge_plan_defaults(dict(payload))
    assert out["outline"] == ["工程概况"]
    assert out["chapter_requirements"] == {}
