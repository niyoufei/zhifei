from __future__ import annotations

from backend.zhifei_autoplan.compliance_policy import (
    DEFAULT_GLOBAL_INSTRUCTION,
    LEGACY_GLOBAL_INSTRUCTION,
    PROJECT_STANDARD_RECORD_FIELDS,
    audit_standard_citations,
    build_project_applicable_standards_manifest,
    build_standard_registry_map,
    canonical_standard_code,
    extract_standard_codes,
    filter_evidence_to_verified_standard_codes,
    is_verified_standard_metadata,
    is_versioned_standard_code,
    replace_unverified_standard_citations,
    should_migrate_global_instruction,
    standard_citation_directive,
)


def _verified_hit(**overrides):
    hit = {
        "standard_code": "GB_50300_2024",
        "source_name": "建筑工程施工质量验收统一标准",
        "official_source": "https://official.example/GB_50300_2024",
        "effective_status": "active",
        "current_version": "GB_50300_2024",
        "latest": True,
        "domain_tags": ["房建工程"],
        "metadata_only": True,
        "verified": True,
        "official_registry_verified": True,
        "clause_no": "5.0.1",
        "tender_evidence_locations": ["tender.pdf#sha@120"],
        "priority": "工程建设强制性规范",
        "conflicts": [],
    }
    hit.update(overrides)
    return hit


def test_global_instruction_replaces_legacy_fixed_count_claim():
    assert "16条" not in DEFAULT_GLOBAL_INSTRUCTION
    assert "未核验的规范不得引用或编造" in DEFAULT_GLOBAL_INSTRUCTION
    assert should_migrate_global_instruction(LEGACY_GLOBAL_INSTRUCTION) is True
    assert should_migrate_global_instruction(DEFAULT_GLOBAL_INSTRUCTION) is False


def test_manifest_has_required_project_standard_fields_and_no_fixed_count():
    manifest = build_project_applicable_standards_manifest(
        [
            {
                "title": "质量管理",
                "compliance_hits": [_verified_hit()],
            }
        ]
    )
    assert manifest["fixed_count_required"] is False
    assert manifest["required_fields"] == list(PROJECT_STANDARD_RECORD_FIELDS)
    assert manifest["verified_count"] == 1
    row = manifest["verified_standards"][0]
    assert row["eligible_for_citation"] is True
    assert row["applicable_specialties_and_chapters"]["chapters"] == ["质量管理"]
    assert row["tender_evidence_locations"] == ["tender.pdf#sha@120"]


def test_manifest_rejects_missing_official_source():
    manifest = build_project_applicable_standards_manifest(
        [{"title": "安全管理", "compliance_hits": [_verified_hit(official_source="")]}]
    )
    assert manifest["verified_count"] == 0
    assert manifest["unverified_count"] == 1
    assert manifest["unverified_candidates"][0]["eligible_for_citation"] is False


def test_manifest_does_not_launder_non_authoritative_mutable_clause() -> None:
    mutable_hit = _verified_hit(
        metadata_only=False,
        verified=False,
        official_registry_verified=True,
        clause_source_authoritative=False,
        locator="mutable.json#node-1",
        text="施工质量应形成验收记录。",
    )
    manifest = build_project_applicable_standards_manifest(
        [{"title": "质量管理", "compliance_hits": [mutable_hit]}]
    )

    assert manifest["verified_count"] == 0
    assert manifest["unverified_count"] == 1
    assert manifest["unverified_candidates"][0]["eligible_for_citation"] is False


def test_manifest_keeps_sealed_metadata_as_applicable_standard() -> None:
    manifest = build_project_applicable_standards_manifest(
        [{"title": "项目适用规范清单", "compliance_hits": [_verified_hit()]}]
    )

    assert manifest["verified_count"] == 1
    assert manifest["verified_standards"][0]["eligible_for_citation"] is True
    assert manifest["verified_standards"][0]["mandatory_clauses"] == ["5.0.1"]


def test_verified_metadata_requires_current_version():
    assert is_verified_standard_metadata(_verified_hit(current_version="")) is False
    assert is_verified_standard_metadata(_verified_hit(current_version="2024")) is False
    assert (
        is_verified_standard_metadata(
            _verified_hit(current_version="GB_50300_2013")
        )
        is False
    )


def test_writer_directive_is_an_explicit_allowlist():
    directive = standard_citation_directive([_verified_hit()])
    assert "GB_50300_2024" in directive
    assert "只允许引用" in directive
    assert "不得" in directive


def test_evidence_filter_drops_lines_with_unverified_standard_codes():
    result = filter_evidence_to_verified_standard_codes(
        [
            "按 GB 50300-2024 形成验收记录。",
            "按 CJJ 1-2008 组织道路验收。",
            "招标文件要求保留旁站记录。",
        ],
        ["GB_50300_2024"],
    )
    assert result["lines"] == [
        "按 GB 50300-2024 形成验收记录。",
        "招标文件要求保留旁站记录。",
    ]
    assert result["dropped_count"] == 1
    assert result["dropped"][0]["standard_codes"] == ["CJJ 1-2008"]


