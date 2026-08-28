from __future__ import annotations

import os
from pathlib import Path

SOURCE_OFFICIAL_REGISTRY_RELATIVE_PATH = Path(
    "知识图谱/compliance/_official_registry.json"
)
SEALED_COMPLIANCE_ROOT_RELATIVE_PATH = Path("sealed-compliance")
SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH = (
    SEALED_COMPLIANCE_ROOT_RELATIVE_PATH / "_official_registry.json"
)


def sealed_official_registry_path(release_root: str | Path) -> Path:
    """Return the lexical sealed-registry path without resolving links."""

    root = Path(os.path.abspath(os.fspath(release_root)))
    return root / SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH
