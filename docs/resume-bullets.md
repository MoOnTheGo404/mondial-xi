# Résumé material — Mondial XI

All figures are measured/verified in this repo (metrics.json, test suite,
manifests). Pick the length that fits your résumé.

## One-line headline
**Mondial XI** — full-stack international-football forecasting &
Monte-Carlo tournament-simulation platform (Next.js + FastAPI + Python ML),
built on 49k+ public-domain matches with leakage-safe, calibrated models.

## Tech stack line
Python · FastAPI · scikit-learn · Polars · NumPy · Next.js 16 · React 19 ·
TypeScript · Tailwind · TanStack Query · SQLite/SQLAlchemy · Playwright ·
Docker · GitHub Actions.

## Standard entry (4 bullets)
- Built a full-stack football analytics platform (Python ML monorepo →
  FastAPI → Next.js) on **49,499 public-domain international matches
  (1872–2026)**; chronologically evaluated 5 probabilistic models and shipped
  a calibrated gradient-boosting champion at **0.870 log loss / 60.8%
  top-pick accuracy / 0.014 ECE** on a held-out 3,693-match test window
  (vs 1.05 baseline).
- Engineered a **leakage-safe chronological feature pipeline** (single
  forward pass over 154 years of results) with a temporal-integrity test
  suite proving future data cannot alter historical feature vectors — the
  discipline most sports models get wrong.
- Designed a **vectorized Monte-Carlo tournament engine** simulating
  **10,000 World Cup outcomes in ~0.4 s** (official 2026 tie-break rules,
  best-thirds allocation, extra-time/penalties, lockable upsets) plus a 2030
  outlook that models **squad aging** from a data-measured scoring-survival
  curve and **±63-Elo four-year uncertainty**.
- Shipped an **auditable, tamper-evident forecast track record**
  (SHA-256-hashed immutable snapshots, scored post-kickoff) and integrated
  two CC0 data sources (results + Wikidata career stats for 7,400 players);
  **86 Python + 12 component + 13 end-to-end tests**, CI, Docker, and full
  methodology docs.

## Compact entry (2 bullets)
- Full-stack football forecasting platform (FastAPI + Next.js 16 + Python
  ML): calibrated model at **0.870 log loss / 60.8% accuracy** on a
  leakage-safe chronological test set of 3,693 matches; vectorized
  Monte-Carlo engine runs **10k tournament simulations in ~0.4 s**.
- Integrated CC0 data (49k matches + Wikidata player stats), an
  aging-aware 2030 outlook, tamper-evident forecast snapshots, and a
  111-test suite with CI/Docker — built end-to-end solo.

## Interview-ready talking points
- Why chronological (not random) validation, and the tests that enforce it.
- Champion selection pre-registered on validation; honest reporting that
  Dixon–Coles edges the GBM on test by 0.004.
- Availability model: goal-involvement shares blended with Wikidata career
  rates; assists wired at 0.5 weight but null (no licensed source — refused
  to fabricate).
- 2030 aging: measured survival curve + centered relative-aging Elo deltas +
  measured 4-year noise = an outlook that gets *humbler* with the horizon.
