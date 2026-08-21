# Architecture reliée au code

Les schémas de ce dossier sont des vues du code, pas des pipelines indépendants.

| Bloc du schéma | Implémentation | Contrat |
| --- | --- | --- |
| Interface métier | `frontend/src/App.tsx` | `QuestionRequest`, `AnswerPayload` |
| API | `backend/app/api/routes.py` | OpenAPI / Pydantic |
| Mapping | `backend/app/domain/profiles.py` | `EvidenceProfile` |
| Planification batch | `backend/app/retrieval/planner.py` | `SearchQuery[]` |
| Recherche hybride | `backend/app/retrieval/hybrid.py` | `Candidate[]`, `ScoreTrace` |
| Contrôle de preuves | `backend/app/evidence/gate.py` | `GateResult` |
| Composition | `backend/app/generation/composer.py` | `Claim[]` |
| Transparence | `frontend/src/App.tsx` | `EvidenceView`, `SourceLocator` |

`flux_technique.png` décrit le chemin d’exécution. `interface_cible.png` décrit ce que voit
l’utilisateur. `architecture_cible.png` présente la séparation ingestion/exécution et
`decision_modeles.png` garde la décision online/local explicite.

Toute évolution d’un bloc doit modifier son contrat, ses tests et le schéma associé.

