from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import stat
import uuid
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_SCHEMA_VERSION = "project-fact-approval-event-v1"
LOCATOR_SCHEMA_VERSION = "project-fact-approval-event-locator-v1"
PROVENANCE_TRUST = "local_owner_controlled"
CRYPTOGRAPHIC_ATTESTATION = False
AUDIT_RELATIVE_PATH = "audit/project_fact_approvals.jsonl"
AUDIT_FILENAME = "project_fact_approvals.jsonl"

_MAX_AUDIT_BYTES = 64 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_ID_RE = re.compile(r"^[^\x00-\x1f/\\]{1,160}$")
_FIELD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,79}$")
_EVENT_ID_RE = re.compile(r"^pfa-[0-9a-f]{32}$")
_ACTOR_CHANNELS = frozenset({"actions_key", "authenticated_user"})
_RECEIPT_FIELDS = (
    "receipt_id",
    "status",
    "project_id",
    "field",
    "value_digest",
    "summary",
    "approved_by",
    "approved_at",
)
_SOURCE_FIELDS = frozenset(
    {
        "locator",
        "filename",
        "source_sha256",
        "extract_text_sha256",
        "ingest_audit_row_digest",
        "source_relative_path",
        "extract_relative_path",
        "enabled",
        "usable",
    }
)
_ACTOR_FIELDS = frozenset({"channel", "actor_id"})
_EVENT_CORE_FIELDS = frozenset(
    {
        "schema_version",
        "provenance_trust",
        "cryptographic_attestation",
        "event_type",
        "event_id",
        "recorded_at",
        "project_id",
        "field",
        "value_digest",
        "approval_receipt_digest",
        "resolution_digest",
        "receipt_id",
        "approved_by",
        "source_evidence",
        "actor",
        "idempotency_key",
    }
)
_EVENT_FIELDS = _EVENT_CORE_FIELDS | {"event_digest"}
_LOCATOR_FIELDS = frozenset(
    {
        "schema_version",
        "audit_path",
        "line",
        "byte_offset",
        "event_id",
        "event_digest",
    }
)


class ProjectFactApprovalAuditError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_NOT_STRICT_JSON",
            "审批审计数据不是有限、可规范化的JSON",
        ) from exc


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def project_fact_value_digest(*, field: str, value: Any, unit: Any = "") -> str:
    normalized_field = _field(field)
    normalized_unit = " ".join(str(unit or "").split()).strip()
    return canonical_digest(
        {
            "field": normalized_field,
            "value": value,
            "unit": normalized_unit,
        }
    )


def build_project_fact_approval_event(
    *,
    project_id: str,
    field: str,
    resolution: Mapping[str, Any],
    trusted_source: Mapping[str, Any],
    actor: Mapping[str, Any],
    recorded_at: str | None = None,
) -> dict[str, Any]:
    normalized_project_id = _project_id(project_id)
    normalized_field = _field(field)
    if not isinstance(resolution, Mapping) or "value" not in resolution:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_RESOLUTION_INVALID",
            "批准参数缺少结构化value",
        )
    resolution_core = dict(resolution)
    resolution_core.pop("approval_event", None)
    canonical_json_bytes(resolution_core)

    evidence = resolution_core.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "批准参数缺少来源证据",
        )
    source_evidence = _source_evidence(
        evidence=evidence,
        trusted_source=trusted_source,
        project_id=normalized_project_id,
    )
    receipt = resolution_core.get("approval_receipt")
    if not isinstance(receipt, Mapping):
        receipt = resolution_core.get("confirmation_receipt")
    if not isinstance(receipt, Mapping):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_RECEIPT_INVALID",
            "批准参数缺少确认回执",
        )
    value_digest = project_fact_value_digest(
        field=normalized_field,
        value=resolution_core.get("value"),
        unit=resolution_core.get("unit"),
    )
    normalized_receipt = _approval_receipt(
        receipt,
        project_id=normalized_project_id,
        field=normalized_field,
        value_digest=value_digest,
    )
    normalized_actor = _actor(actor)
    resolution_digest = canonical_digest(resolution_core)
    approval_receipt_digest = canonical_digest(normalized_receipt)
    idempotency_key = canonical_digest(
        {
            "project_id": normalized_project_id,
            "field": normalized_field,
            "resolution_digest": resolution_digest,
            "approval_receipt_digest": approval_receipt_digest,
            "source_evidence": source_evidence,
            "actor": normalized_actor,
        }
    )
    event_time = _timestamp(
        recorded_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    core: dict[str, Any] = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "provenance_trust": PROVENANCE_TRUST,
        "cryptographic_attestation": CRYPTOGRAPHIC_ATTESTATION,
        "event_type": "project_fact_approval_confirmed",
        "event_id": f"pfa-{uuid.uuid4().hex}",
        "recorded_at": event_time,
        "project_id": normalized_project_id,
        "field": normalized_field,
        "value_digest": value_digest,
        "approval_receipt_digest": approval_receipt_digest,
        "resolution_digest": resolution_digest,
        "receipt_id": normalized_receipt["receipt_id"],
        "approved_by": normalized_receipt["approved_by"],
        "source_evidence": source_evidence,
        "actor": normalized_actor,
        "idempotency_key": idempotency_key,
    }
    return {**core, "event_digest": canonical_digest(core)}


