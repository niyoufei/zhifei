from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


GitRunner = Callable[[Path, Sequence[str]], dict[str, Any]]

DEMO_PROJECT_PATH = Path("projects/_demo_p0/project.json")

REQUIRED_ENTRIES = {
    "backend_entry": Path("backend/app/main.py"),
    "streamlit_workbench": Path("app.py"),
    "tactical_dashboard": Path("tactical_dashboard.py"),
    "launcher_v1_readme": Path("local_launcher/v1/README.md"),
    "launcher_v1_state": Path("local_launcher/v1/launcher-state.json"),
    "web_ui_script": Path("scripts/run_web_ui.sh"),
    "api_smoke_script": Path("scripts/smoke_api.py"),
    "pytest_config": Path("pytest.ini"),
    "requirements": Path("requirements.txt"),
}

REAL_DATA_DIRS = {
    "uploads": Path("data/uploads"),
    "projects": Path("projects"),
    "backend_data": Path("backend/data"),
    "build_outputs": Path("build"),
    "knowledge_graph": Path("知识图谱"),
}

LOG_DIAGNOSTIC_PATHS = {
    "runtime_logs": Path("logs"),
    "clawdbot_audit": Path("build/clawdbot"),
    "backend_audit": Path("backend/data/audit"),
}

SENSITIVE_NAME_MARKERS = (
    ".env",
    "secret",
    "token",
    "password",
    ".pem",
    "id_rsa",
    "private_key",
    "mock-config",
    "auth.py",
    "auth_store.py",
)


def build_p0_readiness_snapshot(
    root: str | Path | None = None,
    *,
    git_runner: GitRunner | None = None,
) -> dict[str, Any]:
    """Build a local-only P0 readiness snapshot without starting services."""

    repo_root = Path(root or ".").resolve()
    git = _git_snapshot(repo_root, git_runner=git_runner)
    entries = _required_entries(repo_root)
    demo = _demo_project_snapshot(repo_root)
    logs = _log_diagnostics(repo_root)
    sensitive = _sensitive_path_snapshot(repo_root)
    real_data = _real_data_snapshot(repo_root)
    commands = _command_catalog()

    failures: list[str] = []
    if not entries["all_present"]:
        failures.append("required_entries_missing")
    if not demo["valid"]:
        failures.append("sanitized_demo_project_missing_or_invalid")
    if git["index_lock_present"]:
        failures.append("git_index_lock_present")
    release_failures = list(failures)
    runtime_failures = list(failures)
    if git["worktree_clean"] is False:
        release_failures.append("worktree_not_clean")

    failures = release_failures
    status = "PASS_P0_READINESS_STATIC" if not release_failures else "NO-GO_P0_READINESS_STATIC"

    return {
        "status": status,
        "failures": failures,
        "runtime_ready": not runtime_failures,
        "release_ready": not release_failures,
        "runtime_failures": runtime_failures,
        "release_failures": release_failures,
        "workspace_root": str(repo_root),
        "scope": {
            "phase": "P0",
            "mode": "local_static_readiness",
            "starts_runtime": False,
            "visits_endpoint": False,
            "reads_real_business_content": False,
            "reads_secrets": False,
            "fetch_pull_merge_push": False,
        },
        "git": git,
        "required_entries": entries,
        "demo_project": demo,
        "log_diagnostics": logs,
        "real_data_dirs": real_data,
        "sensitive_files_handling": sensitive,
        "commands": commands,
        "forbidden_actions_performed": [],
        "next_gate": (
            "P0 controlled runtime/endpoint smoke gate"
            if status == "PASS_P0_READINESS_STATIC"
            else "repair static readiness failures before runtime gate"
        ),
    }


