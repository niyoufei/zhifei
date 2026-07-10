from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import inspect
import json

import pytest

import image_generation.runtime.single_shot_submission_authorization as authorization_module
from image_generation.runtime.single_shot_submission_authorization import (
    build_single_shot_submission_authorization_envelope,
    validate_single_shot_submission_authorization_envelope,
)
from image_generation.workflows.project_prompt_payload_adapter import build_comfyui_prompt_payload


WORKFLOW_ID = "qwen_image_text_to_image"


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


def _authorization(**overrides) -> dict:
    record = {
        "authorization_id": "authorization-demo-001",
        "authorized_by": "reviewer-demo",
        "authorized_at": "2026-07-10T08:00:00Z",
        "expires_at": "2026-07-10T09:00:00+00:00",
        "reason": "批准一次本地单图提交",
        "scope": "qwen_image_text_to_image_single_image",
    }
    record.update(overrides)
    return record


def _payload_from_r12_builder() -> dict:
    plan = {
        "plan_type": "project_template_prompt_plan",
        "plan_version": "027n-r11-a",
        "project_id": "project-demo",
        "template_id": "template-demo",
        "workflow_id": WORKFLOW_ID,
        "candidate_seed": 7,
        "positive_prompt": "施工现场正向提示词",
        "negative_prompt": "水印，模糊",
        "fixed_parameters": {
            "width": 1024,
            "height": 768,
            "batch_size": 1,
            "steps": 8,
            "cfg": 1,
            "sampler": "euler",
            "scheduler": "simple",
        },
        "generation_policy": {
            "batch_generation_enabled": False,
            "video_generation_enabled": False,
            "auto_publish_enabled": False,
            "candidate_generation_mode": "serial_single_image",
        },
        "runtime_execution_authorized": False,
    }
    registry = {
        "workflows": {
            WORKFLOW_ID: {
                "workflow_id": WORKFLOW_ID,
                "workflow_contract_id": WORKFLOW_ID,
                "task_type": "text_to_image",
                "input_type": "text_prompt",
                "input_binding_profile": "qwen_image_text_to_image_inputs",
                "no_video_generation": True,
            }
        }
    }
    contract = {
        "workflow_id": WORKFLOW_ID,
        "input_binding_profile": "qwen_image_text_to_image_inputs",
        "bindings": {
            "positive_prompt": {"node_id": "1", "input_name": "text"},
            "negative_prompt": {"node_id": "2", "input_name": "text"},
            "candidate_seed": {"node_id": "3", "input_name": "seed"},
            "steps": {"node_id": "3", "input_name": "steps"},
            "cfg": {"node_id": "3", "input_name": "cfg"},
            "sampler": {"node_id": "3", "input_name": "sampler_name"},
            "scheduler": {"node_id": "3", "input_name": "scheduler"},
            "width": {"node_id": "4", "input_name": "width"},
            "height": {"node_id": "4", "input_name": "height"},
            "batch_size": {"node_id": "4", "input_name": "batch_size"},
            "output_prefix": {"node_id": "5", "input_name": "filename_prefix"},
        },
    }
    return build_comfyui_prompt_payload(plan, _payload()["api_prompt"], registry, contract)


def _build(payload=None, authorization_record=None) -> dict:
    return build_single_shot_submission_authorization_envelope(
        _payload() if payload is None else payload,
        _authorization() if authorization_record is None else authorization_record,
    )


