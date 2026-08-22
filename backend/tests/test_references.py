from app.domain.models import Candidate, Chunk, ScoreTrace, SourceLocator
from app.retrieval.references import resolve_references


def _chunk(chunk_id: str, text: str, section: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id="public-document",
        text=text,
        locator=SourceLocator(
            document_id="public-document",
            document_title="Public document",
            version="1",
            source_url="https://example.org/public.pdf",
            page=1,
            section_path=[section],
        ),
    )


def test_explicit_section_reference_is_followed_within_same_document() -> None:
    source = _chunk("source", "For details, see section 1.6.3.", "Overview")
    target = _chunk("target", "Materiality selection process.", "ESRS 2 1.6.3")
    candidate = Candidate(field_id="process", chunk=source, score=ScoreTrace(rrf_score=0.1))

    resolution = resolve_references([candidate], [source, target])

    assert [item.chunk.id for item in resolution.candidates] == ["source", "target"]
    assert resolution.resolved
    assert resolution.unresolved == []


def test_unknown_reference_is_reported_without_leaving_scope() -> None:
    source = _chunk("source", "See section 9.9 for details.", "Overview")
    candidate = Candidate(field_id="process", chunk=source, score=ScoreTrace(rrf_score=0.1))

    resolution = resolve_references([candidate], [source])

    assert [item.chunk.id for item in resolution.candidates] == ["source"]
    assert resolution.resolved == []
    assert resolution.unresolved
