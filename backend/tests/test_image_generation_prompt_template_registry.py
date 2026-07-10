from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from image_generation.prompts.project_template_prompt_plan import (
    build_project_template_prompt_plan,
)
from image_generation.router.validators import validate_prompt_templates
from image_generation.workflows.workflow_bridge import WorkflowBridge
from image_generation.workflows.workflow_validator import (
    validate_project_template_instance,
    validate_r4b_static_configs,
)


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ID = "qwen_image_tender_municipal_trench_lifting_v1"
WORKFLOW_ID = "qwen_image_text_to_image"


def _load_json(path: str) -> dict:
    with (ROOT / path).open(encoding="utf-8") as file:
        return json.load(file)


def _load_static_configs() -> tuple[dict, dict, dict]:
    return (
        _load_json("configs/image-generation-prompt-templates.json"),
        _load_json("configs/image-generation-workflow-registry.json"),
        _load_json("configs/comfyui-workflow-manifest.json"),
    )


def _new_template(case_id: str, prompt_templates: dict) -> tuple[str, dict]:
    template_key = f"admission_{case_id}"
    template = deepcopy(prompt_templates["templates"][TEMPLATE_ID])
    template["template_id"] = template_key
    return template_key, template


def _validate_prompt_template_admission(prompt_templates: dict) -> list[str]:
    registry = _load_json("configs/image-generation-workflow-registry.json")
    manifest = _load_json("configs/comfyui-workflow-manifest.json")
    return validate_r4b_static_configs(registry, manifest, prompt_templates)


def _valid_project_template_instance() -> dict:
    return {
        "schema_type": "project_template_instance",
        "schema_version": "027n-r10-c",
        "project_id": "project-027n-r10c-demo",
        "project_name": "市政雨污分流沟槽管道吊装示例项目",
        "template_id": TEMPLATE_ID,
        "workflow_id": WORKFLOW_ID,
        "created_time": "2026-07-08T00:00:00+08:00",
        "operator": "manual-review-operator",
        "variables": {
            "project_type": "市政道路工程",
            "construction_scene": "雨污分流沟槽开挖与管道吊装",
            "key_equipment": "汽车吊、挖掘机、管道吊具",
            "safety_controls": "硬质围挡、吊装警戒区、专人指挥",
            "environmental_controls": "雾炮降尘、材料覆盖、出入口冲洗",
            "site_context": "城市道路半幅封闭施工现场",
        },
        "policy_refs": {
            "generation_policy": "template:generation_policy",
            "review_policy": "template:review_policy",
            "retention_policy": "template:retention_policy",
        },
        "locked_policy_flags": {
            "video_generation_enabled": False,
            "batch_generation_enabled": False,
            "auto_publish_enabled": False,
        },
        "review": {
            "status": "approved_for_bid",
            "previous_status": "selected",
            "approved_time": "2026-07-08T01:00:00+08:00",
            "reviewer": "technical-bid-reviewer",
            "review_notes": "人工终审确认可用于技术标插图。",
            "checks": {
                "template_applicable": True,
                "variables_complete": True,
                "manual_review_completed": True,
                "no_watermark_logo": True,
                "no_obvious_ai_artifacts": True,
                "safety_civilized_construction_correct": True,
                "technical_bid_illustration_fit": True,
            },
        },
    }


def _validate_project_instance(instance: dict) -> list[str]:
    prompt_templates, registry, _ = _load_static_configs()
    return validate_project_template_instance(instance, prompt_templates, registry)


def _remove(field: str):
    def mutate(template: dict) -> None:
        template.pop(field)

    return mutate


def _set_generation_policy(field: str, value: object):
    def mutate(template: dict) -> None:
        template["generation_policy"][field] = value

    return mutate


def _set_review_policy(field: str, value: object):
    def mutate(template: dict) -> None:
        template["review_policy"][field] = value

    return mutate


def _set_retention_policy(field: str, value: object):
    def mutate(template: dict) -> None:
        template["generation_policy"]["retention_policy"][field] = value

    return mutate


