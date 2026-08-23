from __future__ import annotations

from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections
from backend.zhifei_autoplan.schedule_cpm import build_cpm_receipt


def test_build_cpm_receipt_detects_metric_conflict():
    sections = [
        {
            "title": "进度计划",
            "content": "工期120天。关键线路间隔3天。土方工序工期20天，投入人员30人。",
        },
        {
            "title": "资源配置",
            "content": "资源峰值50人。路基工序工期50天，投入人员20人。",
        },
        {
            "title": "施工部署",
            "content": "面层工序工期20天，投入人员10人。",
        },
    ]
    receipt = build_cpm_receipt(sections, canonical={"工期": "120天", "资源峰值": "50人", "关键线路间隔": "3天"})
    assert isinstance(receipt, dict)
    assert receipt.get("algorithm") == "networkx_cpm_v1"
    assert receipt.get("computed", {}).get("project_duration_days") is not None
    assert isinstance(receipt.get("activities"), list)
    # 20+50+20 = 90, with canonical 120 -> should produce at least one conflict
    assert any((c.get("metric") == "工期") for c in (receipt.get("conflicts") or []))


def test_project_totals_repeated_across_chapters_are_not_cpm_activities():
    sections = [
        {
            "title": f"第{i}章",
            "content": "本项目总工期1216天，资源峰值8人，关键线路间隔3天。",
        }
        for i in range(1, 13)
    ]

    receipt = build_cpm_receipt(sections, canonical={})

    assert receipt.get("conflicts") == []
    assert receipt.get("comparison_eligible") == {
        "工期": False,
        "资源峰值": False,
        "关键线路间隔": False,
    }
    assert receipt.get("computed", {}).get("project_duration_days") is None
    assert receipt.get("computed", {}).get("resource_peak") is None
    assert receipt.get("computed", {}).get("critical_interval_days") is None
    assert "cpm_duration_comparison_skipped_insufficient_activity_metrics" in (
        receipt.get("diagnostic_warnings") or []
    )


def test_plan_consistency_receipt_contains_cpm():
    sections = [
        {"title": "进度计划", "content": "工期30天。关键线路间隔2天。"},
        {"title": "资源计划", "content": "资源峰值12人。"},
    ]
    receipt = normalize_metrics_in_sections(sections)
    assert isinstance(receipt, dict)
    assert "cpm" in receipt
    cpm = receipt.get("cpm") or {}
    assert cpm.get("algorithm") == "networkx_cpm_v1"
