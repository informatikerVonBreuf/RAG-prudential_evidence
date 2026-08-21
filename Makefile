.PHONY: install install-lab install-front dev-api dev-front test eval lint build-front validate-corpus validate-notebooks ingest-qrt docker

install:
	python -m pip install -e ".[dev]"

install-lab:
	python -m pip install -e ".[dev,notebooks,ingestion,online-models]"

install-front:
	cd frontend && npm install

dev-api:
	uvicorn app.main:app --app-dir backend --reload

dev-front:
	cd frontend && npm run dev

test:
	pytest

eval:
	python backend/evals/run_evals.py

lint:
	ruff check backend

build-front:
	cd frontend && npm run build

validate-corpus:
	python backend/tools/validate_corpus.py

validate-notebooks:
	python backend/tools/validate_notebooks.py

ingest-qrt:
	pel-ingest data/raw/foyer-groupe-qrt-public-2025.pdf --document-id foyer_group_qrt_2025 --title "QRT public 2025 - Groupe Foyer" --entity "Groupe Foyer" --period 2025 --source-url "https://www.foyer.lu/fr/mydoc/WebSites-Documentsgroupe-376"

build-corpus:
	pel-build-corpus --processed data/processed/foyer_group_qrt_2025 --output backend/app/data/corpus.generated.json

docker:
	docker build -t prudential-evidence-lab .
