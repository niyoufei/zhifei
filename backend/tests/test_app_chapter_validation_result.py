from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


APP_PATH = Path(__file__).resolve().parents[2] / "app.py"


def _load_collect_helper(download):
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"), filename=str(APP_PATH))
    selected = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_collect_job_result"
    ]
    namespace: dict[str, Any] = {
        "Any": Any,
        "json": json,
        "_download_bytes": download,
    }
    exec(
        compile(ast.Module(body=selected, type_ignores=[]), str(APP_PATH), "exec"),
        namespace,
    )
    return namespace["_collect_job_result"]


def test_chapter_validation_collects_json_without_formal_artifact_requests() -> None:
    calls: list[str] = []
    payload = {
        "variants": [
            {
                "delivery_scope": "chapter_validation",
                "delivery_ready": False,
                "quality_checks": {},
                "pipeline_stages": [],
            }
        ]
    }

    def download(_base, _key, _job, kind, _variant, **_kwargs):
        calls.append(kind)
        if kind != "json":
            raise AssertionError(f"chapter validation requested formal artifact: {kind}")
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    collect = _load_collect_helper(download)
    result = collect("http://127.0.0.1:8010", "key", "a" * 32)

    assert calls == ["json"]
    assert result["delivery_scope"] == "chapter_validation"
    assert result["delivery_receipt"] is None
    assert result["artifacts"] == {1: {}}
    assert result["runtime_by_variant"][1]["delivery_ready"] is False
