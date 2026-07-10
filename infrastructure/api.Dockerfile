# Mondial XI — API image (FastAPI + trained model artifacts).
# Build context = repository root:
#   docker build -f infrastructure/api.Dockerfile -t mondial-xi-api .
# The processed data and model artifacts are built INTO the image from the
# CC0 sources during the build, so a fresh git clone (no committed binaries)
# deploys self-contained.
#
# Multi-stage: the `builder` installs deps and trains the models; the `runtime`
# stage carries only the resolved virtualenv + app code + generated data and
# artifacts — no uv, no build tools, no dev dependencies.

# --- builder: deps + data + trained artifacts -------------------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy KICKOFF_REPO_ROOT=/app \
    PYTHONUNBUFFERED=1

# dependency layer (cached across code changes)
COPY pyproject.toml uv.lock ./
COPY ml/pyproject.toml ml/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN mkdir -p ml/kickoff_ml apps/api/kickoff_api \
    && touch ml/kickoff_ml/__init__.py apps/api/kickoff_api/__init__.py \
    && uv sync --all-packages --frozen --no-dev

# application code + committed inputs
COPY ml ml
COPY apps/api apps/api
COPY scripts scripts
COPY data/manifests data/manifests
COPY data/tournaments data/tournaments
# Wikidata career stats (CC0) committed so deploys match local exactly.
COPY data/raw/wikidata_players.json data/raw/wikidata_players.json
RUN uv sync --all-packages --frozen --no-dev

# build processed data + trained artifacts at image-build time. Run via the
# venv directly (not `uv run`) so no dev dependencies are pulled into the venv
# we ship — downloads the CC0 dataset + Wikipedia overlay, validates, builds
# parquet, trains & evaluates, writes the serving bundle + aging calibration.
RUN .venv/bin/python -m kickoff_ml.ingestion.download \
 && .venv/bin/python -m kickoff_ml.ingestion.wikipedia \
 && .venv/bin/python -m kickoff_ml.ingestion.build \
 && .venv/bin/python -m kickoff_ml.models.players \
 && .venv/bin/python -m kickoff_ml.evaluation.run \
 && .venv/bin/python scripts/calibrate_aging.py

# --- runtime: slim, no uv / build tools / dev deps --------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV KICKOFF_REPO_ROOT=/app PYTHONUNBUFFERED=1 PATH="/app/.venv/bin:$PATH"

# the resolved venv + editable-installed source + generated data & artifacts
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/ml /app/ml
COPY --from=builder /app/apps/api /app/apps/api
COPY --from=builder /app/scripts /app/scripts
COPY --from=builder /app/data /app/data

EXPOSE 8000
# Render (and most PaaS) inject $PORT; default to 8000 locally. uvicorn is on
# PATH from the copied venv — no uv needed at runtime.
CMD ["sh", "-c", "uvicorn kickoff_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
