from __future__ import annotations

import json
from pathlib import Path

from image_generation.router.validators import validate_prompt_templates
from image_generation.workflows.workflow_bridge import WorkflowBridge
from image_generation.workflows.workflow_validator import validate_r4b_static_configs


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ID = "qwen_image_tender_municipal_trench_lifting_v1"
WORKFLOW_ID = "qwen_image_text_to_image"


def _load_json(path: str) -> dict:
    with (ROOT / path).open(encoding="utf-8") as file:
        return json.load(file)


def test_qwen_image_tender_municipal_trench_lifting_template_is_registered():
    prompt_templates = _load_json("configs/image-generation-prompt-templates.json")
    registry = _load_json("configs/image-generation-workflow-registry.json")
    manifest = _load_json("configs/comfyui-workflow-manifest.json")

    assert validate_prompt_templates(prompt_templates) == []
    assert validate_r4b_static_configs(registry, manifest, prompt_templates) == []

    template = prompt_templates["templates"][TEMPLATE_ID]
    assert template["template_name"] == "市政雨污分流沟槽管道吊装技术标插图模板"
    assert template["model_role"] == WORKFLOW_ID
    assert template["workflow_contract_id"] == WORKFLOW_ID
    assert template["workflow_id"] == WORKFLOW_ID
    assert template["workflow_json_ref"] == "blueprints/Text to Image (Qwen-Image).json"
    assert template["variable_fields"] == [
        "project_type",
        "construction_scene",
        "key_equipment",
        "safety_controls",
        "environmental_controls",
        "site_context",
    ]
    assert template["fixed_parameters"] == {
        "workflow": WORKFLOW_ID,
        "width": 1024,
        "height": 768,
        "batch_size": 1,
        "steps": 8,
        "cfg": 1,
        "sampler": "euler",
        "scheduler": "simple",
    }
    assert template["generation_policy"] == {
        "single_image_only_by_default": True,
        "video_generation_enabled": False,
        "batch_generation_enabled": False,
        "requires_manual_review": True,
    }
    assert "不适用于视频生成" in template["limitations"]
    assert "不适用于 image edit" in template["limitations"]
    assert "不适用于 FLUX 对比" in template["limitations"]
    assert "/Users/" not in json.dumps(template, ensure_ascii=False)


def test_qwen_image_tender_template_builds_static_single_image_workflow_plan():
    prompt_templates = _load_json("configs/image-generation-prompt-templates.json")
    registry = _load_json("configs/image-generation-workflow-registry.json")
    manifest = _load_json("configs/comfyui-workflow-manifest.json")
    bridge = WorkflowBridge(registry, manifest, prompt_templates)

    assert bridge.workflow_id_for_template(TEMPLATE_ID) == WORKFLOW_ID

    template = prompt_templates["templates"][TEMPLATE_ID]
    plan = bridge.build_plan(
        workflow_id=WORKFLOW_ID,
        prompt_template_key=TEMPLATE_ID,
        generation_options=template["fixed_parameters"],
    )

    assert plan.workflow_id == WORKFLOW_ID
    assert plan.workflow_json_ref == "blueprints/Text to Image (Qwen-Image).json"
    assert plan.runtime_enabled is False
    assert plan.no_video_generation is True
    assert plan.output_policy["max_images"] == 1
    assert plan.output_policy["batch_generation"] is False
    assert plan.input_binding.bindings["width"] == 1024
    assert plan.input_binding.bindings["height"] == 768
    assert plan.input_binding.bindings["steps"] == 8
    assert plan.input_binding.bindings["cfg"] == 1
    assert plan.input_binding.bindings["sampler"] == "euler"
    assert plan.input_binding.bindings["scheduler"] == "simple"
    assert plan.input_binding.source_image_required is False
    assert plan.input_binding.bindings["source_image"]["read_file_in_r4b"] is False
