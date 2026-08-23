"""Pure static authorization envelope for one local ComfyUI submission."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import re
from typing import Any

from image_generation.router.policies import assert_static_policy
from image_generation.workflows.project_prompt_payload_adapter import (
    PAYLOAD_TYPE,
    PAYLOAD_VERSION,
    WORKFLOW_ID,
)
from image_generation.workflows.workflow_output_policy import get_output_policy


ENVELOPE_TYPE = "single_shot_submission_authorization_envelope"
ENVELOPE_VERSION = "027n-r13-a"
AUTHORIZATION_SCOPE = "qwen_image_text_to_image_single_image"

_R12_PAYLOAD_FIELDS = {
    "payload_type",
    "payload_version",
    "project_id",
    "template_id",
    "workflow_id",
    "api_prompt",
    "candidate_seed",
    "expected_output_count",
    "output_prefix",
    "runtime_execution_authorized",
    "submission_authorized",
}
_AUTHORIZATION_FIELDS = {
    "authorization_id",
    "authorized_by",
    "authorized_at",
    "expires_at",
    "reason",
    "scope",
}
_ENVELOPE_AUTHORIZATION_FIELDS = _AUTHORIZATION_FIELDS - {"authorization_id"}
_ENVELOPE_FIELDS = {
    "envelope_type",
    "envelope_version",
    "authorization_id",
    "payload_sha256",
    "payload_snapshot",
    "authorization",
    "execution_limits",
    "safety_policy",
    "runtime_execution_authorized",
    "submission_authorized",
}
_DISABLED_POLICY_FIELDS = {
    "batch_enabled",
    "batch_generation_enabled",
    "video_enabled",
    "video_generation_enabled",
    "auto_publish_enabled",
}
_BOOLEAN_POLICY_ALIASES = {"batch", "video", "auto_publish"}
_IMAGE_EDIT_INPUTS = {
    "source_image",
    "input_image",
    "reference_image",
    "edit_image",
    "image_path",
    "upload",
    "upload_file",
}
_VIDEO_MARKERS = ("video", "svd", "wanvideo", "animatediff", "animated", "animation", "vhs", "gif")
_FORBIDDEN_RUNTIME_CLASS_MARKERS = (
    "aws",
    "azure",
    "batch",
    "download",
    "externalapi",
    "flux",
    "ftp",
    "gcp",
    "gemini",
    "hfhub",
    "http",
    "huggingface",
    "network",
    "openai",
    "remote",
    "replicate",
    "request",
    "s3",
    "socket",
    "stability",
    "telegram",
    "url",
    "webhook",
    "websocket",
)
_FORBIDDEN_KEY_MARKERS = ("token", "secret", "credential", "endpoint", "localhost", "url")
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
_PARENT_PATH_REFERENCE = re.compile(r"(?:^|[\\/])\.\.(?:[\\/]|$)")
_URL_VALUE = re.compile(r"(?i)(?:\b[a-z][a-z0-9+.-]*:(?=\S)|\bwww\.)")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_ISO_8601_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$"
)

_EXECUTION_LIMITS = {
    "max_submissions": 1,
    "max_outputs": 1,
    "batch_size": 1,
    "workflow_id": WORKFLOW_ID,
}
_SAFETY_POLICY = {
    "local_service_only": True,
    "external_network_allowed": False,
    "external_api_allowed": False,
    "video_generation_allowed": False,
    "batch_generation_allowed": False,
    "model_download_allowed": False,
    "flux_allowed": False,
    "image_edit_allowed": False,
    "requires_empty_queue": True,
    "requires_service_health": True,
    "requires_manual_review_after_generation": True,
}


def build_single_shot_submission_authorization_envelope(
    payload: dict,
    authorization_record: dict,
) -> dict:
    """Build a deterministic authorization envelope without runtime side effects."""

    _validate_reused_static_policies()
    _validate_payload(payload)
    _validate_authorization_record(authorization_record)

    payload_snapshot = deepcopy(payload)
    envelope = {
        "envelope_type": ENVELOPE_TYPE,
        "envelope_version": ENVELOPE_VERSION,
        "authorization_id": authorization_record["authorization_id"],
        "payload_sha256": _payload_sha256(payload_snapshot),
        "payload_snapshot": payload_snapshot,
        "authorization": {
            "authorized_by": authorization_record["authorized_by"],
            "authorized_at": authorization_record["authorized_at"],
            "expires_at": authorization_record["expires_at"],
            "reason": authorization_record["reason"],
            "scope": authorization_record["scope"],
        },
        "execution_limits": deepcopy(_EXECUTION_LIMITS),
        "safety_policy": deepcopy(_SAFETY_POLICY),
        "runtime_execution_authorized": True,
        "submission_authorized": True,
    }
    validate_single_shot_submission_authorization_envelope(envelope)
    return envelope


def validate_single_shot_submission_authorization_envelope(envelope: dict) -> None:
    """Validate structure, safety limits, authorization, and payload fingerprint."""

    if not isinstance(envelope, dict):
        raise ValueError("envelope must be an object")
    _strict_json_bytes(envelope, "envelope")
    _validate_no_forbidden_content(envelope, "envelope")
    if set(envelope) != _ENVELOPE_FIELDS:
        raise ValueError("envelope must contain exactly the R13-A envelope fields")
    if envelope.get("envelope_type") != ENVELOPE_TYPE:
        raise ValueError(f"envelope_type must be {ENVELOPE_TYPE}")
    if envelope.get("envelope_version") != ENVELOPE_VERSION:
        raise ValueError(f"envelope_version must be {ENVELOPE_VERSION}")
    if envelope.get("execution_limits") != _EXECUTION_LIMITS:
        raise ValueError("execution_limits must preserve the single-shot limits")
    if envelope.get("safety_policy") != _SAFETY_POLICY:
        raise ValueError("safety_policy must preserve the local-only safety boundary")
    if envelope.get("runtime_execution_authorized") is not True:
        raise ValueError("runtime_execution_authorized must be true")
    if envelope.get("submission_authorized") is not True:
        raise ValueError("submission_authorized must be true")

    payload_snapshot = envelope.get("payload_snapshot")
    _validate_payload(payload_snapshot)
    payload_sha256 = envelope.get("payload_sha256")
    if not isinstance(payload_sha256, str) or not _SHA256_HEX.fullmatch(payload_sha256):
        raise ValueError("payload_sha256 must be a lowercase SHA-256 hex digest")
    if payload_sha256 != _payload_sha256(payload_snapshot):
        raise ValueError("payload_sha256 does not match payload_snapshot")

    authorization = envelope.get("authorization")
    if not isinstance(authorization, dict):
        raise ValueError("authorization must be an object")
    if set(authorization) != _ENVELOPE_AUTHORIZATION_FIELDS:
        raise ValueError("authorization must contain exactly the R13-A authorization fields")
    _validate_authorization_record(
        {
            "authorization_id": envelope.get("authorization_id"),
            **authorization,
        }
    )


def _validate_reused_static_policies() -> None:
    output_policy = get_output_policy("single_image_local_only")
    if (
        type(output_policy.get("max_images")) is not int
        or output_policy["max_images"] != 1
        or output_policy.get("auto_upload") is not False
        or output_policy.get("batch_generation") is not False
    ):
        raise ValueError("single_image_local_only output policy is incompatible with R13-A")

    router_policy = assert_static_policy()
    if (
        router_policy.get("LOCAL_ONLY") is not True
        or router_policy.get("VIDEO_GENERATION_ENABLED") is not False
        or router_policy.get("ALLOW_REMOTE_API_MODELS") is not False
    ):
        raise ValueError("static image routing policy is incompatible with R13-A")


def _validate_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    _strict_json_bytes(payload, "payload")
    _validate_no_forbidden_content(payload, "payload")
    _validate_policy_semantics(payload)
    if set(payload) != _R12_PAYLOAD_FIELDS:
        raise ValueError("payload must contain exactly the R12-A payload fields")
    if payload.get("payload_type") != PAYLOAD_TYPE:
        raise ValueError(f"payload_type must be {PAYLOAD_TYPE}")
    # R12 validates generation policy before emission but does not serialize it.
    # Pin that producer contract, then revalidate its execution-effective graph below.
    if payload.get("payload_version") != PAYLOAD_VERSION:
        raise ValueError(f"payload_version must be {PAYLOAD_VERSION}")
    if payload.get("workflow_id") != WORKFLOW_ID:
        raise ValueError(f"workflow_id must be {WORKFLOW_ID}")
    if type(payload.get("expected_output_count")) is not int or payload["expected_output_count"] != 1:
        raise ValueError("expected_output_count must be 1")
    if payload.get("runtime_execution_authorized") is not False:
        raise ValueError("payload runtime_execution_authorized must be false")
    if payload.get("submission_authorized") is not False:
        raise ValueError("payload submission_authorized must be false")
    if type(payload.get("candidate_seed")) is not int or payload["candidate_seed"] < 0:
        raise ValueError("candidate_seed must be a non-negative integer")
    for field in ("project_id", "template_id", "output_prefix"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"payload.{field} must be a non-empty string")

    api_prompt = payload.get("api_prompt")
    _validate_api_prompt(api_prompt)
    batch_sizes = _values_for_key(api_prompt, "batch_size")
    if not batch_sizes or any(type(value) is not int or value != 1 for value in batch_sizes):
        raise ValueError("api_prompt batch_size values must all be 1")


def _validate_api_prompt(api_prompt: object) -> None:
    if not isinstance(api_prompt, dict) or not api_prompt:
        raise ValueError("api_prompt must be a non-empty object")
    local_image_outputs = 0
    for node_id, node in api_prompt.items():
        if not isinstance(node_id, str) or not isinstance(node, dict):
            raise ValueError("api_prompt must use node objects keyed by string ids")
        class_type = node.get("class_type")
        inputs = node.get("inputs")
        if not isinstance(class_type, str) or not class_type.strip() or not isinstance(inputs, dict):
            raise ValueError("api_prompt nodes must contain class_type and inputs")
        normalized_class = re.sub(r"[^a-z0-9]", "", class_type.lower())
        if any(marker in normalized_class for marker in _VIDEO_MARKERS):
            raise ValueError("api_prompt must not contain video nodes")
        if any(marker in normalized_class for marker in _FORBIDDEN_RUNTIME_CLASS_MARKERS):
            raise ValueError(
                "api_prompt must not contain external API, network, download, FLUX, or batch nodes"
            )
        if (
            "imageedit" in normalized_class
            or normalized_class.startswith("loadimage")
            or "upload" in normalized_class
            or "publish" in normalized_class
        ):
            raise ValueError("api_prompt must not contain image-edit, upload, or publish nodes")
        normalized_inputs = {str(input_name).lower() for input_name in inputs}
        if normalized_inputs & _IMAGE_EDIT_INPUTS or any(
            "publish" in input_name for input_name in normalized_inputs
        ):
            raise ValueError("api_prompt must not contain image-edit, upload, or publish inputs")
        if normalized_class.startswith("saveimage"):
            local_image_outputs += 1
    if local_image_outputs != 1:
        raise ValueError("api_prompt must contain exactly one local SaveImage output node")


def _validate_policy_semantics(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).lower()
            if normalized_key in _DISABLED_POLICY_FIELDS and child is not False:
                raise ValueError(f"{normalized_key} must be false")
            if normalized_key in _BOOLEAN_POLICY_ALIASES and child is not False:
                raise ValueError(f"{normalized_key} must be false")
            if (
                normalized_key == "candidate_generation_mode"
                and child != "serial_single_image"
            ):
                raise ValueError("candidate_generation_mode must be serial_single_image")
            _validate_policy_semantics(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_policy_semantics(child)


def _validate_authorization_record(record: object) -> None:
    if not isinstance(record, dict):
        raise ValueError("authorization_record must be an object")
    _strict_json_bytes(record, "authorization_record")
    _validate_no_forbidden_content(record, "authorization_record")
    if set(record) != _AUTHORIZATION_FIELDS:
        raise ValueError("authorization_record must contain exactly the required fields")
    for field in _AUTHORIZATION_FIELDS:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"authorization_record.{field} must be a non-empty string")
    if record["scope"] != AUTHORIZATION_SCOPE:
        raise ValueError(f"authorization_record.scope must be {AUTHORIZATION_SCOPE}")

    authorized_at = _parse_utc_timestamp(record["authorized_at"], "authorized_at")
    expires_at = _parse_utc_timestamp(record["expires_at"], "expires_at")
    if expires_at <= authorized_at:
        raise ValueError("expires_at must be later than authorized_at")


def _parse_utc_timestamp(value: str, field: str) -> datetime:
    if not _ISO_8601_UTC.fullmatch(value):
        raise ValueError(f"{field} must be a valid ISO-8601 UTC timestamp")
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 UTC timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ValueError(f"{field} must be a valid ISO-8601 UTC timestamp")
    return parsed


def _validate_no_forbidden_content(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{context} keys must be strings")
            normalized_key = key.lower()
            if any(marker in normalized_key for marker in _FORBIDDEN_KEY_MARKERS):
                raise ValueError(
                    f"{context} must not contain token, secret, credential, endpoint, localhost, or URL fields"
                )
            _validate_no_forbidden_content(child, context)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_no_forbidden_content(child, context)
    elif isinstance(value, str):
        normalized_value = value.strip()
        lowered = normalized_value.lower()
        if (
            normalized_value.startswith(("/", "~/", "~\\", "\\"))
            or lowered.startswith("file:")
            or _WINDOWS_ABSOLUTE_PATH.match(normalized_value)
            or _PARENT_PATH_REFERENCE.search(normalized_value)
        ):
            raise ValueError(f"{context} must not contain absolute paths or parent-relative paths")
        if (
            "localhost" in lowered
            or "127.0.0.1" in lowered
            or "[::1]" in lowered
            or ".env" in lowered
            or _URL_VALUE.search(normalized_value)
        ):
            raise ValueError(f"{context} must not contain localhost, .env, or URL references")


def _values_for_key(value: Any, target_key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() == target_key:
                found.append(child)
            found.extend(_values_for_key(child, target_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.extend(_values_for_key(child, target_key))
    return found


def _payload_sha256(payload_snapshot: dict) -> str:
    return hashlib.sha256(_strict_json_bytes(payload_snapshot, "payload_snapshot")).hexdigest()


def _strict_json_bytes(value: Any, label: str) -> bytes:
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON serializable") from exc
    return serialized.encode("utf-8")
