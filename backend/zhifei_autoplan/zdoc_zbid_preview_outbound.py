from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib import error, request


ADAPTER_NAME = "zdoc_zbid_preview_only_outbound"
OUTBOUND_ENABLED_ENV = "ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED"
OUTBOUND_ENDPOINT_ENV = "ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT"
OUTBOUND_NETWORK_SEND_ENABLED_ENV = "ZDOC_ZBID_PREVIEW_ONLY_NETWORK_SEND_ENABLED"
ZBID_PREVIEW_ONLY_RECEIVER_PATH = "/local-llm/zdoc-preview-only/receive"
DEFAULT_SEND_TIMEOUT_SECONDS = 10.0

FORMAL_CHAIN_FALSE_FLAGS = {
    "formal_writeback_allowed": False,
    "review_apply_allowed": False,
    "docx_export_allowed": False,
    "zbid_writeback_allowed": False,
    "output_write_allowed": False,
    "calls_generate_route": False,
    "calls_export_docx_route": False,
    "calls_review_apply_route": False,
    "affects_zbid_writeback": False,
    "writes_output": False,
    "writes_job": False,
    "writes_export": False,
}

USER_VISIBLE_FALSE_FLAGS = {
    "generate_called": False,
    "export_docx_called": False,
    "review_apply_called": False,
    "zbid_writeback_called": False,
    "output_job_export_written": False,
}

NO_WRITE_FALSE_FLAGS = {
    **FORMAL_CHAIN_FALSE_FLAGS,
    **USER_VISIBLE_FALSE_FLAGS,
}
PreviewOnlySender = Callable[[str, dict[str, Any]], Mapping[str, Any]]


def _text(value: Any, *, limit: int = 12000) -> str:
    text = str(value or "").strip()
    if len(text) > limit:
        return text[:limit].rstrip()
    return text


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _append_unique(items: list[str], item: Any) -> None:
    value = _text(item, limit=240)
    if value and value not in items:
        items.append(value)


def _enabled(value: Any) -> bool:
    return _text(value, limit=20).lower() in {"1", "true", "yes", "on"}


def _targets_zbid_preview_receiver(endpoint: str) -> bool:
    clean_endpoint = endpoint.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    return clean_endpoint == ZBID_PREVIEW_ONLY_RECEIVER_PATH or clean_endpoint.endswith(
        ZBID_PREVIEW_ONLY_RECEIVER_PATH
    )


def _combined_blocked_reasons(*sources: Any) -> list[str]:
    reasons: list[str] = []
    for source in sources:
        if isinstance(source, dict):
            for reason in _list(source.get("blocked_reasons")):
                _append_unique(reasons, reason)
        else:
            for reason in _list(source):
                _append_unique(reasons, reason)
    return reasons


def _non_false_formal_chain_flags(*values: Any) -> list[str]:
    found: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key in NO_WRITE_FALSE_FLAGS and item is not False:
                    found.append(str(key))
                found.extend(_non_false_formal_chain_flags(item))
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                found.extend(_non_false_formal_chain_flags(item))
    return sorted(set(found))


def _read_response_body(raw: bytes) -> Any:
    if not raw:
        return {}
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw_response": text}