def test_final_sanitizer_keeps_verified_and_neutralizes_unverified_codes():
    result = replace_unverified_standard_citations(
        "执行 GB 50300-2024，并参照 CJJ 1-2008 完成检查。",
        ["GB_50300_2024"],
    )
    assert result["changed"] is True
    assert result["removed_codes"] == ["CJJ 1-2008"]
    assert "GB 50300-2024" in result["text"]
    assert "CJJ 1-2008" not in result["text"]
    assert "项目适用规范清单中的已核验现行标准" in result["text"]


def test_citation_audit_accepts_verified_code_format_variants():
    sections = [
        {
            "title": "质量管理",
            "content": "质量验收执行 GB 50300-2024，并记录复核结果。",
            "compliance_hits": [_verified_hit()],
        }
    ]
    manifest = build_project_applicable_standards_manifest(sections)
    audit = audit_standard_citations(sections, manifest)
    assert audit["ok"] is True
    assert audit["violation_count"] == 0
    assert audit["verified_standard_count"] == 1
    assert audit["verified_standard_codes"] == ["GB_50300_2024"]


def test_citation_audit_blocks_unverified_code_and_unresolved_conflict():
    sections = [
        {
            "title": "质量管理",
            "content": "质量验收执行 GB 50204-2015。",
            "compliance_hits": [_verified_hit(conflicts=["与招标文件第3.2条冲突"])],
        }
    ]
    manifest = build_project_applicable_standards_manifest(sections)
    audit = audit_standard_citations(sections, manifest)
    assert audit["ok"] is False
    reasons = {row["reason"] for row in audit["violations"]}
    assert "standard_not_in_verified_project_manifest" in reasons
    assert "unresolved_standard_conflict" in reasons


def test_strict_standard_code_supports_jtg_t_and_optional_gb_space():
    assert is_versioned_standard_code("JTG/T 3650-2020") is True
    assert is_versioned_standard_code("JTG/T 3660-2020") is True
    assert is_versioned_standard_code("GB55037-2022") is True
    assert canonical_standard_code("GB55037-2022") == canonical_standard_code(
        "GB 55037-2022"
    )
    assert extract_standard_codes(
        "执行 JTG/T 3650-2020 与 JTG/T 3660-2020。"
    ) == ["JTG/T 3650-2020", "JTG/T 3660-2020"]


def test_strict_standard_code_supports_jtg_volume_and_railway_codes():
    codes = (
        "JTG F80/1-2017",
        "TB 10302-2020",
        "TB 10304-2020",
        "TB 10424-2018",
    )
    assert all(is_versioned_standard_code(code) for code in codes)
    assert extract_standard_codes("执行 " + "、".join(codes) + "。") == list(codes)
    assert canonical_standard_code("JTGF80/1-2017") == canonical_standard_code(
        "JTG F80/1-2017"
    )


def test_strict_standard_code_rejects_ocr_noise_and_malformed_bodies():
    for value in (
        "JTG/T",
        "JTG/T 3650",
        "JTG/T 3650-20",
        "GB BAD1-2022",
        "GB 12 FOO-2022",
        "JTG F80/-2017",
        "JTG F80/ABC-2017",
        "TB BAD1-2020",
        "Dll",
        "HY TR",
    ):
        assert is_versioned_standard_code(value) is False
    assert extract_standard_codes(
        "TB 10302-2020-X；TB 10302-2020.1；JTG F80/1-2017-X"
    ) == []


def test_identity_without_cover_policy_requires_valid_official_pin():
    base = _verified_hit(
        standard_code="GB 55032-2022",
        current_version="GB 55032-2022",
        official_identity_without_cover=True,
    )
    assert is_verified_standard_metadata(base) is False
    assert (
        is_verified_standard_metadata(
            {
                **base,
                "official_document_url": "https://example.gov.cn/gb55032.pdf",
                "official_content_sha256": "a" * 64,
            }
        )
        is True
    )


def test_registry_duplicate_conflicting_pin_or_identity_policy_is_ambiguous():
    first = _verified_hit(
        standard_code="GB 55032-2022",
        current_version="GB 55032-2022",
        official_document_url="https://example.gov.cn/a.pdf",
        official_content_sha256="a" * 64,
        official_identity_without_cover=True,
    )
    for override in (
        {"official_content_sha256": "b" * 64},
        {"official_document_url": "https://example.gov.cn/b.pdf"},
        {"official_identity_without_cover": False},
    ):
        registry = build_standard_registry_map([first, {**first, **override}])
        assert registry["GB_55032_2022"]["_registry_ambiguous"] is True
