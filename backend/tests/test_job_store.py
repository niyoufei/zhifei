"""
Unit tests for backend/zhifei_autoplan/job_store.py
"""
import json
import multiprocessing
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def _merge_result_in_spawned_process(
    job_dir: str,
    job_id: str,
    result_key: str,
    start_event,
) -> None:
    from backend.zhifei_autoplan import job_store

    job_store.JOB_DIR = Path(job_dir)
    start_event.wait(timeout=10)
    job_store.merge_job(job_id, result={result_key: result_key})


class TestCreateJob:
    """Tests for create_job function."""

    def test_create_job_returns_job_id(self, tmp_path):
        """Test create_job returns a valid job_id string."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            payload = {"action": "test"}
            job_id = job_store.create_job(payload)

            assert isinstance(job_id, str)
            assert len(job_id) == 32  # UUID hex

    def test_create_job_with_user_id(self, tmp_path):
        """Test create_job with user_id."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            payload = {"action": "test"}
            job_id = job_store.create_job(payload, user_id=123)

            rec = job_store.get_job(job_id)
            assert rec["user_id"] == 123

    def test_create_job_without_user_id(self, tmp_path):
        """Test create_job without user_id (None)."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            payload = {"action": "test"}
            job_id = job_store.create_job(payload)

            rec = job_store.get_job(job_id)
            assert rec["user_id"] is None

    def test_create_job_sets_queued_status(self, tmp_path):
        """Test create_job sets status to 'queued'."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            rec = job_store.get_job(job_id)
            assert rec["status"] == "queued"

    def test_create_job_stores_payload(self, tmp_path):
        """Test create_job stores the payload."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            payload = {"action": "generate", "params": {"a": 1, "b": 2}}
            job_id = job_store.create_job(payload)

            rec = job_store.get_job(job_id)
            assert rec["payload"] == payload

    def test_create_job_sets_timestamps(self, tmp_path):
        """Test create_job sets created_at and updated_at."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            before = time.time()
            job_id = job_store.create_job({"action": "test"})
            after = time.time()

            rec = job_store.get_job(job_id)
            assert before <= rec["created_at"] <= after
            assert before <= rec["updated_at"] <= after

    def test_create_job_initializes_result_empty(self, tmp_path):
        """Test create_job initializes result as empty dict."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            rec = job_store.get_job(job_id)
            assert rec["result"] == {}

    def test_create_job_initializes_error_none(self, tmp_path):
        """Test create_job initializes error as None."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            rec = job_store.get_job(job_id)
            assert rec["error"] is None

    def test_create_job_writes_file(self, tmp_path):
        """Test create_job writes a JSON file."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            job_file = job_dir / f"{job_id}.json"
            assert job_file.exists()

    def test_create_job_unique_ids(self, tmp_path):
        """Test create_job generates unique IDs."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            ids = [job_store.create_job({"n": i}) for i in range(10)]
            assert len(set(ids)) == 10

    def test_create_job_empty_payload(self, tmp_path):
        """Test create_job with empty payload."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({})

            rec = job_store.get_job(job_id)
            assert rec["payload"] == {}

    def test_create_job_chinese_payload(self, tmp_path):
        """Test create_job with Chinese content in payload."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            payload = {"项目名称": "施工组织设计", "操作": "生成"}
            job_id = job_store.create_job(payload)

            rec = job_store.get_job(job_id)
            assert rec["payload"]["项目名称"] == "施工组织设计"


