from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.compliance_policy import (
    build_standard_registry_map,
    is_verified_standard_metadata,
)
from backend.zhifei_autoplan.sealed_compliance import (
    SealedComplianceError,
    SealedRegistryAuthority,
    load_sealed_registry_authority,
)

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]+")
_CODE_WITH_YEAR_RE = re.compile(r"^(?P<prefix>[A-Z]+)_(?P<num>[A-Z0-9]+)_(?P<year>\d{2,4})$")
_CODE_KEY_RE = re.compile(r"^(?P<prefix>[A-Z]+)_(?P<num>[A-Z0-9]+)")
_DOMAIN_SPLIT_RE = re.compile(r"[;,，；、/|]+")
_REGISTRY_FILENAME = "_official_registry.json"
_MAX_COMPLIANCE_JSON_BYTES = 64 * 1024 * 1024


def _norm_text(v: Any) -> str:
    return str(v or "").strip()


def _norm_domain(v: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", str(v or "").strip().lower())


def _tokenize(text: str) -> list[str]:
    out: list[str] = []
    seen = set()
    for t in _TOKEN_RE.findall(text or ""):
        tt = t.strip()
        if len(tt) < 2 or tt in seen:
            continue
        seen.add(tt)
        out.append(tt)
    return out


def _coerce_domains(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        vals = [x.strip() for x in _DOMAIN_SPLIT_RE.split(v) if x.strip()]
    elif isinstance(v, list):
        vals = [str(x).strip() for x in v if str(x).strip()]
    else:
        vals = [str(v).strip()] if str(v).strip() else []
    out: list[str] = []
    seen = set()
    for x in vals:
        nx = _norm_domain(x)
        if not nx or nx in seen:
            continue
        seen.add(nx)
        out.append(x)
    return out


def _domains_overlap(left: Iterable[Any], right: Iterable[Any]) -> bool:
    a = {_norm_domain(x) for x in (left or []) if _norm_domain(x)}
    b = {_norm_domain(x) for x in (right or []) if _norm_domain(x)}
    if not a or not b:
        return False
    if "general" in a or "通用工程" in a:
        return True
    if "general" in b or "通用工程" in b:
        return True
    return bool(a.intersection(b))


def _parse_standard_key_year(standard_code: str) -> tuple[str, int]:
    code = _norm_text(standard_code).upper()
    canonical = re.sub(r"[^A-Z0-9]+", "_", code).strip("_")
    m1 = _CODE_WITH_YEAR_RE.match(canonical)
    if m1:
        return f"{m1.group('prefix')}_{m1.group('num')}", int(m1.group("year"))
    # Standards such as GB/T 50326-2017 contain a slash in the prefix.  Keep
    # the full canonical prefix and strip only the terminal year.
    m_year = re.match(r"^(?P<key>.+)_(?P<year>\d{4})$", canonical)
    if m_year:
        return str(m_year.group("key")), int(m_year.group("year"))
    m2 = _CODE_KEY_RE.match(canonical)
    if m2:
        return f"{m2.group('prefix')}_{m2.group('num')}", 0
    return canonical or "STD_UNKNOWN", 0


def _compliance_root(root: str | Path | None = None) -> Path:
    if root is not None:
        return Path(root)
    env_root = os.environ.get("ZF_COMPLIANCE_ROOT")
    if env_root and str(env_root).strip():
        return Path(env_root).expanduser()
    repo_root = Path(__file__).resolve().parents[2]
    candidates = (
        repo_root / "知识图谱" / "compliance",
        repo_root / "knowledge_graph" / "compliance",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Deterministic default; never depend on the process launch directory.
    return candidates[0]


def _catalog_path(root: Path) -> Path:
    return root / "_catalog.json"


def _registry_path(root: Path) -> Path:
    return root / _REGISTRY_FILENAME


def _managed_release_registry_authority() -> SealedRegistryAuthority | None:
    """Return the manifest-bound registry for a managed release.

    A managed process never falls back to the mutable knowledge-graph registry.
    Development and explicit test roots continue to use their local source
    registry, but production authority is always the sealed manifest entry.
    """

    if str(os.environ.get("ZF_RELEASE_MANAGED") or "") != "1":
        return None
    release_root = str(os.environ.get("ZF_RELEASE_ROOT") or "").strip()
    if not release_root:
        raise SealedComplianceError("SEALED_COMPLIANCE_RELEASE_ROOT_MISSING")
    return load_sealed_registry_authority(
        release_root,
        expected_release_id=str(os.environ.get("ZF_RELEASE_ID") or "").strip(),
        expected_manifest_digest=str(
            os.environ.get("ZF_RELEASE_MANIFEST_DIGEST") or ""
        ).strip(),
        expected_source_digest=str(
            os.environ.get("ZF_RELEASE_SOURCE_DIGEST") or ""
        ).strip(),
        expected_runtime_digest=str(
            os.environ.get("ZF_RUNTIME_DIGEST") or ""
        ).strip(),
    )


def load_runtime_registry_authority(
    root: str | Path | None = None,
) -> SealedRegistryAuthority:
    """Load one immutable registry snapshot for a generation operation."""

    managed = _managed_release_registry_authority()
    if managed is not None:
        return managed
    compliance_root = _compliance_root(root)
    path = _registry_path(compliance_root)
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SealedComplianceError("COMPLIANCE_SOURCE_REGISTRY_UNAVAILABLE") from exc
    sha256 = hashlib.sha256(raw).hexdigest()
    projection = {
        "schema_version": "source-compliance-registry-authority-v1",
        "source_kind": "explicit_source_registry",
        "release_id": None,
        "manifest_digest": None,
        "source_digest": None,
        "runtime_digest": None,
        "registry_path": str(path),
        "registry_relative_path": _REGISTRY_FILENAME,
        "registry_sha256": sha256,
        "registry_size": len(raw),
        "registry_mode": None,
        "authority_digest": hashlib.sha256(raw).hexdigest(),
    }
    return SealedRegistryAuthority(raw=raw, path=path, projection=projection)


def resolve_runtime_registry_snapshot(
    root: str | Path | None = None,
    *,
    official_registry_bytes: bytes | None = None,
    official_registry_path: str | Path | None = None,
) -> tuple[bytes, Path]:
    """Resolve registry bytes without allowing a managed-runtime downgrade."""

    managed = _managed_release_registry_authority()
    if managed is not None:
        if official_registry_bytes is not None and bytes(
            official_registry_bytes
        ) != bytes(managed.raw):
            raise SealedComplianceError("SEALED_COMPLIANCE_REGISTRY_BYTES_MISMATCH")
        if official_registry_path is not None and Path(
            official_registry_path
        ) != managed.path:
            raise SealedComplianceError("SEALED_COMPLIANCE_REGISTRY_PATH_MISMATCH")
        return bytes(managed.raw), managed.path
    if official_registry_bytes is not None:
        return bytes(official_registry_bytes), Path(
            official_registry_path
            if official_registry_path is not None
            else _registry_path(_compliance_root(root))
        )
    authority = load_runtime_registry_authority(root)
    return bytes(authority.raw), authority.path


def _canonical_standard_code(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(value or "").strip().upper()).strip("_")


def _source_files(root: Path) -> list[Path]:
    files = [
        p
        for p in root.glob("*_compliance.json")
        if p.is_file() and not p.name.startswith("_")
    ]
    registry = _registry_path(root)
    if registry.is_file():
        files.append(registry)
    return sorted(files, key=lambda p: p.name)


def _clause_source_files(root: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in root.glob("*_compliance.json")
            if path.is_file() and not path.is_symlink() and not path.name.startswith("_")
        ],
        key=lambda path: path.name,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_regular_json_snapshot(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return {}, ""
    try:
        before = os.fstat(descriptor)
        if (
            not __import__("stat").S_ISREG(before.st_mode)
            or before.st_size < 0
            or before.st_size > _MAX_COMPLIANCE_JSON_BYTES
        ):
            return {}, ""
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            if sum(len(value) for value in chunks) > _MAX_COMPLIANCE_JSON_BYTES:
                return {}, ""
        after = os.fstat(descriptor)
    except OSError:
        return {}, ""
    finally:
        os.close(descriptor)
    try:
        current = path.lstat()
    except OSError:
        return {}, ""
    if (
        path.is_symlink()
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        return {}, ""
    raw = b"".join(chunks)
    digest = hashlib.sha256(raw).hexdigest()
    expected = str(expected_sha256 or "").strip().lower()
    if expected and digest != expected:
        return {}, ""
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError):
        return {}, ""
    return (value if isinstance(value, dict) else {}), digest


def _source_fingerprint(
    root: Path,
    *,
    registry_path: Path | None = None,
    registry_bytes: bytes | None = None,
    clause_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if clause_rows is not None:
        out.extend(dict(row) for row in clause_rows)
    else:
        for path in _clause_source_files(root):
            try:
                source_info = path.lstat()
            except OSError:
                continue
            if (
                path.is_symlink()
                or not stat.S_ISREG(source_info.st_mode)
                or source_info.st_size < 0
            ):
                continue
            if source_info.st_size > _MAX_COMPLIANCE_JSON_BYTES:
                # Keep a cheap cache-invalidating witness without opening or
                # hashing attacker-controlled oversized clause bytes.
                out.append(
                    {
                        "name": path.name,
                        "size": int(source_info.st_size),
                        "state": "oversized",
                    }
                )
                continue
            payload, digest = _read_regular_json_snapshot(path)
            if not payload or not digest:
                continue
            out.append(
                {
                    "name": path.name,
                    "size": int(source_info.st_size),
                    "sha256": digest,
                }
            )
    if registry_path is not None and registry_bytes is not None:
        out.append(
            {
                "name": _REGISTRY_FILENAME,
                "size": len(registry_bytes),
                "sha256": hashlib.sha256(registry_bytes).hexdigest(),
            }
        )
    return out


def _load_json_file(path: str, content_sha256: str) -> dict[str, Any]:
    """Load JSON bytes without trusting a separately patched existence check.

    ``content_sha256`` is intentionally retained in the call contract so
    callers prove which bytes they meant to read.  The payload itself is not
    cached: test isolation and live file replacement must never turn a
    transient ``Path.exists`` result into a process-lifetime empty registry.
    """
    expected = str(content_sha256 or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        return {}
    payload, _digest = _read_regular_json_snapshot(
        Path(path),
        expected_sha256=expected,
    )
    return payload


def _extract_entry_from_payload(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    standard_code = _norm_text(meta.get("standard_code")) or _norm_text(path.stem.replace("_compliance", "")).upper()
    code_key, code_year = _parse_standard_key_year(standard_code)
    domain_tags = _coerce_domains(meta.get("domain_tags") or meta.get("domain_tag"))
    if not domain_tags:
        # Fallback to sample from nodes.
        for n in (payload.get("nodes") or [])[:120]:
            if not isinstance(n, dict):
                continue
            domain_tags.extend(_coerce_domains(n.get("domain_tag")))
            if domain_tags:
                break
    if not domain_tags:
        domain_tags = ["通用工程"]
    source_name = _norm_text(meta.get("source_name")) or path.name
    official_source = _norm_text(meta.get("official_source")) or _norm_text(meta.get("official_url"))
    effective_status = _norm_text(meta.get("effective_status")) or _norm_text(meta.get("status"))
    current_version = _norm_text(meta.get("current_version")) or standard_code
    prefix_tag = _norm_text(meta.get("prefix_tag")) or _norm_text(standard_code.split("_")[0])
    search_text = " ".join(
        [
            standard_code,
            code_key,
            source_name,
            " ".join(domain_tags),
            prefix_tag,
        ]
    )
    return {
        "path": str(path),
        "filename": path.name,
        "standard_code": standard_code,
        "code_key": code_key,
        "code_year": int(code_year),
        "prefix_tag": prefix_tag,
        "source_name": source_name,
        "official_source": official_source,
        "effective_status": effective_status,
        "current_version": current_version,
        "priority": _norm_text(meta.get("priority")),
        "conflicts": meta.get("conflicts") if isinstance(meta.get("conflicts"), list) else [],
        "domain_tags": domain_tags,
        "generated_at": _norm_text(meta.get("generated_at")),
        "mandatory_count": int(stats.get("mandatory_count") or 0),
        "parameter_count": int(stats.get("parameter_count") or 0),
        "search_text": search_text,
        # Unless an ingested source explicitly declares otherwise, the catalog
        # decides recency by standard key/year below.  Starting at False would
        # make every legacy source ineligible before that comparison runs.
        "latest": bool(meta.get("latest", True)),
        "metadata_only": False,
        "clause_source_standard_code": standard_code,
        "clause_source_name": _norm_text(meta.get("source_name")),
        "clause_source_official_source": _norm_text(
            meta.get("official_source") or meta.get("official_url")
        ),
        "clause_source_current_version": _norm_text(meta.get("current_version")),
        "clause_source_document_sha256": _norm_text(
            meta.get("source_document_sha256")
        ).lower(),
    }


def _official_registry_rows(
    payload: Any,
    *,
    path: Path,
) -> list[dict[str, Any]]:
    rows = payload.get("standards") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        code = _norm_text(raw.get("standard_code"))
        if not code:
            continue
        code_key, code_year = _parse_standard_key_year(code)
        domains = _coerce_domains(raw.get("domain_tags") or raw.get("domain_tag")) or ["通用工程"]
        rec = {
            "path": str(path),
            "filename": path.name,
            "standard_code": code,
            "code_key": code_key,
            "code_year": int(code_year),
            "prefix_tag": _norm_text(raw.get("prefix_tag")) or code_key.split("_")[0],
            "source_name": _norm_text(raw.get("source_name") or raw.get("standard_name")),
            "official_source": _norm_text(raw.get("official_source")),
            "official_document_url": _norm_text(raw.get("official_document_url")),
            "official_content_sha256": _norm_text(
                raw.get("official_content_sha256")
            ).lower(),
            "official_identity_without_cover": (
                raw.get("official_identity_without_cover") is True
            ),
            "effective_status": _norm_text(raw.get("effective_status")),
            "current_version": _norm_text(raw.get("current_version")) or code,
            "priority": _norm_text(raw.get("priority")),
            "conflicts": raw.get("conflicts") if isinstance(raw.get("conflicts"), list) else [],
            "domain_tags": domains,
            "generated_at": _norm_text(raw.get("verified_at") or raw.get("generated_at")),
            "mandatory_count": 0,
            "parameter_count": 0,
            "search_text": " ".join(
                [
                    code,
                    code_key,
                    _norm_text(raw.get("source_name") or raw.get("standard_name")),
                    " ".join(domains),
                ]
            ),
            "latest": bool(raw.get("latest", True)),
            "metadata_only": True,
            "verification_note": _norm_text(raw.get("verification_note")),
            "superseded_clauses": _string_list(raw.get("superseded_clauses")),
        }
        out.append(rec)
    return out


def _parse_official_registry_bytes(
    raw: bytes,
    *,
    path: str | Path,
) -> list[dict[str, Any]]:
    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeError, ValueError):
        return []
    return _official_registry_rows(payload, path=Path(path))


def _load_official_registry(root: Path) -> list[dict[str, Any]]:
    path = _registry_path(root)
    if not path.is_file():
        return []
    try:
        content_sha256 = _file_sha256(path)
    except OSError:
        content_sha256 = ""
    payload = _load_json_file(str(path), content_sha256)
    return _official_registry_rows(payload, path=path)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_values = value
    elif value is None:
        raw_values = []
    else:
        raw_values = [value]
    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        text = _norm_text(raw)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def build_compliance_catalog(
    root: str | Path | None = None,
    *,
    official_registry_bytes: bytes | None = None,
    official_registry_path: str | Path | None = None,
    write_catalog: bool | None = None,
) -> dict[str, Any]:
    """
    Build compact catalog for fast pre-filter retrieval.
    """
    rt = _compliance_root(root)
    if not rt.is_dir():
        return {
            "version": 3,
            "root": ".",
            "count": 0,
            "verified_count": 0,
            "source_fingerprint": [],
            "entries": [],
        }
    files = _clause_source_files(rt)
    try:
        registry_raw, registry_source_path = resolve_runtime_registry_snapshot(
            rt,
            official_registry_bytes=official_registry_bytes,
            official_registry_path=official_registry_path,
        )
    except SealedComplianceError:
        if str(os.environ.get("ZF_RELEASE_MANAGED") or "") == "1":
            raise
        registry_raw = b'{"standards":[]}'
        registry_source_path = _registry_path(rt)
    registry_entries = _parse_official_registry_bytes(
        registry_raw,
        path=registry_source_path,
    )
    registry_by_code = build_standard_registry_map(registry_entries)
    trusted_registry_entries = [
        {
            **{key: value for key, value in row.items() if not key.startswith("_")},
            "path": _REGISTRY_FILENAME,
            "filename": _REGISTRY_FILENAME,
            "official_registry_verified": True,
        }
        for row in registry_by_code.values()
        if row.get("_registry_ambiguous") is not True
        and is_verified_standard_metadata(row)
    ]
    entries: list[dict[str, Any]] = []
    clause_fingerprint: list[dict[str, Any]] = []
    source_warnings: list[str] = []
    for p in files:
        try:
            source_info = p.lstat()
        except OSError:
            source_warnings.append(f"compliance_source_untrusted:{p.name}")
            continue
        if source_info.st_size > _MAX_COMPLIANCE_JSON_BYTES:
            source_warnings.append(f"compliance_source_oversized:{p.name}")
            clause_fingerprint.append(
                {
                    "name": p.name,
                    "size": int(source_info.st_size),
                    "state": "oversized",
                }
            )
            continue
        payload, content_sha256 = _read_regular_json_snapshot(p)
        if not payload or not content_sha256:
            source_warnings.append(f"compliance_source_untrusted:{p.name}")
            continue
        clause_fingerprint.append(
            {
                "name": p.name,
                "size": int(source_info.st_size),
                "sha256": content_sha256,
            }
        )
        entry = _extract_entry_from_payload(p, payload)
        entry["clause_source_sha256"] = content_sha256
        entry["path"] = p.name
        entry["clause_source_path"] = p.name
        registry_meta = registry_by_code.get(
            _canonical_standard_code(entry.get("standard_code"))
        )
        declared_name = _norm_text(entry.get("clause_source_name"))
        declared_official_source = _norm_text(
            entry.get("clause_source_official_source")
        )
        declared_version = _canonical_standard_code(
            entry.get("clause_source_current_version")
        )
        declared_document_sha256 = _norm_text(
            entry.get("clause_source_document_sha256")
        ).lower()
        registry_names = {
            _norm_text((registry_meta or {}).get("source_name")),
            _norm_text((registry_meta or {}).get("standard_name")),
        }
        registry_sources = {
            _norm_text((registry_meta or {}).get("official_source")),
            _norm_text((registry_meta or {}).get("official_document_url")),
        }
        registry_versions = {
            _canonical_standard_code((registry_meta or {}).get("standard_code")),
            _canonical_standard_code((registry_meta or {}).get("current_version")),
        }
        declared_identity_matches = bool(
            (not declared_name or declared_name in registry_names)
            and (
                not declared_official_source
                or declared_official_source in registry_sources
            )
            and (not declared_version or declared_version in registry_versions)
        )
        registry_content_sha256 = _norm_text(
            (registry_meta or {}).get("official_content_sha256")
        ).lower()
        content_pin_matches = bool(
            re.fullmatch(r"[0-9a-f]{64}", declared_document_sha256)
            and declared_document_sha256 == registry_content_sha256
        )
        if (
            isinstance(registry_meta, dict)
            and registry_meta.get("_registry_ambiguous") is not True
            and is_verified_standard_metadata(registry_meta)
            and declared_identity_matches
        ):
            # An official registry record may verify the version/source of a
            # locally ingested text without pretending that registry metadata
            # contains clause bytes.
            for key in (
                "source_name",
                "official_source",
                "official_document_url",
                "official_content_sha256",
                "official_identity_without_cover",
                "effective_status",
                "current_version",
                "priority",
                "conflicts",
                "domain_tags",
                "verification_note",
                "superseded_clauses",
            ):
                value = registry_meta.get(key)
                if value not in (None, "", []):
                    entry[key] = value
            entry["official_registry_verified"] = True
            entry["clause_source_content_pin_matches"] = content_pin_matches
            # A mutable derived JSON file cannot prove that its clauses came
            # from the pinned PDF merely by repeating that PDF's hash.  Until
            # an independently verified ingest/extractor/page-anchor receipt
            # binds both byte sets, it is never formal clause evidence.
            entry["clause_source_authoritative"] = False
        else:
            entry["official_registry_verified"] = False
            entry["clause_source_authoritative"] = False
        entries.append(entry)

    # Keep the sealed metadata projection even when a mutable clause cache uses
    # the same standard code.  The two layers have different trust semantics:
    # official metadata remains verified, while clause text remains explicitly
    # non-authoritative until an independent extractor receipt exists.
    entries.extend(trusted_registry_entries)

    local_latest_by_key: dict[str, tuple[int, str]] = {}
    for entry in entries:
        if (
            entry.get("metadata_only") is True
            or entry.get("official_registry_verified") is True
        ):
            continue
        key = str(entry.get("code_key") or "")
        candidate = (
            int(entry.get("code_year") or 0),
            str(entry.get("generated_at") or ""),
        )
        if candidate > local_latest_by_key.get(key, (0, "")):
            local_latest_by_key[key] = candidate
    for e in entries:
        if (
            e.get("metadata_only") is True
            or e.get("official_registry_verified") is True
        ):
            e["latest"] = bool(e.get("latest", True))
        else:
            e["latest"] = (
                int(e.get("code_year") or 0),
                str(e.get("generated_at") or ""),
            ) == local_latest_by_key.get(str(e.get("code_key") or ""))
        e["verified"] = bool(
            e.get("metadata_only") is True
            or e.get("clause_source_authoritative") is True
        ) and is_verified_standard_metadata(e)

    out = {
        "version": 3,
        # A persisted catalog is a portable projection.  The caller already
        # supplies the catalog root, so recording a checkout-specific absolute
        # path here only makes identical source bytes differ across machines.
        "root": ".",
        "count": len(entries),
        "verified_count": len([e for e in entries if bool(e.get("verified"))]),
        # Derive the projection timestamp from source metadata rather than the
        # wall clock so a clean rebuild is deterministic in every checkout.
        "generated_at": max(
            (str(entry.get("generated_at") or "") for entry in entries),
            default="",
        ),
        "source_fingerprint": _source_fingerprint(
            rt,
            registry_path=registry_source_path,
            registry_bytes=registry_raw,
            clause_rows=clause_fingerprint,
        ),
        "official_registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
        "warnings": sorted(set(source_warnings)),
        "entries": entries,
    }
    if (
        write_catalog is False
        or str(os.environ.get("ZF_RELEASE_MANAGED") or "") == "1"
    ):
        return out
    catalog_path = _catalog_path(rt)
    # Explicit rebuild requests are intentionally idempotent.  A catalog is a
    # versioned projection of its source bytes, not a heartbeat: rewriting it
    # only to refresh ``generated_at`` would dirty the repository after tests
    # or health checks and incorrectly turn static readiness into NO-GO.
    try:
        existing = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        existing = {}
    stable_keys = (
        "version",
        "root",
        "count",
        "verified_count",
        "source_fingerprint",
        "official_registry_sha256",
        "warnings",
        "entries",
    )
    if isinstance(existing, dict) and all(existing.get(key) == out.get(key) for key in stable_keys):
        return existing

    temporary_path = catalog_path.with_name(f".{catalog_path.name}.tmp-{os.getpid()}")
    temporary_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary_path.replace(catalog_path)
    return out


@lru_cache(maxsize=8)
def _load_catalog(root_str: str, catalog_mtime_ns: int) -> dict[str, Any]:
    p = _catalog_path(Path(root_str))
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def _load_or_build_catalog(
    root: Path,
    *,
    release_managed: bool = False,
    official_registry_bytes: bytes | None = None,
    official_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    effective_managed = release_managed or str(
        os.environ.get("ZF_RELEASE_MANAGED") or ""
    ) == "1"
    if effective_managed or official_registry_bytes is not None:
        return build_compliance_catalog(
            root,
            official_registry_bytes=official_registry_bytes,
            official_registry_path=official_registry_path,
            write_catalog=False,
        )
    p = _catalog_path(root)
    if not p.exists():
        return build_compliance_catalog(root)
    try:
        mtime_ns = int(p.stat().st_mtime_ns)
    except OSError:
        mtime_ns = 0
    cat = _load_catalog(str(root), mtime_ns)
    if (
        not isinstance(cat, dict)
        or cat.get("version") != 3
        or not isinstance(cat.get("entries"), list)
    ):
        return build_compliance_catalog(root)
    try:
        authority = load_runtime_registry_authority(root)
    except SealedComplianceError:
        return build_compliance_catalog(root)
    expected_fingerprint = _source_fingerprint(
        root,
        registry_path=authority.path,
        registry_bytes=authority.raw,
    )
    if cat.get("source_fingerprint") != expected_fingerprint:
        return build_compliance_catalog(root)
    if cat.get("official_registry_sha256") != hashlib.sha256(
        authority.raw
    ).hexdigest():
        return build_compliance_catalog(root)
    return cat


def list_verified_standard_metadata(
    *,
    domain_tags: list[str] | None = None,
    root: str | Path | None = None,
    official_registry_bytes: bytes | None = None,
    official_registry_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return metadata directly projected from the captured registry bytes.

    Clause/catalog rows are intentionally excluded.  A mutable clause source
    may contribute searchable text, but it must never become the authority for
    a standard's official name, version, status, URL, or content pin.
    """
    rt = _compliance_root(root)
    try:
        registry_raw, registry_source_path = resolve_runtime_registry_snapshot(
            rt,
            official_registry_bytes=official_registry_bytes,
            official_registry_path=official_registry_path,
        )
    except SealedComplianceError:
        return []
    allowed_domains = [str(x).strip() for x in (domain_tags or []) if str(x).strip()]
    candidates = []
    for raw in _parse_official_registry_bytes(
        registry_raw,
        path=registry_source_path,
    ):
        if not is_verified_standard_metadata(raw):
            continue
        if allowed_domains and not _domains_overlap(
            raw.get("domain_tags") or [],
            allowed_domains,
        ):
            continue
        candidates.append(
            {
                **dict(raw),
                "verified": True,
                "official_registry_verified": True,
            }
        )
    chosen = {
        code: row
        for code, row in build_standard_registry_map(candidates).items()
        if row.get("_registry_ambiguous") is not True
        and row.get("verified") is True
        and row.get("official_registry_verified") is True
        and is_verified_standard_metadata(row)
    }
    return sorted(chosen.values(), key=lambda row: str(row.get("standard_code") or ""))


def get_compliance_registry_status(
    root: str | Path | None = None,
    *,
    official_registry_bytes: bytes | None = None,
    official_registry_path: str | Path | None = None,
) -> dict[str, Any]:
    rt = _compliance_root(root)
    clause_root_exists = rt.is_dir()
    release_managed = str(os.environ.get("ZF_RELEASE_MANAGED") or "") == "1"
    try:
        catalog = _load_or_build_catalog(
            rt,
            release_managed=release_managed,
            official_registry_bytes=official_registry_bytes,
            official_registry_path=official_registry_path,
        )
    except SealedComplianceError as exc:
        return {
            "root": str(rt),
            "exists": clause_root_exists,
            "ready": False,
            "official_registry_ready": False,
            "clause_catalog_ready": False,
            "source_count": len(_clause_source_files(rt)) if clause_root_exists else 0,
            "catalog_count": 0,
            "verified_count": 0,
            "warnings": [exc.code],
        }
    verified_count = len(
        list_verified_standard_metadata(
            root=root,
            official_registry_bytes=official_registry_bytes,
            official_registry_path=official_registry_path,
        )
    )
    warnings: list[str] = []
    warnings.extend(
        str(value)
        for value in (catalog.get("warnings") or [])
        if str(value).strip()
    )
    if not clause_root_exists:
        warnings.append("compliance_clause_root_missing")
    if verified_count <= 0:
        warnings.append("no_verified_standard_metadata")
    return {
        "root": str(rt),
        "exists": clause_root_exists,
        "ready": verified_count > 0,
        "official_registry_ready": verified_count > 0,
        "clause_catalog_ready": clause_root_exists,
        "source_count": len(_source_files(rt)) if clause_root_exists else 0,
        "catalog_count": int(catalog.get("count") or 0),
        "verified_count": verified_count,
        "warnings": warnings,
    }


def _entry_prefilter_score(entry: dict[str, Any], tokens: list[str], *, allowed_domains: list[str]) -> float:
    text = str(entry.get("search_text") or "")
    score = 0.0
    for t in tokens:
        if t and t in text:
            score += 1.0
    if entry.get("latest"):
        score += 0.6
    if allowed_domains and _domains_overlap(entry.get("domain_tags") or [], allowed_domains):
        score += 0.8
    return score


def _node_score(text: str, tokens: list[str]) -> float:
    score = 0.0
    for t in tokens:
        if t and t in text:
            score += 1.0
    if re.search(r"\d", text):
        score += 0.2
    return score


def query_compliance(
    query: str,
    *,
    domain_tags: list[str] | None = None,
    top_k: int = 8,
    prefer_latest: bool = True,
    verified_only: bool = False,
    root: str | Path | None = None,
    official_registry_bytes: bytes | None = None,
    official_registry_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Fast, domain-filtered compliance retrieval with latest-version preference.
    """
    tokens = _tokenize(query)
    if not tokens:
        return []
    rt = _compliance_root(root)
    if not rt.is_dir():
        return []
    allowed_domains = [str(x).strip() for x in (domain_tags or []) if str(x).strip()]
    release_managed = str(os.environ.get("ZF_RELEASE_MANAGED") or "") == "1"
    try:
        if verified_only and official_registry_bytes is None:
            authority = load_runtime_registry_authority(rt)
            official_registry_bytes = authority.raw
            official_registry_path = authority.path
        catalog = _load_or_build_catalog(
            rt,
            release_managed=release_managed,
            official_registry_bytes=official_registry_bytes,
            official_registry_path=official_registry_path,
        )
    except SealedComplianceError:
        return []
    entries = catalog.get("entries") if isinstance(catalog.get("entries"), list) else []
    if not entries:
        return []

    prefiltered: list[tuple[float, dict[str, Any]]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if e.get("metadata_only") is not False:
            continue
        if verified_only and (
            e.get("verified") is not True
            or e.get("official_registry_verified") is not True
            or e.get("clause_source_authoritative") is not True
            or not is_verified_standard_metadata(e)
        ):
            continue
        e_domains = e.get("domain_tags") or []
        if allowed_domains and e_domains and (not _domains_overlap(e_domains, allowed_domains)):
            continue
        sc = _entry_prefilter_score(e, tokens, allowed_domains=allowed_domains)
        if sc <= 0 and not (prefer_latest and e.get("latest")):
            continue
        prefiltered.append((sc, e))
    prefiltered.sort(key=lambda x: x[0], reverse=True)
    # limit deep file reads
    candidates = [x[1] for x in prefiltered[:20]]

    scored: list[tuple[float, dict[str, Any]]] = []
    for e in candidates:
        raw_path = Path(str(e.get("path") or ""))
        p = raw_path if raw_path.is_absolute() else rt / raw_path
        expected_content_sha256 = str(
            e.get("clause_source_sha256") or ""
        ).strip().lower()
        try:
            resolved_root = rt.resolve(strict=True)
            resolved_path = p.resolve(strict=True)
        except OSError:
            continue
        if (
            not p.is_file()
            or p.is_symlink()
            or resolved_path.parent != resolved_root
            or re.fullmatch(r"[0-9a-f]{64}", expected_content_sha256) is None
        ):
            continue
        payload, current_sha256 = _read_regular_json_snapshot(
            p,
            expected_sha256=expected_content_sha256,
        )
        if not payload or current_sha256 != expected_content_sha256:
            continue
        if not isinstance(payload, dict):
            continue
        trust_projection = {
            "metadata_only": False,
            "verified": e.get("verified") is True,
            "official_registry_verified": (
                e.get("official_registry_verified") is True
            ),
            "clause_source_authoritative": (
                e.get("clause_source_authoritative") is True
            ),
            "clause_source_content_pin_matches": (
                e.get("clause_source_content_pin_matches") is True
            ),
            "clause_source_sha256": expected_content_sha256,
            "clause_source_document_sha256": str(
                e.get("clause_source_document_sha256") or ""
            ),
        }
        latest_bonus = 0.5 if (prefer_latest and e.get("latest")) else (0.0 if not prefer_latest else -0.1)
        domain_bonus = 0.4 if (allowed_domains and _domains_overlap(e.get("domain_tags") or [], allowed_domains)) else 0.0

        for n in (payload.get("nodes") or [])[:2400]:
            if not isinstance(n, dict):
                continue
            text = _norm_text(n.get("text"))
            if not text:
                continue
            sc = _node_score(text, tokens)
            if sc <= 0:
                continue
            mandatory_level = _norm_text(n.get("mandatory_level"))
            if mandatory_level == "禁止类":
                sc += 0.3
            sc += latest_bonus + domain_bonus
            scored.append(
                (
                    sc,
                    {
                        "type": "clause",
                        "standard_code": e.get("standard_code"),
                        "code_year": e.get("code_year"),
                        "latest": bool(e.get("latest")),
                        "domain_tags": e.get("domain_tags") or [],
                        "source_name": e.get("source_name"),
                        "official_source": e.get("official_source"),
                        "effective_status": e.get("effective_status"),
                        "current_version": e.get("current_version"),
                        "priority": e.get("priority"),
                        "conflicts": e.get("conflicts") or [],
                        **trust_projection,
                        "clause_no": _norm_text(n.get("clause_no")),
                        "mandatory_level": mandatory_level,
                        "text": text[:320],
                        "locator": f"{p.name}#{_norm_text(n.get('node_id'))}",
                        "source_file": str(p),
                    },
                )
            )

        for pm in (payload.get("parameters") or [])[:2400]:
            if not isinstance(pm, dict):
                continue
            ctx = _norm_text(pm.get("context"))
            name = _norm_text(pm.get("parameter_name"))
            value = _norm_text(pm.get("value"))
            unit = _norm_text(pm.get("unit"))
            txt = f"{name} {value} {unit} {ctx}"
            sc = _node_score(txt, tokens)
            if sc <= 0:
                continue
            sc += 0.2 + latest_bonus + domain_bonus
            scored.append(
                (
                    sc,
                    {
                        "type": "parameter",
                        "standard_code": e.get("standard_code"),
                        "code_year": e.get("code_year"),
                        "latest": bool(e.get("latest")),
                        "domain_tags": e.get("domain_tags") or [],
                        "source_name": e.get("source_name"),
                        "official_source": e.get("official_source"),
                        "effective_status": e.get("effective_status"),
                        "current_version": e.get("current_version"),
                        "priority": e.get("priority"),
                        "conflicts": e.get("conflicts") or [],
                        **trust_projection,
                        "parameter_name": name,
                        "value": value,
                        "unit": unit,
                        "text": txt[:320],
                        "locator": f"{p.name}#{_norm_text(pm.get('parameter_id'))}",
                        "source_file": str(p),
                    },
                )
            )

    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    seen = set()
    for sc, item in scored:
        loc = str(item.get("locator") or "")
        if not loc or loc in seen:
            continue
        seen.add(loc)
        rec = dict(item)
        rec["score"] = round(float(sc), 4)
        out.append(rec)
        if len(out) >= max(1, int(top_k)):
            break
    return out
