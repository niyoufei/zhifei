from __future__ import annotations

"""Deterministic, provider-free rebuild of the formal delivery acceptance gate."""

import errno
import fcntl
import hashlib
import hmac
import json
import math
import os
import posixpath
import re
import secrets
import stat
import time
import uuid
import weakref
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from backend.zhifei_autoplan.boq_focus_policy import (
    MAX_BOQ_FOCUS_ITEMS,
    select_boq_focus_names,
)
from backend.zhifei_autoplan.boq_schedule import build_boq_wbs_cpm
from backend.zhifei_autoplan.compliance_policy import (
    audit_standard_citations,
    build_project_applicable_standards_manifest,
)
from backend.zhifei_autoplan.content_quality import (
    build_independent_content_review,
)
from backend.zhifei_autoplan.cross_index import (
    build_cross_index,
    validate_cross_index_contract,
)
from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.delivery_receipt import (
    canonical_delivery_receipt_digest,
)
from backend.zhifei_autoplan.docx_visual_quality import evaluate_page_quality
from backend.zhifei_autoplan.drawing_index import build_drawing_index
from backend.zhifei_autoplan.evidence import (
    build_ingest_evidence_set_receipt,
    resolve_trusted_ingest_record,
    validate_ingest_evidence_set_receipt,
)
from backend.zhifei_autoplan.formal_artifact_integrity import (
    FormalArtifactIntegrityError,
    validate_formal_ooxml_artifact,
)
from backend.zhifei_autoplan.missing_param_probe import probe_missing_parameters
from backend.zhifei_autoplan.project_fact_approval_audit import (
    ProjectFactApprovalAuditError,
    parse_project_fact_approval_audit,
    verify_project_fact_approval_event,
)
from backend.zhifei_autoplan.project_fact_approval_audit import (
    canonical_digest as approval_canonical_digest,
)
from backend.zhifei_autoplan.project_fact_approval_audit import (
    project_fact_value_digest as approval_value_digest,
)
from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger_from_inputs,
    validate_project_fact_ledger,
)
from backend.zhifei_autoplan.project_namespace import project_storage_key
from backend.zhifei_autoplan.project_parameter_evidence import (
    build_project_parameter_evidence,
    validate_project_parameter_evidence,
)
from backend.zhifei_autoplan.provider_admission import LAYER_NAMES
from backend.zhifei_autoplan.provider_admission import (
    canonical_digest as provider_admission_canonical_digest,
)
from backend.zhifei_autoplan.provider_admission import (
    decide_required_roles as decide_provider_required_roles,
)
from backend.zhifei_autoplan.provider_admission import (
    public_snapshot as provider_public_snapshot,
)
from backend.zhifei_autoplan.sealed_compliance import (
    SEALED_COMPLIANCE_ROOT_RELATIVE_PATH,
    SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH,
    SEALED_REGISTRY_AUTHORITY_SCHEMA,
    SealedComplianceError,
    sealed_official_registry_path,
    validate_registry_authority_projection,
)
from backend.zhifei_autoplan.standard_index import build_standard_index

SCHEMA_VERSION = "autoplan-no-model-acceptance-v2"
_SOURCE_INPUT_SCHEMA = "autoplan-source-input-v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
_JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_EXECUTION_ID_RE = _JOB_ID_RE
_RESERVED_RUN_IDS = frozenset({"latest", "current", "index", "lock"})
_LEGACY_V1_SCHEMA_VERSION = "autoplan-no-model-acceptance-v1"
_LEGACY_V1_TOP_LEVEL_FIELDS = frozenset(
    {
        "code_acceptance",
        "confirmation_checklist",
        "created_at",
        "cross_index",
        "decision",
        "drawing_index",
        "external_blockers",
        "formal_delivery_gate",
        "model_calls",
        "project_fact_ledger",
        "project_id",
        "project_parameter_evidence",
        "provider_probes",
        "receipt_digest",
        "release",
        "run_id",
        "schedule_derivation",
        "schema_version",
        "source_task",
        "standard_index",
        "tender_matrix",
        "tender_sources",
        "v7_drawing_ingest",
    }
)
_LEGACY_V1_RELEASE_FIELDS = frozenset(
    {
        "build_sha",
        "dirty",
        "jobs",
        "manifest_digest",
        "provider_admission",
        "release_id",
        "runtime_digest",
        "runtime_mode",
        "source_digest",
        "supervisor_status",
        "system_id",
    }
)
_MAX_JSON_BYTES = 64 * 1024 * 1024
_MAX_AUDIT_BYTES = 512 * 1024 * 1024
_MAX_EVIDENCE_BYTES = 2 * 1024 * 1024 * 1024
_DIRECTORY_FD_OPERATIONS_SUPPORTED = all(
    operation in os.supports_dir_fd
    for operation in (os.open, os.stat, os.mkdir, os.unlink, os.link, os.rename)
)
_RECEIPT_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema_version",
        "run_id",
        "generated_at",
        "project_id",
        "mode",
        "decision",
        "model_calls",
        "provider_probes",
        "runtime_state",
        "provider_admission",
        "provenance_trust",
        "cryptographic_attestation",
        "release",
        "inputs",
        "formal_source_eligibility",
        "stages",
        "machine_codes",
        "supersedes_receipt_digest",
        "receipt_digest",
    }
)


class AcceptanceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DirectoryWitness:
    path: Path
    device: int
    inode: int
    mode: int
    uid: int


@dataclass(frozen=True)
class DirectoryStateWitness:
    """Stable membership proof for one directly opened directory."""

    path: Path
    device: int
    inode: int
    mode: int
    uid: int
    mtime_ns: int
    members: tuple[str, ...]
    members_digest: str
    directory_chain: tuple[DirectoryWitness, ...] = ()


@dataclass(frozen=True)
class AbsentPathWitness:
    """Proof that a path was absent under a captured existing ancestor."""

    path: Path
    ancestor: DirectoryStateWitness
    relative_parts: tuple[str, ...]


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    raw: bytes
    sha256: str
    size: int
    mtime_ns: int
    device: int
    inode: int
    mode: int
    directory_chain: tuple[DirectoryWitness, ...] = ()


@dataclass(frozen=True)
class FileWitness:
    path: Path
    sha256: str
    size: int
    mtime_ns: int
    device: int
    inode: int
    max_bytes: int
    directory_chain: tuple[DirectoryWitness, ...] = ()


_PREPARED_SIGNING_KEY = secrets.token_bytes(32)


class _PreparedAcceptance:
    """Opaque, immutable in-process capability for publishing one snapshot."""

    __slots__ = (
        "__weakref__",
        "_ingest_receipt_bytes",
        "_receipt_bytes",
        "_release_projection_bytes",
        "_sealed",
        "data_root",
        "expected_latest_file_sha256",
        "jobs_digest",
        "jobs_dir",
        "jobs_directory_chain",
        "output_root",
        "registry_path",
        "release_validator",
        "witnesses",
    )

    def __init__(self) -> None:
        raise TypeError(
            "Prepared acceptance capabilities are created only by collect_acceptance_snapshot"
        )

    def __setattr__(self, _name: str, _value: Any) -> None:
        raise AttributeError("Prepared acceptance capabilities are immutable")

    @property
    def receipt(self) -> dict[str, Any]:
        return json.loads(self._receipt_bytes.decode("utf-8"))

    @property
    def ingest_evidence_set_receipt(self) -> dict[str, Any]:
        return json.loads(self._ingest_receipt_bytes.decode("utf-8"))

    @property
    def release_projection(self) -> dict[str, Any]:
        return json.loads(self._release_projection_bytes.decode("utf-8"))


_PREPARED_CAPABILITIES: weakref.WeakKeyDictionary[_PreparedAcceptance, str] = (
    weakref.WeakKeyDictionary()
)
_CURRENT_WRITE_AUTHORITIES: weakref.WeakKeyDictionary[_PreparedAcceptance, str] = (
    weakref.WeakKeyDictionary()
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_non_finite_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _strict_json_loads(raw: str | bytes) -> Any:
    return json.loads(raw, parse_constant=_reject_non_finite_json_constant)


def receipt_digest_is_valid(receipt: Any) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    claimed = str(receipt.get("receipt_digest") or "").strip().lower()
    if _SHA256_RE.fullmatch(claimed) is None:
        return False
    core = {key: value for key, value in receipt.items() if key != "receipt_digest"}
    try:
        return claimed == canonical_digest(core)
    except (TypeError, ValueError):
        return False


def _prepared_state_bytes(prepared: _PreparedAcceptance) -> bytes:
    witnesses = [_witness_projection(witness) for witness in prepared.witnesses]
    return canonical_json_bytes(
        {
            "receipt_sha256": hashlib.sha256(
                prepared._receipt_bytes
            ).hexdigest(),
            "ingest_receipt_sha256": hashlib.sha256(
                prepared._ingest_receipt_bytes
            ).hexdigest(),
            "release_projection_sha256": hashlib.sha256(
                prepared._release_projection_bytes
            ).hexdigest(),
            "witnesses": witnesses,
            "jobs_dir": str(prepared.jobs_dir),
            "jobs_digest": prepared.jobs_digest,
            "jobs_directory_chain": _directory_chain_projection(
                prepared.jobs_directory_chain
            ),
            "expected_latest_file_sha256": prepared.expected_latest_file_sha256,
            "release_validator_identity": id(prepared.release_validator),
            "current_write_authority": _CURRENT_WRITE_AUTHORITIES.get(prepared),
            "data_root": str(prepared.data_root),
            "registry_path": str(prepared.registry_path),
            "output_root": (
                str(prepared.output_root)
                if prepared.output_root is not None
                else None
            ),
        }
    )


def _witness_projection(
    witness: FileSnapshot
    | FileWitness
    | DirectoryStateWitness
    | AbsentPathWitness,
) -> dict[str, Any]:
    if isinstance(witness, AbsentPathWitness):
        return {
            "kind": "AbsentPathWitness",
            "path": str(witness.path),
            "relative_parts": list(witness.relative_parts),
            "ancestor": _witness_projection(witness.ancestor),
        }
    if isinstance(witness, DirectoryStateWitness):
        return {
            "kind": "DirectoryStateWitness",
            "path": str(witness.path),
            "device": witness.device,
            "inode": witness.inode,
            "mode": witness.mode,
            "uid": witness.uid,
            "mtime_ns": witness.mtime_ns,
            "members": list(witness.members),
            "members_digest": witness.members_digest,
            "directory_chain": _directory_chain_projection(
                witness.directory_chain
            ),
        }
    return {
        "kind": type(witness).__name__,
        "path": str(witness.path),
        "sha256": witness.sha256,
        "size": witness.size,
        "mtime_ns": witness.mtime_ns,
        "device": witness.device,
        "inode": witness.inode,
        "mode": getattr(witness, "mode", None),
        "max_bytes": (
            witness.max_bytes if isinstance(witness, FileWitness) else None
        ),
        "directory_chain": _directory_chain_projection(witness.directory_chain),
    }


def _prepared_signature(prepared: _PreparedAcceptance) -> str:
    return hmac.new(
        _PREPARED_SIGNING_KEY,
        _prepared_state_bytes(prepared),
        hashlib.sha256,
    ).hexdigest()


def _assert_prepared_capability(value: Any) -> _PreparedAcceptance:
    if type(value) is not _PreparedAcceptance:
        raise AcceptanceError(
            "ACCEPTANCE_SNAPSHOT_INVALID", "发布只接受内部签发的不可变验收快照"
        )
    expected = _PREPARED_CAPABILITIES.get(value)
    if expected is None or not hmac.compare_digest(
        expected,
        _prepared_signature(value),
    ):
        raise AcceptanceError(
            "ACCEPTANCE_SNAPSHOT_INVALID", "验收快照能力无效或已发生变化"
        )
    return value


def _validate_run_id(value: Any) -> str:
    run_id = str(value or "").strip()
    if (
        _RUN_ID_RE.fullmatch(run_id) is None
        or ".." in run_id
        or run_id.casefold() in _RESERVED_RUN_IDS
    ):
        raise AcceptanceError("ACCEPTANCE_RUN_ID_INVALID", "run ID格式无效或为保留名称")
    return run_id


def _parse_utc_timestamp(value: Any) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise AcceptanceError(
            "ACCEPTANCE_RECEIPT_SCHEMA_INVALID", "回执缺少生成时间"
        )
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_RECEIPT_SCHEMA_INVALID", "回执生成时间无效"
        ) from exc
    if parsed.tzinfo is None:
        raise AcceptanceError(
            "ACCEPTANCE_RECEIPT_SCHEMA_INVALID", "回执生成时间必须包含时区"
        )
    return parsed.astimezone(timezone.utc)


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        left.st_size,
        left.st_mtime_ns,
    ) == (
        right.st_dev,
        right.st_ino,
        right.st_size,
        right.st_mtime_ns,
    )


def _directory_chain_projection(
    chain: tuple[DirectoryWitness, ...] | None,
) -> list[dict[str, Any]] | None:
    if chain is None:
        return None
    return [
        {
            "path": str(item.path),
            "device": item.device,
            "inode": item.inode,
            "mode": item.mode,
            "uid": item.uid,
        }
        for item in chain
    ]


def _capture_directory_chain(
    directory: str | Path,
    *,
    code: str,
) -> tuple[DirectoryWitness, ...]:
    """Capture one absolute directory path without following any component link."""

    try:
        candidate = Path(os.path.abspath(os.fspath(directory)))
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(code, "目录路径无法安全解析") from exc
    if not candidate.is_absolute():
        raise AcceptanceError(code, "目录路径必须为绝对路径")
    current = Path(candidate.anchor)
    parts = candidate.parts[1:]
    witnesses: list[DirectoryWitness] = []
    for index in range(len(parts) + 1):
        if index:
            current = current / parts[index - 1]
        try:
            info = os.lstat(current)
        except (OSError, ValueError) as exc:
            raise AcceptanceError(code, "目录链无法验证") from exc
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise AcceptanceError(code, "目录链不得包含符号链接或非目录对象")
        witnesses.append(
            DirectoryWitness(
                path=current,
                device=info.st_dev,
                inode=info.st_ino,
                mode=stat.S_IMODE(info.st_mode),
                uid=info.st_uid,
            )
        )
    return tuple(witnesses)


def _verify_directory_chain(
    chain: tuple[DirectoryWitness, ...],
    *,
    code: str,
) -> None:
    for witness in chain:
        try:
            current = os.lstat(witness.path)
        except (OSError, ValueError) as exc:
            raise AcceptanceError(code, "目录链已发生变化") from exc
        if (
            not stat.S_ISDIR(current.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or current.st_dev != witness.device
            or current.st_ino != witness.inode
            or stat.S_IMODE(current.st_mode) != witness.mode
            or current.st_uid != witness.uid
        ):
            raise AcceptanceError(code, "目录链已发生变化")


def _capture_directory_state(
    directory: str | Path,
    *,
    code: str,
) -> DirectoryStateWitness:
    try:
        candidate = Path(os.path.abspath(os.fspath(directory)))
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(code, "目录成员集路径无法安全解析") from exc
    directory_chain = _capture_directory_chain(candidate.parent, code=code)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        descriptor = os.open(candidate, flags)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(code, "目录成员集无法安全读取") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(before.st_mode)
            or before.st_uid != os.getuid()
        ):
            raise AcceptanceError(code, "目录成员集类型或所有者不可信")
        try:
            members = tuple(sorted(os.listdir(descriptor)))
        except (OSError, ValueError) as exc:
            raise AcceptanceError(code, "目录成员集无法安全枚举") from exc
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        current = os.lstat(candidate)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(code, "目录成员集读取后无法复验") from exc
    if (
        stat.S_ISLNK(current.st_mode)
        or not stat.S_ISDIR(current.st_mode)
        or not _same_file_identity(before, after)
        or not _same_file_identity(after, current)
    ):
        raise AcceptanceError(code, "目录成员集读取期间发生变化")
    _verify_directory_chain(directory_chain, code=code)
    return DirectoryStateWitness(
        path=candidate,
        device=after.st_dev,
        inode=after.st_ino,
        mode=stat.S_IMODE(after.st_mode),
        uid=after.st_uid,
        mtime_ns=after.st_mtime_ns,
        members=members,
        members_digest=canonical_digest(list(members)),
        directory_chain=directory_chain,
    )


def _verify_directory_state(
    witness: DirectoryStateWitness,
    *,
    code: str,
) -> None:
    current = _capture_directory_state(witness.path, code=code)
    if current != witness:
        raise AcceptanceError(code, "目录成员集已发生变化")


def _capture_absent_path_witness(
    path: str | Path,
    *,
    code: str,
) -> AbsentPathWitness:
    try:
        candidate = Path(os.path.abspath(os.fspath(path)))
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(code, "缺失路径无法安全解析") from exc
    ancestor = candidate.parent
    missing_parts: list[str] = [candidate.name]
    while True:
        try:
            info = os.lstat(ancestor)
        except FileNotFoundError:
            if ancestor == Path(ancestor.anchor):
                raise AcceptanceError(code, "缺失路径不存在可验证的父目录") from None
            missing_parts.append(ancestor.name)
            ancestor = ancestor.parent
            continue
        except (OSError, ValueError) as exc:
            raise AcceptanceError(code, "缺失路径父目录无法验证") from exc
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise AcceptanceError(code, "缺失路径父链包含不可信对象")
        break
    state = _capture_directory_state(ancestor, code=code)
    relative_parts = tuple(reversed(missing_parts))
    if not relative_parts or relative_parts[0] in state.members:
        raise AcceptanceError(code, "声明缺失的路径当前已经存在")
    return AbsentPathWitness(
        path=candidate,
        ancestor=state,
        relative_parts=relative_parts,
    )


def _verify_absent_path_witness(
    witness: AbsentPathWitness,
    *,
    code: str,
) -> None:
    _verify_directory_chain(witness.ancestor.directory_chain, code=code)
    try:
        current_ancestor = os.lstat(witness.ancestor.path)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(code, "缺失路径父目录已发生变化") from exc
    if (
        not stat.S_ISDIR(current_ancestor.st_mode)
        or stat.S_ISLNK(current_ancestor.st_mode)
        or current_ancestor.st_dev != witness.ancestor.device
        or current_ancestor.st_ino != witness.ancestor.inode
        or stat.S_IMODE(current_ancestor.st_mode) != witness.ancestor.mode
        or current_ancestor.st_uid != witness.ancestor.uid
    ):
        raise AcceptanceError(code, "缺失路径父目录已发生变化")
    current = witness.ancestor.path
    for index, part in enumerate(witness.relative_parts):
        current = current / part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            raise AcceptanceError(code, "缺失路径复验失败") from exc
        if index == len(witness.relative_parts) - 1:
            raise AcceptanceError(code, "验收期间缺失路径变为存在")
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise AcceptanceError(code, "缺失路径父链变为不可信对象")
    raise AcceptanceError(code, "验收期间缺失路径变为存在")


def _read_optional_regular_file_snapshot(
    path: str | Path,
    *,
    max_bytes: int = _MAX_JSON_BYTES,
) -> tuple[FileSnapshot | None, AbsentPathWitness | None]:
    try:
        candidate = Path(os.path.abspath(os.fspath(path)))
        os.lstat(candidate)
    except FileNotFoundError:
        absent = _capture_absent_path_witness(
            candidate,
            code="ACCEPTANCE_INPUT_UNTRUSTED",
        )
        return None, absent
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_UNTRUSTED", "可选输入路径无法安全验证"
        ) from exc
    try:
        snapshot = read_regular_file_snapshot(candidate, max_bytes=max_bytes)
    except AcceptanceError as exc:
        if exc.code != "ACCEPTANCE_INPUT_MISSING":
            raise
        absent = _capture_absent_path_witness(
            candidate,
            code="ACCEPTANCE_INPUT_UNTRUSTED",
        )
        return None, absent
    assert snapshot is not None
    return snapshot, None


def _capture_optional_directory_state(
    path: str | Path,
    *,
    code: str,
) -> tuple[DirectoryStateWitness | None, AbsentPathWitness | None]:
    candidate = Path(os.path.abspath(os.fspath(path)))
    try:
        info = os.lstat(candidate)
    except FileNotFoundError:
        return None, _capture_absent_path_witness(candidate, code=code)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(code, "目录状态无法验证") from exc
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise AcceptanceError(code, "目录状态类型不可信")
    return _capture_directory_state(candidate, code=code), None


def read_regular_file_snapshot(
    path: str | Path,
    *,
    max_bytes: int = _MAX_JSON_BYTES,
    allow_missing: bool = False,
) -> FileSnapshot | None:
    try:
        candidate = Path(os.path.abspath(os.fspath(path)))
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_UNTRUSTED", "输入文件路径无法安全解析"
        ) from exc
    directory_chain = _capture_directory_chain(
        candidate.parent,
        code="ACCEPTANCE_INPUT_UNTRUSTED",
    )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except FileNotFoundError:
        if allow_missing:
            return None
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_MISSING", f"缺少输入文件：{candidate.name}"
        ) from None
    except (OSError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_UNTRUSTED", f"输入文件不可安全读取：{candidate.name}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_size < 0
            or before.st_size > max_bytes
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_UNTRUSTED", f"输入文件类型、所有者或大小不可信：{candidate.name}"
            )
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
        if len(raw) > max_bytes or not _same_file_identity(before, after):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", f"读取期间输入发生变化：{candidate.name}"
            )
    finally:
        os.close(descriptor)
    try:
        current = candidate.lstat()
    except (OSError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_CHANGED", f"读取后输入无法复验：{candidate.name}"
        ) from exc
    if (
        candidate.is_symlink()
        or not _same_file_identity(after, current)
        or stat.S_IMODE(after.st_mode) != stat.S_IMODE(current.st_mode)
    ):
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_CHANGED", f"读取后输入身份发生变化：{candidate.name}"
        )
    _verify_directory_chain(directory_chain, code="ACCEPTANCE_INPUT_CHANGED")
    return FileSnapshot(
        path=candidate,
        raw=raw,
        sha256=hashlib.sha256(raw).hexdigest(),
        size=len(raw),
        mtime_ns=after.st_mtime_ns,
        device=after.st_dev,
        inode=after.st_ino,
        mode=stat.S_IMODE(after.st_mode),
        directory_chain=directory_chain,
    )


def read_regular_file_witness(
    path: str | Path,
    *,
    max_bytes: int = _MAX_EVIDENCE_BYTES,
) -> FileWitness:
    try:
        candidate = Path(os.path.abspath(os.fspath(path)))
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_UNTRUSTED", "证据文件路径无法安全解析"
        ) from exc
    directory_chain = _capture_directory_chain(
        candidate.parent,
        code="ACCEPTANCE_INPUT_UNTRUSTED",
    )
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_UNTRUSTED", f"证据文件不可安全读取：{candidate.name}"
        ) from exc
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_size < 0
            or before.st_size > max_bytes
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_UNTRUSTED",
                f"证据文件类型、所有者或大小不可信：{candidate.name}",
            )
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
        if not _same_file_identity(before, after):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", f"读取期间证据发生变化：{candidate.name}"
            )
    finally:
        os.close(descriptor)
    try:
        current = candidate.lstat()
    except (OSError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_CHANGED", f"读取后证据无法复验：{candidate.name}"
        ) from exc
    if candidate.is_symlink() or not _same_file_identity(after, current):
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_CHANGED", f"读取后证据身份发生变化：{candidate.name}"
        )
    _verify_directory_chain(directory_chain, code="ACCEPTANCE_INPUT_CHANGED")
    return FileWitness(
        path=candidate,
        sha256=digest.hexdigest(),
        size=after.st_size,
        mtime_ns=after.st_mtime_ns,
        device=after.st_dev,
        inode=after.st_ino,
        max_bytes=max_bytes,
        directory_chain=directory_chain,
    )


def _decode_json(snapshot: FileSnapshot, *, require_object: bool = True) -> Any:
    try:
        value = _strict_json_loads(snapshot.raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_JSON_INVALID",
            f"输入不是有效UTF-8 JSON：{snapshot.path.name}",
        ) from exc
    if require_object and not isinstance(value, dict):
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_JSON_INVALID",
            f"输入JSON必须为对象：{snapshot.path.name}",
        )
    return value


def _directory_is_trusted(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISDIR(info.st_mode)
        and not path.is_symlink()
        and info.st_uid == os.getuid()
    )


def _validate_root(path: str | Path, *, code: str) -> Path:
    try:
        candidate = Path(os.path.abspath(os.fspath(path)))
    except (TypeError, ValueError, OSError) as exc:
        raise AcceptanceError(code, "目录路径无法安全解析") from exc
    chain = _capture_directory_chain(candidate, code=code)
    if not _directory_is_trusted(candidate):
        raise AcceptanceError(code, f"目录不存在或不可信：{candidate.name}")
    _verify_directory_chain(chain, code=code)
    return candidate


def _snapshot_projection(
    snapshot: FileSnapshot | None,
    *,
    label: str,
    absent_witness: AbsentPathWitness | None = None,
) -> dict[str, Any]:
    if snapshot is None:
        return {
            "label": label,
            "status": "missing",
            "sha256": None,
            "size": 0,
            "absence_digest": (
                canonical_digest(_witness_projection(absent_witness))
                if absent_witness is not None
                else None
            ),
        }
    return {
        "label": label,
        "status": "present",
        "sha256": snapshot.sha256,
        "size": snapshot.size,
        "absence_digest": None,
    }


def _safe_job_snapshots(jobs_dir: Path) -> tuple[list[tuple[FileSnapshot, dict[str, Any]]], dict[str, Any]]:
    if not jobs_dir.exists():
        return [], {"status": "missing", "digest": canonical_digest([]), "files": []}
    if not _directory_is_trusted(jobs_dir):
        raise AcceptanceError(
            "ACCEPTANCE_JOBS_DIRECTORY_UNTRUSTED", "任务目录类型或所有者不可信"
        )
    rows: list[tuple[FileSnapshot, dict[str, Any]]] = []
    projections: list[dict[str, Any]] = []
    for path in sorted(jobs_dir.iterdir(), key=lambda item: item.name):
        if path.suffix != ".json" or _JOB_ID_RE.fullmatch(path.stem) is None:
            continue
        try:
            snapshot = read_regular_file_snapshot(path)
            assert snapshot is not None
            payload = _decode_json(snapshot)
        except AcceptanceError as exc:
            projections.append(
                {"job_id": path.stem, "status": "rejected", "machine_code": exc.code}
            )
            continue
        rows.append((snapshot, payload))
        projections.append(
            {"job_id": path.stem, "status": "read", "sha256": snapshot.sha256}
        )
    return rows, {
        "status": "present",
        "digest": canonical_digest(projections),
        "files": projections,
    }


def _trusted_ingest_evidence(
    *,
    audit_lines: tuple[str, ...],
    data_root: Path,
    project_id: str,
) -> tuple[dict[str, Any], dict[str, Any], list[FileWitness]]:
    latest: dict[str, dict[str, Any]] = {}
    for line in reversed(audit_lines):
        try:
            row = _strict_json_loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        if str(row.get("project_id") or "").strip() != project_id:
            continue
        sha256 = str(row.get("sha256") or "").strip().lower()
        if _SHA256_RE.fullmatch(sha256) is None or sha256 in latest:
            continue
        latest[sha256] = row

    trusted_records: list[dict[str, Any]] = []
    witnesses: list[FileWitness] = []
    for row in latest.values():
        if row.get("enabled") is False or row.get("usable") is False:
            continue
        trusted = resolve_trusted_ingest_record(
            row,
            workspace_root=data_root,
        )
        if trusted.get("ok") is not True:
            continue
        source_witness = read_regular_file_witness(trusted["source_path"])
        extract_witness = read_regular_file_witness(
            trusted["extract_path"],
            max_bytes=_MAX_AUDIT_BYTES,
        )
        if (
            source_witness.sha256 != trusted.get("source_sha256")
            or extract_witness.sha256 != trusted.get("extract_text_sha256")
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INGEST_EVIDENCE_CHANGED",
                "入库证据字节与审计摘要不一致",
            )
        trusted_records.append(trusted)
        witnesses.extend((source_witness, extract_witness))
    receipt = build_ingest_evidence_set_receipt(
        project_id=project_id,
        audit_path=data_root / "audit" / "ingest.jsonl",
        trusted_records=trusted_records,
    )
    validation = validate_ingest_evidence_set_receipt(
        receipt,
        expected_project_id=project_id,
        audit_lines=audit_lines,
    )
    return receipt, validation, witnesses


def _source_input_receipt_valid(
    receipt: Any,
    *,
    project_id: str,
    tender: dict[str, Any],
    boq: dict[str, Any],
) -> bool:
    if not isinstance(receipt, dict):
        return False
    required = {
        "schema_version",
        "project_id",
        "tender_digest",
        "boq_digest",
        "receipt_digest",
    }
    if set(receipt) != required:
        return False
    core = {key: receipt.get(key) for key in required if key != "receipt_digest"}
    return bool(
        receipt.get("schema_version") == _SOURCE_INPUT_SCHEMA
        and str(receipt.get("project_id") or "").strip() == project_id
        and str(receipt.get("tender_digest") or "").lower()
        == canonical_digest(tender)
        and str(receipt.get("boq_digest") or "").lower() == canonical_digest(boq)
        and str(receipt.get("receipt_digest") or "").lower()
        == canonical_digest(core)
    )


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _assert_path_without_symlinks(
    candidate: Path,
    *,
    root: Path,
    code: str = "ACCEPTANCE_REGISTRY_UNTRUSTED",
    label: str = "官方标准registry",
) -> None:
    """Reject a lexical path if any component below a trusted root is a link."""

    absolute_candidate = Path(os.path.abspath(os.fspath(candidate)))
    absolute_root = Path(os.path.abspath(os.fspath(root)))
    try:
        relative = absolute_candidate.relative_to(absolute_root)
    except ValueError as exc:
        raise AcceptanceError(
            code, f"{label}越出受信目录"
        ) from exc
    try:
        root_info = os.lstat(absolute_root)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(code, f"{label}根目录无法验证") from exc
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode):
        raise AcceptanceError(code, f"{label}根目录不可信")
    current = absolute_root
    for part in relative.parts:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise AcceptanceError(
                code, f"{label}路径无法验证"
            ) from exc
        if stat.S_ISLNK(info.st_mode):
            raise AcceptanceError(
                code, f"{label}路径不得包含符号链接"
            )


