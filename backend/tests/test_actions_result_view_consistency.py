from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.app.routers.actions_bridge import (
    ActionsReviewApplyRequest,
    actions_download,
    actions_job_status,
    actions_jobs_recent,
    actions_result,
    actions_review_apply,
)
from backend.zhifei_autoplan import job_store
from backend.zhifei_autoplan.run_contract import build_result_bundle, load_result_bundle


def _result_view_contract_fields(payload: dict) -> dict:
    return {
        "result_bundle_json": payload.get("result_bundle_json"),
        "result_bundle_available": payload.get("result_bundle_available"),
        "result_bundle_loaded": payload.get("result_bundle_loaded"),
        "result_bundle_complete": payload.get("result_bundle_complete"),
        "result_bundle_schema_version": payload.get("result_bundle_schema_version"),
        "download_ready_count": payload.get("download_ready_count"),
        "download_ready_kinds": payload.get("download_ready_kinds"),
        "primary_download_kind": payload.get("primary_download_kind"),
        "has_blocking_issues": payload.get("has_blocking_issues"),
        "blocking_issue_count": payload.get("blocking_issue_count"),
        "failed_gate_metric_count": payload.get("failed_gate_metric_count"),
        "top_blocking_issue_type": payload.get("top_blocking_issue_type"),
        "has_reference_risks": payload.get("has_reference_risks"),
        "reference_risk_count": payload.get("reference_risk_count"),
        "case_copy_risk_count": payload.get("case_copy_risk_count"),
        "affected_case_ids": payload.get("affected_case_ids"),
        "top_reference_risk_type": payload.get("top_reference_risk_type"),
        "case_library_enabled": payload.get("case_library_enabled"),
        "case_library_selected_ids": payload.get("case_library_selected_ids"),
        "image_library_enabled": payload.get("image_library_enabled"),
        "image_library_selected_ids": payload.get("image_library_selected_ids"),
        "review_apply_variant": payload.get("review_apply_variant"),
        "review_apply_applied_count": payload.get("review_apply_applied_count"),
        "review_apply_reference_case_ids": payload.get("review_apply_reference_case_ids"),
        "review_apply_has_reference_case": payload.get("review_apply_has_reference_case"),
        "review_apply_issue_types": payload.get("review_apply_issue_types"),
        "review_apply_history_count": payload.get("review_apply_history_count"),
        "review_apply_last_applied_at": payload.get("review_apply_last_applied_at"),
    }


def _status_view_contract_fields(response: dict) -> dict:
    return _result_view_contract_fields(response["job"])


def _recent_view_contract_fields(response: dict) -> dict:
    return _result_view_contract_fields(response["items"][0])


def _variant_payload(
    *,
    topic: str,
    generation_mode: str = "stable_delivery",
    logic_template_id: str = "A",
    logic_template_name: str = "交付清单驱动",
) -> dict:
    return {
        "variant_id": 1,
        "topic": topic,
        "outline": ["工程概况"],
        "boq_focus": {"focus_items": []},
        "quality_checks": {},
        "logic_template_id": logic_template_id,
        "logic_template_name": logic_template_name,
        "generation_mode": generation_mode,
        "mode_policy": {
            "profile": generation_mode,
            "mode_effective": generation_mode,
            "stable_output": True,
            "deterministic_variant_forced": True,
            "deterministic_logic_template_id": logic_template_id,
        },
        "generation_trace": {
            "generation_mode": generation_mode,
            "mode_effective": generation_mode,
            "stable_output": True,
            "deterministic_variant_forced": True,
            "deterministic_logic_template_id": logic_template_id,
        },
        "sections": [
            {
                "title": "工程概况",
                "content": "正文内容",
            }
        ],
    }


def _blocking_summary(*, failed_gate_metric_count: int = 1) -> dict:
    failed_metrics = ["engineering_ok_rate"] if failed_gate_metric_count else []
    return {
        "has_blocking_issues": True,
        "blocking_issue_count": 1,
        "failed_gate_metric_count": failed_gate_metric_count,
        "failed_gate_metrics": failed_metrics,
        "top_blocking_issues": [
            {
                "title": "施工部署",
                "type": "engineering_gap",
                "severity": "high",
                "problem": "缺少责任人与验收记录",
                "suggestion": "补齐责任/频次/记录",
            }
        ],
    }


