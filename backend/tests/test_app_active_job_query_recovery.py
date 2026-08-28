from __future__ import annotations

import ast
import re
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


APP_PATH = Path(__file__).resolve().parents[2] / "app.py"
JOB_ID = "a" * 32


class _FakeStreamlit:
    def __init__(self, query_params: dict[str, Any] | None = None) -> None:
        self.query_params = dict(query_params or {})
        self.session_state: dict[str, Any] = {}
        self.messages: list[tuple[str, Any]] = []

    def info(self, value: Any) -> None:
        self.messages.append(("info", value))

    def warning(self, value: Any) -> None:
        self.messages.append(("warning", value))

    def error(self, value: Any) -> None:
        self.messages.append(("error", value))

    def caption(self, value: Any) -> None:
        self.messages.append(("caption", value))

    def dataframe(self, value: Any, **_kwargs: Any) -> None:
        self.messages.append(("dataframe", value))


def _load_helpers(stub: _FakeStreamlit, get_json: Any) -> SimpleNamespace:
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))
    wanted = {
        "_normalize_runtime_job_id",
        "_query_runtime_job_id",
        "_persist_active_job_query",
        "_clear_active_job_query",
        "_active_job_from_snapshot",
        "_restore_active_job_from_query",
        "_finish_active_job",
        "_poll_active_job",
    }
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace: dict[str, Any] = {
        "Any": Any,
        "re": re,
        "time": time,
        "st": stub,
        "_get_json": get_json,
        "_append_log": lambda *_args, **_kwargs: None,
        "_render_progress": lambda *_args, **_kwargs: None,
        "_collect_job_result": lambda *_args, **_kwargs: {"result_json": b"{}"},
        "build_job_activity": lambda job: job,
        "activity_html": lambda view: str(view),
    }
    exec(
        compile(ast.Module(body=selected, type_ignores=[]), str(APP_PATH), "exec"),
        namespace,
    )
    return SimpleNamespace(**namespace)


def test_async_job_id_is_the_only_value_persisted_to_query() -> None:
    stub = _FakeStreamlit()
    helpers = _load_helpers(stub, lambda *_args, **_kwargs: {})

    assert helpers._persist_active_job_query(JOB_ID) is True

    assert stub.query_params == {"job_id": JOB_ID}
    assert "key" not in str(stub.query_params).lower()


def test_refresh_restores_minimal_active_job_from_authenticated_snapshot() -> None:
    stub = _FakeStreamlit({"job_id": JOB_ID})
    calls: list[dict[str, Any]] = []

    def _get_json(base_url: str, path: str, actions_key: str, **kwargs: Any) -> dict[str, Any]:
        calls.append(
            {
                "base_url": base_url,
                "path": path,
                "actions_key": actions_key,
                **kwargs,
            }
        )
        return {
            "job": {
                "job_id": JOB_ID,
                "status": "running",
                "project_id": "project-from-snapshot",
                "variants": 3,
                "created_at": 123.0,
                "progress": {"percent": 42},
                "agent_runtime": {"variants_total": 3},
                "ignored_private_field": "must-not-enter-session",
            }
        }

    helpers = _load_helpers(stub, _get_json)

    assert helpers._restore_active_job_from_query("http://127.0.0.1:8010", "actions-secret") is True

    assert calls == [
        {
            "base_url": "http://127.0.0.1:8010",
            "path": "/actions/job_status",
            "actions_key": "actions-secret",
            "params": {"job_id": JOB_ID},
            "timeout": 15,
        }
    ]
    assert stub.query_params == {"job_id": JOB_ID}
    assert stub.session_state["active_job"] == {
        "job_id": JOB_ID,
        "status": "running",
        "project_id": "project-from-snapshot",
        "variants": 3,
        "started_at": 123.0,
        "progress": {"percent": 42},
        "agent_runtime": {"variants_total": 3},
        "restored_from_url": True,
    }
    assert "actions-secret" not in str(stub.session_state)
    assert "ignored_private_field" not in str(stub.session_state)


def test_invalid_query_job_id_fails_closed_without_backend_request() -> None:
    stub = _FakeStreamlit({"job_id": "../../not-a-job"})

    def _unexpected(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("invalid URL ids must not reach the backend")

    helpers = _load_helpers(stub, _unexpected)

    assert helpers._restore_active_job_from_query("http://127.0.0.1:8010", "secret") is False
    assert stub.query_params == {}
    assert stub.session_state.get("active_job") is None


def test_backend_outage_does_not_permanently_disable_query_recovery() -> None:
    stub = _FakeStreamlit({"job_id": JOB_ID})
    calls = 0

    def _get_json(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("backend temporarily unavailable")
        return {"job": {"job_id": JOB_ID, "status": "running"}}

    helpers = _load_helpers(stub, _get_json)

    try:
        helpers._restore_active_job_from_query("http://127.0.0.1:8010", "secret")
    except ConnectionError:
        pass
    else:
        raise AssertionError("first recovery attempt must expose the outage")

    assert "_active_job_query_restore_attempted" not in stub.session_state
    assert helpers._restore_active_job_from_query(
        "http://127.0.0.1:8010", "secret"
    ) is True
    assert calls == 2


def test_no_query_param_keeps_new_session_untouched() -> None:
    stub = _FakeStreamlit()

    def _unexpected(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("a new session must not query an arbitrary job")

    helpers = _load_helpers(stub, _unexpected)

    assert helpers._restore_active_job_from_query("http://127.0.0.1:8010", "secret") is False
    assert stub.session_state == {}


def test_terminal_poll_clears_active_job_and_query_param() -> None:
    stub = _FakeStreamlit({"job_id": JOB_ID})
    stub.session_state["active_job"] = {
        "job_id": JOB_ID,
        "status": "running",
        "project_id": "project-1",
        "variants": 1,
    }

    def _get_json(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "job": {
                "job_id": JOB_ID,
                "status": "failed",
                "progress": {"percent": 61},
                "error": {
                    "code": "MODEL_CHAIN_EXHAUSTED",
                    "message": "模型链不可用。",
                    "action": "请检查供应商准入状态。",
                },
            }
        }

    helpers = _load_helpers(stub, _get_json)

    helpers._poll_active_job("http://127.0.0.1:8010", "secret", 1.0)

    assert stub.session_state["active_job"] is None
    assert stub.query_params == {}


def test_snapshot_accepts_only_supported_recovery_states() -> None:
    stub = _FakeStreamlit()
    helpers = _load_helpers(stub, lambda *_args, **_kwargs: {})

    for raw_status, expected_status in (
        ("queued", "queued"),
        ("running", "running"),
        ("interrupted", "interrupted_recoverable"),
        ("interrupted_recoverable", "interrupted_recoverable"),
        ("failed", "failed"),
        ("succeeded", "succeeded"),
        ("done", "succeeded"),
    ):
        active = helpers._active_job_from_snapshot(
            {"job_id": JOB_ID, "status": raw_status},
            JOB_ID,
        )
        assert active is not None
        assert active["status"] == expected_status


def test_snapshot_mismatch_or_unknown_status_is_not_restored() -> None:
    for snapshot in (
        {"job_id": "b" * 32, "status": "running"},
        {"job_id": JOB_ID, "status": "cancelled"},
    ):
        stub = _FakeStreamlit({"job_id": JOB_ID})
        helpers = _load_helpers(stub, lambda *_args, **_kwargs: {"job": snapshot})

        assert helpers._restore_active_job_from_query("http://127.0.0.1:8010", "secret") is False
        assert stub.query_params == {}
        assert stub.session_state.get("active_job") is None
