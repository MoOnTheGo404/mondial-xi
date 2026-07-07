# Implementation plan — Kickoff Atlas

Working name: **Kickoff Atlas** — probabilistic forecasting and tournament
simulation for international football.

## Strategy

Build a fully working open-data vertical first (data → models → evaluation →
API → UI), then layer optional provider enrichment behind interfaces. Every
phase ends with passing tests and a commit.

## Phases

1. **Environment + repo init** — toolchain (uv/Python 3.12, pnpm/Node 24),
   .gitignore, planning docs. ✅
2. **Research** — data sources, licenses, WC-2026 rules, flags, weather.
   Output: `docs/data-source-evaluation.md`, DECISIONS entries.
3. **Skeleton** — monorepo layout, pyproject (uv workspace), pnpm workspace,
   Makefile, lint/type/test tooling wired.
4. **Ingestion** — reproducible download of the CC0 international results
   dataset (martj42), SHA-256 manifests, schema validation, parquet outputs,
   committed mini-fixtures.
5. **Entities + features** — canonical team registry (incl. historical
   identities), chronological feature builder with leakage tests.
6. **Baselines** — Elo (tuned), independent Poisson, Dixon–Coles.
7. **Challenger + evaluation** — gradient-boosted / multinomial challenger,
   walk-forward chronological evaluation, calibration, metrics.json,
   model-comparison.json, calibration artifacts, model card.
8. **Player layer** — goalscorer-derived player registry + shrunken attacking
   impact estimates; availability states; scenario adjustment layer
   (clearly labeled, honest about coverage). Provider interfaces for richer
   data (football-data.org adapter, env-gated).
9. **Simulation** — vectorized Monte Carlo group+knockout engine, versioned
   tournament configs (WC-2026 format verified from sources).
10. **API** — FastAPI v1 endpoints, artifact loading, SQLite persistence for
    prediction snapshots, provider status, OpenAPI.
11. **Frontend** — Next.js app: Home, Fixtures, Match Center, Match Lab,
    Scenario Compare, Tournament Simulator, Team Explorer, Player Explorer,
    Archive, Model Performance, Methodology.
12. **Testing** — pytest (unit/integration), Vitest, Playwright e2e.
13. **QA** — visual QA via Playwright screenshots, accessibility pass,
    performance measurements.
14. **Packaging** — Dockerfiles, compose, GitHub Actions, docs, README,
    case study, interview guide.

## Honesty boundaries baked into scope

- No paid API credential exists in this environment → live fixtures,
  injuries, confirmed lineups ship as **provider adapters + graceful empty
  states**, exercised in tests via local fixture providers.
- Player-aware layer trains only on legally usable data (CC0 goalscorers →
  attack-side impact with shrinkage). It is a labeled scenario/adjustment
  layer; the team-level model remains the evaluated champion unless data
  proves otherwise.
- Docker is not installed on this machine → Docker artifacts authored but
  container startup not verified here (documented).
