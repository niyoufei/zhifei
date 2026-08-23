from __future__ import annotations

from copy import deepcopy
import json

import pytest

import image_generation.workflows.project_prompt_payload_adapter as adapter_module
from image_generation.workflows.project_prompt_payload_adapter import (
    build_comfyui_prompt_payload,
)
from image_generation.workflows.workflow_input_binding import (
    PRODUCTION_BINDING_CONTRACT_KEYS,
    PRODUCTION_BINDING_DESCRIPTOR_FIELDS,
)


WORKFLOW_ID = "qwen_image_text_to_image"


def _plan() -> dict:
    return {
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


def _workflow() -> dict:
    return {
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "old-positive"}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "old-negative"}},
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 0,
                "steps": 1,
                "cfg": 1,
                "sampler_name": "old",
                "scheduler": "old",
            },
        },
        "4": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {"width": 1, "height": 1, "batch_size": 1},
        },
        "5": {"class_type": "SaveImage", "inputs": {"filename_prefix": "old", "images": ["3", 0]}},
    }


def _registry() -> dict:
    return {
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


def _contract() -> dict:
    return {
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


def _build(plan=None, workflow=None, registry=None, contract=None):
    return build_comfyui_prompt_payload(
        plan or _plan(),
        workflow or _workflow(),
        registry or _registry(),
        contract or _contract(),
    )


def test_builds_deterministic_serializable_single_image_payload_without_mutation():
    plan, workflow = _plan(), _workflow()
    original_plan, original_workflow = deepcopy(plan), deepcopy(workflow)

    payload = _build(plan=plan, workflow=workflow)

    assert payload == _build(plan=plan, workflow=workflow)
    assert plan == original_plan
    assert workflow == original_workflow
    assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload
    assert payload["payload_type"] == "comfyui_api_prompt_payload"
    assert payload["payload_version"] == "027n-r12-a"
    assert payload["expected_output_count"] == 1
    assert payload["runtime_execution_authorized"] is False
    assert payload["submission_authorized"] is False
    assert payload["api_prompt"]["1"]["inputs"]["text"] == plan["positive_prompt"]
    assert payload["api_prompt"]["2"]["inputs"]["text"] == plan["negative_prompt"]
    assert payload["api_prompt"]["3"]["inputs"] == {
        "seed": 7, "steps": 8, "cfg": 1, "sampler_name": "euler", "scheduler": "simple"
    }
    assert payload["api_prompt"]["4"]["inputs"] == {
        "width": 1024, "height": 768, "batch_size": 1
    }
    assert payload["api_prompt"]["5"]["inputs"]["filename_prefix"] == payload["output_prefix"]


def test_binding_contract_uses_the_shared_immutable_key_and_descriptor_sources():
    bindings = _contract()["bindings"]

    assert adapter_module.PRODUCTION_BINDING_CONTRACT_KEYS is PRODUCTION_BINDING_CONTRACT_KEYS
    assert (
        adapter_module.PRODUCTION_BINDING_DESCRIPTOR_FIELDS
        is PRODUCTION_BINDING_DESCRIPTOR_FIELDS
    )
    assert not hasattr(adapter_module, "_REQUIRED_BINDINGS")
    assert frozenset(bindings) == PRODUCTION_BINDING_CONTRACT_KEYS
    assert all(
        frozenset(descriptor) == PRODUCTION_BINDING_DESCRIPTOR_FIELDS
        for descriptor in bindings.values()
    )


@pytest.mark.parametrize("missing_key", sorted(PRODUCTION_BINDING_CONTRACT_KEYS))
def test_binding_contract_still_rejects_each_missing_required_key(missing_key):
    contract = _contract()
    contract["bindings"].pop(missing_key)

    with pytest.raises(ValueError, match="must contain exactly the allowed binding fields"):
        _build(contract=contract)


def test_binding_contract_still_rejects_an_extra_key():
    contract = _contract()
    contract["bindings"]["extra_binding"] = {
        "node_id": "6",
        "input_name": "extra",
    }

    with pytest.raises(ValueError, match="must contain exactly the allowed binding fields"):
        _build(contract=contract)


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda plan: plan["fixed_parameters"].__setitem__("batch_size", 2), "batch_size must be 1"),
        (lambda plan: plan.__setitem__("workflow_id", "other"), "workflow_id must be"),
        (lambda plan: plan.__setitem__("runtime_execution_authorized", True), "must be false"),
        (lambda plan: plan["generation_policy"].__setitem__("batch_generation_enabled", True), "must be false"),
        (lambda plan: plan["generation_policy"].__setitem__("video_generation_enabled", True), "must be false"),
        (lambda plan: plan["generation_policy"].__setitem__("auto_publish_enabled", True), "must be false"),
    ],
)
def test_rejects_unsafe_or_unsupported_plan(mutate, error):
    plan = _plan()
    mutate(plan)
    with pytest.raises(ValueError, match=error):
        _build(plan=plan)


def test_rejects_registry_or_binding_contract_mismatch():
    registry = _registry()
    registry["workflows"][WORKFLOW_ID]["task_type"] = "image_to_image"
    with pytest.raises(ValueError, match="registry entry does not match"):
        _build(registry=registry)

    contract = _contract()
    contract["input_binding_profile"] = "qwen_image_edit_image_to_image_inputs"
    with pytest.raises(ValueError, match="binding_contract.input_binding_profile"):
        _build(contract=contract)


def test_rejects_missing_node_or_binding_target():
    workflow = _workflow()
    workflow.pop("1")
    with pytest.raises(ValueError, match="binding target node is missing"):
        _build(workflow=workflow)

    workflow = _workflow()
    workflow["1"]["inputs"].pop("text")
    with pytest.raises(ValueError, match="binding target input is missing"):
        _build(workflow=workflow)


def test_rejects_video_node_and_image_edit_input():
    workflow = _workflow()
    workflow["6"] = {"class_type": "VideoCombine", "inputs": {"frames": []}}
    with pytest.raises(ValueError, match="video nodes"):
        _build(workflow=workflow)

    workflow = _workflow()
    workflow["6"] = {"class_type": "LoadImage", "inputs": {"image": "upload.png"}}
    with pytest.raises(ValueError, match="image-edit input nodes"):
        _build(workflow=workflow)


@pytest.mark.parametrize(
    ("node_id", "input_name", "value"),
    [
        ("1", "api_token", "synthetic"),
        ("1", "endpoint", "http://localhost:8188"),
        ("1", "config", ".env"),
        ("1", "model_path", "/models/qwen.safetensors"),
        ("5", "output_path", "/tmp/output"),
    ],
)
def test_rejects_sensitive_runtime_or_absolute_path_content(node_id, input_name, value):
    workflow = _workflow()
    workflow[node_id]["inputs"][input_name] = value
    with pytest.raises(ValueError, match="token|endpoint|localhost|env|absolute paths"):
        _build(workflow=workflow)
