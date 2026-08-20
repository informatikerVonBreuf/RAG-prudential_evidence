from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Mode(StrEnum):
    QUICK = "quick"
    DEEP = "deep"
    SUMMARY = "summary"


class AnswerStatus(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"


class DocumentView(BaseModel):
    id: str
    folder: str
    title: str
    entity: str
    year: int
    document_type: str
    version: str
    source_url: str
    status: Literal["indexed", "reviewed", "synthetic"]
    pages: int
    description: str


class ScopeSelection(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1200)
    mode: Mode = Mode.DEEP
    scope: ScopeSelection = Field(default_factory=ScopeSelection)
    profile_id: str | None = None


class EvidenceField(BaseModel):
    id: str
    label: str
    value_type: Literal["text", "integer", "decimal", "percentage", "currency"]
    required: bool = True
    query_templates: list[str]


class EvidenceProfile(BaseModel):
    id: str
    version: str
    label: str
    description: str
    triggers: list[str]
    fields: list[EvidenceField]


class SearchQuery(BaseModel):
    field_id: str
    field_label: str
    text: str
    document_ids: list[str]


class SourceLocator(BaseModel):
    document_id: str
    document_title: str
    version: str
    source_url: str
    page: int
    section_path: list[str]
    table_id: str | None = None
    row: int | None = None
    column: int | None = None
    bbox: list[float] | None = None


class Fact(BaseModel):
    field_id: str
    label: str
    value: str | int | float
    formatted_value: str
    value_type: Literal["text", "integer", "decimal", "percentage", "currency"]
    unit: str | None = None
    period: str | None = None
    entity: str


class Chunk(BaseModel):
    id: str
    document_id: str
    text: str
    locator: SourceLocator
    facts: list[Fact] = Field(default_factory=list)


class ScoreTrace(BaseModel):
    lexical_rank: int | None = None
    dense_rank: int | None = None
    lexical_score: float = 0
    dense_score: float = 0
    rrf_score: float = 0


class Candidate(BaseModel):
    field_id: str
    chunk: Chunk
    score: ScoreTrace


class EvidenceView(BaseModel):
    id: str
    field_id: str
    field_label: str
    state: Literal["ACCEPTED", "MISSING", "REJECTED", "CONFLICT"]
    excerpt: str | None = None
    fact: Fact | None = None
    source: SourceLocator | None = None
    score: ScoreTrace | None = None
    reason: str | None = None


class Claim(BaseModel):
    id: str
    text: str
    evidence_ids: list[str]


class CoverageItem(BaseModel):
    field_id: str
    label: str
    state: Literal["COVERED", "MISSING", "CONFLICT"]
    evidence_ids: list[str] = Field(default_factory=list)


class QueryTrace(BaseModel):
    field_id: str
    query: str
    candidate_count: int
    consulted_document_ids: list[str]


class AnswerPayload(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    request_id: str
    mode: Mode
    status: AnswerStatus
    profile_id: str
    profile_label: str
    summary: str
    claims: list[Claim]
    evidence: list[EvidenceView]
    coverage: list[CoverageItem]
    missing_fields: list[str]
    corpus_version: str
    query_trace: list[QueryTrace]
    latency_ms: int


class HealthPayload(BaseModel):
    status: Literal["ok"] = "ok"
    corpus_version: str
    documents: int
    chunks: int

