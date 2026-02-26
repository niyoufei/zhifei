#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_PROJECTS_ROOT = Path("/Users/youfeini/Desktop/文档生成系统")
DEFAULT_OUT_JSON = Path("build/real_project_regression_summary.json")
DEFAULT_OUT_MD = Path("build/Real_Project_Regression_Report.md")
DEFAULT_RUNNER = Path("run_real_project.py")
DOC_EXTS = {".pdf", ".doc", ".docx", ".txt", ".md"}
BOQ_EXTS = {".csv", ".xlsx", ".xls", ".pdf"}
QA_HINTS = ("答疑", "澄清", "补遗", "答复", "疑问")
TENDER_HINTS = ("招标", "tender")
BOQ_HINTS = ("清单", "boq")
EXCLUDED_PROJECT_DIR_NAMES = {
    "projects",
    "backend",
    "build",
    "logs",
    "frontend",
    "frontend_web",
    "data",
    "modules",
    "scripts",
    "docs",
    "deploy",
    "venv",
    "api",
    "app",
}
DEFAULT_GATE_CONFIG = {
    "min_pass_rate": 1.0,
    "min_sentence_coverage": 0.95,
    "max_gaps_per_project": 0,
    "max_boq_failed_files": 1,
}


def _slugify(name: str) -> str:
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", str(name or "").strip(), flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "project"


def _is_project_like_dir(path: Path) -> bool:
    name = path.name
    lowered = name.lower()
    if name.startswith("."):
        return False
    if lowered in EXCLUDED_PROJECT_DIR_NAMES:
        return False
    if re.match(r"^\d+[_-].+", name):
        return True
    return any(token in name for token in ("项目", "测试")) or any(token in lowered for token in ("project", "test"))


def _collect_files(project_dir: Path, *, max_depth: int = 3) -> List[Path]:
    files: List[Path] = []
    for p in project_dir.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(project_dir)
        except Exception:
            continue
        if len(rel.parts) > max_depth + 1:
            continue
        files.append(p)
    return sorted(files, key=lambda p: str(p))


def detect_project_inputs(project_dir: Path) -> Dict[str, Any]:
    project_dir = project_dir.expanduser().resolve()
    if not project_dir.exists() or not project_dir.is_dir():
        return {}

    files = _collect_files(project_dir, max_depth=3)
    tender_candidates: List[Path] = []
    qa_candidates: List[Path] = []
    boq_candidates: List[Path] = []

    for p in files:
        suffix = p.suffix.lower()
        name = p.name
        lowered = name.lower()
        if suffix in DOC_EXTS:
            if any(h in lowered for h in TENDER_HINTS):
                tender_candidates.append(p)
            if any(h in name for h in QA_HINTS) or any(h in lowered for h in ("clarification", "qa")):
                qa_candidates.append(p)
        if suffix in BOQ_EXTS and (any(h in name for h in BOQ_HINTS) or "boq" in lowered):
            boq_candidates.append(p)

    boq_path: Path | None = None
    boq_dirs = [d for d in project_dir.rglob("*") if d.is_dir() and "工程量清单" in d.name]
    boq_dirs = sorted(boq_dirs, key=lambda p: str(p))
    if boq_dirs:
        boq_path = boq_dirs[0]
    elif boq_candidates:
        boq_path = sorted(
            boq_candidates,
            key=lambda p: (0 if "汇总" in p.name else 1, 0 if "清单" in p.name else 1, len(p.name)),
        )[0]

    tender_candidates = sorted(
        tender_candidates,
        key=lambda p: (0 if "招标文件" in p.name else 1, 0 if p.suffix.lower() == ".pdf" else 1, len(p.name)),
    )
    qa_candidates = sorted(
        qa_candidates,
        key=lambda p: (0 if "答疑文件" in p.name else 1, len(p.name)),
    )
    tenders = [str(p) for p in tender_candidates]
    for qa in qa_candidates:
        qa_str = str(qa)
        if qa_str not in tenders:
            tenders.append(qa_str)

    if not tenders or boq_path is None:
        return {}
    return {
        "project_dir": str(project_dir),
        "project_name": project_dir.name,
        "tender_paths": tenders,
        "boq_path": str(boq_path),
    }


