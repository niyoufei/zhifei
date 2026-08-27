from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.zhifei_autoplan.project_parameter_evidence import (
    build_project_parameter_evidence,
    validate_project_parameter_evidence,
)


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _record(
    *,
    filename: str,
    sha256: str,
    extract_path: Path,
    project_id: str,
    pages: int,
    source_hint: str,
    tags: list[str] | None = None,
) -> dict:
    workspace = (
        extract_path.parent.parent
        if extract_path.parent.name in {"extracts", "staging"}
        else extract_path.parent
    )
    uploads = workspace / "uploads"
    extracts = workspace / "extracts"
    uploads.mkdir(parents=True, exist_ok=True)
    extracts.mkdir(parents=True, exist_ok=True)
    source_bytes = f"source:{sha256}:{filename}".encode()
    digest = hashlib.sha256(source_bytes).hexdigest()
    source_path = uploads / f"{digest}_{filename}"
    source_path.write_bytes(source_bytes)
    extract_bytes = extract_path.read_bytes()
    extract_text_sha256 = hashlib.sha256(extract_bytes).hexdigest()
    trusted_extract = extracts / f"{digest}_{extract_text_sha256}.txt"
    trusted_extract.write_bytes(extract_bytes)
    return {
        "filename": filename,
        "sha256": digest,
        "file_id": digest,
        "workspace_dir": str(workspace),
        "saved_as": str(source_path),
        "extract_saved_as": str(trusted_extract),
        "extract_text_sha256": extract_text_sha256,
        "project_id": project_id,
        "pages": pages,
        "source_hint": source_hint,
        "tags": tags or [],
        "usable": True,
        "enabled": True,
    }


