# Data card

## Primary dataset — martj42/international_results

- **Source:** https://github.com/martj42/international_results (CSV files)
- **License:** CC0 1.0 Universal (public domain) — verified on the repo;
  redistribution and derivatives permitted.
- **Retrieved:** see `data/manifests/*.json` (timestamp + SHA-256 per file).
- **Contents (at current snapshot):** 49,495 validated completed senior men's
  full internationals (1872-11-30 → 2026-07-05), 6 scheduled fixtures,
  47,875 goal events, 680 shootouts, 36 former-name mappings. Exact counts
  regenerate with the data and live in `data/manifests/data_quality.json`.
- **Fields:** date, home/away team (era-accurate names), score, tournament,
  city, country, neutral flag; goalscorers add scorer/minute/own-goal/penalty;
  shootouts add the winner.
- **Update cadence:** community-maintained, typically updated within days of
  matches; our snapshot freshness is always displayed as "data cutoff".

## Processing

Validation drops malformed dates, exact duplicates (4 in current snapshot),
self-play rows, negative scores. Canonicalization maps era names to current
identities via the upstream table, keeps dissolved states distinct, assigns
stable slug IDs, joins shootout winners, and splits completed vs scheduled.
Quality, missingness and coverage report: `data/manifests/data_quality.json`.

## Known limitations

- Goal-scorer detail covers ~34% of scoring matches (skewed to major
  tournaments and recent decades) — player stats are lower-bound counts.
- No lineups, cards, minutes, or in-match statistics.
- Knockout scores are after extra time; shootout winners separate.
- Community-maintained: occasional upstream corrections; validation catches
  structural issues, not silent factual errors.
- Includes some non-FIFA (CONIFA) teams; they carry data-density warnings.

## Secondary sources

- **flag-icons** (MIT): SVG flags; mapping in `ml/kickoff_ml/entities/teams.py`.
- **Open-Meteo** (CC BY 4.0, non-commercial): matchday forecast display only;
  every panel shows retrieval time + attribution.
- **WC-2026 rules config** (`data/tournaments/wc2026.json`): verified
  2026-07-06 against FIFA/Wikipedia/MLSSoccer sources cited inside the file
  and in `docs/research/wc2026.md`.

## Committed test fixtures

Small deterministic slices of the real data (`data/fixtures/`): 354
core-8-team matches since 1990, WC-2022 (64 matches), edge cases (shootouts,
high scores), goalscorer slice, team registry. Regenerate:
`uv run python scripts/make_test_fixtures.py`.
