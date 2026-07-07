# Interview guide

Prep for defending every major decision. Format: likely question → the
answer grounded in this repo.

## Data & licensing

**Why this dataset?** Only license-clean (CC0) source with full international
coverage; 49.5k matches 1872→present, community-updated (our snapshot even
contains the in-progress WC-2026). Provenance: SHA-256 manifests per file.

**Why didn't you use injuries/lineups?** No free source grants publication
rights (API-Football explicitly excludes it; football-data.org lineups are
paid). Rather than scrape or fake, availability is "unknown" and scenario
inputs are labeled user assumptions. Architecture (providers, snapshot
versioning) is ready for a licensed feed.

**How do you handle renamed/dissolved countries?** Upstream former-names
table maps era names (Zaïre → DR Congo) to current identity; dissolved teams
(Czechoslovakia, East Germany, Yugoslavia) stay distinct; match pages show
the era-accurate name. Tests cover it.

## Leakage & evaluation

**How do you know there's no leakage?** Structurally: one forward pass,
features emitted before state update. Empirically: tests tamper with future
results, own results, and truncate the dataset — earlier features must be
identical. No rankings/odds/post-match stats in features at all.

**Why chronological splits?** Random splits let a 2024 match inform a 2019
prediction via shared team state → inflated metrics. Fit 1980–2018, select
2019–2022, single evaluation on 2023→cutoff.

**Your champion loses to Dixon–Coles on test — why keep it?** Selection was
pre-registered on validation (GBM 0.8555 vs DC 0.8606). Swapping after seeing
test = test-set shopping. The 0.004 gap is within noise; the GBM wins on
calibration (ECE 0.014 vs 0.017) which is what we display to users.

**Why is 60.8% accuracy good?** Three-class problem with structural draw
noise; frequency baseline is 47.2%, Elo 60.3%. Log loss/RPS are the honest
lens; we beat the naive baseline by ~0.18 log loss = large.

## Modeling

**Explain Dixon–Coles ρ.** Independent Poissons misprice low-scoring draws;
τ adjusts the 0-0/1-1/1-0/0-1 cells; we fit ρ by MLE on fitted means
(ρ ≈ small negative → more 0-0/1-1). Test: adjusting ρ raises P(0-0), P(1-1).

**Why isotonic per class?** GBM scores are discriminative but miscalibrated
(uncalibrated test log loss 0.873 > Elo). Isotonic on held-out validation
fixes reliability without touching ordering; renormalize across classes.

**Player impact from goals only — isn't that biased?** Yes, attack-side
only, and the UI says so. EB shrinkage (25-match zero prior, cap 0.9) keeps
small samples near zero; `shrinkage_weight` is displayed. It powers labeled
what-ifs, never the evaluated champion.

**How do doubtful players work?** Expected impact loss = (1−p)·impact —
marginalizing over availability instead of assuming in/out.

## Simulation

**How is it fast?** Score matrices cached per pairing; one vectorized
categorical draw per pairing across all sims; exact 4-team ranking memoized
on the score pattern. 10k sims ≈ 0.37 s (real state) / 2.3 s (full replay).

**2026 tiebreakers?** New this cycle: H2H before overall GD, FIFA ranking
replaces lots. Implemented exactly through criterion 6; conduct/ranking
proxied by Elo (no conduct data exists openly) — documented + tested,
including a three-way-tie case.

**The Germany bug** (tell it — it's a great story): eliminated Germany showed
3% title odds because my thirds-allocation differed from FIFA's actual
Annex-C assignment, so pinned R32 results didn't match simulated pairings.
Fix: recover the real R32 slot mapping from played matches. Lesson: pin real
state at the highest-fidelity level available.

## Engineering

**Why does serving never train?** Startup loads a joblib bundle; `make
train` is the only writer. Fast boots, reproducible responses, and the
artifact-trust boundary is explicit (docs/security.md).

**Snapshot immutability?** Unique (fixture_id, SHA-256(payload)); scoring
only appends result columns; changed forecasts insert new versions. No code
path can backdate a "published" forecast.

**Frontend state?** TanStack Query only; scenario state lives in the URL
(shareable, testable); no global store needed.

## Weak spots (own them before they ask)

Team-level champion; goal-detail coverage 34%; shootouts 50/50; not
deployed publicly yet; Docker verified in CI only; single-maintainer dataset
dependency (mitigated by manifests + validation).
