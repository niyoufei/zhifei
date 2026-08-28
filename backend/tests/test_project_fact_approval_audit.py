from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from backend.zhifei_autoplan.project_fact_approval_audit import (
    CRYPTOGRAPHIC_ATTESTATION,
    PROVENANCE_TRUST,
    ProjectFactApprovalAuditError,
    append_project_fact_approval_event,
    build_project_fact_approval_event,
    canonical_digest,
    canonical_json_bytes,
    parse_project_fact_approval_audit,
    project_fact_value_digest,
    record_project_fact_approval,
    verify_project_fact_approval_event,
)

_PROJECT_ID = "P-APPROVAL-1"
_FIELD = "resource_peak"
_SOURCE_SHA256 = "a" * 64
_EXTRACT_SHA256 = "b" * 64
_AUDIT_ROW_DIGEST = "c" * 64
_FILENAME = "批准资源计划.xlsx"


def _audit_path(tmp_path: Path) -> Path:
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(mode=0o700)
    return audit_dir / "project_fact_approvals.jsonl"


def _resolution(value: int = 80) -> dict:
    value_digest = project_fact_value_digest(
        field=_FIELD,
        value=value,
        unit="人",
    )
    return {
        "value": value,
        "unit": "人",
        "evidence": {
            "file_name": _FILENAME,
            "document_sha256": _SOURCE_SHA256,
            "locator": f"{_FILENAME}#sheet=资源计划&cell=B12",
        },
        "approval_receipt": {
            "receipt_id": f"APR-{value}",
            "status": "approved",
            "project_id": _PROJECT_ID,
            "field": _FIELD,
            "value_digest": value_digest,
            "summary": "批准资源峰值作为本项目正式参数",
            "approved_by": "项目负责人",
            "approved_at": "2026-08-28T08:00:00Z",
        },
    }


def _trusted_source() -> dict:
    return {
        "project_id": _PROJECT_ID,
        "filename": _FILENAME,
        "source_sha256": _SOURCE_SHA256,
        "extract_text_sha256": _EXTRACT_SHA256,
        "audit_row_digest": _AUDIT_ROW_DIGEST,
        "source_relative_path": f"uploads/{_SOURCE_SHA256}_{_FILENAME}",
        "extract_relative_path": (
            f"extracts/{_SOURCE_SHA256}_{_EXTRACT_SHA256}.txt"
        ),
        "enabled": True,
        "usable": True,
    }


def _actor() -> dict:
    return {"channel": "authenticated_user", "actor_id": "user:42"}


def _verify(
    raw: bytes,
    locator: dict,
    resolution: dict,
    *,
    allowlist: list[dict] | None = None,
) -> dict:
    receipt = resolution["approval_receipt"]
    resolution_core = dict(resolution)
    resolution_core.pop("approval_event", None)
    return verify_project_fact_approval_event(
        raw,
        locator,
        expected_project_id=_PROJECT_ID,
        expected_field=_FIELD,
        expected_resolution_digest=canonical_digest(resolution_core),
        expected_value_digest=project_fact_value_digest(
            field=_FIELD,
            value=resolution["value"],
            unit=resolution["unit"],
        ),
        expected_approval_receipt_digest=canonical_digest(receipt),
        expected_source_evidence=resolution["evidence"],
        expected_actor=_actor(),
        current_source_allowlist=allowlist or [_trusted_source()],
    )


def _record(
    path: Path,
    resolution: dict | None = None,
    *,
    recorded_at: str = "2026-08-28T08:01:00Z",
) -> dict:
    return record_project_fact_approval(
        audit_path=path,
        project_id=_PROJECT_ID,
        field=_FIELD,
        resolution=resolution or _resolution(),
        trusted_source=_trusted_source(),
        actor=_actor(),
        recorded_at=recorded_at,
    )


