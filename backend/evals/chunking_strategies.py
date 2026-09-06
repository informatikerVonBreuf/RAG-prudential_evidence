from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.domain.models import Chunk, SearchQuery, SourceLocator
from app.retrieval.hybrid import HybridRetriever


@dataclass(frozen=True)
class RetrievalCase:
    id: str
    query: str
    relevant_markers: tuple[str, ...]


@dataclass(frozen=True)
class StrategyMetrics:
    cases: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mean_reciprocal_rank: float
    mean_candidates_searched: float
    first_relevant_ranks: dict[str, int | None]


def structural_context(chunk: Chunk) -> str:
    """Return deterministic context already available from reviewed provenance."""
    section = " > ".join(chunk.locator.section_path) or "Unsectioned content"
    return (
        f"Document: {chunk.locator.document_title}. "
        f"Section: {section}. Page: {chunk.locator.page}. "
        f"Content type: {chunk.chunk_type}."
    )


def contextualized_chunks(
    chunks: list[Chunk], contexts: dict[str, str] | None = None
) -> list[Chunk]:
    contexts = contexts or {}
    return [
        chunk.model_copy(
            update={
                "text": f"{contexts.get(chunk.id) or structural_context(chunk)} {chunk.text}"
            }
        )
        for chunk in chunks
    ]


def section_key(chunk: Chunk) -> tuple[str, str]:
    path = chunk.locator.section_path
    section = " > ".join(path[:2]) if path else f"Page {chunk.locator.page}"
    return chunk.document_id, section


def parent_chunks(chunks: list[Chunk], max_characters: int = 6000) -> list[Chunk]:
    grouped: dict[tuple[str, str], list[Chunk]] = {}
    for chunk in chunks:
        grouped.setdefault(section_key(chunk), []).append(chunk)
    parents: list[Chunk] = []
    for index, ((document_id, section), children) in enumerate(grouped.items()):
        first = children[0]
        content = " ".join(child.text for child in children)
        parents.append(
            Chunk(
                id=f"parent-{index:04d}",
                document_id=document_id,
                chunk_type="hierarchical_parent",
                text=(
                    f"Document section: {section}. Child chunks: {len(children)}. "
                    f"Section content: {content[:max_characters]}"
                ),
                locator=SourceLocator(
                    document_id=document_id,
                    document_title=first.locator.document_title,
                    version=first.locator.version,
                    source_url=first.locator.source_url,
                    page=min(child.locator.page for child in children),
                    section_path=[section],
                ),
            )
        )
    return parents


def flat_ranking(
    chunks: list[Chunk], query: str, dense_factory: Callable[[list[Chunk]], object] | None = None
) -> list[Chunk]:
    dense = dense_factory(chunks) if dense_factory else None
    retriever = HybridRetriever(chunks, dense_index=dense)
    request = SearchQuery(
        field_id="chunking_eval", field_label="Chunking evaluation", text=query,
        document_ids=sorted({chunk.document_id for chunk in chunks}),
    )
    return [candidate.chunk for candidate in retriever.search(request, k=len(chunks))]


def hierarchical_ranking(
    chunks: list[Chunk], query: str, parent_k: int = 3,
    dense_factory: Callable[[list[Chunk]], object] | None = None,
) -> tuple[list[Chunk], int]:
    parents = parent_chunks(chunks)
    ranked_parents = flat_ranking(parents, query, dense_factory)[:parent_k]
    selected_sections = {parent.locator.section_path[0] for parent in ranked_parents}
    children = [
        chunk for chunk in chunks
        if " > ".join(chunk.locator.section_path[:2]) in selected_sections
        or (not chunk.locator.section_path and f"Page {chunk.locator.page}" in selected_sections)
    ]
    return flat_ranking(children, query, dense_factory), len(parents) + len(children)


def evaluate_rankings(
    cases: list[RetrievalCase], ranking_fn: Callable[[str], tuple[list[Chunk], int]]
) -> StrategyMetrics:
    ranks: list[int | None] = []
    searched: list[int] = []
    for case in cases:
        ranking, candidates = ranking_fn(case.query)
        rank = next(
            (
                index for index, chunk in enumerate(ranking, start=1)
                if any(
                    marker.casefold() in chunk.text.casefold()
                    for marker in case.relevant_markers
                )
            ),
            None,
        )
        ranks.append(rank)
        searched.append(candidates)
    total = max(len(cases), 1)
    return StrategyMetrics(
        cases=len(cases),
        recall_at_1=sum(rank is not None and rank <= 1 for rank in ranks) / total,
        recall_at_3=sum(rank is not None and rank <= 3 for rank in ranks) / total,
        recall_at_5=sum(rank is not None and rank <= 5 for rank in ranks) / total,
        mean_reciprocal_rank=sum(1 / rank for rank in ranks if rank) / total,
        mean_candidates_searched=sum(searched) / total,
        first_relevant_ranks={case.id: rank for case, rank in zip(cases, ranks, strict=True)},
    )


def load_context_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_context_cache(path: Path, contexts: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contexts, ensure_ascii=False, indent=2), encoding="utf-8")
