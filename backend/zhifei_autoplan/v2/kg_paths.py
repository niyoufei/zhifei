from __future__ import annotations

import os
from pathlib import Path

ENV_KG_ROOT_KEY = "ZF_KG_ROOT"


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def embedded_kg_root() -> Path:
    return project_root() / "知识图谱"


def alternate_kg_root() -> Path:
    return project_root() / "knowledge_graph"


def _has_kg_files(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    return any(root.glob("ZF-KG-*.json"))


def resolve_default_kg_root() -> Path:
    env_raw = os.getenv(ENV_KG_ROOT_KEY)
    if env_raw:
        env_path = Path(env_raw).expanduser().resolve()
        if env_path.exists():
            return env_path

    embedded = embedded_kg_root().resolve()
    if _has_kg_files(embedded):
        return embedded

    alternate = alternate_kg_root().resolve()
    if _has_kg_files(alternate):
        return alternate

    return embedded
