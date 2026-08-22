from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.domain.models import Candidate, Chunk

REFERENCE_PATTERN = re.compile(
    r"\b(?:voir|see)\s+(?:ESRS\s+)?(?:la\s+)?(?:section\s+)?([A-Z]?\d+(?:\.\d+){0,3})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReferenceResolution:
    candidates: list[Candidate]
    resolved: list[str]
    unresolved: list[str]


def resolve_references(
    candidates: list[Candidate], corpus_chunks: list[Chunk], max_references: int = 3
) -> ReferenceResolution:
    """Follow explicit section references within the selected document scope."""
    expanded = list(candidates)
    resolved: list[str] = []
    unresolved: list[str] = []
    seen_chunks = {candidate.chunk.id for candidate in candidates}
    references: list[tuple[Candidate, str]] = []
    for candidate in candidates:
        for reference in REFERENCE_PATTERN.findall(candidate.chunk.text):
            references.append((candidate, reference))
    for source, reference in references[:max_references]:
        target = next(
            (
                chunk
                for chunk in corpus_chunks
                if chunk.document_id == source.chunk.document_id
                and chunk.id not in seen_chunks
                and _section_matches(chunk, reference)
            ),
            None,
        )
        label = f"{source.chunk.id} -> section {reference}"
        if target is None:
            unresolved.append(label)
            continue
        expanded.append(source.model_copy(update={"chunk": target}))
        seen_chunks.add(target.id)
        resolved.append(f"{label} -> {target.id}")
    return ReferenceResolution(expanded, resolved, unresolved)


def _section_matches(chunk: Chunk, reference: str) -> bool:
    needle = _normalize(reference)
    return any(needle in _normalize(section).split() for section in chunk.locator.section_path)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode()
