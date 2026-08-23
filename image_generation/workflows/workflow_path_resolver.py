"""Environment-neutral workflow JSON path resolver."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import unicodedata


PRODUCTION_COMFYUI_WORKFLOW_ROOT = Path("workflows/comfyui")

_URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class ProductionWorkflowPathError(ValueError):
    """Fail-closed production workflow path error with a stable reason code."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class WorkflowPathResolution:
    """Resolved workflow JSON reference without touching the filesystem."""

    workflow_id: str
    workflow_json_ref: str | None
    resolved_path: str | None
    workflow_json_status: str
    exists_checked: bool = False


class WorkflowPathResolver:
    """Resolve relative workflow JSON references without runtime checks."""

    def __init__(
        self,
        workflow_base_dir: str | Path = PRODUCTION_COMFYUI_WORKFLOW_ROOT,
    ):
        self._workflow_base_dir = Path(workflow_base_dir)

    def resolve(
        self,
        workflow_id: str,
        workflow_json_ref: str | None,
        workflow_json_status: str,
    ) -> WorkflowPathResolution:
        """Build an environment-neutral path plan; do not read files."""

        if workflow_json_ref is None:
            return WorkflowPathResolution(
                workflow_id=workflow_id,
                workflow_json_ref=None,
                resolved_path=None,
                workflow_json_status=workflow_json_status,
            )

        ref_text = str(workflow_json_ref)
        ref_path = PurePosixPath(ref_text)
        if ref_path.is_absolute() or ref_text.startswith("~") or ".." in ref_path.parts:
            raise ValueError(f"workflow_json_ref must be relative and environment neutral: {ref_text}")

        resolved_path = self._workflow_base_dir / Path(ref_text)
        return WorkflowPathResolution(
            workflow_id=workflow_id,
            workflow_json_ref=ref_text,
            resolved_path=str(resolved_path),
            workflow_json_status=workflow_json_status,
        )


def validate_production_workflow_relative_path(
    workflow_relative_path: object,
) -> PurePosixPath:
    """Validate a workflow path relative to the fixed production asset root."""

    if not isinstance(workflow_relative_path, str):
        raise ProductionWorkflowPathError("production_workflow_path_not_string")
    if not workflow_relative_path.strip():
        raise ProductionWorkflowPathError("production_workflow_path_empty")
    if any(unicodedata.category(character) == "Cc" for character in workflow_relative_path):
        raise ProductionWorkflowPathError("production_workflow_path_control_character")

    posix_path = PurePosixPath(workflow_relative_path)
    windows_path = PureWindowsPath(workflow_relative_path)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ProductionWorkflowPathError("production_workflow_path_absolute")
    if workflow_relative_path.startswith("~"):
        raise ProductionWorkflowPathError("production_workflow_path_home_reference")
    if "\\" in workflow_relative_path:
        raise ProductionWorkflowPathError("production_workflow_path_backslash")
    if _URI_SCHEME.match(workflow_relative_path):
        raise ProductionWorkflowPathError("production_workflow_path_url")

    raw_parts = workflow_relative_path.split("/")
    if any(part in {".", ".."} for part in raw_parts):
        raise ProductionWorkflowPathError("production_workflow_path_traversal")

    production_root_text = PRODUCTION_COMFYUI_WORKFLOW_ROOT.as_posix()
    if workflow_relative_path == production_root_text or workflow_relative_path.startswith(
        f"{production_root_text}/"
    ):
        raise ProductionWorkflowPathError(
            "production_workflow_path_root_prefix_repeated"
        )

    if (
        workflow_relative_path.endswith("/")
        or not workflow_relative_path.endswith(".json")
        or posix_path.name == ".json"
    ):
        raise ProductionWorkflowPathError("production_workflow_path_invalid_suffix")

    return posix_path


def resolve_production_workflow_path(
    repository_root: str | Path,
    workflow_relative_path: object,
) -> Path:
    """Resolve a validated workflow path within the fixed production root."""

    relative_path = validate_production_workflow_relative_path(workflow_relative_path)
    repository_root_resolved = _resolve_repository_root(repository_root)
    production_root = repository_root_resolved / PRODUCTION_COMFYUI_WORKFLOW_ROOT

    try:
        production_root_resolved = production_root.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ProductionWorkflowPathError(
            "production_workflow_path_outside_root"
        ) from exc

    if not _is_relative_to(production_root_resolved, repository_root_resolved):
        raise ProductionWorkflowPathError("production_workflow_path_outside_root")

    candidate = production_root.joinpath(*relative_path.parts)
    try:
        candidate_resolved = candidate.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ProductionWorkflowPathError(
            "production_workflow_path_symlink_escape"
        ) from exc

    if not _is_relative_to(candidate_resolved, production_root_resolved):
        raise ProductionWorkflowPathError("production_workflow_path_symlink_escape")
    return candidate_resolved


def _resolve_repository_root(repository_root: str | Path) -> Path:
    if not isinstance(repository_root, (str, Path)):
        raise ProductionWorkflowPathError("production_workflow_repository_root_invalid")
    root_text = str(repository_root)
    if (
        not root_text.strip()
        or root_text.startswith("~")
        or _URI_SCHEME.match(root_text)
        or any(unicodedata.category(character) == "Cc" for character in root_text)
    ):
        raise ProductionWorkflowPathError("production_workflow_repository_root_invalid")
    try:
        return Path(repository_root).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise ProductionWorkflowPathError(
            "production_workflow_repository_root_invalid"
        ) from exc


def _is_relative_to(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True
