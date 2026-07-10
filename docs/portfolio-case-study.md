# Case study — Mondial XI

## The problem

Football forecasting sites either hide their method ("AI prediction!") or
quietly leak the future into their backtests. I wanted a portfolio project
that does the opposite: a real product where every probability can be traced
to open data, a written protocol, and a reproducible artifact — and where
the fun parts (what if Haaland is out? lock the upset!) are built on the same
honest machinery.

## Data constraints shaped everything

Research first (docs/data-source-evaluation.md): the only license-clean core
is the CC0 international results dataset (~49.5k matches, 1872→present, with
goalscorers and shootouts). Injuries and lineups have **no** free source with
publication rights — API-Football's free tier includes them but its terms
forbid publishing. Decision: build a team-level champion on CC0 data,
implement the player/availability architecture honestly (attack-side impacts
from scoring records; availability "unknown" by default; scenarios as labeled
user assumptions), and keep provider adapters as the upgrade path.

A lucky consequence of using live-maintained open data: the snapshot contains
the *actual in-progress* World Cup 2026 — so the simulator pins real results
and forecasts only the remaining rounds, and the track record contains real
prospective predictions with zero credentials.

## Temporal leakage, treated as a hard invariant

All rolling state is built in one forward pass that emits features before
consuming results. Tests prove: tampering with a future result, tampering
with the match's own result, and truncating the dataset all leave earlier
feature vectors byte-identical. Chronological fit/validation/test windows;
champion frozen on validation before test was touched.

## Modeling

Tuned Elo (grid on validation) → Poisson GLMs → Dixon–Coles (ρ by MLE) →
calibrated GBM. Result on the untouched test window (n=3,689): log loss
0.870 vs 1.054 frequency baseline, top-pick accuracy 60.8%, ECE 0.014.
Honest finding: Dixon–Coles edges the GBM on test by 0.004 — international
outcomes are rating-gap dominated; the GBM mostly buys *calibration* (its
uncalibrated version is worse than Elo). That finding is printed on the
Performance page rather than buried.

## Simulation engineering

The Monte Carlo engine samples scorelines from cached Dixon–Coles matrices
with one vectorized categorical draw per pairing; exact 2026 tiebreakers
(H2H-before-GD, a rule change this cycle) run through a memoized 4-team
ranker; best-thirds slotting is constraint satisfaction (FIFA's Annex C isn't
public — documented). 10,000 tournaments in ~0.37 s from the real state,
~2.3 s for full replays. A subtle bug made this concrete: my solver's thirds
allocation differed from FIFA's actual one, so pinned R32 results didn't
match their simulated pairings and eliminated Germany kept "winning" 3% of
titles — fixed by recovering the real R32 template mapping from the played
matches. Validation: group tables computed from raw results reproduce the
independently verified Wikipedia standings exactly.

## Product & design

Next.js 16 App Router with an editorial "night pitch" identity (Tailwind v4
tokens, Archivo + Plex Mono, an emerald/azure colorblind-safe probability
palette with a trophy-gold champion accent, restrained motion). Every page is
functional: the Match Lab debounces scenario
edits into the API and encodes the entire scenario in the URL; the simulator
exposes seeds, locks and CSV export; every forecast shows model version,
data cutoff, quality grade and generated explanations. Empty states say *why*
(no lineup feed configured) instead of pretending.

## Testing & ops

78 Python/JS unit+integration tests (leakage, tiebreakers, calibration,
honest-degradation API cases) + 12 Playwright journeys with console-error
assertions; ruff/mypy/tsc/eslint clean; CI builds artifacts from scratch,
runs everything, builds Docker images and smoke-tests the API container.
Immutable content-hashed prediction snapshots give an auditable track record.

## Tradeoffs I'd defend

- No deep learning: n≈50k tabular rows; GBM/GLM is the honest ceiling.
- Serving the evaluated pipeline (fit ≤2018) instead of refitting on
  everything: metrics describe the exact deployed artifact; ratings still
  advance to the cutoff.
- Shootouts 50/50 and conduct-tiebreak proxied by Elo: documented
  approximations beat invented signals.

## Limitations

Team-level champion (no licensed lineup history to beat it with); ~34%
goal-detail coverage bounds player stats; not yet publicly deployed; Docker
verified in CI, not on the dev machine.
