from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan import variant_cycle


def _patch_paths(tmp_path: Path, monkeypatch):
    base = tmp_path / "autoplan"
    projects = base / "projects"
    global_state = base / "variant_cycle_global.json"
    monkeypatch.setattr(variant_cycle, "BASE_DIR", base)
    monkeypatch.setattr(variant_cycle, "PROJECTS_DIR", projects)
    monkeypatch.setattr(variant_cycle, "GLOBAL_STATE_PATH", global_state)


def test_project_cycle_increments_across_calls(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)

    ids1 = variant_cycle.reserve_variant_ids(project_id="p1", count=1)
    ids2 = variant_cycle.reserve_variant_ids(project_id="p1", count=2)
    ids3 = variant_cycle.reserve_variant_ids(project_id="p1", count=1)

    assert ids1 == [1]
    assert ids2 == [2, 3]
    assert ids3 == [4]


def test_explicit_template_does_not_consume_cycle(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)

    ids1 = variant_cycle.reserve_variant_ids(project_id="p2", count=1)
    ids_exp = variant_cycle.reserve_variant_ids(project_id="p2", count=1, explicit_template_id="B")
    ids2 = variant_cycle.reserve_variant_ids(project_id="p2", count=1)

    assert ids1 == [1]
    assert ids_exp == [1]
    assert ids2 == [2]


def test_explicit_variant_id_does_not_consume_cycle(tmp_path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)

    ids_exp = variant_cycle.reserve_variant_ids(project_id="p3", count=2, explicit_variant_id=9)
    ids_next = variant_cycle.reserve_variant_ids(project_id="p3", count=1)

    assert ids_exp == [9, 10]
    assert ids_next == [1]
