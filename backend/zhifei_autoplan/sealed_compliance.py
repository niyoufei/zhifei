from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SOURCE_OFFICIAL_REGISTRY_RELATIVE_PATH = Path(
    "知识图谱/compliance/_official_registry.json"
)
SEALED_COMPLIANCE_ROOT_RELATIVE_PATH = Path("sealed-compliance")
SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH = (
    SEALED_COMPLIANCE_ROOT_RELATIVE_PATH / "_official_registry.json"
)
SEALED_REGISTRY_AUTHORITY_SCHEMA = "sealed-compliance-registry-authority-v1"
_FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_ID_RE = re.compile(r"^release-[0-9a-f]{24}$")
_MAX_REGISTRY_BYTES = 2 * 1024 * 1024
_MAX_MANIFEST_BYTES = 64 * 1024 * 1024


class SealedComplianceError(RuntimeError):
    """Raised when the sealed compliance authority cannot be proven."""

    def __init__(self, code: str):
        self.code = str(code or "SEALED_COMPLIANCE_UNTRUSTED")
        super().__init__(self.code)


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _lexical_absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_path_without_symlinks(path: Path, *, root: Path) -> None:
    lexical_root = _lexical_absolute(root)
    lexical_path = _lexical_absolute(path)
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise SealedComplianceError("SEALED_COMPLIANCE_PATH_OUTSIDE_RELEASE") from exc
    current = lexical_root
    try:
        root_info = current.lstat()
        if current.is_symlink() or not stat.S_ISDIR(root_info.st_mode):
            raise SealedComplianceError("SEALED_COMPLIANCE_RELEASE_ROOT_UNTRUSTED")
        for index, part in enumerate(relative.parts):
            current = current / part
            info = current.lstat()
            if current.is_symlink():
                raise SealedComplianceError("SEALED_COMPLIANCE_PATH_SYMLINK")
            if index < len(relative.parts) - 1:
                if not stat.S_ISDIR(info.st_mode):
                    raise SealedComplianceError("SEALED_COMPLIANCE_PATH_UNTRUSTED")
            elif not stat.S_ISREG(info.st_mode):
                raise SealedComplianceError("SEALED_COMPLIANCE_FILE_UNTRUSTED")
    except SealedComplianceError:
        raise
    except OSError as exc:
        raise SealedComplianceError("SEALED_COMPLIANCE_PATH_UNAVAILABLE") from exc


def _read_stable_file(
    path: Path,
    *,
    expected_mode: int,
    max_bytes: int,
    root: Path,
) -> tuple[bytes, str]:
    _assert_path_without_symlinks(path, root=root)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SealedComplianceError("SEALED_COMPLIANCE_FILE_UNREADABLE") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or stat.S_IMODE(before.st_mode) != expected_mode
            or before.st_size <= 0
            or before.st_size > max_bytes
        ):
            raise SealedComplianceError("SEALED_COMPLIANCE_FILE_UNTRUSTED")
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_mode")
    if (
        len(raw) != before.st_size
        or len(raw) > max_bytes
        or any(getattr(before, field) != getattr(after, field) for field in fields)
    ):
        raise SealedComplianceError("SEALED_COMPLIANCE_FILE_CHANGED")
    try:
        current = path.lstat()
    except OSError as exc:
        raise SealedComplianceError("SEALED_COMPLIANCE_FILE_CHANGED") from exc
    if path.is_symlink() or any(
        getattr(after, field) != getattr(current, field) for field in fields
    ):
        raise SealedComplianceError("SEALED_COMPLIANCE_FILE_CHANGED")
    return raw, hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class SealedRegistryAuthority:
    raw: bytes
    path: Path
    projection: dict[str, Any]


