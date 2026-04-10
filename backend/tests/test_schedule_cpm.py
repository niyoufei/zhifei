from __future__ import annotations

from backend.zhifei_autoplan.plan_consistency import normalize_metrics_in_sections
from backend.zhifei_autoplan.schedule_cpm import build_cpm_receipt


def test_build_cpm_receipt_detects_metric_conflict():
    sections = [
        {
            "title": "进度计划",
            "content": "工期120天。关键线路间隔3天。土方工序工期40天，投入人员30人。",
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
    # 40+50+20 = 110, with canonical 120 -> should produce at least one conflict
    assert any((c.get("metric") == "工期") for c in (receipt.get("conflicts") or []))


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


def test_build_cpm_receipt_ignores_generic_crew_size_as_resource_peak():
    sections = [
        {"title": "资源计划", "content": "资源峰值12人。"},
        {"title": "施工部署", "content": "技术工种配置：测量工人数=1人/班；钢筋工人数=2人/班；班组人数=8人/班。"},
    ]

    receipt = build_cpm_receipt(sections)

    assert receipt.get("mentioned", {}).get("资源峰值") == "12.0人/台/套"
    assert receipt.get("computed", {}).get("resource_peak") == 12.0