def test_qwen_image_tender_municipal_trench_lifting_template_is_registered():
    prompt_templates, registry, manifest = _load_static_configs()

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
    policy = template["generation_policy"]
    assert policy["max_candidates_per_task"] == 3
    assert policy["recommended_candidates_per_task"] == 2
    assert policy["recommended_candidates_per_task"] <= policy["max_candidates_per_task"]
    assert policy["single_image_only_by_default"] is True
    assert policy["candidate_generation_mode"] == "serial_single_image"
    assert policy["seed_required"] is True
    assert policy["manual_review_required"] is True
    assert policy["auto_publish_enabled"] is False
    assert policy["video_generation_enabled"] is False
    assert policy["batch_generation_enabled"] is False
    assert policy["cross_model_comparison_enabled"] is False
    assert policy["requires_manual_review"] is True
    assert (
        policy["output_naming_pattern"]
        == "project_slug__template_id__scene_type__seed-{seed}__{width}x{height}__{timestamp}__review-{review_status}.png"
    )
    assert policy["review_status_enum"] == [
        "draft",
        "candidate",
        "selected",
        "rejected",
        "needs_regeneration",
        "approved_for_bid",
    ]
    review_policy = template["review_policy"]
    assert set(review_policy) == {
        "required",
        "manual_review_required",
        "review_status_enum",
        "checklist",
        "approval_required_before_bid",
    }
    assert review_policy["required"] is True
    assert review_policy["manual_review_required"] is True
    assert review_policy["review_status_enum"] == policy["review_status_enum"]
    assert review_policy["checklist"] == [
        "technical_bid_scene_fit",
        "watermark_logo_check",
        "text_artifact_check",
        "safety_civilized_construction_check",
        "person_equipment_integrity_check",
        "formal_document_suitability_check",
    ]
    assert review_policy["approval_required_before_bid"] is True
    assert policy["retention_policy"] == {
        "keep_original_outputs": True,
        "keep_selected_outputs": True,
        "allow_cleanup_rejected_candidates": True,
        "cleanup_requires_manifest": True,
        "auto_delete_enabled": False,
        "never_clear_output_dir": True,
        "never_delete_model_files": True,
    }
    assert policy["duplicate_model_cleanup_policy"] == {
        "keep_current_workflow_target_models": True,
        "keep_hf_cache_symlink_shards_by_default": True,
        "delete_uncertain_assets": False,
        "cleanup_requires_separate_gate": True,
        "forbid_wildcard_rm": True,
        "verify_required_models_after_cleanup": True,
    }
    assert template["model_family"] == "qwen_image"
    assert template["workflow_contract_id"] != "flux_realistic_text_to_image"
    assert template["workflow_contract_id"] != "qwen_image_edit_image_to_image"
    assert "不适用于视频生成" in template["limitations"]
    assert "不适用于 image edit" in template["limitations"]
    assert "不适用于 FLUX 对比" in template["limitations"]
    assert "/Users/" not in json.dumps(template, ensure_ascii=False)


def test_qwen_image_tender_template_builds_static_single_image_workflow_plan():
    prompt_templates, registry, manifest = _load_static_configs()
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


def test_prompt_template_admission_rejects_duplicate_template_id():
    prompt_templates, _, _ = _load_static_configs()
    template = deepcopy(prompt_templates["templates"][TEMPLATE_ID])
    prompt_templates["templates"]["duplicate_qwen_template"] = template

    errors = _validate_prompt_template_admission(prompt_templates)

    assert any("duplicate template_id" in error for error in errors), errors


