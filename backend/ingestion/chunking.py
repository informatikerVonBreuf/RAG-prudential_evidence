from __future__ import annotations

import re
from typing import Any

from ingestion.models import (
    ChunkArtifact,
    FigureArtifact,
    PageArtifact,
    Provenance,
    TableArtifact,
)


def contextualize(
    *, title: str, entity: str | None, period: str | None, section_path: list[str], text: str
) -> str:
    parts = [f"Document: {title}."]
    if entity:
        parts.append(f"Entity: {entity}.")
    if period:
        parts.append(f"Period: {period}.")
    if section_path:
        parts.append(f"Section: {' > '.join(section_path)}.")
    parts.append(f"Content: {text.strip()}")
    return " ".join(parts)


def chunk_pages(
    document_id: str,
    title: str,
    pages: list[PageArtifact],
    entity: str,
    period: str,
    max_characters: int = 1800,
) -> list[ChunkArtifact]:
    chunks: list[ChunkArtifact] = []
    for page in pages:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", page.text) if part.strip()]
        for index, paragraph in enumerate(paragraphs):
            for part_index, start in enumerate(range(0, len(paragraph), max_characters)):
                raw = paragraph[start : start + max_characters]
                chunks.append(
                    ChunkArtifact(
                        id=f"{document_id}-p{page.page:03d}-text-{index:03d}-{part_index:02d}",
                        document_id=document_id,
                        chunk_type="paragraph",
                        raw_text=raw,
                        contextualized_text=contextualize(
                            title=title,
                            entity=entity,
                            period=period,
                            section_path=[],
                            text=raw,
                        ),
                        page_start=page.page,
                        page_end=page.page,
                        entity=entity,
                        period=period,
                        provenance=[Provenance(page=page.page, source_kind="native_pdf_text")],
                    )
                )
    return chunks


def chunk_docling_document(
    document: Any,
    document_id: str,
    title: str,
    entity: str,
    period: str,
    max_characters: int = 1800,
) -> list[ChunkArtifact]:
    """Create textual chunks from Docling's hierarchy while retaining provenance."""
    from docling_core.transforms.chunker import HierarchicalChunker

    chunks: list[ChunkArtifact] = []
    for chunk_index, docling_chunk in enumerate(HierarchicalChunker().chunk(document)):
        raw_text = docling_chunk.text.strip()
        if not raw_text:
            continue
        headings = list(docling_chunk.meta.headings or [])
        provenance = _docling_provenance(docling_chunk.meta.doc_items)
        pages = [item.page for item in provenance] or [1]
        for part_index, start in enumerate(range(0, len(raw_text), max_characters)):
            part = raw_text[start : start + max_characters]
            chunks.append(
                ChunkArtifact(
                    id=f"{document_id}-docling-{chunk_index:04d}-{part_index:02d}",
                    document_id=document_id,
                    chunk_type="docling_hierarchical_text",
                    raw_text=part,
                    contextualized_text=contextualize(
                        title=title,
                        entity=entity,
                        period=period,
                        section_path=headings,
                        text=part,
                    ),
                    page_start=min(pages),
                    page_end=max(pages),
                    section_path=headings,
                    entity=entity,
                    period=period,
                    provenance=provenance,
                )
            )
    return chunks


def _docling_provenance(doc_items: list[Any]) -> list[Provenance]:
    provenance: list[Provenance] = []
    seen: set[tuple[int, tuple[float, ...] | None]] = set()
    for item in doc_items:
        for source in item.prov:
            bbox = [round(value, 2) for value in source.bbox.as_tuple()]
            key = (source.page_no, tuple(bbox))
            if key in seen:
                continue
            seen.add(key)
            provenance.append(
                Provenance(
                    page=source.page_no,
                    bbox=bbox,
                    source_kind="docling_structured_document",
                )
            )
    return provenance


def chunk_figures(
    document_id: str,
    title: str,
    figures: list[FigureArtifact],
    entity: str,
    period: str,
    max_characters: int = 1800,
) -> list[ChunkArtifact]:
    """Turn grounded visual descriptions into searchable text, never typed facts."""
    chunks: list[ChunkArtifact] = []
    for figure in figures:
        description = figure.description
        if not description:
            continue
        observations = [
            observation
            for observation in description.get("observations", [])
            if observation.get("directly_visible") is True
        ][:30]
        image_type = description.get("image_type", figure.classification)
        chunk_type = (
            "table_description"
            if str(image_type).casefold() in {"table", "tableau", "embedded_table"}
            else "image_description"
        )
        parts = [
            f"Visual type: {image_type}.",
            f"Factual description: {description.get('factual_description', '')}",
        ]
        uncertainties = description.get("uncertainties", [])
        if uncertainties:
            parts.append(f"Declared uncertainties: {'; '.join(uncertainties)}.")
        parts.extend(
            f"Directly visible observation: {_format_visual_observation(item)}."
            for item in observations
        )
        for part_index, raw_text in enumerate(_pack_text_parts(parts, max_characters)):
            chunks.append(
                ChunkArtifact(
                    id=(
                        f"{document_id}-{figure.id}-visual-description-"
                        f"{part_index:02d}"
                    ),
                    document_id=document_id,
                    chunk_type=chunk_type,
                    raw_text=raw_text,
                    contextualized_text=contextualize(
                        title=title,
                        entity=description.get("entity") or entity,
                        period=period,
                        section_path=figure.section_path,
                        text=raw_text,
                    ),
                    page_start=figure.page,
                    page_end=figure.page,
                    section_path=figure.section_path,
                    entity=description.get("entity") or entity,
                    period=period,
                    provenance=[
                        Provenance(
                            page=figure.page,
                            bbox=figure.bbox,
                            source_kind="gemini_visual_description",
                        )
                    ],
                )
            )
    return chunks


def _format_visual_observation(observation: dict[str, Any]) -> str:
    value = observation.get("value")
    unit = observation.get("unit")
    rendered_value = "unreadable value" if value is None else str(value)
    if unit:
        rendered_value = f"{rendered_value} {unit}"
    return f"{observation.get('label', 'observation')} = {rendered_value}"


def _pack_text_parts(parts: list[str], max_characters: int) -> list[str]:
    packed: list[str] = []
    current = ""
    for part in (item.strip() for item in parts if item.strip()):
        if current and len(current) + len(part) + 1 > max_characters:
            packed.append(current)
            current = ""
        if len(part) > max_characters:
            packed.extend(
                part[start : start + max_characters]
                for start in range(0, len(part), max_characters)
            )
        else:
            current = f"{current} {part}".strip()
    if current:
        packed.append(current)
    return packed


def chunk_tables(document_id: str, title: str, tables: list[TableArtifact]) -> list[ChunkArtifact]:
    chunks: list[ChunkArtifact] = []
    for table in tables:
        group_text = "; ".join(
            f"{cell.row_code}/{cell.column_code} {cell.row_label}: {cell.raw_value}"
            for cell in table.cells
        )
        chunks.append(
            ChunkArtifact(
                id=f"{document_id}-{table.id.casefold().replace('.', '')}-row-group",
                document_id=document_id,
                chunk_type="table_row_group",
                raw_text=group_text,
                contextualized_text=contextualize(
                    title=title,
                    entity=table.entity,
                    period=table.period,
                    section_path=[table.id, table.title],
                    text=group_text,
                ),
                page_start=min(table.pages),
                page_end=max(table.pages),
                section_path=[table.id, table.title],
                entity=table.entity,
                period=table.period,
                table_id=table.id,
                row_codes=[cell.row_code for cell in table.cells],
                provenance=[cell.provenance for cell in table.cells],
            )
        )
    return chunks
