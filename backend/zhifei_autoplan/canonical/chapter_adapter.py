"""Pure explicit-input handoff helpers for the bounded C4 foundation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .chapter import ChapterContentV1, ChapterGenerationRequestV1, ChapterSetV1
from .evidence import ResponseEvidenceSetV2
from .scoring import SourceProvenanceReferenceV1


@dataclass(frozen=True, slots=True)
class ChapterCandidateV1:
    chapter_key: str
    title: str
    body: str
    source_references: tuple[SourceProvenanceReferenceV1, ...]


def create_initial_chapter_request(
    *,
    origin_namespace: str,
    origin_key: str,
    origin_source_mode: str,
    source_mode_set: Sequence[str],
    source_references: Sequence[SourceProvenanceReferenceV1],
) -> ChapterGenerationRequestV1:
    """Create only the non-circular INITIAL request; no generation is invoked."""

    return ChapterGenerationRequestV1.build(
        origin_namespace=origin_namespace,
        origin_key=origin_key,
        origin_source_mode=origin_source_mode,
        source_mode_set=source_mode_set,
        source_references=source_references,
        generation_index=0,
        generation_phase="INITIAL",
    )


def create_grounded_chapter_request(
    *,
    origin_namespace: str,
    origin_key: str,
    origin_source_mode: str,
    source_mode_set: Sequence[str],
    source_references: Sequence[SourceProvenanceReferenceV1],
    generation_index: int,
    parent_chapter_set: ChapterSetV1,
    response_evidence_sets: Sequence[ResponseEvidenceSetV2],
) -> ChapterGenerationRequestV1:
    """Create a GROUNDED request only from a verified parent and accepted evidence."""

    return ChapterGenerationRequestV1.build(
        origin_namespace=origin_namespace,
        origin_key=origin_key,
        origin_source_mode=origin_source_mode,
        source_mode_set=source_mode_set,
        source_references=source_references,
        generation_index=generation_index,
        generation_phase="GROUNDED",
        parent_chapter_set=parent_chapter_set,
        response_evidence_sets=response_evidence_sets,
    )


def handoff_generated_chapters(
    *,
    request: ChapterGenerationRequestV1,
    candidates: Sequence[ChapterCandidateV1],
) -> ChapterSetV1:
    """Canonicalize explicit generated values without runtime, persistence, or export."""

    chapters = tuple(
        ChapterContentV1.create(
            chapter_key=item.chapter_key,
            title=item.title,
            body=item.body,
            source_references=item.source_references,
        )
        for item in candidates
    )
    return ChapterSetV1.build(request=request, chapters=chapters)
