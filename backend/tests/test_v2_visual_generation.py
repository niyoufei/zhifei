from __future__ import annotations

from pathlib import Path

from backend.zhifei_autoplan.v2.visual_generation import generate_document_visual_assets


def test_generate_document_visual_assets_with_fallback(tmp_path: Path) -> None:
    index_matrix = {
        "project_name": "模块6测试项目",
        "index_matrix": [
            {"dimension": "质量", "keywords": ["质量", "验收"]},
            {"dimension": "安全", "keywords": ["安全", "防护"]},
            {"dimension": "进度", "keywords": ["工期", "关键线路"]},
            {"dimension": "环保", "keywords": ["PM10", "噪声"]},
            {"dimension": "重难点", "keywords": ["关键工序"]},
            {"dimension": "扣分点", "keywords": ["评分项"]},
        ],
    }
    result = generate_document_visual_assets(
        index_matrix=index_matrix,
        sections=[],
        output_dir=tmp_path / "visuals",
        provider="google",
        model="imagen-3.0-generate-002",
        api_key=None,
    )

    assert result["ok"] is True
    assert result["count"] == 4
    assets = result["assets"]
    assert len(assets) == 4
    for asset in assets:
        path = Path(asset["image_path"])
        assert path.exists()
        assert path.suffix.lower() == ".png"
