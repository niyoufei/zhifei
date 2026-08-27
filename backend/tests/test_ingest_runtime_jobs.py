from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from concurrent.futures.process import BrokenProcessPool
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException

from backend.app.routers import ingest as ingest_router
from backend.zhifei_autoplan.cross_index import build_cross_index
from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate
from backend.zhifei_autoplan.drawing_index import build_drawing_index
from backend.zhifei_autoplan.evidence import search_ingested_docs
from backend.zhifei_autoplan.missing_param_probe import probe_missing_parameters
from backend.zhifei_autoplan.ocr_runtime import OcrResult
from backend.zhifei_autoplan.project_fact_ledger import (
    build_project_fact_ledger_from_inputs,
)
from backend.zhifei_autoplan.project_parameter_evidence import (
    build_project_parameter_evidence,
    validate_project_parameter_evidence,
)
from backend.zhifei_autoplan.standard_index import build_standard_index


class _Upload:
    def __init__(self, data: bytes, filename: str) -> None:
        self._data = data
        self._offset = 0
        self.filename = filename

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._data):
            return b""
        if size < 0:
            size = len(self._data) - self._offset
        end = min(len(self._data), self._offset + size)
        chunk = self._data[self._offset:end]
        self._offset = end
        return chunk

    async def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._offset = offset
        elif whence == 2:
            self._offset = len(self._data) + offset
        return self._offset


