from __future__ import annotations

import copy
import hashlib
from types import SimpleNamespace

import pytest

from backend.zhifei_autoplan import evidence, export_docx_service


def _cross_index(*focus_names: str, rows_metric: int | None = None) -> dict:
    value = {
        "ok": True,
        "focus_count": len(focus_names),
        "mentioned_count": 0,
        "closed_ok_count": 0,
        "missing_drawing_locator_count": 0,
        "missing_standard_locator_count": 0,
        "focus_items": [
            {
                "name": name,
                "chapter": None,
                "drawing_locator": None,
                "drawing_requirement": {"status": "required", "reason": ""},
                "drawing_validation": {"ok": False, "reason": "not_mentioned"},
                "closure": {"ok": False},
                "flags": [],
            }
            for name in focus_names
        ],
    }
    if rows_metric is not None:
        value["rows"] = rows_metric
    return value


def _valid_indexes(
    *focus_names: str,
    drawing_index=None,
    standard_index=None,
    rows_metric: int | None = None,
    project_id: str | None = None,
) -> dict:
    if project_id and drawing_index is None:
        drawing_index = {
            "ok": True,
            "project_id": project_id,
            "drawings": [{"filename": "总图.pdf"}],
            "indexed_drawing_count": 1,
            "integrity_rejection_count": 0,
            "invalid_identity_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "text_index_status": "complete",
        }
    if project_id and standard_index is None:
        standard_index = {
            "ok": True,
            "project_id": project_id,
            "standards": [
                {
                    "filename": "规范.pdf",
                    "standard_code": None,
                    "standard_codes": [],
                    "official_registry_status": "not_verified",
                    "source_integrity_status": "verified",
                }
            ],
            "indexed_standard_count": 1,
            "integrity_rejection_count": 0,
            "invalid_identity_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "text_index_status": "complete",
        }
    cross_index = _cross_index(*focus_names, rows_metric=rows_metric)
    if project_id:
        cross_index["project_id"] = project_id
    return {
        "drawing_index": drawing_index,
        "standard_index": standard_index,
        "cross_index": cross_index,
    }


def _closed_indexes(name: str, *, locator: str) -> dict:
    cross_index = _cross_index(name)
    cross_index.update(
        {
            "project_id": "p1",
            "mentioned_count": 1,
            "closed_ok_count": 1,
        }
    )
    cross_index["focus_items"][0].update(
        {
            "chapter": "钢结构施工工艺",
            "drawing_locator": locator,
            "drawing_validation": {"ok": True, "reason": "validated"},
            "closure": {"ok": True},
        }
    )
    return {
        "drawing_index": {},
        "standard_index": {},
        "cross_index": cross_index,
    }


def _empty_requirement_plan() -> dict:
    core = {
        "schema": "requirement-evidence-matrix-v1",
        "phase": "planned",
        "rows": [],
        "summary": {"requirement_count": 0, "mandatory_count": 0},
    }
    return {**core, "matrix_digest": export_docx_service.canonical_export_digest(core)}


def _formal_source_fields(
    project_id: str = "P-EXPORT",
    *,
    sections: list[dict] | None = None,
    tender: dict | None = None,
    boq: dict | None = None,
) -> dict:
    source_sections = sections or [{"title": "工程概况", "content": "文本"}]
    source_core = {
        "schema_version": "autoplan-source-input-v1",
        "project_id": project_id,
        "tender_digest": export_docx_service.canonical_export_digest(tender or {}),
        "boq_digest": export_docx_service.canonical_export_digest(boq or {}),
    }
    return {
        "project_id": project_id,
        "_formal_source_verified": True,
        "_formal_source_job_id": "source-job-formal",
        "_formal_source_delivery_decision_digest": "d" * 64,
        "_formal_source_sections_digest": (
            export_docx_service.canonical_sections_digest(source_sections)
        ),
        "source_input_receipt": {
            **source_core,
            "receipt_digest": export_docx_service.canonical_export_digest(
                source_core
            ),
        },
        "requirement_evidence_plan": _empty_requirement_plan(),
    }


def _passing_complete_delivery_gate() -> dict:
    checks = []
    for name in sorted(export_docx_service._DIRECT_EXPORT_REQUIRED_GATE_CHECKS):
        row = {"name": name, "pass": True}
        if name in {
            "formal_project_parameters",
            "formal_parameter_body_binding",
            "independent_model_review",
        }:
            row["required"] = True
        checks.append(row)
    core = {
        "schema_version": "delivery-quality-gate-v1",
        "strict": True,
        "delivery_allowed": True,
        "checks": checks,
        "blocker_count": 0,
        "warning_count": 0,
        "blockers": [],
        "warnings": [],
    }
    return {**core, "decision_digest": export_docx_service.canonical_export_digest(core)}


def test_source_input_receipt_binds_exact_current_tender_and_boq() -> None:
    tender = {"project_name": "项目A", "planned_duration_days": 150}
    boq = {"items": [{"name": "钢梁", "quantity": 59.214, "unit": "t"}]}
    receipt = _formal_source_fields(
        "P-SOURCE",
        tender=tender,
        boq=boq,
    )["source_input_receipt"]

    assert export_docx_service._validate_source_input_receipt(
        receipt,
        project_id="P-SOURCE",
        tender=tender,
        boq=boq,
    ) == receipt

    with pytest.raises(ValueError, match="direct_export_tender_input_changed"):
        export_docx_service._validate_source_input_receipt(
            receipt,
            project_id="P-SOURCE",
            tender={**tender, "planned_duration_days": 120},
            boq=boq,
        )
    with pytest.raises(ValueError, match="direct_export_boq_input_changed"):
        export_docx_service._validate_source_input_receipt(
            receipt,
            project_id="P-SOURCE",
            tender=tender,
            boq={"items": [{"name": "钢梁", "quantity": 59214, "unit": "t"}]},
        )


