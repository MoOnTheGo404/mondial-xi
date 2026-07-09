from __future__ import annotations

import polars as pl
from fastapi import APIRouter, HTTPException, Query

from kickoff_api.helpers import head_to_head, match_row, require_ready, team_recent_matches
from kickoff_api.state import STATE

router = APIRouter(tags=["fixtures"])


def _find_fixture(fixture_id: str) -> tuple[dict, str]:
    up = STATE.upcoming.filter(pl.col("match_id") == fixture_id)
    if not up.is_empty():
        return up.to_dicts()[0], "scheduled"
    done = STATE.matches.filter(pl.col("match_id") == fixture_id)
    if not done.is_empty():
        return done.to_dicts()[0], "finished"
    raise HTTPException(404, f"Unknown fixture '{fixture_id}'")


@router.get("/fixtures")
def list_fixtures(
    status: str = Query("upcoming", pattern="^(upcoming|recent|all)$"),
    tournament: str | None = None,
    team_id: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
) -> dict:
    require_ready()
    frames = []
    if status in ("upcoming", "all"):
        frames.append(STATE.upcoming.with_columns(pl.lit("scheduled").alias("fx_status")))
    if status in ("recent", "all"):
        frames.append(
            STATE.matches.sort("date", descending=True).head(3000)
            .with_columns(pl.lit("finished").alias("fx_status"))
        )
    df = pl.concat(frames, how="diagonal")
    if tournament:
        df = df.filter(pl.col("tournament").str.contains(tournament, literal=True))
    if team_id:
        df = df.filter((pl.col("home_id") == team_id) | (pl.col("away_id") == team_id))
    if search:
        s = search.lower().replace(" ", "-")
        df = df.filter(
            pl.col("home_id").str.contains(s, literal=True)
            | pl.col("away_id").str.contains(s, literal=True)
        )
    if date_from:
        df = df.filter(pl.col("date") >= pl.lit(date_from).str.to_date())
    if date_to:
        df = df.filter(pl.col("date") <= pl.lit(date_to).str.to_date())
    df = df.sort(["date", "match_id"], descending=(status == "recent"))
    total = df.height
    rows = []
    for m in df.slice(offset, limit).iter_rows(named=True):
        r = match_row(m)
        r["status"] = m["fx_status"]
        # attach a forecast to scheduled fixtures so cards can show a prob bar
        if m["fx_status"] == "scheduled":
            pred = STATE.engine.predict(
                m["home_id"], m["away_id"], neutral=bool(m["neutral"]), importance=4
            )
            r["forecast"] = {
                "probabilities": pred["probabilities"],
                "expected_goals": pred["expected_goals"],
                "data_quality": pred["data_quality"]["grade"],
            }
        rows.append(r)
    return {
        "total": total,
        "fixtures": rows,
        "data_cutoff": STATE.engine.data_cutoff,
        "fixture_source_note": (
            "Fixtures come from the open dataset snapshot (CC0), retrieved at the "
            "time shown in /api/v1/providers — not a live feed."
        ),
    }


@router.get("/fixtures/{fixture_id}")
def fixture_detail(fixture_id: str) -> dict:
    require_ready()
    m, fx_status = _find_fixture(fixture_id)
    base = match_row(m)
    base["status"] = fx_status

    h2h = head_to_head(m["home_id"], m["away_id"])
    detail = {
        **base,
        "head_to_head": h2h,
        "home_recent": team_recent_matches(m["home_id"], 8),
        "away_recent": team_recent_matches(m["away_id"], 8),
        "venue": {
            "city": m.get("city"),
            "country": m.get("country"),
            "neutral": bool(m["neutral"]),
            "altitude_m": STATE.tournament_config.get("venues_high_altitude", {}).get(
                m.get("city")
            ),
        },
    }

    if fx_status == "scheduled":
        detail["prediction"] = STATE.engine.predict(
            m["home_id"], m["away_id"], neutral=bool(m["neutral"]), importance=4
        )
        weather = STATE.weather.forecast_for(m["city"], str(m["date"])) if m.get("city") else None
        detail["weather"] = weather
        detail["weather_note"] = (
            None if weather else
            "No forecast available (beyond horizon, geocoding miss, or weather disabled)"
        )
    else:
        # completed: show how the model scores this match retrospectively
        detail["goals"] = _goal_events(fixture_id)
        detail["retrospective"] = _retrospective(fixture_id)
    return detail