def _isolate_workspace(monkeypatch, tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    monkeypatch.setattr(
        ingest_router,
        "_resolve_workspace_context",
        lambda session_id=None, workspace_dir=None: {
            "session_id": "test",
            "workspace_dir": str(workspace),
        },
    )
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")

    async def _no_ocr(
        path: Path,
        ext: str,
        text: str | None,
        **_kwargs: Any,
    ) -> None:
        return None

    monkeypatch.setattr(ingest_router, "_try_ocr", _no_ocr)
    return workspace


def test_full_sha_cache_skips_second_parse(monkeypatch, tmp_path: Path) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    calls = 0
    original = ingest_router._extract_text_path

    def _parse(ext: str, path: Path) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return original(ext, path)

    monkeypatch.setattr(ingest_router, "_extract_text_path", _parse)
    first = asyncio.run(ingest_router._handle_upload([_Upload(b"cached text", "a.txt")]))
    second = asyncio.run(ingest_router._handle_upload([_Upload(b"cached text", "b.txt")]))

    assert calls == 1
    assert first["cache_hits"] == 0
    assert second["cache_hits"] == 1
    assert second["saved"][0]["file_id"] == first["saved"][0]["file_id"]
    saved = first["saved"][0]
    digest = hashlib.sha256(b"cached text").hexdigest()
    assert Path(saved["saved_as"]).name == f"{digest}_a.txt"
    assert Path(saved["extract_saved_as"]).name == (
        f"{digest}_{saved['extract_text_sha256']}.txt"
    )
    assert saved["extract_text_sha256"] == hashlib.sha256(b"cached text").hexdigest()
    audit = ingest_router.json.loads(
        (workspace / "audit" / "ingest.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert audit["extract_text_sha256"] == saved["extract_text_sha256"]


def test_ingest_extract_identity_is_accepted_by_drawing_index(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    result = asyncio.run(
        ingest_router._handle_upload(
            [_Upload("钢梁安装构件位置与节点做法。".encode(), "钢梁图.txt")],
            project_id="p1",
            source_hint="drawing",
        )
    )
    saved = result["saved"][0]

    assert Path(saved["extract_saved_as"]).name == (
        f"{saved['sha256']}_{saved['extract_text_sha256']}.txt"
    )

    drawing_index = build_drawing_index(
        "示例项目",
        ["钢梁安装施工工艺"],
        project_id="p1",
        workspace_dir=workspace,
    )

    assert drawing_index["integrity_rejections"] == []
    assert drawing_index["indexed_drawing_count"] == 1
    assert drawing_index["drawings"][0]["sha256"] == saved["sha256"]
    assert drawing_index["drawings"][0]["extract_saved_as"] == saved[
        "extract_saved_as"
    ]


def test_ingest_extract_identity_is_shared_with_standard_index_and_revalidated(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    result = asyncio.run(
        ingest_router._handle_upload(
            [
                _Upload(
                    (
                        "GB/T 50326-2017 建设工程项目管理规范。"
                        "钢筋绑扎施工工艺应分段验收并保留记录。"
                    ).encode(),
                    "GB_T_50326-2017_建设工程项目管理规范.txt",
                )
            ],
            project_id="p-standard",
            source_hint="standard",
        )
    )
    saved = result["saved"][0]

    standard_index = build_standard_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p-standard",
        workspace_dir=workspace,
    )

    assert standard_index["integrity_rejections"] == []
    assert standard_index["indexed_standard_count"] == 1
    assert standard_index["standards"][0]["sha256"] == saved["sha256"]
    assert standard_index["standards"][0]["source_integrity_status"] == "verified"

    extract_path = Path(saved["extract_saved_as"])
    extract_path.write_bytes(extract_path.read_bytes() + b"tampered")
    rejected = build_standard_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p-standard",
        workspace_dir=workspace,
    )

    assert rejected["indexed_standard_count"] == 0
    assert rejected["integrity_rejections"] == [
        {
            "filename": "GB_T_50326-2017_建设工程项目管理规范.txt",
            "code": "extract_text_sha256_mismatch",
        }
    ]


def _digest(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _approved_project_fact(project_id: str, field: str, value: Any, unit: str) -> dict:
    document_sha256 = hashlib.sha256(field.encode("utf-8")).hexdigest()
    file_name = f"批准参数-{field}.pdf"
    return {
        "value": value,
        "unit": unit,
        "evidence": {
            "file_name": file_name,
            "document_sha256": document_sha256,
            "locator": f"{file_name}#p1_{document_sha256}@10",
        },
        "approval_receipt": {
            "receipt_id": f"APR-{field}",
            "status": "approved",
            "project_id": project_id,
            "field": field,
            "value_digest": _digest(
                {"field": field, "value": value, "unit": unit}
            ),
            "summary": f"批准 {field} 的正式项目值",
            "approved_by": "项目负责人",
            "approved_at": "2026-08-28T08:00:00+08:00",
        },
    }


def _formal_sections(ledger: dict[str, Any], drawing_locator: str) -> list[dict[str, str]]:
    labels = {
        "planned_duration_days": "总工期",
        "resource_peak": "资源峰值",
        "critical_interval_days": "关键线路间隔",
        "risk_inspection_frequency": "风险检查频次",
        "deviation_action_deadline": "偏差处置时限",
    }
    lines = [
        (
            "围墙施工频次1次/周，间距5m，压实系数≥0.97"
            f"【证据:{drawing_locator}】"
        )
    ]
    for field, fact in ledger["facts"].items():
        if field == "quality_threshold":
            for item in fact["value"]["items"]:
                lines.append(
                    f"质量阈值 {item['process']}：{item['metric']}"
                    f"{item['operator']}{item['value']}{item['unit']}"
                    f"【证据:{item['locator']}】"
                )
        elif field in labels:
            lines.append(
                f"{labels[field]}={fact['value']}{fact['unit']}"
                f"【证据:{fact['evidence']['locator']}】"
            )
    return [{"title": "围墙施工工艺", "content": "\n".join(lines)}]


def _delivery_gate(
    *,
    ledger: dict[str, Any],
    parameters: dict[str, Any],
    sections: list[dict[str, str]],
    cross_index: dict[str, Any],
) -> dict[str, Any]:
    return build_delivery_quality_gate(
        strict=True,
        content_review={"quality_gate": {"pass": True, "blocking_issues": []}},
        plan_consistency={"ok": True, "canonical": {"duration_days": 150}},
        model_review_audit={
            "failed_chapters": [],
            "consistency_review": {"ok": True, "summary": "未发现实质性冲突。"},
        },
        requirement_matrix={
            "summary": {
                "strict_delivery_allowed": True,
                "blocking_requirement_ids": [],
            }
        },
        standard_audit={
            "ok": True,
            "verified_standard_count": 1,
            "verified_standard_codes": ["GB_50000_2020"],
            "violation_count": 0,
            "violations": [],
        },
        standard_index={
            "ok": True,
            "project_id": "P-TRUST-CHAIN",
            "standards": [
                {
                    "filename": "施工标准.pdf",
                    "sha256": "8" * 64,
                    "extract_text_sha256": "9" * 64,
                    "standard_code": "GB 50000-2020",
                    "standard_codes": ["GB 50000-2020"],
                    "primary_identity_status": "identified",
                    "official_registry_status": "verified_clause_source",
                    "official_registry": {
                        "status": "verified_clause_source",
                        "standard_code": "GB 50000-2020",
                    },
                    "text_status": "indexed",
                    "source_integrity_status": "verified",
                    "clause_evidence_eligible": True,
                    "clause_evidence_source": "ingested_standard_text",
                    "registry_metadata_used_as_clause_evidence": False,
                    "page_anchors": [
                        {
                            "page": 1,
                            "text_sha256": "7" * 64,
                            "evidence_eligible": True,
                        }
                    ],
                }
            ],
            "indexed_standard_count": 1,
            "official_registry_verified_count": 1,
            "integrity_rejection_count": 0,
            "invalid_identity_count": 0,
            "missing_text_or_ocr_count": 0,
            "locator_unavailable_count": 0,
            "text_index_status": "complete",
        },
        cross_index=cross_index,
        model_review_required=True,
        formal_delivery_required=True,
        project_parameters=parameters,
        project_fact_ledger=ledger,
        sections=sections,
    )


def test_ingest_to_delivery_trust_chain_rejects_tamper_and_forged_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_id = "P-TRUST-CHAIN"
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    drawings = asyncio.run(
        ingest_router._handle_upload(
            [
                _Upload(
                    (
                        "围墙基础开挖至标高后进行压实，压实系数不小于0.97。"
                    ).encode(),
                    "3 围墙图.txt",
                ),
                _Upload(
                    (
                        "车辆消毒池采用防水混凝土，其强度等级不应低于C25，"
                        "试配混凝土的抗渗等级应比设计要求提高0.2MPa。"
                    ).encode(),
                    "6 车辆消毒池图.txt",
                ),
            ],
            project_id=project_id,
            source_hint="drawing",
        )
    )
    clarification = asyncio.run(
        ingest_router._handle_upload(
            [
                _Upload(
                    (
                        "问题：基础和垫层强度？回复：基础 C30 垫层C20。"
                        "地面涂膜防水厚度按照多少计入？回复：1.8mm厚。"
                    ).encode(),
                    "答疑.txt",
                )
            ],
            project_id=project_id,
            source_hint="tender_qa",
        )
    )
    audit_path = workspace / "audit" / "ingest.jsonl"

    hits = search_ingested_docs(
        "压实系数",
        audit_path=audit_path,
        project_id=project_id,
    )
    assert len(hits) == 1
    assert hits[0]["extract_text_sha256"] == drawings["saved"][0][
        "extract_text_sha256"
    ]

    drawing_index = build_drawing_index(
        "围墙项目",
        ["围墙施工工艺"],
        project_id=project_id,
        workspace_dir=workspace,
    )
    assert drawing_index["integrity_rejections"] == []
    assert drawing_index["indexed_drawing_count"] == 2
    wall_binding = next(
        binding
        for binding in drawing_index["chapter_bindings"]
        if binding["chapter"] == "围墙施工工艺"
    )
    drawing_locator = wall_binding["locator"]

    parameter_evidence = build_project_parameter_evidence(
        project_id=project_id,
        tender={},
        audit_path=audit_path,
    )
    assert parameter_evidence["ready"] is True
    assert parameter_evidence["matched_item_count"] == 6
    assert validate_project_parameter_evidence(parameter_evidence)["ok"] is True

    approved = {
        "planned_duration_days": _approved_project_fact(
            project_id, "planned_duration_days", 150, "天"
        ),
        "resource_peak": _approved_project_fact(
            project_id, "resource_peak", 20, "人"
        ),
        "critical_interval_days": _approved_project_fact(
            project_id, "critical_interval_days", 5, "天"
        ),
        "risk_inspection_frequency": _approved_project_fact(
            project_id, "risk_inspection_frequency", "1次/周", ""
        ),
        "deviation_action_deadline": _approved_project_fact(
            project_id, "deviation_action_deadline", "36小时", ""
        ),
    }
    ledger = build_project_fact_ledger_from_inputs(
        payload={
            "project_id": project_id,
            "approved_project_fact_resolutions": approved,
        },
        tender={},
        boq_wbs_cpm={},
        project_parameter_evidence=parameter_evidence,
    )
    parameters = probe_missing_parameters(
        topic="围墙项目",
        outline=["围墙施工工艺"],
        requirements=[],
        tender={},
        boq={},
        enterprise_profile={},
        project_fact_ledger=ledger,
    )
    parameters["project_fact_ledger_digest"] = ledger["ledger_digest"]
    assert parameters["formal_ready"] is True
    sections = _formal_sections(ledger, drawing_locator)
    cross_index = build_cross_index(
        boq={
            "items": [
                {
                    "name": "围墙",
                    "boq_code": "001",
                    "quantity": 10,
                    "unit": "m",
                    "process": {"name": "围墙施工"},
                }
            ],
            "stats": {
                "top_quantity_items": [
                    {"name": "围墙", "quantity": 10, "unit": "m"}
                ]
            },
        },
        sections=sections,
        boq_focus={"must_cover_keywords": ["围墙"]},
        drawing_index=drawing_index,
        standard_index={"standards": [], "chapter_bindings": []},
        quality_checks={
            "boq_focus_item_closure": {
                "items": [
                    {
                        "item": "围墙",
                        "ok": True,
                        "reason": "ok",
                        "hit_sections": [
                            {
                                "title": "围墙施工工艺",
                                "ok": True,
                                "triplet_count": 1,
                                "hit_keys": ["频次", "间距", "阈值"],
                                "has_units": True,
                                "evidence_count": 1,
                            }
                        ],
                    }
                ]
            }
        },
        project_id=project_id,
    )
    assert cross_index["closed_ok_count"] == 1
    assert cross_index["missing_drawing_locator_count"] == 0
    gate = _delivery_gate(
        ledger=ledger,
        parameters=parameters,
        sections=sections,
        cross_index=cross_index,
    )
    assert gate["delivery_allowed"] is True, gate

    wall_extract = Path(drawings["saved"][0]["extract_saved_as"])
    original_extract = wall_extract.read_bytes()
    wall_extract.write_bytes(original_extract + "篡改".encode())
    assert search_ingested_docs(
        "压实系数", audit_path=audit_path, project_id=project_id
    ) == []
    assert validate_project_parameter_evidence(parameter_evidence)["ok"] is False
    tampered_gate = _delivery_gate(
        ledger=ledger,
        parameters=parameters,
        sections=sections,
        cross_index=cross_index,
    )
    assert tampered_gate["delivery_allowed"] is False
    formal_check = next(
        check
        for check in tampered_gate["checks"]
        if check["name"] == "formal_project_parameters"
    )
    tamper_reasons = {
        row["field"]: row["reasons"]
        for row in formal_check["source_evidence_errors"]
    }
    assert "evidence_set_receipt_invalid" in tamper_reasons["quality_threshold"]

    wall_extract.write_bytes(original_extract)
    same_source_ledger = copy.deepcopy(ledger)
    same_source_fact = same_source_ledger["facts"]["quality_threshold"]
    same_source_item = same_source_fact["value"]["items"][0]
    false_offset = same_source_item["page_start_offset"] + 1
    same_source_item["offset"] = false_offset
    same_source_item["end"] = false_offset + 1
    same_source_item["page_match_start"] = 1
    same_source_item["page_match_end"] = 2
    same_source_item["locator"] = (
        f"{same_source_item['locator'].split('@', 1)[0]}@{false_offset}"
    )
    same_source_item["page_text_sha256"] = "a" * 64
    same_source_item["match_text_sha256"] = "b" * 64
    same_source_evidence = same_source_fact["evidence"]
    same_source_evidence["source_sha256"] = _digest(same_source_fact["value"])
    same_source_evidence["evidence_digest"] = _digest(
        {
            key: value
            for key, value in same_source_evidence.items()
            if key != "evidence_digest"
        }
    )
    same_source_report = copy.deepcopy(parameter_evidence)
    same_source_report["quality_threshold"] = copy.deepcopy(same_source_fact)
    same_source_report["quality_threshold_bundle_digest"] = same_source_evidence[
        "source_sha256"
    ]
    same_source_report_validation = validate_project_parameter_evidence(
        same_source_report
    )
    assert same_source_report_validation["ok"] is False
    assert "quality_bundle_current_bytes_mismatch" in same_source_report_validation[
        "errors"
    ]
    same_source_ledger["ledger_digest"] = _digest(
        {
            key: value
            for key, value in same_source_ledger.items()
            if key != "ledger_digest"
        }
    )
    same_source_parameters = copy.deepcopy(parameters)
    same_source_parameters["project_fact_ledger_digest"] = same_source_ledger[
        "ledger_digest"
    ]
    same_source_gate = _delivery_gate(
        ledger=same_source_ledger,
        parameters=same_source_parameters,
        sections=_formal_sections(same_source_ledger, drawing_locator),
        cross_index=cross_index,
    )
    assert same_source_gate["delivery_allowed"] is False
    same_source_formal = next(
        check
        for check in same_source_gate["checks"]
        if check["name"] == "formal_project_parameters"
    )
    same_source_reasons = {
        row["field"]: row["reasons"]
        for row in same_source_formal["source_evidence_errors"]
    }
    assert "quality_bundle_current_bytes_mismatch" in same_source_reasons[
        "quality_threshold"
    ]

    forged_ledger = copy.deepcopy(ledger)
    quality_fact = forged_ledger["facts"]["quality_threshold"]
    forged_item = quality_fact["value"]["items"][0]
    forged_item["document_sha256"] = "f" * 64
    forged_item["locator"] = f"伪造图纸.pdf#p1_{'f' * 64}@{forged_item['offset']}"
    evidence = quality_fact["evidence"]
    evidence["source_sha256"] = _digest(quality_fact["value"])
    evidence["evidence_digest"] = _digest(
        {key: value for key, value in evidence.items() if key != "evidence_digest"}
    )
    forged_ledger["ledger_digest"] = _digest(
        {
            key: value
            for key, value in forged_ledger.items()
            if key != "ledger_digest"
        }
    )
    forged_parameters = copy.deepcopy(parameters)
    forged_parameters["project_fact_ledger_digest"] = forged_ledger[
        "ledger_digest"
    ]
    forged_sections = _formal_sections(forged_ledger, drawing_locator)
    forged_gate = _delivery_gate(
        ledger=forged_ledger,
        parameters=forged_parameters,
        sections=forged_sections,
        cross_index=cross_index,
    )
    assert forged_gate["delivery_allowed"] is False
    forged_formal = next(
        check
        for check in forged_gate["checks"]
        if check["name"] == "formal_project_parameters"
    )
    forged_reasons = {
        row["field"]: row["reasons"]
        for row in forged_formal["source_evidence_errors"]
    }
    assert "evidence_set_source_identity_mismatch" in forged_reasons[
        "quality_threshold"
    ]

    audit_rows = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    revised_wall_row = next(
        row
        for row in reversed(audit_rows)
        if row.get("sha256") == drawings["saved"][0]["sha256"]
    )
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {**revised_wall_row, "audit_revision_note": "metadata-only-v2"},
                ensure_ascii=False,
            )
            + "\n"
        )
    revised_evidence = build_project_parameter_evidence(
        project_id=project_id,
        tender={},
        audit_path=audit_path,
    )
    assert revised_evidence["ready"] is True
    assert revised_evidence["evidence_set_receipt_digest"] != parameter_evidence[
        "evidence_set_receipt_digest"
    ]
    revised_ledger = build_project_fact_ledger_from_inputs(
        payload={
            "project_id": project_id,
            "approved_project_fact_resolutions": approved,
        },
        tender={},
        boq_wbs_cpm={},
        project_parameter_evidence=revised_evidence,
    )
    revised_parameters = probe_missing_parameters(
        topic="围墙项目",
        outline=["围墙施工工艺"],
        requirements=[],
        tender={},
        boq={},
        enterprise_profile={},
        project_fact_ledger=revised_ledger,
    )
    revised_parameters["project_fact_ledger_digest"] = revised_ledger[
        "ledger_digest"
    ]
    revised_gate = _delivery_gate(
        ledger=revised_ledger,
        parameters=revised_parameters,
        sections=_formal_sections(revised_ledger, drawing_locator),
        cross_index=cross_index,
    )
    assert revised_gate["delivery_allowed"] is True, revised_gate
    assert revised_gate["decision_digest"] != gate["decision_digest"]

    assert clarification["saved"][0]["extract_text_sha256"]


def test_upload_rejects_existing_full_sha_path_with_wrong_bytes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    payload = b"content-addressed-source"
    digest = hashlib.sha256(payload).hexdigest()
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    collision = workspace / "uploads" / day / f"{digest}_source.txt"
    collision.parent.mkdir(parents=True, exist_ok=True)
    collision.write_bytes(b"different-bytes")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            ingest_router._handle_upload(
                [_Upload(payload, "source.txt")],
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "CONTENT_ADDRESS_COLLISION"
    assert collision.read_bytes() == b"different-bytes"


def test_upload_rejects_existing_full_sha_extract_with_wrong_digest(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    payload = b"expected extracted text"
    digest = hashlib.sha256(payload).hexdigest()
    expected_extract_digest = hashlib.sha256(payload).hexdigest()
    collision = workspace / "extracts" / (
        f"{digest}_{expected_extract_digest}.txt"
    )
    collision.parent.mkdir(parents=True, exist_ok=True)
    collision.write_bytes(b"different-extract")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            ingest_router._handle_upload(
                [_Upload(payload, "source.txt")],
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "EXTRACT_CONTENT_COLLISION"
    assert collision.read_bytes() == b"different-extract"


def test_file_id_resolution_verifies_full_path_and_keeps_legacy_read_compatibility(
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "uploads"
    root.mkdir()
    monkeypatch.setattr(ingest_router, "FILE_ID_SEARCH_ROOTS", (root,))
    legacy_payload = b"legacy-content"
    legacy_digest = hashlib.sha256(legacy_payload).hexdigest()
    legacy_path = root / f"{legacy_digest[:8]}_legacy.pdf"
    legacy_path.write_bytes(legacy_payload)

    assert ingest_router.resolve_ingested_file_ids([legacy_digest]) == [
        str(legacy_path)
    ]

    bad_payload = b"expected-content"
    bad_digest = hashlib.sha256(bad_payload).hexdigest()
    (root / f"{bad_digest}_collision.pdf").write_bytes(b"wrong-content")
    with pytest.raises(HTTPException) as exc_info:
        ingest_router.resolve_ingested_file_ids([bad_digest])

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "CONTENT_ADDRESS_COLLISION"


def test_parse_cache_spills_extracted_text_to_validated_sidecar(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"source").hexdigest()
    extracted_text = "有效正文" * 100_000
    parsed = {
        "base": {
            "doc_type": "txt",
            "pages": 1,
            "text_bytes": len(extracted_text.encode("utf-8")),
            "extract_text": extracted_text,
        },
        "parsed_type": None,
        "parsed_meta": None,
    }

    ingest_router._save_parse_cache(digest, parsed)

    metadata_path = ingest_router._parse_cache_path(digest)
    text_path = ingest_router._parse_cache_text_path(digest)
    metadata = metadata_path.read_text(encoding="utf-8")
    assert extracted_text not in metadata
    assert text_path.read_text(encoding="utf-8") == extracted_text
    assert ingest_router._load_parse_cache(digest) == parsed

    metadata_without_sha = ingest_router.json.loads(metadata)
    metadata_without_sha["extract_text_sidecar"].pop("sha256")
    metadata_path.write_text(
        ingest_router.json.dumps(metadata_without_sha, ensure_ascii=False),
        encoding="utf-8",
    )
    assert ingest_router._load_parse_cache(digest) is None

    ingest_router._save_parse_cache(digest, parsed)
    text_path.write_text(extracted_text[:-1], encoding="utf-8")
    assert ingest_router._load_parse_cache(digest) is None


def test_parse_cache_rejects_same_length_sidecar_content_tamper(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"tamper-source").hexdigest()
    extracted_text = "有效正文" * 100_000
    parsed = {
        "base": {"doc_type": "txt", "extract_text": extracted_text},
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(digest, parsed)
    text_path = ingest_router._parse_cache_text_path(digest)
    original_bytes = text_path.read_bytes()

    text_path.write_text("无" + extracted_text[1:], encoding="utf-8")

    assert text_path.stat().st_size == len(original_bytes)
    assert ingest_router._load_parse_cache(digest) is None


def test_parse_cache_keeps_legacy_inline_text_compatible(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"legacy-source").hexdigest()
    path = ingest_router._parse_cache_path(digest)
    path.parent.mkdir(parents=True)
    parsed = {
        "base": {"doc_type": "txt", "extract_text": "旧缓存正文"},
        "parsed_type": None,
        "parsed_meta": None,
    }
    path.write_text(
        ingest_router.json.dumps(
            {
                "parser_version": ingest_router.PARSER_VERSION,
                "ocr_policy": ingest_router.OCR_POLICY_ORDINARY,
                "sha256": digest,
                "parsed": parsed,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert ingest_router._load_parse_cache(digest) == parsed


def test_parse_cache_does_not_reuse_runtime_v5_ocr_cache(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"drawing-cache-source").hexdigest()
    old_version = "2026.08.runtime-v5-source-aware-ocr-cache"
    old_version_digest = hashlib.sha256(old_version.encode("utf-8")).hexdigest()[:12]
    old_path = ingest_router.PARSE_CACHE_DIR / f"{digest}.{old_version_digest}.json"
    old_path.parent.mkdir(parents=True)
    old_path.write_text(
        ingest_router.json.dumps(
            {
                "parser_version": old_version,
                "sha256": digest,
                "parsed": {
                    "base": {
                        "doc_type": "pdf",
                        "pages": 27,
                        "extract_text": "旧版前十页 OCR 结果",
                    },
                    "parsed_type": None,
                    "parsed_meta": None,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert ingest_router.PARSER_VERSION != old_version
    assert ingest_router._parse_cache_path(digest) != old_path
    assert ingest_router._load_parse_cache(digest) is None


def test_drawing_cache_does_not_reuse_direct_v6_predecessor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"v6-drawing-cache-source").hexdigest()
    old_version = "2026.08.runtime-v6-bounded-ocr-proof"
    old_identity = f"{old_version}:{ingest_router.OCR_POLICY_DRAWING}"
    old_identity_digest = hashlib.sha256(old_identity.encode()).hexdigest()[:12]
    old_path = ingest_router.PARSE_CACHE_DIR / (
        f"{digest}.{old_identity_digest}.json"
    )
    old_path.parent.mkdir(parents=True)
    old_path.write_text(
        ingest_router.json.dumps(
            {
                "parser_version": old_version,
                "ocr_policy": ingest_router.OCR_POLICY_DRAWING,
                "sha256": digest,
                "parsed": {
                    "base": {
                        "doc_type": "pdf",
                        "pages": 1,
                        "ocr_pages": 1,
                        "ocr_page_mapping": "source_page_all",
                        "extract_text": "旧 v6 图纸 OCR",
                    },
                    "parsed_type": None,
                    "parsed_meta": None,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    assert ingest_router.PARSER_VERSION != old_version
    assert ingest_router._parse_cache_path(digest, "drawing") != old_path
    assert ingest_router._load_parse_cache(digest, source_hint="drawing") is None


def test_same_pdf_ordinary_cache_does_not_pollute_drawing_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"same-pdf-cross-policy").hexdigest()
    ordinary = {
        "base": {
            "doc_type": "pdf",
            "pages": 27,
            "ocr_pages": 10,
            "ocr_page_mapping": "source_page_prefix",
            "extract_text": "普通资料前十页 OCR",
        },
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(digest, ordinary, source_hint="tender_qa")

    assert ingest_router._load_parse_cache(digest, source_hint="tender") == ordinary
    assert ingest_router._parse_cache_path(
        digest,
        "tender_qa",
    ) != ingest_router._parse_cache_path(digest, "drawing_standard")
    assert ingest_router._load_parse_cache(digest, source_hint="drawing") is None


def test_drawing_cache_requires_ocr_for_every_declared_page(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"drawing-full-page-cache").hexdigest()
    complete = {
        "base": {
            "doc_type": "pdf",
            "pages": 27,
            "ocr_source_pages": 27,
            "ocr_pages": 27,
            "ocr_page_text_count": 27,
            "ocr_page_mapping": "source_page_all",
            "extract_text": "\f".join(
                f"第{page}页图纸 OCR" for page in range(1, 28)
            ),
            "ocr_page_statuses": ["text"] * 27,
            "ocr_page_image_sha256": [
                hashlib.sha256(f"drawing-image-{page}".encode()).hexdigest()
                for page in range(1, 28)
            ],
            "ocr_page_text_sha256": [
                hashlib.sha256(f"第{page}页图纸 OCR".encode()).hexdigest()
                for page in range(1, 28)
            ],
            "ocr_extract_page_sha256": [
                hashlib.sha256(f"第{page}页图纸 OCR".encode()).hexdigest()
                for page in range(1, 28)
            ],
            "ocr_page_proof_version": ingest_router.OCR_PAGE_PROOF_VERSION,
            "ocr_error": None,
            "ocr_blank_pages": [],
            "ocr_graphics_only_pages": [],
            "ocr_no_text_locators": [],
        },
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(digest, complete, source_hint="drawing")
    assert ingest_router._load_parse_cache(digest, source_hint="图纸") == complete

    metadata_path = ingest_router._parse_cache_path(digest, "drawing_standard")
    metadata = ingest_router.json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["parsed"]["base"]["ocr_page_text_count"] = 26
    metadata_path.write_text(
        ingest_router.json.dumps(metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    assert ingest_router._load_parse_cache(digest, source_hint="cad") is None

    incomplete_digest = hashlib.sha256(b"drawing-incomplete-cache").hexdigest()
    incomplete = {
        **complete,
        "base": {
            **complete["base"],
            "ocr_pages": 26,
            "ocr_page_text_count": 26,
        },
    }
    ingest_router._save_parse_cache(
        incomplete_digest,
        incomplete,
        source_hint="drawing_standard",
    )
    assert not ingest_router._parse_cache_path(
        incomplete_digest,
        "drawing_standard",
    ).exists()
    assert ingest_router._load_parse_cache(
        incomplete_digest,
        source_hint="cad",
    ) is None

    failed_page_digest = hashlib.sha256(b"drawing-failed-page-cache").hexdigest()
    failed_page = {
        **complete,
        "base": {
            **complete["base"],
            "ocr_page_statuses": ["failed", *(["text"] * 26)],
            "ocr_page_image_sha256": [
                "",
                *complete["base"]["ocr_page_image_sha256"][1:],
            ],
            "ocr_error": "page_ocr_incomplete",
        },
    }
    ingest_router._save_parse_cache(
        failed_page_digest,
        failed_page,
        source_hint="drawing",
    )
    assert not ingest_router._parse_cache_path(
        failed_page_digest,
        "drawing",
    ).exists()

    graphics_digest = hashlib.sha256(b"drawing-graphics-page-cache").hexdigest()
    graphics_complete = copy.deepcopy(complete)
    graphics_complete["base"]["ocr_page_statuses"][2] = "graphics_only"
    graphics_complete["base"]["ocr_page_text_sha256"][2] = hashlib.sha256(
        b""
    ).hexdigest()
    graphics_complete["base"]["ocr_graphics_only_pages"] = [3]
    graphics_complete["base"]["ocr_no_text_locators"] = [
        {
            "page": 3,
            "status": "graphics_only",
            "reason": "no_machine_readable_text",
            "page_image_sha256": graphics_complete["base"][
                "ocr_page_image_sha256"
            ][2],
            "no_text_locator": True,
        }
    ]
    ingest_router._save_parse_cache(
        graphics_digest,
        graphics_complete,
        source_hint="drawing",
    )
    assert ingest_router._load_parse_cache(
        graphics_digest,
        source_hint="drawing",
    ) == graphics_complete

    graphics_cache_path = ingest_router._parse_cache_path(
        graphics_digest,
        "drawing",
    )
    graphics_metadata = ingest_router.json.loads(
        graphics_cache_path.read_text(encoding="utf-8")
    )
    graphics_metadata["parsed"]["base"]["ocr_no_text_locators"][0][
        "page_image_sha256"
    ] = "f" * 64
    graphics_cache_path.write_text(
        ingest_router.json.dumps(graphics_metadata, ensure_ascii=False),
        encoding="utf-8",
    )
    assert ingest_router._load_parse_cache(
        graphics_digest,
        source_hint="drawing",
    ) is None


def test_standard_cache_is_full_page_and_isolated_from_drawing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"standard-full-page-cache").hexdigest()
    complete = {
        "base": {
            "doc_type": "pdf",
            "pages": 4,
            "ocr_source_pages": 4,
            "ocr_pages": 4,
            "ocr_page_text_count": 4,
            "ocr_page_mapping": "source_page_all",
            "extract_text": "\f".join(f"第{page}页" for page in range(1, 5)),
            "ocr_page_statuses": ["text"] * 4,
            "ocr_page_image_sha256": [
                hashlib.sha256(f"image-{page}".encode()).hexdigest()
                for page in range(1, 5)
            ],
            "ocr_page_text_sha256": [
                hashlib.sha256(f"第{page}页".encode()).hexdigest()
                for page in range(1, 5)
            ],
            "ocr_extract_page_sha256": [
                hashlib.sha256(f"第{page}页".encode()).hexdigest()
                for page in range(1, 5)
            ],
            "ocr_page_proof_version": ingest_router.OCR_PAGE_PROOF_VERSION,
            "ocr_error": None,
            "ocr_blank_pages": [],
            "ocr_graphics_only_pages": [],
            "ocr_no_text_locators": [],
        },
        "parsed_type": None,
        "parsed_meta": None,
    }

    ingest_router._save_parse_cache(digest, complete, source_hint="standard")

    assert ingest_router._ocr_cache_policy("标准") == (
        ingest_router.OCR_POLICY_STANDARD
    )
    assert ingest_router._load_parse_cache(digest, source_hint="standard") == complete
    assert ingest_router._parse_cache_path(
        digest,
        "standard",
    ) != ingest_router._parse_cache_path(digest, "drawing_standard")
    assert ingest_router._load_parse_cache(
        digest,
        source_hint="drawing_standard",
    ) is None

    incomplete_digest = hashlib.sha256(b"standard-partial-cache").hexdigest()
    incomplete = {
        **complete,
        "base": {
            **complete["base"],
            "ocr_pages": 3,
            "ocr_page_text_count": 3,
        },
    }
    ingest_router._save_parse_cache(
        incomplete_digest,
        incomplete,
        source_hint="standard",
    )
    assert not ingest_router._parse_cache_path(
        incomplete_digest,
        "standard",
    ).exists()

    text_digest = hashlib.sha256(b"standard-native-text").hexdigest()
    native_text = {
        "base": {
            "doc_type": "docx",
            "pages": None,
            "extract_text": "已完整解析的企业标准正文",
        },
        "parsed_type": None,
        "parsed_meta": None,
    }
    ingest_router._save_parse_cache(
        text_digest,
        native_text,
        source_hint="standard",
    )
    assert ingest_router._load_parse_cache(
        text_digest,
        source_hint="standard",
    ) == native_text


def test_try_ocr_standard_pdf_uses_declared_full_page_bound(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from backend.zhifei_autoplan import ocr_runtime

    observed: dict[str, Any] = {}

    def _ocr_pdf_path(
        _path: str,
        *,
        max_pages: int,
        scale: float,
        lang: str,
        stop_on_catalog: bool,
        allow_graphics_only: bool,
    ) -> OcrResult:
        observed.update(
            {
                "max_pages": max_pages,
                "scale": scale,
                "lang": lang,
                "stop_on_catalog": stop_on_catalog,
                "allow_graphics_only": allow_graphics_only,
            }
        )
        return OcrResult(
            text="第1页\f\f第3页",
            pages=3,
            lang="chi_sim+eng",
            page_texts=("第1页", "", "第3页"),
            page_statuses=("text", "blank", "text"),
            page_image_sha256=tuple(
                hashlib.sha256(f"image-{page}".encode()).hexdigest()
                for page in range(1, 4)
            ),
            source_pages=3,
        )

    monkeypatch.setattr(ocr_runtime, "is_tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_runtime, "guess_ocr_lang", lambda **_kwargs: "chi_sim+eng")
    monkeypatch.setattr(ocr_runtime, "ocr_pdf_path", _ocr_pdf_path)

    result = asyncio.run(
        ingest_router._try_ocr(
            tmp_path / "standard.pdf",
            "pdf",
            "内嵌字体文本" * 100,
            source_hint="standard",
            declared_pages=3,
        )
    )

    assert isinstance(result, OcrResult)
    assert observed == {
        "max_pages": 3,
        "scale": 2.2,
        "lang": "chi_sim+eng",
        "stop_on_catalog": False,
        "allow_graphics_only": False,
    }


def test_handle_upload_reparses_same_pdf_when_ocr_policy_changes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    parse_calls: list[str] = []
    ocr_policies: list[str] = []

    async def _parse(ext: str, _path: Path, _total_bytes: int) -> dict[str, Any]:
        parse_calls.append(ext)
        return {
            "doc_type": "pdf",
            "pages": 3,
            "text_bytes": 2,
            "extract_text": "\f\f",
        }

    async def _ocr(
        _path: Path,
        _ext: str,
        _text: str | None,
        *,
        source_hint: str | None = None,
        declared_pages: int | None = None,
    ) -> OcrResult:
        policy = ingest_router._ocr_cache_policy(source_hint)
        ocr_policies.append(policy)
        pages = declared_pages if policy == ingest_router.OCR_POLICY_DRAWING else 2
        assert isinstance(pages, int)
        return OcrResult(
            text="\f".join(f"第{index + 1}页" for index in range(pages)),
            pages=pages,
            lang="chi_sim+eng",
            page_texts=tuple(f"第{index + 1}页" for index in range(pages)),
            page_statuses=tuple("text" for _ in range(pages)),
            page_image_sha256=tuple(
                hashlib.sha256(f"image-{index + 1}".encode()).hexdigest()
                for index in range(pages)
            ),
            source_pages=3,
        )

    monkeypatch.setattr(ingest_router, "_extract_text_path_bounded", _parse)
    monkeypatch.setattr(ingest_router, "_try_ocr", _ocr)
    monkeypatch.setattr(
        ingest_router,
        "_run_isolated_process",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=None),
    )
    payload = b"same-pdf-content"

    ordinary = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "ordinary.pdf")],
            source_hint="tender_qa",
        )
    )
    drawing = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "drawing.pdf")],
            source_hint="drawing_standard",
        )
    )
    drawing_cached = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "drawing-again.pdf")],
            source_hint="drawing",
        )
    )

    assert ordinary["cache_hits"] == 0
    assert ordinary["saved"][0]["ocr_pages"] == 2
    assert ordinary["saved"][0]["ocr_page_mapping"] == "source_page_prefix"
    assert drawing["cache_hits"] == 0
    assert drawing["saved"][0]["ocr_pages"] == 3
    assert drawing["saved"][0]["ocr_page_text_count"] == 3
    assert drawing["saved"][0]["ocr_page_mapping"] == "source_page_all"
    assert drawing["saved"][0]["ocr_page_statuses"] == ["text"] * 3
    assert len(drawing["saved"][0]["ocr_extract_page_sha256"]) == 3
    assert drawing_cached["cache_hits"] == 1
    assert drawing_cached["saved"][0]["ocr_pages"] == 3
    assert drawing_cached["saved"][0]["ocr_page_mapping"] == "source_page_all"
    assert parse_calls == ["pdf", "pdf"]
    assert ocr_policies == [
        ingest_router.OCR_POLICY_ORDINARY,
        ingest_router.OCR_POLICY_DRAWING,
    ]


def test_handle_upload_standard_uses_full_page_ocr_and_standard_tag_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    observed: list[tuple[str | None, int | None]] = []

    async def _parse(ext: str, _path: Path, _total_bytes: int) -> dict[str, Any]:
        assert ext == "pdf"
        return {
            "doc_type": "pdf",
            "pages": 3,
            "text_bytes": 2,
            "extract_text": "\f\f",
        }

    async def _ocr(
        _path: Path,
        _ext: str,
        _text: str | None,
        *,
        source_hint: str | None = None,
        declared_pages: int | None = None,
    ) -> OcrResult:
        observed.append((source_hint, declared_pages))
        return OcrResult(
            text="第1页\f\f第3页",
            pages=3,
            lang="chi_sim+eng",
            page_texts=("第1页", "", "第3页"),
            page_statuses=("text", "blank", "text"),
            page_image_sha256=tuple(
                hashlib.sha256(f"image-{page}".encode()).hexdigest()
                for page in range(1, 4)
            ),
            source_pages=3,
        )

    monkeypatch.setattr(ingest_router, "_extract_text_path_bounded", _parse)
    monkeypatch.setattr(ingest_router, "_try_ocr", _ocr)
    monkeypatch.setattr(
        ingest_router,
        "_run_isolated_process",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=None),
    )

    result = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(b"standard-pdf-content", "结构施工图.pdf")],
            source_hint="standard",
            project_id="p1",
        )
    )

    saved = result["saved"][0]
    assert observed == [("standard", 3)]
    assert saved["ocr_cache_policy"] == ingest_router.OCR_POLICY_STANDARD
    assert saved["ocr_pages"] == 3
    assert saved["ocr_page_text_count"] == 3
    assert saved["ocr_page_mapping"] == "source_page_all"
    assert saved["ocr_page_proof_version"] == ingest_router.OCR_PAGE_PROOF_VERSION
    assert saved["ocr_source_pages"] == 3
    assert saved["ocr_page_statuses"] == ["text", "blank", "text"]
    assert saved["ocr_blank_pages"] == [2]
    assert len(saved["ocr_extract_page_sha256"]) == 3
    assert saved["extract_text_sha256"] == hashlib.sha256(
        Path(saved["extract_saved_as"]).read_bytes()
    ).hexdigest()
    assert Path(saved["saved_as"]).name.startswith(f"{saved['sha256']}_")
    assert Path(saved["extract_saved_as"]).name == (
        f"{saved['sha256']}_{saved['extract_text_sha256']}.txt"
    )
    assert saved["tags"] == ["standard"]


def test_drawing_graphics_only_page_is_cached_but_never_searchable_text(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from backend.zhifei_autoplan import evidence as evidence_module

    workspace = _isolate_workspace(monkeypatch, tmp_path)

    async def _parse(ext: str, _path: Path, _total_bytes: int) -> dict[str, Any]:
        assert ext == "pdf"
        return {
            "doc_type": "pdf",
            "pages": 3,
            "text_bytes": 0,
            "extract_text": "原生首页\f图形页残字 钢梁安装\f原生末页",
        }

    page_images = tuple(
        hashlib.sha256(f"graphics-image-{page}".encode()).hexdigest()
        for page in range(1, 4)
    )

    async def _ocr(*_args: Any, **_kwargs: Any) -> OcrResult:
        return OcrResult(
            text="总说明\f\f钢梁安装",
            pages=3,
            lang="chi_sim+eng",
            page_texts=("总说明", "", "钢梁安装"),
            page_statuses=("text", "graphics_only", "text"),
            page_image_sha256=page_images,
            source_pages=3,
            diagnostics={
                "schema_version": "ocr-diagnostics-v1",
                "machine_code": "OCR_COMPLETE_WITH_GRAPHICS_ONLY",
                "error_code": "none",
                "status_counts": {"graphics_only": 1, "text": 2},
                "graphics_only_pages": [2],
            },
        )

    monkeypatch.setattr(ingest_router, "_extract_text_path_bounded", _parse)
    monkeypatch.setattr(ingest_router, "_try_ocr", _ocr)
    monkeypatch.setattr(
        ingest_router,
        "_run_isolated_process",
        lambda *_args, **_kwargs: asyncio.sleep(0, result=None),
    )
    payload = b"mixed-text-and-graphics-drawing"
    first = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "mixed.pdf")],
            source_hint="drawing",
            project_id="p1",
        )
    )
    second = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(payload, "mixed-cache.pdf")],
            source_hint="drawing",
            project_id="p1",
        )
    )

    saved = first["saved"][0]
    assert first["cache_hits"] == 0
    assert second["cache_hits"] == 1
    assert saved["ocr_page_proof_version"] == "ocr-page-proof-v3"
    assert saved["ocr_page_statuses"] == ["text", "graphics_only", "text"]
    assert saved["ocr_graphics_only_pages"] == [2]
    assert saved["ocr_no_text_locators"] == [
        {
            "page": 2,
            "status": "graphics_only",
            "reason": "no_machine_readable_text",
            "page_image_sha256": page_images[1],
            "no_text_locator": True,
        }
    ]
    assert second["saved"][0]["ocr_no_text_locators"] == saved[
        "ocr_no_text_locators"
    ]
    evidence_module._load_audit_records.cache_clear()
    audit_path = workspace / "audit" / "ingest.jsonl"
    text_hit = search_ingested_docs(
        "钢梁安装",
        project_id="p1",
        audit_path=audit_path,
    )
    assert text_hit
    assert text_hit[0]["page"] == 3
    assert search_ingested_docs(
        "图形页残字",
        project_id="p1",
        audit_path=audit_path,
    ) == []

    with pytest.raises(HTTPException):
        asyncio.run(
            ingest_router._handle_upload(
                [_Upload(payload, "mixed-standard.pdf")],
                source_hint="standard",
                project_id="p1",
            )
        )


