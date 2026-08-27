from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.routers import actions_bridge
from backend.app.routers import ingest as ingest_router
from backend.app.routers import zhifei_autoplan as legacy_router
from backend.zhifei_autoplan import generation_checkpoint, job_store


def _configure_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(job_store, "JOB_DIR", tmp_path / "jobs")
    monkeypatch.setattr(
        generation_checkpoint,
        "CHECKPOINT_DIR",
        tmp_path / "checkpoints",
    )


def _payload(*, outline: list[str] | None = None) -> dict:
    return {
        "topic": "租约回归",
        "project_id": "lease-test",
        "outline": list(outline or ["第一章"]),
        "variants": 1,
        "_variant_plan": [{"variant_id": 1}],
        "dry_run": True,
        "delivery_scope": "chapter_validation",
        "_provider_admission_required": False,
    }


def test_reconcile_revokes_lease_and_rejects_every_late_worker_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job(_payload())
    lease = job_store.acquire_job_lease(job_id, owner_instance_id="worker-a")
    assert lease is not None
    attempt_id = str(lease["attempt_id"])
    owner_id = str(lease["owner_instance_id"])
    written: list[str] = []

    claimed_revision = lease["revision"]
    assert (
        job_store.merge_job(
            job_id,
            expected_attempt_id="0" * 32,
            expected_owner_instance_id=owner_id,
            progress={"stage": "forged-attempt"},
        )
        is None
    )
    assert (
        job_store.merge_job(
            job_id,
            expected_attempt_id=attempt_id,
            expected_owner_instance_id="forged-owner",
            progress={"stage": "forged-owner"},
        )
        is None
    )
    assert (job_store.get_job(job_id) or {})["revision"] == claimed_revision

    before = job_store.merge_job(
        job_id,
        expected_attempt_id=attempt_id,
        expected_owner_instance_id=owner_id,
        progress={"percent": 35, "heartbeat_at": 100.0},
    )
    assert before is not None
    assert job_store.reconcile_stale_jobs(now=200.0, stale_after_seconds=60) == [
        job_id
    ]
    reconciled = job_store.get_job(job_id)
    assert reconciled is not None
    reconciled_revision = reconciled["revision"]

    assert (
        job_store.heartbeat_job(
            job_id,
            activity="late-heartbeat",
            expected_attempt_id=attempt_id,
            expected_owner_instance_id=owner_id,
        )
        is None
    )
    assert (
        job_store.merge_job(
            job_id,
            expected_attempt_id=attempt_id,
            expected_owner_instance_id=owner_id,
            progress={"percent": 99, "stage": "late-progress"},
        )
        is None
    )
    assert (
        job_store.transition_job(
            job_id,
            allowed_from={"running"},
            status="succeeded",
            expected_attempt_id=attempt_id,
            expected_owner_instance_id=owner_id,
        )
        is None
    )
    with pytest.raises(job_store.JobLeaseLostError, match="job_lease_lost"):
        job_store.run_with_job_lease(
            job_id,
            attempt_id=attempt_id,
            owner_instance_id=owner_id,
            callback=lambda: written.append("late-checkpoint-or-event"),
        )

    final = job_store.get_job(job_id)
    assert final is not None
    assert final["status"] == "interrupted_recoverable"
    assert final["attempt_id"] is None
    assert final["owner_instance_id"] is None
    assert final["last_attempt_id"] == attempt_id
    assert final["revision"] == reconciled_revision
    assert final["progress"]["percent"] == 35
    assert written == []