@pytest.fixture
def passing_formal_delivery_gate(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    calls: list[dict] = []

    def _build_gate(**kwargs):
        calls.append(kwargs)
        return _passing_complete_delivery_gate()

    monkeypatch.setattr(
        "backend.zhifei_autoplan.delivery_quality.build_delivery_quality_gate",
        _build_gate,
    )
    return calls


def _passing_direct_quality(score: int = 96) -> dict:
    return {
        "score": score,
        "quality_gate": {"pass": True, "blocking_issue_count": 0},
        "independent_content_review": {
            "score": score,
            "quality_gate": {"pass": True, "blocking_issue_count": 0},
            "dimensions": {
                "non_repetition": {"score": 80, "pass": True},
            },
        },
    }


def test_execute_export_docx_request_builds_payload_and_updates_job(
    passing_formal_delivery_gate,
):
    seen: dict[str, object] = {}

    def _create_job(payload, **kwargs):
        seen["job_payload"] = payload
        seen["job_kwargs"] = kwargs
        return "job-export-1"

    def _save_outputs(base_name, results, **kwargs):
        seen["base_name"] = base_name
        seen["results"] = results
        seen["save_kwargs"] = kwargs
        return {"json": "/tmp/actions_export_1.json", "docx": ["/tmp/actions_export_1.docx"]}

    def _update_job(job_id, **kwargs):
        seen["updated_job_id"] = job_id
        seen["update_kwargs"] = kwargs

    payload = export_docx_service.build_export_docx_payload(
        raw_request={
            "topic": "导出测试",
            "project_id": "P-1",
            "style": {"font": "Song"},
            "sections": [{"title": "施工部署", "content": "原始文本"}],
            "generate_images": True,
            "bidder_company": "ACME",
            "bidder_domain": "acme.test",
            "logo_url": "https://example.com/logo.png",
        },
        workspace_dir="/tmp/ws-export",
        load_tender_matrix_fn=lambda **kwargs: {"project_name": "项目A", "project_code": "CODE-A"},
        load_boq_data_fn=lambda **kwargs: {"stats": {"total": 1}},
        build_boq_focus_fn=lambda boq: {"focus_count": 1},
        load_params_fn=lambda: {"image": True},
        strip_nonconcrete_language_fn=lambda text: f"clean:{text}",
        normalize_metrics_in_sections_fn=lambda sections: {
            "ok": True,
            "normalized": True,
            "count": len(sections),
        },
        recommend_four_new_fn=lambda *args, **kwargs: ["四新工艺"],
        run_quality_checks_fn=lambda tender, outline, sections, **kwargs: {
            **_passing_direct_quality(),
            "strict": kwargs["strict"],
            "outline": outline,
            "sections": sections,
        },
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            drawing_index={"rows": 1},
            standard_index={"rows": 2},
            rows_metric=3,
        ),
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [{"title": "施工部署"}], "summary": {"count": 1}},
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/mock.png", "caption": "图示"}],
    )

    assert payload["project_name"] == "项目A"
    assert payload["project_code"] == "CODE-A"
    assert payload["outline"] == ["施工部署"]
    assert payload["sections"] == [{"title": "施工部署", "content": "clean:原始文本"}]
    assert payload["quality_checks"]["score"] == 96
    assert payload["quality_checks"]["strict"] is True
    assert payload["boq_focus"]["four_new_recommendations"] == ["四新工艺"]
    assert payload["drawing_index"] == {"rows": 1}
    assert payload["standard_index"] == {"rows": 2}
    assert payload["cross_index"] == _cross_index(rows_metric=3)
    assert payload["plan_consistency"] == {
        "ok": True,
        "normalized": True,
        "count": 1,
    }
    assert payload["branding"] == {
        "project_id": "P-1",
        "bidder_company": "ACME",
        "bidder_domain": "acme.test",
        "logo_url": "https://example.com/logo.png",
    }
    assert payload["evidence_tracking"] == {"rows": [{"title": "施工部署"}], "summary": {"count": 1}}
    assert payload["media"] == [{"path": "/tmp/mock.png", "caption": "图示"}]

    out = export_docx_service.execute_export_docx_request(
        raw_request={
            "topic": "导出测试",
            **_formal_source_fields(
                "P-1",
                sections=[{"title": "施工部署", "content": "原始文本"}],
                tender={"project_name": "项目A", "project_code": "CODE-A"},
                boq={"stats": {"total": 1}},
            ),
            "style": {"font": "Song"},
            "sections": [{"title": "施工部署", "content": "原始文本"}],
            "generate_images": True,
            "bidder_company": "ACME",
            "bidder_domain": "acme.test",
            "logo_url": "https://example.com/logo.png",
        },
        workspace_dir="/tmp/ws-export",
        save_outputs_fn=_save_outputs,
        load_tender_matrix_fn=lambda **kwargs: {"project_name": "项目A", "project_code": "CODE-A"},
        load_boq_data_fn=lambda **kwargs: {"stats": {"total": 1}},
        build_boq_focus_fn=lambda boq: {"focus_count": 1},
        load_params_fn=lambda: {"image": True},
        strip_nonconcrete_language_fn=lambda text: f"clean:{text}",
        normalize_metrics_in_sections_fn=lambda sections: {
            "ok": True,
            "normalized": True,
            "count": len(sections),
        },
        recommend_four_new_fn=lambda *args, **kwargs: ["四新工艺"],
        run_quality_checks_fn=lambda tender, outline, sections, **kwargs: {
            **_passing_direct_quality(),
            "strict": kwargs["strict"],
            "outline": outline,
            "sections": sections,
        },
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            rows_metric=3,
            project_id="P-1",
        ),
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [{"title": "施工部署"}], "summary": {"count": 1}},
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/mock.png", "caption": "图示"}],
        create_job_fn=_create_job,
        update_job_fn=_update_job,
    )

    assert out == {
        "ok": True,
        "job_id": "job-export-1",
        "files": {"json": "/tmp/actions_export_1.json", "docx": ["/tmp/actions_export_1.docx"]},
    }
    assert seen["job_payload"] == {"action": "export_docx", "workspace_dir": "/tmp/ws-export"}
    assert seen["job_kwargs"] == {"user_id": None, "workspace_dir": "/tmp/ws-export"}
    assert seen["base_name"] == "actions_export_job-export-1"
    assert seen["save_kwargs"] == {"workspace_dir": "/tmp/ws-export"}
    assert seen["updated_job_id"] == "job-export-1"
    assert seen["update_kwargs"] == {
        "status": "done",
        "result": {"json": "/tmp/actions_export_1.json", "docx": ["/tmp/actions_export_1.docx"]},
        "workspace_dir": "/tmp/ws-export",
    }

    exported = seen["results"][0]
    assert exported["sections"] == [
        {"title": "施工部署", "content": "原始文本"}
    ]
    assert exported["delivery_quality_gate"]["delivery_allowed"] is True
    assert exported["delivery_quality_gate"]["decision_digest"] != "d" * 64
    assert export_docx_service.delivery_gate_digest_is_valid(
        exported["delivery_quality_gate"]
    )
    assert exported["direct_export_binding_receipt"][
        "final_sections_digest"
    ] == export_docx_service.canonical_sections_digest(exported["sections"])
    assert exported["direct_export_binding_receipt"][
        "source_delivery_decision_digest"
    ] == "d" * 64
    assert len(passing_formal_delivery_gate) == 1
    rebuilt = passing_formal_delivery_gate[0]
    assert rebuilt["sections"] == exported["sections"]
    assert rebuilt["cross_index"] == exported["cross_index"]
    assert rebuilt["formal_delivery_required"] is True
    assert rebuilt["model_review_required"] is True


