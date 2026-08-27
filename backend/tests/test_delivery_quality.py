from __future__ import annotations

from backend.zhifei_autoplan.delivery_quality import build_delivery_quality_gate


def _base_kwargs() -> dict:
    return {
        "strict": True,
        "content_review": {"quality_gate": {"pass": True, "blocking_issues": []}},
        "plan_consistency": {"ok": True, "canonical": {"duration_days": 180}},
        "model_review_audit": {
            "failed_chapters": [],
            "consistency_review": {
                "ok": True,
                "summary": "未发现实质性冲突。",
            },
        },
        "requirement_matrix": {
            "summary": {"strict_delivery_allowed": True, "blocking_requirement_ids": []}
        },
        "standard_audit": {"ok": True, "violations": []},
        "cross_index": {
            "ok": True,
            "focus_count": 1,
            "mentioned_count": 1,
            "closed_ok_count": 1,
            "missing_drawing_locator_count": 0,
            "missing_standard_locator_count": 0,
            "focus_items": [{"name": "钢筋"}],
        },
        "model_review_required": True,
    }


def test_professional_delivery_gate_passes_complete_evidence_chain():
    gate = build_delivery_quality_gate(**_base_kwargs())
    assert gate["delivery_allowed"] is True
    assert gate["blocker_count"] == 0
    assert len(gate["decision_digest"]) == 64


def test_professional_delivery_gate_blocks_model_conflict():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"] = {
        "failed_chapters": [],
        "consistency_review": {"ok": True, "summary": "发现工期与资源峰值存在明显冲突。"},
    }
    gate = build_delivery_quality_gate(**kwargs)
    assert gate["delivery_allowed"] is False
    assert "DELIVERY_MODEL_REVIEW_BLOCKED" in {
        row["code"] for row in gate["blockers"]
    }


def test_model_review_accepts_machine_readable_pass_decision():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"]["consistency_review"]["summary"] = (
        "DECISION: PASS\n未发现实质性冲突。"
    )

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is True


def test_model_review_machine_readable_block_overrides_pass_phrase():
    kwargs = _base_kwargs()
    kwargs["model_review_audit"]["consistency_review"]["summary"] = (
        "DECISION: BLOCK\n虽然某些项目未发现实质性冲突，但工期口径不一致。"
    )

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False


def test_professional_delivery_gate_blocks_incomplete_boq_cross_index():
    kwargs = _base_kwargs()
    kwargs["cross_index"] = {
        "ok": True,
        "focus_count": 3,
        "mentioned_count": 3,
        "closed_ok_count": 2,
        "missing_drawing_locator_count": 1,
        "missing_standard_locator_count": 0,
        "focus_items": [
            {"name": "钢筋"},
            {"name": "模板"},
            {"name": "混凝土"},
        ],
    }
    gate = build_delivery_quality_gate(**kwargs)
    assert gate["delivery_allowed"] is False
    assert "DELIVERY_CROSS_INDEX_BLOCKED" in {
        row["code"] for row in gate["blockers"]
    }


def test_professional_delivery_gate_fails_closed_when_cross_index_is_unavailable():
    kwargs = _base_kwargs()
    kwargs["cross_index"] = {
        "ok": False,
        "build_failed": True,
        "focus_count": 3,
        "mentioned_count": 0,
        "closed_ok_count": 0,
        "missing_drawing_locator_count": 0,
        "missing_standard_locator_count": 0,
        "focus_items": [],
    }

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False
    assert "DELIVERY_CROSS_INDEX_UNAVAILABLE" in {
        row["code"] for row in gate["blockers"]
    }


def test_professional_delivery_gate_fails_closed_on_empty_cross_index_result():
    kwargs = _base_kwargs()
    kwargs["cross_index"] = {}

    gate = build_delivery_quality_gate(**kwargs)

    assert gate["delivery_allowed"] is False
    assert "DELIVERY_CROSS_INDEX_UNAVAILABLE" in {
        row["code"] for row in gate["blockers"]
    }


def test_model_review_is_informational_when_not_required():
    kwargs = _base_kwargs()
    kwargs["model_review_required"] = False
    kwargs["model_review_audit"] = {}
    gate = build_delivery_quality_gate(**kwargs)
    assert gate["delivery_allowed"] is True
    assert gate["warning_count"] == 1
