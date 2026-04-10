from __future__ import annotations

import time

from backend.zhifei_autoplan.boq_schedule import build_boq_wbs_cpm
from backend.zhifei_autoplan.schedule_cpm import run_cpm


def test_run_cpm_uses_event_sweep_for_large_durations() -> None:
    activities = [
        {"id": "A001", "name": "主体施工", "duration_days": 1_000_000_000.0, "resource_units": 5.0, "deps": []},
        {"id": "A002", "name": "机电安装", "duration_days": 1_000_000_000.0, "resource_units": 8.0, "deps": []},
        {"id": "A003", "name": "收尾", "duration_days": 10.0, "resource_units": 3.0, "deps": ["A001"]},
    ]

    started = time.perf_counter()
    result = run_cpm(activities)
    elapsed = time.perf_counter() - started

    assert elapsed < 2.0
    assert result["ok"] is True
    assert result["resource_peak"] == 13.0
    assert result["project_duration_days"] == 1_000_000_010.0


def test_build_boq_wbs_cpm_falls_back_to_item_count_for_corrupted_quantities() -> None:
    boq_data = {
        "items": [
            {
                "name": "语音跳线2M",
                "quantity": 1.2211180156821004e45,
                "unit": "条",
                "unit_price": 1.0,
                "total_price": 1.2211180156821004e45,
                "process": {"name": "电气安装"},
                "resources": [{"name": "电工"}],
            },
            {
                "name": "六类非屏蔽跳线",
                "quantity": 1.3211180156821003e41,
                "unit": "条",
                "unit_price": 1.0,
                "total_price": 1.3211180156821003e41,
                "process": {"name": "电气安装"},
                "resources": [{"name": "电工"}],
            },
        ],
        "stats": {
            "quantity_dispersion": 31.1254,
            "quantity_scale_index": 1.0,
            "construction_density_index": 1.0,
        },
    }

    result = build_boq_wbs_cpm(boq_data, enterprise_profile={})

    assert result["ok"] is True
    assert result["summary"]["schedule_quantity_mode"] == "item_count_proxy"
    assert result["summary"]["schedule_quantity_reason"] in {"quantity_max_abs_guard", "quantity_distribution_guard"}
    assert result["summary"]["estimated_duration_days"] == 2.0
    assert result["summary"]["resource_peak"] == 2.0

    row = result["wbs"][0]
    assert row["process"] == "电气安装"
    assert row["quantity"] == 2.0
    assert row["quantity_proxy_mode"] == "item_count_proxy"
    assert row["quantity_proxy_items"] == 2
