from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from kickoff_api.helpers import require_ready, team_payload
from kickoff_api.settings import settings
from kickoff_api.state import STATE

router = APIRouter(tags=["simulations"])


class LockedMatch(BaseModel):
    round: str = Field(pattern="^(R32|R16|QF|SF|F)$")
    team_a: str
    team_b: str
    winner: str


class TournamentSimRequest(BaseModel):
    tournament_id: str = "wc2026"
    n_sims: int = Field(10_000, ge=100)
    seed: int = Field(42, ge=0, le=2**31 - 1)
    from_scratch: bool = False
    locked: list[LockedMatch] = Field(default_factory=list, max_length=32)
    blocks: int = Field(16, ge=4, le=32)  # wc2030 only: qualification realizations


@router.post("/simulations/tournament")
def simulate_tournament(req: TournamentSimRequest) -> dict:
    require_ready()
    if req.tournament_id == "wc2030":
        return _simulate_outlook_2030(req)
    if req.tournament_id != "wc2026":
        raise HTTPException(404, f"Unknown tournament '{req.tournament_id}'")
    if req.n_sims > settings.max_simulations:
        raise HTTPException(
            422, f"n_sims capped at {settings.max_simulations} for interactive use"
        )
    locked: dict[str, dict[frozenset[str], str]] = {}
    for lk in req.locked:
        if lk.winner not in (lk.team_a, lk.team_b):
            raise HTTPException(422, f"winner must be one of the two teams: {lk.winner}")
        locked.setdefault(lk.round, {})[frozenset((lk.team_a, lk.team_b))] = lk.winner

    from kickoff_ml.simulation.wc2026_state import simulate_wc2026

    t0 = time.perf_counter()
    result = simulate_wc2026(
        STATE.engine, STATE.matches, n_sims=req.n_sims, seed=req.seed,
        locked_knockout=locked or None, from_scratch=req.from_scratch,
    )
    elapsed_ms = round(1000 * (time.perf_counter() - t0), 1)
    for row in result["teams"]:
        row["team"] = team_payload(row["team_id"])
        row["reach"] = {k: round(float(v), 4) for k, v in row["reach"].items()}
    result["elapsed_ms"] = elapsed_ms
    result["model_version"] = STATE.engine.model_version
    result["data_cutoff"] = STATE.engine.data_cutoff
    result["locked_applied"] = [lk.model_dump() for lk in req.locked]
    return result


def _simulate_outlook_2030(req: TournamentSimRequest) -> dict:
    """WC-2030 outlook: qualification + draw + finals under documented
    assumptions. Heavier than the 2026 path -> tighter sim cap."""
    if req.n_sims > 4000:
        raise HTTPException(422, "n_sims capped at 4000 for the 2030 outlook")
    from kickoff_ml.simulation.wc2030 import simulate_wc2030

    t0 = time.perf_counter()
    result = simulate_wc2030(
        STATE.engine, STATE.teams, n_sims=req.n_sims, seed=req.seed, blocks=req.blocks
    )
    result["elapsed_ms"] = round(1000 * (time.perf_counter() - t0), 1)
    result["model_version"] = STATE.engine.model_version
    result["data_cutoff"] = STATE.engine.data_cutoff
    for row in result["teams"]:
        row["team"] = team_payload(row["team_id"])
    return result