@pytest.mark.asyncio
async def test_actions_result_views_share_contract_semantics_for_complete_bundle(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="views-complete"))
        docx_path = tmp_path / "views-complete.docx"
        docx_path.write_bytes(b"docx")
        result_json = tmp_path / "views-complete.json"
        result_json.write_text(
            json.dumps({"variants": [_variant_payload(topic="三视图完整 bundle")]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        bundle_path = tmp_path / "views-complete-bundle.json"
        bundle_path.write_text(
            json.dumps(
                build_result_bundle(
                    job_id="job-views-complete",
                    payload={
                        "topic": "三视图完整 bundle",
                        "project_id": "views-complete-case",
                        "session_id": "views-complete",
                    },
                    outputs={"json": str(result_json), "docx": [str(docx_path)]},
                    result_metadata={"quality_by_variant": {}},
                    resource_usage_summary={"call_count": 1},
                    variant_summary={"variant_count": 1},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "三视图完整 bundle",
                "project_id": "views-complete-case",
                "workspace_dir": workspace_dir,
                "generation_mode": "stable_delivery",
                "request_id": "req-views-complete",
                "trace_id": "trace-views-complete",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={
                "json": str(result_json),
                "docx": [str(docx_path)],
                "result_bundle_json": str(bundle_path),
                "generation_mode_summary": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
                "quality_by_variant": {
                    "1": {
                        "variant_index": 1,
                        "variant_id": 1,
                        "logic_template_id": "A",
                        "logic_template_name": "交付清单驱动",
                        "quality_score": 96,
                        "quality_gate_ok": False,
                        "quality_gate_failed_count": 1,
                        "blocking_issue_summary": _blocking_summary(),
                    }
                },
                "blocking_issue_summary": _blocking_summary(),
                "blocking_issue_summary_by_variant": {"1": _blocking_summary()},
                "reference_quality_summary": {
                    "has_reference_risks": True,
                    "reference_risk_count": 1,
                    "case_copy_risk_count": 1,
                    "affected_case_ids": ["case-1"],
                    "top_reference_risks": [
                        {
                            "title": "施工部署",
                            "type": "case_reference_copy_risk",
                            "severity": "high",
                        }
                    ],
                },
                "reference_quality_summary_by_variant": {
                    "1": {
                        "has_reference_risks": True,
                        "reference_risk_count": 1,
                        "case_copy_risk_count": 1,
                        "affected_case_ids": ["case-1"],
                        "top_reference_risks": [
                            {
                                "title": "施工部署",
                                "type": "case_reference_copy_risk",
                                "severity": "high",
                            }
                        ],
                    }
                },
                "reference_enhancements": {
                    "case_library": {
                        "enabled": True,
                        "selected_case_ids": ["case-1"],
                        "matched_project_type": "房建",
                        "matched_chapters": ["工程概况"],
                        "match_reasons": ["selected_case_ids"],
                        "hit_count": 1,
                        "warning_list": [],
                        "variant_ids": ["1"],
                    },
                    "image_library": {
                        "enabled": True,
                        "selected_image_ids": ["image-1"],
                        "matched_project_type": "房建",
                        "matched_chapters": ["工程概况"],
                        "match_reasons": ["selected_image_ids"],
                        "hit_count": 1,
                        "warning_list": [],
                        "variant_ids": ["1"],
                    },
                },
                "latest_review_apply_summary": {
                    "variant": 1,
                    "applied_count": 2,
                    "template_applied_count": 2,
                    "replacement_count": 0,
                    "reference_case_ids": ["case-1"],
                    "has_reference_case": True,
                    "issue_types": ["case_reference_copy_risk"],
                },
                "review_apply_history": [
                    {
                        "variant": 1,
                        "applied_count": 1,
                        "template_applied_count": 1,
                        "replacement_count": 0,
                        "reference_case_ids": [],
                        "has_reference_case": False,
                        "issue_types": ["engineering_gap"],
                        "titles": ["工程概况"],
                        "applied_at": "2026-04-12T00:00:00Z",
                    },
                    {
                        "variant": 1,
                        "applied_count": 2,
                        "template_applied_count": 2,
                        "replacement_count": 0,
                        "reference_case_ids": ["case-1"],
                        "has_reference_case": True,
                        "issue_types": ["case_reference_copy_risk"],
                        "titles": ["施工部署"],
                        "applied_at": "2026-04-12T00:00:30Z",
                    },
                ],
            },
        )

        result_view = await actions_result(
            job_id=job_id,
            variant=1,
            session_id="views-complete",
            x_actions_key="test-actions-key",
        )
        status_view = await actions_job_status(
            job_id=job_id,
            session_id="views-complete",
            x_actions_key="test-actions-key",
        )
        recent_view = await actions_jobs_recent(
            limit=8,
            statuses="done",
            max_age_hours=24,
            session_id="views-complete",
            x_actions_key="test-actions-key",
        )

    assert result_view["ok"] is True
    assert status_view["ok"] is True
    assert recent_view["ok"] is True
    assert status_view["job"]["job_id"] == job_id
    assert status_view["job"]["status"] == "done"
    assert recent_view["items"][0]["job_id"] == job_id
    assert recent_view["items"][0]["status"] == "done"

    shared = _result_view_contract_fields(result_view)
    assert shared == _status_view_contract_fields(status_view)
    assert shared == _recent_view_contract_fields(recent_view)
    assert shared["result_bundle_complete"] is True
    assert shared["download_ready_kinds"] == ["docx", "json", "result_bundle_json"]
    assert shared["has_reference_risks"] is True
    assert shared["case_copy_risk_count"] == 1
    assert shared["top_reference_risk_type"] == "case_reference_copy_risk"
    assert shared["case_library_enabled"] is True
    assert shared["case_library_selected_ids"] == ["case-1"]
    assert shared["image_library_enabled"] is True
    assert shared["image_library_selected_ids"] == ["image-1"]
    assert shared["review_apply_applied_count"] == 2
    assert shared["review_apply_reference_case_ids"] == ["case-1"]
    assert shared["review_apply_history_count"] == 2
    assert shared["review_apply_last_applied_at"] == "2026-04-12T00:00:30Z"
    assert result_view["result_bundle_summary"]["path"] == str(bundle_path)
    assert status_view["job"]["result_bundle_summary"]["path"] == str(bundle_path)
    assert result_view["result_bundle_request"]["project_id"] == "views-complete-case"
    assert status_view["job"]["result_bundle_request"]["project_id"] == "views-complete-case"
    assert result_view["download_index"]["docx"]["exists"] is True
    assert status_view["job"]["download_index"]["docx"]["exists"] is True


@pytest.mark.asyncio
async def test_actions_result_views_share_contract_semantics_for_incomplete_bundle(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="views-incomplete"))
        missing_docx = tmp_path / "views-incomplete.docx"
        result_json = tmp_path / "views-incomplete.json"
        result_json.write_text(
            json.dumps({"variants": [_variant_payload(topic="三视图不完整 bundle")]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        bundle_path = tmp_path / "views-incomplete-bundle.json"
        bundle_path.write_text(
            json.dumps(
                build_result_bundle(
                    job_id="job-views-incomplete",
                    payload={
                        "topic": "三视图不完整 bundle",
                        "project_id": "views-incomplete-case",
                        "session_id": "views-incomplete",
                    },
                    outputs={"json": str(result_json), "docx": [str(missing_docx)]},
                    result_metadata={"quality_by_variant": {}},
                    resource_usage_summary={"call_count": 0},
                    variant_summary={"variant_count": 1},
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "三视图不完整 bundle",
                "project_id": "views-incomplete-case",
                "workspace_dir": workspace_dir,
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={
                "json": str(result_json),
                "docx": [str(missing_docx)],
                "result_bundle_json": str(bundle_path),
                "blocking_issue_summary": {
                    "has_blocking_issues": False,
                    "blocking_issue_count": 0,
                    "failed_gate_metric_count": 0,
                    "failed_gate_metrics": [],
                    "top_blocking_issues": [],
                },
                "blocking_issue_summary_by_variant": {
                    "1": {
                        "has_blocking_issues": False,
                        "blocking_issue_count": 0,
                        "failed_gate_metric_count": 0,
                        "failed_gate_metrics": [],
                        "top_blocking_issues": [],
                    }
                },
                "reference_quality_summary": {
                    "has_reference_risks": False,
                    "reference_risk_count": 0,
                    "case_copy_risk_count": 0,
                    "affected_case_ids": [],
                    "top_reference_risks": [],
                },
                "reference_enhancements": {
                    "case_library": {
                        "enabled": False,
                        "selected_case_ids": [],
                        "matched_project_type": None,
                        "matched_chapters": [],
                        "match_reasons": [],
                        "hit_count": 0,
                        "warning_list": ["no_case_match"],
                        "variant_ids": [],
                    },
                    "image_library": {
                        "enabled": False,
                        "selected_image_ids": [],
                        "matched_project_type": None,
                        "matched_chapters": [],
                        "match_reasons": [],
                        "hit_count": 0,
                        "warning_list": ["no_image_match"],
                        "variant_ids": [],
                    },
                },
                "reference_quality_summary_by_variant": {
                    "1": {
                        "has_reference_risks": False,
                        "reference_risk_count": 0,
                        "case_copy_risk_count": 0,
                        "affected_case_ids": [],
                        "top_reference_risks": [],
                    }
                },
                "latest_review_apply_summary": {
                    "variant": 1,
                    "applied_count": 0,
                    "template_applied_count": 0,
                    "replacement_count": 0,
                    "reference_case_ids": [],
                    "has_reference_case": False,
                    "issue_types": [],
                },
                "review_apply_history": [],
            },
        )

        result_view = await actions_result(
            job_id=job_id,
            variant=1,
            session_id="views-incomplete",
            x_actions_key="test-actions-key",
        )
        status_view = await actions_job_status(
            job_id=job_id,
            session_id="views-incomplete",
            x_actions_key="test-actions-key",
        )
        recent_view = await actions_jobs_recent(
            limit=8,
            statuses="done",
            max_age_hours=24,
            session_id="views-incomplete",
            x_actions_key="test-actions-key",
        )

    shared = _result_view_contract_fields(result_view)
    assert shared == _status_view_contract_fields(status_view)
    assert shared == _recent_view_contract_fields(recent_view)
    assert shared["result_bundle_available"] is True
    assert shared["result_bundle_loaded"] is True
    assert shared["result_bundle_complete"] is False
    assert shared["download_ready_kinds"] == ["json", "result_bundle_json"]
    assert shared["download_ready_count"] == 2
    assert shared["has_blocking_issues"] is False
    assert shared["has_reference_risks"] is False
    assert shared["case_copy_risk_count"] == 0
    assert shared["case_library_enabled"] is False
    assert shared["image_library_enabled"] is False
    assert shared["review_apply_applied_count"] == 0
    assert shared["review_apply_history_count"] == 0
    assert result_view["download_index"]["docx"]["exists"] is False
    assert status_view["job"]["download_index"]["docx"]["exists"] is False


@pytest.mark.asyncio
async def test_actions_review_apply_updates_all_result_views_consistently(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="views-review"))
        source_json = tmp_path / "views-review-source.json"
        source_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "topic": "三视图复核一致性",
                            "generation_mode": "stable_delivery",
                            "generation_trace": {
                                "generation_mode": "stable_delivery",
                                "mode_effective": "stable_delivery",
                                "stable_output": True,
                                "deterministic_variant_forced": True,
                                "deterministic_logic_template_id": "A",
                            },
                            "logic_template_id": "A",
                            "logic_template_name": "交付清单驱动",
                            "sections": [{"title": "施工部署", "content": "原始内容"}],
                            "quality_checks": {
                                "score": 96,
                                "issue_list": [
                                    {
                                        "title": "施工部署",
                                        "type": "engineering_gap",
                                        "severity": "high",
                                        "problem": "缺少责任人与验收记录",
                                        "suggestion": "补齐责任/频次/记录",
                                    }
                                ],
                            },
                            "quality_gate": {
                                "ok": False,
                                "failed": [{"metric": "engineering_ok_rate"}],
                            },
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "三视图复核一致性",
                "workspace_dir": workspace_dir,
                "request_id": "req-views-review",
                "trace_id": "trace-views-review",
                "generation_mode": "stable_delivery",
                "logic_template_id": "A",
                "_mode_policy": {
                    "profile": "stable_delivery",
                    "mode_effective": "stable_delivery",
                    "stable_output": True,
                    "deterministic_variant_forced": True,
                    "deterministic_logic_template_id": "A",
                },
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(source_json)},
        )

        def _fake_save_outputs(base_name: str, results: list[dict], *, workspace_dir: str | None = None):
            out_json = tmp_path / f"{base_name}.json"
            out_docx = tmp_path / f"{base_name}.docx"
            out_json.write_text(json.dumps({"variants": results}, ensure_ascii=False, indent=2), encoding="utf-8")
            out_docx.write_bytes(b"docx")
            return {"json": str(out_json), "docx": [str(out_docx)]}

        with patch("backend.app.routers.actions_bridge._save_outputs", side_effect=_fake_save_outputs), patch(
            "backend.app.routers.actions_bridge._rebuild_postprocessed_artifacts",
            return_value=None,
        ), patch("backend.app.routers.actions_bridge.apply_remediation", return_value=None):
            review_response = await actions_review_apply(
                ActionsReviewApplyRequest(job_id=job_id, variant=1, apply_all=True),
                session_id="views-review",
                x_actions_key="test-actions-key",
            )

        result_view = await actions_result(
            job_id=job_id,
            variant=1,
            session_id="views-review",
            x_actions_key="test-actions-key",
        )
        status_view = await actions_job_status(
            job_id=job_id,
            session_id="views-review",
            x_actions_key="test-actions-key",
        )
        recent_view = await actions_jobs_recent(
            limit=8,
            statuses="done",
            max_age_hours=24,
            session_id="views-review",
            x_actions_key="test-actions-key",
        )
        stored = job_store.get_job(job_id, workspace_dir=workspace_dir)

    shared = _result_view_contract_fields(result_view)
    assert shared == _status_view_contract_fields(status_view)
    assert shared == _recent_view_contract_fields(recent_view)
    assert shared == _result_view_contract_fields(review_response)
    assert shared["result_bundle_complete"] is True
    assert shared["download_ready_kinds"] == ["docx", "json", "result_bundle_json"]
    assert shared["blocking_issue_count"] == 1
    assert shared["has_reference_risks"] is False
    assert shared["review_apply_applied_count"] == 1
    assert shared["review_apply_issue_types"] == ["engineering_gap"]
    assert review_response["files"]["result_bundle_json"] == shared["result_bundle_json"]
    assert stored["result"]["result_bundle_json"] == shared["result_bundle_json"]
    bundle = load_result_bundle(shared["result_bundle_json"])
    assert bundle is not None
    assert bundle["result_metadata"]["blocking_issue_summary"]["blocking_issue_count"] == 1
    assert status_view["job"]["status"] == "done"
    assert recent_view["items"][0]["status"] == "done"


@pytest.mark.asyncio
async def test_actions_download_invalid_kind_semantics_remain_stable(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="views-invalid-kind"))
        result_json = tmp_path / "views-invalid-kind.json"
        result_json.write_text(json.dumps({"variants": []}, ensure_ascii=False), encoding="utf-8")
        job_id = job_store.create_job(
            {
                "topic": "非法下载类型稳定性",
                "workspace_dir": workspace_dir,
                "request_id": "req-views-invalid-kind",
                "trace_id": "trace-views-invalid-kind",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(result_json)},
        )

        with pytest.raises(HTTPException) as exc:
            await actions_download(
                job_id=job_id,
                kind="pdf",
                variant=1,
                session_id="views-invalid-kind",
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 400
    detail = exc.value.detail
    assert detail["code"] == "invalid_artifact_kind"
    assert detail["request_id"] == "req-views-invalid-kind"
    assert detail["trace_id"] == "trace-views-invalid-kind"
    assert "result_bundle_json" in detail["extra"]["allowed_kinds"]
