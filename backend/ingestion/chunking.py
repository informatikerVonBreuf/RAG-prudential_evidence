from __future__ import annotations

import re

from ingestion.models import ChunkArtifact, PageArtifact, Provenance, TableArtifact


def contextualize(
    *, title: str, entity: str | None, period: str | None, section_path: list[str], text: str
) -> str:
    parts = [f"Document : {title}."]
    if entity:
        parts.append(f"Entité : {entity}.")
    if period:
        parts.append(f"Période : {period}.")
    if section_path:
        parts.append(f"Section : {' > '.join(section_path)}.")
    parts.append(f"Contenu : {text.strip()}")
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
