from __future__ import annotations

from backend.zhifei_autoplan.project_types import (
    detect_project_type,
    normalize_project_type,
    ordered_project_types,
    project_type_requirements,
)


def test_ordered_project_types_contains_retrofit_type() -> None:
    types = ordered_project_types()
    assert "房建" in types
    assert "维修改造" in types


def test_normalize_project_type_supports_legacy_building_alias() -> None:
    assert normalize_project_type("建房") == "房建"
    assert normalize_project_type("房屋建筑工程") == "房建"


def test_detect_project_type_can_match_retrofit_keywords() -> None:
    assert detect_project_type(topic="办公楼维修改造施工组织设计") == "维修改造"


def test_project_type_requirements_returns_retrofit_rules() -> None:
    reqs = project_type_requirements("维修改造")
    assert any("拆除保护" in item for item in reqs)
