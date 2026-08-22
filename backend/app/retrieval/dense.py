from __future__ import annotations

import hashlib
import json
import math
import os
from contextlib import suppress
from pathlib import Path

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
    provider = "hashing-baseline"

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


class GeminiDenseIndex:
    """Gemini query embeddings over cached Gemini document vectors."""

    provider = "gemini"

    def __init__(self, chunks: list[Chunk], index_directory: Path) -> None:
        manifest_path = index_directory / "embedding_manifest.json"
        vectors_path = index_directory / "embeddings.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cached = json.loads(vectors_path.read_text(encoding="utf-8"))
        if manifest.get("provider") != "gemini" or not manifest.get(
            "is_trained_embedding_model"
        ):
            raise ValueError("The selected cache is not a trained Gemini embedding index.")
        missing = [chunk.id for chunk in chunks if chunk.id not in cached]
        if missing:
            raise ValueError(f"Gemini cache is missing {len(missing)} selected chunks.")
        self.chunks = chunks
        self.vectors = [cached[chunk.id] for chunk in chunks]
        self.model = str(manifest["model"])
        self.query_cache_path = index_directory / "query_embeddings.json"
        self.query_cache = (
            json.loads(self.query_cache_path.read_text(encoding="utf-8"))
            if self.query_cache_path.exists()
            else {}
        )

    def search(self, query: str) -> list[tuple[Chunk, float]]:
        cache_key = hashlib.sha256(f"{self.model}:{query}".encode()).hexdigest()
        query_vector = self.query_cache.get(cache_key)
        if query_vector is None:
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is required for dense query embedding.")
            try:
                import truststore

                truststore.inject_into_ssl()
            except ImportError:
                pass
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model=self.model,
                contents=query,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
            )
            query_vector = response.embeddings[0].values
            self.query_cache[cache_key] = query_vector
            with suppress(OSError):
                self.query_cache_path.write_text(
                    json.dumps(self.query_cache, ensure_ascii=False), encoding="utf-8"
                )
        results = [
            (chunk, sum(left * right for left, right in zip(query_vector, vector, strict=True)))
            for chunk, vector in zip(self.chunks, self.vectors, strict=True)
        ]
        return sorted(results, key=lambda item: (-item[1], item[0].id))


class FallbackDenseIndex:
    """Use a trained index when available and survive provider/cache misses honestly."""

    def __init__(self, primary: GeminiDenseIndex, fallback: LocalDenseIndex) -> None:
        self.primary = primary
        self.fallback = fallback
        self.fallback_used = False

    @property
    def provider(self) -> str:
        return "gemini+hashing-fallback" if self.fallback_used else self.primary.provider

    def search(self, query: str) -> list[tuple[Chunk, float]]:
        try:
            return self.primary.search(query)
        except Exception:  # provider/cache failures must preserve deterministic retrieval
            self.fallback_used = True
            return self.fallback.search(query)
