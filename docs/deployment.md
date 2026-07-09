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

## Daily auto-update

The open dataset (martj42/international_results) is refreshed daily as matches
finish, so the platform can stay current with a scheduled job. One command
does the whole cycle:

```bash
make refresh   # re-download → rebuild → retrain → re-evaluate → re-snapshot
```

**Shipped automation:** `.github/workflows/daily-refresh.yml` runs this at
07:00 UTC daily (and on manual dispatch): it refreshes the data, retrains,
re-runs the leakage/metrics tests as a sanity check, and commits the changed
JSON artifacts + README metrics back to the repo (`[skip ci]`). If the
upstream dataset is unchanged, it no-ops.

**For a deployment:**
- If the platform redeploys on push (Vercel/Railway/Render), the daily commit
  triggers a rebuild that runs `make data && make train`, regenerating the
  parquet + `prediction_bundle.joblib` from the fresh data — no artifacts need
  to travel through git.
- Or run `make refresh` on the host via cron and restart the API (it loads
  artifacts read-only at startup and re-runs snapshot scoring in the
  lifespan hook). Keep the snapshot SQLite DB on a persistent volume so the
  track record accumulates.

**Snapshot scoring:** `scripts/run_snapshots.py` (part of `make refresh`)
records immutable forecasts for genuinely-upcoming fixtures and attaches
results/scores to snapshots whose matches have now finished — the track
record updates itself every day without overwriting past forecasts.

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
