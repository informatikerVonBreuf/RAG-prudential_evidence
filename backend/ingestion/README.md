# Chemin d’ingestion hors ligne

L’ingestion n’est volontairement pas exécutée dans le service Render. Elle doit produire des
artefacts revus et immuables avant déploiement.

1. Télécharger les documents publics et enregistrer URL, date, version et empreinte SHA-256.
2. Utiliser PyMuPDF pour le texte et les coordonnées de base.
3. Router les tableaux vers Camelot (`lattice`, puis `stream`) ou Docling/TableFormer selon leur
   structure. Les scans passent d’abord par OCR.
4. Normaliser chaque cellule dans un `TableFact` typé : métrique, valeur, unité, période, entité,
   page, ligne, colonne et `bbox`.
5. Produire `documents.json`, `chunks.jsonl`, `tables.jsonl`, `facts.json`, l’index lexical et les
   embeddings.
6. Exécuter une revue ciblée des tableaux critiques puis `python backend/tools/validate_corpus.py`.
7. Versionner le manifeste et redéployer.

Le fichier `backend/app/data/corpus.json` fusionne ces artefacts dans un format compact pour le
premier démonstrateur. L’annexe synthétique qu’il contient sert uniquement à tester les
localisateurs de cellules et ne décrit pas Foyer.

