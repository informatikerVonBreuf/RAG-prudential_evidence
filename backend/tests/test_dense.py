import hashlib
import json
from pathlib import Path

import pytest
from app.domain.models import Chunk, SourceLocator
from app.retrieval.dense import GeminiDenseIndex


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id="doc",
        text=text,
        locator=SourceLocator(
            document_id="doc",
            document_title="Document",
            version="1",
            source_url="https://example.test",
            page=1,
            section_path=[],
        ),
    )


def test_gemini_dense_index_uses_cached_query_without_network(tmp_path: Path) -> None:
    chunks = [_chunk("a", "alpha"), _chunk("b", "beta")]
    model = "gemini-embedding-001"
    query = "alpha question"
    cache_key = hashlib.sha256(f"{model}:{query}".encode()).hexdigest()
    (tmp_path / "embedding_manifest.json").write_text(
        json.dumps(
            {
                "provider": "gemini",
                "model": model,
                "is_trained_embedding_model": True,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "embeddings.json").write_text(
        json.dumps({"a": [1.0, 0.0], "b": [0.0, 1.0]}), encoding="utf-8"
    )
    (tmp_path / "query_embeddings.json").write_text(
        json.dumps({cache_key: [1.0, 0.0]}), encoding="utf-8"
    )

    index = GeminiDenseIndex(chunks, tmp_path)

    assert index.search(query)[0][0].id == "a"
    assert index.provider == "gemini"


def test_gemini_dense_index_rejects_hashing_manifest(tmp_path: Path) -> None:
    (tmp_path / "embedding_manifest.json").write_text(
        json.dumps(
            {
                "provider": "hashing-baseline",
                "model": "deterministic-token-trigram-hashing",
                "is_trained_embedding_model": False,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "embeddings.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="not a trained Gemini"):
        GeminiDenseIndex([_chunk("a", "alpha")], tmp_path)
