"""Pure dependency-injected coordinator for one authorized submission."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Protocol

from image_generation.runtime.single_shot_submission_authorization import (
    _validate_no_forbidden_content,
    validate_single_shot_submission_authorization_envelope,
)
from image_generation.workflows.project_prompt_payload_adapter import WORKFLOW_ID


RECEIPT_TYPE = "single_shot_submission_dispatch_receipt"
RECEIPT_VERSION = "027n-r14-a"


class _ClockPort(Protocol):
    def now_utc(self) -> datetime: ...


class _ConsumptionLedgerPort(Protocol):
    def claim(self, authorization_id: str, payload_sha256: str) -> bool: ...

    def mark_submitted(self, authorization_id: str, prompt_id: str) -> None: ...


class _ServiceHealthProbePort(Protocol):
    def check(self) -> bool: ...


class _QueueStateProbePort(Protocol):
    def get_state(self) -> dict: ...


class _SubmitClientPort(Protocol):
    def submit(self, api_prompt: dict) -> dict: ...


def dispatch_single_shot_submission(
    envelope: dict,
    *,
    clock: _ClockPort,
    consumption_ledger: _ConsumptionLedgerPort,
    service_health_probe: _ServiceHealthProbePort,
    queue_state_probe: _QueueStateProbePort,
    submit_client: _SubmitClientPort,
) -> dict:
    """Validate, consume, and dispatch one authorized prompt through injected ports."""

    validate_single_shot_submission_authorization_envelope(envelope)
    _validate_dispatch_limits(envelope)

    now_utc = clock.now_utc()
    _validate_clock_value(now_utc)
    authorization = envelope["authorization"]
    authorized_at = _parse_validated_utc_timestamp(authorization["authorized_at"])
    expires_at = _parse_validated_utc_timestamp(authorization["expires_at"])
    if now_utc < authorized_at:
        raise ValueError("authorization is not active yet")
    if now_utc >= expires_at:
        raise ValueError("authorization has expired")

    if service_health_probe.check() is not True:
        raise ValueError("service health check must be true")

    queue_state = queue_state_probe.get_state()
    _validate_empty_queue(queue_state)

    payload_snapshot = envelope["payload_snapshot"]
    api_prompt = deepcopy(payload_snapshot["api_prompt"])
    authorization_id = envelope["authorization_id"]
    payload_sha256 = envelope["payload_sha256"]
    if consumption_ledger.claim(authorization_id, payload_sha256) is not True:
        raise ValueError("authorization claim failed")

    submission = submit_client.submit(api_prompt)
    if not isinstance(submission, dict):
        raise ValueError("submission result must be an object")
    prompt_id = submission.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id.strip():
        raise ValueError("submission result prompt_id must be a non-empty string")
    _validate_prompt_id(prompt_id)

    consumption_ledger.mark_submitted(authorization_id, prompt_id)
    return {
        "receipt_type": RECEIPT_TYPE,
        "receipt_version": RECEIPT_VERSION,
        "authorization_id": authorization_id,
        "payload_sha256": payload_sha256,
        "workflow_id": WORKFLOW_ID,
        "prompt_id": prompt_id,
        "submission_count": 1,
        "expected_output_count": 1,
        "submission_status": "submitted",
        "submitted_at": _format_utc_timestamp(now_utc),
        "result_monitoring_required": True,
        "generation_completed": False,
    }


def _validate_dispatch_limits(envelope: dict) -> None:
    limits = envelope["execution_limits"]
    payload_snapshot = envelope["payload_snapshot"]
    if (
        limits.get("workflow_id") != WORKFLOW_ID
        or payload_snapshot.get("workflow_id") != WORKFLOW_ID
    ):
        raise ValueError(f"workflow_id must be {WORKFLOW_ID}")
    for field in ("max_submissions", "max_outputs", "batch_size"):
        if type(limits.get(field)) is not int or limits[field] != 1:
            raise ValueError(f"execution_limits.{field} must be 1")
    if (
        type(payload_snapshot.get("expected_output_count")) is not int
        or payload_snapshot["expected_output_count"] != 1
    ):
        raise ValueError("payload expected_output_count must be 1")
    if envelope.get("runtime_execution_authorized") is not True:
        raise ValueError("runtime_execution_authorized must be true")
    if envelope.get("submission_authorized") is not True:
        raise ValueError("submission_authorized must be true")


def _validate_clock_value(value: object) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError("clock.now_utc must return a timezone-aware UTC datetime")


def _parse_validated_utc_timestamp(value: str) -> datetime:
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _validate_empty_queue(queue_state: object) -> None:
    if not isinstance(queue_state, dict):
        raise ValueError("queue state must be an object")
    running = queue_state.get("running")
    pending = queue_state.get("pending")
    if not isinstance(running, list) or not isinstance(pending, list):
        raise ValueError("queue state must contain running and pending lists")
    if running or pending:
        raise ValueError("queue must be empty")


def _validate_prompt_id(value: str) -> None:
    if value != value.strip() or any(
        not (character.isalnum() or character in "-_") for character in value
    ):
        raise ValueError("submission result prompt_id must be a safe identifier")
    _validate_no_forbidden_content({value: ""}, "submission result prompt_id")


def _format_utc_timestamp(value: datetime) -> str:
    formatted = value.isoformat()
    return f"{formatted[:-6]}Z" if formatted.endswith("+00:00") else formatted