def append_project_fact_approval_event(
    audit_path: str | Path,
    event: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_event = _event(event)
    path = _audit_path(audit_path)
    parent_descriptor = _open_parent(path)
    descriptor = -1
    created = False
    try:
        descriptor, created = _open_audit_file(parent_descriptor, path.name)
        info = os.fstat(descriptor)
        _validate_open_audit_file(info, created=created)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        try:
            info = os.fstat(descriptor)
            if info.st_size > _MAX_AUDIT_BYTES:
                raise ProjectFactApprovalAuditError(
                    "PROJECT_FACT_APPROVAL_AUDIT_TOO_LARGE",
                    "审批审计文件超过安全读取上限",
                )
            existing_bytes = _pread_all(descriptor, info.st_size)
            entries = parse_project_fact_approval_audit(existing_bytes)
            matches = [
                entry
                for entry in entries
                if entry["event"]["idempotency_key"]
                == normalized_event["idempotency_key"]
            ]
            latest_for_field = next(
                (
                    entry
                    for entry in reversed(entries)
                    if entry["event"]["project_id"]
                    == normalized_event["project_id"]
                    and entry["event"]["field"] == normalized_event["field"]
                ),
                None,
            )
            if latest_for_field in matches:
                assert latest_for_field is not None
                return {
                    "event": latest_for_field["event"],
                    "locator": latest_for_field["locator"],
                    "reused": True,
                }

            line_bytes = canonical_json_bytes(normalized_event) + b"\n"
            byte_offset = info.st_size
            _write_all(descriptor, line_bytes)
            os.fsync(descriptor)
            after = os.fstat(descriptor)
            if after.st_size != byte_offset + len(line_bytes):
                raise ProjectFactApprovalAuditError(
                    "PROJECT_FACT_APPROVAL_APPEND_INCOMPLETE",
                    "审批审计追加后的长度不符合预期",
                )
            _verify_namespace(parent_descriptor, path.name, after)
            if created:
                os.fsync(parent_descriptor)
            locator = _locator(
                normalized_event,
                line=len(entries) + 1,
                byte_offset=byte_offset,
            )
            return {
                "event": normalized_event,
                "locator": locator,
                "reused": False,
            }
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def record_project_fact_approval(
    *,
    audit_path: str | Path,
    project_id: str,
    field: str,
    resolution: Mapping[str, Any],
    trusted_source: Mapping[str, Any],
    actor: Mapping[str, Any],
    recorded_at: str | None = None,
) -> dict[str, Any]:
    event = build_project_fact_approval_event(
        project_id=project_id,
        field=field,
        resolution=resolution,
        trusted_source=trusted_source,
        actor=actor,
        recorded_at=recorded_at,
    )
    return append_project_fact_approval_event(audit_path, event)


def parse_project_fact_approval_audit(
    audit_bytes: bytes,
) -> list[dict[str, Any]]:
    if not isinstance(audit_bytes, bytes):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_BYTES_INVALID",
            "审批审计快照必须是不可变bytes",
        )
    if len(audit_bytes) > _MAX_AUDIT_BYTES:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_TOO_LARGE",
            "审批审计快照超过安全读取上限",
        )
    if not audit_bytes:
        return []
    if not audit_bytes.endswith(b"\n"):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_TRUNCATED",
            "审批审计末行不完整",
        )
    entries: list[dict[str, Any]] = []
    byte_offset = 0
    seen_event_digests: set[str] = set()
    seen_event_ids: set[str] = set()
    for line_number, line_with_newline in enumerate(
        audit_bytes.splitlines(keepends=True),
        start=1,
    ):
        line = line_with_newline[:-1]
        if not line:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_AUDIT_LINE_INVALID",
                "审批审计包含空行",
            )
        value = _strict_json_object(line)
        event = _event(value)
        if canonical_json_bytes(event) != line:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_AUDIT_NOT_CANONICAL",
                "审批审计行不是规范JSON",
            )
        event_digest = event["event_digest"]
        if event_digest in seen_event_digests:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_AUDIT_DUPLICATE",
                "审批审计包含重复事件",
            )
        seen_event_digests.add(event_digest)
        event_id = event["event_id"]
        if event_id in seen_event_ids:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_AUDIT_DUPLICATE",
                "审批审计包含重复事件ID",
            )
        seen_event_ids.add(event_id)
        entries.append(
            {
                "event": event,
                "locator": _locator(
                    event,
                    line=line_number,
                    byte_offset=byte_offset,
                ),
            }
        )
        byte_offset += len(line_with_newline)
    return entries


