# Guide opérateur — laboratoire, modèles et déploiement

## 1. Préparer l’environnement

Utiliser Python 3.12 et Node.js 22. Sous PowerShell :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,notebooks,ingestion,online-models]"
Set-Location frontend
npm ci
Set-Location ..
Copy-Item .env.example .env
```

Si l’entreprise intercepte TLS, installer son autorité de certification dans Python,
npm et Docker. Ne pas utiliser `strict-ssl=false` ou `--trusted-host` comme solution
permanente.

## 2. Télécharger et vérifier le QRT

Télécharger le QRT public Groupe Foyer 2025 depuis la page financière officielle et le
placer sous `data/raw/foyer-groupe-qrt-public-2025.pdf`.

```powershell
Get-FileHash data/raw/foyer-groupe-qrt-public-2025.pdf -Algorithm SHA256
```

Empreinte observée le 21 août 2026 :
`4AC00A5AEC153C6401F8FF7F9588576916693256CA13BC73083EB5DE2626541A`.

## 3. Exécuter le laboratoire

```powershell
jupyter lab
```

Exécuter les notebooks dans l’ordre `00` à `07`. Le notebook `07` génère le cache dans
`data/processed`. Les appels online du notebook `03` restent désactivés par défaut.

Alternative CLI :

```powershell
make ingest-qrt
make build-corpus
```

Vérifier manuellement `R0660`, `R0680` et `R0690`, leur unité, page et coordonnées avant
de promouvoir le corpus généré.

## 4. Configurer Gemini — optionnel

Dans `.env` uniquement :

```dotenv
GEMINI_API_KEY=votre_cle
GEMINI_GENERATION_MODEL=gemini-2.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
RUN_ONLINE_EXPERIMENT=0
RUN_VISUAL_ENRICHMENT=0
ENABLE_HYBRID_MAPPING=0
```

`ENABLE_HYBRID_MAPPING=1` enables Gemini only for questions whose deterministic
profile score has no clear winner. Clear rules remain at zero calls; ambiguous questions
use one embedding call, then at most one structured judge call. Identical decisions are
cached in memory. Provider failure always falls back to `open_question` rather than guessing.

Sans clé, la composition déterministe et la baseline hashing restent actives. Avec une
clé, Gemini peut reformuler uniquement les preuves acceptées. Il ne décide jamais du
statut `COMPLETE`. Les descriptions d’images sont des interprétations dérivées et non
des preuves primaires.

Pour exécuter volontairement les deux appels de contrôle du notebook `03` (embeddings
et génération), passer temporairement `RUN_ONLINE_EXPERIMENT=1`, exécuter la cellule,
puis remettre la valeur à `0`. Le runtime effectue son appel de synthèse Gemini pour
chaque réponse couverte lorsque la clé et le modèle sont configurés. Le panneau
« Appels modèles » affiche modèle, statut, tentatives et latence.

Pour enrichir volontairement les figures durant l'ingestion hors ligne, passer
`RUN_VISUAL_ENRICHMENT=1`. Chaque visuel retenu est envoyé avec sa légende et son
contexte, puis la réponse structurée est conservée dans `figures.jsonl` et
`document.md`. La valeur `0` garantit qu'aucun appel visuel n'est effectué.

Si Docling a déjà produit le cache, ne pas relancer l'ingestion. Utiliser :

```powershell
pel-enrich-visuals data/processed/foyer_group_qrt_2025
```

Cette commande relit les images existantes, effectue uniquement les appels Gemini,
puis régénère `figures.jsonl`, les chunks visuels, `document.md` et l'index.

## 5. Contrôler la V1

```powershell
ruff check backend notebooks/helpers.py
python backend/tools/validate_corpus.py
python backend/tools/validate_notebooks.py
pytest
python backend/evals/run_evals.py
Set-Location frontend
npm run typecheck
npm run build
Set-Location ..
docker build -t prudential-evidence-lab:local .
```

## 6. Lancer localement

Mode développement, deux terminaux :

```powershell
uvicorn app.main:app --app-dir backend --reload --env-file .env
```

```powershell
Set-Location frontend
npm run dev
```

Mode conteneur :

```powershell
docker run --rm -p 8000:8000 --env-file .env prudential-evidence-lab:local
```

Ouvrir `http://localhost:8000` et vérifier `/api/health`.

## 7. Scénarios de démonstration

1. Sélectionner uniquement le QRT Groupe Foyer 2025.
2. Demander : « Quels éléments publics caractérisent la couverture prudentielle du
   Groupe Foyer en 2025 ? »
3. Montrer les trois requêtes, le statut `COMPLETE` et les cellules QRT.
4. Poser la même question pour 2024 : résultat attendu `NOT_FOUND` avec preuves rejetées.
5. Un identifiant documentaire inexistant doit produire HTTP 422, jamais un scope élargi.

## 8. Déploiement

Après vos propres revues : vérifier l’identité Git, committer, pousser vers votre dépôt,
créer le service depuis `render.yaml`, ajouter `GEMINI_API_KEY` aux secrets seulement si
Gemini est activé, puis vérifier le lien public et `/api/health`.

Le runtime ne doit contenir ni PDF brut, ni modèle Docling, ni poids locaux, ni notebooks.