def test_execute_export_docx_request_accepts_current_store_signatures(
    passing_formal_delivery_gate,
):
    seen: dict[str, object] = {}

    def _load_tender_matrix(*, project_id=None):
        seen["tender_project_id"] = project_id
        return {"project_name": "当前项目", "project_code": "CUR-01"}

    def _load_boq_data(*, project_id=None):
        seen["boq_project_id"] = project_id
        return {"stats": {"items": 1}}

    def _run_quality_checks(tender, outline, sections, *, boq, boq_focus, project_id, strict):
        seen["quality_project_id"] = project_id
        return {**_passing_direct_quality(90), "strict": strict}

    def _build_export_indexes(*, topic, outline, project_id, boq, sections, boq_focus, quality_checks):
        seen["index_project_id"] = project_id
        return _valid_indexes(project_id="P-CURRENT")

    def _create_job(payload, user_id=None):
        seen["job_payload"] = payload
        seen["job_user_id"] = user_id
        return "job-current-store"

    def _save_outputs(base_name, results):
        seen["base_name"] = base_name
        seen["results"] = results
        return {"json": "/tmp/current-store.json"}

    def _update_job(job_id, status=None, result=None):
        seen["updated_job_id"] = job_id
        seen["updated_status"] = status
        seen["updated_result"] = result

    out = export_docx_service.execute_export_docx_request(
        raw_request={
            "topic": "当前签名兼容",
            **_formal_source_fields(
                "P-CURRENT",
                sections=[{"title": "工程概况", "content": "文本"}],
                tender={"project_name": "当前项目", "project_code": "CUR-01"},
                boq={"stats": {"items": 1}},
            ),
            "sections": [{"title": "工程概况", "content": "文本"}],
            "generate_images": False,
        },
        workspace_dir="/tmp/ws-current",
        save_outputs_fn=_save_outputs,
        load_tender_matrix_fn=_load_tender_matrix,
        load_boq_data_fn=_load_boq_data,
        build_boq_focus_fn=lambda boq: {"focus": "ok"},
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: {"ok": True},
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=_run_quality_checks,
        build_export_indexes_fn=_build_export_indexes,
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [], "summary": {}},
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/ignored.png"}],
        create_job_fn=_create_job,
        update_job_fn=_update_job,
    )

    assert out == {"ok": True, "job_id": "job-current-store", "files": {"json": "/tmp/current-store.json"}}
    assert seen["tender_project_id"] == "P-CURRENT"
    assert seen["boq_project_id"] == "P-CURRENT"
    assert seen["quality_project_id"] == "P-CURRENT"
    assert seen["index_project_id"] == "P-CURRENT"
    assert seen["job_payload"] == {"action": "export_docx", "workspace_dir": "/tmp/ws-current"}
    assert seen["job_user_id"] is None
    assert seen["base_name"] == "actions_export_job-current-store"
    assert seen["updated_job_id"] == "job-current-store"
    assert seen["updated_status"] == "done"
    assert seen["updated_result"] == {"json": "/tmp/current-store.json"}
    assert seen["results"][0]["project_name"] == "当前项目"


def _execute_failure_case(
    build_indexes_fn,
    updates: list,
    saves: list,
    *,
    focus_names: tuple[str, ...] = (),
    raw_request_overrides: dict | None = None,
    quality_result: dict | None = None,
    plan_result: dict | None = None,
):
    raw_request = {
        "topic": "失败闭环",
        "sections": [{"title": "工程概况", "content": "文本"}],
        "generate_images": False,
    }
    raw_request.update(raw_request_overrides or {})
    return export_docx_service.execute_export_docx_request(
        raw_request=raw_request,
        workspace_dir="/tmp/ws-fail-close",
        load_tender_matrix_fn=lambda **_kwargs: {},
        load_boq_data_fn=lambda **_kwargs: {},
        build_boq_focus_fn=lambda _boq: {
            "must_cover_keywords": list(focus_names)
        },
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda _sections: plan_result,
        recommend_four_new_fn=lambda *_args, **_kwargs: [],
        run_quality_checks_fn=lambda *_args, **_kwargs: quality_result or {},
        build_export_indexes_fn=build_indexes_fn,
        build_evidence_tracking_fn=lambda **_kwargs: {"rows": [], "summary": {}},
        build_export_media_fn=lambda **_kwargs: [],
        save_outputs_fn=lambda *_args, **_kwargs: saves.append(True),
        create_job_fn=lambda *_args, **_kwargs: "job-fail-close",
        update_job_fn=lambda job_id, **kwargs: updates.append((job_id, kwargs)),
    )


def _assert_export_job_failed(updates: list, saves: list) -> None:
    assert saves == []
    assert len(updates) == 1
    job_id, update = updates[0]
    assert job_id == "job-fail-close"
    assert update["status"] == "failed"
    assert update["error"]["code"] == "EXPORT_DOCX_FAILED"
    assert update["error"]["stage"] == "export_pipeline"
    assert "result" not in update


def test_direct_export_enforcer_exception_marks_job_failed(monkeypatch):
    updates: list = []
    saves: list = []
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.ensure_boq_focus_item_cards",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("enforcer boom")),
    )

    with pytest.raises(RuntimeError, match="enforcer boom"):
        _execute_failure_case(lambda **_kwargs: _valid_indexes(), updates, saves)

    _assert_export_job_failed(updates, saves)
    assert updates[0][1]["error"]["error_type"] == "RuntimeError"


