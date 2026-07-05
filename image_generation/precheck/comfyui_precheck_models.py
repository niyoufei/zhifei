"""Static data models for ComfyUI workflow runtime precheck planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class PrecheckSeverity(str, Enum):
    """Severity labels for static precheck outcomes."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


class PrecheckStatus(str, Enum):
    """Status values emitted by the R5B static scaffold."""

    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    NOT_EXECUTED = "not_executed"
    DESIGN_ONLY = "design_only"
    AUTHORIZATION_REQUIRED = "authorization_required"


class PrecheckScope(str, Enum):
    """R5B separates static checks from future environment/runtime work."""

    STATIC_PRECHECK = "static_precheck"
    ENVIRONMENT_PRECHECK_DESIGN_ONLY = "environment_precheck_design_only"
    RUNTIME_PRECHECK_REQUIRES_AUTHORIZATION = "runtime_precheck_requires_authorization"


@dataclass(frozen=True, slots=True)
class ExplicitAuthorizationRequired:
    """A future action that R5B may describe but must not execute."""

    action_id: str
    required_node: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PrecheckItem:
    """One planned static, design-only, or future-runtime precheck item."""

    check_id: str
    scope: PrecheckScope
    severity: PrecheckSeverity
    target: str
    allowed_in_r5b: bool
    requires_explicit_authorization: bool
    runtime_forbidden: bool
    description: str

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.value
        data["severity"] = self.severity.value
        return data


@dataclass(frozen=True, slots=True)
class PrecheckResult:
    """Static validation result for one precheck item."""

    check_id: str
    status: PrecheckStatus
    severity: PrecheckSeverity
    message: str
    target: str

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["severity"] = self.severity.value
        return data


@dataclass(frozen=True, slots=True)
class RuntimePrecheckPolicy:
    """Static policy switches that must keep all R5B runtime actions disabled."""

    precheck_policy_version: str
    local_only: bool
    video_generation_enabled: bool
    r5b_static_only: bool
    allow_start_comfyui: bool
    allow_access_localhost: bool
    allow_model_weight_read: bool
    allow_ollama_model_dir_read: bool
    allow_env_file_read: bool
    allow_image_generation: bool
    allow_workflow_dry_run: bool
    require_explicit_authorization_for_runtime: bool
    allowed_static_checks: list[str] = field(default_factory=list)
    design_only_environment_checks: list[str] = field(default_factory=list)
    runtime_checks_requiring_explicit_authorization: list[str] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimePrecheckPolicy":
        return cls(
            precheck_policy_version=str(data.get("precheck_policy_version", "")),
            local_only=bool(data.get("local_only", False)),
            video_generation_enabled=bool(data.get("video_generation_enabled", True)),
            r5b_static_only=bool(data.get("r5b_static_only", False)),
            allow_start_comfyui=bool(data.get("allow_start_comfyui", True)),
            allow_access_localhost=bool(data.get("allow_access_localhost", True)),
            allow_model_weight_read=bool(data.get("allow_model_weight_read", True)),
            allow_ollama_model_dir_read=bool(data.get("allow_ollama_model_dir_read", True)),
            allow_env_file_read=bool(data.get("allow_env_file_read", True)),
            allow_image_generation=bool(data.get("allow_image_generation", True)),
            allow_workflow_dry_run=bool(data.get("allow_workflow_dry_run", True)),
            require_explicit_authorization_for_runtime=bool(
                data.get("require_explicit_authorization_for_runtime", False)
            ),
            allowed_static_checks=[str(item) for item in data.get("allowed_static_checks", [])],
            design_only_environment_checks=[
                str(item) for item in data.get("design_only_environment_checks", [])
            ],
            runtime_checks_requiring_explicit_authorization=[
                str(item) for item in data.get("runtime_checks_requiring_explicit_authorization", [])
            ],
            forbidden_paths=[str(item) for item in data.get("forbidden_paths", [])],
            forbidden_actions=[str(item) for item in data.get("forbidden_actions", [])],
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PrecheckPlan:
    """Static R5B plan; it is not an environment probe or runtime runner."""

    node: str
    registry_path: str
    manifest_path: str
    schema_path: str
    prompt_templates_path: str
    policy_path: str
    items: list[PrecheckItem]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["items"] = [item.as_dict() for item in self.items]
        return data


@dataclass(frozen=True, slots=True)
class PrecheckReport:
    """Machine-readable static report for the R5B scaffold."""

    node: str
    status: PrecheckStatus
    plan: PrecheckPlan
    policy: RuntimePrecheckPolicy
    results: list[PrecheckResult]
    explicit_authorizations_required: list[ExplicitAuthorizationRequired]
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "node": self.node,
            "status": self.status.value,
            "plan": self.plan.as_dict(),
            "policy": self.policy.as_dict(),
            "results": [result.as_dict() for result in self.results],
            "blocked_items": [
                result.as_dict()
                for result in self.results
                if result.status in {PrecheckStatus.FAIL, PrecheckStatus.BLOCKED}
            ],
            "next_authorization_required": [
                item.as_dict() for item in self.explicit_authorizations_required
            ],
            "summary": self.summary,
        }
