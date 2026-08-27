from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_legacy_export_app_compiles_and_imports_without_writing(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(repository_root)

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import export_api_patch; "
            "assert any(route.path == '/export' for route in export_api_patch.app.routes)",
        ],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )

    assert completed.returncode == 0, completed.stderr
    assert list(tmp_path.iterdir()) == []
