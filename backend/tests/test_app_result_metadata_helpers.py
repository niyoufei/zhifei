from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _load_helpers() -> SimpleNamespace:
    app_path = Path(__file__).resolve().parents[2] / "app.py"
    tree = ast.parse(app_path.read_text(encoding="utf-8"), filename=str(app_path))
    wanted_funcs = {
        "_load_generation_mode_catalog",
        "_coerce_variant_position",
        "_normalize_variant_dict_map",
        "_recent_job_mode_quality_caption",
        "_recent_job_quality_signal",
        "_recent_job_sort_key",
    }
    wanted_assigns = {
        "GENERATION_MODE_CATALOG",
        "GENERATION_MODE_OPTIONS",
        "GENERATION_MODE_LABELS",
        "GENERATION_ENGINE_LABELS",
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


def test_recent_job_mode_quality_caption_renders_stable_delivery_summary():
    helpers = _load_helpers()

    line = helpers._recent_job_mode_quality_caption(
        {
            "generation_mode_summary": {
                "profile": "stable_delivery",
                "mode_effective": "stable_delivery",
                "stable_output": True,
            },
            "logic_template_name": "交付清单驱动",
            "quality_score": 98,
            "quality_gate_ok": False,
            "quality_gate_failed_count": 1,
        }
    )

    assert "档位=稳交：优先结果一致性" in line
    assert "执行=稳定交付执行" in line
    assert "稳定交付" in line
    assert "模板=交付清单驱动" in line
    assert "质量分=98" in line
    assert "质量闸门=未通过" in line
    assert "未通过项=1" in line


def test_recent_job_quality_signal_marks_warning_and_success_cases():
    helpers = _load_helpers()

    warning_signal = helpers._recent_job_quality_signal(
        {
            "quality_score": 98,
            "quality_gate_ok": False,
            "quality_gate_failed_count": 1,
        }
    )
    assert warning_signal["level"] == "warning"
    assert "质量闸门未通过" in warning_signal["message"]
    assert "未通过项=1" in warning_signal["message"]
    assert "质量分=98" in warning_signal["message"]

    success_signal = helpers._recent_job_quality_signal(
        {
            "quality_score": 100,
            "quality_gate_ok": True,
            "quality_gate_failed_count": 0,
        }
    )
    assert success_signal["level"] == "success"
    assert "质量闸门已通过" in success_signal["message"]
    assert "质量分=100" in success_signal["message"]


def test_recent_job_sort_key_prioritizes_running_then_review_needed_done():
    helpers = _load_helpers()

    running = {"status": "running", "updated_at": 100}
    queued = {"status": "queued", "updated_at": 110}
    review_needed_done = {"status": "done", "quality_gate_ok": False, "updated_at": 90}
    failed = {"status": "failed", "updated_at": 120}
    clean_done = {"status": "done", "quality_gate_ok": True, "updated_at": 130}

    ordered = sorted(
        [clean_done, failed, review_needed_done, queued, running],
        key=helpers._recent_job_sort_key,
    )

    assert ordered == [running, queued, review_needed_done, failed, clean_done]