def _trusted_build_lexical_path(
    raw_path: Any,
    *,
    release_root: Path,
    workspace_root: Path,
) -> Path:
    value = str(raw_path or "").strip()
    if not value:
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源缺少制品路径"
        )
    raw_candidate = Path(value)
    if ".." in raw_candidate.parts:
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源制品路径包含父级跳转"
        )
    candidate = raw_candidate if raw_candidate.is_absolute() else release_root / raw_candidate
    candidate = Path(os.path.abspath(os.fspath(candidate)))
    build_root = Path(
        os.path.abspath(os.fspath(workspace_root / "build"))
    )
    if not _path_within(candidate, build_root) or candidate == build_root:
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源制品越出受信build目录"
        )
    try:
        _assert_path_without_symlinks(
            candidate,
            root=build_root,
            code="HOLD_SOURCE_OUTPUT_UNTRUSTED",
            label="正式来源制品",
        )
        _capture_directory_chain(
            candidate.parent,
            code="HOLD_SOURCE_OUTPUT_UNTRUSTED",
        )
    except (OSError, RuntimeError, ValueError) as exc:
        if isinstance(exc, AcceptanceError):
            raise
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源制品路径无法验证"
        ) from exc
    return candidate


def _trusted_build_snapshot(
    raw_path: Any,
    *,
    release_root: Path,
    workspace_root: Path,
    max_bytes: int = _MAX_EVIDENCE_BYTES,
) -> FileWitness:
    candidate = _trusted_build_lexical_path(
        raw_path,
        release_root=release_root,
        workspace_root=workspace_root,
    )
    return read_regular_file_witness(candidate, max_bytes=max_bytes)


def _decode_witness_json(witness: FileWitness) -> dict[str, Any]:
    snapshot = read_regular_file_snapshot(
        witness.path,
        max_bytes=min(witness.max_bytes, _MAX_JSON_BYTES),
    )
    assert snapshot is not None
    if snapshot.sha256 != witness.sha256:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_CHANGED", f"证据读取期间发生变化：{witness.path.name}"
        )
    return _decode_json(snapshot)


def _validate_pdf_witness(witness: FileWitness) -> None:
    """Verify identity, digest and PDF framing from one no-follow descriptor."""

    _verify_directory_chain(
        witness.directory_chain,
        code="ACCEPTANCE_INPUT_CHANGED",
    )
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(witness.path, flags)
    except (OSError, ValueError) as exc:
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED",
            "正式来源视觉凭证引用的PDF不可安全读取",
        ) from exc
    digest = hashlib.sha256()
    first = b""
    tail = b""
    read_size = 0
    try:
        before = os.fstat(descriptor)
        expected_identity = (
            witness.device,
            witness.inode,
            witness.size,
            witness.mtime_ns,
        )
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or before.st_size < 0
            or before.st_size > witness.max_bytes
            or (
                before.st_dev,
                before.st_ino,
                before.st_size,
                before.st_mtime_ns,
            )
            != expected_identity
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                "正式来源视觉凭证引用的PDF身份无效",
            )
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            if len(first) < 5:
                first = (first + chunk)[:5]
            tail = (tail + chunk)[-1024:]
            read_size += len(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        try:
            current = os.stat(witness.path, follow_symlinks=False)
        except OSError as exc:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED",
                "正式来源PDF读取后无法复验",
            ) from exc
        if (
            not _same_file_identity(before, after)
            or not _same_file_identity(after, current)
            or read_size != witness.size
            or digest.hexdigest() != witness.sha256
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED",
                "正式来源PDF读取期间发生变化",
            )
        if first != b"%PDF-" or b"%%EOF" not in tail:
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                "正式来源视觉凭证引用的PDF格式无效",
            )
    finally:
        os.close(descriptor)
    _verify_directory_chain(
        witness.directory_chain,
        code="ACCEPTANCE_INPUT_CHANGED",
    )


def _xml_local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _ooxml_relationship_target(rels_name: str, target: str) -> str:
    if rels_name == "_rels/.rels":
        base = ""
    else:
        rels_dir = posixpath.dirname(rels_name)
        base = posixpath.dirname(rels_dir)
    return posixpath.normpath(posixpath.join(base, target)).lstrip("/")


def _validate_ooxml_package(
    witness: FileWitness,
    *,
    package_kind: str,
) -> dict[str, Any]:
    """Validate a Word/Excel package from the same witnessed regular file."""

    if package_kind not in {"docx", "xlsx"}:
        raise ValueError("unsupported OOXML package kind")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(witness.path, flags)
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.getuid()
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (witness.device, witness.inode, witness.size, witness.mtime_ns)
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                "正式来源OOXML制品身份不匹配",
            )
        with (
            os.fdopen(os.dup(descriptor), "rb") as package_file,
            zipfile.ZipFile(package_file) as package,
        ):
                infos = package.infolist()
                names = [item.filename for item in infos]
                if (
                    not infos
                    or len(names) != len(set(names))
                    or len(names) > 20_000
                    or any(
                        not name
                        or "\\" in name
                        or name.startswith("/")
                        or ".." in Path(name).parts
                        or item.flag_bits & 0x1
                        for name, item in zip(names, infos, strict=True)
                    )
                    or sum(item.file_size for item in infos) > 2 * 1024 * 1024 * 1024
                ):
                    raise AcceptanceError(
                        "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                        "正式来源OOXML包目录无效",
                    )
                name_set = set(names)
                required_common = {"[Content_Types].xml", "_rels/.rels"}
                main_part = (
                    "word/document.xml"
                    if package_kind == "docx"
                    else "xl/workbook.xml"
                )
                required = required_common | {main_part}
                if package_kind == "xlsx":
                    required.add("xl/_rels/workbook.xml.rels")
                if not required.issubset(name_set):
                    raise AcceptanceError(
                        "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                        "正式来源OOXML包缺少必要部件",
                    )

                parsed_xml: dict[str, ElementTree.Element] = {}
                for name in sorted(name_set):
                    if not name.endswith((".xml", ".rels")):
                        continue
                    try:
                        parsed_xml[name] = ElementTree.fromstring(package.read(name))
                    except (KeyError, RuntimeError, ValueError, ElementTree.ParseError) as exc:
                        raise AcceptanceError(
                            "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                            "正式来源OOXML包含损坏XML",
                        ) from exc

                content_types = parsed_xml["[Content_Types].xml"]
                overrides = {
                    str(item.attrib.get("PartName") or "").lstrip("/"): str(
                        item.attrib.get("ContentType") or ""
                    )
                    for item in content_types
                    if _xml_local_name(item.tag) == "Override"
                }
                expected_content_type = (
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document.main+xml"
                    if package_kind == "docx"
                    else "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet.main+xml"
                )
                root_relationships = parsed_xml["_rels/.rels"]
                office_targets = [
                    _ooxml_relationship_target(
                        "_rels/.rels", str(item.attrib.get("Target") or "")
                    )
                    for item in root_relationships
                    if _xml_local_name(item.tag) == "Relationship"
                    and str(item.attrib.get("Type") or "").endswith("/officeDocument")
                    and str(item.attrib.get("TargetMode") or "").lower() != "external"
                ]
                if overrides.get(main_part) != expected_content_type or office_targets != [
                    main_part
                ]:
                    raise AcceptanceError(
                        "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                        "正式来源OOXML主文档身份无效",
                    )

                for rels_name, root in parsed_xml.items():
                    if not rels_name.endswith(".rels"):
                        continue
                    seen_ids: set[str] = set()
                    for item in root:
                        if _xml_local_name(item.tag) != "Relationship":
                            continue
                        rel_id = str(item.attrib.get("Id") or "")
                        if not rel_id or rel_id in seen_ids:
                            raise AcceptanceError(
                                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                                "正式来源OOXML关系标识无效",
                            )
                        seen_ids.add(rel_id)
                        if str(item.attrib.get("TargetMode") or "").lower() == "external":
                            continue
                        target = _ooxml_relationship_target(
                            rels_name, str(item.attrib.get("Target") or "")
                        )
                        if not target or target.startswith("../") or target not in name_set:
                            raise AcceptanceError(
                                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                                "正式来源OOXML存在悬空关系",
                            )

                main_root = parsed_xml[main_part]
                sheet_count = 0
                if package_kind == "docx":
                    if _xml_local_name(main_root.tag) != "document" or not any(
                        _xml_local_name(item.tag) == "body" for item in main_root
                    ):
                        raise AcceptanceError(
                            "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                            "正式来源Word主文档结构无效",
                        )
                else:
                    if _xml_local_name(main_root.tag) != "workbook":
                        raise AcceptanceError(
                            "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                            "正式来源Excel工作簿结构无效",
                        )
                    workbook_rels = parsed_xml["xl/_rels/workbook.xml.rels"]
                    rel_targets = {
                        str(item.attrib.get("Id") or ""): _ooxml_relationship_target(
                            "xl/_rels/workbook.xml.rels",
                            str(item.attrib.get("Target") or ""),
                        )
                        for item in workbook_rels
                        if _xml_local_name(item.tag) == "Relationship"
                        and str(item.attrib.get("TargetMode") or "").lower()
                        != "external"
                    }
                    sheet_rows = [
                        item
                        for item in main_root.iter()
                        if _xml_local_name(item.tag) == "sheet"
                    ]
                    sheet_count = len(sheet_rows)
                    relationship_key = (
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    )
                    if not sheet_rows or any(
                        not str(item.attrib.get("name") or "").strip()
                        or rel_targets.get(str(item.attrib.get(relationship_key) or ""))
                        not in name_set
                        or not str(
                            rel_targets.get(str(item.attrib.get(relationship_key) or ""))
                            or ""
                        ).startswith("xl/worksheets/")
                        for item in sheet_rows
                    ):
                        raise AcceptanceError(
                            "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                            "正式来源Excel工作表结构无效",
                        )
        after = os.fstat(descriptor)
        current = os.stat(witness.path, follow_symlinks=False)
        if (
            not _same_file_identity(before, after)
            or not _same_file_identity(after, current)
            or after.st_size != witness.size
            or after.st_mtime_ns != witness.mtime_ns
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED",
                "正式来源OOXML制品在解析期间发生变化",
            )
        _verify_directory_chain(
            witness.directory_chain,
            code="ACCEPTANCE_INPUT_CHANGED",
        )
        return {
            "kind": package_kind,
            "entry_count": len(names),
            "main_part": main_part,
            "sheet_count": sheet_count,
        }
    except AcceptanceError:
        raise
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as exc:
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED",
            "正式来源制品不是有效OOXML包",
        ) from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _event_bundle(
    *,
    events_dir: Path,
    job_id: str,
    events_state: DirectoryStateWitness | None = None,
) -> tuple[list[dict[str, Any]], list[FileSnapshot]]:
    if events_state is None:
        captured, _absent = _capture_optional_directory_state(
            events_dir,
            code="HOLD_SOURCE_EVENTS_INCOMPLETE",
        )
        events_state = captured
    if events_state is None or events_state.path != Path(
        os.path.abspath(os.fspath(events_dir))
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源事件目录缺失或不可信"
        )
    pattern = re.compile(rf"^{re.escape(job_id)}(?:\.(\d+))?\.jsonl$")
    candidates: list[tuple[int, Path]] = []
    for name in events_state.members:
        match = pattern.fullmatch(name)
        if match is None:
            continue
        order = int(match.group(1)) if match.group(1) else 2**63 - 1
        candidates.append((order, events_state.path / name))
    if not candidates:
        raise AcceptanceError(
            "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源缺少事件日志"
        )
    events: list[dict[str, Any]] = []
    snapshots: list[FileSnapshot] = []
    previous_timestamp: float | None = None
    for _order, path in sorted(candidates, key=lambda item: (item[0], item[1].name)):
        snapshot = read_regular_file_snapshot(path, max_bytes=_MAX_AUDIT_BYTES)
        assert snapshot is not None
        snapshots.append(snapshot)
        try:
            decoded = snapshot.raw.decode("utf-8")
        except UnicodeError as exc:
            raise AcceptanceError(
                "HOLD_SOURCE_EVENTS_INCOMPLETE",
                "正式来源事件日志不是有效UTF-8",
            ) from exc
        for raw_line in decoded.splitlines():
            try:
                row = _strict_json_loads(raw_line)
            except (UnicodeError, ValueError) as exc:
                raise AcceptanceError(
                    "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源事件日志包含无效JSON"
                ) from exc
            if (
                not isinstance(row, dict)
                or str(row.get("job_id") or "").strip() != job_id
                or not isinstance(row.get("ts"), (int, float))
                or isinstance(row.get("ts"), bool)
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源事件身份不完整"
                )
            try:
                timestamp = float(row["ts"])
            except (OverflowError, TypeError, ValueError) as exc:
                raise AcceptanceError(
                    "HOLD_SOURCE_EVENTS_INCOMPLETE",
                    "正式来源事件时间无效",
                ) from exc
            if not math.isfinite(timestamp) or (
                previous_timestamp is not None and timestamp < previous_timestamp
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_EVENTS_INCOMPLETE",
                    "正式来源事件时间无效或时序倒退",
                )
            previous_timestamp = timestamp
            events.append(row)
    _verify_directory_state(
        events_state,
        code="HOLD_SOURCE_EVENTS_INCOMPLETE",
    )
    return events, snapshots


_FORMAL_PROVIDER_ROLES = frozenset(
    {"text_draft", "text_review", "document_render"}
)
_PROVIDER_ADMISSION_FIELDS = frozenset(
    {
        "schema_version",
        "generated_at",
        "ttl_seconds",
        "required_roles",
        "slots",
        "admitted_chain",
        "role_decision",
        "missing_roles",
        "generation_allowed",
        "fallback_configured",
        "fallback_ready",
        "resilience_degraded",
        "degraded",
        "admission_digest",
    }
)
_PROVIDER_SLOT_FIELDS = frozenset(
    {
        "slot",
        "role",
        "provider",
        "model",
        "credential_fingerprint",
        "identity_digest",
        "admitted",
        "layers",
        "reason_codes",
        "checked_at",
        "expires_at",
        "stream_required",
        "cache_hit",
        "probe_duration_ms",
    }
)
_PROVIDER_CORE_LAYERS = frozenset(
    {"configuration", "credentials", "model", "quota", "circuit"}
)
_PROVIDER_LAYER_STATUSES = frozenset({"pass", "fail", "skipped", "unknown"})
_PROVIDER_REASON_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


def _provider_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _validated_internal_provider_admission(
    value: Any,
) -> dict[str, Any]:
    internal = dict(value) if isinstance(value, Mapping) else {}
    supplied_digest = str(internal.get("admission_digest") or "").strip().lower()
    core = {key: item for key, item in internal.items() if key != "admission_digest"}
    slots = internal.get("slots")
    admitted_chain = internal.get("admitted_chain")
    generated_at = _provider_number(internal.get("generated_at"))
    ttl_seconds = _provider_number(internal.get("ttl_seconds"))
    try:
        expected_snapshot_digest = provider_admission_canonical_digest(core)
    except (OverflowError, TypeError, ValueError) as exc:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "当前持久化供应商准入回执无效",
        ) from exc
    if (
        internal.get("schema_version") != "provider-admission-v1"
        or set(internal) != _PROVIDER_ADMISSION_FIELDS
        or _SHA256_RE.fullmatch(supplied_digest) is None
        or supplied_digest != expected_snapshot_digest
        or generated_at is None
        or generated_at < 0
        or ttl_seconds is None
        or ttl_seconds < 0
        or not isinstance(internal.get("required_roles"), list)
        or not isinstance(internal.get("role_decision"), Mapping)
        or not isinstance(internal.get("missing_roles"), list)
        or any(
            not isinstance(internal.get(field), bool)
            for field in (
                "generation_allowed",
                "fallback_configured",
                "fallback_ready",
                "resilience_degraded",
                "degraded",
            )
        )
        or not isinstance(slots, list)
        or not slots
        or not isinstance(admitted_chain, list)
        or not admitted_chain
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "当前持久化供应商准入回执无效",
        )
    normalized_slots: list[dict[str, Any]] = []
    for raw in slots:
        if not isinstance(raw, Mapping) or set(raw) != _PROVIDER_SLOT_FIELDS:
            raise AcceptanceError(
                "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                "当前持久化供应商准入身份无效",
            )
        identity = {
            field: str(raw.get(field) or "").strip()
            for field in (
                "slot",
                "role",
                "provider",
                "model",
                "credential_fingerprint",
                "identity_digest",
            )
        }
        identity["provider"] = identity["provider"].lower()
        expected_identity_digest = provider_admission_canonical_digest(
            {
                "slot": identity["slot"],
                "provider": identity["provider"],
                "model": identity["model"],
                "credential_fingerprint": identity["credential_fingerprint"],
            }
        )
        layers = raw.get("layers")
        reason_codes = raw.get("reason_codes")
        checked_at = _provider_number(raw.get("checked_at"))
        expires_at = _provider_number(raw.get("expires_at"))
        stream_required = raw.get("stream_required")
        cache_hit = raw.get("cache_hit")
        probe_duration_ms = raw.get("probe_duration_ms")
        layers_valid = bool(
            isinstance(layers, Mapping)
            and set(layers) == set(LAYER_NAMES)
            and all(
                isinstance(layer, Mapping)
                and set(layer) == {"status", "code"}
                and layer.get("status") in _PROVIDER_LAYER_STATUSES
                and _PROVIDER_REASON_CODE_RE.fullmatch(
                    str(layer.get("code") or "")
                )
                is not None
                for layer in layers.values()
            )
        )
        required_layers = set(_PROVIDER_CORE_LAYERS)
        if stream_required is True:
            required_layers.add("stream")
        recomputed_admitted = bool(
            layers_valid
            and all(layers[name].get("status") == "pass" for name in required_layers)
        )
        expected_reason_codes = (
            list(
                dict.fromkeys(
                    str(layers[name].get("code") or "")
                    for name in LAYER_NAMES
                    if layers[name].get("status") == "fail"
                    or (
                        layers[name].get("status") == "unknown"
                        and name in required_layers
                    )
                )
            )
            if layers_valid
            else []
        )
        if (
            not all(identity.values())
            or _SHA256_RE.fullmatch(identity["credential_fingerprint"]) is None
            or _SHA256_RE.fullmatch(identity["identity_digest"]) is None
            or identity["identity_digest"] != expected_identity_digest
            or not isinstance(raw.get("admitted"), bool)
            or not layers_valid
            or not isinstance(stream_required, bool)
            or not isinstance(cache_hit, bool)
            or isinstance(probe_duration_ms, bool)
            or not isinstance(probe_duration_ms, int)
            or probe_duration_ms < 0
            or not isinstance(reason_codes, list)
            or reason_codes != expected_reason_codes
            or any(
                not isinstance(code, str)
                or _PROVIDER_REASON_CODE_RE.fullmatch(code) is None
                for code in reason_codes
            )
            or raw.get("admitted") is not recomputed_admitted
            or (
                stream_required is False
                and (
                    layers["stream"].get("status") != "skipped"
                    or layers["stream"].get("code") != "stream_not_required"
                )
            )
            or checked_at is None
            or checked_at < 0
            or expires_at is None
            or expires_at < checked_at
            or generated_at is None
            or ttl_seconds is None
            or checked_at > generated_at
            or generated_at > expires_at
            or not math.isclose(
                expires_at,
                checked_at + ttl_seconds,
                rel_tol=0.0,
                abs_tol=1e-9,
            )
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                "当前持久化供应商准入身份无法重算",
            )
        normalized_slots.append({**identity, "admitted": recomputed_admitted})
    expected_chain = [
        {
            field: row[field]
            for field in (
                "slot",
                "role",
                "provider",
                "model",
                "credential_fingerprint",
                "identity_digest",
            )
        }
        for row in normalized_slots
        if row["admitted"]
    ]
    normalized_chain = [
        {
            field: (
                str(raw.get(field) or "").strip().lower()
                if field == "provider"
                else str(raw.get(field) or "").strip()
            )
            for field in (
                "slot",
                "role",
                "provider",
                "model",
                "credential_fingerprint",
                "identity_digest",
            )
        }
        for raw in admitted_chain
        if isinstance(raw, Mapping)
    ]
    if (
        len(normalized_chain) != len(admitted_chain)
        or normalized_chain != expected_chain
        or len({row["slot"] for row in normalized_chain}) != len(normalized_chain)
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "当前持久化供应商准入路由与身份不一致",
        )
    try:
        public = provider_public_snapshot(internal)
    except (KeyError, OverflowError, TypeError, ValueError) as exc:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "当前持久化供应商准入公开投影无效",
        ) from exc
    decision = decide_provider_required_roles(slots, internal["required_roles"])
    binding_material = {
        "schema_version": "provider-admission-binding-v1",
        "required_roles": list(internal.get("required_roles") or []),
        "admitted_route_identities": [
            {
                field: row[field]
                for field in ("slot", "role", "provider", "model", "identity_digest")
            }
            for row in normalized_chain
        ],
    }
    if (
        public.get("generation_allowed") is not True
        or set(public.get("required_roles") or []) != _FORMAL_PROVIDER_ROLES
        or public.get("missing_roles") != []
        or internal.get("role_decision") != decision["roles"]
        or internal.get("missing_roles") != decision["missing_roles"]
        or any(
            internal.get(field) != decision[field]
            for field in (
                "generation_allowed",
                "fallback_configured",
                "fallback_ready",
                "resilience_degraded",
                "degraded",
            )
        )
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "当前持久化供应商准入未覆盖正式角色",
        )
    return {
        "public": public,
        "binding_digest": provider_admission_canonical_digest(binding_material),
        "admitted_route_identities": binding_material["admitted_route_identities"],
        "snapshot_digest": supplied_digest,
    }


def _validated_provider_admission(
    value: Any,
    *,
    events: list[dict[str, Any]],
    durable: Mapping[str, Any],
) -> dict[str, Any]:
    admission = dict(value) if isinstance(value, Mapping) else {}
    if admission != durable.get("public"):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源准入公开投影与当前持久化身份不一致",
        )
    public_digest = str(admission.get("public_digest") or "").strip().lower()
    core = {key: item for key, item in admission.items() if key != "public_digest"}
    required_roles = admission.get("required_roles")
    admitted_chain = admission.get("admitted_chain")
    missing_roles = admission.get("missing_roles")
    slots = admission.get("slots")
    expected_fields = {
        "schema_version",
        "status",
        "required_roles",
        "slots",
        "admitted_chain",
        "missing_roles",
        "generation_allowed",
        "fallback_configured",
        "fallback_ready",
        "resilience_degraded",
        "degraded",
        "public_digest",
    }
    if (
        set(admission) != expected_fields
        or admission.get("schema_version") != "provider-admission-v1"
        or admission.get("status") not in {"admitted", "degraded"}
        or _SHA256_RE.fullmatch(public_digest) is None
        or public_digest != canonical_digest(core)
        or not isinstance(required_roles, list)
        or len(required_roles) != len(_FORMAL_PROVIDER_ROLES)
        or set(required_roles) != _FORMAL_PROVIDER_ROLES
        or admission.get("generation_allowed") is not True
        or missing_roles != []
        or not isinstance(admitted_chain, list)
        or not admitted_chain
        or not isinstance(slots, list)
        or not slots
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源供应商准入回执无效",
        )

    normalized_chain: list[dict[str, str]] = []
    for raw in admitted_chain:
        if not isinstance(raw, Mapping) or set(raw) != {
            "slot",
            "role",
            "provider",
            "model",
        }:
            raise AcceptanceError(
                "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                "正式来源供应商准入路由无效",
            )
        row = {
            field: str(raw.get(field) or "").strip()
            for field in ("slot", "role", "provider", "model")
        }
        if not all(row.values()):
            raise AcceptanceError(
                "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                "正式来源供应商准入路由无效",
            )
        normalized_chain.append(row)
    if not _FORMAL_PROVIDER_ROLES.issubset(
        {row["role"] for row in normalized_chain}
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源供应商准入缺少必需角色",
        )
    route_identities = {
        (row["slot"], row["role"], row["provider"], row["model"])
        for row in normalized_chain
    }
    if (
        len(route_identities) != len(normalized_chain)
        or len({row["slot"] for row in normalized_chain}) != len(normalized_chain)
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源供应商准入路由不唯一",
        )
    admitted_slot_identities = {
        (
            str(raw.get("slot") or "").strip(),
            str(raw.get("role") or "").strip(),
            str(raw.get("provider") or "").strip(),
            str(raw.get("model") or "").strip(),
        )
        for raw in slots
        if isinstance(raw, Mapping) and raw.get("admitted") is True
    }
    if any(
        (row["slot"], row["role"], row["provider"], row["model"])
        not in admitted_slot_identities
        for row in normalized_chain
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源供应商准入明细与路由不一致",
        )

    names = [str(row.get("event") or "") for row in events]
    try:
        started_index = max(
            index for index, name in enumerate(names) if name == "job_started"
        )
    except ValueError as exc:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源缺少供应商准入事件",
        ) from exc
    tail = events[started_index:]
    admission_started = [
        (index, row)
        for index, row in enumerate(tail)
        if row.get("event") == "provider_admission_started"
    ]
    admission_completed = [
        (index, row)
        for index, row in enumerate(tail)
        if row.get("event") == "provider_admission_completed"
    ]
    attempt_indexes = [
        index
        for index, row in enumerate(tail)
        if row.get("event") == "provider_attempt_started"
    ]
    if len(admission_started) != 1 or len(admission_completed) != 1:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源供应商准入事件不唯一",
        )
    started_order, started_event = admission_started[0]
    completed_order, completed_event = admission_completed[0]
    binding_digest = str(completed_event.get("binding_digest") or "").strip().lower()
    if (
        started_order >= completed_order
        or (attempt_indexes and completed_order >= min(attempt_indexes))
        or started_event.get("required_roles") != required_roles
        or isinstance(started_event.get("candidate_count"), bool)
        or not isinstance(started_event.get("candidate_count"), int)
        or started_event.get("candidate_count", 0) < len(normalized_chain)
        or completed_event.get("schema_version") != admission.get("schema_version")
        or completed_event.get("status") != admission.get("status")
        or completed_event.get("required_roles") != required_roles
        or completed_event.get("generation_allowed") is not True
        or completed_event.get("degraded") is not admission.get("degraded")
        or completed_event.get("admitted_chain") != admitted_chain
        or completed_event.get("missing_roles") != []
        or str(completed_event.get("public_digest") or "").strip().lower()
        != public_digest
        or binding_digest != durable.get("binding_digest")
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源供应商准入事件与回执不一致",
        )
    document_routes = [
        row for row in normalized_chain if row["role"] == "document_render"
    ]
    if len(document_routes) != 1:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源文档渲染准入路由不唯一",
        )
    return {
        "public_digest": public_digest,
        "binding_digest": binding_digest,
        "durable_snapshot_digest": durable.get("snapshot_digest"),
        "durable_file_sha256": durable.get("file_sha256"),
        "required_roles": list(required_roles),
        "admitted_chain": normalized_chain,
        "admitted_route_identities": list(
            durable.get("admitted_route_identities") or []
        ),
        "document_render": document_routes[0],
    }


def _validate_event_and_provider_chain(
    *,
    events: list[dict[str, Any]],
    variant_id: int,
    allowed_variant_ids: set[int] | None = None,
    sections: list[dict[str, Any]],
    admitted_routes: list[dict[str, str]],
    attempt_id: str,
    owner_instance_id: str,
    job_revision: int,
) -> dict[str, Any]:
    admitted_attempt_identities = {
        (
            str(route.get("slot") or "").strip(),
            str(route.get("provider") or "").strip(),
            str(route.get("model") or "").strip(),
        )
        for route in admitted_routes
        if isinstance(route, Mapping)
        and str(route.get("role") or "").strip() != "document_render"
    }
    if not admitted_attempt_identities:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
            "正式来源缺少已准入的章节供应商路由",
        )
    names = [str(row.get("event") or "") for row in events]
    if "job_started" not in names or "job_succeeded" not in names:
        raise AcceptanceError(
            "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源任务终态事件不完整"
        )
    last_started = max(index for index, name in enumerate(names) if name == "job_started")
    tail = events[last_started:]
    if (
        _EXECUTION_ID_RE.fullmatch(attempt_id) is None
        or _EXECUTION_ID_RE.fullmatch(owner_instance_id) is None
        or isinstance(job_revision, bool)
        or not isinstance(job_revision, int)
        or job_revision <= 0
        or any(
            str(row.get("attempt_id") or "").strip() != attempt_id
            or str(row.get("owner_instance_id") or "").strip()
            != owner_instance_id
            or row.get("job_revision") != job_revision
            for row in tail
        )
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_EVENTS_INCOMPLETE",
            "正式来源事件未绑定同一任务执行谱系",
        )
    terminal_names = [str(row.get("event") or "") for row in tail]
    if terminal_names[-1] != "job_succeeded" or terminal_names.count(
        "job_succeeded"
    ) != 1 or any(
        name in {"job_failed", "job_cancelled", "cancelled", "job_interrupted"}
        for name in terminal_names
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源任务终态事件冲突"
        )
    terminal = tail[-1]
    if (
        terminal.get("dry_run") is not False
        or str(terminal.get("delivery_scope") or "").strip() != "document"
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_EVENTS_INCOMPLETE", "正式来源任务终态范围不完整"
        )
    if any(str(row.get("event") or "") == "chapter_resumed" for row in tail):
        raise AcceptanceError(
            "HOLD_SOURCE_CHECKPOINT_INCOMPLETE", "正式来源包含禁止复用的章节检查点"
        )

    starts: dict[tuple[Any, ...], int] = {}
    finishes: dict[tuple[Any, ...], int] = {}
    outstanding: dict[tuple[Any, ...], int] = {}
    successful_chapters: set[int] = set()
    completed_chapters: set[int] = set()
    checkpointed_chapters: set[int] = set()
    successful_routes: dict[int, dict[str, Any]] = {}
    expected = set(range(1, len(sections) + 1))
    for row in tail:
        event = str(row.get("event") or "")
        try:
            event_variant_id = int(row.get("variant_id") or 0)
        except (OverflowError, TypeError, ValueError):
            event_variant_id = 0
        if event in {
            "provider_attempt_started",
            "provider_attempt_finished",
            "chapter_checkpoint_saved",
            "chapter_completed",
        } and (
            event_variant_id <= 0
            or (
                allowed_variant_ids is not None
                and event_variant_id not in allowed_variant_ids
            )
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                "正式来源事件包含未声明的方案身份",
            )
        if event_variant_id != variant_id:
            continue
        try:
            chapter = int(row.get("chapter_index") or 0)
        except (OverflowError, TypeError, ValueError):
            chapter = 0
        key = (
            variant_id,
            chapter,
            str(row.get("provider") or ""),
            str(row.get("model") or ""),
            str(row.get("slot") or ""),
        )
        if event == "provider_attempt_started":
            if (
                chapter not in expected
                or chapter in successful_chapters
                or chapter in completed_chapters
                or any(not str(value).strip() for value in key[2:])
                or (key[4], key[2], key[3]) not in admitted_attempt_identities
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                    "正式来源供应商尝试身份无效",
                )
            starts[key] = starts.get(key, 0) + 1
            outstanding[key] = outstanding.get(key, 0) + 1
        elif event == "provider_attempt_finished":
            if chapter not in expected or outstanding.get(key, 0) <= 0:
                raise AcceptanceError(
                    "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                    "正式来源供应商尝试顺序或身份无效",
                )
            finishes[key] = finishes.get(key, 0) + 1
            outstanding[key] -= 1
            if row.get("ok") is True and chapter > 0:
                if chapter in successful_chapters:
                    raise AcceptanceError(
                        "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                        "正式来源章节包含重复成功尝试",
                    )
                section = sections[chapter - 1]
                route = {
                    "chapter_index": chapter,
                    "slot": str(row.get("slot") or "").strip(),
                    "provider": str(row.get("provider") or "").strip().lower(),
                    "model": str(row.get("model") or "").strip(),
                }
                if (
                    not isinstance(section, Mapping)
                    or str(section.get("model_slot") or "").strip()
                    != route["slot"]
                    or str(section.get("provider") or "").strip().lower()
                    != route["provider"]
                    or str(section.get("model") or "").strip()
                    != route["model"]
                ):
                    raise AcceptanceError(
                        "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                        "正式来源成功路由与章节结果不一致",
                    )
                successful_chapters.add(chapter)
                successful_routes[chapter] = route
        elif event == "chapter_checkpoint_saved":
            if (
                chapter not in expected
                or chapter not in successful_chapters
                or chapter in checkpointed_chapters
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_CHECKPOINT_INCOMPLETE",
                    "正式来源章节检查点顺序或身份无效",
                )
            checkpointed_chapters.add(chapter)
        elif event == "chapter_completed":
            if (
                row.get("ok") is not True
                or chapter not in expected
                or chapter not in successful_chapters
                or chapter not in checkpointed_chapters
                or chapter in completed_chapters
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                    "正式来源章节完成事件顺序或身份无效",
                )
            completed_chapters.add(chapter)
    if not starts or starts != finishes or any(outstanding.values()):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
            "正式来源供应商尝试未成对闭合",
        )
    if (
        successful_chapters != expected
        or completed_chapters != expected
        or checkpointed_chapters != expected
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
            "正式来源章节、供应商或检查点事件未全量闭合",
        )
    return {
        "event_count": len(events),
        "provider_attempt_count": sum(finishes.values()),
        "provider_attempts": dict(
            sorted(
                (
                    provider,
                    sum(
                        count
                        for key, count in finishes.items()
                        if key[2] == provider
                    ),
                )
                for provider in {key[2] for key in finishes}
            )
        ),
        "successful_chapter_count": len(successful_chapters),
        "attempt_id": attempt_id,
        "owner_instance_id": owner_instance_id,
        "job_revision": job_revision,
        "chapter_routes": [
            successful_routes[index] for index in sorted(successful_routes)
        ],
    }


