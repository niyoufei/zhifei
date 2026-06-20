from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.p0_readiness import (
    DEMO_PROJECT_PATH,
    build_p0_readiness_snapshot,
)


PHASE_ID = "PHASE_1B_DEMO_WORKFLOW_STATIC"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE1B_DEMO_WORKFLOW_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE1B_DEMO_WORKFLOW_STATIC"
NO_GO_STATUS = "NO-GO_PHASE1B_DEMO_WORKFLOW_STATIC"

REQUIRED_DEMO_FLAGS = {
    "sanitized_demo": True,
    "real_business_material": False,
    "external_network_required": False,
    "secret_required": False,
    "safe_to_commit": True,
}

REQUIRED_STEP_IDS = (
    "register_sanitized_project",
    "prove_p0_static_readiness",
    "run_static_boundary_checks",
    "prepare_static_output_index",
    "handoff_to_runtime_gate",
)


def build_phase1b_demo_workflow_snapshot(
    root: str | Path | None = None,
    *,
    p0_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a no-runtime Phase 1B demo workflow snapshot.

    The snapshot consumes only the sanitized P0 demo metadata and P0 static
    readiness output. It does not materialize business outputs, start services,
    visit endpoints, inspect held launcher config contents, or refresh remotes.
    """

    repo_root = Path(root or ".").resolve()
    demo = _demo_contract(repo_root)
    p0 = p0_snapshot if p0_snapshot is not None else build_p0_readiness_snapshot(repo_root)
    p0_status = p0.get("status")

    steps = _workflow_steps(p0_status=p0_status, demo_valid=demo["valid"])
    output_index = _static_output_index()
    checks = _checks(demo=demo, p0_status=p0_status, steps=steps, output_index=output_index)
    failures = [name for name, passed in checks.items() if not passed]
    status = PASS_STATUS if not failures else NO_GO_STATUS

    return {
        "status": status,
        "phase_id": PHASE_ID,
        "failures": failures,
        "workspace_root": str(repo_root),
        "demo_project": demo,
        "p0_readiness": {
            "status": p0_status,
            "failures": p0.get("failures", []),
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json",
        },
        "workflow_steps": steps,
        "output_index": output_index,
        "checks": checks,
        "scope": {
            "phase": "Phase 1B",
            "mode": "local_static_demo_workflow",
            "starts_runtime": False,
            "visits_endpoint": False,
            "runs_launcher": False,
            "reads_real_business_content": False,
            "reads_secrets": False,
            "reads_held_config_content": False,
            "fetch_pull_merge_push": False,
            "materializes_business_outputs": False,
        },
        "forbidden_actions_performed": [],
        "hard_gates_retained": [
            "runtime_start",
            "endpoint_access",
            "launcher_execution",
            "held_config_content_review",
            "real_business_material_access",
            "remote_mutation_or_refresh",
        ],
        "next_gate": (
            "Phase 1C readiness / delivery index"
            if status == PASS_STATUS
            else "repair Phase 1B static workflow failures"
        ),
    }


def format_phase1b_demo_workflow_report(snapshot: dict[str, Any]) -> str:
    step_ids = [item.get("step_id") for item in snapshot.get("workflow_steps", [])]
    output_index = snapshot.get("output_index") or {}
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"demo_project_path: {(snapshot.get('demo_project') or {}).get('path')}",
        f"project_id: {(snapshot.get('demo_project') or {}).get('project_id')}",
        f"p0_readiness_status: {(snapshot.get('p0_readiness') or {}).get('status')}",
        f"workflow_steps: {step_ids}",
        f"output_generation_performed: {output_index.get('output_generation_performed')}",
        f"runtime_gate_required: {output_index.get('runtime_gate_required')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def _demo_contract(root: Path) -> dict[str, Any]:
    path = root / DEMO_PROJECT_PATH
    if not path.exists():
        return {
            "path": str(DEMO_PROJECT_PATH),
            "exists": False,
            "valid": False,
            "reason": "missing",
            "checks": {},
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "path": str(DEMO_PROJECT_PATH),
            "exists": True,
            "valid": False,
            "reason": str(exc),
            "checks": {},
        }

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    requirements = data.get("requirements") if isinstance(data.get("requirements"), list) else []
    plan = data.get("plan") if isinstance(data.get("plan"), dict) else {}
    outline = plan.get("outline") if isinstance(plan.get("outline"), list) else []
    chapter_requirements = (
        plan.get("chapter_requirements")
        if isinstance(plan.get("chapter_requirements"), dict)
        else {}
    )

    checks = {
        **{
            f"metadata_{name}": metadata.get(name) is expected
            for name, expected in REQUIRED_DEMO_FLAGS.items()
        },
        "has_project_id": bool(data.get("project_id")),
        "has_topic": bool(data.get("topic")),
        "has_requirements": bool(requirements),
        "has_outline": bool(outline),
        "has_final_review_checklist": "Final review checklist" in outline,
        "has_key_difficult_works": "Key and difficult works" in outline,
    }

    return {
        "path": str(DEMO_PROJECT_PATH),
        "exists": True,
        "valid": all(checks.values()),
        "checks": checks,
        "project_id": data.get("project_id"),
        "topic_present": bool(data.get("topic")),
        "requirement_count": len(requirements),
        "outline_count": len(outline),
        "chapter_requirement_count": len(chapter_requirements),
    }


def _workflow_steps(*, p0_status: Any, demo_valid: bool) -> list[dict[str, Any]]:
    p0_ready = p0_status == "PASS_P0_READINESS_STATIC"
    return [
        {
            "step_id": "register_sanitized_project",
            "status": "ready" if demo_valid else "blocked",
            "input": str(DEMO_PROJECT_PATH),
            "output": "metadata-only project registration snapshot",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "step_id": "prove_p0_static_readiness",
            "status": "ready" if p0_ready else "blocked",
            "input": "scripts/p0_readiness.py --json",
            "output": "P0 static readiness evidence",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "step_id": "run_static_boundary_checks",
            "status": "ready" if demo_valid and p0_ready else "blocked",
            "input": "sanitized demo metadata plus P0 readiness snapshot",
            "output": "no forbidden action proof",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "step_id": "prepare_static_output_index",
            "status": "ready" if demo_valid and p0_ready else "blocked",
            "input": "Phase 1B static workflow contract",
            "output": "planned output index without materialized business files",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "step_id": "handoff_to_runtime_gate",
            "status": "blocked_until_separate_gate",
            "input": "Phase 1B static report",
            "output": "manual runtime/endpoint gate request only",
            "runtime_required": True,
            "endpoint_required": True,
        },
    ]


def _static_output_index() -> dict[str, Any]:
    return {
        "mode": "planned_static_index_only",
        "output_generation_performed": False,
        "runtime_gate_required": True,
        "materialized_outputs": [],
        "planned_entries": [
            {
                "id": "demo_project_registration",
                "source": str(DEMO_PROJECT_PATH),
                "kind": "sanitized_project_metadata",
                "status": "available_static_input",
            },
            {
                "id": "p0_static_readiness_snapshot",
                "source": "scripts/p0_readiness.py --json",
                "kind": "static_readiness_evidence",
                "status": "must_pass_before_runtime_gate",
            },
            {
                "id": "phase1b_static_workflow_report",
                "source": "scripts/phase1_demo_workflow.py --json",
                "kind": "static_workflow_evidence",
                "status": "available_after_clean_commit",
            },
            {
                "id": "future_runtime_outputs",
                "source": "build/demo_runtime_gate/*",
                "kind": "future_runtime_or_endpoint_artifacts",
                "status": "blocked_until_separate_runtime_endpoint_gate",
            },
        ],
    }


def _checks(
    *,
    demo: dict[str, Any],
    p0_status: Any,
    steps: list[dict[str, Any]],
    output_index: dict[str, Any],
) -> dict[str, bool]:
    step_ids = {str(item.get("step_id")) for item in steps}
    return {
        "demo_contract_valid": demo["valid"] is True,
        "p0_readiness_static_pass": p0_status == "PASS_P0_READINESS_STATIC",
        "workflow_has_required_steps": set(REQUIRED_STEP_IDS).issubset(step_ids),
        "workflow_keeps_runtime_blocked": any(
            item.get("step_id") == "handoff_to_runtime_gate"
            and item.get("status") == "blocked_until_separate_gate"
            for item in steps
        ),
        "output_index_is_static_only": output_index.get("output_generation_performed") is False
        and output_index.get("materialized_outputs") == [],
        "output_index_retains_runtime_gate": output_index.get("runtime_gate_required") is True,
    }
