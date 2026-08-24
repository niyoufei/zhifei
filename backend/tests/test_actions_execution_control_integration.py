from __future__ import annotations

import asyncio

import pytest

from backend.app.routers import actions_bridge


def test_prepare_execution_control_clamps_nested_parallelism_and_budgets() -> None:
    payload = {
        "variants": 3,
        "outline": ["一", "二"],
        "agent_parallelism": 16,
        "variant_parallelism": 3,
        "max_model_parallelism": 6,
        "max_model_attempts": 123,
        "max_model_input_chars": 456_000,
        "max_model_output_tokens": 7_890,
    }

    runtime, policy = actions_bridge._prepare_execution_control(payload)

    assert payload["variant_parallelism"] == 3
    assert payload["agent_parallelism"] == 2
    assert policy["max_model_parallelism"] == 6
    assert policy["max_model_attempts"] == 123
    assert policy["max_input_chars"] == 456_000
    assert policy["max_requested_output_tokens"] == 7_890
    assert runtime.snapshot()["limits"] == {
        "max_concurrency": 6,
        "max_model_attempts": 123,
        "max_input_chars": 456_000,
        "max_requested_output_tokens": 7_890,
    }


@pytest.mark.asyncio
async def test_direct_generate_shares_one_runtime_with_variants_and_renderer(monkeypatch) -> None:
    active = 0
    peak = 0
    runtimes = []
    render_runtime = None

    monkeypatch.setattr(actions_bridge, "_auth_actions_key", lambda _key: None)
    monkeypatch.setattr(
        actions_bridge,
        "_merge_plan_defaults",
        lambda payload: dict(payload),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_build_variant_plan",
        lambda _payload: [{"variant_id": 1}, {"variant_id": 2}],
    )

    async def _fake_run(payload):
        nonlocal active, peak
        runtimes.append(payload.get("_execution_runtime"))
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {
            "variant_id": payload["variant_id"],
            "sections": [],
            "quality_checks": {"ok": True},
        }

    monkeypatch.setattr(actions_bridge, "run_autoplan", _fake_run)
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        lambda _name, _results: {"docx": ["a.docx", "b.docx"], "json": ["r.json"]},
    )

    async def _fake_render(*, job_id, outputs, progress_callback=None, execution_runtime=None):
        nonlocal render_runtime
        assert job_id.startswith("direct-")
        assert progress_callback is None
        render_runtime = execution_runtime
        return dict(outputs)

    monkeypatch.setattr(actions_bridge, "_render_professional_outputs_for_job", _fake_render)

    request = actions_bridge.ActionsGenerateRequest(
        topic="测试",
        outline=["一", "二"],
        variants=2,
        variant_parallelism=2,
        max_model_parallelism=4,
    )
    response = await actions_bridge.actions_generate(request, x_actions_key="ignored")

    assert peak == 2
    assert len(runtimes) == 2
    assert runtimes[0] is runtimes[1]
    assert render_runtime is runtimes[0]
    assert response["execution_control"]["limits"]["max_concurrency"] == 4
    assert [item["variant_id"] for item in response["result"]] == [1, 2]
