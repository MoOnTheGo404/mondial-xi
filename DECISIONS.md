# Decision log

Format: `D-### — decision — rationale — date`

- **D-001 — Product name "Kickoff Atlas"** — original, non-infringing,
  communicates football + cartographic/analytic breadth. 2026-07-06
- **D-002 — Open-data core = martj42/international_results (CC0)** —
  public-domain license permits redistribution and derived works; ~49k senior
  men's internationals since 1872 with tournament, city, country, neutrality;
  companion shootouts + goalscorers files. Verified license before download;
  see docs/data-source-evaluation.md. 2026-07-06
- **D-003 — Python 3.12 via uv** — system Python is 3.9 (EOL track); uv gives
  reproducible pinned toolchain without touching system. 2026-07-06
- **D-004 — pnpm workspaces + Next.js App Router + Tailwind v4** — matches
  spec; pnpm installed globally via npm (corepack not relied upon). 2026-07-06
- **D-005 — SQLite default persistence, Postgres-compatible via SQLAlchemy**
  — zero-config local run is a hard requirement. 2026-07-06
- **D-006 — Flags: `flag-icons` (lipis) MIT** — SVG, maintained, MIT license
  verified; internal team→ISO mapping table handles non-ISO teams (England,
  Scotland, Wales, N. Ireland have official GB-subdivision codes in the
  package); historical teams get a documented fallback glyph. 2026-07-06
- **D-007 — Optional live provider: football-data.org (free tier)** — free
  registration credential, includes World Cup & major comps, explicit ToS,
  lineups for recent matches; adapter env-gated by FOOTBALL_DATA_API_KEY.
  No credential in this environment → adapter tested against recorded local
  fixtures only. 2026-07-06
- **D-008 — Weather: Open-Meteo (no key, CC-BY 4.0, non-commercial free
  tier)** — used for display + scenario context only; NOT a trained model
  feature because historical per-match weather backfill for 49k matches is
  not feasible within API fair-use, so it would fail the "reliably available
  historically" bar. 2026-07-06
- **D-009 — No deep-learning framework** — dataset is tabular, n≈49k;
  gradient boosting + GLM-family models are the defensible ceiling.
  2026-07-06
- **D-010 — Player impact = attack-side only, from CC0 goalscorers, with
  empirical-Bayes shrinkage** — the only legally usable historical
  player-level signal without a paid provider. Defensive/GK impact honestly
  reported as unavailable without licensed data. Player-aware output is a
  labeled adjustment layer, not the evaluated champion. 2026-07-06
- **D-011 — Ratings: hand-rolled Elo with tuned K/home-adv/decay** — full
  control over time-decay + margin handling; standard approach in
  international football literature (WFE/Elo ratings). 2026-07-06
- **D-012 — Monorepo: uv for Python, pnpm for JS, single Makefile facade** —
  one-command bootstrap on a clean machine. 2026-07-06
- **D-013 — WC-2026 tournament config stored as versioned JSON with source
  citations** — 48 teams / 12 groups / round of 32 with 8 best thirds;
  verified via FIFA sources during research phase; engine is fully
  configurable so rule changes are data, not code. 2026-07-06