def test_direct_export_index_exception_marks_job_failed():
    updates: list = []
    saves: list = []

    with pytest.raises(RuntimeError, match="index boom"):
        _execute_failure_case(
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("index boom")),
            updates,
            saves,
        )

    _assert_export_job_failed(updates, saves)
    assert updates[0][1]["error"]["error_type"] == "RuntimeError"


def test_direct_export_missing_cross_index_marks_job_failed():
    updates: list = []
    saves: list = []

    with pytest.raises(ValueError, match="cross_index_not_object"):
        _execute_failure_case(
            lambda **_kwargs: {"drawing_index": {}, "standard_index": {}},
            updates,
            saves,
        )

    _assert_export_job_failed(updates, saves)
    assert updates[0][1]["error"]["error_type"] == "ValueError"


def test_direct_export_incomplete_focus_closure_marks_job_failed():
    updates: list = []
    saves: list = []

    incomplete = _valid_indexes("钢梁")
    with pytest.raises(ValueError, match="cross_index_formal_closure_incomplete"):
        _execute_failure_case(
            lambda **_kwargs: incomplete,
            updates,
            saves,
            focus_names=("钢梁",),
        )

    _assert_export_job_failed(updates, saves)
    assert updates[0][1]["error"]["error_type"] == "ValueError"


@pytest.mark.parametrize(
    ("quality_result", "plan_result", "error_code"),
    [
        (
            {
                "score": 0,
                "quality_gate": {"pass": False},
                "independent_content_review": {
                    "score": 0,
                    "dimensions": {"non_repetition": {"score": 0}},
                },
            },
            {"ok": True},
            "direct_export_content_quality_blocked",
        ),
        (_passing_direct_quality(), {"ok": False}, "direct_export_plan_consistency_blocked"),
    ],
)
def test_direct_export_quality_and_plan_fail_closed(
    quality_result,
    plan_result,
    error_code,
    passing_formal_delivery_gate,
):
    updates: list = []
    saves: list = []

    with pytest.raises(ValueError, match=error_code):
        _execute_failure_case(
            lambda **_kwargs: _valid_indexes(project_id="P-EXPORT"),
            updates,
            saves,
            raw_request_overrides=_formal_source_fields(),
            quality_result=quality_result,
            plan_result=plan_result,
        )

    _assert_export_job_failed(updates, saves)


def test_direct_export_requires_verified_formal_source_job() -> None:
    updates: list = []
    saves: list = []

    with pytest.raises(ValueError, match="direct_export_formal_source_required"):
        _execute_failure_case(
            lambda **_kwargs: _valid_indexes(),
            updates,
            saves,
            raw_request_overrides={"project_id": "P1"},
            quality_result=_passing_direct_quality(),
            plan_result={"ok": True},
        )

    _assert_export_job_failed(updates, saves)


def test_formal_direct_export_rejects_any_section_normalization_mutation() -> None:
    sections = [{"title": "施工进度", "content": "工期150天。工程概况工期120天。"}]
    raw_request = {
        "topic": "源章节摘要绑定",
        **_formal_source_fields("P-BIND", sections=sections),
        "sections": sections,
    }

    def _mutating_normalizer(rows):
        rows[0]["content"] = "工期150天。工程概况工期150天。"
        return {"ok": True, "changed": [{"title": "施工进度"}]}

    with pytest.raises(
        ValueError,
        match="direct_export_sections_require_source_regeneration",
    ):
        export_docx_service.collect_export_docx_inputs(
            raw_request=raw_request,
            workspace_dir="/tmp/ws-bind",
            load_tender_matrix_fn=lambda **_kwargs: {},
            load_boq_data_fn=lambda **_kwargs: {},
            build_boq_focus_fn=lambda _boq: {},
            load_params_fn=dict,
            normalize_metrics_in_sections_fn=_mutating_normalizer,
        )


@pytest.mark.parametrize(
    ("index_name", "field", "value", "error_code"),
    [
        (
            "drawing_index",
            "integrity_rejection_count",
            1,
            "direct_export_drawing_index_incomplete",
        ),
        (
            "standard_index",
            "text_index_status",
            "incomplete",
            "direct_export_standard_index_incomplete",
        ),
        (
            "drawing_index",
            "project_id",
            "P-OTHER",
            "direct_export_drawing_index_project_mismatch",
        ),
    ],
)
def test_formal_direct_export_rejects_incomplete_current_indexes(
    index_name,
    field,
    value,
    error_code,
) -> None:
    indexes = copy.deepcopy(_valid_indexes(project_id="P-INDEX"))
    indexes[index_name][field] = value

    with pytest.raises((TypeError, ValueError), match=error_code):
        export_docx_service._validate_formal_export_indexes(
            indexes,
            project_id="P-INDEX",
        )


def _approved_not_applicable_empty_indexes() -> dict:
    project_id = "P-NA"
    cross_index = _cross_index("氧气瓶")
    cross_index.update(
        {
            "project_id": project_id,
            "mentioned_count": 1,
            "closed_ok_count": 1,
        }
    )
    cross_index["focus_items"][0].update(
        {
            "chapter": "现场安全管理",
            "drawing_requirement": {
                "status": "not_applicable",
                "reason": "经项目负责人确认该物资不依赖设计图定位",
                "approval_receipt": {
                    "receipt_id": "APR-DRAWING-NA-1",
                    "status": "approved",
                    "project_id": project_id,
                    "summary": "批准图纸定位不适用",
                    "approved_by": "项目负责人",
                    "approved_at": "2026-08-28T10:00:00+08:00",
                },
            },
            "drawing_validation": {"ok": True, "reason": "not_applicable"},
            "closure": {"ok": True},
        }
    )
    return {
        "drawing_index": {
            "ok": False,
            "project_id": project_id,
            "drawings": [],
            "indexed_drawing_count": 0,
            "integrity_rejection_count": 0,
            "invalid_identity_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "text_index_status": "no_drawings",
        },
        "standard_index": {
            "ok": False,
            "project_id": project_id,
            "standards": [],
            "indexed_standard_count": 0,
            "integrity_rejection_count": 0,
            "invalid_identity_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "text_index_status": "no_standards",
        },
        "cross_index": cross_index,
    }


