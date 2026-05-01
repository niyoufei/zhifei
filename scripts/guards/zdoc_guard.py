#!/usr/bin/env python3
"""Guarded PR workflow checks for ZDoc.

This script intentionally performs checks only. It does not merge pull
requests, create tags, start services, connect to Ollama, or run generation.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_COUNT_PATHS = [
    "backend/data/autoplan/jobs",
    "build",
    "output",
]

BLOCKED_COMMAND_SNIPPETS = [
    "git clean",
    "git reset --hard",
    "gh pr merge",
    "git tag ",
    "git push",
    "ollama",
    "uvicorn",
    "streamlit",
    "run_autoplan",
    "generate_async",
    "actions/generate",
    "export_docx",
]


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str


def repo_root() -> Path:
    result = run(["git", "rev-parse", "--show-toplevel"], check=True)
    return Path(result.stdout.strip())


def run(args: Sequence[str], *, check: bool = False, cwd: Path | None = None) -> CommandResult:
    proc = subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    result = CommandResult(
        command=" ".join(shlex.quote(str(part)) for part in args),
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
    if check and result.returncode != 0:
        raise SystemExit(format_failure(f"command failed: {result.command}", result))
    return result


def format_failure(message: str, result: CommandResult | None = None) -> str:
    lines = [f"[FAIL] {message}"]
    if result is not None:
        lines.append(f"command: {result.command}")
        lines.append(f"returncode: {result.returncode}")
        if result.stdout.strip():
            lines.append("stdout:")
            lines.append(result.stdout.rstrip())
        if result.stderr.strip():
            lines.append("stderr:")
            lines.append(result.stderr.rstrip())
    return "\n".join(lines)


def print_command_result(result: CommandResult) -> None:
    print(f"$ {result.command}")
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    print(f"[exit {result.returncode}]")


def load_task(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    task_path = Path(path)
    try:
        data = json.loads(task_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"[FAIL] task spec not found: {task_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[FAIL] task spec is not valid JSON: {task_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("[FAIL] task spec root must be a JSON object")
    return data


def normalize_patterns(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        raise SystemExit("[FAIL] task spec path fields must be arrays")
    return [str(item).strip().lstrip("./") for item in values if str(item).strip()]


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return 1
    return sum(1 for child in path.rglob("*") if child.is_file())


def count_snapshot(root: Path, task: dict[str, Any]) -> dict[str, int]:
    paths = normalize_patterns(task.get("count_paths")) or DEFAULT_COUNT_PATHS
    return {rel: count_files(root / rel) for rel in paths}


def print_count_snapshot(snapshot: dict[str, int]) -> None:
    print("artifact_counts:")
    for rel, count in snapshot.items():
        print(f"  {rel}: {count}")


def status_short(root: Path) -> str:
    return run(["git", "status", "--short"], check=True, cwd=root).stdout.rstrip()


def current_branch(root: Path) -> str:
    return run(["git", "branch", "--show-current"], check=True, cwd=root).stdout.strip()


def current_head(root: Path) -> str:
    return run(["git", "log", "-1", "--oneline"], check=True, cwd=root).stdout.strip()


def changed_files(root: Path) -> list[str]:
    files: set[str] = set()
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    for command in commands:
        result = run(command, check=True, cwd=root)
        for line in result.stdout.splitlines():
            clean = line.strip().lstrip("./")
            if clean:
                files.add(clean)
    return sorted(files)


def matches_pattern(path: str, pattern: str) -> bool:
    clean_path = path.lstrip("./")
    clean_pattern = pattern.lstrip("./")
    if clean_pattern.endswith("/"):
        return clean_path.startswith(clean_pattern)
    if fnmatch.fnmatch(clean_path, clean_pattern):
        return True
    return clean_path == clean_pattern


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(matches_pattern(path, pattern) for pattern in patterns)


def scope_report(root: Path, task: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    files = changed_files(root)
    allowed = normalize_patterns(task.get("allowed_files"))
    forbidden = normalize_patterns(task.get("forbidden_files"))
    outside_allowed: list[str] = []
    forbidden_hits: list[str] = []

    for path in files:
        if allowed and not matches_any(path, allowed):
            outside_allowed.append(path)
        if forbidden and matches_any(path, forbidden):
            forbidden_hits.append(path)
    return files, outside_allowed, forbidden_hits


def command_from_spec(value: Any) -> list[str]:
    if isinstance(value, list):
        if not value:
            raise SystemExit("[FAIL] test command array cannot be empty")
        return [str(part) for part in value]
    if isinstance(value, str):
        if not value.strip():
            raise SystemExit("[FAIL] test command cannot be empty")
        return shlex.split(value)
    raise SystemExit("[FAIL] test_commands entries must be strings or arrays")


def ensure_safe_command(command: str) -> None:
    lowered = command.lower()
    for snippet in BLOCKED_COMMAND_SNIPPETS:
        if snippet in lowered:
            raise SystemExit(f"[FAIL] blocked high-risk command in task spec: {command}")


def run_test_commands(root: Path, task: dict[str, Any]) -> list[CommandResult]:
    commands = task.get("test_commands") or []
    if not isinstance(commands, list):
        raise SystemExit("[FAIL] test_commands must be an array")
    results: list[CommandResult] = []
    for item in commands:
        argv = command_from_spec(item)
        command_text = " ".join(shlex.quote(part) for part in argv)
        ensure_safe_command(command_text)
        result = run(argv, cwd=root)
        print_command_result(result)
        results.append(result)
        if result.returncode != 0:
            raise SystemExit(format_failure("test command failed", result))
    return results


def cmd_preflight(args: argparse.Namespace) -> int:
    root = repo_root()
    task = load_task(args.task)
    print(f"repo_root: {root}")
    print(f"branch: {current_branch(root)}")
    print(f"head: {current_head(root)}")
    print("git_status_short:")
    status = status_short(root)
    print(status if status else "<clean>")
    print_count_snapshot(count_snapshot(root, task))
    return 0


def cmd_scope(args: argparse.Namespace) -> int:
    root = repo_root()
    task = load_task(args.task)
    files, outside_allowed, forbidden_hits = scope_report(root, task)

    print("changed_files:")
    if files:
        for path in files:
            print(f"  {path}")
    else:
        print("  <none>")

    if outside_allowed:
        print("outside_allowed:")
        for path in outside_allowed:
            print(f"  {path}")
    if forbidden_hits:
        print("forbidden_hits:")
        for path in forbidden_hits:
            print(f"  {path}")

    if outside_allowed or forbidden_hits:
        print("[FAIL] scope check failed")
        return 2
    print("[PASS] scope check passed")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = repo_root()
    task = load_task(args.task)
    before = count_snapshot(root, task)
    print("counts_before:")
    print_count_snapshot(before)

    diff_check = run(["git", "diff", "--check"], cwd=root)
    print_command_result(diff_check)
    if diff_check.returncode != 0:
        raise SystemExit(format_failure("git diff --check failed", diff_check))

    run_test_commands(root, task)

    after = count_snapshot(root, task)
    print("counts_after:")
    print_count_snapshot(after)
    if before != after:
        print("[FAIL] artifact counts changed")
        for key in sorted(set(before) | set(after)):
            print(f"  {key}: {before.get(key, 0)} -> {after.get(key, 0)}")
        return 2
    print("[PASS] verify checks passed")
    return 0


def cmd_pr_summary(args: argparse.Namespace) -> int:
    root = repo_root()
    task = load_task(args.task)
    files, outside_allowed, forbidden_hits = scope_report(root, task)
    print("# ZDoc Guarded PR Summary")
    print()
    print(f"- PR title: {task.get('pr_title') or '<unset>'}")
    print(f"- Branch: {current_branch(root)}")
    print(f"- HEAD: {current_head(root)}")
    print(f"- Status clean: {'yes' if not status_short(root) else 'no'}")
    print(f"- Changed files: {', '.join(files) if files else '<none>'}")
    print(f"- Scope check: {'pass' if not outside_allowed and not forbidden_hits else 'fail'}")
    print(f"- Test commands: {task.get('test_commands') or []}")
    print("- Artifact counts:")
    for rel, count in count_snapshot(root, task).items():
        print(f"  - {rel}: {count}")
    print("- Guard boundaries: no merge, no tag creation, no service start, no Ollama connection, no real generation.")
    return 0


def cmd_tag_check(args: argparse.Namespace) -> int:
    root = repo_root()
    task = load_task(args.task)
    tag = args.tag or str(task.get("tag_name") or "").strip()
    if not tag:
        print("[FAIL] tag name is required via --tag or task tag_name")
        return 2
    status = status_short(root)
    if status:
        print("[FAIL] git status is not clean; refusing tag precheck pass")
        print(status)
        return 2
    local = run(["git", "tag", "--list", tag], check=True, cwd=root).stdout.strip()
    remote = run(["git", "ls-remote", "--tags", "origin", tag], check=True, cwd=root).stdout.strip()
    print(f"tag: {tag}")
    print(f"local_exists: {'yes' if local else 'no'}")
    print(f"remote_exists: {'yes' if remote else 'no'}")
    if local or remote:
        print("[FAIL] tag already exists")
        return 2
    print("[PASS] tag precheck passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guarded ZDoc PR workflow checks.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name, handler in [
        ("preflight", cmd_preflight),
        ("scope", cmd_scope),
        ("verify", cmd_verify),
        ("pr-summary", cmd_pr_summary),
        ("tag-check", cmd_tag_check),
    ]:
        command = sub.add_parser(name)
        command.add_argument("--task", help="Path to JSON task spec.")
        command.set_defaults(handler=handler)
        if name == "tag-check":
            command.add_argument("--tag", help="Tag name to check.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
