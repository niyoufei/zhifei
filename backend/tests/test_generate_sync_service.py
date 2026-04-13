from __future__ import annotations

from backend.zhifei_autoplan import generate_sync_service


async def test_run_generate_sync_builds_variant_payloads_sequentially():
    seen_payloads: list[dict] = []

    async def _run_autoplan(payload: dict) -> dict:
        seen_payloads.append(payload)
        return {"variant_id": payload["variant_id"], "quality_checks": {"score": 90 + payload["variant_id"]}}

    payload, results = await generate_sync_service.run_generate_sync(
        raw_payload={"topic": "t-1"},
        prepare_runtime_payload_fn=lambda raw: {**raw, "prepared": True},
        build_variant_plan_fn=lambda payload: [
            {"variant_id": 1, "logic_template_id": "A"},
            {"variant_id": 2, "logic_template_id": "B"},
        ],
        normalize_logic_template_id_fn=lambda raw: str(raw or "").strip() or None,
        run_autoplan_fn=_run_autoplan,
    )

    assert payload["_variant_ids"] == [1, 2]
    assert payload["_variant_plan"] == [
        {"variant_id": 1, "logic_template_id": "A"},
        {"variant_id": 2, "logic_template_id": "B"},
    ]
    assert [item["variant_id"] for item in seen_payloads] == [1, 2]
    assert seen_payloads[0]["logic_template_id"] == "A"
    assert seen_payloads[1]["logic_template_id"] == "B"
    assert results == [
        {"variant_id": 1, "quality_checks": {"score": 91}},
        {"variant_id": 2, "quality_checks": {"score": 92}},
    ]


async def test_execute_generate_sync_request_postprocesses_and_saves_outputs():
    postprocess_calls: list[dict] = []
    save_calls: list[dict] = []

    async def _run_autoplan(payload: dict) -> dict:
        return {"variant_id": payload["variant_id"], "quality_checks": {"score": 80 + payload["variant_id"]}}

    out = await generate_sync_service.execute_generate_sync_request(
        raw_payload={"topic": "t-2"},
        prepare_runtime_payload_fn=lambda raw: {**raw, "prepared": True},
        build_variant_plan_fn=lambda payload: [
            {"variant_id": 1, "logic_template_id": "A"},
            {"variant_id": 2, "logic_template_id": "B"},
        ],
        normalize_logic_template_id_fn=lambda raw: str(raw or "").strip() or None,
        run_autoplan_fn=_run_autoplan,
        load_params_fn=lambda: {"variant_diversity": {"auto_fix_rounds": 0}},
        rebuild_postprocessed_fn=lambda *args, **kwargs: None,
        workspace_dir_from_payload_fn=lambda payload: "/tmp/ws-sync",
        save_outputs_fn=lambda base_name, results, **kwargs: save_calls.append(
            {"base_name": base_name, "results": results, "kwargs": kwargs}
        )
        or {"json": "/tmp/actions_generated.json"},
        compute_variant_similarity_fn=lambda *args, **kwargs: postprocess_calls.append({"args": args, "kwargs": kwargs})
        or {"ok": True, "flagged": []},
        apply_diversity_autofix_fn=lambda *args, **kwargs: False,
    )

    assert postprocess_calls
    assert save_calls == [
        {
            "base_name": "actions_generated",
            "results": [
                {"variant_id": 1, "quality_checks": {"score": 81}},
                {"variant_id": 2, "quality_checks": {"score": 82}},
            ],
            "kwargs": {"workspace_dir": "/tmp/ws-sync"},
        }
    ]
    assert out == {
        "ok": True,
        "result": [
            {"variant_id": 1, "quality_checks": {"score": 81}},
            {"variant_id": 2, "quality_checks": {"score": 82}},
        ],
        "quality": [{"score": 81}, {"score": 82}],
        "files": {"json": "/tmp/actions_generated.json"},
    }


def test_build_generate_sync_response_collects_quality_and_files():
    out = generate_sync_service.build_generate_sync_response(
        results=[
            {"variant_id": 1, "quality_checks": {"score": 95}},
            {"variant_id": 2, "quality_checks": {"score": 96}},
        ],
        outputs={"json": "/tmp/actions_generated.json"},
    )
    assert out == {
        "ok": True,
        "result": [
            {"variant_id": 1, "quality_checks": {"score": 95}},
            {"variant_id": 2, "quality_checks": {"score": 96}},
        ],
        "quality": [{"score": 95}, {"score": 96}],
        "files": {"json": "/tmp/actions_generated.json"},
    }
