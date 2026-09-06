# Notebook laboratory: architecture, outputs and interpretation

The notebooks form one continuous evidence pipeline. Read them in numerical order: each notebook consumes or validates the artifact produced by the previous layer.

`PDF → extracted markdown/tables/images → chunks → embeddings/indexes → field queries → candidates → evidence contract → cited answer → evaluation`

For every experiment, distinguish three notions:

- **Observed output**: the tables, scores and statuses printed by the executed cell.
- **Pass criterion**: a precise invariant checked by an assertion.
- **Scope of the conclusion**: what the experiment does not prove. A perfect score on curated fixtures is not production validation.

Les notebooks forment un laboratoire de recherche reproductible. Ils ne remplacent ni les modules
applicatifs ni les tests automatisés. Aucun notebook, modèle local ou parseur lourd n'est requis
dans le conteneur Render.

| Ordre | Notebook | Question vérifiée | Critère de passage |
| --- | --- | --- | --- |
| 00 | `00_environment_and_setup.ipynb` | L'environnement et le kernel sont-ils corrects ? | Python 3.12+, imports et corpus valides |
| 01 | `01_corpus_and_provenance_audit.ipynb` | Les documents et les faits sont-ils traçables ? | Provenance, versions, entités et dates présentes |
| 02 | `02_pdf_and_table_extraction.ipynb` | Les PDF et tableaux sont-ils correctement récupérés ? | Texte/tableaux contrôlés, cellules localisables |
| 03 | `03_models_and_embeddings.ipynb` | Quels modèles sont réellement disponibles ? | Baseline locale active ; modèles optionnels chargés sans fuite de secret |
| 04 | `04_retrieval_and_rrf_diagnostics.ipynb` | Les bons extraits apparaissent-ils par champ ? | Rangs lexical/dense visibles et rappel mesurable |
| 05 | `05_evidence_gate_and_grounding.ipynb` | Le code détecte-t-il manque et conflit ? | COMPLETE, NOT_FOUND et CONFLICT démontrés |
| 06 | `06_end_to_end_evaluation.ipynb` | Le système complet reste-t-il fidèle ? | Zéro fausse complétude sur le jeu initial |
| 07 | `07_offline_ingestion_pipeline.ipynb` | Les artefacts de déploiement sont-ils reproductibles ? | QRT réel, cache complet et cellules critiques validées |
| 08 | `08_chunk_size_and_retrieval_limits.ipynb` | How does chunk size affect retrieval? | Full BM25, Gemini cosine and RRF rankings for 900/1800/3000/4800-character variants |
| 09 | `09_runtime_orchestration_and_reference_loops.ipynb` | Does the runtime use trained vectors, bounded recovery and reference following? | Provider, k-history, stop reason and resolved/unresolved targets visible |
| 10 | `10_complete_acceptance_matrix.ipynb` | Are all recruiter-facing orchestration promises demonstrably covered? | Eleven end-to-end, integration and controlled branch checks pass with their evidence level displayed |
| 11 | `11_hierarchical_and_contextual_chunking.ipynb` | Do parent/child routing or Gemini chunk context improve retrieval? | Same corpus, queries, Gemini embeddings and explicit rank/recall/cost comparison |

## Installation Windows / PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,notebooks,ingestion,online-models]"
python -m ipykernel install --prefix .venv --name prudential-evidence-lab --display-name "Prudential Evidence Lab (.venv)"
Copy-Item .env.example .env
jupyter lab
```

Si PowerShell refuse l'activation, autoriser la session courante uniquement :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Installation macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,notebooks,ingestion,online-models]"
python -m ipykernel install --prefix .venv --name prudential-evidence-lab --display-name "Prudential Evidence Lab (.venv)"
cp .env.example .env
jupyter lab
```

## Ajouter les briques au moment où elles deviennent nécessaires

```bash
python -m pip install -e ".[ingestion]"
python -m pip install -e ".[local-models]"
python -m pip install -e ".[online-models]"
```

- Placer les PDF publics dans `data/raw/`. Ce dossier est ignoré par Git.
- Placer les poids locaux dans `models/`. Ce dossier est ignoré par Git.
- Renseigner uniquement les variables nécessaires dans `.env` et ne jamais committer ce fichier.
- Les appels online sont désactivés par défaut dans les notebooks.
- Pour un vrai modèle local, configurer `LOCAL_EMBEDDING_MODEL_PATH` vers un dossier de poids
  déjà téléchargé. Les notebooks utilisent `local_files_only=True`.
