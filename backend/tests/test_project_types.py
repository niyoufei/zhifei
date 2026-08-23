from __future__ import annotations

from backend.zhifei_autoplan.project_types import (
    detect_project_type,
    normalize_project_type,
    ordered_project_types,
    project_type_catalog_root,
)


def test_project_types_match_ai_knowledge_graph_directories() -> None:
    root = project_type_catalog_root()
    directory_names = sorted(path.name for path in root.iterdir() if path.is_dir() and not path.name.startswith("."))
    configured_names = ordered_project_types()

    assert len(configured_names) == 24
    assert len(set(configured_names)) == len(configured_names)
    assert sorted(configured_names) == directory_names
    assert sum(1 for path in root.rglob("*.md") if path.is_file()) == 130


def test_legacy_project_type_names_normalize_to_catalog_names() -> None:
    assert normalize_project_type("房建") == "房屋建筑"
    assert normalize_project_type("装修") == "装修改造"
    assert normalize_project_type("市政排水") == "市政管网与污水处理"
    assert normalize_project_type("河道治理") == "河道整治工程"


def test_project_type_detection_prefers_specific_catalog_type() -> None:
    assert detect_project_type(topic="医院门诊楼不停诊装修改造工程") == "医院装修改造"
    assert detect_project_type(topic="产业园生产厂房施工总承包") == "产业园厂房房建"
    assert detect_project_type(topic="高标准农田建设项目") == "高标准农田"