def _checkpoint_bundle(
    *,
    checkpoints_dir: Path,
    job_id: str,
    project_id: str,
    variant_id: int,
    outline: list[str],
    sections: list[dict[str, Any]],
    provider_admission_binding_digest: str,
    compliance_registry_authority_digest: str,
    provider_admission_routes: list[dict[str, str]],
    attempt_id: str,
    owner_instance_id: str,
    job_revision: int,
    chapter_routes: list[dict[str, Any]],
) -> tuple[dict[str, Any], FileSnapshot]:
    path = checkpoints_dir / job_id / f"variant-{variant_id}.json"
    snapshot = read_regular_file_snapshot(path)
    assert snapshot is not None
    checkpoint = _decode_json(snapshot)
    core = {
        key: value for key, value in checkpoint.items() if key != "integrity_digest"
    }
    binding = checkpoint.get("binding")
    rows = checkpoint.get("sections")
    binding_fields = {
        "schema_version",
        "job_id",
        "attempt_id",
        "owner_instance_id",
        "job_revision",
        "topic",
        "project_id",
        "project_type",
        "outline",
        "style",
        "chapter_pages",
        "variant_id",
        "delivery_scope",
        "project_fact_digest",
        "requirement_plan_digest",
        "provider_admission_digest",
        "compliance_registry_authority_digest",
        "provider_routes",
        "prompt_contract_digest",
        "binding_digest",
    }
    provider_routes = binding.get("provider_routes") if isinstance(binding, dict) else None
    expected_provider_routes = [
        {
            "slot": str(route.get("slot") or "").strip(),
            "provider": str(route.get("provider") or "").strip().lower(),
            "model": str(route.get("model") or "").strip(),
        }
        for route in provider_admission_routes
        if isinstance(route, Mapping)
        and str(route.get("role") or "").strip() != "document_render"
    ]
    normalized_provider_routes = (
        [
            {
                "slot": str(route.get("slot") or "").strip(),
                "provider": str(route.get("provider") or "").strip().lower(),
                "model": str(route.get("model") or "").strip(),
            }
            for route in provider_routes
            if isinstance(route, Mapping)
        ]
        if isinstance(provider_routes, list)
        else []
    )
    if (
        checkpoint.get("schema_version") != "generation-checkpoint-v3"
        or checkpoint.get("status") != "complete"
        or str(checkpoint.get("integrity_digest") or "") != canonical_digest(core)
        or not isinstance(binding, dict)
        or set(binding) != binding_fields
        or binding.get("schema_version") != "generation-checkpoint-v3"
        or binding.get("job_id") != job_id
        or binding.get("attempt_id") != attempt_id
        or binding.get("owner_instance_id") != owner_instance_id
        or binding.get("job_revision") != job_revision
        or not str(binding.get("topic") or "").strip()
        or not str(binding.get("project_type") or "").strip()
        or not isinstance(binding.get("style"), dict)
        or not binding.get("style")
        or not isinstance(binding.get("chapter_pages"), dict)
        or not binding.get("chapter_pages")
        or _SHA256_RE.fullmatch(
            str(binding.get("project_fact_digest") or "").strip().lower()
        )
        is None
        or _SHA256_RE.fullmatch(
            str(binding.get("requirement_plan_digest") or "").strip().lower()
        )
        is None
        or str(binding.get("provider_admission_digest") or "").strip().lower()
        != provider_admission_binding_digest
        or str(
            binding.get("compliance_registry_authority_digest") or ""
        ).strip().lower()
        != compliance_registry_authority_digest
        or _SHA256_RE.fullmatch(
            str(binding.get("prompt_contract_digest") or "").strip().lower()
        )
        is None
        or not isinstance(provider_routes, list)
        or not provider_routes
        or any(
            not isinstance(route, Mapping)
            or set(route) != {"slot", "provider", "model"}
            or not all(str(route.get(field) or "").strip() for field in route)
            for route in provider_routes
        )
        or not expected_provider_routes
        or normalized_provider_routes != expected_provider_routes
        or len(
            {
                (route["slot"], route["provider"], route["model"])
                for route in normalized_provider_routes
            }
        )
        != len(normalized_provider_routes)
        or str(checkpoint.get("binding_digest") or "")
        != str(binding.get("binding_digest") or "")
        or str(binding.get("binding_digest") or "")
        != canonical_digest(
            {key: value for key, value in binding.items() if key != "binding_digest"}
        )
        or str(binding.get("project_id") or "") != project_id
        or str(binding.get("delivery_scope") or "") != "document"
        or str(binding.get("variant_id") or "") != str(variant_id)
        or binding.get("outline") != outline
        or not isinstance(rows, dict)
        or set(rows) != {str(index) for index in range(len(outline))}
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_CHECKPOINT_INCOMPLETE", "正式来源检查点身份或完整性无效"
        )
    for index, section in enumerate(sections):
        sealed = rows.get(str(index))
        if not isinstance(sealed, dict):
            raise AcceptanceError(
                "HOLD_SOURCE_CHECKPOINT_INCOMPLETE", "正式来源检查点章节缺失"
            )
        section_core = {
            key: value for key, value in sealed.items() if key != "section_digest"
        }
        result = sealed.get("result")
        expected_route = (
            chapter_routes[index]
            if index < len(chapter_routes)
            and isinstance(chapter_routes[index], Mapping)
            else {}
        )
        raw_saved_at = sealed.get("saved_at")
        try:
            saved_at = float(raw_saved_at)
        except (OverflowError, TypeError, ValueError):
            saved_at = 0.0
        if (
            str(sealed.get("section_digest") or "") != canonical_digest(section_core)
            or sealed.get("chapter_index") != index
            or str(sealed.get("chapter_title") or "") != outline[index]
            or _SHA256_RE.fullmatch(
                str(sealed.get("chapter_context_digest") or "").strip().lower()
            )
            is None
            or not math.isfinite(saved_at)
            or saved_at <= 0
            or not isinstance(result, dict)
            or str(result.get("title") or "") != str(section.get("title") or "")
            or str(result.get("content") or "") != str(section.get("content") or "")
            or expected_route.get("chapter_index") != index + 1
            or str(result.get("model_slot") or "").strip()
            != str(expected_route.get("slot") or "").strip()
            or str(result.get("provider") or "").strip().lower()
            != str(expected_route.get("provider") or "").strip().lower()
            or str(result.get("model") or "").strip()
            != str(expected_route.get("model") or "").strip()
            or str(section.get("model_slot") or "").strip()
            != str(expected_route.get("slot") or "").strip()
            or str(section.get("provider") or "").strip().lower()
            != str(expected_route.get("provider") or "").strip().lower()
            or str(section.get("model") or "").strip()
            != str(expected_route.get("model") or "").strip()
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_CHECKPOINT_INCOMPLETE", "正式来源检查点正文不匹配"
            )
    return checkpoint, snapshot


def _structural_quality_receipt_valid(
    value: Any,
    *,
    docx_sha256: str,
    docx_path: Path,
    figure_manifest: Mapping[str, Any],
) -> bool:
    if not isinstance(value, Mapping):
        return False
    claimed = str(value.get("decision_digest") or "").strip().lower()
    material = {
        key: item
        for key, item in value.items()
        if key not in {"decision_digest", "created_at", "receipt", "docx"}
    }
    expected_fields = {
        "schema",
        "created_at",
        "status",
        "docx",
        "docx_sha256",
        "visible_chars",
        "paragraph_count",
        "heading_count",
        "table_count",
        "section_metrics",
        "section_story_references",
        "body_style",
        "word_fields",
        "figure_delivery",
        "package_integrity",
        "hard_failures",
        "warnings",
        "decision_digest",
    }
    section_metrics = value.get("section_metrics")
    story_references = value.get("section_story_references")
    body_style = value.get("body_style")
    word_fields = value.get("word_fields")
    figure_delivery = value.get("figure_delivery")
    package_integrity = value.get("package_integrity")

    def finite_number(raw: Any, *, positive: bool = False) -> bool:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return False
        number = float(raw)
        return math.isfinite(number) and (number > 0 if positive else number >= 0)

    def path_matches(raw: Any, expected: Path) -> bool:
        try:
            candidate = Path(os.path.abspath(os.fspath(str(raw or ""))))
            info = os.lstat(candidate)
            _capture_directory_chain(
                candidate.parent,
                code="HOLD_SOURCE_OUTPUT_UNTRUSTED",
            )
            return (
                candidate == expected
                and stat.S_ISREG(info.st_mode)
                and not stat.S_ISLNK(info.st_mode)
            )
        except (AcceptanceError, OSError, RuntimeError, ValueError):
            return False

    section_rows_valid = bool(
        isinstance(section_metrics, list)
        and section_metrics
        and all(
            isinstance(row, Mapping)
            and set(row)
            == {"section", "width_cm", "height_cm", "margins_cm", "orientation"}
            and row.get("section") == index
            and finite_number(row.get("width_cm"), positive=True)
            and finite_number(row.get("height_cm"), positive=True)
            and row.get("orientation") in {"portrait", "landscape"}
            and isinstance(row.get("margins_cm"), Mapping)
            and set(row["margins_cm"]) == {"top", "right", "bottom", "left"}
            and all(finite_number(row["margins_cm"].get(side)) for side in row["margins_cm"])
            for index, row in enumerate(section_metrics, start=1)
        )
    )
    story_rows_valid = bool(
        isinstance(story_references, list)
        and isinstance(section_metrics, list)
        and len(story_references) == len(section_metrics)
        and all(
            isinstance(row, Mapping)
            and set(row)
            == {
                "section",
                "header_types",
                "footer_types",
                "default_header",
                "default_footer",
            }
            and row.get("section") == index
            and isinstance(row.get("header_types"), list)
            and isinstance(row.get("footer_types"), list)
            and row.get("header_types")
            == sorted({str(item) for item in row.get("header_types") or []})
            and row.get("footer_types")
            == sorted({str(item) for item in row.get("footer_types") or []})
            and row.get("default_header") is True
            and row.get("default_footer") is True
            and "default" in row.get("header_types", [])
            and "default" in row.get("footer_types", [])
            for index, row in enumerate(story_references, start=1)
        )
    )
    try:
        _parse_utc_timestamp(value.get("created_at"))
        return bool(
            set(value) == expected_fields
            and value.get("schema") == "zhifei.docx_structural_quality.v1"
            and value.get("status") == "pass"
            and path_matches(value.get("docx"), docx_path)
            and str(value.get("docx_sha256") or "").strip().lower()
            == docx_sha256
            and value.get("hard_failures") == []
            and isinstance(value.get("warnings"), list)
            and all(isinstance(item, Mapping) for item in value.get("warnings", []))
            and isinstance(value.get("visible_chars"), int)
            and not isinstance(value.get("visible_chars"), bool)
            and value.get("visible_chars", 0) > 0
            and isinstance(value.get("paragraph_count"), int)
            and not isinstance(value.get("paragraph_count"), bool)
            and value.get("paragraph_count", 0) > 0
            and isinstance(value.get("heading_count"), int)
            and not isinstance(value.get("heading_count"), bool)
            and value.get("heading_count", 0) > 0
            and isinstance(value.get("table_count"), int)
            and not isinstance(value.get("table_count"), bool)
            and value.get("table_count", -1) >= 0
            and section_rows_valid
            and story_rows_valid
            and isinstance(body_style, Mapping)
            and set(body_style)
            == {
                "font",
                "size_pt",
                "line_spacing_pt",
                "first_line_chars",
                "space_before_twips",
                "space_after_twips",
            }
            and bool(str(body_style.get("font") or "").strip())
            and finite_number(body_style.get("size_pt"), positive=True)
            and (
                body_style.get("line_spacing_pt") is None
                or finite_number(body_style.get("line_spacing_pt"), positive=True)
            )
            and str(body_style.get("first_line_chars") or "") == "200"
            and str(body_style.get("space_before_twips") or "0") == "0"
            and str(body_style.get("space_after_twips") or "0") == "0"
            and isinstance(word_fields, Mapping)
            and set(word_fields) == {"toc", "page", "numpages", "update_on_open"}
            and all(word_fields.get(field) is True for field in word_fields)
            and isinstance(figure_delivery, Mapping)
            and set(figure_delivery)
            == {"delivery_allowed", "figure_count", "decision_digest"}
            and figure_delivery.get("delivery_allowed") is True
            and figure_delivery.get("figure_count") == figure_manifest.get("figure_count")
            and str(figure_delivery.get("decision_digest") or "")
            == str(figure_manifest.get("decision_digest") or "")
            and isinstance(package_integrity, Mapping)
            and set(package_integrity)
            == {
                "invalid_xml",
                "duplicate_relationship_ids",
                "dangling_relationships",
                "duplicate_bookmark_ids",
                "duplicate_bookmark_names",
                "custom_parts",
            }
            and all(package_integrity.get(field) == [] for field in package_integrity)
            and _SHA256_RE.fullmatch(claimed) is not None
            and claimed == canonical_digest(material)
        )
    except (AcceptanceError, TypeError, ValueError):
        return False


def _visual_quality_receipt_valid(
    value: Any,
    *,
    docx_sha256: str,
    docx_path: Path,
    pdf_path: Path,
    receipt_path: Path,
    preview_dir_path: Path,
) -> bool:
    if not isinstance(value, Mapping):
        return False
    claimed = str(value.get("decision_digest") or "").strip().lower()
    material = {
        key: item
        for key, item in value.items()
        if key
        not in {
            "created_at",
            "decision_digest",
            "docx",
            "pdf",
            "preview_dir",
            "receipt",
        }
    }
    page_count = value.get("page_count")
    page_metrics = value.get("page_metrics")
    expected_fields = {
        "schema",
        "created_at",
        "status",
        "docx",
        "docx_sha256",
        "pdf",
        "pdf_sha256",
        "preview_dir",
        "receipt",
        "page_count",
        "page_metrics",
        "blank_pages",
        "sparse_pages",
        "sparse_page_budget",
        "orphan_heading_pages",
        "edge_clipping_risk_pages",
        "sparse_page_streaks",
        "page_geometry_outliers",
        "cjk_glyph_integrity",
        "hard_failures",
        "warnings",
        "decision_digest",
    }

    def finite_number(raw: Any, *, minimum: float = 0.0) -> bool:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return False
        number = float(raw)
        return math.isfinite(number) and number >= minimum

    def path_matches(raw: Any, expected: Path) -> bool:
        try:
            candidate = Path(os.path.abspath(os.fspath(str(raw or ""))))
            info = os.lstat(candidate)
            _capture_directory_chain(
                candidate.parent,
                code="HOLD_SOURCE_OUTPUT_UNTRUSTED",
            )
            return (
                candidate == expected
                and stat.S_ISREG(info.st_mode)
                and not stat.S_ISLNK(info.st_mode)
            )
        except (AcceptanceError, OSError, RuntimeError, ValueError):
            return False

    def directory_matches(raw: Any, expected: Path) -> bool:
        try:
            candidate = Path(os.path.abspath(os.fspath(str(raw or ""))))
            info = os.lstat(candidate)
            _capture_directory_chain(
                candidate,
                code="HOLD_SOURCE_OUTPUT_UNTRUSTED",
            )
            return (
                candidate == expected
                and stat.S_ISDIR(info.st_mode)
                and not stat.S_ISLNK(info.st_mode)
            )
        except (AcceptanceError, OSError, RuntimeError, ValueError):
            return False

    metric_fields = {
        "page",
        "text_chars",
        "ink_ratio",
        "edge_ink_ratio",
        "pixel_width",
        "pixel_height",
        "blank",
        "sparse",
        "orphan_heading",
        "edge_clipping_risk",
    }
    metrics_valid = bool(
        isinstance(page_metrics, list)
        and isinstance(page_count, int)
        and not isinstance(page_count, bool)
        and page_count > 0
        and len(page_metrics) == page_count
        and all(
            isinstance(row, Mapping)
            and set(row) == metric_fields
            and row.get("page") == index
            and isinstance(row.get("text_chars"), int)
            and not isinstance(row.get("text_chars"), bool)
            and row.get("text_chars", -1) >= 0
            and isinstance(row.get("pixel_width"), int)
            and not isinstance(row.get("pixel_width"), bool)
            and row.get("pixel_width", 0) > 0
            and isinstance(row.get("pixel_height"), int)
            and not isinstance(row.get("pixel_height"), bool)
            and row.get("pixel_height", 0) > 0
            and finite_number(row.get("ink_ratio"))
            and float(row.get("ink_ratio")) <= 1.0
            and finite_number(row.get("edge_ink_ratio"))
            and float(row.get("edge_ink_ratio")) <= 1.0
            and all(
                isinstance(row.get(field), bool)
                for field in (
                    "blank",
                    "sparse",
                    "orphan_heading",
                    "edge_clipping_risk",
                )
            )
            for index, row in enumerate(page_metrics, start=1)
        )
    )
    expected_decision = (
        evaluate_page_quality([dict(row) for row in page_metrics])
        if metrics_valid
        else {}
    )
    glyph = value.get("cjk_glyph_integrity")
    glyph_fields = {
        "status",
        "inspected_glyphs",
        "empty_glyphs",
        "empty_glyph_ratio",
        "unique_cjk_characters",
        "unique_glyph_shapes",
        "shape_retention",
        "largest_shape_collision",
        "hard_failures",
    }
    try:
        _parse_utc_timestamp(value.get("created_at"))
        return bool(
            set(value) == expected_fields
            and value.get("schema") == "zhifei.docx_visual_quality.v1"
            and value.get("status") == "pass"
            and path_matches(value.get("docx"), docx_path)
            and path_matches(value.get("pdf"), pdf_path)
            and path_matches(value.get("receipt"), receipt_path)
            and directory_matches(value.get("preview_dir"), preview_dir_path)
            and str(value.get("docx_sha256") or "").strip().lower()
            == docx_sha256
            and _SHA256_RE.fullmatch(
                str(value.get("pdf_sha256") or "").strip().lower()
            )
            is not None
            and value.get("hard_failures") == []
            and isinstance(value.get("warnings"), list)
            and metrics_valid
            and all(
                value.get(field) == expected_decision.get(field)
                for field in (
                    "status",
                    "page_count",
                    "blank_pages",
                    "sparse_pages",
                    "sparse_page_budget",
                    "orphan_heading_pages",
                    "edge_clipping_risk_pages",
                    "sparse_page_streaks",
                    "page_geometry_outliers",
                    "hard_failures",
                    "warnings",
                )
            )
            and isinstance(glyph, Mapping)
            and set(glyph) == glyph_fields
            and glyph.get("status") == "pass"
            and glyph.get("hard_failures") == []
            and all(
                isinstance(glyph.get(field), int)
                and not isinstance(glyph.get(field), bool)
                and glyph.get(field, -1) >= 0
                for field in (
                    "inspected_glyphs",
                    "empty_glyphs",
                    "unique_cjk_characters",
                    "unique_glyph_shapes",
                    "largest_shape_collision",
                )
            )
            and glyph.get("empty_glyphs", 0) <= glyph.get("inspected_glyphs", 0)
            and finite_number(glyph.get("empty_glyph_ratio"))
            and float(glyph.get("empty_glyph_ratio")) <= 1.0
            and finite_number(glyph.get("shape_retention"))
            and _SHA256_RE.fullmatch(claimed) is not None
            and claimed == canonical_digest(material)
        )
    except (AcceptanceError, TypeError, ValueError):
        return False


def _render_attempt_evidence_valid(
    value: Any,
    *,
    job_id: str,
    variant_id: int,
    route: Mapping[str, Any],
) -> bool:
    if not isinstance(value, Mapping):
        return False
    expected_fields = {
        "schema_version",
        "execution_control_schema_version",
        "role",
        "slot",
        "provider",
        "model",
        "job_id",
        "variant",
        "model_attempts_before",
        "model_attempts_after",
        "attempt_count",
        "provider_attempts_before",
        "provider_attempts_after",
        "provider_attempt_count",
        "evidence_digest",
    }
    claimed = str(value.get("evidence_digest") or "").strip().lower()
    core = {key: item for key, item in value.items() if key != "evidence_digest"}
    integer_fields = (
        "model_attempts_before",
        "model_attempts_after",
        "attempt_count",
        "provider_attempts_before",
        "provider_attempts_after",
        "provider_attempt_count",
    )
    try:
        return bool(
            set(value) == expected_fields
            and value.get("schema_version")
            == "document-render-attempt-evidence-v1"
            and value.get("execution_control_schema_version")
            == "execution-control-v1"
            and value.get("role") == "document_render"
            and value.get("job_id") == job_id
            and value.get("variant") == variant_id
            and all(
                str(value.get(field) or "").strip()
                == str(route.get(field) or "").strip()
                for field in ("slot", "provider", "model")
            )
            and all(
                isinstance(value.get(field), int)
                and not isinstance(value.get(field), bool)
                and int(value.get(field)) >= 0
                for field in integer_fields
            )
            and value.get("attempt_count")
            == value.get("model_attempts_after")
            - value.get("model_attempts_before")
            and value.get("provider_attempt_count")
            == value.get("provider_attempts_after")
            - value.get("provider_attempts_before")
            and value.get("attempt_count", 0) > 0
            and value.get("provider_attempt_count", 0) > 0
            and value.get("attempt_count") == value.get("provider_attempt_count")
            and _SHA256_RE.fullmatch(claimed) is not None
            and claimed == canonical_digest(core)
        )
    except (TypeError, ValueError):
        return False