def _canonical_sha256(value: dict) -> str:
    serialized = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def test_builds_and_validates_single_shot_envelope():
    envelope = _build()

    assert envelope["envelope_type"] == "single_shot_submission_authorization_envelope"
    assert envelope["envelope_version"] == "027n-r13-a"
    assert envelope["authorization_id"] == "authorization-demo-001"
    assert envelope["authorization"] == {
        "authorized_by": "reviewer-demo",
        "authorized_at": "2026-07-10T08:00:00Z",
        "expires_at": "2026-07-10T09:00:00+00:00",
        "reason": "批准一次本地单图提交",
        "scope": "qwen_image_text_to_image_single_image",
    }
    assert envelope["execution_limits"] == {
        "max_submissions": 1,
        "max_outputs": 1,
        "batch_size": 1,
        "workflow_id": WORKFLOW_ID,
    }
    assert envelope["safety_policy"] == {
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
    assert envelope["runtime_execution_authorized"] is True
    assert envelope["submission_authorized"] is True
    assert json.loads(json.dumps(envelope, ensure_ascii=False)) == envelope
    original_envelope = deepcopy(envelope)
    assert validate_single_shot_submission_authorization_envelope(envelope) is None
    assert envelope == original_envelope


def test_accepts_payload_produced_by_r12_builder():
    payload = _payload_from_r12_builder()

    assert payload == _payload()
    assert _build(payload)["payload_snapshot"] == payload


def test_inputs_are_unchanged_and_payload_snapshot_is_detached():
    payload = _payload()
    authorization_record = _authorization()
    original_payload = deepcopy(payload)
    original_authorization = deepcopy(authorization_record)

    envelope = _build(payload, authorization_record)

    assert payload == original_payload
    assert authorization_record == original_authorization
    assert envelope["payload_snapshot"] == payload
    assert envelope["payload_snapshot"] is not payload
    assert envelope["payload_snapshot"]["api_prompt"] is not payload["api_prompt"]

    payload["api_prompt"]["1"]["inputs"]["text"] = "changed input"
    authorization_record["reason"] = "changed authorization"
    assert envelope["payload_snapshot"]["api_prompt"]["1"]["inputs"]["text"] == "施工现场正向提示词"
    assert envelope["authorization"]["reason"] == "批准一次本地单图提交"

    envelope["payload_snapshot"]["api_prompt"]["2"]["inputs"]["text"] = "changed snapshot"
    assert original_payload["api_prompt"]["2"]["inputs"]["text"] == "水印，模糊"


def test_payload_sha256_uses_canonical_utf8_json_and_is_order_independent():
    payload = _payload()
    envelope = _build(payload)
    reordered_payload = dict(reversed(list(payload.items())))
    reordered_envelope = _build(reordered_payload)

    assert envelope["payload_sha256"] == _canonical_sha256(payload)
    assert reordered_envelope["payload_sha256"] == envelope["payload_sha256"]


def test_validator_recomputes_hash_and_rejects_payload_tampering():
    tampered_snapshot = _build()
    tampered_snapshot["payload_snapshot"]["api_prompt"]["1"]["inputs"]["text"] = "tampered"
    with pytest.raises(ValueError, match="does not match"):
        validate_single_shot_submission_authorization_envelope(tampered_snapshot)

    tampered_digest = _build()
    tampered_digest["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="does not match"):
        validate_single_shot_submission_authorization_envelope(tampered_digest)


def test_same_inputs_produce_identical_envelopes():
    payload = _payload()
    authorization_record = _authorization()

    assert _build(payload, authorization_record) == _build(payload, authorization_record)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("payload_type", "other", "payload_type"),
        ("payload_version", "027n-r11-a", "payload_version"),
        ("workflow_id", "other", "workflow_id"),
        ("runtime_execution_authorized", True, "must be false"),
        ("submission_authorized", True, "must be false"),
    ],
)
def test_rejects_wrong_payload_identity_or_pre_authorized_payload(field, value, error):
    payload = _payload()
    payload[field] = value

    with pytest.raises(ValueError, match=error):
        _build(payload)


@pytest.mark.parametrize("value", [0, 2, True, 1.0])
def test_rejects_invalid_expected_output_count(value):
    payload = _payload()
    payload["expected_output_count"] = value

    with pytest.raises(ValueError, match="expected_output_count must be 1"):
        _build(payload)


@pytest.mark.parametrize("value", [-1, True, 1.0, "7"])
def test_rejects_invalid_candidate_seed(value):
    payload = _payload()
    payload["candidate_seed"] = value

    with pytest.raises(ValueError, match="candidate_seed must be a non-negative integer"):
        _build(payload)


@pytest.mark.parametrize("value", [None, {}, {"1": {"class_type": "KSampler"}}])
def test_rejects_missing_or_invalid_api_prompt(value):
    payload = _payload()
    payload["api_prompt"] = value

    with pytest.raises(ValueError, match="api_prompt"):
        _build(payload)


def test_rejects_non_json_serializable_api_prompt():
    payload = _payload()
    payload["api_prompt"]["1"]["inputs"]["invalid"] = {"not-json"}

    with pytest.raises(ValueError, match="JSON serializable"):
        _build(payload)


@pytest.mark.parametrize("value", [2, True, 1.0])
def test_rejects_non_single_batch_size(value):
    payload = _payload()
    payload["api_prompt"]["4"]["inputs"]["batch_size"] = value

    with pytest.raises(ValueError, match="batch_size values must all be 1"):
        _build(payload)


