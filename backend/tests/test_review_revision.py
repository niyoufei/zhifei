from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest


def test_stable_issue_id_is_content_bound_and_order_independent():
    from backend.zhifei_autoplan.review_revision import issue_set_digest, stable_issue_id

    first = {
        "title": "质量管理",
        "type": "core_conclusion",
        "severity": "high",
        "problem": "证据不足",
        "suggestion": "补齐证据",
    }
    second = {
        "title": "安全管理",
        "type": "consistency",
        "severity": "medium",
        "problem": "口径不一致",
        "suggestion": "统一口径",
    }
    first_id = stable_issue_id(first, section_digest="section-a")
    assert first_id == stable_issue_id(dict(first), section_digest="section-a")
    assert first_id != stable_issue_id({**first, "problem": "证据完全缺失"}, section_digest="section-a")
    assert first_id != stable_issue_id(first, section_digest="section-b")

    left = [{**first, "issue_id": first_id}, {**second, "issue_id": stable_issue_id(second)}]
    assert issue_set_digest(left) == issue_set_digest(list(reversed(left)))


def test_revision_snapshot_round_trip_promotion_and_tamper_guard(tmp_path: Path, monkeypatch):
    from backend.zhifei_autoplan import review_revision

    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    artifact = tmp_path / "source.docx"
    artifact.write_bytes(b"document-bytes")
    variants = [{"variant_id": 1, "sections": [{"title": "总则", "content": "正文"}]}]

    created = review_revision.create_revision_snapshot(
        job_id="job-1",
        variants=variants,
        result={"docx": [str(artifact)]},
        reason="pre_review_apply",
        metadata={"actor": "tester"},
    )
    loaded = review_revision.load_revision_snapshot(job_id="job-1", revision_id=created["revision_id"])
    assert loaded["variants"] == variants
    assert loaded["artifacts"][0]["sha256"] == hashlib.sha256(b"document-bytes").hexdigest()
    assert loaded["artifacts"][0]["size"] == len(b"document-bytes")

    finalized = review_revision.finalize_revision_snapshot(
        job_id="job-1",
        revision_id=created["revision_id"],
        promotion={"candidate_result_version": "candidate-v1", "artifacts": []},
    )
    assert finalized["promotion"]["state"] == "committed"
    assert finalized["promotion"]["candidate_result_version"] == "candidate-v1"
    loaded = review_revision.load_revision_snapshot(job_id="job-1", revision_id=created["revision_id"])
    assert loaded["promotion"]["candidate_result_version"] == "candidate-v1"
    assert loaded["promotion"]["state"] == "committed"
    assert loaded["snapshot_digest"]
    rows = review_revision.list_revision_snapshots(job_id="job-1")
    assert rows[0]["promotion"]["candidate_result_version"] == "candidate-v1"
    with pytest.raises(ValueError, match="already finalized"):
        review_revision.finalize_revision_snapshot(
            job_id="job-1",
            revision_id=created["revision_id"],
            promotion={"candidate_result_version": "candidate-v2"},
        )

    path = Path(created["path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["promotion"]["candidate_result_version"] = "tampered"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="snapshot seal mismatch"):
        review_revision.load_revision_snapshot(job_id="job-1", revision_id=created["revision_id"])

    # Restore a valid sealed snapshot, then prove the content digest remains an
    # independent guard for the recoverable document state.
    payload["promotion"]["candidate_result_version"] = "candidate-v1"
    payload["snapshot_digest"] = review_revision.canonical_digest(
        {key: value for key, value in payload.items() if key != "snapshot_digest"}
    )
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["variants"][0]["sections"][0]["content"] = "tampered"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="digest mismatch"):
        review_revision.load_revision_snapshot(job_id="job-1", revision_id=created["revision_id"])


def test_revision_identifiers_reject_path_traversal():
    from backend.zhifei_autoplan.review_revision import list_revision_snapshots

    with pytest.raises(ValueError, match="invalid identifier"):
        list_revision_snapshots(job_id="../../")


def test_revision_promotion_two_phase_is_explicit_and_idempotent(
    tmp_path: Path,
    monkeypatch,
):
    from backend.zhifei_autoplan import review_revision

    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    created = review_revision.create_revision_snapshot(
        job_id="job-two-phase",
        variants=[{"variant_id": 1, "sections": []}],
        result={},
        reason="pre_review_apply",
    )
    prepared = review_revision.prepare_revision_promotion(
        job_id="job-two-phase",
        revision_id=created["revision_id"],
        promotion={
            "candidate_result_version": "candidate-v2",
            "candidate_artifact_digest": "a" * 64,
            "artifacts": [],
        },
    )
    assert prepared["promotion"]["state"] == "candidate_prepared"
    assert "promoted_at" not in prepared["promotion"]

    committed = review_revision.commit_revision_promotion(
        job_id="job-two-phase",
        revision_id=created["revision_id"],
        candidate_artifact_digest="a" * 64,
        promoted_job_revision=12,
        promoted_job_status="succeeded",
    )
    assert committed["promotion"]["state"] == "committed"
    assert committed["promotion"]["promoted_job_revision"] == 12
    replay = review_revision.commit_revision_promotion(
        job_id="job-two-phase",
        revision_id=created["revision_id"],
        candidate_artifact_digest="a" * 64,
        promoted_job_revision=12,
        promoted_job_status="succeeded",
    )
    assert replay["promotion"] == committed["promotion"]