def _write_audit(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_builds_six_process_bound_quality_items_with_reversible_locators(
    tmp_path: Path,
) -> None:
    extracts = tmp_path / "extracts"
    extracts.mkdir()
    wall_sha = _sha("wall")
    vehicle_sha = _sha("vehicle")
    answer_sha = _sha("answer")
    wall = extracts / "wall.txt"
    vehicle = extracts / "vehicle.txt"
    answer = extracts / "answer.txt"
    wall.write_text(
        "基础开挖至标高后，对下部土层进行压实处理，压实系数不小于0.97。",
        encoding="utf-8",
    )
    vehicle.write_text(
        "车辆消毒池需采用防水混凝土，其强度等级不应低于C25，"
        "试配混凝土的抗渗等级应比设计要求提高0. 2Mpa。",
        encoding="utf-8",
    )
    answer.write_text(
        "问题：基础和垫层强度？回复：基础 C30  垫层C20"
        "\f"
        "34、地面涂膜防水厚度按照多少计入？回复：1.8mm 厚",
        encoding="utf-8",
    )
    audit = tmp_path / "audit" / "ingest.jsonl"
    rows = [
        _record(
            filename="3 围墙.pdf",
            sha256=wall_sha,
            extract_path=wall,
            project_id="P1",
            pages=1,
            source_hint="drawing_standard",
        ),
        _record(
            filename="6 车辆消毒池.pdf",
            sha256=vehicle_sha,
            extract_path=vehicle,
            project_id="P1",
            pages=1,
            source_hint="drawing_standard",
        ),
        # This historical row has the wrong project id.  It is admitted only
        # because the current tender matrix carries its exact full SHA.
        _record(
            filename="答疑.pdf",
            sha256=answer_sha,
            extract_path=answer,
            project_id="legacy-wrong-scope",
            pages=2,
            source_hint="tender_qa",
            tags=["tender", "qa"],
        ),
    ]
    _write_audit(audit, rows)
    answer_record = rows[-1]
    tender = {
        "items": [
            {
                "source_spans": [
                    {
                        "file_name": "答疑.pdf",
                        "document_sha256": answer_record["sha256"],
                        "source_sha256": answer_record["sha256"],
                    }
                ]
            }
        ]
    }

    result = build_project_parameter_evidence(
        project_id="P1",
        tender=tender,
        audit_path=audit,
    )

    assert result["ready"] is True
    assert result["status"] == "PASS_PROJECT_PARAMETER_EVIDENCE"
    assert result["matched_item_count"] == 6
    assert result["required_item_count"] == 6
    assert result["coverage_complete"] is True
    assert validate_project_parameter_evidence(result)["ok"] is True
    fact = result["quality_threshold"]
    assert fact["status"] == "derived"
    assert len(fact["evidence"]["source_sha256"]) == 64
    items = {item["id"]: item for item in fact["value"]["items"]}
    assert items["wall-foundation-compaction"]["value"] == 0.97
    assert items["vehicle-pool-concrete-grade"]["value"] == "C25"
    assert items["vehicle-pool-impermeability-trial"]["value"] == 0.2
    assert items["foundation-concrete-grade"]["value"] == "C30"
    assert items["blinding-concrete-grade"]["value"] == "C20"
    assert items["floor-coating-waterproof-thickness"]["value"] == 1.8
    for item in items.values():
        assert f"#p{item['page']}_{item['document_sha256']}@" in item["locator"]
        assert len(item["page_text_sha256"]) == 64
        assert item["status"] == "verified"


def test_conflicting_process_metric_values_hold_without_selecting_a_fact(
    tmp_path: Path,
) -> None:
    first = tmp_path / "wall-a.txt"
    second = tmp_path / "wall-b.txt"
    first.write_text("压实系数不小于0.97。", encoding="utf-8")
    second.write_text("压实系数不小于0.95。", encoding="utf-8")
    audit = tmp_path / "audit" / "ingest.jsonl"
    _write_audit(
        audit,
        [
            _record(
                filename="围墙-A.pdf",
                sha256=_sha("wall-a"),
                extract_path=first,
                project_id="P1",
                pages=1,
                source_hint="drawing_standard",
            ),
            _record(
                filename="围墙-B.pdf",
                sha256=_sha("wall-b"),
                extract_path=second,
                project_id="P1",
                pages=1,
                source_hint="drawing_standard",
            ),
        ],
    )

    result = build_project_parameter_evidence(
        project_id="P1",
        tender={},
        audit_path=audit,
    )

    assert result["ready"] is False
    assert result["quality_threshold"] is None
    assert result["status"] == "HOLD_PROJECT_PARAMETER_EVIDENCE_CONFLICT"
    assert [row["id"] for row in result["conflicts"]] == [
        "wall-foundation-compaction"
    ]


def test_rejects_cross_project_and_unreliable_page_mapping(tmp_path: Path) -> None:
    leaked = tmp_path / "leaked.txt"
    broken = tmp_path / "broken.txt"
    leaked.write_text("压实系数不小于0.97。", encoding="utf-8")
    broken.write_text("压实系数不小于0.96。", encoding="utf-8")
    audit = tmp_path / "audit" / "ingest.jsonl"
    _write_audit(
        audit,
        [
            _record(
                filename="围墙-其他项目.pdf",
                sha256=_sha("leaked"),
                extract_path=leaked,
                project_id="P2",
                pages=1,
                source_hint="drawing_standard",
            ),
            _record(
                filename="围墙-页数错误.pdf",
                sha256=_sha("broken"),
                extract_path=broken,
                project_id="P1",
                pages=2,
                source_hint="drawing_standard",
            ),
        ],
    )

    result = build_project_parameter_evidence(
        project_id="P1",
        tender={},
        audit_path=audit,
    )

    assert result["ready"] is False
    assert result["matched_item_count"] == 0
    assert result["source_count"] == 0
    assert result["status"] == "HOLD_PROJECT_PARAMETER_EVIDENCE_MISSING"


def test_rejects_forged_audit_identity_external_extract_and_short_tender_hint(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external.txt"
    external.write_text(
        "问题：基础和垫层强度？回复：基础 C30 垫层C20。"
        "地面涂膜防水厚度按照多少计入？回复：1.8mm厚。",
        encoding="utf-8",
    )
    audit = tmp_path / "workspace" / "audit" / "ingest.jsonl"
    forged = {
        "filename": "答疑.pdf",
        "sha256": "a" * 64,
        "file_id": "b" * 64,
        "workspace_dir": str(tmp_path / "workspace"),
        "saved_as": str(tmp_path / "missing.pdf"),
        "extract_saved_as": str(external),
        "extract_text_sha256": hashlib.sha256(external.read_bytes()).hexdigest(),
        "project_id": "OTHER",
        "pages": 1,
        "source_hint": "tender_qa",
        "tags": ["tender", "qa"],
        "usable": True,
        "enabled": True,
    }
    _write_audit(audit, [forged])

    result = build_project_parameter_evidence(
        project_id="P1",
        tender={
            "items": [
                {
                    "source_spans": [
                        {"file_name": "aaaaaaaa_答疑.pdf"}
                    ]
                }
            ]
        },
        audit_path=audit,
    )

    assert result["ready"] is False
    assert result["source_count"] == 0
    assert result["matched_item_count"] == 0


def test_partial_known_source_group_holds_on_missing_required_items(
    tmp_path: Path,
) -> None:
    extracts = tmp_path / "workspace" / "staging"
    extracts.mkdir(parents=True)
    answer = extracts / "answer.txt"
    answer.write_text(
        "问题：基础和垫层强度？回复：基础 C30 垫层C20",
        encoding="utf-8",
    )
    record = _record(
        filename="答疑.pdf",
        sha256=_sha("partial-answer"),
        extract_path=answer,
        project_id="P1",
        pages=1,
        source_hint="tender_qa",
        tags=["tender", "qa"],
    )
    audit = tmp_path / "workspace" / "audit" / "ingest.jsonl"
    _write_audit(audit, [record])

    result = build_project_parameter_evidence(
        project_id="P1",
        tender={},
        audit_path=audit,
    )

    assert result["ready"] is False
    assert result["status"] == (
        "HOLD_PROJECT_PARAMETER_EVIDENCE_COVERAGE_INCOMPLETE"
    )
    assert result["matched_item_count"] == 2
    assert result["missing_required_item_ids"] == [
        "floor-coating-waterproof-thickness"
    ]
    validation = validate_project_parameter_evidence(result)
    assert validation["ok"] is False
    assert "status_not_pass" in validation["errors"]
