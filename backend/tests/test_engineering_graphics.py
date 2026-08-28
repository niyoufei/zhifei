from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from backend.zhifei_autoplan.engineering_graphics import (
    CANVAS_HEIGHT_CM,
    CANVAS_HEIGHT_PX,
    CANVAS_WIDTH_CM,
    CANVAS_WIDTH_PX,
    DEFAULT_DPI,
    GraphicEdge,
    GraphicNode,
    GraphicSpec,
    choose_layout,
    render_engineering_graphic,
)
from backend.zhifei_autoplan.media_quality import validate_image_bytes, validate_media_item


@pytest.mark.parametrize(
    ("count", "requested", "expected"),
    [
        (1, "auto", (1,)),
        (2, "auto", (2,)),
        (4, "auto", (4,)),
        (8, "auto", (4, 4)),
        (12, "two_row", (6, 6)),
        (8, "tree", (1, 4, 3)),
        (8, "three_row", (3, 3, 2)),
        (12, "matrix3", (4, 4, 4)),
    ],
)
def test_layout_policy_is_deterministic(count: int, requested: str, expected: tuple[int, ...]) -> None:
    assert choose_layout(count, requested) == expected


@pytest.mark.parametrize("node_count", [1, 2, 4, 8, 12])
def test_engineering_graphic_meets_print_and_layout_contract(tmp_path: Path, node_count: int) -> None:
    nodes = tuple(
        GraphicNode(
            node_id=f"N{index + 1}",
            title=f"第{index + 1}阶段超长中文施工控制节点与风险闭环",
            detail="测量复核、工序检查、见证取样、验收签认及资料归档全过程可追溯",
        )
        for index in range(node_count)
    )
    spec = GraphicSpec(
        title="市政道路工程施工组织与质量验收路径",
        subtitle="合成验收样本 · 非真实项目",
        nodes=nodes,
        edges=tuple(
            GraphicEdge(source=nodes[index].node_id, target=nodes[index + 1].node_id)
            for index in range(max(0, node_count - 1))
        ),
        layout="two_row" if node_count > 4 else "auto",
        caption="所有数据仅用于自动化验收，不代表真实项目事实",
    )
    png_path = tmp_path / f"graphic-{node_count}.png"
    svg_path = tmp_path / f"graphic-{node_count}.svg"

    receipt = render_engineering_graphic(spec, png_path=png_path, svg_path=svg_path)

    assert receipt["status"] == "pass"
    assert receipt["canvas_cm"] == [CANVAS_WIDTH_CM, CANVAS_HEIGHT_CM]
    assert receipt["pixel_size"] == [CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX]
    assert receipt["dpi"] == DEFAULT_DPI
    assert receipt["node_count"] == node_count
    assert receipt["overlaps"] == []
    assert receipt["overflows"] == []
    with Image.open(png_path) as image:
        assert image.size == (3071, 1854)
        assert image.info["dpi"][0] == pytest.approx(300, abs=1)
        assert image.info["dpi"][1] == pytest.approx(300, abs=1)
    decoded = validate_image_bytes(png_path.read_bytes())
    assert decoded["ok"] is True
    media_receipt = validate_media_item(png_path, insert_width_cm=CANVAS_WIDTH_CM)
    assert media_receipt["ok"] is True
    assert media_receipt["effective_dpi"] == pytest.approx(300, abs=0.2)
    svg = svg_path.read_text(encoding="utf-8")
    assert 'width="26.0cm"' in svg
    assert 'height="15.7cm"' in svg
    assert "市政道路工程施工组织与质量验收路径" in svg
    assert "合成验收样本" in svg
    assert "程序化中文文字层" not in svg
