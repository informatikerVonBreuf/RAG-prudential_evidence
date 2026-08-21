from __future__ import annotations

from pathlib import Path
from typing import Any

from ingestion.models import DocumentProfile


class DoclingUnavailableError(RuntimeError):
    pass


def convert(path: Path, profile: DocumentProfile, output_directory: Path) -> Any:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        raise DoclingUnavailableError(
            "Docling n'est pas installé. Installer l'extra `.[ingestion]`."
        ) from exc

    options = PdfPipelineOptions()
    options.generate_page_images = True
    options.generate_picture_images = profile == DocumentProfile.ANNUAL_REPORT_VISUAL
    options.generate_table_images = profile == DocumentProfile.QRT_TABLE_HEAVY
    options.images_scale = 2.0
    options.do_ocr = profile == DocumentProfile.SCANNED_DOCUMENT
    options.do_table_structure = profile == DocumentProfile.QRT_TABLE_HEAVY
    if options.do_table_structure:
        options.table_structure_options.mode = TableFormerMode.ACCURATE
        options.table_structure_options.do_cell_matching = True
    output_directory.mkdir(parents=True, exist_ok=True)
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    return converter.convert(path)
