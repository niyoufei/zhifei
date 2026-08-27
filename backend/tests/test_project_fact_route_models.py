from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.app.routers import actions_bridge
from backend.app.routers import zhifei_autoplan as legacy


@pytest.mark.parametrize(
    ("model", "base"),
    (
        (actions_bridge.ActionsGenerateRequest, {"topic": "项目"}),
        (actions_bridge.ActionsPlanRequest, {"outline": ["第一章"]}),
        (legacy.GenerateRequest, {"topic": "项目"}),
        (legacy.PlanRequest, {"outline": ["第一章"]}),
    ),
)
def test_route_models_round_trip_project_fact_maps(model, base):
    payload = {
        **base,
        "project_facts": {"planned_duration_days": {"value": 150, "unit": "天"}},
        "approved_project_fact_resolutions": {
            "risk_inspection_frequency": {"value": "逐班"}
        },
    }

    dumped = model.model_validate(payload).model_dump()

    assert dumped["project_facts"] == payload["project_facts"]
    assert (
        dumped["approved_project_fact_resolutions"]
        == payload["approved_project_fact_resolutions"]
    )


@pytest.mark.parametrize(
    ("model", "base"),
    (
        (actions_bridge.ActionsGenerateRequest, {"topic": "项目"}),
        (actions_bridge.ActionsPlanRequest, {"outline": ["第一章"]}),
        (legacy.GenerateRequest, {"topic": "项目"}),
        (legacy.PlanRequest, {"outline": ["第一章"]}),
    ),
)
def test_route_models_reject_non_mapping_project_facts(model, base):
    with pytest.raises(ValidationError):
        model.model_validate({**base, "project_facts": ["not-a-map"]})


def test_actions_plan_merge_inherits_omitted_fact_maps_but_preserves_explicit_clear(
    monkeypatch: pytest.MonkeyPatch,
):
    saved_facts = {"planned_duration_days": {"value": 150, "unit": "天"}}
    saved_resolutions = {"risk_inspection_frequency": {"value": "逐班"}}
    monkeypatch.setattr(
        actions_bridge,
        "load_plan",
        lambda **_kwargs: {
            "project_facts": saved_facts,
            "approved_project_fact_resolutions": saved_resolutions,
        },
    )
    monkeypatch.setattr(actions_bridge, "load_tender_matrix", lambda **_kwargs: {})

    inherited = actions_bridge._merge_plan_defaults(
        actions_bridge.ActionsGenerateRequest(topic="项目", dry_run=True).model_dump()
    )
    cleared = actions_bridge._merge_plan_defaults(
        actions_bridge.ActionsGenerateRequest(
            topic="项目",
            dry_run=True,
            project_facts={},
            approved_project_fact_resolutions={},
        ).model_dump()
    )

    assert inherited["project_facts"] == saved_facts
    assert inherited["approved_project_fact_resolutions"] == saved_resolutions
    assert cleared["project_facts"] == {}
    assert cleared["approved_project_fact_resolutions"] == {}


def test_legacy_plan_merge_inherits_only_omitted_fact_maps():
    saved = {
        "project_facts": {"planned_duration_days": 150},
        "approved_project_fact_resolutions": {"quality_threshold": "按工序验收"},
    }
    omitted = legacy.GenerateRequest(topic="项目").model_dump()
    explicit_clear = legacy.GenerateRequest(
        topic="项目",
        project_facts={},
        approved_project_fact_resolutions={},
    ).model_dump()

    assert legacy._inherit_project_fact_plan_fields(omitted, saved)["project_facts"] == saved[
        "project_facts"
    ]
    assert legacy._inherit_project_fact_plan_fields(omitted, saved)[
        "approved_project_fact_resolutions"
    ] == saved["approved_project_fact_resolutions"]
    assert legacy._inherit_project_fact_plan_fields(explicit_clear, saved)["project_facts"] == {}


def test_legacy_adapter_blocks_default_document_without_delivery_gate(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        legacy,
        "_local_adapter_map_output",
        lambda _result: {
            "status": "pass",
            "export_allowed": True,
            "issues": [],
            "hard_gates": [],
            "evidence_summary": {},
        },
    )

    blocked = legacy._local_adapter_gate_results(
        [{"quality_strict": False, "sections": [], "delivery_ready": False}]
    )

    assert blocked["export_allowed"] is False
    assert {row["code"] for row in blocked["issues"]} == {
        "FORMAL_DELIVERY_QUALITY_GATE_BLOCKED"
    }


def test_legacy_adapter_allows_dry_run_but_requires_exact_formal_pass(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        legacy,
        "_local_adapter_map_output",
        lambda _result: {
            "status": "pass",
            "export_allowed": True,
            "issues": [],
            "hard_gates": [],
            "evidence_summary": {},
        },
    )
    dry_run = legacy._local_adapter_gate_results(
        [{"delivery_scope": "document", "dry_run": True, "delivery_ready": False}]
    )
    formal = legacy._local_adapter_gate_results(
        [
            {
                "delivery_scope": "document",
                "dry_run": False,
                "delivery_ready": True,
                "delivery_quality_gate": {"delivery_allowed": True},
            }
        ]
    )

    assert dry_run["export_allowed"] is True
    assert formal["export_allowed"] is True


def test_actions_formal_export_is_blocked_even_when_quality_strict_is_false():
    with pytest.raises(RuntimeError) as raised:
        actions_bridge._save_outputs(
            "must-not-write",
            [
                {
                    "quality_strict": False,
                    "delivery_quality_gate": {
                        "delivery_allowed": False,
                        "decision_digest": "blocked",
                        "blockers": [{"code": "DELIVERY_MODEL_REVIEW_BLOCKED"}],
                    },
                }
            ],
            preview_only=False,
        )

    payload = json.loads(str(raised.value))
    assert payload["code"] == "DELIVERY_QUALITY_GATE_BLOCKED"