def _send_preview_only_payload(
    endpoint: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: float = DEFAULT_SEND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return {
                "status_code": response.status,
                "content_type": response.headers.get("content-type", ""),
                "body": _read_response_body(response.read()),
            }
    except error.HTTPError as exc:
        return {
            "status_code": exc.code,
            "content_type": exc.headers.get("content-type", ""),
            "body": _read_response_body(exc.read()),
        }


def _normalize_sender_response(response: Mapping[str, Any]) -> dict[str, Any]:
    status_code = response.get("status_code", response.get("http_status"))
    if isinstance(status_code, bool):
        status_code = None
    if isinstance(status_code, str) and status_code.isdigit():
        status_code = int(status_code)
    if not isinstance(status_code, int):
        status_code = None

    body = response.get("body", response.get("json", response.get("data", {})))
    if not isinstance(body, Mapping):
        body = {}

    return {
        "status_code": status_code,
        "body": dict(body),
        "content_type": _text(response.get("content_type"), limit=240),
    }


def _receiver_response_blocked_reasons(response: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    status_code = response.get("status_code")
    body = _dict(response.get("body"))
    if not isinstance(status_code, int) or not 200 <= status_code < 300:
        _append_unique(reasons, "zbid_preview_only_receiver_http_error")
    if _text(body.get("status"), limit=80).startswith("blocked"):
        _append_unique(reasons, "zbid_preview_only_receiver_blocked_payload")
    if body.get("receiver_accepted") is False:
        _append_unique(reasons, "zbid_preview_only_receiver_not_accepted")
    if body.get("preview_only") is not True:
        _append_unique(reasons, "zbid_preview_only_receiver_missing_preview_only")
    if body.get("no_write") is not True:
        _append_unique(reasons, "zbid_preview_only_receiver_missing_no_write")
    if body.get("no_evidence") is not True:
        _append_unique(reasons, "zbid_preview_only_receiver_missing_no_evidence")
    for flag in USER_VISIBLE_FALSE_FLAGS:
        if body.get(flag) is not False:
            _append_unique(reasons, f"zbid_preview_only_receiver_flag_not_false:{flag}")
    return reasons


def build_zdoc_zbid_preview_only_outbound_config(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    data = os.environ if env is None else env
    enabled = _enabled(data.get(OUTBOUND_ENABLED_ENV, ""))
    endpoint = _text(data.get(OUTBOUND_ENDPOINT_ENV, ""), limit=2000)
    network_send_enabled = _enabled(data.get(OUTBOUND_NETWORK_SEND_ENABLED_ENV, ""))
    receiver_endpoint_allowed = bool(endpoint) and _targets_zbid_preview_receiver(endpoint)

    if not enabled:
        status = "disabled"
        reasons = ["zdoc_zbid_preview_only_outbound_disabled"]
    elif not endpoint:
        status = "blocked_missing_endpoint"
        reasons = ["zdoc_zbid_preview_only_endpoint_missing"]
    elif not receiver_endpoint_allowed:
        status = "blocked_disallowed_endpoint"
        reasons = ["zdoc_zbid_preview_only_endpoint_not_receiver"]
    elif not network_send_enabled:
        status = "configured_not_sent"
        reasons = ["zdoc_zbid_preview_only_network_send_not_enabled"]
    else:
        status = "network_send_ready"
        reasons = []

    return {
        "adapter_name": ADAPTER_NAME,
        "enabled": enabled,
        "default_off": not network_send_enabled,
        "endpoint_configured": bool(endpoint),
        "endpoint": endpoint,
        "receiver_endpoint_allowed": receiver_endpoint_allowed,
        "network_send_explicitly_enabled": network_send_enabled,
        "status": status,
        "preview_only": True,
        "no_write": True,
        "metadata_only": True,
        "auto_send_allowed": False,
        "network_send_allowed": status == "network_send_ready",
        "network_send_attempted": False,
        "network_send_succeeded": False,
        "zbid_writeback_attempted": False,
        "blocked_reasons": reasons,
        **NO_WRITE_FALSE_FLAGS,
    }


def build_zdoc_zbid_preview_only_outbound_payload(
    *,
    preview_packet: dict[str, Any],
    validator_result: dict[str, Any],
    blocked_reasons: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    packet = _dict(preview_packet)
    validation = _dict(validator_result)
    reasons = _combined_blocked_reasons(blocked_reasons, packet, validation)

    if not isinstance(preview_packet, dict):
        _append_unique(reasons, "invalid_preview_packet_for_outbound")
    if not isinstance(validator_result, dict):
        _append_unique(reasons, "invalid_validator_result_for_outbound")

    return {
        "preview_packet": packet,
        "validator_result": validation,
        "blocked_reasons": reasons,
        **USER_VISIBLE_FALSE_FLAGS,
    }


def prepare_zdoc_zbid_preview_only_outbound(
    *,
    preview_packet: dict[str, Any],
    validator_result: dict[str, Any],
    blocked_reasons: list[str] | tuple[str, ...] | None = None,
    config: dict[str, Any] | None = None,
    sender: PreviewOnlySender | None = None,
) -> dict[str, Any]:
    resolved_config = (
        build_zdoc_zbid_preview_only_outbound_config() if config is None else dict(config)
    )
    payload = build_zdoc_zbid_preview_only_outbound_payload(
        preview_packet=preview_packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
    )
    config_reasons = _combined_blocked_reasons(resolved_config)
    payload_reasons = _combined_blocked_reasons(payload)
    send_blocking_reasons = list(config_reasons)
    for reason in payload_reasons:
        if reason.startswith("invalid_"):
            _append_unique(send_blocking_reasons, reason)
    reasons = _combined_blocked_reasons(payload, config_reasons)
    non_false_flags = _non_false_formal_chain_flags(
        preview_packet,
        validator_result,
        payload,
    )
    for flag in non_false_flags:
        _append_unique(reasons, f"formal_chain_flag_must_be_false:{flag}")
        _append_unique(send_blocking_reasons, f"formal_chain_flag_must_be_false:{flag}")

    result = {
        "ok": False,
        "adapter_name": ADAPTER_NAME,
        "outbound_status": resolved_config.get("status", "disabled"),
        "outbound_enabled": bool(resolved_config.get("enabled")),
        "default_off": bool(resolved_config.get("default_off", True)),
        "endpoint_configured": bool(resolved_config.get("endpoint_configured")),
        "endpoint": _text(resolved_config.get("endpoint"), limit=2000),
        "receiver_endpoint_allowed": bool(
            resolved_config.get("receiver_endpoint_allowed")
        ),
        "network_send_explicitly_enabled": bool(
            resolved_config.get("network_send_explicitly_enabled")
        ),
        "preview_only": True,
        "no_write": True,
        "metadata_only": True,
        "auto_send_allowed": False,
        "network_send_allowed": bool(resolved_config.get("network_send_allowed")),
        "network_send_attempted": False,
        "network_send_succeeded": False,
        "zbid_writeback_attempted": False,
        "produces_evidence": False,
        "produces_writeback": False,
        "writes_storage": False,
        "writes_scoring_basis": False,
        "writes_output_job_export": False,
        "calls_generate_route_runtime": False,
        "calls_export_docx_route_runtime": False,
        "calls_review_apply_route_runtime": False,
        "payload": payload,
        "blocked_reasons": reasons,
        **NO_WRITE_FALSE_FLAGS,
    }

    if send_blocking_reasons or not result["network_send_allowed"]:
        return result

    result["network_send_attempted"] = True
    outbound_sender = sender or _send_preview_only_payload
    try:
        raw_response = outbound_sender(result["endpoint"], payload)
    except Exception as exc:
        result["outbound_status"] = "send_failed"
        result["receiver_response"] = {}
        result["http_status"] = None
        result["error"] = _text(exc, limit=500)
        result["blocked_reasons"] = [
            *result["blocked_reasons"],
            "zdoc_zbid_preview_only_send_failed",
        ]
        return result

    response = _normalize_sender_response(raw_response)
    receiver_reasons = _receiver_response_blocked_reasons(response)
    result["receiver_response"] = response["body"]
    result["http_status"] = response["status_code"]
    result["content_type"] = response["content_type"]
    if receiver_reasons:
        result["outbound_status"] = "receiver_rejected_or_invalid"
        result["blocked_reasons"] = [*result["blocked_reasons"], *receiver_reasons]
        return result

    result["ok"] = True
    result["outbound_status"] = "sent_preview_only"
    result["network_send_succeeded"] = True
    return result


__all__ = [
    "ADAPTER_NAME",
    "DEFAULT_SEND_TIMEOUT_SECONDS",
    "FORMAL_CHAIN_FALSE_FLAGS",
    "NO_WRITE_FALSE_FLAGS",
    "OUTBOUND_ENABLED_ENV",
    "OUTBOUND_ENDPOINT_ENV",
    "OUTBOUND_NETWORK_SEND_ENABLED_ENV",
    "USER_VISIBLE_FALSE_FLAGS",
    "ZBID_PREVIEW_ONLY_RECEIVER_PATH",
    "build_zdoc_zbid_preview_only_outbound_config",
    "build_zdoc_zbid_preview_only_outbound_payload",
    "prepare_zdoc_zbid_preview_only_outbound",
]
