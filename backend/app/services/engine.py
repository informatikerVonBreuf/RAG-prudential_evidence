from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

from app.analytics.service import PrudentialAnalytics
from app.domain.mapping import HybridQuestionMapper
from app.domain.models import (
    AnswerPayload,
    AnswerStatus,
    Mode,
    QueryTrace,
    QuestionRequest,
    RetrievalRunTrace,
)
from app.evidence.gate import DeterministicEvidenceGate
from app.generation.composer import GroundedComposer
from app.generation.providers import OptionalGeminiComposer
from app.retrieval.dense import FallbackDenseIndex, GeminiDenseIndex, LocalDenseIndex
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.planner import plan_queries
from app.retrieval.references import resolve_references
from app.store.artifacts import ArtifactStore, store


def choose_retrieval_strategy(field_count: int) -> str:
    return "sequential_top1" if field_count == 1 else "batch_multi_field"


def stop_reason_for_status(status: AnswerStatus) -> str:
    if status == AnswerStatus.COMPLETE:
        return "contract_complete"
    if status == AnswerStatus.CONFLICT:
        return "conflict"
    return "budget_exhausted"


def retrieval_budget(mode: Mode) -> tuple[int, ...]:
    """Give each product mode a real, inspectable retrieval budget."""
    if mode == Mode.QUICK:
        return (1, 3)
    if mode == Mode.SUMMARY:
        return (3, 5, 8)
    return (1, 3, 5, 8)


class EvidenceEngine:
    def __init__(self, artifact_store: ArtifactStore = store) -> None:
        self.store = artifact_store
        self.gate = DeterministicEvidenceGate()
        self.composer = GroundedComposer()
        self.online_composer = OptionalGeminiComposer()
        self.mapper = HybridQuestionMapper()
        self.analytics = PrudentialAnalytics(artifact_store)
        self._retrievers: dict[tuple[str, ...], HybridRetriever] = {}

    async def answer(self, request: QuestionRequest) -> AnswerPayload:
        if self.analytics.can_handle(request.question):
            return self.analytics.answer(request)
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
        queries = plan_queries(
            request.question,
            profile,
            selected_document_ids,
            request.conversation_context,
        )
        scope_key = tuple(selected_document_ids)
        retriever = self._retrievers.get(scope_key)
        if retriever is None:
            retriever = self._build_retriever(selected_chunks)
            self._retrievers[scope_key] = retriever

        strategy = choose_retrieval_strategy(len(profile.fields))
        k_budget = retrieval_budget(request.mode)
        resolved_references: list[str] = []
        unresolved_references: list[str] = []
        candidate_batches = []
        gate_result = None
        for k in k_budget:
            tasks = [asyncio.to_thread(retriever.search, query, k) for query in queries]
            candidate_batches = await asyncio.gather(*tasks)
            unique_candidates = {}
            for batch in candidate_batches:
                resolution = resolve_references(batch, selected_chunks)
                resolved_references.extend(resolution.resolved)
                unresolved_references.extend(resolution.unresolved)
                for candidate in resolution.candidates:
                    key = (candidate.field_id, candidate.chunk.id)
                    current = unique_candidates.get(key)
                    if current is None or candidate.score.rrf_score > current.score.rrf_score:
                        unique_candidates[key] = candidate
            gate_result = self.gate.evaluate(
                profile, list(unique_candidates.values()), mapped.constraints
            )
            if gate_result.status in {AnswerStatus.COMPLETE, AnswerStatus.CONFLICT}:
                break
        assert gate_result is not None
        stop_reason = stop_reason_for_status(gate_result.status)
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
            retrieval_run=RetrievalRunTrace(
                strategy=strategy,
                dense_provider=retriever.dense.provider,
                rounds=k_budget.index(k) + 1,
                k_history=list(k_budget[: k_budget.index(k) + 1]),
                stop_reason=stop_reason,
                resolved_references=list(dict.fromkeys(resolved_references)),
                unresolved_references=list(dict.fromkeys(unresolved_references)),
            ),
        )

    def _build_retriever(self, selected_chunks):
        index_directory = (
            Path(__file__).parents[1] / "data" / "indexes" / "foyer_group_qrt_2025_gemini"
        )
        try:
            primary = GeminiDenseIndex(selected_chunks, index_directory)
            dense = FallbackDenseIndex(primary, LocalDenseIndex(selected_chunks))
        except (OSError, ValueError, KeyError):
            dense = None
        return HybridRetriever(selected_chunks, dense_index=dense)


engine = EvidenceEngine()
