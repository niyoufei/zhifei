from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.v2.kg_paths import (
    ENV_KG_ROOT_KEY,
    alternate_kg_root,
    embedded_kg_root,
    project_root,
    resolve_default_kg_root,
)


def test_project_root_contains_backend_dir() -> None:
    root = project_root()
    assert (root / "backend").exists()


def test_resolve_default_kg_root_prefers_env(monkeypatch, tmp_path: Path) -> None:
    kg = tmp_path / "kg_env"
    kg.mkdir(parents=True, exist_ok=True)
    (kg / "ZF-KG-01.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv(ENV_KG_ROOT_KEY, str(kg))

    resolved = resolve_default_kg_root()
    assert resolved == kg.resolve()


def test_embedded_kg_root_path_is_inside_project() -> None:
    root = project_root()
    embedded = embedded_kg_root()
    assert str(embedded).startswith(str(root))
    assert embedded.name == "知识图谱"


def test_alternate_kg_root_path_is_inside_project() -> None:
    root = project_root()
    alternate = alternate_kg_root()
    assert str(alternate).startswith(str(root))
    assert alternate.name == "knowledge_graph"


def test_resolve_default_kg_root_falls_back_to_alternate(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    alternate = workspace / "knowledge_graph"
    alternate.mkdir(parents=True, exist_ok=True)
    (alternate / "ZF-KG-01.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr("backend.zhifei_autoplan.v2.kg_paths.project_root", lambda: workspace)
    monkeypatch.delenv(ENV_KG_ROOT_KEY, raising=False)

    resolved = resolve_default_kg_root()
    assert resolved == alternate.resolve()
