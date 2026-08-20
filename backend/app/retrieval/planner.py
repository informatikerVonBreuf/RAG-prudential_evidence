from __future__ import annotations

from app.domain.models import EvidenceProfile, SearchQuery


def plan_queries(
    question: str,
    profile: EvidenceProfile,
    document_ids: list[str],
) -> list[SearchQuery]:
    queries: list[SearchQuery] = []
    for field in profile.fields:
        template = field.query_templates[0]
        queries.append(
            SearchQuery(
                field_id=field.id,
                field_label=field.label,
                text=f"{question} | {template}",
                document_ids=document_ids,
            )
        )
    return queries