@pytest.mark.parametrize(
    ("case_id", "mutate", "expected_error"),
    [
        (
            "missing_workflow_id",
            _remove("workflow_id"),
            "workflow_id must be a non-empty string",
        ),
        (
            "missing_fixed_parameters",
            _remove("fixed_parameters"),
            "fixed_parameters must be an object",
        ),
        (
            "missing_variable_fields",
            _remove("variable_fields"),
            "variable_fields must be a string array",
        ),
        (
            "missing_generation_policy",
            _remove("generation_policy"),
            "generation_policy must be an object",
        ),
        (
            "batch_generation_enabled_true",
            _set_generation_policy("batch_generation_enabled", True),
            "generation_policy.batch_generation_enabled must be false",
        ),
        (
            "video_generation_enabled_true",
            _set_generation_policy("video_generation_enabled", True),
            "generation_policy.video_generation_enabled must be false",
        ),
        (
            "manual_review_required_false",
            _set_generation_policy("manual_review_required", False),
            "generation_policy.manual_review_required must be true",
        ),
        (
            "auto_publish_enabled_true",
            _set_generation_policy("auto_publish_enabled", True),
            "generation_policy.auto_publish_enabled must be false",
        ),
        (
            "review_required_false",
            _set_review_policy("required", False),
            "review_policy.required must be true",
        ),
        (
            "cleanup_requires_manifest_false",
            _set_retention_policy("cleanup_requires_manifest", False),
            "retention_policy.cleanup_requires_manifest must be true",
        ),
        (
            "auto_delete_enabled_true",
            _set_retention_policy("auto_delete_enabled", True),
            "retention_policy.auto_delete_enabled must be false",
        ),
        (
            "unknown_workflow_id",
            lambda template: template.__setitem__("workflow_id", "missing_workflow"),
            "workflow_id must exist in registry",
        ),
    ],
)
def test_prompt_template_admission_rejects_invalid_new_templates(
    case_id: str,
    mutate,
    expected_error: str,
):
    prompt_templates, _, _ = _load_static_configs()
    template_key, template = _new_template(case_id, prompt_templates)
    mutate(template)
    prompt_templates["templates"][template_key] = template

    errors = _validate_prompt_template_admission(prompt_templates)

    assert any(expected_error in error for error in errors), errors


def test_project_template_instance_accepts_valid_instance():
    errors = _validate_project_instance(_valid_project_template_instance())

    assert errors == []


@pytest.mark.parametrize(
    ("case_id", "mutate", "expected_error"),
    [
        (
            "missing_project_id",
            lambda instance: instance.pop("project_id"),
            "project_template_instance missing fields: ['project_id']",
        ),
        (
            "missing_variables_field",
            lambda instance: instance.pop("variables"),
            "project_template_instance missing fields: ['variables']",
        ),
        (
            "missing_variables_site_context",
            lambda instance: instance["variables"].pop("site_context"),
            "variables missing fields: ['site_context']",
        ),
        (
            "variables_empty_value",
            lambda instance: instance["variables"].__setitem__("site_context", "  "),
            "variables.site_context must be a non-empty string",
        ),
        (
            "variables_tbd_value",
            lambda instance: instance["variables"].__setitem__("site_context", "TBD"),
            "variables.site_context contains forbidden placeholder value",
        ),
        (
            "missing_policy_refs",
            lambda instance: instance.pop("policy_refs"),
            "project_template_instance missing fields: ['policy_refs']",
        ),
        (
            "missing_locked_policy_flags",
            lambda instance: instance.pop("locked_policy_flags"),
            "project_template_instance missing fields: ['locked_policy_flags']",
        ),
        (
            "video_generation_enabled_true",
            lambda instance: instance["locked_policy_flags"].__setitem__(
                "video_generation_enabled",
                True,
            ),
            "locked_policy_flags.video_generation_enabled must be false",
        ),
        (
            "batch_generation_enabled_true",
            lambda instance: instance["locked_policy_flags"].__setitem__(
                "batch_generation_enabled",
                True,
            ),
            "locked_policy_flags.batch_generation_enabled must be false",
        ),
        (
            "auto_publish_enabled_true",
            lambda instance: instance["locked_policy_flags"].__setitem__(
                "auto_publish_enabled",
                True,
            ),
            "locked_policy_flags.auto_publish_enabled must be false",
        ),
        (
            "draft_direct_to_approved",
            lambda instance: instance["review"].__setitem__("previous_status", "draft"),
            "review transition draft -> approved_for_bid is not allowed",
        ),
        (
            "candidate_direct_to_approved",
            lambda instance: instance["review"].__setitem__("previous_status", "candidate"),
            "review transition candidate -> approved_for_bid is not allowed",
        ),
        (
            "approved_missing_reviewer",
            lambda instance: instance["review"].pop("reviewer"),
            "review missing approved_for_bid fields: ['reviewer']",
        ),
        (
            "approved_check_false",
            lambda instance: instance["review"]["checks"].__setitem__(
                "variables_complete",
                False,
            ),
            "review.checks.variables_complete must be true for approved_for_bid",
        ),
    ],
)
def test_project_template_instance_rejects_invalid_instances(
    case_id: str,
    mutate,
    expected_error: str,
):
    instance = _valid_project_template_instance()
    mutate(instance)

    errors = _validate_project_instance(instance)

    assert any(expected_error in error for error in errors), errors


