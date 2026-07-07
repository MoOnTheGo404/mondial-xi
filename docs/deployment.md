# Deployment

## Status (honest)

Not deployed to a public host. Docker images are authored and CI builds +
smoke-tests them (`.github/workflows/ci.yml`, `docker` job); the development
machine has no Docker, so container startup was **not** verified locally.
Everything below is the designed path.

## Containers

```bash
make data && make train          # artifacts are baked into the API image
docker compose up --build        # api :8000, web :3000
```

- API image: uv-based, copies processed parquet + artifacts, healthcheck on
  `/api/v1/health`, **never trains at startup**.
- Web image: pnpm build → `next start`, healthcheck on `/`.
- Snapshot DB on a named volume (`sqlite:////app/data/kickoff.db`).

## Low-cost production architecture

- **Fly.io / Railway / Render**: one small VM each for api + web
  (512 MB–1 GB is ample; artifact bundle ~1 MB, dataset parquet ~4 MB).
- **Database**: keep SQLite on a volume at this scale, or set
  `KICKOFF_DATABASE_URL=postgresql+psycopg://…` (SQLAlchemy handles both;
  managed Postgres ≈ $5/mo when multi-instance).
- **Frontend alternative**: Vercel for `apps/web` with `API_INTERNAL_URL`
  pointed at the API host.

## Scheduled jobs (design)

Daily (e.g. 06:00 UTC) via host cron / GitHub Actions schedule / Fly machines:

```bash
uv run python -m kickoff_ml.ingestion.download --force
uv run python -m kickoff_ml.ingestion.build
uv run python -m kickoff_ml.models.players
uv run python -m kickoff_ml.evaluation.run      # weekly is enough
uv run python scripts/run_snapshots.py           # snapshot new fixtures, score finished
```

Then redeploy/restart the API (artifacts are immutable inputs). Snapshots of
fixtures whose forecasts changed insert new immutable versions automatically.

## Environment & secrets

`.env.example` documents every variable; none are required. The only secret
is the optional `FOOTBALL_DATA_API_KEY` — set via the platform's secret
store, never committed (gitignore blocks `.env*`).

## Migrations

Schema is created via SQLAlchemy metadata on startup (single table). For
schema evolution in production: `alembic init` against `kickoff_api.db.Base`
— the store was designed append-only precisely so migrations stay trivial;
adding forecast-version columns is additive.

## Rollback

- Images are immutable: redeploy the previous tag.
- Artifacts are reproducible from any git commit: `git checkout <tag> &&
  make data && make train` rebuilds byte-equivalent evaluation outputs
  (deterministic seeds; dataset pinned by manifest SHA-256 if archived).
- Snapshot DB is append-only; no destructive migrations exist.

## Rate limiting (recommended)

Put the API behind a reverse proxy (Caddy/nginx/platform) with ~60 req/min/IP
and stricter (10/min) on `POST /api/v1/simulations/*`; the app also enforces
`KICKOFF_MAX_SIMULATIONS` server-side.
