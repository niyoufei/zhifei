from __future__ import annotations

import copy
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _admitted_review_chain(monkeypatch):
    """Keep review behavior tests offline; admission has separate contract tests."""

    from backend.app.routers import actions_bridge

    async def fake_admission(payload):
        payload["_provider_admission_run_coordinator"] = object()
        payload.setdefault("provider_chain", [])
        return None

    monkeypatch.setattr(
        actions_bridge,
        "_ensure_review_provider_admission",
        fake_admission,
    )
    # These behavior tests isolate review transformation from the formal
    # delivery/CAS boundary, which has dedicated atomicity tests.
    monkeypatch.setattr(
        actions_bridge,
        "_require_formal_document_mutation",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_capture_promotion_revision",
        lambda _job: ("succeeded", 7),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_promote_job_result_cas",
        lambda **kwargs: {
            "status": kwargs["initial_status"],
            "revision": int(kwargs["initial_revision"]) + 1,
        },
    )
    monkeypatch.setattr(
        actions_bridge,
        "_validate_rollback_snapshot",
        lambda **kwargs: copy.deepcopy(kwargs["revision"]["variants"]),
    )

    def finalize_with_test_rebuild(results, **kwargs):
        return actions_bridge._rebuild_postprocessed_artifacts(
            results,
            payload=kwargs.get("payload") or {},
            report=None,
            params={},
            fail_closed=bool(kwargs.get("fail_closed")),
        )

    monkeypatch.setattr(
        actions_bridge,
        "_finalize_variant_derivatives",
        finalize_with_test_rebuild,
    )


