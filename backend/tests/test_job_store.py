"""
Unit tests for backend/zhifei_autoplan/job_store.py
"""
import json
import pytest
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock


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

    def test_create_job_scrubs_sensitive_provider_keys(self, tmp_path):
        """Job payload persistence should never include raw API keys."""
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, 'JOB_DIR', job_dir):
            payload = {
                "provider": "openai",
                "api_key": "openai-secret",
                "api_keys": {"openai": "secret-a", "fallback_1": "secret-b"},
                "image_api_key": "gemini-secret",
                "provider_chain": [
                    {"slot": "main", "provider": "openai", "model": "gpt-5.4", "api_key": "slot-secret", "key_alias": "OPENAI_API_KEY_TEXT_MAIN"}
                ],
            }
            job_id = job_store.create_job(payload)

            rec = job_store.get_job(job_id)
            stored = rec["payload"]
            assert "api_key" not in stored
            assert "api_keys" not in stored
            assert "image_api_key" not in stored
            assert stored["provider_chain"][0]["key_alias"] == "OPENAI_API_KEY_TEXT_MAIN"
            assert "api_key" not in stored["provider_chain"][0]


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

    def test_update_job_keeps_done_state_under_concurrent_worker_refresh(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()

        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "test"})
            job_store.update_job(job_id, status="running")
            worker_read_started = threading.Event()
            result = {"json": str(tmp_path / "done.json")}
            original_read = job_store._read_job_from_path

            def _slow_read(path):
                rec = original_read(path)
                if threading.current_thread().name == "worker-refresh" and not worker_read_started.is_set():
                    worker_read_started.set()
                    time.sleep(0.15)
                return rec

            def _worker_refresh():
                job_store.update_job(job_id, worker={"alive": False, "pid": 123})

            def _mark_done():
                assert worker_read_started.wait(timeout=1.0) is True
                job_store.update_job(job_id, status="done", result=result)

            with patch.object(job_store, "_read_job_from_path", side_effect=_slow_read):
                t1 = threading.Thread(target=_worker_refresh, name="worker-refresh")
                t2 = threading.Thread(target=_mark_done, name="job-finalize")
                t1.start()
                t2.start()
                t1.join(timeout=2)
                t2.join(timeout=2)

            assert t1.is_alive() is False
            assert t2.is_alive() is False
            rec = job_store.get_job(job_id)
            assert rec["status"] == "done"
            assert rec["result"] == result


