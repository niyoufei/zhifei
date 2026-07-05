"""Static ComfyUI workflow precheck plan construction for R5B."""

from __future__ import annotations

from image_generation.precheck.comfyui_precheck_models import (
    ExplicitAuthorizationRequired,
    PrecheckItem,
    PrecheckPlan,
    PrecheckScope,
    PrecheckSeverity,
)


NODE = "LOCAL-LAUNCHER-027N-R5B-COMFYUI-WORKFLOW-RUNTIME-PRECHECK-SCAFFOLD-IMPLEMENTATION-GATE"
REGISTRY_PATH = "configs/image-generation-workflow-registry.json"
MANIFEST_PATH = "configs/comfyui-workflow-manifest.json"
SCHEMA_PATH = "configs/image-generation-workflow-contract-schema.json"
PROMPT_TEMPLATES_PATH = "configs/image-generation-prompt-templates.json"
POLICY_PATH = "configs/comfyui-runtime-precheck-policy.json"

STATIC_CHECKS = (
    "registry_exists",
    "manifest_exists",
    "schema_exists",
    "workflow_json_status_pending",
    "workflow_json_ref_environment_neutral",
    "runtime_enabled_false",
    "no_video_generation_true",
    "input_binding_complete",
    "output_policy_single_image",
    "prompt_template_mapping_complete",
    "video_generation_disabled",
)

DESIGN_ONLY_ENVIRONMENT_CHECKS = (
    "comfyui_install_path_exists",
    "workflow_json_file_exists",
    "custom_nodes_exist",
    "output_directory_writable",
    "port_available",
    "model_reference_resolvable",
)

RUNTIME_CHECKS_REQUIRING_AUTHORIZATION = (
    "start_comfyui",
    "access_localhost",
    "service_health_check",
    "read_real_model_directory",
    "workflow_dry_run",
    "generate_image",
)


def build_precheck_plan() -> PrecheckPlan:
    """Build the static R5B plan without probing ComfyUI or runtime state."""

    items: list[PrecheckItem] = []
    items.extend(_static_items())
    items.extend(_design_only_environment_items())
    items.extend(_runtime_authorization_items())
    return PrecheckPlan(
        node=NODE,
        registry_path=REGISTRY_PATH,
        manifest_path=MANIFEST_PATH,
        schema_path=SCHEMA_PATH,
        prompt_templates_path=PROMPT_TEMPLATES_PATH,
        policy_path=POLICY_PATH,
        items=items,
    )


def runtime_authorizations_required() -> list[ExplicitAuthorizationRequired]:
    """Return later-node runtime actions that R5B must not execute."""

    return [
        ExplicitAuthorizationRequired(
            action_id="environment_precheck",
            required_node="LOCAL-LAUNCHER-027N-R5C-or-later-explicit-environment-precheck-gate",
            reason="R5B may describe environment checks but must not inspect real services, ports, or model paths.",
        ),
        ExplicitAuthorizationRequired(
            action_id="single_image_generation",
            required_node="LOCAL-LAUNCHER-027N-R6-or-later-explicit-single-image-generation-gate",
            reason="R5B must not execute workflows, run inference, or generate images.",
        ),
    ]


def _static_items() -> list[PrecheckItem]:
    descriptions = {
        "registry_exists": "Confirm the workflow registry JSON is present and parseable.",
        "manifest_exists": "Confirm the ComfyUI workflow manifest JSON is present and parseable.",
        "schema_exists": "Confirm the workflow contract schema JSON is present and parseable.",
        "workflow_json_status_pending": "Confirm all workflow JSON statuses remain pending_real_workflow.",
        "workflow_json_ref_environment_neutral": "Confirm workflow JSON refs are null or relative, not machine paths.",
        "runtime_enabled_false": "Confirm runtime_enabled remains false for registry and manifest entries.",
        "no_video_generation_true": "Confirm every workflow explicitly forbids video generation.",
        "input_binding_complete": "Confirm each workflow has a known static input binding profile.",
        "output_policy_single_image": "Confirm output policy is single-image, local-only, no batch, no auto-upload.",
        "prompt_template_mapping_complete": "Confirm prompt templates map to known workflow contract ids.",
        "video_generation_disabled": "Confirm top-level video_generation_enabled remains false.",
    }
    targets = {
        "registry_exists": REGISTRY_PATH,
        "manifest_exists": MANIFEST_PATH,
        "schema_exists": SCHEMA_PATH,
        "workflow_json_status_pending": MANIFEST_PATH,
        "workflow_json_ref_environment_neutral": f"{REGISTRY_PATH}; {MANIFEST_PATH}",
        "runtime_enabled_false": f"{REGISTRY_PATH}; {MANIFEST_PATH}",
        "no_video_generation_true": f"{REGISTRY_PATH}; {MANIFEST_PATH}",
        "input_binding_complete": f"{REGISTRY_PATH}; {MANIFEST_PATH}",
        "output_policy_single_image": "image_generation/workflows/workflow_output_policy.py",
        "prompt_template_mapping_complete": PROMPT_TEMPLATES_PATH,
        "video_generation_disabled": f"{POLICY_PATH}; {REGISTRY_PATH}; {MANIFEST_PATH}",
    }
    return [
        PrecheckItem(
            check_id=check_id,
            scope=PrecheckScope.STATIC_PRECHECK,
            severity=PrecheckSeverity.ERROR,
            target=targets[check_id],
            allowed_in_r5b=True,
            requires_explicit_authorization=False,
            runtime_forbidden=False,
            description=descriptions[check_id],
        )
        for check_id in STATIC_CHECKS
    ]


def _design_only_environment_items() -> list[PrecheckItem]:
    return [
        PrecheckItem(
            check_id=check_id,
            scope=PrecheckScope.ENVIRONMENT_PRECHECK_DESIGN_ONLY,
            severity=PrecheckSeverity.WARNING,
            target="future explicit environment precheck node",
            allowed_in_r5b=False,
            requires_explicit_authorization=True,
            runtime_forbidden=True,
            description=f"Design-only placeholder for future environment check: {check_id}.",
        )
        for check_id in DESIGN_ONLY_ENVIRONMENT_CHECKS
    ]


def _runtime_authorization_items() -> list[PrecheckItem]:
    return [
        PrecheckItem(
            check_id=check_id,
            scope=PrecheckScope.RUNTIME_PRECHECK_REQUIRES_AUTHORIZATION,
            severity=PrecheckSeverity.BLOCKER,
            target="future explicit runtime authorization node",
            allowed_in_r5b=False,
            requires_explicit_authorization=True,
            runtime_forbidden=True,
            description=f"Runtime action forbidden in R5B and allowed only after explicit authorization: {check_id}.",
        )
        for check_id in RUNTIME_CHECKS_REQUIRING_AUTHORIZATION
    ]