def verify_project_fact_approval_event(
    audit_bytes: bytes,
    locator: Mapping[str, Any],
    *,
    expected_project_id: str,
    expected_field: str,
    expected_resolution_digest: str,
    expected_value_digest: str,
    expected_approval_receipt_digest: str,
    expected_source_evidence: Mapping[str, Any],
    current_source_allowlist: Iterable[Mapping[str, Any]] | Mapping[str, Any],
    expected_actor: Mapping[str, Any] | None = None,
    require_latest: bool = True,
) -> dict[str, Any]:
    try:
        normalized_locator = _validate_locator(locator)
        entries = parse_project_fact_approval_audit(audit_bytes)
        line = normalized_locator["line"]
        if line > len(entries):
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_EVENT_NOT_FOUND",
                "审批事件locator超出审计快照范围",
            )
        selected = entries[line - 1]
        if selected["locator"] != normalized_locator:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_LOCATOR_MISMATCH",
                "审批事件locator与审计快照不一致",
            )
        event = selected["event"]
        expected = {
            "project_id": _project_id(expected_project_id),
            "field": _field(expected_field),
            "resolution_digest": _sha256(
                expected_resolution_digest,
                code="PROJECT_FACT_APPROVAL_RESOLUTION_DIGEST_INVALID",
            ),
            "value_digest": _sha256(
                expected_value_digest,
                code="PROJECT_FACT_APPROVAL_VALUE_DIGEST_INVALID",
            ),
            "approval_receipt_digest": _sha256(
                expected_approval_receipt_digest,
                code="PROJECT_FACT_APPROVAL_RECEIPT_DIGEST_INVALID",
            ),
        }
        for key, expected_value in expected.items():
            if event.get(key) != expected_value:
                raise ProjectFactApprovalAuditError(
                    "PROJECT_FACT_APPROVAL_EVENT_BINDING_MISMATCH",
                    "审批事件与计划参数绑定不一致",
                )
        _expected_source_matches(event["source_evidence"], expected_source_evidence)
        if expected_actor is not None and event["actor"] != _actor(expected_actor):
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_ACTOR_MISMATCH",
                "审批事件与预期认证主体不一致",
            )
        if require_latest:
            later = [
                entry
                for entry in entries[line:]
                if entry["event"]["project_id"] == event["project_id"]
                and entry["event"]["field"] == event["field"]
            ]
            if later:
                raise ProjectFactApprovalAuditError(
                    "PROJECT_FACT_APPROVAL_EVENT_NOT_LATEST",
                    "审批事件不是该项目参数的最新确认",
                )
        source_projection = _current_source_projection(
            current_source_allowlist,
            project_id=event["project_id"],
            source_sha256=event["source_evidence"]["source_sha256"],
        )
        _current_source_matches(event["source_evidence"], source_projection)
        return {
            "ok": True,
            "machine_code": "PROJECT_FACT_APPROVAL_EVENT_VERIFIED",
            "event": event,
            "locator": normalized_locator,
            "source_projection": source_projection,
        }
    except ProjectFactApprovalAuditError as exc:
        return {
            "ok": False,
            "machine_code": exc.code,
            "errors": [exc.code],
        }


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_JSON_INVALID",
            "审批审计包含无效JSON",
        ) from exc
    if not isinstance(value, dict):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_JSON_INVALID",
            "审批审计行必须是JSON对象",
        )
    _assert_finite(value)
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _assert_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_NOT_STRICT_JSON",
            "审批审计包含非有限数",
        )
    if isinstance(value, Mapping):
        for child in value.values():
            _assert_finite(child)
    elif isinstance(value, list):
        for child in value:
            _assert_finite(child)


