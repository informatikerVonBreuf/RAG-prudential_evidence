.PHONY: install install-front dev-api dev-front test eval lint build-front validate-corpus docker

install:
	python -m pip install -e ".[dev]"

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

docker:
	docker build -t prudential-evidence-lab .
