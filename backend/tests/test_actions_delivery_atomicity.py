from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException


def _write_rendered_variant(
    root: Path,
    *,
    job_id: str,
    variant: int,
    stem: str,
) -> dict[str, object]:
    professional_docx = root / f"{stem}.docx"
    professional_json = root / f"{stem}.json"
    render_receipt = root / f"{stem}.receipt.json"
    professional_docx.write_bytes(f"professional-{stem}".encode())
    professional_json.write_text("{}", encoding="utf-8")
    output_sha256 = hashlib.sha256(professional_docx.read_bytes()).hexdigest()
    structural = professional_docx.with_suffix(".structural_quality.json")
    structural.write_text(
        json.dumps({"status": "pass", "docx_sha256": output_sha256}),
        encoding="utf-8",
    )
    visual = professional_docx.with_suffix(".visual_quality.json")
    visual.write_text(
        json.dumps({"status": "pass", "docx_sha256": output_sha256}),
        encoding="utf-8",
    )
    professional_docx.with_suffix(".figure_manifest.json").write_text(
        json.dumps({"delivery_allowed": True}),
        encoding="utf-8",
    )
    quality_gate = {
        "original_preserved": True,
        "titles_preserved": True,
        "evidence_not_reduced": True,
        "tender_style_fields_preserved": True,
        "export_succeeded": True,
        "structural_quality_passed": True,
        "visual_page_quality_passed": True,
        "no_blank_pages": True,
        "no_orphan_headings": True,
    }
    receipt_payload = {
        "job_id": job_id,
        "variant": variant,
        "professional_docx_sha256": output_sha256,
        "quality_gate": quality_gate,
        "structural_quality": {"receipt": str(structural)},
        "visual_quality": {"receipt": str(visual)},
        "display_model": "Sonnet 5",
        "model_id": "test-renderer",
    }
    render_receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")
    return {
        "professional_docx": str(professional_docx),
        "professional_json": str(professional_json),
        "professional_render_receipt": str(render_receipt),
        "receipt": receipt_payload,
    }


