# Tasks

Legend: [ ] todo · [~] in progress · [x] done

## Done
- [x] Phase 1 — env inspection, toolchain (uv/py3.12, pnpm), planning docs
- [x] Phase 2 — research (providers/licensing, WC-2026 rules+groups, assets/stack)
      → docs/research/*, docs/data-source-evaluation.md, scope matrix
- [x] Phase 3 — monorepo skeleton, uv+pnpm workspaces, Makefile, lint/type wiring
- [x] Phase 4 — ingestion w/ SHA-256 manifests, validation, parquet, quality report,
      committed mini-fixtures (49,495 matches; 6 real upcoming WC-2026 fixtures)
- [x] Phase 5 — canonical entities (former names, dissolved states, flags,
      confederations), chronological feature builder, leakage tests
- [x] Phase 6–7 — tuned Elo, Poisson, Dixon–Coles, calibrated GBM; walk-forward
      eval; champion gbm_calibrated (test LL 0.8701, acc 60.8%, ECE 0.0137)
- [x] Phase 8 — goalscorer player registry + EB-shrunk attack impact;
      availability states (all honestly "unknown"); provider adapters
      (local dataset, football-data.org env-gated, Open-Meteo)
- [x] Phase 9–10 (scoped honestly) — player-aware = labeled scenario layer;
      context features evaluated, weather kept display-only (documented)
- [x] Phase 11 — artifacts: metrics/comparison/calibration/test-preds/bundle/cards
- [x] Phase 12 — immutable snapshot track record (SQLite, content-hashed, scored)
- [x] Phase 13 — MC tournament engine (2026 tiebreakers, thirds, locks, seeds);
      WC-2026 real-state reconstruction; 10k sims 0.37s
- [x] Phase 14 — FastAPI v1 (20+ endpoints), 20 integration tests
- [x] Phase 15–19 — Next.js frontend: 12 pages, design system, flags, charts,
      Match Lab URL scenarios, Compare, Simulator (locks+CSV), explorers,
      archive, performance, methodology
- [x] Phase 20 — Vitest (12), Playwright e2e (12 journeys incl. a11y/mobile/
      console checks); ruff+mypy+eslint+tsc clean; prod build green
- [x] Phase 22 — Dockerfiles, compose, GitHub Actions CI, docs suite, README
      with artifact-generated metrics

## In progress
- [~] Phase 21 — visual QA screenshot sweep → docs/screenshots + fixes

## Remaining
- [ ] Alembic migration baseline (currently create_all; design documented)
- [ ] Zod validation at one API boundary (dep present, unused)
- [ ] Final review pass + handoff summary
- [ ] (env-blocked) Docker local verification — no Docker on this machine;
      CI builds + smoke-tests images