@pytest.mark.parametrize(
    ("source_hint", "expected_code"),
    [
        ("standard", "STANDARD_FULL_PAGE_OCR_REQUIRED"),
        ("drawing", "DRAWING_FULL_PAGE_OCR_REQUIRED"),
    ],
)
def test_handle_upload_rejects_failed_full_page_ocr_proof(
    monkeypatch,
    tmp_path: Path,
    source_hint: str,
    expected_code: str,
) -> None:
    _isolate_workspace(monkeypatch, tmp_path)

    async def _parse(ext: str, _path: Path, _total_bytes: int) -> dict[str, Any]:
        assert ext == "pdf"
        return {
            "doc_type": "pdf",
            "pages": 2,
            "text_bytes": 1,
            "extract_text": "\f",
        }

    async def _ocr(*_args: Any, **_kwargs: Any) -> OcrResult:
        return OcrResult(
            text="\f第二页",
            pages=2,
            lang="chi_sim+eng",
            error="page_ocr_incomplete",
            page_texts=("", "第二页"),
            page_statuses=("failed", "text"),
            page_image_sha256=(
                "",
                hashlib.sha256(b"second-page").hexdigest(),
            ),
            source_pages=2,
        )

    monkeypatch.setattr(ingest_router, "_extract_text_path_bounded", _parse)
    monkeypatch.setattr(ingest_router, "_try_ocr", _ocr)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            ingest_router._handle_upload(
                [_Upload(b"failed-full-page-pdf", "source.pdf")],
                source_hint=source_hint,
            )
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "ALL_FILES_REJECTED"
    rejected = exc_info.value.detail["rejected"][0]
    assert rejected["code"] == expected_code
    receipt = rejected["ocr_failure_receipt"]
    assert receipt["schema_version"] == ingest_router.OCR_FAILURE_RECEIPT_VERSION
    assert receipt["code"] == expected_code
    assert receipt["source_sha256"] == hashlib.sha256(
        b"failed-full-page-pdf"
    ).hexdigest()
    assert receipt["ocr_policy"] == ingest_router._ocr_cache_policy(source_hint)
    assert receipt["diagnostics"] == {
        "schema_version": "ocr-diagnostics-v1",
        "machine_code": "OCR_PAGE_PROOF_INCOMPLETE",
        "error_code": "page_ocr_incomplete",
        "engine": "tesseract",
        "lang": "chi_sim+eng",
        "declared_pages": 2,
        "source_pages": 2,
        "attempted_pages": 2,
        "status_counts": {"failed": 1, "text": 1},
        "unreadable_pages": [],
        "failed_pages": [1],
        "timeout_pages": [],
        "graphics_only_pages": [],
        "recovered_pages": [],
    }
    assert len(receipt["receipt_digest"]) == 64
    assert "第二页" not in json.dumps(receipt, ensure_ascii=False)
    assert not ingest_router._parse_cache_path(
        receipt["source_sha256"],
        source_hint,
    ).exists()