class TestCleanupJobs:
    def test_cleanup_jobs_skips_archived_tombstones(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        tombstone = job_dir / "abc.archived.json"
        tombstone.write_text(
            json.dumps(
                {
                    "job_id": "abc",
                    "status": "done",
                    "created_at": 0,
                    "updated_at": 0,
                    "archived_at": "2026-03-19T00:00:00",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with patch.object(job_store, "JOB_DIR", job_dir):
            removed = job_store.cleanup_jobs(older_than_seconds=1, archive=False)

        assert removed == 0
        assert tombstone.exists()

    def test_normalize_archived_tombstones_collapses_duplicate_suffixes(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        duplicate = job_dir / "abc.archived.archived.archived.json"
        duplicate.write_text(
            json.dumps(
                {
                    "job_id": "abc",
                    "status": "done",
                    "created_at": 1,
                    "updated_at": 2,
                    "archived_at": "archive.zip",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with patch.object(job_store, "JOB_DIR", job_dir):
            changed = job_store.normalize_archived_tombstones()

        assert changed >= 1
        canonical = job_dir / "abc.archived.json"
        assert canonical.exists()
        assert not duplicate.exists()

    def test_cleanup_jobs_removes_downloaded_actions_run_dir(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        archive_dir = tmp_path / "archive"
        build_root = tmp_path / "build"
        actions_run_dir = build_root / "actions_runs" / "job123"
        job_dir.mkdir()
        archive_dir.mkdir()
        actions_run_dir.mkdir(parents=True)
        (actions_run_dir / "autoplan_job123.json").write_text("{}", encoding="utf-8")

        with patch.object(job_store, "JOB_DIR", job_dir), \
             patch.object(job_store, "ARCHIVE_DIR", archive_dir), \
             patch("backend.zhifei_autoplan.job_store.Path", wraps=Path) as path_cls:
            job_file = job_dir / "job123.json"
            job_file.write_text(
                json.dumps(
                    {
                        "job_id": "job123",
                        "status": "done",
                        "created_at": time.time() - 10 * 24 * 3600,
                        "updated_at": time.time() - 10 * 24 * 3600,
                        "result": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            original_path = Path

            def _path_side_effect(*args, **kwargs):
                p = original_path(*args, **kwargs)
                if str(p) == "build":
                    return build_root
                return p

            path_cls.side_effect = _path_side_effect
            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600, archive=True)

        assert removed == 1
        assert not actions_run_dir.exists()

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

    def test_update_job_nonexistent_creates_record(self, tmp_path):
        """Test update_job with nonexistent job_id creates minimal record."""
        from backend.zhifei_autoplan import job_store
        
        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        
        with patch.object(job_store, 'JOB_DIR', job_dir):
            result = job_store.update_job("nonexistent_id", status="running")
            
            assert result["job_id"] == "nonexistent_id"
            assert result["status"] == "running"


class TestJobSignature:
    """Tests for request-signature based job reuse."""

    def test_compute_job_signature_ignores_api_keys_and_variant_runtime_fields(self):
        from backend.zhifei_autoplan import job_store

        payload_a = {
            "topic": "施工组织设计",
            "outline": ["第1章", "第2章"],
            "provider_chain": [{"provider": "openai", "model": "ChatGPT-5.4", "api_key": "sk-a"}],
            "_variant_ids": [1, 2],
        }
        payload_b = {
            "topic": "施工组织设计",
            "outline": ["第1章", "第2章"],
            "provider_chain": [{"provider": "openai", "model": "ChatGPT-5.4", "api_key": "sk-b"}],
            "_variant_plan": [{"variant_id": 9, "logic_template_id": "A"}],
        }

        assert job_store.compute_job_signature(payload_a) == job_store.compute_job_signature(payload_b)

    def test_compute_job_signature_ignores_request_and_trace_ids(self):
        from backend.zhifei_autoplan import job_store

        payload_a = {
            "topic": "施工组织设计",
            "project_id": "p1",
            "outline": ["第1章", "第2章"],
            "request_id": "trace-a",
            "trace_id": "trace-a",
        }
        payload_b = {
            "topic": "施工组织设计",
            "project_id": "p1",
            "outline": ["第1章", "第2章"],
            "request_id": "trace-b",
            "trace_id": "trace-b",
        }

        assert job_store.compute_job_signature(payload_a) == job_store.compute_job_signature(payload_b)

    def test_find_reusable_job_prefers_recent_matching_record(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        artifact = tmp_path / "result.docx"
        artifact.write_text("ok", encoding="utf-8")

        payload = {"topic": "施工组织设计", "outline": ["第1章"], "generation_mode": "standard_auto"}
        signature = job_store.compute_job_signature(payload)

        with patch.object(job_store, "JOB_DIR", job_dir):
            old_id = job_store.create_job({"topic": "旧任务"}, request_signature="other")
            job_store.update_job(old_id, status="done", result={"docx": str(artifact)})

            job_id = job_store.create_job(payload, request_signature=signature)
            job_store.update_job(job_id, status="running")

            found = job_store.find_reusable_job(signature, statuses=("queued", "running", "done"), max_age_seconds=3600)
            assert found is not None
            assert found["job_id"] == job_id

    def test_find_reusable_job_skips_done_record_without_artifacts(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        payload = {"topic": "施工组织设计", "outline": ["第1章"], "generation_mode": "standard_auto"}
        signature = job_store.compute_job_signature(payload)

        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job(payload, request_signature=signature)
            job_store.update_job(job_id, status="done", result={"docx": str(tmp_path / "missing.docx")})

            assert job_store.find_reusable_job(signature, statuses=("done",), max_age_seconds=3600) is None

    def test_discover_recent_jobs_keeps_running_and_done_with_artifacts(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        artifact = tmp_path / "result.docx"
        artifact.write_text("ok", encoding="utf-8")

        with patch.object(job_store, "JOB_DIR", job_dir):
            done_missing = job_store.create_job({"topic": "缺失结果"})
            job_store.update_job(done_missing, status="done", result={"docx": str(tmp_path / "missing.docx")})

            done_ok = job_store.create_job({"topic": "已有成品"})
            job_store.update_job(done_ok, status="done", result={"docx": str(artifact)})

            running_id = job_store.create_job({"topic": "进行中任务"})
            job_store.update_job(running_id, status="running")

            rows = job_store.discover_recent_jobs(limit=4, statuses=("queued", "running", "done"), max_age_seconds=3600)
            ids = [str(r.get("job_id") or "") for r in rows]

            assert running_id in ids
            assert done_ok in ids
            assert done_missing not in ids

    def test_discover_recent_jobs_marks_stale_running_job_failed(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        old_ts = time.time() - 600

        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"topic": "超时任务"})
            job_store.update_job(job_id, status="running", heartbeat_at=old_ts, worker={"pid": None})

            rows = job_store.discover_recent_jobs(limit=4, statuses=("running",), max_age_seconds=3600, lease_seconds=120)

            assert rows == []
            rec = job_store.get_job(job_id) or {}
            assert rec.get("status") == "failed"


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
            rec = {"job_id": "test123", "status": "queued"}
            job_store._write_job(rec)
            
            job_file = job_dir / "test123.json"
            assert job_file.exists()

    def test_write_job_content(self, tmp_path):
        """Test _write_job writes correct content."""
        from backend.zhifei_autoplan import job_store
        
        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        
        with patch.object(job_store, 'JOB_DIR', job_dir):
            rec = {"job_id": "test123", "status": "running", "payload": {"a": 1}}
            job_store._write_job(rec)
            
            job_file = job_dir / "test123.json"
            loaded = json.loads(job_file.read_text(encoding="utf-8"))
            assert loaded == rec

    def test_write_job_chinese_content(self, tmp_path):
        """Test _write_job handles Chinese content."""
        from backend.zhifei_autoplan import job_store
        
        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        
        with patch.object(job_store, 'JOB_DIR', job_dir):
            rec = {"job_id": "test123", "payload": {"名称": "施工组织设计"}}
            job_store._write_job(rec)
            
            job_file = job_dir / "test123.json"
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
            rec1 = {"job_id": "test123", "status": "queued"}
            job_store._write_job(rec1)
            
            rec2 = {"job_id": "test123", "status": "done"}
            job_store._write_job(rec2)
            
            job_file = job_dir / "test123.json"
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
            user1_jobs = [
                job_store.create_job({"n": i}, user_id=1) for i in range(3)
            ]
            user2_jobs = [
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


class TestRuntimeHousekeeping:
    """Tests for stale-runner reconciliation and archive cleanup."""

    def test_reconcile_marks_stale_running_job_failed(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        with patch.object(job_store, "JOB_DIR", job_dir):
            job_id = job_store.create_job({"action": "generate"})
            old_ts = time.time() - 3600
            job_store.update_job(
                job_id,
                status="running",
                heartbeat_at=old_ts,
                worker={"pid": None},
            )
            rec = job_store.reconcile_job_runtime(job_id, lease_seconds=120) or {}
            assert rec.get("status") == "failed"
            assert "stale_worker_timeout" in str(rec.get("error") or "")

    def test_mark_stale_running_jobs_counts_fixed(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        job_dir.mkdir()
        with patch.object(job_store, "JOB_DIR", job_dir):
            jid1 = job_store.create_job({"action": "a"})
            jid2 = job_store.create_job({"action": "b"})
            old_ts = time.time() - 1800
            job_store.update_job(jid1, status="running", heartbeat_at=old_ts, worker={"pid": None})
            job_store.update_job(jid2, status="running", heartbeat_at=old_ts, worker={"pid": None})
            fixed = job_store.mark_stale_running_jobs(lease_seconds=120, limit=10)
            assert fixed == 2

    def test_cleanup_jobs_archive_creates_tombstone(self, tmp_path):
        from backend.zhifei_autoplan import job_store

        job_dir = tmp_path / "jobs"
        archive_dir = tmp_path / "archive"
        job_dir.mkdir()
        with patch.object(job_store, "JOB_DIR", job_dir), patch.object(job_store, "ARCHIVE_DIR", archive_dir):
            job_id = job_store.create_job({"action": "archive_test"})
            job_file = job_dir / f"{job_id}.json"
            rec = json.loads(job_file.read_text(encoding="utf-8"))
            rec["updated_at"] = time.time() - 10 * 24 * 3600
            rec["status"] = "done"
            job_file.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            removed = job_store.cleanup_jobs(older_than_seconds=7 * 24 * 3600, archive=True)
            assert removed == 1
            tomb = job_dir / f"{job_id}.archived.json"
            assert tomb.exists()
            archived = json.loads(tomb.read_text(encoding="utf-8"))
            assert archived.get("job_id") == job_id
            assert str(archived.get("archived_at") or "").endswith(".zip")
