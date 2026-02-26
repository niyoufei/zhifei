from __future__ import annotations

import pytest

from backend.zhifei_autoplan.v2.quantitative_boq_engine import (
    QuantitativeBoQEngine,
    QuantitativeSupportError,
    assert_paragraph_quantitative_support,
    assert_section_bundle_support,
)


def _sample_boq_payload():
    return {
        "items": [
            {"boq_code": "A01", "name": "土方开挖", "quantity": 2400, "unit": "m3"},
            {"boq_code": "B01", "name": "基础承台混凝土", "quantity": 900, "unit": "m3"},
            {"boq_code": "C01", "name": "主体结构钢筋", "quantity": 1200, "unit": "t"},
            {"boq_code": "D01", "name": "机电管道安装", "quantity": 650, "unit": "m"},
            {"boq_code": "E01", "name": "装饰装修", "quantity": 500, "unit": "m2"},
        ]
    }


def test_build_quantitative_index_contains_mapping_and_cpm() -> None:
    engine = QuantitativeBoQEngine()
    result = engine.build_quantitative_index(_sample_boq_payload())

    assert "mapping_3d" in result
    assert "cpm" in result
    assert "chapter_structure" in result
    assert "indices" in result

    mapping = result["mapping_3d"]
    assert "土方开挖" in mapping
    assert mapping["土方开挖"]["process"] == "土方工程"
    assert mapping["基础承台混凝土"]["predecessors"]

    cpm = result["cpm"]
    assert cpm["project_duration_days"] > 0
    assert cpm["min_process_interval_days"] >= 1
    assert 0.0 <= cpm["risk_index"] <= 1.0
    assert len(cpm["critical_path"]) >= 1

    chapter = result["chapter_structure"]
    assert chapter["chapter_count"] >= 1
    assert isinstance(chapter["chapters"], list)

    indices = result["indices"]
    for key in (
        "quantity_scale_index",
        "resource_density_index",
        "construction_density_index",
        "complexity_index",
        "duration_index",
        "risk_index",
    ):
        assert key in indices
        assert 0.0 <= float(indices[key]) <= 1.0

    optimization = result.get("optimization") or {}
    assert optimization.get("enabled") is True
    assert int(optimization.get("scenario_total") or 0) >= 2
    assert isinstance(optimization.get("pareto_front_ids"), list)
    best = optimization.get("best_scenario") or {}
    assert str(best.get("scenario_id") or "").strip()
    assert "composite_score" in best


def test_optimize_execution_plan_respects_objective_weights() -> None:
    engine = QuantitativeBoQEngine()
    payload = _sample_boq_payload()
    result = engine.optimize_execution_plan(payload, objective_weights={"duration": 0.7, "risk": 0.2, "resource_density": 0.1})
    assert result["enabled"] is True
    assert int(result["scenario_total"]) >= 2
    weights = result["objective_weights"]
    assert pytest.approx(sum(float(weights[k]) for k in ("duration", "risk", "resource_density")), rel=1e-6) == 1.0
    best = result["best_scenario"]
    assert float(best["composite_score"]) <= 1.0
    assert float(best["composite_score"]) >= 0.0


def test_assert_paragraph_quantitative_support_passes() -> None:
    paragraph = "混凝土浇筑厚度30cm，每天2次检查，由质量员验收。"
    assert_paragraph_quantitative_support(
        paragraph,
        boq_support={"boq_code": "B01", "quantity": 900, "process": "主体结构", "resources": ["混凝土工"]},
    )


def test_assert_paragraph_quantitative_support_fails_without_number() -> None:
    with pytest.raises(QuantitativeSupportError):
        assert_paragraph_quantitative_support(
            "请加强质量管理并严格执行。",
            boq_support={"boq_code": "B01", "process": "主体结构"},
        )


def test_assert_paragraph_quantitative_support_fails_without_support() -> None:
    with pytest.raises(QuantitativeSupportError):
        assert_paragraph_quantitative_support(
            "混凝土浇筑厚度30cm，每天2次检查。",
            boq_support={},
            graph_support={},
        )


def test_assert_section_bundle_support() -> None:
    sections = [
        {"title": "主体结构", "content": "钢筋间距150mm，每班次2次复核，责任人质量员。"},
    ]
    support = {
        "主体结构": {"boq_code": "C01", "quantity": 1200, "process": "主体结构", "resources": ["钢筋工"]}
    }
    assert_section_bundle_support(sections, support_by_title=support)
