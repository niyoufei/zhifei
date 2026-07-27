from __future__ import annotations

import pytest

from backend.tests.export_test_contract_fixtures import (
    isolated_test_module_bindings,
)


_ACTIONS_REVIEW_RUNTIME_BINDINGS = {
    "_review_items_for_variant": (
        "backend.app.routers.actions_bridge",
        "_review_items_for_variant",
    ),
}


@pytest.fixture(scope="module", autouse=True)
def _isolate_actions_review_runtime_modules():
    with isolated_test_module_bindings(
        globals(),
        _ACTIONS_REVIEW_RUNTIME_BINDINGS,
    ):
        yield


def test_review_items_merge_issue_and_suggestion():
    variant = {
        "sections": [
            {"title": "主要施工方法", "content": "内容A"},
            {"title": "安全措施", "content": "内容B"},
        ],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "主要施工方法",
                    "type": "quantitative_gap",
                    "severity": "high",
                    "problem": "量化不足",
                    "suggestion": "补齐量化指标",
                }
            ],
            "auto_revision_suggestions": [
                {
                    "title": "主要施工方法",
                    "type": "quantitative_gap",
                    "suggestion": "补齐量化指标",
                },
                {
                    "title": "安全措施",
                    "type": "risk_triplet_gap",
                    "suggestion": "补齐风险控制验证",
                },
            ],
        },
    }
    rows = _review_items_for_variant(variant)
    assert isinstance(rows, list)
    # issue_list 1条 + auto_revision_suggestions 去重后 1条
    assert len(rows) == 2
    assert any(r.get("issue_id", "").startswith("I") for r in rows)
    assert any(r.get("issue_id", "").startswith("R") for r in rows)
    # High severity should rank first
    assert rows[0].get("severity") == "high"
