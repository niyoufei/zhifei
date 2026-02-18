from __future__ import annotations

from backend.zhifei_autoplan.param_trace import build_param_receipt, diff_params_with_receipt


def test_build_param_receipt_substitutes_placeholders_and_tracks_offsets():
    params = {
        "version": "v1",
        "quant_defaults": {"频次": "2次/日"},
        "boq_focus_card": {"抽检频次": "每100m2 1次"},
        "qse_defaults": {"PM10阈值": "≤150ug/m3"},
    }
    sections = [
        {"title": "质量管理", "content": "抽检按[[PARAM:boq_focus_card.抽检频次]]执行；巡检频次[[PARAM:quant_defaults.频次]]。"},
        {"title": "环保管理", "content": "PM10控制值[[PARAM:qse_defaults.PM10阈值]]。"},
    ]
    receipt = build_param_receipt(sections, params)

    assert "每100m2 1次" in sections[0]["content"]
    assert "2次/日" in sections[0]["content"]
    assert "≤150ug/m3" in sections[1]["content"]

    keys = receipt.get("keys") or {}
    assert "boq_focus_card.抽检频次" in keys
    assert "质量管理" in (keys["boq_focus_card.抽检频次"].get("impacted_chapters") or [])
    assert (keys["boq_focus_card.抽检频次"].get("placeholder_occurrences") or [])


def test_diff_params_with_receipt_contains_occurrence_positions():
    before = {
        "quant_defaults": {"频次": "2次/日"},
        "boq_focus_card": {"抽检频次": "每100m2 1次"},
        "qse_defaults": {"PM10阈值": "≤150ug/m3"},
    }
    after = {
        "quant_defaults": {"频次": "3次/日"},
        "boq_focus_card": {"抽检频次": "每100m2 2次"},
        "qse_defaults": {"PM10阈值": "≤120ug/m3"},
    }
    sections = [
        {"title": "质量管理", "content": "抽检按[[PARAM:boq_focus_card.抽检频次]]执行；巡检频次[[PARAM:quant_defaults.频次]]。"},
        {"title": "环保管理", "content": "PM10控制值[[PARAM:qse_defaults.PM10阈值]]。"},
    ]
    receipt = build_param_receipt(sections, before)
    diff = diff_params_with_receipt(before, after, receipt)

    assert diff["changed_count"] == 3
    by_key = {x["key"]: x for x in (diff.get("changed") or [])}
    rec = by_key["quant_defaults.频次"]
    assert rec["impacted_chapter_count"] >= 1
    assert rec["placeholder_occurrence_count"] >= 1
    assert "质量管理" in (rec.get("occurrence_positions") or {})


def test_diff_params_without_receipt_keeps_contract():
    before = {"quant_defaults": {"频次": "2次/日"}}
    after = {"quant_defaults": {"频次": "4次/日"}}
    diff = diff_params_with_receipt(before, after, None)

    assert diff["changed_count"] == 1
    rec = diff["changed"][0]
    assert rec["key"] == "quant_defaults.频次"
    assert rec["impacted_chapters"] == []
    assert rec["occurrence_positions"] == {}
