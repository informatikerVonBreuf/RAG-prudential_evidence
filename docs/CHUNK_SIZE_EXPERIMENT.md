# Chunk-size experiment with Gemini embeddings

Run date: 22 August 2026. Model: `gemini-embedding-001` (3,072 dimensions).
Document embeddings use `RETRIEVAL_DOCUMENT`; query embeddings use `RETRIEVAL_QUERY`.

The experiment rebuilds page-text variants from the same ten-page Foyer Group QRT and
compares BM25 + Gemini cosine retrieval fused with RRF. The target is the first chunk
containing one of `R0660`, `R0680`, or `R0690`.

| Max characters | Chunks | Natural question rank | Regulatory-label rank | Row-code rank | Underspecified rank |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 900 | 113 | 39 | 1 | 4 | 22 |
| 1,800 | 73 | 36 | 1 | 5 | 14 |
| 3,000 | 56 | 31 | 1 | 5 | 12 |
| 4,800 | 50 | 39 | 1 | 5 | 26 |

## Decision

There is no evidence for changing the global default merely because Gemini returns
3,072-dimensional vectors. A 3,000-character window improved the weak natural and
underspecified cases in this page-based stress test, but exact regulatory labels were
already top-1 at every size and 4,800 characters degraded both weak cases. The production
default therefore remains 1,800 characters while the pipeline accepts an explicit range
of 600–6,000 for document-specific experiments.

The poor natural-question ranks also confirm the architectural requirement for field-level
query planning and verified evidence chunks. Chunk size alone does not solve intent-to-field
alignment. Notebook 04 demonstrates the planned-query path; notebook 08 exposes every
variant chunk and every BM25, Gemini cosine and RRF score.

Reproduce the compact evaluation with:

```powershell
python backend/evals/run_chunk_size_eval.py
```

Rebuild the ignored Gemini caches by setting `RUN_GEMINI_CHUNK_EXPERIMENT=1` before
executing notebook 08. API keys and cached vectors are not committed.