class TestUpdateJob:
    """Tests for update_job function."""

    def test_update_job_status(self, tmp_path):
        """Test update_job can update status."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            job_store.update_job(job_id, status="running")

            rec = job_store.get_job(job_id)
            assert rec["status"] == "running"

    def test_update_job_result(self, tmp_path):
        """Test update_job can update result."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            result = {"json": "/path/to/output.json", "docx": "/path/to/output.docx"}
            job_store.update_job(job_id, result=result)

            rec = job_store.get_job(job_id)
            assert rec["result"] == result

    def test_update_job_error(self, tmp_path):
        """Test update_job can update error."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            job_store.update_job(job_id, status="failed", error="Something went wrong")

            rec = job_store.get_job(job_id)
            assert rec["status"] == "failed"
            assert rec["error"] == "Something went wrong"

    def test_update_job_updates_timestamp(self, tmp_path):
        """Test update_job updates updated_at timestamp."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})
            rec1 = job_store.get_job(job_id)
            original_updated_at = rec1["updated_at"]

            time.sleep(0.01)
            job_store.update_job(job_id, status="running")

            rec2 = job_store.get_job(job_id)
            assert rec2["updated_at"] > original_updated_at

    def test_update_job_returns_record(self, tmp_path):
        """Test update_job returns the updated record."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            result = job_store.update_job(job_id, status="done")

            assert isinstance(result, dict)
            assert result["job_id"] == job_id
            assert result["status"] == "done"

    def test_update_job_multiple_fields(self, tmp_path):
        """Test update_job can update multiple fields at once."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            job_store.update_job(
                job_id,
                status="done",
                result={"output": "test.json"},
                error=None
            )

            rec = job_store.get_job(job_id)
            assert rec["status"] == "done"
            assert rec["result"]["output"] == "test.json"

    def test_update_job_preserves_payload(self, tmp_path):
        """Test update_job preserves original payload."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            original_payload = {"action": "generate", "params": {"x": 1}}
            job_id = job_store.create_job(original_payload)

            job_store.update_job(job_id, status="done")

            rec = job_store.get_job(job_id)
            assert rec["payload"] == original_payload

    def test_update_job_nonexistent_fails_closed(self, tmp_path):
        """A late worker must never resurrect a deleted job record."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            missing_job_id = "f" * 32
            result = job_store.update_job(missing_job_id, status="running")

            assert result is None
            assert not (job_dir / f"{missing_job_id}.json").exists()

    def test_update_job_rejects_invalid_job_id(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        with (
            patch.object(job_store, "JOB_DIR", tmp_path / "jobs"),
            pytest.raises(ValueError, match="invalid job_id"),
        ):
            job_store.update_job("../outside", status="running")


class TestJobStoreSecurity:
    def test_credentials_are_recursively_redacted_on_disk(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        with patch.object(job_store, "JOB_DIR", job_dir):
            payload = {
                "provider": "anthropic",
                "api_key": "secret-main",
                "api_keys": {"openai": "secret-fallback"},
                "nested": [{"authorization": "Bearer secret"}],
                "image_api_key": "secret-image",
            }
            job_id = job_store.create_job(payload)
            raw = (job_dir / f"{job_id}.json").read_text(encoding="utf-8")
            rec = json.loads(raw)

            assert "secret-main" not in raw
            assert "secret-fallback" not in raw
            assert "Bearer secret" not in raw
            assert "secret-image" not in raw
            assert rec["payload"]["api_key"] == "[REDACTED]"
            assert rec["payload"]["api_keys"] == "[REDACTED]"
            assert rec["payload"]["nested"][0]["authorization"] == "[REDACTED]"

    def test_job_directory_and_file_are_private(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "generate"})

            assert job_dir.stat().st_mode & 0o777 == 0o700
            assert (job_dir / f"{job_id}.json").stat().st_mode & 0o777 == 0o600


class TestHeartbeatJob:
    def test_heartbeat_merges_progress_and_runtime(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "generate"})
            job_store.update_job(
                job_id,
                status="running",
                progress={"percent": 15, "stage": "variant_running"},
            )
            rec = job_store.heartbeat_job(
                job_id,
                activity="2个章节Agent正在编辑",
                progress_updates={"chapters_done": 2, "chapters_total": 8},
                agent_runtime_updates={"active_agents": 2},
            )

            assert rec["progress"]["percent"] == 15
            assert rec["progress"]["stage"] == "variant_running"
            assert rec["progress"]["activity"] == "2个章节Agent正在编辑"
            assert rec["progress"]["heartbeat_seq"] == 1
            assert rec["agent_runtime"]["active_agents"] == 2

    def test_heartbeat_does_not_revive_terminal_job(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "generate"})
            job_store.update_job(job_id, status="done", progress={"percent": 100})
            before = job_store.get_job(job_id)
            rec = job_store.heartbeat_job(job_id, activity="不应写入")

            assert rec["status"] == "done"
            assert rec["progress"] == before["progress"]


