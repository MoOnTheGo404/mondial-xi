"""Player registry: recorded goal events (CC0) + career enrichment (Wikidata
CC0) + goal-involvement shares for scenario weighting.

Layers of honesty (docs/player-model.md):
- RECORDED goals come from the partial-coverage CC0 goalscorer log and are
  labeled as floors, with a per-player coverage figure.
- CAREER caps/goals come from Wikidata (CC0) where a player matches
  unambiguously and passes sanity checks; every value carries its source and
  retrieval date. Same-name players are disambiguated by date of birth or
  left unenriched.
- ASSISTS: no legally usable international-assist source exists. The
  contribution model is assists-ready (goals + ASSIST_WEIGHT x assists) and
  the field stays null until a licensed provider supplies it — never
  invented.
- The scenario weight `scenario_share` blends the recent recorded
  goal-involvement share (coverage-robust) with a career-rate share
  (career goals/cap over the team's TRUE goals/match — both true
  quantities), weighted by how much recent evidence exists.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import polars as pl

from kickoff_ml.config import MANIFEST_DIR, PROCESSED_DIR, RAW_DIR

PRIOR_MATCHES = 25.0        # pseudo-matches of zero-goal prior (xG/match display)
SHARE_PRIOR_GOALS = 8.0     # pseudo team-goals prior for the recent share
SHARE_WINDOW_YEARS = 4      # trailing window for "recent attacking share"
RECENT_WINDOW_DAYS = 730    # "recently active" horizon
MAX_IMPACT = 0.9            # cap on xG/match attributed to one player
COLLISION_GAP_YEARS = 10    # goal gap that suggests two same-named players
ASSIST_WEIGHT = 0.5         # weight of an assist vs a goal in contributions
CAREER_BLEND_K = 3.0        # recent goals needed to trust recent share ~50%
MAX_PLAYER_SHARE = 0.5      # one player never exceeds half a team's output


def _load_wikidata() -> tuple[dict[tuple[str, str], list[dict]], str | None]:
    """(team_id, player_slug) -> candidate career rows; plus retrieval date."""
    path = RAW_DIR / "wikidata_players.json"
    if not path.exists():
        return {}, None
    data = json.loads(path.read_text())
    retrieved = None
    manifest = MANIFEST_DIR / "wikidata_players.json"
    if manifest.exists():
        retrieved = json.loads(manifest.read_text()).get("retrieved_at", "")[:10]
    index: dict[tuple[str, str], list[dict]] = {}
    for row in data.get("players", []):
        index.setdefault((row["team_id"], row["player_slug"]), []).append(row)
    return index, retrieved


def _match_career(
    candidates: list[dict], first_goal: date, last_goal: date, recorded_goals: int
) -> tuple[dict | None, bool]:
    """Pick the career row for this recorded player. Returns (row, ambiguous)."""

    def dob_ok(row: dict) -> bool:
        if not row.get("dob"):
            return True
        try:
            born = date.fromisoformat(row["dob"])
        except ValueError:
            return True
        age_last = (last_goal - born).days / 365.25
        age_first = (first_goal - born).days / 365.25
        return 14.0 <= age_first <= 46.0 and 15.0 <= age_last <= 47.0

    viable = [
        c for c in candidates
        if dob_ok(c) and (c.get("goals") is None or c["goals"] + 2 >= recorded_goals)
    ]
    if len(viable) == 1:
        return viable[0], False
    if len(viable) > 1:
        # same name, same team, both age-plausible -> refuse to guess
        return None, True
    return None, len(candidates) > 1


def build_player_registry() -> pl.DataFrame:
    """Aggregate goalscorer events into per-player attack profiles."""
    gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
    matches = pl.read_parquet(PROCESSED_DIR / "matches.parquet")
    cutoff: date = matches["date"].max()  # type: ignore[assignment]
    share_start = cutoff - timedelta(days=365 * SHARE_WINDOW_YEARS)
    career_index, career_retrieved = _load_wikidata()

    goals = gs.filter(~pl.col("own_goal"))

    # --- team-level aggregates ------------------------------------------
    team_matches = pl.concat(
        [
            matches.select(
                pl.col("home_id").alias("team_id"), "date", "match_id",
                pl.col("home_score").alias("scored"),
            ),
            matches.select(
                pl.col("away_id").alias("team_id"), "date", "match_id",
                pl.col("away_score").alias("scored"),
            ),
        ]
    )
    tm_by_team: dict[str, pl.DataFrame] = {}
    for key, g in team_matches.group_by("team_id"):
        tm_by_team[key[0]] = g.sort("date")

    recent_goal_events = goals.filter(pl.col("date") >= share_start)
    team_goals_recorded: dict[str, int] = {
        k[0]: g.height for k, g in recent_goal_events.group_by("team_id")
    }
    # TRUE goals/match from scorelines (not the partial goalscorer log)
    recent_team = team_matches.filter(pl.col("date") >= share_start)
    team_true_rate: dict[str, float] = {}
    for key, g in recent_team.group_by("team_id"):
        if g.height >= 5:
            team_true_rate[key[0]] = float(g["scored"].sum()) / g.height
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
        pl.col("player_slug").first().alias("player_slug"),
    )

    rows = []
    enriched = ambiguous_n = 0
    for r in agg.iter_rows(named=True):
        tdf = tm_by_team.get(r["team_id"])
        if tdf is None:
            continue
        window = tdf.filter(
            (pl.col("date") >= r["first_goal"]) & (pl.col("date") <= r["last_goal"])
        )
        n_team = max(window.height, r["matches_scored_in"])

        window_ids = set(window["match_id"].to_list())
        covered = len(window_ids & covered_matches.get(r["team_id"], set()))
        coverage_pct = round(100 * covered / n_team, 1) if n_team else 0.0

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

        # --- career enrichment (Wikidata CC0) ----------------------------
        career, amb = _match_career(
            career_index.get((r["team_id"], r["player_slug"]), []),
            r["first_goal"], r["last_goal"], r["goals"],
        )
        career_caps = career.get("caps") if career else None
        career_goals = career.get("goals") if career else None
        dob = career.get("dob") if career else None
        if career:
            enriched += 1
        if amb:
            ambiguous_n += 1
        gpc = (
            career_goals / career_caps
            if career_goals is not None and career_caps
            else None
        )

        # --- goal-involvement shares --------------------------------------
        recent_assists: int | None = None  # no licensed source — stays null
        contribution = r["recent_goals"] + ASSIST_WEIGHT * (recent_assists or 0)
        g_team = team_goals_recorded.get(r["team_id"], 0)
        share_recent = contribution / (g_team + SHARE_PRIOR_GOALS) if g_team else 0.0

        true_rate = team_true_rate.get(r["team_id"])
        share_career = (
            min(gpc / true_rate, 0.6) if gpc is not None and true_rate else None
        )
        lam = r["recent_goals"] / (r["recent_goals"] + CAREER_BLEND_K)
        if share_career is not None:
            scenario_share = lam * share_recent + (1 - lam) * share_career * recency
        else:
            scenario_share = share_recent
        scenario_share = min(scenario_share, MAX_PLAYER_SHARE)

        rows.append(
            {
                **{k: r[k] for k in ("player_id", "name", "team_id", "goals", "penalties",
                                     "first_goal", "last_goal", "matches_scored_in")},
                "team_matches_active": n_team,
                "coverage_pct": coverage_pct,
                "possible_name_collision": collision and career is None,
                "raw_goals_per_match": round(raw_rate, 4),
                "attack_impact": round(shrunk, 4),
                "attack_impact_recent": round(shrunk * recency, 4),
                "recent_goals": r["recent_goals"],
                "recent_assists": recent_assists,
                "team_recent_goals": g_team,
                "goal_share_recent": round(share_recent, 4),
                "career_caps": career_caps,
                "career_goals": career_goals,
                "career_goals_per_cap": round(gpc, 4) if gpc is not None else None,
                "career_source": "wikidata_cc0" if career else None,
                "career_retrieved": career_retrieved if career else None,
                "career_ambiguous": amb,
                "dob": dob,
                "scenario_share": round(scenario_share, 4),
                "recently_active": days_since <= RECENT_WINDOW_DAYS,
                "shrinkage_weight": round(n_team / (n_team + PRIOR_MATCHES), 3),
            }
        )
    df = pl.DataFrame(rows).sort("scenario_share", descending=True)
    df.write_parquet(PROCESSED_DIR / "players.parquet")
    summary = {
        "players": df.height,
        "recently_active": int(df["recently_active"].sum()),
        "career_enriched": enriched,
        "career_ambiguous_skipped": ambiguous_n,
        "flagged_possible_collisions": int(df["possible_name_collision"].sum()),
        "as_of": str(cutoff),
        "method": (
            f"scenario share = blend(recent recorded involvement share "
            f"[prior {SHARE_PRIOR_GOALS:.0f}], career goals/cap vs team true rate) "
            f"weighted by recent evidence (k={CAREER_BLEND_K:.0f}); assists weight "
            f"{ASSIST_WEIGHT} (no licensed source yet — null); cap {MAX_PLAYER_SHARE}"
        ),
    }
    (PROCESSED_DIR / "players_summary.json").write_text(json.dumps(summary, indent=2))
    return df


if __name__ == "__main__":
    df = build_player_registry()
    print(df.head(10))