def _event(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _EVENT_FIELDS:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_EVENT_SCHEMA_INVALID",
            "审批事件字段不符合严格schema",
        )
    event = dict(value)
    if (
        event.get("schema_version") != EVENT_SCHEMA_VERSION
        or event.get("provenance_trust") != PROVENANCE_TRUST
        or event.get("cryptographic_attestation") is not False
        or event.get("event_type") != "project_fact_approval_confirmed"
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_EVENT_SCHEMA_INVALID",
            "审批事件信任边界或类型无效",
        )
    _project_id(event.get("project_id"))
    _field(event.get("field"))
    _timestamp(event.get("recorded_at"))
    if _EVENT_ID_RE.fullmatch(str(event.get("event_id") or "")) is None:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_EVENT_ID_INVALID",
            "审批事件ID无效",
        )
    for key in (
        "value_digest",
        "approval_receipt_digest",
        "resolution_digest",
        "idempotency_key",
        "event_digest",
    ):
        event[key] = _sha256(
            event.get(key),
            code="PROJECT_FACT_APPROVAL_EVENT_DIGEST_INVALID",
        )
    if not _text(event.get("receipt_id"), limit=160) or not _text(
        event.get("approved_by"), limit=240
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_EVENT_SCHEMA_INVALID",
            "审批事件缺少回执或批准主体",
        )
    event["source_evidence"] = _validated_event_source(
        event.get("source_evidence")
    )
    event["actor"] = _actor(event.get("actor"))
    core = {key: event[key] for key in _EVENT_CORE_FIELDS}
    if event["event_digest"] != canonical_digest(core):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_EVENT_DIGEST_INVALID",
            "审批事件摘要不匹配",
        )
    expected_idempotency = canonical_digest(
        {
            "project_id": event["project_id"],
            "field": event["field"],
            "resolution_digest": event["resolution_digest"],
            "approval_receipt_digest": event["approval_receipt_digest"],
            "source_evidence": event["source_evidence"],
            "actor": event["actor"],
        }
    )
    if event["idempotency_key"] != expected_idempotency:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_IDEMPOTENCY_INVALID",
            "审批事件幂等摘要不匹配",
        )
    return event


def _approval_receipt(
    receipt: Mapping[str, Any],
    *,
    project_id: str,
    field: str,
    value_digest: str,
) -> dict[str, str]:
    allowed = set(_RECEIPT_FIELDS) | {"receipt_digest"}
    if set(receipt) - allowed:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_RECEIPT_INVALID",
            "批准回执包含未定义字段",
        )
    normalized = {
        key: " ".join(str(receipt.get(key) or "").split()).strip()
        for key in _RECEIPT_FIELDS
    }
    normalized["status"] = normalized["status"].lower()
    normalized["value_digest"] = normalized["value_digest"].lower()
    if (
        any(not value for value in normalized.values())
        or normalized["status"] != "approved"
        or normalized["project_id"] != project_id
        or normalized["field"] != field
        or normalized["value_digest"] != value_digest
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_RECEIPT_INVALID",
            "批准回执未绑定项目、字段或参数值",
        )
    _timestamp(normalized["approved_at"])
    claimed = receipt.get("receipt_digest")
    if claimed is not None and str(claimed).strip().lower() != canonical_digest(
        normalized
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_RECEIPT_INVALID",
            "批准回执摘要不匹配",
        )
    return normalized


