from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.terminology_guard import (
    ENGINEERING_RULES_PATH,
    get_labor_ratio_by_condition,
    load_engineering_rules,
    suggest_labor_ratio_for_chapter,
    validate_engineering_rules,
)


def test_single_source_rules_resolve_from_project_root(monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(project_root / "backend")
    report = validate_engineering_rules()
    assert report["ok"] is True
    assert Path(report["path"]).name == "ZhiFei_Engineering_Rules_CN.json"

    rules = load_engineering_rules()
    assert isinstance(rules.get("建筑法定术语词典"), dict)
    assert isinstance(rules.get("劳动力排班算法矩阵"), dict)
    assert isinstance(rules.get("法定工种白名单"), list)


def test_municipal_road_trade_ratio_not_empty():
    out = get_labor_ratio_by_condition(
        project_type="市政基础设施工程",
        size="大型项目",
        stage="道路路基",
        trade_name="筑路工",
        rules_path=ENGINEERING_RULES_PATH,
    )
    assert out["ok"] is True
    assert out.get("trade_domain") == "市政道路工程"
    trade_value = out.get("trade_value") or {}
    assert isinstance(trade_value, dict) and trade_value
    assert "中级工及以上等级技能工人占比" in trade_value


def test_municipal_bridge_trade_ratio_not_empty():
    out = get_labor_ratio_by_condition(
        project_type="市政基础设施工程",
        size="中型项目",
        stage="桥面系",
        trade_name="钢筋工",
        rules_path=ENGINEERING_RULES_PATH,
    )
    assert out["ok"] is True
    assert out.get("trade_domain") == "市政桥梁工程"
    trade_value = out.get("trade_value") or {}
    assert isinstance(trade_value, dict) and trade_value
    assert "高级工及以上等级技能工人占比" in trade_value


def test_suggest_labor_ratio_for_chapter_returns_domain_and_trade_ratio():
    rules = load_engineering_rules(ENGINEERING_RULES_PATH)
    matrix = rules.get("劳动力排班算法矩阵") if isinstance(rules, dict) else {}
    hint = suggest_labor_ratio_for_chapter(
        matrix,
        project_type="市政基础设施工程",
        chapter_title="主要施工方法（道路路基）",
    )
    assert hint.get("trade_domain") == "市政道路工程"
    trade_ratio = hint.get("trade_ratio") or {}
    assert isinstance(trade_ratio, dict) and trade_ratio
