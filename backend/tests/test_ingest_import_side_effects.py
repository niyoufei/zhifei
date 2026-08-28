from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_importing_ingest_router_does_not_create_runtime_directories(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repository_root)

    subprocess.run(
        [sys.executable, "-c", "import backend.app.routers.ingest"],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert list(tmp_path.iterdir()) == []
