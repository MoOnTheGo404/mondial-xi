# Kickoff Atlas — one Makefile to run everything.
# Requires: uv (https://astral.sh/uv), pnpm, Node 20+. `make bootstrap` checks these.

SHELL := /bin/bash
export PATH := $(HOME)/.local/bin:$(PATH)

.PHONY: bootstrap data data-status train evaluate dev api web test test-e2e \
        lint typecheck build check screenshots clean snapshots

bootstrap: ## install Python + JS dependencies
	@command -v uv >/dev/null || { echo "uv missing — install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	@command -v pnpm >/dev/null || { echo "pnpm missing — install: npm i -g pnpm"; exit 1; }
	uv sync --all-packages
	pnpm install

data: ## download (CC0) + validate + build processed datasets + player registry
	uv run python -m kickoff_ml.ingestion.download
	uv run python -m kickoff_ml.ingestion.build
	uv run python -m kickoff_ml.models.players
	uv run python scripts/make_test_fixtures.py

data-enrich: ## optional: career caps/goals from Wikidata (CC0, ~4 min, throttled)
	uv run python -m kickoff_ml.ingestion.wikidata_players
	uv run python -m kickoff_ml.models.players

data-status: ## show dataset provenance + quality report
	@cat data/manifests/results.json | python3 -m json.tool | head -30
	@echo "---"
	@cat data/manifests/data_quality.json | python3 -m json.tool

train: evaluate ## alias — training and evaluation are one chronological pipeline

evaluate: ## tune Elo, fit candidates, chronological evaluation, write artifacts
	uv run python -m kickoff_ml.evaluation.run

snapshots: ## snapshot upcoming fixtures + score completed ones (also runs at API startup)
	uv run python scripts/run_snapshots.py

api: ## run FastAPI on :8000
	uv run uvicorn kickoff_api.main:app --port 8000 --reload

web: ## run Next.js on :3000
	pnpm --filter @kickoff/web dev

dev: ## run API + web together
	@trap 'kill 0' EXIT; \
	uv run uvicorn kickoff_api.main:app --port 8000 & \
	pnpm --filter @kickoff/web dev & \
	wait

test: ## Python unit+integration tests, then JS unit tests
	uv run pytest tests/unit tests/integration -q
	pnpm --filter @kickoff/web test

test-e2e: ## Playwright end-to-end tests (starts its own servers)
	pnpm --filter @kickoff/web exec playwright test

lint:
	uv run ruff check ml apps/api scripts tests
	pnpm --filter @kickoff/web lint

typecheck:
	uv run mypy ml/kickoff_ml apps/api/kickoff_api
	pnpm -r typecheck

build: ## production frontend build
	pnpm --filter @kickoff/web build

check: lint typecheck test ## full local gate

screenshots: ## regenerate docs/screenshots from the running app
	pnpm --filter @kickoff/web exec playwright test e2e/screenshots.spec.ts

clean:
	rm -rf data/processed data/cache .pytest_cache .ruff_cache
	rm -rf apps/web/.next

help: ## list targets
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