def _source_evidence(
    *,
    evidence: Mapping[str, Any],
    trusted_source: Mapping[str, Any],
    project_id: str,
) -> dict[str, Any]:
    source_project_id = _project_id(trusted_source.get("project_id"))
    if source_project_id != project_id:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "来源证据项目不匹配",
        )
    filename = _filename(
        trusted_source.get("filename") or trusted_source.get("file_name")
    )
    source_sha256 = _sha256(
        trusted_source.get("source_sha256") or trusted_source.get("sha256"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    extract_sha256 = _sha256(
        trusted_source.get("extract_text_sha256"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    audit_row_digest = _sha256(
        trusted_source.get("audit_row_digest")
        or trusted_source.get("ingest_audit_row_digest"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    if trusted_source.get("enabled") is not True or trusted_source.get(
        "usable"
    ) is not True:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
            "来源证据不是当前启用且可用记录",
        )
    locator = _text(evidence.get("locator"), limit=4096)
    evidence_filename = _filename(
        evidence.get("file_name") or evidence.get("filename")
    )
    evidence_sha256 = _sha256(
        evidence.get("document_sha256") or evidence.get("source_sha256"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    locator_file = locator.split("#", 1)[0].split("::", 1)[0]
    if (
        evidence_filename != filename
        or evidence_sha256 != source_sha256
        or locator_file != filename
        or locator == filename
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "参数来源locator、文件名或字节摘要不匹配",
        )
    return {
        "locator": locator,
        "filename": filename,
        "source_sha256": source_sha256,
        "extract_text_sha256": extract_sha256,
        "ingest_audit_row_digest": audit_row_digest,
        "source_relative_path": _relative_path(
            trusted_source.get("source_relative_path")
        ),
        "extract_relative_path": _relative_path(
            trusted_source.get("extract_relative_path")
        ),
        "enabled": True,
        "usable": True,
    }


def _validated_event_source(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _SOURCE_FIELDS:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "审批事件来源证据schema无效",
        )
    source = dict(value)
    source["filename"] = _filename(source.get("filename"))
    source["locator"] = _text(source.get("locator"), limit=4096)
    source["source_sha256"] = _sha256(
        source.get("source_sha256"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    source["extract_text_sha256"] = _sha256(
        source.get("extract_text_sha256"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    source["ingest_audit_row_digest"] = _sha256(
        source.get("ingest_audit_row_digest"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    source["source_relative_path"] = _relative_path(
        source.get("source_relative_path")
    )
    source["extract_relative_path"] = _relative_path(
        source.get("extract_relative_path")
    )
    if source.get("enabled") is not True or source.get("usable") is not True:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
            "审批事件来源未声明启用且可用",
        )
    locator_file = source["locator"].split("#", 1)[0].split("::", 1)[0]
    if not source["locator"] or locator_file != source["filename"]:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "审批事件来源locator无效",
        )
    return source


def _actor(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != _ACTOR_FIELDS:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_ACTOR_INVALID",
            "审批认证主体schema无效",
        )
    channel = _text(value.get("channel"), limit=80)
    actor_id = _text(value.get("actor_id"), limit=240)
    if channel not in _ACTOR_CHANNELS or not actor_id:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_ACTOR_INVALID",
            "审批认证主体缺失或通道无效",
        )
    return {"channel": channel, "actor_id": actor_id}


def _expected_source_matches(
    event_source: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> None:
    if not isinstance(expected, Mapping):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "缺少计划侧来源证据",
        )
    expected_filename = _filename(
        expected.get("filename") or expected.get("file_name")
    )
    expected_source_sha256 = _sha256(
        expected.get("source_sha256") or expected.get("document_sha256"),
        code="PROJECT_FACT_APPROVAL_SOURCE_INVALID",
    )
    if (
        expected_filename != event_source.get("filename")
        or _text(expected.get("locator"), limit=4096)
        != event_source.get("locator")
        or expected_source_sha256 != event_source.get("source_sha256")
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_BINDING_MISMATCH",
            "审批事件与计划来源证据不一致",
        )


def _current_source_projection(
    allowlist: Iterable[Mapping[str, Any]] | Mapping[str, Any],
    *,
    project_id: str,
    source_sha256: str,
) -> dict[str, Any]:
    if isinstance(allowlist, Mapping):
        if "source_sha256" in allowlist or "sha256" in allowlist:
            rows = [allowlist]
        else:
            rows = list(allowlist.values())
    elif isinstance(allowlist, Iterable) and not isinstance(
        allowlist, (str, bytes)
    ):
        rows = list(allowlist)
    else:
        rows = []
    matches = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        row_sha256 = str(
            raw.get("source_sha256") or raw.get("sha256") or ""
        ).strip().lower()
        if (
            str(raw.get("project_id") or "").strip() == project_id
            and row_sha256 == source_sha256
        ):
            matches.append(raw)
    if len(matches) != 1:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
            "当前来源allowlist缺失或不唯一",
        )
    raw = matches[0]
    if raw.get("enabled") is not True or raw.get("usable") is not True:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
            "当前来源已禁用或不可用",
        )
    return {
        "project_id": project_id,
        "filename": _filename(raw.get("filename") or raw.get("file_name")),
        "source_sha256": _sha256(
            raw.get("source_sha256") or raw.get("sha256"),
            code="PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
        ),
        "extract_text_sha256": _sha256(
            raw.get("extract_text_sha256"),
            code="PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
        ),
        "ingest_audit_row_digest": _sha256(
            raw.get("ingest_audit_row_digest") or raw.get("audit_row_digest"),
            code="PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
        ),
        "source_relative_path": _relative_path(raw.get("source_relative_path")),
        "extract_relative_path": _relative_path(raw.get("extract_relative_path")),
        "enabled": True,
        "usable": True,
    }


def _current_source_matches(
    event_source: Mapping[str, Any],
    current: Mapping[str, Any],
) -> None:
    for key in (
        "filename",
        "source_sha256",
        "extract_text_sha256",
        "ingest_audit_row_digest",
        "source_relative_path",
        "extract_relative_path",
        "enabled",
        "usable",
    ):
        if event_source.get(key) != current.get(key):
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT",
                "审批事件来源不再匹配当前可信入库记录",
            )


def _locator(event: Mapping[str, Any], *, line: int, byte_offset: int) -> dict[str, Any]:
    return {
        "schema_version": LOCATOR_SCHEMA_VERSION,
        "audit_path": AUDIT_RELATIVE_PATH,
        "line": line,
        "byte_offset": byte_offset,
        "event_id": event["event_id"],
        "event_digest": event["event_digest"],
    }


def _validate_locator(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _LOCATOR_FIELDS:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_LOCATOR_INVALID",
            "审批事件locator schema无效",
        )
    locator = dict(value)
    if (
        locator.get("schema_version") != LOCATOR_SCHEMA_VERSION
        or locator.get("audit_path") != AUDIT_RELATIVE_PATH
        or _EVENT_ID_RE.fullmatch(str(locator.get("event_id") or "")) is None
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_LOCATOR_INVALID",
            "审批事件locator身份无效",
        )
    for key, minimum in (("line", 1), ("byte_offset", 0)):
        item = locator.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or item < minimum:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_LOCATOR_INVALID",
                "审批事件locator位置无效",
            )
    locator["event_digest"] = _sha256(
        locator.get("event_digest"),
        code="PROJECT_FACT_APPROVAL_LOCATOR_INVALID",
    )
    return locator


def _audit_path(value: str | Path) -> Path:
    try:
        path = Path(os.path.abspath(os.fspath(value)))
    except (TypeError, ValueError, OSError) as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_PATH_INVALID",
            "审批审计路径无效",
        ) from exc
    if path.name != AUDIT_FILENAME or path.parent == path:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_PATH_INVALID",
            "审批审计文件名或父目录无效",
        )
    return path


def _open_parent(path: Path) -> int:
    flags = (
        os.O_RDONLY
        | _required_os_flag("O_DIRECTORY")
        | _required_os_flag("O_NOFOLLOW")
        | _required_os_flag("O_CLOEXEC")
    )
    try:
        descriptor = os.open(path.parent, flags)
    except OSError as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_DIRECTORY_UNTRUSTED",
            "审批审计父目录不存在、是symlink或不可打开",
        ) from exc
    info = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) & 0o022
    ):
        os.close(descriptor)
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_DIRECTORY_UNTRUSTED",
            "审批审计父目录所有者或权限不可信",
        )
    return descriptor


