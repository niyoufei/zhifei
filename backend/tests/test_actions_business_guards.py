from __future__ import annotations

from backend.app.routers.actions_bridge import (
    _delivery_progress_for_run,
    _parse_variant_pair,
    _save_outputs,
)
from backend.app.routers import actions_bridge
import pytest


def test_variant_pair_parser_accepts_similarity_report_ids() -> None:
    assert _parse_variant_pair("v1_v2") == (1, 2)
    assert _parse_variant_pair("v12_v35") == (12, 35)
    assert _parse_variant_pair("variant1_variant2") is None


def test_dry_run_completion_never_claims_professional_delivery() -> None:
    completion = _delivery_progress_for_run(dry_run=True)

    assert completion["stage"] == "dry_run_done"
    assert completion["phase"] == "dry_run_done"
    assert "未生成专业终稿" in completion["detail"]
    assert "可直接下载" not in completion["detail"]


def test_real_run_completion_keeps_professional_delivery_copy() -> None:
    completion = _delivery_progress_for_run(dry_run=False)

    assert completion == {
        "stage": "done",
        "phase": "done",
        "detail": "专业 Word 已完成，可直接下载",
    }


def test_quality_blocked_content_can_only_be_written_as_explicit_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    variant = {
        "delivery_quality_gate": {
            "delivery_allowed": False,
            "decision_digest": "blocked-preview",
            "blockers": [{"code": "CONTENT_REVIEW_BLOCKED"}],
        }
    }
    saved: list[tuple[str, list[dict]]] = []
    monkeypatch.setattr(
        actions_bridge,
        "save_output_artifacts",
        lambda base_name, results, **kwargs: saved.append(
            (base_name, results, kwargs)
        )
        or {"json": "preview.json"},
    )

    with pytest.raises(RuntimeError, match="DELIVERY_QUALITY_GATE_BLOCKED"):
        _save_outputs("formal", [variant])

    assert _save_outputs("preview", [variant], preview_only=True) == {
        "json": "preview.json"
    }
    assert saved == [("preview", [variant], {"preview_only": True})]