def _artifact_bundle(
    *,
    result: dict[str, Any],
    release_root: Path,
    workspace_root: Path,
    expected_variants: list[dict[str, Any]],
    job_id: str,
    provider_admission: Mapping[str, Any],
    job_execution_identity: Mapping[str, Any],
    compliance_registry_authority: Mapping[str, Any],
) -> tuple[
    list[FileWitness | DirectoryStateWitness],
    dict[str, Any],
    list[dict[str, Any]],
]:
    variant_count = len(expected_variants)
    required_lists = (
        "source_docx",
        "docx",
        "professional_docx",
        "professional_json",
        "professional_render_receipt",
        "compare_docx",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    )
    witnesses: list[FileWitness | DirectoryStateWitness] = []
    by_key: dict[str, list[FileWitness]] = {}
    projected: dict[str, Any] = {}
    for key in required_lists:
        values = result.get(key)
        if not isinstance(values, list) or len(values) != variant_count:
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源制品集合不完整"
            )
        digests: list[str] = []
        key_witnesses: list[FileWitness] = []
        for value in values:
            witness = _trusted_build_snapshot(
                value,
                release_root=release_root,
                workspace_root=workspace_root,
            )
            witnesses.append(witness)
            key_witnesses.append(witness)
            digests.append(witness.sha256)
        by_key[key] = key_witnesses
        projected[key] = digests
    source_json_witness = _trusted_build_snapshot(
        result.get("json"),
        release_root=release_root,
        workspace_root=workspace_root,
        max_bytes=_MAX_JSON_BYTES,
    )
    witnesses.append(source_json_witness)
    projected["source_json"] = source_json_witness.sha256
    package_projection: dict[str, list[dict[str, Any]]] = {}
    for key, package_kind in (
        ("source_docx", "docx"),
        ("professional_docx", "docx"),
        ("compare_docx", "docx"),
        ("expert_review_docx", "docx"),
        ("focus_xlsx", "xlsx"),
        ("score_overview_xlsx", "xlsx"),
    ):
        package_projection[key] = []
        for witness in by_key[key]:
            try:
                package = validate_formal_ooxml_artifact(
                    witness.path,
                    artifact_kind=package_kind,
                    expected_size=witness.size,
                    expected_sha256=witness.sha256,
                )
            except FormalArtifactIntegrityError as exc:
                raise AcceptanceError(
                    "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                    "正式来源OOXML制品完整性无效",
                ) from exc
            package_projection[key].append(
                {
                    **package,
                    "witness_compatibility": _validate_ooxml_package(
                        witness,
                        package_kind=package_kind,
                    ),
                }
            )
    projected["ooxml_packages"] = package_projection
    if [row.path for row in by_key["docx"]] != [
        row.path for row in by_key["professional_docx"]
    ]:
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源公开Word与专业Word路径不一致"
        )
    unique_artifact_paths: set[Path] = {source_json_witness.path}
    formal_variants: list[dict[str, Any]] = []
    render_attempt_count = 0
    render_provider_attempts: dict[str, int] = {}
    for key, key_witnesses in by_key.items():
        if key == "docx":
            continue
        for witness in key_witnesses:
            if witness.path in unique_artifact_paths:
                raise AcceptanceError(
                    "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源制品被跨字段或方案复用"
                )
            unique_artifact_paths.add(witness.path)
    receipt_witness = _trusted_build_snapshot(
        result.get("delivery_receipt"),
        release_root=release_root,
        workspace_root=workspace_root,
        max_bytes=_MAX_JSON_BYTES,
    )
    task_receipt = _decode_witness_json(receipt_witness)
    claimed = str(task_receipt.get("decision_digest") or "")
    receipt_variants = task_receipt.get("variants")
    receipt_variant_count = task_receipt.get("variant_count")
    if (
        task_receipt.get("schema") != "zhifei.delivery_receipt.v2"
        or task_receipt.get("status") != "pass"
        or task_receipt.get("delivery_profile") != "sonnet5_professional_word"
        or str(task_receipt.get("job_id") or "") != job_id
        or task_receipt.get("job_execution_identity")
        != dict(job_execution_identity)
        or task_receipt.get("compliance_registry_authority")
        != dict(compliance_registry_authority)
        or isinstance(receipt_variant_count, bool)
        or not isinstance(receipt_variant_count, int)
        or receipt_variant_count != variant_count
        or not isinstance(receipt_variants, list)
        or len(receipt_variants) != variant_count
        or claimed != canonical_delivery_receipt_digest(task_receipt)
        or claimed != str(result.get("delivery_decision_digest") or "")
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源交付回执无效"
        )
    receipt_bindings = {
        "source_docx": "source_docx",
        "professional_docx": "professional_docx",
        "professional_json": "professional_json",
        "professional_render_receipt": "professional_render_receipt",
        "compare_docx": "compare_docx",
        "focus_xlsx": "focus_xlsx",
        "score_overview_xlsx": "score_overview_xlsx",
        "expert_review_docx": "expert_review_docx",
    }
    for index, row in enumerate(receipt_variants, start=1):
        if not isinstance(row, dict) or row.get("variant") != index:
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源交付回执方案身份无效"
            )
        for result_key, receipt_key in receipt_bindings.items():
            artifact = row.get(receipt_key)
            witness = by_key[result_key][index - 1]
            try:
                recorded_path = _trusted_build_lexical_path(
                    (artifact or {}).get("path"),
                    release_root=release_root,
                    workspace_root=workspace_root,
                )
            except (AcceptanceError, OSError, RuntimeError, ValueError):
                recorded_path = Path()
            if (
                not isinstance(artifact, dict)
                or recorded_path != witness.path
                or artifact.get("sha256") != witness.sha256
                or artifact.get("size") != witness.size
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                    "正式来源交付回执未绑定当前制品字节",
                )
        quality_witnesses: dict[str, FileWitness] = {}
        for receipt_key in (
            "structural_quality_receipt",
            "visual_quality_receipt",
            "figure_manifest",
        ):
            artifact = row.get(receipt_key)
            if not isinstance(artifact, dict):
                raise AcceptanceError(
                    "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源质量凭证集合不完整"
                )
            witness = _trusted_build_snapshot(
                artifact.get("path"),
                release_root=release_root,
                workspace_root=workspace_root,
            )
            if (
                artifact.get("sha256") != witness.sha256
                or artifact.get("size") != witness.size
                or witness.path in unique_artifact_paths
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                    "正式来源质量凭证未绑定当前字节",
                )
            unique_artifact_paths.add(witness.path)
            quality_witnesses[receipt_key] = witness
            witnesses.append(witness)
        professional = by_key["professional_docx"][index - 1]
        professional_json_witness = by_key["professional_json"][index - 1]
        render_witness = by_key["professional_render_receipt"][index - 1]
        professional_payload = _decode_witness_json(professional_json_witness)
        render_receipt = _decode_witness_json(render_witness)
        structural_receipt = _decode_witness_json(
            quality_witnesses["structural_quality_receipt"]
        )
        visual_receipt = _decode_witness_json(
            quality_witnesses["visual_quality_receipt"]
        )
        try:
            preview_dir_path = _trusted_build_lexical_path(
                visual_receipt.get("preview_dir"),
                release_root=release_root,
                workspace_root=workspace_root,
            )
            preview_dir_state = _capture_directory_state(
                preview_dir_path,
                code="HOLD_SOURCE_OUTPUT_UNTRUSTED",
            )
        except AcceptanceError as exc:
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                "正式来源预览目录不可信",
            ) from exc
        witnesses.append(preview_dir_state)
        projected.setdefault("preview_directories", []).append(
            {
                "members_digest": preview_dir_state.members_digest,
                "member_count": len(preview_dir_state.members),
            }
        )
        visual_pdf_witness = _trusted_build_snapshot(
            visual_receipt.get("pdf"),
            release_root=release_root,
            workspace_root=workspace_root,
        )
        if (
            visual_pdf_witness.path in unique_artifact_paths
            or visual_pdf_witness.sha256
            != str(visual_receipt.get("pdf_sha256") or "").strip().lower()
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                "正式来源视觉凭证未绑定当前PDF字节",
            )
        _validate_pdf_witness(visual_pdf_witness)
        unique_artifact_paths.add(visual_pdf_witness.path)
        witnesses.append(visual_pdf_witness)
        projected.setdefault("visual_pdf", []).append(visual_pdf_witness.sha256)
        figure_manifest = _decode_witness_json(quality_witnesses["figure_manifest"])
        quality_gate = (
            render_receipt.get("quality_gate")
            if isinstance(render_receipt.get("quality_gate"), dict)
            else {}
        )
        required_quality_gates = {
            "original_preserved",
            "titles_preserved",
            "evidence_not_reduced",
            "tender_style_fields_preserved",
            "export_succeeded",
            "structural_quality_passed",
            "visual_page_quality_passed",
            "no_blank_pages",
            "no_orphan_headings",
        }
        payload_variants = professional_payload.get("variants")
        formal_variant = (
            payload_variants[0]
            if isinstance(payload_variants, list)
            and len(payload_variants) == 1
            and isinstance(payload_variants[0], dict)
            else None
        )
        expected_variant = expected_variants[index - 1]
        document_route = provider_admission.get("document_render")
        formal_routing = (
            formal_variant.get("model_routing")
            if isinstance(formal_variant, dict)
            and isinstance(formal_variant.get("model_routing"), Mapping)
            else {}
        )
        formal_render = (
            formal_variant.get("professional_render")
            if isinstance(formal_variant, dict)
            and isinstance(formal_variant.get("professional_render"), Mapping)
            else {}
        )
        routed_document = (
            formal_routing.get("document_render")
            if isinstance(formal_routing.get("document_render"), Mapping)
            else {}
        )

        def _render_receipt_path(
            field: str,
            *,
            _receipt: dict[str, Any] = render_receipt,
        ) -> Path | None:
            raw = _receipt.get(field)
            raw = raw.get("receipt") if isinstance(raw, dict) else None
            try:
                return _trusted_build_lexical_path(
                    raw,
                    release_root=release_root,
                    workspace_root=workspace_root,
                )
            except (AcceptanceError, OSError, RuntimeError, ValueError):
                return None

        def _render_output_path(
            field: str,
            *,
            _receipt: dict[str, Any] = render_receipt,
        ) -> Path | None:
            try:
                return _trusted_build_lexical_path(
                    _receipt.get(field),
                    release_root=release_root,
                    workspace_root=workspace_root,
                )
            except (AcceptanceError, OSError, RuntimeError, ValueError):
                return None

        def _summary_output_path(
            summary: Mapping[str, Any],
            field: str,
        ) -> Path | None:
            try:
                return _trusted_build_lexical_path(
                    summary.get(field),
                    release_root=release_root,
                    workspace_root=workspace_root,
                )
            except (AcceptanceError, OSError, RuntimeError, ValueError):
                return None

        expected_sections = (
            expected_variant.get("sections")
            if isinstance(expected_variant.get("sections"), list)
            else []
        )
        formal_sections = (
            formal_variant.get("sections")
            if isinstance(formal_variant, dict)
            and isinstance(formal_variant.get("sections"), list)
            else []
        )
        section_provenance_valid = bool(
            len(expected_sections) == len(formal_sections)
            and expected_sections
            and all(
                isinstance(source_section, Mapping)
                and isinstance(final_section, Mapping)
                and str(final_section.get("title") or "")
                == str(source_section.get("title") or "")
                and str(final_section.get("original_content") or "")
                == str(source_section.get("content") or "")
                and str(final_section.get("content") or "").strip()
                and all(
                    str(final_section.get(field) or "").strip()
                    == str(source_section.get(field) or "").strip()
                    for field in ("provider", "model", "model_slot")
                )
                and isinstance(final_section.get("professional_render"), Mapping)
                and final_section["professional_render"].get("status") == "refined"
                for source_section, final_section in zip(
                    expected_sections,
                    formal_sections,
                    strict=True,
                )
            )
        )
        render_attempt = render_receipt.get("render_attempt_evidence")
        structural_summary = (
            render_receipt.get("structural_quality")
            if isinstance(render_receipt.get("structural_quality"), Mapping)
            else {}
        )
        visual_summary = (
            render_receipt.get("visual_quality")
            if isinstance(render_receipt.get("visual_quality"), Mapping)
            else {}
        )
        if (
            render_receipt.get("schema")
            != "zhifei.professional_document_render.v1"
            or str(render_receipt.get("job_id") or "") != job_id
            or render_receipt.get("variant") != index
            or professional_payload.get("professional_render_source_variant")
            != index
            or professional_payload.get("generation_release_identity")
            != expected_variant.get("generation_release_identity")
            or professional_payload.get("compliance_registry_authority")
            != dict(compliance_registry_authority)
            or not isinstance(formal_variant, dict)
            or formal_variant.get("variant_id") != index
            or formal_variant.get("source_input_receipt")
            != expected_variant.get("source_input_receipt")
            or formal_variant.get("generation_release_identity")
            != expected_variant.get("generation_release_identity")
            or formal_variant.get("compliance_registry_authority")
            != dict(compliance_registry_authority)
            or str(
                (
                    formal_routing.get("provider_admission")
                    if isinstance(
                        formal_routing.get("provider_admission"), Mapping
                    )
                    else {}
                ).get("public_digest")
                or ""
            ).strip().lower()
            != str(provider_admission.get("public_digest") or "").strip().lower()
            or not isinstance(document_route, Mapping)
            or {
                field: str(routed_document.get(field) or "").strip()
                for field in ("slot", "provider", "model")
            }
            != {
                field: str(document_route.get(field) or "").strip()
                for field in ("slot", "provider", "model")
            }
            or str(formal_render.get("provider") or "").strip()
            != str(document_route.get("provider") or "").strip()
            or str(formal_render.get("model_id") or "").strip()
            != str(document_route.get("model") or "").strip()
            or str(render_receipt.get("provider") or "").strip()
            != str(document_route.get("provider") or "").strip()
            or str(render_receipt.get("model_id") or "").strip()
            != str(document_route.get("model") or "").strip()
            or str(render_receipt.get("slot") or "").strip()
            != str(document_route.get("slot") or "").strip()
            or render_receipt.get("role") != "document_render"
            or _render_output_path("source_json") != source_json_witness.path
            or str(render_receipt.get("source_json_sha256") or "")
            != source_json_witness.sha256
            or _render_output_path("source_docx")
            != by_key["source_docx"][index - 1].path
            or str(render_receipt.get("source_docx_sha256") or "")
            != by_key["source_docx"][index - 1].sha256
            or _render_output_path("professional_docx") != professional.path
            or _render_output_path("professional_json")
            != professional_json_witness.path
            or str(render_receipt.get("professional_json_sha256") or "")
            != professional_json_witness.sha256
            or render_receipt.get("section_count")
            != len(formal_variant.get("sections") or [])
            or render_receipt.get("source_char_count")
            != sum(
                len(str(section.get("content") or ""))
                for section in expected_sections
                if isinstance(section, Mapping)
            )
            or render_receipt.get("professional_char_count")
            != sum(
                len(str(section.get("content") or ""))
                for section in formal_sections
                if isinstance(section, Mapping)
            )
            or not section_provenance_valid
            or str(render_receipt.get("professional_docx_sha256") or "")
            != professional.sha256
            or str(render_receipt.get("receipt_digest") or "")
            != canonical_digest(
                {
                    key: value
                    for key, value in render_receipt.items()
                    if key != "receipt_digest"
                }
            )
            or not _render_attempt_evidence_valid(
                render_attempt,
                job_id=job_id,
                variant_id=index,
                route=document_route,
            )
            or any(quality_gate.get(field) is not True for field in required_quality_gates)
            or _render_receipt_path("structural_quality")
            != quality_witnesses["structural_quality_receipt"].path
            or _render_receipt_path("visual_quality")
            != quality_witnesses["visual_quality_receipt"].path
            or not _structural_quality_receipt_valid(
                structural_receipt,
                docx_sha256=professional.sha256,
                docx_path=professional.path,
                figure_manifest=figure_manifest,
            )
            or not _visual_quality_receipt_valid(
                visual_receipt,
                docx_sha256=professional.sha256,
                docx_path=professional.path,
                pdf_path=visual_pdf_witness.path,
                receipt_path=quality_witnesses["visual_quality_receipt"].path,
                preview_dir_path=preview_dir_state.path,
            )
            or structural_summary.get("status") != "pass"
            or set(structural_summary)
            != {
                "receipt",
                "receipt_sha256",
                "status",
                "hard_failures",
                "docx_sha256",
                "decision_digest",
                "heading_count",
                "table_count",
                "word_fields",
                "body_style",
                "section_metrics",
                "figure_delivery",
            }
            or structural_summary.get("hard_failures") != []
            or str(structural_summary.get("docx_sha256") or "")
            != professional.sha256
            or str(structural_summary.get("decision_digest") or "")
            != str(structural_receipt.get("decision_digest") or "")
            or str(structural_summary.get("receipt_sha256") or "")
            != quality_witnesses["structural_quality_receipt"].sha256
            or structural_summary.get("heading_count")
            != structural_receipt.get("heading_count")
            or structural_summary.get("table_count")
            != structural_receipt.get("table_count")
            or structural_summary.get("word_fields")
            != structural_receipt.get("word_fields")
            or structural_summary.get("body_style")
            != structural_receipt.get("body_style")
            or structural_summary.get("section_metrics")
            != structural_receipt.get("section_metrics")
            or structural_summary.get("figure_delivery")
            != structural_receipt.get("figure_delivery")
            or visual_summary.get("status") != "pass"
            or set(visual_summary)
            != {
                "receipt",
                "receipt_sha256",
                "status",
                "hard_failures",
                "docx_sha256",
                "decision_digest",
                "page_count",
                "blank_pages",
                "sparse_pages",
                "orphan_heading_pages",
                "edge_clipping_risk_pages",
                "pdf",
                "pdf_sha256",
                "preview_dir",
            }
            or visual_summary.get("hard_failures") != []
            or str(visual_summary.get("docx_sha256") or "")
            != professional.sha256
            or str(visual_summary.get("decision_digest") or "")
            != str(visual_receipt.get("decision_digest") or "")
            or str(visual_summary.get("receipt_sha256") or "")
            != quality_witnesses["visual_quality_receipt"].sha256
            or str(visual_summary.get("pdf_sha256") or "")
            != visual_pdf_witness.sha256
            or visual_summary.get("page_count")
            != visual_receipt.get("page_count")
            or visual_summary.get("blank_pages")
            != visual_receipt.get("blank_pages")
            or visual_summary.get("sparse_pages")
            != visual_receipt.get("sparse_pages")
            or visual_summary.get("orphan_heading_pages")
            != visual_receipt.get("orphan_heading_pages")
            or visual_summary.get("edge_clipping_risk_pages")
            != visual_receipt.get("edge_clipping_risk_pages")
            or _summary_output_path(visual_summary, "pdf")
            != visual_pdf_witness.path
            or _summary_output_path(visual_summary, "preview_dir")
            != preview_dir_state.path
            or figure_manifest.get("schema_version")
            != "docx_figure_delivery.v2"
            or figure_manifest.get("status") != "pass"
            or figure_manifest.get("delivery_allowed") is not True
            or str(figure_manifest.get("decision_digest") or "")
            != canonical_digest(
                {
                    key: value
                    for key, value in figure_manifest.items()
                    if key != "decision_digest"
                }
            )
            or quality_witnesses["figure_manifest"].path
            != professional.path.with_suffix(".figure_manifest.json")
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_OUTPUT_UNTRUSTED",
                "正式来源专业渲染与质量凭证语义无效",
            )
        render_attempt_count += int(render_attempt["attempt_count"])
        render_provider = str(render_attempt["provider"])
        render_provider_attempts[render_provider] = (
            render_provider_attempts.get(render_provider, 0)
            + int(render_attempt["provider_attempt_count"])
        )
        formal_variants.append(formal_variant)
    witnesses.append(receipt_witness)
    return (
        witnesses,
        {
            "artifact_count": len(witnesses),
            "delivery_receipt_digest": claimed,
            "artifact_set_digest": canonical_digest(projected),
            "render_attempt_count": render_attempt_count,
            "render_provider_attempts": dict(sorted(render_provider_attempts.items())),
        },
        formal_variants,
    )


def _expected_generation_release(
    release_identity: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "autoplan-generation-release-v1",
        "system_id": str(release_identity.get("system_id") or "").strip(),
        "release_id": str(release_identity.get("release_id") or "").strip(),
        "manifest_digest": str(
            release_identity.get("manifest_digest") or ""
        ).strip(),
        "source_digest": str(release_identity.get("source_digest") or "").strip(),
        "runtime_digest": str(
            release_identity.get("runtime_digest") or ""
        ).strip(),
        "release_root": str(release_identity.get("release_root") or "").strip(),
        "runtime_mode": "sealed_release",
        "release_managed": True,
    }


def _generation_release_matches(value: Any, expected: Mapping[str, Any]) -> bool:
    return isinstance(value, Mapping) and dict(value) == dict(expected)


def _terminal_job_evidence_valid(job: Mapping[str, Any]) -> bool:
    last_attempt_id = str(job.get("last_attempt_id") or "").strip()
    last_owner_instance_id = str(job.get("last_owner_instance_id") or "").strip()
    last_job_revision = job.get("last_job_revision")
    if (
        job.get("status") != "succeeded"
        or job.get("attempt_id") is not None
        or job.get("owner_instance_id") is not None
        or job.get("error") is not None
        or _EXECUTION_ID_RE.fullmatch(last_attempt_id) is None
        or _EXECUTION_ID_RE.fullmatch(last_owner_instance_id) is None
        or isinstance(last_job_revision, bool)
        or not isinstance(last_job_revision, int)
        or last_job_revision <= 0
        or job.get("lease_revoke_reason") != "transition:succeeded"
        or isinstance(job.get("revision"), bool)
        or not isinstance(job.get("revision"), int)
        or int(job.get("revision")) < 3
        or last_job_revision > int(job.get("revision"))
    ):
        return False
    try:
        created_at = float(job.get("created_at"))
        updated_at = float(job.get("updated_at"))
        acquired_at = float(job.get("lease_acquired_at"))
        revoked_at = float(job.get("lease_revoked_at"))
    except (OverflowError, TypeError, ValueError):
        return False
    return bool(
        all(
            math.isfinite(value) and value > 0
            for value in (created_at, updated_at, acquired_at, revoked_at)
        )
        and created_at <= acquired_at <= revoked_at <= updated_at
    )


def _execution_evidence_valid(
    execution: Any,
    *,
    event_projection: Mapping[str, Any],
    artifact_projection: Mapping[str, Any],
) -> bool:
    if not isinstance(execution, Mapping):
        return False
    limits = execution.get("limits")
    usage = execution.get("usage")
    expected_limits = {
        "max_concurrency",
        "max_model_attempts",
        "max_input_chars",
        "max_requested_output_tokens",
    }
    expected_usage = {
        "model_attempts",
        "input_chars",
        "requested_output_tokens",
        "actual_input_tokens",
        "actual_uncached_input_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "cache_hit_ratio",
        "actual_output_tokens",
        "actual_output_chars",
        "active",
        "peak_active",
        "provider_attempts",
    }
    if (
        execution.get("schema_version") != "execution-control-v1"
        or execution.get("cancelled") is not False
        or not isinstance(limits, Mapping)
        or set(limits) != expected_limits
        or any(
            isinstance(limits.get(field), bool)
            or not isinstance(limits.get(field), int)
            or int(limits.get(field)) <= 0
            for field in expected_limits
        )
        or not isinstance(usage, Mapping)
        or set(usage) != expected_usage
        or not isinstance(usage.get("provider_attempts"), Mapping)
    ):
        return False
    integer_fields = expected_usage - {"cache_hit_ratio", "provider_attempts"}
    if any(
        isinstance(usage.get(field), bool)
        or not isinstance(usage.get(field), int)
        or int(usage.get(field)) < 0
        for field in integer_fields
    ):
        return False
    provider_attempts = usage["provider_attempts"]
    if any(
        not str(provider).strip()
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count <= 0
        for provider, count in provider_attempts.items()
    ):
        return False
    try:
        cache_ratio = float(usage.get("cache_hit_ratio"))
        elapsed = float(execution.get("elapsed_seconds"))
    except (OverflowError, TypeError, ValueError):
        return False
    model_attempts = int(usage["model_attempts"])
    minimum_attempts = int(event_projection.get("provider_attempt_count") or 0) + int(
        artifact_projection.get("render_attempt_count") or 0
    )
    if (
        not math.isfinite(cache_ratio)
        or not 0.0 <= cache_ratio <= 1.0
        or not math.isfinite(elapsed)
        or elapsed <= 0
        or usage.get("active") != 0
        or int(usage.get("peak_active") or 0) <= 0
        or model_attempts != sum(int(value) for value in provider_attempts.values())
        or model_attempts < minimum_attempts
        or int(usage.get("input_chars") or 0) <= 0
        or int(usage.get("requested_output_tokens") or 0) <= 0
        or int(usage.get("actual_output_chars") or 0) <= 0
    ):
        return False
    required_provider_counts: dict[str, int] = {}
    for mapping in (
        event_projection.get("provider_attempts"),
        artifact_projection.get("render_provider_attempts"),
    ):
        if not isinstance(mapping, Mapping):
            return False
        for provider, count in mapping.items():
            required_provider_counts[str(provider)] = (
                required_provider_counts.get(str(provider), 0) + int(count)
            )
    return all(
        int(provider_attempts.get(provider) or 0) >= required
        for provider, required in required_provider_counts.items()
    )


def _compliance_preflight_events_valid(
    *,
    events: list[dict[str, Any]],
    variant_ids: set[int],
    registry_authority: Mapping[str, Any],
) -> bool:
    if len(events) != len(variant_ids):
        return False
    seen: set[int] = set()
    for event in events:
        raw_variant_id = event.get("variant_id")
        if (
            isinstance(raw_variant_id, bool)
            or not isinstance(raw_variant_id, int)
            or raw_variant_id <= 0
            or raw_variant_id in seen
            or event.get("ready") is not True
            or event.get("authority_digest")
            != registry_authority["authority_digest"]
            or event.get("official_registry_sha256")
            != registry_authority["registry_sha256"]
            or isinstance(event.get("verified_standard_count"), bool)
            or not isinstance(event.get("verified_standard_count"), int)
            or int(event.get("verified_standard_count") or 0) <= 0
        ):
            return False
        seen.add(raw_variant_id)
    return seen == variant_ids


