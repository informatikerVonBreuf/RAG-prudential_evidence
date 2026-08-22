from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path

from ingestion.chunking import (
    chunk_docling_document,
    chunk_figures,
    chunk_pages,
    chunk_tables,
)
from ingestion.docling_artifacts import extract_figures
from ingestion.docling_converter import convert as convert_with_docling
from ingestion.exporters import write_canonical_markdown, write_result
from ingestion.indexing import build_embedding_cache
from ingestion.models import IngestionManifest, IngestionResult
from ingestion.profiles import detect_document_profile
from ingestion.pymupdf_fallback import extract_pages, extract_qrt_coverage_table, version
from ingestion.visual_enrichment import describe_with_gemini, should_enrich_visual


def ingest_pdf(
    *, path: Path, document_id: str, title: str, entity: str, period: str,
    source_url: str, output_root: Path, acquired_at: str | None = None,
    max_characters: int = 1800,
) -> IngestionResult:
    if not 600 <= max_characters <= 6000:
        raise ValueError("max_characters must be between 600 and 6000.")
    path = path.resolve()
    output_directory = (output_root / document_id).resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    pages = extract_pages(path, output_directory / "page_images")
    sample_text = "\n".join(page.text for page in pages[:3])
    profile = detect_document_profile(path, sample_text)

    # Docling is the primary structural extractor. Its Markdown export is cached so
    # notebook runs and the deployed application never need to reconvert the PDF.
    extractor = "docling_with_pymupdf_verification"
    extractor_version = package_version("docling")
    extracted_markdown = ""
    docling_document = None
    figures = []
    try:
        conversion = convert_with_docling(
            path, profile=profile, output_directory=output_directory
        )
        docling_document = conversion.document
        extracted_markdown = docling_document.export_to_markdown()
        (output_directory / "docling.md").write_text(extracted_markdown, encoding="utf-8")
        (output_directory / "docling.json").write_text(
            json.dumps(docling_document.export_to_dict(), ensure_ascii=False),
            encoding="utf-8",
        )
        figures = extract_figures(docling_document, output_directory)
        if os.getenv("RUN_VISUAL_ENRICHMENT", "0") == "1":
            enriched_figures = []
            for figure in figures:
                if not should_enrich_visual(figure):
                    enriched_figures.append(figure)
                    continue
                try:
                    description = describe_with_gemini(figure)
                    enriched_figures.append(
                        figure.model_copy(update={"description": description.model_dump()})
                    )
                except Exception as exc:
                    warnings.append(
                        f"Enrichissement visuel {figure.id} en échec: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    enriched_figures.append(figure)
            figures = enriched_figures
    except Exception as exc:
        extractor = "pymupdf_explicit_fallback"
        extractor_version = version()
        warnings.append(f"Docling indisponible ou en échec: {type(exc).__name__}: {exc}")
        extracted_markdown = "\n\n".join(
            f"## Page {page.page}\n\n{page.text}" for page in pages
        )

    # PyMuPDF supplies deterministic page coordinates and verifies the three QRT
    # cells used by the evidence contract; it is not presented as PDF ingestion.
    tables = []
    if profile.value == "qrt_table_heavy":
        table, table_warnings = extract_qrt_coverage_table(path, entity, period)
        warnings.extend(table_warnings)
        if table:
            tables.append(table)
    text_chunks = (
        chunk_docling_document(
            docling_document, document_id, title, entity, period, max_characters
        )
        if docling_document is not None
        else chunk_pages(document_id, title, pages, entity, period, max_characters)
    )
    chunks = [
        *text_chunks,
        *chunk_tables(document_id, title, tables),
        *chunk_figures(
            document_id, title, figures, entity, period, max_characters
        ),
    ]
    result = IngestionResult(
        manifest=IngestionManifest(
            document_id=document_id, title=title, entity=entity, period=period,
            profile=profile, source_url=source_url, source_path=path.as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            acquired_at=acquired_at or datetime.now(UTC).isoformat(),
            extractor=extractor, extractor_version=extractor_version,
            chunker=(
                "docling_hierarchical_chunker"
                if docling_document is not None
                else "pymupdf_page_fallback"
            ),
            output_directory=output_directory.as_posix(), warnings=warnings,
        ),
        pages=pages, sections=[], tables=tables, figures=figures, chunks=chunks,
    )
    write_result(result)
    write_canonical_markdown(result, extracted_markdown)
    build_embedding_cache(result.chunks, output_directory / "indexes")
    return result
