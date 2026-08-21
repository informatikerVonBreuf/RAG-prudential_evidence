from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path

from ingestion.chunking import chunk_pages, chunk_tables
from ingestion.docling_converter import convert as convert_with_docling
from ingestion.exporters import write_result
from ingestion.indexing import build_embedding_cache
from ingestion.models import IngestionManifest, IngestionResult
from ingestion.profiles import detect_document_profile
from ingestion.pymupdf_fallback import extract_pages, extract_qrt_coverage_table, version


def ingest_pdf(
    *, path: Path, document_id: str, title: str, entity: str, period: str,
    source_url: str, output_root: Path, acquired_at: str | None = None,
) -> IngestionResult:
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
    try:
        conversion = convert_with_docling(
            path, profile=profile, output_directory=output_directory
        )
        (output_directory / "docling.md").write_text(
            conversion.document.export_to_markdown(), encoding="utf-8"
        )
    except Exception as exc:
        extractor = "pymupdf_explicit_fallback"
        extractor_version = version()
        warnings.append(f"Docling indisponible ou en échec: {type(exc).__name__}: {exc}")

    # PyMuPDF supplies deterministic page coordinates and verifies the three QRT
    # cells used by the evidence contract; it is not presented as PDF ingestion.
    tables = []
    if profile.value == "qrt_table_heavy":
        table, table_warnings = extract_qrt_coverage_table(path, entity, period)
        warnings.extend(table_warnings)
        if table:
            tables.append(table)
    chunks = [
        *chunk_pages(document_id, title, pages, entity, period),
        *chunk_tables(document_id, title, tables),
    ]
    result = IngestionResult(
        manifest=IngestionManifest(
            document_id=document_id, title=title, entity=entity, period=period,
            profile=profile, source_url=source_url, source_path=path.as_posix(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            acquired_at=acquired_at or datetime.now(UTC).isoformat(),
            extractor=extractor, extractor_version=extractor_version,
            output_directory=output_directory.as_posix(), warnings=warnings,
        ),
        pages=pages, sections=[], tables=tables, figures=[], chunks=chunks,
    )
    write_result(result)
    build_embedding_cache(result.chunks, output_directory / "indexes")
    return result
