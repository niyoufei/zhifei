from __future__ import annotations

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.routers.actions_bridge import (
    ActionsGenerateRequest,
    ActionsReviewApplyRequest,
    _apply_generation_mode_policy,
    _build_variant_plan,
    _chief_agent_status_summary,
    _recent_job_agent_runtime_summary,
    _recent_job_sla_summary,
    _recent_job_remediation_execution_summary,
    _recent_job_remediation_learning_summary,
    _recent_job_remediation_strategy_summary,
    _recent_job_runtime_budget_summary,
    _review_items_for_variant,
    actions_review_issues,
    actions_review_apply,
    actions_result,
    actions_generate_async,
    _watcher_status_summary,
)
from backend.zhifei_autoplan import job_store
from backend.zhifei_autoplan.job_worker import _payload_stage_summary
from backend.zhifei_autoplan.run_contract import load_result_bundle


def _fmt_ts(offset_seconds: int = 0) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + int(offset_seconds)))


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


def test_review_items_keep_reference_case_context():
    variant = {
        "sections": [
            {
                "title": "施工部署",
                "content": "内容A",
                "case_reference_pack": {
                    "match_reason": "selected_case_ids",
                    "non_fact_reference_notice": "案例仅用于结构与表达参考",
                    "hits": [
                        {
                            "case_id": "case-1",
                            "title": "养老院改造样板",
                        }
                    ],
                },
            },
        ],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "施工部署",
                    "type": "case_reference_copy_risk",
                    "severity": "high",
                    "problem": "与案例相似度过高",
                    "suggestion": "重写本章",
                    "reference_case_id": "case-1",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    rows = _review_items_for_variant(variant)
    assert len(rows) == 1
    assert rows[0]["reference_case_id"] == "case-1"
    assert rows[0]["reference_context"] == {
        "reference_case_id": "case-1",
        "reference_case_title": "养老院改造样板",
        "match_reason": "selected_case_ids",
        "non_fact_reference_notice": "案例仅用于结构与表达参考",
    }


@pytest.mark.asyncio
async def test_actions_review_issues_falls_back_to_first_variant_when_requested_out_of_range(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="review-issues-variants"))
        source_json = tmp_path / "review-issues-variants.json"
        source_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "sections": [{"title": "施工部署", "content": "第一版"}],
                            "quality_checks": {
                                "issue_list": [
                                    {
                                        "title": "施工部署",
                                        "type": "engineering_gap",
                                        "severity": "high",
                                        "problem": "缺少责任",
                                        "suggestion": "补齐责任",
                                    }
                                ]
                            },
                        },
                        {
                            "variant_id": 2,
                            "sections": [{"title": "安全措施", "content": "第二版"}],
                            "quality_checks": {
                                "issue_list": [
                                    {
                                        "title": "安全措施",
                                        "type": "risk_triplet_gap",
                                        "severity": "medium",
                                        "problem": "缺少验证",
                                        "suggestion": "补齐验证",
                                    }
                                ]
                            },
                        },
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        job_id = job_store.create_job(
            {
                "topic": "review-issues-variants",
                "workspace_dir": workspace_dir,
                "request_id": "req-review-issues-variants",
                "trace_id": "trace-review-issues-variants",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(source_json)},
        )

        response = await actions_review_issues(
            job_id=job_id,
            variant=9,
            session_id="review-issues-variants",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    assert response["job_id"] == job_id
    assert response["variant"] == 1
    assert response["count"] == 1
    assert response["items"][0]["title"] == "施工部署"
    assert response["items"][0]["issue_id"].startswith("I")


@pytest.mark.asyncio
async def test_actions_review_issues_keeps_reference_case_context(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="review-issues-reference"))
        source_json = tmp_path / "review-issues-reference.json"
        source_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "sections": [
                                {
                                    "title": "施工部署",
                                    "content": "第一版",
                                    "case_reference_pack": {
                                        "match_reason": "selected_case_ids",
                                        "non_fact_reference_notice": "案例仅用于结构与表达参考",
                                        "hits": [
                                            {
                                                "case_id": "case-1",
                                                "title": "养老院改造样板",
                                            }
                                        ],
                                    },
                                }
                            ],
                            "quality_checks": {
                                "issue_list": [
                                    {
                                        "title": "施工部署",
                                        "type": "case_reference_copy_risk",
                                        "severity": "high",
                                        "problem": "与案例相似度过高",
                                        "suggestion": "重写本章",
                                        "reference_case_id": "case-1",
                                    }
                                ]
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
                "topic": "review-issues-reference",
                "workspace_dir": workspace_dir,
                "request_id": "req-review-issues-reference",
                "trace_id": "trace-review-issues-reference",
            },
            workspace_dir=workspace_dir,
        )
        job_store.update_job(
            job_id,
            workspace_dir=workspace_dir,
            status="done",
            result={"json": str(source_json)},
        )

        response = await actions_review_issues(
            job_id=job_id,
            variant=1,
            session_id="review-issues-reference",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    assert response["count"] == 1
    assert response["items"][0]["type"] == "case_reference_copy_risk"
    assert response["items"][0]["reference_case_id"] == "case-1"
    assert response["items"][0]["reference_context"] == {
        "reference_case_id": "case-1",
        "reference_case_title": "养老院改造样板",
        "match_reason": "selected_case_ids",
        "non_fact_reference_notice": "案例仅用于结构与表达参考",
    }


@pytest.mark.asyncio
async def test_actions_review_apply_refreshes_result_bundle_and_blocking_summary(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="review-apply-bundle"))
        source_json = tmp_path / "review-source.json"
        source_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "topic": "复核回写测试",
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
                            "sections": [
                                {"title": "施工部署", "content": "原始内容"}
                            ],
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
                "topic": "复核回写测试",
                "workspace_dir": workspace_dir,
                "request_id": "req-review-apply-bundle",
                "trace_id": "trace-review-apply-bundle",
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

        with patch("backend.app.routers.actions_bridge._save_outputs", side_effect=_fake_save_outputs), \
             patch("backend.app.routers.actions_bridge._rebuild_postprocessed_artifacts", return_value=None), \
             patch("backend.app.routers.actions_bridge.apply_remediation", return_value=None):
            response = await actions_review_apply(
                ActionsReviewApplyRequest(job_id=job_id, variant=1, apply_all=True),
                session_id="review-apply-bundle",
                x_actions_key="test-actions-key",
            )

        stored = job_store.get_job(job_id, workspace_dir=workspace_dir)
        result_view = await actions_result(
            job_id=job_id,
            variant=1,
            session_id="review-apply-bundle",
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    assert Path(response["files"]["result_bundle_json"]).exists()
    assert response["result_bundle_json"] == response["files"]["result_bundle_json"]
    assert response["result_bundle_summary"]["complete"] is True
    assert response["result_bundle_request"]["project_id"] is None
    assert response["result_bundle_artifact_count"] == 2
    assert response["result_bundle_artifacts"][0]["kind"] in {"json", "docx"}
    assert response["download_index"]["docx"]["exists"] is True
    assert response["download_ready_count"] == 3
    assert response["download_ready_kinds"] == ["docx", "json", "result_bundle_json"]
    assert response["primary_download_kind"] == "docx"
    assert response["has_blocking_issues"] is True
    assert response["blocking_issue_count"] == 1
    assert response["applied_items_summary"][0]["title"] == "施工部署"
    assert response["applied_items_summary"][0]["apply_mode"] == "remediation"
    assert response["applied_reference_case_ids"] == []
    assert response["latest_review_apply_summary"]["applied_count"] == 1
    assert response["latest_review_apply_summary"]["issue_types"] == ["engineering_gap"]
    assert response["review_apply_history_count"] == 1
    assert response["review_apply_history"][-1]["applied_count"] == 1
    assert response["review_apply_last_applied_at"]
    assert stored["result"]["result_bundle_json"] == response["files"]["result_bundle_json"]
    assert stored["result"]["blocking_issue_summary"]["has_blocking_issues"] is True
    assert stored["result"]["blocking_issue_summary"]["failed_gate_metric_count"] == 1
    assert stored["result"]["latest_review_apply_summary"]["applied_count"] == 1
    assert stored["result"]["review_apply_history"][-1]["applied_count"] == 1
    bundle = load_result_bundle(stored["result"]["result_bundle_json"])
    assert bundle is not None
    assert bundle["result_metadata"]["blocking_issue_summary"]["blocking_issue_count"] == 1
    assert bundle["result_metadata"]["latest_review_apply_summary"]["applied_count"] == 1
    assert bundle["result_metadata"]["review_apply_history"][-1]["applied_count"] == 1
    assert bundle["result_metadata"]["generation_mode_summary"]["profile"] == "stable_delivery"
    assert result_view["result_bundle_summary"]["path"] == stored["result"]["result_bundle_json"]
    assert result_view["result_bundle_artifact_count"] == 2
    assert result_view["download_index"]["result_bundle_json"]["exists"] is True
    assert result_view["blocking_issue_count"] == 1
    assert result_view["review_apply_history_count"] == 1


@pytest.mark.asyncio
async def test_actions_review_apply_returns_reference_risk_applied_summary(tmp_path):
    from backend.zhifei_autoplan import workspace as ws

    workspaces = tmp_path / "workspaces"
    audit_events: list[dict] = []
    with patch.object(ws, "WORKSPACE_ROOT", workspaces), patch.dict(
        os.environ,
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ):
        workspace_dir = str(ws.resolve_workspace_dir(session_id="review-apply-reference"))
        source_json = tmp_path / "review-reference-source.json"
        source_json.write_text(
            json.dumps(
                {
                    "variants": [
                        {
                            "variant_id": 1,
                            "topic": "复核引用风险回执",
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
                            "sections": [
                                {
                                    "title": "施工部署",
                                    "content": "原始内容",
                                    "case_reference_pack": {
                                        "match_reason": "selected_case_ids",
                                        "non_fact_reference_notice": "案例仅用于结构与表达参考",
                                        "hits": [
                                            {
                                                "case_id": "case-1",
                                                "title": "养老院改造样板",
                                            }
                                        ],
                                    },
                                }
                            ],
                            "quality_checks": {
                                "score": 96,
                                "issue_list": [
                                    {
                                        "title": "施工部署",
                                        "type": "case_reference_copy_risk",
                                        "severity": "high",
                                        "problem": "与案例相似度过高",
                                        "suggestion": "重写本章",
                                        "reference_case_id": "case-1",
                                    }
                                ],
                            },
                            "quality_gate": {
                                "ok": True,
                                "failed": [],
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
                "topic": "review-apply-reference",
                "workspace_dir": workspace_dir,
                "request_id": "req-review-apply-reference",
                "trace_id": "trace-review-apply-reference",
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
        ), patch("backend.app.routers.actions_bridge.apply_remediation", return_value=None), patch(
            "backend.app.routers.actions_bridge.append_resource_event",
            side_effect=lambda event, **fields: audit_events.append({"event": event, **fields}) or str(tmp_path / "resource.jsonl"),
        ):
            response = await actions_review_apply(
                ActionsReviewApplyRequest(job_id=job_id, variant=1, apply_all=True),
                session_id="review-apply-reference",
                x_actions_key="test-actions-key",
            )

    assert response["ok"] is True
    assert response["applied_count"] == 1
    assert response["applied_reference_case_ids"] == ["case-1"]
    assert response["latest_review_apply_summary"]["reference_case_ids"] == ["case-1"]
    assert response["review_apply_history_count"] == 1
    assert response["review_apply_history"][-1]["reference_case_ids"] == ["case-1"]
    assert response["applied_items_summary"] == [
        {
            "issue_id": "I0001",
            "source": "issue_list",
            "title": "施工部署",
            "type": "case_reference_copy_risk",
            "apply_mode": "remediation",
            "reference_case_id": "case-1",
            "reference_context": {
                "reference_case_id": "case-1",
                "reference_case_title": "养老院改造样板",
                "match_reason": "selected_case_ids",
                "non_fact_reference_notice": "案例仅用于结构与表达参考",
            },
        }
    ]
    assert audit_events[-1]["event"] == "review_apply"
    assert audit_events[-1]["job_id"] == job_id
    assert audit_events[-1]["applied_reference_case_ids"] == ["case-1"]
    assert audit_events[-1]["applied_types"] == ["case_reference_copy_risk"]


def test_recent_job_agent_runtime_summary_keeps_parallelism_fields():
    out = _recent_job_agent_runtime_summary(
        {
            "requested_agent_parallelism": 8,
            "agent_parallelism": 2,
            "variant_parallelism": 1,
            "planned_total_pages": 8,
            "outline_count": 3,
            "runtime_agent_parallelism_reason": "small_job_cap=2",
            "runtime_agent_parallelism_learning_applied": True,
            "runtime_agent_parallelism_learning_reason": "historical_task_fallback_rate=0.50_reduce_parallelism",
            "runtime_agent_parallelism_learning_source_runs": 4,
        }
    )
    assert out["requested_agent_parallelism"] == 8
    assert out["agent_parallelism"] == 2
    assert out["variant_parallelism"] == 1
    assert out["planned_total_pages"] == 8
    assert out["outline_count"] == 3
    assert out["runtime_agent_parallelism_reason"] == "small_job_cap=2"
    assert out["runtime_agent_parallelism_learning_applied"] is True
    assert out["runtime_agent_parallelism_learning_reason"] == "historical_task_fallback_rate=0.50_reduce_parallelism"
    assert out["runtime_agent_parallelism_learning_source_runs"] == 4


def test_recent_job_sla_summary_keeps_total_and_running_stage_elapsed():
    with patch("backend.app.routers.actions_bridge.time.time", return_value=150.0):
        out = _recent_job_sla_summary(
            {
                "total_seconds": 48.3,
                "stages": [
                    {
                        "name": "agent_ready",
                        "started_at": 100.0,
                        "ended_at": 120.0,
                        "duration_sec": 20.0,
                        "detail": "多Agent已就绪",
                    },
                    {
                        "name": "variant_running",
                        "started_at": 130.0,
                        "ended_at": None,
                        "duration_sec": None,
                        "detail": "方案完成进度：1/3",
                    },
                ],
            }
        )
    assert out["total_seconds"] == 48.3
    assert out["current_stage"] == "variant_running"
    assert out["current_stage_detail"] == "方案完成进度：1/3"
    assert out["current_stage_seconds"] == 20.0


def test_recent_job_sla_summary_keeps_terminal_dominant_stage_and_exporting_share():
    out = _recent_job_sla_summary(
        {
            "total_seconds": 80.937,
            "stages": [
                {
                    "name": "variant_running",
                    "started_at": 10.0,
                    "ended_at": 29.161,
                    "duration_sec": 19.161,
                    "detail": "方案完成进度：1/1",
                },
                {
                    "name": "exporting",
                    "started_at": 29.161,
                    "ended_at": 90.875,
                    "duration_sec": 61.714,
                    "detail": "正在导出 DOCX / 对照稿 / 问题清单",
                },
                {
                    "name": "done",
                    "started_at": 90.875,
                    "ended_at": 90.937,
                    "duration_sec": 0.062,
                    "detail": "任务完成",
                },
            ],
        }
    )
    assert out["total_seconds"] == 80.937
    assert out["current_stage"] == "done"
    assert out["dominant_stage"] == "exporting"
    assert out["dominant_stage_seconds"] == 61.714
    assert out["exporting_seconds"] == 61.714
    assert out["dominant_stage_share"] == 76.2
    assert out["exporting_share"] == 76.2
    assert out["variant_running_seconds"] == 19.161
    assert out["variant_running_share"] == 23.7


def test_chief_agent_status_summary_reads_maintenance_fields():
    out = _chief_agent_status_summary(
        {
            "timestamp": _fmt_ts(0),
            "backend_listener": 1,
            "web_listener": 1,
            "backend_health": 1,
            "web_health": 1,
            "last_action": "noop",
            "maintenance": {
                "job_housekeep": {
                    "changed": True,
                    "stale_fixed": 2,
                    "removed": 9,
                    "lease_seconds": 900,
                    "retention_seconds": 1209600,
                },
                "self_evolution": {
                    "enabled": True,
                    "runtime_budget_profile": {"changed": True, "entry_count": 21},
                    "task_parallelism_profile": {"changed": False, "entry_count": 2},
                },
            },
            "recent": [
                {"timestamp": _fmt_ts(-180), "kind": "startup", "summary": "startup"},
                {"timestamp": _fmt_ts(-120), "kind": "job_housekeep", "summary": "job housekeep applied"},
                {"timestamp": _fmt_ts(-60), "kind": "restart_web_ui", "summary": "web unhealthy -> restart"},
            ],
        },
        stale_seconds=300,
    )
    assert out["healthy"] is True
    assert out["job_housekeep"]["stale_fixed"] == 2
    assert out["job_housekeep"]["removed"] == 9
    assert out["self_evolution"]["enabled"] is True
    assert out["self_evolution"]["runtime_changed"] is True
    assert out["self_evolution"]["runtime_entry_count"] == 21
    assert "job housekeep=有变更" in out["summary_line"]
    assert "web unhealthy -> restart" in out["recent_summary_line"]
    assert out["recent"][0]["kind"] == "restart_web_ui"
    assert out["recent"][-1]["kind"] == "startup"


def test_chief_agent_status_summary_hides_stale_recent_noise_when_healthy():
    out = _chief_agent_status_summary(
        {
            "timestamp": _fmt_ts(0),
            "backend_listener": 1,
            "web_listener": 1,
            "backend_health": 1,
            "web_health": 1,
            "last_action": "noop",
            "recent": [
                {"timestamp": _fmt_ts(-7200), "kind": "restart_web_ui", "summary": "web unhealthy -> restart"},
                {"timestamp": _fmt_ts(-7100), "kind": "startup", "summary": "startup"},
            ],
        },
        stale_seconds=300,
    )
    assert out["healthy"] is True
    assert out["recent_summary_line"] == "最近无异常动作"
    assert out["recent"][0]["kind"] == "restart_web_ui"


def test_watcher_status_summary_reads_queue_and_project_fields():
    out = _watcher_status_summary(
        {
            "timestamp": _fmt_ts(0),
            "status": "idle",
            "watch_root": "/tmp/projects",
            "last_action": "processed",
            "last_project_id": "p-001",
            "last_project_name": "示例项目",
            "inbox_count": 1,
            "work_count": 2,
            "done_count": 3,
            "failed_count": 4,
            "recent": [
                {"timestamp": _fmt_ts(-180), "kind": "startup", "summary": "startup"},
                {"timestamp": _fmt_ts(-120), "kind": "processed", "summary": "processed project=示例项目"},
                {"timestamp": _fmt_ts(-60), "kind": "error", "summary": "error project=示例项目"},
            ],
        },
        stale_seconds=300,
    )
    assert out["healthy"] is True
    assert out["status"] == "idle"
    assert out["watch_root"] == "/tmp/projects"
    assert out["last_project_id"] == "p-001"
    assert out["last_project_name"] == "示例项目"
    assert out["inbox_count"] == 1
    assert out["work_count"] == 2
    assert out["done_count"] == 3
    assert out["failed_count"] == 4
    assert "watcher=正常" in out["summary_line"]
    assert "error project=示例项目" in out["recent_summary_line"]
    assert out["recent"][0]["kind"] == "error"
    assert out["recent"][-1]["kind"] == "startup"


def test_watcher_status_summary_hides_stale_processed_noise_when_idle():
    out = _watcher_status_summary(
        {
            "timestamp": _fmt_ts(0),
            "status": "idle",
            "watch_root": "/tmp/projects",
            "last_action": "poll",
            "recent": [
                {"timestamp": _fmt_ts(-7200), "kind": "processed", "summary": "processed project=示例项目"},
                {"timestamp": _fmt_ts(-7100), "kind": "processing", "summary": "processing project=示例项目"},
            ],
        },
        stale_seconds=300,
    )
    assert out["healthy"] is True
    assert out["recent_summary_line"] == "最近无项目动作"
    assert {item["kind"] for item in out["recent"]} == {"processed", "processing"}


def test_recent_job_runtime_budget_summary_reads_first_variant_sections(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "sections": [
                            {
                                "title": "工程概况",
                                "requested_timeout_sec": 77,
                                "requested_max_output_tokens": 2600,
                                "requested_section_retry_limit": 1,
                                "runtime_budget_reason": "low_complexity_small_section",
                                "evolution_applied": True,
                                "evolution_reason": "historical_quality_issue_rate=0.67_raise_tokens",
                                "evolution_source_runs": 3,
                                "used_key_alias": "OPENAI_API_KEY_TEXT_MAIN",
                            }
                        ]
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = _recent_job_runtime_budget_summary({"json": str(p)})
    assert len(out) == 1
    assert out[0]["title"] == "工程概况"
    assert out[0]["requested_timeout_sec"] == 77
    assert out[0]["requested_section_retry_limit"] == 1
    assert out[0]["runtime_budget_reason"] == "low_complexity_small_section"
    assert out[0]["evolution_applied"] is True
    assert out[0]["evolution_source_runs"] == 3


async def test_actions_generate_async_reuses_same_payload_with_new_trace_ids(tmp_path):
    workspace_root = tmp_path / "workspaces"
    worker_log = tmp_path / "worker.log"
    audit_events: list[dict] = []
    req = ActionsGenerateRequest(
        topic="复用验证-施工组织设计",
        project_id="reuse_check",
        outline=["工程概况", "主要施工方法"],
        generation_mode="quality_200",
        dry_run=True,
        generate_images=False,
        strict_tender_outline=True,
    )

    def fake_append_resource_event(event: str, **fields):
        audit_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    with patch("backend.zhifei_autoplan.workspace.WORKSPACE_ROOT", workspace_root), \
         patch("backend.app.routers.actions_bridge._spawn_generate_worker", return_value=(99999, str(worker_log))), \
         patch("backend.app.routers.actions_bridge._run_background_housekeeping", return_value=None), \
         patch("backend.app.routers.actions_bridge.append_resource_event", side_effect=fake_append_resource_event), \
         patch("backend.app.routers.actions_bridge.apply_server_provider_routing", side_effect=lambda payload: payload), \
         patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        first = await actions_generate_async(req, x_actions_key="test-actions-key")
        second = await actions_generate_async(req, x_actions_key="test-actions-key")

    assert first["status"] == "queued"
    assert second["status"] == "queued"
    assert second["reused"] is True
    assert second["reuse_reason"] == "same_payload"
    assert first["job_id"] == second["job_id"]
    assert first["admission"]["scope"] == "session"
    assert first["admission"]["requested_jobs"] == 1
    assert second["admission"]["scope"] == "session"
    job_dir = Path(first["workspace_dir"]) / "jobs"
    job_files = list(job_dir.glob("*.json"))
    assert len(job_files) == 1
    stored_job = json.loads(job_files[0].read_text(encoding="utf-8"))
    contract = stored_job["payload"].get("_contract_stamp") if isinstance(stored_job.get("payload"), dict) else {}
    assert contract["request_contract_version"] == "actions-generate-contract-v1"
    assert contract["prompt_prefix_version"]
    assert contract["engineering_rules"]["path"]
    assert len(audit_events) == 1
    assert audit_events[0]["event"] == "job_queued"
    assert audit_events[0]["workspace_dir"] == first["workspace_dir"]
    assert audit_events[0]["session_id"] == first["session_id"]
    assert audit_events[0]["job_id"] == first["job_id"]


async def test_actions_generate_async_dry_run_without_provider_keys_queues_job(tmp_path, monkeypatch):
    workspace_root = tmp_path / "workspaces"
    worker_log = tmp_path / "worker.log"
    audit_events: list[dict] = []
    for key in (
        "OPENAI_API_KEY_TEXT_MAIN",
        "ZF_LLM_MAIN_API_KEY",
        "OPENAI_API_KEY",
        "ZF_OPENAI_API_KEY",
        "OPENAI_API_KEY_TEXT_BACKUP",
        "ZF_LLM_FALLBACK1_API_KEY",
        "GEMINI_API_KEY_A",
        "ZF_GOOGLE_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("ZF_ENABLE_GEMINI_TEXT_FALLBACK", raising=False)

    req = ActionsGenerateRequest(
        topic="无密钥 dry-run",
        project_id="dry_run_providerless",
        outline=["工程概况", "主要施工方法"],
        generation_mode="quality_200",
        dry_run=True,
        generate_images=False,
        strict_tender_outline=True,
        provider="openai",
        model="gpt-5.4",
    )

    def fake_append_resource_event(event: str, **fields):
        audit_events.append({"event": event, **fields})
        return str(tmp_path / "resource_usage.jsonl")

    with patch("backend.zhifei_autoplan.workspace.WORKSPACE_ROOT", workspace_root), \
         patch("backend.app.routers.actions_bridge._spawn_generate_worker", return_value=(99999, str(worker_log))), \
         patch("backend.app.routers.actions_bridge._run_background_housekeeping", return_value=None), \
         patch("backend.app.routers.actions_bridge.append_resource_event", side_effect=fake_append_resource_event), \
         patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        out = await actions_generate_async(
            req,
            session_id="dry-run-providerless",
            x_actions_key="test-actions-key",
        )

    assert out["ok"] is True
    assert out["status"] == "queued"
    job_path = Path(out["workspace_dir"]) / "jobs" / f"{out['job_id']}.json"
    assert job_path.exists()
    stored = json.loads(job_path.read_text(encoding="utf-8"))
    assert stored["payload"]["dry_run"] is True
    assert stored["payload"]["provider_chain"] == []
    assert stored["payload"]["provider"] == "openai"
    assert stored["payload"]["model"] == "gpt-5.4"
    assert audit_events[-1]["event"] == "job_queued"


def test_recent_job_remediation_strategy_summary_reads_indicator_groups(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "quality_checks": {
                            "remediation_strategy_audit": {
                                "issue_count": 4,
                                "remediation_count": 4,
                                "indicator_groups": [
                                    {"indicator_group": "缺量化", "count": 2},
                                    {"indicator_group": "缺闭环", "count": 1},
                                    {"indicator_group": "缺证据", "count": 1},
                                ],
                                "strategies": [
                                    {"strategy_id": "quant_fill_general_v1", "count": 2},
                                    {"strategy_id": "risk_triplet_closure_v1", "count": 1},
                                ],
                            }
                        }
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = _recent_job_remediation_strategy_summary({"json": str(p)})
    assert out["issue_count"] == 4
    assert out["remediation_count"] == 4
    assert out["indicator_groups"][0]["indicator_group"] == "缺量化"
    assert out["strategies"][0]["strategy_id"] == "quant_fill_general_v1"


def test_recent_job_remediation_execution_summary_reads_action_tags(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "quality_checks": {
                            "remediation_execution_audit": {
                                "trace_count": 3,
                                "action_tags": [
                                    {"action_tag": "add_quant_value", "label": "补量化数值", "count": 2},
                                    {"action_tag": "add_record_acceptance", "label": "补验收/记录", "count": 1},
                                ],
                                "strategies": [
                                    {"strategy_id": "quant_fill_general_v1", "count": 2},
                                ],
                                "status_counts": [
                                    {"status": "matched", "count": 2},
                                ],
                            }
                        }
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = _recent_job_remediation_execution_summary({"json": str(p)})
    assert out["trace_count"] == 3
    assert out["action_tags"][0]["action_tag"] == "add_quant_value"
    assert out["action_tags"][0]["label"] == "补量化数值"
    assert out["strategies"][0]["strategy_id"] == "quant_fill_general_v1"


def test_recent_job_remediation_learning_summary_reads_generation_trace(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "generation_trace": {
                            "self_evolution": {
                                "remediation_combo_learning_applied_count": 2,
                                "remediation_combo_learning_source_runs": 3,
                                "remediation_combo_learning_titles": ["工程概况"],
                                "remediation_combo_learning_reasons": [
                                    "工程概况: historical_combo_close_rate=0.67; historical_combo_gate_pass_rate=0.33; action=add_quant_value"
                                ],
                                "remediation_combo_learning_combos": [
                                    "缺量化/quant_fill_general_v1/add_quant_value close=67% pass=33% n=3"
                                ],
                                "remediation_combo_bundle_learning_applied_count": 2,
                                "remediation_combo_bundle_learning_source_runs": 3,
                                "remediation_combo_bundle_learning_titles": ["工程概况"],
                                "remediation_combo_bundle_learning_reasons": [
                                    "工程概况: historical_combo_bundle_pass_rate=0.67; bundle_size=2; bundle_match_count=2"
                                ],
                                "remediation_combo_bundle_learning_bundles": [
                                    "缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify pass=67% n=3"
                                ],
                                "remediation_context_bundle_learning_applied_count": 2,
                                "remediation_context_bundle_learning_source_runs": 3,
                                "remediation_context_bundle_learning_titles": ["工程概况"],
                                "remediation_context_bundle_learning_contexts": ["general/A"],
                                "remediation_context_bundle_learning_reasons": [
                                    "工程概况: historical_context_bundle_pass_rate=1.00; context=general/A; bundle_size=2; bundle_match_count=2"
                                ],
                                "remediation_context_bundle_learning_bundles": [
                                    "general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify pass=100% n=3"
                                ],
                                "remediation_context_bundle_learning_effect_applied_count": 1,
                                "remediation_context_bundle_learning_effect_source_runs": 2,
                                "remediation_context_bundle_learning_effect_titles": ["工程概况"],
                                "remediation_context_bundle_learning_effect_reasons": [
                                    "工程概况: historical_learning_applied_gate_pass_rate=1.00; attribution_runs=2"
                                ],
                                "remediation_context_bundle_learning_effect_bundles": [
                                    "general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify attributed_pass=100% n=2"
                                ],
                                "remediation_context_bundle_learning_metric_effect_applied_count": 2,
                                "remediation_context_bundle_learning_metric_effect_source_runs": 3,
                                "remediation_context_bundle_learning_metric_effect_titles": ["工程概况"],
                                "remediation_context_bundle_learning_metric_effect_metrics": ["量化指标达标率", "风险三元组达标率"],
                                "remediation_context_bundle_learning_metric_effect_reasons": [
                                    "工程概况: 量化指标达标率已拉平; quantitative_ok_rate_resolve_rate=1.00"
                                ],
                                "remediation_context_bundle_learning_metric_effect_bundles": [
                                    "general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify pass=100% n=3"
                                ],
                                "remediation_context_bundle_learning_metric_action_effect_applied_count": 2,
                                "remediation_context_bundle_learning_metric_action_effect_source_runs": 3,
                                "remediation_context_bundle_learning_metric_action_effect_titles": ["工程概况"],
                                "remediation_context_bundle_learning_metric_action_effect_triplets": [
                                    "量化指标达标率/补量化数值",
                                    "风险三元组达标率/补风险→控制→验证",
                                ],
                                "remediation_context_bundle_learning_metric_action_effect_reasons": [
                                    "工程概况: 量化指标达标率/补量化数值已拉平; quantitative_ok_rate/add_quant_value_resolve_rate=1.00"
                                ],
                                "remediation_context_bundle_learning_metric_action_effect_bundles": [
                                    "general/A | 缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify pass=100% n=3"
                                ],
                            }
                        }
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = _recent_job_remediation_learning_summary({"json": str(p)})
    assert out["applied_count"] == 2
    assert out["source_runs"] == 3
    assert out["titles"] == ["工程概况"]
    assert "add_quant_value" in out["reasons"][0]
    assert "quant_fill_general_v1" in out["combos"][0]
    assert out["bundle_applied_count"] == 2
    assert out["bundle_source_runs"] == 3
    assert "risk_triplet_closure_v1" in out["bundles"][0]
    assert out["context_bundle_applied_count"] == 2
    assert out["context_bundle_source_runs"] == 3
    assert out["context_bundle_contexts"] == ["general/A"]
    assert "general/A" in out["context_bundles"][0]
    assert out["context_bundle_effect_applied_count"] == 1
    assert out["context_bundle_effect_source_runs"] == 2
    assert "attribution_runs=2" in out["context_bundle_effect_reasons"][0]
    assert out["context_bundle_metric_effect_applied_count"] == 2
    assert out["context_bundle_metric_effect_source_runs"] == 3
    assert "量化指标达标率" in out["context_bundle_metric_effect_metrics"][0]
    assert out["context_bundle_metric_action_effect_applied_count"] == 2
    assert out["context_bundle_metric_action_effect_source_runs"] == 3
    assert "补量化数值" in out["context_bundle_metric_action_effect_triplets"][0]
    assert out["chapter_effect_summary"][0]["title"] == "工程概况"
    assert "量化指标达标率" in out["chapter_effect_summary"][0]["resolved_metrics"]
    assert "量化指标达标率/补量化数值" in out["chapter_effect_summary"][0]["resolved_action_triplets"]


def test_recent_job_remediation_learning_summary_returns_bundle_only_signal(tmp_path):
    p = tmp_path / "result.json"
    p.write_text(
        json.dumps(
            {
                "variants": [
                    {
                        "generation_trace": {
                            "self_evolution": {
                                "remediation_combo_learning_applied_count": 0,
                                "remediation_combo_bundle_learning_applied_count": 1,
                                "remediation_combo_bundle_learning_source_runs": 2,
                                "remediation_combo_bundle_learning_bundles": [
                                    "缺量化/quant_fill_general_v1/add_quant_value + 缺闭环/risk_triplet_closure_v1/add_risk_control_verify pass=50% n=2"
                                ],
                            }
                        }
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out = _recent_job_remediation_learning_summary({"json": str(p)})
    assert out["applied_count"] == 0
    assert out["bundle_applied_count"] == 1
    assert out["source_runs"] == 2


def test_actions_generate_request_keeps_explicit_logic_template_id_for_variant_plan():
    req = ActionsGenerateRequest(
        topic="模板锁定测试",
        project_type="房建",
        generation_mode="quality_200",
        logic_template_id="C",
        outline=["工程概况"],
        variants=1,
    )
    payload = req.model_dump()
    assert payload["logic_template_id"] == "C"
    plan = _build_variant_plan(payload)
    assert len(plan) == 1
    assert plan[0]["logic_template_id"] == "C"


def test_actions_generate_request_stable_delivery_forces_default_template_when_single_variant():
    req = ActionsGenerateRequest(
        topic="稳定交付测试",
        project_type="房建",
        generation_mode="stable_delivery",
        outline=["工程概况"],
        variants=1,
    )
    payload = _apply_generation_mode_policy(req.model_dump())
    plan = _build_variant_plan(payload)
    assert payload["variant_id"] == 1
    assert payload["logic_template_id"] == "A"
    assert payload["_mode_policy"]["deterministic_variant_forced"] is True
    assert len(plan) == 1
    assert plan[0]["variant_id"] == 1
    assert plan[0]["logic_template_id"] == "A"


def test_actions_generate_request_stable_delivery_keeps_selected_templates():
    req = ActionsGenerateRequest(
        topic="稳定交付显式模板测试",
        project_type="房建",
        generation_mode="stable_delivery",
        outline=["工程概况"],
        variants=2,
        selected_templates=["B", "D"],
    )
    payload = _apply_generation_mode_policy(req.model_dump())
    plan = _build_variant_plan(payload)
    assert payload["_mode_policy"]["stable_output"] is True
    assert payload.get("logic_template_id") in {None, ""}
    assert payload["_mode_policy"].get("deterministic_variant_forced") is None
    assert [item["logic_template_id"] for item in plan] == ["B", "D"]


def test_payload_stage_summary_exposes_stable_delivery_mode_fields():
    out = _payload_stage_summary(
        {
            "topic": "稳定交付测试",
            "generation_mode": "stable_delivery",
            "variant_parallelism": 1,
            "agent_parallelism": 2,
            "_mode_policy": {
                "profile": "stable_delivery",
                "mode_effective": "stable_delivery",
                "stable_output": True,
                "deterministic_variant_forced": True,
                "deterministic_logic_template_id": "A",
            },
        }
    )
    assert out["generation_mode"] == "stable_delivery"
    assert out["mode_effective"] == "stable_delivery"
    assert out["stable_output"] is True
    assert out["deterministic_variant_forced"] is True
    assert out["deterministic_logic_template_id"] == "A"
