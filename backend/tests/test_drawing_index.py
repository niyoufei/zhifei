from __future__ import annotations

import json
from pathlib import Path

from backend.zhifei_autoplan import evidence
from backend.zhifei_autoplan.drawing_index import build_drawing_index


def _write_audit(tmp_path: Path, rows: list[dict]) -> None:
    audit_path = tmp_path / "backend/data/audit/ingest.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    evidence._load_audit_records.cache_clear()
    evidence._load_extract_text.cache_clear()


def _record(
    tmp_path: Path,
    *,
    filename: str,
    sha: str,
    text: str,
    **extra,
) -> dict:
    extract = tmp_path / f"{sha[:12]}.txt"
    extract.write_text(text, encoding="utf-8")
    return {
        "project_id": "p1",
        "filename": filename,
        "sha256": sha,
        "tags": [],
        "source_hint": "drawing_standard",
        "extract_saved_as": str(extract),
        **extra,
    }


def test_drawing_index_deduplicates_same_content_and_keeps_distinct_revisions(
    monkeypatch, tmp_path: Path
) -> None:
    same_sha = "a" * 64
    _write_audit(
        tmp_path,
        [
            _record(tmp_path, filename="1 挤奶厅.pdf", sha=same_sha, text="旧记录"),
            _record(tmp_path, filename="1 挤奶厅.pdf", sha=same_sha, text="新记录"),
            _record(tmp_path, filename="1 挤奶厅.pdf", sha="b" * 64, text="修订版"),
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", [], project_id="p1")

    assert len(result["drawings"]) == 2
    assert {row["sha256"] for row in result["drawings"]} == {same_sha, "b" * 64}


def test_latest_disabled_record_prevents_older_content_from_resurrecting(
    monkeypatch, tmp_path: Path
) -> None:
    sha = "c" * 64
    _write_audit(
        tmp_path,
        [
            _record(tmp_path, filename="2 地磅.pdf", sha=sha, text="旧记录"),
            _record(
                tmp_path,
                filename="2 地磅.pdf",
                sha=sha,
                text="新记录",
                enabled=False,
            ),
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index("示例项目", [], project_id="p1")

    assert result["drawings"] == []


def test_topic_only_hit_does_not_create_claim_grade_chapter_binding(
    monkeypatch, tmp_path: Path
) -> None:
    _write_audit(
        tmp_path,
        [
            _record(
                tmp_path,
                filename="3 围墙.pdf",
                sha="d" * 64,
                text="示例项目总图资料，不含章节特异内容。",
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p1",
    )

    assert len(result["drawings"]) == 1
    assert result["chapter_bindings"] == []
    assert result["chapter_binding_status"] == "no_chapter_specific_evidence"


def test_chapter_specific_extract_binding_preserves_drawing_identity(
    monkeypatch, tmp_path: Path
) -> None:
    sha = "e" * 64
    _write_audit(
        tmp_path,
        [
            _record(
                tmp_path,
                filename="钢筋详图.pdf",
                sha=sha,
                text="钢筋绑扎施工工艺：构件位置与节点做法。",
            )
        ],
    )
    monkeypatch.chdir(tmp_path)

    result = build_drawing_index(
        "示例项目",
        ["钢筋绑扎施工工艺"],
        project_id="p1",
    )

    binding = result["chapter_bindings"][0]
    assert binding["filename"] == "钢筋详图.pdf"
    assert binding["sha256"] == sha
    assert f"_{sha[:8]}@" in binding["locator"] or f"#{sha[:8]}@" in binding["locator"]
    assert binding["binding_basis"] == "chapter_specific_extract_hit"