def validate_registry_authority_projection(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SealedComplianceError("SEALED_COMPLIANCE_AUTHORITY_INVALID")
    projection = dict(value)
    fields = {
        "schema_version",
        "source_kind",
        "release_id",
        "manifest_digest",
        "source_digest",
        "runtime_digest",
        "registry_path",
        "registry_relative_path",
        "registry_sha256",
        "registry_size",
        "registry_mode",
        "authority_digest",
    }
    core = {key: item for key, item in projection.items() if key != "authority_digest"}
    if (
        set(projection) != fields
        or projection.get("schema_version") != SEALED_REGISTRY_AUTHORITY_SCHEMA
        or projection.get("source_kind") != "sealed_release_manifest_entry"
        or _RELEASE_ID_RE.fullmatch(str(projection.get("release_id") or "")) is None
        or any(
            _FULL_SHA256_RE.fullmatch(str(projection.get(field) or "").lower())
            is None
            for field in (
                "manifest_digest",
                "source_digest",
                "runtime_digest",
                "registry_sha256",
            )
        )
        or projection.get("registry_relative_path")
        != SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix()
        or not Path(str(projection.get("registry_path") or "")).is_absolute()
        or isinstance(projection.get("registry_size"), bool)
        or not isinstance(projection.get("registry_size"), int)
        or int(projection.get("registry_size") or 0) <= 0
        or projection.get("registry_mode") != 0o444
        or str(projection.get("authority_digest") or "") != _canonical_digest(core)
    ):
        raise SealedComplianceError("SEALED_COMPLIANCE_AUTHORITY_INVALID")
    if projection["release_id"] != f"release-{projection['source_digest'][:24]}":
        raise SealedComplianceError("SEALED_COMPLIANCE_AUTHORITY_INVALID")
    return projection


def sealed_official_registry_path(release_root: str | Path) -> Path:
    """Return the lexical sealed-registry path without resolving links."""

    root = _lexical_absolute(release_root)
    return root / SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH


def load_sealed_registry_authority(
    release_root: str | Path,
    *,
    expected_release_id: str | None = None,
    expected_manifest_digest: str | None = None,
    expected_source_digest: str | None = None,
    expected_runtime_digest: str | None = None,
) -> SealedRegistryAuthority:
    """Read the manifest-covered registry without following mutable links."""

    root = _lexical_absolute(release_root)
    registry_path = sealed_official_registry_path(root)
    manifest_path = root / "release-manifest.json"
    registry_raw, registry_sha256 = _read_stable_file(
        registry_path,
        expected_mode=0o444,
        max_bytes=_MAX_REGISTRY_BYTES,
        root=root,
    )
    manifest_raw, manifest_digest = _read_stable_file(
        manifest_path,
        expected_mode=0o444,
        max_bytes=_MAX_MANIFEST_BYTES,
        root=root,
    )
    try:
        registry_payload = json.loads(registry_raw.decode("utf-8"))
        manifest = json.loads(manifest_raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise SealedComplianceError("SEALED_COMPLIANCE_JSON_INVALID") from exc
    if (
        not isinstance(registry_payload, dict)
        or not isinstance(registry_payload.get("standards"), list)
        or not registry_payload["standards"]
        or not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or not isinstance(manifest.get("files"), list)
        or not isinstance(manifest.get("directories"), list)
    ):
        raise SealedComplianceError("SEALED_COMPLIANCE_JSON_INVALID")
    release_id = str(manifest.get("release_id") or "").strip()
    source_digest = str(manifest.get("source_digest") or "").strip().lower()
    runtime_digest = str(manifest.get("runtime_digest") or "").strip().lower()
    if (
        _RELEASE_ID_RE.fullmatch(release_id) is None
        or _FULL_SHA256_RE.fullmatch(source_digest) is None
        or _FULL_SHA256_RE.fullmatch(runtime_digest) is None
        or release_id != f"release-{source_digest[:24]}"
        or (expected_release_id is not None and release_id != expected_release_id)
        or (
            expected_manifest_digest is not None
            and manifest_digest != expected_manifest_digest
        )
        or (expected_source_digest is not None and source_digest != expected_source_digest)
        or (
            expected_runtime_digest is not None
            and runtime_digest != expected_runtime_digest
        )
    ):
        raise SealedComplianceError("SEALED_COMPLIANCE_RELEASE_IDENTITY_MISMATCH")
    file_rows = [
        row
        for row in manifest["files"]
        if isinstance(row, Mapping)
        and row.get("path") == SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix()
    ]
    directory_rows = [
        row
        for row in manifest["directories"]
        if isinstance(row, Mapping)
        and row.get("path") == SEALED_COMPLIANCE_ROOT_RELATIVE_PATH.as_posix()
    ]
    if (
        len(file_rows) != 1
        or len(directory_rows) != 1
        or file_rows[0].get("sha256") != registry_sha256
        or file_rows[0].get("size") != len(registry_raw)
        or file_rows[0].get("mode") != 0o444
        or directory_rows[0].get("mode") != 0o555
    ):
        raise SealedComplianceError("SEALED_COMPLIANCE_MANIFEST_MISMATCH")
    core = {
        "schema_version": SEALED_REGISTRY_AUTHORITY_SCHEMA,
        "source_kind": "sealed_release_manifest_entry",
        "release_id": release_id,
        "manifest_digest": manifest_digest,
        "source_digest": source_digest,
        "runtime_digest": runtime_digest,
        "registry_path": str(registry_path),
        "registry_relative_path": SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix(),
        "registry_sha256": registry_sha256,
        "registry_size": len(registry_raw),
        "registry_mode": 0o444,
    }
    projection = {**core, "authority_digest": _canonical_digest(core)}
    validate_registry_authority_projection(projection)
    return SealedRegistryAuthority(
        raw=registry_raw,
        path=registry_path,
        projection=projection,
    )