def format_p0_readiness_report(snapshot: dict[str, Any]) -> str:
    lines = [
        "OPENCLAW_ZHIFEI_DOC_P0_READINESS_STATIC_REPORT",
        f"status: {snapshot.get('status')}",
        f"workspace_root: {snapshot.get('workspace_root')}",
        f"git_branch: {(snapshot.get('git') or {}).get('branch')}",
        f"HEAD: {(snapshot.get('git') or {}).get('head')}",
        f"worktree_clean: {(snapshot.get('git') or {}).get('worktree_clean')}",
        f"index_lock_present: {(snapshot.get('git') or {}).get('index_lock_present')}",
        f"required_entries_all_present: {(snapshot.get('required_entries') or {}).get('all_present')}",
        f"demo_project_valid: {(snapshot.get('demo_project') or {}).get('valid')}",
        f"forbidden_actions_performed: {snapshot.get('forbidden_actions_performed')}",
        f"next_gate: {snapshot.get('next_gate')}",
    ]
    failures = snapshot.get("failures") or []
    if failures:
        lines.append("failures:")
        lines.extend(f"- {item}" for item in failures)
    return "\n".join(lines)


def _git_snapshot(root: Path, *, git_runner: GitRunner | None = None) -> dict[str, Any]:
    index_lock = root / ".git" / "index.lock"
    branch = _git_value(root, ("branch", "--show-current"), git_runner)
    head = _git_value(root, ("rev-parse", "HEAD"), git_runner)
    toplevel = _git_value(root, ("rev-parse", "--show-toplevel"), git_runner)
    upstream = _git_value(root, ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"), git_runner)
    upstream_head = _git_value(root, ("rev-parse", "@{u}"), git_runner)
    porcelain = _git_value(root, ("status", "--porcelain=v1", "--untracked-files=all"), git_runner)

    sealed_head = str(os.environ.get("ZF_BUILD_SHA") or "").strip()
    sealed_branch = str(os.environ.get("ZF_BUILD_BRANCH") or "").strip()
    sealed_dirty_raw = str(os.environ.get("ZF_BUILD_DIRTY") or "").strip()
    if head is None and sealed_head:
        head = sealed_head
    if branch is None and sealed_branch:
        branch = sealed_branch

    worktree_clean = None
    if porcelain is not None:
        worktree_clean = porcelain.strip() == ""
    elif sealed_dirty_raw in {"0", "1"}:
        worktree_clean = sealed_dirty_raw == "0"

    return {
        "toplevel": toplevel,
        "branch": branch,
        "head": head,
        "upstream": upstream,
        "upstream_head_observed_local_ref_only": upstream_head,
        "worktree_clean": worktree_clean,
        "status_porcelain_nonempty": None if porcelain is None else bool(porcelain.strip()),
        "index_lock_present": index_lock.exists(),
        "network_refreshed": False,
        "provenance_source": (
            "sealed_release"
            if porcelain is None and sealed_dirty_raw in {"0", "1"}
            else "git_worktree"
        ),
    }


def _git_value(root: Path, args: Sequence[str], git_runner: GitRunner | None) -> str | None:
    result = _run_git(root, args, git_runner)
    if result["returncode"] != 0:
        return None
    value = str(result["stdout"]).strip()
    return value or None


def _run_git(root: Path, args: Sequence[str], git_runner: GitRunner | None) -> dict[str, Any]:
    if git_runner is not None:
        return git_runner(root, args)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(root),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except Exception as exc:
        return {"returncode": 1, "stdout": "", "stderr": str(exc)}


def _required_entries(root: Path) -> dict[str, Any]:
    items = {
        name: {
            "path": str(path),
            "exists": (root / path).exists(),
        }
        for name, path in REQUIRED_ENTRIES.items()
    }
    missing = [name for name, item in items.items() if not item["exists"]]
    return {"all_present": not missing, "missing": missing, "items": items}


def _demo_project_snapshot(root: Path) -> dict[str, Any]:
    path = root / DEMO_PROJECT_PATH
    if not path.exists():
        return {"path": str(DEMO_PROJECT_PATH), "exists": False, "valid": False, "reason": "missing"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"path": str(DEMO_PROJECT_PATH), "exists": True, "valid": False, "reason": str(exc)}

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    requirements = data.get("requirements") if isinstance(data.get("requirements"), list) else []
    outline = ((data.get("plan") or {}).get("outline") if isinstance(data.get("plan"), dict) else None) or []

    checks = {
        "sanitized_demo": metadata.get("sanitized_demo") is True,
        "no_external_network": metadata.get("external_network_required") is False,
        "no_real_business_material": metadata.get("real_business_material") is False,
        "has_project_id": bool(data.get("project_id")),
        "has_requirements": bool(requirements),
        "has_outline": bool(outline),
    }
    return {
        "path": str(DEMO_PROJECT_PATH),
        "exists": True,
        "valid": all(checks.values()),
        "checks": checks,
        "project_id": data.get("project_id"),
    }


def _log_diagnostics(root: Path) -> dict[str, Any]:
    items = {}
    for name, rel_path in LOG_DIAGNOSTIC_PATHS.items():
        path = root / rel_path
        items[name] = {
            "path": str(rel_path),
            "exists": path.exists(),
            "is_dir": path.is_dir(),
            "content_read": False,
        }
    return {
        "items": items,
        "log_content_read_performed": False,
        "runtime_started": False,
        "endpoint_visited": False,
    }


def _real_data_snapshot(root: Path) -> dict[str, Any]:
    items = {}
    for name, rel_path in REAL_DATA_DIRS.items():
        path = root / rel_path
        items[name] = {
            "path": str(rel_path),
            "exists": path.exists(),
            "is_dir": path.is_dir(),
            "content_read": False,
            "path_count": _path_count(path) if path.exists() else 0,
        }
    return {"items": items, "content_read_performed": False}


def _sensitive_path_snapshot(root: Path) -> dict[str, Any]:
    matches = []
    for path in _iter_repo_paths(root):
        marker = _matched_sensitive_marker(path)
        if marker is None:
            continue
        matches.append(
            {
                "path": str(path.relative_to(root)),
                "category": _sensitive_category(marker),
                "content_read": False,
            }
        )
        if len(matches) >= 200:
            break
    return {
        "paths_detected": matches,
        "content_read_performed": False,
        "handling": "path-category-only",
    }


def _iter_repo_paths(root: Path) -> Iterable[Path]:
    skipped = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skipped]
        current_path = Path(current)
        for name in dirs:
            yield current_path / name
        for name in files:
            yield current_path / name


