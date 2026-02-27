from backend.app.routers.actions_bridge import _apply_generation_mode_policy, _planned_total_pages


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


def test_generation_mode_auto_switch_when_pages_gt_500():
    payload = {
        "generation_mode": "quality_200",
        "total_pages_target": 800,
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