def _goal_events(fixture_id: str) -> list[dict]:
    from kickoff_ml.config import PROCESSED_DIR

    gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
    rows = gs.filter(pl.col("match_id") == fixture_id).sort("minute")
    return [
        {
            "team_id": g["team_id"], "player_id": g["player_id"], "scorer": g["scorer"],
            "minute": g["minute"], "own_goal": bool(g["own_goal"]),
            "penalty": bool(g["penalty"]),
        }
        for g in rows.iter_rows(named=True)
    ]


def _retrospective(fixture_id: str) -> dict | None:
    """Backtest score for a completed fixture IF it falls in the evaluated
    test window — clearly labeled as a backtest, never a published forecast."""
    if STATE.test_predictions.is_empty():
        return None
    row = STATE.test_predictions.filter(pl.col("match_id") == fixture_id)
    if row.is_empty():
        return None
    r = row.to_dicts()[0]
    return {
        "kind": "backtest",
        "label": "Chronological backtest (model refit protocol) — not a published forecast",
        "p_home": r["p_home"], "p_draw": r["p_draw"], "p_away": r["p_away"],
        "outcome": r["outcome"],
    }


@router.get("/fixtures/{fixture_id}/lineups")
def fixture_lineups(fixture_id: str) -> dict:
    require_ready()
    _find_fixture(fixture_id)
    return {
        "fixture_id": fixture_id,
        "home": None,
        "away": None,
        "status": "unavailable",
        "reason": (
            "Confirmed lineups require a licensed provider (football-data.org "
            "paid tier). The open dataset does not include lineups."
        ),
    }


@router.get("/fixtures/{fixture_id}/availability")
def fixture_availability(fixture_id: str) -> dict:
    require_ready()
    m, _ = _find_fixture(fixture_id)
    out = {}
    for side in ("home", "away"):
        tid = m[f"{side}_id"]
        players = []
        if not STATE.players.is_empty():
            players = (
                STATE.players.filter(
                    (pl.col("team_id") == tid) & pl.col("recently_active")
                )
                .sort("attack_impact_recent", descending=True)
                .head(15)
                .select(["player_id", "name", "attack_impact_recent"])
                .to_dicts()
            )
        out[side] = [
            {**p, "status": "unknown", "source": None, "official": False} for p in players
        ]
    return {
        "fixture_id": fixture_id,
        "availability": out,
        "note": (
            "No licensed injury/suspension feed is configured; every status is "
            "'unknown'. Use Match Lab to explore user-assumed scenarios."
        ),
    }


@router.get("/fixtures/{fixture_id}/prediction")
def fixture_prediction(fixture_id: str) -> dict:
    require_ready()
    m, fx_status = _find_fixture(fixture_id)
    if fx_status == "finished":
        retro = _retrospective(fixture_id)
        if retro:
            return {"fixture_id": fixture_id, "kind": "backtest", "backtest": retro}
        raise HTTPException(
            409, "Fixture already completed and outside the evaluated test window"
        )
    from kickoff_api.snapshots import list_snapshots

    snaps = [s for s in list_snapshots(500) if s["fixture_id"] == fixture_id]
    return {
        "fixture_id": fixture_id,
        "kind": "prospective",
        "prediction": STATE.engine.predict(
            m["home_id"], m["away_id"], neutral=bool(m["neutral"]), importance=4
        ),
        "snapshots": snaps,
    }
