from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class DocumentProfile(StrEnum):
    QRT_TABLE_HEAVY = "qrt_table_heavy"
    ANNUAL_REPORT_VISUAL = "annual_report_visual"
    NARRATIVE_POLICY = "narrative_policy"
    SCANNED_DOCUMENT = "scanned_document"
    HTML_REPORT = "html_report"


class Provenance(BaseModel):
    page: int
    bbox: list[float] | None = None
    source_kind: str


class PageArtifact(BaseModel):
    page: int
    text: str
    characters: int
    blocks: int
    potential_scan: bool
    image_path: str | None = None


class SectionArtifact(BaseModel):
    id: str
    title: str
    level: int
    page: int
    parent_id: str | None = None


class TableCellArtifact(BaseModel):
    row_code: str
    column_code: str
    row_label: str
    raw_value: str
    normalized_value: float
    value_type: str
    unit: str
    provenance: Provenance


class TableArtifact(BaseModel):
    id: str
    title: str
    entity: str
    period: str
    pages: list[int]
    cells: list[TableCellArtifact]


class FigureArtifact(BaseModel):
    id: str
    page: int
    section_path: list[str] = Field(default_factory=list)
    caption: str | None = None
    preceding_text: list[str] = Field(default_factory=list)
    following_text: list[str] = Field(default_factory=list)
    classification: str = "unknown"
    image_path: str | None = None
    page_image_path: str | None = None
    bbox: list[float] | None = None
    description: dict[str, object] | None = None


class ChunkArtifact(BaseModel):
    id: str
    document_id: str
    chunk_type: str
    raw_text: str
    contextualized_text: str
    page_start: int
    page_end: int
    section_path: list[str] = Field(default_factory=list)
    entity: str | None = None
    period: str | None = None
    table_id: str | None = None
    row_codes: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)


class IngestionManifest(BaseModel):
    schema_version: str = "1.0.0"
    document_id: str
    title: str
    entity: str
    period: str
    profile: DocumentProfile
    source_url: str
    source_path: str
    sha256: str
    acquired_at: str
    extractor: str
    extractor_version: str | None = None
    canonical_artifact: str = "document.md"
    canonical_format: str = "docling_document_and_markdown"
    chunker: str = "docling_hierarchical_chunker"
    output_directory: str
    warnings: list[str] = Field(default_factory=list)


class IngestionResult(BaseModel):
    manifest: IngestionManifest
    pages: list[PageArtifact]
    sections: list[SectionArtifact]
    tables: list[TableArtifact]
    figures: list[FigureArtifact]
    chunks: list[ChunkArtifact]

    def output_path(self) -> Path:
        return Path(self.manifest.output_directory)