def test_formal_indexes_allow_approved_not_applicable_focus_without_rows() -> None:
    indexes = _approved_not_applicable_empty_indexes()
    export_docx_service._validate_export_indexes(
        indexes,
        boq_focus={"must_cover_keywords": ["氧气瓶"]},
    )
    export_docx_service._validate_formal_export_indexes(
        indexes,
        project_id="P-NA",
    )


def test_formal_indexes_require_complete_rows_when_any_focus_is_required() -> None:
    indexes = _approved_not_applicable_empty_indexes()
    row = indexes["cross_index"]["focus_items"][0]
    row["drawing_requirement"] = {
        "status": "required",
        "reason": "focus_item_default",
    }

    with pytest.raises(ValueError, match="direct_export_drawing_index_incomplete"):
        export_docx_service._validate_formal_export_indexes(
            indexes,
            project_id="P-NA",
        )


def test_formal_indexes_require_standard_rows_when_cross_index_claims_a_locator() -> None:
    indexes = _approved_not_applicable_empty_indexes()
    indexes["cross_index"]["focus_items"][0]["standard_locator"] = (
        f"项目标准.pdf#p1_{'a' * 64}@18"
    )

    with pytest.raises(ValueError, match="direct_export_standard_index_incomplete"):
        export_docx_service._validate_formal_export_indexes(
            indexes,
            project_id="P-NA",
        )


def test_direct_export_binding_detects_current_index_tampering() -> None:
    sections = [{"title": "工程概况", "content": "已复核内容"}]
    raw_request = {
        **_formal_source_fields("P-BIND", sections=sections),
        "sections": sections,
    }
    gate = _passing_complete_delivery_gate()
    indexes = _valid_indexes(project_id="P-BIND")
    quality = _passing_direct_quality()
    quality["delivery_quality_gate"] = gate
    payload = {
        "project_id": "P-BIND",
        "source_input_receipt": copy.deepcopy(
            raw_request["source_input_receipt"]
        ),
        "sections": copy.deepcopy(sections),
        "plan_consistency": {"ok": True},
        "quality_checks": quality,
        **indexes,
        "delivery_quality_gate": gate,
        "requirement_evidence_matrix": {
            "matrix_digest": _empty_requirement_plan()["matrix_digest"]
        },
    }
    export_docx_service._attach_direct_export_binding(
        payload,
        raw_request=raw_request,
    )
    export_docx_service._validate_direct_export_receipts(
        payload,
        raw_request=raw_request,
    )

    payload["drawing_index"]["audit_path"] = "/tmp/tampered-audit.jsonl"
    with pytest.raises(ValueError, match="direct_export_binding_receipt_invalid"):
        export_docx_service._validate_direct_export_receipts(
            payload,
            raw_request=raw_request,
        )


def test_build_export_docx_payload_keeps_image_selection_pack_media_when_generate_images_disabled():
    payload = export_docx_service.build_export_docx_payload(
        raw_request={
            "topic": "图片库导出",
            "sections": [{"title": "施工总平面", "content": "文本"}],
            "generate_images": False,
            "image_selection_pack": {
                "images": [
                    {"source_path": "/tmp/site-plan.png", "caption": "现场平面示意"},
                    {"source_path": "/tmp/site-plan.png", "caption": "重复路径应去重"},
                ]
            },
        },
        workspace_dir="/tmp/ws-export",
        load_tender_matrix_fn=lambda **kwargs: {},
        load_boq_data_fn=lambda **kwargs: {},
        build_boq_focus_fn=lambda boq: {},
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            project_id="P-EVIDENCE"
        ),
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [], "summary": {}},
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/ignored.png", "caption": "不应出现"}],
    )

    assert payload["media"] == [
        {
            "path": "/tmp/site-plan.png",
            "caption": "现场平面示意",
            "image_id": None,
            "chapter_scope": [],
            "semantic_terms": [],
            "source_kind": "library_image",
            "source_sha256": None,
            "source_filename": None,
            "source_page": None,
            "is_project_source": False,
            "required": False,
            "explicit_selection": True,
        }
    ]


def test_build_export_docx_payload_merges_preselected_media_and_generated_media():
    payload = export_docx_service.build_export_docx_payload(
        raw_request={
            "topic": "图片库导出",
            "sections": [{"title": "施工总平面", "content": "文本"}],
            "generate_images": True,
            "media": [{"path": "/tmp/preselected.png", "caption": "预选图片"}],
            "image_selection_pack": {
                "images": [
                    {"source_path": "/tmp/site-plan.png", "caption": "现场平面示意"},
                ]
            },
        },
        workspace_dir="/tmp/ws-export",
        load_tender_matrix_fn=lambda **kwargs: {},
        load_boq_data_fn=lambda **kwargs: {},
        build_boq_focus_fn=lambda boq: {},
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(),
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [], "summary": {}},
        build_export_media_fn=lambda **kwargs: [
            {"path": "/tmp/generated.png", "caption": "生成图"},
            {"path": "/tmp/site-plan.png", "caption": "重复路径应去重"},
        ],
    )

    assert payload["media"] == [
        {"path": "/tmp/preselected.png", "caption": "预选图片"},
        {
            "path": "/tmp/site-plan.png",
            "caption": "现场平面示意",
            "image_id": None,
            "chapter_scope": [],
            "semantic_terms": [],
            "source_kind": "library_image",
            "source_sha256": None,
            "source_filename": None,
            "source_page": None,
            "is_project_source": False,
            "required": False,
            "explicit_selection": True,
        },
        {"path": "/tmp/generated.png", "caption": "生成图"},
    ]


