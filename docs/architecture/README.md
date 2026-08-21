# **Architecture (Code-Linked)**

![Architecture](https://img.shields.io/badge/ARCHITECTURE-diagrams-blue?style=flat-square)

The diagrams in this folder are views of the code (not separate pipeline diagrams).
Each diagram maps a logical block to its implementation file and runtime contract.

---

## Mapping: Block → Implementation → Contract

| Block | Implementation | Contract |
| --- | --- | --- |
| Business UI | `frontend/src/App.tsx` | `QuestionRequest`, `AnswerPayload` |
| API | `backend/app/api/routes.py` | OpenAPI / Pydantic schemas |
| Intent Mapping | `backend/app/domain/profiles.py` | `EvidenceProfile` |
| Batch Planner | `backend/app/retrieval/planner.py` | `SearchQuery[]` |
| Hybrid Retrieval | `backend/app/retrieval/hybrid.py` | `Candidate[]`, `ScoreTrace` |
| Evidence Gate | `backend/app/evidence/gate.py` | `GateResult` |
| Composition / Composer | `backend/app/generation/composer.py` | `Claim[]` |
| Transparency / Viewer | `frontend/src/App.tsx` | `EvidenceView`, `SourceLocator` |

## Diagrams

- `flux_technique.png` — execution flow and component interactions
- `interface_cible.png` — target user interface and evidence presentation
- `architecture_cible.png` — ingestion vs execution separation
- `decision_modeles.png` — model decision boundaries (online vs local)

## Guidelines

- Any change to a block MUST update its contract, tests, and associated diagram.
- Keep diagrams in sync with code; prefer code-linked diagrams over speculative designs.

---

Would you like me to embed the images directly or add small preview thumbnails? If yes, I can add inline previews for each PNG.

