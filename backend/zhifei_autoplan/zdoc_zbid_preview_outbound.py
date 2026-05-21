from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


ADAPTER_NAME = "zdoc_zbid_preview_only_outbound"
OUTBOUND_ENABLED_ENV = "ZDOC_ZBID_PREVIEW_ONLY_OUTBOUND_ENABLED"
OUTBOUND_ENDPOINT_ENV = "ZDOC_ZBID_PREVIEW_ONLY_ENDPOINT"

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


def build_zdoc_zbid_preview_only_outbound_config(
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    data = os.environ if env is None else env
    enabled = _enabled(data.get(OUTBOUND_ENABLED_ENV, ""))
    endpoint = _text(data.get(OUTBOUND_ENDPOINT_ENV, ""), limit=2000)

    if not enabled:
        status = "disabled"
        reasons = ["zdoc_zbid_preview_only_outbound_disabled"]
    elif not endpoint:
        status = "blocked_missing_endpoint"
        reasons = ["zdoc_zbid_preview_only_endpoint_missing"]
    else:
        status = "configured_not_sent"
        reasons = ["zdoc_zbid_preview_only_outbound_not_sent_by_design"]

    return {
        "adapter_name": ADAPTER_NAME,
        "enabled": enabled,
        "default_off": not enabled,
        "endpoint_configured": bool(endpoint),
        "endpoint": endpoint,
        "status": status,
        "preview_only": True,
        "no_write": True,
        "metadata_only": True,
        "auto_send_allowed": False,
        "network_send_allowed": False,
        "network_send_attempted": False,
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
        "preview_only": True,
        "no_write": True,
        "metadata_only": True,
        **NO_WRITE_FALSE_FLAGS,
    }


def prepare_zdoc_zbid_preview_only_outbound(
    *,
    preview_packet: dict[str, Any],
    validator_result: dict[str, Any],
    blocked_reasons: list[str] | tuple[str, ...] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_config = (
        build_zdoc_zbid_preview_only_outbound_config() if config is None else dict(config)
    )
    payload = build_zdoc_zbid_preview_only_outbound_payload(
        preview_packet=preview_packet,
        validator_result=validator_result,
        blocked_reasons=blocked_reasons,
    )
    reasons = _combined_blocked_reasons(resolved_config, payload)

    return {
        "ok": False,
        "adapter_name": ADAPTER_NAME,
        "outbound_status": resolved_config.get("status", "disabled"),
        "outbound_enabled": bool(resolved_config.get("enabled")),
        "default_off": bool(resolved_config.get("default_off", True)),
        "endpoint_configured": bool(resolved_config.get("endpoint_configured")),
        "endpoint": _text(resolved_config.get("endpoint"), limit=2000),
        "preview_only": True,
        "no_write": True,
        "metadata_only": True,
        "auto_send_allowed": False,
        "network_send_allowed": False,
        "network_send_attempted": False,
        "zbid_writeback_attempted": False,
        "payload": payload,
        "blocked_reasons": reasons,
        **NO_WRITE_FALSE_FLAGS,
    }


__all__ = [
    "ADAPTER_NAME",
    "FORMAL_CHAIN_FALSE_FLAGS",
    "NO_WRITE_FALSE_FLAGS",
    "OUTBOUND_ENABLED_ENV",
    "OUTBOUND_ENDPOINT_ENV",
    "USER_VISIBLE_FALSE_FLAGS",
    "build_zdoc_zbid_preview_only_outbound_config",
    "build_zdoc_zbid_preview_only_outbound_payload",
    "prepare_zdoc_zbid_preview_only_outbound",
]
