# Next-level architecture: product modes, SQL and governed evidence

## What changed

The three UI modes now have distinct retrieval budgets:

| Mode | k progression | Product intent |
| --- | --- | --- |
| Quick | `1 → 3` | Low latency, at most two visible claims |
| Deep | `1 → 3 → 5 → 8` | Maximum diagnostic coverage and traces |
| Structured summary | `3 → 5 → 8` | Wider initial batch for multi-evidence briefs |

All modes still use the same deterministic evidence gate. A shorter mode can never turn a
partial contract into a complete one.

## SQL analytical route

Questions asking for a comparison, ranking, minimum, maximum or average of prudential
metrics are routed to SQLite instead of top-k retrieval. The runtime table is built only
from promoted numeric facts already present in the reviewed corpus. SQL templates are
allow-listed, parameterized and read-only. Scope, entity and period remain filters.

The response exposes the executed template, bound parameters, row count and source for
every returned value. Gemini does not write or execute SQL in this implementation.

For an explicitly mixed question (calculation plus explanation), SQL first selects the
winning entity and BM25 retrieves up to two related narrative passages from the selected
reports. Numeric evidence and narrative context remain separate in the response model, so
an unreviewed passage cannot silently become a promoted financial fact.

## Table evidence lifecycle

`EXTRACTED → CANDIDATE → VALIDATED → PROMOTED`

- **Extracted:** reconstructed by a parser; useful for inspection.
- **Candidate:** partly compatible with the business catalogue but missing checks.
- **Validated:** passed structural and semantic checks; this is a conceptual review stage.
- **Promoted:** may enter the deployed evidence corpus.

Promotion currently requires an allow-listed QRT row, column `C0010`, a numeric value,
page and bounding-box provenance, and the expected value type. This is intentionally
targeted rather than universal table understanding.

## Scan routing

If at least two thirds of the first three pages contain fewer than 40 native-text
characters, or the sample itself is shorter than 40 characters, the document is routed
to `SCANNED_DOCUMENT`. Docling then enables OCR and table-structure extraction.

The automated test proves routing with an image-only/blank PDF fixture. It does **not**
prove OCR accuracy. Production acceptance requires labelled scanned pages covering skew,
low resolution, handwriting, decimal separators and complex tables.

## Scale boundary

The in-memory SQLite table is suitable for the six-document demonstrator. At material
volume it should become a governed analytical store (PostgreSQL, warehouse or lakehouse),
while narrative chunks move to a persistent lexical/vector index. Ingestion should be
asynchronous, idempotent and observable, with failed documents quarantined.
