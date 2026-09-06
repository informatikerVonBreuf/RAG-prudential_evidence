from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.domain.profiles import map_question  # noqa: E402
from app.retrieval.dense import LocalDenseIndex  # noqa: E402
from app.retrieval.hybrid import HybridRetriever  # noqa: E402
from app.retrieval.lexical import BM25Index  # noqa: E402
from app.retrieval.planner import plan_queries  # noqa: E402
from app.store.artifacts import store  # noqa: E402


def evaluate(k: int = 5) -> dict[str, object]:
    goldens = json.loads(
        Path(__file__).with_name("golden_questions.json").read_text(encoding="utf-8")
    )
    totals = {"bm25": 0, "hashing_baseline": 0, "hybrid": 0}
    expected_total = 0
    cases = 0
    for golden in goldens:
        expected = set(golden["expected_fields"])
        if not expected or golden["expected_profile"] == "prudential_sql_comparison":
            continue
        chunks = store.selected_chunks(golden["document_ids"])
        profile = map_question(golden["question"], golden.get("profile_id"))
        queries = plan_queries(golden["question"], profile, golden["document_ids"])
        lexical = BM25Index(chunks)
        dense = LocalDenseIndex(chunks)
        hybrid = HybridRetriever(chunks, dense_index=dense)
        covered = {name: set() for name in totals}
        for query in queries:
            result_sets = {
                "bm25": [chunk for chunk, score in lexical.search(query.text)[:k]],
                "hashing_baseline": [chunk for chunk, score in dense.search(query.text)[:k]],
                "hybrid": [candidate.chunk for candidate in hybrid.search(query, k)],
            }
            for name, results in result_sets.items():
                if any(
                    fact.field_id == query.field_id
                    for chunk in results
                    for fact in chunk.facts
                ):
                    covered[name].add(query.field_id)
        for name in totals:
            totals[name] += len(covered[name] & expected)
        expected_total += len(expected)
        cases += 1
    return {
        "cases": cases,
        "k": k,
        "metric": "required-field recall at k",
        "results": {name: value / expected_total for name, value in totals.items()},
        "dense_note": (
            "hashing_baseline is a deterministic diagnostic, not a trained embedding model; "
            "Gemini quality is evaluated separately when an online key is enabled"
        ),
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2))