def _current_attempt_event_slice(
    *,
    events: list[dict[str, Any]],
    attempt_id: str,
    owner_instance_id: str,
    job_revision: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return the terminal attempt and its pre-provider compliance preflights."""

    def belongs_to_current_attempt(row: Mapping[str, Any]) -> bool:
        return (
            str(row.get("attempt_id") or "").strip() == attempt_id
            and str(row.get("owner_instance_id") or "").strip()
            == owner_instance_id
            and row.get("job_revision") == job_revision
        )

    started_indexes = [
        index
        for index, row in enumerate(events)
        if row.get("event") == "job_started"
        and belongs_to_current_attempt(row)
    ]
    succeeded_indexes = [
        index
        for index, row in enumerate(events)
        if row.get("event") == "job_succeeded"
        and belongs_to_current_attempt(row)
    ]
    if (
        len(started_indexes) != 1
        or len(succeeded_indexes) != 1
        or started_indexes[0] >= succeeded_indexes[0]
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_JOB_UNTRUSTED",
            "正式来源当前执行批次缺少唯一开始或成功事件",
        )
    current_attempt_events = events[
        started_indexes[0] : succeeded_indexes[0] + 1
    ]
    if any(
        not belongs_to_current_attempt(row) for row in current_attempt_events
    ):
        raise AcceptanceError(
            "HOLD_SOURCE_JOB_UNTRUSTED",
            "正式来源当前执行批次混入其他任务谱系事件",
        )
    admission_started_indexes = [
        index
        for index, row in enumerate(current_attempt_events)
        if row.get("event") == "provider_admission_started"
    ]
    if len(admission_started_indexes) != 1:
        raise AcceptanceError(
            "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
            "正式来源当前执行批次缺少唯一供应商准入开始事件",
        )
    admission_started_index = admission_started_indexes[0]
    preflight_rows = [
        row
        for index, row in enumerate(current_attempt_events)
        if row.get("event") == "compliance_preflight"
        and 0 < index < admission_started_index
    ]
    current_lineage_preflight_count = sum(
        row.get("event") == "compliance_preflight"
        and belongs_to_current_attempt(row)
        for row in events
    )
    if len(preflight_rows) != current_lineage_preflight_count:
        raise AcceptanceError(
            "HOLD_SOURCE_JOB_UNTRUSTED",
            "正式来源规范预检不在任务开始与供应商准入之间",
        )
    return current_attempt_events, preflight_rows


def _candidate_source(
    *,
    jobs: list[tuple[FileSnapshot, dict[str, Any]]],
    project_id: str,
    tender: dict[str, Any],
    boq: dict[str, Any],
    release_identity: Mapping[str, Any],
    release_root: Path,
    workspace_root: Path,
    requested_job_id: str | None,
    events_state: DirectoryStateWitness | None = None,
    provider_admission_snapshot: FileSnapshot | None = None,
    compliance_registry_authority: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    candidates: list[tuple[float, str, int, dict[str, Any]]] = []
    requested_rejection: str | None = None
    expected_generation_release = _expected_generation_release(release_identity)
    expected_registry_authority = validate_registry_authority_projection(
        compliance_registry_authority
    )
    try:
        if (
            provider_admission_snapshot is None
            or provider_admission_snapshot.mode != 0o600
        ):
            raise AcceptanceError(
                "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                "当前持久化供应商准入回执权限不可信",
            )
        durable_provider_admission = _validated_internal_provider_admission(
            _decode_json(provider_admission_snapshot)
        )
        durable_provider_admission["file_sha256"] = (
            provider_admission_snapshot.sha256
        )
    except AcceptanceError:
        durable_provider_admission = None
    for job_snapshot, job in jobs:
        stem_job_id = job_snapshot.path.stem
        internal_job_id = str(job.get("job_id") or "").strip()
        if requested_job_id and stem_job_id != requested_job_id:
            continue
        if internal_job_id != stem_job_id:
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_JOB_UNTRUSTED"
            continue
        job_id = stem_job_id
        payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
        result = job.get("result") if isinstance(job.get("result"), dict) else {}
        agent_runtime = (
            job.get("agent_runtime")
            if isinstance(job.get("agent_runtime"), dict)
            else {}
        )
        attempt_id = str(job.get("last_attempt_id") or "").strip()
        owner_instance_id = str(job.get("last_owner_instance_id") or "").strip()
        job_revision = job.get("last_job_revision")
        expected_job_execution_identity = {
            "job_id": job_id,
            "attempt_id": attempt_id,
            "owner_instance_id": owner_instance_id,
            "job_revision": job_revision,
        }
        if (
            not _terminal_job_evidence_valid(job)
            or str(payload.get("project_id") or "").strip() != project_id
            or payload.get("delivery_scope") != "document"
            or payload.get("dry_run") is not False
            or payload.get("resume_from_job_id") not in {None, ""}
            or result.get("delivery_ready") is not True
            or result.get("validation_scope") != "document"
            or result.get("delivery_profile") != "sonnet5_professional_word"
            or not _generation_release_matches(
                result.get("generation_release_identity"),
                expected_generation_release,
            )
            or not _generation_release_matches(
                agent_runtime.get("generation_release_identity"),
                expected_generation_release,
            )
            or result.get("compliance_registry_authority")
            != expected_registry_authority
            or agent_runtime.get("compliance_registry_authority")
            != expected_registry_authority
            or result.get("job_execution_identity")
            != expected_job_execution_identity
        ):
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_JOB_UNTRUSTED"
            continue
        raw_updated_at = job.get("updated_at")
        if raw_updated_at is None:
            raw_updated_at = job.get("created_at", 0)
        if isinstance(raw_updated_at, bool) or not isinstance(
            raw_updated_at,
            (int, float),
        ):
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_JOB_UNTRUSTED"
            continue
        try:
            updated_at = float(raw_updated_at)
        except (OverflowError, TypeError, ValueError):
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_JOB_UNTRUSTED"
            continue
        if not math.isfinite(updated_at):
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_JOB_UNTRUSTED"
            continue
        raw_json_path = result.get("json")
        if not isinstance(raw_json_path, str) or not raw_json_path.strip():
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_OUTPUT_UNTRUSTED"
            continue
        try:
            output_witness = _trusted_build_snapshot(
                raw_json_path,
                release_root=release_root,
                workspace_root=workspace_root,
                max_bytes=_MAX_JSON_BYTES,
            )
            if output_witness.path.name != f"actions_{job_id}.json":
                raise AcceptanceError(
                    "HOLD_SOURCE_OUTPUT_UNTRUSTED", "正式来源JSON名称未绑定job"
                )
            output = _decode_witness_json(output_witness)
            event_rows, event_snapshots = _event_bundle(
                events_dir=workspace_root / "backend" / "data" / "autoplan" / "events",
                job_id=job_id,
                events_state=events_state,
            )
            (
                current_attempt_events,
                compliance_preflight_events,
            ) = _current_attempt_event_slice(
                events=event_rows,
                attempt_id=attempt_id,
                owner_instance_id=owner_instance_id,
                job_revision=int(job_revision),
            )
            started_events = [
                row
                for row in current_attempt_events
                if row.get("event") == "job_started"
            ]
            succeeded_events = [
                row
                for row in current_attempt_events
                if row.get("event") == "job_succeeded"
            ]
            if (
                len(started_events) != 1
                or not _generation_release_matches(
                    started_events[0].get("generation_release_identity"),
                    expected_generation_release,
                )
                or started_events[0].get("compliance_registry_authority")
                != expected_registry_authority
                or len(succeeded_events) != 1
                or not _generation_release_matches(
                    succeeded_events[0].get("generation_release_identity"),
                    expected_generation_release,
                )
                or succeeded_events[0].get("compliance_registry_authority")
                != expected_registry_authority
            ):
                raise AcceptanceError(
                    "HOLD_SOURCE_JOB_UNTRUSTED",
                    "正式来源任务事件未绑定当前密封发布",
                )
        except AcceptanceError as exc:
            if requested_job_id:
                requested_rejection = exc.code
            continue
        variants = output.get("variants") if isinstance(output, dict) else None
        if not isinstance(variants, list) or not variants:
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_OUTPUT_UNTRUSTED"
            continue
        try:
            declared_variant_ids = [
                int(variant.get("variant_id"))
                for variant in variants
                if isinstance(variant, dict)
            ]
        except (OverflowError, TypeError, ValueError):
            declared_variant_ids = []
        if (
            len(declared_variant_ids) != len(variants)
            or declared_variant_ids != list(range(1, len(variants) + 1))
            or any(
                not _generation_release_matches(
                    variant.get("generation_release_identity"),
                    expected_generation_release,
                )
                or variant.get("compliance_registry_authority")
                != expected_registry_authority
                for variant in variants
                if isinstance(variant, dict)
            )
        ):
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_OUTPUT_UNTRUSTED"
            continue
        allowed_variant_ids = set(declared_variant_ids)
        if not _compliance_preflight_events_valid(
            events=compliance_preflight_events,
            variant_ids=allowed_variant_ids,
            registry_authority=expected_registry_authority,
        ):
            if requested_job_id:
                requested_rejection = "HOLD_SOURCE_JOB_UNTRUSTED"
            continue
        try:
            if durable_provider_admission is None:
                raise AcceptanceError(
                    "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                    "正式来源缺少当前持久化供应商准入身份",
                )
            provider_admissions = [
                _validated_provider_admission(
                    (
                        (variant.get("model_routing") or {}).get(
                            "provider_admission"
                        )
                        if isinstance(variant, Mapping)
                        and isinstance(variant.get("model_routing"), Mapping)
                        else None
                    ),
                    events=current_attempt_events,
                    durable=durable_provider_admission,
                )
                for variant in variants
            ]
            provider_admission = provider_admissions[0]
            if any(row != provider_admission for row in provider_admissions[1:]):
                raise AcceptanceError(
                    "HOLD_SOURCE_PROVIDER_ADMISSION_INCOMPLETE",
                    "正式来源各方案的供应商准入绑定不一致",
                )
            (
                artifact_witnesses,
                artifact_projection,
                formal_variants,
            ) = _artifact_bundle(
                result=result,
                release_root=release_root,
                workspace_root=workspace_root,
                expected_variants=variants,
                job_id=job_id,
                provider_admission=provider_admission,
                job_execution_identity=expected_job_execution_identity,
                compliance_registry_authority=expected_registry_authority,
            )
        except AcceptanceError as exc:
            if requested_job_id:
                requested_rejection = exc.code
            continue
        seen_variant_ids: set[int] = set()
        job_candidates: list[tuple[float, str, int, dict[str, Any]]] = []
        job_rejection: str | None = None
        for index, (source_variant, variant) in enumerate(
            zip(variants, formal_variants, strict=True)
        ):
            if not isinstance(source_variant, dict) or not isinstance(variant, dict):
                job_rejection = "HOLD_SOURCE_OUTPUT_UNTRUSTED"
                break
            source_sections = source_variant.get("sections")
            source_outline = source_variant.get("outline")
            sections = variant.get("sections")
            outline = variant.get("outline")
            gate = variant.get("delivery_quality_gate")
            source_standard_index = (
                source_variant.get("standard_index")
                if isinstance(source_variant.get("standard_index"), dict)
                else {}
            )
            formal_standard_index = (
                variant.get("standard_index")
                if isinstance(variant.get("standard_index"), dict)
                else {}
            )
            try:
                variant_id = int(variant.get("variant_id"))
            except (OverflowError, TypeError, ValueError):
                variant_id = 0
            if (
                variant_id <= 0
                or variant_id in seen_variant_ids
                or source_variant.get("variant_id") != variant_id
                or not isinstance(source_sections, list)
                or not source_sections
                or any(not isinstance(section, dict) for section in source_sections)
                or not isinstance(source_outline, list)
                or source_outline
                != [
                    str(section.get("title") or "").strip()
                    for section in source_sections
                ]
                or variant.get("delivery_scope") != "document"
                or variant.get("delivery_ready") is not True
                or variant.get("dry_run") is not False
                or not isinstance(sections, list)
                or not sections
                or any(not isinstance(section, dict) for section in sections)
                or any(
                    not str(section.get("title") or "").strip()
                    or not str(section.get("content") or "").strip()
                    or bool(section.get("error"))
                    for section in sections
                )
                or not isinstance(outline, list)
                or outline
                != [str(section.get("title") or "").strip() for section in sections]
                or not isinstance(gate, dict)
                or gate.get("delivery_allowed") is not True
                or str(gate.get("decision_digest") or "")
                != canonical_digest(
                    {
                        key: value
                        for key, value in gate.items()
                        if key != "decision_digest"
                    }
                )
                or not _source_input_receipt_valid(
                    variant.get("source_input_receipt"),
                    project_id=project_id,
                    tender=tender,
                    boq=boq,
                )
                or source_variant.get("source_input_receipt")
                != variant.get("source_input_receipt")
                or source_variant.get("compliance_registry_authority")
                != expected_registry_authority
                or variant.get("compliance_registry_authority")
                != expected_registry_authority
                or any(
                    str(index_value.get("official_registry_sha256") or "")
                    != str(expected_registry_authority["registry_sha256"])
                    or str(index_value.get("official_registry_path") or "")
                    != str(expected_registry_authority["registry_path"])
                    for index_value in (
                        source_standard_index,
                        formal_standard_index,
                    )
                )
            ):
                job_rejection = "HOLD_SOURCE_OUTPUT_UNTRUSTED"
                break
            seen_variant_ids.add(variant_id)
            try:
                event_projection = _validate_event_and_provider_chain(
                    events=current_attempt_events,
                    variant_id=variant_id,
                    allowed_variant_ids=allowed_variant_ids,
                    sections=source_sections,
                    admitted_routes=list(provider_admission["admitted_chain"]),
                    attempt_id=attempt_id,
                    owner_instance_id=owner_instance_id,
                    job_revision=int(job_revision),
                )
                checkpoint, checkpoint_snapshot = _checkpoint_bundle(
                    checkpoints_dir=(
                        workspace_root / "backend" / "data" / "autoplan" / "checkpoints"
                    ),
                    job_id=job_id,
                    project_id=project_id,
                    variant_id=variant_id,
                    outline=[str(value) for value in source_outline],
                    sections=source_sections,
                    provider_admission_binding_digest=str(
                        provider_admission["binding_digest"]
                    ),
                    compliance_registry_authority_digest=str(
                        expected_registry_authority["authority_digest"]
                    ),
                    provider_admission_routes=list(
                        provider_admission["admitted_chain"]
                    ),
                    attempt_id=attempt_id,
                    owner_instance_id=owner_instance_id,
                    job_revision=int(job_revision),
                    chapter_routes=list(event_projection["chapter_routes"]),
                )
                event_projection["event_file_count"] = len(event_snapshots)
                event_projection["event_bundle_digest"] = canonical_digest(
                    [
                        {
                            "name": event_snapshot.path.name,
                            "sha256": event_snapshot.sha256,
                            "size": event_snapshot.size,
                        }
                        for event_snapshot in event_snapshots
                    ]
                )
                event_projection["event_directory_members_digest"] = (
                    events_state.members_digest
                    if events_state is not None
                    else canonical_digest([])
                )
                event_projection["provider_admission"] = provider_admission
                execution = (
                    (job.get("agent_runtime") or {}).get("execution_control")
                    if isinstance(job.get("agent_runtime"), dict)
                    else None
                )
                if not _execution_evidence_valid(
                    execution,
                    event_projection=event_projection,
                    artifact_projection=artifact_projection,
                ):
                    raise AcceptanceError(
                        "HOLD_SOURCE_PROVIDER_ATTEMPTS_INCOMPLETE",
                        "正式来源执行控制证据不完整",
                    )
            except AcceptanceError as exc:
                job_rejection = exc.code
                break
            job_candidates.append(
                (
                    updated_at,
                    job_id,
                    variant_id,
                    {
                        "job_id": job_id,
                        "job_snapshot": job_snapshot,
                        "output_witness": output_witness,
                        "variant_index": index,
                        "variant_id": variant_id,
                        "variant": variant,
                        "checkpoint": checkpoint,
                        "checkpoint_snapshot": checkpoint_snapshot,
                        "event_projection": event_projection,
                        "artifact_projection": artifact_projection,
                        "witnesses": [
                            output_witness,
                            checkpoint_snapshot,
                            *event_snapshots,
                            *artifact_witnesses,
                        ],
                    },
                )
            )
        if job_rejection or len(job_candidates) != len(variants):
            if requested_job_id:
                requested_rejection = (
                    job_rejection or "HOLD_SOURCE_OUTPUT_UNTRUSTED"
                )
            continue
        candidates.extend(job_candidates)
    if not candidates:
        return None, requested_rejection or "HOLD_NO_CURRENT_FORMAL_SOURCE"
    _updated_at, _job_id, _variant_id, selected = max(
        candidates,
        key=lambda row: (row[0], row[1], row[2]),
    )
    return selected, "CURRENT_FORMAL_SOURCE_ELIGIBLE"


def _formal_boq_focus(
    focus_names: list[str],
    *,
    source_variant: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build formal focus input without trusting model-authored exemptions.

    An optional/not-applicable drawing decision is an approval decision, not a
    generation result. Until an independent immutable approval audit exists,
    embedded source-job receipts are diagnostic only and every focus item
    remains required by the cross-index builder.
    """

    source_focus = (
        source_variant.get("boq_focus")
        if isinstance(source_variant, Mapping)
        and isinstance(source_variant.get("boq_focus"), Mapping)
        else {}
    )
    ignored = any(
        isinstance(source_focus.get(field), (dict, list))
        and bool(source_focus.get(field))
        for field in ("drawing_requirements", "drawing_requirement_receipts")
    )
    return {
        "must_cover_keywords": list(focus_names),
        "source_drawing_exemptions_ignored": ignored,
    }


def _requirements(tender: dict[str, Any]) -> list[str]:
    raw = tender.get("global_requirements")
    if not isinstance(raw, list):
        raw = tender.get("requirements")
    return [str(value).strip() for value in (raw or []) if str(value).strip()]


def _outline(tender: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    raw = tender.get("outline") if isinstance(tender.get("outline"), list) else None
    if raw is None:
        raw = plan.get("outline") if isinstance(plan.get("outline"), list) else []
    return [str(value).strip() for value in raw if str(value).strip()]


def _source_or_hold_signals(
    selected: dict[str, Any] | None,
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if selected is None:
        sections: list[dict[str, Any]] = []
        quality_checks: dict[str, Any] = {}
        return (
            sections,
            quality_checks,
            build_independent_content_review({}, sections=sections, strict=True),
            {"ok": False, "reason": "NO_CURRENT_FORMAL_SOURCE"},
            {
                "failed_chapters": [{"code": "NO_CURRENT_FORMAL_SOURCE"}],
                "consistency_review": {
                    "ok": False,
                    "summary": "DECISION: BLOCK - NO_CURRENT_FORMAL_SOURCE",
                },
            },
            {
                "status": "HOLD_NO_CURRENT_FORMAL_SOURCE",
                "summary": {
                    "strict_delivery_allowed": False,
                    "blocking_requirement_ids": ["NO_CURRENT_FORMAL_SOURCE"],
                },
            },
        )
    variant = selected["variant"]
    sections = [dict(section) for section in variant.get("sections") or []]
    quality_checks = (
        dict(variant.get("quality_checks"))
        if isinstance(variant.get("quality_checks"), dict)
        else {}
    )
    content_review = build_independent_content_review(
        quality_checks,
        sections=sections,
        strict=True,
    )
    plan_consistency = (
        dict(variant.get("plan_consistency"))
        if isinstance(variant.get("plan_consistency"), dict)
        else {"ok": False, "reason": "CURRENT_FORMAL_PLAN_RECEIPT_MISSING"}
    )
    model_routing = (
        variant.get("model_routing")
        if isinstance(variant.get("model_routing"), dict)
        else {}
    )
    model_review = (
        dict(model_routing.get("review_audit"))
        if isinstance(model_routing.get("review_audit"), dict)
        else {
            "failed_chapters": [{"code": "CURRENT_FORMAL_MODEL_REVIEW_MISSING"}],
            "consistency_review": {
                "ok": False,
                "summary": "DECISION: BLOCK - CURRENT_FORMAL_MODEL_REVIEW_MISSING",
            },
        }
    )
    requirement_matrix = (
        dict(variant.get("requirement_evidence_matrix"))
        if isinstance(variant.get("requirement_evidence_matrix"), dict)
        else {
            "status": "HOLD_CURRENT_FORMAL_REQUIREMENT_MATRIX_MISSING",
            "summary": {
                "strict_delivery_allowed": False,
                "blocking_requirement_ids": [
                    "CURRENT_FORMAL_REQUIREMENT_MATRIX_MISSING"
                ],
            },
        }
    )
    return (
        sections,
        quality_checks,
        content_review,
        plan_consistency,
        model_review,
        requirement_matrix,
    )


_APPROVAL_RECEIPT_FIELDS = (
    "receipt_id",
    "status",
    "project_id",
    "field",
    "value_digest",
    "summary",
    "approved_by",
    "approved_at",
)


def _verified_approved_resolutions(
    *,
    project_id: str,
    approved: Any,
    approval_audit_bytes: bytes,
    trusted_ingest_records: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    requested = dict(approved) if isinstance(approved, Mapping) else {}
    verified: dict[str, Any] = {}
    rejected: list[dict[str, str]] = []
    audit_status = "missing" if not approval_audit_bytes else "present"
    try:
        parse_project_fact_approval_audit(approval_audit_bytes)
    except ProjectFactApprovalAuditError as exc:
        audit_status = "invalid"
        rejected.extend(
            {"field": str(field), "machine_code": exc.code}
            for field in requested
        )
        requested = {}

    current_sources = [
        {**record, "enabled": True, "usable": True}
        for record in trusted_ingest_records
        if isinstance(record, dict)
    ]
    for raw_field, raw_resolution in requested.items():
        field = str(raw_field or "").strip()
        resolution = (
            dict(raw_resolution) if isinstance(raw_resolution, Mapping) else {}
        )
        locator = resolution.get("approval_event")
        resolution_core = {
            key: value for key, value in resolution.items() if key != "approval_event"
        }
        evidence = (
            resolution_core.get("evidence")
            if isinstance(resolution_core.get("evidence"), Mapping)
            else {}
        )
        receipt = resolution_core.get("approval_receipt")
        if not isinstance(receipt, Mapping):
            receipt = resolution_core.get("confirmation_receipt")
        normalized_receipt = (
            {
                key: " ".join(str(receipt.get(key) or "").split()).strip()
                for key in _APPROVAL_RECEIPT_FIELDS
            }
            if isinstance(receipt, Mapping)
            else {}
        )
        if normalized_receipt:
            normalized_receipt["status"] = normalized_receipt["status"].lower()
            normalized_receipt["value_digest"] = normalized_receipt[
                "value_digest"
            ].lower()
        source_sha256 = str(
            evidence.get("document_sha256") or evidence.get("source_sha256") or ""
        ).strip().lower()
        matching_sources = [
            row
            for row in current_sources
            if str(row.get("source_sha256") or "").strip().lower()
            == source_sha256
        ]
        try:
            if len(matching_sources) != 1:
                raise ValueError("source_not_current")
            source = matching_sources[0]
            expected_source = {
                "locator": str(evidence.get("locator") or "").strip(),
                "filename": str(source.get("filename") or "").strip(),
                "source_sha256": str(source.get("source_sha256") or "")
                .strip()
                .lower(),
                "extract_text_sha256": str(
                    source.get("extract_text_sha256") or ""
                )
                .strip()
                .lower(),
                "ingest_audit_row_digest": str(
                    source.get("audit_row_digest") or ""
                )
                .strip()
                .lower(),
                "source_relative_path": str(
                    source.get("source_relative_path") or ""
                ),
                "extract_relative_path": str(
                    source.get("extract_relative_path") or ""
                ),
                "enabled": True,
                "usable": True,
            }
            outcome = verify_project_fact_approval_event(
                approval_audit_bytes,
                locator if isinstance(locator, Mapping) else {},
                expected_project_id=project_id,
                expected_field=field,
                expected_resolution_digest=approval_canonical_digest(
                    resolution_core
                ),
                expected_value_digest=approval_value_digest(
                    field=field,
                    value=resolution_core.get("value"),
                    unit=resolution_core.get("unit"),
                ),
                expected_approval_receipt_digest=approval_canonical_digest(
                    normalized_receipt
                ),
                expected_source_evidence=expected_source,
                current_source_allowlist=current_sources,
            )
        except (ProjectFactApprovalAuditError, TypeError, ValueError):
            outcome = {
                "ok": False,
                "machine_code": "PROJECT_FACT_APPROVAL_EVENT_INVALID",
            }
        if outcome.get("ok") is True:
            verified[field] = resolution_core
        else:
            rejected.append(
                {
                    "field": field,
                    "machine_code": str(
                        outcome.get("machine_code")
                        or "PROJECT_FACT_APPROVAL_EVENT_INVALID"
                    ),
                }
            )
    machine_codes: list[str] = []
    if rejected:
        if any(
            row["machine_code"] == "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT"
            for row in rejected
        ):
            machine_codes.append("HOLD_PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT")
        elif any(
            row["machine_code"]
            in {
                "PROJECT_FACT_APPROVAL_EVENT_NOT_FOUND",
                "PROJECT_FACT_APPROVAL_LOCATOR_INVALID",
            }
            for row in rejected
        ):
            machine_codes.append("HOLD_PROJECT_FACT_APPROVAL_EVENT_MISSING")
        else:
            machine_codes.append("HOLD_PROJECT_FACT_APPROVAL_EVENT_INVALID")
    return (
        verified,
        {
            "status": audit_status,
            "requested_count": len(verified) + len(rejected),
            "verified_count": len(verified),
            "rejected_count": len(rejected),
            "rejections_digest": canonical_digest(rejected),
        },
        machine_codes,
    )


def _release_projection(release_identity: Mapping[str, Any]) -> dict[str, Any]:
    digest_fields = (
        "manifest_digest",
        "source_digest",
        "runtime_digest",
        "current_json_sha256",
        "supervisor_state_sha256",
        "backend_health_sha256",
    )
    text_fields = (
        "system_id",
        "release_id",
        "release_root",
        "health_status",
        "supervisor_instance_id",
    )
    expected_fields = set(digest_fields) | set(text_fields) | {
        "supervisor_pid",
        "backend_pid",
        "ui_pid",
    }
    if set(release_identity) != expected_fields:
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_IDENTITY_INVALID", "发布身份字段集合不完整或包含未知字段"
        )
    result: dict[str, Any] = {
        field: str(release_identity.get(field) or "").strip()
        for field in (*text_fields, *digest_fields)
    }
    for field in digest_fields:
        if _SHA256_RE.fullmatch(result[field].lower()) is None:
            raise AcceptanceError(
                "ACCEPTANCE_RELEASE_IDENTITY_INVALID",
                f"发布身份字段无效：{field}",
            )
    for field in ("supervisor_pid", "backend_pid", "ui_pid"):
        value = release_identity.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 1:
            raise AcceptanceError(
                "ACCEPTANCE_RELEASE_IDENTITY_INVALID",
                f"发布运行进程字段无效：{field}",
            )
        result[field] = value
    release_root = Path(result["release_root"])
    if (
        not result["system_id"]
        or not result["release_id"]
        or result["health_status"] != "verified_healthy"
        or not result["supervisor_instance_id"]
        or not release_root.is_absolute()
        or release_root.name != result["release_id"]
    ):
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_IDENTITY_INVALID", "发布身份或健康证明不完整"
        )
    return result


def _stage_summaries(
    *,
    drawing: dict[str, Any],
    standards: dict[str, Any],
    parameter_evidence: dict[str, Any],
    parameter_validation: dict[str, Any],
    ledger: dict[str, Any],
    ledger_validation: dict[str, Any],
    checklist: dict[str, Any],
    cross: dict[str, Any],
    cross_validation: dict[str, Any],
    gate: dict[str, Any],
) -> dict[str, Any]:
    standard_rows = [
        row
        for row in (standards.get("standards") or [])
        if isinstance(row, dict)
    ]
    return {
        "drawing_index": {
            "digest": canonical_digest(drawing),
            "ok": drawing.get("ok") is True,
            "processed": int(drawing.get("processed_drawing_count") or 0),
            "indexed": int(drawing.get("indexed_drawing_count") or 0),
            "graphics_only_pages": int(drawing.get("graphics_only_page_count") or 0),
            "integrity_rejections": int(drawing.get("integrity_rejection_count") or 0),
            "identity_errors": int(drawing.get("invalid_identity_count") or 0),
            "text_status": drawing.get("text_index_status"),
            "page_coverage_status": drawing.get("page_coverage_status"),
            "chapter_binding_status": drawing.get("chapter_binding_status"),
        },
        "standard_index": {
            "digest": canonical_digest(standards),
            "ok": standards.get("ok") is True,
            "official_registry_path": standards.get("official_registry_path"),
            "official_registry_sha256": standards.get(
                "official_registry_sha256"
            ),
            "indexed": int(standards.get("indexed_standard_count") or 0),
            "official_verified": int(
                standards.get("official_registry_verified_count") or 0
            ),
            "integrity_rejections": int(standards.get("integrity_rejection_count") or 0),
            "identity_errors": int(standards.get("invalid_identity_count") or 0),
            "missing_text_or_ocr": int(
                standards.get("missing_text_or_ocr_count") or 0
            ),
            "locator_unavailable": int(
                standards.get("locator_unavailable_count") or 0
            ),
            "chapter_binding_count": len(standards.get("chapter_bindings") or []),
            "chapter_binding_status": standards.get("chapter_binding_status"),
            "standards": [
                {
                    "standard_code": row.get("standard_code"),
                    "source_sha256": row.get("sha256"),
                    "identity_status": row.get("primary_identity_status"),
                    "identity_basis": row.get("primary_identity_proof_basis"),
                    "cover_name_status": row.get("cover_name_status"),
                    "registry_status": row.get("official_registry_status"),
                    "source_hash_proof_status": row.get("source_hash_proof_status"),
                    "page_anchor_count": len(row.get("page_anchors") or []),
                }
                for row in standard_rows
            ],
        },
        "project_parameter_evidence": {
            "digest": canonical_digest(parameter_evidence),
            "status": parameter_evidence.get("status"),
            "ready": parameter_evidence.get("ready") is True,
            "coverage_complete": parameter_evidence.get("coverage_complete") is True,
            "conflict_count": len(parameter_evidence.get("conflicts") or []),
            "evidence_set_receipt_digest": parameter_evidence.get(
                "evidence_set_receipt_digest"
            ),
            "validation": parameter_validation,
        },
        "project_fact_ledger": {
            "digest": ledger.get("ledger_digest") or canonical_digest(ledger),
            "validation": ledger_validation,
            "formal_parameter_readiness": ledger.get(
                "formal_parameter_readiness"
            ),
            "unresolved_fields": ledger.get("unresolved_fields") or [],
        },
        "confirmation_checklist": {
            "digest": canonical_digest(checklist),
            "formal_ready": checklist.get("formal_ready") is True,
            "resolved_fields": [
                row.get("field")
                for row in (checklist.get("resolved") or [])
                if isinstance(row, dict)
            ],
            "blocked_fields": checklist.get("blocked_fields") or [],
        },
        "cross_index": {
            "digest": canonical_digest(cross),
            "validation": cross_validation,
            "focus_count": int(cross.get("focus_count") or 0),
            "mentioned_count": int(cross.get("mentioned_count") or 0),
            "closed_ok_count": int(cross.get("closed_ok_count") or 0),
            "missing_drawing_locator_count": int(
                cross.get("missing_drawing_locator_count") or 0
            ),
            "missing_standard_locator_count": int(
                cross.get("missing_standard_locator_count") or 0
            ),
        },
        "formal_delivery_gate": {
            "digest": gate.get("decision_digest") or canonical_digest(gate),
            "delivery_allowed": gate.get("delivery_allowed") is True,
            "blocker_codes": [
                str(row.get("code") or "")
                for row in (gate.get("blockers") or [])
                if isinstance(row, dict) and str(row.get("code") or "")
            ],
            "blocker_count": int(gate.get("blocker_count") or 0),
            "formal_contract_version": gate.get("formal_contract_version"),
        },
    }


def _acceptance_output_directory(
    *,
    data_root: Path,
    project_id: str,
    output_root: str | Path | None,
) -> Path:
    base = (
        Path(os.path.abspath(os.fspath(output_root)))
        if output_root is not None
        else data_root / "autoplan" / "acceptance_receipts" / "no_model_formal"
    )
    if not _path_within(base, data_root):
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执目录必须位于数据根目录内"
        )
    return base / project_storage_key(project_id)


@dataclass(frozen=True)
class _DirectoryLink:
    parent_fd: int
    name: str
    device: int
    inode: int


@dataclass
class _OutputDirectoryHandle:
    root_path: Path
    output_path: Path
    fds: tuple[int, ...]
    links: tuple[_DirectoryLink, ...]
    root_device: int
    root_inode: int
    root_chain: tuple[DirectoryWitness, ...]

    @property
    def fd(self) -> int:
        return self.fds[-1]

    def verify_namespace(self) -> None:
        _verify_directory_chain(
            self.root_chain,
            code="ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
        )
        try:
            root_info = os.lstat(self.root_path)
            opened_root = os.fstat(self.fds[0])
        except OSError as exc:
            raise AcceptanceError(
                "ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
                "验收回执数据根目录已发生变化",
            ) from exc
        if (
            not stat.S_ISDIR(root_info.st_mode)
            or stat.S_ISLNK(root_info.st_mode)
            or root_info.st_uid != os.getuid()
            or stat.S_IMODE(root_info.st_mode) & 0o022
            or opened_root.st_uid != os.getuid()
            or stat.S_IMODE(opened_root.st_mode) & 0o022
            or (opened_root.st_dev, opened_root.st_ino)
            != (self.root_device, self.root_inode)
            or (root_info.st_dev, root_info.st_ino)
            != (self.root_device, self.root_inode)
        ):
            raise AcceptanceError(
                "ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
                "验收回执数据根目录已发生变化",
            )
        for link, descriptor in zip(self.links, self.fds[1:], strict=True):
            try:
                opened = os.fstat(descriptor)
                info = os.stat(
                    link.name,
                    dir_fd=link.parent_fd,
                    follow_symlinks=False,
                )
            except OSError as exc:
                raise AcceptanceError(
                    "ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
                    "验收回执目录链已发生变化",
                ) from exc
            if (
                not stat.S_ISDIR(info.st_mode)
                or stat.S_ISLNK(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o022
                or opened.st_uid != os.getuid()
                or stat.S_IMODE(opened.st_mode) & 0o022
                or (opened.st_dev, opened.st_ino) != (link.device, link.inode)
                or (info.st_dev, info.st_ino) != (link.device, link.inode)
            ):
                raise AcceptanceError(
                    "ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
                    "验收回执目录链已发生变化",
                )

    def close(self) -> None:
        for descriptor in reversed(self.fds):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _assert_directory_fd_supported() -> None:
    if not _DIRECTORY_FD_OPERATIONS_SUPPORTED:
        raise AcceptanceError(
            "ACCEPTANCE_DIRECTORY_FD_UNSUPPORTED",
            "当前运行时不支持安全目录相对发布",
        )


def _validate_owned_directory_fd(descriptor: int) -> os.stat_result:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o022
    ):
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED",
            "验收回执目录类型、所有者或权限不可信",
        )
    return info


def _open_output_directory_handle(
    *,
    data_root: Path,
    project_id: str,
    output_root: str | Path | None,
    create: bool,
) -> _OutputDirectoryHandle | None:
    _assert_directory_fd_supported()
    root = Path(os.path.abspath(os.fspath(data_root)))
    root_chain = _capture_directory_chain(
        root,
        code="ACCEPTANCE_OUTPUT_PATH_UNTRUSTED",
    )
    output_path = _acceptance_output_directory(
        data_root=root,
        project_id=project_id,
        output_root=output_root,
    )
    try:
        relative = output_path.relative_to(root)
    except ValueError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执目录必须位于数据根目录内"
        ) from exc
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptors: list[int] = []
    links: list[_DirectoryLink] = []
    try:
        root_fd = os.open(root, flags)
        descriptors.append(root_fd)
        root_info = _validate_owned_directory_fd(root_fd)
        _verify_directory_chain(
            root_chain,
            code="ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
        )
        parent_fd = root_fd
        for part in relative.parts:
            if part in {"", ".", ".."} or "/" in part:
                raise AcceptanceError(
                    "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED",
                    "回执目录包含不安全路径段",
                )
            created = False
            try:
                child_fd = os.open(part, flags, dir_fd=parent_fd)
            except FileNotFoundError:
                if not create:
                    for descriptor in reversed(descriptors):
                        os.close(descriptor)
                    return None
                try:
                    os.mkdir(part, 0o700, dir_fd=parent_fd)
                    created = True
                    child_fd = os.open(part, flags, dir_fd=parent_fd)
                except OSError as exc:
                    raise AcceptanceError(
                        "ACCEPTANCE_OUTPUT_CREATE_FAILED",
                        "无法安全创建验收回执目录",
                    ) from exc
            except OSError as exc:
                raise AcceptanceError(
                    "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED",
                    "验收回执目录包含符号链接或非目录对象",
                ) from exc
            descriptors.append(child_fd)
            child_info = _validate_owned_directory_fd(child_fd)
            if created:
                os.fchmod(child_fd, 0o700)
                child_info = _validate_owned_directory_fd(child_fd)
                os.fsync(child_fd)
                os.fsync(parent_fd)
            links.append(
                _DirectoryLink(
                    parent_fd=parent_fd,
                    name=part,
                    device=child_info.st_dev,
                    inode=child_info.st_ino,
                )
            )
            parent_fd = child_fd
        handle = _OutputDirectoryHandle(
            root_path=root,
            output_path=output_path,
            fds=tuple(descriptors),
            links=tuple(links),
            root_device=root_info.st_dev,
            root_inode=root_info.st_ino,
            root_chain=root_chain,
        )
        handle.verify_namespace()
        return handle
    except BaseException:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _read_regular_snapshot_at(
    handle: _OutputDirectoryHandle,
    name: str,
    *,
    allow_missing: bool = False,
    max_bytes: int = _MAX_JSON_BYTES,
) -> tuple[FileSnapshot, os.stat_result] | None:
    if Path(name).name != name or name in {"", ".", ".."}:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执文件名无效"
        )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=handle.fd)
    except FileNotFoundError:
        if allow_missing:
            return None
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_MISSING", f"缺少回执文件：{name}"
        ) from None
    except OSError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执文件类型不可信"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise AcceptanceError(
                "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执文件类型或所有者不可信"
            )
        if before.st_size < 0 or before.st_size > max_bytes:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_TOO_LARGE", "回执文件超过允许大小"
            )
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        try:
            current = os.stat(name, dir_fd=handle.fd, follow_symlinks=False)
        except OSError as exc:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", "回执文件在读取期间发生变化"
            ) from exc
        if (
            not _same_file_identity(before, after)
            or not _same_file_identity(after, current)
            or len(raw) != before.st_size
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", "回执文件在读取期间发生变化"
            )
        return (
            FileSnapshot(
                path=handle.output_path / name,
                raw=raw,
                sha256=hashlib.sha256(raw).hexdigest(),
                size=len(raw),
                mtime_ns=before.st_mtime_ns,
                device=before.st_dev,
                inode=before.st_ino,
                mode=stat.S_IMODE(before.st_mode),
            ),
            before,
        )
    finally:
        os.close(descriptor)


