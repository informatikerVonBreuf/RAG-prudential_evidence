# Hierarchical and contextual chunking experiment

Run date: 24 August 2026. Corpus: 87 reviewed chunks from the public 2025 Groupe
Foyer QRT. Dense model: `gemini-embedding-001`. Context model: the configured Gemini
generation model. All variants use BM25 + Gemini cosine retrieval fused with RRF.

## What was actually compared

| Variant | Definition |
|---|---|
| `current_flat` | Current reviewed chunks, already carrying document/entity/period/section metadata |
| `structural_context` | A second deterministic structural prefix added to each current chunk |
| `gemini_contextual` | A cached, chunk-specific sentence generated from the QRT outline and chunk, prepended before both BM25 and embedding |
| `hierarchical_parent_child` | Section parents are retrieved first (`parent_k=3`), then only their child chunks are ranked |

The hierarchical variant is not full RAPTOR: it does not recursively cluster and summarize
the corpus. It is a deliberately cheaper parent/child routing experiment that preserves exact
QRT child citations. The contextual variant adapts Anthropic's contextual-retrieval idea to
Gemini; it does not use Claude or Anthropic prompt caching.

## Results

| Strategy | Recall@1 | Recall@3 | Recall@5 | MRR | Mean candidates | Cached retrieval time |
|---|---:|---:|---:|---:|---:|---:|
| Current flat | 0.500 | 0.667 | 0.667 | 0.603 | 87 | 1.003 s |
| Repeated structural context | 0.167 | 0.500 | 0.500 | 0.383 | 87 | 0.955 s |
| Gemini contextual | 0.500 | 0.500 | 0.500 | 0.561 | 87 | 0.988 s |
| Hierarchical parent/child | **0.667** | **0.667** | **0.667** | **0.693** | **49** | **0.655 s** |

First relevant RRF rank by query:

| Query | Current | Structural | Gemini contextual | Hierarchical |
|---|---:|---:|---:|---:|
| Natural coverage (English) | 24 | 18 | 11 | 21 |
| Natural coverage (French) | 13 | 10 | 9 | 9 |
| Eligible own funds | 2 | 2 | 1 | 1 |
| Group SCR | 1 | 7 | 6 | 1 |
| Coverage ratio | 1 | 2 | 1 | 1 |
| Exact row code | 1 | 1 | 1 | 1 |

## Interpretation

1. **Parent/child routing is the best candidate for a controlled application experiment.**
   It raises MRR from 0.603 to 0.693, places four of six cases at rank 1 instead of three,
   and examines 49 rather than 87 candidates on average.
2. **LLM context helps the weakest natural questions but is not a universal gain.** The two
   natural-question ranks improve from 24/13 to 11/9 and eligible own funds improves from
   rank 2 to 1, but the Group SCR case falls from rank 1 to 6. Aggregate Recall@5 therefore
   decreases from 0.667 to 0.500.
3. **More context can dilute discriminative regulatory terms.** Repeating metadata already
   present in the current chunks produces the worst aggregate result.
4. **Exact QRT identifiers remain easy.** Every strategy retrieves the row-code question at
   rank 1. The architecture still needs field-level query planning for natural questions.

## Decision

Do not replace the production index with Gemini-contextual chunks on this evidence. Keep the
current chunks as the safe baseline and prototype hierarchical parent/child routing behind a
feature flag. Expand the evaluation to narrative SFCR/governance questions before enabling it
by default. Context generation should remain an offline, cached enrichment used selectively
for chunks whose entity, period or referent is genuinely ambiguous.

## Reproduction

Deterministic/local diagnostic:

```powershell
python backend/evals/run_chunking_strategy_eval.py
```

Generate missing Gemini contexts and evaluate with Gemini embeddings:

```powershell
python backend/evals/run_chunking_strategy_eval.py --generate-contexts --dense gemini
```

Context and embedding caches are written below `data/processed/chunking_strategy_experiment`
and remain outside Git. The scripts, tests, notebook outputs and aggregate reference results
are committed; API keys and generated caches are not.

## References

- Anthropic, [Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)
- Sarthi et al., [RAPTOR](https://arxiv.org/abs/2401.18059)
- Docling, [native chunking concepts](https://github.com/docling-project/docling/blob/main/docs/concepts/chunking.md)
