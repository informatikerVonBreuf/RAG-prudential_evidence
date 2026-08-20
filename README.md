# Prudential Evidence Lab

Assistant documentaire auditable construit pour démontrer une architecture RAG sans framework
RAG. Une question est mappée vers un contrat de preuves, décomposée en requêtes par champ, traitée
par deux canaux de récupération, puis contrôlée par du code avant rédaction.

## Ce que montre le MVP

- bibliothèque documentaire publique en lecture seule ;
- trois modes : Question rapide, Analyse approfondie, Synthèse structurée ;
- profils de preuves versionnés et mapping d’intentions ;
- BM25 écrit dans le projet, baseline dense locale et fusion RRF ;
- statuts `COMPLETE`, `PARTIAL`, `NOT_FOUND` et `CONFLICT` décidés hors LLM ;
- citations au niveau de chaque assertion, avec page, section, table/cellule et scores ;
- historique éphémère ou local au navigateur ;
- API FastAPI, interface React/TypeScript et image Docker unique pour Render.

Le corpus embarqué reprend un petit nombre d’indicateurs publiés sur les pages officielles de
[Foyer](https://groupe.foyer.lu/fr/foyer/informations-financieres) et de son
[rapport annuel 2025](https://groupe.foyer.lu/fr/rapport-annuel). Il ne remplace pas les documents
officiels et ne doit pas servir à une décision financière. Un document distinctement marqué
« synthétique » permet de tester la transparence d’une cellule de tableau.

## Démarrage local

Prérequis : Python 3.12 et Node.js 22.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cd frontend && npm install && cd ..
```

Dans deux terminaux :

```bash
make dev-api
make dev-front
```

Ouvrir `http://localhost:5173`. L’API et son contrat OpenAPI sont disponibles sur
`http://localhost:8000/docs`.

## Contrôles

```bash
make lint
make validate-corpus
make test
make eval
make build-front
```

L'évaluation contient aussi des questions volontairement non répondables. Elle calcule la
précision du mapping, l'exactitude du statut, le rappel des champs obligatoires, la précision des
citations et le taux de fausse complétude. La CI échoue dès qu'une question attendue `NOT_FOUND`
est déclarée `COMPLETE`. Les résultats et leurs limites sont documentés dans
`docs/EVALUATION.md`.

## Déploiement Render

1. Pousser le dépôt sur GitHub.
2. Dans Render, créer un Blueprint à partir de `render.yaml`.
3. Render construit le front dans le premier stage Docker, installe uniquement Python dans le
   runtime, puis expose FastAPI.
4. Le health check est `/api/health`.

Le plan gratuit peut s’endormir et son disque est éphémère. L’application ne promet donc aucune
persistance serveur. Les documents durables sont ingérés hors ligne, revus, puis intégrés au
conteneur au redéploiement.

## Limites assumées

- la baseline dense locale est un hashing sémantique déterministe, remplaçable par Gemini ou un
  modèle open-weight via un adapter ; elle n’est pas présentée comme un embedding entraîné ;
- le corpus est volontairement réduit ; au-delà d’environ 50 000 chunks, l’index exact doit être
  remplacé par Qdrant, pgvector ou FAISS ANN ;
- la composition actuelle est déterministe pour que la démo fonctionne sans secret ; un LLM peut
  reformuler uniquement après validation et sous schéma ;
- pas de comptes, de base de conversations, de workers d’ingestion ni de Kubernetes dans le MVP ;
- les tableaux PDF complexes restent un pipeline d’ingestion hors ligne décrit dans
  `backend/ingestion/README.md`.

## Structure

```text
backend/app/domain        contrats Pydantic et profils
backend/app/retrieval     BM25, dense local, RRF, planificateur
backend/app/evidence      gate déterministe
backend/app/generation    composition ancrée
backend/app/api           endpoints FastAPI
frontend/src              interface métier et transparence
docs/architecture         schémas reliés aux modules
.github/workflows         qualité et build du conteneur
```