def _validated_legacy_v1_predecessor_digest(
    value: Any,
    *,
    project_id: str,
) -> str | None:
    """Accept a legacy HOLD only as an immutable predecessor, never as evidence."""

    if (
        not isinstance(value, Mapping)
        or set(value) != _LEGACY_V1_TOP_LEVEL_FIELDS
        or value.get("schema_version") != _LEGACY_V1_SCHEMA_VERSION
        or str(value.get("project_id") or "").strip() != project_id
        or value.get("decision") != "HOLD"
        or value.get("model_calls") != 0
        or value.get("provider_probes") != 0
        or not receipt_digest_is_valid(value)
    ):
        return None
    try:
        _validate_run_id(value.get("run_id"))
        _parse_utc_timestamp(value.get("created_at"))
    except AcceptanceError:
        return None
    mapping_fields = (
        "code_acceptance",
        "confirmation_checklist",
        "cross_index",
        "drawing_index",
        "formal_delivery_gate",
        "project_fact_ledger",
        "project_parameter_evidence",
        "schedule_derivation",
        "source_task",
        "standard_index",
        "tender_matrix",
        "v7_drawing_ingest",
    )
    if (
        not all(isinstance(value.get(field), Mapping) for field in mapping_fields)
        or not isinstance(value.get("external_blockers"), list)
        or not isinstance(value.get("tender_sources"), list)
    ):
        return None
    release = value.get("release")
    if not isinstance(release, Mapping) or set(release) != _LEGACY_V1_RELEASE_FIELDS:
        return None
    manifest_digest = str(release.get("manifest_digest") or "").strip().lower()
    source_digest = str(release.get("source_digest") or "").strip().lower()
    runtime_digest = str(release.get("runtime_digest") or "").strip().lower()
    release_id = str(release.get("release_id") or "").strip()
    build_sha = str(release.get("build_sha") or "").strip().lower()
    jobs = release.get("jobs")
    admission = release.get("provider_admission")
    if (
        any(
            _SHA256_RE.fullmatch(digest) is None
            for digest in (manifest_digest, source_digest, runtime_digest)
        )
        or release_id != f"release-{source_digest[:24]}"
        or re.fullmatch(r"[0-9a-f]{40}", build_sha) is None
        or release.get("system_id") != "docgen-system"
        or release.get("runtime_mode") != "sealed_release"
        or release.get("supervisor_status") != "healthy"
        or release.get("dirty") is not False
        or not isinstance(jobs, Mapping)
        or set(jobs) != {"active", "queued", "running"}
        or any(jobs.get(field) != 0 for field in ("active", "queued", "running"))
        or not isinstance(admission, Mapping)
        or admission.get("admitted") is not False
        or admission.get("generation_allowed") is not False
        or not isinstance(admission.get("configured"), bool)
        or not isinstance(admission.get("degraded"), bool)
        or not str(admission.get("state") or "").strip()
    ):
        return None
    return str(value["receipt_digest"]).strip().lower()


def _capture_latest_state(
    *,
    data_root: Path,
    project_id: str,
    output_root: str | Path | None,
    handle: _OutputDirectoryHandle | None = None,
) -> tuple[str | None, str | None]:
    owned_handle = handle is None
    active = handle or _open_output_directory_handle(
        data_root=data_root,
        project_id=project_id,
        output_root=output_root,
        create=False,
    )
    if active is None:
        return None, None
    try:
        active.verify_namespace()
        latest_result = _read_regular_snapshot_at(
            active,
            "latest.json",
            allow_missing=True,
        )
        if latest_result is None:
            return None, None
        snapshot, latest_info = latest_result
        if stat.S_IMODE(latest_info.st_mode) != 0o600:
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_INVALID", "latest回执权限无效"
            )
        parsed = _decode_json(snapshot)
        current_validation = validate_acceptance_receipt(parsed)
        legacy_predecessor_digest: str | None = None
        if not current_validation.get("ok"):
            legacy_predecessor_digest = _validated_legacy_v1_predecessor_digest(
                parsed,
                project_id=project_id,
            )
        if (
            str(parsed.get("project_id") or "").strip() != project_id
            or (
                not current_validation.get("ok")
                and legacy_predecessor_digest is None
            )
        ):
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_INVALID", "既有latest回执无法验证"
            )
        immutable_name = f"{_validate_run_id(parsed.get('run_id'))}.json"
        immutable_result = _read_regular_snapshot_at(
            active,
            immutable_name,
            allow_missing=True,
        )
        if immutable_result is None:
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_INVALID", "latest缺少同名不可变历史回执"
            )
        immutable, immutable_info = immutable_result
        if (
            immutable.raw != snapshot.raw
            or stat.S_IMODE(immutable_info.st_mode) != 0o400
        ):
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_INVALID", "latest未绑定同字节不可变历史回执"
            )
        active.verify_namespace()
        return (
            snapshot.sha256,
            legacy_predecessor_digest
            or str(parsed.get("receipt_digest") or ""),
        )
    finally:
        if owned_handle:
            active.close()


def collect_acceptance_snapshot(
    *,
    project_id: str,
    data_root: str | Path,
    registry_path: str | Path,
    release_identity: Mapping[str, Any],
    release_witnesses: list[FileSnapshot | FileWitness] | None = None,
    release_validator: Callable[[], Mapping[str, Any]] | None = None,
    output_root: str | Path | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
    source_job_id: str | None = None,
) -> _PreparedAcceptance:
    pid = str(project_id or "").strip()
    if not pid:
        raise AcceptanceError("ACCEPTANCE_PROJECT_ID_MISSING", "缺少项目ID")
    if source_job_id and _JOB_ID_RE.fullmatch(source_job_id) is None:
        raise AcceptanceError(
            "ACCEPTANCE_SOURCE_JOB_ID_INVALID", "指定的source job ID格式无效"
        )
    effective_run_id = run_id or (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid.uuid4().hex[:12]
    )
    effective_run_id = _validate_run_id(effective_run_id)
    release = _release_projection(release_identity)
    if not release_witnesses or not all(
        isinstance(item, (FileSnapshot, FileWitness))
        for item in release_witnesses
    ):
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_WITNESSES_MISSING", "发布身份缺少文件见证"
        )
    witness_digests = {item.sha256 for item in release_witnesses}
    if release["current_json_sha256"] not in witness_digests:
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_WITNESSES_INVALID", "发布身份文件见证不匹配"
        )
    if release_validator is None or _release_projection(release_validator()) != release:
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_CHANGED", "当前发布或健康身份无法复验"
        )
    root = _validate_root(data_root, code="ACCEPTANCE_DATA_ROOT_UNTRUSTED")
    workspace_root = root.parent.parent.resolve(strict=False)
    release_root = Path(release["release_root"]).resolve(strict=False)
    key = project_storage_key(pid)
    project_root = root / "autoplan" / "projects" / key
    if not _directory_is_trusted(project_root):
        raise AcceptanceError(
            "ACCEPTANCE_PROJECT_ROOT_UNTRUSTED", "项目数据目录不存在或不可信"
        )
    tender_snapshot = read_regular_file_snapshot(project_root / "tender_matrix.json")
    boq_snapshot = read_regular_file_snapshot(project_root / "boq_data.json")
    plan_snapshot, plan_absent = _read_optional_regular_file_snapshot(
        project_root / "plan.json"
    )
    audit_snapshot, audit_absent = _read_optional_regular_file_snapshot(
        root / "audit" / "ingest.jsonl",
        max_bytes=_MAX_AUDIT_BYTES,
    )
    approval_audit_snapshot, approval_audit_absent = (
        _read_optional_regular_file_snapshot(
        root / "audit" / "project_fact_approvals.jsonl",
        max_bytes=_MAX_AUDIT_BYTES,
        )
    )
    registry_lexical_path = Path(os.path.abspath(os.fspath(registry_path)))
    expected_registry = sealed_official_registry_path(release_root)
    if registry_lexical_path != expected_registry:
        raise AcceptanceError(
            "ACCEPTANCE_REGISTRY_UNTRUSTED", "官方标准registry路径不可验证"
        )
    _assert_path_without_symlinks(registry_lexical_path, root=release_root)
    registry_snapshot = read_regular_file_snapshot(registry_lexical_path)
    manifest_path = release_root / "release-manifest.json"
    _assert_path_without_symlinks(manifest_path, root=release_root)
    manifest_snapshot = read_regular_file_snapshot(manifest_path)
    try:
        registry_realpath = registry_lexical_path.resolve(strict=True)
    except OSError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_REGISTRY_UNTRUSTED", "官方标准registry路径无法验证"
        ) from exc
    assert tender_snapshot is not None
    assert boq_snapshot is not None
    assert registry_snapshot is not None
    assert manifest_snapshot is not None
    if (
        registry_snapshot.mode != 0o444
        or manifest_snapshot.mode != 0o444
        or manifest_snapshot.sha256 != release["manifest_digest"]
    ):
        raise AcceptanceError(
            "ACCEPTANCE_REGISTRY_UNTRUSTED",
            "密封registry或发布清单权限、摘要不可信",
        )
    manifest = _decode_json(manifest_snapshot)
    if (
        manifest.get("schema_version") != 1
        or str(manifest.get("release_id") or "") != release["release_id"]
        or str(manifest.get("source_digest") or "") != release["source_digest"]
        or str(manifest.get("runtime_digest") or "") != release["runtime_digest"]
        or not isinstance(manifest.get("files"), list)
        or not isinstance(manifest.get("directories"), list)
    ):
        raise AcceptanceError(
            "ACCEPTANCE_REGISTRY_UNTRUSTED",
            "发布清单未绑定当前密封发布身份",
        )
    registry_entries = [
        row
        for row in manifest["files"]
        if isinstance(row, dict)
        and row.get("path") == SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix()
    ]
    sealed_directory_entries = [
        row
        for row in manifest["directories"]
        if isinstance(row, dict)
        and row.get("path") == SEALED_COMPLIANCE_ROOT_RELATIVE_PATH.as_posix()
    ]
    if (
        len(registry_entries) != 1
        or len(sealed_directory_entries) != 1
        or registry_entries[0].get("sha256") != registry_snapshot.sha256
        or registry_entries[0].get("size") != registry_snapshot.size
        or registry_entries[0].get("mode") != 0o444
        or sealed_directory_entries[0].get("mode") != 0o555
    ):
        raise AcceptanceError(
            "ACCEPTANCE_REGISTRY_UNTRUSTED",
            "正式标准registry未被发布清单完整覆盖",
        )
    registry_authority_core = {
        "schema_version": SEALED_REGISTRY_AUTHORITY_SCHEMA,
        "source_kind": "sealed_release_manifest_entry",
        "release_id": release["release_id"],
        "manifest_digest": manifest_snapshot.sha256,
        "source_digest": release["source_digest"],
        "runtime_digest": release["runtime_digest"],
        "registry_path": str(registry_lexical_path),
        "registry_relative_path": SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix(),
        "registry_sha256": registry_snapshot.sha256,
        "registry_size": registry_snapshot.size,
        "registry_mode": registry_snapshot.mode,
    }
    compliance_registry_authority = validate_registry_authority_projection(
        {
            **registry_authority_core,
            "authority_digest": canonical_digest(registry_authority_core),
        }
    )
    tender = _decode_json(tender_snapshot)
    boq = _decode_json(boq_snapshot)
    plan = _decode_json(plan_snapshot) if plan_snapshot is not None else {}
    registry = _decode_json(registry_snapshot)
    if audit_snapshot is None:
        audit_lines: tuple[str, ...] = ()
    else:
        try:
            audit_lines = tuple(audit_snapshot.raw.decode("utf-8").splitlines())
        except UnicodeError as exc:
            raise AcceptanceError(
                "ACCEPTANCE_INGEST_AUDIT_INVALID",
                "入库审计不是有效UTF-8",
            ) from exc
    ingest_receipt, ingest_validation, ingest_witnesses = _trusted_ingest_evidence(
        audit_lines=audit_lines,
        data_root=root,
        project_id=pid,
    )
    jobs, jobs_projection = _safe_job_snapshots(root / "autoplan" / "jobs")
    provider_admission_snapshot, provider_admission_absent = (
        _read_optional_regular_file_snapshot(
            root
            / "autoplan"
            / "provider_admission"
            / "provider-admission-v1.latest.json",
        )
    )
    events_dir = root / "autoplan" / "events"
    events_state, events_absent = _capture_optional_directory_state(
        events_dir,
        code="ACCEPTANCE_EVENTS_DIRECTORY_UNTRUSTED",
    )
    selected, source_code = _candidate_source(
        jobs=jobs,
        project_id=pid,
        tender=tender,
        boq=boq,
        release_identity=release,
        release_root=release_root,
        workspace_root=workspace_root,
        requested_job_id=source_job_id,
        events_state=events_state,
        provider_admission_snapshot=provider_admission_snapshot,
        compliance_registry_authority=compliance_registry_authority,
    )
    topic = str(tender.get("project_name") or tender.get("topic") or "").strip()
    outline = _outline(tender, plan)
    focus_names = select_boq_focus_names(
        boq.get("stats") if isinstance(boq.get("stats"), dict) else {},
        limit=MAX_BOQ_FOCUS_ITEMS,
    )
    boq_focus = _formal_boq_focus(
        focus_names,
        source_variant=(selected or {}).get("variant"),
    )

    drawing = build_drawing_index(
        topic,
        outline,
        project_id=pid,
        workspace_dir=root,
        audit_lines=audit_lines,
    )
    standards = build_standard_index(
        topic,
        outline,
        project_id=pid,
        workspace_dir=root,
        compliance_root=registry_realpath.parent,
        audit_lines=audit_lines,
        official_registry_bytes=registry_snapshot.raw,
        official_registry_path=registry_lexical_path,
    )
    if (
        Path(str(standards.get("official_registry_path") or "")).resolve(
            strict=False
        )
        != registry_realpath
        or str(standards.get("official_registry_sha256") or "").strip().lower()
        != registry_snapshot.sha256
    ):
        raise AcceptanceError(
            "ACCEPTANCE_REGISTRY_MISMATCH",
            "标准索引所用registry与回执快照不一致",
        )
    parameter_evidence = build_project_parameter_evidence(
        project_id=pid,
        tender=tender,
        audit_path=root / "audit" / "ingest.jsonl",
        audit_lines=audit_lines,
    )
    parameter_validation = validate_project_parameter_evidence(
        parameter_evidence,
        audit_lines=audit_lines,
    )
    trusted_source_sha256s = {
        str(row.get("source_sha256") or "").strip().lower()
        for row in (ingest_receipt.get("records") or [])
        if isinstance(row, dict)
    }
    used_source_sha256s = {
        str(row.get("sha256") or "").strip().lower()
        for row in (drawing.get("drawings") or [])
        if isinstance(row, dict)
    } | {
        str(row.get("sha256") or "").strip().lower()
        for row in (standards.get("standards") or [])
        if isinstance(row, dict)
    }
    parameter_receipt = parameter_evidence.get("evidence_set_receipt")
    if isinstance(parameter_receipt, dict):
        used_source_sha256s.update(
            str(row.get("source_sha256") or "").strip().lower()
            for row in (parameter_receipt.get("records") or [])
            if isinstance(row, dict)
        )
    used_source_sha256s.discard("")
    if not used_source_sha256s.issubset(trusted_source_sha256s):
        raise AcceptanceError(
            "ACCEPTANCE_INGEST_EVIDENCE_INCOMPLETE",
            "索引使用的入库证据未全部绑定受信字节回执",
        )
    schedule = build_boq_wbs_cpm(boq, enterprise_profile={})
    ledger_payload: dict[str, Any] = {"project_id": pid, "topic": topic}
    approved = plan.get("approved_project_fact_resolutions")
    (
        verified_approvals,
        approval_projection,
        approval_machine_codes,
    ) = _verified_approved_resolutions(
        project_id=pid,
        approved=approved,
        approval_audit_bytes=(
            approval_audit_snapshot.raw
            if approval_audit_snapshot is not None
            else b""
        ),
        trusted_ingest_records=[
            row
            for row in (ingest_receipt.get("records") or [])
            if isinstance(row, dict)
        ],
    )
    if verified_approvals:
        ledger_payload["approved_project_fact_resolutions"] = verified_approvals
    ledger = build_project_fact_ledger_from_inputs(
        payload=ledger_payload,
        tender=tender,
        boq_wbs_cpm=schedule,
        project_parameter_evidence=parameter_evidence,
        trusted_ingest_audit_lines=audit_lines,
    )
    ledger_validation = validate_project_fact_ledger(ledger)
    checklist = probe_missing_parameters(
        topic=topic,
        outline=outline,
        requirements=_requirements(tender),
        tender=tender,
        boq=boq,
        enterprise_profile={},
        project_fact_ledger=ledger,
    )
    checklist["project_fact_ledger_digest"] = str(
        ledger.get("ledger_digest") or ""
    )
    (
        sections,
        quality_checks,
        content_review,
        plan_consistency,
        model_review,
        requirement_matrix,
    ) = _source_or_hold_signals(selected)
    manifest = build_project_applicable_standards_manifest(sections)
    standard_audit = audit_standard_citations(sections, manifest)
    cross = build_cross_index(
        boq=boq,
        sections=sections,
        boq_focus=boq_focus,
        drawing_index=drawing,
        standard_index=standards,
        quality_checks=quality_checks,
        project_id=pid,
    )
    try:
        validated_cross = validate_cross_index_contract(
            cross,
            expected_names=focus_names,
        )
        cross = validated_cross
        cross_validation = {"ok": True, "machine_code": "CROSS_INDEX_VALID"}
    except ValueError as exc:
        cross = dict(cross)
        cross["ok"] = False
        cross["build_failed"] = True
        cross_validation = {
            "ok": False,
            "machine_code": str(exc) or "CROSS_INDEX_INVALID",
        }
    gate = build_delivery_quality_gate(
        strict=True,
        content_review=content_review,
        plan_consistency=plan_consistency,
        model_review_audit=model_review,
        requirement_matrix=requirement_matrix,
        standard_audit=standard_audit,
        cross_index=cross,
        model_review_required=True,
        formal_delivery_required=True,
        project_parameters=checklist,
        project_fact_ledger=ledger,
        sections=sections,
        standard_index=standards,
        standard_workspace_dir=root,
        standard_compliance_root=registry_realpath.parent,
        trusted_ingest_audit_lines=audit_lines,
        trusted_standard_registry_bytes=registry_snapshot.raw,
    )
    if approval_machine_codes:
        gate = dict(gate)
        blockers = [
            dict(row) for row in (gate.get("blockers") or []) if isinstance(row, dict)
        ]
        checks = [
            dict(row) for row in (gate.get("checks") or []) if isinstance(row, dict)
        ]
        for code in approval_machine_codes:
            blockers.append(
                {
                    "code": code,
                    "severity": "error",
                    "source": "project_fact_approval_audit",
                    "message": "正式参数批准缺少当前、持久化且可反查的用户确认事件。",
                }
            )
        checks.append(
            {
                "name": "project_fact_approval_events",
                "pass": False,
                "required": True,
                "requested_count": approval_projection["requested_count"],
                "verified_count": approval_projection["verified_count"],
                "rejected_count": approval_projection["rejected_count"],
            }
        )
        gate["checks"] = checks
        gate["blockers"] = blockers
        gate["blocker_count"] = len(blockers)
        gate["delivery_allowed"] = False
        gate_core = {
            key: value for key, value in gate.items() if key != "decision_digest"
        }
        gate["decision_digest"] = canonical_digest(gate_core)
    stages = _stage_summaries(
        drawing=drawing,
        standards=standards,
        parameter_evidence=parameter_evidence,
        parameter_validation=parameter_validation,
        ledger=ledger,
        ledger_validation=ledger_validation,
        checklist=checklist,
        cross=cross,
        cross_validation=cross_validation,
        gate=gate,
    )
    source_projection = {
        "eligible": selected is not None,
        "machine_code": source_code,
        "job_id": selected.get("job_id") if selected else None,
        "variant_index": selected.get("variant_index") if selected else None,
        "variant_id": selected.get("variant_id") if selected else None,
        "result_sha256": (
            selected["output_witness"].sha256 if selected is not None else None
        ),
        "source_input_receipt_digest": (
            ((selected or {}).get("variant") or {}).get("source_input_receipt")
            or {}
        ).get("receipt_digest"),
        "checkpoint_digest": (
            (selected or {}).get("checkpoint_snapshot").sha256
            if selected is not None
            else None
        ),
        "event_evidence": (
            (selected or {}).get("event_projection") if selected is not None else None
        ),
        "artifact_evidence": (
            (selected or {}).get("artifact_projection") if selected is not None else None
        ),
        "compliance_registry_authority": (
            dict(compliance_registry_authority) if selected is not None else None
        ),
    }
    registry_rows = registry.get("standards") if isinstance(registry, dict) else []
    latest_file_sha256, latest_receipt_digest = _capture_latest_state(
        data_root=root,
        project_id=pid,
        output_root=output_root,
    )
    effective_generated_at = generated_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    _parse_utc_timestamp(effective_generated_at)
    receipt_core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": effective_run_id,
        "generated_at": effective_generated_at,
        "project_id": pid,
        "mode": "no_model_formal_acceptance",
        "decision": "PASS" if gate.get("delivery_allowed") is True else "HOLD",
        "model_calls": 0,
        "provider_probes": 0,
        "runtime_state": "verified_healthy_sealed_release",
        "provider_admission": "not_probed",
        "provenance_trust": "local_owner_controlled",
        "cryptographic_attestation": False,
        "release": release,
        "inputs": {
            "tender": _snapshot_projection(tender_snapshot, label="tender_matrix.json"),
            "boq": _snapshot_projection(boq_snapshot, label="boq_data.json"),
            "plan": _snapshot_projection(
                plan_snapshot,
                label="plan.json",
                absent_witness=plan_absent,
            ),
            "ingest_audit": _snapshot_projection(
                audit_snapshot,
                label="audit/ingest.jsonl",
                absent_witness=audit_absent,
            ),
            "approval_audit": {
                **_snapshot_projection(
                    approval_audit_snapshot,
                    label="audit/project_fact_approvals.jsonl",
                    absent_witness=approval_audit_absent,
                ),
                **approval_projection,
            },
            "ingest_evidence_set": {
                "status": (
                    "verified" if ingest_validation.get("ok") is True else "unavailable"
                ),
                "digest": ingest_receipt.get("receipt_digest"),
                "record_count": len(ingest_receipt.get("records") or []),
            },
            "jobs": {
                "status": jobs_projection["status"],
                "digest": jobs_projection["digest"],
                "file_count": len(jobs_projection["files"]),
            },
            "events_directory": {
                "status": "present" if events_state is not None else "missing",
                "members_digest": (
                    events_state.members_digest
                    if events_state is not None
                    else canonical_digest([])
                ),
                "member_count": len(events_state.members) if events_state else 0,
                "absence_digest": (
                    canonical_digest(_witness_projection(events_absent))
                    if events_absent is not None
                    else None
                ),
            },
            "provider_admission_state": _snapshot_projection(
                provider_admission_snapshot,
                label="autoplan/provider_admission/provider-admission-v1.latest.json",
                absent_witness=provider_admission_absent,
            ),
            "official_registry": {
                **_snapshot_projection(
                    registry_snapshot,
                    label=SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix(),
                ),
                "entry_count": len(registry_rows) if isinstance(registry_rows, list) else 0,
                "realpath": str(registry_realpath),
                "source_kind": "current_sealed_registry_bytes",
                "standard_index_sha256": standards.get(
                    "official_registry_sha256"
                ),
                "authority_digest": compliance_registry_authority.get(
                    "authority_digest"
                ),
            },
        },
        "formal_source_eligibility": source_projection,
        "stages": stages,
        "machine_codes": list(
            dict.fromkeys(
                [source_code]
                + approval_machine_codes
                + stages["formal_delivery_gate"]["blocker_codes"]
                + ([] if cross_validation["ok"] else [cross_validation["machine_code"]])
            )
        ),
        "supersedes_receipt_digest": latest_receipt_digest,
    }
    receipt = {**receipt_core, "receipt_digest": canonical_digest(receipt_core)}
    witnesses = [
        snapshot
        for snapshot in (
            *release_witnesses,
            tender_snapshot,
            boq_snapshot,
            plan_snapshot,
            audit_snapshot,
            approval_audit_snapshot,
            plan_absent,
            audit_absent,
            approval_audit_absent,
            events_state,
            events_absent,
            provider_admission_snapshot,
            provider_admission_absent,
            manifest_snapshot,
            registry_snapshot,
            *ingest_witnesses,
            *((selected or {}).get("witnesses") or []),
            *(snapshot for snapshot, _payload in jobs),
        )
        if snapshot is not None
    ]
    if _release_projection(release_validator()) != release:
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_CHANGED", "验收计算期间当前发布或健康身份发生变化"
        )
    validation = validate_acceptance_receipt(receipt)
    if validation.get("ok") is not True:
        raise AcceptanceError(
            "ACCEPTANCE_RECEIPT_SCHEMA_INVALID",
            "生成的验收回执未通过严格schema校验",
        )
    prepared = object.__new__(_PreparedAcceptance)
    jobs_dir = root / "autoplan" / "jobs"
    effective_output_root = (
        Path(os.path.abspath(os.fspath(output_root)))
        if output_root is not None
        else None
    )
    object.__setattr__(prepared, "_receipt_bytes", canonical_json_bytes(receipt))
    object.__setattr__(
        prepared,
        "_ingest_receipt_bytes",
        canonical_json_bytes(ingest_receipt),
    )
    object.__setattr__(
        prepared,
        "_release_projection_bytes",
        canonical_json_bytes(release),
    )
    object.__setattr__(prepared, "witnesses", tuple(witnesses))
    object.__setattr__(prepared, "jobs_dir", jobs_dir)
    object.__setattr__(prepared, "jobs_digest", str(jobs_projection["digest"]))
    object.__setattr__(
        prepared,
        "jobs_directory_chain",
        (
            _capture_directory_chain(
                jobs_dir,
                code="ACCEPTANCE_JOBS_DIRECTORY_UNTRUSTED",
            )
            if jobs_dir.exists()
            else None
        ),
    )
    object.__setattr__(
        prepared,
        "expected_latest_file_sha256",
        latest_file_sha256,
    )
    object.__setattr__(prepared, "release_validator", release_validator)
    object.__setattr__(prepared, "data_root", root)
    object.__setattr__(prepared, "registry_path", registry_lexical_path)
    object.__setattr__(prepared, "output_root", effective_output_root)
    object.__setattr__(prepared, "_sealed", True)
    _PREPARED_CAPABILITIES[prepared] = _prepared_signature(prepared)
    return prepared


def verify_snapshot_stability(snapshot: _PreparedAcceptance) -> None:
    snapshot = _assert_prepared_capability(snapshot)
    for witness in snapshot.witnesses:
        if isinstance(witness, FileSnapshot):
            current = read_regular_file_snapshot(
                witness.path,
                max_bytes=(
                    _MAX_AUDIT_BYTES
                    if witness.path.name == "ingest.jsonl"
                    else _MAX_JSON_BYTES
                ),
            )
            stable = current is not None and (
                current.sha256,
                current.size,
                current.device,
                current.inode,
                current.mtime_ns,
                current.mode,
                current.directory_chain,
            ) == (
                witness.sha256,
                witness.size,
                witness.device,
                witness.inode,
                witness.mtime_ns,
                witness.mode,
                witness.directory_chain,
            )
        elif isinstance(witness, FileWitness):
            current_witness = read_regular_file_witness(
                witness.path,
                max_bytes=witness.max_bytes,
            )
            stable = (
                current_witness.sha256,
                current_witness.size,
                current_witness.device,
                current_witness.inode,
                current_witness.mtime_ns,
                current_witness.directory_chain,
            ) == (
                witness.sha256,
                witness.size,
                witness.device,
                witness.inode,
                witness.mtime_ns,
                witness.directory_chain,
            )
        elif isinstance(witness, DirectoryStateWitness):
            _verify_directory_state(witness, code="ACCEPTANCE_INPUT_CHANGED")
            stable = True
        elif isinstance(witness, AbsentPathWitness):
            _verify_absent_path_witness(witness, code="ACCEPTANCE_INPUT_CHANGED")
            stable = True
        else:
            raise AcceptanceError(
                "ACCEPTANCE_SNAPSHOT_WITNESSES_INVALID", "验收快照输入见证无效"
            )
        if not stable:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", f"验收期间输入发生变化：{witness.path.name}"
            )
    if snapshot.jobs_directory_chain is None:
        if snapshot.jobs_dir.exists():
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", "验收期间任务目录由缺失变为存在"
            )
    else:
        _verify_directory_chain(
            snapshot.jobs_directory_chain,
            code="ACCEPTANCE_INPUT_CHANGED",
        )
    _jobs, projection = _safe_job_snapshots(snapshot.jobs_dir)
    if projection["digest"] != snapshot.jobs_digest:
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_CHANGED", "验收期间任务目录发生变化"
        )
    ingest_receipt = snapshot.ingest_evidence_set_receipt
    if isinstance(ingest_receipt, Mapping) and ingest_receipt.get("records"):
        validation = validate_ingest_evidence_set_receipt(
            ingest_receipt,
            expected_project_id=str(snapshot.receipt.get("project_id") or ""),
        )
        if validation.get("ok") is not True:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", "验收期间入库证据集合发生变化"
            )
    if _release_projection(snapshot.release_validator()) != snapshot.release_projection:
        raise AcceptanceError(
            "ACCEPTANCE_RELEASE_CHANGED", "验收期间当前发布或健康身份发生变化"
        )


def _fixed_current_write_context() -> Mapping[str, Any]:
    """Resolve the production write authority through the non-injectable CLI path."""

    from scripts.refresh_no_model_formal_acceptance import (
        _fixed_current_write_context_impl,
    )

    return _fixed_current_write_context_impl()


def _verify_current_write_authority(
    prepared: _PreparedAcceptance,
) -> Mapping[str, Any]:
    expected = _CURRENT_WRITE_AUTHORITIES.get(prepared)
    if _SHA256_RE.fullmatch(str(expected or "")) is None:
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_ATTESTATION_REQUIRED",
            "离线或调用方合成的验收快照永久不可发布",
        )
    try:
        context = _fixed_current_write_context()
        authority_digest = str(context.get("authority_digest") or "").strip().lower()
        current_witness = context.get("current_witness")
        context_matches = bool(
            authority_digest == expected
            and _release_projection(context.get("release_identity") or {})
            == prepared.release_projection
            and Path(os.path.abspath(os.fspath(context.get("data_root"))))
            == prepared.data_root
            and Path(os.path.abspath(os.fspath(context.get("registry_path"))))
            == prepared.registry_path
            and prepared.output_root is None
            and isinstance(current_witness, FileSnapshot)
            and any(
                isinstance(witness, FileSnapshot)
                and witness.path == current_witness.path
                and witness.sha256 == current_witness.sha256
                and witness.size == current_witness.size
                and witness.device == current_witness.device
                and witness.inode == current_witness.inode
                and witness.mtime_ns == current_witness.mtime_ns
                and witness.mode == current_witness.mode
                for witness in prepared.witnesses
            )
        )
    except (AcceptanceError, AttributeError, KeyError, OSError, TypeError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_ATTESTATION_CHANGED",
            "current密封发布、真实运行态或固定路径无法复验",
        ) from exc
    if not context_matches:
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_ATTESTATION_CHANGED",
            "current密封发布、真实运行态或固定路径与签发快照不一致",
        )
    return context