def test_execute_export_docx_request_falls_back_to_empty_evidence_tracking(
    passing_formal_delivery_gate,
):
    seen: dict[str, object] = {}

    payload = export_docx_service.build_export_docx_payload(
        raw_request={
            "topic": "导出测试",
            "sections": [{"title": "工程概况", "content": "文本"}],
            "generate_images": False,
        },
        workspace_dir="/tmp/ws-export",
        load_tender_matrix_fn=lambda **kwargs: {},
        load_boq_data_fn=lambda **kwargs: {},
        build_boq_focus_fn=lambda boq: {},
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            project_id="P-EVIDENCE"
        ),
        build_evidence_tracking_fn=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/ignored.png"}],
    )

    assert payload["evidence_tracking"] == {"rows": [], "summary": {}}
    assert "media" not in payload

    export_docx_service.execute_export_docx_request(
        raw_request={
            "topic": "导出测试",
            **_formal_source_fields("P-EVIDENCE"),
            "sections": [{"title": "工程概况", "content": "文本"}],
            "generate_images": False,
        },
        workspace_dir="/tmp/ws-export",
        save_outputs_fn=lambda base_name, results, **kwargs: (
            seen.__setitem__("payload", results[0]) or {"json": "/tmp/out.json"}
        ),
        load_tender_matrix_fn=lambda **kwargs: {},
        load_boq_data_fn=lambda **kwargs: {},
        build_boq_focus_fn=lambda boq: {},
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: {"ok": True},
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: _passing_direct_quality(80),
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            project_id="P-EVIDENCE"
        ),
        build_evidence_tracking_fn=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/ignored.png"}],
        create_job_fn=lambda *args, **kwargs: "job-export-2",
        update_job_fn=lambda *args, **kwargs: None,
    )

    assert seen["payload"]["evidence_tracking"] == {"rows": [], "summary": {}}
    assert "media" not in seen["payload"]


def test_collect_export_docx_context_returns_preassembled_context():
    context = export_docx_service.collect_export_docx_context(
        raw_request={
            "topic": "上下文测试",
            "project_id": "P-CTX",
            "sections": [{"title": "工程概况", "content": "原始文本"}],
        },
        workspace_dir="/tmp/ws-context",
        load_tender_matrix_fn=lambda **kwargs: {"project_name": "项目CTX", "project_code": "CTX-01"},
        load_boq_data_fn=lambda **kwargs: {"stats": {"items": 2}},
        build_boq_focus_fn=lambda boq: {"focus": 2},
        load_params_fn=lambda: {"runtime": True},
        strip_nonconcrete_language_fn=lambda text: f"norm:{text}",
        normalize_metrics_in_sections_fn=lambda sections: {"normalized": len(sections)},
        recommend_four_new_fn=lambda *args, **kwargs: ["新技术A"],
        run_quality_checks_fn=lambda tender, outline, sections, **kwargs: {"score": 91, "outline": outline},
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            drawing_index={"rows": 1}
        ),
    )

    assert context == {
        "project_id": "P-CTX",
        "tender": {"project_name": "项目CTX", "project_code": "CTX-01"},
        "boq": {"stats": {"items": 2}},
        "boq_focus": {"focus": 2, "four_new_recommendations": ["新技术A"]},
        "params": {"runtime": True},
        "sections": [{"title": "工程概况", "content": "norm:原始文本"}],
        "plan_consistency": {"normalized": 1},
        "outline": ["工程概况"],
        "quality_checks": {"score": 91, "outline": ["工程概况"]},
        "indexes": _valid_indexes(drawing_index={"rows": 1}),
    }


def test_collect_export_docx_inputs_normalizes_sections_and_outline():
    out = export_docx_service.collect_export_docx_inputs(
        raw_request={
            "project_id": "P-IN",
            "sections": [{"title": "工程概况", "content": "原始文本"}],
        },
        workspace_dir="/tmp/ws-inputs",
        load_tender_matrix_fn=lambda **kwargs: {"project_name": "项目IN"},
        load_boq_data_fn=lambda **kwargs: {"stats": {"items": 1}},
        build_boq_focus_fn=lambda boq: {"focus": "ok"},
        load_params_fn=lambda: {"runtime": True},
        strip_nonconcrete_language_fn=lambda text: f"norm:{text}",
        normalize_metrics_in_sections_fn=lambda sections: {"normalized": len(sections)},
    )

    assert out == {
        "project_id": "P-IN",
        "tender": {"project_name": "项目IN"},
        "boq": {"stats": {"items": 1}},
        "boq_focus": {"focus": "ok"},
        "params": {"runtime": True},
        "sections": [{"title": "工程概况", "content": "norm:原始文本"}],
        "plan_consistency": {"normalized": 1},
        "outline": ["工程概况"],
    }


def test_collect_export_docx_inputs_rebuilds_focus_drawing_binding(monkeypatch):
    sha256 = "b" * 64
    drawing_text = "钢梁安装构件位置与连接做法。"
    locator = f"钢梁图.pdf#p1_{sha256}@0"
    hit = {
        "filename": "钢梁图.pdf",
        "sha256": sha256,
        "page": 1,
        "offset": 0,
        "locator": locator,
        "snippet": drawing_text,
        "matched_token": "钢梁安装",
        "matched_text": "钢梁安装",
        "match_start": 0,
        "match_end": 4,
        "match_window": {
            "start_offset": 0,
            "end_offset": len(drawing_text),
            "text": drawing_text,
            "text_sha256": hashlib.sha256(drawing_text.encode()).hexdigest(),
            "summary": drawing_text,
        },
        "page_text_sha256": hashlib.sha256(drawing_text.encode()).hexdigest(),
        "page_summary": drawing_text,
        "page_boundary_status": "reliable_declared_single_page",
    }
    monkeypatch.setattr(
        evidence,
        "list_ingested_filenames_by_tag",
        lambda tag, **_kwargs: ["钢梁图.pdf"] if tag == "drawing" else [],
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_drawing_hit",
        lambda *_args, **_kwargs: dict(hit),
    )
    monkeypatch.setattr(
        "backend.zhifei_autoplan.boq_focus_enforcer.best_ingested_hit",
        lambda *_args, **_kwargs: None,
    )

    seen_indexes: dict[str, object] = {}

    def _build_indexes(**kwargs):
        seen_indexes.update(kwargs)
        return _closed_indexes("钢梁", locator=locator)

    out = export_docx_service.collect_export_docx_context(
        raw_request={
            "topic": "导出 binding 回归",
            "project_id": "p1",
            "sections": [{"title": "钢结构施工工艺", "content": "钢梁施工内容。"}],
        },
        workspace_dir="/tmp/ws-binding",
        load_tender_matrix_fn=lambda **_kwargs: {},
        load_boq_data_fn=lambda **_kwargs: {
            "items": [{"name": "钢梁", "process": {"name": "钢梁安装"}}],
            "stats": {},
        },
        build_boq_focus_fn=lambda _boq: {
            "must_cover_keywords": ["钢梁"],
            "lines": [],
        },
        load_params_fn=dict,
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda _sections: None,
        recommend_four_new_fn=lambda *_args, **_kwargs: [],
        run_quality_checks_fn=lambda *_args, **_kwargs: {},
        build_export_indexes_fn=_build_indexes,
    )

    binding = out["boq_focus"]["drawing_bindings"][0]
    assert binding["locator"] == locator
    assert binding["source_relation"]["focus_item"] == "钢梁"
    assert binding["source_relation"]["chapter"] == "钢结构施工工艺"
    assert locator in out["sections"][0]["content"]
    assert seen_indexes["boq_focus"] is out["boq_focus"]
    assert seen_indexes["boq_focus"]["drawing_bindings"][0]["locator"] == locator


