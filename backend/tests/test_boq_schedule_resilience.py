from __future__ import annotations

import time

from backend.zhifei_autoplan.boq_schedule import (
    build_boq_wbs_cpm,
    sanitize_boq_for_generation,
)
from backend.zhifei_autoplan.schedule_cpm import run_cpm


def test_cpm_peak_is_bounded_by_activity_count_not_duration() -> None:
    started = time.perf_counter()

    result = run_cpm(
        [
            {
                "id": "A",
                "name": "超长异常活动",
                "duration_days": 1.0e70,
                "resource_units": 3,
                "deps": [],
            }
        ]
    )

    assert time.perf_counter() - started < 0.5
    assert result["resource_peak"] == 3.0
    assert result["resource_peak_algorithm"] == "interval_sweep_v2"


def test_cpm_interval_sweep_preserves_parallel_resource_peak() -> None:
    result = run_cpm(
        [
            {"id": "A", "name": "A", "duration_days": 10, "resource_units": 3, "deps": []},
            {"id": "B", "name": "B", "duration_days": 5, "resource_units": 4, "deps": []},
        ]
    )

    assert result["resource_peak"] == 7.0


def test_boq_schedule_excludes_outlier_without_losing_valid_quantity() -> None:
    result = build_boq_wbs_cpm(
        {
            "items": [
                {"name": "混凝土工程", "quantity": 120, "resources": []},
                {"name": "混凝土异常行", "quantity": 1.0e70, "resources": []},
                {"name": "混凝土空行", "quantity": None, "resources": []},
            ]
        },
        enterprise_profile={
            "productivity": {"混凝土浇筑": {"value": 10, "unit": "m3/天"}}
        },
    )

    assert result["summary"]["excluded_quantity_count"] == 1
    assert result["summary"]["total_quantity"] == 120.0
    assert result["summary"]["estimated_duration_days"] == 12.0
    assert result["schedule_input_warnings"] == [
        {"code": "BOQ_QUANTITY_OUTLIER_EXCLUDED", "count": 1}
    ]


def test_generation_view_sanitizes_prompt_stats_without_rewriting_source() -> None:
    source = {
        "items": [
            {"name": "正常项", "quantity": 20, "unit": "m3"},
            {"name": "异常项", "quantity": 1.0e70, "unit": "m3"},
        ],
        "stats": {
            "total_quantity": 1.0e70,
            "top_quantity_items": [{"name": "异常项", "quantity": 1.0e70}],
        },
    }

    safe = sanitize_boq_for_generation(source)

    assert source["items"][1]["quantity"] == 1.0e70
    assert safe["items"][1]["quantity"] is None
    assert safe["stats"]["total_quantity"] == 20.0
    assert safe["stats"]["top_quantity_items"][0]["name"] == "正常项"
    assert safe["runtime_validation"]["excluded_quantity_count"] == 1
