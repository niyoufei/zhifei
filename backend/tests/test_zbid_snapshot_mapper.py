import copy

import pytest

from backend.zhifei_autoplan.zbid_snapshot_mapper import (
    FORBIDDEN_KEYS,
    map_zbid_snapshot_to_zdoc_draft_input,
)


def _valid_snapshot() -> dict:
    return {
        "snapshot_meta": {
            "snapshot_id": "snapshot-1",
            "source_system": "ZBid",
            "schema_version": "0.1",
            "snapshot_created_at": "2026-05-05T10:00:00+08:00",
            "requested_by": "reviewer@example.com",
        },
        "project": {
            "project_id": "project-1",
            "project_name": "技术标项目",
            "project_code": "BID-001",
            "owner_name": "建设单位",
            "bidder_name": "投标单位",
            "document_type": "technical_bid",
        },
        "lot": {
            "lot_id": "lot-1",
            "lot_name": "一标段",
            "scope_summary": "施工范围",
            "planned_duration_days": 180,
            "quality_target": "合格",
            "safety_target": "无重大事故",
        },
        "tender": {
            "scoring_items": [
                {
                    "item_id": "score-1",
                    "item_name": "施工组织",
                    "max_score": 10,
                    "requirement_text": "方案完整可行",
                    "evidence_needed": ["schedule"],
                }
            ]
        },
        "section_tasks": [
            {
                "section_id": "section-1",
                "title": "施工组织设计",
                "draft_intent": "生成只读草稿输入",
                "original_text": "原章节正文",
                "requirements": ["覆盖进度、资源和质量措施"],
                "target_length": "约1200字",
                "related_scoring_item_ids": ["score-1"],
                "related_material_ids": ["material-1", "material-sensitive", "material-disabled"],
            }
        ],
        "technical_materials": [
            {
                "material_id": "material-1",
                "material_type": "schedule",
                "title": "进度控制素材",
                "content_excerpt": "采用周计划和节点跟踪。",
                "source_ref": "material-ref-1",
                "source_version": "v1",
                "confidence": "reviewed",
                "usable_for_draft": True,
                "sensitive": False,
            },
            {
                "material_id": "material-sensitive",
                "content_excerpt": "敏感内容",
                "usable_for_draft": True,
                "sensitive": True,
            },
            {
                "material_id": "material-disabled",
                "content_excerpt": "不可用内容",
                "usable_for_draft": False,
                "sensitive": False,
            },
        ],
        "review_context": {
            "review_state": "pending_review",
            "review_note": "仅供草稿预览",
        },
        "version_hashes": {
            "snapshot_hash": "sha256:snapshot",
            "section_original_hash": "sha256:original",
            "prompt_input_hash": "sha256:prompt",
        },
        "safety_boundary": {
            "draft_only": True,
            "allow_formal_apply": False,
            "allow_export": False,
            "allow_job_write": False,
            "allow_result_bundle_write": False,
            "allow_ollama": False,
        },
    }


def _assert_no_forbidden_keys(value) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert str(key).lower() not in FORBIDDEN_KEYS
            _assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden_keys(child)


def test_valid_snapshot_maps_to_zdoc_draft_only_input() -> None:
    snapshot = _valid_snapshot()
    original = copy.deepcopy(snapshot)

    result = map_zbid_snapshot_to_zdoc_draft_input(snapshot)

    assert snapshot == original
    assert result["mode"] == "draft_only"
    assert result["source_system"] == "zbid"
    assert result["project_context"]["project_id"] == "project-1"
    assert result["project_context"]["lot_name"] == "一标段"
    assert result["review_context"] == snapshot["review_context"]
    assert result["version_hashes"] == snapshot["version_hashes"]
    assert result["safety_boundary"]["draft_only"] is True
    assert result["safety_boundary"]["allow_formal_apply"] is False
    assert result["safety_boundary"]["allow_export"] is False
    assert result["safety_boundary"]["allow_job_write"] is False
    assert result["safety_boundary"]["allow_result_bundle_write"] is False
    assert result["safety_boundary"]["allow_ollama"] is False

    section = result["section_input"][0]
    assert section["section_id"] == "section-1"
    assert section["title"] == "施工组织设计"
    assert section["draft_intent"] == "生成只读草稿输入"
    assert section["original"] == "原章节正文"
    assert section["original_hash"] == "sha256:original"
    assert section["scoring_context"][0]["item_id"] == "score-1"
    assert section["material_context"] == [
        {
            "material_id": "material-1",
            "material_type": "schedule",
            "title": "进度控制素材",
            "content_excerpt": "采用周计划和节点跟踪。",
            "source_ref": "material-ref-1",
            "source_version": "v1",
            "confidence": "reviewed",
        }
    ]


@pytest.mark.parametrize(
    "field",
    [
        "snapshot_meta",
        "project",
        "tender",
        "section_tasks",
        "version_hashes",
        "safety_boundary",
    ],
)
def test_missing_required_top_level_field_raises(field: str) -> None:
    snapshot = _valid_snapshot()
    snapshot.pop(field)

    with pytest.raises(ValueError, match=f"missing required top-level field: {field}"):
        map_zbid_snapshot_to_zdoc_draft_input(snapshot)


def test_empty_section_tasks_raises() -> None:
    snapshot = _valid_snapshot()
    snapshot["section_tasks"] = []

    with pytest.raises(ValueError, match="section_tasks must be a non-empty list"):
        map_zbid_snapshot_to_zdoc_draft_input(snapshot)


@pytest.mark.parametrize("field", ["section_id", "title", "draft_intent"])
def test_section_task_missing_required_field_raises(field: str) -> None:
    snapshot = _valid_snapshot()
    snapshot["section_tasks"][0].pop(field)

    with pytest.raises(ValueError, match=f"section task missing required field: {field}"):
        map_zbid_snapshot_to_zdoc_draft_input(snapshot)


@pytest.mark.parametrize(
    ("field", "bad_value", "expected"),
    [
        ("draft_only", False, True),
        ("allow_formal_apply", True, False),
        ("allow_export", True, False),
        ("allow_job_write", True, False),
        ("allow_result_bundle_write", True, False),
        ("allow_ollama", True, False),
    ],
)
def test_safety_boundary_must_remain_draft_only(field: str, bad_value: bool, expected: bool) -> None:
    snapshot = _valid_snapshot()
    snapshot["safety_boundary"][field] = bad_value

    with pytest.raises(ValueError, match=f"safety_boundary.{field} must be {expected}"):
        map_zbid_snapshot_to_zdoc_draft_input(snapshot)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_KEYS))
def test_forbidden_field_at_top_level_raises(field: str) -> None:
    snapshot = _valid_snapshot()
    snapshot[field] = True

    with pytest.raises(ValueError, match="forbidden field"):
        map_zbid_snapshot_to_zdoc_draft_input(snapshot)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_KEYS))
def test_forbidden_field_nested_raises(field: str) -> None:
    snapshot = _valid_snapshot()
    snapshot["project"]["nested"] = {field: True}

    with pytest.raises(ValueError, match="forbidden field"):
        map_zbid_snapshot_to_zdoc_draft_input(snapshot)


def test_output_does_not_contain_forbidden_keys() -> None:
    result = map_zbid_snapshot_to_zdoc_draft_input(_valid_snapshot())

    _assert_no_forbidden_keys(result)