def test_project_template_prompt_plan_builds_deterministic_safe_plan():
    prompt_templates, registry, _ = _load_static_configs()
    instance = _valid_project_template_instance()

    plan = build_project_template_prompt_plan(instance, prompt_templates, registry, 0)

    assert plan == build_project_template_prompt_plan(instance, prompt_templates, registry, 0)
    assert plan["plan_type"] == "project_template_prompt_plan"
    assert plan["plan_version"] == "027n-r11-a"
    assert plan["project_id"] == instance["project_id"]
    assert plan["project_name"] == instance["project_name"]
    assert plan["template_id"] == TEMPLATE_ID
    assert plan["workflow_id"] == WORKFLOW_ID
    assert plan["candidate_seed"] == 0
    for value in instance["variables"].values():
        assert value in plan["positive_prompt"]
    assert "{" not in plan["positive_prompt"]
    assert "{" not in plan["negative_prompt"]
    assert (
        plan["negative_prompt"]
        == prompt_templates["templates"][TEMPLATE_ID]["negative_prompt_template"]
    )
    assert plan["fixed_parameters"]["batch_size"] == 1
    assert plan["review_status"] == "candidate"
    assert plan["runtime_execution_authorized"] is False
    assert json.loads(json.dumps(plan, ensure_ascii=False)) == plan


def test_project_template_prompt_plan_rejects_unknown_template_id():
    prompt_templates, registry, _ = _load_static_configs()
    instance = _valid_project_template_instance()
    instance["template_id"] = "missing_template"

    with pytest.raises(ValueError, match="template_id must reference an existing template"):
        build_project_template_prompt_plan(instance, prompt_templates, registry, 0)


def test_project_template_prompt_plan_rejects_workflow_mismatch():
    prompt_templates, registry, _ = _load_static_configs()
    instance = _valid_project_template_instance()
    instance["workflow_id"] = "qwen_image_edit_image_to_image"

    with pytest.raises(ValueError, match="workflow_id must match template workflow_id"):
        build_project_template_prompt_plan(instance, prompt_templates, registry, 0)


@pytest.mark.parametrize("candidate_seed", [-1, True, 1.0, "1"])
def test_project_template_prompt_plan_rejects_invalid_candidate_seed(candidate_seed):
    prompt_templates, registry, _ = _load_static_configs()

    with pytest.raises(ValueError, match="candidate_seed must be a non-negative integer"):
        build_project_template_prompt_plan(
            _valid_project_template_instance(),
            prompt_templates,
            registry,
            candidate_seed,
        )


@pytest.mark.parametrize("batch_size", [2, True])
def test_project_template_prompt_plan_rejects_batch_size_other_than_one(batch_size):
    prompt_templates, registry, _ = _load_static_configs()
    prompt_templates["templates"][TEMPLATE_ID]["fixed_parameters"]["batch_size"] = batch_size

    with pytest.raises(ValueError, match="fixed_parameters.batch_size must be 1"):
        build_project_template_prompt_plan(
            _valid_project_template_instance(),
            prompt_templates,
            registry,
            0,
        )


