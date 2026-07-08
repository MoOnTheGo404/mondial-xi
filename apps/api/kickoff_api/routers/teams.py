from __future__ import annotations

import polars as pl
from fastapi import APIRouter, HTTPException, Query

from kickoff_api.helpers import match_row, require_ready, team_payload, team_recent_matches
from kickoff_api.state import STATE

router = APIRouter(tags=["teams"])


@router.get("/teams")
def list_teams(
    search: str | None = None,
    confederation: str | None = None,
    active_only: bool = True,
    limit: int = Query(400, le=500),
) -> dict:
    require_ready()
    df = STATE.teams
    if search:
        df = df.filter(pl.col("name").str.to_lowercase().str.contains(search.lower(), literal=True))
    if confederation:
        df = df.filter(pl.col("confederation") == confederation.upper())
    rows = []
    for t in df.iter_rows(named=True):
        p = team_payload(t["team_id"])
        if active_only and p["matches_played"] < 10:
            continue
        rows.append(p)
    rows.sort(key=lambda r: -(r["elo"] or 0))
    return {"teams": rows[:limit], "total": len(rows)}


@router.get("/teams/{team_id}")
def team_detail(team_id: str) -> dict:
    require_ready()
    if team_id not in STATE.team_index:
        raise HTTPException(404, f"Unknown team '{team_id}'")
    p = team_payload(team_id)

    df = STATE.matches
    home = df.filter(pl.col("home_id") == team_id)
    away = df.filter(pl.col("away_id") == team_id)

    def rec(sub: pl.DataFrame, is_home: bool) -> dict:
        w = sub.filter(
            pl.col("home_score") > pl.col("away_score") if is_home
            else pl.col("away_score") > pl.col("home_score")
        ).height
        losses = sub.filter(
            pl.col("home_score") < pl.col("away_score") if is_home
            else pl.col("away_score") < pl.col("home_score")
        ).height
        d = sub.height - w - losses
        return {"played": sub.height, "wins": w, "draws": d, "losses": losses}

    home_r = rec(home.filter(~pl.col("neutral")), True)
    away_r = rec(away.filter(~pl.col("neutral")), False)
    neutral_df_h = home.filter(pl.col("neutral"))
    neutral_df_a = away.filter(pl.col("neutral"))
    nh, na = rec(neutral_df_h, True), rec(neutral_df_a, False)
    neutral_r = {k: nh[k] + na[k] for k in nh}

    # attack/defense from builder state (rolling last-10)
    st = STATE.engine.builder._state(team_id)
    gf, ga = st.rolling_goals()

    upcoming = [
        match_row(m)
        for m in STATE.upcoming.filter(
            (pl.col("home_id") == team_id) | (pl.col("away_id") == team_id)
        ).iter_rows(named=True)
    ]

    squad = []
    if not STATE.players.is_empty():
        squad = (
            STATE.players.filter(
                (pl.col("team_id") == team_id) & pl.col("recently_active")
            )
            .sort("scenario_share", descending=True)
            .head(20)
            .to_dicts()
        )
        for s in squad:
            s["first_goal"] = str(s["first_goal"])
            s["last_goal"] = str(s["last_goal"])

    wc = STATE.matches.filter(
        ((pl.col("home_id") == team_id) | (pl.col("away_id") == team_id))
        & (pl.col("tournament") == "FIFA World Cup")
    )
    wc_years = sorted({d.year for d in wc["date"].to_list()})

    return {
        **p,
        "form_last10": round(st.form_score(), 3),
        "rolling_goals_for": round(gf, 2),
        "rolling_goals_against": round(ga, 2),
        "record": {"home": home_r, "away": away_r, "neutral": neutral_r},
        "recent_matches": team_recent_matches(team_id, 10),
        "upcoming_fixtures": upcoming,
        "known_attacking_contributors": squad,
        "squad_note": (
            "Derived from CC0 goalscorer records — attack-side contributors only, "
            "NOT a full squad list. No licensed squad/lineup feed is configured."
        ),
        "world_cup_editions": wc_years,
        "data_density_warning": (
            None if p["matches_played"] >= 100
            else f"Only {p['matches_played']} recorded matches — estimates are heavily shrunk"
        ),
    }


@router.get("/teams/{team_id}/matches")
def team_matches(
    team_id: str,
    competitions: str = Query("all", pattern="^(all|competitive|friendly)$"),
    venue: str = Query("all", pattern="^(all|home|away|neutral)$"),
    since: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
) -> dict:
    require_ready()
    if team_id not in STATE.team_index:
        raise HTTPException(404, f"Unknown team '{team_id}'")
    df = STATE.matches.filter(
        (pl.col("home_id") == team_id) | (pl.col("away_id") == team_id)
    )
    if competitions == "competitive":
        df = df.filter(pl.col("tier") != "friendly")
    elif competitions == "friendly":
        df = df.filter(pl.col("tier") == "friendly")
    if venue == "home":
        df = df.filter((pl.col("home_id") == team_id) & ~pl.col("neutral"))
    elif venue == "away":
        df = df.filter((pl.col("away_id") == team_id) & ~pl.col("neutral"))
    elif venue == "neutral":
        df = df.filter(pl.col("neutral"))
    if since:
        df = df.filter(pl.col("date") >= pl.lit(since).str.to_date())
    df = df.sort("date", descending=True)
    total = df.height
    page = df.slice(offset, limit)
    return {
        "total": total,
        "matches": [match_row(m) for m in page.iter_rows(named=True)],
    }


@router.get("/teams/{team_id}/squad")
def team_squad(team_id: str) -> dict:
    require_ready()
    if team_id not in STATE.team_index:
        raise HTTPException(404, f"Unknown team '{team_id}'")
    players = []
    if not STATE.players.is_empty():
        players = (
            STATE.players.filter(pl.col("team_id") == team_id)
            .sort("scenario_share", descending=True)
            .head(40)
            .to_dicts()
        )
        for s in players:
            s["first_goal"] = str(s["first_goal"])
            s["last_goal"] = str(s["last_goal"])
            s["availability"] = "unknown"
    return {
        "team_id": team_id,
        "players": players,
        "coverage_note": (
            "Attack-side contributors reconstructed from goalscorer records (CC0). "
            "Full squads, positions, caps and defensive players are unavailable "
            "without a licensed provider; availability is 'unknown' by default."
        ),
    }


@router.get("/teams/{team_id}/elo-history")
def team_elo_history(team_id: str, since: str = "1950-01-01") -> dict:
    require_ready()
    df = STATE.elo_history.filter(pl.col("date") >= pl.lit(since).str.to_date())
    h = df.filter(pl.col("home_id") == team_id).select(
        "date", pl.col("home_elo").alias("elo")
    )
    a = df.filter(pl.col("away_id") == team_id).select(
        "date", pl.col("away_elo").alias("elo")
    )
    series = pl.concat([h, a]).sort("date")
    # thin to ~400 points for charting
    step = max(1, series.height // 400)
    pts = [
        {"date": str(r["date"]), "elo": round(r["elo"], 1)}
        for i, r in enumerate(series.iter_rows(named=True))
        if i % step == 0 or i == series.height - 1
    ]
    return {"team_id": team_id, "points": pts}