def discover_projects(root: Path) -> List[Dict[str, Any]]:
    root = root.expanduser().resolve()
    projects: List[Dict[str, Any]] = []
    if root.exists() and root.is_dir():
        for child in sorted(root.iterdir(), key=lambda p: p.name):
            if not child.is_dir() or not _is_project_like_dir(child):
                continue
            inputs = detect_project_inputs(child)
            if not inputs:
                continue
            if any(p.get("project_dir") == inputs.get("project_dir") for p in projects):
                continue
            projects.append(inputs)
    if not projects:
        direct = detect_project_inputs(root)
        if direct:
            projects.append(direct)
    return projects


def _run_one_project(
    *,
    project: Dict[str, Any],
    runner: Path,
    workdir: Path,
    out_root: Path,
    self_heal: bool,
) -> Dict[str, Any]:
    project_name = str(project.get("project_name") or "project")
    project_dir = Path(str(project.get("project_dir") or ".")).resolve()
    tenders = [str(x) for x in (project.get("tender_paths") or []) if str(x).strip()]
    boq_path = str(project.get("boq_path") or "")
    safe = _slugify(project_name)
    out_dir = (out_root / safe).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = out_dir / "diagnosis.json"
    missing = out_dir / "Missing_Knowledge_Report.md"

    cmd = [
        "python3",
        str(runner),
        "--tender",
        *tenders,
        "--boq",
        boq_path,
        "--out",
        str(diagnosis),
        "--missing-report",
        str(missing),
        "--no-docx-export",
    ]
    if self_heal:
        cmd.append("--self-heal")
    else:
        cmd.append("--no-self-heal")

    started = time.time()
    proc = subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True)
    elapsed = round(time.time() - started, 2)

    payload: Dict[str, Any] = {}
    if diagnosis.exists():
        try:
            payload = json.loads(diagnosis.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

    agents = payload.get("agents") if isinstance(payload.get("agents"), dict) else {}
    audit_agent = agents.get("audit_agent") if isinstance(agents.get("audit_agent"), dict) else {}
    score_ok = bool((audit_agent.get("result") or {}).get("ok"))
    graph_ok = bool((audit_agent.get("graph_support") or {}).get("ok"))
    intercepted = bool(payload.get("intercepted"))
    gaps = len(payload.get("knowledge_gaps") or [])
    sentence_stats = payload.get("sentence_evidence_stats") if isinstance(payload.get("sentence_evidence_stats"), dict) else {}
    sentence_cov = float(sentence_stats.get("trace_coverage_ratio") or 0.0)
    boq_ingestion = payload.get("boq_ingestion") if isinstance(payload.get("boq_ingestion"), dict) else {}
    failed_boq_files = int(((boq_ingestion.get("stats") or {}).get("failed_file_count") or 0))
    passed = bool(proc.returncode == 0 and not intercepted and gaps == 0 and score_ok and graph_ok)

    return {
        "project_name": project_name,
        "project_dir": str(project_dir),
        "tender_paths": tenders,
        "boq_path": boq_path,
        "return_code": proc.returncode,
        "elapsed_seconds": elapsed,
        "passed": passed,
        "intercepted": intercepted,
        "knowledge_gap_count": gaps,
        "score_coverage_ok": score_ok,
        "graph_support_ok": graph_ok,
        "sentence_trace_coverage": sentence_cov,
        "boq_failed_file_count": failed_boq_files,
        "diagnosis_json": str(diagnosis),
        "missing_report_md": str(missing),
        "stdout_tail": (proc.stdout or "").strip().splitlines()[-20:],
        "stderr_tail": (proc.stderr or "").strip().splitlines()[-20:],
    }


def _evaluate_project_gate(row: Dict[str, Any], gate: Dict[str, Any]) -> Dict[str, Any]:
    reasons: List[str] = []
    base_ok = bool(row.get("passed"))
    if not base_ok:
        reasons.append("base_pipeline_failed")

    min_sentence = float(gate.get("min_sentence_coverage") or 0.0)
    if float(row.get("sentence_trace_coverage") or 0.0) < min_sentence:
        reasons.append("sentence_coverage_below_threshold")

    max_gaps = int(gate.get("max_gaps_per_project") or 0)
    if int(row.get("knowledge_gap_count") or 0) > max_gaps:
        reasons.append("knowledge_gaps_exceed_threshold")

    max_boq_failed = int(gate.get("max_boq_failed_files") or 0)
    if int(row.get("boq_failed_file_count") or 0) > max_boq_failed:
        reasons.append("boq_failed_files_exceed_threshold")

    gate_passed = len(reasons) == 0
    out = dict(row)
    out["gate_passed"] = gate_passed
    out["gate_reasons"] = reasons
    out["passed"] = gate_passed
    return out


def _evaluate_overall_gate(rows: List[Dict[str, Any]], gate: Dict[str, Any]) -> Dict[str, Any]:
    total = len(rows)
    passed = sum(1 for r in rows if r.get("gate_passed"))
    rate = round(passed / total, 4) if total else 0.0
    min_rate = float(gate.get("min_pass_rate") or 0.0)
    ok = bool(total > 0 and rate >= min_rate)
    return {
        "ok": ok,
        "pass_rate": rate,
        "min_pass_rate": min_rate,
        "passed_count": passed,
        "failed_count": max(total - passed, 0),
        "projects_total": total,
    }


def _render_report(summary: Dict[str, Any], *, out_json: Path, out_md: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: List[str] = []
    lines.append("# Real Project Regression Report")
    lines.append("")
    lines.append(f"- Generated At: {summary.get('generated_at')}")
    lines.append(f"- Projects Total: {summary.get('projects_total')}")
    lines.append(f"- Passed: {summary.get('passed_count')}")
    lines.append(f"- Failed: {summary.get('failed_count')}")
    lines.append(f"- Pass Rate: {summary.get('pass_rate')}")
    gate = summary.get("quality_gate") if isinstance(summary.get("quality_gate"), dict) else {}
    if gate:
        lines.append(f"- Quality Gate OK: {bool(gate.get('ok'))}")
        lines.append(
            "- Gate Config: "
            f"min_pass_rate={gate.get('min_pass_rate')}, "
            f"min_sentence_coverage={gate.get('min_sentence_coverage')}, "
            f"max_gaps_per_project={gate.get('max_gaps_per_project')}, "
            f"max_boq_failed_files={gate.get('max_boq_failed_files')}"
        )
    lines.append("")
    lines.append(
        "| Project | Passed | Intercepted | Gaps | ScoreOK | GraphOK | SentenceCoverage | BOQFailFiles | Elapsed(s) | GateReasons |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for row in summary.get("projects") or []:
        reasons = ",".join([str(x) for x in (row.get("gate_reasons") or [])]) or "-"
        lines.append(
            "| {project} | {passed} | {intercepted} | {gaps} | {score_ok} | {graph_ok} | {cov:.4f} | {boq_failed} | {elapsed:.2f} | {reasons} |".format(
                project=row.get("project_name"),
                passed=1 if row.get("passed") else 0,
                intercepted=1 if row.get("intercepted") else 0,
                gaps=int(row.get("knowledge_gap_count") or 0),
                score_ok=1 if row.get("score_coverage_ok") else 0,
                graph_ok=1 if row.get("graph_support_ok") else 0,
                cov=float(row.get("sentence_trace_coverage") or 0.0),
                boq_failed=int(row.get("boq_failed_file_count") or 0),
                elapsed=float(row.get("elapsed_seconds") or 0.0),
                reasons=reasons,
            )
        )
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Batch real-project regression runner for V2 pipeline.")
    p.add_argument("--projects-root", default=str(DEFAULT_PROJECTS_ROOT), help="项目根目录（自动发现项目子目录）。")
    p.add_argument("--project-dir", nargs="*", default=None, help="显式项目目录列表（指定后仅跑这些目录）。")
    p.add_argument("--runner", default=str(DEFAULT_RUNNER), help="run_real_project.py 路径。")
    p.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="回归汇总 JSON 输出路径。")
    p.add_argument("--out-md", default=str(DEFAULT_OUT_MD), help="回归汇总 Markdown 输出路径。")
    p.add_argument("--workdir", default=".", help="执行工作目录。")
    p.add_argument("--max-projects", type=int, default=20, help="最多执行项目数量。")
    p.add_argument("--self-heal", action=argparse.BooleanOptionalAction, default=True, help="是否开启自愈。")
    p.add_argument(
        "--min-pass-rate",
        type=float,
        default=float(DEFAULT_GATE_CONFIG["min_pass_rate"]),
        help="回归通过率下限（0-1）。",
    )
    p.add_argument(
        "--min-sentence-coverage",
        type=float,
        default=float(DEFAULT_GATE_CONFIG["min_sentence_coverage"]),
        help="句级证据链覆盖率下限（0-1）。",
    )
    p.add_argument(
        "--max-gaps-per-project",
        type=int,
        default=int(DEFAULT_GATE_CONFIG["max_gaps_per_project"]),
        help="单项目允许的最大知识缺口数。",
    )
    p.add_argument(
        "--max-boq-failed-files",
        type=int,
        default=int(DEFAULT_GATE_CONFIG["max_boq_failed_files"]),
        help="单项目允许的 BOQ 解析失败文件数上限。",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    workdir = Path(args.workdir).expanduser().resolve()
    runner = Path(args.runner).expanduser().resolve()
    out_json = Path(args.out_json).expanduser().resolve()
    out_md = Path(args.out_md).expanduser().resolve()
    out_root = out_json.parent / "regression_runs"

    if not runner.exists():
        print(f"[ERROR] runner not found: {runner}")
        return 1

    projects: List[Dict[str, Any]] = []
    if args.project_dir:
        for p in args.project_dir:
            inputs = detect_project_inputs(Path(p))
            if inputs:
                projects.append(inputs)
    else:
        projects = discover_projects(Path(args.projects_root))

    if not projects:
        print("[ERROR] no runnable projects discovered")
        return 1

    projects = projects[: max(1, int(args.max_projects or 1))]
    gate_cfg = {
        "min_pass_rate": max(0.0, min(1.0, float(args.min_pass_rate))),
        "min_sentence_coverage": max(0.0, min(1.0, float(args.min_sentence_coverage))),
        "max_gaps_per_project": max(0, int(args.max_gaps_per_project)),
        "max_boq_failed_files": max(0, int(args.max_boq_failed_files)),
    }
    rows: List[Dict[str, Any]] = []
    for project in projects:
        raw_row = _run_one_project(
            project=project,
            runner=runner,
            workdir=workdir,
            out_root=out_root,
            self_heal=bool(args.self_heal),
        )
        row = _evaluate_project_gate(raw_row, gate_cfg)
        rows.append(row)
        print(
            f"[PROJECT] {row['project_name']} passed={row['passed']} gaps={row['knowledge_gap_count']} "
            f"intercepted={row['intercepted']} coverage={row['sentence_trace_coverage']:.4f} "
            f"boq_fail={row['boq_failed_file_count']} elapsed={row['elapsed_seconds']:.2f}s"
        )

    gate_result = _evaluate_overall_gate(rows, gate_cfg)
    passed_count = int(gate_result.get("passed_count") or 0)
    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "projects_total": int(gate_result.get("projects_total") or len(rows)),
        "passed_count": passed_count,
        "failed_count": int(gate_result.get("failed_count") or (len(rows) - passed_count)),
        "pass_rate": float(gate_result.get("pass_rate") or 0.0),
        "quality_gate": {
            "ok": bool(gate_result.get("ok")),
            **gate_cfg,
        },
        "projects": rows,
    }
    _render_report(summary, out_json=out_json, out_md=out_md)
    print(f"summary_json={out_json}")
    print(f"summary_md={out_md}")
    return 0 if bool(gate_result.get("ok")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