def _open_audit_file(parent_descriptor: int, name: str) -> tuple[int, bool]:
    base_flags = (
        os.O_RDWR
        | os.O_APPEND
        | _required_os_flag("O_NOFOLLOW")
        | _required_os_flag("O_CLOEXEC")
    )
    try:
        descriptor = os.open(
            name,
            base_flags | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=parent_descriptor,
        )
        return descriptor, True
    except FileExistsError:
        try:
            descriptor = os.open(name, base_flags, dir_fd=parent_descriptor)
        except OSError as exc:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_AUDIT_FILE_UNTRUSTED",
                "审批审计文件是symlink或不可打开",
            ) from exc
        return descriptor, False
    except OSError as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_FILE_UNTRUSTED",
            "审批审计文件无法安全创建",
        ) from exc


def _validate_open_audit_file(info: os.stat_result, *, created: bool) -> None:
    del created
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_FILE_UNTRUSTED",
            "审批审计文件所有者、类型或权限不可信",
        )


def _verify_namespace(parent_descriptor: int, name: str, expected: os.stat_result) -> None:
    try:
        current = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except OSError as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_NAMESPACE_CHANGED",
            "审批审计文件命名空间在写入期间发生变化",
        ) from exc
    if (
        current.st_dev,
        current.st_ino,
        stat.S_IFMT(current.st_mode),
    ) != (
        expected.st_dev,
        expected.st_ino,
        stat.S_IFMT(expected.st_mode),
    ):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_AUDIT_NAMESPACE_CHANGED",
            "审批审计文件命名空间在写入期间发生变化",
        )