def test_append_records_private_canonical_event_and_exact_locator(
    tmp_path: Path,
) -> None:
    path = _audit_path(tmp_path)
    resolution = _resolution()

    recorded = _record(path, resolution)
    raw = path.read_bytes()

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert recorded["reused"] is False
    assert recorded["locator"]["line"] == 1
    assert recorded["locator"]["byte_offset"] == 0
    assert recorded["event"]["provenance_trust"] == PROVENANCE_TRUST
    assert (
        recorded["event"]["cryptographic_attestation"]
        is CRYPTOGRAPHIC_ATTESTATION
        is False
    )
    assert raw == canonical_json_bytes(recorded["event"]) + b"\n"
    assert _verify(raw, recorded["locator"], resolution)["ok"] is True
    direct_allowlist = verify_project_fact_approval_event(
        raw,
        recorded["locator"],
        expected_project_id=_PROJECT_ID,
        expected_field=_FIELD,
        expected_resolution_digest=canonical_digest(resolution),
        expected_value_digest=project_fact_value_digest(
            field=_FIELD,
            value=resolution["value"],
            unit=resolution["unit"],
        ),
        expected_approval_receipt_digest=canonical_digest(
            resolution["approval_receipt"]
        ),
        expected_source_evidence=resolution["evidence"],
        expected_actor=_actor(),
        current_source_allowlist=_trusted_source(),
    )
    assert direct_allowlist["ok"] is True

    path.write_bytes(b"not the captured audit bytes")
    assert _verify(raw, recorded["locator"], resolution)["ok"] is True