def run_current_runtime_acceptance_write(
    *,
    project_id: str,
    run_id: str | None = None,
    source_job_id: str | None = None,
) -> dict[str, Any]:
    """The sole production-authorized write entrypoint; accepts no dependencies."""

    started = time.monotonic()
    context = _fixed_current_write_context()
    snapshot = collect_acceptance_snapshot(
        project_id=project_id,
        data_root=context["data_root"],
        registry_path=context["registry_path"],
        release_identity=context["release_identity"],
        release_witnesses=[context["current_witness"]],
        release_validator=context["release_validator"],
        output_root=None,
        run_id=run_id,
        source_job_id=source_job_id,
    )
    authority_digest = str(context.get("authority_digest") or "").strip().lower()
    if _SHA256_RE.fullmatch(authority_digest) is None:
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_ATTESTATION_INVALID",
            "正式写入准入摘要无效",
        )
    _CURRENT_WRITE_AUTHORITIES[snapshot] = authority_digest
    _PREPARED_CAPABILITIES[snapshot] = _prepared_signature(snapshot)
    _verify_current_write_authority(snapshot)
    verify_snapshot_stability(snapshot)
    receipt = snapshot.receipt
    return {
        "ok": True,
        "mode": "write",
        "decision": receipt["decision"],
        "receipt": receipt,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "write_result": publish_acceptance_receipt(snapshot),
    }


def _pass_stage_semantics_valid(stages: Mapping[str, Any]) -> bool:
    drawing = stages.get("drawing_index")
    standard = stages.get("standard_index")
    parameter = stages.get("project_parameter_evidence")
    ledger = stages.get("project_fact_ledger")
    checklist = stages.get("confirmation_checklist")
    cross = stages.get("cross_index")
    gate = stages.get("formal_delivery_gate")
    if not all(
        isinstance(row, Mapping)
        for row in (
            drawing,
            standard,
            parameter,
            ledger,
            checklist,
            cross,
            gate,
        )
    ):
        return False
    assert isinstance(drawing, Mapping)
    assert isinstance(standard, Mapping)
    assert isinstance(parameter, Mapping)
    assert isinstance(ledger, Mapping)
    assert isinstance(checklist, Mapping)
    assert isinstance(cross, Mapping)
    assert isinstance(gate, Mapping)
    readiness = ledger.get("formal_parameter_readiness")
    standard_rows = standard.get("standards")
    focus_count = cross.get("focus_count")
    return bool(
        drawing.get("ok") is True
        and isinstance(drawing.get("processed"), int)
        and not isinstance(drawing.get("processed"), bool)
        and drawing.get("processed", 0) > 0
        and isinstance(drawing.get("indexed"), int)
        and not isinstance(drawing.get("indexed"), bool)
        and drawing.get("indexed", 0) > 0
        and drawing.get("integrity_rejections") == 0
        and drawing.get("identity_errors") == 0
        and drawing.get("page_coverage_status") == "complete"
        and standard.get("ok") is True
        and isinstance(standard.get("indexed"), int)
        and not isinstance(standard.get("indexed"), bool)
        and standard.get("indexed", 0) > 0
        and standard.get("official_verified") == standard.get("indexed")
        and standard.get("integrity_rejections") == 0
        and standard.get("identity_errors") == 0
        and standard.get("missing_text_or_ocr") == 0
        and standard.get("locator_unavailable") == 0
        and isinstance(standard_rows, list)
        and len(standard_rows) == standard.get("indexed")
        and all(
            isinstance(row, Mapping)
            and row.get("identity_status") == "identified"
            and str(row.get("registry_status") or "").startswith("verified_")
            and isinstance(row.get("page_anchor_count"), int)
            and not isinstance(row.get("page_anchor_count"), bool)
            and row.get("page_anchor_count", 0) > 0
            for row in standard_rows
        )
        and parameter.get("ready") is True
        and parameter.get("coverage_complete") is True
        and parameter.get("conflict_count") == 0
        and isinstance(parameter.get("validation"), Mapping)
        and parameter["validation"].get("ok") is True
        and isinstance(ledger.get("validation"), Mapping)
        and ledger["validation"].get("ok") is True
        and isinstance(readiness, Mapping)
        and readiness.get("ready") is True
        and not (readiness.get("missing_fields") or [])
        and not (readiness.get("provisional_fields") or [])
        and not (ledger.get("unresolved_fields") or [])
        and checklist.get("formal_ready") is True
        and not (checklist.get("blocked_fields") or [])
        and isinstance(cross.get("validation"), Mapping)
        and cross["validation"].get("ok") is True
        and isinstance(focus_count, int)
        and not isinstance(focus_count, bool)
        and focus_count > 0
        and cross.get("mentioned_count") == focus_count
        and cross.get("closed_ok_count") == focus_count
        and cross.get("missing_drawing_locator_count") == 0
        and cross.get("missing_standard_locator_count") == 0
        and gate.get("delivery_allowed") is True
        and gate.get("blocker_count") == 0
        and gate.get("blocker_codes") == []
    )


def validate_acceptance_receipt(receipt: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(receipt, Mapping):
        return {"ok": False, "errors": ["receipt_not_object"]}
    value = dict(receipt)
    try:
        json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        errors.append("receipt_not_strict_json")
    if set(value) != _RECEIPT_TOP_LEVEL_FIELDS:
        errors.append("receipt_fields_invalid")
    if value.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    try:
        _validate_run_id(value.get("run_id"))
    except AcceptanceError:
        errors.append("run_id_invalid")
    try:
        _parse_utc_timestamp(value.get("generated_at"))
    except AcceptanceError:
        errors.append("generated_at_invalid")
    project_id = str(value.get("project_id") or "").strip()
    if not project_id:
        errors.append("project_id_invalid")
    if value.get("mode") != "no_model_formal_acceptance":
        errors.append("mode_invalid")
    if value.get("decision") not in {"PASS", "HOLD"}:
        errors.append("decision_invalid")
    if value.get("model_calls") != 0 or isinstance(value.get("model_calls"), bool):
        errors.append("model_calls_invalid")
    if value.get("provider_probes") != 0 or isinstance(
        value.get("provider_probes"), bool
    ):
        errors.append("provider_probes_invalid")
    if value.get("runtime_state") != "verified_healthy_sealed_release":
        errors.append("runtime_state_invalid")
    if value.get("provider_admission") != "not_probed":
        errors.append("provider_admission_invalid")
    if value.get("provenance_trust") != "local_owner_controlled":
        errors.append("provenance_trust_invalid")
    if value.get("cryptographic_attestation") is not False:
        errors.append("cryptographic_attestation_invalid")
    try:
        release = _release_projection(value.get("release") or {})
    except AcceptanceError:
        release = {}
        errors.append("release_invalid")

    inputs = value.get("inputs")
    expected_inputs = {
        "tender",
        "boq",
        "plan",
        "ingest_audit",
        "approval_audit",
        "ingest_evidence_set",
        "jobs",
        "events_directory",
        "provider_admission_state",
        "official_registry",
    }
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        errors.append("inputs_invalid")
        inputs = {}
    for field in (
        "tender",
        "boq",
        "plan",
        "ingest_audit",
        "provider_admission_state",
    ):
        row = inputs.get(field)
        if not isinstance(row, Mapping) or set(row) != {
            "label",
            "status",
            "sha256",
            "size",
            "absence_digest",
        }:
            errors.append(f"{field}_input_invalid")
            continue
        status_value = row.get("status")
        digest = row.get("sha256")
        size = row.get("size")
        if status_value not in {"present", "missing"}:
            errors.append(f"{field}_input_invalid")
        if status_value == "present" and _SHA256_RE.fullmatch(
            str(digest or "").lower()
        ) is None:
            errors.append(f"{field}_input_invalid")
        if status_value == "present" and row.get("absence_digest") is not None:
            errors.append(f"{field}_input_invalid")
        if status_value == "missing" and (
            digest is not None
            or _SHA256_RE.fullmatch(
                str(row.get("absence_digest") or "").lower()
            )
            is None
        ):
            errors.append(f"{field}_input_invalid")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            errors.append(f"{field}_input_invalid")
    approval_audit = inputs.get("approval_audit")
    if (
        not isinstance(approval_audit, Mapping)
        or set(approval_audit)
        != {
            "label",
            "status",
            "sha256",
            "size",
            "absence_digest",
            "requested_count",
            "verified_count",
            "rejected_count",
            "rejections_digest",
        }
        or approval_audit.get("label") != "audit/project_fact_approvals.jsonl"
        or approval_audit.get("status") not in {"present", "missing", "invalid"}
        or (
            approval_audit.get("status") == "present"
            and _SHA256_RE.fullmatch(
                str(approval_audit.get("sha256") or "").lower()
            )
            is None
        )
        or (
            approval_audit.get("status") == "present"
            and approval_audit.get("absence_digest") is not None
        )
        or (
            approval_audit.get("status") == "missing"
            and (
                approval_audit.get("sha256") is not None
                or _SHA256_RE.fullmatch(
                    str(approval_audit.get("absence_digest") or "").lower()
                )
                is None
                or approval_audit.get("size") != 0
                or approval_audit.get("requested_count") != 0
                or approval_audit.get("verified_count") != 0
                or approval_audit.get("rejected_count") != 0
            )
        )
        or any(
            isinstance(approval_audit.get(field), bool)
            or not isinstance(approval_audit.get(field), int)
            or approval_audit.get(field, -1) < 0
            for field in (
                "size",
                "requested_count",
                "verified_count",
                "rejected_count",
            )
        )
        or approval_audit.get("requested_count")
        != approval_audit.get("verified_count")
        + approval_audit.get("rejected_count")
        or (
            isinstance(approval_audit.get("verified_count"), int)
            and not isinstance(approval_audit.get("verified_count"), bool)
            and approval_audit.get("verified_count", 0) > 0
            and (
                approval_audit.get("status") != "present"
                or approval_audit.get("size", 0) <= 0
            )
        )
        or _SHA256_RE.fullmatch(
            str(approval_audit.get("rejections_digest") or "").lower()
        )
        is None
    ):
        errors.append("approval_audit_input_invalid")
    jobs = inputs.get("jobs")
    if (
        not isinstance(jobs, Mapping)
        or set(jobs) != {"status", "digest", "file_count"}
        or jobs.get("status") not in {"present", "missing"}
        or _SHA256_RE.fullmatch(str(jobs.get("digest") or "").lower()) is None
        or isinstance(jobs.get("file_count"), bool)
        or not isinstance(jobs.get("file_count"), int)
        or jobs.get("file_count", -1) < 0
    ):
        errors.append("jobs_input_invalid")
    events_directory = inputs.get("events_directory")
    if (
        not isinstance(events_directory, Mapping)
        or set(events_directory)
        != {"status", "members_digest", "member_count", "absence_digest"}
        or events_directory.get("status") not in {"present", "missing"}
        or _SHA256_RE.fullmatch(
            str(events_directory.get("members_digest") or "").lower()
        )
        is None
        or isinstance(events_directory.get("member_count"), bool)
        or not isinstance(events_directory.get("member_count"), int)
        or events_directory.get("member_count", -1) < 0
        or (
            events_directory.get("status") == "present"
            and events_directory.get("absence_digest") is not None
        )
        or (
            events_directory.get("status") == "missing"
            and (
                events_directory.get("member_count") != 0
                or events_directory.get("members_digest") != canonical_digest([])
                or _SHA256_RE.fullmatch(
                    str(events_directory.get("absence_digest") or "").lower()
                )
                is None
            )
        )
    ):
        errors.append("events_directory_input_invalid")
    ingest_set = inputs.get("ingest_evidence_set")
    if (
        not isinstance(ingest_set, Mapping)
        or set(ingest_set) != {"status", "digest", "record_count"}
        or ingest_set.get("status") not in {"verified", "unavailable"}
        or _SHA256_RE.fullmatch(str(ingest_set.get("digest") or "").lower())
        is None
        or isinstance(ingest_set.get("record_count"), bool)
        or not isinstance(ingest_set.get("record_count"), int)
        or ingest_set.get("record_count", -1) < 0
    ):
        errors.append("ingest_evidence_set_invalid")
    registry = inputs.get("official_registry")
    registry_fields = {
        "label",
        "status",
        "sha256",
        "size",
        "absence_digest",
        "entry_count",
        "realpath",
        "source_kind",
        "standard_index_sha256",
        "authority_digest",
    }
    if (
        not isinstance(registry, Mapping)
        or set(registry) != registry_fields
        or registry.get("status") != "present"
        or registry.get("label")
        != SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix()
        or registry.get("absence_digest") is not None
        or _SHA256_RE.fullmatch(str(registry.get("sha256") or "").lower())
        is None
        or registry.get("sha256") != registry.get("standard_index_sha256")
        or _SHA256_RE.fullmatch(
            str(registry.get("authority_digest") or "").lower()
        )
        is None
        or registry.get("source_kind") != "current_sealed_registry_bytes"
        or not Path(str(registry.get("realpath") or "")).is_absolute()
        or isinstance(registry.get("size"), bool)
        or not isinstance(registry.get("size"), int)
        or registry.get("size", -1) <= 0
        or isinstance(registry.get("entry_count"), bool)
        or not isinstance(registry.get("entry_count"), int)
        or registry.get("entry_count", -1) <= 0
    ):
        errors.append("official_registry_input_invalid")
    try:
        registry_authority_core = {
            "schema_version": SEALED_REGISTRY_AUTHORITY_SCHEMA,
            "source_kind": "sealed_release_manifest_entry",
            "release_id": release["release_id"],
            "manifest_digest": release["manifest_digest"],
            "source_digest": release["source_digest"],
            "runtime_digest": release["runtime_digest"],
            "registry_path": str(registry["realpath"]),
            "registry_relative_path": (
                SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix()
            ),
            "registry_sha256": str(registry["sha256"]),
            "registry_size": registry["size"],
            "registry_mode": 0o444,
        }
        reconstructed_registry_authority = (
            validate_registry_authority_projection(
                {
                    **registry_authority_core,
                    "authority_digest": canonical_digest(
                        registry_authority_core
                    ),
                }
            )
        )
        if (
            Path(str(registry["realpath"]))
            != Path(str(release["release_root"]))
            / SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH
            or registry.get("authority_digest")
            != reconstructed_registry_authority["authority_digest"]
        ):
            raise SealedComplianceError(
                "SEALED_COMPLIANCE_AUTHORITY_INVALID"
            )
    except (KeyError, SealedComplianceError, TypeError, ValueError):
        errors.append("official_registry_authority_invalid")

    stages = value.get("stages")
    expected_stages = {
        "drawing_index",
        "standard_index",
        "project_parameter_evidence",
        "project_fact_ledger",
        "confirmation_checklist",
        "cross_index",
        "formal_delivery_gate",
    }
    if not isinstance(stages, Mapping) or set(stages) != expected_stages:
        errors.append("stages_invalid")
        stages = {}
    for name in expected_stages:
        row = stages.get(name)
        if not isinstance(row, Mapping) or _SHA256_RE.fullmatch(
            str(row.get("digest") or "").lower()
        ) is None:
            errors.append(f"{name}_stage_invalid")
    expected_stage_fields = {
        "drawing_index": {
            "digest",
            "ok",
            "processed",
            "indexed",
            "graphics_only_pages",
            "integrity_rejections",
            "identity_errors",
            "text_status",
            "page_coverage_status",
            "chapter_binding_status",
        },
        "standard_index": {
            "digest",
            "ok",
            "official_registry_path",
            "official_registry_sha256",
            "indexed",
            "official_verified",
            "integrity_rejections",
            "identity_errors",
            "missing_text_or_ocr",
            "locator_unavailable",
            "chapter_binding_count",
            "chapter_binding_status",
            "standards",
        },
        "project_parameter_evidence": {
            "digest",
            "status",
            "ready",
            "coverage_complete",
            "conflict_count",
            "evidence_set_receipt_digest",
            "validation",
        },
        "project_fact_ledger": {
            "digest",
            "validation",
            "formal_parameter_readiness",
            "unresolved_fields",
        },
        "confirmation_checklist": {
            "digest",
            "formal_ready",
            "resolved_fields",
            "blocked_fields",
        },
        "cross_index": {
            "digest",
            "validation",
            "focus_count",
            "mentioned_count",
            "closed_ok_count",
            "missing_drawing_locator_count",
            "missing_standard_locator_count",
        },
        "formal_delivery_gate": {
            "digest",
            "delivery_allowed",
            "blocker_codes",
            "blocker_count",
            "formal_contract_version",
        },
    }
    for name, fields in expected_stage_fields.items():
        row = stages.get(name)
        if not isinstance(row, Mapping) or set(row) != fields:
            errors.append(f"{name}_stage_fields_invalid")
    standard_stage = stages.get("standard_index")
    if (
        isinstance(standard_stage, Mapping)
        and isinstance(registry, Mapping)
        and (
            standard_stage.get("official_registry_sha256")
            != registry.get("sha256")
            or Path(str(standard_stage.get("official_registry_path") or ""))
            != Path(str(registry.get("realpath") or ""))
        )
    ):
        errors.append("standard_registry_binding_invalid")
    formal_gate = stages.get("formal_delivery_gate")
    delivery_allowed = (
        formal_gate.get("delivery_allowed")
        if isinstance(formal_gate, Mapping)
        else None
    )
    if delivery_allowed is not (value.get("decision") == "PASS"):
        errors.append("decision_gate_mismatch")

    source = value.get("formal_source_eligibility")
    source_fields = {
        "eligible",
        "machine_code",
        "job_id",
        "variant_index",
        "variant_id",
        "result_sha256",
        "source_input_receipt_digest",
        "checkpoint_digest",
        "event_evidence",
        "artifact_evidence",
        "compliance_registry_authority",
    }
    event_evidence: Any = None
    artifact_evidence: Any = None
    if not isinstance(source, Mapping) or set(source) != source_fields:
        errors.append("formal_source_invalid")
    elif source.get("eligible") is True:
        event_evidence = source.get("event_evidence")
        artifact_evidence = source.get("artifact_evidence")
        try:
            source_authority = validate_registry_authority_projection(
                source.get("compliance_registry_authority")
            )
        except (SealedComplianceError, TypeError, ValueError):
            source_authority = None
        event_count_fields = (
            "event_count",
            "provider_attempt_count",
            "successful_chapter_count",
            "event_file_count",
        )
        provider_attempts_valid = (
            isinstance(event_evidence, Mapping)
            and isinstance(event_evidence.get("provider_attempts"), Mapping)
            and bool(event_evidence.get("provider_attempts"))
            and all(
                str(provider).strip()
                and isinstance(count, int)
                and not isinstance(count, bool)
                and count > 0
                for provider, count in event_evidence["provider_attempts"].items()
            )
        )
        admission_evidence = (
            event_evidence.get("provider_admission")
            if isinstance(event_evidence, Mapping)
            and isinstance(event_evidence.get("provider_admission"), Mapping)
            else {}
        )
        admitted_identities = admission_evidence.get(
            "admitted_route_identities"
        )
        required_roles = admission_evidence.get("required_roles")
        admitted_chain = admission_evidence.get("admitted_chain")
        identity_rows_valid = bool(
            isinstance(admitted_identities, list)
            and admitted_identities
            and all(
                isinstance(row, Mapping)
                and set(row)
                == {
                    "slot",
                    "role",
                    "provider",
                    "model",
                    "identity_digest",
                }
                and all(
                    str(row.get(field) or "").strip()
                    for field in ("slot", "role", "provider", "model")
                )
                and _SHA256_RE.fullmatch(
                    str(row.get("identity_digest") or "").strip().lower()
                )
                is not None
                for row in admitted_identities
            )
        )
        try:
            recomputed_admission_binding = (
                provider_admission_canonical_digest(
                    {
                        "schema_version": "provider-admission-binding-v1",
                        "required_roles": required_roles,
                        "admitted_route_identities": admitted_identities,
                    }
                )
                if identity_rows_valid
                and isinstance(required_roles, list)
                and all(isinstance(role, str) for role in required_roles)
                else None
            )
        except (OverflowError, TypeError, ValueError):
            recomputed_admission_binding = None
        identity_route_projection = (
            [
                {
                    field: str(row.get(field) or "").strip()
                    for field in ("slot", "role", "provider", "model")
                }
                for row in admitted_identities
            ]
            if identity_rows_valid
            else []
        )
        admission_valid = (
            bool(admission_evidence)
            and set(admission_evidence)
            == {
                "public_digest",
                "binding_digest",
                "durable_snapshot_digest",
                "durable_file_sha256",
                "required_roles",
                "admitted_chain",
                "admitted_route_identities",
                "document_render",
            }
            and _SHA256_RE.fullmatch(
                str(
                    admission_evidence.get("public_digest")
                    or ""
                )
            )
            is not None
            and _SHA256_RE.fullmatch(
                str(
                    admission_evidence.get("binding_digest")
                    or ""
                )
            )
            is not None
            and admission_evidence.get("binding_digest")
            == recomputed_admission_binding
            and _SHA256_RE.fullmatch(
                str(
                    admission_evidence.get("durable_snapshot_digest")
                    or ""
                )
            )
            is not None
            and _SHA256_RE.fullmatch(
                str(
                    admission_evidence.get("durable_file_sha256")
                    or ""
                )
            )
            is not None
            and isinstance(required_roles, list)
            and len(required_roles) == len(_FORMAL_PROVIDER_ROLES)
            and all(isinstance(role, str) for role in required_roles)
            and set(required_roles) == _FORMAL_PROVIDER_ROLES
            and isinstance(admitted_chain, list)
            and admitted_chain == identity_route_projection
            and _FORMAL_PROVIDER_ROLES.issubset(
                {row["role"] for row in identity_route_projection}
            )
            and sum(
                row["role"] == "document_render"
                for row in identity_route_projection
            )
            == 1
            and len({row["slot"] for row in identity_route_projection})
            == len(identity_route_projection)
            and admission_evidence.get("document_render")
            in [
                row
                for row in identity_route_projection
                if row["role"] == "document_render"
            ]
        )
        event_counts_valid = isinstance(event_evidence, Mapping) and all(
            isinstance(event_evidence.get(field), int)
            and not isinstance(event_evidence.get(field), bool)
            and event_evidence.get(field, 0) > 0
            for field in event_count_fields
        )
        artifact_count_valid = (
            isinstance(artifact_evidence, Mapping)
            and isinstance(artifact_evidence.get("artifact_count"), int)
            and not isinstance(artifact_evidence.get("artifact_count"), bool)
            and artifact_evidence.get("artifact_count", 0) > 0
            and isinstance(artifact_evidence.get("render_attempt_count"), int)
            and not isinstance(artifact_evidence.get("render_attempt_count"), bool)
            and artifact_evidence.get("render_attempt_count", 0) > 0
            and isinstance(artifact_evidence.get("render_provider_attempts"), Mapping)
            and bool(artifact_evidence.get("render_provider_attempts"))
        )
        if (
            source.get("machine_code") != "CURRENT_FORMAL_SOURCE_ELIGIBLE"
            or source_authority is None
            or not isinstance(registry, Mapping)
            or source_authority.get("authority_digest")
            != registry.get("authority_digest")
            or source_authority.get("registry_sha256") != registry.get("sha256")
            or source_authority.get("registry_size") != registry.get("size")
            or source_authority.get("registry_path") != registry.get("realpath")
            or source_authority.get("registry_relative_path")
            != SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH.as_posix()
            or source_authority.get("release_id") != release.get("release_id")
            or source_authority.get("manifest_digest")
            != release.get("manifest_digest")
            or source_authority.get("source_digest")
            != release.get("source_digest")
            or source_authority.get("runtime_digest")
            != release.get("runtime_digest")
            or Path(str(source_authority.get("registry_path") or ""))
            != Path(str(release.get("release_root") or ""))
            / SEALED_OFFICIAL_REGISTRY_RELATIVE_PATH
            or _JOB_ID_RE.fullmatch(str(source.get("job_id") or "")) is None
            or _SHA256_RE.fullmatch(str(source.get("result_sha256") or "")) is None
            or _SHA256_RE.fullmatch(
                str(source.get("source_input_receipt_digest") or "")
            )
            is None
            or _SHA256_RE.fullmatch(str(source.get("checkpoint_digest") or ""))
            is None
            or isinstance(source.get("variant_index"), bool)
            or not isinstance(source.get("variant_index"), int)
            or source.get("variant_index", -1) < 0
            or isinstance(source.get("variant_id"), bool)
            or not isinstance(source.get("variant_id"), int)
            or source.get("variant_id", 0) <= 0
            or not isinstance(event_evidence, Mapping)
            or not event_counts_valid
            or set(event_evidence)
            != {
                "event_count",
                "provider_attempt_count",
                "provider_attempts",
                "successful_chapter_count",
                "event_file_count",
                "event_bundle_digest",
                "event_directory_members_digest",
                "provider_admission",
                "attempt_id",
                "owner_instance_id",
                "job_revision",
                "chapter_routes",
            }
            or not provider_attempts_valid
            or not admission_valid
            or _SHA256_RE.fullmatch(
                str((event_evidence or {}).get("event_bundle_digest") or "")
            )
            is None
            or _SHA256_RE.fullmatch(
                str(
                    (event_evidence or {}).get("event_directory_members_digest")
                    or ""
                )
            )
            is None
            or (event_evidence or {}).get("event_directory_members_digest")
            != (inputs.get("events_directory") or {}).get("members_digest")
            or (
                (event_evidence or {}).get("provider_admission") or {}
            ).get("durable_file_sha256")
            != (inputs.get("provider_admission_state") or {}).get("sha256")
            or _EXECUTION_ID_RE.fullmatch(
                str((event_evidence or {}).get("attempt_id") or "")
            )
            is None
            or _EXECUTION_ID_RE.fullmatch(
                str((event_evidence or {}).get("owner_instance_id") or "")
            )
            is None
            or isinstance((event_evidence or {}).get("job_revision"), bool)
            or not isinstance((event_evidence or {}).get("job_revision"), int)
            or int((event_evidence or {}).get("job_revision") or 0) <= 0
            or not isinstance((event_evidence or {}).get("chapter_routes"), list)
            or len((event_evidence or {}).get("chapter_routes") or [])
            != (event_evidence or {}).get("successful_chapter_count")
            or any(
                not isinstance(route, Mapping)
                or set(route) != {"chapter_index", "slot", "provider", "model"}
                or route.get("chapter_index") != index
                or not all(
                    str(route.get(field) or "").strip()
                    for field in ("slot", "provider", "model")
                )
                for index, route in enumerate(
                    (event_evidence or {}).get("chapter_routes") or [],
                    start=1,
                )
            )
            or not isinstance(artifact_evidence, Mapping)
            or not artifact_count_valid
            or set(artifact_evidence)
            != {
                "artifact_count",
                "delivery_receipt_digest",
                "artifact_set_digest",
                "render_attempt_count",
                "render_provider_attempts",
            }
            or _SHA256_RE.fullmatch(
                str((artifact_evidence or {}).get("delivery_receipt_digest") or "")
            )
            is None
            or _SHA256_RE.fullmatch(
                str((artifact_evidence or {}).get("artifact_set_digest") or "")
            )
            is None
            or any(
                not str(provider).strip()
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count <= 0
                for provider, count in (
                    artifact_evidence.get("render_provider_attempts") or {}
                ).items()
            )
        ):
            errors.append("formal_source_invalid")
    elif (
        source.get("eligible") is not False
        or not str(source.get("machine_code") or "").startswith("HOLD_")
        or any(
            source.get(field) is not None
            for field in source_fields - {"eligible", "machine_code"}
        )
    ):
        errors.append("formal_source_invalid")

    machine_codes = value.get("machine_codes")
    if (
        not isinstance(machine_codes, list)
        or not machine_codes
        or any(not isinstance(code, str) or not code for code in machine_codes)
        or len(set(machine_codes)) != len(machine_codes)
        or not isinstance(source, Mapping)
        or machine_codes[0] != source.get("machine_code")
    ):
        errors.append("machine_codes_invalid")
    if value.get("decision") == "PASS" and (
        not isinstance(source, Mapping)
        or source.get("eligible") is not True
        or not isinstance(jobs, Mapping)
        or jobs.get("status") != "present"
        or jobs.get("file_count", 0) <= 0
        or not isinstance(events_directory, Mapping)
        or events_directory.get("status") != "present"
        or events_directory.get("member_count", 0) <= 0
        or not isinstance(event_evidence, Mapping)
        or events_directory.get("member_count")
        != event_evidence.get("event_file_count")
        or not provider_attempts_valid
        or event_evidence.get("provider_attempt_count")
        != sum((event_evidence.get("provider_attempts") or {}).values())
        or not isinstance(artifact_evidence, Mapping)
        or not artifact_count_valid
        or artifact_evidence.get("render_attempt_count")
        != sum((artifact_evidence.get("render_provider_attempts") or {}).values())
        or not isinstance(approval_audit, Mapping)
        or approval_audit.get("status") == "invalid"
        or approval_audit.get("rejected_count") != 0
        or approval_audit.get("requested_count")
        != approval_audit.get("verified_count")
        or (
            isinstance(approval_audit.get("verified_count"), int)
            and not isinstance(approval_audit.get("verified_count"), bool)
            and approval_audit.get("verified_count", 0) > 0
            and (
                approval_audit.get("status") != "present"
                or approval_audit.get("size", 0) <= 0
            )
        )
        or not isinstance(ingest_set, Mapping)
        or ingest_set.get("status") != "verified"
        or not isinstance(standard_stage, Mapping)
        or standard_stage.get("ok") is not True
        or delivery_allowed is not True
        or not isinstance(stages, Mapping)
        or not _pass_stage_semantics_valid(stages)
        or machine_codes != ["CURRENT_FORMAL_SOURCE_ELIGIBLE"]
        or any(str(code).startswith("HOLD_") for code in (machine_codes or []))
    ):
        errors.append("pass_preconditions_invalid")
    supersedes = value.get("supersedes_receipt_digest")
    if supersedes is not None and _SHA256_RE.fullmatch(str(supersedes)) is None:
        errors.append("supersedes_receipt_digest_invalid")
    if release and not receipt_digest_is_valid(value):
        errors.append("receipt_digest_invalid")
    return {"ok": not errors, "errors": list(dict.fromkeys(errors))}


def _open_owned_child_directory(
    parent_fd: int,
    name: str,
    *,
    create: bool,
) -> int:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    created = False
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "验收回执子目录不可信"
        ) from exc
    try:
        _validate_owned_directory_fd(descriptor)
        if created:
            os.fchmod(descriptor, 0o700)
            _validate_owned_directory_fd(descriptor)
            os.fsync(descriptor)
            os.fsync(parent_fd)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _verify_owned_child_directory(
    parent_fd: int,
    name: str,
    descriptor: int,
) -> None:
    opened = _validate_owned_directory_fd(descriptor)
    try:
        try:
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", "回执文件在读取期间发生变化"
            ) from exc
    except OSError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
            "验收回执子目录已发生变化",
        ) from exc
    if (
        not stat.S_ISDIR(current.st_mode)
        or stat.S_ISLNK(current.st_mode)
        or (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino)
    ):
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_DIRECTORY_CHANGED",
            "验收回执子目录已发生变化",
        )


