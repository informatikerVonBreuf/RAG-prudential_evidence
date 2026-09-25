# Insurance experiments — isolated corpus, dossiers and scale

Run these notebooks in order. Saved outputs are included. English is used for source
fixtures and experiment explanations; public PDFs retain their original language.

| Notebook | What is actually tested | What is not established |
| --- | --- | --- |
| 01_public_corpus_and_dossiers | Seven public file fingerprints; six synthetic PDF dossiers; invoice table extraction; five failure types | Real policy applicability, general document understanding or coverage |
| 02_large_portfolio_sql | 10,000 and 100,000 JSONL rows; strict transactional import; integer monetary totals; mandatory scope | XLSX parsing, LLM-to-SQL, retrieval accuracy or concurrent production load |
| 03_visual_evidence_triage | Nine visually inspected IPID crops; icon exclusion; meaningful synthetic diagram; optional Gemini experiment | Automatic semantic image classification or model accuracy without running and reviewing the optional call |
| 04_excel_roundtrip_and_scale | Actual 10,000/100,000-row XLSX files; exact all-row comparison; scoped SQL sums; policy and six dossier links; negative cases | General Excel layouts, formula calculation, live UI upload or production load |

## Deliberate separation

```text
notebooks/00..12*.ipynb                  historical prudential experiments (unchanged)
notebooks/13..16*.ipynb                  first insurance experiments (preserved)
notebooks/insurance/                    this new sequence
data/raw/                              historical input locations (preserved)
data/processed/insurance/               first insurance extraction caches (preserved)
data/insurance_v2/
  public/pdf/                          verified Foyer, LALUX and AXA reference PDFs
  public/inventory.json                acquisition status and fingerprints
  synthetic/portfolios/claims_10000/    JSONL, claims.xlsx, fingerprints and SQL benchmarks
  synthetic/portfolios/claims_100000/   larger JSONL/XLSX portfolio and benchmarks
  synthetic/dossiers/D001..D006/        policy, declaration, invoice and inspection fixtures
```

Public documents are *not* automatically attached as applicable case contracts. The six
new dossiers are generated using explicitly synthetic terms. Their claim/policy references
link to the portfolio. A generic inspection diagram exercises visual extraction; it is
not proof of a particular claim's declared peril or a real photograph.

Old files are not deleted, moved or re-indexed. Public PDFs and generated data are ignored
by Git; generators, test expectations, catalogues and notebook outputs are versionable.
The PDF copies require no customer data. Do not assume public availability grants a right
to redistribute whole insurer documents in a public repository.

## Reproduce from the repository root (PowerShell)

Use the existing `.venv`; activate it or keep the explicit executable path:

```powershell
.venv/Scripts/python.exe -m ingestion.insurance_workspace --download
.venv/Scripts/python.exe -m ingestion.insurance_scale --rows 10000 100000
.venv/Scripts/python.exe -m ingestion.insurance_dossiers
.venv/Scripts/python.exe -m ingestion.insurance_excel --rows 10000 100000
.venv/Scripts/python.exe -m pytest
```

Select this environment's Jupyter kernel. The notebooks locate the repository root even
when launched from their nested folder. None of the default cells loads an API key or calls
a model. The optional visual cell requires an explicit RUN_INSURANCE_VISUAL_EXPERIMENT=1.
It makes one Gemini call each time it executes and does not promote its output.

## Excel datasets and tested contract

The user approved reusing openpyxl, already pinned in `.[format-experiments]`, as the
spreadsheet-tool fallback. Two real workbooks now contain five sheets: Readme, Claims,
Policies, DossierLinks and DataDictionary. These are source datasets with **no formulas**;
computed financial results belong to the SQL benchmark, not hardcoded spreadsheet outputs.
Dates are typed Excel dates; monetary amounts are integer EUR cents. Tables have filters,
frozen headers and field definitions. Synthetic distributions are not actuarial estimates.

Export is write-only, import is read-only. Every imported claim is compared with its JSONL
source, then scoped counts and sums are reconciled with external generator expectations.
Policy references, tenants and dates are checked. Six dossier locators are checked against
SQL rows and artifact fingerprints. Physical worksheet row numbers are retained in SQL.
Do not vectorize cells to calculate a portfolio total: use all validated rows in scope.

The importer rejects source formulas/errors, missing cells, duplicate claims, invalid
dates, mixed currencies, wrong policy/tenant links, unexpected headers, macro/external-link
containers and oversized inputs. A failure yields no usable database; no rows are silently
dropped. Formula evaluation, arbitrary layouts, hidden-sheet semantics and quarantine/review
workflows are not implemented. This offline adapter is not a sandbox for hostile uploads.

Supported experiment bounds: 100,000 claims, 50 MiB compressed / 256 MiB expanded XLSX.
SQLite still uses memory for data and indexes; this is not constant-memory end to end.
Notebook 04 defaults to both sizes; CI uses `INSURANCE_EXCEL_ROWS=10000` to stay lightweight.
Its saved local outputs include the actual larger experiment. Timings are machine-specific.

Native Excel visual verification was attempted via read-only, macros-disabled automation,
but Excel could not open the workbook through COM in this environment. Data/structure tests
pass; no claim is made that the native Excel rendering was visually validated here.

## Production boundary

The new corpus and SQL tools are offline experiments, not yet connected to the deployed
UI. No new upload type, authentication, durable case database, automatic coverage decision
or enterprise authorization is claimed. SQLite's mandatory scope argument is a test
control; a production tenant must come from verified identity, not user-supplied text.
