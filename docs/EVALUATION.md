# Évaluation du chemin de preuve

Le jeu d’or initial contient six questions stratifiées : trois répondables, une dont le périmètre
est volontairement incorrect et deux non répondables. Il vérifie autant l’abstention que la
capacité à retrouver un fait.

| Mesure | Résultat actuel | Lecture |
| --- | ---: | --- |
| Exactitude du mapping | 1,00 | Profil attendu sélectionné sur 6/6 questions |
| Exactitude du statut | 1,00 | `COMPLETE` / `NOT_FOUND` correct sur 6/6 |
| Rappel des champs obligatoires | 1,00 | 9/9 champs attendus couverts |
| Précision des citations | 1,00 | Chaque assertion cite une preuve acceptée |
| Taux de fausse complétude | 0,00 | 0/3 questions non complètes déclarées complètes |

Ces résultats valident le câblage du MVP, pas sa généralisation. Six questions et un corpus réduit
ne suffisent pas à conclure sur une qualité de production. L’étape suivante consiste à augmenter le
jeu d’or par type de document, type de tableau, entité, période et difficulté, avec une revue humaine
indépendante.

Le rapport reproductible est obtenu avec :

```bash
python backend/evals/run_evals.py
```