def _matched_sensitive_marker(path: Path) -> str | None:
    rel = path.as_posix().lower()
    name = path.name.lower()
    for marker in SENSITIVE_NAME_MARKERS:
        marker_l = marker.lower()
        if marker_l in {name, rel} or marker_l in rel:
            return marker
    return None


def _sensitive_category(marker: str) -> str:
    lowered = marker.lower()
    if lowered in {"auth.py", "auth_store.py"}:
        return "auth_source"
    if "mock-config" in lowered:
        return "mock_config_hold"
    if lowered in {".env", "secret", "token", "password", ".pem", "id_rsa", "private_key"}:
        return "secret_or_credential_name"
    return "sensitive_name"


def _path_count(path: Path) -> int:
    if not path.is_dir():
        return 1
    count = 0
    for _current, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "__pycache__"}]
        count += len(dirs) + len(files)
    return count


def _command_catalog() -> dict[str, Any]:
    return {
        "static_readiness": "python3 scripts/p0_readiness.py --json",
        "targeted_unit_tests": "PYTHONPATH=$PWD python3 -m unittest backend.tests.test_p0_readiness",
        "full_unit_tests": "PYTHONPATH=$PWD pytest",
        "runtime_smoke_later_gate": {
            "requires_separate_gate": True,
            "start_command": "python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010",
            "smoke_command": "python3 scripts/smoke_api.py http://127.0.0.1:8010",
        },
    }
