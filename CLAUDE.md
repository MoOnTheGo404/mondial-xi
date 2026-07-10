# CLAUDE.md — Engineering guide for this repository

**Product:** Mondial XI — an international football forecasting & tournament
simulation platform. Open-data core (CC0 historical results), provider-based
architecture for optional live enrichment, chronologically-validated
probabilistic models, Monte Carlo tournament engine, Next.js frontend.

## Golden rules (non-negotiable)

1. **No fabricated data.** Every metric, prediction, injury, fixture, or
   provenance claim must trace to a real artifact or provider response.
2. **Temporal integrity.** Pre-match features may only use information
   available strictly before kickoff. Leakage tests live in
   `tests/unit/ml/test_leakage.py` and must always pass.
3. **Chronological evaluation only** for model selection (no random splits).
4. **Every prediction carries** model version + data cutoff + data-quality
   grade. Backtests are never presented as published forecasts.
5. **Graceful degradation.** No credentials → open-data core still works
   fully; provider-backed features report "unavailable", never fake values.
6. **No unlicensed assets.** Flags come from `flag-icons` (MIT). No federation
   crests, tournament logos, player photos without verified license.

## Layout

- `apps/api` — FastAPI app (Python 3.12, uv-managed, SQLite by default)
- `apps/web` — Next.js 15 App Router, TypeScript strict, Tailwind v4
- `ml/` — ingestion → validation → entities → features → ratings → models →
  evaluation → simulation. Pure Python package `kickoff_ml`.
- `ml/artifacts/` — trained artifacts + `metrics.json` etc. (JSON committed,
  binaries regenerated via `make train`)
- `data/` — `raw/` (immutable downloads, gitignored), `processed/` (parquet,
  gitignored), `manifests/` (committed provenance JSON), `fixtures/`
  (committed miniature test data)
- `docs/` — methodology, model card, data card, screenshots

## Commands

`make bootstrap` install everything · `make data` download+build datasets ·
`make train` train models · `make evaluate` produce evaluation artifacts ·
`make dev` run API (:8000) + web (:3000) · `make test` all unit+integration ·
`make test-e2e` Playwright · `make lint` / `make typecheck` / `make build` ·
`make check` lint+typecheck+test.

Python tooling: `uv run --project apps/api …`, Ruff, pyright(basic)/mypy.
Frontend: pnpm workspaces, ESLint flat config, Prettier, Vitest, Playwright.

## Conventions

- Python: typed, Pydantic v2 models at boundaries, `structlog` logging.
- Internal canonical team IDs are slugs (e.g. `brazil`); mapping tables in
  `ml/entities/`. Historical identities (e.g. West Germany) map to successor
  or stay distinct — see `docs/methodology.md`.
- API errors: RFC-7807-style `{"error": {code, message, detail}}`.
- Frontend server state via TanStack Query; no global state library.
- Never train models at API startup; API loads artifacts read-only.
