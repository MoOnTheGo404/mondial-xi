# Résumé material — Mondial XI

Every figure here is measured in this repo and matches the auto-generated
README table and `ml/artifacts/metrics.json`. Champion = **geometric-mean
ensemble** (log-opinion pool of Elo-logistic × Dixon–Coles), selected fully
out-of-sample. Performance claims are documented in
[`PERFORMANCE.md`](./PERFORMANCE.md) with reproduction steps.

**Current numbers (untouched chronological test, n = 3,694):**
log loss **0.8644** · RPS **0.1686** · Brier **0.5084** · top-pick acc.
**60.2%** · ECE **0.0175** · vs ~1.05 frequency baseline. Data: **49,500**
public-domain internationals (1872–2026).

---

## AI/ML résumé

- Built an international-football forecasting platform on **49,500 public-domain
  matches (1872–2026)**; chronologically evaluated 6 probabilistic models and
  shipped a **parameter-free geometric-mean ensemble** (Elo-logistic ×
  Dixon–Coles) at **0.864 log loss / 60.2% top-pick accuracy / 0.017 ECE** on an
  untouched **3,694-match** test window (vs ~1.05 frequency baseline).
- Enforced **temporal integrity** with a leakage-test suite proving future
  results cannot alter any pre-match feature, and pre-registered model selection
  on a **chronological** validation split (never random) — the discipline most
  sports models skip.
- Designed a **vectorized Monte Carlo tournament engine** (10,000 World Cup
  simulations in **~0.33 s**) with official 2026 tie-break rules,
  extra-time/penalties, and user-lockable upsets; plus an aging-aware 2030
  outlook from a data-measured scoring-survival curve and ±63-Elo 4-year
  uncertainty.
- Shipped **isotonic-calibrated** probabilities and a tamper-evident,
  SHA-256-hashed forecast track record scored post-kickoff; a live-results
  pipeline overlays Wikipedia onto the CC0 core so finished matches auto-grade.

## Embedded / systems résumé

*(This is a Python ML/web project — no firmware/C. These bullets sell the
transferable systems & performance work; place under "Projects" as fits.)*

- Cut a Monte Carlo simulation endpoint from **~20 s → ~5 s** by tracing the
  bottleneck to a per-realization GLM rebuild (**~21k builds/request**) and
  replacing it with a **closed-form analytic update** (`mu·exp(±k·shift)`) over
  a shared base cache plus import-time precomputed lookup tables — output bit-for-
  bit identical; also sped the 10k-sim run 0.46 s → 0.33 s. *(see PERFORMANCE.md)*
- Diagnosed and fixed a **512 MB OOM** in a containerized deploy: root-caused it
  to the runtime command re-fetching platform binaries at container start, and
  re-architected to a **self-contained (standalone) build** that boots under the
  cap and binds cleanly. *(see PERFORMANCE.md)*
- Built **deterministic, reproducible pipelines**: seeded end-to-end runs,
  **SHA-256 content-hashed** data-provenance manifests, and multi-stage Docker
  images — gated by GitHub Actions CI (lint/type/unit/integration/e2e + a
  container smoke-test) and a self-healing 30-minute data-refresh job.
- Implemented the numerical models **from first principles** — Elo rating
  dynamics and a Dixon–Coles bivariate-Poisson goal model — in a typed monorepo
  with a 100+-test suite.

## Tech stack line

Python · FastAPI · scikit-learn · Polars · NumPy · SciPy · Next.js 16 ·
React 19 · TypeScript · Tailwind · TanStack Query · SQLite/SQLAlchemy ·
Playwright · Docker · GitHub Actions.

## Interview-ready talking points

- Why chronological (not random) validation, and the leakage tests that enforce
  it.
- Champion pre-registered on validation; honest reporting that the geometric
  ensemble edges the calibrated GBM on test (0.8644 vs 0.8701) and that the
  standalone Dixon–Coles is close behind (0.8662).
- The 20 s → 5 s optimization: *why* the aging delta is exactly linear in the
  GLM, so it can be applied in closed form instead of rebuilding — and how you'd
  verify results are unchanged (identical RNG path).
- The OOM: why `pnpm exec` at container start blew the memory cap, and why
  standalone output is the fix.
- Availability model: goal-involvement shares blended with Wikidata career
  rates; refused to fabricate an assists source it lacks a license for.
