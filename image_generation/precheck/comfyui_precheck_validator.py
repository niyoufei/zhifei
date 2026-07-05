"""Static validators for the R5B ComfyUI workflow runtime precheck scaffold."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any

from image_generation.precheck.comfyui_precheck_models import (
    PrecheckReport,
    PrecheckResult,
    PrecheckSeverity,
    PrecheckStatus,
    RuntimePrecheckPolicy,
)
from image_generation.precheck.comfyui_precheck_plan import (
    DESIGN_ONLY_ENVIRONMENT_CHECKS,
    RUNTIME_CHECKS_REQUIRING_AUTHORIZATION,
    STATIC_CHECKS,
    build_precheck_plan,
    runtime_authorizations_required,
)
from image_generation.workflows.workflow_input_binding import DEFAULT_INPUT_BINDING_PROFILES
from image_generation.workflows.workflow_output_policy import DEFAULT_OUTPUT_POLICIES
from image_generation.workflows.workflow_validator import REQUIRED_WORKFLOW_IDS


REQUIRED_POLICY_FIELDS = {
    "precheck_policy_version",
    "local_only",
    "video_generation_enabled",
    "r5b_static_only",
    "allow_start_comfyui",
    "allow_access_localhost",
    "allow_model_weight_read",
    "allow_ollama_model_dir_read",
    "allow_env_file_read",
    "allow_image_generation",
    "allow_workflow_dry_run",
    "require_explicit_authorization_for_runtime",
    "allowed_static_checks",
    "design_only_environment_checks",
    "runtime_checks_requiring_explicit_authorization",
    "forbidden_paths",
    "forbidden_actions",
}

REQUIRED_FORBIDDEN_ACTIONS = {
    "start_comfyui",
    "access_localhost",
    "run_inference",
    "generate_image",
    "read_model_weights",
    "read_ollama_models",
    "read_env",
    "scan_full_disk",
    "deploy_video_generation",
}

RUNTIME_ALLOW_FALSE_FIELDS = {
    "allow_start_comfyui",
    "allow_access_localhost",
    "allow_model_weight_read",
    "allow_ollama_model_dir_read",
    "allow_env_file_read",
    "allow_image_generation",
    "allow_workflow_dry_run",
}


def validate_static_precheck(repo_root: str | Path = ".") -> PrecheckReport:
    """Return a static report; never probe services, ports, models, or env files."""

    root = Path(repo_root)
    plan = build_precheck_plan()
    loaded: dict[str, Any] = {}
    results: list[PrecheckResult] = []

    for check_id, path_text in (
        ("registry_exists", plan.registry_path),
        ("manifest_exists", plan.manifest_path),
        ("schema_exists", plan.schema_path),
        ("policy_exists", plan.policy_path),
        ("prompt_templates_exists", plan.prompt_templates_path),
    ):
        path = root / path_text
        data, error = _load_json(path)
        if error:
            results.append(_result(check_id, PrecheckStatus.FAIL, error, str(path)))
        else:
            loaded[check_id] = data
            results.append(_result(check_id, PrecheckStatus.PASS, "JSON parsed", str(path)))

    policy_data = loaded.get("policy_exists") or {}
    registry = loaded.get("registry_exists") or {}
    manifest = loaded.get("manifest_exists") or {}
    schema = loaded.get("schema_exists") or {}
    prompt_templates = loaded.get("prompt_templates_exists") or {}
    policy = RuntimePrecheckPolicy.from_dict(policy_data)

    results.extend(_validate_policy(policy_data))
    results.extend(_validate_schema(schema))
    results.extend(_validate_workflow_surfaces(registry, manifest))
    results.extend(_validate_output_policy(registry, manifest))
    results.extend(_validate_prompt_templates(prompt_templates, registry))

    failed = [result for result in results if result.status in {PrecheckStatus.FAIL, PrecheckStatus.BLOCKED}]
    status = PrecheckStatus.BLOCKED if failed else PrecheckStatus.PASS
    summary = (
        "R5B static ComfyUI workflow precheck scaffold passed; no runtime checks executed."
        if status is PrecheckStatus.PASS
        else "R5B static ComfyUI workflow precheck scaffold blocked by static validation failures."
    )
    return PrecheckReport(
        node=plan.node,
        status=status,
        plan=plan,
        policy=policy,
        results=results,
        explicit_authorizations_required=runtime_authorizations_required(),
        summary=summary,
    )


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "file missing"
    except json.JSONDecodeError as exc:
        return None, f"JSON parse failed: {exc}"
    if not isinstance(data, dict):
        return None, "JSON root must be an object"
    return data, None


def _validate_policy(policy_data: dict[str, Any]) -> list[PrecheckResult]:
    results: list[PrecheckResult] = []
    missing = sorted(REQUIRED_POLICY_FIELDS - set(policy_data.keys()))
    results.append(
        _result(
            "policy_fields_complete",
            PrecheckStatus.FAIL if missing else PrecheckStatus.PASS,
            f"missing policy fields: {missing}" if missing else "policy fields complete",
            "configs/comfyui-runtime-precheck-policy.json",
        )
    )

    expected_values: dict[str, Any] = {
        "local_only": True,
        "video_generation_enabled": False,
        "r5b_static_only": True,
        "require_explicit_authorization_for_runtime": True,
    }
    expected_values.update({field: False for field in RUNTIME_ALLOW_FALSE_FIELDS})
    for field, expected in expected_values.items():
        actual = policy_data.get(field)
        results.append(
            _result(
                f"policy_{field}",
                PrecheckStatus.PASS if actual is expected else PrecheckStatus.FAIL,
                f"{field}={actual!r}",
                "configs/comfyui-runtime-precheck-policy.json",
            )
        )

    list_expectations = {
        "allowed_static_checks": set(STATIC_CHECKS),
        "design_only_environment_checks": set(DESIGN_ONLY_ENVIRONMENT_CHECKS),
        "runtime_checks_requiring_explicit_authorization": set(
            RUNTIME_CHECKS_REQUIRING_AUTHORIZATION
        ),
        "forbidden_actions": REQUIRED_FORBIDDEN_ACTIONS,
    }
    for field, expected in list_expectations.items():
        actual = set(policy_data.get(field) or [])
        missing_items = sorted(expected - actual)
        results.append(
            _result(
                f"policy_{field}",
                PrecheckStatus.FAIL if missing_items else PrecheckStatus.PASS,
                f"missing {field}: {missing_items}" if missing_items else f"{field} complete",
                "configs/comfyui-runtime-precheck-policy.json",
            )
        )
    return results


def _validate_schema(schema: dict[str, Any]) -> list[PrecheckResult]:
    required = set(schema.get("required") or [])
    expected = {"runtime_enabled", "no_video_generation", "disabled_video_generation"}
    missing = sorted(expected - required)
    return [
        _result(
            "schema_exists",
            PrecheckStatus.FAIL if missing else PrecheckStatus.PASS,
            f"schema missing required guards: {missing}" if missing else "schema guard fields present",
            "configs/image-generation-workflow-contract-schema.json",
        )
    ]


def _validate_workflow_surfaces(registry: dict[str, Any], manifest: dict[str, Any]) -> list[PrecheckResult]:
    results: list[PrecheckResult] = []
    registry_workflows = registry.get("workflows")
    manifest_workflows = manifest.get("workflows")
    if not isinstance(registry_workflows, dict):
        registry_workflows = {}
    if not isinstance(manifest_workflows, dict):
        manifest_workflows = {}

    for label, workflows, target in (
        ("registry", registry_workflows, "configs/image-generation-workflow-registry.json"),
        ("manifest", manifest_workflows, "configs/comfyui-workflow-manifest.json"),
    ):
        missing = sorted(REQUIRED_WORKFLOW_IDS - set(workflows.keys()))
        results.append(
            _result(
                f"{label}_contains_required_workflows",
                PrecheckStatus.FAIL if missing else PrecheckStatus.PASS,
                f"{label} missing workflows: {missing}" if missing else f"{label} contains 3 workflows",
                target,
            )
        )
        results.extend(_validate_workflow_entries(label, workflows, target))

    video_disabled = (
        registry.get("video_generation_enabled") is False
        and manifest.get("video_generation_enabled") is False
    )
    results.append(
        _result(
            "video_generation_disabled",
            PrecheckStatus.PASS if video_disabled else PrecheckStatus.FAIL,
            "video_generation_enabled=false in registry and manifest"
            if video_disabled
            else "video_generation_enabled must be false in registry and manifest",
            "configs/image-generation-workflow-registry.json; configs/comfyui-workflow-manifest.json",
        )
    )
    return results


def _validate_workflow_entries(label: str, workflows: dict[str, Any], target: str) -> list[PrecheckResult]:
    results: list[PrecheckResult] = []
    runtime_errors: list[str] = []
    video_errors: list[str] = []
    status_errors: list[str] = []
    ref_errors: list[str] = []
    input_errors: list[str] = []
    for workflow_id, entry in workflows.items():
        if not isinstance(entry, dict):
            runtime_errors.append(workflow_id)
            continue
        if entry.get("runtime_enabled") is not False:
            runtime_errors.append(workflow_id)
        if entry.get("no_video_generation") is not True:
            video_errors.append(workflow_id)
        if entry.get("workflow_json_status") != "pending_real_workflow":
            status_errors.append(workflow_id)
        if not _is_environment_neutral_ref(entry.get("workflow_json_ref")):
            ref_errors.append(workflow_id)
        profile_id = entry.get("input_binding_profile")
        if profile_id not in DEFAULT_INPUT_BINDING_PROFILES:
            input_errors.append(workflow_id)

    checks = (
        ("runtime_enabled_false", runtime_errors, "runtime_enabled must be false"),
        ("no_video_generation_true", video_errors, "no_video_generation must be true"),
        (
            "workflow_json_status_pending",
            status_errors,
            "workflow_json_status must be pending_real_workflow",
        ),
        (
            "workflow_json_ref_environment_neutral",
            ref_errors,
            "workflow_json_ref must be null or relative and environment neutral",
        ),
        ("input_binding_complete", input_errors, "input_binding_profile must be known"),
    )
    for check_id, errors, message in checks:
        results.append(
            _result(
                f"{label}_{check_id}",
                PrecheckStatus.FAIL if errors else PrecheckStatus.PASS,
                f"{message}: {errors}" if errors else f"{label} {check_id} passed",
                target,
            )
        )
    return results


def _validate_output_policy(registry: dict[str, Any], manifest: dict[str, Any]) -> list[PrecheckResult]:
    workflows = {}
    for surface in (registry.get("workflows"), manifest.get("workflows")):
        if isinstance(surface, dict):
            workflows.update({k: v for k, v in surface.items() if isinstance(v, dict)})

    errors: list[str] = []
    for workflow_id, entry in workflows.items():
        policy_id = entry.get("output_policy_id")
        policy = DEFAULT_OUTPUT_POLICIES.get(policy_id)
        if not policy:
            errors.append(f"{workflow_id}: unknown output_policy_id {policy_id!r}")
            continue
        if policy.get("max_images") != 1:
            errors.append(f"{workflow_id}: max_images must be 1")
        if policy.get("auto_upload") is not False:
            errors.append(f"{workflow_id}: auto_upload must be false")
        if policy.get("batch_generation") is not False:
            errors.append(f"{workflow_id}: batch_generation must be false")
    return [
        _result(
            "output_policy_single_image",
            PrecheckStatus.FAIL if errors else PrecheckStatus.PASS,
            f"output policy errors: {errors}" if errors else "output policy is single-image, no batch, no auto-upload",
            "image_generation/workflows/workflow_output_policy.py",
        )
    ]


def _validate_prompt_templates(
    prompt_templates: dict[str, Any],
    registry: dict[str, Any],
) -> list[PrecheckResult]:
    templates = prompt_templates.get("templates")
    workflows = registry.get("workflows")
    if not isinstance(templates, dict) or not isinstance(workflows, dict):
        return [
            _result(
                "prompt_template_mapping_complete",
                PrecheckStatus.FAIL,
                "prompt templates and registry workflows must be objects",
                "configs/image-generation-prompt-templates.json",
            )
        ]

    contract_ids = {
        entry.get("workflow_contract_id")
        for entry in workflows.values()
        if isinstance(entry, dict)
    }
    used_contract_ids: set[str] = set()
    errors: list[str] = []
    for template_id, template in templates.items():
        if not isinstance(template, dict):
            errors.append(f"{template_id}: template must be object")
            continue
        contract_id = template.get("workflow_contract_id")
        if contract_id not in contract_ids:
            errors.append(f"{template_id}: unknown workflow_contract_id {contract_id!r}")
        else:
            used_contract_ids.add(str(contract_id))
        if not template.get("qwen_prompt_zh") or not template.get("flux_prompt_en"):
            errors.append(f"{template_id}: missing static prompt mapping")
    missing_contracts = sorted(str(item) for item in contract_ids - used_contract_ids)
    if missing_contracts:
        errors.append(f"unused workflow contracts: {missing_contracts}")

    return [
        _result(
            "prompt_template_mapping_complete",
            PrecheckStatus.FAIL if errors else PrecheckStatus.PASS,
            f"prompt template mapping errors: {errors}" if errors else "prompt template mapping complete",
            "configs/image-generation-prompt-templates.json",
        )
    ]


def _is_environment_neutral_ref(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    ref = PurePosixPath(value)
    return not (
        ref.is_absolute()
        or value.startswith(("~", "file://"))
        or ".." in ref.parts
        or "/Users/" in value
        or "\\Users\\" in value
    )


def _result(
    check_id: str,
    status: PrecheckStatus,
    message: str,
    target: str,
) -> PrecheckResult:
    severity = PrecheckSeverity.ERROR if status is PrecheckStatus.FAIL else PrecheckSeverity.INFO
    return PrecheckResult(
        check_id=check_id,
        status=status,
        severity=severity,
        message=message,
        target=target,
    )