def test_repeated_identical_binding_reuses_original_event(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    resolution = _resolution()
    first = _record(path, resolution, recorded_at="2026-08-28T08:01:00Z")
    second = _record(path, resolution, recorded_at="2026-08-28T09:01:00Z")

    assert second["reused"] is True
    assert second["event"] == first["event"]
    assert second["locator"] == first["locator"]
    assert len(parse_project_fact_approval_audit(path.read_bytes())) == 1


def test_later_value_binding_makes_old_event_stale(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    old_resolution = _resolution(80)
    new_resolution = _resolution(81)
    old = _record(path, old_resolution, recorded_at="2026-08-28T08:01:00Z")
    new = _record(path, new_resolution, recorded_at="2026-08-28T08:02:00Z")
    raw = path.read_bytes()

    old_result = _verify(raw, old["locator"], old_resolution)
    new_result = _verify(raw, new["locator"], new_resolution)

    assert old_result["ok"] is False
    assert old_result["machine_code"] == "PROJECT_FACT_APPROVAL_EVENT_NOT_LATEST"
    assert new_result["ok"] is True
    assert new["locator"]["line"] == 2
    assert new["locator"]["byte_offset"] > 0


def test_reapproving_original_value_after_change_appends_fresh_latest_event(
    tmp_path: Path,
) -> None:
    path = _audit_path(tmp_path)
    resolution_a = _resolution(80)
    resolution_b = _resolution(81)
    first_a = _record(path, resolution_a, recorded_at="2026-08-28T08:01:00Z")
    middle_b = _record(path, resolution_b, recorded_at="2026-08-28T08:02:00Z")
    latest_a = _record(path, resolution_a, recorded_at="2026-08-28T08:03:00Z")
    raw = path.read_bytes()

    assert latest_a["reused"] is False
    assert latest_a["locator"]["line"] == 3
    assert latest_a["event"]["event_id"] != first_a["event"]["event_id"]
    assert latest_a["event"]["event_digest"] != first_a["event"]["event_digest"]
    assert latest_a["event"]["idempotency_key"] == first_a["event"][
        "idempotency_key"
    ]
    assert _verify(raw, first_a["locator"], resolution_a)["machine_code"] == (
        "PROJECT_FACT_APPROVAL_EVENT_NOT_LATEST"
    )
    assert _verify(raw, middle_b["locator"], resolution_b)["machine_code"] == (
        "PROJECT_FACT_APPROVAL_EVENT_NOT_LATEST"
    )
    assert _verify(raw, latest_a["locator"], resolution_a)["ok"] is True


def test_event_content_tampering_fails_digest_validation(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    resolution = _resolution()
    recorded = _record(path, resolution)
    event = json.loads(path.read_text(encoding="utf-8"))
    event["approved_by"] = "篡改者"
    tampered = canonical_json_bytes(event) + b"\n"

    result = _verify(tampered, recorded["locator"], resolution)

    assert result["ok"] is False
    assert result["machine_code"] == "PROJECT_FACT_APPROVAL_EVENT_DIGEST_INVALID"


@pytest.mark.parametrize("field", ("byte_offset", "event_digest"))
def test_locator_offset_or_digest_mismatch_is_rejected(
    tmp_path: Path,
    field: str,
) -> None:
    path = _audit_path(tmp_path)
    resolution = _resolution()
    recorded = _record(path, resolution)
    locator = dict(recorded["locator"])
    locator[field] = 1 if field == "byte_offset" else "f" * 64

    result = _verify(path.read_bytes(), locator, resolution)

    assert result["ok"] is False
    assert result["machine_code"] == "PROJECT_FACT_APPROVAL_LOCATOR_MISMATCH"


def test_disabled_current_source_allowlist_is_rejected(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    resolution = _resolution()
    recorded = _record(path, resolution)
    disabled = _trusted_source()
    disabled["usable"] = False

    result = _verify(
        path.read_bytes(),
        recorded["locator"],
        resolution,
        allowlist=[disabled],
    )

    assert result["ok"] is False
    assert result["machine_code"] == "PROJECT_FACT_APPROVAL_SOURCE_NOT_CURRENT"


def test_non_finite_resolution_and_audit_json_fail_closed(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    invalid_resolution = _resolution()
    invalid_resolution["value"] = float("inf")

    with pytest.raises(ProjectFactApprovalAuditError) as exc_info:
        build_project_fact_approval_event(
            project_id=_PROJECT_ID,
            field=_FIELD,
            resolution=invalid_resolution,
            trusted_source=_trusted_source(),
            actor=_actor(),
            recorded_at="2026-08-28T08:01:00Z",
        )
    assert exc_info.value.code == "PROJECT_FACT_APPROVAL_NOT_STRICT_JSON"

    resolution = _resolution()
    recorded = _record(path, resolution)
    bad_json_result = _verify(b'{"value":NaN}\n', recorded["locator"], resolution)
    assert bad_json_result["ok"] is False
    assert (
        bad_json_result["machine_code"]
        == "PROJECT_FACT_APPROVAL_AUDIT_JSON_INVALID"
    )


def test_existing_non_private_audit_file_is_rejected(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    path.write_bytes(b"")
    path.chmod(0o644)
    event = build_project_fact_approval_event(
        project_id=_PROJECT_ID,
        field=_FIELD,
        resolution=_resolution(),
        trusted_source=_trusted_source(),
        actor=_actor(),
        recorded_at="2026-08-28T08:01:00Z",
    )

    with pytest.raises(ProjectFactApprovalAuditError) as exc_info:
        append_project_fact_approval_event(path, event)

    assert exc_info.value.code == "PROJECT_FACT_APPROVAL_AUDIT_FILE_UNTRUSTED"
    assert path.read_bytes() == b""
    assert stat.S_IMODE(path.stat().st_mode) == 0o644


def test_audit_symlink_is_rejected_without_touching_target(tmp_path: Path) -> None:
    path = _audit_path(tmp_path)
    target = tmp_path / "target.jsonl"
    target.write_bytes(b"preserve-me")
    path.symlink_to(target)
    event = build_project_fact_approval_event(
        project_id=_PROJECT_ID,
        field=_FIELD,
        resolution=_resolution(),
        trusted_source=_trusted_source(),
        actor=_actor(),
        recorded_at="2026-08-28T08:01:00Z",
    )

    with pytest.raises(ProjectFactApprovalAuditError) as exc_info:
        append_project_fact_approval_event(path, event)

    assert exc_info.value.code == "PROJECT_FACT_APPROVAL_AUDIT_FILE_UNTRUSTED"
    assert target.read_bytes() == b"preserve-me"