def test_reconciled_worker_callbacks_checkpoint_and_completion_are_fenced(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    events: list[tuple[str, str, dict]] = []
    observations: dict[str, object] = {}
    job_id = job_store.create_job(_payload())

    monkeypatch.setattr(
        actions_bridge,
        "append_runtime_event",
        lambda jid, event, **fields: events.append((jid, event, fields)),
    )

    async def fake_run_autoplan(payload: dict) -> dict:
        progress = payload["_progress_callback"]
        guard = payload["_checkpoint_write_guard"]
        progress(
            {
                "event": "chapter_started",
                "chapter_index": 1,
                "chapter_title": "第一章",
                "chapters_total": 1,
            }
        )
        guard(lambda: observations.setdefault("checkpoint", "before-reconcile"))
        job_store.merge_job(
            job_id,
            progress={"heartbeat_at": 100.0},
        )
        assert job_store.reconcile_stale_jobs(
            now=200.0,
            stale_after_seconds=60,
        ) == [job_id]
        observations["event_count_after_reconcile"] = len(events)
        observations["record_after_reconcile"] = job_store.get_job(job_id)

        progress(
            {
                "event": "chapter_completed",
                "chapter_index": 1,
                "chapter_title": "第一章",
                "chapters_total": 1,
                "ok": True,
            }
        )
        with pytest.raises(job_store.JobLeaseLostError, match="job_lease_lost"):
            guard(lambda: observations.setdefault("late_checkpoint", True))
        return {"variant_id": 1, "sections": [{"title": "第一章"}]}

    monkeypatch.setattr(actions_bridge, "run_autoplan", fake_run_autoplan)
    actions_bridge.run_actions_generation_job(job_id, _payload())

    after = job_store.get_job(job_id)
    reconciled = observations["record_after_reconcile"]
    assert isinstance(reconciled, dict)
    assert after == reconciled
    assert after["status"] == "interrupted_recoverable"
    assert after["progress"]["percent"] < 100
    assert observations["checkpoint"] == "before-reconcile"
    assert "late_checkpoint" not in observations
    assert len(events) == observations["event_count_after_reconcile"]
    assert not any(
        event in {"job_succeeded", "job_failed", "job_cancelled"}
        for _, event, _ in events
    )


def test_cancel_after_one_saved_chapter_seals_recoverable_checkpoint_and_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    events: list[str] = []
    job_id = job_store.create_job(_payload(outline=["第一章", "第二章"]))
    binding = {
        "binding_digest": "a" * 64,
        "outline": ["第一章", "第二章"],
    }

    monkeypatch.setattr(
        actions_bridge,
        "append_runtime_event",
        lambda _jid, event, **_fields: events.append(event),
    )

    async def fake_run_autoplan(payload: dict) -> dict:
        progress = payload["_progress_callback"]
        guard = payload["_checkpoint_write_guard"]
        progress(
            {
                "event": "chapter_started",
                "chapter_index": 1,
                "chapter_title": "第一章",
                "chapters_total": 2,
            }
        )
        checkpoint = guard(
            generation_checkpoint.save_section_checkpoint,
            namespace=job_id,
            scope="variant-1",
            binding=binding,
            chapter_index=0,
            chapter_title="第一章",
            chapter_context_digest="b" * 64,
            result={"title": "第一章", "content": "可信章节正文"},
        )
        progress(
            {
                "event": "chapter_checkpoint_saved",
                "chapter_index": 1,
                "chapter_title": "第一章",
                "chapters_total": 2,
                "saved_chapter_count": checkpoint["saved_chapter_count"],
                "checkpoint_status": checkpoint["status"],
            }
        )
        progress(
            {
                "event": "chapter_completed",
                "chapter_index": 1,
                "chapter_title": "第一章",
                "chapters_total": 2,
                "ok": True,
            }
        )
        requested = job_store.transition_job(
            job_id,
            allowed_from={"running"},
            status="cancel_requested",
        )
        assert requested is not None
        raise RuntimeError("cancelled_by_user:test")

    monkeypatch.setattr(actions_bridge, "run_autoplan", fake_run_autoplan)
    actions_bridge.run_actions_generation_job(
        job_id,
        _payload(outline=["第一章", "第二章"]),
    )

    record = job_store.get_job(job_id)
    assert record is not None
    assert record["status"] == "cancelled"
    assert record["error"]["code"] == "JOB_CANCELLED"
    assert record["attempt_id"] is None
    assert record["progress"]["percent"] < 100
    assert record["progress"]["chapters"] == {
        "started": 1,
        "succeeded": 1,
        "failed": 0,
        "total": 2,
    }
    assert record["progress"]["checkpoint"]["status"] == "interrupted_recoverable"
    assert record["progress"]["checkpoint"]["saved_chapter_count"] == 1
    assert "job_cancelled" in events
    checkpoint = generation_checkpoint.load_generation_checkpoint(
        namespace=job_id,
        scope="variant-1",
        binding=binding,
    )
    assert checkpoint is not None
    assert checkpoint["status"] == "interrupted_recoverable"


def test_success_event_is_not_emitted_when_terminal_transition_loses_race(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    events: list[str] = []
    job_id = job_store.create_job(_payload())
    real_transition = actions_bridge.transition_job

    async def fake_run_autoplan(_payload_value: dict) -> dict:
        return {"variant_id": 1, "sections": [{"title": "第一章"}]}

    def lose_success_transition(*args, **kwargs):
        if str(kwargs.get("status") or "") == "succeeded":
            return None
        return real_transition(*args, **kwargs)

    monkeypatch.setattr(actions_bridge, "run_autoplan", fake_run_autoplan)
    monkeypatch.setattr(
        actions_bridge,
        "_finalize_variant_derivatives",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        lambda *_args, **_kwargs: {"json": "preview.json", "delivery_ready": False},
    )
    monkeypatch.setattr(actions_bridge, "transition_job", lose_success_transition)
    monkeypatch.setattr(
        actions_bridge,
        "append_runtime_event",
        lambda _jid, event, **_fields: events.append(event),
    )

    actions_bridge.run_actions_generation_job(job_id, _payload())

    assert "job_succeeded" not in events
    assert (job_store.get_job(job_id) or {})["status"] == "running"


def test_success_terminal_projects_complete_checkpoint_before_success_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    payload = _payload()
    payload["dry_run"] = False
    job_id = job_store.create_job(payload)
    terminal_order: list[str] = []
    real_transition = job_store.transition_job

    async def fake_run_autoplan(_payload_value: dict) -> dict:
        return {
            "variant_id": 1,
            "sections": [{"title": "第一章", "content": "可信正文"}],
            "generation_checkpoint": {
                "schema_version": "generation-checkpoint-v3",
                "binding_digest": "a" * 64,
                "status": "complete",
                "saved_chapter_count": 1,
                "saved_chapter_indexes": [0],
                "chapters_total": 1,
            },
        }

    def transition(*args, **kwargs):
        transitioned = real_transition(*args, **kwargs)
        if kwargs.get("status") == "succeeded":
            terminal_order.append("succeeded_transition")
            assert transitioned is not None
            assert transitioned["progress"]["checkpoint"]["status"] == "complete"
        return transitioned

    def append_event(_job_id: str, event: str, **_fields: object) -> None:
        if event == "job_succeeded":
            terminal_order.append("job_succeeded_event")
            record = job_store.get_job(job_id) or {}
            assert record["status"] == "succeeded"
            assert record["progress"]["checkpoint"]["status"] == "complete"

    monkeypatch.setattr(actions_bridge, "run_autoplan", fake_run_autoplan)
    monkeypatch.setattr(
        actions_bridge,
        "_finalize_variant_derivatives",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        lambda *_args, **_kwargs: {
            "json": "preview.json",
            "delivery_ready": False,
        },
    )
    monkeypatch.setattr(actions_bridge, "transition_job", transition)
    monkeypatch.setattr(actions_bridge, "append_runtime_event", append_event)

    actions_bridge.run_actions_generation_job(job_id, payload)

    record = job_store.get_job(job_id) or {}
    assert record["status"] == "succeeded"
    assert record["progress"]["checkpoint"] == {
        "status": "complete",
        "saved_chapter_count": 1,
        "scopes": [
            {
                "schema_version": "generation-checkpoint-v3",
                "binding_digest": "a" * 64,
                "status": "complete",
                "saved_chapter_count": 1,
                "saved_chapter_indexes": [0],
                "chapters_total": 1,
            }
        ],
    }
    assert terminal_order == ["succeeded_transition", "job_succeeded_event"]


@pytest.mark.parametrize(
    "status",
    ["draft_complete", "failed_partial", "interrupted_recoverable", "disabled"],
)
def test_success_checkpoint_projection_never_promotes_non_complete_scope(
    status: str,
) -> None:
    assert (
        actions_bridge._successful_checkpoint_projection(
            [
                {
                    "generation_checkpoint": {
                        "status": status,
                        "saved_chapter_count": 1,
                    }
                }
            ]
        )
        is None
    )


def test_success_checkpoint_projection_aggregates_all_complete_variants() -> None:
    scopes = [
        {"status": "complete", "saved_chapter_count": 2, "variant": 1},
        {"status": "complete", "saved_chapter_count": 3, "variant": 2},
    ]

    assert actions_bridge._successful_checkpoint_projection(
        [{"generation_checkpoint": scope} for scope in scopes]
    ) == {
        "status": "complete",
        "saved_chapter_count": 5,
        "scopes": scopes,
    }


def test_cancel_checkpoint_seal_failure_is_public_and_not_silent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job(_payload())

    async def fake_run_autoplan(_payload_value: dict) -> dict:
        requested = job_store.transition_job(
            job_id,
            allowed_from={"running"},
            status="cancel_requested",
        )
        assert requested is not None
        raise RuntimeError("cancelled_by_user:test")

    monkeypatch.setattr(actions_bridge, "run_autoplan", fake_run_autoplan)
    monkeypatch.setattr(
        generation_checkpoint,
        "mark_checkpoint_namespace_interrupted",
        lambda _job_id: (_ for _ in ()).throw(OSError("disk unavailable")),
    )
    monkeypatch.setattr(
        actions_bridge,
        "append_runtime_event",
        lambda *_args, **_kwargs: None,
    )

    actions_bridge.run_actions_generation_job(job_id, _payload())

    record = job_store.get_job(job_id)
    assert record is not None
    assert record["status"] == "cancelled"
    assert record["error"]["code"] == "JOB_CANCELLED_CHECKPOINT_SEAL_FAILED"
    assert record["progress"]["checkpoint"] == {
        "status": "interruption_seal_failed",
        "saved_chapter_count": 0,
        "error_code": "CHECKPOINT_INTERRUPTION_SEAL_FAILED",
        "error_type": "OSError",
    }


def test_legacy_worker_cannot_write_checkpoint_terminal_or_event_after_reconcile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    events: list[str] = []
    observations: dict[str, object] = {}
    payload = {
        "topic": "旧入口租约回归",
        "project_id": "legacy-lease-test",
        "outline": ["第一章"],
        "variants": 1,
        "_variant_ids": [1],
        "dry_run": True,
        "_provider_admission_required": False,
    }
    job_id = job_store.create_job(payload)
    monkeypatch.setattr(
        legacy_router,
        "append_runtime_event",
        lambda _job_id, event, **_fields: events.append(event),
    )

    async def _run(payload_value: dict) -> dict:
        record = job_store.get_job(job_id) or {}
        updated = job_store.merge_job(
            job_id,
            expected_attempt_id=str(record["attempt_id"]),
            expected_owner_instance_id=str(record["owner_instance_id"]),
            progress={"heartbeat_at": 100.0, "percent": 25},
        )
        assert updated is not None
        assert job_store.reconcile_stale_jobs(
            now=200.0,
            stale_after_seconds=60,
        ) == [job_id]
        observations["record_after_reconcile"] = job_store.get_job(job_id)
        observations["event_count_after_reconcile"] = len(events)
        with pytest.raises(job_store.JobLeaseLostError, match="job_lease_lost"):
            payload_value["_checkpoint_write_guard"](
                lambda: observations.setdefault("late_checkpoint", True)
            )
        return {"variant_id": 1, "sections": [{"title": "第一章"}]}

    monkeypatch.setattr(legacy_router, "run_autoplan", _run)

    legacy_router.run_legacy_generation_job(job_id, payload)

    after = job_store.get_job(job_id)
    assert after == observations["record_after_reconcile"]
    assert after is not None
    assert after["status"] == "interrupted_recoverable"
    assert after["progress"]["percent"] == 25
    assert "late_checkpoint" not in observations
    assert len(events) == observations["event_count_after_reconcile"]
    assert not any(
        event in {"legacy_job_succeeded", "legacy_job_failed", "legacy_job_cancelled"}
        for event in events
    )


def test_ingest_worker_cannot_restore_progress_terminal_or_event_after_reconcile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    spool_root = tmp_path / "ingest-spool"
    monkeypatch.setattr(job_store, "INGEST_SPOOL_DIR", spool_root)
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", spool_root)
    monkeypatch.setattr(ingest_router, "INGEST_WORKERS", 1)
    events: list[str] = []
    observations: dict[str, object] = {}
    source = tmp_path / "source.txt"
    source.write_text("可信资料", encoding="utf-8")
    entry = {
        "filename": "source.txt",
        "path": str(source),
        "bytes": source.stat().st_size,
        "sha256": "a" * 64,
        "file_id": "a" * 64,
    }
    job_id = job_store.create_job({"action": "ingest", "file_count": 1})
    monkeypatch.setattr(
        ingest_router,
        "append_runtime_event",
        lambda _job_id, event, **_fields: events.append(event),
    )

    async def _handle_upload(_uploads: object, **_options: object) -> dict:
        record = job_store.get_job(job_id) or {}
        updated = job_store.merge_job(
            job_id,
            expected_attempt_id=str(record["attempt_id"]),
            expected_owner_instance_id=str(record["owner_instance_id"]),
            progress={"heartbeat_at": 100.0, "percent": 30},
        )
        assert updated is not None
        assert job_store.reconcile_stale_jobs(
            now=200.0,
            stale_after_seconds=60,
        ) == [job_id]
        observations["record_after_reconcile"] = job_store.get_job(job_id)
        observations["event_count_after_reconcile"] = len(events)
        return {
            "accepted": [{"filename": "source.txt", "file_id": "a" * 64}],
            "rejected": [],
            "warnings": [],
            "cache_hits": 0,
        }

    monkeypatch.setattr(ingest_router, "_handle_upload", _handle_upload)

    ingest_router._run_ingest_job(job_id, [entry], {}, [])

    after = job_store.get_job(job_id)
    assert after == observations["record_after_reconcile"]
    assert after is not None
    assert after["status"] == "interrupted_recoverable"
    assert after["progress"]["percent"] == 30
    assert len(events) == observations["event_count_after_reconcile"]
    assert not any(
        event in {"ingest_succeeded", "ingest_failed", "ingest_cancelled"}
        for event in events
    )


def test_legacy_worker_claims_queued_cancellation_and_revokes_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    events: list[str] = []
    payload = {
        "topic": "旧入口排队取消",
        "project_id": "legacy-cancel-test",
        "outline": ["第一章"],
        "variants": 1,
        "_variant_ids": [1],
        "dry_run": True,
        "_provider_admission_required": False,
    }
    job_id = job_store.create_job(payload)
    requested = job_store.transition_job(
        job_id,
        allowed_from={"queued"},
        status="cancel_requested",
    )
    assert requested is not None
    monkeypatch.setattr(
        legacy_router,
        "append_runtime_event",
        lambda _job_id, event, **_fields: events.append(event),
    )

    legacy_router.run_legacy_generation_job(job_id, payload)

    record = job_store.get_job(job_id) or {}
    assert record["status"] == "cancelled"
    assert record["attempt_id"] is None
    assert record["owner_instance_id"] is None
    assert record["error"]["code"] == "JOB_CANCELLED"
    assert record["progress"]["checkpoint"]["status"] == "interrupted_empty"
    assert events == ["legacy_job_cancelled"]


def test_ingest_worker_claims_queued_cancellation_and_revokes_lease(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    spool_root = tmp_path / "ingest-spool"
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", spool_root)
    events: list[str] = []
    job_id = job_store.create_job({"action": "ingest", "file_count": 1})
    requested = job_store.transition_job(
        job_id,
        allowed_from={"queued"},
        status="cancel_requested",
    )
    assert requested is not None
    monkeypatch.setattr(
        ingest_router,
        "append_runtime_event",
        lambda _job_id, event, **_fields: events.append(event),
    )

    ingest_router._run_ingest_job(job_id, [], {}, [])

    record = job_store.get_job(job_id) or {}
    assert record["status"] == "cancelled"
    assert record["attempt_id"] is None
    assert record["owner_instance_id"] is None
    assert record["error"]["code"] == "INGEST_CANCELLED"
    assert events == ["ingest_cancelled"]


def test_active_cancel_lease_cannot_be_stolen_by_duplicate_worker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    job_id = job_store.create_job({"action": "ingest"})
    worker_a = job_store.acquire_job_lease(job_id, owner_instance_id="worker-a")
    assert worker_a is not None
    requested = job_store.transition_job(
        job_id,
        allowed_from={"running"},
        status="cancel_requested",
    )
    assert requested is not None

    assert (
        job_store.acquire_job_lease(job_id, owner_instance_id="worker-b") is None
    )
    assert job_store.job_lease_active(
        job_id,
        attempt_id=str(worker_a["attempt_id"]),
        owner_instance_id=str(worker_a["owner_instance_id"]),
    )


def test_legacy_staged_outputs_are_not_published_after_reconcile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    events: list[str] = []
    observations: dict[str, object] = {}
    payload = {
        "topic": "旧入口输出发布围栏",
        "project_id": "legacy-output-fence",
        "outline": ["第一章"],
        "variants": 1,
        "_variant_ids": [1],
        "dry_run": True,
        "_provider_admission_required": False,
    }
    job_id = job_store.create_job(payload)

    async def _run(_payload_value: dict) -> dict:
        return {"variant_id": 1, "sections": [{"title": "第一章"}]}

    def _export(_variant: dict, path: str) -> None:
        Path(path).write_bytes(b"staged-docx")
        if "record_after_reconcile" in observations:
            return
        record = job_store.get_job(job_id) or {}
        updated = job_store.merge_job(
            job_id,
            expected_attempt_id=str(record["attempt_id"]),
            expected_owner_instance_id=str(record["owner_instance_id"]),
            progress={"heartbeat_at": 100.0, "percent": 55},
        )
        assert updated is not None
        assert job_store.reconcile_stale_jobs(
            now=200.0,
            stale_after_seconds=60,
        ) == [job_id]
        observations["record_after_reconcile"] = job_store.get_job(job_id)

    monkeypatch.setattr(legacy_router, "run_autoplan", _run)
    monkeypatch.setattr(
        legacy_router,
        "_local_adapter_gate_results",
        lambda results: {"export_allowed": True, "results": results, "issues": []},
    )
    monkeypatch.setattr(legacy_router, "export_autoplan_docx", _export)
    monkeypatch.setattr(legacy_router, "export_autoplan_compare_docx", _export)
    monkeypatch.setattr(
        legacy_router,
        "append_runtime_event",
        lambda _job_id, event, **_fields: events.append(event),
    )

    legacy_router.run_legacy_generation_job(job_id, payload)

    record = job_store.get_job(job_id)
    assert record == observations["record_after_reconcile"]
    assert record is not None
    assert record["status"] == "interrupted_recoverable"
    assert not list((tmp_path / "build").glob(f"autoplan_{job_id}*"))
    assert "legacy_job_succeeded" not in events


def test_real_ingest_persistence_stops_at_reconcile_fence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    workspace = tmp_path / "workspace"
    cache_root = tmp_path / "cache"
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", cache_root)
    events: list[str] = []
    observations: dict[str, object] = {}
    source = tmp_path / "source.txt"
    source.write_text("可信资料正文", encoding="utf-8")
    job_id = job_store.create_job({"action": "ingest", "file_count": 1})
    lease = job_store.acquire_job_lease(job_id, owner_instance_id="worker-a")
    assert lease is not None

    async def _extract(_ext: str, _path: Path, _total_bytes: int) -> dict:
        updated = job_store.merge_job(
            job_id,
            expected_attempt_id=str(lease["attempt_id"]),
            expected_owner_instance_id=str(lease["owner_instance_id"]),
            progress={"heartbeat_at": 100.0, "percent": 30},
        )
        assert updated is not None
        assert job_store.reconcile_stale_jobs(
            now=200.0,
            stale_after_seconds=60,
        ) == [job_id]
        observations["record_after_reconcile"] = job_store.get_job(job_id)
        observations["event_count_after_reconcile"] = len(events)
        return {
            "doc_type": "txt",
            "pages": 1,
            "text_bytes": 18,
            "extract_text": "可信资料正文",
        }

    monkeypatch.setattr(ingest_router, "_extract_text_path_bounded", _extract)
    monkeypatch.setattr(
        ingest_router,
        "append_runtime_event",
        lambda _job_id, event, **_fields: events.append(event),
    )
    outcome = ingest_router._process_spooled_entry(
        job_id,
        1,
        1,
        {
            "filename": "source.txt",
            "path": str(source),
            "bytes": source.stat().st_size,
        },
        {"workspace_dir": str(workspace)},
        str(lease["attempt_id"]),
        str(lease["owner_instance_id"]),
    )

    assert outcome["cancelled"] is True
    assert job_store.get_job(job_id) == observations["record_after_reconcile"]
    assert len(events) == observations["event_count_after_reconcile"]
    if cache_root.exists():
        assert not list(cache_root.glob("*"))
    assert not list((workspace / "extracts").glob("*.txt"))
    assert not list((workspace / "previews").glob("*.png"))
    assert not (workspace / "audit" / "ingest.jsonl").exists()


@pytest.mark.parametrize("worker", ["legacy", "ingest"])
def test_success_transition_losing_to_cancel_is_acknowledged_without_success_event(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    worker: str,
) -> None:
    _configure_roots(monkeypatch, tmp_path)
    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    if worker == "legacy":
        payload = {
            "topic": "终态取消竞态",
            "project_id": "legacy-cancel-race",
            "outline": ["第一章"],
            "variants": 1,
            "_variant_ids": [1],
            "dry_run": True,
            "_provider_admission_required": False,
        }
        job_id = job_store.create_job(payload)
        real_transition = legacy_router.transition_job

        async def _run(_payload_value: dict) -> dict:
            return {"variant_id": 1, "sections": [{"title": "第一章"}]}

        def _transition(*args, **kwargs):
            if kwargs.get("status") == "succeeded":
                job_store.transition_job(
                    job_id,
                    allowed_from={"running"},
                    status="cancel_requested",
                )
            return real_transition(*args, **kwargs)

        monkeypatch.setattr(legacy_router, "run_autoplan", _run)
        monkeypatch.setattr(
            legacy_router,
            "_local_adapter_gate_results",
            lambda results: {
                "export_allowed": True,
                "results": results,
                "issues": [],
            },
        )
        monkeypatch.setattr(
            legacy_router,
            "export_autoplan_docx",
            lambda _variant, path: Path(path).write_bytes(b"docx"),
        )
        monkeypatch.setattr(
            legacy_router,
            "export_autoplan_compare_docx",
            lambda _variant, path: Path(path).write_bytes(b"compare"),
        )
        monkeypatch.setattr(legacy_router, "transition_job", _transition)
        monkeypatch.setattr(
            legacy_router,
            "append_runtime_event",
            lambda _job_id, event, **_fields: events.append(event),
        )
        legacy_router.run_legacy_generation_job(job_id, payload)
        success_event = "legacy_job_succeeded"
    else:
        job_id = job_store.create_job({"action": "ingest", "file_count": 1})
        real_transition = ingest_router.transition_job
        monkeypatch.setattr(ingest_router, "INGEST_WORKERS", 1)
        monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")

        def _process(*_args, **_kwargs) -> dict:
            return {
                "index": 1,
                "filename": "source.txt",
                "elapsed_seconds": 0.1,
                "accepted": [{"filename": "source.txt", "file_id": "a" * 64}],
                "rejected": [],
                "warnings": [],
                "cache_hits": 0,
            }

        def _transition(*args, **kwargs):
            if kwargs.get("status") == "succeeded":
                job_store.transition_job(
                    job_id,
                    allowed_from={"running"},
                    status="cancel_requested",
                )
            return real_transition(*args, **kwargs)

        monkeypatch.setattr(ingest_router, "_process_spooled_entry", _process)
        monkeypatch.setattr(ingest_router, "transition_job", _transition)
        monkeypatch.setattr(
            ingest_router,
            "append_runtime_event",
            lambda _job_id, event, **_fields: events.append(event),
        )
        ingest_router._run_ingest_job(
            job_id,
            [
                {
                    "filename": "source.txt",
                    "path": str(tmp_path / "source.txt"),
                    "bytes": 1,
                    "file_id": "a" * 64,
                }
            ],
            {},
            [],
        )
        success_event = "ingest_succeeded"

    record = job_store.get_job(job_id) or {}
    assert record["status"] == "cancelled"
    assert record["attempt_id"] is None
    assert success_event not in events
