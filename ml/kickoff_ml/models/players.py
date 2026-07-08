"""Player registry and attack-share estimates from CC0 goalscorer data.

Honesty contract (see docs/player-model.md):
- The open dataset records only *goalscorers* — not squads, lineups, minutes
  or defensive actions — and scorer detail exists for only part of each
  team's matches. Goal counts are therefore **recorded** counts, not career
  totals, and every player carries an explicit coverage figure.
- Scenario impact uses each player's SHARE of the team's recorded goals in a
  recent window (shares are coverage-robust: numerator and denominator come
  from the same covered matches), shrunk with an empirical-Bayes prior.
- Same-named players of one country collapse into one ID (no birthdates in
  the source); long-gap careers are flagged `possible_name_collision`.
- "Recent scorers" is NOT a squad list; availability defaults to "unknown".
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import polars as pl

from kickoff_ml.config import PROCESSED_DIR

PRIOR_MATCHES = 25.0        # pseudo-matches of zero-goal prior (xG/match display)
SHARE_PRIOR_GOALS = 8.0     # pseudo team-goals prior for the share estimate
SHARE_WINDOW_YEARS = 4      # trailing window for "recent attacking share"
RECENT_WINDOW_DAYS = 730    # "recently active" horizon
MAX_IMPACT = 0.9            # cap on xG/match attributed to one player
COLLISION_GAP_YEARS = 10    # goal gap that suggests two same-named players


def build_player_registry() -> pl.DataFrame:
    """Aggregate goalscorer events into per-player attack profiles."""
    gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
    matches = pl.read_parquet(PROCESSED_DIR / "matches.parquet")
    cutoff: date = matches["date"].max()  # type: ignore[assignment]
    share_start = cutoff - timedelta(days=365 * SHARE_WINDOW_YEARS)

    goals = gs.filter(~pl.col("own_goal"))

    # --- team-level aggregates ------------------------------------------
    team_matches = pl.concat(
        [
            matches.select(pl.col("home_id").alias("team_id"), "date", "match_id"),
            matches.select(pl.col("away_id").alias("team_id"), "date", "match_id"),
        ]
    )
    tm_by_team: dict[str, pl.DataFrame] = {}
    for key, g in team_matches.group_by("team_id"):
        tm_by_team[key[0]] = g.sort("date")

    # recorded team goals + covered matches in the share window, per team
    recent_goals = goals.filter(pl.col("date") >= share_start)
    team_goals_recent: dict[str, int] = {
        k[0]: g.height for k, g in recent_goals.group_by("team_id")
    }
    covered_matches: dict[str, set] = {
        k[0]: set(g["match_id"].to_list()) for k, g in goals.group_by("team_id")
    }

    # --- per-player aggregation ------------------------------------------
    agg = goals.group_by("player_id").agg(
        pl.col("scorer").first().alias("name"),
        pl.col("team_id").first().alias("team_id"),
        pl.len().alias("goals"),
        pl.col("penalty").sum().alias("penalties"),
        pl.col("date").min().alias("first_goal"),
        pl.col("date").max().alias("last_goal"),
        pl.col("match_id").n_unique().alias("matches_scored_in"),
        pl.col("date").sort().alias("goal_dates"),
        (pl.col("date") >= share_start).sum().alias("recent_goals"),
    )

    rows = []
    for r in agg.iter_rows(named=True):
        tdf = tm_by_team.get(r["team_id"])
        if tdf is None:
            continue
        window = tdf.filter(
            (pl.col("date") >= r["first_goal"]) & (pl.col("date") <= r["last_goal"])
        )
        n_team = max(window.height, r["matches_scored_in"])

        # coverage: share of the team's matches in this player's window that
        # have ANY recorded scorer detail — contextualizes the goal count
        window_ids = set(window["match_id"].to_list())
        covered = len(window_ids & covered_matches.get(r["team_id"], set()))
        coverage_pct = round(100 * covered / n_team, 1) if n_team else 0.0

        # name-collision heuristic: a long silent gap inside the career
        dates = r["goal_dates"]
        max_gap_days = max(
            ((b - a).days for a, b in zip(dates[:-1], dates[1:], strict=True)),
            default=0,
        )
        collision = max_gap_days > COLLISION_GAP_YEARS * 365

        raw_rate = r["goals"] / n_team if n_team else 0.0
        shrunk = min(r["goals"] / (n_team + PRIOR_MATCHES), MAX_IMPACT)
        days_since = (cutoff - r["last_goal"]).days
        recency = max(0.0, 1.0 - days_since / RECENT_WINDOW_DAYS)

        # coverage-robust attacking share of the team's recent recorded goals
        g_team = team_goals_recent.get(r["team_id"], 0)
        goal_share = r["recent_goals"] / (g_team + SHARE_PRIOR_GOALS) if g_team else 0.0

        rows.append(
            {
                **{k: r[k] for k in ("player_id", "name", "team_id", "goals", "penalties",
                                     "first_goal", "last_goal", "matches_scored_in")},
                "team_matches_active": n_team,
                "coverage_pct": coverage_pct,
                "possible_name_collision": collision,
                "raw_goals_per_match": round(raw_rate, 4),
                "attack_impact": round(shrunk, 4),           # shrunken xG/match (display)
                "attack_impact_recent": round(shrunk * recency, 4),
                "recent_goals": r["recent_goals"],
                "team_recent_goals": g_team,
                "goal_share_recent": round(goal_share, 4),   # scenario mechanism input
                "recently_active": days_since <= RECENT_WINDOW_DAYS,
                "shrinkage_weight": round(n_team / (n_team + PRIOR_MATCHES), 3),
            }
        )
    df = pl.DataFrame(rows).sort("goal_share_recent", descending=True)
    df.write_parquet(PROCESSED_DIR / "players.parquet")
    summary = {
        "players": df.height,
        "recently_active": int(df["recently_active"].sum()),
        "flagged_possible_collisions": int(df["possible_name_collision"].sum()),
        "as_of": str(cutoff),
        "method": (
            f"xG/match: EB shrinkage prior={PRIOR_MATCHES:.0f} matches, cap {MAX_IMPACT}; "
            f"scenario share: recorded-goal share over trailing {SHARE_WINDOW_YEARS}y, "
            f"prior={SHARE_PRIOR_GOALS:.0f} pseudo team-goals"
        ),
    }
    (PROCESSED_DIR / "players_summary.json").write_text(json.dumps(summary, indent=2))
    return df


if __name__ == "__main__":
    df = build_player_registry()
    print(df.head(10))
