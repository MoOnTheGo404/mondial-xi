from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from kickoff_api.state import STATE

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok" if STATE.ready else "degraded", "ready": STATE.ready}


@router.get("/system/status")
def system_status() -> dict:
    if not STATE.ready:
        return {"ready": False, "error": STATE.load_error}
    return {
        "ready": True,
        "model_version": STATE.engine.model_version,
        "champion_model": STATE.engine.champion_name,
        "data_cutoff": STATE.engine.data_cutoff,
        "completed_matches": STATE.matches.height,
        "upcoming_fixtures": STATE.upcoming.height,
        "teams": STATE.teams.height,
        "players": STATE.players.height,
        "data_quality": STATE.data_quality,
    }


@router.get("/providers")
def providers() -> dict:
    if not STATE.ready:
        return {"providers": []}
    computed = {
        "name": "kickoff-atlas-models",
        "kind": "computed",
        "available": True,
        "capabilities": [
            "elo_ratings", "outcome_forecasts", "score_matrices",
            "tournament_simulation", "player_attack_impact",
        ],
        "license_note": "Derived from CC0 data; models trained in-repo",
        "last_sync": STATE.engine.data_cutoff,
        "detail": f"model {STATE.engine.model_version}",
        "attribution": None,
    }
    return {
        "providers": [
            asdict(STATE.local_provider.status()),
            asdict(STATE.football_data.status()),
            asdict(STATE.weather.status()),
            computed,
        ],
        "unavailable_capabilities": [
            {
                "capability": "confirmed_lineups",
                "reason": "No legally usable free source; football-data.org lineups require a paid plan",
            },
            {
                "capability": "injury_feeds",
                "reason": "No provider with publication rights on a free tier; availability defaults to 'unknown'",
            },
            {
                "capability": "player_photos",
                "reason": "Licensing not verifiable; initials avatars used instead",
            },
            {
                "capability": "international_assists",
                "reason": (
                    "No legally usable source (Wikidata lacks them; Opta/FBref and "
                    "API-Football forbid republication). Contribution model is "
                    "assists-ready at weight 0.5; field stays null until licensed."
                ),
            },
        ],
    }
