from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.p0_readiness import build_p0_readiness_snapshot
from backend.zhifei_autoplan.phase1_demo_workflow import (
    PASS_STATUS as PHASE1B_PASS_STATUS,
    build_phase1b_demo_workflow_snapshot,
)


PHASE_ID = "PHASE_1C_READINESS_DELIVERY_INDEX_STATIC"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE1C_READINESS_DELIVERY_INDEX_STATIC_REPORT"
PASS_STATUS = "PASS_PHASE1C_READINESS_DELIVERY_INDEX_STATIC"
NO_GO_STATUS = "NO-GO_PHASE1C_READINESS_DELIVERY_INDEX_STATIC"


def build_phase1c_delivery_index_snapshot(
    root: str | Path | None = None,
    *,
    p0_snapshot: dict[str, Any] | None = None,
    phase1b_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the no-runtime Phase 1 readiness and local delivery index."""

    repo_root = Path(root or ".").resolve()
    p0 = p0_snapshot if p0_snapshot is not None else build_p0_readiness_snapshot(repo_root)
    phase1b = (
        phase1b_snapshot
        if phase1b_snapshot is not None
        else build_phase1b_demo_workflow_snapshot(repo_root, p0_snapshot=p0)
    )

    readiness_layers = _readiness_layers(p0_status=p0.get("status"), phase1b_status=phase1b.get("status"))
    delivery_entries = _delivery_entries()
    artifact_rules = _artifact_index_rules()
    hard_gates = _hard_gate_matrix()
    checks = _checks(
        p0=p0,
        phase1b=phase1b,
        readiness_layers=readiness_layers,
        delivery_entries=delivery_entries,
        artifact_rules=artifact_rules,
        hard_gates=hard_gates,
    )
    failures = [name for name, passed in checks.items() if not passed]
    status = PASS_STATUS if not failures else NO_GO_STATUS

    return {
        "status": status,
        "phase_id": PHASE_ID,
        "failures": failures,
        "workspace_root": str(repo_root),
        "readiness_layers": readiness_layers,
        "delivery_entries": delivery_entries,
        "artifact_index_rules": artifact_rules,
        "hard_gate_matrix": hard_gates,
        "source_evidence": {
            "p0_readiness_status": p0.get("status"),
            "p0_failures": p0.get("failures", []),
            "phase1b_status": phase1b.get("status"),
            "phase1b_failures": phase1b.get("failures", []),
            "phase1b_output_generation_performed": (
                (phase1b.get("output_index") or {}).get("output_generation_performed")
            ),
            "phase1b_materialized_outputs": (
                (phase1b.get("output_index") or {}).get("materialized_outputs")
            ),
        },
        "checks": checks,
        "scope": {
            "phase": "Phase 1C",
            "mode": "local_static_readiness_delivery_index",
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
        "next_gate": (
            "Phase 1D docs / RUNBOOK closure"
            if status == PASS_STATUS
            else "repair Phase 1C delivery index failures"
        ),
    }


def format_phase1c_delivery_index_report(snapshot: dict[str, Any]) -> str:
    layer_ids = [item.get("layer_id") for item in snapshot.get("readiness_layers", [])]
    entry_ids = [item.get("entry_id") for item in snapshot.get("delivery_entries", [])]
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"readiness_layers: {layer_ids}",
        f"delivery_entries: {entry_ids}",
        f"p0_readiness_status: {(snapshot.get('source_evidence') or {}).get('p0_readiness_status')}",
        f"phase1b_status: {(snapshot.get('source_evidence') or {}).get('phase1b_status')}",
        f"materializes_business_outputs: {(snapshot.get('scope') or {}).get('materializes_business_outputs')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase1c_delivery_index_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)


def _readiness_layers(*, p0_status: Any, phase1b_status: Any) -> list[dict[str, Any]]:
    return [
        {
            "layer_id": "p0_static_readiness",
            "phase": "P0",
            "status": "ready" if p0_status == "PASS_P0_READINESS_STATIC" else "blocked",
            "evidence": "scripts/p0_readiness.py --json",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "layer_id": "phase1b_static_demo_workflow",
            "phase": "Phase 1B",
            "status": "ready" if phase1b_status == PHASE1B_PASS_STATUS else "blocked",
            "evidence": "scripts/phase1_demo_workflow.py --json",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "layer_id": "phase1c_local_delivery_index",
            "phase": "Phase 1C",
            "status": "current_static_gate",
            "evidence": "scripts/phase1_delivery_index.py --json",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "layer_id": "phase1d_docs_runbook_closure",
            "phase": "Phase 1D",
            "status": "planned_next",
            "evidence": "README.md, RUNBOOK.md, docs/openclaw-zhifei-doc-*.md",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "layer_id": "phase1e_static_test_matrix",
            "phase": "Phase 1E",
            "status": "planned_after_docs_closure",
            "evidence": "unit and CLI matrix, no-runtime negative proof",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "layer_id": "runtime_endpoint_launcher_gates",
            "phase": "Post Phase 1 static",
            "status": "blocked_until_manual_gate",
            "evidence": "separate approval required",
            "runtime_required": True,
            "endpoint_required": True,
        },
    ]


def _delivery_entries() -> list[dict[str, Any]]:
    return [
        {
            "entry_id": "phase1a_local_baseline_index",
            "path": "docs/openclaw-zhifei-doc-phase1-local-baseline.md",
            "kind": "baseline_index_doc",
            "materialized": True,
            "runtime_required": False,
        },
        {
            "entry_id": "p0_static_readiness_cli",
            "path": "scripts/p0_readiness.py",
            "kind": "static_cli",
            "materialized": True,
            "runtime_required": False,
        },
        {
            "entry_id": "phase1b_demo_workflow_cli",
            "path": "scripts/phase1_demo_workflow.py",
            "kind": "static_cli",
            "materialized": True,
            "runtime_required": False,
        },
        {
            "entry_id": "phase1b_demo_workflow_doc",
            "path": "docs/openclaw-zhifei-doc-phase1b-demo-workflow.md",
            "kind": "workflow_doc",
            "materialized": True,
            "runtime_required": False,
        },
        {
            "entry_id": "phase1c_delivery_index_cli",
            "path": "scripts/phase1_delivery_index.py",
            "kind": "static_cli",
            "materialized": True,
            "runtime_required": False,
        },
        {
            "entry_id": "phase1c_delivery_index_doc",
            "path": "docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md",
            "kind": "delivery_index_doc",
            "materialized": True,
            "runtime_required": False,
        },
    ]


def _artifact_index_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule_id": "static_evidence_only_before_runtime_gate",
            "description": "Phase 1C indexes docs, static CLIs, and test evidence only.",
            "allowed": True,
        },
        {
            "rule_id": "no_business_output_materialization",
            "description": "Markdown, DOCX, XLSX, PPTX, PDF, HTML, and runtime build outputs stay blocked.",
            "allowed": False,
        },
        {
            "rule_id": "future_outputs_require_runtime_endpoint_gate",
            "description": "Any generated demo output must wait for a separate runtime or endpoint gate.",
            "allowed": False,
        },
        {
            "rule_id": "held_config_content_not_indexed",
            "description": "The held launcher mock config may appear by path category only, not by content.",
            "allowed": False,
        },
    ]


def _hard_gate_matrix() -> list[dict[str, Any]]:
    blocked = [
        "push",
        "fetch_pull_merge",
        "tag_release_pr_mutation",
        "runtime_start",
        "endpoint_access",
        "launcher_execution",
        "held_config_content_read",
        "secret_read",
        "real_business_material_read",
    ]
    return [{"action": action, "status": "blocked_until_manual_gate"} for action in blocked]


def _checks(
    *,
    p0: dict[str, Any],
    phase1b: dict[str, Any],
    readiness_layers: list[dict[str, Any]],
    delivery_entries: list[dict[str, Any]],
    artifact_rules: list[dict[str, Any]],
    hard_gates: list[dict[str, Any]],
) -> dict[str, bool]:
    layer_ids = {str(item.get("layer_id")) for item in readiness_layers}
    entry_ids = {str(item.get("entry_id")) for item in delivery_entries}
    rule_ids = {str(item.get("rule_id")) for item in artifact_rules}
    blocked_actions = {str(item.get("action")) for item in hard_gates if item.get("status") == "blocked_until_manual_gate"}
    phase1b_output_index = phase1b.get("output_index") or {}
    required_layers = {
        "p0_static_readiness",
        "phase1b_static_demo_workflow",
        "phase1c_local_delivery_index",
        "phase1d_docs_runbook_closure",
        "phase1e_static_test_matrix",
        "runtime_endpoint_launcher_gates",
    }
    required_entries = {
        "phase1a_local_baseline_index",
        "p0_static_readiness_cli",
        "phase1b_demo_workflow_cli",
        "phase1b_demo_workflow_doc",
        "phase1c_delivery_index_cli",
        "phase1c_delivery_index_doc",
    }
    required_blocked_actions = {
        "push",
        "fetch_pull_merge",
        "runtime_start",
        "endpoint_access",
        "launcher_execution",
        "held_config_content_read",
        "secret_read",
        "real_business_material_read",
    }
    return {
        "p0_readiness_static_pass": p0.get("status") == "PASS_P0_READINESS_STATIC",
        "phase1b_static_demo_workflow_pass": phase1b.get("status") == PHASE1B_PASS_STATUS,
        "phase1b_did_not_materialize_outputs": phase1b_output_index.get("materialized_outputs") == []
        and phase1b_output_index.get("output_generation_performed") is False,
        "readiness_layers_complete": required_layers.issubset(layer_ids),
        "delivery_entries_complete": required_entries.issubset(entry_ids),
        "artifact_rules_cover_static_and_future_outputs": {
            "static_evidence_only_before_runtime_gate",
            "no_business_output_materialization",
            "future_outputs_require_runtime_endpoint_gate",
            "held_config_content_not_indexed",
        }.issubset(rule_ids),
        "hard_gates_retained": required_blocked_actions.issubset(blocked_actions),
    }
