from __future__ import annotations

import json

import pytest

from backend.zhifei_autoplan import result_read_service


def test_load_result_bundle_returns_variants(tmp_path):
    json_path = tmp_path / "result.json"
    json_path.write_text(json.dumps({"variants": [{"variant_id": 1}]}), encoding="utf-8")

    out = result_read_service.load_result_bundle({"json": str(json_path)})

    assert out.json_path == str(json_path)
    assert out.data == {"variants": [{"variant_id": 1}]}
    assert out.variants == [{"variant_id": 1}]


def test_load_result_bundle_raises_when_json_missing(tmp_path):
    with pytest.raises(result_read_service.ResultReadFailure) as exc:
        result_read_service.load_result_bundle({"json": str(tmp_path / "missing.json")})

    assert exc.value.code == "result_json_not_found"
    assert exc.value.message == "result json not found"
    assert exc.value.extra == {"json_path": str(tmp_path / "missing.json")}


def test_load_result_bundle_raises_when_variants_empty(tmp_path):
    json_path = tmp_path / "empty.json"
    json_path.write_text(json.dumps({"variants": []}), encoding="utf-8")

    with pytest.raises(result_read_service.ResultReadFailure) as exc:
        result_read_service.load_result_bundle({"json": str(json_path)})

    assert exc.value.code == "empty_result"
    assert exc.value.message == "empty result"
    assert exc.value.extra == {"json_path": str(json_path)}


def test_load_result_bundle_with_contract_supports_custom_empty_error(tmp_path):
    json_path = tmp_path / "empty-contract.json"
    json_path.write_text(json.dumps({"variants": []}), encoding="utf-8")

    with pytest.raises(result_read_service.ResultReadFailure) as exc:
        result_read_service.load_result_bundle_with_contract(
            {"json": str(json_path)},
            empty_code="empty_result_variants",
            empty_message="empty result variants",
            read_text_errors="ignore",
        )

    assert exc.value.code == "empty_result_variants"
    assert exc.value.message == "empty result variants"
    assert exc.value.extra == {"json_path": str(json_path)}
