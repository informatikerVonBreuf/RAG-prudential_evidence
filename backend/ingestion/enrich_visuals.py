from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from ingestion.chunking import chunk_figures
from ingestion.exporters import read_result, write_canonical_markdown, write_result
from ingestion.indexing import build_embedding_cache
from ingestion.visual_enrichment import describe_with_gemini, should_enrich_visual


def enrich_cached_visuals(processed_directory: Path) -> tuple[int, int]:
    if os.getenv("RUN_VISUAL_ENRICHMENT", "0") != "1":
        raise RuntimeError(
            "Définir RUN_VISUAL_ENRICHMENT=1 pour autoriser explicitement les appels Gemini."
        )
    result = read_result(processed_directory)
    enriched = list(result.figures)
    calls = 0
    failures: list[str] = []
    for index, figure in enumerate(result.figures):
        if figure.description:
            continue
        if not should_enrich_visual(figure):
            continue
        try:
            description = describe_with_gemini(figure)
        except Exception as exc:
            failures.append(f"{figure.id}: {type(exc).__name__}: {exc}")
            continue
        enriched[index] = figure.model_copy(
            update={"description": description.model_dump()}
        )
        calls += 1
        checkpoint = result.model_copy(update={"figures": enriched})
        write_result(checkpoint)

    retained_chunks = [
        chunk
        for chunk in result.chunks
        if chunk.chunk_type
        not in {"visual_description", "table_description", "image_description"}
    ]
    visual_chunks = chunk_figures(
        result.manifest.document_id,
        result.manifest.title,
        enriched,
        result.manifest.entity,
        result.manifest.period,
    )
    warnings = [*result.manifest.warnings, *failures]
    updated = result.model_copy(
        update={
            "manifest": result.manifest.model_copy(update={"warnings": warnings}),
            "figures": enriched,
            "chunks": [*retained_chunks, *visual_chunks],
        }
    )
    write_result(updated)
    write_canonical_markdown(
        updated, (processed_directory / "docling.md").read_text(encoding="utf-8")
    )
    build_embedding_cache(updated.chunks, processed_directory / "indexes")
    return calls, len(visual_chunks)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Enrichir les visuels déjà extraits sans reconvertir le PDF"
    )
    parser.add_argument("processed_directory", type=Path)
    args = parser.parse_args()
    calls, chunks = enrich_cached_visuals(args.processed_directory)
    print(f"Appels Gemini: {calls}; chunks visuels: {chunks}")


if __name__ == "__main__":
    main()