def test_rejects_payload_without_batch_size():
    payload = _payload()
    payload["api_prompt"]["4"]["inputs"].pop("batch_size")

    with pytest.raises(ValueError, match="batch_size values must all be 1"):
        _build(payload)


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("batch_generation_enabled", True, "must be false"),
        ("video_generation_enabled", True, "must be false"),
        ("auto_publish_enabled", True, "must be false"),
        ("candidate_generation_mode", "parallel", "serial_single_image"),
    ],
)
def test_rejects_explicit_unsafe_policy_semantics(field, value, error):
    payload = _payload()
    payload["api_prompt"]["3"]["inputs"][field] = value

    with pytest.raises(ValueError, match=error):
        _build(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("batch", 1),
        ("video", "yes"),
        ("auto_publish", None),
    ],
)
def test_requires_policy_aliases_to_be_strictly_false(field, value):
    payload = _payload()
    payload["api_prompt"]["3"]["inputs"][field] = value

    with pytest.raises(ValueError, match=f"{field} must be false"):
        _build(payload)


@pytest.mark.parametrize(
    "class_type",
    [
        "VideoCombine",
        "SaveAnimatedWEBP",
        "VHS_LoadImages",
        "LoadImage",
        "LoadImageMask",
        "UploadImage",
        "PublishImage",
    ],
)
def test_rejects_video_image_edit_upload_or_publish_nodes(class_type):
    payload = _payload()
    payload["api_prompt"]["6"] = {"class_type": class_type, "inputs": {}}

    with pytest.raises(ValueError, match="video nodes|image-edit, upload, or publish nodes"):
        _build(payload)


@pytest.mark.parametrize(
    "class_type",
    ["HTTPRequest", "OpenAIImage", "ModelDownload", "FluxGuidance", "ImageBatch"],
)
def test_rejects_external_api_network_download_flux_or_batch_nodes(class_type):
    payload = _payload()
    payload["api_prompt"]["6"] = {"class_type": class_type, "inputs": {}}

    with pytest.raises(ValueError, match="external API, network, download, FLUX, or batch"):
        _build(payload)


@pytest.mark.parametrize("remove_existing", [False, True])
def test_requires_exactly_one_local_save_image_output(remove_existing):
    payload = _payload()
    if remove_existing:
        payload["api_prompt"].pop("5")
    else:
        payload["api_prompt"]["6"] = deepcopy(payload["api_prompt"]["5"])

    with pytest.raises(ValueError, match="exactly one local SaveImage output node"):
        _build(payload)


@pytest.mark.parametrize("input_name", ["source_image", "input_image", "upload_file", "publish_target"])
def test_rejects_image_edit_upload_or_publish_inputs(input_name):
    payload = _payload()
    payload["api_prompt"]["3"]["inputs"][input_name] = "relative-reference"

    with pytest.raises(ValueError, match="image-edit, upload, or publish inputs"):
        _build(payload)


@pytest.mark.parametrize(
    "field",
    ["authorization_id", "authorized_by", "authorized_at", "expires_at", "reason", "scope"],
)
def test_rejects_empty_authorization_fields(field):
    authorization_record = _authorization(**{field: " "})

    with pytest.raises(ValueError, match=field):
        _build(authorization_record=authorization_record)


def test_rejects_wrong_authorization_scope():
    with pytest.raises(ValueError, match="scope must be"):
        _build(authorization_record=_authorization(scope="other"))


def test_accepts_utc_timestamps_without_reading_current_time():
    historical = _authorization(
        authorized_at="2000-01-01T00:00:00Z",
        expires_at="2000-01-01T00:00:01+00:00",
    )

    assert _build(authorization_record=historical)["authorization"]["expires_at"] == historical["expires_at"]


@pytest.mark.parametrize(
    "value",
    [
        "not-a-time",
        "2026-07-10T08:00:00",
        "2026-07-10",
        "2026-07-10X08:00:00Z",
        "2026-07-10T08:00:00+08:00",
    ],
)
def test_rejects_invalid_or_non_utc_authorization_times(value):
    with pytest.raises(ValueError, match="ISO-8601 UTC"):
        _build(authorization_record=_authorization(authorized_at=value))


@pytest.mark.parametrize(
    "expires_at",
    ["2026-07-10T08:00:00Z", "2026-07-10T07:59:59Z"],
)
def test_rejects_non_increasing_authorization_window(expires_at):
    with pytest.raises(ValueError, match="later than authorized_at"):
        _build(authorization_record=_authorization(expires_at=expires_at))


