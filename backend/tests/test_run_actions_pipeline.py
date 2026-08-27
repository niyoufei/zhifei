from __future__ import annotations

import sys

import pytest

from scripts import run_actions_pipeline


def _run_main(
    monkeypatch: pytest.MonkeyPatch,
    *,
    status: str,
    generate_images: bool,
    dry_run: bool = False,
    download: bool = False,
    resume_from_job_id: str = "",
) -> tuple[int, dict]:
    generation_payload: dict = {}

    def _post_json(base, path, actions_key, payload, **kwargs):
        assert path == "/actions/generate_async"
        generation_payload.update(payload)
        return {"job_id": "job-1"}

    def _get_json(base, path, actions_key, params=None, **kwargs):
        if path == "/actions/job_status":
            return {"job": {"status": status}}
        if path == "/actions/result":
            return {
                "quality_checks": {},
                "delivery_scope": "document",
                "delivery_ready": not dry_run,
            }
        raise AssertionError(f"unexpected path: {path}")

    argv = [
        "run_actions_pipeline.py",
        "--topic",
        "合成验收项目",
        "--actions-key",
        "local-actions-key",
        "--no-gate",
        "--timeout-sec",
        "1",
        "--poll-sec",
        "0",
    ]
    if not download:
        argv.append("--no-download")
    if dry_run:
        argv.append("--dry-run")
    if generate_images:
        argv.append("--generate-images")
    if resume_from_job_id:
        argv.extend(["--resume-from-job-id", resume_from_job_id])

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


def test_main_sends_explicit_resume_job_id(monkeypatch):
    result, payload = _run_main(
        monkeypatch,
        status="succeeded",
        generate_images=False,
        resume_from_job_id="a" * 32,
    )

    assert result == 0
    assert payload["resume_from_job_id"] == "a" * 32


def test_dry_run_downloads_json_only(monkeypatch):
    downloads: list[str] = []
    monkeypatch.setattr(
        run_actions_pipeline,
        "_download",
        lambda _base, _key, _job, kind, _variant, _path: downloads.append(kind),
    )

    result, payload = _run_main(
        monkeypatch,
        status="succeeded",
        generate_images=False,
        dry_run=True,
        download=True,
    )

    assert result == 0
    assert payload["dry_run"] is True
    assert downloads == ["json"]


@pytest.mark.parametrize("status", ["failed", "cancelled", "interrupted_recoverable"])
def test_main_stops_on_unsuccessful_terminal_status(monkeypatch, status):
    result, _ = _run_main(
        monkeypatch,
        status=status,
        generate_images=False,
    )

    assert result == 3
