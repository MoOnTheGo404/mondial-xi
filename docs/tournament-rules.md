# Tournament rules — WC 2026

Rules live in **versioned configuration** (`data/tournaments/wc2026.json`,
config_version 1.0.0, verified 2026-07-06), not code. Sources are cited in
the file and in `docs/research/wc2026.md` (FIFA.com, Wikipedia knockout-stage
page, MLSSoccer tiebreaker explainer, FOX Sports).

## Format (verified)
48 teams · 12 groups of 4 · top two per group + 8 best third-placed teams →
Round of 32 → R16 → QF → SF → third-place match → Final (July 19, MetLife).
The engine consumes the official R32 slot template (matches 73–88) and the
fold chains for later rounds.

## Group tiebreakers (2026 order, verified — H2H now precedes overall GD)
1. Points · 2. H2H points among tied teams · 3. H2H goal difference ·
4. H2H goals · 5. overall goal difference · 6. overall goals scored ·
7. team conduct (fair play) · 8. FIFA ranking (no drawing of lots).

**Engine approximation (documented):** criteria 1–6 are implemented exactly
(including tied-cluster mini-tables); conduct data does not exist in the open
dataset, so criteria 7–8 are proxied by current Elo. Unit tests cover clear
orders, two-way and three-way H2H ties, and the full-tie fallback.

## Best thirds
Ranked by points → GD → goals → (conduct → ranking, same proxy); the top 8
advance. Slot assignment: FIFA's Annex C (495 combinations) is not publicly
retrievable, so re-simulations assign thirds by deterministic constraint
satisfaction over each slot's allowed source groups. **The real tournament's
actual allocation is recovered from the played R32 matches**, so
real-state simulations use zero approximation here.

## Knockouts
Level after 90' → 30' extra time → penalties. Engine: ET scorelines from
DC matrices with ⅓-scaled means; shootouts 50/50 (documented; no licensed
shootout-skill data).

## Real-state reconstruction
`kickoff_ml.simulation.wc2026_state` derives everything from the dataset:
group tables (exact tiebreakers), completed knockout results incl. shootout
winners, the actual R32 template mapping, and the surviving bracket. Group I
computed from raw results matches the independently verified Wikipedia table
exactly (France 9/+8, Norway 6/+1, Senegal 3/+2, Iraq 0/−11) — a
whole-pipeline validation.

## Other tournaments
The engine is fully config-driven (any group count, best-thirds count, fold
chain), demonstrated by the toy 2-group tournament in the unit tests. Only a
new JSON config (+ citations) is needed for future editions.
