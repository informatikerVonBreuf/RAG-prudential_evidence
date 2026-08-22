from __future__ import annotations

from app.domain.models import Candidate, Chunk, ScoreTrace, SearchQuery
from app.retrieval.dense import LocalDenseIndex
from app.retrieval.lexical import BM25Index


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], rrf_constant: int = 60, dense_index=None) -> None:
        self.chunks = chunks
        self.lexical = BM25Index(chunks)
        self.dense = dense_index or LocalDenseIndex(chunks)
        self.rrf_constant = rrf_constant

    def search(self, query: SearchQuery, k: int = 5) -> list[Candidate]:
        lexical_results = self.lexical.search(query.text)
        dense_results = self.dense.search(query.text)
        lexical_ranks = {chunk.id: rank for rank, (chunk, _) in enumerate(lexical_results, 1)}
        dense_ranks = {chunk.id: rank for rank, (chunk, _) in enumerate(dense_results, 1)}
        lexical_scores = {chunk.id: score for chunk, score in lexical_results}
        dense_scores = {chunk.id: score for chunk, score in dense_results}

        candidates: list[Candidate] = []
        for chunk in self.chunks:
            lexical_rank = lexical_ranks.get(chunk.id)
            dense_rank = dense_ranks.get(chunk.id)
            rrf_score = 0.0
            if lexical_rank is not None:
                rrf_score += 1 / (self.rrf_constant + lexical_rank)
            if dense_rank is not None:
                rrf_score += 1 / (self.rrf_constant + dense_rank)
            candidates.append(
                Candidate(
                    field_id=query.field_id,
                    chunk=chunk,
                    score=ScoreTrace(
                        lexical_rank=lexical_rank,
                        dense_rank=dense_rank,
                        lexical_score=round(lexical_scores.get(chunk.id, 0), 6),
                        dense_score=round(dense_scores.get(chunk.id, 0), 6),
                        rrf_score=round(rrf_score, 8),
                    ),
                )
            )
        return sorted(candidates, key=lambda item: (-item.score.rrf_score, item.chunk.id))[:k]
