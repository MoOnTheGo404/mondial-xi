# Tasks

Legend: [ ] todo · [~] in progress · [x] done

## Phase 1 — Environment & init
- [x] Inspect environment (macOS arm64, Node 24, brew Python 3.11, no docker)
- [x] Install uv + Python 3.12.13, pnpm 11.10
- [x] .gitignore before any downloads/secrets
- [x] CLAUDE.md, IMPLEMENTATION_PLAN.md, DECISIONS.md, RISK_REGISTER.md, TASKS.md

## Phase 2 — Research
- [~] Provider & licensing research (subagent)
- [~] WC-2026 rules + groups verification (subagent)
- [~] Flags / weather / asset licensing verification (subagent)
- [ ] docs/data-source-evaluation.md finalized
- [ ] Product scope matrix

## Phase 3 — Skeleton
- [ ] Monorepo dirs, pyproject (uv), pnpm workspace, Makefile
- [ ] Ruff / mypy / ESLint / Prettier / pytest / Vitest wiring

## Phase 4 — Data
- [ ] Ingestion script + SHA-256 manifest + raw immutable storage
- [ ] Validation (schema, scores, dupes) + processed parquet
- [ ] Mini fixtures committed; data-quality report

## Phase 5 — Entities & features
- [ ] Canonical team registry incl. historical identities + ISO/flag map
- [ ] Chronological feature builder + leakage tests

## Phase 6–7 — Models & evaluation
- [ ] Elo (tuned) + probability head
- [ ] Poisson + Dixon–Coles
- [ ] Challenger (boosted/multinomial) + calibration
- [ ] Walk-forward evaluation, metrics.json, model card

## Phase 8 — Player layer
- [ ] Player registry from goalscorers (CC0), shrunken attack impact
- [ ] Availability states + scenario adjustment layer
- [ ] Provider interfaces + football-data.org adapter (env-gated) + fixtures

## Phase 9 — Simulation
- [ ] Vectorized MC engine (groups, tiebreaks, thirds, brackets, ET/pens)
- [ ] WC-2026 config (verified) + tests

## Phase 10 — API
- [ ] FastAPI v1 endpoints + snapshots (SQLite) + provider status + tests

## Phase 11 — Frontend
- [ ] Design system + layout + flags
- [ ] Home / Fixtures / Match Center / Match Lab / Scenario Compare
- [ ] Tournament Simulator / Team Explorer / Player Explorer
- [ ] Archive / Model Performance / Methodology

## Phase 12–14 — Test, QA, package
- [ ] Vitest + Playwright e2e
- [ ] Visual QA + screenshots + a11y pass
- [ ] Dockerfiles, compose, GitHub Actions, docs suite, README
