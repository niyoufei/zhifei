"""Pure C4 chapter-generation request and chapter-set foundations.

The module is a deterministic handoff boundary.  It canonicalizes explicit
inputs and explicit generated chapter values, but never invokes a model,
persists a record, exports a document, or treats generated text as evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, Final
import re

from .common import (
    BOOTSTRAP_RULE_ID,
    CANONICAL_PROFILE_ID,
    CanonicalError,
    canonical_json_bytes,
    derive_revision_id,
    derive_stable_id,
    effective_source_mode,
    identities_equal,
    normalize_source_modes,
    normalize_text,
    profile_digest,
    require_no_source_mode_promotion,
    validate_digest,
)
from .evidence import ResponseEvidenceSetV2
from .scoring import SourceProvenanceReferenceV1


_CHAPTER_KEY_RE: Final = re.compile(r"^[a-z][a-z0-9-]*$")
_RESPONSE_SET_STABLE_PREFIX: Final = "ocrc:response-evidence-set:"
_RESPONSE_SET_REVISION_PREFIX: Final = "ocrc-rev:response-evidence-set:"


def _nonempty(value: str, field_name: str, *, human_text: bool = False) -> str:
    value = normalize_text(value, human_text=human_text)
    if not value:
        raise CanonicalError("SCHEMA_VIOLATION", f"{field_name} must be non-empty")
    return value


def _prefixed_identity(value: str, prefix: str, field_name: str) -> str:
    value = normalize_text(value)
    if not value.startswith(prefix):
        raise CanonicalError("REF_TARGET_MISSING", f"{field_name} has the wrong artifact type")
    validate_digest(value[len(prefix) :])
    return value


def _ordered_source_references(
    values: Sequence[SourceProvenanceReferenceV1],
) -> tuple[SourceProvenanceReferenceV1, ...]:
    references = tuple(values)
    if not references or any(not isinstance(item, SourceProvenanceReferenceV1) for item in references):
        raise CanonicalError(
            "REF_TARGET_MISSING",
            "source_references must contain canonical project-material references",
        )
    ordered = tuple(sorted(references, key=lambda item: canonical_json_bytes(item.to_dict())))
    encoded = tuple(canonical_json_bytes(item.to_dict()) for item in ordered)
    if len(set(encoded)) != len(encoded):
        raise CanonicalError("SCHEMA_VIOLATION", "source_references must be unique")
    return ordered


def _merged_source_references(
    groups: Sequence[Sequence[SourceProvenanceReferenceV1]],
) -> tuple[SourceProvenanceReferenceV1, ...]:
    unique: dict[bytes, SourceProvenanceReferenceV1] = {}
    for group in groups:
        for item in group:
            if not isinstance(item, SourceProvenanceReferenceV1):
                raise CanonicalError(
                    "REF_TARGET_MISSING",
                    "source provenance must remain a project-material reference",
                )
            unique[canonical_json_bytes(item.to_dict())] = item
    return _ordered_source_references(tuple(unique.values()))


@dataclass(frozen=True, slots=True)
class ResponseEvidenceSetReferenceV2:
    """Accepted, identity-verified C3 input projected into a C4 request."""

    stable_id: str
    revision_id: str
    record_sha256: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stable_id",
            _prefixed_identity(self.stable_id, _RESPONSE_SET_STABLE_PREFIX, "stable_id"),
        )
        object.__setattr__(
            self,
            "revision_id",
            _prefixed_identity(self.revision_id, _RESPONSE_SET_REVISION_PREFIX, "revision_id"),
        )
        object.__setattr__(self, "record_sha256", validate_digest(self.record_sha256))
        object.__setattr__(
            self,
            "source_references",
            _ordered_source_references(self.source_references),
        )

    @classmethod
    def from_evidence_set(cls, value: ResponseEvidenceSetV2) -> "ResponseEvidenceSetReferenceV2":
        if not isinstance(value, ResponseEvidenceSetV2) or not value.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "response evidence identity is invalid")
        if value.accepted_for_response_use is not True:
            raise CanonicalError(
                "REVIEW_ACCEPTANCE_REQUIRED",
                "response evidence must be accepted before grounded generation",
            )
        sources = _merged_source_references(
            tuple(item.source_references for item in value.evidence_items)
        )
        return cls(value.stable_id, value.revision_id, value.record_sha256, sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_for_response_use": True,
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "source_references": [item.to_dict() for item in self.source_references],
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class ChapterGenerationRequestProvenanceV1:
    bootstrap_rule_id: str
    source_mode_set: tuple[str, ...]
    source_references: tuple[SourceProvenanceReferenceV1, ...]
    response_evidence_refs: tuple[ResponseEvidenceSetReferenceV2, ...]

    @classmethod
    def create(
        cls,
        *,
        source_mode_set: Sequence[str],
        source_references: Sequence[SourceProvenanceReferenceV1],
        response_evidence_refs: Sequence[ResponseEvidenceSetReferenceV2],
    ) -> "ChapterGenerationRequestProvenanceV1":
        modes = normalize_source_modes(source_mode_set)
        sources = _ordered_source_references(source_references)
        evidence = tuple(
            sorted(response_evidence_refs, key=lambda item: canonical_json_bytes(item.to_dict()))
        )
        if any(not isinstance(item, ResponseEvidenceSetReferenceV2) for item in evidence):
            raise CanonicalError("REF_TARGET_MISSING", "invalid response evidence reference")
        encoded = tuple(canonical_json_bytes(item.to_dict()) for item in evidence)
        if len(set(encoded)) != len(encoded):
            raise CanonicalError("SCHEMA_VIOLATION", "response_evidence_refs must be unique")
        return cls(BOOTSTRAP_RULE_ID, modes, sources, evidence)

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "bootstrap_rule_id": self.bootstrap_rule_id,
            "effective_source_mode": self.effective_source_mode,
            "response_evidence_refs": [item.to_dict() for item in self.response_evidence_refs],
            "source_mode_set": list(self.source_mode_set),
            "source_references": [item.to_dict() for item in self.source_references],
        }


@dataclass(frozen=True, slots=True)
class ChapterGenerationRequestV1:
    artifact_type: str
    schema_version: str
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    stable_id: str
    revision_id: str
    content_sha256: str
    provenance_sha256: str
    record_sha256: str
    generation_index: int
    generation_phase: str
    parent_chapter_revision_id: str | None
    response_evidence_refs: tuple[ResponseEvidenceSetReferenceV2, ...]
    provenance: ChapterGenerationRequestProvenanceV1

    ARTIFACT_TYPE: ClassVar[str] = "chapter-generation-request"
    SCHEMA_VERSION: ClassVar[str] = "1"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(
        cls,
        *,
        origin_namespace: str,
        origin_key: str,
        origin_source_mode: str,
        source_mode_set: Sequence[str],
        source_references: Sequence[SourceProvenanceReferenceV1],
        generation_index: int,
        generation_phase: str,
        parent_chapter_set: ChapterSetV1 | None = None,
        response_evidence_sets: Sequence[ResponseEvidenceSetV2] = (),
    ) -> "ChapterGenerationRequestV1":
        namespace = _nonempty(origin_namespace, "origin_namespace")
        key = _nonempty(origin_key, "origin_key")
        origin_mode = normalize_source_modes((origin_source_mode,))[0]
        modes = normalize_source_modes(source_mode_set)
        if not isinstance(generation_index, int) or isinstance(generation_index, bool):
            raise CanonicalError("SCHEMA_VIOLATION", "generation_index must be an integer")
        phase = normalize_text(generation_phase)
        evidence_sets = tuple(response_evidence_sets)

        if phase == "INITIAL":
            if generation_index != 0 or parent_chapter_set is not None or evidence_sets:
                raise CanonicalError(
                    "BOOTSTRAP_CYCLE_FORBIDDEN",
                    "INITIAL generation requires index zero, no parent, and no response evidence",
                )
            parent_revision_id = None
            evidence_refs: tuple[ResponseEvidenceSetReferenceV2, ...] = ()
            inherited_sources: tuple[SourceProvenanceReferenceV1, ...] = ()
        elif phase == "GROUNDED":
            if not isinstance(parent_chapter_set, ChapterSetV1) or not parent_chapter_set.verify_identity():
                raise CanonicalError("REF_TARGET_MISSING", "grounded generation requires a verified parent")
            if (
                parent_chapter_set.review_state != "PROVISIONAL"
                or parent_chapter_set.accepted_for_response_use is not False
            ):
                raise CanonicalError("REVIEW_STATE_INVALID", "grounded parent must be provisional")
            if generation_index <= parent_chapter_set.generation_index:
                raise CanonicalError(
                    "BOOTSTRAP_CYCLE_FORBIDDEN",
                    "grounded generation_index must be greater than its parent",
                )
            if not evidence_sets:
                raise CanonicalError(
                    "REVIEW_ACCEPTANCE_REQUIRED",
                    "grounded generation requires accepted response evidence",
                )
            evidence_refs = tuple(
                sorted(
                    (ResponseEvidenceSetReferenceV2.from_evidence_set(item) for item in evidence_sets),
                    key=lambda item: canonical_json_bytes(item.to_dict()),
                )
            )
            encoded_evidence = tuple(canonical_json_bytes(item.to_dict()) for item in evidence_refs)
            if len(set(encoded_evidence)) != len(encoded_evidence):
                raise CanonicalError("SCHEMA_VIOLATION", "response evidence revisions must be unique")
            require_no_source_mode_promotion(
                parent_chapter_set.provenance.source_mode_set,
                modes,
            )
            for item in evidence_sets:
                require_no_source_mode_promotion(item.provenance.source_mode_set, modes)
            parent_revision_id = parent_chapter_set.revision_id
            inherited_sources = _merged_source_references(
                (
                    parent_chapter_set.provenance.source_references,
                    *(item.source_references for item in evidence_refs),
                )
            )
        else:
            raise CanonicalError("SCHEMA_VIOLATION", "generation_phase must be INITIAL or GROUNDED")

        source_groups: tuple[Sequence[SourceProvenanceReferenceV1], ...] = (
            tuple(source_references),
            inherited_sources,
        )
        sources = _merged_source_references(source_groups)
        provenance = ChapterGenerationRequestProvenanceV1.create(
            source_mode_set=modes,
            source_references=sources,
            response_evidence_refs=evidence_refs,
        )
        content = cls._content_projection(generation_index, phase, parent_revision_id)
        provenance_projection = provenance.to_projection()
        stable_projection = cls._stable_projection(namespace, key, origin_mode)
        content_sha256 = profile_digest(
            "content-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            provenance_projection,
        )
        stable_id = derive_stable_id(cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, stable_projection)
        revision_id = derive_revision_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": parent_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_projection = cls._record_projection(
            origin_namespace=namespace,
            origin_key=key,
            origin_source_mode=origin_mode,
            stable_id=stable_id,
            revision_id=revision_id,
            content_sha256=content_sha256,
            provenance_sha256=provenance_sha256,
            generation_index=generation_index,
            generation_phase=phase,
            parent_chapter_revision_id=parent_revision_id,
            response_evidence_refs=evidence_refs,
            provenance=provenance_projection,
        )
        record_sha256 = profile_digest(
            "record-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, record_projection
        )
        return cls(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            namespace,
            key,
            origin_mode,
            stable_id,
            revision_id,
            content_sha256,
            provenance_sha256,
            record_sha256,
            generation_index,
            phase,
            parent_revision_id,
            evidence_refs,
            provenance,
        )

    @classmethod
    def _stable_projection(cls, namespace: str, key: str, mode: str) -> dict[str, str]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "origin_key": key,
            "origin_namespace": namespace,
            "origin_source_mode": mode,
            "schema_version": cls.SCHEMA_VERSION,
        }

    @staticmethod
    def _content_projection(
        generation_index: int,
        generation_phase: str,
        parent_chapter_revision_id: str | None,
    ) -> dict[str, Any]:
        return {
            "generation_index": generation_index,
            "generation_phase": generation_phase,
            "parent_chapter_revision_id": parent_chapter_revision_id,
        }

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "content_sha256": values["content_sha256"],
            "generation_index": values["generation_index"],
            "generation_phase": values["generation_phase"],
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_chapter_revision_id": values["parent_chapter_revision_id"],
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "response_evidence_refs": [item.to_dict() for item in values["response_evidence_refs"]],
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        content = self._content_projection(
            self.generation_index,
            self.generation_phase,
            self.parent_chapter_revision_id,
        )
        provenance = self.provenance.to_projection()
        content_sha256 = profile_digest(
            "content-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, provenance
        )
        stable_id = derive_stable_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._stable_projection(
                self.origin_namespace,
                self.origin_key,
                self.origin_source_mode,
            ),
        )
        revision_id = derive_revision_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": self.parent_chapter_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_sha256 = profile_digest(
            "record-sha256",
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._record_projection(
                origin_namespace=self.origin_namespace,
                origin_key=self.origin_key,
                origin_source_mode=self.origin_source_mode,
                stable_id=stable_id,
                revision_id=revision_id,
                content_sha256=content_sha256,
                provenance_sha256=provenance_sha256,
                generation_index=self.generation_index,
                generation_phase=self.generation_phase,
                parent_chapter_revision_id=self.parent_chapter_revision_id,
                response_evidence_refs=self.response_evidence_refs,
                provenance=provenance,
            ),
        )
        return all(
            (
                identities_equal(self.content_sha256, content_sha256),
                identities_equal(self.provenance_sha256, provenance_sha256),
                identities_equal(self.stable_id, stable_id),
                identities_equal(self.revision_id, revision_id),
                identities_equal(self.record_sha256, record_sha256),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        value = self._record_projection(
            origin_namespace=self.origin_namespace,
            origin_key=self.origin_key,
            origin_source_mode=self.origin_source_mode,
            stable_id=self.stable_id,
            revision_id=self.revision_id,
            content_sha256=self.content_sha256,
            provenance_sha256=self.provenance_sha256,
            generation_index=self.generation_index,
            generation_phase=self.generation_phase,
            parent_chapter_revision_id=self.parent_chapter_revision_id,
            response_evidence_refs=self.response_evidence_refs,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value


@dataclass(frozen=True, slots=True)
class ChapterContentV1:
    """An explicit generated value, not an evidence artifact or evidence source."""

    chapter_key: str
    title: str
    body: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]

    @classmethod
    def create(
        cls,
        *,
        chapter_key: str,
        title: str,
        body: str,
        source_references: Sequence[SourceProvenanceReferenceV1],
    ) -> "ChapterContentV1":
        key = normalize_text(chapter_key)
        if not _CHAPTER_KEY_RE.fullmatch(key):
            raise CanonicalError("SCHEMA_VIOLATION", "chapter_key must be a lowercase token")
        normalized_title = _nonempty(title, "title", human_text=True)
        normalized_body = _nonempty(body, "body", human_text=True)
        sources = _ordered_source_references(source_references)
        return cls(key, normalized_title, normalized_body, sources)

    def to_content_projection(self) -> dict[str, str]:
        return {
            "body": self.body,
            "chapter_key": self.chapter_key,
            "title": self.title,
        }

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = self.to_content_projection()
        value["source_references"] = [item.to_dict() for item in self.source_references]
        return value


@dataclass(frozen=True, slots=True)
class ChapterGenerationRequestReferenceV1:
    stable_id: str
    revision_id: str
    record_sha256: str

    @classmethod
    def from_request(cls, value: ChapterGenerationRequestV1) -> "ChapterGenerationRequestReferenceV1":
        if not isinstance(value, ChapterGenerationRequestV1) or not value.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "generation request identity is invalid")
        return cls(value.stable_id, value.revision_id, value.record_sha256)

    def to_dict(self) -> dict[str, str]:
        return {
            "record_sha256": self.record_sha256,
            "revision_id": self.revision_id,
            "stable_id": self.stable_id,
        }


@dataclass(frozen=True, slots=True)
class ChapterSetProvenanceV1:
    source_mode_set: tuple[str, ...]
    generation_request: ChapterGenerationRequestReferenceV1
    source_references: tuple[SourceProvenanceReferenceV1, ...]
    chapter_source_references: tuple[
        tuple[str, tuple[SourceProvenanceReferenceV1, ...]], ...
    ]

    @classmethod
    def create(
        cls,
        *,
        request: ChapterGenerationRequestV1,
        chapters: Sequence[ChapterContentV1],
    ) -> "ChapterSetProvenanceV1":
        return cls(
            request.provenance.source_mode_set,
            ChapterGenerationRequestReferenceV1.from_request(request),
            request.provenance.source_references,
            tuple((item.chapter_key, item.source_references) for item in chapters),
        )

    @property
    def effective_source_mode(self) -> str:
        return effective_source_mode(self.source_mode_set)

    def to_projection(self) -> dict[str, Any]:
        return {
            "chapter_source_references": [
                {
                    "chapter_key": chapter_key,
                    "source_references": [item.to_dict() for item in references],
                }
                for chapter_key, references in self.chapter_source_references
            ],
            "effective_source_mode": self.effective_source_mode,
            "generation_request": self.generation_request.to_dict(),
            "source_mode_set": list(self.source_mode_set),
            "source_references": [item.to_dict() for item in self.source_references],
        }


@dataclass(frozen=True, slots=True)
class ChapterSetV1:
    artifact_type: str
    schema_version: str
    origin_namespace: str
    origin_key: str
    origin_source_mode: str
    stable_id: str
    revision_id: str
    parent_revision_id: str | None
    content_sha256: str
    provenance_sha256: str
    record_sha256: str
    generation_index: int
    generation_phase: str
    chapters: tuple[ChapterContentV1, ...]
    provenance: ChapterSetProvenanceV1
    review_state: str
    accepted_for_response_use: bool

    ARTIFACT_TYPE: ClassVar[str] = "chapter-set"
    SCHEMA_VERSION: ClassVar[str] = "1"
    NORMATIVE_PROFILE: ClassVar[str] = CANONICAL_PROFILE_ID

    @classmethod
    def build(
        cls,
        *,
        request: ChapterGenerationRequestV1,
        chapters: Sequence[ChapterContentV1],
    ) -> "ChapterSetV1":
        if not isinstance(request, ChapterGenerationRequestV1) or not request.verify_identity():
            raise CanonicalError("REF_TARGET_MISSING", "request must have a valid C4 identity")
        ordered = tuple(sorted(chapters, key=lambda item: item.chapter_key.encode("utf-8")))
        if not ordered or any(not isinstance(item, ChapterContentV1) for item in ordered):
            raise CanonicalError("SCHEMA_VIOLATION", "chapters must contain canonical values")
        keys = tuple(item.chapter_key for item in ordered)
        if len(set(keys)) != len(keys):
            raise CanonicalError("SCHEMA_VIOLATION", "chapter_key values must be unique")
        allowed = {
            canonical_json_bytes(item.to_dict()) for item in request.provenance.source_references
        }
        for item in ordered:
            actual = {canonical_json_bytes(value.to_dict()) for value in item.source_references}
            if not actual.issubset(allowed):
                raise CanonicalError(
                    "REF_TARGET_MISSING",
                    "chapter source references must come from the generation request",
                )

        content = {"chapters": [item.to_content_projection() for item in ordered]}
        provenance = ChapterSetProvenanceV1.create(request=request, chapters=ordered)
        provenance_projection = provenance.to_projection()
        stable_projection = cls._stable_projection(
            request.origin_namespace,
            request.origin_key,
            request.origin_source_mode,
        )
        content_sha256 = profile_digest(
            "content-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256",
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            provenance_projection,
        )
        stable_id = derive_stable_id(cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, stable_projection)
        revision_id = derive_revision_id(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": request.parent_chapter_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_projection = cls._record_projection(
            origin_namespace=request.origin_namespace,
            origin_key=request.origin_key,
            origin_source_mode=request.origin_source_mode,
            stable_id=stable_id,
            revision_id=revision_id,
            parent_revision_id=request.parent_chapter_revision_id,
            content_sha256=content_sha256,
            provenance_sha256=provenance_sha256,
            generation_index=request.generation_index,
            generation_phase=request.generation_phase,
            chapters=ordered,
            provenance=provenance_projection,
        )
        record_sha256 = profile_digest(
            "record-sha256", cls.ARTIFACT_TYPE, cls.SCHEMA_VERSION, record_projection
        )
        return cls(
            cls.ARTIFACT_TYPE,
            cls.SCHEMA_VERSION,
            request.origin_namespace,
            request.origin_key,
            request.origin_source_mode,
            stable_id,
            revision_id,
            request.parent_chapter_revision_id,
            content_sha256,
            provenance_sha256,
            record_sha256,
            request.generation_index,
            request.generation_phase,
            ordered,
            provenance,
            "PROVISIONAL",
            False,
        )

    @classmethod
    def _stable_projection(cls, namespace: str, key: str, mode: str) -> dict[str, str]:
        return {
            "artifact_type": cls.ARTIFACT_TYPE,
            "origin_key": key,
            "origin_namespace": namespace,
            "origin_source_mode": mode,
            "schema_version": cls.SCHEMA_VERSION,
        }

    @classmethod
    def _record_projection(cls, **values: Any) -> dict[str, Any]:
        return {
            "accepted_for_response_use": False,
            "artifact_type": cls.ARTIFACT_TYPE,
            "chapters": [item.to_dict() for item in values["chapters"]],
            "content_sha256": values["content_sha256"],
            "generation_index": values["generation_index"],
            "generation_phase": values["generation_phase"],
            "origin_key": values["origin_key"],
            "origin_namespace": values["origin_namespace"],
            "origin_source_mode": values["origin_source_mode"],
            "parent_revision_id": values["parent_revision_id"],
            "provenance": values["provenance"],
            "provenance_sha256": values["provenance_sha256"],
            "review_state": "PROVISIONAL",
            "revision_id": values["revision_id"],
            "schema_version": cls.SCHEMA_VERSION,
            "stable_id": values["stable_id"],
        }

    def verify_identity(self) -> bool:
        content = {"chapters": [item.to_content_projection() for item in self.chapters]}
        provenance = self.provenance.to_projection()
        content_sha256 = profile_digest(
            "content-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, content
        )
        provenance_sha256 = profile_digest(
            "provenance-sha256", self.ARTIFACT_TYPE, self.SCHEMA_VERSION, provenance
        )
        stable_id = derive_stable_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._stable_projection(
                self.origin_namespace,
                self.origin_key,
                self.origin_source_mode,
            ),
        )
        revision_id = derive_revision_id(
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            {
                "content_sha256": content_sha256,
                "parent_revision_id": self.parent_revision_id,
                "provenance_sha256": provenance_sha256,
                "stable_id": stable_id,
            },
        )
        record_sha256 = profile_digest(
            "record-sha256",
            self.ARTIFACT_TYPE,
            self.SCHEMA_VERSION,
            self._record_projection(
                origin_namespace=self.origin_namespace,
                origin_key=self.origin_key,
                origin_source_mode=self.origin_source_mode,
                stable_id=stable_id,
                revision_id=revision_id,
                parent_revision_id=self.parent_revision_id,
                content_sha256=content_sha256,
                provenance_sha256=provenance_sha256,
                generation_index=self.generation_index,
                generation_phase=self.generation_phase,
                chapters=self.chapters,
                provenance=provenance,
            ),
        )
        return all(
            (
                identities_equal(self.content_sha256, content_sha256),
                identities_equal(self.provenance_sha256, provenance_sha256),
                identities_equal(self.stable_id, stable_id),
                identities_equal(self.revision_id, revision_id),
                identities_equal(self.record_sha256, record_sha256),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        value = self._record_projection(
            origin_namespace=self.origin_namespace,
            origin_key=self.origin_key,
            origin_source_mode=self.origin_source_mode,
            stable_id=self.stable_id,
            revision_id=self.revision_id,
            parent_revision_id=self.parent_revision_id,
            content_sha256=self.content_sha256,
            provenance_sha256=self.provenance_sha256,
            generation_index=self.generation_index,
            generation_phase=self.generation_phase,
            chapters=self.chapters,
            provenance=self.provenance.to_projection(),
        )
        value["record_sha256"] = self.record_sha256
        return value