def test_compute_export_docx_analysis_adds_recommendations_quality_and_indexes():
    out = export_docx_service.compute_export_docx_analysis(
        raw_request={"topic": "分析测试"},
        workspace_dir="/tmp/ws-analysis",
        project_id="P-AN",
        tender={"project_name": "项目AN"},
        boq={"stats": {"items": 2}},
        boq_focus={"focus": "ok"},
        sections=[{"title": "工程概况", "content": "文本"}],
        outline=["工程概况"],
        recommend_four_new_fn=lambda *args, **kwargs: ["新技术B"],
        run_quality_checks_fn=lambda tender, outline, sections, **kwargs: {
            "score": 89,
            "project_id": kwargs["project_id"],
            "strict": kwargs["strict"],
        },
        build_export_indexes_fn=lambda **kwargs: _valid_indexes(
            drawing_index={"rows": 2},
            standard_index={"rows": 1},
        ),
    )

    assert out == {
        "boq_focus": {"focus": "ok", "four_new_recommendations": ["新技术B"]},
        "quality_checks": {"score": 89, "project_id": "P-AN", "strict": True},
        "indexes": _valid_indexes(
            drawing_index={"rows": 2},
            standard_index={"rows": 1},
        ),
    }


def test_assemble_export_docx_payload_uses_context_and_adds_media():
    payload = export_docx_service.assemble_export_docx_payload(
        raw_request={
            "topic": "装配测试",
            "style": {"font": "Song"},
            "bidder_company": "ACME",
            "generate_images": True,
        },
        workspace_dir="/tmp/ws-context",
        context={
            "project_id": "P-CTX",
            "tender": {"project_name": "项目CTX", "project_code": "CTX-01"},
            "boq": {"stats": {"items": 2}},
            "boq_focus": {"focus": 2},
            "params": {"runtime": True},
            "sections": [{"title": "工程概况", "content": "norm:原始文本"}],
            "plan_consistency": {"normalized": 1},
            "outline": ["工程概况"],
            "quality_checks": {"score": 91},
            "indexes": {"drawing_index": {"rows": 1}, "standard_index": None, "cross_index": None},
        },
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [{"title": "工程概况"}], "summary": {"count": 1}},
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/media.png", "caption": "媒体"}],
    )

    assert payload == {
        "topic": "装配测试",
        "project_id": "P-CTX",
        "project_name": "项目CTX",
        "project_code": "CTX-01",
        "style": {"font": "Song"},
        "outline": ["工程概况"],
        "sections": [{"title": "工程概况", "content": "norm:原始文本"}],
        "quality_checks": {"score": 91},
        "boq_focus": {"focus": 2},
        "drawing_index": {"rows": 1},
        "standard_index": None,
        "cross_index": None,
        "plan_consistency": {"normalized": 1},
        "branding": {
            "project_id": "P-CTX",
            "bidder_company": "ACME",
            "bidder_domain": None,
            "logo_url": None,
        },
        "evidence_tracking": {"rows": [{"title": "工程概况"}], "summary": {"count": 1}},
        "media": [{"path": "/tmp/media.png", "caption": "媒体"}],
    }


def test_build_export_docx_base_payload_and_branding():
    base = export_docx_service.build_export_docx_base_payload(
        raw_request={"topic": "基础装配", "style": {"font": "Song"}},
        project_id="P-B",
        tender={"project_name": "项目B", "project_code": "CODE-B"},
        sections=[{"title": "工程概况", "content": "文本"}],
        outline=["工程概况"],
        quality_checks={"score": 90},
        boq_focus={"focus": 1},
        indexes={"drawing_index": {"rows": 1}, "standard_index": None, "cross_index": {"rows": 2}},
        plan_consistency={"normalized": 1},
    )
    branding = export_docx_service.build_export_docx_branding(
        raw_request={"bidder_company": "ACME", "bidder_domain": "acme.test", "logo_url": "https://example.com/logo.png"},
        project_id="P-B",
    )

    assert base == {
        "topic": "基础装配",
        "project_id": "P-B",
        "project_name": "项目B",
        "project_code": "CODE-B",
        "style": {"font": "Song"},
        "outline": ["工程概况"],
        "sections": [{"title": "工程概况", "content": "文本"}],
        "quality_checks": {"score": 90},
        "boq_focus": {"focus": 1},
        "drawing_index": {"rows": 1},
        "standard_index": None,
        "cross_index": {"rows": 2},
        "plan_consistency": {"normalized": 1},
    }
    assert branding == {
        "project_id": "P-B",
        "bidder_company": "ACME",
        "bidder_domain": "acme.test",
        "logo_url": "https://example.com/logo.png",
    }


