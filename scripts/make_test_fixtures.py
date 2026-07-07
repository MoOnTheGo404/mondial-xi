"""Create miniature committed test fixtures from the real processed data.

Fixtures are small, deterministic slices used by unit/integration tests so
the test suite runs without downloading anything. Regenerate with:
    uv run python scripts/make_test_fixtures.py
"""

from __future__ import annotations

import polars as pl

from kickoff_ml.config import FIXTURES_DIR, PROCESSED_DIR

FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

matches = pl.read_parquet(PROCESSED_DIR / "matches.parquet")

# 1) A focused slice: all matches between 8 well-known teams since 1990 —
#    enough history for Elo/feature tests with realistic pathways.
CORE = ["brazil", "argentina", "france", "germany", "england", "spain", "italy", "netherlands"]
slice_core = matches.filter(
    pl.col("home_id").is_in(CORE) & pl.col("away_id").is_in(CORE)
    & (pl.col("date") >= pl.date(1990, 1, 1))
)

# 2) World Cup 2022 complete tournament (64 matches) for simulator tests.
wc22 = matches.filter(
    (pl.col("tournament") == "FIFA World Cup")
    & (pl.col("date") >= pl.date(2022, 11, 1)) & (pl.col("date") <= pl.date(2022, 12, 31))
)

# 3) Edge cases: shootouts, former names, high scores.
edge = pl.concat(
    [
        matches.filter(pl.col("shootout_winner_id").is_not_null()).head(25),
        matches.filter(pl.col("home_team_name") != pl.col("home_id").str.replace_all("-", " ").str.to_titlecase()).head(0),
        matches.sort("home_score", descending=True).head(5),
    ]
)

slice_core.write_csv(FIXTURES_DIR / "matches_core8.csv")
wc22.write_csv(FIXTURES_DIR / "matches_wc2022.csv")
edge.write_csv(FIXTURES_DIR / "matches_edge.csv")

gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
gs.filter(
    pl.col("team_id").is_in(CORE) & (pl.col("date") >= pl.date(2014, 1, 1))
).write_csv(FIXTURES_DIR / "goalscorers_core8.csv")

teams = pl.read_parquet(PROCESSED_DIR / "teams.parquet")
teams.write_csv(FIXTURES_DIR / "teams.csv")

counts = {}
for p in FIXTURES_DIR.glob("*.csv"):
    with p.open() as fh:
        counts[p.name] = sum(1 for _ in fh) - 1
print("fixtures:", counts)
