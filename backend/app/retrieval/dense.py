from __future__ import annotations

import hashlib
import math

from app.domain.models import Chunk
from app.retrieval.text import tokenize


def _hash_embedding(text: str, dimensions: int = 384) -> list[float]:
    """Deterministic local semantic baseline with no provider or model download.

    It is deliberately an adapter-compatible baseline, not a claim of parity with a
    trained embedding model. Character trigrams improve robustness to morphology.
    """

    vector = [0.0] * dimensions
    tokens = tokenize(text)
    features = list(tokens)
    for token in tokens:
        padded = f"^{token}$"
        features.extend(padded[i : i + 3] for i in range(max(len(padded) - 2, 0)))
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class LocalDenseIndex:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.vectors = [_hash_embedding(chunk.text) for chunk in chunks]

    def search(self, query: str) -> list[tuple[Chunk, float]]:
        query_vector = _hash_embedding(query)
        results = [
            (chunk, sum(left * right for left, right in zip(query_vector, vector, strict=True)))
            for chunk, vector in zip(self.chunks, self.vectors, strict=True)
        ]
        return sorted(results, key=lambda item: (-item[1], item[0].id))