@pytest.mark.parametrize(
    "policy_field",
    ["video_generation_enabled", "batch_generation_enabled", "auto_publish_enabled"],
)
def test_project_template_prompt_plan_rejects_enabled_unsafe_policy(policy_field: str):
    prompt_templates, registry, _ = _load_static_configs()
    prompt_templates["templates"][TEMPLATE_ID]["generation_policy"][policy_field] = True

    with pytest.raises(ValueError, match=rf"generation_policy\.{policy_field} must be false"):
        build_project_template_prompt_plan(
            _valid_project_template_instance(),
            prompt_templates,
            registry,
            0,
        )


def test_project_template_prompt_plan_does_not_mutate_inputs_and_detaches_snapshots():
    prompt_templates, registry, _ = _load_static_configs()
    instance = _valid_project_template_instance()
    original_prompt_templates = deepcopy(prompt_templates)
    original_registry = deepcopy(registry)
    original_instance = deepcopy(instance)

    plan = build_project_template_prompt_plan(instance, prompt_templates, registry, 7)

    assert instance == original_instance
    assert prompt_templates == original_prompt_templates
    assert registry == original_registry
    template = prompt_templates["templates"][TEMPLATE_ID]
    assert plan["fixed_parameters"] == template["fixed_parameters"]
    assert plan["fixed_parameters"] is not template["fixed_parameters"]
    assert plan["generation_policy"] == template["generation_policy"]
    assert plan["generation_policy"] is not template["generation_policy"]
    assert plan["review_policy"] == template["review_policy"]
    assert plan["review_policy"] is not template["review_policy"]
    assert plan["retention_policy"] == template["generation_policy"]["retention_policy"]
    assert plan["retention_policy"] is not template["generation_policy"]["retention_policy"]

    plan["fixed_parameters"]["batch_size"] = 99
    plan["generation_policy"]["video_generation_enabled"] = True
    plan["generation_policy"]["retention_policy"]["auto_delete_enabled"] = True
    plan["review_policy"]["required"] = False
    plan["review_policy"]["checklist"].append("synthetic-check")
    plan["retention_policy"]["auto_delete_enabled"] = True
    assert prompt_templates == original_prompt_templates


def test_project_template_prompt_plan_rejects_undeclared_prompt_variable():
    prompt_templates, registry, _ = _load_static_configs()
    prompt_templates["templates"][TEMPLATE_ID][
        "positive_prompt_template"
    ] += "，{outside_field}"

    with pytest.raises(ValueError, match="contains undeclared variables"):
        build_project_template_prompt_plan(
            _valid_project_template_instance(),
            prompt_templates,
            registry,
            0,
        )


def test_project_template_prompt_plan_rejects_instance_policy_override():
    prompt_templates, registry, _ = _load_static_configs()
    instance = _valid_project_template_instance()
    instance["generation_policy"] = {"batch_generation_enabled": False}

    with pytest.raises(ValueError, match="generation_policy must not be defined"):
        build_project_template_prompt_plan(instance, prompt_templates, registry, 0)


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("api_token", "synthetic-test-value", "must not contain token fields"),
        ("model_path", "/synthetic/model", "must not contain model or output path fields"),
        ("output_path", "/synthetic/output", "must not contain model or output path fields"),
    ],
)
def test_project_template_prompt_plan_rejects_sensitive_runtime_fields(
    field: str,
    value: str,
    expected_error: str,
):
    prompt_templates, registry, _ = _load_static_configs()
    prompt_templates["templates"][TEMPLATE_ID]["fixed_parameters"][field] = value

    with pytest.raises(ValueError, match=expected_error):
        build_project_template_prompt_plan(
            _valid_project_template_instance(),
            prompt_templates,
            registry,
            0,
        )
