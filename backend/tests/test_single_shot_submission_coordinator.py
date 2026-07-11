from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect
import json
import re

import pytest

import image_generation.runtime.single_shot_submission_coordinator as coordinator_module
from image_generation.runtime.single_shot_submission_authorization import (
    build_single_shot_submission_authorization_envelope,
)
from image_generation.runtime.single_shot_submission_coordinator import (
    dispatch_single_shot_submission,
)


WORKFLOW_ID = "qwen_image_text_to_image"
AUTHORIZATION_ID = "authorization-demo-001"
AUTHORIZED_AT = datetime(2026, 7, 10, 8, 0, tzinfo=timezone.utc)
EXPIRES_AT = datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
NOW_UTC = datetime(2026, 7, 10, 8, 30, tzinfo=timezone.utc)
PROMPT_ID = "prompt-demo-001"
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _payload() -> dict:
    return {
        "payload_type": "comfyui_api_prompt_payload",
        "payload_version": "027n-r12-a",
        "project_id": "project-demo",
        "template_id": "template-demo",
        "workflow_id": WORKFLOW_ID,
        "api_prompt": {
            "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "施工现场正向提示词"}},
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "水印，模糊"}},
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 7,
                    "steps": 8,
                    "cfg": 1,
                    "sampler_name": "euler",
                    "scheduler": "simple",
                },
            },
            "4": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {"width": 1024, "height": 768, "batch_size": 1},
            },
            "5": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "project-demo__template-demo__seed-7",
                    "images": ["3", 0],
                },
            },
        },
        "candidate_seed": 7,
        "expected_output_count": 1,
        "output_prefix": "project-demo__template-demo__seed-7",
        "runtime_execution_authorized": False,
        "submission_authorized": False,
    }


def _authorization_record() -> dict:
    return {
        "authorization_id": AUTHORIZATION_ID,
        "authorized_by": "reviewer-demo",
        "authorized_at": "2026-07-10T08:00:00Z",
        "expires_at": "2026-07-10T09:00:00+00:00",
        "reason": "批准一次本地单图提交",
        "scope": "qwen_image_text_to_image_single_image",
    }


def _envelope() -> dict:
    return build_single_shot_submission_authorization_envelope(
        _payload(),
        _authorization_record(),
    )


class _FakeClock:
    def __init__(self, events: list[str], now: datetime) -> None:
        self.events = events
        self.now = now
        self.call_count = 0

    def now_utc(self) -> datetime:
        self.events.append("clock")
        self.call_count += 1
        return self.now


