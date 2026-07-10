# Deployment

## Deploy to Render (recommended — full app, free)

The whole app (Next.js frontend + FastAPI backend + trained models) runs as
two Docker services. The API image **builds the CC0 data and trains the
models during its Docker build**, so a fresh clone deploys self-contained —
no pre-built artifacts, no manual steps.

1. Push this repo to GitHub (already done if you're reading this there).
2. Go to **render.com → New → Blueprint**, connect this repo.
3. Render reads [`render.yaml`](../render.yaml) and provisions both services on
   the **free plan**: `mondial-xi-api` and `mondial-xi-web`. The web service's
   `API_INTERNAL_URL` is wired to the API automatically.
4. First build takes ~3–5 min (the API downloads data + trains). When both are
   live, open the **web** service URL — it behaves exactly like `make dev`.

Notes:
- The browser only talks to the web service; Next proxies `/api/v1/*` to the
  API server-side, so there is no CORS to configure.
- Free web services **sleep after ~15 min idle** and cold-start in ~30–60 s.
  The first request after a nap is slow; everything works after.
- The snapshot SQLite DB is ephemeral on the free plan (regenerated at
  startup). For a persistent track record, attach a paid disk at
  `/app/data` or set `KICKOFF_DATABASE_URL` to managed Postgres.
- **Daily fresh data:** add a `RENDER_DEPLOY_HOOK` repo secret (Render →
  service → Settings → Deploy Hook) and the daily-refresh workflow triggers a
  rebuild each morning; each rebuild re-downloads the latest results.

## Run the container stack locally

```bash
docker compose up --build        # api :8000, web :3000 — no prerequisites
```

The images are identical to what Render builds. (Docker was not installed on
the original dev machine, so images were validated via the CI `docker` job
rather than run locally there.)

## Split host: frontend on Netlify/Vercel + API on Render/Railway/Fly

The frontend can live on a JS host (Netlify, Vercel) while the API runs on a
Python host. **The API cannot run as a Netlify/Vercel serverless function** —
it's a persistent Python process with numpy/scipy/scikit-learn/polars and a
trained model bundle, far past a function bundle's size/runtime limits. Deploy
`apps/api` to a host that runs a real process; the frontend's `/api/v1/*` proxy
([`app/api/v1/[...path]/route.ts`](../apps/web/app/api/v1/%5B...path%5D/route.ts))
forwards to it server-side (so no CORS), reading `API_INTERNAL_URL` at request
time.

1. **Deploy the API** to Render (New → Web Service → Docker,
   `infrastructure/api.Dockerfile`, free plan) — or Railway / Fly.io / Cloud Run
   with the same Dockerfile. The `mondial-xi-api` service in
   [`render.yaml`](../render.yaml) already describes this; via Blueprint you can
   ignore the `mondial-xi-web` service it also creates. Confirm
   `https://<api-host>/api/v1/health` returns `{"status":"ok"}`.
2. **Point the frontend at it**: set the site env var
   `API_INTERNAL_URL = https://<api-host>` (Netlify: Site configuration →
   Environment variables; Vercel: Project → Settings → Environment Variables),
   then **trigger a redeploy** so the proxy function picks up the new value.
3. Re-test `https://<your-frontend>/api/v1/health` — it should now return ok.

Gotcha: an unset `API_INTERNAL_URL` makes the proxy target `localhost:8000`, so
every call returns `{"error":{"code":"upstream_unreachable"}}` (502) — the tell
that the API host or env var is missing.

- **Database**: SQLite by default; set
  `KICKOFF_DATABASE_URL=postgresql+psycopg://…` for managed Postgres
  (SQLAlchemy handles both).

## Daily auto-update

The open dataset (martj42/international_results) is refreshed daily as matches
finish, so the platform can stay current with a scheduled job. One command
does the whole cycle:

```bash
make refresh   # re-download → rebuild → retrain → re-evaluate → re-snapshot
```

**Shipped automation:** `.github/workflows/daily-refresh.yml` runs this **every
30 minutes** (and on manual dispatch): it re-downloads the CC0 core, pulls the
Wikipedia fresh-results overlay, rebuilds, retrains, re-runs the leakage/metrics
tests as a sanity check, commits any changed JSON artifacts + README metrics
back to the repo (`[skip ci]`), and — if `RENDER_DEPLOY_HOOK` is set — redeploys
the live API so new results appear within the half-hour. If nothing changed
upstream, it no-ops.

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
