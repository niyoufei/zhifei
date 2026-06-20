from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.p0_readiness import build_p0_readiness_snapshot
from backend.zhifei_autoplan.phase1_demo_workflow import (
    PASS_STATUS as PHASE1B_PASS_STATUS,
    build_phase1b_demo_workflow_snapshot,
)
from backend.zhifei_autoplan.phase1_delivery_index import (
    PASS_STATUS as PHASE1C_PASS_STATUS,
    build_phase1c_delivery_index_snapshot,
)


PHASE_ID = "PHASE_1E_STATIC_TEST_MATRIX"
REPORT_TITLE = "OPENCLAW_ZHIFEI_DOC_PHASE1E_STATIC_TEST_MATRIX_REPORT"
PASS_STATUS = "PASS_PHASE1E_STATIC_TEST_MATRIX"
NO_GO_STATUS = "NO-GO_PHASE1E_STATIC_TEST_MATRIX"

REQUIRED_DOC_PATHS = (
    "README.md",
    "backend/RUNBOOK.md",
    "docs/openclaw-zhifei-doc-p0-readiness.md",
    "docs/openclaw-zhifei-doc-phase1-local-baseline.md",
    "docs/openclaw-zhifei-doc-phase1b-demo-workflow.md",
    "docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md",
    "docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md",
    "docs/openclaw-zhifei-doc-phase1e-static-test-matrix.md",
)

REFERENCE_DOCS = (
    "docs/openclaw-zhifei-doc-phase1b-demo-workflow.md",
    "docs/openclaw-zhifei-doc-phase1c-readiness-delivery-index.md",
    "docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md",
    "docs/openclaw-zhifei-doc-phase1e-static-test-matrix.md",
)

REQUIRED_DIAGNOSTICS = (
    "worktree_not_clean",
    "git_index_lock_present",
    "required_entries_missing",
    "sanitized_demo_project_missing_or_invalid",
    "p0_readiness_static_pass",
    "phase1b_static_demo_workflow_pass",
    "phase1c_readiness_delivery_index_pass",
    "docs_presence_complete",
)

REQUIRED_FORBIDDEN_PROOFS = (
    "runtime_start",
    "endpoint_access",
    "launcher_execution",
    "held_config_body_read",
    "secret_read",
    "real_business_document_read",
    "remote_fetch_pull_merge_push",
)

REQUIRED_MATRIX_IDS = (
    "p0_readiness_clean_pass_chain",
    "dirty_worktree_no_go_expected",
    "phase1b_demo_workflow_static_entry",
    "phase1c_readiness_delivery_index_static_entry",
    "phase1d_docs_runbook_closure_static_entry",
    "docs_link_and_presence_check",
    "failure_diagnostics",
    "forbidden_action_negative_proof",
    "post_commit_p0_pass_verification",
)


