from __future__ import annotations

import argparse
from pathlib import Path

from ingestion.chunking import chunk_tables
from ingestion.exporters import read_result, write_canonical_markdown, write_result
from ingestion.indexing import build_embedding_cache
from ingestion.pymupdf_fallback import extract_qrt_coverage_table


def refresh_qrt_evidence(processed_directory: Path, pdf_path: Path) -> tuple[int, list[str]]:
    result = read_result(processed_directory)
    table, warnings = extract_qrt_coverage_table(
        pdf_path, result.manifest.entity, result.manifest.period
    )
    tables = [table] if table else []
    retained = [chunk for chunk in result.chunks if chunk.chunk_type != "table_row_group"]
    table_chunks = chunk_tables(
        result.manifest.document_id, result.manifest.title, tables
    )
    updated = result.model_copy(
        update={
            "tables": tables,
            "chunks": [*retained, *table_chunks],
            "manifest": result.manifest.model_copy(update={"warnings": warnings}),
        }
    )
    write_result(updated)
    write_canonical_markdown(
        updated, (processed_directory / "docling.md").read_text(encoding="utf-8")
    )
    build_embedding_cache(updated.chunks, processed_directory / "indexes")
    return len(table.cells) if table else 0, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh verified QRT cells from a cached PDF")
    parser.add_argument("processed_directory", type=Path)
    parser.add_argument("pdf_path", type=Path)
    args = parser.parse_args()
    cells, warnings = refresh_qrt_evidence(args.processed_directory, args.pdf_path)
    print({"verified_cells": cells, "warnings": warnings})


if __name__ == "__main__":
    main()
