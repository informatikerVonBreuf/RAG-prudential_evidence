# Pipeline d’ingestion hors ligne

L’application déployée ne parse aucun PDF. L’ingestion est exécutée sur le poste de
développement et produit des artefacts revus, versionnés puis compilés dans le corpus
léger du runtime.

```text
source publique → profil documentaire → extraction structurée
→ pages, tableaux, figures et provenance → chunks contextualisés
→ index pré-calculés → revue → compilation du corpus runtime
```

## Extracteurs

- Docling est le moteur principal prévu pour la hiérarchie, les tableaux, les figures et
  les pages. `docling_converter.py` configure des pipelines distincts selon le profil.
- Docling 2.121 est l'extracteur structurel réellement exécuté sur le QRT public 2025.
- PyMuPDF fournit les coordonnées de pages, vérifie les trois cellules critiques et
  constitue le fallback explicite si Docling échoue.
- Gemini est optionnel pour les descriptions visuelles et les embeddings. Aucun appel
  n’est effectué sans clé et modèle configurés.

Le pipeline QRT validé extrait `R0660`, `R0680` et `R0690` dans
`S.23.01.22/C0010`. Ce chemin ciblé n’est pas une ingestion universelle de PDF.

## Artefacts

Chaque document obtient un dossier dans `data/processed/<document_id>/` :

```text
manifest.json         pages.jsonl          sections.json
tables.jsonl          facts.jsonl          figures.jsonl
chunks.jsonl          references.json      page_images/
document.md           docling.md            docling.json
indexes/embedding_manifest.json            indexes/embeddings.json
```

`docling.json` est le cache structurel avec provenance. `document.md` en est la vue
lisible destinée à la revue. Les chunks textuels sont produits par le
`HierarchicalChunker` de Docling à partir du même modèle documentaire ; le fallback
PyMuPDF n'est utilisé que si cette conversion échoue.

`data/raw` et `data/processed` restent ignorés par Git, sauf leurs `.gitkeep`. Seuls les
artefacts revus nécessaires au runtime sont promus dans `backend/app/data`.

## Commandes

```powershell
python -m pip install -e ".[dev,notebooks,ingestion,online-models]"
pel-ingest data/raw/foyer-groupe-qrt-public-2025.pdf `
  --document-id foyer_group_qrt_2025 `
  --title "QRT public 2025 - Groupe Foyer" `
  --entity "Groupe Foyer" --period 2025 `
  --source-url "https://www.foyer.lu/fr/mydoc/WebSites-Documentsgroupe-376"
pel-build-corpus `
  --processed data/processed/foyer_group_qrt_2025 `
  --output backend/app/data/corpus.generated.json
```

Comparer le corpus généré au corpus actif avant promotion. Ne jamais remplacer
automatiquement un artefact revu.
