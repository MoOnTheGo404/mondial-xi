# Architecture

## Monorepo layout

- `ml/kickoff_ml/` — pure-Python package: `ingestion` (download + manifests +
  parquet build), `entities` (canonical teams/players), `features`
  (chronological builder), `ratings` (Elo), `models` (goal + outcome models,
  player impact, serving engine), `evaluation` (walk-forward protocol,
  metrics, artifacts), `simulation` (Monte Carlo engine + WC-2026 state),
  `providers` (dataset / football-data.org / Open-Meteo adapters).
- `apps/api/kickoff_api/` — FastAPI app. Loads artifacts read-only at startup
  (never trains), owns the SQLite snapshot store, exposes `/api/v1`.
- `apps/web/` — Next.js 16 App Router (React 19, Tailwind v4, TanStack Query,
  Recharts). Server state only via React Query; no global state library.
- `packages/shared` — TS types + typed fetch client shared by app & UI kit.
- `packages/ui` — presentational primitives (Flag, ProbBar, Card, …).
- `data/` — `raw/` (immutable downloads, gitignored), `processed/` (parquet,
  gitignored), `manifests/` (committed provenance + quality reports),
  `fixtures/` (committed test slices), `tournaments/` (versioned rule configs).
- `ml/artifacts/` — evaluation outputs; JSON committed, binaries rebuilt.

## Key flows

### Data → artifacts (`make data && make train`)
1. `ingestion.download`: HTTPS fetch of 4 CC0 CSVs; SHA-256, row counts,
   date ranges and license recorded per file in `data/manifests/*.json`.
2. `ingestion.build`: schema/score/dupe validation → canonical team IDs
   (former-name resolution, historical identities kept distinct) → sorted
   parquet (`matches`, `upcoming`, `goalscorers`, `teams`) + quality report.
3. `models.players`: goalscorer aggregation → shrunken attack impacts.
4. `evaluation.run`: Elo grid tuned on validation → walk-forward features →
   five candidate models → chronological comparison → calibration → metrics
   artifacts → serving bundle (`prediction_bundle.joblib`).

### Serving
- `PredictionEngine` wraps the bundle: features come from the final builder
  state (ratings/form at data cutoff); champion probabilities from the
  calibrated GBM; scoreline matrices from Dixon–Coles; scenario adjustments
  tilt champion probs by the DC probability ratio (documented mechanism).
- `TournamentSimulator` consumes any `TournamentConfig` (groups, first-round
  template, fold chain, best-thirds count); WC-2026 real state is
  reconstructed from the dataset each request and pinned.
- Snapshots: startup + `scripts/run_snapshots.py` create immutable rows for
  genuinely-upcoming fixtures and score finished ones. Uniqueness =
  (fixture_id, content_hash); re-forecasts insert new rows.

### Frontend
- Browser → Next.js rewrite `/api/v1/*` → FastAPI (server components call the
  API directly via `API_INTERNAL_URL`).
- The historical dataset never ships to the browser: pages request paginated
  or pre-aggregated slices (Elo history is thinned server-side to ≤400 pts).

## Measured performance (Apple Silicon dev machine, 2026-07-07)

- Full 49,495-match walk-forward feature build: **0.39 s**
- Single prediction (engine, warm): **~49 ms median** (cold 59 ms)
- 10,000-run WC-2026 simulation from real state: **0.37 s** engine /
  ~0.4 s through the API (`elapsed_ms` is returned on every response)
- Full-tournament what-if replay, 10,000 runs: **~2.3 s**
- `make evaluate` end-to-end (Elo grid + 6 models + artifacts): **~2 min**
- Next.js production build: 14 routes, all static except dynamic detail pages

## Decisions & tradeoffs (abridged — see DECISIONS.md)
- **uv + pnpm + Makefile facade** for a one-command bootstrap.
- **SQLite default, PostgreSQL-compatible** via SQLAlchemy URL.
- **No deep learning**: tabular n≈50k; GBM/GLM is the defensible ceiling.
- **Serving = evaluated pipeline** (fit ≤2018, calibrated 2019-22): metrics
  describe the exact deployed artifact; only rating state advances.
- **Startup jobs instead of a worker queue** for snapshots at this scale;
  cron design for production in docs/deployment.md.
