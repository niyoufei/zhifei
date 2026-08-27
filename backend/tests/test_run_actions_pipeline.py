from __future__ import annotations

import sys

import pytest

from scripts import run_actions_pipeline


def _run_main(monkeypatch: pytest.MonkeyPatch, *, status: str, generate_images: bool) -> tuple[int, dict]:
    generation_payload: dict = {}

    def _post_json(base, path, actions_key, payload, **kwargs):
        assert path == "/actions/generate_async"
        generation_payload.update(payload)
        return {"job_id": "job-1"}

    def _get_json(base, path, actions_key, params=None, **kwargs):
        if path == "/actions/job_status":
            return {"job": {"status": status}}
        if path == "/actions/result":
            return {"quality_checks": {}}
        raise AssertionError(f"unexpected path: {path}")

    argv = [
        "run_actions_pipeline.py",
        "--topic",
        "合成验收项目",
        "--actions-key",
        "local-actions-key",
        "--no-download",
        "--no-gate",
        "--timeout-sec",
        "1",
        "--poll-sec",
        "0",
    ]
    if generate_images:
        argv.append("--generate-images")

    monkeypatch.setattr(run_actions_pipeline, "_post_json", _post_json)
    monkeypatch.setattr(run_actions_pipeline, "_get_json", _get_json)
    monkeypatch.setattr(sys, "argv", argv)
    return run_actions_pipeline.main(), generation_payload


def test_main_accepts_succeeded_and_disables_images_by_default(monkeypatch):
    result, payload = _run_main(
        monkeypatch,
        status="succeeded",
        generate_images=False,
    )

    assert result == 0
    assert payload["generate_images"] is False


def test_main_keeps_legacy_done_and_supports_image_opt_in(monkeypatch):
    result, payload = _run_main(
        monkeypatch,
        status="done",
        generate_images=True,
    )

    assert result == 0
    assert payload["generate_images"] is True


@pytest.mark.parametrize("status", ["failed", "cancelled", "interrupted_recoverable"])
def test_main_stops_on_unsuccessful_terminal_status(monkeypatch, status):
    result, _ = _run_main(
        monkeypatch,
        status=status,
        generate_images=False,
    )

    assert result == 3