def test_parse_cache_keeps_small_extracted_text_inline(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ingest_router, "PARSE_CACHE_DIR", tmp_path / "cache")
    digest = hashlib.sha256(b"small-source").hexdigest()
    parsed = {
        "base": {"doc_type": "txt", "extract_text": "短正文"},
        "parsed_type": None,
        "parsed_meta": None,
    }

    ingest_router._save_parse_cache(digest, parsed)

    metadata = ingest_router._parse_cache_path(digest).read_text(encoding="utf-8")
    assert "短正文" in metadata
    assert not ingest_router._parse_cache_text_path(digest).exists()
    assert ingest_router._load_parse_cache(digest) == parsed


def test_pdf_preview_reuses_content_addressed_thumbnail(monkeypatch, tmp_path: Path) -> None:
    workspace = _isolate_workspace(monkeypatch, tmp_path)
    content = b"cached-pdf-content"
    digest = hashlib.sha256(content).hexdigest()
    preview = workspace / "previews" / f"{digest}_preview.png"
    preview.parent.mkdir(parents=True, exist_ok=True)
    preview.write_bytes(b"existing-preview")
    monkeypatch.setattr(
        ingest_router,
        "_load_parse_cache",
        lambda _digest, **_kwargs: {
            "base": {"doc_type": "pdf", "pages": 1, "extract_text": "有效正文"},
            "parsed_type": None,
            "parsed_meta": None,
        },
    )

    async def _must_not_render(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("cached preview must not invoke PDFium")

    monkeypatch.setattr(ingest_router, "_run_isolated_process", _must_not_render)
    result = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(content, "招标文件.pdf")],
            source_hint="tender_qa",
        )
    )

    saved = result["saved"][0]
    assert saved["preview_saved_as"] == str(preview)
    assert saved["preview_cache_hit"] is True
    assert saved["preview_sha256"] == hashlib.sha256(
        b"existing-preview"
    ).hexdigest()
    assert result["warnings"] == []


