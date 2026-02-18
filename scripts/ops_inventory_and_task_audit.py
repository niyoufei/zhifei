#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
INVENTORY_DIR = BUILD / "inventory"


EXCLUDE_DIRS = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".cursor",
}


def _iter_files(base: Path) -> Iterable[Path]:
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if any(seg in EXCLUDE_DIRS for seg in p.parts):
            continue
        yield p


def _write_list(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


@dataclass
class TaskStatus:
    task_id: int
    name: str
    status: str
    evidence: list[str]
    pending_reason: str = ""


def _exists_all(paths: list[str]) -> tuple[bool, list[str]]:
    ok = True
    ev: list[str] = []
    for x in paths:
        p = ROOT / x
        if p.exists():
            ev.append(x)
        else:
            ok = False
    return ok, ev


def _task_status() -> list[TaskStatus]:
    tasks: list[TaskStatus] = []

    checks = [
        (
            1,
            "代码基座收敛",
            [
                "backend/zhifei_autoplan/orchestrator.py",
                "backend/app/routers/actions_bridge.py",
                "scripts/check_repo_layout.sh",
            ],
        ),
        (
            2,
            "参数注册表工程化",
            [
                "backend/zhifei_autoplan/params_runtime.py",
                "backend/data/autoplan/params.json",
                "backend/zhifei_autoplan/param_trace.py",
            ],
        ),
        (
            3,
            "重点清单项精确落位",
            [
                "backend/zhifei_autoplan/boq_focus_enforcer.py",
                "backend/zhifei_autoplan/cross_index.py",
                "backend/zhifei_autoplan/focus_card_parser.py",
            ],
        ),
        (
            4,
            "证据定位统一与可追溯",
            [
                "backend/zhifei_autoplan/evidence.py",
                "backend/zhifei_autoplan/drawing_index.py",
                "backend/zhifei_autoplan/standard_index.py",
            ],
        ),
        (
            5,
            "A/B/C章内逻辑与变体轮转",
            [
                "backend/zhifei_autoplan/logic_templates.py",
                "backend/zhifei_autoplan/variant_cycle.py",
                "backend/data/autoplan/logic_templates.json",
            ],
        ),
        (
            6,
            "风险三元组与闭环质控",
            [
                "backend/zhifei_autoplan/quality_check.py",
                "backend/tests/test_quality_check.py",
            ],
        ),
        (
            7,
            "无值守批量编制",
            [
                "scripts/watch_projects_autoplan.py",
                "scripts/install_launchd_agent.sh",
                "deploy/systemd/docgen-autoplan.service",
            ],
        ),
        (
            8,
            "图文生成与品牌能力",
            [
                "backend/zhifei_autoplan/image_runtime.py",
                "backend/zhifei_autoplan/logo_runtime.py",
                "backend/zhifei_autoplan/branding_store.py",
            ],
        ),
        (
            9,
            "计划一致性单一数据源",
            [
                "backend/zhifei_autoplan/plan_consistency.py",
                "backend/zhifei_autoplan/params_runtime.py",
                "backend/zhifei_autoplan/param_trace.py",
            ],
        ),
    ]

    for tid, name, files in checks:
        ok, ev = _exists_all(files)
        tasks.append(
            TaskStatus(
                task_id=tid,
                name=name,
                status="done" if ok else "pending",
                evidence=ev,
                pending_reason="" if ok else "核心文件缺失",
            )
        )

    # task 10: run-and-deliver acceptance by real project artifacts
    done_outputs = sorted((ROOT / "projects" / "done").glob("**/_output/run_summary.json"))
    ok_summaries: list[str] = []
    for p in done_outputs:
        try:
            obj = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            if bool(obj.get("ok")):
                ok_summaries.append(_rel(p))
        except Exception:
            continue
    tasks.append(
        TaskStatus(
            task_id=10,
            name="运行与交付验收",
            status="done" if len(ok_summaries) > 0 else "pending",
            evidence=ok_summaries[:20],
            pending_reason="" if ok_summaries else "未发现通过验收的 run_summary.json",
        )
    )
    return tasks


def _write_markdown(tasks: list[TaskStatus], out: Path) -> None:
    lines = [
        "# 1-10任务文件证据状态",
        "",
        "| 任务 | 状态 | 证据条目数 |",
        "|---|---|---:|",
    ]
    for t in tasks:
        lines.append(f"| {t.task_id}. {t.name} | {t.status} | {len(t.evidence)} |")
    lines.append("")
    pending = [t for t in tasks if t.status != "done"]
    if pending:
        lines.append("## 待推进")
        for t in pending:
            lines.append(f"- {t.task_id}. {t.name}: {t.pending_reason}")
    else:
        lines.append("## 待推进")
        lines.append("- 无")
    _write_list(out, lines)


def main() -> int:
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)

    all_files = sorted(_rel(p) for p in _iter_files(ROOT))
    backend_files = sorted(_rel(p) for p in _iter_files(ROOT / "backend"))

    output_files: list[str] = []
    for p in sorted((ROOT / "projects").glob("**/_output/*")):
        if p.is_file():
            output_files.append(_rel(p))
    for p in sorted(BUILD.glob("actions_*")):
        if p.is_file():
            output_files.append(_rel(p))
    output_files = sorted(set(output_files))

    _write_list(INVENTORY_DIR / "full_files.txt", all_files)
    _write_list(INVENTORY_DIR / "backend_files.txt", backend_files)
    _write_list(INVENTORY_DIR / "output_files.txt", output_files)

    tasks = _task_status()
    status_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workspace": str(ROOT),
        "inventory": {
            "full_files": len(all_files),
            "backend_files": len(backend_files),
            "output_files": len(output_files),
        },
        "tasks": [asdict(t) for t in tasks],
        "pending_task_ids": [t.task_id for t in tasks if t.status != "done"],
    }

    (BUILD / "task_1_10_status.json").write_text(
        json.dumps(status_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_markdown(tasks, BUILD / "task_1_10_status.md")

    print(json.dumps(status_json, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
