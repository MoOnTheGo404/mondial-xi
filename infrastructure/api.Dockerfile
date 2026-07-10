# Mondial XI — API image (FastAPI + trained model artifacts).
# Build context = repository root:
#   docker build -f infrastructure/api.Dockerfile -t mondial-xi-api .
# The processed data and model artifacts are built INTO the image from the
# CC0 sources during the build, so a fresh git clone (no committed binaries)
# deploys self-contained.
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy KICKOFF_REPO_ROOT=/app \
    PYTHONUNBUFFERED=1

# --- dependency layer (cached across code changes) ---
COPY pyproject.toml uv.lock ./
COPY ml/pyproject.toml ml/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN mkdir -p ml/kickoff_ml apps/api/kickoff_api \
    && touch ml/kickoff_ml/__init__.py apps/api/kickoff_api/__init__.py \
    && uv sync --all-packages --frozen --no-dev

# --- application code + committed inputs ---
COPY ml ml
COPY apps/api apps/api
COPY scripts scripts
COPY data/manifests data/manifests
COPY data/tournaments data/tournaments
# Wikidata career stats (CC0) committed so deploys match local exactly.
COPY data/raw/wikidata_players.json data/raw/wikidata_players.json
RUN uv sync --all-packages --frozen --no-dev

# --- build processed data + trained artifacts at image-build time ---
# (downloads the CC0 dataset, validates, builds parquet, trains & evaluates
#  models, writes the serving bundle and the aging calibration)
RUN uv run python -m kickoff_ml.ingestion.download \
 && uv run python -m kickoff_ml.ingestion.wikipedia \
 && uv run python -m kickoff_ml.ingestion.build \
 && uv run python -m kickoff_ml.models.players \
 && uv run python -m kickoff_ml.evaluation.run \
 && uv run python scripts/calibrate_aging.py

EXPOSE 8000
# Render (and most PaaS) inject $PORT; default to 8000 locally.
CMD ["sh", "-c", "uv run --no-sync uvicorn kickoff_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