def _verify_publish_lock(
    handle: _OutputDirectoryHandle,
    descriptor: int,
) -> None:
    try:
        opened = os.fstat(descriptor)
        current = os.stat(
            ".publish.lock",
            dir_fd=handle.fd,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_PUBLICATION_LOCK_CHANGED",
            "发布锁目录项已发生变化",
        ) from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_uid != os.getuid()
        or opened.st_nlink != 1
        or stat.S_IMODE(opened.st_mode) != 0o600
        or not _same_file_identity(opened, current)
    ):
        raise AcceptanceError(
            "ACCEPTANCE_PUBLICATION_LOCK_CHANGED",
            "发布锁目录项已发生变化",
        )


def _read_regular_bytes_at(
    parent_fd: int,
    name: str,
    *,
    allow_missing: bool = False,
    max_bytes: int = _MAX_JSON_BYTES,
) -> tuple[bytes, os.stat_result] | None:
    if Path(name).name != name or name in {"", ".", ".."}:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执文件名无效"
        )
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except FileNotFoundError:
        if allow_missing:
            return None
        raise AcceptanceError(
            "ACCEPTANCE_INPUT_MISSING", f"缺少回执文件：{name}"
        ) from None
    except OSError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执文件类型不可信"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid():
            raise AcceptanceError(
                "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "回执文件类型或所有者不可信"
            )
        if before.st_size < 0 or before.st_size > max_bytes:
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_TOO_LARGE", "回执文件超过允许大小"
            )
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not _same_file_identity(before, after)
            or not _same_file_identity(after, current)
            or len(raw) != before.st_size
        ):
            raise AcceptanceError(
                "ACCEPTANCE_INPUT_CHANGED", "回执文件在读取期间发生变化"
            )
        return raw, before
    finally:
        os.close(descriptor)


def _verify_publication_precommit(
    prepared: _PreparedAcceptance,
    *,
    handle: _OutputDirectoryHandle,
    lock_descriptor: int,
    successors_descriptor: int | None = None,
) -> None:
    """Revalidate every authority immediately before/after namespace commits."""

    _verify_current_write_authority(prepared)
    verify_snapshot_stability(prepared)
    _verify_publish_lock(handle, lock_descriptor)
    handle.verify_namespace()
    if successors_descriptor is not None:
        _verify_owned_child_directory(
            handle.fd,
            "successors",
            successors_descriptor,
        )


def _recover_pending_successor(
    *,
    prepared: _PreparedAcceptance,
    handle: _OutputDirectoryHandle,
    successors_descriptor: int,
    predecessor_name: str,
    latest_file_sha256: str | None,
    latest_receipt_digest: str | None,
    project_id: str,
    lock_descriptor: int,
) -> bool:
    _verify_publication_precommit(
        prepared,
        handle=handle,
        lock_descriptor=lock_descriptor,
        successors_descriptor=successors_descriptor,
    )
    claim_result = _read_regular_bytes_at(
        successors_descriptor,
        predecessor_name,
        allow_missing=True,
    )
    if claim_result is None:
        return False
    claim_raw, claim_info = claim_result
    try:
        claim = _strict_json_loads(claim_raw.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceError(
            "ACCEPTANCE_SUCCESSOR_CLAIM_INVALID",
            "权威后继声明无法验证",
        ) from exc
    if not isinstance(claim, dict):
        raise AcceptanceError(
            "ACCEPTANCE_SUCCESSOR_CLAIM_INVALID",
            "权威后继声明无法验证",
        )
    expected_fields = {
        "schema_version",
        "previous_latest_file_sha256",
        "previous_receipt_digest",
        "run_id",
        "receipt_digest",
        "immutable_name",
        "immutable_file_sha256",
        "claim_digest",
    }
    core = {key: value for key, value in claim.items() if key != "claim_digest"}
    run_id = str(claim.get("run_id") or "")
    immutable_name = str(claim.get("immutable_name") or "")
    if (
        set(claim) != expected_fields
        or stat.S_IMODE(claim_info.st_mode) != 0o400
        or claim.get("schema_version") != "autoplan-acceptance-successor-v1"
        or claim.get("previous_latest_file_sha256") != latest_file_sha256
        or claim.get("previous_receipt_digest") != latest_receipt_digest
        or str(claim.get("claim_digest") or "") != canonical_digest(core)
        or _SHA256_RE.fullmatch(str(claim.get("receipt_digest") or "")) is None
        or _SHA256_RE.fullmatch(
            str(claim.get("immutable_file_sha256") or "")
        )
        is None
    ):
        raise AcceptanceError(
            "ACCEPTANCE_SUCCESSOR_CLAIM_INVALID",
            "权威后继声明无法验证",
        )
    try:
        validated_run_id = _validate_run_id(run_id)
    except AcceptanceError as exc:
        raise AcceptanceError(
            "ACCEPTANCE_SUCCESSOR_CLAIM_INVALID",
            "权威后继声明无法验证",
        ) from exc
    if immutable_name != f"{validated_run_id}.json":
        raise AcceptanceError(
            "ACCEPTANCE_SUCCESSOR_CLAIM_INVALID",
            "权威后继声明无法验证",
        )
    immutable_result = _read_regular_snapshot_at(handle, immutable_name)
    assert immutable_result is not None
    immutable, immutable_info = immutable_result
    receipt = _decode_json(immutable)
    if (
        stat.S_IMODE(immutable_info.st_mode) != 0o400
        or immutable.sha256 != claim.get("immutable_file_sha256")
        or not validate_acceptance_receipt(receipt).get("ok")
        or str(receipt.get("project_id") or "").strip() != project_id
        or receipt.get("run_id") != validated_run_id
        or receipt.get("receipt_digest") != claim.get("receipt_digest")
        or receipt.get("supersedes_receipt_digest") != latest_receipt_digest
    ):
        raise AcceptanceError(
            "ACCEPTANCE_SUCCESSOR_CLAIM_INVALID",
            "权威后继声明未绑定有效不可变回执",
        )
    current_sha, current_digest = _capture_latest_state(
        data_root=handle.root_path,
        project_id=project_id,
        output_root=handle.output_path.parent,
        handle=handle,
    )
    if current_sha != latest_file_sha256 or current_digest != latest_receipt_digest:
        raise AcceptanceError(
            "ACCEPTANCE_LATEST_CONCURRENT_UPDATE",
            "latest已由另一验收运行更新",
        )
    temp_name = f".recover.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    descriptor = -1
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    primary_error: BaseException | None = None
    try:
        descriptor = os.open(temp_name, flags, 0o600, dir_fd=handle.fd)
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, immutable.raw)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        _verify_publication_precommit(
            prepared,
            handle=handle,
            lock_descriptor=lock_descriptor,
            successors_descriptor=successors_descriptor,
        )
        os.rename(
            temp_name,
            "latest.json",
            src_dir_fd=handle.fd,
            dst_dir_fd=handle.fd,
        )
        os.fsync(handle.fd)
        _verify_publication_precommit(
            prepared,
            handle=handle,
            lock_descriptor=lock_descriptor,
            successors_descriptor=successors_descriptor,
        )
        recovered_sha, recovered_digest = _capture_latest_state(
            data_root=handle.root_path,
            project_id=project_id,
            output_root=handle.output_path.parent,
            handle=handle,
        )
        if (
            recovered_sha != hashlib.sha256(immutable.raw).hexdigest()
            or recovered_digest != receipt.get("receipt_digest")
        ):
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_VERIFY_FAILED",
                "恢复后的latest回执反读校验失败",
            )
        _verify_owned_child_directory(handle.fd, "successors", successors_descriptor)
        handle.verify_namespace()
        return True
    except BaseException as exc:  # noqa: BLE001 - cleanup must precede reraising
        primary_error = exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        cleanup_error = _cleanup_entry_error(
            handle.fd,
            temp_name,
            sync_fd=handle.fd,
            code="ACCEPTANCE_RECOVERY_TEMP_CLEANUP_FAILED",
            message="恢复latest后无法清理暂存文件",
        )
        _raise_after_cleanup(primary_error, cleanup_error)


def _predecessor_claim_name(
    latest_file_sha256: str | None,
    latest_receipt_digest: str | None,
) -> str:
    material = canonical_json_bytes(
        {
            "latest_file_sha256": latest_file_sha256,
            "latest_receipt_digest": latest_receipt_digest,
        }
    )
    return hashlib.sha256(material).hexdigest() + ".json"


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        offset += written


def _unlink_output_file_or_fail(
    handle: _OutputDirectoryHandle,
    name: str,
    *,
    code: str,
    message: str,
) -> None:
    try:
        os.unlink(name, dir_fd=handle.fd)
        os.fsync(handle.fd)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise AcceptanceError(code, message) from exc


def _reconcile_hardlink_at(
    parent_fd: int,
    name: str,
    *,
    expected_raw: bytes,
    expected_info: os.stat_result,
    expected_mode: int,
    code: str,
    message: str,
    allow_missing: bool,
) -> bool:
    result = _read_regular_bytes_at(
        parent_fd,
        name,
        allow_missing=allow_missing,
    )
    if result is None:
        return False
    raw, info = result
    if (
        (info.st_dev, info.st_ino)
        != (expected_info.st_dev, expected_info.st_ino)
        or raw != expected_raw
        or stat.S_IMODE(info.st_mode) != expected_mode
    ):
        raise AcceptanceError(code, message)
    return True


def _cleanup_entry_error(
    parent_fd: int,
    name: str,
    *,
    sync_fd: int,
    code: str,
    message: str,
) -> AcceptanceError | None:
    try:
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(sync_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        error = AcceptanceError(code, message)
        error.__cause__ = exc
        return error
    return None


def _raise_after_cleanup(
    primary_error: BaseException | None,
    cleanup_error: AcceptanceError | None,
) -> None:
    if primary_error is not None:
        if isinstance(primary_error, (KeyboardInterrupt, SystemExit)):
            raise primary_error.with_traceback(primary_error.__traceback__)
        if cleanup_error is not None:
            raise cleanup_error
        raise primary_error.with_traceback(primary_error.__traceback__)
    if cleanup_error is not None:
        raise cleanup_error


def _receipt_bytes(receipt: Mapping[str, Any]) -> bytes:
    validation = validate_acceptance_receipt(receipt)
    if validation.get("ok") is not True:
        raise AcceptanceError(
            "ACCEPTANCE_RECEIPT_SCHEMA_INVALID", "回执未通过严格schema与摘要校验"
        )
    return json.dumps(
        dict(receipt),
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ).encode("utf-8") + b"\n"


def publish_acceptance_receipt(
    prepared: _PreparedAcceptance,
) -> dict[str, Any]:
    prepared = _assert_prepared_capability(prepared)
    _verify_current_write_authority(prepared)
    receipt = prepared.receipt
    run_id = _validate_run_id(receipt.get("run_id"))
    project_id = str(receipt.get("project_id") or "").strip()
    root = _validate_root(
        prepared.data_root, code="ACCEPTANCE_DATA_ROOT_UNTRUSTED"
    )
    # Detect a changed release/evidence set before creating any receipt path.
    verify_snapshot_stability(prepared)
    payload = _receipt_bytes(receipt)
    final_name = f"{run_id}.json"
    latest_name = "latest.json"
    temp_name = f".latest.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    immutable_temp_name = (
        f".immutable.{run_id}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    immutable_created = False
    successor_committed = False
    if final_name == latest_name:
        raise AcceptanceError(
            "ACCEPTANCE_RUN_ID_INVALID", "不可变回执路径不得与latest重合"
        )
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    handle: _OutputDirectoryHandle | None = None
    lock_descriptor = -1
    successors_descriptor = -1
    try:
        handle = _open_output_directory_handle(
            data_root=root,
            project_id=project_id,
            output_root=prepared.output_root,
            create=True,
        )
        assert handle is not None
        handle.verify_namespace()
        lock_created = False
        lock_flags = (
            os.O_RDWR
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        try:
            lock_descriptor = os.open(
                ".publish.lock",
                lock_flags | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=handle.fd,
            )
            lock_created = True
        except FileExistsError:
            lock_descriptor = os.open(
                ".publish.lock",
                lock_flags,
                dir_fd=handle.fd,
            )
        lock_info = os.fstat(lock_descriptor)
        current_lock_info = os.stat(
            ".publish.lock",
            dir_fd=handle.fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(lock_info.st_mode)
            or lock_info.st_uid != os.getuid()
            or lock_info.st_nlink != 1
            or not _same_file_identity(lock_info, current_lock_info)
            or (
                not lock_created
                and stat.S_IMODE(lock_info.st_mode) != 0o600
            )
        ):
            raise AcceptanceError(
                "ACCEPTANCE_OUTPUT_PATH_UNTRUSTED", "发布锁文件类型或所有者不可信"
            )
        if lock_created:
            os.fchmod(lock_descriptor, 0o600)
            os.fsync(lock_descriptor)
            os.fsync(handle.fd)
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AcceptanceError(
                "ACCEPTANCE_WRITE_LOCKED",
                "已有验收回执发布正在进行，拒绝等待或重试",
            ) from exc
        _verify_publish_lock(handle, lock_descriptor)

        verify_snapshot_stability(prepared)
        _verify_publish_lock(handle, lock_descriptor)
        handle.verify_namespace()
        current_latest_sha, current_latest_digest = _capture_latest_state(
            data_root=root,
            project_id=project_id,
            output_root=prepared.output_root,
            handle=handle,
        )
        if current_latest_sha != prepared.expected_latest_file_sha256 or (
            current_latest_digest != receipt.get("supersedes_receipt_digest")
        ):
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_CONCURRENT_UPDATE",
                "latest已由另一验收运行更新，拒绝旧结果覆盖",
            )
        successors_descriptor = _open_owned_child_directory(
            handle.fd,
            "successors",
            create=True,
        )
        _verify_owned_child_directory(
            handle.fd,
            "successors",
            successors_descriptor,
        )
        predecessor_name = _predecessor_claim_name(
            current_latest_sha,
            current_latest_digest,
        )
        if _recover_pending_successor(
            prepared=prepared,
            handle=handle,
            successors_descriptor=successors_descriptor,
            predecessor_name=predecessor_name,
            latest_file_sha256=current_latest_sha,
            latest_receipt_digest=current_latest_digest,
            project_id=project_id,
            lock_descriptor=lock_descriptor,
        ):
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_CONCURRENT_UPDATE",
                "已恢复前一正式后继，当前快照必须重新收集",
            )
        descriptor = -1
        immutable_temp_created = False
        immutable_primary_error: BaseException | None = None
        try:
            descriptor = os.open(
                immutable_temp_name,
                flags,
                0o400,
                dir_fd=handle.fd,
            )
            immutable_temp_created = True
            os.fchmod(descriptor, 0o400)
            _write_all(descriptor, payload)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = -1
            staged_result = _read_regular_snapshot_at(
                handle,
                immutable_temp_name,
            )
            assert staged_result is not None
            staged_immutable, staged_info = staged_result
            if (
                staged_immutable.raw != payload
                or stat.S_IMODE(staged_info.st_mode) != 0o400
                or not validate_acceptance_receipt(
                    _decode_json(staged_immutable)
                ).get("ok")
            ):
                raise AcceptanceError(
                    "ACCEPTANCE_IMMUTABLE_VERIFY_FAILED",
                    "不可变回执暂存反读校验失败",
                )
            _verify_publication_precommit(
                prepared,
                handle=handle,
                lock_descriptor=lock_descriptor,
                successors_descriptor=successors_descriptor,
            )
            if _read_regular_bytes_at(
                handle.fd,
                final_name,
                allow_missing=True,
            ) is not None:
                raise FileExistsError(final_name)
            try:
                os.link(
                    immutable_temp_name,
                    final_name,
                    src_dir_fd=handle.fd,
                    dst_dir_fd=handle.fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                raise
            except BaseException as link_error:
                try:
                    immutable_created = _reconcile_hardlink_at(
                        handle.fd,
                        final_name,
                        expected_raw=staged_immutable.raw,
                        expected_info=staged_info,
                        expected_mode=0o400,
                        code="ACCEPTANCE_IMMUTABLE_VERIFY_FAILED",
                        message="不可变回执提交状态无法确认",
                        allow_missing=True,
                    )
                except AcceptanceError:
                    if isinstance(link_error, (KeyboardInterrupt, SystemExit)):
                        raise link_error.with_traceback(link_error.__traceback__)
                    raise
                raise
            immutable_created = _reconcile_hardlink_at(
                handle.fd,
                final_name,
                expected_raw=staged_immutable.raw,
                expected_info=staged_info,
                expected_mode=0o400,
                code="ACCEPTANCE_IMMUTABLE_VERIFY_FAILED",
                message="不可变回执提交后反验失败",
                allow_missing=False,
            )
            os.fsync(handle.fd)
            _verify_publication_precommit(
                prepared,
                handle=handle,
                lock_descriptor=lock_descriptor,
                successors_descriptor=successors_descriptor,
            )
        except FileExistsError as exc:
            immutable_primary_error = AcceptanceError(
                "ACCEPTANCE_RUN_ID_EXISTS", "同名不可变回执已存在，拒绝覆盖"
            )
            immutable_primary_error.__cause__ = exc
        except AcceptanceError as exc:
            immutable_primary_error = exc
        except (KeyboardInterrupt, SystemExit) as exc:
            immutable_primary_error = exc
        except Exception as exc:  # noqa: BLE001
            immutable_primary_error = AcceptanceError(
                "ACCEPTANCE_IMMUTABLE_WRITE_FAILED", "不可变回执写入失败"
            )
            immutable_primary_error.__cause__ = exc
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            cleanup_error = None
            if immutable_temp_created:
                cleanup_error = _cleanup_entry_error(
                    handle.fd,
                    immutable_temp_name,
                    sync_fd=handle.fd,
                    code="ACCEPTANCE_IMMUTABLE_TEMP_CLEANUP_FAILED",
                    message="未提交的不可变回执暂存文件无法安全清理",
                )
            _raise_after_cleanup(immutable_primary_error, cleanup_error)

        immutable_result = _read_regular_snapshot_at(handle, final_name)
        assert immutable_result is not None
        immutable, immutable_info = immutable_result
        if (
            immutable.raw != payload
            or stat.S_IMODE(immutable_info.st_mode) != 0o400
            or not validate_acceptance_receipt(_decode_json(immutable)).get("ok")
        ):
            raise AcceptanceError(
                "ACCEPTANCE_IMMUTABLE_VERIFY_FAILED", "不可变回执反读校验失败"
            )

        latest_descriptor = -1
        latest_primary_error: BaseException | None = None
        try:
            latest_descriptor = os.open(
                temp_name,
                flags,
                0o600,
                dir_fd=handle.fd,
            )
            os.fchmod(latest_descriptor, 0o600)
            _write_all(latest_descriptor, payload)
            os.fsync(latest_descriptor)
            os.close(latest_descriptor)
            latest_descriptor = -1

            # The final stability check is immediately adjacent to publication.
            verify_snapshot_stability(prepared)
            latest_sha, latest_digest = _capture_latest_state(
                data_root=root,
                project_id=project_id,
                output_root=prepared.output_root,
                handle=handle,
            )
            if (
                latest_sha != prepared.expected_latest_file_sha256
                or latest_digest != receipt.get("supersedes_receipt_digest")
            ):
                raise AcceptanceError(
                    "ACCEPTANCE_LATEST_CONCURRENT_UPDATE",
                    "latest在发布前发生变化，拒绝覆盖",
                )
            _verify_publish_lock(handle, lock_descriptor)
            handle.verify_namespace()
            _verify_owned_child_directory(
                handle.fd,
                "successors",
                successors_descriptor,
            )
            claim_core = {
                "schema_version": "autoplan-acceptance-successor-v1",
                "previous_latest_file_sha256": latest_sha,
                "previous_receipt_digest": latest_digest,
                "run_id": run_id,
                "receipt_digest": receipt["receipt_digest"],
                "immutable_name": final_name,
                "immutable_file_sha256": immutable.sha256,
            }
            claim = {
                **claim_core,
                "claim_digest": canonical_digest(claim_core),
            }
            claim_payload = json.dumps(
                claim,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8") + b"\n"
            claim_temp_name = f".claim.{os.getpid()}.{uuid.uuid4().hex}.tmp"
            claim_descriptor = -1
            claim_linked = False
            claim_primary_error: BaseException | None = None
            try:
                claim_descriptor = os.open(
                    claim_temp_name,
                    flags,
                    0o400,
                    dir_fd=successors_descriptor,
                )
                os.fchmod(claim_descriptor, 0o400)
                _write_all(claim_descriptor, claim_payload)
                os.fsync(claim_descriptor)
                os.close(claim_descriptor)
                claim_descriptor = -1
                claim_temp_result = _read_regular_bytes_at(
                    successors_descriptor,
                    claim_temp_name,
                )
                assert claim_temp_result is not None
                claim_temp_raw, claim_temp_info = claim_temp_result
                if (
                    claim_temp_raw != claim_payload
                    or stat.S_IMODE(claim_temp_info.st_mode) != 0o400
                ):
                    raise AcceptanceError(
                        "ACCEPTANCE_SUCCESSOR_WRITE_FAILED",
                        "权威后继声明暂存反验失败",
                    )
                _verify_publication_precommit(
                    prepared,
                    handle=handle,
                    lock_descriptor=lock_descriptor,
                    successors_descriptor=successors_descriptor,
                )
                if _read_regular_bytes_at(
                    successors_descriptor,
                    predecessor_name,
                    allow_missing=True,
                ) is not None:
                    raise FileExistsError(predecessor_name)
                try:
                    os.link(
                        claim_temp_name,
                        predecessor_name,
                        src_dir_fd=successors_descriptor,
                        dst_dir_fd=successors_descriptor,
                        follow_symlinks=False,
                    )
                except FileExistsError:
                    raise
                except BaseException as link_error:
                    try:
                        claim_linked = _reconcile_hardlink_at(
                            successors_descriptor,
                            predecessor_name,
                            expected_raw=claim_temp_raw,
                            expected_info=claim_temp_info,
                            expected_mode=0o400,
                            code="ACCEPTANCE_SUCCESSOR_WRITE_FAILED",
                            message="权威后继声明提交状态无法确认",
                            allow_missing=True,
                        )
                    except AcceptanceError:
                        if isinstance(
                            link_error,
                            (KeyboardInterrupt, SystemExit),
                        ):
                            raise link_error.with_traceback(
                                link_error.__traceback__
                            )
                        raise
                    raise
                claim_linked = _reconcile_hardlink_at(
                    successors_descriptor,
                    predecessor_name,
                    expected_raw=claim_temp_raw,
                    expected_info=claim_temp_info,
                    expected_mode=0o400,
                    code="ACCEPTANCE_SUCCESSOR_WRITE_FAILED",
                    message="权威后继声明提交后反验失败",
                    allow_missing=False,
                )
                os.fsync(successors_descriptor)
                _verify_publication_precommit(
                    prepared,
                    handle=handle,
                    lock_descriptor=lock_descriptor,
                    successors_descriptor=successors_descriptor,
                )
                successor_committed = True
            except FileExistsError as exc:
                try:
                    recovered = _recover_pending_successor(
                        prepared=prepared,
                        handle=handle,
                        successors_descriptor=successors_descriptor,
                        predecessor_name=predecessor_name,
                        latest_file_sha256=latest_sha,
                        latest_receipt_digest=latest_digest,
                        project_id=project_id,
                        lock_descriptor=lock_descriptor,
                    )
                except BaseException as recovery_error:  # noqa: BLE001
                    claim_primary_error = recovery_error
                else:
                    claim_primary_error = AcceptanceError(
                        "ACCEPTANCE_LATEST_CONCURRENT_UPDATE",
                        (
                            "已恢复并发正式后继，当前快照必须重新收集"
                            if recovered
                            else "同一latest前序已有正式后继，拒绝并发覆盖"
                        ),
                    )
                    claim_primary_error.__cause__ = exc
            except AcceptanceError as exc:
                claim_primary_error = exc
            except (KeyboardInterrupt, SystemExit) as exc:
                claim_primary_error = exc
            except OSError as exc:
                claim_primary_error = AcceptanceError(
                    "ACCEPTANCE_SUCCESSOR_WRITE_FAILED",
                    "无法写入权威后继声明",
                )
                claim_primary_error.__cause__ = exc
            except Exception as exc:  # noqa: BLE001
                claim_primary_error = AcceptanceError(
                    "ACCEPTANCE_SUCCESSOR_WRITE_FAILED",
                    "权威后继声明发生未预期失败",
                )
                claim_primary_error.__cause__ = exc
            finally:
                if claim_descriptor >= 0:
                    os.close(claim_descriptor)
                claim_cleanup_error = None
                if claim_linked and not successor_committed:
                    claim_cleanup_error = _cleanup_entry_error(
                        successors_descriptor,
                        predecessor_name,
                        sync_fd=successors_descriptor,
                        code="ACCEPTANCE_SUCCESSOR_CLEANUP_FAILED",
                        message="未提交后继声明无法安全清理",
                    )
                temp_cleanup_error = _cleanup_entry_error(
                    successors_descriptor,
                    claim_temp_name,
                    sync_fd=successors_descriptor,
                    code="ACCEPTANCE_SUCCESSOR_TEMP_CLEANUP_FAILED",
                    message="权威后继声明暂存文件无法安全清理",
                )
                _raise_after_cleanup(
                    claim_primary_error,
                    claim_cleanup_error or temp_cleanup_error,
                )
            _verify_publication_precommit(
                prepared,
                handle=handle,
                lock_descriptor=lock_descriptor,
                successors_descriptor=successors_descriptor,
            )
            os.rename(
                temp_name,
                latest_name,
                src_dir_fd=handle.fd,
                dst_dir_fd=handle.fd,
            )
            os.fsync(handle.fd)
            _verify_publication_precommit(
                prepared,
                handle=handle,
                lock_descriptor=lock_descriptor,
                successors_descriptor=successors_descriptor,
            )
        except AcceptanceError as exc:
            latest_primary_error = exc
        except (KeyboardInterrupt, SystemExit) as exc:
            latest_primary_error = exc
        except OSError as exc:
            latest_primary_error = AcceptanceError(
                "ACCEPTANCE_LATEST_UPDATE_FAILED",
                "不可变回执已生成，但latest原子更新失败",
            )
            latest_primary_error.__cause__ = exc
        except Exception as exc:  # noqa: BLE001
            latest_primary_error = AcceptanceError(
                "ACCEPTANCE_LATEST_UPDATE_FAILED",
                "latest更新发生未预期失败",
            )
            latest_primary_error.__cause__ = exc
        finally:
            if latest_descriptor >= 0:
                os.close(latest_descriptor)
            latest_cleanup_error = _cleanup_entry_error(
                handle.fd,
                temp_name,
                sync_fd=handle.fd,
                code="ACCEPTANCE_LATEST_TEMP_CLEANUP_FAILED",
                message="latest暂存文件无法安全清理",
            )
            _raise_after_cleanup(latest_primary_error, latest_cleanup_error)

        latest_result = _read_regular_snapshot_at(handle, latest_name)
        assert latest_result is not None
        latest, latest_info = latest_result
        if (
            latest.raw != payload
            or stat.S_IMODE(latest_info.st_mode) != 0o600
            or not validate_acceptance_receipt(_decode_json(latest)).get("ok")
        ):
            raise AcceptanceError(
                "ACCEPTANCE_LATEST_VERIFY_FAILED", "latest回执反读校验失败"
            )
        _verify_owned_child_directory(
            handle.fd,
            "successors",
            successors_descriptor,
        )
        _verify_publish_lock(handle, lock_descriptor)
        handle.verify_namespace()
        return {
            "written": True,
            "immutable_receipt": str(handle.output_path / final_name),
            "latest_receipt": str(handle.output_path / latest_name),
            "successor_claim": str(
                handle.output_path / "successors" / predecessor_name
            ),
            "file_sha256": immutable.sha256,
            "receipt_digest": receipt["receipt_digest"],
            "immutable_published": True,
        }
    except BaseException as exc:
        cleanup_error: BaseException | None = None
        if immutable_created and not successor_committed and handle is not None:
            try:
                _unlink_output_file_or_fail(
                    handle,
                    final_name,
                    code="ACCEPTANCE_IMMUTABLE_CLEANUP_FAILED",
                    message="未提交的不可变回执无法安全清理",
                )
            except BaseException as caught_cleanup_error:  # noqa: BLE001
                cleanup_error = caught_cleanup_error
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if cleanup_error is not None:
            raise cleanup_error
        if isinstance(exc, AcceptanceError):
            raise
        if isinstance(exc, OSError):
            raise AcceptanceError(
                "ACCEPTANCE_PUBLICATION_LOCK_FAILED", "回执发布锁不可用"
            ) from exc
        raise AcceptanceError(
            "ACCEPTANCE_PUBLICATION_FAILED",
            "验收回执发布发生未预期失败",
        ) from exc
    finally:
        if successors_descriptor >= 0:
            os.close(successors_descriptor)
        if lock_descriptor >= 0:
            try:
                fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
            finally:
                os.close(lock_descriptor)
        if handle is not None:
            handle.close()


def run_acceptance(
    *,
    project_id: str,
    data_root: str | Path,
    registry_path: str | Path,
    release_identity: Mapping[str, Any],
    release_witnesses: list[FileSnapshot | FileWitness],
    release_validator: Callable[[], Mapping[str, Any]],
    write: bool = False,
    output_root: str | Path | None = None,
    run_id: str | None = None,
    generated_at: str | None = None,
    source_job_id: str | None = None,
) -> dict[str, Any]:
    if write:
        raise AcceptanceError(
            "ACCEPTANCE_WRITE_REQUIRES_CURRENT_CLI",
            "正式写入只能由current密封发布的固定CLI入口执行",
        )
    started = time.monotonic()
    snapshot = collect_acceptance_snapshot(
        project_id=project_id,
        data_root=data_root,
        registry_path=registry_path,
        release_identity=release_identity,
        release_witnesses=release_witnesses,
        release_validator=release_validator,
        output_root=output_root,
        run_id=run_id,
        generated_at=generated_at,
        source_job_id=source_job_id,
    )
    verify_snapshot_stability(snapshot)
    receipt = snapshot.receipt
    result: dict[str, Any] = {
        "ok": True,
        "mode": "write" if write else "dry_run",
        "decision": receipt["decision"],
        "receipt": receipt,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "write_result": None,
    }
    return result
