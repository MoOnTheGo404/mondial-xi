# Kickoff Atlas API image.
# Build context = repository root:
#   docker build -f infrastructure/api.Dockerfile -t kickoff-api .
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy KICKOFF_REPO_ROOT=/app

# dependency layer
COPY pyproject.toml uv.lock ./
COPY ml/pyproject.toml ml/pyproject.toml
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN mkdir -p ml/kickoff_ml apps/api/kickoff_api \
    && touch ml/kickoff_ml/__init__.py apps/api/kickoff_api/__init__.py \
    && uv sync --all-packages --frozen --no-dev

# application code + data artifacts
COPY ml ml
COPY apps/api apps/api
COPY data/manifests data/manifests
COPY data/tournaments data/tournaments
# Processed data and trained artifacts must be built before the image:
#   make data && make train
COPY data/processed data/processed
COPY ml/artifacts ml/artifacts
RUN uv sync --all-packages --frozen --no-dev

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).status==200 else 1)"

CMD ["uv", "run", "--no-sync", "uvicorn", "kickoff_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