@pytest.mark.asyncio
async def test_actions_review_apply_calls_remediation_and_persists_copy(tmp_path: Path, monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    target = {
        "project_id": "P-REVIEW-1",
        "sections": [{"title": "关键线路", "content": "原始内容"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "关键线路",
                    "type": "consistency",
                    "severity": "high",
                    "problem": "关键线路间隔前后冲突",
                    "suggestion": "统一关键线路间隔口径",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    job = {"payload": {"project_id": "P-REVIEW-1"}}
    output_json = tmp_path / "reviewed.json"
    seen: dict[str, object] = {}

    def fake_apply_remediation(sections, remediation, **kwargs):
        seen["sections"] = sections
        seen["remediation"] = remediation
        seen["kwargs"] = kwargs

    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, {}, {"variants": [target]}, [target]),
    )
    monkeypatch.setattr(actions_bridge, "apply_remediation", fake_apply_remediation)
    monkeypatch.setattr(actions_bridge, "strip_nonconcrete_language", lambda value: value)
    monkeypatch.setattr(actions_bridge, "load_params", lambda: {})
    def fake_rebuild(results, **kwargs):
        results[0]["quality_checks"] = {"issue_list": [], "auto_revision_suggestions": []}

    def fake_save(_name, saved_variants):
        output_json.write_text("{}", encoding="utf-8")
        seen["saved_variants"] = saved_variants
        return {"json": str(output_json)}

    monkeypatch.setattr(actions_bridge, "_rebuild_postprocessed_artifacts", fake_rebuild)
    monkeypatch.setattr(actions_bridge, "_save_outputs", fake_save)
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    monkeypatch.setattr(actions_bridge, "create_revision_snapshot", review_revision.create_revision_snapshot)

    async def fake_professional_render(*, job_id, outputs, **_kwargs):
        return dict(outputs)

    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", fake_professional_render)
    monkeypatch.setattr(actions_bridge, "update_job", lambda *args, **kwargs: None)

    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-review-1",
        variant=1,
        apply_all=True,
        decisions=[],
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest=versions["issue_digest"],
    )
    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        response = await actions_bridge.actions_review_apply(
            request,
            x_actions_key="test-actions-key",
        )

    assert response["ok"] is True
    assert response["applied_count"] == 1
    assert response["template_applied_count"] == 1
    assert seen["sections"] is not target["sections"]
    assert seen["remediation"] == [
        {
            "title": "关键线路",
            "type": "consistency",
            "suggestion": "统一关键线路间隔口径",
        }
    ]
    assert output_json.exists()
    assert target["sections"][0]["content"] == "原始内容"
    assert response["revision_id"].startswith("REV-")
    promotion_rows = review_revision.list_revision_snapshots(job_id="job-review-1")
    assert promotion_rows[0]["promotion"]["state"] == "committed"


@pytest.mark.asyncio
async def test_actions_review_apply_rejects_stale_issue_list(monkeypatch):
    from backend.app.routers import actions_bridge

    target = {
        "sections": [{"title": "质量管理", "content": "当前正文"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "质量管理",
                    "type": "core_conclusion",
                    "severity": "high",
                    "problem": "证据不足",
                    "suggestion": "补齐证据",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: ({"payload": {}}, {}, {"variants": [target]}, [target]),
    )
    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-stale",
        apply_all=True,
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest="stale-digest",
    )
    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        with pytest.raises(HTTPException) as exc:
            await actions_bridge.actions_review_apply(request, x_actions_key="test-actions-key")
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "STALE_REVIEW_STATE"


@pytest.mark.asyncio
async def test_actions_review_apply_render_failure_keeps_live_result(tmp_path: Path, monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    target = {
        "sections": [{"title": "安全管理", "content": "原始正文"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "安全管理",
                    "type": "core_conclusion",
                    "severity": "high",
                    "problem": "闭环不足",
                    "suggestion": "补齐闭环",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    job = {"payload": {}}
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, {}, {"variants": [target]}, [target]),
    )
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    monkeypatch.setattr(actions_bridge, "create_revision_snapshot", review_revision.create_revision_snapshot)
    monkeypatch.setattr(actions_bridge, "strip_nonconcrete_language", lambda value: value)
    monkeypatch.setattr(actions_bridge, "load_params", lambda: {})
    monkeypatch.setattr(
        actions_bridge,
        "apply_remediation",
        lambda sections, remediation, **kwargs: sections[0].update(content="候选正文"),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_rebuild_postprocessed_artifacts",
        lambda results, **kwargs: results[0].update(quality_checks={"issue_list": [], "auto_revision_suggestions": []}),
    )
    candidate_json = tmp_path / "candidate.json"
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        lambda _name, _variants: {"json": str(candidate_json)},
    )

    async def fail_render(**kwargs):
        raise RuntimeError("render failed")

    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", fail_render)
    promoted: list[object] = []
    monkeypatch.setattr(actions_bridge, "update_job", lambda *args, **kwargs: promoted.append((args, kwargs)))
    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-atomic",
        apply_all=True,
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest=versions["issue_digest"],
    )
    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        with pytest.raises(RuntimeError, match="render failed"):
            await actions_bridge.actions_review_apply(request, x_actions_key="test-actions-key")
    assert target["sections"][0]["content"] == "原始正文"
    assert promoted == []


@pytest.mark.asyncio
async def test_actions_review_apply_blocks_remaining_high_risk(tmp_path: Path, monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    target = {
        "sections": [{"title": "质量管理", "content": "原始正文"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "质量管理",
                    "type": "core_conclusion",
                    "severity": "high",
                    "problem": "仍有重大问题",
                    "suggestion": "必须解决",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: ({"payload": {}}, {}, {"variants": [target]}, [target]),
    )
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    monkeypatch.setattr(actions_bridge, "create_revision_snapshot", review_revision.create_revision_snapshot)
    monkeypatch.setattr(actions_bridge, "strip_nonconcrete_language", lambda value: value)
    monkeypatch.setattr(actions_bridge, "load_params", lambda: {})
    monkeypatch.setattr(actions_bridge, "apply_remediation", lambda *args, **kwargs: None)
    monkeypatch.setattr(actions_bridge, "_rebuild_postprocessed_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(actions_bridge, "_save_outputs", lambda *args, **kwargs: pytest.fail("must not persist"))
    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-high-risk",
        apply_all=True,
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest=versions["issue_digest"],
    )
    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        with pytest.raises(HTTPException) as exc:
            await actions_bridge.actions_review_apply(request, x_actions_key="test-actions-key")
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "REVIEW_HIGH_RISK_REMAINS"
    assert target["sections"][0]["content"] == "原始正文"


@pytest.mark.asyncio
async def test_actions_review_apply_runs_ai_recheck_and_second_round(tmp_path: Path, monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    target = {
        "project_id": "P-REVIEW-2",
        "sections": [{"title": "施工进度计划", "content": "第一版正文"}],
        "quality_checks": {
            "issue_list": [
                {
                    "title": "全局一致性",
                    "type": "consistency",
                    "severity": "high",
                    "problem": "工期冲突",
                    "suggestion": "统一工期口径",
                }
            ],
            "auto_revision_suggestions": [],
        },
    }
    job = {
        "payload": {
            "project_id": "P-REVIEW-2",
            "provider_chain": [
                {"slot": "text_review", "provider": "anthropic", "model": "review-model"}
            ],
        }
    }
    output_json = tmp_path / "reviewed-ai.json"
    calls = {"rewrite": 0, "rebuild": 0}

    async def fake_rewrite(*, section, issues, payload, round_number):
        calls["rewrite"] += 1
        return (
            f"第{round_number}轮正文",
            {
                "round": round_number,
                "title": section["title"],
                "issue_ids": [item["issue_id"] for item in issues],
                "status": "success",
                "provider": "anthropic",
                "model": "review-model",
                "slot": "text_review",
                "attempts": [],
            },
        )

    def fake_rebuild(results, **kwargs):
        calls["rebuild"] += 1
        rec = results[0]
        if calls["rebuild"] == 1:
            rec["quality_checks"] = {
                "issue_list": [
                    {
                        "title": "全局一致性",
                        "type": "consistency",
                        "severity": "high",
                        "problem": "复核仍发现工期冲突",
                        "suggestion": "再次统一工期口径",
                    }
                ],
                "auto_revision_suggestions": [],
            }
        else:
            rec["quality_checks"] = {"issue_list": [], "auto_revision_suggestions": []}

    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, {}, {"variants": [target]}, [target]),
    )
    monkeypatch.setattr(actions_bridge, "_rewrite_review_section", fake_rewrite)
    monkeypatch.setattr(actions_bridge, "strip_nonconcrete_language", lambda value: value)
    monkeypatch.setattr(actions_bridge, "load_params", lambda: {})
    monkeypatch.setattr(actions_bridge, "_rebuild_postprocessed_artifacts", fake_rebuild)
    saved: dict[str, object] = {}

    def fake_save(_name, saved_variants):
        output_json.write_text("{}", encoding="utf-8")
        saved["variants"] = saved_variants
        return {"json": str(output_json)}

    monkeypatch.setattr(actions_bridge, "_save_outputs", fake_save)
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    monkeypatch.setattr(actions_bridge, "create_revision_snapshot", review_revision.create_revision_snapshot)

    async def fake_professional_render(*, job_id, outputs, **_kwargs):
        return dict(outputs)

    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", fake_professional_render)
    monkeypatch.setattr(actions_bridge, "update_job", lambda *args, **kwargs: None)

    versions = actions_bridge._review_versions([target], 0)
    request = actions_bridge.ActionsReviewApplyRequest(
        job_id="job-review-2",
        variant=1,
        apply_all=True,
        decisions=[],
        expected_result_version=versions["result_version"],
        expected_variant_version=versions["variant_version"],
        expected_issue_digest=versions["issue_digest"],
    )
    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        response = await actions_bridge.actions_review_apply(request, x_actions_key="test-actions-key")

    assert response["ai_rewritten_chapter_count"] == 1
    assert response["round_2_recheck_item_count"] == 1
    assert response["round_2_rewritten_chapter_count"] == 1
    assert response["remaining_issue_count"] == 0
    assert calls == {"rewrite": 2, "rebuild": 2}
    saved_target = saved["variants"][0]
    assert saved_target["sections"][0]["content"] == "第2轮正文"
    assert saved_target["sections"][0]["pre_review_apply_content"] == "第一版正文"
    assert saved_target["review_apply_audit"]["remaining_issue_count"] == 0
    assert target["sections"][0]["content"] == "第一版正文"
    assert output_json.exists()


def test_review_postprocess_can_fail_closed(monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import cross_index, param_trace, plan_consistency

    monkeypatch.setattr(actions_bridge, "load_tender_matrix", lambda **kwargs: {})
    monkeypatch.setattr(actions_bridge, "load_boq_data", lambda **kwargs: {})
    monkeypatch.setattr(actions_bridge, "recommend_four_new", lambda *args, **kwargs: [])
    monkeypatch.setattr(actions_bridge, "run_quality_checks", lambda *args, **kwargs: {"issue_list": []})
    monkeypatch.setattr(plan_consistency, "normalize_metrics_in_sections", lambda sections: {"ok": True})
    monkeypatch.setattr(param_trace, "build_param_receipt", lambda sections, params: {"ok": True})
    monkeypatch.setattr(param_trace, "save_latest_receipt", lambda *args, **kwargs: "receipt.json")
    monkeypatch.setattr(
        cross_index,
        "build_cross_index",
        lambda **kwargs: {
            "ok": True,
            "focus_count": 0,
            "mentioned_count": 0,
            "closed_ok_count": 0,
            "missing_drawing_locator_count": 0,
            "missing_standard_locator_count": 0,
            "focus_items": [],
        },
    )

    def fail_evidence(**kwargs):
        raise ValueError("evidence rebuild failed")

    monkeypatch.setattr(actions_bridge, "build_evidence_tracking", fail_evidence)
    result = {"sections": [{"title": "质量管理", "content": "正文"}], "outline": ["质量管理"]}
    with pytest.raises(RuntimeError, match="POSTPROCESS_REBUILD_FAILED"):
        actions_bridge._rebuild_postprocessed_artifacts(
            [result], payload={}, report=None, params={}, fail_closed=True
        )
    assert result["postprocess_errors"][0]["stage"] == "evidence_tracking"


def test_delivery_quality_block_is_not_misclassified_as_rebuild_failure(monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import cross_index, param_trace, plan_consistency

    monkeypatch.setattr(actions_bridge, "load_tender_matrix", lambda **kwargs: {})
    monkeypatch.setattr(actions_bridge, "load_boq_data", lambda **kwargs: {})
    monkeypatch.setattr(actions_bridge, "recommend_four_new", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        actions_bridge,
        "run_quality_checks",
        lambda *args, **kwargs: {"issue_list": []},
    )
    monkeypatch.setattr(
        plan_consistency,
        "normalize_metrics_in_sections",
        lambda sections: {"ok": True},
    )
    monkeypatch.setattr(
        param_trace,
        "build_param_receipt",
        lambda sections, params: {"ok": True},
    )
    monkeypatch.setattr(
        param_trace,
        "save_latest_receipt",
        lambda *args, **kwargs: "receipt.json",
    )
    monkeypatch.setattr(
        cross_index,
        "build_cross_index",
        lambda **kwargs: {
            "ok": True,
            "focus_count": 0,
            "mentioned_count": 0,
            "closed_ok_count": 0,
            "missing_drawing_locator_count": 0,
            "missing_standard_locator_count": 0,
            "focus_items": [],
        },
    )
    monkeypatch.setattr(
        actions_bridge,
        "build_evidence_tracking",
        lambda **kwargs: {"rows": [], "summary": {}},
    )
    monkeypatch.setattr(
        actions_bridge,
        "audit_standard_citations",
        lambda *args, **kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        actions_bridge,
        "build_delivery_quality_gate",
        lambda **kwargs: {
            "delivery_allowed": False,
            "decision_digest": "blocked-but-not-rebuild-error",
            "blockers": [{"code": "CONTENT_REVIEW_BLOCKED"}],
        },
    )

    result = {"sections": [{"title": "质量管理", "content": "正文"}], "outline": ["质量管理"]}
    actions_bridge._rebuild_postprocessed_artifacts(
        [result],
        payload={"dry_run": True, "quality_strict": False},
        report=None,
        params={},
        fail_closed=True,
    )

    assert "postprocess_errors" not in result
    assert result["delivery_quality_gate"]["delivery_allowed"] is False


def test_review_postprocess_rejects_unrelated_traceable_locator(monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import cross_index, param_trace, plan_consistency
    from backend.zhifei_autoplan.requirement_evidence_matrix import (
        build_requirement_evidence_plan,
    )

    tender = {
        "items": [
            {
                "dimension": "扣分项",
                "keywords": ["质量验收闭环"],
                "source_spans": [
                    {
                        "file_name": "/private/uploads/招标文件.pdf",
                        "page": 3,
                        "start": 88,
                        "end": 96,
                        "snippet": "质量验收闭环",
                    }
                ],
            }
        ]
    }
    contract = {
        "chapters": [
            {
                "chapter_id": "CH-001",
                "title": "质量管理",
                "agents": {"master": "章节主笔Agent", "compliance": "规范合规Agent"},
            }
        ]
    }
    plan = build_requirement_evidence_plan(
        tender=tender,
        chapter_requirements={},
        global_requirements=[],
        agent_contract=contract,
    )
    requirement_id = plan["rows"][0]["requirement_id"]
    result = {
        "sections": [
            {
                "title": "质量管理",
                "content": (
                    f"落实质量验收闭环。【要求:{requirement_id}】"
                    "【证据:无关资料.pdf#p1_deadbeef@9】"
                ),
            }
        ],
        "outline": ["质量管理"],
        "requirement_evidence_plan": plan,
    }
    monkeypatch.setattr(actions_bridge, "load_tender_matrix", lambda **kwargs: tender)
    monkeypatch.setattr(actions_bridge, "load_boq_data", lambda **kwargs: {})
    monkeypatch.setattr(actions_bridge, "recommend_four_new", lambda *args, **kwargs: [])
    monkeypatch.setattr(actions_bridge, "run_quality_checks", lambda *args, **kwargs: {"issue_list": []})
    monkeypatch.setattr(plan_consistency, "normalize_metrics_in_sections", lambda sections: {"ok": True})
    monkeypatch.setattr(param_trace, "build_param_receipt", lambda sections, params: {"ok": True})
    monkeypatch.setattr(param_trace, "save_latest_receipt", lambda *args, **kwargs: "receipt.json")
    monkeypatch.setattr(
        cross_index,
        "build_cross_index",
        lambda **kwargs: {
            "ok": True,
            "focus_count": 0,
            "mentioned_count": 0,
            "closed_ok_count": 0,
            "missing_drawing_locator_count": 0,
            "missing_standard_locator_count": 0,
            "focus_items": [],
        },
    )
    monkeypatch.setattr(actions_bridge, "audit_standard_citations", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(
        actions_bridge,
        "build_delivery_quality_gate",
        lambda **kwargs: {"delivery_allowed": True, "blockers": []},
    )

    with pytest.raises(RuntimeError, match="POSTPROCESS_REBUILD_FAILED"):
        actions_bridge._rebuild_postprocessed_artifacts(
            [result],
            payload={"quality_strict": True, "requirement_evidence_hard_gate": True},
            report=None,
            params={},
            fail_closed=True,
        )
    assert result["requirement_evidence_chapter_gates"][0]["ok"] is False
    assert result["requirement_evidence_chapter_gates"][0]["rows"][0]["status"] == (
        "EVIDENCE_SOURCE_MISMATCH"
    )
    assert any(
        row["stage"] == "requirement_evidence_chapter_gate"
        for row in result["postprocess_errors"]
    )


@pytest.mark.asyncio
async def test_actions_review_rollback_restores_snapshot_atomically(tmp_path: Path, monkeypatch):
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    old_variants = [{"sections": [{"title": "总则", "content": "旧版正文"}]}]
    current_variants = [{"sections": [{"title": "总则", "content": "当前正文"}]}]
    old_revision = review_revision.create_revision_snapshot(
        job_id="job-rollback",
        variants=old_variants,
        result={},
        reason="pre_review_apply",
    )
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: ({"payload": {}}, {}, {"variants": current_variants}, current_variants),
    )
    saved: dict[str, object] = {}
    output_json = tmp_path / "rollback.json"

    def fake_save(_name, variants):
        output_json.write_text("{}", encoding="utf-8")
        saved["variants"] = variants
        return {"json": str(output_json)}

    async def fake_render(**kwargs):
        return dict(kwargs["outputs"])

    promoted: list[object] = []
    monkeypatch.setattr(actions_bridge, "_save_outputs", fake_save)
    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", fake_render)
    monkeypatch.setattr(
        actions_bridge,
        "_promote_job_result_cas",
        lambda **kwargs: promoted.append(kwargs)
        or {"status": "succeeded", "revision": int(kwargs["initial_revision"]) + 1},
    )
    request = actions_bridge.ActionsReviewRollbackRequest(
        job_id="job-rollback",
        revision_id=old_revision["revision_id"],
        expected_result_version=review_revision.result_version(current_variants),
        actor="tester",
    )
    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        response = await actions_bridge.actions_review_rollback(
            request, x_actions_key="test-actions-key"
        )

    assert response["ok"] is True
    assert saved["variants"] == old_variants
    assert current_variants[0]["sections"][0]["content"] == "当前正文"
    assert len(promoted) == 1
    rows = review_revision.list_revision_snapshots(job_id="job-rollback")
    assert len(rows) == 2
    safety = next(row for row in rows if row["revision_id"] == response["safety_revision_id"])
    assert safety["promotion"]["operation"] == "rollback"
    assert safety["promotion"]["state"] == "committed"
