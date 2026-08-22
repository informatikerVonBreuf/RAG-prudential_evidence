import json
from pathlib import Path

import pytest
from ingestion.chunking import chunk_figures
from ingestion.enrich_visuals import enrich_cached_visuals
from ingestion.indexing import build_embedding_cache
from ingestion.models import FigureArtifact
from ingestion.pipeline import ingest_pdf
from ingestion.promote import ROW_FIELDS
from ingestion.pymupdf_fallback import QRT_TEMPLATES


def test_visual_description_becomes_searchable_without_inferences(tmp_path: Path) -> None:
    figure = FigureArtifact(
        id="figure-001",
        page=7,
        section_path=["S.23.01.22"],
        classification="embedded_table",
        bbox=[10.0, 20.0, 30.0, 40.0],
        description={
            "language": "en",
            "image_type": "table",
            "entity": "Groupe Foyer",
            "factual_description": "The table presents the SCR coverage ratio.",
            "observations": [
                {
                    "label": "SCR coverage ratio",
                    "value": 287,
                    "unit": "%",
                    "source": "image",
                    "directly_visible": True,
                },
                {
                    "label": "Assumed projection",
                    "value": 300,
                    "unit": "%",
                    "source": "context",
                    "directly_visible": False,
                },
            ],
            "uncertainties": ["The title is partially cropped."],
            "inferences": ["Future solvency may improve."],
        },
    )

    chunks = chunk_figures(
        "foyer_group_qrt_2025",
        "QRT public 2025",
        [figure],
        "Groupe Foyer",
        "2025",
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.chunk_type == "table_description"
    assert "SCR coverage ratio = 287 %" in chunk.contextualized_text
    assert "Assumed projection" not in chunk.contextualized_text
    assert "Future solvency" not in chunk.contextualized_text
    assert chunk.provenance[0].source_kind == "gemini_visual_description"

    manifest = build_embedding_cache(chunks, tmp_path / "indexes")
    vectors = json.loads((tmp_path / "indexes" / "embeddings.json").read_text())
    assert manifest["chunks"] == 1
    assert manifest["is_trained_embedding_model"] is False
    assert chunk.id in vectors


def test_cached_visual_enrichment_requires_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("RUN_VISUAL_ENRICHMENT", raising=False)
    with pytest.raises(RuntimeError, match="RUN_VISUAL_ENRICHMENT=1"):
        enrich_cached_visuals(tmp_path)


@pytest.mark.parametrize("max_characters", [599, 6001])
def test_ingestion_rejects_unsafe_chunk_character_limits(
    tmp_path: Path, max_characters: int
) -> None:
    with pytest.raises(ValueError, match="between 600 and 6000"):
        ingest_pdf(
            path=tmp_path / "unused.pdf",
            document_id="doc",
            title="Document",
            entity="Entity",
            period="2025",
            source_url="https://example.test/document.pdf",
            output_root=tmp_path,
            max_characters=max_characters,
        )


def test_group_and_solo_qrt_evidence_contracts_are_distinct() -> None:
    assert set(QRT_TEMPLATES["S.23.01.22"]) == {"R0660", "R0680", "R0690"}
    assert set(QRT_TEMPLATES["S.23.01.01"]) == {"R0540", "R0580", "R0620"}
    assert ROW_FIELDS["R0680"][0] == "group_scr"
    assert ROW_FIELDS["R0580"][0] == "entity_scr"
