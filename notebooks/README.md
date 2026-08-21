# Parcours expérimental et évaluation progressive

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

## Installation Windows / PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --user --name prudential-evidence-lab --display-name "Prudential Evidence Lab"
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
python -m pip install -e ".[dev,notebooks]"
python -m ipykernel install --user --name prudential-evidence-lab --display-name "Prudential Evidence Lab"
cp .env.example .env
jupyter lab
```

## Ajouter les briques au moment où elles deviennent nécessaires

```bash
python -m pip install -e ".[ingestion]"
python -m pip install -e ".[tables]"
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
- Docling reste volontairement hors installation par défaut : c'est une étape d'ingestion locale,
  pas une dépendance runtime du prototype.

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
python backend/tools/validate_notebooks.py --execute --in-process
```

Ce mode exécute toutes les cellules dans leur ordre, sans conserver les sorties dans les fichiers.
