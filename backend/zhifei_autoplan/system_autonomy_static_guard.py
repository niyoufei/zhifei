from __future__ import annotations

import shlex
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Iterable


class RiskCategory(str, Enum):
    RUNTIME = "runtime"
    ENDPOINT = "endpoint"
    OLLAMA = "ollama"
    MODEL = "model"
    PROMPT = "prompt"
    KG = "kg"
    REAL_PROJECT_DATA = "real_project_data"
    SECRETS = "secrets"
    OUTPUT_JOB_EXPORT_LOG = "output_job_export_log"
    GENERATION_EXPORT_WRITEBACK = "generation_export_writeback"
    WEB_UI = "web_ui"


AUTHORIZED_CHANGED_FILES = frozenset(
    {
        "backend/zhifei_autoplan/system_autonomy_static_guard.py",
        "backend/tests/test_system_autonomy_static_guard.py",
        "docs/zdoc-system-autonomy-012-implementation-static-guard-scope-correction-no-runtime.md",
    }
)

FORBIDDEN_PATH_MARKERS = {
    RiskCategory.KG: (
        "知识图谱/",
        "knowledge graph",
        "knowledge-graph",
        "knowledge_graph",
        "real kg",
        "real-kg",
        "real_kg",
        "kg/",
        "knowledge_graph/",
        "backend/data/kg/",
        "kg_packs/",
        "backend/kg_packs/",
    ),
    RiskCategory.REAL_PROJECT_DATA: (
        "真实项目",
        "真实资料",
        "招标",
        "投标",
        "图纸",
        "清单",
        "项目样本",
        "real_project",
        "project_data",
        "project_sample",
        "project_samples",
        "tender",
        "bid_file",
        "drawings/",
        "boq/",
        "backend/data/uploads/",
        "backend/data/extracts/",
        "data/uploads/",
        "data/extracts/",
    ),
    RiskCategory.SECRETS: (
        ".env",
        "secrets/",
        "tokens/",
        "credentials/",
        "secret",
        "token",
        "credential",
        "credentials",
        "private_key",
        ".pem",
        ".key",
        ".crt",
    ),
    RiskCategory.OUTPUT_JOB_EXPORT_LOG: (
        "output/",
        "outputs/",
        "job/",
        "jobs/",
        "export/",
        "exports/",
        "log/",
        "logs/",
        ".log",
        "build/",
        ".runtime/docgen",
        ".runtime/docgen/",
        "backend/data/audit/",
        "data/audit/",
    ),
    RiskCategory.RUNTIME: (
        "scripts/run_web_ui.sh",
        "scripts/start_web_ui_background.sh",
        "scripts/stop_web_ui_background.sh",
        "scripts/web_ui_watchdog.sh",
        "deploy/systemd/",
    ),
    RiskCategory.WEB_UI: ("local-launcher-v1/", "frontend_web/", "frontend/"),
    RiskCategory.ENDPOINT: ("backend/app/routers/", "api/server.py", "backend/app/main.py"),
    RiskCategory.MODEL: ("providers/", "llm_client.py", "ollama_preview.py"),
}

FORBIDDEN_COMMAND_MARKERS = {
    RiskCategory.RUNTIME: ("uvicorn", "streamlit", "gunicorn", "hypercorn", "serve", "dev"),
    RiskCategory.WEB_UI: ("run_web_ui.sh", "start_web_ui_background.sh"),
    RiskCategory.ENDPOINT: ("curl", "http://", "https://", "localhost", "127.0.0.1", "port"),
    RiskCategory.OLLAMA: ("ollama",),
    RiskCategory.MODEL: ("model", "inference", "chat", "generate"),
    RiskCategory.PROMPT: ("prompt",),
    RiskCategory.KG: ("kg_runtime", "kg_store", "knowledge_graph", "知识图谱"),
    RiskCategory.GENERATION_EXPORT_WRITEBACK: ("generation", "export", "write-back", "writeback"),
    RiskCategory.OUTPUT_JOB_EXPORT_LOG: ("output", "job", "log", ".runtime/docgen"),
    RiskCategory.SECRETS: (".env", "token", "credential", "secret"),
}


@dataclass(frozen=True)
class StaticGuardResult:
    allowed: bool
    risk_categories: tuple[RiskCategory, ...]
    blocked_items: tuple[str, ...]
    blocked_reasons: tuple[str, ...]


def analyze_path_string(path: str) -> StaticGuardResult:
    normalized = _normalize_path(path)
    risks = _risks_for_text(
        f"{normalized}/{normalized.strip('/')}/", FORBIDDEN_PATH_MARKERS
    )
    return StaticGuardResult(
        allowed=not risks,
        risk_categories=risks,
        blocked_items=(normalized,) if risks else (),
        blocked_reasons=("path_matches_forbidden_static_boundary",) if risks else (),
    )


def analyze_command_string(command: str) -> StaticGuardResult:
    lowered = " ".join(shlex.split(command, posix=True)).lower() if command.strip() else ""
    risks = _risks_for_text(lowered, FORBIDDEN_COMMAND_MARKERS)
    return StaticGuardResult(
        allowed=not risks,
        risk_categories=risks,
        blocked_items=(command,) if risks else (),
        blocked_reasons=("command_matches_forbidden_static_boundary",) if risks else (),
    )


def validate_changed_files(paths: Iterable[str]) -> StaticGuardResult:
    outside = tuple(path for path in paths if _normalize_path(path) not in AUTHORIZED_CHANGED_FILES)
    risks: list[RiskCategory] = []
    for path in outside:
        risks.extend(analyze_path_string(path).risk_categories)
    blocked_reasons = []
    if outside:
        blocked_reasons.append("changed_file_outside_system_autonomy_012_static_guard_scope")
    if risks:
        blocked_reasons.append("changed_file_matches_forbidden_boundary")
    return StaticGuardResult(
        allowed=not outside and not risks,
        risk_categories=tuple(dict.fromkeys(risks)),
        blocked_items=outside,
        blocked_reasons=tuple(blocked_reasons),
    )


def _normalize_path(path: str) -> str:
    clean = str(PurePosixPath(str(path).replace("\\", "/")))
    while clean.startswith("./"):
        clean = clean[2:]
    clean = clean.lstrip("/")
    return "" if clean == "." else clean


def _risks_for_text(
    text: str, marker_map: dict[RiskCategory, tuple[str, ...]]
) -> tuple[RiskCategory, ...]:
    lowered = text.lower()
    risks = [
        category
        for category, markers in marker_map.items()
        if any(marker.lower() in lowered for marker in markers)
    ]
    return tuple(dict.fromkeys(risks))