def test_build_export_docx_evidence_and_media_attachment_have_safe_fallbacks():
    evidence = export_docx_service.build_export_docx_evidence(
        sections=[{"title": "工程概况", "content": "文本"}],
        tender={"project_name": "项目C"},
        build_evidence_tracking_fn=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    media = export_docx_service.build_export_docx_media_attachment(
        raw_request={"generate_images": False},
        project_id="P-C",
        boq={"stats": {"items": 1}},
        params={"runtime": True},
        outline=["工程概况"],
        workspace_dir="/tmp/ws-c",
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/should-not-exist.png"}],
    )

    assert evidence == {"rows": [], "summary": {}}
    assert media == []


def test_build_export_media_keeps_logo_in_branding_and_allows_explicit_outline_image():
    branding_calls: list[dict] = []
    mindmap_calls: list[dict] = []

    out = export_docx_service.build_export_media(
        raw_request={
            "topic": "媒体测试",
            "include_outline_mindmap": True,
            "bidder_company": "ACME",
            "bidder_domain": "acme.test",
            "logo_url": "https://example.com/logo.png",
        },
        project_id="P-9",
        boq={"stats": {"items": 3}},
        params={"image_defaults": True},
        outline=["施工部署"],
        workspace_dir="/tmp/ws-media",
        generate_boq_chart_fn=lambda stats: [{"path": "/tmp/chart.png", "caption": "统计图"}],
        generate_ingested_previews_fn=lambda **kwargs: [{"path": "/tmp/preview.png", "caption": "预览"}],
        get_image_defaults_fn=lambda params: {"aspect_ratio": "4:3"},
        iterate_image_failover_slots_fn=lambda: [
            SimpleNamespace(provider="openai", api_key="skip", model="m0"),
            SimpleNamespace(provider="google", api_key="g-key", model="g-model"),
        ],
        generate_outline_mindmap_fn=lambda topic, outline, **kwargs: mindmap_calls.append(
            {"topic": topic, "outline": outline, "kwargs": kwargs}
        )
        or {"path": "/tmp/mindmap.png", "caption": "脑图"},
        resolve_logo_fn=lambda **kwargs: "/tmp/logo-raw.png",
        prepare_logo_for_embedding_fn=lambda raw: "/tmp/logo-embed.png",
        update_branding_fn=lambda project_id, payload, **kwargs: branding_calls.append(
            {"project_id": project_id, "payload": payload, "kwargs": kwargs}
        ),
    )

    assert out == [
        {"path": "/tmp/chart.png", "caption": "统计图"},
        {"path": "/tmp/preview.png", "caption": "预览"},
        {"path": "/tmp/mindmap.png", "caption": "脑图"},
    ]
    assert branding_calls == [
        {
            "project_id": "P-9",
            "payload": {
                "bidder_company": "ACME",
                "bidder_domain": "acme.test",
                "logo_url": "https://example.com/logo.png",
                "logo_raw_path": "/tmp/logo-raw.png",
                "logo_embed_path": "/tmp/logo-embed.png",
                "logo_path": "/tmp/logo-embed.png",
            },
            "kwargs": {"merge": True, "workspace_dir": "/tmp/ws-media"},
        }
    ]
    assert mindmap_calls == [
        {
            "topic": "媒体测试",
            "outline": ["施工部署"],
            "kwargs": {
                "provider": "openai",
                "api_key": "skip",
                "model": "m0",
                "aspect_ratio": "4:3",
                "logo_path": "/tmp/logo-embed.png",
                "bidder_company": "ACME",
                "logo_url": "https://example.com/logo.png",
                "bidder_domain": "acme.test",
                "fallback_to_deterministic": False,
                "workspace_dir": "/tmp/ws-media",
            },
        }
    ]


def test_build_export_media_accepts_current_media_and_branding_signatures():
    branding_calls: list[dict] = []
    mindmap_calls: list[dict] = []

    def _generate_ingested_previews(limit=6, project_id=None):
        return [{"path": f"/tmp/preview-{project_id}-{limit}.png", "caption": "预览"}]

    def _resolve_logo(*, bidder_company=None, logo_url=None, bidder_domain=None, project_id=None):
        return f"/tmp/logo-{project_id}.png"

    def _update_branding(project_id, payload, merge=True):
        branding_calls.append({"project_id": project_id, "payload": payload, "merge": merge})

    def _generate_outline_mindmap(
        topic,
        outline,
        *,
        provider=None,
        api_key=None,
        model=None,
        aspect_ratio=None,
        logo_path=None,
        bidder_company=None,
        logo_url=None,
        bidder_domain=None,
    ):
        mindmap_calls.append({"topic": topic, "outline": outline, "logo_path": logo_path})
        return {"path": "/tmp/current-mindmap.png", "caption": "脑图"}

    out = export_docx_service.build_export_media(
        raw_request={
            "topic": "当前媒体签名",
            "bidder_company": "ACME",
            "bidder_domain": "acme.test",
            "logo_url": "https://example.com/logo.png",
        },
        project_id="P-CURRENT",
        boq={"stats": {"items": 1}},
        params={},
        outline=["施工部署"],
        workspace_dir="/tmp/ws-media-current",
        generate_boq_chart_fn=lambda stats: [{"path": "/tmp/current-chart.png", "caption": "统计图"}],
        generate_ingested_previews_fn=_generate_ingested_previews,
        get_image_defaults_fn=lambda params: {"aspect_ratio": "16:9"},
        iterate_image_failover_slots_fn=lambda: [SimpleNamespace(provider="google", api_key="g-key", model="g-model")],
        generate_outline_mindmap_fn=_generate_outline_mindmap,
        resolve_logo_fn=_resolve_logo,
        prepare_logo_for_embedding_fn=lambda raw: "/tmp/current-logo-embed.png",
        update_branding_fn=_update_branding,
    )

    assert out == [
        {"path": "/tmp/current-chart.png", "caption": "统计图"},
        {"path": "/tmp/preview-P-CURRENT-6.png", "caption": "预览"},
    ]
    assert branding_calls == [
        {
            "project_id": "P-CURRENT",
            "payload": {
                "bidder_company": "ACME",
                "bidder_domain": "acme.test",
                "logo_url": "https://example.com/logo.png",
                "logo_raw_path": "/tmp/logo-P-CURRENT.png",
                "logo_embed_path": "/tmp/current-logo-embed.png",
                "logo_path": "/tmp/current-logo-embed.png",
            },
            "merge": True,
        }
    ]
    assert mindmap_calls == []


def test_build_export_mindmap_media_returns_none_when_supported_slot_missing():
    out = export_docx_service.build_export_mindmap_media(
        raw_request={"topic": "媒体测试"},
        outline=["工程概况"],
        workspace_dir="/tmp/ws-media",
        aspect_ratio="16:9",
        logo_embed=None,
        iterate_image_failover_slots_fn=lambda: [SimpleNamespace(provider="unsupported", api_key="o-key", model="o-model")],
        generate_outline_mindmap_fn=lambda *args, **kwargs: {"path": "/tmp/should-not-run.png"},
    )

    assert out is None
