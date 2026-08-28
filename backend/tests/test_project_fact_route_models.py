from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.routers import actions_bridge
from backend.app.routers import zhifei_autoplan as legacy
from backend.zhifei_autoplan.project_fact_approval_audit import (
    parse_project_fact_approval_audit,
    project_fact_value_digest,
)

_APPROVAL_PROJECT_ID = "P-APPROVAL-ROUTE"


def _approval_resolution(
    *,
    field: str = "resource_peak",
    value=80,
    unit: str = "人",
    filename: str,
    source_sha256: str,
) -> dict:
    return {
        "value": value,
        "unit": unit,
        "evidence": {
            "file_name": filename,
            "document_sha256": source_sha256,
            "locator": f"{filename}#sheet=资源计划&cell=B12",
        },
        "approval_receipt": {
            "receipt_id": f"APR-{field}",
            "status": "approved",
            "project_id": _APPROVAL_PROJECT_ID,
            "field": field,
            "value_digest": project_fact_value_digest(
                field=field,
                value=value,
                unit=unit,
            ),
            "summary": f"批准{field}作为正式项目参数",
            "approved_by": "项目负责人",
            "approved_at": "2026-08-28T08:00:00Z",
        },
    }


def _approval_ingest_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module,
    *,
    disable_latest: bool = False,
) -> tuple[dict, Path]:
    data_root = tmp_path / "workspace" / "backend" / "data"
    uploads = data_root / "uploads"
    extracts = data_root / "extracts"
    audit_dir = data_root / "audit"
    uploads.mkdir(parents=True)
    extracts.mkdir()
    audit_dir.mkdir()
    filename = "批准资源计划.xlsx"
    source_bytes = b"approved-resource-plan"
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    extract_bytes = "资源峰值 80 人".encode()
    extract_sha256 = hashlib.sha256(extract_bytes).hexdigest()
    source_path = uploads / f"{source_sha256}_{filename}"
    extract_path = extracts / f"{source_sha256}_{extract_sha256}.txt"
    source_path.write_bytes(source_bytes)
    extract_path.write_bytes(extract_bytes)
    row = {
        "project_id": _APPROVAL_PROJECT_ID,
        "workspace_dir": str(data_root),
        "filename": filename,
        "sha256": source_sha256,
        "file_id": source_sha256,
        "saved_as": str(source_path),
        "extract_saved_as": str(extract_path),
        "extract_text_sha256": extract_sha256,
        "enabled": True,
        "usable": True,
    }
    rows = [row]
    if disable_latest:
        rows.append({**row, "enabled": False, "usable": False})
    ingest_path = audit_dir / "ingest.jsonl"
    ingest_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in rows),
        encoding="utf-8",
    )
    approval_path = audit_dir / "project_fact_approvals.jsonl"
    monkeypatch.setattr(module, "_PROJECT_FACT_INGEST_AUDIT_PATH", ingest_path)
    monkeypatch.setattr(module, "_PROJECT_FACT_APPROVAL_AUDIT_PATH", approval_path)
    return (
        _approval_resolution(
            filename=filename,
            source_sha256=source_sha256,
        ),
        approval_path,
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


@pytest.mark.asyncio
async def test_actions_plan_save_persists_explicit_approval_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    resolution, approval_path = _approval_ingest_fixture(
        tmp_path,
        monkeypatch,
        actions_bridge,
    )
    saved: dict = {}

    monkeypatch.setattr(actions_bridge, "_auth_actions_key", lambda _key: None)
    monkeypatch.setattr(actions_bridge, "load_plan", lambda **_kwargs: {})

    def _save(payload, *, project_id=None):
        saved.update(payload)
        assert project_id == _APPROVAL_PROJECT_ID
        return "saved-plan.json"

    monkeypatch.setattr(actions_bridge, "save_plan", _save)
    request = actions_bridge.ActionsPlanRequest(
        outline=["第一章"],
        approved_project_fact_resolutions={"resource_peak": resolution},
    )

    response = await actions_bridge.actions_plan_save(
        request,
        project_id=_APPROVAL_PROJECT_ID,
        x_actions_key="not-persisted",
    )

    locator = saved["approved_project_fact_resolutions"]["resource_peak"][
        "approval_event"
    ]
    entries = parse_project_fact_approval_audit(approval_path.read_bytes())
    assert response == {"ok": True, "saved_at": "saved-plan.json"}
    assert locator == entries[0]["locator"]
    assert entries[0]["event"]["actor"] == {
        "channel": "actions_key",
        "actor_id": "system-actions",
    }
    assert "not-persisted" not in approval_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_legacy_plan_save_persists_authenticated_user_approval_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    resolution, approval_path = _approval_ingest_fixture(
        tmp_path,
        monkeypatch,
        legacy,
    )
    saved: dict = {}
    monkeypatch.setattr(legacy, "_auth_user", lambda _authorization: {"id": 42})
    monkeypatch.setattr(legacy, "load_plan", lambda **_kwargs: {})
    monkeypatch.setattr(legacy, "_audit", lambda *_args, **_kwargs: None)

    def _save(payload, *, project_id=None):
        saved.update(payload)
        assert project_id == _APPROVAL_PROJECT_ID
        return "saved-plan.json"

    monkeypatch.setattr(legacy, "save_plan", _save)
    request = legacy.PlanRequest(
        outline=["第一章"],
        approved_project_fact_resolutions={"resource_peak": resolution},
    )

    response = await legacy.save_plan_api(
        request,
        project_id=_APPROVAL_PROJECT_ID,
        authorization="Bearer opaque",
    )

    locator = saved["approved_project_fact_resolutions"]["resource_peak"][
        "approval_event"
    ]
    entries = parse_project_fact_approval_audit(approval_path.read_bytes())
    assert response == {"ok": True, "saved_at": "saved-plan.json"}
    assert locator == entries[0]["locator"]
    assert entries[0]["event"]["actor"] == {
        "channel": "authenticated_user",
        "actor_id": "user:42",
    }
    assert "Bearer opaque" not in approval_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_omitted_approvals_are_inherited_without_minting_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    approval_path = tmp_path / "audit" / "project_fact_approvals.jsonl"
    inherited = {"resource_peak": {"value": 80, "unit": "人"}}
    saved: dict = {}
    monkeypatch.setattr(actions_bridge, "_auth_actions_key", lambda _key: None)
    monkeypatch.setattr(
        actions_bridge,
        "load_plan",
        lambda **_kwargs: {"approved_project_fact_resolutions": inherited},
    )
    monkeypatch.setattr(
        actions_bridge,
        "_PROJECT_FACT_APPROVAL_AUDIT_PATH",
        approval_path,
    )
    monkeypatch.setattr(
        actions_bridge,
        "save_plan",
        lambda payload, **_kwargs: saved.update(payload) or "saved-plan.json",
    )

    await actions_bridge.actions_plan_save(
        actions_bridge.ActionsPlanRequest(outline=["第一章"]),
        project_id=_APPROVAL_PROJECT_ID,
        x_actions_key="opaque",
    )

    assert saved["approved_project_fact_resolutions"] == inherited
    assert not approval_path.exists()


@pytest.mark.asyncio
async def test_explicit_invalid_batch_returns_422_without_event_or_plan_save(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    valid, approval_path = _approval_ingest_fixture(
        tmp_path,
        monkeypatch,
        actions_bridge,
    )
    invalid = _approval_resolution(
        field="risk_inspection_frequency",
        value="逐班",
        unit="",
        filename="不存在.docx",
        source_sha256="f" * 64,
    )
    save_called = False
    monkeypatch.setattr(actions_bridge, "_auth_actions_key", lambda _key: None)
    monkeypatch.setattr(actions_bridge, "load_plan", lambda **_kwargs: {})

    def _save(_payload, **_kwargs):
        nonlocal save_called
        save_called = True
        return "should-not-save.json"

    monkeypatch.setattr(actions_bridge, "save_plan", _save)
    request = actions_bridge.ActionsPlanRequest(
        outline=["第一章"],
        approved_project_fact_resolutions={
            "resource_peak": valid,
            "risk_inspection_frequency": invalid,
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await actions_bridge.actions_plan_save(
            request,
            project_id=_APPROVAL_PROJECT_ID,
            x_actions_key="opaque",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == {
        "code": "PROJECT_FACT_APPROVAL_CONFIRMATION_INVALID",
        "reason": "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
    }
    assert save_called is False
    assert not approval_path.exists()


@pytest.mark.asyncio
async def test_latest_disabled_ingest_record_blocks_explicit_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    resolution, approval_path = _approval_ingest_fixture(
        tmp_path,
        monkeypatch,
        legacy,
        disable_latest=True,
    )
    save_called = False
    monkeypatch.setattr(legacy, "_auth_user", lambda _authorization: {"id": 7})
    monkeypatch.setattr(legacy, "load_plan", lambda **_kwargs: {})

    def _save(_payload, **_kwargs):
        nonlocal save_called
        save_called = True
        return "should-not-save.json"

    monkeypatch.setattr(legacy, "save_plan", _save)
    request = legacy.PlanRequest(
        outline=["第一章"],
        approved_project_fact_resolutions={"resource_peak": resolution},
    )

    with pytest.raises(HTTPException) as exc_info:
        await legacy.save_plan_api(
            request,
            project_id=_APPROVAL_PROJECT_ID,
            authorization="Bearer opaque",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["reason"] == (
        "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT"
    )
    assert save_called is False
    assert not approval_path.exists()


@pytest.mark.asyncio
async def test_changed_current_source_bytes_block_explicit_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    resolution, approval_path = _approval_ingest_fixture(
        tmp_path,
        monkeypatch,
        actions_bridge,
    )
    ingest_path = actions_bridge._PROJECT_FACT_INGEST_AUDIT_PATH
    ingest_row = json.loads(ingest_path.read_text(encoding="utf-8").splitlines()[0])
    Path(ingest_row["saved_as"]).write_bytes(b"changed-after-ingest")
    save_called = False
    monkeypatch.setattr(actions_bridge, "_auth_actions_key", lambda _key: None)
    monkeypatch.setattr(actions_bridge, "load_plan", lambda **_kwargs: {})

    def _save(_payload, **_kwargs):
        nonlocal save_called
        save_called = True
        return "should-not-save.json"

    monkeypatch.setattr(actions_bridge, "save_plan", _save)
    request = actions_bridge.ActionsPlanRequest(
        outline=["第一章"],
        approved_project_fact_resolutions={"resource_peak": resolution},
    )

    with pytest.raises(HTTPException) as exc_info:
        await actions_bridge.actions_plan_save(
            request,
            project_id=_APPROVAL_PROJECT_ID,
            x_actions_key="opaque",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["reason"] == (
        "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT"
    )
    assert save_called is False
    assert not approval_path.exists()


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
