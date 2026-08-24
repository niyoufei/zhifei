from __future__ import annotations

"""Integrity-bound chapter checkpoints for long-running Autoplan jobs.

The store is deliberately local, lazy and fail-closed:

* importing this module creates no directories;
* a checkpoint is reusable only when its generation binding still matches;
* API keys, tokens and other credential-shaped fields are removed recursively;
* every file and every saved chapter carries a SHA-256 integrity digest; and
* writes use an atomic replace so a process interruption cannot expose a
  half-written chapter as reusable work.
"""

import hashlib
import json
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Mapping


CHECKPOINT_DIR = Path(
    os.environ.get(
        "ZF_AUTOPLAN_CHECKPOINT_DIR",
        "backend/data/autoplan/checkpoints",
    )
)
SCHEMA_VERSION = "generation-checkpoint-v1"
_LOCK = threading.RLock()
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_SECRET_FRAGMENTS = ("api_key", "apikey", "token", "secret", "password", "credential")


class CheckpointIntegrityError(RuntimeError):
    """Raised when persisted checkpoint bytes cannot be trusted."""


def _json_safe(value: Any, *, key: str = "") -> Any:
    lowered = str(key or "").lower()
    if any(fragment in lowered for fragment in _SECRET_FRAGMENTS):
        return "[REDACTED]"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(k): _json_safe(v, key=str(k))
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _validate_name(value: Any, *, field: str) -> str:
    name = str(value or "").strip()
    if not _SAFE_NAME.fullmatch(name):
        raise ValueError(f"invalid checkpoint {field}")
    return name


def _checkpoint_path(
    namespace: Any,
    scope: Any,
    *,
    root: Path | str | None = None,
) -> Path:
    safe_namespace = _validate_name(namespace, field="namespace")
    safe_scope = _validate_name(scope, field="scope")
    base = Path(root) if root is not None else CHECKPOINT_DIR
    return base / safe_namespace / f"{safe_scope}.json"


def build_generation_binding(
    *,
    topic: Any,
    project_id: Any,
    project_type: Any,
    outline: Any,
    style: Any,
    chapter_pages: Any,
    variant_id: Any,
    project_fact_digest: Any,
    requirement_plan_digest: Any,
    provider_routes: Any,
) -> dict[str, Any]:
    """Build the immutable metadata identity for one generation attempt."""

    safe_routes: list[dict[str, Any]] = []
    for route in provider_routes if isinstance(provider_routes, list) else []:
        if not isinstance(route, Mapping):
            continue
        safe_routes.append(
            {
                "slot": str(route.get("slot") or "").strip() or None,
                "provider": str(route.get("provider") or "").strip().lower() or None,
                "model": str(route.get("model") or "").strip() or None,
            }
        )
    core = {
        "schema_version": SCHEMA_VERSION,
        "topic": str(topic or "").strip(),
        "project_id": str(project_id or "").strip() or None,
        "project_type": str(project_type or "").strip() or None,
        "outline": [str(item or "").strip() for item in (outline or [])],
        "style": _json_safe(style if isinstance(style, Mapping) else {}),
        "chapter_pages": _json_safe(chapter_pages if isinstance(chapter_pages, Mapping) else {}),
        "variant_id": str(variant_id or "").strip() or None,
        "project_fact_digest": str(project_fact_digest or "").strip() or None,
        "requirement_plan_digest": str(requirement_plan_digest or "").strip() or None,
        "provider_routes": safe_routes,
    }
    return {**core, "binding_digest": _digest(core)}


