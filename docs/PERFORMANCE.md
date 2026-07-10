# Performance notes

Two optimizations worth walking through. Both are reproducible from this repo;
each cites the commit and the way the numbers were measured, so the claims are
verifiable rather than asserted.

## 1. Interactive WC-2030 outlook: ~20 s → ~5 s

**Symptom.** The 2030 outlook (4,000 Monte Carlo tournaments × 16 draw blocks)
took ~20 s server-side. That was long enough for the browser → Next proxy path
to time out and surface a **500**, even though the API itself returned 200.

**Root cause.** The outlook applies an *aging* adjustment per team, so the
naive path rebuilt the Poisson goal GLM (and its backing DataFrame) once per
realization — on the order of **~21k** GLM/DataFrame builds per request — plus
`score_matrix` rebuilt its factorial/index arrays on every one of ~40k calls.

**Fix** (`14a74e7`):
- **Analytic aging delta.** The aging adjustment only shifts `elo_diff_eff`,
  which enters the goal GLM linearly. So base expected goals are computed
  **once per pairing** (shared cache across all realizations) and the age shift
  is applied in closed form as `mu · exp(±k · shift)`. This replaces the ~21k
  per-call GLM builds with a few hundred. Output is **identical** (same RNG
  path; the shift is exact, not approximated).
- **Precomputed score matrix.** The Poisson index and factorial arrays
  (`_IDX`, `_FACT` in `ml/kickoff_ml/models/goals.py`) are built once at import
  instead of per call, and the Dixon–Coles low-score correction is inlined as
  scalars.

**Measured.**
- 2030 outlook, 4,000 × 16: **~20 s → ~5 s** (re-measured on the running API:
  4.9–5.3 s across three runs; matches the 5.3 s recorded at commit time).
- 2026 tournament sim (10k): **0.46 s → 0.33 s** as a side effect.
- Correctness held: the Dixon–Coles and goal-model unit tests pass unchanged.

**How to reproduce.**
```bash
time curl -s -X POST localhost:8000/api/v1/simulations/tournament \
  -H 'content-type: application/json' \
  -d '{"tournament_id":"wc2030","n_sims":4000,"seed":42,"blocks":16}' >/dev/null
```

## 2. 512 MB OOM on the container runtime

**Symptom.** The web container **built** fine but was killed on deploy with
`Out of memory (used over 512Mi)` and `No open ports detected` on a 512 MB
instance — it never bound a port.

**Root cause.** The runtime command was `pnpm --filter @kickoff/web exec next
start`. At container start, pnpm re-verified the lockfile and **re-downloaded
platform-specific binaries** (`@next/swc-*`, `@tailwindcss/oxide-*`,
`@rolldown/binding-*`, …). That fetch/verify spike exceeded 512 MB before Next
could listen, so the platform's health check saw no open port and killed it.

**Fix** (`d0b7af2`). Switch to Next.js **standalone output**
(`output: "standalone"` + `outputFileTracingRoot` at the monorepo root so the
pnpm-workspace packages are traced in). The runtime image now copies only
`.next/standalone` + `.next/static` and runs `node apps/web/server.js` — a
self-contained server with just the traced dependencies. **No pnpm and no
install at container start**, so the boot footprint is a fraction of before and
it binds cleanly under the cap. `HOSTNAME=0.0.0.0` is set so the platform can
route to it.

**Verified.** Standalone server boots and serves `/`, `/simulator`, and proxies
`/api/v1/*` to `API_INTERNAL_URL` (tested locally in the exact Docker layout);
the CI `docker` job builds the image; the service now reaches "live" on the
512 MB instance instead of OOM-looping.
