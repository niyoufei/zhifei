from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from backend.zhifei_autoplan.evidence import (
    build_ingest_evidence_set_receipt,
    resolve_trusted_ingest_record,
    validate_ingest_evidence_set_receipt,
)
from backend.zhifei_autoplan.ingest_tags import effective_record_tags

SCHEMA_VERSION = "project-parameter-evidence-v1"

_FULL_SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)

_WALL_REQUIRED_IDS = frozenset({"wall-foundation-compaction"})
_VEHICLE_REQUIRED_IDS = frozenset(
    {
        "vehicle-pool-concrete-grade",
        "vehicle-pool-impermeability-trial",
    }
)
_CLARIFICATION_REQUIRED_IDS = frozenset(
    {
        "foundation-concrete-grade",
        "blinding-concrete-grade",
        "floor-coating-waterproof-thickness",
    }
)

_WALL_COMPACTION_RE = re.compile(
    r"压实系数.{0,24}?(?:不小于|不得小于|≥|>=)\s*"
    r"(?P<value>0\s*\.\s*\d+)",
    re.DOTALL,
)
_VEHICLE_POOL_GRADE_RE = re.compile(
    r"防水混凝土.{0,260}?强度等级.{0,48}?"
    r"(?:不应低于|不得低于|不低于|≥|>=)?\s*C\s*(?P<value>\d{2})",
    re.DOTALL,
)
_VEHICLE_POOL_IMPERMEABILITY_RE = re.compile(
    r"抗渗等级.{0,96}?(?:提高|高于|高出).{0,24}?"
    r"(?P<value>\d+\s*\.\s*\d+)\s*(?:MPa|Mpa|兆帕)",
    re.DOTALL,
)
_FOUNDATION_GRADES_RE = re.compile(
    r"回复\s*[：:]\s*基础\s*C\s*(?P<foundation>\d{2})"
    r".{0,48}?垫层\s*C\s*(?P<blinding>\d{2})",
    re.DOTALL,
)
_FLOOR_WATERPROOF_RE = re.compile(
    r"地面涂膜防水厚度.{0,120}?回复\s*[：:]\s*"
    r"(?P<value>\d+(?:\s*\.\s*\d+)?)\s*(?:mm|毫米)",
    re.IGNORECASE | re.DOTALL,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _audit_path(value: str | Path | None) -> Path:
    return (
        Path(value)
        if value is not None
        else Path("backend/data/audit/ingest.jsonl")
    )


def _tender_source_sha256s(tender: Mapping[str, Any] | None) -> set[str]:
    root = tender if isinstance(tender, Mapping) else {}
    document_sha256s: set[str] = set()

    def _remember(value: Any) -> None:
        digest = str(value or "").strip().lower()
        if _FULL_SHA256_RE.fullmatch(digest):
            document_sha256s.add(digest)

    for item in root.get("items") if isinstance(root.get("items"), list) else []:
        if not isinstance(item, Mapping):
            continue
        spans = item.get("source_spans") if isinstance(item.get("source_spans"), list) else []
        for span in spans:
            if isinstance(span, Mapping):
                _remember(
                    span.get("document_sha256") or span.get("source_sha256")
                )

    extraction_meta = (
        root.get("extraction_meta")
        if isinstance(root.get("extraction_meta"), Mapping)
        else {}
    )
    project_facts = (
        extraction_meta.get("project_facts")
        if isinstance(extraction_meta.get("project_facts"), Mapping)
        else {}
    )
    for fact in project_facts.values():
        if not isinstance(fact, Mapping):
            continue
        evidence = fact.get("evidence") if isinstance(fact.get("evidence"), Mapping) else {}
        _remember(
            evidence.get("document_sha256") or evidence.get("source_sha256")
        )
    return document_sha256s


def _source_is_in_scope(
    record: Mapping[str, Any],
    *,
    project_id: str,
    tender_document_sha256s: set[str],
) -> bool:
    if str(record.get("project_id") or "").strip() == project_id:
        return True
    sha256 = str(record.get("sha256") or record.get("file_id") or "").strip().lower()
    return sha256 in tender_document_sha256s


def _source_records(
    *,
    project_id: str,
    tender: Mapping[str, Any] | None,
    audit_path: Path,
) -> list[dict[str, Any]]:
    if not project_id or not audit_path.is_file():
        return []
    tender_document_sha256s = _tender_source_sha256s(tender)
    workspace_root = audit_path.parent.parent.resolve(strict=False)
    try:
        lines = audit_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        sha256 = str(record.get("sha256") or "").strip().lower()
        file_id = str(record.get("file_id") or "").strip().lower()
        if (
            _FULL_SHA256_RE.fullmatch(sha256) is None
            or _FULL_SHA256_RE.fullmatch(file_id) is None
            or sha256 != file_id
            or sha256 in seen
        ):
            continue
        seen.add(sha256)
        if record.get("enabled") is False or record.get("usable") is False:
            continue
        if not _source_is_in_scope(
            record,
            project_id=project_id,
            tender_document_sha256s=tender_document_sha256s,
        ):
            continue
        tags = set(effective_record_tags(record))
        if not tags.intersection({"drawing", "tender", "qa"}) or "logo" in tags:
            continue
        trusted = resolve_trusted_ingest_record(
            record,
            workspace_root=workspace_root,
            read_text=True,
        )
        if trusted.get("ok") is not True:
            continue
        extract_text = str(trusted.get("extract_text") or "")
        declared_pages = record.get("pages")
        try:
            page_count = int(declared_pages)
        except (TypeError, ValueError):
            page_count = None
        if "\f" in extract_text:
            pages = extract_text.split("\f")
            if page_count is not None and page_count > 0 and len(pages) != page_count:
                continue
        elif page_count == 1:
            pages = [extract_text]
        else:
            continue
        rows.append(
            {
                **record,
                "sha256": sha256,
                "file_id": file_id,
                "tags": sorted(tags),
                "saved_as": str(trusted["source_path"]),
                "extract_saved_as": str(trusted["extract_path"]),
                "extract_text_sha256": trusted["extract_text_sha256"],
                "_pages": pages,
                "_trusted_record": trusted,
            }
        )
    return rows


def _clean_decimal(value: Any) -> float:
    return float(re.sub(r"\s+", "", str(value or "")))


def _locator_item(
    *,
    record: Mapping[str, Any],
    page: int,
    page_text: str,
    page_offset: int,
    match: re.Match[str],
    item_id: str,
    process: str,
    metric: str,
    operator: str,
    value: Any,
    unit: str,
    source: str,
) -> dict[str, Any]:
    filename = str(record.get("filename") or "").strip()
    document_sha256 = str(record.get("sha256") or "").strip().lower()
    offset = page_offset + match.start()
    end = page_offset + match.end()
    locator = f"{filename}#p{page}_{document_sha256}@{offset}"
    return {
        "id": item_id,
        "process": process,
        "metric": metric,
        "operator": operator,
        "value": value,
        "unit": unit,
        "status": "verified",
        "source": source,
        "locator": locator,
        "document_sha256": document_sha256,
        "page": page,
        "page_text_sha256": hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
        "extract_text_sha256": str(
            record.get("extract_text_sha256") or ""
        ).strip().lower(),
        "offset": offset,
        "end": end,
        "page_start_offset": page_offset,
        "page_end_offset": page_offset + len(page_text),
        "page_match_start": match.start(),
        "page_match_end": match.end(),
        "match_text_sha256": hashlib.sha256(
            match.group(0).encode("utf-8")
        ).hexdigest(),
    }


def _record_source(record: Mapping[str, Any]) -> str:
    filename = str(record.get("filename") or "")
    tags = set(record.get("tags") or [])
    if "qa" in tags or any(marker in filename for marker in ("答疑", "澄清", "补疑")):
        return "clarification"
    return "reviewed_design" if "drawing" in tags else "tender"


def _required_item_ids_for_record(record: Mapping[str, Any]) -> set[str]:
    filename = str(record.get("filename") or "")
    required: set[str] = set()
    if "围墙" in filename:
        required.update(_WALL_REQUIRED_IDS)
    if "车辆消毒池" in filename:
        required.update(_VEHICLE_REQUIRED_IDS)
    if _record_source(record) == "clarification":
        page_text = "\f".join(
            str(page or "")
            for page in (
                record.get("_pages")
                if isinstance(record.get("_pages"), list)
                else []
            )
        )
        if any(
            marker in page_text
            for marker in ("基础", "垫层", "地面涂膜防水")
        ):
            required.update(_CLARIFICATION_REQUIRED_IDS)
    return required


def _scan_page(
    *,
    record: Mapping[str, Any],
    page: int,
    page_text: str,
    page_offset: int,
) -> list[dict[str, Any]]:
    filename = str(record.get("filename") or "")
    source = _record_source(record)
    out: list[dict[str, Any]] = []

    def _append(
        regex: re.Pattern[str],
        builder: Callable[[re.Match[str]], list[dict[str, Any]]],
    ) -> None:
        for match in regex.finditer(page_text):
            out.extend(builder(match))

    if "围墙" in filename:
        _append(
            _WALL_COMPACTION_RE,
            lambda match: [
                _locator_item(
                    record=record,
                    page=page,
                    page_text=page_text,
                    page_offset=page_offset,
                    match=match,
                    item_id="wall-foundation-compaction",
                    process="围墙基础持力层压实",
                    metric="压实系数",
                    operator="≥",
                    value=_clean_decimal(match.group("value")),
                    unit="",
                    source=source,
                )
            ],
        )

    if "车辆消毒池" in filename:
        _append(
            _VEHICLE_POOL_GRADE_RE,
            lambda match: [
                _locator_item(
                    record=record,
                    page=page,
                    page_text=page_text,
                    page_offset=page_offset,
                    match=match,
                    item_id="vehicle-pool-concrete-grade",
                    process="车辆消毒池防水混凝土",
                    metric="强度等级",
                    operator="≥",
                    value=f"C{match.group('value')}",
                    unit="",
                    source=source,
                )
            ],
        )
        _append(
            _VEHICLE_POOL_IMPERMEABILITY_RE,
            lambda match: [
                _locator_item(
                    record=record,
                    page=page,
                    page_text=page_text,
                    page_offset=page_offset,
                    match=match,
                    item_id="vehicle-pool-impermeability-trial",
                    process="车辆消毒池试配混凝土",
                    metric="抗渗等级相对设计要求提高值",
                    operator="≥",
                    value=_clean_decimal(match.group("value")),
                    unit="MPa",
                    source=source,
                )
            ],
        )

    if source == "clarification":
        _append(
            _FOUNDATION_GRADES_RE,
            lambda match: [
                _locator_item(
                    record=record,
                    page=page,
                    page_text=page_text,
                    page_offset=page_offset,
                    match=match,
                    item_id="foundation-concrete-grade",
                    process="基础混凝土",
                    metric="强度等级",
                    operator="=",
                    value=f"C{match.group('foundation')}",
                    unit="",
                    source=source,
                ),
                _locator_item(
                    record=record,
                    page=page,
                    page_text=page_text,
                    page_offset=page_offset,
                    match=match,
                    item_id="blinding-concrete-grade",
                    process="垫层混凝土",
                    metric="强度等级",
                    operator="=",
                    value=f"C{match.group('blinding')}",
                    unit="",
                    source=source,
                ),
            ],
        )
        _append(
            _FLOOR_WATERPROOF_RE,
            lambda match: [
                _locator_item(
                    record=record,
                    page=page,
                    page_text=page_text,
                    page_offset=page_offset,
                    match=match,
                    item_id="floor-coating-waterproof-thickness",
                    process="地面涂膜防水",
                    metric="厚度",
                    operator="=",
                    value=_clean_decimal(match.group("value")),
                    unit="mm",
                    source=source,
                )
            ],
        )
    return out


def build_project_parameter_evidence(
    *,
    project_id: str,
    tender: Mapping[str, Any] | None,
    audit_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build deterministic, process-bound project parameter evidence.

    The function reads only current ingested extracts.  It never creates a
    global tolerance and never invents a value when a rule is absent or
    contradictory.
    """

    pid = str(project_id or "").strip()
    path = _audit_path(audit_path)
    records = _source_records(
        project_id=pid,
        tender=tender,
        audit_path=path,
    )
    required_item_ids: set[str] = set()
    found: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        required_item_ids.update(_required_item_ids_for_record(record))
        page_offset = 0
        pages = record.get("_pages") if isinstance(record.get("_pages"), list) else []
        for page, page_text_raw in enumerate(pages, start=1):
            page_text = str(page_text_raw or "")
            for item in _scan_page(
                record=record,
                page=page,
                page_text=page_text,
                page_offset=page_offset,
            ):
                found.setdefault(str(item["id"]), []).append(item)
            page_offset += len(page_text)
            if page < len(pages):
                page_offset += 1

    selected: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for item_id in sorted(found):
        rows = found[item_id]
        value_groups: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            identity = _canonical_json(
                {
                    "value": row.get("value"),
                    "unit": row.get("unit"),
                    "operator": row.get("operator"),
                }
            )
            value_groups.setdefault(identity, []).append(row)
        if len(value_groups) != 1:
            conflicts.append(
                {
                    "id": item_id,
                    "candidate_count": len(rows),
                    "values": [
                        {
                            "value": group[0].get("value"),
                            "unit": group[0].get("unit"),
                            "operator": group[0].get("operator"),
                            "locators": sorted(
                                str(row.get("locator") or "") for row in group
                            ),
                        }
                        for group in value_groups.values()
                    ],
                }
            )
            continue
        group = next(iter(value_groups.values()))
        selected.append(
            min(group, key=lambda row: str(row.get("locator") or ""))
        )

    bundle = {"mode": "process_bound", "items": selected}
    bundle_digest = _sha256(bundle)
    selected_ids = {
        str(item.get("id") or "")
        for item in selected
        if str(item.get("id") or "")
    }
    selected_source_sha256s = {
        str(item.get("document_sha256") or "").strip().lower()
        for item in selected
        if _FULL_SHA256_RE.fullmatch(
            str(item.get("document_sha256") or "").strip().lower()
        )
    }
    evidence_set_receipt = build_ingest_evidence_set_receipt(
        project_id=pid,
        audit_path=path,
        trusted_records=[
            record["_trusted_record"]
            for record in records
            if str(record.get("sha256") or "").strip().lower()
            in selected_source_sha256s
            and isinstance(record.get("_trusted_record"), Mapping)
        ],
    )
    evidence_set_validation = validate_ingest_evidence_set_receipt(
        evidence_set_receipt,
        expected_project_id=pid,
    )
    missing_required_item_ids = sorted(required_item_ids - selected_ids)
    unexpected_item_ids = sorted(selected_ids - required_item_ids)
    fact = None
    if (
        required_item_ids
        and selected
        and not conflicts
        and not missing_required_item_ids
        and not unexpected_item_ids
        and evidence_set_validation.get("ok") is True
    ):
        fact = {
            "value": bundle,
            "unit": "",
            "status": "derived",
            "confidence": 1.0,
            "evidence": {
                "locator": "project_parameter_evidence.quality_threshold",
                "source_sha256": bundle_digest,
                "evidence_set_receipt": evidence_set_receipt,
                "evidence_set_receipt_digest": evidence_set_receipt[
                    "receipt_digest"
                ],
            },
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": pid or None,
        "status": (
            "PASS_PROJECT_PARAMETER_EVIDENCE"
            if fact is not None
            else (
                "HOLD_PROJECT_PARAMETER_EVIDENCE_CONFLICT"
                if conflicts
                else (
                    "HOLD_PROJECT_PARAMETER_EVIDENCE_COVERAGE_INCOMPLETE"
                    if required_item_ids
                    else "HOLD_PROJECT_PARAMETER_EVIDENCE_MISSING"
                )
            )
        ),
        "ready": fact is not None,
        "quality_threshold": fact,
        "quality_threshold_bundle_digest": bundle_digest,
        "evidence_set_receipt": evidence_set_receipt,
        "evidence_set_receipt_digest": evidence_set_receipt.get(
            "receipt_digest"
        ),
        "evidence_set_validation": evidence_set_validation,
        "matched_item_count": len(selected),
        "required_item_count": len(required_item_ids),
        "required_item_ids": sorted(required_item_ids),
        "missing_required_item_ids": missing_required_item_ids,
        "unexpected_item_ids": unexpected_item_ids,
        "coverage_complete": bool(
            required_item_ids
            and not missing_required_item_ids
            and not unexpected_item_ids
        ),
        "conflicts": conflicts,
        "source_count": len(records),
        "audit_path": str(path),
    }


def validate_project_parameter_evidence(value: Any) -> dict[str, Any]:
    """Validate the report contract before it may enter the fact ledger."""

    errors: list[str] = []
    report = value if isinstance(value, Mapping) else {}
    if not isinstance(value, Mapping):
        errors.append("report_not_object")
    if str(report.get("schema_version") or "") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if str(report.get("status") or "") != "PASS_PROJECT_PARAMETER_EVIDENCE":
        errors.append("status_not_pass")
    if report.get("ready") is not True:
        errors.append("ready_not_true")
    if report.get("coverage_complete") is not True:
        errors.append("coverage_incomplete")
    if report.get("conflicts") not in ([], ()):
        errors.append("conflicts_present")
    required_ids = {
        str(item or "")
        for item in (
            report.get("required_item_ids")
            if isinstance(report.get("required_item_ids"), list)
            else []
        )
        if str(item or "")
    }
    fact = report.get("quality_threshold")
    bundle = fact.get("value") if isinstance(fact, Mapping) else None
    items = bundle.get("items") if isinstance(bundle, Mapping) else None
    if (
        not isinstance(fact, Mapping)
        or not isinstance(bundle, Mapping)
        or str(bundle.get("mode") or "") != "process_bound"
        or not isinstance(items, list)
        or not items
    ):
        errors.append("quality_threshold_invalid")
        items = []
    item_ids = {
        str(item.get("id") or "")
        for item in items
        if isinstance(item, Mapping) and str(item.get("id") or "")
    }
    if not required_ids or item_ids != required_ids:
        errors.append("required_item_identity_mismatch")
    claimed_digest = str(
        report.get("quality_threshold_bundle_digest") or ""
    ).strip().lower()
    computed_digest = _sha256(bundle) if isinstance(bundle, Mapping) else ""
    if (
        _FULL_SHA256_RE.fullmatch(claimed_digest) is None
        or claimed_digest != computed_digest
    ):
        errors.append("bundle_digest_mismatch")
    fact_evidence = fact.get("evidence") if isinstance(fact, Mapping) else None
    if (
        not isinstance(fact_evidence, Mapping)
        or str(fact_evidence.get("source_sha256") or "").strip().lower()
        != claimed_digest
    ):
        errors.append("fact_evidence_digest_mismatch")
    receipt = (
        report.get("evidence_set_receipt")
        if isinstance(report.get("evidence_set_receipt"), Mapping)
        else {}
    )
    receipt_validation = validate_ingest_evidence_set_receipt(
        receipt,
        expected_project_id=str(report.get("project_id") or "").strip(),
    )
    receipt_digest = str(receipt.get("receipt_digest") or "").strip().lower()
    fact_receipt = (
        fact_evidence.get("evidence_set_receipt")
        if isinstance(fact_evidence, Mapping)
        and isinstance(fact_evidence.get("evidence_set_receipt"), Mapping)
        else {}
    )
    fact_receipt_digest = (
        str(fact_evidence.get("evidence_set_receipt_digest") or "")
        .strip()
        .lower()
        if isinstance(fact_evidence, Mapping)
        else ""
    )
    if receipt_validation.get("ok") is not True:
        errors.append("evidence_set_receipt_invalid")
    receipt_source_sha256s = {
        str(row.get("source_sha256") or "").strip().lower()
        for row in (receipt.get("records") or [])
        if isinstance(row, Mapping)
    }
    item_source_sha256s = {
        str(item.get("document_sha256") or "").strip().lower()
        for item in items
        if isinstance(item, Mapping)
    }
    if (
        not item_source_sha256s
        or receipt_source_sha256s != item_source_sha256s
        or any(
            _FULL_SHA256_RE.fullmatch(value) is None
            for value in item_source_sha256s
        )
    ):
        errors.append("evidence_set_source_identity_mismatch")
    if (
        _FULL_SHA256_RE.fullmatch(receipt_digest) is None
        or str(report.get("evidence_set_receipt_digest") or "").strip().lower()
        != receipt_digest
        or fact_receipt_digest != receipt_digest
        or dict(fact_receipt) != dict(receipt)
    ):
        errors.append("evidence_set_receipt_binding_mismatch")
    return {
        "ok": not errors,
        "errors": list(dict.fromkeys(errors)),
        "claimed_digest": claimed_digest,
        "computed_digest": computed_digest,
        "evidence_set_receipt_validation": receipt_validation,
    }
