from __future__ import annotations

from typing import Any

import polars as pl
from fastapi import HTTPException

from kickoff_api.state import STATE


def require_ready() -> None:
    if not STATE.ready:
        raise HTTPException(
            status_code=503,
            detail=STATE.load_error or "Artifacts not loaded. Run `make data && make train`.",
        )


def team_payload(team_id: str) -> dict[str, Any]:
    t = STATE.team_index.get(team_id)
    b = STATE.engine.builder
    known = STATE.engine.team_known(team_id)
    return {
        "team_id": team_id,
        "name": t["name"] if t else team_id.replace("-", " ").title(),
        "flag_code": t["flag_code"] if t else None,
        "confederation": t["confederation"] if t else "OTHER",
        "is_historical": bool(t["is_historical"]) if t else False,
        "elo": round(b.elo.rating(team_id), 1) if known else None,
        "matches_played": b.elo.matches_played(team_id),
    }


def match_row(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": m["match_id"],
        "date": str(m["date"]),
        "home": team_payload(m["home_id"]),
        "away": team_payload(m["away_id"]),
        "home_score": m.get("home_score"),
        "away_score": m.get("away_score"),
        "tournament": m["tournament"],
        "tier": m.get("tier"),
        "city": m.get("city"),
        "country": m.get("country"),
        "neutral": bool(m["neutral"]),
        "shootout_winner_id": m.get("shootout_winner_id"),
        "home_team_name_then": m.get("home_team_name"),
        "away_team_name_then": m.get("away_team_name"),
    }


def team_recent_matches(team_id: str, limit: int = 10) -> list[dict]:
    df = STATE.matches.filter(
        (pl.col("home_id") == team_id) | (pl.col("away_id") == team_id)
    ).sort("date", descending=True).head(limit)
    return [match_row(m) for m in df.iter_rows(named=True)]


def head_to_head(a: str, b: str, limit: int = 20) -> dict:
    df = STATE.matches.filter(
        ((pl.col("home_id") == a) & (pl.col("away_id") == b))
        | ((pl.col("home_id") == b) & (pl.col("away_id") == a))
    ).sort("date", descending=True)
    wins_a = wins_b = draws = 0
    for m in df.iter_rows(named=True):
        hs, as_ = m["home_score"], m["away_score"]
        if hs == as_:
            draws += 1
        elif (hs > as_) == (m["home_id"] == a):
            wins_a += 1
        else:
            wins_b += 1
    return {
        "total": df.height,
        "wins_a": wins_a,
        "wins_b": wins_b,
        "draws": draws,
        "recent": [match_row(m) for m in df.head(limit).iter_rows(named=True)],
    }
