from __future__ import annotations

import math
from collections import Counter

from app.domain.models import Chunk
from app.retrieval.text import tokenize


class BM25Index:
    """Small, explicit BM25 implementation suitable for the reviewed MVP corpus."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.term_frequencies = [Counter(tokens) for tokens in self.tokens]
        self.document_frequency: Counter[str] = Counter()
        for tokens in self.tokens:
            self.document_frequency.update(set(tokens))
        self.average_length = sum(map(len, self.tokens)) / max(len(self.tokens), 1)

    def search(self, query: str) -> list[tuple[Chunk, float]]:
        query_terms = tokenize(query)
        total = len(self.chunks)
        results: list[tuple[Chunk, float]] = []
        for index, chunk in enumerate(self.chunks):
            length = len(self.tokens[index])
            score = 0.0
            for term in query_terms:
                frequency = self.term_frequencies[index][term]
                if not frequency:
                    continue
                document_frequency = self.document_frequency[term]
                inverse_document_frequency = math.log(
                    1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / max(self.average_length, 1)
                )
                score += inverse_document_frequency * frequency * (self.k1 + 1) / denominator
            results.append((chunk, score))
        return sorted(results, key=lambda item: (-item[1], item[0].id))

