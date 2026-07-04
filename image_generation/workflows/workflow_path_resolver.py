"""Environment-neutral workflow JSON path resolver."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


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

    def __init__(self, workflow_base_dir: str | Path = "workflows/comfyui"):
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