@pytest.mark.parametrize(
    "field",
    ["api_token", "client_secret", "credential", "endpoint", "callback_url", "localhost_config"],
)
def test_rejects_forbidden_fields_in_payload(field):
    payload = _payload()
    payload["api_prompt"]["3"]["inputs"][field] = "synthetic"

    with pytest.raises(ValueError, match="token, secret, credential, endpoint, localhost, or URL"):
        _build(payload)


@pytest.mark.parametrize("field", ["token", "secret", "credential", "endpoint", "url"])
def test_rejects_forbidden_fields_in_authorization_record(field):
    authorization_record = _authorization()
    authorization_record[field] = "synthetic"

    with pytest.raises(ValueError, match="token, secret, credential, endpoint, localhost, or URL"):
        _build(authorization_record=authorization_record)


@pytest.mark.parametrize(
    "value",
    [
        "localhost",
        ".env",
        "https://example.invalid/resource",
        "wss://example.invalid/socket",
        "s3://bucket/key",
        "https:example.invalid/path",
        "ssh:user@example.invalid",
        "tel:+123456",
        "see(www.example.invalid)",
    ],
)
def test_rejects_forbidden_runtime_references(value):
    payload = _payload()
    payload["api_prompt"]["3"]["inputs"]["note"] = value

    with pytest.raises(ValueError, match="localhost, \\.env, or URL"):
        _build(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_path", "/models/qwen.safetensors"),
        ("output_path", "/tmp/output"),
        ("model_path", "~/models/qwen.safetensors"),
        ("output_path", "file:///tmp/output"),
        ("output_path", "file:/tmp/output"),
        ("output_path", "FILE:///tmp/output"),
        ("model_path", "C:\\models\\qwen.safetensors"),
        ("model_path", "\\\\server\\share\\qwen.safetensors"),
        ("model_path", " \\\\server\\share\\qwen.safetensors"),
        ("output_path", " /tmp/output"),
        ("output_path", "../../output"),
    ],
)
def test_rejects_absolute_model_or_output_paths(field, value):
    payload = _payload()
    payload["api_prompt"]["3"]["inputs"][field] = value

    with pytest.raises(ValueError, match="absolute paths"):
        _build(payload)


def test_validator_rechecks_snapshot_safety_even_with_updated_hash():
    envelope = _build()
    envelope["payload_snapshot"]["api_prompt"]["3"]["inputs"]["api_token"] = "synthetic"
    envelope["payload_sha256"] = _canonical_sha256(envelope["payload_snapshot"])

    with pytest.raises(ValueError, match="token, secret, credential"):
        validate_single_shot_submission_authorization_envelope(envelope)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda envelope: envelope["execution_limits"].__setitem__("max_submissions", 2),
        lambda envelope: envelope["execution_limits"].__setitem__("max_outputs", 2),
        lambda envelope: envelope["execution_limits"].__setitem__("batch_size", 2),
        lambda envelope: envelope["execution_limits"].__setitem__("workflow_id", "other"),
        lambda envelope: envelope["safety_policy"].__setitem__("external_network_allowed", True),
        lambda envelope: envelope.__setitem__("runtime_execution_authorized", False),
        lambda envelope: envelope.__setitem__("submission_authorized", False),
        lambda envelope: envelope["authorization"].__setitem__("scope", "other"),
        lambda envelope: envelope["authorization"].__setitem__(
            "expires_at", "2026-07-10T07:59:59Z"
        ),
    ],
)
def test_validator_rejects_tampered_limits_or_authorization_flags(mutate):
    envelope = _build()
    mutate(envelope)

    with pytest.raises(ValueError):
        validate_single_shot_submission_authorization_envelope(envelope)


def test_validator_rejects_duplicate_nested_authorization_id():
    envelope = _build()
    envelope["authorization"]["authorization_id"] = "override"

    with pytest.raises(ValueError, match="exactly the R13-A authorization fields"):
        validate_single_shot_submission_authorization_envelope(envelope)


def test_implementation_has_no_file_environment_network_or_current_time_access():
    source = inspect.getsource(authorization_module)
    tree = ast.parse(source)
    forbidden_modules = {
        "http.client",
        "httpx",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "time",
        "urllib.request",
    }
    forbidden_calls = {
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
            assert all(alias.name not in forbidden_modules for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden_modules
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden_calls | {"now", "open"}
