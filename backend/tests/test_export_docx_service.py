from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.tests.export_test_contract_fixtures import (
    isolated_test_module_bindings,
)


_EXPORT_DOCX_SERVICE_RUNTIME_BINDINGS = {
    "export_docx_service": (
        "backend.zhifei_autoplan.export_docx_service",
        None,
    ),
}


@pytest.fixture(scope="module", autouse=True)
def _isolate_export_docx_service_runtime_modules():
    with isolated_test_module_bindings(
        globals(),
        _EXPORT_DOCX_SERVICE_RUNTIME_BINDINGS,
    ):
        yield


def test_execute_export_docx_request_builds_payload_and_updates_job():
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
        normalize_metrics_in_sections_fn=lambda sections: {"normalized": True, "count": len(sections)},
        recommend_four_new_fn=lambda *args, **kwargs: ["四新工艺"],
        run_quality_checks_fn=lambda tender, outline, sections, **kwargs: {
            "score": 96,
            "strict": kwargs["strict"],
            "outline": outline,
            "sections": sections,
        },
        build_export_indexes_fn=lambda **kwargs: {
            "drawing_index": {"rows": 1},
            "standard_index": {"rows": 2},
            "cross_index": {"rows": 3},
        },
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
    assert payload["cross_index"] == {"rows": 3}
    assert payload["plan_consistency"] == {"normalized": True, "count": 1}
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
            "project_id": "P-1",
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
        normalize_metrics_in_sections_fn=lambda sections: {"normalized": True, "count": len(sections)},
        recommend_four_new_fn=lambda *args, **kwargs: ["四新工艺"],
        run_quality_checks_fn=lambda tender, outline, sections, **kwargs: {
            "score": 96,
            "strict": kwargs["strict"],
            "outline": outline,
            "sections": sections,
        },
        build_export_indexes_fn=lambda **kwargs: {
            "drawing_index": {"rows": 1},
            "standard_index": {"rows": 2},
            "cross_index": {"rows": 3},
        },
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

    assert seen["results"][0] == payload


def test_execute_export_docx_request_accepts_current_store_signatures():
    seen: dict[str, object] = {}

    def _load_tender_matrix(*, project_id=None):
        seen["tender_project_id"] = project_id
        return {"project_name": "当前项目", "project_code": "CUR-01"}

    def _load_boq_data(*, project_id=None):
        seen["boq_project_id"] = project_id
        return {"stats": {"items": 1}}

    def _run_quality_checks(tender, outline, sections, *, boq, boq_focus, project_id, strict):
        seen["quality_project_id"] = project_id
        return {"score": 90, "strict": strict}

    def _build_export_indexes(*, topic, outline, project_id, boq, sections, boq_focus, quality_checks):
        seen["index_project_id"] = project_id
        return {"drawing_index": None, "standard_index": None, "cross_index": None}

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
            "project_id": "P-CURRENT",
            "sections": [{"title": "工程概况", "content": "文本"}],
            "generate_images": False,
        },
        workspace_dir="/tmp/ws-current",
        save_outputs_fn=_save_outputs,
        load_tender_matrix_fn=_load_tender_matrix,
        load_boq_data_fn=_load_boq_data,
        build_boq_focus_fn=lambda boq: {"focus": "ok"},
        load_params_fn=lambda: {},
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
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
        load_params_fn=lambda: {},
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: {},
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [], "summary": {}},
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/ignored.png", "caption": "不应出现"}],
    )

    assert payload["media"] == [{"path": "/tmp/site-plan.png", "caption": "现场平面示意"}]


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
        load_params_fn=lambda: {},
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: {},
        build_evidence_tracking_fn=lambda **kwargs: {"rows": [], "summary": {}},
        build_export_media_fn=lambda **kwargs: [
            {"path": "/tmp/generated.png", "caption": "生成图"},
            {"path": "/tmp/site-plan.png", "caption": "重复路径应去重"},
        ],
    )

    assert payload["media"] == [
        {"path": "/tmp/preselected.png", "caption": "预选图片"},
        {"path": "/tmp/site-plan.png", "caption": "现场平面示意"},
        {"path": "/tmp/generated.png", "caption": "生成图"},
    ]


def test_execute_export_docx_request_falls_back_to_empty_evidence_tracking():
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
        load_params_fn=lambda: {},
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: {},
        build_evidence_tracking_fn=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
        build_export_media_fn=lambda **kwargs: [{"path": "/tmp/ignored.png"}],
    )

    assert payload["evidence_tracking"] == {"rows": [], "summary": {}}
    assert "media" not in payload

    export_docx_service.execute_export_docx_request(
        raw_request={
            "topic": "导出测试",
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
        load_params_fn=lambda: {},
        strip_nonconcrete_language_fn=lambda text: text,
        normalize_metrics_in_sections_fn=lambda sections: None,
        recommend_four_new_fn=lambda *args, **kwargs: [],
        run_quality_checks_fn=lambda *args, **kwargs: {"score": 80},
        build_export_indexes_fn=lambda **kwargs: {},
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
        build_export_indexes_fn=lambda **kwargs: {"drawing_index": {"rows": 1}, "standard_index": None, "cross_index": None},
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
        "indexes": {"drawing_index": {"rows": 1}, "standard_index": None, "cross_index": None},
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
        build_export_indexes_fn=lambda **kwargs: {"drawing_index": {"rows": 2}, "standard_index": {"rows": 1}, "cross_index": None},
    )

    assert out == {
        "boq_focus": {"focus": "ok", "four_new_recommendations": ["新技术B"]},
        "quality_checks": {"score": 89, "project_id": "P-AN", "strict": True},
        "indexes": {"drawing_index": {"rows": 2}, "standard_index": {"rows": 1}, "cross_index": None},
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


def test_build_export_media_includes_logo_and_google_mindmap():
    branding_calls: list[dict] = []
    mindmap_calls: list[dict] = []

    out = export_docx_service.build_export_media(
        raw_request={
            "topic": "媒体测试",
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
        {"path": "/tmp/logo-embed.png", "caption": "投标单位LOGO"},
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
                "api_key": "g-key",
                "model": "g-model",
                "aspect_ratio": "4:3",
                "logo_path": "/tmp/logo-embed.png",
                "bidder_company": "ACME",
                "logo_url": "https://example.com/logo.png",
                "bidder_domain": "acme.test",
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
        {"path": "/tmp/current-logo-embed.png", "caption": "投标单位LOGO"},
        {"path": "/tmp/current-mindmap.png", "caption": "脑图"},
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
    assert mindmap_calls == [
        {
            "topic": "当前媒体签名",
            "outline": ["施工部署"],
            "logo_path": "/tmp/current-logo-embed.png",
        }
    ]


def test_build_export_mindmap_media_returns_none_when_google_slot_missing():
    out = export_docx_service.build_export_mindmap_media(
        raw_request={"topic": "媒体测试"},
        outline=["工程概况"],
        workspace_dir="/tmp/ws-media",
        aspect_ratio="16:9",
        logo_embed=None,
        iterate_image_failover_slots_fn=lambda: [SimpleNamespace(provider="openai", api_key="o-key", model="o-model")],
        generate_outline_mindmap_fn=lambda *args, **kwargs: {"path": "/tmp/should-not-run.png"},
    )

    assert out is None
