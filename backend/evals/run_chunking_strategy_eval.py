from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from app.domain.models import Chunk
from app.retrieval.dense import GeminiDenseIndex
from app.store.artifacts import store
from dotenv import load_dotenv
from evals.chunking_strategies import (
    RetrievalCase,
    contextualized_chunks,
    evaluate_rankings,
    flat_ranking,
    hierarchical_ranking,
    load_context_cache,
    save_context_cache,
)
from ingestion.indexing import build_runtime_embedding_cache

ROOT = Path(__file__).parents[2]
EXPERIMENT_DIRECTORY = ROOT / "data" / "processed" / "chunking_strategy_experiment"
DOCUMENT_ID = "foyer_group_qrt_2025"

CASES = [
    RetrievalCase(
        "natural_coverage_en",
        "What public evidence describes Groupe Foyer prudential coverage in 2025?",
        ("R0660", "R0680", "R0690"),
    ),
    RetrievalCase(
        "natural_coverage_fr",
        "Quels éléments prouvent la couverture prudentielle du Groupe Foyer en 2025 ?",
        ("R0660", "R0680", "R0690"),
    ),
    RetrievalCase(
        "eligible_own_funds",
        "Fonds propres éligibles couvrant le SCR du Groupe",
        ("R0660",),
    ),
    RetrievalCase(
        "group_scr",
        "Montant du capital de solvabilité requis du Groupe",
        ("R0680",),
    ),
    RetrievalCase(
        "coverage_ratio",
        "Ratio entre fonds propres éligibles et SCR du Groupe",
        ("R0690",),
    ),
    RetrievalCase(
        "row_code",
        "S.23.01.22 R0690 C0010",
        ("R0690",),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dense", choices=("local", "gemini"), default="local")
    parser.add_argument("--generate-contexts", action="store_true")
    parser.add_argument("--force-contexts", action="store_true")
    return parser.parse_args()


def context_prompt(chunk: Chunk, document_outline: str) -> str:
    return f"""You prepare retrieval context for an audited insurance document.
Write one factual English sentence of at most 70 words explaining where the chunk belongs
and what it contributes. Use only the outline and chunk. Preserve entity, period, QRT codes,
table identifiers and defined terminology. Do not infer a value or add an interpretation.

DOCUMENT OUTLINE:
{document_outline}

CHUNK SECTION: {' > '.join(chunk.locator.section_path)}
CHUNK:
{chunk.text}

Return only the contextual sentence."""


def generate_contexts(chunks: list[Chunk], force: bool = False) -> dict[str, str]:
    cache_path = EXPERIMENT_DIRECTORY / "contextual_contexts.json"
    contexts = {} if force else load_context_cache(cache_path)
    missing = [chunk for chunk in chunks if chunk.id not in contexts]
    if not missing:
        return contexts
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_GENERATION_MODEL", "").strip()
    if not api_key or not model:
        raise RuntimeError("Gemini generation configuration is required for contextual chunks.")
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass
    from google import genai

    client = genai.Client(api_key=api_key)
    outline = "\n".join(
        sorted({" > ".join(chunk.locator.section_path) for chunk in chunks})
    )
    workers = min(int(os.getenv("CONTEXT_GENERATION_WORKERS", "6")), len(missing))

    def generate(chunk: Chunk) -> tuple[str, str]:
        response = client.models.generate_content(
            model=model, contents=context_prompt(chunk, outline)
        )
        return chunk.id, (response.text or "").strip()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(generate, chunk): chunk.id for chunk in missing}
        for index, future in enumerate(as_completed(futures), start=1):
            chunk_id, context = future.result()
            contexts[chunk_id] = context
            save_context_cache(cache_path, contexts)
            print(f"context {index}/{len(missing)}: {chunk_id}", flush=True)
    return contexts


def dense_factory(strategy: str):
    def factory(chunks: list[Chunk]) -> GeminiDenseIndex:
        identity = hashlib.sha256(
            "\n".join(f"{chunk.id}:{chunk.text}" for chunk in chunks).encode()
        ).hexdigest()[:12]
        directory = EXPERIMENT_DIRECTORY / "gemini" / strategy / identity
        if not (directory / "embeddings.json").exists():
            build_runtime_embedding_cache(chunks, directory)
        return GeminiDenseIndex(chunks, directory)

    return factory


def main() -> None:
    args = parse_args()
    load_dotenv(ROOT / ".env")
    baseline = [chunk for chunk in store.chunks if chunk.document_id == DOCUMENT_ID]
    contexts = (
        generate_contexts(baseline, force=args.force_contexts)
        if args.generate_contexts
        else load_context_cache(EXPERIMENT_DIRECTORY / "contextual_contexts.json")
    )
    variants = {
        "current_flat": baseline,
        "structural_context": contextualized_chunks(baseline),
    }
    if contexts:
        variants["gemini_contextual"] = contextualized_chunks(baseline, contexts)

    results: dict[str, dict[str, object]] = {}
    for name, chunks in variants.items():
        started = time.perf_counter()
        factory = dense_factory(name) if args.dense == "gemini" else None
        metrics = evaluate_rankings(
            CASES,
            lambda query, items=chunks, dense=factory: (
                flat_ranking(items, query, dense), len(items)
            ),
        )
        results[name] = {
            **asdict(metrics), "chunks": len(chunks),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "context_provider": "gemini" if name == "gemini_contextual" else "none",
        }

    started = time.perf_counter()
    hierarchical_factory = dense_factory("hierarchical") if args.dense == "gemini" else None
    hierarchical = evaluate_rankings(
        CASES,
        lambda query: hierarchical_ranking(
            baseline, query, parent_k=3, dense_factory=hierarchical_factory
        ),
    )
    results["hierarchical_parent_child"] = {
        **asdict(hierarchical), "chunks": len(baseline),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "parent_k": 3,
    }
    payload = {
        "document_id": DOCUMENT_ID,
        "dense_provider": args.dense,
        "cases": len(CASES),
        "results": results,
        "warning": (
            "Gemini contextual variant was not run; use --generate-contexts."
            if not contexts else None
        ),
    }
    EXPERIMENT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    (EXPERIMENT_DIRECTORY / f"results_{args.dense}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
