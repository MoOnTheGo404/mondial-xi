# Availability model

## States

The domain model supports: confirmed starter/substitute, expected
starter/substitute, available, doubtful, questionable, injured, suspended,
not selected, withdrawn, unavailable-other, **unknown**. In the current
open-data deployment every real player's state is **unknown** — and the API
says so (`/fixtures/{id}/availability` returns `status: "unknown"`,
`official: false`, `source: null`) rather than inferring anything.

## Why nothing is inferred

- No free provider grants publication rights for injury feeds
  (API-Football's terms exclude publication; football-data.org lineups are a
  paid tier) — see docs/data-source-evaluation.md.
- "Not in an expected lineup" is never treated as injury; no medical
  diagnoses are ever inferred; historical injury lists cannot be
  reconstructed without post-hoc knowledge (leakage), so we refuse to.

## User scenarios

Users may set assumptions in Match Lab / Compare (or via the API):

- `unavailable` — full impact removed;
- `doubtful (p)` — expected impact loss `(1−p)·impact`, i.e. marginalized
  over availability rather than pretending certainty.

Every response labels these as user assumptions, lists each player's
`xg_effect`, and preserves the untouched team-only forecast. Snapshots record
`lineup_status: none_available` so the track record can never claim lineup
knowledge it didn't have.

## With a licensed feed (design)

An `AvailabilityProvider` adapter would attach per-player status with source,
retrieval timestamp, effective fixture, confidence and official/inferred
flag; forecast versions would then progress `early → squad-announcement →
expected-lineup → confirmed-lineup`, each an immutable snapshot (the
versioning column already exists in the store).
