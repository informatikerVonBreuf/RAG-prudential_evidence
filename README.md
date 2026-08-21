# 📊 Prudential Evidence Lab

![AI Agents](https://img.shields.io/badge/AI%20AGENTS-646cff?style=flat-square&logo=ai) ![Advanced](https://img.shields.io/badge/ADVANCED-0078d4?style=flat-square) ![RAG System](https://img.shields.io/badge/RAG%20SYSTEM-8a2be2?style=flat-square) ![Production](https://img.shields.io/badge/PRODUCTION-2ecc71?style=flat-square)

An auditable document assistant demonstrating a framework-less RAG (Retrieval-Augmented
Generation) architecture. User questions map to evidence contracts, are decomposed into
field queries, retrieved by multiple channels, validated deterministically, and composed
into traceable answers with per-assertion citations.

---

📌 Quick links: [Overview](#overview) • [Features](#key-capabilities) • [Tech & Structure](#project-structure) • [Quick Start](#quickstart) • [Usage](#usage)

---

## Overview

This repo is a deployment-ready prototype focused on traceability and reproducibility. Every
assertion includes a citation (page, section, table/cell, scores) and deterministic logic
decides claim statuses (`COMPLETE`, `PARTIAL`, `NOT_FOUND`, `CONFLICT`). The embedded
corpus is small and curated for demo purposes only.

## Problem Solved

- ⚡ Speeds up large-scale document research from hours to minutes
- 🔎 Extracts and synthesizes multi-format data (text, tables, PDFs)
- 🔁 Maintains research continuity across multi-step workflows
- 🧾 Provides cited, traceable analysis for compliance and validation

## Key Capabilities

- 📚 RAG System — Hybrid retrieval (BM25 + local dense baseline + RRF fusion)
- 🧭 Evidence Profiles — Versioned mapping from intents to fields and checks
- 🌐 Multimodal Support — Handles text, tables, and document fragments
- 🐍 Python + Web UI — FastAPI backend and React/TypeScript frontend

## Project Structure

```
backend/app/domain        # Pydantic contracts and evidence profiles
backend/app/retrieval     # BM25, dense baseline, RRF, planner
backend/app/evidence      # Deterministic gate (proof control)
backend/app/generation    # Composer and claim assembly
backend/app/api           # FastAPI endpoints and OpenAPI schema
frontend/src              # React UI + evidence viewer
docs/architecture         # Code-linked diagrams and mappings
.github/workflows         # CI and container build
```

See [docs/architecture/README.md](docs/architecture/README.md) for diagrams and contract-to-code mappings.
See [docs/OPERATIONS.md](docs/OPERATIONS.md) for the complete offline-ingestion, Gemini,
Docker and deployment runbook.

## Quickstart

Prereqs: Python 3.12+, Node.js 22+

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows PowerShell
python -m pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

Start services (two terminals):

```bash
make dev-api
make dev-front
```

Frontend: http://localhost:5173 — API docs: http://localhost:8000/docs

## Usage

- API endpoints: [backend/app/api/routes.py](backend/app/api/routes.py)
- Frontend: [frontend/src](frontend/src)
- Eval harness: [backend/app/evals/run_evals.py](backend/app/evals/run_evals.py)

## Demonstrated case: public QRT 2025

The primary demonstration uses Groupe Foyer's official 2025 public QRT. Three reviewed
cells from table `S.23.01.22` form the evidence contract:

- `R0660/C0010`: eligible own funds covering the total group SCR;
- `R0680/C0010`: total group SCR;
- `R0690/C0010`: coverage ratio.

The PDF was inspected with PyMuPDF and pdfplumber offline. The deployed corpus contains
only the reviewed facts, page/table/cell locators, source URL and document fingerprint;
this is a targeted extraction path, not a claim of generic automated PDF ingestion.

## Controls & Tests

Common targets:

```bash
make lint
make validate-corpus
make test
make eval
make build-front
```

The evaluation suite includes intentionally non-answerable queries and measures mapping accuracy, gating correctness, citation precision, and false-completeness. See [docs/EVALUATION.md](docs/EVALUATION.md).

## Deployment (Render)

1. Push to GitHub
2. Create a Blueprint from `render.yaml` on Render
3. Render builds the frontend in the first Docker stage and exposes FastAPI
4. Health check: `/api/health`

Note: Render free tier may sleep; persistent storage is not guaranteed. Bake durable documents into images for production.

## Limitations

- Local dense baseline is a deterministic semantic hashing fallback and may be replaced by hosted or open-weight models
- Entity and period are enforced when supplied as structured query constraints; the UI sends
  them only for a single-document scope, where they are unambiguous
- Corpus intentionally small; for >50k chunks use Qdrant/pgvector/FAISS
- No user accounts, ingestion workers, or production orchestration in the MVP
- Complex PDF table extraction is an offline ingestion pipeline (`backend/ingestion/README.md`)

---

Would you like the same visual/emoji style applied to [docs/architecture/README.md](docs/architecture/README.md)?
