from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class GeneratePreparedPayload:
    payload: dict[str, Any]
    request_signature: str


def prepare_generate_payload(
    *,
    raw_payload: dict[str, Any],
    prepare_runtime_payload_fn: Callable[[dict[str, Any]], dict[str, Any]],
    attach_contract_stamp_fn: Callable[[dict[str, Any]], Any],
    compute_job_signature_fn: Callable[[dict[str, Any]], str],
) -> GeneratePreparedPayload:
    payload = prepare_runtime_payload_fn(raw_payload)
    attach_contract_stamp_fn(payload)
    request_signature = compute_job_signature_fn(payload)
    return GeneratePreparedPayload(payload=payload, request_signature=request_signature)
