# Evidence-path evaluation

The golden set contains thirteen stratified questions. It covers complete answers,
unanswerable questions, a wrong document scope, a wrong entity, a wrong period, and
deliberately ambiguous multi-entity or multi-period requests. It tests abstention as
well as the retrieval of several compatible evidence fields.

| Metric | Current result | Interpretation |
| --- | ---: | --- |
| Mapping accuracy | 1.00 | Expected profile selected for 13/13 questions |
| Status accuracy | 1.00 | Expected answer status returned for 13/13 questions |
| Required-field recall | 1.00 | Every required field in the positive cases is covered |
| Citation precision | 1.00 | Every generated claim cites accepted evidence |
| False-completeness rate | 0.00 | No non-complete case is reported as `COMPLETE` |

These results validate the MVP wiring, not production generalisation. Thirteen questions
and a small reviewed corpus are insufficient to claim production quality. Conflict and
document-reference cases are tested separately with controlled fixtures; they are not
presented as anomalies observed in Foyer's public sources. Production validation would
require a larger adversarial golden set reviewed independently across document types,
table structures, entities, periods and extraction failures.

Reproduce the report with:

```bash
python backend/evals/run_evals.py
```
