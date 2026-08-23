"""C1 Route C canonical foundation and project-material facade."""

from .common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_JSON_ALGORITHM,
    CANONICAL_PROFILE_ID,
    CanonicalError,
    DiagnosticV1,
    canonical_json_bytes,
    canonical_set_array,
    derive_revision_id,
    derive_stable_id,
    effective_source_mode,
    first_error_diagnostic,
    profile_digest,
)
from .material import (
    ParserIdentityV1,
    ProjectMaterialBundleV1,
    ProjectMaterialInputV1,
    ProjectMaterialProvenanceV1,
    SourceLocatorV1,
)
from .material_adapter import (
    DeterministicParserRegistryV1,
    MaterialAdapterInputV1,
    MaterialAdapterResultV1,
    ParserRegistrationV1,
    adapt_project_material,
)

__all__ = [
    "BOOTSTRAP_RULE_ID",
    "CANONICAL_JSON_ALGORITHM",
    "CANONICAL_PROFILE_ID",
    "CanonicalError",
    "DiagnosticV1",
    "DeterministicParserRegistryV1",
    "MaterialAdapterInputV1",
    "MaterialAdapterResultV1",
    "ParserIdentityV1",
    "ParserRegistrationV1",
    "ProjectMaterialBundleV1",
    "ProjectMaterialInputV1",
    "ProjectMaterialProvenanceV1",
    "SourceLocatorV1",
    "adapt_project_material",
    "canonical_json_bytes",
    "canonical_set_array",
    "derive_revision_id",
    "derive_stable_id",
    "effective_source_mode",
    "first_error_diagnostic",
    "profile_digest",
]
