from __future__ import annotations

from app.domain.models import EvidenceProfile, SearchQuery


def plan_queries(
    question: str,
    profile: EvidenceProfile,
    document_ids: list[str],
) -> list[SearchQuery]:
    queries: list[SearchQuery] = []
    for field in profile.fields:
        # Each template is an explicit, inspectable reformulation for one required
        # field. This is deterministic query expansion, not an LLM call.
        for template in field.query_templates:
            queries.append(
                SearchQuery(
                    field_id=field.id,
                    field_label=field.label,
                    text=template,
                    document_ids=document_ids,
                )
            )
    return queries
