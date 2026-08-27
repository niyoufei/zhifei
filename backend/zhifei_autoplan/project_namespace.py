from __future__ import annotations

"""Collision-resistant project storage namespaces.

Project identifiers are business identifiers, not trusted path components.  A
single implementation is shared by every project-scoped store so Tender, BoQ,
plans, branding, parameter receipts, and variant state can never disagree
about where one project's data belongs.
"""

import hashlib
import re
import unicodedata
from typing import Any


_SAFE_PROJECT_CHARS = re.compile(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]+")


def normalize_project_id(value: Any) -> str:
    """Return the canonical business identifier without making it a path."""

    return unicodedata.normalize("NFKC", str(value or "")).strip()


def project_storage_key(value: Any, *, limit: int = 80) -> str:
    """Return a stable, readable, collision-resistant path component.

    Identifiers already safe and shorter than ``limit`` retain their historical
    directory name, preserving existing ASCII project deployments.  Whenever
    characters must be replaced or the value must be shortened, a digest of the
    *full canonical identifier* is appended so different projects cannot
    collapse into one directory.
    """

    project_id = normalize_project_id(value)
    if not project_id:
        raise ValueError("missing project_id")
    maximum = max(32, min(160, int(limit or 80)))
    readable = _SAFE_PROJECT_CHARS.sub("_", project_id).strip("._-")
    unchanged = readable == project_id and len(readable) <= maximum
    if unchanged:
        return readable

    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:16]
    suffix = f"--{digest}"
    prefix_limit = max(1, maximum - len(suffix))
    prefix = readable[:prefix_limit].rstrip("._-") or "project"
    return f"{prefix}{suffix}"
