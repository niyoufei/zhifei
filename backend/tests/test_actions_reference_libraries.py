from __future__ import annotations

import json
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile


def _write_audit(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(rec, ensure_ascii=False) for rec in records), encoding="utf-8")


@pytest.mark.asyncio
async def test_actions_case_library_upload_and_items_roundtrip(tmp_path: Path) -> None:
    from backend.app.routers.actions_bridge import actions_case_library_items, actions_case_library_upload

    file_obj = UploadFile(filename="房建案例A.txt", file=BytesIO("第一章 工程概况\n第二章 施工部署\n".encode("utf-8")))

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        uploaded = await actions_case_library_upload(
            files=[file_obj],
            project_type="房建",
            title="房建案例A",
            tags="医院,结构",
            chapter_scope="工程概况,施工部署",
            summary="结构清晰",
            style_profile="短句表达",
            workspace_dir=str(tmp_path / "workspace"),
            x_actions_key="test-actions-key",
        )
        listed = await actions_case_library_items(
            project_type="房建",
            workspace_dir=str(tmp_path / "workspace"),
            x_actions_key="test-actions-key",
        )

    assert uploaded["ok"] is True
    assert uploaded["items"][0]["case_id"]
    assert uploaded["items"][0]["project_type"] == "房建"
    assert uploaded["items"][0]["tags"] == ["医院", "结构"]
    assert uploaded["items"][0]["chapter_scope"] == ["工程概况", "施工部署"]
    assert listed["ok"] is True
    assert listed["items"][0]["case_id"] == uploaded["items"][0]["case_id"]
    assert listed["items"][0]["summary"] == "结构清晰"
    assert listed["items"][0]["style_profile"] == "短句表达"