def test_pdf_preview_worker_crash_is_a_stable_warning(monkeypatch, tmp_path: Path) -> None:
    _isolate_workspace(monkeypatch, tmp_path)
    monkeypatch.setattr(
        ingest_router,
        "_load_parse_cache",
        lambda _digest, **_kwargs: {
            "base": {"doc_type": "pdf", "pages": 1, "extract_text": "有效正文"},
            "parsed_type": None,
            "parsed_meta": None,
        },
    )

    async def _crash(*_args: Any, **_kwargs: Any) -> Any:
        raise BrokenProcessPool("native preview worker exited")

    monkeypatch.setattr(ingest_router, "_run_isolated_process", _crash)
    result = asyncio.run(
        ingest_router._handle_upload(
            [_Upload(b"uncached-pdf-content", "招标文件.pdf")],
            source_hint="tender_qa",
        )
    )

    assert len(result["saved"]) == 1
    assert result["saved"][0]["preview_saved_as"] is None
    assert result["warnings"][0]["code"] == "PDF_PREVIEW_WORKER_CRASHED"
    assert "正文解析结果已保留" in result["warnings"][0]["message"]


def test_legacy_doc_fails_closed_without_converter(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "supplement.doc"
    source.write_bytes(b"legacy-doc")
    monkeypatch.setattr(ingest_router.shutil, "which", lambda _name: None)

    with pytest.raises(RuntimeError, match="LEGACY_DOC_CONVERTER_UNAVAILABLE"):
        ingest_router._extract_text_path("doc", source)


def test_create_ingest_job_spools_and_dispatches(monkeypatch, tmp_path: Path) -> None:
    job_id = "a" * 32
    dispatched: dict[str, Any] = {}
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")
    monkeypatch.setattr(ingest_router, "create_job", lambda payload: job_id)

    def _submit(current_job_id: str, callback: Any, *args: Any, **kwargs: Any) -> int:
        dispatched.update({"job_id": current_job_id, "callback": callback, "args": args})
        return 1

    monkeypatch.setattr(ingest_router, "submit_local_job", _submit)
    response = asyncio.run(
        ingest_router.create_ingest_job(
            [_Upload(b"one", "一.txt"), _Upload(b"two", "二.txt")],
            project_id="p1",
            source_hint="drawing_standard",
        )
    )

    assert response["job_id"] == job_id
    assert response["files_total"] == 2
    assert len(response["file_ids"]) == 2
    assert dispatched["job_id"] == job_id
    assert dispatched["callback"] is ingest_router._run_ingest_job
    assert len(list((tmp_path / "spool" / job_id).iterdir())) == 2


def test_ingest_worker_persists_file_level_status_elapsed_pages_and_cache(monkeypatch, tmp_path: Path) -> None:
    updates: list[dict[str, Any]] = []

    def _merge(_job_id: str, **fields: Any) -> dict[str, Any]:
        updates.append(fields)
        return fields

    def _process(
        _job_id: str,
        index: int,
        _total: int,
        entry: dict[str, Any],
        _options: dict[str, Any],
        _attempt_id: str,
        _owner_instance_id: str,
    ) -> dict[str, Any]:
        elapsed = round(index / 100, 3)
        return {
            "index": index,
            "filename": entry["filename"],
            "elapsed_seconds": elapsed,
            "accepted": [
                {
                    "filename": entry["filename"],
                    "file_id": entry["file_id"],
                    "pages": index,
                    "elapsed_seconds": elapsed,
                }
            ],
            "rejected": [],
            "warnings": [],
            "cache_hits": 1 if index == 2 else 0,
        }

    monkeypatch.setattr(
        ingest_router,
        "acquire_job_lease",
        lambda _job_id: {
            "attempt_id": "a" * 32,
            "owner_instance_id": "test-worker",
        },
    )
    monkeypatch.setattr(ingest_router, "job_lease_active", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        ingest_router,
        "run_with_job_lease",
        lambda _job_id, *, callback, callback_args=(), callback_kwargs=None, **_kwargs: callback(
            *callback_args,
            **dict(callback_kwargs or {}),
        ),
    )
    monkeypatch.setattr(ingest_router, "merge_job", _merge)
    monkeypatch.setattr(
        ingest_router,
        "transition_job",
        lambda _job_id, **fields: _merge(_job_id, **fields),
    )
    monkeypatch.setattr(ingest_router, "append_runtime_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ingest_router, "get_job", lambda _job_id: {"status": "running"})
    monkeypatch.setattr(ingest_router, "_process_spooled_entry", _process)
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")
    entries = [
        {
            "filename": f"file-{index}.txt",
            "path": str(tmp_path / f"file-{index}.txt"),
            "bytes": 10,
            "sha256": str(index) * 64,
            "file_id": str(index) * 64,
        }
        for index in range(1, 4)
    ]

    ingest_router._run_ingest_job("b" * 32, entries, {}, [])

    file_updates = [
        item["progress"]["files"]
        for item in updates
        if isinstance(item.get("progress"), dict)
        and isinstance(item["progress"].get("files"), dict)
    ]
    final_files = file_updates[-1]
    assert final_files["completed"] == 3
    assert final_files["accepted"] == 3
    assert [item["status"] for item in final_files["items"]] == ["accepted"] * 3
    assert [item["pages"] for item in final_files["items"]] == [1, 2, 3]
    assert final_files["items"][1]["cache_hit"] is True
    assert all(float(item["elapsed_seconds"]) > 0 for item in final_files["items"])
    terminal = next(item for item in reversed(updates) if item.get("status") == "succeeded")
    assert all("elapsed_seconds" in row for row in terminal["result"]["accepted"])


def test_ingest_worker_heartbeats_while_file_is_still_processing(monkeypatch, tmp_path: Path) -> None:
    heartbeats: list[dict[str, Any]] = []
    real_wait = ingest_router.concurrent.futures.wait
    wait_calls = 0

    def _wait(
        futures: Any,
        *,
        timeout: float | None = None,
        return_when: str,
    ) -> tuple[set[Any], set[Any]]:
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 1:
            assert timeout == ingest_router.INGEST_HEARTBEAT_SECONDS
            return set(), set(futures)
        return real_wait(futures, timeout=timeout, return_when=return_when)

    def _process(
        _job_id: str,
        index: int,
        _total: int,
        entry: dict[str, Any],
        _options: dict[str, Any],
        _attempt_id: str,
        _owner_instance_id: str,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "filename": entry["filename"],
            "elapsed_seconds": 0.1,
            "accepted": [{"filename": entry["filename"], "file_id": entry["file_id"]}],
            "rejected": [],
            "warnings": [],
            "cache_hits": 0,
        }

    monkeypatch.setattr(ingest_router.concurrent.futures, "wait", _wait)
    monkeypatch.setattr(
        ingest_router,
        "acquire_job_lease",
        lambda _job_id: {
            "attempt_id": "a" * 32,
            "owner_instance_id": "test-worker",
        },
    )
    monkeypatch.setattr(ingest_router, "job_lease_active", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        ingest_router,
        "run_with_job_lease",
        lambda _job_id, *, callback, callback_args=(), callback_kwargs=None, **_kwargs: callback(
            *callback_args,
            **dict(callback_kwargs or {}),
        ),
    )
    monkeypatch.setattr(ingest_router, "merge_job", lambda _job_id, **fields: fields)
    monkeypatch.setattr(ingest_router, "transition_job", lambda _job_id, **fields: fields)
    monkeypatch.setattr(
        ingest_router,
        "heartbeat_job",
        lambda _job_id, **fields: (
            heartbeats.append(fields) or {"status": "running"}
        ),
    )
    monkeypatch.setattr(ingest_router, "append_runtime_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(ingest_router, "get_job", lambda _job_id: {"status": "running"})
    monkeypatch.setattr(ingest_router, "_process_spooled_entry", _process)
    monkeypatch.setattr(ingest_router, "INGEST_SPOOL_DIR", tmp_path / "spool")
    entries = [
        {
            "filename": "large.pdf",
            "path": str(tmp_path / "large.pdf"),
            "bytes": 10,
            "sha256": "a" * 64,
            "file_id": "a" * 64,
        }
    ]

    ingest_router._run_ingest_job("c" * 32, entries, {}, [])

    assert len(heartbeats) == 1
    assert heartbeats[0]["activity"] == "1 个文件正在解析"
    assert heartbeats[0]["progress_updates"]["current_file"] == ["large.pdf"]
    assert heartbeats[0]["progress_updates"]["work_state"] == "processing_file"