class TestRuntimeReconciliation:
    def test_cross_process_merges_do_not_lose_updates(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "generate"})
            context = multiprocessing.get_context("spawn")
            start_event = context.Event()
            processes = [
                context.Process(
                    target=_merge_result_in_spawned_process,
                    args=(str(job_dir), job_id, f"worker_{index}", start_event),
                )
                for index in range(6)
            ]
            for process in processes:
                process.start()
            start_event.set()
            for process in processes:
                process.join(timeout=20)
                assert process.exitcode == 0
            result = (job_store.get_job(job_id) or {}).get("result") or {}

        assert set(result) == {f"worker_{index}" for index in range(6)}

    def test_transition_is_revisioned_and_terminal_state_is_monotonic(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        with patch.object(job_store, "JOB_DIR", tmp_path / "jobs"):
            job_id = job_store.create_job({"action": "generate"})
            queued = job_store.get_job(job_id)
            running = job_store.transition_job(
                job_id,
                allowed_from={"queued"},
                status="running",
                expected_revision=queued["revision"],
            )
            finished = job_store.transition_job(
                job_id,
                allowed_from={"running"},
                status="succeeded",
            )
            late_worker = job_store.transition_job(
                job_id,
                allowed_from={"queued", "running"},
                status="failed",
            )

        assert running["revision"] > queued["revision"]
        assert finished["status"] == "succeeded"
        assert late_worker is None

    def test_dispatched_queued_job_is_not_reaped_before_worker_starts(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        with patch.object(job_store, "JOB_DIR", tmp_path / "jobs"):
            job_id = job_store.create_job({"action": "generate"})
            job_store.merge_job(
                job_id,
                updated_at=100.0,
                progress={"heartbeat_at": 100.0},
            )
            reconciled = job_store.reconcile_stale_jobs(
                stale_after_seconds=60,
                now=200.0,
                protected_job_ids={job_id},
            )

            assert reconciled == []
            assert job_store.get_job(job_id)["status"] == "queued"

    def test_dispatched_running_job_is_reaped_after_lease_heartbeat_expires(
        self,
        tmp_path,
    ):
        from backend.zhifei_autoplan import job_store

        with patch.object(job_store, "JOB_DIR", tmp_path / "jobs"):
            job_id = job_store.create_job({"action": "generate"})
            lease = job_store.acquire_job_lease(
                job_id,
                owner_instance_id="hung-worker",
            )
            assert lease is not None
            assert lease["attempt_revision"] == lease["revision"]
            job_store.merge_job(
                job_id,
                expected_attempt_id=str(lease["attempt_id"]),
                expected_owner_instance_id=str(lease["owner_instance_id"]),
                progress={"heartbeat_at": 100.0},
            )

            reconciled = job_store.reconcile_stale_jobs(
                stale_after_seconds=60,
                now=200.0,
                protected_job_ids={job_id},
            )

            record = job_store.get_job(job_id)
            assert reconciled == [job_id]
            assert record["status"] == "interrupted_recoverable"
            assert record["attempt_id"] is None
            assert record["last_attempt_id"] == lease["attempt_id"]
            assert record["last_owner_instance_id"] == lease["owner_instance_id"]
            assert record["last_job_revision"] == lease["attempt_revision"]
            assert record["attempt_revision"] is None

    def test_merge_job_preserves_nested_progress(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        with patch.object(job_store, "JOB_DIR", tmp_path / "jobs"):
            job_id = job_store.create_job({"action": "generate"})
            job_store.update_job(
                job_id,
                status="running",
                progress={"percent": 15, "chapters": {"succeeded": 1, "total": 3}},
            )
            rec = job_store.merge_job(
                job_id,
                status="failed",
                progress={"work_state": "idle", "detail": "failed"},
            )

        assert rec["progress"]["percent"] == 15
        assert rec["progress"]["chapters"] == {"succeeded": 1, "total": 3}
        assert rec["progress"]["work_state"] == "idle"

    def test_reconcile_stale_job_is_fail_closed_and_recoverable(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        with patch.object(job_store, "JOB_DIR", tmp_path / "jobs"):
            job_id = job_store.create_job({"action": "generate"})
            job_store.update_job(
                job_id,
                status="running",
                updated_at=100.0,
                progress={"heartbeat_at": 100.0, "stage": "generation", "percent": 35},
            )
            reconciled = job_store.reconcile_stale_jobs(
                stale_after_seconds=60,
                now=200.0,
            )
            rec = job_store.get_job(job_id)

        assert reconciled == [job_id]
        assert rec["status"] == "interrupted_recoverable"
        assert rec["progress"]["percent"] == 35
        assert rec["progress"]["work_state"] == "idle"
        assert rec["error"]["code"] == "JOB_INTERRUPTED"

    def test_reconcile_stale_ingest_job_cleans_spool_with_stable_error(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_root = tmp_path / "jobs"
        spool_root = tmp_path / "spool"
        with (
            patch.object(job_store, "JOB_DIR", job_root),
            patch.object(job_store, "INGEST_SPOOL_DIR", spool_root),
        ):
            job_id = job_store.create_job({"action": "ingest"})
            spool_dir = spool_root / job_id
            spool_dir.mkdir(parents=True)
            (spool_dir / "upload.pdf").write_bytes(b"spooled")
            job_store.update_job(
                job_id,
                status="running",
                updated_at=100.0,
                progress={"heartbeat_at": 100.0, "stage": "ingest", "percent": 47},
            )

            reconciled = job_store.reconcile_stale_jobs(
                stale_after_seconds=60,
                now=200.0,
            )
            rec = job_store.get_job(job_id)

        assert reconciled == [job_id]
        assert rec["status"] == "interrupted_recoverable"
        assert rec["error"]["code"] == "INGEST_INTERRUPTED"
        assert rec["progress"]["percent"] == 47
        assert not spool_dir.exists()

    def test_reconcile_failed_job_repairs_checkpoint_and_public_error(self, tmp_path):
        from backend.zhifei_autoplan import generation_checkpoint, job_store

        job_root = tmp_path / "jobs"
        checkpoint_root = tmp_path / "checkpoints"
        binding = generation_checkpoint.build_generation_binding(
            topic="项目",
            project_id="p1",
            project_type="房建",
            outline=["一", "二"],
            style={},
            chapter_pages={},
            variant_id=1,
            project_fact_digest="a" * 64,
            requirement_plan_digest="b" * 64,
            provider_routes=[],
        )
        with patch.object(job_store, "JOB_DIR", job_root), patch.object(
            generation_checkpoint,
            "CHECKPOINT_DIR",
            checkpoint_root,
        ):
            job_id = job_store.create_job({"action": "generate"})
            generation_checkpoint.save_section_checkpoint(
                namespace=job_id,
                scope="variant-1",
                binding=binding,
                chapter_index=0,
                chapter_title="一",
                chapter_context_digest="c" * 64,
                result={"title": "一", "content": "正文"},
            )
            job_store.update_job(
                job_id,
                status="failed",
                error="RuntimeError('{\"code\": \"MODEL_CHAIN_EXHAUSTED\", \"message\": \"失败\"}')",
                progress={"percent": 100},
            )
            rec = job_store.reconcile_failed_job_evidence(job_id)

        assert rec["error"]["code"] == "MODEL_CHAIN_EXHAUSTED"
        assert rec["progress"]["percent"] == 45
        assert rec["progress"]["chapters"] == {
            "started": 2,
            "succeeded": 1,
            "failed": 1,
            "total": 2,
        }
        assert rec["progress"]["checkpoint"]["scopes"][0]["status"] == "failed_partial"

    def test_startup_reconciles_failed_jobs_with_false_completion_evidence(self, tmp_path):
        from backend.zhifei_autoplan import generation_checkpoint, job_store

        job_root = tmp_path / "jobs"
        checkpoint_root = tmp_path / "checkpoints"
        binding = generation_checkpoint.build_generation_binding(
            topic="项目",
            project_id="p1",
            project_type="房建",
            outline=["一"],
            style={},
            chapter_pages={},
            variant_id=1,
            project_fact_digest="a" * 64,
            requirement_plan_digest="b" * 64,
            provider_routes=[],
        )
        with patch.object(job_store, "JOB_DIR", job_root), patch.object(
            generation_checkpoint,
            "CHECKPOINT_DIR",
            checkpoint_root,
        ):
            failed_id = job_store.create_job({"action": "generate"})
            generation_checkpoint.save_section_checkpoint(
                namespace=failed_id,
                scope="variant-1",
                binding=binding,
                chapter_index=0,
                chapter_title="一",
                chapter_context_digest="c" * 64,
                result={"title": "一", "content": "正文"},
            )
            generation_checkpoint.finalize_generation_checkpoint(
                namespace=failed_id,
                scope="variant-1",
                binding=binding,
                status="draft_complete",
            )
            job_store.update_job(
                failed_id,
                status="failed",
                error={
                    "code": "REQUIREMENT_EVIDENCE_BLOCKED",
                    "message": "章节初稿已保存，但证据门未通过。",
                    "action": "修复后恢复。",
                },
                progress={
                    "percent": 75,
                    "phase": "quality_review",
                    "stage": "quality_review_failed",
                    "checkpoint": {"status": "draft_complete"},
                },
                result={"checkpoint_status": "draft_complete"},
            )
            untouched_id = job_store.create_job({"action": "generate"})
            job_store.update_job(
                untouched_id,
                status="failed",
                progress={"checkpoint": {"status": "failed_empty"}},
            )
            false_100_id = job_store.create_job({"action": "generate"})
            job_store.update_job(
                false_100_id,
                status="failed",
                progress={"percent": 100, "checkpoint": {"status": "failed_empty"}},
            )

            reconciled = job_store.reconcile_legacy_failed_jobs()
            repaired = job_store.get_job(failed_id)
            normalized_100 = job_store.get_job(false_100_id)

        assert set(reconciled) == {failed_id, false_100_id}
        assert repaired is not None
        assert repaired["error"]["code"] == "REQUIREMENT_EVIDENCE_BLOCKED"
        assert repaired["progress"]["phase"] == "quality_review"
        assert repaired["progress"]["stage"] == "quality_review_failed"
        assert repaired["progress"]["checkpoint"]["status"] == "failed_partial"
        assert repaired["result"]["checkpoint_status"] == "failed_partial"
        assert repaired["result"]["section_count"] == 1
        assert normalized_100["status"] == "failed"
        assert normalized_100["progress"]["percent"] == 99
        assert normalized_100["progress"]["checkpoint"]["status"] == "failed_empty"

    def test_startup_v2_failed_checkpoint_fails_closed_and_scan_continues(self, tmp_path):
        from backend.zhifei_autoplan import generation_checkpoint, job_store

        job_root = tmp_path / "jobs"
        checkpoint_root = tmp_path / "checkpoints"
        binding = generation_checkpoint.build_generation_binding(
            topic="升级兼容性测试",
            project_id="p-v2",
            project_type="房建",
            outline=["一"],
            style={},
            chapter_pages={},
            variant_id=1,
            project_fact_digest="a" * 64,
            requirement_plan_digest="b" * 64,
            provider_routes=[],
        )
        with patch.object(job_store, "JOB_DIR", job_root), patch.object(
            generation_checkpoint,
            "CHECKPOINT_DIR",
            checkpoint_root,
        ):
            # This healthy record is deliberately older.  The newer v2 record is
            # scanned first, proving that its incompatibility does not abort the
            # remaining startup reconciliation pass.
            healthy_id = job_store.create_job({"action": "generate"})
            job_store.update_job(
                healthy_id,
                status="failed",
                progress={"percent": 100, "checkpoint": {"status": "failed_empty"}},
                result={"checkpoint_status": "failed_empty"},
            )

            legacy_id = job_store.create_job({"action": "generate"})
            generation_checkpoint.save_section_checkpoint(
                namespace=legacy_id,
                scope="variant-1",
                binding=binding,
                chapter_index=0,
                chapter_title="一",
                chapter_context_digest="c" * 64,
                result={"title": "一", "content": "旧版正文"},
            )
            checkpoint_path = checkpoint_root / legacy_id / "variant-1.json"
            legacy_record = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            legacy_record["schema_version"] = "generation-checkpoint-v2"
            core = {
                key: value
                for key, value in legacy_record.items()
                if key != "integrity_digest"
            }
            legacy_record["integrity_digest"] = generation_checkpoint._digest(core)
            checkpoint_path.write_text(
                json.dumps(legacy_record, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            legacy_bytes = checkpoint_path.read_bytes()
            job_store.update_job(
                legacy_id,
                status="failed",
                error={
                    "code": "REQUIREMENT_EVIDENCE_BLOCKED",
                    "message": "旧任务质量门失败。",
                    "action": "恢复任务。",
                },
                progress={
                    "percent": 100,
                    "phase": "quality_review",
                    "checkpoint": {"status": "draft_complete"},
                },
                result={"checkpoint_status": "draft_complete"},
            )

            reconciled = job_store.reconcile_legacy_failed_jobs()
            incompatible = job_store.get_job(legacy_id)
            healthy = job_store.get_job(healthy_id)

            assert checkpoint_path.read_bytes() == legacy_bytes
            with pytest.raises(
                generation_checkpoint.CheckpointIntegrityError,
                match="checkpoint_schema_mismatch",
            ):
                generation_checkpoint.load_generation_checkpoint(
                    namespace=legacy_id,
                    scope="variant-1",
                    binding=binding,
                )

        assert set(reconciled) == {legacy_id, healthy_id}
        assert incompatible is not None
        assert incompatible["status"] == "failed"
        assert incompatible["progress"]["percent"] == 99
        assert incompatible["progress"]["stage"] == "checkpoint_schema_incompatible"
        assert incompatible["progress"]["checkpoint"] == {
            "status": "failure_seal_failed",
            "saved_chapter_count": 0,
            "scopes": [],
            "error_code": "CHECKPOINT_SCHEMA_INCOMPATIBLE",
            "error_type": "CheckpointIntegrityError",
            "reason_code": "checkpoint_schema_mismatch",
            "reuse_allowed": False,
            "migration_attempted": False,
            "schema_compatible": False,
        }
        assert incompatible["error"]["code"] == "REQUIREMENT_EVIDENCE_BLOCKED"
        assert incompatible["error"]["checkpoint_seal_failure"]["code"] == (
            "CHECKPOINT_SCHEMA_INCOMPATIBLE"
        )
        assert incompatible["result"] == {
            "checkpoint_status": "failure_seal_failed",
            "section_count": 0,
            "checkpoint_error_code": "CHECKPOINT_SCHEMA_INCOMPATIBLE",
            "checkpoint_reuse_allowed": False,
            "recoverable": False,
            "delivery_ready": False,
        }
        assert healthy is not None
        assert healthy["progress"]["percent"] == 99
        assert healthy["progress"]["checkpoint"]["status"] == "failed_empty"


class TestGetJob:
    """Tests for get_job function."""

    def test_get_job_existing(self, tmp_path):
        """Test get_job returns existing job."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            rec = job_store.get_job(job_id)

            assert rec is not None
            assert rec["job_id"] == job_id

    def test_get_job_nonexistent(self, tmp_path):
        """Test get_job returns None for nonexistent job."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            rec = job_store.get_job("nonexistent_id")

            assert rec is None

    def test_get_job_returns_dict(self, tmp_path):
        """Test get_job returns a dict."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            rec = job_store.get_job(job_id)

            assert isinstance(rec, dict)

    def test_get_job_invalid_json(self, tmp_path):
        """Test get_job returns None for invalid JSON file."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        # Write invalid JSON
        invalid_file = job_dir / "invalid_id.json"
        invalid_file.write_text("invalid json {", encoding="utf-8")

        with patch.object(job_store, 'JOB_DIR', job_dir):
            rec = job_store.get_job("invalid_id")

            assert rec is None

    def test_get_job_contains_all_fields(self, tmp_path):
        """Test get_job result contains all expected fields."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"}, user_id=42)

            rec = job_store.get_job(job_id)

            assert "job_id" in rec
            assert "user_id" in rec
            assert "status" in rec
            assert "created_at" in rec
            assert "updated_at" in rec
            assert "payload" in rec
            assert "result" in rec
            assert "error" in rec


class TestListJobs:
    """Tests for list_jobs function."""

    def test_list_jobs_empty(self, tmp_path):
        """Test list_jobs returns empty list when no jobs."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            jobs = job_store.list_jobs()

            assert jobs == []

    def test_list_jobs_single(self, tmp_path):
        """Test list_jobs returns single job."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            jobs = job_store.list_jobs()

            assert len(jobs) == 1
            assert jobs[0]["job_id"] == job_id

    def test_list_jobs_multiple(self, tmp_path):
        """Test list_jobs returns multiple jobs."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            ids = [job_store.create_job({"n": i}) for i in range(5)]

            jobs = job_store.list_jobs()

            assert len(jobs) == 5
            returned_ids = [j["job_id"] for j in jobs]
            assert set(returned_ids) == set(ids)

    def test_list_jobs_limit(self, tmp_path):
        """Test list_jobs respects limit parameter."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            for i in range(10):
                job_store.create_job({"n": i})

            jobs = job_store.list_jobs(limit=3)

            assert len(jobs) == 3

    def test_list_jobs_filter_by_user_id(self, tmp_path):
        """Test list_jobs filters by user_id."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_store.create_job({"n": 1}, user_id=1)
            job_store.create_job({"n": 2}, user_id=1)
            job_store.create_job({"n": 3}, user_id=2)
            job_store.create_job({"n": 4}, user_id=None)

            jobs_user1 = job_store.list_jobs(user_id=1)
            jobs_user2 = job_store.list_jobs(user_id=2)

            assert len(jobs_user1) == 2
            assert all(j["user_id"] == 1 for j in jobs_user1)
            assert len(jobs_user2) == 1
            assert jobs_user2[0]["user_id"] == 2

    def test_list_jobs_returns_list_of_dicts(self, tmp_path):
        """Test list_jobs returns list of dicts."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_store.create_job({"action": "test"})

            jobs = job_store.list_jobs()

            assert isinstance(jobs, list)
            assert all(isinstance(j, dict) for j in jobs)

    def test_list_jobs_skips_invalid_json(self, tmp_path):
        """Test list_jobs skips files with invalid JSON."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})

            # Write an invalid JSON file
            invalid_file = job_dir / "invalid.json"
            invalid_file.write_text("not valid json", encoding="utf-8")

            jobs = job_store.list_jobs()

            assert len(jobs) == 1
            assert jobs[0]["job_id"] == job_id

    def test_list_jobs_default_limit(self, tmp_path):
        """Test list_jobs default limit is 50."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            for i in range(60):
                job_store.create_job({"n": i})

            jobs = job_store.list_jobs()

            assert len(jobs) == 50


class TestCleanupJobs:
    """Tests for cleanup_jobs function."""

    def test_cleanup_jobs_removes_old(self, tmp_path):
        """Test cleanup_jobs removes old jobs."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            # Create a job and manually set old timestamp
            job_id = job_store.create_job({"action": "test"})
            job_file = job_dir / f"{job_id}.json"

            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["status"] = "succeeded"
            rec["updated_at"] = time.time() - 10 * 24 * 3600  # 10 days ago
            job_file.write_text(json.dumps(rec), encoding="utf-8")

            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert removed == 1
            assert not job_file.exists()

    def test_cleanup_jobs_keeps_recent(self, tmp_path):
        """Test cleanup_jobs keeps recent jobs."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_file = job_dir / f"{job_id}.json"

            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert removed == 0
            assert job_file.exists()

    def test_cleanup_jobs_returns_count(self, tmp_path):
        """Test cleanup_jobs returns number of removed jobs."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            # Create multiple old jobs
            old_time = time.time() - 10 * 24 * 3600
            for i in range(3):
                job_id = job_store.create_job({"n": i})
                job_file = job_dir / f"{job_id}.json"
                rec = json.loads(job_file.read_text(encoding="utf-8"))
                rec["status"] = "succeeded"
                rec["updated_at"] = old_time
                job_file.write_text(json.dumps(rec), encoding="utf-8")

            # Create one recent job
            job_store.create_job({"n": "recent"})

            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert removed == 3
            assert len(job_store.list_jobs()) == 1

    def test_cleanup_jobs_removes_result_files(self, tmp_path):
        """Test cleanup_jobs removes associated result files."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        # Create a result file
        result_file = tmp_path / "output.docx"
        result_file.write_text("dummy content")

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_store.update_job(job_id, result={"docx": str(result_file)})

            # Make job old
            job_file = job_dir / f"{job_id}.json"
            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["status"] = "succeeded"
            rec["updated_at"] = time.time() - 10 * 24 * 3600
            job_file.write_text(json.dumps(rec), encoding="utf-8")

            job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert not result_file.exists()

    def test_cleanup_jobs_removes_new_artifact_files(self, tmp_path):
        """Test cleanup_jobs removes score_overview_xlsx / expert_review_docx artifacts."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        score_file = tmp_path / "score_overview.xlsx"
        review_file = tmp_path / "expert_review.docx"
        score_file.write_text("dummy")
        review_file.write_text("dummy")

        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_store.update_job(
                job_id,
                result={
                    "score_overview_xlsx": str(score_file),
                    "expert_review_docx": str(review_file),
                },
            )

            job_file = job_dir / f"{job_id}.json"
            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["status"] = "succeeded"
            rec["updated_at"] = time.time() - 10 * 24 * 3600
            job_file.write_text(json.dumps(rec), encoding="utf-8")

            job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert not score_file.exists()
            assert not review_file.exists()

    def test_cleanup_jobs_removes_json_list(self, tmp_path):
        """Test cleanup_jobs removes list of JSON files in result."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        # Create result files
        json_files = [tmp_path / f"output{i}.json" for i in range(3)]
        for f in json_files:
            f.write_text("{}")

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_store.update_job(job_id, result={"json": [str(f) for f in json_files]})

            # Make job old
            job_file = job_dir / f"{job_id}.json"
            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["status"] = "succeeded"
            rec["updated_at"] = time.time() - 10 * 24 * 3600
            job_file.write_text(json.dumps(rec), encoding="utf-8")

            job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            for f in json_files:
                assert not f.exists()

    def test_cleanup_jobs_custom_age(self, tmp_path):
        """Test cleanup_jobs with custom age threshold."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_file = job_dir / f"{job_id}.json"

            # Make job 2 days old
            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["status"] = "succeeded"
            rec["updated_at"] = time.time() - 2 * 24 * 3600
            job_file.write_text(json.dumps(rec), encoding="utf-8")

            # Clean with 1 day threshold
            removed = job_store.cleanup_jobs(older_than_seconds=1 * 24 * 3600)

            assert removed == 1

    def test_cleanup_jobs_handles_missing_result_files(self, tmp_path):
        """Test cleanup_jobs handles missing result files gracefully."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_store.update_job(job_id, result={"docx": "/nonexistent/path.docx"})

            # Make job old
            job_file = job_dir / f"{job_id}.json"
            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["status"] = "succeeded"
            rec["updated_at"] = time.time() - 10 * 24 * 3600
            job_file.write_text(json.dumps(rec), encoding="utf-8")

            # Should not raise
            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert removed == 1

    def test_cleanup_jobs_skips_invalid_json(self, tmp_path):
        """Test cleanup_jobs skips files with invalid JSON."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        # Write invalid JSON file
        invalid_file = job_dir / "invalid.json"
        invalid_file.write_text("not valid json", encoding="utf-8")

        with patch.object(job_store, 'JOB_DIR', job_dir):
            # Should not raise
            removed = job_store.cleanup_jobs()

            assert removed == 0
            assert invalid_file.exists()  # Not removed


class TestWriteJob:
    """Tests for _write_job internal function."""

    def test_write_job_creates_file(self, tmp_path):
        """Test _write_job creates a JSON file."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = "1" * 32
            rec = {"job_id": job_id, "status": "queued"}
            job_store._write_job(rec)

            job_file = job_dir / f"{job_id}.json"
            assert job_file.exists()

    def test_write_job_content(self, tmp_path):
        """Test _write_job writes correct content."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = "2" * 32
            rec = {"job_id": job_id, "status": "running", "payload": {"a": 1}}
            job_store._write_job(rec)

            job_file = job_dir / f"{job_id}.json"
            loaded = json.loads(job_file.read_text(encoding="utf-8"))
            assert loaded == rec

    def test_write_job_chinese_content(self, tmp_path):
        """Test _write_job handles Chinese content."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = "3" * 32
            rec = {"job_id": job_id, "payload": {"名称": "施工组织设计"}}
            job_store._write_job(rec)

            job_file = job_dir / f"{job_id}.json"
            loaded = json.loads(job_file.read_text(encoding="utf-8"))
            assert loaded["payload"]["名称"] == "施工组织设计"

    def test_write_job_without_job_id_noop(self, tmp_path):
        """Test _write_job does nothing if no job_id."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            rec = {"status": "queued"}  # No job_id
            job_store._write_job(rec)

            assert list(job_dir.glob("*.json")) == []

    def test_write_job_overwrites_existing(self, tmp_path):
        """Test _write_job overwrites existing file."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = "4" * 32
            rec1 = {"job_id": job_id, "status": "queued"}
            job_store._write_job(rec1)

            rec2 = {"job_id": job_id, "status": "done"}
            job_store._write_job(rec2)

            job_file = job_dir / f"{job_id}.json"
            loaded = json.loads(job_file.read_text(encoding="utf-8"))
            assert loaded["status"] == "done"


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_job_dir_is_path(self):
        """Test JOB_DIR is a Path object."""
        from backend.zhifei_autoplan import job_store
        assert isinstance(job_store.JOB_DIR, Path)

    def test_job_dir_expected_path(self):
        """Test JOB_DIR has expected path."""
        from backend.zhifei_autoplan import job_store
        assert "jobs" in str(job_store.JOB_DIR)


class TestIntegration:
    """Integration tests for job_store workflow."""

    def test_full_job_lifecycle(self, tmp_path):
        """Test complete job lifecycle: create -> update -> get -> cleanup."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            # Create
            job_id = job_store.create_job({"action": "generate"}, user_id=1)

            # Verify initial state
            rec = job_store.get_job(job_id)
            assert rec["status"] == "queued"

            # Update to running
            job_store.update_job(job_id, status="running")
            rec = job_store.get_job(job_id)
            assert rec["status"] == "running"

            # Update to done with result
            job_store.update_job(
                job_id,
                status="done",
                result={"json": "/output/result.json"}
            )
            rec = job_store.get_job(job_id)
            assert rec["status"] == "done"
            assert rec["result"]["json"] == "/output/result.json"

            # List jobs
            jobs = job_store.list_jobs(user_id=1)
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == job_id

    def test_multiple_users_workflow(self, tmp_path):
        """Test workflow with multiple users."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            # Create jobs for different users
            [
                job_store.create_job({"n": i}, user_id=1) for i in range(3)
            ]
            [
                job_store.create_job({"n": i}, user_id=2) for i in range(2)
            ]

            # List by user
            u1_list = job_store.list_jobs(user_id=1)
            u2_list = job_store.list_jobs(user_id=2)

            assert len(u1_list) == 3
            assert len(u2_list) == 2

            # All jobs
            all_jobs = job_store.list_jobs()
            assert len(all_jobs) == 5

    def test_failed_job_workflow(self, tmp_path):
        """Test workflow for failed job."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            job_id = job_store.create_job({"action": "generate"})

            job_store.update_job(job_id, status="running")
            job_store.update_job(
                job_id,
                status="failed",
                error="知识图谱加载失败：文件不存在"
            )

            rec = job_store.get_job(job_id)
            assert rec["status"] == "failed"
            assert "知识图谱" in rec["error"]

    def test_cleanup_with_mixed_ages(self, tmp_path):
        """Test cleanup with jobs of different ages."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            # Create jobs and set different ages
            old_ids = []
            for i in range(2):
                job_id = job_store.create_job({"n": i})
                job_file = job_dir / f"{job_id}.json"
                rec = json.loads(job_file.read_text(encoding="utf-8"))
                rec["status"] = "succeeded"
                rec["updated_at"] = time.time() - 10 * 24 * 3600  # Old
                job_file.write_text(json.dumps(rec), encoding="utf-8")
                old_ids.append(job_id)

            # Create recent jobs
            recent_ids = [
                job_store.create_job({"n": i + 10}) for i in range(3)
            ]

            # Cleanup
            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600)

            assert removed == 2

            # Verify remaining jobs
            remaining = job_store.list_jobs()
            remaining_ids = [j["job_id"] for j in remaining]

            for oid in old_ids:
                assert oid not in remaining_ids
            for rid in recent_ids:
                assert rid in remaining_ids
