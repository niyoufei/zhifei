from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_smart_repo_check_prioritizes_declared_main_chain_entries(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    script = project_root / ".smart_repo_check.py"

    (tmp_path / "backend" / "app").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backend" / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "api").mkdir(parents=True, exist_ok=True)

    (tmp_path / "app.py").write_text(
        "import streamlit as st\nst.title('docgen')\n",
        encoding="utf-8",
    )
    (tmp_path / "backend" / "app" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )
    (tmp_path / "devserver.py").write_text(
        "from fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n"
        "if __name__ == '__main__':\n    uvicorn.run(app)\n",
        encoding="utf-8",
    )
    (tmp_path / "api" / "server.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )
    (tmp_path / "backend" / "tests" / "test_fake_entry.py").write_text(
        "from fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n"
        "if __name__ == '__main__':\n    uvicorn.run(app)\n",
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    report = json.loads((tmp_path / "_smartcheck" / "repo_report.json").read_text(encoding="utf-8"))
    files = [item["file"] for item in report["entry_candidates"][:3]]
    assert files == ["app.py", "backend/app/main.py", "devserver.py"]
    assert "backend/tests/test_fake_entry.py" not in {item["file"] for item in report["entry_candidates"]}


def test_smart_repo_check_skips_runtime_workspace_like_dirs(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    script = project_root / ".smart_repo_check.py"

    runtime_dir = tmp_path / "backend" / "data" / "workspaces" / "demo"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "main.py").write_text(
        "from fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n"
        "if __name__ == '__main__':\n    uvicorn.run(app)\n",
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    report = json.loads((tmp_path / "_smartcheck" / "repo_report.json").read_text(encoding="utf-8"))
    assert "backend/data/workspaces/demo/main.py" not in {item["file"] for item in report["entry_candidates"]}


def test_smart_repo_check_skips_runtime_autoplan_media_dirs(tmp_path):
    project_root = Path(__file__).resolve().parents[2]
    script = project_root / ".smart_repo_check.py"

    runtime_dir = tmp_path / "backend" / "data" / "autoplan" / "media" / "demo"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "server.py").write_text(
        "from fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n"
        "if __name__ == '__main__':\n    uvicorn.run(app)\n",
        encoding="utf-8",
    )

    subprocess.run(
        [sys.executable, str(script)],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    report = json.loads((tmp_path / "_smartcheck" / "repo_report.json").read_text(encoding="utf-8"))
    assert "backend/data/autoplan/media/demo/server.py" not in {item["file"] for item in report["entry_candidates"]}
