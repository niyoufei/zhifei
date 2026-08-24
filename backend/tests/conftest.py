from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture(autouse=True)
def preserve_preloaded_module_identity():
    """Keep destructive import-isolation checks local to their own test.

    Several contract tests deliberately remove already imported production
    modules from ``sys.modules``.  Restoring the exact pre-test module objects
    prevents later tests from patching a newly imported module while calling a
    function retained from the original module object.
    """

    before = dict(sys.modules)
    yield
    for name, module in before.items():
        if sys.modules.get(name) is not module:
            sys.modules[name] = module


@pytest.fixture
def assert_clean_import():
    """Assert import boundaries in a fresh interpreter, independent of order."""

    repo_root = Path(__file__).resolve().parents[2]

    def check(module_name, forbidden_modules):
        forbidden = sorted(set(forbidden_modules))
        code = (
            "import importlib,json,sys;"
            f"importlib.import_module({module_name!r});"
            f"forbidden=set(json.loads({json.dumps(forbidden)!r}));"
            "leaked=sorted(forbidden.intersection(sys.modules));"
            "print(json.dumps(leaked));"
            "raise SystemExit(1 if leaked else 0)"
        )
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(repo_root)
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"{module_name} imported forbidden modules: {result.stdout.strip()}"
            f"\n{result.stderr.strip()}"
        )

    return check


@pytest.fixture
def allow_legacy_export_contract(monkeypatch):
    """Keep legacy renderer tests focused on document structure.

    Production export validation is covered separately by dedicated fail-closed
    gate tests. This fixture never changes production code.
    """
    from backend.zhifei_autoplan import exporter

    monkeypatch.setattr(
        exporter,
        "_local_adapter_validate_before_export",
        lambda _data: {"status": "pass", "export_allowed": True, "issues": []},
    )
