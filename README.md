# Prudential Evidence Lab

An auditable document-research application built from public Groupe Foyer reports and
Solvency II QRTs. It turns a user question into a versioned evidence contract, retrieves
the required facts independently, verifies scope, entity and period, and only then composes
a cited answer.

**Live application:** https://prudential-evidence-lab.onrender.com/

> Demo tip: click **Nouvelle analyse** before testing a different scenario. This clears the
> active conversation context and recalculates the mapping, retrieval scope and answer status.

## Why this project

A conventional RAG can return a fluent answer while silently omitting a required fact,
mixing legal entities or using evidence from the wrong reporting period. Prudential Evidence
Lab makes these failure modes visible. A response is classified as `COMPLETE`, `PARTIAL`,
`CONFLICT` or `NOT_FOUND` by code, not by the generation model.

The project demonstrates one coherent workflow for the three retrieval patterns discussed
in the accompanying engineering brief:

- `sequential_top1` for a single-field contract;
- `batch_multi_field` for a multi-evidence contract;
- bounded reference resolution and explicit stopping conditions.

## What is implemented

- Six public 2025 PDFs: three narrative reports and three tabular QRTs
- Offline PDF processing with Docling and a PyMuPDF fallback
- Reviewed Markdown artifacts for text, tables and Gemini-described figures
- Structure-aware chunks carrying document, page, section, table, row and cell provenance
- Rich, versioned French/English evidence profiles
- Deterministic entity and period extraction with abstention on unresolved ambiguity
- Rules-first intent mapping, optional Gemini similarity and a bounded LLM judge only for
  genuinely ambiguous cases
- Explicit query reformulation for every required evidence field
- Hybrid retrieval using BM25, Gemini dense embeddings and Reciprocal Rank Fusion (RRF)
- Controlled widening through `k=1 → 3 → 5`
- Reproducible flat vs contextual vs hierarchical parent/child chunking benchmark
- Resolution of explicit `see section` / `voir section` references, with at most three
  followed references per batch
- Stop reasons exposed as `contract_complete`, `conflict` or `budget_exhausted`
- A deterministic evidence gate enforcing scope, entity, period and fact compatibility
- Gemini synthesis restricted to accepted evidence, with deterministic composition available
- Per-claim citations and visible lexical, dense and RRF traces
- Responsive React interface with quick, deep-analysis and structured-summary workflows
- Resumable browser-local threads with bounded memory derived only from accepted facts

No LangChain or LlamaIndex abstraction is used. The mapping, planning, retrieval,
orchestration, evidence validation and answer contracts are directly inspectable in the code.

## Demonstrated prudential contract

The primary use case asks for Groupe Foyer's published 2025 prudential coverage. The contract
requires three separately retrieved and verified fields from public table `S.23.01.22`:

| Required field | QRT locator |
|---|---|
| Eligible own funds covering the Group SCR | `R0660 / C0010` |
| Group Solvency Capital Requirement | `R0680 / C0010` |
| Group SCR coverage ratio | `R0690 / C0010` |

The answer can only be `COMPLETE` when all required fields pass the gate for the requested
entity, period and document scope. The same pattern is implemented for the Foyer Assurances
and Foyer Global Health legal-entity QRTs.

## Architecture

```text
User question
    ↓
Bilingual intent mapping + entity/period extraction
    ↓
Versioned evidence profile
    ↓
One inspectable query set per required field
    ↓
BM25 + Gemini dense retrieval → RRF
    ↓
Bounded retrieval loop + explicit reference resolution
    ↓
Deterministic evidence gate
    ↓
Cited deterministic/Gemini composition
    ↓
Business UI + coverage, source and model-call traces
```

| Layer | Main implementation |
|---|---|
| Business contracts and mapping | `backend/app/domain` |
| Retrieval planner and hybrid search | `backend/app/retrieval` |
| Scope and evidence validation | `backend/app/evidence` |
| Controlled answer composition | `backend/app/generation` |
| Runtime orchestration | `backend/app/services/engine.py` |
| REST API and OpenAPI schema | `backend/app/api` |
| Offline document pipeline | `backend/ingestion` |
| React evidence interface | `frontend/src` |
| Experiments and acceptance notebooks | `notebooks` |

