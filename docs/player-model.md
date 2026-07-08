# Player model

## What exists in legally usable data

The only player-level signal in the CC0 core is the **goalscorer log**
(47,875 events; ~34% of scoring matches, biased toward major tournaments).
There are no lineups, minutes, positions, defensive actions, or club data
with publication rights on a free tier. The design follows from that
constraint honestly.

## Attack-impact estimate

For player *p* with `G` recorded goals and `N` team matches during their
active window (first→last recorded goal):

```
impact(p)        = min( G / (N + 25), 0.9 )      # EB shrinkage to a zero prior
impact_recent(p) = impact(p) × max(0, 1 − days_since_last_goal / 730)
```

- The 25-match pseudo-count means a 2-goals-in-3-matches flash never outranks
  a sustained scorer; `shrinkage_weight = N/(N+25)` is displayed so users see
  how much of the estimate is data vs prior.
- Interpretation: shrunken expected goals contributed per team match,
  **attack-side only**. The UI states explicitly that this is *not* overall
  player quality (defenders/keepers barely appear in scoring logs).
- Goal counts are labeled **recorded** goals with a per-player coverage
  figure (share of the team's matches in the player's span that have scorer
  detail) — they are floors, not career totals.
- Same-named players of one country share an ID (no birthdates in the
  source); careers with a >10-year scoring gap are flagged
  `possible_name_collision` and warned about in the UI.

## How it enters forecasts

Only through **labeled scenarios** (Match Lab / Compare / API `scenario`),
via each player's `goal_share_recent`: their share of the team's recorded
goals over the trailing 4 years, shrunk with an 8-pseudo-goal prior. Shares
are **coverage-robust** — numerator and denominator come from the same
covered matches, so the ~30–70% scorer-detail coverage cancels out (unlike
absolute rates, which it would bias low). Removing players scales expected
goals by `(1 − Σ shares)` (no-replacement bound, stated in every
explanation; capped at −90%), floored at 0.15 xG; doubtful players
contribute `(1−p_avail)×share`. The Dixon–Coles matrix is recomputed and the
champion probabilities tilted by the DC ratio; the unadjusted team-only
forecast is always returned alongside. Removing a team's whole known
attacking core therefore collapses its attack — e.g. Argentina with all 12
listed contributors out drops from ~39% to ~5% vs France.

## What we deliberately do NOT claim

- No claim that the player layer improves historical accuracy — there is no
  historical availability data to validate against, so the team-level model
  remains the evaluated champion (see RISK_REGISTER R-03).
- No defensive or goalkeeper impacts ("n/a" in the UI, not zeros).
- No use of popularity, transfer values, or video-game ratings.

## Upgrade path with licensed data

The provider interfaces (`SquadProvider`-shaped adapters) and the scenario
mechanism are the integration points: with licensed historical lineups one
would (1) build availability-timestamped features, (2) evaluate player-aware
vs team-only over identical fixtures chronologically, (3) promote only on
measured improvement — the protocol in docs/methodology.md already covers it.
