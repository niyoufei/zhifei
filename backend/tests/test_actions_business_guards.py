from __future__ import annotations

import pytest

from backend.app.routers import actions_bridge
from backend.app.routers.actions_bridge import (
    _delivery_progress_for_run,
    _parse_variant_pair,
    _save_outputs,
)
from backend.zhifei_autoplan import export_docx_service


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


@pytest.mark.parametrize(
    "variant,reason",
    [
        ({}, "delivery_gate_missing"),
        (
            {
                "delivery_quality_gate": {
                    "delivery_allowed": True,
                    "decision_digest": "a" * 64,
                    "blockers": [],
                }
            },
            "decision_digest_invalid",
        ),
    ],
)
def test_formal_save_fails_closed_when_gate_or_digest_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
    variant: dict,
    reason: str,
) -> None:
    monkeypatch.setattr(
        actions_bridge,
        "save_output_artifacts",
        lambda *_args, **_kwargs: pytest.fail("formal artifact must not be saved"),
    )

    with pytest.raises(RuntimeError, match=reason):
        _save_outputs("formal", [variant])


def test_formal_save_accepts_only_canonically_sealed_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core = {
        "schema_version": "delivery-quality-gate-v1",
        "delivery_allowed": True,
        "checks": [],
        "blocker_count": 0,
        "blockers": [],
    }
    variant = {
        "delivery_quality_gate": {
            **core,
            "decision_digest": export_docx_service.canonical_export_digest(core),
        }
    }
    monkeypatch.setattr(
        actions_bridge,
        "save_output_artifacts",
        lambda base_name, results: {
            "base_name": base_name,
            "variant_count": len(results),
        },
    )

    assert _save_outputs("formal", [variant]) == {
        "base_name": "formal",
        "variant_count": 1,
    }


def test_missing_gate_remains_available_only_for_explicit_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        actions_bridge,
        "save_output_artifacts",
        lambda base_name, results, **kwargs: {
            "base_name": base_name,
            "variant_count": len(results),
            "preview_only": kwargs.get("preview_only"),
        },
    )

    with pytest.raises(RuntimeError, match="variant_set_empty"):
        _save_outputs("formal-empty", [])
    assert _save_outputs("preview", [{}], preview_only=True) == {
        "base_name": "preview",
        "variant_count": 1,
        "preview_only": True,
    }
