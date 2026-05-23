"""Docs-only draft for disabled KG entity pair static checks.

This file is intentionally inert:
- no shebang
- no CLI entry
- no file reads
- no file writes
- no service, endpoint, Ollama, CI, or ZDoc runtime integration

The functions below describe a future offline static validation shape. Callers
would have to provide already-loaded dictionaries and explicit docs paths.
"""

EXPECTED_MANIFEST_ENTITY_PATH = (
    "docs/kg-controlled-entities/"
    "zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.manifest.entity.json"
)
EXPECTED_REGISTRY_ENTITY_PATH = (
    "docs/kg-controlled-entities/"
    "zdoc-kg-pilot-qn-index-municipal-bridge-kg01.disabled.registry.entity.json"
)

MANIFEST_FALSE_FIELDS = (
    "enabled",
    "runtime_loadable",
    "rag_loadable",
    "prompt_registry_loadable",
    "system_instruction_loadable",
    "evidence_allowed",
    "scoring_allowed",
)

REGISTRY_FALSE_FIELDS = (
    "enabled",
    "runtime_loadable",
    "registry_loadable",
    "rag_loadable",
    "prompt_registry_loadable",
    "system_instruction_loadable",
    "evidence_allowed",
    "scoring_allowed",
)


def draft_validate_disabled_entity_pair(
    manifest_entity,
    registry_entity,
    manifest_entity_path,
    registry_entity_path,
):
    """Return a draft static validation result for already-supplied data.

    This draft does not load JSON files. It only expresses the field checks that
    a future separately authorized offline validator could perform.
    """
    issues = []

    _expect_path(issues, "manifest_entity_path", manifest_entity_path, EXPECTED_MANIFEST_ENTITY_PATH)
    _expect_path(issues, "registry_entity_path", registry_entity_path, EXPECTED_REGISTRY_ENTITY_PATH)

    _expect_value(issues, "manifest.registration_status", manifest_entity, "registration_status", "not_registered")
    _expect_value(issues, "registry.registration_status", registry_entity, "registration_status", "not_registered")

    for field in MANIFEST_FALSE_FIELDS:
        _expect_false(issues, "manifest." + field, manifest_entity, field)

    for field in REGISTRY_FALSE_FIELDS:
        _expect_false(issues, "registry." + field, registry_entity, field)

    _expect_path(
        issues,
        "registry.linked_manifest_entity_path",
        registry_entity.get("linked_manifest_entity_path"),
        manifest_entity_path,
    )
    _expect_path(
        issues,
        "registry.linked_manifest_candidate_path",
        registry_entity.get("linked_manifest_candidate_path"),
        manifest_entity.get("created_from_path"),
    )
    _expect_path(
        issues,
        "manifest.linked_registry_candidate_path",
        manifest_entity.get("linked_registry_candidate_path"),
        registry_entity.get("created_from_path"),
    )

    status = "pass" if not issues else "fail"
    return {
        "draft_only": True,
        "runtime_executed": False,
        "validation_status": status,
        "issues": issues,
        "checked_paths": {
            "manifest_entity_path": manifest_entity_path,
            "registry_entity_path": registry_entity_path,
        },
    }


def _expect_path(issues, label, actual, expected):
    if actual != expected:
        issues.append(
            {
                "check": label,
                "expected": expected,
                "actual": actual,
            }
        )


def _expect_value(issues, label, record, field, expected):
    actual = record.get(field)
    if actual != expected:
        issues.append(
            {
                "check": label,
                "expected": expected,
                "actual": actual,
            }
        )


def _expect_false(issues, label, record, field):
    actual = record.get(field)
    if actual is not False:
        issues.append(
            {
                "check": label,
                "expected": False,
                "actual": actual,
            }
        )
