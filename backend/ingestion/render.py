from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.chunking import chunk_figures, contextualize
from ingestion.exporters import read_result, write_canonical_markdown, write_result
from ingestion.indexing import build_embedding_cache
from ingestion.profiles import detect_document_profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Régénérer document.md depuis les artefacts déjà extraits"
    )
    parser.add_argument("processed_directory", type=Path)
    args = parser.parse_args()
    result = read_result(args.processed_directory)
    source_path = Path(result.manifest.source_path)
    if source_path.exists():
        sample_text = "\n".join(page.text for page in result.pages[:3])
        detected_profile = detect_document_profile(source_path, sample_text)
        warnings = result.manifest.warnings
        if detected_profile.value != "qrt_table_heavy":
            warnings = [
                warning
                for warning in warnings
                if "QRT" not in warning and "R0660/R0680/R0690" not in warning
            ]
        result = result.model_copy(
            update={
                "manifest": result.manifest.model_copy(
                    update={"profile": detected_profile, "warnings": warnings}
                )
            }
        )
    retained_chunks = []
    for chunk in result.chunks:
        if chunk.chunk_type in {
            "visual_description",
            "table_description",
            "image_description",
        }:
            continue
        retained_chunks.append(
            chunk.model_copy(
                update={
                    "contextualized_text": contextualize(
                        title=result.manifest.title,
                        entity=chunk.entity or result.manifest.entity,
                        period=chunk.period or result.manifest.period,
                        section_path=chunk.section_path,
                        text=chunk.raw_text,
                    )
                }
            )
        )
    visual_chunks = chunk_figures(
        result.manifest.document_id,
        result.manifest.title,
        result.figures,
        result.manifest.entity,
        result.manifest.period,
    )
    result = result.model_copy(
        update={"chunks": [*retained_chunks, *visual_chunks]}
    )
    write_result(result)
    docling_markdown = (args.processed_directory / "docling.md").read_text(encoding="utf-8")
    path = write_canonical_markdown(result, docling_markdown)
    build_embedding_cache(result.chunks, args.processed_directory / "indexes")
    print(f"{path} — chunks visuels: {len(visual_chunks)}")


if __name__ == "__main__":
    main()