def _registry_authority(tmp_path: Path) -> dict[str, object]:
    source_digest = "d" * 64
    release_id = "release-" + source_digest[:24]
    registry_core = {
        "schema_version": "sealed-compliance-registry-authority-v1",
        "source_kind": "sealed_release_manifest_entry",
        "release_id": release_id,
        "manifest_digest": "e" * 64,
        "source_digest": source_digest,
        "runtime_digest": "f" * 64,
        "registry_path": str(
            tmp_path
            / release_id
            / "sealed-compliance"
            / "_official_registry.json"
        ),
        "registry_relative_path": "sealed-compliance/_official_registry.json",
        "registry_sha256": "c" * 64,
        "registry_size": 128,
        "registry_mode": 0o444,
    }
    return {
        **registry_core,
        "authority_digest": hashlib.sha256(
            json.dumps(
                registry_core,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
    }


def _generation_release_identity(
    registry_authority: dict[str, object],
) -> dict[str, object]:
    return {
        "schema_version": "autoplan-generation-release-v1",
        "system_id": "docgen-system",
        "release_id": registry_authority["release_id"],
        "manifest_digest": registry_authority["manifest_digest"],
        "source_digest": registry_authority["source_digest"],
        "runtime_digest": registry_authority["runtime_digest"],
        "release_root": str(Path(str(registry_authority["registry_path"])).parents[1]),
        "runtime_mode": "sealed_release",
        "release_managed": True,
    }


def _formal_delivery_fixture(
    tmp_path: Path,
    *,
    job_id: str = "a" * 32,
    variant_ids: tuple[int, ...] = (1,),
    include_registry_authority: bool = True,
    managed_runtime_chain: bool = False,
) -> tuple[dict, dict, list[dict]]:
    from backend.zhifei_autoplan.delivery_receipt import build_delivery_receipt
    from backend.zhifei_autoplan.export_docx_service import canonical_export_digest
    from backend.zhifei_autoplan.generation_checkpoint import (
        build_generation_binding,
        finalize_generation_checkpoint,
        save_section_checkpoint,
    )
    from backend.zhifei_autoplan.professional_document_renderer import (
        canonical_professional_render_receipt_digest,
    )
    from backend.zhifei_autoplan.runtime_events import append_runtime_event

    sources: list[str] = []
    professional: list[str] = []
    professional_json: list[str] = []
    render_receipts: list[str] = []
    compare_docx: list[str] = []
    focus_xlsx: list[str] = []
    score_overview_xlsx: list[str] = []
    expert_review_docx: list[str] = []
    variants: list[dict] = []
    registry_authority = _registry_authority(tmp_path)
    generation_release = _generation_release_identity(registry_authority)
    execution_identity = {
        "job_id": job_id,
        "attempt_id": "b" * 32,
        "owner_instance_id": "c" * 32,
        "job_revision": 17,
    }
    for index, variant_id in enumerate(variant_ids, start=1):
        source = tmp_path / f"source-v{index}.docx"
        source.write_bytes(f"source-{index}".encode())
        rendered = _write_rendered_variant(
            tmp_path,
            job_id=job_id,
            variant=index,
            stem=f"professional-v{index}",
        )
        sources.append(str(source))
        professional.append(str(rendered["professional_docx"]))
        professional_json.append(str(rendered["professional_json"]))
        render_receipts.append(str(rendered["professional_render_receipt"]))
        ancillary_paths = {
            "compare_docx": tmp_path / f"compare-v{index}.docx",
            "focus_xlsx": tmp_path / f"focus-v{index}.xlsx",
            "score_overview_xlsx": tmp_path / f"score-v{index}.xlsx",
            "expert_review_docx": tmp_path / f"expert-v{index}.docx",
        }
        for kind, path in ancillary_paths.items():
            path.write_bytes(f"{kind}-{index}".encode())
        compare_docx.append(str(ancillary_paths["compare_docx"]))
        focus_xlsx.append(str(ancillary_paths["focus_xlsx"]))
        score_overview_xlsx.append(str(ancillary_paths["score_overview_xlsx"]))
        expert_review_docx.append(str(ancillary_paths["expert_review_docx"]))
        standard_index = {
            "ok": True,
            "project_id": "P-ATOMIC",
            "standards": [{"standard_code": "GB 50000-2020"}],
        }
        standard_audit = {
            "ok": True,
            "verified_standard_codes": ["GB_50000_2020"],
        }
        delivery_gate = {
            "schema_version": "delivery-quality-gate-v1",
            "formal_contract_version": "formal-evidence-v2",
            "strict": True,
            "delivery_allowed": True,
            "checks": [
                {
                    "name": "verified_standards",
                    "pass": True,
                    "required": True,
                    "standard_audit_digest": canonical_export_digest(
                        standard_audit
                    ),
                    "standard_index_digest": canonical_export_digest(
                        standard_index
                    ),
                    "audit_verified_standard_codes": ["GB_50000_2020"],
                    "index_verified_standard_codes": ["GB_50000_2020"],
                    "missing_verified_standard_codes": [],
                }
            ],
            "blocker_count": 0,
            "warning_count": 0,
            "blockers": [],
            "warnings": [],
        }
        delivery_gate["decision_digest"] = canonical_export_digest(delivery_gate)
        variant_record = {
            "variant_id": variant_id,
            "delivery_scope": "document",
            "delivery_ready": True,
            "delivery_quality_gate": delivery_gate,
            "standard_index": standard_index,
            "standard_citation_audit": standard_audit,
            "compliance_registry_authority": registry_authority,
            "sections": [],
            "quality_checks": {"issue_list": [], "auto_revision_suggestions": []},
        }
        if managed_runtime_chain:
            managed_standard_index = {
                **standard_index,
                "official_registry_path": registry_authority["registry_path"],
                "official_registry_sha256": registry_authority[
                    "registry_sha256"
                ],
            }
            delivery_gate["checks"][0]["standard_index_digest"] = (
                canonical_export_digest(managed_standard_index)
            )
            delivery_gate["decision_digest"] = canonical_export_digest(
                {
                    key: value
                    for key, value in delivery_gate.items()
                    if key != "decision_digest"
                }
            )
            section = {
                "title": "第一章",
                "content": f"方案{variant_id}正式正文",
                "provider": "provider-a",
                "model": "model-a",
                "model_slot": "text_primary",
            }
            binding = build_generation_binding(
                **execution_identity,
                topic="项目施工组织设计",
                project_id="P-ATOMIC",
                project_type="房屋建筑工程",
                outline=["第一章"],
                style={"tone": "professional"},
                chapter_pages={"第一章": 1},
                variant_id=variant_id,
                project_fact_digest="1" * 64,
                requirement_plan_digest="2" * 64,
                provider_routes=[
                    {
                        "slot": "text_primary",
                        "provider": "provider-a",
                        "model": "model-a",
                    }
                ],
                delivery_scope="document",
                provider_admission_digest="3" * 64,
                compliance_registry_authority_digest=registry_authority[
                    "authority_digest"
                ],
                prompt_contract={"version": 1},
            )
            save_section_checkpoint(
                namespace=job_id,
                scope=f"variant-{variant_id}",
                binding=binding,
                chapter_index=0,
                chapter_title="第一章",
                chapter_context_digest="4" * 64,
                result=section,
            )
            checkpoint_summary = finalize_generation_checkpoint(
                namespace=job_id,
                scope=f"variant-{variant_id}",
                binding=binding,
                status="complete",
            )
            variant_record.update(
                {
                    "generation_release_identity": generation_release,
                    "standard_index": managed_standard_index,
                    "outline": ["第一章"],
                    "sections": [section],
                    "generation_checkpoint": checkpoint_summary,
                }
            )
        variants.append(variant_record)

    result_json = tmp_path / "result.json"
    result_json.write_text(json.dumps({"variants": variants}), encoding="utf-8")

    if managed_runtime_chain:
        for index, (variant, path) in enumerate(
            zip(variants, professional_json, strict=True),
            start=1,
        ):
            professional_variant = copy.deepcopy(variant)
            professional_variant["sections"] = [
                {
                    **dict(variant["sections"][0]),
                    "original_content": variant["sections"][0]["content"],
                    "professional_render": {"status": "refined"},
                }
            ]
            Path(path).write_text(
                json.dumps(
                    {
                        "generation_release_identity": generation_release,
                        "compliance_registry_authority": registry_authority,
                        "variants": [professional_variant],
                        "professional_render_source_variant": index,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            render_receipt_path = Path(render_receipts[index - 1])
            render_receipt = json.loads(
                render_receipt_path.read_text(encoding="utf-8")
            )
            render_receipt.update(
                {
                    "schema": "zhifei.professional_document_render.v1",
                    "source_json": str(result_json),
                    "source_json_sha256": hashlib.sha256(
                        result_json.read_bytes()
                    ).hexdigest(),
                    "source_docx": sources[index - 1],
                    "source_docx_sha256": hashlib.sha256(
                        Path(sources[index - 1]).read_bytes()
                    ).hexdigest(),
                    "professional_docx": professional[index - 1],
                    "professional_docx_sha256": hashlib.sha256(
                        Path(professional[index - 1]).read_bytes()
                    ).hexdigest(),
                    "professional_json": professional_json[index - 1],
                    "professional_json_sha256": hashlib.sha256(
                        Path(professional_json[index - 1]).read_bytes()
                    ).hexdigest(),
                }
            )
            render_receipt["receipt_digest"] = (
                canonical_professional_render_receipt_digest(render_receipt)
            )
            render_receipt_path.write_text(
                json.dumps(render_receipt, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
        append_runtime_event(
            job_id,
            "job_started",
            **{key: value for key, value in execution_identity.items() if key != "job_id"},
            generation_release_identity=generation_release,
            compliance_registry_authority=registry_authority,
        )
        for variant in variants:
            append_runtime_event(
                job_id,
                "compliance_preflight",
                **{
                    key: value
                    for key, value in execution_identity.items()
                    if key != "job_id"
                },
                variant_id=variant["variant_id"],
                ready=True,
                authority_digest=registry_authority["authority_digest"],
                official_registry_sha256=registry_authority["registry_sha256"],
                verified_standard_count=3,
                project_domains=["房建工程"],
            )
        append_runtime_event(
            job_id,
            "provider_admission_started",
            **{key: value for key, value in execution_identity.items() if key != "job_id"},
        )
        append_runtime_event(
            job_id,
            "job_succeeded",
            **{key: value for key, value in execution_identity.items() if key != "job_id"},
            dry_run=False,
            delivery_scope="document",
            generation_release_identity=generation_release,
            compliance_registry_authority=registry_authority,
        )
    sealed = build_delivery_receipt(
        job_id=job_id,
        source_docx=sources,
        professional_docx=professional,
        professional_json=professional_json,
        professional_receipts=render_receipts,
        compare_docx=compare_docx,
        focus_xlsx=focus_xlsx,
        score_overview_xlsx=score_overview_xlsx,
        expert_review_docx=expert_review_docx,
        receipt_path=tmp_path / "delivery-receipt.json",
        compliance_registry_authority=(
            registry_authority if include_registry_authority else None
        ),
        job_execution_identity=(
            execution_identity if managed_runtime_chain else None
        ),
    )
    result = {
        "json": str(result_json),
        "source_docx": sources,
        "docx": list(professional),
        "professional_docx": professional,
        "professional_json": professional_json,
        "professional_render_receipt": render_receipts,
        "compare_docx": compare_docx,
        "focus_xlsx": focus_xlsx,
        "score_overview_xlsx": score_overview_xlsx,
        "expert_review_docx": expert_review_docx,
        "delivery_profile": "sonnet5_professional_word",
        "delivery_ready": True,
        "validation_scope": "document",
        "delivery_receipt": str(sealed["receipt"]),
        "delivery_decision_digest": str(sealed["decision_digest"]),
        "compliance_registry_authority": registry_authority,
    }
    if managed_runtime_chain:
        result.update(
            {
                "generation_release_identity": generation_release,
                "job_execution_identity": execution_identity,
            }
        )
    job = {
        "job_id": job_id,
        "status": "succeeded",
        "revision": 17,
        "payload": {"delivery_scope": "document", "dry_run": False},
        "result": result,
    }
    if managed_runtime_chain:
        job.update(
            {
                "last_attempt_id": execution_identity["attempt_id"],
                "last_owner_instance_id": execution_identity[
                    "owner_instance_id"
                ],
                "last_job_revision": execution_identity["job_revision"],
                "agent_runtime": {
                    "generation_release_identity": generation_release,
                    "compliance_registry_authority": registry_authority,
                },
            }
        )
    return job, result, variants


def _configure_managed_runtime_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, object], dict[str, object]]:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import generation_checkpoint, runtime_events

    authority = _registry_authority(tmp_path)
    generation_release = _generation_release_identity(authority)
    monkeypatch.setattr(
        generation_checkpoint,
        "CHECKPOINT_DIR",
        tmp_path / "checkpoints",
    )
    monkeypatch.setattr(runtime_events, "EVENT_DIR", tmp_path / "events")
    monkeypatch.setattr(
        actions_bridge,
        "_GENERATION_RELEASE_IDENTITY_AT_START",
        generation_release,
    )
    monkeypatch.setattr(
        actions_bridge,
        "_generation_compliance_registry_authority_from_environment",
        lambda: copy.deepcopy(authority),
    )
    return generation_release, authority


def test_managed_formal_delivery_state_verifies_runtime_authority_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge

    _configure_managed_runtime_chain(tmp_path, monkeypatch)
    job, result, variants = _formal_delivery_fixture(
        tmp_path,
        variant_ids=(1, 2),
        managed_runtime_chain=True,
    )

    assert actions_bridge._formal_delivery_state(job, result, variants) == (
        True,
        "formal_document_ready",
    )


def test_managed_formal_delivery_rejects_missing_current_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge

    _configure_managed_runtime_chain(tmp_path, monkeypatch)
    job, result, variants = _formal_delivery_fixture(
        tmp_path,
        variant_ids=(1, 2),
        managed_runtime_chain=True,
    )
    event_path = tmp_path / "events" / f"{job['job_id']}.jsonl"
    events = [json.loads(line) for line in event_path.read_text().splitlines()]
    removed = False
    retained = []
    for event in events:
        if event.get("event") == "compliance_preflight" and not removed:
            removed = True
            continue
        retained.append(event)
    event_path.write_text(
        "".join(json.dumps(event) + "\n" for event in retained),
        encoding="utf-8",
    )

    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "runtime_event_evidence_invalid"
    )


def test_managed_formal_delivery_rejects_resealed_wrong_checkpoint_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan.review_revision import canonical_digest

    _configure_managed_runtime_chain(tmp_path, monkeypatch)
    job, result, variants = _formal_delivery_fixture(
        tmp_path,
        managed_runtime_chain=True,
    )
    checkpoint_path = tmp_path / "checkpoints" / job["job_id"] / "variant-1.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    binding = checkpoint["binding"]
    binding["compliance_registry_authority_digest"] = "f" * 64
    binding["binding_digest"] = canonical_digest(
        {key: value for key, value in binding.items() if key != "binding_digest"}
    )
    checkpoint["binding_digest"] = binding["binding_digest"]
    variants[0]["generation_checkpoint"]["binding_digest"] = binding[
        "binding_digest"
    ]
    checkpoint["integrity_digest"] = canonical_digest(
        {
            key: value
            for key, value in checkpoint.items()
            if key != "integrity_digest"
        }
    )
    checkpoint_path.write_text(
        json.dumps(checkpoint, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "generation_checkpoint_evidence_invalid"
    )


def test_managed_formal_delivery_rejects_resealed_professional_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan.delivery_receipt import build_delivery_receipt

    _configure_managed_runtime_chain(tmp_path, monkeypatch)
    job, result, variants = _formal_delivery_fixture(
        tmp_path,
        managed_runtime_chain=True,
    )
    professional_path = Path(result["professional_json"][0])
    professional = json.loads(professional_path.read_text(encoding="utf-8"))
    professional["compliance_registry_authority"] = {
        **professional["compliance_registry_authority"],
        "registry_sha256": "f" * 64,
    }
    professional_path.write_text(
        json.dumps(professional, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    sealed = build_delivery_receipt(
        job_id=job["job_id"],
        source_docx=result["source_docx"],
        professional_docx=result["professional_docx"],
        professional_json=result["professional_json"],
        professional_receipts=result["professional_render_receipt"],
        compare_docx=result["compare_docx"],
        focus_xlsx=result["focus_xlsx"],
        score_overview_xlsx=result["score_overview_xlsx"],
        expert_review_docx=result["expert_review_docx"],
        receipt_path=tmp_path / "delivery-resealed.json",
        job_execution_identity=result["job_execution_identity"],
        compliance_registry_authority=result["compliance_registry_authority"],
    )
    result["delivery_receipt"] = str(sealed["receipt"])
    result["delivery_decision_digest"] = sealed["decision_digest"]

    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "professional_json_authority_invalid"
    )
    with pytest.raises(HTTPException) as error:
        actions_bridge._require_formal_document_mutation(job, result, variants)
    assert error.value.status_code == 409
    assert error.value.detail == {
        "code": "NON_DELIVERABLE_MUTATION_FORBIDDEN",
        "message": "非正式交付任务仅允许只读复核，不能晋升、回滚或渲染正式交付文件。",
        "reason": "professional_json_authority_invalid",
    }


@pytest.mark.parametrize("reseal_task_receipt", (False, True))
def test_managed_formal_delivery_rejects_source_json_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reseal_task_receipt: bool,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan.delivery_receipt import build_delivery_receipt

    _configure_managed_runtime_chain(tmp_path, monkeypatch)
    job, result, _variants = _formal_delivery_fixture(
        tmp_path,
        managed_runtime_chain=True,
    )
    source_json_path = Path(result["json"])
    rewritten = json.loads(source_json_path.read_text(encoding="utf-8"))
    rewritten["variants"][0]["sections"][0]["content"] = "事后改写的正文"
    source_json_path.write_text(
        json.dumps(rewritten, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    if reseal_task_receipt:
        sealed = build_delivery_receipt(
            job_id=job["job_id"],
            source_docx=result["source_docx"],
            professional_docx=result["professional_docx"],
            professional_json=result["professional_json"],
            professional_receipts=result["professional_render_receipt"],
            compare_docx=result["compare_docx"],
            focus_xlsx=result["focus_xlsx"],
            score_overview_xlsx=result["score_overview_xlsx"],
            expert_review_docx=result["expert_review_docx"],
            receipt_path=tmp_path / "delivery-source-resealed.json",
            job_execution_identity=result["job_execution_identity"],
            compliance_registry_authority=result[
                "compliance_registry_authority"
            ],
        )
        result["delivery_receipt"] = str(sealed["receipt"])
        result["delivery_decision_digest"] = sealed["decision_digest"]
    monkeypatch.setattr(actions_bridge, "get_job", lambda _job_id: job)
    loaded_job, loaded_result, _data, loaded_variants = (
        actions_bridge._load_done_job_variants(job["job_id"])
    )

    assert actions_bridge._formal_delivery_state(
        loaded_job,
        loaded_result,
        loaded_variants,
    )[1] == "professional_render_receipt_binding_invalid"
    with pytest.raises(HTTPException) as error:
        actions_bridge._require_formal_document_mutation(
            loaded_job,
            loaded_result,
            loaded_variants,
        )
    assert error.value.status_code == 409
    assert error.value.detail["reason"] == (
        "professional_render_receipt_binding_invalid"
    )


def test_formal_delivery_state_requires_sealed_exact_professional_artifacts(
    tmp_path: Path,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    assert actions_bridge._formal_delivery_state(job, result, variants) == (
        True,
        "formal_document_ready",
    )


    outer_blocked = dict(result, delivery_ready=False)
    assert actions_bridge._formal_delivery_state(job, outer_blocked, variants)[1] == (
        "outer_delivery_not_ready"
    )
    wrong_profile = dict(result, delivery_profile="professional_render_incomplete")
    assert actions_bridge._formal_delivery_state(job, wrong_profile, variants)[1] == (
        "delivery_profile_mismatch"
    )
    wrong_public_word = copy.deepcopy(result)
    wrong_public_word["docx"] = list(result["source_docx"])
    assert actions_bridge._formal_delivery_state(job, wrong_public_word, variants)[1] == (
        "public_professional_path_mismatch"
    )
    failed_job = dict(job, status="failed")
    assert actions_bridge._formal_delivery_state(failed_job, result, variants)[1] == (
        "job_not_succeeded"
    )

    tampered_gate = copy.deepcopy(variants)
    tampered_gate[0]["delivery_quality_gate"]["delivery_allowed"] = False
    assert actions_bridge._formal_delivery_state(job, result, tampered_gate)[1] == (
        "delivery_gate_invalid"
    )

    stale_gate = copy.deepcopy(variants)
    gate = stale_gate[0]["delivery_quality_gate"]
    gate.pop("formal_contract_version")
    gate["decision_digest"] = actions_bridge.export_docx_core.canonical_export_digest(
        {key: value for key, value in gate.items() if key != "decision_digest"}
    )
    assert actions_bridge._formal_delivery_state(job, result, stale_gate)[1] == (
        "delivery_gate_contract_stale"
    )

    tampered_index = copy.deepcopy(variants)
    tampered_index[0]["standard_index"]["renamed"] = True
    assert actions_bridge._formal_delivery_state(job, result, tampered_index)[1] == (
        "delivery_gate_contract_stale"
    )

    forged_code_binding = copy.deepcopy(variants)
    forged_gate = forged_code_binding[0]["delivery_quality_gate"]
    forged_standard_check = forged_gate["checks"][0]
    forged_standard_check["audit_verified_standard_codes"] = ["CJJ_1_2008"]
    forged_standard_check["missing_verified_standard_codes"] = []
    forged_gate["decision_digest"] = (
        actions_bridge.export_docx_core.canonical_export_digest(
            {
                key: value
                for key, value in forged_gate.items()
                if key != "decision_digest"
            }
        )
    )
    assert actions_bridge._formal_delivery_state(
        job,
        result,
        forged_code_binding,
    )[1] == "delivery_gate_contract_stale"


def test_formal_pass_receipt_requires_sealed_registry_authority(
    tmp_path: Path,
) -> None:
    from backend.zhifei_autoplan.delivery_receipt import DeliveryReceiptError

    with pytest.raises(
        DeliveryReceiptError,
        match="缺少标准registry权威身份",
    ):
        _formal_delivery_fixture(
            tmp_path,
            include_registry_authority=False,
        )


def test_formal_delivery_scope_must_be_explicit_in_payload_and_every_variant(
    tmp_path: Path,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    missing_payload_scope = copy.deepcopy(job)
    missing_payload_scope["payload"].pop("delivery_scope")
    assert actions_bridge._formal_delivery_state(
        missing_payload_scope,
        result,
        variants,
    )[1] == "delivery_scope_missing"

    missing_variant_scope = copy.deepcopy(variants)
    missing_variant_scope[0].pop("delivery_scope")
    assert actions_bridge._formal_delivery_state(
        job,
        result,
        missing_variant_scope,
    )[1] == "variant_scope_missing"


@pytest.mark.parametrize("value", [None, False, "true"])
def test_formal_delivery_outer_ready_must_be_literal_true(
    tmp_path: Path,
    value: object,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    result["delivery_ready"] = value
    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "outer_delivery_not_ready"
    )


@pytest.mark.parametrize("value", [None, "", "chapter_validation"])
def test_formal_delivery_outer_validation_scope_must_be_document(
    tmp_path: Path,
    value: object,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    result["validation_scope"] = value
    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "outer_validation_scope_mismatch"
    )


def test_task_receipt_decision_digest_is_recomputed_from_canonical_content(
    tmp_path: Path,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    receipt_path = Path(result["delivery_receipt"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "zhifei.delivery_receipt.v2"
    receipt["variants"][0]["quality_gate"]["export_succeeded"] = False
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "delivery_receipt_digest_mismatch"
    )


@pytest.mark.parametrize("attack", ("invalid_utf8", "symlink", "oversized"))
def test_task_receipt_requires_bounded_regular_stable_json(
    tmp_path: Path,
    attack: str,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    receipt_path = Path(result["delivery_receipt"])
    if attack == "invalid_utf8":
        receipt_path.write_bytes(b"\xff\xfe\xfd")
    elif attack == "symlink":
        target = tmp_path / "task-receipt-target.json"
        receipt_path.replace(target)
        receipt_path.symlink_to(target)
    else:
        with receipt_path.open("wb") as handle:
            handle.truncate(actions_bridge._MAX_FORMAL_RUNTIME_JSON_BYTES + 1)

    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "delivery_receipt_invalid"
    )


@pytest.mark.parametrize(
    "artifact_key",
    [
        "professional_json",
        "compare_docx",
        "focus_xlsx",
        "score_overview_xlsx",
        "expert_review_docx",
    ],
)
def test_formal_delivery_v2_binds_every_downloadable_variant_artifact(
    tmp_path: Path,
    artifact_key: str,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    Path(result[artifact_key][0]).write_bytes(b"tampered-after-seal")
    assert actions_bridge._formal_delivery_state(job, result, variants)[1] == (
        "delivery_receipt_hash_mismatch"
    )


@pytest.mark.parametrize("artifact_key", ["compare_docx", "focus_xlsx"])
def test_formal_delivery_rejects_scalar_variant_artifact_paths(
    tmp_path: Path,
    artifact_key: str,
) -> None:
    from backend.app.routers import actions_bridge

    job, result, variants = _formal_delivery_fixture(tmp_path)
    malformed = copy.deepcopy(result)
    malformed[artifact_key] = result[artifact_key][0]
    assert actions_bridge._formal_delivery_state(job, malformed, variants)[1] == (
        "delivery_artifact_set_incomplete"
    )


@pytest.mark.asyncio
async def test_candidate_prepared_audit_blocks_mutation_and_download_until_committed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    job, result, variants = _formal_delivery_fixture(tmp_path)
    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    created = review_revision.create_revision_snapshot(
        job_id=job["job_id"],
        variants=copy.deepcopy(variants),
        result=result,
        reason="pre_review_apply",
    )
    candidate_digest = "a" * 64
    prepared = review_revision.prepare_revision_promotion(
        job_id=job["job_id"],
        revision_id=created["revision_id"],
        promotion={"candidate_artifact_digest": candidate_digest},
    )
    pending_result = copy.deepcopy(result)
    pending_result["promotion_audit_receipt"] = prepared["path"]
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, pending_result, {"variants": variants}, variants),
    )

    assert actions_bridge._formal_delivery_state(job, pending_result, variants)[1] == (
        "promotion_audit_pending"
    )
    with pytest.raises(HTTPException) as mutation_error:
        actions_bridge._require_formal_document_mutation(
            job,
            pending_result,
            variants,
        )
    assert mutation_error.value.detail["reason"] == "promotion_audit_pending"
    with (
        patch.dict("os.environ", {"ZF_ACTIONS_KEY": "test-actions-key"}, clear=False),
        pytest.raises(HTTPException) as download_error,
    ):
        await actions_bridge.actions_download(
            job_id=job["job_id"],
            kind="docx",
            variant=1,
            x_actions_key="test-actions-key",
        )
    assert download_error.value.detail["reason"] == "promotion_audit_pending"

    review_revision.commit_revision_promotion(
        job_id=job["job_id"],
        revision_id=created["revision_id"],
        candidate_artifact_digest=candidate_digest,
        promoted_job_revision=job["revision"],
        promoted_job_status=job["status"],
    )
    assert actions_bridge._formal_delivery_state(job, pending_result, variants) == (
        True,
        "formal_document_ready",
    )


@pytest.mark.asyncio
async def test_candidate_render_uses_unique_task_receipt_but_original_owner_job_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge

    job_id = "b" * 32
    source = tmp_path / "source.docx"
    source.write_bytes(b"source")
    compare = tmp_path / "compare.docx"
    compare.write_bytes(b"compare")
    result_json = tmp_path / "result.json"
    result_json.write_text('{"variants":[{}]}', encoding="utf-8")
    calls: list[str] = []

    async def fake_render(*, job_id, variant, result, artifact_namespace, **_kwargs):
        calls.append(artifact_namespace)
        return _write_rendered_variant(
            tmp_path,
            job_id=job_id,
            variant=variant,
            stem=f"{artifact_namespace}-{len(calls)}",
        )

    monkeypatch.setattr(actions_bridge, "render_professional_document", fake_render)
    outputs = {
        "json": str(result_json),
        "docx": [str(source)],
        "compare_docx": [str(compare)],
        "focus_xlsx": [None],
        "score_overview_xlsx": [None],
        "expert_review_docx": [None],
        "compliance_registry_authority": _registry_authority(tmp_path),
    }
    first = await actions_bridge._render_professional_outputs_for_job(
        job_id=job_id,
        outputs=outputs,
        artifact_namespace="candidate-shared",
        slot_override=object(),
    )
    second = await actions_bridge._render_professional_outputs_for_job(
        job_id=job_id,
        outputs=outputs,
        artifact_namespace="candidate-shared",
        slot_override=object(),
    )

    assert calls == ["candidate-shared", "candidate-shared"]
    assert first["delivery_receipt"] != second["delivery_receipt"]
    first_receipt = json.loads(Path(first["delivery_receipt"]).read_text(encoding="utf-8"))
    second_receipt = json.loads(Path(second["delivery_receipt"]).read_text(encoding="utf-8"))
    assert first_receipt["job_id"] == second_receipt["job_id"] == job_id
    assert "candidate-shared" in Path(first["delivery_receipt"]).name


@pytest.mark.asyncio
async def test_professional_rerender_is_unique_and_stale_cas_cannot_overwrite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge

    job_id = "c" * 32
    job, result, variants = _formal_delivery_fixture(tmp_path, job_id=job_id)
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, result, {"variants": variants}, variants),
    )

    async def fake_admission():
        return object()

    namespaces: list[str] = []

    async def fake_render(*, job_id, variant, artifact_namespace, **_kwargs):
        namespaces.append(artifact_namespace)
        return _write_rendered_variant(
            tmp_path,
            job_id=job_id,
            variant=variant,
            stem=f"rerender-{len(namespaces)}",
        )

    cas_calls: list[dict] = []

    def stale_transition(_job_id, **kwargs):
        cas_calls.append(kwargs)

    monkeypatch.setattr(
        actions_bridge,
        "_admit_current_server_route_for_existing_evidence",
        fake_admission,
    )
    monkeypatch.setattr(actions_bridge, "render_professional_document", fake_render)
    monkeypatch.setattr(actions_bridge, "transition_job", stale_transition)

    with patch.dict(
        "os.environ",
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ), pytest.raises(HTTPException) as exc_info:
        await actions_bridge.actions_professional_render(
            actions_bridge.ActionsProfessionalRenderRequest(
                job_id=job_id,
                variant=1,
            ),
            x_actions_key="test-actions-key",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "STALE_PROMOTION"
    assert len(namespaces) == 1
    assert namespaces[0].startswith(f"{job_id}-rerender-v1-")
    assert cas_calls[0]["expected_revision"] == 17
    assert cas_calls[0]["allowed_from"] == {"succeeded"}


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda revision: revision.update(schema_version="review-revision-v0"), "schema_mismatch"),
        (lambda revision: revision.update(snapshot_digest=""), "snapshot_seal_missing"),
        (lambda revision: revision.update(variant_count=99), "variant_count_mismatch"),
        (
            lambda revision: revision["variants"][0].update(variant_id=999),
            "variant_identity_mismatch",
        ),
        (
            lambda revision: revision["variants"][0].update(delivery_ready=False),
            "restored_delivery_not_ready",
        ),
    ],
)
def test_rollback_snapshot_identity_fails_closed_before_candidate_writes(
    tmp_path: Path,
    mutation,
    reason: str,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    job, result, variants = _formal_delivery_fixture(tmp_path, variant_ids=(41,))
    revision_root = tmp_path / "revisions"
    original_root = review_revision.REVISION_ROOT
    review_revision.REVISION_ROOT = revision_root
    try:
        snapshot = review_revision.create_revision_snapshot(
            job_id=job["job_id"],
            variants=copy.deepcopy(variants),
            result=result,
            reason="pre_review_apply",
        )
        revision = review_revision.load_revision_snapshot(
            job_id=job["job_id"],
            revision_id=snapshot["revision_id"],
        )
    finally:
        review_revision.REVISION_ROOT = original_root
    mutation(revision)

    with pytest.raises(HTTPException) as exc_info:
        actions_bridge._validate_rollback_snapshot(
            revision=revision,
            current_job=job,
            current_result=result,
            current_variants=variants,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "ROLLBACK_SNAPSHOT_INVALID"
    assert exc_info.value.detail["reason"] == reason


@pytest.mark.asyncio
async def test_rollback_route_validates_snapshot_before_any_candidate_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan.review_revision import result_version

    job_id = "e" * 32
    job, result, variants = _formal_delivery_fixture(
        tmp_path,
        job_id=job_id,
        variant_ids=(51,),
    )
    invalid_revision = {
        "schema_version": "review-revision-v1",
        "snapshot_digest": "sealed-by-loader",
        "variant_count": 1,
        "variants": [dict(variants[0], variant_id=999)],
    }
    monkeypatch.setattr(
        actions_bridge,
        "_load_done_job_variants",
        lambda _job_id: (job, result, {"variants": variants}, variants),
    )
    monkeypatch.setattr(
        actions_bridge,
        "load_revision_snapshot",
        lambda **_kwargs: invalid_revision,
    )
    writes: list[str] = []
    monkeypatch.setattr(
        actions_bridge,
        "create_revision_snapshot",
        lambda **_kwargs: writes.append("snapshot"),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_save_outputs",
        lambda *_args, **_kwargs: writes.append("save"),
    )

    async def forbidden_render(**_kwargs):
        writes.append("render")

    monkeypatch.setattr(
        actions_bridge,
        "_render_professional_outputs_for_job",
        forbidden_render,
    )
    request = actions_bridge.ActionsReviewRollbackRequest(
        job_id=job_id,
        revision_id="REV-invalid",
        expected_result_version=result_version(variants),
    )
    with patch.dict(
        "os.environ",
        {"ZF_ACTIONS_KEY": "test-actions-key"},
        clear=False,
    ), pytest.raises(HTTPException) as exc_info:
        await actions_bridge.actions_review_rollback(
            request,
            x_actions_key="test-actions-key",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "ROLLBACK_SNAPSHOT_INVALID"
    assert writes == []


def test_promotion_cas_checks_transition_return(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    monkeypatch.setattr(actions_bridge, "transition_job", lambda *_args, **_kwargs: None)
    with pytest.raises(HTTPException) as exc_info:
        actions_bridge._promote_job_result_cas(
            job_id="d" * 32,
            initial_status="done",
            initial_revision=9,
            result={"delivery_profile": "sonnet5_professional_word"},
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "STALE_PROMOTION"


def test_two_phase_prepare_failure_leaves_live_job_untouched(monkeypatch) -> None:
    from backend.app.routers import actions_bridge

    cas_calls: list[dict] = []
    monkeypatch.setattr(
        actions_bridge,
        "prepare_revision_promotion",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    monkeypatch.setattr(
        actions_bridge,
        "_promote_job_result_cas",
        lambda **kwargs: cas_calls.append(kwargs),
    )
    with pytest.raises(HTTPException) as exc_info:
        actions_bridge._promote_review_candidate_two_phase(
            job_id="f" * 32,
            revision_id="REV-prepare-failure",
            initial_status="succeeded",
            initial_revision=20,
            result={"delivery_profile": "sonnet5_professional_word"},
            promotion={"candidate_artifact_digest": "1" * 64, "artifacts": []},
        )
    assert exc_info.value.detail["code"] == "PROMOTION_AUDIT_PREPARE_FAILED"
    assert cas_calls == []


def test_two_phase_stale_cas_never_marks_snapshot_promoted(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    created = review_revision.create_revision_snapshot(
        job_id="job-stale-two-phase",
        variants=[{"variant_id": 1, "sections": []}],
        result={},
        reason="pre_review_apply",
    )

    def stale_cas(**_kwargs):
        raise HTTPException(
            status_code=409,
            detail={"code": "STALE_PROMOTION", "message": "stale"},
        )

    monkeypatch.setattr(actions_bridge, "_promote_job_result_cas", stale_cas)
    result: dict[str, object] = {}
    with pytest.raises(HTTPException) as exc_info:
        actions_bridge._promote_review_candidate_two_phase(
            job_id="job-stale-two-phase",
            revision_id=created["revision_id"],
            initial_status="succeeded",
            initial_revision=21,
            result=result,
            promotion={"candidate_artifact_digest": "2" * 64, "artifacts": []},
        )
    assert exc_info.value.detail["code"] == "STALE_PROMOTION"
    loaded = review_revision.load_revision_snapshot(
        job_id="job-stale-two-phase",
        revision_id=created["revision_id"],
    )
    assert loaded["promotion"]["state"] == "candidate_prepared"
    assert "promoted_at" not in loaded["promotion"]
    assert "committed_at" not in loaded["promotion"]
    assert result["promotion_audit_receipt"] == created["path"]


def test_two_phase_commit_failure_is_explicitly_pending_and_recoverable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge
    from backend.zhifei_autoplan import review_revision

    monkeypatch.setattr(review_revision, "REVISION_ROOT", tmp_path / "revisions")
    created = review_revision.create_revision_snapshot(
        job_id="job-pending-two-phase",
        variants=[{"variant_id": 1, "sections": []}],
        result={},
        reason="pre_review_rollback",
    )
    monkeypatch.setattr(
        actions_bridge,
        "_promote_job_result_cas",
        lambda **_kwargs: {"status": "succeeded", "revision": 31},
    )
    monkeypatch.setattr(
        actions_bridge,
        "commit_revision_promotion",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("commit write failed")),
    )
    result: dict[str, object] = {}
    with pytest.raises(HTTPException) as exc_info:
        actions_bridge._promote_review_candidate_two_phase(
            job_id="job-pending-two-phase",
            revision_id=created["revision_id"],
            initial_status="succeeded",
            initial_revision=30,
            result=result,
            promotion={"candidate_artifact_digest": "3" * 64, "artifacts": []},
        )
    assert exc_info.value.detail["code"] == "PROMOTION_AUDIT_COMMIT_PENDING"
    assert exc_info.value.detail["job_promotion_committed"] is True
    assert exc_info.value.detail["promoted_job_revision"] == 31
    loaded = review_revision.load_revision_snapshot(
        job_id="job-pending-two-phase",
        revision_id=created["revision_id"],
    )
    assert loaded["promotion"]["state"] == "candidate_prepared"
    assert loaded["promotion"]["candidate_artifact_digest"] == "3" * 64
    assert loaded["promotion"]["expected_job_revision"] == 30
    assert loaded["promotion"]["expected_promoted_job_revision"] == 31
    assert loaded["promotion"]["recovery"]["operation"] == (
        "commit_prepared_promotion_after_job_cas_verification"
    )
    assert result["promotion_audit_receipt"] == created["path"]


def test_invalid_acquired_lease_identity_does_not_call_undefined_side_effect(
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge

    checkpoint_calls: list[str] = []
    transition_calls: list[dict] = []
    monkeypatch.setattr(
        actions_bridge,
        "acquire_job_lease",
        lambda _job_id: {"attempt_id": "", "owner_instance_id": ""},
    )
    monkeypatch.setattr(
        actions_bridge,
        "get_job",
        lambda _job_id: {
            "job_id": _job_id,
            "status": "running",
            "payload": {"delivery_scope": "document"},
        },
    )
    monkeypatch.setattr(
        actions_bridge,
        "_seal_failed_run_checkpoints",
        lambda _job_id: checkpoint_calls.append(_job_id),
    )
    monkeypatch.setattr(
        actions_bridge,
        "transition_job",
        lambda _job_id, **kwargs: transition_calls.append(kwargs),
    )

    actions_bridge.run_actions_generation_job("invalid-lease-job", {})

    assert checkpoint_calls == []
    assert transition_calls == []


@pytest.mark.parametrize("case", ("malformed", "symlink", "oversized"))
def test_done_job_result_json_is_bounded_regular_and_fail_closed(
    tmp_path: Path,
    monkeypatch,
    case: str,
) -> None:
    from backend.app.routers import actions_bridge

    result_path = tmp_path / "result.json"
    if case == "malformed":
        result_path.write_bytes(b"{not-json")
    elif case == "symlink":
        target = tmp_path / "target.json"
        target.write_text('{"variants":[{}]}', encoding="utf-8")
        result_path.symlink_to(target)
    else:
        with result_path.open("wb") as stream:
            stream.truncate(actions_bridge._MAX_FORMAL_RUNTIME_JSON_BYTES + 1)

        def forbidden_read(*_args, **_kwargs):
            raise AssertionError("oversized result body must not be read")

        monkeypatch.setattr(actions_bridge.os, "read", forbidden_read)

    monkeypatch.setattr(
        actions_bridge,
        "get_job",
        lambda _job_id: {
            "job_id": _job_id,
            "status": "succeeded",
            "result": {"json": str(result_path)},
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        actions_bridge._load_done_job_variants("a" * 32)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "RESULT_JSON_UNTRUSTED"


@pytest.mark.asyncio
async def test_result_endpoint_rejects_malformed_result_with_stable_machine_code(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from backend.app.routers import actions_bridge

    result_path = tmp_path / "result.json"
    result_path.write_bytes(b"{not-json")
    monkeypatch.setattr(actions_bridge, "_auth_actions_key", lambda _key: None)
    monkeypatch.setattr(
        actions_bridge,
        "get_job",
        lambda _job_id: {
            "job_id": _job_id,
            "status": "succeeded",
            "result": {"json": str(result_path)},
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        await actions_bridge.actions_result(job_id="a" * 32)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "RESULT_JSON_UNTRUSTED"