@pytest.mark.asyncio
async def test_actions_case_library_upload_rejects_invalid_project_type(tmp_path: Path) -> None:
    from backend.app.routers.actions_bridge import actions_case_library_upload

    file_obj = UploadFile(filename="无效案例.txt", file=BytesIO("案例内容".encode("utf-8")))

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        with pytest.raises(HTTPException) as exc:
            await actions_case_library_upload(
                files=[file_obj],
                project_type="不存在的类型",
                title="无效案例",
                workspace_dir=str(tmp_path / "workspace"),
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 400
    assert exc.value.detail == "case library upload requires valid project_type"


def test_build_case_reference_pack_no_match_warns(tmp_path: Path) -> None:
    from backend.zhifei_autoplan.case_library_service import build_case_reference_pack

    audit_path = tmp_path / "ingest.jsonl"
    _write_audit(audit_path, [])

    pack = build_case_reference_pack(
        options={"enabled": True, "top_k": 2},
        topic="医院改造",
        chapter_title="工程概况",
        project_type="房建",
        audit_path=audit_path,
    )

    assert pack["enabled"] is True
    assert pack["hits"] == []
    assert "no_case_match" in pack["warning_list"]


def test_build_case_reference_pack_with_selected_case_ids(tmp_path: Path) -> None:
    from backend.zhifei_autoplan.case_library_service import build_case_reference_pack, case_library_record_id

    audit_path = tmp_path / "ingest.jsonl"
    extract_path = tmp_path / "case.txt"
    extract_path.write_text("第一章 工程概况\n第二章 施工部署\n", encoding="utf-8")
    record = {
        "ts": "2026-04-12T10:00:00Z",
        "filename": "房建案例A.docx",
        "project_type": "房建",
        "library_scope": "case_library",
        "extract_saved_as": str(extract_path),
        "saved_as": str(tmp_path / "房建案例A.docx"),
        "library_title": "房建案例A",
        "library_tags": ["医院"],
        "chapter_scope": ["工程概况"],
        "library_summary": "结构清晰",
        "library_style_profile": "短句表达",
        "sha256": "a" * 64,
    }
    _write_audit(audit_path, [record])

    pack = build_case_reference_pack(
        options={"enabled": True, "selected_case_ids": [case_library_record_id(record)]},
        topic="医院改造",
        chapter_title="工程概况",
        project_type="房建",
        audit_path=audit_path,
    )

    assert pack["selected_case_ids"] == [case_library_record_id(record)]
    assert pack["match_reason"] == "selected_case_ids"
    assert pack["style_hints"]


@pytest.mark.asyncio
async def test_actions_image_library_upload_and_items_roundtrip(tmp_path: Path) -> None:
    from backend.app.routers.actions_bridge import actions_image_library_items, actions_image_library_upload

    file_obj = UploadFile(filename="现场平面.png", file=BytesIO(b"fake-png-binary"))

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        uploaded = await actions_image_library_upload(
            files=[file_obj],
            project_type="房建",
            title="现场平面",
            tags="平面,临建",
            chapter_scope="施工总平面",
            process_scope="临建布置",
            caption="现场平面示意",
            description="用于施工总平面章节",
            workspace_dir=str(tmp_path / "workspace"),
            x_actions_key="test-actions-key",
        )
        listed = await actions_image_library_items(
            project_type="房建",
            workspace_dir=str(tmp_path / "workspace"),
            x_actions_key="test-actions-key",
        )

    assert uploaded["ok"] is True
    assert uploaded["items"][0]["image_id"]
    assert uploaded["items"][0]["project_type"] == "房建"
    assert uploaded["items"][0]["tags"] == ["平面", "临建"]
    assert listed["items"][0]["caption"] == "现场平面示意"


@pytest.mark.asyncio
async def test_actions_image_library_upload_rejects_invalid_project_type(tmp_path: Path) -> None:
    from backend.app.routers.actions_bridge import actions_image_library_upload

    file_obj = UploadFile(filename="现场平面.png", file=BytesIO(b"fake-png-binary"))

    with patch.dict(os.environ, {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False):
        with pytest.raises(HTTPException) as exc:
            await actions_image_library_upload(
                files=[file_obj],
                project_type="不存在的类型",
                title="现场平面",
                workspace_dir=str(tmp_path / "workspace"),
                x_actions_key="test-actions-key",
            )

    assert exc.value.status_code == 400
    assert exc.value.detail == "image library upload requires valid project_type"


def test_build_image_selection_pack_roundtrip(tmp_path: Path) -> None:
    from backend.zhifei_autoplan.image_library import (
        build_image_selection_pack,
        image_library_record_id,
        image_selection_pack_media_entries,
    )

    audit_path = tmp_path / "ingest.jsonl"
    image_path = tmp_path / "现场平面.png"
    image_path.write_bytes(b"fake")
    record = {
        "ts": "2026-04-12T11:00:00Z",
        "filename": "现场平面.png",
        "project_type": "房建",
        "library_scope": "image_library",
        "saved_as": str(image_path),
        "library_title": "现场平面",
        "library_tags": ["平面", "临建"],
        "chapter_scope": ["施工总平面"],
        "process_scope": ["临建布置"],
        "library_caption": "现场平面示意",
        "library_description": "用于施工总平面章节",
        "enabled": True,
        "usable": True,
        "sha256": "b" * 64,
    }
    _write_audit(audit_path, [record])

    pack = build_image_selection_pack(
        options={"enabled": True, "selected_image_ids": [image_library_record_id(record)]},
        topic="医院改造项目",
        chapter_title="施工总平面",
        project_type="房建",
        tags=["平面"],
        audit_path=audit_path,
    )

    assert pack["selected_image_ids"] == [image_library_record_id(record)]
    assert pack["match_reason"] == "selected_image_ids"
    assert pack["images"][0]["caption"] == "现场平面示意"
    assert image_selection_pack_media_entries(pack) == [
        {"path": str(image_path), "caption": "现场平面示意"}
    ]


def test_image_selection_pack_media_entries_skips_missing_paths_and_deduplicates() -> None:
    from backend.zhifei_autoplan.image_library import image_selection_pack_media_entries

    assert image_selection_pack_media_entries(
        {
            "caption_hint": "兜底图注",
            "images": [
                {"source_path": "/tmp/a.png", "caption": "现场平面示意"},
                {"storage_path": "/tmp/a.png", "caption": "重复路径"},
                {"storage_path": "/tmp/b.png", "title": "材料堆场"},
                {"caption": "缺少路径"},
            ],
        }
    ) == [
        {"path": "/tmp/a.png", "caption": "现场平面示意"},
        {"path": "/tmp/b.png", "caption": "材料堆场"},
    ]


def test_build_image_selection_pack_no_match_is_noop_warning(tmp_path: Path) -> None:
    from backend.zhifei_autoplan.image_library import build_image_selection_pack

    audit_path = tmp_path / "ingest.jsonl"
    _write_audit(audit_path, [])

    pack = build_image_selection_pack(
        options={"enabled": True},
        topic="医院改造项目",
        chapter_title="施工总平面",
        project_type="房建",
        tags=["平面"],
        audit_path=audit_path,
    )

    assert pack["enabled"] is True
    assert pack["images"] == []
    assert pack["warning_list"] == ["no_image_match"]
