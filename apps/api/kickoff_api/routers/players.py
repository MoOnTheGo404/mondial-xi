from __future__ import annotations

import polars as pl
from fastapi import APIRouter, HTTPException, Query

from kickoff_api.helpers import require_ready, team_payload
from kickoff_api.state import STATE

router = APIRouter(tags=["players"])


def _serialize(p: dict) -> dict:
    return {
        **p,
        "first_goal": str(p["first_goal"]),
        "last_goal": str(p["last_goal"]),
        "team": team_payload(p["team_id"]),
        "availability": {
            "status": "unknown",
            "source": None,
            "note": "No licensed availability feed configured",
        },
        "impact_note": (
            "Attack-side estimate from international scoring records with "
            "empirical-Bayes shrinkage — NOT an overall player-quality rating."
        ),
    }


@router.get("/players")
def list_players(
    search: str | None = None,
    team_id: str | None = None,
    recent_only: bool = True,
    limit: int = Query(50, le=200),
    offset: int = 0,
) -> dict:
    require_ready()
    if STATE.players.is_empty():
        return {"total": 0, "players": [], "note": "player registry not built"}
    df = STATE.players
    if search:
        df = df.filter(pl.col("name").str.to_lowercase().str.contains(search.lower(), literal=True))
    if team_id:
        df = df.filter(pl.col("team_id") == team_id)
    if recent_only:
        df = df.filter(pl.col("recently_active"))
    df = df.sort("goal_share_recent", descending=True)
    total = df.height
    return {
        "total": total,
        "players": [_serialize(p) for p in df.slice(offset, limit).to_dicts()],
    }


@router.get("/players/{player_id:path}")
def player_detail(player_id: str) -> dict:
    require_ready()
    if STATE.players.is_empty():
        raise HTTPException(404, "player registry not built")
    row = STATE.players.filter(pl.col("player_id") == player_id)
    if row.is_empty():
        raise HTTPException(404, f"Unknown player '{player_id}'")
    p = _serialize(row.to_dicts()[0])

    from kickoff_ml.config import PROCESSED_DIR

    gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
    goals = gs.filter(pl.col("player_id") == player_id).sort("date", descending=True)
    p["goal_log"] = [
        {
            "date": str(g["date"]),
            "match_id": g["match_id"],
            "against": g["away_id"] if g["team_id"] == g["home_id"] else g["home_id"],
            "minute": g["minute"],
            "penalty": bool(g["penalty"]),
        }
        for g in goals.head(15).iter_rows(named=True)
    ]

    # impact on upcoming team forecast, if any fixture exists
    upcoming = STATE.upcoming.filter(
        (pl.col("home_id") == p["team_id"]) | (pl.col("away_id") == p["team_id"])
    )
    if not upcoming.is_empty():
        fx = upcoming.sort("date").to_dicts()[0]
        from kickoff_ml.models.service import Scenario

        is_home = fx["home_id"] == p["team_id"]
        base = STATE.engine.predict(fx["home_id"], fx["away_id"], neutral=bool(fx["neutral"]))
        absent = STATE.engine.predict(
            fx["home_id"], fx["away_id"], neutral=bool(fx["neutral"]),
            scenario=Scenario(
                home_absences=[player_id] if is_home else [],
                away_absences=[] if is_home else [player_id],
            ),
        )
        side = "home" if is_home else "away"
        p["upcoming_fixture_impact"] = {
            "fixture_id": fx["match_id"],
            "date": str(fx["date"]),
            "opponent": fx["away_id"] if is_home else fx["home_id"],
            "team_win_prob_with": base["probabilities"][side],
            "team_win_prob_without": absent["probabilities"][side],
            "delta_pp": round(
                100 * (absent["probabilities"][side] - base["probabilities"][side]), 2
            ),
        }
    return p
