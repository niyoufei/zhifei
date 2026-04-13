from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ResultReadFailure(Exception):
    code: str
    message: str
    next_action: str
    extra: dict[str, Any]


@dataclass
class ResultReadBundle:
    json_path: str
    data: dict[str, Any]
    variants: list[Any]


def load_result_bundle(result: dict[str, Any]) -> ResultReadBundle:
    json_path = result.get("json")
    if not json_path or not Path(json_path).exists():
        raise ResultReadFailure(
            code="result_json_not_found",
            message="result json not found",
            next_action="check worker log and result artifact output",
            extra={"json_path": str(json_path or "")},
        )
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    variants = data.get("variants") or []
    if not variants:
        raise ResultReadFailure(
            code="empty_result",
            message="empty result",
            next_action="check result json content",
            extra={"json_path": str(json_path or "")},
        )
    return ResultReadBundle(json_path=str(json_path), data=data, variants=variants)


def load_result_bundle_with_contract(
    result: dict[str, Any],
    *,
    empty_code: str,
    empty_message: str,
    read_text_errors: str | None = None,
) -> ResultReadBundle:
    json_path = result.get("json")
    if not json_path or not Path(json_path).exists():
        raise ResultReadFailure(
            code="result_json_not_found",
            message="result json not found",
            next_action="check worker log and result artifact output",
            extra={"json_path": str(json_path or "")},
        )
    read_kwargs = {"encoding": "utf-8"}
    if read_text_errors is not None:
        read_kwargs["errors"] = read_text_errors
    data = json.loads(Path(json_path).read_text(**read_kwargs))
    variants = data.get("variants") if isinstance(data.get("variants"), list) else []
    if not variants:
        raise ResultReadFailure(
            code=empty_code,
            message=empty_message,
            next_action="check result json content",
            extra={"json_path": str(json_path or "")},
        )
    return ResultReadBundle(json_path=str(json_path), data=data, variants=variants)
