from __future__ import annotations

from backend.zhifei_autoplan import runtime_payload_service


def test_merge_plan_defaults_uses_plan_and_tender_before_policy():
    payload = {"project_id": "p-1", "outline": [], "chapter_requirements": None, "style": None, "chapter_pages": None}

    out = runtime_payload_service.merge_plan_defaults(
        dict(payload),
        workspace_dir_from_payload_fn=lambda payload: "/tmp/ws",
        load_plan_fn=lambda **kwargs: {
            "outline": ["计划大纲"],
            "chapter_requirements": {"第1章": ["约束"]},
            "style": {"tone": "formal"},
            "chapter_pages": {"第1章": 2},
            "generation_mode": "stable_delivery",
        },
        load_tender_matrix_fn=lambda **kwargs: {"outline": ["招标大纲"]},
        normalize_selected_templates_fn=lambda raw: [],
        apply_generation_mode_policy_fn=lambda payload: {**payload, "_policy_applied": True},
    )

    assert out["outline"] == ["计划大纲"]
    assert out["chapter_requirements"] == {"第1章": ["约束"]}
    assert out["style"] == {"tone": "formal"}
    assert out["chapter_pages"] == {"第1章": 2}
    assert out["generation_mode"] == "stable_delivery"
    assert out["_policy_applied"] is True


def test_prepare_runtime_payload_resolves_workspace_and_sets_trace_id():
    out = runtime_payload_service.prepare_runtime_payload(
        {"topic": "t-1", "session_id": "sess-x", "workspace_dir": "/tmp/raw"},
        resolve_workspace_context_fn=lambda **kwargs: {"session_id": "sess-1", "workspace_dir": "/tmp/ws"},
        merge_plan_defaults_fn=lambda payload: {**payload, "merged": True},
        apply_server_provider_routing_fn=lambda payload: {**payload, "provider": "openai"},
        uuid_hex_fn=lambda: "uuid-1",
    )

    assert out["session_id"] == "sess-1"
    assert out["workspace_dir"] == "/tmp/ws"
    assert out["merged"] is True
    assert out["provider"] == "openai"
    assert out["request_id"] == "uuid-1"
    assert out["trace_id"] == "uuid-1"


def test_merge_plan_defaults_carries_reference_library_options():
    out = runtime_payload_service.merge_plan_defaults(
        {"project_id": "p-2", "outline": ["工程概况"], "case_library": None, "image_library": None},
        workspace_dir_from_payload_fn=lambda payload: "/tmp/ws",
        load_plan_fn=lambda **kwargs: {
            "case_library": {"enabled": True, "selected_case_ids": ["case-1"]},
            "image_library": {"enabled": True, "selected_image_ids": ["image-1"]},
        },
        load_tender_matrix_fn=lambda **kwargs: {},
        normalize_selected_templates_fn=lambda raw: [],
        apply_generation_mode_policy_fn=lambda payload: payload,
    )

    assert out["case_library"] == {"enabled": True, "selected_case_ids": ["case-1"]}
    assert out["image_library"] == {"enabled": True, "selected_image_ids": ["image-1"]}