def _pread_all(descriptor: int, size: int) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < size:
        chunk = os.pread(descriptor, min(1024 * 1024, size - offset), offset)
        if not chunk:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_AUDIT_READ_INCOMPLETE",
                "审批审计文件读取不完整",
            )
        chunks.append(chunk)
        offset += len(chunk)
    return b"".join(chunks)


def _write_all(descriptor: int, value: bytes) -> None:
    view = memoryview(value)
    written = 0
    while written < len(value):
        count = os.write(descriptor, view[written:])
        if count <= 0:
            raise ProjectFactApprovalAuditError(
                "PROJECT_FACT_APPROVAL_APPEND_INCOMPLETE",
                "审批审计追加写入不完整",
            )
        written += count


def _required_os_flag(name: str) -> int:
    value = getattr(os, name, None)
    if not isinstance(value, int):
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_PLATFORM_UNSUPPORTED",
            f"当前平台缺少安全文件标志{name}",
        )
    return value


def _timestamp(value: Any) -> str:
    text = _text(value, limit=80)
    if not text:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_TIMESTAMP_INVALID",
            "审批时间缺失",
        )
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_TIMESTAMP_INVALID",
            "审批时间格式无效",
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_TIMESTAMP_INVALID",
            "审批时间必须包含时区",
        )
    return text


def _project_id(value: Any) -> str:
    text = _text(value, limit=160)
    if _PROJECT_ID_RE.fullmatch(text) is None:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_PROJECT_INVALID",
            "审批事件项目ID无效",
        )
    return text


def _field(value: Any) -> str:
    text = _text(value, limit=80)
    if _FIELD_RE.fullmatch(text) is None:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_FIELD_INVALID",
            "审批事件字段名无效",
        )
    return text


def _filename(value: Any) -> str:
    text = _text(value, limit=255)
    if not text or Path(text).name != text or "/" in text or "\\" in text:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "来源证据文件名无效",
        )
    return text


def _relative_path(value: Any) -> str:
    text = _text(value, limit=2048)
    try:
        path = Path(text)
    except (TypeError, ValueError, OSError) as exc:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "来源证据相对路径无效",
        ) from exc
    if not text or path.is_absolute() or ".." in path.parts:
        raise ProjectFactApprovalAuditError(
            "PROJECT_FACT_APPROVAL_SOURCE_INVALID",
            "来源证据相对路径无效",
        )
    return text


def _sha256(value: Any, *, code: str) -> str:
    text = str(value or "").strip().lower()
    if _SHA256_RE.fullmatch(text) is None:
        raise ProjectFactApprovalAuditError(code, "SHA-256摘要无效")
    return text


def _text(value: Any, *, limit: int) -> str:
    text = str(value or "").strip()
    if not text or len(text) > limit or any(ord(char) < 32 for char in text):
        return ""
    return text
