from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SUITE_PATH = ROOT_DIR / "backend" / "data" / "autoplan" / "release_regression_suite.json"
DEFAULT_BASE_URL = "http://127.0.0.1:8010"
DEFAULT_ACTIONS_KEY_ENV = "ZF_ACTIONS_KEY"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def load_release_regression_suite(*, suite_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(suite_path or DEFAULT_SUITE_PATH).resolve()
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("release regression suite must be a JSON object")
    doc["_suite_path"] = str(path)
    return doc


def validate_release_regression_suite(
    doc: dict[str, Any],
    *,
    root_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(root_dir or ROOT_DIR).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    cases_out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    runner = _clean_text(doc.get("runner"))
    runner_path = (root / runner).resolve() if runner else None
    if not runner:
        errors.append("runner missing")
    elif not runner_path.exists():
        errors.append(f"runner not found: {runner}")

    raw_cases = doc.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        errors.append("cases missing or empty")
        raw_cases = []

    for idx, raw_case in enumerate(raw_cases):
        prefix = f"cases[{idx}]"
        if not isinstance(raw_case, dict):
            errors.append(f"{prefix} must be object")
            continue
        cid = _clean_text(raw_case.get("id"))
        if not cid:
            errors.append(f"{prefix}.id missing")
            continue
        if cid in seen_ids:
            errors.append(f"duplicate case id: {cid}")
            continue
        seen_ids.add(cid)

        tender_files = raw_case.get("tender_files")
        ingest_files = raw_case.get("ingest_files") or []
        if not isinstance(tender_files, list) or not tender_files:
            errors.append(f"{cid}: tender_files missing or empty")
            continue
        if not isinstance(ingest_files, list):
            errors.append(f"{cid}: ingest_files must be list")
            continue

        boq_file = _clean_text(raw_case.get("boq_file"))
        if not boq_file:
            errors.append(f"{cid}: boq_file missing")
            continue

        normalized = {
            "id": cid,
            "priority": _clean_text(raw_case.get("priority")) or "P1",
            "release_gate": bool(raw_case.get("release_gate")),
            "topic": _clean_text(raw_case.get("topic")) or cid,
            "project_id": _clean_text(raw_case.get("project_id")) or f"release_reg_{cid}",
            "variant_id": _clean_int(raw_case.get("variant_id"), 0),
            "logic_template_id": _clean_text(raw_case.get("logic_template_id")).upper(),
            "description": _clean_text(raw_case.get("description")),
            "notes": _clean_text(raw_case.get("notes")),
            "suggested_timeout_sec": int(raw_case.get("suggested_timeout_sec") or 180),
            "quality_strict": bool(raw_case.get("quality_strict", True)),
            "auto_remediate": bool(raw_case.get("auto_remediate", False)),
            "strict_tender_outline": bool(raw_case.get("strict_tender_outline", False)),
            "risk_tags": [str(item).strip() for item in (raw_case.get("risk_tags") or []) if str(item).strip()],
            "tender_files": [str(item).strip() for item in tender_files if str(item).strip()],
            "boq_file": boq_file,
            "ingest_files": [str(item).strip() for item in ingest_files if str(item).strip()],
            "outline": [str(item).strip() for item in (raw_case.get("outline") or []) if str(item).strip()],
        }

        missing_paths: list[str] = []
        for rel in normalized["tender_files"] + [normalized["boq_file"]] + normalized["ingest_files"]:
            if rel.startswith("/"):
                errors.append(f"{cid}: paths must be repository-relative, got absolute path {rel}")
                continue
            if not (root / rel).exists():
                missing_paths.append(rel)
        if missing_paths:
            errors.append(f"{cid}: missing files -> {', '.join(missing_paths)}")
        if normalized["variant_id"] < 0:
            errors.append(f"{cid}: variant_id must be >= 0")
        if normalized["logic_template_id"] and normalized["logic_template_id"] not in {"A", "B", "C", "D", "E"}:
            errors.append(f"{cid}: logic_template_id must be one of A/B/C/D/E")
        cases_out.append(normalized)

    declared_release_gate = doc.get("release_gate_cases") or []
    if not isinstance(declared_release_gate, list):
        errors.append("release_gate_cases must be list")
        declared_release_gate = []
    declared_release_gate_ids = [str(item).strip() for item in declared_release_gate if str(item).strip()]
    case_map = {case["id"]: case for case in cases_out}
    for cid in declared_release_gate_ids:
        if cid not in case_map:
            errors.append(f"release_gate_cases references unknown case: {cid}")
    derived_release_gate_ids = [case["id"] for case in cases_out if case["release_gate"]]
    if sorted(set(declared_release_gate_ids)) != sorted(set(derived_release_gate_ids)):
        warnings.append("release_gate_cases and cases[].release_gate are inconsistent; using union during selection.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "runner": runner,
        "runner_path": str(runner_path) if runner_path is not None else None,
        "suite_version": _clean_text(doc.get("suite_version")) or None,
        "cases": cases_out,
        "case_ids": [case["id"] for case in cases_out],
        "release_gate_cases": sorted(set(declared_release_gate_ids) | set(derived_release_gate_ids)),
    }


def select_release_regression_cases(
    validated: dict[str, Any],
    *,
    case_ids: list[str] | None = None,
    release_only: bool = False,
) -> list[dict[str, Any]]:
    cases = list(validated.get("cases") or [])
    if case_ids:
        wanted = {str(item).strip() for item in case_ids if str(item).strip()}
        out = [case for case in cases if case["id"] in wanted]
        missing = sorted(wanted - {case["id"] for case in out})
        if missing:
            raise ValueError(f"unknown regression cases: {', '.join(missing)}")
        return out
    if release_only:
        wanted = set(validated.get("release_gate_cases") or [])
        return [case for case in cases if case["id"] in wanted]
    return cases


def build_release_regression_command(
    case: dict[str, Any],
    *,
    root_dir: str | Path | None = None,
    base_url: str = DEFAULT_BASE_URL,
    dry_run: bool = True,
    download: bool = True,
    actions_key_env: str = DEFAULT_ACTIONS_KEY_ENV,
) -> list[str]:
    root = Path(root_dir or ROOT_DIR).resolve()
    cmd = [
        sys.executable,
        str((root / "scripts" / "run_actions_pipeline.py").resolve()),
        "--base-url",
        _clean_text(base_url) or DEFAULT_BASE_URL,
        "--topic",
        str(case["topic"]),
        "--project-id",
        str(case["project_id"]),
        "--session-id",
        str(case["project_id"]),
        "--timeout-sec",
        str(int(case.get("suggested_timeout_sec") or 180)),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if not download:
        cmd.append("--no-download")
    if case.get("quality_strict", True):
        cmd.append("--quality-strict")
    else:
        cmd.append("--no-quality-strict")
    if case.get("auto_remediate", False):
        cmd.append("--auto-remediate")
    else:
        cmd.append("--no-auto-remediate")
    if case.get("strict_tender_outline", False):
        cmd.append("--strict-tender-outline")
    if int(case.get("variant_id") or 0) > 0:
        cmd.extend(["--variant-id", str(int(case["variant_id"]))])
    if _clean_text(case.get("logic_template_id")):
        cmd.extend(["--logic-template-id", _clean_text(case.get("logic_template_id")).upper()])
    for outline in case.get("outline") or []:
        cmd.extend(["--outline", str(outline)])
    for tender in case.get("tender_files") or []:
        cmd.extend(["--tender", str((root / tender).resolve())])
    cmd.extend(["--boq", str((root / str(case.get("boq_file"))).resolve())])
    for extra in case.get("ingest_files") or []:
        cmd.extend(["--ingest", str((root / extra).resolve())])
    return cmd


def shell_render_command(cmd: list[str], *, actions_key_env: str = DEFAULT_ACTIONS_KEY_ENV) -> str:
    return f"{actions_key_env}=... " + " ".join(shlex.quote(part) for part in cmd)


def run_release_regression_case(cmd: list[str], *, root_dir: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    root = Path(root_dir or ROOT_DIR).resolve()
    return subprocess.run(cmd, cwd=str(root), text=True, capture_output=True)