Detailed diagrams and code mappings are available in
[`docs/architecture/README.md`](docs/architecture/README.md).

## Technology stack

**AI and retrieval:** Google Gemini API, Gemini Embeddings, BM25, RRF, parameterized
SQLite analytics, deterministic evidence contracts and an optional bounded LLM judge.

**Document processing:** Docling, PyMuPDF, Markdown artifacts and Jupyter notebooks.

**Application:** Python, FastAPI, Pydantic, React, TypeScript and Vite.

**Quality and delivery:** Pytest, Ruff, Docker multi-stage builds, GitHub Actions and Render.

## Evaluation results

The current acceptance suite contains positive, partial, wrong-scope, wrong-entity,
wrong-period and deliberately ambiguous cases.

| Metric | Result |
|---|---:|
| Backend tests | 59 passed |
| Golden evaluation cases | 30 / 30 |
| Mapping accuracy | 100% |
| Required-field recall | 100% |
| Citation precision | 100% |
| False-completeness rate | 0% |

These values describe the committed demonstration corpus and evaluation set; they are not
presented as general production benchmarks. See [`docs/EVALUATION.md`](docs/EVALUATION.md)
for metric definitions and individual cases.

## Run locally

Requirements: Python 3.12+, Node.js 22+ and, for online model calls, a Gemini API key.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,online-models]"
cd frontend
npm ci
cd ..
```

Copy `.env.example` to `.env`, then configure the required model variables. Never commit the
real `.env` file or an API key.

Start the API and frontend in two terminals:

```bash
make dev-api
make dev-front
```

- Application: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

Alternatively, use the same container path as the deployment:

```bash
docker build -t prudential-evidence-lab .
docker run --env-file .env -p 8000:8000 prudential-evidence-lab
```

## Validation commands

```bash
make lint
make validate-corpus
make test
make eval
make build-front
```

The notebooks document environment setup, corpus provenance, PDF/table extraction,
multimodal descriptions, embeddings, hybrid retrieval, evidence gating, chunk-size limits,
runtime orchestration, hierarchical/contextual chunking and the complete acceptance matrix.
Notebook 12 demonstrates distinct product-mode budgets, exhaustive SQL queries over promoted
QRT facts, the table-evidence lifecycle and scan routing. See
[`docs/NEXT_LEVEL_ARCHITECTURE.md`](docs/NEXT_LEVEL_ARCHITECTURE.md).

The latest chunking experiment finds that parent/child routing improves MRR from 0.603 to
0.693 and reduces mean candidates from 87 to 49 on the principal QRT, while Gemini-generated
chunk context improves some natural questions but reduces aggregate Recall@5. It therefore
remains an offline selective enrichment rather than the production default. See
[`docs/HIERARCHICAL_CONTEXTUAL_CHUNKING.md`](docs/HIERARCHICAL_CONTEXTUAL_CHUNKING.md).

## Honest boundaries

- The included corpus is small and deliberately curated for a technical demonstration.
- PDF extraction is an offline, reviewed pipeline—not universal automated PDF ingestion.
- Gemini dense embeddings are the intended dense retrieval path. If they are unavailable,
  the runtime explicitly reports `gemini+hashing-fallback`; hashing is only a deterministic
  resilience baseline and is never presented as a semantic embedding model.
- Explicit reference resolution currently supports numbered section references only.
- Browser conversation history is local and is not a regulated system of record.
- There are no user accounts, background ingestion workers or distributed orchestration.
- The OCR test validates scan routing, not production OCR accuracy on a representative corpus.
- SQLite is an in-memory demonstrator over promoted facts, not the target analytical store at scale.
- At larger scale, local retrieval should move to a vector store such as pgvector, Qdrant or
  FAISS, with asynchronous ingestion, document-version governance and observability.

## Deployment

`render.yaml` and the multi-stage `Dockerfile` provide the current Render deployment path.
GitHub Actions runs quality checks and the container build before release. Operational details,
environment variables and offline-ingestion steps are documented in
[`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Data and provenance

Only public Groupe Foyer documents and reviewed derived artifacts are included. Source URLs,
page counts and checksums are listed in
[`docs/PUBLIC_SOURCES_2025.md`](docs/PUBLIC_SOURCES_2025.md).