- Camelot peut demander des dépendances système selon le type de tableau et la plateforme.
- Docling est installé dans l'environnement de laboratoire local, mais reste absent du runtime
  Docker : l'application déployée consomme uniquement les artefacts préparés.

Le notebook 07 lit le cache par défaut. Pour relancer volontairement Docling, définir
`RUN_PDF_INGESTION=1`. Pour déclencher aussi les descriptions Gemini, définir
`RUN_VISUAL_ENRICHMENT=1` et renseigner la clé dans `.env`.

## Commit recommandé

Conserver les expérimentations dans un commit identifiable, sans poids ni secrets :

```bash
git add notebooks backend/tools/validate_notebooks.py backend/tests/test_notebooks.py
git add pyproject.toml .gitignore .env.example data/raw/.gitkeep data/processed/.gitkeep models/.gitkeep
git commit -m "test(notebooks): add progressive RAG experimentation and evaluation lab"
```

La modification du workflow GitHub Actions peut être conservée dans le commit CI/CD séparé.

## Validation sans serveur Jupyter

Dans un environnement qui interdit les sockets ou le démarrage d'un kernel :

```bash
python backend/tools/validate_notebooks.py --execute
```

This executes all cells without saving their outputs. To refresh and persist every output for reviewer reading:

```bash
python backend/tools/validate_notebooks.py --save-outputs
```

## How to interpret the twelve notebooks

| Notebook | Input | Main procedure | Output to inspect | What a pass really means |
| --- | --- | --- | --- | --- |
| 00 | Python environment and `.env` presence | Version/import/configuration checks | Environment report | The selected kernel can run the laboratory; no model quality is tested |
| 01 | Runtime corpus and source inventory | Provenance/entity/period/type audit | One row per document and chunk counts | Sources are traceable and synthetic data is labeled |
| 02 | Cached real PDFs | Docling/PyMuPDF text, table and page inspection | Extracted tables with page/row/column metadata | Target QRT content is reconstructable; it is not a universal PDF benchmark |
| 03 | Short diagnostic texts and provider configuration | Hashing, optional local model, Ollama connectivity, optional Gemini calls | Dimensions, cosine examples, provider flags | Providers are honestly identified; retrieval quality remains untested |
| 04 | One business question and the Groupe Foyer QRT | Profile mapping, field reformulation, BM25 + Gemini + RRF | Every query, excerpt, source score/rank, recall@k and full chunk corpus | Required evidence reaches the candidate set; the gate must still validate it |
| 05 | Complete, missing and conflicting candidate fixtures | Deterministic evidence contract | COMPLETE/PARTIAL/NOT_FOUND/CONFLICT and source checks | False completeness is prevented for tested conditions |
| 06 | Eleven positive and negative golden cases | Full engine, latency loop and FastAPI contract | Per-case statuses, aggregate metrics, p50/p95 and HTTP response | Demo acceptance passes; sample size and in-process latency limit generalization |
| 07 | Cached extraction artifacts | Offline assembly, visual/table enrichment and promotion checks | Artifact counts and validation failures | Deployment can read reviewed artifacts without parsing PDFs online |
| 08 | The same PDF chunked at 900/1800/3000/4800 characters | Retrieval comparison across chunk sizes | Full rankings and field recall by size | Chunk size is an empirical trade-off; embedding dimension alone cannot choose it |
| 09 | Real QRT runtime requests plus controlled reference chunks | Bounded top-k recovery, contract stop and explicit reference following | Strategy, provider, k-history, stop reason and reference traces | Runtime orchestration is observable; reference resolution remains explicit and same-document only |
| 10 | Real QRT requests plus minimal controlled rare-branch fixtures | Requirement-to-test acceptance matrix | Eleven checks with evidence level, observed value and pass state | The scoped demo promises are executable; controlled fixtures are not claims about public-source events |
| 11 | 87 reviewed Groupe Foyer QRT chunks and six bilingual retrieval cases | Flat, structural-context, Gemini-context and parent/child comparison | Per-query ranks, Recall@k, MRR, candidate count and cached latency | Hierarchical routing is promising on one QRT; contextual enrichment is not yet justified as a default |

The stored reference run currently shows 11/11 expected end-to-end outcomes, citation precision 1.0, required-field recall 1.0 and false-completeness rate 0.0. These results are coherent for the curated demo. The most important limitation is coverage: more documents, paraphrases, OCR failures, conflicting periods and adversarial questions are required before claiming robustness at scale.
