from app.domain.models import Chunk, SourceLocator
from evals.chunking_strategies import (
    RetrievalCase,
    contextualized_chunks,
    evaluate_rankings,
    hierarchical_ranking,
    parent_chunks,
)


def _chunk(chunk_id: str, section: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id="doc",
        text=text,
        locator=SourceLocator(
            document_id="doc", document_title="Report", version="1",
            source_url="https://example.com", page=1, section_path=[section],
        ),
    )


def test_parent_chunks_preserve_section_routing() -> None:
    chunks = [_chunk("a", "Capital", "SCR is 100"), _chunk("b", "Capital", "Ratio is 200%")]
    parents = parent_chunks(chunks)

    assert len(parents) == 1
    assert "Capital" in parents[0].text
    assert "SCR is 100" in parents[0].text


def test_contextual_chunks_keep_original_provenance() -> None:
    source = _chunk("a", "Capital", "The ratio is 200%")
    enriched = contextualized_chunks([source], {"a": "This is the entity SCR ratio."})[0]

    assert enriched.text.endswith(source.text)
    assert enriched.locator == source.locator


def test_hierarchical_ranking_returns_children_not_parent_summaries() -> None:
    chunks = [
        _chunk("a", "Governance", "Board committee responsibilities"),
        _chunk("b", "Capital", "Eligible own funds R0660"),
    ]
    ranking, searched = hierarchical_ranking(chunks, "eligible own funds", parent_k=1)

    assert ranking[0].id == "b"
    assert all(chunk.chunk_type != "hierarchical_parent" for chunk in ranking)
    assert searched < len(parent_chunks(chunks)) + len(chunks) + 1


def test_metrics_do_not_hide_missing_relevant_chunks() -> None:
    chunks = [_chunk("a", "Capital", "Eligible own funds R0660")]
    cases = [
        RetrievalCase("hit", "funds", ("R0660",)),
        RetrievalCase("miss", "market share", ("R9999",)),
    ]
    metrics = evaluate_rankings(cases, lambda _query: (chunks, len(chunks)))

    assert metrics.recall_at_1 == 0.5
    assert metrics.mean_reciprocal_rank == 0.5
