from __future__ import annotations

import asyncio
import time
import uuid

from app.domain.models import AnswerPayload, QueryTrace, QuestionRequest
from app.domain.profiles import map_question
from app.evidence.gate import DeterministicEvidenceGate
from app.generation.composer import GroundedComposer
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.planner import plan_queries
from app.store.artifacts import ArtifactStore, store


class EvidenceEngine:
    def __init__(self, artifact_store: ArtifactStore = store) -> None:
        self.store = artifact_store
        self.gate = DeterministicEvidenceGate()
        self.composer = GroundedComposer()

    async def answer(self, request: QuestionRequest) -> AnswerPayload:
        started = time.perf_counter()
        profile = map_question(request.question, request.profile_id)
        requested_scope = self.store.valid_document_ids(request.scope.document_ids)
        selected_chunks = self.store.selected_chunks(requested_scope)
        selected_document_ids = sorted({chunk.document_id for chunk in selected_chunks})
        queries = plan_queries(request.question, profile, selected_document_ids)
        retriever = HybridRetriever(selected_chunks)

        tasks = [asyncio.to_thread(retriever.search, query, 5) for query in queries]
        candidate_batches = await asyncio.gather(*tasks)
        candidates = [candidate for batch in candidate_batches for candidate in batch]
        gate_result = self.gate.evaluate(profile, candidates)
        summary, claims = self.composer.compose(
            question=request.question,
            mode=request.mode,
            status=gate_result.status,
            evidence=gate_result.evidence,
            missing_fields=gate_result.missing_fields,
        )

        traces = [
            QueryTrace(
                field_id=query.field_id,
                query=query.text,
                candidate_count=len(batch),
                consulted_document_ids=selected_document_ids,
            )
            for query, batch in zip(queries, candidate_batches, strict=True)
        ]
        latency_ms = round((time.perf_counter() - started) * 1000)
        return AnswerPayload(
            request_id=str(uuid.uuid4()),
            mode=request.mode,
            status=gate_result.status,
            profile_id=profile.id,
            profile_label=profile.label,
            summary=summary,
            claims=claims,
            evidence=gate_result.evidence,
            coverage=gate_result.coverage,
            missing_fields=gate_result.missing_fields,
            corpus_version=self.store.corpus_version,
            query_trace=traces,
            latency_ms=latency_ms,
        )


engine = EvidenceEngine()

