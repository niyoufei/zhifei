#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.zhifei_autoplan.release_regression_suite import (
    DEFAULT_ACTIONS_KEY_ENV,
    build_release_regression_command,
    load_release_regression_suite,
    run_release_regression_case,
    select_release_regression_cases,
    shell_render_command,
    validate_release_regression_suite,
)


def _validated(args: argparse.Namespace) -> dict:
    doc = load_release_regression_suite(suite_path=args.suite)
    validated = validate_release_regression_suite(doc)
    if not validated["ok"]:
        print(json.dumps(validated, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    return validated


def cmd_list(args: argparse.Namespace) -> int:
    validated = _validated(args)
    cases = select_release_regression_cases(validated, release_only=bool(args.release_only))
    out = {
        "ok": True,
        "suite_version": validated.get("suite_version"),
        "release_gate_cases": validated.get("release_gate_cases"),
        "cases": cases,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    doc = load_release_regression_suite(suite_path=args.suite)
    validated = validate_release_regression_suite(doc)
    print(json.dumps(validated, ensure_ascii=False, indent=2))
    return 0 if validated["ok"] else 1


def cmd_command(args: argparse.Namespace) -> int:
    validated = _validated(args)
    cases = select_release_regression_cases(
        validated,
        case_ids=args.case,
        release_only=bool(args.release_only),
    )
    payload = []
    for case in cases:
        cmd = build_release_regression_command(
            case,
            base_url=args.base_url,
            dry_run=not bool(args.live),
            download=not bool(args.no_download),
            actions_key_env=args.actions_key_env,
        )
        payload.append(
            {
                "id": case["id"],
                "priority": case["priority"],
                "release_gate": case["release_gate"],
                "command": shell_render_command(cmd, actions_key_env=args.actions_key_env),
            }
        )
    print(json.dumps({"ok": True, "cases": payload}, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    validated = _validated(args)
    cases = select_release_regression_cases(
        validated,
        case_ids=args.case,
        release_only=bool(args.release_only),
    )
    reports = []
    exit_code = 0
    for case in cases:
        cmd = build_release_regression_command(
            case,
            base_url=args.base_url,
            dry_run=not bool(args.live),
            download=not bool(args.no_download),
            actions_key_env=args.actions_key_env,
        )
        proc = run_release_regression_case(cmd)
        reports.append(
            {
                "id": case["id"],
                "priority": case["priority"],
                "release_gate": case["release_gate"],
                "returncode": proc.returncode,
                "stdout_tail": (proc.stdout or "").splitlines()[-40:],
                "stderr_tail": (proc.stderr or "").splitlines()[-40:],
            }
        )
        if proc.returncode != 0:
            exit_code = proc.returncode
            if not args.continue_on_error:
                break
    print(json.dumps({"ok": exit_code == 0, "reports": reports}, ensure_ascii=False, indent=2))
    return int(exit_code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="release_regression_suite.py")
    parser.add_argument("--suite", default="", help="override suite json path")
    parser.add_argument("--base-url", default="http://127.0.0.1:8010", help="backend base url")
    parser.add_argument("--actions-key-env", default=DEFAULT_ACTIONS_KEY_ENV, help="env var name shown in rendered commands")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="list regression cases")
    p_list.add_argument("--release-only", action="store_true", help="only show release gate cases")
    p_list.set_defaults(func=cmd_list)

    p_check = sub.add_parser("check", help="validate suite file and referenced paths")
    p_check.set_defaults(func=cmd_check)

    p_command = sub.add_parser("command", help="render run_actions_pipeline commands")
    p_command.add_argument("--case", action="append", default=[], help="specific case id (repeatable)")
    p_command.add_argument("--release-only", action="store_true", help="only render release gate cases")
    p_command.add_argument("--live", action="store_true", help="render live generation commands instead of dry-run")
    p_command.add_argument("--no-download", action="store_true", help="render commands with --no-download")
    p_command.set_defaults(func=cmd_command)

    p_run = sub.add_parser("run", help="execute selected regression cases")
    p_run.add_argument("--case", action="append", default=[], help="specific case id (repeatable)")
    p_run.add_argument("--release-only", action="store_true", help="run only release gate cases")
    p_run.add_argument("--live", action="store_true", help="run live generation instead of dry-run")
    p_run.add_argument("--no-download", action="store_true", help="run with --no-download")
    p_run.add_argument("--continue-on-error", action="store_true", help="continue running later cases after a failure")
    p_run.set_defaults(func=cmd_run)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