def _read_verified(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CheckpointIntegrityError("checkpoint_json_invalid") from exc
    if not isinstance(record, dict):
        raise CheckpointIntegrityError("checkpoint_record_invalid")
    claimed = str(record.get("integrity_digest") or "").strip()
    core = {k: v for k, v in record.items() if k != "integrity_digest"}
    if not claimed or claimed != _digest(core):
        raise CheckpointIntegrityError("checkpoint_integrity_mismatch")
    if str(record.get("schema_version") or "") != SCHEMA_VERSION:
        raise CheckpointIntegrityError("checkpoint_schema_mismatch")
    return record


def _empty_record(binding: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "binding": _json_safe(dict(binding)),
        "binding_digest": str(binding.get("binding_digest") or ""),
        "status": "partial",
        "created_at": time.time(),
        "updated_at": time.time(),
        "sections": {},
    }


def _write_atomic(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    core = {k: _json_safe(v, key=str(k)) for k, v in record.items() if k != "integrity_digest"}
    payload = {**core, "integrity_digest": _digest(core)}
    temp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    finally:
        temp.unlink(missing_ok=True)


def load_generation_checkpoint(
    *,
    namespace: Any,
    scope: Any,
    binding: Mapping[str, Any],
    root: Path | str | None = None,
) -> dict[str, Any] | None:
    path = _checkpoint_path(namespace, scope, root=root)
    with _LOCK:
        record = _read_verified(path)
    if record is None:
        return None
    expected = str(binding.get("binding_digest") or "").strip()
    if not expected or str(record.get("binding_digest") or "") != expected:
        return None
    return record


def load_section_checkpoint(
    *,
    namespace: Any,
    scope: Any,
    binding: Mapping[str, Any],
    chapter_index: int,
    chapter_title: str,
    root: Path | str | None = None,
) -> dict[str, Any] | None:
    record = load_generation_checkpoint(
        namespace=namespace,
        scope=scope,
        binding=binding,
        root=root,
    )
    if not record:
        return None
    section = (record.get("sections") or {}).get(str(int(chapter_index)))
    if not isinstance(section, dict):
        return None
    stored_index = section.get("chapter_index")
    if stored_index is None or int(stored_index) != int(chapter_index):
        raise CheckpointIntegrityError("checkpoint_section_index_mismatch")
    if str(section.get("chapter_title") or "") != str(chapter_title or ""):
        return None
    claimed = str(section.get("section_digest") or "")
    core = {k: v for k, v in section.items() if k != "section_digest"}
    if not claimed or claimed != _digest(core):
        raise CheckpointIntegrityError("checkpoint_section_integrity_mismatch")
    result = section.get("result")
    return dict(result) if isinstance(result, dict) else None


def save_section_checkpoint(
    *,
    namespace: Any,
    scope: Any,
    binding: Mapping[str, Any],
    chapter_index: int,
    chapter_title: str,
    result: Mapping[str, Any],
    root: Path | str | None = None,
) -> dict[str, Any]:
    path = _checkpoint_path(namespace, scope, root=root)
    with _LOCK:
        record = _read_verified(path) if path.exists() else None
        expected = str(binding.get("binding_digest") or "").strip()
        if not expected:
            raise ValueError("checkpoint binding digest is required")
        if record is None or str(record.get("binding_digest") or "") != expected:
            record = _empty_record(binding)
        section_core = {
            "chapter_index": int(chapter_index),
            "chapter_title": str(chapter_title or ""),
            "saved_at": time.time(),
            "result": _json_safe(dict(result)),
        }
        section = {**section_core, "section_digest": _digest(section_core)}
        sections = dict(record.get("sections") or {})
        sections[str(int(chapter_index))] = section
        record["sections"] = sections
        record["status"] = "partial"
        record["updated_at"] = time.time()
        _write_atomic(path, record)
    return checkpoint_summary(record)


def finalize_generation_checkpoint(
    *,
    namespace: Any,
    scope: Any,
    binding: Mapping[str, Any],
    status: str = "complete",
    root: Path | str | None = None,
) -> dict[str, Any]:
    path = _checkpoint_path(namespace, scope, root=root)
    with _LOCK:
        record = _read_verified(path) if path.exists() else None
        expected = str(binding.get("binding_digest") or "").strip()
        if record is None or str(record.get("binding_digest") or "") != expected:
            record = _empty_record(binding)
        record["status"] = str(status or "complete")
        record["updated_at"] = time.time()
        _write_atomic(path, record)
    return checkpoint_summary(record)


def checkpoint_summary(record: Mapping[str, Any] | None) -> dict[str, Any]:
    data = record if isinstance(record, Mapping) else {}
    sections = data.get("sections") if isinstance(data.get("sections"), Mapping) else {}
    return {
        "schema_version": str(data.get("schema_version") or SCHEMA_VERSION),
        "binding_digest": str(data.get("binding_digest") or "") or None,
        "status": str(data.get("status") or "missing"),
        "saved_chapter_count": len(sections),
        "saved_chapter_indexes": sorted(int(x) for x in sections if str(x).isdigit()),
        "updated_at": data.get("updated_at"),
    }


def cleanup_checkpoint_namespace(
    namespace: Any,
    *,
    root: Path | str | None = None,
) -> bool:
    safe_namespace = _validate_name(namespace, field="namespace")
    base = Path(root) if root is not None else CHECKPOINT_DIR
    target = base / safe_namespace
    if not target.exists():
        return False
    with _LOCK:
        shutil.rmtree(target)
    return True
