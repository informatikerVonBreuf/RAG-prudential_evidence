from __future__ import annotations

import asyncio
import time
import uuid

from app.domain.mapping import HybridQuestionMapper
from app.domain.models import AnswerPayload, QueryTrace, QuestionRequest
from app.evidence.gate import DeterministicEvidenceGate
from app.generation.composer import GroundedComposer
from app.generation.providers import OptionalGeminiComposer
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.planner import plan_queries
from app.store.artifacts import ArtifactStore, store


class EvidenceEngine:
    def __init__(self, artifact_store: ArtifactStore = store) -> None:
        self.store = artifact_store
        self.gate = DeterministicEvidenceGate()
        self.composer = GroundedComposer()
        self.online_composer = OptionalGeminiComposer()
        self.mapper = HybridQuestionMapper()
        self._retrievers: dict[tuple[str, ...], HybridRetriever] = {}

    async def answer(self, request: QuestionRequest) -> AnswerPayload:
        started = time.perf_counter()
        mapped = self.mapper.map(
            request.question,
            explicit_profile_id=request.profile_id,
            explicit_constraints=request.constraints,
        )
        profile = mapped.profile
        requested_scope = self.store.validate_document_ids(request.scope.document_ids)
        selected_chunks = self.store.selected_chunks(requested_scope)
        selected_document_ids = sorted({chunk.document_id for chunk in selected_chunks})
        queries = plan_queries(request.question, profile, selected_document_ids)
        scope_key = tuple(selected_document_ids)
        retriever = self._retrievers.get(scope_key)
        if retriever is None:
            retriever = HybridRetriever(selected_chunks)
            self._retrievers[scope_key] = retriever

        tasks = [asyncio.to_thread(retriever.search, query, 5) for query in queries]
        candidate_batches = await asyncio.gather(*tasks)
        unique_candidates = {}
        for batch in candidate_batches:
            for candidate in batch:
                key = (candidate.field_id, candidate.chunk.id)
                current = unique_candidates.get(key)
                if current is None or candidate.score.rrf_score > current.score.rrf_score:
                    unique_candidates[key] = candidate
        candidates = list(unique_candidates.values())
        gate_result = self.gate.evaluate(profile, candidates, mapped.constraints)
        summary, claims = self.composer.compose(
            question=request.question,
            mode=request.mode,
            status=gate_result.status,
            evidence=gate_result.evidence,
            missing_fields=gate_result.missing_fields,
        )
        generation_provider = "deterministic"
        online_result = await asyncio.to_thread(
            self.online_composer.compose, request.question, gate_result.evidence
        )
        if online_result.text:
            summary = online_result.text
            generation_provider = online_result.provider

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
            generation_provider=generation_provider,
            model_calls=[*mapped.decision.model_calls, online_result.trace],
            mapping_trace=mapped.decision.model_dump(mode="json"),
        )


engine = EvidenceEngine()
