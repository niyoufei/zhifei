from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "standard_ingestion_pipeline.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("standard_ingestion_pipeline_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ingestion_requires_explicit_matching_sidecar_for_official_metadata(tmp_path: Path):
    module = _load_module()
    source = tmp_path / "CJJ 1-2008.pdf"
    source.write_bytes(b"placeholder")
    assert module._load_official_metadata_sidecar(source, standard_code="CJJ 1-2008") == {}

    sidecar = source.with_name(source.name + ".metadata.json")
    sidecar.write_text(
        json.dumps(
            {
                "standard_code": "CJJ 1-2008",
                "standard_name": "城镇道路工程施工与质量验收规范",
                "official_source": "https://official.example/CJJ-1-2008",
                "effective_status": "active",
                "current_version": "CJJ 1-2008",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    metadata = module._load_official_metadata_sidecar(source, standard_code="CJJ 1-2008")
    assert metadata["official_source"].startswith("https://official.example/")
    assert metadata["current_version"] == "CJJ 1-2008"


def test_ingestion_rejects_sidecar_bound_to_another_standard(tmp_path: Path):
    module = _load_module()
    source = tmp_path / "CJJ 1-2008.pdf"
    source.write_bytes(b"placeholder")
    source.with_name(source.name + ".metadata.json").write_text(
        json.dumps(
            {
                "standard_code": "GB 50300-2013",
                "official_source": "https://official.example/GB-50300-2013",
                "effective_status": "active",
                "current_version": "GB 50300-2013",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="official_metadata_standard_code_mismatch"):
        module._load_official_metadata_sidecar(source, standard_code="CJJ 1-2008")
