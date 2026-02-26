from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "run_real_project.py"
    spec = importlib.util.spec_from_file_location("run_real_project", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_boq_payload_can_merge_directory_csv_files(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "a.csv").write_text(
        "boq_code,name,quantity,unit\nA01,土方开挖,100,m3\nA02,钢筋工程,20,t\n",
        encoding="utf-8",
    )
    (boq_dir / "b.csv").write_text(
        "boq_code,name,quantity,unit\nA01,土方开挖,100,m3\nA03,模板工程,300,m2\n",
        encoding="utf-8",
    )

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    assert isinstance(payload.get("items"), list)
    assert len(payload["items"]) == 3  # one duplicate row should be deduped
    assert int((payload.get("stats") or {}).get("source_file_count") or 0) == 2
    assert int((payload.get("stats") or {}).get("failed_file_count") or 0) == 0


def test_load_boq_payload_keeps_running_when_some_files_fail(tmp_path: Path) -> None:
    mod = _load_module()
    boq_dir = tmp_path / "boq"
    boq_dir.mkdir(parents=True, exist_ok=True)

    (boq_dir / "ok.csv").write_text(
        "boq_code,name,quantity,unit\nB01,机电管线安装,260,m\n",
        encoding="utf-8",
    )
    # Invalid PDF content to force parser failure; merge should continue.
    (boq_dir / "broken.pdf").write_text("not-a-real-pdf", encoding="utf-8")

    payload = asyncio.run(mod._load_boq_payload(boq_dir))
    stats = payload.get("stats") or {}
    assert int(stats.get("item_count") or 0) >= 1
    assert int(stats.get("source_file_count") or 0) == 2
    assert int(stats.get("failed_file_count") or 0) == 1
    assert len(payload.get("parse_errors") or []) == 1