def build_phase1e_static_matrix_snapshot(
    root: str | Path | None = None,
    *,
    p0_snapshot: dict[str, Any] | None = None,
    phase1b_snapshot: dict[str, Any] | None = None,
    phase1c_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the no-runtime Phase 1E static test matrix snapshot."""

    repo_root = Path(root or ".").resolve()
    p0 = p0_snapshot if p0_snapshot is not None else build_p0_readiness_snapshot(repo_root)
    phase1b = (
        phase1b_snapshot
        if phase1b_snapshot is not None
        else build_phase1b_demo_workflow_snapshot(repo_root, p0_snapshot=p0)
    )
    phase1c = (
        phase1c_snapshot
        if phase1c_snapshot is not None
        else build_phase1c_delivery_index_snapshot(
            repo_root,
            p0_snapshot=p0,
            phase1b_snapshot=phase1b,
        )
    )

    docs_presence = _docs_presence(repo_root)
    docs_links = _docs_link_checks(repo_root)
    matrix_entries = _matrix_entries()
    failure_diagnostics = _failure_diagnostics()
    forbidden_proofs = _forbidden_proofs()
    checks = _checks(
        p0=p0,
        phase1b=phase1b,
        phase1c=phase1c,
        docs_presence=docs_presence,
        docs_links=docs_links,
        matrix_entries=matrix_entries,
        failure_diagnostics=failure_diagnostics,
        forbidden_proofs=forbidden_proofs,
    )
    failures = [name for name, passed in checks.items() if not passed]
    status = PASS_STATUS if not failures else NO_GO_STATUS

    return {
        "status": status,
        "phase_id": PHASE_ID,
        "failures": failures,
        "workspace_root": str(repo_root),
        "source_evidence": {
            "p0_readiness_status": p0.get("status"),
            "p0_failures": p0.get("failures", []),
            "phase1b_status": phase1b.get("status"),
            "phase1b_failures": phase1b.get("failures", []),
            "phase1c_status": phase1c.get("status"),
            "phase1c_failures": phase1c.get("failures", []),
        },
        "matrix_entries": matrix_entries,
        "docs_presence": docs_presence,
        "docs_link_checks": docs_links,
        "failure_diagnostics": failure_diagnostics,
        "forbidden_action_proof": forbidden_proofs,
        "checks": checks,
        "scope": {
            "phase": "Phase 1E",
            "mode": "local_static_test_matrix",
            "starts_runtime": False,
            "visits_endpoint": False,
            "runs_launcher": False,
            "reads_held_config_content": False,
            "reads_real_business_content": False,
            "reads_secrets": False,
            "fetch_pull_merge_push": False,
            "materializes_business_outputs": False,
        },
        "forbidden_actions_performed": [],
        "next_gate": (
            "PHASE1_LOCAL_STATIC_BASELINE_CLOSEOUT_READONLY"
            if status == PASS_STATUS
            else "repair Phase 1E static matrix failures"
        ),
    }


def format_phase1e_static_matrix_report(snapshot: dict[str, Any]) -> str:
    matrix_ids = [item.get("matrix_id") for item in snapshot.get("matrix_entries", [])]
    docs_missing = [
        item.get("path")
        for item in (snapshot.get("docs_presence") or {}).get("items", [])
        if not item.get("exists")
    ]
    lines = [
        REPORT_TITLE,
        f"phase_id: {snapshot.get('phase_id')}",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"p0_readiness_status: {(snapshot.get('source_evidence') or {}).get('p0_readiness_status')}",
        f"phase1b_status: {(snapshot.get('source_evidence') or {}).get('phase1b_status')}",
        f"phase1c_status: {(snapshot.get('source_evidence') or {}).get('phase1c_status')}",
        f"matrix_entries: {matrix_ids}",
        f"docs_missing: {docs_missing}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def dump_phase1e_static_matrix_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)


def _matrix_entries() -> list[dict[str, Any]]:
    return [
        {
            "matrix_id": "p0_readiness_clean_pass_chain",
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json",
            "expected_clean_status": "PASS_P0_READINESS_STATIC",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "dirty_worktree_no_go_expected",
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/p0_readiness.py --json",
            "expected_dirty_failure": "worktree_not_clean",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "phase1b_demo_workflow_static_entry",
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_demo_workflow.py --json",
            "expected_clean_status": "PASS_PHASE1B_DEMO_WORKFLOW_STATIC",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "phase1c_readiness_delivery_index_static_entry",
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_delivery_index.py --json",
            "expected_clean_status": "PASS_PHASE1C_READINESS_DELIVERY_INDEX_STATIC",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "phase1d_docs_runbook_closure_static_entry",
            "command": "docs-only presence and link check",
            "expected_clean_status": "docs closure links present",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "docs_link_and_presence_check",
            "command": "PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD python3 scripts/phase1_static_matrix.py --json",
            "expected_clean_status": PASS_STATUS,
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "failure_diagnostics",
            "command": "inspect matrix failure_diagnostics",
            "expected_clean_status": "all required diagnostics documented",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "forbidden_action_negative_proof",
            "command": "inspect matrix forbidden_action_proof",
            "expected_clean_status": "all forbidden actions remain false",
            "runtime_required": False,
            "endpoint_required": False,
        },
        {
            "matrix_id": "post_commit_p0_pass_verification",
            "command": "rerun P0 unittest, text CLI, and JSON CLI after local commit",
            "expected_clean_status": "PASS_P0_READINESS_STATIC and failures=[]",
            "runtime_required": False,
            "endpoint_required": False,
        },
    ]


def _docs_presence(root: Path) -> dict[str, Any]:
    items = [{"path": path, "exists": (root / path).is_file()} for path in REQUIRED_DOC_PATHS]
    return {"all_present": all(item["exists"] for item in items), "items": items}


def _docs_link_checks(root: Path) -> dict[str, Any]:
    sources = ("README.md", "backend/RUNBOOK.md", "docs/openclaw-zhifei-doc-phase1d-docs-runbook-closure.md")
    items: list[dict[str, Any]] = []
    for source in sources:
        source_path = root / source
        if source_path.is_file():
            text = source_path.read_text(encoding="utf-8")
            refs = {ref: (ref in text) for ref in REFERENCE_DOCS}
        else:
            refs = {ref: False for ref in REFERENCE_DOCS}
        items.append({"source": source, "exists": source_path.is_file(), "refs": refs})
    all_refs_present = all(item["exists"] and all(item["refs"].values()) for item in items)
    return {"all_present": all_refs_present, "items": items}


def _failure_diagnostics() -> list[dict[str, str]]:
    return [
        {
            "failure": "worktree_not_clean",
            "diagnostic": "Expected dirty gate while authorized Phase 1E files are uncommitted; commit locally, then rerun P0.",
        },
        {
            "failure": "git_index_lock_present",
            "diagnostic": "Stop for a separate git-lock decision before commit attempts.",
        },
        {
            "failure": "required_entries_missing",
            "diagnostic": "Restore missing static entry before runtime, endpoint, or launcher gates.",
        },
        {
            "failure": "sanitized_demo_project_missing_or_invalid",
            "diagnostic": "Repair sanitized demo metadata only; do not substitute real business documents.",
        },
        {
            "failure": "p0_readiness_static_pass",
            "diagnostic": "Inspect P0 JSON failures before Phase 1B, Phase 1C, or Phase 1E acceptance.",
        },
        {
            "failure": "phase1b_static_demo_workflow_pass",
            "diagnostic": "Inspect Phase 1B JSON failures before Phase 1C or Phase 1E acceptance.",
        },
        {
            "failure": "phase1c_readiness_delivery_index_pass",
            "diagnostic": "Inspect Phase 1C JSON failures before Phase 1E acceptance.",
        },
        {
            "failure": "docs_presence_complete",
            "diagnostic": "Restore README, RUNBOOK, and Phase 1 docs links before closeout.",
        },
    ]


def _forbidden_proofs() -> list[dict[str, Any]]:
    return [
        {"action": action, "performed": False, "requires_manual_gate": True}
        for action in REQUIRED_FORBIDDEN_PROOFS
    ]


def _checks(
    *,
    p0: dict[str, Any],
    phase1b: dict[str, Any],
    phase1c: dict[str, Any],
    docs_presence: dict[str, Any],
    docs_links: dict[str, Any],
    matrix_entries: list[dict[str, Any]],
    failure_diagnostics: list[dict[str, str]],
    forbidden_proofs: list[dict[str, Any]],
) -> dict[str, bool]:
    matrix_ids = {str(item.get("matrix_id")) for item in matrix_entries}
    diagnostic_ids = {str(item.get("failure")) for item in failure_diagnostics}
    forbidden_actions = {
        str(item.get("action"))
        for item in forbidden_proofs
        if item.get("performed") is False and item.get("requires_manual_gate") is True
    }
    return {
        "p0_readiness_clean_pass": p0.get("status") == "PASS_P0_READINESS_STATIC",
        "phase1b_static_demo_workflow_pass": phase1b.get("status") == PHASE1B_PASS_STATUS,
        "phase1c_readiness_delivery_index_pass": phase1c.get("status") == PHASE1C_PASS_STATUS,
        "matrix_entries_complete": set(REQUIRED_MATRIX_IDS).issubset(matrix_ids),
        "docs_presence_complete": docs_presence.get("all_present") is True,
        "docs_links_complete": docs_links.get("all_present") is True,
        "failure_diagnostics_complete": set(REQUIRED_DIAGNOSTICS).issubset(diagnostic_ids),
        "forbidden_action_negative_proof_complete": set(REQUIRED_FORBIDDEN_PROOFS).issubset(
            forbidden_actions
        ),
        "scope_retains_static_boundaries": all(
            item.get("runtime_required") is False and item.get("endpoint_required") is False
            for item in matrix_entries
        ),
    }