class _FakeConsumptionLedger:
    def __init__(
        self,
        events: list[str],
        existing_claims: dict[str, str] | None = None,
        mark_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.claims = dict(existing_claims or {})
        self.mark_error = mark_error
        self.claim_calls: list[tuple[str, str]] = []
        self.mark_calls: list[tuple[str, str]] = []
        self.release_calls: list[str] = []

    def claim(self, authorization_id: str, payload_sha256: str) -> bool:
        self.events.append("claim")
        self.claim_calls.append((authorization_id, payload_sha256))
        if authorization_id in self.claims:
            return False
        self.claims[authorization_id] = payload_sha256
        return True

    def mark_submitted(self, authorization_id: str, prompt_id: str) -> None:
        self.events.append("mark_submitted")
        self.mark_calls.append((authorization_id, prompt_id))
        if self.mark_error is not None:
            raise self.mark_error

    def release(self, authorization_id: str) -> None:
        self.events.append("release")
        self.release_calls.append(authorization_id)
        self.claims.pop(authorization_id, None)


class _FakeServiceHealthProbe:
    def __init__(self, events: list[str], healthy: bool) -> None:
        self.events = events
        self.healthy = healthy
        self.call_count = 0

    def check(self) -> bool:
        self.events.append("health")
        self.call_count += 1
        return self.healthy


class _FakeQueueStateProbe:
    def __init__(self, events: list[str], state: dict) -> None:
        self.events = events
        self.state = deepcopy(state)
        self.call_count = 0

    def get_state(self) -> dict:
        self.events.append("queue")
        self.call_count += 1
        return deepcopy(self.state)


class _FakeSubmitClient:
    def __init__(
        self,
        events: list[str],
        response: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.response = {"prompt_id": PROMPT_ID} if response is None else response
        self.error = error
        self.calls: list[dict] = []

    def submit(self, api_prompt: dict) -> dict:
        self.events.append("submit")
        self.calls.append(api_prompt)
        if self.error is not None:
            raise self.error
        return deepcopy(self.response)


class _Ports:
    def __init__(
        self,
        *,
        now: datetime = NOW_UTC,
        healthy: bool = True,
        queue_state: dict | None = None,
        existing_claims: dict[str, str] | None = None,
        submit_response: dict | None = None,
        submit_error: Exception | None = None,
        mark_error: Exception | None = None,
    ) -> None:
        self.events: list[str] = []
        self.clock = _FakeClock(self.events, now)
        self.consumption_ledger = _FakeConsumptionLedger(
            self.events,
            existing_claims,
            mark_error,
        )
        self.service_health_probe = _FakeServiceHealthProbe(self.events, healthy)
        self.queue_state_probe = _FakeQueueStateProbe(
            self.events,
            {"running": [], "pending": []} if queue_state is None else queue_state,
        )
        self.submit_client = _FakeSubmitClient(
            self.events,
            response=submit_response,
            error=submit_error,
        )


def _dispatch(envelope: dict, ports: _Ports) -> dict:
    return dispatch_single_shot_submission(
        envelope,
        clock=ports.clock,
        consumption_ledger=ports.consumption_ledger,
        service_health_probe=ports.service_health_probe,
        queue_state_probe=ports.queue_state_probe,
        submit_client=ports.submit_client,
    )


def _assert_receipt_has_no_forbidden_runtime_content(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower()
            assert normalized_key not in {"api_prompt", "payload_snapshot"}
            assert not any(
                marker in normalized_key
                for marker in ("token", "secret", "credential", "endpoint")
            )
            assert normalized_key != "path" and not normalized_key.endswith("_path")
            _assert_receipt_has_no_forbidden_runtime_content(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _assert_receipt_has_no_forbidden_runtime_content(child)
    elif isinstance(value, str):
        normalized_value = value.strip()
        lowered = normalized_value.lower()
        assert "localhost" not in lowered
        assert "127.0.0.1" not in lowered
        assert "[::1]" not in lowered
        assert "://" not in lowered
        assert not normalized_value.startswith(("/", "~/", "~\\", "\\"))
        assert not lowered.startswith("file:")
        assert _WINDOWS_ABSOLUTE_PATH.match(normalized_value) is None


def test_dispatches_valid_envelope_once_in_required_order_and_returns_safe_receipt(
    monkeypatch,
) -> None:
    envelope = _envelope()
    original_envelope = deepcopy(envelope)
    ports = _Ports(
        submit_response={
            "prompt_id": PROMPT_ID,
            "token": "synthetic-token",
            "endpoint": "synthetic-endpoint",
            "model_path": "/synthetic/model",
            "output_path": "/synthetic/output",
        }
    )
    real_validator = coordinator_module.validate_single_shot_submission_authorization_envelope
    validator_calls: list[dict] = []

    def validate_spy(value: dict) -> None:
        ports.events.append("validate")
        validator_calls.append(value)
        real_validator(value)

    monkeypatch.setattr(
        coordinator_module,
        "validate_single_shot_submission_authorization_envelope",
        validate_spy,
    )

    receipt = _dispatch(envelope, ports)

    assert validator_calls == [envelope]
    assert ports.events == [
        "validate",
        "clock",
        "health",
        "queue",
        "claim",
        "submit",
        "mark_submitted",
    ]
    assert ports.clock.call_count == 1
    assert ports.service_health_probe.call_count == 1
    assert ports.queue_state_probe.call_count == 1
    assert ports.consumption_ledger.claim_calls == [
        (AUTHORIZATION_ID, envelope["payload_sha256"])
    ]
    assert len(ports.submit_client.calls) == 1
    assert ports.consumption_ledger.mark_calls == [(AUTHORIZATION_ID, PROMPT_ID)]
    assert ports.consumption_ledger.release_calls == []

    submitted_prompt = ports.submit_client.calls[0]
    snapshot_prompt = envelope["payload_snapshot"]["api_prompt"]
    assert submitted_prompt == snapshot_prompt
    assert submitted_prompt is not snapshot_prompt
    assert submitted_prompt["1"] is not snapshot_prompt["1"]
    assert submitted_prompt["1"]["inputs"] is not snapshot_prompt["1"]["inputs"]
    assert envelope == original_envelope

    expected_receipt_fields = {
        "receipt_type": "single_shot_submission_dispatch_receipt",
        "receipt_version": "027n-r14-a",
        "authorization_id": AUTHORIZATION_ID,
        "payload_sha256": envelope["payload_sha256"],
        "workflow_id": WORKFLOW_ID,
        "prompt_id": PROMPT_ID,
        "submission_count": 1,
        "expected_output_count": 1,
        "submission_status": "submitted",
        "result_monitoring_required": True,
        "generation_completed": False,
    }
    for key, expected in expected_receipt_fields.items():
        assert receipt[key] == expected
    assert set(receipt) == set(expected_receipt_fields) | {"submitted_at"}
    submitted_at = datetime.fromisoformat(receipt["submitted_at"].replace("Z", "+00:00"))
    assert submitted_at == NOW_UTC
    assert submitted_at.utcoffset() == timedelta(0)
    assert json.loads(json.dumps(receipt, ensure_ascii=False)) == receipt
    _assert_receipt_has_no_forbidden_runtime_content(receipt)

    monkeypatch.setattr(
        coordinator_module,
        "validate_single_shot_submission_authorization_envelope",
        real_validator,
    )
    equivalent_receipt = _dispatch(_envelope(), _Ports())
    assert equivalent_receipt == receipt


@pytest.mark.parametrize(
    "mutate",
    [
        lambda envelope: envelope["execution_limits"].__setitem__("workflow_id", "other"),
        lambda envelope: envelope["payload_snapshot"].__setitem__("workflow_id", "other"),
        lambda envelope: envelope["execution_limits"].__setitem__("max_submissions", 2),
        lambda envelope: envelope["execution_limits"].__setitem__("max_submissions", True),
        lambda envelope: envelope["execution_limits"].__setitem__("max_outputs", 2),
        lambda envelope: envelope["execution_limits"].__setitem__("batch_size", 2),
        lambda envelope: envelope["payload_snapshot"].__setitem__("expected_output_count", 2),
        lambda envelope: envelope.__setitem__("runtime_execution_authorized", False),
        lambda envelope: envelope.__setitem__("submission_authorized", False),
    ],
    ids=[
        "workflow-id",
        "payload-workflow-id",
        "max-submissions",
        "boolean-max-submissions",
        "max-outputs",
        "batch-size",
        "expected-output-count",
        "runtime-authorization",
        "submission-authorization",
    ],
)
def test_rechecks_single_shot_limits_before_clock(monkeypatch, mutate) -> None:
    envelope = _envelope()
    mutate(envelope)
    validator_calls: list[dict] = []
    ports = _Ports()
    monkeypatch.setattr(
        coordinator_module,
        "validate_single_shot_submission_authorization_envelope",
        lambda value: validator_calls.append(value),
    )

    with pytest.raises(ValueError):
        _dispatch(envelope, ports)

    assert validator_calls == [envelope]
    assert ports.events == []


@pytest.mark.parametrize(
    "now",
    [
        AUTHORIZED_AT - timedelta(microseconds=1),
        EXPIRES_AT,
        NOW_UTC.replace(tzinfo=None),
        NOW_UTC.astimezone(timezone(timedelta(hours=8))),
    ],
    ids=["before-authorized-at", "at-expiry", "naive", "non-utc"],
)
def test_rejects_invalid_clock_or_authorization_window_before_health(now) -> None:
    ports = _Ports(now=now)

    with pytest.raises(ValueError):
        _dispatch(_envelope(), ports)

    assert ports.events == ["clock"]
    assert ports.clock.call_count == 1
    assert ports.service_health_probe.call_count == 0
    assert ports.queue_state_probe.call_count == 0
    assert ports.consumption_ledger.claim_calls == []
    assert ports.submit_client.calls == []


@pytest.mark.parametrize("healthy", [False, 1], ids=["false", "truthy-non-boolean"])
def test_rejects_unhealthy_service_before_queue_or_claim(healthy) -> None:
    ports = _Ports(healthy=healthy)

    with pytest.raises(ValueError):
        _dispatch(_envelope(), ports)

    assert ports.events == ["clock", "health"]
    assert ports.queue_state_probe.call_count == 0
    assert ports.consumption_ledger.claim_calls == []
    assert ports.submit_client.calls == []


@pytest.mark.parametrize(
    "queue_state",
    [
        {"running": [{"prompt_id": "running-prompt"}], "pending": []},
        {"running": [], "pending": [{"prompt_id": "pending-prompt"}]},
    ],
    ids=["running", "pending"],
)
def test_rejects_nonempty_queue_before_claim(queue_state) -> None:
    ports = _Ports(queue_state=queue_state)

    with pytest.raises(ValueError):
        _dispatch(_envelope(), ports)

    assert ports.events == ["clock", "health", "queue"]
    assert ports.consumption_ledger.claim_calls == []
    assert ports.submit_client.calls == []


@pytest.mark.parametrize("claim_state", ["consumed", "hash-conflict"])
def test_rejects_consumed_or_conflicting_claim_before_submit(claim_state) -> None:
    envelope = _envelope()
    existing_hash = (
        envelope["payload_sha256"] if claim_state == "consumed" else "f" * 64
    )
    original_claims = {AUTHORIZATION_ID: existing_hash}
    ports = _Ports(existing_claims=original_claims)

    with pytest.raises(ValueError):
        _dispatch(envelope, ports)

    assert ports.events == ["clock", "health", "queue", "claim"]
    assert ports.consumption_ledger.claim_calls == [
        (AUTHORIZATION_ID, envelope["payload_sha256"])
    ]
    assert ports.consumption_ledger.claims == original_claims
    assert ports.submit_client.calls == []
    assert ports.consumption_ledger.mark_calls == []
    assert ports.consumption_ledger.release_calls == []


def test_submit_failure_is_not_retried_and_claim_remains_consumed() -> None:
    envelope = _envelope()
    ports = _Ports(submit_error=RuntimeError("synthetic submit failure"))

    with pytest.raises(RuntimeError, match="synthetic submit failure"):
        _dispatch(envelope, ports)

    assert ports.events == ["clock", "health", "queue", "claim", "submit"]
    assert len(ports.submit_client.calls) == 1
    assert ports.consumption_ledger.claims == {
        AUTHORIZATION_ID: envelope["payload_sha256"]
    }
    assert ports.consumption_ledger.mark_calls == []
    assert ports.consumption_ledger.release_calls == []


def test_mark_failure_is_not_retried_and_claim_remains_consumed() -> None:
    envelope = _envelope()
    ports = _Ports(mark_error=RuntimeError("synthetic mark failure"))

    with pytest.raises(RuntimeError, match="synthetic mark failure"):
        _dispatch(envelope, ports)

    assert ports.events == [
        "clock",
        "health",
        "queue",
        "claim",
        "submit",
        "mark_submitted",
    ]
    assert len(ports.submit_client.calls) == 1
    assert ports.consumption_ledger.mark_calls == [(AUTHORIZATION_ID, PROMPT_ID)]
    assert ports.consumption_ledger.claims == {
        AUTHORIZATION_ID: envelope["payload_sha256"]
    }
    assert ports.consumption_ledger.release_calls == []


@pytest.mark.parametrize(
    "submit_response",
    [
        {},
        {"prompt_id": ""},
        {"prompt_id": " "},
        {"prompt_id": None},
        {"prompt_id": "/tmp/output"},
        {"prompt_id": "http://localhost/prompt"},
        {"prompt_id": "localhost"},
        {"prompt_id": "api-token-001"},
        {"prompt_id": "client-secret-001"},
        {"prompt_id": "service-endpoint-001"},
    ],
    ids=[
        "missing",
        "empty",
        "whitespace",
        "non-string",
        "path",
        "address",
        "local-name",
        "token",
        "secret",
        "endpoint",
    ],
)
def test_rejects_invalid_prompt_id_without_release(submit_response) -> None:
    envelope = _envelope()
    ports = _Ports(submit_response=submit_response)

    with pytest.raises(ValueError):
        _dispatch(envelope, ports)

    assert ports.events == ["clock", "health", "queue", "claim", "submit"]
    assert len(ports.submit_client.calls) == 1
    assert ports.consumption_ledger.claims == {
        AUTHORIZATION_ID: envelope["payload_sha256"]
    }
    assert ports.consumption_ledger.mark_calls == []
    assert ports.consumption_ledger.release_calls == []


def test_implementation_has_no_system_time_file_environment_or_network_access() -> None:
    source = inspect.getsource(coordinator_module)
    tree = ast.parse(source)
    forbidden_module_roots = {
        "http",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "time",
        "urllib",
    }
    forbidden_calls = {
        "__import__",
        "getenv",
        "open",
        "read_bytes",
        "read_text",
        "today",
        "time",
        "urlopen",
        "utcnow",
        "write_bytes",
        "write_text",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".", 1)[0] not in forbidden_module_roots
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            module_root = (node.module or "").split(".", 1)[0]
            assert module_root not in forbidden_module_roots
        elif isinstance(node, ast.Attribute):
            assert node.attr != "environ"
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls | {"now", "open"}
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            assert "localhost" not in lowered
            assert "127.0.0.1" not in lowered
            assert "[::1]" not in lowered
            assert "/prompt" not in lowered
            assert "http://" not in lowered
            assert "https://" not in lowered
            assert "endpoint" not in lowered
            assert "requests" not in lowered
            assert "curl" not in lowered
