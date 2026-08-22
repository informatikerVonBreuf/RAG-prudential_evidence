from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import Chunk, SearchQuery, SourceLocator
from app.retrieval.dense import GeminiDenseIndex
from app.retrieval.hybrid import HybridRetriever
from dotenv import load_dotenv
from ingestion.chunking import chunk_pages
from ingestion.exporters import read_result

ROOT = Path(__file__).parents[2]
SIZES = (900, 1800, 3000, 4800)
QUERIES = {
    "natural": "What public evidence describes Groupe Foyer's prudential coverage in 2025?",
    "regulatory_labels": "Eligible own funds, group SCR and SCR coverage ratio",
    "row_codes": "S.23.01.22 R0660 R0680 R0690 C0010",
    "underspecified": "Foyer solvency",
}


def main() -> None:
    load_dotenv(ROOT / ".env")
    source = read_result(ROOT / "data" / "processed" / "foyer_group_qrt_2025")
    results = []
    for size in SIZES:
        artifacts = chunk_pages(
            source.manifest.document_id,
            source.manifest.title,
            source.pages,
            source.manifest.entity,
            source.manifest.period,
            max_characters=size,
        )
        chunks = [
            Chunk(
                id=item.id,
                document_id=item.document_id,
                chunk_type=f"experimental_page_text_{size}",
                text=item.contextualized_text,
                locator=SourceLocator(
                    document_id=item.document_id,
                    document_title=source.manifest.title,
                    version=source.manifest.sha256[:12],
                    source_url=source.manifest.source_url,
                    page=item.page_start,
                    section_path=item.section_path,
                ),
            )
            for item in artifacts
        ]
        dense = GeminiDenseIndex(
            chunks, ROOT / "data" / "processed" / "chunk_size_experiment" / str(size)
        )
        retriever = HybridRetriever(chunks, dense_index=dense)
        for case_id, text in QUERIES.items():
            query = SearchQuery(
                field_id="diagnostic",
                field_label="Diagnostic",
                text=text,
                document_ids=[source.manifest.document_id],
            )
            ranking = retriever.search(query, k=len(chunks))
            target_ranks = [
                rank
                for rank, candidate in enumerate(ranking, start=1)
                if any(code in candidate.chunk.text for code in ("R0660", "R0680", "R0690"))
            ]
            results.append(
                {
                    "max_characters": size,
                    "chunks": len(chunks),
                    "case": case_id,
                    "first_target_rrf_rank": min(target_ranks) if target_ranks else None,
                    "target_in_top_1": bool(target_ranks and min(target_ranks) <= 1),
                    "target_in_top_3": bool(target_ranks and min(target_ranks) <= 3),
                    "target_in_top_5": bool(target_ranks and min(target_ranks) <= 5),
                }
            )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
