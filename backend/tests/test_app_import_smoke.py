from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import BaseModel, EmailStr, ValidationError


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_RESULT_PREFIX = "R144_APP_IMPORT_RESULT="
_REQUIRED_ROUTES = frozenset({"/health", "/p0/readiness"})
_PARENT_FORBIDDEN_MODULES = frozenset(
    {
        "backend.app.main",
        "backend.app.routers.actions_bridge",
        "backend.zhifei_autoplan.export_docx_service",
        "backend.zhifei_autoplan.exporter",
        "backend.zhifei_autoplan.job_store",
        "backend.zhifei_autoplan.orchestrator",
        "backend.zhifei_autoplan.output_artifacts",
        "backend.zhifei_autoplan.zbid_snapshot_mapper",
        "docx",
    }
)
_CHILD_SCRIPT = r"""
import importlib
import json

from fastapi import FastAPI

app_module = importlib.import_module("backend.app.main")
app = app_module.app
route_paths = sorted({route.path for route in app.routes})
result = {
    "app_is_fastapi": isinstance(app, FastAPI),
    "required_routes": ["/health", "/p0/readiness"],
    "route_paths": route_paths,
    "optional_healthz_present": "/healthz" in route_paths,
}
print("R144_APP_IMPORT_RESULT=" + json.dumps(result, sort_keys=True))
"""


class _LocalEmailModel(BaseModel):
    email: EmailStr


def _child_environment() -> dict[str, str]:
    environment = {
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(_REPOSITORY_ROOT),
    }
    if os.environ.get("PATH"):
        environment["PATH"] = os.environ["PATH"]
    for name in ("TMPDIR", "TMP", "TEMP"):
        if os.environ.get(name):
            environment[name] = os.environ[name]
    return environment


def _run_full_app_import() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT],
        cwd=_REPOSITORY_ROOT,
        env=_child_environment(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )


def _parse_child_result(stdout: str) -> dict[str, object]:
    result_lines = [
        line.removeprefix(_RESULT_PREFIX)
        for line in stdout.splitlines()
        if line.startswith(_RESULT_PREFIX)
    ]
    assert len(result_lines) == 1, stdout
    return json.loads(result_lines[0])


def test_full_app_import_exposes_required_routes() -> None:
    before = _PARENT_FORBIDDEN_MODULES.intersection(sys.modules)
    completed = _run_full_app_import()
    after = _PARENT_FORBIDDEN_MODULES.intersection(sys.modules)

    assert completed.returncode == 0, (
        f"child exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
    payload = _parse_child_result(completed.stdout)
    route_paths = set(payload["route_paths"])

    assert payload["app_is_fastapi"] is True
    assert _REQUIRED_ROUTES.issubset(route_paths)
    assert set(payload["required_routes"]) == _REQUIRED_ROUTES
    assert "/healthz" not in payload["required_routes"]
    assert after == before


def test_emailstr_accepts_and_rejects_local_fictitious_samples() -> None:
    validated = _LocalEmailModel(email="valid-example@example.com")
    assert str(validated.email) == "valid-example@example.com"

    with pytest.raises(ValidationError):
        _LocalEmailModel(email="not-an-email")
