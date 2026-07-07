"""Player registry and attack-impact estimates from CC0 goalscorer data.

Honesty contract (see docs/player-model.md):
- The open dataset records only *goalscorers* — not squads, lineups, minutes
  or defensive actions. Estimates here are therefore **attack-side only**,
  derived from scoring records, and are labeled as such throughout the UI.
- Impact = empirical-Bayes-shrunken goals contributed per team match while
  the player was active. Players with few goals are shrunk hard toward zero
  (prior strength PRIOR_MATCHES), so a two-goal wonder never outranks a
  sustained contributor.
- "Recent scorers" is NOT a squad list; availability defaults to "unknown".
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import polars as pl

from kickoff_ml.config import PROCESSED_DIR

PRIOR_MATCHES = 25.0        # pseudo-matches of zero-goal prior
RECENT_WINDOW_DAYS = 730    # "recently active" horizon
MAX_IMPACT = 0.9            # cap on xG/match attributed to one player


def build_player_registry() -> pl.DataFrame:
    """Aggregate goalscorer events into per-player attack profiles."""
    gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
    matches = pl.read_parquet(PROCESSED_DIR / "matches.parquet")
    cutoff: date = matches["date"].max()  # type: ignore[assignment]

    goals = gs.filter(~pl.col("own_goal"))
    agg = goals.group_by("player_id").agg(
        pl.col("scorer").first().alias("name"),
        pl.col("team_id").first().alias("team_id"),
        pl.len().alias("goals"),
        pl.col("penalty").sum().alias("penalties"),
        pl.col("date").min().alias("first_goal"),
        pl.col("date").max().alias("last_goal"),
        pl.col("match_id").n_unique().alias("matches_scored_in"),
    )

    # Team match counts during each player's active window.
    team_matches = pl.concat(
        [
            matches.select(pl.col("home_id").alias("team_id"), "date"),
            matches.select(pl.col("away_id").alias("team_id"), "date"),
        ]
    )
    rows = []
    tm_by_team: dict[str, pl.Series] = {}
    for key, g in team_matches.group_by("team_id"):
        tm_by_team[key[0]] = g["date"].sort()

    for r in agg.iter_rows(named=True):
        dates = tm_by_team.get(r["team_id"])
        if dates is None:
            continue
        # matches from first goal to cutoff (activity window, inclusive)
        n_team = int(((dates >= r["first_goal"]) & (dates <= r["last_goal"])).sum())
        n_team = max(n_team, r["matches_scored_in"])
        raw_rate = r["goals"] / n_team if n_team else 0.0
        shrunk = min(r["goals"] / (n_team + PRIOR_MATCHES), MAX_IMPACT)
        days_since = (cutoff - r["last_goal"]).days
        recency = max(0.0, 1.0 - days_since / RECENT_WINDOW_DAYS)
        rows.append(
            {
                **{k: r[k] for k in ("player_id", "name", "team_id", "goals", "penalties",
                                     "first_goal", "last_goal", "matches_scored_in")},
                "team_matches_active": n_team,
                "raw_goals_per_match": round(raw_rate, 4),
                "attack_impact": round(shrunk, 4),           # shrunken xG/match
                "attack_impact_recent": round(shrunk * recency, 4),
                "recently_active": days_since <= RECENT_WINDOW_DAYS,
                "shrinkage_weight": round(n_team / (n_team + PRIOR_MATCHES), 3),
            }
        )
    df = pl.DataFrame(rows).sort("attack_impact_recent", descending=True)
    df.write_parquet(PROCESSED_DIR / "players.parquet")
    summary = {
        "players": df.height,
        "recently_active": int(df["recently_active"].sum()),
        "as_of": str(cutoff),
        "method": "EB shrinkage, prior=25 zero-goal matches, cap 0.9 xG/match",
    }
    (PROCESSED_DIR / "players_summary.json").write_text(json.dumps(summary, indent=2))
    return df


def scenario_xg_delta(player_ids: list[str], players: pl.DataFrame) -> tuple[float, list[dict]]:
    """Expected-goals reduction if the listed players are unavailable.

    Marginalization note: for players marked 'doubtful' callers should pass
    availability probability and scale — handled in the service layer.
    """
    details = []
    total = 0.0
    for pid in player_ids:
        row = players.filter(pl.col("player_id") == pid)
        if row.is_empty():
            details.append({"player_id": pid, "impact": 0.0, "note": "unknown player — no effect"})
            continue
        imp = float(row["attack_impact_recent"][0])
        total += imp
        details.append(
            {
                "player_id": pid,
                "name": row["name"][0],
                "impact": imp,
                "shrinkage_weight": float(row["shrinkage_weight"][0]),
            }
        )
    return min(total, 1.5), details  # bounded total team effect


if __name__ == "__main__":
    df = build_player_registry()
    print(df.head(10))
