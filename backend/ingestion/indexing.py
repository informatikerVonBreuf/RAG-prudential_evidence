from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from ingestion.models import ChunkArtifact


def build_embedding_cache(
    chunks: list[ChunkArtifact], output_directory: Path, provider: str = "hashing-baseline"
) -> dict[str, object]:
    texts = [chunk.contextualized_text for chunk in chunks]
    if provider == "local-model":
        vectors, model = _local_embeddings(texts)
        is_trained_model = True
    elif provider == "gemini":
        vectors, model = _gemini_embeddings(texts)
        is_trained_model = True
    elif provider == "hashing-baseline":
        from app.retrieval.dense import _hash_embedding

        vectors = [_hash_embedding(text) for text in texts]
        model = "deterministic-token-trigram-hashing"
        is_trained_model = False
    else:
        raise ValueError(f"Fournisseur d'embeddings inconnu : {provider}")

    output_directory.mkdir(parents=True, exist_ok=True)
    payload = {chunk.id: vector for chunk, vector in zip(chunks, vectors, strict=True)}
    (output_directory / "embeddings.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    manifest = {
        "provider": provider,
        "model": model,
        "is_trained_embedding_model": is_trained_model,
        "dimensions": len(vectors[0]) if vectors else 0,
        "chunks": len(chunks),
        "content_sha256": hashlib.sha256(
            "\n".join(f"{chunk.id}:{chunk.contextualized_text}" for chunk in chunks).encode()
        ).hexdigest(),
    }
    (output_directory / "embedding_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def _local_embeddings(texts: list[str]) -> tuple[list[list[float]], str]:
    model_path = os.getenv("LOCAL_EMBEDDING_MODEL_PATH", "").strip()
    if not model_path or not Path(model_path).exists():
        raise RuntimeError("LOCAL_EMBEDDING_MODEL_PATH doit pointer vers des poids locaux.")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_path, local_files_only=True)
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist(), model_path


def _gemini_embeddings(texts: list[str]) -> tuple[list[list[float]], str]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_EMBEDDING_MODEL", "").strip()
    if not api_key or not model:
        raise RuntimeError("GEMINI_API_KEY et GEMINI_EMBEDDING_MODEL sont requis.")
    from google import genai

    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(model=model, contents=texts)
    return [embedding.values for embedding in result.embeddings], model
