from __future__ import annotations

from fastapi import APIRouter, HTTPException

from kickoff_api.helpers import require_ready, team_payload
from kickoff_api.state import STATE

router = APIRouter(tags=["tournaments"])


@router.get("/tournaments")
def list_tournaments() -> dict:
    require_ready()
    cfg = STATE.tournament_config
    from kickoff_ml.simulation.wc2030 import config_2030

    c30 = config_2030()
    return {
        "tournaments": [
            {
                "tournament_id": cfg["tournament_id"],
                "name": cfg["name"],
                "config_version": cfg["config_version"],
                "verified_on": cfg["verified_on"],
                "teams": cfg["format"]["teams"],
                "status": "knockout_in_progress_at_data_cutoff",
            },
            {
                "tournament_id": c30["tournament_id"],
                "name": c30["name"],
                "config_version": c30["config_version"],
                "verified_on": c30["verified_on"],
                "teams": c30["verified_facts"]["teams"],
                "status": "outlook_simulation_only",
            },
        ]
    }


@router.get("/tournaments/{tournament_id}")
def tournament_detail(tournament_id: str) -> dict:
    require_ready()
    if tournament_id != "wc2026":
        raise HTTPException(404, f"Unknown tournament '{tournament_id}'")
    from kickoff_ml.simulation.summary import tournament_summary

    summary = tournament_summary(STATE.matches, STATE.upcoming)
    for rows in summary["groups"].values():
        for r in rows:
            r["team"] = team_payload(r["team_id"])
    for rnd in summary["bracket"]:
        for m in rnd["matches"]:
            m["home"] = team_payload(m["home_id"])
            m["away"] = team_payload(m["away_id"])
    summary["data_cutoff"] = STATE.engine.data_cutoff
    return summary
